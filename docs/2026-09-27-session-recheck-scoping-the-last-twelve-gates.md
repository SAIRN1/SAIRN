# The last twelve session gates with no re-check — scoping, not a fix

**Written 2026-09-27 (Fourth). This is a SCOPE, and nothing in it is
implemented.** Item 9 asked for the mechanism to be scoped; the ordering,
per-file feasibility and the three real decisions are below, each grounded in the
files rather than in the pattern.

## What the gap is, and why it is not "eleven files need a line adding"

`verifySessionToken()` proves a token was minted by us and has not expired. **It
proves nothing about now.** There is no server-side session store on this
platform, so a credential DEACTIVATED after its token was issued keeps working
until `exp` — up to 12 hours. Deactivation is the one control an owner has over
somebody who has just left.

`tools/session_recheck_coverage.py` measures which gates have a re-check. Re-run
2026-09-27 — **do not quote these from here, run it**:

```
GATES_IN_FILES_WITH_NEITHER_MECHANISM:12
FILES_WITH_NEITHER:11
```

`api/sd-data.js` closed **132 gates in one edit** on 2026-09-26 with a single
pre-gate at the dispatcher entry point, and that is the precedent to copy. Its own
header states the reason plainly: *"131 separate edits would have been 131 chances
to miss one."*

## The survey — measured per file, not assumed from the pattern

Every one of the eleven has **exactly one `module.exports` handler**, and ten of
the eleven have **exactly one `verifySessionToken()` call**. That is the shape the
pre-gate needs, and it is why this is a small job per file rather than a
refactor.

| File | Gates | App the token is pinned to | `rest`/`headers` already built | Effective? |
|---|---|---|---|---|
| `api/accounting.js` | 1 | `appId` — **caller-supplied** | yes | **partly** |
| `api/ledger.js` | 1 | `appId` — **caller-supplied** | yes | **partly** |
| `api/alf-alerts.js` | 1 | `'sairncare'` | **no** | yes |
| `api/legal-citator.js` | 1 | `'sairnlaw'` | **no** | yes |
| `api/legal-deadlines.js` | 1 | `'sairnlaw'` | **no** | yes |
| `api/legal-reference.js` | 1 | `'sairnlaw'` | **no** | yes |
| `api/sc-ai.js` | 1 | `APP` constant | **no** | yes |
| `api/sc-credentials.js` | 1 | `APP` constant | yes | yes |
| `api/sc-eligibility.js` | 1 | `APP` constant | yes | yes |
| `api/sd-sub-data.js` | 2 | — **two call sites** | yes | needs reading |
| `api/stonedesk-track.js` | 1 | `'stonedesk'` | headers only | yes |

## Ordering — money, then life-safety, then named-patient data

Not by ease. By what a deactivated credential can still reach:

1. **`api/accounting.js` and `api/ledger.js` — MONEY.** A departed employee's
   token still reaches the accounting-package connection and the ledger.
2. **`api/alf-alerts.js` — LIFE-SAFETY.** A SAIRNcare alert sweep. Fixed app, so
   the re-check is fully effective here with no caveat.
3. **`api/sc-credentials.js` and `api/sc-eligibility.js` — NAMED-PATIENT DATA**,
   and `sc-credentials` is itself the credential surface.
4. The three `legal-*` files, `sc-ai.js`, `stonedesk-track.js`.
5. **`api/sd-sub-data.js` LAST**, because it is the only one whose shape is not
   already settled — see below.

## Three decisions this needs, and they are decisions, not details

### 1. `accounting.js` and `ledger.js` can only be PARTLY closed, and saying otherwise would be the defect

Both pin the session to **`appId`, which the caller supplies**.
`credentialStillActive()` chooses the employee table from `AUTH_TABLE_BY_APP[
session.app]`, so:

- caller claims an app **with** an auth table → the re-check works;
- caller claims an app **without** one → `NO_ACTIVE_CHECK`, the third state.

The token's signature still binds it to *some* app, so a caller cannot simply
claim an unauthenticated app to dodge the check — `verifySessionToken` would
reject the mismatch. **But the coverage these two files get is a function of
which apps have auth tables, and that is not a constant.** Whatever lands here
must say so in the file, or `session_recheck_coverage.py` will read them as
covered and the residual will be invisible — which is the exact shape the
`sd-data.js` incident took, where an accurate-sounding comment sat beside a
property that was 1-of-132 done.

### 2. `NO_ACTIVE_CHECK` must continue the request, and must be LOGGED

Follow `api/sd-data.js:1249-1253` verbatim rather than re-reasoning it. A
transport failure is not a deactivation; refusing everybody whenever the database
blinks is a worse failure than the one being closed. **It is still not a pass** —
it is logged so a run of them is visible rather than silent.

The `sd-data.js` pre-gate also learned that **a missing row is only a
deactivation when the resource's expected app is KNOWN and matches the token's**;
its first draft told healthy users in the wrong app that their credential was
deactivated, and three arms of `api/sd-data-law-phase2-session.test.js` caught it
immediately. Nine of these eleven files have a FIXED app, so that ambiguity does
not arise for them — **but it does arise for `accounting.js` and `ledger.js`**,
and they are the two at the top of the ordering.

### 3. `api/sd-sub-data.js` has TWO call sites and must not get a pre-gate before somebody reads why

Two `verifySessionToken()` calls is the one shape the "one edit covers
everything" argument does not automatically fit. A pre-gate above both is
probably right and might be wrong — if the second call deliberately re-verifies
against a *different* app or licence, a single re-check above both would be
weaker than it looks. **This is the file where reading beats the pattern.**

## What would make the fix verifiable rather than merely present

- `tools/session_recheck_coverage.py` must move — it is a ratchet, so the pinned
  numbers change in the same commit, and **only after** the count actually falls.
- **Per-file arms that drive a DEACTIVATED credential**, not a missing one. The
  `sd-data.js` control was eight green arms every one of which was true of a
  single call site; presence is not coverage.
- **An ablation.** Deleting the pre-gate from `sd-data.js` once made every pinned
  aggregate read *better* — uncovered-in-partial 131 → 0 — so the fix could have
  been reverted in silence. Whatever lands here needs the same treatment before
  it is believed: delete it and confirm something goes red.

## What this scope does NOT claim

It does not claim the twelve gates NEED the re-check. `session_recheck_coverage.py`
says so about itself and it is right: *"whether a given gate needs the re-check is
per endpoint — a read-only or self-scoped route is a weaker case than a money
write — and that judgement is not automatable."* The ordering above is that
judgement made explicitly for these eleven files, and it is a recommendation, not
a measurement.

**Nothing here is implemented, and the gap is unchanged as of this commit.** Two
of these files touch money and one is a life-safety sweep, so an unowned scoping
document is a better state than the previous one — unowned and unscoped — and a
worse state than a fix.
