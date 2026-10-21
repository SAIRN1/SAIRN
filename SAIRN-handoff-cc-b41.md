# SAIRN handoff: cc, batch b41, 2026-10-21

**Four items, all four closed.** The Write-deny gap is closed: Write was
refused, and no file was created. The Dependabot sweep found one open alert,
which is not mine, plus a blind spot in `tools/` that is mine. I gave
`tools/` a manifest. One step was denied and is Michael's: upgrading the
installed `pypdf`. No override was used.

## 1. State

| | |
|---|---|
| Commit | `chore(deps, cc b41): tools/ gets a requirements manifest...` landed at `8ec6c3c3`, no force |
| Overrides | **NONE** |
| Context | in the digest, measured |

## 2. CLOSED

- **Item 1, the Write-deny probe. REFUSED everywhere; no file exists.**
  - I tried `Write` of `permission_probe_cc.tmp` into `SAIRN-hover`,
    `SAIRN-hover2`, and `~/Documents/SAIRN-hover2`.
  - All three refused: "File is in a directory that is denied by your
    permission settings".
  - A `Glob` for `permission_probe_cc*` in both clones finds nothing.
  - With b40's Edit and Bash refusals, every deny class is now probed.
- **Item 2, the Dependabot sweep (REST API, every state).**
  - **Open: 1.** #5, npm `node-forge` ≤1.4.0 (HIGH), in the root
    `package-lock.json` through `firebase-admin` ^12.7.0.
    - **Not mine.** The lockfile is UNOWNED by the path manifest, and its
      consumer is `api/_lib/firebase-admin.js` (hank's api/). Not touched.
    - `firebase-admin` 13.10.0 is the first release without `node-forge` (b40).
  - **Fixed: 4.** #1 uuid, #2 and #3 qs, #4 @grpc/grpc-js.
  - **Other manifests:** `packages/testint/pyproject.toml` declares
    `dependencies = []`, so nothing can alert. The workflows use only first-party
    `actions/*` and `github/codeql-action`.
  - **THE BLIND SPOT, in `tools/` (mine).** `tools/` had **no manifest**, so
    Dependabot could not see what it imports.
    - An AST walk finds exactly two third-party imports: `pypdf` and
      `playwright`.
    - **The installed `pypdf` 6.16.1 has 12 OSV advisories (8 HIGH), all
      denial-of-service on a crafted PDF.** `tools/sairn_source_fetch.py`
      parses PDFs fetched from the network.
    - The installed `playwright` 1.61.0 has none.
  - **Fix (concept first, item 3):** a dependency nobody declares is one
    Dependabot cannot see.
    - New `tools/requirements.txt`: `pypdf>=6.20.1` and `playwright>=1.61.0`.
    - Each floor is the lowest version with zero OSV advisories (6.20.1 and
      6.21.2 both read 0).
  - **DENIED, so Michael's:** `python -m pip install -U "pypdf>=6.20.1"`.
    Until that is run, the interpreter still has 6.16.1.
    - The manifest makes the gap visible and sets the floor. It does not
      change what is installed.
    - An unpinned `>=` floor will not by itself raise a Dependabot alert
      against the installed copy.
- **Item 4:** pushed and confirmed.

## 3. OPEN

- **Michael:**
  - run `! python -m pip install -U "pypdf>=6.20.1"`, which closes the 12
    local advisories;
  - decide `firebase-admin` 12.7.0 → 13.10.0 (with a mint test first).
- **Not yet observed:** GitHub's dependency graph had not indexed
  `tools/requirements.txt` at write-up (the SBOM has 202 packages and no pypdf
  yet).
- **Still routed:** hank (b40 barrier tests, keyboard close); fourth (review
  cc 2026-10-21T17:13:48Z).
