const fs = require('node:fs');
const assert = require('node:assert/strict');
const vm = require('node:vm');

const source = fs.readFileSync(__dirname + '/../custom_components/ha_menu_c3/frontend/ha-menu-panel.js', 'utf8');
const ctx = {
  HTMLElement: class {
    attachShadow() {
      this.shadowRoot = {addEventListener() {}};
      return this.shadowRoot;
    }
  },
  customElements: {get(){return undefined;}, define(){}},
  console,
};
vm.createContext(ctx);
vm.runInContext(source + '\nthis.Controller = HAMenuC3Panel;', ctx);

const panel = new ctx.Controller();
const item = {id:'fan', label:'Fan', parent:'', kind:'action', service:'fan.toggle',
  entity_id:'fan.office', controls:{}, data:{}, confirm:false};
panel.status = {config:{items:[item], shortcuts:{}, settings:{language:'en',
  sleep_seconds:30, font_size:'normal', brightness_step:5}}};
panel.selectedId = 'fan';
panel._hass = {states:{
  'fan.office': {state:'on', attributes:{supported_features:7, percentage:50}},
  'cover.office': {state:'open', attributes:{supported_features:15, current_position:70}},
  'media_player.office': {state:'playing', attributes:{supported_features:4|1|16|32}},
}};
assert.match(panel.renderControlOptions(item, false), /fan_percentage/);
assert.match(panel.renderControlOptions(item, false), /fan_oscillate/);
assert.match(panel.renderControlOptions(item, false), /fan_direction/);
item.entity_id='cover.office';
assert.match(panel.renderControlOptions(item, false), /cover_position/);
assert.match(panel.renderControlOptions(item, false), /cover_stop/);
item.entity_id='media_player.office';
assert.match(panel.renderControlOptions(item, false), /media_volume/);
assert.match(panel.renderControlOptions(item, false), /media_next/);

const container = {innerHTML:''};
panel.shadowRoot.querySelector = (selector)=>selector==='#settings' ? container : null;
panel.renderSettings();
assert.match(container.innerHTML,/data-setting="language"/);
assert.match(container.innerHTML,/data-setting="offline_cache"/);
assert.match(container.innerHTML,/data-setting="direct_edit"/);
assert.match(container.innerHTML,/data-shortcut="double"/);
assert.match(container.innerHTML,/data-shortcut="triple"/);
assert.match(container.innerHTML,/data-shortcut="hold"/);

panel.onInput({target:{dataset:{setting:'brightness_step'}, type:'number', value:'10'}});
assert.equal(panel.status.config.settings.brightness_step, 10);
panel.onInput({target:{dataset:{shortcut:'double', shortcutKey:'service'}, value:'light.toggle'}});
assert.equal(panel.status.config.shortcuts.double.service, 'light.toggle');
panel.onInput({target:{dataset:{shortcut:'double', shortcutKey:'entity_id'}, value:'light.office'}});
assert.equal(panel.status.config.shortcuts.double.entity_id, 'light.office');

panel.onInput({target:{dataset:{confirm:true}, checked:true}});
assert.equal(item.confirm,true);

console.log('V0.6 panel controls and settings tests passed');
