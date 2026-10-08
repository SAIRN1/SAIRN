# Hover (H1) sweep-class method -- reusable for any future sweep class

Generalised from `hover_money_on_row_sweep.py` (built 2026-10-06, seq 935) so the NEXT sweep class does not re-derive this shape from scratch. This is a method writeup, not an invokable Claude Code skill in the `.claude/skills/` sense -- it lives in this role's own log directory because this role builds its own tools only in its own location, never in a build-agent file or the shared skills tree.

## The four steps every sweep class needs

1. **POPULATION DERIVATION, LIVE, EVERY RUN.** Never hardcode the count (Y). Read it from the current source of truth (for money-on-row: every Tier-B row in `docs/CRITICALITY-TIERS.md`, re-parsed fresh). A count copied from a prior batch is the exact defect this role's own methodology entries (seq 918, 933) exist to name -- "31 remaining" was wrong because nobody re-derived it, not because the search was dishonest.

2. **A HEURISTIC SCREEN THAT ERRS TOWARD MORE CANDIDATES, NEVER FEWER.** Build the narrowest check that still catches everything a hand sweep already proved true (lock it with fixtures built FROM those proven cases, not invented ones -- `hover_money_on_row_sweep.py`'s own two real bugs were both caught this way: a fixture using a proven-true case the tool returned the wrong answer for). Bias toward false positives, same direction `gate_parity_check.py` and every other report-only checker on this platform already leans, because a wasted human read costs less than a silently skipped real one.

3. **X-OF-Y REPORTING THAT NAMES WHAT IT DOES NOT KNOW.** Report THREE numbers, not one: population size (Y), how many were SCREENED by the tool (should always equal Y once the tool runs to completion), and how many are CONFIRMED by an actual human read. Collapsing "screened" into "confirmed" is the specific failure this writeup exists to prevent -- 116 screened and 4 confirmed are not the same claim, and reporting only one number hides which one you mean.

4. **OWNER ROUTING, NEVER A FIX.** A confirmed match gets `--routable` with the resource/file name and a target that is a build agent, never `self` (a mistake this role made and had to correct at seq 920 -- `target: self` on a platform-code finding is always wrong, because hover does not fix platform code). An unconfirmed candidate is NOT routed as a finding -- it is tracked in this role's own coverage ledger (`hover_coverage_ledger_own.md`) as "flagged, unread," which is a different, weaker claim than "found."

## Spot-check discipline

Before trusting a sweep's own output, hand-verify a sample (5 was the number this batch used, chosen to cover both already-proven and fresh candidates) and REPORT THE MEASURED PRECISION even when it is bad -- this batch's own money-on-row tool measured 2 of 5 (40%) on its first full run, and that number is in the log (seq 935) rather than smoothed over. A tool that is only ever run once and trusted is a tool nobody has actually checked.

## What this does not cover

Ownership and ESCALATION (what to do when a routed finding stalls) is a separate discipline, already covered by this role's own stall-handling entries (seq 894, 901, 912, 920, 929, 936) rather than folded into this sweep-method writeup -- a sweep finds candidates; what happens to a confirmed one afterward is a different problem with its own rules.
