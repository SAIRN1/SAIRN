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

  // ── THE LOCAL-ONLY RECORD, 2026-09-08 ───────────────────────────────────
  // Closes the open-work row "TWELVE record collections live on one
  // workstation and reach no server at all". THE TWELVE WAS AN UNDERCOUNT and
  // this is the corrected figure: tools/local_only_collection_check.py, after
  // the 2026-09-08 repair whose own commit message says "the checker could not
  // read half of StoneDesk", reports 26 of 37 collections with NO route to a
  // server. The twelve came from its pre-fix run.
  //
  // WORSE HERE THAN IN SAIRNbiz OR SAIRNbuild, and for a reason specific to
  // this app: StoneDesk DOES sync slabs, customers, CRM and approvals. So the
  // records that look authoritative survive a browser-data clear and the
  // INVOICES that justify them do not. A uniformly local app at least fails
  // honestly.
  //
  // Twenty-one below. One generic read/write pair in api/sd-data.js, not
  // twenty-one copy-pasted blocks -- same shape and same reasoning as
  // BLD_RESOURCES, SB_RESOURCES and LEG_RESOURCES. See
  // sql/stonedesk_data_schema.sql for the tables and the id-column rule.
  //
  // NAMING: the resource name is the localStorage key verbatim, which is not
  // cosmetic -- the client's sync hook keys off the storage key directly, so a
  // rename would need a mapping table on both sides to stay correct. That is
  // why `stonedesk_quote_history` keeps its odd, unprefixed name.
  //
  // NO SESSION GATE, and that is a decision rather than an omission. It
  // follows BLD_RESOURCES rather than SB_RESOURCES: these are the shared shop
  // record -- the quote history, the inventory, the drawings, the schedule of
  // remakes -- and every role in a fabrication shop reads them. StoneDesk's
  // personnel and financial data already sits behind session gates elsewhere
  // (`sd_hr_employees`, `sd_hr_certs`, `employees`, `sd_approvals`), which is
  // where that boundary belongs. If a future per-role rule is wanted on one of
  // these it needs its own bespoke branch, not a gate bolted onto the loop.
    'sd_invoices',
    'sd_drawings',
    'sd_remakes',
    'sd_fin_jobs',
    'sd_pricing_rules',
    'sd_negotiated_prices',
    'sd_order_history',
    'sd_inventory',
    'sd_comms',
    'sd_sms_log',
  // The odd name is the real localStorage key -- see NAMING above.
    'stonedesk_quote_history',
    'sd_business_snapshots',
    'sd_field_stops',
    'sd_exec_msgs',
    'sd_aiquotes',
    'sd_nesting_saved',
    'sd_veinmatch',
    'sd_seamai',
  // Reported by the checker as COULD-NOT-TELL because st('sd_customers', ...)
  // happens to sit on the line above it. Read by hand: it is NOT server-backed
  // and it belongs here.
    'sd_photos',
  // The Template Manager's canonical key -- a 5-state workflow with a
  // statusLog[] audit trail, and the surviving half of a 2026-07-30 feature
  // de-duplication. Records, not settings.
    'sd_templates',
  // Accumulated email-security findings, loaded and saved as a plain array
  // like any other record list. Read before placing: it is not recomputed from
  // a scan, so losing it loses the shop's history.
    'sd_email_threats',

  // ── DELIBERATELY NOT BACKED UP, with the reason for each ─────────────────
  // Written down here rather than left as an absence, because "not in the list"
  // and "decided against" look identical to the next reader.
  //
  //   sd_ai_counts        -- a usage counter. Regenerable, and a stale count
  //                          restored from a backup would be worse than none.
  //   sd_settings         -- device configuration.
  //   sd_alert_settings   -- device configuration. SAIRNdental syncs its
  //                          equivalent; that is a defensible difference, not a
  //                          precedent, and it can be revisited on its own
  //                          evidence rather than by analogy.
  //   sd_stonehead_history -- an AI conversation transcript.
  //   sd_stonehub_log      -- a log.
  //   sd_market_history    -- derived market data, recomputed.
  //   sd_intake            -- ALREADY server-backed, by a different route:
  //                          sb.from(INTAKE_TABLE), a direct Supabase call the
  //                          checker cannot tie to a storage key. Adding it
  //                          here would create a SECOND, differently-tenanted
  //                          copy of the same records.
  ],

  // ── 'soft_delete' ON THE TWENTY-ONE BACKED-UP COLLECTIONS (2026-09-08) ───
  // Michael's decision on the platform's long-open "no delete capability"
  // row: SOFT delete. A record is marked deleted and hidden from view; the
  // underlying row stays and stays recoverable. A hard-delete path for a
  // genuine erasure request is its own separate action if it is ever needed.
  //
  // WHY THE VERB IS 'soft_delete' AND NOT 'delete'. 'delete' already exists on
  // this platform and means a real DELETE -- the SAIRNcode family's
  // Compliance-Admin-gated branch issues the only `method: 'DELETE'` in
  // api/sd-data.js. Two verbs that destroy different amounts of data must not
  // share a name; a caller copying a working `delete` call from one family to
  // another would silently get the other behaviour.
  //
  // IT NEEDS NO NEW DATABASE PRIVILEGE, which is the point of the design: the
  // marker lives inside the existing `data` jsonb and the write is an UPDATE.
  // sql/stonedesk_data_schema.sql grants select/insert/update and no delete,
  // and that stays true.
  //
  // SCOPED TO THIS FAMILY DELIBERATELY. The other generic families (BLD, SB,
  // LEG, SDN, LAW, DNT...) share the same table shape and could take the same
  // verb mechanically -- but each has its own session or role gate, and who
  // may delete is not the same question as who may write. Widening is one
  // decision per family, not a sweep.
  extraActions: {
    'sd_invoices': ['soft_delete'],
    'sd_drawings': ['soft_delete'],
    'sd_remakes': ['soft_delete'],
    'sd_fin_jobs': ['soft_delete'],
    'sd_pricing_rules': ['soft_delete'],
    'sd_negotiated_prices': ['soft_delete'],
    'sd_order_history': ['soft_delete'],
    'sd_inventory': ['soft_delete'],
    'sd_comms': ['soft_delete'],
    'sd_sms_log': ['soft_delete'],
    'stonedesk_quote_history': ['soft_delete'],
    'sd_business_snapshots': ['soft_delete'],
    'sd_field_stops': ['soft_delete'],
    'sd_exec_msgs': ['soft_delete'],
    'sd_aiquotes': ['soft_delete'],
    'sd_nesting_saved': ['soft_delete'],
    'sd_veinmatch': ['soft_delete'],
    'sd_seamai': ['soft_delete'],
    'sd_photos': ['soft_delete'],
    'sd_templates': ['soft_delete'],
    'sd_email_threats': ['soft_delete'],
  // SOFT DELETE ON sd_quote_requests (2026-09-12), Michael's decision, and it
  // is the ONLY one of these twenty-two that is fed by an UNAUTHENTICATED
  // PUBLIC FORM. Everything above is written by a signed-in employee, so its
  // volume is bounded by staff effort; this one is bounded by whatever a
  // stranger submits.
  //
  // The gap it closes, found 2026-09-12 by reading the writer for the
  // removal-path burn-down: api/sd-data.js correctly refuses to let staff EDIT
  // the submitted text, because it is evidence of what a customer asked for --
  // but that is an argument against EDITING and it had been standing in for an
  // argument against REMOVAL. The two are not the same, and only one of them
  // was ever decided.
  //
  // Declining did NOT stand in for removal either: pcRenderRequests() rendered
  // every row with no status filter, so a declined request stayed in the table
  // permanently and the inbox could only grow.
  //
  // 'soft_delete', not 'delete', for the reason the platform decision already
  // gives: the row stays and stays recoverable, the marker lives in the
  // existing jsonb, and no new database privilege is needed --
  // sql/stonedesk_public_surface_schema.sql grants select/insert/update and
  // that stays true. THE SUBMITTED TEXT IS STILL NOT EDITABLE: soft delete
  // adds `_deleted_at` and changes nothing else, so what the customer wrote
  // survives a deletion exactly as written.
    'sd_quote_requests': ['soft_delete'],
  },
  // ── DECLARED NOT SYNCED (2026-09-10) ────────────────────────────────────
  // The same decisions already written in prose above, in a form the checker
  // can read. tools/local_only_collection_check.py had been CLEARING these
  // through a bug -- a one-line save wrapper matched its own signature as the
  // server call -- so they never appeared. With that fixed they surfaced all
  // at once and read like a regression, when every one of them is a choice
  // somebody made and recorded.
  //
  // A DECLARATION IS NOT COVERAGE. These keys still reach no server; what this
  // changes is whether that is news. Absent means UNDECIDED, not exempt, so a
  // new local-only key still shows up in the findings section where it belongs.
  notSynced: [
    'sd_settings',         // device configuration
    'sd_alert_settings',   // device configuration
    'sd_ai_counts',        // a usage counter; a stale count restored from a backup is worse than none
    'sd_market_history',   // derived market data, recomputed
    'sd_stonehead_history',// an AI conversation transcript
    'sd_stonehub_log',     // a log
  ],
};
