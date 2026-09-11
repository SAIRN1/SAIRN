// api/_resources/sairndental.js
// Resource registry for SAIRNdental.
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
  app: 'sairndental',
  resources: [
  // SAIRNdental (2026-08-10) -- see sql/sairndental_data_schema.sql. All 12 prefixed dnt_.
    'dnt_patients',
    'dnt_providers',
    'dnt_operatories',
    'dnt_provider_hours',
    'dnt_procedure_types',
    'dnt_coverage_rules',
    'dnt_appointments',
  // APPEND-ONLY BY DESIGN, and that is a statement about the code, verified
  // 2026-09-11 rather than asserted from the table name. `dnt_charges` has
  // exactly ONE write call in sairndental.html -- addChargeEntry(), which does
  // `list.push(rec)` and nothing else. There is no edit path and no remover. A
  // billing correction is a second row, not a rewritten one, which is what
  // makes patientBalance() and dnAging() reconstructable from the ledger.
  // api/_lib/dental-ledger.js records the same fact from the other direction:
  // the payment and charge validators note the resource is "append-only in
  // fact", which is why neither can block an existing row.
  //
  // So the absence of a delete verb here is the CORRECT design, not an
  // omission -- recorded because tools/removal_path_check.py reads this comment
  // and would otherwise carry the resource as unassessed silence.
    'dnt_charges',
  // `dnt_payments` is APPEND-ONLY BY DESIGN, same verification and the same
  // date. One write call, addPaymentEntry(), push only, no edit path, no
  // remover. A refund or a correction is a further row.
    'dnt_payments',
    'dnt_denial',
    'dnt_ar',
    'dnt_revenue',
  // SAIRNdental availability + booking (2026-08-10) -- see
  // sql/sairndental_availability_booking_schema.sql. dnt_appointments was
  // already added above but gets its OWN dedicated read/write handler
  // below (not the generic DNT_RESOURCES block) because it now has real
  // promoted columns the EXCLUDE constraints check against -- still
  // listed here since this map only gates "is this a known resource
  // string," not which code path handles it.
    'dnt_settings',
    'dnt_referrals',
    'dnt_complaints',
  // Licensing / credentialing (2026-08-24) -- see
  // sql/sairndental_credentials_schema.sql and the Ohio rule seed beside it.
  // dnt_cred_rules holds versioned requirements as data, each carrying a real
  // citation; dnt_credentials is the APPEND-ONLY per-provider record store
  // (state licences, DEA registrations, CE cycles, BLS/CPR certifications).
    'dnt_cred_rules',
    'dnt_credentials',
  // Good faith estimates (2026-09-02) -- No Surprises Act, 45 CFR 149.610. See
  // sql/sairndental_gfe_schema.sql. Handled by the generic DNT_RESOURCES block
  // in api/sd-data.js, and registered there as BOTH financial (it prices a
  // service) and patient-scoped (it names one patient and their date of birth).
    'dnt_gfe',
  // Recall & reactivation outreach (2026-09-02, competitive-gap audit A8) --
  // see sql/sairndental_recall_schema.sql. One row per contact ACTUALLY made
  // about a patient being due back; this app sends nothing itself. Handled by
  // the generic DNT_RESOURCES block and registered as patient-scoped (it names
  // a patient and records what they said) but NOT financial -- it carries no
  // charge, and the hygiene side works this list as much as the front desk.
    'dnt_recall_outreach',
  // Treatment plans (2026-09-02, competitive-gap audit A9) -- see
  // sql/sairndental_treatment_plans_schema.sql. Proposed work, phased and
  // priced, BEFORE any of it is charged; distinct from dnt_charges, which
  // records work already done. Handled by the generic DNT_RESOURCES block and
  // registered as BOTH financial (it prices what the patient is being asked to
  // accept) and patient-scoped (it names one patient and their proposed care).
    'dnt_txplans',
  // ── THE LAST FOUR LOCAL-ONLY COLLECTIONS (2026-09-10) ───────────────────
  // tools/local_only_collection_check.py reported this app as 18 of 22
  // collections covered and four with NO route to a server:
  // dnt_supplies_list, dnt_vendor_contacts, dnt_vendor_order_history and
  // dnt_vendor_pricing_rules. Everything clinical has been server-backed
  // since 2026-09-05, so a browser-data clear left the chart intact and took
  // the purchasing history and the negotiated vendor discounts with it. That
  // SELECTIVE shape is worse than a uniformly local app -- what survives
  // looks authoritative. See sql/sairndental_vendor_schema.sql.
  //
  // THE TWO LIST-SHAPED NAMES ARE NOT THEIR STORAGE KEYS, following this
  // app's existing [resource, storage-key] pair convention in
  // DNT_SYNC_RESOURCES rather than inventing a second one. The two OBJECT
  // ones match their keys exactly, and the reason is in the note below:
  //   dnt_supplies        <-> dnt_supplies_list
  //   dnt_vendor_orders   <-> dnt_vendor_order_history
  //   dnt_vendor_contacts <-> dnt_vendor_contacts
  //   dnt_vendor_pricing_rules <-> dnt_vendor_pricing_rules  (same name:
  //     the checker resolves coverage by matching a resource name against
  //     the storage key, and a differing pair is only visible to it when
  //     it appears in a [resource, key] literal. These two objects are
  //     hydrated in their own block, not through DNT_SYNC_RESOURCES, so
  //     naming them identically is what makes the coverage MEASURABLE
  //     rather than a permanent could-not-tell.)
  //
  // TWO ARE SINGLE OBJECTS AND ARE STORED AS ONE ROW EACH, id 'default' --
  // dnt_vendor_contacts is a map keyed by vendor, dnt_vendor_pricing_rules is
  // one settings object. Same treatment dnt_settings already gets here, and
  // for the stated reason: merge-by-id over something with no per-record id
  // appends the whole object every sync.
  //
  // SESSION-GATED like every other dnt_* resource -- sdnData() sends BOTH the
  // licence and the employee session, and every dnt_* branch in
  // api/sd-data.js has refused without the second since 2026-08-27. Not
  // FINANCIAL-gated, though, and that is a decision rather than an oversight:
  // DNT_FINANCIAL_RESOURCES exists to keep patient charges, payments and
  // priced treatment plans behind the owner/front-desk roles. A supply
  // cupboard and a vendor price list are practice operations, worked by
  // whoever orders the gloves. Not patient-scoped either -- none of the four
  // names a patient.
    'dnt_supplies',
    'dnt_vendor_orders',
    'dnt_vendor_contacts',
    'dnt_vendor_pricing_rules',
  // NOT REGISTERED, deliberately: dnt_vendor_cart. It is a shopping cart --
  // device state that exists between opening the vendor panel and placing the
  // order, cleared by vCartClear() the moment the order is placed. The
  // checker already classifies it as device state; it is named here so
  // "absent" reads as "decided" rather than "missed".
  ],
  // 'evaluate' computes the expiry/CE alert board from stored records and the
  // seeded rules. It READS ONLY and writes nothing -- looking at who is about
  // to lapse must never itself change a credential record. Same compute-only
  // shape as SAIRNcare's alf_compliance_rules 'evaluate', and the reason it is
  // declared here rather than in api/sd-data.js is the 2026-08-24 verb-gate
  // change: the verb belongs next to the resource that owns it.
  extraActions: {
    dnt_credentials: ['evaluate'],
  // SOFT DELETE ON dnt_supplies ONLY, AND WITHOUT IT THE BACKUP WOULD BE A BUG
  // (2026-09-10). removeSupply() drops an item from dnt_supplies_list. The
  // hydrate merges the server's rows back in BY ID, so a supply the practice
  // removed would REAPPEAR on the next sync -- a backup that resurrects
  // deleted records is worse than no backup, because it looks like the app
  // losing track of a deletion the user watched succeed.
  //
  // The other three need nothing: the two object resources are replaced
  // wholesale, and dnt_vendor_orders is append-only (the client's 200-row cap
  // is a local display bound, not a deletion -- the server keeps all of them,
  // which is the point).
  //
  // 'soft_delete', not 'delete': the record is marked and hidden, the row
  // stays, and no new database privilege is needed because the marker lives
  // inside the existing jsonb and the write is an UPDATE.
    dnt_supplies: ['soft_delete'],
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
    'dnt_vendor_cart',     // a shopping cart -- device state between opening the panel and placing the order
  ],
};
