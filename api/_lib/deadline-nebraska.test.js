// Nebraska deadline rows -- isolated verification against the REAL engine and
// the REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// The centrepiece assertion is not ours. Comment [3] to Neb. Ct. R. Pldg.
// § 6-1106 works an example in the rule's own text -- 30 days ending on a
// Saturday expires Monday, and three added days make it THURSDAY -- and the
// engine is asserted against it directly. No other seeded jurisdiction supplies
// a worked example of the exact sequencing this engine models.
//
// Five more things would be wrong if carried from a neighbour:
//
//   - THE PRIOR RULES ARE STILL PUBLISHED, correctly labelled, one click away,
//     and the 2025 amendments moved 20 -> 21 and 15 -> 21. Every row carries the
//     current number, and a pre-2025 trigger REFUSES.
//   - NO SHORT-PERIOD EXCLUSION AT ALL.
//   - ARBOR DAY, the last Friday in April, exists on no other calendar here.
//     Nor does the day after Thanksgiving as a STATUTORY holiday. Idaho, the
//     neighbour seeded the same day, has neither, nor Juneteenth.
//   - ALL THREE DISCOVERY RULES SAY "WHICHEVER IS LONGER" IN THEIR OWN WORDS,
//     where Idaho has no floor at all.
//   - MAIL ONLY, BY CROSS-REFERENCE to one lettered subparagraph out of six.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_nebraska.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_nebraska.json'), 'utf8'));

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
    jurisdiction: 'ne', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));
const codeOf = r => (r.ok ? 'OK:' + r.due_date : r.code);

// ── The seed's own shape ──────────────────────────────────────────────────
check('10 rules seeded', seed.rules.length, 10);
check('every rule is Nebraska civil litigation on ne_25_2221',
  seed.rules.filter(r => r.jurisdiction === 'ne' && r.domain === 'civil-litigation'
    && r.computation === 'ne_25_2221').length, 10);
check('every rule carries a verbatim quote and retrieved_at',
  seed.rules.filter(r => r.authority.quote && r.authority.quote.length > 40
    && r.authority.retrieved_at === '2026-08-30').length, 10);
// Two sources: the court rules (nebraskajudicial.gov exports) and the
// Legislature's own statute pages for the two post-judgment motions.
check('eight rows cite the judicial branch and two cite the Legislature',
  [seed.rules.filter(r => /nebraskajudicial\.gov/.test(r.authority.url)).length,
   seed.rules.filter(r => /nebraskalegislature\.gov/.test(r.authority.url)).length], [8, 2]);
check('two effective dates -- the 2025 amendments and the 2004 statutory convention',
  [...new Set(seed.rules.map(r => r.effective_from))].sort(), ['2005-01-01', '2025-01-01']);
check('NO backward row is seeded',
  seed.rules.filter(r => r.count && r.count.direction === 'backward').map(r => r.rule_id), []);
check('ALL THREE discovery rows are later_of -- the rule says "whichever is longer"',
  seed.rules.filter(r => typeof r.trigger_event !== 'string').map(r => r.rule_id).sort(),
  ['ne-6-333b2-interrogatory-answers-later-of',
   'ne-6-334b2A-production-response-later-of',
   'ne-6-336a4-admissions-answer-later-of']);

// ── The standards ────────────────────────────────────────────────────────
const std = engine.COMPUTATION_STANDARDS.ne_25_2221;
check('ne_25_2221 is a STATUTE and declares no short-period exclusion',
  [std.label, std.impl, std.short_period_exclusion_days],
  ['Neb. Rev. Stat. § 25-2221', 'frcp_6a', undefined]);
check('§ 25-2221 is unsubdivided, so every citation suffix is empty rather than guessed',
  [std.base_period_suffix, std.months_years_suffix,
   std.rollover_suffix_forward, std.rollover_suffix_backward], ['', '', '', '']);
const ext = engine.SERVICE_EXTENSION_STANDARDS.ne_6_1106_c;
check('the order is AFTER-EXPIRY, which the 2024 amendment exists to state',
  [ext.label, ext.sequence], ['Neb. Ct. R. Pldg. § 6-1106(c)', 'roll_then_add_then_roll']);
check('mail qualifies; the five sibling methods named beside it do not',
  ['mail', 'email', 'electronic', 'designated_delivery_service', 'efiling_service_provider',
   'other_consented_means'].map(m => ext.qualifies(m)),
  [true, false, false, false, false, false]);

// ── ★ THE COURT'S OWN WORKED EXAMPLE ─────────────────────────────────────
// Comment [3] to § 6-1106: "answers to interrogatories are normally due 30 days
// after service ... If the 30th day is a Saturday, the period would expire on
// Monday ... Adding 3 days after the period would otherwise expire (Monday)
// extends the period to Thursday."
//
// Interrogatories served Thursday 19 February 2026: +30 lands on Saturday
// 21 March, expires Monday 23 March, and mailed service adds three to give
// Thursday 26 March. Both halves asserted, because the unmailed date is what
// proves the "expire on Monday" step the comment describes.
{
  const rid = 'ne-6-333b2-interrogatory-answers-later-of';
  const dates = { service_of_interrogatories: '2026-02-19',
                  service_of_summons_for_interrogatories: '2026-01-01' };
  check('the 30th day is a Saturday, so the period expires on the MONDAY',
    dateOf(compute(rid, '2026-02-19', { trigger_dates: dates })), '2026-03-23');
  check('and three mailed days added AFTER that give the THURSDAY the comment names',
    dateOf(compute(rid, '2026-02-19', { trigger_dates: dates, service_method: 'mail' })), '2026-03-26');
  // Period-lengthening would have added three to the unrolled Saturday, giving
  // Tuesday 24 March. That is the reading the 2024 amendment removed.
  check('period-lengthening would have given the Tuesday, and does not',
    dateOf(compute(rid, '2026-02-19', { trigger_dates: dates, service_method: 'mail' })) !== '2026-03-24',
    true);
}

// ── The calendar: three dates its neighbour does not have ────────────────
const d2026 = Object.fromEntries(calendars.ne['2026'].map(d => [d.date, d.name]));
check('the 2026 calendar has fourteen dates',
  Object.keys(d2026).sort(),
  ['2026-01-01', '2026-01-19', '2026-02-16', '2026-04-24', '2026-05-25', '2026-06-19',
   '2026-07-03', '2026-07-04', '2026-09-07', '2026-10-12', '2026-11-11', '2026-11-26',
   '2026-11-27', '2026-12-25']);
check('ARBOR DAY is the last Friday in April and is named as such',
  [d2026['2026-04-24'], new Date('2026-04-24T00:00:00Z').getUTCDay()], ['Arbor Day', 5]);
check('Columbus Day and Indigenous Peoples\' Day are ONE entry under both names',
  d2026['2026-10-12'], 'Indigenous Peoples\' Day and Columbus Day');
check('the day after Thanksgiving is a STATUTORY holiday here',
  '2026-11-27' in d2026, true);
check('and Friday 3 July is derived from the mandatory Saturday shift',
  ['2026-07-03' in d2026, '2026-07-04' in d2026], [true, true]);
check('no 2027 calendar exists, even though § 25-2221 would generate one',
  Object.keys(calendars.ne), ['2026']);

// ── Arithmetic: every day counts, and the three unusual dates roll ───────
// 16 November 2026 + 30 straight calendar days = 16 December, crossing
// Thanksgiving AND the day after AND counting both, because there is no
// short-period exclusion and neither is the LAST day.
check('a 30-day period counts Thanksgiving and the day after as ordinary days',
  dateOf(compute('ne-6-1112a1A-answer-summons-and-complaint-30-days', '2026-11-16')), '2026-12-16');
check('a period landing on ARBOR DAY rolls to the Monday',
  dateOf(compute('ne-6-1112a1A-answer-summons-and-complaint-30-days', '2026-03-25')), '2026-04-27');
check('a period landing on JUNETEENTH rolls -- Nebraska enumerates it, Idaho does not',
  dateOf(compute('ne-6-1112a1A-answer-summons-and-complaint-30-days', '2026-05-20')), '2026-06-22');
check('a period landing on the day after Thanksgiving rolls to the Monday',
  dateOf(compute('ne-6-1112a1A-answer-summons-and-complaint-30-days', '2026-10-28')), '2026-11-30');
check('a period landing on the shifted Friday 3 July rolls to Monday the 6th',
  dateOf(compute('ne-6-1112a1A-answer-summons-and-complaint-30-days', '2026-06-03')), '2026-07-06');

// ── The notice / service split, same shape as Idaho ──────────────────────
check('the post-motion row runs from NOTICE and takes nothing even when mailed',
  [dateOf(compute('ne-6-1112a2A-responsive-pleading-after-motion-denied-21-days', '2026-11-16')),
   dateOf(compute('ne-6-1112a2A-responsive-pleading-after-motion-denied-21-days', '2026-11-16', { service_method: 'mail' }))],
  ['2026-12-07', '2026-12-07']);
check('its SERVICE sibling does take the three days',
  dateOf(compute('ne-6-1112a2B-responsive-pleading-after-more-definite-statement-21-days', '2026-11-16',
    { service_method: 'mail' })), '2026-12-10');
check('a mailed summons adds nothing to the answer; a mailed counterclaim pleading does',
  [dateOf(compute('ne-6-1112a1A-answer-summons-and-complaint-30-days', '2026-11-16', { service_method: 'mail' })),
   dateOf(compute('ne-6-1112a1B-answer-to-counterclaim-or-crossclaim-30-days', '2026-11-16', { service_method: 'mail' }))],
  ['2026-12-16', '2026-12-21']);
check('both statutory post-judgment rows take nothing -- entry of judgment is not service',
  [dateOf(compute('ne-25-1144-01-motion-for-new-trial-10-days', '2026-11-16', { service_method: 'mail' })),
   dateOf(compute('ne-25-1329-motion-to-alter-or-amend-judgment-10-days', '2026-11-16', { service_method: 'mail' }))],
  ['2026-11-30', '2026-11-30']);

// ── The later-of, and the Idaho contrast ─────────────────────────────────
{
  const rid = 'ne-6-336a4-admissions-answer-later-of';
  check('partial triggers refuse rather than guess', codeOf(compute(rid, '2026-10-01')), 'INCOMPLETE_TRIGGERS');
  check('the 45-day summons floor governs when it is later',
    dateOf(compute(rid, '2026-10-01', { trigger_dates: {
      service_of_request_for_admission: '2026-10-01',
      service_of_summons_for_admission: '2026-09-20' } })), '2026-11-04');
  check('the plain 30 days governs when the summons was served long before',
    dateOf(compute(rid, '2026-10-01', { trigger_dates: {
      service_of_request_for_admission: '2026-10-01',
      service_of_summons_for_admission: '2026-08-01' } })), '2026-11-02');
}
// Idaho's identical-looking Rule 36(a)(4) has NO floor. Reading Nebraska's row
// across would tell an Idaho defendant a matter is not yet admitted when it is.
check('Idaho, seeded the same day, still has no later_of on any discovery row',
  (() => {
    const idSeed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_idaho.json'), 'utf8'));
    return idSeed.rules.filter(r => typeof r.trigger_event !== 'string').length;
  })(), 0);

// ── Refusals: the still-published prior rules ────────────────────────────
check('a pre-2025 trigger REFUSES rather than answering with the superseded 20-day number',
  codeOf(compute('ne-6-1112a2A-responsive-pleading-after-motion-denied-21-days', '2024-11-16')),
  'NO_RULE_IN_FORCE');
check('the post-motion row carries the CURRENT 21, not the prior 20',
  seed.rules.find(r => r.rule_id === 'ne-6-1112a2A-responsive-pleading-after-motion-denied-21-days').count.value, 21);
check('and the ordered-reply row carries the CURRENT 21, not the prior 15',
  seed.rules.find(r => r.rule_id === 'ne-6-1112a1C-reply-after-order-to-reply-21-days').count.value, 21);
check('a 2027 trigger refuses -- the calendar is not generated forward',
  codeOf(compute('ne-6-1112a1A-answer-summons-and-complaint-30-days', '2027-03-01')), 'NOT_PROVISIONED');
check('an unseeded Nebraska event does not fall through to another rule',
  codeOf(engine.computeDeadline({
    jurisdiction: 'ne', domain: 'civil-litigation', trigger_event: 'hearing_date_specified',
    trigger_date: '2026-11-16', rules: seed.rules, calendars: calendars, as_of: '2026-11-16'
  })), 'NO_MATCHING_RULE');

// ── The coverage disclosure ──────────────────────────────────────────────
const cov = engine.JURISDICTION_COVERAGE.ne;
check('Nebraska discloses an incomplete calendar whose error direction is EARLY',
  [!!cov, cov.complete, cov.direction], [true, false, 'early']);
check('the disclosure names Arbor Day, the federal-override clause and the two open limbs',
  [/ARBOR DAY/.test(cov.detail), /FEDERAL holiday schedule/.test(cov.detail),
   /CHIEF JUSTICE/.test(cov.detail), /PROCLAMATION OF THE/.test(cov.detail)],
  [true, true, true, true]);

// ── Nothing else moved ───────────────────────────────────────────────────
check('the coverage table gained ne and nothing else',
  Object.keys(engine.JURISDICTION_COVERAGE).sort(),
  ['al', 'ar', 'fl', 'id', 'ks', 'ma', 'md', 'mn', 'mo', 'ms', 'ne', 'nm', 'va', 'wi']);
check('Nebraska adds no service-completion standard',
  Object.keys(engine.SERVICE_COMPLETION_STANDARDS), ['mo_rule_43_01_d']);
check('the no-exclusion family now has six members and the neighbours keep their own numbers',
  ['ks_60_206', 'mn_rcp_6_01', 'ut_urcp_6', 'nv_nrcp_6', 'id_ircp_2_2', 'ne_25_2221']
    .map(k => engine.COMPUTATION_STANDARDS[k].short_period_exclusion_days === undefined ? 'none' : 'HAS_ONE')
    .concat([engine.COMPUTATION_STANDARDS.ms_r_civ_p_6.short_period_exclusion_days,
             engine.COMPUTATION_STANDARDS.nm_1_006.short_period_exclusion_days]),
  ['none', 'none', 'none', 'none', 'none', 'none', 7, 11]);

console.log((fail ? 'FAIL ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
