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
  // SAIRNsenior agency-level settings (2026-08-27) -- see
  // sql/sairnsenior_settings_schema.sql. Keyed rows, one per setting, same
  // shape as rf_settings. Holds 'agency_profile' and 'evv_config', both of
  // which previously lived ONLY in localStorage -- a federally-mandated EVV
  // configuration that did not survive a browser-data clear and was invisible
  // to everyone else at the agency, while the panel reported it as saved.
  // READ is open to any authenticated employee; WRITE is management-only.
  // REGISTERED DELIBERATELY, not as an afterthought: a table with no registered
  // resource is invisible to the no-credentials provisioning probe (a
  // PostgREST 404 maps to provisioned:false on read), which is how 41 declared
  // tables ended up unmeasurable -- see docs/SAIRN-OPEN-WORK-INDEX.md.
  // Bespoke branch below.
    'sen_settings',
  // SAIRNsenior referral-source CRM (2026-09-02, competitive-gap audit A7) --
  // see sql/sairnsenior_referrals_schema.sql. sen_referral_sources is the
  // hospital / SNF / discharge-planner / physician-practice relationship;
  // sen_referrals is one referred person and what happened to them. Gated on
  // the INTAKE roles (management + coordinator + scheduler), not on management
  // alone and not on every employee -- a referral names a prospective client, so
  // a caregiver is out, but a coordinator takes the call and must be in.
  // Bespoke branch below, shared by both.
    'sen_referral_sources',
    'sen_referrals',
  // SAIRNsenior caregiver training hours (2026-09-02, competitive-gap audit
  // A6) -- see sql/sairnsenior_training_schema.sql. sen_training_rules holds
  // the in-service/pre-service requirement as DATA carrying its own citation
  // and its own scope (programme + aide type), because the real figures differ
  // by both -- 12 hours under 42 CFR 484.80(d) against 6 under ORC
  // 5164.913(A)(1). sen_training_records is what a caregiver actually
  // completed. Same intake-role gate and same shared branch as the referral
  // resources above: schedulers and coordinators decide who can be sent to a
  // visit and need to see standing; a caregiver does not read the roster's.
    'sen_training_rules',
    'sen_training_records',
  // SAIRNsenior caregiver hiring funnel (2026-09-02, competitive-gap audit
  // A5) -- see sql/sairnsenior_applicants_schema.sql. One person who applied,
  // the source that sent them, the stage they reached, and once hired the
  // sen_caregivers row they became. Retention is NOT stored: it is measured
  // from sen_visits, so the answer to "which sources produce caregivers who
  // stay" cannot drift away from the work those caregivers actually did.
  // Same intake-role gate and same shared branch as the referral and training
  // resources above: an applicant is employment data about someone who is not
  // yet staff, so a caregiver is out and the coordinator who screens the call
  // is in.
    'sen_applicants',
  // SAIRNsenior branches (2026-09-02, competitive-gap audit B1) -- see
  // sql/sairnsenior_branches_schema.sql. An office the agency operates from,
  // and the STATE it operates in. Gate is SPLIT and matches sen_settings, not
  // the referral family: READ is open to any signed-in employee because a
  // caregiver's own roster row names a branch and the name has to resolve or
  // the screen shows a raw id; WRITE is management-only, because opening or
  // closing an office is not a scheduling decision. Bespoke branch below.
    'sen_branches',
  // SAIRNsenior payer contracts (2026-09-02, competitive-gap audit B4) --
  // see sql/sairnsenior_payer_contracts_schema.sql. What a payer pays per
  // hour, for a stated period, optionally scoped to one state. Gate is
  // MANAGEMENT-ONLY for read AND write, matching sen_claims rather than the
  // referral family: a contracted rate is financial data and a caregiver,
  // coordinator or scheduler has no minimum-necessary reason to see what
  // each payer pays. Bespoke branch below.
    'sen_payer_contracts',
  // SAIRNsenior payer authorisations (2026-09-02, competitive-gap audit A3) --
  // see sql/sairnsenior_authorizations_schema.sql. What a payer approved for
  // one client: the authorisation number, the period, and how many units.
  // Gate is SPLIT and deliberately NOT the contract gate directly above:
  // READ is open to management, coordinators and schedulers because remaining
  // units are SCHEDULING CAPACITY and the person booking the next visit is
  // exactly who needs them -- and an authorisation carries units, not money,
  // so it does not leak what a payer pays. WRITE is management-only: recording
  // what a payer approved is not a scheduling decision. Consumption is NOT
  // stored on this resource and is computed from sen_visits. Bespoke branch
  // below.
    'sen_authorizations',
  ],
  // 'readiness' is COMPUTE-ONLY and owned by sen_visits alone -- same carve-out
  // shape as SAIRNcare's 'route'/'evaluate'/'derive_charges', and narrow for the
  // same reason: a verb reaches exactly the resource whose app granted it.
  // It PERSISTS NOTHING. Checking whether a visit could be submitted must never
  // itself modify the visit, which is why it is a separate verb rather than a
  // flag on 'read'.
  extraActions: {
    sen_visits: ['readiness'],
  },
};
