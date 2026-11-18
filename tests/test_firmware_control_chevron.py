"""Verify OLED indicators and live controls are kept in both firmware variants."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = (
    ROOT / "esphome" / "ha-menu-c3.yaml",
    ROOT / "esphome" / "packages" / "ha-menu-c3.yaml",
)


class LongPressChevronTests(unittest.TestCase):
    def test_chevron_follows_live_control_flags(self):
        for path in FIRMWARE:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertIn("std::string &state, bool submenu, bool controls", source)
                self.assertIn("} else if (controls) {", source)
                self.assertIn('it.print(x + 117, y, id(menu_font), ink, ">");', source)
                self.assertIn("id(menu_control_flags)[i] != 0", source)
                self.assertIn('it.print(x + 109, y, id(menu_font), ink, TextAlign::TOP_RIGHT,', source)
                self.assertIn("submenu ? \"\" : id(menu_states)[i]", source)
                self.assertIn("id(menu_control_flags)[slot] =", source)
                self.assertIn("if (id(menu_control_flags)[i] != 0)", source)

    def test_firmware_versions_and_secrets(self):
        for path in FIRMWARE:
            self.assertIn('fw_version: "0.6.3"', path.read_text(encoding="utf-8"))
        standalone = FIRMWARE[0].read_text(encoding="utf-8")
        package = FIRMWARE[1].read_text(encoding="utf-8")
        self.assertIn("key: !secret api_encryption_key", standalone)
        self.assertIn("password: !secret ota_password", standalone)
        self.assertNotIn("!secret", package)


if __name__ == "__main__":
    unittest.main()
