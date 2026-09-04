// api/alf-append-only-fail-closed.test.js
// Run: node api/alf-append-only-fail-closed.test.js
//
// SIX APPEND-ONLY INTEGRITY CHECKS IN SAIRNcare THAT FAILED OPEN, found
// 2026-09-04 by continuing the sweep that produced the ledger and pharmacy
// fixes.
//
// Each of the six reads a table to see whether an entry_id already exists and
// answers 409 ALREADY_RECORDED if it does. Each protects a record the code's
// own comments say must never be quietly rewritten:
//
//   alf_mar                -- a past medication administration or count
//   alf_incidents          -- an incident report
//   alf_signals            -- a resident signal
//   alf_claim_routes       -- how a real claim was billed
//   alf_staff_credentials  -- a completed-training assertion
//   alf_op_audits          -- an audit observation
//
// All six read it as `existingR.ok ? await existingR.json() : []`, so a 401,
// 403, 500 or 503 answered "no existing record" and the write proceeded.
//
// ══ THE COST SPLITS IN TWO, AND THE HALVES ARE NOT THE SAME ═══════════════
// Checked against the six write sites and four schema files rather than
// assumed from the shared shape:
//
//   * alf_mar, alf_incidents and alf_op_audits write with
//     `on_conflict=...merge-duplicates`. On a failed check the prior record is
//     SILENTLY OVERWRITTEN. For those three, the append-only guarantee is
//     enforced by this application check ALONE.
//
//   * alf_signals, alf_claim_routes and alf_staff_credentials use a plain
//     INSERT, and all six tables carry `unique (license_hash, entry_id)`. The
//     database refuses the duplicate regardless, so a failed check there costs
//     a confusing upstream error instead of a clean 409 -- wrong, not
//     corrupting.
//
// That distinction is asserted separately below. Flattening it would overstate
// three of the six and understate the other three.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

let passed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

const SRC = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8').replace(/\r\n/g, '\n');
// Comment lines stripped before any shape scan: the fix's own header quotes the
// old expression to explain what it replaced, and a raw file-wide match hits
// that explanation. Same trap tests/cut_sheet_basis_parity.js already records.
const CODE = SRC.split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');

const TABLES = ['alf_mar', 'alf_incidents', 'alf_signals',
                'alf_claim_routes', 'alf_staff_credentials', 'alf_op_audits'];
const OVERWRITES = ['alf_mar', 'alf_incidents', 'alf_op_audits'];

function main() {
  console.log('SAIRNcare append-only checks: a check that could not run is not a clean bill');

  test('the fail-open existingRows read is gone from sd-data.js entirely', () => {
    const hits = CODE.match(/existingR\.ok \? await existingR\.json\(\) : \[\]/g) || [];
    assert.deepStrictEqual(hits, [],
      'still ' + hits.length + ' append-only check(s) treating a failed read as "no existing record"');
  });

  test('all six sites go through the checked reader', () => {
    TABLES.forEach((t) => {
      assert.ok(CODE.includes("appendOnlyExisting(res, existingR, '" + t + "')"),
        t + ' does not use appendOnlyExisting');
    });
    const uses = (CODE.match(/await appendOnlyExisting\(/g) || []).length;
    assert.strictEqual(uses, 6, 'expected exactly 6 checked reads, found ' + uses);
  });

  test('every call site returns immediately when the check could not run', () => {
    // Without the guard the helper returns null and the code carries on with
    // `existingRows === null`, which is falsy -- so `existingRows.length` would
    // throw AFTER a 502 was already sent. The `if (!existingRows) return;` is
    // what makes the refusal actually refuse.
    const sites = CODE.match(/await appendOnlyExisting\(res, existingR, '[a-z_]+'\);[^\n]*/g) || [];
    assert.strictEqual(sites.length, 6);
    sites.forEach((line) => {
      assert.match(line, /if \(!existingRows\) return;/,
        'a call site does not bail out: ' + line.trim());
    });
  });

  test('the helper refuses on a failed read AND on a non-array body', () => {
    assert.match(SRC, /async function appendOnlyExisting\(res, r, what\)/);
    assert.match(SRC, /INTEGRITY_CHECK_FAILED/);
    assert.match(SRC, /so nothing was written/,
      'the message must say nothing was written -- a caller that retries blindly is the risk');
    assert.match(SRC, /if \(!Array\.isArray\(rows\)\)/);
    assert.match(SRC, /append-only check failed \(' \+ what \+ '\), HTTP/,
      'the log must name WHICH check died -- there are six of them');
  });

  test('the helper returns null so a caller cannot mistake a refusal for an empty result', () => {
    // Returning [] on failure would put us straight back where we started.
    const body = SRC.slice(SRC.indexOf('async function appendOnlyExisting'));
    const end = body.indexOf('\n}');
    const fn = body.slice(0, end);
    assert.ok(!/return \[\];/.test(fn), 'the helper returns [] somewhere -- that is the original bug');
    // Three, not two: the two failure paths plus the `.catch(() => null)` on
    // the body parse, which is what makes the non-array branch reachable at all.
    // Counted from the code rather than from what I expected to find.
    assert.strictEqual((fn.match(/return null;?/g) || []).length, 3,
      'expected both failure paths and the parse catch to yield null');
  });

  // ── the severity split, asserted rather than flattened ───────────────────
  test('the three OVERWRITING tables really do write with merge-duplicates', () => {
    // This is what makes those three integrity failures rather than bad UX.
    // If a future change moved any of them to a plain insert, the comment
    // above would become wrong and this catches it.
    OVERWRITES.forEach((t) => {
      const i = CODE.indexOf("rest('" + t + "?on_conflict=license_hash,entry_id'");
      assert.ok(i > 0, t + ' no longer upserts on (license_hash, entry_id) -- re-read the severity note');
    });
  });

  test('the other three use a plain insert, and the schema backstops them', () => {
    ['alf_signals', 'alf_claim_routes', 'alf_staff_credentials'].forEach((t) => {
      assert.ok(!CODE.includes("rest('" + t + "?on_conflict="),
        t + ' now upserts -- it would become an overwrite risk, re-read the severity note');
    });
    // All six tables carry the unique constraint. That is the backstop the
    // severity split leans on, so it is checked in the SQL, not assumed.
    const sqlDir = path.join(__dirname, '..', 'sql');
    const files = fs.readdirSync(sqlDir).filter((f) => f.endsWith('.sql'))
      .map((f) => fs.readFileSync(path.join(sqlDir, f), 'utf8')).join('\n');
    TABLES.forEach((t) => {
      const i = files.indexOf('create table if not exists public.' + t + ' ');
      assert.ok(i > 0, 'no schema found for ' + t);
      const decl = files.slice(i, files.indexOf(');', i));
      assert.match(decl, /unique \(license_hash, entry_id\)/,
        t + ' has no unique (license_hash, entry_id) -- the severity note assumes it does');
    });
  });

  test('the 409 ALREADY_RECORDED answers survive -- this fixed the check, not the rule', () => {
    const n = (CODE.match(/ALREADY_RECORDED/g) || []).length;
    assert.ok(n >= 5, 'expected the append-only refusals to remain, found ' + n);
  });

  test('branches that already handled 404/400 as NOT_PROVISIONED still do', () => {
    // alf_incidents and alf_op_audits distinguished "table absent" from "table
    // silent" before this change. A table that does not exist is a different
    // answer from one that would not answer, and it had the better message.
    //
    // A LOWER BOUND, NOT AN EXACT COUNT. A first draft asserted exactly 2 and
    // failed at 10 -- because nine unrelated branches in this shared file use
    // the same pre-check. An exact count here would go stale the next time
    // anyone adds a resource, which is the brittle-counter trap the
    // session-gate test already recorded once tonight.
    const n = (CODE.match(/existingR\.status === 404 \|\| existingR\.status === 400/g) || []).length;
    assert.ok(n >= 2, 'the NOT_PROVISIONED pre-checks were removed, found ' + n);
  });

  test('the seven branches that ALREADY failed closed were not touched', () => {
    // Seven other existingR reads in this file already did
    // `if (!existingR.ok) return upstream(res, existingRows)`. They were never
    // part of this defect and this change must not have disturbed them --
    // checked because the patch was applied by pattern across a 9,600-line
    // file shared by eleven apps.
    const n = (CODE.match(/if \(!existingR\.ok\) return upstream\(/g) || []).length;
    assert.strictEqual(n, 7, 'expected the 7 already-correct branches intact, found ' + n);
  });

  console.log('\n' + passed + ' assertions passed');
}

main();
