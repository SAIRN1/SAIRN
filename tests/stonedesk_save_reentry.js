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
//   S4  a sale with no slab attached awaits nothing, but the form stays
//       filled until the 2.5 s reset (cody b65, b64 handoff item 3): a second
//       press inside that window records ONE invoice and is told why, and
//       once the reset has run the next sale goes through. This arm said
//       "one invoice per press, exactly as before" until b65 -- it pinned the
//       duplicate as the CONTROL.
//
// The function is lifted from the shipped file by brace matching and run in a
// vm with stubs; no browser, no network. An extraction that fails exits 2.
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const H = require('./lib/save_reentry_harness.js');

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
    window: { posResetForm: () => { ctx.resets++; } }, timers: [], resets: 0,
    document: { getElementById: el },
    posItems: [{ desc: 'Kitchen counter', amt: 3200 }],
    posReservedSlabId: slabId,
    posUpdateTotal: () => 3200, posEsigIsBlank: () => false,
    sdSlabs: [{ id: 'SLAB-9' }],
    sdReserveSlab: (slab, who) => { ctx.reserves++; return reserve(slab, who); },
    invGenNum: () => 'INV-' + (++n), sd_invoices: [], invSaveStore() {},
    sdLocalToday: () => '2026-10-29',
    showToast: (m) => ctx.toasts.push(String(m)),
    setTimeout: (fn) => { ctx.timers.push(fn); return ctx.timers.length; }
  };
  vm.createContext(ctx); vm.runInContext(SRC, ctx);
  // Runs every reset the handler scheduled, as if the 2.5 s had passed.
  const elapse = () => { const t = ctx.timers.splice(0); t.forEach((fn) => fn()); };
  return { ctx, elapse, sale: () => ctx.window.posCompleteSale(), err: () => els['pos-err'] ? els['pos-err'].textContent : '' };
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
    w.elapse();
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
  console.log('3. no slab attached: the reset window');
  {
    const w = world(() => Promise.resolve({ ok: true }), null);
    await w.sale(); await w.sale();
    check('S4 no slab: a second press before the form resets records NO second invoice, and says so',
      w.ctx.reserves === 0 && w.ctx.sd_invoices.length === 1 && /Still completing|already recorded/.test(w.err()),
      JSON.stringify({ reserves: w.ctx.reserves, invoices: w.ctx.sd_invoices.length, err: w.err() }));
    w.elapse();
    await w.sale();
    check('S4b ...and once the reset has run, the next sale is recorded',
      w.ctx.resets === 1 && w.ctx.sd_invoices.length === 2, JSON.stringify({ resets: w.ctx.resets, invoices: w.ctx.sd_invoices.length, err: w.err() }));
  }
  {
    // S4c (cc b76 F2 on cody b65's 2026-10-29T19:34:54Z record): the hold is
    // released by a `finally` inside the reset timer, and no arm pinned it --
    // removing the `finally` left this suite at 17/0. A reset that THROWS must
    // still free the POS for the next sale.
    const w = world(() => Promise.resolve({ ok: true }), null);
    w.ctx.window.posResetForm = () => { w.ctx.resets++; throw new Error('reset failed'); };
    await w.sale();
    try { w.elapse(); } catch (e) { /* the timer's own throw; the hold is the question */ }
    await w.sale();
    check('S4c a reset that THROWS still releases the hold: the next sale is recorded',
      w.ctx.resets === 1 && w.ctx.sd_invoices.length === 2 && !/Still completing/.test(w.err()),
      JSON.stringify({ resets: w.ctx.resets, invoices: w.ctx.sd_invoices.length, err: w.err() }));
  }
  // 4. TWO MORE (cody b65). saveQuote with a slab attached AWAITS the slab
  // reservation before it files the quote, with the slab still attached and
  // the quote number not yet advanced: a second press reserved again for the
  // same client and filed a second quote under the SAME number.
  // sdSlabsImportLegacy pushes each legacy row into real inventory and AWAITS
  // its sync, and only marks the import done after the last one: a second
  // press during that loop imported every legacy slab again. Arms QS / LI 1-3,
  // meanings in tests/lib/save_reentry_harness.js.
  console.log('4. saveQuote (slab attached), the legacy slab import, intake accept, AI quote');
  const L = H.makeLift(html, FILE);
  for (const s of [
    {
      id: 'QS', name: 'saveQuote (slab attached)',
      src: H.optional(html, /var sdQuoteSaving\s*=\s*false;/) + '\n' + L('async function saveQuote() {'),
      fields: { 'client-name': 'Dana Whitfield' },
      given: (write, box) => ({
        lastCalc: { total: 5400, proj: { name: 'Kitchen' }, mat: { name: 'Granite' }, tierKey: 'std' },
        TIERS: { std: { label: 'Standard' } }, currentTier: 'std', currentQuoteNum: 'Q-7', quoteCounter: 8,
        sdSlabs: [{ id: 'SLAB-9' }], SD_HOLD_MINUTES_QUOTE: 30,
        sdReserveSlab: write, quoteHistory: box.rows, st: () => true
      }),
      // The salesperson re-attaches the slab before each press: a filed quote
      // detaches it on purpose.
      refill: (ctx) => { ctx.qbReservedSlabId = 'SLAB-9'; },
      press: (ctx) => ctx.saveQuote(),
      ok: { ok: true, slab: { reservedUntil: '2026-10-30T12:00:00Z' } },
      refused: { ok: false, message: 'That slab is held for Lee.' }
    },
    {
      // Each slab is pushed BEFORE its sync, so a second row is the duplicate.
      id: 'LI', name: 'sdSlabsImportLegacy',
      src: H.optional(html, /var sdSlabImporting\s*=\s*false;/) + '\n' + L('window.sdSlabsImportLegacy=async function(){'),
      given: (write, box) => ({
        legacyRows: () => [{ stone: 'Calacatta', size: '120x60', vendor: 'MSI', location: 'A3' }],
        sdSlabs: box.rows, slabSyncOne: write, localStorage: { setItem() {}, getItem: () => null }
      }),
      rows: (box) => box.rows.length,
      press: (ctx) => ctx.sdSlabsImportLegacy(),
      ok: true, refused: false
    },
    // 5. TWO MORE (cody b69, reentry_hold_check criteria 2026-10-30.cody-b69.4).
    // intakeAccept unshifts a NEW Job ('JOB'+Date.now(), no intakeId check)
    // and then AWAITS the server status write, with the Accept button still
    // rendered: a second press filed a second Job for the same intake (the
    // customer is name-deduped, the job is not). Arms IA 1-3.
    {
      id: 'IA', name: 'intakeAccept',
      src: H.optional(html, /var intakeAccepting\s*=\s*false;/) + '\n' + L('async function intakeAccept(id) {'),
      given: (write, box) => ({
        intakeSubmissions: [{ id: 'I1', client_name: 'Dana Whitfield', project_type: 'kitchen', shape: 'lshape', rough_run_a_ft: 12, notes: '' }],
        sdCustomers: [], sdJobs: box.rows, intakeServerWrite: write, INTAKE_TABLE: 'sd_intake',
        sdLocalToday: () => '2026-10-30'
      }),
      rows: (box) => box.rows.length,
      press: (ctx) => ctx.intakeAccept('I1'),
      ok: true, refused: false
    },
    // sdAIQGenerate AWAITS the extraction call to Claude with every field still
    // filled and the Generate button live: a second press paid for a second
    // pair of AI calls and recorded a second AI quote. `write` is the
    // extraction call (max_tokens 300) only, so one generation is one write;
    // the narrative call answers at once. Arms AQ 1-3.
    {
      id: 'AQ', name: 'sdAIQGenerate',
      src: H.optional(html, /var sdAIQGenerating\s*=\s*false;/) + '\n' + L('window.sdAIQGenerate=async function(){'),
      fields: { 'aiq-cust': 'Dana Whitfield', 'aiq-type': 'kitchen', 'aiq-desc': 'Granite kitchen, about 20 linear feet', 'aiq-tier': 'retail' },
      given: (write, box) => ({
        TIERS: { retail: {} }, PROJECTS: { kitchen: { name: 'Kitchen' } }, MATERIALS: { granite: { name: 'Granite' } },
        currentTier: 'retail', lastCalc: { total: 5400 }, localStorage: { getItem: () => null, setItem() {} },
        sdClaude: (sys, inp, n) => (n === 300 ? write(sys, inp, n) : Promise.resolve('Your quote')),
        // aiqFmtDuration is called inside escHtml(...), which the harness's
        // free-call scan does not see, so without this every completed press
        // fell into the catch and recorded nothing.
        load: () => box.rows, save() {}, aiqFmtDuration: () => '1 second'
      }),
      press: (ctx) => ctx.sdAIQGenerate(),
      ok: '{"project_type":"kitchen","material":"granite","total_linear_feet":20}',
      refused: 'not json'
    }
  ]) {
    await H.drive({ check, id: s.id, name: s.name, mk: H.mkFor(s), ok: s.ok, refused: s.refused });
  }
  finished = true;
  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  stonedesk save re-entry: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + e.stack); process.exit(2); });
// A run that ends with an arm still waiting (the IIFE unsettled) exits 0 in
// node with nothing printed. It must read as COULD NOT RUN.
process.on('exit', () => { if (!finished) { console.log('COULD NOT RUN: the run ended before its last arm'); process.exitCode = 2; } });
