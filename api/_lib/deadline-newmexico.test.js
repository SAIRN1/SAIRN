// New Mexico deadline rows -- isolated verification against the REAL engine and
// the REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Five things here would be wrong if carried from a neighbour or from any
// secondary source, and each is asserted as arithmetic rather than as a comment:
//
//   - ELECTRONIC SERVICE NO LONGER GETS THREE DAYS. Supreme Court Order No.
//     S-1-RCR-2023-00046 struck "electronic transmission," from Rule 1-006(C)
//     effective 31 December 2024. Facsimile survived. Every secondary source
//     still quotes the old list, and granting the days reports THREE DAYS LATE.
//   - THE THRESHOLD IS ELEVEN, NOT THE TEN THE RULE PRINTS. "Ten days or less"
//     is < 11 at a strict-less-than field, and the ten-day rows are exactly
//     where writing 10 would stop excluding.
//   - PRESIDENTS' DAY IS OBSERVED IN NOVEMBER. The judiciary observes it on the
//     day after Thanksgiving; Rule 1-006(A)(7)(a) says so in a parenthetical. A
//     generated third-Monday-in-February calendar is wrong in both directions,
//     and both directions are probed.
//   - THE THREE ADDED DAYS COUNT STRAIGHT THROUGH weekends and holidays even
//     when the base period excluded them -- one rule, two opposite counting
//     modes, applied in sequence.
//   - A SHORT BACKWARD ROW IS SAFE HERE, which it was not in Mississippi,
//     because Rule 1-006(A)(6) states which way "next day" runs.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_newmexico.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_newmexico.json'), 'utf8'));

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
    jurisdiction: 'nm', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));
const codeOf = r => (r.ok ? 'OK:' + r.due_date : r.code);

// ── The seed's own shape ──────────────────────────────────────────────────
check('15 rules seeded', seed.rules.length, 15);
check('every rule is New Mexico civil litigation on nm_1_006',
  seed.rules.filter(r => r.jurisdiction === 'nm' && r.domain === 'civil-litigation'
    && r.computation === 'nm_1_006').length, 15);
check('every rule cites the official NMRA Rule Set 1 document and a verbatim quote',
  seed.rules.filter(r => r.authority.url === 'https://nmonesource.com/nmos/nmra/en/5687/1/document.do'
    && r.authority.quote && r.authority.quote.length > 40).length, 15);
check('every rule carries retrieved_at, so the load-state gate cannot false-STALE the jurisdiction',
  seed.rules.every(r => r.authority.retrieved_at === '2026-08-30'), true);
// Seven distinct dates, printed per rule, spanning 1980 to the December 2025
// amendment of Rule 1-055. Only the 1980 one is a convention.
check('effective dates are per rule, seven distinct values',
  [...new Set(seed.rules.map(r => r.effective_from))].sort(),
  ['1980-01-01', '1989-08-01', '2003-08-01', '2009-05-15', '2013-12-31', '2021-12-31', '2025-12-31']);

// ── The election / floor split ───────────────────────────────────────────
check('EXACTLY ONE row is a later_of -- admissions, the only rule that says "shall not be required"',
  seed.rules.filter(r => typeof r.trigger_event !== 'string').map(r => r.rule_id),
  ['nm-1-036a-admissions-answer-later-of']);
check('Rules 1-033 and 1-034 are plain rows -- both say a defendant "MAY serve"',
  ['nm-1-033c3-interrogatory-answers-30-days', 'nm-1-034b-production-response-30-days']
    .map(id => typeof seed.rules.find(r => r.rule_id === id).trigger_event), ['string', 'string']);

// ── The standards ────────────────────────────────────────────────────────
const std = engine.COMPUTATION_STANDARDS.nm_1_006;
check('nm_1_006 excludes below ELEVEN, in BOTH directions',
  [!!std, std.impl, std.short_period_exclusion_days, std.short_period_exclusion_directions],
  [true, 'frcp_6a', 11, undefined]);
const ext = engine.SERVICE_EXTENSION_STANDARDS.nm_1_006_c;
check('the order is the FEDERAL after-expiry order', ext.sequence, 'roll_then_add_then_roll');
// THE HEADLINE. Facsimile survived the 2024 amendment and electronic
// transmission did not, even though Rule 1-005(C)(1)(b) makes them siblings.
check('mail, FACSIMILE and court-facility deposit qualify; ELECTRONIC transmission and e-filing do NOT',
  ['mail', 'facsimile', 'court_facility_deposit', 'electronic', 'email', 'efiling_service_provider', 'electronic_mail']
    .map(m => ext.qualifies(m)),
  [true, true, true, false, false, false, false]);

// ── The calendar ─────────────────────────────────────────────────────────
const d2026 = Object.fromEntries(calendars.nm['2026'].map(d => [d.date, d.name]));
check('the 2026 calendar has eleven dates, one per named holiday in Rule 1-006(A)(7)(a)',
  Object.keys(d2026).sort(),
  ['2026-01-01', '2026-01-19', '2026-05-25', '2026-06-19', '2026-07-03', '2026-09-07',
   '2026-10-12', '2026-11-11', '2026-11-26', '2026-11-27', '2026-12-25']);
check('Presidents\' Day is the 27th of NOVEMBER, the day after Thanksgiving',
  d2026['2026-11-27'].indexOf('Presidents') > -1, true);
check('and the third Monday in February is NOT a holiday -- a generated calendar would add it',
  '2026-02-16' in d2026, false);
check('Independence Day is transcribed as observed on Friday 3 July, not shifted by a rule',
  ['2026-07-03' in d2026, '2026-07-04' in d2026], [true, false]);
check('no 2027 calendar exists, even though the 2026 memo announces 1 January 2027',
  Object.keys(calendars.nm), ['2026']);

// ── THE THRESHOLD, proved by two periods over the same trigger ───────────
// 16 November 2026 is a Monday. Counting ten days and excluding intermediate
// weekends and holidays skips BOTH Thanksgiving (26 Nov) and Presidents' Day
// (27 Nov) and lands on 2 December. Counting fifteen days straight through
// lands on 1 December -- EARLIER, from a LONGER period. That inversion only
// happens if the exclusion is really firing at ten and really not firing at
// fifteen.
check('a ten-day period excludes intermediate days and lands on 2 December',
  dateOf(compute('nm-1-012a2-responsive-pleading-after-more-definite-statement-10-days', '2026-11-16')),
  '2026-12-02');
check('a FIFTEEN-day period counts straight through and lands EARLIER, on 1 December',
  dateOf(compute('nm-1-056d2-response-memorandum-15-days', '2026-11-16')), '2026-12-01');
// The negative half of the Presidents' Day finding: nothing may roll off the
// third Monday in February.
check('a ten-day period spanning 16 February does NOT skip it',
  dateOf(compute('nm-1-012a2-responsive-pleading-after-more-definite-statement-10-days', '2026-02-09')),
  '2026-02-23');

// ── SHORT AND BACKWARD -- the shape Mississippi had to refuse ────────────
// 16 November 2026 minus three days, excluding intermediate weekends and
// Veterans Day (Wed 11 Nov): 13th, 12th, then skip the 11th, then the 10th.
check('the three-day default-judgment notice counts BACKWARD and skips Veterans Day',
  dateOf(compute('nm-1-055b-default-judgment-notice-3-days-before-hearing', '2026-11-16')), '2026-11-10');
check('and it is the only backward row, deliberately, with no service extension',
  seed.rules.filter(r => r.count && r.count.direction === 'backward')
    .map(r => [r.rule_id, 'service_extension' in r]),
  [['nm-1-055b-default-judgment-notice-3-days-before-hearing', false]]);

// ── THE EXTENSION: order, and the added days counting straight through ───
// Base period 2026-12-02 (already excluding two holidays), plus three CALENDAR
// days = Saturday 5 December, which then rolls to Monday 7 December. Both
// halves of Rule 1-006(C)'s own sentence, in one date.
check('mailed: three days added AFTER the period expires, counting weekends, then rolled',
  dateOf(compute('nm-1-012a2-responsive-pleading-after-more-definite-statement-10-days', '2026-11-16',
    { service_method: 'mail' })), '2026-12-07');
check('FACSIMILE gets the same three days -- it survived the 2024 amendment',
  dateOf(compute('nm-1-012a2-responsive-pleading-after-more-definite-statement-10-days', '2026-11-16',
    { service_method: 'facsimile' })), '2026-12-07');
check('ELECTRONIC transmission gets NOTHING -- struck effective 31 December 2024',
  dateOf(compute('nm-1-012a2-responsive-pleading-after-more-definite-statement-10-days', '2026-11-16',
    { service_method: 'electronic' })), '2026-12-02');
// A base period that does NOT land badly, so the second roll is provably
// conditional rather than always applied.
check('a fifteen-day period served by mail lands on Friday 4 December with no second roll',
  dateOf(compute('nm-1-056d2-response-memorandum-15-days', '2026-11-16', { service_method: 'mail' })),
  '2026-12-04');

// ── The service-of-process reading, proved by computing WITH mail ────────
check('the answer row declares no service_extension at all',
  'service_extension' in seed.rules.find(r => r.rule_id === 'nm-1-012a-answer-summons-and-complaint-30-days'),
  false);
check('a mailed summons adds NOTHING to the answer -- Rule 1-006(C) is read as reaching Rule 1-005 service only',
  [dateOf(compute('nm-1-012a-answer-summons-and-complaint-30-days', '2026-11-16')),
   dateOf(compute('nm-1-012a-answer-summons-and-complaint-30-days', '2026-11-16', { service_method: 'mail' }))],
  ['2026-12-16', '2026-12-16']);
check('while a mailed CROSS-CLAIM does take the three days',
  dateOf(compute('nm-1-012a-answer-to-crossclaim-30-days', '2026-11-16', { service_method: 'mail' })),
  '2026-12-21');
// The two ten-day Rule 1-012 rows differ on their trigger AND on whether the
// extension reaches them, and the rule states both differences in terms.
check('the post-motion row runs from the COURT\'S ACTION and takes no extension',
  [dateOf(compute('nm-1-012a1-responsive-pleading-after-motion-denied-10-days', '2026-11-16')),
   dateOf(compute('nm-1-012a1-responsive-pleading-after-motion-denied-10-days', '2026-11-16', { service_method: 'mail' }))],
  ['2026-12-02', '2026-12-02']);

// ── The admissions later_of ──────────────────────────────────────────────
{
  const rid = 'nm-1-036a-admissions-answer-later-of';
  check('partial triggers refuse rather than guess', codeOf(compute(rid, '2026-10-01')), 'INCOMPLETE_TRIGGERS');
  check('the 45-day summons floor governs when it is later',
    dateOf(compute(rid, '2026-10-01', { trigger_dates: {
      service_of_request_for_admission: '2026-10-01',
      service_of_summons_and_complaint_for_admission: '2026-09-20'
    } })), '2026-11-04');
  check('the plain 30 days governs when the summons was served long before',
    dateOf(compute(rid, '2026-10-01', { trigger_dates: {
      service_of_request_for_admission: '2026-10-01',
      service_of_summons_and_complaint_for_admission: '2026-08-01'
    } })), '2026-11-02');
}

// ── Refusals ─────────────────────────────────────────────────────────────
check('a 2027 trigger refuses -- the single announced 2027 date did NOT open a year',
  codeOf(compute('nm-1-012a-answer-summons-and-complaint-30-days', '2027-03-01')), 'NOT_PROVISIONED');
check('Rule 1-055 refuses before its December 2025 amendment',
  codeOf(compute('nm-1-055b-default-judgment-notice-3-days-before-hearing', '2025-12-20')), 'NO_RULE_IN_FORCE');
check('Rule 1-034 refuses before its December 2021 amendment',
  codeOf(compute('nm-1-034b-production-response-30-days', '2021-12-20')), 'NO_RULE_IN_FORCE');
check('an unseeded New Mexico event does not fall through to another rule',
  codeOf(engine.computeDeadline({
    jurisdiction: 'nm', domain: 'civil-litigation', trigger_event: 'service_of_subpoena_to_produce',
    trigger_date: '2026-11-16', rules: seed.rules, calendars: calendars, as_of: '2026-11-16'
  })), 'NO_MATCHING_RULE');

// ── The coverage disclosure ──────────────────────────────────────────────
const cov = engine.JURISDICTION_COVERAGE.nm;
check('New Mexico discloses an incomplete calendar whose error direction is EARLY',
  [!!cov, cov.complete, cov.direction], [true, false, 'early']);
check('the disclosure names the unavailability limb, the November Presidents\' Day, and the 2027 refusal',
  [/1-006\(A\)\(4\)/.test(cov.detail), /27 NOVEMBER 2026/.test(cov.detail), /2027 IS REFUSED/.test(cov.detail)],
  [true, true, true]);

// ── Nothing else moved ───────────────────────────────────────────────────
check('the coverage table gained nm and nothing else',
  Object.keys(engine.JURISDICTION_COVERAGE).sort(),
  ['al', 'ar', 'de', 'fl', 'hi', 'id', 'ks', 'ma', 'md', 'mn', 'mo', 'ms', 'ne', 'nh', 'nm', 'nv', 'ut', 'va', 'wi']);
check('New Mexico adds no service-completion standard',
  Object.keys(engine.SERVICE_COMPLETION_STANDARDS), ['mo_rule_43_01_d']);
// The two jurisdictions that also use an 11-day threshold must be untouched --
// nm_1_006, al_r_civ_p_6 and wi_801_15 are separate standards that agree on one
// number and on nothing else.
check('Alabama and Wisconsin still declare their own 11-day standards, with their own labels',
  [engine.COMPUTATION_STANDARDS.wi_801_15.short_period_exclusion_days,
   engine.COMPUTATION_STANDARDS.wi_801_15.label,
   engine.COMPUTATION_STANDARDS.nm_1_006.label],
  [11, 'Wis. Stat. Sec. 801.15', 'Rule 1-006 NMRA']);
// And Mississippi, seeded the same day, must keep its own 7 and its own
// mail-only extension.
check('Mississippi is unchanged by New Mexico landing beside it',
  [engine.COMPUTATION_STANDARDS.ms_r_civ_p_6.short_period_exclusion_days,
   engine.SERVICE_EXTENSION_STANDARDS.ms_r_civ_p_6_e.sequence,
   engine.SERVICE_EXTENSION_STANDARDS.ms_r_civ_p_6_e.qualifies('facsimile')],
  [7, 'add_to_period_then_roll', false]);

console.log((fail ? 'FAIL ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
