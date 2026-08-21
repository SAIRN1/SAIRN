// api/_resources/sairnsenior.js
// Resource registry for SAIRNsenior.
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
  app: 'sairnsenior',
  resources: [
  // SAIRNsenior client (home-care recipient) data (2026-08-20) -- see
  // sql/sairnsenior_clients_schema.sql. Ground-up app, built with a real
  // HIPAA minimum-necessary privacy gate from day one -- a caregiver only
  // ever sees clients assigned to them; owner/billing (management) see
  // every client. Bespoke branch below, same shape as bld_bids/sdn_clients/
  // sd_crm -- assignee-based visibility, not the generic resource loop.
    'sen_clients',
  // SAIRNsenior caregiver/staff roster (2026-08-20, closing the Phase 1
  // disclosed gap) -- see sql/sairnsenior_caregivers_schema.sql. Lighter
  // gate than sen_clients: readable by any authenticated employee (a
  // scheduler/coordinator genuinely needs the whole roster to staff a
  // visit), writable only by management (owner/billing). Bespoke branch
  // below, not the generic loop, for that read-broad/write-narrow shape.
    'sen_caregivers',
  // SAIRNsenior scheduled visits + EVV (2026-08-20) -- see
  // sql/sairnsenior_visits_schema.sql. Combines scheduling and Electronic
  // Visit Verification in one resource (EVV verifies a scheduled visit,
  // it isn't a separate concept). Assignee-based privacy gate like
  // sen_clients, but with a field-level write split the client gate
  // doesn't need: scheduling fields are writable by management/
  // coordinator/scheduler, EVV clock-in/out fields are writable ONLY by
  // the assigned caregiver. Bespoke branch below.
    'sen_visits',
  // SAIRNsenior billing claims (2026-08-20) -- see
  // sql/sairnsenior_claims_schema.sql. Financial/billing data, not
  // clinical assignment data -- management (owner/billing) only, both
  // read and write, no assignee-based visibility at all. A claim
  // references a completed EVV-verified visit, matching the app's own
  // real SOP User Guide's Ready-to-Bill workflow. Bespoke branch below.
    'sen_claims',
  ],
};
