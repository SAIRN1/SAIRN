# SAIRN handoff: cc, batch b52, 2026-10-22

**All four items are closed.**

- **CLAUDE.md:** the line was never in it. It is added now, at `c300b33e`,
  and it points at the tuple rather than copying it.
- **rt_stops SQL:** all three files are landed in git. Both of the files that
  change the schema are applied on the live database (measured). The probe
  file changes nothing, so whether it was run cannot be seen.
- **Push:** no `--force`, no override. The clone reads 0 0 against origin.

| | |
|---|---|
| Landed | `c300b33e` (CLAUDE.md), then these deliverables |
| Context | see the digest's CONTEXT line (measured) |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\87a27b9f-55e9-45e8-b017-01ed1febac1a.jsonl` |

## 1. SEN-AUDIT-2026 / KNOWN_AUDIT_KEYS line in CLAUDE.md: ADDED (`c300b33e`)

- **Before this batch, the line was never in any CLAUDE.md.** `grep` over
  the project `CLAUDE.md` and `~/.claude/CLAUDE.md` found nothing.
- The key itself has been in `KNOWN_AUDIT_KEYS` since hank b35 (`0ff033a3`).
  That tuple is at `tools/audit_licence.py:106`. cc b40 reported the same
  thing.
- **I added the line to the project `CLAUDE.md`, under Project context.**
  - It names the key, the tuple, the file and the commit that added it.
  - It **points at the tuple rather than copying it**, as the primer already
    does for the script-block count. A copied list is the second copy that
    goes stale.
- **I corrected my first draft before committing.** It said an unlisted key
  is "refused". I read `audit_licence.py:132-141`, which shows that an
  audit-shaped key not in the tuple **proceeds with a NOTE**, so the line now
  says that.
- **Which file I read "your own CLAUDE.md" as:** the project CLAUDE.md in
  this clone. The path manifest leaves CLAUDE.md for cc's decision. It is
  tracked, so every clone sees the line. If you meant the private
  `~/.claude/CLAUDE.md` instead, say so and I will move the line.

## 2. The three b28 rt_stops SQL files: exact state

**In git, all three are LANDED on origin.**
- Two of them were last changed at `cb0d94f5` (b28, 2026-10-20 06:01): "one
  purpose per file".
- The FK file has an earlier version at `d19d99e9` (b27).

**On the live database, measured this batch.** This was a read-only
`pg_constraint` query on sairn-platform (`ejrlrrkvhtllxbbypdjb`), the
project the repo's own reviews name as live.

| File | What it does | Live state | Verdict |
|---|---|---|---|
| `sql/rt_stops_license_hash_composite_fk.sql` | adds `rtroutes_id_license_uniq` UNIQUE (id, license_hash) on rt_routes, and FK `rtstops_license_matches_route` (route_id, license_hash) → rt_routes(id, license_hash) ON DELETE CASCADE | **both PRESENT**; FK `convalidated = true`; 0 mismatched rows (the tables are currently empty: 0 routes, 0 stops) | **RUN** |
| `sql/rt_routes_drop_saved_sane.sql` | drops `rtroutes_saved_sane` | **ABSENT**; its replacement `rtroutes_saving_has_a_basis` is PRESENT | **RUN** |
| `sql/rt_stops_fk_probe.sql` | a control that raises on purpose; it changes nothing | nothing to observe | **NOT DETERMINABLE.** With the FK present, it would pass |

- The old single-column `rt_stops_route_id_fkey` is still present. The FK
  file says not to drop it, so that is as intended.

## 3. Methodology (item 3): where "ran" is actually recorded

- **The migration history is empty.** `list_migrations` on sairn-platform
  returns `[]`. These files are pasted into the SQL editor by Michael, so no
  migration row exists, and the history cannot say whether anything ran.
- **The commit log records landing, not running.** `cb0d94f5` and
  `d19d99e9` prove the files are on origin. They say nothing about the
  database.
- **So the evidence for "ran" is the catalog itself**, read this batch:
  `pg_constraint`, `convalidated` and the row counts. It is not cc b40's note
  of 2026-10-21, which said the same thing but was a day old.
- The probe file is the one case where nothing records whether it ran. Its
  only effect is a raised error in the SQL editor. That is stated as
  not determinable rather than assumed either way.
- **The rule this applies:** a "ran" claim about SQL names the catalog read
  that shows it, because on this platform neither git nor the migration
  table records execution.

## 4. OPEN

| Item | Owner | Next step |
|---|---|---|
| Whether "your own CLAUDE.md" meant the private file | Michael | Only if so: say it, and cc moves the line. |
| `rt_stops_fk_probe.sql` | Michael | Optional. Run it once, after a route row exists, to see the control raise. Nothing depends on it. |
| Carried | fourth | register problems 1-7, then the b49 gaps (cc b51). |
| Carried | hank | `38b2b506` (cc b50). |
| Carried | cody | `d6b37bb1` (cc b50). |
