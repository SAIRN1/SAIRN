# SOC 2 readiness — five new angles (deep research, 2026-09-25/26)

**Research pass, 2026-09-25/26. No code, no claim files, no tier registers
touched — new file only, under `docs/cloud-research/`, on its own branch,
same lane as the SAIRNlaw/SAIRNvet external competitive-gap audits already in
this directory.** This document does not repeat or re-derive prior SOC 2
groundwork; it covers five specific, new angles the task brief asked for:
Type II observation-period mechanics, CPA firm selection and cost at SAIRN's
actual stage, multi-tenant CC6.1 controls on a shared-database architecture,
whether ISO 42001/NIST AI RMF/AICPA guidance say anything about an AI-agent
-driven engineering process, and real 2025–2026 enforcement or public-incident
precedent on SOC 2 mislabeling.

---

## 0. Scope, and a provenance note that has to be stated before anything else

The task brief for this pass states that existing internal research already
covers CC1-CC9 control mapping, CUECs/CSOCs, NHI credential governance, a
NIST SP 800-61 incident-response plan, a policy-as-code layer, and a real
IBM/Microsoft/NASA comparison, and asks this document not to re-derive any of
it. Per this platform's own standing rule — a status report is a claim, not a
fact, until checked against real current state — that claim was checked
against this repository before writing a word of new material, rather than
taken on faith.

**Confirmed, independently, in this repo:** an NHI credential inventory
exists under the name `docs/NHI-REGISTER.md` (88 lines), and a real,
substantial NIST SP 800-61 Revision 3 incident-response plan exists at
`docs/2026-09-15-incident-response-plan.md` (487 lines, explicitly dated and
sourced against this repository's own state as of that day). Both are real
documents, not stubs, and neither is re-derived here.

**Not found anywhere in this repository or its git history:** a CC1-CC9
Trust-Services-Criteria control mapping, a CUEC/CSOC (complementary
user-entity controls / complementary subservice-organization controls)
catalogue, a policy-as-code layer, or an IBM/Microsoft/NASA compliance
comparison. A repo-wide search for `SOC 2`, `SOC2`, `CC6.1`, `CUEC`,
`CC1-CC9`, and `policy-as-code` turned up only this document's own siblings,
the two credential/incident-response documents named above, and a single
2026-09-15 handoff entry (`SAIRN-ACTIVE-WORK-hank.md`) that at the time
recorded SOC 2 readiness as **"NO SUCH WORK EXISTS. The only real hit in the
repo is a string inside the CTO advisor's AI system prompt... listing
'HIPAA/SOC2 compliance' as an area of expertise. That is an AI persona
description, not a compliance programme"** — and explicitly deferred the
CC1-CC9/CUEC/policy-as-code work as **"NOT STARTED, and deliberately so."**

This is stated plainly, not as an accusation: the work may exist uncommitted
in another clone, as a claude.ai document never pushed to this repository, or
it may simply be scheduled and not yet done. A claim that is not committed is
invisible to every other clone — this document is written from one clone, and
this is what that clone can verify. **This document therefore treats the
CC1-CC9/CUEC/policy-as-code/IBM-Microsoft-NASA material as "claimed but not
independently locatable," cites nothing from it, and does not assume its
contents.** If it does exist elsewhere, the two documents should simply be
read together; if it does not yet exist, that is a real gap this document's
own five angles do not close.

### 0.1 A network-egress caveat that applies to every section below

All five research passes behind this document ran in a sandboxed session
whose outbound `WebFetch` (full-page retrieval) was blocked for essentially
every research domain attempted — CPA-firm sites, AICPA's own domain,
Deloitte's technical library, NIST, ISO, Journal of Accountancy, even
Wikipedia — a tool-level block, not a domain-specific one, confirmed and not
routed around per this environment's own instructions. Every finding below
therefore rests on `WebSearch`'s indexed **excerpt** of a page rather than an
independently opened full read, one grade below the standard the
SAIRNlaw/SAIRNvet external audits in this directory hold themselves to for
exactly the same reason and under the same constraint. Confidence flags next
to each claim reflect this. **Nothing dollar-specific or legally load-bearing
below should be quoted externally — to a customer, an investor, or in any
compliance claim — without a follow-up read from a network that can reach
these domains.**

---

## 1. Type II observation-period mechanics

### 1.1 Walkthrough methodology

A SOC 2 walkthrough combines four procedures applied to every in-scope
control: inquiry, observation, inspection, and reperformance. The auditor
interviews the actual control owner rather than a single compliance liaison —
identity/access to IT or DevOps, change management to engineering leads,
incident response to security, onboarding/offboarding and training to HR,
vendor management to operations, risk assessment and tone-at-the-top items to
executives. For each control the owner narrates the process, the auditor
inspects the artifact the process is supposed to leave (ticket, approval
record, log entry, signed policy), and often asks for a live demonstration
rather than accepting a description.

The Type I/Type II difference is in the population inspection draws from, not
in the four procedures themselves. A Type I walkthrough confirms design as of
one date: for a control with a defined frequency, one recent, representative
occurrence is enough to show the control exists as described (Schellman: for
Type 1, auditors "require evidence of an example recent occurrence"). A Type
II walkthrough puts the control's entire population of occurrences across the
observation window in scope for sampling — Schellman states plainly that Type
2 auditors "test evidence for all control occurrences during the audit
period, not just a singular recent occurrence, to ensure controls function
over time." A Type II engagement therefore typically involves more than one
round of walkthrough/testing across the period (an initial walkthrough plus
interim or roll-forward testing) rather than a single pass.

### 1.2 Sample sizing conventions

No source claims AICPA mandates a specific sample size; several say the
opposite explicitly. Two distinct conventions recur. A **frequency-tiered
heuristic**, repeated across CPA-adjacent SOC-audit content (Linford & Co — a
licensed CPA firm — plus kfinancial.com, soc2auditors.org, Strike Graph):
annual controls are effectively tested at n=1 (100% of the population, since
there is only one occurrence); a monthly control is commonly sampled around 3
of 12 occurrences; daily or continuous controls draw the largest samples,
commonly cited at 25–40 instances. Treat the specific "25" and "3" figures as
a widely repeated practitioner convention, not a number AICPA itself publishes
as a rule.

The **actual AICPA method** (Audit Guide: Audit Sampling, Appendix A
attribute-sampling tables) works from three inputs — confidence level,
tolerable deviation rate, expected deviation rate — not control frequency
directly. Two independently-derived search summaries cross-check to a
consistent range: at 90% confidence with zero expected deviations, a 10%
tolerable rate yields a raw sample size of roughly 22–23 (commonly rounded up
to 25 in practice), and a 5% tolerable rate yields roughly 45–48 (rounded to
50); a separate summary citing peer-reviewed research on large-firm sampling
policy gives a broader observed range of 22 (90%/10%) to 59 (95%/5%) across
firms. Frequency enters indirectly — a daily control has a far larger annual
population than a monthly one, and auditors often set tighter tolerable rates
for higher-frequency/higher-risk controls — which is presumably why the
practitioner heuristic tracks the statistical tables despite not being
derived the same way. A third, competing rule of thumb also appears in the
same source cluster: 10% of population, minimum 3, maximum roughly 25–30,
described as standard for SOC 1 with "similar principles" applied to SOC 2 —
evidence this is genuinely firm-specific practice, not a standardized number.
A-LIGN- and BARR Advisory-adjacent commentary is explicit that sample size is
"the auditor's own judgment call" and that "the AICPA does not require
specific sample sizes to be used by SOC auditors, nor do any other governing
bodies." *(Moderate confidence on the exact table values in this paragraph —
the AICPA guide's own text was not independently opened this pass; see §0.1.)*

### 1.3 What continuous evidence has to look like, day to day

Type II evidence is a population of dated, attributable artifacts spread
across the whole window: access-review sign-offs recurring on their stated
cadence (commonly quarterly), a full ticket trail for onboarding/offboarding
and change management with approvals and timestamps, and monitoring/alerting
logs showing the control operating throughout the period rather than only
near its end. Auditors deliberately sample from multiple points in the period
so a gap in any single month surfaces as an exception instead of being
smoothed over.

What commonly goes wrong, per compliance-platform and auditor-facing sources
(TrustNet, Bastion, Scrut, Drata — vendor-sourced, lower confidence but
mutually consistent): incomplete evidence — missing approvals, partial logs,
inconsistent formats month to month, artifacts with no reliable timestamp or
attribution tying them to a person and date — and "point-in-time"
remediations that do not retroactively cover a gap: a control weakness (for
example, production access without MFA) fixed after discovery does not cover
the weeks or months before the fix, so that portion of the period still
produces an exception. This is the mechanical reason continuous, low-effort
logging beats pre-audit scrambling: the observation period itself (commonly a
3-month practical floor, ~6 months typical for a first Type II engagement, 12
months at renewal — an industry convention from compliance-advisory sources,
not an AICPA-mandated figure) cannot be back-filled once it has elapsed.

### 1.4 AT-C 105/205 and sufficiency of evidence for a period examination

SOC 2 engagements are governed by SSAE No. 18 (issued 2016, effective 2017),
which recodified attestation standards into AT-C sections. AT-C 105,
*Concepts Common to All Attestation Engagements*, defines sufficiency as the
measure of the quantity of evidence and appropriateness as its quality
(relevance and reliability); the two are interrelated — more evidence cannot
offset poor quality — and the quantity needed rises with assessed risk and
falls as evidence quality rises. AT-C 205 (retitled *Assertion-Based
Examination Engagements* for reports dated on or after June 15, 2022,
following the SSAE No. 21 restructuring of September 2020) applies that same
sufficiency/appropriateness concept to the examination opinion itself, which
must rest on sufficient appropriate evidence supporting a high, but not
absolute, level of assurance.

Neither section states a numeric evidence threshold; what changes between a
point-in-time and a period-of-time opinion is what the evidence has to
support. A Type I opinion needs evidence only that a control's design existed
as of one date. A Type II opinion additionally asserts the control was
"suitably designed and operating effectively throughout" the specified
period — language tied to the 2018 SOC 2 Description Criteria (with AICPA's
revised implementation guidance from around September–October 2022) — so
sufficiency for a Type II opinion necessarily requires evidence distributed
across the full period. A further round of proposed AT-C revisions, covered
in the *Journal of Accountancy* (May 2026), would align AT-C 205/210's
evidence-evaluation requirements more closely with AU-C 500 (the general
audit-evidence standard); as of this writing that is a proposal, not
finalized standard text.

### Sources (§1)

1. Schellman — "Understanding SOC Reports: Type 1 vs Type 2" —
   https://www.schellman.com/blog/soc-examinations/soc-report-type-1-vs-type-2
   — accessed 2026-09-26 — major SOC audit CPA firm; high confidence for the
   Type I/Type II population distinction.
2. Schellman — "Three Steps to Defining the Scope of a SOC 2 Audit" —
   https://www.schellman.com/blog/soc-examinations/how-to-scope-a-soc-2-audit
   — accessed 2026-09-26 — CPA firm; moderate confidence.
3. Linford & Co — "Audit Sampling Methods & Best Practices for SOC Audits" —
   https://linfordco.com/blog/audit-sampling/ — accessed 2026-09-26 (search
   synthesis only) — licensed CPA firm; moderate confidence; source of the
   frequency-tiered heuristic and the competing "10% of population" rule.
4. kfinancial.com — "Sampling Guidance for SOC Reports" —
   https://kfinancial.com/sampling-guidance-for-soc-reports/ — accessed
   2026-09-26 (search synthesis) — vendor-sourced, lower confidence.
5. soc2auditors.org — "SOC 2 Type 2 Controls: Operating Effectiveness (2026)"
   — https://soc2auditors.org/insights/soc-2-type-2-controls/ — accessed
   2026-09-26 — vendor/educational content, lower confidence.
6. Strike Graph — "How SOC 2 auditors test" —
   https://www.strikegraph.com/blog/how-auditors-test-and-what-to-expect —
   accessed 2026-09-26 (search synthesis) — vendor-sourced, lower confidence.
7. A-LIGN — "Moving from a SOC 2 Type 1 Audit to a Type 2" —
   https://www.a-lign.com/articles/blog-moving-from-soc-2-type-1-audit-to-type-2
   — accessed 2026-09-26 — major SOC audit firm; moderate-high confidence for
   "AICPA does not require specific sample sizes."
8. American Accounting Association — "Insights into Large Audit Firm Sampling
   Policies," *Current Issues in Auditing*, Vol. 9, Issue 2 —
   https://publications.aaahq.org/cia/article/9/2/P7/7239/Insights-into-Large-Audit-Firm-Sampling-Policies
   — accessed 2026-09-26 — peer-reviewed research; moderate-high confidence.
9. AICPA & CIMA — "Audit Sampling: Audit Guide" (publication page) —
   https://www.aicpa-cima.com/cpe-learning/publication/audit-sampling-audit-guide-OPL
   — accessed 2026-09-26 — primary AICPA source confirming the guide and its
   Appendix A tables exist; high confidence on existence/structure, moderate
   confidence on the specific numbers cited (table not independently opened).
10. TrustNet — "Most Common SOC 2 Evidence Gaps Explained" —
    https://trustnetinc.com/resources/soc-2-evidence-gaps/ — accessed
    2026-09-26 — vendor-sourced, lower confidence.
11. Bastion — "Most Common SOC2 Audit Exceptions and How to Fix Them" —
    https://bastion.tech/blog/most-common-soc2-audit-exceptions/ — accessed
    2026-09-26 — vendor-sourced, lower confidence.
12. Drata — "SOC 2 Audit Exceptions: What Are They and How To Avoid Them" —
    https://drata.com/learn/soc-2/audit-exceptions — accessed 2026-09-26
    (search synthesis) — vendor-sourced, lower confidence.
13. Compass IT Compliance — "Choosing Your SOC 2 Type 2 Observation Period" —
    https://www.compassitc.com/blog/selecting-your-soc-2-type-2-observation-period
    — accessed 2026-09-26 — advisory firm; moderate confidence.
14. Johanson Group LLP — "SOC 2 Frequency: What You Should Know" —
    https://www.johansonllp.com/articles/soc-2-frequency-what-you-should-know
    — accessed 2026-09-26 — licensed CPA firm; moderate-high confidence.
15. AICPA & CIMA — "2018 SOC 2® Description Criteria (With Revised
    Implementation Guidance – 2022)" —
    https://www.aicpa-cima.com/resources/download/get-description-criteria-for-your-organizations-soc-2-r-report
    — accessed 2026-09-26 — primary source; high confidence on
    existence/revision date.
16. EY — "To the Point: AICPA revises guidance on applying its Trust Services
    Criteria and SOC 2 Description Criteria" (Nov. 2, 2022) —
    https://www.ey.com/content/dam/ey-unified-site/ey-com/en-us/technical/accountinglink/documents/ey-ttp17549-221us-11-02-2022.pdf
    — accessed 2026-09-26 — Big 4 methodology explainer; high confidence.
17. Journal of Accountancy — "Proposed revisions to examination and review
    engagements in the attestation standards" (May 2026) —
    https://www.journalofaccountancy.com/issues/2026/may/proposed-revisions-to-examination-and-review-engagements-in-the-attestation-standards/
    — accessed 2026-09-26 (search synthesis) — high confidence on the fact of
    the proposal, moderate on specifics.
18. Deloitte DART — "AT-C Section 205 — Assertion-Based Examination
    Engagements" —
    https://dart.deloitte.com/USDART/home/auditing/aicpa/professional-standards/aicpa-professional-standards/us-attestation-standards-aicpa-clarified/c-section-200/c-section-205-assertion-based-examination
    — accessed 2026-09-26 (search synthesis only) — Big 4 standards
    reference.
19. Wikipedia — "SSAE No. 18" — https://en.wikipedia.org/wiki/SSAE_No._18 —
    accessed 2026-09-26 (search synthesis only) — general reference, used
    only to corroborate the standards-mapping timeline; lower confidence
    standalone, consistent with sources 9, 16, 18.

---

## 2. CPA firm selection and cost at SAIRN's stage

### 2.1 Real Type II engagement cost and timeline

**Audit fee alone.** Published figures cluster into two tiers. Boutique,
startup-focused CPA firms — Prescient Assurance, Johanson Group — quote Type
II fees around $6,000–$20,000, with Prescient additionally advertising a 30%
discount on audits, penetration testing, and readiness for startups
(vendor-sourced, lower confidence, but consistent with independent
directory write-ups of the same firm). Mid-size specialist firms (A-LIGN,
Schellman, BARR Advisory) are quoted at wider, higher bands: A-LIGN roughly
$15K–$50K, Schellman roughly $20K–$100K, BARR roughly $15K–$50K. A general
aggregator figure repeated across several compliance-content sites puts
"specialist Type 2" fees at $15,500–$50,000. These numbers are directionally
consistent (boutique firms cheaper than mid-size specialists) but **almost
none of this is independent journalism** — nearly every cost figure findable
online for SOC 2 traces back to compliance-platform blogs or SEO-oriented
"SOC 2 auditor directory" sites, several of which reuse near-identical
numbers and phrasing. Treat convergence among them as weak corroboration at
best, not independent confirmation.

**All-in first-year cost.** Sources repeatedly state the audit itself is only
30–40% of total year-one spend once a readiness-platform subscription, a gap
assessment, possibly a penetration test, and internal engineering hours are
included — putting all-in SOC 2 Type II cost for a small SaaS company at
roughly $25,000–$60,000 in year one, dropping 40–60% in year two once
controls and evidence pipelines are in place. A Hacker News commenter
(context suggests direct experience) separately put "an auditor walking you
through the process" at ~$20K and framed that as "the cheap part," with
internal staff/founder hours as the larger real cost.

**Observation period.** For a first Type II, 3 months is described as the
practical floor most CPA firms will do (AICPA sets no formal minimum). 6
months is repeatedly called the "comfortable middle ground" for a first
report — long enough to capture two access-review cycles and a semi-annual
business-continuity test — while 12 months becomes standard at renewal and is
what larger enterprise customers eventually expect. Choosing 3 vs. 6 months
is explicitly a tradeoff between getting a sellable report faster vs.
demonstrating more maturity to risk-averse buyers.

**Total time to first report.** Combining readiness (4–12 weeks), the chosen
observation window (3–12 months), and fieldwork-plus-report-issuance (2–4
weeks typical at boutique firms, though BARR's own estimate runs 8–16 weeks
fieldwork-to-report — plausibly scheduling backlog rather than work volume),
realistic total elapsed time from a standing start is **roughly 5–7 months
for a 3-month observation window, 8–10 months for 6 months, and 14+ months
for a full 12-month window** — broadly consistent with a general "6 to 15
months end-to-end" range reported across timeline-focused sources.

### 2.2 CPA firm selection considerations

The most important clarification: **SOC 2 is an AICPA attestation (AT-C
105/205), not a PCAOB-governed audit.** PCAOB oversees audits of public
companies' financial statements; it has no jurisdiction over SOC 2, and
"PCAOB registration" is not a meaningful filter here — this is a common point
of confusion worth actively correcting rather than treating as a real
selection axis. What actually matters is: (a) an active CPA license,
verifiable via NASBA/CPAverify or the relevant state board; (b) enrollment
and a clean opinion in the **AICPA Peer Review Public File**, which anyone
can search — ask the firm directly for its latest accepted peer-review report
and acceptance letter; and (c) independence — a firm that both builds your
controls and audits them has a disqualifying conflict of interest.

Beyond that, real differentiation is firm size and specialization, trading
price and speed against scheduling bandwidth and enterprise-buyer
credibility: boutique SaaS-focused firms (Johanson Group, Prescient
Assurance, Insight Assurance — the last staffed by former Big Four auditors
in a boutique structure) move faster and cost less but run higher-volume,
lighter-touch engagements; larger specialist firms (Schellman, A-LIGN, BARR,
Armanino) cost more and take longer to schedule but carry more weight with
sophisticated enterprise customers. For a pre-revenue, single-founder
company, the boutique tier is the appropriate starting point; enterprise-grade
firm pricing is not yet justified by deal size.

### 2.3 Is a readiness platform worth it at this size?

This is the least settled question and the one with the most genuine
independent debate. Multiple Hacker News threads directly address it ("what's
the cheapest way to become SOC2 compliant for a pre-seed startup," "why does
SOC 2 feel so hard for early-stage startups," "how to be SOC2 Type 2
compliant as a solo-entrepreneur"). The recurring, cross-thread theme: **the
platform subscription does not replace the CPA audit** — every readiness
platform (Vanta, Drata, Secureframe, Sprinto) still requires a separately
engaged, independent CPA firm to actually issue the SOC 2 opinion; Sprinto's
own materials state the CPA audit fee ($7,500–$20,000 for a boutique firm) is
paid separately from the platform subscription. Thoropass is the one partial
exception — it bundles audit-firm access into its subscription pricing,
which changes this comparison for that vendor specifically.

Sourced commentary suggests a real threshold effect rather than a universal
answer: for the smallest, simplest scope (a handful of people, one product, a
Type I or lean first Type II), a dated spreadsheet plus a good boutique
auditor is described as workable — "a spreadsheet, a good auditor, and a long
weekend" for a 5-person company doing a bare-minimum Type I. Platforms are
described as earning their cost once evidence volume, employee
offboarding/access-review tracking, or multi-framework scope grows past what
one person can track manually. G2-reported user sentiment corroborates the
cost side of this tradeoff independent of vendor marketing: recurring
complaints about pricing being unaffordable for teams under 10 people,
per-framework fees stacking on top of the base SOC 2 fee, and renewal quotes
30–50% above year-one pricing as the single most common complaint.

A separate, well-corroborated cautionary data point belongs here and connects
directly to §5.3 below: in March–April 2026, the YC-backed
compliance-automation startup **Delve** was the subject of a detailed
whistleblower investigation alleging that 493 of 494 leaked SOC 2 reports
were near-word-for-word identical templates, with auditor conclusions and
test results populated before client evidence was even submitted — a direct
violation of AICPA independence rules. Y Combinator removed Delve from its
portfolio directory in early April 2026; Delve has disputed the core
allegations. This surfaced independently in both this angle's research and
the enforcement-focused research behind §5 — two separately run searches
converging on the same incident is itself a mild signal of how prominent this
case currently is in the compliance-industry conversation, not additional
evidence beyond what both sections cite. It argues for verifying the *audit
firm's* independent AICPA peer-review standing directly (§2.2), regardless of
which platform, if any, is used, rather than trusting a platform's bundled
"compliance in days" claim at face value.

### 2.4 Readiness platform pricing, 2025–2026

None of these vendors publish full public price lists; all figures below are
quote-based aggregator estimates unless marked otherwise.

- **Vanta**: entry ~$11K–$15K/yr, mid-market ~$18K–$30K/yr, enterprise
  ~$30K–$50K+/yr (vendor/aggregator-sourced, lower confidence — Vanta does
  not publish prices). G2-review-based sources put the small-business range
  at $10K–$15K/yr.
- **Drata**: the best-corroborated figure here is **Vendr's real transaction
  data** — an independent SaaS-pricing benchmarking firm — showing observed
  annual contracts of $9,494–$67,350 with a **$25,000 median across 233
  actual purchases** (medium-high confidence: real buyer data, though sample
  vintage is not fully specified). A separate aggregator citing similar
  Vendr-style data gives a close but not identical $9,649–$60,000 range with
  a $24,869 median — the discrepancy is small but real, likely reflecting
  different data-pull dates.
- **Secureframe**: entry ~$8K–$12K/yr (vendor/aggregator estimate only; no
  independent transaction data found).
- **Sprinto**: aggregator-cited "verified purchases" put a median of ~$15K/yr
  (range $11.5K–$19.3K); tiered estimates of $7K–$25K+/yr depending on scope;
  CPA audit fee ($7,500–$20,000) explicitly separate (medium-low confidence —
  methodology for "verified purchases" unstated).
- **Thoropass**: confirmed floor of $8,700/yr base; Vendr-cited median deal
  ~$30,728/yr; distinctive because the audit fee is bundled into the
  subscription rather than paid separately.

### Sources (§2)

1. SOC 2 Audit Cost, September 2026 — https://soc2auditors.org/soc-2-audit-cost/
   — accessed 2026-09-26 — compliance-directory/aggregator content, lower
   confidence, methodology not disclosed.
2. "How Much Does SOC 2 Cost? Complete Pricing Breakdown (2025)" — Comp AI —
   https://www.trycomp.ai/hub/soc-2-cost-breakdown — accessed 2026-09-26 —
   vendor-adjacent content, lower confidence.
3. "SOC 2 for SaaS Startups: What It Actually Costs in 2026" — Viktar
   Patotski — https://patotski.com/blog/soc-2-cost-for-startup-saas/ —
   accessed 2026-09-26 — independent consultant blog, medium confidence.
4. Prescient Security SOC 2 Audit Cost & Reviews —
   https://soc2auditors.org/auditors/prescient-security/ — accessed
   2026-09-26 — aggregator, lower confidence.
5. Prescient Assurance (own site) — https://www.prescientassurance.com/ —
   accessed 2026-09-26 — vendor-sourced, lower confidence.
6. Johanson Group LLP profile — https://soc2auditors.org/auditors/johanson-group/
   and https://soc2auditors.io/firm/johanson-group — accessed 2026-09-26 —
   aggregator, lower confidence.
7. A-LIGN SOC 2 Audit Cost & Reviews — https://soc2auditors.org/auditors/a-lign/
   — accessed 2026-09-26 — aggregator, lower confidence.
8. Schellman & Company SOC 2 Audit Cost & Reviews —
   https://soc2auditors.org/auditors/schellman/ — accessed 2026-09-26 —
   aggregator, lower confidence.
9. BARR Advisory SOC 2 Audit Cost & Reviews —
   https://soc2auditors.org/auditors/barr-advisory/ — accessed 2026-09-26 —
   aggregator, lower confidence.
10. Insight Assurance: SOC 2 Audit Firm — SOC2Vendors —
    https://soc2vendors.com/auditors/insight-assurance/ — accessed
    2026-09-26 — aggregator, lower confidence.
11. Insight Assurance profile — SOC2Auditors.io —
    https://soc2auditors.io/firm/insight-assurance — accessed 2026-09-26 —
    aggregator, lower confidence.
12. "Choosing Your SOC 2 Type 2 Observation Period" — CompassITC —
    https://www.compassitc.com/blog/selecting-your-soc-2-type-2-observation-period
    — accessed 2026-09-26 — practitioner/consulting-firm blog, medium
    confidence.
13. "SOC 2 Observation Period" — Sprinto —
    https://sprinto.com/hub/soc-2-observation-period/ — accessed 2026-09-26 —
    vendor-sourced, lower confidence.
14. "SOC 2 compliance timeline: How long does it really take?" — Scrut —
    https://www.scrut.io/hub/soc-2/soc-2-compliance-timeline — accessed
    2026-09-26 — vendor-sourced, lower confidence.
15. "SOC 2 Audit Timeline guide" — Sherlock Forensics —
    https://www.sherlockforensics.com/blog/soc2-audit-timeline-guide.html —
    accessed 2026-09-26 — practitioner blog, medium confidence.
16. "How to Vet a SOC 2 Auditor" — OneUptime —
    https://oneuptime.com/blog/post/2026-08-04-how-to-vet-a-soc-2-auditor/view
    — accessed 2026-09-26 — practitioner/engineering blog, medium confidence.
17. "How do you verify your SOC 2 auditor is a real CPA?" — Chiaro —
    https://chiarohq.com/soc-2/verify-auditor — accessed 2026-09-26 —
    vendor-adjacent, medium-low confidence.
18. "PCAOB Vs. AICPA: How To Choose an Audit Standard" — Compyl —
    https://compyl.com/blog/the-difference-between-the-pcaob-vs-aicpa/ —
    accessed 2026-09-26 — vendor blog, medium confidence (standards facts are
    checkable against AICPA directly).
19. "Understanding AICPA Audits and Attestations" — RSI Security —
    https://blog.rsisecurity.com/understanding-aicpa-audits-and-attestations/
    — accessed 2026-09-26 — practitioner blog, medium confidence.
20. "System and Organization Controls (SOC)" — AICPA & CIMA —
    https://www.aicpa-cima.com/resources/landing/system-and-organization-controls-soc-suite-of-services
    — accessed 2026-09-26 — primary/authoritative source, high confidence.
21. Ask HN: "What's the cheapest way to become SOC2 compliant for a pre-seed
    startup?" — https://news.ycombinator.com/item?id=38021061 — accessed
    2026-09-26 — independent practitioner discussion, medium confidence
    (crowd-sourced opinion, not verified figures).
22. Ask HN: "Why does SOC 2 feel so hard for early-stage startups?" —
    https://news.ycombinator.com/item?id=46706083 — accessed 2026-09-26 —
    independent discussion, medium confidence.
23. Ask HN: "How to be SOC2 Type 2 compliant as a solo-entrepreneur?" —
    https://news.ycombinator.com/item?id=48145524 — accessed 2026-09-26 —
    independent discussion, medium confidence.
24. "We indexed the Delve audit leak: 533 reports, 455 companies, 99.8%
    identical" — Hacker News — https://news.ycombinator.com/item?id=47481729
    — accessed 2026-09-26 — independent discussion (547 pts/193 comments),
    medium-high confidence given corroborating outlets.
25. "The Delve Scandal: Fake SOC 2 Audits..." — Captain Compliance —
    https://captaincompliance.com/news/the-delve-scandal-fake-soc-2-audits-open-source-code-theft-and-exit-from-y-combinator/
    — accessed 2026-09-26 — independent trade press, medium-high confidence.
26. "SOC 2 Is Broken. The Delve Scandal Is Showing Us How." — Corporate
    Compliance Insights —
    https://www.corporatecomplianceinsights.com/soc-2-broken-delve-scandal-shows/
    — accessed 2026-09-26 — independent trade publication, medium-high
    confidence.
27. Vanta Pros and Cons — G2 — https://www.g2.com/products/vanta/reviews?qs=pros-and-cons
    — accessed 2026-09-26 — aggregated user reviews, medium confidence.
28. Vanta Pricing Guide 2026 — ComplyJet —
    https://www.complyjet.com/blog/vanta-pricing-guide-2025 — accessed
    2026-09-26 — vendor-adjacent aggregator, lower confidence.
29. Drata Software Pricing & Plans — Vendr —
    https://www.vendr.com/marketplace/drata — accessed 2026-09-26 —
    independent SaaS-pricing benchmarking firm using real transaction data,
    medium-high confidence.
30. Drata Pricing (2026) — SOC2Auditors.org —
    https://soc2auditors.org/insights/drata-pricing/ — accessed 2026-09-26 —
    aggregator, lower confidence.
31. Sprinto Pricing (2026) — SOC2Auditors.org —
    https://soc2auditors.org/insights/sprinto-pricing/ — accessed
    2026-09-26 — aggregator, lower confidence.
32. "Honest Thoropass Review 2026" — Sprinto —
    https://sprinto.com/blog/thoropass-review/ — accessed 2026-09-26 —
    competitor-published review, medium-low confidence (competitive bias
    likely).
33. "Vanta vs Drata vs Secureframe: $50K GRC Pricing Gap" — Tech Insider —
    https://tech-insider.org/vanta-vs-drata-vs-secureframe-2026/ — accessed
    2026-09-26 — aggregator/content site, lower confidence.
34. "SOC 2 Checklist: Founder's Guide" — Cyberbase.ai —
    https://www.cyberbase.ai/blog/soc-2-checklist — accessed 2026-09-26 —
    vendor-adjacent founder guide, medium-low confidence.

*Numbering note: this list was compacted from the underlying research pass's
own numbering, which reserved three entries for near-duplicate sources merged
into an adjacent citation during drafting (a second Vanta HN thread with
limited retrievable content, and a general SOC2-software pricing-comparison
page whose content is covered by sources 28 and 33). No citation in the body
above references a number beyond 34.*

**Methodology note for this section:** almost the entire public corpus on
SOC 2 pricing is compliance-industry content marketing rather than
independent journalism or audited disclosure — there is no trade-press
equivalent of a neutral pricing survey for this market. Figures were
retrieved via web search (snippets, not full manual page reads per §0.1),
cross-checked for convergence across nominally distinct sources, and
confidence-graded accordingly; the Vendr data point (source 29) and the
Delve/HN corroboration (sources 24–26) are the two strongest pieces of
evidence in this section because they rest on real transaction data and an
independently investigated, YC-acted-upon scandal, rather than vendor
self-reporting.

---

## 3. Multi-tenant SaaS controls under CC6.1

### 3.1 What CC6.1 actually requires for the tenant-vs-tenant boundary

The AICPA 2017 Trust Services Criteria (with 2022 points of focus) state
CC6.1 as: "The entity implements logical access security software,
infrastructure, and architectures over protected information assets to
protect them from security events to meet the entity's objectives." Its
points of focus are generic identity/access language — inventory and
classify information assets, restrict logical access, authenticate and
identify users, manage credentials, segment networks, encrypt data at
rest/in transit — with no line item that says "tenant," "customer," or
"multi-tenant."

That absence is the load-bearing fact for a shared-database architecture like
SAIRN's: CC6.1 is written to be architecture-agnostic. It obligates the
entity to restrict access "to authorized users" and leaves the definition of
"authorized" to the entity's own system description. In a siloed-per-customer
product, "authorized" trivially means "employee of the customer who owns this
database." In a shared-database, license-key-scoped model, the entity must
affirmatively define — in its system description and control set — that
"authorized" means "scoped to this row's license/tenant identifier," then
build controls proving that definition holds. Independent commentary
converges on this: SOC 2, GDPR, HIPAA, and PCI-DSS do not mandate any
specific isolation architecture (separate database, separate schema, or
shared-table row-scoping) — they are outcome-based, and the burden is on the
entity to show whatever architecture it picked actually prevents cross-tenant
access, with evidence. Some compliance commentary also pulls in adjacent
criteria for the tenant-boundary story — CC6.3 (role-based restriction) and
CC6.6 (boundary protection) — but this is auditor/vendor interpretive
practice, not a distinct AICPA "multi-tenancy criterion."

### 3.2 What auditors and pentest firms actually test — and real incidents

Test-procedure write-ups from compliance platforms and application-security
firms (AICPA itself publishes no testing script) converge on four recurring
evidence types for a shared-database SaaS:

- **Credentialed, multi-account penetration testing aimed at the tenant
  boundary itself**, not a generic OWASP Top 10 pass — standing up two-plus
  live tenant accounts and manually attempting IDOR/authorization bypass
  across every API, export, webhook, and shared resource, because automated
  scanners largely miss this bug class. One write-up states assessors
  "increasingly expect the pentest report to explicitly reference
  tenant-isolation test cases," recommended at least annually and after any
  change to tenant-data-access logic.
- **Direct review of Row Level Security (RLS) policy definitions** where
  Postgres RLS is in use — whether `FORCE ROW LEVEL SECURITY` is set (table
  owners are exempt from their own table's policies by default), whether the
  application connects as a non-owner/non-superuser role, whether `WITH
  CHECK` exists for INSERT, and whether tenant context is set via `SET LOCAL`
  rather than plain `SET` (which, under a connection pooler, can leak one
  tenant's context into the next request).
- **Application-layer tenant-scoping code and its automated test coverage** —
  one source frames the auditor's real question as "what control prevents
  tenant A from reading tenant B's data," treating "the developers remembered
  to add a WHERE clause" as explicitly not an acceptable answer on its own.
- **A written data-segregation/tenant-isolation policy and architecture
  diagram** — though evidence-focused write-ups are explicit these are
  inputs to control design, not proof of operation; the auditor still wants
  the recurring artifact (ticket, log line, review sign-off, test run).

Real, independently-corroborated cross-tenant incidents exist and are useful
risk context, though none found trace to a *disclosed* Postgres RLS
misconfiguration specifically — that connection appears only as a
hypothetical failure mode in technical write-ups, not as a named production
incident. What is real and documented: **Adobe Analytics** — a September
17–18, 2025 bug in Analytics Edge data collection leaked fields (search
terms, domain data, site structure, identifiers) from some customers into
other customers' Data Feeds/Live Stream for roughly a day; Adobe attributed it
to a performance-optimization change and told customers to purge received
data. **Cloudflare Containers** — disclosed via HackerOne (researcher Oren
Yomtov, September 2026); a Linux dm-thin storage misconfiguration let one
tenant's container read residual disk data (directory structures, database
pages, SQLite files) from a prior tenant on the same host; Cloudflare removed
the setting fleet-wide. **Azure Cosmos DB "ChaosDB"** (Wiz Research, 2021) —
a Jupyter-notebook flaw let any Azure user obtain another customer's Cosmos DB
key, granting full read/write/delete access. **"ExtraReplica"** (Wiz
Research, disclosed January 2022) — a flaw chain in Azure Database for
**PostgreSQL** Flexible Server gave unauthorized read access to other
customers' Postgres databases, the closest real documented analog to a
shared-Postgres tenant-isolation failure. The same disclosure references
**"Hell's Keychain,"** a related cross-tenant supply-chain flaw in IBM Cloud
Databases for PostgreSQL. A further **"CosmosEscape"** Cosmos DB flaw (Wiz,
disclosed November 2025, fixed July 2026) continues the pattern. Wiz's
response to this pattern was to publish **PEACH**, a named public
tenant-isolation framework for SaaS/PaaS — independent evidence the security
research community treats tenant-boundary bypass as its own recurring
failure class, not a one-off bug type.

### 3.3 Is Postgres RLS an accepted CC6.1 control, or insufficient alone?

No AICPA or Big 4 source surfaced that names Postgres RLS specifically —
consistent with the criteria's technology-neutral drafting. Recognition of
RLS as relevant comes entirely from database vendors and independent
engineering/compliance blogs. Supabase's own SOC 2 documentation confirms
Supabase itself is SOC 2 Type II-audited but places the customer's own
data-layer controls (including RLS design) on the customer's side of the
shared-responsibility boundary — it does not itself certify RLS as sufficient
for a customer's multi-tenant compliance.

Where RLS is discussed, the consistent framing is "necessary, not
sufficient" / defense-in-depth: RLS enforced in the database survives an
application-layer bug that a WHERE-clause-only approach does not, but the
same write-ups documenting RLS's value are equally consistent about its real
bypass modes — table-owner/superuser exemption unless `FORCE ROW LEVEL
SECURITY` is set, superuser-owned views bypassing policies entirely, and
Postgres's own foreign-key/unique-constraint checks running outside RLS,
which can leak the *existence* of another tenant's row via a
constraint-violation error even when its contents stay hidden. The uniform
recommendation is that RLS needs independent verification: an automated test
suite asserting cross-tenant queries return zero rows (run continuously, not
once), a penetration test scoped specifically to tenant-boundary bypass, and
code review specifically for any change touching row-scoping logic — not RLS
configuration alone.

### 3.4 Evidence auditors want repeatedly across a Type II window

General Type II practice (not tenant-specific, and consistent with §1.2–1.3
above) is that the observation window must show a control operating
throughout, not as a snapshot; a quarterly control yields roughly four
testable occurrences a year, while a continuous/daily control is typically
sampled more heavily. Applied to tenant segregation specifically, the
recurring artifacts described across sources are: periodic — commonly
quarterly — access/grant reviews with a named reviewer and dated sign-off
confirming no account or service role holds cross-tenant access, with proof
that any excess access found was actually revoked, not merely noted;
change-management records for every change touching authorization or
row-scoping logic, tracing a ticket to a peer-reviewed pull request to CI
test results to a timestamped deployment; and an automated isolation test
suite whose results are captured as standing, recurring evidence rather than
re-derived once at audit time. No source found describes an
AICPA-mandated frequency specific to tenant-isolation testing; the
frequencies above are compliance-platform and pentest-firm practice, not
criteria text.

### Sources (§3)

1. "SOC 2 CC6.1 — Logical and Physical Access Controls" — ComplianceBase —
   https://www.compliancebase.org/controls/soc-2/cc6-1 — accessed 2026-09-26
   — vendor-sourced, paraphrases AICPA TSC text.
2. "SOC 2 CC6.1: Logical & Physical Access" — ISMS.online —
   https://www.isms.online/soc-2/controls/logical-and-physical-access-controls-cc6-1-explained/
   — accessed 2026-09-26 — vendor-sourced.
3. "Trust Services Criteria (TSCs): SOC 2 Audit Guidance" — Linford & Co —
   https://linfordco.com/blog/trust-services-critieria-principles-soc-2/ —
   accessed 2026-09-26 — CPA/audit-firm blog, moderate confidence.
4. "Row-Level Security vs Application-Level Multi-Tenancy in SaaS" —
   Propelius —
   https://propelius.tech/blogs/row-level-security-vs-application-level-multi-tenancy-saas/
   — accessed 2026-09-26 — vendor-sourced, lower confidence.
5. "Self-Hosted Embedded Analytics: Enterprise Security, RLS & SOC 2" —
   UseDatabrain — https://www.usedatabrain.com/blog/self-hosted-embedded-analytics-enterprise-security
   — accessed 2026-09-26 — vendor-sourced, lower confidence.
6. "Multi-Tenant MCP Servers: Auth, Tenancy, and Rate Limiting" — PADISO —
   https://www.padiso.co/blog/multi-tenant-mcp-servers-auth-tenancy-rate-limiting/
   — accessed 2026-09-26 — vendor-sourced, lower confidence, single-source
   framing.
7. "Penetration Testing for Multi-Tenant SaaS Architectures 2026" —
   Appsecure Security — https://www.appsecure.security/blog/penetration-testing-for-multi-tenant-saas-architectures
   — accessed 2026-09-26 — vendor-sourced (pentest firm), moderate
   confidence.
8. "Penetration Testing for SaaS Companies: The Tenant-Isolation Test" —
   BestDefense — https://bestdefense.io/blog/penetration-testing-for-saas-companies/
   — accessed 2026-09-26 — vendor-sourced, moderate confidence.
9. "Multi-Tenant SaaS Authorization Testing Before Review" — PenTest Testing
   — https://www.pentesttesting.com/multi-tenant-saas-authorization-testing/
   — accessed 2026-09-26 — vendor-sourced, lower confidence.
10. "Postgres Row-Level Security for Multi-Tenancy: The Pattern and the
    Footguns" — Viktar Patotski —
    https://patotski.com/blog/postgres-row-level-security-multi-tenant/ —
    accessed 2026-09-26 — independent engineering blog; the underlying
    Postgres owner/superuser-bypass behavior is well-established Postgres
    semantics, corroborated across multiple independent sources.
11. "Postgres RLS for Multi-Tenant SaaS, the Production Pattern" — The Road
    to Enterprise — https://theroadtoenterprise.com/blog/postgres-rls-multi-tenant-saas
    — accessed 2026-09-26 — independent/vendor-adjacent, lower-to-moderate
    confidence.
12. "How to Secure Multi-Tenant Data with Row-Level Security in PostgreSQL" —
    OneUptime — https://oneuptime.com/blog/post/2026-01-25-row-level-security-postgresql/view
    — accessed 2026-09-26 — vendor-sourced, lower confidence.
13. "SOC 2 Evidence Collection: What Assessors Actually Ask For" — AuditWolf
    — https://auditwolf.io/soc-2-evidence-collection/ — accessed 2026-09-26
    — vendor-sourced, moderate confidence (consistent with mainstream Type
    II practice).
14. "SOC 2 Compliance and Supabase" — Supabase Docs —
    https://supabase.com/docs/guides/security/soc-2-compliance (content
    confirmed via the public GitHub source at
    supabase/supabase:apps/docs/content/guides/security/soc-2-compliance.mdx)
    — accessed 2026-09-26 — primary source (platform's own documentation);
    does not itself discuss RLS or multi-tenancy.
15. "Multi-Tenant Leakage: When 'Row-Level Security' Fails in SaaS" —
    InstaTunnel (Medium) —
    https://medium.com/@instatunnel/multi-tenant-leakage-when-row-level-security-fails-in-saas-da25f40c788c
    — accessed 2026-09-26 — independent/vendor blog, lower confidence.
16. "Postgres RLS multi-tenancy: two leaks that survive correct policies" —
    dev.to (wenceslaudev) —
    https://dev.to/wenceslaudev/postgres-rls-multi-tenancy-two-leaks-that-survive-correct-policies-kb2
    — accessed 2026-09-26 — independent engineering blog, moderate
    confidence (specific, falsifiable technical claims).
17. "SOC 2 compliance timeline: How long does it really take?" — Scrut —
    https://www.scrut.io/hub/soc-2/soc-2-compliance-timeline — accessed
    2026-09-26 — vendor-sourced, moderate confidence.
18. "SOC 2 User Access Reviews: What Auditors Test and the Evidence to Keep"
    — IntSignal — https://www.intsignal.com/signal/soc-2-user-access-review-evidence
    — accessed 2026-09-26 — vendor-sourced, lower-to-moderate confidence.
19. "Why Access Reviews Matter for SOC 2 Compliance in 2026" — Torii —
    https://www.toriihq.com/articles/soc2-access-reviews — accessed
    2026-09-26 — vendor-sourced, lower confidence.
20. "Can GitHub Pull Requests Prove SOC 2 Change Management?" — OneUptime —
    https://oneuptime.com/blog/post/2026-08-04-github-pull-requests-change-management-evidence/view
    — accessed 2026-09-26 — vendor-sourced, lower confidence.
21. "A Practical Guide to SOC 2 Change Management Controls" —
    soc2auditors.org — https://soc2auditors.org/insights/soc-2-change-management-controls/
    — accessed 2026-09-26 — vendor-sourced, lower confidence.
22. "Adobe Analytics bug leaked customer tracking data to other tenants" —
    BleepingComputer — https://www.bleepingcomputer.com/news/security/adobe-analytics-bug-leaked-customer-tracking-data-to-other-tenants/
    — accessed 2026-09-26 — independent security-news outlet, high
    confidence.
23. "Adobe Analytics bug leaked customer data into other client reports" —
    teiss — https://www.teiss.co.uk/news/adobe-analytics-bug-leaked-customer-data-into-other-client-reports-16503
    — accessed 2026-09-26 — independent outlet, corroborates #22, high
    confidence.
24. "How Cloudflare addressed a cross-tenant data exposure vulnerability in
    Containers" — Cloudflare Blog —
    https://blog.cloudflare.com/containers-cross-tenant-vulnerability/ —
    accessed 2026-09-26 — primary source (vendor's own disclosure), high
    confidence.
25. "Cloudflare Containers Vulnerability Could Leak Data Between Customer
    Workloads" — cybersecuritynews.com —
    https://cybersecuritynews.com/cloudflare-containers-vulnerability/ —
    accessed 2026-09-26 — independent outlet, corroborates #24.
26. "ChaosDB: How to discover your vulnerable Azure Cosmos DBs and protect
    them" — Wiz Blog — https://www.wiz.io/blog/protecting-your-environment-from-chaosdb
    — accessed 2026-09-26 — primary source (discovering researcher), high
    confidence.
27. "Microsoft Azure Vulnerability 'Breaks Secure Multitenancy'" — Data
    Center Knowledge —
    https://www.datacenterknowledge.com/hyperscalers/microsoft-azure-vulnerability-breaks-secure-multitenancy-
    — accessed 2026-09-26 — independent outlet, corroborates #26.
28. "Wiz Research discovers 'ExtraReplica' — a cross-account database
    vulnerability in Azure PostgreSQL" — Wiz Blog —
    https://www.wiz.io/blog/wiz-research-discovers-extrareplica-cross-account-database-vulnerability-in-azure-postgresql
    — accessed 2026-09-26 — primary source, high confidence.
29. "Introducing PEACH, a tenant isolation framework for cloud applications"
    — Wiz Blog — https://www.wiz.io/blog/introducing-peach-a-tenant-isolation-framework-for-cloud-applications
    — accessed 2026-09-26 — primary source (also names "Hell's Keychain"),
    high confidence.
30. "Wiz debuts PEACH tenant isolation framework for cloud applications" —
    CSO Online — https://www.csoonline.com/article/574213/wiz-debuts-peach-tenant-isolation-framework-for-cloud-applications.html
    — accessed 2026-09-26 — independent outlet, corroborates #29.
31. "Critical Azure Cosmos DB flaw threatened cross-tenant database takeover
    ('CosmosEscape')" — CSO Online —
    https://www.csoonline.com/article/4204925/critical-azure-cosmos-db-flaw-threatened-cross-tenant-database-takeover.html
    — accessed 2026-09-26 — independent outlet, high confidence.
32. "Azure Cosmos DB Flaw Exposed Platform-Wide Key That Could Access Any
    Database" — The Hacker News —
    https://thehackernews.com/2026/07/azure-cosmos-db-flaw-exposed-platform.html
    — accessed 2026-09-26 — independent outlet, corroborates #31.

**Note on research method:** `WebFetch` (full-page retrieval) was blocked by
this session's network egress proxy for nearly every domain attempted, per
§0.1; only one raw GitHub file fetch succeeded (source 14). Every other claim
above rests on `WebSearch`'s synthesized snippets rather than a direct
full-page read, which is why confidence notes lean toward "vendor-sourced"
wherever a single blog is the only carrier of a claim. No named incident,
auditor test, or company example above was invented; no disclosed real-world
incident tying a leak specifically to Postgres RLS misconfiguration was
found, as distinct from the many hypothetical/technical write-ups on how that
could happen.

---

## 4. AI-native platform supplemental frameworks

*Sourcing note: as in every section above, full-page fetches were unavailable
in the research environment (tool-level block, per §0.1); claims below rely
on search-engine-returned excerpts rather than independently re-verified
full-text reads.*

### 4.1 ISO/IEC 42001 and SOC 2

ISO/IEC 42001:2023 (published December 2023) is the first certifiable AI
management system (AIMS) standard, built on ISO's common high-level
structure — the same skeleton as ISO 27001. Clauses 1–3 cover scope/terms;
certifiable requirements run through clauses 4–10 (context of the
organization, leadership, planning, support, operation, performance
evaluation, improvement); Annex A supplies roughly 38 controls across nine
control objectives (A.2–A.10): AI policy, internal organization, resourcing,
impact assessment, the AI system life cycle, data for AI systems, information
for interested parties, use of AI systems, and third-party/supplier
relationships.

The scope clause applies to any organization that "develops, provides, or
uses" AI-enabled products or services, and the standard explicitly defines an
"AI User" role — deploying AI systems within organizational operations —
alongside AI Developer, Provider, Producer, and Partner roles. So by the
standard's own text, ISO 42001 is written for **both** fact patterns relevant
here, not one: a company embedding AI in its product sits in the
Provider/Producer role; a company using AI systems to run its own
operations — including AI coding agents building software — sits in the User
role the standard also governs. SAIRN would plausibly hold both roles at
once: AI User (Claude-based agents performing SAIRN's own engineering) and AI
Producer/integrator (apps that call Claude's API as an in-product feature).

Compliance-audit firms already sell combined SOC 2 + ISO 42001 programs:
A-LIGN, Schellman, BarrAdvisory, and Barnes Dennig (a named "SOC 2 and ISO
42001" service line) all frame the two as complementary — SOC 2's Trust
Services Criteria give an operational/security assurance baseline with no
AI-specific criteria of its own; ISO 42001 layers AI governance (risk,
transparency, bias, accountability) on top. Treat this "complementary, not
redundant" framing as **vendor-sourced, lower confidence** — every firm
making the argument also sells both engagements.

### 4.2 NIST AI RMF 1.0 and AI 600-1

NIST AI RMF 1.0 (January 2023) is voluntary, non-certifiable guidance
organized around four functions: Govern, Map, Measure, Manage. NIST AI 600-1,
the Generative AI Profile (published July 2024), extends it with
generative-AI-specific risk categories and suggested actions mapped to the
same four functions. NIST itself publishes official "crosswalks" from AI RMF
to other frameworks, but no NIST- or AICPA-issued crosswalk to SOC 2's Trust
Services Criteria was found. Every SOC2-to-AI-RMF "mapping" located (Security
Boulevard, LBMC, Lazarus Alliance, Orca Security) is independent
compliance-advisory content, not an official cross-reference —
**vendor-sourced, lower confidence**, collectively. Their converging
practical approach is nonetheless a useful framing: treat AI RMF as an
overlay on an existing SOC 2/ISO 27001 program — map current controls to
Govern/Manage first, add new evidence (model cards, eval harnesses,
drift/runtime monitoring) where Map/Measure demand it. Worth carrying forward
as a general framing line, repeated across sources: auditors can provide
reasonable assurance on the *controls around* AI, not on the correctness of
AI output itself.

### 4.3 AICPA guidance — the crux question

**No "SOC for AI" AICPA offering exists as of September 2026** — checked
directly, not assumed. The governing standard is still the 2017 Trust
Services Criteria with points-of-focus refreshed in 2022; there is no "2026
TSC." The AICPA Auditing Standards Board's live 2026 attestation-standards
project (exposure draft issued February 26, 2026; comments closed June 30,
2026; at "Discuss Comment Letters" stage per its August 2026 meeting) targets
sustainability-information attestation and general modernization of
attestation standards — AI is named only as a future "emerging area," with no
dedicated track or exposure draft. Separately, the *Journal of Accountancy*
(November 1, 2025, "A New Frontier: CPAs as AI System Evaluators") floats
CPAs becoming third-party "AI auditors" assessing AI systems' reliability,
security, and bias, explicitly analogized to SOC engagements — but this is
aspirational commentary about auditing AI systems as a subject, not existing
criteria, and not aimed at a service organization's own AI-driven internal
process.

On AI-agent-authored code and CC8.1 (change management) specifically: **no
AICPA statement was found addressing it.** All substantive commentary —
whether an AI reviewer can satisfy CC8.1, how evidence should differ, who is
accountable — comes from compliance-automation vendors and audit-adjacent
blogs (Workstreet, heygrc, Teleport, The Bright Byte, Accel Comply, Another
Dimension Creative Group), not AICPA doctrine. Their converging
non-authoritative reading: CC8.1's text is agent-neutral — it requires
changes be authorized, tested, approved, and documented, without naming the
reviewer as human — so an AI reviewer can technically satisfy the letter of
the criterion. The trap several flag: if a company's own written policy says
a human must peer-review production code, substituting an AI reviewer is a
documented-control deviation regardless of review quality; every source
insists accountability must resolve to one named, traceable human who
approved the change, never the AI or the prompt-writer alone. Convergent new
evidence expectations across these sources: immutable per-change audit logs
tied to a developer identity/session, a written policy that actually names
AI-authored/reviewed code (so the control runs as documented, not as
assumed), and AI service accounts/API keys held to the same least-privilege
and deprovisioning discipline as human accounts. **This is useful
practitioner convergence, but it is not AICPA guidance and should not be
represented as such** — the absence itself is the genuine, useful finding
this angle was asked to surface.

### 4.4 Real disclosed examples

Two named, well-documented, high-profile disclosures of large-scale
AI-driven engineering exist. **Anthropic's** own "When AI Builds Itself"
report (May 2026, covered by VentureBeat and others) states over 80% of code
merged into Anthropic's production codebase is authored by Claude with human
review, up from low single digits before Claude Code's February 2025 research
preview. **Coinbase** CEO Brian Armstrong publicly stated (on X, widely
covered by The Block and others) that roughly 40% of Coinbase's daily code is
AI-generated, targeting over 50% by October 2026. **Neither disclosure is
publicly connected by the company to its own SOC 2 (or equivalent) audit
experience** — no source ties either statistic to a CC8.1 discussion, an
auditor evidence request, or an attestation outcome. That exact
intersection — a named company describing how AI-driven engineering
interacted with an actual SOC 2 engagement — does not appear to be publicly
documented as of this research.

Weaker, closer-fitting matches: a compliance-automation vendor self-published
a post describing its own agents generating SOC 2 compliance evidence,
committing to git, and filing GitHub issues under human review
(vendor-sourced, single-source, unverified — lower confidence); and a couple
of compliance blogs recount anonymized, unnamed-company anecdotes — for
example, a "Series C fintech" SOC 2 Type II prep call where one auditor
question about how a stack trace pasted into an AI tool is handled reportedly
added six weeks to the audit — illustrating the real friction point without
being attributable or independently verifiable. **Plainly: a real, checkable,
named-company account matching the exact fact pattern here (AI-agent-driven
engineering plus how it interacted with a SOC 2 audit) was not found.** SAIRN
would have no established market precedent to point to; an auditor would be
interpreting CC8.1 fresh against SAIRN's specific setup.

### Sources (§4)

1. ISO/IEC 42001:2023 — AI management systems (official standard page) —
   https://www.iso.org/standard/42001 — accessed 2026-09-26 —
   primary/authoritative.
2. ISO — "ISO/IEC 42001 explained" —
   https://www.iso.org/home/insights-news/resources/iso-42001-explained-what-it-is.html
   — accessed 2026-09-26 — primary/authoritative.
3. Schellman — "Understanding Your AI Role in ISO 42001 Certification" —
   https://www.schellman.com/blog/iso-certifications/what-is-your-iso-42001-ai-role
   — accessed 2026-09-26 — accredited audit/cert firm, moderate confidence.
4. Konfirmity — "ISO 42001 Controls: The 38 Annex A Controls" —
   https://www.konfirmity.com/blog/iso-42001-controls — accessed 2026-09-26 —
   vendor-sourced, lower confidence (control-count corroboration).
5. A-LIGN — "ISO 42001 and AIUC-1: How Two AI Assurance Standards Work
   Together" — https://www.a-lign.com/articles/iso-42001-and-aiuc-1 —
   accessed 2026-09-26 — vendor-sourced (certification body), lower
   confidence.
6. BarrAdvisory — "SOC 2 vs. ISO 42001: Which AI Compliance Framework Is
   Right for You?" — https://www.barradvisory.com/resource/soc-iso-ai-compliance/
   — accessed 2026-09-26 — vendor-sourced, lower confidence.
7. Barnes Dennig — "SOC 2 and ISO 42001 | Essentials of AI Governance"
   (service page) — https://www.barnesdennig.com/service/soc-2-and-iso-42001/
   — accessed 2026-09-26 — vendor-sourced, lower confidence.
8. NIST — AI RMF Crosswalks —
   https://www.nist.gov/itl/ai-risk-management-framework/crosswalks-nist-artificial-intelligence-risk-management-framework
   — accessed 2026-09-26 — primary/authoritative.
9. NIST — AI 600-1, Generative AI Profile (July 2024) —
   https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf — accessed
   2026-09-26 — primary/authoritative.
10. Security Boulevard — "5 AI Governance Frameworks for SOC 2 Compliance"
    (July 2026) — https://securityboulevard.com/2026/07/5-ai-governance-frameworks-for-soc-2-compliance/
    — accessed 2026-09-26 — vendor-sourced, lower confidence.
11. LBMC Cybersecurity — "Generative AI Risk Management with SOC 2" —
    https://www.lbmc.com/blog/generative-ai-soc-2/ — accessed 2026-09-26 —
    vendor-sourced, lower confidence.
12. Lazarus Alliance/michaelpeters.org — "AI RMF Integration: SOC 2 Risk
    Management" — https://michaelpeters.org/ai-rmf-integration-soc-2-risk-management-with-lazarus-alliance/
    — accessed 2026-09-26 — vendor-sourced, lower confidence.
13. Aprio — "SOC 2 and AI in 2026: The Criteria Didn't Change, but the
    Examination Did" — https://www.aprio.com/insights-events/soc-2-and-ai-in-2026-the-criteria-didnt-change-but-the-examination-did-ins-article/
    — 2026, accessed 2026-09-26 — advisory firm, moderate confidence.
14. CPA Practice Advisor — "AICPA Seeks Public Comment on Proposed Updates to
    Attestation Standards" (Feb. 27, 2026) —
    https://www.cpapracticeadvisor.com/2026/02/27/aicpa-seeks-public-comment-on-proposed-updates-to-attestation-standards/177561/
    — accessed 2026-09-26 — trade press, high confidence.
15. Journal of Accountancy — "Auditing Standards Board proposes changes to
    attestation standards" (Feb. 2026) —
    https://www.journalofaccountancy.com/news/2026/feb/auditing-standards-board-proposes-changes-to-attestation-standards/
    — accessed 2026-09-26 — AICPA-affiliated publication, high confidence.
16. Journal of Accountancy — "Proposed attestation changes: What CPAs should
    know" (Apr. 2026) —
    https://www.journalofaccountancy.com/issues/2026/apr/proposed-attestation-changes-what-cpas-should-know/
    — accessed 2026-09-26 — high confidence.
17. Journal of Accountancy (podcast) — "The Auditing Standards Board's
    priorities for 2026 and beyond" (May 2026) —
    https://www.journalofaccountancy.com/podcast/2026/may/the-auditing-standards-boards-priorities-for-2026-and-beyond/
    — accessed 2026-09-26 — high confidence.
18. Journal of Accountancy — "A new frontier: CPAs as AI system evaluators,"
    by Jamie J. Roessner (Nov. 1, 2025) —
    https://www.journalofaccountancy.com/issues/2025/nov/a-new-frontier-cpas-as-ai-system-evaluators/
    — accessed 2026-09-26 — high confidence.
19. Schellman — "What Does the AICPA Require of Artificial Intelligence?" —
    https://www.schellman.com/blog/soc-examinations/artificial-intelligence-in-soc-reports
    — accessed 2026-09-26 — accredited audit firm, moderate confidence.
20. Workstreet — "Can AI Agents Satisfy SOC 2 Code Review Requirements?" —
    https://www.workstreet.com/blog/can-ai-agents-satisfy-soc-2-code-review-requirements
    — accessed 2026-09-26 — vendor-sourced, lower confidence.
21. heygrc — "SOC 2 never said a human has to approve your pull requests" —
    https://heygrc.com/blog/soc-2-never-said-a-human-approves-your-prs —
    accessed 2026-09-26 — vendor-sourced, lower confidence.
22. Teleport — "How AI Agents Impact SOC 2 Trust Services Criteria" —
    https://goteleport.com/blog/ai-agents-soc-2/ — accessed 2026-09-26 —
    vendor-sourced, lower confidence.
23. The Bright Byte — "AI Coding Agents and SOC 2: A Field Guide" —
    https://thebrightbyte.com/playbook/expertise/ai-coding-agents-soc2 —
    accessed 2026-09-26 — vendor-sourced, lower confidence.
24. Vibe Coder Blog — "SOC 2 Considerations When Your Product Is Built With
    AI Tools" — https://blog.vibecoder.me/soc2-considerations-ai-built-products
    — accessed 2026-09-26 — vendor-sourced, lower confidence.
25. Accel Comply — "Does SOC 2 Require Code Review for AI-Generated Code?" —
    https://www.accelcomply.com/articles/code-review-control-never-tested-for-ai
    — accessed 2026-09-26 — vendor-sourced, lower confidence (source of the
    anonymized fintech anecdote).
26. Another Dimension Creative Group — "What Auditors Actually Ask About
    AI-Generated Code" —
    https://anotherdimensioncreativegroup.com/blog/what-auditors-ask-ai-generated-code
    — accessed 2026-09-26 — vendor-sourced, lower confidence.
27. TeamDay — "AI-Native SOC 2 Compliance: How We Replaced Our Compliance
    Team with AI Agents" — https://www.teamday.ai/blog/ai-native-soc2-compliance
    — accessed 2026-09-26 — vendor-sourced/self-published, single-source,
    lower confidence.
28. VentureBeat — "Anthropic says 80% of its new production code is now
    authored by Claude — how your enterprise can keep up" (2026) —
    https://venturebeat.com/technology/anthropic-says-80-of-its-new-production-code-is-now-authored-by-claude-how-your-enterprise-can-keep-up
    — accessed 2026-09-26 — tech trade press reporting on Anthropic's
    primary report, high confidence.
29. The Block — "Brian Armstrong says about 40% of Coinbase's daily code is
    AI-generated" (2026) — https://www.theblock.co/post/369460/brian-armstrong-coinbase-ai
    — accessed 2026-09-26 — trade press, high confidence.
30. Brian Armstrong (@brian_armstrong) on X — original statement (2026) —
    https://x.com/brian_armstrong/status/1963315806248604035 — accessed
    2026-09-26 — primary source (self-disclosure).

**Key takeaways:** ISO 42001 explicitly covers internal AI *use* as well as
AI-in-product, per its own "AI User" role definition — the strongest,
best-sourced finding here, and it directly supports treating ISO 42001 as
relevant to SAIRN's engineering-process fact pattern, not just its Claude-API
product features. No AICPA "SOC for AI" product exists, and the live 2026
AICPA attestation-standards exposure draft is about sustainability reporting,
not AI. No AICPA guidance addresses AI-agent code review under CC8.1 — that
gap is filled only by non-authoritative vendor/advisory-firm commentary. And
no named company was found publicly connecting AI-driven engineering to a
SOC 2 audit experience specifically, which makes SAIRN's actual situation a
genuine first-mover case with no market precedent to cite either way.

---

## 5. Real enforcement and mislabeling cases

*Methodology note: direct fetches to primary sources (sec.gov, ftc.gov,
journalofaccountancy.com, aicpa-cima.com, techcrunch.com) were blocked per
§0.1. Findings below were verified through search-result cross-referencing —
each fact corroborated across two or more independent sources (law-firm
client alerts, journalism, or the indexed .gov press-release title/URL
itself) rather than a single direct document fetch. One apparent
AI-search-summary hallucination was caught and discarded during this
research: a claim that the SEC's BF Borgers case involved "falsified SOC 2
audit documentation." Independently checked and confirmed false — BF Borgers
is a PCAOB financial-statement-audit fraud case, unrelated to SOC 2/AT-C
attestation engagements. It is named below only to flag the conflation, not
as a SOC 2 precedent.*

### 5.1 SEC enforcement actions

**No SEC enforcement action was found that names "SOC 2" specifically as the
misrepresented claim.** This is a real gap, not a search failure: SOC 2
examinations are a private attestation product between a company and its
customers/vendors, not a disclosure item with its own line in securities law,
so the SEC's interest only attaches when a compliance/security claim becomes
*material to investors* (S-1 language, earnings calls, 8-Ks). The closest
genuine SEC precedent is **SEC v. SolarWinds Corp. and Timothy Brown**
(complaint filed October 30, 2023, SDNY), which alleged SolarWinds' public
Security Statement and other statements misrepresented its cybersecurity
controls before the 2020 SUNBURST breach. On July 18, 2024, the court
dismissed most of the case — all claims tied to SEC filings, press releases,
and blog/podcast statements as non-actionable "puffery," and rejected the
theory that internal-controls rules reach cybersecurity controls — leaving
only the Security Statement claim alive. The SEC itself moved to dismiss that
remaining claim with prejudice on November 20, 2025, ending the case. The
practical lesson for this document: even the SEC's most aggressive attempt to
treat a security-practices web page as an actionable representation to
investors substantially failed in court.

The **structurally closest analogous precedent** is the SEC's "AI-washing"
line — false capability/compliance-style claims, not SOC 2, but the same
theory of liability (materially overstating a status the company does not
actually hold). **Delphia (USA) Inc. and Global Predictions Inc.** (SEC
press release 2024-36, March 18, 2024) settled for $225,000 and $175,000
respectively for claiming AI/machine-learning capabilities they did not have
(Global Predictions also falsely called itself "the first regulated AI
financial advisor"). **Presto Automation Inc.** (SEC Release No. 33-11352,
January 14, 2025) was the first AI-washing case against a *public* company:
it overstated its drive-through voice-AI's autonomy, did not disclose that a
third party actually owned/operated the underlying technology, and did not
disclose that 70%+ of orders needed human intervention — resolved with a
cease-and-desist only, no penalty. Separately, **SEC v. BF Borgers CPA PC**
(Release 2024-51, May 2024, $12M firm penalty plus $2M personal penalty) is
worth flagging as an *analogous fabrication pattern* — the firm was charged
with rolling forward prior workpapers and fabricating audit documentation
across 1,500+ SEC filings — but this is, again, a PCAOB financial-statement
-audit case, **not** a SOC 2 matter, and should not be cited as one.

### 5.2 FTC enforcement actions

**No FTC action was found that names "SOC 2" specifically either.** The
FTC's real, repeated pattern of "false certification" enforcement is the
**EU-U.S. Privacy Shield program** — roughly 40 actions from 2017–2020
against companies (for example RagingWire Data Centers and EmpiriStat, both
2019) that claimed current Privacy Shield participation after their
certification lapsed, or claimed certification they never completed. This is
a genuine, direct precedent for "claiming a compliance status you no
longer/never held," just against a different named framework.

**FTC v. Verkada Inc.** (Matter 2123068, complaint and $2.95M order, 2024) is
instructive precisely because it is *not* a false-certification case: Verkada
actually held real SOC 2 Type I/II reports and later added ISO
27001/27017/27018 — the FTC's complaint instead targeted separate false
claims of HIPAA and Privacy Shield compliance, plus employee-authored fake
reviews. This is a useful cautionary data point: holding a real attestation
in one area does not immunize false compliance claims made elsewhere. **FTC
v. Drizly, LLC** (2022, with the CEO personally bound for a decade) shows the
FTC's general willingness to reach individual executives for security
-practice failures, though it did not involve a certification claim.

### 5.3 Public incident: the Delve scandal (2026)

This is the most on-point, most recent finding — and, as noted in §2.3, it
surfaced independently in both this angle's research and the CPA-cost
research above, which is itself a mild signal of how prominent the case
currently is in the compliance-industry conversation. It is **not formal
enforcement** — it is an ongoing, contested public allegation. Starting March
18, 2026, an anonymous whistleblower group ("DeepDelver") published a
leaked-spreadsheet investigation alleging that Delve — a YC-backed
compliance-automation startup valued at $300M — had systematically produced
fabricated SOC 2 reports for its customers: 493 of 494 examined reports were
near-identical (same paragraphs, same typo), auditor conclusions and test
procedures existed in draft before clients submitted evidence, and the
"U.S.-based CPA firms" named were allegedly shell/mailbox operations.
TechCrunch independently reported the story (March 22 and March 30, 2026). Y
Combinator removed Delve from its company directory in early April 2026.
**Delve's own position, on the record, is that it never issues compliance
reports** — it describes itself as a platform that feeds evidence to
independent, licensed third-party auditors who alone issue the opinion — so
the allegation and the company's denial should both be represented if this
case is cited. No SEC, AICPA, or state CPA board enforcement order was
confirmed via a primary source in this research; a federal class action
referencing "sham security audits" has been reported by secondary/legal
-aggregator coverage, but a docket number could not be independently verified
this session, so it should be cited as "reported, not court-confirmed here."
One regulator-adjacent response is corroborated across multiple industry
sources: the AICPA Peer Review Board reportedly issued guidance in May 2026
directing peer reviewers to flag identical risk assessments, sample sizes,
and testing procedures across clients as "nonconforming" — a direct response
to the pattern this scandal surfaced, even without a named enforcement
target.

### 5.4 Why "SOC 2 compliant/certified" is the wrong phrase

This part has clean, consistent, non-thin sourcing. AICPA's own SOC 2/SOC 3
examination guidance and independent CPA-firm commentary (for example
Schneider Downs) agree: **SOC 2 is an attestation engagement under SSAE
18/AT-C Section 105 and 205, not a certification.** There is no accrediting
body for SOC 2 auditors, no AICPA-sanctioned "SOC 2 certified" seal, and no
central registry of compliant companies the way ISO 27001 has certification
bodies. "Certified" implies a fixed pass/fail bar audited against a uniform
standard; a SOC 2 report is instead one named CPA firm's professional
opinion, scoped to that engagement's specific control set and period. For a
company that has not yet completed its audit, the defensible language is
"pursuing/undergoing a SOC 2 Type I or Type II examination," "SOC 2 readiness
assessment complete," or "targeting a SOC 2 report by [date]" — never "SOC 2
compliant" or "SOC 2 certified" until a real report exists, and never
"certified" even after it does.

### Sources (§5)

1. SEC Press Release 2024-36, "SEC Charges Two Investment Advisers with
   Making False and Misleading Statements About Their Use of Artificial
   Intelligence" — https://www.sec.gov/newsroom/press-releases/2024-36 —
   accessed 2026-09-26 — high confidence, primary source (.gov), corroborated
   by 4 independent law-firm summaries.
2. WilmerHale — "SEC Brings Two More AI Washing Enforcement Actions..."
   (Delphia/Global Predictions detail) —
   https://www.wilmerhale.com/en/insights/client-alerts/20240327-sec-brings-two-more-ai-washing-enforcement-actions-against-investment-advisers-continuing-its-pursuit-of-misstatements-related-to-ai
   — accessed 2026-09-26 — high confidence, reputable law firm.
3. Cooley PubCo — "SEC charges 'AI-washing' at Presto Automation" (Release
   No. 33-11352) — https://cooleypubco.com/2025/01/30/sec-charges-ai-washing/
   — accessed 2026-09-26 — high confidence, corroborated by D&O Diary and
   Lowenstein Sandler.
4. Cooley — "Federal Court Dismisses Bulk of SEC's Complaint Against
   SolarWinds" —
   https://www.cooley.com/news/insight/2024/2024-07-23-federal-court-dismisses-bulk-of-secs-complaint-against-solarwinds-in-cyberattack-case
   — accessed 2026-09-26 — high confidence.
5. Jones Day — "SEC Dismisses Remaining SolarWinds Claims" (Nov. 20, 2025) —
   https://www.jonesday.com/en/insights/2025/12/sec-dismisses-remaining-solarwinds-claims
   — accessed 2026-09-26 — high confidence, corroborated by the Harvard Law
   School Forum on Corporate Governance.
6. SEC Press Release 2024-51, "SEC Charges Audit Firm BF Borgers and Its
   Owner with Massive Fraud Affecting More Than 1,500 SEC Filings" —
   https://www.sec.gov/newsroom/press-releases/2024-51 — accessed 2026-09-26
   — high confidence primary source; explicitly **not** a SOC 2 case (PCAOB
   financial-statement audits) — flagged here to correct a conflation seen in
   one secondary aggregator during this research.
7. FTC Press Release — "Five Companies Settle FTC Allegations that they
   Falsely Claimed Participation in the EU-U.S. Privacy Shield" (Sept. 2019)
   — https://www.ftc.gov/news-events/news/press-releases/2019/09/five-companies-settle-ftc-allegations-they-falsely-claimed-participation-eu-us-privacy-shield
   — accessed 2026-09-26 — high confidence, primary source title/URL
   indexed; direct fetch blocked this session.
8. FTC Press Release — "FTC Reaches Settlements with Four Companies That
   Falsely Claimed Participation in the EU-U.S. Privacy Shield" (Sept. 2018)
   — https://www.ftc.gov/news-events/news/press-releases/2018/09/ftc-reaches-settlements-four-companies-falsely-claimed-participation-eu-us-privacy-shield
   — accessed 2026-09-26 — high confidence.
9. IAPP — "Keeping your shield up: Unpacking the FTC's Privacy Shield
   enforcement action" — https://iapp.org/news/a/keeping-your-shield-up-unpacking-the-ftcs-privacy-shield-enforcement-action
   — accessed 2026-09-26 — high confidence, reputable privacy-law
   publication summarizing the ~40-action pattern.
10. FTC — "Verkada Inc., U.S. v." case page (Matter 2123068) and complaint —
    https://www.ftc.gov/legal-library/browse/cases-proceedings/2123068-verkada-inc-us-v
    and https://www.ftc.gov/system/files/ftc_gov/pdf/2123068verkadacomplaint.pdf
    — accessed 2026-09-26 — high confidence primary source; corroborated by
    HIPAA Journal and the National Law Review that the complaint's
    compliance claims were HIPAA/Privacy Shield, not SOC 2/ISO.
11. Alston & Bird — "FTC Settles with Drizly for Alleged Security Failures"
    — https://www.alston.com/en/insights/publications/2022/10/ftc-settles-with-drizly-for-alleged-security
    — accessed 2026-09-26 — high confidence, corroborated by Mintz and
    Sidley.
12. TechCrunch — "Delve accused of misleading customers with 'fake
    compliance'" (March 22, 2026) —
    https://techcrunch.com/2026/03/22/delve-accused-of-misleading-customers-with-fake-compliance/
    — accessed 2026-09-26 — medium-high confidence; mainstream tech
    journalism, but underlying claims originate from an anonymous
    whistleblower and are disputed by Delve.
13. TechCrunch — "Delve whistleblower strikes again, with alleged receipts
    about 'fake compliance'" (March 30, 2026) —
    https://techcrunch.com/2026/03/30/delve-whistleblower-strikes-again-with-alleged-receipts-about-fake-compliance/
    — accessed 2026-09-26 — medium-high confidence, same caveat as above.
14. Boulay Group (CPA advisory firm) — "Delve Allegations Highlight Risks in
    Automated Compliance" (includes the reported May 2026 AICPA Peer Review
    Board guidance) —
    https://boulaygroup.com/delve-allegations-raise-concerns-for-automated-compliance/
    — accessed 2026-09-26 — medium confidence; credible trade source, but
    the AICPA guidance detail could not be cross-checked against AICPA's own
    site this session (fetch blocked).
15. LegalClarity — "Delve Lawsuit and Scandal: Fake Compliance Reports
    Exposed" — https://legalclarity.org/delve-lawsuit-and-scandal-fake-compliance-reports-exposed/
    — accessed 2026-09-26 — low-medium confidence; reports a federal class
    action but no docket number was independently verified — treat as
    unconfirmed pending a court-record check.
16. AICPA & CIMA — "Read the latest FAQs for SOC 2® and SOC 3® Examinations"
    — https://www.aicpa-cima.com/resources/article/read-the-latest-faqs-for-soc-2-r-and-soc-3-r-examinations
    — accessed 2026-09-26 — high confidence this is the correct primary
    AICPA resource; direct fetch was blocked this session, so specific
    wording is drawn from consistent secondary paraphrase rather than a
    direct quote.
17. Schneider Downs (CPA firm) — "SOC 2 - What is ACTUALLY required?" —
    https://schneiderdowns.com/our-thoughts-on/soc-2-misconceptions-and-requirements/
    — accessed 2026-09-26 — high confidence, practicing CPA firm source
    independent of compliance-automation vendors.
18. soc2auditors.org — "Is SOC 2 a Certification? What the Term Actually
    Means" — https://soc2auditors.org/insights/what-is-soc-2-certification/
    — accessed 2026-09-26 — medium confidence, industry publication;
    corroborates but is not itself an AICPA or CPA-firm primary source.

---

## 6. What this document does not establish or decide

- **It does not resolve the provenance question in §0.** Whether the
  CC1-CC9/CUEC/policy-as-code/IBM-Microsoft-NASA research the task brief
  referenced exists somewhere this clone cannot see, or has not actually been
  written yet, is unresolved here and should be checked directly rather than
  assumed either way.
- **No claim in this document should be quoted externally** — to a customer,
  investor, or auditor — without a follow-up read from a network that can
  reach the underlying primary sources; every finding above rests on
  search-engine snippets, per §0.1, not independently opened pages.
- **This document does not recommend whether SAIRN should pursue a SOC 2
  Type II audit, when, or through which firm or platform.** That is a
  `sairn-decision-gate` question — it turns on facts (actual revenue,
  customer contractual pressure, real budget) this research pass has no
  visibility into and should not guess at.
- **No dollar figure, sample-size number, or named case above should be
  treated as legally or contractually authoritative.** Several are explicitly
  flagged as internally inconsistent across sources (for example, Vetology
  -style pricing conflicts noted in comparable research, or the Vendr-vs
  -aggregator Drata median discrepancy in §2.4); this document preserves
  those disagreements rather than resolving them by picking one number.
- **The Delve allegations in §2.3/§5.3 are allegations, not adjudicated
  fact.** Delve disputes them. They are cited because they are
  well-corroborated as a *live public controversy*, not because this
  document takes a position on their truth.

## 7. Decay

Every source above is a search-index snapshot from 2026-09-26 of pages this
session's sandboxed network could not open directly (§0.1). Standards
documents (AT-C 105/205, the 2017/2022 TSC) are stable and will not go stale
quickly; market-dependent material — CPA and readiness-platform pricing
(§2), the Delve situation (§2.3, §5.3), and the AICPA attestation-standards
proposal (§4.3) — will. **Do not treat any pricing figure, live-controversy
status, or "as of September 2026" regulatory-status claim in this document as
current without re-checking the source directly**, and re-run this pass from
a network that can reach the underlying domains before any figure here is
used in a customer-, investor-, or auditor-facing statement.
