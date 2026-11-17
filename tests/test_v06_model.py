"""V0.6 configuration validation and backwards compatibility."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "ha_menu_c3"))
from model import validate_config, MenuValidationError


class V06ModelTests(unittest.TestCase):
    def test_legacy_settings_keep_defaults(self):
        config = validate_config({"items": [], "led": {}})
        self.assertEqual(config["settings"]["language"], "fr")
        self.assertEqual(config["settings"]["brightness_step"], 5)
        self.assertTrue(config["settings"]["offline_cache"])
        self.assertEqual(config["shortcuts"], {})

    def test_info_and_local_actions(self):
        raw = [
            {"id": "temp", "label": "Temperature", "parent": "",
             "kind": "info", "entity_id": "sensor.room", "service": "", "controls": {}},
            {"id": "led", "label": "Toggle LED", "parent": "",
             "kind": "local", "local_command": "led_toggle",
             "entity_id": "", "service": "", "confirm": True},
        ]
        items = validate_config({"items": raw})["items"]
        self.assertEqual(items[0]["kind"], "info")
        self.assertTrue(items[1]["confirm"])
        self.assertEqual(items[1]["local_command"], "led_toggle")

    def test_supported_controls(self):
        item = {"id": "fan", "label": "Fan", "parent": "",
                "entity_id": "fan.office", "service": "fan.toggle",
                "controls": {"fan_percentage": True, "fan_direction": True}}
        result = validate_config({"items": [item]})
        self.assertTrue(result["items"][0]["controls"]["fan_percentage"])
        item["controls"] = {"media_volume": True}
        with self.assertRaises(MenuValidationError):
            validate_config({"items": [item]})

    def test_shortcuts_and_device_preferences(self):
        config = validate_config({
            "items": [],
            "settings": {"language": "en", "font_size": "small",
                         "brightness_step": 10, "direct_edit": True,
                         "oled_contrast": 60, "animation_ms": 160,
                         "encoder_inverted": True, "animations": False,
                         "offline_cache": False},
            "shortcuts": {"double": {"service": "light.toggle",
                                    "entity_id": "light.office", "data": {}}},
        })
        self.assertEqual(config["shortcuts"]["double"]["service"], "light.toggle")
        self.assertEqual(config["settings"]["language"], "en")
        self.assertEqual(config["settings"]["animation_ms"], 160)

    def test_reject_invalid_local_command(self):
        bad = {"id": "cmd", "label": "Command", "kind": "local",
               "local_command": "shell_command", "parent": ""}
        with self.assertRaises(MenuValidationError):
            validate_config({"items": [bad]})


if __name__ == "__main__":
    unittest.main()
