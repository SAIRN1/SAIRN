// api/_lib/roofing-damage-assessment.test.js
// Plain node:assert tests. Run: node api/_lib/roofing-damage-assessment.test.js
//
// The assertion that matters most in this file is the one that proves a
// missing test-square count does NOT come back as below_threshold. Everything
// else here is arithmetic; that one is the silent-failure guard.

const assert = require('assert');
const d = require('./roofing-damage-assessment');

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ok - ' + name); }
  catch (err) { failed++; console.error('  FAIL - ' + name); console.error('    ' + err.message); }
}

const TH = { hits_per_test_square: 8, source: 'Company standard, 2026 field manual p.14' };

console.log('Threshold is required and must carry a source:');
test('no threshold at all refuses', () => {
  const r = d.assess({ peril: 'hail', slopes: [{ slope_label: 'North', test_squares: 1, hits: 9 }] });
  assert.strictEqual(r.ok, false);
  assert.ok(r.problems.some(p => /no damage threshold is configured/.test(p)));
});
test('a threshold with no source refuses -- an unsourced number is a guess', () => {
  const r = d.assess({ peril: 'hail', threshold: { hits_per_test_square: 8 }, slopes: [{ slope_label: 'N', test_squares: 1, hits: 9 }] });
  assert.strictEqual(r.ok, false);
  assert.ok(r.problems.some(p => /source is required/.test(p)));
});
test('a zero or fractional threshold refuses', () => {
  assert.strictEqual(d.validateThreshold({ hits_per_test_square: 0, source: 'x y z' }).length, 1);
  assert.strictEqual(d.validateThreshold({ hits_per_test_square: 8.5, source: 'x y z' }).length, 1);
});

console.log('Peril selects which count is compared -- never both, never summed:');
test('missing peril refuses', () => {
  const r = d.assess({ threshold: TH, slopes: [{ slope_label: 'N', test_squares: 1, hits: 9 }] });
  assert.strictEqual(r.ok, false);
  assert.ok(r.problems.some(p => /peril must be one of/.test(p)));
});
test('wind reads creased_or_missing and ignores hits entirely', () => {
  const r = d.assess({ peril: 'wind', threshold: TH, slopes: [{ slope_label: 'N', test_squares: 1, hits: 40, creased_or_missing: 2 }] });
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.slopes[0].outcome, 'below_threshold');
  assert.strictEqual(r.slopes[0].counted, 2, '40 hail hits must not leak into a wind assessment');
});
test('hail reads hits and ignores creases entirely', () => {
  const r = d.assess({ peril: 'hail', threshold: TH, slopes: [{ slope_label: 'N', test_squares: 1, hits: 2, creased_or_missing: 40 }] });
  assert.strictEqual(r.slopes[0].counted, 2);
  assert.strictEqual(r.slopes[0].outcome, 'below_threshold');
});

console.log('The three outcomes, and the arithmetic behind each:');
test('at threshold exactly meets it -- >= not >', () => {
  const r = d.assess({ peril: 'hail', threshold: TH, slopes: [{ slope_label: 'S', test_squares: 1, hits: 8 }] });
  assert.strictEqual(r.slopes[0].outcome, 'meets_threshold');
});
test('one under the threshold is below it', () => {
  const r = d.assess({ peril: 'hail', threshold: TH, slopes: [{ slope_label: 'S', test_squares: 1, hits: 7 }] });
  assert.strictEqual(r.slopes[0].outcome, 'below_threshold');
});
test('density is per test square, not a raw total', () => {
  // 12 hits across 3 squares is 4 per square, which is BELOW 8 -- a raw-total
  // comparison would wrongly call this slope total.
  const r = d.assess({ peril: 'hail', threshold: TH, slopes: [{ slope_label: 'E', test_squares: 3, hits: 12 }] });
  assert.strictEqual(r.slopes[0].per_test_square, 4);
  assert.strictEqual(r.slopes[0].outcome, 'below_threshold');
});
test('density is not rounded up into a total', () => {
  // 15 over 2 squares is 7.5 per square. Rounding to 8 would manufacture a
  // totalled slope out of arithmetic. It must stay below.
  const r = d.assess({ peril: 'hail', threshold: TH, slopes: [{ slope_label: 'W', test_squares: 2, hits: 15 }] });
  assert.strictEqual(r.slopes[0].per_test_square, 7.5);
  assert.strictEqual(r.slopes[0].outcome, 'below_threshold');
});

console.log('THE SILENT-FAILURE GUARD -- unrecorded is never "fine":');
test('no hit count recorded is insufficient_evidence, NOT below_threshold', () => {
  const r = d.assess({ peril: 'hail', threshold: TH, slopes: [{ slope_label: 'North', test_squares: 2 }] });
  assert.strictEqual(r.slopes[0].outcome, 'insufficient_evidence');
  assert.notStrictEqual(r.slopes[0].outcome, 'below_threshold');
  assert.ok(/not a finding of low damage/.test(r.slopes[0].evidence_gap));
});
test('no test squares recorded is insufficient_evidence even with a hit count', () => {
  const r = d.assess({ peril: 'hail', threshold: TH, slopes: [{ slope_label: 'North', hits: 20 }] });
  assert.strictEqual(r.slopes[0].outcome, 'insufficient_evidence');
});
test('zero hits over a real test square IS a real finding, not missing data', () => {
  // The distinction the guard above must not over-reach on: somebody DID
  // inspect and found nothing. That is below_threshold, a genuine result.
  const r = d.assess({ peril: 'hail', threshold: TH, slopes: [{ slope_label: 'North', test_squares: 2, hits: 0 }] });
  assert.strictEqual(r.slopes[0].outcome, 'below_threshold');
});
test('a partially-recorded roof reports the gap at the summary level', () => {
  const r = d.assess({
    peril: 'hail', threshold: TH,
    slopes: [
      { slope_label: 'N', test_squares: 1, hits: 9 },
      { slope_label: 'S', test_squares: 1, hits: 2 },
      { slope_label: 'E' }
    ]
  });
  assert.deepStrictEqual(r.summary, {
    slopes_total: 3, meets_threshold: 1, below_threshold: 1, insufficient_evidence: 1, unassessed_slopes_remain: true
  });
});

console.log('Hard replace trigger -- a fact about availability, not a count:');
test('discontinued material meets the threshold with no count at all', () => {
  const r = d.assess({ peril: 'hail', threshold: TH, slopes: [{ slope_label: 'N', discontinued_material: true }] });
  assert.strictEqual(r.slopes[0].outcome, 'meets_threshold');
  assert.strictEqual(r.slopes[0].basis, 'discontinued_material');
  assert.strictEqual(r.slopes[0].counted, null);
});

console.log('Photo traceability and the boundary the output must not cross:');
test('a slope with no cited photo is flagged as unsupported', () => {
  const r = d.assess({ peril: 'hail', threshold: TH, slopes: [{ slope_label: 'N', test_squares: 1, hits: 9 }] });
  assert.ok(/No photo cited/.test(r.slopes[0].evidence_gap));
});
test('cited photos are carried through and blanks dropped', () => {
  const r = d.assess({ peril: 'hail', threshold: TH, slopes: [{ slope_label: 'N', test_squares: 1, hits: 9, photo_ids: ['P1', '', '  ', 'P2'] }] });
  assert.deepStrictEqual(r.slopes[0].photo_ids, ['P1', 'P2']);
  assert.strictEqual(r.slopes[0].evidence_gap, null);
});
test('every result carries the threshold AND its source, so the reader can check it', () => {
  const r = d.assess({ peril: 'hail', threshold: TH, slopes: [{ slope_label: 'N', test_squares: 1, hits: 9 }] });
  assert.strictEqual(r.slopes[0].threshold, 8);
  assert.strictEqual(r.slopes[0].threshold_source, TH.source);
});
test('there is NO roof-level totalled verdict field anywhere in the output', () => {
  // The public-adjuster boundary, asserted mechanically. Carriers total
  // slopes; a roof-level yes/no is the sentence this engine may not say.
  const r = d.assess({ peril: 'hail', threshold: TH, slopes: [{ slope_label: 'N', test_squares: 1, hits: 20 }] });
  const flat = JSON.stringify(r).toLowerCase();
  ['totalled', 'totaled', 'should_replace', 'replace_roof', 'approved', 'entitled', 'owed'].forEach(function (banned) {
    assert.ok(flat.indexOf(banned) === -1, 'output must not contain "' + banned + '"');
  });
  assert.ok(!Object.prototype.hasOwnProperty.call(r.summary, 'verdict'));
});
test('an override is recorded as an override rather than silently applied', () => {
  const r = d.assess({ peril: 'hail', threshold: { hits_per_test_square: 5, source: 'Carrier bulletin 2026-03' }, threshold_is_override: true, slopes: [{ slope_label: 'N', test_squares: 1, hits: 6 }] });
  assert.strictEqual(r.threshold_is_override, true);
  assert.strictEqual(r.slopes[0].outcome, 'meets_threshold');
});

console.log('\n' + passed + ' passed, ' + failed + ' failed');
process.exit(failed ? 1 : 0);
