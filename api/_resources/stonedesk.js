// api/_resources/stonedesk.js
// Resource registry for StoneDesk.
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
  app: 'stonedesk',
  resources: [
  // StoneDesk CRM/Lead Pipeline (2026-08-19) -- see sql/sd_crm_schema.sql. First real server
  // sync this resource has ever had (was pure localStorage) -- also carries the per-lead
  // assignment privacy gate, see the read/write branches below.
    'sd_crm',
  ],
};
