# SAIRN handoff: cc, batch b45, 2026-10-21

**Two items, both closed.** Local api tests now resolve every SDK from this
clone's own lockfile install, and no stale copy is left. Nothing in the repo
changed (`node_modules` is gitignored), so only these deliverables were pushed.

## 1. What was measured

- **The home `node_modules` is gone.** `C:\Users\marsh\node_modules` no
  longer exists, and neither `Documents\`, `C:\Users\` nor `C:\` has one.
- **Before the clone install, the dependent tests failed loudly.**
  `firebase-mint.test.js` threw `Cannot find module 'firebase-admin'`, and
  `verify.test.js` / `stripe-webhook.test.js` threw
  `Cannot find module 'stripe'`, all exit 1.
  - So **`stripe` was also coming from the home directory**, not only
    firebase-admin.
  - This is the right failure: no silent pass on a missing SDK.
- **After Michael's `npm ci --ignore-scripts` in this clone:** each SDK
  resolves from `<clone>\node_modules` at exactly the lockfile version:
  `firebase-admin` 13.10.0, `stripe` 17.7.0, `@simplewebauthn/server` 13.3.2.
  `node-forge` is absent.
- **Proof from inside each run**, not assumed. A `node -r` preload logs the
  SDK file each test actually loads.
  - `firebase-mint.test.js` passes **16/16**, loading `firebase-admin=13.10.0
    @ <clone>\node_modules`.
  - `verify` 22/22, `stripe-webhook` pass, and `portal` 19/19, each loading
    `stripe=17.7.0 @ <clone>`.
  - `stripe-api-version`, the trial suites and the two passkey suites load no
    SDK in-process (they stub), and all pass.
- **Full api/ suite:** 333 suites. The only failures are the same 4
  long-standing reds (law-trust-reconcile-endpoint, app-boundary,
  family-contacts, law-trusttx-clearance). **No exit code changed** against
  the b38 run; one new suite (`api/b45-leg-settings-owner-write.test.js`,
  not mine) passes.

## 2. Worth knowing

Every other clone (hank, cody, fourth) is now in the state this clone was in
before the install: no `node_modules`. Their SDK-dependent api tests will exit
1 with `Cannot find module` until each runs
`npm ci --ignore-scripts --no-audit --no-fund` once. That is the correct
failure, not a regression; it used to pass by silently using the home
directory's 12.7.0.

## 3. OPEN

- The other clones need `npm ci` once each (above).
- Unchanged from b44: `rtdbUpdate`/`rtdbGet` not driven against a real
  Realtime Database; the pre-existing SAIRNcash stripe-webhook config 500;
  fourth to paste the triage addendum.
