# SAIRNcode external competitive-gap audit — encoders, autonomous coding, specialty billing, denial management (2026-09-26)

**Research pass, 2026-09-26. No code, no claims, no tier registers touched —
new file only, under `docs/cloud-research/`, on its own branch, same lane as
the SOC2/SAIRNvet/StoneDesk/Novaclad/SAIRNlaw research already in this
directory.**

---

## 0. Scope, and a correction to "confirmed closed/no open items"

The task brief for this pass described SAIRNcode as "confirmed
closed/no open items" and asked that any apparent internal gap be treated
with real skepticism before being reported externally. That skepticism was
applied — in both directions, per this platform's own verify-before-report
rule — and it does not support the brief's framing. **A real, dated,
independently-verified internal competitive-gap audit already exists**:
`docs/competitive-gap-audit-sairncode.md`, dated 2026-09-23 (three days
before this pass), with every verdict re-derived against `sairncode.html`
at HEAD rather than assumed. It records real, current open items:

- **The largest one, in its own words**: SAIRNcode has no fully-autonomous
  coding path with confidence-scoring and exception-only human review —
  "the real 2026 category," naming **CodaMetrix** and **Nym Health**
  specifically as the competitive bar. `autonomous` appears zero times in
  the file; there is no exception queue and no auto-post path.
- A **partial gap**: real-time payer-eligibility verification exists
  (`panel-eligibility`, 270/271 checks), but nothing feeds an eligibility
  result back into a coding suggestion — the join, not the data, is
  missing.
- A **narrow, confirmed specialty gap**: the physical-therapy panel is
  missing the **GP modifier**, required on every Medicare outpatient
  therapy claim — the panel's own tooltip lists CQ (a different, PTA
  -specific modifier) where GP should be.
- **Explicitly unmeasured, not confirmed either way**: depth on eight
  enterprise RCM panels (claims, prebill, HCC, DRG, RAC, denial, AR,
  revenue) beyond "the vocabulary and resources are present," and EHR
  interoperability, which "was not measured at all, in either direction."

**The same internal document also records real, verified strengths**, and
this document does not re-litigate those either: AI-drafted appeal letters
with mandatory human review (built, 2026-08-20); a specialty-to-billable
-code validation architecture confirmed across 14 of 15 supplied specialty
facts; and — called out as "the app's strongest differentiator, lead with
this" — an explainability/citation-trail system where every coded item
stores a **verbatim quote from the clinical note plus the specific billing
rule that justified the code**, not just a bare code or a confidence
number. It also records a genuine engineering-integrity decision: the code
explicitly considered and **declined** to build a denial-probability
percentage, on the documented grounds that no real, calibrated model or
outcome data exists to base one on — a distinction the file states plainly:
a count of real logged denials is "real, checkable, and genuinely useful";
a predicted percentage with nothing behind it is not, and was refused.

**This document does not re-derive that internal audit.** It treats its
six-day-old findings as the current internal baseline and researches
whether the market validates, exceeds, or contextualizes each one — which
is what every section below actually does. Unlike the SAIRNvet, StoneDesk,
and SAIRNlaw research in this same series, **no existing external
competitive-gap document for SAIRNcode was found** — this genuinely is
new ground, and the task brief is correct on that specific point.

### 0.1 A network-egress caveat that applies to every section below

As with every research pass run from this environment, outbound `WebFetch`
(full-page retrieval) returned `EGRESS_BLOCKED` for essentially every
vendor, trade-press, and government domain attempted across all four
research angles behind this document — including, this time, GAO.gov and
KFF.org. Every finding below therefore rests on `WebSearch`'s indexed
**excerpt** of a page, not an independently opened full read. Confidence
flags per claim reflect this. **Nothing pricing-specific,
capability-specific, or legally load-bearing below should be quoted
externally — to a health system, a prospect, or in a proposal — without a
follow-up read from a network that can reach these domains.**

---

## 1. Traditional encoder and reference-tool competitors

**All four named vendors — 3M/Solventum CodeFinder, Optum EncoderPro, AAPC
Codify, and Find-A-Code — are human-queried code-lookup/reference tools,
not RCM platforms comparable in scope to SAIRNcode.** A coder enters a term
or code and reviews returned descriptions, cross-references, and edits;
none performs claims submission, AR, denial management, eligibility
checking, or anything resembling SAIRNcode's other 27 resources. They
compete directly with exactly one piece of SAIRNcode — its `sc_encoder`
module — not with the platform as a whole. **Solventum CodeFinder** (the
current name; 3M spun off its health-information-systems business as
Solventum in April 2024) is a decision-logic "coding pathway" encoder,
usually sold as part of the larger 360 Encompass computer-assisted-coding
suite. **Optum EncoderPro.com** (Optum360, a UnitedHealth Group subsidiary)
is a cloud CPT/HCPCS/ICD-10-CM search tool with NCCI/MUE edit-checking.
**Codify by AAPC** — AAPC being, first, the world's largest medical-coding
certification body (200,000+ members), with Codify a companion product to
its training curriculum — covers CPT/HCPCS/ICD-10 with CDT dental as a paid
add-on. **Find-A-Code** (innoviHealth, founded 2006) is the broadest pure
-reference tool, explicitly positioned toward individual coders, students,
and small practices on cost.

**Pricing is published for two of the four.** Optum EncoderPro.com lists
tiered annual pricing: Standard $299.95/yr, Professional $549.95/yr, Expert
$999.95/yr, with multi-user pricing quote-only. Codify's tiers are reported
by a third-party aggregator at roughly $415–$625/yr — not independently
confirmed on AAPC's own site in this pass, moderate confidence. Find-A-Code
similarly shows an aggregator-cited entry price near $45/month, also not
independently confirmed. **Solventum publishes no price at all** — enterprise
quote-only; an unattributed "$1,500–$2,500 per coder per year" figure
surfaced in search results but could not be traced to any citable source
and is not reported as a figure per this document's sourcing rules.

**Code-set currency is claimed everywhere and quantified nowhere.** CMS
updates ICD-10-CM annually effective October 1 (FY2026: 487 new codes, 38
revisions, 28 deletions); the AMA owns and updates CPT annually effective
January 1, with Category III/PLA/MAAA codes on separate, faster cycles; any
vendor displaying CPT descriptors must hold an AMA license. Every vendor
checked makes a qualitative freshness claim (Optum: automatic monthly
updates "before implementation"; AAPC: annual/quarterly per the official
cycle; Find-A-Code: "always up-to-date"; Solventum: FY-aligned logic
updates) — **none publishes a numeric turnaround SLA from AMA/CMS release
to platform availability.** The compliance risk this creates is real and
independently documented: multiple RCM-industry sources describe deleted or
outdated codes as a common, payer-enforced cause of automatic claim
rejection "regardless of clinical accuracy," concentrated in the weeks
after each October/January cutover — and note the failure mode is often not
a vendor's master table lagging, but stale entries surviving in EHR
templates, superbills, and a coder's saved "favorites" that a code-set
update never touches.

**None of the four does autonomous AI code assignment.** All remain human
-queried; the one confirmed AI feature among them — Codify's "AI-powered
Smart Search" (August 2025) — improves typo/acronym-tolerant query
matching, not code justification. **No vendor here publishes anything
resembling SAIRNcode's verbatim-quote-plus-specific-rule citation trail** —
on current public evidence, that remains a real, uncontested differentiator
against this specific competitor tier (though see §2 for the tier where it
is genuinely contested).

**A material, current fact worth flagging precisely rather than glossing
over**: Solventum publicly announced in **August 2026** — reportedly under
activist-investor pressure — its intent to separate its entire Health
Information Systems segment (CodeFinder's home) within 12–18 months, via a
structure (spinoff, sale, or combination with "a scaled industry peer") not
yet chosen as of this research. Solventum is the correct *current* owner of
CodeFinder, but that ownership is actively in play, not settled, and should
not be presented as a stable long-term competitive fact.

### Sources (§1)

1. Solventum — 3M Codefinder Software Fact Sheet —
   https://www.solventum.com/content/dam/public/language-masters/en_gb/hisb/document/2023/3m-his-codefinder-hr-factsheet-en-ca.pdf
   — accessed 2026-09-26 — vendor fact sheet, snippet only.
2. 3M — Codefinder Software Fact Sheet —
   https://multimedia.3m.com/mws/media/2000759O/3m-codefinder-software-fact-sheet.pdf
   — accessed 2026-09-26 — vendor material, snippet only.
3. Solventum — Codefinder Software product page —
   https://www.solventum.com/en-au/home/health-information-technology/solutions/codefinder/
   — accessed 2026-09-26 — vendor page, snippet only.
4. IntuitionLabs — 3M CodeFinder overview —
   https://intuitionlabs.ai/software/medical-coding-computer-assisted-coding-cac/cpt-and-hcpcs-coding-tools/3m-codefinder
   — accessed 2026-09-26 — third-party aggregator, moderate confidence.
5. GovTribe — Optum360, LLC vendor record —
   https://govtribe.com/vendors/optum360-llc-7cf84 — accessed 2026-09-26 —
   confirms UnitedHealth Group subsidiary relationship, moderate-high
   confidence.
6. Medical Coding Software — Optum EncoderPro.com Pricing —
   https://medicalcodingsoftware.org/encoder-pro-pricing — accessed
   2026-09-26 — third-party pricing aggregator, moderate confidence.
7. Optum — EncoderPro.com Competitive Comparison (PDF) —
   https://www.optumcoding.com/upload/docs/Optum_EncoderPro.com_Competitive_Comparison_HR.pdf
   — accessed 2026-09-26 — vendor marketing, moderate confidence.
8. AAPC — CDT Codes (Current Dental Terminology add-on) —
   https://www.aapc.com/codify/current-dental-terminology.aspx — accessed
   2026-09-26 — vendor page, moderate-high confidence.
9. AAPC — "How often is Codify code data updated?" —
   https://www.aapc.com/support/codify-by-aapc/how-often-is-the-code-data-updated
   — accessed 2026-09-26 — vendor FAQ, moderate-high confidence.
10. SaaSWorthy — Codify Pricing —
    https://www.saasworthy.com/product/codify/pricing — accessed
    2026-09-26 — third-party aggregator, moderate confidence, not confirmed
    against aapc.com directly.
11. AAPC — "Now on Codify: AI-powered Smart Search" —
    https://www.aapc.com/codes/latest-updates/now-on-codify-make-aipowered-smart-search-your-default-search-08192025
    — accessed 2026-09-26 — vendor announcement, moderate-high confidence.
12. AAPC — "Typos and abbreviations are no problem for our AI-powered
    Smart Search" —
    https://www.aapc.com/codes/latest-updates/now-on-codify-typos-and-abbreviations-are-no-problem-for-our-aipowered-smart-search-08012025
    — accessed 2026-09-26 — vendor announcement, moderate-high confidence.
13. Find-A-Code — FAQ — https://www.findacode.com/aboutus/faq.html —
    accessed 2026-09-26 — vendor FAQ, moderate-high confidence.
14. Find-A-Code — CDT Dental Code Set —
    https://www.findacode.com/dental-codes/cdt-dental-codes-set.html —
    accessed 2026-09-26 — vendor page, moderate confidence.
15. Find-A-Code — Subscribe page —
    https://www.findacode.com/account/subscribe.php — accessed 2026-09-26 —
    referenced only via aggregator summary, low-medium confidence on the
    $45/month figure, flagged unconfirmed.
16. IntuitionLabs — Find-A-Code overview —
    https://intuitionlabs.ai/software/medical-coding-computer-assisted-coding-cac/icd-10-cmpcs-encoders/find-a-code
    — accessed 2026-09-26 — third-party aggregator, moderate confidence.
17. Find-A-Code — "Computer-Assisted Medical Coding (CAC) vs Autonomous
    Medical Coding" —
    https://www.findacode.com/articles/computer-assisted-medical-coding-vs-autonomous-medical-coding-37397.html
    — accessed 2026-09-26 — vendor-published but neutral/explanatory,
    moderate-high confidence.
18. Nym Health blog — "Encoders vs. Computer-Assisted Coding vs. Autonomous
    Coding" —
    https://blog.nym.health/optimizing-medical-coding-with-technology-comparing-encoders-computer-assisted-coding-and-autonomous-coding-solutions
    — accessed 2026-09-26 — competitor-adjacent industry blog, moderate
    confidence.
19. Medicodio — "Medicodio vs 3M CodeFinder" —
    https://medicodio.ai/resources/blog/medicodio-vs-3m-codefinder —
    accessed 2026-09-26 — competitor-authored marketing content, lower
    confidence, used only for a characterization consistent with neutral
    sources.
20. Avalere Health Advisory — "FY 2026 ICD-10-CM Codes Released" —
    https://advisory.avalerehealth.com/insights/fy-2026-icd-10-cm-codes-released
    — accessed 2026-09-26 — health-policy advisory firm, high confidence.
21. AMA — "The CPT® code process" —
    https://www.ama-assn.org/about/cpt-editorial-panel/cpt-code-process —
    accessed 2026-09-26 — primary source, high confidence.
22. AMA — "CPT® licensing frequently asked questions" —
    https://www.ama-assn.org/practice-management/cpt/cpt-licensing-frequently-asked-questions-faqs
    — accessed 2026-09-26 — primary source, high confidence.
23. RCM Gen — "2027 ICD-10 Changes: New Codes & Claim Denial Risks" —
    https://rcmgen.com/2027-icd-10-changes-new-diagnosis-codes-and-claim-denial-risks-effective-october-1-2026/
    — accessed 2026-09-26 — RCM-industry publisher, moderate confidence.
24. Medical Billers and Coders — "Why Do Unspecified ICD-10 Codes Get
    Claims Denied?" —
    https://www.medicalbillersandcoders.com/article/why-unspecified-icd-10-codes-get-claims-denied.html
    — accessed 2026-09-26 — RCM-industry publisher, moderate confidence.
25. Solventum Investor Relations — "Solventum Announces Intent to Separate
    its Health Information Systems Business" —
    https://investors.solventum.com/news-events/press-releases/detail/151/solventum-announces-intent-to-separate-its-health-information-systems-business
    — accessed 2026-09-26 — primary source (Aug 2026), high confidence.
26. HIT Consultant — "Solventum Announces Intent to Separate Health
    Information Systems Business" —
    https://hitconsultant.net/2026/08/06/solventum-announces-intent-to-separate-health-information-systems-business/
    — accessed 2026-09-26 — trade press corroboration, moderate-high
    confidence.
27. 3M Investor Relations — "3M Completes Spin-off of Solventum" —
    https://investors.3m.com/news-events/press-releases/detail/1835/3m-completes-spin-off-of-solventum
    — accessed 2026-09-26 — primary source (Apr 2024), high confidence.
28. AAPC — CPC certification page — https://www.aapc.com/certifications/cpc
    — accessed 2026-09-26 — org's own page, corroborated by secondary
    sources, moderate-high confidence.
29. SelectHub — "Top EncoderPro Alternatives & Competitors 2026" —
    https://www.selecthub.com/medical-coding-software/encoderpro/alternatives/
    — accessed 2026-09-26 — third-party comparison aggregator, moderate
    confidence.

---

## 2. Autonomous and AI-assisted coding competitors

**This is the real competitive bar, and the internal audit's own framing of
it as "the largest gap" holds up under external research — precisely, not
just directionally.** **CodaMetrix** markets "autonomous medical coding"
with confidence-based routing to human coders below a tunable threshold —
not a claim to eliminate coders. Vendor-published figures: ~98% average
accuracy, "validated in real-world deployments" at Mass General Brigham and
University of Colorado; automation above 96% on average (customer UMass
Memorial reports 86%); a reported 70% drop in denial rates on autonomously
-coded radiology claims at Oregon Health & Science University. CodaMetrix
ranked No. 1 in KLAS Research's first "Best in KLAS" category for autonomous
coding (2026) — see the credibility discussion below for exactly what that
does and doesn't verify. On explainability specifically — the sharpest test
of SAIRNcode's own claimed strongest differentiator — CodaMetrix's
"traceable audit trail" language appears mainly in third-party aggregator
copy, and one independent industry commentary explicitly names explainability
as an *open question* for deep-learning coding systems, calling out
CodaMetrix by name as "the question to test."

**Nym Health is the one company in this entire research pass that
affirmatively brands an explainable-AI/audit-trail feature closely
resembling SAIRNcode's own.** Nym (a Mass General Brigham AI spinoff)
markets more aggressive full autonomy — "zero human intervention" language,
a third-party review titled "No Coder in the Loop" — with vendor-claimed
98.7% accuracy and 50–70% of records coded with zero human touch, varying
by specialty. Nym's named customer list is nearly identical to what the
internal audit cited as the competitive bar: Mass General Brigham, UC San
Diego Health, Yale Medicine, Mayo Clinic, and Henry Ford Health. Nym's own
blog runs a post specifically titled "How AI Powers Explainable and
Auditable Medical Coding," claiming a transparent audit trail showing
"exactly which clinical evidence supported the assignment and which
guidelines were applied." **This narrows SAIRNcode's differentiation gap on
paper — but the one specific, checkable fact that would resolve it, whether
Nym's evidence-linkage reaches SAIRNcode's verbatim-quoted-span granularity
or only a coarser document/section-level reference, could not be confirmed
in this pass** (the source page's direct fetch was blocked). This should be
treated as genuinely undetermined, not assumed either way, and is worth a
direct-access follow-up before anyone states confidently that SAIRNcode's
explainability is or isn't still ahead of Nym's specifically.

**Other real, named vendors in this category**: AKASA (branded "expert
-in-the-loop," not zero-touch, with vendor-driven research claiming its
model beat prior state-of-the-art autonomous-coding models by "more than
18%"); Fathom Health (a named 2026 customer, Your Health, reports a 95.5%
automation rate and accuracy improving from 96.3% to 98.3% since go-live;
KLAS gave it a 95.5 performance score "with customers validating 90%+
automation rates"); XpertCoding/AGS Health (>90% autonomous coding under a
"performance warranty," ~99% accuracy claimed); Iodine Software (primarily
a clinical-documentation-improvement platform, not a full autonomous-coding
product in the CodaMetrix/Nym sense); Semantic Health (evidence-linked
concurrent coding and pre-bill auditing, no published autonomy percentage);
and Solventum's own newer "360 Encompass Autonomous Coding System,"
explicitly positioned against "black box" concerns but without a published
accuracy figure found. **No explainability/citation-trail feature
comparable to Nym's (or SAIRNcode's) was found documented for any of these
other vendors.**

**How credible are these numbers, honestly assessed?** Every figure above
is vendor-published or vendor-commissioned unless noted. The clearest
independent statement on the category comes from the **U.S. GAO's July
2026 Science & Tech Spotlight on AI for medical notes and coding**
(GAO-26-109116), which found "relatively few independent studies evaluating
the accuracy of AI documentation and coding tools" and warned that
inaccurate outputs can cause over- or under-reimbursement, that models can
fabricate information, and can "potentially enable billing fraud." Secondary
coverage of the same report cites a documented red flag: one facility's
coding-complexity rating rose 6.7% after announcing an AI coding switch,
versus 0.9% among peer facilities in the same state — a real signal of
upcoding risk, not a validated accuracy figure either way. **The single
clearest, most consequential precedent for judging any vendor's unaudited
accuracy claim** is the Texas Attorney General's 2024 first-of-its-kind
settlement with **Pieces Technologies**, a generative clinical-documentation
AI company: the state found the company's advertised "critical
hallucination rate" (<0.001%) and "severe hallucination rate" (<1 per
100,000) were "likely inaccurate" and may have misled hospitals. Pieces
doesn't do coding specifically, but it is the clearest available case of a
regulator formally rejecting a health-AI company's self-reported accuracy
metric, and it is directly relevant context for every accuracy percentage
cited above. **KLAS Research's methodology** — the closest thing to
independent scrutiny actually found — is customer-satisfaction interviewing
("product works as promoted," "likelihood to recommend"), not a blinded
chart-level accuracy audit against a human-coder gold standard; it validates
that customers *perceive* vendor claims as roughly matching experience, not
that the underlying percentages are metrologically correct. **No
independent, peer-reviewed, vendor-specific validation of any named
vendor's live production accuracy claim was found in this pass.**

**Adoption remains an early-majority-not-yet phenomenon, not a settled
market.** AMA survey data cited in the GAO report shows clinician use of AI
for documentation/coding rising from 21% (2024) to 28% (2026). Oliver
Wyman's 2026 Healthcare RCM Survey (200+ decision-makers) found under 20% of
provider organizations have successfully scaled AI tools enterprise-wide,
and only 15% have fully integrated AI into standard RCM operations — even as
70–90% expect to increase AI-RCM spending over the next three years. This is
real, sourced evidence that autonomous coding remains an early-adoption
minority practice as of 2026, which matters for how urgently SAIRNcode
needs to close this gap versus how much runway exists.

### Sources (§2)

1. CodaMetrix — "Year One Real Results" —
   https://www.codametrix.com/resources/year-one-real-results-how-health-systems-are-using-ai-to-deliver-fast-roi-in-the-revenue-cycle
   — accessed 2026-09-26 — vendor claim, snippet only.
2. SourceForge / MedAI Verdict — CodaMetrix product descriptions —
   https://sourceforge.net/software/product/CodaMetrix/ ,
   https://medaiverdict.com/tools/codametrix — accessed 2026-09-26 —
   third-party aggregator, moderate confidence.
3. ASP RCM Solutions — "How Autonomous Coding Platforms Are Reducing Claim
   Denials by 70%" — https://asprcmsolutions.com/blog/reducing-claim-denials-70/
   — accessed 2026-09-26 — industry blog citing vendor/customer figures.
4. CodaMetrix — "Named No. 1 in Inaugural Best in KLAS" —
   https://www.codametrix.com/resources/codametrix-named-no-1-in-inaugural-best-in-klas-title-for-autonomous-medical-coding
   — accessed 2026-09-26 — vendor release describing a third-party (KLAS)
   result; see methodology caveat in body text.
5. MedAI Verdict — CodaMetrix explainability commentary —
   https://medaiverdict.com/tools/codametrix — accessed 2026-09-26 —
   third-party aggregator; the "question to test" framing is independent
   editorial caveat, not a CodaMetrix claim.
6. Nym Health — Engine page — https://nym.health/autonomous-medical-coding/nym-engine/
   — accessed 2026-09-26 — vendor claim, snippet only.
7. RevCycleAI — "Nym Health Review: No Coder in the Loop" —
   https://revcycleai.com/blog/nym-health-vendor-deep-dive/ — accessed
   2026-09-26 — third-party analyst deep-dive, moderate confidence.
8. Becker's Hospital Review — "Henry Ford Health taps Mass General Brigham
   AI spinoff for bedside medical coding" —
   https://www.beckershospitalreview.com/healthcare-information-technology/innovation/henry-ford-health-taps-mass-general-brigham-ai-spinoff-for-bedside-medical-coding/
   — accessed 2026-09-26 — trade press, snippet only.
9. Nym Health blog — "How AI Powers Explainable and Auditable Medical
   Coding" — https://blog.nym.health/explainable-ai-in-healthcare —
   accessed 2026-09-26 — **key source for the explainability comparison**,
   vendor's own claim, fetch blocked, snippet only; verbatim-quote
   granularity unconfirmed.
10. AKASA blog — "Using Machine Learning to Enable Autonomous Medical
    Coding" — https://akasa.com/blog/using-machine-learning-to-enable-autonomous-medical-coding
    — accessed 2026-09-26 — vendor claim.
11. PR Newswire — "New AI Approach Exceeds Performance of Traditional
    Models For Automatic Coding of Medical Notes" —
    https://www.prnewswire.com/news-releases/new-ai-approach-exceeds-performance-of-traditional-models-for-automatic-coding-of-medical-notes-301348526.html
    — accessed 2026-09-26 — vendor-issued release describing
    vendor-affiliated research.
12. RFP.wiki — AKASA profile — https://www.rfp.wiki/specialty-industries/healthcare-life-sciences/healthcare/revenue-cycle-management-software/akasa
    — accessed 2026-09-26 — third-party aggregator; possibly generic
    boilerplate phrasing, low-moderate confidence.
13. BusinessWire — "Your Health Deploys Fathom Autonomous Medical Coding..."
    — https://www.businesswire.com/news/home/20260319818217/en/ — accessed
    2026-09-26 — joint vendor/customer release, moderate-high confidence as
    a vendor claim.
14. BusinessWire — "Fathom Achieves 95.5 Overall Performance Score in KLAS
    Research Autonomous Coding Report..." —
    https://www.businesswire.com/news/home/20251002716056/en/ — accessed
    2026-09-26 — release describing a third-party (KLAS) customer
    -interview report.
15. AGS Health / XpertDox — https://www.agshealth.com/ai-platform/autonomous-coding/
    , https://www.xpertdox.com/xpertcoding/ — accessed 2026-09-26 — vendor
    claims.
16. Fierce Healthcare — Iodine Software coverage —
    https://www.fiercehealthcare.com/health-tech/iodine-software-rolls-out-ai-software-tackle-major-hospital-challenge
    — accessed 2026-09-26 — trade press, moderate confidence.
17. Semantic Health — https://www.semantichealth.ai/post/how-we-are-unlocking-data-driven-care-applications-by-helping-medical-coders-and-auditors
    — accessed 2026-09-26 — vendor claim.
18. Solventum — 360 Encompass CAC —
    https://www.solventum.com/en-us/home/health-information-technology/solutions/360-encompass-cac/
    — accessed 2026-09-26 — vendor claim.
19. Solventum — 360 Encompass Autonomous Coding System —
    https://www.solventum.com/en-us/home/health-information-technology/solutions/360-encompass-autonomous/
    — accessed 2026-09-26 — vendor claim.
20. U.S. GAO — "Science & Tech Spotlight: AI for Medical Notes and Coding"
    (GAO-26-109116, July 16, 2026) — https://www.gao.gov/products/gao-26-109116
    — accessed 2026-09-26 — primary federal source, fetch blocked but
    triangulated across independent secondary summaries, high confidence
    despite no direct read.
21. National Law Review / Mondaq — summaries of the GAO report —
    https://natlawreview.com/article/ai-medical-documentation-and-coding-emerging-uses-benefits-and-risks-healthcare
    , https://www.mondaq.com/unitedstates/healthcare/1842732/ai-in-medical-documentation-and-coding-emerging-uses-benefits-and-risks-for-healthcare-providers
    — accessed 2026-09-26 — law-firm secondary analysis, moderate-high
    confidence, source of the 6.7%-vs-0.9% statistic.
22. Texas Attorney General — official press release, Pieces Technologies
    settlement — https://www.texasattorneygeneral.gov/news/releases/attorney-general-ken-paxton-reaches-settlement-first-its-kind-healthcare-generative-ai-investigation
    — accessed 2026-09-26 — primary government source, snippet only, high
    confidence.
23. Healthcare Dive — "Texas attorney general, generative AI company settle
    over accuracy allegations" —
    https://www.healthcaredive.com/news/texas-attorney-general-ken-paxton-settles-pieces-technologies-generative-ai-accuracy/727699/
    — accessed 2026-09-26 — trade press, moderate-high confidence.
24. KLAS Research — "From Hype to Reality: What Healthcare Leaders Should
    Know About Autonomous Coding Solutions" —
    https://engage.klasresearch.com/blog/from-hype-to-reality-what-healthcare-leaders-should-know-about-autonomous-coding-solutions/8341/
    — accessed 2026-09-26 — primary KLAS source, fetch blocked, snippet
    only.
25. OAE Publish — "Revamping medical coding with AI: a systematic review of
    interdisciplinary applications" — https://www.oaepublish.com/articles/ais.2024.78
    — accessed 2026-09-26 — peer-reviewed-adjacent; scope is academic
    classifier studies, not the named commercial vendors.
26. AMA — "2026 Physician Survey on Augmented Intelligence" —
    https://www.ama-assn.org/system/files/physician-ai-sentiment-report.pdf
    — accessed 2026-09-26 — primary survey source, snippet only, cited via
    the GAO report.
27. Oliver Wyman — "AI in revenue cycle is delivering results across
    healthcare" (2026 Healthcare RCM Survey) —
    https://www.oliverwyman.com/our-expertise/perspectives/health/2026/may/ai-impact-revenue-cycle-healthcare.html
    — accessed 2026-09-26 — named consultancy primary survey,
    moderate-high confidence.
28. HIMSS — "The State of Healthcare AI & Digital Transformation" (2026 AI
    Landscape Report) — https://www.himss.org/the-state-of-healthcare-ai-and-digital-transformation-adoption-risk-and-readiness/
    — accessed 2026-09-26 — primary source identified; no coding-specific
    adoption percentage retrieved, flagged as incomplete.
29. AHIMA — Advocacy page — https://www.ahima.org/advocacy/news-events/ —
    accessed 2026-09-26 — primary org source; no quantified
    autonomous-coding adoption survey found.

---

## 3. Specialty-specific billing software: chiropractic, dialysis/ESRD, and oncology

**Chiropractic is the closest real fit to SAIRNcode's own architecture, and
the regulatory complexity behind it is real and well-documented.** Named
competitors ChiroTouch, Platinum System, and ChiroSpring are full clinical
-plus-billing EHR systems, not standalone coding tools. The specific rule at
issue — Medicare pays only for active/corrective treatment of a subluxation
(CPT 98940–98942) and requires an **AT modifier**; claims without it are
treated as maintenance care and denied, since Medicare does not cover
maintenance therapy at all — is genuinely error-prone: an OIG audit found
**82% of Medicare payments for chiropractic services were unallowable**,
mostly from billing maintenance care as active treatment. ChiroTouch's
marketing describes real, specific automation matching this exact problem:
macros that auto-append the AT modifier, a pre-submission "Compliance Scan,"
and an AI assistant reviewing documentation for gaps — all vendor-described,
not independently verified against real audit outcomes. Because these are
full EHR+PM systems with the modifier logic wired directly into clinical
documentation, the honest comparison for SAIRNcode isn't "does it beat
ChiroTouch" — it's "is SAIRNcode's own AT-modifier/medical-necessity logic
correct as one module in a multi-specialty platform," a narrower and more
answerable question this document does not resolve (out of scope, see §6).

**Dialysis/ESRD is, honestly, barely a contestable third-party software
market at all.** DaVita and Fresenius Medical Care jointly control roughly
77–84% of U.S. dialysis facilities/hemodialysis volume, up from 59% in
2005 — a level of vertical integration that walls off the majority of this
specialty from any third-party software, regardless of quality. Real,
named third-party vendors do exist for the remainder: **MIQS** (in use
since 1995, CROWNWeb-certified standalone billing) and **Gaia Software**,
both explicitly marketed toward "independent and hospital-based" facilities
— the roughly 15–20% of the market DaVita/Fresenius don't own. On the
regulatory side, two distinct structures should not be conflated: the
**ESRD Prospective Payment System** is the facility-side bundle (CY2026
base rate $281.71 per treatment, covering nearly all drugs/labs/supplies),
while the **physician-side Monthly Capitation Payment** (CPT 90951–90966)
is what SAIRNcode's described "monthly bundled/capitated" model actually
maps to — a facility-side tool would additionally need the separate
per-treatment PPS logic. **Honest finding: SAIRNcode's ESRD module
realistically competes against two small dialysis-only specialists in a
niche-within-a-niche, not against a real open market**, and its competitive
weight should be assessed accordingly.

**Oncology sits in between, and shows a real, structural opening even at
the top of the market.** Real, named EHR-embedded competitors dominate:
Flatiron Health's OncoEMR (5,100+ providers, 220+ community oncology
practices), McKesson/Ontada's iKnowMed, and Elekta ARIA/MOSAIQ for radiation
oncology. CMS requires either the JW (discarded amount) or JZ (no-waste
attestation) modifier on every single-dose-vial J-code claim; OncoEMR
derives the waste amount directly from clinical/nursing documentation of
drug administration — something a standalone coding tool structurally
cannot do without that same documentation feed. Prior authorization is a
uniquely large burden here: 85% of surveyed cancer patients faced PA
requirements, and 72% of oral anticancer drugs require it. **The single
strongest finding in this section**: even the dominant, fully EHR-embedded
oncology billing product doesn't consider itself sufficient — Flatiron just
partnered with Candid Health, an outside "autonomous RCM" company,
explicitly because oncology billing's complexity "can overwhelm traditional
RCM systems" (Flatiron's own framing). Radiation oncology shows the same
pattern, with third parties selling add-on revenue-verification tools
against Elekta's own platform. **Oncology billing is EHR-embedded as the
primary pattern, but the market is actively growing a second, bolt-on RCM
-automation layer on top of that** — which is a real, structural opening for
a correctly-built coding module used as a component, not as a head-to-head
EHR replacement.

### Sources (§3)

1. CMS — Billing and Coding: Chiropractic Services (A56273) —
   https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleId=56273
   — accessed 2026-09-26 — primary regulatory source, high confidence.
2. CMS — Billing and Coding Guidelines L34585 (Chiropractic PDF) —
   https://downloads.cms.gov/medicare-coverage-database/lcd_attachments/34585_31/Billing_and_Coding_Guidelines_L34585.pdf
   — accessed 2026-09-26 — primary regulatory source, high confidence.
3. ChiroEco — "Properly documenting an AT modifier for Medicare
   reimbursement" — https://www.chiroeco.com/at-modifier-medicare/ —
   accessed 2026-09-26 — trade publication, moderate-high confidence.
4. AAA Medical Billing — "Chiropractic Billing: AT Modifiers, Maintenance
   Care & Medicare Rules" — https://aaamb.com/chiropractic-billing-at-modifiers-maintenance-care-medicare-rules/
   — accessed 2026-09-26 — billing-company content, moderate confidence,
   cites the OIG 82% figure.
5. ChiroTouch — FAQs — https://www.chirotouch.com/faqs — accessed
   2026-09-26 — vendor marketing, low-medium confidence.
6. ChiroTouch — Biller solutions page —
   https://chirotouch.com/solutions/role/biller/ — accessed 2026-09-26 —
   vendor marketing, low-medium confidence.
7. Bushido Billing — "How to Optimize ChiroTouch for Faster Claim
   Processing in 2026" — https://bushidobilling.com/optimize-chirotouch-claim-processing-2026/
   — accessed 2026-09-26 — billing-company blog describing vendor
   features, low confidence.
8. Platinum System — homepage — https://www.platinumsystem.com/ —
   accessed 2026-09-26 — vendor marketing, low confidence.
9. Software Finder — ClinicSource profile —
   https://softwarefinder.com/emr-software/clinicsource-therapy —
   accessed 2026-09-26 — third-party listing; basis for excluding
   ClinicSource as general-therapy, not chiropractic-specific.
10. ChiroSpring — homepage — https://www.chirospring.com/ — accessed
    2026-09-26 — vendor marketing, low confidence.
11. Health Law Alliance — "Chiropractic Medicare Audits: The AT Modifier
    Problem" — https://www.healthlawalliance.com/blog/chiropractic-medicare-audits-the-at-modifier-problem
    — accessed 2026-09-26 — law-firm content, moderate confidence,
    corroborates the OIG finding.
12. CMS — End Stage Renal Disease (ESRD) Prospective Payment System —
    https://www.cms.gov/medicare/payment/prospective-payment-systems/end-stage-renal-disease-esrd
    — accessed 2026-09-26 — primary regulatory source, high confidence.
13. Federal Register — CY2026 ESRD PPS Final Rule —
    https://www.federalregister.gov/documents/2025/11/24/2025-20681/medicare-program-end-stage-renal-disease-prospective-payment-system-payment-for-renal-dialysis
    — accessed 2026-09-26 — primary source, high confidence.
14. Applied Policy — "CMS Finalizes 2.2 Percent Payment Increase for ESRD
    Facilities in CY 2026" — https://www.appliedpolicy.com/cms-finalizes-2-2-percent-payment-increase-for-esrd-facilities-in-cy-2026/
    — accessed 2026-09-26 — policy-analysis firm, moderate-high confidence.
15. CMS — CY2026 ESRD PPS Fact Sheet —
    https://www.cms.gov/newsroom/fact-sheets/calendar-year-cy-2026-end-stage-renal-disease-esrd-prospective-payment-system-proposed-rule-cms-1830
    — accessed 2026-09-26 — primary source, high confidence.
16. FCSO Medicare — "ESRD Monthly Capitation Payment (MCP) claims" —
    https://medicare.fcso.com/billing/end-stage-renal-disease-esrd-monthly-capitation-payment-mcp-claims
    — accessed 2026-09-26 — Medicare Administrative Contractor, high
    confidence.
17. AAPC — "Ins and Outs of Pro Fee ESRD Monthly Capitation Payments" —
    https://www.aapc.com/blog/92745-ins-and-outs-of-pro-fee-esrd-monthly-capitation-payments/
    — accessed 2026-09-26 — moderate-high confidence.
18. Gaia Software — Dialysis Billing — https://gaiasoftware.com/dialysis-billing/
    — accessed 2026-09-26 — vendor marketing, low-medium confidence.
19. Gaia Software — homepage — https://gaiasoftware.com/ — accessed
    2026-09-26 — vendor marketing, low-medium confidence.
20. MIQS — Overview — http://www.miqs.com/overview — accessed 2026-09-26 —
    vendor marketing, low-medium confidence.
21. MIQS — Financial/Billing — http://www.miqs.com/financial — accessed
    2026-09-26 — vendor marketing, low-medium confidence.
22. Healio — "MIQS releases stand-alone dialysis billing software" —
    https://www.healio.com/news/nephrology/20180227/miqs-releases-standalone-dialysis-billing-software
    — accessed 2026-09-26 — trade news, moderate-high confidence.
23. Renal Billing — homepage — https://www.renalbilling.com/ — accessed
    2026-09-26 — unverified, snippet only, low confidence.
24. Transonic — "Fresenius and DaVita Capture 84% of U.S. Hemodialysis
    Market" — https://blog.transonic.com/hemodialysis/fresenius-and-davita-hemodialysis-market
    — accessed 2026-09-26 — moderate confidence.
25. PMC — "Stakeholder Theory and For-Profit Dialysis: A Call for Greater
    Accountability" — https://pmc.ncbi.nlm.nih.gov/articles/PMC10564339/ —
    accessed 2026-09-26 — peer-reviewed, high confidence.
26. Managed Healthcare Executive — "Dialysis Industry Is Now the Most
    Concentrated in Healthcare" —
    https://www.managedhealthcareexecutive.com/view/dialysis-industry-is-now-the-most-concentrated-in-healthcare-study-finds-with-prices-far-higher-in-monopoly-areas
    — accessed 2026-09-26 — moderate-high confidence.
27. CIO.com — "DaVita's technology strategy driven by the 'power of
    purpose'" — https://www.cio.com/article/416120/davitas-technology-strategy-driven-by-the-power-of-purpose.html
    — accessed 2026-09-26 — trade press, moderate confidence; no specific
    named billing system found.
28. Flatiron Health — OncoEMR product page —
    https://flatiron.com/oncology/oncology-ehr — accessed 2026-09-26 —
    vendor marketing, low-medium confidence.
29. CMS — JW and JZ Modifier Billing Guidelines (A55932) —
    https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleid=55932
    — accessed 2026-09-26 — primary regulatory source, high confidence.
30. Droidal — "J-Code Billing Guide 2026" —
    https://droidal.ai/blog/j-code-billing-guide-2026/ — accessed
    2026-09-26 — moderate confidence.
31. Ontada — iKnowMed point-of-care page —
    https://www.ontada.com/point-of-care-solutions/iknowmed/ — accessed
    2026-09-26 — vendor marketing, low-medium confidence.
32. IntuitionLabs — iKnowMed profile —
    https://intuitionlabs.ai/software/oncology-specific-ehremr/integrated-oncology-ehr-platforms/iknowmed
    — accessed 2026-09-26 — third-party analysis, moderate confidence.
33. AmerisourceBergen — "AmerisourceBergen Acquires IntrinsiQ, LLC" —
    https://investor.amerisourcebergen.com/news/news-details/2011/AmerisourceBergen-Acquires-IntrinsiQ-LLC/default.aspx
    — accessed 2026-09-26 — primary corporate source, high confidence.
34. EHR Source — "ARIA Oncology Information System EHR Review" —
    https://www.ehrsource.com/vendors/aria-oncology/ — accessed
    2026-09-26 — third-party review, moderate confidence.
35. BioSpace — "Fuse Oncology Announces Partnership With Elekta" —
    https://www.biospace.com/press-releases/fuse-oncology-announces-partnership-with-elekta
    — accessed 2026-09-26 — press release, moderate confidence.
36. Oncology News Central — "Nearly 9 in 10 Cancer Patients Experience
    Prior Authorization" — https://www.oncologynewscentral.com/oncology/nearly-9-in-10-cancer-patients-experience-prior-authorization
    — accessed 2026-09-26 — moderate-high confidence.
37. PMC — "The Promise and Perils of Oncology Care in Medicare Advantage" —
    https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12120503/ — accessed
    2026-09-26 — peer-reviewed, high confidence.
38. Flatiron Health — "Candid Health and Flatiron Health Partner to Bring
    Revenue Cycle Management to Oncology Practices" —
    https://resources.flatiron.com/press/candid-health-and-flatiron-health-partner-to-bring-revenue-cycle-management-to-oncology-practices
    — accessed 2026-09-26 — primary press release, high confidence for the
    partnership fact; framing language is vendor-authored.

---

## 4. Denial management, payer-specific rules, and the credibility of AI-accuracy claims

**AI-drafted appeal letters — SAIRNcode's built A4 feature — are now table
stakes, not a differentiator.** Waystar's AltitudeCreate generates appeals
from a library covering 1,100+ payer-specific templates; AKASA's AI Advisor
drafts appeals from chart context; R1 RCM's Phare platform drafts and files
appeals, targeting near-40%-of-denied-dollars full automation by end of
2025. **All three describe letting some share of appeals go out with no
human ever reviewing them** — a materially more aggressive automation
posture than SAIRNcode's mandatory-review-on-every-appeal design. This
means SAIRNcode's A4 feature should be understood as parity, not a lead-with
claim, in this specific comparison.

**On the sharper question — does the market publish the exact
denial-probability percentage SAIRNcode refused to build — the answer is
yes, and this is the most important finding in this section.** Experian
Health's AI Advantage scores each claim's probability of denial and,
separately, the probability an appeal will succeed. Inovalon's model
"estimate[s] how likely a claim is to be denied before it is submitted."
Waystar's engine "scores denials by estimated overturn probability."
**None of this vendor material — product pages, press releases, vendor
blogs — discloses a calibration methodology**: no reliability diagram, no
Brier score, no stated validation cohort, no confidence interval on the
percentage itself. One academic study of denial-prediction modeling reports
an AUC of 0.83 for its best model — a discrimination metric (ranking
ability), not a calibration metric (whether a stated "34%" reflects an
empirical 34% frequency) — and it is general academic literature, not a
disclosed validation of any specific vendor's live production score.
**Shipping the percentage is the market norm; disclosed calibration is
absent everywhere this research looked. SAIRNcode's refusal is the outlier
here, not standard practice** — but see below for why that outlier position
looks principled rather than merely cautious.

**Real, serious independent scrutiny of exactly this category of claim
exists — one layer over, on the payer side, where similar AI techniques are
used to issue denials rather than manage or appeal them.** ProPublica's
investigation of Cigna's PxDx system found the insurer's algorithm-driven
batch review let medical directors deny roughly 300,000 claims over two
months at about 1.2 seconds of review per claim, without opening patient
files — reporting that triggered a Congressional inquiry and multiple
lawsuits. A STAT News investigation, now central to active federal
litigation, alleges UnitedHealth/NaviHealth's nH Predict algorithm was used
to cut off post-acute care, citing a KFF analysis finding roughly 90% of
internally-appealed nH-Predict-driven denials were overturned, while only
about 0.2% of affected enrollees ever appealed at all (litigation-alleged
figures, not independently adjudicated in this pass, but discovery was
still being actively compelled by a federal magistrate as of March 2026).
Stanford researchers (Mello et al., *Health Affairs*, January 2026)
concluded that "institutional governance by insurers and providers has not
fully met the challenge of ensuring responsible use" of these systems,
citing opacity, automation bias, and insufficient reviewer time. **This is
real, current, credible evidence that the exact category of claim SAIRNcode
declined to make — an AI-generated probability presented with implied
confidence — is facing serious independent scrutiny industry-wide right
now.** SAIRNcode's engineering decision reads, in light of this research, as
a defensible, well-timed position rather than a competitive gap, and it is
fair to describe it that way externally.

**Payer-specific rule engines are a real, marketed category, concretely
documented mainly for the largest national payers.** Availity's Essentials
Pro, Optum's ClaimsXten-based editors, and R1's Phare all describe learned
or configured payer-specific claim editing; the concrete named examples
everywhere are UnitedHealthcare, Anthem/Elevance, Aetna, Cigna, and
Medicare/Medicaid. No vendor publishes a specific count of individually
-modeled payer rule sets — scale claims are expressed as payer-connectivity
or training-data volume, not documented rule-by-rule coverage.

**The scale of the underlying problem is real and worth carrying into any
pitch**: Experian Health's 2025 survey found an industry-wide initial denial
rate of 11.8% (up from ~10.2% a few years prior), with 41% of providers
reporting more than 10% of claims denied. ACA marketplace plans hit a 19–20%
denial rate in 2024 — yet fewer than 1% of denials were appealed. In
Medicare Advantage, insurers made 52.8 million prior-authorization
determinations in 2024, denying 4.1 million (7.7%), but only 11.5% of those
denials were ever appealed, even though 80.7% of appeals succeeded. The
American Hospital Association's 2025 "Costs of Caring" report puts hospital
spending fighting denials and prior authorization at $43 billion. **One
structural observation worth stating plainly as this document's own
inference, not a claim any source made directly**: because so few denials
are ever appealed (under 15% in every dataset found here, closer to 1% in
ACA marketplace plans, 0.2% in the litigated Medicare Advantage subset), any
model trained or validated against "what happened when this was appealed"
is learning from a small, self-selected slice of cases — a real calibration
obstacle independent of algorithm quality, and one no vendor material
reviewed addresses.

### Sources (§4)

1. Waystar — "Denial + Appeal Management" —
   https://www.waystar.com/our-platform/denial-prevention-recovery/denial-appeal-management/
   — accessed 2026-09-26 — vendor claim.
2. Waystar — "Waystar unveils transformative generative AI innovation..."
   — https://www.waystar.com/news/announcing-generative-ai/ — accessed
   2026-09-26 — vendor claim.
3. Waystar blog — "Powerful AI: Examining results of Waystar AltitudeAI in
   RCM" — https://waystar.com/blog-powerful-ai-examining-results-of-waystar-altitudecreate-in-rcm
   — accessed 2026-09-26 — vendor claim.
4. AKASA — "AI Advisor" — https://akasa.com/solutions/ai-advisor/ —
   accessed 2026-09-26 — vendor claim.
5. RevCycleAI — "Akasa Review" — https://revcycleai.com/blog/akasa-vendor-deep-dive/
   — accessed 2026-09-26 — independent trade analysis, moderate
   confidence.
6. R1 RCM — "Denials Management" — https://www.r1rcm.com/solutions/denials-management
   — accessed 2026-09-26 — vendor claim.
7. R1 RCM — "R1 Launches Phare..." — https://www.r1rcm.com/newsroom/r1-launches-phare-healthcare-s-first-revenue-operating-system
   — accessed 2026-09-26 — vendor claim, corroborated by Hospitalogy —
   https://hospitalogy.com/articles/2026-07-13/the-revenue-cycle-has-an-infrastructure-problem-r1-built-the-os-to-solve-it/
   — accessed 2026-09-26.
8. Experian Health blog — "AI Advantage™: Transforming claim denials
   management" — https://www.experian.com/blogs/healthcare/ai-advantage-transforming-claim-denials-management/
   — accessed 2026-09-26 — vendor claim.
9. Inovalon blog — "AI in Healthcare Claims Processing" —
   https://www.inovalon.com/blog/ai-in-healthcare-claims-processing-best-practices-to-predict-and-prevent-denials/
   — accessed 2026-09-26 — vendor claim.
10. IRCM blog — "How Predictive Denial Tools Are Reducing Claim Denials by
    30–40%" — https://ircm.com/blog/how-predictive-denial-tools-cut-claim-denials/
    — accessed 2026-09-26 — low confidence, unattributed "87% accuracy"
    figure with no stated methodology.
11. Exploration Pub — "Use of responsible artificial intelligence to
    predict health insurance claims..." — https://www.explorationpub.com/Journals/edht/Article/10119
    — accessed 2026-09-26 — academic source; AUC=0.83 is a discrimination
    metric, not calibration.
12. Availity — "Denial Prevention & Management" —
    https://www.availity.com/denial-prevention-and-management/ — accessed
    2026-09-26 — vendor claim.
13. HIT Consultant — "Availity Launches AI-Powered Claims Denial Prediction
    Tool" — https://hitconsultant.net/2024/04/05/availity-launches-ai-powered-claims-denial-prediction-tool/
    — accessed 2026-09-26 — trade press relaying vendor claim.
14. Optum — "Comprehensive Denial Prevention" —
    https://business.optum.com/en/operations-technology/payment-integrity/claim-editing/comprehensive-denial-prevention.html
    — accessed 2026-09-26 — vendor claim.
15. Optum — "Real Edit Intelligence" —
    https://business.optum.com/en/operations-technology/payment-integrity/claim-editing/real-edit-intelligence.html
    — accessed 2026-09-26 — vendor claim.
16. Healthcare Finance News — "Optum Real, Microsoft partner on AI for
    claims and reimbursement" — https://www.healthcarefinancenews.com/news/optum-real-microsoft-partner-ai-claims-and-reimbursement
    — accessed 2026-09-26 — trade press relaying an unaudited vendor
    -reported pilot result.
17. ProPublica — "Cigna PxDx medical health insurance rejection claims" —
    https://www.propublica.org/article/cigna-pxdx-medical-health-insurance-rejection-claims
    — accessed 2026-09-26 — primary investigative journalism, high
    confidence.
18. Healthcare Dive — "Cigna sued over algorithm allegedly used to deny
    claims" — https://www.healthcaredive.com/news/cigna-lawsuit-algorithm-claims-denials-california/688857/
    — accessed 2026-09-26 — corroborating trade press.
19. CBS News — "UnitedHealth uses faulty AI to deny elderly patients
    medically necessary coverage, lawsuit claims" —
    https://www.cbsnews.com/news/unitedhealth-lawsuit-ai-deny-claims-medicare-advantage-health-insurance-denials/
    — accessed 2026-09-26 — reports on active litigation, allegations not
    adjudicated fact.
20. Becker's Payer Issues — "Judge orders UnitedHealth to hand over
    documents in AI coverage denial case" —
    https://www.beckerspayer.com/legal/judge-orders-unitedhealth-to-hand-over-broad-discovery-in-ai-coverage-denial-case/
    — accessed 2026-09-26 — confirms litigation active as of March 2026.
21. Health Affairs Forefront — "Best Practices For AI In Health Insurance
    Claims Adjudication and Decision-Making" —
    https://www.healthaffairs.org/content/forefront/best-practices-ai-health-insurance-claims-adjudication-and-decision-making
    — accessed 2026-09-26 — independent academic/policy commentary, high
    confidence.
22. Stanford Report — "AI-driven insurance decisions raise concerns about
    human oversight" — https://news.stanford.edu/stories/2026/01/ai-algorithms-health-insurance-care-risks-research
    — accessed 2026-09-26 — independent academic reporting, high
    confidence.
23. AAPC Knowledge Center — "Taking a Stand Against AI Denials" —
    https://www.aapc.com/blog/93960-taking-a-stand-against-ai-denials/ —
    accessed 2026-09-26 — trade-association commentary, moderate-high
    confidence.
24. Experian PLC — "Experian Health's 3rd Annual State of Claims Survey" —
    https://www.experianplc.com/newsroom/press-releases/2025/experian-health-s-3rd-annual-state-of-claims-survey-finds-denial
    — accessed 2026-09-26 — vendor-commissioned survey, moderate
    confidence (self-reported).
25. HFMA — "ACA marketplace plans see highest denial rate in nine years" —
    https://www.hfma.org/fast-finance/aca-marketplace-plans-payment-denial/
    — accessed 2026-09-26 — trade press reporting KFF data, high
    confidence.
26. KFF — "Claims Denials and Appeals in ACA Marketplace Plans in 2024" —
    https://www.kff.org/patient-consumer-protections/claims-denials-and-appeals-in-aca-marketplace-plans-in-2024/
    — accessed 2026-09-26 — primary source, fetch blocked, sourced via
    search-indexed snippets and corroborating trade press.
27. KFF — "Medicare Advantage Insurers Made Nearly 53 Million Prior
    Authorization Determinations in 2024" —
    https://www.kff.org/medicare/medicare-advantage-insurers-made-nearly-53-million-prior-authorization-determinations-in-2024/
    — accessed 2026-09-26 — primary source, high confidence.
28. AOL — coverage of the KFF Medicare Advantage report —
    https://www.aol.com/articles/advantage-plans-said-no-4-153036000.html —
    accessed 2026-09-26 — corroborating secondary reporting.
29. TechTarget — "AHA: Hospitals spent $43B chasing pay from denials, prior
    auths" — https://www.techtarget.com/revcyclemanagement/news/366640113/AHA-Hospitals-spent-43B-chasing-pay-from-denials-prior-auths
    — accessed 2026-09-26 — trade press reporting AHA's "Costs of Caring"
    report, high confidence.
30. Becker's Hospital Review — "The link between care denials and
    increasing administrative costs: AHA" —
    https://www.beckershospitalreview.com/finance/the-link-between-care-denials-and-increasing-administrative-costs-aha/
    — accessed 2026-09-26 — corroborating trade press.
31. American Hospital Association — "Payer Denial Tactics — How to
    Confront a $20 Billion Problem" — https://www.aha.org/aha-center-health-innovation-market-scan/2024-04-02-payer-denial-tactics-how-confront-20-billion-problem
    — accessed 2026-09-26 — primary source, a separate/earlier (2024)
    figure from source 29 — not the same metric, not to be conflated.

---

## 5. Synthesis — what actually changed, and what looks better than expected

1. **The internal audit's "largest gap" is now precisely quantified, not
   just named.** CodaMetrix and Nym Health are real, well-funded, customer
   -validated (via KLAS interviews) products already serving the exact
   named hospital systems the internal audit cited. This is a real,
   serious, and now externally corroborated gap, not a hypothetical one.
2. **SAIRNcode's principled refusal to fabricate a denial-probability score
   looks better, not worse, in light of this research.** Real competitors
   ship the exact percentage SAIRNcode declined to build, and none discloses
   how it's calibrated — while the closest real-world analog (AI-driven
   denial decisions on the payer side) is under active, credible,
   independent scrutiny right now: a ProPublica investigation, active
   federal litigation, a GAO warning, and a state Attorney General settlement
   finding a health-AI company's self-reported accuracy metric "likely
   inaccurate." This is a genuine, well-evidenced, current validation of an
   internal engineering decision, and it is fair and honest to describe it
   to a buyer that way.
3. **The citation-trail explainability differentiator (A5) is still real,
   but Nym Health is now the one competitor that could credibly claim
   something similar.** The one specific, checkable fact that would resolve
   whether SAIRNcode's verbatim-quote mechanism is still ahead — Nym's
   actual evidence-linkage granularity — could not be confirmed in this
   pass and needs a direct-access follow-up before it's stated as settled
   either way.
4. **The GP-modifier gap is real, narrow, and the chiropractic-competitor
   research reinforces exactly why it matters**: real competitors treat
   this class of modifier logic (the analogous AT modifier) as a first
   -class, clinically-integrated feature, and an OIG audit found 82% of
   Medicare chiropractic payments unallowable largely from this exact
   failure mode. This is a small, well-scoped, high-value fix, not a
   speculative one.
5. **Dialysis/ESRD's competitive weight should be recalibrated downward,
   honestly.** With ~80% of the market walled off by DaVita/Fresenius
   vertical integration, SAIRNcode's ESRD module's real competitive set is
   two small specialists (MIQS, Gaia), not the broader coding-software
   market — this doesn't make the module less correct, but it does mean it
   shouldn't be expected to carry much competitive weight in a sales
   conversation.
6. **Oncology shows a real, structural opening worth naming as an
   opportunity, not deciding here**: even Flatiron, the dominant
   EHR-embedded oncology billing product, has concluded its own embedded
   billing isn't sufficient and bought in outside RCM automation. A
   correctly-built, standalone coding layer for oncology's J-code/waste
   -modifier/prior-auth complexity is a real, evidenced gap in the market —
   not proof SAIRNcode should build toward it, but a genuine signal worth
   carrying forward.

---

## 6. What this document does not establish or decide

- **No claim in this document should be quoted externally** — to a health
  system, a prospect, or in a proposal — without a follow-up read from a
  network that can reach the underlying primary sources, including
  GAO.gov and KFF.org, which this pass could not open directly (§0.1).
- **This document does not decide whether or how SAIRNcode should build
  autonomous coding, close the GP-modifier gap, or pursue oncology's
  bolt-on RCM opportunity** — that is a `sairn-software-architect` /
  `sairn-decision-gate` question, consistent with how the internal
  2026-09-23 audit treats its own findings.
- **It does not resolve whether Nym Health's explainability feature
  matches SAIRNcode's verbatim-quote granularity** — flagged in §2 as
  genuinely undetermined and worth a direct follow-up check.
- **It does not verify AT-modifier or medical-necessity logic correctness**
  inside SAIRNcode's own chiropractic panel, or the depth of SAIRNcode's
  eight enterprise RCM panels, or its EHR interoperability — all three
  remain exactly as unmeasured as the internal 2026-09-23 audit left them.
- **It does not adjudicate any of the litigation or regulatory matters
  cited in §2 and §4** (the Pieces Technologies settlement, the
  UnitedHealth/nH Predict and Cigna/PxDx lawsuits) — these are reported as
  real, current, sourced context, not resolved legal conclusions.

## 7. Decay

Every source above is a search-index snapshot from 2026-09-26. Several
things in this document are unusually likely to move soon: Solventum's
Health Information Systems separation (§1, a 12–18 month process just
announced), the UnitedHealth/nH Predict litigation and discovery (§4, active
as of March 2026), and the broader autonomous-coding adoption figures (§2 —
AMA's 21%→28% two-year trend suggests this category is still moving
quickly). The regulatory material cited (CMS billing rules, the ESRD PPS
rate, CPT/ICD-10 update cycles) is far more stable. **Do not treat any
accuracy claim, adoption figure, litigation status, or corporate-ownership
fact here as current without re-checking directly against the live
source.**
