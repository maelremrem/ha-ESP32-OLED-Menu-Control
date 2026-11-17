import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"custom_components"/"ha_menu_c3"))
from controls import attributes_payload, adjustment


def state(value="on", **attrs):
    return SimpleNamespace(state=value, attributes=attrs)


class ControlsTests(unittest.TestCase):
    def test_light_capabilities(self):
        item={"entity_id":"light.salon", "controls":{"brightness": True,"color_temp":True,"color":True}}
        value=state(supported_color_modes=["color_temp","hs"], brightness=123,
                    min_color_temp_kelvin=2700,max_color_temp_kelvin=6000)
        data=attributes_payload(item,value)
        self.assertEqual(data["flags"],7)
        self.assertEqual(data["brightness"],123)
        immediate = adjustment(item,value,"brightness","170")
        self.assertEqual(immediate.domain, "light")
        self.assertEqual(immediate.service, "turn_on")
        self.assertEqual(immediate.data, {
            "entity_id": "light.salon", "brightness": 170, "transition": 0,
        })
        white = adjustment(item,value,"color_temp","2000")
        self.assertEqual(white.data["color_temp_kelvin"], 2700)
        self.assertEqual(white.data["transition"], 0)
        color = adjustment(item,value,"color","45")
        self.assertEqual(color.data["hs_color"], [45,100])
        self.assertEqual(color.data["transition"], 0)

    def test_non_rgb_light(self):
        item={"entity_id":"light.salon","controls":{"color":True,"brightness":True}}
        value=state(supported_color_modes=["brightness"])
        self.assertEqual(attributes_payload(item,value)["flags"],1)
        with self.assertRaises(ValueError): adjustment(item,value,"color","200")

    def test_climate(self):
        item={"entity_id":"climate.room","controls":{"temperature":True,"hvac_mode":True}}
        value=state("heat", supported_features=1,temperature=20.5,min_temp=16,max_temp=30,
                    hvac_modes=["off","heat","auto"])
        self.assertEqual(attributes_payload(item,value)["flags"],24)
        self.assertEqual(adjustment(item,value,"temperature","255").data["temperature"],25.5)
        self.assertEqual(adjustment(item,value,"hvac_mode","heat").data["hvac_mode"],"heat")
        with self.assertRaises(ValueError): adjustment(item,value,"hvac_mode","emergency_heat")

    def test_humidifier(self):
        item={"entity_id":"humidifier.bedroom","controls":{"humidity":True,"humidifier_mode":True}}
        value=state(supported_features=1,humidity=47,min_humidity=30,max_humidity=70,
                    available_modes=["normal","quiet"],mode="normal")
        self.assertEqual(attributes_payload(item,value)["flags"],96)
        self.assertEqual(adjustment(item,value,"humidity","95").data["humidity"],70)
        self.assertEqual(adjustment(item,value,"humidifier_mode","quiet").data["mode"],"quiet")

    def test_unsupported_mode(self):
        item={"entity_id":"humidifier.bedroom","controls":{"humidifier_mode":True}}
        value=state(supported_features=0,available_modes=["quiet"])
        self.assertEqual(attributes_payload(item,value)["flags"],0)
