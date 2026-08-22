# SAIRNlaw deadline engine — approved external-facing claim

**Approved 2026-08-22, after the Phase 5 `sairn-decision-gate` re-run.**
This is the sentence to use with anyone outside the team — proposals, sales
conversations, status updates. Do not paraphrase it looser.

> The deadline engine computes federal civil-litigation deadlines across
> answer, discovery, amendment, service, summary-judgment and
> pretrial-disclosure deadlines, with narrower state coverage — Michigan and
> Pennsylvania include discovery response deadlines; Ohio and Indiana
> currently cover the answer deadline only. Every date traces to
> primary-source rule text with a full audit trail, and the engine refuses
> rather than estimating anything it does not cover.

## Why this lives in a document and not in the app

The sentence contains two different kinds of fact, and only one of them is
safe to write down.

The **invariant** half — every date traces to primary-source rule text, there
is a full audit trail, the engine refuses rather than estimating — is true
independent of what is loaded. That half IS in the app, in the coverage card's
standing notice.

The **specific** half — which states have discovery, which have only the
answer deadline — is true as of the date above and becomes false the moment a
rule is added. Hardcoding it into the panel would recreate precisely the stale
second copy the coverage card was built to eliminate, and would do it in the
one place a user is most likely to trust. The app therefore renders those
specifics live from the loaded rule set, with per-jurisdiction rule and family
counts given visual prominence so the unevenness reads at a glance.

**So: this document is the point-in-time claim a human makes. The app is the
live one. When they disagree, the app is right and this file is stale.**

## What the claim is measured against (live at time of approval)

| Jurisdiction | Rules | Coverage |
|---|---:|---|
| United States (Federal) | 20 | answer, discovery, amendment, service, summary judgment, pretrial disclosures, notice of appeal |
| Michigan | 7 | answer + interrogatories + admissions |
| Pennsylvania | 4 | pleading + interrogatories + admissions |
| Ohio | 1 | answer only |
| Indiana | 1 | answer only |

Federal is 20 of 33 rules — 61% of all coverage. Holiday calendars 2026–2031
for all five.

## Two claims that are NOT approved

- ❌ *"answer and notice-of-appeal deadlines across federal, OH, IN, MI, PA"* —
  the language approved at the Phase 4 gate. Now understates: Phase 5 added
  discovery, amendment, service, summary judgment and backward-counted
  pretrial deadlines.
- ❌ *"litigation deadlines across five jurisdictions"* — implies a parity that
  does not exist. Ohio and Indiana carry one rule each.

## Why Ohio and Indiana are thin, if asked

Not an oversight, and worth saying plainly because it is a point in the
product's favour. Ohio Civ.R. 33(A)/36(A) and Ind. T.R. 33(C)/36(A) set the
discovery response period as *"a period designated by the party submitting…
not less than"* 28 or 30 days. The operative deadline is whatever the
propounding party designated; the rule supplies only a floor. Encoding the
floor as a deadline would put a date on screen that is not the user's
deadline whenever the request designated longer. The engine refuses instead.

"We correctly refuse" and "we cover Ohio" are different claims. This document
makes the first one and not the second.

## Re-run the gate before changing this

Any material coverage change makes this file stale. The standard set across
Phases 4 and 5: re-run `sairn-decision-gate` and rewrite this sentence before
the new claim goes outside the team. It has now caught two distinct failure
modes — a true statement implying more breadth than existed, then a true
statement implying more parity than exists — neither of which was obvious
without deliberately looking.
