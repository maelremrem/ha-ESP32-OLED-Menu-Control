"""HA Menu C3: dynamic menu editor and ESPHome action bridge."""

from __future__ import annotations

import asyncio
import logging
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
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_DEVICE_NAME,
    DOMAIN,
    EVENT_READY,
    EVENT_SELECTED,
    PANEL_URL,
)
from .model import DEFAULT_CONFIG, MenuValidationError, validate_config

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1
STORAGE_KEY = "ha_menu_c3"
FRONTEND_FILE = Path(__file__).parent / "frontend" / "ha-menu-panel.js"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Allow the config flow to load this integration."""
    return True


class MenuManager:
    """Persist the menu, dispatch actions, synchronize the ESPHome display."""

    def __init__(self, hass: HomeAssistant, device_name: str) -> None:
        self.hass = hass
        self.device_name = device_name
        self.device_slug = device_name.replace("-", "_")
        self.store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.config = validate_config(DEFAULT_CONFIG)
        self.sync_lock = asyncio.Lock()
        self.last_sync = "not_synced"
        self.last_error = ""
        self.last_sync_at = None
        self.heartbeat_ok = False

    async def load(self) -> None:
        stored = await self.store.async_load()
        if stored:
            try:
                self.config = validate_config(stored)
            except MenuValidationError:
                _LOGGER.exception("Stored HA Menu C3 configuration is invalid")

    async def save(self, data: dict) -> dict:
        config = validate_config(data)
        self.config = config
        await self.store.async_save(config)
        await self.sync()
        return self.status()

    def diagnostics(self) -> dict:
        """Read ESPHome diagnostics without assuming the entity has its default name."""
        suffixes = {
            "wifi": "wifi_signal",
            "uptime": "uptime",
            "ip": "ip_address",
            "extension_connected": "extension_connected",
            "extension_update": "extension_last_update",
        }
        found = {key: None for key in suffixes}
        # ESPHome's normal entity IDs start with the node's friendly-name slug.
        # Renamed IDs remain available in the native ESPHome device page.
        for state in self.hass.states.async_all():
            object_id = state.entity_id.split(".", 1)[-1]
            if not object_id.startswith(self.device_slug + "_"):
                continue
            for key, suffix in suffixes.items():
                if object_id == f"{self.device_slug}_{suffix}" or object_id.endswith("_" + suffix):
                    found[key] = {"entity_id": state.entity_id, "state": state.state,
                                  "unit": state.attributes.get("unit_of_measurement", "")}
        return found

    def status(self) -> dict:
        return {
            "device": self.device_name,
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
                    })
                await self._call_esp("set_menu_count", {"count": len(items)})
                await self._call_esp("set_sleep_timeout", {
                    "seconds": self.config["settings"]["sleep_seconds"]
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

    async def handle_selection(self, item_id: str) -> None:
        item = next((i for i in self.config["items"] if i["id"] == item_id), None)
        success = False
        try:
            if item is None:
                raise ValueError(f"Unknown menu entry {item_id}")
            if any(i["parent"] == item_id for i in self.config["items"]):
                raise ValueError("Submenu entry cannot execute an action")
            if not item["service"]:
                raise ValueError(f"No action configured for {item_id}")

            domain, action = item["service"].split(".", 1)
            if not self.hass.services.has_service(domain, action):
                raise ValueError(f"Action unavailable: {domain}.{action}")
            service_data = dict(item["data"])
            if item["entity_id"]:
                service_data["entity_id"] = item["entity_id"]
            await self.hass.services.async_call(domain, action, service_data, blocking=True)
            success = True
        except Exception:
            _LOGGER.exception("HA Menu C3 action failed for %s", item_id)
        finally:
            try:
                await self._call_esp("action_result", {
                    "item_id": item_id, "success": success,
                })
            except Exception as err:
                _LOGGER.warning("Unable to report action result: %s", err)

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
        if event.data.get("entity_id") == self.config["led"]["entity_id"]:
            self.hass.async_create_task(self._sync_led_safe())

    async def _sync_led_safe(self) -> None:
        try:
            await self.sync_led()
        except Exception as err:
            _LOGGER.debug("Could not update base LED: %s", err)


@websocket_api.websocket_command({vol.Required("type"): "ha_menu_c3/get"})
@websocket_api.require_admin
@callback
def ws_get(hass, connection, msg):
    """Retrieve the currently saved menu."""
    manager = hass.data.get(DOMAIN)
    if manager is None:
        connection.send_error(msg["id"], "not_loaded", "Integration not loaded")
        return
    connection.send_result(msg["id"], manager.status())


@websocket_api.websocket_command({
    vol.Required("type"): "ha_menu_c3/save",
    vol.Required("config"): dict,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_save(hass, connection, msg):
    """Validate and persist the editor state, then attempt live sync."""
    manager = hass.data.get(DOMAIN)
    if manager is None:
        connection.send_error(msg["id"], "not_loaded", "Integration not loaded")
        return
    try:
        result = await manager.save(msg["config"])
    except MenuValidationError as err:
        connection.send_error(msg["id"], "invalid_config", str(err))
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "ha_menu_c3/sync"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_sync(hass, connection, msg):
    """Manually resynchronize after reconnecting the device."""
    manager = hass.data.get(DOMAIN)
    if manager is None:
        connection.send_error(msg["id"], "not_loaded", "Integration not loaded")
        return
    await manager.sync()
    connection.send_result(msg["id"], manager.status())


@websocket_api.websocket_command({vol.Required("type"): "ha_menu_c3/identify"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_identify(hass, connection, msg):
    """Identify the hardware through its purple LED animation."""
    manager = hass.data.get(DOMAIN)
    if manager is None:
        connection.send_error(msg["id"], "not_loaded", "Integration not loaded")
        return
    try:
        await manager._call_esp("play_led_animation", {"animation": "identify"})
    except Exception as err:
        connection.send_error(msg["id"], "device_error", str(err))
        return
    connection.send_result(msg["id"], {"ok": True})


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Register the backend event bridge and the sidebar panel."""
    manager = MenuManager(hass, entry.data[CONF_DEVICE_NAME])
    await manager.load()
    hass.data[DOMAIN] = manager

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
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="ha-menu-c3-panel",
        frontend_url_path=PANEL_URL,
        sidebar_title="HA Menu C3",
        sidebar_icon="mdi:gesture-tap-button",
        module_url="/ha_menu_c3_assets/ha-menu-panel.js?v=2",
        require_admin=True,
    )

    entry.async_on_unload(hass.bus.async_listen(EVENT_READY, manager.on_ready))
    entry.async_on_unload(hass.bus.async_listen(EVENT_SELECTED, manager.on_selected))
    entry.async_on_unload(hass.bus.async_listen(EVENT_STATE_CHANGED, manager.on_state))
    entry.async_on_unload(hass.bus.async_listen(
        "esphome.ha_menu_sleep_changed", manager.on_sleep_changed))
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
    """Unload event listeners and the sidebar panel."""
    entry.async_unload()
    hass.data.pop(DOMAIN, None)
    frontend.async_remove_panel(hass, PANEL_URL)
    return True
