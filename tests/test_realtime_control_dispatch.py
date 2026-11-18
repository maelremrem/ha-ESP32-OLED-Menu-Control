"""Regression tests for low-latency encoder adjustments and 1-degree hue."""

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = (
    ROOT / "esphome" / "ha-menu-c3.yaml",
    ROOT / "esphome" / "packages" / "ha-menu-c3.yaml",
)
INTEGRATION = ROOT / "custom_components" / "ha_menu_c3" / "__init__.py"


class RealtimeControlsTests(unittest.TestCase):
    def test_ha_service_call_does_not_wait_for_device(self):
        source = INTEGRATION.read_text(encoding="utf-8")
        tree = ast.parse(source)
        manager = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "MenuManager"
        )
        method = next(
            node for node in manager.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "apply_control"
        )
        service_calls = [
            node for node in ast.walk(method)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "async_call"
        ]
        self.assertEqual(len(service_calls), 1)
        call = service_calls[0]
        kwargs = {keyword.arg: keyword.value for keyword in call.keywords}
        self.assertIn("blocking", kwargs)
        self.assertIsInstance(kwargs["blocking"], ast.Constant)
        self.assertIs(kwargs["blocking"].value, False)
        self.assertIn("self.adjustments.push(item_id, field, value)", source)

    def test_firmware_sends_every_event_in_order(self):
        for path in FIRMWARE:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                script = source.split("  - id: send_adjust\n", 1)[1].split(
                    "\n  - id: send_selection", 1
                )[0]
                self.assertIn("mode: queued", script)
                self.assertIn("max_runs: 64", script)
                self.assertIn("event: esphome.ha_menu_control_adjust", script)
                self.assertIn('field: "{{ field_key }}"', script)
                self.assertIn('value: "{{ field_value }}"', script)
                self.assertIn('fw_version: "0.6.3"', source)

    def test_hue_moves_one_degree_and_wraps_both_ways(self):
        for path in FIRMWARE:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertIn(
                    "id(ctrl_hue) = (id(ctrl_hue) + delta + 360) % 360;",
                    source,
                )
                self.assertNotIn("id(ctrl_hue) + delta * 15", source)
        self.assertEqual((0 - 1 + 360) % 360, 359)
        self.assertEqual((359 + 1 + 360) % 360, 0)
        self.assertEqual((180 + 1 + 360) % 360, 181)


if __name__ == "__main__":
    unittest.main()
