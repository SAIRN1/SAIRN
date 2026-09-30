# The relocated hover tooling is invisible to every build-agent enumerator — measured, read-only

**2026-09-29 (Hank), queue25 item 10.** The hover auditor's tools moved to
`.claude/skills/sairn-hover-auditor/tools/` in the platform repo. The question asked
was whether any build-agent **gate, sweep, glob, coverage denominator or defect
count** now treats that path as build code.

**Nothing was written. No file under `.claude/skills/sairn-hover-auditor/` was
opened for writing, and no gate was armed** — a build agent reaching into the
auditor's scope is the same boundary problem running the other way, and
`tools/hover_auditor_scope_gate.py` exists to stop it.

---

## The answer

**No build-agent enumerator can reach that directory, and no hover file is a keyed
entry in any generated artefact.** Four measurements, each by a different method.

### 1. What is actually there

**39 files, 32 of them `.py`.** Enumerated from disk, not from a list:
`claim_collision_scan.py`, `code_quality_baseline.py`,
`defect_density_weighting.py`, `dependency_health_check.py`,
`flagged_then_argued_down_scan.py`, `git_history_secrets_scan.py`,
`hover-watchlist.json`, `hover_backup_mirror.py`, and 31 more.

### 2. Every file-enumerating module in `tools/` and `tests/`, and what root it walks

**72 modules enumerate files** (`glob.glob`, `glob.iglob`, `os.walk`, `.rglob`).
Their roots were extracted from the source rather than guessed:

| | count |
|---|---|
| patterns confined to `tools/`, `tests/`, `docs/`, `api/`, `sql/`, `*.html` | **71** |
| patterns that name `.claude`, `skills`, or walk from the repository root | **1** |

**The one is `tools/sairn_claim_hook.py`, and every `.claude` path in it is
`.claude/claims`:**

```
if os.path.isdir(os.path.join(d, '.claude', 'claims')):
'.claude/claims/'], cwd=repo,
for path in sorted(glob.glob(os.path.join(repo, '.claude', 'claims', '*.json'))):
```

It reads the claim files. It never descends into `.claude/skills`.

### 3. The two broadest collectors, by their own collection expressions

* **`tools/run_all_tests.py`** — `os.walk(os.path.join(REPO, 'tests'))` and
  `os.listdir(api)`. Two roots, neither of them `.claude`.
* **`tools/tooling_inventory.py`** — `TOOLS = os.path.join(REPO, 'tools')` and
  `os.walk(os.path.join(REPO, 'tests'))`. Same answer.

**And no hover filename exists under `tools/` or `tests/`** — checked directly, zero
matches — so even a collector that walked those roots exhaustively could not pick
one up.

**A COULD-NOT-TELL, RECORDED RATHER THAN PAPERED OVER:** the first attempt ran
`run_all_tests.py --list` and **it timed out at 300 seconds**. That run produced no
answer, and the expression read above is a *different method*, not a substitute for
it. If somebody wants the run itself, it needs a bound in the tens of minutes.

### 4. Generated artefacts and denominators: is a hover file a KEYED ENTRY anywhere?

The question that matters is not whether a hover name appears in a document — an
index and a review ledger exist to name work — but whether one is **counted**: a
table row key, a manifest key, a matrix row.

| artefact | hover files as a keyed entry |
|---|---|
| `docs/TOOLING-INVENTORY.md` | **none** |
| `docs/traceability-matrix.md` | **none** |
| `docs/hook-manifest.json` | **none** |
| `docs/defect-density-register.json` | **none** |
| `docs/role-gate-negative-coverage.json` | **none** |
| `docs/SOUP-REGISTER.md` | **none** |

**Keyed-entry hits total: 0.**

Where hover names *do* appear, they appear in prose, and every instance is a
reference rather than a count:

* `docs/defect-density-register.json` — `sabotage_claim_verify.py`, inside a commit
  **subject** and the narrative summary of hover2's own finding about it.
* `docs/SAIRN-OPEN-WORK-INDEX.md` — `hover_coverage_ledger.py`, `hover_log.py`,
  `hover_self_health_fires.jsonl`, `hover_self_health_hook.py`,
  `sabotage_claim_verify.py`, `tool_provenance_check.py`. These are routing rows
  about auditor work, which is what the index is for.

---

## PASS 1 OF THIS CHECK WAS WRONG, AND THE WAY IT WAS WRONG IS THE POINT

The first pass matched hover tool **stems as substrings** and reported **four**
generated documents as carrying a hover name — `TOOLING-INVENTORY.md`,
`traceability-matrix.md`, `hook-manifest.json` and `defect-density-register.json`.

**Three of those four were one substring collision.** `hover_self_health` matched
**`hover_self_health_shim.py`**, which is a **BUILD-SIDE** tool at
`tools/hover_self_health_shim.py` — and its entire job is the hover separation
(*"a SessionStart hook registered by ABSOLUTE PATH into ONE clone, so a second
instance of the same role self-checks the FIRST clone's record"*). It is exactly
the file that **should** be in the inventory, the matrix and the hook manifest.

The build-side names that share a prefix with a relocated hover file, so the next
reader does not repeat this:

| relocated hover file | build-side file sharing its prefix |
|---|---|
| `hover_self_health.py` | `hover_self_health_shim.py` |
| `sabotage_claim_verify.py` | `sabotage.py` |
| `sabotage_closed_system_check.py` | `sabotage.py` |

**This is the same defect class as the 62-of-69 field screen earlier in the same
session:** a wide match over a shared prefix, producing individually plausible hits
and a rate that reads as a discovery. Pass 2 replaced substring matching with
keyed-entry matching, and the four became zero.

---

## What this does NOT say

* **It does not say the separation is correct.** It says no build-agent enumerator
  in `tools/` or `tests/` can see that path today. `tools/hover_auditor_scope_gate.py`
  (prevent) and `tools/hover_separation_audit.py` (detect) are the tools that own the
  boundary, and this is not a substitute for either.
* **It does not cover the hooks' runtime behaviour.** `docs/hook-manifest.json` has
  no hover key, and one wiring line does invoke
  `tools/hover_self_health_shim.py` — the build-side shim, by design, which is a
  deliberate silent no-op in a build clone.
* **`run_all_tests.py --list` was never successfully run.** Recorded above as a
  could-not-tell.
* **It is a point-in-time read.** The one enumerator that names `.claude` today
  names only `.claude/claims`. A second one added tomorrow would not announce
  itself, and nothing here re-checks on a cadence.
