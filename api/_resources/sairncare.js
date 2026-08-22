// api/_resources/sairncare.js
// Resource registry for SAIRNcare.
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
  app: 'sairncare',
  resources: [
  // SAIRNcare (assisted living) residents (2026-08-20) -- see
  // sql/sairncare_clients_schema.sql. Ground-up app, real resident
  // privacy gate from day one, same shape as sen_clients but with a
  // real FOUR-tier gate instead of three -- Activities Coordinator gets
  // read-only broad roster access with zero clinical/billing write
  // authority, a genuinely different tier than nursing's broad-read-AND-
  // edit. Bespoke branch below.
    'alf_clients',
  // SAIRNcare (2026-08-20) -- staff roster, closing the SAIRNsenior Phase 1
  // gap (Caregivers/Staff shipped local-only there) proactively from the
  // start instead of leaving it for a later batch. See
  // sql/sairncare_staff_schema.sql's own header for the gate reasoning.
    'alf_staff',
  // SAIRNcare MAR (2026-08-20) -- see sql/sairncare_mar_schema.sql's own
  // header for the full research-grounded reasoning and entry_type shapes.
    'alf_mar',
  // SAIRNcare Billing (2026-08-20) -- see sql/sairncare_billing_schema.sql's
  // own header for the private-pay vs Medicaid HCBS separation reasoning.
    'alf_billing',
  // SAIRNcare Compliance/Incident Reporting (2026-08-20) -- see
  // sql/sairncare_incidents_schema.sql's own header for the asymmetric
  // read/write reasoning and the real research this is grounded in.
    'alf_incidents',
  // SAIRNcare Activities calendar (2026-08-20) -- see
  // sql/sairncare_activities_schema.sql's own header for the broad-read/
  // narrow-write reasoning.
    'alf_activities',
  // SAIRNcare facility profile + licensing jurisdiction (2026-08-21) -- see
  // sql/sairncare_facility_schema.sql's own header. This replaces a
  // localStorage-only 'alf_facility' key; licensing_state is the field that
  // forced it server-side, since a licensed entity's state is a legal fact
  // that must be identical on every device before any compliance-rules
  // engine can trust it. Keyed by facility_id, not license_hash alone.
    'alf_facility',
  // SAIRNcare passive-monitoring signal log (2026-08-21, Phase 0 item 3) --
  // see sql/sairncare_signals_schema.sql's own header. Append-only, no
  // risk_score column -- reads return a {have, need} coverage contract for
  // a future derived view, never a fabricated number, since no monitoring
  // device is actually wired up yet.
    'alf_signals',
  // SAIRNcare payer/billing-routing engine (2026-08-22, Phase 1) -- see
  // sql/sairncare_payer_rules_schema.sql. alf_payer_rules holds VERSIONED
  // state billing rules as data (Indiana's mandate was published and paused
  // within one month, which is why they are not hardcoded); alf_claim_routes
  // is the append-only log of routing decisions actually made.
    'alf_payer_rules',
    'alf_claim_routes',
  ],
};
