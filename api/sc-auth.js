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
const { writeAuditLog } = require('./_lib/audit');

const APP = 'sairncode';
const TABLE = 'sairncode_employee_auth';
const ROLES = ROLES_BY_APP[APP];
const LOCKOUT_THRESHOLD = 5;
const LOCKOUT_MINUTES = 15;
const AUDIT_TABLE = 'sairncode_audit_log';
// The only role that can provision or change credentials. Counted by the
// last-admin guard below -- if this list ever grows, that guard grows with it
// automatically rather than needing a second edit someone forgets.
const PROVISIONING_ROLES = ['admin'];

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

    // ── roster: who exists on this license (2026-08-23) ──
    // Ported from api/sd-auth.js, which has had this since 2026-08-19.
    // SAIRNcode had none, which made set_active below unusable on its own --
    // an admin cannot deactivate an employee_id they have no way to look up.
    // Admin-only, matching setup. 'auditor' deliberately gets NO access:
    // read-only on the app's DATA is its job; the credential roster is not
    // data, it is the access-control surface itself.
    // Never returns pin_hash/pin_salt/lockout state -- same rule sd-auth's
    // roster follows. Includes inactive rows (unlike sd-auth's, which filters
    // to active=true) precisely BECAUSE reactivation exists: an admin has to
    // be able to see a deactivated person in order to turn them back on.
    if (action === 'roster') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || PROVISIONING_ROLES.indexOf(caller.role) === -1) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Compliance Admin can view the employee roster' } });
        return;
      }
      const r = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&select=employee_id,display_name,role,active&order=employee_id.asc'), { headers });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      // A session token carries a role claim and stays valid for its full
      // 12h life -- including after the credential behind it is deactivated.
      // Found live 2026-08-23 while exercising the LAST_ADMIN path: a
      // deactivated admin could still act. Re-check the caller's CURRENT
      // active state against the row we just read, so deactivation takes
      // effect immediately rather than whenever the token happens to expire.
      const callerRowR = (rows || []).filter(function (x) { return x.employee_id === caller.employee_id; })[0];
      if (!callerRowR || callerRowR.active !== true) {
        res.status(403).json({ error: { code: 'CREDENTIAL_INACTIVE', message: 'This credential has been deactivated. Sign in again with an active account.' } });
        return;
      }
      res.status(200).json({ ok: true, employees: rows || [] });
      return;
    }

    // ── set_active: the credential lifecycle this app never had ──
    // Until today an account could be created and never removed, disabled, or
    // rotated-with-knowledge through the API. Every cleanup needed a
    // hand-written SQL file and a round trip through a human with Supabase
    // access. That is the gap this closes.
    //
    // DEACTIVATION, NOT DELETION, deliberately. The row stays; only `active`
    // flips. Login already filters active=eq.true (see the login branch
    // above), so the flag is enforced the moment it is written -- there is no
    // second mechanism to keep in sync. Keeping the row preserves created_at,
    // the role history, and any audit entries that reference the employee_id;
    // deleting is what made the earlier cleanups both unrecoverable and
    // unauditable.
    //
    // THE LOCKOUT THIS MUST NOT CAUSE, and why the guard below is the
    // load-bearing part of this whole feature: `bootstrap` refuses once ANY
    // row exists for the license and does NOT filter on active (see its own
    // branch above). So deactivating the last admin produces a license where
    // nobody can log in, nobody can run setup, and bootstrap still 409s --
    // permanently unusable through the API, recoverable only by direct
    // database access. That is exactly how SD-AUDIT-2026 was lost, and
    // without this guard a single call would reproduce it.
    //
    // bootstrap is deliberately NOT changed to fall back to "no ACTIVE rows".
    // It would auto-heal a lockout, but it would also let anyone holding the
    // license key deactivate their way to a fresh bootstrap and seize the
    // account. The existence check stays absolute; recovery goes through
    // another admin.
    if (action === 'set_active') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || PROVISIONING_ROLES.indexOf(caller.role) === -1) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Compliance Admin can activate or deactivate a credential' } });
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
      // A reason is required to switch someone OFF and not to switch them on.
      // Reactivating is self-explanatory and always safe; a deactivation is
      // the thing someone will be trying to reconstruct months later.
      if (!nextActive && !reason) {
        res.status(400).json({ error: { message: 'reason is required when deactivating a credential' } });
        return;
      }
      if (reason.length > 500) { res.status(400).json({ error: { message: 'reason max 500 characters' } }); return; }

      // No self-deactivation. It is the likeliest accidental route into the
      // last-admin case below, and there is no legitimate reason to do it to
      // yourself rather than have another admin do it.
      if (!nextActive && target_id === caller.employee_id) {
        await audit('credential_change_refused', { target: target_id, requested_active: false, reason_code: 'SELF_DEACTIVATE' });
        res.status(409).json({ error: { code: 'SELF_DEACTIVATE', message: 'You cannot deactivate your own credential. Ask another Compliance Admin to do it.' } });
        return;
      }

      // Read the real current roster ONCE and decide from it -- never from
      // what the client claimed about the target or about who else exists.
      const allR = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&select=employee_id,role,active'), { headers });
      const all = await allR.json();
      if (!allR.ok) return upstream(res, all);
      const rowsAll = Array.isArray(all) ? all : [];

      // The caller must still be ACTIVE, not merely holding a token that says
      // 'admin'. Found live 2026-08-23: a session survives its own credential's
      // deactivation for up to 12h, so without this an admin who was just
      // removed could keep removing other people -- including walking the
      // license down to the LAST_ADMIN refusal from the wrong side. Checked
      // against the row read below, so it costs no extra query.
      const callerRow = rowsAll.filter(function (x) { return x.employee_id === caller.employee_id; })[0];
      if (!callerRow || callerRow.active !== true) {
        await audit('credential_change_refused', { target: target_id, requested_active: nextActive, reason_code: 'CREDENTIAL_INACTIVE' });
        res.status(403).json({ error: { code: 'CREDENTIAL_INACTIVE', message: 'This credential has been deactivated. Sign in again with an active account.' } });
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
      // THE GUARD. Only bites when the change would actually remove the last
      // one: deactivating a non-admin, or a non-last admin, is unaffected,
      // and reactivation can only ever increase the count so it is never
      // blocked (confirmed decision: reactivation is unconditional).
      //
      // CURRENTLY UNREACHABLE BY CONSTRUCTION, and kept deliberately -- this
      // is a quarantined guard, not dead code, and the distinction is
      // recorded here so a future reader does not delete it as unused.
      // Reaching it needs: caller is an ACTIVE admin, target is a different
      // ACTIVE admin, and exactly one active admin exists. The first two
      // conditions imply at least two, so the third cannot hold. Before the
      // caller-still-active re-check above was added, it WAS reachable and
      // was proven firing live on 2026-08-23 -- a deactivated admin whose
      // 12h token had not yet expired could deactivate the last remaining
      // admin. Closing that hole is what made this branch unreachable.
      // It stays because reachability is a property of the CURRENT rule set:
      // adding a second provisioning role to PROVISIONING_ROLES, a
      // service-to-service caller, or any path that does not go through the
      // active re-check would make it live again, and a lockout is not a
      // failure mode worth re-discovering in production.
      if (!nextActive && PROVISIONING_ROLES.indexOf(target.role) !== -1 && target.active === true && activeAdmins.length <= 1) {
        await audit('credential_change_refused', { target: target_id, requested_active: false, reason_code: 'LAST_ADMIN', active_admins: activeAdmins.length });
        res.status(409).json({
          error: {
            code: 'LAST_ADMIN',
            message: 'This is the only active Compliance Admin on this license. Deactivating it would lock everyone out with no way back in through the app — provision another admin first, then retry.'
          }
        });
        return;
      }

      // No-op writes are reported honestly rather than as a change that did
      // not happen.
      if (target.active === nextActive) {
        res.status(200).json({ ok: true, employee_id: target_id, active: nextActive, unchanged: true, remaining_admins: activeAdmins.length });
        return;
      }

      const patchR = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&employee_id=eq.' + enc(target_id)), {
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

      // Follows the audit contract in api/_lib/audit.js: a failed log write
      // never blocks the action. But for a CREDENTIAL change the caller is
      // told, rather than the failure being silent -- same shape as
      // api/sc-ai.js's audited flag.
      const audited = await audit(nextActive ? 'credential_reactivated' : 'credential_deactivated', {
        target: target_id, target_role: target.role, previous_active: target.active,
        new_active: nextActive, reason: reason || null, remaining_admins: remaining
      });

      res.status(200).json({ ok: true, employee_id: target_id, active: nextActive, remaining_admins: remaining, audited: audited });
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
