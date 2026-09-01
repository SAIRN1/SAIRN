// api/_lib/dnt-location.js
// SAIRNdental multi-location: WRITE-SIDE CAPTURE ONLY.
//
// WHY THIS EXISTS, AND WHY IT IS DELIBERATELY THIS SMALL:
// SAIRNdental's tenancy boundary is license_hash -- one license, one
// practice. There was no location concept anywhere: a costing pass on
// 2026-08-24 grepped location_id/practice_id/office_id/multi-location
// across api/sd-data.js, api/sairndental/*.js and sairndental.html and
// found zero matches.
//
// Of the whole multi-location problem, exactly one part has a deadline:
// CAPTURING which location a row belongs to at the moment it is written.
// Consolidated reporting, a per-location booking page, and a client-side
// location selector can all be built later at the same cost. Attribution
// cannot -- a charge, payment, AR entry or appointment recorded without a
// location can never be assigned to one afterwards, because the
// information was never collected. That asymmetry is the entire reason
// this ships now and the rest is held.
//
// It is invisible to a single-location practice: every write with no
// location_id is stamped DEFAULT_LOCATION_ID, so existing data and
// existing UI behave exactly as before.
//
// NOT IN SCOPE (held deliberately, see SAIRN-BACKLOG.md):
//   - splitting dnt_settings into one row per location (booking_slug is
//     globally unique and there is one settings row per license, so a
//     second location cannot have its own public booking page yet)
//   - filtering api/sairndental/public-availability.js by location
//   - the client location selector across 12 accessors / 17 renderers
//   - any server-side cross-location aggregation

'use strict';

// The implicit location every pre-existing and single-practice row belongs
// to. A real registry entry may later be given this id; nothing here
// assumes the string is absent from dnt_settings.data.locations.
const DEFAULT_LOCATION_ID = 'LOC-DEFAULT';

const MAX_LOCATION_ID_LEN = 64;
const MAX_LOCATION_NAME_LEN = 128;
const MAX_LOCATIONS = 50;

// Returns a shallow copy of payload with location_id guaranteed present.
// A caller-supplied location_id is trusted but bounded; anything absent,
// blank, non-string or over-length falls back to the default rather than
// being rejected, because refusing a write here would break every existing
// single-location client that has never heard of locations.
//
// seam-check: server-supplied location_id
//
// Declared for tools/sairn_seam_check.py, and the reason is the interesting
// part. That tool's model is "the engine reads X, so the endpoint must send
// X" -- which is right for a calculating engine and WRONG for a stamper. This
// function exists precisely to SUPPLY location_id when the caller has none;
// api/sairndental/public-book.js omits it deliberately (see the comment at its
// call site about dnt_settings not yet being split per location). Without this
// line the checker reports a defect on code that is behaving exactly as
// designed. The declaration lives here, next to the contract it describes,
// rather than in the tool -- a stale exception is then visible in the diff of
// the file it excuses.
function stampLocation(payload) {
  const out = Object.assign({}, payload || {});
  const raw = out.location_id;
  const clean = (typeof raw === 'string') ? raw.trim() : '';
  out.location_id = (clean && clean.length <= MAX_LOCATION_ID_LEN) ? clean : DEFAULT_LOCATION_ID;
  return out;
}

// Validates dnt_settings.data.locations -- the minimal registry. Kept in
// settings rather than a new dnt_locations table on purpose: a new table
// needs a migration nobody can run or verify from this environment, and
// the registry is small (2-50 rows, rarely edited). It gets revisited when
// dnt_settings is split per location, which is the held work above.
// Absent locations is valid -- a single-location practice never sets it.
function validateLocations(locations) {
  if (locations === undefined || locations === null) return { ok: true };
  if (!Array.isArray(locations)) {
    return { ok: false, code: 'BAD_LOCATIONS', message: 'locations must be an array' };
  }
  if (locations.length > MAX_LOCATIONS) {
    return { ok: false, code: 'BAD_LOCATIONS', message: 'locations may not exceed ' + MAX_LOCATIONS + ' entries' };
  }
  const seen = Object.create(null);
  for (let i = 0; i < locations.length; i++) {
    const loc = locations[i];
    if (!loc || typeof loc !== 'object') {
      return { ok: false, code: 'BAD_LOCATIONS', message: 'each location must be an object with id and name' };
    }
    const id = (typeof loc.id === 'string') ? loc.id.trim() : '';
    const name = (typeof loc.name === 'string') ? loc.name.trim() : '';
    if (!id || id.length > MAX_LOCATION_ID_LEN) {
      return { ok: false, code: 'BAD_LOCATIONS', message: 'each location needs a non-empty id of at most ' + MAX_LOCATION_ID_LEN + ' characters' };
    }
    if (!name || name.length > MAX_LOCATION_NAME_LEN) {
      return { ok: false, code: 'BAD_LOCATIONS', message: 'each location needs a non-empty name of at most ' + MAX_LOCATION_NAME_LEN + ' characters' };
    }
    // A duplicate id would silently split one location's history in two.
    if (seen[id]) {
      return { ok: false, code: 'BAD_LOCATIONS', message: 'duplicate location id: ' + id };
    }
    seen[id] = true;
  }
  return { ok: true };
}

module.exports = {
  DEFAULT_LOCATION_ID: DEFAULT_LOCATION_ID,
  MAX_LOCATIONS: MAX_LOCATIONS,
  stampLocation: stampLocation,
  validateLocations: validateLocations
};
