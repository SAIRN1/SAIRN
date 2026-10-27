// api/_lib/jsonb-text-bytes.js
// ---------------------------------------------------------------------------
// The byte length Postgres's `octet_length(data::text)` reports for a value
// stored in a jsonb column -- the measure every `*_data_size` CHECK
// constraint on this platform uses.
//
// WHY IT EXISTS (cody b52, hover H2 seq1109). api/sd-data.js gave
// dnt_appointments and rf_claim_photos a cap EQUAL to their table's
// constraint so that an oversized write gets a clear 413 rather than an
// opaque store error. The numbers were equal; the measures were not. The gate
// counted compact JSON (`JSON.stringify`); jsonb's text output puts a space
// after every ':' and ',', so the database counts more bytes than the gate
// did. About 29 bytes on a normal booking, about 25% on an array-heavy record
// -- and in that window the staff user got the unclassified-store message the
// equal cap was there to prevent.
//
// THE RULES, from Postgres's jsonb output: `{"a": 1, "b": [1, 2]}`, `{}` and
// `[]` when empty. Key order and duplicate keys do not change the length.
// Strings are escaped as JSON escapes them and non-ASCII is raw UTF-8, which
// is what JSON.stringify produces. KNOWN GAP, said rather than hidden: a
// number JS prints in exponent form (1e+21) Postgres prints in full; no
// stored record on this platform carries such a number.
// ---------------------------------------------------------------------------

'use strict';

function valueBytes(v) {
  if (v === null || typeof v !== 'object') {
    return Buffer.byteLength(JSON.stringify(v), 'utf8');
  }
  if (Array.isArray(v)) {
    if (v.length === 0) return 2;
    let n = 2 + 2 * (v.length - 1);                    // [ ] and ", " between
    for (const item of v) n += valueBytes(item);
    return n;
  }
  const keys = Object.keys(v);
  if (keys.length === 0) return 2;
  let n = 2 + 2 * (keys.length - 1);                   // { } and ", " between
  for (const k of keys) {
    n += Buffer.byteLength(JSON.stringify(k), 'utf8') + 2 + valueBytes(v[k]);  // "k": v
  }
  return n;
}

/**
 * Bytes of `value` as Postgres jsonb text. The value is first round-tripped
 * through JSON so that whatever JSON.stringify drops (undefined, functions)
 * is dropped here too -- the same value the write would store.
 */
function jsonbTextBytes(value) {
  const s = JSON.stringify(value);
  if (s === undefined) return 0;
  return valueBytes(JSON.parse(s));
}

module.exports = { jsonbTextBytes };
