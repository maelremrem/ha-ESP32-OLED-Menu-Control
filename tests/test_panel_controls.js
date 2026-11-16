const fs = require('node:fs');
const assert = require('node:assert/strict');
const vm = require('node:vm');

const source = fs.readFileSync(__dirname + '/../custom_components/ha_menu_c3/frontend/ha-menu-panel.js', 'utf8');
const ctx = {
  HTMLElement: class { attachShadow() { this.shadowRoot = { addEventListener() {} }; return this.shadowRoot; } },
  customElements: { get() { return undefined; }, define() {} },
  console,
};
vm.createContext(ctx);
vm.runInContext(source + '\nthis.Panel = HAMenuC3Panel;', ctx);

const panel = new ctx.Panel();
const item = {
  id: 'bureau', parent: '', label: 'Bureau', service: 'light.toggle',
  entity_id: '', data: {}, controls: {},
};
panel.status = { config: { items: [item] } };
panel.selectedId = 'bureau';
const container = { innerHTML: '' };
panel.shadowRoot.querySelector = (selector) => selector === '#control-options' ? container : null;
panel.renderEntityResults = () => {};
panel.renderTree = () => {};
panel._hass = {
  states: {
    'light.tower_leds_bureau': {
      state: 'on',
      attributes: { supported_color_modes: ['brightness', 'color_temp', 'rgb'] },
    },
  },
};

panel.refreshControlOptions();
assert.match(container.innerHTML, /Sélectionne une lampe/);
panel.onInput({ target: {
  dataset: { edit: 'entity_id', entitySearch: 'true' },
  value: 'light.tower_leds_bureau',
} });
assert.equal(item.entity_id, 'light.tower_leds_bureau');
assert.equal(item.service, 'light.toggle');
assert.match(container.innerHTML, /Intensité \(0–100 %\)/);
assert.match(container.innerHTML, /data-control="brightness"/);
assert.match(container.innerHTML, /data-control="color_temp"/);
assert.match(container.innerHTML, /data-control="color"/);
assert.doesNotMatch(container.innerHTML, /data-control="brightness"[^>]*disabled/);
panel.onChange({ target: { dataset: { control: 'brightness' }, checked: true } });
assert.equal(item.controls.brightness, true);
panel.onInput({ target: { dataset: { control: 'color_temp' }, checked: true } });
assert.equal(item.controls.color_temp, true, 'checkbox input commits even before change event');

panel.hasLoaded = true;
panel.isConnected = true;
panel.hass = { states: {
  'light.tower_leds_bureau': { state: 'on', attributes: { supported_color_modes: ['onoff'] } },
} };
assert.match(container.innerHTML, /Intensité \(0–100 %\)/);
assert.match(container.innerHTML, /indisponible/);

// Frequent HA state updates must not replace the checkbox DOM while editing.
panel.refreshControlOptions();
container.innerHTML = 'SENTINEL';
panel.hass = { states: {
  'light.tower_leds_bureau': { state: 'off', attributes: { supported_color_modes: ['onoff'], brightness: 10 } },
} };
assert.equal(container.innerHTML, 'SENTINEL', 'unchanged capabilities must not rebuild checkboxes');
assert.equal(item.controls.brightness, true);
assert.equal(item.controls.color_temp, true);

panel.onInput({ target: {
  dataset: { edit: 'entity_id', entitySearch: 'true' },
  value: 'light.missing_bureau',
} });
assert.match(container.innerHTML, /Entité introuvable/);

// Restoring the original entity keeps selected options on Save.
item.entity_id = 'light.tower_leds_bureau';
panel.deviceId = 'device-a';
panel.commitEditor = () => true;
panel.render = () => {};
panel.call = async (type, data) => {
  assert.equal(type, 'ha_menu_c3/save');
  assert.equal(data.entry_id, 'device-a');
  assert.equal(data.config.items[0].controls.brightness, true);
  assert.equal(data.config.items[0].controls.color_temp, true);
  return { entry_id: 'device-a', config: data.config, devices: [], sync: 'ok' };
};
(async () => {
  await panel.save();
  assert.equal(item.controls.brightness, true);
  console.log('Panel advanced control tests passed');
})().catch(err => { console.error(err); process.exitCode = 1; });
