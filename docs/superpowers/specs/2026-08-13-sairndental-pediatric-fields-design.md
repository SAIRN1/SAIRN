# SAIRNdental Pediatric Fields — Design Spec

**Date:** 2026-08-13
**Status:** Approved, ready for implementation planning

## Problem

SAIRNdental's patient record (`dnt_patients`) has no concept of a minor
patient. Every patient is treated identically: one `phone`/`email` pair is
the only contact info on file. For a minor patient, the person who actually
needs to be reached for appointment reminders, billing, and treatment
consent is the parent/guardian — not (or not only) the patient. Today there
is no field anywhere in the app to record that person.

## Current State (verified against the real code)

- `dnt_patients` (`sql/sairndental_data_schema.sql:35-39`) is a JSONB-blob
  table — one row per patient, all real fields live inside the `data`
  column as JSON, enforced by app code only, not SQL column constraints.
  Adding fields here requires no migration.
- The Add Patient form (`sairndental.html:257-271`) captures `name`, `dob`
  (a real `<input type="date">`), `phone`, `email`, `insurance_payer`,
  `insurance_member_id`. `addPatient()` (`sairndental.html:677-689`) builds
  the record, requires only `name` to be non-empty, saves it locally
  (`st('dnt_patients_list', list)`), re-renders the table, and attempts a
  best-effort server sync via `sdnData('write', 'dnt_patients', rec)`.
- The Patients table (`sairndental.html:272-274`, rendered by `rPatients()`
  at `:668-676`) shows Name / DOB / Phone / Payer / Member ID / Remove,
  with `--` as the established convention for any empty optional field.
- There is no edit flow for any resource in this app (patients, providers,
  operatories, etc.) — every panel is add/remove only. This is a platform-
  wide convention (confirmed by grepping for `edit` handlers across all
  patient/provider/operatory functions — none exist), not something this
  feature should introduce on its own.
- Automated reminders and billing statements are explicitly not wired to
  send/use contact data yet — the Dashboard panel's own text
  (`sairndental.html:249`) states real-time balance, self-scheduling,
  automated reminders, and denial/A/R/revenue reporting are "built on top
  of this foundation in separate follow-up work." The Billing panel
  (`sairndental.html:443-466`) tracks charges/payments only; it has no
  statement-recipient or contact-display logic today.

## Scope

**In scope:**
- Add four new fields to the `dnt_patients` record: `guardian_name`,
  `guardian_relationship`, `guardian_phone`, `guardian_email`.
- Auto-detect minor status from `dob` (age < 18 as of today) via one
  shared helper function, `isMinorPatient(dob)` — no separate manual
  minor flag.
- Add Patient form: when the entered DOB implies age < 18, show the
  guardian fields (name, relationship dropdown, phone, email) inline in
  the form, live as the DOB field changes.
- Validation: `addPatient()` blocks save (existing toast pattern, e.g.
  `sairndental.html:679`'s "Patient name required") if DOB implies a minor
  and `guardian_name` is empty, or both `guardian_phone` and
  `guardian_email` are empty. Adult patients are unaffected — no new
  validation applies to them.
- Patients table: add one "Guardian" column showing `guardian_name` +
  `guardian_relationship` (e.g. "Jane Doe (Mother)") for minors, `--` for
  adult patients, matching the table's existing `--` convention.

**Explicitly out of scope:**
- No edit-patient flow. The whole app has no edit capability for any
  resource; adding one just for guardian fields would be inconsistent
  scope creep beyond this feature's actual request.
- No changes to reminders, billing statements, or consent-document
  generation. Those systems don't consume contact data today — this
  feature makes the guardian data exist and display correctly so that
  future work on those systems has real data to use, but doesn't build
  those systems now.
- No server-side/SQL validation of the minor-requires-guardian rule.
  `dnt_patients` is a JSONB blob with no column-level constraints on any
  existing field either (not even `name`, which the client already
  requires) — this feature matches that existing pattern rather than
  introducing a new, inconsistent enforcement layer at the DB level for
  just this one field set.

## Design

### Data model

Four new optional string fields added to the patient record object built
in `addPatient()`, alongside the existing `insurance_group_number`/
`insurance_plan_type` blank-string pattern:

```js
guardian_name: '', guardian_relationship: '', guardian_phone: '', guardian_email: ''
```

`guardian_relationship` is populated from a dropdown with options Mother /
Father / Legal Guardian / Other — matching the existing `<select>` pattern
already used elsewhere in this file (e.g. Payment Method in the Billing
panel).

### Minor detection

One shared helper:

```js
function isMinorPatient(dob) {
  if (!dob) return false;
  var b = new Date(dob), today = new Date();
  var age = today.getFullYear() - b.getFullYear();
  var m = today.getMonth() - b.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < b.getDate())) age--;
  return age < 18;
}
```

Called from both `addPatient()` (validation) and `rPatients()` (table
rendering) — a single source of truth for the age math, no duplicated
logic that could drift between the two call sites.

An empty/unset DOB is treated as NOT a minor (`return false`) — matching
the form's existing behavior where DOB is optional for adults today; a
patient with no DOB entered is not blocked from being added, and no
guardian fields are forced on them.

### Add Patient form

The guardian field group is a new `<div class="fr">` block in the existing
form (`sairndental.html:257-269`), initially hidden, shown/hidden by an
`onchange`/`oninput` handler on the existing DOB input
(`pt-add-dob`) that calls `isMinorPatient()` and toggles the group's
visibility live as the user types or picks a date — not only checked at
submit time, so staff see the requirement before they try to save.

### Validation (in `addPatient()`)

After the existing `if(!name)` check, add:

```js
var dob = $('pt-add-dob').value;
if (isMinorPatient(dob)) {
  var gName = $('pt-add-guardian-name').value.trim();
  var gPhone = $('pt-add-guardian-phone').value.trim();
  var gEmail = $('pt-add-guardian-email').value.trim();
  if (!gName || (!gPhone && !gEmail)) {
    toast('Guardian name and at least one contact method (phone or email) are required for a minor patient');
    return;
  }
}
```

Guardian fields are read into the record object regardless of minor
status (blank strings for adults, matching every other optional field's
pattern), and cleared in the existing field-reset `forEach` alongside the
other Add Patient inputs after a successful save.

### Display

`rPatients()`'s row template gets one added `<td>`:

```js
H(isMinorPatient(p.dob) && p.guardian_name ? p.guardian_name + (p.guardian_relationship ? ' (' + p.guardian_relationship + ')' : '') : '--')
```

Table header gets one added `<th>Guardian</th>` between Payer and the
trailing Remove-button column, matching the existing column order and
`--` empty-value convention exactly.

## Testing / Verification Plan

- `python tools/checkblocks.py sairndental.html` — confirmed this is the
  real, working syntax-check command for this file (single-script-block
  app; run against it during this spec's own review: `TOTAL_BLOCKS:1`,
  `FAILED_BLOCKS:0` on the current unmodified file).
- Manual verification: add an adult patient (DOB > 18 years ago or blank)
  — confirm no guardian fields appear, save succeeds, table shows `--` in
  the Guardian column.
- Add a minor patient (DOB implying age < 18) with no guardian info —
  confirm save is blocked with the correct toast message.
- Add a minor patient with guardian name + phone only (no email) — confirm
  save succeeds (at least one contact method is enough).
- Add a minor patient with full guardian info — confirm save succeeds and
  the table shows "Guardian Name (Relationship)".
- Confirm an adult patient's own phone/email fields still save and display
  normally, unaffected by this change (regression check on existing
  behavior).

## Open Questions

None — all material design decisions were resolved during brainstorming
(minor detection: auto from DOB; guardian fields: supplement, not replace;
guardian info: required when minor; relationship field: included).
