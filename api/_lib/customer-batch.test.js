// api/_lib/customer-batch.test.js
// REQUIREMENT: the sd_customers write_batch DECISIONS -- writable, refused,
//   skipped -- must be answerable by passing arguments, with no fake fetch, no
//   fake licence module and no fake session.
//
// Run: node api/_lib/customer-batch.test.js
//
// ── WHAT THIS SUITE IS FOR, AND WHAT IT IS NOT ─────────────────────────────
// It is NOT a second copy of api/sd-data-customers-batch.test.js. That suite
// is the ENDPOINT contract -- trip counts, HTTP statuses, response keys, the
// registry declaration -- and it is deliberately unchanged by this refactor,
// because a refactor that also changed behaviour could not be verified as
// either. This suite is the cases that suite cannot cheaply reach: the ones
// that are about an ARRAY rather than about a request.
//
// EVERY ARM BELOW IS A FUNCTION CALL. That is the whole claim of item 92, and
// the honest measure of it is the line count above the first assertion: the
// endpoint suite needs sixty lines of harness, this one needs none.
//
// ── THE NEGATIVE CONTROLS ARE SECTION 5, and they are not decoration ───────
// The platform measured on 2026-09-13 that 23 of 39 negative controls never
// verified their own sabotage applied. Section 5 mutates the core's returned
// values and asserts the arms above would have caught it -- for the two arms
// whose failure mode is silence rather than a throw.

'use strict';
const assert = require('assert');
const core = require('./customer-batch');

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; console.log('  ok   ' + label); }
function eq(a, b, label) { assert.deepStrictEqual(a, b, label + '\n      got ' + JSON.stringify(a)); n++; console.log('  ok   ' + label); }
function section(s) { console.log('\n' + s); }

console.log('sd_customers write_batch -- the core decides, the shell does the I/O\n');

function recs(k) {
  const out = [];
  for (let i = 1; i <= k; i++) out.push({ id: 'C' + i, name: 'Customer ' + i });
  return out;
}

section('1. planBatch -- THREE states, never two');
{
  eq(core.planBatch(null).refusal.code, 'NO_RECORDS',
     'no payload at all is a refusal, not an empty batch');
  eq(core.planBatch({}).refusal.code, 'NO_RECORDS', 'no records key is a refusal');
  eq(core.planBatch({ records: 'C1' }).refusal.code, 'NO_RECORDS',
     'a STRING is refused rather than coerced -- "C1" has a length and would '
     + 'otherwise look like a one-record batch');
  eq(core.planBatch({ records: { 0: { id: 'C1' } } }).refusal.code, 'NO_RECORDS',
     '...and so is an object with numeric keys, which also has no Array shape');

  ok(core.planBatch({ records: [] }).empty === true,
     'an EMPTY list is its own state -- not a refusal and not a write');
  ok(!core.planBatch({ records: [] }).refusal,
     '...and specifically NOT a refusal: the client sent a complete list that '
     + 'happens to be empty, and calling that an error trains a caller to ignore errors');

  const p = core.planBatch({ records: recs(3) });
  eq(core.ids(p.withId), ['C1', 'C2', 'C3'], 'a good batch yields its ids in order');
  eq(p.skippedWithoutId, 0, '...and reports nothing skipped');
}

section('2. planBatch -- the cap refuses, and the boundary is exact');
{
  eq(core.BATCH_CAP, 500, 'the cap is a named export, not a number typed into a branch');
  ok(!core.planBatch({ records: recs(500) }).refusal,
     'EXACTLY 500 is accepted -- "at most 500" means 500');
  eq(core.planBatch({ records: recs(501) }).refusal.code, 'BATCH_TOO_LARGE',
     '501 is refused');
  eq(core.planBatch({ records: recs(501) }).refusal.status, 413, '...as a 413');
  ok(/refuses rather than truncating/.test(core.planBatch({ records: recs(501) }).refusal.message),
     '...and the message says WHY it is not a truncation, because a truncated '
     + 'batch reports success for records that were never sent');
  // A CALLER-SUPPLIED CAP, so the boundary arm above is testing a boundary and
  // not a coincidence of the number 500.
  eq(core.planBatch({ records: recs(3) }, 2).refusal.code, 'BATCH_TOO_LARGE',
     'the cap is a parameter: 3 records against a cap of 2 is refused');
  ok(/at most 2 records/.test(core.planBatch({ records: recs(3) }, 2).refusal.message),
     '...and the message quotes the cap in force rather than a hardcoded 500 -- '
     + 'a refusal naming the wrong limit is one the caller cannot act on');
}

section('3. planBatch -- a record with no usable id is COUNTED, never dropped silently');
{
  const p = core.planBatch({ records: [{ id: 'C1' }, { name: 'no id' }, null, undefined] });
  eq(core.ids(p.withId), ['C1'], 'only the record with an id survives');
  eq(p.skippedWithoutId, 3,
     'and the other three are COUNTED -- a silent drop here is the discarded '
     + 'write one level up');

  // THE FALSY-ID CASES, which are exactly what a pure function is cheap to ask
  // about and a mocked endpoint is not. These are documented as skipped rather
  // than fixed: `c.id` is a truthiness test in the shipped branch and changing
  // it would be a behaviour change smuggled into a refactor.
  const f = core.planBatch({ records: [{ id: 0 }, { id: '' }, { id: false }, { id: 'C9' }] });
  eq(core.ids(f.withId), ['C9'],
     'an id of 0, "" or false is treated as NO id -- the shipped branch tests '
     + 'truthiness and this arm records that, it does not endorse it');
  eq(f.skippedWithoutId, 3, '...and all three are counted as skipped');

  eq(core.planBatch({ records: [{ name: 'x' }, null] }).refusal.code, 'NO_IDS',
     'a batch where NOTHING carries an id is a refusal, not a 0-written success');
}

section('4. tombstonedIds + partition -- refused BY NAME');
{
  const del = core.tombstonedIds([
    { customer_id: 'C2', data: { _deleted_at: '2026-09-01T00:00:00Z' } },
    { customer_id: 'C3', data: { name: 'alive' } },
    { customer_id: 'C4', data: null },
    null
  ]);
  eq(Object.keys(del), ['C2'],
     'only a row whose stored blob carries _deleted_at is tombstoned; a null '
     + 'row and a null data are neither tombstoned nor a throw');

  const split = core.partition(recs(3), del);
  eq(split.keep.map((c) => c.id), ['C1', 'C3'], 'the tombstoned id is not written');
  eq(split.refused, [{ id: 'C2', code: 'DELETED',
      reason: 'that customer record was deleted on another device; drop it locally' }],
     'and it is refused BY NAME with a sentence the client can act on -- id, '
     + 'code and reason, not a count');

  // "SAID NOTHING" IS NOT EVIDENCE OF A DELETION. This mirrors the shell's
  // documented fall-through for a pre-read that answered with a refusal or
  // whose body did not parse.
  eq(Object.keys(core.tombstonedIds(null)), [], 'a null pre-read body is an EMPTY map');
  eq(Object.keys(core.tombstonedIds('not json')), [], '...and so is a string');
  eq(core.partition(recs(2), core.tombstonedIds(null)).keep.length, 2,
     '...so nothing is refused on the strength of a read that said nothing');

  const all = core.partition(recs(2), core.tombstonedIds([
    { customer_id: 'C1', data: { _deleted_at: 'x' } },
    { customer_id: 'C2', data: { _deleted_at: 'x' } }]));
  eq(all.keep, [], 'an entirely tombstoned batch keeps nothing');
  eq(all.refused.length, 2, '...and still names both refusals');
}

section('5. upsertRows -- the blob rule, and the clock as an ARGUMENT');
{
  const rows = core.upsertRows(
    [{ id: 'C1', name: 'A', _deleted_at: null, license_hash: 'SPOOFED', stage: 'quoted' }],
    { licHash: 'real-hash', appId: 'stonedesk', now: '2026-09-27T12:00:00Z' });
  eq(rows.length, 1, 'one record in, one row out');
  eq(rows[0].customer_id, 'C1', 'the id becomes the real column');
  eq(rows[0].data.id, undefined, '...and is NOT left inside the blob, because the '
     + 'read spreads {id: customer_id} + data and would echo a stale copy');
  eq(rows[0].data.name, 'A', 'ordinary fields survive');
  ok('_deleted_at' in rows[0].data,
     '_deleted_at is NOT stripped -- it lives inside data by design and '
     + 'tombstonedIds() reads it there');
  eq(rows[0].license_hash, 'real-hash',
     'the licence hash comes from the caller-supplied context...');
  eq(rows[0].data.license_hash, undefined,
     '...and a PAYLOAD license_hash is stripped from the blob by api/_lib/blob.js, '
     + 'so a spoofed one cannot ride in and be echoed back as a lying field');

  eq(rows[0].updated_at, '2026-09-27T12:00:00Z', 'the timestamp is the one passed in');
  // THE ARM THAT MAKES THIS A CORE AND NOT JUST A FILE. No fallback clock: the
  // module's answer cannot depend on when it ran.
  eq(core.upsertRows([{ id: 'C1' }], { licHash: 'h', appId: 'a' })[0].updated_at, undefined,
     'omitting `now` yields updated_at: undefined -- there is NO fallback clock, '
     + 'so this module can never answer differently on a different day');

  const args = [{ id: 'C1', name: 'A' }];
  const ctx = { licHash: 'h', appId: 'stonedesk', now: '2026-01-01T00:00:00Z' };
  eq(core.upsertRows(args, ctx), core.upsertRows(args, ctx),
     'and the same arguments give a deep-equal answer twice -- determinism '
     + 'driven, not asserted in a comment');
}

section('6. NEGATIVE CONTROLS -- the two arms whose failure mode is SILENCE');
{
  // Both arms below would pass on a broken core if they were written the
  // obvious way, so each is shown to FAIL against a deliberately wrong value.
  let caught = 0;
  try {
    assert.deepStrictEqual(core.partition(recs(3),
      core.tombstonedIds([{ customer_id: 'C2', data: { _deleted_at: 'x' } }]))
      .keep.map((c) => c.id), ['C1', 'C2', 'C3']);
  } catch (e) { caught++; }
  ok(caught === 1,
     'CONTROL: asserting the tombstoned id IS kept fails -- so section 4\'s keep '
     + 'arm is distinguishing a filtered list from an unfiltered one');

  caught = 0;
  try {
    assert.deepStrictEqual(
      core.upsertRows([{ id: 'C1', name: 'A' }], { licHash: 'h', appId: 'a', now: 't' })[0].data.id,
      'C1');
  } catch (e) { caught++; }
  ok(caught === 1,
     'CONTROL: asserting `id` SURVIVES inside the blob fails -- so the strip arm '
     + 'is testing storedBlob\'s effect rather than an absent key');
}

console.log('\n' + n + ' passed, 0 failed');
