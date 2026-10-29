// tests/stonedesk_save_reentry.js
//
// REQUIREMENT: a second press of the Mobile POS "Complete Sale" while the
// first press's slab reservation is still waiting on the server records NO
// second sale -- and the hold is released once the reservation answers, is
// refused, or throws.
//
// Run:  node tests/stonedesk_save_reentry.js [path-to-stonedesk.html]
//
// THE DEFECT (cody b64 re-entry sweep, the shape cody b63 fixed in
// sairnmechanical saveDoc). When a slab is attached to the sale,
// posCompleteSale AWAITS sdReserveSlab before it builds the invoice. The
// button stayed live for that whole wait and every field -- customer, lines,
// deposit, signature -- still held its value, so a second press reserved the
// slab again for the same customer (which the server allows) and recorded a
// SECOND signed invoice with its own deposit payment.
//
//   S1  two presses while the reservation is pending: ONE invoice, ONE
//       reservation request, and the second press is told why.
//   S2  once the reservation answers, the hold is gone (the next press is
//       not held).
//   S3  after a REFUSED reservation and one that THROWS, it is released.
//   S4  CONTROL: a sale with no slab attached never waits and records one
//       invoice per press, exactly as before.
//
// The function is lifted from the shipped file by brace matching and run in a
// vm with stubs; no browser, no network. An extraction that fails exits 2.
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = process.argv[2] || path.join(__dirname, '..', 'stonedesk.html');
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
    else if (html[k] === '}' && --depth === 0) return html.slice(i, k + 1) + ';';
  }
  console.log('COULD NOT RUN: unbalanced ' + head); process.exit(2);
}
// The hold's declaration is lifted if it exists, so the pre-fix file (no
// declaration, no reference) runs unchanged and S1 measures the fix.
const guardDecl = (html.match(/var posSaleSaving\s*=\s*false;/) || [''])[0];
const SRC = guardDecl + '\n' + lift('window.posCompleteSale=async function(){');

const flush = () => new Promise((r) => setImmediate(r));

function world(reserve, slabId) {
  const els = {};
  const el = (id) => (els[id] = els[id] || { id, value: '', textContent: '', innerHTML: '', style: {}, toDataURL: () => 'data:sig' });
  el('pos-cust').value = 'Dana Whitfield'; el('pos-method').value = 'Card'; el('pos-deposit').value = '500';
  let n = 0;
  const ctx = {
    toasts: [], reserves: 0,
    JSON, Object, Array, Math, Number, String, Promise, Date, parseFloat,
    window: {},
    document: { getElementById: el },
    posItems: [{ desc: 'Kitchen counter', amt: 3200 }],
    posReservedSlabId: slabId,
    posUpdateTotal: () => 3200, posEsigIsBlank: () => false,
    sdSlabs: [{ id: 'SLAB-9' }],
    sdReserveSlab: (slab, who) => { ctx.reserves++; return reserve(slab, who); },
    invGenNum: () => 'INV-' + (++n), sd_invoices: [], invSaveStore() {},
    sdLocalToday: () => '2026-10-29',
    showToast: (m) => ctx.toasts.push(String(m)),
    setTimeout: () => 0
  };
  vm.createContext(ctx); vm.runInContext(SRC, ctx);
  return { ctx, sale: () => ctx.window.posCompleteSale(), err: () => els['pos-err'] ? els['pos-err'].textContent : '' };
}

(async () => {
  console.log('1. one sale at a time while the slab reservation is pending');
  {
    // EVERY held reservation is settled below -- an unsettled one would end
    // the run with the IIFE waiting, and node exits 0 on that.
    const held = [];
    let holding = true;
    const w = world(() => (holding ? new Promise((r) => held.push(r)) : Promise.resolve({ ok: true })), 'SLAB-9');
    const first = w.sale();
    await flush();
    const second = w.sale();   // the double press, reservation still pending
    await flush();
    check('S1 a second press while the reservation is pending sends NO second reservation, and says so',
      w.ctx.reserves === 1 && /Still completing/.test(w.err()),
      JSON.stringify({ reserves: w.ctx.reserves, err: w.err() }));
    holding = false;
    held.forEach((r) => r({ ok: true }));
    await first; await second; await flush();
    check('S1b ...and exactly ONE invoice is recorded', w.ctx.sd_invoices.length === 1,
      JSON.stringify(w.ctx.sd_invoices.map((i) => i.num)));
    const before = w.ctx.sd_invoices.length;
    await w.sale();
    check('S2 once the reservation answers, the next press is not held',
      w.ctx.sd_invoices.length === before + 1 && !/Still completing/.test(w.err()),
      JSON.stringify({ before, invoices: w.ctx.sd_invoices.length, err: w.err() }));
  }
  console.log('2. the hold is released whichever way the reservation ends');
  for (const [label, reserve] of [
    ['a REFUSED reservation', () => Promise.resolve({ ok: false, message: 'That slab is already reserved for Lee.' })],
    ['a reservation that THROWS', () => Promise.reject(new Error('offline'))]
  ]) {
    const w = world(reserve, 'SLAB-9');
    let threw = 0;
    try { await w.sale(); } catch (e) { threw++; }
    try { await w.sale(); } catch (e) { threw++; }
    check('S3 after ' + label + ' the next press is not held: two presses, two reservation requests, no invoice',
      w.ctx.reserves === 2 && w.ctx.sd_invoices.length === 0 && !/Still completing/.test(w.err()),
      JSON.stringify({ threw, reserves: w.ctx.reserves, err: w.err() }));
  }
  console.log('3. control');
  {
    const w = world(() => Promise.resolve({ ok: true }), null);
    await w.sale(); await w.sale();
    check('S4 CONTROL: with no slab attached nothing is awaited and each press records its invoice, as before',
      w.ctx.reserves === 0 && w.ctx.sd_invoices.length === 2, JSON.stringify({ reserves: w.ctx.reserves, invoices: w.ctx.sd_invoices.length }));
  }
  finished = true;
  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  stonedesk save re-entry: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + e.stack); process.exit(2); });
// A run that ends with an arm still waiting (the IIFE unsettled) exits 0 in
// node with nothing printed. It must read as COULD NOT RUN.
process.on('exit', () => { if (!finished) { console.log('COULD NOT RUN: the run ended before its last arm'); process.exitCode = 2; } });
