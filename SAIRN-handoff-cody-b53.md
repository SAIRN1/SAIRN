# SAIRN handoff — cody b53 (2026-10-27)

**READ THIS FIRST: the b53 commits are NOT on origin/main.** They are committed in this clone, 15 commits ahead of origin and 0 behind, with a clean tree and green suites.

Why they are not pushed:
- Every push this batch lost a race with the remote. The pre-push gate takes about 4 minutes on an `api/sd-data.js` change, and the remote moved during each run (`fetch first` / `cannot lock ref`).
- My background retry loop was then **stopped by Claude Code because the machine was critically low on memory**. The harness said not to restart it on my own, so I have not.
- That loop was killed in the middle of a rebase. I finished the rebase, so nothing is half-applied.

**Exact next step:** from this clone, run `python tools/push_retry.py --loop`, or a plain `git push origin main` (not forced) when the remote is quiet. Then confirm with `git merge-base --is-ancestor e37425be6 origin/main`. The hashes will change if the push rebases.

Nothing else is half-finished.

## Committed state (local)
| commit | what |
|---|---|
| `e37425be6` | feat(caps): the 64KB default is measured as jsonb text at all four sites |
| `7542e7169` | fix(tests): run_condition_coverage_probe is green |
| `9fd69b1de` | fix(tests): the probe refuses an import (CHECK 5e flagged it UNGUARDED) |
| `bacb8fb6f` | Tier A obligation for the default-cap change |

Plus register records and re-seats, and gate bookkeeping.

- **Claim:** the `platform` (b53) claim commit `249baf1c0` is also local only, so other clones cannot see it. Treat cody as unclaimed until the push lands, then release it.
- **Path manifest:** cody override b53 replaces b52 and names the four api files and the b52 test.
- **Transcript:** `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\2d1bcf76-c842-40ed-b21d-9b20d98e7d45.jsonl`

## 1. SAIRNdental demo booking: SEEDED, live on the demo licence
The public booking page was empty for two reasons, and both are fixed. These were live data writes through the owner session on DNT-PINNACLE-2026. No code was involved.

Cause one:
- `dnt_settings.publicly_bookable_procedure_type_ids` held one stale id, `PC-1786416376504-314`, that matches no procedure.
- It is now `PC-DEMO-1` (D0120 periodic evaluation), `PC-DEMO-2` (D1110 adult prophylaxis) and `PC-DEMO-3` (D0274 bitewings): routine items a patient books directly. Restorative work (D2391, D2740) was left off, because it needs a dentist's plan first.

Cause two:
- The only `dnt_provider_hours` row was for `PV-VERIFY-1`, so no demo provider had hours.
- I added 15 rows: `PH-DEMO-{1,2,3}-{MON..FRI}`, Monday to Friday 09:00–17:00, for `PV-DEMO-1/2/3`.

**Live check:** public availability now lists the 3 procedures. Slots for PV-DEMO-1 over two weeks: 240 for D0120, 90 for D1110 and 320 for D0274.

**FINDING, routed to hank (`api/sairndental/`):** `public-availability.js` builds slots with `Date.UTC(...)` from the stored hours and ignores the practice timezone (`America/New_York`). So "09:00" is served as 09:00Z, which is 05:00 Eastern. That is true of the pre-existing `PV-VERIFY-1` row too, and is not new. The fix is to interpret the hours in `settings.timezone`.

## 2. The 64KB default measures jsonb text: DONE (committed, not pushed)
Following b52's per-resource precedent, the default now measures `octet_length(data::text)` on jsonb at all four places it lives:
- the `api/sd-data.js` gate, after the dental location stamp;
- `api/sd-sub-data.js`;
- `api/_lib/sd-store.js` (writeSlab and writeMemory);
- `api/bridge.js` push.

Tests:
- `api/b52-cap-jsonb-measure.test.js` is re-aimed, 6/6. Arm G3: a dnt_patients record at 65,471 bytes compact and 98,196 as jsonb gets 413 at the gate.
- Full api run: **328 of 333 suites green.** The 5 red ones are red identically with this change stashed: family-contacts, law-trusttx-clearance, leg-bookings-toctou, leg-session-gate, law-trust-reconcile-endpoint.

## 3. tests/run_condition_coverage_probe.py: GREEN (26 PASS, 0 failed)
There were two causes, and in both the probe had fallen behind its tool:
- **Arm 4** dirtied the tree with an UNTRACKED marker and looked for `WORKING TREE IS DIRTY`. The tool now scopes its refusal to the engines it measures, deliberately ignores untracked files, and says `AN ENGINE OR ITS SUITE IS MODIFIED`.
  - Re-aimed: the arm appends one line to a measured engine and restores it from a byte snapshot.
  - New arm 4c checks the engine is byte-identical afterwards.
- **Arm 5** called `sweep()` without the now-required `root=` and crashed before 5a–5e. It now passes the sandbox root.
- Because arm 4 now touches a tracked file, CHECK 5e flagged the probe UNGUARDED. It now refuses an import. `mutation_anchor_check` reports no unguarded probes.
- Register record written.

## 4. Methodology: ratio sweep of the tools/ scripts b52 did not cover — REPORTED, NOT FIXED
A subagent examined 300 files and traced about 75 that print a real ratio. **I did not re-read these in the code and did not fix them.** I chose to wrap up at the 80% context rule with the push still open rather than start twelve tools/ edits I could not push. They are leads, listed for cc (tools/ owner) or my next batch.

Shape present (9):
- `run_all_tests.py:1924` — "N of M pass" counts `not_run` files as passing.
- `flaky_checker_quarantine.py:718/749` — the numerator is every checker ever measured and is never intersected with the registry, so it can exceed M. Separately, `:543` drops registered checkers with no file without counting them.
- `checker_confidence.py:84` — `classify(entry)` with no tree argument pools all of history. Its sibling tool already fixed this.
- `sairn_reachability_check.py:154` — `panels_with_handlers or panels_seen`: a real 0 falls through to the wrong metric.
- `reliability_growth.py:79-91` — defects over the whole register against commits windowed since 2026-09-08.
- `hover_separation_audit.py:1110/1121` — repeated pairs are counted per row in the numerator and once in the denominator.
- `text_gate_literal_sweep.py:173-205` — a hard-coded probe list, matched by name, and COULD-NOT-RUN counts as covered.
- `defect_budget_policy.py:168-216` — an all-history total over a 30-day budget. This is documented as deliberate.
- `ownership_evidence_drift.py:94` — a net count difference, so a dropped table and an added table cancel out.

Minor (3):
- `gate1_verify.py --app` divides one app's rows by the platform total.
- `live_probe_residue_audit.py` excludes `archive/` without printing a count.
- `cron_beat_refusal_check.py` skips path-less crons without counting them.

About 60 traced scripts are CLEAN. They are listed in the subagent report, which is in this session's transcript.

## 5. "seq1139 items 13–16": NOT ACTIONABLE BY A BUILD AGENT
- These are **H2's** seq1139, a blind cold read of H2's own PL-2 tooling. The numbering 13–16 comes from H2's b84 handoff, not from the log entry.
- They map to logged items 7, 6 and 8:
  - 13: the judge counts stderr.
  - 14: weak selftests for the older PL-2 code.
  - 15: `private_key_files()` misses DER, PKCS#12, JWK and subdirectories, and the holder verifies with the auditor's own `sealed_evidence.py`.
  - 16: `--score` never checks the registration was pushed.
- All four are in `tools-hover2`, the auditor's own tooling, which a build agent must not edit. H2's own reports carry them as "items 13–16 stand", most recently b87.
- Nothing is routed to cody. Next step: H2.

## Open, and the exact next step
| # | open | next step |
|---|---|---|
| O1 | **15 b53 commits unpushed** | cody / Michael: `python tools/push_retry.py --loop` from SAIRN-cody when memory allows; confirm on origin; release `platform` |
| O2 | public-availability ignores the practice timezone | hank: build slots in `settings.timezone` |
| O3 | 12 ratio-shape leads (§4) | cc or cody next batch: re-read each site, then fix |
| O4 | seq1139 items 13–16 | H2 (own tooling) |
| O5 | Tier A review of the default-cap change (after it lands) | assignee named in docs/tier-a-reviews.json |
| O6 | 5 pre-existing api reds (§2) | owners of those suites; all were red before b53 |
