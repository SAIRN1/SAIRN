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
  ],
};
