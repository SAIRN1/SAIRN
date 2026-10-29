// tests/sairnbuild_cost_forecast_writer.js
//
// REQUIREMENT: a cost line's `forecast` (estimated cost at completion) can be
//   ENTERED, EDITED and CLEARED through the cost modal, because the WIP
//   schedule divides by it (forecastFor(), sairnbuild.html) and nothing wrote it.
//
// Run:  node tests/sairnbuild_cost_forecast_writer.js
//
// ── THE GAP (fourth b64 audit leftover, closed fourth b68) ─────────────────
// forecastFor() reads `c.forecast` and falls back to `budget` per line, and
// the WIP card says "% Complete = cost to date / estimated cost at completion
// -- the revised forecast, not the original budget". But saveCost() wrote
// budget, committed and actual only, so every job's "forecast" was its budget
// and the stale-forecast warning ("re-forecast the affected cost lines") asked
// for something the app gave no way to do.
//
// WRITTEN BEFORE THE FIX and run against the unfixed app: arms 1-4 failed.
// Arm 5 is the CONTROL: a line saved with the box blank has NO forecast, so
// forecastFor() still falls back to budget exactly as before.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const src = fs.readFileSync(path.resolve(__dirname, '..', 'sairnbuild.html'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
// The app's own functions, lifted and RUN. Each is a column-0 `function`
// whose body closes at a column-0 `}`.
function lift(name) {
  const at = src.indexOf('\nfunction ' + name + '(');
  assert.notStrictEqual(at, -1, 'function ' + name + ' not found in sairnbuild.html');
  // A one-line declaration (`function $(s){...}`) closes on its own line;
  // reading on to the next column-0 `}` would run whatever top-level code
  // sits between the two.
  const first = src.slice(at + 1, src.indexOf('\n', at + 1));
  if (/\}\s*$/.test(first)) return first;
  const end = src.indexOf('\n}', at + 1);
  return src.slice(at + 1, end + 2);
}

const els = {};
function el(id) {
  if (!els[id]) els[id] = { value: '', classList: { add() {}, remove() {} } };
  return els[id];
}
let store = [];
const ctx = vm.createContext({
  console: console,
  document: { getElementById: el },
  ceid: null,
  jobs: () => [{ id: 'J1' }],
  costs: () => store,
  st: (k, v) => { store = v; return true; },
  fillJobSelects() {}, rCost() {}, rJobs() {}, rDash() {}, toast() {}
});
['$', 'closeCostModal', 'openCostModal', 'editCost', 'saveCost', 'forecastFor', 'hasForecastFor']
  .forEach((f) => vm.runInContext(lift(f), ctx));

function fill(v) {
  el('cm-job').value = 'J1'; el('cm-kind').value = 'labour'; el('cm-code').value = '01-Labour';
  el('cm-vendor').value = ''; el('cm-budget').value = '1000'; el('cm-committed').value = '0';
  el('cm-actual').value = '400'; el('cm-forecast').value = v;
}

console.log('SAIRNBUILD -- the cost modal writes the forecast the WIP schedule divides by');

test('1. the modal HAS a forecast input', () => {
  assert.ok(/<input id="cm-forecast"/.test(src), 'no #cm-forecast input in the cost modal');
});

test('2. a new line saved with a forecast stores it, and forecastFor() uses it', () => {
  store = []; ctx.openCostModal(); fill('1500'); ctx.saveCost();
  assert.strictEqual(store.length, 1);
  assert.strictEqual(store[0].forecast, 1500, 'forecast stored as ' + JSON.stringify(store[0].forecast));
  assert.strictEqual(ctx.forecastFor('J1'), 1500);
  assert.strictEqual(ctx.hasForecastFor('J1'), true);
});

test('3. editing a line shows its forecast, and a changed figure is saved', () => {
  ctx.editCost(store[0].id);
  assert.strictEqual(String(el('cm-forecast').value), '1500', 'edit did not load the forecast');
  el('cm-forecast').value = '1800'; ctx.saveCost();
  assert.strictEqual(store[0].forecast, 1800);
});

test('4. clearing the box CLEARS the forecast -- the carry-forward must not resurrect it', () => {
  ctx.editCost(store[0].id); el('cm-forecast').value = ''; ctx.saveCost();
  assert.strictEqual(store[0].forecast, null, 'forecast after clearing: ' + JSON.stringify(store[0].forecast));
  assert.strictEqual(ctx.forecastFor('J1'), 1000, 'a cleared forecast must fall back to budget');
  assert.strictEqual(ctx.hasForecastFor('J1'), false);
});

test('5. CONTROL -- a line saved with the box blank has no forecast; budget stands in as before', () => {
  store = []; ctx.openCostModal(); fill(''); ctx.saveCost();
  assert.ok(store[0].forecast === undefined || store[0].forecast === null);
  assert.strictEqual(ctx.forecastFor('J1'), 1000);
  assert.strictEqual(ctx.hasForecastFor('J1'), false);
});

test('6. a typed $0 forecast is kept as 0, not read as blank', () => {
  store = []; ctx.openCostModal(); fill('0'); ctx.saveCost();
  assert.strictEqual(store[0].forecast, 0);
  assert.strictEqual(ctx.hasForecastFor('J1'), true);
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
