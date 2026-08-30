// Kansas deadline rows -- isolated verification against the REAL engine and the
// REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Kansas puts civil procedure in the STATUTE rather than in court rules, so the
// whole seed comes from one free official publisher. Three things here would be
// wrong if carried from any neighbour, and each is asserted as arithmetic:
//
//   - THERE IS NO SHORT-PERIOD EXCLUSION AT ALL. K.S.A. 60-206(a)(1)(B) counts
//     every day "including intermediate Saturdays, Sundays and legal holidays".
//     Asserted on the SEVEN-day backward row, which is exactly where a
//     Maryland-style threshold would change the answer.
//   - NO ELECTRONIC LIMB. 60-206(d) reaches mail and leaving-with-the-clerk
//     only, so e-mail gets nothing -- the opposite of Arkansas and Alabama.
//   - THE ORDER IS FEDERAL after-expiry, asserted against the date
//     period-lengthening would have produced on a base period that lands on a
//     Saturday before a holiday Monday.
//
// Plus the calendar's own oddity: TWO days for Thanksgiving.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_kansas.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_kansas.json'), 'utf8'));

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
    jurisdiction: 'ks', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── The seed's own shape ──────────────────────────────────────────────────
check('10 rules seeded', seed.rules.length, 10);
check('every rule is Kansas civil litigation on ks_60_206',
  seed.rules.filter(r => r.jurisdiction === 'ks' && r.domain === 'civil-litigation'
    && r.computation === 'ks_60_206').length, 10);
check('every rule cites the Revisor of Statutes and a verbatim quote',
  seed.rules.filter(r => /^https:\/\/www\.ksrevisor\.gov\/statutes\/chapters\/ch60\//.test(r.authority.url)
    && r.authority.quote && r.authority.quote.length > 40).length, 10);
// Effective dates are PRINTED by the publisher per section, not inferred.
check('effective dates are per section, three distinct values',
  [...new Set(seed.rules.map(r => r.effective_from))].sort(),
  ['2010-07-01', '2017-07-01', '2020-03-19']);
// No row is a resolve_periods: all three discovery statutes say "may".
check('NO row is a later-of -- all three discovery periods are ELECTIONS',
  seed.rules.filter(r => typeof r.trigger_event !== 'string').length, 0);

// ── The standard: the absence is the finding ─────────────────────────────
const std = engine.COMPUTATION_STANDARDS.ks_60_206;
check('ks_60_206 declares NO short-period exclusion at all',
  [!!std, std.impl, std.short_period_exclusion_days], [true, 'frcp_6a', undefined]);
const ext = engine.SERVICE_EXTENSION_STANDARDS.ks_60_206_d;
check('the order is FEDERAL after-expiry', ext.sequence, 'roll_then_add_then_roll');
check('mail and leaving-with-the-clerk qualify; e-mail and e-filing do NOT',
  ['mail', 'left_with_clerk', 'electronic_mail', 'efiling_service_provider'].map(m => ext.qualifies(m)),
  [true, true, false, false]);

// ── The calendar ─────────────────────────────────────────────────────────
const d2026 = Object.fromEntries(calendars.ks['2026'].map(d => [d.date, d.name]));
check('twelve dates', calendars.ks['2026'].length, 12);
check('TWO days for Thanksgiving',
  [!!d2026['2026-11-26'], !!d2026['2026-11-27']], [true, true]);
check('Independence Day is the published Friday, and 07-04 is absent',
  [!!d2026['2026-07-03'], !!d2026['2026-07-04']], [true, false]);

// ── The 21-day answer, and the extension it does not take ────────────────
// 2026-05-01 Fri + 21 = 2026-05-22 Fri. Straight count, no rollover.
check('60-212(a)(1)(A)(i) answer: 21 days',
  dateOf(compute('ks-60-212a1Ai-answer-21-days', '2026-05-01')), '2026-05-22');
check('E-MAIL ADDS NOTHING -- 60-206(d) has no electronic limb',
  dateOf(compute('ks-60-212a1Ai-answer-21-days', '2026-05-01', { service_method: 'electronic_mail' })),
  '2026-05-22');

// ── THE FEDERAL ORDER, against the answer the other order gives ──────────
// 2026-05-02 Sat + 21 = 2026-05-23, a SATURDAY.
//   FEDERAL after-expiry: roll first -> Mon 05-25 is MEMORIAL DAY -> Tue 05-26;
//     add 3 -> Fri 05-29; roll -> 05-29.
//   Period-lengthening would add 3 to 05-23 -> Tue 05-26 and stop.
check('mail takes the three days in the FEDERAL order, through Memorial Day',
  dateOf(compute('ks-60-212a1Ai-answer-21-days', '2026-05-02', { service_method: 'mail' })),
  '2026-05-29');
check('and the period-lengthening answer, 2026-05-26, is NOT what it returns',
  dateOf(compute('ks-60-212a1Ai-answer-21-days', '2026-05-02', { service_method: 'mail' })) !== '2026-05-26',
  true);
check('leaving with the clerk gets the same three days as mail',
  dateOf(compute('ks-60-212a1Ai-answer-21-days', '2026-05-02', { service_method: 'left_with_clerk' })),
  '2026-05-29');

// ── TWO DAYS OF THANKSGIVING, as arithmetic ──────────────────────────────
// 2026-11-05 Thu + 21 = 2026-11-26 THANKSGIVING -> 11-27 also a holiday ->
// Sat 28, Sun 29 -> Mon 2026-11-30. Four consecutive non-days.
check('rolls through BOTH Thanksgiving days and the weekend',
  dateOf(compute('ks-60-212a1Ai-answer-21-days', '2026-11-05')), '2026-11-30');

// ── NO SHORT-PERIOD EXCLUSION, asserted where it would show ──────────────
// 60-206(c)(1): 7 days BACKWARD from Mon 2026-06-08 = 2026-06-01 Mon, counting
// straight through the intervening weekend. A Maryland-style threshold would
// drop Sat 06 and Sun 07 and answer 2026-05-28 -- three days earlier, and on a
// backward period that means refusing to let a party serve when the statute
// still allows it.
check('the 7-day backward row counts the intervening weekend',
  dateOf(compute('ks-60-206c1-motion-and-notice-of-hearing', '2026-06-08')), '2026-06-01');
check('and the excluded answer, 2026-05-28, is NOT what it returns',
  dateOf(compute('ks-60-206c1-motion-and-notice-of-hearing', '2026-06-08')) !== '2026-05-28', true);
// The 14-day rows count straight through too.
// 2026-05-11 Mon + 14 = 2026-05-25, MEMORIAL DAY -> Tue 2026-05-26.
check('the 14-day limb counts straight through and then rolls off Memorial Day',
  dateOf(compute('ks-60-212a2B-responsive-pleading-after-more-definite-statement', '2026-05-11')),
  '2026-05-26');
// The notice-triggered sibling takes no extension.
check('the notice-triggered sibling takes nothing on mail',
  dateOf(compute('ks-60-212a2A-responsive-pleading-after-motion-denied', '2026-05-11',
    { service_method: 'mail' })), '2026-05-26');

// ── The one-day backward affidavit ───────────────────────────────────────
// Hearing Wed 2026-06-10, one day back = Tue 2026-06-09. No weekend involved.
check('60-206(c)(2) opposing affidavit: one day backward',
  dateOf(compute('ks-60-206c2-opposing-affidavit', '2026-06-10')), '2026-06-09');

// ── The three discovery rows are PLAIN, not floors ───────────────────────
// 2026-05-01 + 30 = 2026-05-31 SUNDAY -> Mon 2026-06-01, for all three.
check('all three discovery rows are a plain 30 days -- the 45 is an ELECTION',
  ['ks-60-233b2-interrogatory-answers', 'ks-60-234b2A-production-response',
   'ks-60-236a3-admission-response'].map(r => dateOf(compute(r, '2026-05-01'))),
  ['2026-06-01', '2026-06-01', '2026-06-01']);

// ── The coverage disclosure ──────────────────────────────────────────────
{
  const r = compute('ks-60-212a1Ai-answer-21-days', '2026-05-01');
  check('Kansas discloses the ad hoc-declaration gap, direction EARLY',
    [r.ok, r.coverage && r.coverage.direction], [true, 'early']);
  // The distinction from Wisconsin is the point of the entry, so it is pinned.
  check('and the disclosure explains why this is NOT the Wisconsin problem',
    [/Wisconsin/.test(r.coverage.detail), /half holiday/i.test(r.coverage.detail)], [true, true]);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
