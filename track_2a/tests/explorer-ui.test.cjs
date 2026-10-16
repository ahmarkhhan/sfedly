// Offline controller QA. Source content and records are synthetic, never gold.
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

class Element {
  constructor(tag = "div") {
    this.tag = tag; this.children = []; this.listeners = {}; this.attributes = {};
    this.value = ""; this.textContent = ""; this.checked = false; this.open = false;
    this.classList = {toggle() {}};
  }
  get options() { return this.children; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(event, listener) { this.listeners[event] = listener; }
  setAttribute(key, value) { this.attributes[key] = value; }
  getAttribute(key) { return this.attributes[key]; }
  showModal() { this.open = true; }
  close() { this.open = false; this.listeners.close?.(); }
  querySelector(selector) { return this.children.find(c => c.tag === selector); }
  scrollIntoView() {}
}
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return {promise, resolve, reject};
}
function collection(total = 0) {
  return {total, offset:0, limit:30, scope_note:"Synthetic QA", results:[],
    insights:{dossiers:total, documents:total, bodies:total ? 1 : 0, with_answer_text:0,
      with_decision_text:0, practice_dossiers:0, pages_needing_ocr:0},
    facets:{bodies:[], languages:[], topics:[]}};
}
async function controller() {
  const elements = new Map(), requests = [];
  const get = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  let serve = () => collection();
  const context = vm.createContext({
    document:{getElementById:get, createElement:tag => new Element(tag),
      createTextNode:text => ({text, children:[]}), querySelectorAll:() => []},
    Option:class extends Element { constructor(label, value) { super("option"); this.textContent = label; this.value = value; } },
    URLSearchParams, location:{search:""}, history:{replaceState() {}}, window:{addEventListener() {}},
    requestAnimationFrame:fn => fn(),
    fetch:async path => { requests.push(path); const value = await serve(path); return {ok:!value.error, json:async () => value}; },
  });
  vm.runInContext(readFileSync(join(__dirname, "../web/explore.js"), "utf8"), context);
  await new Promise(setImmediate);
  return {get, context, requests, serve(handler) { serve = handler; },
    run(code) { return vm.runInContext(code, context); }};
}

test("an old search cannot overwrite newer results or export filters", async () => {
  const ui = await controller(), pending = deferred();
  ui.serve(path => path.includes("q=old") ? pending.promise : collection(2));
  ui.get("query").value = "old";
  const old = ui.run("search()");
  ui.get("query").value = "new";
  await ui.run("search()");
  pending.resolve(collection(99)); await old;
  assert.equal(ui.get("stat-dossiers").textContent, 2);
  assert.match(ui.get("export-json").href, /q=new/);
  assert.equal(ui.get("export-json").getAttribute("aria-disabled"), "false");
});

test("a failed search clears stale stats and disables prior downloads", async () => {
  const ui = await controller();
  ui.serve(() => collection(4)); await ui.run("search()");
  ui.serve(() => ({error:"Synthetic unavailable source"})); await ui.run("search()");
  assert.equal(ui.get("stat-dossiers").textContent, "—");
  assert.equal(ui.get("export-json").getAttribute("aria-disabled"), "true");
  assert.equal(ui.get("next").disabled, true);
  assert.equal(ui.get("message").textContent, "Synthetic unavailable source");
});

test("changing field mode cancels an in-flight dossier", async () => {
  const ui = await controller(), pending = deferred();
  ui.serve(path => path.includes("/dossiers/") ? pending.promise : collection());
  const opening = ui.run('openDossier("synthetic-id")');
  assert.equal(ui.get("dossier-dialog").open, true);
  ui.get("reviewed-only").checked = true;
  await ui.run("search()");
  pending.resolve({title:"Stale dossier must not render"}); await opening;
  assert.equal(ui.get("dossier-dialog").open, false);
  assert.equal(ui.run("dossier"), null);
});

test("closing evidence cancels late page text and clears its PDF link", async () => {
  const ui = await controller(), pending = deferred();
  ui.serve(() => pending.promise);
  const opening = ui.run('showEvidence({document_id:"synthetic",page:1})');
  ui.get("evidence-dialog").close();
  pending.resolve({document:{pages:[{number:1,text:"Stale source"}]}}); await opening;
  assert.equal(ui.get("source-text").children.length, 0);
  assert.equal(ui.get("source-pdf").hidden, true);
});

test("source offsets count Unicode characters and human image text is never highlighted as a span", async () => {
  const ui = await controller();
  await ui.run('showEvidence({document_id:"synthetic",page:1,start:2,end:6}, {pages:[{number:1,text:"😀 Café"}]})');
  assert.equal(ui.get("source-text").children.find(c => c.tag === "mark").textContent, "Café");
  await ui.run('showEvidence({document_id:"synthetic",page:1,basis:"image",quote:"Human wording",start:0,end:5}, {pages:[{number:1,text:"OCR text"}]})');
  assert.equal(ui.get("source-text").children.length, 0);
  assert.match(ui.get("source-text").textContent, /Human transcription:\nHuman wording/);
});
