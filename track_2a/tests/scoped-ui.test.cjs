// Offline browser-controller checks. All records are synthetic engineering QA.
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

class Element {
  constructor(tag = "div") {
    this.tag = tag;
    this.children = [];
    this.value = "";
    this.listeners = {};
    this.classList = { toggle() {} };
  }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(event, listener) { this.listeners[event] = listener; }
  querySelectorAll(selector) {
    assert.equal(selector, "input:checked");
    return this.children.flatMap(child => [child, ...child.children])
      .filter(child => child.tag === "input" && child.checked);
  }
}

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function snapshot(id) { return { snapshot_id: id, snapshot: { scope_ids: ["synthetic-scope"] } }; }
function comparison(id) { return { result_id: id, historical_warning: false, result: { rows: [] } }; }
function response(value) { return { ok: true, json: async () => value }; }

async function controller() {
  const elements = new Map(), requests = [];
  const get = id => {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  };
  let serve = path => path === "/api/state" ? { documents: [], csrf_token: "synthetic-token" } : [];
  const context = vm.createContext({
    document: {
      getElementById: get,
      createElement: tag => new Element(tag),
      createTextNode: text => ({ text, children: [] }),
    },
    localStorage: { getItem() { return ""; } },
    fetch: async (path, options) => {
      requests.push({ path, options });
      return response(await serve(path, options));
    },
  });
  vm.runInContext(readFileSync(join(__dirname, "../web/scoped.js"), "utf8"), context);
  // Let the controller's ordinary initial refresh finish.
  await new Promise(setImmediate);
  get("snapshot").value = "synthetic-a";
  get("question").value = "Synthetic question";
  return { get, requests, context, serve(handler) { serve = handler; },
    compare() { return vm.runInContext("compare()", context); },
    change(id, event = "change") { get(id).listeners[event](); },
  };
}

test("changing the snapshot while it loads cancels the old comparison", async () => {
  const ui = await controller(), pending = deferred();
  ui.serve(path => path.startsWith("/api/v2/snapshots/") ? pending.promise : comparison("old"));
  const request = ui.compare();
  ui.get("snapshot").value = "synthetic-b";
  ui.change("snapshot");
  pending.resolve(snapshot("synthetic-a"));
  await request;
  assert.equal(ui.requests.filter(r => r.path === "/api/v2/comparisons").length, 0);
  assert.equal(ui.get("download-comparison").disabled, true);
});

test("changing comparison inputs while a result loads keeps downloads disabled", async () => {
  for (const [id, event] of [["snapshot", "change"], ["columns", "change"], ["question", "input"]]) {
    const ui = await controller(), pending = deferred();
    ui.serve(path => path.startsWith("/api/v2/snapshots/") ? snapshot("synthetic-a") : pending.promise);
    const request = ui.compare();
    await new Promise(setImmediate);
    ui.change(id, event);
    pending.resolve(comparison("outdated"));
    await request;
    assert.equal(ui.get("download-comparison").disabled, true, id);
    assert.equal(ui.get("comparison").children.length, 0, id);
  }
});

test("an older request cannot replace a newer completed comparison", async () => {
  const ui = await controller(), first = deferred(), second = deferred();
  let calls = 0;
  ui.serve(path => path.startsWith("/api/v2/snapshots/") ? snapshot(ui.get("snapshot").value) :
    (++calls === 1 ? first.promise : second.promise));
  const a = ui.compare();
  await new Promise(setImmediate);
  ui.get("snapshot").value = "synthetic-b";
  ui.change("snapshot");
  const b = ui.compare();
  await new Promise(setImmediate);
  second.resolve(comparison("newer"));
  await b;
  first.resolve(comparison("older"));
  await a;
  assert.equal(vm.runInContext("comparisonResult.result_id", ui.context), "newer");
});

test("a failed new comparison clears the preceding downloadable result", async () => {
  const ui = await controller();
  ui.serve(path => path.startsWith("/api/v2/snapshots/") ? snapshot("synthetic-a") : comparison("previous"));
  await ui.compare();
  assert.equal(ui.get("download-comparison").disabled, false);
  ui.serve(() => { throw new Error("Synthetic load failure"); });
  await assert.rejects(ui.compare(), /Synthetic load failure/);
  assert.equal(ui.get("download-comparison").disabled, true);
  assert.equal(ui.get("comparison").children.length, 0);
});
