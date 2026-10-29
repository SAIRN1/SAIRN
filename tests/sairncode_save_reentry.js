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

// ---- section 3: the other 24 add-functions, driven from one table ----------
const SC_TABLE = ['addRevenueEntry', 'addDenialEntry', 'addDenialEventEntry', 'addComplianceItem',
  'addFraudAlert', 'addScrubEntry', 'addScrubRule', 'addHccEntry', 'addDrgEntry', 'addQueryEntry',
  'addEncoderCode', 'addRacEntry', 'addTelehealthEntry', 'addAsaBaseUnit', 'addAnesthesiaEntry',
  'saveSpecialtyCheck', 'addSpecialtyChecklistItem', 'addAuthEntry', 'addAuthRequestEntry', 'addArEntry',
  'addProviderEntry', 'addCredentialScope', 'addDmeRecord', 'addPcTcEntry'];
// The shared hold is lifted when it exists, so the pre-fix file runs unchanged
// and T1 measures the fix. A handler that CALLS the hold while the file has no
// declaration throws ReferenceError, and its arms fail rather than pass.
const SC_HOLD = /var scSavePending\s*=\s*\{\};/.test(html)
  ? html.match(/var scSavePending\s*=\s*\{\};/)[0] + '\n' + lift('function scSaveBusy(key){') + '\n' + lift('async function scHoldWhile(key, write){')
  : '';
const NOT_STUBBED = new Set(['if', 'for', 'while', 'switch', 'catch', 'function', 'return', 'typeof', 'scSaveBusy', 'scHoldWhile']);
function tableWorld(names, push) {
  const src = SC_HOLD + '\n' + names.map((n) => lift('async function ' + n + '(){')).join('\n');
  const store = {};
  const els = {};
  let seq = 0;
  const el = (id) => (els[id] = els[id] || { id, value: String(5 + seq), style: {}, innerHTML: '', checked: false });
  const ctx = {
    toasts: [], writes: [],
    JSON, Object, Array, Number, String, Boolean, Promise, Date, Math, parseFloat, parseInt, isNaN, isFinite,
    document: { getElementById: el, querySelector: () => null, querySelectorAll: () => [] },
    localStorage: { getItem: () => 'emp-1', setItem() {} },
    scLocalToday: () => '2026-10-29', scWriteRefusalText: (f) => f,
    showToast: (m) => ctx.toasts.push(String(m)),
    scData: (action, resource, rec) => { ctx.writes.push(resource); return push(resource, rec); }
  };
  // Every other free call in the lifted source: get<X>() reads store X,
  // save<X>(list) writes it, anything else (render*) is a no-op.
  const declared = new Set([...src.matchAll(/function\s+([A-Za-z_$][\w$]*)/g)].map((m) => m[1]));
  for (const m of src.matchAll(/(^|[^.\w$])([A-Za-z_$][\w$]*)\s*\(/g)) {
    const id = m[2];
    if (id in ctx || declared.has(id) || NOT_STUBBED.has(id)) continue;
    if (/^get[A-Z]/.test(id)) ctx[id] = () => JSON.parse(store[id.slice(3)] || '[]');
    else if (/^save[A-Z]/.test(id)) ctx[id] = (list) => { store[id.slice(4)] = JSON.stringify(list); return true; };
    else ctx[id] = () => {};
  }
  vm.createContext(ctx); vm.runInContext(src, ctx);
  // Fresh values for every press, so a press that is NOT held has what it
  // needs and is never refused as a duplicate of the last one.
  const refill = () => {
    seq++;
    Object.values(els).forEach((e) => { e.value = String(5 + seq); });
    ctx._spcLastAnswer = { specialty: 'cardiology', question: 'q' + seq };
  };
  const press = (n) => ctx[n]();
  const rows = () => Object.values(store).reduce((s, v) => s + JSON.parse(v).length, 0);
  return { ctx, refill, press, rows };
}

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

  // 3. THE OTHER 24 ADD-FUNCTIONS (cody b65). Same template as addClaimEntry:
  // push, store, AWAIT scData, then clear the form. Each is lifted from the
  // shipped file and driven through the same three arms, plus a sync throw.
  //   T1  two presses while the write is pending: ONE row and ONE write, and
  //       the second press is told why.
  //   T2  once the write answers, the next press goes through.
  //   T3  after a refused write, a rejected write and a write that throws
  //       synchronously, the next press is not held.
  //   T4  the hold is per form: a pending write in one panel does not hold
  //       another panel's add.
  console.log('3. the other 24 add-functions, table-driven');
  for (const name of SC_TABLE) {
    {
      const held = [];
      let holding = true;
      const w = tableWorld([name], () => (holding ? new Promise((r) => held.push(r)) : Promise.resolve({ id: 'x' })));
      w.refill();
      const first = w.press(name);
      await flush();
      w.refill();
      const second = w.press(name);
      await flush();
      check('T1 ' + name + ': a second press while the write is pending adds NO second row, and says so',
        w.rows() === 1 && w.ctx.writes.length === 1 && w.ctx.toasts.some((t) => /Still saving/.test(t)),
        JSON.stringify({ rows: w.rows(), writes: w.ctx.writes.length, toasts: w.ctx.toasts }));
      holding = false;
      held.forEach((r) => r({ id: 'x' }));
      await first.catch(() => {}); await second.catch(() => {}); await flush();
      const before = w.rows();
      w.refill();
      await w.press(name);
      check('T2 ' + name + ': once the write answers, the next press goes through',
        w.rows() === before + 1, JSON.stringify({ before, rows: w.rows(), toasts: w.ctx.toasts }));
    }
    for (const [label, push] of [
      ['a REFUSED write', () => Promise.resolve(null)],
      ['a REJECTED write', () => Promise.reject(new Error('offline'))],
      ['a write that THROWS', () => { throw new Error('offline'); }]
    ]) {
      const w = tableWorld([name], push);
      w.refill(); await w.press(name).catch(() => {});
      w.refill(); await w.press(name).catch(() => {});
      check('T3 ' + name + ': after ' + label + ' the next press is not held',
        w.rows() === 2 && !w.ctx.toasts.some((t) => /Still saving/.test(t)),
        JSON.stringify({ rows: w.rows(), toasts: w.ctx.toasts }));
    }
  }
  {
    const held = [];
    const w = tableWorld(['addRevenueEntry', 'addDenialEntry'], (res) => (res === 'sc_revenue' ? new Promise((r) => held.push(r)) : Promise.resolve({ id: 'x' })));
    w.refill();
    const first = w.press('addRevenueEntry');
    await flush();
    w.refill();
    await w.press('addDenialEntry');
    check('T4 a pending revenue write does not hold the denial form',
      w.ctx.writes.filter((r) => r === 'sc_denial').length === 1 && !w.ctx.toasts.some((t) => /Still saving/.test(t)),
      JSON.stringify({ writes: w.ctx.writes, toasts: w.ctx.toasts }));
    held.forEach((r) => r({ id: 'x' }));
    await first.catch(() => {});
  }
  finished = true;
  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairncode save re-entry: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + e.stack); process.exit(2); });
// A run that ends with an arm still waiting (the IIFE unsettled) exits 0 in
// node with nothing printed. It must read as COULD NOT RUN.
process.on('exit', () => { if (!finished) { console.log('COULD NOT RUN: the run ended before its last arm'); process.exitCode = 2; } });
