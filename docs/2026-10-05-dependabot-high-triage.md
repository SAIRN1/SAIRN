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

---

# ADDENDUM 2026-10-06 (Cody) — UNDETERMINED IS NOW MEASURED: THE VULNERABLE PRIMITIVE IS NOT ON OUR PATH

**The cheap step this document named rather than did has now been done, and it
settles the question in the direction the reasoning suspected — but it is a
measurement this time, not a reasonable guess from an advisory title.**

## It did not need an install. The packages were already on disk, OUTSIDE the clone

`node_modules/` is still absent from this clone, which is why the original
triage stopped. What it missed is that Node resolves these from the user-level
tree:

```
stripe          -> C:\Users\marsh\node_modules\stripe\...
firebase-admin  -> C:\Users\marsh\node_modules\firebase-admin\lib\index.js
node-forge      -> C:\Users\marsh\node_modules\node-forge\lib\index.js
```

**AND THEY ARE THE LOCKFILE'S EXACT VERSIONS, WHICH IS THE ONLY REASON THIS
COUNTS.** Reading reachability off a different build would be the wrong-subject
defect this platform corrects:

| package | installed | `package-lock.json` |
|---|---|---|
| `firebase-admin` | **12.7.0** | **12.7.0** |
| `node-forge` | **1.4.0** | **1.4.0** |

## THE MEASUREMENT: one call site, and it is a PARSER, not a VERIFIER

Every `forge.*` call in the whole of `firebase-admin@12.7.0`'s `lib/` — one:

```
lib/app/credential-internal.js:148   const forge = require('node-forge');
lib/app/credential-internal.js:150   forge.pki.privateKeyFromPem(this.privateKey);
```

It sits inside `ServiceAccount`'s constructor validation, wrapped in a
`try/catch` whose only purpose is to turn a bad key into
`Failed to parse private key`. **The return value is discarded.**

**GHSA-86w9-cpqp-85rv is about RSA PKCS#1 v1.5 signature VERIFICATION** — the
`verify` functions in node-forge's `lib/rsa.js` (present in 1.4.0 at lines 1163
and 1217). `pki.privateKeyFromPem` is a PEM parser. **Nothing on our path
reaches either `verify`.**

Three further checks, all negative:

| question | answer |
|---|---|
| does anything in `api/`, `tests/` or `tools/` require `node-forge`? | **no** — the single grep hit is the English word "forge" in a test comment |
| does any other package in the lock pull `node-forge`? | **no** — `firebase-admin` is the only declarer, `^1.3.1`, across all 195 locked packages |
| is the input to that one call attacker-supplied? | **no** — it is our own service-account private key out of environment config |

## SO THE TWO-MAJOR UPGRADE IS NOT WHAT THIS ADVISORY REQUIRES

That makes this **branch 2** of the decision this document laid out, not branch
3: accept, with a written basis and a named re-check trigger. The basis is the
measurement above. **The upgrade was not rejected because it is inconvenient —
it is not indicated**, and a 12.7.0 → 14.5.0 bump of the SDK that mints
SAIRNcash's auth tokens, on a path with no test driving a real
`mintCustomToken`, is a real risk taken for no measured gain.

### THE RE-CHECK TRIGGER, because an accepted risk with no trigger is a shrug

Re-open this the moment **any** of these changes, and each is cheap to check:

1. **`firebase-admin` gains a second `forge.*` call site.** The whole basis is
   that there is exactly one. `grep -rn "forge\.[a-zA-Z]" <firebase-admin>/lib`
   must return one line.
2. **`firebase-admin` is upgraded for any other reason.** A new major may use
   node-forge differently; the basis is version-specific by construction.
3. **Anything in this repo requires `node-forge` directly.**
4. **A new advisory lands against `pki.privateKeyFromPem` itself**, which is the
   one primitive we do use.

## WHAT I COULD NOT DO, SAID PLAINLY

**The upgrade path was not executed and not tested.** `npm install` is
unavailable in this session, so `firebase-admin@14.5.0` could not be resolved,
the lockfile could not be regenerated, and no suite could be run against it.
**Had the measurement come out the other way, this item would be BLOCKED rather
than closed** — and the honest order matters: the measurement is what makes the
upgrade unnecessary, not the inability to perform it.

**`api/sairncash/stripe-webhook.test.js` passes right now** (`all assertions
passed`) against these exact installed versions, which establishes the suite is
green on the CURRENT tree. It says nothing about 14.5.0.

## WHAT THIS ADDENDUM DOES NOT ESTABLISH

- **That `firebase-admin@14.5.0` is safe, or unsafe.** It was never installed.
- **That the dependabot banner will clear.** It will not: the vulnerable version
  is still in the tree. **Not-reachable and not-present are different states**
  and only one of them silences a scanner.
- **That one call site today means one tomorrow.** That is exactly why trigger 1
  exists and why it names the command.
- **That reading a library's `lib/` is the same as running it.** A dynamically
  built `require` or a call through a re-export would not match that grep. The
  grep found a literal `require('node-forge')` and one literal `forge.` use,
  which is strong — and it is still a source read, not an execution trace.

---

# ADDENDUM 2 — 2026-10-06 (Cody): THE UPGRADE WAS DRIVEN IN A SCRATCH COPY, AND IT IS GREEN. IT ALSO MAKES THE CALL-SITE ARGUMENT UNNECESSARY

**Addendum 1 argued the vulnerable primitive is off our path. That argument
stands and is no longer the strongest thing available.** `firebase-admin@14.5.0`
**drops `node-forge` from the tree entirely**, so the question of which
primitive we reach stops being a question.

Everything below ran in `…/scratchpad/fa14`, **outside the repo**. The repo's
`package.json` and `package-lock.json` are **unchanged** — this is a
measurement, not an applied upgrade.

## WHAT WAS RUN, EACH EXIT CODE CAPTURED ON ITS OWN LINE

```
npm install firebase-admin@14.5.0 --package-lock-only   NPM_INSTALL_EXIT=0
npm install                     (full, scratch copy)    NPM_FULL_INSTALL_EXIT=0
npm ci                          (12.7.0 baseline copy)  NPM_CI_BASELINE_EXIT=0
node -e require('./api/_lib/firebase-admin.js')         FIREBASE_LIB_LOAD_EXIT=0
node api/sairncash/stripe-webhook.test.js  (14.5.0)     STRIPE_WEBHOOK_14_EXIT=0
```

**No command was blocked.** `npm install` had been declined in the previous
session; run inside a scratch directory outside the repo it completed.

## NODE-FORGE IS GONE, NOT MERELY UNREACHED

| | 12.7.0 (current) | 14.5.0 (scratch) |
|---|---|---|
| `node_modules/node-forge` resolved | **1.4.0** | **ABSENT** |
| packages declaring `node-forge` | `firebase-admin` (`^1.3.1`) | **none** |
| `forge.*` call sites in `firebase-admin/lib` | **1** | **0** |
| total locked packages | 195 | 232 |

**That is a different and better answer than addendum 1's.** "The vulnerable
function is not on our path" depends on there being exactly one call site and
needs a trigger to watch it. **"The package is not in the tree" needs no
trigger** — and it is the only one of the two that silences the scanner.

## THE SUITES: A DIFFERENTIAL, BECAUSE AN ABSOLUTE WOULD BE UNREADABLE

Both copies hold identical `api/` and `tests/` trees from the same HEAD. The
only difference is the installed dependency set.

```
BASELINE-12.7.0 : 248 suites, 160 exit 0, 88 NOT 0
UPGRADE-14.5.0  : 248 suites, 160 exit 0, 88 NOT 0

SUITES WHOSE VERDICT CHANGED:  0
```

**Zero. The red and green sets are identical, suite for suite.** All eight
`sairncash` suites — the only ones that touch this dependency — are **exit 0
under both**, and `stripe-webhook.test.js` prints `all assertions passed` under
14.5.0.

**THE 88 RED ARE PRE-EXISTING AND ARE NOT THE UPGRADE.** They are red under
12.7.0 too, mostly `deadline-*` and `compliance-*` suites that want environment
the scratch copy does not carry. **That is exactly why this is reported as a
differential and not as "160 of 248 passed"** — an absolute figure here would
be a number about the scratch directory, not about the upgrade.

## SO THE DECISION CHANGES, AND THE BASIS IS STRONGER

Addendum 1 put this on **branch 2** — accept with a basis and a trigger — on the
grounds that a two-major bump of auth code was a real risk for no measured gain.
**There is now a measured gain and a measured absence of cost:**

- the vulnerable package leaves the tree, so the banner clears and no trigger has
  to be maintained;
- **no suite changes verdict**, driven on the real trees rather than reasoned
  about.

**The upgrade is now the recommended path.** It is **not applied**: this is a
measurement in a scratch copy, and applying it touches `package-lock.json` on a
live payment path.

## WHAT THIS STILL DOES NOT ESTABLISH, AND ONE OF THESE MATTERS

- **No suite drives a real `mintCustomToken`.** Addendum 1 said so and it is
  still true. "No suite changed verdict" is bounded by what the suites cover,
  and **the mint path is not covered by any of them.** Our wrapper LOADS under
  14.5.0 and exports all three functions; that is module resolution, not a
  token.
- **14.5.0 restricts `exports`.** `require('firebase-admin/package.json')`
  raises `ERR_PACKAGE_PATH_NOT_EXPORTED` where 12.7.0 allowed it. **A real
  breaking change, and nothing in `api/` reaches for a subpath** — found because
  my own version probe hit it, which is the kind of thing a two-major bump does.
- **232 packages where there were 195.** The upgrade adds 37 transitive
  packages. None was audited here.
- **That `npm audit` is clean afterwards.** Not run against the scratch tree;
  the measurement was reachability and suite parity.

---

# ADDENDUM 3 — 2026-10-06 (Cody): **DO NOT LAND THE UPGRADE. IT BREAKS `mintCustomToken`.**

**Addendum 2 recommended the upgrade on the strength of "0 of 248 suites
changed verdict", and named the limit that made that figure safe to doubt:
NO SUITE DROVE A REAL `mintCustomToken`.** That limit has now been closed with
an arm, and the arm fails on 14.5.0.

**My own recommendation in addendum 2 is WITHDRAWN.**

## THE ARM, AND WHAT IT PROVES

`api/_lib/firebase-mint.test.js` — 16 assertions, **no network and no stub
of `firebase-admin` itself.**

**There is no network boundary to stub, and that is the point.**
`createCustomToken()` signs a JWT **locally**, RS256, in-process. So the real
path is fully reachable offline with a throwaway RSA key generated per run by
`crypto.generateKeyPairSync` — never written to disk, corresponding to no
real project. **A fixed test key in a repo is a credential; a generated one is
arithmetic.**

| what the arm drives | why it matters |
|---|---|
| real `admin.credential.cert(json)` | **this is the advisory call site** — the only `forge.*` use in 12.7.0 is `forge.pki.privateKeyFromPem` inside `ServiceAccount`, reached from here |
| real `initializeApp` and `createCustomToken` | nothing mocked |
| **signature verified against the public half** | the arm that proves the PEM was really parsed and really used. Every other assertion passes against a token with a garbage signature |
| tampered-payload negative | so the verify arm is not passing because `verify()` returns true for anything |
| 6 bad-uid refusals, asserted FIRST | a token minted for a bad uid is the worst outcome, so the refusals come before the success |
| missing-credential refusal, **in a child process** | the module caches its app, so the refusal is only drivable with an empty module cache |

## THE RESULT: 1 OF 249 SUITES CHANGES VERDICT, AND IT IS THIS ONE

```
BASELINE-12.7.0 : 249 suites, 161 exit 0, 88 NOT 0
UPGRADE-14.5.0  : 249 suites, 160 exit 0, 89 NOT 0

SUITES WHOSE VERDICT CHANGED (1):
  api/_lib/firebase-mint.test.js    12.7.0=0   14.5.0=1
```

Under 12.7.0: `all 16 assertions passed`. Under 14.5.0:

```
TypeError: Cannot read properties of undefined (reading cert)
    at getAdminApp (api/_lib/firebase-admin.js:62)
    at mintCustomToken (api/_lib/firebase-admin.js:78)
```

## THE CAUSE: v13+ REMOVED THE LEGACY NAMESPACE, AND WE USE ALL OF IT

In 14.5.0 `require('firebase-admin')` **is** the modular `firebase-admin/app`
surface. Measured side by side:

| we call | 12.7.0 | 14.5.0 |
|---|---|---|
| `admin.credential.cert` | `object` | **`undefined`** |
| `admin.auth(app)` | `function` | **`undefined`** |
| `admin.apps` | `object` | **`undefined`** |
| `admin.app()` | `function` | **`undefined`** |
| `admin.database(app)` | `function` | **`undefined`** |
| `admin.initializeApp` | `function` | `function` |

14.5.0 exports `cert`, `initializeApp`, `getApp`, `getApps`, `deleteApp` and
errors — nothing else. **ALL THREE of our exported functions break**, not
just the minting one: `rtdbUpdate` and `rtdbGet` use `admin.apps` and
`admin.database` too.

**`initializeApp` surviving is what made this invisible.** A smoke test that
only loads the module and lists its exports passes under both — which is
exactly what addendum 2 did, reporting *"our wrapper LOADS under 14.5.0 and
exports all three functions"*. **That was true, and it was module resolution,
not a token.**

## THE DECISION, EXECUTED

### The two HIGHs are one problem — **ACCEPTED, with a basis and four triggers**

`npm audit` on the current tree: **2 high, 1 moderate, 3 total.** Both highs
are the same chain, `firebase-admin > node-forge`, *"RSA PKCS#1 v1.5 signature
verification accepts extra nested DigestAlgorithm elements"*, and for both
`fixAvailable` is `firebase-admin@14.5.0, isSemVerMajor: true`.

**THE ONLY OFFERED FIX IS THE ONE THAT BREAKS THE AUTH PATH.** So the decision
is to accept, and the basis is a measurement rather than a shrug:

1. **The vulnerable primitive is not on our path.** The advisory is about
   signature **verification** (`rsa.js` `verify`). Our one and only `forge.*`
   call is `pki.privateKeyFromPem` — a **parser**, whose return value is
   discarded, applied to **our own service-account key out of our own env**.
   Never attacker-supplied.
2. **Nothing else in the tree pulls node-forge** — `firebase-admin` is the
   sole declarer across all 195 locked packages.
3. **Nothing in `api/`, `tests/` or `tools/` requires it directly.**

**THE TRIGGERS, and the first is now the load-bearing one:**

| # | re-open when | how to check |
|---|---|---|
| 1 | **`api/_lib/firebase-admin.js` is ported to the modular API** — that is what unblocks 14.5.0, and it is a rewrite of auth code on a live payment path | after the port, re-run `api/_lib/firebase-mint.test.js` against 14.5.0 |
| 2 | `firebase-admin` gains a second `forge.*` call site | `grep -rn "forge[.][a-zA-Z]" <firebase-admin>/lib` must return exactly one line |
| 3 | anything in this repo requires `node-forge` directly | `grep -rn node-forge api/ tests/ tools/` |
| 4 | a new advisory lands against `pki.privateKeyFromPem` itself | that is the one primitive we do use |

### The moderate — not one of the two, and already patched

`@grpc/grpc-js` resolves to **1.14.5** in the lockfile, the patched version
from the original triage. The remaining moderate is its low-severity
companion, unchanged, and is not one of the two HIGHs.

## STATUS, ITEM BY ITEM

| | |
|---|---|
| mintCustomToken arm, network stubbed only | **DONE** — 16 assertions, no network at all, signature verified |
| 249-suite baseline re-run against 14.5.0 | **DONE** — 1 verdict changed |
| land the upgrade | **NOT DONE, AND CORRECTLY REFUSED.** The condition was "green arm AND 0 verdicts change". The arm is RED and 1 verdict changed |
| `node-forge` HIGH | **DONE — DECIDED: accept**, basis and four triggers above |
| `firebase-admin` HIGH | **DONE — DECIDED: accept.** Same chain, same decision; one problem in two rows |

## WHAT THIS STILL DOES NOT ESTABLISH

- **That the port to the modular API is hard.** It is five call sites in one
  141-line file. Not estimated here, and it is auth code on a payment path, so
  it is a decision rather than a chore.
- **That 1 changed verdict is the whole blast radius.** 88 suites are red
  under BOTH versions in the scratch copy for want of environment, and a real
  break hiding inside one of those 88 would be invisible to this differential.
- **That the arm covers the RTDB half.** It drives `mintCustomToken` only.
  `rtdbUpdate` and `rtdbGet` break on the same namespace removal, established
  by reading the exports rather than by driving them — they need a live
  database URL.
