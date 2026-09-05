// api/_resources/sairnlaw.js
// Resource registry for SAIRNlaw.
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
  app: 'sairnlaw',
  resources: [
  // SAIRNlaw trust disbursement server-sync, step 1 (2026-08-16) -- see
  // sql/sairnlaw_data_schema.sql and
  // docs/superpowers/specs/2026-08-14-sairnlaw-trust-data-schema-design.md.
  // No role gating on these three -- all LAW_ROLES (owner/attorney/
  // paralegal) may write, matching sairnlaw.html's current unrestricted
  // client-side behavior. Auth is Bearer license key only, same as
  // grd_jobs -- sdnData() never sends a session token to this endpoint.
    'law_clients',
    'law_matters',
    'law_trusttx',
  // Deadlines (2026-08-21) -- FIXING A REAL PRE-EXISTING BREAK, not adding a
  // feature. sairnlaw.html has been calling sdnData('write','law_deadlines')
  // since before this session (lines ~2188 and ~2195) against a resource that
  // was never registered: production returned 400 "unrecognized resource"
  // while law_matters returned 200. It failed honestly -- the toast reads
  // "Saved on this device only -- server sync not yet enabled for this app" --
  // but the consequence was that every deadline in SAIRNlaw lived on exactly
  // one browser, was never hydrated back, and was lost with the profile.
  // Registered first, before the deadline engine, because an engine that
  // computes a correct statutory date into a resource that 400s is worse than
  // no engine: the user then believes the date is recorded.
    'law_deadlines',
  // NOT REGISTERED HERE, deliberately: law_deadline_rules and law_holidays.
  // Those are read and written by api/legal-deadlines.js talking to Supabase
  // directly, never through api/sd-data.js. Registering a name here without a
  // matching handler branch in sd-data.js does NOT make it work -- it passes
  // the allowlist and then falls through to "Unsupported action/resource
  // combination", which is a worse failure than not registering it at all.
  // Found live: law_deadlines returned exactly that until its handler branch
  // was added. Registration gates the name; the branch does the work.
  // -- THE FIFTEEN THAT NEVER REACHED THE SERVER (2026-09-04) ------------
  // Until this, sairnlaw.html wrote TWENTY resources and four were
  // registered. The other fifteen were refused by the resource allowlist on
  // every save -- proven live with a control before anything was written: on
  // a bogus licence key law_matters answers 401 INVALID_LICENSE (past the
  // resource gate) while law_invoices answers 400 "resource must be one of",
  // same request shape, only the name different. 23 call sites, including
  // billable time, invoices, matter documents and operating-account money.
  //
  // Every one of those failures rendered as "server sync not yet enabled for
  // this app", which is why it went unnoticed. That message is now honest
  // (same session), so a resource that is not set up says so.
  //
  // REGISTERING A NAME IS NECESSARY AND NOT SUFFICIENT -- the note the
  // law_deadlines branch in api/sd-data.js already carries. Each of these has
  // a handler branch in the generic LAW_RESOURCES pair, and a table in
  // sql/sairnlaw_data_extended_schema.sql which MUST be run before any of
  // them answers anything but 503 NOT_PROVISIONED.
  // Documents filed on a matter -- metadata and the e-sign stamp, no file bytes. SIX call sites, the most-written of the fifteen.
    'law_matterdocs',
  // Tasks on a matter, with a due date and an assignee.
    'law_mattertasks',
  // Dated milestones on a matter -- the case chronology.
    'law_mattermilestones',
  // BILLABLE TIME. What invoices are built from; losing it loses the fee.
    'law_timeentries',
  // Client invoices, with their line items and status.
    'law_invoices',
  // OPERATING accounts -- the firm side of the ledger, distinct from client trust.
    'law_opaccounts',
  // Operating-account transactions. Firm money moving.
    'law_optx',
  // Bank statement balances, used to reconcile against the ledger.
    'law_bankstatements',
  // Personal-injury cases: gross settlement, fee percentage, costs.
    'law_picases',
  // Medical providers and billed amounts on a PI case. See the security note in this header -- health information, at the same tier as everything else here.
    'law_pimedical',
  // Messages exchanged with a client through the portal.
    'law_portalmessages',
  // E-signature stamps: who signed what, and when.
    'law_portalesign',
  // Bar admissions per staff member and their status.
    'law_barcerts',
  // CLE credits earned, per staff member and jurisdiction.
    'law_clecredits',
  // CLE requirements per jurisdiction -- hours and period.
    'law_clerequirements',
  ],
};
