# Handoff — fourth (Ted), batch b3, 2026-10-08

New file because the date rolled over; batches 12–17 are in
`docs/handoff-fourth-2026-10-07.md`, which this one continues from rather than
replaces.

---

# BATCH b3 CHECKPOINT LOG — one row appended BEFORE the next item starts

Mirrored into the memory directory after every item as well, at
`~/.claude/projects/C--Users-marsh-Documents-SAIRN-fourth/memory/batch-b3-progress.md`,
so a stop mid-batch loses nothing.

| item | state | evidence | exact next step |
|---|---|---|---|
| **1** state check + Tier A | **DONE — and the Tier A discharge is BLOCKED, not skipped** | `<scratchpad>/b3_claims.txt`, `b3_tiera.txt` | HEAD `398328fc`, **`ahead 0 / behind 0`**, working tree clean except the pre-existing untracked `sql/restore_demo_pins_2026-09-29.sql` (four batches running, not mine). **MY CLAIMS ARE RELEASED** — `sairn_claim.py list` shows no `fourth` row at all; the two active claims are **cody** (batch25-b2, 0.6h) and **cc** (batch17-b3, 1.4h). `tier_a_review_gate.py check --list` → **exit 1, 22 open obligations**, of which **3 are ASSIGNED TO ME**: hank `2026-09-27T03:42:29Z` **261h** (COULD-NOT-TELL, recorded sha `54e4835ac96e` does not resolve in this clone), cody `2026-09-28T03:34:57Z` **237h** (COULD-NOT-TELL, `f88105a88287` does not resolve), hover2 `2026-09-30T13:59:56Z` **179h** — the only one of the three with **no freshness complaint**, so the only one I could actually have reviewed. **I DID NOT DISCHARGE, AND THE REASON IS A LIVE CLAIM:** `--discharge` writes `docs/tier-a-reviews.json`, and that file is declared in **cc's live claim FILES**. Flagged back rather than proceeding with a disclosure |
| **2** settings merge | **DONE AND LANDED — claimed, applied, proved, claim released** | `<scratchpad>/b3_i2_dryrun2.out` (plan + full 175-line diff), `b3_i2_apply.out`, `b3_i2_test_before.out`, `b3_i2_test_after.out`, `b3_settings_BEFORE.json` | claimed `.claude/settings.json` FIRST (CLEAR — cody's and cc's live FILES lists both read in full, neither names it), **released immediately after**. `claude --version` → **2.1.222**, which is **older** than 2.1.288, so **branch (c)**: `env CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=75` and **`autoCompactWindow` deliberately NOT set** — the test asserts its absence so the wrong branch cannot pass. Plus **(d)** `env BASH_MAX_OUTPUT_LENGTH=10000`. **21 hooks added**, all five repo hook types now present. **PreCompact is NOT duplicated, and the dedupe is measured rather than assumed:** `difflib.SequenceMatcher` over the two commands reports exactly ONE non-equal opcode, an INSERT of the 24 characters `, Documents/SAIRN-fourth` at offset 640, so the repo's command contains **every character** of the global's — the global entry is superseded by its own strict superset, which keeps the hook and ends a double-fire. If that proof ever fails the script REFUSES to supersede and keeps both, which is loud rather than silent. **THE TEST RUNS IN BOTH DIRECTIONS:** against the pre-merge bytes it **FAILS 6 of 14 arms** (exit 1), against the merged file it **PASSES all 14** (exit 0). Arms 6a–6c and 7a–7b exist because the file is shared by all six agents: no top-level key removed, none added beyond the branch's own, every other key **byte-identical**, no env var removed or changed. Pre-write bytes saved to the scratchpad **before** anything was written, so a restore is from captured bytes and never from `git checkout` |
| **3** SEQ 17-B, the left-operand case | **DONE — fixed, controlled in both directions, three baseline entries removed** | `<scratchpad>/b3_i3_tool_prebaseline.out`, `b3_i3_tool_after.out`, `b3_i3_probe_after.out`, `b3_i3_ablate.out`; `truthy_sum_check.PREFIX.py` / `.FIXED.py` | `occurrences()` now reads the **next significant character after the closing `)`** and excludes the term when it is `*`, `/` or `%` — the value added is then a product, which is numeric whatever the field holds. **The exclusion is COUNTED AND PRINTED on every run, never silent** (`left operand of a * / or %, so numeric, not counted : 6`) and `--full` names each, because the tool's own docstring says a silent exclusion reads as coverage. The raw match floor now adds the new bucket so the probe's `>= 100` arm does not quietly measure less. **`-` is deliberately NOT in the set** and arm 14f asserts it is still reported: over-reporting is this tool's stated safe direction and widening past the measured instance is how a classifier earns its next false negative. **THE CONTROL IS A PAIR, AND THE LEFT HALF FAILS WITHOUT THE FIX** — which is the whole lesson, because section 2 only ever tested the side that already worked. Ablated with the pre-fix tool restored from **captured bytes, not `git checkout`**: probe **`0 → 1 → 0`**, arms **`40 → 36 → 40`**, and the arms that fire without the fix are **14a, 14e(`/`), 14e(`%`)** plus arm 11 going red because the baseline entries are gone. Restore **byte-identical** `7f2b6f36`. Baseline **50 → 47**: the three entries that said *"Remove this entry when the checker handles the left operand"* are gone, `u.cost` deliberately KEPT because it is not a multiplicative case. Tool **exit 0 CLEAN**, probe **exit 0, 40 arms**. **A SIXTH occurrence I had not known about surfaced in the new bucket** — `tests/sv_boarding_revenue_coercion.js:144 b.rate`, whose baseline entry is a deliberate negative control and stays live because the same key still has a non-multiplicative occurrence; the stale-key count went `5 → 2` and the 2 remaining (`x.lab`, `x.oth`) are pre-existing and not mine |
| **4** SEQ 17-A, the four named sites | **DONE — 3 fixed, 1 WITHDRAWN as not a defect, and the sweep's own measurement fault is corrected** | `<scratchpad>/b3_i4_subjects.out`, `b3_orphan_before.out` / `after.out` / `after2.out` / `final.out` / `selftest.out`, `b3_vet_control3.out`, `b3_dsl_after.out`, `b3_cld_sen_after.out`, `b3_cld_probe_H2.out`, `b3_i4_ledger.out`; routed in `docs/2026-10-07-fourth-routed.md` **SEQ 17-A: CORRECTED** | **TAKING THEM EXPOSED HOW THE 47 WERE MEASURED.** Batch 17 ran each pattern against the app file its containing file reads — a DEFAULT, not a measurement. Re-measured against the subject read out of the source: **`tools/stale_row_sweep.py:240` is NOT a PR 1.2 site at all** (its subject is `cells`, a markdown row of the open-work index; `row_symbols(cells)` is the only caller and no app file reaches it) — the *29 → 0, 100% phantom* headline is **WITHDRAWN**. **`tests/sairnvet_seed_never_syncs.js:98`** real shape but **LATENT** (39 pairs raw, 39 stripped, 0 phantom). **`tests/demo_seed_licence_scope.js:216`** same — **33 / 33 / 0**. **`tools/orphan_register_check.py:163` is ACTIVE and in a different syntax than routed**: its subject is `sql/*.sql`, so the hazard is a SQL `--` comment, and **91 names raw → 70 stripped, 21 exist only inside a comment**. **AND IT HAD A SECOND ACTIVE CASE THE SWEEP NEVER SAW** — `writers()`/`key_present()` read the raw app, and `sd_comms` has **2 writers raw, 1 stripped**. **Two of that file's three predicates SUPPRESS a finding**, which is the direction nobody notices. Fixed so `parse_register` **still reads raw** (the `@REGISTER` entries live in comments) and only the code predicates read stripped; `citation_line_drift_check.py` likewise, with `cited line reads:` kept RAW on purpose. **`sen_settings` is now INCONCLUSIVE instead of DRIFTED-onto-a-comment: `sen_` goes ANCHORED 9→7, DRIFTED 7→5, INCONCLUSIVE 2→6**, which is the verdict that comment block itself predicted. **22 control arms, every set with an ANTI-VACUITY arm**, and two of them earned it: `4b`/`4c` FAILED on their first run because `strip_comments` treats `//` as a comment only inside `<script>` and the fixtures were bare JS — a bare `.js` is stripped **silently, not at all**. **MY OWN 48th INSTANCE FIXED AND MEASURED: exactly one script changes bucket** — `tests/run_defect_register_vocab_sabotage_probe.py` was `derives_with_anchor` on a comment match — so the ledger figure is **979 of 1232**, not 978, and §11 now carries both columns. **A WRONG DEFAULT COST ME THREE TIMES IN ONE ITEM**: the sweep's subject default, `blank_string_bodies` carried over from another tool (CLEAN → 8 false findings), and the bare-JS stripper no-op, twice |
| **5** three reconciliations | **DONE — and premise (a) does NOT hold** | `<scratchpad>/b3_i5a.out`, `b3_i5b_final.out`, `b3_i5c.out`, `b3_census_i5.out`; routed as **SEQ b3-A** | **(a) THE TABLE IS ARITHMETICALLY CORRECT; THE READING OF IT WAS NOT.** All 16 published cells MATCH the tool's own summary lines, and every column sums: `11+9+3+24=47`, `6+0+1+4=11`, `9+7+1+7=24`, `3+2+20+0=25`. The challenged equalities compare **ANCHORED against the sum of the other three as if it were a row total** — it is a PEER VERDICT, one of four mutually exclusive outcomes per citation. Evaluated as asked: `alf_` 11 vs 18, `dnt_` 3 vs 22, `bld_` 24 vs 11, all-four 47 vs 60, **none equal and none should be** — and **`sen_` 9 vs 9 IS equal by coincidence**, which is how such a reading survives. **BUT THE TABLE INVITED IT, so that is fixed:** republished with an explicit **ROW SUM** column. **The per-row sum that DOES have to hold was checked too and holds** (29/29, 18/18, 25/25, 35/35) — **and my first row-counter was wrong by exactly 4 per app** because `^  ANCHORED\s+\S` also matched the summary line; corrected, with the tell recorded. **The table was also STALE:** item 4 moved it — ANCHORED **47→45**, DRIFTED **24→22**, INCONCLUSIVE **25→29**, total **107→107**, all of it `sen_settings` ceasing to resolve onto a comment. **(b) THE UNITS DIFFER AND THE GAP DECOMPOSES EXACTLY: `entries` 76 − 5 rows not in the 83 − 20 rows in the 83 with no sha-stamped run = 51 VERIFIED RED, identity True.** The 5 are named; `check9_probe.py` is the one the pinned run reported SKIPPED not FAIL. **And the other direction nobody asked about: 7 pinned FAIL names had NO register row at all** — red and unattributable. **(c) ALL THREE DEFERRED SUITES ARE GREEN**, driven in a **throwaway CLONE, not a worktree** (a worktree shares `.git/config`, which is how `core.bare` leaked twice): exit **0 / 0 / 0**, none left the tree dirty, none moved `.git/config` — so **the mutation confound the register records for this family is HISTORICAL, not current**. `run_bare_run_write_probe.py` is in **cody's live claim**, so read-only, never edited. **NOTHING RESTORED IN THE MAIN CLONE BECAUSE NOTHING WAS TOUCHED:** status digest `2eeda7ffde63` and `.git/config` `789cfb6edb72` identical before and after. Three `recovered` rows added (5→8); census now **GREEN 8 · RED 51 · UNMEASURED 24 = 83**, individually verified **59 of 83** |
| **6** METHODOLOGY: cody's and cc's conventions | **DONE — 4 landed as 27–30; TWO of cody's claimed six are NOT LOCATABLE and are NOT invented** | `docs/2026-09-13-cross-domain-disciplines.md` 27–30; `docs/METHODOLOGY.md` 4 promotion rows; `<scratchpad>/b3_i6.out` | **COUNTED BEFORE AND AFTER, not trusted: 26 → 30, highest 26 → 30, numbers contiguous 1..30, and zero stale `twenty-five`/`twenty-six` strings left anywhere.** Group heading, denominator note and body all moved **twenty-six → thirty**. **CODY'S SIX, ACCOUNTED FOR HONESTLY.** Three are locatable verbatim in `docs/2026-10-06-cody-queue17-inventory.md` METHODOLOGY (ITEM 15) and are landed in cody's own figures: **27** a fix that closes named instances leaves the mechanism open (*162 of 169* → **169 of 521**; the hole was 352 rules in 105 files, not 7 in one), **28** every figure carries its denominator, command, commit and date (three of cody's own documents reported a sweep with **no exit code at all**), **29** a tier that clears a whole category and finds nothing in it is the outcome to distrust (**22 of 22 exercised, 0 dead** → **17 exercised, 5 DEAD** after the digest stopped including the mutation). **A FOURTH was already landed and had been double-counted:** the queue-16 rule is **convention 15**, *derived by cody*, with that exact document cited in `METHODOLOGY.md` lines 44 and 64. **THE REMAINING TWO CANNOT BE LOCATED AND ARE NOT INVENTED.** cody's handoff says *"plus the three from queue 16"*, but `docs/2026-10-06-cody-queue16-inventory.md` has **exactly one** `## METHODOLOGY` section across all 17 of its headings — ITEM 8, the captured-exit-code rule, which is convention 15. Searched: that file's full heading list, every `docs/handoff-cody-*.md`, and every `docs/2026-10-0*-cody-*.md`. **CC'S ONE landed as 30**, text unchanged in substance, **with cc's reason for leaving the number blank quoted rather than paraphrased** (*"picking a number from outside the file is how two 11ths happened on 2026-09-25"*). **The membership question was asked of all four and all four are OUTSIDE the cannot-fire group, which stays at TEN** — 29 is the one that needed arguing and it loses on a real distinction: cody's tier CAN fire, so the fault is a mechanism that cannot DISTINGUISH, not one that cannot fail. **Bonus, because cc's file said so and `METHODOLOGY.md` is mine: cc's half of cody's `--open` row is CLOSED**, including cc's own correction from *ZERO of 238* to **1 of 239 post-fix, and it passes**; cody's half stays open; `docs/tier-a-reviews.json` untouched |
| **7** one measured lesson | **DONE — routed, not self-promoted** | `docs/METHODOLOGY.md`, routed queue | **SHARING A HELPER DOES NOT SHARE ITS CONFIGURATION: a stripper's stage set and its input contract are properties of the CALLER, and carrying either across gives a wrong answer silently.** Reuse was the right call — `jscomments.py` exists because seven private strippers destroyed up to 90% of their input, `strip_comments.js` because three were each wrong differently — **and it is not the end of the problem. Measured FOUR times in this one batch, every one a DEFAULT: (1)** `blank_string_bodies` carried from `truthy_sum_check.py` into `orphan_register_check.py` took it **CLEAN → 8 FINDINGS, all false**, because there the pattern is code-also-in-prose and here the pattern **IS** a string literal — caught **only by diffing the verdict**, the exit code read as a successful fix; **(2)** `strip_comments` on a bare-JS fixture **stripped nothing, silently** (outside `<script>` only `<!-- -->` is a comment) — caught because the new control arms **FAILED on their first run**, and the arm that failed was the **anti-vacuity** one; **(3)** the same assumption an hour later on the `__file__` re-derivation, where `jscomments` has no `strip_js` at all — caught by an `AttributeError`, i.e. **by luck**; **(4)** the same shape one level out, the SEQ 17-A sweep's default SUBJECT, which made *"set 29 → 0, 100% phantom"* an artefact of my harness and one of the four named sites **not a defect at all**. **THE RULE: re-derive and ASSERT a shared helper's input contract and stage set for the new caller rather than inheriting them** — say what the caller's pattern is (code / string literal / prose), assert the helper did something on the new input, and diff the subject's verdict across the adoption. **THE SECOND-ORDER LESSON IS WORTH MORE: three of four were caught by an arm or a diff and the fourth by an accident — the anti-vacuity arm is the difference between a fix and a fix certified by a vacuous test.** Routed because every instance is mine; it sits beside **cody's 29** rather than inside it (29 distrusts a category-wide CLEAR; case 1 is the same mechanism loudly in the opposite direction, and **zero-from-anything is the one nobody looks at**) |
| **8** handoff before the report | **DONE** | the BATCH b3 FINAL STATE section below | written at a point where nothing is half-finished: `ahead 0 / behind 0`, all three b3 commits **ON-REF** by `merge-base --is-ancestor`, every touched suite re-run alone at the final HEAD and all **exit 0**, no long-running job open |


---

# BATCH b3 FINAL STATE -- written before the report

## COMMITTED AND PUSHED

| | |
|---|---|
| branch | `main` |
| HEAD | **`4c3d24a2`** |
| pushed | **yes -- `ahead 0 / behind 0`** of `origin/main` at the time of writing |
| working tree | clean except **one pre-existing untracked file**, `sql/restore_demo_pins_2026-09-29.sql`, there at session open for five batches and not mine |
| `git config core.bare` | **empty -- unset.** `git status` answers normally |
| `git stash` | **one entry: `stash@{0}: autostash`.** Pre-existing since batch 15, not created here |
| long-running jobs | **none.** No whole-tree run and no `--pinned` run started; every suite driven individually |
| the global settings file | **`~/.claude/settings.json` was WRITTEN this batch** -- outside the repo, under its own claim, released straight after. Pre-write bytes are in `<scratchpad>/b3_settings_BEFORE.json` |

**Commits this batch, each verified ON-REF with `merge-base --is-ancestor`:**

| commit | what |
|---|---|
| `c7e2f6fb` | SEQ 17-B: the left-operand fix, arm 14 as a pair, three baseline entries removed |
| `e502a628` | SEQ 17-A at four sites: three checkers read code instead of prose, one finding withdrawn |
| `4c3d24a2` | conventions 27-30, the three reconciliations, the measured lesson |

Plus four `chore(claims)` commits: the settings-only claim taken and released, and
the items 3-7 claim taken (released after the report).

## EVERY SUITE RE-RUN ALONE AT THE FINAL HEAD

Each as its own command with `$?` read on the next line -- no pipe, no `&&`, no
`;` chain, which is convention 24 applied to the measurement:

    TRUTHY_SUM_CHECK_EXIT=0          CLEAN, 47 baseline keys
    TRUTHY_SUM_PROBE_EXIT=0          40 arms
    ORPHAN_SELFTEST_EXIT=0           11 arms
    ORPHAN_REGISTER_CHECK_EXIT=0     verdict identical to pre-fix
    SAIRNVET_SUITE_EXIT=0            23 arms
    DEMO_SEED_SUITE_EXIT=0           20 arms
    CITATION_DRIFT_PROBE_EXIT=0      24 arms
    KNOWN_RED_CHECK_FIXTURES_EXIT=0

## FINAL FIGURES, re-derived at this HEAD

| | |
|---|---|
| standing conventions | **30** -- counted from `## <n>.` headings, contiguous 1..30 |
| conventions landed this batch | **4**: 27/28/29 **derived by cody**, 30 **derived by cc** |
| **the 83, in three counts** | **VERIFIED GREEN 8 · VERIFIED RED 51 · UNMEASURED 24 = 83** |
| individually verified, either way | **59 of 83** -- the figure that only goes up |
| register | `entries` **76**, `recovered` **8**, empty `why` **11** |
| `truthy_sum` baseline | **47** keys (50 - the 3 that said to remove them) |
| citation drift, four apps | ANCHORED **45** · SOUND **11** · DRIFTED **22** · INCONCLUSIVE **29** · row sums **107** |
| `__file__` population | **979 of 1232** code-only (was published as 978 raw) |
| control arms added | **22** across four files, every set with an anti-vacuity arm |
| global settings hooks | all **five** repo hook types present; PreCompact fires **once** |

## WHAT IS OPEN, AND WHY

| open | why |
|---|---|
| **the Tier A discharge** | **BLOCKED, not skipped.** `--discharge` writes `docs/tier-a-reviews.json`, which is in **cc's live claim FILES**. Three obligations are assigned to me; two are COULD-NOT-TELL (their subject shas do not resolve in this clone) and **hover2 `2026-09-30T13:59:56Z`, 179h, is the only one with no freshness complaint** -- the one to take the moment cc's claim clears |
| **43 of the 47 SEQ 17-A findings** | and they **inherit a measurement fault**: the sweep measured every pattern against the app file its containing file reads. Of the four taken, **one was not a defect at all**. Each remaining one needs its real subject read **before** it is actioned |
| **2 of cody's 6 methodology conventions** | **NOT LOCATABLE and not invented.** Searched the full heading list of `docs/2026-10-06-cody-queue16-inventory.md` (one `## METHODOLOGY` section, already convention 15), every `docs/handoff-cody-*.md` and every `docs/2026-10-0*-cody-*.md` |
| **24 of the 83 unmeasured** | down from 27. Unmeasured individually, **not presumed red** |
| **20 register rows in the 83 with no sha-stamped run** | the remaining census work, named in `<scratchpad>/b3_i5b_final.out` |
| **7 pinned FAIL names with no register row at all** | three became `recovered` rows this batch; the other four -- `run_citation_anchor_hop_sabotage.py`, `run_committer_identity_probe.py`, `run_purge_evidence_probe.py`, `stale_row_sweep_control.py` -- are **red and unattributable**, the state an entry exists to remove |
| **11 register rows with an empty `why`** | NOT DIAGNOSED YET, which this register defines as a backlog rather than a shrug |
| **`tools/jscomments.py` has no `strip_js`** | so a bare `.py` or `.js` handed to its `strip_comments` is stripped **silently, not at all**. Worked around twice this batch (a `<script>` wrapper, and `pycomments` for `.py`). **Routed as a gap, not patched** -- that file is not in my claim |
| **the `__file__` predicate is still lexical inside STRINGS** | comments are handled now; a `rev-parse` inside a string literal still counts as anchored, and the effect is unmeasured |
| **cody's half of the `--open` finding** | cc's half is closed and recorded. cody's remains open |

## EXACT NEXT STEP, PER OPEN ITEM

1. **The Tier A discharge: hover2 `2026-09-30T13:59:56Z`** (`leg_insurance`,
   `mech_checks`), the moment `docs/tier-a-reviews.json` leaves cc's FILES. The
   other two of mine cannot be reviewed from this clone at all -- their subject
   shas do not resolve here.
2. **Before taking ANY of the 43:** read the pattern's real subject out of the
   source and measure against THAT. `<scratchpad>/b3_i4_subjects.py` is the
   worked example and it is four lines of work per site.
3. **The four unattributable pinned names** -- one register row each, from a run
   whose output exists. They are cheap and they remove an unattributable red.
4. **The census** -- 24 to go. Re-extract the 83 from `pinned2_stdout.txt` every
   time and let the script refuse on a disagreement; never quote the 83.
5. **`jscomments.strip_js`** -- route it to that file's owner, or wrap at every
   call site and say so. Two call sites already do the latter.
6. **The `__file__` predicate inside strings** -- measure the effect before
   deciding whether to fix it; it may be zero.

## CLAIMS HELD

**`fourth` is HELD** as the items 3-7 claim, declaring
`tools/truthy_sum_check.py`, `tests/run_truthy_sum_probe.py`,
`tools/truthy_sum_baseline.json`, `tools/stale_row_sweep.py`,
`tests/sairnvet_seed_never_syncs.js`, `tools/orphan_register_check.py`,
`tests/demo_seed_licence_scope.js`, `tools/citation_line_drift_check.py`,
`docs/2026-10-07-fourth-coverage-ledger.md`, `docs/2026-10-07-fourth-routed.md`,
`docs/METHODOLOGY.md`, `docs/2026-09-13-cross-domain-disciplines.md`,
`docs/known-red-suites.json`, `docs/handoff-fourth-2026-10-08.md` and
`SAIRN-ACTIVE-WORK-fourth.md`. **Released after the report.**

The settings-only claim on `.claude/settings.json` was **taken before that write
and released immediately after it**, as instructed.

Two other sessions live throughout: **cody** (batch25-b2) and **cc** (batch17-b3),
both re-read from `sairn_claim.py list` at pickup -- which is convention 30, landed
this batch and applied in it.

**NOT TOUCHED, each checked rather than assumed:** `docs/tier-a-reviews.json`,
`tools/defect_register.py`, `tools/tool_owner_map.py`, `docs/tool-owner-map.json`,
`tools/tooling_inventory.py`, `CLAUDE.md` and `docs/scrutiny-flags.json` (**cc**,
live); `tools/run_all_tests.py`, `tools/capture_exit.py`,
`tests/run_bare_run_write_probe.py`, `tools/clone_health_check.py`,
`docs/defect-density-register.json` and `docs/SAIRN-PROCESS-RULES.md` (**cody**,
live); `docs/CRITICALITY-TIERS.md`; and nothing anywhere under
`.claude/skills/sairn-hover-auditor/`. **No defect record was added by me** -- both
register paths are inside other sessions' live claims.

**`docs/scrutiny-flags.json` is cc's and the push gate WRITES IT on every push.** It
was **restored, never committed**, three times this batch. That is standing friction
worth naming: a gate that writes a file another session owns makes every push a
choice between a dirty tree and touching somebody else's file.

**I closed only findings I originated, and reclassified none.**

## TRANSCRIPT

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\7e379670-c1b8-4e19-9aa2-b1affe2f960e\scratchpad

Batch b3, in item order: `b3_claims.txt`, `b3_tiera.txt` (item 1);
`b3_i2_merge.py` / `b3_i2_patch.py` / `b3_i2_dryrun2.out` / `b3_i2_apply.out`,
`b3_i2_test.py` with `b3_i2_test_before.out` (**6 of 14 arms FAIL**) and
`b3_i2_test_after.out` (**14/14 pass**), `b3_settings_BEFORE.json` /
`b3_settings_AFTER.json` (item 2); `b3_i3_fix.py`, `b3_i3_tool_prebaseline.out`,
`b3_i3_tool_after.out`, `b3_i3_probe_after.out`, `b3_i3_ablate.py` / `.out`,
`truthy_sum_check.PREFIX.py` / `.FIXED.py` (item 3); `b3_i4_subjects.py` / `.out` --
**the script that found one of the four named sites is not a defect** --
`b3_orphan_*.out`, `b3_vet_control.out` (**the control arms failing**) and
`b3_vet_control3.out` (passing), `b3_dsl_after.out`, `b3_cld_sen_after.out`,
`b3_cld_probe_H2.out`, `b3_i4_ledger.py` / `.out` (item 4); `b3_i5a.py` / `.out`,
`b3_i5b.py` / `b3_i5b_final.out`, `b3_i5c.py` / `.out`, `b3_census_i5.out`
(item 5); `b3_i6.py` / `.out` (item 6); `b3_i7.py` (item 7);
`b3_final_krc.out`, `scrutiny-flags.GATE-WROTE.json`.

**And the batch-14/15 session's scratchpad, a DIFFERENT directory**, which holds
`pinned2_stdout.txt` -- the only copy of the pinned run the 83 is re-extracted from
every time -- and `sweep_full.py`, the report gate:

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\4975e2e9-8002-4f73-9d9d-240c42c3b643\scratchpad

**And the memory directory**, which carries a per-item checkpoint of this batch
updated after every single item:

    C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\memory\batch-b3-progress.md

---

# BATCH b4 CHECKPOINT LOG -- one row appended BEFORE the next item starts

Mirrored into the memory directory after every item at `batch-b4-progress.md`.

| item | state | evidence | exact next step |
|---|---|---|---|
| **1** claim + resume check | **DONE — and items 4 and 7 are NARROWED at pickup, which is convention 30 doing its job** | `<scratchpad>/b4_claims2.txt`, `b4_claim.txt` | claimed first, then resumed. **HEAD is `10f5e431`, not the `aa2e0ec9` in the brief — 26 commits landed from other sessions in between**, so the brief's anchor was one batch stale; `aa2e0ec9` is still ON-REF and all four b3 commits (`c7e2f6fb`, `e502a628`, `4c3d24a2`, `aa2e0ec9`) re-verified ON-REF by `merge-base --is-ancestor`. `ahead 0 / behind 0`, tree clean except the pre-existing untracked `sql/restore_demo_pins_2026-09-29.sql` (six batches, not mine). **Nothing from b4 had landed, so nothing is skipped.** **ONE live session: cody batch26 at 0.5h, and its FILES declare `docs/METHODOLOGY.md` AND `docs/external-files-index.json`** — the two files items 4 and 7 would have written. So item 4 is a **READ-ONLY recount** and item 7's registration half is **FLAGGED BACK into my own routed doc**, declared in the claim rather than reworded past. `tools/jscomments.py`, the conventions file, my routed doc and `.claude/skills/` were each checked against that same live list and are **FREE** |
| **2** the remaining 43, subject-verified | **DONE — 36 REAL / 7 WITHDRAWN, and EVERY surviving magnitude is withdrawn too** | `<scratchpad>/b4_i2_subjects.py` / `.out`, `b4_i2_context.out`, `b4_i2_verdicts.py` / `.out` / `.json`; routed in `docs/2026-10-07-fourth-routed.md` **SEQ 17-A -- THE REMAINING 43** | population first: **47 carried forward, 4 taken in b3, 43 across 23 sites**, arithmetic asserted. **The automated subject-tracer resolved only 3 of 23 and reported UNRESOLVED for 20 — recorded rather than hidden**, so it is reported as a POPULATION tool and the 20 subjects were READ. Verdicts: **REAL 36 findings / 17 sites**, **WITHDRAWN 7 / 6 sites** — a local literal in a control arm (`grd_write_faults.js:396`, `local_only_shape_probe.py:102`), two lexer-anchored `.match(content, i)` definitions in a tool that carries its own character-by-character JS lexer (`duplicate_global_check.py:68/69`), and **`orphan_register_check.py:134`, which reads a `// @REGISTER` line ON PURPOSE** — the clearest non-defect, and the one b3 deliberately preserved by leaving `parse_register` on the raw source. **ONE WITHDRAWAL IS A RECLASSIFICATION, NOT A CLEARANCE:** `grd_write_faults.js:385` strips comments first — with its own `/\/\/[^\n]*/g`, which eats the rest of any line containing `//` inside a URL. That is the **eighth private stripper**, the class `jscomments.py` exists to end, and it is routed as that. **AND THE NUMBER THAT MATTERS MOST: of 23 sites, exactly ONE (`seed_never_syncs_platform.js:250`) applies its pattern to a WHOLE app file.** The other 22 use a slice, an array body, another source file or a literal — so for **22 of 23** the published phantom count is an artefact of batch 17's harness. Shape real where marked REAL; number not, anywhere else. Nothing fixed: **36 findings across 17 sites stay open, now with their real subject on record** |
| **3** `jscomments.py`: `strip_js` + the language refusal | **DONE — and my own b3 claim about this file was WRONG, corrected in the file itself** | `<scratchpad>/b4_i3_measure.out`, `b4_i3_probe.out` (**16 new arms, exit 0**), `b4_i3_callsites.out` | **MEASURED FIRST, and it inverted the premise.** `strip_comments` has **never** tracked `<script>` context, so it **already handled a bare `.js` file correctly** — b3's handoff sentence *"its strip_comments on a bare .py or .js is a no-op"* is **FALSE for `.js`**, and it generalised from `tests/lib/strip_comments.js`, the JS library, which really does need a `<script>` element. Two libraries, similar names, **opposite input contracts**. The correction is written into `jscomments.py` itself, not just here. **AND ON PYTHON IT IS NOT A NO-OP, IT IS DESTRUCTIVE:** `y = x // 3  # floor division` → `y = x` plus spaces, because **`//` is FLOOR DIVISION in python** and the scanner blanks to end of line. A caller gets a shorter file, no error and a wrong answer. `pycomments.strip_comments` handles the identical input correctly. **ADDED:** `strip_js(src, path)` (JS-only forms; no `<!-- -->`, since in a `.js` file that would eat a line containing `<!--` in a string), `strip_auto(src, path)` where **`path` is a required argument with no default** — convention 26 applied to a library — refusing `.py` by name and any unregistered extension, `looks_like_python()`, and a `WrongLanguage` exception. **`strip_comments` behaviour is UNCHANGED for all 20 existing importers** when no `path` is passed, so nothing breaks; it refuses only when told the path or when the source is unambiguously python. **16 arms, every pair in both directions, plus `L10` which asserts the damage is real and `L7b` which asserts the DETECTOR'S OWN LIMIT** — a python fragment with no `def`/`class`/`import` at line start is not detected, deliberately, because in a library 20 tools import a false positive is worse than the old silence. **CALL-SITE SWEEP: 50 sites across 20 files.** 11 flagged by the automated python signal, **all 11 read, and NONE actually feeds python to this module** — `tooling_inventory.py:2278` already carries the exact guard (`if not name.endswith('.py')`) and so does `temporary_state_check.py:177`; `retry_policy_audit.live_files()` is `git ls-files '*.js' '*.html'`, so no `.py` reaches it. **The blind spot was LATENT across the whole call graph, with no active wrong answer**, and that is stated rather than dressed up |
