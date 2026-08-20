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
  sairndesign: ['owner', 'designer', 'office']
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
  const secret = getSecret();
  const payload = {
    typ: 'session', // added 2026-08-08 -- see verifySessionToken's own comment for why this is a safe, non-breaking addition
    app: app,
    employee_id: claims.employee_id,
    role: claims.role,
    license_hash: claims.license_hash,
    iat: Date.now(),
    exp: Date.now() + SESSION_TTL_MS
  };
  const payloadStr = JSON.stringify(payload);
  const payloadB64 = b64url(payloadStr);
  const sig = crypto.createHmac('sha256', secret).update(payloadB64).digest();
  return payloadB64 + '.' + b64url(sig);
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
  if (!token || typeof token !== 'string') return null;
  const parts = token.split('.');
  if (parts.length !== 2) return null;
  const [payloadB64, sigB64] = parts;
  let secret;
  try { secret = getSecret(); } catch (e) { return null; }
  const expectedSig = crypto.createHmac('sha256', secret).update(payloadB64).digest();
  let givenSig;
  try { givenSig = b64urlDecode(sigB64); } catch (e) { return null; }
  if (givenSig.length !== expectedSig.length) return null;
  if (!crypto.timingSafeEqual(givenSig, expectedSig)) return null;

  let payload;
  try { payload = JSON.parse(b64urlDecode(payloadB64).toString('utf8')); } catch (e) { return null; }
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
  const secret = getSecret();
  const payload = { typ: 'preauth', app: claims.app, employee_id: claims.employee_id, role: claims.role, license_hash: claims.license_hash, iat: Date.now(), exp: Date.now() + PREAUTH_TTL_MS };
  const payloadB64 = b64url(JSON.stringify(payload));
  const sig = crypto.createHmac('sha256', secret).update(payloadB64).digest();
  return payloadB64 + '.' + b64url(sig);
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
  if (!token || typeof token !== 'string') return null;
  const parts = token.split('.');
  if (parts.length !== 2) return null;
  const [payloadB64, sigB64] = parts;
  let secret;
  try { secret = getSecret(); } catch (e) { return null; }
  const expectedSig = crypto.createHmac('sha256', secret).update(payloadB64).digest();
  let givenSig;
  try { givenSig = b64urlDecode(sigB64); } catch (e) { return null; }
  if (givenSig.length !== expectedSig.length) return null;
  if (!crypto.timingSafeEqual(givenSig, expectedSig)) return null;
  let payload;
  try { payload = JSON.parse(b64urlDecode(payloadB64).toString('utf8')); } catch (e) { return null; }
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
function getEncryptionKey() {
  // A 32-byte key is required for AES-256 -- SD_AUTH_SECRET's own length is
  // whatever Michael generated it as, so this derives a real fixed-length
  // key from it via SHA-256 rather than assuming the raw secret is exactly
  // 32 bytes.
  return crypto.createHash('sha256').update(getSecret()).digest();
}
function encryptSecret(plaintext) {
  const key = getEncryptionKey();
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  const encrypted = Buffer.concat([cipher.update(String(plaintext), 'utf8'), cipher.final()]);
  const authTag = cipher.getAuthTag();
  return b64url(iv) + '.' + b64url(authTag) + '.' + b64url(encrypted);
}
function decryptSecret(stored) {
  const parts = String(stored || '').split('.');
  if (parts.length !== 3) return null;
  const key = getEncryptionKey();
  const iv = b64urlDecode(parts[0]);
  const authTag = b64urlDecode(parts[1]);
  const encrypted = b64urlDecode(parts[2]);
  try {
    const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
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
  const secret = getSecret();
  const payload = {
    typ: 'sso_state', app: claims.app, license_hash: claims.license_hash,
    code_verifier: claims.code_verifier, iat: Date.now(), exp: Date.now() + SSO_STATE_TTL_MS
  };
  const payloadB64 = b64url(JSON.stringify(payload));
  const sig = crypto.createHmac('sha256', secret).update(payloadB64).digest();
  return payloadB64 + '.' + b64url(sig);
}
function verifySsoState(token, expectedApp) {
  const claims = verifyRawToken(token);
  if (!claims) return null;
  if (claims.typ !== 'sso_state') return null;
  if (expectedApp && claims.app !== expectedApp) return null;
  return { license_hash: claims.license_hash, code_verifier: claims.code_verifier };
}

module.exports = {
  ROLES,
  ROLES_BY_APP,
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
