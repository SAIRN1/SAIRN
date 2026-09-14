// tests/sairnbiz_bill_cannot_settle_unmatched.js
//
// Run:  node tests/sairnbiz_bill_cannot_settle_unmatched.js
//
// SAIRNBIZ HAD A ZERO-WAY MATCH AND TWO OF THE THREE DOCUMENTS DID NOT EXIST.
//
//   saveBill()   created a payable from ONE form -- vendor, amount, optional
//                invoice number, one person -- and posted bill_received to the
//                ledger immediately.
//   sbPayBill()  settled it FROM THAT SAME INTERNALLY-CREATED ROW. No second
//                document, no second person, no amount re-entry.
//
// `grep -ciE "purchase order|receiving|packing slip|bill of lading"` returned 0
// against this file. The match was not skipped: there was nothing to match
// against.
//
// WHAT THE GATE DOES AND DOES NOT DO, because the difference is the design. It
// does NOT refuse to RECORD a bill -- a bill that has arrived is a real
// document, and a system that refuses to write it down moves the problem to a
// spreadsheet where there is no control at all. It refuses to let one be
// SETTLED. An unmatched bill is recorded, HELD, and cannot be paid.
//
// THE FUNCTIONS ARE EXTRACTED FROM THE SHIPPED sairnbiz.html AND DRIVEN.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const HTML = fs.readFileSync(process.env.SB_HTML || path.join(ROOT, 'sairnbiz.html'),
                             'utf8').replace(/\r\n/g, '\n');

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; console.log('  ok   ' + label); }

function grab(sig) {
  const start = HTML.indexOf(sig);
  assert.ok(start > 0, 'not found in sairnbiz.html: ' + sig);
  let i = HTML.indexOf('{', start + sig.length - 1), depth = 0, q = null;
  for (; i < HTML.length; i++) {
    const c = HTML[i], p = HTML[i - 1];
    if (q) { if (c === q && p !== '\\') q = null; continue; }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '/' && HTML[i + 1] === '/') { i = HTML.indexOf('\n', i); continue; }
    if (c === '/' && HTML[i + 1] === '*') { i = HTML.indexOf('*/', i) + 1; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (!depth) return HTML.slice(start, i + 1); }
  }
  throw new Error('unterminated: ' + sig);
}

function makeCtx(store, fields) {
  const els = {};
  Object.keys(fields || {}).forEach(k => { els[k] = { value: String(fields[k]) }; });
  const toasts = [];
  const ctx = {
    console: console,
    toasts: toasts,
    localStorage: {
      getItem: k => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); }
    },
    store: store,
    stFails: false,
    toast: (m) => { toasts.push(String(m)); },
    $: id => (id in els ? els[id] : null),
    H: s => String(s),
    fmt: v => '$' + Number(v).toFixed(2),
    sbLocalToday: () => '2026-09-14',
    ld: (k, d) => { try { const v = JSON.parse(store[k]); return v === null ? d : v; } catch (e) { return d; } },
    st: function (k, v) { if (ctx.stFails) return false; store[k] = JSON.stringify(v); return true; },
    rAP: () => {}, rDash: () => {}, closeBillModal: () => {},
    sbNormalizeBills: d => (Array.isArray(d) ? d : []),
    sbGlPost: () => {},
    els: els
  };
  vm.createContext(ctx);
  vm.runInContext('window = this;', ctx);
  // sbMoneyCents was added 2026-09-14 by the independent review that found
  // sbThreeWayMatch deciding money equality in floating point. It has to be
  // loaded BEFORE sbThreeWayMatch, which now calls it -- a missing helper here
  // throws at match time rather than failing an assertion, which is louder but
  // reads like a harness fault rather than a missing dependency.
  for (const sig of ['function sbMoneyCents(v){',
                     'function sbPOAll(){', 'function sbRecvAll(){',
                     'function sbVendorKey(v){', 'function sbPONext(rows,year){',
                     // sbIsVoid joined 2026-09-14 with the void mechanism.
                     // sbMatchPure and sbRecvLog both call it; it threw
                     // ReferenceError here the moment it landed, which is this
                     // hand-listed set doing its job loudly again.
                     'function sbIsVoid(r){',
                     // sbMatchPure is the FUNCTIONAL CORE and must load BEFORE the
                     // shell that calls it (item 92, 2026-09-14). This hand-listed
                     // set is the same shape this repo has recorded going stale
                     // three times -- a sandbox that mirrors declarations by hand
                     // and then throws ReferenceError on a correct file. It threw
                     // here the moment the split landed, which is the list doing
                     // its job loudly rather than a suite going quietly green.
                     'function sbMatchPure(pos,recs,po_num,vendor,amt){',
                     'function sbThreeWayMatch(po_num,vendor,amt){',
                     'function sbPOCreate(){', 'function sbRecvLog(){',
                     'function saveBill(){', 'function sbPayBill(id){']) {
    vm.runInContext(grab(sig), ctx);
  }
  vm.runInContext('var SB_MATCH_TOLERANCE = 0.00;', ctx);
  return ctx;
}

const bills = ctx => JSON.parse(ctx.store.sb_ap || '[]');

console.log('SAIRNbiz: a bill cannot settle unmatched\n');

// ── 1. THE THREE DOCUMENTS AGREE ─────────────────────────────────────────────
console.log('1. all three agree -- the bill is matched and settles');
{
  const store = {};
  let ctx = makeCtx(store, { popvendor: 'Stone World', popdesc: 'Slabs', popamt: '1200' });
  ctx.sbPOCreate();
  const po = JSON.parse(store.sb_po)[0];
  ok(po.po_num === 'PO-2026-001', 'a PO is raised with a real sequence number (' + po.po_num + ')');

  ctx = makeCtx(store, { rcvpo: po.po_num, rcvvendor: 'Stone World', rcvval: '1200' });
  ctx.sbRecvLog();
  ok(JSON.parse(store.sb_recv).length === 1, 'a receipt is logged against it');

  ctx = makeCtx(store, {
    blvendor: 'Stone World', blinv: 'INV-9', bldate: '2026-09-14', bldue: '2026-10-14',
    blamt: '1200', blstatus: 'Open', blpo: po.po_num
  });
  ctx.saveBill();
  const b = bills(ctx)[0];
  ok(b.matched === true, 'the bill records itself as MATCHED');
  ok(b.status === 'Open', '...and is Open, not Held');

  ctx.sbPayBill(b.id);
  ok(bills(ctx)[0].status === 'Paid', 'and it SETTLES');
}

// ── 2. EACH LEG MISSING OR DISAGREEING REFUSES ──────────────────────────────
console.log('\n2. FIRES -- each way the three can fail to agree');
function scenario(setup, billFields) {
  const store = {};
  setup(store);
  const ctx = makeCtx(store, Object.assign({
    blvendor: 'Stone World', blinv: 'INV-9', bldate: '2026-09-14',
    bldue: '2026-10-14', blamt: '1200', blstatus: 'Open'
  }, billFields));
  ctx.saveBill();
  const b = bills(ctx)[0];
  ctx.toasts.length = 0;
  ctx.sbPayBill(b.id);
  return { bill: bills(ctx)[0], stored: b, toasts: ctx.toasts };
}
function withPO(store, amt, vendor) {
  const c = makeCtx(store, { popvendor: vendor || 'Stone World', popdesc: 'Slabs', popamt: String(amt) });
  c.sbPOCreate();
  return JSON.parse(store.sb_po)[0].po_num;
}
function withRecv(store, po_num, val, vendor) {
  const c = makeCtx(store, { rcvpo: po_num, rcvvendor: vendor || 'Stone World', rcvval: String(val) });
  c.sbRecvLog();
}

{
  const r = scenario(() => {}, { blpo: '' });
  ok(r.stored.status === 'Held', 'NO PO NUMBER: the bill is HELD');
  ok(r.bill.status === 'Held', '...and stays Held after a pay attempt');
  ok(/no purchase order number/.test(r.toasts.join(' ')), '...and the refusal says why');
}
{
  const r = scenario(() => {}, { blpo: 'PO-2026-999' });
  ok(r.bill.status === 'Held', 'A PO NUMBER THAT EXISTS NOWHERE: held');
  ok(/no purchase order PO-2026-999 exists/.test(r.toasts.join(' ')), '...named exactly');
}
{
  const store = {};
  const num = withPO(store, 1200);
  const ctx = makeCtx(store, {
    blvendor: 'Stone World', blinv: 'I', bldate: '2026-09-14', bldue: '2026-10-14',
    blamt: '1200', blstatus: 'Open', blpo: num
  });
  ctx.saveBill();
  const b = bills(ctx)[0];
  ok(b.status === 'Held', 'PO EXISTS BUT NOTHING WAS RECEIVED: held');
  ctx.toasts.length = 0;
  ctx.sbPayBill(b.id);
  ok(bills(ctx)[0].status === 'Held', '...and it will not settle');
  ok(/nothing has been recorded as received/.test(ctx.toasts.join(' ')), '...and says so');
}
{
  const store = {};
  const num = withPO(store, 1200);
  withRecv(store, num, 1200);
  const ctx = makeCtx(store, {
    blvendor: 'Stone World', blinv: 'I', bldate: '2026-09-14', bldue: '2026-10-14',
    blamt: '1900', blstatus: 'Open', blpo: num
  });
  ctx.saveBill();
  ok(bills(ctx)[0].status === 'Held', 'BILLED MORE THAN THE PO: held');
  ctx.toasts.length = 0;
  ctx.sbPayBill(bills(ctx)[0].id);
  const t = ctx.toasts.join(' ');
  ok(/billed \$1900\.00 against a PO of \$1200\.00/.test(t),
     '...and BOTH figures are named, with the difference');
}
{
  const store = {};
  const num = withPO(store, 1200);
  withRecv(store, num, 400);          // a partial delivery, billed in full
  const ctx = makeCtx(store, {
    blvendor: 'Stone World', blinv: 'I', bldate: '2026-09-14', bldue: '2026-10-14',
    blamt: '1200', blstatus: 'Open', blpo: num
  });
  ctx.saveBill();
  ctx.toasts.length = 0;
  ctx.sbPayBill(bills(ctx)[0].id);
  ok(bills(ctx)[0].status === 'Held', 'BILLED IN FULL FOR A PARTIAL DELIVERY: held');
  ok(/against \$400\.00 actually received/.test(ctx.toasts.join(' ')),
     '...naming what actually arrived');
}
{
  const store = {};
  const num = withPO(store, 1200, 'Stone World');
  withRecv(store, num, 1200, 'Stone World');
  const ctx = makeCtx(store, {
    blvendor: 'Atlas Marble', blinv: 'I', bldate: '2026-09-14', bldue: '2026-10-14',
    blamt: '1200', blstatus: 'Open', blpo: num
  });
  ctx.saveBill();
  ctx.toasts.length = 0;
  ctx.sbPayBill(bills(ctx)[0].id);
  ok(bills(ctx)[0].status === 'Held', 'A DIFFERENT VENDOR ON THE BILL: held');
  ok(/vendor differs/.test(ctx.toasts.join(' ')), '...and says which two names disagree');
}

// ── 3. A BILL MARKED PAID ON CREATION CANNOT SKIP THE GATE ──────────────────
console.log('\n3. the obvious way round it is closed');
{
  const store = {};
  const ctx = makeCtx(store, {
    blvendor: 'Stone World', blinv: 'I', bldate: '2026-09-14', bldue: '2026-10-14',
    blamt: '1200', blstatus: 'Paid', blpo: ''
  });
  ctx.saveBill();
  const b = bills(ctx)[0];
  ok(b.status === 'Held', 'status=Paid on an UNMATCHED new bill is refused');
  ok(b.bal === 1200, '...and the balance is not zeroed');
  ok(/cannot be marked paid before it matches/.test(ctx.toasts.join(' ')),
     '...and the refusal is explicit');
}

// ── 4. THE STALE-VERDICT ARM, which is why both checks run ──────────────────
console.log('\n4. a matched bill whose documents later vanish still will not settle');
{
  const store = {};
  const num = withPO(store, 1200);
  withRecv(store, num, 1200);
  let ctx = makeCtx(store, {
    blvendor: 'Stone World', blinv: 'I', bldate: '2026-09-14', bldue: '2026-10-14',
    blamt: '1200', blstatus: 'Open', blpo: num
  });
  ctx.saveBill();
  ok(bills(ctx)[0].matched === true, 'the bill was matched when it was entered');
  // Somebody deletes the receipt afterwards.
  store.sb_recv = JSON.stringify([]);
  ctx = makeCtx(store, {});
  ctx.toasts.length = 0;
  ctx.sbPayBill(bills(ctx)[0].id);
  ok(bills(ctx)[0].status !== 'Paid',
     'a STALE matched:true does not settle it once the receipt is gone');
  ok(/nothing has been recorded as received/.test(ctx.toasts.join(' ')),
     '...and the live evaluation is what says so');
}

// ── 5. CONTROLS ─────────────────────────────────────────────────────────────
console.log('\n5. controls -- the gate must not refuse everything');
{
  // Without this the whole suite passes on a gate that is simply always shut,
  // which is the same as an app with no AP.
  const store = {};
  const num = withPO(store, 1200);
  withRecv(store, num, 1200);
  const ctx = makeCtx(store, {
    blvendor: '  stone   world ', blinv: 'I', bldate: '2026-09-14',
    bldue: '2026-10-14', blamt: '1200', blstatus: 'Open', blpo: num
  });
  ctx.saveBill();
  ok(bills(ctx)[0].matched === true,
     'CONTROL: vendor comparison ignores case and spacing, so a real match still passes');
}
{
  // A receipt must name a PO that exists, or the join is decoration.
  const store = {};
  const ctx = makeCtx(store, { rcvpo: 'PO-2026-404', rcvvendor: 'X', rcvval: '5' });
  ctx.sbRecvLog();
  ok(!store.sb_recv, 'a receipt against a PO that does not exist is refused');
  ok(/No purchase order PO-2026-404 exists/.test(ctx.toasts.join(' ')), '...and says so');
}
{
  // The sequence must not reuse a number after a delete -- it is the match key.
  const store = {};
  withPO(store, 100); withPO(store, 200); withPO(store, 300);
  const kept = JSON.parse(store.sb_po).filter(p => p.po_num !== 'PO-2026-002');
  store.sb_po = JSON.stringify(kept);
  const ctx = makeCtx(store, { popvendor: 'V', popdesc: '', popamt: '400' });
  ctx.sbPOCreate();
  const nums = JSON.parse(store.sb_po).map(p => p.po_num);
  ok(new Set(nums).size === nums.length, 'after a delete the next PO number is not a reuse');
  ok(nums.indexOf('PO-2026-004') !== -1, '...it is PO-2026-004, the sequence continuing');
}
{
  // A failed reservation must not issue a number nothing recorded.
  const store = {};
  const ctx = makeCtx(store, { popvendor: 'V', popdesc: '', popamt: '9' });
  ctx.stFails = true;
  ctx.sbPOCreate();
  ok(!store.sb_po, 'a failed write leaves no PO behind');
  ok(/Could not reserve a PO number/.test(ctx.toasts.join(' ')), '...and refuses out loud');
}

// -- 7. MONEY IS COMPARED IN CENTS, NOT IN FLOATS -------------------------
// FOUND 2026-09-14 BY INDEPENDENT REVIEW, and it refused CORRECT bills. The
// comparison was Math.abs(billAmt - recvVal) > SB_MATCH_TOLERANCE with the
// tolerance at exactly 0.00 and recvVal a float sum of the receipts. Two
// partial deliveries of $1,870.93 and $1,957.54 sum to 3828.4700000000003, so
// a $3,828.47 bill against a $3,828.47 PO came out 4.5e-13 apart and was
// refused -- printing "billed $3828.47 against $3828.47 actually received",
// two identical figures and a refusal, with nothing a person could correct.
//
// THE ARMS BELOW GO BOTH WAYS ON PURPOSE. Making the comparison lenient enough
// to settle these would also settle a genuine overbill, so the arm proving a
// correct bill now settles is paired with one proving a wrong one still does
// not.
console.log('\n7. money is compared in cents -- a correct multi-receipt bill settles');
{
  const store = {};
  let ctx = makeCtx(store, { popvendor: 'Mountain Stone', popdesc: 'Slabs', popamt: '3828.47' });
  ctx.sbPOCreate();
  const po = JSON.parse(store.sb_po)[0];

  for (const v of ['1870.93', '1957.54']) {
    ctx = makeCtx(store, { rcvpo: po.po_num, rcvvendor: 'Mountain Stone', rcvval: v });
    ctx.sbRecvLog();
  }
  ok(JSON.parse(store.sb_recv).length === 2, 'two partial deliveries are on file');
  const floatSum = 1870.93 + 1957.54;
  ok(floatSum !== 3828.47,
     'CONTROL: the float sum really is off (' + floatSum + '), so this arm is not vacuous');

  ctx = makeCtx(store, {
    blvendor: 'Mountain Stone', blinv: 'INV-FL', bldate: '2026-09-14', bldue: '2026-10-14',
    blamt: '3828.47', blstatus: 'Open', blpo: po.po_num
  });
  ctx.saveBill();
  const b = bills(ctx).filter(x => x.inv === 'INV-FL')[0];
  ok(b.matched === true,
     'a bill that agrees TO THE CENT with two receipts is MATCHED, not held');
  ok(b.status !== 'Held', '...and is not put on hold');
}
{
  // The other direction, on the same shape: one cent over must still refuse.
  const store = {};
  let ctx = makeCtx(store, { popvendor: 'Mountain Stone', popdesc: 'Slabs', popamt: '3828.47' });
  ctx.sbPOCreate();
  const po = JSON.parse(store.sb_po)[0];
  for (const v of ['1870.93', '1957.54']) {
    ctx = makeCtx(store, { rcvpo: po.po_num, rcvvendor: 'Mountain Stone', rcvval: v });
    ctx.sbRecvLog();
  }
  ctx = makeCtx(store, {
    blvendor: 'Mountain Stone', blinv: 'INV-OVER', bldate: '2026-09-14', bldue: '2026-10-14',
    blamt: '3828.48', blstatus: 'Open', blpo: po.po_num
  });
  ctx.saveBill();
  const b = bills(ctx).filter(x => x.inv === 'INV-OVER')[0];
  ok(b.matched === false, 'ONE CENT over the PO is still refused -- the fix did not widen the gate');
  ok(b.status === 'Held', '...and the bill is held');
  ok(/3828\.48/.test((b.match_reasons || []).join(' ')),
     '...and the refusal still prints the real figures');
}
{
  // The helper itself, at the boundaries that decide everything above.
  const ctx = makeCtx({}, {});
  ok(ctx.sbMoneyCents('1870.93') === 187093, 'a decimal string converts exactly');
  ok(ctx.sbMoneyCents(0.1) + ctx.sbMoneyCents(0.2) === ctx.sbMoneyCents(0.3),
     'the classic float case is exact in cents');
  ok(ctx.sbMoneyCents(undefined) === 0 && ctx.sbMoneyCents('abc') === 0,
     'a non-number is 0, NOT NaN -- NaN compares false against everything, '
     + 'including the tolerance, so it would silently MATCH');
}

// -- 8. TWO PURCHASE ORDERS WITH THE SAME NUMBER ---------------------------
// ADDED 2026-09-14, and tests/sairnbiz_fault_probe.py found the hole rather
// than a reader: planting `if(false)` over sbMatchPure's duplicate refusal left
// this suite GREEN. The refusal existed, was commented at length, and nothing
// anywhere exercised it -- which is exactly what gate 4 exists to surface, and
// the reason a mutation probe is worth more on a DENSE suite than a thin one.
//
// THE STATE IS REAL, NOT CONTRIVED. po_num comes from sb_po_seq, a PER-DEVICE
// counter, so two workstations both raise PO-2026-001; before the sb_po server
// sync neither device could see the other's, and after hydration one device
// holds both. The rows are written into the store directly because that is how
// they ARRIVE -- through hydration, not through sbPOCreate(), which cannot mint
// a collision on one device.
console.log('\n8. two POs with one number is a refusal, not a pick-the-first');
{
  const store = {};
  // Same number, DIFFERENT amounts. A gate that takes [0] validates against
  // whichever is first in insertion order and says nothing about the other.
  store.sb_po = JSON.stringify([
    { id: 'PO-A', po_num: 'PO-2026-001', vendor: 'Mountain Stone', desc: 'Slabs',
      amt: 1000, date: '2026-09-14', status: 'Open' },
    { id: 'PO-B', po_num: 'PO-2026-001', vendor: 'Mountain Stone', desc: 'Slabs',
      amt: 4000, date: '2026-09-14', status: 'Open' }
  ]);
  store.sb_recv = JSON.stringify([
    { id: 'RC-1', po_num: 'PO-2026-001', vendor: 'Mountain Stone', val: 1000,
      date: '2026-09-14' }
  ]);
  const m = makeCtx(store, {}).sbThreeWayMatch('PO-2026-001', 'Mountain Stone', '1000.00');
  ok(m.ok === false,
     'a bill agreeing perfectly with ONE of two same-numbered POs is refused');
  ok(/2 different purchase orders are numbered PO-2026-001/.test(m.reasons.join(' ')),
     '...and the reason NAMES the count so the duplicate can be found: '
     + m.reasons.join(' '));

  // CONTROL: the refusal must come from the DUPLICATE and from nothing else.
  // Without this the arm above passes against a gate that refuses everything.
  const single = { sb_po: JSON.stringify([JSON.parse(store.sb_po)[0]]),
                   sb_recv: store.sb_recv };
  const m2 = makeCtx(single, {}).sbThreeWayMatch('PO-2026-001', 'Mountain Stone', '1000.00');
  ok(m2.ok === true,
     'CONTROL: the SAME bill against a SINGLE PO matches, so the refusal above '
     + 'is the duplicate rather than a gate that refuses everything: '
     + m2.reasons.join(' '));

  // And the documented correction really works: voiding the one raised in
  // error leaves a single live PO and the correct bill matches, while both
  // rows and the reason stay on the record.
  const rows = JSON.parse(store.sb_po);
  rows[1].status = 'Void';
  rows[1].void_reason = 'raised in error on the second workstation';
  const fixed = { sb_po: JSON.stringify(rows), sb_recv: store.sb_recv };
  const m3 = makeCtx(fixed, {}).sbThreeWayMatch('PO-2026-001', 'Mountain Stone', '1000.00');
  ok(m3.ok === true,
     'voiding the duplicate clears the ambiguity and the correct bill matches: '
     + m3.reasons.join(' '));
  ok(JSON.parse(fixed.sb_po).length === 2,
     '...and BOTH rows are still on the record -- a void removes a row from the '
     + 'FIGURES, never from the trail');
}

console.log('\nALL ' + n + ' ASSERTIONS PASS');
