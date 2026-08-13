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

async function writeAuditLog(supabaseUrl, serviceKey, { license_hash, employee_id, role, event_type, detail }) {
  if (!supabaseUrl || !serviceKey || !license_hash || !event_type) return false;
  try {
    const r = await fetch(supabaseUrl.replace(/\/+$/, '') + '/rest/v1/sairnlaw_audit_log', {
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
