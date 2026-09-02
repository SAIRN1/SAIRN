// api/_lib/mech-credentials.test.js
// Run: node api/_lib/mech-credentials.test.js
//
// SAIRNmechanical's first data module. The 2026-08-27 competitive research
// ranks "credential registry + expiry + dispatch eligibility" first of ten
// capabilities -- "Nothing else can be gated correctly until this exists".
//
// The two properties worth most of these assertions:
//
//   EPA 608 SECTIONS ARE EQUIPMENT, NOT RANKS. Type I is small appliances,
//   Type II high-pressure, Type III low-pressure, Universal all three. A Type I
//   technician is not "less certified" than a Type II one. Dispatching on "has
//   an EPA card" is how somebody is sent to a chiller they may not legally
//   open, so the section is matched, not merely the presence.
//
//   ELIGIBILITY REFUSES, IT DOES NOT GUESS. Missing -> not eligible. Expired ->
//   not eligible. Present with an unknown expiry -> NOT eligible, and the
//   reason says "unknown" rather than "expired" or "ok". Those lead to
//   different phone calls.

'use strict';
const assert = require('assert');
const m = require('./mech-credentials');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

const TODAY = '2026-09-02';
const rec = (o) => Object.assign({ technician_id: 't1', record_type: 'nate', has_expiry: true }, o);

// ---------------------------------------------------------------------------
section('expiry has four states, and unknown is one of them');

test('a future date is current', () => {
  assert.strictEqual(m.classifyRecord(rec({ expires_on: '2027-01-01' }), TODAY).status, 'current');
});

test('inside the warning window is expiring, not current', () => {
  assert.strictEqual(m.classifyRecord(rec({ expires_on: '2026-09-20' }), TODAY).status, 'expiring');
});

test('a past date is expired', () => {
  assert.strictEqual(m.classifyRecord(rec({ expires_on: '2026-08-01' }), TODAY).status, 'expired');
});

test('THE ONE THAT MATTERS: no date on a record that should have one is UNKNOWN', () => {
  // Not 'current'. An absent renewal date is missing evidence, and reporting
  // it as valid is how an expired licence gets dispatched.
  assert.strictEqual(m.classifyRecord(rec({ expires_on: null }), TODAY).status, 'unknown');
  assert.strictEqual(m.classifyRecord(rec({ expires_on: 'soon' }), TODAY).status, 'unknown');
});

test('has_expiry:false is CURRENT -- a lifetime credential is not missing data', () => {
  // EPA 608 is for life (40 CFR 82.161). Collapsing this into a null date
  // would report a valid lifetime card as incomplete.
  const c = m.classifyRecord({ record_type: 'epa_608', has_expiry: false }, TODAY);
  assert.strictEqual(c.status, 'current');
  assert.strictEqual(c.no_expiry, true);
});

test('expiring exactly on the boundary day counts as expiring, not current', () => {
  assert.strictEqual(m.classifyRecord(rec({ expires_on: '2026-10-02' }), TODAY).status, 'expiring');
  assert.strictEqual(m.classifyRecord(rec({ expires_on: '2026-10-03' }), TODAY).status, 'current');
});

test('expiring TODAY is not yet expired', () => {
  assert.strictEqual(m.classifyRecord(rec({ expires_on: TODAY }), TODAY).status, 'expiring');
});

// ---------------------------------------------------------------------------
section('a renewal supersedes, and the history survives');

test('the latest issue date wins per technician/type/section', () => {
  const rows = m.latestByKey([
    { technician_id: 't1', record_type: 'nate', issued_on: '2022-01-01', expires_on: '2024-01-01', has_expiry: true },
    { technician_id: 't1', record_type: 'nate', issued_on: '2024-01-01', expires_on: '2026-12-01', has_expiry: true }
  ]);
  assert.strictEqual(rows.length, 1);
  assert.strictEqual(rows[0].expires_on, '2026-12-01');
});

test('two EPA sections for one technician are two records, not a duplicate', () => {
  const rows = m.latestByKey([
    { technician_id: 't1', record_type: 'epa_608', epa_section: 'type_i', has_expiry: false },
    { technician_id: 't1', record_type: 'epa_608', epa_section: 'type_ii', has_expiry: false }
  ]);
  assert.strictEqual(rows.length, 2, 'one section overwrote the other');
});

test('two state licences in different jurisdictions are two records', () => {
  const rows = m.latestByKey([
    { technician_id: 't1', record_type: 'state_license', jurisdiction: 'OH', has_expiry: true, expires_on: '2027-01-01' },
    { technician_id: 't1', record_type: 'state_license', jurisdiction: 'PA', has_expiry: true, expires_on: '2027-01-01' }
  ]);
  assert.strictEqual(rows.length, 2);
});

// ---------------------------------------------------------------------------
section('THE SECTION RULE: EPA 608 is equipment, not a rank');

const EPA = (t, s) => ({ technician_id: t, record_type: 'epa_608', epa_section: s, has_expiry: false, issued_on: '2020-01-01' });
const needTypeII = [{ record_type: 'epa_608', epa_section: 'type_ii' }];

test('Universal satisfies a Type II job', () => {
  const e = m.evaluateEligibility([EPA('t1', 'universal')], needTypeII, TODAY);
  assert.deepStrictEqual(e.eligible, ['t1']);
});

test('Type II satisfies a Type II job', () => {
  assert.deepStrictEqual(m.evaluateEligibility([EPA('t1', 'type_ii')], needTypeII, TODAY).eligible, ['t1']);
});

test('Type I does NOT satisfy a Type II job -- different equipment', () => {
  const e = m.evaluateEligibility([EPA('t1', 'type_i')], needTypeII, TODAY);
  assert.deepStrictEqual(e.eligible, []);
  assert.strictEqual(e.technicians[0].blocking[0].reason, 'missing');
});

test('Type III does not satisfy Type II either -- it is not a ladder', () => {
  assert.deepStrictEqual(m.evaluateEligibility([EPA('t1', 'type_iii')], needTypeII, TODAY).eligible, []);
});

test('a job that names no section accepts any EPA 608 card', () => {
  const anyEpa = [{ record_type: 'epa_608' }];
  assert.deepStrictEqual(m.evaluateEligibility([EPA('t1', 'type_i')], anyEpa, TODAY).eligible, ['t1']);
});

test('an unknown section in the REQUIREMENT is refused, not ignored', () => {
  const e = m.evaluateEligibility([EPA('t1', 'universal')], [{ record_type: 'epa_608', epa_section: 'type_iv' }], TODAY);
  assert.strictEqual(e.ok, false);
  assert.strictEqual(e.error.code, 'UNKNOWN_EPA_SECTION');
});

// ---------------------------------------------------------------------------
section('eligibility refuses rather than guessing');

test('NO REQUIREMENTS is refused -- an empty list is not "anyone may go"', () => {
  const e = m.evaluateEligibility([EPA('t1', 'universal')], [], TODAY);
  assert.strictEqual(e.ok, false);
  assert.strictEqual(e.error.code, 'NO_REQUIREMENTS');
  assert.match(e.error.message, /anyone may go/);
});

test('an expired credential blocks, and the reason says expired', () => {
  const recs = [{ technician_id: 't1', record_type: 'nate', has_expiry: true, expires_on: '2026-01-01' }];
  const e = m.evaluateEligibility(recs, [{ record_type: 'nate' }], TODAY);
  assert.deepStrictEqual(e.eligible, []);
  assert.strictEqual(e.technicians[0].blocking[0].reason, 'expired');
});

test('AN UNKNOWN EXPIRY BLOCKS TOO, and never reports as expired or ok', () => {
  // Missing paperwork and a lapsed licence are different problems that lead to
  // different phone calls. Collapsing them loses the difference.
  const recs = [{ technician_id: 't1', record_type: 'nate', has_expiry: true, expires_on: null }];
  const e = m.evaluateEligibility(recs, [{ record_type: 'nate' }], TODAY);
  assert.deepStrictEqual(e.eligible, []);
  assert.strictEqual(e.technicians[0].blocking[0].reason, 'unknown');
});

test('EXPIRING still dispatches -- it is valid today -- but is warned about', () => {
  const recs = [{ technician_id: 't1', record_type: 'nate', has_expiry: true, expires_on: '2026-09-10' }];
  const e = m.evaluateEligibility(recs, [{ record_type: 'nate' }], TODAY);
  assert.deepStrictEqual(e.eligible, ['t1']);
  assert.strictEqual(e.technicians[0].warnings.length, 1);
  assert.strictEqual(e.technicians[0].warnings[0].days, 8);
});

test('every requirement must be met, not just one', () => {
  const recs = [EPA('t1', 'universal')];
  const e = m.evaluateEligibility(recs, [{ record_type: 'epa_608' }, { record_type: 'nate' }], TODAY);
  assert.deepStrictEqual(e.eligible, []);
  assert.strictEqual(e.technicians[0].blocking.length, 1);
  assert.strictEqual(e.technicians[0].blocking[0].record_type, 'nate');
});

test('a state licence must match the jurisdiction the job is in', () => {
  const recs = [{ technician_id: 't1', record_type: 'state_license', jurisdiction: 'OH', has_expiry: true, expires_on: '2027-01-01' }];
  const inPA = [{ record_type: 'state_license', jurisdiction: 'PA' }];
  assert.deepStrictEqual(m.evaluateEligibility(recs, inPA, TODAY).eligible, []);
  // Case-INsensitive on purpose: a dispatcher typing 'oh' must not silently
  // fail to match a licence recorded as 'OH'.
  const inOH = [{ record_type: 'state_license', jurisdiction: 'oh' }];
  assert.deepStrictEqual(m.evaluateEligibility(recs, inOH, TODAY).eligible, ['t1'],
    'jurisdiction matching became case-sensitive');
});

test('an unknown requirement TYPE is refused, not silently skipped', () => {
  const e = m.evaluateEligibility([EPA('t1', 'universal')], [{ record_type: 'vibes' }], TODAY);
  assert.strictEqual(e.ok, false);
  assert.strictEqual(e.error.code, 'UNKNOWN_REQUIREMENT');
});

test('a technician with no records at all does not appear as eligible', () => {
  const e = m.evaluateEligibility([], [{ record_type: 'nate' }], TODAY);
  assert.deepStrictEqual(e.eligible, []);
  assert.strictEqual(e.evaluated, 0);
});

test('a bad today is refused rather than compared against', () => {
  assert.strictEqual(m.evaluateEligibility([], [{ record_type: 'nate' }], 'today').ok, false);
  assert.strictEqual(m.evaluateBoard([], 'nope').ok, false);
});

// ---------------------------------------------------------------------------
section('the board surfaces its unknowns instead of burying them');

test('counts every state, and reports unknown_count beside the totals', () => {
  const b = m.evaluateBoard([
    { technician_id: 't1', record_type: 'nate', has_expiry: true, expires_on: '2027-01-01' },
    { technician_id: 't2', record_type: 'nate', has_expiry: true, expires_on: '2026-09-10' },
    { technician_id: 't3', record_type: 'nate', has_expiry: true, expires_on: '2026-01-01' },
    { technician_id: 't4', record_type: 'nate', has_expiry: true, expires_on: null }
  ], TODAY);
  assert.strictEqual(b.ok, true);
  assert.deepStrictEqual(b.counts, { current: 1, expiring: 1, expired: 1, unknown: 1 });
  assert.strictEqual(b.unknown_count, 1);
});

test('an empty registry is an empty board, not an error and not a verdict', () => {
  const b = m.evaluateBoard([], TODAY);
  assert.strictEqual(b.ok, true);
  assert.strictEqual(b.rows.length, 0);
  assert.deepStrictEqual(b.counts, { current: 0, expiring: 0, expired: 0, unknown: 0 });
});

test('the module ships NO seeded credentials of any kind', () => {
  // This app had invented technicians with invented NATE and EPA 608 cards
  // presented as a live roster until 2026-08-27. An invented certification
  // here is a claim that a named person may legally handle refrigerant.
  const src = require('fs').readFileSync(require.resolve('./mech-credentials.js'), 'utf8');
  assert.ok(!/NATE Certified|technician_id: *'(?!t1|t2)/.test(src));
  assert.ok(!/const SEED|SAMPLE_|DEMO_/.test(src), 'the engine carries seed data');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' MECH-CREDENTIAL ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
