// api/_resources/routes.js
// Resource registry for the SHARED ROUTING PRIMITIVE.
//
// WHY THIS IS ITS OWN REGISTRY FILE AND NOT A LINE IN shared.js. These two
// resources genuinely are shared — StoneDesk, SAIRNgrounds, SAIRNscape,
// SAIRNroofing and SAIRNmechanical all order a day's stops for one person, and
// `api/_resources/shared.js` is where a shared resource would naturally go.
//
// It would also have been INVISIBLE there. `apps_with_registries()` in
// tools/criticality_tier_check.py skips this directory's two non-app files by
// name:
//
//     if app in ('index', 'shared'):
//         continue
//
// so the completeness arm that caught `sairnsenior/sen_period_closings` cannot
// see anything registered in shared.js. Measured 2026-10-19: all seven of that
// file's resources (profile, memory, employees, slabs, render_usage,
// shared_knowledge, employee_profile) have NO row in docs/CRITICALITY-TIERS.md
// and the checker reports no finding about it.
//
// These rows are Tier A on confidentiality. A Tier A resource whose tier
// nothing enforces is the shape this platform keeps paying for, so the
// registry was chosen to be checkable rather than to be tidy. The shared.js
// gap is recorded in the register's own gaps section; it is NOT closed here.
//
// Adding a resource: add the name here, add its row in
// docs/CRITICALITY-TIERS.md, and add its handler branch in api/sd-data.js.
// All three, or it 400s on the allowlist (api/_resources/index.js records why)
// or ships untiered.

module.exports = {
  app: 'routes',
  resources: [
    // One planned run of stops for one assignee on one date.
    // sql/rt_routes_schema.sql.
    'rt_routes',
    // One stop on that run. The address is the input; `seq` is the output.
    'rt_stops',
  ],
};
