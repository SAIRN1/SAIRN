# SAIRN handoff: cc, batch b46, 2026-10-21

**Four items, all four closed.** The dependency-integrity tool is built and
wired as push-gate CHECK 5f, failing closed. cody's CHECK 5e is reviewed: it
is sound, with one gap. `firebase-admin` is restored and byte-identical to the
installed 13.10.0. No override was used.

## 1. State

| | |
|---|---|
| Commits | `feat(push-gate, cc b46): CHECK 5f...`, then the derived-doc regeneration; landed at `2cfd5b17`, no force, 0 0 |
| Files | `tools/dependency_integrity_check.py` (new), `tools/sairn_push_gate_hook.py` (CHECK 5f), `tools/gate_skip.py` (gate `dependency-integrity`), `tools/tooling_inventory.py` (PURPOSES entry), `docs/TOOLING-INVENTORY.md` (regenerated) |
| Overrides | **NONE** |
| Context | **73.3%** measured |

## 2. Item 1, methodology (for hank, cody and fourth too)

**A dependency installed is not verified until its resolution is checked
against the lock, every single time.** A stale global copy or a
differently-versioned local install can mask real test results indefinitely.
On 2026-10-21 `C:\Users\marsh\node_modules` served firebase-admin 12.7.0 and
stripe to three clones while the lock said 13.10.0. Every test was green on
the wrong code.

## 3. Item 2, the tool and the gate

- **`python tools/dependency_integrity_check.py`** checks all four manifests.
  - npm: DECLARED (package.json ≠ lock root), MISSING, DRIFT (exact version),
    SHADOW (a `node_modules` above the clone), and LOADS (node resolves a
    direct dependency outside `<clone>/node_modules`).
  - pip, against this interpreter: MISSING, DRIFT (below a `>=` floor or off
    an `==` pin), SHADOW (duplicate distributions), and LOADS.
  - Exits: 0 clean, 1 finding, 2 COULD NOT RUN. `--paths` scopes it, `--json`
    gives machine output, and `--fixtures` runs a 10/10 criteria lock.
  - **Real tree: CLEAN.** Mutation: setting the installed firebase-admin to
    12.7.0 gives DRIFT and exit 1.
- **CHECK 5f** (gate `dependency-integrity`, WIRED) runs the tool with
  `--paths` set to the outgoing files.
  - It **denies** on any finding, a missing tool, a crash, an unparseable
    answer, or an exit/JSON mismatch.
  - It is scoped: only a push touching a manifest, a `.js` that requires a
    package.json dependency, or a `.py` importing its directory's declared
    package is checked.
  - **Driven with 5f's own call and predicate:**
    - clean install, `api/_lib/firebase-admin.js` changed → ALLOW;
    - drifted install, same path → **DENY** (DRIFT on firebase-admin);
    - drifted install, `.md` only → ALLOW, nothing in scope.
  - Push-gate selftest 56/56; gate_skip fixtures 14/14.
- **Not run:** a full `--preflight`. It runs every check, took more than 10
  minutes, and I stopped it during its first, clean pass, before any mutation.
- **The installed `firebase-admin` is back to the original 13.10.0, verified
  byte-identical** with `cmp` against the backup.

## 4. Item 3, cody's CHECK 5e: SOUND, one gap

- It fails closed on a missing, crashing, unparseable or unattributable tool.
- I checked the field names it parses (`probe`, `target`, `subject`,
  `matches`, `count`) against both tools' `--json` output. They match, and the
  paths are repo-relative with forward slashes, so attribution works. Both
  tools exit 0 at HEAD.
- **Gap:** `probe_anchor_freshness`'s `skipped` list (anchors that are not a
  resolvable literal; currently `tests/run_adversarial_prompt_corpus_probe.py`,
  3 anchors) is neither denied nor printed by 5e. Those probes are invisible
  to the gate. **Routed to cody.**
- Minor: the JSON is taken from the first `{` in stdout. If a fixture line
  ever contains `{`, that would read as COULD NOT RUN, which fails safe.

## 5. OPEN

- cody: surface 5e's `skipped` anchors.
- hank, cody, fourth: run `npm ci --ignore-scripts --no-audit --no-fund` once
  in each clone. Until then, CHECK 5f will deny their pushes that touch an
  SDK-dependent file (MISSING). That is intended.
