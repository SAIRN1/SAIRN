// api/sc-auth.js
// ---------------------------------------------------------------------------
// SAIRNcode per-employee login/credential-provisioning endpoint.
//
// Replaces the old client-only auth gate (sairncode.html's
// PINS = {coder:'1234', biller:'2345', auditor:'3456', admin:'4567'} --
// one shared, hardcoded, IDENTICAL-FOR-EVERY-CUSTOMER PIN per role, baked
// into this public repo's client source, zero server involvement, any
// role self-assertable by editing the DOM). Direct port of
// api/sd-auth.js's proven shape (StoneDesk's equivalent) -- same license-
// bearer convention, same lockout design, same generic-error discipline.
//
// Four actions, all POST, license key via Authorization: Bearer:
//
//   action: 'check_license'  {}
//     Confirms the key is real/active before the client stores it.
//
//   action: 'bootstrap'  { employee_id, display_name, pin }
//     Only works when this license has ZERO sairncode_employee_auth rows
//     yet. Creates the first credential, always role 'admin' (SAIRNcode's
//     single top role -- matches requireAdminForDelete()'s existing
//     "Compliance Admin" framing). Refused with 409 once any row exists.
//
//   action: 'login'      { employee_id, pin }
//     Verifies pin against the stored hash, returns a session token+role
//     on success. Locks out after LOCKOUT_THRESHOLD consecutive misses.
//
//   action: 'setup'      { employee_id, display_name, pin, role }
//     Provisions or updates ANOTHER employee's credential. Requires a
//     valid session token belonging to an admin -- coder/biller/auditor
//     cannot self-serve or provision anyone else.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SD_AUTH_SECRET
// See docs/superpowers/specs/2026-08-18-sairncode-real-data-layer-design.md
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const { hashPin, verifyPin, signSessionToken, verifySessionToken, tokenFromRequest, ROLES_BY_APP } = require('./_lib/auth');

const APP = 'sairncode';
const TABLE = 'sairncode_employee_auth';
const ROLES = ROLES_BY_APP[APP];
const LOCKOUT_THRESHOLD = 5;
const LOCKOUT_MINUTES = 15;

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
  if (['bootstrap', 'login', 'setup', 'check_license'].indexOf(action) === -1) {
    res.status(400).json({ error: { message: "action must be 'bootstrap', 'login', 'setup', or 'check_license'" } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY || !process.env.SD_AUTH_SECRET) {
    console.error('sc-auth: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
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
    res.status(200).json({ ok: true, active: true, app_id: lic.app_id || null });
    return;
  }

  const licHash = lic.license_hash;
  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };
  const rest = (path) => SUPABASE_URL + '/rest/v1/' + path;
  const enc = encodeURIComponent;

  try {
    if (action === 'bootstrap') {
      const employee_id = String((body.employee_id || '')).trim();
      const pin = String((body.pin || '')).trim();
      if (!employee_id || employee_id.length > 128 || !/^\d{6,8}$/.test(pin)) {
        res.status(400).json({ error: { message: 'employee_id (max 128 chars) and a 6-8 digit pin are required' } });
        return;
      }
      if (body.display_name && String(body.display_name).length > 128) {
        res.status(400).json({ error: { message: 'display_name max 128 chars' } });
        return;
      }
      const existingR = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&select=id&limit=1'), { headers });
      if (existingR.status === 404 || existingR.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Auth table not set up yet -- run sql/sairncode_employee_auth_schema.sql in Supabase first.' } });
        return;
      }
      const existingRows = await existingR.json();
      if (!existingR.ok) return upstream(res, existingRows);
      if (Array.isArray(existingRows) && existingRows.length > 0) {
        res.status(409).json({ error: { code: 'ALREADY_PROVISIONED', message: 'This license already has employee credentials set up — use action:setup instead' } });
        return;
      }
      const { pin_hash, pin_salt } = hashPin(pin);
      const r = await fetch(rest(TABLE), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, employee_id, display_name: body.display_name || employee_id,
          role: 'admin', pin_hash, pin_salt, active: true
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const token = signSessionToken({ employee_id, role: 'admin', license_hash: licHash, app: APP });
      res.status(200).json({ ok: true, token, role: 'admin', employee_id });
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
        TABLE + '?license_hash=eq.' + enc(licHash) + '&employee_id=eq.' + enc(employee_id) +
        '&active=eq.true&select=employee_id,role,pin_hash,pin_salt,failed_attempts,locked_until&limit=1'), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Auth table not set up yet -- run sql/sairncode_employee_auth_schema.sql in Supabase first.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const row = Array.isArray(rows) && rows[0];

      if (row && row.locked_until && new Date(row.locked_until).getTime() > Date.now()) {
        res.status(429).json({ error: { code: 'LOCKED', message: 'Too many failed attempts — try again later' } });
        return;
      }

      // verifyPin always runs at equal cost whether row exists or not --
      // no early-return on missing row, so employee_id existence can't be
      // timed.
      const pinOk = row ? verifyPin(pin, row.pin_hash, row.pin_salt) : verifyPin(pin, null, null);

      if (!pinOk) {
        if (row) {
          const attempts = (row.failed_attempts || 0) + 1;
          const patchBody = attempts >= LOCKOUT_THRESHOLD
            ? { failed_attempts: 0, locked_until: new Date(Date.now() + LOCKOUT_MINUTES * 60000).toISOString() }
            : { failed_attempts: attempts };
          try {
            await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&employee_id=eq.' + enc(employee_id)), {
              method: 'PATCH', headers, body: JSON.stringify(patchBody)
            });
          } catch (e) { /* non-fatal — the login is refused either way */ }
        }
        res.status(401).json({ error: { code: 'INVALID_CREDENTIALS', message: 'Incorrect employee ID or PIN' } });
        return;
      }

      if (row.failed_attempts) {
        try {
          await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&employee_id=eq.' + enc(employee_id)), {
            method: 'PATCH', headers, body: JSON.stringify({ failed_attempts: 0, locked_until: null })
          });
        } catch (e) { /* non-fatal */ }
      }
      const token = signSessionToken({ employee_id: row.employee_id, role: row.role, license_hash: licHash, app: APP });
      res.status(200).json({ ok: true, token, role: row.role, employee_id: row.employee_id });
      return;
    }

    if (action === 'setup') {
      const callerToken = tokenFromRequest(req);
      const caller = verifySessionToken(callerToken, licHash, APP);
      if (!caller || caller.role !== 'admin') {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Compliance Admin can provision employee credentials' } });
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
      res.status(200).json({ ok: true, employee_id, role });
      return;
    }
  } catch (err) {
    console.error('api/sc-auth error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
};

function upstream(res, detail) {
  console.error('sc-auth upstream error:', detail);
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}
