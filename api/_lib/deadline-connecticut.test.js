// Connecticut deadline rows -- isolated verification against the REAL engine
// and the REAL seed JSON on disk, not a scratch copy of either.
//
// THIS TEST ASSERTS THAT CONNECTICUT NEVER PRODUCES A DATE, WHICH IS THE
// POINT OF THE SEED. Every other jurisdiction's test proves its arithmetic;
// this one proves a HOLD. Connecticut is the first jurisdiction seeded with
// no holiday calendar, because its rollover keys on CLERK'S-OFFICE CLOSURE
// (Practice Book Sec. 7-17) rather than on any holiday list -- the word
// "holiday" appears five times in the whole 699-page Practice Book and never
// as a definition. Building a `ct` calendar out of Conn. Gen. Stat. Sec. 1-4's
// statutory list would roll LATE on any listed day a clerk's office is in fact
// open, which is exactly what left Wisconsin gated.
//
// So the cases below target the hold and the traps around it:
//
//   - the refusal is UNCONDITIONAL, not weekend-triggered: rollOff consults
//     the calendar before it looks at the weekday, so a Tuesday landing
//     refuses exactly like a Sunday one. A test that only checked weekends
//     would pass while the engine quietly answered on weekdays.
//   - `return_day` MUST NOT match. The seeded row runs from the preceding
//     PLEADING; the return-day limb is not seeded and the return day is not
//     derivable from a service date.
//   - no short_period_exclusion_days on ct_pb_63_2, where six seeded states
//     use 7 and three use 11 -- the field must be ABSENT, not a number.
//   - no `ct` entry in JURISDICTION_COVERAGE: that text rides on SUCCESSFUL
//     computations, and Connecticut has none, so an entry would be dormant.
//
// IF SOMEONE LOADS A `ct` CALENDAR, THESE TESTS BREAK. That is deliberate and
// is the mechanical part of the hold -- see the seed's _readme for the four
// questions that must be answered first.
//
// Run: node api/_lib/deadline-connecticut.test.js
'use strict';

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_connecticut.json'), 'utf8'));

// DELIBERATELY NOT EMPTY-BUT-PRESENT. `{ ct: {} }` would be a different and
// much weaker test: holidayFor would report the YEAR missing rather than the
// jurisdiction, and a future half-built calendar would still pass. Connecticut
// must be absent from the map entirely, exactly as it is in production.
const calendars = {};

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

function compute(triggerDate, extra) {
  const rule = seed.rules[0];
  const ev = typeof rule.trigger_event === 'string' ? rule.trigger_event : rule.trigger_event.id;
  return engine.computeDeadline(Object.assign({
    jurisdiction: 'ct', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const codeOf = r => (r.ok === false ? r.code : 'COMPUTED:' + r.due_date);

// ── The seed's own shape ──────────────────────────────────────────────────
check('exactly 1 rule seeded', seed.rules.length, 1);
check('the row is jurisdiction ct', seed.rules[0].jurisdiction, 'ct');
check('the row uses ct_pb_63_2', seed.rules[0].computation, 'ct_pb_63_2');
check('the row cites a real quote and url',
  !!(seed.rules[0].authority.quote && /^https?:\/\//.test(seed.rules[0].authority.url)), true);
check('effective_from is Sec. 10-8s real amendment date, not a restyling fallback',
  seed.rules[0].effective_from, '2014-01-01');
check('thirty calendar days forward',
  [seed.rules[0].count.value, seed.rules[0].count.unit, seed.rules[0].count.direction],
  [30, 'calendar_days', 'forward']);

// THE TRIGGER NAME IS A SAFETY DEVICE, not a label. "answer" or "return_day"
// here would invite exactly the misreading the gate flagged.
check('trigger is named for the preceding pleading',
  seed.rules[0].trigger_event, 'filing_of_preceding_pleading');
check('no row claims to be an answer deadline',
  seed.rules.some(r => /answer/i.test(r.trigger_event)), false);

// A service block on a rule that runs from a FILING would be a field the
// engine reads for an event that never happens.
check('no service_extension on a filing-triggered row', !!seed.rules[0].service_extension, false);
check('no service_completion on a filing-triggered row', !!seed.rules[0].service_completion, false);

// ── The computation standard ──────────────────────────────────────────────
const std = engine.COMPUTATION_STANDARDS.ct_pb_63_2;
check('ct_pb_63_2 is registered', !!std, true);
check('NO short-period exclusion -- absent, not zero',
  'short_period_exclusion_days' in std, false);
check('it maps onto the frcp_6a implementation', std.impl, 'frcp_6a');
// The counting rule and the trial-court rollover are in different chapters of
// the Practice Book, so the rollover step must name both or it sends a
// Superior Court filer to the appellate rules.
check('the rollover step cites Sec. 7-17 alongside Sec. 63-2',
  std.label + std.rollover_suffix_forward, 'Conn. Practice Book Sec. 63-2 with Sec. 7-17');
check('backward is blank -- no backward provision was found',
  std.rollover_suffix_backward, '');

// ── THE HOLD ──────────────────────────────────────────────────────────────
// 2026-09-01 is a Tuesday; +30 lands 2026-10-01, a Thursday. Nothing about
// this date needs a calendar to resolve a weekend, and it MUST still refuse.
check('a weekday landing still refuses', codeOf(compute('2026-09-01')), 'NOT_PROVISIONED');
// 2026-09-03 is a Thursday; +30 lands 2026-10-03, a Saturday.
check('a Saturday landing refuses', codeOf(compute('2026-09-03')), 'NOT_PROVISIONED');
// 2026-09-04 is a Friday; +30 lands 2026-10-04, a Sunday.
check('a Sunday landing refuses', codeOf(compute('2026-09-04')), 'NOT_PROVISIONED');
// New Year's Day is the case rollOff's comment names as the reason it refuses
// on an unknown calendar rather than treating the year as holiday-free.
check('a New Years Day landing refuses', codeOf(compute('2026-12-02')), 'NOT_PROVISIONED');

const r = compute('2026-09-01');
check('the refusal names the jurisdiction, not a year',
  [r.missing.jurisdiction, r.missing.year], ['ct', null]);
check('the refusal says the date was not computed rather than computed badly',
  /is not computed rather than computed against an incomplete calendar/.test(r.message), true);

// ── The traps ─────────────────────────────────────────────────────────────
check('return_day does NOT match this rule',
  codeOf(engine.computeDeadline({
    jurisdiction: 'ct', domain: 'civil-litigation', trigger_event: 'return_day',
    trigger_date: '2026-09-01', rules: seed.rules, calendars: calendars, as_of: '2026-09-01'
  })), 'NO_MATCHING_RULE');
check('a pre-2014 trigger refuses on effective_from, before the calendar',
  codeOf(compute('2013-06-01')), 'NO_RULE_IN_FORCE');

// ── Nothing else moved ────────────────────────────────────────────────────
check('Connecticut declares NO coverage entry -- it never computes, so one would be dormant',
  Object.keys(engine.JURISDICTION_COVERAGE).sort(), ['al', 'ar', 'ma', 'md', 'mn', 'mo', 'va', 'wi']);
check('Connecticut adds no service-completion standard',
  Object.keys(engine.SERVICE_COMPLETION_STANDARDS), ['mo_rule_43_01_d']);
// A pre-existing jurisdiction must be untouched by the new standard.
{
  const mnSeed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_minnesota.json'), 'utf8'));
  const mnCal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_minnesota.json'), 'utf8'));
  const mc = {};
  for (const row of mnCal.holiday_calendars) {
    mc[row.jurisdiction] = mc[row.jurisdiction] || {};
    mc[row.jurisdiction][String(row.year)] = row.dates;
  }
  const mr = engine.computeDeadline({
    jurisdiction: 'mn', domain: 'civil-litigation', trigger_event: 'service_of_summons',
    trigger_date: '2026-05-01', rules: mnSeed.rules, calendars: mc, as_of: '2026-05-01'
  });
  check('Minnesota still computes normally alongside an unprovisioned neighbour',
    [mr.ok, mr.due_date], [true, '2026-05-22']);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
