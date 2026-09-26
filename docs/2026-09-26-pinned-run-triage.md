# Triage of the 56-failure pinned run

**2026-09-26 (Cody).** The first full-suite run this platform has produced that
is attributable to a single commit and whose output was captured whole:
`tools/run_all_tests.py --pinned --out`, detached worktree at **`fec9e5d9`**,
**56 failing files, 56 of 56 names captured**.

Previous attempts reported 59 failures with only 42 names surviving a `tail`.
**56 is not an improvement on 59** — different commit, different tree, and no
like-for-like comparison exists.

---

## 1. The method, because the number alone is not the finding

All 56 were re-run **in the live clone on a clean tree** and the two results
diffed. A failure present in both is a platform failure. A failure present only
in the pinned worktree is an artefact of how the run was performed — which
matters twice over, because `--pinned` is a tool I shipped yesterday and this is
its first real use.

| | count |
|---|---|
| **fail in BOTH** — real, pre-existing, not caused by pinning | **46** |
| **fail ONLY under `--pinned`** — artefacts of the run | **9** |
| **exit 2, COULD NOT RUN** — a third state, not a failure | **1** |

---

## 2. THE NINE ARTEFACTS — and they are two different causes, not one

This is the load-bearing finding. `--pinned` does not merely test an older tree;
**for a specific class of test it cannot produce a valid result at all.**

### 2.1 STALE SNAPSHOT — 1 file

| file | cause |
|---|---|
| `tests/sf_operator_payee_review_probe.js` | **fixed after the pin.** One commit touches it between `fec9e5d9` and HEAD (`c87aeeda`, which repaired it from asserting nothing). The worktree holds the broken version, so it fails there and passes in the clone. |

**Not an artefact of pinning — an artefact of pinning to a commit that predates
a fix.** Exactly what `--pinned` is supposed to do, behaving correctly.

> **RESOLVED 2026-09-26, LATER THE SAME DAY, AND §2.2 BELOW WAS WRONG.**
> Fixed in `50e05934`. Only **ONE** of these is pinning-incompatible; the other
> seven are not, and the cause is a single missing file.
>
> They die on `sairn_session_identity.NoIdentity: THIS CLONE IS NOT PROVISIONED
> — <git-dir>/sairn-session does not exist`, because **a git worktree has its own
> git dir** and the per-clone identity marker lives in `.git/`. Copying the
> clone's marker in makes them pass: measured `rc=1` before and `rc=0` after on
> `run_coding_rule_channel_probe.py` and `run_review_gate_validate_probe.py`, and
> then on `run_registry_claim_probe.py`, `run_released_visibility_probe.py` and
> `refspec_and_override_probe.py` in a provisioned worktree. `--pinned` now
> provisions before running and refuses (exit 2) if the clone itself has no
> identity to copy.
>
> **`stale_row_sweep_control.py` is neither** — it times out past 280s in the
> clone AND in a worktree. Load-sensitive, not location-sensitive.
>
> **THE DECLARED SET IS ONE ENTRY:** `run_selftest_independence_probe.py`, via
> `tools/nhi_register.py --selftest`, which **enumerates sibling clones beside
> the repository directory**. A worktree in a temp dir has none, so the
> enumeration finds zero and the probe correctly refuses. Clone `rc=0`, worktree
> `rc=2`.
>
> **HAD I ACTED ON §2.2 AS WRITTEN, SIX FILES WOULD HAVE STOPPED BEING TESTED
> UNDER `--pinned` FOREVER, for a defect that takes one file copy to fix.** The
> hypothesis was plausible, specific, and wrong, and the thing that caught it was
> re-running in a worktree at HEAD rather than at the pinned commit — which
> separated "old code" from "wrong environment". §2.2 is left below exactly as it
> stood, because the reasoning is the reasoning and editing it silently would
> hide that a triage conclusion needed its own control too.

### 2.2 PINNING-INCOMPATIBLE — 8 files, and this is a real limitation of the tool

The other eight were **not** changed after the pin (0 commits each), so a stale
snapshot cannot explain them. Reproduced directly:

```
tests/claims/run_released_visibility_probe.py   clone=0   worktree=1
    FAIL  the real CLI still exits 0 on a clear check
    FAIL  and still prints CLEAR
```

These probes drive the **live repository state** — `sairn_claim.py` against
`.claude/claims/`, git refs, `origin/main`, `merge-base`. A detached worktree at
an old commit carries *old claim files* while the shared registry outside the
clone is current, and its git context is not the clone's. `refspec_and_override_probe.py`
alone references git/worktree/origin concepts **20 times**.

**So the answer is not "these tests are flaky."** It is:

> **`--pinned` is valid for tests that read the tree, and invalid for tests
> whose subject IS the repository's live state.** A pinned full-suite run will
> always report those as failures, and they are not failures.

**THIS IS A DEFECT IN THE TOOL I SHIPPED, AND IT IS THE KIND THAT MATTERS:**
`--pinned` was added so a long run could be attributed to one commit. It does
that — and it silently converts one class of passing test into a failure, with
nothing in the output saying so. A reader of the 56 would have spent time on
eight non-problems.

**Not fixed here.** The fix is a declared exclusion set with a written reason per
entry — the `CONCURRENCY_SENSITIVE` convention — and it needs the full set
identified rather than the eight this run happened to surface. Recorded as the
next piece of work on that tool, because a tool that reports eight false
failures per run is a tool that gets its output ignored.

---

## 3. THE COULD-NOT-RUN — 1 file

`tests/law_reconcile_role_vocab_check.py` exits **2** in both environments.
Exit 2 is this platform's "could not tell", and it is correctly **not** a
failure. It is also not a pass, and it is not counted in either column above.

---

## 4. THE 46 REAL FAILURES

Pre-existing, present in the clone on a clean tree, **not caused by pinning and
not caused by anything in this session.** Nine of them are the same nine that
appeared to "catch" the ablation mutation in
`docs/2026-09-26-ablation-gated-resource-header.md` — they were red all along,
which is how they produced a false positive there.

Grouped by what the name says they are:

| group | n | note |
|---|---|---|
| `run_*_probe.py` — tool/meta probes | ~24 | probes ABOUT checkers, not about apps |
| app-behaviour suites (`ai_*`, `customer_delete_*`, `stonedesk_server_backup`, `sairnscape_memory`, …) | ~12 | the ones that would matter to a customer |
| `*_fault_probe.py` / `*_control.py` | ~6 | sabotage and control harnesses |
| `seam_check/*`, `push_gate/*`, `sql_preflight/*` | 6 | gate self-checks |

**NO ROOT CAUSE IS CLAIMED FOR THE 46 HERE, and that is deliberate rather than
lazy.** Root-causing 46 suites is a work item, not a paragraph, and this document
exists to say which failures are worth opening — the honest output of a triage is
a partition, not a diagnosis of every partition member. Three things about them
are established:

1. **They are not new.** The active-work log recorded 17 failing on 2026-09-16/17
   against a smaller suite; the suite has since grown to 747 files. Whether 46 is
   growth, drift, or both is unmeasured.
2. **They are not mine.** Every one fails on a tree with none of this session's
   changes.
3. **Nine of them actively produce false positives** in other measurements, as
   §4's first paragraph shows. That is the strongest argument for fixing them:
   a red suite is not inert, it corrupts the next experiment that touches it.

---

## 5. What changed about how the suite should be run

- **`--out` works and should always be used.** 56 of 56 names captured versus 42
  of 59 through a `tail`.
- **`--pinned` is right for attribution and wrong for eight known tests.** Until
  §2.2's exclusion set exists, a pinned run's failure list must be diffed against
  a clone run before any of it is believed. **That diff is the method of this
  document and it should be the standing method.**
- **A baseline is not optional.** The ablation in the companion document produced
  a completely wrong verdict for want of one.

---

## 6. Decay

`fec9e5d9` for the pinned run, HEAD at triage time for the clone run, both
2026-09-26. The 56 will move with the next push from any of five clones.
**Re-derive the partition before acting on any single name** — and in particular
re-check §2.2's eight, because the moment an exclusion set exists they stop being
artefacts and the count changes.
