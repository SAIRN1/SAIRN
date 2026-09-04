// tests/roofing_claim_gate_single_source.js
//
// Run:  node tests/roofing_claim_gate_single_source.js
//
// The SAIRNroofing claim assignment gate was hand-written at six branches of
// api/sd-data.js: claim photo read, claim photo write, assess, reconcile, the
// job gate, and rfClaimGate itself -- plus a seventh spelling on the rf_claims
// write path. api/rf-auth.js's own header names duplicated role logic as
// SAIRNsenior's root cause.
//
// This test does two things a reviewer cannot do by eye:
//
//   1. proves rfAuth.ownsRow() answers IDENTICALLY to the expression it
//      replaced, over every combination of role, assignee and missing row --
//      the retrofit is only safe if it is a substitution, not a rewrite;
//   2. asserts the hand-written form has not come back.
//
// It does NOT assert the six branches respond the same way to each other. They
// deliberately do not: a read degrades to an empty list, a write refuses
// loudly, and unifying those would be a behaviour change dressed up as a
// refactor. Only the PREDICATE is shared.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
const rfAuth = require(path.join(ROOT, 'api', 'rf-auth.js'));
const src = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// The exact expression that used to sit at each site.
function legacyDenies(session, row) {
  return !rfAuth.MANAGEMENT_ROLES[session.role]
      && !rfAuth.BROAD_READ_ROLES[session.role]
      && row.assigned_employee_id !== session.employee_id;
}

const ROLES = ['owner', 'admin', 'estimator', 'foreman', 'crew', 'sales', '', 'unknown-role'];
const EMPLOYEES = ['E1', 'E2'];
const ROWS = [
  { label: 'assigned to E1', row: { assigned_employee_id: 'E1' } },
  { label: 'assigned to E2', row: { assigned_employee_id: 'E2' } },
  { label: 'unassigned (null)', row: { assigned_employee_id: null } },
  { label: 'unassigned (absent)', row: {} },
];

// ---------------------------------------------------------------------------
section('ownsRow() is the same answer as the expression it replaced');

test('every role x employee x row combination agrees', () => {
  let checked = 0;
  ROLES.forEach((role) => EMPLOYEES.forEach((emp) => ROWS.forEach((r) => {
    const session = { role: role, employee_id: emp };
    const legacy = !legacyDenies(session, r.row);   // legacy DENIES; ownsRow ALLOWS
    const now = rfAuth.ownsRow(session, r.row);
    assert.strictEqual(now, legacy,
      'disagree for role=' + JSON.stringify(role) + ' emp=' + emp + ' row=' + r.label +
      ' (legacy allowed=' + legacy + ', ownsRow=' + now + ')');
    checked++;
  })));
  assert.strictEqual(checked, ROLES.length * EMPLOYEES.length * ROWS.length);
  console.log('       (' + checked + ' combinations)');
});

test('THE CASE THE OLD rf_claims WRITE HANDLED BY HAND: a missing row denies', () => {
  // That branch read `if (!existing || existing.assigned !== emp)`. ownsRow has
  // to reproduce the `!existing` half or an unassigned claim becomes writable
  // by anyone narrow.
  const narrow = { role: 'foreman', employee_id: 'E1' };
  assert.strictEqual(rfAuth.ownsRow(narrow, undefined), false);
  assert.strictEqual(rfAuth.ownsRow(narrow, null), false);
  assert.strictEqual(rfAuth.ownsRow(narrow, false), false);   // PostgREST rows[0] on empty
});

test('...but a broad reader still passes with no row at all', () => {
  assert.strictEqual(rfAuth.ownsRow({ role: 'estimator', employee_id: 'E9' }, false), true);
});

test('a missing session is denied rather than throwing', () => {
  assert.strictEqual(rfAuth.ownsRow(null, { assigned_employee_id: 'E1' }), false);
  assert.strictEqual(rfAuth.seesAllRows(null), false);
});

test('seesAllRows matches the role half exactly', () => {
  ROLES.forEach((role) => {
    const s = { role: role, employee_id: 'E1' };
    const legacy = !!(rfAuth.MANAGEMENT_ROLES[role] || rfAuth.BROAD_READ_ROLES[role]);
    assert.strictEqual(rfAuth.seesAllRows(s), legacy, 'role ' + JSON.stringify(role));
  });
});

// ---------------------------------------------------------------------------
section('the role sets, and the redundancy that hides a future bug');

test('seesAllRows keeps BOTH terms, which no behavioural test can check today', () => {
  // Deleting the MANAGEMENT term is a no-op right now -- that is precisely why
  // it needs a structural assertion. A negative control that removed it passed
  // every behavioural arm in this file, because today the two sets overlap.
  // The term is kept for the day they do not, so the guard has to be about the
  // SOURCE, not the answer.
  const authSrc = fs.readFileSync(path.join(ROOT, 'api', 'rf-auth.js'), 'utf8');
  const i = authSrc.indexOf('function seesAllRows(session)');
  assert.ok(i > 0, 'seesAllRows not found');
  const body = authSrc.slice(i, authSrc.indexOf('\n}', i)).replace(/\/\/[^\n]*/g, '');
  assert.match(body, /MANAGEMENT_ROLES\[session\.role\]/,
    'the MANAGEMENT term was dropped from seesAllRows. It is redundant today and '
    + 'will not be the moment a management role is added that is not a broad reader.');
  assert.match(body, /BROAD_READ_ROLES\[session\.role\]/);
});

test('MANAGEMENT_ROLES is currently a SUBSET of BROAD_READ_ROLES', () => {
  // Recorded as a test rather than a comment because it is the reason both
  // terms are kept. If someone adds a management role that is not a broad
  // reader, this fails -- and that is the moment to check every call site whose
  // comment says "management or broad" actually still means it.
  const mgmt = Object.keys(rfAuth.MANAGEMENT_ROLES);
  const broad = new Set(Object.keys(rfAuth.BROAD_READ_ROLES));
  const outside = mgmt.filter((r) => !broad.has(r));
  assert.deepStrictEqual(outside, [],
    'a management role is no longer a broad reader: ' + outside.join(', ') +
    '. ownsRow/seesAllRows keep BOTH terms so this stays correct -- but every ' +
    'sd-data.js branch still spelling the role test by hand must be re-read.');
});

// ---------------------------------------------------------------------------
section('the hand-written gate has not come back');

test('no branch spells the assignment predicate itself any more', () => {
  const code = src.replace(/\/\/[^\n]*/g, '');   // comments discuss it on purpose
  const hand = code.match(/MANAGEMENT_ROLES\[session\.role\][^\n]*assigned_employee_id !== session\.employee_id/g) || [];
  assert.deepStrictEqual(hand, [],
    'the assignment gate is hand-written again at ' + hand.length + ' site(s)');
});

test('all six claim/job gates go through ownsRow', () => {
  const uses = src.match(/rfAuth\.ownsRow\(session, (claim|job|existing)\)/g) || [];
  assert.ok(uses.length >= 7,
    'expected at least 7 ownsRow call sites, found ' + uses.length + ': ' + uses.join(', '));
});

test('the rf_claims write path no longer keeps its own role booleans', () => {
  const i = src.indexOf("resource === 'rf_claims' && action === 'write'");
  assert.ok(i > 0, 'could not find the rf_claims write branch');
  const block = src.slice(i, i + 2600).replace(/\/\/[^\n]*/g, '');
  assert.ok(!/const isManagement =/.test(block), 'isManagement is back');
  assert.ok(!/const isBroad =/.test(block), 'isBroad is back');
  assert.match(block, /rfAuth\.seesAllRows\(session\)/);
});

// ---------------------------------------------------------------------------
section('what was deliberately NOT unified');

test('each branch keeps its own not-provisioned policy', () => {
  // A read degrading to an empty list and a write refusing with 503 are both
  // correct and are not the same answer. If a later change makes them
  // identical, that is a decision to make on purpose, not a side effect.
  assert.match(src, /rf_claim_photos read requires payload\.claim_id/);
  const photoRead = src.slice(src.indexOf("resource === 'rf_claim_photos' && action === 'read'"));
  assert.match(photoRead.slice(0, 1400), /ok: true, data: \[\], provisioned: false/,
    'the photo READ no longer degrades to an empty list');
  const photoWrite = src.slice(src.indexOf("resource === 'rf_claim_photos' && action === 'write'"));
  assert.match(photoWrite.slice(0, 1400), /NOT_PROVISIONED/,
    'the photo WRITE no longer refuses loudly');
});

test('the fifteen ROLE-ONLY sites are still there and still counted', () => {
  // Out of scope for this change and recorded in the open-work index. The count
  // is asserted so the row cannot quietly go stale the way "four ways" did --
  // it was 21 when someone finally counted.
  const code = src.replace(/\/\/[^\n]*/g, '');
  const roleOnly = code.match(/!rfAuth\.MANAGEMENT_ROLES\[session\.role\] && !rfAuth\.BROAD_READ_ROLES\[session\.role\]/g) || [];
  assert.strictEqual(roleOnly.length, 15,
    'the role-only count moved to ' + roleOnly.length + ' -- update the index row, or sweep them');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' CLAIM-GATE ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
