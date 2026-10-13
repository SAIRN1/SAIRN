# `tools/bare_run_write_check.py` repo-wide — hank b5, 2026-10-13

Run in an ISOLATED SCRATCH CLONE (`git clone --local --no-hardlinks`), never in
the live clone, because the tool runs every tool it finds. Full log:
`docs/hank-evidence/b5_bare_run_write_check.out`.

| | |
|---|---|
| tools swept | **313** |
| `WRITES(bare)` — writes the repo with no arguments | **2** |
| `WRITES(SHARED)` — mutates state OUTSIDE the repo | **11** |
| `INTENDED` — allowlisted in `tools/bare_run_writers.py`, each naming its path | 4 |
| `COULD NOT RUN` — did not finish in 25s | **34** |

**`COULD NOT RUN` IS A THIRD STATE AND IS NOT A PASS.** 34 of 313 tools were
not classified at all; the sweep is conclusive for **279**. A tool that times
out has not been shown not to write. Any figure quoted from this run has to
carry that denominator.

## Findings, routed

**EVERY ONE OF THE 13 IS A `tools/*.py` FILE, SO ALL 13 GO TO cc.** Nothing in
this sweep lands on `api/` (hank), `tests/` (cody) or `docs/` (ted) — and that
is worth saying plainly, because several of the *write targets* are under
`docs/` while every *tool* is under `tools/`. The brief routes by the file that
needs changing, which is the tool.

### `WRITES(bare)` — two, and both write a tracked document

| tool | exit | writes |
|---|---|---|
| `tools/mech_gate_live_probe.py` | 0 | `docs/live-residue/2026-10-13-mech_gate_live_probe.json` |
| `tools/tool_owner_map.py` | 1 | `docs/tool-owner-map.json` |

Both are plausibly INTENDED writers that were never added to
`tools/bare_run_writers.py` — `tool_owner_map.py` is a generator by name, and
`mech_gate_live_probe.py` writing a dated residue file is how a live probe
records what it saw. **The fix is probably an allowlist entry with a reason, not
a code change**, and the allowlist's own design note says why that matters: "an
exemption nobody can see is indistinguishable from a check that stopped
running."

### `WRITES(SHARED)` — eleven, mutating state outside the repo

| tool | exit | what it changed outside the repo |
|---|---|---|
| `condition_coverage.py` | None | WORKTREES |
| `dead_rule_sweep.py` | None | WORKTREES |
| `guard_ablation.py` | None | WORKTREES |
| `guard_ablation.py --help` | None | WORKTREES |
| `idempotency_check.py` | 1 | `SAIRN-SESSION-LOCKS/status/hover.json` |
| `install_git_hooks.py` | None | **GIT CONFIG** + WORKTREES |
| `invisible_in_pattern_check.py --help` | 0 | WORKTREES |
| `register_freshness_check.py --help` | 1 | `SAIRN-SESSION-LOCKS/status/fourth.json` |
| `run_all_tests.py` | None | WORKTREES |
| `run_semgrep.py` | 1 | WORKTREES |
| `shape_antipattern_check.py` | 1 | `SAIRN-SESSION-LOCKS/status/hover2.json` |

**THREE OF THESE WRITE ANOTHER SESSION'S STATUS ROW.** `idempotency_check.py`,
`register_freshness_check.py --help` and `shape_antipattern_check.py` each
changed a `status/<other-session>.json` in the shared registry — `hover.json`,
`fourth.json`, `hover2.json`. The registry is the thing every clone reads to
decide whether somebody else is working; a checker that edits another session's
row while merely being *run* is the sharpest item in this table.

**AND FOUR OF THE THIRTEEN FIRE ON `--help`.** `guard_ablation.py --help`,
`invisible_in_pattern_check.py --help` and `register_freshness_check.py --help`
mutate state. A read-only-sounding invocation that mutates is PR §1.4, and I hit
it myself this batch: `tools/sairn_rebase_resolve.py --help` *performed a merge*
rather than printing usage.

**`install_git_hooks.py` changing GIT CONFIG on a bare run** is its purpose, but
it is not allowlisted, and `core.hooksPath` is the setting whose absence makes a
clone arm no hooks at all.

## What the sweep does NOT say

* Nothing about the 34 that timed out.
* Nothing about whether any of these writes is *wrong* — only that it happens
  with no arguments, which is the condition under which a sweep that runs every
  tool does damage.
* It was run against a scratch clone, so WORKTREES/GITCONFIG findings are about
  **that** clone. The shared-registry findings are real and global: the registry
  lives outside every clone.
