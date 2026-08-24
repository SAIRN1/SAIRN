// api/_resources/sairncode.js
// Resource registry for SAIRNcode.
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

const RESOURCES = [
  // SAIRNcode real data layer + per-employee auth (2026-08-18) -- see
  // sql/sairncode_data_schema.sql and
  // docs/superpowers/specs/2026-08-18-sairncode-real-data-layer-design.md.
  // All 15 share one generic handler (SC_RESOURCES below) since they're
  // identical in shape (one row per entry, license_hash-scoped, a jsonb
  // data column) -- the only resource family on this endpoint with a
  // real 'delete' action, admin-role-gated server-side (see SC_RESOURCES
  // handler), because SAIRNcode's client already has real remove buttons
  // for each of these (removeDenialEntry() etc.) that previously only
  // filtered a local array -- this endpoint had never supported an
  // actual delete verb for any resource before now (a platform-wide gap
  // already logged in SAIRN-PLATFORM-SESSION3-HANDOFF.md item 4).
    'sc_denial',
    'sc_revenue',
    'sc_compliance',
    'sc_fraud',
    'sc_prebill',
    'sc_hcc',
    'sc_drg',
    'sc_query',
    'sc_rac',
    'sc_telehealth',
    'sc_anesthesia',
    'sc_auth',
    'sc_ar',
    'sc_providers',
    'sc_encoder',
  // Claims Management (2026-08-19) -- the 16th SC_RESOURCES entry, added
  // when a full audit found Claims was the one SAIRNcode panel still
  // static/hardcoded (8 fake patient rows, fabricated KPIs) after the
  // 2026-08-18 fabrication audit fixed every sibling panel. Same generic
  // shape/handler as the other 15. REQUIRES sql/sairncode_claims_schema.sql
  // to be run in Supabase before this resource's read/write/delete will
  // work -- not run yet as of this commit (no DB execution access from
  // this session, same real blocker every other new-table addition this
  // session has hit).
    'sc_claims',
  // Scrub Rules Reference (2026-08-19, rule-based scrubbing expansion) --
  // the 17th SC_RESOURCES entry. Deliberately empty by default, never
  // seeded -- a coder/admin adds real, verified NCCI/CCI PTP,
  // Excludes1/Excludes2, and modifier rules they've confirmed themselves.
  // See docs/superpowers/specs/2026-08-19-sairncode-scrub-explainability-design.md
  // for why this table starts empty rather than pre-loaded with rules this
  // session can't independently verify are current/correct. Same generic
  // shape/handler as every other sc_* resource. REQUIRES
  // sql/sairncode_scrubrules_schema.sql to be run in Supabase.
    'sc_scrubrules',
  // Denial Pattern Log (2026-08-20, denial pattern tracking expansion) --
  // the 18th SC_RESOURCES entry. Event-level rows (code + payer + reason +
  // amount + date), separate from the aggregate sc_denial resource above
  // which has no payer field and can't support real per-payer/per-reason
  // pattern analysis. Same generic shape/handler as every other sc_*
  // resource. REQUIRES sql/sairncode_denial_events_schema.sql to be run
  // in Supabase.
    'sc_denial_events',
  // Eligibility check history (2026-08-20, BYO-credential expansion) -- the
  // 19th SC_RESOURCES entry. A LOG of real 270/271 checks the practice has
  // run, not the live call: the actual check goes out through
  // api/sc-eligibility.js against the practice's own Stedi account, and is
  // never cached here as authoritative. The raw 271 is deliberately not
  // stored -- see sql/sairncode_eligibility_schema.sql's header. Same
  // generic shape/handler as every other sc_* resource. REQUIRES
  // sql/sairncode_eligibility_schema.sql to be run in Supabase.
    'sc_eligibility',
  // Per-practice SAIRNcode settings (2026-08-20, firewall audit layer 26) --
  // the 20th SC_RESOURCES entry. Currently holds only the data-retention
  // POLICY value. It does NOT cause any deletion: no purge or expiry
  // mechanism exists in SAIRNcode, deliberately -- see
  // sql/sairncode_settings_schema.sql's header. The retention floor is
  // enforced in the write branch below precisely BECAUSE this value will one
  // day drive irreversible deletion. REQUIRES
  // sql/sairncode_settings_schema.sql to be run in Supabase.
    'sc_settings',
  // Prior-auth REQUEST lifecycle (2026-08-20, Phase 2a/2b) -- the 21st
  // SC_RESOURCES entry. A different object than sc_auth (an authorization
  // already held): this is the submitted->pending->approved/denied
  // lifecycle with a payer, a submission method, and a real regulatory
  // clock. sc_auth is untouched -- see sql/sairncode_auth_requests_schema
  // .sql's header for the full reasoning. Write carries one extra
  // server-side gate below: signing off a request (moving it toward
  // submission-ready) requires a real Compliance Admin session, same
  // weight as the delete gate every other sc_* resource already has.
  // REQUIRES sql/sairncode_auth_requests_schema.sql to be run in Supabase.
    'sc_auth_requests',
  // Specialty spot-check harness (2026-08-20, pre-SAIRNcare gap pass) --
  // real coder-submitted specialty questions with the coder's OWN pass/
  // fail/needs-review verdict, never a verdict this app computes. See
  // sql/sairncode_specialty_checks_schema.sql's header for why this exists
  // instead of a claimed coverage percentage. REQUIRES
  // sql/sairncode_specialty_checks_schema.sql to be run in Supabase.
    'sc_specialty_checks',
  // Specialty documentation checklists (2026-08-20) -- deliberately empty
  // by default, Source field required, same discipline as sc_scrubrules.
  // REQUIRES sql/sairncode_specialty_checklists_schema.sql to be run in
  // Supabase.
    'sc_specialty_checklists',
  // ASA Base Units Reference (2026-08-20) -- deliberately empty by default,
  // Source field required, same discipline as sc_scrubrules. See
  // sql/sairncode_anesthesia_base_units_schema.sql for why. REQUIRES that
  // migration to be run in Supabase.
    'sc_anesthesia_base_units',
  // Per-coded-item citation + review record (2026-08-20, Phase 1) -- the
  // 25th SC_RESOURCES entry. suggestCodesFromNote() already produced a
  // real, independently-verified citation per suggested code and then
  // discarded it (render-only, confirmed by grep before building); this
  // makes it a stored record so "why was this code assigned" survives past
  // the screen. Also carries the honest needs-human-review escalation
  // flag. Confidence on these rows is a DERIVED label ('high'/'low') from
  // mechanically-checkable signals, never a model-emitted percentage --
  // see sql/sairncode_coded_items_schema.sql's header for why that
  // distinction is load-bearing (this file's own Fraud panel had a
  // fabricated 82%/71% confidence score removed in the 2026-08-18
  // fabrication audit). REQUIRES sql/sairncode_coded_items_schema.sql to
  // be run in Supabase.
    'sc_coded_items',
  // Provider credential scope (2026-08-20, Phase 4 item 7) -- the 26th
  // SC_RESOURCES entry. Backs the reusable credential-gating layer every
  // Phase 5 specialty module depends on. sc_providers could NOT express
  // this: its `cred` field is a Yes/No dropdown (credentialed-at-all,
  // not per-code) and its `specialty` is free text, so nothing could
  // reliably match a code against it. Deliberately empty by default and
  // never seeded -- which specialties may bill which codes varies by
  // payer policy and state scope-of-practice law and was not verified
  // against a primary source here, so the practice enters scopes THEY
  // verified, with a required source field, same discipline as
  // sc_scrubrules. The gate FAILS CLOSED on missing data (routes to
  // human review, never an auto-pass) -- see the schema file header.
  // REQUIRES sql/sairncode_credential_scope_schema.sql to be run.
    'sc_credential_scope',
  // PC/TC Indicator Reference (2026-08-21, gap-closure pass 2 item 3) -- the
  // 27th SC_RESOURCES entry. Holds the per-code CMS PC/TC indicator that
  // decides whether a code can carry -26/-TC at all. Deliberately empty by
  // default and never seeded: the authoritative list is ~10k codes reissued
  // annually with the NPFS Relative Value File, so a copy embedded here
  // would be unverifiable and would go stale silently. Source field required
  // on the Add form, same discipline as sc_scrubrules. REQUIRES
  // sql/sairncode_pctc_schema.sql to be run in Supabase.
    'sc_pctc',
  // DME/DMEPOS records (2026-08-22, gap-closure pass 2 item 6) -- the 28th
  // SC_RESOURCES entry. Stores delivered-equipment history (the same-or-
  // similar duplicate-payment gate cannot work without it) and per-supplier
  // prior-authorization exemption status under CMS-1828-F, which is per
  // annual cycle and expires. Deliberately does NOT store the Required PA
  // List itself -- see sql/sairncode_dme_schema.sql's header. REQUIRES
  // sql/sairncode_dme_schema.sql to be run in Supabase.
    'sc_dme',
];

module.exports = {
  app: 'sairncode',
  resources: RESOURCES,
  // 'delete' is a real verb for every sc_* resource and only for them --
  // SAIRNcode's client has had real remove buttons since 2026-08-18. Declared
  // here rather than as a hand-kept list inside api/sd-data.js, which is where
  // it used to live: that file carried a SECOND copy of the 28 names purely to
  // answer "may this resource be deleted", and a copy of a list is the exact
  // drift this directory exists to prevent (employee_profile had already gone
  // missing from one such copy). Derived from RESOURCES above, so a resource
  // added to this file can never be silently ungated or over-gated.
  extraActions: RESOURCES.reduce(function (map, name) {
    map[name] = ['delete'];
    return map;
  }, {}),
};
