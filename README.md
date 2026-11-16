# HA Menu C3

Home Assistant menu controller for an ESP32-C3 SuperMini, 128×64 SSD1306 OLED, rotary encoder and WS2812B LED. Menus and HA actions are configured in Home Assistant; the firmware handles input and display.

## Install

1. In HACS, add `https://github.com/maelremrem/ha-ESP32-OLED-Menu-Control` as a custom **Integration** repository.
2. Install **HA Menu C3** and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → HA Menu C3**.
4. Enter the exact ESPHome node name (`esphome.name`). Add one integration entry per controller.
5. Open **HA Menu C3** in the sidebar, select a device, edit its menu and save.

Each controller has its **own menu, LED settings and sleep timer**. The device selector switches between them. Existing installations automatically migrate their saved menu from the former single-device storage when the integration first starts after upgrading.

## Firmware

Flash the file [`esphome/ha-menu-c3.yaml`](esphome/ha-menu-c3.yaml) to use the new OLED animation and direct diagnostic reporting. For a second controller, set a different `device_name` substitution at the top of its ESPHome YAML and add that node separately in HA. The ESPHome secrets keep these names:

```yaml
api:
  id: native_api
  encryption:
    key: !secret api_encryption_key

ota:
  - platform: esphome
    password: !secret ota_password
```

The HACS update **does not flash ESPHome**. Install the new integration first, then flash your controller(s).

| Device | ESP32-C3 GPIO |
| --- | --- |
| OLED SDA / SCL | 4 / 5 |
| Encoder CLK / DT | 6 / 7 |
| Encoder switch | 3 |
| WS2812B DIN | 10 |

Use 3.3 V for OLED/encoder and 5 V for the LED, with a common ground. A logic-level shifter for the WS2812B data pin is recommended.

## Controls

- Turn the encoder to navigate, press to select, long-press to go back.
- Submenus always include `< Retour`; `À propos` is fixed at the end of the root menu.
- Menu entries can be reordered with drag-and-drop in Home Assistant. Actions run in HA, not on the ESP32.
- Current HA entity states appear beside menu entries. The header has separate Wi-Fi and HA connection icons.
- A completed service call displays a checkmark drawn in the center; failures display a drawn cross and a short error. Results close after 10 seconds or any encoder input. **A check means Home Assistant accepted the service call**, not that a physical device necessarily reached its target state.
- The RGB LED shows a persistent status color and temporary animations. OLED and LED share a configurable sleep timer.

## Diagnostics

Open **Réglages et état** in the sidebar panel for Wi-Fi RSSI, SSID, IP, uptime, HA connection and last sync. The panel refreshes automatically every 15 seconds. Firmware **0.4.0** sends diagnostic updates directly on integration heartbeat; it also exposes regular ESPHome entities. Previous firmware may require enabling its diagnostics entities in Home Assistant.

The menu and settings are saved by HA. The ESP32 uses RAM for the menu and restores it from HA when connected. There are up to 32 configurable entries and 8 levels. Each device requires a unique `esphome.name`. Sensitive actions such as locks or garages currently execute without an on-screen confirmation.

## Development checks

```bash
python -m unittest discover -s tests -v
node tests/test_panel_drag.js
node tests/test_multi_device.js
node --check custom_components/ha_menu_c3/frontend/ha-menu-panel.js
```

## License

MIT. See [LICENSE](LICENSE).
