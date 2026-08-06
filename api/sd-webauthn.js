// api/sd-webauthn.js
// ---------------------------------------------------------------------------
// StoneDesk passwordless login via WebAuthn/passkeys -- ADDITIONAL login
// method alongside PIN auth (api/sd-auth.js), not a replacement. PIN stays
// as fallback for devices/browsers without WebAuthn support.
//
// NOT facial recognition, NOT biometric data collection. The device's own
// platform authenticator (Face ID / Touch ID / Windows Hello) verifies the
// person LOCALLY and this server never receives or stores any biometric
// data -- only a public key and a signed challenge, the cryptographic
// output of a local check, same category of thing as a TLS certificate.
// This is deliberate: server-side facial recognition would trigger BIPA
// and similar biometric-privacy-law exposure (written consent, published
// retention schedule, real class-action history) -- WebAuthn sidesteps
// that class of risk entirely because no biometric data is ever collected.
//
// Uses @simplewebauthn/server (this repo's first npm dependency -- see
// package.json's header for why hand-rolling this class of crypto code
// would be the wrong call).
//
// Four actions, all POST, license key via Authorization: Bearer:
//
//   action: 'reg-options'   (requires X-SD-Auth -- registration ADDS a
//     passkey for an already PIN-authenticated employee, never creates a
//     new identity) -> { ok, options, challengeToken }
//
//   action: 'reg-verify'    { response, challengeToken } (requires
//     X-SD-Auth, same session the options were issued to)
//     -> { ok, credentialId }
//
//   action: 'auth-options'  { employee_id } (no session yet -- this IS the
//     login step) -> { ok, options, challengeToken }
//     Deliberately returns a well-formed (possibly empty-allowCredentials)
//     response for an unknown employee_id rather than a distinguishing
//     error, so this endpoint can't be used to enumerate valid employee
//     IDs -- same principle as api/sd-auth.js's login action returning a
//     generic INVALID_CREDENTIALS regardless of whether the employee_id
//     exists.
//
//   action: 'auth-verify'   { response, challengeToken } -> { ok, token,
//     role, employee_id } -- same response shape as api/sd-auth.js's own
//     login action, so client-side session handling after either method
//     is identical.
//
// challengeToken is a short-lived (5 min), HMAC-signed, stateless token
// binding {challenge, purpose, employee_id, license_hash, exp} -- avoids
// needing a server-side challenge-storage table between the two requests
// of each ceremony, consistent with this codebase's existing
// sign/verifySessionToken pattern (api/_lib/auth.js) rather than adding a
// new stateful table for something this short-lived.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SD_AUTH_SECRET
// (same shared secret as every other app's session tokens -- reused here
// for challenge tokens too, scoped apart by the `purpose` claim).
// ---------------------------------------------------------------------------

const crypto = require('crypto');
const {
  generateRegistrationOptions,
  verifyRegistrationResponse,
  generateAuthenticationOptions,
  verifyAuthenticationResponse
} = require('@simplewebauthn/server');
const { validateLicenseKey } = require('./_lib/license');
const { verifySessionToken, tokenFromRequest, signSessionToken } = require('./_lib/auth');

const APP = 'stonedesk';
const TABLE = 'sd_webauthn_credentials';
const AUTH_TABLE = 'sd_employee_auth';
const RP_NAME = 'StoneDesk';
const RP_ID = 'sairn.vercel.app';
const ORIGIN = 'https://sairn.vercel.app';
const CHALLENGE_TTL_MS = 5 * 60 * 1000; // 5 minutes -- long enough for a real ceremony, short enough to limit replay window

function b64url(buf) {
  return Buffer.from(buf).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function b64urlDecode(str) {
  str = str.replace(/-/g, '+').replace(/_/g, '/');
  while (str.length % 4) str += '=';
  return Buffer.from(str, 'base64');
}
function getChallengeSecret() {
  const s = process.env.SD_AUTH_SECRET;
  if (!s) { const e = new Error('SD_AUTH_SECRET not set'); e.code = 'CONFIG'; throw e; }
  return s;
}
function signChallengeToken(payload) {
  const secret = getChallengeSecret();
  const payloadB64 = b64url(JSON.stringify(payload));
  const sig = crypto.createHmac('sha256', secret).update(payloadB64).digest();
  return payloadB64 + '.' + b64url(sig);
}
function verifyChallengeToken(token, purpose, employeeId, licHash) {
  if (!token || typeof token !== 'string') return null;
  const parts = token.split('.');
  if (parts.length !== 2) return null;
  const [payloadB64, sigB64] = parts;
  let secret;
  try { secret = getChallengeSecret(); } catch (e) { return null; }
  const expectedSig = crypto.createHmac('sha256', secret).update(payloadB64).digest();
  let givenSig;
  try { givenSig = b64urlDecode(sigB64); } catch (e) { return null; }
  if (givenSig.length !== expectedSig.length) return null;
  if (!crypto.timingSafeEqual(givenSig, expectedSig)) return null;
  let payload;
  try { payload = JSON.parse(b64urlDecode(payloadB64).toString('utf8')); } catch (e) { return null; }
  if (!payload || payload.purpose !== purpose) return null;
  if (!payload.exp || Date.now() > payload.exp) return null;
  if (payload.employee_id !== employeeId) return null;
  if (payload.license_hash !== licHash) return null;
  return payload;
}

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

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) {
      res.status(400).json({ error: { message: 'Invalid JSON body' } });
      return;
    }
  }
  const action = body && body.action;
  if (['reg-options', 'reg-verify', 'auth-options', 'auth-verify'].indexOf(action) === -1) {
    res.status(400).json({ error: { message: "action must be 'reg-options', 'reg-verify', 'auth-options', or 'auth-verify'" } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY || !process.env.SD_AUTH_SECRET) {
    console.error('sd-webauthn: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  let lic;
  try {
    lic = await validateLicenseKey(licenseKey);
  } catch (err) {
    if (err.code === 'CONFIG') { res.status(500).json({ error: { message: 'Server configuration error — contact support' } }); return; }
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }
  if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }

  const licHash = lic.license_hash;
  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };
  const rest = (path) => SUPABASE_URL + '/rest/v1/' + path;
  const enc = encodeURIComponent;

  try {
    if (action === 'reg-options') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!session) { res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Sign in with your PIN first, then register a passkey' } }); return; }
      const existing = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&employee_id=eq.' + enc(session.employee_id) + '&select=credential_id,transports'), { headers });
      if (existing.status === 404 || existing.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Passkey storage is not set up yet — run sql/sd_webauthn_credentials_schema.sql in Supabase first.' } }); return; }
      const existingRows = existing.ok ? await existing.json() : [];
      const excludeCredentials = (existingRows || []).map((r) => ({ id: r.credential_id, transports: r.transports || undefined }));
      const options = await generateRegistrationOptions({
        rpName: RP_NAME,
        rpID: RP_ID,
        userName: session.employee_id,
        // BUGFIX (2026-08-06, confirmed via a real navigator.credentials.create()
        // call against a CDP virtual authenticator -- "TypeError: User handle
        // exceeds 64 bytes."): the raw concatenation licHash + ':' + employee_id
        // is 64 bytes (the hex-encoded sha256 hash alone) plus a colon plus the
        // employee_id itself -- always over the WebAuthn spec's 64-byte user.id
        // ceiling, for every real employee_id, not just long ones. The spec limit
        // is enforced by the browser/authenticator at navigator.credentials.create()
        // time, not by this library's option-generation step, which is why this
        // didn't surface until an actual ceremony ran. Fixed with a fixed-size
        // (32-byte) sha256 digest of the same identifier instead of the raw
        // string -- still deterministic per (license, employee) pair, which is
        // what matters for excludeCredentials/resident-key matching to work
        // correctly across repeat registrations, well under the limit regardless
        // of employee_id length.
        userID: crypto.createHash('sha256').update(licHash + ':' + session.employee_id).digest(),
        attestationType: 'none',
        excludeCredentials,
        authenticatorSelection: { residentKey: 'preferred', userVerification: 'preferred' }
      });
      const challengeToken = signChallengeToken({ challenge: options.challenge, purpose: 'reg', employee_id: session.employee_id, license_hash: licHash, exp: Date.now() + CHALLENGE_TTL_MS });
      res.status(200).json({ ok: true, options, challengeToken });
      return;
    }

    if (action === 'reg-verify') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!session) { res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Sign in with your PIN first, then register a passkey' } }); return; }
      const challengePayload = verifyChallengeToken(body.challengeToken, 'reg', session.employee_id, licHash);
      if (!challengePayload) { res.status(400).json({ error: { code: 'CHALLENGE_EXPIRED', message: 'Registration expired — try again' } }); return; }
      let verification;
      try {
        verification = await verifyRegistrationResponse({
          response: body.response,
          expectedChallenge: challengePayload.challenge,
          expectedOrigin: ORIGIN,
          expectedRPID: RP_ID
        });
      } catch (err) {
        res.status(400).json({ error: { code: 'VERIFICATION_FAILED', message: 'Could not verify passkey — try again' } });
        return;
      }
      if (!verification.verified || !verification.registrationInfo) {
        res.status(400).json({ error: { code: 'VERIFICATION_FAILED', message: 'Could not verify passkey — try again' } });
        return;
      }
      const info = verification.registrationInfo;
      const deviceLabel = (function () {
        const ua = req.headers['user-agent'] || '';
        if (/windows/i.test(ua)) return 'Windows device';
        if (/mac ?os|macintosh/i.test(ua)) return 'Mac device';
        if (/iphone|ipad/i.test(ua)) return 'iOS device';
        if (/android/i.test(ua)) return 'Android device';
        return 'Unknown device';
      })();
      const r = await fetch(rest(TABLE), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash,
          employee_id: session.employee_id,
          credential_id: info.credential.id,
          public_key: Buffer.from(info.credential.publicKey).toString('base64'),
          counter: info.credential.counter,
          transports: info.credential.transports || [],
          device_type: info.credentialDeviceType,
          backed_up: info.credentialBackedUp,
          device_label: deviceLabel
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, credentialId: info.credential.id });
      return;
    }

    if (action === 'auth-options') {
      const employeeId = String((body.employee_id || '')).trim();
      if (!employeeId) { res.status(400).json({ error: { message: 'employee_id is required' } }); return; }
      const existing = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&employee_id=eq.' + enc(employeeId) + '&select=credential_id,transports'), { headers });
      // Deliberately generic on both "table not provisioned" and "employee
      // has no passkeys" -- an empty allowCredentials list still produces a
      // valid, well-formed options object (the browser will just report no
      // matching credential when the ceremony runs), so this never reveals
      // via a distinguishing error whether employeeId is a real employee.
      const existingRows = (existing.ok) ? await existing.json() : [];
      const allowCredentials = (existingRows || []).map((r) => ({ id: r.credential_id, transports: r.transports || undefined }));
      const options = await generateAuthenticationOptions({
        rpID: RP_ID,
        allowCredentials: allowCredentials.length ? allowCredentials : undefined,
        userVerification: 'preferred'
      });
      const challengeToken = signChallengeToken({ challenge: options.challenge, purpose: 'auth', employee_id: employeeId, license_hash: licHash, exp: Date.now() + CHALLENGE_TTL_MS });
      res.status(200).json({ ok: true, options, challengeToken });
      return;
    }

    if (action === 'auth-verify') {
      const employeeId = String((body.employee_id || '')).trim();
      if (!employeeId) { res.status(400).json({ error: { message: 'employee_id is required' } }); return; }
      const challengePayload = verifyChallengeToken(body.challengeToken, 'auth', employeeId, licHash);
      if (!challengePayload) { res.status(400).json({ error: { code: 'CHALLENGE_EXPIRED', message: 'Sign-in expired — try again' } }); return; }
      const credRow = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&employee_id=eq.' + enc(employeeId) + '&credential_id=eq.' + enc(body.response && body.response.id || '') + '&select=credential_id,public_key,counter,transports&limit=1'), { headers });
      if (!credRow.ok) { res.status(401).json({ error: { code: 'INVALID_CREDENTIALS', message: 'Unrecognized passkey' } }); return; }
      const credRows = await credRow.json();
      const stored = Array.isArray(credRows) && credRows[0];
      if (!stored) { res.status(401).json({ error: { code: 'INVALID_CREDENTIALS', message: 'Unrecognized passkey' } }); return; }
      let verification;
      try {
        verification = await verifyAuthenticationResponse({
          response: body.response,
          expectedChallenge: challengePayload.challenge,
          expectedOrigin: ORIGIN,
          expectedRPID: RP_ID,
          credential: {
            id: stored.credential_id,
            publicKey: new Uint8Array(Buffer.from(stored.public_key, 'base64')),
            counter: Number(stored.counter),
            transports: stored.transports || undefined
          }
        });
      } catch (err) {
        res.status(401).json({ error: { code: 'INVALID_CREDENTIALS', message: 'Could not verify passkey' } });
        return;
      }
      if (!verification.verified) { res.status(401).json({ error: { code: 'INVALID_CREDENTIALS', message: 'Could not verify passkey' } }); return; }
      // Clone-detection: verifyAuthenticationResponse already compares counter internally and
      // would have thrown/returned verified:false on a stale-or-lower counter when the stored
      // counter is nonzero -- persisting newCounter here is what makes that check meaningful on
      // the NEXT login, not this one.
      try {
        await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&credential_id=eq.' + enc(stored.credential_id)), {
          method: 'PATCH', headers, body: JSON.stringify({ counter: verification.authenticationInfo.newCounter, last_used_at: new Date().toISOString() })
        });
      } catch (e) { /* non-fatal -- login still succeeds, next login's clone-check just uses a stale counter */ }

      const authRow = await fetch(rest(AUTH_TABLE + '?license_hash=eq.' + enc(licHash) + '&employee_id=eq.' + enc(employeeId) + '&active=eq.true&select=employee_id,role&limit=1'), { headers });
      if (!authRow.ok) { res.status(401).json({ error: { code: 'INVALID_CREDENTIALS', message: 'This employee is no longer active' } }); return; }
      const authRows = await authRow.json();
      const authRecord = Array.isArray(authRows) && authRows[0];
      if (!authRecord) { res.status(401).json({ error: { code: 'INVALID_CREDENTIALS', message: 'This employee is no longer active' } }); return; }

      const token = signSessionToken({ employee_id: authRecord.employee_id, role: authRecord.role, license_hash: licHash, app: APP });
      res.status(200).json({ ok: true, token, role: authRecord.role, employee_id: authRecord.employee_id });
      return;
    }
  } catch (err) {
    console.error('api/sd-webauthn error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
};

function upstream(res, detail) {
  console.error('sd-webauthn upstream error:', detail);
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}
