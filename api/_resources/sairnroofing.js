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
  // Company-level settings (2026-08-26) -- see sql/sairnroofing_settings_schema.sql.
  // Keyed rows, one per setting, so this is the last settings migration this
  // app needs. Currently holds 'damage_threshold' for the repair-vs-replace
  // engine. REGISTERED DELIBERATELY, not as an afterthought: a table with no
  // registered resource is invisible to the cheap no-credentials provisioning
  // probe (api/sd-data.js maps a PostgREST 404 to provisioned:false on read),
  // and 41 declared tables are already blind to it for exactly that reason --
  // see docs/SAIRN-OPEN-WORK-INDEX.md. Registering it on day one keeps this
  // one out of that list.
    'rf_settings',
  // Subcontractor directory, compliance and assignments (2026-09-02) -- see
  // sql/subcontractor_compliance_schema.sql and api/_lib/subcontractor-
  // compliance.js. Tier-A gap A3 from the worldwide competitive-gap audit:
  // scheduling, COI/licence/W-9 tracking and payment against a job.
  //
  // THESE TWO ARE UNPREFIXED BECAUSE THEY ARE SHARED. StoneDesk already built
  // this once (sd_subs / sd_sub_auth / sd_sub_jobs) and SAIRNbuild is the
  // obvious third consumer; a second and third per-app implementation is the
  // duplication CLAUDE.md records as SAIRNsenior's root cause. They carry
  // app_id so one table serves every app while keeping tenants apart, the
  // same convention as `employees` and `business_profiles`.
  //
  // Registered on day one for the reason rf_settings' note gives: a table with
  // no registered resource is invisible to the cheap provisioning probe.
    'subcontractors',
    'sub_assignments',
  // Manufacturer warranty tiers and per-job registration (2026-09-02) -- see
  // sql/sairnroofing_warranties_schema.sql and api/_lib/roofing-warranties.js.
  // Tier-A gap A1 from the worldwide competitive-gap audit, which recorded ZERO
  // occurrences of "warranty" anywhere in this app (re-verified 2026-09-02).
  //
  // APP-PREFIXED, the opposite call from the two above and deliberately: a
  // shingle warranty gated on GAF Master Elite standing is roofing, and it
  // hangs off rf_company_programs, which is already roofing-only. Generalising
  // it now would carry a dependency from a platform table into an rf_ table.
  //
  // Registered on day one for the reason rf_settings' note gives.
    'rf_warranty_tiers',
    'rf_job_warranties',
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
    // 'assess_damage' (2026-08-26) computes the per-slope repair-vs-replace
    // EVIDENCE assessment from slope rows on the claim, against the company's
    // configured threshold in rf_settings. Reads only -- looking at whether a
    // slope meets a threshold must never record that it does. The snapshot of
    // the threshold used is written by the ordinary rf_claims WRITE, not here,
    // for exactly that reason. It never says a roof should be replaced; see
    // the boundary note at the top of api/_lib/roofing-damage-assessment.js.
    rf_claims: ['reconcile', 'assess_damage'],
    // 'agreement_status' (Phase 5) computes the rescission clock from the
    // claim's append-only agreement chain and the state rule. Reads only.
    // Looking at whether a cancellation window is open must never advance,
    // extend or close it -- same compute-only shape as 'reconcile'.
    rf_claim_agreements: ['agreement_status'],
    // 'set_status' (Phase 4a) lets a crew member mark their own scheduled day.
    // Status ONLY -- it cannot move the day, change the job or touch the crew,
    // so it is not a way around the management-only schedule write.
    // 'crew_load' (2026-09-02, gap A2) computes who is on how many jobs each
    // day over an explicit range, and names the two problem classes the
    // schedule could not previously see at all: the same person on two jobs
    // (a conflict, sometimes deliberate) and the same person on the same job
    // twice (a duplicated row, always an error). Reads only -- looking at
    // whether the week is overbooked must never change the week.
    rf_schedule: ['set_status', 'crew_load'],
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
