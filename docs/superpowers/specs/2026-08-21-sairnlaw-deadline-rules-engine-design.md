# SAIRNlaw Deadline Rules Engine — Design (Phase 1, design only)

**Date:** 2026-08-21
**Status:** Design and scope. No code written.
**Standing rule:** every date rule is verified against the actual statute or
court rule before encoding. No date is computed from model memory. A wrong
deadline in a legal product is malpractice exposure, not a bug.

---

## 0. A blocker found before designing anything

`law_deadlines` **is not a registered resource.** The client has been writing
to it since before this session:

```
sairnlaw.html:2188   await sdnData('write','law_deadlines',rec)
sairnlaw.html:2195   await sdnData('write','law_deadlines',d)
```

Verified live against production:

| resource | HTTP |
|---|---|
| `law_deadlines` | **400** (unrecognised resource) |
| `law_matters` | 200 (control) |

To its credit this fails *honestly* rather than silently — the toast reads
*"Saved on this device only — server sync not yet enabled for this app"*. But
the consequence is that **every deadline in SAIRNlaw today exists on exactly
one browser**, is never hydrated back, and is lost with the profile.

This is a prerequisite, not a side quest. An engine that computes a correct
statutory deadline and then stores it somewhere it can vanish is worse than no
engine, because the user now believes the date is recorded. **Registering
`law_deadlines` is step one of implementation.**

---

## 1. Rule representation

### 1.1 The core decision: rules are data, not handlers

Deadline rules live in a new `law_deadline_rules` resource as one row per
rule, never as branches in a computation function. Three reasons, all
practical rather than aesthetic:

1. **The law changes.** A handler must be redeployed; a row can be superseded.
2. **A rule must be auditable.** A partner needs to see *which* authority
   produced a date, and follow it to the source.
3. **Deadlines must be computable as the law stood at the trigger date**, not
   as it stands today. That is impossible if the rule is code.

### 1.2 Row shape

```
{
  rule_id:        'frcp-12a1Ai-answer-summons',
  jurisdiction:   'us-federal',
  domain:         'civil-litigation',
  label:          'Answer to a complaint after service of summons',

  trigger_event:  'service_of_summons_and_complaint',

  count:          { value: 21, unit: 'calendar_days', direction: 'forward' },
  computation:    'frcp_6a',            // named, versioned algorithm

  service_extension: {
    standard:     'frcp_6d',
    add:          3,
    unit:         'calendar_days',
    applies_when: ['mail', 'left_with_clerk', 'other_consented_means'],
    order:        'after_base_period'    // see §2.4 — order is load-bearing
  },

  authority: {
    citation:     'Fed. R. Civ. P. 12(a)(1)(A)(i)',
    url:          'https://www.law.cornell.edu/rules/frcp/rule_12',
    retrieved_at: '2026-08-21',
    verified_by:  'employee_id'
  },

  effective_from: '2009-12-01',
  effective_to:   null,                  // null = currently in force
  version:        1,
  supersedes:     null
}
```

### 1.3 Non-negotiable field rules

- **`authority` is required, with a real resolvable URL.** Same discipline as
  `sc_scrubrules` and `sc_credential_scope` in SAIRNcode: a rule with no
  traceable source cannot be saved. This table is never seeded with rules
  nobody verified.
- **`effective_from` / `effective_to` are required**, and supersession is
  additive — an amended rule is a *new row* pointing at the old one via
  `supersedes`. Rules are never edited in place and never deleted, because a
  matter triggered in 2023 must still compute against the 2023 rule.
- **`computation` names a versioned algorithm**, it does not contain one.
  `frcp_6a` is implemented once and reused by every rule that cites it.

### 1.4 The holiday calendar is a separate versioned resource

`law_holidays`, keyed by jurisdiction **and year**. Not embedded in rules,
because the same rule spans many years and holidays move.

```
{ jurisdiction: 'us-federal', year: 2026, kind: 'federal',
  dates: [{ date: '2026-01-01', name: "New Year's Day", authority: '5 U.S.C. §6103' }, ...],
  authority: { citation, url, retrieved_at, verified_by } }
```

Two subtleties this separation exists to handle:

- **Presidentially declared holidays.** FRCP 6(a)(6) counts "any day declared
  a holiday by the President or Congress." Those appear with little notice and
  cannot live in code.
- **State holidays are direction-dependent.** Under FRCP 6(a)(6), a holiday
  declared by the state where the district court sits counts **only for
  forward-counted periods**. So `kind` matters and the algorithm must consult
  it against `direction`. This is exactly the sort of asymmetry a hardcoded
  holiday array gets silently wrong.

---

## 2. Computation — the parts that are actually hard

### 2.1 Trigger events

The engine **never computes from "today"** and never infers a trigger. A
computation requires an explicitly recorded trigger event whose `type` matches
the rule's `trigger_event` exactly. Unmatched or absent trigger → refusal, not
a guess.

Trigger types are themselves a controlled vocabulary per domain
(`service_of_summons_and_complaint`, `entry_of_judgment`, `last_furnishing_of_labor_or_materials`, …),
because "when the clock started" is the single most litigated input and a free-text
trigger cannot be validated against a rule.

### 2.2 Calendar days vs business days

`unit` is explicit and there is no default. This matters more than it looks:

**FRCP periods are calendar days with special treatment of the last day only.**
Rule 6(a)(1) directs you to *"count every day, including intermediate
Saturdays, Sundays, and legal holidays."* Implementing FRCP as "business days"
is the classic error and produces dates that are wrong in the safe-looking
direction — later than reality.

**Verified and worth recording because it inverts older practice guidance:**
the pre-2009 rule under which periods shorter than 11 days *excluded*
intermediate weekends is **obsolete**. The 2009 amendment unified computation
so all day-periods count the same way regardless of length. Any implementation
copied from an older form book will be wrong here.

`unit` supports `calendar_days`, `business_days`, `months`, `years` — months
and years being genuinely different (anniversary-date arithmetic with
end-of-month clamping), not 30/365-day approximations.

### 2.3 Weekend / holiday rollover

Per FRCP 6(a)(1)(C): exclude the trigger day, include the last day, and if the
last day is a Saturday, Sunday or legal holiday, the period runs to the end of
the next day that is none of those. Rollover applies to the **last day only**,
never to intermediate days.

Backward-counted periods (FRCP 6(a)(5)) roll in the opposite direction — to
the *preceding* business day. `direction` drives this, and the two must be
tested separately.

### 2.4 Service-method extensions, and why order is load-bearing

FRCP 6(d) adds 3 days when service was by mail, by leaving with the clerk, or
by other consented means — and adds them **"after the period would otherwise
expire under Rule 6(a)."**

So the sequence is:

```
1. base period from trigger, per 6(a)          → provisional date
2. last-day rollover per 6(a)(1)(C)            → date A
3. if service method qualifies, +3 days        → date B
4. rollover applied again if B lands on a
   weekend/holiday                             → final
```

**Step 4 is flagged as needing its own verification before encoding.** That
the +3 is applied after the base period is explicit in the rule text; whether
a further rollover then applies to the extended date is the kind of detail
this design refuses to assume. It will be verified against the rule text and
the Advisory Committee notes before any code computes it, and until then the
engine will not offer service-extension computation at all.

That is the whole reason `order` is a stored field rather than an implicit
convention: a jurisdiction that adds service time *before* applying rollover
produces a different date, and the difference is a missed filing.

---

## 3. What happens when a jurisdiction is not loaded

**Fail closed. Always. No exceptions and no approximations.**

The engine returns a refusal, never a date, in every one of these cases:

| Condition | Response |
|---|---|
| Jurisdiction has no rules loaded | `NOT_PROVISIONED` — names the jurisdiction |
| Domain not loaded for that jurisdiction | `NOT_PROVISIONED` — names the domain |
| No rule matches the trigger event | `NO_MATCHING_RULE` — lists the triggers that *are* covered |
| Trigger date falls outside every rule version's effective window | `NO_RULE_IN_FORCE` — states the windows that exist |
| **Holiday calendar missing for a year the computation crosses** | `NOT_PROVISIONED` — names jurisdiction *and* year |
| Service method given but extension rule unverified | `EXTENSION_UNVERIFIED` — returns the base date, clearly labelled as excluding any service extension |

The holiday-year case deserves emphasis: **a rule can be loaded while the
holiday calendar for the relevant year is not.** A 21-day period triggered
21 December crosses into the following year. Computing it against a missing
calendar would silently skip New Year's Day. The engine must refuse on the
*year it actually needs*, not merely on the year of the trigger.

This mirrors the posture just applied across SAIRNlaw's reference endpoints
and SAIRNcode's credential gate: **the failure names the missing thing.** An
opaque error teaches users to retry; a named one teaches them to load the
jurisdiction. And nothing here ever emits a date it cannot source.

---

## 4. Seed jurisdiction: **U.S. Federal — civil litigation under the FRCP**

One jurisdiction, one domain, on the first pass. Seeded with the Rule 12
response deadlines computed through the Rule 6(a) standard.

### Why this one

1. **The primary sources are free, authoritative and stable.** The full FRCP
   text is hosted by Cornell LII; federal holidays are fixed by statute at
   5 U.S.C. §6103; the federal courts publish their own calendars. Every rule
   can be verified and re-verified without a paywall — which is what makes the
   `authority` URL requirement enforceable rather than decorative.
2. **Rule 6(a) is algorithmic by design.** It is written as a procedure —
   exclude, count, include, roll. It is the closest thing in American practice
   to a specification, which makes it the right thing to implement first and
   the right thing to test against.
3. **It exercises every hard part named in the scope**: a defined trigger
   event (service), calendar-day counting, weekend/holiday rollover with a
   direction-dependent holiday definition, and a service-method extension.
   Nothing is deferred to a later jurisdiction to make the first pass look easy.
4. **One jurisdiction, nationwide reach.** Every federal district court uses
   it. The coverage-per-rule-encoded ratio is the best available.
5. **It is the reusable core.** FRAP 26(a) mirrors FRCP 6(a) almost exactly,
   so the appellate domain later reuses the same computation standard rather
   than a second implementation. Bankruptcy Rule 9006 likewise.

### Why explicitly not the others first

- **Construction liens** — per-state, and the trigger (*last furnishing of
  labor or materials*) is itself frequently litigated. Encoding a contested
  trigger as though it were determinate would be the worst possible first move.
- **Breach notification** — a 50-state patchwork that is actively changing.
  High churn is exactly what a v1 should avoid.
- **Immigration / SSA / VA** — federal, but the deadlines sit in regulations
  with dense exception structures and more frequent amendment than the FRCP.
- **Tax controversy** — deadlines are often jurisdictional and unextendable,
  which raises the cost of a v1 error to its maximum. It should be built on a
  proven engine, not used to prove one.

---

## 5. Files this touches

**New**

| File | Purpose |
|---|---|
| `sql/sairnlaw_deadline_rules_schema.sql` | `law_deadline_rules`, `law_holidays`, and `law_deadlines` (the missing one) |
| `api/_lib/deadline-engine.js` | Pure computation. Versioned standards (`frcp_6a`), no I/O, fully Node-testable |
| `api/legal-deadlines.js` | Endpoint: `compute`, `rules_status`, `add_rule`, `add_holidays` |
| `docs/superpowers/specs/2026-08-21-sairnlaw-deadline-rules-engine-design.md` | This document |

**Modified**

| File | Change |
|---|---|
| `api/_resources/sairnlaw.js` | Register `law_deadline_rules`, `law_holidays`, **and `law_deadlines`** (§0) |
| `sairnlaw.html` | Deadline-rules panel; compute-from-trigger in the existing deadline modal; show the authority behind every computed date |

**Deliberately untouched**

`api/sd-data.js` — the per-app registry split means new resources are added in
`api/_resources/sairnlaw.js` alone. No shared-file edit, no collision surface.

---

## 6. Testing posture before any of this ships

- `deadline-engine.js` is pure and gets isolated-logic tests against **worked
  examples taken from the rule text and Advisory Committee notes**, not
  invented ones.
- Boundary cases are mandatory: trigger on a Friday; last day on a Saturday;
  last day on a federal holiday; a period crossing a year boundary; a
  backward-counted period; a period whose service extension lands on a weekend.
- A green test is not accepted without confirming it can still fail — the
  planted-failure check applied to the Phase D guardrail.
- Nothing is encoded from memory. Every rule row carries the URL it was read
  from and the date it was read.
