"""ESPHome must send newest rotary settings rather than replay stale values."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    ROOT / "esphome" / "ha-menu-c3.yaml",
    ROOT / "esphome" / "packages" / "ha-menu-c3.yaml",
)


class RealtimeBrightnessFirmwareTests(unittest.TestCase):
    def test_adjustment_dispatch_is_latest_first(self):
        for path in FILES:
            with self.subTest(firmware=path.name):
                source = path.read_text(encoding="utf-8")
                script = source.split("  - id: send_adjust\n", 1)[1].split("\n  - id: send_selection", 1)[0]
                self.assertIn("mode: restart", script)
                self.assertNotIn("mode: queued", script)
                self.assertNotIn("max_runs:", script)
                self.assertIn("esphome.ha_menu_control_adjust", script)
                self.assertIn("field: \"{{ field_key }}\"", script)
                self.assertIn("value: \"{{ field_value }}\"", script)
                self.assertIn("id(send_adjust).execute(", source)
                self.assertIn('fw_version: "0.6.2"', source)

    def test_secrets_stay_local(self):
        standalone = FILES[0].read_text(encoding="utf-8")
        package = FILES[1].read_text(encoding="utf-8")
        self.assertIn("key: !secret api_encryption_key", standalone)
        self.assertIn("password: !secret ota_password", standalone)
        self.assertNotIn("!secret", package)


if __name__ == "__main__":
    unittest.main()
