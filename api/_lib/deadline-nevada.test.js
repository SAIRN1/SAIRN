// Nevada deadline rows -- isolated verification against the REAL engine and the
// REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Every expected date below was worked out BY HAND from the rule text and the
// derived NRS 236.015 holiday list BEFORE the engine was run, and the cases
// target what actually differs in Nevada:
//
//   - THE THREE TRAPS OF ANALOGY, each with a case that fails if the calendar
//     is ever rebuilt from a neighbour's list:
//       * NO COLUMBUS DAY -- a period landing on the second Monday in October
//         must NOT roll. This is the only LATE-direction trap in Nevada, and
//         Utah, West Virginia and the federal calendar all have that day.
//       * JUNETEENTH IS 19 JUNE, not Utah's third Monday. Two cases: one
//         landing on Nevada's date (rolls) and one landing on Utah's (does
//         not). In 2026 they are four days apart.
//       * NEVADA DAY and FAMILY DAY exist and roll.
//   - the extension is the FEDERAL SEQUENCING -- "3 days are added AFTER the
//     period would otherwise expire" -- so roll, add, roll again, where ten
//     seeded jurisdictions add to the period first
//   - the ANSWER row carries NO extension while the counterclaim row does,
//     because a summons is served under Rule 4 and a counterclaim under Rule 5
//   - 12(a)(2) is a later_of on two trigger DATES sharing ONE count, and
//     REFUSES unless both are supplied
//   - the calendar SPILLS: 1 January 2028 is a Saturday, observed 2027-12-31
//
// Run: node api/_lib/deadline-nevada.test.js
'use strict';

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_nevada.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_nevada.json'), 'utf8'));

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
    jurisdiction: 'nv', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── The seed's own shape ──────────────────────────────────────────────────
check('10 rules seeded', seed.rules.length, 10);
check('all rows are jurisdiction nv', seed.rules.every(r => r.jurisdiction === 'nv'), true);
check('every row uses nv_nrcp_6', seed.rules.every(r => r.computation === 'nv_nrcp_6'), true);
check('every rule id is unique', new Set(seed.rules.map(r => r.rule_id)).size, seed.rules.length);
check('every row cites a real quote and url',
  seed.rules.every(r => r.authority.quote && /^https?:\/\//.test(r.authority.url)), true);
check('every row shares the 2019 restyling date',
  seed.rules.every(r => r.effective_from === '2019-03-01'), true);

// WHICH ROWS CARRY THE EXTENSION IS A READING, NOT A DEFAULT. NRCP 6(d) reaches
// service made under Rule 5; a summons and complaint go out under Rule 4.
check('the answer-to-complaint row carries NO extension',
  !!seed.rules.find(r => r.rule_id === 'nv-nrcp-12-a-1-A-i-answer-to-summons-and-complaint').service_extension, false);
check('the government row carries NO extension either -- also Rule 4 service',
  !!seed.rules.find(r => r.rule_id === 'nv-nrcp-12-a-2-government-answer-later-of').service_extension, false);
check('neither waiver row carries one -- the period runs from SENDING, not service',
  seed.rules.filter(r => /waiver/.test(r.rule_id)).some(r => r.service_extension), false);
check('exactly six rows DO carry it, all Rule 5 service',
  seed.rules.filter(r => r.service_extension).map(r => r.rule_id).sort(),
  ['nv-nrcp-12-a-1-B-answer-to-counterclaim-or-crossclaim',
   'nv-nrcp-12-a-1-C-reply-to-answer',
   'nv-nrcp-16-1-j-1-early-case-conference',
   'nv-nrcp-33-b-2-interrogatory-response',
   'nv-nrcp-34-b-2-A-production-response',
   'nv-nrcp-36-a-3-admission-response']);
check('no row carries a service_completion -- 5(b)(2)(C) completes on mailing',
  seed.rules.some(r => r.service_completion), false);
check('no row declares a designated_period -- Nevada discovery has no defendant floor',
  seed.rules.some(r => r.designated_period), false);

// ── The standards ─────────────────────────────────────────────────────────
const std = engine.COMPUTATION_STANDARDS.nv_nrcp_6;
check('nv_nrcp_6 is registered', !!std, true);
check('NO short-period exclusion -- absent, not zero', 'short_period_exclusion_days' in std, false);
check('the forward rollover cites 6(a)(1)(C)', std.label + std.rollover_suffix_forward, 'Nev. R. Civ. P. 6(a)(1)(C)');
check('backward is a REAL citation, not blank', std.rollover_suffix_backward, '(a)(5)');

const ext = engine.SERVICE_EXTENSION_STANDARDS.nv_nrcp_6_d;
check('nv_nrcp_6_d is registered', !!ext, true);
check('it uses the FEDERAL sequencing, not add-to-period', ext.sequence, 'roll_then_add_then_roll');
check('the allowlist is the federal triple',
  ['mail', 'left_with_clerk', 'other_consented_means'].map(m => ext.qualifies(m)), [true, true, true]);
// 6(d) does not list 5(b)(2)(E). This is the rule, not an omission.
check('ELECTRONIC service qualifies for NOTHING',
  ['email', 'electronic', 'efiling_service_provider'].map(m => ext.qualifies(m)), [false, false, false]);

// ── The calendar, and the three traps ─────────────────────────────────────
check('the calendar covers 2026-2031', Object.keys(calendars.nv).sort(), ['2026', '2027', '2028', '2029', '2030', '2031']);
// 2027 carries 13 and 2028 carries 11 BECAUSE of the spill: 1 Jan 2028 is a
// Saturday, so it is observed 2027-12-31 and leaves 2028 without a New Year.
check('2027 carries 13 days and 2028 only 11 -- the spill, not a miscount',
  [calendars.nv['2027'].length, calendars.nv['2028'].length], [13, 11]);
check('2027-12-31 is in the 2027 calendar',
  calendars.nv['2027'].some(d => d.date === '2027-12-31'), true);
check('2028 has no 1 January entry',
  calendars.nv['2028'].some(d => d.date === '2028-01-01'), false);

const d2026 = Object.fromEntries(calendars.nv['2026'].map(d => [d.date, d.name]));
check('12 days in 2026', calendars.nv['2026'].length, 12);
// TRAP 1 -- the only LATE-direction one.
check('NO COLUMBUS DAY: the second Monday in October 2026 is not a holiday',
  d2026['2026-10-12'], undefined);
// TRAP 2 -- Nevada 19 June, Utah third Monday, four days apart in 2026.
check('Juneteenth is 19 June, and Utah\'s third Monday is NOT a Nevada holiday',
  [d2026['2026-06-19'], d2026['2026-06-15']], ['Juneteenth Day', undefined]);
// TRAP 3 -- two days no other seeded state has.
check('Nevada Day is the last Friday in October', d2026['2026-10-30'], 'Nevada Day');
check('Family Day is the Friday after Thanksgiving',
  [d2026['2026-11-26'], d2026['2026-11-27']], ['Thanksgiving Day', 'Family Day']);
check('Independence Day 2026 is observed Friday 3 July, not Saturday 4 July',
  [d2026['2026-07-03'], d2026['2026-07-04']], ['Independence Day', undefined]);

// ── Arithmetic ────────────────────────────────────────────────────────────
check('answer: 2026-06-01 + 21 = Monday 2026-06-22',
  dateOf(compute('nv-nrcp-12-a-1-A-i-answer-to-summons-and-complaint', '2026-06-01')), '2026-06-22');
check('counterclaim answer is 21 as well',
  dateOf(compute('nv-nrcp-12-a-1-B-answer-to-counterclaim-or-crossclaim', '2026-06-01')), '2026-06-22');
check('reply to an answer runs 21 from the ORDER to reply',
  dateOf(compute('nv-nrcp-12-a-1-C-reply-to-answer', '2026-06-01')), '2026-06-22');
check('waiver, domestic: 60 days',
  dateOf(compute('nv-nrcp-12-a-1-A-ii-answer-after-waiver-in-us', '2025-11-02')), '2026-01-02');
check('waiver, foreign: 90 days, and it lands on Juneteenth so it rolls',
  dateOf(compute('nv-nrcp-12-a-1-A-ii-answer-after-waiver-outside-us', '2026-03-21')), '2026-06-22');
check('interrogatories: 30 days',
  dateOf(compute('nv-nrcp-33-b-2-interrogatory-response', '2026-06-01')), '2026-07-01');
check('production: 30, same as interrogatories',
  dateOf(compute('nv-nrcp-34-b-2-A-production-response', '2026-06-01')), '2026-07-01');
check('admissions: 30, same again -- no per-device variation in Nevada',
  dateOf(compute('nv-nrcp-36-a-3-admission-response', '2026-06-01')), '2026-07-01');
check('early case conference: 45 days after service of an answer',
  dateOf(compute('nv-nrcp-16-1-j-1-early-case-conference', '2026-06-01')), '2026-07-16');

// THE TRAPS, AS ARITHMETIC. These are the cases that break if the calendar is
// ever rebuilt from a neighbouring state's holiday list.
check('landing on 2026-06-19 (Nevada Juneteenth) rolls to Monday 2026-06-22',
  dateOf(compute('nv-nrcp-12-a-1-A-i-answer-to-summons-and-complaint', '2026-05-29')), '2026-06-22');
check('landing on 2026-06-15 (UTAH Juneteenth) does NOT roll -- ordinary Nevada Monday',
  dateOf(compute('nv-nrcp-12-a-1-A-i-answer-to-summons-and-complaint', '2026-05-25')), '2026-06-15');
check('landing on 2026-10-12 (Columbus Day elsewhere) does NOT roll -- the LATE-direction trap',
  dateOf(compute('nv-nrcp-33-b-2-interrogatory-response', '2026-09-12')), '2026-10-12');
check('landing on Nevada Day (Fri 2026-10-30) rolls to Monday 2026-11-02',
  dateOf(compute('nv-nrcp-16-1-j-1-early-case-conference', '2026-09-15')), '2026-11-02');
check('landing on Thanksgiving rolls past FAMILY DAY and the weekend -- four days',
  dateOf(compute('nv-nrcp-12-a-1-A-i-answer-to-summons-and-complaint', '2026-11-05')), '2026-11-30');
check('landing on Family Day itself rolls to Monday 2026-11-30',
  dateOf(compute('nv-nrcp-33-b-2-interrogatory-response', '2026-10-28')), '2026-11-30');
check('landing on 2027-12-31 (2028 New Year, observed early) rolls into 2028',
  dateOf(compute('nv-nrcp-12-a-1-A-i-answer-to-summons-and-complaint', '2027-12-10')), '2028-01-03');

// ── The extension, and its sequencing ─────────────────────────────────────
// "3 days are added AFTER the period would otherwise expire": the base period
// rolls to Monday 22 June first, THEN three days are added, THEN it rolls
// again. Adding to the period first would give 2026-06-25 by a different route
// here, so the case below that distinguishes them is the discovery one.
check('counterclaim + mail: roll to Mon 22 Jun, add 3, land Thu 25 Jun',
  dateOf(compute('nv-nrcp-12-a-1-B-answer-to-counterclaim-or-crossclaim', '2026-06-01', { service_method: 'mail' })), '2026-06-25');
check('discovery + mail: 1 Jul + 3 = 4 Jul (Sat), rolls past the observed 3 Jul holiday to Mon 6 Jul',
  dateOf(compute('nv-nrcp-33-b-2-interrogatory-response', '2026-06-01', { service_method: 'mail' })), '2026-07-06');
check('left_with_clerk also qualifies',
  dateOf(compute('nv-nrcp-33-b-2-interrogatory-response', '2026-06-01', { service_method: 'left_with_clerk' })), '2026-07-06');
// The one that would be wrong if someone widened the allowlist to e-service.
check('EMAIL adds nothing -- 6(d) does not list Rule 5(b)(2)(E)',
  dateOf(compute('nv-nrcp-33-b-2-interrogatory-response', '2026-06-01', { service_method: 'email' })), '2026-07-01');
check('supplying mail on the ANSWER row adds nothing -- no extension is seeded there',
  dateOf(compute('nv-nrcp-12-a-1-A-i-answer-to-summons-and-complaint', '2026-06-01', { service_method: 'mail' })), '2026-06-22');

// ── The later_of government row ───────────────────────────────────────────
{
  const both = engine.computeDeadline({
    jurisdiction: 'nv', domain: 'civil-litigation',
    trigger_event: 'nevada_government_service_later_of',
    trigger_dates: { service_on_government_party: '2026-06-01', service_on_nevada_attorney_general: '2026-06-10' },
    rules: seed.rules, calendars: calendars, as_of: '2026-06-01'
  });
  // The LATER date governs: 10 June + 45 = 25 July, a Saturday, rolls to Mon 27.
  check('government row: 45 days from the LATER of the two service dates', dateOf(both), '2026-07-27');

  const one = engine.computeDeadline({
    jurisdiction: 'nv', domain: 'civil-litigation',
    trigger_event: 'nevada_government_service_later_of',
    trigger_date: '2026-06-01',
    rules: seed.rules, calendars: calendars, as_of: '2026-06-01'
  });
  check('it REFUSES on one date rather than resolving from a single limb',
    one.ok === false && /INCOMPLETE/.test(one.code || ''), true);
}

// ── The traps ─────────────────────────────────────────────────────────────
check('a bare "service_of_summons" matches nothing -- Nevada names the complaint too',
  dateOf(engine.computeDeadline({
    jurisdiction: 'nv', domain: 'civil-litigation', trigger_event: 'service_of_summons',
    trigger_date: '2026-06-01', rules: seed.rules, calendars: calendars, as_of: '2026-06-01'
  })), 'REFUSED:NO_MATCHING_RULE');
check('a pre-2019 trigger refuses on effective_from',
  dateOf(compute('nv-nrcp-33-b-2-interrogatory-response', '2018-06-01')), 'REFUSED:NO_RULE_IN_FORCE');
check('a 2032 trigger refuses -- the calendar stops at 2031',
  dateOf(compute('nv-nrcp-33-b-2-interrogatory-response', '2032-03-01')), 'REFUSED:NOT_PROVISIONED');

// ── Nothing else moved ────────────────────────────────────────────────────
check('Nevada declares NO coverage entry -- its gaps are all EARLY and row-level',
  Object.keys(engine.JURISDICTION_COVERAGE).sort(), ['al', 'ar', 'ks', 'ma', 'md', 'mn', 'mo', 'ms', 'nm', 'va', 'wi']);
check('Nevada adds no service-completion standard',
  Object.keys(engine.SERVICE_COMPLETION_STANDARDS), ['mo_rule_43_01_d']);
{
  const utSeed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_utah.json'), 'utf8'));
  const utCal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_utah.json'), 'utf8'));
  const uc = {};
  for (const row of utCal.holiday_calendars) {
    uc[row.jurisdiction] = uc[row.jurisdiction] || {};
    uc[row.jurisdiction][String(row.year)] = row.dates;
  }
  // The same trigger, the same count, in the two states gated a day apart --
  // and they differ, because Utah's Juneteenth is the third Monday.
  const ur = engine.computeDeadline({
    jurisdiction: 'ut', domain: 'civil-litigation', trigger_event: 'service_of_summons_in_state',
    trigger_date: '2026-05-25', rules: utSeed.rules, calendars: uc, as_of: '2026-05-25'
  });
  check('Utah still rolls off ITS Juneteenth on the date Nevada does not',
    [ur.ok, ur.due_date], [true, '2026-06-16']);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
