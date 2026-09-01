// Alabama deadline rows -- isolated verification against the REAL engine and
// the REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Every expected date was worked out BY HAND from the rule text and the derived
// 2026 union calendar BEFORE the engine was run, and the cases target the four
// things the gate said would be wrong if inherited from a neighbour:
//
//   - THE SERVICE ORDER IS FEDERAL after-expiry: "3 days are added AFTER THE
//     PERIOD WOULD OTHERWISE EXPIRE". Asserted against the date the
//     period-lengthening order would have produced, so the test fails if the
//     sequence is ever copied from the recent neighbours.
//   - THE EXCLUSION IS ELEVEN DAYS, not seven and not Arkansas's fourteen.
//   - THE HOLIDAY UNION carries two days NO other jurisdiction on this platform
//     has: CONFEDERATE MEMORIAL DAY (fourth Monday in April) and JEFFERSON
//     DAVIS' BIRTHDAY (first Monday in June). Neither is federal and neither is
//     in Rule 6(a)(4)(A)'s own eleven -- both reach deadlines only through
//     6(a)(4)(B). Both asserted as arithmetic.
//   - "MAY" vs "SHALL NOT BE REQUIRED". Rules 33 and 34 give the defendant an
//     ELECTION to take 45 days; only Rule 36 imposes a FLOOR. Asserted by
//     showing 33 and 34 do NOT extend to 45 on the same facts where 36 does.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_alabama.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_alabama.json'), 'utf8'));

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
    jurisdiction: 'al', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── The seed's own shape ──────────────────────────────────────────────────
check('11 rules seeded', seed.rules.length, 11);
check('every rule is Alabama civil litigation on al_rcp_6',
  seed.rules.filter(r => r.jurisdiction === 'al' && r.domain === 'civil-litigation'
    && r.computation === 'al_rcp_6').length, 11);
check('every rule cites its own official PDF and a verbatim quote',
  seed.rules.filter(r => /^https:\/\/judicial\.alabama\.gov\/docs\/library\/rules\/cv\d+\.pdf$/.test(r.authority.url)
    && r.authority.quote && r.authority.quote.length > 40).length, 11);
// Per-rule effective dates, read from each PDF's own amendment line. Rule 6 is
// the freshest text on the platform; Rule 36's dates from 1995.
check('effective dates are PER RULE, not one collection date',
  [...new Set(seed.rules.map(r => r.effective_from))].sort(),
  ['1995-10-01', '2009-11-18', '2010-02-01', '2012-11-28', '2026-04-09']);

// ── The standards ─────────────────────────────────────────────────────────
const std = engine.COMPUTATION_STANDARDS.al_rcp_6;
check('al_rcp_6 exists and defers to the FRCP 6(a) implementation',
  [!!std, std && std.impl], [true, 'frcp_6a']);
check('THE SHORT-PERIOD EXCLUSION IS ELEVEN', std.short_period_exclusion_days, 11);
const ext = engine.SERVICE_EXTENSION_STANDARDS.al_rcp_6_d;
check('THE ORDER IS FEDERAL after-expiry, not period-lengthening',
  ext.sequence, 'roll_then_add_then_roll');
check('mail and the e-filing system qualify; personal service does not',
  ['mail', 'efiling_service_provider', 'personal'].map(m => ext.qualifies(m)),
  [true, true, false]);

// ── The union, and the two days nothing else on this platform has ─────────
const d2026 = Object.fromEntries(calendars.al['2026'].map(d => [d.date, d.name]));
check('thirteen dates in the 2026 union', calendars.al['2026'].length, 13);
check('CONFEDERATE MEMORIAL DAY and JEFFERSON DAVIS BIRTHDAY are both present',
  [!!d2026['2026-04-27'], !!d2026['2026-06-01']], [true, true]);
check('4 July 2026 is a SATURDAY so the holiday moved BACK to Friday 07-03',
  [!!d2026['2026-07-03'], !!d2026['2026-07-04']], [true, false]);

// ── The answer row: 30 days, no extension, and it lands on a state-only day
// 2026-05-01 Fri + 30 = 2026-05-31 SUNDAY -> Mon 06-01, which is JEFFERSON
// DAVIS' BIRTHDAY -> Tue 2026-06-02. Two consecutive rollovers, the second off
// a day that exists on no other calendar here.
check('Rule 12(a) answer: 30 days, Sunday then Jefferson Davis rollover',
  dateOf(compute('al-arcp-12a-answer-after-service', '2026-05-01')), '2026-06-02');
check('THE ANSWER TAKES NO THREE DAYS ON MAIL -- 6(d) reaches Rule 5(b)(2) only',
  dateOf(compute('al-arcp-12a-answer-after-service', '2026-05-01', { service_method: 'mail' })),
  '2026-06-02');

// ── THE FEDERAL ORDER, asserted against the answer the other order gives ──
// Cross-claim answer, same base period. Unrolled last day 2026-05-31 Sun.
//   FEDERAL after-expiry: roll first -> 06-01 holiday -> 06-02 Tue; add 3 ->
//     06-05 Fri; roll -> 06-05.
//   Period-lengthening would instead add 3 to 05-31 -> 06-03 Wed and stop.
// The two differ, which is the whole point of reading 6(d)'s own words.
check('cross-claim answer takes the three days in the FEDERAL order',
  dateOf(compute('al-arcp-12a-answer-to-crossclaim', '2026-05-01', { service_method: 'mail' })),
  '2026-06-05');
check('and the period-lengthening answer, 2026-06-03, is NOT what it returns',
  dateOf(compute('al-arcp-12a-answer-to-crossclaim', '2026-05-01', { service_method: 'mail' })) !== '2026-06-03',
  true);
check('e-filing-system service gets the same three days as mail',
  dateOf(compute('al-arcp-12a-answer-to-crossclaim', '2026-05-01', { service_method: 'efiling_service_provider' })),
  '2026-06-05');

// ── CONFEDERATE MEMORIAL DAY, as arithmetic ──────────────────────────────
// 2026-03-28 + 30 = 2026-04-27, the fourth Monday in April. Not federal, not in
// the rule's own eleven -- a calendar built from either alone lands on 04-27.
check('rolls off CONFEDERATE MEMORIAL DAY (state only, via 6(a)(4)(B))',
  dateOf(compute('al-arcp-12a-answer-after-service', '2026-03-28')), '2026-04-28');
// 2026-06-03 + 30 = 2026-07-03, the observed Fourth -> Mon 07-06.
check('rolls off the OBSERVED Fourth of July, shifted BACK to Friday',
  dateOf(compute('al-arcp-12a-answer-after-service', '2026-06-03')), '2026-07-06');

// ── THE ELEVEN-DAY EXCLUSION, as arithmetic ──────────────────────────────
// 10-day limb from 2026-05-20 Wed, counting only days that are not Saturday,
// Sunday or a legal holiday:
//   Thu 21, Fri 22, [23/24, MEMORIAL 25], Tue 26, Wed 27, Thu 28, Fri 29,
//   [30/31, JEFFERSON DAVIS Jun 1], Tue Jun 2, Wed 3, Thu 4, Fri 5.
check('10-day limb EXCLUDES weekends, Memorial Day AND Jefferson Davis Birthday',
  dateOf(compute('al-arcp-12a2-responsive-pleading-after-more-definite-statement', '2026-05-20')),
  '2026-06-05');
// ...then the federal order adds three: 06-05 Fri is already fine, +3 = 06-08 Mon.
check('and then takes the three days on mail, federal order',
  dateOf(compute('al-arcp-12a2-responsive-pleading-after-more-definite-statement', '2026-05-20',
    { service_method: 'mail' })), '2026-06-08');
// The sibling limb runs from NOTICE, not service, so it takes nothing.
check('the notice-triggered sibling limb takes NO days on mail',
  dateOf(compute('al-arcp-12a1-responsive-pleading-after-motion-denied', '2026-05-20',
    { service_method: 'mail' })), '2026-06-05');

// ── The two backward rows ────────────────────────────────────────────────
// Hearing 2026-06-08 Mon. 5 days back, excluding: Fri 05, Thu 04, Wed 03,
// Tue 02, [JEFFERSON DAVIS Mon Jun 1], Fri May 29.
check('Rule 6(c)(1) motion: 5 days BACKWARD, exclusion applies',
  dateOf(compute('al-arcp-6c1-motion-and-notice-of-hearing', '2026-06-08')), '2026-05-29');
check('Rule 6(c)(2) opposing affidavit: 1 day BACKWARD',
  dateOf(compute('al-arcp-6c2-opposing-affidavit', '2026-06-08')), '2026-06-05');

// ── "MAY" vs "SHALL NOT BE REQUIRED" ─────────────────────────────────────
// Same facts for all three: request served 2026-05-01, summons 2026-04-20.
// Rule 36's floor is mandatory, so it runs to 04-20 + 45 = 2026-06-04.
// Rules 33 and 34 give an ELECTION, so they stay on the plain 30 days and land
// where the answer row does -- 05-31 Sun, 06-01 holiday, 06-02 Tue.
{
  const dates = {
    service_of_request_for_admission: '2026-05-01',
    service_of_summons_and_complaint_for_admission: '2026-04-20'
  };
  check('Rule 36 IS a floor -- the 45-day limb wins',
    dateOf(compute('al-arcp-36a-admission-response-defendant-later-of', '2026-05-01',
      { trigger_dates: dates })), '2026-06-04');
}
check('Rule 33 is NOT a floor -- plain 30 days, no 45-day extension',
  dateOf(compute('al-arcp-33a-interrogatory-answers', '2026-05-01')), '2026-06-02');
check('Rule 34 is NOT a floor either',
  dateOf(compute('al-arcp-34b-production-response', '2026-05-01')), '2026-06-02');

// ── The coverage disclosure, including the one LATE-direction item ────────
{
  const r = compute('al-arcp-12a-answer-after-service', '2026-05-01');
  check('Alabama discloses its gaps on an ok result',
    [r.ok, r.coverage && r.coverage.direction], [true, 'late']);
  check('and the disclosure names Mardi Gras AND the stay-open provision whose direction is LATE',
    [/mardi gras/i.test(r.coverage.detail), /LATE/.test(r.coverage.summary + r.coverage.detail)],
    [true, true]);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
