# SAIRNlaw deadline engine — approved external-facing claim

**Updated 2026-08-23, after the Phase 6 `sairn-decision-gate` re-run.**
Supersedes the Phase 5 version. This is the sentence to use with anyone
outside the team — proposals, sales conversations, status updates. Do not
paraphrase it looser.

> The deadline engine computes civil-litigation deadlines across five
> jurisdictions — federal, Ohio, Indiana, Michigan and Pennsylvania — covering
> answer, discovery, amendment, service, summary-judgment, pretrial-disclosure
> and appeal deadlines. Federal coverage is the deepest; state coverage is
> narrower and uneven, and the app shows exactly what is loaded for each.
> Every date traces to primary-source rule text with a full audit trail, and
> the engine refuses rather than estimating anything it does not cover.

## What changed at this gate, and why the claim moved

Phase 6 added the designated-period rule shape and with it the four Ohio and
Indiana discovery rules that Phase 5 had deliberately refused to seed. Ohio
went 1 → 3 rules, Indiana 1 → 3. Every jurisdiction now covers more than the
answer deadline alone.

That retires the Phase 5 sentence, which said *"Ohio and Indiana currently
cover the answer deadline only."* True then, false now.

But the correction runs **both** ways, and the gate caught the second half:
the temptation at this point is to claim parity, because every jurisdiction
now has three or more families. Federal still holds **20 of 37 rules — 54%**.
Ohio and Indiana have three each. So the new sentence says *narrower and
uneven* explicitly and points at the app rather than enumerating, which is
what keeps it from going stale the way its predecessor did.

## The one genuinely new thing worth saying out loud

The Ohio and Indiana discovery rules **do not set deadlines**. They set a
floor on a period the requesting party designates. The engine now asks for the
designated period and computes from it — and **refuses** a request designating
less than the rule's minimum, naming the floor, rather than quietly computing
the minimum instead.

That refusal is a feature, not a limitation, and it is worth demonstrating: no
other deadline tool that computes a fixed 28 days for Ohio interrogatories is
answering the right question, because the rule does not set 28 days.

It also declines a question it should decline. Whether a below-floor request
is void or merely unenforceable as to timing is a matter of law. The engine
says so in the refusal and produces no date either way.

## Why this lives in a document and not in the app

The sentence contains two kinds of fact, and only one is safe to write down.

The **invariant** half — every date traces to primary-source rule text, there
is a full audit trail, the engine refuses rather than estimating — is true
independent of what is loaded. That half IS in the app, in the coverage card's
standing notice.

The **specific** half — which jurisdiction covers what — is true as of the
date above and becomes false the moment a rule is added. It has now gone stale
**twice**, at the Phase 5 gate and again here, which is the strongest possible
argument for not hardcoding it. The app renders those specifics live from the
loaded rule set, with per-jurisdiction rule and family counts given visual
prominence so unevenness reads at a glance.

**So: this document is the point-in-time claim a human makes. The app is the
live one. When they disagree, the app is right and this file is stale.**

## What the claim is measured against (live at time of approval)

| Jurisdiction | Rules | Families | Coverage |
|---|---:|---:|---|
| United States (Federal) | 20 | 9 | answer, discovery, amendment, service, summary judgment, pretrial disclosures, notice of appeal |
| Michigan | 7 | 3 | answer + interrogatories + admissions |
| Pennsylvania | 4 | 3 | pleading + interrogatories + admissions |
| Ohio | 3 | 3 | answer + interrogatories + admissions (both designated-period) |
| Indiana | 3 | 3 | response to pleading + interrogatories + admissions (both designated-period) |

37 rules total; federal is 54%. Holiday calendars 2026–2031 for all five.

## Claims that are NOT approved

- ❌ *"answer and notice-of-appeal deadlines across federal, OH, IN, MI, PA"* —
  the Phase 4 language. Understates by two phases.
- ❌ *"Michigan and Pennsylvania include discovery; Ohio and Indiana cover the
  answer deadline only"* — the Phase 5 language. **Now false**: Ohio and
  Indiana both have discovery as of Phase 6.
- ❌ *"litigation deadlines across five jurisdictions"* — still implies a parity
  that still does not exist. Federal remains more than half of all coverage.
- ❌ *"computes Ohio's 28-day interrogatory deadline"* — Ohio has no such
  deadline. 28 days is a floor on a party-designated period. Getting this
  wrong in a sales conversation would be worse than saying nothing.

## Re-run the gate before changing this

This file has now been rewritten at two consecutive gates. The pattern is
established: any material coverage change makes it stale, and the specific
half is the part that rots. Re-run `sairn-decision-gate` and rewrite the
sentence before a new claim goes outside the team.

The gate has now caught three distinct failure modes across three runs, none
of them obvious without deliberately looking:

1. **Phase 4** — a true statement implying more *breadth* than existed.
2. **Phase 5** — a true statement implying more *parity* than existed.
3. **Phase 6** — a previously-approved statement that had simply become
   *false*, in the direction of understating, because the product improved
   underneath it. Stale claims are not only a risk when they overstate.
