// api/_lib/roofing-supplier-match.test.js
// Run: node api/_lib/roofing-supplier-match.test.js
//
// SAIRNroofing B6 -- the only genuinely open item on the 2026-09-02 re-derived
// status list. Re-verified absent before building: `supplier` and `vendor`
// each appear ZERO times in sairnroofing.html, and the single `receiving` hit
// is inside a patent-claim comment.
//
// The assertion that carries the most weight:
//
//   NO RECEIPT RECORDED IS `receipt_unknown`, NEVER `short_received`. Nobody
//   scanning the delivery is a different fact from the delivery not arriving,
//   and only one of them is the supplier's problem. Reporting the first as the
//   second sends a contractor to argue about a truck that did arrive.
//
// And the second: DISCREPANCIES ARE NEVER NETTED. Over-invoiced on one line
// and short on another is two problems, not zero.

'use strict';
const assert = require('assert');
const m = require('./roofing-supplier-match');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

const order = (lines, o) => Object.assign({ doc_type: 'order', po_number: 'PO-1', supplier: 'ABC Supply', lines: lines }, o || {});
const receipt = (lines) => ({ doc_type: 'receipt', po_number: 'PO-1', lines: lines });
const invoice = (lines) => ({ doc_type: 'invoice', po_number: 'PO-1', lines: lines });
const codes = (r, key) => {
  const l = r.lines.filter(x => x.key === key)[0];
  return l ? l.findings.map(f => f.code).sort() : ['(no such line)'];
};

const SHINGLE = { item_code: 'SH-30', description: 'Architectural shingle', qty_ordered: 100, unit_price: 32 };

// ---------------------------------------------------------------------------
section('THE ONE THAT MATTERS: unrecorded is not short');

test('no receipt document at all -> receipt_unknown, NEVER short_received', () => {
  const r = m.matchOrder([order([SHINGLE])]);
  assert.deepStrictEqual(codes(r, 'c:sh-30').filter(c => c !== 'unbilled'), ['receipt_unknown']);
  assert.ok(!codes(r, 'c:sh-30').includes('short_received'));
});

test('...and the reason says so, so nobody phones the supplier over it', () => {
  const r = m.matchOrder([order([SHINGLE])]);
  const f = r.lines[0].findings.filter(x => x.code === 'receipt_unknown')[0];
  assert.match(f.detail, /not evidence the material did not arrive/);
});

test('receipts exist but none names this line -> still unknown, not short', () => {
  const r = m.matchOrder([
    order([SHINGLE, { item_code: 'NAIL-1', description: 'Coil nails', qty_ordered: 20, unit_price: 40 }]),
    receipt([{ item_code: 'NAIL-1', qty_received: 20 }])
  ]);
  assert.ok(codes(r, 'c:sh-30').includes('receipt_unknown'));
  assert.ok(!codes(r, 'c:sh-30').includes('short_received'));
});

test('a RECORDED short IS short -- the distinction cuts both ways', () => {
  const r = m.matchOrder([order([SHINGLE]), receipt([{ item_code: 'SH-30', qty_received: 80 }])]);
  assert.ok(codes(r, 'c:sh-30').includes('short_received'));
  assert.ok(!codes(r, 'c:sh-30').includes('receipt_unknown'));
  const f = r.lines[0].findings.filter(x => x.code === 'short_received')[0];
  assert.strictEqual(f.variance, -20);
});

test('a recorded ZERO received is short, not unknown -- somebody checked', () => {
  const r = m.matchOrder([order([SHINGLE]), receipt([{ item_code: 'SH-30', qty_received: 0 }])]);
  assert.ok(codes(r, 'c:sh-30').includes('short_received'));
  assert.ok(!codes(r, 'c:sh-30').includes('receipt_unknown'));
});

test('an EMPTY quantity string is unknown, not a recorded zero', () => {
  // Number('') is 0. A blank field must not become "we received none".
  const r = m.matchOrder([order([SHINGLE]), receipt([{ item_code: 'SH-30', qty_received: '' }])]);
  assert.ok(!codes(r, 'c:sh-30').includes('short_received'));
});

test('an invoice against a line with no recorded receipt is NOT over_invoiced', () => {
  // There is nothing to compare it to. It stands unverified, which is true.
  const r = m.matchOrder([order([SHINGLE]), invoice([{ item_code: 'SH-30', qty_invoiced: 100, unit_price: 32 }])]);
  assert.ok(!codes(r, 'c:sh-30').includes('over_invoiced_qty'));
  assert.ok(codes(r, 'c:sh-30').includes('receipt_unknown'));
});

// ---------------------------------------------------------------------------
section('the findings that cost money');

test('invoiced more than received is over_invoiced_qty, with the amount', () => {
  const r = m.matchOrder([
    order([SHINGLE]),
    receipt([{ item_code: 'SH-30', qty_received: 90 }]),
    invoice([{ item_code: 'SH-30', qty_invoiced: 100, unit_price: 32 }])
  ]);
  const f = r.lines[0].findings.filter(x => x.code === 'over_invoiced_qty')[0];
  assert.ok(f, 'over-invoicing was not flagged');
  assert.strictEqual(f.variance, 10);
});

test('invoiced but never ordered is flagged, and that is the expensive one', () => {
  const r = m.matchOrder([
    order([SHINGLE]),
    invoice([{ item_code: 'MYSTERY-9', description: 'Ridge vent', qty_invoiced: 5, unit_price: 60 }])
  ]);
  assert.ok(codes(r, 'c:mystery-9').includes('not_ordered'));
});

test('price is compared PER UNIT, so a price rise cannot hide behind a qty change', () => {
  const r = m.matchOrder([
    order([SHINGLE]),                                        // 100 @ 32 = 3200
    receipt([{ item_code: 'SH-30', qty_received: 50 }]),
    invoice([{ item_code: 'SH-30', qty_invoiced: 50, unit_price: 40 }])   // 50 @ 40 = 2000
  ]);
  // Extended totals would show LESS billed than ordered and look fine.
  const f = r.lines[0].findings.filter(x => x.code === 'price_variance')[0];
  assert.ok(f, 'a 25% unit price rise was missed because the total went down');
  assert.ok(Math.abs(f.variance - 8) < 1e-9);
});

test('a missing unit price is price_unknown, not a zero-variance pass', () => {
  const r = m.matchOrder([
    order([{ item_code: 'SH-30', qty_ordered: 100 }]),
    invoice([{ item_code: 'SH-30', qty_invoiced: 100, unit_price: 32 }])
  ]);
  assert.ok(codes(r, 'c:sh-30').includes('price_unknown'));
  assert.ok(!codes(r, 'c:sh-30').includes('price_variance'));
});

test('ordered with no invoice yet is unbilled -- a normal state, still visible', () => {
  const r = m.matchOrder([order([SHINGLE]), receipt([{ item_code: 'SH-30', qty_received: 100 }])]);
  assert.ok(codes(r, 'c:sh-30').includes('unbilled'));
});

// ---------------------------------------------------------------------------
section('NEVER NETTED');

test('over on one line and short on another is TWO problems, not zero', () => {
  const r = m.matchOrder([
    order([SHINGLE, { item_code: 'NAIL-1', description: 'Coil nails', qty_ordered: 100, unit_price: 32 }]),
    receipt([{ item_code: 'SH-30', qty_received: 90 }, { item_code: 'NAIL-1', qty_received: 100 }]),
    invoice([{ item_code: 'SH-30', qty_invoiced: 100, unit_price: 32 }, { item_code: 'NAIL-1', qty_invoiced: 90, unit_price: 32 }])
  ]);
  assert.strictEqual(r.counts.over_invoiced_qty, 1);
  assert.strictEqual(r.counts.short_received, 1);
  // And there is no single netted variance anywhere in the result.
  assert.ok(!('variance' in r) && !('net_variance' in r) && !('total_variance' in r));
});

test('the result carries no approve / hold / pay verdict', () => {
  const r = m.matchOrder([order([SHINGLE])]);
  ['approved', 'approve', 'pay', 'hold', 'recommendation'].forEach(function (k) {
    assert.ok(!(k in r), 'the engine issued a payment verdict: ' + k);
  });
  assert.match(r.note, /not a payment decision/);
});

test('unverified lines are counted beside the clean ones, not inside them', () => {
  const r = m.matchOrder([order([SHINGLE])]);
  assert.strictEqual(r.clean_lines, 0);
  assert.strictEqual(r.unverified_lines, 1);
});

// ---------------------------------------------------------------------------
section('matching, tolerances and refusals');

test('lines match on item code, NOT on position', () => {
  // A supplier does not invoice in the order you ordered. Matching by index
  // would compare shingles to fasteners.
  const r = m.matchOrder([
    order([SHINGLE, { item_code: 'NAIL-1', qty_ordered: 20, unit_price: 40 }]),
    receipt([{ item_code: 'NAIL-1', qty_received: 20 }, { item_code: 'SH-30', qty_received: 100 }])
  ]);
  assert.ok(!codes(r, 'c:sh-30').includes('short_received'));
  assert.ok(!codes(r, 'c:nail-1').includes('short_received'));
});

test('with no item code it falls back to a normalised description', () => {
  const r = m.matchOrder([
    order([{ description: '  Ridge   Vent ', qty_ordered: 10, unit_price: 5 }]),
    receipt([{ description: 'ridge vent', qty_received: 10 }])
  ]);
  assert.ok(!codes(r, 'd:ridge vent').includes('short_received'));
});

test('tolerances forgive only what they are set to, and are REPORTED', () => {
  const docs = [order([SHINGLE]), receipt([{ item_code: 'SH-30', qty_received: 99 }])];
  assert.ok(codes(m.matchOrder(docs), 'c:sh-30').includes('short_received'));
  const lenient = m.matchOrder(docs, { qty_tolerance: 1 });
  assert.ok(!codes(lenient, 'c:sh-30').includes('short_received'));
  assert.strictEqual(lenient.qty_tolerance, 1, 'the tolerance used was not reported');
});

test('the DEFAULT tolerance is exact matching, not a silent forgiveness', () => {
  assert.strictEqual(m.DEFAULT_QTY_TOLERANCE, 0);
  assert.strictEqual(m.DEFAULT_PRICE_TOLERANCE, 0);
  assert.strictEqual(m.matchOrder([order([SHINGLE])]).qty_tolerance, 0);
});

test('no purchase order -> refused, and the message says what that MEANS', () => {
  const r = m.matchOrder([invoice([{ item_code: 'SH-30', qty_invoiced: 100, unit_price: 32 }])]);
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.error.code, 'NO_ORDER');
  assert.match(r.error.message, /unordered charge/);
});

test('two orders under one PO -> refused rather than silently halving the order', () => {
  const r = m.matchOrder([order([SHINGLE]), order([SHINGLE])]);
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.error.code, 'DUPLICATE_ORDER');
});

test('unknown document types are ignored, not guessed at', () => {
  const r = m.matchOrder([order([SHINGLE]), { doc_type: 'quote', lines: [{ item_code: 'SH-30', qty_ordered: 999 }] }]);
  assert.strictEqual(r.lines[0].ordered_qty, 100);
});

test('junk input does not throw', () => {
  assert.strictEqual(m.matchOrder(null).ok, false);
  assert.strictEqual(m.matchOrder([null, 'x', 7]).ok, false);
  const r = m.matchOrder([order([SHINGLE, null, { }])]);
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.lines.length, 1);
});

test('the module ships NO seeded suppliers or part numbers', () => {
  const src = require('fs').readFileSync(require.resolve('./roofing-supplier-match.js'), 'utf8');
  const code = src.split('\n').filter(l => l.trim().indexOf('//') !== 0).join('\n');
  assert.ok(!/ABC Supply|Beacon|SRS|const SEED|SAMPLE_/.test(code), 'seed data in the engine');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' SUPPLIER-MATCH ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
