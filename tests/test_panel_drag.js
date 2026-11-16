const fs = require('fs');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const source = fs.readFileSync(__dirname+'/../custom_components/ha_menu_c3/frontend/ha-menu-panel.js','utf8');
const ctx = {HTMLElement: class {attachShadow(){this.shadowRoot = {addEventListener(){}};return this.shadowRoot;}}, customElements:{get(){return null;},define(){}}, console};
vm.createContext(ctx);
vm.runInContext(source+'\nthis.Panel = HAMenuC3Panel;', ctx);
const panel = new ctx.Panel();
panel.status = {config:{items:[
  {id:'a',parent:'',label:'A',service:'',data:{}},
  {id:'c',parent:'a',label:'C',service:'light.toggle',data:{}},
  {id:'b',parent:'',label:'B',service:'',data:{}},
  {id:'d',parent:'b',label:'D',service:'',data:{}},
  {id:'e',parent:'',label:'E',service:'light.toggle',data:{}}
]}};
panel.renderTree=()=>{};panel.renderEditor=()=>{};panel.show=()=>{};
assert.equal(panel.moveTreeItem('b','a','before'),true);
assert.deepEqual(Array.from(panel.items, i=>i.id),['b','d','a','c','e']);
assert.equal(panel.moveTreeItem('c','b','inside'),true);
assert.deepEqual(Array.from(panel.items, i=>i.id),['b','d','c','a','e']);
assert.equal(panel.items.find(i=>i.id==='c').parent,'b');
assert.equal(panel.moveTreeItem('b','c','inside'),false,'no cycles');
assert.equal(panel.moveTreeItem('a','e','inside'),false,'cannot drop onto action');
assert.equal(panel.moveTreeItem('d','','root'),true);
assert.deepEqual(Array.from(panel.items, i=>i.id),['b','c','a','e','d']);
assert.equal(panel.items.find(i=>i.id==='d').parent,'');
assert.equal(panel.indentItem('e'),true);
assert.equal(panel.items.find(i=>i.id==='e').parent,'a');
assert.equal(panel.outdentItem('e'),true);
assert.equal(panel.items.find(i=>i.id==='e').parent,'');
assert.equal(panel.outdentItem('e'),false, 'root cannot outdent');
assert.equal(panel.indentItem('b'),false, 'first root cannot indent');
console.log('Drag tree tests passed');
