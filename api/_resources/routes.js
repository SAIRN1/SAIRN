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
  // ── NOT AN APP, SO NOT VISIBLE TO ONE. ADDED 2026-10-19 (cody b27) ──────
  // `routes` is a pseudo-app: no licence is ever issued for it. isVisibleTo()
  // in api/_resources/index.js had exactly two routes to visibility -- be in
  // `shared`, or be owned by the caller's own app -- so BOTH of these names
  // were invisible to every real licence and checkEnvelope answered 400
  // FOREIGN_RESOURCE before the handler branch was ever reached. MEASURED:
  // isVisibleTo('rt_routes','stonedesk') was false, and so was sairngrounds
  // and sairnmechanical.
  //
  // So the handler branch landed exactly as routed and the feature was still
  // dead, in a FOURTH place -- the registry entry, the handler branch and the
  // extraActions declaration were all correct. Found by driving the real
  // dispatcher rather than this module.
  //
  // This flag, not a move into shared.js: the header above explains why
  // shared.js is the wrong home (the tier checker skips it by name and these
  // rows are Tier A), and moving them would have bought reachability with
  // invisibility to the tier arm.
  visibleToAllApps: true,
  resources: [
    // One planned run of stops for one assignee on one date.
    // sql/rt_routes_schema.sql.
    'rt_routes',
    // One stop on that run. The address is the input; `seq` is the output.
    'rt_stops',
  ],
  // ── THE THREE NON-READ VERBS, DECLARED WITH THE HANDLER AND NOT BEFORE IT ──
  // 'upsert', 'reorder' and 'optimize' are verbs beyond read/write, and
  // api/_resources/index.js asserts extra actions AT LOAD: a verb
  // declared for a resource whose module does not register it is
  // refused, and a verb declared with no handler branch asserts a
  // capability that answers 400. So this line lands in the SAME edit as
  // the api/sd-data.js branch -- fourth's routing document held it back
  // on purpose for exactly that reason.
  //
  // rt_stops gets NO extra verbs. Every verb here operates on a ROUTE
  // and its stop set together -- 'reorder' renumbers the whole set and
  // 'optimize' replaces it -- so a verb aimed at a single stop would be
  // a capability with no handler behind it.
  extraActions: {
    rt_routes: ['upsert', 'reorder', 'optimize'],
  },
};
