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
