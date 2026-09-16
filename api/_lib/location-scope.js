// api/_lib/location-scope.js
// ---------------------------------------------------------------------------
// ONE MODULE OWNS "WHICH LOCATION DID THIS ROW HAPPEN AT". Item 4's shared
// half, and it is deliberately SMALL -- see the boundary at the bottom, which
// is the more useful part of this file.
//
// ── WHY THIS EXISTS: MEASURED, NOT PROPOSED ────────────────────────────────
// Two apps independently built the same location stamp, two sessions apart:
//
//   api/_lib/dnt-location.js:37    const DEFAULT_LOCATION_ID = 'LOC-DEFAULT';
//   api/_lib/roofing-locations.js:38  const DEFAULT_LOCATION_ID = 'LOC-DEFAULT';
//
// and their stampLocation() functions are behaviourally identical: same trim,
// same 64-character cap, same fall back to the default rather than refusing a
// write. On top of that the literal 'LOC-DEFAULT' is hardcoded in 30+ further
// places across four apps' JS, HTML and SQL -- including four Postgres column
// DEFAULTs and a coalesce inside rf_allocate_invoice_number.
//
// THAT IS `isDate` DEFINED FOURTEEN TIMES, ONE LAYER UP. Item 94 already paid
// for that lesson on calendar dates and fixed it with exactly this shape: one
// deep module the rest of the platform calls. This is the same fix applied to
// the concept the platform is currently mid-way through reinventing for the
// third time.
//
// ── WHAT IS DELIBERATELY *NOT* HERE, AND THIS IS THE DESIGN ────────────────
// THE ROLL-UPS ARE NOT UNIFIED, because they are not the same computation, and
// discovering that is what stopped this module from being three times the size:
//
//   api/_lib/dnt-rollup.js          ONE AXIS. Buckets are per LOCATION.
//                                   Its interesting signal is
//                                   `unregistered_location_ids` -- an id on
//                                   real rows the registry does not know.
//   api/_lib/roofing-consolidation.js
//                                   TWO AXES. Buckets are per legal ENTITY,
//                                   with location->entity as a mapping, and it
//                                   reports a PROBLEM when a location names an
//                                   entity not on file. UNKNOWN_LOCATION and
//                                   UNASSIGNED are separate buckets on purpose:
//                                   "one is assign the branch, the other is
//                                   create the branch".
//
// So LOCATION and BRAND/ENTITY ARE TWO AXES, not one, and roofing already
// models both while dental models one. Folding them together would either give
// dental an entity concept it does not have or flatten roofing's -- and the
// platform-wide item names this work "multi-location/multi-brand" as though it
// were a single thing. It is not. **Roofing is the reference implementation for
// the two-axis model; nothing here replaces it.**
//
// ── AND WHAT STONEDESK AND SAIRNSENIOR ACTUALLY HAVE, since both are named as
// ── having this problem and neither has the shape the name implies ─────────
//   StoneDesk       `sd_locations` is a yard REGISTRY and nothing stamps a
//                   location onto a StoneDesk row. Its gap row reads "BUILT --
//                   ATTRIBUTION, NOT ACCESS PARTITIONING"; measured, it is not
//                   attribution yet either. A list of yards, unattached.
//   SAIRNsenior     `sen_franchise_agreements` is a franchisor/franchisee
//                   BRAND relationship. That is the second axis, not the first,
//                   and it is the closest thing on the platform to roofing's
//                   entity layer.
//
// SO THE FIRST MIGRATION IS NOT A NEW APP. It is the two modules that already
// hold identical copies of this function, before a third is written.

'use strict';

// The implicit location every pre-existing and single-site row belongs to.
// A real registry row MAY later be created carrying this id; nothing here
// assumes the string is absent from any app's registry, and both callers
// already relied on that.
const DEFAULT_LOCATION_ID = 'LOC-DEFAULT';

// Both copies used 64. Kept, rather than widened to the larger of the two,
// because a cap that changes on consolidation would silently start accepting
// ids the older rows could never have carried.
const MAX_LOCATION_ID_LEN = 64;

/**
 * Return a shallow copy of `payload` with `location_id` guaranteed present
 * and bounded.
 *
 * A caller-supplied value is TRUSTED BUT LENGTH-CAPPED; anything absent,
 * blank, non-string or over-length falls back to the default rather than
 * being rejected. That is not leniency for its own sake and both original
 * copies argued it the same way: refusing a write here would break every
 * existing single-location client that has never heard of locations, and a
 * record must never fail to save because of an OPTIONAL attribution field.
 *
 * seam-check: server-supplied location_id
 *
 * Carried over from dnt-location.js verbatim, and the reason is worth keeping
 * with it. tools/sairn_seam_check.py's model is "the engine reads X, so the
 * endpoint must send X" -- correct for a calculating engine and WRONG for a
 * stamper. This function exists precisely to SUPPLY location_id when the
 * caller has none. The declaration lives next to the contract it describes so
 * that a stale exception shows up in the diff of the file it excuses.
 */
function stampLocation(payload) {
  const out = Object.assign({}, payload || {});
  const raw = out.location_id;
  const clean = (typeof raw === 'string') ? raw.trim() : '';
  out.location_id = (clean && clean.length <= MAX_LOCATION_ID_LEN)
    ? clean
    : DEFAULT_LOCATION_ID;
  return out;
}

/**
 * Is `id` the implicit default rather than a real registry id?
 *
 * Added here rather than copied a third time: sairnroofing.html asks this
 * question inline twice (`id==='LOC-DEFAULT'`), and a UI that hardcodes the
 * sentinel is the next place the constant drifts.
 */
function isDefaultLocation(id) {
  return (typeof id === 'string' ? id.trim() : '') === DEFAULT_LOCATION_ID;
}

module.exports = {
  DEFAULT_LOCATION_ID: DEFAULT_LOCATION_ID,
  MAX_LOCATION_ID_LEN: MAX_LOCATION_ID_LEN,
  stampLocation: stampLocation,
  isDefaultLocation: isDefaultLocation
};
