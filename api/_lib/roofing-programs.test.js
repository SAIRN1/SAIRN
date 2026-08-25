// api/_lib/roofing-programs.test.js
// Isolation suite for Phase 4d -- company-level manufacturer programmes.
// Every threshold used here is TEST DATA, not a claim about any real
// manufacturer's terms. Nothing in this repo seeds real programme thresholds,
// deliberately -- see the header of roofing-programs.js.

'use strict';
const test = require('node:test');
const assert = require('node:assert');
const pg = require('./roofing-programs.js');

const TODAY = '2026-08-25';

const ROSTER = [
  { employee_id: 'e1', role: 'foreman', active: true },
  { employee_id: 'e2', role: 'crew', active: true },
  { employee_id: 'e3', role: 'crew', active: true },
  { employee_id: 'e4', role: 'admin', active: true },
  { employee_id: 'e5', role: 'crew', active: false }   // inactive -- must not count
];

const CERTS = [
  { employee_id: 'e1', record_type: 'installer_cert', credential: 'Master Craftsman', expires_on: '2027-01-01' },
  { employee_id: 'e2', record_type: 'installer_cert', credential: 'Master Craftsman', has_expiry: false },
  { employee_id: 'e3', record_type: 'installer_cert', credential: 'Master Craftsman', expires_on: '2026-01-01' }, // EXPIRED
  { employee_id: 'e4', record_type: 'safety_training', credential: 'Master Craftsman', expires_on: '2027-01-01' }, // wrong type
  { employee_id: 'e5', record_type: 'installer_cert', credential: 'Master Craftsman', expires_on: '2027-01-01' }  // inactive employee
];

function shareReq(over) {
  return Object.assign({
    req_id: 'R1', label: 'Half the crew hold Master Craftsman',
    kind: 'employee_credential_share', credential: 'Master Craftsman',
    denominator: 'all_active', threshold: 50, source: 'our programme agreement, rev C'
  }, over || {});
}
function attestedReq(over) {
  return Object.assign({
    req_id: 'R2', label: 'General liability', kind: 'insurance_minimum',
    threshold: 1000000, unit: 'USD', attested_value: 2000000,
    attested_on: '2026-08-01', source: 'our COI'
  }, over || {});
}
function program(over) {
  return Object.assign({
    program_id: 'PRG-1', manufacturer: 'TestCo', program_name: 'Test Elite',
    requirements: [], standing: { status: 'not_enrolled' }
  }, over || {});
}

test('a requirement with NO SOURCE is unusable, not evaluated', () => {
  // The whole no-seed decision in one test: a threshold with no stated origin
  // is somebody's guess and must never become a verdict.
  const r = pg.evaluateRequirement(shareReq({ source: '' }), { roster: ROSTER, certifications: CERTS, today: TODAY });
  assert.strictEqual(r.status, 'unusable');
  assert.match(r.detail, /no source named/);
});

test('computed share: expired, wrong-type and inactive holders are all excluded', () => {
  // e1 current, e2 no-expiry -> 2 holders. e3 expired, e4 wrong record_type,
  // e5 inactive. Pool is the 4 active employees. 2/4 = 50%.
  const r = pg.evaluateRequirement(shareReq(), { roster: ROSTER, certifications: CERTS, today: TODAY });
  assert.strictEqual(r.basis, 'computed');
  assert.strictEqual(r.pool_size, 4);
  assert.strictEqual(r.holders, 2);
  assert.strictEqual(r.actual, 50);
  assert.strictEqual(r.status, 'met'); // threshold is >=
  assert.deepStrictEqual(r.holder_ids, ['e1', 'e2']);
});

test('a share one point above the holding is not_met, and says the real numbers', () => {
  const r = pg.evaluateRequirement(shareReq({ threshold: 51 }), { roster: ROSTER, certifications: CERTS, today: TODAY });
  assert.strictEqual(r.status, 'not_met');
  assert.match(r.detail, /2 of 4 \(50%\)/);
});

test('the DENOMINATOR is named on the result and changes the answer', () => {
  // "50% of employees" does not say which employees. Restricted to the crew
  // roles, the pool is e2/e3 and only e2 holds a current card -> 50%.
  const r = pg.evaluateRequirement(
    shareReq({ denominator: 'listed_roles', roles: ['crew'] }),
    { roster: ROSTER, certifications: CERTS, today: TODAY }
  );
  assert.strictEqual(r.denominator, 'listed_roles');
  assert.deepStrictEqual(r.roles, ['crew']);
  assert.strictEqual(r.pool_size, 2);
  assert.strictEqual(r.holders, 1);
  assert.strictEqual(r.actual, 50);
});

test('listed_roles with no roles listed is unusable rather than silently all_active', () => {
  const r = pg.evaluateRequirement(shareReq({ denominator: 'listed_roles', roles: [] }), { roster: ROSTER, certifications: CERTS, today: TODAY });
  assert.strictEqual(r.status, 'unusable');
  assert.match(r.detail, /no roles were listed/);
});

test('an EMPTY pool is unknown, not 100%', () => {
  // Zero over zero must never read as a satisfied share.
  const r = pg.evaluateRequirement(
    shareReq({ denominator: 'listed_roles', roles: ['estimator'] }),
    { roster: ROSTER, certifications: CERTS, today: TODAY }
  );
  assert.strictEqual(r.status, 'unknown');
  assert.strictEqual(r.actual, null);
  assert.match(r.detail, /a share cannot be computed/);
});

test('a computed requirement that names no credential is unusable', () => {
  const r = pg.evaluateRequirement(shareReq({ credential: '' }), { roster: ROSTER, certifications: CERTS, today: TODAY });
  assert.strictEqual(r.status, 'unusable');
});

test('employee_credential_count counts people, not percent', () => {
  const r = pg.evaluateRequirement(
    shareReq({ kind: 'employee_credential_count', threshold: 3 }),
    { roster: ROSTER, certifications: CERTS, today: TODAY }
  );
  assert.strictEqual(r.unit, 'people');
  assert.strictEqual(r.actual, 2);
  assert.strictEqual(r.status, 'not_met');
});

test('attested: a value over the threshold is met, and SAYS it is self-reported', () => {
  const r = pg.evaluateRequirement(attestedReq(), {});
  assert.strictEqual(r.basis, 'attested');
  assert.strictEqual(r.status, 'met');
  assert.match(r.detail, /self-reported, not verified/);
});

test('attested: nothing recorded is unknown, never met', () => {
  const r = pg.evaluateRequirement(attestedReq({ attested_value: undefined }), {});
  assert.strictEqual(r.status, 'unknown');
  assert.match(r.detail, /only you can supply/);
});

test('attested: a value with NO DATE is unknown -- a limit is meaningful only as of a date', () => {
  const r = pg.evaluateRequirement(attestedReq({ attested_on: '' }), {});
  assert.strictEqual(r.status, 'unknown');
  assert.match(r.detail, /without a date/);
});

test('attested: below the threshold is not_met', () => {
  const r = pg.evaluateRequirement(attestedReq({ attested_value: 500000 }), {});
  assert.strictEqual(r.status, 'not_met');
});

test('attested: a non-numeric requirement is checked only for being present and dated', () => {
  const r = pg.evaluateRequirement({
    req_id: 'R9', label: 'Code of ethics signed', kind: 'other',
    attested_value: 'signed', attested_on: '2026-02-02', source: 'programme agreement'
  }, {});
  assert.strictEqual(r.status, 'met');
  assert.match(r.detail, /self-reported/);
});

test('attested: a numeric threshold with a non-numeric value is unknown, not met', () => {
  const r = pg.evaluateRequirement(attestedReq({ attested_value: 'lots' }), {});
  assert.strictEqual(r.status, 'unknown');
});

test('verdict: everything met reads appears_met, NOT "eligible"', () => {
  const r = pg.evaluateProgram({
    program: program({ requirements: [shareReq(), attestedReq()] }),
    roster: ROSTER, certifications: CERTS, today: TODAY
  });
  assert.strictEqual(r.verdict, 'appears_met');
  assert.strictEqual(r.totals.met, 2);
});

test('verdict: one unknown makes the whole thing incomplete, never met', () => {
  const r = pg.evaluateProgram({
    program: program({ requirements: [shareReq(), attestedReq({ attested_value: undefined })] }),
    roster: ROSTER, certifications: CERTS, today: TODAY
  });
  assert.strictEqual(r.verdict, 'incomplete');
});

test('verdict: one not_met outranks any number of unknowns', () => {
  const r = pg.evaluateProgram({
    program: program({ requirements: [shareReq({ threshold: 90 }), attestedReq({ attested_value: undefined })] }),
    roster: ROSTER, certifications: CERTS, today: TODAY
  });
  assert.strictEqual(r.verdict, 'requirements_not_met');
});

test('verdict: an unusable requirement cannot be ignored into a pass', () => {
  const r = pg.evaluateProgram({
    program: program({ requirements: [shareReq(), shareReq({ req_id: 'R3', source: '' })] }),
    roster: ROSTER, certifications: CERTS, today: TODAY
  });
  assert.strictEqual(r.verdict, 'incomplete');
  assert.strictEqual(r.totals.unusable, 1);
});

test('verdict: no requirements entered is its own answer', () => {
  const r = pg.evaluateProgram({ program: program(), roster: ROSTER, certifications: CERTS, today: TODAY });
  assert.strictEqual(r.verdict, 'no_requirements_entered');
});

test('the not-regulatory and self-reported disclosures ride on EVERY result', () => {
  const good = pg.evaluateProgram({ program: program({ requirements: [shareReq()] }), roster: ROSTER, certifications: CERTS, today: TODAY });
  const bad = pg.evaluateProgram({ program: program({ requirements: [shareReq({ threshold: 99 })] }), roster: ROSTER, certifications: CERTS, today: TODAY });
  [good, bad].forEach(function (r) {
    assert.match(r.disclosures.not_regulatory, /voluntary and commercial/);
    assert.match(r.disclosures.thresholds_are_yours, /not verified against TestCo/);
  });
});

test('an all-attested programme says the app verified nothing', () => {
  const r = pg.evaluateProgram({ program: program({ requirements: [attestedReq()] }), roster: ROSTER, certifications: CERTS, today: TODAY });
  assert.strictEqual(r.disclosures.verified_by_app, 'every requirement here is self-reported -- the app verified none of them');
});

test('a mixed programme counts computed vs self-reported separately', () => {
  const r = pg.evaluateProgram({ program: program({ requirements: [shareReq(), attestedReq()] }), roster: ROSTER, certifications: CERTS, today: TODAY });
  assert.strictEqual(r.totals.computed, 1);
  assert.strictEqual(r.totals.attested, 1);
  assert.match(r.disclosures.verified_by_app, /1 requirement\(s\) computed/);
});

test('renewal: a held credential whose expiry has passed reads lapsed_by_date', () => {
  // These programmes are recurring, not one-time badges. A stored status of
  // 'held' must not outrank a date that has gone by.
  const r = pg.evaluateProgram({
    program: program({ standing: { status: 'held', obtained_on: '2020-01-01', expires_on: '2026-01-01' } }),
    roster: ROSTER, certifications: CERTS, today: TODAY
  });
  assert.strictEqual(r.standing.status, 'held');
  assert.strictEqual(r.renewal.status, 'lapsed_by_date');
  assert.ok(r.renewal.days < 0);
});

test('renewal: inside the warning window reads expiring', () => {
  const r = pg.evaluateProgram({
    program: program({ standing: { status: 'held', expires_on: '2026-09-10' } }),
    roster: ROSTER, certifications: CERTS, today: TODAY
  });
  assert.strictEqual(r.renewal.status, 'expiring');
  assert.strictEqual(r.renewal.days, 16);
});

test('renewal: held with no expiry date recorded is unknown, not current', () => {
  const r = pg.evaluateProgram({
    program: program({ standing: { status: 'held' } }),
    roster: ROSTER, certifications: CERTS, today: TODAY
  });
  assert.strictEqual(r.renewal.status, 'unknown');
});

test('renewal: an explicit no-expiry programme is an answer, not a blank', () => {
  const r = pg.evaluateProgram({
    program: program({ standing: { status: 'held', has_expiry: false } }),
    roster: ROSTER, certifications: CERTS, today: TODAY
  });
  assert.strictEqual(r.renewal.status, 'no_expiry');
});

test('renewal is not_applicable when the company does not hold the programme', () => {
  const r = pg.evaluateProgram({
    program: program({ standing: { status: 'in_progress' } }),
    roster: ROSTER, certifications: CERTS, today: TODAY
  });
  assert.strictEqual(r.renewal.status, 'not_applicable');
});

test('validateProgram demands a manufacturer and a programme name', () => {
  const p = pg.validateProgram({ id: 'PRG-1' });
  assert.ok(p.some((x) => /manufacturer/.test(x)));
  assert.ok(p.some((x) => /program_name/.test(x)));
  assert.deepStrictEqual(pg.validateProgram({ id: 'P', manufacturer: 'M', program_name: 'N' }), []);
});

test('validateProgram refuses an unknown standing status', () => {
  assert.ok(pg.validateProgram({ id: 'P', manufacturer: 'M', program_name: 'N', status: 'certified-ish' }).length);
});

test('the vocabularies are closed', () => {
  assert.deepStrictEqual(pg.PROGRAM_STATUSES, ['not_enrolled', 'in_progress', 'held', 'lapsed']);
  assert.deepStrictEqual(pg.COMPUTED_KINDS, ['employee_credential_share', 'employee_credential_count']);
  assert.deepStrictEqual(pg.DENOMINATORS, ['all_active', 'listed_roles']);
});
