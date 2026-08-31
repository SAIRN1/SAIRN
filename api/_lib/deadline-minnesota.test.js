// Minnesota deadline rows -- isolated verification against the REAL engine and
// the REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Every expected date below was worked out BY HAND from the rule text and the
// Minn. Stat. 645.44 subd. 5 holiday list BEFORE the engine was run, and the
// cases target what actually differs in Minnesota:
//
//   - NO short-period exclusion at all (days are days), where six seeded states
//     use 7 and three use 11 -- the field must be ABSENT, not a number
//   - the ENUMERATED both-ways shift, applied to five named days only, and the
//     YEAR-BOUNDARY SPILL it produces that Sunday-only states cannot
//   - INDIGENOUS PEOPLES DAY, encoded on the postal limb rather than the branch
//     option, which is the one inference in this jurisdiction
//   - R. 6.01(e)'s NEGATIVE-CONDITION extension: +3 for mail, +1 for anything
//     else after 5 p.m., and 0 for anything else before it
//   - production having NO defendant floor where interrogatories and admissions
//     both do
//
// Run: node api/_lib/deadline-minnesota.test.js
'use strict';

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_minnesota.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_minnesota.json'), 'utf8'));

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
  const ev = typeof rule.trigger_event === 'string' ? rule.trigger_event : rule.trigger_event.id;
  return engine.computeDeadline(Object.assign({
    jurisdiction: 'mn', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── The seed's own shape ──────────────────────────────────────────────────
check('11 rules seeded', seed.rules.length, 11);
check('all rows are jurisdiction mn', seed.rules.every(r => r.jurisdiction === 'mn'), true);
check('every row uses mn_rcp_6_01', seed.rules.every(r => r.computation === 'mn_rcp_6_01'), true);
check('every rule id is unique', new Set(seed.rules.map(r => r.rule_id)).size, seed.rules.length);
check('every row cites a real quote and url',
  seed.rules.every(r => r.authority && r.authority.quote && r.authority.url), true);
// THE EXTENSION IS A NEGATIVE CONDITION, so no row may carry applies_when --
// listing methods would narrow a rule that names none.
check('no extending row carries applies_when (the rule names no methods)',
  seed.rules.filter(r => r.service_extension)
    .every(r => r.service_extension.applies_when === undefined), true);
check('no row carries a service_completion (Minnesota has no completion rule)',
  seed.rules.some(r => r.service_completion), false);
check('only the answer-to-summons row lacks the extension (Rule 4 service)',
  seed.rules.filter(r => !r.service_extension && typeof r.trigger_event === 'string')
    .map(r => r.rule_id), ['mn-r-12-01-answer-to-summons']);
// EXACTLY TWO later_of rows -- production grants no defendant floor.
check('exactly two later_of rows -- interrogatories and admissions, NOT production',
  seed.rules.filter(r => r.trigger_event && r.trigger_event.resolve_periods).map(r => r.rule_id),
  ['mn-r-33-01b-interrogatory-answers-defendant-later-of-periods',
   'mn-r-36-01-admission-response-defendant-later-of-periods']);
check('both later_of rows use the 30/45 pair',
  seed.rules.filter(r => r.trigger_event && r.trigger_event.resolve_periods)
    .map(r => r.trigger_event.limbs.map(L => L.count.value)), [[30, 45], [30, 45]]);

// ── The standards ─────────────────────────────────────────────────────────
// THE MOST IMPORTANT ASSERTION IN THIS FILE. Six seeded states use 7 and three
// use 11; Minnesota must have NO exclusion at all. A number here would push
// every short Minnesota deadline LATER than the rule provides.
check('mn_rcp_6_01 declares NO short-period exclusion (days are days)',
  engine.COMPUTATION_STANDARDS.mn_rcp_6_01.short_period_exclusion_days, undefined);
check('mn_rcp_6_01 defines the backward suffix (R. 6.01(c))',
  engine.COMPUTATION_STANDARDS.mn_rcp_6_01.rollover_suffix_backward, '(c)');
check('mn_rcp_6_01_e lengthens the period',
  engine.SERVICE_EXTENSION_STANDARDS.mn_rcp_6_01_e.sequence, 'add_to_period_then_roll');
// qualifies() must be true for EVERYTHING -- the rule reaches the complement of
// mail, not an enumerated set.
check('mn_rcp_6_01_e qualifies every method, including ones no rule names',
  ['mail', 'email', 'facsimile', 'efiling_service', 'personal_delivery', 'left_with_clerk']
    .filter(m => engine.SERVICE_EXTENSION_STANDARDS.mn_rcp_6_01_e.qualifies(m)).length, 6);
{
  const amt = engine.SERVICE_EXTENSION_STANDARDS.mn_rcp_6_01_e.amount;
  check('mail gets three days with no clock', amt('mail', {}).add, 3);
  check('non-mail at 16:59 gets nothing', amt('email', { service_time: '16:59' }).add, 0);
  check('non-mail at exactly 17:00 gets nothing -- NOT "after 5:00 p.m."',
    amt('email', { service_time: '17:00' }).add, 0);
  check('non-mail at 17:01 gets one day', amt('email', { service_time: '17:01' }).add, 1);
  // No midnight ceiling: Minnesota measures against the day of service, so a
  // 23:59 transmission still gets its one day. Missouri and Virginia both stop
  // at midnight; this one does not need to.
  check('non-mail at 23:59 still gets one day -- no midnight ceiling',
    amt('facsimile', { service_time: '23:59' }).add, 1);
  check('non-mail with no service_time refuses', !!amt('email', {}).refuse, true);
}

// ── Coverage disclosure ──────────────────────────────────────────────────
const disc = compute('mn-r-12-01-answer-to-summons', '2026-05-01');
check('a Minnesota computation still succeeds', disc.ok, true);
check('coverage is present and incomplete', disc.coverage && disc.coverage.complete, false);
check('coverage direction is early', disc.coverage.direction, 'early');
// This entry is unlike the other three: it also discloses an INFERENCE whose
// error direction is LATE. That honesty is the thing being pinned here.
check('coverage discloses the Indigenous Peoples Day reading as an inference',
  /reading of the rule and not a quoted holding/i.test(disc.coverage.detail), true);
check('coverage warns the inference could run LATE',
  /could be LATE|be LATE/i.test(disc.coverage.summary), true);
check('coverage names the Friday after Thanksgiving as the safe-default omission',
  /FRIDAY AFTER THANKSGIVING/i.test(disc.coverage.detail), true);

// ── The calendar ─────────────────────────────────────────────────────────
const mn26 = calendars.mn['2026'].map(d => d.date);
const mn27 = calendars.mn['2027'].map(d => d.date);
check('11 holidays in 2026', mn26.length, 11);
check('INDIGENOUS PEOPLES DAY 2026 is Monday 12 October', mn26.includes('2026-10-12'), true);
// THE ENUMERATED BOTH-WAYS SHIFT. 4 July 2026 is a SATURDAY and 645.44 names
// Independence Day in its shift proviso, so it moves BACK to Friday 3 July.
// Massachusetts and Missouri would leave it on the Saturday.
check('Independence Day 2026 (a Saturday) shifts BACK to Friday 3 July',
  mn26.includes('2026-07-03') && !mn26.includes('2026-07-04'), true);
// 4 July 2027 is a SUNDAY, so it moves FORWARD to Monday 5 July. Both
// directions, from one proviso.
check('Independence Day 2027 (a Sunday) shifts FORWARD to Monday 5 July',
  mn27.includes('2027-07-05') && !mn27.includes('2027-07-04'), true);
// THE YEAR-BOUNDARY SPILL. 1 January 2028 is a Saturday, so the holiday is the
// PRECEDING day -- Friday 31 December 2027, which belongs to the 2027 calendar.
// A Sunday-only state cannot produce this; the generator's own assertion caught
// it when the Massachusetts/Missouri check was carried over.
check('New Year 2028 observed lands in the 2027 calendar, on 31 December 2027',
  mn27.includes('2027-12-31'), true);
check('and it is NOT also filed under 2028',
  calendars.mn['2028'].map(d => d.date).includes('2027-12-31'), false);
check('no calendar entry falls on a weekend (the shift is both ways)',
  Object.keys(calendars.mn).every(y => calendars.mn[y].every(d => {
    const w = new Date(d.date + 'T00:00:00Z').getUTCDay(); return w !== 0 && w !== 6;
  })), true);
// The Friday after Thanksgiving must be ABSENT -- the safe default.
check('the Friday after Thanksgiving 2026 (27 Nov) is NOT encoded',
  mn26.includes('2026-11-27'), false);

// ── Computations, hand-checked ───────────────────────────────────────────
// Fri 2026-05-01 +21 = Fri 2026-05-22, a business day.
check('R. 12.01 21-day answer', dateOf(compute('mn-r-12-01-answer-to-summons', '2026-05-01')), '2026-05-22');
// Mon 2026-09-21 +21 = Mon 2026-10-12 = INDIGENOUS PEOPLES DAY -> Tue 10-13.
// No other jurisdiction in this engine has a holiday on that date, so nothing
// else could produce this roll.
check('R. 12.01 rolls off INDIGENOUS PEOPLES DAY',
  dateOf(compute('mn-r-12-01-answer-to-summons', '2026-09-21')), '2026-10-13');
// Fri 2026-06-12 +21 = Fri 2026-07-03 = Independence Day OBSERVED (shifted back
// from Saturday 4 July) -> Mon 2026-07-06. Proves the backward limb of the
// enumerated shift is live in the calendar.
check('R. 12.01 rolls off the BACK-SHIFTED Independence Day observance',
  dateOf(compute('mn-r-12-01-answer-to-summons', '2026-06-12')), '2026-07-06');
// The answer to the summons takes no extension: Rule 4 service.
{
  const r = compute('mn-r-12-01-answer-to-summons', '2026-05-01', { service_method: 'mail' });
  check('answer to the summons: mail adds nothing', r.due_date, '2026-05-22');
  check('answer to the summons: state is not_requested', r.service_extension.state, 'not_requested');
}

// ── The negative-condition extension, live through the engine ────────────
// Cross-claim served Fri 2026-05-01: +21 = Fri 2026-05-22.
const XC = 'mn-r-12-01-answer-to-crossclaim';
check('cross-claim by mail: +3 -> Mon 2026-05-25 is MEMORIAL DAY -> Tue 05-26',
  dateOf(compute(XC, '2026-05-01', { service_method: 'mail' })), '2026-05-26');
check('cross-claim by e-mail before 5pm: adds nothing',
  dateOf(compute(XC, '2026-05-01', { service_method: 'email', service_time: '16:00' })), '2026-05-22');
check('cross-claim by e-mail after 5pm: +1 -> Sat 05-23 -> rolls to Tue 05-26 past Memorial Day',
  dateOf(compute(XC, '2026-05-01', { service_method: 'email', service_time: '17:30' })), '2026-05-26');
// A method NO rule anywhere enumerates must still be reached -- that is the
// whole point of a negative condition.
check('a method no rule enumerates is still extended after 5pm',
  dateOf(compute(XC, '2026-05-01', { service_method: 'personal_delivery', service_time: '18:00' })),
  '2026-05-26');
check('...and adds nothing before 5pm',
  dateOf(compute(XC, '2026-05-01', { service_method: 'personal_delivery', service_time: '09:00' })),
  '2026-05-22');
{
  const r = compute(XC, '2026-05-01', { service_method: 'email', service_time: '16:00' });
  check('a 0-day extension reports as APPLIED, not not_qualifying',
    [r.service_extension.state, r.service_extension.days_added], ['applied', 0]);
}
// Missing service_time on a non-mail method: SOFT refusal, date still returned.
{
  const r = compute(XC, '2026-05-01', { service_method: 'email' });
  check('non-mail with no service_time refuses SOFTLY and still returns a date',
    [r.ok, r.service_extension.state, r.due_date], [true, 'refused_missing_context', '2026-05-22']);
}
// Mail needs no clock at all.
check('mail needs no service_time', compute(XC, '2026-05-01', { service_method: 'mail' }).ok, true);

// ── Discovery ────────────────────────────────────────────────────────────
// Fri 2026-05-01 +30 = Sun 2026-05-31 -> Mon 2026-06-01.
check('R. 33.01(b) 30-day interrogatory answers roll off a Sunday',
  dateOf(compute('mn-r-33-01b-interrogatory-answers', '2026-05-01')), '2026-06-01');
check('R. 34.02(c)(1) 30-day production response',
  dateOf(compute('mn-r-34-02c1-production-response', '2026-05-01')), '2026-06-01');
check('R. 36.01 30-day admission response',
  dateOf(compute('mn-r-36-01-admission-response', '2026-05-01')), '2026-06-01');
// The 30/45 floors. Served with the summons and complaint, both 2026-05-01:
// 30-day limb ends 05-31, 45-day limb ends Mon 2026-06-15. The floor governs.
function floorCase(tid, evA, evB) {
  const t = {}; t[evA] = '2026-05-01'; t[evB] = '2026-05-01';
  return dateOf(engine.computeDeadline({
    jurisdiction: 'mn', domain: 'civil-litigation', trigger_event: tid,
    trigger_dates: t, rules: seed.rules, calendars: calendars, as_of: '2026-05-01'
  }));
}
check('interrogatories defendant floor is 45 days',
  floorCase('interrogatories_on_defendant', 'service_of_interrogatories_on_defendant',
    'service_of_summons_and_complaint_for_interrogatories'), '2026-06-15');
check('admissions defendant floor is also 45 -- Minnesota is internally consistent, unlike Missouri',
  floorCase('admission_request_on_defendant', 'service_of_request_for_admission_on_defendant',
    'service_of_summons_and_complaint_for_admission'), '2026-06-15');
// PRODUCTION HAS NO FLOOR. There is no such trigger to call.
check('production grants NO defendant floor -- no such rule exists',
  compute('mn-r-34-02c1-production-response', '2026-05-01') &&
  seed.rules.some(r => r.rule_id === 'mn-r-34-02c1-production-response-defendant-later-of-periods'),
  false);

// ── Refusals that must stay refusals ─────────────────────────────────────
check('a pre-2020 trigger is refused, not computed',
  compute('mn-r-12-01-answer-to-summons', '2019-05-01').ok, false);
check('a year outside the loaded calendars refuses',
  compute('mn-r-12-01-answer-to-summons', '2033-05-01').code, 'NOT_PROVISIONED');

// ── Blast radius ─────────────────────────────────────────────────────────
check('four jurisdictions declare a coverage gap',
  Object.keys(engine.JURISDICTION_COVERAGE).sort(), ['al', 'ar', 'fl', 'hi', 'id', 'ks', 'ma', 'md', 'mn', 'mo', 'ms', 'ne', 'nm', 'va', 'wi']);
check('Missouri is still the only jurisdiction with a completion standard',
  Object.keys(engine.SERVICE_COMPLETION_STANDARDS), ['mo_rule_43_01_d']);
// A pre-existing jurisdiction must be untouched by the new standards.
{
  const moSeed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_missouri.json'), 'utf8'));
  const moCal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_missouri.json'), 'utf8'));
  const mc = {};
  for (const row of moCal.holiday_calendars) {
    mc[row.jurisdiction] = mc[row.jurisdiction] || {};
    mc[row.jurisdiction][String(row.year)] = row.dates;
  }
  const r = engine.computeDeadline({
    jurisdiction: 'mo', domain: 'civil-litigation', trigger_event: 'service_of_interrogatories',
    trigger_date: '2026-05-01', service_method: 'email', service_time: '17:01',
    rules: moSeed.rules, calendars: mc, as_of: '2026-05-01'
  });
  check('Missouri e-mail after 5pm still SHIFTS the trigger and adds nothing',
    [r.trigger_date, r.service_extension.days_added, r.service_completion.state],
    ['2026-05-04', 0, 'shifted']);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
