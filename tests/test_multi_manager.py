"""Test the integration bridge without requiring a Home Assistant installation."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1] / "custom_components" / "ha_menu_c3"


def stub(name, **kwargs):
    module = types.ModuleType(name)
    for key, val in kwargs.items():
        setattr(module, key, val)
    return module


def identity(fn):
    return fn


class MemoryStore:
    data = {}
    def __init__(self, hass, version, key):
        self.key = key
    async def async_load(self):
        return self.data.get(self.key)
    async def async_save(self, data):
        self.data[self.key] = data


class FakeStates:
    def __init__(self, values):
        self._values = values
    def async_all(self):
        return list(self._values.values())
    def get(self, entity_id):
        return self._values.get(entity_id)


def load_integration():
    modules = {
        "voluptuous": stub("voluptuous", Required=lambda x:x, Optional=lambda x:x),
        "homeassistant": stub("homeassistant"),
        "homeassistant.components": stub("homeassistant.components"),
        "homeassistant.components.frontend": stub("homeassistant.components.frontend", async_remove_panel=lambda *args:None),
        "homeassistant.components.panel_custom": stub("homeassistant.components.panel_custom", async_register_panel=lambda *a,**kw:None),
        "homeassistant.components.websocket_api": stub("homeassistant.components.websocket_api",
           websocket_command=lambda schema:identity, require_admin=identity, async_response=identity,
           async_register_command=lambda *args:None),
        "homeassistant.components.http": stub("homeassistant.components.http", StaticPathConfig=object),
        "homeassistant.core": stub("homeassistant.core", EVENT_HOMEASSISTANT_STARTED="start",
           EVENT_STATE_CHANGED="state", HomeAssistant=object, callback=identity),
        "homeassistant.helpers": stub("homeassistant.helpers"),
        "homeassistant.helpers.storage": stub("homeassistant.helpers.storage", Store=MemoryStore),
        "homeassistant.helpers.event": stub("homeassistant.helpers.event", async_track_time_interval=lambda *args:None),
        "homeassistant.helpers.device_registry": stub("homeassistant.helpers.device_registry", async_get=lambda h:types.SimpleNamespace(devices={})),
        "homeassistant.helpers.entity_registry": stub("homeassistant.helpers.entity_registry", async_get=lambda h:types.SimpleNamespace(entities={})),
    }
    with patch.dict(sys.modules, modules):
        name = "ha_menu_c3"
        spec = importlib.util.spec_from_file_location(name, BASE / "__init__.py", submodule_search_locations=[str(BASE)])
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return mod


class MultiManagerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        MemoryStore.data.clear()
        self.mod = load_integration()
        self.hass = types.SimpleNamespace(states=FakeStates({}), data={})

    async def test_migrate_old_single_menu_only_for_first_node(self):
        cfg = {"items":[{"id":"test","label":"Lampe","parent":"","service":"light.toggle",
                         "entity_id":"light.living","data":{}}], "led":{}}
        MemoryStore.data["ha_menu_c3"] = cfg
        first = self.mod.MenuManager(self.hass, "node-a", "entry-a", True)
        second = self.mod.MenuManager(self.hass, "node-b", "entry-b", False)
        await first.load()
        await second.load()
        self.assertEqual(len(first.config["items"]), 1)
        self.assertEqual(second.config["items"], [])
        self.assertIn("ha_menu_c3_node_a", MemoryStore.data)
        self.assertNotIn("ha_menu_c3_node_b", MemoryStore.data)

    async def test_select_correct_device(self):
        a = self.mod.MenuManager(self.hass, "node-a", "entry-a")
        b = self.mod.MenuManager(self.hass, "node-b", "entry-b")
        self.hass.data[self.mod.DOMAIN] = {"entry-a": a, "entry-b": b}
        self.assertIs(self.mod._get_manager(self.hass, {"entry_id":"entry-b"}), b)
        self.assertIsNone(self.mod._get_manager(self.hass, {"entry_id":"unknown"}))
        self.assertEqual(len(self.mod._response(self.hass, a)["devices"]), 2)

    async def test_diagnostics_event_bound_to_device(self):
        a = self.mod.MenuManager(self.hass, "node-a", "entry-a")
        b = self.mod.MenuManager(self.hass, "node-b", "entry-b")
        event = types.SimpleNamespace(data={"device":"node-b", "wifi":"-61", "ip":"192.168.1.88", "uptime":"321"})
        a.on_diagnostics(event)
        b.on_diagnostics(event)
        self.assertIsNone(a.diagnostics()["wifi"])
        self.assertEqual(b.diagnostics()["wifi"]["state"], "-61")
        self.assertEqual(b.diagnostics()["ip"]["state"], "192.168.1.88")

if __name__ == "__main__":
    unittest.main()
