"""Portable configuration validation, independent from Home Assistant."""

from __future__ import annotations

import re

MAX_ITEMS = 32
ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
SERVICE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
CONTROL_KEYS = {
    "brightness": "light", "color_temp": "light", "color": "light",
    "temperature": "climate", "hvac_mode": "climate",
    "humidity": "humidifier", "humidifier_mode": "humidifier",
    "cover_position": "cover", "cover_open": "cover", "cover_stop": "cover", "cover_close": "cover",
    "fan_percentage": "fan", "fan_oscillate": "fan", "fan_direction": "fan",
    "media_volume": "media_player", "media_toggle": "media_player",
    "media_next": "media_player", "media_previous": "media_player",
}

ITEM_KINDS = {"action", "info", "local"}
LOCAL_COMMANDS = {"led_toggle", "identify", "oled_sleep"}
GESTURES = ("double", "triple", "hold")



class MenuValidationError(ValueError):
    """Invalid menu configuration."""


def validate_config(config: dict) -> dict:
    """Validate, normalize and flatten the menu to a stable preorder."""
    if not isinstance(config, dict):
        raise MenuValidationError("Configuration invalide")

    items = config.get("items", [])
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise MenuValidationError("Maximum 32 entrées")

    entries = []
    seen = set()
    for raw in items:
        if not isinstance(raw, dict):
            raise MenuValidationError("Entrée invalide")
        ident = raw.get("id", "")
        label = raw.get("label", "")
        parent = raw.get("parent", "")
        service = raw.get("service", "")
        entity = raw.get("entity_id", "")
        data = raw.get("data", {})
        controls = raw.get("controls", {})
        kind = raw.get("kind", "action")
        local_command = raw.get("local_command", "")
        confirm = raw.get("confirm", False)
        if kind not in ITEM_KINDS or type(confirm) is not bool:
            raise MenuValidationError(f"Type d'entree invalide : {ident}")
        if not isinstance(local_command, str) or (kind == "local" and local_command not in LOCAL_COMMANDS):
            raise MenuValidationError(f"Action locale invalide : {ident}")
        if not isinstance(ident, str) or not ID_PATTERN.fullmatch(ident):
            raise MenuValidationError("Identifiant invalide (lettres, chiffres, _ et -)")
        if ident == "__about":
            raise MenuValidationError("Identifiant reserve : __about")
        if ident in seen:
            raise MenuValidationError(f"Identifiant dupliqué : {ident}")
        seen.add(ident)
        if not isinstance(label, str) or not label.strip() or len(label.encode("utf-8")) > 64:
            raise MenuValidationError(f"Libellé invalide (64 octets max) : {ident}")
        if not isinstance(parent, str) or (parent and not ID_PATTERN.fullmatch(parent)):
            raise MenuValidationError(f"Parent invalide : {ident}")
        if not isinstance(service, str) or (service and not SERVICE_PATTERN.fullmatch(service)):
            raise MenuValidationError(f"Action invalide : {ident}")
        if not isinstance(entity, str) or len(entity) > 255:
            raise MenuValidationError(f"Entité invalide : {ident}")
        if not isinstance(data, dict):
            raise MenuValidationError(f"Données d'action invalides : {ident}")
        # Reject huge or deeply nested action data before persisting / executing it.
        import json
        try:
            serialized = json.dumps(data, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError, RecursionError) as err:
            raise MenuValidationError(f"Données d'action non JSON : {ident}") from err
        if len(serialized.encode("utf-8")) > 4096:
            raise MenuValidationError(f"Données d'action trop longues : {ident}")
        if not isinstance(controls, dict) or any(
            key not in CONTROL_KEYS or type(value) is not bool
            for key, value in controls.items()
        ):
            raise MenuValidationError(f"Commandes avancees invalides : {ident}")
        active_controls = {key: True for key, value in controls.items() if value}
        if kind != "action":
            active_controls = {}
        if active_controls:
            domain = entity.split(".", 1)[0]
            if any(CONTROL_KEYS[key] != domain for key in active_controls):
                raise MenuValidationError(f"Commandes incompatibles avec l'entite : {ident}")
        entries.append({
            "id": ident, "label": label.strip(), "parent": parent,
            "service": service, "entity_id": entity.strip(), "data": data,
            "controls": active_controls,
            "kind": kind, "local_command": local_command if kind == "local" else "",
            "confirm": confirm if kind != "info" else False,
        })

    by_id = {item["id"]: item for item in entries}
    for item in entries:
        if item["parent"] and item["parent"] not in by_id:
            raise MenuValidationError(f"Parent introuvable : {item['parent']}")
        if item["parent"] == item["id"]:
            raise MenuValidationError("Un menu ne peut pas être son propre parent")

    sorted_items = []
    visited = set()
    active = set()

    def visit(item: dict, depth: int) -> None:
        if depth > 8:
            raise MenuValidationError("8 niveaux maximum")
        ident = item["id"]
        if ident in active:
            raise MenuValidationError("Boucle détectée dans les sous-menus")
        if ident in visited:
            return
        active.add(ident)
        visited.add(ident)
        sorted_items.append(item)
        for child in entries:
            if child["parent"] == ident:
                visit(child, depth + 1)
        active.remove(ident)

    for item in entries:
        if not item["parent"]:
            visit(item, 0)
    if len(sorted_items) != len(entries):
        raise MenuValidationError("Sous-menu inaccessible ou boucle de parents")

    led = config.get("led", {})
    if not isinstance(led, dict):
        raise MenuValidationError("Configuration LED invalide")

    def rgb(key: str, fallback: list[int]) -> list[int]:
        value = led.get(key, fallback)
        if (not isinstance(value, list) or len(value) != 3 or
                any(type(ch) is not int or not 0 <= ch <= 255 for ch in value)):
            raise MenuValidationError(f"Couleur LED invalide : {key}")
        return value

    status_entity = led.get("entity_id", "")
    active_state = led.get("active_state", "on")
    if not isinstance(status_entity, str) or len(status_entity) > 255:
        raise MenuValidationError("Entité de statut LED invalide")
    if not isinstance(active_state, str) or not 0 < len(active_state) <= 80:
        raise MenuValidationError("État actif LED invalide")

    settings = config.get("settings", {})
    if not isinstance(settings, dict):
        raise MenuValidationError("Paramètres invalides")
    sleep_seconds = settings.get("sleep_seconds", 30)
    if type(sleep_seconds) is not int or not 0 <= sleep_seconds <= 3600:
        raise MenuValidationError("Veille : entier entre 0 et 3600 secondes")

    opts = {
        "language": ("fr", "en"),
        "font_size": ("normal", "small"),
        "brightness_step": (1, 5, 10),
    }
    for key, values in opts.items():
        default = {"language": "fr", "font_size": "normal", "brightness_step": 5}[key]
        if settings.get(key, default) not in values:
            raise MenuValidationError(f"Parametre {key} invalide")
    for key, default in {"direct_edit": False, "encoder_inverted": False,
                         "animations": True, "offline_cache": True}.items():
        if type(settings.get(key, default)) is not bool:
            raise MenuValidationError(f"Parametre {key} invalide")
    animation_ms = settings.get("animation_ms", 220)
    if type(animation_ms) is not int or not 100 <= animation_ms <= 500:
        raise MenuValidationError("Vitesse animation invalide")
    contrast = settings.get("oled_contrast", 80)
    if type(contrast) is not int or not 1 <= contrast <= 100:
        raise MenuValidationError("Contraste OLED invalide")
    shortcuts = config.get("shortcuts", {})
    if not isinstance(shortcuts, dict) or any(g not in GESTURES for g in shortcuts):
        raise MenuValidationError("Raccourcis invalides")
    safe_shortcuts = {}
    for gesture, action in shortcuts.items():
        if not isinstance(action, dict):
            raise MenuValidationError("Raccourci invalide")
        svc = action.get("service", "")
        entity_id = action.get("entity_id", "")
        payload = action.get("data", {})
        if not svc and not entity_id and not payload:
            continue
        if (not isinstance(svc, str) or not SERVICE_PATTERN.fullmatch(svc)
                or not isinstance(entity_id, str) or len(entity_id) > 255
                or not isinstance(payload, dict)):
            raise MenuValidationError("Service de raccourci invalide")
        import json
        try:
            raw = json.dumps(payload, allow_nan=False)
        except (TypeError, ValueError, RecursionError) as err:
            raise MenuValidationError("Donnees de raccourci invalides") from err
        if len(raw.encode("utf-8")) > 2048:
            raise MenuValidationError("Donnees de raccourci trop longues")
        safe_shortcuts[gesture] = {"service": svc, "entity_id": entity_id.strip(), "data": payload}

    return {
        "settings": {
            "sleep_seconds": sleep_seconds,
            "language": settings.get("language", "fr"),
            "font_size": settings.get("font_size", "normal"),
            "brightness_step": settings.get("brightness_step", 5),
            "direct_edit": settings.get("direct_edit", False),
            "encoder_inverted": settings.get("encoder_inverted", False),
            "animations": settings.get("animations", True),
            "animation_ms": animation_ms,
            "offline_cache": settings.get("offline_cache", True),
            "oled_contrast": contrast,
        },
        "shortcuts": safe_shortcuts,
        "items": sorted_items,
        "led": {
            "entity_id": status_entity.strip(),
            "active_state": active_state.strip(),
            "on": rgb("on", [0, 180, 0]),
            "off": rgb("off", [0, 0, 0]),
        },
    }


DEFAULT_CONFIG = validate_config({"items": [], "led": {}})
