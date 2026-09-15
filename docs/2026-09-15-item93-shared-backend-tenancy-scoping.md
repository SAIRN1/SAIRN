# Item 93, widened: which tenants share a backend, and how many are on each

**Scoping only. Nothing built, nothing changed.** 2026-09-15, Hank.
Claim: `item93 — shared resource tenancy audit which tenants share a backend`.

---

## Why this exists, and what it widens

`docs/SAIRN-OPEN-WORK-INDEX.md` records CC's 2026-09-14 cron fix: two hourly
jobs both scheduled `0 * * * *`, both failing about a third of their runs, and
`/api/claude`'s rate-limit RPC failing at the same minute. Its own conclusion is
the sentence this document starts from:

> **THE MECHANISM IS A SHARED BACKEND, NOT A CALL PATH, and the obvious reading
> is wrong:** NEITHER cron calls `/api/claude`. … What all three share is the
> Supabase project.

That fix spread two schedules. It did not ask the general question, which is the
one AWS's shuffle-sharding work is about: **when one tenant misbehaves, who else
is affected — and is that set the whole platform, one app, or one customer?**

CC's dependency graph already answered a neighbouring question in **modules**
(`env:SUPABASE_URL` reaches 70 of 144 production modules). This asks it in
**tenants**, which is a different unit and a different answer.

---

## Method, and what it does and does not establish

Everything below is counted from the repo at `ce7764fa`:

- tenants: `insert into public.license_keys` statements across `sql/` — 16 files.
- reach: `process.env.X` in production `api/**.js`, comments and block comments
  stripped first.
- scope keys: read out of the limiter source and its SQL function, not inferred.

**What this does NOT establish.** No production traffic was measured — the
2026-09-13 triage found **one** successful non-cron request in 24 hours, so
there is no observed contention to rank rows by, and this is a structural
audit rather than an incident analysis. Seeded licences are also a **floor**,
not the live tenant count: a licence sold and inserted by hand is invisible
here. Every number below is "at least".

---

## The inventory

| Shared resource | Keyed by | Tenants sharing one instance | Enforcing today? |
|---|---|---|---|
| **Supabase project** (`SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`) | nothing — one project | **every tenant of every app: 19 licence rows, 14 apps with seeds, 22 apps registered** | yes, and already implicated at `:00` |
| **CourtListener budget** | a single global constant | **every SAIRNlaw firm** | **yes** |
| **AI daily limit** (200/day) | `app_id` | all tenants of one app — **max 3 today** | **no — observe mode** |
| **AI advisory lock** (`pg_advisory_xact_lock`) | `app_id` | same set | **yes**, in observe mode too |
| **Anonymous licence-validation cap** | in-memory, per Vercel instance | whoever lands on that instance | yes |
| **Resend sender** (`RESEND_API_KEY`) | one key | 3 production modules, all apps that mail | yes |
| **Anthropic key** (`ANTHROPIC_API_KEY`) | one key | 3 modules; 20 distinct `app_id`s allowlisted on `/api/claude` | yes |

Credential reach, production modules only:

```
SUPABASE_SERVICE_ROLE_KEY   58        STRIPE_SECRET_KEY          5
SUPABASE_URL                58        CRON_SECRET                4
SD_AUTH_SECRET              19        RESEND_API_KEY             3
                                      ANTHROPIC_API_KEY          3
                                      COURTLISTENER_API_TOKEN    3
```

Tenants per `app_id`, from the licence seeds:

```
stonedesk 3 · sairnbiz 2 · sairnlaw 2 · sairnvet 2
sairncare, sairndental, sairndesign, sairnfreedom, sairngrounds,
sairnlegacy, sairnmechanical, sairnroofing, sairnscape, sairnsenior · 1 each
```

---

## The finding

**Three different sharing scopes exist on this platform — global, per-app, and
per-instance — and each was chosen independently, at the time the thing was
built, for reasons local to that thing.**

Two of the three were reasoned about explicitly, and correctly:

- **CourtListener is global ON PURPOSE**, and `sql/cl_rate_limit_consume_fn_2026-09-04.sql`
  says why in terms: *"THE LOCK KEY IS A SINGLE CONSTANT, not a per-tenant one.
  That is deliberate and is the difference from the AI limiter, which keys on
  app_id: there is one CourtListener token, so there is one budget, so there is
  one lock. A per-firm key would let two firms pass the same window
  simultaneously."* That is right. It is also the **sharpest shared-fate on the
  platform**: one firm can consume the entire platform's CourtListener budget
  and every other firm's legal research stops. The design note explains why it
  must be one budget. It does not say what should happen to the second firm.
- **The anonymous cap is per-instance ON PURPOSE**, and `api/_lib/anon-rate-limit.js`
  discloses the limitation rather than hiding it.

**The third was not.** `api/_lib/ai-rate-limit.js` keys on `app_id`, and every
line of justification in that file is about **atomicity** — the count-then-insert
race, the advisory lock, the exact-count header. All of it is good and none of
it is about tenancy. Nowhere does anything ask whether two customers of the same
app should share a quota. The `app_id` key reads as inherited from the table
shape rather than chosen.

### Why that matters more than the numbers suggest

The exposure is **small today and structurally unchanged at any size**. Three
StoneDesk tenants share one 200/day bucket. At thirty they still share one
bucket, and nothing in the code will mention it when the third becomes the
thirtieth.

Two specific consequences worth stating:

1. **It is one environment variable from being live.** The file ships
   `SAIRN_AI_RATE_LIMIT_MODE=observe` and warns *"DO NOT switch to enforce while
   the fallback is live."* That warning is about the RACE. Flipping to `enforce`
   is **also a tenancy decision** — the moment it is on, one customer exhausting
   the app's 200 locks out every other customer of that app for the rest of the
   day — and nothing at the switch says so.
2. **The lock is already shared, even in observe mode.** `pg_advisory_xact_lock(hashtext('sairn_ai_rl:' || p_app_id))`
   serialises every AI call across all tenants of an app **today**. That is a
   contention point, not a quota one, and it is live now.

---

## What shuffle sharding would and would not buy here

Shuffle sharding assigns each tenant a random subset of backend instances so
that no two tenants share the same full set — the blast radius of one bad tenant
becomes a small, mostly-disjoint slice rather than everybody.

**It does not apply to the Supabase project**, and saying so early is the point:
there is exactly one project and one service-role key. Sharding that is a
provisioning and cost decision (multiple projects, or connection pooling with
per-tenant pools), not a code change, and it is Michael's call, not an
engineering task to be picked up.

**It does apply, cheaply, to the two limiters**, and in the same shape for both:
a per-tenant sub-budget carved out of the global one, so a single tenant cannot
consume more than its slice while the global ceiling still holds. For the AI
limiter that is a second key column; for CourtListener it is a per-firm
allowance checked inside the existing global lock, which preserves exactly the
property the design note protects.

---

## Recommendation

**Do not build anything yet.** Three things, in order, and the first two are
cheap:

1. **Write the tenancy scope down where the switch is**, in
   `api/_lib/ai-rate-limit.js`, next to the `enforce` instruction: that flipping
   it makes one tenant able to exhaust an app's whole daily quota. Documentation,
   not code. This is the highest value per minute in the whole audit.
2. **Decide the question that was never asked** — should tenants of one app
   share an AI quota? The answer may legitimately be yes (one Anthropic bill,
   one budget, the CourtListener argument). What is not acceptable is that it
   has never been asked, because the answer is currently a side effect of a
   column name.
3. **Only then**, if the answer is no, add the tenant key. It is a small change
   in both limiters and it is not worth doing before (2).

**Explicitly out of scope and Michael's decision:** anything that multiplies
Supabase projects, and anything that changes what is bought.

---

## Loose end found while measuring, not a finding

`/api/claude`'s allowlist has **21 entries and 20 distinct values** —
`sairnsenior` appears twice, once in the 2026-08-20 retrofit and once again
below it. Harmless (membership is a containment test) and recorded so the next
person to count that list does not treat 21 as the app count.
