// api/_resources/sairnvet.js
// Resource registry for SAIRNvet.
//
// IT OWNS NOTHING, AND THE EMPTY LIST IS THE POINT (2026-09-05).
//
// SAIRNvet is a real, live app that really does call /api/sd-data --
// sairnvet.html:8343, `SV_DATA_API = https://sairn.vercel.app/api/sd-data`,
// through svData(). MEASURED off the file rather than assumed: the only
// resource it ever names is `shared_knowledge`, which shared.js owns. Two call
// sites, one read and one write, and nothing else.
//
// So it had no module. That was harmless until 2026-09-04, when two changes
// started reading `lic.app_id` -- scoping the "resource must be one of" list to
// the caller's own app, and then the app-boundary gate. Both ask "is this a
// known app?", and for a live app with no module the answer was no, which
// dropped its licences into the unrecognised-app fallback: the full list, and
// no boundary. The independent review of the scoping change found it.
//
// Registering it with an EMPTY list is the honest fix and not a placeholder:
// zero own resources is the true answer, and it makes SAIRNvet's licences
// attributable, so they get the shared resources they actually use and nothing
// else. If SAIRNvet ever gains server-side data of its own, the names go here
// and the gate follows automatically.
//
// Deliberately NOT invented: SAIRNvet has a large localStorage surface, and it
// would have been easy to register `sv_*` names for it. Not one of them is sent
// to sd-data today, and a registry that lists resources no code requests is a
// claim about the platform that nothing backs.

module.exports = {
  app: 'sairnvet',
  resources: [],
};
