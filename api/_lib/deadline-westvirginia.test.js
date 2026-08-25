// West Virginia deadline rows -- isolated verification against the REAL engine
// and the REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Every expected date below was worked out BY HAND from the rule text and the
// W. Va. Code 2-2-1 holiday list before the engine was run, and the cases were
// chosen to land on the things that actually differ in West Virginia rather
// than on convenient Tuesdays:
//
//   - the 2025 restyling's removal of the short-period exclusion (the 7-day
//     reply-memorandum row, which under the FORMER rule would have skipped
//     weekends and does not now)
//   - the both-way weekend shift in 2-2-1(b), including a holiday observed on
//     the preceding FRIDAY, which no other jurisdiction in this engine does
//   - backward counting under Rule 6(a)(5)
//   - the contested Rule 6(e) cross-reference, which must REFUSE rather than
//     silently decline
//   - the appellate standard's short-period exclusion, which the civil one
//     does not have
//
// Run: node api/_lib/deadline-westvirginia.test.js
'use strict';

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_westvirginia.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_westvirginia.json'), 'utf8'));

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
  return engine.computeDeadline(Object.assign({
    jurisdiction: 'wv', domain: rule.domain, trigger_event: rule.trigger_event,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── The seed's own shape ──────────────────────────────────────────────────
check('17 rules seeded', seed.rules.length, 17);
check('all rows are jurisdiction wv', seed.rules.every(r => r.jurisdiction === 'wv'), true);
check('civil rows use wv_rcp_6a',
  seed.rules.filter(r => r.domain === 'civil-litigation').every(r => r.computation === 'wv_rcp_6a'), true);
check('appellate rows use wv_rap_39a',
  seed.rules.filter(r => r.domain === 'appellate').every(r => r.computation === 'wv_rap_39a'), true);
check('every rule id is unique',
  new Set(seed.rules.map(r => r.rule_id)).size, seed.rules.length);
check('no appellate row carries a service extension (R. App. P. 39(c) carve-out)',
  seed.rules.filter(r => r.domain === 'appellate').some(r => r.service_extension), false);
check('every extending row lists only the two uncontested methods',
  seed.rules.filter(r => r.service_extension)
    .every(r => JSON.stringify(r.service_extension.applies_when) === JSON.stringify(['mail', 'left_with_clerk'])), true);
check('every row cites a real quote and url',
  seed.rules.every(r => r.authority && r.authority.quote && r.authority.url), true);

// ── The standards themselves ──────────────────────────────────────────────
check('civil standard declares NO short-period exclusion (the 2025 change)',
  engine.COMPUTATION_STANDARDS.wv_rcp_6a.short_period_exclusion_days, undefined);
check('appellate standard declares a 7-day short-period exclusion',
  engine.COMPUTATION_STANDARDS.wv_rap_39a.short_period_exclusion_days, 7);
check('civil standard cites the backward subsection Rule 6(a)(5) really has',
  engine.COMPUTATION_STANDARDS.wv_rcp_6a.rollover_suffix_backward, '(5)');
check('appellate standard leaves backward blank (39(a) is forward-only)',
  engine.COMPUTATION_STANDARDS.wv_rap_39a.rollover_suffix_backward, '');
check('6(e) sequences the FEDERAL way after the 2025 restyling',
  engine.SERVICE_EXTENSION_STANDARDS.wv_rcp_6e.sequence, 'roll_then_add_then_roll');

// ── The calendar: the both-way shift, and the year-boundary entry ─────────
const wv2026 = calendars.wv['2026'].map(d => d.date);
check('West Virginia Day 2026 is observed FRIDAY 19 June (20 June is a Saturday)',
  wv2026.includes('2026-06-19') && !wv2026.includes('2026-06-20'), true);
check('Independence Day 2026 is observed FRIDAY 3 July',
  wv2026.includes('2026-07-03') && !wv2026.includes('2026-07-04'), true);
check("Lincoln's Day 2026 is the day after Thanksgiving, not 12 February",
  wv2026.includes('2026-11-27') && !wv2026.includes('2026-02-12'), true);
check('Juneteenth is NOT in the civil list as its own holiday in 2027',
  calendars.wv['2027'].map(d => d.date).includes('2027-06-19'), false);
check('the 2028 New Year holiday sits in the 2027 calendar, not the 2028 one',
  calendars.wv['2027'].map(d => d.date).includes('2027-12-31') &&
  !calendars.wv['2028'].map(d => d.date).includes('2027-12-31'), true);
check('even years carry the statewide primary and general election days',
  calendars.wv['2026'].filter(d => /election/i.test(d.name)).map(d => d.date),
  ['2026-05-12', '2026-11-03']);
check('odd years carry none', calendars.wv['2027'].some(d => /election/i.test(d.name)), false);

// ── Civil computations, hand-checked ─────────────────────────────────────
// Served Fri 2026-05-01. +30 calendar days = Sun 2026-05-31 -> rolls to Mon
// 2026-06-01. Nothing intermediate matters: the 2025 rule counts every day.
check('12(a)(1)(A) 30-day answer, landing on a Sunday, rolls to Monday',
  dateOf(compute('wv-rcp-12-a1A-answer-to-complaint', '2026-05-01')), '2026-06-01');

// Served Mon 2026-06-01. +30 = Wed 2026-07-01. Independence Day observed
// Fri 2026-07-03 is INTERMEDIATE and is counted, not skipped -- the 2025 rule
// has no short-period exclusion and this period is long anyway.
check('12(a)(1)(A) counts an intermediate observed holiday',
  dateOf(compute('wv-rcp-12-a1A-answer-to-complaint', '2026-06-01')), '2026-07-01');

// The answer to the COMPLAINT takes no extension (Rule 4 service, not Rule 5).
const noExt = compute('wv-rcp-12-a1A-answer-to-complaint', '2026-05-01', { service_method: 'mail' });
check('answer to the complaint: mail service adds nothing', noExt.due_date, '2026-06-01');
check('answer to the complaint: extension state is not_requested',
  noExt.service_extension.state, 'not_requested');

// The answer to a COUNTERCLAIM does take it. Served Fri 2026-05-01, +30 =
// Sun 2026-05-31, roll -> Mon 2026-06-01, +3 = Thu 2026-06-04. Federal order.
const cc = compute('wv-rcp-12-a1B-answer-to-counterclaim-or-crossclaim', '2026-05-01', { service_method: 'mail' });
check('12(a)(1)(B) by mail: roll first, then add 3 (2025 sequencing)', cc.due_date, '2026-06-04');
check('12(a)(1)(B) by mail: 3 days recorded', cc.service_extension.days_added, 3);
check('12(a)(1)(B) by mail: state is applied', cc.service_extension.state, 'applied');

// THE CONTESTED METHODS. Both must refuse visibly and add nothing.
for (const m of ['other_electronic_means_consented', 'other_means_consented']) {
  const r = compute('wv-rcp-12-a1B-answer-to-counterclaim-or-crossclaim', '2026-05-01', { service_method: m });
  check('6(e) refuses "' + m + '" visibly', r.service_extension.state, 'refused_contested_standard');
  check('6(e) adds nothing for "' + m + '"', r.service_extension.days_added, 0);
  check('6(e) still returns the unextended date for "' + m + '"', r.due_date, '2026-06-01');
}
// A method neither reading reaches is a plain non-qualifier, NOT a refusal --
// the two states must stay distinguishable.
const efile = compute('wv-rcp-12-a1B-answer-to-counterclaim-or-crossclaim', '2026-05-01', { service_method: 'wv_efiling' });
check('e-filed service does not qualify and is NOT reported as contested',
  efile.service_extension.state, 'not_qualifying');

// THE 7-DAY REPLY MEMORANDUM -- the row the 2025 change actually moves.
// Served Wed 2026-05-20, +7 calendar days = Wed 2026-05-27. Under the FORMER
// rule ("fewer than 11 days") the intervening Sat/Sun and Memorial Day Mon
// 2026-05-25 would have been skipped, landing Tue 2026-06-02.
check('6(d)(3) reply: 7 days counts every day, including Memorial Day weekend',
  dateOf(compute('wv-rcp-6-d3-reply-memorandum', '2026-05-20')), '2026-05-27');

// BACKWARD. Hearing Wed 2026-07-08, less 14 days = Wed 2026-06-24, a business
// day, no roll needed. Hearing Mon 2026-07-20 less 14 = Mon 2026-07-06.
check('6(d)(1) notice counts backward from the hearing',
  dateOf(compute('wv-rcp-6-d1-motion-and-notice-of-hearing', '2026-07-08')), '2026-06-24');
// Hearing Fri 2026-07-17, less 14 = Fri 2026-07-03 = Independence Day
// OBSERVED. Rule 6(a)(5) rolls a backward period BACKWARD, so the notice is
// due EARLIER, Thu 2026-07-02 -- never later, which would shorten the notice.
check('6(d)(1) backward landing on an observed holiday rolls EARLIER',
  dateOf(compute('wv-rcp-6-d1-motion-and-notice-of-hearing', '2026-07-17')), '2026-07-02');
// Hearing Mon 2026-06-29, less 7 = Mon 2026-06-22. Hearing Fri 2026-06-26,
// less 7 = Fri 2026-06-19 = West Virginia Day observed -> back to Thu 06-18.
check('6(d)(2) backward landing on West Virginia Day observed rolls EARLIER',
  dateOf(compute('wv-rcp-6-d2-opposing-affidavit', '2026-06-26')), '2026-06-18');

// The two Rule 34 limbs are separate triggers, not a later-of.
check('34(b)(2)(A) ordinary limb runs from service',
  dateOf(compute('wv-rcp-34-b2A-production-response', '2026-03-02')), '2026-04-01');
check('34(b)(2)(A) early-delivery limb runs from the Rule 26(f) conference',
  dateOf(compute('wv-rcp-34-b2A-production-response-early-delivery', '2026-03-02')), '2026-04-01');
const early = compute('wv-rcp-34-b2A-production-response-early-delivery', '2026-03-02', { service_method: 'mail' });
check('early-delivery limb takes no extension (it runs from a conference)',
  early.service_extension.state, 'not_requested');

// ── Appellate computations ───────────────────────────────────────────────
// Entered Fri 2026-05-01, +30 = Sun 2026-05-31 -> Mon 2026-06-01.
check('R. App. P. 5(b) 30-day notice of appeal',
  dateOf(compute('wv-rap-5-b-notice-of-appeal', '2026-05-01')), '2026-06-01');
// Mail service must not extend a docketing deadline -- 39(c) says so, and the
// row carries no service_extension at all, so the state is not_requested.
const app = compute('wv-rap-5-b-notice-of-appeal', '2026-05-01', { service_method: 'mail' });
check('notice of appeal: mail adds nothing (39(c) docketing carve-out)', app.due_date, '2026-06-01');
// Four months by anniversary. Entered 2026-05-01 -> 2026-09-01 (a Tuesday;
// Labor Day 2026 is Mon 09-07, so no roll).
check('R. App. P. 5(f) four months by anniversary date',
  dateOf(compute('wv-rap-5-f-perfect-appeal', '2026-05-01')), '2026-09-01');
// Entered 2026-10-31 -> 2027-02-28 by end-of-month clamping (2027 is not a
// leap year), a Sunday, rolling to Mon 2027-03-01.
check('R. App. P. 5(f) clamps to end of month, then rolls',
  dateOf(compute('wv-rap-5-f-perfect-appeal', '2026-10-31')), '2027-03-01');
// 20 days from filing. Filed Mon 2026-06-01 -> Sun 2026-06-21 -> Mon 06-22.
check('R. App. P. 5(c) 20-day notice of continuing interest',
  dateOf(compute('wv-rap-5-c-notice-of-continuing-interest', '2026-06-01')), '2026-06-22');

// ── Refusals that must stay refusals ─────────────────────────────────────
// A trigger before the restyled rules took effect selects no version.
const old = compute('wv-rcp-12-a1A-answer-to-complaint', '2024-05-01');
check('a pre-2025 civil trigger is refused, not computed', old.ok, false);
// A year with no calendar must refuse rather than treat the year as empty.
const noCal = engine.computeDeadline({
  jurisdiction: 'wv', domain: 'civil-litigation',
  trigger_event: 'service_of_summons_and_complaint', trigger_date: '2032-05-01',
  rules: seed.rules, calendars: calendars, as_of: '2032-05-01'
});
check('a year outside the loaded calendars refuses', noCal.code, 'NOT_PROVISIONED');

// ── The new engine branch must not reach any other jurisdiction ──────────
// `contested` is checked before qualifies() for every standard, so the guard
// that keeps it West Virginia-only is that no other standard declares it.
// Asserted rather than assumed, because this is the whole blast radius of the
// engine change and there is no other suite covering the deadline standards.
check('wv_rcp_6e is the ONLY standard declaring a contested predicate',
  Object.keys(engine.SERVICE_EXTENSION_STANDARDS)
    .filter(k => typeof engine.SERVICE_EXTENSION_STANDARDS[k].contested === 'function'),
  ['wv_rcp_6e']);

// A pre-existing jurisdiction still computes what it computed, through the
// same code path the new branch was inserted into. Georgia's 30-day answer
// from Fri 2026-05-01 lands Sun 2026-05-31 and rolls to Mon 2026-06-01 under
// O.C.G.A. 1-3-1(d)(3); mail service adds nothing, because 9-11-6(e) reaches
// only papers "other than process".
{
  const gaSeed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_georgia.json'), 'utf8'));
  const gaCal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_georgia.json'), 'utf8'));
  const gc = {};
  for (const row of gaCal.holiday_calendars) {
    gc[row.jurisdiction] = gc[row.jurisdiction] || {};
    gc[row.jurisdiction][String(row.year)] = row.dates;
  }
  const r = engine.computeDeadline({
    jurisdiction: 'ga', domain: 'civil-litigation',
    trigger_event: 'service_of_summons_and_complaint', trigger_date: '2026-05-01',
    service_method: 'mail', rules: gaSeed.rules, calendars: gc, as_of: '2026-05-01'
  });
  check('Georgia still computes unchanged through the modified extension path',
    dateOf(r), '2026-06-01');
  check('Georgia mail service is still not_requested, not mislabelled contested',
    r.service_extension.state, 'not_requested');
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
