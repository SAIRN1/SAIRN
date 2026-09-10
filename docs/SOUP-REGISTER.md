# SOUP Register — Software of Unknown Provenance

**What this is.** Every third-party component this platform runs, with its
version, where it is used, what is known against it, and **a real stated reason
it is trusted**. The term is IEC 62304's: software nobody here wrote, whose
development process we cannot inspect, carried inside something that has to be
correct.

**Why it exists.** Started 2026-09-10 as one of three standing disciplines for
vertical work, alongside criticality tiering and requirements-to-test
traceability. It is **net-new** — nothing on this platform tracked dependencies
before this file.

**The rule this register is built on:** *"it is popular"* is not a reason. Every
entry below states what would go wrong if the component were malicious or
broken, and what bounds that. Where the honest answer is "nothing bounds it",
the entry says so rather than inventing comfort.

**Kept honest mechanically.** `python tools/soup_register_check.py` derives the
real set from `package.json`, `package-lock.json` and every root `*.html`, and
reports anything present in the code and missing here — or listed here and no
longer present. A register maintained by remembering is a register that goes
stale; this repo has that written down in six other places.

**And it was not honest enough on day one.** That checker reported
`CLEAN -- every running component is in the register` while a third browser
component was running unregistered on a floating major, because it only read
static `<script src>` tags and that one is injected from JS. Fixed 2026-09-10;
see the `tesseract.js` entry, which is kept as the worked example. **A derived
check is only as wide as the shape it can see, and the shape it cannot see is
the entry it will never ask you for.**

---

## Tier

Criticality tiering applies to components too, not only to features. The tier
below is **the worst consequence of that component failing or being hostile**,
not how likely it is.

| Tier | Meaning |
|---|---|
| **A** | Catastrophic — money moves wrongly, a regulated record is corrupted, or authentication is bypassed |
| **B** | Serious — data loss or exposure without a regulatory dimension |
| **C** | Contained — a feature degrades, nothing else is reachable |

---

## Server-side (npm, runs in Vercel serverless functions)

Three direct dependencies. The repo ran **zero npm dependencies** until
2026-08-06 and `api/_lib/auth.js` still carries the header explaining why —
that restraint is itself part of the provenance story, and each addition below
had to argue for itself.

| Component | Version | Licence | Tier | Used by |
|---|---|---|---|---|
| `@simplewebauthn/server` | 13.3.2 | MIT | **A** | `api/sd-webauthn.js` — StoneDesk passkey login |
| `firebase-admin` | 12.7.0 | Apache-2.0 | **A** | SAIRNcash real-auth sync |
| `stripe` | 17.7.0 | MIT | **A** | `api/sairncash/checkout.js` |

### `@simplewebauthn/server` — why it is trusted

**Because the alternative is worse, and that is the whole argument.** The
`package.json` header states it: hand-rolling WebAuthn attestation and assertion
verification means COSE key parsing, CBOR decoding and signature verification —
exactly the class of security-critical crypto that should not be custom code.
A subtle bug in hand-rolled verification is an authentication bypass that looks
like working login.

**What a hostile version could do:** accept a forged assertion, i.e. log an
attacker in as any registered user of a StoneDesk licence.

**What bounds it:** nothing at the library boundary. The pin is `^13.3.2`, so a
patched-in minor is installed without a commit here. **This is the sharpest
unbounded entry in the register** and is recorded as such rather than softened.

### `firebase-admin` — why it is trusted

Google-maintained, Apache-2.0, and the server half of an auth product whose
client half is already the trust anchor for SAIRNcash's sign-in. Replacing it
would mean hand-rolling token verification against Google's JWKS — the same
argument as WebAuthn above, one tier less exotic.

**What a hostile version could do:** validate a forged ID token, or exfiltrate
service-account credentials it is already given.

**What bounds it:** the service account's own scope, which is not narrow. Worth
a real read if SAIRNcash ever carries more than sign-in.

### `stripe` — why it is trusted

The vendor's own SDK for the vendor's own API. Using anything else to talk to
Stripe means reimplementing request signing and webhook signature verification,
and a webhook-verification bug is *"accept a payment event that never
happened"*.

**What a hostile version could do:** report a payment as succeeded that did not,
or leak the secret key it holds.

**What bounds it:** `STRIPE_SECRET_KEY` is not currently configured in Vercel —
`api/sairncash/checkout.js` returns `{"error":"Stripe not configured"}` today
(its own open-work row). So the blast radius is presently zero and **will not
be once that key is set**. Re-read this entry at that moment.

### Transitive

**189 top-level entries in `package-lock.json`** against 3 declared
dependencies. They are not individually assessed and this register does not
pretend otherwise — that is the honest state, not an omission. What exists:

- `package-lock.json` is committed, so the tree is reproducible;
- one explicit `overrides` entry, `uuid >= 11.1.1` (installed: 14.0.2), added to
  force a transitive dependency past a known-bad range — the one place this repo
  has already exercised a supply-chain response;
- GitHub Dependabot is enabled and reports against the default branch. **The two
  moderate alerts open on 2026-09-10 are TRIAGED AND FIXED** — see the next
  subsection. The earlier version of this bullet said "one moderate alert",
  said it was untriaged because `gh` is not installed here, and was wrong about
  the count; the real number came off GitHub's own push output.

### The `qs` alerts — triaged 2026-09-10, and `gh` was never needed

**Both alerts were the same package.** `npm audit --json` reads the committed
lockfile and needs no GitHub credential at all, which is what the previous
"needs the GitHub UI or an authenticated API call" bullet had wrong — the
blocker was assumed, not tested.

| Advisory | Flaw is in | Trigger | Affected |
|---|---|---|---|
| `GHSA-x5fp-wj9c-mxmx` | `qs.parse` | bracket-key + comma values, needs `comma: true` | 6.14.2 – 6.15.3 |
| `GHSA-4mjr-xmp4-gh2g` | `qs.stringify` | an object whose `constructor.isBuffer` is truthy but not callable | >= 2.2.5 < 6.16.0 |

**`qs@6.15.3` was transitive, pulled by `stripe@17.7.0` through `^6.11.0`.**
6.16.0 satisfies that range, so the fix is a **lockfile-only** bump — one
package changed, `package.json` untouched, still three direct dependencies.
`npm audit` now reports 0 vulnerabilities. Deliberately done with
`npm update qs --package-lock-only`, not `npm install qs@6.16.0`, which was
tried first and **added `qs` as a fourth direct dependency** — a register entry
for a package no SAIRN file imports.

**Reachability, read rather than assumed, because it changes what the fix is
worth:**

- **`GHSA-x5fp` was never reachable.** `stripe@17.7.0` references `qs` exactly
  once, in `cjs/utils.js`, and it calls **`qs.stringify` only** —
  `queryStringifyRequestData`, serialising outbound request data. It never calls
  `qs.parse`. Verified by unpacking the published tarball, not by reasoning
  about the SDK.
- **`GHSA-4mjr` was reachable, and by a wider door than its own advisory
  describes.** The advisory frames it as a `parse`-then-`stringify` round trip
  needing `plainObjects: true` or `allowPrototypes: true`. The actual defect is
  one line in `utils.js`: 6.15.3 tests `obj.constructor.isBuffer &&
  obj.constructor.isBuffer(obj)` — truthy, not callable — and 6.16.0 tests
  `typeof obj.constructor.isBuffer === 'function'`. **Any** object with an own
  `constructor.isBuffer` that is truthy and not a function reaches it, and
  `JSON.parse` sets such a key freely. `api/sairncash/checkout.js` passes
  `req.body.email` straight into `stripe.checkout.sessions.create`, so
  `{"email":{"constructor":{"isBuffer":"x"}}}` on an unauthenticated POST is
  that shape. **No `qs.parse` required.**
- **What bounded it, and it is not the code being careful about this:** every
  Stripe call in `api/sairncash/` sits inside a `try/catch` that answers a 500
  JSON error, so the `TypeError` became a 500 rather than a dead worker. On top
  of that, `STRIPE_SECRET_KEY` is unset, so `checkout.js` returns
  `{"error":"Stripe not configured"}` before `stripe` is ever required. Two
  incidental bounds, neither designed for this — which is exactly why the bump
  is the fix rather than the analysis.

---

## Browser-side (loaded from a CDN at run time)

This is the half a `package.json` audit does not see, and it is the half that had
the weaker provenance story. **As of 2026-09-10 all four are pinned to an exact
version and carry a `sha384` integrity hash with `crossorigin=anonymous`** —
without the `crossorigin`, the browser does not check the hash at all.

| Component | Version | Tier | Loaded by | SRI |
|---|---|---|---|---|
| `@supabase/supabase-js` | 2.116.0 (pinned) | **A** | `sairnbiz.html`, `stonedesk.html` | ✓ sha384 |
| `qrcodejs` | 1.0.0 (pinned) | **C** | `stonedesk.html` | ✓ sha384 |
| `tesseract.js` | 5.1.1 (pinned) | **B** | `sairnlaw.html` (injected on demand) | ✓ sha384, entry script only |

### `@supabase/supabase-js@2.116.0` — why it is trusted

**It is the client for the database this platform already depends on entirely.**
That is a real reason, and on its own it was not sufficient, because of *how* it
used to be loaded: `@2`, a floating major, resolving to whatever jsDelivr served
that day, in the same page as the licence key and the session token. The bytes
running in a customer's browser could change with no commit, no review, and no
notice here. Pinned and hashed in `799d78db`.

**What a hostile version could do:** read `localStorage` and `sessionStorage` on
two apps, including `sd_session_token` and every licence key, and exfiltrate them.

**What bounds it:** the integrity hash — a substituted file now fails to execute
rather than executing undetected. Moving to a new 2.x is a commit with a new
hash, which is the point.

### `qrcodejs@1.0.0` — why it is trusted

Pinned to an exact version, and it does one thing: render a QR code into a div.
It is **not** given the session token or the licence key, and nothing downstream
of it makes a decision — the worst realistic failure is a QR code that does not
scan.

**What a hostile version could do:** same-origin script access like any other
loaded script — so in principle the same reach as the entry above. It is tiered
**C** on consequence-of-malfunction and would be **A** on
consequence-of-compromise; that distinction is stated because collapsing the two
is how a "harmless" library gets waved through.

**What bounds it:** the integrity hash, cross-checked rather than computed once
— see `799d78db` for how.

### `tesseract.js@5.1.1` — the entry this register missed, and the only partly-covered one

**It is trusted because it is the only way the OCR feature works without sending
a client's document to a third-party service.** SAIRNlaw's OCR runs entirely in
the browser: the alternative is uploading privileged client material to a cloud
OCR API, which is worse for exactly the reason this app exists. That is the
stated reason, and it is a real one.

**How it was missed, recorded because the mechanism matters more than the
finding.** It is injected from JS —
`document.createElement('script'); s.src = '…'` — rather than written as a
`<script src>` tag. That single property made it invisible to three independent
checks at the same time: Semgrep's `missing-integrity` rule, StoneDesk's own
Layer 12 SRI walk, and **this register's own derived checker**, which reported
`CLEAN -- every running component is in the register` while this component was
running, unregistered, on a floating major. `tools/soup_register_check.py` now
reads both shapes and states in its own docstring which loader shapes it still
cannot see.

**Tier B, and the tier table above does not fit it cleanly — said out loud
rather than rounded.** SAIRNlaw holds privileged client matter records, so a
compromise is a confidentiality breach of regulated material, which is well past
C's *"a feature degrades"*. But **B** is defined as exposure *"without a
regulatory dimension"* and this has one, while **A** is defined by money moving
wrongly, a record being **corrupted**, or authentication being bypassed — and
none of those three apply: nothing pays through OCR, it writes nothing without a
human reviewing the extracted text first (the modal says so), and it is not in
an auth path. Tiered **B** because A's three named triggers are all absent, and
recorded here that the table needs a confidentiality axis it does not have.
Rounding this to A to avoid the awkwardness would make every tier meaningless.

**What a hostile version could do:** the entry script runs in the page's own
context, so it has the same reach as any other script on the page — read the
session token and licence key from storage, read any matter document already in
the DOM, and exfiltrate. It also receives the image file being OCR'd, which is
by definition a client document.

**What bounds it — and this is the entry to read honestly.** The integrity hash
covers **one of four fetched artefacts**. Verified by reading the shipped files,
not assumed:

| Fetched at run time | From | Hashed? |
|---|---|---|
| `tesseract.min.js` (entry, main thread) | `cdn.jsdelivr.net/npm/tesseract.js@5.1.1` | **✓ sha384** |
| `worker.min.js` | same pinned path | ✗ no supported way |
| `tesseract.js-core` (wasm) | `cdn.jsdelivr.net/npm/tesseract.js-core@…` | ✗ no supported way |
| `@tesseract.js-data/<lang>` (traineddata) | `cdn.jsdelivr.net/npm/@tesseract.js-data/…` | ✗ no supported way |

The hashed one is the one that runs in the page's own context with access to the
DOM and the session token, which is the artefact whose compromise is worst. The
other three run inside a Worker. **That is a reduction in reach, not a
boundary** — a hostile worker still receives every document put through OCR and
can reach the network. Nothing this repo controls bounds those three, and per
this register's own rule, *"nothing"* is an acceptable answer that has to be
written down rather than left blank.

**Also true and out of scope for this entry:** `sairnlaw.html` has no
Content-Security-Policy at all, unlike `stonedesk.html`. So there is no
`script-src` narrowing which hosts these four fetches may come from. Recorded
here because it is the control that would bound the three unhashed artefacts,
and it does not exist yet.

---

## What this register does NOT claim

- **It is not an audit.** Nothing below the three direct npm dependencies has
  been read. 189 transitive packages are named by the lockfile and assessed by
  nobody.
- **It is not a licence-compliance review.** Licences are recorded because the
  lockfile states them, not because anyone checked obligations.
- **It does not track the toolchain** — Node, Python, `node --check`, the
  checkers in `tools/`. Those shape what ships without running in production,
  and they are a deliberate second pass, not an oversight.
- **It has no CVE feed of its own.** Dependabot is the only automated watch, it
  covers npm only, and it sees none of the three CDN components. **The two
  moderate alerts open on 2026-09-10 are triaged and fixed** — both were `qs`,
  see the Transitive section. `npm audit` reports 0 vulnerabilities as of that
  date. **That is a snapshot, not a standing property**, and nothing in this
  repo runs `npm audit` on a schedule.
- **It does not cover a script element built by any loader shape other than a
  literal `document.createElement('script')`.** That is stated in the checker's
  own docstring too. The gap that let `tesseract.js` sit here unrecorded was
  exactly this kind of blind spot, one shape narrower.

---

## Adding an entry

A new dependency is a decision, not a convenience. Record, in the same commit
that adds it:

1. name, version, licence, and the exact files that use it;
2. its **tier** — worst consequence of failure, not likelihood;
3. **what a hostile version could do**, concretely;
4. **what bounds that**, and *"nothing"* is an acceptable answer that must be
   written down rather than left blank;
5. why the alternative — writing it here — is worse. If it is not worse, do not
   add the dependency.
