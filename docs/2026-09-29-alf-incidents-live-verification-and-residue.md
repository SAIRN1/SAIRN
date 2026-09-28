# alf_incidents attribution — the live run, its observed values, and its residue

**2026-09-29 (Fourth).** Two things live here because neither belongs in a
commit message: the **evidence** that the care-role self-scope was driven
against a real deployment, and the **residue** that driving it left behind.

The first exists because a promise in a commit message is write-only. On
2026-09-27 the attribution fix shipped saying *"LIVE RE-VERIFICATION IS STILL
OWED"* — accurate, in the right place, and the last anybody would have heard of
it; the next day the live run found the fix did not work. `tools/verification_owed_report.py`
now reads those sentences, and **a clearance it computes from file overlap is
not the same as a record of what was actually observed.** This is that record.

---

## What was driven, and where

**Licence: `ALF-AUDIT-2026`.** Not a demo-facing licence. Credentials were
created through the product's own `bootstrap` and `setup` actions and
**deactivated afterwards**, rather than seeded by SQL.

| Role | Employee id | Created via | State now |
|---|---|---|---|
| owner | `zz-audit-owner` | `alf-auth` `bootstrap` | **active** — see residue |
| caregiver | `zz-audit-caregiver` | `alf-auth` `setup` | deactivated |
| nursing | `zz-audit-nursing` | `alf-auth` `setup` | deactivated |

## Observed values

Each of the two non-management roles filed one incident, **both carrying a
forged `reported_by` AND a forged `recorded_by` in the payload**:

```
caregiver write -> 200   reported_by present in stored blob: False
nursing   write -> 200   reported_by present in stored blob: False

caregiver read  -> 200   scoped_to_self=True    rows=1  ids=['ZZ-AUDIT-INC-CAREGIVER']
                         recorded_by seen:      ['zz-audit-caregiver']
nursing   read  -> 200   scoped_to_self=False   rows=2  (both incidents)
owner     read  -> 200   scoped_to_self=False   rows=2  (both incidents)
```

Deactivation, through the product:

```
set_active zz-audit-caregiver false -> 200 {"active": false, "remaining_admins": 1}
set_active zz-audit-nursing   false -> 200 {"active": false, "remaining_admins": 1}
roster: zz-audit-caregiver active=False | zz-audit-nursing active=False
        zz-audit-owner     active=True
```

### The four claims, and which of them this settles

1. **A forged `reported_by` is ignored.** Settled — absent from the stored blob
   on both writes.
2. **A care role reads only its own filings.** Settled — one row, its own, with
   `scoped_to_self=True`.
3. **A care role cannot read another employee's.** Settled — the nursing
   employee's incident did not appear, and the nursing session proves the row
   exists and is readable by somebody.
4. **Management reads all.** Settled for owner *and* nursing.

**Not settled here: legacy `recorded_by IS NULL` rows.** `ALF-AUDIT-2026` was
created after the migration, so it has none. The in-process suite covers it
(`api/sd-data-alf-caregiver-scope.test.js`, arm *"a LEGACY row with recorded_by
NULL is invisible to the care tier"*) — **which is the evidence class that
missed the read-path override**, and that is why it is named here as a gap
rather than folded into the four above.

### A detail worth keeping

The **write response** reports `recorded_by` as `None` while the **read**
returns the correct value. That is not a defect: the incidents write echo maps
from the request body, and `recorded_by` is added to the row rather than the
body. It is recorded because a reader comparing the two responses would
otherwise reasonably suspect one.

### A mistake this run corrected

The first deactivation attempt returned **400** and my script printed `OK`,
because it read `error.code` and a 400 without that field rendered as success.
`api/_lib/employee-lifecycle.js:195` requires a `reason` when deactivating.
**A cleanup step that cannot fail loudly is a cleanup step that does not
happen** — the credentials were live for the minutes between.

---

## Residue, with its deletion path

### On `ALF-AUDIT-2026` — from this run

| Object | Id | Why it cannot be removed through the product | Deletion path |
|---|---|---|---|
| `alf_incidents` row | `ZZ-AUDIT-INC-CAREGIVER` | append-only: the resource accepts `read` and `write` only | SQL below |
| `alf_incidents` row | `ZZ-AUDIT-INC-NURSING` | same | SQL below |
| credential | `zz-audit-owner` | **kept active on purpose** | see below |

`zz-audit-owner` is **left active deliberately**. `bootstrap` works only while a
licence has **zero** credential rows, so deactivating the sole owner would make
the audit licence unusable for the next live verification with no way to recover
it through the product. It is the licence's provisioning account, on an audit
licence, and that is what an audit licence is for. Deactivate it only when
retiring the licence.

### On `ALF-TEST-2026` — from the earlier run, on a demo-facing licence

One `alf_incidents` row, `ZZ-VERIFY-RECORDEDBY`, written before
`ALF-AUDIT-2026` existed. **That was the wrong licence** and it is why hank's
`sql/audit_license_seed_2026-09-28.sql` exists.

## SQL — for Michael to run

Select first. Nothing here is scoped by anything but the entry id and the app.

```sql
-- 1. The demo-licence residue. VERIFY: expect exactly one row.
select entry_id, recorded_by, created_at
  from public.alf_incidents
 where app_id = 'sairncare'
   and entry_id = 'ZZ-VERIFY-RECORDEDBY';

delete from public.alf_incidents
 where app_id = 'sairncare'
   and entry_id = 'ZZ-VERIFY-RECORDEDBY';

-- 2. The audit-licence residue. VERIFY: expect exactly two rows.
select entry_id, recorded_by, created_at
  from public.alf_incidents
 where app_id = 'sairncare'
   and entry_id in ('ZZ-AUDIT-INC-CAREGIVER', 'ZZ-AUDIT-INC-NURSING');

delete from public.alf_incidents
 where app_id = 'sairncare'
   and entry_id in ('ZZ-AUDIT-INC-CAREGIVER', 'ZZ-AUDIT-INC-NURSING');
```

Both deletes are scoped on `entry_id` and `app_id` and nothing else. **If the
first `select` returns no rows, do not run the `delete`** — a delete matching
nothing reports success, and "0 rows" is indistinguishable from "nothing needed
changing", which is the argument `tools/sairn_sql_preflight.py` is built on.

---

## What this does not claim

It does not claim the deployment is correct for any role other than the three
driven, on any resource other than `alf_incidents`, or for a licence other than
`ALF-AUDIT-2026`. And it does not claim the legacy-NULL behaviour has been seen
live — it has not.
