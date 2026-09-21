// Maine Superior and District Court civil deadline rows -- isolated verification
// against the REQUIREMENT: a Maine deadline is computed from MAINE's own rule text,
//   its own statutory holiday list and its own service-extension sequencing,
//   against the real seed and calendar on disk -- no other jurisdiction's data,
//   and no other jurisdiction's SEQUENCING, can produce a Maine answer
//
// REAL engine and the REAL seed/calendar JSON on disk, not a scratch copy.
//
// Eight things would be wrong if carried from a neighbour or from the family, and
// every one of them is driven below rather than asserted from the source:
//
//   - TWENTY DAYS, NOT TWENTY-ONE. Maine never adopted the 2009 federal
//     restyling. A 21 from the FRCP family, Montana or Delaware is one day LATE
//     on every Maine answer.
//   - THE SEQUENCING IS NEW YORK'S, NOT THE FEDERAL ONE. Rule 6(c) says "3 days
//     shall be added to the PRESCRIBED PERIOD", which lengthens the period and
//     rolls once. frcp_6d says "added AFTER the period would otherwise expire",
//     which rolls, adds and rolls again. Driven on a case where the two differ by
//     a day, with the FRCP order the LATER of the two.
//   - MAIL ONLY. frcp_6d also extends for leaving with the clerk and for other
//     consented means, and Maine's Rule 5(b)(2) names all three routes in one
//     sentence while 6(c) picks out only mail. Asserted as a direct disagreement
//     between the two standards on the same method, not just as a shorter list.
//   - THE HOLIDAY CALENDAR IS THE STATUTE, NOT THE PUBLISHED COURT SCHEDULE.
//     Five Fridays across the two seeded years are on the Judicial Branch's list
//     and in no statute. Probed as NEGATIVES -- they must not roll -- and the
//     statutory days probed as positives, including PATRIOT'S DAY, which exists
//     on no other calendar on this platform.
//   - ONE ROW TAKES THE UNDER-7-DAY EXCLUSION and it is the reason that limb is
//     exercised at all. Probed on a count that must skip Juneteenth AND the
//     weekend behind it.
//   - RULES 33 AND 34 CARRY AN ELECTION AND RULE 36 CARRIES A FLOOR -- the same
//     split as Montana and the OPPOSITE of Delaware. Both Rule 36 limbs are
//     probed with each winning in turn, and the extension is probed as scoped to
//     the request limb only.
//   - `impl` IS INERT. The gate predicted Maine would "map to the ohio_civ_r_6a
//     implementation" and flagged the prediction UNVERIFIED. It is verified here
//     by MUTATION rather than by reading: the impl string is replaced with a
//     value naming nothing and the computed date must not move.
//   - NO BACKWARD ROW, AND NO MONTHS OR YEARS. Both are asserted as ABSENCES,
//     because the under-inclusive calendar that is safe forward is unsafe
//     backward, and Rule 6 does not address months at all.

'use strict';

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_maine.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_maine.json'), 'utf8'));

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
    jurisdiction: 'me', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate,
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : 'REFUSED:' + r.code);
const WD = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const weekday = iso => WD[new Date(iso + 'T00:00:00Z').getUTCDay()];

const ANSWER = 'me-mrcivp-12a-answer-after-service-20-days';
const FOREIGN = 'me-mrcivp-12a-answer-served-outside-continental-us-or-canada-50-days';
const CROSS = 'me-mrcivp-12a-answer-to-crossclaim-20-days';
const REPLY = 'me-mrcivp-12a-reply-to-counterclaim-20-days';
const REPLY_ORDER = 'me-mrcivp-12a-reply-after-court-order-20-days';
const AFTER_MOTION = 'me-mrcivp-12a1-responsive-pleading-after-motion-denied-or-postponed-10-days';
const AFTER_MDS = 'me-mrcivp-12a2-responsive-pleading-after-more-definite-statement-10-days';
const ROGS = 'me-mrcivp-33a-interrogatory-answers-30-days';
const PROD = 'me-mrcivp-34b-production-response-30-days';
const ADMIT = 'me-mrcivp-36a-admissions-later-of';
const DEPOBJ = 'me-mrcivp-30b5-objection-to-deposition-production-request-5-days';
const NEWTRIAL = 'me-mrcivp-59b-motion-for-new-trial-14-days';
const ALTER = 'me-mrcivp-59e-motion-to-alter-or-amend-judgment-14-days';
const OPPAFF = 'me-mrcivp-59c-opposing-affidavits-24-days';

// ── 1. THE STANDARD, DECLARED ───────────────────────────────────────────────
const std = engine.COMPUTATION_STANDARDS.me_mr_civ_p_6;
check('me_mr_civ_p_6 exists', !!std, true);
check('label is the rule, not the code', std && std.label, 'M.R. Civ. P. 6');
check('the under-7-day exclusion is declared at 7', std && std.short_period_exclusion_days, 7);
check('the exclusion is NOT per-direction -- Maine has one rule for it, unlike Maryland',
  std && std.short_period_exclusion_directions, undefined);
check('there is no shifted start -- Maine excludes the trigger day, it does not begin at the next business day like Florida',
  std && std.shifted_start, undefined);
check('no weekend_days override -- Rule 6(a) names Saturday and Sunday, the engine default',
  std && std.weekend_days, undefined);
check('the computation and the rollover both cite subdivision (a)',
  [std && std.base_period_suffix, std && std.rollover_suffix_forward], ['(a)', '(a)']);
check('months/years and BACKWARD are deliberately blank -- Rule 6 addresses neither, and backward is a SAFETY bound here',
  [std && std.months_years_suffix, std && std.rollover_suffix_backward], ['', '']);

// `impl` IS INERT, PROVED BY MUTATION. This is the one thing the gate flagged
// UNVERIFIED, and reading the source would only show that nothing appears to use
// it. Replacing it with a value naming no implementation at all and re-driving
// is the check that cannot be satisfied by a misreading.
const implBefore = dateOf(compute(NEWTRIAL, '2026-06-05'));
const savedImpl = std.impl;
std.impl = 'there-is-no-such-implementation';
const implAfter = dateOf(compute(NEWTRIAL, '2026-06-05'));
std.impl = savedImpl;
check('the computed date does not move when impl is replaced with a value naming nothing -- impl is a LABEL and the declared properties are what compute',
  [implBefore, implAfter, implBefore === implAfter], ['2026-06-22', '2026-06-22', true]);
check('and impl was restored so this file leaves no state behind', std.impl, 'ohio_civ_r_6a');

// ── 2. THE SERVICE EXTENSION, AND WHERE IT DISAGREES WITH THE FRCP ──────────
const ext = engine.SERVICE_EXTENSION_STANDARDS.me_mr_civ_p_6_c;
check('me_mr_civ_p_6_c exists', !!ext, true);
check('it cites 6(c)', ext && ext.label, 'M.R. Civ. P. 6(c)');
check('THE SEQUENCING IS add_to_period_then_roll -- "3 days shall be added to the prescribed period", not "after the period would otherwise expire"',
  ext && ext.sequence, 'add_to_period_then_roll');
check('it is an enumerated allowlist, not a negative condition like FRAP 26(c)',
  ext && ext.shape, 'enumerated_allowlist');
check('mail qualifies and nothing else does', [
  ext.qualifies('mail'), ext.qualifies('electronic'), ext.qualifies('electronic_service'),
  ext.qualifies('email'), ext.qualifies('left_with_clerk'), ext.qualifies('other_consented_means'),
  ext.qualifies(undefined),
], [true, false, false, false, false, false, false]);
// A DIRECT DISAGREEMENT, not just a shorter list. If a future edit widened
// Maine's allowlist to frcp_6d's, this arm is what notices.
const frcp = engine.SERVICE_EXTENSION_STANDARDS.frcp_6d;
check('Maine and FRCP 6(d) genuinely DISAGREE on leaving it with the clerk and on other consented means',
  ['left_with_clerk', 'other_consented_means'].map(m => [frcp.qualifies(m), ext.qualifies(m)]),
  [[true, false], [true, false]]);
check('and they disagree on sequencing too', [frcp.sequence, ext.sequence],
  ['roll_then_add_then_roll', 'add_to_period_then_roll']);

// ── 3. EVERY ROW, PLAIN ─────────────────────────────────────────────────────
// Trigger Monday 2026-06-15 for all of them, so a number that moved shows up as
// a date rather than as a passing suite.
check('the trigger used throughout is a Monday', weekday('2026-06-15'), 'Monday');
check('20-day answer: +20 lands Sunday 2026-07-05 and rolls',
  dateOf(compute(ANSWER, '2026-06-15')), '2026-07-06');
check('and the landing day really was a Sunday', weekday('2026-07-05'), 'Sunday');
check('50-day foreign-service answer', dateOf(compute(FOREIGN, '2026-06-15')), '2026-08-04');
check('20-day cross-claim answer', dateOf(compute(CROSS, '2026-06-15')), '2026-07-06');
check('20-day reply to a counterclaim', dateOf(compute(REPLY, '2026-06-15')), '2026-07-06');
check('20-day reply after a court order', dateOf(compute(REPLY_ORDER, '2026-06-15')), '2026-07-06');
check('10-day responsive pleading after a motion is denied', dateOf(compute(AFTER_MOTION, '2026-06-15')), '2026-06-25');
check('10-day responsive pleading after a more definite statement', dateOf(compute(AFTER_MDS, '2026-06-15')), '2026-06-25');
check('30-day interrogatory answers', dateOf(compute(ROGS, '2026-06-15')), '2026-07-15');
check('30-day production response', dateOf(compute(PROD, '2026-06-15')), '2026-07-15');
check('14-day motion for a new trial', dateOf(compute(NEWTRIAL, '2026-06-15')), '2026-06-29');
check('14-day motion to alter or amend', dateOf(compute(ALTER, '2026-06-15')), '2026-06-29');
check('24-day opposing affidavits', dateOf(compute(OPPAFF, '2026-06-15')), '2026-07-09');

// TWENTY, NOT TWENTY-ONE -- asserted against the arithmetic rather than against
// the JSON, so a row edited to 21 fails here and not only in a field comparison.
check('the answer period is 20 days and not the federal 21: +20 from a Wednesday lands where 20 days land',
  [dateOf(compute(ANSWER, '2026-06-03')), weekday('2026-06-03')], ['2026-06-23', 'Wednesday']);

// ── 4. THE UNDER-7-DAY EXCLUSION, THE ONLY ROW THAT TAKES IT ────────────────
// Monday 2026-06-15 + 5 counted days: Tue 16, Wed 17, Thu 18, [Fri 19 is
// Juneteenth -- SKIPPED, and so is the weekend behind it], Mon 22, Tue 23.
check('the 5-day objection SKIPS Juneteenth and the weekend rather than merely rolling off them',
  dateOf(compute(DEPOBJ, '2026-06-15')), '2026-06-23');
check('Juneteenth 2026 really is the Friday being skipped', weekday('2026-06-19'), 'Friday');
// Straight calendar counting would have landed on Saturday 2026-06-20 and rolled
// to Monday 2026-06-22. The exclusion is worth a day here, so an arm that lost it
// would change this date.
check('straight counting would have given the Monday -- the exclusion is doing work, not decorating',
  engine.addDays('2026-06-15', 5), '2026-06-20');
const depSteps = compute(DEPOBJ, '2026-06-15').steps;
check('the audit trail says the exclusion fired and names the threshold',
  [depSteps.length, depSteps[0].step, /less than 7 days/.test(depSteps[0].detail)],
  [1, 'base_period', true]);
check('the exclusion step cites the rule without a subdivision, which is how this engine cites every short-period standard',
  depSteps[0].authority, 'M.R. Civ. P. 6');
// AND THE ROW CARRIES NO EXTENSION, deliberately. Two readings of 6(a)+6(c)
// together disagree by three days on a five-day period and the engine's one is
// the LATER; see the row's own note. A mailed objection is NOT computed here.
check('the 5-day row declares NO service_extension',
  seed.rules.find(r => r.rule_id === DEPOBJ).service_extension, undefined);
check('so mail cannot move the 5-day date, and that is the point', [
  dateOf(compute(DEPOBJ, '2026-06-15')),
  dateOf(compute(DEPOBJ, '2026-06-15', { service_method: 'mail' })),
], ['2026-06-23', '2026-06-23']);
check('nothing else in the seed is short enough to reach the exclusion',
  seed.rules.filter(r => r.count && r.count.value < 7).map(r => r.rule_id), [DEPOBJ]);

// ── 5. THE SEQUENCING, ON A CASE WHERE THE TWO ORDERS DIFFER ────────────────
// Trigger Monday 2026-06-01, 20 days -> unrolled Sunday 2026-06-21.
//   add_to_period_then_roll (Maine):  06-21 + 3 = Wednesday 06-24, no roll.
//   roll_then_add_then_roll (FRCP):   roll to Mon 06-22, + 3 = Thursday 06-25.
// One day apart, and the FRCP order is the later. This is the arm that fails if
// Maine's sequence is ever changed to the family default.
check('the unrolled 20-day landing is a Sunday', weekday('2026-06-21'), 'Sunday');
check('mailed cross-claim answer takes Maine sequencing',
  dateOf(compute(CROSS, '2026-06-01', { service_method: 'mail' })), '2026-06-24');
check('unmailed, the same row rolls to the Monday',
  dateOf(compute(CROSS, '2026-06-01')), '2026-06-22');
check('the FRCP order would have produced the Thursday, which is LATER -- stated as arithmetic so the difference is visible',
  engine.addDays('2026-06-22', 3), '2026-06-25');
check('electronic service adds nothing', dateOf(compute(CROSS, '2026-06-01', { service_method: 'electronic' })), '2026-06-22');
check('leaving it with the clerk adds nothing either, where FRCP 6(d) would add three',
  dateOf(compute(CROSS, '2026-06-01', { service_method: 'left_with_clerk' })), '2026-06-22');
const mailed = compute(CROSS, '2026-06-01', { service_method: 'mail' });
check('the result reports the extension and names Maine\'s own standard',
  [mailed.service_extension_applied, mailed.service_extension.standard, mailed.service_extension.days_added],
  [true, 'me_mr_civ_p_6_c', 3]);

// THE ANSWER ROW GETS NO EXTENSION even when mailed, which is the safe side of
// the Rule 4 question. If a future edit attaches one, this arm moves.
check('the Rule 4 answer rows carry no extension at all', [
  seed.rules.find(r => r.rule_id === ANSWER).service_extension,
  seed.rules.find(r => r.rule_id === FOREIGN).service_extension,
], [undefined, undefined]);
check('so a mailed summons does not move the answer date',
  dateOf(compute(ANSWER, '2026-06-15', { service_method: 'mail' })), '2026-07-06');
// And the 10-day pair splits on the extension, in adjacent clauses of one
// sentence -- 12(a)(1) runs from NOTICE, 12(a)(2) from SERVICE.
check('the two 10-day rows disagree on the extension because their triggers differ', [
  dateOf(compute(AFTER_MOTION, '2026-06-15', { service_method: 'mail' })),
  dateOf(compute(AFTER_MDS, '2026-06-15', { service_method: 'mail' })),
], ['2026-06-25', '2026-06-29']);

// ── 6. RULE 36 IS A FLOOR; RULES 33 AND 34 ARE NOT ─────────────────────────
const admit = seed.rules.find(r => r.rule_id === ADMIT);
// READ DEFENSIVELY, AND THAT IS NOT DEFENSIVE STYLE -- IT IS SO A SABOTAGE FAILS
// CLEANLY. Flattening this row to a plain 30-day count made the suite throw a
// TypeError here, which is a failure and therefore "caught", but the throw
// ABORTS the run so every later arm goes unreported and the summary line reads
// like a partial pass. Same treatment below for the coverage entry and the
// trigger-document guard, both of which threw on their own mutations.
const admitTrigger = (admit && admit.trigger_event) || {};
check('the admission row is a later_of over two limbs',
  [admitTrigger.resolve_periods, (admitTrigger.limbs || []).length], ['later_of', 2]);
check('33 and 34 are plain single-trigger rows -- the defendant limb is an ELECTION and is not modelled',
  [typeof seed.rules.find(r => r.rule_id === ROGS).trigger_event,
   typeof seed.rules.find(r => r.rule_id === PROD).trigger_event], ['string', 'string']);
const adm = (req, sum, extra) => dateOf(compute(ADMIT, req, Object.assign({
  trigger_dates: {
    service_of_request_for_admission: req,
    me_service_of_summons_and_complaint_for_admission: sum,
  },
}, extra || {})));
// REQUEST LIMB WINS: 2026-06-15 + 30 = Wednesday 2026-07-15, against
// 2026-05-01 + 45 = 2026-06-15.
check('the 30-day request limb governs when the summons is old', adm('2026-06-15', '2026-05-01'), '2026-07-15');
// FLOOR WINS: 2026-06-10 + 45 = Saturday 2026-07-25, rolling to Monday 07-27,
// against 2026-06-15 + 30 = 2026-07-15.
check('the 45-day floor governs when the summons is recent, and rolls off the Saturday',
  adm('2026-06-15', '2026-06-10'), '2026-07-27');
check('and the floor limb really did land on a Saturday before rolling', weekday('2026-07-25'), 'Saturday');
// THE EXTENSION IS SCOPED TO THE REQUEST LIMB. Adding three days when the
// summons floor governs would report LATE.
check('mail extends the REQUEST limb', adm('2026-06-15', '2026-05-01', { service_method: 'mail' }), '2026-07-20');
check('mail does NOT extend the SUMMONS floor', adm('2026-06-15', '2026-06-10', { service_method: 'mail' }), '2026-07-27');
check('and the scoping is declared rather than emergent',
  admit.service_extension.applies_to_limbs, ['service_of_request_for_admission']);

// ── 7. THE CALENDAR IS THE STATUTE ─────────────────────────────────────────
// POSITIVES: statutory days must roll.
check("Patriot's Day Monday 2026-04-20 rolls -- the day that exists on no other calendar here",
  [dateOf(compute(NEWTRIAL, '2026-04-06')), weekday('2026-04-20')], ['2026-04-21', 'Monday']);
check('Juneteenth Friday 2026-06-19 rolls past the weekend', dateOf(compute(NEWTRIAL, '2026-06-05')), '2026-06-22');
check("Washington's Birthday Monday 2026-02-16 rolls", dateOf(compute(NEWTRIAL, '2026-02-02')), '2026-02-17');
check('Indigenous Peoples Day Monday 2026-10-12 rolls', dateOf(compute(NEWTRIAL, '2026-09-28')), '2026-10-13');
check("the Sunday-to-Monday limb is live in 2027: the 4th of July falls on a Sunday and Monday 2027-07-05 rolls",
  [dateOf(compute(NEWTRIAL, '2027-06-21')), weekday('2027-07-04')], ['2027-07-06', 'Sunday']);

// NEGATIVES: the five published-but-not-statutory Fridays must NOT roll. These
// are the arms that would fail if somebody "completed" the calendar from the
// Judicial Branch's schedule, which is the LATE direction.
const notAHoliday = [
  ['Thanksgiving Friday 2026-11-27', '2026-11-13', '2026-11-27'],
  ['Independence observed Friday 2026-07-03', '2026-06-19', '2026-07-03'],
  ['Juneteenth observed Friday 2027-06-18', '2027-06-04', '2027-06-18'],
  ['Thanksgiving Friday 2027-11-26', '2027-11-12', '2027-11-26'],
  ['Christmas observed Friday 2027-12-24', '2027-12-10', '2027-12-24'],
];
for (const [what, trigger, expected] of notAHoliday) {
  check('NOT a Maine legal holiday, so no roll: ' + what,
    [dateOf(compute(NEWTRIAL, trigger)), weekday(expected)], [expected, 'Friday']);
}
// And they are absent from the data as well as from the arithmetic, so the two
// cannot drift apart.
const allDates = [].concat(...cal.holiday_calendars.map(r => r.dates.map(d => d.date)));
check('none of the five is in the calendar file',
  notAHoliday.map(([, , d]) => allDates.includes(d)), [false, false, false, false, false]);
check('the statutory count is 11 for 2026 and 10 for 2027 -- a day added or lost moves a number here',
  cal.holiday_calendars.map(r => [r.year, r.dates.length]), [[2026, 11], [2027, 10]]);
check('no Saturday or Sunday is enumerated -- Rule 6(a) excludes both by name, so a per-date entry would be redundant',
  allDates.filter(d => [0, 6].includes(new Date(d + 'T00:00:00Z').getUTCDay())), []);
check('every calendar entry carries a derivation naming its statutory phrase',
  [].concat(...cal.holiday_calendars.map(r => r.dates)).filter(d => !/1051|5 U\.S\.C/.test(d.derivation)).map(d => d.date), []);
check('2028 is REFUSED rather than derived', dateOf(compute(NEWTRIAL, '2028-01-03')), 'REFUSED:NOT_PROVISIONED');

// ── 8. SCOPE AND ABSENCES, ASSERTED AS ABSENCES ────────────────────────────
check('every row uses the Maine standard and nothing else',
  [...new Set(seed.rules.map(r => r.computation))], ['me_mr_civ_p_6']);
check('every row is jurisdiction me, domain civil-litigation',
  [...new Set(seed.rules.map(r => r.jurisdiction + '/' + r.domain))], ['me/civil-litigation']);
check('NO ROW COUNTS BACKWARD -- the under-inclusive calendar is safe forward and unsafe backward',
  seed.rules.filter(r => r.count && r.count.direction !== 'forward').map(r => r.rule_id), []);
check('and no LIMB counts backward either',
  seed.rules.filter(r => r.trigger_event && r.trigger_event.limbs
    && r.trigger_event.limbs.some(l => l.count && l.count.direction === 'backward')).map(r => r.rule_id), []);
check('no row uses months or years -- Rule 6 does not address either',
  [...new Set(seed.rules.filter(r => r.count).map(r => r.count.unit))], ['calendar_days']);
check('every row carries an effective_from, and it is one of the two dates the documents state',
  [...new Set(seed.rules.map(r => r.effective_from))].sort(), ['2014-11-01', '2023-11-15']);
// THE TWO BOUNDS ARE DIFFERENT AND THE REFUSAL CODE SAYS WHICH ONE FIRED.
// Before the amendment the EFFECTIVE WINDOW refuses; on the day it took effect
// that gate stops firing and the CALENDAR refuses instead, because the calendar
// only carries 2026 and 2027. Asserting the code rather than just ok:false is
// what makes this an assertion about the effective_from at all -- a single
// "it refuses" arm would have passed for the wrong reason, and did on the way in.
check('a matter triggered before the 2023 e-service amendment is refused by the EFFECTIVE WINDOW',
  dateOf(compute(ANSWER, '2023-11-01')), 'REFUSED:NO_RULE_IN_FORCE');
check('on the day the amendment took effect that gate stops firing and the CALENDAR bound is what remains',
  dateOf(compute(ANSWER, '2023-11-15')), 'REFUSED:NOT_PROVISIONED');
check('so the calendar is currently the TIGHTER bound of the two, and no real Maine computation is reached by effective_from alone',
  [compute(ANSWER, '2026-06-15').ok, compute(NEWTRIAL, '2026-06-15').ok], [true, true]);
check('the Rule 59 rows reach back to 2014-11-01, which their own document states',
  [NEWTRIAL, ALTER, OPPAFF].map(id => seed.rules.find(r => r.rule_id === id).effective_from),
  ['2014-11-01', '2014-11-01', '2014-11-01']);
check('every rule_id is unique', seed.rules.length, new Set(seed.rules.map(r => r.rule_id)).size);
check('every trigger is unique, because the engine matches one rule per (jurisdiction, domain, trigger)',
  seed.rules.length,
  new Set(seed.rules.map(r => typeof r.trigger_event === 'string' ? r.trigger_event : r.trigger_event.id)).size);
check('every row quotes its rule and names where it was read',
  seed.rules.filter(r => !r.authority || !r.authority.quote || !r.authority.url
    || !r.authority.consolidated_url || r.authority.retrieved_at !== '2026-09-21').map(r => r.rule_id), []);

// ── 9. THE DISCLOSURE RIDES ON THE ANSWER ──────────────────────────────────
const cov = engine.JURISDICTION_COVERAGE.me || {};
const covSummary = cov.summary || '';
const covDetail = cov.detail || '';
check('Maine declares a coverage entry', !!engine.JURISDICTION_COVERAGE.me, true);
check('direction is early and it says EARLIER where a caller will read it',
  [cov.direction, cov.complete, /EARLIER/.test(covSummary)], ['early', false, true]);
check('it carries no late_exposure block, because nothing here fails late', cov.late_exposure, undefined);
check('the summary names the calendar choice rather than only gesturing at a gap',
  [/1051/.test(covSummary), /statutory/i.test(covSummary)], [true, true]);
check('the detail names the dangling Rule 6(a)/77(c) cross-reference and the officer the rule gets wrong',
  [/77\(c\)/.test(covDetail), /SUPREME JUDICIAL COURT/.test(covDetail)], [true, true]);
check('the detail names all five divergent Fridays by date',
  ['3 July 2026', '27 November 2026', '18 June 2027', '26 November 2027', '24 December 2027']
    .map(d => covDetail.includes(d)), [true, true, true, true, true]);
check('and it names the 2023 trigger change, which is the one thing a stale source would hide',
  /NOTICE REGARDING ELECTRONIC SERVICE/.test(covDetail), true);
check('the disclosure is attached to a real computed answer, not only to the table',
  (compute(NEWTRIAL, '2026-06-05').coverage || {}).direction, 'early');
check('the whole coverage table is still structurally valid with Maine in it',
  engine.coverageTableDefects(engine.JURISDICTION_COVERAGE), []);

// ── 10. THE UI WOULD SHOW A NAME, NOT A CODE ───────────────────────────────
const endpointSrc = fs.readFileSync(path.join(__dirname, '..', 'legal-deadlines.js'), 'utf8');
check("api/legal-deadlines.js labels me as Maine, in the same commit as the seed",
  /(^|[,{\s])me:\s*'Maine'/m.test(endpointSrc), true);

// ── 11. THE TRIGGER GUARDS ─────────────────────────────────────────────────
const ansTd = compute(ANSWER, '2026-06-15').trigger_document || {};
check('the answer row guards its three-document trigger and warns rather than refusing',
  [ansTd.state, ansTd.expected],
  ['unconfirmed', 'service_of_summons_complaint_and_electronic_service_notice']);
check('and it names what the date must NOT be, including the pre-2023 trigger',
  /summons and complaint/.test(ansTd.not_the || ''), true);
check('confirming the trigger document clears the warning',
  (compute(ANSWER, '2026-06-15', { trigger_document: 'service_of_summons_complaint_and_electronic_service_notice' })
    .trigger_document || {}).state, 'confirmed');
check('the three Rule 59 rows each guard entry of judgment',
  [NEWTRIAL, ALTER, OPPAFF].map(id => !!seed.rules.find(r => r.rule_id === id).trigger_document),
  [true, true, true]);
check('and each declares a distinct trigger_document id, matching its own trigger',
  [NEWTRIAL, ALTER, OPPAFF].map(id => {
    const r = seed.rules.find(x => x.rule_id === id);
    return r.trigger_document.id === r.trigger_event;
  }), [true, true, true]);
check('no trigger_document in this seed is malformed',
  seed.rules.filter(r => r.trigger_document
    && engine.triggerDocumentDefects(r.trigger_document).length).map(r => r.rule_id), []);

console.log('\ndeadline-maine: ' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
