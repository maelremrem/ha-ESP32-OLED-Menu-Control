"""Firmware regression checks for universal controller features."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "esphome" / "ha-menu-c3.yaml",
         ROOT / "esphome" / "packages" / "ha-menu-c3.yaml"]


class V06FirmwareTests(unittest.TestCase):
    def test_firmware_features(self):
        for path in FILES:
            with self.subTest(firmware=path.name):
                source = path.read_text(encoding="utf-8")
                for name in ("set_user_settings", "set_shortcut_config", "set_menu_item",
                             "set_control_flags", "open_controls", "execute_item",
                             "run_local", "dispatch_click", "send_shortcut"):
                    self.assertIn(name, source)
                self.assertIn('fw_version: "0.6.3"', source)
                self.assertIn('const int total = (int)id(ctrl_fields).size() + 1;', source)
                self.assertIn("id(menu_confirm)[slot]", source)
                self.assertIn("id(menu_cached)", source)
                self.assertIn("restore_value: yes", source)
                self.assertEqual(source.count("max_restore_data_length: 240"), 16)
                self.assertIn("id(cached_menu_checksum)", source)
                self.assertIn("crc == id(cached_menu_checksum)", source)
                self.assertNotIn("cached_menu_blob", source)
                self.assertIn('"OFFLINE"', source)
                self.assertIn('"en"', source)
                self.assertIn("id(ui_brightness_step)", source)
                self.assertIn("id(ui_encoder_inverted)", source)
                self.assertIn("id(ui_animation_ms)", source)
                self.assertIn("id(oled).set_contrast", source)

    def test_local_secrets_never_added_to_remote_package(self):
        local = FILES[0].read_text(encoding="utf-8")
        package = FILES[1].read_text(encoding="utf-8")
        self.assertIn("key: !secret api_encryption_key", local)
        self.assertIn("password: !secret ota_password", local)
        self.assertNotIn("!secret", package)
        self.assertEqual(
            local[local.index("\nfont:\n"):local.index("\ninterval:\n")],
            package[package.index("\nfont:\n"):package.index("\ninterval:\n")],
        )


if __name__ == "__main__":
    unittest.main()
