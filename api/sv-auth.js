// api/sv-auth.js
// ---------------------------------------------------------------------------
// SAIRNvet per-employee login, lockout, and credential lifecycle.
//
// THE SIXTEENTH AND LAST APP TO GET THIS, AND IT WAS BUILT OUT OF TURN.
// Fifteen apps already shipped api/*-auth.js and `sv` was not among them;
// `grep -rln "sv_employee_auth" sql/ api/` returned nothing. Until today
// SAIRNvet authenticated on the LICENCE KEY ONLY, which sairnvet.html states
// itself at :2011 -- "`role` is a self-selected dropdown, never
// server-verified."
//
// WHY THAT MATTERED MORE HERE THAN ANYWHERE ELSE. This app holds
// `sv_controlled`, which api/_resources/sairnvet.js calls "the
// controlled-substance register (DEA-relevant)", and `sv_audit_log`, its
// dosing trail. `python tools/removal_path_check.py --burn-down` ranks
// sv_controlled TIER A WITH NO REMOVAL PATH -- a wrong row cannot be taken
// back through the product at all. So the one app whose sharpest record is
// legally permanent was the one that knew which PRACTICE was writing and never
// which PERSON.
//
// Found 2026-09-13 while scoping the irreversible-write witnessing lock
// (docs/2026-09-13-irreversible-write-witnessing-scoping.md), where this is
// the stated hard prerequisite rather than a detail: a lock that records "the
// practice confirmed it" is theatre. THIS FILE EXISTS SO THAT LOCK CAN BE
// HONEST.
//
// Modelled on api/rf-auth.js (SAIRNroofing), which is the only endpoint in the
// family with both `whoami` and `set_active` and the only one that re-checks
// caller-active in `setup` as well. Every one of those is carried here rather
// than rediscovered.
//
// ROLE MODEL -- the app's own vocabulary, read out of sairnvet.html's staff
// roster dropdown (:1365 and :6887) rather than invented:
//
//   owner      -- Owner/DVM. Principal, and the ONLY provisioning role.
//   dvm        -- Associate DVM. A licensed veterinarian.
//   tech       -- Veterinary Technician (CVT/RVT/LVT by state).
//   assistant  -- Veterinary Assistant.
//   manager    -- Practice Manager. Runs the office; NOT a clinician.
//   frontdesk  -- Front Desk / reception.
//
// The roster's seventh option, 'Other', is deliberately not a role -- see
// api/_lib/auth.js's ROLES_BY_APP.sairnvet for why.
//
// TIERS -- exported so gates elsewhere import them instead of re-listing role
// names, which is the drift that cost SAIRNsenior a real bug on 2026-08-20.
//
//   PROVISIONING  owner                 -- mints and deactivates credentials
//   MANAGEMENT    owner, manager        -- may read the credential roster
//   PRESCRIBER    owner, dvm            -- THE LICENSED-PRACTITIONER TIER
//
// PRESCRIBER_ROLES IS NOT COSMETIC AND IS NOT A UI HINT. A controlled-substance
// entry is a legal act by a licensed veterinarian, so the witnessing lock on
// sv_controlled must key on this tier and not on a role string it re-lists. It
// is exported for exactly that, the same way rf-auth.js exports its tiers.
// Deliberately EXCLUDES 'manager': a Practice Manager runs the office and is
// not a clinician, and conflating the two is how a non-veterinarian ends up
// recorded as the author of a DEA-relevant row.
//
// WIRE FORMAT: `LAST_ADMIN` / `remaining_admins`, because `roster` and
// `set_active` go through api/_lib/employee-lifecycle.js and that is the
// spelling it emits. CORRECTED 2026-09-13, and the correction is the point:
// this header said `LAST_OWNER` / `remaining_owners` while the file was
// hand-written off api/rf-auth.js, and WIRING IT ONTO THE SHARED HELPER
// CHANGED THE WIRE FORMAT without changing the sentence describing it. The
// platform has two spellings, a client written against one breaks against the
// other, and a header that describes the version before last is how that
// breakage gets shipped. Read the helper, not this line, if they ever
// disagree again.
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
// REQUIRES sql/sairnvet_employee_auth_schema.sql to have been run.
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const lifecycle = require('./_lib/employee-lifecycle');
const {
  hashPin, verifyPin, signSessionToken, verifySessionToken, tokenFromRequest,
  ROLES_BY_APP
} = require('./_lib/auth');

const APP = 'sairnvet';
const TABLE = 'sairnvet_employee_auth';
const SV_ROLES = ROLES_BY_APP[APP];
const LOCKOUT_THRESHOLD = 5;
const LOCKOUT_MINUTES = 15;
const ACTIONS = ['check_license', 'whoami', 'bootstrap', 'login', 'setup', 'roster', 'set_active'];

// Only 'owner' provisions or changes credentials. A veterinary practice has one
// principal, and the blast radius of a mistaken deactivation here includes the
// author of every controlled-substance entry that person has signed.
//
// READ OFF THIS FILE'S OWN `setup` GATE, not assumed, and asserted against it by
// api/_lib/employee-lifecycle-wiring.test.js -- the shared helper takes this as
// a PARAMETER so each app passes its own, and a guard hardcoding 'owner' passes
// clean forever while checking nothing on an app whose list differs
// (SAIRNcode's is 'admin').
const PROVISIONING_ROLES = ['owner'];
const PROVISIONING_LABEL = 'an Owner';
// The credential roster is the access-control surface, not app data -- the same
// reason api/sc-auth.js denies its read-only 'auditor' role. A Practice Manager
// runs the office and legitimately needs it; a DVM does not.
const MANAGEMENT_ROLES = { owner: true, manager: true };
// See the header. The witnessing lock on sv_controlled imports THIS.
const PRESCRIBER_ROLES = { owner: true, dvm: true };

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

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY || !process.env.SD_AUTH_SECRET) {
    console.error('sv-auth: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  // ── THE ENVELOPE GATE SITS BELOW LICENCE VALIDATION, from the first commit ──
  // Body parse and action enum answer AFTER the licence is validated. Above it,
  // a caller holding no credential could distinguish malformed JSON from a
  // valid envelope with a bad action from a bad licence -- three separable
  // answers, and the action refusal would name this app's whole verb
  // vocabulary. Fifteen endpoints were reordered for this on 2026-09-05/08;
  // this one is built that way rather than joining the list.
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

  // Answers before licHash/headers exist, so the licence-entry screen can
  // confirm a key BEFORE storing it. Without this a bad licence key gets
  // misattributed to a wrong PIN and the practice chases the wrong problem.
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
  // Conditioned on EITHER field, not just the counter. sc and sd test only
  // failed_attempts, so a post-lockout success leaves a stale locked_until in
  // the row permanently -- harmless today because the check is `> Date.now()`,
  // and real divergent stored state regardless. rf and law get this right.
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
      // The ROLE COMES FROM THE DATABASE ROW, not from the token, so a role
      // change via setup takes effect on the next call rather than waiting out
      // the token's 12h life. loadEmployee filters active=eq.true, so a
      // deactivated credential's still-valid token correctly fails here too.
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
      // DELIBERATELY DOES NOT FILTER ON active, and this is the single most
      // consequential line in the file. A licence whose only credential has
      // been deactivated must not become re-bootstrappable: that would let
      // anyone holding the licence key deactivate their way to a fresh owner
      // account and seize the practice -- including its controlled-substance
      // register. The cost is real and accepted: a licence with zero active
      // owners is dead through the API and recoverable only by direct database
      // access, which is exactly how SD-AUDIT-2026 was lost. The protection
      // against THAT is the last-owner refusal in set_active, not a softer
      // bootstrap.
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

      // The lock check PRECEDES verifyPin and returns immediately: a locked
      // account never reaches the hash comparison.
      if (isLocked(row)) {
        res.status(429).json({ error: { code: 'LOCKED', message: 'Too many failed attempts — try again later' } });
        return;
      }

      // verifyPin runs a full scrypt against a dummy salt even when no row was
      // found (api/_lib/auth.js's DUMMY_SALT_FOR_TIMING), so employee_id
      // existence cannot be timed. From a real 2026-08-03 finding: without it,
      // a real id took scrypt-milliseconds to reject and an unknown one
      // returned in under one, which enumerates valid ids. Never "optimise"
      // this back. One generic error either way -- never tell the caller which
      // half was wrong.
      const pinOk = row ? verifyPin(pin, row.pin_hash, row.pin_salt) : verifyPin(pin, null, null);
      if (!pinOk) {
        // Increments only against a row that EXISTS. An attempt on an unknown
        // employee_id writes nothing; the timing equalisation above is what
        // hides that, not the counter.
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
      // CALLER MUST STILL BE ACTIVE, not merely holding a token that says
      // 'owner'. A session outlives its own credential's deactivation by up to
      // 12h. Only rf does this in setup among the fifteen -- sc, sd and law
      // block a deactivated owner from roster and set_active and still let
      // them provision. Carried here rather than joining that list.
      const callerRow = await loadEmployee(caller.employee_id);
      if (!callerRow) {
        res.status(403).json({ error: { code: 'CREDENTIAL_INACTIVE', message: 'This credential has been deactivated. Sign in again with an active account.' } });
        return;
      }
      const employee_id = String(body.employee_id || '').trim();
      const pin = String(body.pin || '').trim();
      const role = body.role;
      if (!employee_id || employee_id.length > 128 || !/^\d{6,8}$/.test(pin) || SV_ROLES.indexOf(role) === -1) {
        res.status(400).json({ error: { message: 'employee_id (max 128 chars), a 6-8 digit pin, and a valid role (' + SV_ROLES.join('|') + ') are required' } });
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
      // THE SHARED HELPER, not a seventeenth hand-written copy. It INCLUDES
      // INACTIVE ROWS on purpose -- set_active can reactivate, and an owner has
      // to be able to SEE a deactivated person to turn them back on -- and it
      // never returns pin_hash / pin_salt / failed_attempts / locked_until.
      //
      // canView is DELIBERATELY WIDER THAN provisioningRoles here: a Practice
      // Manager runs the office and legitimately reads the roster, while only
      // an Owner may change it. The credential roster is the access-control
      // surface rather than app data, which is why a DVM is not on this list
      // even though a DVM outranks a manager clinically.
      const out = await lifecycle.roster({
        caller: caller, licHash: licHash, table: TABLE, rest: rest, headers: headers,
        canView: !!(caller && MANAGEMENT_ROLES[caller.role]),
        viewLabel: 'an Owner or Practice Manager'
      });
      if (out.upstream) return upstream(res, out.upstream);
      res.status(out.status).json(out.body);
      return;
    }

    // ── set_active: the credential lifecycle, through the shared helper ──
    // Deactivation, NEVER deletion. login / whoami / loadEmployee all filter
    // active=eq.true, so the flag is enforced the moment it is written and
    // there is no second mechanism to keep in sync. Keeping the row preserves
    // created_at, role history, and -- here specifically -- the identity every
    // sv_controlled and sv_audit_log entry was written under. Deleting a
    // credential row in this app would orphan the author of a DEA-relevant
    // record, and hand-written SQL deletes are what lost three StoneDesk
    // licences.
    //
    // WIRED RATHER THAN HAND-WRITTEN, and the first draft of this file got that
    // wrong. It was modelled on api/rf-auth.js, which is the cleanest COMPLETE
    // example of the action set -- and is also one of the five endpoints that
    // predate api/_lib/employee-lifecycle.js and were deliberately left
    // un-migrated because rewriting live auth for tidiness risks a locked-out
    // customer. That reasoning does not extend to an endpoint written today.
    // api/_lib/employee-lifecycle-wiring.test.js caught it at the push gate:
    // "an auth endpoint exists that no list mentions". Adding it to
    // PRE_EXISTING would have been raising a count to get past a gate, which is
    // what that gate's own message warns against.
    if (action === 'set_active') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      const out = await lifecycle.setActive({
        caller: caller, body: body, licHash: licHash, table: TABLE,
        provisioningRoles: PROVISIONING_ROLES, roleLabel: PROVISIONING_LABEL,
        // `soleRole: null` -- STATED, not defaulted (2026-09-21). The engine
        // reads this field, and a call site that never sets it takes the
        // engine's default branch in silence, which is the seam-check defect
        // class. This app has ONE provisioning role, so the last-admin count
        // over `provisioningRoles` and over a sole role are the same set and
        // null is not merely safe here, it is exact.
        soleRole: null,
        rest: rest, headers: headers
        // No `audit`: api/_lib/audit.js allowlists sairnlaw / sairncode /
        // stonedesk only. This app HAS sv_audit_log, but that is the DOSING
        // trail for sv_controlled -- a different record class, and routing
        // credential events into it would mix the two in the one table a DEA
        // inspector would read. Adding sairnvet to the shared writer belongs
        // with the witnessing lock, where credential identity starts having
        // consequences worth logging.
      });
      if (out.upstream) return upstream(res, out.upstream);
      res.status(out.status).json(out.body);
      return;
    }
  } catch (err) {
    if (err && err.notProvisioned) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNvet employee accounts are not set up yet — run sql/sairnvet_employee_auth_schema.sql' } });
      return;
    }
    console.error('api/sv-auth error:', err);
    res.status(502).json({ error: { message: 'Upstream error — try again' } });
    return;
  }
};

module.exports.MANAGEMENT_ROLES = MANAGEMENT_ROLES;
// THE TIER THE WITNESSING LOCK KEYS ON. Exported rather than re-listed at the
// gate: re-listing role names in two places is the drift that cost SAIRNsenior
// a real bug, and here the two places would be an access-control surface and a
// DEA-relevant register.
module.exports.PRESCRIBER_ROLES = PRESCRIBER_ROLES;

// May this session sign a controlled-substance entry? A licensed veterinarian
// only. `session` is the verified token payload, and the caller must ALSO have
// confirmed the credential is still active -- this answers the role question
// and deliberately not the liveness one, which needs a database read.
function isPrescriber(session) {
  return !!(session && PRESCRIBER_ROLES[session.role]);
}
module.exports.isPrescriber = isPrescriber;

function isMissingTable(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('PGRST205') !== -1 || s.indexOf('does not exist') !== -1;
}
function isPermissionDenied(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('42501') !== -1 || s.indexOf('permission denied') !== -1;
}
// NOT_PROVISIONED and NOT_GRANTED are distinguished, following rf and law. sc
// and sd have a two-line upstream() stub, so a missing migration and a missing
// grant both surface as an unactionable 502 -- the difference between a
// five-second fix and an hour of guessing.
function upstream(res, detail) {
  console.error('sv-auth upstream error:', detail);
  if (isMissingTable(detail)) {
    res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNvet employee accounts are not set up yet — run sql/sairnvet_employee_auth_schema.sql' } });
    return;
  }
  if (isPermissionDenied(detail)) {
    res.status(503).json({ error: { code: 'NOT_GRANTED', message: 'The SAIRNvet employee table exists but the server role lacks privileges on it — re-run the GRANT block at the end of sql/sairnvet_employee_auth_schema.sql' } });
    return;
  }
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}

// ── Exported for tools/licence_recoverability_check.py via
// api/provisioner-health.js. The trapdoor is a licence with credential rows and
// ZERO rows that are both `active` and hold one of these roles. The detector
// must read THIS list rather than assume 'owner' -- SAIRNcode's is 'admin' --
// so the list is exported instead of duplicated.
module.exports.PROVISIONING_ROLES = PROVISIONING_ROLES;
module.exports.EMPLOYEE_TABLE = TABLE;
