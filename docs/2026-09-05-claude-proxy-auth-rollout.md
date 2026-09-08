# Requiring a licence key on `api/claude.js` — the rollout, and the two decisions in it

**Written 2026-09-05 (Cody). Skills used: `owasp-security`, `sairn-software-architect`,
`sairn-decision-gate`.**

> **The interim fix is SHIPPED and LIVE-VERIFIED** — `max_tokens` capped at 4096
> in `callAnthropic()`, and the rate limiter moved out of the caller-controlled
> `is_demo` branch. Commit `8fe970a9`. Production probe: a request asking for
> 64000 tokens returned `stop_reason: max_tokens` with `output_tokens: 4096`.
>
> **That does not close the finding.** `/api/claude` still requires no
> credential. This document is the plan for the part that does, and it stops
> short of building the client half because two facts found while designing it
> change the shape of the work enough that they are Michael's call, not mine.

---

## 1. What has to become true

Every request to `/api/claude` carries a credential the server can validate, and
the server refuses those that do not — without any window in which a live app's
AI feature breaks because its client had not caught up yet.

## 2. The two facts that shape the plan

### FACT ONE — there are ~134 call sites, not 17, and most bypass their own wrapper

Measured off the files, comment-stripped, not estimated:

| app | call sites | | app | call sites |
|---|---|---|---|---|
| **stonedesk** | **85** | | sairnlegacy | 3 |
| sairnbuild | 8 | | sairnsenior | 3 |
| sairngrounds | 8 | | sairnlaw | 3 |
| sairnscape | 4 | | sairnbiz | 2 |
| sairnvet | 4 | | sairnroofing | 2 |
| sairncare | 3 | | sairnfreedom | 1 |
| sairncash | 3 | | sairnmechanical | 1 |
| sairndental | 3 | | | |
| sairndesign | 3 | | **TOTAL** | **~134** |

**StoneDesk has ONE `fetch(PROXY, …)` and eighty-four other calls that hardcode
the URL** — 71 as `'https://sairn.vercel.app/api/claude'`, 3 with double quotes,
10 through a `SAIRN_API` const that is *redeclared locally in at least three
places*. The `callClaude()` wrapper exists and most of the app ignores it.

**I nearly reported this as 1 site.** My first count matched `fetch(\s*PROXY`
and found exactly one, which was true and useless. A second pass over the raw
call forms found the other eighty-four. Recorded because the first number was
the one that would have made this look like an afternoon's work.

### FACT TWO — SAIRNcash has no licence key at all, and never did

Every other app already holds a bearer licence key and already sends it to
*other* endpoints. SAIRNcash is a consumer app: it identifies a user by
`sairncash_did` (a device id) plus a Stripe subscription in `sairncash_sub`.
There is no SAIRN licence key anywhere in it.

It also sends `is_demo: false` — which is precisely why the `is_demo` bypass
existed, and why until today SAIRNcash's AI calls had **no cost control of any
kind**. The interim fix already changed that.

So "require a licence key" cannot be uniform. SAIRNcash needs its own answer.

---

## 3. DECISION ONE — how the client sends the credential

### Option A — edit all ~134 call sites

Explicit and readable: every call site shows its own auth. But it is ~134 hand
edits across 16 files, and **this repo's syntax rule forbids bulk find-replace**,
which is the only thing that would make it quick. High edit-risk for zero
architectural gain.

### Option B — route every site through one wrapper per app, then add auth there

The right end state — one `callClaude()` per app instead of 85 copies of a
fetch. But it is the same ~134 edits *plus* the behavioural risk of rewriting
call sites that currently differ from each other in ways nobody has catalogued.
A big refactor riding along with a security fix, which this repo's
differential-review discipline specifically warns against.

### Option C — one `fetch` wrapper per app that attaches the header — **RECOMMENDED**

One insertion per app, **16 edits total, zero call-site changes**:

```js
// Installed ONCE, near the top of the app's script. Every call to the Claude
// proxy carries the licence key from here on, including the eighty-four in
// this file that hardcode the URL and never went through callClaude().
(function () {
  var real = window.fetch;
  window.fetch = function (input, init) {
    var url = typeof input === 'string' ? input : (input && input.url) || '';
    if (url.indexOf('/api/claude') !== -1) {
      init = init || {};
      init.headers = Object.assign({}, init.headers);
      if (!init.headers.Authorization && !init.headers.authorization) {
        var k = licenceKey();               // each app's own accessor
        if (k) init.headers.Authorization = 'Bearer ' + k;
      }
    }
    return real(input, init);
  };
})();
```

**Why it wins here:** it is the only option whose blast radius is proportional
to the change. It touches no call site, so no AI feature can break from a
mis-edited fetch; it is one reversible block per file; and StoneDesk already has
precedent for wrapping `fetch` (`installStreamingHook`, `installHandoffHook`).

**Its real cost, stated rather than buried:** auth becomes invisible at the call
site. A reader of any of those 85 fetches will not see a credential. That is
genuine "spooky action" and it is the argument for Option B. It is mitigated by
a loud comment at the install point and by the server-side observe phase, which
*measures* whether the header actually arrives instead of trusting that it does
— but it is not eliminated.

**If Michael prefers B**, the honest estimate is a multi-session refactor that
should be its own piece of work with its own review, not folded into this.

## 4. DECISION TWO — what SAIRNcash does

**Recommended: SAIRNcash stops calling `/api/claude` and gets its own endpoint**,
`api/sairncash/ai.js`, which verifies the Stripe subscription server-side and
then calls `callAnthropic()` in-process.

This is not a new pattern — it is exactly what `api/law-auth.js:596` and
`api/sc-ai.js:259` already do, twice-proven on this platform. It also *gains*
something: SAIRNcash currently has no server-side check that an AI caller is a
paying subscriber at all, and this adds one.

The alternative — minting a SAIRN licence key per SAIRNcash subscriber — drags
the licence system into a consumer product it was not built for.

**Consequence for sequencing:** SAIRNcash's three call sites must move *before*
enforcement, or its AI breaks the moment the flag flips.

---

## 5. The sequencing, which is the part that must not be rushed

Modelled on the pattern this platform already uses for
`SAIRN_AI_RATE_LIMIT_MODE`: **observe, measure, then enforce, behind an env flag
that can be reverted without a deploy.**

**Phase 0 — done.** Interim fix shipped and live-verified. `8fe970a9`.

**Phase 1 — server reads and records, enforces nothing.**
`api/claude.js` reads `Authorization`, validates the key when present, and
records `auth_present` / `auth_valid` per `app_id`. Behind
`SAIRN_CLAUDE_AUTH_MODE`, default `observe`. **Deploying this cannot break
anything, because nothing is refused.** Ship first, on its own.

**Phase 2 — clients start sending the key.** The 15 licence-holding apps get the
wrapper from §3. SAIRNcash gets its own endpoint from §4. Still nothing is
enforced, so a missed app costs nothing yet.

**Phase 3 — measure, and let the data name what was missed.** Read Phase 1's
counters for at least a week. **The gate to Phase 4 is that every live `app_id`
shows ~100% `auth_valid` for a sustained period** — not "we updated all the
files". The counters are what catch the call site nobody found; the file count
is not evidence.

**Phase 4 — enforce.** Flip `SAIRN_CLAUDE_AUTH_MODE=enforce`. Reversible in
seconds with no deploy. Verify with the same shape of probe that found the hole:
an unauthenticated request must return 401.

**Phase 5 — independent review**, per the standing rule for a live financial
exposure. Both the interim fix and the full requirement are in scope, and the
author of a security change is the worst person to certify it.

### Premortem — "it is a month from now and this broke a customer's AI"

1. **An app was missed and its AI went dead at the flip.** → Phase 3's gate is
   measured traffic, not a file checklist, precisely for this.
2. **A licence-less path was missed** — a pre-login demo surface calling AI with
   no key to send. → Phase 1's counters distinguish *absent* from *invalid*;
   an app showing persistent `auth_present: false` is that case, and it surfaces
   before enforcement.
3. **The fetch wrapper was installed after the first AI call could fire.** →
   Install at the top of the script, and assert its position in a test rather
   than trusting placement.
4. **A third party depends on the open proxy.** Unlikely but unfalsifiable from
   here; Phase 3's counters would show traffic from an `app_id` whose own client
   is fully updated yet still arrives unauthenticated.

---

## 6. What I am NOT doing until Michael answers §3 and §4

Building Phase 2. Both decisions change what Phase 2 *is* — 16 edits or ~134,
and whether SAIRNcash needs a new endpoint first. Phase 1 is independent of
both, non-breaking, and is the thing that makes Phase 3's gate possible, so it
can be built immediately either way.
