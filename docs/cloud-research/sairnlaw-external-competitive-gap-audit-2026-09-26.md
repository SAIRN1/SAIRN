# SAIRNlaw external competitive-gap audit — jurisdiction/deadline engines, citator parity, client portals, sensitive-data handling (2026-09-26)

**Research pass, 2026-09-26. No code, no claims, no tier registers touched —
new file only, under `docs/cloud-research/`, on its own branch, same lane as
the SOC2/SAIRNvet/StoneDesk/Novaclad research already in this directory.**

---

## 0. Scope, and a correction to "no fresh external competitor audit exists"

The task brief for this pass stated "no fresh external competitor audit
exists for this vertical." That is not correct, and per this platform's own
verify-before-report rule the actual state is worth stating precisely:
**`docs/cloud-research/SAIRNlaw-external-competitive-gap-audit-2026-09-25.md`
already exists**, written the previous day, and it is thorough — it covers
SAIRNlaw's billing-operations competitors (Clio, MyCase, PracticePanther,
CosmoLex, Smokeball, TimeSolv, Bill4Time, LeanLaw, Centerbase, Rocket
Matter, Tabs3, Aderant, Intapp) in real depth across six confirmed gaps
(LEDES export, ambient time capture, rate cards, origination credit,
outside-counsel guidelines, and role/permission depth), and separately
validates SAIRNlaw's trust-accounting three-way reconciliation as **table
stakes, correctly implemented — not a gap and not a differentiator** — and
flags its intake conflict-of-interest blocking override as a genuine
candidate differentiator pending further verification.

**This document does not re-derive any of that.** It covers the four
angles the task brief actually asked for that the existing audit did not
touch: multi-jurisdiction deadline/court-rules engine depth (SAIRNlaw's own
named core differentiator), citator/case-law research parity, client-portal
feature depth, and sensitive-data handling in legal practice-management
software generally — with a light pricing spot-check folded into the last
section rather than a full re-survey.

**The headline finding across the first two sections is not comfortable,
and it is stated plainly rather than softened**: both of the two features
this task's brief calls out as SAIRNlaw's core differentiators — the
deadline engine and the citator — turn out to already be matched or
exceeded, on real evidence, by at least one well-funded named competitor.
That does not mean SAIRNlaw's implementation is bad. It means the
competitive claim needs to be about *what specifically differs* (native
integration, pricing, the US+UK combination) rather than *exclusivity*,
and §5 states that distinction directly.

### 0.1 A network-egress caveat that applies to every section below

As with every research pass run from this environment, outbound `WebFetch`
(full-page retrieval) returned `EGRESS_BLOCKED` for essentially every
vendor, trade-press, and reference domain attempted — vendor sites, LawSites
(lawnext.com), ABA Journal, Above the Law, americanbar.org, and others.
This was confirmed environment-wide, not domain-specific. Every finding
below therefore rests on `WebSearch`'s indexed **excerpt** of a page, not an
independently opened full read. Confidence flags per claim reflect this.
**Nothing pricing-specific, capability-specific, or legally load-bearing
below should be quoted externally — to a firm, a prospect, or in a
proposal — without a follow-up read from a network that can reach these
domains.**

---

## 0.2 Internal grounding, and a correction on the privacy question specifically

**Citator and deadline engine are confirmed real and substantial** — nearly
100 combined markers for citator/deadline-engine/client-portal identifiers
were found directly in `sairnlaw.html` and `api/_lib/deadline-engine.js`, a
volume consistent with the task brief's description (269 rules across
24-29+ jurisdictions, US + UK England/Wales). This document does not
re-verify the exact rule count or re-litigate whether these features work —
per the task's own instruction, that ground is treated as already
established internally, not re-audited here.

**The privacy question needs a real correction before this document's §4
can be read accurately.** The task brief frames the open privacy question
as being about "family law/immigration case files as PII-heavy as health
data." An existing internal document
(`docs/2026-09-15-sairnlaw-privacy-scoping.md`, dated 2026-09-15, read
directly against the schema, not assumed) already answered a more specific
and different question: **SAIRNlaw does not model family law or immigration
as distinct practice areas at all.** The `practice_area` field is free
text with no validation, no enumerated option list, and no `MATTER_TYPES`
constant; a direct search of the app and the deadline engine for
`divorce`, `dissolution`, `child support`, `immigration`, `USCIS`, `I-130`,
`I-485`, and `N-400` returned **zero hits for every term**. The one
apparent signal (`custody`, 7 hits) resolved entirely to "AI Chain of
Custody," an unrelated audit-trail feature, not child custody. That
document's own conclusion is worth restating precisely because it reframes
what "sensitive" means for SAIRNlaw specifically: **the real, confirmed,
practice-area-independent sensitive resource is `law_pimedical` —
personal-injury medical records** — plus trust/operating financial data,
client identifiers, and portal communications/signatures. Family law and
immigration would each add sensitivity *if* a firm using SAIRNlaw happened
to practice them, but SAIRNlaw has no way to know or enforce that, and the
2026-09-15 document explicitly recommends dropping the practice-area
framing rather than trying to answer an unanswerable question.

**That internal document also explicitly states what it does not do**: "It
does not map controls to Privacy criteria P1–P8. That is the SOC 2
readiness work... A P1–P8 mapping written here would be the first half of a
compliance document with no second half." That mapping work is, as of this
research pass, a separate, actively claimed task by another session on this
platform. **This document does not touch, resolve, or duplicate that work.**
§4 below is scoped strictly to external market research — how the legal-tech
industry handles sensitive case data generally, and specifically around
personal-injury medical records (SAIRNlaw's actual, confirmed sensitive
resource) and, separately, family-law/immigration data (the task brief's
original hypothesis, reported honestly even though it doesn't map cleanly
onto SAIRNlaw's current architecture).

---

## 1. Multi-jurisdiction deadline and court-rules engines

**Clio is a real, native, larger-scale competitor on this exact axis, and
has been since 2021.** Clio acquired CalendarRules outright in July 2021
and ships it as a native "Court Rules" feature — not a bolt-on integration —
available on its Essentials/Advanced/Complete plans. Clio's own materials
describe coverage of all 50 U.S. states and, depending on which page is
read (a real internal inconsistency in Clio's own materials, not resolvable
without a direct fetch), roughly 2,200–2,300 jurisdictions/rule sets — a
larger number than SAIRNlaw's 269 rules across 24-29+ jurisdictions, though
no vendor in this category publishes a rule-count granular enough for a
true rule-for-rule comparison, so this is a jurisdiction/court-count
comparison, not an apples-to-apples one. Clio does also claim UK and
Australian coverage, but explicitly calls it **"a limited set of
conveyancing rule sets"** — property-transaction timelines, not general
civil-procedure/litigation deadlines, which matters directly for §1's UK
finding below.

**MyCase, PracticePanther, and Smokeball do not build their own engine —
they resell LawToolBox**, a real, independent, Microsoft-365-native
specialist product (Outlook/Teams/SharePoint/OneNote integration) marketing
"thousands of jurisdictions" across the US, Canada, and internationally,
priced roughly $35–42/user/month at small seat counts down to $18–25/user
at scale, with a minimum one-year term. MyCase added the integration in
October 2022; PracticePanther's tier is capped free (5 calculations) or
paid (20 rule-sets/20 jurisdictions); Smokeball lists it as a marketplace
partner. This is exactly the pattern the task brief anticipated: a
third-party add-on a firm buys and connects separately, with the
practice-management vendor as distribution channel, not the rules owner.
**CosmoLex shows no evidence of either a native or integrated rules
engine** — its calendaring is described as manual event creation with
reminders.

**The specialist category is older and larger than the practice-management
layer, and is the real benchmark.** Beyond LawToolBox: **CompuLaw**, a
long-standing court-rules product acquired by **Aderant** in 2011 (Aderant
already appears in the sibling audit's billing-competitor list — worth
flagging as a direct cross-reference, since Aderant now competes with
SAIRNlaw on both the billing and the deadline-engine axis), claims
2,500–3,000+ US jurisdictions and was modernized into a new cloud product,
**Milana**, in October 2022, while CompuLaw continues to be sold separately.
Aderant also runs **Deadlines.com**, a CompuLaw-powered offering aimed at
smaller firms, at roughly $35/case/month for one active case. **Westlaw
Legal Calendaring / Deadline Assistant** (Thomson Reuters, inside Firm
Central) is a fourth real, named, attorney-editor-maintained rules engine
claiming coverage of "virtually all federal and state courts" plus major
arbitration/IP tribunals.

**Immigration is a structurally different, single-jurisdiction problem, and
every signal treats it as a complement rather than a rival.** **Docketwise**
is real and immigration-specific (USCIS/EOIR filing-type deadlines), but
immigration deadlines are federal and don't vary state-by-state, so it is
not a "multi-jurisdiction rules engine" in SAIRNlaw's sense. Its ownership
confirms the complement framing: Docketwise → acquired by MyCase (May 2022)
→ MyCase's parent AffiniPay rebranded as **8am** (August 2025) with
Docketwise as one sibling product alongside MyCase and the personal-injury
-specific CasePeer — and Clio separately sells its own Clio-Docketwise
integration rather than treating it as competitive.

**On the specific US+UK combination SAIRNlaw claims, the evidence supports
treating it as genuinely unusual — the one place this section's findings
run in SAIRNlaw's favor.** Clio's UK coverage is conveyancing-only, as
above. Two UK general practice-management vendors (LawWare, PracticeEvolve)
show generic calendaring with no dedicated court-rules engine found. The one
real, dedicated UK specialist located, **Deadline Engine**
(deadlineengine.com), is genuinely deep — non-AI, rule-encoded from statutory
materials, covering CPR civil claims, employment, family, criminal, judicial
review, tax tribunal, immigration, the FCA Handbook, planning,
landlord-tenant, insolvency, company law, and construction, with clear-day
counting and bank-holiday handling — but it is England & Wales only, with no
US coverage. **No product combining deep US state-by-state coverage with
comparably deep UK CPR-wide coverage was found anywhere in this pass.**
Given the near-total network block, this should be read as "not found in
this pass," not a certified negative — but on the visible evidence,
SAIRNlaw's claimed US+UK combination at real depth on both sides looks like
the genuinely rare part of its differentiator, even though the single
-country deadline-engine claim does not hold up as unique.

**Why it matters, with real numbers and real caveats**: missed deadlines
are reported, via secondary trade-press citation of ABA Standing Committee
on Lawyers' Professional Liability data (2020–2023), as the largest single
category of legal malpractice claims at roughly 24.6%, ahead of substantive
errors (18.3%). A malpractice insurer's own claims data (TLIE, 1996–99, also
reached only via secondary citation) splits the failure into "never
calendared" (7.03% of claims) versus "calendared but failed to act" (1.27%).
A widely-repeated "34%" figure traces to a LawToolBox marketing PDF and
should be treated as vendor-interested rather than independent. No
immigration-specific (EOIR/USCIS) missed-deadline malpractice statistic was
found anywhere.

### Sources (§1)

1. LawToolBox — Deadline Calculator —
   https://lawtoolbox.com/deadline-calculator/ — accessed 2026-09-26 —
   vendor marketing, snippet only.
2. LawToolBox — Legal Deadline Calculator (M365) —
   https://lawtoolbox.com/legal-deadline-calculator/ — accessed 2026-09-26
   — vendor marketing, snippet only.
3. LawToolBox — Pricing — https://lawtoolbox.com/pricing/ — accessed
   2026-09-26 — vendor page, cross-cited by third-party aggregators
   (GetApp, ITQlick), moderate confidence.
4. LawToolBox — Partner/Ruleset Pricing —
   https://lawtoolbox.com/partner-pricing/ — accessed 2026-09-26 — vendor
   page, snippet only.
5. PitchBook — CompuLaw company profile —
   https://pitchbook.com/profiles/company/25200-28 — accessed 2026-09-26 —
   third-party financial-data aggregator, moderate-high confidence on
   ownership facts.
6. LawSites — "Aderant Unveils Cloud Docketing Product that Combines
   CompuLaw with American LegalNet" —
   https://www.lawnext.com/2022/10/aderant-unveils-cloud-docketing-product-that-combines-compulaw-with-american-legalnet.html
   — accessed 2026-09-26 — independent trade press, high confidence.
7. Aderant — CompuLaw solutions page —
   https://www.aderant.com/solutions-compulaw/ — accessed 2026-09-26 —
   vendor source, jurisdiction-count claim varies across renderings.
8. Aderant — Milana solutions page —
   https://www.aderant.com/solutions-milana/ — accessed 2026-09-26 —
   vendor marketing, snippet only.
9. Deadlines.com — https://www.deadlines.com/ — accessed 2026-09-26 —
   vendor page, snippet only; pricing via third-party aggregator, medium
   -low confidence.
10. Clio — Court Rules Help Center —
    https://help.clio.com/hc/en-us/articles/9289840995867-Court-Rules —
    accessed 2026-09-26 — primary vendor documentation, jurisdiction count
    inconsistent across renderings, flagged.
11. Clio blog — "Master Court Deadlines with Rules-Based Legal Calendaring
    Software" — https://www.clio.com/blog/rules-based-calendaring-software-law-firms/
    — accessed 2026-09-26 — vendor marketing, snippet only.
12. Clio press release — CalendarRules acquisition —
    https://www.clio.com/about/press/calendarrulesacquisition/ — accessed
    2026-09-26 — primary company announcement, high confidence on the
    acquisition fact.
13. LawSites — "Clio Acquires CalendarRules" —
    https://www.lawnext.com/2021/07/clio-acquires-calendarrules-product-that-automates-calendaring-of-court-deadlines.html
    — accessed 2026-09-26 — independent trade press, high confidence.
14. Clio press release — Clio and CalendarRules integration —
    https://www.clio.com/about/press/clio-and-calendarrules-offer-new-integration-to-help-lawyers-better-manage-busy-law-firms-and-calendars/
    — accessed 2026-09-26 — vendor source, snippet only.
15. LawSites — "MyCase Now Integrates with LawToolBox" —
    https://www.lawnext.com/2022/10/mycase-now-integrates-with-lawtoolbox-for-rules-based-court-calendaring.html
    — accessed 2026-09-26 — independent trade press, high confidence.
16. MyCase — LawToolBox integration page —
    https://www.mycase.com/integrations/lawtoolbox/ — accessed 2026-09-26 —
    vendor source, snippet only.
17. PracticePanther blog — LawToolBox integration announcement —
    https://www.practicepanther.com/blog/integration-with-lawtoolbox/ —
    accessed 2026-09-26 — vendor source, snippet only.
18. PracticePanther — Court Rules Integration FAQ —
    https://support.practicepanther.com/en/articles/1188276-court-rules-integration-faq
    — accessed 2026-09-26 — vendor documentation, source of the "20 rule
    -sets/20 jurisdictions" figure.
19. Smokeball Marketplace — LawToolBox partner page —
    https://marketplace.smokeball.com/partners/lawtoolbox — accessed
    2026-09-26 — vendor source, snippet only.
20. Smokeball Support — LawToolBox article —
    https://support.smokeball.com/hc/en-us/articles/6009518909847-LawToolBox
    — accessed 2026-09-26 — vendor documentation, snippet only.
21. CosmoLex — Legal Calendaring Software feature page —
    https://www.cosmolex.com/features/legal-calendaring-software/ —
    accessed 2026-09-26 — vendor source, snippet only.
22. CosmoLex Support — "Manage Calendar Event Reminders" —
    https://support.cosmolex.com/knowledge-base/manage-calendar-event-reminders/
    — accessed 2026-09-26 — vendor documentation, supports "manual
    reminder only" characterization.
23. Software Advice — Westlaw Legal Calendaring / Firm Central profile —
    https://www.softwareadvice.com/legal/westlaw-legal-calendaring-profile/
    — accessed 2026-09-26 — third-party review aggregator, moderate
    confidence.
24. LawSites — "Firm Central Gets Court Rules Calendaring" (2014) —
    https://www.lawnext.com/2014/07/firm-central-gets-court-calendaring.html
    — accessed 2026-09-26 — independent trade press, high confidence,
    historical.
25. Docketwise — "About Docketwise" — https://www.docketwise.com/llm-info/
    — accessed 2026-09-26 — vendor source, snippet only.
26. 8am — Docketwise product page — https://www.8am.com/docketwise/ —
    accessed 2026-09-26 — vendor source, snippet only.
27. LawSites — "AffiniPay... Rebrands As '8am'" —
    https://www.lawnext.com/2025/08/affinipay-parent-to-lawpay-mycase-and-others-rebrands-as-8am-to-signify-its-evolution-into-a-unified-professional-services-platform.html
    — accessed 2026-09-26 — independent trade press, high confidence.
28. MyCase blog — "MyCase Adds Docketwise to its Portfolio" —
    https://www.mycase.com/blog/general/mycase-adds-docketwise-to-its-portfolio/
    — accessed 2026-09-26 — vendor source, corroborates acquisition
    timeline.
29. Big Mode Consulting — "Clio vs Docketwise" comparison —
    https://www.bigmodeconsulting.com/compare/clio-vs-docketwise — accessed
    2026-09-26 — independent comparison site, not peer-reviewed, moderate
    confidence.
30. Clio App Directory — Docketwise integration —
    https://www.clio.com/app-directory/docketwise/ — accessed 2026-09-26 —
    vendor source, snippet only.
31. Deadline Engine — https://deadlineengine.com/ — accessed 2026-09-26 —
    vendor source; methodology claims specific and checkable.
32. Deadline Engine — Methodology page —
    https://deadlineengine.com/methodology — accessed 2026-09-26 — vendor
    source, snippet only.
33. LawWare — https://www.lawware.co.uk/ — accessed 2026-09-26 — vendor
    site, no dedicated deadline-calculator claim found.
34. PracticeEvolve — Case Management page —
    https://www.practiceevolve.com/case-management/ — accessed 2026-09-26 —
    vendor site, no dedicated rules-engine claim found.
35. Minnesota Lawyer — "Legal malpractice trends: ABA, EPIC, Lockton
    2020-2023" — https://minnlawyer.com/2025/10/21/legal-malpractice-trends-aba-epic-lockton-2020-2023/
    — accessed 2026-09-26 — independent trade press citing ABA data
    secondhand, moderate confidence.
36. WSBA NW Sidebar — "Risk Management by the Numbers" —
    https://nwsidebar.wsba.org/2020/10/22/risk-management-by-the-numbers-new-aba-study-on-malpractice-claims/
    — accessed 2026-09-26 — bar-association blog citing ABA data
    secondhand, moderate confidence.
37. TLIE — "Scheduling Errors and Legal Malpractice" —
    https://www.tlie.org/resource/scheduling-errors-and-legal-malpractice —
    accessed 2026-09-26 — malpractice insurer, independent of software
    vendors, moderate confidence.
38. LawToolBox marketing PDF — "LawToolBox Reduces the Risk of Missed
    Deadlines and Legal Malpractice" (2025) —
    https://lawtoolbox.com/wp-content/uploads/2025/09/LawToolBox-Reduces-the-Risk-of-Missed-Deadlines-and-Legal-Malpractice-2025.pdf
    — accessed 2026-09-26 — vendor marketing, low confidence, source of the
    "34%" figure, flagged as vendor-interested.
39. Plaintiff Magazine — "Missed deadlines will kill you" —
    https://plaintiffmagazine.com/recent-issues/item/missed-deadlines-will-kill-you-use-technology-to-stay-on-track
    — accessed 2026-09-26 — independent trade press; the "$750–1,000/month"
    figure is a single unverified data point, low confidence.

**Unresolved after this pass**: exact current jurisdiction/rule-set counts
for Clio Court Rules (2,200 vs. 2,300) and CompuLaw (2,500 vs. 3,000+)
could not be reconciled without direct site access; no vendor publishes a
rule-count as granular as SAIRNlaw's 269, so no rule-for-rule comparison is
possible from public data; no confirmation either way that LawToolBox's
library includes England & Wales civil procedure.

---

## 2. Citator and case-law research parity

**Clio's citator gap is not closed by paperwork — it owns a real, working,
shipped citator, confirmed across many independent trade-press sources, not
just its own marketing.** vLex is a real, previously-independent
legal-research and citator company with roughly 25 years of history,
merged with **Fastcase** (the bar-association-distributed US research
service, co-founded 1999) in April 2023, and claimed 1+ billion documents
from 100+ countries, already deployed at eight of the world's ten largest
law firms before Clio bought it. Clio signed the acquisition June 30, 2025
and closed it November 10, 2025 for roughly $1 billion, alongside a $500M
Series G at a $5B valuation. vLex has a real, specifically-named citator,
**"Vincent Cert,"** flagging negative treatment ("Overruled in," "Reversed
in," etc.) — functionally a Shepard's/KeyCite equivalent, though one
lower-confidence independent source claims its depth still trails
Westlaw/Lexis.

**Clio has genuinely shipped this to its own customers, not just kept it as
an unintegrated subsidiary.** Clio built two Clio-branded products on the
acquired assets — "Clio Library" (the research/document layer) and "Clio
Work" (an AI research/drafting/analysis workspace) — and Clio Work went
**standalone** (no Clio Manage subscription required) on April 21, 2026, at
$199/user/month. At the same time, vLex/Fastcase continues to be sold as a
separate product to the wider market, including free access through 80+ bar
associations — Clio did both, rather than fully merging or fully separating
the asset. This is not friction-free: Fastcase (now Clio's subsidiary) sued
a Toronto AI-legal-research company, Alexi Technologies, in December 2025
over a data-license dispute; Alexi countersued alleging the acquisition
violates US antitrust law, calling the combined database "one of only three
comprehensive primary-law databases of United States caselaw" — a disputed
litigation position, but independent, adversarial confirmation that outside
players view the combined Fastcase/vLex asset as tier-1 alongside
Westlaw/Lexis, headed to trial by mid-2026.

**Of the other nine named competitors, only Smokeball has anything
comparable, and it arrived via partnership rather than acquisition.** A
March 25, 2026 deal integrates Smokeball's practice-management platform
with Thomson Reuters' **CoCounsel Legal** (bundling Westlaw Advantage and
Practical Law), with Smokeball's own AI kept for firm-internal data and
CoCounsel/Westlaw supplying research via real-time document sync.
**CosmoLex** has an exclusive Casemaker integration dating to 2016, still
referenced as recently as April 2025, but it links research time-tracking
to matters with no evidence of citator-style "still good law" flagging.
**MyCase** has an older Fastcase connector for research-time tracking, but
its current AI push targets document summarization and drafting, not
case-law research. **PracticePanther, Rocket Matter, TimeSolv, Bill4Time,
LeanLaw, Centerbase, and Tabs3** — searched specifically — show **no
evidence of any citator, case-law-research, or legal-research-platform
integration at all.** This is a "nothing found" result rather than a
certified absence, but it was searched for directly and came up empty
across all seven.

**Is bundling case-law research into practice-management software a real
trend, or an outlier?** Real, named trade-press commentary (LawSites'
year-end retrospective) calls "platform convergence" — the collapse of
boundaries between practice management, research, document management, and
AI — one of the ten defining legal-tech themes of 2025, with Clio/vLex as
its centerpiece example, and the Smokeball/Thomson Reuters deal four months
later is a second, structurally different data point pointing the same
direction. But this should not be read as universal: of eleven vendors
examined (the nine named competitors plus Clio and the reference research
platforms), only two show real bundling, and Casetext's own trajectory cuts
the other way — Thomson Reuters retired it as a standalone product in April
2025 and now sells its AI successor only bundled *into* Westlaw, a research
incumbent absorbing an AI upstart upward rather than a practice-management
vendor absorbing research downward. **The honest read: real momentum at the
top of the market among the best-funded vendors, not yet evidence the long
tail is expected to follow** — which is directly relevant to how SAIRNlaw
should read its own competitive position, since it sits in that long tail
alongside seven of the nine vendors that show nothing on this axis.

**Untangling the M&A history, since it's genuinely tangled and easy to
misstate:** Fastcase (1999) merged with vLex (April 2023) → acquired by
Clio (November 2025). Separately, **Casetext** was acquired by Thomson
Reuters for $650M (closed August 2023) and retired as a standalone brand
in April 2025, folded into CoCounsel Legal (Westlaw-bundled only). A third,
older, unrelated thread: **Ravel Law** (Stanford-origin legal analytics) was
acquired by LexisNexis in 2017 and folded into Lexis Advance — the brand is
effectively retired. These are three separate ownership chains that share
no data or technology today; the two original dominant citators remain
**KeyCite** (Westlaw) and **Shepard's** (Lexis), with Bloomberg Law's
**BCite** as the most commonly cited third option, structurally distinct
from vLex's Vincent Cert.

### Sources (§2)

1. ABA Journal — "Clio completes $1B acquisition of vLex..." —
   https://www.abajournal.com/news/article/clio-completes-1b-acquisition-of-vlex-and-announces-5b-company-valuation
   — accessed 2026-09-26 — independent trade press, snippet only.
2. LawSites — "Clio Completes Historic $1 Billion vLex Acquisition..." —
   https://www.lawnext.com/2025/11/clio-completes-historic-1-billion-vlex-acquisition-announces-500-million-series-g-at-5-billion-valuation-plus-exclusive-interview-with-ceo-and-cfo.html
   — accessed 2026-09-26 — independent trade press (Bob Ambrogi), snippet
   only.
3. LawSites — "In A Mega Deal, Clio Buys vLex for $1 Billion..." —
   https://www.lawnext.com/2025/06/in-a-mega-deal-clio-buys-vlex-for-1-billion-merging-ai-research-and-practice-management.html
   — accessed 2026-09-26 — independent trade press, snippet only.
4. LawSites — "A Conversation with CEO Jack Newton on Clio's Acquisition of
   vLex" — https://www.lawnext.com/2025/06/a-conversation-with-ceo-jack-newton-on-clios-acquisition-of-vlex.html
   — accessed 2026-09-26 — independent trade press interview, snippet only.
5. Clio press release — "Clio Completes Landmark $1B vLex Acquisition..." —
   https://www.clio.com/about/press/clio-completes-landmark-1b-vlex-acquisition-series-g-5b-valuation/
   — accessed 2026-09-26 — vendor source, reliable for deal mechanics/dates.
6. vLex Library Knowledge Base — "Treatment types" / "Viewing Vincent
   Coverage by Jurisdiction" —
   https://support.vlex.com/document-types/case-law/treatment-types ,
   https://support.vlex.com/vincent-by-vlex/vincent/getting-started-with-vincent/viewing-vincent-coverage-by-jurisdiction
   — accessed 2026-09-26 — vendor technical documentation, snippet only.
7. LawSites — "...vLex's Vincent AI Adds Multi-Modal Capabilities..." (Feb
   2025) — https://www.lawnext.com/2025/02/exclusive-with-its-latest-release-out-today-vlexs-vincent-ai-adds-multi-modal-capabilities-litigation-workflows-and-coverage-for-four-new-countries.html
   — accessed 2026-09-26 — independent trade press, snippet only.
8. AI Vortex — "vLex Vincent AI: Legal Research Without Westlaw Lock-In" —
   https://www.aivortex.io/legal/ai-tools/vlex-vincent-ai/ — accessed
   2026-09-26 — independent blog, not major trade press, low confidence,
   single-source citator-depth comparison claim.
9. LawSites — "vLex and Fastcase Merge..." (2023) —
   https://www.lawnext.com/2023/04/in-major-legal-tech-deal-vlex-and-fastcase-merge-creating-a-global-legal-research-company-backed-by-oakley-capital-and-bain-capital.html
   — accessed 2026-09-26 — independent trade press, snippet only.
10. Law.com Legaltech News — "Fastcase Merges With vLex..." —
    https://www.law.com/legaltechnews/2023/04/04/fastcase-merges-with-vlex-with-plans-for-intergrated-ai-powered-research-offerings/
    — accessed 2026-09-26 — independent trade press, snippet only.
11. LawSites — "Alexi Fires Back at Fastcase Lawsuit with Counterclaims..."
    — https://www.lawnext.com/2026/01/alexi-fires-back-at-fastcase-lawsuit-with-counterclaims-alleging-anticompetitive-conduct-following-clios-1b-acquisition.html
    — accessed 2026-09-26 — independent trade press, snippet only.
12. LawSites — "Fastcase And Alexi Head To Court This Week..." —
    https://www.lawnext.com/2026/07/fastcase-and-alexi-head-to-court-this-week-in-high-stakes-fight-over-legal-ai-caselaw-data-and-clios-1b-vlex-deal.html
    — accessed 2026-09-26 — independent trade press, snippet only.
13. BusinessWire — "Alexi Files Counterclaims Against Clio and vLex..." —
    https://www.businesswire.com/news/home/20260116609508/en/Alexi-Files-Counterclaims-Against-Clio-and-vLex-Alleges-$1B-Merger-Created-Unlawful-Clog-on-Competition
    — accessed 2026-09-26 — wire-service litigation report; Alexi's
    characterizations are a disputed legal position.
14. LawSites — "Clio Work...Now Available To Solo and Smaller Law Firms As
    A Standalone Product" —
    https://www.lawnext.com/2026/04/clio-work-clios-ai-workspace-is-now-available-to-solo-and-smaller-law-firms-as-a-standalone-product.html
    — accessed 2026-09-26 — independent trade press, snippet only.
15. LawSites — "Fastcase Founder Ed Walters On the Implications of Clio's
    Acquisition of vLex" —
    https://www.lawnext.com/2026/01/on-lawnext-fastcase-founder-ed-walters-on-the-implications-of-clios-acquisition-of-vlex.html
    — accessed 2026-09-26 — independent trade press podcast, snippet only.
16. Artificial Lawyer — "Ed Walters on Clio's AI Capabilities After the
    vLex Deal" — https://www.artificiallawyer.com/2026/01/22/ed-walters-on-clios-ai-capabilities-after-the-vlex-deal/
    — accessed 2026-09-26 — independent trade press, snippet only.
17. Artificial Lawyer — "Clio's Jack Newton On The vLex 'Convergence' Deal"
    — https://www.artificiallawyer.com/2025/06/30/clios-jack-newton-on-the-vlex-convergence-deal/
    — accessed 2026-09-26 — independent trade press, snippet only.
18. LawSites — "The 10 Legal Tech Trends that Defined 2025" —
    https://www.lawnext.com/2026/01/the-10-legal-tech-trends-that-defined-2025.html
    — accessed 2026-09-26 — independent trade press, year-end analysis.
19. Above the Law — "Clio's Metamorphosis: From Practice Management To A
    Comprehensive AI And Law Practice Provider" —
    https://abovethelaw.com/2025/10/clios-metamorphosis-from-practice-management-to-a-comprehensive-ai-and-law-practice-provider/
    — accessed 2026-09-26 — independent trade press, snippet only.
20. National Magazine (Canadian Bar Association) — "How Clio's big moves in
    AI could affect legal practice" —
    https://www.nationalmagazine.ca/en-ca/articles/legal-market/legal-tech/2025/how-clio-s-big-moves-in-ai-will-affect-legal-practice
    — accessed 2026-09-26 — independent bar-association publication, low
    -moderate confidence, paraphrase only.
21. LawSites — "Exclusive: Smokeball and Thomson Reuters Partner..." —
    https://www.lawnext.com/2026/03/exclusive-smokeball-and-thomson-reuters-partner-to-integrate-cocounsel-legal-ai-with-practice-management-platform.html
    — accessed 2026-09-26 — independent trade press, snippet only.
22. Above the Law — "Finally, Something For Small Law Firms" —
    https://abovethelaw.com/2026/05/finally-something-for-small-law-firms/
    — accessed 2026-09-26 — independent trade press on Smokeball/TR,
    snippet only.
23. LawSites — "CosmoLex and Casemaker Integrate..." (2016) —
    https://www.lawnext.com/2016/02/cosmolex.html — accessed 2026-09-26 —
    independent trade press, historical.
24. CosmoLex blog — "CosmoLex Announces New Partnership with Wyoming State
    Bar" (2025) — https://www.cosmolex.com/blog/new-partnership-with-wyoming-state-bar/
    — accessed 2026-09-26 — vendor source, confirms Casemaker relationship
    still referenced in 2025.
25. Thomson Reuters — "Thomson Reuters completes acquisition of Casetext" —
    https://www.thomsonreuters.com/en/press-releases/2023/august/thomson-reuters-completes-acquisition-of-casetext-inc
    — accessed 2026-09-26 — vendor/company source, reliable for deal
    date/amount.
26. vaquill.ai — "Casetext vs Westlaw (2026): Pricing After the $650M
    Acquisition" — https://www.vaquill.ai/blog/casetext-vs-westlaw-pricing-2026
    — accessed 2026-09-26 — independent pricing-research blog, moderate
    confidence.
27. LawSites — "Breaking: LexisNexis Acquires Ravel Law" (2017) —
    https://www.lawnext.com/2017/06/breaking-lexisnexis-acquires-ravel-law.html
    — accessed 2026-09-26 — independent trade press.
28. ABA Journal — "LexisNexis acquires case analytics firm Ravel Law" —
    https://www.abajournal.com/news/article/lexisnexis_acquires_ravel_law —
    accessed 2026-09-26 — independent trade press.
29. LawSites — "MyCase Unveils Its First Gen AI Tools..." —
    https://www.lawnext.com/2024/01/mycase-unveils-its-first-gen-ai-tools-as-parent-affinipay-lays-out-plan-to-embed-ai-across-all-its-products.html
    — accessed 2026-09-26 — independent trade press.
30. BetaKit — "Clio to acquire Spanish-American legaltech vLex for $1
    billion USD" — https://betakit.com/clio-to-acquire-american-legaltech-vlex-for-1-billion-usd/
    — accessed 2026-09-26 — independent tech-business press.
31. BetaKit — "Alexi escalates legal fight with Clio by filing antitrust
    claim" — https://betakit.com/alexi-escalates-legal-fight-with-clio-by-filing-antitrust-claim/
    — accessed 2026-09-26 — independent tech-business press.
32. vLex — bar-association / Fastcase Library pages —
    https://vlex.com/bar-associations , https://vlex.com/fastcase-library —
    accessed 2026-09-26 — vendor source, low independent confidence.

---

## 3. Client portal depth

**Clio and Smokeball anchor the two ends of a real, meaningful spread; the
rest cluster in between with genuine gaps in specific features rather than
an overall tier.** **Clio for Clients** is the most fully-documented:
secure two-way messaging that auto-files to the matter, document
upload/download with a built-in mobile scanner, **native e-signature
included in the base subscription at no extra cost**, online invoice
payment, and — distinctively — a **separate, dedicated "Clio for Clients"
app**, free, on iOS and Android, localized in English and Spanish (not the
same app firm staff use). **Smokeball** is the frictionless outlier:
clients open the portal via a secure emailed link with **no account or
password setup**, get a personalized "To Do List" of pending actions, an
SMS bridge into the same message thread, and a genuinely client-facing
appointment-booking flow embedded in custom intake forms — but Smokeball
has **no native e-signature**, requiring a paid third-party (DocuSign or
its own InfoTrack) integration.

**MyCase** is deep on native e-signature (signer fields, templates,
expiration, automatic reminders, audit trail), messaging, document sharing,
online bill pay, and conditional-logic intake forms — but its own help
center explicitly states **the mobile app is for firm users only**; clients
on every tier are directed to a mobile browser, not a native app, a real
and sourced gap relative to Clio's model. **PracticePanther** has native
e-signature (email, text, or portal, with batch sending), messaging,
real-time case/billing visibility, and embeddable branded intake forms, but
no confirmed client-specific mobile app. **CosmoLex** ships a native
e-signature/file-sharing pair (branded LexSign/LexShare) plus in-portal
chat and bill pay, all included free — but no confirmed client-facing
scheduling or a client-specific app. **Centerbase** and **Rocket Matter**
both require a client's firm to hold its own DocuSign account for
e-signature (an integration, not a built-in signer), and **TimeSolv** is
billing-first, reusing the same LexSign/LexShare pair also seen at CosmoLex.
**Note on ownership**: CosmoLex, TimeSolv, Rocket Matter, and Tabs3 are all
owned by the same private-equity roll-up (ProfitSolv/Lightyear Capital) —
their shared LexSign/LexShare branding and jointly-announced features
reflect that, so they should be read as a related family, not four fully
independent competitors, when weighing how many *different* approaches this
market actually contains.

**The clearest real split across all eight vendors checked is on two
specific axes, not an overall ranking**: native e-signature (Clio, MyCase,
PracticePanther, CosmoLex, and TimeSolv have it built in; Smokeball,
Centerbase, and — unconfirmed — Rocket Matter require a third-party
DocuSign/InfoTrack connection), and a dedicated client-facing mobile app
(only Clio and Smokeball clearly document one; the rest are undocumented or,
in MyCase's case, explicitly excluded). Document sharing, messaging, and
bill pay are table stakes present everywhere checked.

**Portal adoption is real but still modest, and there's a documented
client-experience gap worth carrying into any SAIRNlaw portal decision.**
Secondary reporting attributed to the ABA Legal Technology Survey Report
(exact year not confirmable, primary source blocked) puts secure client
-portal adoption among firms rising from 22% (2017) to 29% in the more
recent cited year — still a minority. Among adopting firms, usage skews
toward documents (~42%) and messaging (~38%) over case-status updates
(~23%), and Clio's own (vendor-commissioned) Legal Trends data found roughly
60% of consumers comfortable using a portal for documents but still
preferring phone calls for status updates specifically. A separate,
third-party-run 2025 survey (433 clients, 109 attorneys, commissioned by a
competing client-communication vendor and framed accordingly) found a stark
perception gap: 72% of attorneys call their firm "caring," only 40% of
clients agree.

**Security claims for the portal specifically are inconsistent across
vendors, and at least one is genuinely disputed.** Clio makes the strongest,
most independently-checkable claim — annual SOC 2 Type II *and* SOC 1 Type
II examinations published via a public trust center. MyCase is claimed
SOC 2 Type II compliant in most secondary sources, but one third-party
compliance directory states it could not independently confirm a SOC 2
report for MyCase — a real, unresolved conflict, not a confirmed fact
either way. Smokeball documents real encryption/MFA practices but its
SOC 2 exposure is inherited through AWS hosting, not an independently
-attested report of its own — a materially weaker claim than Clio's.
Industry framing converges on SOC 2 Type II increasingly being treated as a
non-negotiable procurement requirement for larger buyers, meaning this is
trending toward a real competitive checkbox even where a given vendor
hasn't clearly documented it yet.

### Sources (§3)

1. Clio for Clients — https://www.clio.com/clients/ — accessed 2026-09-26
   — vendor marketing, snippet only.
2. Clio Help Center — "Share Documents" —
   https://help.clio.com/hc/en-us/articles/14983640722971-Share-Documents
   — accessed 2026-09-26 — vendor documentation.
3. Clio Help Center — "Get Started With e-Signatures" —
   https://help.clio.com/hc/en-us/articles/9207223181979-Get-Started-With-e-Signatures
   — accessed 2026-09-26 — vendor documentation.
4. Clio for Clients — App Store —
   https://apps.apple.com/us/app/clio-for-clients/id1506329289 — accessed
   2026-09-26 — independent app-store listing, corroborates dedicated app.
5. Clio for Clients — Google Play —
   https://play.google.com/store/apps/details?id=com.themis.clientmobile —
   accessed 2026-09-26 — same corroboration, Android.
6. MyCase — "Law Firm Client Portal: Key Features & Benefits" —
   https://www.mycase.com/blog/client-management/law-firm-client-portal/ —
   accessed 2026-09-26 — vendor marketing.
7. MyCase Mobile App overview (support) —
   https://supportcenter.mycase.com/en/articles/9369862-mycase-mobile-app —
   accessed 2026-09-26 — source of "app is for firm users only," high
   confidence (explicit vendor statement).
8. MyCase — "Data Security" — https://www.mycase.com/features/security/ —
   accessed 2026-09-26 — vendor marketing.
9. MyCase — "Customizable Legal Client Intake Software" —
   https://www.mycase.com/features/client-intake-forms/ — accessed
   2026-09-26 — vendor marketing.
10. PracticePanther — "Attorney Client Portal" —
    https://www.practicepanther.com/legal-crm/client-portal/ — accessed
    2026-09-26 — vendor marketing.
11. PracticePanther — "Speed Up Client Intake with Native eSignature" —
    https://www.practicepanther.com/legal-esignature-software-law-firms/ —
    accessed 2026-09-26 — vendor marketing.
12. PracticePanther — Client Portal help collection —
    https://support.practicepanther.com/en/collections/340576-client-portal-for-clients
    — accessed 2026-09-26 — vendor documentation.
13. PracticePanther — "How Secure Is Your Law Firm's Data?" —
    https://www.practicepanther.com/security/ — accessed 2026-09-26 —
    vendor marketing; no SOC 2 claim found, HIPAA/Box.com claims only.
14. CosmoLex — "Legal Client Portal Software" —
    https://www.cosmolex.com/features/legal-client-portal-software/ —
    accessed 2026-09-26 — vendor marketing.
15. CosmoLex Support — "Chat with Clients via the Client Portal" —
    https://support.cosmolex.com/knowledge-base/chat-with-clients-via-client-portal/
    — accessed 2026-09-26 — vendor documentation.
16. CosmoLex — "E Signature and File Sharing Software" (LexSign/LexShare)
    — https://www.cosmolex.com/features/secure-file-sharing-electronic-signature/
    — accessed 2026-09-26 — vendor marketing.
17. Smokeball — "Secure Legal Client Portal" —
    https://www.smokeball.com/features/law-firm-client-portal-software —
    accessed 2026-09-26 — vendor marketing.
18. Smokeball Support — "Client Portal Tour" —
    https://support.smokeball.com/hc/en-us/articles/31069248964119-Client-Portal-Tour
    — accessed 2026-09-26 — vendor documentation.
19. Smokeball blog — "Smokeball offers simplified e-signing" —
    https://www.smokeball.com/blog/smokeball-offers-simplified-e-signing —
    accessed 2026-09-26 — vendor blog, corroborates third-party e-sign.
20. Smokeball Support — "Insert electronic signatures with InfoTrack:
    DocuSign" — https://support.smokeball.com/hc/en-us/articles/6009198121367-Insert-electronic-signatures-with-InfoTrack-DocuSign
    — accessed 2026-09-26 — vendor documentation.
21. Smokeball — Security Policy — https://www.smokeball.com/security-policy
    — accessed 2026-09-26 — vendor policy page.
22. Smokeball Community — "New Intake Calendar Booking Feature" —
    https://community.smokeball.com/product-updates/new-intake-calendar-booking-feature-streamline-client-appointments-1577
    — accessed 2026-09-26 — vendor product-update post.
23. Centerbase — "Configurable Client Portal Software" —
    https://centerbase.com/features/client-portal/ — accessed 2026-09-26 —
    vendor marketing.
24. Centerbase Support — "eSignature (Doc Management)" —
    https://support.centerbase.com/hc/en-us/articles/25310135309211-2-eSignature-Doc-Management
    — accessed 2026-09-26 — confirms DocuSign-account requirement.
25. Centerbase — "Mobile App" — https://www.centerbase.com/features/mobile-app
    — accessed 2026-09-26 — vendor marketing, appears staff-oriented.
26. Rocket Matter Knowledge Base — "Client Portal" —
    https://rocketmatter.screenstepslive.com/s/1166/m/54811/c/279706 —
    accessed 2026-09-26 — vendor documentation.
27. Rocket Matter — "Kirk" release announcement (2013) —
    https://www.rocketmatter.com/annoucement-kirk-release-featuring-client-portal-20-integrated-credit-card-payments/
    — accessed 2026-09-26 — vendor announcement, likely stale for
    security-spec language.
28. TimeSolv — "Legal Client Portal | Secure Access" —
    https://www.timesolv.com/client-engagement/features/client-portal/ —
    accessed 2026-09-26 — vendor marketing.
29. TimeSolv — "Legal File Sharing and E-Signature Software" —
    https://www.timesolv.com/business-management/features/file-sharing-esignature/
    — accessed 2026-09-26 — vendor marketing.
30. LawNext — "ProfitSolv, Parent To Multiple Law Practice Management
    Platforms..." — https://www.lawnext.com/2025/06/profitsolv-parent-to-multiple-law-practice-management-platforms-secures-substantial-strategic-investment.html
    — accessed 2026-09-26 — independent trade press, high confidence on
    ownership structure.
31. MyCase blog — "ABA Survey: Lawyers, Cybersecurity, and Secure Client
    Portals" — https://www.mycase.com/blog/general/aba-survey-lawyers-cybersecurity-and-secure-client-portals/
    — accessed 2026-09-26 — vendor blog reporting ABA survey data, primary
    source blocked, moderate confidence.
32. 2Civility — "Clio Legal Trends Report Reveals How Clients Want to
    Communicate With Attorneys" — https://www.2civility.org/clio-legal-trends-report-reveals-how-clients-want-to-communicate-with-attorneys/
    — accessed 2026-09-26 — bar-association blog summarizing a
    vendor-commissioned survey, moderate confidence.
33. PR Newswire — "Nearly 80% of Law Firm Clients Feel Uncared For" (Case
    Status Legal Client Experience Report 2025) —
    https://www.prnewswire.com/news-releases/nearly-80-of-law-firm-clients-feel-uncared-for-new-survey-reveals-major-disconnect-302483162.html
    — accessed 2026-09-26 — press release describing an independently
    -fielded but vendor-commissioned survey.
34. RiscLens — "Is MyCase SOC 2 Compliant?" —
    https://risclens.com/compliance/directory/mycase — accessed 2026-09-26
    — third-party compliance directory, states no confirmed SOC 2 report
    found — directly conflicts with other sources, unresolved.
35. Rocket Matter blog — "SOC 2 Compliance: A Must-Have for SaaS Solutions
    in Law Firms" — https://www.rocketmatter.com/blog/soc-2-compliance-a-must-have-for-saas-solutions-in-law-firms/
    — accessed 2026-09-26 — used only for industry-framing claim, not
    Rocket Matter's own certification.

---

## 4. Sensitive-data handling in legal practice management, and a pricing refresh

**The market's default is generic, horizontal security marketing — not
anything keyed to practice area or data type.** Across Clio, MyCase,
PracticePanther, CosmoLex, and Smokeball, the standard claims are
AES-256/TLS encryption, SOC 2 Type II or ISO 27001 certification,
role-based access, 2FA, and AWS/Azure-inherited compliance — identical
regardless of whether a matter is a contract dispute or a personal-injury
case with real medical records attached. No MyCase-specific HIPAA/BAA
language was found at all.

**Clio is the one real, concrete, practice-area-specific exception, and it
maps directly onto SAIRNlaw's own confirmed sensitive resource.** Clio
sells a named, paid **"Personal Injury Add-On" bundled with a separate
"HIPAA Add-on"**: buying it lets a firm's account owner execute a Business
Associate Agreement with Clio (no redlines accepted) covering electronic
PHI, marketed as managing "medical records, damages, and settlements, with
HIPAA compliance included." This is the clearest finding in this section —
a named competitor selling exactly the kind of protection SAIRNlaw's
`law_pimedical` resource would need, as a paid add-on rather than a default.
No comparable "family law" or "immigration" add-on with its own
data-handling posture was found at Clio or anywhere else. Specialist
personal-injury platforms (Filevine, Litify, CASEpeer, SmartAdvocate,
CloudLex) all treat a signed BAA as baseline, since medical records are
their core workflow — but even there the commitment is a compliance
wrapper (BAA, encryption, permissions), not a differentiated *technical*
control like field-level encryption or redaction built into the platform.
One search result attributed to SmartAdvocate's family-law page states it
"protects sensitive records like financial disclosures and domestic
violence documentation with secure, permission-based access" — the only
vendor language found naming domestic-violence data specifically, but it
could not be independently verified beyond a search snippet and should be
treated as low-confidence. **No named vendor, general or specialist,
markets field-level encryption, redaction, or a restricted-access case type
keyed to practice area** — dedicated redaction tools exist (CaseGuard,
VIDIZMO Redactor) but as separate eDiscovery/court products, not features
integrated into any named competitor's core platform.

**The regulatory/ethical framing explains why the market looks like this**:
ABA Model Rule 1.6(c) requires "reasonable efforts" to prevent unauthorized
disclosure, and its Comment 18 weighs the *sensitivity* of information as
one factor in that reasonableness test alongside cost and likelihood of
disclosure — but there is **no legal-ethics analog to "PHI" as a defined,
mandated-safeguard category** the way HIPAA's Security Rule works. A
personal-injury client's medical record and a routine contract's business
records sit in the identical doctrinal bucket ("information relating to
the representation"), differing only in how much care is "reasonable."
Relevant ABA opinions (Formal Opinion 95-398 on vendor access and breach
-disclosure duty, Formal Opinion 477R on cloud/vendor due diligence, Formal
Opinion 483 on post-breach obligations) and twenty-plus state bar opinions
approving cloud storage "conditioned on reasonable care" all treat
sensitivity as a sliding-scale input, not a category trigger requiring its
own named control.

**Real incidents show the concrete cost of that gap, and they land squarely
on the exact data categories at issue here.** **Docketwise**, the
immigration-specific case-management platform already discussed in §1,
disclosed in April 2026 a breach (beginning September 2025, discovered
February 2026) traced to compromised third-party credentials in a
data-migration pipeline, exposing an estimated 116,666–143,000 individuals'
names, Social Security numbers, government ID numbers, financial data, and
health information — commentary specifically flagged exposure of asylum
applications, deportation-defense records, and visa petitions, and it is
now the subject of active class-action litigation. Separately, an
unsecured Cook County, Illinois court-records database — 323,277 plaintext
records with no access restriction, tagged by case-type codes **IMM
(immigration), FAM (family), and CRI (criminal)** — was discovered by
security researchers and independently corroborated by two separate
outlets. Both incidents are **generic infrastructure/credential/access
failures landing on an unusually sensitive data set, not anything specific
to the case type** — real, current evidence that the legal industry has not
engineered a distinct technical threat response for these categories any
more than it has marketed one to compete on.

**Pricing spot-check (checked one day after the 2026-09-25 baseline):** most
figures held exactly — PracticePanther, CosmoLex, Rocket Matter (plus a new
$129 "Elite" tier added), and LeanLaw (plus a new custom-priced "Elite"
tier added) all matched. Two real, sourced discrepancies: **MyCase Pro
appears to have increased from $99 to $120/month** ($100 annual), per the
vendor's own support center dated June 1, 2026; and **TimeSolv shows
materially higher pricing on its own direct-pricing channel ($42.74–$49.99
-/user) than a still-live AWS Marketplace listing ($29.95–$34.95/user)** —
likely a real price increase with a stale figure persisting on the
third-party marketplace, not independently resolvable without a direct
fetch. **Bill4Time could not be confirmed at all** — no trace of the
previously-recorded "Solo" plan or per-user pricing model; current search
results show an entirely different tier structure (Time & Billing /
Enterprise / Legal Pro / Legal Enterprise), which may reflect a genuine
repricing or a product-line mismatch and is flagged as unresolved rather
than guessed at. Clio's own tier structure has changed since the baseline
in a different way — its Essentials/Advanced/Expand pricing is no longer
publicly listed and now sits behind a "Get Pricing" lead form.

### Sources (§4)

1. Clio Compliance — Help Center —
   https://help.clio.com/hc/en-us/articles/9284651312411-Compliance —
   accessed 2026-09-26 — vendor-published, moderate confidence.
2. Clio Security — https://www.clio.com/security/ — accessed 2026-09-26 —
   vendor marketing, lower confidence.
3. Clio blog — "Understanding HIPAA Compliance for Law Firms" —
   https://www.clio.com/blog/hipaa-compliance-law-firms/ — accessed
   2026-09-26 — vendor blog describing the HIPAA/PI add-on, moderate
   confidence.
4. Clio — Personal Injury Law Software —
   https://www.clio.com/practice-types/personal-injury-law-software/ —
   accessed 2026-09-26 — vendor marketing.
5. PracticePanther Pricing — https://www.practicepanther.com/pricing/ —
   accessed 2026-09-26 — vendor page, moderate confidence.
6. CosmoLex — "Enterprise-Grade Security for Law Firms" —
   https://www.cosmolex.com/features/enterprise-grade-security/ —
   accessed 2026-09-26 — vendor marketing, lower confidence.
7. CosmoLex blog — "CosmoLex Embraces State-of-the-Art Security Standards
   with SOC 2 Attestation" — https://www.cosmolex.com/blog/security-standards-soc-2/
   — accessed 2026-09-26 — vendor blog.
8. Smokeball Security Policy — https://www.smokeball.com/security-policy —
   accessed 2026-09-26 — vendor marketing, lower confidence.
9. Filevine — Personal Injury — https://www.filevine.com/practice-types/personal-injury/
   — accessed 2026-09-26 — vendor marketing.
10. CASEpeer vs Filevine comparison —
    https://www.casepeer.com/comparison/casepeer-vs-filevine/ — accessed
    2026-09-26 — vendor marketing, lower confidence.
11. SmartAdvocate — Family Law — https://www.smartadvocate.com/practice-area/family-law
    — accessed 2026-09-26 — vendor marketing, snippet only, lowest
    confidence, flagged explicitly.
12. ABA Model Rule 1.6 and Comment —
    https://www.americanbar.org/groups/professional_responsibility/publications/model_rules_of_professional_conduct/rule_1_6_confidentiality_of_information/comment_on_rule_1_6/
    — accessed 2026-09-26 — primary source, high confidence.
13. ABA Formal Opinion 477R summary —
    https://nonasec.com/resources/aba-opinion-477r-attorney-cloud-security
    — accessed 2026-09-26 — secondary summary, moderate confidence.
14. ABA Formal Opinion 483 (PDF) —
    https://www.americanbar.org/content/dam/aba/administrative/professional_responsibility/ethics-opinions/aba-formal-op-483.pdf
    — accessed 2026-09-26 — primary source, high confidence.
15. ABA Formal Opinion 95-398 (PDF) —
    https://www.americanbar.org/content/dam/aba/publications/YourABA/95-398.authcheckdam.pdf
    — accessed 2026-09-26 — primary source, high confidence.
16. Pennsylvania Bar Association Formal Opinion 2011-200 (PDF) —
    https://www.pabar.org/members/catalogs/Ethics%20Opinions/formal/F2011-200.pdf
    — accessed 2026-09-26 — primary source, high confidence.
17. Illinois State Bar Association Ethics Opinion 16-06 —
    https://www.isba.org/ethics/opinions/1606 — accessed 2026-09-26 —
    primary source, high confidence.
18. The Florida Bar, Opinion 12-3 —
    https://www.floridabar.org/etopinions/etopinion-12-3/ — accessed
    2026-09-26 — primary source, high confidence.
19. New York State Bar Association, Ethics Opinion 1020 —
    https://nysba.org/ethics-opinion-1020/ — accessed 2026-09-26 — primary
    source, high confidence.
20. ComplexDiscovery — "When Your Legal Tech Vendor Gets Breached: DocketWise
    Incident..." — https://complexdiscovery.com/when-your-legal-tech-vendor-gets-breached-docketwise-incident-exposes-116666-immigration-records-and-a-professions-blind-spot/
    — accessed 2026-09-26 — journalistic analysis, cross-confirmed,
    moderate-high confidence.
21. Cole & Van Note — "DocketWise Data Breach Investigation" —
    https://colevannote.com/2026/04/06/docketwise-data-breach-investigation/
    — accessed 2026-09-26 — plaintiffs'-firm summary, moderate confidence.
22. Top Class Actions — "DocketWise class action claims 'utter failure'..."
    — https://topclassactions.com/lawsuit-settlements/lawsuit-news/docketwise-class-action-claims-utter-failure-to-protect-information-led-to-data-breach/
    — accessed 2026-09-26 — moderate confidence.
23. Rescana — "DocketWise Data Breach 2026" —
    https://www.rescana.com/post/docketwise-data-breach-2026-credential-compromise-exposes-sensitive-client-data-in-immigration-case-management-platform
    — accessed 2026-09-26 — third-party security-vendor analysis, moderate
    confidence.
24. WebsitePlanet — "Report: Data Breach Exposed 323K Records Including
    Sensitive Court Files" — https://www.websiteplanet.com/blog/court-records-leak-report/
    — accessed 2026-09-26 — original discovery/research source, high
    confidence.
25. SecurityWeek — "Illinois Court Exposes More Than 323,000 Sensitive
    Records" — https://www.securityweek.com/illinois-court-exposes-more-323000-sensitive-records/
    — accessed 2026-09-26 — independent corroboration, high confidence.
26. Infosecurity Magazine — "Cook County Leaks 320,000 Court Records" —
    https://www.infosecurity-magazine.com/news/cook-county-leaks-320000-court/
    — accessed 2026-09-26 — independent corroboration, high confidence.
27. Clio Pricing — https://www.clio.com/pricing/ — accessed 2026-09-26 —
    vendor page, moderate confidence.
28. MyCase pricing (support center + third-party trackers) —
    https://supportcenter.mycase.com/en/articles/9369812-how-much-does-mycase-cost
    , https://costbench.com/software/legal-practice-management/mycase-lpm/
    — accessed 2026-09-26 — moderate confidence; source of the $99→$120
    discrepancy.
29. CosmoLex pricing tracker — https://checkthat.ai/brands/cosmolex/pricing
    — accessed 2026-09-26 — third-party tracker, moderate confidence.
30. Rocket Matter Pricing — https://www.rocketmatter.com/pricing/ —
    accessed 2026-09-26 — vendor page, moderate confidence.
31. TimeSolv Pricing — https://www.timesolv.com/pricing/ — and AWS
    Marketplace listing —
    https://aws.amazon.com/marketplace/pp/prodview-kfxc3hhcsjvfq — accessed
    2026-09-26 — conflicting figures, flagged explicitly, medium-low
    confidence.
32. Bill4Time Pricing — https://www.bill4time.com/pricing/ — accessed
    2026-09-26 — vendor page; could not confirm baseline figures, flagged
    explicitly as unresolved.
33. LeanLaw Pricing — https://www.leanlaw.co/pricing/ — accessed 2026-09-26
    — vendor page, moderate confidence.

---

## 5. Synthesis — what actually changed, stated plainly

1. **Both of SAIRNlaw's stated core differentiators — the deadline engine
   and the citator — are matched or exceeded by Clio specifically, and the
   citator (only) is also matched by Smokeball via its Thomson Reuters
   partnership.** Clio's Court Rules engine (native since 2021) covers
   roughly 2,200–2,300 jurisdictions/rule-sets across all 50 states, larger
   in scale than SAIRNlaw's 269 rules across 24-29+ jurisdictions; Clio's
   Vincent Cert citator (via the $1B vLex acquisition) is real, independently
   -confirmed, and shipped to customers. **The honest, defensible framing
   for SAIRNlaw going forward is not "nobody else does this" — it's specific:
   what's comparatively rare is the genuine US+UK combination at real depth
   on both sides (§1), and native platform integration versus a $199/month
   standalone add-on (Clio Work) or a separately-contracted third-party
   reseller relationship (LawToolBox at MyCase/PracticePanther/Smokeball).**
   That is a real, different, and still-defensible claim — but it is not the
   claim "no other legal practice-management platform has a jurisdiction
   -aware deadline calculator or a citator," which this research does not
   support.
2. **Seven of the nine other named competitors (everyone except Clio and
   Smokeball) show no citator/legal-research capability at all**, and most
   show no native deadline-rules engine either (they resell LawToolBox or
   have nothing). SAIRNlaw's position relative to that broader long tail,
   as opposed to the market leader specifically, remains genuinely strong.
3. **Client portal depth is realistically mid-pack** against a market where
   Clio (free native e-sign + dedicated client app) and Smokeball
   (no-login-friction, client-facing scheduling) both show real, adoptable
   patterns SAIRNlaw's messaging+e-signature baseline doesn't yet match,
   while several other named competitors (Centerbase, Rocket Matter,
   TimeSolv) are behind SAIRNlaw on at least one axis (native e-signature).
4. **Sensitive-data handling is a real, still-open opportunity specifically
   around `law_pimedical`** — Clio's Personal Injury/HIPAA add-on is the
   only named practice-area-specific technical/compliance offering found
   anywhere in this market, and it maps directly onto SAIRNlaw's own
   confirmed sensitive resource. The DocketWise and Cook County incidents
   (§4) are concrete, current evidence of what's at stake generically, not
   proof any specific SAIRNlaw control is missing. **Any decision about what
   to build here should route through the SOC 2/Privacy P1-P8 scoping work
   already in progress elsewhere on this platform, not be decided by this
   document** — this document only establishes the external market
   context, per its own scope in §0.2.
5. **Family-law and immigration-specific data handling, the task brief's
   original hypothesis, is not something any named competitor markets
   either** — the one low-confidence exception (SmartAdvocate's domestic
   -violence language) could not be independently verified. This is
   consistent with, not contradictory to, the internal finding that
   SAIRNlaw itself doesn't model these practice areas structurally (§0.2) —
   neither SAIRNlaw nor its competitors have built anything specific to
   these categories; the market-wide gap and SAIRNlaw's own architecture
   happen to point the same direction for a different reason each.

---

## 6. What this document does not establish or decide

- **No claim in this document should be quoted externally** — to a firm, a
  prospect, or in a proposal — without a follow-up read from a network that
  can reach the underlying primary sources; every finding rests on
  search-engine snippets, per §0.1.
- **This document does not decide whether or how SAIRNlaw should respond**
  to Clio's deadline-engine and citator parity, invest in client-portal
  features, or build anything for sensitive-data handling — that is a
  `sairn-software-architect` / `sairn-decision-gate` question, consistent
  with how the sibling 2026-09-25 audit treats its own six gaps.
- **It does not touch, map, or resolve SAIRNlaw's own Privacy P1-P8
  scoping** — that is separately in-progress work on this platform (per
  §0.2) and this document's §4 is scoped strictly to external market
  research, not an internal compliance determination.
- **It does not re-verify SAIRNlaw's own citator or deadline-engine
  implementation** (rule count, jurisdiction list, or correctness) — per
  the task's own instruction, that ground was treated as already
  established and was not re-audited here.
- **It does not resolve the Bill4Time or TimeSolv pricing discrepancies**
  found in §4 — both are flagged as genuinely unresolved rather than
  guessed at.

## 7. Decay

Every source above is a search-index snapshot from 2026-09-26. Three things
in this document are unusually likely to move soon and should be
re-checked before being treated as settled: the Fastcase/Alexi antitrust
litigation (§2, headed to trial by mid-2026), Clio's own tier pricing (§4 —
already moved behind a lead form since the 2026-09-25 baseline), and the
DocketWise class-action litigation (§4, active as of this writing). The
regulatory/ethics material in §4 (ABA Model Rules and opinions) is far more
stable and not expected to shift on the same timescale. **Do not treat any
pricing figure, competitive-parity claim, or litigation status here as
current without re-checking directly against the live source.**
