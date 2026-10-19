// api/law-countersign.js
// ---------------------------------------------------------------------------
// SAIRNlaw's countersignature lock -- the TWO-STAGE TRUST DISBURSEMENT. The
// profile is the whole file; see api/_lib/countersign.js for the mechanism and
// for why there is one mechanism rather than one copy per app.
//
// ── WHAT IT LOCKS AND WHY (practitioner answer C2, 2026-10-17, b18) ──────
// `law_trusttx`, MODE_PREPARED_ONLY. Michael's answer to C2 is that a
// paralegal MAY PREPARE a trust disbursement for an attorney to authorise.
//
// ── MODE_PREPARED_ONLY, AND THE DIFFERENCE FROM F1 IS A REAL DECISION ────
// SAIRNlegacy's lock is MODE_ALWAYS: a cremation authorisation needs a second
// person no matter who writes it. THIS ONE DOES NOT, and the reason is what
// C2 actually asked and answered. C2 asked whether a paralegal may prepare. It
// did NOT ask, and Michael did not answer, whether an attorney now needs a
// second attorney to move client money -- and deciding that here would be this
// file answering a bar-rules question nobody put to it.
//
// SO: an attorney or the firm owner writes a trust transaction exactly as they
// did before b18. A paralegal's disbursement is PREPARED, is a pending row
// that moves money nowhere, and is filed only when a bar-admitted person has
// signed it. The refusal a paralegal gets on a direct write NAMES that route
// (api/_lib/law-roles.js denyMessage), so the lock reads as a workflow rather
// than a wall.
//
// THIS ASYMMETRY IS THE MOST LIKELY THING IN b18 TO BE WRONG, and it is wrong
// in the direction of changing less than was asked rather than more. It is
// named as a follow-up question in the b18 handoff, not buried here.
//
// ── WHO MAY SIGN: THE LICENSURE TIER, IMPORTED ───────────────────────────
// LAW_BAR_ADMITTED_ROLES from api/_lib/law-roles.js -- C3's answer, `{ owner,
// attorney }`, modelled on api/sv-auth.js's PRESCRIBER_ROLES. IMPORTED, never
// re-listed: authorising money out of client trust is a legal act by a
// licensed person, and re-typing that list here would put the two copies in an
// access-control surface and an IOLTA ledger.
//
// ── WHO MAY PREPARE: LAW_TRUST_PREPARE_ROLES, ALSO IMPORTED ──────────────
// `{ paralegal }`. NOT `bookkeeper`: C1's answer is a money role and client
// trust is the one account C2's own question separates from the operating
// account. Adding bookkeeper is a decision, not a convenience, and it is a
// one-line change in law-roles.js where the policy lives.
//
// REQUIRES sql/sairnlaw_countersign_schema.sql AND
// sql/sairnlaw_employee_auth_schema.sql.
// ---------------------------------------------------------------------------

'use strict';

const cs = require('./_lib/countersign');
const { runCountersignAction } = require('./_lib/countersign-endpoint');
const { validateLicenseKey } = require('./_lib/license');
const lawRoles = require('./_lib/law-roles');
const { AUTH_TABLE_BY_APP } = require('./_lib/auth');

const APP = 'sairnlaw';

const PROFILE = Object.freeze({
  app: APP,
  employeeTable: AUTH_TABLE_BY_APP[APP],
  tokenTable: 'sairnlaw_countersign_tokens',
  sqlFile: 'sql/sairnlaw_countersign_schema.sql',
  // ONE RESOURCE. law_bankstatements is the other member of the trust lock and
  // is deliberately absent: it is the BANK's side of the three-way
  // reconciliation, it is imported rather than authored, and nobody at the
  // firm prepares one. api/_lib/law-roles.js's LAW_TRUST_TWO_STAGE says the
  // same thing and this list is asserted against it by arm E3 of
  // api/b18-countersign-lock.test.js rather than merely agreeing with it by
  // eye.
  lockedResources: Object.freeze(Object.assign(Object.create(null), {
    law_trusttx: cs.MODE_PREPARED_ONLY
  })),
  signerRoles: lawRoles.LAW_BAR_ADMITTED_ROLES,
  preparerRoles: lawRoles.LAW_TRUST_PREPARE_ROLES,
  signerLabel: 'an attorney or the firm owner',
  requiredMessage:
    'Money out of client trust has to be authorised by an attorney or the firm '
  + 'owner. This disbursement is prepared and is waiting for that signature -- '
  + 'nothing has moved and nothing was saved.',
  preparerRefusal:
    'Only an attorney, the firm owner or a paralegal preparing for one can '
  + 'stage a trust disbursement.',
  signerRefusal:
    'Only an attorney or the firm owner can authorise money out of client '
  + 'trust. A paralegal may prepare a disbursement but may not authorise one.'
});

// VALIDATED AT MODULE LOAD -- see api/leg-countersign.js for why.
cs.assertProfile(PROFILE);

// ── THE AUTH BOUNDARY, IN THE FILE THAT IS THE ROUTE ──────────────────────
// Method, bearer presence, then `validateLicenseKey` -- the same order as all
// fifteen api/*-auth.js handlers. api/leg-countersign.js carries the full note
// on why these ~30 lines appear in BOTH route files rather than once in
// api/_lib/countersign-endpoint.js: tools/preauth_oracle_check.py reported
// both as "UNDECLARED PUBLIC -- no auth boundary" when they delegated, and the
// checker was right.
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
