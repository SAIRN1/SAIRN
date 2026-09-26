// api/_lib/compliance-rules-wv.test.js
//
//   node api/_lib/compliance-rules-wv.test.js
//
// WEST VIRGINIA, AND THE COVERAGE CAP THAT STOPS AT FIVE.
//
// THE ARM THAT MATTERS IS THE DENOMINATOR ONE. Every secondary summary of
// 64 CSR 14 renders the staffing rule as a census ratio -- "Day 1:10, Evening
// 1:15, Night 1:18". The code text does not say that: each ADDITIONAL staff
// member is required per N residents "identified on their needs assessments to
// have two or more" of an enumerated list of care needs, and those additions
// sit on top of a one-staff-at-all-times floor.
//
// The difference is not academic. A 30-bed residence with four such residents
// needs TWO on days under the code and THREE under the summary. The summary's
// answer is higher, which is why it would never have been questioned -- an
// over-statement reads as conservative and therefore safe. It is still a wrong
// number on a staffing board, and the arm below pins the real one.
//
// The second arm that matters is the refusal: given a CENSUS and no
// special-care-needs count, the engine must report `missing` rather than
// quietly using the census as the denominator.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const REPO = path.dirname(__dirname);
const e = require('./compliance-rules');
const seed = JSON.parse(fs.readFileSync(
  path.join(REPO, '..', 'sql', 'sairncare_compliance_seed.json'), 'utf8'));
const rules = seed.rules;
const D = '2026-09-25';
const WV = { state: 'WV', facility_class: 'assisted_living_residence', on_date: D };

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (err) { console.log('  FAIL ' + name + '\n         ' + err.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

section('STAFFING: the denominator is special-care-needs residents, not census');

test('THE ARM THAT MATTERS: 4 residents with two or more special care needs on '
   + 'the day shift requires the 1 floor + 1, not 1 per 10 of the census', () => {
  const r = e.evaluateStaffing(rules, Object.assign({}, WV,
    { shift: 'day', special_care_needs_residents: 4, direct_care_staff: 2 }));
  assert.strictEqual(r.evaluated, true);
  assert.strictEqual(r.baseline_staff, 1);
  assert.strictEqual(r.additional_for_special_needs, 1);
  assert.strictEqual(r.required_staff, 2);
  assert.strictEqual(r.meets, true);
});

test('NEGATIVE CONTROL: the summary\'s answer for the same facility is HIGHER, '
   + 'so a census-based implementation would have looked conservative and been wrong', () => {
  const r = e.evaluateStaffing(rules, Object.assign({}, WV,
    { shift: 'day', special_care_needs_residents: 4, direct_care_staff: 2 }));
  assert.ok(r.required_staff < Math.ceil(30 / 10) + 0,
    'the engine produced the census answer for a 30-bed home with 4 qualifying residents');
});

test('THE FLOOR STANDS ON ITS OWN: zero qualifying residents still requires one '
   + 'direct care staff person, because 4.4.1 is a separate sentence', () => {
  const r = e.evaluateStaffing(rules, Object.assign({}, WV,
    { shift: 'night', special_care_needs_residents: 0, direct_care_staff: 1 }));
  assert.strictEqual(r.required_staff, 1);
  assert.strictEqual(r.meets, true);
});

test('...and zero staff against that floor does NOT meet it', () => {
  const r = e.evaluateStaffing(rules, Object.assign({}, WV,
    { shift: 'night', special_care_needs_residents: 0, direct_care_staff: 0 }));
  assert.strictEqual(r.meets, false);
});

test('the three shifts carry three different divisors, and the boundary rounds UP', () => {
  const at = function (shift, n) {
    return e.evaluateStaffing(rules, Object.assign({}, WV,
      { shift: shift, special_care_needs_residents: n })).required_staff;
  };
  assert.strictEqual(at('day', 10), 2);
  assert.strictEqual(at('day', 11), 3, 'one over the divisor must round up, not down');
  assert.strictEqual(at('evening', 15), 2);
  assert.strictEqual(at('evening', 16), 3);
  assert.strictEqual(at('night', 18), 2);
  assert.strictEqual(at('night', 19), 3);
});

test('THE SECOND ARM THAT MATTERS: a CENSUS with no special-needs count is '
   + 'REPORTED MISSING, never substituted as the denominator', () => {
  const r = e.evaluateStaffing(rules, Object.assign({}, WV,
    { shift: 'day', census: 30, direct_care_staff: 3 }));
  assert.strictEqual(r.evaluated, false);
  assert.deepStrictEqual(r.missing, ['special_care_needs_residents']);
  assert.ok(/over-state/.test(r.note), r.note);
  assert.strictEqual(r.required_staff, undefined, 'a number was produced anyway');
});

test('no shift is missing too -- the requirement differs by shift and there is '
   + 'no single number correct for all three', () => {
  const r = e.evaluateStaffing(rules, Object.assign({}, WV,
    { special_care_needs_residents: 4 }));
  assert.strictEqual(r.evaluated, false);
  assert.ok(r.missing.indexOf('shift') !== -1, JSON.stringify(r.missing));
});

test('an undefined shift is refused by name rather than defaulted', () => {
  const r = e.evaluateStaffing(rules, Object.assign({}, WV,
    { shift: 'swing', special_care_needs_residents: 4 }));
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.error.code, 'UNKNOWN_SHIFT');
});

test('the enumerated care needs travel WITH the answer -- which needs count is '
   + 'not this app\'s to decide', () => {
  const r = e.evaluateStaffing(rules, Object.assign({}, WV,
    { shift: 'day', special_care_needs_residents: 1 }));
  assert.ok(Array.isArray(r.special_care_needs) && r.special_care_needs.length >= 8,
    JSON.stringify(r.special_care_needs));
});

section('THE OTHER FOUR STATES ARE UNTOUCHED BY THE NEW METHOD');

test('the four pre-existing staffing methods still answer, and none of them '
   + 'became the new one', () => {
  const methods = {};
  rules.filter(function (r) { return r.requirement_type === 'staffing'; })
    .forEach(function (r) { methods[r.state] = methods[r.state] || r.data.method; });
  assert.strictEqual(methods.WV, 'baseline_plus_special_needs_by_shift');
  ['OH', 'IN', 'MI', 'PA'].forEach(function (s) {
    assert.ok(methods[s] && methods[s] !== 'baseline_plus_special_needs_by_shift',
      s + ' now reports ' + methods[s]);
  });
});

test('an unseeded state still fails CLOSED, naming the state', () => {
  const r = e.evaluateStaffing(rules, { state: 'KY', on_date: D, shift: 'day' });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.error.code, 'NO_RULE_FOR_STATE');
  assert.ok(/KY/.test(r.error.message));
});

test('a WV class this seed does not carry fails CLOSED too, rather than '
   + 'borrowing the assisted_living_residence numbers', () => {
  const r = e.evaluateStaffing(rules, { state: 'WV', on_date: D, shift: 'day',
    facility_class: 'memory_care' });
  assert.strictEqual(r.ok, false);
  assert.ok(/NO_RULE_FOR_CLASS|NO_RULE_FOR_STATE/.test(r.error.code), r.error.code);
});

section('THE COVERAGE CAP: five states, and a sixth cannot arrive quietly');

test('the cap is recorded IN the seed, with who decided it and when', () => {
  assert.deepStrictEqual(seed.coverage_cap.states, ['OH', 'IN', 'MI', 'PA', 'WV']);
  assert.strictEqual(seed.coverage_cap.decided_by, 'Michael');
  assert.strictEqual(seed.coverage_cap.decided_on, '2026-09-25');
});

test('THE GUARD: every state with a rule in this file is inside the cap -- a '
   + 'sixth state seeded without a decision turns this red', () => {
  const seeded = Array.from(new Set(rules.map(function (r) { return r.state; }))).sort();
  const capped = seed.coverage_cap.states.slice().sort();
  const outside = seeded.filter(function (s) { return capped.indexOf(s) === -1; });
  assert.deepStrictEqual(outside, [],
    'seeded outside the cap: ' + outside.join(', ') + ' -- the cap is a decision, not a backlog');
});

test('...and claimed_states agrees with what is actually seeded, so the header '
   + 'cannot claim a state the rules do not carry', () => {
  const seeded = Array.from(new Set(rules.map(function (r) { return r.state; }))).sort();
  assert.deepStrictEqual(seed.claimed_states.slice().sort(), seeded);
});

test('CONTROL: the guard really bites -- a rule for an uncapped state is detected', () => {
  const withKy = rules.concat([{ state: 'KY', requirement_type: 'staffing' }]);
  const seeded = Array.from(new Set(withKy.map(function (r) { return r.state; })));
  const outside = seeded.filter(function (s) { return seed.coverage_cap.states.indexOf(s) === -1; });
  assert.deepStrictEqual(outside, ['KY']);
});

section('WHAT WV DOES NOT ASSERT');

test('the training rule reports NO hour figure for orientation, because the '
   + 'code sets none -- a deadline is not an hour total', () => {
  const t = rules.find(function (r) { return r.rule_id === 'WV-TRAINING-ALR-2026'; });
  assert.strictEqual(t.data.orientation.hours, null);
  assert.ok(/15 days/.test(t.data.orientation.deadline));
});

test('the licensure rule records the term as a CEILING, not a fixed year', () => {
  const l = rules.find(function (r) { return r.rule_id === 'WV-LICENSURE-ALR-2026'; });
  assert.strictEqual(l.data.max_term_months, 12);
  assert.strictEqual(l.data.transferable, false);
  assert.ok(/NOT EXCEED|not a fixed year|CEILING/i.test(JSON.stringify(l.data.notes)));
});

test('every WV rule carries a citation, a quote and the date it was read', () => {
  rules.filter(function (r) { return r.state === 'WV'; }).forEach(function (r) {
    const a = r.data.authority;
    assert.ok(a && a.citation && a.quote && a.read_on, r.rule_id + ' is missing provenance');
    assert.strictEqual(a.read_on, '2026-09-25', r.rule_id);
  });
});

test('the staffing correction is recorded on the rule, so the wrong summary '
   + 'cannot be re-introduced from older notes', () => {
  const s = rules.find(function (r) { return r.rule_id === 'WV-STAFFING-ALR-2026'; });
  assert.ok(/census ratio/.test(s.data._corrected), s.data._corrected);
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' WV COMPLIANCE ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
