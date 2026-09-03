// api/alf-auth.js
// ---------------------------------------------------------------------------
// SAIRNcare (assisted living) per-employee login + lockout endpoint.
//
// Built from ZERO -- SAIRNcare is a ground-up app, never had a shared-PIN
// scaffold to replace, same starting point as SAIRNlegacy/SAIRNlaw/
// SAIRNbuild/SAIRNsenior's real-auth builds. Real per-employee identity is
// the prerequisite for the resident privacy gate this app is built around
// (api/sd-data.js's alf_clients branch): a Med Aide or Caregiver must only
// ever see residents assigned to them.
//
// Modelled directly on api/sen-auth.js (SAIRNsenior's equivalent, built
// 2026-08-20 for the same reason). Deliberately SMALL: no MFA, no SSO, no
// audit-log table -- none of that was asked for. The 'roster' action
// (read-only, management-only) backs the Assign-To/reassign controls for
// the resident privacy gate, same shape as every other app's 'roster'
// action this session.
//
// All actions are POST, license key via Authorization: Bearer.
//
//   check_license  {}
//   whoami         {}                      (session required)
//   bootstrap      { employee_id, display_name, pin }   -> role 'owner'
//   login          { employee_id, pin }    -> { ok, token, role, employee_id }
//   setup          { employee_id, display_name, pin, role }  (owner session)
//   roster         {}                      (owner/billing session)
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SD_AUTH_SECRET.
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const lifecycle = require('./_lib/employee-lifecycle');
const {
  hashPin, verifyPin, signSessionToken, verifySessionToken, tokenFromRequest,
  ROLES_BY_APP
} = require('./_lib/auth');

const APP = 'sairncare';
const TABLE = 'sairncare_employee_auth';
const ALF_ROLES = ROLES_BY_APP[APP];
const LOCKOUT_THRESHOLD = 5;
const LOCKOUT_MINUTES = 15;
const ACTIONS = ['check_license', 'whoami', 'bootstrap', 'login', 'setup', 'roster', 'set_active'];
// READ OFF THIS APP'S OWN `setup` GATE below, not assumed. CLAUDE.md records a
// platform guard that hardcoded `owner` and therefore checked nothing on
// SAIRNcode forever; three apps' provisioning lists are NOT owner-only
// (SAIRNgrounds superintendent, SAIRNbiz hr, SAIRNscape crew_lead). This one is,
// and this constant exists so that stays a checked fact rather than an
// assumption baked into a shared helper.
const PROVISIONING_ROLES = ['owner'];
const PROVISIONING_LABEL = 'an Owner';
// 'billing' (Business Office) needs the same broad resident visibility
// 'owner' has for private-pay/HCBS billing across the whole roster --
// same reasoning as every other app's MANAGEMENT_ROLES split this session.
const MANAGEMENT_ROLES = { owner: true, billing: true };

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
    console.error('alf-auth: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
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

  async function loadEmployee(employee_id) {
    const select = 'employee_id,role,pin_hash,pin_salt,failed_attempts,locked_until';
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
    if (action === 'whoami') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const row = await loadEmployee(caller.employee_id);
      if (!row) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'This session is no longer valid — sign in again' } }); return; }
      res.status(200).json({ ok: true, role: row.role, employee_id: row.employee_id });
      return;
    }

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
        res.status(409).json({ error: { code: 'ALREADY_PROVISIONED', message: 'This facility already has employee credentials set up — use action:setup instead' } });
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
      const token = signSessionToken({ employee_id, role: 'owner', license_hash: licHash, app: APP });
      res.status(200).json({ ok: true, token, role: 'owner', employee_id });
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
        res.status(429).json({ error: { code: 'LOCKED', message: 'Too many failed attempts — try again later' } });
        return;
      }

      const pinOk = row ? verifyPin(pin, row.pin_hash, row.pin_salt) : verifyPin(pin, null, null);
      if (!pinOk) {
        await recordFailure(row);
        res.status(401).json({ error: { code: 'INVALID_CREDENTIALS', message: 'Incorrect employee ID or PIN' } });
        return;
      }
      await clearFailures(row);

      const token = signSessionToken({ employee_id: row.employee_id, role: row.role, license_hash: licHash, app: APP });
      res.status(200).json({ ok: true, token, role: row.role, employee_id: row.employee_id });
      return;
    }

    if (action === 'setup') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || caller.role !== 'owner') {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner can provision employee credentials' } });
        return;
      }
      const employee_id = String(body.employee_id || '').trim();
      const pin = String(body.pin || '').trim();
      const role = body.role;
      if (!employee_id || employee_id.length > 128 || !/^\d{6,8}$/.test(pin) || ALF_ROLES.indexOf(role) === -1) {
        res.status(400).json({ error: { message: 'employee_id (max 128 chars), a 6-8 digit pin, and a valid role (' + ALF_ROLES.join('|') + ') are required' } });
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

    // -- ROSTER AND DEACTIVATION (2026-09-03) ------------------------------
    // Both run through api/_lib/employee-lifecycle.js. Read that file's header
    // for why this app had no way to switch a credential off at all, and for
    // the four lockout guards it applies.
    //
    // THE ROSTER NOW RETURNS INACTIVE ROWS. It used to filter `active=eq.true`.
    // Reactivating somebody requires seeing them first, so an access panel
    // cannot work without the change -- but any client that builds a picker
    // from this list must now filter `active !== false` itself, or a departed
    // employee becomes selectable again. sairncare.html's consumers were updated in the
    // same commit; `_alfRoster` is the grep that finds them.
    if (action === 'roster') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      const out = await lifecycle.roster({
        caller: caller, licHash: licHash, table: TABLE, rest: rest, headers: headers,
        canView: !!(caller && MANAGEMENT_ROLES[caller.role]),
        viewLabel: 'Owner or Billing'
      });
      if (out.upstream) return upstream(res, out.upstream);
      res.status(out.status).json(out.body);
      return;
    }

    if (action === 'set_active') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      const out = await lifecycle.setActive({
        caller: caller, body: body, licHash: licHash, table: TABLE,
        provisioningRoles: PROVISIONING_ROLES, roleLabel: PROVISIONING_LABEL,
        rest: rest, headers: headers
        // No `audit`: this app has no audit-log table (api/_lib/audit.js's
        // allow-list is sairnlaw / sairncode / stonedesk only). Omitted rather
        // than passed a no-op, so the response carries no `audited` field --
        // `audited:false` would read as an audit that ran and failed.
      });
      if (out.upstream) return upstream(res, out.upstream);
      res.status(out.status).json(out.body);
      return;
    }
  } catch (err) {
    if (err && err.notProvisioned) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNcare employee accounts are not set up yet — run sql/sairncare_employee_auth_schema.sql' } });
      return;
    }
    console.error('api/alf-auth error:', err);
    res.status(502).json({ error: { message: 'Upstream error — try again' } });
    return;
  }
};

function isMissingTable(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('PGRST205') !== -1 || s.indexOf('does not exist') !== -1;
}
function isPermissionDenied(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('42501') !== -1 || s.indexOf('permission denied') !== -1;
}
function upstream(res, detail) {
  console.error('alf-auth upstream error:', detail);
  if (isMissingTable(detail)) {
    res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNcare employee accounts are not set up yet — run sql/sairncare_employee_auth_schema.sql' } });
    return;
  }
  if (isPermissionDenied(detail)) {
    res.status(503).json({ error: { code: 'NOT_GRANTED', message: 'The SAIRNcare tables exist but the server role lacks privileges on them — re-run the GRANT block at the end of sql/sairncare_employee_auth_schema.sql' } });
    return;
  }
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}
