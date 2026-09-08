// api/_resources/sairncash.js
// Resource registry for SAIRNcash.
//
// IT OWNS NOTHING, AND -- CORRECTING THE FINDING THAT PRODUCED THIS FILE --
// IT DOES NOT CALL /api/sd-data AT ALL (2026-09-05).
//
// The independent review of the 2026-09-05 scoping change reported that
// "`sairnvet.html` posts to /api/sd-data ... as does `sairncash.html`". The
// first half is true and is why api/_resources/sairnvet.js exists. THE SECOND
// HALF IS NOT. Checked before writing this file rather than after: the only
// occurrence of the string "sd-data" in sairncash.html is inside a comment
// ("sd-data.js zero times and ..."), and the only endpoint it names anywhere is
//
//     https://sairn.vercel.app/api/sairncash/checkout
//
// There is no svData/sdnData-shaped helper and no `resource:` literal in the
// file. So SAIRNcash was never on the unrecognised-app fallback through this
// endpoint, because it never reaches this endpoint.
//
// IT IS REGISTERED ANYWAY, DELIBERATELY, and the reason is about licences
// rather than about the page. `license_keys.app_id` is set by whoever issues a
// key, not by the app, so a SAIRNcash licence can exist and can be presented to
// /api/sd-data by anything holding it. With no module, such a key is
// unattributable: it takes the full-resource-list fallback and bypasses the
// app-boundary gate. Registering an empty list makes it attributable, so it
// reaches the shared resources and nothing else.
//
// The list is empty because zero is the measured answer. If SAIRNcash gains
// server-side data of its own, the names go here.

module.exports = {
  app: 'sairncash',
  resources: [],
};
