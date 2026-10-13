# H1 -> hank: leg_monuments inscription-mismatch override has no attribution

Written 2026-10-13, batch b24. First found b23 (seq1359). `api/` is
hank's directory; the fix is client + server (a new column/field), not
a pure client change, so routed rather than left client-only.

## The gap, exact file:line

`sairnlegacy.html:4600-4618`, `saveMonument()`:

```js
async function saveMonument(){
  ...
  var mismatches=monumentMismatches($('mnname').value,$('mndates').value,caseObj);
  if(mismatches.length&&status!=='Draft'&&!$('mnoverride').checked){
    $('monument-err').textContent='Cannot finalize with an unresolved inscription mismatch -- fix it or check the override box';
    return;
  }
  var rec={id:ceid||newId('MN'),case_id:caseId,vendor_name:$('mnvendor').value.trim(),monument_type:$('mntype').value,
    material:$('mnmaterial').value.trim(),inscription_name:$('mnname').value.trim(),inscription_dates:$('mndates').value.trim(),
    inscription_epitaph:$('mnepitaph').value.trim(),status:status,order_date:legLocalToday(),notes:$('mnnotes').value.trim(),created_at:legLocalToday()};
  ...
}
```

`$('mnoverride').checked` gates whether a mismatched, non-Draft save is
allowed through at all -- a real, deliberate decision point. `rec`
(the object actually written to `leg_monuments`) has no field recording
that this decision was made, who made it, or when. A reader of the
saved record cannot tell a clean match from an overridden mismatch
after the fact.

## Why this matters for this specific resource

A funeral home's monument order carries a permanent inscription (name,
dates, epitaph) that gets physically carved. `monumentMismatches()`
exists specifically to catch a typo or a stale case record before that
happens. The override exists for the legitimate case (a nickname, a
deliberate stylistic choice) -- but once the record is saved, "this was
overridden deliberately by a staff member who checked the mismatch
against the real facts" and "the mismatch check simply never ran" are
indistinguishable. If an incorrect inscription ships, there is no
record to show whether it was a caught-and-accepted risk or a silent
miss.

## The audit-event shape needed

Same shape as the credential-deactivation lifecycle this platform
already uses elsewhere (`doAudit()` in `api/_lib/employee-lifecycle.js`,
emitting `credential_deactivated`/`credential_reactivated`/
`credential_change_refused`) -- an attributed event, not just a stored
flag on the record. Minimum fields:

- `event_type`: a new value, e.g. `monument_inscription_override`.
- `actor` / `employee_id`: who checked the override box. `saveMonument()`
  does not currently have a session object in scope at all -- this is
  the real blocker: the resource is written via the generic
  `LEG_RESOURCES` family gate (`api/sd-data.js:14360`), which confirms a
  session exists but does not thread the caller's identity back to the
  client for inclusion on the record. Either the server stamps
  `employee_id` server-side from the verified session (preferred -- the
  client cannot be trusted to self-report who clicked the box), or the
  write path gains a dedicated branch like `bld_draws`'s own
  `dSession.employee_id` pattern.
- `timestamp`: when the override was accepted -- `created_at` on the
  record already exists but is the ORDER date, not necessarily the
  override moment if the record is edited later.
- `mismatch_detail`: what `monumentMismatches()` actually found,
  verbatim -- the same "skipped_findings" principle cc's own per-gate-
  skip design already uses for a different override (the push gate):
  an override log entry that doesn't say what was overridden is a
  field that means nothing.

## Not this role's to decide

Whether this becomes a new `leg_audit_log`-style event, a column on
`leg_monuments` itself, or something else is a design call. This role
names the gap and the shape of evidence a fix should produce; building
it is hank's.
