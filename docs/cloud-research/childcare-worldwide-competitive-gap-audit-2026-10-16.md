# Worldwide competitive-gap audit — LICENSED CHILD CARE / EARLY LEARNING CENTRES

**Written 2026-10-16 by fourth, batch b28 item 4. SAIRN has no app in this
vertical. This is a market audit, not a product audit.**

---

## 0. THE DISPATCH'S PREMISE WAS WRONG AND THE CORRECTION CHANGED WHAT GOT WRITTEN

**Stated so it is not read as a silent reinterpretation.** The dispatch said to
pick *"the next vertical NOT already covered by the four existing audit docs
(plumbing/electrical/HVAC, roofing+dental+senior, SAIRNmechanical,
StoneDesk)."*

`docs/cloud-research/` holds **20 documents**, not four, and
`docs/2026-09-29-competitive-gap-doc-inventory.md` — which derives its universe
with `git ls-files '*.html'` rather than trusting a list — records that **every
one of the 18 real SAIRN products has a competitive-gap doc**, the last three
gaps (`sairndesign`, `sairnlegacy`, `sairnscape`) having been closed on
2026-10-05 and `sairncare`'s having been landed on main the same day. The four
named in the dispatch are real documents, but they are four of twenty.

**So "the next vertical not covered" cannot be an existing SAIRN app, and the
only non-vacuous reading is a vertical SAIRN HAS NOT BUILT FOR.** That is what
this document audits. Had it been read the other way, the work would have been
a 21st audit of an already-audited app.

**Why this vertical:** it is the closest uncovered market to primitives the
platform already ships, and §4 names those primitives with the command that
found them rather than asserting a fit.

---

## 1. THE MARKET, AND ITS DENOMINATOR DISAGREES WITH ITSELF

**Three sources, three numbers, and they are not reconcilable — so all three
are given rather than one being picked.**

| count | what it counts | source |
|---|---|---|
| **92,786** | licensed child care centres, 2023 | Center for American Progress, *Measuring America's Licensed Child Care Supply* |
| **83,176 centres + 53,653 family homes** | licensed facilities, **29 states only**, Sep 2026 | LocationLists licensed-provider database |
| **82,162** | **employer establishments** in child care services, 2023; 1,045,052 employees; $31.0bn annual payroll | US Census County Business Patterns 2023 |

The Census figure is **not** a licensing registry and its own publisher says so;
it counts establishments with paid employees, which excludes most family child
care homes and is a different question. **A fourth figure of "around 634,500
licensed childcare facilities" appears in secondary coverage and is an order of
magnitude above the other three; it is recorded here as UNRECONCILED and is not
used.**

**What is safe to say:** the US has **on the order of 80–95 thousand licensed
centres** plus a comparable number of family homes, and roughly a million
employees. **What is not safe to say:** any precise total, which is why none is
quoted as one.

---

## 2. THE INCUMBENTS, AND THE MARKET LEADER IS WEAK WHERE COMPLIANCE LIVES

**This is the finding.** Shares below are 6sense's tech-install share for the
*Child Care and Daycare Management* category — **an install-base estimate from
observed technographics, not revenue share and not a census**, which matters
because it over-weights detectable web-facing deployments.

| vendor | share | customers |
|---|---|---|
| **brightwheel** | **45.92%** | 2,456 |
| **Procare** | **27.07%** | 1,448 |
| ChildCareCRM | 10.71% | 573 |
| Bright Horizons | 9.42% | — |
| Kidsoft | 3.20% | — |
| EZCare | 1.46% | — |
| DayCare Works | 1.01% | — |

**Lillio (formerly HiMama) does not appear in that ranking at all**, while
secondary comparison coverage treats it as one of three leaders. Recorded as a
**discrepancy between sources, not resolved** — a category share table that
omits a vendor other sources call a leader is evidence about the table.

### The split, in the incumbents' own competitive material

* **Procare** is the compliance product: real-time staff-to-child ratio with
  configurable alerts when a ratio goes off; state-specific licensing
  compliance reports — daily attendance records, ratio documentation,
  **background-check expiration tracking**, incident logs; deepest CCDF
  subsidy billing.
* **brightwheel** is the parent-engagement product: **no proactive ratio alerts
  at any tier**, **no real-time staff-to-child ratio monitoring**, compliance
  features limited on lower tiers, and it trails Procare on complex subsidy
  billing and detailed licensing compliance reports. Multi-location centres
  additionally lack consolidated reporting.

**SO THE VENDOR WITH ~46% OF THE INSTALL BASE IS THE ONE WITHOUT RATIO
MONITORING OR CREDENTIAL-EXPIRY TRACKING** — and ratio and background-check
currency are the two things a licensing inspector asks about. That is not a
feature gap in a small vendor; it is the largest share of the market running
without the compliance layer, with the compliance-strong alternative at 27%.

**CAVEAT THAT IS NOT FOLDED INTO THAT CLAIM:** the "brightwheel does not have
X" statements above come from **comparison and competitor-authored content**,
including Procare's own marketing and third-party review blogs. They are
consistent across several independent sources, and they are **not** vendor
documentation. **No brightwheel account was provisioned and no feature was
driven.** This is a reading of the market's own literature, which is the right
evidence for *where the gap is claimed to be* and the wrong evidence for
*whether it is really absent today*. Closing that needs a trial account.

---

## 3. THE REGULATORY SURFACE, AND IT MOVED TWICE IN TWENTY-SIX MONTHS

This is the part a software product gets wrong, and it is dated and verifiable.

### 3.1 Background checks — federal floor, state variation

Every state must require an **eight-component** background check for child care
staff under **45 CFR 98.43**: FBI fingerprint check; NCIC National Sex Offender
Registry; and criminal, sex-offender and child-abuse registry checks in **each
state of residence from the past five years**. **Renewed at least once every
five years** for existing staff — **45 CFR 98.43(d)(2)(ii)**.

**A five-year renewal clock, per employee, per state of residence, with eight
components that can each be outstanding separately.** That is an expiry-tracking
problem with a compound key, and it is exactly what Procare sells and
brightwheel is reported not to have.

### 3.2 Ratios — set per state, per age band, with a separate group-size cap

Two examples, from 2026 state requirement summaries:

| state | infant | toddler | preschool |
|---|---|---|---|
| Illinois | 1:4, max group 12 | 1:5, max group 15 | 1:12, max group 24 |
| Delaware | 1:4, max group 8 | 1:6, max group 12 | 1:10, max group 20 |

**Ratio and group size are two separate constraints and a room can satisfy one
while violating the other** — 1:4 with 16 infants in one group meets the
Illinois ratio and breaks its group cap. A product that models only a ratio
cannot see that.

### 3.3 THE BILLING BASIS WAS MANDATED, THEN RESCINDED — AND THE RESCISSION IS LIVE

| date | instrument | what changed |
|---|---|---|
| **2024-03-01** | *Improving Child Care Access, Affordability, and Stability in the CCDF*, final rule, 45 CFR Part 98 | required states to pay providers **prospectively** and **on authorised ENROLMENT rather than attendance**; capped family co-payments at **7%** of income; required some direct services via grants or contracts |
| 2024 | CCDF rule update | tightened **attendance documentation** requirements for subsidy-receiving providers |
| 2026-01 | HHS proposed rescission | proposed removing the four most onerous of those requirements |
| **2026-05-12** | ***Restoring Flexibility in the Child Care and Development Fund (CCDF)*, FINAL RULE**, 91 FR No. 91, doc 2026-09382 | **RESCINDS all four**: the 7% co-pay cap, the grants/contracts requirement, **prospective payment**, and **payment based on authorised enrolment**. Restores reimbursement-basis payment as an option. States **may** still implement any of them by choice. |
| **2026-07-13** | — | **that rescission takes effect** |

**THE BILLING BASIS FLIPPED FROM ATTENDANCE TO ENROLMENT AND BACK INSIDE
TWENTY-SIX MONTHS, AND IT IS NOW A PER-STATE CHOICE RATHER THAN A FEDERAL
RULE.** Any product that hardcoded "pay on enrolment" in 2024 is wrong from
2026-07-13 in every state that reverts, and wrong the other way in every state
that keeps it. **A correct product cannot hold one answer at all** — it has to
hold the rule **per state, with an effective window, and evaluate it against
the SERVICE PERIOD** rather than against today.

**That is the same shape as the problem SAIRNdental solved for CDT editions on
2026-09-02 and that I finished in this same batch:** a published rule set that
is reissued on a schedule, where the correct determination depends on the date
of service and not on the current edition. §4.

---

## 4. WHAT SAIRN ALREADY HAS, VERIFIED RATHER THAN ASSERTED

Measured, not recalled — `grep -ciE` over the app files at the repo root:

**A credential-expiry primitive already ships in 14 of the 18 products**
(`sairnbiz`, `sairnbuild`, `sairncare`, `sairncash`, `sairncode`, `sairndental`,
`sairnfreedom`, `sairngrounds`, `sairnlaw`, `sairnlegacy`, `sairnmechanical`,
`sairnroofing`, `sairnsenior`, `stonedesk`) — each carrying both expiry and
credential vocabulary.

**An EFFECTIVE-WINDOW / date-of-service determination primitive ships in four**
(`grep -lci effective_from`): `sairncare`, `sairndental`, `sairnlaw`,
`sairnsenior`. SAIRNdental's is the fully worked one: `cdtStatusFor(proc,
serviceDate)` evaluates a code against the **date of service, not today**, with
a four-state verdict in which **"not verifiable" is a real state** rather than a
pass, and — as of this batch — a revise path that keeps the row's identity so
posted charges stay attributable, and a charge-level stamp of the code and
edition **as billed**.

**That is a direct structural answer to §3.3**, which is the one requirement in
this vertical that no incumbent can have got right, because it changed after
they shipped.

**AND THE HONEST OTHER HALF.** Mapping is not building, and this platform's
own standing convention says a byte-identical pattern is not safe in a new
context until the target's scale, input range and criticality tier are
re-qualified. Specifically **unqualified** here:

* **Ratio-and-group-size is NOT an existing primitive in any app.** No SAIRN
  product models a live occupancy constraint with two simultaneous limits. It
  is the single largest build item and nothing in §4 reduces it.
* **CCDF subsidy billing** is deeper than any billing path the platform
  ships; Procare's lead there is described as its strongest area and is not
  something an effective-window primitive addresses.
* **Scale is different.** A centre has 1 room–20 rooms and 10–200 children
  checking in inside the same 30 minutes. The check-in burst is the load shape,
  and brightwheel's reported app crashes "during critical check-in times" say
  the incumbents find it hard. No SAIRN app has that arrival profile.
* **Criticality tier would be high and is not assessed.** A wrong ratio is a
  child-safety determination and a licensing action, not a billing error.

---

## 5. WHERE THE GAP IS, AND WHAT WOULD HAVE TO BE TRUE

**The gap is not "a childcare app".** It is three specific things the market's
own literature says the 46%-share leader does not do and the 27% alternative
sells as its differentiator:

1. **Live ratio AND group-size compliance per room per age band, per state**,
   evaluated continuously rather than reported after the fact — two constraints,
   not one (§3.2).
2. **Eight-component background-check currency per employee**, with a five-year
   renewal clock and a per-state-of-residence component set, where an
   outstanding component is a named state and never a silent pass (§3.1).
3. **Subsidy billing basis held as a per-state rule with an effective window**,
   evaluated against the service period — because the federal answer changed on
   2026-03-01 and changes back on 2026-07-13 (§3.3).

**WHAT WOULD HAVE TO BE TRUE BEFORE THIS IS A BUILD DECISION, and none of it is
established here:**

* **A trial account on brightwheel and on Procare**, driven, to replace
  competitor-authored claims about absent features with observed behaviour.
  **This audit's central claim rests on secondary sources and says so.**
* **One real centre director interviewed.** Nothing in this document comes from
  an operator; every source is a vendor, an aggregator or a regulation.
* **The per-state rule matrix sized.** 50 states × age bands × group caps ×
  subsidy basis is a content obligation, not a code one, and the platform has
  no precedent for maintaining one. SAIRNdental deliberately refused to bundle
  a CDT library on copyright grounds and made the practice enter its own codes;
  **state ratio tables are public and that refusal does not transfer** — but
  somebody owns keeping 50 of them current, and that is a cost with no owner.
* **The decision gate.** Per `sairn-decision-gate`, a new vertical is a
  commitment that is expensive to reverse, and this document is explicitly not
  that gate.

---

## 6. WHAT THIS DOCUMENT DOES NOT CLAIM

* **No product was driven.** No brightwheel, Procare, Lillio or ChildCareCRM
  account was provisioned, opened or tested. Every statement about what a
  competitor does or does not do is a reading of published material, much of it
  **written by a competitor**, and §2 names that limit rather than burying it.
* **No market size is asserted as a single number.** §1's three sources
  disagree and a fourth is an order of magnitude out and is excluded as
  unreconciled.
* **The share table is an install-base technographic estimate**, not revenue
  share and not a census, and it omits a vendor other sources call a leader.
* **No regulation was read in full.** §3.3's rescission is sourced to the
  Federal Register document number, its volume and its effective date; the
  underlying rule text was not read end to end, and a redirect blocked the
  direct fetch. **Re-derive from 91 FR No. 91 / doc 2026-09382 before quoting
  it in anything customer-facing.**
* **Nothing here is a recommendation to build.** §5 is a list of what is
  unestablished, which is the opposite.

---

## Sources

- [Measuring America's Licensed Child Care Supply — Center for American Progress](https://www.americanprogress.org/article/measuring-americas-licensed-child-care-supply/)
- [Licensed Childcare Provider Database — LocationLists](https://locationlists.com/data/childcare-provider-database)
- [Daycare Industry Statistics (2026), Census County Business Patterns](https://startbusinessbystate.com/daycare-industry-statistics/)
- [brightwheel — Market Share, Competitor Insights (6sense)](https://6sense.com/tech/child-care-and-daycare-management/brightwheel-market-share)
- [Procare — Market Share, Competitor Insights (6sense)](https://6sense.com/tech/child-care-and-daycare-management/procare-market-share)
- [Best Child Care And Daycare Management Software in 2026 (6sense)](https://6sense.com/tech/child-care-and-daycare-management)
- [Best Childcare Center Management Software 2026: Procare vs Brightwheel vs HiMama vs Kangarootime — LaunchAdvisor](https://www.launchadvisor.co/guides/childcare-center-management-software-child-daycare-center)
- [Why Some Child Care Centers Are Switching from Brightwheel in 2026 — Procare (competitor-authored)](https://www.procaresoftware.com/blog/why-some-child-care-centers-are-switching-from-brightwheel-in-2026/)
- [Brightwheel vs. Lillio vs. Procare — Illumine](https://illumine.app/blog/brightwheel-vs-lillio-vs-procare)
- [Childcare Background Check Requirements by State (2026) — Reveal Background](https://www.revealbackground.com/childcare-background-check-requirements-by-state/)
- [Illinois Childcare Licensing Requirements (2026) — brightwheel](https://mybrightwheel.com/licensing-requirements/illinois/)
- [Delaware Childcare Licensing Requirements (2026) — brightwheel](https://mybrightwheel.com/licensing-requirements/delaware/)
- [Improving Child Care Access, Affordability, and Stability in the CCDF — final rule, 2024-03-01](https://www.federalregister.gov/documents/2024/03/01/2024-04139/improving-child-care-access-affordability-and-stability-in-the-child-care-and-development-fund-ccdf)
- [2024 CCDF Final Rule FAQ — ACF Office of Child Care](https://acf.gov/occ/faq/2024-ccdf-final-rule)
- [Restoring Flexibility in the Child Care and Development Fund (CCDF) — final rule, 2026-05-12, 91 FR No. 91, doc 2026-09382](https://www.govinfo.gov/content/pkg/FR-2026-05-12/pdf/2026-09382.pdf)
- [2026 CCDF Final Rule — ACF Office of Child Care](https://acf.gov/occ/law-regulation/2026-ccdf-final-rule)
- [Overview of 2026 Final CCDF Regulation — Child Care Aware](https://info.childcareaware.org/hubfs/2026-Final-CCDF-Regulation.pdf)
- [2024 CCDF Rule New Payment Practices Requirements — TCC Solutions](https://tccsolutions.com/news-insights/2024-ccdf-rule-new-payment-practices-requirements-implementation-considerations-for-state-policymakers/)
