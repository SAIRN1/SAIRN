# Candidate domain skill — `sairn-regulated-boundary`

**Not built. Not installed.** A proposal, with the evidence base assembled so
the decision can be made on whether the pattern is real rather than on whether
it sounds useful.

**Answers two questions at once:** whether tonight's SAIRNfreedom work produced
a skill-worthy incident (it did), and what the next **domain** candidate is
after `sairn-rbac` — the 8-process/1-domain imbalance flagged in the pack README.

---

## The pattern

**A product feature that sits next to a licensed or regulated activity, where
the boundary is defined by what the feature DOES, not by what it is called.**

Every instance below is the same failure waiting to happen: a feature named
after the regulated activity, or assumed safe because it is named something
else. The label is not the boundary.

**Five apps. All verified against the committed record, not recalled.**

### 1. SAIRNfreedom — VA claims (2026-08-30, tonight)

38 U.S.C. § 5901 restricts acting *"as an agent or attorney in the preparation,
presentation, or prosecution"* of a claim. **The restricted thing is the
agent-or-attorney capacity in those three verbs — not being helpful about VA
benefits.** The one-line feature name "Service Officer" implied a far broader
prohibition than the statute imposes; reading it moved the feature from blocked
to scoped.

The operative rule the doc lands on, verbatim: *"Anything that **functions as**
the above regardless of what the UI calls it."*

Two product rules fall out that a disclaimer cannot satisfy:
- **No fee may attach**, anywhere — every recognition route requires certifying
  no compensation of any nature, so the function cannot sit behind a paid tier.
- **The AI must decline in its system prompt, not in a disclaimer.** An
  assistant answering "what should I claim for" *is* claim preparation, under
  the post's brand, at scale.

### 2. SAIRNroofing — the same call, already made

Cited inside the VA doc as precedent: the operations assistant's system prompt
was changed to refuse claim-strategy questions, because *"it was never given
claim data, but nothing stopped it answering a negotiation question from
general knowledge, and an app-branded answer of that shape was the real
exposure."*

**Two apps, same conclusion, reached independently.** That is the bar for a
pattern rather than an incident.

### 3. SAIRNlaw — deliberately not a filing transmitter

Ohio has no statewide trial-court e-filing system; programmatic filing requires
EFSP certification — *"a contract, not an API key."* So the app **does not
file**. It ships an **E-Filing Readiness Check** instead: inspects real PDF
bytes against two courts' published rules, every rule carrying its citation.

Three-state results — **PASS / FAIL / CANNOT VERIFY** — because margins, line
spacing and "exclusive of the table of contents" page counts cannot be read
from PDF bytes, and *"reporting them as passes would be the exact
false-confidence failure this module exists to avoid."* The panel says on
screen that it files nothing.

**The general move: build the adjacent thing you can do honestly, and say on
screen what it does not do.**

### 4. SAIRNsenior — Iowa ch. 135Q, and the trap underneath it

Iowa Code 135Q.1(6) requires **three cumulative elements** — an internet
marketplace, an independent contractor **bidding**, and open shifts **posted**
by a health care entity. SAIRNsenior has none, verified against the file
itself: zero occurrences of open-shift, bid, marketplace, independent
contractor or 1099, against a roster-and-assign model with 65 "assign" hits.

**And the trap, which is the transferable part:** "nursing services" at
135Q.1(10) expressly includes home health aides and noncertified personal-care
staff — so *"we only do non-medical care"* **would not be a defence** for a
future marketplace feature. The exemption today comes from the *model*, not
from the care type. Change the model and the exemption goes.

### 5. SAIRNdental — a service agreement is not a BAA

From the open-work index: *"a service agreement containing 'HIPAA-trigger
language' is **not** a BAA and does not satisfy the requirement. They are
separate instruments with different required contents."*

**The named failure mode: drafting a good service agreement and believing the
HIPAA question is handled.** Same shape — a document that reads like compliance
is not compliance.

---

## Why this is a domain skill and not a restatement of `sairn-decision-gate`

`sairn-decision-gate` asks *should we pursue this, and is this claim true.* It
is a judgment gate on a decision.

This is narrower and more mechanical: **given that we are building next to a
regulated activity, where exactly is the line, and what does crossing it look
like in code.** It produces build constraints — system-prompt refusals, no-fee
tiers, on-screen statements of what a feature does not do, three-state results
instead of two.

Nearest existing neighbour is `sairn-decision-gate`; both would need to name
each other, per `sairn-skill-author` rule 7.

## Why it qualifies on the pack's own test

The README's standard is *"nobody else can write this."* A generic
"regulatory-compliance skill" would be worthless — the rules differ per
jurisdiction and per domain, and restating any public standard has no moat.

What is not reproducible is **the collection**: five apps, five different
regulators (VA, insurance-claims practice, court e-filing, Iowa employment
agencies, HIPAA), each with the boundary found the same way, and each with the
specific code-level consequence recorded. That is a pattern nobody outside this
platform has the material to assemble.

## Before building it

- **Read `38 CFR 14.629` first** — disclosed as NOT READ in the VA doc, and it
  governs what accreditation-tracking fields mean.
- Check whether SAIRNcare and SAIRNvet have instances too (SAIRNcare is
  HIPAA-adjacent; SAIRNvet has USDA APHIS and CITES surfaces). Five is already
  a pattern; seven would set the structure.
- Run `sairn-skill-vetter` over it before it ships anywhere, same as the nine.

**Recommendation: build it, after the nine-pack has been vetted.** It is the
strongest domain candidate available and it directly corrects the imbalance the
README names — but the pack's own gate should run first, on principle.
