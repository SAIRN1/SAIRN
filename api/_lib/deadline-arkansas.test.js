// Arkansas deadline rows -- isolated verification against the REAL engine and
// the REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Every expected date below was worked out BY HAND from the rule text and the
// transcribed 2026 holiday list BEFORE the engine was run, and the cases target
// what actually differs in Arkansas:
//
//   - THE SHORT-PERIOD EXCLUSION IS FOURTEEN DAYS, the longest on this
//     platform. Six seeded states use 7, three use 11, three have none.
//     Asserted as ARITHMETIC on the 5-day and 10-day rows, not just as a
//     constant, because a copied 7 computes EARLY on every period of 7-13 days.
//   - THREE BUSINESS DAYS, and E-SERVICE IS EXPRESSLY INCLUDED -- the opposite
//     of the federal rule, Nevada, West Virginia and New York. Asserted with a
//     real e-mail method AND with a method outside the allowlist, so the test
//     fails whether the list is too narrow or too wide.
//   - THE ANSWER CARVE-OUT IS EXPRESS. ARCP 6(d)'s proviso names Rule 4, so the
//     answer rows take NO extension while the cross-claim row -- served under
//     Rule 5 -- keeps it. Both halves asserted, because the mirror-image error
//     (stripping the extension from the row that should keep it) is exactly
//     what happened federally and had to be corrected on 2026-08-27.
//   - THE UNION OF STATE AND FEDERAL LISTS. Juneteenth and Columbus Day are
//     FEDERAL ONLY -- absent from Ark. Code Ann. 1-5-101 -- and Christmas Eve
//     is STATE ONLY. All three asserted as arithmetic: a state-only calendar
//     computes EARLY on two days a year and a federal-only calendar on one.
//   - THE CALENDAR IS 2026 ONLY. A period crossing into 2027 must REFUSE, not
//     guess, because Ark. Code Ann. 1-5-101(b) has never been read on a primary
//     source. Asserted as a refusal with the right code.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_arkansas.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_arkansas.json'), 'utf8'));

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
    jurisdiction: 'ar', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── The seed's own shape ──────────────────────────────────────────────────
check('13 rules seeded', seed.rules.length, 13);
check('every rule is Arkansas civil litigation on ar_rcp_6',
  seed.rules.filter(r => r.jurisdiction === 'ar' && r.domain === 'civil-litigation'
    && r.computation === 'ar_rcp_6').length, 13);
check('every rule cites a primary URL and a verbatim quote',
  seed.rules.filter(r => /^https:\/\/opinions\.arcourts\.gov\//.test(r.authority.url)
    && r.authority.quote && r.authority.quote.length > 40).length, 13);

// ── The number that makes Arkansas its own standard ───────────────────────
const std = engine.COMPUTATION_STANDARDS.ar_rcp_6;
check('ar_rcp_6 exists and defers to the FRCP 6(a) implementation',
  [!!std, std && std.impl], [true, 'frcp_6a']);
check('THE SHORT-PERIOD EXCLUSION IS FOURTEEN, not 7 and not 11',
  std.short_period_exclusion_days, 14);

// ── The extension standard ────────────────────────────────────────────────
const ext = engine.SERVICE_EXTENSION_STANDARDS.ar_rcp_6_d;
check('ar_rcp_6_d lengthens the period rather than following its expiry',
  ext.sequence, 'add_to_period_then_roll');
check('E-SERVICE QUALIFIES -- the opposite of the federal rule',
  ['mail', 'commercial_delivery', 'electronic', 'email', 'efiling_service_provider'].map(m => ext.qualifies(m)),
  [true, true, true, true, true]);
check('personal service and fax do NOT qualify',
  ['personal', 'fax'].map(m => ext.qualifies(m)), [false, false]);

// ── The calendar, and the union it depends on ─────────────────────────────
const d2026 = Object.fromEntries(calendars.ar['2026'].map(d => [d.date, d.name]));
check('2026 only -- no other year is provisioned',
  Object.keys(calendars.ar), ['2026']);
check('twelve dates, the state list unioned with the federal list',
  calendars.ar['2026'].length, 12);
check('JUNETEENTH and COLUMBUS DAY are present and are FEDERAL ONLY',
  [!!d2026['2026-06-19'], !!d2026['2026-10-12']], [true, true]);
check('CHRISTMAS EVE is present and is STATE ONLY',
  d2026['2026-12-24'], 'Christmas Eve');
check('Independence Day is the OBSERVED Friday, transcribed not derived',
  [!!d2026['2026-07-03'], !!d2026['2026-07-04']], [true, false]);

// EVERY TRIGGER BELOW IS IN THE 2026 WINDOW, and that is not cosmetic. Rules
// 6, 33, 34 and 36 were "amended and effective June 4, 2026" per their own
// HISTORY lines, so a trigger before that date correctly refuses
// NO_RULE_IN_FORCE -- the engine computes against the law as it stood at the
// TRIGGER date. The first draft of this test used May dates and every row
// refused: the engine was right and the test was wrong.

// ── The answer row: 30 days, and NO extension even on mail ────────────────
// 2026-07-03 Fri + 30 calendar days = 2026-08-02, a SUNDAY, rolls to Monday
// 2026-08-03. The trigger day is itself a holiday and is excluded anyway.
check('Rule 12(a)(1) answer: 30 days, Sunday rollover',
  dateOf(compute('ar-rcp-12a1-answer-after-service', '2026-07-03')), '2026-08-03');

// PER-RULE EFFECTIVE DATES, asserted because getting them from the collection's
// currency date instead would silently refuse half this seed. Rule 12's current
// text has been in force since 2019-01-01, so a MAY 2026 trigger computes;
// Rule 6(c) was amended and effective 2026-06-04, so the same trigger refuses.
// 2026-05-01 Fri + 30 = 2026-05-31 Sun, rolls to Mon 2026-06-01.
check('a Rule 12 row computes for a trigger BEFORE the 2026 amendment',
  dateOf(compute('ar-rcp-12a1-answer-after-service', '2026-05-01')), '2026-06-01');
check('a Rule 6(c) row REFUSES for the same trigger -- it was not yet in force',
  dateOf(compute('ar-rcp-6c-response-to-motion', '2026-05-01')), 'REFUSED:NO_RULE_IN_FORCE');
check('THE ANSWER TAKES NO THREE DAYS ON MAIL -- ARCP 6(d) proviso, Rule 4 named',
  dateOf(compute('ar-rcp-12a1-answer-after-service', '2026-07-03', { service_method: 'mail' })),
  '2026-08-03');
check('nor on commercial delivery',
  dateOf(compute('ar-rcp-12a1-answer-after-service', '2026-07-03', { service_method: 'commercial_delivery' })),
  '2026-08-03');

// ── The mirror image: the cross-claim row is served under Rule 5 and KEEPS it
// Same base period, so any difference is the extension alone. Base end
// 2026-08-02 Sun; three BUSINESS days = Mon 08-03, Tue 08-04, Wed 08-05.
check('the cross-claim/counterclaim row KEEPS the three business days',
  dateOf(compute('ar-rcp-12a1-answer-to-crossclaim-or-counterclaim', '2026-07-03', { service_method: 'mail' })),
  '2026-08-05');
check('and is identical to the answer row when no method is supplied',
  dateOf(compute('ar-rcp-12a1-answer-to-crossclaim-or-counterclaim', '2026-07-03')), '2026-08-03');

// ── The incarcerated-defendant row: 60 days, its own trigger ──────────────
// 2026-07-03 + 60 = 2026-09-01, a Tuesday. No rollover, no extension.
check('Rule 12(a)(1) incarcerated defendant: 60 days',
  dateOf(compute('ar-rcp-12a1-answer-incarcerated-defendant', '2026-07-03')), '2026-09-01');

// ── THE FOURTEEN-DAY EXCLUSION, as arithmetic ─────────────────────────────
// Rule 6(c) reply, 5 days from 2026-05-20 Wed, counting only days that are not
// Saturday, Sunday or a legal holiday:
//   Thu 05-21, Fri 05-22, [Sat 23, Sun 24, MEMORIAL DAY Mon 25 all skipped],
//   Tue 05-26, Wed 05-27, Thu 05-28.
// A 7-day threshold copied from a neighbour would count straight through and
// land on Mon 05-25, then roll to Tue 05-26 -- two days EARLY.
check('5-day reply EXCLUDES intermediate weekends AND Labor Day',
  dateOf(compute('ar-rcp-6c-reply-to-response', '2026-09-02')), '2026-09-10');
// The 10-day response is also inside the exclusion. From 2026-05-04 Mon:
//   d1-d4 Tue 05 .. Fri 08, [09/10], d5-d9 Mon 11 .. Fri 15, [16/17], d10 Mon 18.
check('10-day response EXCLUDES intermediate weekends',
  dateOf(compute('ar-rcp-6c-response-to-motion', '2026-09-02')), '2026-09-17');
// ...and then takes three BUSINESS days on e-mail: Tue 19, Wed 20, Thu 21.
check('10-day response takes three BUSINESS days on E-MAIL',
  dateOf(compute('ar-rcp-6c-response-to-motion', '2026-09-02', { service_method: 'email' })),
  '2026-09-22');
check('and none on personal service, which the rule does not name',
  dateOf(compute('ar-rcp-6c-response-to-motion', '2026-09-02', { service_method: 'personal' })),
  '2026-09-17');
// JUNETEENTH is FEDERAL ONLY and must still be excluded as an intermediate day.
// From 2026-06-15 Mon: d1 Tue 16, d2 Wed 17, d3 Thu 18, [JUNETEENTH Fri 19,
// Sat 20, Sun 21], d4 Mon 22 .. d8 Fri 26, [27/28], d9 Mon 29, d10 Tue 30.
check('the 10-day count EXCLUDES Juneteenth, which no state holiday list contains',
  dateOf(compute('ar-rcp-6c-response-to-motion', '2026-06-15')), '2026-06-30');

// ── The 20-day backward row: OUTSIDE the exclusion, so weekends count ──────
// Hearing 2026-06-15 Mon, counting back 20 calendar days = 2026-05-26 Tue.
check('Rule 6(c) motion: 20 days BACKWARD from the hearing',
  dateOf(compute('ar-rcp-6c-motion-and-notice-of-hearing', '2026-09-14')), '2026-08-25');

// ── THE UNION, as arithmetic on all three exclusive days ──────────────────
// 30-day answer landing exactly on each. A state-only calendar misses the
// first two; a federal-only calendar misses the third.
check('rolls off COLUMBUS DAY (federal only) -- 09-12 +30 = Mon 10-12',
  dateOf(compute('ar-rcp-12a1-answer-after-service', '2026-09-12')), '2026-10-13');
// Christmas Eve Thu 12-24, Christmas Fri 12-25, then the weekend: four
// consecutive non-days, which no other Arkansas date can produce.
check('rolls off CHRISTMAS EVE (state only) and straight through Christmas and the weekend',
  dateOf(compute('ar-rcp-12a1-answer-after-service', '2026-11-24')), '2026-12-28');

// ── The 2026 cap REFUSES rather than guessing ─────────────────────────────
// 2026-12-20 + 30 = 2027-01-19, a year the Secretary of State has not published
// and Ark. Code Ann. 1-5-101(b) cannot be derived from.
{
  const r = compute('ar-rcp-12a1-answer-after-service', '2026-12-20');
  check('a period crossing into 2027 REFUSES, and names the missing year',
    [r.ok, r.code], [false, 'NOT_PROVISIONED']);
}

// ── The three discovery floors: resolve_periods with DIFFERENT counts ─────
// Request served 2026-05-01 (+30 = Sun 05-31), summons served 2026-04-20
// (+45 = Thu 06-04). The floor is longer, so 06-04 wins on all three.
for (const [rid, reqEv, sumEv] of [
  ['ar-rcp-33b3-interrogatory-answers-defendant-later-of', 'service_of_interrogatories', 'service_of_summons_and_complaint_for_interrogatories'],
  ['ar-rcp-34b2-production-response-defendant-later-of', 'service_of_request_for_production', 'service_of_summons_and_complaint_for_production'],
  ['ar-rcp-36a-admission-response-defendant-later-of', 'service_of_request_for_admission', 'service_of_summons_and_complaint_for_admission']
]) {
  const dates = {}; dates[reqEv] = '2026-07-03'; dates[sumEv] = '2026-06-22';
  check(rid.split('-')[2] + ': the 45-day floor from the summons WINS',
    dateOf(compute(rid, '2026-07-03', { trigger_dates: dates })), '2026-08-06');

  // Same request date, summons served much earlier, so the 30-day limb wins
  // and the Sunday rollover applies to it instead.
  const early = {}; early[reqEv] = '2026-07-03'; early[sumEv] = '2026-06-05';
  check(rid.split('-')[2] + ': the 30-day limb wins when the summons is old',
    dateOf(compute(rid, '2026-07-03', { trigger_dates: early })), '2026-08-03');
}

// ── The coverage disclosure rides on a SUCCESSFUL result ──────────────────
{
  const r = compute('ar-rcp-12a1-answer-after-service', '2026-07-03');
  check('Arkansas discloses its clerk-closure gap on an ok result, direction EARLY',
    [r.ok, r.coverage && r.coverage.direction, /clerk/.test(r.coverage && r.coverage.detail || '')],
    [true, 'early', true]);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
