# The 23 formerly COULD NOT RUN rules — cause, bound, and what each one is now

**2026-10-06 (Cody). The ledger H2 starts from.** Every row carries the
command, the commit and the date that produced it. **Re-run rather than quote.**

| | |
|---|---|
| population | `python tools/dead_rule_sweep.py`, commit `8f204050`, 2026-10-06, **`EXIT 2`** read from its `capture_exit` status file |
| 540 rules, 517 checked | **23 COULD NOT RUN** — down from 36 after the encoding fixes |
| re-ask | `python tools/dead_rule_sweep.py` `--tool cross_tenant_isolation_scope.py --corpus-timeout 200`, commit `6d19c775`, **`EXIT 1`** |
| the two left | `--tool run_all_tests.py` and `--tool guard_ablation.py`, commit `6f313a77`, **`EXIT 2`** each |

## THE CAUSE WAS MINE FOR 21 OF THE 23, AND IT WAS NOT "NO EVIDENCE"

`CORPUS_TIMEOUT` was **45s** platform-wide. `cross_tenant_isolation_scope.py`
needs **131s**, measured. Its bare run timed out on every ablation and all 21
of its rules printed *"no fixture lock and no control to ablate against"* —
**false about the half that mattered.** The evidence existed; my sweep declined
to wait for it. The verdict text now leads with the bound and never mentions a
lock, held by arms K1-K4 in `tests/run_dead_rule_sweep_probe.py`.

## THE TABLE

| rule | tool:line | cause | bound | command | commit |
|---|---|---|---|---|---|
| `BRANCH` | `cross_tenant_isolation_scope.py:150` | **RESOLVED** — my 45s bound, not an absence of evidence | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `BRANCH_ALT` | `cross_tenant_isolation_scope.py:155` | **RESOLVED** — my 45s bound, not an absence of evidence | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `_ACTIONS` | `cross_tenant_isolation_scope.py:157` | **RESOLVED** — my 45s bound, not an absence of evidence | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `DISPATCH_MAP` | `cross_tenant_isolation_scope.py:162` | **RESOLVED** — my 45s bound, not an absence of evidence | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `DISPATCH_USE` | `cross_tenant_isolation_scope.py:163` | **RESOLVED** — my 45s bound, not an absence of evidence | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `_EQ_READ` | `cross_tenant_isolation_scope.py:343` | **RESOLVED** — my 45s bound, not an absence of evidence | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `_EQ_READ2` | `cross_tenant_isolation_scope.py:346` | **RESOLVED** — my 45s bound, not an absence of evidence | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `_HASH_LITERALS` | `cross_tenant_isolation_scope.py:347` | **RESOLVED, and DEAD** — the bound was hiding it | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `_HASH_RETURNED` | `cross_tenant_isolation_scope.py:348` | **RESOLVED, and DEAD** — the bound was hiding it | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `_HASH_CONST` | `cross_tenant_isolation_scope.py:352` | **RESOLVED** — my 45s bound, not an absence of evidence | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `_HASH_USE` | `cross_tenant_isolation_scope.py:353` | **RESOLVED** — my 45s bound, not an absence of evidence | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `_REFUSAL_STATUS` | `cross_tenant_isolation_scope.py:382` | **RESOLVED** — my 45s bound, not an absence of evidence | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `_REFUSAL_LENGTH` | `cross_tenant_isolation_scope.py:385` | **RESOLVED, and DEAD** — the bound was hiding it | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `_REFUSAL_CONTENT` | `cross_tenant_isolation_scope.py:386` | **RESOLVED** — my 45s bound, not an absence of evidence | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `_DECLARES` | `cross_tenant_isolation_scope.py:613` | **RESOLVED** — my 45s bound, not an absence of evidence | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `_DECLARES_NONE` | `cross_tenant_isolation_scope.py:614` | **RESOLVED** — my 45s bound, not an absence of evidence | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `_TABLE` | `cross_tenant_isolation_scope.py:638` | **RESOLVED** — my 45s bound, not an absence of evidence | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `_ROW_NAME` | `cross_tenant_isolation_scope.py:642` | **RESOLVED** — my 45s bound, not an absence of evidence | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `_DECL_BLOCK` | `cross_tenant_isolation_scope.py:821` | **RESOLVED, and DEAD** — the bound was hiding it | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `_HARM_MONEY` | `cross_tenant_isolation_scope.py:1042` | **RESOLVED** — my 45s bound, not an absence of evidence | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `_HARM_PERSON` | `cross_tenant_isolation_scope.py:1045` | **RESOLVED** — my 45s bound, not an absence of evidence | **280s** (measured 131s, 2x headroom, 2026-10-06) | `--tool cross_tenant_isolation_scope.py --corpus-timeout 200` | `6d19c775` |
| `GATE` | `guard_ablation.py:?` | **UNRESOLVED — NO BOUND CAN BE SET.** Measured **>420s without finishing**; a long-running HARNESS whose output is dominated by what it orchestrates | **none** — a bound from a measurement that did not finish is an invented number | `--tool guard_ablation.py` | `6f313a77` |
| `PUSH_RE` | `run_all_tests.py:?` | **UNRESOLVED — NO BOUND CAN BE SET.** Measured **>420s without finishing**; a long-running HARNESS whose output is dominated by what it orchestrates | **none** — a bound from a measurement that did not finish is an invented number | `--tool run_all_tests.py` | `6f313a77` |

## THE 21 ARE RESOLVED — 21 of 21 ANSWERABLE, AND FOUR ARE DEAD

```
python tools/dead_rule_sweep.py --tool cross_tenant_isolation_scope.py
       --corpus-timeout 200                                EXIT 1
  corpus bound: 200s per bare real run (--corpus-timeout)
  CHECKED / UNIVERSE: 21 of 21 rules could be ABLATED
  17 move the output, 4 DO NOT MOVE A BYTE
```

## THE 2 UNRESOLVED, CLASSIFIED

| tool | rule | classification |
|---|---|---|
| `run_all_tests.py` | `PUSH_RE` | **UNBOUNDABLE.** >420s, did not finish. It drives the whole suite, so its output is dominated by what it orchestrates — neutralising one regex is lost in the noise even if the run completed |
| `guard_ablation.py` | `GATE` | **UNBOUNDABLE.** >420s, did not finish. It builds worktrees and ablates inside them: a harness, not a checker |

**NEITHER IS "NO LOCK, NO CONTROL" AND NEITHER IS A BOUND PROBLEM.** Both now
report `COULD NOT RUN: NO BOUND CAN BE SET -- measured >420s without finishing
... NOT an absence of a lock`, declared in `dead_rule_sweep.UNBOUNDABLE` with
the measurement, the date and the structural reason. Held by arms K7b-K7d.

**The right repair for both is a FIXTURE LOCK or a declared CONTROL**, not a
bigger bound: the real run is the wrong evidence class for a harness.

---

## FOR H2 — WHAT THIS FILE DOES AND DOES NOT SETTLE

- **It settles the CAUSE of all 23**, with the command and commit per row.
- **It does not diagnose the 4 DEAD rules** — that is
  `docs/2026-10-06-cody-queue18-inventory.md`, which names a DIFFERENT cause
  for each of the four.
- **It does not claim 23 is the platform total.** It is the survivors of a
  540-rule run at `8f204050`. The universe moved +12 in the previous day, so
  re-run `--universe` before treating any count here as current.
