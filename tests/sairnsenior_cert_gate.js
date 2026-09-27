// tests/sairnsenior_cert_gate.js
//
// Run:  node tests/sairnsenior_cert_gate.js
//
// A CAREGIVER WITH AN EXPIRED CPR COULD BE ASSIGNED TO A CLIENT, AND THE APP
// ALREADY KNEW.
//
// `cpr_expiry` is stored per caregiver, `certDaysUntil()` computes the days, and
// `rCaregivers()` renders a red **Expired** badge for that same person. Three
// write paths -- `saveClient()`, `senReassignClient()` and `saveVisit()` --
// assigned them anyway. Two screens, two answers, no disagreement flagged.
//
// ── THE THING THAT MAKES THIS GATE HARD, AND WHAT THE ARMS ARE FOR ────────
//
// THE TWO RECORDS WERE NEVER JOINED. `assigned_employee_id` is an `employee_id`
// out of SAIRNbiz's roster; a `sen_caregivers` row is keyed `CG-...` with a
// `name`. Matching on NAME was the obvious shortcut and is worse than no gate at
// all: a roster display name differing by a middle initial, a married name or
// Bob-for-Robert produces NO MATCH, and a no-match gate PASSES -- silently, on
// exactly the person it exists to stop. Arm D1 asserts the gate does not read
// `name` at all, because that is the shortcut a later edit would reach for.
//
// SO A LINK FIELD WAS ADDED, and the price is a third state. An unlinked
// caregiver is COULD-NOT-CHECK, never OK:
//   * it does NOT block -- blocking on could-not-tell would make every existing
//     install unusable until somebody migrated its data, a bigger harm than the
//     one being fixed;
//   * it DOES speak, on every single save, naming which record could not be
//     reached. Arms B3/B4/C4 hold that, because an allow that is silent about
//     why is the state this whole gate exists to remove.
//
// AND THE BLOCK IS A DECISION, NOT A DEFAULT. api/_lib/mech-credentials.js
// argues the opposite for its own case -- "WHAT THIS IS NOT: a gate. Nothing
// here refuses a dispatch" -- because a mechanical dispatcher covering an
// emergency should not be stopped by a lapsed certificate. Michael's call here is
// the opposite and the suite holds the refusal rather than a warning.
//
// Set SEN_HTML to a mutated copy for a negative control.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(process.env.SEN_HTML
  || path.join(__dirname, '..', 'sairnsenior.html'), 'utf8')
  .replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in sairnsenior.html: ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

const { stripComments } = require('./lib/strip_comments.js');
// Shared, because three suites grew three versions in one day and all three
// were wrong differently -- see that module's header. The naive inline version
// this replaces treated `/*` as a comment start anywhere, so
// `accept="image/*"` opened a block comment that swallowed the rest of the
// file and arm E1 failed against correct markup.
const codeOnly = stripComments(html);

const TODAY = '2026-09-26';

function gateCtx(cgRows) {
  const src = [
    grab('function certDaysUntil(d){', '\n'),
    grab('function senCertGate(employeeId){', '\n}'),
    grab('function senCertGateMessage(g){', '\n}')
  ].join('\n\n');
  const ctx = {
    Object, Array, String, Number, Math, Date, JSON, isFinite,
    caregivers: () => cgRows,
    senEmployeeName: (id) => 'Employee ' + id,
    senLocalToday: () => TODAY,
    console: { log() {}, warn() {} }
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(src, ctx, { filename: 'sairnsenior-certgate-extract.js' });
  return ctx;
}
function gate(rows, id) { return gateCtx(rows).senCertGate(id); }
function msg(rows, id) { const c = gateCtx(rows); return c.senCertGateMessage(c.senCertGate(id)); }

const OK = { id: 'CG-1', name: 'Rosa Alvarez', employee_id: 'E100', cpr_expiry: '2027-06-01' };
const EXPIRED = { id: 'CG-2', name: 'Dan Okafor', employee_id: 'E200', cpr_expiry: '2026-09-01' };
const SOON = { id: 'CG-3', name: 'Mei Tan', employee_id: 'E300', cpr_expiry: '2026-10-10' };
const NODATE = { id: 'CG-4', name: 'Jo Rivers', employee_id: 'E400', cpr_expiry: '' };
const UNLINKED = { id: 'CG-5', name: 'Sam Reid', cpr_expiry: '2020-01-01' };   // no employee_id
const ROWS = [OK, EXPIRED, SOON, NODATE, UNLINKED];

console.log('SAIRNsenior -- an expired CPR refuses the assignment, and an unlinked record says so');

// ── A. THE BLOCKING STATES ───────────────────────────────────────────────
section('A. expired refuses, and the refusal is actionable');
test('A1. an EXPIRED certificate blocks', () => {
  const g = gate(ROWS, 'E200');
  assert.strictEqual(g.state, 'expired');
  assert.strictEqual(g.days, 25, 'expected 25 days past 2026-09-01 on ' + TODAY + ', got ' + g.days);
  const m = msg(ROWS, 'E200');
  assert.strictEqual(m.block, true, 'an expired CPR did not block the assignment');
  assert.ok(/REFUSED/.test(m.msg) && /2026-09-01/.test(m.msg) && /25 days ago/.test(m.msg),
    'the refusal does not carry the date AND the day count, so it is not actionable '
    + 'in the same breath: ' + m.msg);
  assert.ok(/Nothing was saved/.test(m.msg),
    'the refusal does not say nothing was saved -- a user cannot tell a refusal '
    + 'from a silent failure');
});
test('A2. TWO caregiver records for one employee blocks -- array order must not decide', () => {
  const dup = ROWS.concat([{ id: 'CG-9', name: 'Dan O.', employee_id: 'E200', cpr_expiry: '2028-01-01' }]);
  const g = gate(dup, 'E200');
  assert.strictEqual(g.state, 'ambiguous',
    'with two linked records the gate picked one, which makes the answer depend on '
    + 'array order -- and the second row here would turn an expired cert into a valid one');
  assert.strictEqual(msg(dup, 'E200').block, true);
});

// ── B. THE COULD-NOT-CHECK STATES ────────────────────────────────────────
section('B. could-not-check allows, and is never silent');
test('B1. an UNLINKED employee is `unlinked`, not ok', () => {
  assert.strictEqual(gate(ROWS, 'E999').state, 'unlinked');
});
test('B2. ...and it does NOT block', () => {
  assert.strictEqual(msg(ROWS, 'E999').block, false,
    'blocking on could-not-tell would make every install with unmigrated caregiver '
    + 'data unusable, which is a bigger harm than the one being fixed');
});
test('B3. ...and it SAYS SO, naming what to do', () => {
  const m = msg(ROWS, 'E999');
  assert.ok(/NOT CHECKED/.test(m.msg), 'the allow is silent: ' + JSON.stringify(m.msg));
  assert.ok(/Linked employee/.test(m.msg),
    'it does not name the field that fixes it: ' + m.msg);
  assert.ok(/Saved anyway/.test(m.msg), 'it does not say the save went through');
});
test('B4. a MISSING CPR DATE is not a current certificate, and says that', () => {
  assert.strictEqual(gate(ROWS, 'E400').state, 'no_date');
  const m = msg(ROWS, 'E400');
  assert.strictEqual(m.block, false);
  assert.ok(/NOT CHECKED/.test(m.msg));
  assert.ok(/absent date is not a current certificate/i.test(m.msg),
    'an absent date must not read as a pass: ' + m.msg);
});

// ── C. THE PASSING STATES ────────────────────────────────────────────────
section('C. current passes quietly, expiring passes loudly');
test('C1. a current certificate passes with NOTHING to say', () => {
  const g = gate(ROWS, 'E100');
  assert.strictEqual(g.state, 'ok');
  const m = msg(ROWS, 'E100');
  assert.strictEqual(m.block, false);
  assert.strictEqual(m.msg, '',
    'a current certificate produced a message. A reassuring line on every normal '
    + 'assignment is how the genuinely-wrong ones stop standing out');
});
test('C2. an EXPIRING certificate passes and names the days', () => {
  const g = gate(ROWS, 'E300');
  assert.strictEqual(g.state, 'expiring');
  assert.strictEqual(g.days, 14);
  const m = msg(ROWS, 'E300');
  assert.strictEqual(m.block, false, 'expiring must not block -- the certificate is still valid');
  assert.ok(/14 days/.test(m.msg) && /2026-10-10/.test(m.msg), m.msg);
});
test('C3. NO employee assigned is not a certificate problem', () => {
  assert.strictEqual(gate(ROWS, '').state, 'unassigned');
  const m = msg(ROWS, '');
  assert.strictEqual(m.block, false);
  assert.strictEqual(m.msg, '', 'leaving a client unassigned produced a cert message: ' + m.msg);
});
test('C4. the boundary: 0 days left is still valid, -1 is expired', () => {
  const zero = [{ id: 'CG-Z', name: 'Z', employee_id: 'EZ', cpr_expiry: TODAY }];
  assert.strictEqual(gate(zero, 'EZ').state, 'expiring',
    'a certificate expiring TODAY must not read as already expired');
  const minus = [{ id: 'CG-M', name: 'M', employee_id: 'EM', cpr_expiry: '2026-09-25' }];
  assert.strictEqual(gate(minus, 'EM').state, 'expired',
    'yesterday must read as expired -- an off-by-one here lets one more day through');
});

// ── D. THE JOIN, AND WHERE THE GATE IS CALLED ────────────────────────────
section('D. resolved by employee_id, called on all three write paths');
test('D1. THE GATE DOES NOT MATCH ON NAME', () => {
  const g = grab('function senCertGate(employeeId){', '\n}');
  assert.ok(/employee_id/.test(g), 'the gate does not resolve by employee_id');
  assert.ok(!/\.name\s*===|\.name\s*==|name\s*===\s*sen|display_name/.test(g),
    'the gate compares a NAME somewhere. A name join produces no match -- and '
    + 'therefore a silent PASS -- on exactly the mismatched record it exists to '
    + 'catch:\n' + g);
});
test('D2. all three assignment paths call the gate and RETURN on a block', () => {
  [['async function saveClient', 'saveClient'],
   ['async function senReassignClient', 'senReassignClient'],
   ['async function saveVisit', 'saveVisit']].forEach(([sig, name]) => {
    const fn = grab(sig, '\n}');
    assert.ok(/senCertGateMessage\(senCertGate\(/.test(fn),
      name + ' does not call the gate');
    assert.ok(/\.block\)\s*\{\s*toast\([^)]*\);\s*return;/.test(fn.replace(/\n/g, '')),
      name + ' calls the gate and does not return on a block, so the refusal is '
      + 'advisory and the write happens anyway');
  });
});
test('D3. the gate runs BEFORE anything is written, on all three', () => {
  [['async function saveClient', 'st(\'sen_clients\''],
   ['async function senReassignClient', 'st(\'sen_clients\''],
   ['async function saveVisit', 'st(\'sen_visits\'']].forEach(([sig, writeCall]) => {
    const fn = grab(sig, '\n}');
    const g = fn.indexOf('senCertGate(');
    const w = fn.indexOf(writeCall);
    assert.ok(g > 0 && w > 0, sig + ': could not locate both the gate and the write');
    assert.ok(g < w,
      sig + ' writes before it checks, so a refusal leaves a record behind');
  });
});
test('D4. the could-not-check message reaches the user on all three', () => {
  const n = (codeOnly.match(/\.msg\?'\s*'\+/g) || []).length
          + (codeOnly.match(/\+\(_?\w*g\.msg\?' '\+\w*g\.msg:''\)/g) || []).length;
  assert.ok(n >= 3,
    'the could-not-check text is appended to ' + n + ' success toast(s); all three '
    + 'assignment paths need it, or one of them allows silently');
});
test('D5. REACHABILITY: the gate and all three callers are in ONE script block', () => {
  const blocks = [];
  const re = /<script[^>]*>/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    const start = m.index + m[0].length;
    const end = html.indexOf('</script>', start);
    blocks.push([start, end === -1 ? html.length : end]);
  }
  const blockOf = i => blocks.findIndex(([a, b]) => i >= a && i < b);
  const def = blockOf(html.indexOf('function senCertGate(employeeId){'));
  assert.ok(def >= 0, 'the gate is outside every script block');
  ['async function saveClient', 'async function senReassignClient', 'async function saveVisit']
    .forEach(sig => assert.strictEqual(blockOf(html.indexOf(sig)), def,
      sig + ' is in a different script block from the gate -- declarations do not '
      + 'hoist across blocks, so this is a ReferenceError at run time'));
});

// ── E. THE LINK FIELD ────────────────────────────────────────────────────
section('E. the link is stored, offered, and never silently cleared');
test('E1. the caregiver modal offers a Linked employee select', () => {
  assert.ok(/id="cg-employee"/.test(codeOnly), 'no cg-employee control exists');
  assert.ok(/Not linked/.test(codeOnly), 'the select has no explicit not-linked option');
});
test('E2. saveCaregiver persists employee_id', () => {
  const fn = grab('async function saveCaregiver(){', '\n}');
  assert.ok(/employee_id:\(\$\('cg-employee'\)/.test(fn),
    'the link is offered and not saved: ' + fn.slice(0, 400));
});
test('E3. a stored link NOT on the current roster is KEPT as an option', () => {
  const fn = grab('function senPopulateCaregiverEmployee(cur){', '\n}');
  assert.ok(/not on the current roster/.test(fn),
    'a stored employee_id missing from the roster would be silently dropped by the '
    + 'select, turning a CHECKED caregiver into an unchecked one -- the direction '
    + 'that must never happen quietly');
});

console.log('\n' + (fail ? 'FAIL' : 'ALL') + ' -- ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
