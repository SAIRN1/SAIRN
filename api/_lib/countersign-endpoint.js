// api/_lib/countersign-endpoint.js
// ---------------------------------------------------------------------------
// The HTTP half of the countersignature lock. One handler, built from an app
// profile; see api/_lib/countersign.js for why this is one mechanism rather
// than one file per app.
//
// Actions, all POST, licence via `Authorization: Bearer`, session via
// `X-SD-Auth`:
//
//   prepare       { resource, payload }        -> { token, expires_at }
//   countersign   { token }                     (a DIFFERENT qualified signer)
//   status        { token }                    -> what stage it is at
//   open          { }                          -> every UNSPENT row, staged
//
// `prepare` IS NAMED `prepare` AND NOT `request`, which api/sv-witness.js
// calls it. The verb is the one api/_lib/law-roles.js and api/_lib/leg-roles.js
// both export as their PREPARE_ACTION and the one the role tables decide on,
// so three files use one word. A fourth spelling for the endpoint would be the
// drift that cost SAIRNsenior a real bug when two halves each called
// effectiveClock() and only one passed the as-of.
//
// ── THE TOKEN IS RETURNED ONCE AND STORED HASHED ─────────────────────────
// There is no way to read it back; a lost token is re-prepared, which costs
// one confirmation rather than leaving a readable table of live signatures.
//
// ── THE AUTH BOUNDARY IS **NOT** IN THIS FILE, AND THAT IS NOT A GAP ─────
// Method check, bearer presence, environment check and `validateLicenseKey`
// all live in the two `api/*-countersign.js` route files, exactly as they do
// in all fifteen `api/*-auth.js` handlers and in api/sv-witness.js. This file
// receives an ALREADY-VALIDATED licence.
//
// IT WAS WRITTEN THE OTHER WAY FIRST AND A CHECKER CAUGHT IT.
// `tools/preauth_oracle_check.py` reads each `api/*.js` route for an auth
// boundary (`await validateLicenseKey(` or `verifySessionToken(`) and reported
// both new endpoints as "UNDECLARED PUBLIC -- no auth boundary", because the
// boundary was one `require` away in here. The checker's premise is right and
// the first draft was wrong: THE FILE THAT IS THE ROUTE SHOULD SHOW ITS OWN
// BOUNDARY, because that is the file a reader opens when asking "what can
// reach this URL unauthenticated". ~30 lines of preamble appear twice; the
// ~200 lines of lock logic still appear once.
// ---------------------------------------------------------------------------

'use strict';

const { verifySessionToken, tokenFromRequest } = require('./auth');
const cs = require('./countersign');

const ACTIONS = ['prepare', 'countersign', 'status', 'open'];

// ── `open` EXISTS BECAUSE THE INDEX DID AND THE QUERY DID NOT (b20) ───────
// Both app schemas ship `idx_<app>_countersign_open` --
// `(license_hash, resource, expires_at) WHERE spent_at IS NULL` -- and both
// carry a comment saying it is "the query a director's 'needs your signature'
// list is built from". NOTHING QUERIED IT. `status` takes a `{ token }` and
// returns ONE row, and the clear token is handed out exactly once, at
// `prepare`, TO THE PREPARER -- so a signer holds no token and could not drive
// `status` for anything. The list panel both apps are owed had no endpoint to
// read, and the index served nobody.
//
// Found by reading the endpoint rather than the routing note: b19's routed
// spec and the b20 dispatch both say the panel is "driven by the `status`
// action" AND that the index "exists to serve that query", and those two
// sentences cannot both be true of what shipped.
//
// ── IT RETURNS NO TOKEN AND NO TOKEN HASH, AND THAT IS NOT AN OVERSIGHT ───
// Both SQL files say why in their own words: "a readable table of live tokens
// is a table of signatures waiting to be borrowed". A token is a bearer
// credential for exactly one irreversible write. An endpoint that listed them
// to every qualified signer would hand out the mechanism the content hash and
// the single-use rule exist to protect.
//
// SO THE PANEL IS READ-ONLY BY CONSTRUCTION, not by politeness. It tells a
// signer what is waiting; signing still requires the token the preparer hands
// them out of band, which is the design and not a gap. The UI must say so
// rather than render a button that cannot work.
const OPEN_CAP = 200;

/**
 * @param {object} profile see api/_lib/countersign.js assertProfile
 * @param {object} lic the VALIDATED licence envelope from the route file --
 *   `{ valid: true, active: true, license_hash }`. Re-asserted below rather
 *   than trusted: a caller that passes an unvalidated or failed envelope must
 *   be refused here too, because "the route checked it" is an assumption and
 *   this function is reachable from any future route.
 */
// ── ONE STAGE COMPUTATION, CALLED BY BOTH `status` AND `open` (b20) ───────
// THE STAGE IS COMPUTED HERE AND NAMED, rather than returning four nullable
// columns for a client to reason over. Four columns is four chances for a
// panel to render "signed" for a spent-and-expired row.
//
// EXTRACTED RATHER THAN COPIED when `open` was added, and the reason is the
// whole point of the stage existing: two copies of this ladder would be two
// answers to "what is this record", and the second one would be the one in the
// list a signer actually reads. The ORDER is the policy -- spent first,
// expired before signed -- so a row that was signed and then expired reads
// `expired`, which is what it is.
const STAGES = Object.freeze(['awaiting_signature', 'signed', 'filed', 'expired']);
function stageOf(row, nowMs) {
  const expired = new Date(row.expires_at).getTime() <= nowMs;
  return row.spent_at ? 'filed'
       : expired ? 'expired'
       : row.countersign_employee_id ? 'signed'
       : 'awaiting_signature';
}

// The column list both actions select. ONE STRING, so a column added for one
// and not the other cannot make `stageOf` read `undefined` on one path --
// which would compute `awaiting_signature` for a filed record and is precisely
// the failure the computed stage exists to prevent.
const STAGE_COLUMNS = 'resource,prepared_by,prepared_role,'
  + 'countersign_employee_id,countersign_role,countersigned_at,spent_at,'
  + 'expires_at';

function runCountersignAction(profile, req, res, lic) {
  cs.assertProfile(profile);
  if (!lic || lic.valid !== true || lic.active !== true || !lic.license_hash) {
    console.error(profile.app + '-countersign: runCountersignAction called '
      + 'without a validated licence envelope');
    res.status(401).json({ error: { code: 'NO_LICENSE',
      message: 'Missing bearer license key' } });
    return Promise.resolve();
  }
  return handleAction(profile, req, res, lic);
}

async function handleAction(profile, req, res, lic) {
  {
    const SUPABASE_URL = process.env.SUPABASE_URL;
    const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
    if (!SUPABASE_URL || !SERVICE_KEY || !process.env.SD_AUTH_SECRET) {
      console.error(profile.app + '-countersign: SUPABASE_URL / '
        + 'SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
      res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
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

    const licHash = lic.license_hash;
    const headers = {
      apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY,
      'Content-Type': 'application/json'
    };
    const rest = (p) => SUPABASE_URL + '/rest/v1/' + p;
    const enc = encodeURIComponent;

    function upstream(detail) {
      console.error(profile.app + '-countersign upstream error:', detail);
      if (cs.isMissingTable(detail)) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED',
          message: 'The ' + profile.app + ' countersignature table is not set up '
                 + 'yet — run ' + profile.sqlFile } });
        return;
      }
      res.status(502).json({ error: { message: 'Data store error — try again' } });
    }

    // THE CALLER MUST BE A LIVE, ACTIVE EMPLOYEE -- not merely the holder of a
    // token that says so. A session outlives its credential's deactivation by
    // up to 12h, and a signature from a revoked account is worse than no
    // signature: it carries a name that no longer means anything.
    async function activeCaller() {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, profile.app);
      if (!caller) return null;
      const r = await fetch(rest(profile.employeeTable + '?license_hash=eq.' + enc(licHash) +
        '&employee_id=eq.' + enc(caller.employee_id) +
        '&active=eq.true&select=employee_id,role&limit=1'), { headers });
      const rows = await r.json().catch(() => null);
      if (!r.ok) { const e = new Error('caller lookup failed'); e.detail = rows; throw e; }
      const row = (Array.isArray(rows) && rows[0]) || null;
      if (!row) return null;
      // ROLE FROM THE DATABASE ROW, not from the token, so a demotion takes
      // effect at once rather than waiting out the token's life.
      return { employee_id: row.employee_id, role: row.role };
    }

    try {
      if (action === 'prepare') {
        const caller = await activeCaller();
        if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
        const resource = String(body.resource || '');
        if (!profile.lockedResources[resource]) {
          res.status(400).json({ error: { message: 'resource must be one of: '
            + Object.keys(profile.lockedResources).join(', ') } });
          return;
        }
        // THE ROLE LISTS ARE IMPORTED INTO THE PROFILE, never re-typed here.
        if (!cs.isPreparer(profile, caller.role)) {
          res.status(403).json({ error: { code: 'NOT_A_PREPARER',
            message: profile.preparerRefusal } });
          return;
        }
        if (!body.payload || typeof body.payload !== 'object') {
          res.status(400).json({ error: { message: 'payload is required and must be the exact record to be written' } });
          return;
        }
        const tok = cs.newToken();
        const expires = new Date(Date.now() + cs.TOKEN_TTL_MS).toISOString();
        const r = await fetch(rest(profile.tokenTable), {
          method: 'POST',
          headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
          body: JSON.stringify({
            license_hash: licHash,
            resource: resource,
            token_hash: cs.hashToken(tok),
            content_hash: cs.contentHash(resource, body.payload),
            prepared_by: caller.employee_id,
            prepared_role: caller.role,
            expires_at: expires
          })
        });
        const rows = await r.json().catch(() => null);
        if (!r.ok) return upstream(rows);
        res.status(200).json({
          ok: true, token: tok, expires_at: expires,
          resource: resource,
          prepared_by: caller.employee_id,
          countersigned: false,
          // SAID ON EVERY PREPARE, not only on a refusal: the preparer needs
          // to know who to go to, and a workflow lock whose next step is
          // unnamed is a workflow stall.
          countersign_required_from: profile.signerLabel,
          // AND WHETHER THE PREPARER MAY FILE IT THEMSELVES, which is the
          // F1-vs-C2 difference and the thing a UI has to render differently.
          preparer_may_file:
            profile.lockedResources[resource] === cs.MODE_PREPARED_ONLY
            && cs.isSigner(profile, caller.role)
        });
        return;
      }

      if (action === 'countersign') {
        const caller = await activeCaller();
        if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
        if (!cs.isSigner(profile, caller.role)) {
          res.status(403).json({ error: { code: 'NOT_QUALIFIED_TO_SIGN',
            message: profile.signerRefusal } });
          return;
        }
        const tok = String(body.token || '');
        if (!tok) { res.status(400).json({ error: { message: 'token is required' } }); return; }
        const r = await fetch(rest(profile.tokenTable + '?license_hash=eq.' + enc(licHash) +
          '&token_hash=eq.' + enc(cs.hashToken(tok)) +
          '&select=id,resource,prepared_by,countersign_employee_id,spent_at,expires_at&limit=1'),
          { headers });
        const rows = await r.json().catch(() => null);
        if (!r.ok) return upstream(rows);
        const row = (Array.isArray(rows) && rows[0]) || null;
        if (!row) { res.status(404).json({ error: { code: 'NO_SUCH_TOKEN', message: 'That record is not recognised.' } }); return; }
        if (row.spent_at) { res.status(409).json({ error: { code: 'ALREADY_SPENT', message: 'That signature has already been used.' } }); return; }
        if (new Date(row.expires_at).getTime() <= Date.now()) {
          res.status(409).json({ error: { code: 'EXPIRED', message: 'That record has expired — prepare it again.' } });
          return;
        }
        // A SIGNATURE BY THE PREPARER IS NOT A COUNTERSIGNATURE.
        if (row.prepared_by === caller.employee_id) {
          res.status(409).json({ error: { code: 'SAME_PERSON',
            message: 'A second person must sign. You prepared this record yourself.' } });
          return;
        }
        if (row.countersign_employee_id) {
          res.status(409).json({ error: { code: 'ALREADY_COUNTERSIGNED', message: 'That record has already been signed.' } });
          return;
        }
        // COMPARE-AND-SET on `countersign_employee_id=is.null`, for the same
        // reason the spend is one: two qualified signers racing the same
        // record must not both be recorded, because only one of them is the
        // signature the write will cite.
        const patch = await fetch(rest(profile.tokenTable + '?id=eq.' + enc(row.id)
          + '&countersign_employee_id=is.null'), {
          method: 'PATCH',
          headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
          body: JSON.stringify({
            countersign_employee_id: caller.employee_id,
            countersign_role: caller.role,
            countersigned_at: new Date().toISOString()
          })
        });
        const patched = await patch.json().catch(() => null);
        if (!patch.ok) return upstream(patched);
        if (!Array.isArray(patched) || patched.length === 0) {
          res.status(409).json({ error: { code: 'ALREADY_COUNTERSIGNED',
            message: 'Somebody else signed that record a moment ago.' } });
          return;
        }
        res.status(200).json({
          ok: true, countersigned: true,
          resource: row.resource,
          prepared_by: row.prepared_by,
          countersign_employee_id: caller.employee_id
        });
        return;
      }

      if (action === 'status') {
        const caller = await activeCaller();
        if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
        const tok = String(body.token || '');
        if (!tok) { res.status(400).json({ error: { message: 'token is required' } }); return; }
        const r = await fetch(rest(profile.tokenTable + '?license_hash=eq.' + enc(licHash) +
          '&token_hash=eq.' + enc(cs.hashToken(tok)) +
          '&select=' + STAGE_COLUMNS + '&limit=1'), { headers });
        const rows = await r.json().catch(() => null);
        if (!r.ok) return upstream(rows);
        const row = (Array.isArray(rows) && rows[0]) || null;
        if (!row) { res.status(404).json({ error: { code: 'NO_SUCH_TOKEN', message: 'That record is not recognised.' } }); return; }
        // b20: the ladder moved to `stageOf` so `open` cannot grow a second
        // copy of it. Same answer, same order, one implementation.
        const stage = stageOf(row, Date.now());
        res.status(200).json({
          ok: true, stage: stage,
          resource: row.resource,
          prepared_by: row.prepared_by, prepared_role: row.prepared_role,
          countersign_employee_id: row.countersign_employee_id || null,
          countersign_role: row.countersign_role || null,
          countersigned_at: row.countersigned_at || null,
          spent_at: row.spent_at || null,
          expires_at: row.expires_at,
          countersign_required_from: profile.signerLabel
        });
        return;
      }

      // ── `open` -- THE LIST THE INDEX WAS BUILT FOR (b20) ───────────────
      if (action === 'open') {
        const caller = await activeCaller();
        if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
        // THE SIGNER SET, NOT EVERY EMPLOYEE. The outstanding queue names who
        // prepared each pending irreversible act and what resource it is on;
        // it is the signer's work list and nobody else's. Gated on
        // `profile.signerRoles` -- the SAME set `countersign` checks, read
        // from the profile rather than re-listed, so the list and the act it
        // leads to cannot disagree about who is qualified.
        //
        // THE PREPARER IS DELIBERATELY NOT INCLUDED, and it is a real
        // omission rather than an accident: a paralegal wanting to know
        // whether their disbursement was authorised has the token and can
        // call `status`, which is the narrower route and already exists.
        // Widening this to preparers is a decision, not a convenience.
        if (profile.signerRoles[caller.role] !== true) {
          res.status(403).json({ error: { code: 'NOT_QUALIFIED_TO_SIGN',
            message: profile.signerRefusal } });
          return;
        }
        // EXACTLY THE INDEX'S PREDICATE -- `license_hash` and
        // `spent_at is null` -- ordered by `expires_at`, which is the index's
        // third column. Written to match idx_<app>_countersign_open rather
        // than hoping the planner finds a use for it.
        //
        // EXPIRED-BUT-UNSPENT ROWS ARE RETURNED, not filtered server-side,
        // and the stage says which they are. A row that expired unsigned is
        // the one thing a signer most needs to see -- an authorisation that
        // quietly vanished from the list looks exactly like one that was
        // never prepared, and the preparer is sitting waiting for it.
        const r = await fetch(rest(profile.tokenTable + '?license_hash=eq.' + enc(licHash) +
          '&spent_at=is.null&select=' + STAGE_COLUMNS +
          '&order=expires_at.asc&limit=' + (OPEN_CAP + 1)), { headers });
        const rows = await r.json().catch(() => null);
        if (!r.ok) return upstream(rows);
        const all = Array.isArray(rows) ? rows : [];
        // ── THE CAP IS REPORTED, NEVER SILENT ──────────────────────────
        // There is no DELETE on either token table by design, so unspent
        // expired rows accumulate forever and this list has no natural
        // bound. A truncated list that does not say it was truncated is
        // indistinguishable from a complete one -- the platform's most
        // expensive defect shape -- so one extra row is fetched purely to
        // detect the condition and `truncated` is part of the response.
        const truncated = all.length > OPEN_CAP;
        const now = Date.now();
        const items = all.slice(0, OPEN_CAP).map((row) => ({
          stage: stageOf(row, now),
          resource: row.resource,
          prepared_by: row.prepared_by,
          prepared_role: row.prepared_role,
          countersign_employee_id: row.countersign_employee_id || null,
          countersign_role: row.countersign_role || null,
          countersigned_at: row.countersigned_at || null,
          expires_at: row.expires_at
          // NO token, NO token_hash, NO content_hash. See the note above
          // ACTIONS. `spent_at` is omitted too: every row here is unspent by
          // the query's own predicate, so a column that is always null would
          // only invite a client to reason over it.
        }));
        res.status(200).json({
          ok: true,
          items: items,
          truncated: truncated,
          cap: OPEN_CAP,
          stages: STAGES,
          countersign_required_from: profile.signerLabel,
          // THE LIMIT OF WHAT THIS LIST IS, carried in the response rather
          // than left to the UI to word. A signer cannot act from this list:
          // the token is the preparer's and is handed over out of band.
          note: 'This list is read-only. Authorising a record needs the '
              + 'reference the person who prepared it gives you -- it is not '
              + 'shown here and cannot be recovered from this list.'
        });
        return;
      }
    } catch (err) {
      if (err && cs.isMissingTable(err.detail)) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED',
          message: 'The ' + profile.app + ' countersignature table is not set up '
                 + 'yet — run ' + profile.sqlFile } });
        return;
      }
      console.error('api/' + profile.app + '-countersign error:', err);
      res.status(502).json({ error: { message: 'Upstream error — try again' } });
      return;
    }
  }
}

module.exports = { runCountersignAction, ACTIONS };
