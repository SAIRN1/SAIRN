// Mississippi deadline rows -- isolated verification against the REAL engine and
// the REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Mississippi's rules are free and official and its CODE is not, which is the
// mirror image of Colorado. Five things here would be wrong if carried from any
// neighbour, and each is asserted as arithmetic rather than as a comment:
//
//   - THE CALENDAR IS TWO DAYS LONG ON PURPOSE. Miss. Code Ann. Sec. 3-3-7(2)
//     lets any county trade any ONE of the ten statutory holidays for Mardi
//     Gras or another day, excepting only the third Monday in January and
//     11 November. Jackson County has actually done it. The absences are
//     asserted, because the absence IS the finding.
//   - THE MAIL EXTENSION IS PERIOD-LENGTHENING, asserted against the date the
//     federal after-expiry order would have produced on a base period landing
//     on a Saturday.
//   - MAIL AND NOTHING ELSE, even though Rule 5(b) has permitted electronic
//     service since 1989 and MEC service since 2009.
//   - THE ANSWER TO A SUMMONS TAKES NO EXTENSION AT ALL -- Rule 6(e) says so in
//     terms -- asserted by computing that row WITH service_method 'mail'.
//   - TWO DISCOVERY PERIODS ARE ELECTIONS AND THE THIRD IS A FLOOR, so exactly
//     one row is a later_of.
//
// Plus the constraint that keeps this jurisdiction safe: NO BACKWARD ROW IS
// SEEDED AT ALL. That is asserted over the seed itself, not left to a reviewer,
// because it is the only way Mississippi could compute LATE. Under-inclusion is
// EARLY forward and LATE backward, in BOTH mechanisms -- the short-period
// exclusion and the last-day rollover -- so a longer period does not rescue a
// backward row. Rule 56(c)'s ten days clears the seven-day threshold and was
// still dropped for that reason.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_mississippi.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_mississippi.json'), 'utf8'));

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
    jurisdiction: 'ms', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));
const codeOf = r => (r.ok ? 'OK:' + r.due_date : r.code);

// ── The seed's own shape ──────────────────────────────────────────────────
check('11 rules seeded', seed.rules.length, 11);
check('every rule is Mississippi civil litigation on ms_r_civ_p_6',
  seed.rules.filter(r => r.jurisdiction === 'ms' && r.domain === 'civil-litigation'
    && r.computation === 'ms_r_civ_p_6').length, 11);
check('every rule cites the 2026-07-01 MRCP PDF and a verbatim quote',
  seed.rules.filter(r => /^https:\/\/courts\.ms\.gov\/research\/rules\/msrulesofcourt\/2026-07-01%20Rules%20of%20Civil%20Procedure/.test(r.authority.url)
    && r.authority.quote && r.authority.quote.length > 40).length, 11);
check('no rule points at the commented-out 2026-06-18 file, which is a soft-404',
  seed.rules.filter(r => /2026-06-18/.test(r.authority.url)).length, 0);
// Rules 12, 36 and 56 carry no amendment bracket in the PDF, so they date from
// adoption; Rules 33 and 34 were amended four days apart in October 2021 by two
// separate orders.
check('effective dates are per rule, four distinct values',
  [...new Set(seed.rules.map(r => r.effective_from))].sort(),
  ['1982-01-01', '1997-07-01', '2021-10-07', '2021-10-11']);

// ── The election / floor split, inside one rule set ──────────────────────
check('EXACTLY ONE row is a later_of -- admissions, the only rule that says "shall not be required"',
  seed.rules.filter(r => typeof r.trigger_event !== 'string').map(r => r.rule_id),
  ['ms-36a-admissions-answer-later-of']);
check('Rules 33 and 34 are plain rows -- both say a defendant "MAY serve"',
  ['ms-33b3-interrogatory-answers-30-days', 'ms-34b-production-response-30-days']
    .map(id => typeof seed.rules.find(r => r.rule_id === id).trigger_event), ['string', 'string']);

// ── THE SAFETY CONSTRAINT, asserted over the seed rather than trusted ────
// Under-inclusion is EARLY forward and LATE backward, in both the short-period
// exclusion and the last-day rollover. A longer period fixes only the first.
{
  check('NO Mississippi row is seeded backward, at any length',
    seed.rules.filter(r => r.count && r.count.direction === 'backward').map(r => r.rule_id), []);
  check('every seeded row states its direction explicitly rather than defaulting',
    seed.rules.filter(r => r.count && !r.count.direction).map(r => r.rule_id), []);
  // resolve_periods limbs are forward-only in the engine, so the later_of row
  // cannot smuggle a backward count in either.
  check('the later_of limbs declare no direction, and the engine implements forward only',
    seed.rules.filter(r => typeof r.trigger_event !== 'string')
      .flatMap(r => r.trigger_event.limbs.map(L => L.count.direction || 'forward')), ['forward', 'forward']);
}

// ── The standards ────────────────────────────────────────────────────────
const std = engine.COMPUTATION_STANDARDS.ms_r_civ_p_6;
check('ms_r_civ_p_6 excludes below SEVEN, in both directions',
  [!!std, std.impl, std.short_period_exclusion_days, std.short_period_exclusion_directions],
  [true, 'frcp_6a', 7, undefined]);
const ext = engine.SERVICE_EXTENSION_STANDARDS.ms_r_civ_p_6_e;
check('the order is PERIOD-LENGTHENING, not the federal after-expiry order',
  ext.sequence, 'add_to_period_then_roll');
check('mail qualifies; electronic, e-mail, MEC e-filing and leaving-with-the-clerk do NOT',
  ['mail', 'electronic', 'email', 'efiling_service_provider', 'left_with_clerk'].map(m => ext.qualifies(m)),
  [true, false, false, false, false]);

// ── The calendar, where the ABSENCES are the finding ─────────────────────
const d2026 = Object.fromEntries(calendars.ms['2026'].map(d => [d.date, d.name]));
check('the 2026 calendar is exactly two days long', Object.keys(d2026).sort(),
  ['2026-01-19', '2026-11-11']);
check('both are the days Sec. 3-3-7(2) forbids a county to substitute away',
  [d2026['2026-01-19'].indexOf('Martin Luther King') > -1, d2026['2026-11-11'].indexOf('Armistice') > -1],
  [true, true]);
check('every substitutable statutory holiday is DELIBERATELY absent',
  ['2026-01-01', '2026-02-16', '2026-04-27', '2026-05-25', '2026-09-07', '2026-11-26', '2026-12-25']
    .map(x => x in d2026), [false, false, false, false, false, false, false]);
check('the permissive Friday-before-a-Saturday-holiday closure is absent too',
  '2026-07-03' in d2026, false);
check('every date is kind "declared" -- Rule 6(a) draws no forward-only distinction',
  [...new Set(calendars.ms['2026'].map(d => d.kind))], ['declared']);

// ── Arithmetic: the calendar bites, forward and backward ─────────────────
// 12 October 2026 + 30 = 11 November, Armistice Day, a Wednesday.
check('a 30-day answer landing on Armistice Day rolls to the Thursday',
  dateOf(compute('ms-12a-answer-summons-and-complaint-30-days', '2026-10-12')), '2026-11-12');
// The non-enlargeable post-judgment rows. 1 November 2026 + 10 = Wednesday
// 11 November, Armistice Day, so both roll to the Thursday -- and ten is not
// less than seven, so no intermediate exclusion fires on the way.
check('a Rule 59(b) new-trial motion landing on Armistice Day rolls to the Thursday',
  dateOf(compute('ms-59b-motion-for-new-trial-10-days', '2026-11-01')), '2026-11-12');
check('Rule 59(e) is the same ten days from the same trigger, and its own citation',
  [dateOf(compute('ms-59e-motion-to-alter-or-amend-judgment-10-days', '2026-11-01')),
   seed.rules.find(r => r.rule_id === 'ms-59e-motion-to-alter-or-amend-judgment-10-days').authority.citation],
  ['2026-11-12', 'Miss. R. Civ. P. 59(e)']);
// Rule 6(b) forbids the court to enlarge either, so neither may quietly acquire
// a service extension that would make a late filing look timely.
check('neither Rule 59 row declares a service extension -- entry of judgment is not service',
  ['ms-59b-motion-for-new-trial-10-days', 'ms-59e-motion-to-alter-or-amend-judgment-10-days']
    .map(id => 'service_extension' in seed.rules.find(r => r.rule_id === id)), [false, false]);
check('and a mailed service_method adds nothing to them',
  dateOf(compute('ms-59b-motion-for-new-trial-10-days', '2026-11-01', { service_method: 'mail' })), '2026-11-12');

// ── THE ORDER OF THE MAIL EXTENSION, proved against the alternative ──────
// 8 October 2026 + 30 = Saturday 7 November.
//   Mississippi (add to the period, then roll):  7 Nov + 3 = Tuesday 10 Nov.
//   Federal / Kansas (roll, add, roll again):    7 Nov -> 9 Nov, +3 = 12 Nov.
// Two days apart, and only one of them is Miss. R. Civ. P. 6(e).
check('mailed interrogatories: three days are ADDED TO THE PERIOD, then rolled',
  dateOf(compute('ms-33b3-interrogatory-answers-30-days', '2026-10-08', { service_method: 'mail' })),
  '2026-11-10');
check('the same row served electronically gets NOTHING -- Rule 6(e) never reached Rule 5(b) e-service',
  dateOf(compute('ms-33b3-interrogatory-answers-30-days', '2026-10-08', { service_method: 'electronic' })),
  '2026-11-09');

// ── THE RULE 4 CARVE-OUT, proved by computing the row WITH mail ──────────
check('the answer row declares no service_extension at all',
  'service_extension' in seed.rules.find(r => r.rule_id === 'ms-12a-answer-summons-and-complaint-30-days'), false);
check('a mailed summons adds NOTHING to the answer -- Rule 6(e) excludes Rule 4 responses in terms',
  [dateOf(compute('ms-12a-answer-summons-and-complaint-30-days', '2026-10-08')),
   dateOf(compute('ms-12a-answer-summons-and-complaint-30-days', '2026-10-08', { service_method: 'mail' }))],
  ['2026-11-09', '2026-11-09']);
// The cross-claim answer is the same 30 days and DOES take the three days,
// which is the whole reason the carve-out is worth a separate row.
check('an answer to a cross-claim, served by mail, DOES take the three days',
  dateOf(compute('ms-12a-answer-to-crossclaim-30-days', '2026-10-08', { service_method: 'mail' })), '2026-11-10');

// ── The admissions later_of ──────────────────────────────────────────────
{
  const rid = 'ms-36a-admissions-answer-later-of';
  check('partial triggers refuse rather than guess', codeOf(compute(rid, '2026-10-01')), 'INCOMPLETE_TRIGGERS');
  // Request 1 Oct + 30 = Saturday 31 Oct.  Summons 20 Sep + 45 = Wednesday 4 Nov.
  check('the 45-day summons floor governs when it is later',
    dateOf(compute(rid, '2026-10-01', { trigger_dates: {
      service_of_request_for_admission: '2026-10-01',
      service_of_summons_for_admission: '2026-09-20'
    } })), '2026-11-04');
  // Request 1 Oct + 30 = 31 Oct (Sat) -> 2 Nov.  Summons 1 Aug + 45 = 15 Sep.
  check('the plain 30 days governs when the summons was served long before',
    dateOf(compute(rid, '2026-10-01', { trigger_dates: {
      service_of_request_for_admission: '2026-10-01',
      service_of_summons_for_admission: '2026-08-01'
    } })), '2026-11-02');
}

// ── Refusals ─────────────────────────────────────────────────────────────
check('a 2027 trigger refuses -- the calendar is 2026 only and a later year is not derived',
  codeOf(compute('ms-12a-answer-summons-and-complaint-30-days', '2027-03-01')), 'NOT_PROVISIONED');
check('a Rule 34 trigger two days before the 2021 amendment refuses on effective_from',
  codeOf(compute('ms-34b-production-response-30-days', '2021-10-05')), 'NO_RULE_IN_FORCE');
check('an unseeded Mississippi event does not fall through to another rule',
  codeOf(engine.computeDeadline({
    jurisdiction: 'ms', domain: 'civil-litigation', trigger_event: 'hearing_date_for_opposing_affidavit',
    trigger_date: '2026-11-16', rules: seed.rules, calendars: calendars, as_of: '2026-11-16'
  })), 'NO_MATCHING_RULE');

// ── The coverage disclosure ──────────────────────────────────────────────
const cov = engine.JURISDICTION_COVERAGE.ms;
check('Mississippi discloses an incomplete calendar whose error direction is EARLY',
  [!!cov, cov.complete, cov.direction], [true, false, 'early']);
check('the disclosure names the substitution statute and the real county that used it',
  [/3-3-7\(2\)/.test(cov.detail), /Jackson County/.test(cov.detail), /25-1-99/.test(cov.detail)],
  [true, true, true]);
check('and it names the one shape that could compute LATE, and says it is closed by construction',
  /Counting BACKWARD it inverts/.test(cov.detail) && /NO MISSISSIPPI ROW IS SEEDED BACKWARD AT ALL/.test(cov.detail),
  true);

// ── Nothing else moved ───────────────────────────────────────────────────
check('the coverage table holds ms alongside the others',
  Object.keys(engine.JURISDICTION_COVERAGE).sort(),
  ['al', 'ar', 'de', 'fl', 'hi', 'id', 'ks', 'ma', 'md', 'mn', 'mo', 'ms', 'mt', 'ne', 'nh', 'nm', 'nv', 'ut', 'va', 'wi']);
check('Mississippi adds no service-completion standard',
  Object.keys(engine.SERVICE_COMPLETION_STANDARDS), ['mo_rule_43_01_d']);
// A pre-existing jurisdiction with the SAME seven-day threshold must be
// untouched -- ms_r_civ_p_6 and oh_civ_r_6a are separate standards that happen
// to agree on one number.
{
  const ohSeed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_ohio.json'), 'utf8'));
  const ohCal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_2027_2031.json'), 'utf8'));
  check('Ohio still declares its own standard, not Mississippi\'s',
    [engine.COMPUTATION_STANDARDS.ohio_civ_r_6a.short_period_exclusion_days,
     ohSeed.rules.every(r => r.computation !== 'ms_r_civ_p_6'),
     Array.isArray(ohCal.holiday_calendars)],
    [7, true, true]);
}

console.log((fail ? 'FAIL ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
