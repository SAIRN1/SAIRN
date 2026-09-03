// api/_resources/stonedesk.js
// Resource registry for StoneDesk.
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
  app: 'stonedesk',
  resources: [
  // NEXUS per-user style profile (2026-09-02). One shared table across apps,
  // keyed (license_hash, employee_id); see sql/sairn_style_profiles_schema.sql
  // and docs/2026-09-02-nexus-style-profile-design.md. Listed here because
  // api/sd-data.js validates against THIS file -- api/_resources/index.js
  // records that a working resource missing from a hand-kept list is exactly
  // how employee_profile silently 400'd, and a new resource that is not
  // registered here fails the same way.
    'style_profile',
  // [0072] supplier lead time per (supplier, material) -- see
  // sql/sd_supplier_lead_times_schema.sql and api/_lib/job-risk.js. Ships
  // with NO rows and no defaults: a projection built on an invented lead
  // time is a number a shop would schedule a customer against.
    'supplier_lead_times',
  // Executive Suite advisor prompts (2026-09-02). READ ONLY, owner/admin only,
  // and it reads no table at all -- api/_lib/exec-context.js is the whole
  // store. It exists because those strings carry SAIRN's own chart of
  // accounts, price book and patent deadlines, and living in stonedesk.html
  // meant every customer could read them with View Source. The showPanel()
  // role gate closed the UI path and could not close that one.
    'exec_context',
  // Signed customer approvals (2026-09-02) -- see sql/sd_approvals_schema.sql.
  // esigApprove() captured a real signature and wrote it to localStorage and
  // nowhere else, read back from nowhere: the document proving a customer
  // agreed to a price lived in one browser and died with its cache. APPEND
  // ONLY here and in the table -- a signed price must not be editable, so the
  // write branch refuses a duplicate approval_id rather than merging it.
    'sd_approvals',
  // StoneDesk CRM/Lead Pipeline (2026-08-19) -- see sql/sd_crm_schema.sql. First real server
  // sync this resource has ever had (was pure localStorage) -- also carries the per-lead
  // assignment privacy gate, see the read/write branches below.
    'sd_crm',
  // Public catalog + quote requests (2026-09-02, competitive-gap audit GAP 1)
  // -- see sql/stonedesk_public_surface_schema.sql. These two are the STAFF
  // half; the anonymous half is api/stonedesk-public.js, which holds no license
  // key and is served by its own file, stonedesk-catalog.html, never by
  // stonedesk.html. Both are management-only here (owner/admin): publishing a
  // catalog decides what the world sees of this shop, and a quote request is an
  // unqualified stranger's name and phone number. Bespoke branches below.
  // Customer records (2026-09-02) -- see sql/stonedesk_public_surface_schema.sql.
  // Was localStorage-only: the shop's whole customer list lived in one browser,
  // the same state sd_crm was in before it got a real sync. Registered here
  // because order tracking must resolve to the REAL record rather than to a
  // status snapshot that drifts. Read by any authenticated employee, written by
  // management only.
    'sd_customers',
    'sd_public_shop',
    'sd_quote_requests',
  // Slab lineage (2026-08-22, Phase 1b) -- block -> bundle -> slab -> remnant.
  // See sql/sd_slab_lineage_schema.sql for why these are sibling tables and
  // not fields on sd_slabs' jsonb blob: that blob is capped at 65536 bytes by
  // sdslabs_data_size and ~55KB of it is already photo, so unbounded per-slab
  // history would make a record more likely to fail the longer it is used.
  // The slab -> block link is a plain string in the slab's data, deliberately
  // NOT a database foreign key, so dropping these tables can never orphan or
  // break a slab. REQUIRES sql/sd_slab_lineage_schema.sql to be run.
    'sd_blocks',
    'sd_bundles',
    'sd_slab_history',
  // HR onboarding (2026-08-29) -- see sql/sd_hr_schema.sql. Backs
  // stonedesk-hr.html, whose only persistence since 2026-06-10 was two
  // localStorage keys, i.e. one browser on one machine. One of its six forms
  // is an OSHA 1910.1053(k)(3) silica training record, which the employer is
  // required to make and maintain -- localStorage does not maintain anything.
  // Unlike the sd_slab_* lineage tables above, these are SESSION-GATED AND
  // MANAGEMENT-ONLY (see SD_HR in api/sd-data.js): personnel data with pay
  // rate, contact details and training history about identifiable people.
  // REQUIRES sql/sd_hr_schema.sql to be run.
    'sd_hr_employees',
    'sd_hr_certs',
  // Remnant yard (2026-09-02, competitive-gap audit GAP 8) -- see
  // sql/stonedesk_remnants_schema.sql. Before this the remnant yard read and
  // wrote `sd_remnant` (SINGULAR) in localStorage and had no server table at
  // all, so a remnant existed on exactly one machine and nothing could publish
  // it -- the public endpoint reads Supabase, not somebody's laptop.
  //
  // Same gate shape as 'slabs': licence-scoped, no employee session, because a
  // remnant is yard inventory rather than personnel or financial data. The
  // PUBLIC catalog reads this table through api/stonedesk-public.js after
  // resolving a shop_slug, exactly as it does for slabs.
  // REQUIRES sql/stonedesk_remnants_schema.sql to be run.
    'remnants',
  // Multi-location / yards (2026-09-03, competitive-gap audit GAP 7) -- see
  // sql/stonedesk_locations_schema.sql. A yard the shop operates. The SLAB is
  // the only record that carries a location_id; quotes, jobs, POs and remnants
  // derive theirs from the slab and store none of their own, because stamping a
  // location onto a job at creation freezes it -- move the work and the history
  // stays with the old yard forever.
  //
  // ATTRIBUTION, NOT ACCESS CONTROL. This does not scope any employee to any
  // yard; every employee still reads every yard. Same licence-scoped gate as
  // 'slabs' -- a yard's name and address is operational data.
  // REQUIRES sql/stonedesk_locations_schema.sql to be run.
    'locations',
  ],
};
