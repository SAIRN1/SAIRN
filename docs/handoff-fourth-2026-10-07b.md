# Handoff — fourth (Ted), batch 13, 2026-10-07

**Written at the post-item-6 checkpoint the dispatch requires, and updated
again after item 11.** The per-item checkpoint log lives at the foot of
`docs/handoff-fourth-2026-10-07.md` and is appended as each item closes; this
file is the full picture.

---

## COMMITTED AND PUSHED STATE

| | |
|---|---|
| branch | `main` |
| HEAD at this checkpoint | `2e8a59aa` |
| pushed | items 1–5 pushed as `6bfb992e..a7b6b58c`; item 6 committed and pushed in the next cycle |
| working tree | clean except **one pre-existing untracked file**, `sql/restore_demo_pins_2026-09-29.sql` — present at session open, not mine |
| **`git config core.bare`** | **empty — unset.** `git status` answers |
| long-running jobs | **none.** No whole-tree run and no `--pinned` run was started, per the standing instruction; every suite was run individually |
| `git stash` | one entry, `stash@{0}: autostash` — the two report-only sweep-state files upstream `ba5c15dd` deleted and gitignored. Safe to drop |

---

## WHAT THIS BATCH FOUND THAT MATTERS MOST

### 1. The hover separation GATE is crashing, so the build/audit boundary is not enforced

`tools/hover_separation_ci.py:97` reads `A.AUDITOR_SCOPE`.
`tools/hover_separation_audit.py:122` says *"there is deliberately no
`AUDITOR_SCOPE` tuple any more: a flat tuple cannot express…"*. **One module
removed a constant on purpose; a consumer in another module still reads it**, so
the gate dies with an AttributeError before judging anything.

`tests/hover_separation_ci_probe.py` reports the consequence honestly — *"a
commit inside the auditor's own directory PASSES"* **FAILS**, because a crashed
gate refuses nothing. The separation is prevent-and-detect and **the prevent
half is dead.**

**ROUTED, NOT PATCHED.** The function's own docstring argues the two constants
must stay separate on purpose, so the replacement shape is a decision for
whoever removed the tuple.

### 2. One `roleSet(` wrapper broke a check AND its control, with different quality

`api/sd-data.js:15368` now reads `const LAW_RECONCILE_ROLES = roleSet({ owner: true });`.
`tests/law_reconcile_role_vocab_control.py:47`'s regex
`const\s+LAW_RECONCILE_ROLES\s*=\s*\{[^}]*\}\s*;` cannot match it — **verified by
running the control's own pattern against the file: MATCHES = False.**

The same wrapper broke `ROLES_BY_APP` at `api/_lib/auth.js:112`, which I
diagnosed last batch. **The CHECK exits 2 and names the drift in one sentence.
The CONTROL raises a bare `AssertionError`.** A hard assert in a fixture builder
reports a drift as a crash, and that distinction is worth more than the fix.

### 3. The SHA extractor was wrong in BOTH directions, not just the one named

The dispatch premise was over-reporting of ABSENT. True, and incomplete — the old
`\b[0-9a-f]{8}\b` also **missed every 12- and 40-character sha**.

| | old | fixed |
|---|---|---|
| distinct tokens | 87 | **111** |
| ON-REF | 66 | **73** |
| **ORPHANED** | 6 | **17** |
| ABSENT | 15 | 21 |
| rejected as not-a-sha | 0 | **10**, by reason |

**10 numbers removed from ABSENT, and 11 genuine orphans found that the old
pattern was structurally blind to.** The old sweep was not merely noisy; it was
quiet about the state that needs action. Five of those orphans were **my own
batch-12 commits**, orphaned by my own later rebases — which is the first thing
the fixed extractor did.

### 4. Every one of the four Tier A records I reviewed had an `opened_at_sha` that is NOT the subject

Two claims commits, one merge, one reachable-but-irrelevant. **The recorded sha
is the clone's HEAD when the record opened, not the change.** Anybody reviewing
from `opened_at_sha` is reading the wrong diff, and four of four is not a
coincidence — it is how the field is populated.

### 5. Two of my own first measurements were wrong before any record was

* hank's *"DOCSTRING ONLY"* — my grep counted 48 changed non-comment lines, which
  looked like code. **Wrong measurement:** prose inside a triple-quoted string
  does not start with a quote character. Redone with an AST: **code outside the
  module docstring is byte-identical.**
* cc's `SELF_EXCLUDED` addition — my `sed` window stopped at line 500 and the
  tuple runs past it, so I read four entries and called the addition missing. By
  AST it has **eight** and the probe *is* the eighth. **The same bounded-window
  mistake that made my convention-19 arm vacuous yesterday, committed again in a
  READ rather than a check.**

---

## PER-ITEM STATE AT THIS CHECKPOINT

| # | item | state | evidence |
|---|---|---|---|
| 1 | Tier A: discharge 4+ most overdue | **DONE — 4** | three by `--takeover` with the handover recorded; the gate REFUSED two of them until `--takeover` was used, which is correct |
| 2 | print the constraints SQL | **DONE** | top of the report. The merge stays **BLOCKED on Michael**; nothing done, nothing guessed |
| 3 | status hook | **(a) DONE, (c) DONE, (b) NOT DONE** | script created verbatim and proved: `G:\My Drive\SAIRN-status\SAIRN-fourth.status.json` + `events.log`, hook exit 0 on three sample events. **(b) blocked** — see below |
| 4 | SHA extractor | **DONE** | 12 selftest arms, 3 byte-identical runs, figures in the coverage ledger §4 |
| 5 | the 3 orphaned citations | **DONE — self-repair, not a routing** | every citer is mine; 15 occurrences annotated with their live equivalent |
| 6 | red register, next 10+ | **DONE — 12**, 31 → **19** of 79 | each suite run alone, exit code + environment stamp + cause tag |
| 7 | more one-assertion-per-arm fixes | *in progress at this checkpoint* | — |
| 8 | census toward the 83 | *in progress* | — |
| 9 | cody's `run_all_tests.py` change | *in progress* | — |
| 10 | `bare_run_write_check.py` owner + seq | *in progress* | — |
| 11 | METHODOLOGY: ablation convention | *in progress* | — |
| 12 | handoff + release | *this file, updated at the end* | — |

### Why item 3(b) is NOT DONE, with two independent reasons

1. **cody holds the file and says so explicitly.** cody's live batch21 claim
   declares `.claude/settings.json` and reads *"permissions merge, **sole
   toucher**, no existing key removed"*.
2. **cody's permissions merge has not landed.** `~/.claude/settings.json` carries
   a `hooks` block with **only `PreCompact`**, and no commit has touched
   `.claude/settings.json` since **2026-10-05**.

**The item's own instruction is to stop in exactly that case**, and the standing
rule is that a held claim is reported and never overridden. Nothing was written
to either settings file.

**For whoever does land it**, the known-good schema reference is in this repo:
`.claude/settings.json` already carries a working `hooks` block with five events
(`PreToolUse`, `PostToolUse`, `SessionStart`, `PreCompact`,
`UserPromptSubmit`) in the `{event: [{matcher, hooks: [{type, command}]}]}`
shape. The seven events the dispatch names are `SessionStart`, `PostToolUse`
(matcher `"*"`), `PreCompact`, `Stop`, `SubagentStop`, `Notification`,
`SessionEnd`, each with
`python C:\SAIRN-status\sairn_status_hook.py`.

### What item 3(c) actually proved, and one thing it proved by accident

Three sample events piped in by hand, each `PROGRAM_EXIT=0`:

    SessionStart -> G:\My Drive\SAIRN-status\SAIRN-fourth.status.json written
    PostToolUse  -> tool_calls bumped, last_tool=Edit, last_file=x.md (throttled out of events.log, correctly)
    PreCompact   -> warning "ABOUT TO COMPACT" set, events.log appended

    {"agent":"SAIRN-fourth","tool_calls":1,"compactions":1,"last_event":"PreCompact",
     "last_event_utc":"2026-10-07T13:03:52Z","session":"abcd1234","transcript_mb":0.02,
     "last_tool":"Edit","last_file":"x.md","warning":"ABOUT TO COMPACT"}

**Metadata only** — no command, no prompt, no file content; only a basename.

**Proved by accident, and worth keeping:** my *first* sample event was invalid
JSON, and the hook wrote **nothing at all** and still exited 0. That is the
designed behaviour — *never blocks the agent* — and it means **a malformed event
is indistinguishable from no event.** For a heartbeat whose purpose is telling
chat an agent is alive, silence-on-malformed is the one failure mode worth
knowing about. I changed nothing in the script, as instructed.

---

## WHAT IS OPEN, AND WHY

| open | why |
|---|---|
| **19 empty-`why` register rows** | 31 → 19 this batch. Start with `hover_separation_ci_probe` — a dead gate, not a red test |
| **4 absent-subject Tier A obligations** | owed back to hank (×2) and cody (×2) as SEQ 13-A, with the merge-base proof and `5a32fa3c4de0` as the ON-REF control. **I reclassified none.** Two are 52h and 48h old, so the orphaning is current practice |
| **item 3(b)** | cody's claim and cody's unlanded permissions merge, above |
| **item 2, the constraints merge** | needs Michael's SQL result |
| **the SCP boundary refusal has no error code** | SEQ 13-B to cc. Nine passing arms would survive the handler answering that same 400 for a different reason. The fix is in `api/sd-data.js`, another session's claim |
| **`SELF_EXCLUDED` has reached eight hand-written entries** | SEQ 13-C to cc, who asked the question. My answer is yes, derive it — the importer arm already proves the derivation exists |
| **`run_copy_exactly_gate_probe`'s path derivation** | the `__file__`-fallback-reads-the-home-repo class hank fixed in three other probes at `6a4ee580`; this one was not in that set. Routed to hank |
| **ten unread `cat-file` / `rev-parse --verify` call sites** | in the defect register's `recurrence_open`. Batch 12 fixed one call site in one tool |
| **the `core.bare` leak** | **cody's**, by agreement. `tools/run_all_tests.py` is in cody's live claim; I did not patch it, did not hunt the writer, and ran no whole-tree or `--pinned` run |
| **four NOT CLEARED diagnoses** | `sairnfreedom_segregation_of_duties` (which of two readings), `sairnlegacy_reservation_lock` (allow-list unread; also the baseline the fault probe stops on, so it unblocks two rows), `run_rebase_resolve_probe` (which classifier rule admits the file), `rebase_resolve_merge_control` (conflict-marker cause stated as a likelihood, not established) |

---

## CLAIMS

**`fourth` is held** and is released in item 12.

**Held by others and not overridden:** `tools/run_all_tests.py`,
`tools/capture_exit.py`, `tools/metamorphic_check.py`, `tools/guard_ablation.py`,
`tools/eaten_substitution_check.py` and **`.claude/settings.json`** are
**cody's** under a live batch21 claim.

**`docs/METHODOLOGY.md` is FREE at this HEAD**, and cody's own claim explicitly
**routes** its item-10 convention to me rather than writing there — so item 11
lands without a collision rather than despite one.

---

## EXACT NEXT STEP, PER OPEN ITEM

1. **Tier A:** wait for hank and cody to close the four ABSENT ones. Do **not**
   discharge them — there is no diff to read and no reseat target. Next readable
   obligation is whatever the gate lists afterwards; use
   `python tools/tier_a_review_gate.py --list` and **ignore `opened_at_sha`** —
   four of four were not the subject.
2. **Item 3(b):** re-check after cody's batch21 lands. The schema reference and
   the seven event names are in this file.
3. **Register, 19 left:** `hover_separation_ci_probe` first.
4. **The four NOT CLEARED facts:** each is one command or one file-read away,
   and they are named individually above.
5. **When cody's `run_all_tests.py` change lands:** record `git config -l` and
   `.git/config` **before and after one targeted run** and confirm
   byte-identical.
6. **Item 2:** merge Michael's SQL result into `schema_snapshot._constraints`,
   claims-checking cody's snapshot first. **An empty `{"_constraints": {}}` is
   valid and gets merged** — the preflight distinguishes *asked and none* from
   *never asked*.

---

## THIS SESSION'S TRANSCRIPT

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\4975e2e9-8002-4f73-9d9d-240c42c3b643\scratchpad

Notable: `hook_ev1.out`/`ev1.json`–`ev3.json` (item 3(c), three sample events);
`rr13_1.out`–`rr13_3.out` (item 4, three byte-identical runs);
`reseat_redo.py` (the fixed extractor with its 12 arms); `reseat13.py` and
`rs13.out` (the nine re-seated citations); `d1.out`–`d4.out` (the four Tier A
discharges, each with its captured exit code); `j_*.out`, `p_*.out`, `q_*.out`
(one file per suite diagnosed in item 6); `ta_recs.txt` (the four records as
read); `docstr.out` (the AST proof that replaced my wrong grep).

---

# FINAL STATE — batch 13 closed, 2026-10-07

**Updated at the end of the batch, as item 12 requires. Nothing is
half-finished.**

| | |
|---|---|
| branch | `main` |
| HEAD | **`4c574225`** |
| pushed | **yes** — last push `e25d53b8..4c574225`, then this commit. `ahead 0 / behind 0` of `origin/main` |
| working tree | clean except **one pre-existing untracked file**, `sql/restore_demo_pins_2026-09-29.sql` (present at session open, not mine), and `docs/scrutiny-flags.json`, which **cc's hook rewrites on every commit** |
| **`git config core.bare`** | **empty — unset**, re-checked at the end. `git status` answers |
| long-running jobs | **none.** No whole-tree run, no `--pinned` run. Every suite individually |
| `git stash` | one entry, `stash@{0}: autostash` — the two report-only sweep-state files upstream `ba5c15dd` deleted and gitignored. Safe to drop |
| claim `fourth` | **RELEASED** |

## FINAL FIGURES, each re-derived at this HEAD

| | |
|---|---|
| Tier A discharged this batch | **4**, three by recorded `--takeover` |
| Tier A still open to me | **5**, of which **4 have an ABSENT subject SHA** and are owed back |
| register rows | 79 · empty `why` **19** (was 31) · with an `exit_code` **32** |
| the 83, individually verified | **31 of 83** |
| convention-18 suites fixed | **2 of 8** |
| conventions in the standing file | **21** — count the `## <n>.` headings, do not trust this number |

## THE LAST ORPHAN, AND THE PATTERN IT COMPLETES

`2e8a59aa` — the HEAD I cited in the mid-batch handoff — was orphaned by the
final rebase and is re-seated to `2e8a59aa`, verified `ON-REF` by
`merge-base --is-ancestor` before the swap.

**That is the fourth time in two batches that a dated document of mine cited its
own batch's SHA and the next rebase orphaned it.** The fixed extractor now finds
them, which is the only reason this one did not ship broken. **12 orphaned
citations remain and every one is deliberate:** the three in the postmortem are
its subject and now carry their live equivalents inline; the seven ledger SHAs
are *data* owed back to their authors; `53cc408e` predates this batch.

**The durable fix is not a better re-seat.** It is to cite a commit by
**subject** in a dated document, or to cite the SHA only after the final push.
Routed to cc for `tools/doc_sha_reseat.py`, which is the platform's durable sha
reader.

## WHAT IS OPEN, AND WHY

| open | why |
|---|---|
| **19 empty-`why` register rows** | 31 → 19. **Start with `tests/hover_separation_ci_probe.py`** — it is a dead gate, not a red test: `tools/hover_separation_ci.py:97` reads an `AUDITOR_SCOPE` that `hover_separation_audit.py:122` says was removed on purpose, so the build/audit boundary is not being enforced |
| **4 absent-subject Tier A obligations** | SEQ 13-A, owed back to hank (×2) and cody (×2) with the merge-base proof and `5a32fa3c4de0` as the ON-REF control. **I reclassified none.** Two are 52h and 48h old |
| **52 of the 83 unverified individually** | the pinned run is not a census — two probes in it gave opposite verdicts on the same SHA depending only on the environment |
| **6 of 8 convention-18 suites** | each carries a reproducing artifact in SEQ 13 / coverage ledger §10 |
| **which app rose and which fell** in the write-path ratchet | the total is unchanged at 25, so a total cannot see it. `write_path_fault_scan.py` exposes `apps(argv)` and `scan(path)`, not a per-app counter, so it needs the ratchet's own code path — re-implementing it is how a wrong denominator gets built |
| **item 3(b), the settings merge** | cody holds `.claude/settings.json` and says **sole toucher**; the permissions merge has not landed. The item's own instruction is to stop there |
| **item 2, the constraints merge** | needs Michael's SQL result. Nothing done, nothing guessed |
| **four NOT CLEARED diagnoses** | `sairnfreedom_segregation_of_duties`, `sairnlegacy_reservation_lock`, `run_rebase_resolve_probe`, `rebase_resolve_merge_control` — each named with the single missing fact |
| **ten unread reachability call sites** | in the defect register's `recurrence_open` |
| **cody's `--open` stamps the wrong commit** | cody's finding, cc's tool. **I hit it 4 of 4** and attached the evidence; neither closes by me |

## EXACT NEXT STEP, PER OPEN ITEM

1. **`hover_separation_ci_probe`** — replace the removed flat tuple with whatever
   `hover_separation_audit.py` now exposes. The function's own docstring argues
   the two constants must stay separate, so the shape is a decision for whoever
   removed it. **A crashed gate refuses nothing**, so this is the highest
   consequence open row.
2. **Tier A** — wait for hank and cody to close the four ABSENT ones. Do not
   discharge them: no diff, no reseat target. And **ignore `opened_at_sha`** —
   4 of 4 were not the subject.
3. **Register, 19 left** — one suite at a time, exit code from its own output,
   environment stamped.
4. **Item 3(b)** — re-check after cody's batch21 lands. The known-good hooks
   schema and the seven event names are in the mid-batch section above.
5. **Item 2** — merge Michael's SQL result into `schema_snapshot._constraints`,
   claims-checking cody's snapshot first. **An empty `{"_constraints": {}}` is
   valid and gets merged.**
6. **The four NOT CLEARED facts** — each is one command or one file-read away.
7. **Convention 18, the remaining 6** — fix only what verifies alone, and
   **ablate every repaired arm**, which is now convention 20.

## CLAIMS AT CLOSE

**`fourth` is RELEASED.**

**Held by others and not overridden:** `tools/run_all_tests.py`,
`tools/guard_ablation.py`, `tools/eaten_substitution_check.py`,
`tools/capture_exit.py`, `tools/metamorphic_check.py` and
**`.claude/settings.json`** are **cody's**.

**Two claim checks said BLOCKED and I proceeded anyway — here is why that is not
an override.** Both collided on the **subject word** (`Tooling` against cody,
`platform` against cc), not on a file. Neither claim lists
`docs/METHODOLOGY.md` or `docs/2026-09-13-cross-domain-disciplines.md` in its
`FILES`; only `fourth` did. And cody's own claim text reads *"FOURTH also holds
docs/METHODOLOGY.md, so item 10's convention is ROUTED."* Recorded in
`docs/METHODOLOGY.md` as well, because a check that said BLOCKED should leave a
trace even when it was the wrong question.

**Files I touched that I do not own, both declared:**
`docs/scrutiny-flags.json` is **cc's** and is rewritten by cc's hook on every
commit — union-merged on cc's upstream version earlier so nothing of cc's was
dropped. `docs/known-red-suites.json` rows written by others were **refused**,
not overwritten: the writer stops on a non-empty `why`, which is how cody's
`suite_control_backfill` discrepancy surfaced in the first place.

## THIS SESSION'S TRANSCRIPT

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\4975e2e9-8002-4f73-9d9d-240c42c3b643\scratchpad

Notable, in item order: `ev1.json`–`ev3.json` and `hook_ev*.out` (item 3(c));
`rr13_1.out`–`rr13_3.out` and `reseat_redo.py` (item 4, three byte-identical
runs and the 12-arm extractor); `rs13.out`/`rs13b.out` (ten re-seated
citations); `d1.out`–`d4.out` (the four Tier A discharges with captured exit
codes); `j_*.out`, `p_*.out`, `q_*.out` (one file per suite diagnosed in item
6); `i7b_1.out`/`i7b_2.out` and `i7_abl.out` (item 7's two runs and its
ablation); `census.out` (31 of 83); `item9.out` (the isolation proof);
`perapp2.out` (the per-app attempt that did **not** succeed, kept because the
NOT CLEARED depends on it); `docstr.out` (the AST proof that replaced my wrong
grep).
