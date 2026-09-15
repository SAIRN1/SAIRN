---
name: sairn-resilience-patterns
description: 'Architectural hardening patterns to reach for WHILE BUILDING, distilled from cross-industry practice and anchored to the SAIRN implementation of each one. Trigger before adding a call to anything you do not control (another service, Anthropic, Stripe, Supabase, CourtListener); before a limit, quota or budget that more than one customer shares; when writing a workaround, an accepted risk or a "temporary" anything; when a correction would move a live system in one jump; and when a check has failed twice and the instinct is to check harder. NOT an audit skill — sairn-guardian-v2 checks code that exists and sairn-hover-auditor adversarially re-checks what another session built. This one is consulted at design time, before the thing is written.'
---

# SAIRN Resilience Patterns

Seven patterns. Every one is stated with **the SAIRN file that implements it**,
because a resilience pattern described in the abstract is a blog post, and this
platform has already paid for the difference between a pattern and a pattern
*that survives this runtime*.

**Read this BEFORE writing the thing, not after.** The companion skills run the
other way round: `sairn-guardian-v2` checks code that exists, `sairn-hover-auditor`
adversarially re-checks what another session built, `sairn-software-architect`
decides whether to build at all. This one is about the shape of the thing once
that decision is made.

**Do not cite a pattern here as evidence that the platform HAS it.** Each anchor
below was verified to exist on 2026-09-15; whether it is wired into the path you
are about to write is a separate question, and the answer is usually no.

---

## 0. The rule that governs the other seven

**A pattern that cannot fire is worse than no pattern, because it reads as
coverage.** Every section below therefore states the condition under which the
pattern is inert, and the first question to ask of any of them is *"what would
have to be true for this to never fire, and is that true today?"*

This is not a generic caution. It is the specific way each of these has failed
here: a breaker whose counter is diluted at the moment it should trip, a
blast-radius control on a resource shared by one tenant, an expiry nobody
evaluates, a health window shorter than the failure it watches.

---

## 1. Circuit breaker and bulkhead — and why the textbook version does not work here

**Anchor: `api/_lib/resilience.js` (+ `api/_lib/resilience.test.js`, 34 arms,
`sql/sairn_circuit_breaker_schema.sql`).** Composed breaker → bulkhead → timeout,
so an open circuit costs no socket and a saturated bulkhead refuses before one is
taken.

**THE PART THAT IS SAIRN-SPECIFIC AND IS THE REASON TO READ THAT FILE RATHER THAN
A LIBRARY'S README.** A classic in-process breaker — Hystrix, Resilience4j, Polly
— is a per-instance failure counter with a threshold. That does not work on this
runtime, and it was MEASURED rather than reasoned about:
`api/_lib/anon-rate-limit.js` recorded on 2026-09-05 that 40 concurrent requests
against a limit of 20 produced **not one trip**, because a dozen Vercel instances
each counted the same subject from 1.

For a breaker it is worse than for a rate limiter, and the reason is the whole
lesson: **load is what makes a dependency degrade, so the per-instance counter is
diluted most at exactly the moment the breaker is supposed to trip.** A breaker
here takes a shared store or it is decoration.

**Reach for it when:** you are about to call anything you do not control.
**It is inert when:** the store is per-instance, or the failure you fear is a
slow success rather than an error (a timeout is a separate primitive for a
reason).

---

## 2. Blast-radius containment — cells, and shuffle sharding

**Anchors: `docs/2026-09-15-item93-shared-backend-tenancy-scoping.md` (the
measurement), `sql/sairn_ai_tenant_subbudget_2026-09-15.sql` (the
implementation), `docs/SPOF-REGISTER.md` (the register).**

The question is not "is this shared" — almost everything is. It is **"when one
tenant misbehaves, who else is affected, and is that set the whole platform, one
app, or one customer?"**

That audit found three sharing scopes on this platform — global, per-app,
per-instance — each chosen when its thing was built, and **two of the three were
reasoned about explicitly while the third was not**. The third keyed on `app_id`
because that was the column that happened to exist, so a real fairness question
had been answered by a column name.

**THE DESIGN LESSON, which is the one that generalises:** a hard per-tenant cap
is a REGRESSION on a platform where most apps have one tenant — it takes capacity
away from somebody contending with nobody, to protect tenants who do not exist.
The sub-budget therefore binds **only under contention**: below a floor nobody is
capped, and above it no single tenant may hold more than its share.

**And say what it does not cover.** Shuffle sharding does not apply to a single
Supabase project with a single service-role key: that is a provisioning and spend
decision, not a code change. Naming that early stops the pattern being cited as
though it had solved something it cannot reach.

**Reach for it when:** a limit, quota, budget or lock is keyed on something
coarser than the party whose behaviour you are bounding.
**It is inert when:** there is exactly one tenant — which is the normal case
here, and is why the floor exists.

---

## 3. Temporary workarounds that expire by themselves

**Anchor: `tools/accepted_risk_expiry_audit.py`.**

The pattern is not "write down that it is temporary". It is **"can the expiry
actually fire"** — an acceptance with a review date nobody evaluates is a
permanent decision wearing a temporary label, and the label is what stops anybody
looking again.

That tool is deliberately distinct from `tools/accepted_risk_scan.py`, and the
distinction is worth repeating because it is the same distinction this whole
skill rests on: the scan asks whether an acceptance reached a register **at all**;
the audit starts where that finishes and asks whether the one that did can ever
lapse. One looks at code and asks about documentation; the other looks at the
documentation and asks whether it is alive.

**Reach for it when:** you write the words temporary, for now, until, workaround,
accepted, or a TODO with a condition in it.
**It is inert when:** the expiry is a date in prose rather than a field something
reads.

---

## 4. Untrusted input is isolated, not sanitised in place

**Anchors: `api/claude.js`'s `app_id` allowlist and `ALLOWED_SERVER_TOOL_TYPES`;
`api/_lib/anon-rate-limit.js`; `api/greeting.js`'s never-echo rule.**

The pattern is **containment before cleaning**. A fixed allowlist answers "is this
one of ours" without ever interpreting the caller's string; a sanitiser answers
"is this safe" and has to be right about every input anybody will ever send.

Two real instances, both from this platform rather than from a textbook:

* `api/greeting.js` **never echoes caller input**, because its result is injected
  with `innerHTML` inside a template literal — so anything returned is parsed as
  HTML. `app_id` is matched against a fixed table and anything else falls through
  to neutral copy. **The client escapes it too** — two guards, because a future
  client could be pointed at a future endpoint that forgets.
* `sanitizeTools` in the Claude proxy shipped `Number(x) || CEILING`, which is
  falsy for `0`, `NaN`, `null` and `"abc"` — so each of those bought the MAXIMUM
  billed web searches. Coercion is not validation, and a default reached by
  falsiness is not a default anybody chose.

**Reach for it when:** a value crosses a trust boundary — a request body, a
model's output, another app's session, a licence key.
**It is inert when:** the allowlist is derived from the same input it is meant to
constrain.

---

## 5. Sliding-window health, not a point reading

**Anchors: `api/_lib/ai-rate-limit.js`, `api/_lib/courtlistener.js`,
`api/_lib/heartbeat.js` + `api/cron-watchdog.js`.**

A point reading answers "is it up right now", which is the question nobody is
asking. A window answers "how has it behaved over the interval that matters",
which is what a decision rests on.

**THE TWO THINGS THAT GO WRONG HERE, both recorded:**

* **The window must be counted atomically or it is not a window.** The rate
  limiter counted and inserted in two uncoordinated HTTP calls, so N concurrent
  requests all read the same count and all passed — 50 requests arriving at 199
  against a limit of 200 were **all** permitted. The fix is one RPC under an
  advisory lock. And the lock alone is not enough: it serialises acquisition, not
  the transaction's SNAPSHOT, so the function **refuses** under any isolation
  level other than READ COMMITTED rather than trusting nobody changes a setting.
* **A health check that rots with the wall clock is worse than none.**
  `api/cron-watchdog.test.js` built fixtures against a hardcoded instant, passed in
  the morning and reported every healthy fixture DEAD a few hours later — and a
  test that fails by time of day gets blamed on whatever was committed nearest to
  when somebody noticed.

**Reach for it when:** you are about to store a boolean for "healthy".
**It is inert when:** the window is shorter than the failure's period — an hourly
job cannot be judged by a five-minute window.

---

## 6. Gradual correction, not a disruptive jump

**Anchors: `api/_lib/cron-jitter.js`; `SAIRN_AI_RATE_LIMIT_MODE=observe`;
`docs/2026-09-15-item99-graduated-consent-for-irreversible-changes.md`.**

The pattern: when a live system is wrong, move it in a direction that can be
measured, not to where it should have been.

* **Observe before enforce.** The AI limiter ships recording every call and
  reporting when a limit WOULD have been exceeded, because a 200/day cap has
  never actually been enforced and turning it on blind risks a platform-wide
  outage on a threshold nobody has measured. **The observe-mode data is the
  precondition for the decision, not a delay before it.**
* **Jitter rather than a second fixed minute.** Two crons colliding at `:00` were
  moved to `:07` and `:37` — and a bounded random offset was added as well,
  because a fixed minute fixes those two and nothing else: the fifth cron will be
  typed by hand and can land on an occupied minute silently.
* **And the change was shaped so the next week of logs ANSWERS the question.** If
  the failures move with the schedule the collision was the cause; if they stay at
  `:00`, something else spikes at the top of the hour and this was the wrong fix,
  cheaply.

**Reach for it when:** the correct value is known and the current one is live.
**It is inert when:** the gradual step is small enough that nothing can be
distinguished from noise — a ramp nobody can read is a delay, not a measurement.

---

## 7. Reposition the check; do not just check harder

**Anchors: `api/_lib/calendar-date.js`; the licence re-key guard in every app
HTML; `api/_lib/stripe-config.js`; `api/_lib/stripe-api-version.js`.**

When the same check has to be right in many places, the fix is usually to move it
somewhere it only has to be right once — not to make each copy stricter.

* `isDate` was defined **fourteen times, all byte-identical, and all wrong the
  same way** — they validated the SHAPE of a date and not the DATE, so
  `2026-02-31` passed and `new Date` silently repaired it into 2026-03-03. **The
  interesting finding is not that the copies disagreed. It is that they agreed**,
  which is the failure mode of copying rather than importing. One fix would have
  been fourteen.
* The licence re-key guard **deliberately did NOT namespace every storage key by
  licence**, which was the obvious repair: that rewrites every read and write in
  the file and needs a migration, and getting it wrong orphans a customer's
  records. It closes the same exposure **at one hook**.
* Five SAIRNcash files independently re-derived "is Stripe configured" and three
  disagreed; one module owns it now.

**The counter-example matters as much as the rule.** `api/_lib/auth.js` and
`api/_lib/license.js` have the widest blast radius on the platform and that is
CORRECT — they are the single implementations repositioning is supposed to
produce. `docs/SPOF-REGISTER.md` marks them ACCEPTED with a reason rather than
counting them as defects, because calling a wide blast radius a defect regardless
of cause is the analysis leading the judgement.

**Reach for it when:** the same rule appears in more than about three places, or
a fix has to be applied N times to be correct.
**It is inert when:** the N copies are genuinely different rules that happen to
look alike — which is why the move is justified by READING them, not by counting
them.

---

## What this skill does not do

It does not decide whether a feature should exist (`sairn-software-architect`),
check code that is already written (`sairn-guardian-v2`, `sairn-code-scrubber`),
or re-review another session's work (`sairn-hover-auditor`,
`sairn-adversarial-reviewer`). It does not rank the patterns: which one applies is
a property of what you are building, and a priority order here would be a
judgement made without the case in front of it.

**And it carries no count of how many patterns "the platform has".** Every anchor
above is a file that exists; none of them is claimed to be wired into the path you
are working on. Check that yourself — that is the point of reading this before you
build rather than after.
