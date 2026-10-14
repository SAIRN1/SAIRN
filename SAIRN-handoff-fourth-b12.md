# HANDOFF — fourth / ted, batch b12, 2026-10-14

**Written BEFORE the report**, at a point where nothing is half-finished: the
five substantive items are committed and pushed, `HEAD == origin/main`, the
working tree is clean, no rebase or stash is in progress.

**EVERY FIGURE BELOW NAMES THE COMMAND THAT PRODUCED IT** (b11's rule), and
every checker figure comes from a checker that has now been **driven on a
deliberately bad input and seen to fail closed** (b12's rule, below).

**Transcript and working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\240036a6-0d02-441d-a22d-73ed022c11a3\scratchpad\`
The derivations are scripts, not prose: `bad_drive_b12.py` (+
`bad_drive_b12.log`) is new in this batch; `ack_check.py`, `index_resolve.py`,
`ablation_b12.py` and `gen_undriven_doc.py` were carried in from b11's
scratchpad at
`...\d1bef68d-f747-45a9-89b1-59dd99a42ae2\scratchpad\` and re-driven here.
Logs: `ack_live_b12.log`, `ack_fixtures_b12b.log`, `index_fixtures_b12b.log`,
`ablation_b12b.log`, `gen_undriven_b12b.log`, `why_unmoved_b12b.log`,
`cody_latest_push_b12.log`, `spec_premises_b12.log`, `holds_b12.log`,
`hooks_settings_b12.log`, `push_b12.log`, `landed_b12.log`.

---

## 0. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| HEAD | `73700129` | `git rev-parse HEAD` |
| `origin/main` | `73700129` | `git rev-parse origin/main` |
| behind / ahead | **0 / 0** | `git rev-list --left-right --count origin/main...HEAD` |
| working tree | clean | `git status --porcelain` (empty) |
| the b12 work commit | `73700129`, 3 files, +536 | `git show --stat --format= 73700129` |
| the b12 claim commit | `c0cd082b` | `git log --format=%h --all --grep="fourth claims fourth -- batch b12 -- (1) re-drive"` |
| push forced? | **NO** | one rebase onto `d29b8846`, then `d29b8846..73700129` |
| `SAIRN_SEED_GATE=off` | **not used**, any form | — |
| `.claude/settings.json` | **not committed by me** | see §5 — it is NOT hooks-empty any more, and that is somebody else's commit |
| files edited under `tools/` | **0** | by instruction; item 3 is route-only |

**`73700129` IS THE STATE AT FINALISATION OF THIS HANDOFF and will be stale by
the time you read it** — the report, the digest and the claim release all land
after it. **Re-derive HEAD rather than quoting this table.**

---

## 1. ITEM BY ITEM

| # | item | state | exact next step |
|---|---|---|---|
| 1 | re-drive both fail-open-first checkers on a deliberately bad input, record fail-closed | **DONE — 10 arms, 0 failing, exit codes asserted** | nothing |
| 2 | the bad-input-fixture rule into `docs/METHODOLOGY.md`, applied to both checkers | **DONE — and the rule grew a third part when driven** | **nothing mechanises it**: no gate refuses a checker with no `--fixtures` arm. That is the obvious next piece and belongs to the `tools/` owner |
| 3 | docs spec for a by-design-register validator, routed to the `tools/` owner | **DONE — routed, no `tools/` edit** | **cc writes either half**: `tools/by_design_register_check.py` to the spec, or a `NOT_PROMOTED` entry saying why a one-row register does not need one, with the reason |
| 4 | the routed-findings ack check re-run against current `origin/main` | **DONE — still 6 of 9 UNACKNOWLEDGED** | **tests owner 4, tools owner 2** — see §3 |
| 5 | regenerate the 36-undriven-suites doc after the tests owner's latest push | **DONE — 36, byte-identical output** | **the tests owner drives the 36 in a worktree**; its b8 push is a claim, not results (§3) |
| 6 | push without force, confirm it landed | **DONE — `d29b8846..73700129`, 0/0** | nothing |
| — | this handoff, before the report | **DONE** | — |

### Item 1, with the command and the output

    CMD python scratchpad/bad_drive_b12.py          ->  exit 0
        ok  A1  no NOT_PROMOTED block in the ACK source        want 2  got 2
        ok  A2  a routing document it reads is absent          want 2  got 2
        ok  A3  v2 on a MENTION-ONLY block                     want 1  got 1
        ok  A3  ABLATED (guard removed) is FAIL-OPEN           want 0  got 0
        ok  I1  a declared DRIVE path that does not resolve    want 1  got 1
        ok  I2  the Drive index is absent                      want 2  got 2
        ok  I2b the Drive index is not valid JSON              want 2  got 2
        ok  I3  v2 on one UNEXPLAINED dead docs/ token         want 1  got 1
        ok  I3  ABLATED (guard removed) prints it and ALLOWS   want 0  got 0
        ok  I4  CONTROL: the 3 EXPLAINED tokens alone PASS     want 0  got 0
        10 arm(s), 0 failing

Each checker was also re-driven in-process, unchanged from b11:
`ack_check.py --fixtures` → 8 arms, 0 failing; `index_resolve.py --fixtures` →
8 arms, 0 failing; `ablation_b12.py` → exit 0.

**TWO THINGS THE END-TO-END RUN FOUND THAT NO IN-PROCESS ARM COULD, and the
next session should not "fix" either back:**

1. **MY OWN FIRST BAD-INPUT FILE TESTED THE OPPOSITE OF WHAT IT CLAIMED.** Arm
   A1 writes a `report_only_checks.py` with *no* `NOT_PROMOTED` block — and my
   first version said exactly that **in a comment**. The reader is a substring
   search, it found the token in the comment, and the arm returned **exit 0
   where it must be exit 2**. Caught only because the arm declares the exit code
   it demands. The fixture file must never name the token it is built to lack.
2. **`ack_check.v1.py` AND `index_resolve.v1.py` IN b11's SCRATCHPAD ARE NOT THE
   AS-SHIPPED VERSIONS.** They are mid-patch snapshots and already carry the fix
   at the use site: driven on the bad trees, both produce the *corrected*
   verdict. **"Driven against v1" would have been a false evidence line**, and
   those checkers were never committed, so no as-shipped copy exists in git. The
   ablation therefore removes the one guard from the **real current file** by
   exact text substitution and **refuses unless the substitution applies exactly
   once**.

---

## 2. CLAIMS, LOCKS AND EXTERNAL HOLDS

| hold | count | detail | command |
|---|---:|---|---|
| repo claims held | **1** | b12, published on `origin/main` in `c0cd082b`; release it when the report and digest are up | `sairn_claim.py list` |
| **my claim reads DEAD** | — | `state: DEAD, because CLAUDE_PID 53204 no longer exists` — the PID heartbeat is not re-stamped between tool calls. **The entry is published and the work landed in `73700129`**; the liveness field is what is wrong, not the claim. Same shape hover2 hit in b19 and b20 | `sairn_claim.py own` |
| session locks held | **1** | `fourth.lock`. 14 lock files exist in `~/SAIRN-SESSION-LOCKS/`, including `b12wt2.lock`, which is still the orphan b11 recorded | `ls ~/SAIRN-SESSION-LOCKS/*.lock` |
| locks released by me | **0** | none of the dead ones is attributable to me | — |
| worktrees besides main | **4** | **none mine**: `gate12-65340-3`, `invis-c0-75132`, `sairn-abl-q_gv10j5`, `sairn-gate-base-d78d62e71203` — unchanged from b11, the last still the push gate's own unremoved throwaway | `git worktree list` |
| `git stash` | **0** | two stashes were taken and popped during this batch to let the claim rebase; none is held | `git stash list` |
| `refs/salvage/*` | **0** | | `git for-each-ref refs/salvage/` |

**Nothing was edited outside the declared `FILES` set, and no file under
`tools/` was edited.**

---

## 3. WHAT IS OPEN, AND WHY — owner and exact next step

### THE SIX UNACKNOWLEDGED ROUTED FINDINGS — unchanged, re-measured

    CMD python scratchpad/ack_check.py        ->  exit 1
        BY STATE: {'UNACK': 4, 'MENTION_ONLY': 2, 'ACK_COMMIT': 1, 'ACK_STATUS': 2}
        UNACKNOWLEDGED (UNACK + MENTION_ONLY): 6   of 9 in scope

**tests owner (cody) — 4, all from b9.** Next step for each: a commit touching
the line, or a `NOT_PROMOTED` entry naming the file **and** the line. Nothing
else closes it.

* `tests/faults/grd_write_faults.js:385` — UNACK
* `tests/push_gate/check8_probe.py:209` — UNACK
* `tests/sairnlegacy_session_gate_review_probe.js:202` — UNACK
* `tests/seed_never_syncs_platform.js:274` — UNACK

**tools owner (cc) — 2, both MENTION_ONLY, which is NOT acknowledgement.**

* `tools/hover_auditor_scope_gate.py:409` — also carries the single row in
  `docs/by-design-register.json`, state `DECIDE_OR_NOT_PROMOTED`. Next step:
  either half of that state.
* `tools/session_lock_check.py:128` — routed in b9,
  `docs/2026-10-13-fourth-routed-to-cc.md`.

**hank — 0 routed `file:line` findings**, stated rather than left as an empty
section.

**WHY THEY DID NOT MOVE, measured over a 27-commit window:**

    CMD git rev-list --count 29f27993..origin/main                    ->  27
    CMD git log --format=%h origin/main --not 29f27993 -- <the six routed files>
        (empty)
    CMD git log --format=%h origin/main --not 29f27993 -- tools/report_only_checks.py
        (empty — a NOT_PROMOTED decision would have landed here)

### THE 36 UNDRIVEN SUITES — and the tests owner's latest push is a CLAIM, not a result

    CMD python scratchpad/gen_undriven_doc.py        ->  exit 0
        undriven rows        : 36
        list/TSV cross-check : IDENTICAL (36 names)
        undriven by owner    : {'cody': 36}
        driven b9 states     : {'RED': 43, 'COULD NOT RUN': 5}
        entries with no why  : 21
    CMD git diff --stat -- docs/2026-10-13-fourth-b10-undriven-suites.md
        (no output — the regenerated file is byte-identical)

    CMD git show --stat --format= 433860be          ->  .claude/claims/cody.json only
    CMD git cat-file -e origin/main:docs/2026-10-13-cody-b8-undriven-suite-results.md
        exit 128  (that results document is NOT on origin/main)
    CMD git log -1 --format='%h %cI' origin/main -- docs/known-red-suites.json
        5bb0950a 2026-10-13T16:33:58-04:00

The tests owner's b8 claim declares a results document and *"first 12 undriven
suites from fourth b10"*; the push carries **one file**, the claim itself. So
the 36 is not a figure read too early — the work is claimed and in flight, and
the register it would move was last touched before b11's own measurement.
**Exact next step: the tests owner drives the 36 in a worktree** (several write
when run); exit 0 moves an entry out of `entries`, exit 2/3/timeout must not.

### The rest, each another session's or an observation with its owner named

* **The b12 rule is mechanised by nothing.** No gate greps for a `--fixtures`
  arm and refuses a checker without one, and the ablation is **per guard** — a
  checker with ten guards and one fixture is locked at one point. `tools/`
  owner's call; deliberately not built here.
* **`docs/by-design-register.json` still has exactly 1 row and still no reader.**
  The validator is now **specified** —
  `docs/2026-10-13-fourth-b12-routed-to-cc-bydesign-validator.md`, 15 arms of
  which 4 exist to stop it over-refusing — and **built by nobody**. Every
  premise of that spec was re-verified at this HEAD: 1 ruling row, the four
  states read from the register's own `_the_states`, all seven cited tools
  present, `tools/by_design_register_check.py` correctly ABSENT.
* **21 of 84 red-suite register entries carry no `why`, and 5 of the 48 driven
  came back COULD NOT RUN** — a suite that cannot run has no verdict and reads
  as "still red" for ever.
* **The unfetched-base checker is specified and built by nobody**; recorded as a
  *planned* action on defect record **`55777a74`** (b11's handoff spells it
  `5577a74`, one `7` short — the register's own
  `evidence.planned_action_recorded_on` is the authority) and as the register's
  one ruling row, `2026-10-13-unfetched-base-scope-gate`.
* **4 pre-existing bad rows in `docs/scrutiny-flags.json`** — already on
  `origin/main`, the tests owner's file; they make
  `tools/sairn_rebase_resolve.py` REFUSE on every scrutiny-flags conflict.
* **`docs/TOOLING-INVENTORY.md` cannot be regenerated in this working tree and
  that is correct** — `tools/tooling_inventory.py` derives one of seven sources
  from `.claude/settings.json` and refuses (exit 2) rather than writing a
  thinner document. Regenerate it inside a detached worktree of the commit.
  **Do not restore hooks to make it pass.**
* **`fourth.lock`** — still held; release denied by the permission layer for a
  **sixth** successive batch. A standing fact about this clone, not an event.

---

## 4. THE ONE THING THE NEXT SESSION MUST NOT "FIX"

**`.v1.py` files in a scratchpad are not evidence.** See §1. If you need to show
a fail-open guard, **ablate the current file** and assert the substitution
applied — do not drive a snapshot whose provenance you have not checked.

---

## 5. HOOKS — THE STATE CHANGED, AND NOT BY ME

    CMD python -c "json.load(.claude/settings.json)['hooks']"
        hook groups: 1, entries: 1
    CMD git log --format='%h %s' -1 -- .claude/settings.json
        eb53e267 feat(compaction survival): ONE SessionStart hook on matcher
                 compact -- the authorised exception, and not a restoration

**I added nothing, restored nothing, and committed nothing to that file.** It
arrived on `origin/main` in another session's commit before this batch opened,
and the working tree matches HEAD (`git status --porcelain` empty). Recorded
because b11's handoff says *hooks 0 groups, 0 entries*, and a session that
quotes that line will conclude something was restored here.

**Nothing is partial.** Every open item above is another session's, or an
observation with its owner named, or a measurement with its command stated.
