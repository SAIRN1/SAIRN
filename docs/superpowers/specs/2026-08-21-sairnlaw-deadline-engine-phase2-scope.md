# SAIRNlaw Deadline Engine — Phase 2 Scope (design only)

**Date:** 2026-08-21
**Status:** Scope proposal. No code written.
**Phase 1:** `f17bf99`, corrected by `92c4783`. Federal civil, FRCP Rule 12(a).

---

## Headline recommendation

**Phase 2 should be engine capability, not jurisdiction breadth.**

Verification of the candidate rule families turned up three *structural* gaps
that no amount of additional rule rows can paper over. Adding a second
jurisdiction on top of a one-trigger engine would mean encoding rules that the
representation cannot express — and the failure mode is a rule that looks
loaded and computes a wrong date, which is the worst possible outcome here.

Concretely: **FRAP civil appeals + three engine capabilities.** Not a state
seed yet.

---

## What verification confirmed as safe to reuse

**FRAP 26(a) is identical to FRCP 6(a).** Read directly, not assumed:

> "exclude the day of the event that triggers the period" … "count every day,
> including intermediate Saturdays, Sundays, and legal holidays" … "if the last
> day is a Saturday, Sunday, or legal holiday, the period continues to run
> until the end of the next day that is not"

FRAP 26(a)(6) also carries the **same forward-only condition on state
holidays** as FRCP 6(a)(6) — "for periods that are measured after an event."

So the Phase 1 decision to map `frap_26a → frcp_6a` rather than write a second
implementation is **verified correct**, not merely plausible. That mapping
already ships.

---

## The three gaps, each with the rule that exposes it

### Gap 1 — "Later of" multi-trigger

**FRAP 4(b)(1)(A)**, criminal notice of appeal:

> "a defendant's notice of appeal must be filed in the district court within 14
> days after **the later of**: (i) the entry of either the judgment or the
> order being appealed; or (ii) the filing of the government's notice of
> appeal."

This is the **same shape as FRCP 12(a)(3)**, which Phase 1 deliberately did not
encode for exactly this reason. The engine models one trigger per rule, so a
"later of" rule would compute from whichever trigger happened to be supplied
and be **too early roughly half the time** — the dangerous direction.

One capability unlocks both rules. That is the strongest argument for doing
capability before coverage.

*Representation sketch:* `trigger_event` becomes optionally an array with a
`resolve: 'later_of' | 'earlier_of'`, and the engine refuses unless **every**
named trigger has a supplied date — partial input must not silently degrade to
single-trigger behaviour.

### Gap 2 — Trigger substitution (tolling / reset)

**FRAP 4(a)(4)(A)**: certain post-judgment motions do not extend the appeal
period — they **replace its trigger**:

> "the time to file an appeal runs for all parties from the entry of the order
> disposing of the last such remaining motion."

This is not "later of" and not an extension. The original trigger is
*discarded* and the clock restarts from a different event. The engine has no
concept of this at all.

It is also the gap most likely to be gotten wrong by assumption, because a
reasonable implementer would reach for the service-extension mechanism (add
days) when the rule actually says re-trigger. The resulting date would be
wrong in **either** direction depending on when the motion was resolved.

*Representation sketch:* a `retrigger` clause naming the qualifying events and
the substitute trigger, plus an explicit engine refusal when a qualifying
motion is recorded as pending but its disposition date is absent — the period
genuinely has not started, and any date would be invented.

### Gap 3 — Service extension is per-standard, not global (a latent defect **in shipped code**)

**FRAP 26(c) is not FRCP 6(d).**

| | Condition | Shape |
|---|---|---|
| FRCP 6(d) | mail, left with clerk, other consented means | **enumerated allowlist** |
| FRAP 26(c) | "not served electronically or delivered on the date stated in the proof of service" | **negative condition, excludes e-service** |

Phase 1's engine carries a single global `SERVICE_METHODS_EXTENDING` allowlist
containing only the FRCP three, and requires a method to pass **both** it and
the per-rule `applies_when`. **Demonstrated against the shipped engine:** a
FRAP rule whose `applies_when` includes `non_electronic_delivery` gets
`service_extension_applied: false` and no extension.

It fails **safe** (an earlier date), but it fails **silently** — the result
reports `service_extension_applied: false` with no indication that a rule
asked for an extension and the engine refused it. Silent-and-safe is still
wrong, and it is exactly the class of thing that would be discovered later by
someone wondering why FRAP dates were three days early.

*Fix shape:* move the allowlist behind `service_extension.standard`
(`frcp_6d` vs `frap_26c`), and make a refused-but-requested extension a
disclosed condition rather than a silent no-op.

---

## Proposed Phase 2 content

**Engine (do first):**
1. Multi-trigger `later_of` / `earlier_of`, refusing on incomplete input.
2. Trigger substitution for tolling motions, refusing when a qualifying motion
   is pending without a disposition date.
3. Per-standard service extension, with a disclosed refusal when a rule
   requests an extension the engine cannot evaluate.

**Rules (after the engine supports them):**
- **FRAP 4(a)(1)(A)** — 30 days after entry of the judgment or order appealed
  from. *Verified quote captured.*
- **FRAP 4(a)(1)(B)** — 60 days when the United States is a party. *Verified.*
- **FRAP 4(a)(4)(A)** — the tolling-motion retrigger. Requires Gap 2.
- **FRAP 4(b)(1)(A)** — 14 days, criminal, "later of". Requires Gap 1.
- **FRCP 12(a)(3)** — backfilled from Phase 1's deliberate omission once
  Gap 1 lands. Closing a known, documented hole is higher value than opening a
  new jurisdiction.

**Explicitly deferred: a first state jurisdiction.** Same reasoning that kept
construction liens out of Phase 1. States multiply *coverage* against an engine
that cannot yet express structures already present in the federal rules, and
state primary sources are less uniform to verify against. A state seed is the
right Phase 3 once the engine can represent what it encounters.

---

## Open questions for Michael

1. **Appellate as a new `domain`, or a new jurisdiction key?** Recommend
   `domain: 'appellate'` under `us-federal` — the holiday calendar is shared
   and FRAP 26(a)(6) names the *circuit* clerk's office alongside the district
   court, so it is the same jurisdiction with a different rule family.
2. **Should Gap 3 be fixed immediately as a bugfix, ahead of the rest of
   Phase 2?** It is shipped, latent, and currently unreachable (no FRAP rules
   exist to trigger it). My recommendation is to fix it *with* Phase 2 rather
   than as a hotfix, since nothing can hit it today — but it is disclosed now
   rather than discovered later.
3. **Circuit-specific local rules** are out of scope for this proposal and
   should stay out until the national rules are complete. Flagging so their
   absence is a decision rather than an oversight.

---

## Standing discipline, unchanged

Every day count and every quoted condition above was read from the primary
source on 2026-08-21 and is quoted verbatim in this document. Nothing was
computed or recalled from memory. Any rule that reaches the tool will carry
its authority URL, its effective window, and a server-stamped `verified_by`,
and the engine will refuse rather than estimate whenever a rule, a trigger, or
a holiday year it needs is absent.
