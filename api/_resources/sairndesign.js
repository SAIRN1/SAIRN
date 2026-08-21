// api/_resources/sairndesign.js
// Resource registry for SAIRNdesign.
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
  app: 'sairndesign',
  resources: [
  // SAIRNdesign (2026-08-07) -- see sql/sairndesign_data_schema.sql. sdn_ prefix on every one of
  // these, not just 'sdn_schedule'/'sdn_invoices' which would otherwise collide with the bare
  // 'schedule'/'invoices' names already claimed above -- consistency across all 18, not a mixed
  // scheme. Closes the whole-app sync gap described in that SQL file's header.
    'sdn_clients',
    'sdn_projects',
    'sdn_specitems',
    'sdn_proposals',
    'sdn_vendors',
    'sdn_samplerequests',
    'sdn_team',
    'sdn_moodboards',
    'sdn_colorcodes',
    'sdn_pos',
    'sdn_invoices',
    'sdn_timeentries',
    'sdn_schedule',
    'sdn_samples',
    'sdn_contracts',
    'sdn_referrals',
    'sdn_discounts',
    'sdn_roomdims',
  ],
};
