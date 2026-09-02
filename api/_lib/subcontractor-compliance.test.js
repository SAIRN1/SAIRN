// api/_lib/subcontractor-compliance.test.js
// Plain node:assert tests -- no framework, matching api/'s zero-npm-dependency
// convention (see api/_lib/auth.test.js, dental-photo-validation.test.js).
// Run: node api/_lib/subcontractor-compliance.test.js

const assert = require('assert');
const s = require('./subcontractor-compliance');

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

console.log('api/_lib/subcontractor-compliance.js');

const TODAY = '2026-09-02';

// ── documentState ──────────────────────────────────────────────────────────

test('missing and expired are DIFFERENT states, not one "not ok"', () => {
  assert.strictEqual(s.documentState(null, TODAY).state, 'missing');
  assert.strictEqual(s.documentState('2026-08-01', TODAY).state, 'expired');
});

test('expiring is bounded by the warn window and valid is beyond it', () => {
  assert.strictEqual(s.documentState('2026-09-20', TODAY).state, 'expiring');   // 18 days
  assert.strictEqual(s.documentState('2026-12-01', TODAY).state, 'valid');
});

test('the warn window is caller-overridable', () => {
  assert.strictEqual(s.documentState('2026-12-01', TODAY, 200).state, 'expiring');
});

test('expiring TODAY is expiring, not expired -- the boundary is inclusive', () => {
  const d = s.documentState(TODAY, TODAY);
  assert.strictEqual(d.state, 'expiring');
  assert.strictEqual(d.days_left, 0);
});

test('a garbled date is UNREADABLE, never silently valid', () => {
  assert.strictEqual(s.documentState('soon', TODAY).state, 'unreadable');
  assert.strictEqual(s.documentState('2026-13-45', TODAY).state, 'unreadable');
});

// ── evaluateSubcontractor ──────────────────────────────────────────────────

test('it REFUSES to assume a clock', () => {
  const r = s.evaluateSubcontractor({ subcontractor: { sub_id: 'S1' } });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.error.code, 'NO_TODAY');
});

test('no subcontractor is an explicit error, not an empty pass', () => {
  const r = s.evaluateSubcontractor({ today: TODAY });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.error.code, 'NO_SUBCONTRACTOR');
});

test('w9 is boolean, not a date, and missing means missing', () => {
  const r = s.evaluateSubcontractor({ today: TODAY, subcontractor: { sub_id: 'S1' } });
  assert.strictEqual(r.documents.w9.state, 'missing');
  const r2 = s.evaluateSubcontractor({ today: TODAY, subcontractor: { sub_id: 'S1', w9_on_file: true } });
  assert.strictEqual(r2.documents.w9.state, 'valid');
});

test('an expired document only BLOCKS when the operator requires it', () => {
  const sub = { sub_id: 'S1', coi_expiry: '2026-01-01' };
  const notRequired = s.evaluateSubcontractor({ today: TODAY, subcontractor: sub });
  assert.deepStrictEqual(notRequired.blocking, []);
  assert.strictEqual(notRequired.compliant, true);
  // ...but it is still REPORTED. Silence would be the wrong kind of quiet.
  assert.ok(notRequired.warnings.indexOf('coi') !== -1);

  const required = s.evaluateSubcontractor({ today: TODAY, subcontractor: sub, required: ['coi'] });
  assert.deepStrictEqual(required.blocking, ['coi']);
  assert.strictEqual(required.compliant, false);
});

test('an unrecognised requirement is surfaced and treated as UNMET', () => {
  const r = s.evaluateSubcontractor({
    today: TODAY, subcontractor: { sub_id: 'S1', w9_on_file: true }, required: ['w9', 'bond']
  });
  assert.deepStrictEqual(r.unknown_requirements, ['bond']);
  assert.strictEqual(r.compliant, false, 'a typo in a policy list must not read as satisfied');
});

// ── canAssign ──────────────────────────────────────────────────────────────

test('a fully-papered but INACTIVE sub is compliant and still cannot be assigned', () => {
  const sub = { sub_id: 'S1', active: false, w9_on_file: true, coi_expiry: '2027-01-01' };
  const ev = s.evaluateSubcontractor({ today: TODAY, subcontractor: sub, required: ['coi', 'w9'] });
  assert.strictEqual(ev.compliant, true);
  const a = s.canAssign({ today: TODAY, subcontractor: sub, required: ['coi', 'w9'] });
  assert.strictEqual(a.allowed, false);
  assert.ok(a.reasons.some(r => /not active/.test(r)));
});

test('assignment refusal names every reason, not just the first', () => {
  const a = s.canAssign({
    today: TODAY,
    subcontractor: { sub_id: 'S1', active: false, coi_expiry: '2026-01-01' },
    required: ['coi', 'w9']
  });
  assert.strictEqual(a.allowed, false);
  assert.strictEqual(a.reasons.length, 3, a.reasons.join(' | '));
});

test('a compliant active sub is allowed, and the evaluation rides along', () => {
  const a = s.canAssign({
    today: TODAY,
    subcontractor: { sub_id: 'S1', w9_on_file: true, coi_expiry: '2027-01-01', licence_expiry: '2027-06-01' },
    required: ['coi', 'licence', 'w9']
  });
  assert.strictEqual(a.allowed, true);
  assert.deepStrictEqual(a.reasons, []);
  assert.strictEqual(a.evaluation.documents.licence.state, 'valid');
});

// ── summariseAssignment ────────────────────────────────────────────────────

test('outstanding is DERIVED from recorded payments, never stored', () => {
  const r = s.summariseAssignment({
    assignment_id: 'A1', amount: 1000, status: 'complete',
    payments: [{ amount: 400 }, { amount: 250 }]
  });
  assert.strictEqual(r.paid, 650);
  assert.strictEqual(r.outstanding, 350);
  assert.strictEqual(r.payment_status, 'part_paid');
});

test('a fully paid assignment reads paid, and overpayment is surfaced not hidden', () => {
  assert.strictEqual(s.summariseAssignment({ amount: 500, payments: [{ amount: 500 }] }).payment_status, 'paid');
  const over = s.summariseAssignment({ amount: 500, payments: [{ amount: 600 }] });
  assert.strictEqual(over.outstanding, 0);
  assert.strictEqual(over.overpaid, 100, 'a duplicated payment is a real condition worth showing');
});

test('no amount agreed reads unbilled, not paid', () => {
  assert.strictEqual(s.summariseAssignment({ amount: 0 }).payment_status, 'unbilled');
});

test('an unrecognised status becomes null WITH a problem, never passed through', () => {
  const r = s.summariseAssignment({ status: 'donezo', amount: 100 });
  assert.strictEqual(r.status, null);
  assert.ok(/unrecognised status/.test(r.problems[0]));
});

test('a garbled scheduled_date is null, not echoed back as if real', () => {
  assert.strictEqual(s.summariseAssignment({ scheduled_date: 'tomorrow' }).scheduled_date, null);
});

test('non-numeric payment amounts are ignored rather than producing NaN', () => {
  const r = s.summariseAssignment({ amount: 100, payments: [{ amount: '50' }, { amount: 25 }] });
  assert.strictEqual(r.paid, 25);
  assert.strictEqual(r.outstanding, 75);
});

console.log(passed + ' passed');
