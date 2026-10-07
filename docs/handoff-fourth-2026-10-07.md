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
`100b82fc` (now `6b77545f`), `7c911e5c` (now `326d277e`), `6984634e` (now `7eabd192`), `53cc408e` — are **deliberately left
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
| **5** the 3 orphaned citations | **DONE — self-repair, not a routing** | SEQ 13-D in `docs/2026-10-07-fourth-routed.md`; 15 occurrences annotated with their live equivalent | none. `.claude/claims/fourth.json` still cites them and is left alone on purpose: a claim file is a record of what was claimed |
| **6** red register, next 10+ | **DONE — 12**, 31 → **19** of 79 | see the twelve `why` fields; commit below | 19 left. Start with `tests/hover_separation_ci_probe.py` — it is a DEAD GATE, not a red test |
| **7** convention-18 fixes | **PARTIAL — 2 of 8** | `run_write_path_scan_probe` fixed, verified twice, ablated; coverage ledger §10 | 6 open with artifacts. Next is naming WHICH app rose and which fell, through the ratchet's own code path |
| **8** census toward the 83 | **PARTIAL — 31 of 83** | coverage ledger §5; the 83 re-extracted from the pinned log, not quoted | 52 unverified. Note 4 of the 31 exit 2 and 1 now exits 0 |
| **9** cody's `run_all_tests.py` change | **DONE — LANDED and VERIFIED** | SEQ 13-F; `git config -l` 29→29 identical, `.git/config` 489→489 byte-identical, `core.bare` None→None | none. cody closes the finding; this is confirmation attached to it |
| **10** `bare_run_write_check.py` owner | **DONE** | SEQ 13-E; owner is **cody** on three pieces of evidence, and the owner map says `basis: NONE` because the file has no `OWNER:` line | cody patches it; the missing OWNER line is the 283-header backlog showing up where it costs something |
| **11** METHODOLOGY ablation convention | **DONE** | conventions **20** (mine) and **21** (cody's, verbatim) in `docs/2026-09-13-cross-domain-disciplines.md`; promotion rows + the received-routings table in `docs/METHODOLOGY.md` | cause tags are in both sections. Two claim checks said BLOCKED on the SUBJECT WORD, not on either file — recorded in METHODOLOGY.md rather than silently proceeded past |
| **12** final handoff + release | **DONE** | this file and the FINAL STATE section of `docs/handoff-fourth-2026-10-07b.md` | claim `fourth` released; `git config core.bare` printed in the report |

# BATCH 14 CHECKPOINT LOG

| item | state | commit / seq | exact next step |
|---|---|---|---|
| **1** full SHA sweep | **DONE** | coverage ledger §6; `<scratchpad>/sweep_full.py`, 13 arms, 3 byte-identical runs, `PROGRAM_EXIT=0` | the premise was one batch stale — the width was fixed in batch 13; the CORPUS was the narrow part. **79 orphans repo-wide; do not quote the 13,807 ABSENT** |
| **2** the 4 ABSENT Tier A | **DONE** | SEQ 14-A; `--reseat-shas --write`, `PROGRAM_EXIT=0`, 5 reseated on a strong basis | **two are now STALE and REVIEWABLE** (hank 54h, cody 50h) — discharge those next. The weak-basis one needs `--write-weak-basis`, an explicit containment decision for cody. The 251h one is `[NO_OBJECT_IN_CLONE]` and can only be reseated from hank's own clone |
| **3** red register next slice | **DONE — 9**, 19 → **10** of 79 | SEQ 14-B; each run alone, `git status` unchanged, `node --check` clean | **three single arms block six rows** — fix `phi_cache_scoped_to_user.js` arm 5a first; it is a PHI purge arm and it blocks three |
| **4** convention-18 fixes | **PARTIAL — 4 of 8** | coverage ledger §7; `run_removal_path_probe` ablated in place, `preauth_exemption_anchor_probe` now reports `PREAUTH_ORACLES:11` | 4 open with artifacts. And **two ablation attempts COULD NOT RUN** before the one that worked — both recorded |
| **5** census toward the 83 | **PARTIAL — 40 of 83** | handoff-c item 5; the log re-extracted AND cross-checked against its own summary line, which the script refuses to proceed past on a disagreement | 43 unverified. Note 1 exits 0 and 4 exit 2, so 83 is at most 78 + 5 |
| **6** settings merge | **BLOCKED — re-checked once** | cody's claim is RELEASED but the merge has NOT landed: only `PreCompact` in `~/.claude/settings.json`, no commit to `.claude/settings.json` since 2026-10-05 | nothing written. Re-check when the merge lands |
| **7** two corrected measurements | **DONE** | handoff-c item 7, for chat to route | I edited neither hank's nor cc's files and closed neither finding |
| **8** convention 22 | **DONE** | `docs/2026-09-13-cross-domain-disciplines.md` §22 + a METHODOLOGY promotion row | cause-tagged `measurement/window/unbounded-view-presented-as-the-whole` |
| **9** cody's routing path | **DONE** | METHODOLOGY *"Routed here — RE-DERIVED"* section | cc's three are now READABLE and resolved; cody's ITEM 15 has **no `## ITEM 15` section** — a table row naming a section that was never written |
| **10** final handoff + release | **DONE** | the FINAL STATE section of `docs/handoff-fourth-2026-10-07c.md` | claim `fourth` released; `git config core.bare` printed in the report |

# BATCH 15 CHECKPOINT LOG

| item | state | commit / seq | exact next step |
|---|---|---|---|
| **1** Tier A discharges | **DONE — 3** | the three `verdict` fields; one by recorded takeover | cc 173h and cc 168h remain readable and takeover-eligible; the two ABSENT ones are items 7 and the weak-basis decision |
| **2** memory-checkpoint tool | **DONE — answered NO** | nothing built, as instructed | see the report; a decision for chat |
| **10** settings merge | **BLOCKED — re-checked once** | only `PreCompact` in `~/.claude/settings.json`; no commit to `.claude/settings.json` since 2026-10-05 | re-check when cody's merge lands |
| **3** ablation, remaining 4 | **PARTIAL — 7 of 8** | coverage ledger §8; 3 attempts, the first two had a wrong PREDICATE not wrong arms | `run_truthy_sum_probe` outstanding: empty the subject's BASELINE FILE rather than override its exit |
| **4** census toward 83 | **PARTIAL — 40 of 83, unchanged** | coverage ledger §9; log re-extracted and cross-checked against its own summary | 43 unverified; the suites run this batch were already counted or not members |
| **5** the three blocking arms | **DONE** | SEQ 15-A — artifact + owner per arm | **arm 1 is UNOWNED** (`owner: None, basis: NONE`, no claim in history) and is the PHI one. Chat assigns it first |
| **6** orphan re-seat | **PARTIAL — 5 re-seated of 28 mine, 84 total** | SEQ 15-C | 56 are other sessions' files and not mine to edit; 6 purge-evidence SHAs deliberately left |
| **7** the hank command | **DONE** | SEQ 15-B — command, dry-run-first, and 3 checks | check 3 is the one that matters: the subject must be READABLE |
| **8** report gate | **DONE** | `--report-gate` on the existing sweep; fixture FAILED before (flag ignored, exit 0) and exits 1 after, naming the known orphan | run it as the last step before every report |
| **9** `__file__` sweep | **DONE — 424 of 1214** | coverage ledger §10 | not 424 defects — 424 that cannot be ablated or sandboxed from a copy |
| **11** cc's three conventions | **DONE** | the report; none conflicts with the 22 | chat decides adoption |
| **12** method improvement | **DONE** | handoff-c ITEM 12, with the before/after predicate | folded into convention 20 |
| **13** final handoff + release | **DONE** | the FINAL STATE section of `docs/handoff-fourth-2026-10-07c.md` | claim released; report gate run as the last step |

# BATCH 16 CHECKPOINT LOG -- one line per item, appended BEFORE the next item starts

The first attempt at this batch was **stopped mid-compaction**. Two rows had been
written. The numbering below is the RESUME dispatch's 1-15.

**MY FIRST RETRACTION OF ROW 2 WAS ITSELF WRONG, AND IT IS CORRECTED HERE RATHER
THAN QUIETLY EDITED.** I retracted it on two grounds. I checked **my own**
scratchpad, found it empty, and wrote that the cited `abl_i2c.out` *"does not
exist"*. It exists -- in the **stopped session's** scratchpad
(`4975e2e9-8002-4f73-9d9d-240c42c3b643`), which is a different directory from mine
(`7e379670-...`) because a resumed session gets a new one. I looked in the right
SHAPE of place and the wrong place, and reported absence. Same defect class as
everything else in this batch: **a cheap way to check was available and a narrower
view was used instead.**

The second ground was also wrong, and reading the file is what settled it. Row 2's
*"tool exit 1->0, probe 1->0"* is an **accurate record of the lever it actually
pulled**, which was **ADDING the 16 occurrences to the baseline (46 -> 54 keys)**,
not emptying it. `abl_i2.out`, written minutes earlier, records the EMPTYING lever
as **tool 1, probe 1 -- no response**, and says so in its own verdict line:
*"COULD-NOT-RUN -- the lever never engaged"*.

**So the row was TRUE and the LABEL was missing**, and the correction runs in the
useful direction: two sessions independently measured the emptying lever as
non-responsive, and the opposite lever is the one that moves it. Row 3 below
carries all three results.

| item | state | commit / evidence | exact next step |
|---|---|---|---|
| **2** ablation 8 of 8 (stopped session) | **STANDS, with the lever NAMED -- my retraction of it is WITHDRAWN** | `4975e2e9-.../scratchpad/abl_i2c.out` and `abl_i2.out`, both present and readable | the row's "tool 1->0, probe 1->0" is correct **for the lever it used: ADDING the 16 occurrences to the baseline, 46 -> 54 keys**. The EMPTYING lever the dispatch named was measured in the same hour and recorded as `COULD-NOT-RUN -- the lever never engaged`. The row was true; what was missing was WHICH LEVER. See the correction above |
| **1** per-item checkpointing | **DONE** | this table, one row appended before the next item starts | memory directory untouched; no tool built |
| **2** state check | **DONE** | claims list, `git status`, `git log`, handoff read. HEAD was `f4514979`, **0 ahead / 3 behind** origin/main, fast-forwarded to `2156abb1`. Everything in my batch-15 log is PUSHED | nothing of mine is unpushed; the only uncommitted work was 10 census entries in `docs/known-red-suites.json` and the two retracted handoff rows |
| **3** ablation 8 of 8, truthy_sum | **DONE — and the live-repo lever is INCONCLUSIVE, which is the finding** | `<scratchpad>/abl_truthy_sum.out` and `<scratchpad>/abl_truthy_sum_fixture.out` | live tree: tool `1→1→1`, probe `1→1→1`, 32 arms ok / 1 FAIL **unchanged** by emptying the baseline, because the only arm that reads it (arm 11, `run_truthy_sum_probe.py:173`) is **already red from real tree state** and exit 1 before is exit 1 after. Baseline restored, sha256 `9fa29263…` byte-identical, `git status` unchanged. Then the SAME lever on an already-clean fixture, per convention 12: **A present `0` → B EMPTIED `1` → C ABSENT `1`**. Lever engaged, emptied and absent agree. **The 16 unbaselined occurrences in `stonedesk.html` are what make the live arm unmeasurable**; they are routed, not fixed. **AND THE THIRD RESULT, from the stopped session's own evidence read after the fact: the lever that DOES move the live probe is the opposite one.** Adding those 16 to the baseline (46 -> 54 keys -- `key()` is `file::term`, so **16 occurrences are 8 distinct keys**) takes the tool **1 -> 0** and the probe **1 -> 0**, restored byte-identical. So: **emptying does nothing on a dirty tree and everything on a clean fixture; filling does everything on a dirty tree.** The layer's effect is only visible from a clean baseline, in whichever direction you reach it -- convention 12's already-clean-code requirement arriving as a measurement rather than as a rule |
| **4** census, 3 slices | **DONE -- 40 -> 50 of 83** | `<scratchpad>/census_slices.out`, `census_now.out`, `census_after.out`; register restamped at `2156abb1` | ten suites driven **alone**, 300s ceiling, boundary verified **after every one** (`git status` digest, sha256 of `.git/config`, `node --check api/sd-data.js`) -- all three unchanged start to end. All ten exit **1**; all ten AGREE with the rows the stopped session had written, so those rows are now stamped on a run whose output exists. `known_red_check.py --fixtures` **exit 0**. **33 still unverified**, and they are unmeasured-individually, not presumed red |
| **5** phi_cache arm 5a | **DONE -- FIXED, and it was the SUITE, not the app. ONE ARM CLEARED FOUR ROWS** | `1c53498d` (fix), `93ed64c7` (defect record), `5be55ef4` (post-rebase re-seat) -- all three **ON-REF** by `merge-base --is-ancestor` | claim-checked CLEAR, carried under my existing `fourth` claim rather than re-claimed (the tool REFUSES a second overlapping claim from the same session, so a new one would have been a reworded duplicate). Arm 5a expected `[]`, got `["sen_settings"]`. **`sen_settings` is not an unpurged PHI cache**: it is server-authoritative, and `sairnsenior.html:5768-5780` is a comment that exists to stop anyone re-creating the local copy -- and to say that, it has to quote `st('sen_settings')`. Arm 5 ran `[ls][dt]\('(sen_[a-z_]+)'` over the **raw** file, so **the comment explaining the key is never written was counted as the key being written, twice**. Fix is in `tests/phi_cache_scoped_to_user.js`: write sites now come from `tests/lib/strip_comments.js`. **NOT** fixed by adding one word to `SEN_UNSCOPED_CACHES`. Measured: stripping changes exactly one key in one of four apps, so 5b/5c cannot regress. **Arm 5e is the control and it FAILS FIRST** -- ablated, probe `0 -> 1` naming 5e in all four apps and 5a in SAIRNsenior, restored byte-identical `e38eac06`, back to `0`. 63/1 -> **72 passed, 0 failed** |
| **5b** the chained rows | **DONE -- 4 register rows deleted as RECOVERED** | `<scratchpad>/chained.out`; register 79 -> 75 entries, `known_red_check.py --fixtures` **exit 0** | each driven ALONE with the boundary verified after it: `phi_cache_scoped_to_user.js` **1->0**, `phi_cache_scope_probe.py` **2->0** (ALL 12 ARMS PASS, 7 mutations -- it had been planting nothing), `sairncare_fault_probe.py` **1->0**, `sairnbuild_fault_probe.py` **1->0**. Deleted per the register's own rule; diagnoses preserved in `_recovered_2026_10_07_fourth`. **AND THE CENSUS GOES DOWN BECAUSE OF IT: 50 of 83 measured, then 4 verified rows deleted on recovery, so the register-derived recount reads 46 of 83.** The 4 are verified GREEN, not unverified. **FLAGGED NOT TOUCHED:** `tests/run_primitive_obsession_probe.py` still stands as an entry with `exit_code 0` and RECOVERED in its own `why` -- the state that rule forbids |
| **6** sairnfreedom owner correction | **DONE -- routed, not applied** | the ROUTE TO CC block above, in this file | premise re-derived both ways at `5be55ef4`: the map really does say `owner: null, basis: NONE`, and claim `c1e06f33` really does name the file. **And the cause is not staleness** -- `tool_owner_map.py:76` reads only `FILES:` out of the claim subject, and that claim has no `FILES:` list, so a regeneration today reproduces `NONE`. `docs/tool-owner-map.json` **not touched** |
| **7** orphan re-seat | **DONE -- FINISHED, and the remaining re-seatable set is EMPTY.** Not 28-minus-5: **zero** | `<scratchpad>/orphans.py`, `<scratchpad>/orphans.out` (read-only, writes nothing) | re-derived at `5be55ef4` with the predicate WRITTEN DOWN, which is why it disagrees with the 84/28/56: a citation is a **40-char or 12-char** lowercase-hex token, word-bounded, in a tracked `.md`/`.json`; 7-11 char abbreviations are excluded because `9fa29263` is a sha256 prefix and `1234abcd` was a test string. **93 orphaned citations, 18 in my documents, 75 in other sessions'.** ORPHANED cannot contain a false positive -- a non-SHA resolves to no object. **ALL 18 OF MINE ARE QUOTATIONS OF AN ORPHAN, NOT CITATIONS TO FOLLOW**, so re-seating any of them would falsify the document: 8 in `docs/2026-10-07-fourth-routed.md` ARE the seven orphaned Tier A ledger SHAs that document reports plus the short form inside the quoted `** STALE ** moved since 00030f2d11b7` verdict; 6 in `docs/purge-evidence/2026-09-30-SAIRN-fourth.json`, **left untouched as instructed**; 4 are `00030f2d11b7` in the handoff, the conventions file, `SAIRN-ACTIVE-WORK-fourth.md` and the postmortem -- **the dead SHA convention 19 is ABOUT**. A 19th, also `00030f2d11b7`, is in `docs/METHODOLOGY.md:66` in convention 19's own row, same reason |
| **8** `__file__` sweep | **MEASURED -- and the 424 is NOT REPRODUCIBLE, which is the finding** | `<scratchpad>/filesweep.out` | the script population itself moved **1214 -> 1227**. Re-derived with a STATED predicate: `none` 172, **`derives-repo-from-__file__-with-no-git-anchor` 974**, `uses-but-does-not-derive` 3, `derives-and-anchored` 78, sum 1227. **974, not 424** -- and the ledger records the four BUCKET NAMES but never the predicate, so the 424 can be neither confirmed nor denied. Then the half that had never been done: **three slices of five, each script copied ALONE into a scratch directory and run there, deterministic evenly-spaced selection.** 13 of 15 could NOT run from a copy (exit 1 or 2) and **2 DID -- `tools/response_shape_check.py` and `tools/write_without_readback_check.py` both exit 0** -- so the static claim is wrong for 2 of 15 and the method constraint derived from it is a generalisation with a measured exception rate, not a rule |

| **9** settings merge | **STILL BLOCKED ON CODY -- re-checked ONCE, as instructed, and not attempted** | re-checked **2026-10-07T19:30:51Z**; blocker recorded here | `~/.claude/settings.json` carries hooks `['PreCompact']` only; the repo's `.claude/settings.json` carries `['PostToolUse','PreToolUse','PreCompact','SessionStart','UserPromptSubmit']`, so the merge has **not** landed. Last commit to `.claude/settings.json` is `3cf3d5ec`, **2026-10-05 19:02:00 -0400** -- unmoved. cody's claim at **2026-10-07T16:03:49Z** declares `.claude/settings.json` and is LIVE, so this is blocked on cody by a live claim, not by a released one as batch 15 recorded. **Nothing written to either file.** Re-check when cody's merge lands |

| **10** cc's three as conventions 23-25 | **DONE -- LANDED, CREDITED TO CC** | `docs/2026-09-13-cross-domain-disciplines.md`; `## <n>.` heading count **22 -> 25**, counted rather than trusted, before and after | **23** a brief is a snapshot: re-derive each premise and record the result PER premise, with four verdicts kept apart (CONFIRMED / STALE / WRONG / NOT-REPRODUCIBLE). **24** a leg that returns success on a failed leg is a silent skip and must fail loud. **25** at three false-positive CLASSES from one checker, stop patching and review the design. Each section says **DERIVED BY CC** in its first line and carries cc's own instance first, with fourth's second and labelled as such; cc's `defect_register --reseat` measurement is attributed to cc and marked **NOT re-run by me**. **The membership question was asked of all three** rather than assumed: **24 IS A TENTH MEMBER** of the cannot-fire group (item 8 one layer out -- it never turns a passing subject red, only a failing one green), 23 and 25 are NOT, with reasons. Group heading, its denominator note and the body sentence all moved **nine -> ten** and **twenty-two -> twenty-five** rather than left to drift |
| **11** rule log, my two wrong measurements | **DONE** | the RULE LOG section below, in this file | both re-driven at `5be55ef4` with the exit code read on its own line, not through a pipe |
| **12** report gate + SHA sweep | **RUN AFTER THIS FILE, BY DESIGN** | `<scratchpad>/report_gate.out` | the dispatch puts the handoff **before** the report and the gate as the **last step before sending** the report, so this row is the only one in the table whose evidence post-dates it. The gate is `--report-gate <path> --known-orphan <sha>` on the batch-14 sweep, carried into this session's scratchpad from `4975e2e9-.../sweep_full.py` and **not rewritten**; it is read-only by construction and `chdir`s to the clone, so it runs from anywhere. Its selftest arm exits **2** if the named known orphan is not even extracted, so a clean pass cannot be a gate nobody watched fail |
| **13** methodology entry | **DONE -- and the claim was taken and released around the write alone** | `6cc8f251`; `docs/METHODOLOGY.md` | claim sequence, all four commits on `origin/main`: release `fourth` (batch claim) -> claim `fourth` **FILES: docs/METHODOLOGY.md** only -> write -> commit -> push -> release. `sairn_claim.py` **REFUSES a second overlapping claim from the same session**, so a dedicated claim on a shared file is only reachable by releasing first, and that is stated in the claim text rather than worked around. **THE ENTRY: a progress metric whose numerator is counted out of a mutable register moves BACKWARD on success** -- this batch took the census 40 -> 50 of 83, then one arm fix cleared four suites, the register's own rule required deleting those four rows, and the census read **46 of 83 ten minutes after it read 50**. The four that left are the only four in the population that are **verified GREEN** rather than verified red. Routed, **not self-promoted** -- convention 11 |
| **14** correction owed and paid | **DONE** | `09e0461b` | convention 23's own cited instance and the METHODOLOGY promotion row for 23 both called a stopped session's record WRONG. Reading that session's evidence showed it **TRUE with its lever unnamed**. Corrected in both files, left **visible** under the table rather than edited out, and it adds a fifth verdict to 23's four: **WRONG-BY-MY-OWN-CHECK** |
| **15** final handoff | **DONE** | the FINAL STATE section below | written at a point where nothing is half-finished: `ahead 0 / behind 0`, every commit ON-REF by `merge-base --is-ancestor`, no long-running job open |

---

# ROUTE TO CC: ONE OWNER-MAP CORRECTION, WITH ITS MECHANISM

`docs/tool-owner-map.json` is **not edited by me**. It is a GENERATED file
(`python tools/tool_owner_map.py`) and its owner is cc by the batch-14 claim; cc's
batch-15 claim says that claim was released and the file is now declared by nobody.
Either way the fix is one regeneration plus one decision, and it is cc's to make.

| field | value |
|---|---|
| **file** | `tests/sairnfreedom_server_backup.js` |
| **owner map says** | `{"owner": null, "basis": "NONE", "also_claimed_by": [], }` -- and `NONE` in that file's own `_basis_vocabulary` means **UNKNOWN, not unowned** |
| **real owner** | **cody** |
| **basis** | `LAST_CLAIM` |
| **claim id** | `c1e06f332925120a213927449843b1289cdd13db` (`c1e06f33`) |
| **claim subject, verbatim** | `chore(claims): cody claims cody -- negative control for tests/sairnfreedom_server_backup.js -- sf_ledger sf_disbursements tier A` |
| **what it blocks** | itself (exit 1, `FAIL - the registry still holds exactly 35 resources`, 16 passed 1 failed) and `tests/sairnfreedom_fault_probe.py` (exit 1), which stops on *"the shipped tree PASSES ... 16 passed, 1 failed"* |

**THE MECHANISM, WHICH IS THE PART WORTH ROUTING.** This is not a stale
regeneration -- regenerating today would produce `NONE` again.
`tools/tool_owner_map.py:76` derives ownership from `FILES:\s*(.*)$` in the claim
commit **subject**. Claim `c1e06f33` names the file **in prose** and carries **no
`FILES:` list at all**, so the generator sees no file and writes `NONE`. Every
claim that names its subject in prose rather than in a `FILES:` list is invisible
to that map, and the map reports the result as UNKNOWN rather than as
NOT-DERIVABLE-FROM-THIS-SOURCE.

**Two options, and the choice is cc's:** an `OWNER_LINE` in the file itself (the
map's own vocabulary calls that *authoritative*), or widen the generator to also
read file paths out of claim-subject prose -- which is a looser match and will
want its own both-directions control before it is trusted.

**This is the SECOND instance of this gap**, the first routed in SEQ 13-E, so the
shape is recurring rather than a one-off.

---


---

# RULE LOG -- TWO MEASUREMENTS I GOT WRONG, each with its before and after

Both were mine. Both were re-driven at `5be55ef4` with the exit code read on its
own line rather than through a pipe, which is itself convention 24.

## 1. A bare `citation_line_drift_check.py` exiting 2 is a MISSING ARGUMENT, not a regression

| | |
|---|---|
| **BEFORE -- what I measured and reported** | `python tools/citation_line_drift_check.py` → **exit 2**, read and reported as the tool being in a COULD-NOT-RUN state, i.e. as a regression in the tool |
| **AFTER -- what it actually is** | exit 2 is the tool's **own argument refusal**, printed in its own words: *"--app and --prefix are both required. Neither is guessed from the other: an app file and a resource prefix do not follow one rule, and a guess would measure the wrong file."* |
| **the measurement that settles it** | `--app sairnsenior` alone → **still exit 2** (BOTH are required, which is the part I had not established). `--app sairnsenior.html --prefix sen_` → **exit 1** with a real result: ANCHORED **9**, SOUND **0**, DRIFTED **7**, INCONCLUSIVE **2** |
| **what was wrong with the method, not the tool** | I read a 2 as a STATE of the tool when it was a verdict on MY INVOCATION. The tool was behaving exactly as designed, and its design is the thing this platform asks for -- a third state for could-not-run, refusing rather than guessing |
| **the rule** | **An exit 2 from a tool that takes required arguments is a claim about the command line until the command line is shown to be complete.** Before reporting a tool as broken, run it with every required argument and read the refusal text it printed; the refusal usually names the missing argument. This is the inverse direction of PR 1.11 -- that rule stops a missing dependency being read as a pass; this one stops a refusal being read as a failure |

## 2. An ablation scored by PRINTED TEXT instead of by the exit code

| | |
|---|---|
| **BEFORE -- what was recorded** | the stopped session's batch-16 row: *"ablation 8 of 8 **DONE** -- lever engaged (tool exit 1→0), arm responded (probe 1→0)"*, citing `<scratchpad>/abl_i2c.out` |
| **why it was wrong, twice over** | (a) the evidence file was in that session's scratchpad and **does not exist**, so the claim could not be checked by anybody including me; (b) the direction it recorded is **contradicted by re-measurement** |
| **AFTER -- scored by exit code alone, each read on its own line** | live tree: tool **1 → 1 → 1**, probe **1 → 1 → 1**, probe arms **32 ok / 1 FAIL unchanged** by emptying the baseline. The lever does not move the probe's exit code at all, because the only arm that reads the repo baseline (arm 11, `run_truthy_sum_probe.py:173`) is **already red from real tree state**, and exit 1 before is exit 1 after |
| **and the lever DOES work where it can be seen** | same lever on an already-clean fixture, per convention 12: baseline present **0** → baseline EMPTIED **1** → baseline ABSENT **1**. Emptied and absent agree |
| **what was wrong with the method** | printed text is produced by the arm that is still running; an exit code is produced by the whole program. Reading the text let a plausible narrative stand in for a measurement, and the narrative was in the right shape and the wrong direction |
| **the rule** | **An ablation's verdict is the subject's exit code before, during and after, printed as three numbers on one line, and the restored state is proved by hash and not by the absence of a complaint.** If the exit code cannot move -- because the arm that reads the ablated layer is already red -- the honest verdict is INCONCLUSIVE, and the ablation moves to a clean fixture rather than being written up from the text |

**What the two share, and it is the reason they are logged together:** in both
cases a number was available and I used a sentence instead. The first read a
refusal as a state; the second read a narrative as a result.


---

# FINAL STATE -- batch 16, written before the report

## COMMITTED AND PUSHED

| | |
|---|---|
| branch | `main` |
| HEAD | **`09e0461b`** |
| pushed | **yes -- `ahead 0 / behind 0`** of `origin/main` at the time of writing |
| working tree | clean except **one pre-existing untracked file**, `sql/restore_demo_pins_2026-09-29.sql`, which was there at session open and is not mine |
| `git config core.bare` | **empty -- unset.** `git status` answers normally |
| `git stash` | **one entry held: `stash@{0}: autostash`.** Pre-existing, carried from batch 15, not created by this batch |
| long-running jobs | **none.** No whole-tree run and no `--pinned` run was started; every suite was driven individually with a 300s ceiling |
| boundary discipline | `git status` digest, sha256 of `.git/config` and `node --check api/sd-data.js` captured **after every suite and every ablation**, not once at the end. Start digest == end digest throughout |

**Commits this batch, each verified ON-REF with
`git merge-base --is-ancestor <sha> origin/main` -- not with an existence test,
which is convention 19:**

| commit | what |
|---|---|
| `1c53498d` | the phi-cache fix: write sites from `strip_comments.js`, arm 5e as the control |
| `93ed64c7` | the defect record the push gate required (layer `test`, severity `high`, rule PR 1.2) |
| `5be55ef4` | the post-rebase hook's own re-seat of that record's commit citation |
| `a7ca2d08` | cc's conventions **23, 24, 25**, credited to cc; 24 recorded as a TENTH member |
| `6cc8f251` | METHODOLOGY: three promotion rows + one routed entry from this batch |
| `0fe8dedb` | **my retraction withdrawn** -- the evidence existed and the record was true |
| `09e0461b` | convention 23 corrects its own cited instance |

Plus four `chore(claims)` commits: the batch claim released, the METHODOLOGY-only
claim taken and released, and the close-out claim taken and re-taken wider.

## FINAL FIGURES, re-derived at this HEAD

| | |
|---|---|
| register rows | **75** (79 - 4 deleted as RECOVERED) |
| the 83, individually verified | **50 of 83 measured this batch**; **46 of 83** when recounted off the register after the four recoveries. Both numbers are real and they mean different things -- see item 13 |
| ablation | **8 of 8 -- and the eighth has three results, not one** |
| orphans, whole corpus | **93** citations -- 18 mine, 75 other sessions'. **0 of mine remain re-seatable** |
| `__file__` population | **974 of 1227** under a stated predicate. The old **424 of 1214** is NOT REPRODUCIBLE -- its predicate was never recorded |
| scripts driven from a copy | **15**, three slices of five: **13 could not run, 2 could** |
| conventions | **25** -- counted from `## <n>.` headings before and after, never quoted |
| conventions I landed this batch | **3, all CREDITED TO CC** |
| defect records | 483, `--check` **exit 0** |

## THE 75 OTHER-SESSION ORPHANS -- one line each: file, owner, count

Not mine to edit. Owner is taken from the filename where the filename names a
session, and **UNASSIGNED is written where it does not** rather than guessed.

| count | file | owner |
|---|---|---|
| 35 | `docs/2026-09-29-stale-branch-tips.md` | **UNASSIGNED** -- a document *about* stale tips, so most of these may be intentional data |
| 8 | `docs/defect-density-register.json` | **UNASSIGNED** -- written only through `tools/defect_register.py`, which is cc's |
| 7 | `docs/purge-evidence/2026-09-30-SAIRN-cc.json` | **cc** -- append-only purge evidence; re-seating would falsify it, same as mine |
| 7 | `docs/tier-a-reviews.json` | **UNASSIGNED** by filename; **cc** by the live claim at 2026-10-07T17:24:00Z. These are the seven I routed in SEQ 15-C |
| 4 | `docs/scrutiny-flags.json` | **cc** -- push-gate bookkeeping |
| 3 | `docs/handoff-cody-2026-10-07.md` | **cody** |
| 2 | `docs/purge-evidence/2026-09-30-SAIRN-hank.json` | **hank** -- append-only, same caveat |
| 1 | `docs/handoff-cc-2026-10-06c.md` | **UNASSIGNED** by my matcher, **cc** by content |
| 1 | `docs/2026-10-06-cc-batch-10-inventory.md` | **UNASSIGNED** by my matcher, **cc** by content |
| 1 | `docs/2026-10-05-cc-batch-5-inventory.md` | **UNASSIGNED** by my matcher, **cc** by content |
| 1 | `SAIRN-ACTIVE-WORK-cc.md` | **cc** -- append-only log, never rewritten |
| 1 | `docs/METHODOLOGY.md` | **fourth + hank**, shared. It is `00030f2d11b7` in convention 19's own row -- the dead SHA that convention is ABOUT, so deliberate |
| 1 | `docs/2026-10-06-cody-queue18-items-10-12-13.md` | **cody** |
| 1 | `docs/handoff-cody-2026-10-06b.md` | **cody** |
| 1 | `docs/2026-10-07-cody-batch20.md` | **cody** |
| 1 | `docs/2026-10-07-cody-harness-exit-mismatches.md` | **cody** |

**My matcher's own limitation, stated rather than left to be found:** three `cc`
files above came back **UNASSIGNED** because my owner rule keys on `-cc.` /
`SAIRN-ACTIVE-WORK-cc` and those filenames spell it `-cc-batch-` and
`handoff-cc-`. The counts are right; the owner column under-attributes by three
rows and I am saying so instead of hand-editing it into looking complete.

## WHAT IS OPEN, AND WHY

| open | why |
|---|---|
| **16 unbaselined `+ (x \|\| 0)` occurrences in `stonedesk.html`** | **8 distinct `file::term` keys.** They are what make `run_truthy_sum_probe` arm 11 red and the live ablation lever unmeasurable. Each needs a per-site judgement -- baseline with a stated reason if the field is provably numeric, otherwise wrap in `Number()`. **Per-site, not a sweep**, and not mine to decide unilaterally |
| **37 of the 83 unverified** | unmeasured individually, **not presumed red** |
| **`tests/run_primitive_obsession_probe.py` still stands as a register entry** with `exit_code 0` and RECOVERED in its own `why` | the state the register's own rule forbids: while it stands it swallows the next real failure of that file. **Flagged, not deleted** -- reported for a decision rather than acted on unasked |
| **the owner-map gap** | `tool_owner_map.py:76` derives ownership only from `FILES:` in a claim subject. Claim `c1e06f33` names its file in PROSE, so a regeneration **today** reproduces `owner: null, basis: NONE`. Routed to cc in the block below; **`docs/tool-owner-map.json` not touched** |
| **the settings merge** | **BLOCKED ON CODY.** Re-checked once at `2026-10-07T19:30:51Z`: `~/.claude/settings.json` carries hooks `['PreCompact']` only, the repo's carries five, last commit to `.claude/settings.json` is `3cf3d5ec` on **2026-10-05 19:02:00 -0400**, unmoved. cody's live claim at `2026-10-07T16:03:49Z` declares the file. **Nothing written to either** |
| **the 424's predicate** | unrecorded, so the figure can be neither confirmed nor denied. **974 of 1227** is the re-derivation with its predicate written down, and the two are not comparable |
| **2 of 15 scripts DID run from a copy** | `tools/response_shape_check.py` and `tools/write_without_readback_check.py` both exit 0 from a scratch directory, so the platform-wide method constraint is a generalisation with a **measured exception rate**, not a rule. The other 959 are unmeasured |
| **the 6 purge-evidence SHAs in `docs/purge-evidence/2026-09-30-SAIRN-fourth.json`** | **left untouched as instructed.** Append-only evidence of what was purged; rewriting it would falsify the evidence rather than fix a citation |
| **the fifth verdict for convention 23** | **WRONG-BY-MY-OWN-CHECK** is written into section 23's correction note but is **not** in its four-verdict list, because adding a verdict to a convention one hour after chat adopted it is a change to what was adopted. Chat's call |

## EXACT NEXT STEP, PER OPEN ITEM

1. **The 16 `stonedesk.html` sites** -- 8 keys, one judgement each. That is the
   only thing standing between `run_truthy_sum_probe` and a measurable live
   ablation, and it unblocks arm 11 for every future batch, not just this lever.
2. **`run_primitive_obsession_probe.py`'s register row** -- decide: delete it (the
   register's own rule) or amend the rule to carry RECOVERED as a third state.
   **The methodology entry from this batch argues for the second**, and both are
   one edit.
3. **The owner-map gap** -- cc chooses: an `OWNER_LINE` in
   `tests/sairnfreedom_server_backup.js` (the map's own vocabulary calls that
   authoritative) or widen `tool_owner_map.py` to read paths out of claim-subject
   prose, with a both-directions control before it is trusted.
4. **The census** -- 37 to go. Re-extract the 83 from `pinned2_stdout.txt` every
   time and let the script refuse on a disagreement with the log's own summary
   line; never quote the 83 from a document.
5. **The `__file__` population** -- either record the 424's predicate so it
   becomes checkable, or retire the figure and adopt a stated one. 959 scripts
   remain unmeasured empirically.
6. **The settings merge** -- re-check when cody's lands. Do not attempt it.
7. **Run the report gate as the last step before any report.** It is carried in
   `<scratchpad>/sweep_full.py`, read-only, with a selftest arm that exits 2 if
   the known orphan is not extracted.

## CLAIMS HELD AT THE TIME OF WRITING

**`fourth` is HELD**, as the batch-16 close-out claim, declaring
`docs/2026-09-13-cross-domain-disciplines.md`, `docs/METHODOLOGY.md`,
`docs/handoff-fourth-2026-10-07.md` and `SAIRN-ACTIVE-WORK-fourth.md`. **It is
released at the very end of the batch, after the report gate.**

Three other sessions were live throughout: **cody** (`Tooling`, batch 24),
**hank** (`platform`, batch 13) and **hover2** (audit batch N). Each was
re-derived from `sairn_claim.py list` rather than from a sibling's claim text,
which is convention 23.

**NOT TOUCHED, and each one checked rather than assumed:**
`.claude/settings.json` (**cody**, live claim `2026-10-07T16:03:49Z`);
`docs/tool-owner-map.json` and `tools/doc_sha_reseat.py` (**cc**);
`docs/purge-evidence/2026-09-30-SAIRN-fourth.json` (instructed);
`docs/tier-a-reviews.json` (**cc**, live claim `2026-10-07T17:24:00Z` -- no Tier A
discharge was taken this batch and none was in the dispatch);
and nothing anywhere under `.claude/skills/sairn-hover-auditor/`.

**I closed only findings I originated, and reclassified none.**

## THIS SESSION'S TRANSCRIPT

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\7e379670-c1b8-4e19-9aa2-b1affe2f960e\scratchpad

In item order: `abl_truthy_sum.py` / `.out` and `abl_truthy_sum_fixture.py` /
`.out` (item 3 -- the live lever measured non-responsive, then the same lever on a
clean fixture); `census.py`, `census_now.out`, `census_after.out`,
`census_final.out` (the census, re-extracted from the pinned log every time);
`census_slices.py` / `.out` and `census_slices.json` (the ten suites driven alone
with the boundary verified after each); `chained.py` / `.out` (the four rows one
arm cleared); `phi_cache_fixed.js` (the restore copy the ablation used **instead of
`git checkout`**, after `git checkout` silently discarded the uncommitted fix the
first time -- that mistake and its fix are both in this directory);
`orphans.py` / `.out` (the orphan census, read-only); `filesweep.py` / `.out` (the
`__file__` re-derivation and the three measured slices); `conv.py`, `meth.py`,
`hf2.py`, `fixretract.py`, `fixretract2.py`, `corr23.py` (the document edits, each
asserting its anchor matched exactly once before writing); `sweep_full.py` (carried
from the batch-14 session, unmodified) and `report_gate.out`.

**And the batch-14/15 session's scratchpad, which this batch had to read and which
is a different directory -- the mistake that produced the withdrawn retraction:**

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\4975e2e9-8002-4f73-9d9d-240c42c3b643\scratchpad

`abl_i2.out` (the EMPTYING lever: *"COULD-NOT-RUN -- the lever never engaged"*) and
`abl_i2c.out` (the FILLING lever: tool `1 -> 0`, probe `1 -> 0`, restored
byte-identical).


---

# ITEM 12 RESULT -- the report gate, run as the last step, and it REFUSED FIRST

Appended after the report was written, which is the one place in this file where
the evidence post-dates its row, and the row above says so.

**FIVE RUNS. The gate refused twice and the REPORT was changed both times, never
the gate.**

| run | subject | exit | what |
|---|---|---|---|
| 1 | a FIXTURE COPY of the report with a known orphan pasted in | **1** | **the selftest.** `gate selftest : the known orphan ... was caught as ORPHANED`. 20 citations, 14 ON-REF, 6 not. A gate that only ever sees clean input is a gate nobody has watched fail -- convention 20 |
| 2 | the report body | **1** | **5 flagged.** One genuinely ORPHANED commit I was quoting as data, and **four that are not commits at all** -- two sha256 prefixes, a session-uuid fragment and a literal 8-character test string |
| 3 | the body, four rewritten | **1** | one left: the dead sha convention 19 is about, still written out |
| 4 | the body, that one cited by subject | **0** | 14 citations, **14 ON-REF**, 0 not |
| 5 | **`G:\My Drive\SAIRN-status\SAIRN-report-ted-b1.txt`, after a fresh `git fetch`** | **0** | the delivered file. 14 extracted, 14 ON-REF |

**The fix was the report, following the gate's own refusal text** -- *"Cite it by
SUBJECT, or cite the sha only after the final push."* A full 64-character sha256
is over the extractor's 40-char ceiling and a full uuid is rejected by shape, so
the two hashes that mattered are written in full rather than abbreviated into
something that looks like a commit.

**AND THE GATE'S FOUR FALSE POSITIVES ARE CONVENTION 25 ARRIVING ON THE DAY IT
LANDED.** `[0-9a-fA-F]{8,40}` cannot tell a short commit from a sha256 prefix,
from a uuid fragment, or from a test string -- **three distinct false-positive
classes from one predicate, which is 25's exact trigger.** The gate lives in the
batch-14 session's scratchpad and I carried it here **unmodified**: it is
report-only, it was right to refuse, and narrowing its pattern today would be the
fourth patch rather than the design review 25 asks for. **Recorded as the
finding, not fixed**, and it is the first independent instance of a convention
this batch landed an hour earlier.

## SHA SWEEP ON THE FINAL REPORT

`<scratchpad>/finalize.out`. The sha256 covers every byte before the `SHA256:`
line, LF endings, UTF-8, `hashlib`:

    bytes on disk      25030
    CR bytes present   0
    lines              443
    first line         'REPORT ted b1'
    second-to-last     'SHA256: 2f4cf99b055e15a2929cef0fa61d3ab815969e98a098e24b1379b2d5e4ed12c3'
    last line          'END-OF-REPORT'
    MATCH              True

**Recomputed FROM THE FILE ON DISK after writing, not from the buffer that was
written** -- a hash verified against its own source proves the hash function
works and nothing about the file. **Plus a negative control: one byte changed
still matches == False.** Without that arm the match is a tautology, which is
convention 20 applied to a hash.
