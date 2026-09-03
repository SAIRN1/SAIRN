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
  // -- THE BUSINESS RECORD (2026-09-03) ------------------------------------
  // Until this, SAIRNbuild wrote THIRTY-SEVEN localStorage collections and
  // had server sync for exactly TWO of them. A builder's jobs, job costs,
  // draw schedule, lien waivers, safety incidents and daily logs lived in one
  // browser. Clearing it lost the company's records with no copy anywhere.
  //
  // All handled by the generic BLD_RESOURCES read/write pair in
  // api/sd-data.js -- same shape as LEG_RESOURCES and SDN_RESOURCES. See
  // sql/sairnbuild_data_schema.sql, which must be run before any of these
  // answer anything but 503 NOT_PROVISIONED.
  // The spine. Every other record below references a job_id.
    'bld_jobs',
  // Job costing: budget / committed / actual per cost code.
    'bld_costs',
  // Contract modifications. Money and scope, in writing.
    'bld_change_orders',
  // Payment applications and retainage.
    'bld_draws',
  // Legal instruments. A lost waiver is a real financial exposure.
    'bld_lien_waivers',
  // The contemporaneous site record -- what construction disputes turn on.
    'bld_daily_logs',
  // Safety incidents. OSHA-relevant.
    'bld_incidents',
  // Inspection results and re-inspection dates.
    'bld_inspections',
  // Toolbox talks delivered, with attendance.
    'bld_toolbox_talks',
  // Requests for information -- the contract-administration trail.
    'bld_rfis',
  // Submittals and their approval state.
    'bld_submittals',
  // Punch items at closeout.
    'bld_punchlist',
  // Warranty claims after handover.
    'bld_warranty',
  // Subcontractor roster.
    'bld_subs',
  // Bids received FROM subs (distinct from bld_bids, which is bids OUT).
    'bld_sub_bids',
  // Supplier roster.
    'bld_suppliers',
  // Purchase orders.
    'bld_pos',
  // Material deliveries received.
    'bld_deliveries',
  // Payments issued.
    'bld_checks',
  // Labour hours -- what job costing is computed from.
    'bld_timesheet',
  // Task assignments.
    'bld_tasks',
  // The build schedule.
    'bld_schedule_entries',
  // Client selections and their deadlines.
    'bld_selections',
  // Document register with version history. Metadata only, no file bytes.
    'bld_documents',
  // Equipment register.
    'bld_equipment',
  // Client and sub communication log.
    'bld_comm_log',
  // Referral sources.
    'bld_referrals',
  // Client reviews.
    'bld_reviews',
  // The price book estimates are built from.
    'bld_price_points',
  // AI site-photo findings. Text only -- no image bytes are stored.
    'bld_photo_analyses',
  // DELIBERATELY NOT SYNCED, and why -- so the next reader does not have to
  // re-derive the judgement or assume it was an oversight:
  //   bld_bids -- already synced, and by a BESPOKE branch with a privacy gate (2026-08-20). Not folded into the generic block -- that would drop the gate.
  //   bld_tna -- already synced, bespoke branch, subject-based visibility.
  //   bld_company_profile -- a single object, not a keyed collection. Needs its own one-row shape.
  //   bld_settings -- app configuration, not a business record.
  //   bld_role -- a client-side display value. The real role comes from the session token.
  //   bld_seeded -- a local seed marker. Syncing it would suppress seeding on a second device.
  //   bld_integrations -- connection configuration. Syncing config across devices needs its own conflict story, and this is not it.
  //   bld_ai_chat -- an unbounded conversation transcript, not a business record.
  ],
};
