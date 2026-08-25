// New Jersey deadline rows -- isolated verification against the REAL engine and
// the REAL seed/calendar JSON on disk.
//
// Expected dates were worked out BY HAND from the rule text and the Supreme
// Court's own legal-holiday orders before the engine was run. The cases target
// what is distinctive about New Jersey:
//
//   - the calendar comes from a COURT ORDER, not a statute, and the order
//     distinguishes "Legal Holiday" from "Court Recess" -- recess days must
//     not roll anything
//   - Columbus Day and general election day ARE legal holidays here, where
//     other states exclude them
//   - Juneteenth is the THIRD FRIDAY IN JUNE, not 19 June
//   - R. 1:3-3 adds FIVE days, for ORDINARY MAIL ONLY, and lengthens the period
//   - four rules, four different first periods, and the two later-of rules do
//     not share a pair
//   - coverage is calendar 2026 alone and everything else must REFUSE
//
// Run: node api/_lib/deadline-newjersey.test.js
'use strict';

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_newjersey.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_newjersey.json'), 'utf8'));

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
    jurisdiction: 'nj', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── Seed shape ────────────────────────────────────────────────────────────
check('11 rules seeded', seed.rules.length, 11);
check('all rows are jurisdiction nj', seed.rules.every(r => r.jurisdiction === 'nj'), true);
check('all rows use nj_r_1_3_1', seed.rules.every(r => r.computation === 'nj_r_1_3_1'), true);
check('every rule id is unique', new Set(seed.rules.map(r => r.rule_id)).size, seed.rules.length);
check('TWO resolve_periods rows, not three -- interrogatories has no defendant limb',
  seed.rules.filter(r => typeof r.trigger_event !== 'string' && r.trigger_event.resolve_periods).length, 2);
check('the interrogatory row is a PLAIN rule, not resolve_periods',
  typeof byId('nj-r-4-17-4-interrogatory-answers').trigger_event, 'string');
check('no resolve_periods row carries a service extension',
  seed.rules.filter(r => typeof r.trigger_event !== 'string' && r.trigger_event.resolve_periods)
    .some(r => r.service_extension), false);
check('every extending row lists ordinary_mail, never bare mail',
  seed.rules.filter(r => r.service_extension)
    .every(r => JSON.stringify(r.service_extension.applies_when) === JSON.stringify(['ordinary_mail'])), true);
check('every extension adds FIVE days, not three',
  [...new Set(seed.rules.filter(r => r.service_extension).map(r => r.service_extension.add))], [5]);
check('no backward row is seeded', seed.rules.some(r => r.count && r.count.direction === 'backward'), false);

// FOUR RULES, FOUR DIFFERENT FIRST PERIODS -- and the two later-of pairs differ.
check('answer is 35 days', byId('nj-r-4-6-1-answer-to-complaint').count.value, 35);
check('reply to an answer is 20 days', byId('nj-r-4-6-1-reply-to-answer').count.value, 20);
check('interrogatories are 60 days', byId('nj-r-4-17-4-interrogatory-answers').count.value, 60);
const limbs = id => byId(id).trigger_event.limbs.map(L => L.count.value);
check('production limbs are 35/50', limbs('nj-r-4-18-1-production-response-defendant-later-of-periods'), [35, 50]);
check('admission limbs are 30/45, NOT the same pair as production',
  limbs('nj-r-4-22-1-admission-response-defendant-later-of-periods'), [30, 45]);
// And they must not have converged with the two states seeded just before.
{
  const wa = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_washington.json'), 'utf8'));
  const nc = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_northcarolina.json'), 'utf8'));
  const pick = (s, id) => s.rules.find(r => r.rule_id === id).trigger_event.limbs.map(L => L.count.value);
  check('Washington admissions are still 30/40', pick(wa, 'wa-cr-36-a-admission-response-defendant-later-of-periods'), [30, 40]);
  check('North Carolina admissions are still 30/60', pick(nc, 'nc-rcp-36-a-admission-response-defendant-later-of-periods'), [30, 60]);
}

// ── Standards ─────────────────────────────────────────────────────────────
check('nj_r_1_3_1 declares the 7-day short-period exclusion',
  engine.COMPUTATION_STANDARDS.nj_r_1_3_1.short_period_exclusion_days, 7);
check('nj_r_1_3_1 leaves backward blank', engine.COMPUTATION_STANDARDS.nj_r_1_3_1.rollover_suffix_backward, '');
check('nj_r_1_3_3 lengthens the period', engine.SERVICE_EXTENSION_STANDARDS.nj_r_1_3_3.sequence, 'add_to_period_then_roll');
check('nj_r_1_3_3 qualifies ordinary_mail and rejects bare mail',
  ['ordinary_mail', 'mail', 'certified_mail', 'electronic', 'email']
    .filter(m => engine.SERVICE_EXTENSION_STANDARDS.nj_r_1_3_3.qualifies(m)), ['ordinary_mail']);

// ── Calendar ──────────────────────────────────────────────────────────────
const nj = calendars.nj['2026'].map(d => d.date);
check('13 legal holidays in calendar 2026', nj.length, 13);
// UPDATED 2026-08-25 when the 2027-2028 order was found published (dated
// 2026-06-01, /s/ Stuart Rabner C.J.) and calendar 2027 became completable.
// This assertion used to read `['2026']` and was CORRECT then; it is kept as a
// coverage assertion rather than deleted, because the point it guards has not
// changed -- New Jersey must expose exactly the years both of whose covering
// orders have issued, never a half-known one.
check('exactly 2026 and 2027 are loaded', Object.keys(calendars.nj), ['2026', '2027']);
check('14 legal holidays in calendar 2027', calendars.nj['2027'].length, 14);
check('Columbus Day IS a New Jersey legal holiday', nj.includes('2026-10-12'), true);
check('general election day IS a legal holiday, in an EVEN year', nj.includes('2026-11-03'), true);
check('Good Friday IS a legal holiday', nj.includes('2026-04-03'), true);
check('Independence Day appears as the observed Friday 3 July', nj.includes('2026-07-03') && !nj.includes('2026-07-04'), true);
// The order lists these as Court Recess / Judicial College, NOT Legal Holiday.
// R. 1:3-1 rolls off legal holidays only, so including them would push LATE.
for (const d of ['2026-11-23', '2026-11-24', '2026-11-25', '2026-12-28', '2026-12-29', '2026-12-30', '2026-12-31']) {
  check('recess/College day is NOT in the calendar: ' + d, nj.includes(d), false);
}
check('no calendar entry falls on a weekend',
  nj.filter(d => { const w = new Date(d + 'T00:00:00Z').getUTCDay(); return w === 0 || w === 6; }), []);

// ── Computations, hand-checked ───────────────────────────────────────────
// Served Fri 2026-05-01, +35 = Fri 2026-06-05. No weekend, no holiday.
check('4:6-1 35-day answer', dateOf(compute('nj-r-4-6-1-answer-to-complaint', '2026-05-01')), '2026-06-05');
// Ordinary mail must add nothing to the R. 4:4-4 answer period.
const ans = compute('nj-r-4-6-1-answer-to-complaint', '2026-05-01', { service_method: 'ordinary_mail' });
check('answer to the complaint: ordinary mail adds nothing', ans.due_date, '2026-06-05');
check('answer to the complaint: state is not_requested', ans.service_extension.state, 'not_requested');

// THE FIVE-DAY, PERIOD-LENGTHENING CASE. Counterclaim served Sun 2026-04-26 ->
// +35 = Sun 2026-05-31. New Jersey adds 5 to the UNROLLED 05-31 -> Fri
// 2026-06-05. The federal order would roll 05-31 to Mon 06-01 first, then add
// 5 -> Sat 2026-06-06, rolling again to Mon 2026-06-08.
const cc = compute('nj-r-4-6-1-answer-to-counterclaim-or-crossclaim', '2026-04-26', { service_method: 'ordinary_mail' });
check('1:3-3: five days lengthen the PERIOD (06-05, not federal 06-08)', cc.due_date, '2026-06-05');
check('1:3-3: five days recorded', cc.service_extension.days_added, 5);
// A bare "mail" must be refused, not silently extended.
const bare = compute('nj-r-4-6-1-answer-to-counterclaim-or-crossclaim', '2026-04-26', { service_method: 'mail' });
check('a bare "mail" does NOT qualify under 1:3-3', bare.service_extension.state, 'not_qualifying');
check('and gets the unextended date', bare.due_date, '2026-06-01');
for (const m of ['certified_mail', 'email', 'electronic']) {
  check('1:3-3 does not extend for "' + m + '"',
    compute('nj-r-4-6-1-answer-to-counterclaim-or-crossclaim', '2026-04-26', { service_method: m })
      .service_extension.state, 'not_qualifying');
}

// COLUMBUS DAY MUST ROLL HERE, where it must not in Washington and North
// Carolina. Request served Sat 2026-09-12 -> +30 = Mon 2026-10-12 = Columbus
// Day -> Tue 2026-10-13.
check('Columbus Day 2026 DOES roll in New Jersey',
  dateOf(compute('nj-r-4-22-1-admission-response', '2026-09-12')), '2026-10-13');
{
  const wa = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_washington.json'), 'utf8'));
  const wc = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_washington.json'), 'utf8'));
  const wcal = {};
  for (const row of wc.holiday_calendars) {
    wcal[row.jurisdiction] = wcal[row.jurisdiction] || {};
    wcal[row.jurisdiction][String(row.year)] = row.dates;
  }
  check('and on the same date Washington does NOT roll it',
    dateOf(engine.computeDeadline({
      jurisdiction: 'wa', domain: 'civil-litigation',
      trigger_event: 'service_of_request_for_production', trigger_date: '2026-09-12',
      rules: wa.rules, calendars: wcal, as_of: '2026-09-12'
    })), '2026-10-12');
}
// A recess day must NOT roll. Interrogatories served Fri 2026-10-30, +60 =
// Tue 2026-12-29, which is inside the 28-31 December Court Recess. The order
// does not call those days legal holidays, so no roll.
check('a Court Recess day does NOT roll (29 December 2026)',
  dateOf(compute('nj-r-4-17-4-interrogatory-answers', '2026-10-30')), '2026-12-29');

// ── resolve_periods ──────────────────────────────────────────────────────
// Summons served Mon 2026-06-01 -> 45 days = Thu 2026-07-16. Request served
// Mon 2026-06-08 -> 30 days = Wed 2026-07-08. The 45-day limb governs.
check('4:22-1 defendant: the 45-day process limb governs an early request',
  dateOf(engine.computeDeadline({
    jurisdiction: 'nj', domain: 'civil-litigation',
    trigger_event: 'admission_request_on_defendant',
    trigger_dates: {
      service_of_request_for_admission_on_defendant: '2026-06-08',
      service_of_summons_and_complaint_for_admission: '2026-06-01'
    },
    rules: seed.rules, calendars: calendars, as_of: '2026-06-08'
  })), '2026-07-16');
// Production on the same facts uses 50, not 45 -- proving the two New Jersey
// later-of rules really do carry different pairs. 2026-06-01 + 50 = Tue
// 2026-07-21.
check('4:18-1 defendant on identical facts uses 50, not 45',
  dateOf(engine.computeDeadline({
    jurisdiction: 'nj', domain: 'civil-litigation',
    trigger_event: 'production_request_on_defendant',
    trigger_dates: {
      service_of_request_for_production_on_defendant: '2026-06-08',
      service_of_summons_and_complaint_for_production: '2026-06-01'
    },
    rules: seed.rules, calendars: calendars, as_of: '2026-06-08'
  })), '2026-07-21');
check('a resolve_periods rule refuses on one date',
  compute('nj-r-4-22-1-admission-response-defendant-later-of-periods', '2026-06-08').code,
  'INCOMPLETE_TRIGGERS');

// ── The 2027 calendar, read from the 2026-2027 and 2027-2028 orders ──────
const nj27 = calendars.nj['2027'].map(d => d.date);
// Juneteenth is "the third Friday in June", NOT 19 June. 2026 hides this
// (the third Friday IS the 19th); 2027 and 2028 expose it.
check('Juneteenth 2027 is the third FRIDAY, 18 June, not the 19th',
  nj27.includes('2027-06-18') && !nj27.includes('2027-06-19'), true);
check('Good Friday 2027 moved to 26 March', nj27.includes('2027-03-26'), true);
check('Independence Day 2027 is the observed Monday 5 July (4 July is a Sunday)',
  nj27.includes('2027-07-05') && !nj27.includes('2027-07-04'), true);
check('Christmas 2027 is the observed Friday 24 December (25 Dec is a Saturday)',
  nj27.includes('2027-12-24') && !nj27.includes('2027-12-25'), true);
// THE YEAR-BOUNDARY ENTRY. 1 January 2028 is a Saturday, so the order
// designates Friday 31 December 2027 the legal holiday -- it belongs to the
// 2027 calendar, not 2028. Same shape already flagged in WV and VA.
check('New Year 2028 observed lands in the 2027 calendar, on 31 December 2027',
  nj27.includes('2027-12-31'), true);
check('General Election Day is a legal holiday in the ODD year 2027 too',
  nj27.includes('2027-11-02'), true);
check('Columbus Day 2027 is still a New Jersey legal holiday', nj27.includes('2027-10-11'), true);
// The 2027-2028 order's recess and College days must not have leaked in.
for (const d of ['2027-11-22', '2027-11-23', '2027-11-24',
                 '2027-12-27', '2027-12-28', '2027-12-29', '2027-12-30']) {
  check('2027 recess/College day is NOT in the calendar: ' + d, nj27.includes(d), false);
}
check('no 2027 calendar entry falls on a weekend',
  nj27.filter(d => { const w = new Date(d + 'T00:00:00Z').getUTCDay(); return w === 0 || w === 6; }), []);

// ── Coverage: 2027 now computes, 2028 still honestly refuses ─────────────
// These three assertions previously proved the 2027 GAP. They now prove the
// FIX, and the 2028 one proves the same discipline still holds one year out:
// the January-June 2028 half is known from the 2027-2028 order, but the
// July-December half belongs to a 2028-2029 order that has not issued, and a
// half-filled year would look complete to the engine.
check('a 2027 trigger now COMPUTES -- the 2027-2028 order issued 2026-06-01',
  dateOf(compute('nj-r-4-6-1-answer-to-complaint', '2027-02-01')), '2027-03-08');
check('a late-2026 period crossing into 2027 now computes',
  compute('nj-r-4-17-4-interrogatory-answers', '2026-12-01').ok, true);
check('a 2028 trigger still refuses -- the 2028-2029 order has not issued',
  compute('nj-r-4-6-1-answer-to-complaint', '2028-02-01').code, 'NOT_PROVISIONED');
check('a late-2027 period crossing into 2028 also still refuses',
  compute('nj-r-4-6-1-answer-to-complaint', '2027-12-15').code, 'NOT_PROVISIONED');
check('a 2025 trigger refuses', compute('nj-r-4-6-1-answer-to-complaint', '2025-06-01').code, 'NOT_PROVISIONED');

// ── Blast radius ─────────────────────────────────────────────────────────
check('nj_r_1_3_1 has its own impl string', engine.COMPUTATION_STANDARDS.nj_r_1_3_1.impl, 'nj_r_1_3_1');
check('wv_rcp_6e is still the only contested standard',
  Object.keys(engine.SERVICE_EXTENSION_STANDARDS)
    .filter(k => typeof engine.SERVICE_EXTENSION_STANDARDS[k].contested === 'function'), ['wv_rcp_6e']);

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
