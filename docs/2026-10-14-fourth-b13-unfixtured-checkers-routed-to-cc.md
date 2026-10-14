# ROUTED TO cc — 613 checkers with no bad-input fixture, and the SPEC for the gate that would refuse them — 2026-10-14, fourth b13

**`tools/` is cc's directory and NOTHING UNDER IT WAS EDITED.** This document
is the whole of my change: an inventory produced by one command, and a
specification. The check it specifies is not built here.

**Why it exists:** b12 wrote the rule *every checker ships with a deliberately
bad input fixture proving it fails closed* into `docs/METHODOLOGY.md` and said
in the same breath that **nothing mechanises it**. A rule nothing measures is a
sentence. This is the measurement, and the spec for the thing that would make
it stick.

---

## 1. THE COMMAND, AND ITS OWN CRITERIA LOCK

```
CMD python scratchpad/unfixtured_b13.py --fixtures        ->  exit 0
  ok   LOCKED         -> LOCKED
  ok   HAPPY-PATH     -> HAPPY-PATH
  ok   NO-FIXTURE     -> NO-FIXTURE
  ok   NOT-A-CHECKER  -> NOT-A-CHECKER
  unfixtured_b13 --fixtures: 4 arm(s), 0 failing
  ARM 2 IS THE BAD INPUT: a fixture arm that proves only the happy path must
  NOT be credited as locked.
```

**The inventory tool is itself locked against a deliberately bad input**, which
is the rule applied to the tool that measures the rule. Arm 2 is the one that
matters: a file carrying a `--fixtures` arm whose every assertion is a *pass*
must not be counted as protected.

```
CMD python scratchpad/unfixtured_b13.py                   ->  exit 1
CHECKER FIXTURE INVENTORY -- 1024 tracked .py/.js under tools + tests

  LOCKED           206
  LOCKED-BY-PROBE  149
  HAPPY-PATH         6
  NO-FIXTURE       607
  NOT-A-CHECKER     56
  COULD-NOT-READ     0

  CHECKERS (can refuse)           968
  WITHOUT A FAIL-CLOSED FIXTURE   613   (63% of checkers)

BY DIRECTORY, unfixtured checkers:
  tools      52
  tests     561
```

### How the population is defined, so the number is reproducible rather than mine

* **A CHECKER** is a tracked `.py`/`.js` under `tools/` or `tests/` whose source
  contains a **non-zero process exit**. A program that cannot refuse cannot
  fail closed; 56 such files are counted separately as `NOT-A-CHECKER` rather
  than quietly dropped. **Name is not the test** — `reb.py` is a checker and
  does not say so.
* **LOCKED** — a fixture arm exists *and* at least one arm expects a refusal.
* **LOCKED-BY-PROBE** — **149 of them, and crediting this was the difference
  between an honest list and an alarming one.** A `tools/` checker whose
  bad-input fixture lives in `tests/run_<tool>_probe.py` is locked; it just
  does not carry the arm in-file. Without this rule the unfixtured count would
  have read **762**.
* **HAPPY-PATH** — a fixture arm with no refusal expectation anywhere.
  **Sharper than NO-FIXTURE, not softer:** it prints a criteria-lock line in
  its own output, so a reader concludes the guard is tested.
* The refusal-expectation pattern is **deliberately broad** (`want 1`, `-> 2`,
  `EXIT 1`, `BAD INPUT`, `must refuse`, `is a finding`, …) and therefore errs
  toward **crediting** a checker. **613 is a floor, never an inflated figure.**

### What this inventory does NOT say

* **It does not say the 613 are wrong.** It says nothing has ever shown them
  refusing. That is the whole claim.
* **It does not read semantics.** A fixture arm that asserts `want 1` against a
  trivially-wrong input still counts as locked here. This finds absence, not
  weakness.
* **It cannot see a fixture that lives in a `tests/` file naming the tool only
  indirectly** — a probe that shells out via a variable is missed, and that
  miss makes the list longer, not shorter.
* **The `tests/` 561 is reported, not routed.** Requiring a *probe* to carry
  its own bad-input probe is the control-pair question
  `tools/sabotage_control_check.py` already owns; the gate specified below is
  scoped to `tools/`.

---

## 2. THE 52 `tools/` CHECKERS WITH NO FAIL-CLOSED FIXTURE — the routable list, in full

**HAPPY-PATH (2) — a fixture arm that has never been seen to refuse:**

```
tools/clone_health_check.py
tools/independence_check.py
```

**THE FIRST RUN OF THIS INVENTORY PUT FIVE FILES IN THAT BUCKET AND THREE WERE
FALSE POSITIVES — said here because it is the measurement's own error bar.**
`tools/digest_lint.py`, `tools/suite_override_consistency.py` and
`tools/tool_owner_map.py` all DO assert a refusal; they write it as a fixture
**tuple** rather than as prose. `digest_lint.py:114` reads
`('over the word ceiling', _GOOD + ('filler ' * (MAX_WORDS + 10)), 1)` and
`:130` asserts `hit == want_findings`, which is a bad-input arm by any
reasonable reading. The pattern now recognises `want_<x>` and a trailing
`, 1)` tuple element, which moved 5 files from unfixtured to LOCKED — and
**that is the direction a mis-calibrated pattern must err in**, because the
cost of over-crediting is a shorter list and the cost of under-crediting is
somebody being sent to write a fixture that already exists.

**NO-FIXTURE (50) — no fixture arm at all:**

```
tools/accepted_risk_scan.py              tools/licence_recoverability_check.py
tools/audit_licence.py                   tools/mech_panels_live_check.py
tools/bare_run_writers.py                tools/outline.py
tools/blob_overrides_column_scan.py      tools/purpose_expired_measure.py
tools/cleanup_residue_check.py           tools/reservation_lock_invariants.js
tools/defect_budget_gate.py              tools/resource_reachability_check.py
tools/extract_panels.py                  tools/run_tlc.py
tools/fail_open_scan.py                  tools/sairn_ai_fact_scan.py
tools/gen_ma_calendar.py                 tools/sairn_dead_function_sweep.py
tools/gen_mn_calendar.py                 tools/sairn_reachability_probe.py
tools/gen_mn_seed.py                     tools/sairn_self_state.py
tools/gen_mo_calendar.py                 tools/sairn_source_fetch.py
tools/gen_nj_calendar.py                 tools/sairn_stale_snapshot_scan.py
tools/gen_nv_calendar.py                 tools/sairnlaw_citation_audit.py
tools/gen_ok_calendar.py                 tools/scratch-archive/build_index.py
tools/gen_or_calendar.py                 tools/scratch-archive/triage86.py
tools/gen_sc_calendar.py                 tools/second_pass_coverage_scan.py
tools/gen_ut_calendar.py                 tools/service_role_tier_a_gate_check.py
tools/gen_va_calendar.py                 tools/strict_args_harness.js
tools/gh_verify.py                       tools/text_gate_literal_sweep.py
tools/git_discovery_anchoring_check.py   tools/tier_a_bypass_check.py
tools/hank_session_start_check.py        tools/verify_review_gates.py
tools/hover_eqa_escalation.py            tools/wait_for.py
tools/hover_self_health_shim.py
tools/html_script_check.py
tools/law_billing_code_trim_live_probe.py
tools/leg_session_gate_live_probe.py
```

**THE FOUR IN THAT LIST I WOULD READ FIRST, and the reason is their subject,
not their code:**

1. **`tools/fail_open_scan.py`** — a scanner for fail-open code that has never
   been shown to refuse a fail-open input. If this one is wrong, it is wrong
   about the exact defect class b12 was about.
2. **`tools/licence_recoverability_check.py`** — the guard behind the
   *two end states are safe and only two* rule (PR §3.4). A silent pass here
   is a credential row nobody can recover.
3. **`tools/tier_a_bypass_check.py`** and
   **`tools/service_role_tier_a_gate_check.py`** — Tier A is the criticality
   tier where a wrong answer reaches a person.

**THE 11 `gen_*_calendar/seed` ENTRIES ARE A DIFFERENT SHAPE and should not be
treated as the other 39.** `docs/METHODOLOGY.md` already says a generator's
correctness lock is *"it refuses to write when its inputs disagree"*, which is
the stronger form. The right fixture for a generator is therefore **a
disagreeing-input arm asserting it writes nothing**, not a bad-input arm
asserting a verdict. Counted here because they *can* exit non-zero; flagged
separately so nobody bolts the wrong kind of arm onto eleven files.

---

## 3. SPEC — `tools/fixture_lock_check.py`

### 3.1 What it does

```
python tools/fixture_lock_check.py                 # report every unfixtured tools/ checker
python tools/fixture_lock_check.py --changed-only  # only files in the outgoing push
python tools/fixture_lock_check.py --fixtures      # its own criteria lock
python tools/fixture_lock_check.py --json
```

| exit | meaning |
|---:|---|
| **0** | every checker in scope is LOCKED or LOCKED-BY-PROBE, **or** carries a registered waiver (§3.4) |
| **1** | at least one checker in scope has no fail-closed fixture |
| **2** | **COULD NOT CHECK** — `git ls-files` failed, a file is unreadable, or the waiver register is absent or unparseable. **Never folded into 0 or 1** (PR §1.11) |

### 3.2 The classification is the one above, and it must be ONE function

`classify(source) -> LOCKED | HAPPY-PATH | NO-FIXTURE | NOT-A-CHECKER` plus
`probe_locks(rel, tests_sources) -> tests/… | None`. Both pure, both fed only
text, so both are lockable by fixtures without touching a repo. The prototype
in `scratchpad/unfixtured_b13.py` is **not** a draft to copy blindly — its
`EXIT_NONZERO` pattern is a regex over source and will mis-read a checker that
exits through a helper. **Specified, not hidden:** that is a known
false-NOT-A-CHECKER direction, which makes the list shorter than the truth.

### 3.3 WIRE IT `--changed-only` FIRST, AND NOT AS A BLANKET GATE

**A gate that fails on 52 pre-existing files on its first run is a gate
somebody turns off within the hour** — and this platform already has the
mechanism for that (`tools/gate_skip.py`), which means the realistic outcome of
over-reaching here is a permanent scoped exemption, not 57 fixtures.

So:

1. **Phase 1 — report-only, whole repo.** One batch. Nobody's push blocks.
2. **Phase 2 — `--changed-only`, blocking.** A checker **added or modified** in
   the outgoing push must be LOCKED or LOCKED-BY-PROBE or waived. New debt
   stops accruing; the 52 are untouched.
3. **Phase 3 — the backlog, by criticality, not alphabetically.** The four
   named in §2 first.

### 3.4 The waiver register, because the alternative is a lie

`docs/fixture-lock-waivers.json`, one row per file: `path`, `why` (≥ 80
characters), `by`, `on`, and `expires_on` (**required**, ≤ 90 days out). The
check **refuses an expired waiver** and refuses a waiver whose `path` no longer
exists. Without an expiry this register becomes the permanent record of the
rule not applying — which is what `docs/by-design-register.json` and the
accepted-risk register were both built to stop being.

### 3.5 THE CRITERIA LOCK — 12 arms, and four of them exist to stop it over-refusing

| # | input | expected |
|---:|---|---|
| 1 | a checker with a fixture arm asserting `want 1` | **LOCKED** |
| 2 | **BAD INPUT:** a fixture arm whose every assertion is a pass | **HAPPY-PATH**, counted as unfixtured |
| 3 | a checker with no fixture arm | **NO-FIXTURE** |
| 4 | a file with no non-zero exit at all | **NOT-A-CHECKER**, not counted |
| 5 | a `tools/` checker named by a `tests/` probe that expects a refusal | **LOCKED-BY-PROBE** |
| 6 | the same, where the probe expects **no** refusal | **NOT** locked |
| 7 | `--changed-only` with an unfixtured file **outside** the change set | **exit 0** |
| 8 | `--changed-only` with an unfixtured file **inside** it | **exit 1**, file named |
| 9 | a valid, unexpired waiver for that file | **exit 0** |
| 10 | the same waiver with `expires_on` in the past | **exit 1**, expiry named |
| 11 | the waiver register absent or unparseable | **exit 2**, not 0 and not 1 |
| 12 | **CONTROL: the repo as it stands, `--changed-only`, empty change set** | **exit 0** |

**Arms 4, 6, 7 and 12 are the over-refusal guards.** A check that refuses a
generator, or a clean push, or the repo it was written for, has moved the defect
rather than closed it.

### 3.6 What it must NOT do

* **It must not judge a fixture's quality.** `want 1` against a trivial input
  passes. This is a presence check and says so in its own banner.
* **It must not write.** Not the waiver register, not a fixture stub. A tool
  that generates the fixture that satisfies it is the
  detector-blesses-its-own-fix shape.
* **It must not be `SAIRN_SKIP`-able blanket-wide** once Phase 2 lands — per
  `docs/2026-10-13-per-gate-skip-design.md`, a skip is for a gate whose *input*
  is temporarily wrong, and "I did not write the fixture" is not that.

---

## WHAT I AM ASKING FOR

Either `tools/fixture_lock_check.py` to this spec, or a `NOT_PROMOTED` entry
saying why the rule stays unmechanised — **with the reason**. Both are answers.
What is not an answer is the current state, in which
`docs/METHODOLOGY.md` carries the rule and **613 of 968 checkers, 63%, have
never been seen to refuse anything.**
