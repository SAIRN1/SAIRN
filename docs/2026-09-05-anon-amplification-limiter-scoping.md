# Scoping: a rate limiter that actually works for the unauthenticated licence lookup

**Written 2026-09-05 (Cody). Skills used: `sairn-decision-gate` (Premortem), `sairn-software-architect`.
This is a PROPOSAL. Nothing in it is built. Michael's decision is "invest in a real
fix, scope it properly rather than rushing something inadequate" — this is that scope.**

---

## 1. The problem, as measured rather than as feared

Moving licence validation above the request-envelope gate closed a real
enumeration hole and is not in question. Its cost is:

> before — a junk token with a garbage body was refused **locally, for free**
> after  — every junk token costs one `license_keys` SELECT before anything else

A previously-free anonymous path became a database-amplification path.

**The surface is now SIXTEEN endpoints, not one.** `sd-data` and `sd-sub-data`
(2026-09-04), plus the fourteen reordered on 2026-09-05. If the deferred fifteen
`*-auth.js` handlers are done it becomes **thirty-one**. That growth is a
consequence of a fix that was correct; it is the reason this is worth real
infrastructure work rather than a patch.

**The existing limiter does not work, and this is measured, not suspected.**
`api/_lib/anon-rate-limit.js` shipped enforcing. Live: 40 concurrent junk-token
requests returned 40 × 401 and **not one 429**, against a limit of 20 in 60
seconds. Instrumentation showed the counts climbing in many parallel sequences —
a dozen or more instances each counting the same address from 1.

> **Horizontal scale-out defeats a per-instance counter, and it does so IN
> PROPORTION TO THE ATTACK.** Concurrency is what makes Vercel add instances, so
> a bigger flood spreads across more of them and every individual count gets
> *lower*. The design fails hardest against exactly the case it was written for.

It now defaults to observe, so today there is **no working limiter at all** on
any of the sixteen.

**The one property worth preserving from that design**, because it is what made
it safe to enforce by default: it counted only FAILED validations, so a valid
key accumulated nothing at any volume from any address. It could never refuse a
working customer. Any replacement that loses this property has to earn it back
some other way.

---

## 2. Options

Michael named two. A third is included because neither named option is
obviously right on its own, and rejecting it explicitly is cheaper than having
someone propose it in three weeks.

### Option A — a Vercel WAF rate-limit rule (platform layer, at the edge)

**Availability: CONFIRMED.** `list_teams` reports `sairn1s-projects` on plan
**`pro`**. WAF custom rules with the `rate_limit` action are a Pro feature.
Project is `prj_bj475nKLxC1TTmpFU6j7HVCSMEhn`, team `team_xlXR8IEKwOD7fvQQeiJtzxiT`.

**Capability, read off the CLI reference rather than assumed:**

| knob | range |
|---|---|
| `--rate-limit-window` | 10 – 3,600 seconds |
| `--rate-limit-requests` | 1 – 10,000,000 per window |
| `--rate-limit-keys` | `ip`, `ja4`, `header:<name>` |
| `--rate-limit-algo` | `fixed_window`, `token_bucket` |
| `--rate-limit-action` | `rate_limit`, `deny`, `challenge`, `log` |
| `--duration` | `1m`, `5m`, `15m`, `30m`, `1h` |

Rules are managed by `vercel firewall rules add/edit/list` + `vercel firewall
publish`, or `PUT /v1/security/firewall/config`, and are versioned with an
explicit activate step.

**Why it is the strongest option: it is the only one that stops the request
before it reaches compute or the database.** The firewall is evaluated by the
Edge Network ahead of routing — which is why a `bypass` action exists to
*"bypass firewall evaluation for requests matching `/api/internal`"*, and why
`ANOMALY_SCORE_EXCEEDED` is returned by the firewall rather than by a function.
A mitigated request therefore costs no function invocation and no Supabase round
trip. **It removes the amplification. B and C only bound it.**

It is also global by construction. There is no per-instance counter, which is
precisely the defect that made the current limiter inert.

**THE REAL COST, and it is not small.** A WAF rule matches on **request
attributes only**. It cannot know whether the licence turned out to be valid, so
it counts real customers alongside attackers — **losing the exact property that
made the previous design safe to enforce.** A dental practice behind one NAT is
one key; ten workstations syncing at 8am are one key. This is mitigable (set the
ceiling far above measured real use) but not eliminable, and the failure mode is
a real customer seeing a 429 from an origin the app does not control and cannot
explain.

**Second cost: the config lives outside this repo.** It is invisible to
`git log`, to every reviewer, and to every gate in this repository. That is the
same class of problem the seed-file push gate exists for, and it needs the same
answer (see §4).

### Option B — `checkRateLimit()` from `@vercel/firewall` (in code, platform-counted)

Same platform counter, called from inside the function against a rule id
pre-defined in the dashboard, with a caller-supplied `rateLimitKey`:

```js
const { rateLimited } = await checkRateLimit('anon-licence-lookup', {
  request, rateLimitKey: addressOf(req),
});
```

**This restores the property A costs us.** Call it only on the
failed-validation path, keyed by address, and the semantics are exactly Fourth's
— a valid key accumulates nothing — but the counter is platform-global instead
of a per-instance `Map`. That single substitution fixes the measured defect
without redesigning the intent.

`package.json` already exists (added for `@simplewebauthn/server`) and Vercel
installs dependencies for the functions, so adding `@vercel/firewall` is
routine.

**What it does NOT do: remove the amplification.** By the time we know
validation failed, the `license_keys` SELECT has already happened. It caps the
*next* requests from that address. That is what a limiter does — but it bounds
the cost rather than removing it, and on its own it leaves the first request of
every burst paid for.

### Option C — fuse the limiter into the licence lookup as one Postgres RPC — REJECTED

Not one of the two named; recorded so it is rejected on the record rather than
re-proposed later. The pattern already exists and is proven:
`public.sairn_ai_rate_limit_consume` takes `pg_advisory_xact_lock`, counts and
records inside one transaction. The same shape could check the anon counter and
return the licence row in a **single** round trip — exactly today's cost,
globally exact, no new vendor surface.

**Rejected for two reasons, the second decisive:**

1. **It does not reduce database load at all.** Every request still contacts
   Postgres. It bounds what an attacker *achieves*, not what the platform
   *pays*. The amplification factor stays at 1× either way.
2. **Blast radius.** It puts rate-limit state inside `api/_lib/license.js`,
   whose own header reads *"SHARED license-key validation. Single source of
   truth — do NOT fork this"* and which every app on the platform authenticates
   through. A bug there is a platform-wide authentication outage. That is the
   worst blast radius of the three for the least benefit.

---

## 3. Recommendation

**A and B together, in that order, and delete the in-memory `Map`.**

- **A is the fix.** It is the only option that removes the amplification instead
  of bounding it, it costs nothing per request, and it cannot be defeated by
  scale-out.
- **B is the precision layer that buys back what A costs.** A alone counts real
  customers; B counts only callers who already failed validation. Together the
  coarse ceiling never has to be set tight enough to endanger a real practice.
- **`anon-rate-limit.js`'s in-memory counting is deleted, not left dormant.** It
  is measured non-functional. Dormant code that looks like protection is worse
  than no code, and this repo has a standing rule against exactly that. Its
  header — which is an unusually honest post-mortem — should be preserved into
  whatever replaces it.

Neither A nor B is a code-only change: A is platform configuration with its own
verification and drift problem, B needs a dependency, a dashboard rule and a
fail-open test. That is why this is scoped rather than shipped tonight.

---

## 4. Premortem — "it is three months from now and this failed"

Stated as fact, per the framework, not hedged as possibility.

**1. The WAF rule refused a real practice.** A multi-site customer behind one
NAT crossed the IP ceiling during a morning sync. The app cannot explain it —
the 429 comes from an origin the app does not control, so the user sees a bare
failure with no SAIRN wording at all.
→ **Ship the rule in `log` action first and leave it there for a full week.**
Set the ceiling from *measured* traffic in the firewall log, never from a guess.
Only then switch to `rate_limit`. This is the whole reason A is staged rather
than published in one step.

**2. The rule silently stopped existing.** Someone disabled it, or a config
version was never activated, and nothing noticed for months. **This is the
`anon-rate-limit` failure repeating one layer up** — a protection nobody
verifies is not a protection.
→ **A committed checker**, `tools/waf_rule_check.py`, that reads the live config
from `GET /v1/security/firewall/config?projectId=…` and asserts the rule exists,
is **active**, and carries the expected window / limit / keys / action. Wired
into the push gate the same way the seed gate is, and **failing loudly on "could
not tell"** rather than treating silence as agreement.

**3. We never measured whether it worked.** Precisely what happened last time:
it shipped enforcing and was inert for a day while looking fine.
→ **The acceptance test is the same probe that exposed the last one** — 40
concurrent junk-token requests — and it must produce 429s before any of this is
called done. Not "the rule is configured". Observed refusals.

**4. `checkRateLimit()` failed and took the endpoint with it.** A firewall
service blip turned into a 500 on every request.
→ **It must fail OPEN**, the same standard as every other gate here, and that
must be **asserted in a test**, not stated in a comment. The existing limiter
gets this right and the replacement must not lose it.

**5. The limiter works and the amplification was never the real risk.** We spent
the effort on a flood that never came while `license_keys` itself had no index
on `key`, or the real exposure was something else entirely.
→ Cheap to check before building: confirm the `license_keys` lookup is an index
scan, and read a week of real traffic. If the observed anonymous volume is
trivial, **the honest recommendation may become "A only, in log mode, plus the
checker"** — and that is a legitimate outcome of this scoping, not a failure of it.

---

## 5. What I could NOT verify from here — needed before building

Stated as unknowns rather than assumed, because the last limiter was defeated by
an unverified assumption about how the platform behaves.

1. **Are WAF-mitigated requests billed, and do they count as function
   invocations?** The documentation corpus available here does not say. This
   matters: if a mitigated request still costs an invocation, A's headline
   benefit shrinks to "no database round trip" rather than "free". Verify in the
   usage dashboard or with Vercel support.
2. **The project's current firewall configuration.** No Vercel API token is
   available in this environment, so I could not read whether any rule already
   exists. `vercel firewall rules list --expand`, or
   `GET /v1/security/firewall/config?projectId=prj_bj475nKLxC1TTmpFU6j7HVCSMEhn`.
3. **Real traffic volume per IP.** This is the gating unknown for step 1 — the
   ceiling cannot be chosen without it, and choosing it by guess is how
   mitigation 1 above turns into incident 1 above.
4. **Whether `checkRateLimit()` requires the rule to pre-exist in the
   dashboard** (the docs say the id refers to a dashboard-configured rule) **and
   what latency it adds.** If it is a network call per invocation, B's cost is
   not zero and that changes how tightly A can be tuned.

---

## 6. Proposed sequence, if approved

1. Read the current firewall config and a week of traffic. **Answer §5.1–5.4
   first.** If the volume is trivial, re-open the recommendation.
2. Add the WAF rule in **`log`** action, keyed by `ip`, scoped to `/api/*`.
   Publish. Change nothing else.
3. Ship `tools/waf_rule_check.py` in the same pass as the rule, not after it.
   A rule without its checker is mitigation 2 above, already failing.
4. Read a week of firewall log. Set the ceiling from what is there.
5. Switch the rule to `rate_limit`. **Verify with the 40-concurrent probe.**
   Observed 429s or it is not done.
6. Add `@vercel/firewall`, replace `anon-rate-limit.js`'s `Map` with
   `checkRateLimit()` on the failed-validation path only, keeping its
   never-count-a-valid-key semantics and its fail-open behaviour. Test both.
7. Delete the in-memory counting. Keep the header's post-mortem.
8. Close the open-work rows for the amplification, and record the measured
   before/after — not the configuration.
