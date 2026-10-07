# Handoff — fourth (Ted), batch 12, 2026-10-07

Written at a point where **nothing is half-finished**: every change is
committed and pushed, the clone is healthy, no long-running job is open, and
the claim is released at the end of this file.

---

## COMMITTED AND PUSHED STATE

| | |
|---|---|
| branch | `main` |
| pushed | **yes** — final push below; `ahead 0 / behind 0` of `origin/main` at the time of writing |
| working tree | clean except **one pre-existing untracked file**, `sql/restore_demo_pins_2026-09-29.sql`, which was there at session open and is not mine |
| **`git config core.bare`** | **empty — unset.** Printed at the end of this file as the dispatch asked. `git status` answers normally |
| long-running jobs | **none.** No whole-tree run and no `--pinned` run was started, per the standing instruction; every suite was run individually |
| `git stash` | **one entry held: `stash@{0}: autostash`.** It is the two report-only sweep-state files that upstream `ba5c15dd` deleted and gitignored. Kept rather than dropped so nothing is lost; safe to drop |

**Commits this batch landed** (verified `ON-REF` with
`git merge-base --is-ancestor <sha> origin/main`, not with an existence test):

| commit | what |
|---|---|
| `850a4849` | the **environment stamp** on all 79 register rows, plus 4 arms in `known_red_check.py --fixtures` |
| `905b1736` | **11 more red-register diagnoses**, each suite run alone |
| `f2ee7be0` | **convention 19** — the Tier A gate's freshness path asked existence, not reachability |
| `780004db` | the convention-19 defect registered (the push gate required it) |
| `c74f5e6f` | **two Tier A discharges**, four routed back as ABSENT |
| `c6a841cb` | **convention 18**, the arm-ordering fix, the postmortem, the coverage ledger |
| *(this one)* | SHA re-seat + this handoff |

---

## PER-ITEM MAP

| # | item | state | evidence |
|---|---|---|---|
| 1 | Tier A: discharge most overdue; note the absent ones | **DONE** | `c74f5e6f`. **2 discharged** via `--discharge`, exit 0 each; **4 routed back as ABSENT** with merge-base proof, none reclassified. `docs/tier-a-reviews.json` was **FREE** — no active claim declared it |
| 2 | print the constraints SQL verbatim | **DONE** | top of the report |
| 3 | re-seat verification redo by merge-base | **DONE** | `850a4849` message + `<scratchpad>/reseat_redo.out`. 12 SHAs over 7 docs: 7 ON-REF, **3 ORPHANED**, 2 ABSENT. The 3 orphaned are exactly the ones an existence test answers OK for |
| 4 | core.bare evidence attached to cody's finding; no hunt, no patch | **DONE** | `docs/2026-10-07-fourth-routed.md` item 6. `tools/run_all_tests.py` **untouched** — cody's live claim |
| 5 | environment stamp, backfill where provable, X of 79 | **DONE — 70 of 79** | `850a4849`. 13 all four keys, 57 where/pinned/tool with `sha` unknown, **9 wholly unknown and never guessed** |
| 6 | ≥10 more empty-`why` diagnoses | **DONE — 11**, 42 → **31** of 79 | `905b1736`. Each run alone, own exit code, failing arm read |
| 7 | convention 18: artifact per suite, then fix what verifies | **DONE — 8 artifacts, 1 fixed** | `c6a841cb` + routed doc item 9. The one fixed was the only **gate**; 3 stay **NOT CLEARED** by name |
| 8 | the 7 "WinError 123" rows → could-not-run | **PARTIAL, and the premise does not hold** | **There is no WinError 123 row inside the 83.** That was ONE row in the 08:41 **un-pinned** run, corrected in batch 11. Of the 7 precondition-stop rows I shortlisted, **5 are could-not-runs and 2 are not**, each re-verified alone. So **83 = 78 FAIL + 5 COULD-NOT-RUN as far as individually verified** — a floor, not a census |
| 9 | constraints merge | **BLOCKED on Michael.** Nothing done, nothing guessed | — |
| 10 | coverage ledger, exhausted at this depth | **DONE** | `docs/2026-10-07-fourth-coverage-ledger.md` |
| 11 | postmortem + one system fix in an existing check + the arm | **DONE** | `docs/2026-10-07-fourth-postmortem-object-existence.md`, fix at `f2ee7be0` |
| 12 | conventions 18 and 19 into METHODOLOGY as chat-adopted | **DONE** | `c6a841cb`. Full sections in `docs/2026-09-13-cross-domain-disciplines.md`, recorded in `docs/METHODOLOGY.md` as **chat-adopted** |
| 13 | handoff, release, print `core.bare` | **DONE** | this file |

---

## THE THREE THINGS WORTH READING FIRST

### 1. The Tier A gate was printing verdicts computed against commits no other clone has

`tools/tier_a_review_gate.py` resolved each record's subject SHA with
`git rev-parse --verify --quiet <sha>^{commit}` — an **existence** test — then
diffed against it and printed an ordinary FRESH or STALE verdict.
`docs/tier-a-reviews.json` cited **seven orphaned 40-char SHAs**, and
`** STALE ** moved since 00030f2d11b7` was printed on an **open** obligation.

**The gate already contained the right test** — its own `_is_reachable()` uses
`merge-base --is-ancestor`, ~1,500 lines below. The file carried both the strong
and weak form and the path that mattered used the weak one.

Fixed at `f2ee7be0`; four open records now report `COULD-NOT-TELL … ORPHANED`.
**The seven ledger SHAs are NOT fixed** — the gate only reports them now, and
re-seat-or-retire is a per-record decision for each author.

### 2. The first arm I wrote to enforce that convention was VACUOUS, and only an ablation found it

It sliced ~1,500 lines of source and **swallowed the definition of the function
it was looking for**, so the substring matched whether or not the code called
it. **With the guard removed, the probe stayed green.** I would otherwise have
shipped a convention, a fix and a guard that could not fail, and reported all
three as verified.

Window now bounded to 3,000 bytes, truncated at `def _is_reachable`, **the bound
asserted by its own arm**, and the extraction exercised in both directions
against synthetic sources. Re-ablated: guard removed → exit 1 naming both arms;
restored byte-identical; guard back → exit 0.

### 3. `tools/bare_run_write_check.py` will accept a LINKED WORKTREE as a scratch target

Found while reviewing cody's obligation, which asked for a third option on
exactly this. `REAL_CLONE_RX` is end-anchored and **does not match a worktree of
a real clone** — measured `False` for a live one, and **five such worktrees are
on disk now**. A worktree **shares `.git/config`**, which is how
`core.bare = true` reached this clone twice on 2026-10-06, and this is a
275-tool bare sweep.

**The third option, measured both ways:** refuse any target where
`git rev-parse --git-common-dir` differs from `--git-dir`. Shape-free, so it
answers cody's own objection that a clone registry goes stale. Routed, not
patched.

---

## WHAT IS OPEN, AND WHY

| open | why |
|---|---|
| **31 empty-`why` register rows** | 42 → 31 this batch. Two of the earlier eight stay **NOT CLEARED**: `write_path_scan`'s fallen baseline key and `removal_path`'s unaccounted resource are still unnamed |
| **`core.bare` leak** | **cody's**, by agreement. `tools/run_all_tests.py` is in cody's live claim and I did not patch it, did not hunt the writer again, and ran no whole-tree or `--pinned` run. My evidence is attached to cody's finding |
| **4 absent-SHA Tier A obligations** | routed to hank (×2) and cody (×2) to close as ABSENT. **I did not reclassify them.** Two are 248h and 224h; two are **51h and 47h**, so this is still happening |
| **4 Tier A obligations still open to me** | 2 discharged of 8 eligible. Next by age: cody `2026-09-30T12:08:26Z` (168h, STALE, `sv_audit_log`) then hank `2026-09-30T12:59:51Z` (167h, fresh, 7 resources) |
| **7 orphaned SHAs in the ledger** | reported by the gate now; re-seat-or-retire is per-record and per-author |
| **ten other `cat-file` / `rev-parse --verify` call sites** | recorded as `recurrence_open` in the defect register. **None has been read** to decide whether it asks existence where it means reachability |
| **3 convention-18 suites NOT CLEARED** | `write_path_scan`, `removal_path`, `preauth_exemption_anchor` — each missing one named fact |
| **item 9, constraints merge** | needs Michael's SQL result |
| **`tests/claims/run_registry_claim_probe.py` and `…_sabotage_probe.py`** | red in the pinned run and **unregistered**, so `known_red_check` would call them NEW. I drove only one of the two, so I added neither row |
| **stale git worktrees** | `check8-probe-*` ×5, `condcov-*` ×3, `cc-review-*` (locked), and `sairn-suite-pinned-*` on disk. Not mine to prune; `tools/clone_health_check.py` already names `git worktree prune` |

---

## CLAIMS

**`fourth` is RELEASED at the end of this batch** — see the last section.

**Held by others and not overridden:** `tools/run_all_tests.py`,
`tools/capture_exit.py` and `tools/metamorphic_check.py` are **cody's** under a
claim taken 0.2h before mine. `docs/tier-a-reviews.json` was in **no** active
claim's FILES list when I checked, which is why item 1 proceeded.

**Two files I touched that I do not own, both declared:**
`docs/scrutiny-flags.json` is **cc's** — cc's hook wrote my two files into it
during my commits and I published that, **union-merged on cc's upstream version
so nothing of cc's was dropped** (15 upstream + my 2 = 17).
`docs/defect-density-register.json` was written through the sanctioned
`tools/defect_register.py --add`, because the push gate refused the fix commit
without a record.

---

## EXACT NEXT STEP, PER OPEN ITEM

1. **Tier A, next two by age:** cody `2026-09-30T12:08:26Z` (`sv_audit_log`,
   STALE, subject SHA `5a32fa3c4de0` is **ON-REF** so it is reviewable), then
   hank `2026-09-30T12:59:51Z`. Use
   `python tools/tier_a_review_gate.py --list` and read the `what` field — and
   **do not review against `opened_at_sha`**: in both records I discharged it
   was a merge or a claims commit and did not contain the subject at all.
2. **The four ABSENT obligations:** wait for hank and cody to close them. Do
   **not** discharge them — there is no diff to read and no reseat target.
3. **Register, 31 left:** continue one suite at a time, exit code from its own
   output, environment stamped. Start with the two NOT CLEARED facts
   (`write_path_scan`'s fallen key, `removal_path`'s resource) because both are
   one command away and both are the kind a ratchet cannot self-diagnose.
4. **When cody's `run_all_tests.py` change lands:** record `git config -l`
   **before and after one targeted run** and confirm `.git/config` is
   byte-identical. Until then `check8_probe` and `run_delegation_probe` stay as
   **fixed** — both were selftested in the live clone in batch 11.
5. **The ten unread reachability call sites:** read each and decide whether it
   asks existence where it means reachability. List is in the defect register's
   `recurrence_open` and in the postmortem.
6. **`bare_run_write_check.py`:** cody's, with the discriminator written out.
7. **Item 9:** merge Michael's SQL result into `schema_snapshot._constraints`,
   claims-checking cody's snapshot first. **An empty `{"_constraints": {}}` is
   valid and gets merged** — the preflight distinguishes *asked and none* from
   *never asked*.
8. **The three span sites** from the coverage ledger still need a planted
   control each before any repoint.

---

## TWO MEASUREMENT CAVEATS I AM NOT LEAVING FOR SOMEBODY ELSE TO TRIP ON

**1. My own SHA sweeps over-report ABSENT, because an 8-hex regex is not a SHA
detector.** The final sweep across 11 of my documents reported 15 ABSENT
tokens. Among them: `20260318` and `20260825` (dates), and `4975e2e9` and
`c430231c` (**scratchpad session UUIDs**, which appear in the handoff on
purpose). The same inflation applies to the 62 ABSENT reported from
`docs/tier-a-reviews.json`, which picked up `4111111111111111` and
`1234567890123`. **The ORPHANED counts are the trustworthy ones** — every
orphaned token found was a genuine 40-char SHA. Do not quote my ABSENT totals.

**2. Six citations were ORPHANED at the end of this batch and I re-seated two.**
`9e380383` → `9e380383` and `f2ee7be0` → `f2ee7be0`, each replacement verified
`ON-REF` by `merge-base --is-ancestor` before the swap. The other four —
`100b82fc`, `7c911e5c`, `6984634e`, `53cc408e` — are **deliberately left
orphaned**: the first three are the subject of the postmortem and naming the
dead SHAs is the point, and the fourth predates this batch. **A dated document
citing its own batch's SHAs is orphaned by the next rebase** — cite after the
final push, or cite by commit subject.

---

## THIS SESSION'S TRANSCRIPT

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\4975e2e9-8002-4f73-9d9d-240c42c3b643\scratchpad

Notable: `reseat_redo.out` and `reseat_final.out` (item 3, both directions);
`env.out` and `arm_ablation.out` (the stamp and its ablation);
`i6_*.out` and `i8_*.out` (one file per suite diagnosed, each with its own exit
code); `c19_ablate2.out` (the convention-19 ablation that passed after the
first one failed); `po_ablate.out` (the no-op-mutation ablation);
`disch1.out` / `disch2.out` (the two Tier A discharges);
`dr_add6.out` (the defect record); `ta_reach.out` (the seven orphaned ledger
SHAs); `sf_merge.out` (the union merge on cc's scrutiny flags).

The **batch-11** scratchpad, which this batch's items 3 and 4 continue from:

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\c430231c-cc9c-43df-9850-e4efe2dd54a3\scratchpad

---

# BATCH 13 CHECKPOINT LOG — one row per item, appended as each closed

| item | state | commit / seq | exact next step |
|---|---|---|---|
| **3(a)** create the hook script | **DONE** | `C:\SAIRN-status\sairn_status_hook.py`, verbatim, nothing changed | none |
| **3(c)** prove it | **DONE** | `G:\My Drive\SAIRN-status\SAIRN-fourth.status.json` and `events.log` written; hook `PROGRAM_EXIT=0` on all three sample events | none |
| **3(b)** merge the hooks into settings | **NOT DONE** | cody's live batch21 claim declares `.claude/settings.json` and says **SOLE TOUCHER**, and that permissions merge **has not landed**: `~/.claude/settings.json` carries only a `PreCompact` hook, and no commit has touched `.claude/settings.json` since 2026-10-05 | the item's own instruction says to stop in exactly that case. Re-check once cody's batch21 lands |
| **1** Tier A discharges | **DONE — 4** | the four `verdict` fields in `docs/tier-a-reviews.json`; three by `--takeover` with the handover recorded | 4 ABSENT remain, owed back as SEQ 13-A. Next readable one is whatever the gate lists after hank and cody close those |
| **2** print the SQL | **DONE** | top of the report; the merge stays **BLOCKED on Michael** and nothing was done on it | wait for Michael's SQL result |
| **4** SHA extractor | **DONE** | fixed in `<scratchpad>/reseat_redo.py`, 12 selftest arms, 3 byte-identical runs; figures in `docs/2026-10-07-fourth-coverage-ledger.md` §4 | route the four rejection rules to cc for `tools/doc_sha_reseat.py`, the durable reader |
