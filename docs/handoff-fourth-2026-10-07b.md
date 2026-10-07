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
| HEAD at this checkpoint | `bcc743db` |
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
