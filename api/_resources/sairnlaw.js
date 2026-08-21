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
  // Deadline rules engine (2026-08-21) -- see
  // docs/superpowers/specs/2026-08-21-sairnlaw-deadline-rules-engine-design.md
  // and sql/sairnlaw_deadline_rules_schema.sql.
  //
  // law_deadline_rules holds jurisdiction rules as DATA rows rather than
  // handler branches, each carrying a required authority URL and an
  // effective_from/effective_to window, because a matter triggered in 2023
  // must still compute against the 2023 rule -- impossible if the rule is
  // code. Rules are superseded additively, never edited in place or deleted.
  //
  // law_holidays is deliberately separate and keyed by jurisdiction AND year:
  // FRCP 6(a)(6) counts days declared holidays by the President or Congress
  // (which appear with little notice), and treats state holidays as counting
  // only for FORWARD-counted periods -- a direction-dependent asymmetry a flat
  // holiday array gets silently wrong.
    'law_deadline_rules',
    'law_holidays',
  ],
};
