// api/_resources/sairnlegacy.js
// Resource registry for SAIRNlegacy.
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
  app: 'sairnlegacy',
  resources: [
  // SAIRNlegacy (2026-08-07) -- see sql/sairnlegacy_data_schema.sql. All 36 prefixed leg_.
    'leg_aftercare',
    'leg_bookings',
    'leg_cases',
    'leg_catererorders',
    'leg_caterers',
    'leg_certs',
    'leg_clergy',
    'leg_clergybookings',
    'leg_cremations',
    'leg_custodylog',
    'leg_deathrecords',
    'leg_dispatches',
    'leg_documents',
    'leg_facilities',
    'leg_floristorders',
    'leg_florists',
    'leg_gplservices',
    'leg_guestbook',
    'leg_insurance',
    'leg_invoices',
    'leg_keepsakeorders',
    'leg_keepsakes',
    'leg_liverybookings',
    'leg_liveryvendors',
    'leg_maintenance',
    'leg_memorials',
    'leg_merch_catalog',
    'leg_merch_units',
    'leg_monuments',
    'leg_obituaries',
    'leg_petcases',
    'leg_plots',
    'leg_preneed',
    'leg_processions',
    'leg_tributes',
    'leg_vehicles',
  ],
};
