// api/_resources/sairngrounds.js
// Resource registry for SAIRNgrounds (incl. the msb_ marketplace family).
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
  app: 'sairngrounds',
  resources: [
  // SAIRNgrounds (2026-08-05) -- see sql/sairngrounds_data_schema.sql. Read branches degrade to
  // an empty-but-ok response (provisioned:false) if that migration hasn't run yet, same pattern
  // as render_usage/shared_knowledge above, rather than hard-failing the whole panel.
    'properties',
    'jobs',
    'quotes',
    'golf_zones',
  // SAIRNgrounds schedule + progress-photo QC (2026-08-06, related-bug + item-3 cross-device fix)
  // -- see the block comments below for why these are prefixed rather than reusing 'schedule'/
  // 'progress_photos' bare.
    'grd_schedule',
    'grd_progress_photos',
  // SAIRNgrounds invoices + DreamClose (2026-08-06, sweep fix) -- 'invoices' bare was already
  // claimed by SAIRNscape below (customer_id-scoped); 'dreamclose' never had a route at all.
    'grd_invoices',
    'grd_dreamclose',
  // Full resource-name sweep, phase 2 (2026-08-06) -- see
  // sql/sairngrounds_data_schema_phase2.sql and
  // sql/sairnscape_data_schema_phase2.sql for the complete rationale.
    'grd_invasive_sightings',
    'grd_ecosystem_reports',
    'grd_designs',
    'grd_irr_controllers',
    'grd_irr_zones',
    'grd_irr_schedules',
    'grd_water_features',
    'grd_training_courses',
    'grd_training_completions',
    'grd_boq_rates',
    'grd_vendors',
    'msb_products',
    'msb_sales',
    'msb_licenses',
    'msb_inventory_log',
    'msb_bottle_scans',
    'msb_food_scans',
    'msb_food_waste',
    'msb_food_cost_log',
    'msb_sale_hours',
  // On-Course Caddie (2026-09-02) -- see sql/sairngrounds_caddie_schema.sql.
  // Both are server-side rather than localStorage-only because each is read by
  // somebody other than the device that wrote it: pace of play is the loop back
  // into operations, and a cart order the Pro Shop cannot see is not an order.
    'grd_rounds',
    'grd_cart_orders',
  ],
};
