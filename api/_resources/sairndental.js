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
  // Licensing / credentialing (2026-08-24) -- see
  // sql/sairndental_credentials_schema.sql and the Ohio rule seed beside it.
  // dnt_cred_rules holds versioned requirements as data, each carrying a real
  // citation; dnt_credentials is the APPEND-ONLY per-provider record store
  // (state licences, DEA registrations, CE cycles, BLS/CPR certifications).
    'dnt_cred_rules',
    'dnt_credentials',
  // Good faith estimates (2026-09-02) -- No Surprises Act, 45 CFR 149.610. See
  // sql/sairndental_gfe_schema.sql. Handled by the generic DNT_RESOURCES block
  // in api/sd-data.js, and registered there as BOTH financial (it prices a
  // service) and patient-scoped (it names one patient and their date of birth).
    'dnt_gfe',
  // Recall & reactivation outreach (2026-09-02, competitive-gap audit A8) --
  // see sql/sairndental_recall_schema.sql. One row per contact ACTUALLY made
  // about a patient being due back; this app sends nothing itself. Handled by
  // the generic DNT_RESOURCES block and registered as patient-scoped (it names
  // a patient and records what they said) but NOT financial -- it carries no
  // charge, and the hygiene side works this list as much as the front desk.
    'dnt_recall_outreach',
  // Treatment plans (2026-09-02, competitive-gap audit A9) -- see
  // sql/sairndental_treatment_plans_schema.sql. Proposed work, phased and
  // priced, BEFORE any of it is charged; distinct from dnt_charges, which
  // records work already done. Handled by the generic DNT_RESOURCES block and
  // registered as BOTH financial (it prices what the patient is being asked to
  // accept) and patient-scoped (it names one patient and their proposed care).
    'dnt_txplans',
  ],
  // 'evaluate' computes the expiry/CE alert board from stored records and the
  // seeded rules. It READS ONLY and writes nothing -- looking at who is about
  // to lapse must never itself change a credential record. Same compute-only
  // shape as SAIRNcare's alf_compliance_rules 'evaluate', and the reason it is
  // declared here rather than in api/sd-data.js is the 2026-08-24 verb-gate
  // change: the verb belongs next to the resource that owns it.
  extraActions: {
    dnt_credentials: ['evaluate'],
  },
};
