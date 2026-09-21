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
//   * alf_incidents and alf_op_audits write with `on_conflict=...
//     merge-duplicates`. On a failed check the prior record is SILENTLY
//     OVERWRITTEN. For those two, the append-only guarantee is enforced by
//     this application check ALONE.
//
//   * alf_signals, alf_claim_routes and alf_staff_credentials use a plain
//     INSERT, and all six tables carry `unique (license_hash, entry_id)`. The
//     database refuses the duplicate regardless, so a failed check there costs
//     a confusing upstream error instead of a clean 409 -- wrong, not
//     corrupting.
//
// That distinction is asserted separately below. Flattening it would overstate
// the remaining two and understate the other three.
//
// alf_mar WAS in the first group and is no longer in either (2026-09-21,
// hover_log #314). appendOnlyExisting + merge-duplicates was itself a real
// TOCTOU on this table -- two callers could each pass the SELECT before
// either POST landed, and the second POST's merge-duplicates resolution
// would silently overwrite the first row. It now routes through
// public.alf_check_and_insert_mar_entry(), a pg_advisory_xact_lock-scoped
// Postgres function (same pattern as law_check_and_insert_disbursement) that
// holds the check-then-write atomically inside one transaction -- strictly
// stronger than either group below, asserted in its own dedicated test.

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
const OVERWRITES = ['alf_incidents', 'alf_op_audits'];
// alf_mar moved OFF the appendOnlyExisting + merge-duplicates pattern
// entirely on 2026-09-21 (hover_log #314): that pattern was a genuine TOCTOU
// -- two callers could each pass the SELECT before either POST landed, and
// the second POST's merge-duplicates resolution would silently overwrite the
// first row rather than hitting the 409 path this suite was written to
// guard. It now routes through public.alf_check_and_insert_mar_entry(), a
// pg_advisory_xact_lock-scoped Postgres function (same pattern as
// law_check_and_insert_disbursement) that holds the check-then-write
// atomically inside one transaction -- a STRICTER guarantee than the
// application-level check this file otherwise tests, not a weaker one, so it
// is asserted separately below rather than folded into either list.
const APPEND_ONLY_EXISTING_TABLES = ['alf_incidents', 'alf_signals',
                'alf_claim_routes', 'alf_staff_credentials', 'alf_op_audits'];

function main() {
  console.log('SAIRNcare append-only checks: a check that could not run is not a clean bill');

  test('the fail-open existingRows read is gone from sd-data.js entirely', () => {
    const hits = CODE.match(/existingR\.ok \? await existingR\.json\(\) : \[\]/g) || [];
    assert.deepStrictEqual(hits, [],
      'still ' + hits.length + ' append-only check(s) treating a failed read as "no existing record"');
  });

  test('the remaining five sites go through the checked reader', () => {
    APPEND_ONLY_EXISTING_TABLES.forEach((t) => {
      assert.ok(CODE.includes("appendOnlyExisting(res, existingR, '" + t + "')"),
        t + ' does not use appendOnlyExisting');
    });
    const uses = (CODE.match(/await appendOnlyExisting\(/g) || []).length;
    assert.strictEqual(uses, 5, 'expected exactly 5 checked reads (alf_mar moved to the atomic RPC), found ' + uses);
  });

  test('alf_mar routes through the atomic RPC instead of appendOnlyExisting + merge-duplicates', () => {
    assert.ok(!CODE.includes("appendOnlyExisting(res, existingR, 'alf_mar')"),
      'alf_mar still uses appendOnlyExisting -- the TOCTOU-vulnerable pattern was supposed to be replaced, not kept alongside the RPC');
    assert.ok(CODE.includes("rest('rpc/alf_check_and_insert_mar_entry')"),
      'alf_mar write does not call the atomic RPC');
    assert.ok(!CODE.includes("rest('alf_mar?on_conflict=license_hash,entry_id')"),
      'alf_mar still has the old direct upsert alongside the RPC -- the TOCTOU window is still open if both paths exist');
  });

  test('every call site returns immediately when the check could not run', () => {
    // Without the guard the helper returns null and the code carries on with
    // `existingRows === null`, which is falsy -- so `existingRows.length` would
    // throw AFTER a 502 was already sent. The `if (!existingRows) return;` is
    // what makes the refusal actually refuse.
    const sites = CODE.match(/await appendOnlyExisting\(res, existingR, '[a-z_]+'\);[^\n]*/g) || [];
    assert.strictEqual(sites.length, 5, 'expected 5 (alf_mar moved to the atomic RPC), found ' + sites.length);
    sites.forEach((line) => {
      assert.match(line, /if \(!existingRows\) return;/,
        'a call site does not bail out: ' + line.trim());
    });
  });

  test('the helper refuses on a failed read AND on a non-array body', () => {
    assert.match(SRC, /async function appendOnlyExisting\(res, r, what\)/);
    assert.match(SRC, /so nothing was written/,
      'the message must say nothing was written -- a caller that retries blindly is the risk');
    assert.match(SRC, /append-only check failed \(' \+ what \+ '\), HTTP/,
      'the log must name WHICH check died -- there are six of them');

    // ── ADDED 2026-09-15 BY THIS SUITE'S FIRST NEGATIVE CONTROL ──────────
    // tests/alf_append_only_probe.py planted `if (false)` in place of the
    // `if (!r.ok)` branch and this test STAYED GREEN. Every assertion above
    // matched text NEAR the guard -- the function signature, the message, the
    // log line -- and none of them matched the guard's own condition, so the
    // fail-open branch could be disabled with the suite reporting clean.
    //
    // That is the test-layer half of defect cluster 5b98fd27, reproduced in a
    // different file: an assertion that does not depend on the thing the
    // mutation changed. The fix is to assert on the CONDITION, in its own
    // function body rather than anywhere in a 400KB file.
    const FN_START = SRC.indexOf('async function appendOnlyExisting');
    const FN = SRC.slice(FN_START, SRC.indexOf('\n}', FN_START));
    assert.match(FN, /if \(!r\.ok\) \{/,
      'the helper must TEST r.ok -- matching the message or the signature '
      + 'leaves the branch itself unasserted, which is how it can be disabled '
      + 'with this suite green');

    // ── AND THE SAME FIX, THREE DAYS LATE, ON THE ASSERTION NEXT TO IT ─────
    // Moved here from a whole-file `assert.match(SRC, ...)` on 2026-09-21.
    // THE 2026-09-15 PASS FIXED TWO OF THE THREE ASSERTIONS IN THIS TEST AND
    // LEFT THIS ONE, and it went on biting for three days because there was
    // exactly one `if (!Array.isArray(rows))` in api/sd-data.js -- so the
    // whole-file match happened to be equivalent to a scoped one.
    //
    // ON 2026-09-18 AT 19:15, COMMIT 92be209a ADDED A SECOND ONE, thirty
    // lines above this function, inside wroteRow(). Nothing about this suite
    // or this guard changed. From that moment arm 5 of
    // tests/alf_append_only_probe.py ("a non-array body stops refusing") was
    // SILENT: the mutation removes the guard here and the assertion is
    // satisfied by the copy in wroteRow(). Demonstrated rather than inferred
    // -- planting the mutation and testing both forms, the whole-file regex
    // passes and the function-scoped one fails.
    //
    // That is the eighth standing discipline exactly: nothing announces the
    // day a check stops testing anything, and here the announcement would
    // have had to come from an unrelated commit in a different app's sweep.
    assert.match(FN, /if \(!Array\.isArray\(rows\)\)/,
      'the helper must TEST the shape of the parsed body, IN ITS OWN BODY -- '
      + 'a whole-file match for this condition is satisfied by wroteRow() '
      + 'thirty lines above, so the guard can be removed with this suite green');

    // And the code is asserted INSIDE the function too. `INTEGRITY_CHECK_FAILED`
    // appears twice there; a whole-file match is satisfied by whichever one was
    // not changed, so the probe's arm 6 also passed on a broken build.
    const codes = FN.match(/code: '([A-Z_]+)'/g) || [];
    assert.strictEqual(codes.length, 2,
      'expected both refusal paths to carry a code, found ' + codes.length);
    codes.forEach((c) => assert.strictEqual(c, "code: 'INTEGRITY_CHECK_FAILED'",
      'both refusals must carry INTEGRITY_CHECK_FAILED, found ' + c));
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
  test('the two remaining OVERWRITING tables really do write with merge-duplicates', () => {
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
