"""Portable configuration validation, independent from Home Assistant."""

from __future__ import annotations

import re

MAX_ITEMS = 32
ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
SERVICE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")


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
        entries.append({
            "id": ident, "label": label.strip(), "parent": parent,
            "service": service, "entity_id": entity.strip(), "data": data,
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

    return {
        "settings": {"sleep_seconds": sleep_seconds},
        "items": sorted_items,
        "led": {
            "entity_id": status_entity.strip(),
            "active_state": active_state.strip(),
            "on": rgb("on", [0, 180, 0]),
            "off": rgb("off", [0, 0, 0]),
        },
    }


DEFAULT_CONFIG = validate_config({"items": [], "led": {}})
