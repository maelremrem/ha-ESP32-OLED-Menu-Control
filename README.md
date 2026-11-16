# HA Menu C3 — dynamic OLED menu for Home Assistant

A Home Assistant custom integration for the **ESP32-C3 SuperMini**, a **SSD1306 128×64 0.96-inch OLED**, **KY-040 rotary encoder with push button**, and **WS2812B RGB LED** running ESPHome.

Build an OLED menu from Home Assistant without reflashing the ESP32. Add, remove, rename, reorder and nest menu entries, then associate items with Home Assistant actions, scripts, lights, scenes, etc. Configure the steady RGB status color, with temporary action animations handled by ESPHome.

> **Status:** Early v0.1.0 integration. Menu validation has automated tests; the Home Assistant UI and firmware pairing still need real-device testing.

## Installation with HACS (custom repository)

1. Install HACS in Home Assistant if it is not installed yet.
2. Open **HACS → three-dot menu → Custom repositories**.
3. Paste `https://github.com/maelremrem/ha-ESP32-OLED-Menu-Control` and choose **Integration**.
4. Find **HA Menu C3** in HACS and download it.
5. **Restart Home Assistant**.
6. In **Settings → Devices & services → Add integration**, search **HA Menu C3**.
7. Enter the **ESPHome node name** (`ha-menu-c3`, not the friendly name).
8. Open **HA Menu C3** from the sidebar, edit items, and click **Save**.

The integration is installed at `custom_components/ha_menu_c3/`. The sample ESPHome YAML is **not** installed by HACS; it is in `esphome/ha-menu-c3.yaml` as reference firmware.

## Required ESPHome firmware

Use the working **V4** from [`esphome/ha-menu-c3.yaml`](esphome/ha-menu-c3.yaml). It provides:

- Native ESPHome API commands: `set_menu_item`, `set_menu_count`, `set_base_led`, `play_led_animation`, `action_result`.
- `esphome.ha_menu_ready` and `esphome.ha_menu_selected` events.
- Up to 32 menu entries with nested submenus, `< Retour`, encoder filtering and OLED transitions.
- Persistent status RGB and temporary action animations.

Keep your existing ESPHome secrets names:

```yaml
api:
  id: native_api
  encryption:
    key: !secret api_encryption_key

ota:
  - platform: esphome
    password: !secret ota_password
```

This repository contains **references to** secrets, not their values. Adjust the Wi-Fi secrets in your own ESPHome configuration.

### Wiring

| Peripheral | ESP32-C3 pin |
| --- | --- |
| SSD1306 SDA | GPIO4 |
| SSD1306 SCL | GPIO5 |
| Encoder CLK | GPIO6 |
| Encoder DT | GPIO7 |
| Encoder button | GPIO3 |
| WS2812B DIN | GPIO10 |

Power the OLED and encoder from 3.3 V, the WS2812B from 5 V and connect grounds. A 3.3 V-to-5 V logic-level shifter for LED DIN is recommended.

## Using the menu editor

- **+ Entry / + Submenu:** add an item at the root.
- **+ Add to this menu:** add a child to the selected submenu.
- **Move up/down:** reorder entries on the same menu level.
- **Action:** select a preset or enter a Home Assistant action like `light.toggle` with `entity_id` and optional JSON data.
- **RGB status:** select a tracked HA entity and on/off RGB values.
- **Save:** persist the configuration in Home Assistant and attempt immediate sync to ESPHome.
- **Sync:** resend the menu to the device.
- **Identify:** trigger the purple identifying LED animation.

The ESPHome V4 firmware keeps the menu in RAM and loads a demo menu on boot. **Home Assistant is the source of truth** and resends the saved menu when the ESPHome node connects.

> **Security:** Be careful with sensitive actions (garage doors, locks, alarms). This version does not require confirmation on the OLED before calling the action.

## Limitations of v0.1.0

- Supports one ESP32-C3 node per configured integration (single config entry).
- A submenu must have at least one child to open on the V4 firmware.
- The menu holds at most 32 entries in total and 8 levels of nesting.
- ESPHome reports accepted command success, not necessarily completion of asynchronous scripts.
- Action result animation times out if the service is still busy after the firmware timeout.
- Browser UI and Home Assistant lifecycle compatibility require device testing before considering the integration stable.

## Troubleshooting

If syncing fails, verify the ESPHome node is online and its action services exist under **Developer tools → Actions**. The expected names are `esphome.ha_menu_c3_set_menu_item` and `esphome.ha_menu_c3_set_menu_count`. Check Home Assistant logs for `ha_menu_c3`, and ensure ESPHome is allowed to raise Home Assistant events.

## Local checks

```bash
python -m unittest discover -s tests -v
python -m compileall -q custom_components/ha_menu_c3
node --check custom_components/ha_menu_c3/frontend/ha-menu-panel.js
```

## Files

```text
custom_components/ha_menu_c3/   # HACS installs this folder only
esphome/ha-menu-c3.yaml          # Example firmware V4
examples/                        # Example menus and actions
tests/                           # Configuration model unit tests
hacs.json                        # HACS metadata
```

## License

MIT — see [LICENSE](LICENSE).
