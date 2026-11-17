"""HA Menu C3: dynamic menu editor and ESPHome action bridge."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import (
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_STATE_CHANGED,
    HomeAssistant,
    callback,
)
from homeassistant.helpers.storage import Store
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_DEVICE_NAME,
    DOMAIN,
    EVENT_READY,
    EVENT_SELECTED,
    PANEL_URL,
)
from .model import DEFAULT_CONFIG, MenuValidationError, validate_config
from .controls import adjustment, attributes_payload
from .realtime import LatestAdjustmentQueue

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1
STORAGE_KEY = "ha_menu_c3"
FRONTEND_FILE = Path(__file__).parent / "frontend" / "ha-menu-panel.js"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Allow the config flow to load this integration."""
    return True


class MenuManager:
    """Persist the menu, dispatch actions, synchronize the ESPHome display."""

    def __init__(self, hass: HomeAssistant, device_name: str, entry_id: str, migrate_legacy: bool = False) -> None:
        self.hass = hass
        self.device_name = device_name
        self.device_slug = device_name.replace("-", "_")
        self.entry_id = entry_id
        self.store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{self.device_slug}")
        self.migrate_legacy = migrate_legacy
        self.reported_diagnostics = {}
        self.reported_at = None
        self.config = validate_config(DEFAULT_CONFIG)
        self.sync_lock = asyncio.Lock()
        self.adjustments = LatestAdjustmentQueue(hass.async_create_task, self.apply_control)
        self.last_sync = "not_synced"
        self.last_error = ""
        self.last_sync_at = None
        self.heartbeat_ok = False

    async def load(self) -> None:
        stored = await self.store.async_load()
        if stored is None and self.migrate_legacy:
            stored = await Store(self.hass, STORAGE_VERSION, STORAGE_KEY).async_load()
            if stored is not None:
                _LOGGER.info("Migrating menu settings for %s", self.device_name)
        if stored:
            try:
                self.config = validate_config(stored)
                if self.migrate_legacy:
                    await self.store.async_save(self.config)
            except MenuValidationError:
                _LOGGER.exception("Stored HA Menu C3 configuration is invalid")

    async def save(self, data: dict) -> dict:
        config = validate_config(data)
        self.config = config
        await self.store.async_save(config)
        await self.sync()
        return self.status()

    def diagnostics(self) -> dict:
        """Resolve ESPHome diagnostic entities, including renamed entity IDs."""
        aliases = {
            "wifi": ("wifi_signal", "wifi_signal_strength"),
            "uptime": ("uptime",),
            "ip": ("ip_address",),
            "ssid": ("wifi_ssid",),
            "extension_connected": ("extension_connected",),
            "extension_update": ("extension_last_update",),
        }
        found = {key: None for key in aliases}
        try:
            devices = dr.async_get(self.hass)
            entities = er.async_get(self.hass)
            needle = self.device_name.replace("-", "_").lower()
            device_ids = set()
            for device in devices.devices.values():
                names = [device.name, device.name_by_user]
                names += [str(value) for domain, value in device.identifiers if domain == "esphome"]
                if any(name and name.lower().replace("-", "_").replace(" ", "_") == needle
                       for name in names):
                    device_ids.add(device.id)
            registry_entries = {e.entity_id: e for e in entities.entities.values()
                                if e.device_id in device_ids}
        except Exception:  # Registry can be temporarily unavailable during startup.
            registry_entries = {}

        # Prefer registry-linked entities; use the ESPHome node name for fallback.
        candidates = list(registry_entries)
        legacy_names = {f"{self.device_slug}_{suffix}" for names in aliases.values()
                        for suffix in names}
        candidates.extend(s.entity_id for s in self.hass.states.async_all()
                          if s.entity_id.split(".", 1)[-1] in legacy_names)
        for entity_id in dict.fromkeys(candidates):
            state = self.hass.states.get(entity_id)
            if state is None:
                continue
            registry_entry = registry_entries.get(entity_id)
            names = [entity_id.rsplit(".", 1)[-1]]
            if registry_entry is not None:
                names.extend([registry_entry.original_name or "", registry_entry.unique_id or ""])
            normalized = [re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") for name in names]
            for key, suffixes in aliases.items():
                if found[key] is not None:
                    continue
                if any(n == suffix or n.endswith("_" + suffix)
                       for n in normalized for suffix in suffixes):
                    found[key] = {"entity_id": entity_id, "state": state.state,
                                  "unit": state.attributes.get("unit_of_measurement", "")}

        # Firmware v0.4 can report live diagnostics even if HA entities were renamed/disabled.
        if self.reported_at and datetime.now(timezone.utc) - self.reported_at < timedelta(seconds=100):
            for key, val in self.reported_diagnostics.items():
                if val not in ("", "unknown", "unavailable"):
                    found[key] = {"entity_id": None, "state": str(val),
                                  "unit": "dBm" if key == "wifi" else ""}
        return found

    @callback
    def on_diagnostics(self, event) -> None:
        if event.data.get("device") != self.device_name:
            return
        allowed = ("wifi", "uptime", "ip", "ssid", "extension_connected", "extension_update")
        self.reported_diagnostics = {key: event.data[key] for key in allowed
                                     if isinstance(event.data.get(key), (str, int, float))}
        self.reported_at = datetime.now(timezone.utc)

    def status(self) -> dict:
        return {
            "device": self.device_name,
            "entry_id": self.entry_id,
            "config": self.config,
            "sync": self.last_sync,
            "error": self.last_error,
            "last_sync_at": self.last_sync_at,
            "extension_online": self.heartbeat_ok,
            "diagnostics": self.diagnostics(),
        }

    async def _call_esp(self, action: str, data: dict) -> None:
        name = f"{self.device_slug}_{action}"
        if not self.hass.services.has_service("esphome", name):
            raise RuntimeError(
                f"Action esphome.{name} introuvable. Vérifie que le C3 "
                "est connecté et utilise le firmware V5."
            )
        await self.hass.services.async_call("esphome", name, data, blocking=True)

    def item_state(self, item: dict) -> str:
        """Render a short, safe state string for the 128x64 display."""
        entity_id = item.get("entity_id", "")
        if not entity_id:
            return ""
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return "?"
        if state.state in ("on", "off"):
            return state.state.upper()
        if state.state in ("open", "closed", "opening", "closing"):
            return {"open":"OPEN", "closed":"CLOSED", "opening":"OPENING", "closing":"CLOSING"}[state.state]
        unit = state.attributes.get("unit_of_measurement", "")
        text = f"{state.state} {unit}" if unit else str(state.state)
        return re.sub(r"[\r\n\t]+", " ", text).strip()[:12]

    async def sync_item_states(self, entity_id: str | None = None) -> None:
        """Send state snapshots; only the affected entity on live updates."""
        async with self.sync_lock:
            for slot, item in enumerate(self.config["items"]):
                if entity_id is not None and item["entity_id"] != entity_id:
                    continue
                await self._call_esp("set_menu_status", {
                    "slot": slot, "status": self.item_state(item),
                })
                await self._call_esp("set_control_flags", {
                    "slot": slot, "flags": self.control_payload(item)["flags"],
                })

    def control_payload(self, item: dict) -> dict:
        state = self.hass.states.get(item.get("entity_id", ""))
        return attributes_payload(item, state)

    async def _update_item_state_safe(self, entity_id: str) -> None:
        try:
            await self.sync_item_states(entity_id)
        except Exception as err:
            _LOGGER.debug("Unable to sync item status for %s: %s", entity_id, err)

    async def sync(self) -> None:
        """Send every entry in order; set the count last to commit."""
        async with self.sync_lock:
            self.last_sync = "syncing"
            self.last_error = ""
            try:
                items = self.config["items"]
                for slot, item in enumerate(items):
                    await self._call_esp("set_menu_item", {
                        "slot": slot,
                        "item_id": item["id"],
                        "parent_id": item["parent"],
                        "label": item["label"],
                        "kind": item.get("kind", "action"),
                        "local_command": item.get("local_command", ""),
                        "confirm": item.get("confirm", False),
                    })
                for slot, item in enumerate(items):
                    await self._call_esp("set_control_flags", {
                        "slot": slot, "flags": self.control_payload(item)["flags"],
                    })
                await self._call_esp("set_menu_count", {"count": len(items)})
                for slot, item in enumerate(items):
                    await self._call_esp("set_menu_status", {
                        "slot": slot, "status": self.item_state(item),
                    })
                await self._call_esp("set_sleep_timeout", {
                    "seconds": self.config["settings"]["sleep_seconds"]
                })
                settings = self.config["settings"]
                await self._call_esp("set_user_settings", {
                    "language": settings["language"],
                    "direct_edit": settings["direct_edit"],
                    "brightness_step": settings["brightness_step"],
                    "encoder_inverted": settings["encoder_inverted"],
                    "animations": settings["animations"],
                    "oled_contrast": settings["oled_contrast"],
                    "font_size": settings["font_size"],
                    "offline_cache": settings["offline_cache"],
                })
                await self.sync_led()
                stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
                await self._call_esp("set_extension_status", {"last_update": stamp})
            except Exception as err:  # device disconnected or service call failed
                self.last_sync = "error"
                self.heartbeat_ok = False
                self.last_error = str(err)
                _LOGGER.warning("Cannot sync HA Menu C3: %s", err)
            else:
                self.last_sync = "ok"
                self.heartbeat_ok = True
                self.last_sync_at = stamp
                _LOGGER.info("Synced %d items to %s", len(self.config["items"]), self.device_name)

    async def heartbeat(self) -> None:
        """Keep extension connectivity independent from ESPHome API log clients."""
        try:
            await self._call_esp("extension_heartbeat", {})
            self.heartbeat_ok = True
        except Exception as err:
            self.heartbeat_ok = False
            _LOGGER.debug("HA Menu C3 heartbeat failed: %s", err)

    async def save_sleep_from_device(self, seconds: int) -> None:
        """Keep the panel in sync if the native ESPHome number was changed."""
        if self.config["settings"]["sleep_seconds"] == seconds:
            return
        updated = dict(self.config)
        updated["settings"] = {"sleep_seconds": seconds}
        try:
            self.config = validate_config(updated)
        except MenuValidationError:
            _LOGGER.warning("Ignoring invalid sleep timeout from device: %s", seconds)
            return
        await self.store.async_save(self.config)

    @callback
    def on_sleep_changed(self, event) -> None:
        if event.data.get("device") != self.device_name:
            return
        try:
            seconds = int(event.data.get("seconds", ""))
        except (ValueError, TypeError):
            return
        self.hass.async_create_task(self.save_sleep_from_device(seconds))

    async def sync_led(self) -> None:
        led = self.config["led"]
        if led["entity_id"]:
            state = self.hass.states.get(led["entity_id"])
            active = state is not None and state.state == led["active_state"]
            red, green, blue = led["on"] if active else led["off"]
        else:
            red, green, blue = led["on"]
        await self._call_esp("set_base_led", {
            "red": red, "green": green, "blue": blue,
        })

    async def execute_shortcut(self, gesture: str) -> None:
        """Run explicitly configured user shortcuts on the HA side."""
        action = self.config.get("shortcuts", {}).get(gesture)
        if not action:
            return
        try:
            domain, service = action["service"].split(".", 1)
            if not self.hass.services.has_service(domain, service):
                raise ValueError(f"Service unavailable: {domain}.{service}")
            data = dict(action["data"])
            if action["entity_id"]:
                data["entity_id"] = action["entity_id"]
            await self.hass.services.async_call(domain, service, data, blocking=True)
        except Exception as err:
            _LOGGER.warning("Shortcut %s on %s failed: %s", gesture, self.device_name, err)

    @callback
    def on_shortcut(self, event) -> None:
        if event.data.get("device") != self.device_name:
            return
        gesture = event.data.get("gesture")
        if gesture in ("double", "triple", "hold"):
            self.hass.async_create_task(self.execute_shortcut(gesture))

    async def handle_selection(self, item_id: str) -> None:
        item = next((i for i in self.config["items"] if i["id"] == item_id), None)
        success = False
        message = "Commande envoyee"
        try:
            if item is None:
                raise ValueError(f"Unknown menu entry {item_id}")
            if item.get("kind") != "action":
                raise ValueError("Entry does not perform a Home Assistant action")
            if any(i["parent"] == item_id for i in self.config["items"]):
                raise ValueError("Submenu entry cannot execute an action")
            if not item["service"]:
                raise ValueError("Aucune action configuree")
            if item["entity_id"]:
                state = self.hass.states.get(item["entity_id"])
                if state is None or state.state == "unavailable":
                    raise ValueError("Entite indisponible")

            domain, action = item["service"].split(".", 1)
            if not self.hass.services.has_service(domain, action):
                raise ValueError(f"Action unavailable: {domain}.{action}")
            service_data = dict(item["data"])
            if item["entity_id"]:
                service_data["entity_id"] = item["entity_id"]
            await self.hass.services.async_call(domain, action, service_data, blocking=True)
            success = True
        except Exception as err:
            message = re.sub(r"[\r\n\t]+", " ", str(err)).strip()[:96] or "Echec de l'action"
            _LOGGER.exception("HA Menu C3 action failed for %s", item_id)
        finally:
            try:
                await self._call_esp("action_result", {
                    "item_id": item_id, "success": success, "message": message,
                })
            except Exception as err:
                _LOGGER.warning("Unable to report action result: %s", err)

    async def open_controls(self, item_id: str) -> None:
        item = next((i for i in self.config["items"] if i["id"] == item_id), None)
        if item is None:
            return
        try:
            payload = self.control_payload(item)
            if not payload["flags"]:
                raise ValueError("Aucun reglage disponible")
            payload["slot"] = self.config["items"].index(item)
            await self._call_esp("open_controls", payload)
        except Exception as err:
            _LOGGER.debug("Controls unavailable for %s: %s", item_id, err)
            await self._report_control_error(str(err))

    async def _report_control_error(self, message: str) -> None:
        try:
            await self._call_esp("control_error", {"message": str(message)[:80]})
        except Exception as err:
            _LOGGER.debug("Control error could not reach OLED: %s", err)

    async def apply_control(self, item_id: str, field: str, value: str) -> None:
        item = next((i for i in self.config["items"] if i["id"] == item_id), None)
        try:
            if item is None:
                raise ValueError("Entree inconnue")
            state = self.hass.states.get(item.get("entity_id", ""))
            if state is None or state.state in ("unavailable", "unknown"):
                raise ValueError("Appareil indisponible")
            request = adjustment(item, state, field, value)
            if not self.hass.services.has_service(request.domain, request.service):
                raise ValueError("Commande indisponible")
            # Serialize service completion so older brightness values cannot overtake newer ones.
            await self.hass.services.async_call(
                request.domain, request.service, request.data, blocking=True,
            )
        except Exception as err:
            _LOGGER.warning("Control %s/%s rejected: %s", item_id, field, err)
            await self._report_control_error(str(err))

    @callback
    def on_controls_open(self, event) -> None:
        if event.data.get("device") != self.device_name:
            return
        item_id = event.data.get("item_id")
        if isinstance(item_id, str) and item_id:
            self.hass.async_create_task(self.open_controls(item_id))

    @callback
    def on_adjust(self, event) -> None:
        if event.data.get("device") != self.device_name:
            return
        item_id = event.data.get("item_id")
        field = event.data.get("field")
        value = event.data.get("value")
        if isinstance(item_id, str) and isinstance(field, str) and isinstance(value, str):
            self.adjustments.push(item_id, field, value)

    @callback
    def on_ready(self, event) -> None:
        if event.data.get("device") != self.device_name:
            return
        self.hass.async_create_task(self.sync())

    @callback
    def on_selected(self, event) -> None:
        if event.data.get("device") != self.device_name:
            return
        item_id = event.data.get("item_id")
        if not isinstance(item_id, str) or not item_id:
            _LOGGER.warning("Received invalid menu selection: %s", event.data)
            return
        self.hass.async_create_task(self.handle_selection(item_id))

    @callback
    def on_state(self, event) -> None:
        entity_id = event.data.get("entity_id")
        if entity_id == self.config["led"]["entity_id"]:
            self.hass.async_create_task(self._sync_led_safe())
        if any(item["entity_id"] == entity_id for item in self.config["items"]):
            self.hass.async_create_task(self._update_item_state_safe(entity_id))

    async def _sync_led_safe(self) -> None:
        try:
            await self.sync_led()
        except Exception as err:
            _LOGGER.debug("Could not update base LED: %s", err)


def _managers(hass: HomeAssistant) -> dict[str, MenuManager]:
    return hass.data.get(DOMAIN, {})


def _get_manager(hass: HomeAssistant, msg: dict) -> MenuManager | None:
    managers = _managers(hass)
    requested = msg.get("entry_id")
    if requested:
        return managers.get(requested)
    return sorted(managers.values(), key=lambda mgr: mgr.device_name)[0] if managers else None


def _response(hass: HomeAssistant, manager: MenuManager) -> dict:
    return {
        **manager.status(),
        "devices": [
            {"entry_id": mgr.entry_id, "name": mgr.device_name,
             "online": mgr.heartbeat_ok, "sync": mgr.last_sync}
            for mgr in sorted(_managers(hass).values(), key=lambda mgr: mgr.device_name)
        ],
    }


@websocket_api.websocket_command({
    vol.Required("type"): "ha_menu_c3/get",
    vol.Optional("entry_id"): str,
})
@websocket_api.require_admin
@callback
def ws_get(hass, connection, msg):
    manager = _get_manager(hass, msg)
    if manager is None:
        connection.send_error(msg["id"], "not_loaded", "Appareil introuvable")
        return
    connection.send_result(msg["id"], _response(hass, manager))


@websocket_api.websocket_command({
    vol.Required("type"): "ha_menu_c3/save",
    vol.Optional("entry_id"): str,
    vol.Required("config"): dict,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_save(hass, connection, msg):
    manager = _get_manager(hass, msg)
    if manager is None:
        connection.send_error(msg["id"], "not_loaded", "Appareil introuvable")
        return
    try:
        await manager.save(msg["config"])
    except MenuValidationError as err:
        connection.send_error(msg["id"], "invalid_config", str(err))
        return
    connection.send_result(msg["id"], _response(hass, manager))


@websocket_api.websocket_command({
    vol.Required("type"): "ha_menu_c3/sync",
    vol.Optional("entry_id"): str,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_sync(hass, connection, msg):
    manager = _get_manager(hass, msg)
    if manager is None:
        connection.send_error(msg["id"], "not_loaded", "Appareil introuvable")
        return
    await manager.sync()
    connection.send_result(msg["id"], _response(hass, manager))


@websocket_api.websocket_command({
    vol.Required("type"): "ha_menu_c3/identify",
    vol.Optional("entry_id"): str,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_identify(hass, connection, msg):
    manager = _get_manager(hass, msg)
    if manager is None:
        connection.send_error(msg["id"], "not_loaded", "Appareil introuvable")
        return
    try:
        await manager._call_esp("play_led_animation", {"animation": "identify"})
    except Exception as err:
        connection.send_error(msg["id"], "device_error", str(err))
        return
    connection.send_result(msg["id"], {"ok": True})


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Set up a separately configured controller."""
    was_legacy = entry.unique_id == "main"
    manager = MenuManager(hass, entry.data[CONF_DEVICE_NAME], entry.entry_id, was_legacy)
    await manager.load()
    managers = hass.data.setdefault(DOMAIN, {})
    managers[entry.entry_id] = manager
    if was_legacy:
        hass.config_entries.async_update_entry(entry, unique_id=manager.device_name)

    if not hass.data.get(f"{DOMAIN}_ws_registered"):
        websocket_api.async_register_command(hass, ws_get)
        websocket_api.async_register_command(hass, ws_save)
        websocket_api.async_register_command(hass, ws_sync)
        websocket_api.async_register_command(hass, ws_identify)
        hass.data[f"{DOMAIN}_ws_registered"] = True

    if not hass.data.get(f"{DOMAIN}_static_registered"):
        await hass.http.async_register_static_paths([
            StaticPathConfig(
                "/ha_menu_c3_assets/ha-menu-panel.js", str(FRONTEND_FILE), cache_headers=False,
            )
        ])
        hass.data[f"{DOMAIN}_static_registered"] = True
    if not hass.data.get(f"{DOMAIN}_panel_registered"):
        await panel_custom.async_register_panel(
            hass,
            webcomponent_name="ha-menu-c3-panel",
            frontend_url_path=PANEL_URL,
            sidebar_title="HA Menu C3",
            sidebar_icon="mdi:gesture-tap-button",
            module_url="/ha_menu_c3_assets/ha-menu-panel.js?v=9",
            require_admin=True,
        )
        hass.data[f"{DOMAIN}_panel_registered"] = True

    entry.async_on_unload(hass.bus.async_listen(EVENT_READY, manager.on_ready))
    entry.async_on_unload(hass.bus.async_listen(EVENT_SELECTED, manager.on_selected))
    entry.async_on_unload(hass.bus.async_listen(
        "esphome.ha_menu_shortcut", manager.on_shortcut))
    entry.async_on_unload(hass.bus.async_listen(
        "esphome.ha_menu_controls_open", manager.on_controls_open))
    entry.async_on_unload(hass.bus.async_listen(
        "esphome.ha_menu_control_adjust", manager.on_adjust))
    entry.async_on_unload(hass.bus.async_listen(EVENT_STATE_CHANGED, manager.on_state))
    entry.async_on_unload(hass.bus.async_listen(
        "esphome.ha_menu_sleep_changed", manager.on_sleep_changed))
    entry.async_on_unload(hass.bus.async_listen(
        "esphome.ha_menu_diagnostics", manager.on_diagnostics))
    entry.async_on_unload(async_track_time_interval(
        hass, lambda now: hass.async_create_task(manager.heartbeat()), timedelta(seconds=30)))
    if hass.is_running:
        hass.async_create_task(manager.sync())
    else:
        entry.async_on_unload(hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED,
            lambda event: hass.async_create_task(manager.sync()),
        ))
    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    entry.async_unload()
    managers = hass.data.get(DOMAIN, {})
    manager = managers.pop(entry.entry_id, None)
    if manager is not None:
        manager.adjustments.close()
    if not managers:
        hass.data.pop(DOMAIN, None)
        frontend.async_remove_panel(hass, PANEL_URL)
        hass.data.pop(f"{DOMAIN}_panel_registered", None)
    return True
