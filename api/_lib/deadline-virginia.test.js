// Virginia deadline rows -- isolated verification against the REAL engine and
// the REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Every expected date below was worked out BY HAND from the rule text before
// the engine was run, and the cases were chosen to land on the things that
// actually differ in Virginia rather than on convenient Tuesdays:
//
//   - the coverage DISCLOSURE for the 1-210(F)/local-closure gap (fails EARLY,
//     so it rides on the result instead of refusing it -- the opposite call
//     from Kentucky, which fails LATE and refuses)
//   - Va. Sup. Ct. R. 1:7, the engine's first TIME-OF-DAY service extension:
//     0 days at/before 5:00 p.m., 1 day after it, for the same method, and a
//     visible refusal rather than a guess when service_time is missing
//   - the 21/28 later-of pair on the discovery rows
//   - Election Day falling in an ODD year (2027), not just even ones
//   - the year-boundary calendar entry (2028's New Year's Day observed
//     2027-12-31, filed under 2027)
//
// Run: node api/_lib/deadline-virginia.test.js
'use strict';

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_virginia.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_virginia.json'), 'utf8'));

// Same shaping the endpoint does: flat rows -> { jurisdiction: { year: [...] } }
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

function compute(ruleId, triggerDate, extra) {
  const rule = seed.rules.find(r => r.rule_id === ruleId);
  if (!rule) throw new Error('no such rule: ' + ruleId);
  const triggerEvent = typeof rule.trigger_event === 'string' ? rule.trigger_event : rule.trigger_event.id;
  return engine.computeDeadline(Object.assign({
    jurisdiction: 'va', domain: rule.domain, trigger_event: triggerEvent,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── The seed's own shape ──────────────────────────────────────────────────
check('12 rules seeded', seed.rules.length, 12);
check('all rows are jurisdiction va', seed.rules.every(r => r.jurisdiction === 'va'), true);
check('every row uses va_code_1_210', seed.rules.every(r => r.computation === 'va_code_1_210'), true);
check('every rule id is unique', new Set(seed.rules.map(r => r.rule_id)).size, seed.rules.length);
check('every row cites a real quote and url',
  seed.rules.every(r => r.authority && r.authority.quote && r.authority.url), true);
check('exactly 3 rows carry the va_rule_1_7 service extension (the plain discovery limbs)',
  seed.rules.filter(r => r.service_extension && r.service_extension.standard === 'va_rule_1_7').length, 3);
check('no later_of row carries a service extension',
  seed.rules.filter(r => r.trigger_event && r.trigger_event.resolve_periods)
    .every(r => !r.service_extension), true);

// ── The standards themselves ────────────────────────────────────────────
check('va_code_1_210 declares NO short-period exclusion',
  engine.COMPUTATION_STANDARDS.va_code_1_210.short_period_exclusion_days, undefined);
check('va_code_1_210 defines the backward suffix, unlike NJ/NC/WA',
  engine.COMPUTATION_STANDARDS.va_code_1_210.rollover_suffix_backward, '(A)');
check('va_rule_1_7 sequences period-lengthening (add-then-roll), not federal after-expiry',
  engine.SERVICE_EXTENSION_STANDARDS.va_rule_1_7.sequence, 'add_to_period_then_roll');

// ── Coverage disclosure: the §1-210(F)/local-closure gap ───────────────────
// This is the whole point of DISCLOSING rather than refusing: a successful
// Virginia computation still returns ok:true, and the caveat rides alongside
// it rather than blocking it.
const disc = compute('va-r-3-8a-answer-to-complaint', '2026-05-01');
check('a Virginia computation still succeeds', disc.ok, true);
check('coverage is present and incomplete', disc.coverage && disc.coverage.complete, false);
check('coverage direction is early, never late', disc.coverage.direction, 'early');
check('coverage summary names the gap as EARLIER, never later',
  /EARLIER/.test(disc.coverage.summary) && !/never earlier/i.test(disc.coverage.summary), true);
check('coverage is null for a jurisdiction with no declared gap (West Virginia)',
  engine.JURISDICTION_COVERAGE.wv, undefined);

// ── The calendar: derivable-core checks ─────────────────────────────────
const va2026 = calendars.va['2026'].map(d => d.date);
const va2027 = calendars.va['2027'].map(d => d.date);
check('Independence Day 2026 (a Saturday) observes FRIDAY 3 July',
  va2026.includes('2026-07-03') && !va2026.includes('2026-07-04'), true);
check('Day after Thanksgiving is in the statute itself, not an add-on',
  va2026.includes('2026-11-27'), true);
check('Election Day falls in ODD year 2027, not just even years',
  va2027.includes('2027-11-02'), true);
check('the 2028 New Year holiday (observed on a Saturday) sits in the 2027 calendar',
  va2027.includes('2027-12-31') && !calendars.va['2028'].map(d => d.date).includes('2027-12-31'), true);
check('Columbus Day is a Virginia legal holiday (unlike NC and WA)',
  va2026.includes('2026-10-12'), true);

// ── Civil computations, hand-checked ────────────────────────────────────
// Served Fri 2026-05-01. +21 calendar days = Fri 2026-05-22, a business day,
// no roll needed.
check('R. 3:8(a) 21-day answer, landing on a business day',
  dateOf(compute('va-r-3-8a-answer-to-complaint', '2026-05-01')), '2026-05-22');

// Served Wed 2026-10-21. +21 = Wed 2026-11-11 = Veterans Day. §1-210(B) rolls
// to the next open day, Thu 2026-11-12.
check('R. 3:8(a) rolls off Veterans Day under §1-210(B)',
  dateOf(compute('va-r-3-8a-answer-to-complaint', '2026-10-21')), '2026-11-12');

// The answer to the complaint takes no extension: R. 1:7 reaches only service
// on counsel of record, and the summons is served on the defendant, who has
// none yet.
const noExt = compute('va-r-3-8a-answer-to-complaint', '2026-05-01', { service_method: 'mail' });
check('answer to the complaint: mail service adds nothing', noExt.due_date, '2026-05-22');
check('answer to the complaint: extension state is not_requested',
  noExt.service_extension.state, 'not_requested');

// A pre-2025-08-17 trigger selects no version of R. 3:8.
const old = compute('va-r-3-8a-answer-to-complaint', '2024-05-01');
check('a pre-currency trigger is refused, not computed', old.ok, false);

// A year with no loaded calendar refuses rather than treating it as empty.
const noCal = engine.computeDeadline({
  jurisdiction: 'va', domain: 'civil-litigation',
  trigger_event: 'service_of_summons_and_complaint', trigger_date: '2033-05-01',
  rules: seed.rules, calendars: calendars, as_of: '2033-05-01'
});
check('a year outside the loaded calendars refuses', noCal.code, 'NOT_PROVISIONED');

// ── The 21/28 later-of pair on discovery ────────────────────────────────
// Interrogatories served WITH the complaint, both 2026-05-01: limb A (21
// days from interrogatories) ends 2026-05-22, limb B (28 days from the
// complaint) ends 2026-05-29. The 28-day floor governs.
{
  const r = engine.computeDeadline({
    jurisdiction: 'va', domain: 'civil-litigation',
    trigger_event: 'interrogatories_on_defendant',
    trigger_dates: {
      service_of_interrogatories_on_defendant: '2026-05-01',
      service_of_summons_and_complaint_for_interrogatories: '2026-05-01'
    },
    rules: seed.rules, calendars: calendars, as_of: '2026-05-01'
  });
  check('interrogatories served with the complaint: the 28-day floor governs', dateOf(r), '2026-05-29');
  check('the 28-day limb is recorded as governing',
    r.steps[0].detail.indexOf('2026-05-29 <- governs') !== -1, true);
}
// Interrogatories served three weeks after the complaint: limb A (21 days
// from 2026-05-22) ends 2026-06-12, limb B (28 days from 2026-05-01) ends
// 2026-05-29. The 21-day period governs because it now runs later.
{
  const r = engine.computeDeadline({
    jurisdiction: 'va', domain: 'civil-litigation',
    trigger_event: 'interrogatories_on_defendant',
    trigger_dates: {
      service_of_interrogatories_on_defendant: '2026-05-22',
      service_of_summons_and_complaint_for_interrogatories: '2026-05-01'
    },
    rules: seed.rules, calendars: calendars, as_of: '2026-05-22'
  });
  check('interrogatories served three weeks in: the 21-day period governs', dateOf(r), '2026-06-12');
  check('the 21-day limb is recorded as governing',
    r.steps[0].detail.indexOf('2026-06-12 <- governs') !== -1, true);
}
// The plain (non-defendant) interrogatory row carries the extension; the
// later-of row deliberately does not.
check('the plain interrogatory row carries the va_rule_1_7 extension',
  seed.rules.find(r => r.rule_id === 'va-r-4-8d-interrogatory-answers').service_extension.standard,
  'va_rule_1_7');
check('the later-of interrogatory row carries no extension',
  seed.rules.find(r => r.rule_id === 'va-r-4-8d-interrogatory-answers-defendant-later-of-periods').service_extension,
  undefined);

// ── Va. Sup. Ct. R. 1:7: the time-of-day service extension ─────────────
// Interrogatories served Fri 2026-05-01. +21 = Fri 2026-05-22, unrolled.
const R17_RULE = 'va-r-4-8d-interrogatory-answers';

// Manual delivery at or before 5:00 p.m. adds nothing.
check('manual delivery at 16:00 adds nothing',
  compute(R17_RULE, '2026-05-01', { service_method: 'manual_delivery', service_time: '16:00' }).due_date,
  '2026-05-22');
check('manual delivery at exactly 17:00 (the boundary) still adds nothing',
  compute(R17_RULE, '2026-05-01', { service_method: 'manual_delivery', service_time: '17:00' }).due_date,
  '2026-05-22');
{
  const r = compute(R17_RULE, '2026-05-01', { service_method: 'manual_delivery', service_time: '16:00' });
  check('manual delivery at 16:00: extension state is applied with 0 days',
    [r.service_extension.state, r.service_extension.days_added], ['applied', 0]);
}

// After 5:00 p.m.: one day added, then rolled. 2026-05-22 + 1 = 2026-05-23
// (Saturday) -> rolls through Sunday 05-24 and Memorial Day 05-25 -> Tue 05-26.
check('manual delivery at 17:01 adds one day, then rolls off the holiday weekend',
  dateOf(compute(R17_RULE, '2026-05-01', { service_method: 'manual_delivery', service_time: '17:01' })),
  '2026-05-26');
check('facsimile at 20:15 (after 5pm, before midnight) also adds one day',
  dateOf(compute(R17_RULE, '2026-05-01', { service_method: 'facsimile', service_time: '20:15' })),
  '2026-05-26');
check('electronic mail at 23:59 also adds one day',
  dateOf(compute(R17_RULE, '2026-05-01', { service_method: 'electronic_mail', service_time: '23:59' })),
  '2026-05-26');

// Fixed amounts, no clock needed.
check('mail always adds three days regardless of time of day',
  dateOf(compute(R17_RULE, '2026-05-01', { service_method: 'mail' })), '2026-05-26');
check('commercial delivery for NEXT-DAY service always adds one day',
  dateOf(compute(R17_RULE, '2026-05-01', { service_method: 'commercial_delivery_next_day' })), '2026-05-26');
check('commercial delivery for SAME-DAY service follows the clock like manual delivery',
  compute(R17_RULE, '2026-05-01', { service_method: 'commercial_delivery_same_day', service_time: '16:00' }).due_date,
  '2026-05-22');

// A bare 'commercial_delivery' is not one of the six named methods.
check('a bare "commercial_delivery" does not qualify (the rule splits by service bought)',
  compute(R17_RULE, '2026-05-01', { service_method: 'commercial_delivery' }).service_extension.state,
  'not_qualifying');

// Missing or malformed service_time REFUSES rather than guessing, and leaves
// the unextended date in place.
{
  const r = compute(R17_RULE, '2026-05-01', { service_method: 'manual_delivery' });
  check('missing service_time refuses visibly', r.service_extension.state, 'refused_missing_context');
  check('a refused extension still returns the unextended date', r.due_date, '2026-05-22');
}
{
  const r = compute(R17_RULE, '2026-05-01', { service_method: 'facsimile', service_time: '5:00 PM' });
  check('a non-24-hour service_time is refused, not parsed leniently', r.service_extension.state, 'refused_missing_context');
}

// ── The new context argument must not reach any other jurisdiction ─────
// amount() now receives (method, ctx); every pre-Virginia standard's amount()
// must still behave exactly as before with the extra argument present.
{
  const ncSeed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_northcarolina.json'), 'utf8'));
  const ncCal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_northcarolina.json'), 'utf8'));
  const nc = {};
  for (const row of ncCal.holiday_calendars) {
    nc[row.jurisdiction] = nc[row.jurisdiction] || {};
    nc[row.jurisdiction][String(row.year)] = row.dates;
  }
  // Served Fri 2026-05-01, +30 = Sun 2026-05-31, +3 mail (add-then-roll) =
  // Wed 2026-06-03, a business day.
  const r = engine.computeDeadline({
    jurisdiction: 'nc', domain: 'civil-litigation',
    trigger_event: 'service_of_pleading_stating_crossclaim', trigger_date: '2026-05-01',
    service_method: 'mail', rules: ncSeed.rules, calendars: nc, as_of: '2026-05-01'
  });
  check('North Carolina 6(e) mail extension still computes unchanged through amount(method, ctx)',
    dateOf(r), '2026-06-03');
  check('North Carolina result carries no coverage disclosure', r.coverage, null);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
