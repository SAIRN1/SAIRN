// api/provisioner-health.js
// ---------------------------------------------------------------------------
// IS THIS LICENCE STILL RECOVERABLE?
//
// A licence is in the trapdoor when it has credential rows and ZERO rows that
// are both `active` and hold a role in that app's PROVISIONING_ROLES. All three
// exits are then shut: `bootstrap` refuses 409 while any row exists (its
// existence probe deliberately does not filter on `active`), and `setup` and
// `set_active` both require an active provisioner.
//
// RF-PINNACLE-2026 entered that state, sat in it long enough for a HIGH
// PRIORITY row to be written about it, then recovered — and NOTHING NOTICED
// EITHER TRANSITION. The index row was still asserting zero active owners on
// 2026-08-29 when a live roster read showed two. This endpoint exists so the
// state is reported rather than discovered.
//
// ── WHY IT IS NOT A `roster` CALL ──────────────────────────────────────────
// `roster` needs a management session, and a licence in the trapdoor has nobody
// who can sign in — the check would be unavailable exactly when it matters.
// This is licence-key-only and returns COUNTS, never employee ids, names, roles
// per person, or anything resembling a credential.
//
// ── WHY THE ROLES ARE IMPORTED, NOT LISTED HERE ────────────────────────────
// Each app's PROVISIONING_ROLES is exported from its own auth module. Four are
// `['owner']`; SAIRNcode's is `['admin']` and StoneDesk's is
// `['owner','admin']`. A detector that assumed `owner` would report SAIRNcode
// healthy forever while checking nothing — the app answers normally right up
// until someone needs to recover it. Importing means this file cannot drift
// from the rule it is checking.
//
// Read-only. One action, no writes, no branch that can reach one.
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const { sbClient } = require('./_lib/courtlistener');

const dnt = require('./dnt-auth');
const mech = require('./mech-auth');
const rf = require('./rf-auth');
const sc = require('./sc-auth');
const sd = require('./sd-auth');

// app_id -> { table, roles }. Only apps that implement set_active have a
// provisioner concept at all; the other eleven auth files have neither
// set_active nor PROVISIONING_ROLES and cannot reach this state, so they are
// out of scope rather than unaudited.
const APPS = {
  sairndental: { table: dnt.EMPLOYEE_TABLE, roles: dnt.PROVISIONING_ROLES },
  sairnmechanical: { table: mech.EMPLOYEE_TABLE, roles: mech.PROVISIONING_ROLES },
  sairnroofing: { table: rf.EMPLOYEE_TABLE, roles: rf.PROVISIONING_ROLES },
  sairncode: { table: sc.EMPLOYEE_TABLE, roles: sc.PROVISIONING_ROLES },
  stonedesk: { table: sd.EMPLOYEE_TABLE, roles: sd.PROVISIONING_ROLES }
};

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  const authz = req.headers['authorization'] || '';
  const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : null;
  if (!licenseKey) { res.status(401).json({ error: { code: 'NO_LICENSE', message: 'Missing bearer license key' } }); return; }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { res.status(400).json({ error: { message: 'Invalid JSON body' } }); return; }
  }
  if (!body || body.action !== 'provisioner_health') {
    res.status(400).json({ error: { message: 'action must be: provisioner_health' } });
    return;
  }

  let lic;
  try { lic = await validateLicenseKey(licenseKey); }
  catch (err) {
    if (err.code === 'CONFIG') { console.error('provisioner-health config error:', err.message); res.status(500).json({ error: { message: 'Server configuration error — contact support' } }); return; }
    console.error('provisioner-health license validation error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }
  if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }

  const cfg = APPS[lic.app_id];
  if (!cfg) {
    // Reported as NOT_APPLICABLE rather than as healthy. An app with no
    // set_active cannot reach the trapdoor, but saying "healthy" would let a
    // future app that DOES implement it inherit a clean answer it never earned.
    res.status(200).json({
      ok: true, app_id: lic.app_id || null, state: 'NOT_APPLICABLE',
      message: 'This app does not implement set_active or PROVISIONING_ROLES, so it has no provisioner concept and cannot reach the unrecoverable state.'
    });
    return;
  }

  let sb;
  try { sb = sbClient(); }
  catch (err) { console.error('provisioner-health supabase config error:', err.message); res.status(500).json({ error: { message: 'Server configuration error — contact support' } }); return; }

  try {
    const r = await fetch(sb.rest(cfg.table + '?license_hash=eq.' + encodeURIComponent(lic.license_hash) + '&select=role,active'), { headers: sb.headers });
    if (r.status === 404 || r.status === 400) {
      res.status(503).json({ ok: false, code: 'NOT_PROVISIONED',
        message: 'The employee-auth table for this app is not set up yet. Nothing is claimed about recoverability.' });
      return;
    }
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const rows = (await r.json()) || [];
    const active = rows.filter((x) => x && x.active === true &&
      cfg.roles.indexOf(x.role) !== -1).length;

    // Three states, and NO_CREDENTIALS is deliberately not lumped in with
    // TRAPDOOR: zero rows RE-ARMS bootstrap and is recovery, not lockout.
    // Conflating the two is what made this hard to reason about for a day.
    const state = rows.length === 0 ? 'NO_CREDENTIALS'
      : (active === 0 ? 'TRAPDOOR' : 'HEALTHY');

    res.status(200).json({
      ok: true,
      app_id: lic.app_id,
      provisioning_roles: cfg.roles,
      credential_rows: rows.length,
      active_provisioners: active,
      state,
      message: state === 'TRAPDOOR'
        ? 'UNRECOVERABLE THROUGH THE API: this licence has credential rows and no active provisioner. bootstrap refuses while any row exists; setup and set_active both need an active provisioner. Fix with one SQL statement — reactivate or promote a provisioner, or delete every credential row for this licence to re-arm bootstrap. Never delete a subset of the provisioners.'
        : state === 'NO_CREDENTIALS'
          ? 'No credential rows. bootstrap is armed and this licence is recoverable — this is the healthy empty state, not a fault.'
          : 'At least one active provisioner. setup and set_active both work.'
    });
  } catch (err) {
    console.error('provisioner-health read failed:', err && err.message);
    res.status(502).json({ error: { message: 'Could not read credential state — try again' } });
  }
};
