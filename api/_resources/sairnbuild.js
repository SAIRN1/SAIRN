// api/_resources/sairnbuild.js
// Resource registry for SAIRNbuild.
//
// WHY THIS FILE EXISTS: api/sd-data.js used to carry one shared RESOURCES map
// that every SAIRN app appended to, plus a hand-maintained error-message
// string listing the same names. Both were single shared lines, so any two
// sessions adding a resource in parallel collided on every push -- that was
// the cause of every api/sd-data.js merge conflict, not the request handlers,
// which append in separate regions and merge cleanly.
//
// Each app now owns its own registry file. sd-data.js merges them at load and
// GENERATES the error string from the merge, so the two can no longer drift
// apart (they already had: employee_profile was a valid resource missing from
// the hand-maintained list).
//
// Adding a resource: add the name here, and add its handler branch in
// api/sd-data.js as before. Nothing else needs editing.
//
// The request-handling branches themselves were deliberately NOT moved -- they
// close over ~15 handler-local bindings and serve 11 live apps, and they were
// never the source of the collisions.

module.exports = {
  app: 'sairnbuild',
  resources: [
  // SAIRNbuild Bids & Proposals real server sync (2026-08-20) -- see
  // sql/sairnbuild_bids_schema.sql. Task 3 of the platform sales-lead-
  // privacy rule (StoneDesk's sd_crm was item 1, SAIRNdesign's sdn_clients
  // was item 2). Had ZERO server sync before this -- confirmed by grep, no
  // bld_bids reference anywhere in this file, saveBid() was pure
  // localStorage. Handled by its own bespoke read/write branch below (like
  // sdn_clients), not the generic-loop pattern, because of the privacy
  // gate -- this map only gates "is this a known resource string."
    'bld_bids',
  // SAIRNbuild Training Needs Assessment (2026-08-20) -- see
  // sql/sairnbuild_tna_schema.sql. Hennessy-Hicks-style importance/
  // performance-gap instrument (structure verified via live web research
  // before building, item wording adapted for construction -- see that
  // SQL file's header for the full provenance disclosure). Bespoke branch
  // below, same reasoning as bld_bids/sdn_clients -- subject-based
  // visibility, not assignee-based, so it needed its own read/write logic
  // rather than reusing the bld_bids shape verbatim.
    'bld_tna',
  ],
};
