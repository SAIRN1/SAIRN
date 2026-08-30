// Wisconsin deadline rows -- isolated verification against the REAL engine and
// the REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Wisconsin is the first jurisdiction whose CALENDAR is the finding. Wis. Stat.
// 801.15(1)(b) rolls the last day on "a day the clerk of courts office is
// closed" -- a courthouse-closure test -- while excluding intermediate days on
// the statutory holiday LIST in 801.15(1)(a). Two tests, one subsection, and no
// single calendar can serve both. Wisconsin's clerks are COUNTY officers and
// the court system's own 2026 schedule shows they diverge, so the calendar
// carries only the STATEWIDE INTERSECTION of actual closures: three days.
//
// The cases below target exactly that, plus:
//   - the 45-day INSURER-OR-TORT branch, which turns on what the claim is
//     about and is the most commonly hit branch in practice;
//   - "MAY" vs "SHALL NOT BE REQUIRED" across 804.08/804.09 and 804.11;
//   - the 5 p.m. boundary, including 17:00 exactly and a 02:00 transmission,
//     which a naive "after 5 p.m." reading gets wrong;
//   - the deliberate UNDER-exclusion, asserted on Juneteenth: a day the
//     statutory list would exclude and this calendar does not, so the result is
//     EARLIER than a list-based engine would report and never later.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_wisconsin.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_wisconsin.json'), 'utf8'));

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
    jurisdiction: 'wi', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── The seed's own shape ──────────────────────────────────────────────────
check('12 rules seeded', seed.rules.length, 12);
check('every rule is Wisconsin civil litigation on wi_801_15',
  seed.rules.filter(r => r.jurisdiction === 'wi' && r.domain === 'civil-litigation'
    && r.computation === 'wi_801_15').length, 12);
check('every rule cites the Legislature\'s own certified PDF and a verbatim quote',
  seed.rules.filter(r => /^https:\/\/docs\.legis\.wisconsin\.gov\/statutes\/statutes\/\d+\.pdf$/.test(r.authority.url)
    && r.authority.quote && r.authority.quote.length > 40).length, 12);

// ── THE CALENDAR IS THE FINDING ──────────────────────────────────────────
const d2026 = Object.fromEntries(calendars.wi['2026'].map(d => [d.date, d.name]));
check('THREE dates, the statewide intersection of actual closures',
  Object.keys(d2026).sort(), ['2026-01-01', '2026-05-25', '2026-11-26']);
// Every one of these IS on the statutory 801.15(1)(a) list and is NOT here,
// because at least one county's clerk is open on it. Including them would roll
// deadlines in those counties -- LATER than the statute allows.
check('Juneteenth, Columbus Day, Christmas and Good Friday are all ABSENT',
  ['2026-06-19', '2026-10-12', '2026-12-25', '2026-04-03'].map(d => !!d2026[d]),
  [false, false, false, false]);

// ── The standards ─────────────────────────────────────────────────────────
const std = engine.COMPUTATION_STANDARDS.wi_801_15;
check('wi_801_15 exists, defers to frcp_6a, and excludes under ELEVEN days',
  [!!std, std && std.impl, std && std.short_period_exclusion_days], [true, 'frcp_6a', 11]);
const ext = engine.SERVICE_EXTENSION_STANDARDS.wi_801_15_5;
check('wi_801_15_5 lengthens the period rather than following its expiry',
  ext.sequence, 'add_to_period_then_roll');
check('mail is a flat three days and does not touch the clock',
  ext.amount('mail', {}), { add: 3, unit: 'calendar_days' });
// THE BOUNDARY. "between 5 p.m. and midnight" -- 17:00 exactly is read as
// OUTSIDE, because reading it inside would add a day and report LATE.
check('16:59 -> 0, 17:00 -> 0, 17:01 -> 1, 23:59 -> 1',
  ['16:59', '17:00', '17:01', '23:59'].map(t => ext.amount('electronic_mail', { service_time: t }).add),
  [0, 0, 1, 1]);
// And the case a naive "after 5 p.m." implementation gets wrong.
check('02:00 is NOT between 5 p.m. and midnight, so it adds NOTHING',
  ext.amount('facsimile', { service_time: '02:00' }).add, 0);
check('a missing service_time REFUSES rather than guessing between 0 and 1',
  Object.keys(ext.amount('electronic_mail', {})), ['refuse']);

// ── The 20-day answer, and the extension it does NOT take ────────────────
// 2026-05-01 Fri + 20 = 2026-05-21 Thu. No rollover.
check('802.06(1)(a) answer: 20 days',
  dateOf(compute('wi-802-06-1a-answer-20-days', '2026-05-01')), '2026-05-21');
check('and it takes NO three days on mail -- the 801.15(5) question is unread',
  dateOf(compute('wi-802-06-1a-answer-20-days', '2026-05-01', { service_method: 'mail' })),
  '2026-05-21');

// ── The 45-day branches ──────────────────────────────────────────────────
// 2026-05-01 + 45 = 2026-06-15 Mon.
check('the INSURER-OR-TORT branch is 45 days, not 20',
  dateOf(compute('wi-802-06-1a-answer-45-days-insurer-or-tort', '2026-05-01')), '2026-06-15');
check('the state branch is 45 days too',
  dateOf(compute('wi-802-06-1a-answer-45-days-state', '2026-05-01')), '2026-06-15');
// The gap between the default row and the tort row is 25 days, and a caller who
// picks the wrong one is told 05-21 when the answer is really due 06-15.
check('the default row and the tort row genuinely differ',
  dateOf(compute('wi-802-06-1a-answer-20-days', '2026-05-01'))
    !== dateOf(compute('wi-802-06-1a-answer-45-days-insurer-or-tort', '2026-05-01')), true);

// ── The extension where it DOES apply, through a holiday ─────────────────
// Cross-claim answer, same base: 2026-05-21 Thu, + 3 = 05-24 SUNDAY, roll to
// Mon 05-25 which is MEMORIAL DAY -- one of the three intersection days -- so
// it rolls again to Tue 05-26.
check('cross-claim answer + mail rolls through Sunday AND Memorial Day',
  dateOf(compute('wi-802-06-1a-answer-to-crossclaim', '2026-05-01', { service_method: 'mail' })),
  '2026-05-26');
check('e-mail at 17:01 adds one day; at 17:00 it adds none',
  ['17:01', '17:00'].map(t => dateOf(compute('wi-802-06-1a-answer-to-crossclaim', '2026-05-01',
    { service_method: 'electronic_mail', service_time: t }))),
  ['2026-05-22', '2026-05-21']);

// ── The guardian ad litem row: a trigger that is not service at all ──────
check('guardian ad litem: 20 days from APPOINTMENT, and no extension on mail',
  [dateOf(compute('wi-802-06-1a-guardian-ad-litem-answer', '2026-05-01')),
   dateOf(compute('wi-802-06-1a-guardian-ad-litem-answer', '2026-05-01', { service_method: 'mail' }))],
  ['2026-05-21', '2026-05-21']);

// ── THE ELEVEN-DAY EXCLUSION, and the deliberate UNDER-exclusion ─────────
// 10-day limb from 2026-05-11 Mon, excluding weekends and the three closure
// days: Tue 12 .. Fri 15, [16/17], Mon 18 .. Fri 22, [23/24, MEMORIAL 25],
// Tue 26.
check('10-day limb excludes weekends AND Memorial Day',
  dateOf(compute('wi-802-06-1a-responsive-pleading-after-more-definite-statement', '2026-05-11')),
  '2026-05-26');
// THE UNDER-EXCLUSION, ASSERTED. From 2026-06-11 Thu: Fri 12, [13/14], Mon 15
// .. Fri 19, [20/21], Mon 22 .. Thu 25. JUNETEENTH (Fri 06-19) IS COUNTED,
// because at least one county is open on it and it is not in this calendar. A
// statutory-list engine would exclude it and answer 06-26 -- one day LATER.
check('JUNETEENTH IS COUNTED, not excluded -- the calendar is deliberately narrow',
  dateOf(compute('wi-802-06-1a-responsive-pleading-after-more-definite-statement', '2026-06-11')),
  '2026-06-25');
// The sibling limb runs from NOTICE, so it takes no extension.
check('the notice-triggered sibling takes nothing on mail',
  dateOf(compute('wi-802-06-1a-responsive-pleading-after-motion-denied', '2026-05-11',
    { service_method: 'mail' })), '2026-05-26');

// ── "MAY" vs "SHALL NOT BE REQUIRED" ─────────────────────────────────────
// 2026-05-01 + 30 = 2026-05-31 SUNDAY -> Mon 2026-06-01 (not a closure day).
check('804.08 interrogatories: a plain 30 days, the 45 is an ELECTION',
  dateOf(compute('wi-804-08-1b-interrogatory-answers', '2026-05-01')), '2026-06-01');
check('804.09 production: the same',
  dateOf(compute('wi-804-09-2b1-production-response', '2026-05-01')), '2026-06-01');
{
  // 804.11 IS a floor: request 05-01 (+30 -> 06-01), summons 04-20 (+45 -> 06-04).
  const dates = {
    service_of_request_for_admission: '2026-05-01',
    service_of_summons_and_complaint_for_admission: '2026-04-20'
  };
  check('804.11 admissions IS a floor -- the 45-day limb wins',
    dateOf(compute('wi-804-11-1b-admission-response-defendant-later-of', '2026-05-01',
      { trigger_dates: dates })), '2026-06-04');
}

// ── The coverage disclosure ──────────────────────────────────────────────
{
  const r = compute('wi-802-06-1a-answer-20-days', '2026-05-01');
  check('Wisconsin discloses the closure-vs-list split, direction EARLY',
    [r.ok, r.coverage && r.coverage.direction], [true, 'early']);
  check('and the disclosure names the county divergence in numbers',
    [/clerk/i.test(r.coverage.detail), /67 of 72|intersection/i.test(r.coverage.detail)],
    [true, true]);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
