// api/rf-auth.js
// ---------------------------------------------------------------------------
// SAIRNroofing per-employee login, lockout, and credential lifecycle.
//
// Built from ZERO -- SAIRNroofing is a ground-up app with no shared-PIN
// scaffold to replace. Modelled on api/alf-auth.js (SAIRNcare, 2026-08-20),
// which is the newest and cleanest of the family.
//
// TWO DELIBERATE DIFFERENCES FROM EVERY EARLIER APP'S AUTH, both because this
// app is being built AFTER the lessons rather than before them:
//
//   1. set_active SHIPS IN v1. Every other app got its credential lifecycle
//      retrofitted -- StoneDesk and SAIRNcode on 2026-08-23/24, and SAIRNcash's
//      trial equivalent is still an open product decision. Before those, the
//      only way to neutralise a credential was a hand-written SQL DELETE run by
//      a human with Supabase access, which is how three StoneDesk licences were
//      lost (SD-PINNACLE-2026's PIN is still undocumented). This app does not
//      repeat that.
//
//   2. The caller-still-active re-check is present from the first commit.
//      Found live on SAIRNcode 2026-08-24: a session token carries a role claim
//      and stays valid for its full 12h life INCLUDING after the credential
//      behind it is deactivated, so a just-removed admin could keep removing
//      other people. Carried across rather than waiting to rediscover it here.
//
// ROLE MODEL (confirmed by Michael 2026-08-24, not invented):
//   owner      -- principal. The only role that can provision credentials.
//   admin      -- office manager. Broad operational visibility, no provisioning.
//   estimator  -- COMBINED sales-and-estimating, one role on purpose. At 20-100
//                 employees the person who knocks the door, meets the adjuster
//                 on the roof and writes the estimate is usually the same
//                 person. A shop that later wants sales and estimating split is
//                 NOT blocked: the privacy gate keys on TIER (see below), not on
//                 the literal role string, so splitting means adding a role to
//                 ROLES_BY_APP and one line to a tier -- not rebuilding the gate.
//   foreman    -- runs crews on assigned jobs.
//   crew       -- own assigned jobs only.
//
// VISIBILITY TIERS -- the thing that makes the role split cheap to change later.
// Gates elsewhere in the platform (api/sd-data.js's rf_jobs branch, when Phase 4
// builds it) must import these rather than re-listing role names, which is the
// drift that cost SAIRNsenior a real bug on 2026-08-20 when one function used
// senIsManagement() where the rest used senIsBroadRead().
//
//   MANAGEMENT  owner, admin            -- full visibility + reassignment
//   BROAD_READ  owner, admin, estimator -- see every job; estimator needs the
//                                          whole board to quote and to work a
//                                          storm canvass, but cannot reassign
//   NARROW      foreman, crew           -- own assigned jobs only
//
// COMMERCIAL WORK IS FIRST-CLASS, not an edge case (confirmed 2026-08-24). Mid-
// market residential/storm shops pick up commercial projects opportunistically.
// Nothing in this file branches on residential-vs-commercial and nothing should:
// job class is a property of a job, never of an identity. Recorded here because
// the temptation in Phase 4 will be to add a 'commercial_pm' role, and that
// would put job type into the identity model where it does not belong.
//
// All actions are POST, license key via Authorization: Bearer, employee session
// via X-SD-Auth:
//
//   check_license  {}
//   whoami         {}                                            (session)
//   bootstrap      { employee_id, display_name, pin }   -> role 'owner'
//   login          { employee_id, pin }    -> { ok, token, role, employee_id }
//   setup          { employee_id, display_name, pin, role }      (owner)
//   roster         {}                                            (management)
//   set_active     { employee_id, active, reason }               (owner)
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SD_AUTH_SECRET.
// REQUIRES sql/sairnroofing_employee_auth_schema.sql to have been run.
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const {
  hashPin, verifyPin, signSessionToken, verifySessionToken, tokenFromRequest,
  ROLES_BY_APP
} = require('./_lib/auth');

const APP = 'sairnroofing';
const TABLE = 'sairnroofing_employee_auth';
const RF_ROLES = ROLES_BY_APP[APP];
const LOCKOUT_THRESHOLD = 5;
const LOCKOUT_MINUTES = 15;
const ACTIONS = ['check_license', 'whoami', 'bootstrap', 'login', 'setup', 'roster', 'set_active', 'set_certifications'];

// Phase 2, Tesla Solar Roof capability gate (scope doc sec.3). Deliberately
// one key today -- see sql/sairnroofing_employee_auth_certifications_
// migration.sql's header for why the column is a small jsonb bag rather
// than a dedicated boolean, and why the other manufacturer programmes
// named in the scope doc are NOT being added here.
const KNOWN_CERTIFICATION_KEYS = { tesla_certified: true };

// See the tier note in the header. Exported shape kept deliberately simple so a
// later split of 'estimator' is a one-line change here, not a gate rewrite.
const MANAGEMENT_ROLES = { owner: true, admin: true };
const BROAD_READ_ROLES = { owner: true, admin: true, estimator: true };
// Only 'owner' provisions or changes credentials. 'admin' runs the office but
// does not mint identities -- deliberately narrower than StoneDesk, where both
// owner and admin can, because a 20-100 person shop has one principal and the
// blast radius of a mistaken deactivation is the whole company.
const PROVISIONING_ROLES = ['owner'];

// Exported so gates elsewhere (api/sd-data.js's rf_jobs branch) import these
// rather than re-listing role names -- see the header note on why that drift
// is the exact bug class this app is built to avoid from the start.
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
    console.error('rf-auth: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
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
      // loadEmployee filters active=eq.true, so a deactivated credential's
      // still-valid token correctly fails here too.
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
      // Deliberately does NOT filter on active. A licence whose only credential
      // has been deactivated must not become re-bootstrappable: that would let
      // anyone holding the licence key deactivate their way to a fresh owner
      // account and seize the shop. Recovery goes through another owner, or a
      // scoped SQL reset. Same decision as api/sc-auth.js and api/sd-auth.js.
      const existing = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&select=id&limit=1'), { headers });
      const existingRows = await existing.json();
      if (!existing.ok) return upstream(res, existingRows);
      if (Array.isArray(existingRows) && existingRows.length > 0) {
        res.status(409).json({ error: { code: 'ALREADY_PROVISIONED', message: 'This company already has employee credentials set up — use action:setup instead' } });
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

      // verifyPin runs at equal cost whether the row exists or not (see
      // api/_lib/auth.js's DUMMY_SALT_FOR_TIMING) so employee_id existence
      // cannot be timed. The same generic error is returned either way.
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
      if (!caller || PROVISIONING_ROLES.indexOf(caller.role) === -1) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner can provision employee credentials' } });
        return;
      }
      // The caller must still be ACTIVE, not merely holding a token that says
      // 'owner'. See the header note -- a session outlives its own credential's
      // deactivation by up to 12h.
      const callerRow = await loadEmployee(caller.employee_id);
      if (!callerRow) {
        res.status(403).json({ error: { code: 'CREDENTIAL_INACTIVE', message: 'This credential has been deactivated. Sign in again with an active account.' } });
        return;
      }
      const employee_id = String(body.employee_id || '').trim();
      const pin = String(body.pin || '').trim();
      const role = body.role;
      if (!employee_id || employee_id.length > 128 || !/^\d{6,8}$/.test(pin) || RF_ROLES.indexOf(role) === -1) {
        res.status(400).json({ error: { message: 'employee_id (max 128 chars), a 6-8 digit pin, and a valid role (' + RF_ROLES.join('|') + ') are required' } });
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

    if (action === 'roster') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || !MANAGEMENT_ROLES[caller.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner or Office Manager can view the employee roster' } });
        return;
      }
      // INCLUDES INACTIVE ROWS on purpose: set_active can reactivate, and an
      // owner has to be able to see a deactivated person in order to turn them
      // back on. Never returns pin_hash/pin_salt/failed_attempts/locked_until.
      // certifications included (2026-08-24, Phase 2) so the Estimate tab can
      // show which employees are Tesla-certified when assigning an installer.
      const r = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) +
        '&select=employee_id,display_name,role,active,certifications&order=employee_id.asc'), { headers });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const callerRow = (rows || []).filter(function (x) { return x.employee_id === caller.employee_id; })[0];
      if (!callerRow || callerRow.active !== true) {
        res.status(403).json({ error: { code: 'CREDENTIAL_INACTIVE', message: 'This credential has been deactivated. Sign in again with an active account.' } });
        return;
      }
      res.status(200).json({ ok: true, employees: rows || [] });
      return;
    }

    // ── set_certifications: Tesla Solar Roof capability gate (2026-08-24, Phase 2) ──
    // Owner-only, same provisioning gate as setup/set_active -- deliberately NOT
    // folded into setup, which requires a pin and full role and would force a
    // credential change just to flip a certification flag. Only known keys are
    // ever accepted, so this can never become a free-form data store for
    // arbitrary client-supplied jsonb.
    if (action === 'set_certifications') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || PROVISIONING_ROLES.indexOf(caller.role) === -1) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner can set employee certifications' } });
        return;
      }
      const callerRow = await loadEmployee(caller.employee_id);
      if (!callerRow) {
        res.status(403).json({ error: { code: 'CREDENTIAL_INACTIVE', message: 'This credential has been deactivated. Sign in again with an active account.' } });
        return;
      }
      const target_id = String(body.employee_id || '').trim();
      if (!target_id) { res.status(400).json({ error: { message: 'employee_id is required' } }); return; }
      const incoming = body.certifications;
      if (!incoming || typeof incoming !== 'object' || Array.isArray(incoming)) {
        res.status(400).json({ error: { message: 'certifications must be an object' } });
        return;
      }
      const cleaned = {};
      for (const key of Object.keys(incoming)) {
        if (!KNOWN_CERTIFICATION_KEYS[key]) {
          res.status(400).json({ error: { message: 'Unknown certification key: ' + key } });
          return;
        }
        if (typeof incoming[key] !== 'boolean') {
          res.status(400).json({ error: { message: 'certifications.' + key + ' must be true or false' } });
          return;
        }
        cleaned[key] = incoming[key];
      }
      const existing = await loadEmployee(target_id);
      if (!existing) { res.status(404).json({ error: { code: 'NOT_FOUND', message: 'No such employee on this license' } }); return; }
      const patchR = await patchEmployee(target_id, { certifications: cleaned });
      const patched = await patchR.json();
      if (!patchR.ok) return upstream(res, patched);
      res.status(200).json({ ok: true, employee_id: target_id, certifications: cleaned });
      return;
    }

    // ── set_active: the credential lifecycle, shipped in v1 ──
    // Deactivation, NEVER deletion. login/whoami/loadEmployee all filter
    // active=eq.true, so the flag is enforced the moment it is written. Keeping
    // the row preserves created_at, role history, and any later audit linkage;
    // deleting is what made three StoneDesk licences unrecoverable.
    if (action === 'set_active') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || PROVISIONING_ROLES.indexOf(caller.role) === -1) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner can activate or deactivate a credential' } });
        return;
      }

      const target_id = String(body.employee_id || '').trim();
      const nextActive = body.active === true;
      const reason = String(body.reason || '').trim();
      if (!target_id) { res.status(400).json({ error: { message: 'employee_id is required' } }); return; }
      if (typeof body.active !== 'boolean') { res.status(400).json({ error: { message: 'active must be true or false' } }); return; }
      // Required to switch someone OFF, not on. Reactivating is self-explanatory
      // and always safe; a deactivation is what someone reconstructs later.
      if (!nextActive && !reason) {
        res.status(400).json({ error: { message: 'reason is required when deactivating a credential' } });
        return;
      }
      if (reason.length > 500) { res.status(400).json({ error: { message: 'reason max 500 characters' } }); return; }

      // No self-deactivation. It is the likeliest accidental route to a licence
      // with zero active owners, and there is no legitimate reason to do it to
      // yourself rather than have another owner do it.
      if (!nextActive && target_id === caller.employee_id) {
        res.status(409).json({ error: { code: 'SELF_DEACTIVATE', message: 'You cannot deactivate your own credential. Ask another Owner to do it.' } });
        return;
      }

      // Read the real roster ONCE and decide from it -- never from what the
      // client claimed about the target or about who else exists.
      const allR = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&select=employee_id,role,active'), { headers });
      const all = await allR.json();
      if (!allR.ok) return upstream(res, all);
      const rowsAll = Array.isArray(all) ? all : [];

      const callerRow = rowsAll.filter(function (x) { return x.employee_id === caller.employee_id; })[0];
      if (!callerRow || callerRow.active !== true) {
        res.status(403).json({ error: { code: 'CREDENTIAL_INACTIVE', message: 'This credential has been deactivated. Sign in again with an active account.' } });
        return;
      }

      const target = rowsAll.filter(function (x) { return x.employee_id === target_id; })[0];
      if (!target) {
        res.status(404).json({ error: { code: 'NOT_FOUND', message: 'No such employee on this license' } });
        return;
      }

      const activeOwners = rowsAll.filter(function (x) {
        return x.active === true && PROVISIONING_ROLES.indexOf(x.role) !== -1;
      });
      // LAST_OWNER guard. bootstrap refuses once ANY row exists and does not
      // filter on active (see that branch), so a licence with zero active owners
      // cannot log in, cannot run setup, and cannot re-bootstrap -- dead through
      // the API, recoverable only by direct database access. That is exactly how
      // SD-AUDIT-2026 was lost.
      //
      // Currently unreachable by construction while the caller-still-active
      // check above stands: an active owner caller plus a DIFFERENT active owner
      // target implies at least two. Kept and quarantined deliberately --
      // reachability is a property of today's rule set, and widening
      // PROVISIONING_ROLES or adding any path that skips the active re-check
      // makes it live again. Same reasoning recorded in api/sc-auth.js.
      if (!nextActive && PROVISIONING_ROLES.indexOf(target.role) !== -1 && target.active === true && activeOwners.length <= 1) {
        res.status(409).json({
          error: {
            code: 'LAST_OWNER',
            message: 'This is the only active Owner on this license. Deactivating it would lock everyone out with no way back in through the app — provision another Owner first, then retry.'
          }
        });
        return;
      }

      if (target.active === nextActive) {
        res.status(200).json({ ok: true, employee_id: target_id, active: nextActive, unchanged: true, remaining_owners: activeOwners.length });
        return;
      }

      const patchR = await patchEmployee(target_id, { active: nextActive });
      const patched = await patchR.json();
      if (!patchR.ok) return upstream(res, patched);

      const remaining = rowsAll.filter(function (x) {
        var isActive = (x.employee_id === target_id) ? nextActive : x.active === true;
        return isActive && PROVISIONING_ROLES.indexOf(x.role) !== -1;
      }).length;

      // NO AUDIT LOG YET, stated rather than silently absent: SAIRNroofing has
      // no audit table (api/_lib/audit.js allowlists sairnlaw, sairncode and
      // stonedesk only). Adding one is a Phase 4 item alongside the licensing
      // and certification compliance work, where it has more than one event
      // type to carry. Recorded here so it is a known gap, not an oversight.
      res.status(200).json({ ok: true, employee_id: target_id, active: nextActive, remaining_owners: remaining, audited: false });
      return;
    }
  } catch (err) {
    if (err && err.notProvisioned) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNroofing employee accounts are not set up yet — run sql/sairnroofing_employee_auth_schema.sql' } });
      return;
    }
    console.error('api/rf-auth error:', err);
    res.status(502).json({ error: { message: 'Upstream error — try again' } });
    return;
  }
};

module.exports.MANAGEMENT_ROLES = MANAGEMENT_ROLES;
module.exports.BROAD_READ_ROLES = BROAD_READ_ROLES;

function isMissingTable(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('PGRST205') !== -1 || s.indexOf('does not exist') !== -1;
}
function isPermissionDenied(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('42501') !== -1 || s.indexOf('permission denied') !== -1;
}
function upstream(res, detail) {
  console.error('rf-auth upstream error:', detail);
  if (isMissingTable(detail)) {
    res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNroofing employee accounts are not set up yet — run sql/sairnroofing_employee_auth_schema.sql' } });
    return;
  }
  if (isPermissionDenied(detail)) {
    res.status(503).json({ error: { code: 'NOT_GRANTED', message: 'The SAIRNroofing tables exist but the server role lacks privileges on them — re-run the GRANT block at the end of sql/sairnroofing_employee_auth_schema.sql' } });
    return;
  }
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}
