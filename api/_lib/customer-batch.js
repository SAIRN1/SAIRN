// api/_lib/customer-batch.js -- Pure functions, no I/O.
//
// METHODOLOGY ITEM 92 (functional core, imperative shell), applied to
// `sd_customers write_batch` in api/sd-data.js. The plan's own words name the
// second class of target as "any state-mutation code shaped like the Quote
// Builder bug", and this branch is that shape: it decides WHICH of up to 500
// records get written, WHICH are refused by name, and WHICH were skipped --
// and every one of those decisions was reachable only by standing up a fake
// `fetch`, a fake licence module and a fake session, then reading the decision
// back out of a captured HTTP body.
//
// WHY THIS BRANCH AND NOT A SWEEP. The existing endpoint suite
// (api/sd-data-customers-batch.test.js) needs SIXTY LINES of mock harness
// before it can ask "is a record with no id counted or dropped", which is a
// question about an array. The suite is good and stays exactly as it is -- it
// is the regression evidence for this refactor, and a refactor that also
// changed behaviour could not be verified as either. What changes is that the
// decisions below can now be driven as ARGUMENTS, so the cases a reader would
// want (a null in the list, an id of 0, a batch that is entirely tombstoned,
// a pre-read that answered with rubbish) are four calls rather than four
// worlds.
//
// THE CLOCK IS AN ARGUMENT AND THAT IS LOAD-BEARING, not a style choice.
// `upsertRows` takes `now` and has NO fallback: omit it and the row carries
// `updated_at: undefined`, which a caller notices. A default of
// `new Date().toISOString()` would make this module's answer depend on when it
// ran, which is the one property the whole split exists to remove --
// tests/functional_core_is_pure.js asserts both halves.
//
// WHAT IS DELIBERATELY NOT HERE: the pre-read, the upsert, the HTTP statuses'
// transport, and the fall-through rule for a pre-read that ANSWERED with a
// refusal. That last one is a decision about I/O outcomes, it is documented in
// the shell where the fetch is, and moving it here would mean handing this
// module a response object -- which is the world coming back in through the
// argument list.

'use strict';

const { storedBlob } = require('./blob');

// THE CAP LIVES WITH THE DECISION IT CONSTRAINS. It was a bare 500 in the
// branch; a caller that wants a different one passes it, and nothing has to
// re-type the number to know what it is.
const BATCH_CAP = 500;

// planBatch(payload, cap) -> one of three shapes, never two:
//
//   { refusal: {status, code, message} }   the batch is not writable as sent
//   { empty: true }                        a legitimately empty list
//   { withId, skippedWithoutId }           what to pre-read and how many were
//                                          dropped for having no id
//
// THREE STATES RATHER THAN TWO IS THE POINT. An empty batch is NOT a refusal
// (the client sent a complete list that happens to be empty) and it is not a
// write either, and collapsing it into either one is how "nothing to do"
// becomes either a spurious error or a silent success.
function planBatch(payload, cap) {
  const limit = (typeof cap === 'number' && cap > 0) ? cap : BATCH_CAP;
  const recs = (payload && Array.isArray(payload.records)) ? payload.records : null;
  if (!recs) {
    return { refusal: { status: 400, code: 'NO_RECORDS',
      message: 'write_batch needs payload.records as an array. A single record still uses write.' } };
  }
  // A CAP THAT REFUSES RATHER THAN TRUNCATING. A silently truncated batch is
  // the same defect as the discarded per-record loop this branch replaced --
  // the caller is told the list was saved and part of it never left.
  if (recs.length > limit) {
    return { refusal: { status: 413, code: 'BATCH_TOO_LARGE',
      message: 'write_batch accepts at most ' + limit + ' records; send them in '
        + 'chunks. It refuses rather than truncating, because a truncated batch '
        + 'reports success for records that were never sent.' } };
  }
  if (!recs.length) return { empty: true };
  const withId = recs.filter(function (c) { return c && c.id; });
  const skippedWithoutId = recs.length - withId.length;
  if (!withId.length) {
    return { refusal: { status: 400, code: 'NO_IDS',
      message: 'no record in this batch carries an id' } };
  }
  return { withId: withId, skippedWithoutId: skippedWithoutId };
}

// ids(withId) -> the id strings for the ONE pre-read, in order. The shell
// url-encodes them; deciding WHICH ids to ask about is not an I/O decision.
function ids(withId) {
  return (withId || []).map(function (c) { return String(c.id); });
}

// tombstonedIds(rows) -> { id: true } for every pre-read row carrying
// `_deleted_at`. Takes the RAW rows, because reading a deletion out of the
// stored blob is the RULE, not plumbing -- the single-record write path reads
// `_deleted_at` from exactly the same place and there must not be two
// spellings of it.
//
// A NON-ARRAY IS AN EMPTY MAP, NOT A THROW, and that mirrors the shell's
// documented fall-through: a pre-read whose body did not parse said nothing
// about a deletion, and "said nothing" is not evidence of one.
function tombstonedIds(rows) {
  const out = {};
  (Array.isArray(rows) ? rows : []).forEach(function (row) {
    if (row && row.data && row.data._deleted_at) out[String(row.customer_id)] = true;
  });
  return out;
}

// partition(withId, deleted) -> { keep, refused }
//
// REFUSED RECORDS ARE NAMED, NOT COUNTED. A batch that silently dropped the
// tombstoned ones would be the discarded-write silence one level up, so each
// carries its id, a code and a sentence the client can act on.
function partition(withId, deleted) {
  const del = deleted || {};
  const keep = [], refused = [];
  (withId || []).forEach(function (c) {
    if (del[String(c.id)]) {
      refused.push({ id: c.id, code: 'DELETED',
        reason: 'that customer record was deleted on another device; drop it locally' });
    } else {
      keep.push(c);
    }
  });
  return { keep: keep, refused: refused };
}

// upsertRows(keep, ctx) -> the rows to POST. ctx = {licHash, appId, now}.
//
// SAME BLOB RULE AS THE SINGLE WRITE, and the same column list: the read
// spreads {id: customer_id} + data, so `id` is the only real column.
// `_deleted_at` is deliberately NOT stripped -- it lives inside data by design
// and tombstonedIds() above reads it there.
//
// `now` HAS NO DEFAULT. See the header.
function upsertRows(keep, ctx) {
  const c = ctx || {};
  return (keep || []).map(function (rec) {
    return { license_hash: c.licHash, app_id: c.appId,
             customer_id: String(rec.id), data: storedBlob(rec, ['id']),
             updated_at: c.now };
  });
}

module.exports = { BATCH_CAP: BATCH_CAP, planBatch: planBatch, ids: ids,
                   tombstonedIds: tombstonedIds, partition: partition,
                   upsertRows: upsertRows };
