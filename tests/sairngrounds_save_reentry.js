// tests/sairngrounds_save_reentry.js
//
// REQUIREMENT: a second press of "Create Invoice + Schedule Job" while the
// first press's three server writes are still in flight creates NO second
// invoice, schedule entry or DreamClose record -- and the hold is released
// once those writes answer, are refused, or throw.
//
// Run:  node tests/sairngrounds_save_reentry.js [path-to-sairngrounds.html]
//
// THE DEFECT (cody b64 re-entry sweep, the shape cody b63 fixed in
// sairnmechanical saveDoc). dcCreateInvoiceAndSchedule builds the invoice,
// the schedule entry and the DreamClose record, stores all three, then AWAITS
// all three server writes before it reports. Nothing it reads is reset --
// dcCurrentApproved and dcCurrentQuoteId stay set -- and the button stayed
// live for that whole wait, so a second press billed the same approved
// proposal twice: a second customer invoice and a second job on the schedule.
//
//   G1  two presses while the writes are pending: ONE invoice, ONE schedule
//       entry, ONE DreamClose record, and the second press is told why.
//   G2  once the writes answer, the hold is gone (the next press is not held).
//   G3  after REFUSED writes and after a write that THROWS, it is released.
//
// The function is lifted from the shipped file by brace matching and run in a
// vm with stubs; no browser, no network. An extraction that fails exits 2.
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const H = require('./lib/save_reentry_harness.js');

const FILE = process.argv[2] || path.join(__dirname, '..', 'sairngrounds.html');
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
// declaration, no reference) runs unchanged and G1 measures the fix.
const guardDecl = (html.match(/var grdDcInvoicing\s*=\s*false;/) || [''])[0];
const SRC = guardDecl + '\n' + lift('async function dcCreateInvoiceAndSchedule(){');

const flush = () => new Promise((r) => setImmediate(r));

function world(push) {
  const store = { grd_quotes: JSON.stringify([{ id: 'Q-1', lines: [{ d: 'Patio', a: 4200 }] }]) };
  const ld = (k, d) => (k in store ? JSON.parse(store[k]) : d);
  const els = {};
  const el = (id) => (els[id] = els[id] || { id, value: '', textContent: '', style: {} });
  el('dc-property').value = 'PROP-1';
  const ctx = {
    toasts: [], writes: [],
    JSON, Object, Array, Number, String, Promise, Date,
    $: el, ld,
    st: (k, v) => { store[k] = JSON.stringify(v); return true; },
    bldInv: () => ld('grd_invoices', []), bldSched: () => ld('grd_schedule', []), bldDcRecords: () => ld('grd_dreamclose', []),
    dcCurrentApproved: true, dcCurrentQuoteId: 'Q-1', dcCurrentApprover: 'Owner',
    grdLocalToday: () => '2026-10-29', daysFromNow: () => '2026-11-05', fdate: (x) => x,
    rInv() {}, rSched() {}, rDreamClose() {},
    toast: (m) => ctx.toasts.push(String(m)),
    grdData: (action, resource, rec) => { ctx.writes.push(resource); return push(resource, rec); }
  };
  vm.createContext(ctx); vm.runInContext(SRC, ctx);
  const n = (k) => ld(k, []).length;
  return { ctx, counts: () => ({ inv: n('grd_invoices'), sched: n('grd_schedule'), dc: n('grd_dreamclose') }) };
}

(async () => {
  console.log('1. one invoice + schedule at a time while the writes are pending');
  {
    // EVERY pending write is settled below -- an unsettled one would end the
    // run with the IIFE waiting, and node exits 0 on that.
    const held = [];
    let holding = true;
    const w = world(() => (holding ? new Promise((r) => held.push(r)) : Promise.resolve({ ok: true })));
    const first = w.ctx.dcCreateInvoiceAndSchedule();
    await flush();
    const second = w.ctx.dcCreateInvoiceAndSchedule();   // the double press, writes still pending
    await flush();
    const c = w.counts();
    check('G1 a second press while the writes are pending creates NO second invoice, schedule entry or DreamClose record, and says so',
      c.inv === 1 && c.sched === 1 && c.dc === 1 && w.ctx.toasts.some((t) => /Still creating/.test(t)),
      JSON.stringify({ counts: c, toasts: w.ctx.toasts }));
    holding = false;
    held.forEach((r) => r({ ok: true }));
    await first; await second; await flush();
    const before = w.counts();
    await w.ctx.dcCreateInvoiceAndSchedule();
    const after = w.counts();
    check('G2 once the writes answer, the next press is not held',
      after.inv === before.inv + 1 && !w.ctx.toasts.slice(-1).some((t) => /Still creating/.test(t)),
      JSON.stringify({ before, after, toasts: w.ctx.toasts }));
  }
  console.log('2. the hold is released whichever way the writes end');
  for (const [label, push] of [
    ['REFUSED writes', () => Promise.resolve(null)],
    ['a write that THROWS', (res) => (res === 'grd_schedule' ? Promise.reject(new Error('offline')) : Promise.resolve({ ok: true }))]
  ]) {
    const w = world(push);
    let threw = 0;
    try { await w.ctx.dcCreateInvoiceAndSchedule(); } catch (e) { threw++; }
    try { await w.ctx.dcCreateInvoiceAndSchedule(); } catch (e) { threw++; }
    check('G3 after ' + label + ' the next press is not held: two presses, two invoices',
      w.counts().inv === 2 && !w.ctx.toasts.some((t) => /Still creating/.test(t)),
      JSON.stringify({ threw, counts: w.counts(), toasts: w.ctx.toasts }));
  }
  // 3. FIVE MORE (cody b65). Four quote senders file a draft quote locally,
  // then AWAIT its server write before they say anything, with the source
  // panel unchanged -- a second press filed the same draft quote again under a
  // new Q- id. genEcosystemReport waits on the AI call and then on the report
  // write; a second press during either wait generated and filed a second
  // report. Arms: IZ / BQ / WF / DQ / EA / EB 1-3, meanings in
  // tests/lib/save_reentry_harness.js. Quote senders store BEFORE the write,
  // so a second row is the duplicate too.
  console.log('3. the quote senders and the ecosystem report');
  let seq = 0;
  const L = H.makeLift(html, FILE);
  const quoteWorld = (write, box) => ({
    ld: (k, d) => (k === 'grd_quotes' ? box.rows.slice() : (d || [])),
    st: (k, list) => { if (k === 'grd_quotes') box.rows = list; return true; },
    daysFromNow: () => '2026-11-28', grdData: write, fmt: (n) => '$' + n,
    computeBOQ: () => [{ label: 'Rotor head', qty: 4, unit: 'ea', rate: 30, extended: 120 }],
    dcCurrentDesignText: '- sod the front bed\n- edge with pavers', dcCurrentQuoteId: null
  });
  const quoteSpec = (id, name, decl, fields) => ({
    id, name, fields,
    src: H.optional(html, new RegExp('var ' + decl + '\\s*=\\s*false;')) + '\n' + L('async function ' + name + '(){'),
    given: quoteWorld, rows: (box) => box.rows.length, press: (ctx) => ctx[name](),
    ok: { id: 'x' }, refused: null
  });
  const AI_OK = { json: () => Promise.resolve({ content: [{ text: 'Layer 7: aerate the 9th.' }] }) };
  const AI_REFUSED = { json: () => Promise.resolve({ error: { message: 'rate limited' } }) };
  const ecoSpec = (id, leg) => ({
    id, name: 'genEcosystemReport (' + leg + ' pending)',
    src: H.optional(html, /var grdEcoReporting\s*=\s*false;/) + '\n' + L('async function genEcosystemReport(){'),
    fields: { ecoproperty: 'P-1', 'eco-soil': 'compacted', 'eco-bio': 'herons' },
    given: (write, box) => ({
      PROXY: '/api/claude', APP_ID: 'sairngrounds',
      ld: (k, d) => (d || []), bldIrrZones: () => [], bldWf: () => [], bldInvasive: () => [],
      bldEcoReports: () => box.rows.slice(), st: (k, list) => { if (k === 'grd_ecosystem_reports') box.rows = list; return true; },
      sfFence: (a, b) => b, grdLocalToday: () => '2026-10-29', fdate: (d) => d,
      fetch: leg === 'AI call' ? write : () => Promise.resolve(AI_OK),
      grdData: leg === 'AI call' ? () => Promise.resolve({ id: 'x' }) : write
    }),
    // The report is filed after the AI answers: a row only measures the
    // write-leg wait.
    rows: leg === 'AI call' ? undefined : (box) => box.rows.length,
    press: (ctx) => ctx.genEcosystemReport(),
    ok: leg === 'AI call' ? AI_OK : { id: 'x' }, refused: leg === 'AI call' ? AI_REFUSED : null
  });
  for (const s of [
    quoteSpec('IZ', 'sendIrrZoneToQuote', 'grdIrrQuoting', { izproperty: 'P-1', izname: 'Zone 3', izchecklist: '4 rotors\n1 valve' }),
    quoteSpec('BQ', 'sendBoqToQuote', 'grdBoqQuoting', { boqproperty: 'P-1' }),
    quoteSpec('WF', 'sendWfToQuote', 'grdWfQuoting', { wfproperty: 'P-1', wfname: 'Koi pond', wfchecklist: '1 pump\n2 lights' }),
    quoteSpec('DQ', 'dcCreateQuote', 'grdDcQuoting', { 'dc-property': 'P-1' }),
    ecoSpec('EA', 'AI call'),
    ecoSpec('EB', 'report write')
  ]) {
    await H.drive({ check, id: s.id, name: s.name, mk: H.mkFor(s), ok: s.ok, refused: s.refused });
  }
  // 4. THE GPS WAIT IS A WAIT TOO (cody b65, b64 handoff item 3). gcdPlaceOrder
  // and gcdMarkShotEnd await the device's GPS fix, not the server, so the b64
  // sweep (which looked for a server write) passed them. A second press during
  // the fix sent a second Pro Shop order, or recorded the same shot twice. Here
  // the pending call is cmCaptureGps; arms PO / MS 1-3 as in the harness.
  console.log('4. the caddie GPS handlers: one fix at a time');
  const FIX = { lat: 40.1, lng: -75.2, accuracy_m: 4 };
  const caddie = (write, box) => ({
    gcdActiveRound: () => box.round, gcdCurrentHole: () => box.hole,
    cmCaptureGps: write, gcdSaveRound() {}, gcdHaversineM: () => 142,
    gcdOrderTotal: () => 12, gcdOrders: () => box.rows.slice(),
    st: (k, list) => { if (k === 'grd_cart_orders') box.rows = list; return true; },
    grdData: () => Promise.resolve({ id: 'x' })
  });
  const gpsSpec = (id, name, decl, refill, rows) => ({
    id, name,
    src: H.optional(html, new RegExp('var ' + decl + '\\s*=\\s*false;')) + '\n' + L('async function ' + name + '(){'),
    given: (write, box) => {
      box.round = { id: 'R-1', property_id: 'P-1', player_label: 'Group 4' };
      box.hole = { zone_id: 'Z-9', zone_name: 'Hole 9', shots: [] };
      return caddie(write, box);
    },
    // No `rows` for the harness: the record is made AFTER the fix, so while
    // the fix is pending there is none to count. The count is checked below,
    // once both presses have settled.
    refill, count: rows, press: (ctx) => ctx[name](),
    ok: FIX, refused: null
  });
  for (const s of [
    gpsSpec('PO', 'gcdPlaceOrder', 'gcdOrderPlacing',
      (ctx) => { ctx.gcdOrderLines = [{ name: 'Water', price: 2, qty: 6 }]; }, (box) => box.rows.length),
    gpsSpec('MS', 'gcdMarkShotEnd', 'gcdShotEnding',
      (ctx) => { ctx.gcdShotStart = { lat: 40.0, lng: -75.2, accuracy_m: 3 }; }, (box) => box.hole.shots.length)
  ]) {
    await H.drive({ check, id: s.id, name: s.name, mk: H.mkFor(s), ok: s.ok, refused: s.refused });
    const held = [];
    const box = {};
    const spec = Object.assign({}, s, { given: (write, b) => { Object.assign(box, { b }); return s.given(write, b); } });
    const w = H.mkFor(spec)(() => new Promise((r) => held.push(r)));
    w.refill(); const a = w.press(); await H.flush();
    w.refill(); const b2 = w.press(); await H.flush();
    held.forEach((r) => r(FIX));
    await Promise.allSettled([a, b2]); await H.settle();
    check(s.id + '4 ' + s.name + ': two presses during one fix leave exactly ONE record',
      s.count(box.b) === 1, JSON.stringify({ records: s.count(box.b), fixes: w.writes() }));
  }
  // 5. START DURING A PENDING END (cc b76 F1 on cody b65's 2026-10-29T19:34:54Z
  // record). gcdMarkShotEnd read gcdShotStart AFTER its fix arrived and then
  // nulled it, so a START pressed for the next shot while END's fix was
  // pending became the measured shot's start (0 m), and was then thrown away.
  console.log('5. a START pressed while END\'s fix is pending');
  {
    const TEE = { lat: 40.0, lng: -75.0, accuracy_m: 3 };
    const LANDED = { lat: 40.002, lng: -75.0, accuracy_m: 4 };
    const NEXT = { lat: 40.0021, lng: -75.0, accuracy_m: 3 };
    const src = L('async function gcdMarkShotStart(){') + '\n' +
      H.optional(html, /var gcdShotEnding\s*=\s*false;/) + '\n' + L('async function gcdMarkShotEnd(){');
    const hole = { zone_id: 'Z-9', zone_name: 'Hole 9', shots: [] };
    const pending = [];
    const ctx = H.vmWorld(src, {
      gcdShotStart: TEE, gcdActiveRound: () => ({ id: 'R-1' }), gcdCurrentHole: () => hole,
      cmCaptureGps: () => new Promise((r) => pending.push(r)),
      gcdHaversineM: (a, b) => Math.round(Math.abs(b.lat - a.lat) * 111000),
      gcdSaveRound() {}, rCaddie() {}, gcdAccBadge: () => '', toast() {},
      $: () => ({ innerHTML: '' })
    });
    const end = ctx.gcdMarkShotEnd(); await H.flush();          // END: fix pending
    const start = ctx.gcdMarkShotStart(); await H.flush();      // START for the next shot
    pending[1](NEXT); await start; await H.flush();             // START's fix lands first
    pending[0](LANDED); await end; await H.settle();            // then END's
    const shot = hole.shots[0] || {};
    check('GS1 the shot is measured from the tee it was started at, not from the next start',
      hole.shots.length === 1 && shot.from === TEE && shot.meters > 100, JSON.stringify({ n: hole.shots.length, meters: shot.meters }));
    check('GS2 ...and the next shot\'s start, marked meanwhile, is kept, not thrown away',
      ctx.gcdShotStart === NEXT, JSON.stringify(ctx.gcdShotStart));
  }
  // 6. TWO MORE (cody b69, tools/reentry_hold_check.py). sendDesignToQuote
  // files a draft quote, then AWAITS its write -- rec.quote_id, the guard that
  // refuses a re-send, is set only after it -- so a second press filed a second
  // quote for the same design. grdUploadProgressPhoto waits on the AI call and
  // then on the photo write, and clears grdPhotoB64 only at the end, so a second
  // press during either wait filed a second photo record. Arms SQ / PA / PB 1-3.
  console.log('6. the design-to-quote sender and the progress-photo upload');
  const designSpec = {
    id: 'SQ', name: 'sendDesignToQuote',
    src: H.optional(html, /var grdDesignQuoting\s*=\s*false;/) + '\n' + L('async function sendDesignToQuote(){'),
    given: (write, box) => Object.assign(quoteWorld(write, box), {
      dwid: 'DW-1', DW_TYPE_LABELS: { bed: 'Bed' }, fdate: (d) => d,
      // A fresh read each call, as ld('grd_designs') is: approved, not yet sent.
      grdDesigns: () => [{ id: 'DW-1', property_id: 'P-1', approved: true, approved_by: 'Owner',
        approved_at: '2026-10-29', quote_id: null, elements: [{ type: 'bed', label: 'Front bed' }] }],
      saveDesignRecord: () => Promise.resolve(true)
    }),
    rows: (box) => box.rows.length, press: (ctx) => ctx.sendDesignToQuote(),
    ok: { id: 'x' }, refused: null
  };
  const photoSpec = (id, leg) => ({
    id, name: 'grdUploadProgressPhoto (' + leg + ' pending)',
    src: H.optional(html, /var grdPhotoUploading\s*=\s*false;/) + '\n' + L('async function grdUploadProgressPhoto(){'),
    given: (write, box) => ({
      PROXY: '/api/claude', APP_ID: 'sairngrounds', grdPhotoScheduleId: 'S-1',
      bldSched: () => [], bldGrdProgressPhotos: () => box.rows.slice(),
      st: (k, list) => { if (k === 'grd_progress_photos') box.rows = list; return true; },
      fetch: leg === 'AI call' ? write : () => Promise.resolve(AI_OK),
      grdData: leg === 'AI call' ? () => Promise.resolve({ id: 'x' }) : write
    }),
    // The handler clears the photo when it finishes; a new press has a new one.
    refill: (ctx) => { ctx.grdPhotoB64 = 'aGVsbG8='; },
    // The record is filed after the AI answers: a row only measures the
    // write-leg wait.
    rows: leg === 'AI call' ? undefined : (box) => box.rows.length,
    press: (ctx) => ctx.grdUploadProgressPhoto(),
    ok: leg === 'AI call' ? AI_OK : { id: 'x' }, refused: leg === 'AI call' ? AI_REFUSED : null
  });
  for (const s of [designSpec, photoSpec('PA', 'AI call'), photoSpec('PB', 'photo write')]) {
    await H.drive({ check, id: s.id, name: s.name, mk: H.mkFor(s), ok: s.ok, refused: s.refused });
  }
  finished = true;
  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairngrounds save re-entry: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + e.stack); process.exit(2); });
// A run that ends with an arm still waiting (the IIFE unsettled) exits 0 in
// node with nothing printed. It must read as COULD NOT RUN.
process.on('exit', () => { if (!finished) { console.log('COULD NOT RUN: the run ended before its last arm'); process.exitCode = 2; } });
