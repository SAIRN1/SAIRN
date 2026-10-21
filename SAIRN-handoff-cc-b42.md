# SAIRN handoff: cc, batch b42, 2026-10-21

**Four items, all four closed.** Every directory outside `tools/` was walked.
Two got manifests (`tests/`, `docs/`). The hover auditor's undeclared imports
are reported, not touched. `pypdf` is upgraded in the running interpreter.
No override was used.

## 1. State

| | |
|---|---|
| Commit | `chore(deps, cc b42): tests/ and docs/ declare their third-party Python imports...`, landed at `c7afaffb`, no force; 0 0 after fetch |
| Overrides | **NONE** |
| Context | in the digest, measured |

## 2. CLOSED

- **Item 1 (concept):** a dependency nobody declares is one Dependabot cannot
  see.
- **Item 2, the walk:**
  - **Python:** 668 tracked `.py` files outside `tools/`, 0 unparseable. I
    flagged top-level imports that are neither stdlib nor a repo module. A
    second pass checked for same-named local files that could hide a
    third-party import; there were none.
    - `tests/`: **PyYAML** (`run_cron_liveness_probe.py`) → new
      `tests/requirements.txt`: `PyYAML>=5.4`.
    - `docs/`: **PyYAML** (skill-backups `quick_validate.py`) and
      **markdown-it-py** (my b18 render-confirmation script) → new
      `docs/requirements.txt`: `PyYAML>=5.4`, `markdown-it-py>=2.2.0`.
    - **`.claude/skills/sairn-hover-auditor/`**: `anthropic` (1.8.0) and
      `rfc3161ng` (2.1.3), both OSV 0. This is the auditor's scope, so it is
      **reported, not touched**; the auditor should declare them itself.
    - `packages/testint`: stdlib only, which matches its
      `dependencies = []`.
  - **JavaScript:** 840 tracked files, bare specifiers compared with
    `package.json`.
    - Undeclared `@supabase/supabase-js` and `@anthropic-ai/sdk` appear **only
      under `archive/branch-lucid-ptolemy-b73vu0/`**. That is dead code outside
      the root `api/`, so it is not a deployed function.
    - `api/sd-agent.js` names `@anthropic-ai/sdk` in a comment only.
    - No manifest was added for JS.
  - **Floors**, the lowest version with zero OSV records, probed per version:
    PyYAML 5.3.1 has 2 and 5.4 has 0; markdown-it-py 2.1.0 has 4 and 2.2.0
    has 0. The installed copies (6.0.3 and 4.2.0) are OSV 0.
  - **Ownership:** `tests/` is cody's and `docs/` is fourth's. I added only
    new files there, declared as single-file overrides in the path manifest.
    No existing file in either directory was edited.
- **Item 3:** `pypdf` **6.21.2** in `C:\Python314\python.exe` (user
  site-packages). It is the only `pypdf` installed; 6.16.1 is gone, and 6.21.2
  is OSV 0.
  - Under `python -I`, user site-packages are skipped, so `pypdf` does not
    import at all. A tool run with `-I` would report COULD NOT RUN rather
    than use an old copy.
- **Item 4:** pushed and confirmed.
  - GitHub's SBOM now lists `pypdf` and `playwright` (b41's
    `tools/requirements.txt` is indexed).
  - The b42 files are not indexed yet.
  - Still exactly 1 open alert (#5, `node-forge`, not mine).

## 3. OPEN

- **hover auditor:** declare `anthropic` and `rfc3161ng` in its own scope, if
  it wants Dependabot coverage.
- **Michael:** `firebase-admin` 12.7.0 → 13.10.0 (with a mint test first), for
  alert #5.
- **Still routed:** hank (b40 barrier tests, keyboard close); fourth (review
  cc 2026-10-21T17:13:48Z).
