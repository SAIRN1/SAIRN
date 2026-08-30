// api/dnt-auth.js
// ---------------------------------------------------------------------------
// SAIRNdental per-employee login, lockout, and credential lifecycle.
//
// EMERGENCY BUILD 2026-08-27 -- SAIRNdental shipped with a client-only PIN
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
// ROLE MODEL -- taken from the app's OWN existing vocabulary, not invented.
// sairndental.html already used owner / frontdesk / provider as the three keys
// of its client-side PIN object; this build reuses those exact three names so
// no practice has to relearn anything and no unused permission surface is
// created.
//   owner     -- principal dentist / practice owner. The ONLY role that can
//                provision or change credentials.
//   frontdesk -- scheduling, check-in, payments, patient contact details.
//   provider  -- treating clinician.
//
// NO FOURTH ROLE. There is no billing-only screen in this app, and adding a
// role with no feature behind it is a permission surface with nothing to
// permit. If a billing role is wanted later it goes in ROLES_BY_APP and into
// one tier below -- the gates key on TIER, not on literal role strings.
//
// VISIBILITY TIERS -- three now, not two (2026-08-27)
//   MANAGEMENT   owner              -- provisioning, AND the provider roster
//   FINANCIAL    owner, frontdesk   -- charges, payments, denial, A/R, revenue,
//                                      coverage rules (READ; write not yet)
//   PATIENT      owner, frontdesk   -- practice-wide patient visibility;
//                                      a provider is scoped to their own
//                                      patients, and sees none until linked
//
// MINIMUM-NECESSARY TIERING -- BOTH HALVES CLOSED 2026-08-27, with one honest
// residual (write). Read this whole note before assuming any of it.
//
// The emergency build made every DNT_RESOURCES call require a VALID SESSION,
// which closed the exploitable gap, but did not narrow what each role may see.
// That was recorded as deferred rather than finished. Since then:
//
//   ✅ FINANCIAL TIER -- DONE (read side). api/sd-data.js DNT_FINANCIAL_ROLES
//      = {owner, frontdesk}; dnt_charges, dnt_payments, dnt_denial, dnt_ar,
//      dnt_revenue and dnt_coverage_rules now 403 for a provider on READ.
//      Write is unchanged and still open to all three roles -- a deliberate,
//      disclosed asymmetry, not an oversight. See that file's own comment.
//
//   ✅ PROVIDER-SCOPED PATIENT READ -- DONE, same day, once the missing link
//      was built. A provider now reads only patients they have an appointment
//      with; dnt_referrals is scoped the same way (it carries patient_id and a
//      clinical reason); dnt_appointments filters in the database on the
//      promoted provider_id column. An UNLINKED provider gets 403
//      PROVIDER_NOT_LINKED -- see-nothing, never see-everything -- with a
//      message naming the Providers panel and the owner as the fix.
//      THE LINK: `linked_employee_id` on the dnt_providers DATA BLOB. No
//      migration; dnt_providers is (license_hash, provider_id, data jsonb).
//      Enforced one-to-one server-side (409 EMPLOYEE_ALREADY_LINKED), because
//      two rows carrying the same link would make scoping depend on row order.
//      THE ROSTER IS NOW AN ACCESS-CONTROL TABLE, so dnt_providers WRITE is
//      owner-only (403 ROLE_NOT_PERMITTED). Read stays open to every
//      authenticated role -- provider NAMES render throughout the app.
//      Providers are DEACTIVATED, never deleted: the old client-side remove was
//      local-only and the next sync merged the row back, so "remove and re-add
//      to fix the link" would have restored the stale row AND minted a duplicate
//      PV- id, orphaning appointment history.
//
//   HISTORICAL, kept because it explains why the link had to be built first and
//   why the obvious filter would have been a silent failure rather than a bug:
//      The decision taken was "a provider sees only their linked patients,"
//      resolved through dnt_appointments.provider_id. That could NOT be
//      implemented directly, and must never be faked:
//        - dnt_providers rows are created client-side as `newId('PV')` ->
//          "PV-xxxxx" (sairndental.html:1022), carrying only name, clinical
//          role and operatory.
//        - An auth employee's `employee_id` is a free-text string chosen at
//          bootstrap/setup, living in sairndental_employee_auth.
//        - NOTHING joins them. dnt_appointments.provider_id references the PV-
//          id, and the client never writes employee_id into any dnt_* record.
//      So a server-side filter of `provider_id === session.employee_id` would
//      match zero rows and hand every provider an empty patient list with a
//      200 OK -- a permission check manufacturing a false empty state, which is
//      worse than the honest authenticated-only read it replaced.
//      WHAT IT NEEDED FIRST, all of which now exists: the link field; a
//      provider EDIT path (this app had none at all -- every roster was
//      add-or-remove only, so an existing provider could not be linked without
//      deleting and re-adding them); an owner-gated link control populated from
//      the `roster` action above; and a fix for the local-only delete. The
//      fallback question was decided by Michael on 2026-08-27: SEE-NOTHING when
//      unlinked, paired with a visible fix path, because an unlinked provider
//      defaulting to practice-wide read is the same shape of gap the tiering
//      pass existed to close.
//
// SAIRNsenior's sen_clients gate is often cited as the worked example. It is
// the right SHAPE and the wrong MECHANISM for this app: it filters on a
// PROMOTED assigned_employee_id column, and dnt_patients has no promoted
// columns at all -- it is (license_hash, patient_id, data jsonb). Do not try to
// port it directly.
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
// REQUIRES sql/sairndental_employee_auth_schema.sql to have been run.
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const {
  hashPin, verifyPin, signSessionToken, verifySessionToken, tokenFromRequest,
  ROLES_BY_APP
} = require('./_lib/auth');

const APP = 'sairndental';
const TABLE = 'sairndental_employee_auth';
const DNT_ROLES = ROLES_BY_APP[APP];
const LOCKOUT_THRESHOLD = 5;
const LOCKOUT_MINUTES = 15;
const ACTIONS = ['check_license', 'whoami', 'bootstrap', 'login', 'setup', 'roster', 'set_active'];


// See the tier note in the header. Exported shape kept deliberately simple so a
// later split of 'estimator' is a one-line change here, not a gate rewrite.
const MANAGEMENT_ROLES = { owner: true };
const AUTHENTICATED_ROLES = { owner: true, frontdesk: true, provider: true };
// Only 'owner' provisions or changes credentials.
//
// CORRECTED 2026-08-29. This comment used to read "'admin' runs the office but
// does not mint identities -- deliberately narrower than StoneDesk, where both
// owner and admin can". SAIRNDENTAL HAS NO 'admin' ROLE. The vocabulary is
// ROLES_BY_APP.sairndental = ['owner','frontdesk','provider']; the sentence was
// carried over from an app that does have one, and it made this look like a
// deliberate narrowing from two provisioning roles to one when it was never
// two. Left as it was, the likeliest outcome was a future reader "restoring" a
// role that never existed here.
//
// The design itself is unchanged and is deliberate: a 20-100 person practice
// has one principal, and the blast radius of a mistaken deactivation is the
// whole company. The real second-role candidates in THIS app are 'frontdesk'
// (the least-trusted and highest-turnover seat) and 'provider' (clinical, and
// the app cannot tell a partner from a locum) -- which is why widening here is
// a harder call than in SAIRNmechanical or SAIRNroofing, both of which already
// carry an 'admin' that could simply be added.
//
// NOT a lockout mitigation, and worth saying so where the list lives: the API
// cannot reach the zero-active-provisioner state. set_active refuses
// self-deactivation, refuses to deactivate the last active provisioner, and
// re-reads that the caller's own row is still active. That state is created
// only by SQL, and is guarded by tools/employee_auth_guard_check.py and
// detected by api/provisioner-health.js.
//
// Full options, costs and the standing recommendation (leave it as-is):
// docs/2026-08-29-sairndental-provisioning-role-decision.md
const PROVISIONING_ROLES = ['owner'];

// Exported so gates elsewhere (api/sd-data.js's DNT_RESOURCES branch) import these
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
    console.error('dnt-auth: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
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
        res.status(409).json({ error: { code: 'ALREADY_PROVISIONED', message: 'This practice already has employee credentials set up — use action:setup instead' } });
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
      if (!employee_id || employee_id.length > 128 || !/^\d{6,8}$/.test(pin) || DNT_ROLES.indexOf(role) === -1) {
        res.status(400).json({ error: { message: 'employee_id (max 128 chars), a 6-8 digit pin, and a valid role (' + DNT_ROLES.join('|') + ') are required' } });
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
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner can view the employee roster' } });
        return;
      }
      // INCLUDES INACTIVE ROWS on purpose: set_active can reactivate, and an
      // owner has to be able to see a deactivated person in order to turn them
      // back on. Never returns pin_hash/pin_salt/failed_attempts/locked_until.
      // Inactive rows INCLUDED deliberately -- once set_active exists an owner
      // show which employees are Tesla-certified when assigning an installer.
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
      // PostgREST answers a PATCH with 204 No Content unless Prefer:
      // return=representation is set, and patchEmployee deliberately does not
      // set it. Parsing the body unconditionally therefore THREW on success,
      // the outer catch turned it into a 502, and the caller saw a failure
      // for a mutation that had already landed. Proven live 2026-08-27: both
      // deactivate and reactivate returned 502 while the row changed
      // correctly underneath. Only parse when there is an error to read.
      if (!patchR.ok) { const detail = await patchR.json().catch(function () { return null; }); return upstream(res, detail); }

      const remaining = rowsAll.filter(function (x) {
        var isActive = (x.employee_id === target_id) ? nextActive : x.active === true;
        return isActive && PROVISIONING_ROLES.indexOf(x.role) !== -1;
      }).length;

      // NO AUDIT LOG YET, stated rather than silently absent: SAIRNdental has
      // no audit table (api/_lib/audit.js allowlists sairnlaw, sairncode and
      // stonedesk only). Adding one is a Phase 4 item alongside the licensing
      // and certification compliance work, where it has more than one event
      // type to carry. Recorded here so it is a known gap, not an oversight.
      res.status(200).json({ ok: true, employee_id: target_id, active: nextActive, remaining_owners: remaining, audited: false });
      return;
    }
  } catch (err) {
    if (err && err.notProvisioned) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNdental employee accounts are not set up yet — run sql/sairndental_employee_auth_schema.sql' } });
      return;
    }
    console.error('api/dnt-auth error:', err);
    res.status(502).json({ error: { message: 'Upstream error — try again' } });
    return;
  }
};

module.exports.MANAGEMENT_ROLES = MANAGEMENT_ROLES;
module.exports.AUTHENTICATED_ROLES = AUTHENTICATED_ROLES;

function isMissingTable(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('PGRST205') !== -1 || s.indexOf('does not exist') !== -1;
}
function isPermissionDenied(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('42501') !== -1 || s.indexOf('permission denied') !== -1;
}
function upstream(res, detail) {
  console.error('dnt-auth upstream error:', detail);
  if (isMissingTable(detail)) {
    res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNdental employee accounts are not set up yet — run sql/sairndental_employee_auth_schema.sql' } });
    return;
  }
  if (isPermissionDenied(detail)) {
    res.status(503).json({ error: { code: 'NOT_GRANTED', message: 'The SAIRNdental tables exist but the server role lacks privileges on them — re-run the GRANT block at the end of sql/sairndental_employee_auth_schema.sql' } });
    return;
  }
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}

// ── Exported for tools/licence_recoverability_check.py via
// api/provisioner-health.js, added 2026-08-29. The trapdoor is a licence with
// credential rows and ZERO rows that are both `active` and hold one of these
// roles. The detector must read THIS list rather than assume 'owner' --
// SAIRNcode's is 'admin' -- so the list is exported instead of duplicated.
module.exports.PROVISIONING_ROLES = PROVISIONING_ROLES;
module.exports.EMPLOYEE_TABLE = TABLE;
