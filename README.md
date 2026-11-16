# HA Menu C3 — dynamic OLED menu for Home Assistant

A Home Assistant custom integration for the **ESP32-C3 SuperMini**, a **SSD1306 128×64 0.96-inch OLED**, **KY-040 rotary encoder with push button**, and **WS2812B RGB LED** running ESPHome.

Build an OLED menu from Home Assistant without reflashing the ESP32. Add, remove, rename, reorder and nest menu entries, then associate items with Home Assistant actions, scripts, lights, scenes, etc. Configure the steady RGB status color, with temporary action animations handled by ESPHome.

> **Status:** v0.2.0 integration. Configuration and YAML syntax tests pass; real-device verification is still required for the new V5 features.

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

Use the updated **V5** from [`esphome/ha-menu-c3.yaml`](esphome/ha-menu-c3.yaml). It provides:

- Native ESPHome API commands: `set_menu_item`, `set_menu_count`, `set_base_led`, `play_led_animation`, `action_result`, `set_sleep_timeout`, `set_extension_status`, `extension_heartbeat`.
- `esphome.ha_menu_ready` and `esphome.ha_menu_selected` events.
- Up to 32 menu entries with nested submenus, `< Retour`, encoder filtering and OLED transitions.
- Persistent status RGB and temporary action animations.
- Shared OLED + RGB sleep timer (0 = never), hardware OLED power-off, and a proportional OLED scrollbar.
- ESPHome diagnostic entities: Wi-Fi signal, uptime, IP address, extension connectivity, last menu-sync timestamp.
- ESPHome config entities: `number` for sleep timeout and `button` to identify the device.

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
- **Searchable entity picker:** search by friendly name or entity ID; `switch.*` smart plugs are included, with `homeassistant.toggle` offered for plugs exposed under other domains.
- **Configuration & diagnostics:** set the **shared OLED + LED timeout**, identify the hardware, and view signal, uptime, IP and integration sync/connection states.
- **Sleep:** default 30 seconds; 0 disables sleep. Sleep settings are saved in the integration and synchronized back from the ESPHome number entity when changed there.

The ESPHome V5 firmware keeps the menu in RAM and loads a demo menu on boot. **Home Assistant is the source of truth** and resends the saved menu when the ESPHome node connects.

> **Security:** Be careful with sensitive actions (garage doors, locks, alarms). This version does not require confirmation on the OLED before calling the action.

## Upgrading from V4 / v0.1.0

1. Download/update the HACS integration from this repository (v0.2.0) and **restart Home Assistant**.
2. Copy `esphome/ha-menu-c3.yaml` into the device's ESPHome configuration and flash **V5** once (OTA works). Keep the existing `api_encryption_key` and `ota_password` secrets unchanged.
3. In **HA Menu C3 → Configuration & diagnostics**, set the sleep timeout (seconds). It applies to **both** OLED and RGB LED. `0` leaves both always active.
4. Find the ESPHome device diagnostic entities (they may be hidden by default under the device's diagnostic section): Wi-Fi Signal, Uptime, IP Address, Extension Connected, Extension Last Update. The device also gains a `Sleep Timeout` number and `Identify` button.
5. Verify the extension sync status; the integration requires V5 commands to report successful sync.

The OLED and LED sleep together, while transient identification/notifications can briefly light the LED during sleep. A knob/button interaction wakes the device without triggering the menu action. The displayed "Extension Last Update" means **last successful menu/config sync**, not an available software update in HACS. The extension connection diagnostic uses a 30-second heartbeat with a 90-second timeout.

## Limitations of v0.2.0

- Supports one ESP32-C3 node per configured integration (single config entry).
- A submenu must have at least one child to open on the V5 firmware.
- The menu holds at most 32 entries in total and 8 levels of nesting.
- ESPHome reports accepted command success, not necessarily completion of asynchronous scripts.
- Action result animation times out if the service is still busy after the firmware timeout.
- Browser UI and Home Assistant lifecycle compatibility require device testing before considering the integration stable.
- Diagnostics in the editor look up the default ESPHome entity IDs. If you renamed them, access their values directly in the device's Home Assistant diagnostic entities.

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
esphome/ha-menu-c3.yaml          # Example firmware V5
examples/                        # Example menus and actions
tests/                           # Configuration model unit tests
hacs.json                        # HACS metadata
```

## License

MIT — see [LICENSE](LICENSE).

## V0.3.0 — tree editor and OLED feedback

### Home Assistant editor

- Drag menu entries using the **⠿ handle** to reorder them. Drop at the top/bottom edge of a row to insert before/after, or at its center to move inside an existing submenu. A dedicated drop area moves an entry back to the root.
- Dropping on an action is blocked: clear its action before turning it into a submenu. Circular nesting is rejected. The up/down buttons and parent selector remain available on mobile.
- Save to persist changes and synchronize with the ESP32. Drag-and-drop edits are local until saved.
- Connected entity states are sent on sync and whenever their state changes (`ON`, `OFF`, numeric sensor values, etc.).

### OLED firmware (V0.3.0)

- The header contains a Wi-Fi signal icon and an HA connection icon; both reflect the actual connectivity status.
- Configured entities display their live status on the right of each menu row (for example `ON`, `OFF`, or a sensor reading). Home Assistant supplies the state updates; the OLED is not a network client.
- Running an action shows a progress screen. Once Home Assistant accepts the service call, a large check mark and the message `Commande envoyee` appear. Failed calls show a cross and an error explanation; the screen disappears after **10 seconds**, or immediately on the first encoder rotation or button action. That first input only dismisses the message.
- `A Propos` is always the last item of the root menu and cannot be deleted or moved. It shows firmware version, Wi-Fi status, SSID, IP address, RSSI, HA extension status, last sync and uptime.
- The firmware requires the updated V0.3.0 integration because the `action_result` ESPHome action now includes `message` and the integration calls `set_menu_status` to update entity states. **Update HACS first, then flash the firmware immediately** to avoid an incompatible transition. The HACS update alone does not flash the device.

Connection secrets in the ESPHome example remain `api_encryption_key` and `ota_password`.
