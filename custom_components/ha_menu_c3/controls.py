"""Capability checks and safe service requests for rotary device controls."""

from __future__ import annotations

from dataclasses import dataclass

BITS = {
    "brightness": 1, "color_temp": 2, "color": 4,
    "temperature": 8, "hvac_mode": 16,
    "humidity": 32, "humidifier_mode": 64,
}
COLORS = {"hs", "rgb", "rgbw", "rgbww", "xy"}


@dataclass(frozen=True)
class Adjustment:
    domain: str
    service: str
    data: dict


def bounded_int(value, low: int, high: int, fallback: int) -> int:
    try:
        return min(high, max(low, int(round(float(value)))))
    except (ValueError, TypeError, OverflowError):
        return fallback


def attributes_payload(item: dict, state) -> dict:
    """Return firmware-ready capabilities; unavailable features are hidden."""
    entity_id = item.get("entity_id", "")
    domain = entity_id.split(".", 1)[0]
    settings = item.get("controls") or {}
    attrs = state.attributes if state is not None else {}
    payload = {
        "flags": 0, "slot": 0, "brightness": 128, "kelvin": 3000,
        "hue": 0, "temp_x10": 200, "humidity": 50,
        "min_kelvin": 2000, "max_kelvin": 6500,
        "min_temp_x10": 70, "max_temp_x10": 350, "temp_step_x10": 5,
        "min_humidity": 0, "max_humidity": 100, "humidity_step": 1,
        "modes": "", "current_mode": "", "temp_unit": "C",
    }
    if not state or state.state in ("unknown", "unavailable"):
        return payload
    modes = set(attrs.get("supported_color_modes") or [])
    if domain == "light":
        if settings.get("brightness") and modes and modes != {"onoff"}:
            payload["flags"] |= BITS["brightness"]
        if settings.get("color_temp") and "color_temp" in modes:
            payload["flags"] |= BITS["color_temp"]
        if settings.get("color") and bool(modes & COLORS):
            payload["flags"] |= BITS["color"]
        payload["brightness"] = bounded_int(attrs.get("brightness"), 0, 255, 128)
        payload["min_kelvin"] = bounded_int(attrs.get("min_color_temp_kelvin"), 1000, 15000, 2000)
        payload["max_kelvin"] = bounded_int(attrs.get("max_color_temp_kelvin"), payload["min_kelvin"], 15000, 6500)
        payload["kelvin"] = bounded_int(attrs.get("color_temp_kelvin"), payload["min_kelvin"], payload["max_kelvin"], 3000)
        hs = attrs.get("hs_color")
        if isinstance(hs, (list, tuple)) and hs:
            payload["hue"] = bounded_int(hs[0], 0, 359, 0)
    elif domain == "climate":
        features = bounded_int(attrs.get("supported_features"), 0, 2**20, 0)
        if settings.get("temperature") and features & 1:
            payload["flags"] |= BITS["temperature"]
        modes = [m for m in (attrs.get("hvac_modes") or []) if isinstance(m, str) and 0 < len(m) <= 30 and "|" not in m]
        modes = modes[:12]
        if settings.get("hvac_mode") and modes:
            payload["flags"] |= BITS["hvac_mode"]
        payload["modes"] = "|".join(modes)
        payload["current_mode"] = state.state if state.state in modes else (modes[0] if modes else "")
        payload["temp_unit"] = "F" if attrs.get("temperature_unit") in ("°F", "F") else "C"
        payload["min_temp_x10"] = bounded_int(float(attrs.get("min_temp", 7) or 7) * 10, -500, 1000, 70)
        payload["max_temp_x10"] = bounded_int(float(attrs.get("max_temp", 35) or 35) * 10, payload["min_temp_x10"], 1000, 350)
        payload["temp_step_x10"] = bounded_int(float(attrs.get("target_temp_step", 0.5) or 0.5) * 10, 1, 100, 5)
        payload["temp_x10"] = bounded_int(float(attrs.get("temperature", 20) or 20) * 10, payload["min_temp_x10"], payload["max_temp_x10"], 200)
    elif domain == "humidifier":
        if settings.get("humidity"):
            payload["flags"] |= BITS["humidity"]
        features = bounded_int(attrs.get("supported_features"), 0, 2**20, 0)
        modes = [m for m in (attrs.get("available_modes") or []) if isinstance(m, str) and 0 < len(m) <= 30 and "|" not in m]
        modes = modes[:12]
        if settings.get("humidifier_mode") and (features & 1) and modes:
            payload["flags"] |= BITS["humidifier_mode"]
        payload["modes"] = "|".join(modes)
        payload["current_mode"] = attrs.get("mode") if attrs.get("mode") in modes else (modes[0] if modes else "")
        payload["min_humidity"] = bounded_int(attrs.get("min_humidity"), 0, 100, 0)
        payload["max_humidity"] = bounded_int(attrs.get("max_humidity"), payload["min_humidity"], 100, 100)
        payload["humidity_step"] = bounded_int(attrs.get("target_humidity_step"), 1, 20, 1)
        payload["humidity"] = bounded_int(attrs.get("humidity", attrs.get("target_humidity")), payload["min_humidity"], payload["max_humidity"], 50)
    return payload


def adjustment(item: dict, state, field: str, value: str) -> Adjustment:
    """Validate both the configured permission and current entity capability."""
    payload = attributes_payload(item, state)
    if field not in BITS or not payload["flags"] & BITS[field]:
        raise ValueError("Reglage indisponible")
    entity = item["entity_id"]
    kind = entity.split(".", 1)[0]
    try:
        number = float(value)
    except (ValueError, TypeError):
        number = None
    if field in ("brightness", "color_temp", "color", "temperature", "humidity") and (number is None or not number == number or number == float("inf") or number == float("-inf")):
        raise ValueError("Valeur invalide")
    data = {"entity_id": entity}
    if field == "brightness":
        data["brightness"] = bounded_int(number, 0, 255, 0)
        data["transition"] = 0
        return Adjustment("light", "turn_on", data)
    if field == "color_temp":
        data["color_temp_kelvin"] = bounded_int(number, payload["min_kelvin"], payload["max_kelvin"], payload["kelvin"])
        return Adjustment("light", "turn_on", data)
    if field == "color":
        data["hs_color"] = [bounded_int(number, 0, 359, 0), 100]
        return Adjustment("light", "turn_on", data)
    if field == "temperature":
        tenths = bounded_int(number, payload["min_temp_x10"], payload["max_temp_x10"], payload["temp_x10"])
        data["temperature"] = tenths / 10
        return Adjustment("climate", "set_temperature", data)
    if field == "humidity":
        data["humidity"] = bounded_int(number, payload["min_humidity"], payload["max_humidity"], payload["humidity"])
        return Adjustment("humidifier", "set_humidity", data)
    selected = str(value)
    modes = payload["modes"].split("|")
    if selected not in modes:
        raise ValueError("Mode non disponible")
    if field == "hvac_mode":
        data["hvac_mode"] = selected
        return Adjustment("climate", "set_hvac_mode", data)
    data["mode"] = selected
    return Adjustment("humidifier", "set_mode", data)
