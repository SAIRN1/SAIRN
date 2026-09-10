// api/_resources/sairnmechanical.js
// Resource registry for SAIRNmechanical.
//
// WHY THIS FILE EXISTS AT ALL: until 2026-09-02 SAIRNmechanical had complete
// per-employee auth (api/mech-auth.js, including the deactivation lifecycle)
// and NO data layer -- no registry module, and the string `sairnmechanical`
// appeared zero times in api/sd-data.js. Every panel in the app was an honest
// empty state. This registers its first resource.
//
// See api/_resources/index.js for why each app owns its own file: one shared
// map plus a hand-maintained error string is what made two sessions collide on
// every push, and what let employee_profile be a working resource missing from
// the list.

module.exports = {
  app: 'sairnmechanical',
  resources: [
  // Technician credential registry (2026-09-02) -- see
  // sql/mech_credentials_schema.sql and api/_lib/mech-credentials.js. Ranked
  // first of ten capabilities in the 2026-08-27 competitive research
  // ("Nothing else can be gated correctly until this exists"). APPEND ONLY in
  // the table and in the handler: a renewal is a new row, because "what did
  // this technician hold on the day we dispatched them" is the question the
  // records exist to answer, and editing a licence row in place destroys it.
    'mech_credentials',
  // Site asset registry (2026-09-02) -- see sql/mech_site_assets_schema.sql and
  // api/_lib/mech-assets.js. Capability #2 on the same research list:
  // "Prerequisite for A3, A5, A7, B8, G13. Table stakes."
  //
  // NOT append-only, unlike mech_credentials above, and the difference is
  // deliberate: a credential is evidence and must not be overwritten, an asset
  // is a description of a physical thing whose serial gets corrected and whose
  // location changes. It carries an UPDATE grant; it still carries no DELETE.
    'mech_site_assets',
  // ── THE LAST LOCAL-ONLY COLLECTIONS ON THE PLATFORM (2026-09-10) ────────
  // tools/local_only_collection_check.py reported this app as 5 of 5 with NO
  // route to a server -- the only one left undeclared after that day's sweep.
  // Not a pre-server app: mechData() works, mech_credentials and
  // mech_site_assets are live, and the licence is real. These were never wired.
  //
  // THE CHECK REGISTER IS THE SHARP ONE. saveCheck() stores {num, date, payee,
  // amount, memo} -- a business's record of money it paid out, on one browser.
  // The app's own comment beside it notes that a lost write is how two checks
  // end up sharing a number; losing the register loses the audit trail for
  // every cheque written.
  //
  // NAMES ARE NOT THE STORAGE KEYS HERE. This app's keys are APP_ID + '_quotes'
  // and its resources carry the established `mech_` prefix, so MECH_SYNCED in
  // sairnmechanical.html is a [resource, storage-key] PAIR list -- the shape
  // SAIRNdental's DNT_SYNC_RESOURCES already uses, and what makes the coverage
  // readable to the checker rather than a permanent could-not-tell.
  //
  // mech_checks KEYS ON THE CHECK NUMBER, not a minted id. That is what the
  // register has always keyed on and what makes a duplicate visible; minting a
  // second identity for a document that already has one would hide it.
  //
  // Licence-gated only, matching mechData()'s existing calls. See
  // sql/sairnmechanical_records_schema.sql.
    'mech_quotes',
    'mech_checks',
    'mech_docs',
    'mech_takeoffs',
  ],
  // ── DECLARED NOT SYNCED ─────────────────────────────────────────────────
  // Storage keys this app deliberately keeps on the device, in the form
  // tools/local_only_collection_check.py reads. A declaration is NOT coverage:
  // these still reach no server. What it changes is whether that is news.
  notSynced: [
    'sairnmechanical_memory',   // AI conversation memory -- 30 truncated strings, no records and no ids
    'sairnmechanical_crnum',    // the next check number; a counter, and a stale one restored from a backup would REPEAT a number
    'sairnmechanical_pricing',  // the rate card the quote engine prices against; configuration
  ],
  // 'eligibility' (mech_credentials, 2026-09-02) answers "who may be dispatched
  // to THIS job", against the credentials the job actually requires. It is
  // COMPUTE-ONLY -- it reads the registry and writes nothing, because asking
  // whether a technician may legally do the work must never itself record that
  // they may.
  //
  // It takes the requirements from the CALLER and refuses an empty list rather
  // than treating "no requirements stated" as "anyone may go". There is no
  // default requirement set, because what a job needs depends on the equipment
  // and the jurisdiction and cannot be inferred from a trade name.
  //
  // The EPA 608 section is matched, not merely the presence of a card: Type I
  // is small appliances, Type II high-pressure, Type III low-pressure,
  // Universal all three. They are different EQUIPMENT, not ranks. Dispatching
  // on "has EPA 608" is how a technician gets sent to a chiller they may not
  // legally open.
  extraActions: {
    mech_credentials: ['eligibility'],
  },
};
