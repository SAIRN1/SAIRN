# cody — latest

**Batch b17 · 2026-10-15 · LANDED on `origin/main` at `27470aeb`**
0 ahead / 0 behind, ancestry verified. Pushed without `--force`. Nothing
overridden. No `api/`, `sql/` or `tools/` file edited. No hook restored.
Claim `tests` released.

## The one-line result

**Eight of the thirty remaining `tests/` failures closed at cause — and not one
of the thirty was a live `api/` defect that b15's last-line triage had named
correctly.**

## What it was instead

| cause | files |
|---|---|
| a probe anchor that quietly stopped matching its subject | **6** |
| an operator decision (the 23 hooks cleared 2026-10-11) reported as a defect | **4** |
| an intentional `sairn_claim.py` policy change reported as a regression | **2** |
| a real `api/`-side defect, correctly identified | **2**, and both differ from what b15 routed |

**The sharpest one was never red.** `tests/sairnbuild_server_wins.js:420`
asserted the literal `key==='bld_bids'` appears in `bldRetryPending`. It does
not — but the string occurs twice in `sairnbuild.html` and **both are
comments**, one of them *inside that very function*, explaining that the old
form used to read that way. **The assertion was satisfied by the comment
documenting the removal of the thing it asserted**, while the sabotage arm
guarding it was ANCHOR-0. Two layers of guard, neither guarding.

## Item 1 — the compaction diagnosis

**232 transcripts across all six clones. ZERO structural compaction events.
Peaks of 957k–999,683 tokens.**

The winning source is `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE = "97"` in
`~/.claude/settings.json` — the only autocompact knob set anywhere, confirmed
live. No `autoCompactWindow` at any scope, no `modelSettings` block at all,
neither managed-settings file on disk, and **all six live `claude.exe`
processes launched with zero arguments**. Fixed baseline **59,434 tokens**,
measured.

**Verdict: not threshold, not window, not flooding.** These sessions do not
compact — they end. At the fastest growth rate ever measured here (5,820
tok/min) a 1M window takes 2.6 hours to fill.

**Read the zero as "no record of any compaction", not as proof none occurred**
— three sessions crossed the trigger point and still emitted no marker.

## Open, with the blocker named

* **The 16 CHANGED / 9 RECOVERED register rows.** Not done: the register was
  measured 2026-10-12 against 411 files and **none of b17's eight newly-green
  files has a row in it (0 of 66)**. Needs a full-tree log.
* **`docs/test-file-floor.json` not raised** — and "808 vs 970" is **two
  different metrics**: the floor's own population is **819**, so the real gap
  is 11, not 162.
* **18 of the 30 routed from their failure line, not read to cause.**
  Hypotheses with evidence attached.

→ **HANK:** a widened `sf` session gate is currently **SILENT**;
`law_trusttx` is the **sairndental** pre-gate, not sairncare; `rf_schedule`
fails three ways. **Two of b15's three `api/` suites are confirmed landed.**
→ **CC:** `tooling_inventory.py --hooked` fails **open** on an empty hook set.
→ **FOURTH:** the `bld_bids` Tier A review is assigned to you.

**Full detail:** `SAIRN-report-cody-b17.txt` ·
`docs/2026-10-15-cody-b17-triage.md` ·
`docs/2026-10-15-cody-b17-compaction-diagnosis.md` ·
`SAIRN-handoff-cody-b17.md`
