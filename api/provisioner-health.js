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
  const ACTIONS = ['provisioner_health', 'rate_limit_health'];
  if (!body || ACTIONS.indexOf(body.action) === -1) {
    res.status(400).json({ error: { message: 'action must be one of: ' + ACTIONS.join(', ') } });
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

  // ── IS THE AI RATE LIMITER ACTUALLY ATOMIC RIGHT NOW? ───────────────────
  // Added 2026-09-02, and it is here rather than in its own file for the same
  // reason this file exists at all: a state that nothing reports gets
  // discovered instead. api/_lib/ai-rate-limit.js silently degrades to its old
  // count-then-insert path whenever the RPC is missing or erroring, and that
  // path is racy by construction -- N concurrent requests all read the same
  // count and all proceed. Nothing outside the server could tell which path was
  // live, so "is the limit real" was unanswerable after any deploy or any
  // change to the database.
  //
  // READ-ONLY, and that is not incidental. It probes with an EMPTY app_id,
  // which the function rejects before it takes the advisory lock and before it
  // inserts anything -- so this endpoint cannot add a row to the rate-limit log
  // and cannot itself consume budget. Calling the function normally would
  // record a call, which would make the health check pollute the thing it
  // measures.
  if (body.action === 'rate_limit_health') {
    let sbrl;
    try { sbrl = sbClient(); }
    catch (err) {
      console.error('rate-limit health supabase config error:', err.message);
      res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
      return;
    }
    let status = null, payload = null;
    try {
      const rr = await fetch(sbrl.rest('rpc/sairn_ai_rate_limit_consume'), {
        method: 'POST',
        headers: sbrl.headers,
        body: JSON.stringify({ p_app_id: '', p_limit: 1, p_window_seconds: 86400 })
      });
      status = rr.status;
      payload = await rr.json().catch(() => null);
    } catch (err) {
      res.status(502).json({ ok: false, atomic: false, state: 'UNKNOWN',
        message: 'Could not reach Supabase to probe the rate-limit function. Nothing is claimed about atomicity.' });
      return;
    }

    const present = status === 200 && payload && payload.error === 'app_id required';
    const absent = status === 404;
    res.status(200).json({
      ok: true,
      atomic: present,
      state: present ? 'ATOMIC' : (absent ? 'RACY_FALLBACK' : 'UNKNOWN'),
      probe_status: status,
      message: present
        ? 'public.sairn_ai_rate_limit_consume exists and is callable by service_role, so the limiter counts and records inside one transaction under an advisory lock. The limit is real under concurrency.'
        : absent
          ? 'The RPC is absent, so api/_lib/ai-rate-limit.js is running its count-then-insert fallback. THE LIMIT IS APPROXIMATE UNDER CONCURRENCY -- do not set SAIRN_AI_RATE_LIMIT_MODE=enforce until sql/sairn_ai_rate_limit_consume_fn.sql has been run.'
          : 'The RPC answered unexpectedly (HTTP ' + status + '). Treat the limiter as racy until this is explained; nothing is claimed either way.'
    });
    return;
  }

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
