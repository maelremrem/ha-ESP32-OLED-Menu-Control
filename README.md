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

**Recommended:** use the [minimal local YAML](esphome/example-minimal.yaml). Its package references the [remote ESPHome configuration](esphome/packages/ha-menu-c3.yaml) from GitHub, so the local file only carries the Wi-Fi credentials, API encryption and OTA password.

For a second controller change `device_name` (unique per ESP32), and optionally `friendly_name`, and add a separate Home Assistant integration instance. **Do not put secrets in a remote package.** For troubleshooting, the standalone [full firmware](esphome/ha-menu-c3.yaml) is also available. Existing firmware continues to work until you flash the new version. Keep these local blocks:

```yaml
api:
  id: native_api
  encryption:
    key: !secret api_encryption_key

ota:
  - platform: esphome
    password: !secret ota_password
```

The HACS update **does not flash ESPHome**. Install the new integration first, then flash your controller(s). A Python integration update normally requires restarting Home Assistant once to load the new code; editing menus and options does not. ESPHome firmware changes still require OTA flashing, though subsequent changes to the GitHub package need no local YAML copy-paste.

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
- Menu entries can be reordered with drag-and-drop. In the tree, use **→** to indent under the previous (action-free) menu entry, or **←** to move a child out of its submenu. The parent picker also supports explicit moves. Actions run in HA, not on the ESP32.
- For supported lights, choose a `light.*` entity (for example `light.tower_leds_bureau`) and enable **Intensité**, **Température** and/or **Couleur** in **Réglages par appui long**. Click **Appliquer les réglages** to save and synchronize. A short click on the normal menu entry still performs its action; a long press opens advanced controls. In those controls, **`< Retour` is the first row**: select it with the encoder and short-click to return. Short-click another row to start/stop editing; long press still returns directly. The ESP32 only shows capabilities supported by the entity. Thermostats and humidifiers support the same navigation.
- Current HA entity states appear beside menu entries. Entries with enabled and supported long-press controls show a **`>` chevron directly after the state**, for example `ON >` / `OFF >`. The header has separate Wi-Fi and HA connection icons.
- A completed service call displays a checkmark drawn in the center; failures display a drawn cross and a short error. Results close after 10 seconds or any encoder input. **A check means Home Assistant accepted the service call**, not that a physical device necessarily reached its target state.
- The OLED displays light brightness as **0–100%** in 5% encoder steps while keeping Home Assistant's 0–255 brightness service values internally.
- The bottom controls legend has been removed from the OLED, restoring **four visible rows** in menus and advanced controls; longer lists remain scrollable.
- On boot, the OLED displays **En attente de Home Assistant** with an animated spinner. After **30 seconds without a completed sync**, it replaces the spinner with a specific error: Wi-Fi unavailable, no Home Assistant API connection, HA Menu C3 integration missing, or menu sync incomplete. The device **continues retrying** and immediately opens the real menu when the integration confirms a successful sync. Encoder input and sleep stay disabled while waiting. No demo entries are loaded; a successfully synced empty menu still shows `À propos`.
- The RGB LED shows a persistent status color and temporary animations. OLED and LED share a configurable sleep timer.

## Diagnostics

Open **Réglages et état** in the sidebar panel for Wi-Fi RSSI, SSID, IP, uptime, HA connection and last sync. The panel refreshes automatically every 15 seconds. Firmware **0.5.6** sends diagnostic updates directly on integration heartbeat; it also exposes regular ESPHome entities. Previous firmware may require enabling its diagnostics entities in Home Assistant.

The menu and settings are saved by HA. The ESP32 uses RAM for the menu and restores it from HA when connected. There are up to 32 configurable entries and 8 levels. Each device requires a unique `esphome.name`. Sensitive actions such as locks or garages currently execute without an on-screen confirmation.

## Development checks

```bash
python -m unittest discover -s tests -v
node tests/test_panel_drag.js
node tests/test_multi_device.js
node tests/test_panel_controls.js
node --check custom_components/ha_menu_c3/frontend/ha-menu-panel.js
```

## License

MIT. See [LICENSE](LICENSE).
