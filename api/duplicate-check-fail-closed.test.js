// api/duplicate-check-fail-closed.test.js
// Run: node api/duplicate-check-fail-closed.test.js
//
// TWO DUPLICATE CHECKS THAT FAILED OPEN, found 2026-09-04 by sweeping the
// platform for the shape fixed on SAIRNdental's public surface.
//
// `const rows = r.ok ? await r.json() : []` appears at roughly fifty sites in
// api/. Most are read-then-render, where a failed read degrades to "nothing to
// show" -- wrong, but visible. THE DANGEROUS SUBSET IS WHERE A FAILED READ
// FEEDS A DECISION, and these two are the sharpest of those: both are
// idempotence checks, and both answered "no duplicate found" when the honest
// answer was "I could not look".
//
//   api/ledger.js       -- checks (source_kind, source_id) before posting a
//                          journal entry. entry_id comes from the CALLER and
//                          the header merges on it, so a retry with the same
//                          id is safe -- but a retry that mints a NEW id for
//                          the same business event is exactly what this check
//                          exists to stop. Failing open posts revenue twice
//                          into a double-entry general ledger.
//
//   api/alf-pharmacy.js -- checks alf_mar before receiving a pharmacy order.
//                          This one does NOT create a second row: entry_id is
//                          derived from the pharmacy's order id and the write
//                          merges on it, so the database is the real
//                          guarantee. What failing open costs is subtler --
//                          the code falls through to a merge that overwrites
//                          `data` with a record whose pharmacy_status is
//                          'pending_review', silently REVERTING an order staff
//                          had already reviewed, and telling the pharmacy
//                          "received" instead of "already received".
//
// The severity difference between the two is real and is asserted separately
// rather than flattened into one story.

'use strict';
const assert = require('assert');
const path = require('path');

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

function mockRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
function reply(status, json) {
  return { ok: status >= 200 && status < 300, status, json: async () => json };
}

async function main() {
  console.log('a duplicate check that could not run is not a clean bill');
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  // ── source-level assertions ───────────────────────────────────────────────
  // Both handlers need a licence + session to reach the check, which these
  // tests deliberately do not fake -- driving that far would test the auth
  // stack, not the fix. What matters is that the fail-open shape is gone and
  // the refusal exists, on the exact lines that had it.
  const fs = require('fs');
  const ledger = fs.readFileSync(path.join(__dirname, 'ledger.js'), 'utf8');
  const pharmacy = fs.readFileSync(path.join(__dirname, 'alf-pharmacy.js'), 'utf8');

  await test('ledger: the fail-open duplicate read is gone', () => {
    assert.ok(!/const drows = dup\.ok \? await dup\.json\(\) : \[\]/.test(ledger),
      'ledger still treats a failed duplicate check as "no duplicate"');
  });

  await test('ledger: a failed duplicate check REFUSES and posts nothing', () => {
    assert.match(ledger, /if \(!dup\.ok\)/, 'no !dup.ok branch');
    assert.match(ledger, /DUPLICATE_CHECK_FAILED/, 'no distinct error code');
    assert.match(ledger, /so nothing was posted/,
      'the message must say nothing was posted -- a caller that retries blindly is the whole risk');
    assert.match(ledger, /idempotence check failed, HTTP/, 'the refusal is not logged');
  });

  await test('ledger: a non-array body is refused too, not read as no-duplicate', () => {
    assert.match(ledger, /if \(!Array\.isArray\(drows\)\)/);
  });

  await test('ledger: BOTH refusal branches come before the header write', () => {
    // Order is the whole fix -- refusing after the insert would refuse nothing.
    //
    // A first draft used indexOf() on the error code and SURVIVED a mutation
    // that gutted the first branch, because the code also appears in the
    // second (non-array) branch a few lines down. One indexOf on a string that
    // occurs twice proves nothing about either occurrence. Count them and
    // check the LAST one instead.
    const write = ledger.indexOf("rest('ledger_entries?on_conflict=");
    assert.ok(write > 0, 'the entry header write moved or was renamed');
    const positions = [];
    let i = ledger.indexOf('DUPLICATE_CHECK_FAILED');
    while (i !== -1) { positions.push(i); i = ledger.indexOf('DUPLICATE_CHECK_FAILED', i + 1); }
    assert.strictEqual(positions.length, 2,
      'expected two refusal branches (failed read, non-array body), found ' + positions.length);
    assert.ok(positions[positions.length - 1] < write,
      'every duplicate refusal must precede the entry header write');
  });

  await test('ledger: 404/400 still means NOT_PROVISIONED, not a data-store error', () => {
    // A table that does not exist is a different answer from one that would
    // not answer, and it already had the better message. Do not regress it.
    assert.match(ledger, /dup\.status === 404 \|\| dup\.status === 400.*notProvisioned/);
  });

  await test('pharmacy: the fail-open duplicate read is gone', () => {
    assert.ok(!/const dupeRows = dupe\.ok \? await dupe\.json\(\)\.catch\(\(\) => \[\]\) : \[\]/.test(pharmacy),
      'alf-pharmacy still treats a failed duplicate check as "not received yet"');
  });

  await test('pharmacy: a failed duplicate check REFUSES and changes nothing', () => {
    assert.match(pharmacy, /if \(!dupe\.ok\)/);
    assert.match(pharmacy, /DUPLICATE_CHECK_FAILED/);
    assert.match(pharmacy, /so nothing was changed/,
      'the message must say nothing was changed -- the risk here is an overwrite, not a duplicate row');
    assert.match(pharmacy, /duplicate check failed, HTTP/, 'the refusal is not logged');
  });

  await test('pharmacy: the refusal comes BEFORE the merging write', () => {
    const refuse = pharmacy.indexOf('DUPLICATE_CHECK_FAILED');
    const write = pharmacy.indexOf("rest('alf_mar?on_conflict=");
    assert.ok(refuse > 0 && write > 0 && refuse < write,
      'the refusal must precede the merge that would reset pharmacy_status');
  });

  await test('pharmacy: the comment records WHY this one is not a duplicate-row bug', () => {
    // The severity was checked before it was described: the merge is the real
    // idempotence guarantee, so the cost is a silent revert, not a second row.
    // A future reader who assumes "duplicate check" means "duplicate row" will
    // fix the wrong thing.
    assert.match(pharmacy, /does NOT create a second row/);
    assert.match(pharmacy, /pending_review/);
  });

  // ── the shape itself, so a third one cannot quietly appear ────────────────
  await test('neither file has ANY remaining `.ok ? await x.json() : []` read', () => {
    // Comment lines stripped first. The fix's own comment QUOTES the old
    // expression to explain what it replaced, and a raw file-wide match hits
    // that explanation -- the same trap tests/stonedesk_locations.js and
    // tests/cut_sheet_basis_parity.js both record. Scrubber item 16 shape A.
    //
    // THIS ASSERTION EARNED ITS KEEP THE MOMENT IT WAS WRITTEN: it was added
    // to cover the one duplicate check I was sent to fix, and it immediately
    // found FOUR MORE in ledger.js -- including trial_balance, where a failed
    // ledger_lines read produced a balanced, empty trial balance, and reverse,
    // where it produced a reversal with no lines. Asserting the SHAPE is gone
    // from the whole file, rather than from the one line, is why.
    const strip = (src) => src.split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
    [['ledger.js', ledger], ['alf-pharmacy.js', pharmacy]].forEach(([name, src]) => {
      const hits = (strip(src).match(/\.ok \? await [A-Za-z]+\.json\(\)(\.catch\([^)]*\))? : \[\]/g) || []);
      assert.deepStrictEqual(hits, [],
        name + ' still has ' + hits.length + ' fail-open read(s): ' + hits.join(' | '));
    });
  });

  await test('ledger: read / trial_balance / reverse are GONE, not hardened', () => {
    // THE ARM THIS REPLACES asserted that trial_balance and reverse refused
    // rather than computing from a partial read. They did, correctly, and the
    // assertion was worth having -- it is what found four fail-open reads in
    // this file in the first place.
    //
    // All three actions had ZERO CALLERS anywhere on the platform.
    // sairnbiz.html is this endpoint's only client and it calls `post` and
    // nothing else. They also carried the only SOFT failure shape left in the
    // file: an absent ledger_entries answered 200 with provisioned:false and
    // trial_balance:null, so whoever wired a trial balance up would have
    // inherited A BALANCED, EMPTY SET OF BOOKS RENDERED FROM A TABLE THAT DOES
    // NOT EXIST.
    //
    // Deleted rather than hardened on 2026-09-14: hardening code nobody calls
    // leaves the same trap for later and adds a second thing to keep true.
    ['read', 'trial_balance', 'reverse'].forEach((a) => {
      assert.ok(ledger.indexOf("action === '" + a + "'") === -1,
        "action '" + a + "' is back in api/ledger.js -- it had no callers and "
        + 'carried the soft provisioned:false shape');
    });
    // The helper went with its last caller.
    assert.ok(!/await rowsOrFail\(/.test(ledger),
      'rowsOrFail is called again -- it existed only for the deleted actions');
    // A request for one of them must get a NAMED refusal, never a silent 200.
    assert.match(ledger, /Unknown action: /,
      'the fall-through refusal is the thing that makes deleting them safe');
  });

  await test('ledger: CONTROL -- the surviving actions and their HARD refusal are untouched', () => {
    // Without this the arm above passes just as well on an empty file, and a
    // deletion that took too much would look identical to one that took
    // exactly enough.
    ['chart', 'validate', 'post'].forEach((a) => {
      assert.ok(ledger.indexOf("action === '" + a + "'") !== -1,
        "action '" + a + "' was deleted too -- that is not the change");
    });
    // post refuses an absent table LOUDLY, at both of its write sites. This is
    // the shape a real trial-balance feature should be built on, and the
    // reason the soft one was not worth keeping.
    const hard = (ledger.match(/notProvisioned\(\);/g) || []).length;
    assert.ok(hard >= 2,
      'expected the write path to refuse at both sites, found ' + hard);
    assert.match(ledger, /NOT_PROVISIONED/);
    // And the pure functions a rebuild would use are still exported and still
    // tested elsewhere -- deleting the endpoint actions did not delete them.
    const lib = fs.readFileSync(path.join(__dirname, '_lib', 'ledger.js'), 'utf8');
    assert.match(lib, /^\s*trialBalance,?$/m, '_lib/ledger.js no longer exports trialBalance');
    assert.match(lib, /^\s*reversalOf,?$/m, '_lib/ledger.js no longer exports reversalOf');
  });

  // ── a live sanity check on the helper both refusals lean on ──────────────
  await test('reply() fixture models a PostgREST failure the way the code sees it', () => {
    // Guarding the guard: if this fixture said ok:true for a 502 the assertions
    // above would be testing nothing.
    assert.strictEqual(reply(502, {}).ok, false);
    assert.strictEqual(reply(200, []).ok, true);
    const r = mockRes(); r.status(502).json({ x: 1 });
    assert.strictEqual(r.statusCode, 502);
  });

  console.log('\n' + passed + ' assertions passed');
}

main();
