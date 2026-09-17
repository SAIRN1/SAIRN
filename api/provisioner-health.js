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
const sv = require('./sv-auth');

// app_id -> { table, roles }. Only apps that implement set_active have a
// provisioner concept at all; the other ten auth files have neither
// set_active nor PROVISIONING_ROLES and cannot reach this state, so they are
// out of scope rather than unaudited.
//
// SAIRNvet ADDED 2026-09-13, the day its auth was built. Registering it HERE
// rather than later is not housekeeping: the trapdoor this endpoint detects is
// a licence with credential rows and zero active provisioners, which on this
// app means nobody can mint a credential and therefore nobody can be recorded
// as the author of a controlled-substance entry. A new auth endpoint that is
// not in this map is one whose trapdoor nothing watches.
const APPS = {
  sairndental: { table: dnt.EMPLOYEE_TABLE, roles: dnt.PROVISIONING_ROLES },
  sairnmechanical: { table: mech.EMPLOYEE_TABLE, roles: mech.PROVISIONING_ROLES },
  sairnroofing: { table: rf.EMPLOYEE_TABLE, roles: rf.PROVISIONING_ROLES },
  sairncode: { table: sc.EMPLOYEE_TABLE, roles: sc.PROVISIONING_ROLES },
  stonedesk: { table: sd.EMPLOYEE_TABLE, roles: sd.PROVISIONING_ROLES },
  sairnvet: { table: sv.EMPLOYEE_TABLE, roles: sv.PROVISIONING_ROLES }
};

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  const authz = req.headers['authorization'] || '';
  const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : null;
  if (!licenseKey) { res.status(401).json({ error: { code: 'NO_LICENSE', message: 'Missing bearer license key' } }); return; }

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

  // ── ENVELOPE GATES MOVED BELOW LICENCE VALIDATION 2026-09-05 ─────────────
  // Above it, a caller holding no valid licence could tell malformed JSON from
  // a valid envelope with a bad action, and read the action list straight out
  // of the refusal. Same shape as api/sd-data.js and api/sd-sub-data.js. The
  // 405 and bearer-presence checks stay above, because neither can say
  // anything about what exists. The cost is real and is not hidden: a junk key
  // now costs one license_keys lookup it did not before, and a malformed
  // request from a bad licence reports the licence, not the malformation.
  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { res.status(400).json({ error: { message: 'Invalid JSON body' } }); return; }
  }
  const ACTIONS = ['provisioner_health', 'rate_limit_health'];
  if (!body || ACTIONS.indexOf(body.action) === -1) {
    res.status(400).json({ error: { message: 'action must be one of: ' + ACTIONS.join(', ') } });
    return;
  }

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
    // ── TWO PROBES, BECAUSE THERE ARE TWO QUESTIONS AND THIS ANSWERED ONE
    // ── WHILE SPEAKING FOR BOTH (2026-09-17).
    //
    // The old message read "The limit is real under concurrency." That is true
    // of the APP CEILING and says nothing about the TENANT SUB-BUDGET, which
    // is a separate migration (sql/sairn_ai_tenant_subbudget_2026-09-15.sql)
    // and a separate failure: with the app ceiling perfectly atomic, ONE
    // TENANT CAN STILL EXHAUST ALL OF IT. A reader acting on that sentence
    // would turn enforcement on believing a property nothing here had tested.
    //
    // THE 3-ARG CALL CANNOT TELL THE TWO APART, AND THAT IS STRUCTURAL rather
    // than an oversight. The tenant migration DROPS the 3-arg function and
    // replaces it with a 6-arg one whose last three parameters default to
    // null -- deliberately, because an overload would make every 3-arg call
    // ambiguous and take the platform down. So a 3-arg call succeeds against
    // BOTH, and only a call carrying the tenant arguments discriminates: with
    // the old function alone, PostgREST finds no matching signature and 404s.
    // That is the same discriminator api/_lib/ai-rate-limit.js already uses
    // for its 6-arg -> 3-arg fallback.
    //
    // BOTH PROBES ARE READ-ONLY BY CONSTRUCTION, verified by reading both
    // function bodies rather than by trusting the endpoint's name: p_app_id ''
    // is refused first, before the advisory lock and before any insert.
    //
    // AND THE TWO FUNCTIONS REFUSE DIFFERENTLY, which is why `present` below
    // accepts two shapes. The 3-arg one RETURNS jsonb_build_object('error',
    // 'app_id required') as HTTP 200; the 6-arg one RAISES, which reaches us
    // as a 4xx. The previous test demanded the 200-with-object shape ONLY, so
    // RUNNING THE TENANT MIGRATION WOULD HAVE FLIPPED THIS ENDPOINT FROM
    // ATOMIC TO UNKNOWN -- a correct upgrade reading as a regression, on a
    // check whose whole job is to say whether the fix is in force.
    async function probe(args) {
      try {
        const rr = await fetch(sbrl.rest('rpc/sairn_ai_rate_limit_consume'), {
          method: 'POST', headers: sbrl.headers, body: JSON.stringify(args)
        });
        return { status: rr.status, payload: await rr.json().catch(() => null) };
      } catch (err) {
        return { status: null, payload: null, unreachable: true };
      }
    }

    const base = await probe({ p_app_id: '', p_limit: 1, p_window_seconds: 86400 });
    if (base.unreachable) {
      res.status(502).json({ ok: false, atomic: false, tenant_subbudget: false,
        state: 'UNKNOWN', tenant_state: 'UNKNOWN',
        message: 'Could not reach Supabase to probe the rate-limit function. Nothing is claimed about atomicity or about tenant sub-budgeting.' });
      return;
    }
    const status = base.status, payload = base.payload;
    const refusedByReturn = status === 200 && payload && payload.error === 'app_id required';
    const refusedByRaise = (status === 400 || status === 500)
      && /p_app_id is required/i.test(JSON.stringify(payload || ''));
    const present = refusedByReturn || refusedByRaise;
    const absent = status === 404;

    // Only worth asking if there is a function at all. A 404 here against an
    // absent function would be indistinguishable from a 404 against a 3-arg
    // one, and reporting "no sub-budget" about a limiter that does not exist
    // would be a true sentence pointing at the wrong problem.
    let tenantState = 'NOT_APPLICABLE';
    if (present) {
      const t = await probe({ p_app_id: '', p_limit: 1, p_window_seconds: 86400,
                              p_tenant_key: '', p_tenant_limit: 1, p_contention_floor: 1 });
      tenantState = t.unreachable ? 'UNKNOWN'
        : t.status === 404 ? 'APP_CEILING_ONLY'
        : (t.status === 200 || t.status === 400 || t.status === 500) ? 'SUB_BUDGETED'
        : 'UNKNOWN';
    }
    const subBudgeted = tenantState === 'SUB_BUDGETED';

    res.status(200).json({
      ok: true,
      atomic: present,
      tenant_subbudget: subBudgeted,
      state: present ? 'ATOMIC' : (absent ? 'RACY_FALLBACK' : 'UNKNOWN'),
      tenant_state: tenantState,
      probe_status: status,
      message: present
        ? (subBudgeted
            ? 'public.sairn_ai_rate_limit_consume exists and is callable by service_role, so the limiter counts and records inside one transaction under an advisory lock. THE APP CEILING is real under concurrency, AND the tenant sub-budget is live, so one licence cannot exhaust the whole ceiling.'
            : 'THE APP CEILING is real under concurrency -- the RPC counts and records in one transaction under an advisory lock. BUT THE TENANT SUB-BUDGET IS NOT LIVE: only the 3-argument signature answers, so every call is counted against the app and ONE LICENCE CAN EXHAUST THE ENTIRE CEILING. api/_lib/ai-rate-limit.js handles this correctly by falling back, so nothing is broken -- it is a fairness gap, not an outage. Run sql/sairn_ai_tenant_subbudget_2026-09-15.sql to close it.')
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
