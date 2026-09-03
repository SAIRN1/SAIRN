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
  // Commercial roof asset registry (2026-09-02) -- see
  // sql/sairnroofing_asset_registry_schema.sql and
  // api/_lib/roofing-asset-registry.js. Tier-B gap B1, which the audit calls
  // "the single largest Tier B structural gap": many roofs per customer, one
  // contractor servicing hundreds of buildings. rf_jobs is one job at a time
  // and was deliberately left alone rather than made to pretend otherwise.
  //
  // Registered on day one for the reason rf_settings' note gives.
    'rf_buildings',
    'rf_roof_sections',
  // Progress billing: draw requests and retainage (2026-09-02) -- see
  // sql/sairnroofing_draws_schema.sql and api/_lib/wip-accounting.js. Tier-B
  // gap B3's first two thirds. Certified payroll is NOT included and is not
  // coming as a side effect -- it needs external prevailing-wage
  // determinations, and inventing a wage rate would put a fabricated number in
  // a federal filing.
  //
  // Registered on day one for the reason rf_settings' note gives.
    'rf_draws',
  // Fall-protection equipment and job hazard assessments (2026-09-02) -- see
  // sql/sairnroofing_safety_schema.sql and api/_lib/roofing-safety.js. Tier-B
  // gap B4. Deliberately NOT incident logging: SAIRNbuild and StoneDesk both
  // already have that client-side, and this is the other half -- equipment
  // that expires and an assessment the crew on the roof today has or has not
  // signed.
  //
  // Registered on day one for the reason rf_settings' note gives.
    'rf_safety_equipment',
    'rf_job_hazard_assessments',
  // The contractor's OWN prequalification packet and bonding position
  // (2026-09-02) -- see sql/sairnroofing_prequal_schema.sql and
  // api/_lib/roofing-prequal.js. Tier-B gap B7. Faces the OPPOSITE way from
  // SAIRNbuild's prequal fields, which sit on its subcontractors: SAIRNroofing's
  // customer is the roofer, and at Tier B the roofer is the sub being qualified.
  //
  // Registered on day one for the reason rf_settings' note gives.
    'rf_prequal_documents',
    'rf_bonding',
  // Legal entities, for multi-entity consolidation (2026-09-02) -- see
  // sql/sairnroofing_entities_schema.sql and api/_lib/roofing-consolidation.js.
  // Tier-B gap B5, whose own audit note is the diagnosis: rf_locations is
  // attribution-only, and branch != entity. entity_id lives on the LOCATION
  // and nowhere else, so moving a branch moves its whole history.
  //
  // Registered on day one for the reason rf_settings' note gives.
    'rf_entities',
  // Supplier purchase orders, receipts and invoices (2026-09-02, B6) -- see
  // sql/sairnroofing_supplier_documents_schema.sql and
  // api/_lib/roofing-supplier-match.js. ONE table, three doc_types, keyed by
  // the PO number the paperwork already shares.
  //
  // APPEND ONLY, and here that is not a style choice: these documents are what
  // a contractor argues from when an invoice is wrong, and a receipt edited
  // after the fact is worth nothing in that argument. No UPDATE grant, no
  // DELETE grant. A corrected invoice is a NEW document and the match shows
  // both. Same reasoning as mech_credentials, and the opposite of
  // mech_site_assets -- the difference is whether the row is evidence or a
  // description.
    'rf_supplier_documents',
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
    // 'portfolio' (2026-09-02, gap B1) computes the capital/lifecycle forecast
    // across every roof section: which year each is due, the area coming due,
    // and -- surfaced beside the totals rather than under them -- the sections
    // that CANNOT be planned because nobody has entered an expected service
    // life. Reads only; looking at a capital plan must never write one.
    rf_roof_sections: ['portfolio'],
    // 'wip' (2026-09-02, gap B3) computes the work-in-progress schedule across
    // every job: retainage held, what is outstanding, and over- versus
    // under-billing kept APART rather than netted. Reads only -- looking at a
    // WIP position must never change one.
    rf_draws: ['wip'],
    // 'board' (2026-09-02, gap B4) computes the fall-protection inspection
    // board: overdue, due soon, never inspected, and -- kept apart -- the
    // records whose clock CANNOT run because no sourced interval was entered.
    // Reads only. It carries its own disclaimer in the response, because a
    // safety screen that omits one reads as a compliance verdict.
    rf_safety_equipment: ['board'],
    // 'crew_check' compares a hazard assessment against the crew actually
    // scheduled on that job that day and names who has not signed. Reads both
    // rf_job_hazard_assessments and rf_schedule; writes nothing.
    rf_job_hazard_assessments: ['crew_check'],
    // 'readiness' (2026-09-02, gap B7) answers "can we submit THIS GC's
    // prequalification form" against the kinds that GC asked for -- there is no
    // default list, because every form differs. Reads only.
    rf_prequal_documents: ['readiness'],
    // 'capacity' computes remaining bonding capacity from the aggregate limit
    // and the committed backlog, which is DERIVED from the WIP schedule rather
    // than stored -- a second backlog figure would drift from it the moment a
    // draw was entered. Reads only.
    rf_bonding: ['capacity'],
    // 'consolidate' (2026-09-02, gap B5) totals the book per legal entity by
    // joining each invoice to its location and then to that location's CURRENT
    // entity. Reads only. 'preview_move' answers what reassigning one branch
    // would do BEFORE anyone clicks -- including proving the grand total does
    // not change, which is the invariant the whole design rests on.
    rf_entities: ['consolidate', 'preview_move'],
    // Phase 4b. 'issue' allocates the gapless invoice number and is idempotent
    // -- re-issuing must never burn a second number. 'add_payment' appends ONE
    // entry server-side. 'reconcile_claim' compares the invoice against the
    // linked claim and writes nothing to either.
    rf_invoices: ['issue', 'add_payment', 'reconcile_claim'],
    // 'match' (rf_supplier_documents, 2026-09-02, B6) runs the three-way
    // reconciliation for one purchase order: what was ORDERED against what was
    // RECEIVED against what was INVOICED. Reads every document under that PO
    // and writes nothing -- asking whether an invoice is right must never
    // itself approve it, and the engine deliberately returns no pay/hold
    // verdict at all.
    //
    // It is NOT EDI transport. An X12 850/856/810 exchange needs a
    // trading-partner agreement and a per-partner certification cycle; the
    // reconciliation those documents exist to enable is identical whether they
    // arrive over EDI, as a PDF, or typed off a paper packing slip, and that
    // is the half this builds.
    rf_supplier_documents: ['match'],
  },
};
