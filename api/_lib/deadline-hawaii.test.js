// Hawaiʻi deadline rows -- isolated verification against the REAL engine and the
// REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Five things would be wrong if carried from a neighbour:
//
//   - TWO DAYS FOR MAILED SERVICE, NOT THREE. Hawaiʻi is the only seeded
//     jurisdiction that says two, and an `add: 3` copied from anywhere else
//     over-counts by a day and reports LATE.
//   - FOUR HOLIDAYS THAT EXIST NOWHERE ELSE HERE -- Prince Kuhio Day, King
//     Kamehameha I Day, Statehood Day, and GOOD FRIDAY, the only computed-from-
//     Easter date in the whole engine. And NO Juneteenth, no Columbus Day, no
//     day after Thanksgiving.
//   - THE SEC. 8-2 WEEKEND SHIFT IS DELIBERATELY OMITTED, which in 2026 means
//     Friday 3 July must NOT roll. That is a reading, and it is probed.
//   - RULE 6(e) HAS THE NOTICE LIMB, so the post-motion row DOES take the days
//     -- where Idaho's and Nebraska's, on the same trigger words, take nothing.
//   - THE HOLIDAY REFERENT IS EXPRESS, naming HRS Sec. 8-1 by number, which is
//     exactly what Idaho's rule did not do.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_hawaii.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_hawaii.json'), 'utf8'));

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
    jurisdiction: 'hi', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));
const codeOf = r => (r.ok ? 'OK:' + r.due_date : r.code);
const ANSWER = 'hi-hrcp-12a1-answer-summons-and-complaint-20-days';

// ── The seed's own shape ──────────────────────────────────────────────────
check('11 rules seeded', seed.rules.length, 11);
check('every rule is Hawaiʻi civil litigation on hi_hrcp_6',
  seed.rules.filter(r => r.jurisdiction === 'hi' && r.domain === 'civil-litigation'
    && r.computation === 'hi_hrcp_6').length, 11);
check('every rule cites the official HRCP document, a verbatim quote and retrieved_at',
  seed.rules.filter(r => r.authority.url === 'https://www.courts.state.hi.us/wp-content/uploads/2024/09/hrcp_ada.htm'
    && r.authority.quote && r.authority.quote.length > 40
    && r.authority.retrieved_at === '2026-08-31').length, 11);
check('three effective dates -- Rule 12/59 in 2000, discovery in 2015, Rule 36 in 2026',
  [...new Set(seed.rules.map(r => r.effective_from))].sort(),
  ['2000-01-01', '2015-01-01', '2026-01-01']);
check('EXACTLY ONE row is a later_of -- admissions, the only rule saying "shall not be required"',
  seed.rules.filter(r => typeof r.trigger_event !== 'string').map(r => r.rule_id),
  ['hi-hrcp-36a-admissions-answer-later-of']);
check('NO backward row is seeded',
  seed.rules.filter(r => r.count && r.count.direction === 'backward').map(r => r.rule_id), []);

// ── ★ TWO DAYS, NOT THREE ────────────────────────────────────────────────
check('EVERY service extension adds 2 -- not one row carries 3',
  [...new Set(seed.rules.filter(r => r.service_extension).map(r => r.service_extension.add))], [2]);
check('and every one names the Hawaiʻi standard',
  [...new Set(seed.rules.filter(r => r.service_extension).map(r => r.service_extension.standard))],
  ['hi_hrcp_6_e']);

// ── The standards ────────────────────────────────────────────────────────
const std = engine.COMPUTATION_STANDARDS.hi_hrcp_6;
check('hi_hrcp_6 excludes below SEVEN, in both directions',
  [std.label, std.impl, std.short_period_exclusion_days, std.short_period_exclusion_directions],
  ['Haw. R. Civ. P. 6', 'frcp_6a', 7, undefined]);
const ext = engine.SERVICE_EXTENSION_STANDARDS.hi_hrcp_6_e;
check('the order is PERIOD-LENGTHENING -- "added to the prescribed period"',
  [ext.label, ext.sequence], ['Haw. R. Civ. P. 6(e)', 'add_to_period_then_roll']);
check('mail qualifies and nothing else does',
  ['mail', 'facsimile', 'electronic', 'email', 'efiling_service_provider'].map(m => ext.qualifies(m)),
  [true, false, false, false, false]);

// ── The calendar: four dates nowhere else, three absences ────────────────
const d2026 = Object.fromEntries(calendars.hi['2026'].map(d => [d.date, d.name]));
check('the 2026 calendar has thirteen dates',
  Object.keys(d2026).sort(),
  ['2026-01-01', '2026-01-19', '2026-02-16', '2026-03-26', '2026-04-03', '2026-05-25',
   '2026-06-11', '2026-07-04', '2026-08-21', '2026-09-07', '2026-11-11', '2026-11-26',
   '2026-12-25']);
check('the four Hawaiʻi-only holidays are present and named',
  [d2026['2026-03-26'], d2026['2026-06-11'], d2026['2026-08-21'], d2026['2026-04-03']],
  ['Prince Jonah Kuhio Kalanianaole Day', 'King Kamehameha I Day', 'Statehood Day', 'Good Friday']);
// Good Friday is computed from Easter, so it must be a Friday and it must be
// two days before Easter Sunday 5 April 2026.
check('Good Friday is derived: two days before Easter Sunday, and it IS a Friday',
  [new Date('2026-04-03T00:00:00Z').getUTCDay(),
   new Date('2026-04-05T00:00:00Z').getUTCDay()], [5, 0]);
check('Statehood Day is the THIRD FRIDAY in August, not a fixed date',
  new Date('2026-08-21T00:00:00Z').getUTCDay(), 5);
check('NO Juneteenth, NO Columbus Day, NO day after Thanksgiving -- Nebraska has all three',
  ['2026-06-19' in d2026, '2026-10-12' in d2026, '2026-11-27' in d2026], [false, false, false]);
check('the Sec. 8-2 shifted Friday is ABSENT and the Saturday itself is present',
  ['2026-07-03' in d2026, '2026-07-04' in d2026], [false, true]);
check('no 2027 calendar exists', Object.keys(calendars.hi), ['2026']);

// ── Arithmetic: the unique holidays roll, the omitted ones do not ────────
// 10 March 2026 + 20 straight days = Monday 30 March, crossing Prince Kuhio
// Day on the 26th and counting it, because 20 is not less than 7.
check('a 20-day period counts Prince Kuhio Day as an ordinary intermediate day',
  dateOf(compute(ANSWER, '2026-03-10')), '2026-03-30');
check('a period landing on PRINCE KUHIO DAY rolls to the Friday',
  dateOf(compute(ANSWER, '2026-03-06')), '2026-03-27');
check('a period landing on GOOD FRIDAY rolls through the weekend to Easter Monday',
  dateOf(compute(ANSWER, '2026-03-14')), '2026-04-06');
check('a period landing on KING KAMEHAMEHA I DAY rolls to the Friday',
  dateOf(compute(ANSWER, '2026-05-22')), '2026-06-12');
check('a period landing on STATEHOOD DAY rolls to the Monday',
  dateOf(compute(ANSWER, '2026-08-01')), '2026-08-24');
// The two deliberate omissions, probed as negatives.
check('a period landing on Friday 3 July does NOT roll -- the Sec. 8-2 shift is omitted',
  dateOf(compute(ANSWER, '2026-06-13')), '2026-07-03');
check('a period landing on Juneteenth does NOT roll -- Hawaiʻi has no Juneteenth',
  dateOf(compute(ANSWER, '2026-05-30')), '2026-06-19');

// ── The extension: two days, added to the period, then rolled ────────────
// Base 20 March (Friday) + 2 = Sunday 22 March, rolled to Monday the 23rd.
check('mailed: two days added to the period, then rolled off the Sunday',
  dateOf(compute('hi-hrcp-12a3B-responsive-pleading-after-more-definite-statement-10-days',
    '2026-03-10', { service_method: 'mail' })), '2026-03-23');
// If this said three the answer would be Tuesday the 24th. That is the whole
// point of the two-day finding, asserted as a date rather than a field.
check('THREE days would have given the Tuesday, and does not',
  dateOf(compute('hi-hrcp-12a3B-responsive-pleading-after-more-definite-statement-10-days',
    '2026-03-10', { service_method: 'mail' })) !== '2026-03-24', true);
check('electronic service gets NOTHING',
  dateOf(compute('hi-hrcp-33b3-interrogatory-answers-30-days', '2026-03-10',
    { service_method: 'electronic' })), '2026-04-09');

// ── The notice limb: the third answer across four states ─────────────────
check('the NOTICE row DOES take the two days here, unlike Idaho and Nebraska',
  [dateOf(compute('hi-hrcp-12a3A-responsive-pleading-after-motion-denied-10-days', '2026-03-10')),
   dateOf(compute('hi-hrcp-12a3A-responsive-pleading-after-motion-denied-10-days', '2026-03-10',
     { service_method: 'mail' }))],
  ['2026-03-20', '2026-03-23']);
check('because Hawaiʻi and Mississippi have the notice limb and Idaho and Nebraska do not',
  [/notice or other paper/i.test(seed.rules.find(r => r.rule_id ===
     'hi-hrcp-12a3A-responsive-pleading-after-motion-denied-10-days').authority.note),
   engine.SERVICE_EXTENSION_STANDARDS.id_ircp_2_2_c.qualifies('mail'),
   engine.SERVICE_EXTENSION_STANDARDS.ne_6_1106_c.qualifies('mail')],
  [true, true, true]);
check('a mailed summons adds nothing to the answer; a mailed cross-claim does',
  [dateOf(compute(ANSWER, '2026-03-10', { service_method: 'mail' })),
   dateOf(compute('hi-hrcp-12a2-answer-to-crossclaim-20-days', '2026-03-10', { service_method: 'mail' }))],
  ['2026-03-30', '2026-04-01']);
check('both Rule 59 rows take nothing -- entry of judgment is not service of a paper',
  [dateOf(compute('hi-hrcp-59b-motion-for-new-trial-10-days', '2026-03-10', { service_method: 'mail' })),
   dateOf(compute('hi-hrcp-59e-motion-to-alter-or-amend-judgment-10-days', '2026-03-10', { service_method: 'mail' }))],
  ['2026-03-20', '2026-03-20']);

// ── The later-of ─────────────────────────────────────────────────────────
{
  const rid = 'hi-hrcp-36a-admissions-answer-later-of';
  check('partial triggers refuse rather than guess', codeOf(compute(rid, '2026-03-10')), 'INCOMPLETE_TRIGGERS');
  check('the 45-day summons floor governs when it is later',
    dateOf(compute(rid, '2026-03-10', { trigger_dates: {
      service_of_request_for_admission: '2026-03-10',
      service_of_summons_and_complaint_for_admission: '2026-03-01' } })), '2026-04-15');
  check('the plain 30 days governs when the summons was served long before',
    dateOf(compute(rid, '2026-03-10', { trigger_dates: {
      service_of_request_for_admission: '2026-03-10',
      service_of_summons_and_complaint_for_admission: '2026-01-05' } })), '2026-04-09');
}

// ── Refusals ─────────────────────────────────────────────────────────────
check('a 2027 trigger refuses -- the calendar is not generated forward',
  codeOf(compute(ANSWER, '2027-03-01')), 'NOT_PROVISIONED');
check('the admissions row refuses before its 1 January 2026 amendment',
  codeOf(compute('hi-hrcp-36a-admissions-answer-later-of', '2025-06-01', { trigger_dates: {
    service_of_request_for_admission: '2025-06-01',
    service_of_summons_and_complaint_for_admission: '2025-05-01' } })), 'NO_RULE_IN_FORCE');
check('an unseeded Hawaiʻi event does not fall through to another rule',
  codeOf(engine.computeDeadline({
    jurisdiction: 'hi', domain: 'civil-litigation', trigger_event: 'hearing_date_specified',
    trigger_date: '2026-03-10', rules: seed.rules, calendars: calendars, as_of: '2026-03-10'
  })), 'NO_MATCHING_RULE');

// ── The coverage disclosure ──────────────────────────────────────────────
const cov = engine.JURISDICTION_COVERAGE.hi;
check('Hawaiʻi discloses an incomplete calendar whose error direction is EARLY',
  [!!cov, cov.complete, cov.direction], [true, false, 'early']);
check('the disclosure names the three omissions and the exact date the shift affects',
  [/SEC\. 8-2/.test(cov.detail), /FRIDAY 3 JULY 2026/.test(cov.detail),
   /GENERAL ELECTION DAY/.test(cov.detail), /proclamation/i.test(cov.detail)],
  [true, true, true, true]);
check('and it records that Rule 6 was amended twice without a redline',
  /not determined/i.test(cov.detail), true);

// ── Nothing else moved ───────────────────────────────────────────────────
check('the coverage table gained hi and nothing else',
  Object.keys(engine.JURISDICTION_COVERAGE).sort(),
  ['al', 'ar', 'fl', 'hi', 'id', 'ks', 'ma', 'md', 'mn', 'mo', 'ms', 'ne', 'nh', 'nm', 'nv', 'ut', 'va', 'wi']);
check('Hawaiʻi adds no service-completion standard',
  Object.keys(engine.SERVICE_COMPLETION_STANDARDS), ['mo_rule_43_01_d']);
// Hawaiʻi is the ONLY two-day extension. Every other enumerated standard that
// a seeded row uses must still be paired with its own amount.
check('no other jurisdiction seeded today or yesterday moved to two days',
  ['sql/sairnlaw_deadline_seed_idaho.json', 'sql/sairnlaw_deadline_seed_nebraska.json',
   'sql/sairnlaw_deadline_seed_mississippi.json', 'sql/sairnlaw_deadline_seed_newmexico.json']
    .map(f => [...new Set(JSON.parse(fs.readFileSync(path.join(SQL, '..', f), 'utf8')).rules
      .filter(r => r.service_extension).map(r => r.service_extension.add))]),
  [[3], [3], [3], [3]]);

console.log((fail ? 'FAIL ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
