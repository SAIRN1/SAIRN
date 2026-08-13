// api/law-auth.js
// ---------------------------------------------------------------------------
// SAIRNlaw per-employee login + MFA (TOTP) + SSO (OIDC) endpoint.
//
// Replaces sairnlaw.html's old client-only gate (DEFAULT_PINS = one shared
// PIN per role, in the page source, zero server involvement — every
// attorney shared one PIN, so nothing could ever be attributed to an
// individual and any role was self-assertable by editing the DOM). This is
// the server side of the real model: each employee has their own PIN,
// hashed server-side, checked against sairnlaw_employee_auth
// (sql/sairnlaw_employee_auth_schema.sql), optionally protected by a real
// RFC 6238 TOTP second factor, with an optional real OIDC SSO path.
//
// Modelled directly on api/sd-auth.js (StoneDesk's equivalent) — same
// license-bearer convention, same lockout design, same generic-error
// discipline. SAIRNlaw-specific additions are the mfa_* and sso_* actions
// and audit logging on every event.
//
// All actions are POST, license key via Authorization: Bearer.
//
//   check_license  {}
//     Confirms the key is real/active before the client stores it.
//
//   bootstrap      { employee_id, display_name, pin }
//     Only works when this license has ZERO rows yet. Creates the first
//     credential, always role 'owner'. 409 once any row exists — one-time
//     setup, not a standing backdoor.
//
//   login          { employee_id, pin }
//     -> { ok, token, role }                    (MFA not enabled)
//     -> { ok, mfa_required: true, preauth_token } (MFA enabled)
//     The pre-auth token is NOT a session token and is rejected by
//     verifySessionToken — see api/_lib/auth.js's typ-claim comment.
//
//   mfa_verify     { preauth_token, code }
//     Second step. Exchanges a valid pre-auth token + a real TOTP code for
//     a real session token.
//
//   mfa_setup      {}                      (session required)
//     Generates a real 160-bit TOTP secret, stores it ENCRYPTED with
//     mfa_enabled still false, returns the secret + otpauth:// URI for the
//     caller to show as a QR code. Enrolling is not enabling.
//
//   mfa_enable     { code }                (session required)
//     Verifies one real code against the stored secret, THEN flips
//     mfa_enabled. A secret that was never confirmed with a working code
//     never starts gating logins — that ordering is what stops an employee
//     locking themselves out with a mis-scanned QR code.
//
//   mfa_reset      { employee_id }         (owner session required)
//     Clears another employee's MFA enrollment. Exists because a lost
//     phone would otherwise be permanent, unrecoverable lockout. Audit-
//     logged like everything else; an owner cannot reset their own (see
//     the check at that action — an attacker who has an owner session
//     already has everything, but this keeps the log honest about who
//     reset whom).
//
//   setup          { employee_id, display_name, pin, role }  (owner session)
//     Provisions/updates another employee's credential.
//
//   sso_start      {}
//     -> { ok, authorization_url, state } or 503 NOT_CONFIGURED.
//
//   audit_read     { limit }                (owner session required)
//     Returns this firm's most recent audit-log rows for the security
//     panel, newest first. Read-only — there is no update or delete path
//     to this table anywhere in the codebase, by design.
//
//   sso_callback   { code, state }
//     Exchanges the authorization code, CRYPTOGRAPHICALLY VERIFIES the
//     id_token against the provider's JWKS (api/_lib/auth.js
//     oidcVerifyIdToken), and issues a session token — but only for an
//     employee record that ALREADY EXISTS for this license. SSO never
//     auto-creates accounts: doing so would grant SAIRNlaw access to
//     everyone in the firm's whole identity-provider tenant.
//
// AUDIT: every auth event here writes to sairnlaw_audit_log via
// api/_lib/audit.js. See that file and the schema header for the honest,
// deliberately-limited scope of what audit logging covers today.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SD_AUTH_SECRET.
// SSO additionally requires OIDC_ISSUER_URL, OIDC_CLIENT_ID,
// OIDC_CLIENT_SECRET, OIDC_REDIRECT_URI — absent those, sso_* actions
// return a clear 503 NOT_CONFIGURED, never a raw crash.
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const { writeAuditLog } = require('./_lib/audit');
const {
  hashPin, verifyPin, signSessionToken, verifySessionToken, tokenFromRequest,
  signPreAuthToken, verifyPreAuthToken,
  generateTotpSecret, verifyTotpCode, totpProvisioningUri,
  encryptSecret, decryptSecret,
  oidcConfigured, generatePkcePair, oidcDiscoverEndpoints, oidcAuthorizationUrl,
  oidcExchangeCode, oidcVerifyIdToken, signSsoState, verifySsoState,
  ROLES_BY_APP
} = require('./_lib/auth');
// AI Chain of Custody server-side capture (2026-08-13): callAnthropic() and
// the demo-limit helpers are imported directly from api/claude.js (an
// in-process function call, not a second HTTP round trip back through that
// endpoint), so this handler applies the SAME logic and limit -- same
// DEMO_DAILY_LIMIT, same getDemoKey() day-bucketing, same increment-then-
// compare shape -- as every other app's is_demo traffic. On Vercel each
// api/*.js file is its own serverless function/bundle, so demoCallCounts
// here is a separate in-memory object per instance, not literally shared
// with the real /api/claude endpoint's instances -- best-effort and
// per-instance, same documented limitation api/claude.js already has.
const { callAnthropic, getDemoKey, demoCallCounts, DEMO_DAILY_LIMIT } = require('./claude.js');

const APP = 'sairnlaw';
const TABLE = 'sairnlaw_employee_auth';
const LAW_ROLES = ROLES_BY_APP[APP];
const LOCKOUT_THRESHOLD = 5;
const LOCKOUT_MINUTES = 15;
const ACTIONS = [
  'check_license', 'bootstrap', 'login', 'setup',
  'mfa_setup', 'mfa_enable', 'mfa_verify', 'mfa_reset',
  'sso_start', 'sso_callback', 'audit_read',
  'ai_generate', 'ai_list', 'ai_review', 'ai_reject', 'ai_used_in_filing'
];
// AI Chain of Custody roles (2026-08-13): licensed attorneys, not
// paralegals, are the ones sanctioned for AI-generated fake citations --
// review/reject/filing-attestation are restricted accordingly. Any
// authenticated role may trigger an AI interaction (ai_generate) -- everyone's
// usage gets logged the same way, only the review/attestation actions are
// role-gated.
const AI_COC_REVIEW_ROLES = { owner: true, attorney: true };
const AI_PROMPT_RESPONSE_CAP = 20000;
// Separate, smaller cap for LIST-time preview length. AI_PROMPT_RESPONSE_CAP
// above governs what's stored at INSERT time (ai_generate); this one governs what
// ai_list returns per entry, so a listing of up to 1000 entries can't balloon
// to multi-megabyte responses and risk exceeding Vercel's response size limit.
const AI_LIST_PREVIEW_CAP = 500;

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
  body = body || {};
  const action = body.action;
  if (ACTIONS.indexOf(action) === -1) {
    res.status(400).json({ error: { message: 'action must be one of: ' + ACTIONS.join(', ') } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY || !process.env.SD_AUTH_SECRET) {
    console.error('law-auth: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  let lic;
  try {
    lic = await validateLicenseKey(licenseKey);
  } catch (err) {
    if (err.code === 'CONFIG') {
      res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
      return;
    }
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }
  if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }

  if (action === 'check_license') {
    res.status(200).json({ ok: true, active: true, app_id: lic.app_id || null, sso_available: oidcConfigured() });
    return;
  }

  const licHash = lic.license_hash;
  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };
  const rest = (path) => SUPABASE_URL + '/rest/v1/' + path;
  const enc = encodeURIComponent;
  const audit = (event_type, fields) => writeAuditLog(SUPABASE_URL, SERVICE_KEY,
    Object.assign({ license_hash: licHash, event_type }, fields || {}));

  // Loads one employee row, or null. Throws a tagged error if the table
  // itself is missing so the caller can answer 503 NOT_PROVISIONED instead
  // of a generic 500 that looks identical to a real outage.
  async function loadEmployee(employee_id, extraSelect) {
    const select = 'employee_id,role,pin_hash,pin_salt,failed_attempts,locked_until,mfa_enabled' + (extraSelect ? (',' + extraSelect) : '');
    const r = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&employee_id=eq.' + enc(employee_id) +
      '&active=eq.true&select=' + select + '&limit=1'), { headers });
    const rows = await r.json();
    if (!r.ok) { const e = new Error('lookup failed'); e.detail = rows; e.notProvisioned = isMissingTable(rows); throw e; }
    return (Array.isArray(rows) && rows[0]) || null;
  }

  async function patchEmployee(employee_id, patch) {
    return fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&employee_id=eq.' + enc(employee_id)), {
      method: 'PATCH', headers, body: JSON.stringify(Object.assign({ updated_at: new Date().toISOString() }, patch))
    });
  }

  // Shared failure bookkeeping for both PIN and TOTP misses — a 6-digit
  // TOTP code with a ±1-step acceptance window is brute-forceable at high
  // request rates without this, so MFA failures count toward the same
  // lockout as PIN failures rather than being unthrottled.
  async function recordFailure(row) {
    if (!row) return false;
    const attempts = (row.failed_attempts || 0) + 1;
    const locked = attempts >= LOCKOUT_THRESHOLD;
    try {
      await patchEmployee(row.employee_id, locked
        ? { failed_attempts: 0, locked_until: new Date(Date.now() + LOCKOUT_MINUTES * 60000).toISOString() }
        : { failed_attempts: attempts });
    } catch (e) { /* non-fatal — the attempt is refused either way */ }
    return locked;
  }

  async function clearFailures(row) {
    if (!row || (!row.failed_attempts && !row.locked_until)) return;
    try { await patchEmployee(row.employee_id, { failed_attempts: 0, locked_until: null }); } catch (e) { /* non-fatal */ }
  }

  function isLocked(row) {
    return !!(row && row.locked_until && new Date(row.locked_until).getTime() > Date.now());
  }

  try {
    if (action === 'bootstrap') {
      const employee_id = String(body.employee_id || '').trim();
      const pin = String(body.pin || '').trim();
      if (!employee_id || employee_id.length > 128 || !/^\d{6,8}$/.test(pin)) {
        res.status(400).json({ error: { message: 'employee_id (max 128 chars) and a 6-8 digit pin are required' } });
        return;
      }
      if (body.display_name && String(body.display_name).length > 128) {
        res.status(400).json({ error: { message: 'display_name max 128 chars' } });
        return;
      }
      const existing = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&select=id&limit=1'), { headers });
      const existingRows = await existing.json();
      if (!existing.ok) return upstream(res, existingRows);
      if (Array.isArray(existingRows) && existingRows.length > 0) {
        res.status(409).json({ error: { code: 'ALREADY_PROVISIONED', message: 'This firm already has employee credentials set up — use action:setup instead' } });
        return;
      }
      const { pin_hash, pin_salt } = hashPin(pin);
      const r = await fetch(rest(TABLE), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, employee_id, display_name: body.display_name || employee_id,
          role: 'owner', pin_hash, pin_salt, active: true
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      await audit('pin_bootstrap', { employee_id, role: 'owner' });
      const token = signSessionToken({ employee_id, role: 'owner', license_hash: licHash, app: APP });
      res.status(200).json({ ok: true, token, role: 'owner', employee_id, mfa_enabled: false });
      return;
    }

    if (action === 'login') {
      const employee_id = String(body.employee_id || '').trim();
      const pin = String(body.pin || '').trim();
      if (!employee_id || !pin) {
        res.status(400).json({ error: { message: 'employee_id and pin are required' } });
        return;
      }
      const row = await loadEmployee(employee_id);

      if (isLocked(row)) {
        await audit('lockout', { employee_id, role: row.role, detail: { stage: 'pin' } });
        res.status(429).json({ error: { code: 'LOCKED', message: 'Too many failed attempts — try again later' } });
        return;
      }

      // verifyPin runs at equal cost whether the row exists or not (see
      // api/_lib/auth.js DUMMY_SALT_FOR_TIMING) — no early return on a
      // missing row, so employee_id existence can't be timed.
      const pinOk = row ? verifyPin(pin, row.pin_hash, row.pin_salt) : verifyPin(pin, null, null);
      if (!pinOk) {
        const locked = await recordFailure(row);
        await audit(locked ? 'lockout' : 'login_failed', { employee_id, role: row ? row.role : null, detail: { stage: 'pin' } });
        res.status(401).json({ error: { code: 'INVALID_CREDENTIALS', message: 'Incorrect employee ID or PIN' } });
        return;
      }
      await clearFailures(row);

      if (row.mfa_enabled) {
        // PIN was right, but this is NOT a session yet. The pre-auth token
        // says only "PIN verified for this employee", expires in 5 minutes,
        // and is refused by verifySessionToken.
        const preauth_token = signPreAuthToken({ app: APP, employee_id: row.employee_id, role: row.role, license_hash: licHash });
        res.status(200).json({ ok: true, mfa_required: true, preauth_token, employee_id: row.employee_id });
        return;
      }

      await audit('login_success', { employee_id: row.employee_id, role: row.role, detail: { method: 'pin', mfa: false } });
      const token = signSessionToken({ employee_id: row.employee_id, role: row.role, license_hash: licHash, app: APP });
      res.status(200).json({ ok: true, token, role: row.role, employee_id: row.employee_id, mfa_enabled: false });
      return;
    }

    if (action === 'mfa_verify') {
      const pre = verifyPreAuthToken(body.preauth_token, licHash, APP);
      if (!pre) {
        res.status(401).json({ error: { code: 'PREAUTH_INVALID', message: 'Login step expired — start again' } });
        return;
      }
      const row = await loadEmployee(pre.employee_id, 'mfa_secret_encrypted');
      if (!row || !row.mfa_enabled || !row.mfa_secret_encrypted) {
        res.status(401).json({ error: { code: 'MFA_NOT_ENABLED', message: 'Login step expired — start again' } });
        return;
      }
      if (isLocked(row)) {
        await audit('lockout', { employee_id: row.employee_id, role: row.role, detail: { stage: 'mfa' } });
        res.status(429).json({ error: { code: 'LOCKED', message: 'Too many failed attempts — try again later' } });
        return;
      }
      const secret = decryptSecret(row.mfa_secret_encrypted);
      if (!secret) {
        // Decrypt failure means the stored ciphertext can't be read with the
        // current key (tampered, or SD_AUTH_SECRET was rotated). Fail closed
        // and say so in the log — never fall back to skipping MFA.
        console.error('law-auth: mfa secret decrypt failed for', row.employee_id);
        await audit('mfa_failed', { employee_id: row.employee_id, role: row.role, detail: { reason: 'secret_undecryptable' } });
        res.status(500).json({ error: { code: 'MFA_UNAVAILABLE', message: 'Two-factor verification is unavailable — contact your firm administrator' } });
        return;
      }
      if (!verifyTotpCode(secret, body.code)) {
        const locked = await recordFailure(row);
        await audit(locked ? 'lockout' : 'mfa_failed', { employee_id: row.employee_id, role: row.role, detail: { stage: 'mfa' } });
        res.status(401).json({ error: { code: 'MFA_INVALID', message: 'Incorrect authentication code' } });
        return;
      }
      await clearFailures(row);
      await audit('mfa_verified', { employee_id: row.employee_id, role: row.role });
      await audit('login_success', { employee_id: row.employee_id, role: row.role, detail: { method: 'pin', mfa: true } });
      const token = signSessionToken({ employee_id: row.employee_id, role: row.role, license_hash: licHash, app: APP });
      res.status(200).json({ ok: true, token, role: row.role, employee_id: row.employee_id, mfa_enabled: true });
      return;
    }

    if (action === 'mfa_setup') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      // SECURITY (found 2026-08-08 by real live testing, not code review):
      // this action writes mfa_enabled:false alongside the new secret, so
      // calling it on an ALREADY-ENROLLED account silently switched two-
      // factor OFF. Anyone holding a stolen session token could therefore
      // disable MFA without presenting a single code -- defeating the exact
      // protection MFA exists to provide, and contradicting the security
      // panel's own statement that only an Owner can turn it off. Re-
      // enrollment now requires an Owner reset (action:mfa_reset), which is
      // audit-logged and attributable to a person.
      const existing = await loadEmployee(caller.employee_id);
      if (existing && existing.mfa_enabled) {
        res.status(409).json({ error: { code: 'MFA_ALREADY_ENABLED', message: 'Two-factor is already on for this account. An Owner must reset it before it can be set up again.' } });
        return;
      }
      const secret = generateTotpSecret();
      const r = await patchEmployee(caller.employee_id, { mfa_secret_encrypted: encryptSecret(secret), mfa_enabled: false });
      if (!r.ok) return upstream(res, await r.json());
      res.status(200).json({
        ok: true,
        secret,
        otpauth_uri: totpProvisioningUri(secret, caller.employee_id, 'SAIRNlaw'),
        note: 'Scan this in an authenticator app, then confirm one code to turn two-factor on.'
      });
      return;
    }

    if (action === 'mfa_enable') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const row = await loadEmployee(caller.employee_id, 'mfa_secret_encrypted');
      if (!row || !row.mfa_secret_encrypted) {
        res.status(409).json({ error: { code: 'NO_ENROLLMENT', message: 'Start two-factor setup first' } });
        return;
      }
      const secret = decryptSecret(row.mfa_secret_encrypted);
      if (!secret || !verifyTotpCode(secret, body.code)) {
        await audit('mfa_failed', { employee_id: caller.employee_id, role: caller.role, detail: { stage: 'enrollment' } });
        res.status(401).json({ error: { code: 'MFA_INVALID', message: 'That code did not match — check your authenticator app and try again' } });
        return;
      }
      const r = await patchEmployee(caller.employee_id, { mfa_enabled: true });
      if (!r.ok) return upstream(res, await r.json());
      await audit('mfa_enrolled', { employee_id: caller.employee_id, role: caller.role });
      res.status(200).json({ ok: true, mfa_enabled: true });
      return;
    }

    if (action === 'mfa_reset') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || caller.role !== 'owner') {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner can reset two-factor for an employee' } });
        return;
      }
      const target = String(body.employee_id || '').trim();
      if (!target) { res.status(400).json({ error: { message: 'employee_id is required' } }); return; }
      const r = await patchEmployee(target, { mfa_enabled: false, mfa_secret_encrypted: null });
      if (!r.ok) return upstream(res, await r.json());
      await audit('mfa_enrolled', { employee_id: target, role: null, detail: { reset_by: caller.employee_id, enabled: false } });
      res.status(200).json({ ok: true, employee_id: target, mfa_enabled: false });
      return;
    }

    if (action === 'setup') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      // expectedApp:APP matters — without it a valid StoneDesk/SAIRNbiz
      // owner token ('owner' exists in every app's role list) would pass
      // this check and be able to provision SAIRNlaw credentials.
      if (!caller || caller.role !== 'owner') {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner can provision employee credentials' } });
        return;
      }
      const employee_id = String(body.employee_id || '').trim();
      const pin = String(body.pin || '').trim();
      const role = body.role;
      if (!employee_id || employee_id.length > 128 || !/^\d{6,8}$/.test(pin) || LAW_ROLES.indexOf(role) === -1) {
        res.status(400).json({ error: { message: 'employee_id (max 128 chars), a 6-8 digit pin, and a valid role (' + LAW_ROLES.join('|') + ') are required' } });
        return;
      }
      if (body.display_name && String(body.display_name).length > 128) {
        res.status(400).json({ error: { message: 'display_name max 128 chars' } });
        return;
      }
      const { pin_hash, pin_salt } = hashPin(pin);
      const r = await fetch(rest(TABLE + '?on_conflict=license_hash,employee_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, employee_id, display_name: body.display_name || employee_id,
          role, pin_hash, pin_salt, active: true, updated_at: new Date().toISOString()
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      await audit('pin_setup', { employee_id, role, detail: { by: caller.employee_id } });
      res.status(200).json({ ok: true, employee_id, role });
      return;
    }

    if (action === 'audit_read') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || caller.role !== 'owner') {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner can view the security audit log' } });
        return;
      }
      const limit = Math.min(Math.max(parseInt(body.limit, 10) || 100, 1), 500);
      const r = await fetch(rest('sairnlaw_audit_log?license_hash=eq.' + enc(licHash) +
        '&event_type=not.in.(ai_interaction,ai_reviewed,ai_rejected,ai_used_in_filing)' +
        '&select=id,employee_id,role,event_type,detail,created_at&order=created_at.desc&limit=' + limit), { headers });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({
        ok: true,
        entries: rows || [],
        // Honest scope, returned with the data itself so a UI can't display
        // the log as if it covered more than it does. See
        // sql/sairnlaw_audit_log_schema.sql for the full reasoning.
        coverage: {
          // AI interactions (2026-08-13) are tracked in this same table but
          // deliberately NOT included in this general endpoint's own
          // results (see ai_list below) -- their detail payload carries
          // real prompt/response text, which may contain privileged client
          // matter content, and does not belong in this page's generic
          // JSON.stringify(detail) rendering. Disclosed here so this page
          // stays honest about the fact that coverage without implying
          // this view shows it.
          covered: ['authentication events', 'two-factor enrollment and verification', 'single sign-on', 'credential provisioning', 'citator research lookups', 'AI interactions (see AI Chain of Custody, not shown on this page)'],
          not_covered: ['trust/IOLTA transactions', 'document access', 'matter changes'],
          not_covered_reason: 'Those features store their data in the browser only and never reach the server, so the server cannot observe or attest to them. Server-side auditing of those actions requires them to become server-backed first — a separate, real piece of work that has not been done.'
        }
      });
      return;
    }

    // ── AI CHAIN OF CUSTODY -- SERVER-SIDE CAPTURE (2026-08-13) ─────────
    // Replaces ai_log. The old design let the client submit an arbitrary
    // prompt/response pair as a SEPARATE, unlinked request after the AI
    // answer had already rendered -- a real capture gap (the second
    // request might never fire) and a real fabrication gap (nothing tied
    // a logged pair to a real Claude call). This action calls Claude
    // itself and writes the log entry from the REAL response it just
    // received, BEFORE the client ever sees that text -- a response
    // literally cannot reach the rep without a genuine log entry already
    // existing. See docs/superpowers/specs/2026-08-13-sairnlaw-ai-chain-of-
    // custody-server-side-capture-design.md.
    if (action === 'ai_generate') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in required' } }); return; }
      const messages = Array.isArray(body.messages) ? body.messages : null;
      if (!messages || !messages.length) { res.status(400).json({ error: { message: 'messages array is required' } }); return; }

      // Same is_demo daily-cap logic api/claude.js's own HTTP handler applies
      // to every other app -- same DEMO_DAILY_LIMIT, same getDemoKey()
      // day-bucketing, applied per-instance like everywhere else (see the
      // import comment above), preserved rather than silently dropped here.
      const key = getDemoKey('sairnlaw');
      demoCallCounts[key] = (demoCallCounts[key] || 0) + 1;
      if (demoCallCounts[key] > DEMO_DAILY_LIMIT) {
        res.status(200).json({ error: 'demo_limit' });
        return;
      }

      const result = await callAnthropic({ system: body.system, messages: messages, max_tokens: body.max_tokens, tools: body.tools });
      if (!result.ok) {
        res.status(result.status).json({ error: result.error });
        return;
      }

      const blocks = (result.data && result.data.content) || [];
      const toolUse = blocks.filter(function (b) { return b.type === 'tool_use'; })[0];
      if (toolUse) {
        // Intermediate tool-use directive -- nothing user-facing yet, so
        // there is nothing real to log. The client executes the tool
        // locally (unchanged; tool data is law_* localStorage, not
        // server-accessible) and calls this same action again with the
        // tool result appended to `messages` for the second, final leg.
        res.status(200).json(Object.assign({ok:true}, result.data));
        return;
      }

      // Final text -- the only case a rep ever actually sees output.
      const responseText = (blocks[0] && blocks[0].text) || '';
      // Derive the logged prompt from the REAL messages array rather than
      // trusting body.prompt_for_log outright -- a client could otherwise
      // send a genuine question in `messages` (what Claude actually saw)
      // and a different prompt_for_log (what gets logged). Fall back to
      // prompt_for_log only for the one shape where the last user turn
      // isn't plain text: sendAI()'s second leg, whose last user message
      // is a tool_result content-block array, not a string.
      const lastUser = messages.filter(function (m) { return m && m.role === 'user'; }).pop();
      const derivedPrompt = (lastUser && typeof lastUser.content === 'string') ? lastUser.content : null;
      const prompt = String(derivedPrompt || body.prompt_for_log || '').slice(0, AI_PROMPT_RESPONSE_CAP);
      if (!prompt) { res.status(400).json({ error: { message: 'Could not establish a prompt to log — request rejected' } }); return; }
      const response = responseText.slice(0, AI_PROMPT_RESPONSE_CAP);
      const matter_id = body.matter_id ? String(body.matter_id) : 'general';
      // Derive tools_used from the REAL messages array rather than trusting
      // body.tools_used -- on the final leg of a tool-use exchange, the
      // assistant turn that requested the tool is right there in `messages`
      // with a real tool_use block and real name, so there is no reason to
      // trust client-asserted metadata about which tools were actually used.
      var toolsUsedSet = {};
      messages.forEach(function (m) {
        if (m && m.role === 'assistant' && Array.isArray(m.content)) {
          m.content.forEach(function (b) { if (b && b.type === 'tool_use' && b.name) { toolsUsedSet[String(b.name)] = true; } });
        }
      });
      const tools_used = Object.keys(toolsUsedSet);
      const logged = await audit('ai_interaction', { employee_id: caller.employee_id, role: caller.role, detail: { prompt, response, matter_id, tools_used } });
      if (!logged) {
        res.status(502).json({ error: { code: 'LOG_WRITE_FAILED', message: 'Could not write to the AI Chain of Custody log — the AI response was generated but is being withheld until this is logged. Try again.' } });
        return;
      }
      res.status(200).json(Object.assign({ok:true}, result.data));
      return;
    }

    if (action === 'ai_list') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || !AI_COC_REVIEW_ROLES[caller.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner or Attorney can view the AI Chain of Custody log' } });
        return;
      }
      const limit = Math.min(Math.max(parseInt(body.limit, 10) || 200, 1), 1000);
      const r = await fetch(rest('sairnlaw_audit_log?license_hash=eq.' + enc(licHash) +
        '&event_type=in.(ai_interaction,ai_reviewed,ai_rejected,ai_used_in_filing)' +
        '&select=id,employee_id,role,event_type,detail,created_at&order=created_at.desc&limit=' + limit), { headers });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const all = rows || [];
      const interactions = all.filter(function (e) { return e.event_type === 'ai_interaction'; });
      const statusEvents = all.filter(function (e) { return e.event_type !== 'ai_interaction'; });
      // Most recent status event per log_entry_id wins -- statusEvents is
      // already ordered newest-first (order=created_at.desc above), so the
      // FIRST match found per id in this loop is the current status.
      const statusById = {};
      statusEvents.forEach(function (e) {
        var lid = e.detail && e.detail.log_entry_id;
        if (lid && !statusById[lid]) statusById[lid] = e;
      });
      const truncPreview = function (s) {
        s = s || '';
        return s.length > AI_LIST_PREVIEW_CAP ? (s.slice(0, AI_LIST_PREVIEW_CAP) + '…') : s;
      };
      const entries = interactions.map(function (e) {
        var statusEvent = statusById[e.id];
        var status = 'unreviewed';
        if (statusEvent) {
          if (statusEvent.event_type === 'ai_reviewed') status = 'reviewed';
          else if (statusEvent.event_type === 'ai_rejected') status = 'rejected';
          else if (statusEvent.event_type === 'ai_used_in_filing') status = 'used_in_filing';
        }
        var fullPrompt = (e.detail && e.detail.prompt) || '';
        var fullResponse = (e.detail && e.detail.response) || '';
        return {
          id: e.id, employee_id: e.employee_id, role: e.role, created_at: e.created_at,
          matter_id: e.detail && e.detail.matter_id, prompt: truncPreview(fullPrompt),
          prompt_truncated: fullPrompt.length > AI_LIST_PREVIEW_CAP,
          response: truncPreview(fullResponse),
          response_truncated: fullResponse.length > AI_LIST_PREVIEW_CAP,
          tools_used: (e.detail && e.detail.tools_used) || [],
          status: status,
          reject_reason: (statusEvent && statusEvent.event_type === 'ai_rejected' && statusEvent.detail) ? statusEvent.detail.reason : null,
          reviewed_by: statusEvent ? statusEvent.employee_id : null,
          reviewed_at: statusEvent ? statusEvent.created_at : null
        };
      });
      res.status(200).json({
        ok: true,
        entries: entries,
        // Honest coverage/scope disclosure alongside the data itself, same
        // precedent as audit_read's `coverage` field above — the UI can't
        // imply this listing is complete or untruncated when it isn't.
        note: 'Showing the ' + entries.length + ' most recent AI Chain of Custody events for this license.'
      });
      return;
    }

    // Re-derives one entry's current status server-side -- never trusts the
    // client's belief about it. Returns { interactionExists, status } —
    // status is 'unreviewed'/'reviewed'/'rejected'/'used_in_filing', same
    // rule as ai_list above, just scoped to a single log_entry_id instead
    // of a full-license listing.
    async function aiCurrentStatus(logEntryId) {
      const interactionR = await fetch(rest('sairnlaw_audit_log?license_hash=eq.' + enc(licHash) +
        '&id=eq.' + enc(logEntryId) + '&event_type=eq.ai_interaction&select=id&limit=1'), { headers });
      const interactionRows = await interactionR.json();
      if (!interactionR.ok) { const e = new Error('lookup failed'); e.detail = interactionRows; throw e; }
      if (!Array.isArray(interactionRows) || !interactionRows.length) return { interactionExists: false, status: null };
      const eventsR = await fetch(rest('sairnlaw_audit_log?license_hash=eq.' + enc(licHash) +
        '&event_type=in.(ai_reviewed,ai_rejected,ai_used_in_filing)&detail->>log_entry_id=eq.' + enc(logEntryId) +
        '&select=event_type,detail,created_at&order=created_at.desc&limit=1'), { headers });
      const events = await eventsR.json();
      if (!eventsR.ok) { const e = new Error('lookup failed'); e.detail = events; throw e; }
      if (!Array.isArray(events) || !events.length) return { interactionExists: true, status: 'unreviewed' };
      const match = events[0];
      const status = match.event_type === 'ai_reviewed' ? 'reviewed' : (match.event_type === 'ai_rejected' ? 'rejected' : 'used_in_filing');
      return { interactionExists: true, status: status };
    }

    if (action === 'ai_review') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || !AI_COC_REVIEW_ROLES[caller.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner or Attorney can review AI Chain of Custody entries' } });
        return;
      }
      const logEntryId = body.log_entry_id ? String(body.log_entry_id) : null;
      if (!logEntryId) { res.status(400).json({ error: { message: 'log_entry_id is required' } }); return; }
      let current;
      try { current = await aiCurrentStatus(logEntryId); } catch (e) { return upstream(res, e.detail); }
      if (!current.interactionExists) { res.status(404).json({ error: { code: 'NOT_FOUND', message: 'No such AI interaction' } }); return; }
      if (current.status !== 'unreviewed') { res.status(409).json({ error: { code: 'ALREADY_REVIEWED', message: 'This entry is already ' + current.status } }); return; }
      const logged = await audit('ai_reviewed', { employee_id: caller.employee_id, role: caller.role, detail: { log_entry_id: logEntryId } });
      if (!logged) {
        res.status(502).json({ error: { code: 'LOG_WRITE_FAILED', message: 'Could not write to the AI Chain of Custody log — try again' } });
        return;
      }
      res.status(200).json({ ok: true });
      return;
    }

    if (action === 'ai_reject') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || !AI_COC_REVIEW_ROLES[caller.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner or Attorney can review AI Chain of Custody entries' } });
        return;
      }
      const logEntryId = body.log_entry_id ? String(body.log_entry_id) : null;
      const reason = String(body.reason || '').trim().slice(0, 2000);
      if (!logEntryId) { res.status(400).json({ error: { message: 'log_entry_id is required' } }); return; }
      if (!reason) { res.status(400).json({ error: { message: 'A reason is required to reject an AI interaction' } }); return; }
      let current;
      try { current = await aiCurrentStatus(logEntryId); } catch (e) { return upstream(res, e.detail); }
      if (!current.interactionExists) { res.status(404).json({ error: { code: 'NOT_FOUND', message: 'No such AI interaction' } }); return; }
      if (current.status !== 'unreviewed') { res.status(409).json({ error: { code: 'ALREADY_REVIEWED', message: 'This entry is already ' + current.status } }); return; }
      const logged = await audit('ai_rejected', { employee_id: caller.employee_id, role: caller.role, detail: { log_entry_id: logEntryId, reason: reason } });
      if (!logged) {
        res.status(502).json({ error: { code: 'LOG_WRITE_FAILED', message: 'Could not write to the AI Chain of Custody log — try again' } });
        return;
      }
      res.status(200).json({ ok: true });
      return;
    }

    if (action === 'ai_used_in_filing') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || !AI_COC_REVIEW_ROLES[caller.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner or Attorney can attest to AI Chain of Custody entries' } });
        return;
      }
      const logEntryId = body.log_entry_id ? String(body.log_entry_id) : null;
      if (!logEntryId) { res.status(400).json({ error: { message: 'log_entry_id is required' } }); return; }
      let current;
      try { current = await aiCurrentStatus(logEntryId); } catch (e) { return upstream(res, e.detail); }
      if (!current.interactionExists) { res.status(404).json({ error: { code: 'NOT_FOUND', message: 'No such AI interaction' } }); return; }
      if (current.status === 'used_in_filing') { res.status(409).json({ error: { code: 'ALREADY_USED', message: 'This entry has already been marked used in filing' } }); return; }
      if (current.status !== 'reviewed') { res.status(409).json({ error: { code: 'NOT_REVIEWED', message: 'This entry must be reviewed and approved before it can be marked used in a filing' } }); return; }
      const logged = await audit('ai_used_in_filing', { employee_id: caller.employee_id, role: caller.role, detail: { log_entry_id: logEntryId } });
      if (!logged) {
        res.status(502).json({ error: { code: 'LOG_WRITE_FAILED', message: 'Could not write to the AI Chain of Custody log — try again' } });
        return;
      }
      res.status(200).json({ ok: true });
      return;
    }

    if (action === 'sso_start') {
      if (!oidcConfigured()) {
        res.status(503).json({ error: { code: 'NOT_CONFIGURED', message: 'Single sign-on is not set up for this deployment — your firm administrator must register SAIRNlaw with your identity provider first.' } });
        return;
      }
      const endpoints = await oidcDiscoverEndpoints();
      const { verifier, challenge } = generatePkcePair();
      const state = signSsoState({ app: APP, license_hash: licHash, code_verifier: verifier });
      res.status(200).json({ ok: true, authorization_url: oidcAuthorizationUrl(endpoints, state, challenge), state });
      return;
    }

    if (action === 'sso_callback') {
      if (!oidcConfigured()) {
        res.status(503).json({ error: { code: 'NOT_CONFIGURED', message: 'Single sign-on is not set up for this deployment' } });
        return;
      }
      const st = verifySsoState(body.state, APP);
      if (!st || st.license_hash !== licHash) {
        res.status(401).json({ error: { code: 'STATE_INVALID', message: 'Sign-in link expired — start again' } });
        return;
      }
      const endpoints = await oidcDiscoverEndpoints();
      const tokens = await oidcExchangeCode(endpoints, String(body.code || ''), st.code_verifier);
      const claims = await oidcVerifyIdToken(endpoints, tokens.id_token);
      const sub = claims && claims.sub;
      const email = claims && claims.email ? String(claims.email).trim().toLowerCase() : null;
      if (!sub) {
        res.status(502).json({ error: { code: 'SSO_NO_SUBJECT', message: 'Identity provider returned no subject claim' } });
        return;
      }

      // Match an EXISTING employee: by previously-linked sso_subject first,
      // then by employee_id equal to the verified email claim. Never
      // auto-create — see this file's header.
      let row = null;
      const bySub = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&sso_subject=eq.' + enc(sub) +
        '&active=eq.true&select=employee_id,role,mfa_enabled&limit=1'), { headers });
      const subRows = await bySub.json();
      if (!bySub.ok) return upstream(res, subRows);
      row = (Array.isArray(subRows) && subRows[0]) || null;

      let linked = false;
      if (!row && email) {
        row = await loadEmployee(email);
        if (row) {
          const link = await patchEmployee(row.employee_id, { sso_subject: sub });
          if (link.ok) linked = true;
        }
      }
      if (!row) {
        await audit('sso_login', { employee_id: email, role: null, detail: { result: 'no_matching_employee', sub_present: true } });
        res.status(403).json({ error: { code: 'NO_MATCHING_EMPLOYEE', message: 'No SAIRNlaw account is linked to that identity — your firm administrator must create it first.' } });
        return;
      }
      if (linked) await audit('sso_link', { employee_id: row.employee_id, role: row.role });
      await audit('sso_login', { employee_id: row.employee_id, role: row.role, detail: { result: 'success' } });
      await audit('login_success', { employee_id: row.employee_id, role: row.role, detail: { method: 'sso' } });
      const token = signSessionToken({ employee_id: row.employee_id, role: row.role, license_hash: licHash, app: APP });
      res.status(200).json({ ok: true, token, role: row.role, employee_id: row.employee_id, mfa_enabled: !!row.mfa_enabled });
      return;
    }
  } catch (err) {
    if (err && err.notProvisioned) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw employee accounts are not set up yet — run sql/sairnlaw_employee_auth_schema.sql' } });
      return;
    }
    if (err && err.code === 'NOT_CONFIGURED') {
      res.status(503).json({ error: { code: 'NOT_CONFIGURED', message: 'Single sign-on is not set up for this deployment' } });
      return;
    }
    console.error('api/law-auth error:', err);
    res.status(err && err.status === 401 ? 401 : 502).json({
      error: { message: err && err.status === 401 ? 'Single sign-on verification failed' : 'Upstream connection error — try again' }
    });
  }
};

// PostgREST answers a missing table with a specific code rather than a
// network error — distinguishing it lets the caller say "run the migration"
// instead of "upstream error", which is the difference between a 5-second
// fix and an hour of guessing.
function isMissingTable(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('PGRST205') !== -1 || s.indexOf('does not exist') !== -1;
}

// A table that EXISTS but has no service_role grant fails with Postgres
// 42501, not a missing-table code — so the check above doesn't catch it and
// it fell through to a generic 502. That happened for real on the first
// live call after these tables were created (2026-08-08): the migration had
// been run correctly, but Supabase's default privileges hadn't applied, and
// the response said nothing useful. Detected separately now so the message
// names the actual fix.
function isPermissionDenied(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('42501') !== -1 || s.indexOf('permission denied') !== -1;
}

function upstream(res, detail) {
  console.error('law-auth upstream error:', detail);
  if (isMissingTable(detail)) {
    res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw employee accounts are not set up yet — run sql/sairnlaw_employee_auth_schema.sql' } });
    return;
  }
  if (isPermissionDenied(detail)) {
    res.status(503).json({ error: { code: 'NOT_GRANTED', message: 'The SAIRNlaw tables exist but the server role lacks privileges on them — re-run the GRANT block at the end of sql/sairnlaw_employee_auth_schema.sql' } });
    return;
  }
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}
