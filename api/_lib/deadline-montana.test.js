// Montana District Court deadline rows -- isolated verification against the
// REAL engine and the REAL seed/calendar JSON on disk, not a scratch copy.
//
// Seven things would be wrong if carried from a neighbour or from the family:
//
//   - THE COURT IS PART OF THE JURISDICTION, AND THE COLLISION IS INSIDE ONE
//     TITLE OF ONE CODE. Mont. Just. & City Ct. R. Civ. P. 6 (MCA Title 25
//     ch. 23) is also called Rule 6 and is a DIFFERENT computation: no
//     definition of "legal holiday" at all, no clerk-inaccessibility limb, no
//     backward "next day" rule, and a MAIL-ONLY extension that LENGTHENS the
//     period where the District Court rule adds after it expires. Not seeded.
//   - NO SHORT-PERIOD EXCLUSION AT ALL. Rule 6(a)(1)(B) counts "every day,
//     including intermediate Saturdays, Sundays, and legal holidays". Five of
//     the fifteen rows are shorter than 15 days; a 7 from NJ/NC/WA/MA/MO/SC or
//     an 11 from Delaware would lengthen all five and report them LATE.
//     Asserted as an ABSENT property and probed on a real 14-day count.
//   - RULE 6(d) IS THE PRE-2016 FEDERAL SET AND STILL EXTENDS FOR CONSENTED
//     ELECTRONIC SERVICE. frcp_6d does not. Asserted as a direct disagreement
//     between the two standards on the same method.
//   - RULES 33 AND 34 CARRY AN ELECTION AND RULE 36 CARRIES A FLOOR -- the
//     OPPOSITE split from Delaware, where 33 and 34 carry an election and 36
//     carries nothing. Asserted as shapes, and both Rule 36 limbs are probed
//     with each winning in turn.
//   - TWO ROWS COUNT BACKWARD, because Rule 6(a)(5) addresses the direction
//     expressly where Delaware's Rule 6(a) does not. Probed on a backward
//     landing that must roll off Presidents' Day AND the weekend behind it.
//   - THE SATURDAY OBSERVANCE SHIFT AND THE STATE GENERAL ELECTION DAY ARE
//     BOTH CARRIED. Probed as positives: 3 July 2026 and 3 November 2026.
//   - THE DAY AFTER THANKSGIVING IS NOT. Montana's statute does not name it
//     where Delaware's does. Probed as a negative in both available ways.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_montana.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_montana.json'), 'utf8'));

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
    jurisdiction: 'mt', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : 'REFUSED:' + r.code);

const ANSWER = 'mt-mrcp-12a1A-answer-after-service-21-days';
const CROSS = 'mt-mrcp-12a1B-answer-counterclaim-crossclaim-21-days';
const REPLY = 'mt-mrcp-12a1C-reply-to-answer-21-days';
const STATE_OFFICIAL = 'mt-mrcp-12a2-state-official-capacity-answer-42-days';
const STATE_INDIV = 'mt-mrcp-12a3-state-officer-individual-capacity-42-days';
const AFTER_MOTION = 'mt-mrcp-12a4A-responsive-pleading-after-motion-resolved-14-days';
const AFTER_MDS = 'mt-mrcp-12a4B-responsive-pleading-after-more-definite-statement-14-days';
const ROGS = 'mt-mrcp-33b2-interrogatory-answers-30-days';
const PROD = 'mt-mrcp-34b2A-production-response-30-days';
const ADMIT = 'mt-mrcp-36a3-admissions-later-of';
const NEWTRIAL = 'mt-mrcp-59b-new-trial-28-days';
const ALTER = 'mt-mrcp-59e-alter-or-amend-judgment-28-days';
const OPPAFF59 = 'mt-mrcp-59c-opposing-affidavits-14-days';
const NOTICE = 'mt-mrcp-6c1-motion-and-notice-of-hearing-14-days-before';
const OPPAFF6 = 'mt-mrcp-6c2-opposing-affidavit-7-days-before';

const EXT_METHODS = ['mail', 'left_with_clerk', 'electronic', 'email', 'other_consented_means'];

// ── The seed's own shape ──────────────────────────────────────────────────
check('15 rules seeded', seed.rules.length, 15);
check('every row is Montana civil litigation',
  [...new Set(seed.rules.map(r => r.jurisdiction + '/' + r.domain))], ['mt/civil-litigation']);
check('every row uses the District Court standard, and the court is in its name',
  [...new Set(seed.rules.map(r => r.computation))], ['mt_rcp_6a']);
check('every trigger is unique -- no two rows can match one event',
  seed.rules.length, new Set(seed.rules.map(r => JSON.stringify(r.trigger_event))).size);
check('every row carries a citation, a quote and a retrieval date',
  seed.rules.filter(r => !r.authority || !r.authority.citation || !r.authority.quote || !r.authority.retrieved_at)
    .map(r => r.rule_id), []);
check('the readme names the Justice and City Court rule it is NOT',
  /Justice and City Court/.test(seed._readme), true);

// EXACTLY ONE OF EACH MULTI-TRIGGER SHAPE, and they are different arithmetic.
check('exactly one resolve_periods row -- Rule 36, the only real floor',
  seed.rules.filter(r => typeof r.trigger_event === 'object' && r.trigger_event.resolve_periods).map(r => r.rule_id),
  [ADMIT]);
check('exactly one resolve row -- Rule 12(a)(3), one count and two start dates',
  seed.rules.filter(r => typeof r.trigger_event === 'object' && r.trigger_event.resolve).map(r => r.rule_id),
  [STATE_INDIV]);
check('exactly two backward rows, both from Rule 6(c)',
  seed.rules.filter(r => (r.count || {}).direction === 'backward').map(r => r.rule_id),
  [NOTICE, OPPAFF6]);
check('exactly two rows declare a trigger_document, both under Rule 59',
  seed.rules.filter(r => r.trigger_document).map(r => r.rule_id), [NEWTRIAL, ALTER]);

// ── The standard, and the absence that carries the seed ──────────────────
const std = engine.COMPUTATION_STANDARDS.mt_rcp_6a;
check('the standard exists and names the court', std.label, 'Mont. R. Civ. P. 6(a)');
check('NO short-period exclusion -- Rule 6(a)(1)(B) counts every day',
  std.short_period_exclusion_days, undefined);
check('and Delaware still has its eleven, so this is an absence rather than a global change',
  engine.COMPUTATION_STANDARDS.de_super_ct_civ_r_6a.short_period_exclusion_days, 11);
check('NO weekend_days declaration -- Rule 6(a)(1)(C) names both weekend days itself',
  std.weekend_days, undefined);
check('federal subdivision numbering, including the backward rule at (a)(5)',
  [std.base_period_suffix, std.months_years_suffix, std.rollover_suffix_forward, std.rollover_suffix_backward],
  ['(1)(A)-(B)', '(1)(C)', '(1)(C)', '(5)']);

// ── The dates. Hand-computed from the rule first, then asserted ──────────
// 1 June 2026 is a Monday.
// +21 = Monday 22 June, no roll.
check('21-day answer from 1 June', dateOf(compute(ANSWER, '2026-06-01')), '2026-06-22');
check('the counterclaim and reply rows carry the same 21 days from their own triggers',
  [dateOf(compute(CROSS, '2026-06-01')), dateOf(compute(REPLY, '2026-06-01'))],
  ['2026-06-22', '2026-06-22']);
// +42 = Monday 13 July, no roll. FORTY-TWO, not the federal sixty.
check('42-day State answer from 1 June', dateOf(compute(STATE_OFFICIAL, '2026-06-01')), '2026-07-13');
// +30 = Wednesday 1 July, no roll.
check('30-day interrogatory answer from 1 June', dateOf(compute(ROGS, '2026-06-01')), '2026-07-01');
check('production carries the same 30 days', dateOf(compute(PROD, '2026-06-01')), '2026-07-01');
// +28 = Monday 29 June, no roll.
check('28-day new-trial and alter-or-amend motions from 1 June',
  [dateOf(compute(NEWTRIAL, '2026-06-01')), dateOf(compute(ALTER, '2026-06-01'))],
  ['2026-06-29', '2026-06-29']);

// NO EXCLUSION, WHICH IS THE WHOLE REASON THE MISSING THRESHOLD MATTERS.
// 1 June + 14 counting EVERY day = Monday 15 June. Excluding intermediate
// weekends -- what a threshold of 15 or more would do -- gives Friday 19 June:
// Jun 2-5 = 4, Jun 8-12 = 9, Jun 15-19 = 14. Four days apart, in the LATE
// direction, which is the direction that loses a filing.
check('a 14-day period counts straight through weekends, landing on 15 June',
  dateOf(compute(AFTER_MDS, '2026-06-01')), '2026-06-15');
check('and the Rule 12(a)(4)(A) row, whose trigger differs, computes identically',
  dateOf(compute(AFTER_MOTION, '2026-06-01')), '2026-06-15');
check('the Rule 59(c) opposing-affidavit row is the third 14-day count',
  dateOf(compute(OPPAFF59, '2026-06-01')), '2026-06-15');

// ── Backward periods, which Rule 6(a)(5) addresses expressly ─────────────
// Hearing Monday 1 June 2026. -14 = Monday 18 May, no roll.
check('14 days back from a 1 June hearing', dateOf(compute(NOTICE, '2026-06-01')), '2026-05-18');
// -7 = Monday 25 May, which is MEMORIAL DAY. Rolling BACKWARD under Rule
// 6(a)(5) walks past Sunday the 24th and Saturday the 23rd to Friday 22 May.
// Rolling forward would land on Tuesday the 26th and leave the opposing party
// fewer than the seven days the rule guarantees.
check('7 days back from a 1 June hearing rolls BACKWARD off Memorial Day and the weekend',
  dateOf(compute(OPPAFF6, '2026-06-01')), '2026-05-22');
// Hearing Friday 17 July 2026. -14 = Friday 3 July, the observed Independence
// Day, so it rolls back to Thursday 2 July.
check('a backward landing on the observed 3 July rolls back to the 2nd',
  dateOf(compute(NOTICE, '2026-07-17')), '2026-07-02');
// Hearing Monday 23 February 2026. -7 = Monday 16 February, Presidents' Day,
// rolling back through the weekend to Friday 13 February. This is the date the
// naming question in Rule 6(a)(6)(A) turns on, and carrying it backward is the
// SAFE direction: not rolling would report a LATER date than the rule allows.
check('a backward landing on Presidents\' Day rolls back to Friday 13 February',
  dateOf(compute(OPPAFF6, '2026-02-23')), '2026-02-13');

// ── The two multi-trigger rows, which are different arithmetic ───────────
// Rule 12(a)(3): ONE count of 42, from the LATER of two dates.
check('the individual-capacity row counts 42 from the later date, whichever order it arrives in',
  [dateOf(compute(STATE_INDIV, '2026-06-01', { trigger_dates: {
      service_on_montana_state_officer_or_employee: '2026-06-01',
      service_on_montana_attorney_general_individual_capacity: '2026-06-10' } })),
   dateOf(compute(STATE_INDIV, '2026-06-01', { trigger_dates: {
      service_on_montana_state_officer_or_employee: '2026-06-10',
      service_on_montana_attorney_general_individual_capacity: '2026-06-01' } }))],
  ['2026-07-22', '2026-07-22']);
check('and it REFUSES on one date rather than resolving from whichever arrived',
  dateOf(compute(STATE_INDIV, '2026-06-01', { trigger_dates: {
      service_on_montana_state_officer_or_employee: '2026-06-01' } })),
  'REFUSED:INCOMPLETE_TRIGGERS');

// Rule 36: TWO counts, and the later RESULT governs. Each limb wins in turn.
// Request served 1 June, summons served 1 April: 30 days -> 1 July beats
// 45 days from 1 April -> 16 May.
check('Rule 36 takes the 30-day limb when the summons is old',
  dateOf(compute(ADMIT, '2026-06-01', { trigger_dates: {
      service_of_request_for_admission: '2026-06-01',
      service_of_summons_and_complaint_for_admission: '2026-04-01' } })),
  '2026-07-01');
// Both served 1 June: 45 days -> Thursday 16 July beats 30 days -> 1 July.
// THIS IS THE FLOOR DOING ITS WORK, and it is the case Delaware's Rule 36 does
// not have at all -- seeding a flat thirty here would report 1 July and tell a
// defendant a matter is still open fifteen days after it was admitted.
check('and the 45-day defendant FLOOR when the requests arrive with the complaint',
  dateOf(compute(ADMIT, '2026-06-01', { trigger_dates: {
      service_of_request_for_admission: '2026-06-01',
      service_of_summons_and_complaint_for_admission: '2026-06-01' } })),
  '2026-07-16');
check('Rules 33 and 34 are NOT floors -- their 45-day limb is an election and is a plain field',
  [typeof seed.rules.find(r => r.rule_id === ROGS).trigger_event,
   typeof seed.rules.find(r => r.rule_id === PROD).trigger_event],
  ['string', 'string']);

// ── The Rule 6(d) extension ──────────────────────────────────────────────
// "3 days are added AFTER the period would otherwise expire under Rule 6(a)":
// 30 days -> Wednesday 1 July (a good day, no interim roll), +3 -> Saturday
// 4 July, which rolls through Sunday to Monday 6 July.
check('mail adds three days after the period expires, and the result then rolls',
  dateOf(compute(ROGS, '2026-06-01', { service_method: 'mail' })), '2026-07-06');
check('all five Rule 5(b)(2) methods extend, and nothing else does',
  EXT_METHODS.concat(['hand_delivery', 'facsimile'])
    .map(m => dateOf(compute(ROGS, '2026-06-01', { service_method: m }))),
  ['2026-07-06', '2026-07-06', '2026-07-06', '2026-07-06', '2026-07-06', '2026-07-01', '2026-07-01']);

// THE 2016 FEDERAL DIVERGENCE, ASSERTED AS A DISAGREEMENT RATHER THAN A CLAIM.
// FRCP 6(d) dropped Rule 5(b)(2)(E) -- electronic service -- in 2016. Montana's
// rule still names it, so reusing frcp_6d here would silently drop three days
// from every consented electronic service.
check('mt_rcp_6d extends for consented electronic service and frcp_6d does not',
  [engine.SERVICE_EXTENSION_STANDARDS.mt_rcp_6d.qualifies('email'),
   engine.SERVICE_EXTENSION_STANDARDS.mt_rcp_6d.qualifies('electronic'),
   engine.SERVICE_EXTENSION_STANDARDS.frcp_6d.qualifies('email'),
   engine.SERVICE_EXTENSION_STANDARDS.frcp_6d.qualifies('electronic')],
  [true, true, false, false]);
check('and the sequence is the federal after-expiry order, not the Justice Court\'s period-lengthening one',
  engine.SERVICE_EXTENSION_STANDARDS.mt_rcp_6d.sequence, 'roll_then_add_then_roll');

check('exactly six of the fifteen rows carry a service extension',
  seed.rules.filter(r => r.service_extension).length, 6);
check('and every one of them is the Rule 6(d) standard with the same five methods',
  [[...new Set(seed.rules.filter(r => r.service_extension).map(r => r.service_extension.standard))],
   [...new Set(seed.rules.filter(r => r.service_extension).map(r => r.service_extension.applies_when.join(',')))]],
  [['mt_rcp_6d'], [EXT_METHODS.join(',')]]);

// THE ROWS THAT DELIBERATELY CARRY NO EXTENSION, each for its own reason.
check('no extension on the answer-to-process row -- Rule 6(d) names Rule 5(b)(2) and process goes out under Rule 4',
  dateOf(compute(ANSWER, '2026-06-01', { service_method: 'mail' })), '2026-06-22');
check('nor on the State rows, for the same reason',
  dateOf(compute(STATE_OFFICIAL, '2026-06-01', { service_method: 'mail' })), '2026-07-13');
check('nor on the new-trial row, whose period runs from entry of judgment',
  dateOf(compute(NEWTRIAL, '2026-06-01', { service_method: 'mail' })), '2026-06-29');
check('nor on the Rule 12(a)(4)(A) row, whose period runs from notice of the court\'s action',
  dateOf(compute(AFTER_MOTION, '2026-06-01', { service_method: 'mail' })), '2026-06-15');
check('nor on either backward row -- there is no period after service to extend',
  [dateOf(compute(NOTICE, '2026-06-01', { service_method: 'mail' })),
   dateOf(compute(OPPAFF6, '2026-06-01', { service_method: 'mail' }))],
  ['2026-05-18', '2026-05-22']);
check('nor on Rule 36, whose 45-day limb runs from Rule 4 service and would be extended wrongly',
  dateOf(compute(ADMIT, '2026-06-01', { service_method: 'mail', trigger_dates: {
      service_of_request_for_admission: '2026-06-01',
      service_of_summons_and_complaint_for_admission: '2026-06-01' } })),
  '2026-07-16');

// EXCLUSIVITY: Utah and Florida both carry requires_exclusive. Montana's rule
// says "service is made under Rule 5(b)(2)(C), (D), or (E), or (F)" with no
// "only" or "exclusively", so supplying the full set must change nothing.
check('no row declares requires_exclusive',
  seed.rules.filter(r => (r.service_extension || {}).requires_exclusive).map(r => r.rule_id), []);
check('supplying service_methods -- exclusive or combined -- does not change a Montana date',
  [dateOf(compute(ROGS, '2026-06-01', { service_method: 'mail', service_methods: ['mail'] })),
   dateOf(compute(ROGS, '2026-06-01', { service_method: 'mail', service_methods: ['mail', 'email'] })),
   dateOf(compute(ROGS, '2026-06-01', { service_method: 'email', service_methods: ['email', 'hand_delivery'] }))],
  ['2026-07-06', '2026-07-06', '2026-07-06']);

// ── The calendar ─────────────────────────────────────────────────────────
const dates2026 = cal.holiday_calendars.find(c => c.year === 2026).dates.map(d => d.date);
check('eleven dates for 2026', dates2026.length, 11);
check('only 2026 is provisioned', cal.holiday_calendars.map(c => c.year), [2026]);
check('Sundays are NOT enumerated, although sec. 1-1-216(1)(a) makes each one a holiday',
  dates2026.filter(d => engine.dayOfWeek(d) === 0), []);
check('every entry applies in BOTH directions -- no forward-only kind is used',
  [...new Set(cal.holiday_calendars[0].dates.map(d => d.kind))], ['declared']);

// THE SATURDAY SHIFT IS CARRIED. 4 July 2026 is a Saturday and
// sec. 1-1-216(2)(b) makes the preceding Friday a holiday; Rule 6(a)(6)(A)
// reaches "the day set aside by statute for OBSERVING" the holiday, so the
// shifted day is inside the reference.
check('Friday 3 July 2026 is carried as the observed Independence Day', dates2026.includes('2026-07-03'), true);
check('and 4 July itself is not separately enumerated', dates2026.includes('2026-07-04'), false);
// 30 days from 3 June lands on Friday 3 July and must roll past it and the
// weekend to Monday 6 July.
check('a forward period landing on 3 July rolls past the observed holiday and the weekend',
  dateOf(compute(ROGS, '2026-06-03')), '2026-07-06');

// THE STATE GENERAL ELECTION DAY IS CARRIED, and Montana needed no reach for
// it: the rule, the holiday statute and sec. 13-1-104 all use one term.
check('Tuesday 3 November 2026 is carried as the state general election day',
  dates2026.includes('2026-11-03'), true);
check('a period landing on 3 November rolls to the 4th', dateOf(compute(ROGS, '2026-10-04')), '2026-11-04');

// PRESIDENTS' DAY IS CARRIED despite Rule 6(a)(6)(A) still calling it
// "Lincoln's and Washington's Birthdays" -- the statute renamed it in 2025 and
// moved nothing.
check('Monday 16 February 2026 is carried as Presidents\' Day', dates2026.includes('2026-02-16'), true);
check('a forward period landing on Presidents\' Day rolls to the 17th',
  dateOf(compute(ROGS, '2026-01-17')), '2026-02-17');

// THE DAY AFTER THANKSGIVING IS NOT A MONTANA HOLIDAY -- probed as a negative
// in both directions, because Delaware's statute DOES name it and a calendar
// copied across would report LATE.
check('Friday 27 November 2026 is NOT carried', dates2026.includes('2026-11-27'), false);
check('Thanksgiving itself rolls only as far as that Friday',
  dateOf(compute(ROGS, '2026-10-27')), '2026-11-27');
check('and a period landing on that Friday does not roll at all',
  dateOf(compute(ROGS, '2026-10-28')), '2026-11-27');
check('no Juneteenth and no Good Friday -- sec. 1-1-216 names neither',
  [dates2026.includes('2026-06-19'), dates2026.includes('2026-04-03')], [false, false]);
check('Indigenous Peoples\' Day and Columbus Day is one date, the second Monday in October',
  [dates2026.includes('2026-10-12'), dateOf(compute(ROGS, '2026-09-12'))], [true, '2026-10-13']);

check('the calendar refuses a year it does not hold rather than deriving one',
  dateOf(compute(ROGS, '2027-06-01')), 'REFUSED:NOT_PROVISIONED');

// ── Effective dates come from each rule's own published History line ─────
check('a pre-adoption trigger refuses on effective_from',
  dateOf(compute(ROGS, '2011-09-01')), 'REFUSED:NO_RULE_IN_FORCE');
check('Rule 59 carries a LATER effective date than the rest, from its 2016 amendment',
  [seed.rules.find(r => r.rule_id === NEWTRIAL).effective_from,
   seed.rules.find(r => r.rule_id === ROGS).effective_from],
  ['2017-07-01', '2011-10-01']);
// THE SPLIT IS REAL AND THE TWO REFUSALS PROVE IT, WHICH IS THE ONLY WAY IT
// CAN BE PROVEN HERE: no 2017 calendar exists, so both rules refuse on a June
// 2017 trigger -- but for DIFFERENT reasons. Rule 59 never reaches the calendar
// at all because it was not yet in force; Rule 33 was in force and refuses only
// because the year is not provisioned. Asserting the two CODES is asserting the
// effective_from split rather than a symptom of it.
check('a June 2017 trigger refuses on Rule 59 for want of a rule and on Rule 33 only for want of a calendar',
  [dateOf(compute(NEWTRIAL, '2017-06-01')), dateOf(compute(ROGS, '2017-06-01'))],
  ['REFUSED:NO_RULE_IN_FORCE', 'REFUSED:NOT_PROVISIONED']);
check('no row invents an effective_to',
  seed.rules.filter(r => r.effective_to !== null).map(r => r.rule_id), []);

// ── The trigger-document guard on the two Rule 59 rows ───────────────────
check('an unconfirmed entry-of-judgment date still returns, with the assumption stated',
  [compute(NEWTRIAL, '2026-06-01').trigger_document.state, dateOf(compute(NEWTRIAL, '2026-06-01'))],
  ['unconfirmed', '2026-06-29']);
check('confirming the right document says so',
  compute(NEWTRIAL, '2026-06-01', { trigger_document: 'entry_of_judgment' }).trigger_document.state,
  'confirmed');
check('and confirming the OTHER Rule 59 row\'s document is refused rather than accepted',
  dateOf(compute(NEWTRIAL, '2026-06-01', { trigger_document: 'entry_of_judgment_for_motion_to_alter_or_amend' })),
  'REFUSED:TRIGGER_DOCUMENT_MISMATCH');

// ── Coverage, and it leads with scope ────────────────────────────────────
const cov = engine.JURISDICTION_COVERAGE.mt;
check('Montana declares a coverage entry', [!!cov, cov.complete, cov.direction], [true, false, 'early']);
check('the summary leads with DISTRICT COURT ONLY', /^DISTRICT COURT ONLY/.test(cov.summary), true);
check('and the detail names the Justice and City Court rule explicitly',
  /Just\. & City Ct\. R\. Civ\. P\. 6/.test(cov.detail), true);
check('the clerk-inaccessibility limb is disclosed', /inaccessib/i.test(cov.detail), true);
check('the forward-only limb (C) asymmetry is disclosed', /6\(a\)\(6\)\(C\)/.test(cov.detail), true);
check('and the Presidents\' Day naming question is disclosed rather than left to be rediscovered',
  /Presidents' Day/.test(cov.detail), true);
check('a real computation carries the disclosure',
  [compute(ROGS, '2026-06-01').ok, !!compute(ROGS, '2026-06-01').coverage], [true, true]);

// ── Nothing else moved ───────────────────────────────────────────────────
check('Montana adds no service-completion standard',
  Object.keys(engine.SERVICE_COMPLETION_STANDARDS), ['mo_rule_43_01_d']);
check('and Delaware\'s mail-only extension is untouched',
  ['mail', 'email', 'left_with_clerk', 'other_consented_means']
    .map(m => engine.SERVICE_EXTENSION_STANDARDS.de_super_ct_civ_r_6e.qualifies(m)),
  [true, false, false, false]);

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
if (fail) process.exit(1);
