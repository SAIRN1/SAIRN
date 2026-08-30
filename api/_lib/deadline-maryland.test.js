// Maryland deadline rows -- isolated verification against the REAL engine and
// the REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Maryland is the first jurisdiction that needed an ENGINE change rather than
// only a standard, and the first with an ambiguity that has no safe side. The
// cases target exactly the things that would be wrong if anything here were
// carried across from a neighbour:
//
//   - THE EXCLUSION THRESHOLD IS 8, not 7. "Seven days or less" is <= 7, which
//     is < 8, and the field is compared with a strict less-than. Asserted as
//     ARITHMETIC at exactly seven days, which is where writing 7 would break.
//   - THE EXCLUSION IS FORWARD-ONLY. Rule 1-203(b) counts backward periods
//     "including intervening Saturdays, Sundays, and holidays". Asserted with a
//     SYNTHETIC backward rule, because no seeded Maryland row counts backward
//     yet -- the engine behaviour is what is being pinned, not a seed row.
//   - THE MAIL EXTENSION REFUSES ON A SHORT PERIOD (decision one). Also
//     asserted synthetically: no seeded Maryland row is seven days or shorter,
//     so the refusal is currently unreachable from the seed by construction.
//   - THE CHAINED FLOOR TAKES A CALLER-SUPPLIED DATE (decision two), on four
//     rows, one of which -- Rule 2-424 -- DEEMS FACTS ADMITTED if missed.
//   - TWO CALENDAR ENTRIES NOTHING ELSE HERE HAS: Election Day (even years
//     only) and American Indian Heritage Day.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_maryland.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_maryland.json'), 'utf8'));

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
    jurisdiction: 'md', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// A rule that does not exist in the seed, used ONLY to reach engine behaviour
// no seeded Maryland row can reach yet. Stated plainly so nobody mistakes it
// for coverage.
function synthetic(over) {
  return Object.assign({
    rule_id: 'md-synthetic', jurisdiction: 'md', domain: 'civil-litigation',
    label: 'synthetic', trigger_event: 'synthetic_event', computation: 'md_rule_1_203',
    count: { value: 5, unit: 'calendar_days', direction: 'backward' },
    authority: { citation: 'Md. Rule 1-203', url: 'x', quote: 'x' },
    effective_from: '1984-07-01', effective_to: null
  }, over || {});
}
function computeSynthetic(rule, triggerDate, extra) {
  return engine.computeDeadline(Object.assign({
    jurisdiction: 'md', domain: 'civil-litigation', trigger_event: 'synthetic_event',
    trigger_date: triggerDate, rules: [rule], calendars: calendars, as_of: triggerDate
  }, extra || {}));
}

// ── The seed's own shape ──────────────────────────────────────────────────
check('11 rules seeded', seed.rules.length, 11);
check('every rule is Maryland civil litigation on md_rule_1_203',
  seed.rules.filter(r => r.jurisdiction === 'md' && r.domain === 'civil-litigation'
    && r.computation === 'md_rule_1_203').length, 11);
check('FOUR rows take the caller-supplied chained date',
  seed.rules.filter(r => typeof r.trigger_event !== 'string'
    && r.trigger_event.limbs.some(l => l.event === 'date_initial_pleading_is_required')).length, 4);
// No seeded row is seven days or shorter, so decision one's refusal cannot be
// reached from the seed today. Stated as an assertion so it stays true or the
// test fails when someone adds a short row.
check('NO seeded Maryland row is 7 calendar days or shorter',
  seed.rules.filter(r => r.count && r.count.unit === 'calendar_days' && r.count.value <= 7).length, 0);

// ── The standard, and the two numbers that had to be read ────────────────
const std = engine.COMPUTATION_STANDARDS.md_rule_1_203;
check('THE THRESHOLD IS 8, not the 7 in the rule text', std.short_period_exclusion_days, 8);
check('and the exclusion is FORWARD-ONLY', std.short_period_exclusion_directions, ['forward']);

// ── The mail extension: mail only, and it REFUSES on a short period ───────
const ext = engine.SERVICE_EXTENSION_STANDARDS.md_rule_1_203_c;
check('mail qualifies; e-mail and personal service do not -- (c) names mail alone',
  ['mail', 'electronic_mail', 'personal'].map(m => ext.qualifies(m)), [true, false, false]);
check('a 30-day period takes the three days',
  ext.amount('mail', { base_period_count: 30, base_period_unit: 'calendar_days' }),
  { add: 3, unit: 'calendar_days' });
check('a SEVEN-day period REFUSES -- the two readings have no safe side',
  Object.keys(ext.amount('mail', { base_period_count: 7, base_period_unit: 'calendar_days' })), ['refuse']);
check('an EIGHT-day period does not refuse -- the interaction cannot arise',
  ext.amount('mail', { base_period_count: 8, base_period_unit: 'calendar_days' }),
  { add: 3, unit: 'calendar_days' });

// ── The calendar ─────────────────────────────────────────────────────────
const d2026 = Object.fromEntries(calendars.md['2026'].map(d => [d.date, d.name]));
check('thirteen dates', calendars.md['2026'].length, 13);
check('ELECTION DAY and AMERICAN INDIAN HERITAGE DAY are both present',
  [d2026['2026-11-03'], d2026['2026-11-27']],
  ['Election Day', 'American Indian Heritage Day']);
check('Independence Day is the SATURDAY-shifted Friday, and 07-04 is absent',
  [!!d2026['2026-07-03'], !!d2026['2026-07-04']], [true, false]);
// The four days General Provisions 1-111 would have added, none of which is a
// court holiday. Their presence would report LATE.
check('Good Friday, Lincoln\'s Birthday, Maryland Day and Defenders\' Day are ABSENT',
  ['2026-04-03', '2026-02-12', '2026-03-25', '2026-09-12'].map(d => !!d2026[d]),
  [false, false, false, false]);

// ── The answer rows ──────────────────────────────────────────────────────
// 2026-05-01 Fri + 30 = 2026-05-31 SUNDAY -> Mon 2026-06-01.
check('Rule 2-321(a): 30 days, Sunday rollover',
  dateOf(compute('md-rule-2-321a-answer-30-days', '2026-05-01')), '2026-06-01');
// Mail: 30 is above the threshold so no refusal. Period end 05-31 + 3 = 06-03 Wed.
check('and mail adds three days to the PERIOD, then rolls once',
  dateOf(compute('md-rule-2-321a-answer-30-days', '2026-05-01', { service_method: 'mail' })),
  '2026-06-03');
check('60-day and 90-day service branches',
  [dateOf(compute('md-rule-2-321b1-answer-60-days-served-outside-state', '2026-05-01')),
   dateOf(compute('md-rule-2-321b5-answer-90-days-served-outside-us', '2026-05-01'))],
  ['2026-06-30', '2026-07-30']);
// The gap between the default and the 90-day branch is two months.
check('the default row and the outside-the-US row genuinely differ',
  dateOf(compute('md-rule-2-321a-answer-30-days', '2026-05-01'))
    !== dateOf(compute('md-rule-2-321b5-answer-90-days-served-outside-us', '2026-05-01')), true);

// ── The two distinctive holidays, as arithmetic ──────────────────────────
// 2026-10-04 Sun + 30 = 2026-11-03, ELECTION DAY -> Wed 11-04.
check('rolls off ELECTION DAY, which only exists in even years',
  dateOf(compute('md-rule-2-321a-answer-30-days', '2026-10-04')), '2026-11-04');
// 2026-10-28 Wed + 30 = 2026-11-27, AMERICAN INDIAN HERITAGE DAY, then the
// weekend -> Mon 11-30.
check('rolls off AMERICAN INDIAN HERITAGE DAY and through the weekend',
  dateOf(compute('md-rule-2-321a-answer-30-days', '2026-10-28')), '2026-11-30');

// ── The 15-day rows, and the notice-vs-service split ─────────────────────
// 2026-05-01 + 15 = 2026-05-16 SATURDAY -> Mon 2026-05-18. 15 is above the
// threshold, so intermediate days are counted.
check('Rule 2-321(c) after an order: 15 days, no extension on mail',
  [dateOf(compute('md-rule-2-321c-answer-after-preliminary-motion-or-remand', '2026-05-01')),
   dateOf(compute('md-rule-2-321c-answer-after-preliminary-motion-or-remand', '2026-05-01',
     { service_method: 'mail' }))],
  ['2026-05-18', '2026-05-18']);
// The sibling limb runs from SERVICE, so it takes the three days: 05-16 + 3 =
// 05-19 Tue.
check('the more-definite-statement limb DOES take the three days',
  dateOf(compute('md-rule-2-321c-answer-after-more-definite-statement', '2026-05-01',
    { service_method: 'mail' })), '2026-05-19');

// ── DECISION TWO: the caller-supplied chained date ───────────────────────
{
  // Request served 05-01 (+30 -> 05-31 Sun -> 06-01). Pleading due 06-15
  // (+15 -> 06-30 Tue). The floor wins.
  const late = {
    service_of_interrogatories: '2026-05-01',
    date_initial_pleading_is_required: '2026-06-15'
  };
  check('2-421: the chained floor wins when the pleading is due later',
    dateOf(compute('md-rule-2-421b-interrogatory-response-later-of', '2026-05-01',
      { trigger_dates: late })), '2026-06-30');
  // Pleading due 04-01 (+15 -> 04-16). The plain 30 days wins.
  const early = {
    service_of_interrogatories: '2026-05-01',
    date_initial_pleading_is_required: '2026-04-01'
  };
  check('2-421: the plain 30 days wins when the pleading was due earlier',
    dateOf(compute('md-rule-2-421b-interrogatory-response-later-of', '2026-05-01',
      { trigger_dates: early })), '2026-06-01');
}
{
  // Rule 2-424 is the one where silence DEEMS FACTS ADMITTED. Same shape.
  const dates = {
    service_of_request_for_admission: '2026-05-01',
    date_initial_pleading_is_required: '2026-06-15'
  };
  check('2-424 admissions: the chained floor wins -- the rule that deems facts admitted',
    dateOf(compute('md-rule-2-424b-admission-response-later-of', '2026-05-01',
      { trigger_dates: dates })), '2026-06-30');
}
{
  // Rule 2-311(b)'s second limb is the required DATE itself, count 0.
  // Motion served 05-01 (+15 -> 05-16 Sat -> 05-18). Pleading due 06-15 (+0).
  const dates = {
    service_of_motion: '2026-05-01',
    date_initial_pleading_is_required: '2026-06-15'
  };
  check('2-311(b): the zero-count limb returns the supplied date itself',
    dateOf(compute('md-rule-2-311b-response-to-motion-later-of', '2026-05-01',
      { trigger_dates: dates })), '2026-06-15');
}

// ── ENGINE BEHAVIOUR NO SEEDED ROW REACHES YET ───────────────────────────
// Synthetic, and labelled as such. A 5-day BACKWARD period from Mon 2026-06-08:
// Maryland counts all intervening days, so Jun 7, 6, 5, 4, 3 -> 2026-06-03 Wed.
// If the forward exclusion were wrongly applied it would skip Sat 6 and Sun 7
// and answer 2026-06-01 -- two days LATER than the rule allows, which on a
// backward period means telling someone they may still serve after the last
// lawful day.
check('BACKWARD periods count intervening weekends -- the exclusion is forward-only',
  dateOf(computeSynthetic(synthetic(), '2026-06-08')), '2026-06-03');
check('and the wrongly-excluded answer, 2026-06-01, is NOT what it returns',
  dateOf(computeSynthetic(synthetic(), '2026-06-08')) !== '2026-06-01', true);
// A forward 5-day period DOES exclude: from Mon 2026-05-18, Tue 19, Wed 20,
// Thu 21, Fri 22, [23/24], Mon 25 is MEMORIAL DAY, so Tue 2026-05-26.
check('a FORWARD short period still excludes weekends and holidays',
  dateOf(computeSynthetic(synthetic({ count: { value: 5, unit: 'calendar_days', direction: 'forward' } }),
    '2026-05-18')), '2026-05-26');
// And decision one, reached synthetically: a mailed 7-day period refuses.
{
  const r = computeSynthetic(
    synthetic({ count: { value: 7, unit: 'calendar_days', direction: 'forward' },
      service_extension: { standard: 'md_rule_1_203_c', add: 3, unit: 'calendar_days',
        applies_when: ['mail'], order: 'after_base_period' } }),
    '2026-05-01', { service_method: 'mail' });
  check('a MAILED seven-day period refuses the extension and returns the unextended date',
    [r.ok, r.service_extension && r.service_extension.state], [true, 'refused_missing_context']);
  check('and the refusal names both readings rather than picking one',
    [/EARLIER/.test(r.service_extension.detail), /LATER/.test(r.service_extension.detail)],
    [true, true]);
}

// ── The coverage disclosure ──────────────────────────────────────────────
{
  const r = compute('md-rule-2-321a-answer-30-days', '2026-05-01');
  check('Maryland discloses the clerk-closure trigger, direction EARLY',
    [r.ok, r.coverage && r.coverage.direction], [true, 'early']);
  check('and the disclosure records the wrong-source trap',
    [/1-302/.test(r.coverage.detail), /1-111/.test(r.coverage.detail)], [true, true]);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
