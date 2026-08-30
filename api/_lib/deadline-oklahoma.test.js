// Oklahoma deadline rows -- isolated verification against the REAL engine and
// the REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Every expected date below was worked out BY HAND from the statute text and
// the derived 25 O.S. 82.1(A) holiday list BEFORE the engine was run, and the
// cases target what actually differs in Oklahoma:
//
//   - THE ROLLOVER HAS LOUISIANA'S SHAPE. 12 O.S. 2006(A)(1) does NOT name
//     Saturday or Sunday; it rolls on "a legal holiday as defined by Section
//     82.1". Oklahoma is safe only because 82.1(A) opens "Each Saturday,
//     Sunday", statewide. Asserted here because the same structure BLOCKED
//     Louisiana and the difference is one clause in a different statute.
//   - THE SHORT-PERIOD THRESHOLD IS ELEVEN, not the 7 of six other states.
//     Every seeded row is >= 20 days, so no row reaches it -- asserted, so
//     that stays true if a short row is ever added.
//   - FOUR ANSWER ROWS, because the period turns on TWO facts the engine
//     cannot derive: the plaintiff's 20-vs-35 election, and whether process
//     went by mail (which changes the TRIGGER to receipt/refusal, not the
//     amount). Guessing either runs LATE.
//   - THE CALENDAR OMITS ONE DAY A YEAR on a weekday Christmas, because
//     82.1(A) says "the day before OR after" and only the Governor's
//     Executive Order resolves it -- and those orders are scanned images.
//     Omitting reports EARLY. Asserted in both directions.
//   - NO JUNETEENTH and NO COLUMBUS DAY.
//
// Run: node api/_lib/deadline-oklahoma.test.js
'use strict';

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_oklahoma.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_oklahoma.json'), 'utf8'));

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
    jurisdiction: 'ok', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── The seed's own shape ──────────────────────────────────────────────────
check('9 rules seeded', seed.rules.length, 9);
check('all rows are jurisdiction ok', seed.rules.every(r => r.jurisdiction === 'ok'), true);
check('every row uses ok_12_2006', seed.rules.every(r => r.computation === 'ok_12_2006'), true);
check('every row cites a real quote and url',
  seed.rules.every(r => r.authority.quote && /^https?:\/\//.test(r.authority.url)), true);

// FOUR ANSWER ROWS. Two facts the engine cannot derive, so two dimensions:
// 20-vs-35 (the plaintiff's election) x service-vs-receipt (mailed process).
check('four distinct answer rows, one per combination of the two facts',
  seed.rules.filter(r => /answer-(20|35)/.test(r.rule_id)).map(r => r.rule_id).sort(),
  ['ok-12-2006-d-answer-20-days-after-mail-receipt-or-refusal',
   'ok-12-2006-d-answer-35-days-after-mail-receipt-or-refusal',
   'ok-12-2012-a1-answer-20-days',
   'ok-12-2012-a4-answer-35-days-elected']);
// The trigger names must carry the fact, or a caller cannot tell them apart.
check('every answer trigger names its election explicitly',
  seed.rules.filter(r => /answer-(20|35)/.test(r.rule_id))
    .every(r => /_(20|35)_day/.test(r.trigger_event)), true);
check('the mailed-process rows run from RECEIPT OR REFUSAL, not service',
  seed.rules.filter(r => /after-mail/.test(r.rule_id))
    .every(r => /^receipt_or_refusal_/.test(r.trigger_event)), true);

// The extension reaches papers served between parties, not process.
check('NO answer row carries the extension -- process, or the proviso replacing it',
  seed.rules.filter(r => /answer-(20|35)/.test(r.rule_id)).some(r => r.service_extension), false);
check('exactly the four inter-party rows carry it',
  seed.rules.filter(r => r.service_extension).map(r => r.rule_id).sort(),
  ['ok-12-2012-a2-answer-to-crossclaim',
   'ok-12-2012-a3-reply-to-counterclaim',
   'ok-12-3233-interrogatory-response',
   'ok-12-3234-production-response']);
check('the admissions later-of row carries none',
  !!seed.rules.find(r => /3236/.test(r.rule_id)).service_extension, false);

// ── The standards ─────────────────────────────────────────────────────────
const std = engine.COMPUTATION_STANDARDS.ok_12_2006;
check('ok_12_2006 is registered', !!std, true);
check('THE THRESHOLD IS ELEVEN, not seven', std.short_period_exclusion_days, 11);
check('backward is blank -- 2006 has no backward provision', std.rollover_suffix_backward, '');
// No seeded row is short enough to reach the exclusion; assert it stays so.
check('no seeded row is under 11 days, so none reaches the exclusion',
  seed.rules.filter(r => r.count).every(r => r.count.value >= 11), true);

const ext = engine.SERVICE_EXTENSION_STANDARDS.ok_12_2006_d;
check('ok_12_2006_d is registered', !!ext, true);
check('it LENGTHENS the period', ext.sequence, 'add_to_period_then_roll');
check('mail, THIRD-PARTY COMMERCIAL CARRIER and electronic all qualify',
  ['mail', 'third_party_commercial_carrier', 'electronic'].map(m => ext.qualifies(m)),
  [true, true, true]);
// e-mail is not named in the statute; "electronic means" is.
check('and nothing else does', ['email', 'facsimile', 'hand_delivery'].map(m => ext.qualifies(m)),
  [false, false, false]);

// ── The calendar ──────────────────────────────────────────────────────────
check('the calendar covers 2026-2031',
  Object.keys(calendars.ok).sort(), ['2026', '2027', '2028', '2029', '2030', '2031']);
const d2026 = Object.fromEntries(calendars.ok['2026'].map(d => [d.date, d.name]));
check('NO JUNETEENTH on 19 June -- Oklahoma has none in 82.1', d2026['2026-06-19'], undefined);
check('NO COLUMBUS DAY', d2026['2026-10-12'], undefined);
check('the day after Thanksgiving IS a holiday',
  [d2026['2026-11-26'], d2026['2026-11-27']], ['Thanksgiving Day', 'The day after Thanksgiving Day']);
check('Independence Day 2026 observed Friday 3 July', d2026['2026-07-03'], 'Independence Day');
// THE OMITTED DAY, asserted in BOTH directions: 25 December 2026 is a Friday,
// so the statute adds one unidentified neighbour and neither may be encoded.
check('Christmas 2026 is present but its unidentified neighbour is NOT, either side',
  [d2026['2026-12-25'], d2026['2026-12-24'], d2026['2026-12-26']],
  ['Christmas Day', undefined, undefined]);
// 2027 is the clean year -- Christmas falls on a Saturday, so the statute
// names the Thursday and Friday before and nothing is ambiguous.
{
  const d2027 = Object.fromEntries(calendars.ok['2027'].map(d => [d.date, d.name]));
  check('a Saturday Christmas gives BOTH the Thursday and Friday before',
    [!!d2027['2027-12-23'], !!d2027['2027-12-24']], [true, true]);
}

// ── Arithmetic ────────────────────────────────────────────────────────────
check('answer 20: 2026-06-01 + 20 = Sun 21 Jun, rolls to Mon 22',
  dateOf(compute('ok-12-2012-a1-answer-20-days', '2026-06-01')), '2026-06-22');
check('answer 35 (elected): the SAME trigger date gives 2026-07-06 — fifteen days apart',
  dateOf(compute('ok-12-2012-a4-answer-35-days-elected', '2026-06-01')), '2026-07-06');
check('mailed process, 20 days from receipt or refusal',
  dateOf(compute('ok-12-2006-d-answer-20-days-after-mail-receipt-or-refusal', '2026-06-01')), '2026-06-22');
check('mailed process AND the election: 35 days from receipt or refusal',
  dateOf(compute('ok-12-2006-d-answer-35-days-after-mail-receipt-or-refusal', '2026-06-01')), '2026-07-06');
check('crossclaim answer: 20 days', dateOf(compute('ok-12-2012-a2-answer-to-crossclaim', '2026-06-01')), '2026-06-22');
check('reply to counterclaim: 20 days', dateOf(compute('ok-12-2012-a3-reply-to-counterclaim', '2026-06-01')), '2026-06-22');
check('interrogatories: 30 days', dateOf(compute('ok-12-3233-interrogatory-response', '2026-06-01')), '2026-07-01');
check('production: 30 days', dateOf(compute('ok-12-3234-production-response', '2026-06-01')), '2026-07-01');

// Rollover cases, including the one that proves the omitted day is omitted.
check('landing on a Sunday rolls to the Monday',
  dateOf(compute('ok-12-2012-a1-answer-20-days', '2026-06-15')), '2026-07-06');
check('landing on the OBSERVED Independence Day rolls past the weekend',
  dateOf(compute('ok-12-2012-a1-answer-20-days', '2026-06-13')), '2026-07-06');
check('landing on Christmas Day (Fri) rolls to Monday 28 December',
  dateOf(compute('ok-12-2012-a1-answer-20-days', '2026-12-05')), '2026-12-28');
// THE DISCLOSED GAP, AS ARITHMETIC. 24 December 2026 may or may not be a
// holiday -- only the Governor's order says -- so it is omitted and a deadline
// landing there does NOT roll. That is EARLY, and it is deliberate.
check('landing on 24 Dec 2026 does NOT roll -- the omitted day, EARLY by design',
  dateOf(compute('ok-12-2012-a1-answer-20-days', '2026-12-04')), '2026-12-24');

// ── The extension ─────────────────────────────────────────────────────────
check('discovery + mail: +3 to the period, one rollover, Mon 6 Jul',
  dateOf(compute('ok-12-3233-interrogatory-response', '2026-06-01', { service_method: 'mail' })), '2026-07-06');
check('THIRD-PARTY COMMERCIAL CARRIER qualifies -- unique to Oklahoma',
  dateOf(compute('ok-12-3234-production-response', '2026-06-01', { service_method: 'third_party_commercial_carrier' })), '2026-07-06');
check('electronic means qualifies',
  dateOf(compute('ok-12-2012-a2-answer-to-crossclaim', '2026-06-01', { service_method: 'electronic' })), '2026-06-24');
check('e-mail does NOT -- the statute says "electronic means", and the row lists that',
  compute('ok-12-3233-interrogatory-response', '2026-06-01', { service_method: 'email' }).service_extension.state,
  'not_qualifying');
check('supplying mail on an ANSWER row adds nothing -- the proviso replaces it',
  dateOf(compute('ok-12-2012-a1-answer-20-days', '2026-06-01', { service_method: 'mail' })), '2026-06-22');

// ── The admissions later-of ───────────────────────────────────────────────
{
  const both = engine.computeDeadline({
    jurisdiction: 'ok', domain: 'civil-litigation', trigger_event: 'oklahoma_admission_period_later_of',
    trigger_dates: {
      service_of_request_for_admission: '2026-06-01',
      filing_of_answer_to_petition: '2026-06-20'
    },
    rules: seed.rules, calendars: calendars, as_of: '2026-06-01'
  });
  // The period does not commence until the answer is filed, so the LATER date
  // governs: 20 June + 30 = 20 July.
  check('admissions: the period runs from the LATER of request and answer-filing',
    dateOf(both), '2026-07-20');

  const early = engine.computeDeadline({
    jurisdiction: 'ok', domain: 'civil-litigation', trigger_event: 'oklahoma_admission_period_later_of',
    trigger_dates: {
      service_of_request_for_admission: '2026-06-20',
      filing_of_answer_to_petition: '2026-06-01'
    },
    rules: seed.rules, calendars: calendars, as_of: '2026-06-01'
  });
  check('and it resolves on the DATE, not on limb order', dateOf(early), '2026-07-20');

  const one = engine.computeDeadline({
    jurisdiction: 'ok', domain: 'civil-litigation', trigger_event: 'oklahoma_admission_period_later_of',
    trigger_date: '2026-06-01', rules: seed.rules, calendars: calendars, as_of: '2026-06-01'
  });
  check('and REFUSES on a partial set rather than assuming the answer was filed',
    one.ok === false && /INCOMPLETE/.test(one.code || ''), true);
}

// ── The traps ─────────────────────────────────────────────────────────────
check('a bare "service_of_summons_and_petition" matches nothing -- the election must be stated',
  dateOf(engine.computeDeadline({
    jurisdiction: 'ok', domain: 'civil-litigation', trigger_event: 'service_of_summons_and_petition',
    trigger_date: '2026-06-01', rules: seed.rules, calendars: calendars, as_of: '2026-06-01'
  })), 'REFUSED:NO_MATCHING_RULE');
check('a pre-2019 trigger refuses on a discovery row',
  dateOf(compute('ok-12-3233-interrogatory-response', '2018-06-01')), 'REFUSED:NO_RULE_IN_FORCE');
check('a 2032 trigger refuses -- the calendar stops at 2031',
  dateOf(compute('ok-12-3233-interrogatory-response', '2032-03-01')), 'REFUSED:NOT_PROVISIONED');

// ── Nothing else moved ────────────────────────────────────────────────────
check('Oklahoma declares NO coverage entry',
  Object.keys(engine.JURISDICTION_COVERAGE).sort(), ['al', 'ar', 'ma', 'md', 'mn', 'mo', 'va', 'wi']);
{
  const orSeed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_oregon.json'), 'utf8'));
  const orCal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_oregon.json'), 'utf8'));
  const oc = {};
  for (const row of orCal.holiday_calendars) {
    oc[row.jurisdiction] = oc[row.jurisdiction] || {};
    oc[row.jurisdiction][String(row.year)] = row.dates;
  }
  // Oregon's threshold is 7 and Oklahoma's is 11. Same engine, different
  // standards -- if either ever takes the other's number, this catches it.
  check('Oregon still declares 7 where Oklahoma declares 11',
    [engine.COMPUTATION_STANDARDS.or_orcp_10.short_period_exclusion_days,
     engine.COMPUTATION_STANDARDS.ok_12_2006.short_period_exclusion_days], [7, 11]);
  const or = engine.computeDeadline({
    jurisdiction: 'or', domain: 'civil-litigation', trigger_event: 'service_of_summons',
    trigger_date: '2026-06-01', rules: orSeed.rules, calendars: oc, as_of: '2026-06-01'
  });
  check('Oregon still computes normally alongside Oklahoma', [or.ok, or.due_date], [true, '2026-07-01']);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
