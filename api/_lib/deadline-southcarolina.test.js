// South Carolina deadline rows -- isolated verification against the REAL engine
// and the REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Every expected date below was worked out BY HAND from the rule text and the
// derived state-union-federal holiday list BEFORE the engine was run, and the
// cases target what actually differs in South Carolina:
//
//   - THE FIRST STATE-PLUS-FEDERAL UNION. SCRCP 6(a) rolls on "a State OR
//     Federal holiday", so JUNETEENTH and COLUMBUS DAY count even though
//     neither is in S.C. Code 53-5-10. Both asserted as shape AND arithmetic,
//     because a state-only calendar would report EARLY.
//   - FIVE DAYS FOR MAIL, not three, and it reaches SERVICE UPON A STATUTORY
//     AGENT, which no other seeded rule does.
//   - E-MAIL DOES NOT QUALIFY, deliberately. The question is unresolved on the
//     primary sources, and adding the days would compute LATE if wrong.
//   - THE "MAY" / "SHALL NOT BE REQUIRED" SPLIT. Rules 33 and 34 give a
//     defendant a PERMISSIVE 45-day alternative (own plain row); Rule 36 gives
//     a MANDATORY 45-day floor (resolve_periods). The wordings are close
//     enough to read across and mean opposite things.
//   - A THREE-DAY CHRISTMAS BLOCK that COLLIDES under the shift in half the
//     years -- and in 2027 Christmas Day itself is not an emitted date.
//
// Run: node api/_lib/deadline-southcarolina.test.js
'use strict';

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_southcarolina.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_southcarolina.json'), 'utf8'));

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
    jurisdiction: 'sc', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── The seed's own shape ──────────────────────────────────────────────────
check('9 rules seeded', seed.rules.length, 9);
check('all rows are jurisdiction sc', seed.rules.every(r => r.jurisdiction === 'sc'), true);
check('every row uses sc_rcp_6', seed.rules.every(r => r.computation === 'sc_rcp_6'), true);
check('every row cites a real quote and url',
  seed.rules.every(r => r.authority.quote && /^https?:\/\//.test(r.authority.url)), true);

// THE "MAY" / "SHALL NOT BE REQUIRED" SPLIT, as shape. Rules 33 and 34's
// alternatives are PLAIN rows; only Rule 36's floor is a resolve_periods.
check('the 33 and 34 defendant alternatives are PLAIN rows, not floors',
  seed.rules.filter(r => /defendant-45$/.test(r.rule_id))
    .every(r => typeof r.trigger_event === 'string'), true);
check('exactly one resolve_periods row, and it is Rule 36\'s mandatory floor',
  seed.rules.filter(r => typeof r.trigger_event !== 'string').map(r => r.rule_id),
  ['sc-rcp-36-admission-response-defendant-later-of']);
// The three process-triggered rows take no extension; the rest do.
check('the rows running from PROCESS carry no extension',
  seed.rules.filter(r => !r.service_extension).map(r => r.rule_id).sort(),
  ['sc-rcp-12a-answer-to-complaint',
   'sc-rcp-33-interrogatory-answers-defendant-45',
   'sc-rcp-34-production-response-defendant-45',
   'sc-rcp-36-admission-response-defendant-later-of']);
check('every extension row is FIVE days, never three',
  [...new Set(seed.rules.filter(r => r.service_extension).map(r => r.service_extension.add))], [5]);
check('and none of them lists e-mail',
  seed.rules.filter(r => r.service_extension)
    .some(r => r.service_extension.applies_when.includes('email')), false);
// The two 45-day rows describe the same real-world event but must not share a
// trigger, or the engine sees two rules in force at once.
check('the two 45-day alternatives use DISTINCT trigger names',
  seed.rules.filter(r => /defendant-45$/.test(r.rule_id)).map(r => r.trigger_event),
  ['service_of_summons_and_complaint_for_interrogatories',
   'service_of_summons_and_complaint_for_production']);

// ── The standards ─────────────────────────────────────────────────────────
const std = engine.COMPUTATION_STANDARDS.sc_rcp_6;
check('sc_rcp_6 is registered', !!std, true);
check('the threshold is SEVEN', std.short_period_exclusion_days, 7);
check('backward is blank -- Rule 6(a) has no backward provision', std.rollover_suffix_backward, '');

const ext = engine.SERVICE_EXTENSION_STANDARDS.sc_rcp_6_e;
check('sc_rcp_6_e is registered', !!ext, true);
check('it LENGTHENS the period', ext.sequence, 'add_to_period_then_roll');
check('mail and STATUTORY AGENT qualify -- the latter unique to South Carolina',
  ['mail', 'statutory_agent'].map(m => ext.qualifies(m)), [true, true]);
// The deliberate default. If this ever flips, the e-mail question was resolved
// -- go and read why before accepting it.
check('E-MAIL DOES NOT QUALIFY -- unresolved on the primary sources, and adding it would be LATE',
  ['email', 'electronic', 'facsimile'].map(m => ext.qualifies(m)), [false, false, false]);

// ── The calendar: the union, and the Christmas block ──────────────────────
check('the calendar covers 2026-2031',
  Object.keys(calendars.sc).sort(), ['2026', '2027', '2028', '2029', '2030', '2031']);
const d2026 = Object.fromEntries(calendars.sc['2026'].map(d => [d.date, d.name]));
// THE UNION. Neither of these is in S.C. Code 53-5-10.
check('JUNETEENTH is present -- federal only', d2026['2026-06-19'], 'Juneteenth National Independence Day');
check('COLUMBUS DAY is present -- federal only', d2026['2026-10-12'], 'Columbus Day');
// The two state-only days no other seeded jurisdiction has.
check('Confederate Memorial Day, 10 May 2026 being a Sunday, is observed the 11th',
  [d2026['2026-05-11'], d2026['2026-05-10']], ['Confederate Memorial Day', undefined]);
check('the day after Thanksgiving is in the statute here',
  d2026['2026-11-27'], 'Day after Thanksgiving');
// THE COLLISION. 26 December 2026 is a Saturday, so its observance merges onto
// the 25th, which is already Christmas Day.
check('2026: the three-day block collapses to two observed dates',
  [d2026['2026-12-24'], d2026['2026-12-25'], d2026['2026-12-26']],
  ['Christmas Eve', 'Christmas Day', undefined]);
{
  const d2027 = Object.fromEntries(calendars.sc['2027'].map(d => [d.date, d.name]));
  // 2027: 24 Fri stays, 25 Sat merges BACK onto the 24th, 26 Sun moves FORWARD
  // to Monday the 27th. Christmas Day itself is not an emitted date.
  check('2027: Christmas Day itself is NOT an emitted date',
    [d2027['2027-12-24'], d2027['2027-12-25'], d2027['2027-12-27']],
    ['Christmas Eve', undefined, 'Day after Christmas']);
}
check('no observed date is ever duplicated',
  Object.keys(calendars.sc).every(y =>
    calendars.sc[y].length === new Set(calendars.sc[y].map(d => d.date)).size), true);

// ── Arithmetic ────────────────────────────────────────────────────────────
check('answer to complaint: 2026-06-01 + 30 = 2026-07-01',
  dateOf(compute('sc-rcp-12a-answer-to-complaint', '2026-06-01')), '2026-07-01');
check('crossclaim answer: 30 days', dateOf(compute('sc-rcp-12a-answer-to-crossclaim', '2026-06-01')), '2026-07-01');
check('reply to counterclaim: 30 days', dateOf(compute('sc-rcp-12a-reply-to-counterclaim', '2026-06-01')), '2026-07-01');
check('interrogatories: 30 days', dateOf(compute('sc-rcp-33-interrogatory-answers', '2026-06-01')), '2026-07-01');
check('production: 30 days', dateOf(compute('sc-rcp-34-production-response', '2026-06-01')), '2026-07-01');
check('admissions: 30 days', dateOf(compute('sc-rcp-36-admission-response', '2026-06-01')), '2026-07-01');
check('the defendant 45-day alternative is a different clock entirely',
  dateOf(compute('sc-rcp-33-interrogatory-answers-defendant-45', '2026-06-01')), '2026-07-16');

// THE UNION, AS ARITHMETIC. These are the cases that fail if the federal half
// is ever dropped from the calendar.
check('landing on JUNETEENTH rolls -- and it is federal-only',
  dateOf(compute('sc-rcp-12a-answer-to-complaint', '2026-05-20')), '2026-06-22');
check('landing on COLUMBUS DAY rolls -- also federal-only',
  dateOf(compute('sc-rcp-33-interrogatory-answers', '2026-09-12')), '2026-10-13');
check('landing on the observed Confederate Memorial Day rolls',
  dateOf(compute('sc-rcp-12a-answer-to-complaint', '2026-04-11')), '2026-05-12');
check('landing in the Christmas block rolls clear of all of it',
  dateOf(compute('sc-rcp-12a-answer-to-complaint', '2026-11-24')), '2026-12-28');
check('and in 2027, where the block merges, it still clears',
  dateOf(compute('sc-rcp-12a-answer-to-complaint', '2027-11-24')), '2027-12-28');

// ── The extension ─────────────────────────────────────────────────────────
check('discovery + mail: FIVE days added to the period, landing Mon 6 Jul',
  dateOf(compute('sc-rcp-33-interrogatory-answers', '2026-06-01', { service_method: 'mail' })), '2026-07-06');
check('STATUTORY AGENT qualifies too -- unique to South Carolina',
  dateOf(compute('sc-rcp-34-production-response', '2026-06-01', { service_method: 'statutory_agent' })), '2026-07-06');
check('e-mail adds NOTHING, and says so distinctly',
  [dateOf(compute('sc-rcp-33-interrogatory-answers', '2026-06-01', { service_method: 'email' })),
   compute('sc-rcp-33-interrogatory-answers', '2026-06-01', { service_method: 'email' }).service_extension.state],
  ['2026-07-01', 'not_qualifying']);
check('supplying mail on the answer-to-complaint row adds nothing -- process, not a paper',
  dateOf(compute('sc-rcp-12a-answer-to-complaint', '2026-06-01', { service_method: 'mail' })), '2026-07-01');

// ── Rule 36's later-of ────────────────────────────────────────────────────
{
  const both = engine.computeDeadline({
    jurisdiction: 'sc', domain: 'civil-litigation',
    trigger_event: 'southcarolina_admission_defendant_later_of',
    trigger_dates: {
      service_of_request_for_admission_on_defendant: '2026-06-01',
      service_of_summons_and_complaint_for_admission: '2026-05-25'
    },
    rules: seed.rules, calendars: calendars, as_of: '2026-06-01'
  });
  // 30 from the request = 1 Jul; 45 from the summons = 9 Jul. The LONGER
  // PERIOD wins from the EARLIER trigger -- the case a plain later_of misses.
  check('admissions later-of: the 45-day limb wins from the EARLIER trigger date',
    dateOf(both), '2026-07-09');

  const one = engine.computeDeadline({
    jurisdiction: 'sc', domain: 'civil-litigation',
    trigger_event: 'southcarolina_admission_defendant_later_of',
    trigger_date: '2026-06-01', rules: seed.rules, calendars: calendars, as_of: '2026-06-01'
  });
  check('and it REFUSES on a partial set', one.ok === false && /INCOMPLETE/.test(one.code || ''), true);
}

// ── The traps ─────────────────────────────────────────────────────────────
check('a pre-1985 trigger refuses on effective_from',
  dateOf(compute('sc-rcp-12a-answer-to-complaint', '1984-06-01')), 'REFUSED:NO_RULE_IN_FORCE');
check('a 2032 trigger refuses -- the calendar stops at 2031',
  dateOf(compute('sc-rcp-33-interrogatory-answers', '2032-03-01')), 'REFUSED:NOT_PROVISIONED');

// ── Nothing else moved ────────────────────────────────────────────────────
check('South Carolina declares NO coverage entry',
  Object.keys(engine.JURISDICTION_COVERAGE).sort(), ['al', 'ar', 'id', 'ks', 'ma', 'md', 'mn', 'mo', 'ms', 'nm', 'va', 'wi']);
{
  // Three neighbours, three different mail amounts, one engine. If any two ever
  // converge, one of them took the other's number.
  check('SC adds 5, Oregon 3, Oklahoma 3 -- read from three different rules',
    [engine.SERVICE_EXTENSION_STANDARDS.sc_rcp_6_e.qualifies('mail'),
     engine.SERVICE_EXTENSION_STANDARDS.or_orcp_10_b.qualifies('email'),
     engine.SERVICE_EXTENSION_STANDARDS.ok_12_2006_d.qualifies('email')],
    [true, true, false]);
  const okSeed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_oklahoma.json'), 'utf8'));
  const okCal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_oklahoma.json'), 'utf8'));
  const oc = {};
  for (const row of okCal.holiday_calendars) {
    oc[row.jurisdiction] = oc[row.jurisdiction] || {};
    oc[row.jurisdiction][String(row.year)] = row.dates;
  }
  // Same trigger date, same 30-day period, opposite answers on Columbus Day:
  // South Carolina counts it (federal union), Oklahoma does not.
  const ok = engine.computeDeadline({
    jurisdiction: 'ok', domain: 'civil-litigation', trigger_event: 'service_of_interrogatories',
    trigger_date: '2026-09-12', rules: okSeed.rules, calendars: oc, as_of: '2026-09-12'
  });
  check('Oklahoma does NOT roll off Columbus Day where South Carolina does',
    [ok.ok, ok.due_date], [true, '2026-10-12']);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
