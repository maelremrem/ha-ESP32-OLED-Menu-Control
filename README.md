# HA Menu C3

Home Assistant menu controller for an ESP32-C3 SuperMini, 128×64 SSD1306 OLED, rotary encoder and WS2812B LED. Menus and HA actions are configured in Home Assistant; the firmware handles input and display.

## Install

1. In HACS, add `https://github.com/maelremrem/ha-ESP32-OLED-Menu-Control` as a custom **Integration** repository.
2. Install **HA Menu C3** and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → HA Menu C3**.
4. Enter the exact ESPHome node name (`esphome.name`). Add one integration entry per controller.
5. Open **HA Menu C3** in the sidebar, select a device, edit its menu and save.

Each controller has its **own menu, LED settings and sleep timer**. The device selector switches between them. Existing installations automatically migrate their saved menu from the former single-device storage when the integration first starts after upgrading.

## Version 0.6 — Universal controller

Version **0.6.0** introduces six groups of features plus French/English localization.

1. **Direct controls:** enable *Direct edit on long press* in the settings to start adjusting the first numeric property immediately when a compatible device opens. Other properties are selectable with the encoder. Percent-based values can use steps of 1%, 5%, or 10%.
2. **More Home Assistant devices:** configurable long-press options for covers (position/open/stop/close), fans (percentage/oscillation/direction), and media players (volume/play-pause/next/previous), in addition to lights, climate and humidifiers. Unsupported operations are hidden based on the entity's supported feature flags.
3. **Informational entries:** choose *Information only* for an entity to show live state in the menu and a bigger, two-line readout after pressing. A normal action entry can still display an entity's live state.
4. **Shortcuts:** bind Home Assistant services (plus entity and optional JSON data) to double click, triple click and extended hold. When a multi-click shortcut is configured, single clicks are delayed about 320 ms to distinguish the gesture. Normal 0.7–1.8-second long presses continue to open the control menu; an extended 1.8-second hold triggers its configured shortcut.
5. **Offline cache and confirmation:** the controller saves the last fully synchronized menu to ESP32 NVS flash (up to 3,800 serialized characters). At boot, a cached menu can be browsed without HA, with an **OFFLINE** heading. Only the explicitly supported local actions (*Identify LED*, *Toggle LED*, *OLED sleep*) run without HA; Home Assistant services and advanced controls require a connection. Enable **Require confirmation** on sensitive actions so the OLED asks for approval before executing them. Menu snapshots are saved only after a successful full sync, not on every entity state update. Very large menus may exceed the cache capacity and remain online-only.
6. **Display and encoder personalization:** language, font size (normal/small), OLED contrast, navigation animations and speed, encoder direction, direct-edit behavior, and idle sleep are configurable in the HA Menu C3 panel.

### English support

In **Settings & status → Language**, choose **English** (or **Français**), then click **Save**. The OLED's system labels and the configuration panel follow the selected language. The option is stored per controller.

### Upgrade

Update the HACS integration to **0.6.0**, **restart Home Assistant**, and **OTA flash ESPHome 0.6.0** from the existing GitHub package. The new integration and firmware must be updated together because new ESPHome user actions and menu fields are required.

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
- The OLED displays light brightness as **0–100%** in 5% encoder steps while keeping Home Assistant's 0–255 brightness service values internally. In edit mode, every encoder step immediately sends the new value for **all** available controls: brightness, color temperature, hue, thermostat temperature/mode and humidifier humidity/mode. Light brightness, color temperature and hue use `light.turn_on` with `transition: 0`; climate and humidifier services do not expose the same transition parameter. Rapid adjustments use a latest-value queue per control, so stale settings are skipped while the final requested value is still applied. Actual response time depends on the light and its integration.
- The bottom controls legend has been removed from the OLED, restoring **four visible rows** in menus and advanced controls; longer lists remain scrollable.
- On boot, the OLED displays **En attente de Home Assistant** with an animated spinner. After **30 seconds without a completed sync**, it replaces the spinner with a specific error: Wi-Fi unavailable, no Home Assistant API connection, HA Menu C3 integration missing, or menu sync incomplete. The device **continues retrying** and immediately opens the real menu when the integration confirms a successful sync. Encoder input and sleep stay disabled while waiting. No demo entries are loaded; a successfully synced empty menu still shows `À propos`.
- The RGB LED shows a persistent status color and temporary animations. OLED and LED share a configurable sleep timer.

## Diagnostics

Open **Réglages et état** in the sidebar panel for Wi-Fi RSSI, SSID, IP, uptime, HA connection and last sync. The panel refreshes automatically every 15 seconds. Firmware **0.6.0** sends diagnostic updates directly on integration heartbeat; it also exposes regular ESPHome entities. Previous firmware may require enabling its diagnostics entities in Home Assistant.

The menu and settings are saved by HA. The ESP32 uses RAM for the menu and restores it from HA when connected. There are up to 32 configurable entries and 8 levels. Each device requires a unique `esphome.name`. Sensitive actions such as locks or garages currently execute without an on-screen confirmation.

## Development checks

```bash
python -m unittest discover -s tests -v
node tests/test_panel_drag.js
node tests/test_multi_device.js
node tests/test_panel_controls.js
node tests/test_panel_v06.js
node --check custom_components/ha_menu_c3/frontend/ha-menu-panel.js
```

## License

MIT. See [LICENSE](LICENSE).
