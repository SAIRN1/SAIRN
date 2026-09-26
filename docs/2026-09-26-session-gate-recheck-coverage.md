# A session gate that never asks again — 131 of 132, and the control that says it is closed

**Derived 2026-09-26 (Fourth).** Measured by `tools/session_recheck_coverage.py`
at HEAD; every figure below is that tool's output, not a one-off script.

---

## 0. The finding

`api/sd-data.js` contains **132 `verifySessionToken()` gates and exactly one
`credentialStillActive()` re-check.** A credential DEACTIVATED after a token was
issued keeps read and write access on the other 131 for the remaining life of that
token — **up to 12 hours**, `SESSION_TTL_MS`.

**The commit that closed it says it closed the data path.** Verbatim from
`api/sd-data.js`, beside the one re-check:

> *"Until 2026-09-16 a deactivated employee kept read and write access to every
> gated resource here for the remaining life of a 12h token — and deactivation is
> the one control an owner has for somebody who has just left. … **NOTHING CLOSED
> IT FOR THE DATA PATH, which is thirteen apps' resources.**"*

That paragraph is the justification for the fix, and the fix is real. What it
covers is not "the data path": the re-check sits inside

```js
if (SD_SESSION_GATED[resource] && SD_SESSION_GATED[resource].indexOf(action) !== -1) {
```

so it runs for **34 resources / 70 (resource, action) pairs** and for nothing
else. Every later per-app branch — SAIRNroofing's ~40 gates, SAIRNcare's ~27,
SAIRNsenior's ~17, SAIRNcode's 6, and the rest — calls `verifySessionToken` and
proceeds.

**`verifySessionToken()` is not at fault and is not the fix.** It is strong at
what it does, driven in-process: signature verified through the rotation-aware
verifier, `typ` checked so a pre-auth token cannot masquerade as a session, app
and role checked against `ROLES_BY_APP`, `license_hash` bound, and **`exp`
enforced with a missing `exp` REJECTED**. What it cannot do is prove anything
about *now* — there is no server-side session store on this platform, every
endpoint being a stateless function, so revocation before `exp` has to be a
database read and that read is the thing 131 gates skip.

---

## 1. THE CONTROL THAT EXISTS IS SATISFIED BY ONE CALL SITE, AND THAT IS THE SHARPER HALF

`api/sd-data-active-credential.test.js` — **8 arms, all green at HEAD**. What they
assert:

| arm | what it checks |
|---|---|
| imported, not reimplemented | `require('./_lib/auth')` present, `credentialStillActive` referenced, no local `AUTH_TABLE_BY_APP` |
| called and awaited | `/await\s+credentialStillActive\(/` **matches** |
| ORDER | the re-check runs after the token verify and before the first handler |
| refusal | 403 `CREDENTIAL_INACTIVE` |
| CONTROL | `NO_ACTIVE_CHECK` does **not** refuse — a transport failure is not a deactivation |
| CONTROL | the outcome is logged |
| CONTROL | the logging cannot itself refuse a request |
| CONTROL | *"this file would notice the gate being **deleted**"* |

**Every one of those is true of the single gate at line 1249 and says nothing
about the other 131.** The suite is a presence-and-shape check on one call site:
`/await\s+credentialStillActive\(/` is satisfied by one match, and the last arm
guards against the gate being *deleted* — which it is not — while nothing asserts
**coverage**.

So the platform has a green control, a correct fix, and an accurate-sounding
comment, and the property is 1 of 132 done. That combination is this codebase's
own recorded failure shape — a check that passes while the thing it names is
barely started — and it is why the new tool measures a **ratio** rather than a
presence.

---

## 2. THE PLATFORM NUMBERS, AND THE FIRST ONE I PRODUCED WAS WRONG

**Counting only `credentialStillActive(` gives 3 of 222 gates — 1.4% — and that
figure is wrong.** It is recorded here because it is exactly the sort of number
that gets quoted. Every `api/*-auth.js` endpoint re-checks by a **different
mechanism**: it loads the employee row filtered `active=eq.true` inside
`loadEmployee()`, so a deactivated credential simply does not come back and the
route refuses without ever naming the re-check. Reporting 1.4% would have accused
seventeen correct files.

Both mechanisms counted, from `tools/session_recheck_coverage.py`:

```
GATES_TOTAL:222
GATES_IN_FILES_WITH_NEITHER_MECHANISM:12
GATES_UNCOVERED_INSIDE_PARTIAL_FILES:131
FILES_WITH_NEITHER:11
FILES_PARTIAL:1
```

### 2.1 PARTIAL — one file, and it is the whole original finding

| file | gates | explicit re-checks | uncovered |
|---|---|---|---|
| `api/sd-data.js` | 132 | 1 | **131** |

### 2.2 NEITHER MECHANISM — 11 files, 12 gates, and some of them carry money

A deactivated credential works on these until the token expires, by either route:

| file | gates |
|---|---|
| `api/sd-sub-data.js` | 2 |
| `api/accounting.js` | 1 |
| `api/ledger.js` | 1 |
| `api/alf-alerts.js` | 1 |
| `api/sc-credentials.js` | 1 |
| `api/sc-eligibility.js` | 1 |
| `api/sc-ai.js` | 1 |
| `api/legal-citator.js` | 1 |
| `api/legal-deadlines.js` | 1 |
| `api/legal-reference.js` | 1 |
| `api/stonedesk-track.js` | 1 |

`accounting.js` and `ledger.js` are money. `alf-alerts.js` is a life-safety alert
sweep. `sc-credentials.js` and `sc-eligibility.js` touch named-patient data.

**WHAT THIS LIST IS NOT.** It is a file-level count and it is not a per-gate
audit. Whether a given gate *needs* the re-check is per endpoint — a read-only or
self-scoped route is a weaker case than a money write — and that judgement is not
automatable and is not made here. **The per-gate read of those 12 is the next unit
of work and it is not done.**

---

## 3. THE FIX IS ONE EDIT, NOT 131

The obvious remedy — add `credentialStillActive` beside each of 131 gates — is the
wrong shape: 131 chances to get it wrong, 131 diffs to review, and a 132nd gate
added next week with nothing to stop it.

`api/sd-data.js` has a **single entry point** (`module.exports = async (req, res)`)
and the licence is already resolved there before any branch runs. A **pre-gate**
at that choke point — if the request carries a session token at all, re-check the
credential once and refuse 403 `CREDENTIAL_INACTIVE` — covers all 132 gates in one
edit, costs one database read per authenticated request, and inherits the
`NO_ACTIVE_CHECK` third state already written and already argued: a transport
failure is not a deactivation, so it logs and continues.

**One thing to decide rather than assume, and it is why this is a proposal and not
a patch:** the pre-gate needs the caller's `app`, and a token names its own app,
so the re-check can be made before any resource dispatch — but `AUTH_TABLE_BY_APP`
has no entry for some apps, which is exactly what `NO_ACTIVE_CHECK` reports. The
existing gate handles that by continuing and logging. A pre-gate would do the same
and would therefore **log once per request** for those apps rather than once per
gated resource, which is a louder log for the same fact. That is a real
operational change and belongs to whoever owns the file.

**NOT APPLIED. `api/sd-data.js` is inside cc's active `cc-queue10` claim** (which
declares it in FILES and is working `gh_push` and blob conversions in the same
file). Editing 132 gates' worth of choke point under that claim is a guaranteed
rebase collision on the platform's largest shared API file. Flagged rather than
pushed past.

---

## 4. WHAT LANDED INSTEAD, AND WHY IT IS THE PART THAT LASTS

`tools/session_recheck_coverage.py` — a **ratchet, not a pass/fail**, pinned to
`docs/session-recheck-coverage.json`.

* It counts **both** mechanisms, so it cannot repeat the 1.4% mistake.
* It reports `PARTIAL` separately from `covered`, which is the distinction the
  existing presence-check cannot make.
* It **fails when coverage gets worse** — a new bare gate, or a new file with no
  mechanism — so the 132nd gate cannot arrive unnoticed while the fix is blocked.
* It reports `IMPROVED` and asks to be re-pinned, so closing gates is recorded
  rather than lost.
* **A ratchet is not a pass, and it says so on every run:** *"OK below means 'no
  worse than the pinned state', never 'closed'."* An absent or unparseable pin
  file is **exit 2 COULD NOT TELL**, never 0.

`tests/run_session_recheck_coverage_probe.py` — 9 sections, both directions on
every arm, in a throwaway repo-shaped sandbox:

* a new **unprotected** gate → regression, exit 1 · a new **protected** gate →
  silent (a ratchet that fired on every new gate would be switched off in a day)
* 10 gates + 1 re-check → `PARTIAL` with **9** uncovered, not 0
* **the arm against this tool's own first wrong number**: a gate protected only by
  `active=eq.true` reads as covered — and stripping that route puts the same file
  back to `NEITHER`, so the arm cannot pass on a tool that calls everything covered
* a commented-out gate is not a gate · an unparseable pin file is exit 2
* and a closing arm asserting the tool **wrote nothing** to the real repo

---

## 5. Limits

* **No live check.** Every figure is the repository at HEAD. The in-process drive
  that established `exp` enforcement, licence revocation (`status` re-read per
  request → 403 `LICENSE_INACTIVE` on revoked/suspended/cancelled) and the
  zero-employee-table-reads result used a stubbed transport, not the deployed
  function.
* **The 12 `NEITHER` gates are not individually read**, and the per-endpoint
  judgement of whether each needs the re-check is not made.
* **The fix is proposed, not applied**, and its one open operational question
  (log volume on `NO_ACTIVE_CHECK` apps) is not decided.
* **No app file was touched.** Two new files and one pinned JSON.
