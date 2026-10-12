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
// ── ONE APP -> TABLE MAP, AND AUDIT_TABLES IS DERIVED FROM IT (2026-10-11) ──
// WHY A MAP RATHER THAN A CONSTANT PER FILE. Fourteen of the seventeen
// api/*-auth.js files recorded NOTHING when a `setup` action granted an
// employee credential -- no row, no `created_by`, nothing. (Reported by hover2
// as seq958, which put the figure at 15 of 17; the real figure is 14 of 17,
// because api/law-auth.js DOES audit its setup through a local `audit()`
// wrapper and a scan keyed on the string `writeAuditLog` cannot see it.)
//
// The fix needs a table name in each of those files, and a table name repeated
// in fourteen files is fourteen chances to mistype one -- and a mistyped name
// does not fail loudly here, it lands in the `AUDIT_TABLES` refusal below and
// becomes a server-log line nobody reads. So the name is DERIVED from the app
// id the file already has, in one place, and the allowlist is derived from the
// same object rather than maintained beside it. Two lists that must agree is
// the defect shape SD_SESSION_GATED and SD_GATE_APP pay for in api/sd-data.js.
//
// THE NAMES COME FROM docs/2026-10-07-hank-migration-sql-for-michael.md, which
// prints the DDL for twelve of these tables (STEPS 1-12) plus sairnvet_audit_log
// (STEP 13 / 13-ALT, decided 2026-10-08). THIRTEEN OF THEM DO NOT EXIST IN
// SUPABASE YET and that is said here rather than left to be discovered: until
// Michael runs that SQL, `writeAuditLog` gets a 404 from PostgREST, returns
// false, and every caller below surfaces `attributed: false`. The grant still
// succeeds -- a logging outage must never block a legitimate grant -- but the
// caller is told the attribution did not land. THAT IS NOT THE SAME AS FIXED,
// and the two apps whose tables already exist are the two that work today:
// stonedesk_sub (stonedesk_audit_log) and sairnlaw.
//
// `stonedesk_sub` AND `stonedesk` DELIBERATELY SHARE ONE TABLE. The sub-
// contractor credential is a credential on a StoneDesk licence; splitting its
// provisioning history into a second table would mean "who was granted access
// to this licence" could not be answered by one query.
const AUDIT_TABLE_BY_APP = {
  sairnlaw: 'sairnlaw_audit_log',
  sairncode: 'sairncode_audit_log',
  stonedesk: 'stonedesk_audit_log',
  stonedesk_sub: 'stonedesk_audit_log',
  sairncare: 'sairncare_audit_log',
  sairnbuild: 'sairnbuild_audit_log',
  sairndental: 'sairndental_audit_log',
  sairngrounds: 'sairngrounds_audit_log',
  sairnlegacy: 'sairnlegacy_audit_log',
  sairnmechanical: 'sairnmechanical_audit_log',
  sairnroofing: 'sairnroofing_audit_log',
  sairnbiz: 'sairnbiz_audit_log',
  sairnscape: 'sairnscape_audit_log',
  sairndesign: 'sairndesign_audit_log',
  sairnsenior: 'sairnsenior_audit_log',
  sairnfreedom: 'sairnfreedom_audit_log',
  sairnvet: 'sairnvet_audit_log'
};
// DERIVED, NOT A SECOND LIST. This read
//   { sairnlaw_audit_log: true, sairncode_audit_log: true, stonedesk_audit_log: true }
// as a hand-written object. It is now computed from the map above so a name can
// never be in one and absent from the other.
//
// WHAT THE DERIVATION COSTS, said plainly: before this, an audit write for an
// app with no table was refused here with `unknown table`, which read as "not
// provisioned". Now it reaches PostgREST and fails with a 404 instead. Both end
// in a server-log line and `return false`, so no caller's behaviour changes --
// but the WORDING of the log line does, and anyone grepping for the old string
// should know why it stopped appearing.
const AUDIT_TABLES = {};
Object.keys(AUDIT_TABLE_BY_APP).forEach(function (app) {
  AUDIT_TABLES[AUDIT_TABLE_BY_APP[app]] = true;
});
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

// ── THE `setup` ATTRIBUTION, SHAPED ONCE (2026-10-11) ───────────────────────
// WHAT WAS WRONG, and it is the same gap in fourteen files: a `setup` action on
// an api/*-auth.js endpoint writes a PIN credential row for another employee --
// it is the moment access is GRANTED -- and it recorded nothing. The row it
// writes carries no `created_by`. Meanwhile `set_active` in those same files
// audits every outcome including its refusals. So REVOKING access was
// reconstructible and GRANTING it was not, which is the wrong way round.
//
// WHY A HELPER AND NOT SIX COPIED LINES. api/sc-auth.js and api/sd-auth.js
// already carry the fix as six hand-written lines each, and they agree today.
// Copying them a further fourteen times is the propagation this platform's own
// convention warns about -- byte-identical is not safe-in-context, and the
// thing that actually drifts here is not the call, it is the EVENT TYPE STRING
// and the DETAIL KEYS. `event_type` has to match a CHECK constraint in the
// table DDL; the detail keys have to match across apps or no cross-app query
// can read them. Both now live here, once.
//
// THE DETAIL SHAPE IS sc-auth's AND sd-auth's, NOT A NEW ONE:
//   { target: <employee being granted>, granted_role: <role granted> }
// chosen so the two files that already work do not have to change and no
// divergence is created. Converting them to call this helper is available and
// is NOT done here -- they are correct, and rewriting working audit paths to
// route through new code is a risk with no finding behind it.
//
// api/law-auth.js IS LEFT ALONE AND THE REASON IS NOT TIMIDITY. It audits its
// setup already, through a local `audit()` wrapper, but with a different stored
// shape: `{ employee_id, role, detail: { by } }` -- a `detail` key nested
// inside `detail`. Normalising that would change the recorded shape of rows
// ALREADY IN a live legal-sector audit table, which is a data decision and not
// a side-effect of closing an unrelated gap. Reported rather than changed.
//
// FAILS CLOSED ON AN UNKNOWN APP. An app id with no entry in
// AUDIT_TABLE_BY_APP returns false and logs which app, rather than falling back
// to DEFAULT_AUDIT_TABLE -- a mis-spelled app id must not quietly file one
// app's credential grants into another app's audit log.
//
// BEST-EFFORT, LIKE writeAuditLog. The return value is the point: a caller
// surfaces it as `attributed`, because an unrecorded attribution and a recorded
// one are otherwise indistinguishable to whoever just granted the access.
async function auditPinSetup(supabaseUrl, serviceKey, { app, license_hash, caller, target, granted_role }) {
  const table = AUDIT_TABLE_BY_APP[app];
  if (!table) {
    console.error('audit pin_setup refused: no audit table is mapped for app', app);
    return false;
  }
  return writeAuditLog(supabaseUrl, serviceKey, {
    license_hash: license_hash,
    employee_id: caller && caller.employee_id,
    role: caller && caller.role,
    event_type: 'pin_setup',
    detail: { target: target, granted_role: granted_role },
    table: table
  });
}

module.exports = { writeAuditLog, auditPinSetup, AUDIT_TABLE_BY_APP };
