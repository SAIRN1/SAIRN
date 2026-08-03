// api/sd-auth.js
// ---------------------------------------------------------------------------
// StoneDesk per-employee login/credential-provisioning endpoint.
//
// Replaces the old client-only auth-gate (role pill + one shared PIN per
// role, DEFAULT_PINS visible in the page source, zero server involvement).
// This is the server side of the new model: each employee has their own
// PIN, hashed server-side, checked against sd_employee_auth (see
// sql/sd_employee_auth_schema.sql). A successful login returns a signed
// session token (api/_lib/auth.js) that other endpoints — currently
// api/sd-data.js's employees resource — verify before returning data.
//
// Three actions, all POST, license key via Authorization: Bearer (same
// convention as api/sd-data.js):
//
//   action: 'bootstrap'  { employee_id, display_name, pin }
//     Only works when this license has ZERO sd_employee_auth rows yet.
//     Creates the first credential, always role 'owner'. Refused with 409
//     once any row exists — this is a one-time setup step, not a standing
//     backdoor.
//
//   action: 'login'      { employee_id, pin }
//     Verifies pin against the stored hash, returns a session token +role
//     on success. No lockout/rate-limit here yet (matches sd-data.js's own
//     honest scope) — worth adding before wide exposure, same note as that
//     file's Authorization-bearer trust model.
//
//   action: 'setup'      { employee_id, display_name, pin, role }
//     Provisions or updates ANOTHER employee's credential. Requires a valid
//     session token (X-SD-Auth header) belonging to an owner or admin —
//     Sales/Install cannot self-serve, matching real shop practice (a
//     Technician doesn't hand out their own StoneDesk access role).
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SD_AUTH_SECRET
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const { hashPin, verifyPin, signSessionToken, verifySessionToken, tokenFromRequest, ROLES } = require('./_lib/auth');

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
  if (['bootstrap', 'login', 'setup'].indexOf(action) === -1) {
    res.status(400).json({ error: { message: "action must be 'bootstrap', 'login', or 'setup'" } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY || !process.env.SD_AUTH_SECRET) {
    console.error('sd-auth: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
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

  const licHash = lic.license_hash;
  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };
  const rest = (path) => SUPABASE_URL + '/rest/v1/' + path;
  const enc = encodeURIComponent;

  try {
    if (action === 'bootstrap') {
      const employee_id = String((body.employee_id || '')).trim();
      const pin = String((body.pin || '')).trim();
      // Minimum bumped 4->6 digits (security-auditor finding): a 4-digit PIN
      // is only 10,000 combinations, guessable fast against a live endpoint
      // even with the lockout added below. Length cap on employee_id/
      // display_name is a light storage-bloat guard, not an injection
      // control (everything here is a JSON body -> PostgREST, never
      // string-concatenated into SQL).
      if (!employee_id || employee_id.length > 128 || !/^\d{6,8}$/.test(pin)) {
        res.status(400).json({ error: { message: 'employee_id (max 128 chars) and a 6-8 digit pin are required' } });
        return;
      }
      if (body.display_name && String(body.display_name).length > 128) {
        res.status(400).json({ error: { message: 'display_name max 128 chars' } });
        return;
      }
      // Refuse unless this license truly has zero credentials yet.
      const existing = await fetch(rest('sd_employee_auth?license_hash=eq.' + enc(licHash) + '&select=id&limit=1'), { headers });
      const existingRows = await existing.json();
      if (!existing.ok) { return upstream(res, existingRows); }
      if (Array.isArray(existingRows) && existingRows.length > 0) {
        res.status(409).json({ error: { code: 'ALREADY_PROVISIONED', message: 'This license already has employee credentials set up — use action:setup instead' } });
        return;
      }
      const { pin_hash, pin_salt } = hashPin(pin);
      const r = await fetch(rest('sd_employee_auth'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, employee_id, display_name: body.display_name || employee_id,
          role: 'owner', pin_hash, pin_salt, active: true
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const token = signSessionToken({ employee_id, role: 'owner', license_hash: licHash });
      res.status(200).json({ ok: true, token, role: 'owner', employee_id });
      return;
    }

    if (action === 'login') {
      const employee_id = String((body.employee_id || '')).trim();
      const pin = String((body.pin || '')).trim();
      if (!employee_id || !pin) {
        res.status(400).json({ error: { message: 'employee_id and pin are required' } });
        return;
      }
      const r = await fetch(rest(
        'sd_employee_auth?license_hash=eq.' + enc(licHash) + '&employee_id=eq.' + enc(employee_id) +
        '&active=eq.true&select=employee_id,role,pin_hash,pin_salt,failed_attempts,locked_until&limit=1'), { headers });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const row = Array.isArray(rows) && rows[0];

      // LOCKOUT (security-auditor finding: PIN brute-force had zero
      // throttling — a 4-digit PIN was guessable in <10k requests against a
      // live endpoint regardless of hashing). Checked before the PIN
      // comparison so a locked account never even reaches verifyPin.
      if (row && row.locked_until && new Date(row.locked_until).getTime() > Date.now()) {
        res.status(429).json({ error: { code: 'LOCKED', message: 'Too many failed attempts — try again later' } });
        return;
      }

      // verifyPin always runs at equal cost whether row exists or not (see
      // api/_lib/auth.js DUMMY_SALT_FOR_TIMING) — no early-return here on
      // missing row, so employee_id existence can't be timed.
      const pinOk = row ? verifyPin(pin, row.pin_hash, row.pin_salt) : verifyPin(pin, null, null);

      if (!pinOk) {
        if (row) {
          // Track failures per-credential; lock for LOCKOUT_MINUTES after
          // LOCKOUT_THRESHOLD consecutive misses. Best-effort — if this PATCH
          // itself fails, still refuse the login rather than fail open.
          const attempts = (row.failed_attempts || 0) + 1;
          const LOCKOUT_THRESHOLD = 5, LOCKOUT_MINUTES = 15;
          const patchBody = attempts >= LOCKOUT_THRESHOLD
            ? { failed_attempts: 0, locked_until: new Date(Date.now() + LOCKOUT_MINUTES * 60000).toISOString() }
            : { failed_attempts: attempts };
          try {
            await fetch(rest('sd_employee_auth?license_hash=eq.' + enc(licHash) + '&employee_id=eq.' + enc(employee_id)), {
              method: 'PATCH', headers, body: JSON.stringify(patchBody)
            });
          } catch (e) { /* non-fatal — the login is refused either way */ }
        }
        // Same generic error whether the employee_id doesn't exist or the
        // pin is wrong — don't leak which one via response differences.
        res.status(401).json({ error: { code: 'INVALID_CREDENTIALS', message: 'Incorrect employee ID or PIN' } });
        return;
      }

      // Success — clear any accumulated failure count.
      if (row.failed_attempts) {
        try {
          await fetch(rest('sd_employee_auth?license_hash=eq.' + enc(licHash) + '&employee_id=eq.' + enc(employee_id)), {
            method: 'PATCH', headers, body: JSON.stringify({ failed_attempts: 0, locked_until: null })
          });
        } catch (e) { /* non-fatal */ }
      }
      const token = signSessionToken({ employee_id: row.employee_id, role: row.role, license_hash: licHash });
      res.status(200).json({ ok: true, token, role: row.role, employee_id: row.employee_id });
      return;
    }

    if (action === 'setup') {
      const callerToken = tokenFromRequest(req);
      const caller = verifySessionToken(callerToken, licHash);
      if (!caller || (caller.role !== 'owner' && caller.role !== 'admin')) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Owner or Manager can provision employee credentials' } });
        return;
      }
      const employee_id = String((body.employee_id || '')).trim();
      const pin = String((body.pin || '')).trim();
      const role = body.role;
      if (!employee_id || employee_id.length > 128 || !/^\d{6,8}$/.test(pin) || ROLES.indexOf(role) === -1) {
        res.status(400).json({ error: { message: 'employee_id (max 128 chars), a 6-8 digit pin, and a valid role (' + ROLES.join('|') + ') are required' } });
        return;
      }
      if (body.display_name && String(body.display_name).length > 128) {
        res.status(400).json({ error: { message: 'display_name max 128 chars' } });
        return;
      }
      // Managers may not mint another Owner — only an existing Owner can.
      if (role === 'owner' && caller.role !== 'owner') {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an existing Owner can grant Owner access' } });
        return;
      }
      const { pin_hash, pin_salt } = hashPin(pin);
      const r = await fetch(rest('sd_employee_auth?on_conflict=license_hash,employee_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, employee_id, display_name: body.display_name || employee_id,
          role, pin_hash, pin_salt, active: true, updated_at: new Date().toISOString()
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, employee_id, role });
      return;
    }
  } catch (err) {
    console.error('api/sd-auth error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
};

function upstream(res, detail) {
  console.error('sd-auth upstream error:', detail);
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}
