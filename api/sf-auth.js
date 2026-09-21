// api/sf-auth.js
// ---------------------------------------------------------------------------
// SAIRNfreedom per-employee credentials. The SEVENTEENTH app to get one, and
// it had NO employee auth at all until today.
//
// ── WHY IT WAS BUILT NOW ──────────────────────────────────────────────────
// Measured 2026-09-21 while building the cross-tenant isolation arms:
// api/sd-data.js's SF_RESOURCES dispatcher serves 35 resources, THREE of them
// Tier A -- sf_accounts, sf_ledger, sf_vendor_prices -- and NEITHER its read
// branch nor its write branch carried a session check of any kind. The licence
// key was the entire authorisation, and the licence key is shipped to the
// browser and readable by anyone who can open the app. Same shape law_trusttx
// had until 2026-09-16; SAIRNfreedom was not swept with it.
//
// THE TENANT BOUNDARY WAS NEVER THE PROBLEM AND IS ASSERTED --
// api/sd-data-cross-tenant-dispatchers.test.js drives all three and they filter
// by license_hash correctly, so one post cannot read another's ledger. This is
// identity WITHIN a post: today the answer to "who may read this general
// ledger" is "anyone holding the licence key", with no employee identity and no
// role. Plus the audit half, which never shows up as a refusal -- a write with
// no session has no employee_id to record, so the ledger cannot say who made an
// entry, which is the first question an audit asks.
//
// ── THE ROLES ARE CAPABILITY IDS, AND THEY ARE THE APP'S OWN ──────────────
// sairn-employee-auth-scaffold says the per-app role vocabulary is an explicit
// judgment call every time and never a silent copy. SAIRNfreedom had already
// made that call, written it down and justified it, so this LIFTS it rather
// than deciding again -- sairnfreedom.html's CAPABILITIES array, under its own
// comment: "Capabilities are the enum. Officer titles are display, mapped per
// org type."
//
// A GENERIC owner/admin/staff LIST WOULD HAVE BEEN ACTIVELY WRONG HERE. A VFW
// finance officer is the Quartermaster; an Elks one is the Treasurer; a Moose
// post is governed by a Governor and a Legion post by a Commander. The app maps
// five org types onto one stable capability set precisely because, in its own
// words, "hardcoding one vocabulary would be wrong for three of the five target
// orders". The capability id is the stable thing and the title is display.
//
// ── PROVISIONING AND THE SOLE CAPABILITY ──────────────────────────────────
// PROVISIONING_ROLES is post.govern and post.govern.deputy, taken from the
// app's own PROVISIONING_CAPS rather than chosen here. post.govern carries
// `sole:true` in CAPABILITIES -- one per post -- and that is what the
// last-governor refusal in set_active keys on. Note it keys on the SOLE
// capability, not on the whole provisioning list: a post may have a deputy, and
// deactivating a deputy while a governor is in place is ordinary business.
//
// ── MODELLED ON api/rf-auth.js ────────────────────────────────────────────
// Generation 2, the only endpoint with BOTH whoami and set_active, and the only
// one that re-checks caller-active in `setup` as well as roster/set_active.
// Deliberately NOT modelled on sd-auth.js (the ancestor whose own header has
// drifted from its code) or sc-auth.js (which states the reason for
// PROVISIONING_ROLES and then uses literals in its own gates anyway).
//
// All actions are POST, licence key via Authorization: Bearer, employee session
// via X-SD-Auth:
//
//   check_license  {}
//   whoami         {}                                          (session)
//   bootstrap      { employee_id, display_name, pin }  -> role 'post.govern'
//   login          { employee_id, pin }   -> { ok, token, role, employee_id }
//   setup          { employee_id, display_name, pin, role }    (provisioning)
//   roster         {}                                          (management)
//   set_active     { employee_id, active, reason }             (provisioning)
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SD_AUTH_SECRET.
// REQUIRES sql/sairnfreedom_employee_auth_schema.sql to have been run.
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const {
  hashPin, verifyPin, signSessionToken, verifySessionToken, tokenFromRequest,
  ROLES_BY_APP
} = require('./_lib/auth');

const APP = 'sairnfreedom';
const TABLE = 'sairnfreedom_employee_auth';
const SF_ROLES = ROLES_BY_APP[APP];
const LOCKOUT_THRESHOLD = 5;
const LOCKOUT_MINUTES = 15;
const ACTIONS = ['check_license', 'whoami', 'bootstrap', 'login', 'setup', 'roster', 'set_active'];

// ── THE THREE TIERS, AND WHY THEY ARE THE APP'S OWN SPLIT ────────────────
// PROVISIONING mirrors sairnfreedom.html's PROVISIONING_CAPS exactly. The
// deputy is included because a post whose only governance credential is the
// governor is a post that cannot add anyone while the governor is away -- and
// the deputy capability exists in the app precisely to carry that.
const PROVISIONING_ROLES = ['post.govern', 'post.govern.deputy'];
// Who may READ the credential roster. The same two: the roster is not post
// data, it is the access-control surface itself, and the finance officer
// having the ledger does not make the roster theirs. Same reasoning
// api/sc-auth.js records for excluding its `auditor` role.
const MANAGEMENT_ROLES = { 'post.govern': true, 'post.govern.deputy': true };
// The SOLE capability -- one per post, from CAPABILITIES' `sole:true`. This is
// what the last-governor guard counts, NOT the provisioning list, because a
// deputy is not a substitute for the governor in the bootstrap-trapdoor sense.
const SOLE_ROLE = 'post.govern';
const BOOTSTRAP_ROLE = SOLE_ROLE;

// Exported so gates elsewhere import these rather than re-listing capability
// ids. Re-listing is the drift that cost SAIRNsenior a real bug on 2026-08-20.
module.exports.PROVISIONING_ROLES = PROVISIONING_ROLES;
module.exports.MANAGEMENT_ROLES = MANAGEMENT_ROLES;
module.exports.SOLE_ROLE = SOLE_ROLE;
module.exports.EMPLOYEE_TABLE = TABLE;

module.exports = Object.assign(async (req, res) => {
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

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY || !process.env.SD_AUTH_SECRET) {
    console.error('sf-auth: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  // THE ENVELOPE GATE SITS BELOW LICENCE VALIDATION, matching the 2026-09-08
  // reordering of the other fifteen. Above it, a caller holding no credential
  // could tell malformed JSON from a valid envelope with a bad action from a
  // bad licence -- three distinguishable answers, and the action refusal named
  // the whole verb vocabulary.
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

  // check_license short-circuits BEFORE licHash/headers exist, so the licence
  // screen can confirm a key before storing it. Without it a bad licence key
  // gets misattributed to a wrong PIN and the post chases the wrong problem.
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
    // Conditioned on EITHER field, not just the counter. sc and sd test only
    // failed_attempts, so a post-lockout success leaves a stale locked_until in
    // the row permanently -- harmless today because the check is > Date.now(),
    // and real divergent stored state. rf and law get this right; so does this.
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
      // Returns the role from the DATABASE ROW, not from the token, so a role
      // change via setup takes effect on the next call rather than waiting out
      // the token's 12h life. loadEmployee filters active=eq.true, so a
      // deactivated credential's still-valid token fails here too -- which is
      // the whole reason this action exists.
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
      // ── THE TRAPDOOR. DELIBERATELY DOES NOT FILTER ON active. ─────────────
      // This is the single most important decision in the whole pattern and it
      // is a trade, not an oversight. A licence whose only credential has been
      // deactivated must NOT become re-bootstrappable: that would let anyone
      // holding the licence key deactivate their way to a fresh governor
      // account and seize the post. The cost is that such a licence is dead
      // through the API and recoverable only by direct database access -- which
      // is exactly how SD-AUDIT-2026 was lost. The protection against that
      // lockout is the last-governor refusal in set_active, NOT a softer
      // bootstrap. Do not add &active=eq.true here.
      const existing = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&select=id&limit=1'), { headers });
      const existingRows = await existing.json();
      if (!existing.ok) return upstream(res, existingRows);
      if (Array.isArray(existingRows) && existingRows.length > 0) {
        res.status(409).json({ error: { code: 'ALREADY_PROVISIONED', message: 'This post already has employee credentials set up — sign in instead.' } });
        return;
      }
      const { pin_hash, pin_salt } = hashPin(pin);
      const r = await fetch(rest(TABLE), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, employee_id, display_name: body.display_name || employee_id,
          role: BOOTSTRAP_ROLE, pin_hash, pin_salt, active: true
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const token = signSessionToken({ employee_id, role: BOOTSTRAP_ROLE, license_hash: licHash, app: APP });
      res.status(200).json({ ok: true, token, role: BOOTSTRAP_ROLE, employee_id });
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

      // The lock check PRECEDES verifyPin and returns immediately. A locked
      // account never reaches the hash comparison.
      if (isLocked(row)) {
        res.status(429).json({ error: { code: 'LOCKED', message: 'Too many failed attempts — try again later' } });
        return;
      }

      // verifyPin runs a full scrypt against a dummy salt even when no row was
      // found (api/_lib/auth.js's DUMMY_SALT_FOR_TIMING), so employee_id
      // existence cannot be timed. From a real 2026-08-03 auditor finding: the
      // original short-circuited, so a real id took milliseconds to reject and
      // an unknown one returned in under one. Never "optimise" this back.
      const pinOk = row ? verifyPin(pin, row.pin_hash, row.pin_salt) : verifyPin(pin, null, null);
      if (!pinOk) {
        // Increments only against a row that EXISTS. An attempt at an unknown
        // employee_id writes nothing; the timing equalisation above is what
        // hides that, not the counter.
        await recordFailure(row);
        // ONE generic failure. Never tell the caller which half was wrong.
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
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only the post governance officers can provision employee credentials' } });
        return;
      }
      // CALLER-STILL-ACTIVE, in setup as well as roster and set_active. Only rf
      // does this among the sixteen, and it is right: a session outlives its own
      // credential's deactivation by up to 12h, so without it a just-deactivated
      // governor can still mint credentials for half a day.
      const callerRow = await loadEmployee(caller.employee_id);
      if (!callerRow) {
        res.status(403).json({ error: { code: 'CREDENTIAL_INACTIVE', message: 'This credential has been deactivated. Sign in again with an active account.' } });
        return;
      }
      const employee_id = String(body.employee_id || '').trim();
      const pin = String(body.pin || '').trim();
      const role = body.role;
      if (!employee_id || employee_id.length > 128 || !/^\d{6,8}$/.test(pin) || SF_ROLES.indexOf(role) === -1) {
        res.status(400).json({ error: { message: 'employee_id (max 128 chars), a 6-8 digit pin, and a valid capability (' + SF_ROLES.join('|') + ') are required' } });
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
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only the post governance officers can view the credential roster' } });
        return;
      }
      // INCLUDES INACTIVE ROWS on purpose: set_active can reactivate, and a
      // governor has to be able to SEE a deactivated person in order to turn
      // them back on. StoneDesk originally filtered active=eq.true and flipped
      // it on 2026-08-23 for exactly this reason. Never returns pin_hash,
      // pin_salt, failed_attempts or locked_until.
      const r = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) +
        '&select=employee_id,display_name,role,active&order=employee_id.asc'), { headers });
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

    if (action === 'set_active') {
      // ── GUARD ORDERING IS COPIED EXACTLY AND THE ORDER IS LOAD-BEARING ───
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || PROVISIONING_ROLES.indexOf(caller.role) === -1) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only the post governance officers can activate or deactivate a credential' } });
        return;
      }

      const target_id = String(body.employee_id || '').trim();
      const nextActive = body.active === true;
      const reason = String(body.reason || '').trim();
      if (!target_id) { res.status(400).json({ error: { message: 'employee_id is required' } }); return; }
      if (typeof body.active !== 'boolean') { res.status(400).json({ error: { message: 'active must be true or false' } }); return; }
      // Required to switch someone OFF, not on. Reactivating is self-explanatory
      // and always safe; a deactivation is what somebody reconstructs later.
      if (!nextActive && !reason) {
        res.status(400).json({ error: { message: 'reason is required when deactivating a credential' } });
        return;
      }
      if (reason.length > 500) { res.status(400).json({ error: { message: 'reason max 500 characters' } }); return; }

      // SELF-DEACTIVATION REFUSAL BEFORE THE ROSTER READ, deliberately: an
      // already-deactivated caller deactivating themselves gets
      // SELF_DEACTIVATE, not CREDENTIAL_INACTIVE. It is the likeliest
      // accidental route to a licence with zero active governors.
      if (!nextActive && target_id === caller.employee_id) {
        res.status(409).json({ error: { code: 'SELF_DEACTIVATE', message: 'You cannot deactivate your own credential. Ask another governance officer to do it.' } });
        return;
      }

      // ONE roster read, and every decision below comes off it -- never off
      // what the client claimed about the target or about who else exists.
      const allR = await fetch(rest(TABLE + '?license_hash=eq.' + enc(licHash) + '&select=employee_id,role,active'), { headers });
      const all = await allR.json();
      if (!allR.ok) return upstream(res, all);
      const rowsAll = Array.isArray(all) ? all : [];

      // Caller-still-active, computed off that same read. Costs no extra query.
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

      // ── THE LAST-GOVERNOR GUARD, AND IT COUNTS THE SOLE CAPABILITY ───────
      // NOT the provisioning list. post.govern carries `sole:true` in the app's
      // CAPABILITIES and is one per post; post.govern.deputy is not a
      // substitute for it in the bootstrap-trapdoor sense, so deactivating a
      // deputy while a governor is in place is ordinary business and is
      // allowed. This is the one place SAIRNfreedom's guard differs from rf's,
      // and it differs because the app's own capability model differs.
      //
      // bootstrap refuses once ANY row exists and does not filter on active, so
      // a licence with zero active governors cannot log in, cannot run setup,
      // and cannot re-bootstrap -- dead through the API, recoverable only by
      // direct database access. That is exactly how SD-AUDIT-2026 was lost.
      //
      // QUARANTINED, NOT DEAD. It is currently unreachable while the
      // caller-still-active check above stands AND the caller is themselves a
      // governor -- but a DEPUTY caller can reach it, because a deputy
      // deactivating the sole governor satisfies every condition. That makes it
      // live here in a way it is not in rf, which has one provisioning role.
      // Keep it.
      const activeGovernors = rowsAll.filter(function (x) {
        return x.active === true && x.role === SOLE_ROLE;
      });
      if (!nextActive && target.role === SOLE_ROLE && target.active === true && activeGovernors.length <= 1) {
        res.status(409).json({
          error: {
            code: 'LAST_OWNER',
            message: 'This is the only active governing officer on this license. Deactivating it would lock everyone out with no way back in through the app. Appoint another first.'
          }
        });
        return;
      }

      if (target.active === nextActive) {
        res.status(200).json({ ok: true, employee_id: target_id, active: nextActive, unchanged: true, remaining_owners: activeGovernors.length });
        return;
      }

      const patchR = await patchEmployee(target_id, { active: nextActive });
      // PostgREST answers a PATCH with 204 No Content unless Prefer:
      // return=representation is set, and patchEmployee deliberately does not
      // set it. Parsing the body unconditionally THREW on success in rf, the
      // outer catch turned it into a 502, and the caller saw a failure for a
      // mutation that had already landed -- proven live 2026-08-27. Only parse
      // when there is an error to read.
      if (!patchR.ok) { const detail = await patchR.json().catch(function () { return null; }); return upstream(res, detail); }

      const remaining = rowsAll.filter(function (x) {
        var isActive = (x.employee_id === target_id) ? nextActive : x.active === true;
        return isActive && x.role === SOLE_ROLE;
      }).length;

      // NO AUDIT LOG, stated rather than silently absent: api/_lib/audit.js
      // allowlists sairnlaw, sairncode and stonedesk only, so SAIRNfreedom
      // cannot audit today. Saying so beats letting silence read as coverage.
      // `audited: false` is reported on the SUCCESS path here; the NOT_FOUND
      // and unchanged branches above carry no audited key, which is the same
      // honest limit sc and sd record about their own.
      res.status(200).json({ ok: true, employee_id: target_id, active: nextActive, remaining_owners: remaining, audited: false });
      return;
    }
  } catch (err) {
    if (err && err.notProvisioned) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNfreedom employee accounts are not set up yet — run sql/sairnfreedom_employee_auth_schema.sql in Supabase first.' } });
      return;
    }
    console.error('api/sf-auth error:', err);
    res.status(502).json({ error: { message: 'Upstream error — try again' } });
    return;
  }
}, {
  PROVISIONING_ROLES: PROVISIONING_ROLES,
  MANAGEMENT_ROLES: MANAGEMENT_ROLES,
  SOLE_ROLE: SOLE_ROLE,
  EMPLOYEE_TABLE: TABLE
});

// NOT_PROVISIONED and NOT_GRANTED are distinguished rather than collapsed into
// one 502. sd and sc have a two-line upstream() stub, so a missing migration
// and a missing grant both surface as an unactionable 502 -- the difference
// between a five-second fix and an hour of guessing. A missing grant is a 42501
// that looks like nothing else.
function isMissingTable(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('PGRST205') !== -1 || s.indexOf('does not exist') !== -1;
}
function isPermissionDenied(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('42501') !== -1 || s.indexOf('permission denied') !== -1;
}
function upstream(res, detail) {
  console.error('sf-auth upstream error:', detail);
  if (isMissingTable(detail)) {
    res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNfreedom employee accounts are not set up yet — run sql/sairnfreedom_employee_auth_schema.sql in Supabase first.' } });
    return;
  }
  if (isPermissionDenied(detail)) {
    res.status(503).json({ error: { code: 'NOT_GRANTED', message: 'The SAIRNfreedom credential table exists but the server role lacks privileges on it — re-run the grants at the foot of sql/sairnfreedom_employee_auth_schema.sql.' } });
    return;
  }
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}
