"""V0.6 capability and service mapping tests."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "ha_menu_c3"))
from controls import adjustment, attributes_payload, BITS


def state(value="on", **attrs):
    return SimpleNamespace(state=value, attributes=attrs)


class V06ControlsTests(unittest.TestCase):
    def test_cover_position_and_actions(self):
        entry = {"entity_id": "cover.bedroom", "controls": {
            "cover_position": True, "cover_open": True, "cover_stop": True, "cover_close": True}}
        current = state(supported_features=15, current_position=53)
        payload = attributes_payload(entry, current)
        self.assertEqual(payload["flags"], 128 | 256 | 512 | 1024)
        pos = adjustment(entry, current, "cover_position", "75")
        self.assertEqual(pos.data["position"], 75)
        self.assertEqual((pos.domain, pos.service), ("cover", "set_cover_position"))
        self.assertEqual(adjustment(entry, current, "cover_stop", "1").service, "stop_cover")

    def test_fan_speed_direction_oscillation(self):
        entry = {"entity_id": "fan.office", "controls": {
            "fan_percentage": True, "fan_oscillate": True, "fan_direction": True}}
        current = state(supported_features=7, percentage=45, oscillating=True, direction="forward")
        payload = attributes_payload(entry, current)
        self.assertEqual(payload["flags"], 2048 | 4096 | 8192)
        self.assertEqual(adjustment(entry, current, "fan_percentage", "80").data["percentage"], 80)
        self.assertEqual(adjustment(entry, current, "fan_oscillate", "0").data["oscillating"], False)
        self.assertEqual(adjustment(entry, current, "fan_direction", "reverse").data["direction"], "reverse")

    def test_media_controls(self):
        entry = {"entity_id": "media_player.tv", "controls": {
            "media_volume": True, "media_toggle": True,
            "media_next": True, "media_previous": True}}
        current = state(supported_features=4 | 1 | 32 | 16, volume_level=0.45)
        payload = attributes_payload(entry, current)
        self.assertEqual(payload["flags"], 16384 | 32768 | 65536 | 131072)
        request = adjustment(entry, current, "media_volume", "65")
        self.assertEqual(request.service, "volume_set")
        self.assertEqual(request.data["volume_level"], 0.65)
        self.assertEqual(adjustment(entry, current, "media_next", "1").service, "media_next_track")

    def test_disabled_capabilities_cannot_execute(self):
        entry = {"entity_id": "cover.basic", "controls": {"cover_position": True}}
        with self.assertRaises(ValueError):
            adjustment(entry, state(supported_features=1), "cover_position", "75")


if __name__ == "__main__":
    unittest.main()
