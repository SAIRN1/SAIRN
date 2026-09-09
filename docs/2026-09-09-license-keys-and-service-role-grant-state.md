# `license_keys` and `service_role` grants: what is actually still open

**Written 2026-09-09 (Fourth).** The open-work index carries four Platform rows
on this subject. **Three of them describe work that has already been run — two
of those for two weeks.** This document establishes which is which from the
files and commits, so the rows can be corrected rather than re-worked.

Nothing here was taken from a row's own status cell. Every claim below names
the commit or file it came from.

---

## The short version

| Index row | Says | Actually |
|---|---|---|
| `license_keys` grants need their own dedicated review | **CLOSED 2026-09-05** | Correct — run end to end by Michael, `e5a98af6` |
| `anon` cannot read `license_keys`; three things still unmeasured | Open | **Two of the three are now measured.** Row is stale |
| `service_role` holds TRUNCATE/REFERENCES/TRIGGER/MAINTAIN beyond the append-only set | "Diagnosed, draft fix written, **not run**" | **RUN 2026-08-25, clean pass** (`923a31c`). Duplicated by resolved row |
| `service_role` granted DELETE on the slab tables with no code path | Open, "decide first" | **The decision was taken by execution 2026-08-25** — 134 tables lost DELETE. Needs one confirming read, then closure |

---

## 1. `license_keys` — genuinely closed, and closed well

`sql/license_keys_grant_review_2026-09-05.sql` was run as `postgres` in the
Supabase editor and recorded in `e5a98af6`. Result:

- `service_role` held **all seven** privileges — DELETE, INSERT, REFERENCES,
  SELECT, TRIGGER, TRUNCATE, UPDATE — and now holds **SELECT alone**, which is
  exactly what the code review predicted from the single GET at
  `api/_lib/license.js:71`.
- Section 5 verified `LOST` = exactly the six excess, `GAINED` = nothing.
- **`anon` and `authenticated` held nothing.**

The follow-through is the part worth preserving: both
`unused_delete_grant_revoke_2026-08-24.sql` and
`full_crud_truncate_sweep_2026-08-24.sql` open by telling a reader to expect
**one** row — `license_keys` — in their 3a verification. It no longer holds
DELETE or TRUNCATE, so re-running either now returns **zero**, and a future
session would reasonably read that as a broken check. The correction was
written into those two files, not only into the index. That is the right place
and it should stay there.

## 2. The `anon` row is stale — two of its three open items are answered

The row lists three things as unmeasured:

1. **`authenticated` was never probed** — no clone holds a signed-in JWT.
   → **Answered for this table.** The `postgres` run confirmed
   `authenticated` holds nothing on `license_keys`. Still unmeasured
   *platform-wide*, which is a different and much larger question.
2. **The non-SELECT verbs for `anon`** (TRUNCATE / REFERENCES / TRIGGER, known
   present on 158 tables).
   → **Still genuinely open, platform-wide.** PostgREST exposes no verb that
   can reach them, so they are inert over HTTP — ungranted work, not exposure.
3. **Whether `license_keys` is one of those 158.**
   → **Answered: it is not.** Same run, same commit.

Two independent methods agreed here — a live publishable-key probe from
outside with no credential, and a `postgres` read from inside. That is what
retires the exposure rather than leaving it "probably fine", and the row should
say so instead of listing it as open.

## 3. `service_role` TRUNCATE/REFERENCES/TRIGGER/MAINTAIN — this ran two weeks ago

The open row's status cell reads *"Diagnosed, draft fix written, not run"*.

`sql/full_crud_truncate_sweep_2026-08-24.sql` line 3 reads
**`SECTION 2 WAS RUN 2026-08-25. CLEAN PASS.`** and `923a31c` records the
verification in detail: 3a returned one row (`license_keys`, the deliberate
exclusion); **3b returned five rows, all `GAINED`, zero `LOST`** across 774
baseline privilege rows on 209 tables; 3c confirmed 774/209 unchanged, so the
diff ran against a real before-state. The five `GAINED` are the Phase 5 `rf_*`
tables created after Section 0 captured, and Section 2 is structurally
incapable of producing a `GAINED` — its GRANT list is filtered from each
table's own existing grants, so it can only restore a subset.

The source was fixed too: `append_only_grant_audit.sql:192-193`'s
`ALTER DEFAULT PRIVILEGES` revoke means the excess cannot come back.

**This is already recorded as resolved elsewhere in the same index.** The open
row and the resolved row are the same work. The open one should be struck.

## 4. The unused DELETE grants — the decision was made by running it

The open row says the slab tables (`sd_slabs`, `sd_blocks`, `sd_bundles`,
`sd_slab_history`) plus SAIRNgrounds/MSB carry a `service_role` DELETE with no
code path, and — correctly, at the time — that narrowing it is a real
functional-capability change needing a decision first, unlike stripping a
default nobody ever granted on purpose.

**That decision was taken the following day.** Section 2 of
`sql/unused_delete_grant_revoke_2026-08-24.sql` was run 2026-08-25. Its 3b
returned a single row, `LOST | DELETE | 134` — 134 tables lost all DELETE, with
**zero GAINED and zero LOST of any other privilege type**, which is what proves
no SELECT/INSERT/UPDATE was collaterally dropped. 3c: baseline 785/213, live
651/213; 785 − 134 = 651 exactly, table count unchanged, so no table was
emptied.

**Section 2 is list-free.** It discovers its targets from
`information_schema` and excludes exactly two things: `license_keys` and the
`sc_*` family (3d confirmed all 26 live `sc_*` tables kept DELETE, which is
correct — the platform's only `method: 'DELETE'` is the SAIRNcode
Compliance-Admin branch in `api/sd-data.js`). The slab tables are neither
exception, so they were in the 134.

One genuinely interesting finding survives from that file and should not be
lost when the row is closed: **`scp_employee_auth` was the only
`*_employee_auth` table on the platform holding DELETE**, and the cause was an
overcorrection rather than an oversight — `sql/scp_employee_auth_schema.sql:47`
literally writes the full CRUD verb list, while all eight siblings stop at
`select, insert, update`. The author was fixing a pattern of *missing* grants
and, being explicit, wrote more verbs than the app uses.

### The one thing to actually do

**Confirm it live before closing the row.** Everything in section 4 is
established from documents and commit messages, which is a strong trail and is
still not a measurement. One read-only query as `postgres` settles it:

```sql
select table_name, privilege_type
from information_schema.role_table_grants
where grantee = 'service_role'
  and privilege_type = 'DELETE'
  and table_schema = 'public'
order by table_name;
```

**Expected: only `sc_*` tables.** Anything else — in particular any `sd_slab*`,
`sd_block*`, `sd_bundle*` or `grd_*` row — means the 2026-08-25 run did not
cover what this document concludes it covered, and the row stays open with a
real finding attached.

## 5. Recommendation

1. **Strike the TRUNCATE row.** It duplicates a resolved row and the fix ran
   with a verified clean pass.
2. **Run the one query above.** On the expected result, strike the DELETE row
   too and move its `scp_employee_auth` finding into the resolved entry so the
   reasoning is not lost with the row.
3. **Rewrite the `anon` row** down to its single remaining item — the
   non-SELECT verbs for `anon`/`authenticated` on 158 tables platform-wide —
   and say plainly that they are inert over HTTP. As written, the row reads as
   three open exposures when it is one piece of tidy-up.
4. **Leave `license_keys` closed.** It is the one row here that is exactly what
   it says it is.

The pattern underneath all four is worth naming, because it is not about
grants: **three of these rows went stale the day the work was run, because the
run was recorded in a resolved row and in the SQL file, and nobody went back to
the open row that asked for it.** An index where completed work stays visible
as open is not merely untidy — it is what sends the next session to redo a
sweep that has already been run against a live database.
