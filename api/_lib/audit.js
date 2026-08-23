// api/_lib/audit.js
// ---------------------------------------------------------------------------
// Shared immutable audit-log writer for SAIRNlaw (sql/sairnlaw_audit_log_schema.sql).
//
// SCOPE (2026-08-08, confirmed with Michael): only events that actually
// cross the server boundary can be honestly audited here — auth events
// (api/law-auth.js) and citator lookups (api/legal-citator.js). Trust
// transactions, document access, and matter changes are localStorage-only
// in sairnlaw.html today and are NOT logged by this file — see the schema
// file's own header for why faking that would be worse than disclosing it.
//
// Best-effort by design: a failed audit write must never block or fail the
// real action it's describing (a login that succeeds but fails to log is
// far better than a login blocked by a logging outage). Errors are
// swallowed here, not thrown — callers should not wrap this in their own
// try/catch.
//
// Return value (added 2026-08-13): resolves true on a confirmed write,
// false on any failure. This does NOT change the best-effort posture above
// — existing callers (login/MFA/citator events in api/law-auth.js) already
// `await audit(...)` without checking the return value and must keep doing
// so; a failed log write must still never block those actions. The return
// value exists so a caller for whom the write itself IS the point (e.g. the
// AI Chain of Custody actions, where the log entry is the deliverable) can
// choose to check it and report an honest failure instead of a false
// {ok:true}.
// ---------------------------------------------------------------------------

// TABLE PARAMETER (added 2026-08-20, SAIRNcode AI audit log): `table` is
// optional and defaults to sairnlaw_audit_log, so every existing SAIRNlaw
// caller (api/law-auth.js, api/legal-citator.js) is byte-for-byte unaffected
// -- this is a purely additive change to a shared file, not a behavior change.
// SAIRNcode passes 'sairncode_audit_log' (sql/sairncode_audit_log_schema.sql),
// which is the same shape and the same immutability posture.
//
// The name is allowlisted rather than interpolated freely: this value becomes
// part of a REST URL, and an unvalidated table name from a caller is exactly
// the kind of thing that turns into an injection vector later even if every
// caller today passes a constant.
const AUDIT_TABLES = { sairnlaw_audit_log: true, sairncode_audit_log: true, stonedesk_audit_log: true };
const DEFAULT_AUDIT_TABLE = 'sairnlaw_audit_log';

async function writeAuditLog(supabaseUrl, serviceKey, { license_hash, employee_id, role, event_type, detail, table }) {
  if (!supabaseUrl || !serviceKey || !license_hash || !event_type) return false;
  const target = table || DEFAULT_AUDIT_TABLE;
  if (!AUDIT_TABLES[target]) {
    console.error('audit log write refused: unknown table', target);
    return false;
  }
  try {
    const r = await fetch(supabaseUrl.replace(/\/+$/, '') + '/rest/v1/' + target, {
      method: 'POST',
      headers: {
        apikey: serviceKey,
        Authorization: 'Bearer ' + serviceKey,
        'Content-Type': 'application/json',
        Prefer: 'return=minimal'
      },
      body: JSON.stringify({
        license_hash,
        employee_id: employee_id || null,
        role: role || null,
        event_type,
        detail: detail || null
      })
    });
    if (!r.ok) {
      console.error('audit log write failed:', event_type, r.status, await r.text().catch(function () { return ''; }));
      return false;
    }
    return true;
  } catch (e) {
    // Non-fatal — see header. Logged server-side only, never surfaced to the caller.
    console.error('audit log write failed:', event_type, e && e.message);
    return false;
  }
}

module.exports = { writeAuditLog };
