"""Guard against ESPHome StringRef ternary compile failures."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    ROOT / "esphome" / "ha-menu-c3.yaml",
    ROOT / "esphome" / "packages" / "ha-menu-c3.yaml",
)


class StringRefCompileTests(unittest.TestCase):
    def test_api_action_kind_does_not_mix_stringref_with_literal(self):
        bad = 'kind == "info" || kind == "local" ? kind : "action"'
        for path in FILES:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn(bad, source)
                self.assertIn('if (kind == "info" || kind == "local")', source)
                self.assertIn('id(menu_kinds)[slot] = kind.c_str();', source)
                self.assertIn('id(menu_kinds)[slot] = "action";', source)
                self.assertIn('fw_version: "0.6.3"', source)

    def test_local_api_ota_secrets_unchanged(self):
        standalone = FILES[0].read_text(encoding="utf-8")
        package = FILES[1].read_text(encoding="utf-8")
        self.assertIn("key: !secret api_encryption_key", standalone)
        self.assertIn("password: !secret ota_password", standalone)
        self.assertNotIn("!secret", package)


if __name__ == "__main__":
    unittest.main()
