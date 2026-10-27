# SAIRN handoff — cody b54 (2026-10-27)

All six items are closed or routed. Nothing is half-finished. I wrapped at 75% context with the remaining leads routed, rather than start more edits I could not push.

## Committed / pushed state
- **Item 1 — b53's 15 local commits LANDED.** They went out on push attempt 2 of a bounded 5. Every b53 work commit was checked with `merge-base --is-ancestor`:
  - `f45edc2c3` caps
  - `3a450c744` and `5f04bec63` probe
  - `d92e71c22` Tier A
  - `528b103d3` b53 deliverables
- **b54 fix LANDED** as `ae2600407` (five tools/ ratio fixes) plus its register record, on attempt 3 of 5. Checked with `merge-base --is-ancestor`.
- **How the push was done:** `tools/push_retry.py` has no single-attempt mode. Without `--loop` it only prints usage, and every git call inside it has a 120s timeout, which is shorter than this gate's ~4 minutes on an sd-data range.
  - Per your instruction, no `--loop`.
  - Instead I ran one bounded attempt per call: commit bookkeeping by name, rebase with the ledger resolver, push. Up to 5 attempts, and the ~4-minute gate run is itself the backoff.
  - Never forced. No skips.
- **Claims:** the `platform` claim is RELEASED. The release commit rides with this deliverables push; this file is written before that push, so its landing is confirmed in the report.
- **Path manifest:** cody override b54 replaces b53 and names the five tools/ files.
- **Transcript:** `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\2d1bcf76-c842-40ed-b21d-9b20d98e7d45.jsonl`

## 2. The ratio-shape leads: 5 FIXED (worst first), 7 ROUTED with exact sites
I re-read each one in the code before editing. All five are fixed in `ae2600407`, and each now prints what it excluded:

| tool | what was wrong | after the fix |
|---|---|---|
| `run_all_tests.py` (the worst) | `ran` subtracted SKIPPED but not a pinned run's `not_run`, so "N of M pass" counted files that never executed, and with no skips it printed "ALL M TEST FILES PASS" | `not_run` is subtracted and named |
| `text_gate_literal_sweep.py` | a COULD-NOT-RUN probe counted as coverage, matched by name with no intersection | only probes that RAN, for gates the sweep found, count. Today: 2 of 223 |
| `flaky_checker_quarantine.py` | divided every checker the ledger ever saw by today's registry, and printed "N of N" when the registry was unreadable | intersection; the rest named; an unreadable registry says so. 46 of 78 today, unchanged |
| `sairn_reachability_check.py` | a real `panels_with_handlers` of 0 fell through `or` to the wrong metric | 0 now counts as an answer |
| `checker_confidence.py` | pooled all history, unlike the quarantine tool beside it | scoped to the current tree |

Exit codes are unchanged against HEAD for each tool I ran. `run_all_tests` was compiled, not run in full.

**Not fixed, routed to cc (tools/ owner) or my next batch.** These are b53 subagent leads I have **not** re-read:
- `reliability_growth.py:79-91`: defects over the whole register against commits windowed from 2026-09-08.
- `hover_separation_audit.py:1110/1121`: a repeated pair counts per row in the numerator and once in the denominator.
- `defect_budget_policy.py:168-216`: an all-history total over a 30-day budget. Documented as deliberate, so it needs a decision, not just a fix.
- `ownership_evidence_drift.py:94`: a net count difference, so a dropped table and an added table cancel out.
- `gate1_verify.py --app`: one app's rows over the platform total.
- `live_probe_residue_audit.py:195`: the `archive/` exclusion is not counted.
- `cron_beat_refusal_check.py:372`: path-less crons are not counted.

## 3. Methodology: is not-run or skipped counted as pass anywhere I have touched?
**Yes, in two places this batch, and both are fixed:** run_all_tests (`not_run`) and text_gate_literal_sweep (COULD-NOT-RUN).

Earlier batches had already closed the same shape in:
- condition_coverage: a `--limit` subset now exits 2 (b52).
- probe_anchor_freshness: `skipped` and unresolvable entries are now counted and named by CHECK 5e (b49/b52).
- the b52 seven-tool fix.

**Coverage, stated plainly:**
- The b52 and b53 sweeps examined about 333 tools/ files, and about 108 were traced for numerator and denominator.
- The b53 sweep's 12 hits were the only not-run/skipped shapes found among the traced ones.
- The about 225 untraced files were classified as not-a-ratio from their print lines only.
- So "nowhere else" is claimed for the traced set only.

## 4. FOR HANK — the dental public-availability timezone finding (NOT mine to fix)
**`api/sairndental/public-availability.js` builds slots in UTC and ignores the practice timezone.**
- It builds each slot with `Date.UTC(y, m, d, sh, sm)` from the stored `dnt_provider_hours` "HH:MM" strings.
- `settings.timezone` is `America/New_York` and is never applied. So a provider's "09:00" is served as `09:00Z`, which is **05:00 Eastern**.
- Seen live in b53: the first slot was `2026-10-28T09:00:00.000Z`.
- It is pre-existing, and the `PV-VERIFY-1` row has the same issue.
- **Fix:** interpret block start and end in `settings.timezone`, DST-aware, before converting to UTC. Then add an arm that a 09:00 New York block yields `13:00Z` in summer and `14:00Z` in winter.
- Routed to hank. I have not touched it.

## Open, and the exact next step
| # | open | next step |
|---|---|---|
| O1 | dental availability timezone (§4) | **hank**: build slots in `settings.timezone`, plus the DST arm |
| O2 | 7 unfixed ratio leads (§2) | cc or cody next batch: re-read each site, then fix |
| O3 | push_retry has no bounded single-attempt mode, and its git timeout (120s) is shorter than the gate | cc: add `--attempts N` without `--loop` semantics, and a push timeout above the gate's runtime |
| O4 | Tier A reviews of b52/b53 cap changes | assignees in docs/tier-a-reviews.json (cc) |
