# SAIRNlaw deadline engine — approved external-facing claim

**Updated 2026-08-23, after the Phase 8 `sairn-decision-gate` re-run.**
Supersedes the Phase 7 version. This is the sentence to use with anyone
outside the team — proposals, sales conversations, status updates. Do not
paraphrase it looser.

> The deadline engine computes civil-litigation deadlines across five
> jurisdictions — federal, Ohio, Indiana, Michigan and Pennsylvania. All five
> cover the three main discovery devices: interrogatories, requests for
> admission and requests for production. Federal has the widest range of rule
> families; Michigan now has the most rules of any single jurisdiction's state
> rules, including subpoena and deposition timing. Every date traces to
> primary-source rule text with a full audit trail, and the engine refuses
> rather than estimating anything it does not cover — including where a rule
> sets no deadline at all, as Ohio's and Indiana's discovery rules do, and
> where a rule sets only a standard rather than a period, as every
> jurisdiction's general deposition-notice rule does.

## What changed at this gate, and the fifth distinct failure mode

Phase 8 read the subpoena and deposition rules in all five jurisdictions and
seeded seven. Coverage went 42 → 49 rules. Federal fell to **41%**, and
Michigan rose to 14 rules — the largest state set, ahead of Pennsylvania's 6
and Indiana's 5.

But the finding that moves the claim is not a count. **Phase 8 found the first
rules that no future capability can ever compute.**

Every general deposition-notice rule in all five jurisdictions requires only
*"reasonable written notice."* Indiana's subpoena rule requires a motion
*"promptly."* Michigan's general subpoena rule allows objection *"before the
designated time for appearance."* These set a **standard, not a quantity**.
There is no number to compute and no capability that could produce one.

**So the fifth failure mode is: a claim that describes a gap as temporary when
it is permanent.** Every previous "not yet covered" in this document meant *not
yet verified* or *awaiting a capability*. These do not. Saying "we don't cover
deposition notice yet" implies a roadmap item; the honest statement is that
the rule sets no computable deadline, and refusing is the **final and correct**
answer, not an interim one.

The claim now says this explicitly rather than letting it sit in the general
"refuses what it does not cover" clause, where a reader would reasonably assume
it was a coverage gap like any other.

The running tally across five gates, none of these obvious without looking:

1. **Phase 4** — a true statement implying more *breadth* than existed.
2. **Phase 5** — a true statement implying more *parity* than existed.
3. **Phase 6** — a previously-approved statement that became *false* because
   the product improved underneath it.
4. **Phase 7** — a statement true on one dimension and misleading on another,
   where one adjective could not carry both.
5. **Phase 8** — a statement describing a *permanent* limit in language that
   implies a *temporary* one.

## Two things most worth demonstrating

**Ohio's and Indiana's discovery rules set no deadline.** All six of them,
across interrogatories, admissions and production, set a floor on a period the
requesting party designates. The engine asks for that period, computes from it,
and **refuses** a request designating less than the rule's minimum rather than
quietly computing the minimum. Phase 7 confirmed this is a property of the
state's discovery regime rather than of a device — verified over twelve rules
and three phases, not inferred.

Any tool returning a flat 28 days for an Ohio interrogatory request is
answering a question the rule does not ask.

**"At least X before" and "not less than X after" are not symmetrical.** A
lead-time minimum ("serve notice at least 20 days before service") fixes the
last day the acting party may act — a real deadline they can miss, and the
engine computes it. A designated-period floor ("a period designated in the
request, not less than 28 days") constrains what someone *else* may demand and
says nothing about your deadline until they choose — the engine refuses until
told. Both are minimums; only one produces a date. Phase 8 turned on this
distinction.

## Why this lives in a document and not in the app

The sentence contains two kinds of fact, and only one is safe to write down.

The **invariant** half — every date traces to primary-source rule text, there
is a full audit trail, the engine refuses rather than estimating — is true
independent of what is loaded. That half IS in the app, in the coverage card's
standing notice.

The **specific** half — which jurisdiction covers what — has now gone stale at
**four consecutive gates**. That is the argument for never hardcoding it. The
app renders those specifics live from the loaded rule set, with per-jurisdiction
rule and family counts given visual prominence so unevenness reads at a glance.

**So: this document is the point-in-time claim a human makes. The app is the
live one. When they disagree, the app is right and this file is stale.**

## What the claim is measured against (live at time of approval)

| Jurisdiction | Rules | Families | Notes |
|---|---:|---:|---|
| United States (Federal) | 20 | 9 | widest family range: answer, discovery, amendment, service, summary judgment, pretrial disclosures, appeal |
| Michigan | 14 | 7 | largest state set: answer, all three discovery devices, subpoena and deposition timing |
| Pennsylvania | 6 | 5 | pleading, all three discovery devices, non-party subpoena prior notice |
| Indiana | 5 | 5 | response to pleading, all three discovery devices (designated-period), organizational-deposition conferral |
| Ohio | 4 | 4 | answer, all three discovery devices (designated-period) |

49 rules; federal 41%. Eight backward-counted. Six designated-period. Holiday
calendars 2026–2031 for all five.

## Claims that are NOT approved

- ❌ *"answer and notice-of-appeal deadlines across federal, OH, IN, MI, PA"* —
  Phase 4 language. Understates by four phases.
- ❌ *"Ohio and Indiana cover the answer deadline only"* — Phase 5 language.
  False since Phase 6.
- ❌ *"state coverage is narrower and uneven"* used **unqualified** — Phase 6
  language. Misleading about discovery, where all five are complete and equal.
- ❌ *"we don't cover deposition notice yet"* — **Phase 8 language to avoid.**
  Implies a roadmap item. The rule sets no computable deadline; refusing is
  final, not interim.
- ❌ *"litigation deadlines across five jurisdictions"* — still implies overall
  parity. Federal remains the only jurisdiction with appellate,
  summary-judgment or pretrial-disclosure rules.
- ❌ *"computes Ohio's 28-day interrogatory deadline"* — **Ohio has no such
  deadline.** 28 is a floor on a party-designated period. This one sounds
  competent and is wrong; it would be the most damaging thing on this list to
  say in a sales conversation.

## Re-run the gate before changing this

Rewritten at four consecutive gates. The pattern is not going away: any
material coverage change makes the specific half stale, and the failure mode
is different every time. Re-run `sairn-decision-gate` and rewrite the sentence
before a new claim goes outside the team.

## Not covered, and the two kinds of "not covered"

**Permanently uncomputable — refusing is the final answer:**
general deposition notice in all five jurisdictions (*"reasonable notice"*);
Ind. T.R. 45 motions to quash (*"promptly"*); Mich. Ct. R. 2.506 objections
(*"before the designated time for appearance"*).

**Not built, awaiting a decision — a real capability would fix these:**
federal FRCP 45(d)(2)(B) and Ohio Civ.R. 45(C)(3) subpoena objections, which
need a *cap* shape (earlier of a computed period and a date the issuing party
chose). Named, scoped, not improvised.

**Not yet verified — absence means unread, not absent:**
state appellate deadlines in all four states.

**Deliberately out of scope:** statutes of limitation anywhere. Claim-type-
specific, often statutory rather than rules-based, and the highest-consequence
error class in the product.
