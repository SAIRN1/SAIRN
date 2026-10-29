// tests/sairncode_save_reentry.js
//
// REQUIREMENT: a second press of "Add Claim" while the first press's server
// write is still in flight adds NO second claim -- and the hold is released
// once that write answers, is refused, or throws.
//
// Run:  node tests/sairncode_save_reentry.js [path-to-sairncode.html]
//
// THE DEFECT (cody b64 re-entry sweep, the shape cody b63 fixed in
// sairnmechanical saveDoc). addClaimEntry pushes the claim, stores it, then
// AWAITS scData before it clears the form. The button stayed live for that
// whole wait and the form still held every value, so a second press added the
// same claim -- same Claim ID, same amount -- as a second row with a second
// id, and synced it. A duplicated claim is a duplicated billed amount.
//
//   C1  two presses while the write is pending: ONE claim, and the second
//       press is told why.
//   C2  once the write answers, the next press goes through.
//   C3  after a REFUSED write and after a write that THROWS, it is released.
//
// The function is lifted from the shipped file by brace matching and run in a
// vm with stubs; no browser, no network. An extraction that fails exits 2.
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = process.argv[2] || path.join(__dirname, '..', 'sairncode.html');
const html = fs.readFileSync(FILE, 'utf8').replace(/\r\n/g, '\n');

let pass = 0, fail = 0, finished = false;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + String(detail).slice(0, 400) : '')); }
}
function lift(head) {
  const i = html.indexOf(head);
  if (i < 0 || html.indexOf(head, i + 1) !== -1) {
    console.log('COULD NOT RUN: "' + head + '" found ' + (i < 0 ? 0 : 'more than one') + ' time(s) in ' + FILE);
    process.exit(2);
  }
  let k = html.indexOf('{', i), depth = 0;
  for (; k < html.length; k++) {
    if (html[k] === '{') depth++;
    else if (html[k] === '}' && --depth === 0) return html.slice(i, k + 1);
  }
  console.log('COULD NOT RUN: unbalanced ' + head); process.exit(2);
}
// The hold's declaration is lifted if it exists, so the pre-fix file (no
// declaration, no reference) runs unchanged and C1 measures the fix.
const guardDecl = (html.match(/var scClaimSaving\s*=\s*false;/) || [''])[0];
const SRC = guardDecl + '\n' + lift('async function addClaimEntry(){');

const flush = () => new Promise((r) => setImmediate(r));

function world(push) {
  const store = { sc_claims: '[]' };
  const els = {};
  const el = (id) => (els[id] = els[id] || { id, value: '' });
  el('clm-add-id').value = 'CLM-778'; el('clm-add-patient').value = 'Pat Doe';
  el('clm-add-payer').value = 'Aetna'; el('clm-add-amount').value = '1840.50';
  el('clm-add-status').value = 'Submitted'; el('clm-add-date').value = '2026-10-29';
  const ctx = {
    toasts: [],
    JSON, Object, Array, Number, String, Promise, Date, parseFloat, isNaN, isFinite,
    document: { getElementById: el },
    getClaimEntries: () => JSON.parse(store.sc_claims),
    saveClaimEntries: (list) => { store.sc_claims = JSON.stringify(list); return true; },
    renderClaims() {}, renderDashboard() {},
    scLocalToday: () => '2026-10-29', scWriteRefusalText: (f) => f,
    showToast: (m) => ctx.toasts.push(String(m)),
    scData: (action, resource, rec) => push(resource, rec)
  };
  vm.createContext(ctx); vm.runInContext(SRC, ctx);
  // The form is cleared after each save; refill it so a press that is NOT
  // held has the values it needs to add a row.
  const refill = () => { el('clm-add-id').value = 'CLM-778'; el('clm-add-patient').value = 'Pat Doe'; el('clm-add-amount').value = '1840.50'; };
  return { ctx, refill, rows: () => JSON.parse(store.sc_claims) };
}

(async () => {
  console.log('1. one claim at a time while the write is pending');
  {
    // EVERY pending write is settled below -- an unsettled one would end the
    // run with the IIFE waiting, and node exits 0 on that.
    const held = [];
    let holding = true;
    const w = world(() => (holding ? new Promise((r) => held.push(r)) : Promise.resolve({ id: 'x' })));
    const first = w.ctx.addClaimEntry();
    await flush();
    const second = w.ctx.addClaimEntry();   // the double press, write still pending
    await flush();
    check('C1 a second press while the write is pending adds NO second claim, and says so',
      w.rows().length === 1 && w.ctx.toasts.some((t) => /Still adding/.test(t)),
      JSON.stringify({ rows: w.rows().length, toasts: w.ctx.toasts }));
    holding = false;
    held.forEach((r) => r({ id: 'x' }));
    await first; await second; await flush();
    const before = w.rows().length;
    w.refill();
    await w.ctx.addClaimEntry();
    check('C2 once the write answers, the next press goes through: one more claim',
      w.rows().length === before + 1, JSON.stringify({ before, rows: w.rows().length, toasts: w.ctx.toasts }));
  }
  console.log('2. the hold is released whichever way the write ends');
  for (const [label, push] of [
    ['a REFUSED write', () => Promise.resolve(null)],
    ['a write that THROWS', () => Promise.reject(new Error('offline'))]
  ]) {
    const w = world(push);
    let threw = 0;
    try { await w.ctx.addClaimEntry(); } catch (e) { threw++; }
    w.refill();
    try { await w.ctx.addClaimEntry(); } catch (e) { threw++; }
    check('C3 after ' + label + ' the next press is not held: two presses, two claims',
      w.rows().length === 2 && !w.ctx.toasts.some((t) => /Still adding/.test(t)),
      JSON.stringify({ threw, rows: w.rows().length, toasts: w.ctx.toasts }));
  }
  finished = true;
  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairncode save re-entry: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + e.stack); process.exit(2); });
// A run that ends with an arm still waiting (the IIFE unsettled) exits 0 in
// node with nothing printed. It must read as COULD NOT RUN.
process.on('exit', () => { if (!finished) { console.log('COULD NOT RUN: the run ended before its last arm'); process.exitCode = 2; } });
