# The 54 checkers with no known-positive on their own run -- triaged by owner

**2026-09-29 (Cody).** `tools/checker_selftest_check.py` asks every tool in the
report-only registry one question: *on the run that just said CLEAN, did you
demonstrate -- in your own output -- that you still report a known-positive?* It
found **54 of 67** could not. This document routes them.

## What "owner" means here, and why it is not `git log`

**Every commit in this repository carries one git identity.** `git log --format=%an`
returns the same name for every file, so it cannot answer "which agent owns
this". The only session attribution the repo has is the **claim record**: each
claim names the files it takes. So ownership below is *the most recent session
that ever named this file in a claim*, parsed out of `.claude/claims/*.json`.

**That is an approximation and it is stated as one.** A session that edited a
file without naming it in a claim does not appear. A file nobody has ever claimed
shows as NEVER CLAIMED, which means *unrouted*, not *unowned by anyone*.

**No file in this list is under a LIVE claim** at the time of writing, so none of
the routing below is blocked on a lock -- it is blocked on knowing who has the
context to write good fixtures, which is a different thing and the reason this is
a routing document rather than a to-do list I worked through.

---

## FIXED HERE -- 4 of the 5 that were mine

| tool | was | fix |
|---|---|---|
| `probe_anchor_freshness.py` | FLAG-ONLY | its `selftest()` (20 arms) now runs on the **default path**, prints `self-test: 20/20`, and a failing lock is **exit 2** -- an anchor-freshness figure from criteria that cannot classify a hand-built case is not a measurement |
| `mutation_anchor_check.py` | NO FIXTURE SET | 6-case lock on `mutates_repo_path`, both directions, including **the two false positives its earlier versions actually shipped** -- a temp-path write (v1 flagged six of those) and the unsafe pattern appearing as a **quoted fixture string** (v2 flagged this tool's own probe). One case locks a known **false negative** rather than leaving it to be found |
| `criticality_tier_check.py` | NO FIXTURE SET | 6-case lock on `cells` and `asserts_access_control`: the **escaped pipe** that this file's own index row tripped, an uncited gate claim, the same claim **with** a citation, and a **quoted** old sentence, which is the opposite of asserting one |
| `metamorphic_check.py` | NO FIXTURE SET | **nothing -- the finding was wrong.** See below |

### `metamorphic_check.py` was a false negative of my own checker

It has one of the best fixture locks in the repo: `blind_lock()` writes a
SENSITIVE and a ROBUST fixture, requires every SAME relation to catch the first
and none to catch the second, runs on the default path, prints `blind lock:
LOCKED (N fixture comparisons)`, and **refuses the measurement** when unlocked.

It was invisible because the function is called `blind_lock` and my detection was
a hand-kept name list -- the weakness the tool's own header already admitted to.
A runner is now **also** any function reading a module-level constant whose name
says it holds hand-built cases (`FIXTURE`, `CASES`, `GOLDEN`, `KNOWN_BAD`,
`KNOWN_GOOD`; `LOCK` deliberately excluded as too generic).

**Measured before widening: exactly ONE of the 46 carried such a constant**, so
this widens the detector by one and not by forty. The first fixture run of the
widening caught it over-matching a scalar (`CONFIG_CASES = 3`), so the constant
must now hold **data** -- a list, tuple, dict or string. Both directions locked
as fixtures.

### NOT fixed, and the reason is a boundary, not effort

| tool | why |
|---|---|
| `hover_separation_audit.py` | It is the **detector of the build-agent / hover-auditor separation**. A build agent writing the known-positive for the very check that watches build agents is *the detector blessing its own fix*, one level up -- the shape discipline 11 exists for. Needs an independent owner: the hover auditor, or a build agent other than me. |

---

## ROUTED -- 50 remaining, by owner

### fourth — 7

| tool | last claimed | verdict |
|---|---|---|
| `tools/defect_budget_policy.py` | 170h ago | NO FIXTURE SET |
| `tools/defect_register.py` | 34h ago | NO FIXTURE SET |
| `tools/hover_process_pass_freshness.py` | 169h ago | FLAG-ONLY |
| `tools/install_git_hooks.py` | 119h ago | NO FIXTURE SET |
| `tools/register_feed_gate.py` | 33h ago | FLAG-ONLY |
| `tools/tooling_inventory.py` | 15h ago | NO FIXTURE SET |
| `tools/verification_owed_report.py` | 31h ago | NO FIXTURE SET |

### cc — 2

| tool | last claimed | verdict |
|---|---|---|
| `tools/checker_denominator.py` | 16h ago | FLAG-ONLY |
| `tools/claim_activity_check.py` | 25h ago | FLAG-ONLY |

### hank — 1

| tool | last claimed | verdict |
|---|---|---|
| `tools/fact_sheet_regenerates.py` | 25h ago | NO FIXTURE SET |

### NEVER CLAIMED -- 39, and these need an owner before they need fixtures

No session has ever named these in a claim. They are **unrouted**, not unowned:
whoever wrote them did it without declaring the file, so the record cannot say
who. A chat session assigning these should pick by who has context on the
subject, not by this list's order.

| tool | verdict |
|---|---|
| `tools/accepted_risk_expiry_audit.py` | FLAG-ONLY |
| `tools/ai_action_approval_audit.py` | FLAG-ONLY |
| `tools/bypassed_constant_check.py` | NO FIXTURE SET |
| `tools/checkblocks.py` | NO FIXTURE SET |
| `tools/cleanup_confirm_check.py` | NO FIXTURE SET |
| `tools/comment_quote_check.py` | NO FIXTURE SET |
| `tools/comment_sensitivity_check.py` | NO FIXTURE SET |
| `tools/committer_identity_check.py` | NO FIXTURE SET |
| `tools/control_char_check.py` | NO FIXTURE SET |
| `tools/discarded_verdict_check.py` | NO FIXTURE SET |
| `tools/discarded_verdict_crossfile.py` | NO FIXTURE SET |
| `tools/div_balance_check.py` | NO FIXTURE SET |
| `tools/duplicate_global_check.py` | NO FIXTURE SET |
| `tools/eaten_substitution_check.py` | NO FIXTURE SET |
| `tools/export_coverage_check.py` | NO FIXTURE SET |
| `tools/fail_open_check.py` | NO FIXTURE SET |
| `tools/gate_column_check.py` | NO FIXTURE SET |
| `tools/index_duplicate_check.py` | NO FIXTURE SET |
| `tools/key_collision_check.py` | NO FIXTURE SET |
| `tools/literal_drift_check.py` | NO FIXTURE SET |
| `tools/master_plan.py` | NO FIXTURE SET |
| `tools/md_table_check.py` | NO FIXTURE SET |
| `tools/nav_panel_check.py` | NO FIXTURE SET |
| `tools/npm_audit_check.py` | NO FIXTURE SET |
| `tools/orphan_register_check.py` | NO FIXTURE SET |
| `tools/overrun_inversion_scan.py` | FLAG-ONLY |
| `tools/ownership_evidence_drift.py` | NO FIXTURE SET |
| `tools/panel_nesting_check.py` | NO FIXTURE SET |
| `tools/removal_path_check.py` | NO FIXTURE SET |
| `tools/sairn_dead_button_audit.py` | NO FIXTURE SET |
| `tools/sairn_strict_args_check.py` | NO FIXTURE SET |
| `tools/schema_snapshot_freshness.py` | NO FIXTURE SET |
| `tools/soup_register_check.py` | NO FIXTURE SET |
| `tools/subprocess_decode_check.py` | NO FIXTURE SET |
| `tools/temporary_state_check.py` | NO FIXTURE SET |
| `tools/traceability_matrix.py` | NO FIXTURE SET |
| `tools/truthy_sum_check.py` | NO FIXTURE SET |
| `tools/vercel_config_check.py` | NO FIXTURE SET |
| `tools/write_without_readback_check.py` | NO FIXTURE SET |

---

## The two repair shapes, so nobody has to re-derive them

**FLAG-ONLY -> PUBLISHED** is small. The fixture set already exists; move the
call onto the default path and print one line. `probe_anchor_freshness.py` is the
worked example: six lines, and the failing case becomes exit 2 rather than a
number nobody can trust.

**NO FIXTURE SET -> PUBLISHED** is real work, and it is the work that matters.
The fixture set has to contain at least one case the tool must **report** and at
least one it must stay **silent** on. A lock of only-positives is satisfied by a
tool that reports everything; a lock of only-negatives by a tool that reports
nothing -- and the second is the failure this whole exercise is about.

**What this does NOT measure, stated so nobody over-reads the number:** whether
the fixtures are any *good*. A fixture set of one trivially-true case clears
`checker_selftest_check.py`. That is `tools/sabotage_control_check.py`'s
question, and a tool moving from NO FIXTURE SET to PRINTED is the beginning of
the answer, not the end of it.

**Re-run the figures, do not quote them from here.**

    python tools/checker_selftest_check.py --all
