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
const { writeAuditLog } = require('./_lib/audit');
const { hashPin, verifyPin, signSessionToken, verifySessionToken, tokenFromRequest, ROLES } = require('./_lib/auth');

const AUDIT_TABLE = 'stonedesk_audit_log';
// Roles that can provision or change credentials on StoneDesk. BOTH count
// toward the last-admin guard -- unlike SAIRNcode, where 'admin' is the only
// provisioning role. Matches this file's own setup and roster gates exactly,
// so the three checks cannot drift apart.
const PROVISIONING_ROLES = ['owner', 'admin'];

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
  if (['bootstrap', 'login', 'setup', 'check_license', 'roster', 'set_active'].indexOf(action) === -1) {
    res.status(400).json({ error: { message: "action must be 'bootstrap', 'login', 'setup', 'check_license', 'roster', or 'set_active'" } });
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

  // check_license: the self-service license-entry screen (stonedesk.html's
  // #sd-license-view, added 2026-08-05) needs to confirm a key is real
  // BEFORE storing it to localStorage and moving the user to employee
  // login -- the alternative (only finding out via a failed login attempt)
  // would misattribute a bad license key to a wrong PIN. License validity
  // is already fully checked above, common to every action; this just
  // stops here instead of falling through to bootstrap/login/setup's
  // employee-credential logic, which a bare license check has no business
  // touching.
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
      const token = signSessionToken({ employee_id, role: 'owner', license_hash: licHash, app: 'stonedesk' });
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
      const token = signSessionToken({ employee_id: row.employee_id, role: row.role, license_hash: licHash, app: 'stonedesk' });
      res.status(200).json({ ok: true, token, role: row.role, employee_id: row.employee_id });
      return;
    }

    if (action === 'setup') {
      const callerToken = tokenFromRequest(req);
      // expectedApp:'stonedesk' matters here — without it, a valid SAIRNbiz
      // owner token (role 'owner' exists in both apps' role lists) would
      // also pass this check, letting a SAIRNbiz login provision StoneDesk
      // credentials. Caught while wiring up api/sb-auth.js's mirror of this
      // same endpoint.
      const caller = verifySessionToken(callerToken, licHash, 'stonedesk');
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

    // Added 2026-08-19 for the CRM/Lead Pipeline reassignment control --
    // owner/admin need a real roster to assign/reassign a lead to, and
    // there was no read path for StoneDesk's own sd_employee_auth roster
    // anywhere before this (the 'employees' resource in api/sd-data.js is
    // a different table entirely -- SAIRNbiz-owned HR data cross-read by
    // StoneDesk, not this app's own login credentials). Read-only, no PIN
    // hashes/salts/lockout state ever leave this endpoint.
    if (action === 'roster') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, 'stonedesk');
      if (!caller || (caller.role !== 'owner' && caller.role !== 'admin')) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Owner or Manager can view the employee roster' } });
        return;
      }
      // Includes INACTIVE rows as of 2026-08-23, where this previously
      // filtered to active=eq.true. That filter made sense when there was no
      // way to deactivate anyone; now that set_active exists, an Owner or
      // Manager has to be able to SEE a deactivated person in order to turn
      // them back on. Same shape as api/sc-auth.js's roster.
      const r = await fetch(rest('sd_employee_auth?license_hash=eq.' + enc(licHash) + '&select=employee_id,display_name,role,active&order=employee_id.asc'), { headers });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      // A session token carries a role claim and stays valid for its full
      // life INCLUDING after the credential behind it is deactivated. Found
      // live on SAIRNcode 2026-08-23 and fixed there; carried here rather
      // than waiting to rediscover it on StoneDesk.
      const callerRowR = (rows || []).filter(function (x) { return x.employee_id === caller.employee_id; })[0];
      if (!callerRowR || callerRowR.active !== true) {
        res.status(403).json({ error: { code: 'CREDENTIAL_INACTIVE', message: 'This credential has been deactivated. Sign in again with an active account.' } });
        return;
      }
      res.status(200).json({ ok: true, employees: rows || [] });
      return;
    }

    // ── set_active: credential lifecycle (2026-08-23) ──
    // StoneDesk's half of the same feature built for SAIRNcode in 12c670c.
    // Identical design, adjusted for this app's provisioning roles: StoneDesk
    // has owner AND admin (Manager), both of which can run setup, so both
    // count toward the last-admin guard -- unlike SAIRNcode where 'admin' is
    // the only one.
    //
    // WHY THIS EXISTS AT ALL: three StoneDesk licenses were already lost to
    // untracked credential state. SD-PINNACLE-2026's PIN is still
    // undocumented, SD-AUDIT-2026 needed a hand-written DELETE run directly
    // in Supabase, and SD-PARTNER-2026 was provisioned purely to route around
    // both. There was no way to disable a credential through the API.
    //
    // DEACTIVATION, NOT DELETION. The row stays; only `active` flips. The
    // login branch above already filters active=eq.true, so the flag is
    // enforced the moment it is written. Keeping the row preserves
    // created_at, role history and audit linkage -- deleting is what made
    // those three cleanups both unrecoverable and unauditable.
    //
    // THE LOCKOUT THIS MUST NOT CAUSE: bootstrap refuses once ANY row exists
    // for the license and does NOT filter on active. So a license with zero
    // active owner/admins cannot log in, cannot run setup, and cannot
    // re-bootstrap -- dead through the API, recoverable only by direct
    // database access. That is exactly how SD-AUDIT-2026 was lost. bootstrap
    // is deliberately NOT changed to fall back to "no ACTIVE rows": that
    // would auto-heal a lockout, but would also let anyone holding a license
    // key deactivate their way to a fresh bootstrap and seize the account.
    if (action === 'set_active') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, 'stonedesk');
      if (!caller || PROVISIONING_ROLES.indexOf(caller.role) === -1) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Owner or Manager can activate or deactivate a credential' } });
        return;
      }
      const audit = (event_type, detail) => writeAuditLog(SUPABASE_URL, SERVICE_KEY, {
        license_hash: licHash, employee_id: caller.employee_id, role: caller.role,
        event_type: event_type, detail: detail, table: AUDIT_TABLE
      });

      const target_id = String((body.employee_id || '')).trim();
      const nextActive = body.active === true;
      const reason = String((body.reason || '')).trim();
      if (!target_id) { res.status(400).json({ error: { message: 'employee_id is required' } }); return; }
      if (typeof body.active !== 'boolean') { res.status(400).json({ error: { message: 'active must be true or false' } }); return; }
      // Required to switch someone OFF, not to switch them on. Reactivating
      // is self-explanatory and always safe; a deactivation is the thing
      // someone will be trying to reconstruct months later.
      if (!nextActive && !reason) {
        res.status(400).json({ error: { message: 'reason is required when deactivating a credential' } });
        return;
      }
      if (reason.length > 500) { res.status(400).json({ error: { message: 'reason max 500 characters' } }); return; }

      if (!nextActive && target_id === caller.employee_id) {
        const selfAudited = await audit('credential_change_refused', { target: target_id, requested_active: false, reason_code: 'SELF_DEACTIVATE' });
        res.status(409).json({ audited: selfAudited, error: { code: 'SELF_DEACTIVATE', message: 'You cannot deactivate your own credential. Ask another Owner or Manager to do it.' } });
        return;
      }

      // Read the real roster ONCE and decide from it -- never from what the
      // client claimed about the target or about who else exists.
      const allR = await fetch(rest('sd_employee_auth?license_hash=eq.' + enc(licHash) + '&select=employee_id,role,active'), { headers });
      const all = await allR.json();
      if (!allR.ok) return upstream(res, all);
      const rowsAll = Array.isArray(all) ? all : [];

      const callerRow = rowsAll.filter(function (x) { return x.employee_id === caller.employee_id; })[0];
      if (!callerRow || callerRow.active !== true) {
        const inactiveAudited = await audit('credential_change_refused', { target: target_id, requested_active: nextActive, reason_code: 'CREDENTIAL_INACTIVE' });
        res.status(403).json({ audited: inactiveAudited, error: { code: 'CREDENTIAL_INACTIVE', message: 'This credential has been deactivated. Sign in again with an active account.' } });
        return;
      }

      const target = rowsAll.filter(function (x) { return x.employee_id === target_id; })[0];
      if (!target) {
        res.status(404).json({ error: { code: 'NOT_FOUND', message: 'No such employee on this license' } });
        return;
      }

      const activeAdmins = rowsAll.filter(function (x) {
        return x.active === true && PROVISIONING_ROLES.indexOf(x.role) !== -1;
      });
      // Quarantined guard, same as SAIRNcode's: unreachable by construction
      // while the caller-still-active check above stands, because an active
      // caller plus a DIFFERENT active admin target implies at least two.
      // Kept because reachability is a property of today's rule set -- a new
      // provisioning role or any path skipping that check makes it live
      // again, and a lockout is not worth re-discovering in production.
      if (!nextActive && PROVISIONING_ROLES.indexOf(target.role) !== -1 && target.active === true && activeAdmins.length <= 1) {
        const lastAdminAudited = await audit('credential_change_refused', { target: target_id, requested_active: false, reason_code: 'LAST_ADMIN', active_admins: activeAdmins.length });
        res.status(409).json({
          audited: lastAdminAudited,
          error: {
            code: 'LAST_ADMIN',
            message: 'This is the only active Owner or Manager on this license. Deactivating it would lock everyone out with no way back in through the app — provision another first, then retry.'
          }
        });
        return;
      }

      if (target.active === nextActive) {
        res.status(200).json({ ok: true, employee_id: target_id, active: nextActive, unchanged: true, remaining_admins: activeAdmins.length });
        return;
      }

      const patchR = await fetch(rest('sd_employee_auth?license_hash=eq.' + enc(licHash) + '&employee_id=eq.' + enc(target_id)), {
        method: 'PATCH',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({ active: nextActive, updated_at: new Date().toISOString() })
      });
      const patched = await patchR.json();
      if (!patchR.ok) return upstream(res, patched);

      const remaining = rowsAll.filter(function (x) {
        var isActive = (x.employee_id === target_id) ? nextActive : x.active === true;
        return isActive && PROVISIONING_ROLES.indexOf(x.role) !== -1;
      }).length;

      const audited = await audit(nextActive ? 'credential_reactivated' : 'credential_deactivated', {
        target: target_id, target_role: target.role, previous_active: target.active,
        new_active: nextActive, reason: reason || null, remaining_admins: remaining
      });

      res.status(200).json({ ok: true, employee_id: target_id, active: nextActive, remaining_admins: remaining, audited: audited });
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

// ── Exported for tools/licence_recoverability_check.py via
// api/provisioner-health.js, added 2026-08-29. The trapdoor is a licence with
// credential rows and ZERO rows that are both `active` and hold one of these
// roles. The detector must read THIS list rather than assume 'owner' --
// SAIRNcode's is 'admin' -- so the list is exported instead of duplicated.
module.exports.PROVISIONING_ROLES = PROVISIONING_ROLES;
module.exports.EMPLOYEE_TABLE = 'sd_employee_auth';
