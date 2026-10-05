# The dependabot HIGH — it was three advisories, one is FIXED, and two are one decision nobody has been asked to make

**2026-10-05 (Cody).** GitHub has been printing *"1 vulnerability on
SAIRN1/SAIRN's default branch (1 high)"* on every push and nobody had opened it.
Investigated. **It is three advisories across three packages, all HIGH or
HIGH-adjacent, and they are two different problems with two different answers.**

---

## WHAT THEY ARE

| package | severity | version here | vulnerable range | fix |
|---|---|---|---|---|
| `@grpc/grpc-js` | **high** + a companion low | 1.14.4 | `>=1.14.0 <1.14.5` | **1.14.5 — a PATCH** |
| `node-forge` | **high** | 1.4.0 | `<=1.4.0` | `firebase-admin@14.5.0` |
| `firebase-admin` | **high** (via `node-forge`) | 12.7.0 | `5.0.0 - 13.9.0` | `14.5.0`, **two majors** |

- **GHSA-m9gg-hp2v-232j** — `@grpc/grpc-js`: in certain configurations
  `getAuthContext` can return **unauthorized certificates as though they were
  authorized**.
- **GHSA-f596-whhp-79r4** — `@grpc/grpc-js` (low): the server transmits some
  handler-thrown error messages to the client in status messages.
- **GHSA-86w9-cpqp-85rv** — `node-forge`: **RSA PKCS#1 v1.5 signature
  VERIFICATION accepts extra nested DigestAlgorithm elements.**

**The dependency chain, read out of `package-lock.json` rather than guessed:**

```
package.json   firebase-admin ^12.7.0        <- DIRECT, and really used
  └─ node-forge ^1.3.1   -> resolved 1.4.0   <- the HIGH
  └─ ... google-gax
       └─ @grpc/grpc-js ^1.10.9 -> 1.14.4    <- the other HIGH, OPTIONAL dep
```

---

## ONE IS FIXED, AND IT COST THREE LINES

`google-gax` asks for `@grpc/grpc-js: ^1.10.9`, so **1.14.5 satisfies the
existing range** and no manifest change is needed.

```
npm update @grpc/grpc-js --package-lock-only
```

**MEASURED: exactly ONE package moved and the diff is 3 lines** — version,
resolved URL and integrity hash on `node_modules/@grpc/grpc-js`, 1.14.4 →
1.14.5. Nothing else in the lockfile changed, verified by diffing every
package's version between the before and after copies rather than by reading the
diff stat.

`tools/npm_audit_check.py` **3 advisories → 2** after it.

**This is the form the repo's own tool recommends and the reason it does:**
`npm install <pkg>@<version>` would have added a DIRECT dependency on a package
nothing here imports. `--package-lock-only` moves the resolution and leaves the
dependency graph's shape alone.

---

## TWO ARE ONE PROBLEM, AND IT IS NOT A FALSE POSITIVE

**`firebase-admin` IS REAL, LIVE CODE ON THIS PLATFORM.** Not a dev dependency,
not vendored-and-forgotten:

- `api/_lib/firebase-admin.js` exports `mintCustomToken`, `rtdbUpdate`,
  `rtdbGet`.
- Called from `api/sairncash/verify.js`, `api/sairncash/trial-verify.js` and
  `api/sairncash/stripe-webhook.js`.
- **Both endpoints answer in production right now** — `POST
  /api/sairncash/trial-verify` returns `400 Missing trialToken` and
  `/api/sairncash/verify` returns `400 Missing sessionId or subscriptionId`, so
  the handlers are reachable. (I sent deliberately malformed bodies: reaching the
  firebase call itself would MINT A REAL TOKEN, which is not a triage step.)
- Its own header records why it exists: SAIRNcash's Realtime Database sync had
  **no Firebase Authentication step at all** until 2026-08-19, and this is the
  real-auth answer Michael chose over trusting an unguessable id in a path.

**SO THE VULNERABLE VERSION IS GENUINELY IN A LIVE TREE. What I CANNOT establish
is whether the vulnerable PRIMITIVE is on our path, and I am not going to assert
either way.**

### The reachability question, stated precisely rather than answered

The advisory is about RSA PKCS#1 v1.5 **signature VERIFICATION**. Our documented
use is the opposite direction: `mintCustomToken` **SIGNS** a JWT with the
service-account private key, and the RTDB calls then carry that token.
Verification of it happens inside Firebase, not here.

**That is a reason to suspect the primitive is off our path. It is NOT a
measurement, and here is why I could not make one:** `node_modules/` is not
installed in this clone, so I could not grep `firebase-admin`'s own source for
where it calls `node-forge`. A reachability claim built on reasoning about an
advisory title, without reading the library, is exactly the shape this platform
corrects — so the honest verdict is **UNDETERMINED**, not "not exploitable".

### Why it is not fixed here

`fixAvailable` is `{"name": "firebase-admin", "version": "14.5.0",
"isSemVerMajor": true}` — **12.7.0 → 14.5.0, two major versions, of the SDK that
mints SAIRNcash's auth tokens.** That is:

- a breaking-change upgrade to security-critical auth code,
- on an app whose Firebase path has no test that drives a real mint,
- during a review batch, with no SAIRNcash owner asked.

**A two-major bump of the thing that authenticates a customer's financial data
is a decision with a person's name on it, not a lockfile edit.** `npm audit fix
--force` would do it and would be the wrong way to find out.

---

## WHAT IS OWED, AND BY WHOM

> **THE DECISION, and it is not Michael's SQL queue — it is an engineering
> call:** upgrade `firebase-admin` 12.7.0 → 14.5.0, or accept the risk with a
> written basis and a re-check trigger.
>
> **What has to happen either way, in this order:**
>
> 1. **Read what `firebase-admin` uses `node-forge` for.** `npm ci` in a
>    throwaway directory, then grep its `lib/` for `node-forge`. That turns the
>    UNDETERMINED above into a yes or a no, and it is the cheapest step by far.
> 2. **If the primitive is off our path** — accept it, record it in the
>    accepted-risk register with a NAMED trigger
>    (`tools/accepted_risk_trigger_check.py` exists for exactly this and is
>    report-only pending its next real register state), and stop the dependabot
>    banner being read as "nobody looked".
> 3. **If it is on our path** — the upgrade is not optional and needs a test
>    that drives a real `mintCustomToken` first, because there is none today.
>
> **DO NOT run `npm audit fix --force`** to clear the banner. It performs the
> two-major bump silently and the banner going away would be the only evidence
> anybody had.

---

## WHAT THIS DOES NOT ESTABLISH

- **That the `grpc-js` fix is exercised.** `@grpc/grpc-js` is an **optional**
  dependency of `google-gax` and nothing in this repo imports it directly; the
  patch removes a vulnerable version from the tree, which is not the same as
  proving the old one was ever loaded.
- **That two advisories is the floor.** `npm audit` reports what the registry
  knows today; it is a snapshot with a date, like every other figure here.
- **Anything about the node-forge path.** See above — undetermined, and the one
  cheap step that would settle it is named rather than done.
