# SAIRN platform — fourth (Ted), batch 11 continuation — handoff

**Written 2026-10-07.** Batch 11 hit 2% context mid-item and Michael
interrupted it; this session is the continuation and this is its handoff.
Written at a point where **nothing is half-finished**: everything is committed
and pushed, the clone is healthy, and the long-running job that was open
has finished.

---

## COMMITTED AND PUSHED STATE

| | |
|---|---|
| branch | `main` |
| HEAD | **`eb1c0425`** |
| pushed | **yes** — `3c7bcaed..eb1c0425`, `ahead 0 / behind 0` of `origin/main` |
| working tree | clean except **one pre-existing untracked file**, `sql/restore_demo_pins_2026-09-29.sql`, which was already there at session open and is not mine |
| `core.bare` | **unset**, verified; `git status` answers |
| long-running job | the pinned whole-tree suite **finished**, `PROGRAM_EXIT=1`, 782 lines |
| git worktrees | the one I created for the reproduction was removed with `git worktree remove --force`. **Many stale ones from other sessions remain** — see *Owed*, below |

**Commits this session landed** (SHAs after the final rebase; two earlier ones
survived three rebases unchanged because they were pushed before them):

| commit | what |
|---|---|
| `6b77545f` | 8 real red-register diagnoses, 50 → 42 empty `why` |
| `326d277e` | **convention 17** — a third state for absence is not a third state for ambiguity |
| `d5dc62b8`† | *(not mine — cc's Tier A review, landed between my pushes)* |
| `f98a4e39` | re-seat of the 7 SHAs my own rebase orphaned |
| `9e380383` | `SAIRN-ACTIVE-WORK-fourth.md` batch-11 entry |
| `eb1c0425` | **andon pulls 4–6 + item 3** — the pinned run finished, corrected the provably-wrong verdict, and broke the clone |
| *(within the above)* | item 4's live-clone selftest, the gap-doc re-derivation, the batch-11 inventory |

† listed only so the reader does not attribute it to me.

---

## PER-ITEM MAP — the dispatch's 13 items

| # | item | state | evidence |
|---|---|---|---|
| 1 | constraints query printed | **DONE** before the interruption | not reprinted, per instruction |
| 2 | map batch 11 DONE/PARTIAL/NOT DONE | **DONE** | this table, derived from `git log` and the interrupted session's scratchpad |
| 3 | pinned `seam_check` run — died or finished? | **DONE** | it **died** (`pinned.status` still `RUNNING 66464`, 656 lines, no summary, pid gone). Rerun **finished**: `PROGRAM_EXIT=1`, pinned `762b084b`, 746 files, 4 skipped by name, 83 failing. **Verdict corrected** — see below |
| 4 | two corrupting probes, claims-check then fix, selftest | **PARTIAL — and it reopened bigger** | `run_delegation_probe` **exit 0, green**, config and status unchanged, and `node --check` independently clears both files it used to sabotage. `check8_probe`'s **corruption is fixed** and it now proves that itself. **But the whole-tree run corrupted the clone again** and the writer is not either probe |
| 5 | gap docs, next slice of 30 | **DONE — 36 of 36** | `PROGRAM_EXIT=0` at `762b084b`, run 3×. The "5 of 35" premise was batch 9's |
| 6 | span sweep, 14 remaining of 38 | **DONE — 34 of 34** | `PROGRAM_EXIT=0`, judged by V8. The 38 re-derives to **34**; 3 site spans are not function bodies |
| 7 | red register, slice of 66 empty `why` | **DONE — 8 diagnosed, 50 → 42 of 79** | the 66 was batch 9's; batch 10 took it to 50. Each run individually, exit code and failing arm read. **2 of the 8 are explicitly NOT CLEARED** |
| 8 | convention 11 heading with no body | **DONE** at `b23dbc2e`, before the interruption | body present, with a note on where the text had been sitting |
| 9 | Tier A obligations | **NOT DONE — blocked, and 2 are unreviewable** | `docs/tier-a-reviews.json` is cody's; 9 eligible obligations **listed most-overdue-first**, none discharged |
| 10 | schema constraints merge | **BLOCKED on Michael**, not waited on, not guessed | unchanged |
| 11 | `demo_credentials_check.py` on SAIRNvet | **DONE — 16 of 16 OK** | `PROGRAM_EXIT=0`, sairnvet `role=owner` |
| 12 | one methodology rule + cause tags | **DONE** | convention **17** at `326d277e`; 8 cause tags in the inventory |
| 13 | handoff | **DONE** | this file |

---

## THE THREE THINGS WORTH READING FIRST

### 1. `--pinned` IS NOT ISOLATION FOR CONFIG WRITES — and it broke this clone twice in one session

The clone was found with `core.bare = true` at **session open**, repaired, and
found that way **again** right after the pinned run finished. Both times
`git status` answered `fatal: this operation must be run in a work tree`.

The mechanism is proven in two commands, and the `.git/config` delta matches
the one the run left **byte-for-byte**:

    git worktree add -q --detach <WT> HEAD
    git -C <WT> config core.bare true        # exit 0
    → the CLONE's .git/config gains `bare = true`

A linked worktree **has no config of its own**. `--pinned` isolates *files*,
not *configuration*. The runner's banner — *"Nothing done in `<REPO>` during
this run can reach it"* — is **true and one-directional**; the direction that
broke the clone is the unstated one.

`b23dbc2e` already fixed this exact defect one layer down by making
`check8_probe`'s fixture a throwaway **clone** instead of a worktree. The
runner still uses a worktree.

Full artifact, both candidate fixes (with the weaker one marked as **not**
actually closing it), and the one-command-per-candidate next step:
**`docs/2026-10-07-fourth-routed-pinned-worktree-shared-config.md`**.
`tools/run_all_tests.py` is in **no active claim** — `CLEAR` at `e50e9d5c`.

### 2. EVERY EXISTING "GREEN AT SHA X" CLAIM ABOUT THIS SUITE IS AMBIGUOUS

Two probes give **opposite verdicts** depending only on which environment ran
them — same SHA, same machine, minutes apart:

| probe | in the pinned worktree | standalone in the live clone |
|---|---|---|
| `tests/seam_check/run_delegation_probe.py` | **FAIL** | **exit 0, fully green** |
| `tests/push_gate/check8_probe.py` | **ok** | **exit 1, 2 arms failed** |

**No record on this platform names the environment** — including
`docs/known-red-suites.json`, whose entries carry a `tail` and no environment
field. That invalidates the register's premise, which is not mine to redesign,
so it is escalated rather than changed.

### 3. SIX OF EIGHT RED SUITES ARE ONE ROOT CAUSE, RUNNING IN BOTH DIRECTIONS

A probe arm that asserts something about the **live tree** is a drift
tripwire, not a test of the detector.

* **Five** say *"the tree is clean of what I detect"* and go red on ordinary
  feature work: `truthy_sum` (16 new unbaselined `|| 0` additions in
  `stonedesk.html:25471–28942`), `primitive_obsession` (18 across five apps),
  `subprocess_decode` (40 files with no `encoding=`), `write_path_scan`
  (baseline no longer passes **and a baselined count fell**), `removal_path`
  (one resource unaccounted).
* **One** says the opposite — `completeness` asserts the tool *still finds*
  `api/sen-portal.js MANAGEMENT_ROLES`, and it exits 0 because that was fixed.

**And arm ordering alone decides the blast radius from an identical
assertion:** `primitive_obsession` places it at **arm 0 as a gate**, so one
FAIL line prints and **none** of its mutation arms run — the detector is
unverified in either direction. `truthy_sum` places it **last** and still
reports 13 passing arms. **That is the next methodology rule and it is named,
not self-promoted** — one rule per real catch, and convention 17 was this
batch's.

---

## WHAT IS OPEN, AND WHY

| open item | why it is open |
|---|---|
| **the pinned-worktree config leak** | routed, not patched. The fix is a strategy change to the one tool every session uses to ask "does the suite pass", and it can only be verified by a full pinned run — **now measured at over two hours** (17:57 → past midnight for 782 lines) against 22 minutes for 656 lines earlier the same day. Landing it unverified at batch end is not a trade worth making |
| **the config writer's identity** | four bare-repo-creating candidates each came back `CONFIG UNCHANGED` **standalone — which proves nothing**, because standalone is not in a worktree, so the mechanism cannot fire. Convention 16, for the second time on this same defect |
| **`check8_probe`'s 2 red arms** | **not a regression** — the 08:41 capture already read `2 failed`, before `b23dbc2e` landed at 16:03. Both arms assert *which* refusal fires; the gate's fail-closed `no ref lines on stdin` path fires first. Environment-dependent (exit 0 four times from a dev copy). **Why is not established** |
| **9 Tier A obligations** | the write is cody's and I did not override it. **The two most overdue cannot be reviewed at all**: `54e4835ac96e` and `f88105a88287` are genuinely absent, so there is no diff to read |
| **item 10, schema constraints** | needs Michael's SQL result. Not waited on, not guessed |
| **42 red-register entries** | undiagnosed. 2 of the 8 I did are **NOT CLEARED** and say so |
| **3 span sites, 17 gap-doc count claims, 40-file `encoding=` sweep, 16 + 18 unbaselined numeric occurrences** | measured and routed, not acted on |
| **stale git worktrees** | `git worktree list` shows a long tail from other sessions — `check8-probe-*` ×5, `condcov-*` ×3, `cc-review-*` (locked), `sairn-suite-pinned-*` ×3 on disk. **Not mine to prune**, and `tools/clone_health_check.py` already names `git worktree prune`. Flagged, untouched |

---

## CLAIMS HELD

**One, and it must be released by whoever picks this up if I do not return:**

    python tools/sairn_claim.py release fourth

Its text declares, and I did not override any of it: `docs/tier-a-reviews.json`
is **cody's** (claim past the 4h timer, but `sairn_status.py` showed cody
`working` LIVE on queue19 whose first item is this work verbatim — **expiry is
a timer, not a release**, and hank's later claim confirms cody re-took the file
at 2026-10-06T22:06:45Z and has already written a discharge by takeover);
`docs/METHODOLOGY.md`, `docs/CRITICALITY-TIERS.md`,
`docs/SAIRN-OPEN-WORK-INDEX.md` and `tools/tooling_inventory.py` are **hank's**
or **cody's**; `tools/sairn_push_gate_hook.py` is **cc's**.

**`docs/2026-10-07-fourth-routed-pinned-worktree-shared-config.md` is not in
that claim's FILES list** — it was created after the claim, and it is new and
uncontested. Stated rather than left to be noticed.

---

## EXACT NEXT STEP, PER OPEN ITEM

1. **Identify the config writer.** For each of
   `tests/claims/run_freshness_probe.py`, `tests/run_cron_liveness_probe.py`,
   `tests/claims/run_push_verify_probe.py` and any other caller of
   `git init --bare`: `git worktree add --detach <WT> HEAD`, copy
   `.git/config`, run the probe **with cwd inside `<WT>`**, diff the clone's
   config. One command per candidate. Standalone runs do **not** reproduce it.
2. **Fix `--pinned`** with a throwaway **clone**, not a worktree — the shape
   already proven at `b23dbc2e`. Budget **over two hours** for the verifying
   run, and add a `.git/config` snapshot-and-compare to the runner so it
   reports what it did to the clone. The `extensions.worktreeConfig` route
   does **not** close it; the routed doc says why.
3. **Wire `tools/clone_health_check.py` to run after a suite run.** It already
   detects `core.bare is TRUE in a clone with a working tree`, is clean, and
   does not write (`--fixtures`, exit 0, `CONFIG UNCHANGED`). **Cody's tool,
   cody's call.**
4. **`check8_probe`'s 2 arms**: find why `git push --dry-run` delivers no ref
   lines to the pre-push hook in this clone but does in a dev copy. The clone
   being ahead of `origin/main` is a candidate, not a finding.
5. **Red register**: 42 left. Start with `write_path_scan`'s **fallen baseline
   key** — a drop means the scanner may have stopped seeing files, which a
   ratchet cannot self-diagnose — then `removal_path`'s unaccounted resource.
6. **Tier A**: when cody releases `docs/tier-a-reviews.json`, discharge the 9
   in the order tabled in the andon log. **Do not discharge the top two** —
   `54e4835ac96e`, `f88105a88287` — their subject diffs are absent; they need a
   reseat or a re-derivation from the author, not a signature.
7. **Item 10**: merge Michael's SQL result into the snapshot, claims-checking
   cody's snapshot first. **An empty `{"_constraints": {}}` is valid and gets
   merged** — the preflight distinguishes *asked and none* from *never asked*.
8. **Span sites**: repoint the 3 that are not function bodies, one planted
   control per site proving the new span is the right one.
9. **Promote the arm-ordering rule** (section 3 above) as convention 18, from
   its own evidence, when somebody other than me has read the eight
   diagnoses.

---

## A SMALL THING THAT COST TIME TWICE, SO IT IS WRITTEN DOWN

**A dated document that cites its own batch's commit SHAs is guaranteed to be
orphaned by the next rebase.** Mine were, 20 minutes after writing them.
`.githooks/post-rewrite` ran and correctly reported *"NONE of them is cited in
the tracking documents"* — it re-seats the defect register and the generated
pair, and a dated inventory is **neither**, so its clean verdict was true and
did not cover me. Cite a SHA only after the final push, or cite by commit
subject.

**And the verification I used for the re-seat was itself wrong**, which is the
more useful half: `git cat-file -e <sha>^{commit}` tests whether the **object
exists**, not whether any ref reaches it, and an orphaned commit's object
survives until `git gc` — so it answered OK for all four orphans and would
have let the re-seat pass itself as verified. `git merge-base --is-ancestor
<sha> origin/main` is the test that answers the question, and it separates
three states where `cat-file` sees two: **on a ref**, **orphaned but present**,
**absent**. Corrected in both documents, and recorded as a second instance of
convention 17 rather than promoted to an eighteenth.

---

## THIS SESSION'S TRANSCRIPT

Scratchpad, with every captured run and exit code:

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\4975e2e9-8002-4f73-9d9d-240c42c3b643\scratchpad

Notable files in it: `pinned2_stdout.txt` / `pinned2_run.txt` (782 lines) and
`pinned2_exit.txt` (`PROGRAM_EXIT=1`); `gitconfig_before.txt` and
`gitconfig_corrupted2.txt` (the two-state config pair that proves the delta);
`c8_live.out` and `dlg_live.out` (item 4's selftests); `gv5all.txt` (36 gap
documents); `span_head.txt` (34 span sites); `rr_*.out` (the eight red-register
diagnoses, one file each); `demo.out` (16 of 16); `gapverify2.py` (the hardened
verifier with its fourth and fifth states).

**The interrupted session's scratchpad**, which carries the batch-11 work this
one continued — including `pinned.status` showing `RUNNING` with no exit line,
which is how the death was established:

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\c430231c-cc9c-43df-9850-e4efe2dd54a3\scratchpad
