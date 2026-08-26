---
name: postgres-grant-sweep
description: 'How to safely audit and narrow Postgres/Supabase privileges across many tables at once — excess GRANTs, not missing ones. Trigger whenever a task involves changing what a role (service_role, or any other) is allowed to do on tables: revoking TRUNCATE/DELETE/REFERENCES/TRIGGER, auditing who can do what, writing a schema file''s grant line, reacting to "this role has more than it needs", planning a privilege sweep, or reviewing one someone else wrote. Also trigger on "grant", "revoke", "privilege", "information_schema.role_table_grants", "pg_default_acl", "ALTER DEFAULT PRIVILEGES", "permission denied", "42501", and before writing ANY new `grant ...` line.'
license: MIT
metadata:
  origin: Extracted from three real production grant sweeps, 2026-08
  validation: One codebase, one operator, one stack — see "How far this has been proven"
---

# Grant sweeps: changing privileges without breaking the database

A grant sweep is a change to what a role is *allowed* to do, applied across
many tables at once, usually to remove capability nobody uses. It has an
unusual risk shape: the change is invisible until something that used to work
stops working, and the verification is very easy to write in a way that passes
without proving anything.

**The default outcome of a careless sweep is a green check over a broken
database.** Everything below exists to prevent that specific failure.

## How far this has been proven — read this before relying on it

Stated plainly because the alternative is implying more than is true.

This was extracted from **three real sweeps against one production Postgres
database on Supabase**, run by **one operator**, over roughly three weeks in
2026. Every rule below closed a failure that actually happened on that
database — none is theoretical, and none has been validated anywhere else.
It has never been run against a self-hosted Postgres, a non-Supabase managed
provider, a multi-schema database, or by anyone who did not write it.

What that means in practice: the *reasoning* generalises — catalog-driven
discovery, revoke-then-grant, diffing both directions — and the *specifics*
may not. Treat unfamiliar behaviour on your database as a gap in this
document, not as your database being wrong.

## The safety property that makes this publishable at all

**Nothing here is meant to be executed by an AI agent, and it cannot be.**

`REVOKE` requires the object owner. A pooled application role — Supabase's
`service_role` included — cannot perform these sweeps regardless of what
privileges it holds. A sweep is **always a hand-off to a human with owner-level
SQL access**, who reads Section 1's output and deliberately uncomments Section 2.

If you are reading this with owner credentials in hand: that changes the risk,
not the procedure. Sections 0 and 3 exist precisely because being *able* to run
Section 2 is not the same as being able to prove afterwards what it did.

## The shape: four sections, always in this order

**Section 0 — BASELINE.** Capture the current grant state to a **real table**
before anything mutates.
**Section 1 — DISCOVER.** Query the live catalog for what needs changing.
**Section 2 — FIX.** One `DO` block, commented out by default.
**Section 3 — VERIFY.** Diff post-state against the Section 0 baseline.

Sections 0, 2 and 3 belong to one run. Section 1's output gets *read by a
human* before Section 2 is uncommented.

---

## Rule 1 — Never hand-build the table list

Discover from `information_schema` at run time. A hand-written list is wrong
the moment a table is added, and transcribing ~150 table names is exactly the
manual step that introduces the next bug.

```sql
select t.table_name,
       string_agg(distinct g.privilege_type, ', ' order by g.privilege_type) as privs
from information_schema.tables t
join information_schema.role_table_grants g
  on g.table_name = t.table_name and g.table_schema = t.table_schema
where t.table_schema = 'public' and g.grantee = '<ROLE>'
group by t.table_name
having bool_or(g.privilege_type = '<TARGET>')
order by t.table_name;
```

This also finds tables **neither you nor the last session knew existed**. On the
source database that was not hypothetical: 227 tables were live while the repo
carried grant lines for ~131, and five real tables had no tracked `CREATE TABLE`
anywhere in version control. Any database old enough to have had more than one
person touch it will have some.

## Rule 2 — Revoke-then-grant, preserving exactly what was there

Never `REVOKE <verb>` alone and never re-`GRANT` a fixed verb list. Read what
the table already holds, strip everything, restore precisely that minus the
target:

```sql
DO $$
DECLARE r RECORD; keep_privs TEXT;
BEGIN
  FOR r IN
    SELECT t.table_name,
           string_agg(DISTINCT g.privilege_type, ', ') AS all_privs
    FROM information_schema.tables t
    JOIN information_schema.role_table_grants g
      ON g.table_name = t.table_name AND g.table_schema = t.table_schema
    WHERE t.table_schema = 'public' AND g.grantee = '<ROLE>'
    GROUP BY t.table_name
    HAVING bool_or(g.privilege_type = '<TARGET>')
  LOOP
    SELECT string_agg(priv, ', ') INTO keep_privs
    FROM unnest(string_to_array(r.all_privs, ', ')) AS priv
    WHERE priv IN ('SELECT','INSERT','UPDATE');   -- the verbs to KEEP

    EXECUTE format('REVOKE ALL ON public.%I FROM <ROLE>', r.table_name);
    IF keep_privs IS NOT NULL THEN
      EXECUTE format('GRANT %s ON public.%I TO <ROLE>', keep_privs, r.table_name);
    END IF;

    RAISE NOTICE 'Swept %: kept %', r.table_name,
      coalesce(keep_privs, '(nothing -- held ONLY the target, check it)');
  END LOOP;
END $$;
```

`REVOKE ALL` first is what clears the default-ACL baseline; a bare `GRANT` is
additive and **cannot** remove a privilege the role already holds. A table that
ends with no grants is *reported*, never silently emptied.

## Rule 3 — The baseline goes in a REAL table, not a temp table

The obvious version uses `create temp table grant_baseline as ...`. **Do not.**
A browser-based SQL console does not guarantee two Run clicks share a session,
and a temp table that vanishes between clicks takes the only proof with it —
leaving a mutation applied and nothing to check it against.

Use a real table, capture it before Section 2, drop it deliberately after
Section 3 passes.

## Rule 4 — Verify LOST and GAINED, not "the target is gone"

The most common bad verification checks only that the target privilege
disappeared. A loop bug that dropped `UPDATE` passes that check silently.

Full-outer-join the baseline against the post-run state and expect **zero rows
on both sides**:

```sql
select coalesce(b.table_name, a.table_name) as table_name,
       coalesce(b.privilege_type, a.privilege_type) as privilege_type,
       case when a.table_name is null then 'LOST' else 'GAINED' end as delta
from grant_baseline b
full outer join (
  select table_name, privilege_type
  from information_schema.role_table_grants
  where table_schema='public' and grantee='<ROLE>'
    and privilege_type in ('SELECT','INSERT','UPDATE','DELETE')
) a on a.table_name = b.table_name and a.privilege_type = b.privilege_type
where a.table_name is null or b.table_name is null;
```

**Guard the guard.** If Section 0 under-read, the diff passes vacuously. Assert
a lower bound on the baseline's own row/table count, derived independently from
the discovery output, and treat anything at or below it as a failed capture —
not a pass. On one real run this meant expecting `>739 rows / >194 tables` and
getting `774 / 209`, with the difference reconciled exactly against the repo's
own grant lines.

## The R1–R6 hardening checklist

Findings from a real adversarial review of a sweep that looked finished. Run
all six before any sweep executes.

- **R1 — No baseline, no proof.** Logic correctness is not run correctness. Without Section 0 there is no artifact to diff and Section 3 can only prove a removal, never a survival. *Closed by Rules 3 and 4.*
- **R2 — Do not filter on one privilege when the file is about four.** `having bool_or(privilege_type = 'TRUNCATE')` makes a REFERENCES-only table invisible to the sweep **and to its verification**, so Section 3 reports "clean" over tables still holding it. Widen the `HAVING` in the discovery, the fix, **and** the verify. Add a dedicated query hunting the un-co-occurring case; the main export cannot surface it *by construction*.
- **R3 — Every exclusion must rest on a verified claim.** One table was excluded for "already has zero real CRUD" — disproved by three live 200s. Re-read the excluded table's actual row in Section 1's output before keeping or dropping any exclusion. Do not silently delete one either.
- **R4 — Column grants and `WITH GRANT OPTION` die silently.** `REVOKE ALL ON <table>` strips column-level privileges; the re-`GRANT` restores table-level only. Neither appears in `role_table_grants`. Pre-flight both, expect zero rows:
  - column ACLs — query `pg_attribute.attacl` via `aclexplode`, **not** `information_schema.role_column_grants`, which echoes table-level grants per column and can never return zero on any database
  - `select ... from information_schema.role_table_grants where is_grantable='YES'`
- **R5 — One `DO` block is one transaction holding `AccessExclusiveLock` per relation.** All-or-nothing is the right trade (no window where a table is revoked but not re-granted), but the *first* table locked stays locked for the whole loop, against live traffic. Catalog-only work should be fast; "should be" is not a measurement. **Schedule a quiet window.**
- **R6 — State the owner precondition.** `role_table_grants` only shows grants where the current user is grantor, grantee, or a member; `REVOKE` only removes what the executing role has authority over. Run as anything less and the loop iterates a **short list**, changes less than it claims, and Section 3 reports clean *through the same blind spot*. First line of every run:

```sql
select current_user;   -- must print the owner role
```

## Sequencing — never two grant changes in one window

If a second sweep runs inside the first one's baseline-to-verify window, the
second's intended changes appear in the first's Section 3 as `LOST` rows. The
check stops being a check exactly when it matters most. On the source database,
running a `DELETE` sweep inside a `TRUNCATE` sweep's window would have reported
~135 deliberate revokes as losses.

**One sweep per window. Verify. Drop the baseline. Then the next.**

## Grant only the verbs the code actually calls

The sweeps exist because of the opposite mistake. A session correcting a pattern
of *missing* grants wrote the full CRUD verb list into two schema files — seven
unused `DELETE` grants across seven tables of one application, including an auth
credentials table, on an app with no delete path at all.

Before writing `delete` into any grant line, prove the code calls it:

```bash
grep -rn "method: *'DELETE'" --include=*.js .
```

On the source codebase that returned **exactly one hit**, admin-session gated.
Corrections were upserts, cancellation was a status field, and the GDPR design
*retained* the identifier with a suppression flag and redacted fields — an
`UPDATE`, not a `DELETE`.

Cleanup scripts are **not** a reason to grant `DELETE`: run them as the owner
role instead, and say so in the file header.

Why it matters beyond tidiness: where a table carries RLS `using (false)` and
the swept role **bypasses RLS entirely** — as Supabase's `service_role` does —
the grant is the only layer between a leaked key and irreversible row loss.

## Counting discipline

Grant audits generate numbers, and the numbers go wrong in predictable ways.

- **Exports get truncated.** A row-limited SQL client returned 100 rows and a "~107 tables" figure was written up as a live-DB fact. The real count was 227. Cross-check any export against something you already know exists.
- **Counting repo grant lines is not counting the database.** 83 explicit `grant ... delete` lines in version control versus 135 live rows — a 52-table gap that was entirely untracked schema.
- **Name what a number counts.** "227 tables" and "214 tables" can both be correct and describe different things (all tables vs. tables where the role holds `TRUNCATE`). Using them interchangeably makes a reconciliation impossible.
- **An arithmetic fit is not evidence.** `83 + 48 + 4 = 135` matched exactly and the hypothesis behind it was still wrong — all 48 came back clean. Flag a fit as unverified until a query confirms it.

## What a sweep does NOT cover — say so in the file

- Roles other than the one swept (`anon`, `authenticated`, application roles)
- Schemas other than the one swept
- **The default privileges that made it recur.** A new schema file copying `grant select, insert, update, delete` reintroduces the grant. The durable fix is `ALTER DEFAULT PRIVILEGES ... REVOKE ...` for the baseline *plus* stopping the source line. **Check first whether the target is actually in the default ACL** — on the source database `pg_default_acl` granted `TRUNCATE/REFERENCES/TRIGGER/MAINTAIN` and **not** `DELETE`, so widening it to include `delete` would have been a no-op that read like a fix.
- Fixing the live grant does not fix the schema file. `create table if not exists` files are safe to re-run, so a source line still saying `delete` puts it straight back. **Fix both, in separate commits.**

## Non-negotiables

1. Section 2 ships **commented out**. It is the only mutating statement; uncommenting is a deliberate act by a human.
2. Nothing is reported as run unless it was run. "SQL written, NOT RUN" is a complete and honest status.
3. `MAINTAIN` is PostgreSQL 18+. On an older server the word is a syntax error, not a harmless extra.
4. **A cleanup or migration is not done when it is run — it is done when its result is queried back.** A multi-statement paste into a browser SQL console can apply partway and still report success. End every file with a per-statement confirm query carrying its expected answer, and ask for those answers rather than accepting "it ran."
