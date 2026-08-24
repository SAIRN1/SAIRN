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
  ],
  // 'evaluate' computes the expiry board from stored records and seeded rules.
  // Reads only, writes nothing -- looking at who is about to lapse must never
  // change a credential record. Same compute-only shape as SAIRNcare's
  // alf_compliance_rules and SAIRNdental's dnt_credentials.
  extraActions: {
    rf_certifications: ['evaluate'],
  },
};
