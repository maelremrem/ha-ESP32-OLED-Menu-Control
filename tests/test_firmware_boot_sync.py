"""Regression checks for the HA sync gate and boot display."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = (
    ROOT / "esphome" / "ha-menu-c3.yaml",
    ROOT / "esphome" / "packages" / "ha-menu-c3.yaml",
)


class BootSyncTests(unittest.TestCase):
    def test_firmware_waits_for_completed_sync(self):
        for path in FIRMWARE:
            with self.subTest(firmware=path.name):
                source = path.read_text(encoding="utf-8")
                boot = source.split("\nesp32:", 1)[0]
                self.assertIn("id(menu_length) = 0;", boot)
                self.assertIn("id(menu_synced) = false;", boot)
                self.assertNotIn("id(menu_ids)[0]", boot)
                self.assertNotIn('id(boot_started)', source)
                self.assertIn("initial_value: 'false'", source)
                self.assertIn("id(menu_synced) = true;", source)
                self.assertIn("if (!id(menu_synced)) {", source)
                self.assertIn('"En attente de"', source)
                self.assertIn('"Home Assistant"', source)
                self.assertIn("if (id(menu_synced) && !id(screen_sleep)", source)
                self.assertEqual(source.count("if (!id(menu_synced)) return;"), 3)

    def test_commit_action_is_after_menu_count(self):
        for path in FIRMWARE:
            with self.subTest(firmware=path.name):
                source = path.read_text(encoding="utf-8")
                action_count = source.index("- action: set_menu_count")
                action_commit = source.index("- action: set_extension_status")
                self.assertLess(action_count, action_commit)
                self.assertLess(
                    source.index("id(extension_last_update).publish_state("),
                    source.index("id(menu_synced) = true;"),
                )

    def test_api_and_ota_secrets_remain_local(self):
        standalone = FIRMWARE[0].read_text(encoding="utf-8")
        package = FIRMWARE[1].read_text(encoding="utf-8")
        self.assertIn("key: !secret api_encryption_key", standalone)
        self.assertIn("password: !secret ota_password", standalone)
        self.assertNotIn("!secret", package)


if __name__ == "__main__":
    unittest.main()
