// api/_lib/roofing-supplement.test.js
// Plain node:assert tests. Run: node api/_lib/roofing-supplement.test.js
//
// This engine is the one that must be provably deterministic -- a wrong number
// here goes in front of an adjuster. Every branch is arithmetic and is checked
// with the arithmetic done by hand in the assertion.

const assert = require('assert');
const s = require('./roofing-supplement');

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ok - ' + name); }
  catch (err) { failed++; console.error('  FAIL - ' + name); console.error('    ' + err.message); }
}

const MEASURED = { squares: 30, ridge_lf: 40, valley_lf: 60, eave_lf: 120 };
const EXPECTED = [
  { item_key: 'ridge_cap', label: 'Ridge cap', measured_from: 'ridge_lf', unit: 'LF', unit_price: 8 },
  { item_key: 'valley_metal', label: 'Valley metal', measured_from: 'valley_lf', unit: 'LF', unit_price: 12 },
  { item_key: 'field', label: 'Field shingles', measured_from: 'squares', unit: 'SQ', unit_price: 350 }
];

console.log('Derived supplements -- pure arithmetic:');
test('a quantity shortfall is quantity_correction with the delta priced', () => {
  const r = s.reconcile({ measured: MEASURED, expected_items: EXPECTED,
    adjuster_lines: [{ item_key: 'ridge_cap', quantity: 25, unit_price: 8 }] });
  const rc = r.derived.find((d) => d.item_key === 'ridge_cap');
  assert.strictEqual(rc.status, 'quantity_short');
  assert.strictEqual(rc.reason_code, 'quantity_correction');
  assert.strictEqual(rc.shortfall_qty, 15);          // 40 - 25
  assert.strictEqual(rc.supplement_amount, 120);     // 15 * 8
});
test('an item absent from the adjuster estimate is omitted_item at full measured qty', () => {
  const r = s.reconcile({ measured: MEASURED, expected_items: EXPECTED, adjuster_lines: [] });
  const v = r.derived.find((d) => d.item_key === 'valley_metal');
  assert.strictEqual(v.status, 'omitted');
  assert.strictEqual(v.reason_code, 'omitted_item');
  assert.strictEqual(v.shortfall_qty, 60);
  assert.strictEqual(v.supplement_amount, 720);      // 60 * 12
});
test('an exactly-matched quantity is matched, zero supplement', () => {
  const r = s.reconcile({ measured: MEASURED, expected_items: EXPECTED,
    adjuster_lines: [{ item_key: 'field', quantity: 30, unit_price: 350 }] });
  const f = r.derived.find((d) => d.item_key === 'field');
  assert.strictEqual(f.status, 'matched');
  assert.strictEqual(f.reason_code, null);
  assert.strictEqual(f.supplement_amount, 0);
});
test('the adjuster allowing MORE than measured never nets negative', () => {
  const r = s.reconcile({ measured: MEASURED, expected_items: EXPECTED,
    adjuster_lines: [
      { item_key: 'field', quantity: 35, unit_price: 350 },   // 5 over -> no supplement, no negative
      { item_key: 'valley_metal', quantity: 0, unit_price: 12 } // omitted-ish: 60 short
    ] });
  const f = r.derived.find((d) => d.item_key === 'field');
  assert.strictEqual(f.status, 'adjuster_over');
  assert.strictEqual(f.supplement_amount, 0);
  // The over-allowance must NOT reduce the real shortfalls. ridge_cap has no
  // adjuster line -> omitted 40*8=320; valley is 60 short -> 720; field over
  // -> 0. Total 1040, and crucially the +5 on field nets against nothing.
  assert.strictEqual(r.totals.derived_supplement, 1040);
});
test('tolerance absorbs float noise but not a real shortfall', () => {
  const r = s.reconcile({ measured: { ridge_lf: 40 }, tolerance: 0.5,
    expected_items: [{ item_key: 'ridge_cap', measured_from: 'ridge_lf', unit_price: 8 }],
    adjuster_lines: [{ item_key: 'ridge_cap', quantity: 39.7, unit_price: 8 }] });
  assert.strictEqual(r.derived[0].status, 'matched'); // 0.3 within tolerance
  const r2 = s.reconcile({ measured: { ridge_lf: 40 }, tolerance: 0.5,
    expected_items: [{ item_key: 'ridge_cap', measured_from: 'ridge_lf', unit_price: 8 }],
    adjuster_lines: [{ item_key: 'ridge_cap', quantity: 39, unit_price: 8 }] });
  assert.strictEqual(r2.derived[0].status, 'quantity_short'); // 1.0 exceeds tolerance
});
test('a measured value that is missing is flagged, not treated as zero', () => {
  const r = s.reconcile({ measured: {}, expected_items: EXPECTED, adjuster_lines: [] });
  assert.ok(r.derived.every((d) => d.status === 'no_measurement'));
  assert.strictEqual(r.totals.derived_supplement, 0); // never fabricates omissions from absent data
});
test('matching is by explicit item_key ONLY -- an unkeyed adjuster line is a flagged problem', () => {
  const r = s.reconcile({ measured: MEASURED, expected_items: EXPECTED,
    adjuster_lines: [{ description: 'Ridge cap replacement', quantity: 25 }] }); // no item_key
  assert.ok(r.problems.some((p) => /no item_key/.test(p)));
  // and ridge_cap is therefore still omitted, not fuzzily matched to the text
  assert.strictEqual(r.derived.find((d) => d.item_key === 'ridge_cap').status, 'omitted');
});
test('two adjuster lines with the same key are summed and flagged', () => {
  const r = s.reconcile({ measured: MEASURED, expected_items: EXPECTED,
    adjuster_lines: [
      { item_key: 'ridge_cap', quantity: 20, unit_price: 8 },
      { item_key: 'ridge_cap', quantity: 10, unit_price: 8 }
    ] });
  const rc = r.derived.find((d) => d.item_key === 'ridge_cap');
  assert.strictEqual(rc.adjuster_qty, 30);           // 20 + 10
  assert.strictEqual(rc.shortfall_qty, 10);          // 40 - 30
  assert.ok(r.problems.some((p) => /2 lines keyed/.test(p)));
});

console.log('\nAsserted supplements -- evidence-required, never computed:');
test('a hidden_damage line WITH a photo counts', () => {
  const r = s.reconcile({ measured: MEASURED, expected_items: [], adjuster_lines: [],
    asserted_lines: [{ reason_code: 'hidden_damage', description: 'Deck rot', quantity: 2, unit_price: 65, photo_ids: ['P1'] }] });
  assert.strictEqual(r.asserted[0].valid, true);
  assert.strictEqual(r.asserted[0].supplement_amount, 130); // 2 * 65
  assert.strictEqual(r.totals.asserted_supplement, 130);
});
test('an asserted line WITHOUT a photo is invalid and contributes ZERO', () => {
  const r = s.reconcile({ measured: MEASURED, expected_items: [], adjuster_lines: [],
    asserted_lines: [{ reason_code: 'code_upgrade', description: 'Ice & water', quantity: 3, unit_price: 120, photo_ids: [] }] });
  assert.strictEqual(r.asserted[0].valid, false);
  assert.ok(r.asserted[0].issues.some((i) => /photo/.test(i)));
  assert.strictEqual(r.asserted[0].supplement_amount, 0);   // never silently inflates the total
  assert.strictEqual(r.totals.asserted_supplement, 0);
  assert.strictEqual(r.totals.asserted_invalid_count, 1);
});
test('a derived reason cannot be used as an asserted line', () => {
  const r = s.reconcile({ measured: MEASURED, expected_items: [], adjuster_lines: [],
    asserted_lines: [{ reason_code: 'omitted_item', description: 'x', quantity: 1, unit_price: 10, photo_ids: ['P1'] }] });
  assert.strictEqual(r.asserted[0].valid, false);
  assert.ok(r.asserted[0].issues.some((i) => /code_upgrade or hidden_damage/.test(i)));
});
test('a zero or negative asserted quantity is invalid', () => {
  const r = s.reconcile({ measured: MEASURED, expected_items: [], adjuster_lines: [],
    asserted_lines: [{ reason_code: 'hidden_damage', quantity: 0, unit_price: 10, photo_ids: ['P1'] }] });
  assert.strictEqual(r.asserted[0].valid, false);
});

console.log('\nTotals:');
test('the total is derived + asserted, and the counts add up', () => {
  const r = s.reconcile({
    measured: MEASURED, expected_items: EXPECTED,
    adjuster_lines: [{ item_key: 'ridge_cap', quantity: 25, unit_price: 8 }], // short 15 -> 120; valley omitted -> 720; field omitted -> 350*30=10500
    asserted_lines: [{ reason_code: 'hidden_damage', quantity: 2, unit_price: 65, photo_ids: ['P1'] }] // 130
  });
  assert.strictEqual(r.totals.quantity_short_count, 1);
  assert.strictEqual(r.totals.omitted_count, 2);           // valley + field
  assert.strictEqual(r.totals.derived_supplement, 120 + 720 + 10500);
  assert.strictEqual(r.totals.asserted_supplement, 130);
  assert.strictEqual(r.totals.total_supplement, 120 + 720 + 10500 + 130);
});
test('an empty worksheet is a clean zero, not an error', () => {
  const r = s.reconcile({});
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.totals.total_supplement, 0);
  assert.deepStrictEqual(r.derived, []);
});
test('reason-code sets are disjoint and complete', () => {
  assert.deepStrictEqual(s.DERIVED_REASONS.concat(s.ASSERTED_REASONS).sort(), s.REASON_CODES.slice().sort());
  assert.strictEqual(s.DERIVED_REASONS.filter((x) => s.ASSERTED_REASONS.indexOf(x) !== -1).length, 0);
});

console.log('\n' + passed + ' passed, ' + failed + ' failed');
if (failed > 0) process.exit(1);
