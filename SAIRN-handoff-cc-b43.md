# SAIRN handoff: cc, batch b43, 2026-10-21

**Three items, all three closed.** Both b42 manifests are indexed, and the
alert count is unchanged. No code changed; only these deliverables were
pushed. No override was used.

## 1. CLOSED

- **Item 1: indexed.** GitHub's dependency-graph GraphQL API now lists **11
  manifests, all `parseable: true`**:
  - `tests/requirements.txt`: 1 dependency (pyyaml);
  - `docs/requirements.txt`: 2 (markdown-it-py, pyyaml);
  - `tools/requirements.txt`: 2 (playwright, pypdf);
  - plus `package.json` (3), `package-lock.json` (193),
    `packages/testint/pyproject.toml` (1) and the five workflows.
  - The SBOM (created 2026-10-21T18:46:37Z) has 207 packages. It includes
    markdown-it-py, pyyaml (×2), pypdf and playwright.
- **Item 2: still only #5.** Dependabot by state: **open 1** (#5 `node-forge`,
  `package-lock.json`), **fixed 4** (#1 uuid, #2 and #3 qs, #4 @grpc/grpc-js),
  **dismissed 0**, **auto_dismissed 0**. Declaring the five Python
  dependencies surfaced no new alert.
- **Item 3:** nothing in the repo changed, so only these deliverables were
  pushed.

## 2. ONE OBSERVATION, not a defect

The graph stores the `requirements` string as **empty** for all five
`requirements.txt` entries; my `>=` floors were not captured. So the packages
are now visible to GitHub, but whether Dependabot can match a future advisory
against an unpinned `>=` range is **not verified**. Pinning exact versions
would make it certain, at the cost of a bump per release. That is a judgement
call, so I left the floors as they are and am noting it rather than acting.

## 3. OPEN (unchanged)

- **Michael:** alert #5, `firebase-admin` 12.7.0 → 13.10.0 (with a mint test
  first).
- **hover:** declare `anthropic` and `rfc3161ng` in its own scope.
- **Routed:** hank (b40 barrier tests); fourth (review cc
  2026-10-21T17:13:48Z).
