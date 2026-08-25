// North Carolina deadline rows -- isolated verification against the REAL engine
// and the REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Every expected date was worked out BY HAND from the rule text and the NCAOC
// closure schedule before the engine was run, and the cases target what is
// actually distinctive about North Carolina rather than convenient Tuesdays:
//
//   - the calendar is a COURT CLOSURE SCHEDULE, not G.S. 103-4, so a day the
//     statute calls a holiday but the courthouse stays open for must NOT roll
//   - the three-day Christmas and two-day Thanksgiving blocks, which no rule
//     produces and which a generated calendar would get wrong
//   - Rule 6(e) is period-lengthening, NOT the federal after-expiry order, and
//     is mail-only
//   - three discovery rules with three different defendant periods (45/45/60),
//     each a resolve_periods later_of
//   - coverage ends after 2027 and must REFUSE beyond it rather than compute
//
// Run: node api/_lib/deadline-northcarolina.test.js
'use strict';

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_northcarolina.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_northcarolina.json'), 'utf8'));

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
    jurisdiction: 'nc', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── Seed shape ────────────────────────────────────────────────────────────
check('13 rules seeded', seed.rules.length, 13);
check('all rows are jurisdiction nc', seed.rules.every(r => r.jurisdiction === 'nc'), true);
check('all rows use nc_rcp_6a', seed.rules.every(r => r.computation === 'nc_rcp_6a'), true);
check('every rule id is unique', new Set(seed.rules.map(r => r.rule_id)).size, seed.rules.length);
check('three resolve_periods rows, one per discovery rule',
  seed.rules.filter(r => typeof r.trigger_event !== 'string' && r.trigger_event.resolve_periods).length, 3);
check('no resolve_periods row carries a service extension (limb two is Rule 4 service)',
  seed.rules.filter(r => typeof r.trigger_event !== 'string' && r.trigger_event.resolve_periods)
    .some(r => r.service_extension), false);
check('every extending row is mail-only',
  seed.rules.filter(r => r.service_extension)
    .every(r => JSON.stringify(r.service_extension.applies_when) === JSON.stringify(['mail'])), true);
check('every row cites a real quote and url',
  seed.rules.every(r => r.authority && r.authority.quote && r.authority.url), true);
check('no backward row is seeded (Rule 6(a) does not define the direction)',
  seed.rules.some(r => r.count && r.count.direction === 'backward'), false);

// THE NUMBER THAT MATTERS MOST. Rule 36 is self-executing and its defendant
// limb is SIXTY days, where Rules 33 and 34 use forty-five. A row built on 45
// would concede facts fifteen days early.
const limbCounts = id => byId(id).trigger_event.limbs.map(L => L.count.value);
check('Rule 33 defendant limbs are 30/45',
  limbCounts('nc-rcp-33-a-interrogatory-answers-defendant-later-of-periods'), [30, 45]);
check('Rule 34 defendant limbs are 30/45',
  limbCounts('nc-rcp-34-b-production-response-defendant-later-of-periods'), [30, 45]);
check('Rule 36 defendant limbs are 30/60, NOT 30/45',
  limbCounts('nc-rcp-36-a-admission-response-defendant-later-of-periods'), [30, 60]);

// ── The standards ─────────────────────────────────────────────────────────
check('nc_rcp_6a declares the 7-day short-period exclusion',
  engine.COMPUTATION_STANDARDS.nc_rcp_6a.short_period_exclusion_days, 7);
check('nc_rcp_6a leaves backward blank (the rule is silent)',
  engine.COMPUTATION_STANDARDS.nc_rcp_6a.rollover_suffix_backward, '');
check('nc_rcp_6e is PERIOD-LENGTHENING, not the federal after-expiry order',
  engine.SERVICE_EXTENSION_STANDARDS.nc_rcp_6e.sequence, 'add_to_period_then_roll');
check('nc_rcp_6e qualifies mail and nothing else',
  ['mail', 'electronic', 'electronic_service', 'fax', 'left_with_clerk', 'other_consented_means']
    .filter(m => engine.SERVICE_EXTENSION_STANDARDS.nc_rcp_6e.qualifies(m)), ['mail']);
check('nc_rcp_6e declares no contested predicate (only West Virginia does)',
  typeof engine.SERVICE_EXTENSION_STANDARDS.nc_rcp_6e.contested, 'undefined');

// ── The calendar: closure schedule, not the statute ──────────────────────
const nc2026 = calendars.nc['2026'].map(d => d.date);
check('12 court holidays in 2026', nc2026.length, 12);
check('12 court holidays in 2027', calendars.nc['2027'].length, 12);
check('Christmas 2026 is THREE days: 24, 25 and 28 December',
  nc2026.filter(d => d.startsWith('2026-12')), ['2026-12-24', '2026-12-25', '2026-12-28']);
check('Thanksgiving 2026 is TWO days: 26 and 27 November',
  nc2026.filter(d => d === '2026-11-26' || d === '2026-11-27'), ['2026-11-26', '2026-11-27']);
check('Independence Day 2026 is observed Friday 3 July (4 July is a Saturday)',
  nc2026.includes('2026-07-03') && !nc2026.includes('2026-07-04'), true);
check('Good Friday IS a court holiday', nc2026.includes('2026-04-03'), true);
// The statute-only days. Each of these is a G.S. 103-4 legal public holiday and
// none is a court closure. If any ever appears here, the calendar has been
// regenerated from the statute and every deadline crossing it is LATE.
const statuteOnly2026 = {
  'Robert E. Lee\'s Birthday': '2026-01-19',      // shares MLK's date in 2026
  'Greek Independence Day': '2026-03-25',
  'Halifax Resolves': '2026-04-12',
  'Confederate Memorial Day': '2026-05-10',
  'Mecklenburg Declaration': '2026-05-20',
  'Washington\'s Birthday': '2026-02-16',
  'First Responders Day': '2026-09-11',
  'Columbus Day': '2026-10-12'
};
for (const [name, date] of Object.entries(statuteOnly2026)) {
  if (date === '2026-01-19') continue; // MLK Day genuinely is a closure that day
  check('G.S. 103-4 day NOT in the calendar: ' + name, nc2026.includes(date), false);
}
check('no calendar entry falls on a weekend',
  Object.values(calendars.nc).flat().filter(d => {
    const wd = new Date(d.date + 'T00:00:00Z').getUTCDay();
    return wd === 0 || wd === 6;
  }), []);

// ── Computations, hand-checked ───────────────────────────────────────────
// Served Fri 2026-05-01, +30 = Sun 2026-05-31 -> Mon 2026-06-01.
check('12(a)(1) 30-day answer, landing on a Sunday, rolls to Monday',
  dateOf(compute('nc-rcp-12-a1-answer-to-complaint', '2026-05-01')), '2026-06-01');
// Mail must add nothing on the answer to the complaint: Rule 4 service.
const ans = compute('nc-rcp-12-a1-answer-to-complaint', '2026-05-01', { service_method: 'mail' });
check('answer to the complaint: mail adds nothing', ans.due_date, '2026-06-01');
check('answer to the complaint: state is not_requested', ans.service_extension.state, 'not_requested');

// THE SEQUENCING CASE. Crossclaim served Fri 2026-05-01. Base +30 = Sun
// 2026-05-31. Under the FEDERAL order that would roll to Mon 06-01 and then
// add 3 -> Thu 06-04. North Carolina lengthens the PERIOD instead: 05-31 + 3 =
// Wed 2026-06-03, no roll needed. The two orders differ by one day here.
const cc = compute('nc-rcp-12-a1-answer-to-crossclaim', '2026-05-01', { service_method: 'mail' });
check('12(a)(1) crossclaim by mail: days lengthen the PERIOD (06-03, not 06-04)',
  cc.due_date, '2026-06-03');
check('crossclaim by mail: 3 days recorded', cc.service_extension.days_added, 3);
// Every non-mail method must decline, and be reported as declining rather than
// as contested -- only West Virginia has a contested standard.
for (const m of ['electronic', 'fax', 'left_with_clerk', 'other_consented_means']) {
  const r = compute('nc-rcp-12-a1-answer-to-crossclaim', '2026-05-01', { service_method: m });
  check('6(e) does not extend for "' + m + '"', r.service_extension.state, 'not_qualifying');
  check('6(e) adds nothing for "' + m + '"', r.due_date, '2026-06-01');
}

// A period whose last day is a court holiday. Interrogatories served
// Wed 2026-11-25 -> +30 = Fri 2026-12-25, Christmas, a closure -> Mon 12-28 is
// also a closure -> Tue 2026-12-29.
check('33(a) rolling across the three-day Christmas block',
  dateOf(compute('nc-rcp-33-a-interrogatory-answers', '2026-11-25')), '2026-12-29');

// A G.S. 103-4 day the courthouse stays OPEN for must not roll. Columbus Day
// 2026 is Mon 2026-10-12. Request served Sat 2026-09-12 -> +30 = Mon 10-12.
// Under the statute that would roll to Tue 10-13. It must NOT.
check('a G.S. 103-4 day that is not a closure does NOT roll (Columbus Day 2026)',
  dateOf(compute('nc-rcp-34-b-production-response', '2026-09-12')), '2026-10-12');

// ── resolve_periods: the limb that wins must bring its OWN count ─────────
// Rule 36 defendant. Summons served Mon 2026-06-01 (60 days -> Fri 2026-07-31).
// Request served Mon 2026-07-06 (30 days -> Wed 2026-08-05). Limb one wins.
check('36(a) defendant: request-limb governs when it ends later',
  dateOf(engine.computeDeadline({
    jurisdiction: 'nc', domain: 'civil-litigation',
    trigger_event: 'admission_request_on_defendant',
    trigger_dates: {
      service_of_request_for_admission_on_defendant: '2026-07-06',
      service_of_summons_and_complaint_for_admission: '2026-06-01'
    },
    rules: seed.rules, calendars: calendars, as_of: '2026-07-06'
  })), '2026-08-05');
// Same summons, but the request comes early: served Mon 2026-06-08, 30 days ->
// Wed 2026-07-08. The 60-day process limb (Fri 2026-07-31) governs. This is the
// case an ordinary later_of gets wrong: it would pick the later trigger date
// (2026-06-08) and apply 30 days, landing 2026-07-08 -- 23 days early, on a
// SELF-EXECUTING rule.
check('36(a) defendant: 60-day process limb governs an early request',
  dateOf(engine.computeDeadline({
    jurisdiction: 'nc', domain: 'civil-litigation',
    trigger_event: 'admission_request_on_defendant',
    trigger_dates: {
      service_of_request_for_admission_on_defendant: '2026-06-08',
      service_of_summons_and_complaint_for_admission: '2026-06-01'
    },
    rules: seed.rules, calendars: calendars, as_of: '2026-06-08'
  })), '2026-07-31');
// And the 45-day sibling on identical facts must land two weeks earlier, which
// is the proof the two rules were not encoded from one another.
check('33(a) defendant on identical facts uses 45, not 60',
  dateOf(engine.computeDeadline({
    jurisdiction: 'nc', domain: 'civil-litigation',
    trigger_event: 'interrogatories_on_defendant',
    trigger_dates: {
      service_of_interrogatories_on_defendant: '2026-06-08',
      service_of_summons_and_complaint_for_interrogatories: '2026-06-01'
    },
    rules: seed.rules, calendars: calendars, as_of: '2026-06-08'
  })), '2026-07-16');
// Partial input must refuse, not silently degrade to one limb.
check('a resolve_periods rule refuses on one date',
  compute('nc-rcp-36-a-admission-response-defendant-later-of-periods', '2026-06-08').code,
  'INCOMPLETE_TRIGGERS');

// ── Coverage ends after 2027 and must refuse, not compute ────────────────
check('a 2028 trigger refuses rather than computing against an unknown year',
  compute('nc-rcp-12-a1-answer-to-complaint', '2028-03-01').code, 'NOT_PROVISIONED');
// A 2027 trigger whose period crosses into 2028 must also refuse -- the engine
// checks the year it actually needs, not the year of the trigger.
check('a late-2027 period that crosses into 2028 also refuses',
  compute('nc-rcp-12-a1-answer-to-complaint', '2027-12-20').code, 'NOT_PROVISIONED');

// ── The engine change must not reach any other jurisdiction ─────────────
check('nc_rcp_6a is not accidentally sharing Ohio/Indiana/WV impl strings',
  engine.COMPUTATION_STANDARDS.nc_rcp_6a.impl, 'nc_rcp_6a');
{
  const wvSeed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_westvirginia.json'), 'utf8'));
  const wvCal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_westvirginia.json'), 'utf8'));
  const wc = {};
  for (const row of wvCal.holiday_calendars) {
    wc[row.jurisdiction] = wc[row.jurisdiction] || {};
    wc[row.jurisdiction][String(row.year)] = row.dates;
  }
  const r = engine.computeDeadline({
    jurisdiction: 'wv', domain: 'civil-litigation',
    trigger_event: 'service_of_pleading_stating_counterclaim_or_crossclaim',
    trigger_date: '2026-05-01', service_method: 'mail',
    rules: wvSeed.rules, calendars: wc, as_of: '2026-05-01'
  });
  check('West Virginia still uses the FEDERAL order (06-04) after adding NC',
    dateOf(r), '2026-06-04');
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
