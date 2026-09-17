// api/_lib/auth.js
// ---------------------------------------------------------------------------
// Shared per-employee RBAC — PIN hashing + signed session tokens, used by
// BOTH StoneDesk (api/sd-auth.js) and SAIRNbiz (api/sb-auth.js), plus any
// api/*.js endpoint that needs to know WHO is calling and WHAT ROLE they
// hold (currently api/sd-data.js's employees resource, both read and
// write).
//
// WHY THIS EXISTS: the old client-side scaffolding (currentRole var,
// body.is-admin/is-exec, DEFAULT_PINS shared per role) never told the
// server anything — role was purely self-asserted in the browser. This
// gives the server something it can actually verify: a token signed with a
// secret only the server holds, naming one specific employee_id + role,
// expiring after SESSION_TTL_MS.
//
// GENERALIZED 2026-08-03 (was StoneDesk-only): api/sd-data.js's employees
// WRITE branch used to trust a client-supplied body.app_id==='sairnbiz'
// string with zero verification — any bearer of a shop's license key could
// set that field and write payroll data regardless of role. Fixing it
// couldn't rely on a secret embedded in sairnbiz.html itself (a static
// client file with no backend — anything in it is exactly as extractable
// as the app_id string already was). The real fix: sign WHICH APP issued
// the token as a claim inside the HMAC payload (unforgeable, unlike a body
// field), and give each app its own role vocabulary — StoneDesk's
// owner/admin/sales/install vs SAIRNbiz's owner/hr/accounting/manager/staff
// are deliberately separate, not merged (sql/sd_employee_auth_schema.sql
// vs sql/sb_employee_auth_schema.sql are two distinct tables, same design).
//
// Zero new npm dependencies — this app's api/ layer has none today
// (see api/_lib/license.js's use of built-in crypto). Token format is a
// minimal HMAC-signed JSON, not a full JWT library: header/alg negotiation
// isn't needed when both signer and verifier are this one codebase.
//
// REQUIRES env: SD_AUTH_SECRET (a long random string, shared across both
// apps' tokens — the `app` claim inside the signed payload is what keeps
// them distinct, not separate secrets; token forgery is possible without
// it, so treat it like SUPABASE_SERVICE_ROLE_KEY — set it in Vercel project
// env vars, never commit it).
// ---------------------------------------------------------------------------

const crypto = require('crypto');

const SESSION_TTL_MS = 12 * 60 * 60 * 1000; // 12h
const ROLES_BY_APP = {
  stonedesk: ['owner', 'admin', 'sales', 'install'],
  sairnbiz: ['owner', 'hr', 'accounting', 'manager', 'staff'],
  // Subcontractor Portal (2026-08-04): a DELIBERATELY separate app namespace,
  // not a new role added to 'stonedesk' above. Subs are not staff — giving
  // them a 'sub' role inside the 'stonedesk' app would mean any endpoint
  // that checks verifySessionToken(token, licHash, 'stonedesk') without also
  // checking the specific role would treat a sub token as a valid (if
  // low-privilege) employee token. A separate app means expectedApp:
  // 'stonedesk_sub' on every sub-facing check rejects an employee token
  // outright and vice versa, the same cross-app-collision discipline this
  // file's header already documents for stonedesk vs sairnbiz.
  stonedesk_sub: ['sub'],
  // SAIRNgrounds (2026-08-05): matches sairngrounds.html's Phase 1 role picker
  // (Superintendent/Grounds Manager/Crew/Office) plus 'owner' for bootstrap,
  // same convention as every other app's first-provisioned credential.
  sairngrounds: ['owner', 'superintendent', 'manager', 'crew', 'office'],
  // SAIRNscape (2026-08-06): matches sairnscape.html's Phase 1 role picker
  // (Owner/Crew Lead/Office) -- 'owner' already covers bootstrap.
  sairnscape: ['owner', 'crew_lead', 'office'],
  // SAIRNlaw (2026-08-08, Phase 3 security hardening): matches
  // sairnlaw.html's role picker (Owner/Attorney/Paralegal). Graduating from
  // the old shared-PIN-per-role scaffold to this real per-employee system
  // is what makes MFA and genuine session independence possible at all --
  // MFA authenticates a specific person, and a "session" that's really
  // just a shared role PIN has no single person to independently log out.
  sairnlaw: ['owner', 'attorney', 'paralegal'],
  // SAIRNcode (2026-08-18, real-data-layer + auth pass): matches the app's
  // existing role vocabulary exactly (its old client-only PIN gate already
  // had these 4 names -- coder/biller/auditor/admin -- just as one shared,
  // hardcoded, identical-for-every-customer PIN per role instead of a real
  // per-employee credential). 'admin' is the bootstrap/top role, matching
  // requireAdminForDelete()'s existing "Compliance Admin" framing in the UI.
  sairncode: ['admin', 'coder', 'biller', 'auditor'],
  // SAIRNdental (2026-08-27, EMERGENCY auth build). Matches sairndental.html's
  // existing role vocabulary EXACTLY -- owner/frontdesk/provider -- because
  // those three names were already in the app's old client-only PIN object
  // (`DEFAULT_PINS={owner:'1234',frontdesk:'2345',provider:'3456'}`, hardcoded
  // in a PUBLIC repo, compared in the browser, role stored in localStorage).
  // No fourth role invented: the app has no billing-only screen, and adding a
  // role nobody uses would be a permission surface with no feature behind it.
  // 'owner' is the bootstrap/provisioning role. This app holds PHI, so the
  // stakes on this list are higher than any other app's on the platform.
  sairndental: ['owner', 'frontdesk', 'provider'],
  // SAIRNmechanical (2026-08-27, recovery build). The app was written
  // 2026-06-14 on a branch that never merged, and is being brought onto main
  // only after real auth exists -- it shipped with
  // `DEFAULT_PINS={"owner":"1234","tech":"2345","sales":"3456","admin":"4567"}`
  // compared in the browser, the same client-only pattern StoneDesk, SAIRNcode
  // and SAIRNdental were each remediated for. Roles are the app's OWN four,
  // taken from that PIN object rather than invented, so nothing in the UI has
  // to be relearned. 'owner' provisions; 'admin' runs the office without
  // minting identities, matching SAIRNroofing's narrower split rather than
  // StoneDesk's.
  sairnmechanical: ['owner', 'admin', 'sales', 'tech'],
  // SAIRNlegacy (2026-08-19, real employee auth for the shared-knowledge
  // permission gate): matches sairnlegacy.html's existing role vocabulary
  // exactly (its old client-only PIN gate already had these 3 names --
  // owner/director/staff -- just as one shared, hardcoded, identical-for-
  // every-employee PIN per role instead of a real per-employee credential,
  // same starting point SAIRNlaw's owner/attorney/paralegal had before its
  // own Phase 3 hardening). 'owner' and 'director' are this app's
  // management tier (confirmed with Michael) -- 'staff' needs an explicit
  // per-employee grant for shared-knowledge access specifically, tracked
  // on the employee row itself, not a 4th role.
  sairnlegacy: ['owner', 'director', 'staff'],
  // SAIRNdesign (2026-08-20, real employee auth for the client/lead
  // privacy gate -- Task 2 of the platform sales-lead-privacy rule):
  // matches sairndesign.html's existing role vocabulary exactly
  // (owner/designer/office). 'owner' and 'office' are this app's
  // management tier -- 'office' is the closest thing this app has to a
  // back-office/coordinator role (no separate 'admin'/'manager' role
  // exists here, unlike StoneDesk), needing broad client visibility for
  // scheduling/invoicing the same way StoneDesk's 'admin' does; 'designer'
  // is the assigned-party role whose own clients get scoped, the analog
  // of StoneDesk's 'sales'. Flagged as a judgment call, not confirmed with
  // Michael ahead of building -- same reasoning documented in
  // api/sd-data.js's sdn_clients gate.
  sairndesign: ['owner', 'designer', 'office'],
  // SAIRNbuild (2026-08-20, real employee auth built from zero -- unlike
  // StoneDesk/SAIRNlegacy/SAIRNdesign this app had NO server auth at all
  // before now, just the client-only shared-PIN scaffold): matches
  // sairnbuild.html's existing DEFAULT_PINS role vocabulary exactly
  // (owner/pm/office). 'owner' and 'office' are this app's management
  // tier for the Bids & Proposals privacy gate -- 'office' is the closest
  // thing this app has to a back-office/coordinator role, same reasoning
  // as SAIRNdesign's 'office'; 'pm' (project manager) is the assigned-
  // party role whose own bids get scoped, the analog of StoneDesk's
  // 'sales'/SAIRNdesign's 'designer'. Judgment call, not confirmed with
  // Michael ahead of building -- same disclosed-not-silent pattern as
  // every prior app's role mapping in this file.
  sairnbuild: ['owner', 'pm', 'office'],
  // SAIRNsenior (2026-08-20, real employee auth built from zero, ground-up
  // like SAIRNlegacy/SAIRNlaw/SAIRNbuild): a home-care-agency operations
  // platform (caregivers travel to clients' homes, EVV/GPS visit
  // verification, multi-payer billing) -- confirmed as a SEPARATE app from
  // SAIRNcare (facility-based assisted living/hospice/retirement), a real
  // scope conflict found and resolved before any code was written (see
  // SAIRN-ACTIVE-WORK.md, 2026-08-20). Role vocabulary matches the app's
  // own real, dated SOP User Guide (agency owner, scheduler, care
  // coordinator, billing manager, caregiver), not invented. 'owner' and
  // 'billing' are this app's management tier for the HIPAA minimum-
  // necessary client-visibility gate -- billing needs claims/payer-level
  // visibility across the whole client roster the same way StoneDesk's
  // 'admin' does, and (unlike the pure-operational scheduler/coordinator
  // roles) has no legitimate reason to be scoped to one caregiver's
  // caseload. 'caregiver' is the assigned-party role whose own clients get
  // scoped, the analog of every other app's field/individual-contributor
  // role. Judgment call, not confirmed with Michael ahead of building --
  // same disclosed-not-silent pattern as every other app's role mapping.
  sairnsenior: ['owner', 'scheduler', 'coordinator', 'billing', 'caregiver'],
  // SAIRNcare (2026-08-20) -- ground-up, assisted-living facility app.
  // Scoped from live research, not a real signed SOP the way most other
  // apps' role lists were -- see docs/superpowers/specs/2026-08-20-
  // sairncare-v1-scope.md, flagged there as needing a real AL operator's
  // review before launch. 'owner' = Administrator/Executive Director, the
  // state-licensed role of record. 'nursing' = Resident Care Director
  // (often "Director of Nursing" depending on state licensing level) --
  // clinical oversight, care plans, medication program. 'med_aide' =
  // medication administration record access, own-assigned-residents-only
  // like every other app's front-line clinical role. 'caregiver' =
  // ADL/daily support, same scoping. 'billing' = Business Office/Billing
  // Manager, full resident-billing visibility, no clinical write access --
  // same split as sairnsenior's billing role. 'activities' = Activities
  // Coordinator, lighter read-only roster access, no clinical or billing
  // write access at all.
  sairncare: ['owner', 'nursing', 'med_aide', 'caregiver', 'billing', 'activities'],
  // SAIRNroofing (2026-08-24). Mid-market roofing contractor, 20-100 employees,
  // single- and multi-location. Confirmed by Michael before Phase 1 rather than
  // invented and discovered wrong later -- SAIRNcare cost a scope correction for
  // exactly that.
  //
  // 'estimator' is DELIBERATELY ONE COMBINED SALES-AND-ESTIMATING ROLE, not a
  // pair. That matches how residential/storm-restoration shops actually run at
  // this size: the person who knocks the door, meets the adjuster on the roof and
  // writes the estimate is usually the same person. A shop that later wants to
  // split sales from estimating is not blocked -- adding a role to this array and
  // a case to the visibility tiers is all it takes, because the privacy gate keys
  // on TIER (broad-read vs own-assigned) rather than on the literal role string.
  // Building the split now would be speculative structure for a shape nobody has
  // asked for yet.
  sairnroofing: ['owner', 'admin', 'estimator', 'foreman', 'crew'],
  // SAIRNvet (2026-09-13) -- the SIXTEENTH app to get per-employee auth and the
  // LAST one without it, which is the reason it was built now rather than in
  // turn. SAIRNvet holds `sv_controlled`, described in its own registry file as
  // "the controlled-substance register (DEA-relevant)", plus `sv_audit_log`,
  // its dosing trail. Until today the app authenticated on the LICENCE KEY
  // ONLY: sairnvet.html:2011 says so in its own words -- "`role` is a
  // self-selected dropdown, never server-verified". So the one app on the
  // platform holding a DEA-relevant register knew which PRACTICE was writing
  // and never which PERSON. Found 2026-09-13 while scoping the witnessing lock
  // (docs/2026-09-13-irreversible-write-witnessing-scoping.md), where it is
  // the hard prerequisite: a lock that records "the practice confirmed it" is
  // theatre.
  //
  // THE VOCABULARY IS THE APP'S OWN, READ OUT OF IT RATHER THAN INVENTED.
  // sairnvet.html's staff roster already offers exactly this list at two
  // places (:1365 and :6887): Owner/DVM, Associate DVM, Veterinary Technician,
  // Veterinary Assistant, Practice Manager, Front Desk, Other.
  //
  //   owner      -- Owner/DVM. Principal, and the only provisioning role.
  //   dvm        -- Associate DVM. A licensed veterinarian.
  //   tech       -- Veterinary Technician (CVT/RVT/LVT depending on state).
  //   assistant  -- Veterinary Assistant.
  //   manager    -- Practice Manager. Runs the office; NOT a clinician.
  //   frontdesk  -- Front Desk / reception.
  //
  // 'Other' IS DELIBERATELY DROPPED. It is a roster label, not an identity: a
  // role that means nothing cannot be gated on, and admitting it would put a
  // permanently un-gateable role into the access-control surface of an app
  // whose sharpest record is a controlled-substance log.
  //
  // owner + dvm ARE THE LICENSED-PRACTITIONER TIER and that distinction is
  // load-bearing rather than cosmetic -- a controlled-substance entry is a
  // legal act by a licensed veterinarian. Exported from api/sv-auth.js as
  // PRESCRIBER_ROLES so the witnessing lock imports it instead of re-listing
  // role names, which is the drift that cost SAIRNsenior a real bug.
  //
  // Judgment call on the SHORT NAMES only, not on the vocabulary -- same
  // disclosed-not-silent convention as every other app above.
  sairnvet: ['owner', 'dvm', 'tech', 'assistant', 'manager', 'frontdesk']
};
// Back-compat export — StoneDesk's own role list, unchanged shape for any
// existing caller that imported ROLES expecting just StoneDesk's set.
const ROLES = ROLES_BY_APP.stonedesk;

function b64url(buf) {
  return Buffer.from(buf).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function b64urlDecode(str) {
  str = str.replace(/-/g, '+').replace(/_/g, '/');
  while (str.length % 4) str += '=';
  return Buffer.from(str, 'base64');
}

function getSecret() {
  const s = process.env.SD_AUTH_SECRET;
  if (!s) {
    const e = new Error('SD_AUTH_SECRET not set in environment');
    e.code = 'CONFIG';
    throw e;
  }
  return s;
}

// ── STAGE C: KEY ID + DUAL-KEY VERIFICATION, SO ROTATION IS POSSIBLE ──────
// 2026-09-17. Before this there was no way to tell which key signed a token,
// so rotating the signing secret meant invalidating every live session at once.
//
// THE BACKWARD-COMPATIBLE PATTERN IS THE ONE THIS FILE ALREADY USED FOR `typ`
// on 2026-08-08: a claim that is ABSENT is treated as the legacy case and no
// already-issued token is invalidated. A token with no `kid` is simply tried
// against every configured key, which is exactly what it would have needed.
//
// HOW A ROTATION RUNS, and why it needs no mass logout: SESSION_TTL_MS is 12
// hours, so
//   1. set SD_AUTH_SECRET_PREVIOUS to the current secret,
//   2. set SD_AUTH_SECRET to the new one,
//   3. wait 12 hours -- every token signed with the old key has expired,
//   4. clear SD_AUTH_SECRET_PREVIOUS.
// Nobody is signed out; the window drains itself.
//
// THE KEY ID IS DERIVED FROM THE KEY, not named by hand. A hand-kept name is a
// second thing to get wrong during the one operation where being wrong logs
// everybody out, and this platform has recorded that shape (a hand-written list
// drifting from the thing it names) enough times to stop writing them.
//
// IT IS NOT A SECRET AND IS NOT TREATED AS ONE: eight hex characters of
// sha256(key), which identifies which key without narrowing a search for it.
// Selecting a key by the token's own `kid` is safe even though `kid` is
// attacker-controlled -- picking a key does not verify anything, and forging a
// signature still requires the key itself.
function keyId(secret) {
  return crypto.createHash('sha256').update(String(secret)).digest('hex').slice(0, 8);
}

// ── STAGE D: PER-APP SIGNING SECRETS ──────────────────────────────────────
// 2026-09-17. `SD_AUTH_SECRET_<APP>` (e.g. SD_AUTH_SECRET_SAIRNLAW) makes one
// app's sessions unforgeable with any other app's key. Entirely optional: an
// app with no dedicated secret uses the platform one exactly as before, so this
// rolls out app by app rather than as one cutover.
//
// AN APP WITH ITS OWN KEY DOES NOT ALSO ACCEPT THE PLATFORM KEY, and that is
// the whole point. Keeping the platform key as a permanent fallback would mean
// the platform secret could still mint SAIRNlaw tokens after SAIRNlaw had its
// own -- a blast-radius reduction that reduces nothing. The migration uses the
// SAME window stage C built: set SD_AUTH_SECRET_SAIRNLAW_PREVIOUS to the
// platform secret, set SD_AUTH_SECRET_SAIRNLAW to the new one, wait one
// SESSION_TTL_MS, clear the previous. Nobody is signed out and the platform key
// stops working for that app at the end.
//
// THE SUBTLETY, NAMED BEFORE ANYBODY TRIPS ON IT: a verifier has to choose a
// key BEFORE it has verified anything, and the only hint available is the
// token's own `app` claim -- which an attacker supplies. That is safe in fact
// (choosing a key is not trusting a claim, and forging a signature still needs
// the key) but it reads backwards against "verify before you trust", so it is
// written here rather than left for a reviewer to rediscover and mistake for a
// bug. The claim is re-checked properly after verification by
// verifySessionToken's ROLES_BY_APP and expectedApp checks.
function appEnvSuffix(app) {
  return String(app || '').toUpperCase().replace(/[^A-Z0-9]+/g, '_');
}

function signingKeys(app) {
  // Current first. Order is load-bearing: signPayload() always uses [0], and
  // verification tries them in order, so a token with no `kid` is checked
  // against the CURRENT key before the outgoing one.
  const suffix = appEnvSuffix(app);
  const appCur = suffix ? process.env['SD_AUTH_SECRET_' + suffix] : null;
  const out = [];
  const push = (v) => {
    const sv = String(v == null ? '' : v);
    if (!sv.trim()) return;
    if (out.some((k) => k.secret === sv)) return;   // a no-op rotation is a no-op
    out.push({ id: keyId(sv), secret: sv });
  };
  if (appCur && String(appCur).trim()) {
    push(appCur);
    push(process.env['SD_AUTH_SECRET_' + suffix + '_PREVIOUS']);
    return out;                                     // NO platform fallback -- see above
  }
  push(getSecret());
  push(process.env.SD_AUTH_SECRET_PREVIOUS);
  return out;
}

// EVERY token this file issues goes through here, and that is deliberate. A
// rotation that applied to session tokens but not to the SSO state token would
// be a partial rotation -- the subtlest possible version of this bug, and one
// that only shows up as a broken login half a day later.
function signPayload(payload) {
  // Keyed on the payload's own app. Every signer in this file includes one.
  const key = signingKeys(payload && payload.app)[0];
  const payloadB64 = b64url(JSON.stringify(
    Object.assign({ kid: key.id }, payload)));
  const sig = crypto.createHmac('sha256', key.secret).update(payloadB64).digest();
  return payloadB64 + '.' + b64url(sig);
}

// Returns the parsed payload when SOME configured key signed it, else null.
// Constant-time comparison per candidate, and a length check first because
// timingSafeEqual throws on a mismatch rather than returning false.
function verifySignedPayload(token) {
  if (!token || typeof token !== 'string') return null;
  const parts = token.split('.');
  if (parts.length !== 2) return null;
  const [payloadB64, sigB64] = parts;
  let givenSig;
  try { givenSig = b64urlDecode(sigB64); } catch (e) { return null; }
  // The app is read from the UNVERIFIED payload purely to choose which keys to
  // try -- see the note on signingKeys(). If it is absent or names an app with
  // no dedicated key, the platform keys are what get tried, which is exactly
  // what a pre-stage-D token needs.
  let claimedApp = null;
  let claimedKid = null;
  try {
    const peek = JSON.parse(b64urlDecode(payloadB64).toString('utf8'));
    if (peek && typeof peek.app === 'string') claimedApp = peek.app;
    if (peek && typeof peek.kid === 'string') claimedKid = peek.kid;
  } catch (e) { /* unparseable payload fails the signature check below anyway */ }

  let keys;
  try { keys = signingKeys(claimedApp); } catch (e) { return null; }

  // If the token names a key we hold, try that one FIRST -- it is the common
  // case and it keeps the expensive path short. It is not a shortcut around
  // verification: the signature is still checked, and an unknown or absent
  // `kid` falls through to trying every key.
  if (claimedKid) {
    keys = keys.slice().sort(function (a2, b2) {
      return (b2.id === claimedKid ? 1 : 0) - (a2.id === claimedKid ? 1 : 0);
    });
  }

  for (const k of keys) {
    const expected = crypto.createHmac('sha256', k.secret).update(payloadB64).digest();
    if (givenSig.length !== expected.length) continue;
    if (crypto.timingSafeEqual(givenSig, expected)) {
      try { return JSON.parse(b64urlDecode(payloadB64).toString('utf8')); }
      catch (e) { return null; }
    }
  }
  return null;
}

// ── PIN hashing (scrypt, per-credential random salt) ──────────────────────
function hashPin(pin) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(String(pin), salt, 64).toString('hex');
  return { pin_hash: hash, pin_salt: salt };
}

// Fixed dummy salt/hash used ONLY to keep verifyPin's cost constant when no
// real row exists (see DUMMY_HASH_FOR_TIMING below) — never a valid credential.
const DUMMY_SALT_FOR_TIMING = '0000000000000000000000000000000000000000000000000000000000000000';

function verifyPin(pin, pin_hash, pin_salt) {
  // SECURITY (security-auditor finding, 2026-08-03): when pin_hash/pin_salt
  // are absent (caller found no matching employee_id), always still run a
  // scrypt computation of equal cost against a fixed dummy salt before
  // returning false. Originally this branch short-circuited immediately —
  // real employee_ids took ~scrypt-cost ms to reject (wrong PIN), unknown
  // employee_ids returned in <1ms, and that response-time gap let an
  // attacker enumerate valid employee_ids before brute-forcing PINs against
  // only the confirmed-real ones. Constant-time now regardless of which
  // case this is.
  const saltToUse = pin_salt || DUMMY_SALT_FOR_TIMING;
  const check = crypto.scryptSync(String(pin || ''), saltToUse, 64);
  if (!pin || !pin_hash || !pin_salt) return false;
  const stored = Buffer.from(pin_hash, 'hex');
  if (check.length !== stored.length) return false;
  return crypto.timingSafeEqual(check, stored);
}

// ── Session tokens ──────────────────────────────────────────────────────
// signSessionToken({employee_id, role, license_hash, app}) -> 'payload.sig'
// `app` must be 'stonedesk' or 'sairnbiz' — it's signed INTO the payload
// (not a caller-suppliable field on verify), which is what makes this an
// actual fix for the old body.app_id=='sairnbiz' spoofing problem.
function signSessionToken(claims) {
  const app = claims.app;
  const roles = ROLES_BY_APP[app];
  if (!roles) {
    throw new Error('signSessionToken: unknown app "' + app + '"');
  }
  if (roles.indexOf(claims.role) === -1) {
    throw new Error('signSessionToken: invalid role "' + claims.role + '" for app "' + app + '"');
  }
  const payload = {
    typ: 'session', // added 2026-08-08 -- see verifySessionToken's own comment for why this is a safe, non-breaking addition
    app: app,
    employee_id: claims.employee_id,
    role: claims.role,
    license_hash: claims.license_hash,
    iat: Date.now(),
    exp: Date.now() + SESSION_TTL_MS
  };
  return signPayload(payload);
}

// verifySessionToken(token, license_hash, expectedApp) -> {employee_id, role, app} or null
// license_hash is required and checked: a token minted for one shop's
// license must never be accepted against a different shop's requests, even
// if somehow replayed (Bearer-license-per-request model matches
// api/sd-data.js — the token augments that, it doesn't replace it).
// expectedApp, when passed, requires the token's signed `app` claim to
// match — this is what lets a single endpoint (api/sd-data.js's employees
// write gate) tell a genuine StoneDesk token from a genuine SAIRNbiz token,
// without either app being able to just claim to be the other the way the
// old body.app_id string could.
function verifySessionToken(token, license_hash, expectedApp) {
  // SIGNATURE FIRST, through the shared verifier, so a rotation reaches this
  // path too. Everything below is unchanged -- the claim checks were already
  // right and are not what this stage is about.
  const payload = verifySignedPayload(token);
  // SECURITY (found while adding SAIRNlaw's MFA pre-auth token, 2026-08-08):
  // a pre-auth token (issued after PIN success, BEFORE the MFA code is
  // verified) has the same payload shape as a session token (app,
  // employee_id, role, license_hash, exp) and would otherwise pass every
  // check below unchanged -- meaning a caller could skip MFA entirely by
  // presenting the pre-auth token where a real session token is expected.
  // Explicit typ check closes this: existing StoneDesk/SAIRNbiz tokens
  // issued before this change have no `typ` field at all (payload.typ is
  // undefined) and must keep verifying exactly as before, so a MISSING typ
  // is accepted as an implicit 'session' (backward compatible, does not
  // invalidate any already-issued live token) -- but an EXPLICIT
  // typ:'preauth' is always rejected here, full stop.
  if (payload && payload.typ && payload.typ !== 'session') return null;
  if (!payload || !payload.app || !ROLES_BY_APP[payload.app]) return null;
  if (ROLES_BY_APP[payload.app].indexOf(payload.role) === -1) return null;
  if (expectedApp && payload.app !== expectedApp) return null;
  if (!payload.exp || Date.now() > payload.exp) return null;
  if (!license_hash || payload.license_hash !== license_hash) return null;

  return { employee_id: payload.employee_id, role: payload.role, app: payload.app };
}

// Convenience: pull the session token out of the X-SD-Auth header (kept
// separate from the Authorization header, which carries the license key —
// same "don't let two different secrets share one header" reasoning as
// api/sd-data.js keeping the license key out of the body/URL).
function tokenFromRequest(req) {
  const h = req.headers['x-sd-auth'];
  return typeof h === 'string' && h.trim() ? h.trim() : null;
}

// ── PRE-AUTH TOKENS (2026-08-08, SAIRNlaw MFA) ────────────────────────────
// A real, standard PIN-then-second-factor login is two round trips (PIN
// verified -> caller submits a TOTP code -> full session issued), but this
// codebase has no server-side session store between requests (every
// endpoint here is a stateless Vercel function). A short-lived, narrowly-
// scoped signed token carries "PIN was verified for this employee" between
// the two steps without needing one -- same signing mechanism as
// signSessionToken, deliberately different `typ` claim and a much shorter
// TTL (5 minutes, not 12 hours) so a leaked pre-auth token is far less
// useful than a leaked full session token, and it can never be presented
// to a data endpoint that expects a real session (verifySessionToken()
// below refuses any token whose typ isn't 'session').
const PREAUTH_TTL_MS = 5 * 60 * 1000;
function signPreAuthToken(claims) {
  return signPayload({ typ: 'preauth', app: claims.app, employee_id: claims.employee_id, role: claims.role, license_hash: claims.license_hash, iat: Date.now(), exp: Date.now() + PREAUTH_TTL_MS });
}
function verifyPreAuthToken(token, license_hash, expectedApp) {
  const claims = verifyRawToken(token);
  if (!claims) return null;
  if (claims.typ !== 'preauth') return null;
  if (expectedApp && claims.app !== expectedApp) return null;
  if (!license_hash || claims.license_hash !== license_hash) return null;
  return { employee_id: claims.employee_id, role: claims.role, app: claims.app };
}

// Shared signature/expiry verification, used by both verifySessionToken and
// verifyPreAuthToken so the two never drift on the actual crypto check.
function verifyRawToken(token) {
  const payload = verifySignedPayload(token);
  if (!payload || !payload.exp || Date.now() > payload.exp) return null;
  return payload;
}

// ── REAL TOTP (RFC 6238), zero external dependency ────────────────────────
// Standard 30-second-step, 6-digit, HMAC-SHA1 TOTP -- the same algorithm
// Google Authenticator/Authy/1Password/Microsoft Authenticator all
// implement, so a real code from any of those apps verifies correctly here
// and vice versa. Built on Node's built-in crypto only, matching this
// codebase's zero-new-npm-dependency convention (see this file's own
// header) -- no third-party MFA service, nothing to configure beyond the
// secret this generates and stores (encrypted, see encryptSecret below).
const TOTP_STEP_SECONDS = 30;
const TOTP_DIGITS = 6;
const TOTP_WINDOW = 1; // accept the previous/next 30s step too, for clock drift

// RFC 4648 base32 (no padding) -- what every real authenticator app expects
// for the secret encoded into an otpauth:// URI/QR code.
const BASE32_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
function base32Encode(buf) {
  let bits = 0, value = 0, output = '';
  for (let i = 0; i < buf.length; i++) {
    value = (value << 8) | buf[i];
    bits += 8;
    while (bits >= 5) { output += BASE32_ALPHABET[(value >>> (bits - 5)) & 31]; bits -= 5; }
  }
  if (bits > 0) output += BASE32_ALPHABET[(value << (5 - bits)) & 31];
  return output;
}
function base32Decode(str) {
  str = String(str || '').toUpperCase().replace(/=+$/, '');
  let bits = 0, value = 0;
  const bytes = [];
  for (let i = 0; i < str.length; i++) {
    const idx = BASE32_ALPHABET.indexOf(str[i]);
    if (idx === -1) continue;
    value = (value << 5) | idx;
    bits += 5;
    if (bits >= 8) { bytes.push((value >>> (bits - 8)) & 0xff); bits -= 8; }
  }
  return Buffer.from(bytes);
}

// A real 160-bit random secret (20 bytes -- the RFC-recommended length for
// HMAC-SHA1-based TOTP), never a predictable or short value.
function generateTotpSecret() {
  return base32Encode(crypto.randomBytes(20));
}

function totpAt(secretBase32, timeStepCounter) {
  const key = base32Decode(secretBase32);
  const counterBuf = Buffer.alloc(8);
  counterBuf.writeUInt32BE(Math.floor(timeStepCounter / 0x100000000), 0);
  counterBuf.writeUInt32BE(timeStepCounter >>> 0, 4);
  const hmac = crypto.createHmac('sha1', key).update(counterBuf).digest();
  const offset = hmac[hmac.length - 1] & 0x0f;
  const binCode = ((hmac[offset] & 0x7f) << 24) | ((hmac[offset + 1] & 0xff) << 16) | ((hmac[offset + 2] & 0xff) << 8) | (hmac[offset + 3] & 0xff);
  const code = binCode % Math.pow(10, TOTP_DIGITS);
  return String(code).padStart(TOTP_DIGITS, '0');
}

// Real, constant-time-per-candidate verification against a small window of
// time steps (now, and TOTP_WINDOW steps before/after) so a slightly-slow
// phone clock or network round trip doesn't spuriously reject a real code.
function verifyTotpCode(secretBase32, code) {
  const clean = String(code || '').replace(/\D/g, '');
  if (clean.length !== TOTP_DIGITS) return false;
  const counter = Math.floor(Date.now() / 1000 / TOTP_STEP_SECONDS);
  for (let w = -TOTP_WINDOW; w <= TOTP_WINDOW; w++) {
    const expected = totpAt(secretBase32, counter + w);
    const a = Buffer.from(expected), b = Buffer.from(clean);
    if (a.length === b.length && crypto.timingSafeEqual(a, b)) return true;
  }
  return false;
}

// Real otpauth:// provisioning URI -- what a QR code encodes for an
// authenticator app to scan. issuer/accountLabel are cosmetic (shown in the
// app), the secret is what actually matters cryptographically.
function totpProvisioningUri(secretBase32, accountLabel, issuer) {
  const label = encodeURIComponent((issuer || 'SAIRN') + ':' + accountLabel);
  const params = new URLSearchParams({ secret: secretBase32, issuer: issuer || 'SAIRN', algorithm: 'SHA1', digits: String(TOTP_DIGITS), period: String(TOTP_STEP_SECONDS) });
  return 'otpauth://totp/' + label + '?' + params.toString();
}

// ── AES-256-GCM encryption for stored MFA secrets ─────────────────────────
// A TOTP secret is a long-lived credential equivalent in sensitivity to a
// password -- unlike a PIN, it can't be one-way hashed (the server must be
// able to recompute the expected code from it), so it needs real encryption
// at rest, not just Supabase's own disk-level encryption (defense in depth
// -- see sql/sairnlaw_employee_auth_schema.sql's own header for why this
// matters even with RLS/service-role-only access already in place).
// Reuses SD_AUTH_SECRET (already treated as a real secret, never committed,
// set in Vercel env) rather than requiring a second secret to provision.
// ── STAGE B: THE ENCRYPTION DUTY IS SPLIT FROM THE SIGNING DUTY ───────────
// 2026-09-17. `getEncryptionKey()` used to be sha256(SD_AUTH_SECRET), so ONE
// string was both the session-signing HMAC key and the AES-256-GCM key for
// secrets at rest: attorney MFA/TOTP secrets (api/law-auth.js) and a stored
// Stedi API key (api/sc-credentials.js, api/sc-eligibility.js).
//
// TWO CONSEQUENCES, AND THE SECOND IS WHY THIS IS STAGE B RATHER THAN A NICETY.
// A leak did not only forge sessions, it decrypted every secret at rest. And
// the secret was effectively UNROTATABLE: changing it makes every stored
// ciphertext undecryptable, NOTHING ERRORS AT DEPLOY TIME, and MFA starts
// failing per-attorney as each one next signs in. "Rotate the shared secret"
// reads as routine hygiene and was a data-loss event with a delayed fuse.
//
// THE FORMAT CARRIES THE KEY IT USED, rather than the trial decryption the
// options document proposed. Trial decryption is SAFE here -- GCM's auth tag
// makes a wrong key fail cleanly instead of yielding garbage -- but it cannot
// tell you whether a backfill has finished, so the fallback could never be
// removed with confidence. A version segment can:
//
//   legacy   iv.tag.ciphertext          -> sha256(SD_AUTH_SECRET)
//   v2       v2.iv.tag.ciphertext       -> sha256(SD_ENCRYPTION_KEY)
//
// UNTIL `SD_ENCRYPTION_KEY` IS SET THIS DEPLOY CHANGES NOTHING. New writes stay
// in the legacy format and old values keep decrypting, so the code can land
// before the environment does -- the opposite order is what turns a migration
// into an outage.
const ENC_V2 = 'v2';

function dedicatedEncryptionKey() {
  const s = process.env.SD_ENCRYPTION_KEY;
  if (!s || !String(s).trim()) return null;
  // Derived rather than used raw for the same reason as before: AES-256 needs
  // exactly 32 bytes and whatever is pasted into the dashboard is not.
  return crypto.createHash('sha256').update(String(s)).digest();
}

function legacyEncryptionKey() {
  return crypto.createHash('sha256').update(getSecret()).digest();
}
function encryptSecret(plaintext) {
  const dedicated = dedicatedEncryptionKey();
  const key = dedicated || legacyEncryptionKey();
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  const encrypted = Buffer.concat([cipher.update(String(plaintext), 'utf8'), cipher.final()]);
  const authTag = cipher.getAuthTag();
  const body = b64url(iv) + '.' + b64url(authTag) + '.' + b64url(encrypted);
  return dedicated ? (ENC_V2 + '.' + body) : body;
}
function decryptSecret(stored) {
  let parts = String(stored || '').split('.');
  // WHICH KEY, DECIDED BY THE STORED FORMAT rather than by trying both. A `v2`
  // value was written with the dedicated key and must not silently fall back to
  // the signing secret: that fallback would quietly re-couple the two duties
  // this split exists to separate.
  let key;
  if (parts.length === 4 && parts[0] === ENC_V2) {
    const dedicated = dedicatedEncryptionKey();
    if (!dedicated) {
      // LOUD, because a null here is read by every caller as "no secret
      // stored" -- which for MFA means "MFA is not set up". A v2 ciphertext
      // with SD_ENCRYPTION_KEY unset is a CONFIGURATION error, not an absent
      // credential, and the two must not look alike in a log.
      console.error('auth: a v2 ciphertext was found but SD_ENCRYPTION_KEY is '
        + 'not set. This is a configuration error, not a missing secret -- the '
        + 'value was written by a deployment that had the key.');
      return null;
    }
    key = dedicated;
    parts = parts.slice(1);
  } else if (parts.length === 3) {
    key = legacyEncryptionKey();
  } else {
    return null;
  }
  const iv = b64urlDecode(parts[0]);
  const authTag = b64urlDecode(parts[1]);
  const encrypted = b64urlDecode(parts[2]);
  try {
    // authTagLength IS NOT OPTIONAL HERE, and omitting it is not the same as
    // leaving it at a safe default. Node accepts a GCM tag of 4, 8, or 12-16
    // bytes unless the length is pinned, and `authTag` above is read straight
    // out of the stored ciphertext -- so anything that can write that column
    // could present a FOUR-byte tag and drop forgery resistance from 2^128 to
    // 2^32. encryptSecret() has always produced the full 16 (getAuthTag()
    // defaults to it), so pinning it here rejects nothing that was written by
    // this codebase. Found by Semgrep `gcm-no-tag-length`, 2026-09-10.
    const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv, { authTagLength: 16 });
    if (authTag.length !== 16) return null;
    decipher.setAuthTag(authTag);
    return Buffer.concat([decipher.update(encrypted), decipher.final()]).toString('utf8');
  } catch (e) { return null; } // wrong key or tampered ciphertext -- never throw into a caller that might leak detail
}

// ── Generic OIDC client (real SSO, provider-agnostic) ─────────────────────
// A real, standards-compliant OpenID Connect authorization-code-flow client
// (RFC 6749 + OIDC Core), not a vendor-specific SDK -- works with any real
// OIDC-compliant identity provider (Google Workspace, Microsoft
// Entra ID, Okta, Auth0, etc.) once the 4 env vars below are set, so
// building this doesn't require knowing in advance which provider a firm
// will use. What it CANNOT do without those env vars: this server cannot
// register an OAuth application with any provider on anyone's behalf --
// that is a real account-creation step only the firm's own admin can do
// (same category of external dependency as CourtListener's API token,
// disclosed the same way — see NOT_CONFIGURED below).
// REQUIRES env (only when SSO is actually used): OIDC_ISSUER_URL,
// OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_REDIRECT_URI.
function oidcConfigured() {
  return !!(process.env.OIDC_ISSUER_URL && process.env.OIDC_CLIENT_ID && process.env.OIDC_CLIENT_SECRET && process.env.OIDC_REDIRECT_URI);
}
// Real PKCE (RFC 7636) -- required by several providers (Google included)
// even for confidential clients, and real defense against authorization-
// code interception regardless.
function generatePkcePair() {
  const verifier = b64url(crypto.randomBytes(32));
  const challenge = b64url(crypto.createHash('sha256').update(verifier).digest());
  return { verifier, challenge };
}
async function oidcDiscoverEndpoints() {
  const issuer = process.env.OIDC_ISSUER_URL;
  if (!issuer) { const e = new Error('OIDC not configured'); e.code = 'NOT_CONFIGURED'; throw e; }
  const wellKnownUrl = issuer.replace(/\/+$/, '') + '/.well-known/openid-configuration';
  const r = await fetch(wellKnownUrl);
  if (!r.ok) { const e = new Error('OIDC discovery failed: HTTP ' + r.status); e.status = 502; throw e; }
  return r.json();
}
function oidcAuthorizationUrl(endpoints, state, codeChallenge) {
  const params = new URLSearchParams({
    client_id: process.env.OIDC_CLIENT_ID, redirect_uri: process.env.OIDC_REDIRECT_URI,
    response_type: 'code', scope: 'openid email profile', state,
    code_challenge: codeChallenge, code_challenge_method: 'S256'
  });
  return endpoints.authorization_endpoint + '?' + params.toString();
}
async function oidcExchangeCode(endpoints, code, codeVerifier) {
  const r = await fetch(endpoints.token_endpoint, {
    method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code', code, redirect_uri: process.env.OIDC_REDIRECT_URI,
      client_id: process.env.OIDC_CLIENT_ID, client_secret: process.env.OIDC_CLIENT_SECRET, code_verifier: codeVerifier
    })
  });
  const data = await r.json();
  if (!r.ok) { const e = new Error('OIDC token exchange failed: ' + JSON.stringify(data).slice(0, 300)); e.status = 502; throw e; }
  return data; // { id_token, access_token, ... } -- id_token is a real JWT from the provider; callers MUST run it through oidcVerifyIdToken() below before trusting any claim, this function does no verification itself
}
// Decodes WITHOUT verifying signature/exp/iss/aud -- only safe to call on
// an id_token that oidcVerifyIdToken() has already verified (e.g. to read
// convenience claims after verification), or in a context that doesn't
// need trust (never for auth decisions). Kept separate from
// oidcVerifyIdToken so callers can't accidentally skip verification by
// reaching for the decode function first.
function decodeIdTokenUnverified(idToken) {
  const parts = String(idToken || '').split('.');
  if (parts.length !== 3) return null;
  try { return JSON.parse(b64urlDecode(parts[1]).toString('utf8')); } catch (e) { return null; }
}

// Real cryptographic verification against the provider's own published
// JWKS (2026-08-08 — closes the gap flagged above, rather than shipping
// SSO on decode-only trust). Fetches endpoints.jwks_uri, matches the
// id_token's `kid`, verifies the RS256 signature with Node's built-in
// crypto (no external JWT library), and checks exp/iss/aud. RS256 is the
// only algorithm accepted — every major OIDC provider (Google Workspace,
// Entra ID, Okta, Auth0) defaults to it; anything else fails closed rather
// than silently trusting an unexpected alg (e.g. a provider misconfigured
// to allow `alg:none`).
async function oidcVerifyIdToken(endpoints, idToken) {
  const parts = String(idToken || '').split('.');
  if (parts.length !== 3) { const e = new Error('Malformed id_token'); e.status = 502; throw e; }
  const [headerB64, payloadB64, sigB64] = parts;
  let header, payload;
  try {
    header = JSON.parse(b64urlDecode(headerB64).toString('utf8'));
    payload = JSON.parse(b64urlDecode(payloadB64).toString('utf8'));
  } catch (e) { const err = new Error('Malformed id_token JSON'); err.status = 502; throw err; }
  if (header.alg !== 'RS256') { const e = new Error('Unsupported id_token alg: ' + header.alg); e.status = 502; throw e; }

  const jwksUrl = endpoints.jwks_uri;
  if (!jwksUrl) { const e = new Error('OIDC discovery document missing jwks_uri'); e.status = 502; throw e; }
  const jwksResp = await fetch(jwksUrl);
  if (!jwksResp.ok) { const e = new Error('JWKS fetch failed: HTTP ' + jwksResp.status); e.status = 502; throw e; }
  const jwks = await jwksResp.json();
  const jwk = Array.isArray(jwks.keys) && jwks.keys.find(k => k.kid === header.kid && k.kty === 'RSA');
  if (!jwk) { const e = new Error('No matching JWKS key for kid ' + header.kid); e.status = 502; throw e; }

  let publicKey;
  try {
    publicKey = crypto.createPublicKey({ key: { kty: 'RSA', n: jwk.n, e: jwk.e }, format: 'jwk' });
  } catch (e) { const err = new Error('Invalid JWK from provider'); err.status = 502; throw err; }

  const signingInput = Buffer.from(headerB64 + '.' + payloadB64, 'utf8');
  const signature = b64urlDecode(sigB64);
  const sigValid = crypto.verify('RSA-SHA256', signingInput, publicKey, signature);
  if (!sigValid) { const e = new Error('id_token signature verification failed'); e.status = 401; throw e; }

  if (!payload.exp || Date.now() >= payload.exp * 1000) { const e = new Error('id_token expired'); e.status = 401; throw e; }
  const expectedIssuer = process.env.OIDC_ISSUER_URL;
  if (expectedIssuer && payload.iss && payload.iss.replace(/\/+$/, '') !== expectedIssuer.replace(/\/+$/, '')) {
    const e = new Error('id_token iss mismatch'); e.status = 401; throw e;
  }
  const expectedAud = process.env.OIDC_CLIENT_ID;
  const aud = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
  if (expectedAud && aud.indexOf(expectedAud) === -1) { const e = new Error('id_token aud mismatch'); e.status = 401; throw e; }

  return payload;
}

// ── SSO STATE TOKENS ───────────────────────────────────────────────────────
// The OIDC authorization-code flow needs to carry the PKCE code_verifier
// and which license/app initiated the flow from sso_start through to
// sso_callback, across a redirect to the IdP and back -- another case (like
// pre-auth tokens above) where this codebase's stateless-serverless-
// function constraint means there's no server-side place to stash it
// between requests. Same signed-token mechanism, deliberately different
// `typ` so it can never be presented as a preauth or session token
// (verifyRawToken alone doesn't check typ -- callers must, same as
// verifyPreAuthToken/verifySessionToken do for their own typ).
const SSO_STATE_TTL_MS = 10 * 60 * 1000;
function signSsoState(claims) {
  return signPayload({
    typ: 'sso_state', app: claims.app, license_hash: claims.license_hash,
    code_verifier: claims.code_verifier, iat: Date.now(), exp: Date.now() + SSO_STATE_TTL_MS
  });
}
function verifySsoState(token, expectedApp) {
  const claims = verifyRawToken(token);
  if (!claims) return null;
  if (claims.typ !== 'sso_state') return null;
  if (expectedApp && claims.app !== expectedApp) return null;
  return { license_hash: claims.license_hash, code_verifier: claims.code_verifier };
}

// ── A TOKEN IS A CLAIM ABOUT THE PAST ──────────────────────────────────────
// `verifySessionToken` proves a token was minted by this platform, for this
// licence and this app, and has not expired. IT PROVES NOTHING ABOUT NOW.
//
// THE LIVE FINDING, 2026-08-23, on SAIRNcode and against production: a session
// token carries a role claim and stays valid for its full 12h life INCLUDING
// after the credential behind it is deactivated. `api/sc-auth.js` fixed that
// for its own `roster` and `set_active`, and `api/_lib/employee-lifecycle.js`
// carries the same re-check for the apps that share it.
//
// NOTHING CLOSED IT FOR THE DATA PATH. `api/sd-data.js` gates thirteen apps'
// resources on `session.role` read from the token claim and never asks whether
// that credential is still active, so a deactivated employee kept read and
// write access to every gated resource until their token happened to expire.
// Deactivation is the one control an owner has for somebody who has just left.
//
// DECLARED, NEVER DERIVED. Fifteen apps and no rule: `sd`, `sb`, `grd` and
// `scp` use a prefix, the rest use the full app name, and `sairncare`'s table
// is not `alf_*` though its endpoint is. A derivation would be wrong for at
// least five of them and wrong SILENTLY -- a missing table reads as "no active
// row", which would refuse every caller in that app.
const AUTH_TABLE_BY_APP = {
  stonedesk: 'sd_employee_auth',
  sairnbiz: 'sb_employee_auth',
  sairngrounds: 'grd_employee_auth',
  sairnscape: 'scp_employee_auth',
  sairnlaw: 'sairnlaw_employee_auth',
  sairncode: 'sairncode_employee_auth',
  sairndental: 'sairndental_employee_auth',
  sairnmechanical: 'sairnmechanical_employee_auth',
  sairnlegacy: 'sairnlegacy_employee_auth',
  sairndesign: 'sairndesign_employee_auth',
  sairnbuild: 'sairnbuild_employee_auth',
  sairnsenior: 'sairnsenior_employee_auth',
  sairncare: 'sairncare_employee_auth',
  sairnroofing: 'sairnroofing_employee_auth',
  sairnvet: 'sairnvet_employee_auth'
  // stonedesk_sub is DELIBERATELY ABSENT. Subcontractors authenticate against
  // `sd_sub_auth` keyed on sub_id, not employee_id, and their removal path is
  // a different one. Listing it here with the wrong key would refuse every
  // subcontractor; omitting it makes credentialStillActive() answer
  // NO_ACTIVE_CHECK, which the caller must handle rather than read as a pass.
};

/**
 * Is the credential behind this session STILL active?
 *
 * Returns { ok: true } when it is, { ok: false, code, message } when it is not,
 * and { ok: false, code: 'NO_ACTIVE_CHECK' } when this app has no employee
 * table to ask. THE THIRD STATE IS NOT A PASS and is not an error -- it is
 * "could not tell", and a caller that folds it into either is the defect this
 * platform has a standing rule against.
 *
 * COSTS ONE QUERY PER GATED REQUEST, and that is the price of the control
 * rather than an oversight. It is a single indexed lookup by licence and
 * employee id, and the alternative -- a cache -- would reintroduce exactly the
 * window this closes, just shorter.
 */
async function credentialStillActive(session, licHash, rest, headers) {
  if (!session || !session.employee_id) {
    return { ok: false, code: 'FORBIDDEN', message: 'A valid employee session is required' };
  }
  const table = AUTH_TABLE_BY_APP[session.app];
  if (!table) return { ok: false, code: 'NO_ACTIVE_CHECK' };
  let rows;
  try {
    const r = await fetch(rest(table + '?license_hash=eq.' + encodeURIComponent(licHash) +
      '&employee_id=eq.' + encodeURIComponent(session.employee_id) +
      '&select=active&limit=1'), { headers });
    rows = await r.json();
    if (!r.ok) return { ok: false, code: 'NO_ACTIVE_CHECK' };
  } catch (e) {
    // A TRANSPORT FAILURE IS NOT A DEACTIVATION. Answering "inactive" here
    // would lock every user out of an app whenever the database blinked, and
    // answering "active" would silently disable the control. Third state.
    return { ok: false, code: 'NO_ACTIVE_CHECK' };
  }
  const row = Array.isArray(rows) && rows[0];
  if (!row || row.active !== true) {
    return {
      ok: false,
      code: 'CREDENTIAL_INACTIVE',
      message: 'This credential has been deactivated. Sign in again with an active account.'
    };
  }
  return { ok: true };
}

module.exports = {
  ROLES,
  ROLES_BY_APP,
  AUTH_TABLE_BY_APP,
  credentialStillActive,
  hashPin,
  verifyPin,
  signSessionToken,
  verifySessionToken,
  signPreAuthToken,
  verifyPreAuthToken,
  tokenFromRequest,
  generateTotpSecret,
  verifyTotpCode,
  totpProvisioningUri,
  encryptSecret,
  decryptSecret,
  oidcConfigured,
  generatePkcePair,
  oidcDiscoverEndpoints,
  oidcAuthorizationUrl,
  oidcExchangeCode,
  decodeIdTokenUnverified,
  oidcVerifyIdToken,
  signSsoState,
  verifySsoState
};
