// Synthetic controller checks for source selection and asynchronous PDF overlays.
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

class Element {
  constructor(tag="div") { this.tag=tag;this.children=[];this.attrs={};this.listeners={};this.hidden=false;this.value="";this.scrollTop=0;this.clientHeight=400;this.classList={toggle(){}}; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children=children; }
  setAttribute(key,value) { this.attrs[key]=value; }
  getAttribute(key) { return this.attrs[key]??null; }
  addEventListener(key,listener) { this.listeners[key]=listener; }
  querySelector(selector) { for(const c of this.children){if(c.tag===selector||c.className?.split(" ").includes(selector.slice(1)))return c;const result=c.querySelector?.(selector);if(result)return result;}return null; }
  getBoundingClientRect() { return {top:20,bottom:40,height:20}; }
  scrollIntoView() {}
}
function deferred(){let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};}
const tick=()=>new Promise(setImmediate);
const region={x:.1,y:.2,width:.3,height:.02};
const geometry=(field="title",revision=0)=>({field,revision,page:1,status:"located",regions:[region]});

async function controller(){
  const elements=new Map(),requests=[];
  const get=id=>{
    for(const root of elements.values()){const walk=n=>n.id===id?n:n.children?.map(walk).find(Boolean);const found=walk(root);if(found)return found;}
    if(!elements.has(id))elements.set(id,new Element());return elements.get(id);
  };
  let serve=async path=>path==="/api/state"?{documents:[],csrf_token:"test"}:geometry();
  const context=vm.createContext({document:{getElementById:get,createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag),createTextNode:text=>({textContent:text}),addEventListener(){}},
    localStorage:{getItem(){return "";}},location:{search:""},URLSearchParams,window:{innerWidth:1200},setTimeout,clearTimeout,requestAnimationFrame:fn=>fn(),
    fetch:async path=>{requests.push(path);return {ok:true,json:()=>serve(path)};}});
  vm.runInContext(readFileSync(join(__dirname,"../web/app.js"),"utf8"),context);
  await tick();
  vm.runInContext(`current={id:"synthetic",revision:0,filename:"Practice.pdf",source:{},document:{pages:[{number:1,text:"First passage"},{number:2,text:"Second passage"}]},fields:Object.fromEntries(Object.keys(labels).map(key=>[key,{review:null,suggestion:{value:key,status:"source_located",provenance:{page:1,start:0,end:13,quote:"First passage"}}}]))};`,context);
  return {get,requests,run:code=>vm.runInContext(code,context),serve:handler=>{serve=handler;}};
}

test("clicking a value selects the original PDF and keeps its passage pinned",async()=>{
  const ui=await controller();ui.run('renderFields();');
  ui.get("field-title").querySelector(".evidence-value").listeners.click();await tick();
  assert.equal(ui.run("view"),"image");assert.equal(ui.run("pinnedEvidence.field"),"title");
  assert.equal(ui.get("page-highlights").querySelector("rect").attrs.x,"0.1");
  assert.match(ui.get("source-evidence-status").textContent,/Unreviewed suggestion/);
});

test("a late response cannot overwrite the newly selected field",async()=>{
  const ui=await controller(),old=deferred();
  ui.serve(path=>path.includes("/title/")?old.promise:geometry("answer_text"));
  ui.run('showEvidence("title",current.fields.title.suggestion.provenance)');
  ui.run('showEvidence("answer_text",current.fields.answer_text.suggestion.provenance)');await tick();
  old.resolve({...geometry(),regions:[{...region,x:.9}]});await tick();
  assert.match(ui.get("source-evidence-title").textContent,/Government answer/);
  assert.equal(ui.get("page-highlights").querySelector("rect").attrs.x,"0.1");
});

test("ending a preview restores the pinned passage and source view",async()=>{
  const ui=await controller();
  ui.run('showEvidence("title",current.fields.title.suggestion.provenance);view="text";previewEvidence("answer_text",{page:2,quote:"Second passage"});restoreEvidence()');await tick();
  assert.equal(ui.run("activeEvidence.field"),"title");assert.equal(ui.run("page"),1);assert.equal(ui.run("view"),"text");
});

test("ending an unpinned preview clears its overlay even if the response arrives later",async()=>{
  const ui=await controller(),pending=deferred();ui.serve(()=>pending.promise);
  ui.run('previewEvidence("title",current.fields.title.suggestion.provenance);restoreEvidence()');
  pending.resolve(geometry());await tick();
  assert.equal(ui.get("source-evidence").hidden,true);assert.equal(ui.get("page-highlights").children.length,0);
});

test("a response for another revision never draws coordinates",async()=>{
  const ui=await controller();ui.serve(()=>geometry("title",4));
  ui.run('showEvidence("title",current.fields.title.suggestion.provenance)');await tick();
  assert.equal(ui.get("page-highlights").children.length,0);assert.match(ui.get("source-evidence-status").textContent,/document changed/);
});

test("unavailable geometry preserves a readable passage and explains the fallback",async()=>{
  const ui=await controller();ui.serve(()=>({...geometry(),status:"unavailable",regions:[],reason:"No region coordinates recorded."}));
  ui.run('showEvidence("title",current.fields.title.suggestion.provenance)');await tick();
  assert.equal(ui.get("source-evidence-quote").textContent,"First passage");assert.match(ui.get("source-evidence-status").textContent,/No region/);
  assert.equal(ui.get("page-highlights").children.length,0);
});

test("clearing evidence and changing documents invalidate pending overlays",async()=>{
  const ui=await controller(),pending=deferred();ui.serve(()=>pending.promise);
  ui.run('showEvidence("title",current.fields.title.suggestion.provenance);resetEvidence();current.id="different";renderSource()');
  pending.resolve(geometry());await tick();
  assert.equal(ui.get("source-evidence").hidden,true);assert.equal(ui.get("page-highlights").children.length,0);
});
