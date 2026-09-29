// tests/compliance_training_window_boundary.js
//
// REQUIREMENT: the hire-anchored training window reports a date that exists, and
//   does not turn the first day of a new training year into a non-compliance
//   finding.
//
// Run:  node tests/compliance_training_window_boundary.js
//
// ── TWO REPROS, BOTH DRIVEN 2026-09-29 ────────────────────────────────────
//
// (1) THE ONE-DAY CLIFF. Hire 2024-11-03, one 8-hour record on 2026-10-15:
//
//       evaluated 2026-11-02 -> window_from 2025-11-03   total 8
//       evaluated 2026-11-03 -> window_from 2026-11-03   total 0
//
//     The boundary itself is right -- an annual requirement anchored to hire
//     date means "within each twelve-month period following hire", and the
//     anniversary opens a new period. What follows from it is not:
//     `evaluateTraining` reaches `else if (recorded < poolMax) verdict = false`,
//     so a person who completed a full year's training three weeks earlier is
//     reported NON-COMPLIANT on their anniversary. They are not late. They have
//     twelve months.
//
//     THE MODULE ALREADY MAKES THIS ARGUMENT, one door along. NO_HIRE_DATE
//     produces a null verdict with the reason spelled out: *"a total of zero
//     would report a fully trained person as non-compliant from a missing
//     field."* Substitute "from a window that reset this morning" and the
//     sentence is unchanged.
//
// (2) A DATE THAT DOES NOT EXIST. `from` was assembled as
//     `String(year) + hire.slice(4)`, so a leap-day hire published:
//
//       hire 2024-02-29, evaluated 2026-03-15 -> window_from 2026-02-29
//
//     There is no 29 February 2026. The counting was unaffected, because `from`
//     is only ever string-compared and '2026-02-29' sorts between the 28th and
//     the 1st -- but `window_from` is printed on a compliance finding a surveyor
//     reads, and it reads as a real date.
//
// ── THE SCOPE OF THE VERDICT CHANGE, STATED ───────────────────────────────
// `meets` becomes null ONLY where the verdict is certainly meaningless: zero
// days elapsed in the window. Every other day gets `window_days_elapsed` and
// `window_days_remaining` on the finding instead, so a consumer can tell late
// from early without this module inventing a threshold. AT WHAT POINT IN A
// WINDOW A SHORTFALL BECOMES A FINDING IS A PRODUCT DECISION and is deliberately
// not made here -- a fraction-of-the-window rule would be a policy chosen by
// whoever happened to be editing the file.

'use strict';

const assert = require('assert');
const path = require('path');
const m = require(path.join(__dirname, '..', 'api', '_lib', 'compliance-rules.js'));

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

const HIRE = '2024-11-03';
const RECS = [
  { completed_on: '2026-10-15', hours: 8, category: 'general' },
  { completed_on: '2026-11-04', hours: 2, category: 'general' }
];

function win(on, hire, recs) {
  return m.hoursInWindow(recs || RECS, 'rolling_12_months_from_hire', on, null,
                         hire || HIRE);
}

section('1. THE WINDOW ARITHMETIC IS UNCHANGED -- the boundary was right');

test('the day BEFORE the anniversary is still in the year that is ending', () => {
  const r = win('2026-11-02');
  assert.strictEqual(r.window_from, '2025-11-03');
  assert.strictEqual(r.total, 8);
});

test('the anniversary OPENS the new year, and the count really is zero', () => {
  // This is correct and is NOT what is being changed. The count is a fact; the
  // verdict drawn from it was the defect.
  const r = win('2026-11-03');
  assert.strictEqual(r.window_from, '2026-11-03');
  assert.strictEqual(r.total, 0);
});

section('2. REPRO (2) -- window_from must be a date that exists');

test('a leap-day hire does not publish 29 February of a common year', () => {
  const r = win('2026-03-15', '2024-02-29',
                [{ completed_on: '2026-06-01', hours: 5, category: 'general' }]);
  assert.notStrictEqual(r.window_from, '2026-02-29',
    'window_from is 2026-02-29, which is not a date');
  assert.ok(/^\d{4}-\d{2}-\d{2}$/.test(r.window_from), r.window_from);
  const d = new Date(r.window_from + 'T00:00:00Z');
  assert.strictEqual(d.toISOString().slice(0, 10), r.window_from,
    'window_from ' + r.window_from + ' does not round-trip as a real date');
});

test('...and a leap-day hire evaluated in a LEAP year keeps the 29th', () => {
  // The correction must not move the anchor in years where it exists.
  const r = win('2028-06-01', '2024-02-29', []);
  assert.strictEqual(r.window_from, '2028-02-29');
});

test('...and the leap-day window still counts the right records', () => {
  const r = win('2027-02-28', '2024-02-29',
                [{ completed_on: '2026-06-01', hours: 5, category: 'general' }]);
  assert.strictEqual(r.total, 5, 'the normalisation changed what is counted');
});

section('3. THE WINDOW REPORTS HOW FAR THROUGH IT IS');

test('days elapsed and remaining are on the window result', () => {
  const r = win('2026-11-03');
  assert.strictEqual(r.window_days_elapsed, 0,
    'elapsed = ' + JSON.stringify(r.window_days_elapsed));
  assert.ok(r.window_days_remaining > 360,
    'remaining = ' + JSON.stringify(r.window_days_remaining));
  const mid = win('2027-05-03');
  assert.ok(mid.window_days_elapsed > 170 && mid.window_days_elapsed < 190,
    'mid-window elapsed = ' + mid.window_days_elapsed);
});

test('they are absent, not zero, when the window could not be computed', () => {
  // Zero is a real answer here. A window that could not be computed must not
  // produce one -- that is the same could-not-tell-is-not-a-value rule the
  // window_error field already follows.
  const r = m.hoursInWindow(RECS, 'rolling_12_months_from_hire', '2026-11-03',
                            null, '');
  assert.strictEqual(r.window_error, 'NO_HIRE_DATE');
  assert.strictEqual(r.window_days_elapsed, null);
  assert.strictEqual(r.window_days_remaining, null);
});

section('4. REPRO (1) -- day zero of a window is not a non-compliance finding');

// A RULE SET, not a rule -- evaluateTraining selects from a list by state,
// type and effective date, the way the endpoint hands it the loaded seed.
const RULES = [{
  rule_id: 'ZZ-TRAINING', state: 'PA', requirement_type: 'training',
  citation: 'ZZ 1.1', effective_from: '2020-01-01',
  data: {
    annual_window: 'rolling_12_months_from_hire',
    requirements: [{ id: 'r1', annual_hours: 8, pool: 'general',
                     applies_to_positions: ['caregiver'] }]
  }
}];

function evaluate(onDate, records) {
  return m.evaluateTraining(RULES, {
    state: 'PA',
    staff: [{ staff_id: 's1', name: 'A Person', position: 'caregiver',
              hire_date: HIRE, records: records }],
    on_date: onDate
  });
}

test('THE DEFECT: on the anniversary, a person trained three weeks ago is NOT '
  + 'reported non-compliant', () => {
    const out = evaluate('2026-11-03', [RECS[0]]);
    const f = (out.staff_findings || [])[0];
    assert.ok(f, 'no finding was produced: ' + JSON.stringify(out).slice(0, 300));
    assert.notStrictEqual(f.meets, false,
      'meets=false on day zero of a new training year. recorded='
      + JSON.stringify(f.recorded_hours) + ' window_from='
      + JSON.stringify(f.hours_window_from));
    assert.strictEqual(f.meets, null,
      'meets should be null -- the same refusal the module already gives for '
      + 'NO_HIRE_DATE. got ' + JSON.stringify(f.meets));
    assert.ok(/window/i.test(String(f.meets_unknown_reason || '')),
      'the null carries no reason naming the window: '
      + JSON.stringify(f.meets_unknown_reason));
  });

test('CONTROL: a genuine shortfall LATER in the window is still false', () => {
    // The arm that keeps this from being a way to never report anybody. If the
    // refusal widened past day zero, this goes green-for-the-wrong-reason and
    // the module stops answering the question it exists for.
    const out = evaluate('2027-05-03', [RECS[0]]);
    const f = (out.staff_findings || [])[0];
    assert.strictEqual(f.meets, false,
      'a person six months into a window with no hours in it is no longer '
      + 'reported short. meets=' + JSON.stringify(f.meets));
  });

test('CONTROL: meeting the requirement ON day zero is still true', () => {
    // Somebody who front-loads training on their anniversary is determinately
    // compliant, and a blanket "day zero is unknowable" would have hidden that.
    const out = evaluate('2026-11-03',
      [{ completed_on: '2026-11-03', hours: 8, category: 'general' }]);
    const f = (out.staff_findings || [])[0];
    assert.strictEqual(f.meets, true, 'meets=' + JSON.stringify(f.meets));
  });

test('CONTROL: the day BEFORE the anniversary is unaffected', () => {
    const out = evaluate('2026-11-02', [RECS[0]]);
    const f = (out.staff_findings || [])[0];
    assert.strictEqual(f.meets, true,
      '8 hours in the year that is ending no longer reads as compliant');
  });

test('NEGATIVE CONTROL: the harness can produce a false verdict at all', () => {
    // Without this, a change that made `meets` null everywhere would satisfy the
    // defect arm and every control that asserts "not false".
    const out = evaluate('2027-05-03', []);
    const f = (out.staff_findings || [])[0];
    assert.strictEqual(f.meets, false,
      'this harness can no longer produce a false verdict, so the arms above '
      + 'are not measuring what they claim');
  });

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' TRAINING-WINDOW BOUNDARY ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
