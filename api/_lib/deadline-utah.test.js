// Utah deadline rows -- isolated verification against the REAL engine and the
// REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Every expected date below was worked out BY HAND from the rule text and the
// derived URCP 6(a)(6) holiday list BEFORE the engine was run, and the cases
// target what actually differs in Utah:
//
//   - the ROLLOVER CLAUSE NAMES BOTH WEEKEND DAYS ITSELF (6(a)(1)(C)), the
//     first seeded jurisdiction where the standing weekend-coverage check
//     stops at step one
//   - NO short-period exclusion at all (6(a)(1)(B) counts every intermediate
//     day), where six seeded states use 7 and three use 11 -- the field must
//     be ABSENT, not a number
//   - the OBSERVATION SHIFT in Utah Code 63G-1-301(2): Independence Day 2026
//     falls on a Saturday and is observed FRIDAY 3 JULY, so a period landing
//     on 3 July rolls a full three days to Monday 6 July. Encoding 4 July
//     instead would report that deadline a day EARLY
//   - JUNETEENTH ON THE THIRD MONDAY OF JUNE (2026-06-15), not 19 June
//   - THE 2026 CALENDAR CAP: a period landing in 2027 must REFUSE, because
//     Utah Code 63G-1-301 is superseded 1/1/2027 and moves Juneteenth
//   - the 21-day in-state / 30-day out-of-state split being TWO ROWS with
//     distinct triggers, since picking the wrong one is a nine-day error
//   - NO ROW CARRYING A SERVICE EXTENSION, held deliberately: URCP 6(c)'s
//     seven days apply only to service made EXCLUSIVELY by mail, and this
//     engine's single service_method field cannot express exclusivity
//
// Run: node api/_lib/deadline-utah.test.js
'use strict';

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_utah.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_utah.json'), 'utf8'));

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
    jurisdiction: 'ut', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── The seed's own shape ──────────────────────────────────────────────────
check('9 rules seeded', seed.rules.length, 9);
check('all rows are jurisdiction ut', seed.rules.every(r => r.jurisdiction === 'ut'), true);
check('every row uses ut_urcp_6', seed.rules.every(r => r.computation === 'ut_urcp_6'), true);
check('every rule id is unique', new Set(seed.rules.map(r => r.rule_id)).size, seed.rules.length);
check('every row cites a real quote and url',
  seed.rules.every(r => r.authority.quote && /^https?:\/\//.test(r.authority.url)), true);
check('every row counts calendar days forward',
  seed.rules.every(r => r.count.unit === 'calendar_days' && r.count.direction === 'forward'), true);

// THE HOLD IS LIFTED. Until 2026-08-27 this asserted that NO row carried an
// extension, because URCP 6(c)'s seven days apply only to service made
// "exclusively by mail" and one service_method field could not express that.
// The exclusive-vs-combined mechanism was built that day and the row is now
// seeded, so the assertion becomes its opposite -- with the Rule 4 / Rule 5
// split guarded, which is the part that could still go wrong.
check('the seven Rule 5 rows carry URCP 6(c)',
  seed.rules.filter(r => r.service_extension).map(r => r.rule_id).sort(),
  ['ut-r-12-a-1-A-responsive-pleading-after-motion-resolved',
   'ut-r-12-a-1-B-responsive-pleading-after-more-definite-statement',
   'ut-r-12-a-1-answer-to-counterclaim',
   'ut-r-12-a-1-answer-to-crossclaim',
   'ut-r-33-b-interrogatory-response',
   'ut-r-34-b-2-production-response',
   'ut-r-36-c-1-admission-response']);
// 6(c) points at Rule 5(b)(3)(C)(i); a Utah summons goes out under Rule 4.
check('NEITHER answer-to-summons row carries it -- Rule 4 service',
  seed.rules.filter(r => /answer-(in|out-of)-state$/.test(r.rule_id)).some(r => r.service_extension), false);
check('every extension row declares exclusivity and REFUSES rather than assuming',
  seed.rules.filter(r => r.service_extension)
    .every(r => r.service_extension.requires_exclusive === true
             && r.service_extension.on_unknown_exclusivity === 'refuse'), true);
check('and it is SEVEN days, not a neighbour\'s three',
  [...new Set(seed.rules.filter(r => r.service_extension).map(r => r.service_extension.add))], [7]);
check('NO row carries a service_completion -- 5(b)(4) completes on sending, so it would never move anything',
  seed.rules.some(r => r.service_completion), false);
check('no row declares a designated_period -- Utah discovery has no defendant floor',
  seed.rules.some(r => r.designated_period), false);

// effective_from is REAL PER RULE here, not one restyling date for the batch.
check('effective_from is per-rule, from each rule page\'s own Effective: line',
  seed.rules.map(r => [r.rule_id.slice(0, 8), r.effective_from]).filter(x => x[0] !== 'ut-r-12-'),
  [['ut-r-33-', '2011-11-01'], ['ut-r-34-', '2017-05-01'], ['ut-r-36-', '2021-05-01']]);
check('the Rule 12 rows share Rule 12\'s own date',
  seed.rules.filter(r => /^ut-r-12-/.test(r.rule_id)).every(r => r.effective_from === '2024-05-01'), true);

// ── The computation standard ──────────────────────────────────────────────
const std = engine.COMPUTATION_STANDARDS.ut_urcp_6;
check('ut_urcp_6 is registered', !!std, true);
check('NO short-period exclusion -- absent, not zero', 'short_period_exclusion_days' in std, false);
check('it maps onto the frcp_6a implementation', std.impl, 'frcp_6a');
check('the forward rollover cites 6(a)(1)(C)', std.label + std.rollover_suffix_forward, 'Utah R. Civ. P. 6(a)(1)(C)');
// 6(a)(5) defines backward outright, unlike NJ/NC/WA/MA/MO/WI where it is blank.
check('backward is a REAL citation, not blank', std.rollover_suffix_backward, '(a)(5)');
const uext = engine.SERVICE_EXTENSION_STANDARDS.ut_urcp_6_c;
check('ut_urcp_6_c is registered', !!uext, true);
check('it is mail-only and uses the after-expiry sequencing',
  [uext.qualifies('mail'), uext.qualifies('email'), uext.sequence],
  [true, false, 'roll_then_add_then_roll']);

// ── EXCLUSIVITY, the whole reason this row waited ─────────────────────────
// A bare service_method cannot say whether mail was the ONLY method used, and
// seven days is far too large an overshoot to assume -- so Utah refuses where
// Florida (five days, already live, exclusive service the ordinary case)
// assumes and discloses. The two differ deliberately; see ut_urcp_6_c's note.
check('bare service_method REFUSES the extension and returns the date without it',
  [dateOf(compute('ut-r-33-b-interrogatory-response', '2026-06-01', { service_method: 'mail' })),
   compute('ut-r-33-b-interrogatory-response', '2026-06-01', { service_method: 'mail' }).service_extension.state],
  ['2026-06-29', 'refused_unverified_exclusivity']);
check('an EXCLUSIVE set applies all seven days',
  [dateOf(compute('ut-r-33-b-interrogatory-response', '2026-06-01', { service_method: 'mail', service_methods: ['mail'] })),
   compute('ut-r-33-b-interrogatory-response', '2026-06-01', { service_method: 'mail', service_methods: ['mail'] }).service_extension.days_added],
  ['2026-07-06', 7]);
check('a COMBINED set adds nothing, and says so distinctly from not_qualifying',
  [dateOf(compute('ut-r-33-b-interrogatory-response', '2026-06-01', { service_method: 'mail', service_methods: ['mail', 'email'] })),
   compute('ut-r-33-b-interrogatory-response', '2026-06-01', { service_method: 'mail', service_methods: ['mail', 'email'] }).service_extension.state],
  ['2026-06-29', 'not_exclusive']);
check('e-mail never qualifies in the first place',
  compute('ut-r-33-b-interrogatory-response', '2026-06-01', { service_method: 'email' }).service_extension.state,
  'not_qualifying');
// The refusal must not be silent -- that was the defect this engine already
// fixed once for West Virginia's contested methods.
check('the refusal explains itself and names the input that would resolve it',
  /service_methods/.test(compute('ut-r-33-b-interrogatory-response', '2026-06-01', { service_method: 'mail' }).service_extension.detail), true);
check('supplying mail on an ANSWER row still adds nothing -- no extension seeded there',
  dateOf(compute('ut-r-12-a-1-answer-in-state', '2026-06-01', { service_method: 'mail', service_methods: ['mail'] })), '2026-06-22');

// ── The calendar ──────────────────────────────────────────────────────────
check('the calendar covers 2026 AND NOTHING ELSE', Object.keys(calendars.ut), ['2026']);
check('12 observed days in 2026', calendars.ut['2026'].length, 12);
check('every date is kind: declared', calendars.ut['2026'].every(d => d.kind === 'declared'), true);
check('no observed day lands on a weekend',
  calendars.ut['2026'].every(d => { const w = new Date(d.date + 'T00:00:00Z').getUTCDay(); return w !== 0 && w !== 6; }), true);
// THE TWO UTAH-SPECIFIC DAYS, and the two that are computed rather than fixed.
const byDate = Object.fromEntries(calendars.ut['2026'].map(d => [d.date, d.name]));
check('Pioneer Day is 24 July', byDate['2026-07-24'], 'Pioneer Day');
check('Independence Day 2026 is OBSERVED on Friday 3 July, not Saturday 4 July',
  [byDate['2026-07-03'], byDate['2026-07-04']], ['Independence Day', undefined]);
check('Juneteenth is the THIRD MONDAY of June, not 19 June',
  [byDate['2026-06-15'], byDate['2026-06-19']], ['Juneteenth National Freedom Day', undefined]);
check('Washington and Lincoln Day carries the rule\'s name, not the statute\'s',
  byDate['2026-02-16'], 'Washington and Lincoln Day');
// Good Friday 2026 is 3 April. 6(a)(6) omits it; omitting can only report EARLY.
check('Good Friday is NOT encoded -- 6(a)(6) says "means", and omitting fails EARLY',
  byDate['2026-04-03'], undefined);

// ── Arithmetic ────────────────────────────────────────────────────────────
check('answer in-state: 2026-06-01 + 21 = Monday 2026-06-22',
  dateOf(compute('ut-r-12-a-1-answer-in-state', '2026-06-01')), '2026-06-22');
check('answer out-of-state: the SAME trigger date + 30 = 2026-07-01',
  dateOf(compute('ut-r-12-a-1-answer-out-of-state', '2026-06-01')), '2026-07-01');
check('crossclaim answer is 21 with no out-of-state limb',
  dateOf(compute('ut-r-12-a-1-answer-to-crossclaim', '2026-06-01')), '2026-06-22');
check('counterclaim answer is 21',
  dateOf(compute('ut-r-12-a-1-answer-to-counterclaim', '2026-06-01')), '2026-06-22');
check('14 days after notice of the court\'s action on a Rule 12 motion',
  dateOf(compute('ut-r-12-a-1-A-responsive-pleading-after-motion-resolved', '2026-12-04')), '2026-12-18');
check('14 days after service of a more definite statement',
  dateOf(compute('ut-r-12-a-1-B-responsive-pleading-after-more-definite-statement', '2026-12-04')), '2026-12-18');

// All three discovery devices are 28 -- Utah has no per-device variation.
check('interrogatories: 28 days',
  dateOf(compute('ut-r-33-b-interrogatory-response', '2026-05-25')), '2026-06-22');
check('production: 28 days, same as interrogatories',
  dateOf(compute('ut-r-34-b-2-production-response', '2026-05-25')), '2026-06-22');
check('admissions: 28 days, same again',
  dateOf(compute('ut-r-36-c-1-admission-response', '2026-05-25')), '2026-06-22');

// THE OBSERVATION SHIFT, and the case that proves it is load-bearing.
// 2026-06-12 + 21 lands on 2026-07-03 -- Friday, and the OBSERVED Independence
// Day because 4 July 2026 is a Saturday. The period rolls past the weekend to
// Monday 6 July: THREE days. Encoding 4 July instead of 3 July would return
// 2026-07-03 here, a day EARLY.
check('landing on OBSERVED Independence Day (Fri 3 Jul) rolls three days to Mon 6 Jul',
  dateOf(compute('ut-r-12-a-1-answer-in-state', '2026-06-12')), '2026-07-06');
check('one day earlier lands Thursday 2 July and does NOT roll',
  dateOf(compute('ut-r-12-a-1-answer-in-state', '2026-06-11')), '2026-07-02');
check('landing on Juneteenth (Mon 15 Jun) rolls one day to Tue 16 Jun',
  dateOf(compute('ut-r-12-a-1-answer-in-state', '2026-05-25')), '2026-06-16');
// Utah does NOT make the day after Thanksgiving a holiday, unlike some
// court-observed lists -- so a Thanksgiving landing rolls exactly one day.
check('landing on Thanksgiving rolls ONE day to Friday, not past the weekend',
  dateOf(compute('ut-r-12-a-1-answer-in-state', '2026-11-05')), '2026-11-27');

// ── THE 2026 CAP ──────────────────────────────────────────────────────────
// 2026-12-11 + 21 lands 2027-01-01. There is no 2027 calendar, on purpose,
// because 63G-1-301 is superseded 1/1/2027 and moves Juneteenth. If someone
// adds 2027 without resolving which reading of URCP 6(a)(6)(E) governs, this
// stops failing -- which is the reminder to go and read the generator.
const capped = compute('ut-r-12-a-1-answer-in-state', '2026-12-11');
check('a period landing in 2027 REFUSES rather than computing', dateOf(capped), 'REFUSED:NOT_PROVISIONED');
check('the refusal names the missing YEAR, not the jurisdiction',
  [capped.missing.jurisdiction, capped.missing.year], ['ut', '2027']);
check('a 2027 trigger refuses too',
  dateOf(compute('ut-r-33-b-interrogatory-response', '2027-03-01')), 'REFUSED:NOT_PROVISIONED');

// ── The traps ─────────────────────────────────────────────────────────────
check('a bare "service_of_summons" matches NOTHING -- the split is explicit',
  dateOf(engine.computeDeadline({
    jurisdiction: 'ut', domain: 'civil-litigation', trigger_event: 'service_of_summons',
    trigger_date: '2026-06-01', rules: seed.rules, calendars: calendars, as_of: '2026-06-01'
  })), 'REFUSED:NO_MATCHING_RULE');
check('a pre-2011 trigger refuses on effective_from',
  dateOf(compute('ut-r-33-b-interrogatory-response', '2010-06-01')), 'REFUSED:NO_RULE_IN_FORCE');
// Supplying a service method must NOT quietly add Utah's seven days.
check('supplying service_method: mail adds NOTHING -- no extension is seeded',
  dateOf(compute('ut-r-12-a-1-answer-in-state', '2026-06-01', { service_method: 'mail' })), '2026-06-22');

// ── Nothing else moved ────────────────────────────────────────────────────
check('Utah declares NO coverage entry -- its gaps are all EARLY and row-level',
  Object.keys(engine.JURISDICTION_COVERAGE).sort(), ['ar', 'ma', 'mn', 'mo', 'va']);
check('Utah adds no service-completion standard',
  Object.keys(engine.SERVICE_COMPLETION_STANDARDS), ['mo_rule_43_01_d']);
// Two pre-existing jurisdictions must be untouched by the new standard.
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
  check('Minnesota still computes normally alongside Utah', [mr.ok, mr.due_date], [true, '2026-05-22']);
}
{
  const ctSeed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_connecticut.json'), 'utf8'));
  const cr = engine.computeDeadline({
    jurisdiction: 'ct', domain: 'civil-litigation', trigger_event: 'filing_of_preceding_pleading',
    trigger_date: '2026-09-01', rules: ctSeed.rules, calendars: calendars, as_of: '2026-09-01'
  });
  check('Connecticut still refuses even with a Utah calendar loaded in the same map',
    cr.code, 'NOT_PROVISIONED');
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
