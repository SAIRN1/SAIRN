// North Dakota deadline rows -- isolated verification against the REAL engine and
// the REAL seed/calendar JSON on disk (hank b63, 2026-10-28).
//
// REQUIREMENT: North Dakota deadlines are computed from North Dakota's OWN rule
//   text, holiday list and mail extension --
//   docs/sairnlaw-northdakota-deadline-seed-gate.md.
//
// Every expected date was derived BY HAND before the engine ran. What a copied
// neighbour would get wrong:
//
//   - BOTH SHIFTS ARE LAW HERE. N.D.R.Civ.P. 6(a)(6) names 1-03-02 AND 1-03-02.1
//     by number, so Friday 3 July 2026 IS a holiday -- the exact day Alaska's
//     employees-only shift does NOT roll.
//   - GOOD FRIDAY and MLK DAY are holidays; JUNETEENTH and COLUMBUS DAY are not.
//   - THE MAIL DAYS COME AFTER EXPIRY (6(e)(1), the federal order), so a period
//     that rolls off Good Friday to Monday then gains three days from Monday.
//   - NO SHORT-PERIOD EXCLUSION: a 7-day reply brief counts every day.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_northdakota.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_northdakota.json'), 'utf8'));

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
    jurisdiction: 'nd', domain: rule.domain, trigger_event: rule.trigger_event,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── Shape ─────────────────────────────────────────────────────────────
check('9 rules seeded', seed.rules.length, 9);
check('all rows are nd', seed.rules.every(r => r.jurisdiction === 'nd'), true);
check('only the appeal row uses App. R. 26(a)',
  seed.rules.filter(r => r.computation === 'nd_app_r_26a').map(r => r.rule_id), ['nd-app-r-4a1-notice-of-appeal']);
check('every other row uses Civ. R. 6(a)',
  seed.rules.filter(r => r.computation !== 'nd_app_r_26a').every(r => r.computation === 'nd_rcp_6a'), true);
check('every rule id is unique', new Set(seed.rules.map(r => r.rule_id)).size, seed.rules.length);
check('every row cites a quote, a url and retrieved_at',
  seed.rules.every(r => r.authority && r.authority.quote && r.authority.url && r.authority.retrieved_at), true);
check('exactly the Rule 4 answer and the 59(c) row carry NO extension',
  seed.rules.filter(r => !r.service_extension).map(r => r.rule_id),
  ['nd-rcp-12a1a-answer-to-complaint', 'nd-rcp-59c2-motion-for-new-trial']);

// ── Standards ─────────────────────────────────────────────────────────
const CS = engine.COMPUTATION_STANDARDS, XS = engine.SERVICE_EXTENSION_STANDARDS;
check('nd_rcp_6a is the federal count with NO short-period exclusion',
  [CS.nd_rcp_6a.impl, CS.nd_rcp_6a.short_period_exclusion_days], ['frcp_6a', undefined]);
check('nd_app_r_26a is the same', CS.nd_app_r_26a.impl, 'frcp_6a');
check('nd_rcp_6e: mail and third-party commercial carrier only',
  ['mail', 'third_party_commercial_carrier', 'email', 'efiling_service', 'electronic', 'personal']
    .filter(m => XS.nd_rcp_6e.qualifies(m)), ['mail', 'third_party_commercial_carrier']);
check('nd_rcp_6e adds AFTER expiry', XS.nd_rcp_6e.sequence, 'roll_then_add_then_roll');
check('nd_app_r_26c adds AFTER expiry, electronic earns nothing',
  [XS.nd_app_r_26c.sequence, XS.nd_app_r_26c.qualifies('electronic')], ['roll_then_add_then_roll', false]);

// ── Coverage ──────────────────────────────────────────────────────────
const disc = compute('nd-rcp-12a1a-answer-to-complaint', '2026-05-01');
check('a North Dakota computation succeeds', disc.ok, true);
check('coverage is incomplete and EARLY', [disc.coverage && disc.coverage.complete, disc.coverage && disc.coverage.direction],
  [false, 'early']);
check('coverage names Juneteenth, inaccessibility and the 45-day floor',
  !!disc.coverage && /JUNETEENTH/i.test(disc.coverage.detail) && /INACCESSIBLE/i.test(disc.coverage.detail) &&
  /45 days/.test(disc.coverage.detail), true);

// ── Calendar ──────────────────────────────────────────────────────────
const nd = y => calendars.nd[String(y)].map(d => d.date);
check('six years, 2026-2031', Object.keys(calendars.nd), ['2026', '2027', '2028', '2029', '2030', '2031']);
check('GOOD FRIDAY 2026 is 3 April (Easter 5 April)', nd(2026).includes('2026-04-03'), true);
check('MLK DAY 2026 is a holiday', nd(2026).includes('2026-01-19'), true);
check('SATURDAY SHIFT: Friday 3 July 2026 is a holiday', nd(2026).includes('2026-07-03'), true);
check('no Juneteenth, no Columbus Day',
  [nd(2026).includes('2026-06-19'), nd(2026).includes('2026-10-12')], [false, false]);
check('SUNDAY SHIFT: Independence Day 2027 is Monday 5 July', nd(2027).includes('2027-07-05'), true);
check('1 January 2028 is a Saturday, so Friday 31 December 2027 is the holiday', nd(2027).includes('2027-12-31'), true);
check('the Saturday shift reaches only the four named days -- no Friday before a Monday holiday',
  cal.holiday_calendars.every(y => y.dates.filter(d => /Saturday shift/.test(d.name))
    .every(d => /New Year|Independence|Veterans|Christmas/.test(d.name))), true);
check('no calendar entry falls on a Sunday',
  cal.holiday_calendars.every(y => y.dates.every(d => new Date(d.date + 'T00:00:00Z').getUTCDay() !== 0)), true);

// ── Computations, every date derived by hand first ─────────────────────
// Fri 12 Jun + 21 = Fri 3 Jul (holiday) -> Sat, Sun -> Mon 6 Jul.
check('answer: lands on the Saturday-shift Friday and rolls to Monday',
  dateOf(compute('nd-rcp-12a1a-answer-to-complaint', '2026-06-12')), '2026-07-06');
check('answer: Rule 4 mail adds NOTHING (6(e)(2): the period runs from delivery)',
  dateOf(compute('nd-rcp-12a1a-answer-to-complaint', '2026-06-12', { service_method: 'mail' })), '2026-07-06');
// 4 Mar + 30 = Fri 3 Apr (Good Friday) -> Mon 6 Apr.
check('interrogatories: Good Friday rolls to Monday',
  dateOf(compute('nd-rcp-33b2-interrogatory-answers', '2026-03-04')), '2026-04-06');
// Expires Mon 6 Apr after the rollover; +3 AFTER expiry = Thu 9 Apr (add-to-period would give Mon 6 Apr).
check('interrogatories by MAIL: +3 counted from the ROLLED expiry -- Thursday 9 April',
  dateOf(compute('nd-rcp-33b2-interrogatory-answers', '2026-03-04', { service_method: 'mail' })), '2026-04-09');
check('interrogatories by commercial carrier: the same 9 April',
  dateOf(compute('nd-rcp-33b2-interrogatory-answers', '2026-03-04', { service_method: 'third_party_commercial_carrier' })),
  '2026-04-09');
check('interrogatories by EMAIL: nothing added',
  dateOf(compute('nd-rcp-33b2-interrogatory-answers', '2026-03-04', { service_method: 'email' })), '2026-04-06');
// 20 May + 30 = Fri 19 Jun -- Juneteenth is not a North Dakota legal holiday.
check('admissions: Juneteenth does NOT roll',
  dateOf(compute('nd-rcp-36a3-admission-response', '2026-05-20')), '2026-06-19');
// 5 Jan + 14 = Mon 19 Jan (MLK) -> Tue 20 Jan.
check('answer brief: MLK Day rolls (it is in 1-03-01)',
  dateOf(compute('nd-rct-32a2-answer-brief', '2026-01-05')), '2026-01-20');
// Fri 9 Jan + 7 = Fri 16 Jan, every day counted.
check('reply brief: 7 days, weekends counted', dateOf(compute('nd-rct-32a2-reply-brief', '2026-01-09')), '2026-01-16');
// 24 Nov 2027 + 30 = Fri 24 Dec 2027 (Saturday-shift Christmas) -> Mon 27 Dec.
check('production: the 2027 Christmas Saturday shift rolls Friday 24 December',
  dateOf(compute('nd-rcp-34b2a-production-response', '2027-11-24')), '2027-12-27');
// 1 Sep + 60 = Sat 31 Oct -> Mon 2 Nov.
check('notice of appeal: 60 days, weekend rolls',
  dateOf(compute('nd-app-r-4a1-notice-of-appeal', '2026-09-01')), '2026-11-02');
check('notice of appeal by MAIL: +3 after the rolled expiry -- Thursday 5 November',
  dateOf(compute('nd-app-r-4a1-notice-of-appeal', '2026-09-01', { service_method: 'mail' })), '2026-11-05');
check('new trial: no mail days, by the disclosed EARLY reading',
  dateOf(compute('nd-rcp-59c2-motion-for-new-trial', '2026-09-01', { service_method: 'mail' })), '2026-11-02');

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
