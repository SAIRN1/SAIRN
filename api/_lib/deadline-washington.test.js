// Washington deadline rows -- isolated verification against the REAL engine and
// the REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Expected dates were worked out BY HAND from the rule text and RCW 1.16.050
// before the engine was run, and the cases target what is distinctive about
// Washington rather than convenient Tuesdays:
//
//   - CR 6(a) names its holiday statute expressly, and RCW 1.16.050(7)
//     excludes its own decoys, so a (7) day must NOT roll a deadline
//   - the both-way weekend shift, including a holiday landing in the PREVIOUS
//     year's calendar
//   - CR 6(e) LENGTHENS the period rather than following its expiry, and is
//     mail-only
//   - CR 12(a)'s five limbs are not interchangeable: 20 vs 60 days
//   - three discovery rules that all use 30/40, where North Carolina's use
//     45/45/60 -- the numbers must not have leaked between states
//   - the 7-day short-period exclusion, which Washington really can reach
//
// Run: node api/_lib/deadline-washington.test.js
'use strict';

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_washington.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_washington.json'), 'utf8'));

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
function byId(id) {
  const r = seed.rules.find(x => x.rule_id === id);
  if (!r) throw new Error('no such rule: ' + id);
  return r;
}
function compute(ruleId, triggerDate, extra) {
  const rule = byId(ruleId);
  const ev = typeof rule.trigger_event === 'string' ? rule.trigger_event : rule.trigger_event.id;
  return engine.computeDeadline(Object.assign({
    jurisdiction: 'wa', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── Seed shape ────────────────────────────────────────────────────────────
check('14 rules seeded', seed.rules.length, 14);
check('all rows are jurisdiction wa', seed.rules.every(r => r.jurisdiction === 'wa'), true);
check('all rows use wa_cr_6a', seed.rules.every(r => r.computation === 'wa_cr_6a'), true);
check('every rule id is unique', new Set(seed.rules.map(r => r.rule_id)).size, seed.rules.length);
check('three resolve_periods rows, one per discovery rule',
  seed.rules.filter(r => typeof r.trigger_event !== 'string' && r.trigger_event.resolve_periods).length, 3);
check('no resolve_periods row carries a service extension (limb two is CR 4 service)',
  seed.rules.filter(r => typeof r.trigger_event !== 'string' && r.trigger_event.resolve_periods)
    .some(r => r.service_extension), false);
check('every extending row is mail-only',
  seed.rules.filter(r => r.service_extension)
    .every(r => JSON.stringify(r.service_extension.applies_when) === JSON.stringify(['mail'])), true);
check('no backward row is seeded (CR 6(a) does not define the direction)',
  seed.rules.some(r => r.count && r.count.direction === 'backward'), false);
check('effective_from is each rule\'s own amendment date, not one blanket date',
  new Set(seed.rules.map(r => r.effective_from)).size > 1, true);
check('CR 12 rows carry the 2025-09-01 amendment date',
  seed.rules.filter(r => r.rule_id.startsWith('wa-cr-12-')).every(r => r.effective_from === '2025-09-01'), true);

// THE NUMBERS THAT MUST NOT HAVE LEAKED FROM NORTH CAROLINA. Washington is
// 30/40 on all three; North Carolina is 45/45/60.
const limbs = id => byId(id).trigger_event.limbs.map(L => L.count.value);
check('CR 33 defendant limbs are 30/40', limbs('wa-cr-33-a-interrogatory-answers-defendant-later-of-periods'), [30, 40]);
check('CR 34 defendant limbs are 30/40', limbs('wa-cr-34-b-production-response-defendant-later-of-periods'), [30, 40]);
check('CR 36 defendant limbs are 30/40, NOT North Carolina\'s 30/60',
  limbs('wa-cr-36-a-admission-response-defendant-later-of-periods'), [30, 40]);
{
  const ncSeed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_northcarolina.json'), 'utf8'));
  const nc36 = ncSeed.rules.find(r => r.rule_id === 'nc-rcp-36-a-admission-response-defendant-later-of-periods');
  check('and North Carolina still has 30/60, so the two states did not converge',
    nc36.trigger_event.limbs.map(L => L.count.value), [30, 60]);
}

// ── Standards ─────────────────────────────────────────────────────────────
check('wa_cr_6a declares the 7-day short-period exclusion',
  engine.COMPUTATION_STANDARDS.wa_cr_6a.short_period_exclusion_days, 7);
check('wa_cr_6a leaves backward blank', engine.COMPUTATION_STANDARDS.wa_cr_6a.rollover_suffix_backward, '');
check('wa_cr_6e LENGTHENS the period', engine.SERVICE_EXTENSION_STANDARDS.wa_cr_6e.sequence, 'add_to_period_then_roll');
check('wa_cr_6e qualifies mail and nothing else',
  ['mail', 'electronic', 'electronic_service', 'fax', 'left_with_clerk', 'other_consented_means']
    .filter(m => engine.SERVICE_EXTENSION_STANDARDS.wa_cr_6e.qualifies(m)), ['mail']);

// ── Calendar ──────────────────────────────────────────────────────────────
const wa2026 = calendars.wa['2026'].map(d => d.date);
check('11 legal holidays in 2026', wa2026.length, 11);
check('Juneteenth IS a Washington legal holiday', wa2026.includes('2026-06-19'), true);
check('Native American Heritage Day is the Friday after Thanksgiving',
  wa2026.includes('2026-11-26') && wa2026.includes('2026-11-27'), true);
check('Independence Day 2026 observed Friday 3 July (4 July is a Saturday)',
  wa2026.includes('2026-07-03') && !wa2026.includes('2026-07-04'), true);
// RCW 1.16.050(7) days -- "may not be considered legal holidays for any
// purpose". If any appears, the calendar was regenerated from the whole
// section instead of subsection (1), and every deadline crossing it is LATE.
check('Columbus Day is NOT in the calendar (RCW 1.16.050(7))', wa2026.includes('2026-10-12'), false);
check('Pearl Harbor Day is NOT in the calendar (RCW 1.16.050(7))', wa2026.includes('2026-12-07'), false);
check('no Sunday is listed even though RCW 1.16.050(1)(a) makes Sunday a holiday',
  Object.values(calendars.wa).flat().filter(d => new Date(d.date + 'T00:00:00Z').getUTCDay() === 0), []);
check('no calendar entry falls on a weekend',
  Object.values(calendars.wa).flat().filter(d => {
    const wd = new Date(d.date + 'T00:00:00Z').getUTCDay();
    return wd === 0 || wd === 6;
  }), []);
check('the 2028 New Year holiday sits in the 2027 calendar, not the 2028 one',
  calendars.wa['2027'].map(d => d.date).includes('2027-12-31') &&
  !calendars.wa['2028'].map(d => d.date).includes('2027-12-31'), true);
check('2028 therefore has ten entries, not eleven', calendars.wa['2028'].length, 10);

// ── Computations, hand-checked ───────────────────────────────────────────
// Served Fri 2026-05-01, +20 = Thu 2026-05-21. No weekend, no holiday.
check('CR 12(a)(1) 20-day answer', dateOf(compute('wa-cr-12-a1-answer-to-complaint', '2026-05-01')), '2026-05-21');
// Out-of-state service, same date, +60 = Tue 2026-06-30. FORTY days later than
// the ordinary limb -- the case that proves the limbs are not interchangeable.
check('CR 12(a)(3) out-of-state service is 60 days, not 20',
  dateOf(compute('wa-cr-12-a3-answer-after-out-of-state-personal-service', '2026-05-01')), '2026-06-30');
check('CR 12(a)(2) publication limb runs from first publication',
  dateOf(compute('wa-cr-12-a2-answer-after-service-by-publication', '2026-05-01')), '2026-06-30');
// Mail service must not extend the CR 4 answer period.
const ans = compute('wa-cr-12-a1-answer-to-complaint', '2026-05-01', { service_method: 'mail' });
check('answer to the complaint: mail adds nothing', ans.due_date, '2026-05-21');
check('answer to the complaint: state is not_requested', ans.service_extension.state, 'not_requested');

// SEQUENCING. Crossclaim served Wed 2026-05-13, +20 = Tue 2026-06-02, +3 = Fri
// 2026-06-05, no roll. Now one that separates the two orders: served Fri
// 2026-05-08, +20 = Thu 2026-05-28, +3 = Sun 2026-05-31 -> roll to Mon 06-01.
// Under the FEDERAL order the base would roll first (05-28 is a Thursday, no
// roll) and give the same answer here, so pick a base landing on a weekend:
// served Mon 2026-05-11 -> +20 = Sun 2026-05-31. Washington adds 3 to the
// UNROLLED 05-31 -> Wed 2026-06-03. The federal order would roll 05-31 to Mon
// 06-01 first, then add 3 -> Thu 2026-06-04.
const cc = compute('wa-cr-12-a-answer-to-crossclaim', '2026-05-11', { service_method: 'mail' });
check('CR 6(e) by mail: days lengthen the PERIOD (06-03, not federal 06-04)', cc.due_date, '2026-06-03');
check('CR 6(e) by mail: 3 days recorded', cc.service_extension.days_added, 3);
for (const m of ['electronic', 'fax', 'other_consented_means']) {
  const r = compute('wa-cr-12-a-answer-to-crossclaim', '2026-05-11', { service_method: m });
  check('CR 6(e) does not extend for "' + m + '"', r.service_extension.state, 'not_qualifying');
}

// A RCW 1.16.050(7) day must not roll anything. Columbus Day 2026 is Mon
// 2026-10-12. Request served Sat 2026-09-12 -> +30 = Mon 2026-10-12. If the
// calendar had been built from the whole statute this would roll to 10-13.
check('a RCW 1.16.050(7) "recognized day" does NOT roll (Columbus Day 2026)',
  dateOf(compute('wa-cr-34-b-production-response', '2026-09-12')), '2026-10-12');
// But a real (1) holiday does. Interrogatories served Tue 2026-11-24 -> +30 =
// Thu 2026-12-24. Christmas Fri 12-25 is not the last day, so no roll: 12-24.
// Use a landing ON Christmas instead: served Wed 2026-11-25 -> +30 = Fri
// 2026-12-25 (Christmas) -> Sat, Sun -> Mon 2026-12-28.
check('a real RCW 1.16.050(1) holiday DOES roll (Christmas 2026)',
  dateOf(compute('wa-cr-33-a-interrogatory-answers', '2026-11-25')), '2026-12-28');

// THE SHORT-PERIOD EXCLUSION, which Washington can actually reach. The 10-day
// CR 12(a)(A) row is ABOVE the threshold, so intermediate days still count:
// notice Fri 2026-05-22 + 10 calendar days = Mon 2026-06-01. Memorial Day Mon
// 2026-05-25 is intermediate and is COUNTED, not skipped.
check('a 10-day period is above the 7-day threshold and counts intermediate holidays',
  dateOf(compute('wa-cr-12-aA-responsive-pleading-after-motion-denied', '2026-05-22')), '2026-06-01');

// ── resolve_periods ──────────────────────────────────────────────────────
// Summons served Mon 2026-06-01 -> 40 days = Sat 2026-07-11 (unrolled).
// Request served Mon 2026-06-08 -> 30 days = Wed 2026-07-08. The 40-day limb
// governs; its end rolls off the Saturday to Mon 2026-07-13.
check('CR 36 defendant: the 40-day process limb governs an early request',
  dateOf(engine.computeDeadline({
    jurisdiction: 'wa', domain: 'civil-litigation',
    trigger_event: 'admission_request_on_defendant',
    trigger_dates: {
      service_of_request_for_admission_on_defendant: '2026-06-08',
      service_of_summons_and_complaint_for_admission: '2026-06-01'
    },
    rules: seed.rules, calendars: calendars, as_of: '2026-06-08'
  })), '2026-07-13');
// Same facts against North Carolina's 60-day floor would be 2026-07-31. Proving
// the two states really do differ, live, on identical inputs.
{
  const ncSeed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_northcarolina.json'), 'utf8'));
  const ncCal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_northcarolina.json'), 'utf8'));
  const nc = {};
  for (const row of ncCal.holiday_calendars) {
    nc[row.jurisdiction] = nc[row.jurisdiction] || {};
    nc[row.jurisdiction][String(row.year)] = row.dates;
  }
  check('North Carolina on identical facts gives 2026-07-31, eighteen days later',
    dateOf(engine.computeDeadline({
      jurisdiction: 'nc', domain: 'civil-litigation',
      trigger_event: 'admission_request_on_defendant',
      trigger_dates: {
        service_of_request_for_admission_on_defendant: '2026-06-08',
        service_of_summons_and_complaint_for_admission: '2026-06-01'
      },
      rules: ncSeed.rules, calendars: nc, as_of: '2026-06-08'
    })), '2026-07-31');
}
check('a resolve_periods rule refuses on one date',
  compute('wa-cr-36-a-admission-response-defendant-later-of-periods', '2026-06-08').code,
  'INCOMPLETE_TRIGGERS');

// ── Refusals ─────────────────────────────────────────────────────────────
check('a pre-amendment CR 12 trigger is refused, not computed',
  compute('wa-cr-12-a1-answer-to-complaint', '2025-06-01').ok, false);
check('a year outside the loaded calendars refuses',
  compute('wa-cr-12-a1-answer-to-complaint', '2032-05-01').code, 'NOT_PROVISIONED');

// ── The engine change must not reach other jurisdictions ────────────────
check('wa_cr_6a has its own impl string', engine.COMPUTATION_STANDARDS.wa_cr_6a.impl, 'wa_cr_6a');
check('wa_cr_6e declares no contested predicate (only West Virginia does)',
  Object.keys(engine.SERVICE_EXTENSION_STANDARDS)
    .filter(k => typeof engine.SERVICE_EXTENSION_STANDARDS[k].contested === 'function'), ['wv_rcp_6e']);

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
