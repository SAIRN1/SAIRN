# Ablation test 1: what does the sabotage harness's own verdict actually catch?

**2026-09-25 (CC).** Methodology item 98 — ablation testing, SpaceX's technique
rather than chaos engineering: **pull ONE named protective layer, with sensors
on that exact spot, and measure what it individually contributed.** Item 70's
chaos engineering asks "does the platform survive a random failure". This asks
the sharper question: **what does THIS layer catch that nothing else would?**

The subject picked itself. `tests/sabotage_harness.py` is the single point 27
negative controls pass through, and until 2026-09-25 its per-mutation verdict
was `rc != 0` — a mutant that failed to PARSE was indistinguishable from one the
suite refused. A layer whose own pass/fail signal is ambiguous is the ideal
ablation subject, because you cannot reason about what it catches; you have to
remove it and count.

---

## The experiment

**Layer under test:** the harness's per-mutation parse check (`_parse_error`),
added 2026-09-25.

**Ablation:** the layer did not exist until today, so the "ablated" condition is
**main as of yesterday** — no synthetic removal needed, and no sandbox risk,
which is the cleanest form this experiment can take.

**Instrumentation:** every probe that imports `run_probe` (27 files), run in
both conditions, comparing per-arm verdicts rather than exit codes alone.

**Subject state:** "already-known-clean code" per the brief — main was green by
every gate and every generated document; all 27 probes were believed passing.

## What slipped through that every other layer also missed

**THREE probes were reporting CAUGHT on mutants that never parsed.** Each had
been green for as long as the arm existed, and no other layer on this platform —
not the push gate, not the suites themselves, not `mutation_anchor_check.py`,
which verifies an anchor is unique but never that the RESULT compiles — could
see it:

| Probe | Arm | The mutant | What was really proved |
|---|---|---|---|
| `active_credential_gate_probe.py` | 6, the logging try/catch | `try {` → `if (true) {`, orphaning `} catch` | nothing — SyntaxError |
| `dnt_bi_scope_probe.py` | 2, the failed scope lookup | replacement ended in a dangling `if (false) {` | nothing — Unexpected end of input |
| `law_resources_phase_boundary_probe.py` | 6, a folded bespoke resource | `[].concat([...new Set(` — unbalanced paren | nothing — Unexpected end of input |

**That is the layer's individual contribution, measured rather than argued: 3
arms out of ~180, in three separate probes, written by three different sessions,
all green.** Each claimed a specific security or correctness property was
enforced. None of the three was evidence of anything.

## And the ablation found a second class the layer does NOT catch

Running all 27 in both conditions surfaced **five more arms that were red on
main for a different reason entirely** — stale anchors (ANCHOR-0) and, in two
cases, premises that had expired:

* `law_trusttx_session_probe.py` arms 1 and 4 — `SD_SESSION_GATED` and
  `SD_GATE_APP` both grew past the single-line literals the anchors quoted.
* `law_resources_phase_boundary_probe.py` arms 1, 2 and 5 — the same growth,
  **plus two arms whose PREMISE completed**: the SAIRNlaw phased rollout
  finished, so "law_deadlines is gated early" now plants current reality and
  reported SILENT forever, and the pre-completion open list it quoted is gone.
* `dnt_financial_tier_probe.py` arm 3 — `dadfedf4`'s platform-wide sweep wrapped
  all 48 role maps in `roleSet({…})` and the bare-literal anchor stopped
  matching the same day.
* `fail_open_triage_probe.py` — baseline red because `api/fail-open-triage-2026-09-04.test.js`
  pins the acceptance count at 11 and `24b7e3fb` legitimately removed one on
  2026-09-18. **The pin did its job** (an acceptance removed IS a decision) and
  then sat unmoved for six days, holding the suite AND the probe behind it out
  of service.

**The layer being ablated did not catch any of these five** — a stale anchor and
an expired premise are visible to the harness's existing ANCHOR-0/SILENT arms,
which were already reporting them correctly to anybody who ran the probes. What
was missing was not a check; it was **anybody running them**. That is the more
uncomfortable half of this result: five arms were failing loudly on main and the
signal had nowhere to go, because no gate runs the probe corpus.

## What this says about ablation as a practice here

1. **It works, and it is cheap when the layer is new.** No sandbox, no synthetic
   failure injection: the pre-layer condition is a git ref.
2. **Pick a layer whose signal is ambiguous.** The value here came from the fact
   that CAUGHT and CRASHED printed the same word. A layer with an unambiguous
   verdict has less to learn from ablation and more from a sabotage control.
3. **Measure per-ARM, not per-exit-code.** Three of the eight findings are
   invisible at the exit-code level: the probes exited non-zero in both
   conditions, for different reasons.
4. **The second-order finding outranked the first.** The experiment was designed
   to measure one layer's contribution; what it actually established is that the
   probe corpus has no runner, so 8 of ~180 arms across 27 probes were
   unreliable and nothing was going to say so. Filed as an open-work row.

## Reproducing it

    git stash                      # or check out the pre-layer ref
    for f in $(grep -rln "from sabotage_harness import" tests/*.py); do
      python "$f" >/tmp/o 2>&1; echo "$f exit:$?"
    done
    git stash pop
    # ...and again, comparing per-arm lines, not just the exit codes

The three MALFORMED-MUTATION findings are now permanent: `tests/run_sabotage_harness_parse_check_probe.py`
drives both directions (a parsing-and-refused mutant still reports CAUGHT; a
non-parsing one fails its arm naming the parse error) against the committed
fixtures, so the layer cannot silently revert.
