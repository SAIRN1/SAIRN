// api/_resources/sairnroofing.js
// Resource registry for SAIRNroofing.
//
// Adding a resource: add the name here, and add its handler branch in
// api/sd-data.js as before. Nothing else needs editing. See
// api/_resources/index.js for why this per-app-file split exists.

module.exports = {
  app: 'sairnroofing',
  resources: [
  // SAIRNroofing jobs (2026-08-24, Phase 1) -- see
  // sql/sairnroofing_jobs_schema.sql. Ground-up app, real assignment-based
  // privacy gate from day one, three-tier (management/broad-read/narrow),
  // same shape as sen_clients. Bespoke branch below.
    'rf_jobs',
  // SAIRNroofing measurement photos (2026-08-24, Phase 2) -- see
  // sql/sairnroofing_photos_schema.sql. Same tier gate as rf_jobs, keyed by
  // job_id. Bespoke branch below.
    'rf_photos',
  // Certifications + licensing (2026-08-24, Phase 3a) -- see
  // sql/sairnroofing_certifications_schema.sql and the Ohio rule seed beside
  // it. rf_cert_rules holds versioned requirements as data, each with a real
  // citation; rf_certifications is the APPEND-ONLY per-employee record store.
    'rf_cert_rules',
    'rf_certifications',
  // Insurance claims + photo evidence (2026-08-24, Phase 3b) -- see
  // sql/sairnroofing_claims_schema.sql. rf_claims is a MUTABLE claim record
  // (evolves over a 45-90 day lifecycle); rf_claim_photos is APPEND-ONLY
  // tagged evidence. The money lifecycle lives as separate fields inside
  // rf_claims.data, normalized by api/_lib/roofing-claims.js.
    'rf_claims',
    'rf_claim_photos',
  // Contingency agreement + per-state rescission rules (2026-08-25, Phase 5
  // final piece) -- see sql/sairnroofing_agreements_schema.sql and the Ohio
  // rule seed beside it. rf_contingency_rules holds the per-state rescission
  // requirements as data, each with a real citation; rf_claim_agreements is the
  // APPEND-ONLY signed-document record, where a rescission is a second row.
    'rf_contingency_rules',
    'rf_claim_agreements',
  // Multi-location + crew scheduling (2026-08-25, Phase 4a) -- see
  // sql/sairnroofing_locations_schema.sql. rf_locations is the branch
  // registry; rf_schedule is mutable crew days (a schedule genuinely changes,
  // unlike the append-only evidence tables above). location_id is ATTRIBUTION
  // only -- it is deliberately NOT an access-control axis, see
  // api/_lib/roofing-locations.js.
    'rf_locations',
    'rf_schedule',
  // Manufacturer certification programmes at COMPANY level (2026-08-25,
  // Phase 4d) -- see sql/sairnroofing_programs_schema.sql. Voluntary
  // commercial programmes, NOT regulation: deliberately a different table and
  // a different posture from rf_cert_rules, which carries state licensing.
  // Nothing is seeded; the contractor enters their own thresholds citing their
  // own programme agreement.
    'rf_company_programs',
  // Estimate -> proposal -> invoice (2026-08-25, Phase 4b) -- see
  // sql/sairnroofing_billing_schema.sql. rf_proposals is APPEND-ONLY and every
  // issued row SNAPSHOTS its price rather than pointing at the live estimate;
  // rf_invoices is a mutable header whose payments the SERVER appends. There is
  // no balance column anywhere -- it is derived on read.
    'rf_proposals',
    'rf_invoices',
  ],
  // 'evaluate' computes the expiry board from stored records and seeded rules.
  // Reads only, writes nothing -- looking at who is about to lapse must never
  // change a credential record. Same compute-only shape as SAIRNcare's
  // alf_compliance_rules and SAIRNdental's dnt_credentials.
  extraActions: {
    rf_certifications: ['evaluate'],
    // 'reconcile' (Phase 3c) computes the supplement worksheet -- a
    // DETERMINISTIC comparison of the adjuster's estimate against the measured
    // scope. Reads the claim and its job, writes nothing. Never an LLM opinion.
    rf_claims: ['reconcile'],
    // 'agreement_status' (Phase 5) computes the rescission clock from the
    // claim's append-only agreement chain and the state rule. Reads only.
    // Looking at whether a cancellation window is open must never advance,
    // extend or close it -- same compute-only shape as 'reconcile'.
    rf_claim_agreements: ['agreement_status'],
    // 'set_status' (Phase 4a) lets a crew member mark their own scheduled day.
    // Status ONLY -- it cannot move the day, change the job or touch the crew,
    // so it is not a way around the management-only schedule write.
    rf_schedule: ['set_status'],
    // 'evaluate' (Phase 4d) scores the company against the requirements the
    // contractor entered, computing the roster-credential share from the real
    // Phase 3a rf_certifications store and treating every business fact as
    // self-reported. Reads only, writes nothing.
    rf_company_programs: ['evaluate'],
    // Phase 4b. 'issue' allocates the gapless invoice number and is idempotent
    // -- re-issuing must never burn a second number. 'add_payment' appends ONE
    // entry server-side. 'reconcile_claim' compares the invoice against the
    // linked claim and writes nothing to either.
    rf_invoices: ['issue', 'add_payment', 'reconcile_claim'],
  },
};
