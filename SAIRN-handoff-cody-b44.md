# SAIRN handoff — cody b44 (2026-10-21)

Four items, all done. Nothing is half-finished.

## State
- Landed on origin/main, no force, first attempt:
  `6506b6875` register re-seat, `0db6373d6` two probe anchors.
- No app code, no SQL, no live writes. Nothing is deployed, so there is no live-verify.
- `.claude/settings.local.json.bak` is gone (Michael deleted it after b43).
- No claim taken. No active claim names these files (fourth b51: sairndental/sairnlegacy html and the a11y tests; cc b44: firebase-admin).

## Item 1: ce15ddaa6a3c register gap. Resolved.
**Concept:** the record cited my b27 commit's sha from before the rebase, and
the subject changed when it landed. So `--reseat` had nothing to match by subject.
- `ce15ddaa6a3c` exists only in this clone, kept alive by the reflog
  (`HEAD@{527}`, a `pull --rebase` pick). It is not an ancestor of origin/main.
- The landed commit is `864e6b764`. Its subject reads "rt_routes made reachable", not
  "the rt_routes primitive made reachable". It cites the same two files with the
  same numstat (routes.test.js +239, _resources/index.js +48).
- **Fix:** the record's `commit` and `subject` are corrected together, as 2 changed
  lines. `defect_register.py --check` was exit 1 in every clone and is now **exit 0**
  (708 records after rebasing onto hank b44).
- The `date` field (2026-10-19) was left alone. --check does not validate it.

## Item 2: scrutiny rows before pulling. Already built, now used.
**Concept:** the gap was in my own procedure, not in the tooling.
`tools/push_retry.py --loop` (b31) already runs `fold_scrutiny()` before every
rebase. It folds the gate's `docs/scrutiny-flags.json` write-back into ONE
bookkeeping commit, which later rounds amend. In b43 I wrote my own loop instead,
and it made five near-identical scrutiny commits. This batch pushed with the tool,
which landed on attempt 1. Saved as a cody memory (`push-with-push-retry-loop`).
The tree is dirty with the final push's scrutiny rows, as expected. The next
`--loop` folds them.

## Item 3: sweep for duplicated anchors. 2 found, both fixed.
**Concept:** a later commit copied an anchored line, so the anchor matched twice.
The harness refuses a non-unique anchor, so that arm tested nothing.
Two existing tools count exactly this: `tools/mutation_anchor_check.py`
(76 probes, 532 anchors) and `tools/probe_anchor_freshness.py` (417 files,
645 anchors). They agreed on 2, and both ran exit 1. Both are registered in
`tools/report_only_checks.py` as report-only, so they do not block anything. These
two anchors and the dental one stayed broken anyway. I did not check who reads
that report.
- `tests/run_law_phase2_session_sabotage_probe.py` arm 4: `bd836b641` (2026-10-19)
  gave `lawCountersign()` a copy of sdnData's token lines. The anchor is widened with
  sdnData's `if(!lic)return` head.
- `tests/claims/run_registry_claim_sabotage_probe.py` arm 4: `331cebe3c`
  (2026-10-16) gave the own-claim read a copy of the status line. The anchor is
  widened with the `for sess, c in rows:` line, which only the registry path has.
- **Differential:** the HEAD versions exit 1 and fail only that arm. The
  widened versions exit 0: law 9/9, registry 13/13, targets byte-identical.
  Both tools now exit 0, with 0 ambiguous and 0 vanished.

## Guardian
Check 0: `py_compile` is clean on both probes, and the register parses (--check).
The other checks cover app code, and no app code changed.

## Open
- `mutation_anchor_check.py` / `probe_anchor_freshness.py` are report-only. As a
  blocking gate they would have stopped all three duplicates at the commit that made
  them, and they take about a second. Not done: that is a gate change and Michael's call.
- A uniqueness check cannot see an anchor that is unique but sits on the wrong code (PR 1.3).
- Carried: hank F2/F3 owner write path; cc Tier A b31–b37; fourth defects 7/8.
