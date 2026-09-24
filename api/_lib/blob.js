// api/_lib/blob.js -- ONE place that knows what never belongs in a stored
// jsonb blob. Methodology item 94 (Ousterhout): this is information leakage
// made concrete. Dozens of api/sd-data.js branches independently re-implement
// "build the data blob from the payload, minus the fields that are real
// columns" -- Object.assign({}, payload) followed by a hand-typed delete list
// -- and every copy of that decision is a chance to forget something. Two
// forgettings are already on the record from one review (2026-09-24, the
// 2026-09-23T18:54:03Z discharge): a payload `license_hash` rides into the
// blob on most branches and is echoed back on read as a lying field the row's
// real tenant column contradicts, and a payload `created_at` on the two ALF
// trails SHADOWS the mapped column because the read spreads the blob last.
//
// THE DECISION THIS MODULE HIDES: scope keys -- the fields whose only meaning
// is "whose row is this / which app wrote it" -- are derived by the handler
// from the verified licence and session, NEVER stored inside data, on any
// branch, ever. That is one sentence, it was previously spread across every
// write branch as an omission, and a caller cannot get it wrong any more:
// stripping them is not optional and not listed per call site.
//
// COLUMN KEYS STAY PER-BRANCH, deliberately, and the asymmetry is the design:
// which payload fields are real columns is a fact about each table (alf_mar's
// created_at is a mapped column; sairnlegacy blobs carry created_at as data
// on purpose), so a global list would strip real data somewhere. The scope
// keys are the only universal truth, so they are the only thing hidden here.
//
// NOT A SANITISER. This does not validate, coerce or deep-copy nested
// values; it makes the same shallow copy every branch already made. Branches
// that build their blob column-by-column (rf_supplier_documents) are already
// immune and gain nothing from calling this.

'use strict';

// `p_license_hash` is included because alf_mar's RPC-argument spelling can
// arrive in a payload too -- same key class, different prefix.
const NEVER_STORED = ['license_hash', 'app_id', 'p_license_hash'];

// storedBlob(payload, columnKeys) -> shallow copy of payload with the
// branch's COLUMN keys and the universal scope keys removed.
function storedBlob(payload, columnKeys) {
  const blob = Object.assign({}, payload);
  (columnKeys || []).forEach(function (k) { delete blob[k]; });
  NEVER_STORED.forEach(function (k) { delete blob[k]; });
  return blob;
}

module.exports = { storedBlob: storedBlob, NEVER_STORED: NEVER_STORED };
