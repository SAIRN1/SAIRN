# Handoff — fourth (Ted), batch 14, 2026-10-07

**Written at the post-item-4 checkpoint the dispatch requires, and updated again
at the end.** The per-item checkpoint log is at the foot of
`docs/handoff-fourth-2026-10-07.md`; this file is the full picture.

---

## COMMITTED AND PUSHED STATE

| | |
|---|---|
| branch | `main` |
| pushed | **yes** — `760b4696..8ff247a2`, `ahead 0 / behind 0` of `origin/main` |
| working tree | clean except the pre-existing untracked `sql/restore_demo_pins_2026-09-29.sql` and `docs/scrutiny-flags.json`, which **cc's hook rewrites on every commit** |
| **`git config core.bare`** | **empty — unset.** `git status` answers |
| long-running jobs | **none.** No whole-tree run, no `--pinned` run. Every suite individually |
| probes run | `git status` captured **before and after every probe** and unchanged throughout; `node --check api/sd-data.js` clean after the three seam probes |

---

## THE FOUR THINGS WORTH READING FIRST

### 1. Three single arms block six register rows, and one of them is a PHI purge

| the one arm | lives in | rows blocked |
|---|---|---|
| **`5a  SAIRNsenior: every cached key is purged OR explicitly excluded`** | `tests/phi_cache_scoped_to_user.js` — 63 passed, **1 failed** | **3** |
| **`the registry still holds exactly 35 resources`** | `tests/sairnfreedom_server_backup.js` — 16 passed, **1 failed** | **2** |
| **`...and names the exact command that publishes the earlier entry`** | `tests/claims/run_push_verify_probe.py` — 68 passed, **1 failed** | **2** |

**Fix three arms, clear six rows.** The phi-cache one is not cosmetic: a cached
key neither purged nor explicitly excluded is **resident health data surviving a
logout**.

### 2. The four ABSENT Tier A records land in THREE different places, and two are now REVIEWABLE

They had been routed back to their originators twice and nobody closed them.
**That framing was wrong for three of the four** — the gate's own
`--reseat-shas` already knew where they go:

* hank `2026-10-05T09:03:14Z` → `9e3caeefd07f` `[EXACT FILE SET]` — **now STALE,
  reviewable**
* cody `2026-10-05T13:23:46Z` → `5e33157ee606` `[EXACT FILE SET]` — **now STALE,
  reviewable**
* cody `2026-09-28T03:34:57Z` → `bb840eeccb3c` **WEAK basis** (file-set subset,
  0.1h apart). Deliberately **not** written: `--write-weak-basis` is a
  containment argument and making it for cody's record is the judgement
  convention 11's human gate exists for
* hank `2026-09-27T03:42:29Z` → **REFUSED `[NO_OBJECT_IN_CLONE]`**, and the gate
  names the only action: run `--reseat-shas` **in the clone whose rebase
  orphaned it**, or fetch the object in first

`RESEATED 5 record(s) on a strong basis, 0 on the WEAK basis, 8 refused.`
`PROGRAM_EXIT=0`. This repoints a **provenance field** through the sanctioned
path — nothing was discharged, closed or reclassified.

### 3. The sweep premise was one batch stale, and widening it made a column useless

The dispatch said the matcher *"used a width of 8"*. **Fixed in batch 13.** What
was still narrow was the **corpus** — ten of my own documents, a convenience
sample. Now all **1,101** tracked `*.md` and `*.json`.

| | my 10 documents | the full corpus |
|---|---|---|
| distinct sha-shaped tokens | 115 | **16,319** |
| ON-REF | 82 | **2,433** |
| **ORPHANED** | 12 | **79** |
| ABSENT | 21 | **13,807** |
| rejected as not-a-sha | 10 | **1,624** |

**Quote the 79; never the 13,807.** At repo scale ABSENT is dominated by non-sha
hex in the JSON registers, and it is the state that attracts every false
positive. **My own five batch-12 commits are all five ON-REF** — the first batch
in three with none of my citations orphaned. And a correction to my own batch-12
figure: I called `docs/defect-density-register.json` **0 ORPHANED** using a
`{12,40}` pattern that could not see an 8-char prefix; it has **7**.

### 4. Two ablation attempts COULD NOT RUN before the one that worked

Ablating the removal-path split by **removing the `C=` emission from the
subject**: `COULD NOT RUN` — no such string in `tools/removal_path_check.py`.
Ablating it by running a modified **copy** of the probe from `%TEMP%`: ran and
printed **neither arm**, because the probe resolves its paths from `__file__`.
**That is the home-repository path class again, this time in my own ablation
harness.**

**In-place-modify-then-restore is the method that works for a tool that locates
itself.** Under convention 20 an attempt that could not run is not an ablation,
and reporting only the third attempt would have been the easy version.

---

## PER-ITEM STATE AT THIS CHECKPOINT

| # | item | state | evidence |
|---|---|---|---|
| 1 | full SHA sweep | **DONE** | coverage ledger §6; 13 arms, 3 byte-identical runs, `PROGRAM_EXIT=0`, `git status` unchanged |
| 2 | the 4 ABSENT Tier A | **DONE** | SEQ 14-A; `--reseat-shas --write`, 5 reseated on a strong basis |
| 3 | red register next slice | **DONE — 9**, 19 → **10** of 79 | SEQ 14-B |
| 4 | convention-18 fixes | **PARTIAL — 4 of 8** | coverage ledger §7 |
| 5 | census toward the 83 | *next* | — |
| 6 | settings merge re-check | *next* | — |
| 7 | the two corrected measurements | *next* | — |
| 8 | convention 22 | *next* | — |
| 9 | cody's routing path | *next* | — |
| 10 | handoff + release | *this file, updated at the end* | — |

---

## WHAT IS OPEN, AND WHY

| open | why |
|---|---|
| **10 empty-`why` register rows** | 19 → 10. **Three single arms would clear six of them** — see §1 |
| **4 of 8 convention-18 suites** | each carries a reproducing artifact |
| **two Tier A records are now reviewable** (hank 54h, cody 50h) | they became readable because of this batch's reseat. Discharging them is the cheapest high-value work available |
| **one Tier A needs a containment decision** | cody `2026-09-28T03:34:57Z`, `--write-weak-basis` |
| **one Tier A can only be reseated elsewhere** | hank `2026-09-27T03:42:29Z`, `[NO_OBJECT_IN_CLONE]` — from hank's clone |
| **two NOT CLEARED in this slice** | `seam_check/run_or_default_probe` (is the could-not-tell justified?) and `seam_check/run_ref_probe` (`baseline_clean` is False, so the arms below it say nothing) |
| **`QUOTABLE` does not name `cloud`** | one entry, and the better fix is to derive the vocabulary from the session registry |
| **`35` pinned in two suites, `33`/`81` in one arm** | convention 14; assert floors with n of N |

---

## CLAIMS

**`fourth` is held** and is released in item 10. The only other active claims are
**cc** (0.9h) and **hover2** (1.6h), and **neither declares any file in my set** —
re-derived at `10521191` from `sairn_claim.py list`, not assumed.

**`.claude/settings.json` was not touched regardless**, per item 6.

---

## THIS SESSION'S TRANSCRIPT

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\4975e2e9-8002-4f73-9d9d-240c42c3b643\scratchpad

Notable: `sweep_full.py` and `sw14_1.out`–`sw14_3.out` (item 1, three
byte-identical runs); `reseat_dry.out` and `reseat_write.out` (item 2, the dry
run and the write); `r3_*.out` and `phi.out`/`sfb.out` (item 3, one file per
suite plus the two baselines whose single arms block six rows);
`i4_abl.out`/`i4_abl2.out`/`i4_abl3.out` (item 4 — **the two attempts that could
not run and the one that did**).

---

## ITEM 5 — THE CENSUS: 40 of 83, re-extracted and cross-checked against the log's own summary

**The 83 is re-extracted from `pinned2_stdout.txt` on every run and never
quoted.** The script also reads the log's **own summary line** and **REFUSES if
the two disagree** — so "83" is not a number I carry, it is a number two
independent readings of the same file agree on.

    83 re-extracted from the log: 83 row(s)
    the log's own summary line  : 83

| | |
|---|---|
| **X of 83 verified individually** | **40** (was 31) |
| by exit code | **1 × exit 0**, 35 × exit 1, **4 × exit 2** |
| verified but NOT in the 83 | 1 — `tests/push_gate/check9_probe.py`, which the pinned run **SKIPPED** |
| still unverified of the 83 | **43** |

**40 is not 40 failures.** One exits **0** (`run_primitive_obsession_probe`,
recovered by the convention-18 fix) and four exit **2** — a could-not-run, not a
failure. So the 83 is at most 78 failures and 5 could-not-runs *as far as
individually verified*, and the 43 remain **unmeasured** rather than presumed
red.

---

## ITEM 6 — THE SETTINGS MERGE: RE-CHECKED ONCE, STILL BLOCKED

**Re-derived at `10521191`, and the blocking fact has changed shape without
changing the answer.**

* **cody's batch21 claim is now RELEASED** — `sairn_claim.py list` shows only
  `cc` and `hover2` active. So the *claim* no longer blocks it.
* **But the permissions merge still has not landed.** `~/.claude/settings.json`
  carries a `hooks` block with **only `PreCompact`**, and
  `git log -- .claude/settings.json` shows **no commit since 2026-10-05**.

**BLOCKED, and reported as such rather than retried.** The item says re-check
once and move on; one check, and nothing was written to either settings file.

**For whoever lands it:** the known-good schema is already in this repo —
`.claude/settings.json` carries a working `hooks` block with five events in the
`{event: [{matcher, hooks: [{type, command}]}]}` shape. The seven the brief names
are `SessionStart`, `PostToolUse` (matcher `"*"`), `PreCompact`, `Stop`,
`SubagentStop`, `Notification`, `SessionEnd`, each with
`python C:\SAIRN-status\sairn_status_hook.py`.

---

## ITEM 7 — TWO CORRECTED MEASUREMENTS, FOR CHAT TO ROUTE

**I have edited neither hank's nor cc's files, and neither finding is mine to
close.** Both were MY measurements and both were wrong; the records they were
measuring were right. Recorded here so chat can route them to their owners.

### TO HANK — the *"docstring only"* claim was CORRECT; my grep was not

| | |
|---|---|
| **what I measured first** | `git show f9f832c1 -- tools/tier_sentence_gate.py`, counting changed lines that are not comment-or-blank → **48**, which read as code |
| **why it was wrong** | **prose inside a triple-quoted string does not start with a quote character**, so a docstring body counts as code under that filter |
| **the measurement that answers it** | parse both sides with `ast`, replace the **module docstring** with a placeholder using its `lineno`/`end_lineno`, compare |
| **the result** | **CODE OUTSIDE THE MODULE DOCSTRING IS BYTE-IDENTICAL: True.** The docstring span grew 1–60 → 1–115. No criterion, threshold, field list or verdict moved |

**hank's record was exact.** This correction is already inside the `verdict` I
wrote on that obligation, so it is on the record — but hank should see it
without having to read a discharge.

### TO CC — the `SELF_EXCLUDED` addition IS present; my `sed` window was not

| | |
|---|---|
| **what I measured first** | `sed -n '459,500p'` over `tools/cross_tenant_isolation_scope.py`, read **four** entries, concluded the probe was **missing** from `SELF_EXCLUDED` |
| **why it was wrong** | the tuple runs **past line 500** — each entry is separated by a long comment — so the window ended before the list did |
| **the measurement that answers it** | `ast.literal_eval` on the `SELF_EXCLUDED` assignment |
| **the result** | **EIGHT entries, and `tests/run_cross_tenant_isolation_scope_probe.py` is the eighth.** The grader's own output names all eight. Its line 57 is `import cross_tenant_isolation_scope as S`, confirming cc's stated reason |

**cc's record was exact**, and the related `12 → 17` pin figure was exact too:
at cc's own record SHA the pin **was** 17, and `1b453253` covered one more gate
188h later. **My premise was stale, not cc's figure.**

**This is the third instance behind convention 22** and the one that makes it
general: a bounded view presented as the whole, with no tool involved.
