# Calibrating the standard vs recalibrating during use: which one this platform does

**2026-09-27, CC.** Methodology sweep prompted by a distinction leak-testing
equipment makes and this platform does not: **periodic calibration of the
reference standard** is a different job from **recalibration against drift
while the process is running**. A standard that was correct when it was set can
still drift out from under a process that keeps running against it.

`tools/probe_anchor_freshness.py` — wired earlier today — is a point-in-time
check. It catches an anchor that is *already* wrong. It says nothing about one
that goes wrong between runs. This sweep asks which other freshness tooling
shares that gap and what it costs.

**The answer turned out to be one layer further down than the question.** The
gap that has actually been costing findings is not drift *between* runs of an
instrument. It is that **nothing measures which probes any instrument is
pointed at**, and 4 of 99 were pointed at by nothing at all.

---

## 1. What was measured

Three passes, all mechanical, all re-runnable. Scripts are one-offs in a scratch
directory and are **not committed** — stated here rather than left to be
discovered, because an uncommitted script is not a standing check.

### Pass A — cadence: is the standard ever calibrated at all?

Every `tools/*.py` whose name carries `fresh|drift|stale|anchor|snapshot|reseat|recheck|ratchet`,
cross-referenced against `.claude/settings.json`, the push gate,
`report_only_checks.REGISTRY`, and `.githooks/`.

**20 freshness tools. 8 run automatically. 12 run only when somebody
remembers.**

| runs automatically | runs only on request |
|---|---|
| `citation_drift_hook.py` (PostToolUse) | `entitlement_freshness_check.py` |
| `hover_process_pass_freshness.py` | `git_discovery_anchoring_check.py` |
| `literal_drift_check.py` | `load_schema_snapshot.py` |
| `mutation_anchor_check.py` | `pinned_list_drift_check.py` |
| `ownership_evidence_drift.py` | `register_freshness_propose.py` |
| `probe_anchor_freshness.py` *(as of today)* | `review_ledger_reseat.py` |
| `register_freshness_check.py` | `sairn_claim_doc_freshness.py` |
| `schema_snapshot_freshness.py` | `sairn_stale_snapshot_scan.py` |
| | `session_recheck_coverage.py` |
| | `stale_row_sweep.py` |
| | `tiering_recheck.py` |
| | `verification_plan_staleness_check.py` |

A tool with no cadence has an **unbounded exposure window** no matter how good
its criteria are. Four of the twelve are proposers or installers where on-demand
is the right answer (`register_freshness_propose.py`, `review_ledger_reseat.py`,
`load_schema_snapshot.py`, `tiering_recheck.py` — all of them PROPOSE and must
not apply). The rest are detectors that only ever run when a dispatch remembers
to ask for them.

### Pass B — in-run re-check: is the standard re-read after the verdicts?

The exemplar already exists. `tools/guard_ablation.py` hashes its subject at the
start, **re-reads it at the end**, and printed, on a real run:

> `api/sd-data.js CHANGED DURING THIS RUN … the verdicts are valid for sha256
> b1cd55206c37; the LINE NUMBERS are not`

That is in-use recalibration, and it exists because a sweep was overlapped by an
edit and every line number came out silently off by one.

**Measured across 21 tools (the 20 above plus `guard_ablation.py` as a control):
exactly ONE has it.** A pattern search for end-of-run re-read language returned
four candidates; three were false positives — `register_freshness_propose.py`,
`sairn_stale_snapshot_scan.py` and `stale_row_sweep.py` all use "re-read" in
prose to mean *a human should re-read this row*, which is a different thing
entirely. Stated because a 4-hit search reported as 4 findings would have been
75% wrong.

**Runtime, measured rather than assumed** (the exposure window inside one run):

| tool | run |
|---|---|
| `ownership_evidence_drift.py` | 0.3 s |
| `literal_drift_check.py` | 0.4 s |
| `hover_process_pass_freshness.py` | 0.6 s |
| `probe_anchor_freshness.py` | 1.9 s |
| `mutation_anchor_check.py` | 3.9 s *(exit 2, COULD NOT RUN)* |
| `register_freshness_check.py` | 19.8 s |
| `schema_snapshot_freshness.py` | 25.7 s |

**In-run drift is a real window for the last two and not for the rest.** Five
clones push to this branch concurrently; this session alone was rebased five
times in a few hours. A 20–26 second read of documents that four clones edit is
not atomic with respect to that. Neither re-reads its subject at the end, so a
push landing mid-run produces a verdict about a state that no longer exists and
nothing says so.

**`mutation_anchor_check.py` is wired and currently exits 2, COULD NOT RUN** —
several arms' targets do not resolve. A cadenced checker sitting permanently in
could-not-run is the third state working exactly as designed and nobody reading
it.

### Pass C — coverage: what is each instrument pointed at?

This is the pass that found the real gap, and it was not the question asked.

`ast`-parsed all 99 probe files and classified by **the shape of the call**,
because `arm(label, suite, old, new)` and `arm(label, [(SUBJECT, old, new)])`
are different shapes wearing the same name:

| convention | probes | checker |
|---|---|---|
| a module-level `MUTATIONS` list | **85** | `mutation_anchor_check.py` (wired) |
| `arm(…, [(SUBJECT, old, new)])` | **10** | `probe_anchor_freshness.py` (wired today) |
| `arm(label, suite, old, new)` | **4 → 2 real** | **nothing** |

**The overlap between the first two populations is ZERO.** Two anchor-freshness
checkers have existed side by side, each covering a disjoint set, neither aware
of the other. `mutation_anchor_check.py` has been wired and running the whole
time — and **all three probes that died silently this week were in the other
population**, which is precisely why a working, cadenced, correct checker could
not have caught any of them.

The third convention is `tests/sairnbiz_fault_probe.py` and
`tests/sairnvet_fault_probe.py` — the second of which arms a controlled-substance
register. Both carry the same `once()` uniqueness guard internally and **both
pass today**, so their anchors are fine. What was missing is anything that would
say so on a cadence, or say when they stopped being fine, before somebody ran a
minutes-long probe.

*(A first pass counted 4 probes in convention 3. Two were false — a seven-parameter
fixture helper and an assertion helper `def arm(name, ok, detail='')` — caught by
reading the helper's declared parameter names rather than counting string
literals. See below.)*

---

## 2. What was changed

`probe_anchor_freshness.py` now reads convention 3 as well. **100 → 114 anchors,
all agreeing with the rule that applies to them.**

**The shape is read off the helper's own declaration, never guessed.** A helper
whose signature literally names `old` and `new` is a mutation helper and their
positions say which arguments to read. One whose signature does not is left
alone however many string literals its calls carry.

**And the obvious discriminator is circular and is refused by name:** "treat it
as an anchor if the subject contains it" can never report an anchor as VANISHED,
because vanishing is exactly the case where the subject does not contain it. A
rule that requires a match in order to look reports every healthy anchor and no
broken one.

Four selftest arms, both directions, including a CONTROL that an assertion
helper of the same name contributes **no** anchors — without which every
assertion in every probe named `arm()` becomes a phantom anchor and the VANISHED
list fills with strings that were never anchors.

One probe is now **reported as NOT FULLY SCANNED** rather than silently absent:
`tests/run_adversarial_prompt_corpus_probe.py`, 3 unresolvable literals. That is
the tool's own promised behaviour working — an unreadable anchor is a stated gap,
not a smaller denominator.

---

## 3. What carries real consequence if it drifts silently in between

Ranked by what is BELIEVED TRUE during the window, which is the only ranking that
matters for a silent failure. The consequence column is a judgement, and is
labelled as one.

| tool | cadence | what is believed during the window | tier |
|---|---|---|---|
| `mutation_anchor_check.py` | wired, **exit 2 today** | that 85 probes' anchors are verified. They are not — the tool cannot resolve several targets and says so, in output nobody reads | **HIGH** |
| `schema_snapshot_freshness.py` | wired, 25.7 s | that `db/schema_snapshot.json` describes the database this repo builds. Every gate reasoning about columns rests on it | **HIGH** |
| `entitlement_freshness_check.py` | **none** | that something in this repo can REVOKE an entitlement it granted. Its own docstring asks that question; nothing asks it on a cadence | **HIGH** |
| `session_recheck_coverage.py` | **none** | that a session gate asks again rather than checking once at the door | **HIGH** |
| `register_freshness_check.py` | wired, 19.8 s | that every register cell's citation still resolves. Already known to have 10 dead shas needing a human read each | MODERATE |
| `pinned_list_drift_check.py` | **none** | that a hand-written list still matches the register it was pinned to. The pinned-list-drift defect has bitten this platform three times | MODERATE |
| `stale_row_sweep.py` | **none** | that an open work-index row's subject has not moved underneath it. Correctly a re-read REQUEST, not a closure — but only if somebody runs it | MODERATE |
| `verification_plan_staleness_check.py` | **none** | that the verification plan describes what is actually done | MODERATE |
| `probe_anchor_freshness.py` | wired today, 1.9 s | that 114 anchors still match. Fast enough that in-run drift is not a window; the gap was cadence, and it is closed | LOW (now) |

---

## 4. The finding, stated once

**This platform calibrates its standards and does not recalibrate during use —
but that is the second-order problem.** The first-order one is that **no
instrument's COVERAGE is measured**, so an instrument can be perfectly
calibrated, perfectly cadenced, and pointed at the wrong 85 of 99 things, and
every report it produces reads as a clean bill for the whole population.

`mutation_anchor_check.py` was wired, running, and correct about the 85 probes
it could see, while three probes in the other 14 were dead. Nothing was broken.
Nothing was stale. The number of things being checked was simply never compared
against the number of things there are.

**The generalisable rule:** a freshness instrument must publish its
**denominator** — how many candidates exist, how many it can read, and how many
it cannot — and the ones it cannot read must be NAMED, not absent. This tool now
does the last part for unresolvable anchors and does **not** do the first: it
reports 114 anchors without saying 114 out of what.

---

## 5. What this sweep did NOT do

- **The three one-off scripts are not committed**, so none of Pass A, B or C is
  a standing check. The coverage question that produced the main finding will
  not be asked again unless somebody asks it.
- **`probe_anchor_freshness.py` still reports no denominator.** It says 114
  anchors agree; it does not say how many probe files declare anchors in a form
  it cannot read. That is the exact gap named in section 4 and it is open.
- **In-run re-checking was not added to the two tools that need it.**
  `schema_snapshot_freshness.py` (25.7 s) and `register_freshness_check.py`
  (19.8 s) still produce verdicts against a subject they never re-read. The fix
  is `guard_ablation.py`'s and is about ten lines each; both are outside this
  session's declared file set.
- **`mutation_anchor_check.py`'s exit 2 was not resolved.** It needs its
  unresolvable targets read one at a time, which is a judgement per arm.
- **The 12 uncadenced tools were not wired.** Four of them correctly should not
  be (proposers and installers). The other eight are a promotion decision each,
  with a cost measured per tool, and promoting eight checkers as a rider on a
  methodology sweep is how a push gate becomes something people turn off.
- **No claim is made that convention 3 is the last convention.** Three were
  found by looking; a fourth would be invisible the same way the third was.
