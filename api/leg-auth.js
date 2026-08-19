// api/leg-auth.js
// ---------------------------------------------------------------------------
// SAIRNlegacy per-employee login + lockout endpoint.
//
// Replaces sairnlegacy.html's old client-only gate (DEFAULT_PINS = one
// shared PIN per role, in the page source, zero server involvement — every
// director shared one PIN, so nothing could ever be attributed to an
// individual and any role was self-assertable by editing the DOM). This is
// the server side of the real model: each employee has their own PIN,
// hashed server-side, checked against sairnlegacy_employee_auth
// (sql/sairnlegacy_employee_auth_schema.sql).
//
// Modelled directly on api/law-auth.js (SAIRNlaw's equivalent) — same
// license-bearer convention, same lockout design, same generic-error
// discipline. Deliberately SMALLER in scope than law-auth.js: no MFA, no
// SSO, no audit-log table — none of that was asked for building this
// (confirmed with Michael, 2026-08-19), and an unused column/table is
// exactly the kind of dead-schema drift Guardian's own dormant-code rule
// flags elsewhere in this project. Add them later as their own scoped
// change if actually needed.
//
// The one action beyond SAIRNlaw's own set: grant_shared_knowledge_access.
// This is the real, server-enforced permission mechanism behind
// sairnlegacy.html's shared company-knowledge layer -- owner/director get
// it by role alone (checked in api/sd-data.js's shared_knowledge branch,
// not here), 'staff' needs an explicit named grant, which this action
// sets. Restricted to owner OR director (Michael's own framing was
// "management" for who can grant, not "owner only") -- provisioning a
// brand-new employee's credentials via 'setup' stays owner-only, matching
// SAIRNlaw's precedent exactly, since that's account creation, a more
// sensitive action than granting one existing employee a data-visibility
// flag.
//
// All actions are POST, license key via Authorization: Bearer.
//
//   check_license  {}
//     Confirms the key is real/active before the client stores it.
//
//   whoami         {}                      (session required)
//     Re-verifies a locally-cached session token against the server, not
//     just the token's own unexpired signature -- same fix SAIRNlaw needed
//     live (2026-08-18), applied here from the start rather than waiting
//     to rediscover the same gap.
//
//   bootstrap      { employee_id, display_name, pin }
//     Only works when this license has ZERO rows yet. Creates the first
//     credential, always role 'owner'. 409 once any row exists.
//
//   login          { employee_id, pin }
//     -> { ok, token, role, employee_id }
//
//   setup          { employee_id, display_name, pin, role }  (owner session)
//     Provisions/updates another employee's credential.
//
//   grant_shared_knowledge_access { employee_id, granted }  (owner/director session)
//     Sets the target employee's shared_knowledge_access flag. Does
//     nothing for an owner/director target (they already have access by
//     role) -- only meaningful for a 'staff' row, but not refused for the
//     others either, since a no-op grant is harmless and refusing it would
//     just be a confusing extra error case for no real benefit.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SD_AUTH_SECRET.
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const {
  hashPin, verifyPin, signSessionToken, verifySessionToken, tokenFromRequest,
  ROLES_BY_APP
} = require('./_lib/auth');

const APP = 'sairnlegacy';
const TABLE = 'sairnlegacy_employee_auth';
const LEG_ROLES = ROLES_BY_APP[APP];
const LOCKOUT_THRESHOLD = 5;
const LOCKOUT_MINUTES = 15;
const ACTIONS = ['check_license', 'whoami', 'bootstrap', 'login', 'setup', 'grant_shared_knowledge_access'];
const MANAGEMENT_ROLES = { owner: true, director: true };

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
    console.error('leg-auth: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
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

  // Loads one employee row, or null. Throws a tagged error if the table
  // itself is missing so the caller can answer 503 NOT_PROVISIONED instead
  // of a generic 500 that looks identical to a real outage.
  async function loadEmployee(employee_id) {
    const select = 'employee_id,role,pin_hash,pin_salt,failed_attempts,locked_until,shared_knowledge_access';
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

  // Shared failure bookkeeping, same shape as api/law-auth.js's own.
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
      res.status(200).json({ ok: true, role: row.role, employee_id: row.employee_id, shared_knowledge_access: !!row.shared_knowledge_access });
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
        res.status(409).json({ error: { code: 'ALREADY_PROVISIONED', message: 'This funeral home already has employee credentials set up — use action:setup instead' } });
        return;
      }
      const { pin_hash, pin_salt } = hashPin(pin);
      const r = await fetch(rest(TABLE), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, employee_id, display_name: body.display_name || employee_id,
          role: 'owner', pin_hash, pin_salt, active: true, shared_knowledge_access: false
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

      // verifyPin runs at equal cost whether the row exists or not (see
      // api/_lib/auth.js DUMMY_SALT_FOR_TIMING) — no early return on a
      // missing row, so employee_id existence can't be timed.
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
      // expectedApp:APP matters — without it a valid owner token from a
      // DIFFERENT app ('owner' exists in most apps' role lists) would pass
      // this check and be able to provision SAIRNlegacy credentials.
      if (!caller || caller.role !== 'owner') {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner can provision employee credentials' } });
        return;
      }
      const employee_id = String(body.employee_id || '').trim();
      const pin = String(body.pin || '').trim();
      const role = body.role;
      if (!employee_id || employee_id.length > 128 || !/^\d{6,8}$/.test(pin) || LEG_ROLES.indexOf(role) === -1) {
        res.status(400).json({ error: { message: 'employee_id (max 128 chars), a 6-8 digit pin, and a valid role (' + LEG_ROLES.join('|') + ') are required' } });
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

    if (action === 'grant_shared_knowledge_access') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || !MANAGEMENT_ROLES[caller.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner or Director can grant shared-knowledge access' } });
        return;
      }
      const target = String(body.employee_id || '').trim();
      if (!target) { res.status(400).json({ error: { message: 'employee_id is required' } }); return; }
      const granted = !!body.granted;
      const targetRow = await loadEmployee(target);
      if (!targetRow) { res.status(404).json({ error: { code: 'NOT_FOUND', message: 'No active employee with that ID' } }); return; }
      const r = await patchEmployee(target, { shared_knowledge_access: granted });
      if (!r.ok) return upstream(res, await r.json());
      res.status(200).json({ ok: true, employee_id: target, granted: granted, granted_by: caller.employee_id });
      return;
    }
  } catch (err) {
    if (err && err.notProvisioned) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlegacy employee accounts are not set up yet — run sql/sairnlegacy_employee_auth_schema.sql' } });
      return;
    }
    console.error('api/leg-auth error:', err);
    res.status(502).json({ error: { message: 'Upstream error — try again' } });
    return;
  }
};

// PostgREST answers a missing table with a specific code rather than a
// network error — distinguishing it lets the caller say "run the migration"
// instead of "upstream error". Same pattern as api/law-auth.js.
function isMissingTable(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('PGRST205') !== -1 || s.indexOf('does not exist') !== -1;
}
function isPermissionDenied(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('42501') !== -1 || s.indexOf('permission denied') !== -1;
}
function upstream(res, detail) {
  console.error('leg-auth upstream error:', detail);
  if (isMissingTable(detail)) {
    res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlegacy employee accounts are not set up yet — run sql/sairnlegacy_employee_auth_schema.sql' } });
    return;
  }
  if (isPermissionDenied(detail)) {
    res.status(503).json({ error: { code: 'NOT_GRANTED', message: 'The SAIRNlegacy tables exist but the server role lacks privileges on them — re-run the GRANT block at the end of sql/sairnlegacy_employee_auth_schema.sql' } });
    return;
  }
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}
