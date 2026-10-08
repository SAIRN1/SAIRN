# Hank handoff — 2026-10-08, batch 19 (b3)

**Per-item checkpoint.** A row is appended after EACH item, before the next
begins. Every row is state at the moment it was written, not a plan.

Previous handoff: `docs/handoff-hank-2026-10-07d.md` (batch 18, pushed
`5c9dc265`).

---

## PER-ITEM LOG

### item 1 — CLAIM AND RESUME CHECK — DONE

**`5c9dc265` IS AN ANCESTOR OF `origin/main`** — verified with
`git merge-base --is-ancestor`, not read off the previous handoff. Batch 18 is
fully landed; nothing from it is redone.

At pickup: HEAD was 7 behind. Rebased to **`0faec47e`, ahead 0 / behind 0**,
tree clean, `core.bare` = `false`.

**MY BATCH-18 CLAIM WAS ALREADY RELEASED** (I released it at the close of b2);
re-claimed `platform` for batch 19 and the claim is pushed and verified on
`origin/main`.

**LIVE FILES READ, NOT INFERRED — and it changes two items before they start.**
Three live claims (cody ×2 at 0.6h/0.8h, fourth at 0.9h). Each of my targets
checked against their declared FILES:

| target | holder |
|---|---|
| `docs/tier-a-reviews.json` | **DECLARED BY NOBODY** |
| `tools/bare_run_write_check.py` | DECLARED BY NOBODY |
| `tests/run_bare_run_write_probe.py` | **cody** (0.6h, 0.8h) |
| `docs/defect-density-register.json` | **cody** (0.6h, 0.8h) |
| `docs/METHODOLOGY.md` | **fourth** (0.9h) |
| `docs/known-red-suites.json` | **fourth** (0.9h) |
| `tools/cron_liveness_check.py`, `tools/audit_checkpoint_status.py` | DECLARED BY NOBODY |
| `docs/CRON-LIVENESS-STATUS.md`, `docs/AUDIT-CHECKPOINT-STATUS.md` | DECLARED BY NOBODY |
| `tools/dead_rule_sweep.py`, `tools/bare_run_writers.py` | DECLARED BY NOBODY |
| `tests/push_gate/check4_probe.py` | DECLARED BY NOBODY |

**TWO CONSEQUENCES, decided here rather than discovered mid-item:**

- **ITEM 7 IS UNBLOCKED.** `docs/tier-a-reviews.json` was cc's through batch 18
  and is now held by nobody. The 15 obligations are dischargeable, subject to
  the per-obligation rule in the item.
- **ITEM 6 IS NARROWED, NOT REWORDED.** `tools/bare_run_write_check.py` is free
  so the widened scope goes in; **`tests/run_bare_run_write_probe.py` is CODY'S
  and is NOT edited** — its arms go in a file of mine.

`docs/defect-density-register.json` is cody's: appended **only** through
`defect_register.py --add`, never edited. `docs/METHODOLOGY.md` is fourth's, so
Rule G (item 9) goes in my own routed file, which is where the item puts it
anyway.

### item 2 — STEP 13 REWRITTEN AS 13-ALT — DONE. Document only; no code touched.

`docs/2026-10-07-hank-migration-sql-for-michael.md` STEP 13 is replaced — not
amended — with a new **`sairnvet_audit_log`** in exactly the form of STEP 1-12.
**`sv_audit_log` is left alone and no statement in STEP 13 touches it.**

**THREE PRE-FLIGHT QUERIES, each with the failure it would catch:**

- **13-PRE (a)** — does the new name already exist? `create table if not
  exists` is **silent** on a name that is already there, which would leave you
  believing you made a table you did not. Expect exactly one row,
  `sv_audit_log`.
- **13-PRE (b)** — **record the dosing trail's size, columns and grants BEFORE
  touching anything**, so 13-V (d) can prove nothing changed. Expect
  `service_role` with SELECT, INSERT **and UPDATE** — UPDATE is *correct* on
  that table and must still be there afterwards.
- **13-PRE (c)** — `pgcrypto`, because the DDL defaults a uuid primary key.
  Almost certainly present; asked rather than assumed, because the failure mode
  is the DDL erroring half way through.

**FOUR VERIFY QUERIES**: the table reads (0 rows, no error); **the grants are
exactly SELECT + INSERT** for `service_role` — the immutability control and the
thing most likely to be wrong, since `service_role` bypasses RLS; the CHECK
constraint really exists and lists five values (a table created before the
constraint would accept any event name and nothing downstream would notice); and
**13-V (d), the one that matters most — the dosing trail is byte-for-byte the
same, grants included.**

**THE EVENT VOCABULARY USES THE STRICT `in (...)` FORM**, which is only possible
because the table is new and empty. The rejected option could not: `sv_audit_log`
has existing rows with no `event_type`, so it needed
`event_type is null or event_type in (...)` — a weaker constraint arrived at by
accident of history, not by choice.

**TWO STALE STATEMENTS CORRECTED IN THE SAME FILE, because a document that says
two things is the defect this sequence keeps finding.** STEP 0d and the top
"WHAT CHANGED" table both still read *"DECIDED: reuse `sv_audit_log` … one line
of JavaScript"*. Both are now marked **SUPERSEDED** and STEP 0d opens with **DO
NOT RUN THE JAVASCRIPT BELOW**, pointing at STEP 13. The original text is kept,
struck through rather than deleted: *a superseded step that is deleted is one
somebody re-derives from scratch; a superseded step that is silently corrected
is one nobody knows was ever wrong.*

```
python tools/md_table_check.py docs/2026-10-07-hank-migration-sql-for-michael.md
  EXIT 0   OK (13/13 rows checked), 0 malformed, 0 uncheckable
```

**THE CODE HALF IS WRITTEN DOWN AND NOT DONE.** `api/_lib/audit.js` and
`api/sv-auth.js` are untouched and stay that way until Michael confirms STEP 13
has run — writing them first makes every SAIRNvet audit write hit a table that
does not exist, PostgREST answers 404, `writeAuditLog` returns false
non-fatally, and **the row is absent with nothing on screen to say so.** The
five ordered steps are in the document, ending with: re-run
`tests/run_audit_event_type_probe.py` and **watch arm H1** — it asserts every
allowlisted table has the four columns `writeAuditLog` posts, so if it goes red
the DDL did not run the way step 1 assumes.

### item 3 — THE 101 SUITE FAILURES SPLIT BY OWNER — committed

`docs/2026-10-08-hank-suite-failure-owners.md`.
`md_table_check` **EXIT 0, 120/120 rows, 0 malformed, 0 uncheckable.**

| verdict | count |
|---|---:|
| **REAL** | **89** |
| CASCADE (listed separately, NOT counted as failures) | 8 |
| TIMEOUT at 240 s alone (a third state, neither) | 4 |

**THE 89 REAL, BY OWNER:**

| owner | count |
|---|---:|
| **UNOWNED** | **62** |
| cody | 11 |
| fourth | 8 |
| cc | 5 |
| hank | 2 |
| cc+fourth+hank | 1 |

**OWNER IS DERIVED FROM TWO SOURCES AND EVERY ROW SAYS WHICH.** `map` = a
non-null entry in `docs/tool-owner-map.json`. `claim` = a session **declared the
file in a claim's `FILES:` list**, read out of every record in
`.claude/claims/*.json` — the only durable record of who has worked on a file.
**`UNOWNED` means neither source names anybody**, not that nobody wrote it. 502
of the owner map's 680 ownerless entries are under `tests/`, so 62 of 89 is the
expected shape, not a surprise — and **a file with no owner cannot be routed to
anybody**, which is the same problem `tools/va_rule_currency.py` had in b1.

**ONLY 2 OF THE 89 ARE MINE.**

**CASCADE AND TIMEOUT ARE IN THEIR OWN SECTIONS WITH THEIR OWN HEADINGS**, each
carrying what the suite said beside what the file says alone. The one to read
twice is still `tests/phi_cache_scoped_to_user.js`: **72 passed / 0 failed
alone**, while fourth's batch-16 item 4 took it on as *"basis NONE, no owner,
blocks three register rows"*.

**THE DOCUMENT SAYS WHAT IT DOES NOT CLAIM**, in its own closing section: it
does not claim the 89 are NEW — `known_red_check.py --from-run` on the same log
reports 101 red against a registry of 75, i.e. **30 red and not recorded**, and
that register is **fourth's** and is not touched — and it does not diagnose any
of them. The "first failing assertion" column is quoted, not interpreted.

**A GENERATOR DEFECT WORTH ONE LINE, because the damage was wildly out of
proportion to the cause.** The first build produced *"3 malformed, 62
unreadable"*. The cause was a bare **carriage return** inside three traceback
cells, captured from a Windows subprocess. **One broken row unparses every row
after it**, so three bad cells cost 62 rows. Escaping the pipe was never the
fix — the invisible character was. The generator now maps every control
character to a space and every pipe to a slash, and `md_table_check` is the
arbiter that has to be satisfied rather than my own reading of the markdown.
