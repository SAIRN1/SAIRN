// api/sd-data-sf-session-gate.test.js
// Run: node api/sd-data-sf-session-gate.test.js
//
// ELEVEN SAIRNfreedom RESOURCES REQUIRE AN EMPLOYEE SESSION. Three were armed
// 2026-09-21 (sf_accounts, sf_ledger, sf_vendor_prices); eight more on
// 2026-09-22, after hover2 audited all 35 and Michael made the call.
//
// ── WHAT THE EIGHT CARRY, because a gate with no recorded reason is the next
//    session's mystery and this suite is where a reader will look ───────────
//   sf_operators            name + DOB + a FELONY flag and a GAMBLING
//                           disqualification flag -- a criminal-history
//                           assertion about a named volunteer, and the single
//                           most sensitive field the audit found
//   sf_gaming_expenses      payee name + amount, ORC 2915.10(A)(2) and (C)
//   sf_disbursements        the giving side of the same statute
//   sf_donations            donor name + amount
//   sf_youth_participants   MINORS
//   sf_staff                DOB, which the app age-gates off
//   sf_waivers              health and military-status disclosure
//   sf_service_appointments a member tied to a VA-adjacent referral outcome
//
// ── THIS SUITE ASSERTS THE TWO LISTS AGREE, NOT WHAT EITHER CONTAINS ───────
// SD_SESSION_GATED says a resource needs a session. A SECOND map says which
// APP's session counts. The file's own comment records what happens when they
// disagree: expectedApp resolves to 'stonedesk' by default and every correctly
// signed-in caller is refused with FORBIDDEN "sign in first" -- it fails CLOSED
// and CONFUSINGLY, which is the hardest failure to read and the one that gets
// a security change reverted as "broken" rather than fixed.
//
// So the load-bearing assertion here is set equality between the two maps.
// Asserting a hardcoded list of eleven names instead would go stale the next
// time anyone gates a twelfth, and would pass while the second map was
// forgotten -- which is the actual defect.
//
// ── WHAT THIS SUITE CANNOT TELL YOU, said here rather than left to be assumed
// It reads SOURCE. It does not prove a live call is refused. As of 2026-09-22
// sql/sairnfreedom_employee_auth_schema.sql has NOT been run against the live
// database -- /api/sf-auth login answers 503 NOT_PROVISIONED -- so NO real
// caller can hold a session, every gated resource answers 403, and the other
// half of live verification (a real session PASSING the gate) is not merely
// unrun, it is IMPOSSIBLE until that file is run. A suite that said "gated,
// verified" today would be claiming the half nobody can drive.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

let passed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

const SRC_PATH = path.join(__dirname, 'sd-data.js');
let SRC;
try {
  SRC = fs.readFileSync(SRC_PATH, 'utf8').replace(/\r\n/g, '\n');
} catch (e) {
  // FAIL CLOSED. PR 1.11 -- a check that cannot read its subject did not run,
  // and "did not run" is a third state that is never folded into "passed".
  console.error('COULD NOT RUN: ' + SRC_PATH + ' is unreadable (' + e.code + ').');
  console.error('  Nothing below was checked. This is NOT a pass.');
  process.exit(2);
}
// Comment lines blanked before any scan: the block above this change quotes
// both lists to explain them, and a raw file-wide match counts that prose as
// code. Same trap api/alf-append-only-fail-closed.test.js already records.
const CODE = SRC.split('\n')
  .map((l) => (/^\s*(\/\/|\*|\/\*)/.test(l) ? '' : l)).join('\n');

const EIGHT_ADDED = [
  'sf_disbursements', 'sf_donations', 'sf_gaming_expenses', 'sf_operators',
  'sf_service_appointments', 'sf_staff', 'sf_waivers', 'sf_youth_participants',
];
const THREE_PRIOR = ['sf_accounts', 'sf_ledger', 'sf_vendor_prices'];

function gatedSet() {
  return new Set((CODE.match(/'(sf_\w+)':\s*\['read', 'write'\]/g) || [])
    .map((s) => s.match(/'(sf_\w+)'/)[1]));
}
function expectedAppSet() {
  return new Set((CODE.match(/'(sf_\w+)': 'sairnfreedom'/g) || [])
    .map((s) => s.match(/'(sf_\w+)'/)[1]));
}

function main() {
  console.log('SAIRNfreedom session gate: two lists that must agree, and a third state');

  test('the gated list was actually parsed -- a zero-length scan would make ' +
       'every set assertion below vacuously true', () => {
    assert.ok(gatedSet().size >= 11,
      'expected at least the 11 known gated sf_ resources, parsed ' +
      gatedSet().size + '. A regex that matched nothing passes set equality ' +
      'against another empty set, which is a green run over no data.');
  });

  test('every one of the eight added 2026-09-22 requires a session on BOTH verbs', () => {
    const g = gatedSet();
    const missing = EIGHT_ADDED.filter((r) => !g.has(r));
    assert.deepStrictEqual(missing, [],
      'ungated: ' + missing.join(', ') + ' -- these carry minors\' names, a ' +
      'felony flag, or an ORC 2915 payee record.');
  });

  test('...and the three armed 2026-09-21 were not disturbed', () => {
    const g = gatedSet();
    const missing = THREE_PRIOR.filter((r) => !g.has(r));
    assert.deepStrictEqual(missing, [],
      'a previously gated resource lost its gate: ' + missing.join(', '));
  });

  test('THE LOAD-BEARING ONE: the gated list and the expectedApp list are the ' +
       'SAME SET', () => {
    const g = [...gatedSet()].sort();
    const e = [...expectedAppSet()].sort();
    const gatedOnly = g.filter((r) => !e.includes(r));
    const appOnly = e.filter((r) => !g.includes(r));
    assert.deepStrictEqual(
      { gatedButNoExpectedApp: gatedOnly, expectedAppButNotGated: appOnly },
      { gatedButNoExpectedApp: [], expectedAppButNotGated: [] },
      'the two maps disagree. A resource gated with no expectedApp entry ' +
      'resolves to \'stonedesk\' and refuses every correctly signed-in ' +
      'SAIRNfreedom caller with FORBIDDEN "sign in first" -- it fails closed ' +
      'and confusingly, which is the failure that gets a security change ' +
      'reverted rather than fixed.');
  });

  test('the gate is a SINGLE check both verbs pass through, not a per-branch copy', () => {
    // One `if (SD_SESSION_GATED[resource] && ...indexOf(action) !== -1)` before
    // the dispatch. Asserted as EXACTLY ONE: a second copy is a second place
    // for the answer to drift, and the read branch losing its copy is the half
    // that leaks rather than the half that changes rows.
    const n = (CODE.match(/if \(SD_SESSION_GATED\[resource\] && SD_SESSION_GATED\[resource\]\.indexOf\(action\) !== -1\)/g) || []).length;
    assert.strictEqual(n, 1,
      'expected exactly 1 session-gate dispatch check, found ' + n);
  });

  test('the remaining sf_ resources are NOT silently swept in -- this batch is ' +
       'fourteen, and the rest are still an open decision', () => {
    // A gate that quietly widened to all 35 would pass every assertion above
    // and would be a product decision nobody made.
    //
    // ── THIS ARM REFUSED THE 2026-09-22 ADDITION AND WAS RIGHT TO ─────────
    // `sf_members` was in the earlier batch's absence list, and adding it here
    // tripped this arm exactly as designed, with a message naming both things
    // to do. It is now gated ON PURPOSE, with `sf_donor_awards` and
    // `sf_donor_tiers`, and the arm's JOB IS UNCHANGED rather than removed:
    // `sf_signatures` is still an open decision and its absence is still what
    // this asserts.
    //
    // WHY sf_members MOVED: the gate comment above it already called it an
    // acknowledged gap rather than a decision. WHY sf_donor_awards MOVED: its
    // rows are {donorKey, tierId, ...}, so the row says THIS PERSON GAVE AT
    // LEAST THIS MUCH -- the same disclosure sf_donations was gated for.
    // WHY sf_donor_tiers MOVED, and it is the weak one: it carries NO PERSON,
    // and it is gated only so an awards row's opaque tierId cannot be resolved
    // back to an amount. That is defence in depth, not an identity finding.
    const g = gatedSet();
    ['sf_signatures'].forEach((r) => {
      assert.ok(!g.has(r),
        r + ' is gated, but it was not in an approved batch. If that is ' +
        'intended, update this arm AND the open-work row that still lists it ' +
        'as an open decision -- do not let the row and the code disagree.');
    });
    // THE PAIRED POSITIVE. Without this, the arm above is satisfied by a gate
    // that is EMPTY -- and an empty gate passes "nothing was swept in" while
    // protecting nothing at all.
    ['sf_members', 'sf_donor_awards', 'sf_donor_tiers'].forEach((r) => {
      assert.ok(g.has(r),
        r + ' was added to the gate on 2026-09-22 and is not there. This arm ' +
        'asserts what IS gated as well as what is not, so it cannot be ' +
        'satisfied by a gate that protects nothing.');
    });
  });
}

main();
console.log('\n' + passed + ' assertions passed');
