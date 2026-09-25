> **CORRECTION, 2026-09-25 (same session):** this document says the corpus is
> **27 probes**. It is **65** — the count came from a grep matching one import
> spelling, so the sweep below ran against a subset of the corpus it claimed.
> Every arm it fixed was really broken, but **the coverage claim was overstated
> by more than half**, and "15 of ~180 arms across 27 probes" is really 15 arms
> out of a larger population. Measured, with the corrected figures and the
> gate decision they support, in
> `docs/2026-09-25-probe-corpus-cost-and-decision.md`. Left in place rather
> than rewritten: a number I published and then corrected is exactly the
> instrument-drift this platform keeps recording, and hiding the first version
> would remove the evidence.

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

**SIX probe arms were reporting CAUGHT on mutants that never parsed.** Each had
been green for as long as the arm existed, and no other layer on this platform —
not the push gate, not the suites themselves, not `mutation_anchor_check.py`,
which verifies an anchor is unique but never that the RESULT compiles — could
see it:

| Probe | Arm | The mutant | What was really proved |
|---|---|---|---|
| `active_credential_gate_probe.py` | 6, the logging try/catch | `try {` → `if (true) {`, orphaning `} catch` | nothing — SyntaxError |
| `dnt_bi_scope_probe.py` | 2, the failed scope lookup | replacement ended in a dangling `if (false) {` | nothing — Unexpected end of input |
| `law_resources_phase_boundary_probe.py` | 6, a folded bespoke resource | `[].concat([...new Set(` — unbalanced paren | nothing — Unexpected end of input |
| `run_reclassification_sweep_sabotage_probe.py` | the unreadable `.docx` | replaced the `raise` line, left its continuation dangling | nothing — unexpected indent |
| `run_unconfirmed_write_sweep_sabotage_probe.py` | 8, UNKNOWN answering success | dropped one `{` while the block's `} } });` stayed | nothing — missing `)` after argument list |
| `run_law_phase2_session_sabotage_probe.py` | 1 and 2 (after their anchors were repaired) | replacement entry with no trailing comma, spliced mid-map | nothing — Unexpected string |

**That is the layer's individual contribution, measured rather than argued: 6
arms across 6 probes, written by at least three different sessions, all green
or silently ANCHOR-0.** Each claimed a specific security or correctness property
was enforced. None was evidence of anything. **The last row is the sharpest: it
was introduced BY THIS QUEUE, when repairing a stale anchor changed the splice
context — so the layer caught a malformed mutant that did not exist an hour
earlier, which is the strongest available evidence it is load-bearing going
forward rather than a one-off cleanup.**

## And the ablation found a second class the layer does NOT catch

Running all 27 in both conditions surfaced **nine more arms that were red on
main for a different reason entirely** — stale anchors (ANCHOR-0), premises that
had expired, and two baselines held red by a stale FIXTURE:

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
  of service. Re-verified before moving it: a full `fail_open_check.py` run
  reports 10 live acceptances and **no stale ones**, so the removal really was
  a fix rather than a fail-open that moved.
* `run_law_phase2_session_sabotage_probe.py` arms 1 and 2, `session_gate_table_probe.py`
  arms 2 and 5, `run_sv_session_gate_sabotage_probe.py` arm 5 — five more stale
  anchors, all from the same cause in different files: a map grew a row
  (`law_deadlines` gained a trailing comma; `slabs` gained a `release` verb) or
  a query gained a header (`Prefer: count=exact`, 2026-09-24), and the arm
  quoted the old spelling. **The sv arm is the instructive one:** its anchor
  included the read's whole query line, so a header added for an unrelated
  truncation-disclosure fix silently disarmed a DEA-relevant gate-ordering
  control. Re-anchored on the branch's opening line only.
* `run_hover_audit_method_sabotage_probe.py` — baseline red on a stale FIXTURE,
  not a stale anchor: `tests/run_defect_register_probe.py`'s TRAP8 took "the
  last commit touching `.claude/claims/`" and assumed it was bookkeeping-only.
  Claims commits now routinely carry `docs/tier-a-reviews.json`, which is not in
  `BOOKKEEPING` (it is a real record, not a generated document), so the commit
  was MIXED, `--add` correctly declined to refuse it, and the arm failed **about
  its own fixture while reading as a defect in the guard**. The fixture now
  asks `is_bookkeeping_only()` itself over recent history — the predicate the
  arm exists to prove is wired — and says COULD NOT RUN if no such commit
  exists in the window.

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
   probe corpus has no runner, so **15 arms across 12 of the 27 probes** were
   unreliable — 6 malformed mutants, 7 stale anchors, 2 expired premises, and 2
   baselines held red by stale fixtures — and nothing was going to say so.
   Filed as an open-work row.
5. **A THIRD CLASS THE LAYER CANNOT SEE, stated because the count above would
   otherwise read as complete:** a mutant that PARSES and is caught for the
   wrong reason. `_parse_error` proves the mutant compiles; nothing proves the
   suite went red about the property the arm's name claims. Every one of the six
   rewrites here was re-read by hand for that, and hand-reading is not a check.

## A third finding, from running the platform's OWN control-guard checker after

`tools/sabotage_control_check.py` reported **1 UNGUARDED** control out of 83 —
`tests/run_claim_doc_freshness_probe.py`, written by this session the day
before. Its mutations edit an in-memory FIXTURE rather than a tracked file, so a
rename cannot reach them; the quiet failure is identical anyway. An anchor that
stops matching leaves the "mutated" text byte-identical to the clean one, the
checker under test correctly answers OK, and **the NEGATIVE arm reads that OK as
a pass**. Every mutation now asserts its anchor matches exactly once and that
the replacement changed something. **Re-measured: 83 of 83 guarded, 0
unguarded.**

Worth recording because of what it says about the practice: the ablation above
found what one layer catches, and a DIFFERENT existing checker immediately found
a defect in the probe written to hold the ablation's own fix. Neither could see
the other's finding.

## A fourth finding, and it is the corpus finding again one layer down

`run_hover_audit_method_sabotage_probe.py` was the one probe the repairs above
could not turn green, and the reason has nothing to do with hover auditing:
its subject suite calls `defect_register.py --check`, which **exits 1
platform-wide on ONE malformed record** (`094aed1fa42f`, cody, 2026-09-25) —
both its `contributing_factors` carry `factor`/`action` instead of the required
`kind`/`action_status`, and `found_by_session: cody` is refused because that
field is reserved for a hover instance name.

**One thing was fixed and the rest deliberately was not.** `app` read
`SAIRNSCAPE` against the known value `sairnscape` — one app counted as two
entities by every per-app figure in the file, a typo with exactly one correct
answer. The vocabulary fields were left alone: choosing `kind` and
`action_status` for somebody else's factors fabricates the judgement the field
exists to record.

**The class is the interesting part.** A single record failing a vocabulary
check takes down every consumer of the whole file — the same all-or-nothing
shape a conflict marker has. 289 good records are unusable because of one.
A per-record quarantine (report the bad row, keep checking the rest) would have
kept two probe suites in service, one of them the control on the hover
auditor's own method. Filed as an open-work row against the record's author.

## Numbering note

This landed as **discipline 12**, not 11: another session added a human-gated
auto-remediation convention within the same hour, and a rebase had to pick an
order. Both are on origin; mine renumbered. Recorded because the CLAUDE.md
pointer now says COUNT THE HEADINGS for exactly this reason.

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
