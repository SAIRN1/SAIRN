# Holding my own tools to the standard I spent the day enforcing

**2026-09-29 (Cody).** `tools/checker_selftest_check.py` found that 54 of 67
registry checkers cannot show, on the run that says CLEAN, that they still
report a known-positive. Before building anything else, the same question was
asked of every tool I built or touched in this session and the one before it.

**Two questions, and they are not the same question.** Conflating them is how a
tool ends up looking covered:

- **A FIXTURE LOCK** proves the *criteria* classify a hand-built case. It lives
  inside the tool and runs on the real run.
- **A CONTROL** proves the *shipped tool* still fires and still refuses. It lives
  outside the tool and drives it from the command line.

A tool can pass the first and fail the second, and one of mine did.

---

## The table, run rather than recalled

| tool | self-test on the real run | known-bad arm | silent half | control |
|---|---|---|---|---|
| `assertion_label_shape_check.py` | PRINTED | yes | yes | `run_assertion_label_shape_probe.py` |
| `entry_point_scope_check.py` | PRINTED | yes | yes | `run_entry_point_scope_probe.py` |
| `parse_zero_third_state_check.py` | PRINTED | yes | yes | `run_parse_zero_third_state_probe.py` |
| `checker_selftest_check.py` | PRINTED | yes | yes | `run_checker_selftest_probe.py` |
| `mutation_anchor_check.py` | PRINTED | yes | yes | `run_mutation_anchor_probe.py` |
| `criticality_tier_check.py` | PRINTED | yes | — | `run_criticality_tier_probe.py` |
| `probe_anchor_freshness.py` | PRINTED | yes | — | `run_probe_anchor_freshness_probe.py` **(new)** |
| `claim_provenance.py` | n/a — not a criteria checker | yes | yes | `run_claim_provenance_probe.py` **(new)** |
| `tier_a_review_gate.py` | n/a — a gate, not a scanner | yes | yes | `run_tier_a_review_gate_probe.py` + sabotage probe **(newly declared)** |
| `report_only_checks.py` | n/a — a runner | yes | yes | `run_report_only_checks_probe.py` |
| `tooling_inventory.py` | n/a — a generator | yes | yes | `run_tooling_inventory_probe.py` |
| `control_char_check.py` | NONE | — | yes | `run_control_char_probe.py` |
| `checker_control_check.py` | NONE | — | — | **none** |
| `conflict_marker_check.py` | NONE | — | — | **none** |
| `probe_selector.py` | flag-only | — | — | **none** |
| `purpose_expired_measure.py` | NONE | — | — | **none** |

The last four were touched this session only to add a **zero-corpus guard** —
one `if not X: return 2` each, from the `parse_zero_third_state_check` sweep.
That is a refusal, not a criterion, and inventing a fixture set for a tool I did
not write would be the worst kind of coverage: a lock whose expected verdicts I
guessed. **They are reported here, not papered over**, and they are in
`docs/2026-09-29-selftest-triage-cody.md` with the rest of the 50.

---

## THE TWO REAL FINDINGS THIS PASS PRODUCED

### 1. The repo's largest control was invisible to the tool that counts controls

`tests/run_tier_a_review_gate_probe.py` — over a hundred arms — and
`tests/run_tier_a_review_gate_sabotage_probe.py` — 17 arms over 13 planted
mutations — **declared neither `CONTROLS_FOR` nor `CONTROLLED_BY`**.
`checker_control_check.py` finds a pair from those declarations and nothing
else, so one of the most consequential gates in this repo registered as having
**NO DECLARED CONTROL**.

Every arm ran. Every arm passed. The pair was simply not visible to the thing
whose whole job is to notice a checker with no control — and **a missing
one-line declaration is indistinguishable from a missing control file** to the
tool that reads it. Three declarations added; the registry moved from 5 tools
with no declared control to 4.

### 2. A fixture lock is not a control, and `probe_anchor_freshness` proved it

It carried a **20-arm `selftest()`** — a genuinely good lock — and
`checker_control_check` still listed it under NO DECLARED CONTROL. That was
accurate: **the lock lived inside the tool, so nothing independent ever drove
it.** A checker whose only witness is itself is exactly the shape this family of
tools exists to find.

`tests/run_probe_anchor_freshness_probe.py` (12 arms) now sabotages a criterion
**in process**, asserts the sabotage applied *before* asserting anything about
behaviour, requires exit 2 rather than an anchor-freshness figure, asserts the
restore, and then checks the lock result reaches the reader of the real run with
both figures non-zero and equal — because a `0/0` lock prints the same sentence
and proves nothing.

---

## What this pass does NOT establish

**Whether any of these fixture sets is any good.** Every table row above is a
structural answer: a lock exists, it runs, it prints, a control drives it. A
fixture set of one trivially-true case satisfies all four columns. That is
`tools/sabotage_control_check.py`'s question and it is not answered here.

**Two `silent half` columns are blank and that is a regex limit, not a verdict.**
`criticality_tier_check` and `probe_anchor_freshness` both have known-good arms;
the scanner looks for a specific vocabulary (`SILENT HALF`, `must not report`,
`stays silent`) and those two phrase it differently. Stated rather than left as
an unexplained gap — the same rule this session applied to fourteen NOT-JUDGED
arms.

**Re-run it, do not quote it.**

    python tools/checker_selftest_check.py --all
    python tools/checker_control_check.py
