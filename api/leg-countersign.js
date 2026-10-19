// api/leg-countersign.js
// ---------------------------------------------------------------------------
// SAIRNlegacy's countersignature lock. THE PROFILE IS THE WHOLE FILE; the
// mechanism is api/_lib/countersign.js and the HTTP half is
// api/_lib/countersign-endpoint.js, and that file's header says why there is
// one mechanism rather than one copy per app.
//
// ── WHAT IT LOCKS AND WHY (practitioner answer F1, 2026-10-17, b18) ──────
// `leg_cremations`, on EVERY write, MODE_ALWAYS. Michael's answer to F1 is
// that a cremation authorisation takes a second named, signing person.
//
// A cremation authorisation is the sharpest irreversible act in this app and
// api/_lib/leg-roles.js's own row says so: there is no undoing it and no
// amended record that helps. `python tools/removal_path_check.py --burn-down`
// is the tool that ranks that class; the row's `why` has carried the
// second-person question as an open state-law reading since the table was
// written, and this is that question answered.
//
// ── MODE_ALWAYS INCLUDES THE OWNER, AND THAT IS THE POINT ────────────────
// A rule the owner is exempt from is not "the paperwork needs a second named
// person". Compare LEG_APPEND_ONLY in api/_lib/leg-roles.js, which is
// append-only for every role INCLUDING the owner for the same reason: a
// custody record the owner can edit is not a custody record.
//
// ── WHO MAY SIGN: DERIVED, NEVER RETYPED ────────────────────────────────
// LEG_REGULATED_WRITE_ROLES is computed in api/_lib/leg-roles.js from the
// `leg_cremations` row itself -- the roles with `rw` on the REGULATED band,
// which in this app's vocabulary is what "a licensed funeral director" means.
// So a band change moves the signer list with it, and the two places that
// would otherwise drift are an irreversible authorisation and the list of
// people who may approve it.
//
// ── WHO MAY PREPARE: F3's CONFIG, AND IT IS NOT HARDCODED HERE ───────────
// `apprentice` is listed as a preparer role at the ENDPOINT, and the per-home
// F3 config in api/_lib/leg-roles.js is what decides whether this home's
// apprentices may prepare THIS resource -- `decide(resource, 'apprentice',
// 'prepare', null, home)` is the authority and api/sd-data.js consults it.
// THE ENDPOINT IS THEREFORE THE WIDER OF THE TWO GATES ON PURPOSE: it answers
// "could an apprentice ever prepare anything here", and the role table answers
// "may this home's apprentice prepare this record". A home with an empty F3
// config has apprentices who can reach this endpoint and are refused by the
// role table, which is the correct direction -- the narrow gate is the one
// nearest the data.
//
// REQUIRES sql/sairnlegacy_countersign_schema.sql AND
// sql/sairnlegacy_employee_auth_schema.sql.
// ---------------------------------------------------------------------------

'use strict';

const cs = require('./_lib/countersign');
const { runCountersignAction } = require('./_lib/countersign-endpoint');
const { validateLicenseKey } = require('./_lib/license');
const legRoles = require('./_lib/leg-roles');
const { AUTH_TABLE_BY_APP } = require('./_lib/auth');

const APP = 'sairnlegacy';

// PREPARER ROLES, AND ONLY THE ONES THAT ARE NOT ALREADY SIGNERS.
// `isPreparer` unions this with the signer set itself, so owner and director
// are absent here deliberately rather than by omission -- they may obviously
// prepare what they may file, and listing them twice is how a union gets one
// member in one place and not the other.
//
// `arranger`, `prep`, `office`, `livery` and `staff` are NOT here. None of
// them has any write on the REGULATED band and a cremation authorisation is
// not theirs to stage; F3's answer is about apprentices specifically.
const PREPARER_ROLES = Object.freeze(Object.assign(Object.create(null), {
  apprentice: true
}));

const PROFILE = Object.freeze({
  app: APP,
  employeeTable: AUTH_TABLE_BY_APP[APP],
  tokenTable: 'sairnlegacy_countersign_tokens',
  sqlFile: 'sql/sairnlegacy_countersign_schema.sql',
  lockedResources: Object.freeze(Object.assign(Object.create(null), {
    leg_cremations: cs.MODE_ALWAYS
  })),
  signerRoles: legRoles.LEG_REGULATED_WRITE_ROLES,
  preparerRoles: PREPARER_ROLES,
  signerLabel: 'a licensed funeral director (Owner or Director)',
  // THE REFUSALS ARE WRITTEN OUT, not generated from the label, because each
  // one has to say what the person should do next. "You may not" with no route
  // sends somebody to ask for a permission that is not the problem.
  requiredMessage:
    'A cremation authorisation needs a second named, signing person before it '
  + 'can be filed. Ask another licensed director to review and countersign it. '
  + 'Nothing was saved and nothing was authorised.',
  preparerRefusal:
    'Only a licensed director, or an apprentice your home has authorised to '
  + 'prepare one, can stage a cremation authorisation for signature.',
  signerRefusal:
    'Only a licensed funeral director (Owner or Director) can countersign a '
  + 'cremation authorisation.'
});

// VALIDATED AT MODULE LOAD, not on the first request. A malformed profile is a
// programming error in this repo and should take the endpoint down loudly at
// deploy rather than answer 503 to one unlucky caller.
cs.assertProfile(PROFILE);

// ── THE AUTH BOUNDARY, IN THE FILE THAT IS THE ROUTE ──────────────────────
// Method, bearer presence, then `validateLicenseKey` -- the same order as all
// fifteen api/*-auth.js handlers and api/sv-witness.js, and the order
// api/preauth-envelope-ordering.test.js and tools/preauth_oracle_check.py both
// require. The first draft of this file delegated the whole handler to
// api/_lib/countersign-endpoint.js and the oracle reported it as "UNDECLARED
// PUBLIC -- no auth boundary": correctly, because the file a reader opens to
// ask "what reaches this URL unauthenticated" showed nothing.
//
// Envelope gate BELOW licence validation -- see api/sv-auth.js's note.
module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }
  const authz = req.headers['authorization'] || '';
  const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : null;
  if (!licenseKey) {
    res.status(401).json({ error: { code: 'NO_LICENSE', message: 'Missing bearer license key' } });
    return;
  }
  let lic;
  try {
    lic = await validateLicenseKey(licenseKey);
  } catch (err) {
    if (err && err.code === 'CONFIG') {
      res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
      return;
    }
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }
  if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }
  return runCountersignAction(PROFILE, req, res, lic);
};
module.exports.PROFILE = PROFILE;
module.exports.PREPARER_ROLES = PREPARER_ROLES;
