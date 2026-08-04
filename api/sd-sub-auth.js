// api/sd-sub-auth.js
// ---------------------------------------------------------------------------
// Subcontractor Portal (Phase 1) — login/credential-provisioning endpoint for
// subs. Mirrors api/sd-auth.js's shape closely (same PIN-hash/session-token
// primitives from api/_lib/auth.js) but is intentionally a SEPARATE endpoint,
// not a new action bolted onto sd-auth.js — subs are not staff, and keeping
// their credential path physically separate makes it easier to verify (by
// inspection, not just by trusting a role check) that nothing here can ever
// mint or accept a real employee token. See api/_lib/auth.js's
// 'stonedesk_sub' app namespace for the other half of that separation.
//
// Two actions, both POST, license key via Authorization: Bearer (same
// convention as api/sd-auth.js / api/sd-data.js):
//
//   action: 'setup'  { sub_id, pin }
//     Provisions or resets a sub's PIN. Requires a valid EMPLOYEE session
//     token (X-SD-Auth header, app:'stonedesk') belonging to owner or admin
//     — subs never self-provision; office sets their PIN when adding them
//     to the roster (or resetting it later). Requires the sub already exist
//     in sd_subs (added via api/sd-sub-data.js's roster write) — this
//     endpoint only ever touches credentials, never creates a roster row,
//     same separation-of-concerns as sd_employee_auth vs `employees`.
//
//   action: 'login'  { sub_id, pin }
//     Verifies pin against the stored hash, returns a session token scoped
//     app:'stonedesk_sub', role:'sub' on success. Same lockout-after-5-
//     failed-attempts and constant-time-reject-on-unknown-id protections as
//     api/sd-auth.js's login action, copied deliberately rather than
//     "simplified" — a lower-value credential tier is not a reason to accept
//     weaker brute-force protection.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SD_AUTH_SECRET
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const { hashPin, verifyPin, signSessionToken, verifySessionToken, tokenFromRequest } = require('./_lib/auth');

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
  if (['setup', 'login'].indexOf(action) === -1) {
    res.status(400).json({ error: { message: "action must be 'setup' or 'login'" } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY || !process.env.SD_AUTH_SECRET) {
    console.error('sd-sub-auth: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
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
    if (action === 'setup') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, 'stonedesk');
      if (!caller || (caller.role !== 'owner' && caller.role !== 'admin')) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Owner or Manager can provision subcontractor credentials' } });
        return;
      }
      const sub_id = String((body.sub_id || '')).trim();
      const pin = String((body.pin || '')).trim();
      if (!sub_id || sub_id.length > 128 || !/^\d{6,8}$/.test(pin)) {
        res.status(400).json({ error: { message: 'sub_id (max 128 chars) and a 6-8 digit pin are required' } });
        return;
      }
      // The sub must already exist on the roster — this endpoint only ever
      // touches credentials. Refuses rather than silently creating a
      // roster-less credential nothing else would ever surface.
      const rosterCheck = await fetch(rest('sd_subs?license_hash=eq.' + enc(licHash) + '&sub_id=eq.' + enc(sub_id) + '&select=sub_id&limit=1'), { headers });
      const rosterRows = await rosterCheck.json();
      if (!rosterCheck.ok) return upstream(res, rosterRows);
      if (!Array.isArray(rosterRows) || !rosterRows.length) {
        res.status(404).json({ error: { code: 'SUB_NOT_FOUND', message: 'Add this subcontractor to the roster first' } });
        return;
      }
      const { pin_hash, pin_salt } = hashPin(pin);
      const r = await fetch(rest('sd_sub_auth?on_conflict=license_hash,sub_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, sub_id, pin_hash, pin_salt, active: true,
          failed_attempts: 0, locked_until: null, updated_at: new Date().toISOString()
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, sub_id });
      return;
    }

    if (action === 'login') {
      const sub_id = String((body.sub_id || '')).trim();
      const pin = String((body.pin || '')).trim();
      if (!sub_id || !pin) {
        res.status(400).json({ error: { message: 'sub_id and pin are required' } });
        return;
      }
      const r = await fetch(rest(
        'sd_sub_auth?license_hash=eq.' + enc(licHash) + '&sub_id=eq.' + enc(sub_id) +
        '&active=eq.true&select=sub_id,pin_hash,pin_salt,failed_attempts,locked_until&limit=1'), { headers });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const row = Array.isArray(rows) && rows[0];

      if (row && row.locked_until && new Date(row.locked_until).getTime() > Date.now()) {
        res.status(429).json({ error: { code: 'LOCKED', message: 'Too many failed attempts — try again later' } });
        return;
      }

      const pinOk = row ? verifyPin(pin, row.pin_hash, row.pin_salt) : verifyPin(pin, null, null);

      if (!pinOk) {
        if (row) {
          const attempts = (row.failed_attempts || 0) + 1;
          const LOCKOUT_THRESHOLD = 5, LOCKOUT_MINUTES = 15;
          const patchBody = attempts >= LOCKOUT_THRESHOLD
            ? { failed_attempts: 0, locked_until: new Date(Date.now() + LOCKOUT_MINUTES * 60000).toISOString() }
            : { failed_attempts: attempts };
          try {
            await fetch(rest('sd_sub_auth?license_hash=eq.' + enc(licHash) + '&sub_id=eq.' + enc(sub_id)), {
              method: 'PATCH', headers, body: JSON.stringify(patchBody)
            });
          } catch (e) { /* non-fatal — the login is refused either way */ }
        }
        res.status(401).json({ error: { code: 'INVALID_CREDENTIALS', message: 'Incorrect ID or PIN' } });
        return;
      }

      if (row.failed_attempts) {
        try {
          await fetch(rest('sd_sub_auth?license_hash=eq.' + enc(licHash) + '&sub_id=eq.' + enc(sub_id)), {
            method: 'PATCH', headers, body: JSON.stringify({ failed_attempts: 0, locked_until: null })
          });
        } catch (e) { /* non-fatal */ }
      }

      // Also pull the sub's display name from the roster so the portal can
      // greet them by name without a second round-trip.
      let name = row.sub_id;
      try {
        const nameRes = await fetch(rest('sd_subs?license_hash=eq.' + enc(licHash) + '&sub_id=eq.' + enc(row.sub_id) + '&select=name&limit=1'), { headers });
        const nameRows = await nameRes.json();
        if (nameRes.ok && Array.isArray(nameRows) && nameRows[0] && nameRows[0].name) name = nameRows[0].name;
      } catch (e) { /* non-fatal — fall back to sub_id as the display name */ }

      const token = signSessionToken({ employee_id: row.sub_id, role: 'sub', license_hash: licHash, app: 'stonedesk_sub' });
      res.status(200).json({ ok: true, token, sub_id: row.sub_id, name });
      return;
    }
  } catch (err) {
    console.error('api/sd-sub-auth error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
};

function upstream(res, detail) {
  console.error('sd-sub-auth upstream error:', detail);
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}
