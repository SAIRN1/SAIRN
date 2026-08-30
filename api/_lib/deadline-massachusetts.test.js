// Massachusetts deadline rows -- isolated verification against the REAL engine
// and the REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Every expected date below was worked out BY HAND from the rule text and the
// Mass. G.L. c. 4, s. 7, Cl. 18 holiday list BEFORE the engine was run, and
// the cases were chosen to land on the things that actually differ in
// Massachusetts rather than on convenient Tuesdays:
//
//   - PATRIOTS' DAY, the third Monday in April, which exists in no other
//     jurisdiction in this engine
//   - the SUNDAY-ONLY weekend shift, and the Saturday legal holiday it leaves
//     in place (4 July 2026), which is the opposite of Virginia and West
//     Virginia and which a carried-over generator would have got wrong
//   - the SUFFOLK COUNTY coverage disclosure, which rides on a SUCCESSFUL
//     result because the gap can only ever run EARLY
//   - R. 6(d) extending for ELECTRONIC service, the opposite of FRCP 6(d)
//   - R. 33(a)(4), whose 40 days expressly ABSORB the R. 6(d) three days, so
//     the row must carry no extension at all
//   - R. 33's ABSENT defendant floor, where R. 34 and R. 36 both have one
//
// Run: node api/_lib/deadline-massachusetts.test.js
'use strict';

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_massachusetts.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_massachusetts.json'), 'utf8'));

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
    jurisdiction: 'ma', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── The seed's own shape ──────────────────────────────────────────────────
check('11 rules seeded', seed.rules.length, 11);
check('all rows are jurisdiction ma', seed.rules.every(r => r.jurisdiction === 'ma'), true);
check('every row uses ma_rcp_6a', seed.rules.every(r => r.computation === 'ma_rcp_6a'), true);
check('every rule id is unique', new Set(seed.rules.map(r => r.rule_id)).size, seed.rules.length);
check('every row cites a real quote and url',
  seed.rules.every(r => r.authority && r.authority.quote && r.authority.url), true);
check('no later_of row carries a service extension',
  seed.rules.filter(r => r.trigger_event && r.trigger_event.resolve_periods)
    .every(r => !r.service_extension), true);
// R. 33 grants NO defendant floor, so there must be exactly TWO later_of rows
// (production and admissions), not three.
check('exactly two later_of rows -- production and admissions, NOT interrogatories',
  seed.rules.filter(r => r.trigger_event && r.trigger_event.resolve_periods).map(r => r.rule_id),
  ['ma-r-34-b2A-production-response-defendant-later-of-periods',
   'ma-r-36-a-admission-response-defendant-later-of-periods']);

// ── The standards ─────────────────────────────────────────────────────────
check('ma_rcp_6a declares the 7-day short-period exclusion',
  engine.COMPUTATION_STANDARDS.ma_rcp_6a.short_period_exclusion_days, 7);
check('ma_rcp_6a leaves backward blank (R. 6(a) defines no backward direction)',
  engine.COMPUTATION_STANDARDS.ma_rcp_6a.rollover_suffix_backward, '');
check('ma_rcp_6d lengthens the period, not the federal after-expiry order',
  engine.SERVICE_EXTENSION_STANDARDS.ma_rcp_6d.sequence, 'add_to_period_then_roll');
// THE ELECTRONIC LIMB. FRCP 6(d) stopped extending for electronic service in
// 2016 and NC's 6(e) reaches mail only; Massachusetts reaches both.
check('ma_rcp_6d qualifies mail AND the three electronic routes',
  ['mail', 'email', 'electronic', 'efiling_service_provider',
   'ordinary_mail', 'left_with_clerk', 'facsimile']
    .filter(m => engine.SERVICE_EXTENSION_STANDARDS.ma_rcp_6d.qualifies(m)),
  ['mail', 'email', 'electronic', 'efiling_service_provider']);

// ── Coverage disclosure: the Suffolk County gap ──────────────────────────
const disc = compute('ma-r-12-a1-answer-to-complaint', '2026-05-01');
check('a Massachusetts computation still succeeds', disc.ok, true);
check('coverage is present and incomplete', disc.coverage && disc.coverage.complete, false);
check('coverage direction is early, never late', disc.coverage.direction, 'early');
check('coverage names Suffolk County by name', /Suffolk/.test(disc.coverage.summary), true);
check('coverage detail names both county-only holidays',
  /Evacuation Day/.test(disc.coverage.detail) && /Bunker Hill Day/.test(disc.coverage.detail), true);
check('coverage detail says the omission is never late',
  /never late/.test(disc.coverage.detail), true);

// ── The calendar ─────────────────────────────────────────────────────────
const ma26 = calendars.ma['2026'].map(d => d.date);
const ma27 = calendars.ma['2027'].map(d => d.date);
check('12 statewide legal holidays in 2026', ma26.length, 12);
// PATRIOTS' DAY -- the third Monday in April. No other jurisdiction here.
check("Patriots' Day 2026 is Monday 20 April", ma26.includes('2026-04-20'), true);
check("Patriots' Day 2027 is Monday 19 April", ma27.includes('2027-04-19'), true);
// THE SUNDAY-ONLY SHIFT. 4 July 2026 is a SATURDAY and Cl. 18 does NOT move
// it -- the opposite of Virginia and West Virginia, which would shift it back
// to Friday 3 July. A Friday entry here would mean a generator was copied.
check('Independence Day 2026 stays on SATURDAY 4 July -- no Saturday shift exists',
  ma26.includes('2026-07-04') && !ma26.includes('2026-07-03'), true);
// 4 July 2027 IS a Sunday, so it DOES move, to Monday 5 July.
check('Independence Day 2027 falls on a Sunday and moves to Monday 5 July',
  ma27.includes('2027-07-05') && !ma27.includes('2027-07-04'), true);
check('no calendar entry ever falls on a SUNDAY (the shift would have failed)',
  Object.keys(calendars.ma).every(y => calendars.ma[y]
    .every(d => new Date(d.date + 'T00:00:00Z').getUTCDay() !== 0)), true);
// Suffolk-only days must be absent from every year.
check('Evacuation Day (17 March) is NOT in any calendar year',
  Object.keys(calendars.ma).some(y => calendars.ma[y].some(d => /-03-17$/.test(d.date))), false);
check('Bunker Hill Day (17 June) is NOT in any calendar year',
  Object.keys(calendars.ma).some(y => calendars.ma[y].some(d => /-06-17$/.test(d.date))), false);
check('Columbus Day IS a Massachusetts legal holiday', ma26.includes('2026-10-12'), true);

// ── Computations, hand-checked ───────────────────────────────────────────
// Served Fri 2026-05-01. +20 = Thu 2026-05-21, a business day.
check('R. 12(a)(1) 20-day answer', dateOf(compute('ma-r-12-a1-answer-to-complaint', '2026-05-01')), '2026-05-21');
// Served Tue 2026-03-31. +20 = Mon 2026-04-20 = PATRIOTS' DAY -> Tue 04-21.
check("R. 12(a)(1) rolls off Patriots' Day",
  dateOf(compute('ma-r-12-a1-answer-to-complaint', '2026-03-31')), '2026-04-21');
// The answer to the complaint takes no extension: Rule 4 service, not Rule 5.
const noExt = compute('ma-r-12-a1-answer-to-complaint', '2026-05-01', { service_method: 'mail' });
check('answer to the complaint: mail adds nothing', noExt.due_date, '2026-05-21');
check('answer to the complaint: state is not_requested', noExt.service_extension.state, 'not_requested');

// The Rule 5 sibling DOES extend. +20 = Thu 2026-05-21, +3 = Sun 2026-05-24,
// roll -> Mon 2026-05-25 = MEMORIAL DAY -> Tue 2026-05-26.
{
  const r = compute('ma-r-12-a1-responsive-pleading-to-pleading-served-under-rule-5', '2026-05-01',
    { service_method: 'mail' });
  check('R. 12(a)(1) Rule 5 branch by mail: add 3 then roll off Memorial Day', r.due_date, '2026-05-26');
  check('R. 12(a)(1) Rule 5 branch: 3 days recorded', r.service_extension.days_added, 3);
}
// ELECTRONIC SERVICE EXTENDS TOO -- the finding that separates Massachusetts
// from the federal rule and from North Carolina.
for (const m of ['email', 'electronic', 'efiling_service_provider']) {
  check('R. 6(d) extends for "' + m + '" (FRCP 6(d) would not)',
    compute('ma-r-12-a1-responsive-pleading-to-pleading-served-under-rule-5', '2026-05-01',
      { service_method: m }).due_date, '2026-05-26');
}
// A method the rule does not name must NOT extend.
check('service left with the clerk does not qualify under R. 6(d)',
  compute('ma-r-12-a1-responsive-pleading-to-pleading-served-under-rule-5', '2026-05-01',
    { service_method: 'left_with_clerk' }).service_extension.state, 'not_qualifying');

// R. 12(a)(2)(i): 10 days from NOTICE of the court's action. Fri 2026-05-22
// +10 = Mon 2026-06-01. 10 is NOT less than 7, so every day counts.
check('R. 12(a)(2)(i) 10 days from notice of the court\'s action',
  dateOf(compute('ma-r-12-a2i-responsive-pleading-after-motion-denied', '2026-05-22')), '2026-06-01');
check('R. 12(a)(2)(i) takes no extension (notice of the court\'s own action)',
  compute('ma-r-12-a2i-responsive-pleading-after-motion-denied', '2026-05-22',
    { service_method: 'mail' }).service_extension.state, 'not_requested');
// The sibling limb runs from SERVICE of a paper, so it DOES extend.
check('R. 12(a)(2)(ii) DOES extend -- it runs from service of the more definite statement',
  compute('ma-r-12-a2ii-responsive-pleading-after-more-definite-statement', '2026-05-22',
    { service_method: 'mail' }).service_extension.state, 'applied');

// R. 33(a)(3): 45 days. Fri 2026-05-01 +45 = Mon 2026-06-15.
check('R. 33(a)(3) 45-day interrogatory answers',
  dateOf(compute('ma-r-33-a3-interrogatory-answers', '2026-05-01')), '2026-06-15');
// R. 34 / R. 36 plain limb: 30 days. Fri 2026-05-01 +30 = Sun 2026-05-31 -> Mon 06-01.
check('R. 34(b)(2)(A) 30-day production response rolls off a Sunday',
  dateOf(compute('ma-r-34-b2A-production-response', '2026-05-01')), '2026-06-01');
check('R. 36(a) 30-day admission response rolls off a Sunday',
  dateOf(compute('ma-r-36-a-admission-response', '2026-05-01')), '2026-06-01');

// R. 33(a)(4): 40 days, and the rule ABSORBS the 3-day extension.
check('R. 33(a)(4) 40 days from service of the final request',
  dateOf(compute('ma-r-33-a4-application-for-final-judgment', '2026-05-01')), '2026-06-10');
check('R. 33(a)(4) carries NO service_extension in the data',
  seed.rules.find(r => r.rule_id === 'ma-r-33-a4-application-for-final-judgment').service_extension,
  undefined);
// Even asked for by mail, nothing may be added -- the 40 already includes it.
{
  const r = compute('ma-r-33-a4-application-for-final-judgment', '2026-05-01', { service_method: 'mail' });
  check('R. 33(a)(4) adds nothing even when mail service is supplied', r.due_date, '2026-06-10');
  check('R. 33(a)(4) reports not_requested, never applied', r.service_extension.state, 'not_requested');
}

// ── The 30/45 later-of pair ──────────────────────────────────────────────
// Request served WITH the complaint, both 2026-05-01: limb A ends 2026-05-31,
// limb B ends 2026-06-15. The 45-day floor governs.
{
  const r = engine.computeDeadline({
    jurisdiction: 'ma', domain: 'civil-litigation',
    trigger_event: 'production_request_on_defendant',
    trigger_dates: {
      service_of_request_for_production_on_defendant: '2026-05-01',
      service_of_summons_and_complaint_for_production: '2026-05-01'
    },
    rules: seed.rules, calendars: calendars, as_of: '2026-05-01'
  });
  check('production served with the complaint: the 45-day floor governs', dateOf(r), '2026-06-15');
  check('the 45-day limb is recorded as governing',
    r.steps[0].detail.indexOf('2026-06-15 <- governs') !== -1, true);
}
// Request served three months in: limb A (30 from 2026-08-03) ends 2026-09-02,
// limb B (45 from 2026-05-01) ends 2026-06-15. The 30-day period governs.
{
  const r = engine.computeDeadline({
    jurisdiction: 'ma', domain: 'civil-litigation',
    trigger_event: 'admission_request_on_defendant',
    trigger_dates: {
      service_of_request_for_admission_on_defendant: '2026-08-03',
      service_of_summons_and_complaint_for_admission: '2026-05-01'
    },
    rules: seed.rules, calendars: calendars, as_of: '2026-08-03'
  });
  check('admissions served three months in: the 30-day period governs', dateOf(r), '2026-09-02');
}

// ── Refusals that must stay refusals ─────────────────────────────────────
check('a pre-2008 R. 12 trigger is refused, not computed',
  compute('ma-r-12-a1-answer-to-complaint', '2007-05-01').ok, false);
check('a year outside the loaded calendars refuses',
  compute('ma-r-12-a1-answer-to-complaint', '2033-05-01').code, 'NOT_PROVISIONED');

// ── Blast radius: nothing else may have moved ────────────────────────────
check('ma_rcp_6a reuses the ohio_civ_r_6a impl but keeps its own label',
  [engine.COMPUTATION_STANDARDS.ma_rcp_6a.impl, engine.COMPUTATION_STANDARDS.ma_rcp_6a.label],
  ['ohio_civ_r_6a', 'Mass. R. Civ. P. 6(a)']);
check('wv_rcp_6e is still the only contested standard',
  Object.keys(engine.SERVICE_EXTENSION_STANDARDS)
    .filter(k => typeof engine.SERVICE_EXTENSION_STANDARDS[k].contested === 'function'), ['wv_rcp_6e']);
// UPDATED 2026-08-26 when Missouri was seeded and declared its own gap. The
// assertion is kept rather than deleted because the property it guards has not
// changed: a coverage disclosure must be declared DELIBERATELY, per
// jurisdiction, so an accidental or copy-pasted entry shows up here as a
// failure. Add a jurisdiction to this list only when its gap was actually
// reasoned about, never to make the test pass.
check('exactly Alabama, Arkansas, Kansas, Maryland, Wisconsin, Massachusetts, Minnesota, Mississippi, Missouri, New Mexico and Virginia declare a coverage gap',
  Object.keys(engine.JURISDICTION_COVERAGE).sort(), ['al', 'ar', 'ks', 'ma', 'md', 'mn', 'mo', 'ms', 'nm', 'va', 'wi']);
// Each entry must be its OWN text, not another state's copied across -- the
// failure mode this pins down is a disclosure that names the wrong state.
check('each coverage summary names its own jurisdiction',
  ['al', 'ar', 'ks', 'ma', 'md', 'mn', 'mo', 'ms', 'nm', 'va', 'wi'].filter(k => {
    const s = engine.JURISDICTION_COVERAGE[k].summary;
    return { al: /Alabama/, ar: /Arkansas/, ks: /Kansas/, ma: /Massachusetts|Suffolk/, md: /Maryland/, mn: /Minnesota|Indigenous/, mo: /Missouri/, ms: /Mississippi/, nm: /New Mexico/, va: /Virginia/, wi: /Wisconsin/ }[k].test(s);
  }), ['al', 'ar', 'ks', 'ma', 'md', 'mn', 'mo', 'ms', 'nm', 'va', 'wi']);
// A pre-existing jurisdiction still computes what it computed, through the
// same standards table the two new entries were added to.
{
  const vaSeed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_virginia.json'), 'utf8'));
  const vaCal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_virginia.json'), 'utf8'));
  const vc = {};
  for (const row of vaCal.holiday_calendars) {
    vc[row.jurisdiction] = vc[row.jurisdiction] || {};
    vc[row.jurisdiction][String(row.year)] = row.dates;
  }
  const r = engine.computeDeadline({
    jurisdiction: 'va', domain: 'civil-litigation',
    trigger_event: 'service_of_summons_and_complaint', trigger_date: '2026-10-21',
    rules: vaSeed.rules, calendars: vc, as_of: '2026-10-21'
  });
  check('Virginia still computes unchanged after the Massachusetts additions',
    dateOf(r), '2026-11-12');
  check('Virginia coverage is still its own, not overwritten by Massachusetts',
    r.coverage.summary.indexOf('Virginia') === 0, true);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
