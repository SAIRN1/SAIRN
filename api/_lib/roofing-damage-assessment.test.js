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
    slopes_total: 3, meets_threshold: 1, below_threshold: 1, material_unavailable: 0,
    insufficient_evidence: 1, unassessed_slopes_remain: true
  });
});

console.log('Hard replace trigger -- a fact about availability, not a count:');
test('discontinued material gets its OWN outcome, never meets_threshold', () => {
  // CHANGED 2026-08-26 (Michael's call). This previously returned
  // meets_threshold, which made a supply fact read as "this slope met your hail
  // threshold" -- nothing was measured against the threshold at all.
  const r = d.assess({ peril: 'hail', threshold: TH, slopes: [{ slope_label: 'N', discontinued_material: true }] });
  assert.strictEqual(r.slopes[0].outcome, 'material_unavailable');
  assert.strictEqual(r.slopes[0].basis, 'discontinued_material');
  assert.strictEqual(r.slopes[0].counted, null);
  assert.match(r.slopes[0].reason, /NOT measured against the damage threshold/);
  // It must not be counted as a threshold hit anywhere in the summary either.
  assert.strictEqual(r.summary.meets_threshold, 0);
  assert.strictEqual(r.summary.material_unavailable, 1);
});
test('discontinued material is EXEMPT from the strict photo rule, and says why', () => {
  // A discontinued shingle is evidenced by a supplier letter, not a roof photo.
  const r = d.assess({
    peril: 'hail', threshold: TH, claim_photo_ids: [],
    slopes: [{ slope_label: 'N', discontinued_material: true }]
  });
  assert.strictEqual(r.slopes[0].outcome, 'material_unavailable');
  assert.match(r.slopes[0].evidence_gap, /supplier or manufacturer letter/);
});

console.log('THE STRICT PHOTO RULE -- a count with no evidence is not a finding:');
test('a met threshold with NO photo does not reach meets_threshold', () => {
  const r = d.assess({
    peril: 'hail', threshold: TH, claim_photo_ids: ['REAL1'],
    slopes: [{ slope_label: 'N', test_squares: 1, hits: 40, photo_ids: [] }]
  });
  assert.strictEqual(r.slopes[0].outcome, 'insufficient_evidence');
  assert.strictEqual(r.slopes[0].photo_verified, false);
  // The count is REPORTED in full -- suppressing it would hide real field work.
  assert.strictEqual(r.slopes[0].counted, 40);
  assert.strictEqual(r.slopes[0].per_test_square, 40);
  assert.match(r.slopes[0].reason, /met by the numbers/);
});
test('a photo id NOT on this claim does not evidence the slope, and is named', () => {
  const r = d.assess({
    peril: 'hail', threshold: TH, claim_photo_ids: ['REAL1'],
    slopes: [{ slope_label: 'N', test_squares: 1, hits: 40, photo_ids: ['GHOST', 'REAL1'] }]
  });
  // REAL1 resolves, so the slope IS evidenced and the threshold stands.
  assert.strictEqual(r.slopes[0].outcome, 'meets_threshold');
  assert.deepStrictEqual(r.slopes[0].photo_ids, ['REAL1']);
  assert.deepStrictEqual(r.slopes[0].unresolved_photo_ids, ['GHOST']);
});
test('ONLY ghost ids means unverified -- the ids are named, not silently dropped', () => {
  const r = d.assess({
    peril: 'hail', threshold: TH, claim_photo_ids: ['REAL1'],
    slopes: [{ slope_label: 'N', test_squares: 1, hits: 40, photo_ids: ['GHOST1', 'GHOST2'] }]
  });
  assert.strictEqual(r.slopes[0].outcome, 'insufficient_evidence');
  assert.deepStrictEqual(r.slopes[0].unresolved_photo_ids, ['GHOST1', 'GHOST2']);
  assert.match(r.slopes[0].evidence_gap, /not on this claim: GHOST1, GHOST2/);
});
test('the strict rule binds meets_threshold ONLY -- below_threshold still reports', () => {
  const r = d.assess({
    peril: 'hail', threshold: TH, claim_photo_ids: [],
    slopes: [{ slope_label: 'N', test_squares: 1, hits: 2, photo_ids: [] }]
  });
  assert.strictEqual(r.slopes[0].outcome, 'below_threshold');
});
test('an unverifiable caller is told so rather than failing every slope', () => {
  // No claim_photo_ids supplied at all: photo_verified is null, not false, and
  // the cited ids are taken at face value.
  const r = d.assess({
    peril: 'hail', threshold: TH,
    slopes: [{ slope_label: 'N', test_squares: 1, hits: 40, photo_ids: ['P1'] }]
  });
  assert.strictEqual(r.slopes[0].outcome, 'meets_threshold');
  assert.strictEqual(r.slopes[0].photo_verified, null);
  assert.strictEqual(r.photo_verification, 'not_verified');
});
test('a verifying caller is recorded as having verified', () => {
  const r = d.assess({
    peril: 'hail', threshold: TH, claim_photo_ids: ['P1'],
    slopes: [{ slope_label: 'N', test_squares: 1, hits: 40, photo_ids: ['P1'] }]
  });
  assert.strictEqual(r.photo_verification, 'server_verified');
  assert.strictEqual(r.slopes[0].photo_verified, true);
});
test('the outcome vocabulary is closed and has exactly four members', () => {
  assert.deepStrictEqual(d.OUTCOMES,
    ['meets_threshold', 'below_threshold', 'material_unavailable', 'insufficient_evidence']);
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
