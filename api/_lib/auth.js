// api/_lib/auth.js
// ---------------------------------------------------------------------------
// StoneDesk per-employee RBAC — PIN hashing + signed session tokens.
// Shared by api/sd-auth.js (issues tokens) and any api/*.js endpoint that
// needs to know WHO is calling and WHAT ROLE they hold (currently
// api/sd-data.js's employees resource).
//
// WHY THIS EXISTS: the old client-side scaffolding (currentRole var,
// body.is-admin/is-exec, DEFAULT_PINS shared per role) never told the
// server anything — role was purely self-asserted in the browser. This
// gives the server something it can actually verify: a token signed with a
// secret only the server holds, naming one specific employee_id + role,
// expiring after SESSION_TTL_MS.
//
// Zero new npm dependencies — this app's api/ layer has none today
// (see api/_lib/license.js's use of built-in crypto). Token format is a
// minimal HMAC-signed JSON, not a full JWT library: header/alg negotiation
// isn't needed when both signer and verifier are this one codebase.
//
// REQUIRES env: SD_AUTH_SECRET (a long random string; token forgery is
// possible without it, so treat it like SUPABASE_SERVICE_ROLE_KEY — set it
// in Vercel project env vars, never commit it).
// ---------------------------------------------------------------------------

const crypto = require('crypto');

const SESSION_TTL_MS = 12 * 60 * 60 * 1000; // 12h
const ROLES = ['owner', 'admin', 'sales', 'install'];

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
// signSessionToken({employee_id, role, license_hash}) -> 'payload.sig'
function signSessionToken(claims) {
  if (ROLES.indexOf(claims.role) === -1) {
    throw new Error('signSessionToken: invalid role "' + claims.role + '"');
  }
  const secret = getSecret();
  const payload = {
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

// verifySessionToken(token, license_hash) -> {employee_id, role} or null
// license_hash is required and checked: a token minted for one shop's
// license must never be accepted against a different shop's requests, even
// if somehow replayed (Bearer-license-per-request model matches
// api/sd-data.js — the token augments that, it doesn't replace it).
function verifySessionToken(token, license_hash) {
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
  if (!payload || ROLES.indexOf(payload.role) === -1) return null;
  if (!payload.exp || Date.now() > payload.exp) return null;
  if (!license_hash || payload.license_hash !== license_hash) return null;

  return { employee_id: payload.employee_id, role: payload.role };
}

// Convenience: pull the session token out of the X-SD-Auth header (kept
// separate from the Authorization header, which carries the license key —
// same "don't let two different secrets share one header" reasoning as
// api/sd-data.js keeping the license key out of the body/URL).
function tokenFromRequest(req) {
  const h = req.headers['x-sd-auth'];
  return typeof h === 'string' && h.trim() ? h.trim() : null;
}

module.exports = {
  ROLES,
  hashPin,
  verifyPin,
  signSessionToken,
  verifySessionToken,
  tokenFromRequest
};
