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
- GitHub Dependabot is enabled and reports against the default branch. **One
  moderate alert was open as of 2026-09-10**, surfaced on every `git push`
  ("GitHub found 1 vulnerability on SAIRN1/SAIRN's default branch"). It is not
  triaged here because the alert detail needs the GitHub UI or an authenticated
  API call, and `gh` is not installed in this clone. **Recorded as untriaged
  rather than assumed benign.**

---

## Browser-side (loaded from a CDN at run time)

This is the half a `package.json` audit does not see, and it is the half with
the weaker provenance story: these are fetched by the customer's browser from a
third-party host, at page load, with **no Subresource Integrity hash on either**.

| Component | Version | Tier | Loaded by | SRI |
|---|---|---|---|---|
| `@supabase/supabase-js` | **`@2` — floating major** | **A** | `sairnbiz.html`, `stonedesk.html` | ✗ none |
| `qrcodejs` | 1.0.0 (pinned) | **C** | `stonedesk.html` | ✗ none |

### `@supabase/supabase-js@2` — the weakest entry in this register

**It is trusted because it is the client for the database this platform already
depends on entirely.** That is a real reason and it is not sufficient on its own,
because of *how* it is loaded:

- **the version is a floating major.** `@2` resolves to whatever jsDelivr serves
  today. The bytes running in a customer's browser can change with no commit,
  no review and no notice here;
- **there is no `integrity` attribute**, so nothing detects a substituted file;
- it runs in the same page as the licence key and the session token.

**What a hostile version could do:** read `localStorage` and `sessionStorage` on
two apps, including `sd_session_token` and every licence key, and exfiltrate them.

**What bounds it:** jsDelivr's own integrity, and nothing this repo controls.
**Fixing it is a pin plus an SRI hash on both apps** — filed as its own open-work
row rather than done here, because changing how two live apps load their
database client is a change that wants its own verification, not a footnote in a
documentation commit.

### `qrcodejs@1.0.0` — why it is trusted

Pinned to an exact version, and it does one thing: render a QR code into a div.
It is **not** given the session token or the licence key, and nothing downstream
of it makes a decision — the worst realistic failure is a QR code that does not
scan.

**What a hostile version could do:** same-origin script access like any other
loaded script — so in principle the same reach as the entry above. It is tiered
**C** on consequence-of-malfunction and would be **A** on
consequence-of-compromise; that distinction is stated because collapsing the two
is how a "harmless" library gets waved through. It shares the missing-SRI
finding above and the same fix closes both.

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
  covers npm only, and it does not see either CDN script.

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
