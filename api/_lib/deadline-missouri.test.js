// Missouri deadline rows -- isolated verification against the REAL engine and
// the REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Every expected date below was worked out BY HAND from the rule text and the
// RSMo 9.010 holiday list BEFORE the engine was run, and the cases target what
// actually differs in Missouri rather than convenient Tuesdays:
//
//   - LINCOLN DAY (12 Feb) and TRUMAN DAY (8 May), which no other jurisdiction
//     in this engine has, used to prove the calendar is genuinely being read
//   - the SERVICE-COMPLETION mechanism: fax/e-mail/e-filing move the TRIGGER
//     DATE and add nothing, while mail adds three days and never shifts
//   - the HARD refusal when service_time is missing for a completion-governed
//     method, which is a different refusal from Virginia's soft one
//   - the 45/45/60 defendant floors, where admissions is the outlier and
//     silence ADMITS
//   - the SUNDAY-ONLY shift, and the Saturday holiday it correctly leaves alone
//
// Run: node api/_lib/deadline-missouri.test.js
'use strict';

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_missouri.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_missouri.json'), 'utf8'));

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
    jurisdiction: 'mo', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── The seed's own shape ──────────────────────────────────────────────────
check('14 rules seeded', seed.rules.length, 14);
check('all rows are jurisdiction mo', seed.rules.every(r => r.jurisdiction === 'mo'), true);
check('every row uses mo_rule_44_01_a', seed.rules.every(r => r.computation === 'mo_rule_44_01_a'), true);
check('every rule id is unique', new Set(seed.rules.map(r => r.rule_id)).size, seed.rules.length);
check('every row cites a real quote and url',
  seed.rules.every(r => r.authority && r.authority.quote && r.authority.url), true);
// EXACTLY the three plain discovery rows carry BOTH mechanisms. That pairing is
// the Missouri design, not a duplicate, and it must not spread.
check('exactly the three plain discovery rows carry BOTH extension and completion',
  seed.rules.filter(r => r.service_extension && r.service_completion).map(r => r.rule_id),
  ['mo-r-57-01-c1-interrogatory-answers',
   'mo-r-58-01-c1-production-response',
   'mo-r-59-01-d1-admission-response']);
check('no row carries a completion standard without an extension, or vice versa',
  seed.rules.filter(r => !!r.service_extension !== !!r.service_completion).length, 0);
check('no later_of row carries either service mechanism',
  seed.rules.filter(r => r.trigger_event && r.trigger_event.resolve_periods)
    .every(r => !r.service_extension && !r.service_completion), true);
// THE OVERLAP THAT MUST NEVER EXIST: a method cannot both add days and shift.
check('no method appears in both applies_when and the completion standard',
  seed.rules.filter(r => r.service_extension && r.service_completion)
    .flatMap(r => (r.service_extension.applies_when || [])
      .filter(m => engine.SERVICE_COMPLETION_STANDARDS[r.service_completion.standard].governs(m))),
  []);

// ── The standards ─────────────────────────────────────────────────────────
check('mo_rule_44_01_a declares the 7-day short-period exclusion, NOT eleven',
  engine.COMPUTATION_STANDARDS.mo_rule_44_01_a.short_period_exclusion_days, 7);
check('mo_rule_44_01_a leaves backward blank',
  engine.COMPUTATION_STANDARDS.mo_rule_44_01_a.rollover_suffix_backward, '');
check('mo_rule_44_01_d extends for MAIL AND ONLY MAIL',
  ['mail', 'email', 'facsimile', 'efiling_service', 'electronic']
    .filter(m => engine.SERVICE_EXTENSION_STANDARDS.mo_rule_44_01_d.qualifies(m)), ['mail']);
check('mo_rule_44_01_d lengthens the period',
  engine.SERVICE_EXTENSION_STANDARDS.mo_rule_44_01_d.sequence, 'add_to_period_then_roll');
check('mo_rule_43_01_d governs the three electronic methods and NOT mail',
  ['mail', 'facsimile', 'email', 'efiling_service']
    .filter(m => engine.SERVICE_COMPLETION_STANDARDS.mo_rule_43_01_d.governs(m)),
  ['facsimile', 'email', 'efiling_service']);
check('mo_rule_43_01_d cutoff is 17:00 exactly',
  engine.SERVICE_COMPLETION_STANDARDS.mo_rule_43_01_d.cutoff_minutes, 17 * 60);
check('Missouri is the only jurisdiction with a completion standard so far',
  Object.keys(engine.SERVICE_COMPLETION_STANDARDS), ['mo_rule_43_01_d']);

// ── Coverage disclosure ──────────────────────────────────────────────────
const disc = compute('mo-r-55-25a-answer-after-personal-service', '2026-05-01');
check('a Missouri computation still succeeds', disc.ok, true);
check('coverage is present and incomplete', disc.coverage && disc.coverage.complete, false);
check('coverage direction is early', disc.coverage.direction, 'early');
check('coverage discloses the CONVERGENCE basis, not a false cross-reference',
  /CONVERGENCE/.test(disc.coverage.detail) && /Kentucky/.test(disc.coverage.detail), true);

// ── The calendar ─────────────────────────────────────────────────────────
const mo26 = calendars.mo['2026'].map(d => d.date);
check('13 statutory holidays in 2026', mo26.length, 13);
check('LINCOLN DAY 12 February is a Missouri holiday', mo26.includes('2026-02-12'), true);
check('TRUMAN DAY 8 May is a Missouri holiday', mo26.includes('2026-05-08'), true);
// SUNDAY-ONLY SHIFT. 4 July 2026 is a Saturday and RSMo 9.010 does NOT move it.
// A Friday 3 July entry would mean a Virginia/West Virginia generator was copied.
check('Independence Day 2026 stays on SATURDAY 4 July -- no Saturday shift exists',
  mo26.includes('2026-07-04') && !mo26.includes('2026-07-03'), true);
check('no calendar entry ever falls on a SUNDAY',
  Object.keys(calendars.mo).every(y => calendars.mo[y]
    .every(d => new Date(d.date + 'T00:00:00Z').getUTCDay() !== 0)), true);

// ── Computations, hand-checked ───────────────────────────────────────────
// Fri 2026-05-01 +30 = Sun 2026-05-31 -> Mon 2026-06-01.
check('R. 55.25(a) 30-day answer rolls off a Sunday',
  dateOf(compute('mo-r-55-25a-answer-after-personal-service', '2026-05-01')), '2026-06-01');
// Tue 2026-01-13 +30 = Thu 2026-02-12 = LINCOLN DAY -> Fri 2026-02-13. No other
// jurisdiction in this engine has that holiday, so nothing else could roll here.
check('R. 55.25(a) rolls off LINCOLN DAY',
  dateOf(compute('mo-r-55-25a-answer-after-personal-service', '2026-01-13')), '2026-02-13');
// Wed 2026-04-08 +30 = Fri 2026-05-08 = TRUMAN DAY -> Mon 2026-05-11.
check('R. 55.25(a) rolls off TRUMAN DAY into the following Monday',
  dateOf(compute('mo-r-55-25a-answer-after-personal-service', '2026-04-08')), '2026-05-11');
// The answer takes neither mechanism: Rule 54 service, not Rule 43.
{
  const r = compute('mo-r-55-25a-answer-after-personal-service', '2026-05-01', { service_method: 'mail' });
  check('answer: mail adds nothing', r.due_date, '2026-06-01');
  check('answer: extension state is not_requested', r.service_extension.state, 'not_requested');
  check('answer: no completion block at all', r.service_completion, null);
}
// The publication branch is 45 days, not 30. Fri 2026-05-01 +45 = Mon 06-15.
check('R. 55.25(a) publication branch is 45 days',
  dateOf(compute('mo-r-55-25a-answer-after-publication', '2026-05-01')), '2026-06-15');
// The 20-day ordered-reply row. Fri 2026-05-01 +20 = Thu 2026-05-21.
check('R. 55.25(b) ordered reply is 20 days from ENTRY of the order',
  dateOf(compute('mo-r-55-25b-reply-ordered-by-court', '2026-05-01')), '2026-05-21');
// 10 days is NOT less than seven, so every day counts. Fri 05-22 +10 = Mon 06-01.
check('R. 55.25(c) 10 days counts every intermediate day',
  dateOf(compute('mo-r-55-25c-responsive-pleading-after-motion-denied', '2026-05-22')), '2026-06-01');

// ── Mail: three days, no shift ───────────────────────────────────────────
// Discovery served Fri 2026-05-01: +30 = Sun 05-31, +3 = Wed 2026-06-03.
{
  const r = compute('mo-r-57-01-c1-interrogatory-answers', '2026-05-01', { service_method: 'mail' });
  check('interrogatories by mail: +3 days, period-lengthening', r.due_date, '2026-06-03');
  check('interrogatories by mail: 3 days recorded', r.service_extension.days_added, 3);
  // Mail is NOT governed by the completion rule -- reported distinctly from
  // "no completion standard exists", so a reader can tell it was considered.
  check('mail is reported as not_governed by the completion standard',
    r.service_completion.state, 'not_governed');
  check('mail needs no service_time', r.ok, true);
}

// ── Completion: electronic service shifts the TRIGGER and adds nothing ───
// Served by e-mail Fri 2026-05-01 at 10:00 -> complete same day -> +30 = Sun
// 05-31 -> Mon 2026-06-01. Identical to no service method at all.
{
  const r = compute('mo-r-57-01-c1-interrogatory-answers', '2026-05-01',
    { service_method: 'email', service_time: '10:00' });
  check('e-mail before 5pm on a business day: complete on transmission', r.due_date, '2026-06-01');
  check('e-mail adds NO days', r.service_extension.days_added, 0);
  check('completion state is complete_on_transmission', r.service_completion.state, 'complete_on_transmission');
  check('trigger_date reported is the transmission date', r.trigger_date, '2026-05-01');
}
// AT 17:00 EXACTLY is NOT "after 5:00 p.m." -- the boundary minute.
check('e-mail at exactly 17:00 is still complete on transmission',
  compute('mo-r-57-01-c1-interrogatory-answers', '2026-05-01',
    { service_method: 'email', service_time: '17:00' }).due_date, '2026-06-01');
// 17:01 IS after. Complete Mon 2026-05-04 -> +30 = Wed 2026-06-03.
{
  const r = compute('mo-r-57-01-c1-interrogatory-answers', '2026-05-01',
    { service_method: 'email', service_time: '17:01' });
  check('e-mail at 17:01 on a Friday is complete the following MONDAY', r.trigger_date, '2026-05-04');
  check('e-mail at 17:01: the whole period runs from the shifted date', r.due_date, '2026-06-03');
  check('completion state is shifted', r.service_completion.state, 'shifted');
  check('completion records what was transmitted vs when complete',
    [r.service_completion.transmitted, r.service_completion.complete_on], ['2026-05-01', '2026-05-04']);
  check('a service_completion step appears in the audit trail',
    r.steps.some(s => s.step === 'service_completion'), true);
}
// THE SHIFT ALSO CLEARS HOLIDAYS, WHICH VIRGINIA'S CUTOFF DOES NOT.
// Transmitted Thu 2026-05-07 at 18:00 -> next day is Fri 2026-05-08 = TRUMAN
// DAY -> so complete Mon 2026-05-11. +30 = Wed 2026-06-10.
{
  const r = compute('mo-r-58-01-c1-production-response', '2026-05-07',
    { service_method: 'facsimile', service_time: '18:00' });
  check('a fax after 5pm rolls past TRUMAN DAY to the next open day',
    r.service_completion.complete_on, '2026-05-11');
  check('and the period runs from there', r.due_date, '2026-06-10');
}
// Transmitted ON a Saturday, before 5pm -- the day itself is bad, so it shifts
// regardless of the clock. Sat 2026-05-09 -> Mon 2026-05-11.
check('transmission ON a Saturday shifts even at 09:00',
  compute('mo-r-58-01-c1-production-response', '2026-05-09',
    { service_method: 'efiling_service', service_time: '09:00' }).service_completion.complete_on,
  '2026-05-11');

// ── The HARD refusal, which is what distinguishes this from Virginia ─────
{
  const r = compute('mo-r-57-01-c1-interrogatory-answers', '2026-05-01', { service_method: 'email' });
  check('a completion-governed method with NO service_time refuses OUTRIGHT', r.ok, false);
  check('and names its own code', r.code, 'SERVICE_COMPLETION_TIME_REQUIRED');
  check('the message says why a date cannot be produced at all',
    /period RUNS FROM/.test(r.message) && /service_time/.test(r.message), true);
}
check('a malformed service_time is refused, not parsed leniently',
  compute('mo-r-57-01-c1-interrogatory-answers', '2026-05-01',
    { service_method: 'facsimile', service_time: '5:00 PM' }).code, 'SERVICE_COMPLETION_TIME_REQUIRED');
// Virginia's equivalent refusal is SOFT -- it still returns a date. The two must
// stay distinguishable, because they mean different things.
{
  const vaSeed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_virginia.json'), 'utf8'));
  const vaCal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_virginia.json'), 'utf8'));
  const vc = {};
  for (const row of vaCal.holiday_calendars) {
    vc[row.jurisdiction] = vc[row.jurisdiction] || {};
    vc[row.jurisdiction][String(row.year)] = row.dates;
  }
  const r = engine.computeDeadline({
    jurisdiction: 'va', domain: 'civil-litigation', trigger_event: 'service_of_interrogatories',
    trigger_date: '2026-05-01', service_method: 'manual_delivery',
    rules: vaSeed.rules, calendars: vc, as_of: '2026-05-01'
  });
  check('Virginia\'s missing-time refusal is still SOFT and returns a date',
    [r.ok, r.service_extension.state, r.due_date],
    [true, 'refused_missing_context', '2026-05-22']);
}

// ── The 45/45/60 defendant floors ────────────────────────────────────────
// Served with the complaint, both 2026-05-01: 30-day limb ends 05-31, floor
// limb ends 06-15 (45) or 06-30 (60). The floor governs in each case.
function floorCase(triggerId, evA, evB, expected) {
  const t = {};
  t[evA] = '2026-05-01';
  t[evB] = '2026-05-01';
  return dateOf(engine.computeDeadline({
    jurisdiction: 'mo', domain: 'civil-litigation', trigger_event: triggerId,
    trigger_dates: t, rules: seed.rules, calendars: calendars, as_of: '2026-05-01'
  }));
}
check('interrogatories defendant floor is 45 days',
  floorCase('interrogatories_on_defendant', 'service_of_interrogatories_on_defendant',
    'earlier_of_defendant_appearance_or_service_of_process_for_interrogatories'), '2026-06-15');
check('production defendant floor is also 45 days',
  floorCase('production_request_on_defendant', 'service_of_request_for_production_on_defendant',
    'earlier_of_defendant_appearance_or_service_of_process_for_production'), '2026-06-15');
// THE OUTLIER. Admissions is SIXTY, and silence ADMITS, so reading 45 here
// would compute EARLY on the most consequential deadline in the seed.
check('admissions defendant floor is SIXTY days, not 45',
  floorCase('admission_request_on_defendant', 'service_of_request_for_admission_on_defendant',
    'earlier_of_defendant_appearance_or_service_of_process_for_admission'), '2026-06-30');
check('the three floors really are 45/45/60 in the data',
  ['mo-r-57-01-c1-interrogatory-answers-defendant-later-of-periods',
   'mo-r-58-01-c1-production-response-defendant-later-of-periods',
   'mo-r-59-01-d1-admission-response-defendant-later-of-periods']
    .map(id => seed.rules.find(r => r.rule_id === id).trigger_event.limbs[1].count.value),
  [45, 45, 60]);

// ── Refusals that must stay refusals ─────────────────────────────────────
check('a pre-2021 interrogatory trigger is refused',
  compute('mo-r-57-01-c1-interrogatory-answers', '2020-05-01').ok, false);
check('a year outside the loaded calendars refuses',
  compute('mo-r-55-25a-answer-after-personal-service', '2033-05-01').code, 'NOT_PROVISIONED');

// ── Blast radius ─────────────────────────────────────────────────────────
check('three jurisdictions declare a coverage gap',
  Object.keys(engine.JURISDICTION_COVERAGE).sort(), ['ma', 'mo', 'va']);
// A pre-existing jurisdiction must compute exactly what it did before the
// completion mechanism was inserted into the pipeline.
{
  const maSeed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_massachusetts.json'), 'utf8'));
  const maCal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_massachusetts.json'), 'utf8'));
  const mc = {};
  for (const row of maCal.holiday_calendars) {
    mc[row.jurisdiction] = mc[row.jurisdiction] || {};
    mc[row.jurisdiction][String(row.year)] = row.dates;
  }
  const r = engine.computeDeadline({
    jurisdiction: 'ma', domain: 'civil-litigation',
    trigger_event: 'service_of_pleading_requiring_responsive_pleading', trigger_date: '2026-05-01',
    service_method: 'email', rules: maSeed.rules, calendars: mc, as_of: '2026-05-01'
  });
  check('Massachusetts e-mail still ADDS three days and is not shifted',
    [dateOf(r), r.service_extension.days_added, r.service_completion], ['2026-05-26', 3, null]);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
