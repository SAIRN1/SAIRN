// api/_lib/dental-credentials.test.js
// Plain node:assert tests -- no test framework, matching api/'s existing
// zero-npm-dependency convention (see api/_lib/auth.test.js).
// Run: node api/_lib/dental-credentials.test.js
//
// Every threshold is tested at BOTH SIDES of its boundary -- one day inside,
// one day outside -- because an off-by-one here does not throw, it just fails
// to warn a real dentist that a real licence is about to lapse.
//
// The Ohio hour figures asserted below are the ones read verbatim from the
// statute on 2026-08-24 (ORC 4715.141(A) = 30 for dentists, ORC 4715.25(A) =
// 20 for hygienists) and stored in sql/sairndental_credentials_seed_ohio.json.
// These tests read that seed file directly, so if the seed is ever edited to
// a different number without a new citation, they fail.

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const e = require('./dental-credentials');

const SEED = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', '..', 'sql', 'sairndental_credentials_seed_ohio.json'), 'utf8'));
const RULES = SEED.rules;
const TODAY = '2026-08-24';

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ok - ' + name); }
  catch (err) { failed++; console.error('  FAIL - ' + name); console.error('    ' + err.message); }
}

console.log('daysUntil:');
test('counts whole days forward and backward', () => {
  assert.strictEqual(e.daysUntil('2026-08-25', TODAY), 1);
  assert.strictEqual(e.daysUntil('2026-08-24', TODAY), 0);
  assert.strictEqual(e.daysUntil('2026-08-23', TODAY), -1);
});
test('crosses a month and a leap year correctly', () => {
  assert.strictEqual(e.daysUntil('2026-09-01', '2026-08-31'), 1);
  assert.strictEqual(e.daysUntil('2028-03-01', '2028-02-28'), 2); // 2028 is a leap year
});
test('returns null on junk rather than a number', () => {
  assert.strictEqual(e.daysUntil('', TODAY), null);
  assert.strictEqual(e.daysUntil('08/24/2026', TODAY), null);
  assert.strictEqual(e.daysUntil(null, TODAY), null);
  assert.strictEqual(e.daysUntil('2026-08-24', 'not-a-date'), null);
});

console.log('\n30-day general threshold — BOUNDARY:');
test('exactly 30 days out is expiring (inclusive)', () => {
  assert.strictEqual(e.classifyExpiry('2026-09-23', TODAY, 30).status, 'expiring');
  assert.strictEqual(e.classifyExpiry('2026-09-23', TODAY, 30).days, 30);
});
test('31 days out is ok — one day outside', () => {
  assert.strictEqual(e.classifyExpiry('2026-09-24', TODAY, 30).status, 'ok');
  assert.strictEqual(e.classifyExpiry('2026-09-24', TODAY, 30).days, 31);
});
test('29 days out is expiring — one day inside', () => {
  assert.strictEqual(e.classifyExpiry('2026-09-22', TODAY, 30).status, 'expiring');
});
test('today is expiring, not expired', () => {
  assert.strictEqual(e.classifyExpiry(TODAY, TODAY, 30).status, 'expiring');
  assert.strictEqual(e.classifyExpiry(TODAY, TODAY, 30).days, 0);
});
test('yesterday is expired — the other side of zero', () => {
  assert.strictEqual(e.classifyExpiry('2026-08-23', TODAY, 30).status, 'expired');
  assert.strictEqual(e.classifyExpiry('2026-08-23', TODAY, 30).days, -1);
});
test('a missing expiry is unknown, never silently ok', () => {
  assert.strictEqual(e.classifyExpiry(null, TODAY, 30).status, 'unknown');
  assert.strictEqual(e.classifyExpiry('', TODAY, 30).status, 'unknown');
});

console.log('\n60-day DEA threshold — BOUNDARY (21 CFR 1301.13 renewal window):');
test('DEA records use 60 days, everything else uses 30', () => {
  assert.strictEqual(e.warnDaysFor('dea_registration'), 60);
  assert.strictEqual(e.warnDaysFor('state_license'), 30);
  assert.strictEqual(e.warnDaysFor('certification'), 30);
  assert.strictEqual(e.DEA_WARN_DAYS, 60);
  assert.strictEqual(e.DEFAULT_WARN_DAYS, 30);
});
test('exactly 60 days out is expiring for DEA', () => {
  const r = e.classifyExpiry('2026-10-23', TODAY, e.warnDaysFor('dea_registration'));
  assert.strictEqual(r.days, 60);
  assert.strictEqual(r.status, 'expiring');
});
test('61 days out is ok for DEA — one day outside', () => {
  const r = e.classifyExpiry('2026-10-24', TODAY, e.warnDaysFor('dea_registration'));
  assert.strictEqual(r.days, 61);
  assert.strictEqual(r.status, 'ok');
});
test('the same date is ok for a state licence but expiring for DEA', () => {
  // 45 days out: inside the DEA window, outside the general one. This is the
  // whole point of having two thresholds rather than one.
  assert.strictEqual(e.classifyExpiry('2026-10-08', TODAY, 30).status, 'ok');
  assert.strictEqual(e.classifyExpiry('2026-10-08', TODAY, 60).status, 'expiring');
});

console.log('\nCE pacing — hours remaining vs time remaining, not a day count:');
const cyc = (logged, start, end) => ({
  cycle_start: start || '2025-01-01', cycle_end: end || '2026-12-31',
  hours_required: 30, hours_logged: logged
});
test('all hours logged is complete, even on the last day', () => {
  const r = e.evaluateCeCycle(cyc(30), '2026-12-31');
  assert.strictEqual(r.status, 'complete');
  assert.strictEqual(r.hours_remaining, 0);
});
test('more hours than required is still complete, never negative remaining', () => {
  const r = e.evaluateCeCycle(cyc(35), TODAY);
  assert.strictEqual(r.status, 'complete');
  assert.strictEqual(r.hours_remaining, 0);
});
test('hours outstanding after the cycle ends is overdue', () => {
  const r = e.evaluateCeCycle(cyc(29), '2027-01-01');
  assert.strictEqual(r.status, 'overdue');
  assert.strictEqual(r.hours_remaining, 1);
  assert.ok(r.days_remaining < 0);
});
test('BOUNDARY: pace exactly on the line is on_track, not behind', () => {
  // A 100-day cycle, exactly half elapsed, exactly half the hours done.
  const r = e.evaluateCeCycle({
    cycle_start: '2026-01-01', cycle_end: '2026-04-11', // 100 days
    hours_required: 30, hours_logged: 15
  }, '2026-02-20'); // day 50
  assert.strictEqual(r.cycle_days, 100);
  assert.strictEqual(r.days_elapsed, 50);
  assert.strictEqual(r.status, 'on_track');
});
test('BOUNDARY: one hour under that same line is behind', () => {
  const r = e.evaluateCeCycle({
    cycle_start: '2026-01-01', cycle_end: '2026-04-11',
    hours_required: 30, hours_logged: 14
  }, '2026-02-20');
  assert.strictEqual(r.status, 'behind');
});
test('BOUNDARY: one day later at the same hours is behind', () => {
  const r = e.evaluateCeCycle({
    cycle_start: '2026-01-01', cycle_end: '2026-04-11',
    hours_required: 30, hours_logged: 15
  }, '2026-02-21'); // day 51, still 15 hours
  assert.strictEqual(r.status, 'behind');
});
test('zero hours on day one is on_track, not behind', () => {
  const r = e.evaluateCeCycle(cyc(0, '2026-08-24', '2028-08-23'), TODAY);
  assert.strictEqual(r.status, 'on_track');
  assert.strictEqual(r.days_elapsed, 0);
});
test('a day count would get this wrong, which is why CE does not use one', () => {
  // 10 days left, but the hours are done: NOT an alert.
  const done = e.evaluateCeCycle(cyc(30, '2025-01-01', '2026-09-03'), TODAY);
  assert.strictEqual(done.status, 'complete');
  // 400 days left, nothing logged, most of the cycle gone: IS an alert.
  const behind = e.evaluateCeCycle({
    cycle_start: '2024-01-01', cycle_end: '2027-09-28', hours_required: 30, hours_logged: 0
  }, TODAY);
  assert.strictEqual(behind.status, 'behind');
  assert.ok(behind.days_remaining > 365);
});
test('junk input is refused, not coerced to zero', () => {
  assert.strictEqual(e.evaluateCeCycle({ cycle_start: 'x', cycle_end: 'y', hours_required: 30 }, TODAY).ok, false);
  assert.strictEqual(e.evaluateCeCycle(cyc(-5), TODAY).ok, false);
  assert.strictEqual(e.evaluateCeCycle({ cycle_start: '2026-12-31', cycle_end: '2026-01-01', hours_required: 30 }, TODAY).error.code, 'BAD_CYCLE');
});

console.log('\nOhio rules — read from the seed, fails closed elsewhere:');
test('Ohio dentist rule is 30 hours and carries a real citation', () => {
  const sel = e.selectCeRule(RULES, { state: 'OH', role: 'dentist', on_date: TODAY });
  assert.strictEqual(sel.ok, true);
  assert.strictEqual(sel.rule.data.hours_required, 30);
  assert.strictEqual(sel.rule.data.authority.citation, 'ORC 4715.141(A)');
  assert.ok(sel.rule.data.authority.quote.indexOf('not less than thirty hours') !== -1);
});
test('Ohio hygienist rule is 20 hours — a different statute, not the dentist figure', () => {
  const sel = e.selectCeRule(RULES, { state: 'OH', role: 'hygienist', on_date: TODAY });
  assert.strictEqual(sel.ok, true);
  assert.strictEqual(sel.rule.data.hours_required, 20);
  assert.strictEqual(sel.rule.data.authority.citation, 'ORC 4715.25(A)');
});
test('an unseeded state refuses by name and never borrows Ohio', () => {
  const sel = e.selectCeRule(RULES, { state: 'MI', role: 'dentist', on_date: TODAY });
  assert.strictEqual(sel.ok, false);
  assert.strictEqual(sel.error.code, 'NO_RULE_FOR_STATE');
  assert.ok(sel.error.message.indexOf('MI') !== -1);
});
test('an unseeded role refuses by name rather than substituting', () => {
  const sel = e.selectCeRule(RULES, { state: 'OH', role: 'assistant', on_date: TODAY });
  assert.strictEqual(sel.ok, false);
  assert.strictEqual(sel.error.code, 'NO_RULE_FOR_ROLE');
});
test('every seeded rule carries citation, url, quote and read_on', () => {
  RULES.forEach((r) => {
    const a = r.data.authority;
    assert.ok(a && a.citation && a.url && a.quote && a.read_on, r.rule_id + ' is missing authority');
  });
});
test('no rule encodes a statewide renewal calendar date', () => {
  // The correction this research pass found: ORC 4715.24(A) makes expiry a
  // per-licensee anniversary. If someone later adds a fixed-date rule, this
  // fails and they have to justify it against the statute.
  const term = RULES.find((r) => r.requirement_type === 'license_term');
  assert.strictEqual(term.data.expiry_basis, 'per_licensee_anniversary');
  assert.strictEqual(term.data.renewal_month, undefined);
  assert.strictEqual(term.data.renewal_day, undefined);
});
test('MATE is one-time, not an expiring thing', () => {
  const mate = RULES.find((r) => r.rule_id === 'US-DEA-MATE-8-HOUR');
  assert.strictEqual(mate.data.one_time, true);
  assert.strictEqual(mate.data.hours_required, 8);
});

console.log('\nAppend-only supersession:');
const REC = (over) => Object.assign({
  entry_id: 'DCRED-1', provider_id: 'PRV-1', record_type: 'state_license',
  state: 'OH', expires_on: '2026-08-01', recorded_at: '2026-01-01T00:00:00Z'
}, over);
test('the latest row per provider/type/subject wins', () => {
  const out = e.latestByKey([
    REC({ entry_id: 'DCRED-1', expires_on: '2026-08-01', recorded_at: '2026-01-01T00:00:00Z' }),
    REC({ entry_id: 'DCRED-2', expires_on: '2028-08-01', recorded_at: '2026-06-01T00:00:00Z' })
  ]);
  assert.strictEqual(out.length, 1);
  assert.strictEqual(out[0].expires_on, '2028-08-01');
});
test('a superseded expired licence stops firing', () => {
  const board = e.evaluateBoard([
    REC({ entry_id: 'DCRED-1', expires_on: '2026-08-01', recorded_at: '2026-01-01T00:00:00Z' }),
    REC({ entry_id: 'DCRED-2', expires_on: '2028-08-01', recorded_at: '2026-06-01T00:00:00Z' })
  ], RULES, TODAY);
  assert.strictEqual(board.counts.expired, 0);
  assert.strictEqual(board.counts.ok, 1);
});
test('two different providers do not supersede each other', () => {
  const out = e.latestByKey([REC({ provider_id: 'PRV-1' }), REC({ entry_id: 'DCRED-9', provider_id: 'PRV-2' })]);
  assert.strictEqual(out.length, 2);
});
test('licences in two different states do not supersede each other', () => {
  const out = e.latestByKey([REC({ state: 'OH' }), REC({ entry_id: 'DCRED-9', state: 'IN' })]);
  assert.strictEqual(out.length, 2);
});

console.log('\nThe board:');
test('counts, MATE outstanding, and action_required add up', () => {
  const board = e.evaluateBoard([
    REC({ entry_id: 'A', provider_id: 'PRV-1', record_type: 'state_license', expires_on: '2026-08-01' }),      // expired
    REC({ entry_id: 'B', provider_id: 'PRV-2', record_type: 'state_license', expires_on: '2026-09-23' }),      // expiring (30)
    REC({ entry_id: 'C', provider_id: 'PRV-2', record_type: 'dea_registration', expires_on: '2026-10-23', mate_attested: false }), // expiring (60) + MATE
    REC({ entry_id: 'D', provider_id: 'PRV-1', record_type: 'certification', credential: 'BLS', expires_on: '2027-01-01' })        // ok
  ], RULES, TODAY);
  assert.strictEqual(board.counts.expired, 1);
  assert.strictEqual(board.counts.expiring, 2);
  assert.strictEqual(board.counts.ok, 1);
  assert.strictEqual(board.mate_outstanding, 1);
  assert.strictEqual(board.action_required, 4);
});
test('an attested MATE does not count as outstanding', () => {
  const board = e.evaluateBoard([
    REC({ entry_id: 'C', record_type: 'dea_registration', expires_on: '2028-01-01', mate_attested: true, mate_attested_on: '2024-03-01' })
  ], RULES, TODAY);
  assert.strictEqual(board.mate_outstanding, 0);
  assert.strictEqual(board.items[0].mate_attested_on, '2024-03-01');
});
test('a CE cycle with no hours_required pulls the figure from the seeded rule', () => {
  const board = e.evaluateBoard([
    REC({ entry_id: 'E', record_type: 'ce_cycle', state: 'OH', role: 'dentist',
      cycle_start: '2025-01-01', cycle_end: '2026-12-31', hours_logged: 30, expires_on: undefined })
  ], RULES, TODAY);
  assert.strictEqual(board.ce.complete, 1);
  assert.strictEqual(board.items[0].hours_required, 30);
  assert.strictEqual(board.items[0].hours_required_from, 'rule:OH-CE-DENTIST-BIENNIAL');
});
test('a CE cycle in an unseeded state is unresolved, not assumed', () => {
  const board = e.evaluateBoard([
    REC({ entry_id: 'F', record_type: 'ce_cycle', state: 'MI', role: 'dentist',
      cycle_start: '2025-01-01', cycle_end: '2026-12-31', hours_logged: 0, expires_on: undefined })
  ], RULES, TODAY);
  assert.strictEqual(board.ce.unresolved, 1);
  assert.strictEqual(board.items[0].reason, 'NO_RULE_FOR_STATE');
});
test('most urgent sorts first', () => {
  const board = e.evaluateBoard([
    REC({ entry_id: 'ok', provider_id: 'P1', expires_on: '2030-01-01' }),
    REC({ entry_id: 'dead', provider_id: 'P2', expires_on: '2020-01-01' }),
    REC({ entry_id: 'soon', provider_id: 'P3', expires_on: '2026-09-01' })
  ], RULES, TODAY);
  assert.deepStrictEqual(board.items.map((i) => i.status), ['expired', 'expiring', 'ok']);
});
test('an empty practice produces an empty board, not an error', () => {
  const board = e.evaluateBoard([], RULES, TODAY);
  assert.strictEqual(board.ok, true);
  assert.strictEqual(board.action_required, 0);
  assert.deepStrictEqual(board.items, []);
});
test('an unknown record_type is ignored rather than counted', () => {
  const board = e.evaluateBoard([REC({ record_type: 'malpractice_policy' })], RULES, TODAY);
  assert.deepStrictEqual(board.items, []);
});
test('coverage names what is and is not sourced', () => {
  const cov = e.credentialCoverage(RULES, ['OH', 'MI']);
  assert.deepStrictEqual(cov.covered_states, ['OH', 'US']);
  assert.deepStrictEqual(cov.uncovered_states, ['MI']);
});

// ── PAYER ENROLMENT (competitive-gap audit B1, 2026-09-02) ──────────────
// A LICENCE SAYS THE DENTIST MAY PRACTISE; AN ENROLMENT SAYS A PARTICULAR
// PAYER WILL PAY THEM. The two wear a similar word and this app already had
// the first, which is exactly why the second was easy to believe was present.
// Verified absent before building: `enroll`/`enrol` 0, `CAQH` 0, `revalidat` 0.
//
// The assertions that carry the most weight are the ones about NOT KNOWING.
// `no_record` must never be reported as "not enrolled" and must never be
// summed into money at risk: an absence predicts nothing, and turning it into
// a denial forecast is the fabrication this whole module exists to avoid.
console.log('\npayer enrolment:');
const PE = (over) => Object.assign({
  entry_id: 'pe1', provider_id: 'P1', record_type: 'payer_enrollment',
  payer: 'Delta Dental', recorded_at: '2026-01-01T00:00:00Z'
}, over || {});
const ON = '2026-06-15';

test('effective when the effective date is on or before the service date and nothing terminated it', () => {
  const r = e.enrollmentOnDate([PE({ effective_on: '2026-01-01' })], { provider_id: 'P1', payer: 'Delta Dental', on_date: ON });
  assert.strictEqual(r.status, 'effective');
});
test('the effective date boundary is INCLUSIVE -- effective ON the service date counts', () => {
  assert.strictEqual(e.enrollmentOnDate([PE({ effective_on: ON })], { provider_id: 'P1', payer: 'Delta Dental', on_date: ON }).status, 'effective');
  assert.strictEqual(e.enrollmentOnDate([PE({ effective_on: '2026-06-16' })], { provider_id: 'P1', payer: 'Delta Dental', on_date: ON }).status, 'not_yet_effective');
});
test('the termination boundary is inclusive too -- terminated ON the service date is still covered', () => {
  assert.strictEqual(e.enrollmentOnDate([PE({ effective_on: '2026-01-01', term_on: ON })], { provider_id: 'P1', payer: 'Delta Dental', on_date: ON }).status, 'effective');
  assert.strictEqual(e.enrollmentOnDate([PE({ effective_on: '2026-01-01', term_on: '2026-06-14' })], { provider_id: 'P1', payer: 'Delta Dental', on_date: ON }).status, 'terminated');
});
test('a record with no effective date reads in_process rather than being given one', () => {
  const r = e.enrollmentOnDate([PE({ network_status: 'applied' })], { provider_id: 'P1', payer: 'Delta Dental', on_date: ON });
  assert.strictEqual(r.status, 'in_process');
  assert.strictEqual(r.effective_on, null);
});
test('NO RECORD is its own answer and says so -- never "not enrolled"', () => {
  const r = e.enrollmentOnDate([PE({ effective_on: '2026-01-01' })], { provider_id: 'P1', payer: 'Guardian', on_date: ON });
  assert.strictEqual(r.status, 'no_record');
  assert.ok(/this is an absence, not a finding that the provider is out of network/.test(r.message));
});
test('a patient with no payer is not reported as a provider problem', () => {
  assert.strictEqual(e.enrollmentOnDate([], { provider_id: 'P1', payer: '', on_date: ON }).status, 'no_payer_on_file');
});
test('the payer name is matched case- and whitespace-insensitively, matching the app\'s own coverage lookup', () => {
  const recs = [PE({ effective_on: '2026-01-01' })];
  assert.strictEqual(e.enrollmentOnDate(recs, { provider_id: 'P1', payer: '  delta DENTAL ', on_date: ON }).status, 'effective');
});
test('the payer is part of the append-only key, so a second payer does not retire the first', () => {
  const recs = [
    PE({ entry_id: 'a', payer: 'Delta Dental', effective_on: '2026-01-01', recorded_at: '2026-01-01T00:00:00Z' }),
    PE({ entry_id: 'b', payer: 'Cigna', effective_on: '2026-08-01', recorded_at: '2026-02-01T00:00:00Z' })
  ];
  assert.strictEqual(e.enrollmentOnDate(recs, { provider_id: 'P1', payer: 'Delta Dental', on_date: ON }).status, 'effective');
  assert.strictEqual(e.enrollmentOnDate(recs, { provider_id: 'P1', payer: 'Cigna', on_date: ON }).status, 'not_yet_effective');
});
test('a later record for the SAME payer supersedes the earlier one', () => {
  const recs = [
    PE({ entry_id: 'a', effective_on: '2026-01-01', recorded_at: '2026-01-01T00:00:00Z' }),
    PE({ entry_id: 'b', effective_on: '2026-01-01', term_on: '2026-05-01', recorded_at: '2026-06-01T00:00:00Z' })
  ];
  assert.strictEqual(e.enrollmentOnDate(recs, { provider_id: 'P1', payer: 'Delta Dental', on_date: ON }).status, 'terminated');
});
test('one provider\'s enrolment never answers for another', () => {
  const recs = [PE({ provider_id: 'P1', effective_on: '2026-01-01' })];
  assert.strictEqual(e.enrollmentOnDate(recs, { provider_id: 'P2', payer: 'Delta Dental', on_date: ON }).status, 'no_record');
});
test('a bad service date refuses rather than resolving', () => {
  assert.strictEqual(e.enrollmentOnDate([], { provider_id: 'P1', payer: 'x', on_date: 'June 2026' }).ok, false);
});

console.log('\nclaims at enrolment risk:');
const RISK_RECS = [
  PE({ entry_id: 'a', provider_id: 'P1', payer: 'Delta Dental', effective_on: '2026-07-01' }),        // not yet effective
  PE({ entry_id: 'b', provider_id: 'P1', payer: 'Aetna', effective_on: '2025-01-01', term_on: '2026-03-01' }), // terminated
  PE({ entry_id: 'c', provider_id: 'P2', payer: 'Cigna', effective_on: '2026-01-01' })                // fine
];
const LINES = [
  { charge_id: 'c1', patient_name: 'A', provider_id: 'P1', payer: 'Delta Dental', service_date: ON, amount: 500 },
  { charge_id: 'c2', patient_name: 'B', provider_id: 'P1', payer: 'Aetna', service_date: ON, amount: 300 },
  { charge_id: 'c3', patient_name: 'C', provider_id: 'P2', payer: 'Cigna', service_date: ON, amount: 900 },
  { charge_id: 'c4', patient_name: 'D', provider_id: 'P2', payer: 'Guardian', service_date: ON, amount: 700 },
  { charge_id: 'c5', patient_name: 'E', provider_id: 'P2', payer: '', service_date: ON, amount: 250 }
];
test('only charges a stored record contradicts are at risk, and they are sorted by money', () => {
  const out = e.claimsAtEnrollmentRisk(RISK_RECS, LINES);
  assert.deepStrictEqual(out.at_risk.map((r) => r.charge_id), ['c1', 'c2']);
  assert.strictEqual(out.amount_at_risk, 800);
});
test('a charge with NO enrolment record is reported separately and NEVER added to the exposure', () => {
  const out = e.claimsAtEnrollmentRisk(RISK_RECS, LINES);
  assert.deepStrictEqual(out.unknown.map((r) => r.charge_id), ['c4']);
  assert.strictEqual(out.amount_unknown, 700);
  assert.notStrictEqual(out.amount_at_risk, 1500);
  assert.ok(/The two are never added together/.test(out.note));
});
test('an effective provider and a self-pay patient are in neither list', () => {
  const out = e.claimsAtEnrollmentRisk(RISK_RECS, LINES);
  const all = out.at_risk.concat(out.unknown).map((r) => r.charge_id);
  assert.ok(all.indexOf('c3') === -1);
  assert.ok(all.indexOf('c5') === -1);
});
test('a charge with no service date is skipped rather than dated to today', () => {
  const out = e.claimsAtEnrollmentRisk(RISK_RECS, [{ charge_id: 'x', provider_id: 'P1', payer: 'Aetna', amount: 100 }]);
  assert.deepStrictEqual(out.at_risk, []);
  assert.deepStrictEqual(out.unknown, []);
});
test('risk is judged on the SERVICE date, not on today', () => {
  const before = e.claimsAtEnrollmentRisk(RISK_RECS, [{ charge_id: 'x', provider_id: 'P1', payer: 'Delta Dental', service_date: '2026-06-15', amount: 100 }]);
  const after = e.claimsAtEnrollmentRisk(RISK_RECS, [{ charge_id: 'x', provider_id: 'P1', payer: 'Delta Dental', service_date: '2026-07-02', amount: 100 }]);
  assert.strictEqual(before.at_risk.length, 1);
  assert.strictEqual(after.at_risk.length, 0);
});

console.log('\npayer enrolment on the board:');
test('an enrolment shows BOTH its enrolment state and its revalidation state', () => {
  const board = e.evaluateBoard([PE({ effective_on: '2026-01-01', revalidation_due_on: '2026-09-01' })], RULES, TODAY);
  const item = board.items[0];
  assert.strictEqual(item.enrollment_status, 'effective');
  assert.strictEqual(item.revalidation_status, 'expiring');
});
test('a TERMINATED enrolment is not hidden behind a far-off revalidation date', () => {
  const board = e.evaluateBoard([PE({ effective_on: '2025-01-01', term_on: '2026-01-01', revalidation_due_on: '2030-01-01' })], RULES, TODAY);
  assert.strictEqual(board.items[0].enrollment_status, 'terminated');
});
test('no revalidation date on file counts as unknown, not ok', () => {
  const board = e.evaluateBoard([PE({ effective_on: '2026-01-01' })], RULES, TODAY);
  assert.strictEqual(board.items[0].revalidation_status, 'unknown');
  assert.strictEqual(board.counts.unknown, 1);
  assert.strictEqual(board.counts.ok, 0);
});
test('payer_enrollment is a permitted record type, so the write path accepts it', () => {
  assert.strictEqual(e.RECORD_TYPES.payer_enrollment, true);
});
test('and the endpoint names the permitted set from that table rather than a retyped list', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'sd-data.js'), 'utf8');
  assert.ok(/record_type must be one of: ' \+ Object\.keys\(dentalCreds\.RECORD_TYPES\)/.test(src));
});
// THE DATABASE HAD ITS OWN LIST AND IT WAS NOT THE ENGINE'S. dnt_credentials
// carries a CHECK constraint enumerating the record types, so payer_enrollment
// passed every JavaScript guard and would have been rejected by Postgres --
// and the page would have said "saved on this device only", which reads as a
// connectivity problem. Three places have to agree and now one test says so.
test('the schema CHECK constraint permits exactly the engine\'s record types', () => {
  const sql = fs.readFileSync(path.join(__dirname, '..', '..', 'sql', 'sairndental_credentials_schema.sql'), 'utf8');
  const m = sql.match(/constraint dntcd_type_check check \(record_type in\s*\r?\n?\s*\(([^)]*)\)/);
  assert.ok(m, 'the CHECK constraint is still in the schema file');
  const inSql = m[1].split(',').map((s) => s.trim().replace(/^'|'$/g, '')).sort();
  assert.deepStrictEqual(inSql, Object.keys(e.RECORD_TYPES).sort());
});
test('and an idempotent ALTER is shipped for databases that already ran the file', () => {
  const sql = fs.readFileSync(path.join(__dirname, '..', '..', 'sql', 'sairndental_credentials_schema.sql'), 'utf8');
  assert.ok(/alter table public\.dnt_credentials drop constraint if exists dntcd_type_check/.test(sql));
  assert.ok(/alter table public\.dnt_credentials add constraint dntcd_type_check[\s\S]*payer_enrollment/.test(sql));
});
test('a check-constraint rejection is reported as a migration step, not as a sync failure', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'sd-data.js'), 'utf8');
  assert.ok(/RECORD_TYPE_NOT_MIGRATED/.test(src));
  assert.ok(/dntcd_type_check\|violates check constraint/.test(src));
});
test('the enrolment check is NOT reimplemented in the browser', () => {
  const html = fs.readFileSync(path.join(__dirname, '..', '..', 'sairndental.html'), 'utf8');
  assert.ok(html.indexOf('claims_at_risk') !== -1, 'the page reads the server result');
  assert.ok(html.indexOf('enrollmentOnDate') === -1, 'the page must not carry its own copy of the decision');
});

console.log('\n' + passed + ' passed, ' + failed + ' failed');
if (failed > 0) process.exit(1);
