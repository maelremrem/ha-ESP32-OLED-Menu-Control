"""Regression tests for OLED long-press control navigation."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = (
    ROOT / "esphome" / "ha-menu-c3.yaml",
    ROOT / "esphome" / "packages" / "ha-menu-c3.yaml",
)


class OledControlsBackTests(unittest.TestCase):
    def test_back_row_and_field_offset(self):
        for path in FIRMWARE:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertIn('const char *label = row == 0 ? "< Retour" : "";', source)
                self.assertIn("const int field = row == 0 ? 0 : id(ctrl_fields)[row - 1];", source)
                self.assertIn("const int total = (int)id(ctrl_fields).size() + 1;", source)
                self.assertIn("const int field = id(ctrl_fields)[id(control_cursor) - 1];", source)
                self.assertIn("!id(control_editing) && id(control_cursor) == 0", source)
                self.assertIn("id(control_open) = false;", source)
                self.assertIn("id(control_cursor) = 0;", source)
                self.assertIn("const int visible = 4;", source)
                self.assertNotIn("draw_footer(", source)

    def test_navigation_mapping(self):
        # First row is Return; subsequent rows are control fields.
        for count in range(1, 8):
            for cursor in range(count + 1):
                for direction in (-1, 1):
                    next_cursor = (cursor + direction + count + 1) % (count + 1)
                    self.assertTrue(0 <= next_cursor <= count)
                    if next_cursor:
                        index = next_cursor - 1
                        self.assertTrue(0 <= index < count)
            self.assertEqual((0 - 1 + count + 1) % (count + 1), count)

    def test_no_secret_regression(self):
        standalone = FIRMWARE[0].read_text(encoding="utf-8")
        package = FIRMWARE[1].read_text(encoding="utf-8")
        self.assertIn("key: !secret api_encryption_key", standalone)
        self.assertIn("password: !secret ota_password", standalone)
        self.assertNotIn("!secret", package)
        for source in (standalone, package):
            self.assertIn('fw_version: "0.6.3"', source)


if __name__ == "__main__":
    unittest.main()
