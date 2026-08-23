# SAIRNlaw deadline engine — approved external-facing claim

**Updated 2026-08-23, after the Phase 7 `sairn-decision-gate` re-run.**
Supersedes the Phase 6 version. This is the sentence to use with anyone
outside the team — proposals, sales conversations, status updates. Do not
paraphrase it looser.

> The deadline engine computes civil-litigation deadlines across five
> jurisdictions — federal, Ohio, Indiana, Michigan and Pennsylvania. All five
> now cover the three main discovery devices: interrogatories, requests for
> admission and requests for production. Federal additionally covers answer,
> amendment, service, summary-judgment, pretrial-disclosure and appeal
> deadlines, so overall depth is still greatest there. Every date traces to
> primary-source rule text with a full audit trail, and the engine refuses
> rather than estimating anything it does not cover — including where a rule
> sets no deadline at all, as Ohio's and Indiana's discovery rules do.

## What changed at this gate, and the fourth distinct failure mode

Phase 7 read the four state production rules and seeded five. Coverage went
37 → 42 rules. Two things changed qualitatively:

1. **All five jurisdictions now cover all three discovery devices.** That was
   not true at any previous gate.
2. **Federal fell below half of total coverage** for the first time — 20 of 42,
   48%.

The Phase 6 sentence said state coverage was *"narrower and uneven."* That is
still true of totals and now **misleading on discovery specifically**, where
coverage is complete and equal across all five.

**So the fourth failure mode is this: a claim can be simultaneously true on one
dimension and wrong on another, and a single adjective forces you to pick.**
"Uneven" undersells discovery; "parity" oversells depth. The fix is not a
better adjective — it is naming *which dimension* each statement is about,
which is what the new sentence does.

The running tally across four gates, none of these obvious without looking:

1. **Phase 4** — a true statement implying more *breadth* than existed.
2. **Phase 5** — a true statement implying more *parity* than existed.
3. **Phase 6** — a previously-approved statement that became *false* because
   the product improved underneath it.
4. **Phase 7** — a statement true on one dimension and misleading on another,
   where one adjective cannot carry both.

## The thing most worth demonstrating

Ohio's and Indiana's discovery rules — all six of them, across interrogatories,
admissions and production — **do not set deadlines**. They set a floor on a
period the requesting party designates. The engine asks for that period,
computes from it, and **refuses** a request designating less than the rule's
minimum rather than quietly computing the minimum.

Phase 7 confirmed this is a property of the *state's discovery regime*, not of
a particular device: Ohio and Indiana are designated-period across all three,
Michigan and Pennsylvania are fixed across all three, verified rule by rule
over twelve rules and three phases rather than inferred.

Any tool that returns a flat 28 days for an Ohio interrogatory request is
answering a question the rule does not ask.

## Why this lives in a document and not in the app

The sentence contains two kinds of fact, and only one is safe to write down.

The **invariant** half — every date traces to primary-source rule text, there
is a full audit trail, the engine refuses rather than estimating — is true
independent of what is loaded. That half IS in the app, in the coverage card's
standing notice.

The **specific** half — which jurisdiction covers what — has now gone stale at
**three consecutive gates**. That is the argument for never hardcoding it. The
app renders those specifics live from the loaded rule set, with per-jurisdiction
rule and family counts given visual prominence so unevenness reads at a glance.

**So: this document is the point-in-time claim a human makes. The app is the
live one. When they disagree, the app is right and this file is stale.**

## What the claim is measured against (live at time of approval)

| Jurisdiction | Rules | Families | Discovery devices | Notes |
|---|---:|---:|---|---|
| United States (Federal) | 20 | 9 | all three | plus answer, amendment, service, summary judgment, pretrial disclosures, appeal |
| Michigan | 9 | 4 | all three (fixed) | + answer; four rules trigger from service of process |
| Pennsylvania | 5 | 4 | all three (fixed) | + pleading |
| Ohio | 4 | 4 | all three (**designated-period**) | + answer |
| Indiana | 4 | 4 | all three (**designated-period**) | + response to pleading |

42 rules; federal 48%. Six designated-period rules. Holiday calendars
2026–2031 for all five.

## Claims that are NOT approved

- ❌ *"answer and notice-of-appeal deadlines across federal, OH, IN, MI, PA"* —
  Phase 4 language. Understates by three phases.
- ❌ *"Ohio and Indiana cover the answer deadline only"* — Phase 5 language.
  False since Phase 6.
- ❌ *"state coverage is narrower and uneven"* used **unqualified** — Phase 6
  language. Still true of totals, now misleading about discovery, where all
  five are complete and equal.
- ❌ *"litigation deadlines across five jurisdictions"* — still implies overall
  parity that still does not exist. Federal is 48% of coverage and the only
  jurisdiction with appellate, summary-judgment or pretrial-disclosure rules.
- ❌ *"computes Ohio's 28-day interrogatory deadline"* — **Ohio has no such
  deadline.** 28 is a floor on a party-designated period. This one sounds
  competent and is wrong; it would be the most damaging thing on this list to
  say in a sales conversation.

## Re-run the gate before changing this

Rewritten at three consecutive gates now. The pattern is not going away: any
material coverage change makes the specific half stale, and the failure mode
is different each time. Re-run `sairn-decision-gate` and rewrite the sentence
before a new claim goes outside the team.

## Still not covered, and disclosed on the same standard

Subpoena-to-non-party analogues and deposition-notice timing in every
jurisdiction; state appellate deadlines in all four states; statutes of
limitation anywhere. Absence means **not yet verified**, not verified absent.
Statutes of limitation in particular remain deliberately out of scope — they
are claim-type-specific and often statutory rather than rules-based, and are
the highest-consequence error class in the product.
