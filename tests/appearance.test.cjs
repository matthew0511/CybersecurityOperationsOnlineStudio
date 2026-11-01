const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('src/cyberstudio/web/static/appearance.js','utf8');
function harness(saved,{dark=false,blocked=false}={}) {
  const handlers={},mediaHandlers={},root={dataset:{},style:{}},storage=new Map();
  if(saved!==null)storage.set('studio:theme',saved);
  const media={matches:dark,addEventListener:(type,fn)=>mediaHandlers[type]=fn};
  const context={document:{documentElement:root,querySelectorAll:()=>[],querySelector:()=>null,addEventListener:(type,fn)=>handlers['document:'+type]=fn},localStorage:{getItem:key=>{if(blocked)throw Error('blocked');return storage.get(key)??null;},setItem:(key,value)=>{if(blocked)throw Error('blocked');storage.set(key,value);}},CustomEvent:class {constructor(type,init){this.type=type;this.detail=init.detail;}}};
  context.window={matchMedia:()=>media,dispatchEvent:()=>{},addEventListener:(type,fn)=>handlers[type]=fn};
  vm.runInNewContext(script,context);
  return {api:context.window.StudioAppearance,root,handlers,media,mediaHandlers,storage};
}
test('system default follows operating-system changes; explicit choice stays fixed',()=>{
  const h=harness(null,{dark:true});assert.equal(h.root.dataset.theme,'dark');
  h.media.matches=false;h.mediaHandlers.change();assert.equal(h.root.dataset.theme,'light');
  h.api.set('dark');h.mediaHandlers.change();assert.equal(h.root.dataset.theme,'dark');assert.equal(h.storage.get('studio:theme'),'dark');
  h.api.set('system');assert.equal(h.root.dataset.theme,'light');
});
test('invalid preferences fall back; blocked browser storage does not break switching',()=>{
  const h=harness('invalid',{blocked:true,dark:true});assert.equal(h.api.get(),'system');
  h.api.set('light');assert.equal(h.root.dataset.theme,'light');assert.equal(h.root.style.colorScheme,'light');
});
test('another tab and cleared storage update the current appearance',()=>{
  const h=harness('light',{dark:true});h.handlers.storage({key:'studio:theme',newValue:'dark'});assert.equal(h.root.dataset.theme,'dark');
  h.handlers.storage({key:null,newValue:null});assert.equal(h.api.get(),'system');assert.equal(h.root.dataset.theme,'dark');
});
