// South Dakota deadline rows -- isolated verification against the REAL engine and
// the REAL seed/calendar JSON on disk (hank b64, 2026-10-29).
//
// REQUIREMENT: South Dakota deadlines are computed from SDCL 15-6-6 and 1-5-1 --
//   docs/sairnlaw-southdakota-deadline-seed-gate.md.
//
// Every expected date was derived BY HAND before the engine ran. What a copied
// neighbour would get wrong:
//
//   - THE SHORT-PERIOD THRESHOLD IS ELEVEN, not seven: a 10-day period skips
//     intermediate weekends and holidays.
//   - NATIVE AMERICANS' DAY (second Monday in October) and JUNETEENTH are legal
//     holidays, and Juneteenth is one of the FIVE days with both weekend shifts.
//   - THE MAIL DAYS ARE ADDED TO THE PERIOD (one rollover at the end), the
//     opposite of North Dakota's after-expiry order.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_southdakota.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_southdakota.json'), 'utf8'));
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
    jurisdiction: 'sd', domain: rule.domain, trigger_event: rule.trigger_event,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── Shape ─────────────────────────────────────────────────────────────
check('8 rules seeded', seed.rules.length, 8);
check('all rows are sd and use sd_rcp_6a',
  seed.rules.every(r => r.jurisdiction === 'sd' && r.computation === 'sd_rcp_6a'), true);
check('every rule id is unique', new Set(seed.rules.map(r => r.rule_id)).size, seed.rules.length);
check('every row cites a quote, a url and retrieved_at',
  seed.rules.every(r => r.authority && r.authority.quote && r.authority.url && r.authority.retrieved_at), true);
check('NO row with a base count under 11 carries the mail extension (the unstated ordering question)',
  seed.rules.filter(r => r.service_extension && r.count.value < 11).length, 0);
check('exactly the answer, 59(b) and appeal rows carry NO extension',
  seed.rules.filter(r => !r.service_extension).map(r => r.rule_id),
  ['sd-sdcl-15-6-12a-answer-to-complaint', 'sd-sdcl-15-6-59b-motion-for-new-trial', 'sd-sdcl-15-26a-6-notice-of-appeal']);

// ── Standards ─────────────────────────────────────────────────────────
const CS = engine.COMPUTATION_STANDARDS, XS = engine.SERVICE_EXTENSION_STANDARDS;
check('sd_rcp_6a: Ohio mechanism, threshold ELEVEN',
  [CS.sd_rcp_6a.impl, CS.sd_rcp_6a.short_period_exclusion_days], ['ohio_civ_r_6a', 11]);
check('sd_rcp_6e: mail only',
  ['mail', 'facsimile', 'email', 'efiling_service', 'electronic', 'third_party_commercial_carrier']
    .filter(m => XS.sd_rcp_6e.qualifies(m)), ['mail']);
check('sd_rcp_6e lengthens the period', XS.sd_rcp_6e.sequence, 'add_to_period_then_roll');

// ── Coverage ──────────────────────────────────────────────────────────
const disc = compute('sd-sdcl-15-6-12a-answer-to-complaint', '2026-05-01');
check('a South Dakota computation succeeds', disc.ok, true);
check('coverage is incomplete and EARLY',
  [disc.coverage && disc.coverage.complete, disc.coverage && disc.coverage.direction], [false, 'early']);
check('coverage names the clerk limb, the 11:59 p.m. rule and the 45-day floor',
  !!disc.coverage && /inaccessible/.test(disc.coverage.detail) && /11:59/.test(disc.coverage.detail) &&
  /45 days/.test(disc.coverage.detail), true);

// ── Calendar ──────────────────────────────────────────────────────────
const sd = y => calendars.sd[String(y)].map(d => d.date);
check('six years, 2026-2031', Object.keys(calendars.sd), ['2026', '2027', '2028', '2029', '2030', '2031']);
check("NATIVE AMERICANS' DAY 2026 is Monday 12 October", sd(2026).includes('2026-10-12'), true);
check('JUNETEENTH and MLK are holidays', [sd(2026).includes('2026-06-19'), sd(2026).includes('2026-01-19')], [true, true]);
check('Saturday shift: Friday 3 July 2026', sd(2026).includes('2026-07-03'), true);
check('Juneteenth 2027 is a Saturday, so Friday 18 June 2027 is the holiday', sd(2027).includes('2027-06-18'), true);
check('Sunday shift: Independence Day 2027 is Monday 5 July', sd(2027).includes('2027-07-05'), true);
check('no Good Friday', sd(2026).includes('2026-04-03'), false);
check('no calendar entry falls on a Sunday',
  cal.holiday_calendars.every(y => y.dates.every(d => new Date(d.date + 'T00:00:00Z').getUTCDay() !== 0)), true);

// ── Computations, every date derived by hand first ─────────────────────
// 3 Jun + 30 = Fri 3 Jul (Saturday-shift holiday) -> Mon 6 Jul.
check('answer: the shifted Friday rolls to Monday',
  dateOf(compute('sd-sdcl-15-6-12a-answer-to-complaint', '2026-06-03')), '2026-07-06');
check('answer: mail adds NOTHING (process)',
  dateOf(compute('sd-sdcl-15-6-12a-answer-to-complaint', '2026-06-03', { service_method: 'mail' })), '2026-07-06');
// 12 Sep + 30 = Mon 12 Oct (Native Americans' Day) -> Tue 13 Oct.
check("interrogatories: Native Americans' Day rolls",
  dateOf(compute('sd-sdcl-15-6-33a-interrogatory-answers', '2026-09-12')), '2026-10-13');
// Added to the period: 30 + 3 from 12 Sep = Thu 15 Oct.
check('interrogatories by MAIL: 33 days, one rollover at the end -- Thursday 15 October',
  dateOf(compute('sd-sdcl-15-6-33a-interrogatory-answers', '2026-09-12', { service_method: 'mail' })), '2026-10-15');
check('interrogatories by EMAIL: nothing added',
  dateOf(compute('sd-sdcl-15-6-33a-interrogatory-answers', '2026-09-12', { service_method: 'email' })), '2026-10-13');
// Fri 5 Jun, 10 days under 11: 8,9,10,11,12 (5), 15,16,17,18 (9), Fri 19 Juneteenth skipped, Mon 22 (10).
check('new trial: 10 days is UNDER ELEVEN -- weekends and Juneteenth skipped, Monday 22 June',
  dateOf(compute('sd-sdcl-15-6-59b-motion-for-new-trial', '2026-06-05')), '2026-06-22');
// 20 May + 30 = Fri 19 Jun (Juneteenth) -> Mon 22 Jun.
check('notice of appeal: Juneteenth rolls',
  dateOf(compute('sd-sdcl-15-26a-6-notice-of-appeal', '2026-05-20')), '2026-06-22');
// 29 May 2027 + 20 = Fri 18 Jun 2027 (Juneteenth Saturday shift) -> Mon 21 Jun.
check('cross-claim answer: the 2027 Juneteenth Friday shift rolls',
  dateOf(compute('sd-sdcl-15-6-12a-answer-to-crossclaim', '2027-05-29')), '2027-06-21');

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
