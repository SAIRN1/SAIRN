// api/_lib/roofing-warranties.test.js
// Plain node:assert tests -- no framework, matching api/'s zero-npm-dependency
// convention (see api/_lib/auth.test.js, subcontractor-compliance.test.js).
// Run: node api/_lib/roofing-warranties.test.js
//
// These test the DECISIONS, not the happy path. Every case below is a way the
// feature could quietly say something untrue about somebody's roof warranty.

const assert = require('assert');
const w = require('./roofing-warranties');

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('  ok - ' + name);
  } catch (e) {
    console.error('  FAIL - ' + name + '\n      ' + e.message);
    process.exitCode = 1;
  }
}

const TODAY = '2026-09-02';
const held = { program_id: 'PRG-ME', program_name: 'Master Elite', status: 'held', has_expiry: true, expires_on: '2027-06-01' };
const tier = { tier_id: 'T1', manufacturer: 'GAF', tier_name: 'Golden Pledge', requires_program_id: 'PRG-ME', source: 'our 2026 programme agreement, p.4' };

// ── it refuses to assume a clock ───────────────────────────────────────────

test('every entry point REFUSES without today rather than defaulting to UTC now', () => {
  ['tierAvailability', 'registrationState', 'coverageState', 'evaluateWarranty'].forEach((fn) => {
    const r = w[fn]({});
    assert.strictEqual(r.ok, false, fn + ' should refuse');
    assert.strictEqual(r.error.code, 'NO_TODAY', fn + ' should refuse with NO_TODAY');
  });
});

// ── the tier gate ─────────────────────────────────────────────────────────

test('a tier gated on a held, current programme is available', () => {
  const r = w.tierAvailability({ today: TODAY, tiers: [tier], programs: [held] });
  assert.strictEqual(r.tiers[0].availability, 'available');
  assert.deepStrictEqual(r.available, ['T1']);
});

test('a lapsed-by-DATE programme blocks the tier even while stored as held', () => {
  const stale = Object.assign({}, held, { expires_on: '2026-01-01' });
  const r = w.tierAvailability({ today: TODAY, tiers: [tier], programs: [stale] });
  assert.strictEqual(r.tiers[0].availability, 'unavailable');
  assert.ok(/lapsed 244 days ago/.test(r.tiers[0].reason), r.tiers[0].reason);
});

test('a programme held with NO readable expiry is unusable, never available', () => {
  const vague = Object.assign({}, held, { expires_on: null });
  const r = w.tierAvailability({ today: TODAY, tiers: [tier], programs: [vague] });
  assert.strictEqual(r.tiers[0].availability, 'unusable');
  assert.deepStrictEqual(r.available, [], 'the whole point of the gate is that standing lapses');
});

test('has_expiry:false is a real answer and does not fall into the unusable branch', () => {
  const perpetual = { program_id: 'PRG-ME', program_name: 'Master Elite', status: 'held', has_expiry: false };
  const r = w.tierAvailability({ today: TODAY, tiers: [tier], programs: [perpetual] });
  assert.strictEqual(r.tiers[0].availability, 'available');
});

test('a tier naming a programme that is NOT on file is unusable, not available', () => {
  const r = w.tierAvailability({ today: TODAY, tiers: [tier], programs: [] });
  assert.strictEqual(r.tiers[0].availability, 'unusable');
  assert.deepStrictEqual(r.unusable, ['T1'], 'a typo in a programme id must not read as permission to sell');
});

test('a tier with NO SOURCE is unusable -- same rule as an unsourced requirement', () => {
  const unsourced = Object.assign({}, tier, { source: '' });
  const r = w.tierAvailability({ today: TODAY, tiers: [unsourced], programs: [held] });
  assert.strictEqual(r.tiers[0].availability, 'unusable');
});

test('a tier with no certification condition is unrestricted, and says so', () => {
  const std = { tier_id: 'T0', manufacturer: 'GAF', tier_name: 'Standard limited', source: 'shipped with the product' };
  const r = w.tierAvailability({ today: TODAY, tiers: [std], programs: [] });
  assert.strictEqual(r.tiers[0].availability, 'unrestricted');
  assert.deepStrictEqual(r.available, ['T0']);
});

test('every tier is flagged self_reported -- the app never speaks for the manufacturer', () => {
  const r = w.tierAvailability({ today: TODAY, tiers: [tier], programs: [held] });
  assert.strictEqual(r.tiers[0].self_reported, true);
});

// ── the registration clock ────────────────────────────────────────────────

test('no stated deadline produces no_deadline_stated, NEVER a guessed 30 days', () => {
  const r = w.registrationState({ today: TODAY, warranty: { status: 'not_registered', installed_on: '2026-08-01' } });
  assert.strictEqual(r.registration, 'no_deadline_stated');
  assert.strictEqual(r.deadline_on, null);
  assert.strictEqual(r.days_left, null);
});

test('an unregistered roof past its stated deadline is overdue, with the date', () => {
  const r = w.registrationState({ today: TODAY, warranty: { status: 'not_registered', installed_on: '2026-07-01', register_within_days: 45 } });
  assert.strictEqual(r.deadline_on, '2026-08-15');
  assert.strictEqual(r.registration, 'overdue');
  assert.strictEqual(r.days_left, -18);
});

test('inside the warn window it is due_soon; outside it, open', () => {
  const soon = w.registrationState({ today: TODAY, warranty: { status: 'not_registered', installed_on: '2026-08-20', register_within_days: 30 } });
  assert.strictEqual(soon.registration, 'due_soon');
  assert.strictEqual(soon.days_left, 17);
  const open = w.registrationState({ today: TODAY, warranty: { status: 'not_registered', installed_on: '2026-08-20', register_within_days: 120 } });
  assert.strictEqual(open.registration, 'open');
});

test('the warn window is a caller setting, not a manufacturer term', () => {
  const wa = { status: 'not_registered', installed_on: '2026-08-20', register_within_days: 30 };
  assert.strictEqual(w.registrationState({ today: TODAY, warranty: wa, warn_days: 5 }).registration, 'open');
  assert.strictEqual(w.registrationState({ today: TODAY, warranty: wa, warn_days: 60 }).registration, 'due_soon');
});

test('LATE registration is reported rather than hidden, and stays registered', () => {
  const r = w.registrationState({ today: TODAY, warranty: {
    status: 'registered', installed_on: '2026-06-01', register_within_days: 30, registered_on: '2026-07-15' } });
  assert.strictEqual(r.registration, 'registered');
  assert.strictEqual(r.registered_late_by, 14);
  assert.ok(/registered 14 days after/.test(r.problems[0]));
});

test('registered ON TIME carries no late problem', () => {
  const r = w.registrationState({ today: TODAY, warranty: {
    status: 'registered', installed_on: '2026-06-01', register_within_days: 30, registered_on: '2026-06-20' } });
  assert.deepStrictEqual(r.problems, []);
  assert.strictEqual(r.registered_late_by, undefined);
});

test('no install date cannot produce a deadline, and says which fact is missing', () => {
  const r = w.registrationState({ today: TODAY, warranty: { status: 'not_registered', register_within_days: 30 } });
  assert.strictEqual(r.registration, 'no_install_date');
});

test('an unrecognised status becomes null WITH a problem, never passed through', () => {
  const r = w.registrationState({ today: TODAY, warranty: { status: 'filed-ish', installed_on: '2026-08-01' } });
  assert.strictEqual(r.status, null);
  assert.ok(/unrecognised warranty status/.test(r.problems[0]));
});

test('a void warranty short-circuits -- no deadline theatre on a dead warranty', () => {
  const r = w.registrationState({ today: TODAY, warranty: { status: 'void', installed_on: '2026-01-01', register_within_days: 30 } });
  assert.strictEqual(r.registration, 'void');
  assert.strictEqual(r.deadline_on, null);
});

// ── coverage ──────────────────────────────────────────────────────────────

test('coverage derives from the term when no certificate date is on file', () => {
  const r = w.coverageState({ today: TODAY, warranty: { installed_on: '2026-05-10', coverage_years: 25 } });
  assert.strictEqual(r.expires_on, '2051-05-10');
  assert.strictEqual(r.basis, 'derived_from_term');
  assert.strictEqual(r.state, 'active');
});

test('the CERTIFICATE date wins over our arithmetic, and the disagreement is reported', () => {
  const r = w.coverageState({ today: TODAY, warranty: {
    installed_on: '2026-05-10', coverage_years: 25, coverage_expires_on: '2051-06-01' } });
  assert.strictEqual(r.expires_on, '2051-06-01');
  assert.strictEqual(r.basis, 'stated');
  assert.ok(/disagree/.test(r.problems[0]), 'a silent mismatch is the bug');
});

test('an agreeing term and certificate raise nothing', () => {
  const r = w.coverageState({ today: TODAY, warranty: {
    installed_on: '2026-05-10', coverage_years: 25, coverage_expires_on: '2051-05-10' } });
  assert.deepStrictEqual(r.problems, []);
});

test('no term and no date is basis none, not a zero-year warranty expiring today', () => {
  const r = w.coverageState({ today: TODAY, warranty: { installed_on: '2026-05-10' } });
  assert.strictEqual(r.basis, 'none');
  assert.strictEqual(r.expires_on, null);
  assert.strictEqual(r.state, undefined);
});

// ── whole ─────────────────────────────────────────────────────────────────

test('evaluateWarranty gathers registration and coverage problems into one list', () => {
  const r = w.evaluateWarranty({ today: TODAY, warranty: {
    warranty_id: 'W1', job_id: 'JOB-1', status: 'registered',
    installed_on: '2026-06-01', register_within_days: 30, registered_on: '2026-07-15',
    // 25 years from 2026-06-01 derives 2051-06-01, so the certificate date
    // below genuinely disagrees. The first draft of this fixture used
    // 2051-06-01 and the two AGREED -- the assertion failed and was right to:
    // I had written a test for a disagreement that did not exist.
    coverage_years: 25, coverage_expires_on: '2051-07-01' } });
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.problems.length, 2, 'one late registration + one coverage disagreement');
});

test('no warranty is an explicit error, not an empty pass', () => {
  const r = w.evaluateWarranty({ today: TODAY });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.error.code, 'NO_WARRANTY');
});

console.log(passed + ' passed');
