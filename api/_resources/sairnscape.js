// api/_resources/sairnscape.js
// Resource registry for SAIRNscape.
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
  app: 'sairnscape',
  resources: [
  // SAIRNscape (2026-08-06) -- see sql/sairnscape_data_schema.sql. Same graceful-degrade pattern.
  // Named 'scp_jobs'/'scp_quotes' rather than plain 'jobs'/'quotes' specifically to avoid
  // colliding with SAIRNgrounds' existing 'jobs'/'quotes' resource strings above -- two identical
  // resource names would each need an `if (resource==='jobs' && action==='read')` branch, and
  // only the first one in file order would ever match, silently routing SAIRNscape calls into
  // SAIRNgrounds' grd_jobs table. Caught before writing any branch, not after.
    'customers',
    'scp_jobs',
    'scp_quotes',
    'schedule',
    'invoices',
  // SAIRNscape progress-photo QC (2026-08-06) -- same fix, same prefixing reason.
    'scp_progress_photos',
    'scp_designs',
    'scp_irr_controllers',
    'scp_irr_zones',
    'scp_irr_schedules',
    'scp_water_features',
    'scp_vendors',
  ],
};
