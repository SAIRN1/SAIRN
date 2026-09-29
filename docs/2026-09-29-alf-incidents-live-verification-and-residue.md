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

---

# 2026-09-29 — `alf_mar` actor identity, live-verified, and its residue

Same licence (`ALF-AUDIT-2026`), same session (`zz-audit-owner`, role `owner`),
driven against the deployed endpoint after `d6d7efd1` reached `origin/main`.

**Observed values. Every write sent a forged actor naming `emp-someone-else`:**

```
                     write   WRITE-ECHO                        READ-BACK
administration       200     administered_by='zz-audit-owner'  administered_by='zz-audit-owner'
count                200     counted_by='zz-audit-owner'       counted_by='zz-audit-owner'
reconciliation       200     reconciled_by='zz-audit-owner'    reconciled_by='zz-audit-owner'
assessment_refusal   200     documented_by='zz-audit-owner'    documented_by='zz-audit-owner'
```

**Both hops, deliberately.** The write echo and a separate read are reported as
two columns because they are two claims. On 2026-09-28 `alf_incidents` stored a
correct column and served a blob spread over it, so the echo and the read
disagreed and only the read was wrong.

**The cross-type arm, live.** A `count` carrying a forged `administered_by`,
`reconciled_by` *and* `documented_by`:

```
ZZ-MAR-SMUGGLE   {'counted_by': 'zz-audit-owner', 'witness_id': 'zz-witness'}
```

None of the three foreign actor keys is stored. Only the one belonging to a
`count` is, and it comes from the session.

**`witness_id` survives, as designed** — `'zz-witness'` is present on both count
rows. It names a second person who is by definition not the caller. **SAIRNcare
still has no server-side witness verification of any kind**; that is registered
as its own HIGH finding and is *not* addressed by this change.

## Residue — `alf_mar` and `alf_clients` are APPEND-ONLY

Both refuse `soft_delete` and `delete` with `400 action must be 'read' or
'write'`, driven in both directions rather than assumed. Six rows need a human in
the SQL editor.

```sql
-- VERIFY FIRST. Expect one alf_clients row and five alf_mar rows.
select 'alf_clients' as t, client_id as id from public.alf_clients
 where app_id = 'sairncare' and client_id = 'ZZ-MAR-RESIDENT'
union all
select 'alf_mar', entry_id from public.alf_mar
 where app_id = 'sairncare'
   and entry_id in ('ZZ-MAR-ADMINI','ZZ-MAR-COUNT','ZZ-MAR-RECONC',
                    'ZZ-MAR-ASSESS','ZZ-MAR-SMUGGLE');

delete from public.alf_mar
 where app_id = 'sairncare'
   and entry_id in ('ZZ-MAR-ADMINI','ZZ-MAR-COUNT','ZZ-MAR-RECONC',
                    'ZZ-MAR-ASSESS','ZZ-MAR-SMUGGLE');

delete from public.alf_clients
 where app_id = 'sairncare' and client_id = 'ZZ-MAR-RESIDENT';
```

**Order matters and is not cosmetic:** the MAR rows reference the resident, so
the resident goes last. If the `select` returns fewer rows than named, stop and
read — a delete matching nothing reports success.

## What this does not claim

It does not claim anything about a role other than `owner`, about the offline
replay path in `sairncare.html` (which writes to local storage first and syncs
after), or about rows written before `d6d7efd1`. **Every `alf_mar` row written
before that commit carries an actor field that was supplied by the request**, and
there is no way to tell which of those values are correct. No backfill is
possible: the only candidate source is the forgeable field itself.

---

# 2026-09-29 — ALL live-verification residue on ALF-AUDIT-2026, one block

**Enumerated from the live endpoint, not recited from memory** — every id below
was read back through `action: 'read'` on 2026-09-29 immediately before this was
written. Counts observed: 4 `alf_family_contacts`, 5 `alf_mar`, 1 `alf_clients`,
2 `alf_incidents`, 3 credentials.

**Scoped by LICENCE HASH, and the hash is DERIVED rather than copied:**
`sha256('ALF-AUDIT-2026')` =
`7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c`, confirmed
against the `license_hash` on a real row returned by the endpoint today. Scoping
on the hash rather than on `app_id` alone means a paste that lands in the wrong
database deletes nothing instead of deleting somebody's real facility.

**Nothing here was deleted by me.** `alf_mar`, `alf_clients`,
`alf_family_contacts` and `alf_incidents` all refuse `delete` and `soft_delete`
with `400 action must be 'read' or 'write'` — driven in both directions, not
assumed. These need a human in the SQL editor.

**DELETE ORDER, and it is not cosmetic.** Children before parents:

1. `alf_mar` and `alf_incidents` — both reference `resident_id`
2. `alf_family_contacts` — also references `resident_id`
3. `alf_clients` — the resident every row above points at, last
4. the two deactivated credentials, independent of the rest

```sql
-- ═══════════════════════════════════════════════════════════════════════
-- ALF-AUDIT-2026 live-verification residue, 2026-09-29.
-- SELECT first. DELETE second. CONFIRM third. Run the three in that order.
-- If any SELECT returns a different count from the one in its comment, STOP
-- and read -- a delete that matches nothing reports success, and "0 rows" is
-- indistinguishable from "nothing needed changing".
-- ═══════════════════════════════════════════════════════════════════════

-- ── 1. SELECT -- expect 4 + 5 + 1 + 2 = 12 rows, and 2 credentials ──────
select 'alf_family_contacts' as t, contact_id as id, '' as extra
  from public.alf_family_contacts
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c'
   and contact_id in ('ZZ-FC-BADCONSENT','ZZ-FC-OK','ZZ-FC-DEFAULT','ZZ-FC-RESTAMP')
union all
select 'alf_mar', entry_id, entry_type
  from public.alf_mar
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c'
   and entry_id in ('ZZ-MAR-ADMINI','ZZ-MAR-COUNT','ZZ-MAR-RECONC',
                    'ZZ-MAR-ASSESS','ZZ-MAR-SMUGGLE')
union all
select 'alf_incidents', entry_id, coalesce(recorded_by,'(null)')
  from public.alf_incidents
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c'
   and entry_id in ('ZZ-AUDIT-INC-CAREGIVER','ZZ-AUDIT-INC-NURSING')
union all
select 'alf_clients', client_id, ''
  from public.alf_clients
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c'
   and client_id = 'ZZ-MAR-RESIDENT'
order by 1, 2;

-- The two credentials, separately -- expect 2, both active = false.
select employee_id, role, active
  from public.alf_employee_auth
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c'
   and employee_id in ('zz-audit-caregiver','zz-audit-nursing')
order by employee_id;

-- ── 2. DELETE -- children first, the resident last ─────────────────────
delete from public.alf_mar
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c'
   and entry_id in ('ZZ-MAR-ADMINI','ZZ-MAR-COUNT','ZZ-MAR-RECONC',
                    'ZZ-MAR-ASSESS','ZZ-MAR-SMUGGLE');

delete from public.alf_incidents
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c'
   and entry_id in ('ZZ-AUDIT-INC-CAREGIVER','ZZ-AUDIT-INC-NURSING');

delete from public.alf_family_contacts
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c'
   and contact_id in ('ZZ-FC-BADCONSENT','ZZ-FC-OK','ZZ-FC-DEFAULT','ZZ-FC-RESTAMP');

-- The resident LAST: every row above points at it.
delete from public.alf_clients
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c'
   and client_id = 'ZZ-MAR-RESIDENT';

-- The two deactivated probe credentials. zz-audit-owner is NOT here and must
-- NOT be added: bootstrap only works on a licence with zero credentials, so
-- deleting the sole owner strands ALF-AUDIT-2026 with no product-level way back
-- in. It is left active deliberately.
delete from public.alf_employee_auth
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c'
   and employee_id in ('zz-audit-caregiver','zz-audit-nursing');

-- ── 3. CONFIRM -- every count must be 0, and the owner must still be 1 ──
select 'alf_family_contacts' as t, count(*) as remaining from public.alf_family_contacts
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c'
   and contact_id like 'ZZ-%'
union all
select 'alf_mar', count(*) from public.alf_mar
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c'
   and entry_id like 'ZZ-%'
union all
select 'alf_incidents', count(*) from public.alf_incidents
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c'
   and entry_id like 'ZZ-%'
union all
select 'alf_clients', count(*) from public.alf_clients
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c'
   and client_id like 'ZZ-%'
union all
select 'zz credentials', count(*) from public.alf_employee_auth
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c'
   and employee_id in ('zz-audit-caregiver','zz-audit-nursing')
union all
select 'OWNER (must stay 1)', count(*) from public.alf_employee_auth
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c'
   and employee_id = 'zz-audit-owner'
order by 1;
```

**The `LIKE 'ZZ-%'` in the confirm step is deliberate and is wider than the
delete.** The deletes name exact ids; the confirm asks whether ANY probe row
remains under that prefix, so a row some later run created and nobody listed
shows up here rather than staying invisible.

**Still outstanding and NOT in this block:** `ZZ-VERIFY-RECORDEDBY` in
`alf_incidents` on **ALF-TEST-2026** — a different licence
(`sha256` = `6dd308f1270f2bd66d5be5f8815c09007390b16e7846bd2b6f27f65f8209c3dd`),
with its own SQL earlier in this document. It is deliberately not merged into
this block: one paste that spans two licences is one paste that can go wrong on
the wrong one.
