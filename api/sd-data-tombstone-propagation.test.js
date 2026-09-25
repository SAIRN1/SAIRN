// api/sd-data-tombstone-propagation.test.js
// REQUIREMENT: a record deleted on one device must become knowable to another
//   one. The soft-delete filter stops a deletion bouncing back on the device
//   that made it; NOTHING told any other device.
//
// Run:  node --test api/sd-data-tombstone-propagation.test.js
//
// ── THE GAP, IN THE WORDS OF THE CODE THAT HALF-CLOSED IT ─────────────────
// sd_customers' read branch says it outright:
//
//   "sdHydrateCustomers() merges the server's rows into the local list BY ID
//    and never deletes -- so before this existed, a customer deleted in the
//    browser was pushed straight back in on the next load. Filtering at the
//    query is what makes the deletion stick; THE CLIENT CANNOT DO IT, because
//    a record it has deleted is a record it no longer knows to skip."
//
// That is device A. Device B hydrated the same id last week: the read simply
// stops returning it, every hydrate on this platform is ADDITIVE BY ID, and an
// absence is not a signal. B keeps the record forever.
//
// ── WHAT THESE ARMS ASSERT, AND WHY EACH ONE EXISTS ───────────────────────
// They are SOURCE-LEVEL, deliberately: the handler is a 13,000-line dispatcher
// against a live PostgREST instance and these assertions have to hold without
// one. What they can check is the shape of the query and the shape of the
// answer, which is where every defect in this family has actually lived -- a
// missing filter, a wrong predicate, an empty list standing in for "cannot
// tell".
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const SRC = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');

// Derived, not typed: the seven soft-delete SAIRNcode resources come from the
// registry that owns them, so adding an eighth cannot leave this file behind.
const SC_SOFT = require('./_resources/sairncode').tierASoftDeleteOnly;

const TOMBSTONE_RESOURCES = ['sd_customers', 'sd_quote_requests'];

test('every soft-delete branch accepts the tombstones action', () => {
  for (const r of TOMBSTONE_RESOURCES) {
    const guard = new RegExp(
      "resource === '" + r + "' && \\(action === 'read'[^)]*'tombstones'\\)");
    assert.ok(guard.test(SRC),
      r + " does not admit 'tombstones' on the same guard as its read. A "
      + 'separate guard is a separate place for the auth check to be wrong, '
      + 'which is the reason soft_delete shares this one.');
  }
});

test('the tombstone query asks for rows that HAVE the marker, not rows that lack it', () => {
  // The read filter is `=is.null`. Inverting it is the entire mechanism, and
  // getting it backwards returns every LIVE row as a deletion -- which would
  // instruct every device to erase its whole local copy.
  const hits = SRC.match(/data->>_deleted_at=not\.is\.null/g) || [];
  assert.ok(hits.length >= 3,
    'expected a not.is.null predicate in each tombstone branch, found '
    + hits.length + '. A tombstone query that reuses the read filter reports '
    + 'every live record as deleted.');
});

test('a tombstone answer carries ids and deleted_at, and NOT the row contents', () => {
  // The deleted row still holds a name, an address, a price. A caller asking
  // what was removed has no business receiving it.
  // Split on the HANDLER, not on the string: the branch GUARDS also contain
  // `action === 'tombstones'`, and splitting on the bare string produced two
  // extra blocks that carry no mapping code and failed the assertion below
  // about code that was never in them.
  const blocks = SRC.split("if (action === 'tombstones') {").slice(1);
  assert.strictEqual(blocks.length, 3,
    'expected exactly three tombstone handlers, found ' + blocks.length);
  for (const b of blocks) {
    const head = b.slice(0, 1400);
    assert.ok(/deleted_at: \(x\.data \|\| \{\}\)\._deleted_at \|\| null/.test(head),
      'a tombstone row must carry deleted_at so an offline client can compare '
      + 'it against its own edit');
    assert.ok(!/Object\.assign\(\{ id:[^}]*\}, x\.data/.test(head),
      'a tombstone handler must NOT spread x.data into its answer -- that '
      + 'returns the contents of a record somebody deleted');
    assert.ok(!/_deleted_by/.test(head),
      'who deleted a record is a different question with a different audience '
      + 'and is not part of this answer');
  }
});

test('an unprovisioned table answers provisioned:false, never a bare empty list', () => {
  const blocks = SRC.split("if (action === 'tombstones') {").slice(1);
  for (const b of blocks) {
    const head = b.slice(0, 1400);
    assert.ok(/r\.status === 404 \|\| r\.status === 400/.test(head)
      && /provisioned: false/.test(head),
      'a missing table must be reported as NOT PROVISIONED. An empty list '
      + 'would read as "nothing has been deleted", which is the could-not-tell '
      + 'folded into a pass.');
  }
});

test('a hard-deleting SAIRNcode resource cannot even REACH the handler', () => {
  // The first version of this arm asserted a NO_TOMBSTONES refusal INSIDE the
  // branch. That refusal is gone, and its removal is the finding: the
  // dispatcher checks an action allowlist BEFORE any resource branch, so
  // declaring `tombstones` only where a tombstone can exist makes the refusal
  // unreachable -- and unreachable code that reads like a control is Guardian
  // check 0d's subject.
  //
  // The allowlist's own message is also the better one: it names the verbs the
  // resource DOES have.
  const extra = require('./_resources/sairncode').extraActions;
  const soft = require('./_resources/sairncode').tierASoftDeleteOnly;
  const all = require('./_resources/sairncode').resources;
  for (const r of all) {
    const declared = (extra[r] || []).indexOf('tombstones') !== -1;
    assert.strictEqual(declared, soft.indexOf(r) !== -1,
      r + ': tombstones must be declared for exactly the soft-delete resources. '
      + 'Declared for a hard-deleting one, the handler answers a query that can '
      + 'only ever return nothing; missing from a soft-delete one, the handler '
      + 'is unreachable behind BAD_ACTION.');
  }
});

test('THE LIVE-PROBE LESSON: every tombstones handler has a matching extraActions entry', () => {
  // This arm exists because the first version SHIPPED UNREACHABLE. Every
  // source-level assertion in this file passed while the deployed endpoint
  // answered "action must be 'read' or 'write' or 'soft_delete'" -- the
  // allowlist runs before the branch, and nothing here was looking at it.
  const sd = require('./_resources/stonedesk').extraActions;
  for (const r of ['sd_customers', 'sd_quote_requests']) {
    assert.ok((sd[r] || []).indexOf('tombstones') !== -1,
      r + ' implements tombstones and does not declare it, so the dispatcher '
      + 'refuses the call before the branch is reached. A handler nothing can '
      + 'call is not a feature.');
  }
});

test('the seven that DO keep tombstones are read from the registry, not typed here', () => {
  assert.ok(Array.isArray(SC_SOFT) && SC_SOFT.length >= 7,
    'tierASoftDeleteOnly did not resolve to a list -- this file would then be '
    + 'asserting nothing about which resources are covered. Got: ' + JSON.stringify(SC_SOFT));
  // The handler is generic over that list, so the only thing to assert here is
  // that the list is the registry's and not a second copy.
  assert.ok(/SC_TIER_A_SOFT_DELETE_ONLY = require\('\.\/_resources\/sairncode'\)/.test(SRC),
    'sd-data.js must take the soft-delete list from the registry; a hand-kept '
    + 'copy is the drift this platform keeps recording');
});

test('THE PAIRED NEGATIVE: the read filter is still is.null, so tombstones did not invert it', () => {
  // Without this, an edit that flipped the READ to not.is.null -- returning
  // only deleted rows to every caller -- would satisfy every arm above.
  const reads = SRC.match(/data->>_deleted_at=is\.null/g) || [];
  assert.ok(reads.length >= 3,
    'the live-row filter has gone missing from at least one read branch. '
    + 'Found ' + reads.length + ' occurrences of the is.null predicate.');
});

// ── SERVER-WINS: A WRITE CANNOT RESURRECT A DELETED RECORD (2026-09-24) ────
// The audit that asked whether this design carried a quiet last-write-wins
// dependency found one, and it lived in the WRITE branches, not here: both
// sd_customers' write and the SAIRNcode generic write are merge-duplicates
// upserts that replace the stored jsonb WHOLESALE, so a stale device's
// ordinary save cleared `_deleted_at` and un-deleted the record -- on
// sd_customers, whose deleted rows a live tracking link resolves against,
// and on the seven soft-delete-only Tier A billing resources. Michael's
// decision is SERVER-WINS. sd_quote_requests had the guard from day one
// ("the API is the boundary, not the panel"); these arms hold the other two
// to the same rule.

test('the sd_customers WRITE refuses a soft-deleted row with 409 DELETED', () => {
  // RE-ANCHORED 2026-09-25: the blob builder became storedBlob(payload, ['id'])
  // when api/_lib/blob.js was adopted on this branch, so the Object.assign
  // spelling this arm quoted stopped existing. Anchored on the VARIABLE now,
  // which is what the guard actually sits in front of, rather than on one
  // spelling of how it is built.
  const i = SRC.indexOf('const custData =');
  assert.ok(i > 0, 'the sd_customers write body moved -- re-anchor this arm');
  assert.strictEqual(SRC.indexOf('const custData =', i + 1), -1,
    'custData is built in two places -- this arm would guard whichever came first');
  const before = SRC.slice(Math.max(0, i - 2600), i);
  assert.ok(/_deleted_at/.test(before) && /'DELETED'/.test(before)
    && /409/.test(before),
    'the sd_customers write no longer checks the STORED row for _deleted_at '
    + 'before upserting -- a stale device\'s save resurrects a deleted '
    + 'customer, and the deletion quietly loses to the last writer');
});

test('the SAIRNcode generic WRITE refuses a soft-deleted row on the seven, and ONLY the seven', () => {
  const i = SRC.indexOf("rest(resource + '?on_conflict=license_hash,entry_id')");
  assert.ok(i > 0, 'the SAIRNcode generic upsert moved -- re-anchor this arm');
  const before = SRC.slice(Math.max(0, i - 1800), i);
  assert.ok(/scIsSoftDeleteOnly\(resource\)/.test(before)
    && /_deleted_at/.test(before) && /'DELETED'/.test(before),
    'the SAIRNcode generic write no longer guards the soft-delete-only '
    + 'resources against resurrection-by-upsert');
  // ONLY the seven: the guard must be inside the scIsSoftDeleteOnly branch,
  // because the other 21 resources have no marker and a pre-read there would
  // be a round trip buying nothing.
  // indexOf on the CODE spelling, not the first mention -- the guard's own
  // comment says _deleted_at before the branch does, and matching the comment
  // failed this arm on code that was correct (the comment-counted-as-code
  // shape, in miniature, inside the arm hunting a related defect).
  const guardIdx = before.indexOf("if (scIsSoftDeleteOnly(resource)) {");
  const delIdx = before.indexOf('sstored._deleted_at');
  assert.ok(guardIdx !== -1 && delIdx > guardIdx,
    'the resurrection check is not scoped to the soft-delete-only resources');
});

test('the deleted_at rationale no longer invites client-side last-write-wins', () => {
  // The tombstone comment originally said deleted_at rides along so a client
  // can "decide whether its own local edit is newer" -- which is an
  // instruction to implement the LWW Michael decided against, waiting for
  // whoever writes the client half. The comment now states SERVER-WINS.
  assert.ok(!/decide whether its own local edit is newer/.test(SRC),
    'the LWW-inviting sentence is back in a tombstone comment -- the client '
    + 'half will be written to it');
  assert.ok(/SERVER-WINS/.test(SRC),
    'the server-wins decision is no longer stated at the tombstone branch');
});
