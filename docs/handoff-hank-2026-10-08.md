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

### item 4 — STALE LOCKS AND WORKTREES — 2 locks removed, 1 refused on its own rule, 0 worktrees removed

Evidence gathered FIRST by a script that removes nothing
(`scratchpad/b3_item4_evidence.py`, output `i4ev.json` / `i4ev.log`), against a
**single process snapshot of 363 processes** so every item is judged against the
same moment rather than a moving target.

**A MISSING MEASUREMENT IS NOT-REMOVABLE, never removable-by-default.** If the
lock's pid cannot be read, "gone" is unprovable; if `git status` cannot run in a
worktree, "clean" is unprovable. Both outcomes are refusals.

#### LOCKS — 16 present. The three named, each with its evidence:

| lock | recorded pid | alive? | age | verdict |
|---|---|---|---|---|
| `b11wt2.lock` | 78192 | **gone** | **36.49h** | **REMOVED** |
| `bare_scratch.lock` | 56660 | **gone** | **189.86h** | **REMOVED** |
| `b12wt2.lock` | 78192 | gone | **21.57h** | **LEFT — fails the 24h test by 2.4h** |

Contents captured before deletion; both backups are at
`scratchpad/removed.<lock>.bak`:

```
b11wt2.lock       {"pid": 81228, "claude_pid": 78192, "started": "2026-10-06T16:23:12", "task": ""}
bare_scratch.lock {"pid": 38620, "claude_pid": 56660, "started": "2026-09-30T07:01:21", "task": ""}
```

**`b12wt2.lock` WAS NAMED IN THE DISPATCH AND IS STILL THERE.** Its process is
gone, so it is certainly dead — but the rule I was given is *"verify the owning
process is gone **and the age**"*, and at 21.57h it is under 24h. **It fails by
two and a half hours.** Removing it would mean applying the rule to two items and
making an exception for the third, which is exactly RULE E's defect. It will
qualify on its own a few hours from now; it is listed as open rather than quietly
taken.

**FOUR MORE LOCKS MEET THE SAME CRITERIA AND WERE NOT TOUCHED**, because they are
outside the three the dispatch named and their owners are not established:
`repo.lock` (pid 39448 gone, 48.40h), `sairn_idem_o66nnvth.lock` (58388 gone,
199.93h), `sairn_idem_q5p4bqkx.lock` (58388 gone, 200.14h),
`sairn_idem_rhbjx2yx.lock` (61668 gone, 207.88h). Listed for chat. Six live
locks (cc, cody, fourth, hank, hover, hover2 and two of mine) have **alive**
pids and are correctly untouched.

#### WORKTREES — 13 registered. **ZERO are removable, and that is the finding.**

| worktree | uncommitted | live procs | newest file | verdict |
|---|---:|---:|---|---|
| `gate12-48848-8` | **2563** | 0 | 295.5h | LEFT — uncommitted |
| `defreg-probe-13672` | **2221** | 0 | 511.8h | LEFT — uncommitted |
| `r5-served-4288` | **1975** | 0 | 563.4h | LEFT — uncommitted |
| `check4-probe-30700` | **1664** | 0 | 621.5h | LEFT — uncommitted |
| `sairn-abl-vzdwjmc0` | 5 | 0 | 17.7h | LEFT — uncommitted |
| `r5-cover-85152` | 2 | 0 | 16.1h | LEFT — uncommitted |
| `condcov-37872` | 1 | 0 | 12.6h | LEFT — uncommitted |
| `condcov-83660` | 1 | 0 | 19.3h | LEFT — uncommitted |
| `defreg-probe-84136` | 1 | 0 | 9.9h | LEFT — uncommitted |
| `sairn-abl-ffstikqt` | 1 | 0 | 15.1h | LEFT — uncommitted |
| `condcov-75140` | 0 | 0 | 17.3h | LEFT — quiet only 17.3h |
| `sairn-sab-b1u8mfer` | 0 | 0 | 9.7h | LEFT — quiet only 9.7h |
| `gate12-29772-4` | 0 | 0 | 9.4h | LEFT — quiet only 9.4h |

**THE RULE AS WRITTEN CANNOT REACH THE WORST OFFENDERS, AND THAT IS WORTH MORE
THAN THE CLEANUP WOULD HAVE BEEN.** The four worst — 1,664 to 2,563 uncommitted
paths each, untouched for **295 to 621 hours (12 to 26 days)** — are the most
obviously abandoned and the ONLY ones the rule forbids removing, because
**abandoned probe fixtures are indistinguishable from uncommitted work.** A
worktree with 2,563 dirty paths and no file touched in twelve days is almost
certainly a probe that planted a fixture and died; "almost certainly" is not the
standard the item set, and I did not lower it.

Every one of those 13 is also a live door for the shared-`.git/config` write that
corrupted this clone in batch 18 (section 6a there, RULE G below). **The leak is
not fixed by pruning registrations** — it is fixed per probe, by building the
sandbox as a **clone** rather than a worktree, which `check8_probe.py` already
does.

**NEXT STEP for chat:** either (a) give removal a second criterion that can
distinguish probe litter from work — e.g. every dirty path matches a known
fixture pattern, or the newest file is older than N days with no branch — or
(b) decide these four by hand. I have not done either; both are judgement calls
about other sessions' artefacts.

### item 5 — A MISSING SECRET NO LONGER OVERWRITES A GOOD RECORD — root cause fixed, 14/14 arms

**THE ROOT CAUSE WAS A SOUND RULE APPLIED TO THE WRONG STATE.** Both tools held
*"say so rather than keeping a stale OK"* — which is **right** when the tool
**asked** and could not get an answer (a 401, a timeout, an unparseable body;
those are facts about the subject) and **wrong** when it could not ask at all.
**A missing environment variable is a fact about the clone, not about the cron
jobs or the audit logs** — and five of the six clones on this box do not carry
`CRON_SECRET`, so every sweep that drove every tool bare erased the record again.

**THE FIX IS A FOURTH EXIT CODE, not a condition bolted onto the third.**
`EXIT_NO_SECRET = 3` in both tools; the missing-secret path now **writes nothing**
and returns 3. **Every other could-not-tell path is unchanged** and still records
COULD NOT TELL, because those ran — the fix is scoped to the state that justified
it (RULE E).

**MEASURED on the real documents, md5 before and after:**

```
docs/CRON-LIVENESS-STATUS.md      14f7f60abf4552fb0a7cdea3f89bf1ab  ->  unchanged
docs/AUDIT-CHECKPOINT-STATUS.md   dad31b8ebd43b1d51e6ef841902c0e0e  ->  unchanged
tools/cron_liveness_check.py      EXIT 3
tools/audit_checkpoint_status.py  EXIT 3
```

Both now print **`NOTHING WAS WRITTEN. <doc> is UNCHANGED and still holds
whatever the last run that COULD ask recorded.`**

**`tests/run_status_doc_secret_probe.py` — EXIT 0, 14 passed / 0 failed.**
Four arms per tool plus three sabotage arms per tool:

| arm | what it pins |
|---|---|
| **A** | exits **3, not 2** — exit 2 belongs to the paths that DID ask |
| **B** | the status document is **byte-identical** afterwards. *The defect was never a wrong exit code; it was a destroyed record* |
| **C** | the output SAYS nothing was written, so a reader is not left guessing |
| **D** | the planted sentinel survives — proving B compared a real file, not two absences |
| **S1** | **SABOTAGE**: the old behaviour restored exits 2, so **arm A would have failed on it** |
| **S2** | SABOTAGE overwrites the planted record, so **arm B would have failed on it** |
| **S3** | and the sentinel is **GONE** — the destroyed record stated as a fact, not as a hash difference |

**THE SABOTAGE IS WHAT MAKES THE ARMS EVIDENCE.** It rewrites the
missing-secret path back to `write_status(...)` + exit 2 **in a copy**, and the
probe asserts the copy both exits 2 and destroys the sentinel. *An arm that
cannot be made to fail has not been tested.*

**DRIVEN IN A SYNTHETIC SANDBOX, NOT A WORKTREE.** Each subject is copied into a
bare directory holding `tools/<subject>.py`, `tools/sairn_http.py` and a `docs/`
with a planted good record; the subjects derive their root from `__file__`, so
the sandbox is a complete world and nothing shared is reachable. **Not a linked
worktree on purpose** — batch 18 found a worktree shares `.git/config` with its
clone, which is RULE G below. Confirmed: the real documents are unchanged by the
probe itself.

**WHAT IT DOES NOT COVER, printed by the probe on every run:** the other
could-not-tell paths still write COULD NOT TELL **deliberately**, and a run WITH
a real secret is not driven — no credential was manufactured, so the happy path
is untested by this file.

**ONE CONSEQUENCE FOR ITEM 6, noted here so it is not read as a regression:**
both tools are in `tools/bare_run_writers.py`, the declared-intended-writers
allowlist. They are still correctly listed — with a secret set they do write —
but a **bare** run in a clone without the secret now writes nothing, so the
widened bare-run sweep will see them as non-writers.
