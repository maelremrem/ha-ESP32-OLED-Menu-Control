"""Capability checks and safe service requests for rotary device controls."""

from __future__ import annotations

from dataclasses import dataclass

BITS = {
    "brightness": 1, "color_temp": 2, "color": 4,
    "temperature": 8, "hvac_mode": 16,
    "humidity": 32, "humidifier_mode": 64,
    "cover_position": 128, "cover_open": 256, "cover_stop": 512, "cover_close": 1024,
    "fan_percentage": 2048, "fan_oscillate": 4096, "fan_direction": 8192,
    "media_volume": 16384, "media_toggle": 32768,
    "media_next": 65536, "media_previous": 131072,
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
        "cover_position": 0, "fan_percentage": 0, "fan_oscillating": 0,
        "fan_direction": "forward", "media_volume": 50,
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
    elif domain == "cover":
        features = bounded_int(attrs.get("supported_features"), 0, 2**20, 0)
        for name, supported in (
            ("cover_position", features & 4), ("cover_open", features & 1),
            ("cover_stop", features & 8), ("cover_close", features & 2),
        ):
            if settings.get(name) and supported:
                payload["flags"] |= BITS[name]
        payload["cover_position"] = bounded_int(attrs.get("current_position"), 0, 100, 0)
    elif domain == "fan":
        features = bounded_int(attrs.get("supported_features"), 0, 2**20, 0)
        for name, feature in (
            ("fan_percentage", 1), ("fan_oscillate", 2), ("fan_direction", 4),
        ):
            if settings.get(name) and features & feature:
                payload["flags"] |= BITS[name]
        payload["fan_percentage"] = bounded_int(attrs.get("percentage"), 0, 100, 0)
        payload["fan_oscillating"] = int(attrs.get("oscillating") is True)
        payload["fan_direction"] = "reverse" if attrs.get("direction") == "reverse" else "forward"
    elif domain == "media_player":
        features = bounded_int(attrs.get("supported_features"), 0, 2**24, 0)
        for name, supported in (
            ("media_volume", features & 4),
            ("media_toggle", features & (1 | 16384)),
            ("media_next", features & 32),
            ("media_previous", features & 16),
        ):
            if settings.get(name) and supported:
                payload["flags"] |= BITS[name]
        try:
            volume = float(attrs.get("volume_level") or 0) * 100
        except (ValueError, TypeError):
            volume = 50
        payload["media_volume"] = bounded_int(volume, 0, 100, 50)
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
    if field in ("brightness", "color_temp", "color", "temperature", "humidity", "cover_position", "fan_percentage", "media_volume") and (number is None or not number == number or number == float("inf") or number == float("-inf")):
        raise ValueError("Valeur invalide")
    data = {"entity_id": entity}
    if field == "brightness":
        data["brightness"] = bounded_int(number, 0, 255, 0)
        data["transition"] = 0
        return Adjustment("light", "turn_on", data)
    if field == "color_temp":
        data["color_temp_kelvin"] = bounded_int(number, payload["min_kelvin"], payload["max_kelvin"], payload["kelvin"])
        data["transition"] = 0
        return Adjustment("light", "turn_on", data)
    if field == "color":
        data["hs_color"] = [bounded_int(number, 0, 359, 0), 100]
        data["transition"] = 0
        return Adjustment("light", "turn_on", data)
    if field == "temperature":
        tenths = bounded_int(number, payload["min_temp_x10"], payload["max_temp_x10"], payload["temp_x10"])
        data["temperature"] = tenths / 10
        return Adjustment("climate", "set_temperature", data)
    if field == "humidity":
        data["humidity"] = bounded_int(number, payload["min_humidity"], payload["max_humidity"], payload["humidity"])
        return Adjustment("humidifier", "set_humidity", data)
    if field == "cover_position":
        data["position"] = bounded_int(number, 0, 100, 0)
        return Adjustment("cover", "set_cover_position", data)
    if field in ("cover_open", "cover_stop", "cover_close"):
        return Adjustment("cover", {"cover_open": "open_cover",
                                     "cover_stop": "stop_cover",
                                     "cover_close": "close_cover"}[field], data)
    if field == "fan_percentage":
        data["percentage"] = bounded_int(number, 0, 100, 0)
        return Adjustment("fan", "set_percentage", data)
    if field == "fan_oscillate":
        data["oscillating"] = str(value) in ("true", "1", "on")
        return Adjustment("fan", "oscillate", data)
    if field == "fan_direction":
        if value not in ("forward", "reverse"):
            raise ValueError("Direction invalide")
        data["direction"] = value
        return Adjustment("fan", "set_direction", data)
    if field == "media_volume":
        data["volume_level"] = bounded_int(number, 0, 100, 50) / 100
        return Adjustment("media_player", "volume_set", data)
    if field in ("media_toggle", "media_next", "media_previous"):
        return Adjustment("media_player", {"media_toggle": "media_play_pause",
                          "media_next": "media_next_track",
                          "media_previous": "media_previous_track"}[field], data)
    selected = str(value)
    modes = payload["modes"].split("|")
    if selected not in modes:
        raise ValueError("Mode non disponible")
    if field == "hvac_mode":
        data["hvac_mode"] = selected
        return Adjustment("climate", "set_hvac_mode", data)
    data["mode"] = selected
    return Adjustment("humidifier", "set_mode", data)
