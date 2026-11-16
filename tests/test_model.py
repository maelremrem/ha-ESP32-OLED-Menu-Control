"""Run: python -m unittest discover -s tests -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "ha_menu_c3"))
from model import MenuValidationError, validate_config  # noqa: E402


def item(identifier, parent="", service="light.toggle"):
    return {"id": identifier, "parent": parent, "label": identifier,
            "service": service, "entity_id": "light.test", "data": {}}


class MenuValidationTests(unittest.TestCase):
    def test_valid_nested_order(self):
        result = validate_config({"items": [item("child", "folder"), item("other"), item("folder", "", "")], "led": {}})
        self.assertEqual([i["id"] for i in result["items"]], ["other", "folder", "child"])

    def test_duplicate(self):
        with self.assertRaisesRegex(MenuValidationError, "dupliqué"):
            validate_config({"items": [item("x"), item("x")]})

    def test_parent_missing(self):
        with self.assertRaisesRegex(MenuValidationError, "introuvable"):
            validate_config({"items": [item("x", "wrong")]})

    def test_cycle(self):
        with self.assertRaises(MenuValidationError):
            validate_config({"items": [item("x", "y"), item("y", "x")]})

    def test_max_items(self):
        with self.assertRaisesRegex(MenuValidationError, "32"):
            validate_config({"items": [item(f"i{i}") for i in range(33)]})

    def test_utf8_limit(self):
        one = item("long")
        one["label"] = "é" * 33
        with self.assertRaisesRegex(MenuValidationError, "64"):
            validate_config({"items": [one]})

    def test_led_invalid(self):
        with self.assertRaisesRegex(MenuValidationError, "Couleur"):
            validate_config({"items": [], "led": {"on": [0, 999, 0]}})

    def test_submenu_depth(self):
        items=[item("x0")]
        for i in range(1,10):
            items.append(item(f"x{i}", f"x{i-1}"))
        with self.assertRaisesRegex(MenuValidationError, "8 niveaux"):
            validate_config({"items":items})

    def test_default_sleep_setting(self):
        cfg = validate_config({"items": []})
        self.assertEqual(cfg["settings"]["sleep_seconds"], 30)

    def test_disable_sleep(self):
        cfg = validate_config({"items": [], "settings": {"sleep_seconds": 0}})
        self.assertEqual(cfg["settings"]["sleep_seconds"], 0)

    def test_max_sleep(self):
        cfg = validate_config({"items": [], "settings": {"sleep_seconds": 3600}})
        self.assertEqual(cfg["settings"]["sleep_seconds"], 3600)

    def test_bad_sleep_values(self):
        for value in [-1, 3601, 3.5, True, "30", None]:
            with self.subTest(value=value), self.assertRaisesRegex(MenuValidationError, "Veille"):
                validate_config({"items": [], "settings": {"sleep_seconds": value}})

    def test_json_payload(self):
        one=item("x")
        one["data"]={"brightness_pct":50}
        self.assertEqual(validate_config({"items":[one]})["items"][0]["data"]["brightness_pct"],50)


if __name__ == "__main__": unittest.main()
