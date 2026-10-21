# SAIRN handoff: cc, batch b44, 2026-10-21

**Dependabot #5 is closed at the source.** `firebase-admin` is upgraded
12.7.0 → 13.10.0, and `node-forge` is gone from the lockfile. This executes
the plan Michael approved (`~/.claude/plans/h-serene-sloth.md`). No override
was used.

## 1. State

| | |
|---|---|
| Commit | `fix(deps, cc b44): firebase-admin 12.7.0 -> 13.10.0 removes node-forge...`, landed at `775ee2da`, no force, 0 0 after fetch |
| Files | `package.json` (one line) and `package-lock.json`. Both are UNOWNED by the path manifest. `api/_lib/firebase-admin.js` is **unchanged** |
| Tier A | the gate says none applies: no Tier A resource and no coding rule is touched |
| Overrides | **NONE** |
| Deploy / alert | see the report: the deploy result, the SAIRNcash smoke check, and the alert #5 state |

## 2. What was measured

- **Lockfile, package by package:** 1 removed (`node-forge`), 10 added, 10
  changed, **all inside the firebase-admin subtree**. Every one of the 20 is
  OSV 0. Michael generated it with `npm install --package-lock-only
  --ignore-scripts`; the harness denies npm.
- **Driven on 13.10.0, with proof.** I copied `api/` into a scratch `npm ci`
  of this exact lock.
  - `api/_lib/firebase-admin.js` (instrumented, scratch copy only) printed
    `SDK_VERSION=13.10.0` from the scratch `node_modules`.
  - `firebase-mint.test.js` passes **16/16**: a real `credential.cert()`, a
    real `createCustomToken()`, and the signature verified.
  - The sairncash suites are green: verify 22, trial-start 10, trial-renew 4,
    idempotency 11, and stripe-webhook. These stub the SDK.
- Vercel runs Node 24.x; 13.10.0 needs Node ≥18.

## 3. A TRAP, worth knowing

**`C:\Users\marsh\node_modules` holds `firebase-admin` 12.7.0, with
`node-forge`.** No clone has its own `node_modules`, so Node's walk up the
parent directories lands there. **Every clone's api tests that load
firebase-admin have been testing 12.7.0 from the home directory**, not the
repo's lock. My first test run did exactly that, and I discarded those passes.

Nothing was changed there; it is Michael's home directory. Either delete it,
or bump it to 13.10.0 so local tests match production.

## 4. OPEN

- **Not driven:** `rtdbUpdate` / `rtdbGet` against a real Realtime Database.
  `@firebase/database-compat` moved 1.0.8 → 2.1.7, and no offline test covers
  the RTDB path.
- **The triage-doc addendum** (`docs/2026-10-05-dependabot-high-triage.md`,
  trigger 2 has fired) is fourth's file, and fourth held the path manifest
  this batch. The addendum text is in my report for fourth to paste in.
- **Michael:** the home-directory `node_modules` above.
