// api/_lib/employee-lifecycle.js
// ---------------------------------------------------------------------------
// The credential-deactivation lifecycle, once, for every app that does not
// already have its own copy. Not routed by Vercel (leading underscore).
//
// ── THE GAP THIS CLOSES ─────────────────────────────────────────────────────
// `sairn-app-scaffold` declares the deactivation lifecycle REQUIRED in v1 for
// any app with per-employee credentials. Measured 2026-09-03 across the
// platform, by grep rather than from the tracking table:
//
//   * 14 apps ship a `*_employee_auth` table with an `active` column;
//   * every login endpoint filters `active=eq.true`, so the column works;
//   * only FIVE endpoints could set it (sd, sc, dnt, mech, rf).
//
// For the other NINE -- SAIRNcare, SAIRNbuild, SAIRNgrounds, SAIRNlaw,
// SAIRNlegacy, SAIRNbiz, SAIRNscape, SAIRNdesign, SAIRNsenior -- a departing
// employee's credential could only be switched off by a HAND-WRITTEN SQL EDIT
// in the Supabase editor. api/sd-auth.js:304-308 records what that costs: three
// StoneDesk licences lost to untracked credential state. This is that same
// hazard, standing open in nine more apps.
//
// ── WHY A SHARED LIB AND NOT A TENTH HAND-WRITTEN COPY ──────────────────────
// The five existing implementations are ~100 lines each and agree on every
// rule. Writing nine more by hand would put fourteen copies of a security
// decision in the repo, and `sairn-employee-auth-scaffold` exists specifically
// to say don't. The per-app variation is genuinely four values: the table, the
// app id the session token must be scoped to, that app's provisioning roles,
// and the human label for them in a refusal message.
//
// ⚠ THE FIVE EXISTING IMPLEMENTATIONS ARE DELIBERATELY NOT REFACTORED ONTO
// THIS. They are live, in production, on the authentication path, and
// rewriting working auth to remove duplication is a change whose only benefit
// is tidiness and whose failure mode is a locked-out customer. They should
// converge here eventually, as their own scoped change with its own
// verification. Until then this file is the SECOND implementation, not the
// only one, and that is stated rather than implied.
//
// ── EVERY RULE BELOW CAME FROM A REAL LOCKOUT, NOT FROM A THREAT MODEL ──────
// The guards are transcribed from api/sd-auth.js's implementation, which is the
// most complete of the five. Restated because each one is load-bearing:
//
//   1. PROVISIONERS ONLY. And the roles are read PER APP -- SAIRNgrounds
//      allows superintendent, SAIRNbiz allows hr, SAIRNscape allows crew_lead.
//      CLAUDE.md records a guard that hardcoded `owner` and therefore checked
//      nothing on SAIRNcode forever. Passing them in is how that cannot recur.
//   2. NO SELF-DEACTIVATION. The likeliest accidental route to a licence with
//      zero active provisioners, and there is no legitimate reason to do it to
//      yourself instead of asking another provisioner.
//   3. THE CALLER'S OWN ROW IS RE-READ AND MUST STILL BE ACTIVE. A session
//      token outlives the credential it was minted from; without this, someone
//      deactivated an hour ago still holds a working provisioning token.
//   4. NEVER THE LAST ACTIVE PROVISIONER. Zero active provisioners is
//      UNRECOVERABLE THROUGH THE API -- `bootstrap` refuses 409 while any row
//      exists, and `setup`/`set_active` both need an active provisioner. That
//      is the exact state RF-PINNACLE-2026 was found in.
//   5. A REASON IS REQUIRED TO DEACTIVATE, NOT TO REACTIVATE. Reactivating is
//      self-explanatory and always safe; a deactivation is the thing somebody
//      reconstructs months later.
//
// Guard 4 is UNREACHABLE BY CONSTRUCTION while guards 2 and 3 stand -- an
// active caller plus a different active provisioner target implies at least
// two. It is kept anyway, and tested, because reachability is a property of
// today's rule set: a new provisioning role, or any future path that skips the
// caller re-read, makes it live again. A lockout is not worth rediscovering in
// production.
//
// ── THE DECISION IS MADE FROM THE DATABASE, NEVER FROM THE REQUEST ──────────
// The roster is read ONCE and every check runs against those rows. Nothing the
// client says about who the target is, what role they hold, or who else exists
// is trusted.
// ---------------------------------------------------------------------------

// Rows the caller may see. Includes INACTIVE rows on purpose: reactivating
// somebody requires being able to see them first, and an access panel that can
// only ever deactivate is half a lifecycle. Never selects pin_hash, pin_salt,
// failed_attempts or locked_until.
const ROSTER_SELECT = 'employee_id,display_name,role,active';

function refusal(status, code, message, extra) {
  return { status: status, body: Object.assign({ error: { code: code, message: message } }, extra || {}) };
}

// Reads the whole roster for a licence. Returns {ok:true, rows} or
// {ok:false, detail} so the caller can run its own upstream() -- each endpoint
// has an app-specific NOT_PROVISIONED / NOT_GRANTED message naming its own
// schema file, and flattening those into one generic string here would lose
// the only sentence that tells someone which SQL file to run.
async function readRoster(ctx) {
  const r = await fetch(
    ctx.rest(ctx.table + '?license_hash=eq.' + encodeURIComponent(ctx.licHash) +
             '&select=' + ROSTER_SELECT + '&order=employee_id.asc'),
    { headers: ctx.headers });
  const rows = await r.json();
  if (!r.ok) return { ok: false, detail: rows };
  return { ok: true, rows: Array.isArray(rows) ? rows : [] };
}

// ── set_active ─────────────────────────────────────────────────────────────
// ctx:
//   caller             the verified session, or null. VERIFY IT AGAINST THIS
//                      APP's id before calling -- an `owner` token from another
//                      app must not pass, which is why every endpoint passes
//                      expectedApp to verifySessionToken.
//   body               the parsed request body
//   licHash, table     this licence and this app's auth table
//   provisioningRoles  array, READ FROM THIS APP's setup gate, not assumed
//   roleLabel          how to name those roles to a human ("Owner or HR")
//   rest, headers      PostgREST helpers from the endpoint
//   audit              optional async (event_type, detail) => boolean. Only
//                      three apps have an audit log (api/_lib/audit.js's
//                      allow-list is sairnlaw / sairncode / stonedesk); the rest
//                      pass nothing and the response carries no `audited` field
//                      at all, rather than claiming an audit that never ran.
//
// seam-check: server-supplied audit
//
// That declaration is for tools/sairn_seam_check.py, which correctly notices
// that `audit` is read here and forwarded by none of the four current call
// sites. It is not a dropped field -- it is absent BY DESIGN for every app
// without an audit-log table, and the absence is load-bearing: it is what makes
// the response omit `audited` instead of reporting `audited:false`, which would
// read as an audit that was attempted and failed. When an app with an audit log
// is wired here it passes one, and nothing about this changes. Declared rather
// than silenced with an override, and stated next to the contract it describes
// so it goes stale visibly.
//
// Returns { status, body } on a decision, or { upstream: detail } when
// PostgREST failed and the endpoint should run its own upstream(res, detail).
async function setActive(ctx) {
  const caller = ctx.caller;
  const roles = ctx.provisioningRoles || [];
  const label = ctx.roleLabel || 'a provisioner';
  const audit = ctx.audit || null;
  const doAudit = async (event_type, detail) => (audit ? await audit(event_type, detail) : undefined);
  // Only present when an audit actually ran. An `audited:false` on an app with
  // no audit log would read as "we tried to record this and failed".
  const withAudit = (v) => (v === undefined ? {} : { audited: v });

  if (!caller || roles.indexOf(caller.role) === -1) {
    return refusal(403, 'FORBIDDEN', 'Only ' + label + ' can activate or deactivate a credential');
  }

  const body = ctx.body || {};
  const target_id = String(body.employee_id || '').trim();
  const nextActive = body.active === true;
  const reason = String(body.reason || '').trim();

  if (!target_id) return { status: 400, body: { error: { message: 'employee_id is required' } } };
  if (typeof body.active !== 'boolean') {
    return { status: 400, body: { error: { message: 'active must be true or false' } } };
  }
  if (!nextActive && !reason) {
    return { status: 400, body: { error: { message: 'reason is required when deactivating a credential' } } };
  }
  if (reason.length > 500) {
    return { status: 400, body: { error: { message: 'reason max 500 characters' } } };
  }

  if (!nextActive && target_id === caller.employee_id) {
    const a = await doAudit('credential_change_refused',
      { target: target_id, requested_active: false, reason_code: 'SELF_DEACTIVATE' });
    return refusal(409, 'SELF_DEACTIVATE',
      'You cannot deactivate your own credential. Ask another ' + label + ' to do it.', withAudit(a));
  }

  const roster = await readRoster(ctx);
  if (!roster.ok) return { upstream: roster.detail };
  const rowsAll = roster.rows;

  const callerRow = rowsAll.filter((x) => x.employee_id === caller.employee_id)[0];
  if (!callerRow || callerRow.active !== true) {
    const a = await doAudit('credential_change_refused',
      { target: target_id, requested_active: nextActive, reason_code: 'CREDENTIAL_INACTIVE' });
    return refusal(403, 'CREDENTIAL_INACTIVE',
      'This credential has been deactivated. Sign in again with an active account.', withAudit(a));
  }

  const target = rowsAll.filter((x) => x.employee_id === target_id)[0];
  if (!target) {
    return refusal(404, 'NOT_FOUND', 'No such employee on this license');
  }

  const activeProvisioners = rowsAll.filter(
    (x) => x.active === true && roles.indexOf(x.role) !== -1);

  if (!nextActive && roles.indexOf(target.role) !== -1 &&
      target.active === true && activeProvisioners.length <= 1) {
    const a = await doAudit('credential_change_refused',
      { target: target_id, requested_active: false, reason_code: 'LAST_ADMIN',
        active_admins: activeProvisioners.length });
    return refusal(409, 'LAST_ADMIN',
      'This is the only active ' + label + ' on this license. Deactivating it would lock ' +
      'everyone out with no way back in through the app — provision another first, then retry.',
      withAudit(a));
  }

  // Already in the requested state. Reported as unchanged rather than as a
  // write, so a double-click does not look like two deactivations in an audit
  // log, and no PATCH is issued.
  if (target.active === nextActive) {
    return { status: 200, body: { ok: true, employee_id: target_id, active: nextActive,
      unchanged: true, remaining_admins: activeProvisioners.length } };
  }

  const patchR = await fetch(
    ctx.rest(ctx.table + '?license_hash=eq.' + encodeURIComponent(ctx.licHash) +
             '&employee_id=eq.' + encodeURIComponent(target_id)),
    { method: 'PATCH',
      headers: Object.assign({}, ctx.headers, { Prefer: 'return=representation' }),
      body: JSON.stringify({ active: nextActive, updated_at: new Date().toISOString() }) });
  const patched = await patchR.json();
  if (!patchR.ok) return { upstream: patched };

  // Recomputed from the roster with the target's new state substituted, rather
  // than by adding or subtracting one -- the arithmetic version is wrong the
  // moment the target was not a provisioner.
  const remaining = rowsAll.filter((x) => {
    const isActive = (x.employee_id === target_id) ? nextActive : x.active === true;
    return isActive && roles.indexOf(x.role) !== -1;
  }).length;

  const a = await doAudit(nextActive ? 'credential_reactivated' : 'credential_deactivated',
    { target: target_id, target_role: target.role, previous_active: target.active,
      new_active: nextActive, reason: reason || null, remaining_admins: remaining });

  return { status: 200, body: Object.assign({
    ok: true, employee_id: target_id, active: nextActive, remaining_admins: remaining
  }, withAudit(a)) };
}

// ── roster ─────────────────────────────────────────────────────────────────
// The read the access panel needs, with the same caller-still-active re-check
// set_active applies. Returns { status, body } or { upstream }.
//
// ⚠ THIS RETURNS INACTIVE ROWS, WHICH THE `roster` ACTION IN THESE APPS DID NOT
// BEFORE. Any existing client that builds an assignee picker from the roster
// MUST filter `active !== false` or a deactivated employee becomes assignable
// again. That is a real regression and every consumer was updated in the same
// commit that introduced this.
async function roster(ctx) {
  const caller = ctx.caller;
  if (!caller || !ctx.canView) {
    // viewLabel only. This used to fall back to roleLabel and then to
    // 'management' -- dead flexibility that tools/sairn_seam_check.py correctly
    // flagged: roster() read a field no call site forwards, so the fallback
    // could only ever fire by accident, and an accidental fallback in a refusal
    // message tells a customer to ask the wrong person for help.
    return refusal(403, 'FORBIDDEN', 'Only ' + ctx.viewLabel +
      ' can view the employee roster');
  }
  const r = await readRoster(ctx);
  if (!r.ok) return { upstream: r.detail };
  const callerRow = r.rows.filter((x) => x.employee_id === caller.employee_id)[0];
  if (!callerRow || callerRow.active !== true) {
    return refusal(403, 'CREDENTIAL_INACTIVE',
      'This credential has been deactivated. Sign in again with an active account.');
  }
  return { status: 200, body: { ok: true, employees: r.rows } };
}

module.exports = { setActive, roster, readRoster, ROSTER_SELECT };
