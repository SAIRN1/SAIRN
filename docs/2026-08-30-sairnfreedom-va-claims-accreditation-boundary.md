# SAIRNfreedom — the VA claims accreditation boundary

**Read 2026-08-30 from primary source.** 38 U.S.C. §§ 5901, 5902, 5903, 5904 and
38 CFR 14.630, via Cornell LII's published text of the Code and the CFR.

**Purpose:** the Service Officer feature was held pending this. It is the
highest legal-risk item in the phased build spec and it arrived as a one-line
feature name. This establishes what actually requires federal accreditation and
what does not, so the feature can be scoped against the statute rather than
against an assumption.

**I am not a lawyer and this is not legal advice.** It is a primary-source read
of the operative text, done to the same standard as the ORC 2915 pass. Before
anything ships to a real post, counsel should confirm it.

---

## The operative prohibition, verbatim

**38 U.S.C. § 5901 — *Prohibition against acting as claims agent or attorney***

> "Except as provided by section 500 of title 5, no individual may act as an
> agent or attorney in the preparation, presentation, or prosecution of any
> claim under laws administered by the Secretary unless such individual has been
> recognized for such purposes by the Secretary."

**Read the sentence carefully, because the scope is narrower than the feature
name suggests.** The prohibited thing is *acting as an agent or attorney* in
the **preparation, presentation, or prosecution** of a claim. It is not a
prohibition on being helpful about VA benefits. The three verbs and the
agent-or-attorney capacity are both load-bearing.

Note the statute says **"recognized"**, not "accredited". Accreditation is the
administrative mechanism through which recognition is granted; the words are
used interchangeably in practice, and the regulation uses "accredited".

---

## Who gets recognised, and the fee condition that runs through everything

**38 U.S.C. § 5902(a)(1)**, verbatim:

> "The Secretary may recognize representatives of the American National Red
> Cross, the American Legion, the Disabled American Veterans, the United Spanish
> War Veterans, the Veterans of Foreign Wars, and such other organizations as
> the Secretary may approve, in the preparation, presentation, and prosecution
> of claims under laws administered by the Secretary."

**This is directly on point for this product.** The American Legion and the VFW
are named *in the statute* as organizations whose representatives the Secretary
may recognize. A post's Service Officer is, in the ordinary case, an accredited
representative of exactly such an organization.

**§ 5902(b)(1)(A)** conditions that recognition on a certification that

> "no fee or compensation of any nature will be charged any individual for
> services rendered in connection with any claim."

**§ 5903 — *Recognition with respect to particular claims*** carries the same
shape: recognition for a particular claim requires the no-fee certification and
a filed power of attorney.

**§ 5904(c)** restricts fees for agents and attorneys at the front of the
process — no fee for services provided **before** the claimant is given notice of
the agency of original jurisdiction's initial decision — and caps the total at
**20 percent of past-due benefits** where paid from those benefits.

> **The single thread through §§ 5902, 5903, 5904 and 14.630 is FEE.** Every
> route to representing a claimant either forbids compensation outright or caps
> and stages it. This matters for the product in one specific way, in §"What the
> software must never do" below.

---

## The one-claim exception, verbatim

**38 CFR § 14.630(a)** — *Authorization for a particular claim*:

> "Any person may be authorized to prepare, present, and prosecute one claim."

Conditions: execution of **VA Form 21-22a** (appointment of an individual as
claimant's representative) and a signed statement that **"no compensation will
be charged or paid for the services."** Limited to **one claim**, with a General
Counsel exception available in unusual circumstances.

So an unaccredited person is not categorically barred from helping — but the
route out is narrow, one-claim, paperwork-bound and unpaid.

---

## The boundary, stated as a build rule

### Requires accreditation — the software must NOT enable an unaccredited user to do these

- **Prepare** a claim: drafting, assembling, or auto-filling a VA claim form
  (21-526EZ and family), composing statements in support of a claim, organising
  an evidence package for submission.
- **Present** a claim: submitting to VA on a claimant's behalf, or acting as the
  channel through which a claim reaches VA.
- **Prosecute** a claim: managing it through the process, responding to
  development letters, arguing rating decisions, pursuing appeals.
- Anything that **functions as** the above regardless of what the UI calls it. A
  "helper" that produces claim language is claim preparation.

### Does NOT require accreditation — safe to build

- **Referral** to an accredited representative, a VSO, a county veterans service
  office, or VA directly. Naming who can help is not representing.
- **Appointment scheduling** with the post's Service Officer, and a log of who
  was seen and when.
- **General information**: published VA material, eligibility overviews, links
  to VA's own resources — presented as information, attributed, and not tailored
  into advice about a specific claim.
- **Tracking the post's own accreditation facts** — which officers are
  accredited, through which organization, with what number and date. This is a
  compliance-support feature and it is genuinely useful, because accreditation
  is a per-person, per-organization status that expires and changes.
- **Recording that a referral happened** and its outcome at a coarse level, for
  the post's own service-hour reporting.

### The grey zone that must not be entered casually

A post's Service Officer **who is personally accredited** may lawfully do the
first list. But the software would then be a system of record touching live VA
claim material — a completely different product with its own privacy,
retention and records obligations, and a fresh legal review. **That is not phase
1 and should not be reached by accident**, which is exactly how it would be
reached if "help with claims" were implemented as a feature and accreditation
checked later.

---

## What the software must never do, and one precedent for why

**No fee may attach to claims assistance.** Every recognition route in §§ 5902,
5903 and 14.630 requires certifying that no compensation is charged. A post is a
nonprofit and its Service Officer serves without charge, so this is satisfied
naturally — **but the product must never introduce a charge, tier, subscription
gate or paid-upgrade that sits between a veteran and claims help.** Putting the
Service Officer function behind a paid tier would create exactly the
compensation the certification denies.

**The AI assistant must decline claim-strategy questions outright.** This
platform has already made this exact call once, on SAIRNroofing: the operations
assistant's system prompt was changed to refuse claim-strategy questions,
because *"it was never given claim data, but nothing stopped it answering a
negotiation question from general knowledge, and an app-branded answer of that
shape was the real exposure."*

**The same reasoning applies here with higher stakes.** An AI answering "what
should I claim for?" or "how should I word my statement?" is producing claim
preparation, under the post's brand, for an unaccredited asker, at scale. The
decline must be in the system prompt, not in a disclaimer the user scrolls past.

---

## Verdict for the phased build spec

**The Service Officer feature is safe to build in Phase 5, scoped to: referral
directory, appointment scheduling and log, accreditation-status tracking, and
attributed general information.** That is a real, useful feature and it is
entirely outside the § 5901 prohibition.

**Everything touching claim preparation, presentation or prosecution is out of
scope for this product**, and should stay out until there is a specific decision,
a legal review, and a reason better than "the officer is accredited so we can."

Spec item §9a.1 moves from *blocked pending research* to *scoped, with a named
boundary*.

---

## Read, and not read — stated plainly

**Read in full:** 38 U.S.C. §§ 5901, 5902(a)(1) and (b)(1)(A), 5903, 5904(a) and
(c); 38 CFR § 14.630(a).

**NOT read, and each could change the detail below the boundary rather than the
boundary itself:**

- **38 CFR § 14.629** — the accreditation requirements themselves. **eCFR was
  unreachable**: `ecfr.gov` 302-redirected to `unblock.federalregister.gov`, so
  the CFR text here came from Cornell LII instead. 14.629 was not retrieved from
  either source and should be read before any accreditation-tracking fields are
  finalised, since it governs what those fields mean.
- **38 CFR §§ 14.631–14.637** — powers of attorney, suspension and cancellation.
- **VA's own accreditation program materials** and the searchable accredited
  representative database, which is the practical source for verifying an
  officer's status.
- **State-level** restrictions on claims assistance, if any. Ohio was not
  checked.
- **38 U.S.C. § 5904(b)** suspension procedures, referenced by § 5903 and not
  retrieved.

Everything above came from one automated read per section. The verbatim quotes
are reproduced exactly as returned; before any of this is encoded into product
behaviour, a second human read of the statute pages is warranted — the same
standard applied to ORC 2915.
