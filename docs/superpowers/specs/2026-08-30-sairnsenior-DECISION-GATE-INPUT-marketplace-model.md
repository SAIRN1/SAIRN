# DECISION-GATE INPUT — SAIRNsenior: may we ever ship an open-shift marketplace?

2026-08-30. **This is not research. It is a packet for a `sairn-decision-gate`
run**, and it exists because two independent findings bear on **one** decision and
must be considered together rather than as separate compliance items.

**Nothing here needs deciding today.** SAIRNsenior as built on 2026-08-30 is
outside every category examined. **This packet fires only if someone proposes
open-shift claiming, shift bidding, a caregiver pool shared across agencies, or
any feature where a person who is not the agency's employee chooses work.**

> **Documented readings of primary text, not legal advice.** Confirm with counsel
> before any of it is relied on commercially.

---

## The decision

**Would SAIRNsenior ship a feature that lets a non-employee caregiver select or
bid on work?**

## Why the two findings must be read together

They are not two compliance items. **They are one business-model question, and
they answer it in opposite ways.**

| | **Iowa** | **Rhode Island** |
|---|---|---|
| Instrument | Iowa Code ch. 135Q / 481 IAC ch. 55 | R.I. Gen. Laws ch. 23-17.7.1 / 216-RICR-40-10-10 |
| What it does | **Creates a licensed category** for exactly this model — *health care technology platform*, defined as a marketplace where an **independent contractor bids on open shifts** posted by a health care entity | **Denies the model's premise** — a person supplying workers on a temporary basis **is their employer**, and those workers *"shall be considered employees and **not independent contractors**"*, **for all purposes** |
| So the model is… | **permitted, if registered and policed** | **not available in that form** |

**Iowa tells you what it costs to run the model. Rhode Island tells you that in
at least one state the model does not exist as conceived.** A plan that satisfies
Iowa can still be structurally impossible in Rhode Island, and a fifty-state
product cannot resolve that by registering.

## What Iowa would require if we went inside it

- **Annual registration** with the Department of Inspections, Appeals and
  Licensing; **$500/yr**; certificate issued on approval.
- **Failure to register prohibits contracting with any health care entity in
  Iowa** — a market ban, not a fine.
- **§ 135Q.3(2)(a) is the heavy one:** the platform must verify each professional
  *"meets all applicable state requirements and qualifications of personnel in a
  health care entity setting."* **Across the 38 states surveyed that is the whole
  five-axis model plus the behaviour constraints — per worker, as a condition of
  operating.**
- Verify **minimum state licensing/certification**, and **professional liability
  insurance of $1M per occurrence / $3M aggregate**.
- **Background re-checks triggered by two consecutive years of a worker's
  inactivity** — a compliance job driven by scheduling data.
- **No noncompete** restricting a professional's employment opportunities.
- **Immediate** facility notification on a dependent-adult-abuse allegation.
- **CNA work-assignment reporting** to the direct care worker registry sufficient
  to maintain the worker's active status.
- **Quarterly reporting** of every Medicare/Medicaid entity contracted with **and
  the average amount charged**, broken down by provider type and worker category —
  i.e. **price disclosure to the state**.
- **The scope trap:** "nursing services" at § 135Q.1(10) expressly **includes
  home health aides and non-certified staff providing personal care**. *"We only
  do non-medical care"* is **not** a defence.

## What Rhode Island would do to the same plan

- **R.I. Gen. Laws § 23-17.7.1-2(d):** anyone *"doing business within the state
  that supplies, on a temporary basis, registered nurses, licensed practical
  nurses, or nursing assistants"* to a facility is a **nursing service agency** —
  and **"nursing assistant" expressly includes a home health aide** (§ (c)).
- **The reclassification clause:** *"For all purposes a nursing service agency
  shall be considered an **employer** and those persons that it supplies on a
  temporary basis shall be considered **employees and not independent
  contractors**, and the nursing service agency shall be subject to all state and
  federal laws which govern employer-employee relations."*
- **Consequence:** the supplier carries wage, hour, tax, unemployment,
  workers'-compensation and benefits obligations **by statute**, regardless of
  what any agreement says.

## The four other triggers, which do not move together

Recorded so nobody assumes one clearance covers the rest. **Each was determined
separately and each turns on a different fact:**

| State | Category | Trigger |
|---|---|---|
| Iowa | health care technology platform | **bidding** on open shifts |
| Oregon | caregiver registry (**licence**) | a roster of **private contractor** caregivers **given to the client for hiring** |
| Colorado | home care placement agency | **a fee, for referrals only** |
| Nevada | employment agency for nonmedical services | **contracting with the caregivers** |
| Rhode Island | nursing service agency | **supplying personnel on a temporary basis** |

**A marketplace feature must be re-tested against all five. They would not all
flip together, and Rhode Island's would not be cured by registering.**

## Two marketing-copy constraints that bind today

**These are live now, not conditional on any future feature:**

- **Oregon ORS 443.100** — a person may not *"represent to the public that the
  person is a caregiver registry"* without a licence.
- **Rhode Island 216-RICR-40-10-10 § 10.3(A)(1)** — no agency may *"hold itself
  or represent itself as a nursing service agency or use the term 'nursing
  service agency' **or other similar term** in its advertising, publicity or any
  other form of communication"* without a licence.

**Any Oregon- or Rhode-Island-facing copy should be checked against these before
publication.**

## What is NOT known, and matters to the decision

- **How many other states reclassify — SWEPT 2026-08-30, and it is three, not one.**
  `2026-08-30-sairnsenior-reclassification-sweep.md` ran a ten-pattern sweep over
  every corpus gathered tonight. **Employment status is assigned by law in three
  of the states read, three different ways:**
  - **Rhode Island** — the supplier is the employer and the workers are **not
    independent contractors, for all purposes**. **And the clause is in BOTH the
    staffing part and the home-care part (216-RICR-40-10-17)** — so it binds
    ordinary licensed home care agencies, not only staffing businesses. Broader
    than the determination first recorded.
  - **Nevada** — the intermediary service organization is **employer of record**,
    while the **client directs and trains** (NAC 449.395xx).
  - **Oregon** — the agency is **common law employer** of direct support workers
    **recruited by the individual**, and the individual is a statutory
    **co-employer** (ORS 443.360(1)(g)).

  **Consequences for the decision:** `employment_type` is not a free field — the
  state can override the contract; **"employer" and "who directs the work" are
  separable** and two states separate them explicitly; and a marketplace premised
  on independent contractors has **no lawful shape at all in Rhode Island**.
  **The sweep covers the text fetched tonight, not the country** — a state with no
  hit may still have such a clause in a chapter never fetched.
- **How many other states have a platform-registration category.** Three found
  (IA, CO, OR) plus two adjacent (NV, RI). **They share no keyword** — a term
  sweep finds one of five.
- **Whether Iowa's or Rhode Island's provisions have been applied to app-based
  models** — no case law or agency guidance was sought.
- **The remaining ~12 untouched states.**

## Recommended framing for the gate

1. **Treat "ship a marketplace" as a fifty-state business-model decision, not a
   feature.** The compliance surface is per-state and the *legal character of the
   worker* changes between states.
2. **If the answer is yes, decide the state footprint first** — Rhode Island and
   any other reclassifying state may need to be excluded from the feature rather
   than served differently.
3. **If the answer is no, write it down with its trigger**, so the standing
   condition in the four determinations has something to point at.
