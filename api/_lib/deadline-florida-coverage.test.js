// Florida's coverage disclosure -- added 2026-08-31, on its own, as a fix to a
// gap and NOT as part of the citation audit that found it.
//
// THE GAP WAS WHERE THE DISCLOSURE LIVED, NOT WHETHER IT EXISTED. Florida's
// chief-justice hurricane limb has been documented since the jurisdiction was
// seeded -- in sql/sairnlaw_deadline_calendars_florida.json's authority.note,
// naming 2.514(a)(6)(B), (a)(1)(C) and (a)(3)(C) and calling it "Florida's
// HURRICANE MECHANISM". But an authority note is stored on the row. It is not
// returned to a caller. Every other disclosed jurisdiction rides its caveat on
// the compute response through JURISDICTION_COVERAGE; Florida did not, so a
// Florida answer arrived with no warning attached while thirteen others did.
//
// This file asserts the caveat now travels with the answer, and that adding it
// moved nothing else.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_florida.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_florida.json'), 'utf8'));

const calendars = {};
for (const row of cal.holiday_calendars) {
  calendars[row.jurisdiction] = calendars[row.jurisdiction] || {};
  calendars[row.jurisdiction][String(row.year)] = row.dates;
}

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}
function compute(triggerDate, extra) {
  return engine.computeDeadline(Object.assign({
    jurisdiction: 'fl', domain: 'civil-litigation',
    trigger_event: 'service_of_original_process_and_initial_pleading',
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}

// ── The entry exists and says what it must ───────────────────────────────
const cov = engine.JURISDICTION_COVERAGE.fl;
check('Florida now declares a coverage entry', !!cov, true);
check('it is incomplete and its error direction is EARLY',
  [cov.complete, cov.direction], [false, 'early']);
// All three places 2.514 reaches an emergency order, plus the two other
// unknowable sources in (a)(6)(B). Naming only the famous one would understate
// the gap.
check('it names ALL THREE subdivisions that reach a chief-justice order',
  [/\(a\)\(1\)\(C\)/.test(cov.detail), /\(a\)\(3\)\(C\)/.test(cov.detail),
   /\(a\)\(6\)\(B\)/.test(cov.detail)], [true, true, true]);
check('and the clerk\'s office and chief JUDGE limbs, which are not the same source',
  [/CLERK'S OFFICE/.test(cov.detail), /CHIEF JUDGE/.test(cov.detail),
   /per-circuit/.test(cov.detail)], [true, true, true]);
check('it names the mechanism plainly rather than by rule number alone',
  /HURRICANE MECHANISM/.test(cov.detail), true);
// The EARLY direction is conditional on the seed's shape, and the entry has to
// say so or it becomes a stale reassurance the moment a backward row lands.
check('it states the CONDITION under which EARLY holds, and what breaks it',
  [/EVERY SEEDED FLORIDA ROW IS FORWARD/.test(cov.detail),
   /STOPS BEING TRUE/.test(cov.detail),
   /2\.514\(a\)\(5\)/.test(cov.detail)], [true, true, true]);
check('it records the two gaps that touch no seeded row -- hours, and the split cut-off',
  [/HOURS arithmetic/.test(cov.detail), /11:59:59 p\.m\./.test(cov.detail)], [true, true]);

// ── The condition the entry relies on is TRUE of the seed, right now ─────
// If any of these three flips, the disclosure's direction claim is wrong and
// this test fails rather than the claim quietly becoming false.
check('every Florida row is forward',
  seed.rules.filter(r => (r.count || {}).direction === 'backward').map(r => r.rule_id), []);
check('no Florida row is stated in hours',
  seed.rules.filter(r => (r.count || {}).unit === 'hours').map(r => r.rule_id), []);
check('no Florida row is under the 7-day threshold at 2.514(a)(2)',
  seed.rules.filter(r => ((r.count || {}).value || 99) < 7).map(r => r.rule_id), []);

// ── The caveat actually travels with the answer ──────────────────────────
{
  const r = compute('2026-09-01');
  check('a successful Florida computation now carries the disclosure',
    [r.ok, !!r.coverage, r.coverage && r.coverage.direction], [true, true, 'early']);
  check('and the returned text names the chief justice',
    /chief justice/i.test((r.coverage || {}).summary || ''), true);
}

// ── Nothing else moved ───────────────────────────────────────────────────
check('the coverage table gained fl and nothing else',
  Object.keys(engine.JURISDICTION_COVERAGE).sort(),
  ['al', 'ar', 'de', 'fl', 'hi', 'id', 'ks', 'ma', 'md', 'mn', 'mo', 'ms', 'mt', 'ne', 'nh', 'nm', 'nv', 'ut', 'va', 'wi']);
// The standard itself is untouched -- this change is a disclosure, not a
// computation change, and the arithmetic must be identical.
const std = engine.COMPUTATION_STANDARDS.fl_rgpja_2514;
check('the Florida standard is unchanged -- shifted start, threshold 7, direction rule at (a)(5)',
  [std.label, std.shifted_start, std.short_period_exclusion_days, std.rollover_suffix_backward],
  ['Fla. R. Gen. Prac. & Jud. Admin. 2.514', true, 7, '(a)(5)']);
// A date that predates this change must still be the same date. Service on
// Tuesday 1 September 2026: 2.514(a)(1)(A)'s SHIFTED START makes Wednesday the
// 2nd day one, and nineteen more days land on Monday the 21st.
check('the arithmetic did not move: a 20-day answer from 1 September 2026',
  compute('2026-09-01').due_date, '2026-09-21');
check('and the Friday after Thanksgiving is still a Florida holiday',
  Object.fromEntries(calendars.fl['2026'].map(d => [d.date, true]))['2026-11-27'], true);

console.log((fail ? 'FAIL ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
