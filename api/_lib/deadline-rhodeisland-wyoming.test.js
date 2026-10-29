// Rhode Island and Wyoming deadline rows -- verified against the REAL engine and
// the REAL seed/calendar JSON on disk (hank b65, 2026-10-29). Every expected
// date was derived BY HAND first.
//
// RHODE ISLAND: ONE day for mail OR electronic service (6(d)), added to the
//   period; 40-day interrogatories and production; Victory Day, RI
//   Independence Day, Columbus Day, Juneteenth, election day 2026; the
//   employee-only Saturday->Monday shift is NOT encoded (early).
// WYOMING: three days for mail or delivery to the clerk (6(d)); Sunday-only
//   shift; NO Juneteenth, NO Columbus Day; the 6(c)(2) motion response is not
//   seeded (it ends at the EARLIER of two dates).

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');
const SQL = path.join(__dirname, '..', '..', 'sql');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}
function load(j, file) {
  const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_' + file + '.json'), 'utf8'));
  const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_' + file + '.json'), 'utf8'));
  const calendars = {};
  for (const row of cal.holiday_calendars) {
    calendars[row.jurisdiction] = calendars[row.jurisdiction] || {};
    calendars[row.jurisdiction][String(row.year)] = row.dates;
  }
  const compute = (id, d, extra) => {
    const rule = seed.rules.find(r => r.rule_id === id);
    if (!rule) throw new Error('no such rule: ' + id);
    const r = engine.computeDeadline(Object.assign({ jurisdiction: j, domain: rule.domain, trigger_event: rule.trigger_event,
      trigger_date: d, rules: seed.rules, calendars: calendars, as_of: d }, extra || {}));
    return r.ok ? r.due_date : ('REFUSED:' + r.code);
  };
  return { seed, cal, calendars, compute, days: y => calendars[j][String(y)].map(x => x.date) };
}
const CS = engine.COMPUTATION_STANDARDS, XS = engine.SERVICE_EXTENSION_STANDARDS;

// ── RHODE ISLAND ──────────────────────────────────────────────────────
const RI = load('ri', 'rhodeisland');
check('RI: 8 rules, all ri_rcp_6a', [RI.seed.rules.length, RI.seed.rules.every(r => r.computation === 'ri_rcp_6a')], [8, true]);
check('RI: 6(d) is ONE day on every extended row', RI.seed.rules.filter(r => r.service_extension).every(r => r.service_extension.add === 1), true);
check('RI: 6(d) qualifies mail AND electronic, not personal or carrier',
  ['mail', 'email', 'electronic', 'efiling_service', 'personal', 'third_party_commercial_carrier'].filter(m => XS.ri_rcp_6d.qualifies(m)),
  ['mail', 'email', 'electronic', 'efiling_service']);
check('RI: federal count, no short-period exclusion', [CS.ri_rcp_6a.impl, CS.ri_rcp_6a.short_period_exclusion_days], ['frcp_6a', undefined]);
check('RI: coverage is EARLY', engine.JURISDICTION_COVERAGE.ri.direction, 'early');
check('RI 2026: Victory Day 10 Aug, RI Independence 4 May, election day 3 Nov, Thanksgiving 26 Nov',
  ['2026-08-10', '2026-05-04', '2026-11-03', '2026-11-26'].every(d => RI.days(2026).includes(d)), true);
check('RI 2028: NO election day (legislative-only year, omitted early)', RI.days(2028).includes('2028-11-07'), false);
check('RI 2026: Saturday 4 July does NOT make Monday 6 July a holiday (employee-only shift omitted)',
  RI.days(2026).includes('2026-07-06'), false);
check('RI 2027: Sunday 4 July makes Monday 5 July a holiday (general shift)', RI.days(2027).includes('2027-07-05'), true);
// 21 Jul + 20 = Mon 10 Aug (Victory Day) -> Tue 11 Aug.
check('RI answer: Victory Day rolls', RI.compute('ri-rcp-12a1a-answer-to-complaint', '2026-07-21'), '2026-08-11');
check('RI answer: mail adds nothing (process)', RI.compute('ri-rcp-12a1a-answer-to-complaint', '2026-07-21', { service_method: 'mail' }), '2026-08-11');
// 24 Sep + 40 = Tue 3 Nov (election day) -> Wed 4 Nov.
check('RI interrogatories: 40 days onto election day, rolls', RI.compute('ri-rcp-33-interrogatory-answers', '2026-09-24'), '2026-11-04');
// 23 Sep + 40 + 1 (email) = Tue 3 Nov -> Wed 4 Nov.
check('RI interrogatories by EMAIL: +1 day, then roll', RI.compute('ri-rcp-33-interrogatory-answers', '2026-09-23', { service_method: 'email' }), '2026-11-04');
check('RI interrogatories by hand: no day added', RI.compute('ri-rcp-33-interrogatory-answers', '2026-09-23', { service_method: 'personal' }), '2026-11-02');
// 4 Apr + 30 = Mon 4 May (RI Independence Day) -> Tue 5 May.
check('RI admissions: 30 days onto RI Independence Day', RI.compute('ri-rcp-36a-admission-response', '2026-04-04'), '2026-05-05');
// 26 Jun + 10 = Mon 6 Jul -- NOT a holiday on this reading.
check('RI new trial: Monday 6 July 2026 is a working day', RI.compute('ri-rcp-59b-motion-for-new-trial', '2026-06-26'), '2026-07-06');

// ── WYOMING ───────────────────────────────────────────────────────────
const WY = load('wy', 'wyoming');
check('WY: 6 rules, all wy_rcp_6a', [WY.seed.rules.length, WY.seed.rules.every(r => r.computation === 'wy_rcp_6a')], [6, true]);
check('WY: 6(d) mail or delivery to the clerk only',
  ['mail', 'left_with_clerk', 'email', 'electronic', 'personal'].filter(m => XS.wy_rcp_6d.qualifies(m)), ['mail', 'left_with_clerk']);
check('WY: 6(d) added to the period', XS.wy_rcp_6d.sequence, 'add_to_period_then_roll');
check('WY: coverage is EARLY and names local officials',
  [engine.JURISDICTION_COVERAGE.wy.direction, /local officials/.test(engine.JURISDICTION_COVERAGE.wy.detail)], ['early', true]);
check('WY: no motion-response row (the EARLIER-of limb)', WY.seed.rules.some(r => /6c|response-to-motion/.test(r.rule_id)), false);
check('WY 2026: no Juneteenth, no Columbus Day', [WY.days(2026).includes('2026-06-19'), WY.days(2026).includes('2026-10-12')], [false, false]);
check('WY 2026: no Saturday shift (Friday 3 July is a working day)', WY.days(2026).includes('2026-07-03'), false);
check('WY 2027: Sunday 4 July -> Monday 5 July', WY.days(2027).includes('2027-07-05'), true);
// 20 May + 30 = Fri 19 Jun -- Juneteenth is not a Wyoming legal holiday.
check('WY interrogatories: Juneteenth does NOT roll', WY.compute('wy-rcp-33b2-interrogatory-answers', '2026-05-20'), '2026-06-19');
// 20 May + 30 + 3 (mail) = Mon 22 Jun.
check('WY interrogatories by MAIL: +3 added to the period', WY.compute('wy-rcp-33b2-interrogatory-answers', '2026-05-20', { service_method: 'mail' }), '2026-06-22');
check('WY interrogatories by EMAIL: nothing added', WY.compute('wy-rcp-33b2-interrogatory-answers', '2026-05-20', { service_method: 'email' }), '2026-06-19');
// 13 Jun + 20 = Fri 3 Jul -- no Saturday shift, stays.
check('WY answer: Friday 3 July 2026 stays', WY.compute('wy-rcp-12a1ai-answer-to-complaint', '2026-06-13'), '2026-07-03');
// 30 Oct + 28 = Fri 27 Nov (day after Thanksgiving, not a holiday).
check('WY new trial: 28 days, the day after Thanksgiving is a working day', WY.compute('wy-rcp-59b-motion-for-new-trial', '2026-10-30'), '2026-11-27');

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
