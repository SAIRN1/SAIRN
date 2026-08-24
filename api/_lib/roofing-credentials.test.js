// api/_lib/roofing-credentials.test.js
// Plain node:assert tests -- no framework, matching api/'s zero-dependency
// convention. Run: node api/_lib/roofing-credentials.test.js
//
// Thresholds are tested on BOTH sides of the boundary. The no-expiry cases get
// the same treatment, because the whole point of has_expiry is that 'current'
// and 'unknown' must never collapse into each other.
//
// The Ohio and OSHA facts asserted below are read from the seed file itself, so
// editing the seed to a different claim without a new citation fails here.

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const e = require('./roofing-credentials');

const SEED = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', '..', 'sql', 'sairnroofing_certifications_seed_ohio.json'), 'utf8'));
const RULES = SEED.rules;
const TODAY = '2026-08-24';

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ok - ' + name); }
  catch (err) { failed++; console.error('  FAIL - ' + name); console.error('    ' + err.message); }
}

const REC = (over) => Object.assign({
  entry_id: 'RFCERT-1', employee_id: 'EMP-1', record_type: 'safety_training',
  credential: 'Fall Protection', expires_on: '2027-01-01',
  recorded_at: '2026-01-01T00:00:00Z'
}, over);

console.log('30-day threshold — BOUNDARY:');
test('exactly 30 days out is expiring (inclusive)', () => {
  const r = e.classifyRecord({ expires_on: '2026-09-23' }, TODAY, 30);
  assert.strictEqual(r.days, 30);
  assert.strictEqual(r.status, 'expiring');
});
test('31 days out is ok — one day outside', () => {
  const r = e.classifyRecord({ expires_on: '2026-09-24' }, TODAY, 30);
  assert.strictEqual(r.days, 31);
  assert.strictEqual(r.status, 'ok');
});
test('29 days out is expiring — one day inside', () => {
  assert.strictEqual(e.classifyRecord({ expires_on: '2026-09-22' }, TODAY, 30).status, 'expiring');
});
test('today is expiring, yesterday is expired', () => {
  assert.strictEqual(e.classifyRecord({ expires_on: TODAY }, TODAY, 30).status, 'expiring');
  assert.strictEqual(e.classifyRecord({ expires_on: '2026-08-23' }, TODAY, 30).status, 'expired');
});

console.log('\nNo-expiry is an answer, not a blank:');
test('has_expiry:false is CURRENT, not unknown', () => {
  const r = e.classifyRecord({ has_expiry: false }, TODAY, 30);
  assert.strictEqual(r.status, 'current');
  assert.strictEqual(r.no_expiry, true);
  assert.strictEqual(r.days, null);
});
test('a missing expiry on a record that should have one is UNKNOWN', () => {
  const r = e.classifyRecord({ expires_on: null }, TODAY, 30);
  assert.strictEqual(r.status, 'unknown');
  assert.strictEqual(r.no_expiry, false);
});
test('the two never collapse — same null date, different answers', () => {
  const lifetime = e.classifyRecord({ has_expiry: false, expires_on: null }, TODAY, 30);
  const missing = e.classifyRecord({ expires_on: null }, TODAY, 30);
  assert.strictEqual(lifetime.status, 'current');
  assert.strictEqual(missing.status, 'unknown');
  assert.notStrictEqual(lifetime.status, missing.status);
});
test('has_expiry:false wins even if a stale date is present', () => {
  // A lifetime card that once carried a guessed date must not read as expired.
  assert.strictEqual(e.classifyRecord({ has_expiry: false, expires_on: '2020-01-01' }, TODAY, 30).status, 'current');
});
test('unknown counts as action_required, current does not', () => {
  const b1 = e.evaluateBoard([REC({ expires_on: null })], RULES, TODAY);
  assert.strictEqual(b1.counts.unknown, 1);
  assert.strictEqual(b1.action_required, 1);
  const b2 = e.evaluateBoard([REC({ record_type: 'osha_card', credential: 'OSHA 30', has_expiry: false, expires_on: null })], RULES, TODAY);
  assert.strictEqual(b2.counts.current, 1);
  assert.strictEqual(b2.action_required, 0);
});

console.log('\nOhio licensing — a NEGATIVE answer, sourced:');
test('Ohio rule says no state roofing licence, and cites the statute', () => {
  const sel = e.selectLicensingRule(RULES, { state: 'OH', on_date: TODAY });
  assert.strictEqual(sel.ok, true);
  assert.strictEqual(sel.rule.data.state_license_required, false);
  assert.strictEqual(sel.rule.data.authority.citation, 'ORC 4740.01 (Construction Industry Licensing Board — definitions)');
});
test('the five licensed trades are enumerated and roofing is not among them', () => {
  const sel = e.selectLicensingRule(RULES, { state: 'OH', on_date: TODAY });
  const trades = sel.rule.data.licensed_trades.map((t) => t.toLowerCase());
  assert.strictEqual(trades.length, 5);
  assert.ok(trades.indexOf('roofing') === -1, 'roofing must not appear in the licensed set');
  ['hvac', 'refrigeration', 'electrical', 'plumbing', 'hydronics'].forEach((t) => {
    assert.ok(trades.indexOf(t) !== -1, t + ' missing');
  });
});
test('another state REFUSES — Ohio\'s negative answer must never be reused', () => {
  const sel = e.selectLicensingRule(RULES, { state: 'CA', on_date: TODAY });
  assert.strictEqual(sel.ok, false);
  assert.strictEqual(sel.error.code, 'NO_RULE_FOR_STATE');
  assert.ok(sel.error.message.indexOf('CA') !== -1);
  // The message must say WHY reusing Ohio would be dangerous, not just refuse.
  assert.ok(/never be reused|no roofing trade at the state level/i.test(sel.error.message));
});
test('federal rules apply regardless of state and are returned separately', () => {
  const fed = e.federalRules(RULES, TODAY);
  assert.strictEqual(fed.length, 2);
  const ids = fed.map((r) => r.rule_id).sort();
  assert.deepStrictEqual(ids, ['US-OSHA-FALL-PROTECTION-6FT', 'US-OSHA-OUTREACH-CARD-NO-EXPIRY']);
});
test('the OSHA fall-protection trigger is 6 feet, quoted from 1926.501', () => {
  const r = RULES.find((x) => x.rule_id === 'US-OSHA-FALL-PROTECTION-6FT');
  assert.strictEqual(r.data.trigger_height_feet, 6);
  assert.ok(r.data.authority.quote.indexOf('6 feet') !== -1);
  assert.strictEqual(r.data.authority.citation, '29 CFR 1926.501(b)(10)-(11)');
});
test('the OSHA card rule records NO federal expiry', () => {
  const r = RULES.find((x) => x.rule_id === 'US-OSHA-OUTREACH-CARD-NO-EXPIRY');
  assert.strictEqual(r.data.federal_expiry, false);
  // Ohio deliberately absent from the refresh map: no claim either way.
  assert.strictEqual(r.data.known_state_refresh_windows_years.OH, undefined);
});
test('every seeded rule carries citation, url, quote and read_on', () => {
  RULES.forEach((r) => {
    const a = r.data.authority;
    assert.ok(a && a.citation && a.url && a.quote && a.read_on, r.rule_id + ' missing authority');
  });
});
test('manufacturer programmes are absent — they are company-level, Phase 4', () => {
  const blob = JSON.stringify(RULES).toLowerCase();
  ['master elite', 'platinum preferred', 'certainteed select'].forEach((p) => {
    assert.ok(blob.indexOf(p) === -1, p + ' must not be seeded as a per-employee rule');
  });
});

console.log('\nAppend-only supersession:');
test('the latest row per employee/type/subject wins', () => {
  const out = e.latestByKey([
    REC({ entry_id: 'A', expires_on: '2026-01-01', recorded_at: '2026-01-01T00:00:00Z' }),
    REC({ entry_id: 'B', expires_on: '2028-01-01', recorded_at: '2026-06-01T00:00:00Z' })
  ]);
  assert.strictEqual(out.length, 1);
  assert.strictEqual(out[0].expires_on, '2028-01-01');
});
test('a superseded expired card stops firing', () => {
  const b = e.evaluateBoard([
    REC({ entry_id: 'A', expires_on: '2026-01-01', recorded_at: '2026-01-01T00:00:00Z' }),
    REC({ entry_id: 'B', expires_on: '2028-01-01', recorded_at: '2026-06-01T00:00:00Z' })
  ], RULES, TODAY);
  assert.strictEqual(b.counts.expired, 0);
  assert.strictEqual(b.counts.ok, 1);
});
test('two employees do not supersede each other', () => {
  assert.strictEqual(e.latestByKey([REC({ employee_id: 'EMP-1' }), REC({ entry_id: 'Z', employee_id: 'EMP-2' })]).length, 2);
});
test('two different credentials for one employee do not supersede each other', () => {
  assert.strictEqual(e.latestByKey([
    REC({ credential: 'Fall Protection' }),
    REC({ entry_id: 'Z', credential: 'Ladder Safety' })
  ]).length, 2);
});
test('local_license rows key on jurisdiction, not credential', () => {
  const out = e.latestByKey([
    REC({ entry_id: 'A', record_type: 'local_license', credential: '', jurisdiction: 'Columbus' }),
    REC({ entry_id: 'B', record_type: 'local_license', credential: '', jurisdiction: 'Cleveland' })
  ]);
  assert.strictEqual(out.length, 2);
});

console.log('\nThe board:');
test('counts and ordering — most urgent first', () => {
  const b = e.evaluateBoard([
    REC({ entry_id: 'ok', employee_id: 'E1', expires_on: '2030-01-01' }),
    REC({ entry_id: 'dead', employee_id: 'E2', expires_on: '2020-01-01' }),
    REC({ entry_id: 'soon', employee_id: 'E3', expires_on: '2026-09-01' }),
    REC({ entry_id: 'life', employee_id: 'E4', record_type: 'osha_card', credential: 'OSHA 10', has_expiry: false, expires_on: null })
  ], RULES, TODAY);
  assert.deepStrictEqual(b.items.map((i) => i.status), ['expired', 'expiring', 'ok', 'current']);
  assert.strictEqual(b.action_required, 2);
});
test('an unknown record_type is ignored, not counted', () => {
  assert.deepStrictEqual(e.evaluateBoard([REC({ record_type: 'gaf_master_elite' })], RULES, TODAY).items, []);
});
test('an empty roster produces an empty board, not an error', () => {
  const b = e.evaluateBoard([], RULES, TODAY);
  assert.strictEqual(b.ok, true);
  assert.strictEqual(b.action_required, 0);
});
test('a bad date is refused', () => {
  assert.strictEqual(e.evaluateBoard([], RULES, 'nope').ok, false);
});
test('coverage names what is and is not sourced', () => {
  const cov = e.credentialCoverage(RULES, ['OH', 'CA']);
  assert.deepStrictEqual(cov.covered_states, ['OH', 'US']);
  assert.deepStrictEqual(cov.uncovered_states, ['CA']);
});

console.log('\n' + passed + ' passed, ' + failed + ' failed');
if (failed > 0) process.exit(1);
