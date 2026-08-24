# SAIRNlaw deadline engine — approved external-facing claim

**Updated 2026-08-24, after the Batch 2 `sairn-decision-gate` re-run.**
Supersedes the Phase 8c version, which described **five jurisdictions and 64
rules** and had gone **four phases stale**. This is the sentence to use with
anyone outside the team — proposals, sales conversations, status updates. Do
not paraphrase it looser.

> The deadline engine computes civil-litigation and appellate deadlines across
> eleven jurisdictions — federal, Ohio, Indiana, Michigan, Pennsylvania,
> Illinois, Florida, California, Texas, New York and Georgia — from 119 rules,
> every one of them encoded from primary-source rule text read verbatim, with a
> full audit trail from the date back to the authority that produced it. No
> language model is anywhere in the computation. Every jurisdiction carries both
> domains and a holiday calendar for 2026 through 2031, and every calendar is
> built from the statute that defines a legal holiday rather than from a court's
> published closure schedule, because those two lists genuinely differ. The
> engine refuses rather than estimating anything it does not cover — a missing
> rule, a missing holiday year, an ambiguous rule set, or a rule that sets no
> deadline at all. **It computes from the trigger date it is given and does not
> verify that the date means what the rule requires; where a rule runs from a
> legally computed or defined event, the user must supply that event's date, and
> the engine will not detect a wrong one.** Appeal periods in particular are not
> portable across state lines: Michigan allows twenty-one days, Pennsylvania ten
> in three named subject matters, Texas twenty for an accelerated appeal, and the
> clock starts from a different event in five different states.

---

## What this gate found, and the sixth distinct failure mode

**Failure mode six: a claim that is true about the rules and silent about the
inputs.**

The premortem question was *"someone outside the team relied on this engine, got
a wrong date, and pointed at our claim. What did they find?"* The honest answer
was not a coverage gap. It was this:

Every previous version of this claim described how carefully the **rules** were
encoded, and every word of that was true. None of them said anything about the
**trigger date the user supplies**, and the engine does not check it. Five
jurisdictions now start an appeal clock five different ways:

| Jurisdiction | The appeal clock starts on |
|---|---|
| Georgia | **entry** of the appealable decision or judgment |
| Texas | the **signing** of the judgment |
| Florida | **rendition** — a defined term of art, not the signature or mailing date |
| New York | **service** of the judgment **with written notice of its entry** |
| California | service of a notice of entry (two limbs), or 180 days from entry |

Hand the engine an entry date where New York wants service-of-notice-of-entry
and it returns a confident, fully-audited, **wrong** date. Same for New York's
CPLR 320(a) and 3012(c), which run from when *"service is complete"* — a date
CPLR 308 computes and this engine deliberately does not.

That is a real limit, it is the highest-consequence one in the product, and it
had never been in the claim. It is now in the claim, in the sentence itself
rather than in a footnote, because a reader who stops after the first two lines
must still have seen it.

**This is different in kind from failure modes one through five.** Those were all
about coverage — breadth, parity, permanence, one adjective carrying two
dimensions. This one is about the boundary of what the product is responsible
for. Naming it changes what a demo has to show: the trigger vocabulary is part
of the product, not a detail of the input form.

The running tally across six gates, none of these obvious without looking:

1. **Phase 4** — a true statement implying more *breadth* than existed.
2. **Phase 5** — a true statement implying more *parity* than existed.
3. **Phase 6** — a previously-approved statement that became *false* because the
   product improved underneath it.
4. **Phase 7** — a statement true on one dimension and misleading on another,
   where one adjective could not carry both.
5. **Phase 8** — a statement describing a *permanent* limit in language that
   implied a *temporary* one.
6. **Batch 2** — a statement true about the *rules* and silent about the
   *inputs*, in a product where a wrong input produces a confident wrong answer.

## Which frameworks actually applied, and which did not

**Bid/No-Bid: not applicable, and saying so beats a hollow pass.** This is not a
pursuit decision. Nothing is being bid on and no resources are being committed
to an opportunity. Scoring it out of ten would have produced a number that meant
nothing.

**Premortem: this is where the work was.** See above. Also re-run on the
verification method itself, per the standing rule that a clean result is only as
good as what the method could see: *"our own testing said 119 rules, 8,076
computations, zero hard errors — what did that method structurally miss?"* It
misses **whether the date is right**. Every one of those computations proves the
engine did not crash and produced *a* date; only the hand-worked examples in the
per-state tests prove any date is *correct*. Georgia's O.C.G.A. 9-11-36(a)(2)
row is the proof this matters: it passed every automated check and was still
fifteen days wrong, and it was caught by working the arithmetic by hand.

**NIST AI RMF: applies, and the answer is unusual enough to put in the claim.**
There is **no AI in this feature at all** — no model call, no prompt, no
inference, anywhere between the trigger date and the returned deadline. Verified
by reading the code path, not assumed. That matters externally for two reasons.
First, SAIRNlaw does have real AI features elsewhere, so a reader can reasonably
assume these dates come from a model unless told otherwise, and "an LLM produced
your filing deadline" is exactly the sentence that would lose a legal buyer.
Second, it means the Map/Measure/Manage functions have no surface here: there is
no hallucination rate to test and no drift to monitor, because the output is a
deterministic function of stored rule data. **Govern still applies** — someone
owns which rules go in and by what standard — and that is the primary-source
discipline described below, which is the real governance control on this feature.

## What the claim is measured against (live at time of approval)

| Jurisdiction | Rules | Civil | Appellate | Rule families | Notes |
|---|---:|---:|---:|---:|---|
| United States (Federal) | 21 | 18 | 3 | 11 | widest family range: answer, discovery, amendment, service, summary judgment, pretrial disclosures, expert disclosures, subpoena, appeal |
| Michigan | 18 | 14 | 4 | 8 | largest state set; **21-day appeal period** |
| Georgia | 12 | 9 | 3 | 5 | only computable **cross-appeal** in the engine |
| Pennsylvania | 11 | 6 | 5 | 6 | **10-day appeal period in three named subject matters** |
| California | 10 | 7 | 3 | 5 | 60/60/180 earliest-of appeal; per-method service extensions |
| New York | 10 | 8 | 2 | 7 | 20-day discovery periods; service extension **does** reach a notice of appeal |
| Texas | 10 | 6 | 4 | 6 | answer deadline is a **Monday at 10:00 a.m.**, not a day count |
| Florida | 7 | 6 | 1 | 5 | shifted-start counting |
| Indiana | 7 | 5 | 2 | 6 | discovery rules set no deadline |
| Ohio | 7 | 5 | 2 | 6 | discovery rules set no deadline |
| Illinois | 6 | 4 | 2 | 5 | thinnest set |

**119 rules; federal 18%.** All eleven carry both civil-litigation and appellate
rules and holiday calendars for 2026–2031. Eight backward-counted. Seven
designated-period. Two capped. Four multi-trigger. One terminal-day rule.
Periods are counted in calendar days or in months by anniversary date — nothing
in the engine approximates a month as thirty days.

## The three things most worth demonstrating

**1. The same words mean different things in different states, and the engine
reads each one.** Three of the four states added in Batch 2 add service-extension
days *"to the prescribed period"* (New York, Texas, Georgia); Florida and the
federal rules add them *"after the period would otherwise expire."* That is a
three-day difference on the same facts, always in the late direction if you
assume the federal order. It was found by a failing test, not by reading, and it
had already shipped wrong in Texas before New York exposed it.

**2. Ohio's and Indiana's discovery rules set no deadline.** All six of them,
across interrogatories, admissions and production, set a floor on a period the
requesting party designates. The engine asks for that period, computes from it,
and **refuses** a request designating less than the minimum rather than quietly
computing the minimum. Any tool returning a flat 28 days for an Ohio
interrogatory request is answering a question the rule does not ask.

**3. A holiday calendar is a statutory question, not an attendance record.**
Pennsylvania's courts commonly close on days no statute makes a holiday;
Georgia's statute freezes the federal list as it stood on 1 January 2022 and
separately tells the Governor to close state offices on thirteen days, which are
not the same set; Texas makes five days legal holidays on which courthouses are
routinely open. The engine encodes the statutory test in every case and discloses
the divergence, because padding a calendar with observed closures produces
deadlines **later** than the law allows, which is the direction that misses a
filing.

## Claims that are NOT approved

- ❌ *"litigation deadlines across eleven jurisdictions"* used **unqualified** —
  implies parity that does not exist. Illinois has 6 rules, federal has 21.
  Federal is still the only jurisdiction with summary-judgment, expert-disclosure
  or pretrial-disclosure rules.
- ❌ *"a thirty-day appeal deadline"* stated generally — **false in Michigan**
  (21), in three Pennsylvania subject matters (10), and for a Texas accelerated
  appeal (20). The single most dangerous generalisation in the product.
- ❌ *"computes Ohio's 28-day interrogatory deadline"* — **Ohio has no such
  deadline.** 28 is a floor on a party-designated period. This one sounds
  competent and is wrong.
- ❌ *"we don't cover deposition notice yet"* — implies a roadmap item. Every
  general deposition-notice rule requires only *"reasonable notice"*; there is no
  number and refusing is the final answer, not an interim one.
- ❌ **NEW — ❌ *"give it the date and it gives you the deadline."*** This is the
  Batch 2 failure mode in one sentence. It is true only if the date supplied is
  the event the rule actually names, and in five jurisdictions that event differs
  for the same-sounding act. Never demo the engine without saying which event the
  trigger is.
- ❌ **NEW — ❌ *"every date is verified against primary sources."*** The **rules**
  are, without exception. Three *interpretive* questions rest on secondary
  reading and are documented as such in the seed files: the Texas service-
  extension sequencing (no Texas appellate authority found), *Proctor v. Green*'s
  holding on the Texas Monday rule (full opinion not accessible), and Georgia's
  cascading-rollover reading. Say "every rule," not "every date."
- ❌ **NEW — ❌ *"the engine never returns a date later than the true deadline."***
  Tempting, because that is the design posture nearly everywhere. **Georgia is a
  deliberate exception:** where O.C.G.A. 1-3-1(d)(3) is silent on a Saturday
  whose following Monday is a holiday, the engine cascades to Tuesday, the later
  reading, because the earlier one would fix a deadline on a day the courthouse
  is shut. Documented in the standard's own comment. Do not make a directional
  guarantee.

## Known limits, and what kind of limit each one is

**Permanently uncomputable — refusing is the final answer:** general deposition
notice in every jurisdiction (*"reasonable notice"*); Ind. T.R. 45 motions to
quash (*"promptly"*); Mich. Ct. R. 2.506 objections (*"before the designated time
for appearance"*).

**Unknowable in advance — every jurisdiction has one:** executive-proclamation
and court-closure limbs. Illinois's Governor-proclamation days, Indiana's
office-closed limb, Florida's chief-justice hurricane extension, California's
CCP 12b, Texas's Tex. R. App. P. 4.1(b), New York's presidential and
gubernatorial proclamation days, and Georgia's 1-4-1(a)(2) — which is the
strongest of them, because the statute *requires* the Governor to designate at
least one such day every year.

**A buildable capability gap, currently forcing five refusals:** a "later of two
computed periods" shape. CPLR 5513(c), Tex. R. App. P. 26.1(d), Ohio App.R.
4(B)(1), FRCP 15(a)(3) and Georgia's O.C.G.A. 9-11-36(a)(2) all take the later or
earlier of two limbs that have **different day counts**, where the engine's
existing multi-trigger resolves between two supplied *dates* under one count.
Georgia's is decomposed into two honest rows as a stopgap; the other four refuse.
**This is scoped and buildable — do not describe it as permanent.** That is
precisely the Phase 8 failure mode running in reverse.

**A structural input limit, disclosed above and in the claim itself:** the engine
does not derive a trigger date the law defines or computes, and does not validate
the one it is given.

**A versioning limit:** rule versions are selected by the date the period runs
from. Where an amendment order keys applicability to the date the **case was
filed** — as the Texas Supreme Court's Misc. Docket No. 20-9153 does — the engine
cannot see that and will pick the wrong version for a case filed before the
cutoff whose events fall after it.

**Deliberately out of scope:** statutes of limitation anywhere. Claim-type
specific, often statutory rather than rules-based, and the highest-consequence
error class in the product.

## Why this lives in a document and not in the app

The sentence contains two kinds of fact, and only one is safe to write down.

The **invariant** half — every rule traces to primary-source text, there is a
full audit trail, no model is involved, the engine refuses rather than estimating
— is true independent of what is loaded. That half **is** in the app, in the
coverage card's standing notice.

The **specific** half — which jurisdiction covers what — has now gone stale at
**five consecutive gates**, most recently by four whole phases. That is the
argument for never hardcoding it. The app renders those specifics live from the
loaded rule set.

**So: this document is the point-in-time claim a human makes. The app is the live
one. When they disagree, the app is right and this file is stale.**

## Re-run the gate before changing this

Rewritten at five consecutive gates. The pattern is not going away: any material
coverage change makes the specific half stale, and the failure mode has been
different every single time. Re-run `sairn-decision-gate` and rewrite the sentence
before a new claim goes outside the team.
