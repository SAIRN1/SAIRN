// api/_resources/sairndental.js
// Resource registry for SAIRNdental.
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
  app: 'sairndental',
  resources: [
  // SAIRNdental (2026-08-10) -- see sql/sairndental_data_schema.sql. All 12 prefixed dnt_.
    'dnt_patients',
    'dnt_providers',
    'dnt_operatories',
    'dnt_provider_hours',
    'dnt_procedure_types',
    'dnt_coverage_rules',
    'dnt_appointments',
    'dnt_charges',
    'dnt_payments',
    'dnt_denial',
    'dnt_ar',
    'dnt_revenue',
  // SAIRNdental availability + booking (2026-08-10) -- see
  // sql/sairndental_availability_booking_schema.sql. dnt_appointments was
  // already added above but gets its OWN dedicated read/write handler
  // below (not the generic DNT_RESOURCES block) because it now has real
  // promoted columns the EXCLUDE constraints check against -- still
  // listed here since this map only gates "is this a known resource
  // string," not which code path handles it.
    'dnt_settings',
    'dnt_referrals',
    'dnt_complaints',
  ],
};
