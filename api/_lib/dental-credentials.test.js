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

console.log('\n' + passed + ' passed, ' + failed + ' failed');
if (failed > 0) process.exit(1);
