# REMOVAL PATHS for the four resources that have none — `sv_scribe_consent` first — 2026-10-14, fourth b17

**ROUTED TO hank (`api/`, `sql/`) and cody (`tests/`). SPEC ONLY — nothing
outside `docs/` is written here.**

**THE FINDING THIS ANSWERS, re-measured at this HEAD:**

```
CMD python tools/removal_path_check.py                       ->  EXIT 1
  keyed, no removal path, and NOT in the baseline : 4
    - alf_family_contacts      (sairncare)        upserts on (license_hash, id)
    - mech_insurance_policies  (sairnmechanical)  upserts on (license_hash, id)
    - sf_trustee_audits        (sairnfreedom)     id column trustee_audit_id
    - sv_scribe_consent        (sairnvet)         id column scribe_consent_id
  grandfathered in the baseline : 321
```

The tool's own sentence: *a record written to one of these cannot be removed
through the product — only by hand in the SQL editor.* **All four arrived after
the baseline was cut, which is what the baseline is for.**

---

## 1. THE PATTERN — `soft_delete`, because all four are Tier A

**This platform already has the right shape and it is not a new design.**

```
CMD grep -nE "REMOVAL_VERBS" tools/removal_path_check.py
    89  REMOVAL_VERBS = ('delete', 'soft_delete')
CMD grep -n "action === 'soft_delete'" api/sd-data.js
    4297   (sd_customers -- the reference implementation)
CMD sed -n '17701,17716p' api/sd-data.js
    'delete' on a Tier A record -> 403 SOFT_DELETE_ONLY,
    "cannot be destroyed. Use action 'soft_delete', which hides the record and
     keeps the row." … "Two verbs that destroy different amounts of data must
     not share a name."
```

**So for each of the four: declare `soft_delete` in the verb registry, mark the
row, keep it, and refuse hard `delete` with `403 SOFT_DELETE_ONLY`.**

`sd_customers` (`api/sd-data.js:4297-4330`) is the implementation to copy, and
it already encodes the four things that make a removal path honest:

| it does | and the reason, in its own words |
|---|---|
| reads the row first | so it can tell "removed" from "never existed" |
| **404 when there is no server row** | *"NOT A SILENT SUCCESS … saying 'deleted' would be reporting work that did not happen"* |
| **`already_deleted: true` and a 200 when `_deleted_at` is set** | idempotent, and it says so rather than pretending to act twice |
| stamps `_deleted_at` **and** `_deleted_by` from the **verified session** | the row records who, not what the caller claimed |

**`503 NOT_PROVISIONED`** when the table is absent is the fifth, and it is the
fail-closed one.

---

## 2. `sv_scribe_consent` — FIRST, because it is a CONSENT record

**A consent that cannot be withdrawn through the product is the sharpest of the
four.** It is also one of the 42 resources my b15 SAIRNvet role matrix gates,
where `sv_scribe_consent` write is `owner`/`dvm` only.

### 2.1 What withdrawal must do

**WITHDRAWAL IS RECORDED, THE AUDIT TRAIL IS KEPT.** A withdrawn consent is not
an absent consent: the practice must still be able to show that consent existed
for the period it covered, and that it was withdrawn on a date by a named
person. **Destroying the row destroys the defence.**

```js
// action: 'soft_delete'  -- the ONLY removal verb for this resource
// payload: { id, withdrawn_reason }   // reason REQUIRED, see 2.2
// marks:   _withdrawn_at, _withdrawn_by (verified session), _withdrawn_reason
// keeps:   every original field, including the consent's own effective dates
// refuses: action 'delete'  -> 403 SOFT_DELETE_ONLY
```

**AND ONE THING THE OTHER THREE DO NOT NEED: an audit row.**
`sv_audit_log` is this app's dosing trail and is append-only. **A consent
withdrawal is exactly the class of event it exists for**, so the withdrawal
writes `event_type` `'scribe_consent_withdrawn'` **and the CHECK list must gain
that value in the same migration** — `sql/sairnvet_audit_log_schema.sql`'s
`event_type ... check (event_type in (...))` refuses an unlisted value, and
this platform has shipped silently-rejected audit writes before.

### 2.2 Why the reason is required and the write must fail without it

**A withdrawal with no reason is indistinguishable from a mis-click**, and the
record is evidence. `400` with the field named, not a default of `''`.

### 2.3 Who may do it

**`owner` / `dvm` only** — the same pair that may write it
(`api/sv-auth.js:118` `PRESCRIBER_ROLES`). **A consent withdrawn by somebody
who could not have taken the consent is a worse record than no withdrawal.**

### 2.4 The failing-first test arm — cody

```js
// tests/sv_scribe_consent_withdrawal.test.js
// S1  BAD INPUT, AND IT MUST FAIL BEFORE THE CODE EXISTS:
//     action 'soft_delete' on sv_scribe_consent -> today the envelope refuses
//     the verb (the registry does not grant it). THAT REFUSAL IS THE RED.
//     After hank's change: 200, row still present, _withdrawn_at set.
// S2  action 'delete' -> 403 SOFT_DELETE_ONLY, and the row is UNTOUCHED
//     (assert by re-reading, not by the status).
// S3  'soft_delete' with no withdrawn_reason -> 400, and NOTHING written
//     (assert the upstream call count is zero).
// S4  a 'tech' token -> 403. A 'dvm' token -> 200. The role pair, both ways.
// S5  the audit row: sv_audit_log gains exactly ONE
//     'scribe_consent_withdrawn' row naming the verified employee_id.
// S6  THE CHECK-LIST HAZARD: with 'scribe_consent_withdrawn' absent from the
//     event_type CHECK, the withdrawal must FAIL LOUDLY (5xx) and the consent
//     must NOT be marked withdrawn. A withdrawal whose audit row was rejected
//     must not report success.
// S7  idempotence: a second 'soft_delete' -> 200 with already_withdrawn: true,
//     and _withdrawn_at UNCHANGED.
// S8  CONTROL: an ordinary write to a live consent still works for owner/dvm.
```

**S6 is the arm that matters most and the one most likely to be cut.** It is
the `T7` shape from the AI spec, applied here: **the audit write and the state
change must succeed or fail together.**

---

## 3. `alf_family_contacts` — a person asking to be forgotten

**sairncare. Upserts on `(license_hash, id)`.** This holds **a named family
member's contact details** in an assisted-living record, and it is the one of
the four where the subject of the data may be the one asking for removal.

```js
// action: 'soft_delete'   payload: { id, removed_reason? }   // reason OPTIONAL
// marks:  _deleted_at, _deleted_by (verified session)
// keeps:  the row, so the care record's history of who was contacted stays true
// refuses: 'delete' -> 403 SOFT_DELETE_ONLY
```

**WHY SOFT AND NOT HARD, even though this is the closest thing to a
right-to-be-forgotten case:** the MAR and incident records reference *who was
notified*. **A hard delete turns "we called her daughter at 02:10" into "we
called somebody".** If a true erasure is ever required, that is a separate,
deliberate operation with its own authority — **not this verb**, and not a
quiet reuse of it.

**Who:** the app's management tier. **Not** `caregiver`.

### The failing-first arm — cody

```
A1  'soft_delete' before the change -> refused by the envelope. THE RED.
A2  after: 200, row present, _deleted_at set, _deleted_by = verified employee.
A3  a soft-deleted contact DISAPPEARS from the contacts read and STILL RESOLVES
    in an incident/MAR notification lookup -- the arm that proves §3's argument
    rather than asserting it.
A4  'delete' -> 403 SOFT_DELETE_ONLY, row untouched.
A5  CONTROL: a caregiver token -> 403, and nothing written.
```

**A3 is the point of this resource's spec.** Without it, "we kept the row"
is a claim about the database rather than about the product.

---

## 4. `sf_trustee_audits` — an ORC 2915 controls record

**sairnfreedom, id column `trustee_audit_id`, verbs today `['read','write']`
(`api/sd-data.js:1013`).** The registry comment already says what it is:
*"WHO attested to the post's financial controls, and the fidelity bond covering
the people who handle gaming receipts."*

```js
// action: 'soft_delete'  ONLY. Hard delete is never granted for this resource.
// payload: { id, superseded_reason }    // REQUIRED
// marks:  _deleted_at, _deleted_by, _superseded_reason
// refuses: 'delete' -> 403 SOFT_DELETE_ONLY, permanently
```

**THIS IS THE ONE WHERE THE REMOVAL PATH IS NOT FOR REMOVING ANYTHING.** A
statutory controls attestation is not deleted because somebody changed their
mind; it is **corrected**, and the correction must leave both the original and
the reason visible. **Owner-only** — the same stance
`LAW_RECONCILE_ROLES` takes on trust reconciliation.

### The failing-first arm — cody

```
F1  'soft_delete' before the change -> refused. THE RED.
F2  after: 200, row present, both _deleted_at and _superseded_reason set.
F3  no superseded_reason -> 400, nothing written.
F4  'delete' -> 403 SOFT_DELETE_ONLY -- and this arm must pass FOREVER, not
    only until somebody decides a hard delete would be convenient.
F5  a non-owner officer token -> 403.
F6  CONTROL: the read path still returns soft-deleted rows to the owner with
    their marks, because a hidden statutory record is worse than a visible
    withdrawn one.
```

**F6 inverts the usual rule and that is deliberate** — for this resource the
owner must still see what was superseded.

---

## 5. `mech_insurance_policies` — the ordinary case, spec'd last on purpose

**sairnmechanical. Upserts on `(license_hash, id)` (`api/sd-data.js:3012`).**
A policy record: a certificate of insurance with dates.

```js
// action: 'soft_delete'   payload: { id }
// marks:  _deleted_at, _deleted_by
// refuses: 'delete' -> 403 SOFT_DELETE_ONLY
// Who: management.
```

**No reason field, no audit row, no special read behaviour.** A lapsed or
mis-entered policy is removed from the working list and the row stays for
history. **It is listed last because it needs the least argument** — and
because a spec that treats all four identically would have missed §2's audit
coupling and §4's never-delete stance.

### The failing-first arm — cody

```
M1  'soft_delete' before the change -> refused. THE RED.
M2  after: 200, row present, marks set.
M3  'delete' -> 403 SOFT_DELETE_ONLY.
M4  a soft-deleted policy is excluded from the coverage-gap calculation if one
    exists -- otherwise a removed policy still "covers" a job.
M5  CONTROL: a live policy still reads and writes normally.
```

---

## 6. THE ORDER, AND WHAT CLOSES THE FINDING

1. **`sv_scribe_consent`** — a consent nobody can withdraw.
2. **`alf_family_contacts`** — a named person's details, with A3 as the proof.
3. **`sf_trustee_audits`** — statutory, owner-only, never destroyed.
4. **`mech_insurance_policies`** — the ordinary one.

**Each lands as: the verb in the registry map, the branch in `api/sd-data.js`,
any `sql/` CHECK-list change in the SAME migration, and cody's arms.**

**AND THE FINDING IS NOT CLOSED BY A BASELINE ROW.** Four rows added to
`docs/removal-path-baseline` would make
`python tools/removal_path_check.py` exit 0 tomorrow and would be the wrong
answer for all four: **a consent, a named person's contact details, a statutory
attestation and an insurance certificate are not the kind of record you
grandfather.** If any of them is genuinely un-removable by design, that is a
baseline row **with a reason** — and I cannot see which of the four that would
be.

---

## 7. WHAT THIS SPEC DOES NOT DO

* **It does not implement anything.** No `api/`, `sql/` or `tests/` file is
  touched; `docs/` is this batch's only writer.
* **It does not decide the erasure question** in §3. If a true hard erasure is
  ever required for a family contact, that is a separate authority and a
  separate verb.
* **It does not re-examine the 321 grandfathered resources.** It answers the
  four the checker reports as new.
* **It does not claim `soft_delete` is enough for a regulator.** It is enough to
  make the record removable through the product and auditable afterwards, which
  is what the checker measures and what the product currently lacks.
