---
name: sairn-decision-gate
description: 'The layer above architecture and above code quality. Trigger before: pursuing any RFP or government/institutional contract, committing to a new vertical or major build, making any claim in a proposal or to a customer about status ("production," "live," "complete," "compliant"), and any time a decision is expensive or embarrassing to walk back. This is not a coding skill and not a writing skill — it is the judgment layer that decides whether something should be pursued at all and whether a claim being made is actually true. Trigger words: "should we," "is this real," "RFP," "proposal," "bid," "walk away," "is this true," "before we commit."'
---

# SAIRN Decision Gate

Three real, authoritative frameworks — not invented for SAIRN, borrowed from where they already work, because reinventing this badly is worse than adopting something proven. Each answers a different question. Run all three before anything expensive or public-facing goes out the door.

## Framework 1 — Bid/No-Bid Gate (should we even pursue this?)

Adapted from the Shipley Capture Process and the APMP (Association of Proposal Management Professionals) Body of Knowledge — the industry-standard discipline government contractors use. The core finding that justifies this existing as a formal gate rather than a gut call: bid/no-bid discipline is the single highest-leverage decision in the entire process, more impactful than proposal quality itself, because it stops resources from being spent on pursuits that were never winnable.

**Run this before committing real time to any RFP, government contract, major new client, or new vertical:**

| # | Question | SAIRN-specific version |
|---|----------|------------------------|
| 1 | Is the opportunity real? | Funding confirmed, timeline achievable, not a fishing expedition |
| 2 | Do we meet the qualifications TODAY, not aspirationally? | Production examples, references, certifications — as they actually stand right now, not what they'll be in 3 months |
| 3 | What's the true cost of pursuing this? | Hours, money, and what NOT building elsewhere costs us meanwhile |
| 4 | What's the cost of a "no"? | Sometimes zero — a walked-away pursuit that was never winnable costs nothing but ego |
| 5 | Does this fit the platform's actual strategic direction? | Or is it a shiny distraction from StoneDesk/SAIRNbuild/SAIRNdesign momentum |
| 6 | Can our current team/bandwidth actually deliver if we win? | A win we can't execute is worse than a loss |
| 7 | What do we NOT currently have that this requires? | Insurance, bonding, financials, a live reference — name every gap explicitly |
| 8 | Is any gap fixable before the deadline, and is that realistic given everything else in flight? | Not "could we," — will we, given the actual calendar |

**Score honestly, out of 10 per question. Below roughly 60-65%, the honest answer is usually walk away or explicitly accept the long odds going in — don't quietly hope the gaps close themselves.**

This gate would have surfaced the Cleveland Metroparks insurance/bonding/production-example gaps in minutes as a structured pass, instead of them emerging one at a time across a longer conversation. Use it FIRST, at the moment an opportunity appears — not after time is already sunk into it.

## Framework 2 — Premortem (is this actually going to work, or are we fooling ourselves?)

Gary Klein's technique, later popularized by Daniel Kahneman: assume the thing has already failed — a year from now, the RFP was lost, the claim was challenged, the app broke under real load — and work backward to explain why. This works because imagining a failure as having already happened measurably improves people's ability to identify its real causes, versus asking "what could go wrong" in the abstract, which tends to produce polite, hedged answers instead of real ones.

**Run this on:**
- Any proposal before it's submitted: *"It's six months from now and Cleveland Metroparks rejected us / found something we claimed was false. What was it, and why didn't we catch it before submitting?"*
- Any "production" or "complete" claim before it's said out loud to anyone outside the team: *"Someone checked this claim and it wasn't true. What did they find?"*
- Any architecture decision before it ships: *"This broke at 10x the current load. What broke first?"*

The rule that makes this work: assume the failure as a stated fact, don't hedge it as a possibility. "What might go wrong" gets polite answers. "This already failed, why" gets real ones.

**Pair this with Annie Duke's distinction: judge the decision by the quality of the reasoning at the time, not by how it turned out.** A good decision made with the actual information available can still lose. A bad decision (skipped diligence, wishful claims) can still win by luck. Keep a short decision log for anything that went through this gate — what we knew, what we decided, why — so a later win doesn't get mistaken for proof the shortcuts were fine, and a later loss doesn't get mistaken for proof the honest gate was wrong to have been strict.

**Real proof this works, not just theory (added 2026-07-27):** a real "assume it already failed" question — "we called StoneDesk clean after a full mechanical review; what did the review never actually see?" — would have surfaced the auth-gate blind spot before it needed a dedicated visual-review pass to find it: every code-level check that session ran, however thorough, never got past the login screen, because none of them actually ran the app. Four completely inaccessible panels and a permanent broken overlay sat undetected through every "clean" mechanical pass, because nobody had asked what the review method itself couldn't see. Premortem isn't just for RFPs — run it on "what did our own verification method structurally miss" before trusting any clean result.

## Framework 3 — NIST AI RMF (is the AI risk actually managed, or just asserted?)

The US National Institute of Standards and Technology's AI Risk Management Framework, extended for generative AI via NIST AI 600-1 — the same document Cleveland Metroparks' own RFP cites by name. Four functions, Govern sitting at the center of the other three:

- **Govern** — who owns AI risk decisions here, is there an actual policy (not just a verbal understanding), does it cover data use/training restrictions, subprocessor disclosure, output ownership
- **Map** — for this specific use case, what data touches the AI, what could realistically go wrong, who's affected if it does
- **Measure** — is accuracy/hallucination rate/bias actually tested, or just assumed to be fine because it usually seems fine
- **Manage** — is there a real monitoring and incident-response plan, or does "we'll handle it if it happens" count as the plan

**Run this before:** any AI feature ships to a real customer, any government/institutional proposal that will be scored on AI governance (Cleveland Metroparks weights this at 35% under Technical Capability), any time the honest answer to "have we tested this for bias/drift" is "we assume it's fine."

The dual value here: doing this work honestly, internally, for SAIRN's own AI features is the same work that answers the RFP's own governance questions — this isn't overhead on top of winning the contract, it's the actual substance of a winning proposal.

## When all three disagree

Bid/No-Bid says pursue it, Premortem surfaces a real unaddressed failure mode, NIST RMF finds a governance gap — in that order of precedence, fix what Premortem and RMF found before treating the Bid/No-Bid "go" as final. A good opportunity with an unaddressed real risk is not yet a good decision; it's a good opportunity with homework left to do.

## Prioritization Principle: risk first, not scope first (added 2026-07-29)

When facing a queue of known issues, order by actual risk/impact, never by scope size or order of discovery. These are different axes and conflating them produces the wrong sequence.

**Proof this works, from one real session:** a live data-clobber bug (`nps-score-btns`, a few lines of code, actively destroying real survey data on every panel visit) got fixed immediately. The Vendor Ordering Catalog (a large, real, multi-session feature with ~120KB of legitimate logic) got correctly *deferred* — not because it was unimportant, but because nothing about leaving it unbuilt was actively harming anyone, while the data-clobber bug was.

**The actual ordering, in practice:**
1. Anything actively destroying or corrupting real data, right now
2. Security vulnerabilities (stored XSS, exposed credentials)
3. Crashes on normal, expected use
4. Silent incorrect behavior (a button that does nothing, a number that's quietly wrong)
5. Cosmetic/structural issues with no functional impact (a false-positive scanner hit, a harmless split)
6. Real feature/scope decisions (build vs. delete vs. defer) — these can be large and important, but they're a different kind of question than "is something broken right now," and rushing them at the end of a long session produces worse decisions than deferring them to fresh judgment.

A large, well-scoped, explicitly-deferred decision is not unfinished work — it's the correct output of applying this principle honestly.

## "100%/complete" is a different claim than "correctly prioritized" (added 2026-07-30)

The Prioritization Principle above answers a different question than this one, and the two must not get merged. Prioritization decides *what to fix first* when something is already known to be broken. It does not decide *whether a "100%"/"complete"/"done" claim is true* while that known thing is still broken. Those are separate axes, and running the prioritization logic in answer to a completeness question is a category error, not a nuanced judgment call.

**The rule:** a known bug — however low-severity, however correctly deferred by risk-ordering — does not get to ride along unfixed underneath a "100% done" or "fully complete" claim. If it's not fixed, the honest claim is "complete except for N known items" (name them), not "100% complete." Severity governs the fix queue; it does not govern what the completeness claim is allowed to say.

**Why this needs to be a named rule and not just "obviously true":** the failure mode isn't lying outright — it's reaching for the Prioritization Principle's own language ("this is low-severity," "this was correctly deferred," "this doesn't block anything") to talk a "100%" claim back down to something softer than what a person holding the line on "100% means 100%" is actually asking. That person is applying the correct standard. Prioritization logic, built for a different question, should never be the tool used to argue them out of it.

**How to apply:** when someone pushes back on a "100%/complete" claim by pointing at a known unfixed item — even one already correctly triaged as low-severity and deferred — the right response is to correct the claim (scope it honestly to what's actually done), not to defend the claim by re-explaining why the item was deprioritized. Prioritization was never in question; the claim's accuracy was.
