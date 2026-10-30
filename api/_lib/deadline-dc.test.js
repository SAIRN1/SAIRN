// District of Columbia, Superior Court, PROBATE DIVISION deadline rows --
// isolated verification against the REAL engine and the REAL seed/calendar JSON
// on disk (hank b70, 2026-10-30).
//
// REQUIREMENT: D.C. Probate deadlines are computed from D.C. Super. Ct. Prob. R.
//   128(a) -- docs/2026-10-30-hank-b70-dc-probate-deadline-seed-gate.md.
//
// Every expected date was derived BY HAND before the engine ran. What a copied
// neighbour would get wrong:
//
//   - THE HOLIDAY LIST IS THE RULE'S OWN, NOT D.C. CODE 28-2701's: Rule
//     128(a)(6)(A) names eleven days and does NOT name DC Emancipation Day or
//     Inauguration Day, so April 16 is a working day here (EARLY by design).
//   - EACH DAY IS "THE DAY SET ASIDE BY STATUTE FOR OBSERVING" IT: a Saturday
//     holiday is the Friday before -- including New Year's Day 2028, observed on
//     Friday 2027-12-31, which must sit in the 2027 calendar to be reachable.
//   - NO ROW RUNS FROM SERVICE, so Rule 128(d)'s three mail days never apply.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_dc.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_dc.json'), 'utf8'));
function calendarsFrom(holidayCalendars) {
  const out = {};
  for (const row of holidayCalendars) {
    out[row.jurisdiction] = out[row.jurisdiction] || {};
    out[row.jurisdiction][String(row.year)] = row.dates;
  }
  return out;
}
const calendars = calendarsFrom(cal.holiday_calendars);

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}
function compute(ruleId, triggerDate, cals) {
  const rule = seed.rules.find(r => r.rule_id === ruleId);
  if (!rule) throw new Error('no such rule: ' + ruleId);
  return engine.computeDeadline({
    jurisdiction: 'dc', domain: rule.domain, trigger_event: rule.trigger_event,
    trigger_date: triggerDate, rules: seed.rules, calendars: cals || calendars, as_of: triggerDate
  });
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── Shape ─────────────────────────────────────────────────────────────
check('5 rules seeded', seed.rules.length, 5);
check('all rows are dc / probate and use dc_probate_r_128a',
  seed.rules.every(r => r.jurisdiction === 'dc' && r.domain === 'probate' && r.computation === 'dc_probate_r_128a'), true);
check('every rule id is unique', new Set(seed.rules.map(r => r.rule_id)).size, seed.rules.length);
check('every row cites a quote, the primary-source URL on dccourts.gov and retrieved_at',
  seed.rules.every(r => r.authority && r.authority.quote && /^https:\/\/www\.dccourts\.gov\//.test(r.authority.url) && r.authority.retrieved_at), true);
check('NO row carries a service extension (none runs from service)', seed.rules.filter(r => r.service_extension).length, 0);
check('Rule 125(c)(1) is NOT seeded (its second cut-off would make the date LATE)',
  seed.rules.some(r => /125c1/.test(r.rule_id)), false);

// ── Standard and coverage ─────────────────────────────────────────────
check('the standard exists and uses the federal implementation',
  engine.COMPUTATION_STANDARDS && engine.COMPUTATION_STANDARDS.dc_probate_r_128a
    ? engine.COMPUTATION_STANDARDS.dc_probate_r_128a.impl : 'MISSING', 'frcp_6a');
check('coverage is declared incomplete, direction early',
  [engine.JURISDICTION_COVERAGE.dc.complete, engine.JURISDICTION_COVERAGE.dc.direction], [false, 'early']);

// ── Calendar ──────────────────────────────────────────────────────────
const all = cal.holiday_calendars.flatMap(c => c.dates.map(d => d.date));
check('every calendar date sits in the year it falls in (else unreachable)',
  cal.holiday_calendars.every(c => c.dates.every(d => d.date.slice(0, 4) === String(c.year))), true);
check('New Year\'s Day 2028 is observed on Friday 2027-12-31', all.includes('2027-12-31'), true);
check('DC Emancipation Day is NOT a holiday under Rule 128(a)(6)(A)', all.some(d => /-04-16$/.test(d)), false);
check('Inauguration Day 2029 is NOT a holiday under Rule 128(a)(6)(A)', all.includes('2029-01-20') || all.includes('2029-01-22'), false);

// ── Dates, each derived by hand ───────────────────────────────────────
check('105(c)(2): filed Fri 2026-07-17 + 14 -> Fri 2026-07-31',
  dateOf(compute('dc-probate-r105c2-response-to-petition-or-objection', '2026-07-17')), '2026-07-31');
check('105(c)(2): filed 2026-06-19 + 14 = Fri 2026-07-03, the observed Independence Day -> Mon 2026-07-06',
  dateOf(compute('dc-probate-r105c2-response-to-petition-or-objection', '2026-06-19')), '2026-07-06');
check('105(c)(2): filed 2026-04-02 + 14 = Thu 2026-04-16, Emancipation Day, a WORKING day here -> 2026-04-16 (EARLY)',
  dateOf(compute('dc-probate-r105c2-response-to-petition-or-objection', '2026-04-02')), '2026-04-16');
check('112(c)(1): appointed 2026-08-13 + 90 = Wed 2026-11-11, Veterans\' Day -> Thu 2026-11-12',
  dateOf(compute('dc-probate-r112c1-inventory', '2026-08-13')), '2026-11-12');
check('112(c)(2): appointed 2026-10-27 + 60 = Sat 2026-12-26 -> Mon 2026-12-28',
  dateOf(compute('dc-probate-r112c2-conservator-inventory', '2026-10-27')), '2026-12-28');
check('113(e)(6)(B): approved 2027-12-04 + 20 = Fri 2027-12-24, Christmas observed -> Mon 2027-12-27',
  dateOf(compute('dc-probate-r113-demand-for-formal-audit', '2027-12-04')), '2027-12-27');
check('125(c)(2): entered 2027-12-11 + 20 = Fri 2027-12-31, New Year\'s 2028 observed -> Mon 2028-01-03',
  dateOf(compute('dc-probate-r125c2-reconsideration-after-final-account', '2027-12-11')), '2028-01-03');

// ── ABLATION: the observed-day entries are what move these dates ─────
const noShifts = calendarsFrom(cal.holiday_calendars.map(c => Object.assign({}, c, {
  dates: c.dates.filter(d => !/shift\)$/.test(d.name)) })));
check('ABLATION: without the shift entries, the 2026-07-03 case is due ON the observed holiday',
  dateOf(compute('dc-probate-r105c2-response-to-petition-or-objection', '2026-06-19', noShifts)), '2026-07-03');
check('ABLATION: without the shift entries, the cross-year New Year case is due 2027-12-31',
  dateOf(compute('dc-probate-r125c2-reconsideration-after-final-account', '2027-12-11', noShifts)), '2027-12-31');

console.log((fail ? 'FAILED' : 'ok') + '  dc-probate deadlines: ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
