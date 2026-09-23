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

test('a hard-deleting SAIRNcode resource is REFUSED, not answered with an empty list', () => {
  const i = SRC.indexOf("if (action === 'tombstones') {", SRC.indexOf('if (isScResource)'));
  assert.ok(i > -1, 'no tombstones handler inside the SAIRNcode branch');
  const b = SRC.slice(i, i + 1400);
  assert.ok(/scIsSoftDeleteOnly\(resource\)/.test(b),
    'the SAIRNcode handler must ask whether this resource keeps tombstones at all');
  assert.ok(/NO_TOMBSTONES/.test(b),
    'a resource that hard-deletes must REFUSE. An empty list from a resource '
    + 'that cannot answer is indistinguishable from one that answered "none".');
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
