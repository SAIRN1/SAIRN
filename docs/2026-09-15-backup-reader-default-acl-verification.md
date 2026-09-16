# `backup_reader_role.sql` verify 2c and 2d — paste-ready, and NEVER RUN

**2026-09-15 (Fourth).** These two queries were written on 2026-09-15 and have
**never been executed against the deployed database.** Nothing in this
repository can execute them: there is no route from a clone to the Supabase
project. Until somebody runs them and reads the output, the question they were
written to answer is **COULD NOT RUN**, which is a third state and is not a pass.

Same shape as the isolation-level footers in
`docs/2026-09-15-advisory-lock-isolation-sweep.md`: the query, what a correct
answer looks like, and what each wrong answer means.

---

## The question

`sql/backup_reader_role.sql` grants `sairn_backup_reader` SELECT on everything
in `public`, then sets a **default ACL** so tables created *from now on* are
covered automatically. A default ACL is per **grantor role**: it only applies to
objects created by the role it was set `FOR`.

**So the grant is complete only if a default ACL exists for every role that
creates tables here.** If Supabase's dashboard or migration runner creates
tables as `supabase_admin` while the default ACL was set only `FOR ROLE
postgres`, every table added through the dashboard from today on is **silently
absent from the backup** — and the backup keeps succeeding.

2c asks *who creates tables on this deployment*. 2d asks *is every one of them
covered*. 2b (already in the file) only asks whether the grants that were made
took effect, which a hand-written list passes while still being incomplete.

---

## Verify 2c — who creates tables on this deployment

```sql
select tableowner                       as objects_created_by,
       count(*)                         as tables_owned,
       min(tablename)                   as example_table
  from pg_tables
 where schemaname = 'public'
 group by tableowner
 order by tables_owned desc;
```

**How to read it**

| result | meaning |
|---|---|
| only `postgres` appears | the dashboard creates as `postgres` on this project; the `supabase_admin` clause is harmless insurance |
| `supabase_admin` appears | **confirmed** — the `FOR ROLE` clause is load-bearing, not defensive |
| a **third** role appears | the original hardcoded pair was incomplete. The derived loop in the file now covers it, and **2d is what proves it did** |
| **zero rows** | `public` has no base tables, which on this project means you are connected to the wrong database — not that there is nothing to cover |

**One caveat, stated because it changes what this query proves.**
`pg_tables.tableowner` is the **current owner**, not the creator. They are the
same unless an `ALTER TABLE … OWNER TO` has been run. If ownership was ever
reassigned in bulk, 2c answers *who owns* and the question asked was *who
creates* — and the honest reading is then "this is the best available proxy",
not "confirmed". 2d is unaffected: it is about coverage of current owners, which
is what the default ACL keys on.

---

## Verify 2d — every owner is covered by a default ACL

```sql
with owners as (
  select distinct tableowner as rolname
    from pg_tables where schemaname = 'public'
), covered as (
  select distinct pg_get_userbyid(d.defaclrole) as rolname
    from pg_default_acl d
    join pg_namespace n on n.oid = d.defaclnamespace
   where n.nspname = 'public'
     and array_to_string(d.defaclacl, ',') like '%sairn_backup_reader%'
)
select (select count(*) from owners)                          as distinct_owners,
       (select count(*) from owners
         where rolname not in (select rolname from covered))  as uncovered,
       (select string_agg(rolname, ', ' order by rolname)
          from owners
         where rolname not in (select rolname from covered))  as uncovered_names;
```

**Expected: `uncovered = 0` and `uncovered_names` null.**

| result | meaning |
|---|---|
| `uncovered = 0` | every role that owns a table in `public` has a default ACL granting `sairn_backup_reader`. New tables from any of them are covered automatically |
| `uncovered > 0` | **the gap is live.** `uncovered_names` lists the roles. Every table those roles create from now on is absent from the backup, and the backup will not report it |
| `distinct_owners = 0` | same wrong-database reading as 2c's zero-row case |

**If `uncovered > 0`, the fix is in the file already** — re-run
`sql/backup_reader_role.sql`, whose loop derives the role list from `pg_tables`
rather than hardcoding it, then re-run 2d. Both are idempotent.

---

## What this document does NOT establish

- **That either query has been run.** They have not. This is the text and the
  reading key, nothing more.
- **That the backup is complete.** 2d answers coverage of *future* tables. 2a
  (in the file) answers *current* tables, and it is a separate query with its
  own expected result.
- **Anything about restore.** A grant that lets the reader SELECT is not
  evidence the dump restores; `nightly-backup.yml` restores what it took and
  runs a coherence check, and that is the half that proves it is a backup.
