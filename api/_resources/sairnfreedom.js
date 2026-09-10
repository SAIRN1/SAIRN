// api/_resources/sairnfreedom.js
// Resource registry for SAIRNfreedom -- NEW 2026-09-09, this app's first.
//
// SAIRNfreedom reached api/sd-data.js for the first time today. Before this
// its only server call was /api/claude, which takes an app_id and no licence,
// so it had no registry module, no licence row, and no server-side presence of
// any kind. tools/sairn_app_map_check.py found the same absence on the
// Guardian side the same day: the app was not in the App File Map either, so
// every "all apps" pass had been excluding it.
//
// WHY: tools/local_only_collection_check.py measured sairnfreedom.html at 35
// of 35 collections with NO route to a server. Membership, the ledger, gaming
// sessions, gaming expenses and CHARITABLE DISBURSEMENTS -- the ORC 2915
// reportable side of a fraternal post's gaming -- lived in one browser.
//
// REQUIRES sql/sairnfreedom_license_seed.sql AS WELL AS THE SCHEMA. Registering
// a name here gates it; it does not provision a licence. Without that seed
// every write answers 401 INVALID_LICENSE, which is a different failure from
// the 503 NOT_PROVISIONED an un-run schema gives, and both are honest.
//
// THIRTY-FIVE RESOURCES, one generic read/write pair in api/sd-data.js.
// Resource names are the localStorage keys verbatim -- the sync hook keys off
// the storage key directly.
//
// NO SESSION GATE: SAIRNfreedom has no per-employee authentication. The
// licence is the whole boundary. Same posture as sairnvet.js, same reason.
module.exports = {
  app: 'sairnfreedom',
  resources: [
    'sf_accounts',
    'sf_bottle_fills',
    'sf_ceremonial_items',
    'sf_disbursements',
    'sf_district_imports',
    'sf_documents',
    'sf_donations',
    'sf_donor_awards',
    'sf_donor_tiers',
    'sf_events',
    'sf_gaming_expenses',
    'sf_honor_details',
    'sf_inventory_counts',
    'sf_ledger',
    'sf_members',
    'sf_national_categories',
    'sf_officers',
    'sf_operators',
    'sf_permit_flags',
    'sf_products',
    'sf_rentals',
    'sf_service_appointments',
    'sf_service_hours',
    'sf_service_referrals',
    'sf_sessions',
    'sf_shifts',
    'sf_signatures',
    'sf_staff',
    'sf_tickets',
    'sf_vehicle_service',
    'sf_vehicles',
    'sf_vendor_prices',
    'sf_vendors',
    'sf_waivers',
    'sf_youth_participants',
  // ── DELIBERATELY NOT BACKED UP, with the reason for each ────────────────
  //
  //   sf_license_key         -- the licence key itself. A credential, and the
  //                             thing the backup authenticates WITH.
  //   sf_post                -- the post's own identity/config object.
  //   sf_fees                -- a fee schedule object, configuration.
  //   sf_hall_rates          -- a rate card object, configuration.
  //   sf_phase4_config       -- configuration.
  //   sf_district_keypair    -- SIGNING KEY MATERIAL. It must not leave the
  //                             device, and a backup is the opposite of that.
  //   sf_district_known_keys -- the trust-on-first-use fingerprint map for
  //                             district keys. Device-local by design: syncing
  //                             it would let one device's first-seen decision
  //                             silently become another device's trust anchor.
  //
  // 42 keys written, 35 backed up, 7 excluded above -- the count reconciles.
  ],
};
