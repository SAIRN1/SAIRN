// Alaska deadline rows -- isolated verification against the REAL engine and the
// REAL seed/calendar JSON on disk (hank b63, 2026-10-28).
//
// REQUIREMENT: Alaska deadlines are computed from Alaska's OWN rule text, holiday
//   list and mail extension -- docs/sairnlaw-alaska-deadline-seed-gate.md.
//
// Every expected date below was derived BY HAND from the rule text and a
// calendar, before the engine was run, and each one names the reading it
// exercises. The ones that would be wrong if a neighbour were copied:
//
//   - SEWARD'S DAY (last Monday of March) and ALASKA DAY (18 October) exist in
//     no other seeded jurisdiction.
//   - THE SUNDAY SHIFT IS IN, THE SATURDAY SHIFT IS OUT. AS 44.12.020 makes the
//     Monday after a Sunday holiday a legal holiday; AS 44.12.025's Friday is
//     "for officers and employees of the state" only. So Monday 19 October 2026
//     rolls and Friday 3 July 2026 does NOT.
//   - MLK DAY IS NOT ENCODED (AS 44.12.010(a)(2) is "as provided in (b)", and
//     (b) is employment-only). Omitted on purpose: the EARLY reading.
//   - THE UNDER-7 TEST IS ON THE BASE COUNT, "not counting any period for
//     mailing added under subsection (c)", and the 3 mail days lengthen the
//     period with one rollover at the end.
//   - 4(h) process and the distribution-triggered rows take NO mail days.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_alaska.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_alaska.json'), 'utf8'));

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
    jurisdiction: 'ak', domain: rule.domain, trigger_event: rule.trigger_event,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── The seed's own shape ──────────────────────────────────────────────
check('12 rules seeded', seed.rules.length, 12);
check('all rows are jurisdiction ak', seed.rules.every(r => r.jurisdiction === 'ak'), true);
check('every row uses an Alaska standard',
  seed.rules.every(r => r.computation === 'ak_civ_r_6a' || r.computation === 'ak_app_r_502a'), true);
check('only the appellate row uses App. R. 502(a)',
  seed.rules.filter(r => r.computation === 'ak_app_r_502a').map(r => r.rule_id), ['ak-app-r-204a1-notice-of-appeal']);
check('every rule id is unique', new Set(seed.rules.map(r => r.rule_id)).size, seed.rules.length);
check('every row cites a quote, a url and retrieved_at',
  seed.rules.every(r => r.authority && r.authority.quote && r.authority.url && r.authority.retrieved_at), true);
check('every extension is ak_civ_r_6c, +3 calendar days, mail only',
  seed.rules.filter(r => r.service_extension).every(r =>
    r.service_extension.standard === 'ak_civ_r_6c' && r.service_extension.add === 3 &&
    r.service_extension.unit === 'calendar_days' &&
    JSON.stringify(r.service_extension.applies_when) === '["mail"]'), true);
check('exactly the process and distribution rows carry NO extension',
  seed.rules.filter(r => !r.service_extension).map(r => r.rule_id),
  ['ak-civ-r-12a-answer-to-complaint', 'ak-civ-r-12a-state-answer',
   'ak-civ-r-59b-motion-for-new-trial', 'ak-app-r-204a1-notice-of-appeal']);

// ── The standards ─────────────────────────────────────────────────────
const CS = engine.COMPUTATION_STANDARDS, XS = engine.SERVICE_EXTENSION_STANDARDS;
check('ak_civ_r_6a uses the Ohio mechanism', CS.ak_civ_r_6a.impl, 'ohio_civ_r_6a');
check('ak_civ_r_6a short-period exclusion is "less than seven days"', CS.ak_civ_r_6a.short_period_exclusion_days, 7);
check('ak_app_r_502a has the same mechanism', [CS.ak_app_r_502a.impl, CS.ak_app_r_502a.short_period_exclusion_days],
  ['ohio_civ_r_6a', 7]);
check('ak_civ_r_6c extends for NON-ELECTRONIC MAIL ONLY',
  ['mail', 'email', 'facsimile', 'efiling_service', 'electronic', 'personal'].filter(m => XS.ak_civ_r_6c.qualifies(m)),
  ['mail']);
check('ak_civ_r_6c lengthens the period', XS.ak_civ_r_6c.sequence, 'add_to_period_then_roll');

// ── Coverage disclosure ───────────────────────────────────────────────
const disc = compute('ak-civ-r-12a-answer-to-complaint', '2026-05-01');
check('an Alaska computation succeeds', disc.ok, true);
check('coverage is present and incomplete', disc.coverage && disc.coverage.complete, false);
check('coverage direction is EARLY', disc.coverage && disc.coverage.direction, 'early');
check('coverage names the three omitted readings',
  !!disc.coverage && /MLK|Martin Luther King/.test(disc.coverage.detail) && /44\.12\.025/.test(disc.coverage.detail) &&
  /proclamation/i.test(disc.coverage.detail), true);

// ── The calendar ──────────────────────────────────────────────────────
const ak26 = calendars.ak['2026'].map(d => d.date);
check('six years, 2026-2031', Object.keys(calendars.ak), ['2026', '2027', '2028', '2029', '2030', '2031']);
check('11 legal holidays in 2026 (Alaska Day on Sunday is entered as its Monday)', ak26.length, 11);
check("SEWARD'S DAY is Monday 30 March 2026", ak26.includes('2026-03-30'), true);
check('JUNETEENTH is an Alaska legal holiday', ak26.includes('2026-06-19'), true);
check('ALASKA DAY 2026 is a Sunday, so Monday 19 October is the holiday (AS 44.12.020)',
  ak26.includes('2026-10-19') && !ak26.includes('2026-10-18'), true);
check('NO Saturday->Friday shift: Friday 3 July 2026 is not a holiday (AS 44.12.025 is employees only)',
  ak26.includes('2026-07-04') && !ak26.includes('2026-07-03'), true);
check('MLK DAY is NOT encoded (19 January 2026)', ak26.includes('2026-01-19'), false);
check('no Columbus Day (12 October 2026)', ak26.includes('2026-10-12'), false);
check('no calendar entry falls on a Sunday',
  cal.holiday_calendars.every(y => y.dates.every(d => new Date(d.date + 'T00:00:00Z').getUTCDay() !== 0)), true);
check('every entry carries a derivation',
  cal.holiday_calendars.every(y => y.dates.every(d => typeof d.derivation === 'string' && d.derivation.length > 10)), true);
check('the 2027 Independence Day Sunday shift lands on Monday 5 July',
  calendars.ak['2027'].map(d => d.date).includes('2027-07-05'), true);

// ── Computations, every date derived by hand first ─────────────────────
// 29 Jun + 20 = Sun 19 Jul -> Mon 20 Jul.
check('answer: 20 days, Sunday rolls to Monday',
  dateOf(compute('ak-civ-r-12a-answer-to-complaint', '2026-06-29')), '2026-07-20');
// 28 Sep + 20 = Sun 18 Oct (Alaska Day) -> Mon 19 Oct is the Sunday-shift holiday -> Tue 20 Oct.
check('answer: lands on Alaska Day Sunday, skips the shifted Monday too',
  dateOf(compute('ak-civ-r-12a-answer-to-complaint', '2026-09-28')), '2026-10-20');
// 4(h): a summons by mail earns nothing.
check('answer: MAIL service of process adds NOTHING (Rule 6(c) excludes 4(h))',
  dateOf(compute('ak-civ-r-12a-answer-to-complaint', '2026-06-29', { service_method: 'mail' })), '2026-07-20');
// 3 Jun + 30 = Fri 3 Jul. Not a holiday in Alaska computation.
check('interrogatories: Friday 3 July 2026 does NOT roll (no Saturday shift)',
  dateOf(compute('ak-civ-r-33a3-interrogatory-answers', '2026-06-03')), '2026-07-03');
// 3 Jun + 30 + 3 = Mon 6 Jul.
check('interrogatories by MAIL: 30 + 3 = Monday 6 July',
  dateOf(compute('ak-civ-r-33a3-interrogatory-answers', '2026-06-03', { service_method: 'mail' })), '2026-07-06');
check('interrogatories by EMAIL: no days added',
  dateOf(compute('ak-civ-r-33a3-interrogatory-answers', '2026-06-03', { service_method: 'email' })), '2026-07-03');
// 4 Jun + 30 = Sat 4 Jul -> Sun 5 -> Mon 6 Jul.
check('admissions: Independence Day Saturday rolls forward to Monday',
  dateOf(compute('ak-civ-r-36a-admission-response', '2026-06-04')), '2026-07-06');
// 9 Jan + 10 = Mon 19 Jan (MLK) -- stays, by the EARLY reading.
check('opposition: lands on MLK Day and does NOT roll (the disclosed early reading)',
  dateOf(compute('ak-civ-r-77c2-opposition-to-motion', '2026-01-09')), '2026-01-19');
// 20 Mar + 10 = Mon 30 Mar (Seward's Day) -> Tue 31 Mar.
check("opposition: Seward's Day rolls the deadline",
  dateOf(compute('ak-civ-r-77c2-opposition-to-motion', '2026-03-20')), '2026-03-31');
// 1 May + 15 = Sat 16 May -> Mon 18 May.
check('dispositive opposition: 15 days',
  dateOf(compute('ak-civ-r-77c2b-opposition-to-dispositive-motion', '2026-05-01')), '2026-05-18');
// Fri 9 Oct, 5 days under 7: Mon 12 (1, no Columbus Day), 13, 14, 15, Fri 16 (5).
check('reply: 5 days excludes intermediate weekends -- Friday to Friday',
  dateOf(compute('ak-civ-r-77d-reply', '2026-10-09')), '2026-10-16');
// Wed 14 Oct: 15 (1), 16 (2), skip 17-18, skip Mon 19 (holiday), 20 (3), 21 (4), 22 (5).
check('reply: the Alaska Day Monday is excluded as an intermediate holiday',
  dateOf(compute('ak-civ-r-77d-reply', '2026-10-14')), '2026-10-22');
// Fri 9 Oct by mail: base 5 (under 7 on the BASE count) -> Fri 16; +3 calendar = Mon 19 (holiday) -> Tue 20.
check('reply by MAIL: short-period test on the base 5, then +3 added, then one rollover',
  dateOf(compute('ak-civ-r-77d-reply', '2026-10-09', { service_method: 'mail' })), '2026-10-20');
// 26 Feb + 30 = Sat 28 Mar -> Sun 29 -> Mon 30 (Seward's) -> Tue 31 Mar.
check("notice of appeal: weekend then Seward's Day",
  dateOf(compute('ak-app-r-204a1-notice-of-appeal', '2026-02-26')), '2026-03-31');
check('notice of appeal: a MAILED judgment adds NOTHING (disclosed early reading)',
  dateOf(compute('ak-app-r-204a1-notice-of-appeal', '2026-02-26', { service_method: 'mail' })), '2026-03-31');
// 13 Nov + 10 = Mon 23 Nov.
check('new trial: 10 days from the certificate date',
  dateOf(compute('ak-civ-r-59b-motion-for-new-trial', '2026-11-13')), '2026-11-23');
// 6 Nov + 20 = Thu 26 Nov (Thanksgiving) -> Fri 27 Nov (NOT a holiday in Alaska).
check('cross-claim answer: Thanksgiving rolls one day, the Friday after is a working day',
  dateOf(compute('ak-civ-r-12a-answer-to-crossclaim', '2026-11-06')), '2026-11-27');

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
