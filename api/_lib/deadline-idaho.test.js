// Idaho deadline rows -- isolated verification against the REAL engine and the
// REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Six things here would be wrong if carried from a neighbour, and each is
// asserted as arithmetic rather than as a comment:
//
//   - THE RULE NUMBER. Idaho restyled in 2016 and computation moved from Rule 6
//     to RULE 2.2. Rule 6 has pointed at nothing since 1 July 2016.
//   - NO SHORT-PERIOD EXCLUSION AT ALL. Four seeded rows are FOURTEEN days,
//     which Arkansas's threshold would exclude and Idaho's counts straight
//     through, so the absent field is asserted as undefined rather than small.
//   - NO DEFENDANT FLOOR ANYWHERE. "45 days" does not appear in the I.R.C.P.
//     Idaho is the first seeded state where no discovery row is a later_of.
//   - FRIDAY 3 JULY 2026 IS A HOLIDAY BY STATUTE and the Secretary of State's
//     own list does not show it. JUNETEENTH IS NOT, and the Secretary of
//     State's list does. Both halves are probed.
//   - RULE 2.2(c) SAYS "AFTER SERVICE" AND NOT "AFTER SERVICE OF A NOTICE",
//     which is four words fewer than Mississippi and decides a whole row.
//   - NO BACKWARD ROW IS SEEDED, and the seed is asserted to contain none.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_idaho.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_idaho.json'), 'utf8'));

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
  return engine.computeDeadline(Object.assign({
    jurisdiction: 'id', domain: rule.domain, trigger_event: rule.trigger_event,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));
const codeOf = r => (r.ok ? 'OK:' + r.due_date : r.code);

// ── The seed's own shape ──────────────────────────────────────────────────
check('11 rules seeded', seed.rules.length, 11);
check('every rule is Idaho civil litigation on id_ircp_2_2',
  seed.rules.filter(r => r.jurisdiction === 'id' && r.domain === 'civil-litigation'
    && r.computation === 'id_ircp_2_2').length, 11);
check('every rule cites the official I.R.C.P. page, a verbatim quote and retrieved_at',
  seed.rules.filter(r => r.authority.url === 'https://isc.idaho.gov/rules-procedure/ircp'
    && r.authority.quote && r.authority.quote.length > 40
    && r.authority.retrieved_at === '2026-08-30').length, 11);
check('two effective dates -- the 2016 restyling and the 2018 Rule 12 amendment',
  [...new Set(seed.rules.map(r => r.effective_from))].sort(), ['2016-07-01', '2018-07-01']);
check('NO row is a later_of -- Idaho has no defendant floor and no election',
  seed.rules.filter(r => typeof r.trigger_event !== 'string').length, 0);
check('NO backward row is seeded, at any length',
  seed.rules.filter(r => r.count && r.count.direction === 'backward').map(r => r.rule_id), []);

// ── The standards ────────────────────────────────────────────────────────
const std = engine.COMPUTATION_STANDARDS.id_ircp_2_2;
check('id_ircp_2_2 declares NO short-period exclusion at all',
  [!!std, std.impl, std.short_period_exclusion_days, std.label],
  [true, 'frcp_6a', undefined, 'I.R.C.P. 2.2']);
const ext = engine.SERVICE_EXTENSION_STANDARDS.id_ircp_2_2_c;
check('the order is PERIOD-LENGTHENING -- "added to the specified time"',
  ext.sequence, 'add_to_period_then_roll');
check('mail qualifies and nothing else does',
  ['mail', 'facsimile', 'electronic', 'email', 'efiling_service_provider', 'left_with_clerk']
    .map(m => ext.qualifies(m)), [true, false, false, false, false, false]);

// ── The calendar, where two entries disagree with the executive branch ───
const d2026 = Object.fromEntries(calendars.id['2026'].map(d => [d.date, d.name]));
check('the 2026 calendar has eleven dates',
  Object.keys(d2026).sort(),
  ['2026-01-01', '2026-01-19', '2026-02-16', '2026-05-25', '2026-07-03', '2026-07-04',
   '2026-09-07', '2026-10-12', '2026-11-11', '2026-11-26', '2026-12-25']);
check('JUNETEENTH IS ABSENT -- Idaho Code 73-108 does not enumerate it',
  '2026-06-19' in d2026, false);
check('FRIDAY 3 JULY IS PRESENT -- the statutory Saturday shift, which the SOS list omits',
  ['2026-07-03' in d2026, '2026-07-04' in d2026], [true, true]);
check('Columbus Day IS enumerated in Idaho and is carried',
  '2026-10-12' in d2026, true);
check('the day after Thanksgiving is NOT a statutory Idaho holiday',
  '2026-11-27' in d2026, false);
check('no 2027 calendar exists, even though 73-108 would generate one mechanically',
  Object.keys(calendars.id), ['2026']);

// ── Arithmetic: every day counts, and the statutory shift bites ──────────
// 16 November 2026 + 21 straight calendar days = Monday 7 December. It crosses
// Thanksgiving, which is a holiday here and is counted anyway -- that is the
// whole point of having no short-period exclusion.
check('a 21-day period counts Thanksgiving as an ordinary intermediate day',
  dateOf(compute('id-ircp-12a1A-answer-summons-and-complaint-21-days', '2026-11-16')), '2026-12-07');
// 12 June + 21 = Friday 3 July, a holiday only because 4 July is a Saturday.
// Rolling off it lands on Monday 6 July, because the 4th and 5th are the
// weekend. A calendar built from the Secretary of State's list would have
// answered 3 July.
check('a period landing on the SHIFTED Friday 3 July rolls all the way to Monday the 6th',
  dateOf(compute('id-ircp-12a1A-answer-summons-and-complaint-21-days', '2026-06-12')), '2026-07-06');
// 29 May + 21 = Friday 19 June, Juneteenth on the SOS list and not in the
// statute. It must NOT roll.
check('a period landing on Juneteenth does NOT roll -- the contested date, omitted on purpose',
  dateOf(compute('id-ircp-12a1A-answer-summons-and-complaint-21-days', '2026-05-29')), '2026-06-19');
check('a period landing on Columbus Day DOES roll',
  dateOf(compute('id-ircp-12a1A-answer-summons-and-complaint-21-days', '2026-09-21')), '2026-10-13');

// ── The extension: order, and the second roll ────────────────────────────
// Base 2026-12-16 (Wed) + 3 calendar days = Saturday 19 December, rolled to
// Monday the 21st.
check('mailed interrogatories: three days added to the period, then rolled off the Saturday',
  dateOf(compute('id-ircp-33b2-interrogatory-answers-30-days', '2026-11-16', { service_method: 'mail' })),
  '2026-12-21');
check('the same row served electronically gets NOTHING',
  dateOf(compute('id-ircp-33b2-interrogatory-answers-30-days', '2026-11-16', { service_method: 'electronic' })),
  '2026-12-16');
check('and facsimile gets nothing either -- Idaho wrote this rule in 2016 and still reached only mail',
  dateOf(compute('id-ircp-33b2-interrogatory-answers-30-days', '2026-11-16', { service_method: 'facsimile' })),
  '2026-12-16');

// ── FOUR WORDS: the Mississippi divergence, proved on identical triggers ─
// Both states run this period from "notice of the court's action". Mississippi
// extends for "the service of a NOTICE or other paper"; Idaho extends only
// "after service". So the Idaho row takes nothing and its sibling, which runs
// from SERVICE of the more definite statement, takes three days.
check('the post-motion row runs from NOTICE and takes NOTHING even when mailed',
  [dateOf(compute('id-ircp-12a2A-responsive-pleading-after-motion-denied-14-days', '2026-11-16')),
   dateOf(compute('id-ircp-12a2A-responsive-pleading-after-motion-denied-14-days', '2026-11-16', { service_method: 'mail' }))],
  ['2026-11-30', '2026-11-30']);
check('its sibling runs from SERVICE and does take the three days',
  dateOf(compute('id-ircp-12a2B-responsive-pleading-after-more-definite-statement-14-days', '2026-11-16',
    { service_method: 'mail' })), '2026-12-03');
check('and Mississippi still extends on ITS notice row, because its rule has the notice limb',
  engine.SERVICE_EXTENSION_STANDARDS.ms_r_civ_p_6_e.qualifies('mail'), true);

// ── Service of process, and the frozen Rule 59 pair ──────────────────────
check('the answer row declares no service_extension at all',
  'service_extension' in seed.rules.find(r => r.rule_id === 'id-ircp-12a1A-answer-summons-and-complaint-21-days'),
  false);
check('a mailed summons adds nothing while a mailed counterclaim pleading does',
  [dateOf(compute('id-ircp-12a1A-answer-summons-and-complaint-21-days', '2026-11-16', { service_method: 'mail' })),
   dateOf(compute('id-ircp-12a1B-answer-to-counterclaim-or-crossclaim-21-days', '2026-11-16', { service_method: 'mail' }))],
  ['2026-12-07', '2026-12-10']);
// Rule 2.2(b)(3) freezes 59(b) and 59(e) and says nothing about 59(c), which
// grants its own extension. Only 59(c) runs from service, so only it extends.
check('the two frozen Rule 59 rows take no extension; the one extendable row does',
  [dateOf(compute('id-ircp-59b-motion-for-new-trial-14-days', '2026-11-16', { service_method: 'mail' })),
   dateOf(compute('id-ircp-59e-motion-to-alter-or-amend-judgment-14-days', '2026-11-16', { service_method: 'mail' })),
   dateOf(compute('id-ircp-59c-opposing-affidavits-14-days', '2026-11-16', { service_method: 'mail' }))],
  ['2026-11-30', '2026-11-30', '2026-12-03']);

// ── Refusals ─────────────────────────────────────────────────────────────
check('a 2027 trigger refuses -- the calendar is not generated forward',
  codeOf(compute('id-ircp-12a1A-answer-summons-and-complaint-21-days', '2027-03-01')), 'NOT_PROVISIONED');
check('a Rule 12 trigger before the 2018 amendment refuses',
  codeOf(compute('id-ircp-12a1A-answer-summons-and-complaint-21-days', '2018-06-01')), 'NO_RULE_IN_FORCE');
check('a Rule 33 trigger before the 2016 restyling refuses',
  codeOf(compute('id-ircp-33b2-interrogatory-answers-30-days', '2016-06-01')), 'NO_RULE_IN_FORCE');
check('an unseeded Idaho event does not fall through to another rule',
  codeOf(engine.computeDeadline({
    jurisdiction: 'id', domain: 'civil-litigation', trigger_event: 'hearing_date_specified',
    trigger_date: '2026-11-16', rules: seed.rules, calendars: calendars, as_of: '2026-11-16'
  })), 'NO_MATCHING_RULE');

// ── The coverage disclosure ──────────────────────────────────────────────
const cov = engine.JURISDICTION_COVERAGE.id;
check('Idaho discloses an incomplete calendar whose error direction is EARLY',
  [!!cov, cov.complete, cov.direction], [true, false, 'early']);
check('the disclosure names the three lists, Juneteenth, and why no backward row is seeded',
  [/73-108/.test(cov.detail), /JUNETEENTH/.test(cov.detail),
   /Secretary of State/.test(cov.detail), /NO BACKWARD ROW IS SEEDED/.test(cov.detail)],
  [true, true, true, true]);

// ── Nothing else moved ───────────────────────────────────────────────────
check('the coverage table gained id and nothing else',
  Object.keys(engine.JURISDICTION_COVERAGE).sort(),
  ['al', 'ar', 'fl', 'hi', 'id', 'ks', 'ma', 'md', 'mn', 'mo', 'ms', 'ne', 'nh', 'nm', 'va', 'wi']);
check('Idaho adds no service-completion standard',
  Object.keys(engine.SERVICE_COMPLETION_STANDARDS), ['mo_rule_43_01_d']);
// The other four no-threshold jurisdictions must still declare no threshold,
// and the two neighbours seeded today must keep their own.
check('the no-exclusion family is intact and the two states seeded today keep their own numbers',
  ['ks_60_206', 'mn_rcp_6_01', 'ut_urcp_6', 'nv_nrcp_6', 'id_ircp_2_2'].map(k => {
    const s = engine.COMPUTATION_STANDARDS[k];
    return s ? (s.short_period_exclusion_days === undefined ? 'none' : s.short_period_exclusion_days)
             : 'ABSENT_STANDARD';
  }).concat([engine.COMPUTATION_STANDARDS.ms_r_civ_p_6.short_period_exclusion_days,
             engine.COMPUTATION_STANDARDS.nm_1_006.short_period_exclusion_days]),
  ['none', 'none', 'none', 'none', 'none', 7, 11]);

console.log((fail ? 'FAIL ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
