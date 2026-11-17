"""Regression tests for the initial Home Assistant sync error screen."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = (
    ROOT / "esphome" / "ha-menu-c3.yaml",
    ROOT / "esphome" / "packages" / "ha-menu-c3.yaml",
)


class StartupDiagnosticsTests(unittest.TestCase):
    def test_boot_timer_and_timeout(self):
        for path in FIRMWARE:
            with self.subTest(firmware=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertIn("id(sync_wait_started) = millis();", source)
                self.assertIn("id(menu_synced) = false;", source)
                self.assertIn("initial_value: '0'", source)
                self.assertIn("(uint32_t)(now - id(sync_wait_started)) >= 30000U", source)
                self.assertIn("if (!id(menu_synced) && !id(menu_cached)) {", source)
                self.assertIn("id(menu_synced) = true;", source)

    def test_connection_error_reasons(self):
        for path in FIRMWARE:
            with self.subTest(firmware=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertIn("!id(wifi_node).is_connected()", source)
                self.assertIn("!id(native_api).is_connected_with_state_subscription()", source)
                self.assertIn("id(last_extension_seen) == 0", source)
                self.assertIn('"Wi-Fi indisponible"', source)
                self.assertIn('"HA non connecte"', source)
                self.assertIn('"Integration absente"', source)
                self.assertIn('"Menu non recu"', source)

    def test_secrets_remain_local(self):
        standalone = FIRMWARE[0].read_text(encoding="utf-8")
        package = FIRMWARE[1].read_text(encoding="utf-8")
        self.assertIn("key: !secret api_encryption_key", standalone)
        self.assertIn("password: !secret ota_password", standalone)
        self.assertNotIn("!secret", package)


if __name__ == "__main__":
    unittest.main()
