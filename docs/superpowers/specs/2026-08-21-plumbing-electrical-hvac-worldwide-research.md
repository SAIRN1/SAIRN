# Research Report: Plumbing / Electrical / HVAC Software Landscape (Worldwide)

Research pass, 2026-08-21. No code written, no repository files touched beyond this doc. Findings only, per Michael's explicit instruction — no architecture decision made here.

Scope note up front: search access is US-search-engine-mediated (results skew English/US even for non-English queries), and several claims below come from vendor marketing copy or SEO-content sites rather than primary sources — flagged inline where that's the case. Pricing and feature claims should be treated as directionally accurate, not contract-grade.

---

## 1. Competitive landscape per trade, AS A STANDALONE

**Plumbing-specific:**
- **Knowify** — positioned repeatedly as the standout for project-based/commercial plumbing (job costing, WIP, subcontractor billing) rather than residential service-call plumbing.
- **Dataforma**, **FieldConnect**, **Service Fusion** — all market dedicated "plumbing software" landing pages with plumbing-specific workflow language (drain-cleaning ticket types, water-heater replacement templates, hydro-jetting job types), but these are largely the same core FSM engine re-skinned per trade rather than plumbing-native code.
- **Zuper** — markets a plumbing vertical with route/dispatch emphasis.
- Backflow/cross-connection is handled by a *separate* category of software entirely outside general plumbing FSM — see Area 6.
- Overall: no plumbing-only company emerged with meaningful market prominence the way ServiceTitan dominates multi-trade — the "plumbing-specific" vendors found are smaller players layering plumbing terminology onto generic FSM cores.

Sources: [BuildOps plumbing](https://buildops.com/resources/plumbing-field-service-software/), [Zuper](https://www.zuper.co/plumbing-software), [Dataforma](https://www.dataforma.com/industry/plumbing-software/), [Service Fusion](https://www.servicefusion.com/plumbing-software), [FieldConnect](https://www.fieldconnect.com/industries/plumbing/)

**Electrical-specific:**
- **FieldPulse**, **Sera**, **FieldServicely**, **Optsy**, **Dataforma** all run "electrical contractor software" pages, again largely generic FSM with electrical-flavored templates (panel upgrades, EV charger job types, flat-rate electrical price books).
- **BuildOps** is the one repeatedly described as purpose-built for *commercial* electrical contractors specifically — compliance documentation, asset/equipment tracking, and complex multi-site service agreements are called out as differentiators from generic tools.
- No electrical-only software vendor was found with the market weight of a dedicated single-trade leader — same pattern as plumbing: relabeled generic FSM, not trade-native architecture.

Sources: [FieldPulse electrical](https://www.fieldpulse.com/solutions/electrical), [BuildOps electrical](https://buildops.com/resources/electrical-field-service-software/), [Sera](https://sera.tech/who-we-serve/industry/electrical)

**HVAC-specific:**
- HVAC is the one trade with a genuinely distinct sub-market: **refrigerant/EPA-608 compliance software** as its own product category, separate from general FSM — **RefriTrak**, **RefriComply**, **Field Ascend**, **Fexa Trakref**. These exist *because* HVAC has a hard regulatory requirement (leak-rate calculation, 30-day repair countdowns, per-technician EPA cert tracking) that plumbing and electrical don't have equivalents of.
- **FieldCamp** advertises a "custom objects" engine specifically so refrigerant logs/EPA cert records/leak-rate calcs can live alongside work orders.
- **Commusoft**, **Service Pro (MSI Data)** — general FSM with refrigerant-tracking bolted on.
- This is the clearest case of a real, load-bearing trade-specific technical requirement driving a genuinely separate software category (see also Area 6).

Sources: [RefriTrak](https://www.refritrak.com/en/blog/best-refrigerant-compliance-software-2026), [RefriComply](https://www.refricomply.com/blog/best-refrigerant-tracking-software-2026/), [Field Ascend](https://field-ascend.com/en-us/refrigerant-tracking-software), [FieldCamp](https://fieldcamp.ai/industries/hvac/)

**Overall Area 1 takeaway:** genuinely trade-*native* software (built from a different data model, not just relabeled) exists in force only where a hard regulatory forcing-function exists — HVAC refrigerant compliance, UK gas safety certs, backflow/cross-connection. Otherwise "plumbing software" / "electrical software" / "HVAC software" are largely the same generic FSM core with per-trade marketing pages and pricebook templates.

---

## 2. Real multi-trade platforms

**ServiceTitan** — one product, not separate bundled products. Multi-trade businesses use **business units and separate pricebook categories per vertical** (e.g., "electrical flat-rate pricebook" vs. "HVAC flat-rate pricebook") inside a single account/codebase, per ServiceTitan's own industry pages. Pricing is per-technician, not per-trade: **$245–$500+/technician/month** across Starter/Essentials/Works tiers (third-party estimates, ServiceTitan does not publish pricing), plus **$5K–$50K implementation fees**, plus paid "Pro" add-on modules (marketing, phone system, flat-rate pricebook) sold separately from the base seat price. A 10-tech shop reportedly pays **$2,450–$5,000+/month** in base fees alone; first-year cost with implementation can exceed $63,000 for a 10-user company (third-party analysis, not ServiceTitan-published).

Sources: [ServiceTitan industries](https://www.servicetitan.com/industries), [ServiceTitan pricing breakdown](https://projul.com/blog/servicetitan-pricing-analysis-2026/), [myquoteiq](https://myquoteiq.com/servicetitan-pricing-per-month/)

**Housecall Pro** — **the single most directly relevant finding for this research question.** In 2026 Housecall Pro launched **three separate, trade-specific "packages"** — HVAC, Plumbing, and Electrical — each "preconfigured with industry-specific onboarding, templates, workflows and default settings," a mechanical KPI dashboard, membership-plan tooling, AI pricing benchmarks, and technician-efficiency reporting. This is explicitly framed by Housecall Pro as a *packaging* decision (separate SKUs per trade) layered on the same underlying platform, not a rebuild — but the public announcement and pricing page do **not disclose** whether/how a customer runs two trade packages under one account, or what it costs to add a second trade. General Housecall Pro pricing (not the new trade packages specifically): Basic $79/mo (1 user), Essentials $229–299/mo, Max $349–649/mo, plus per-additional-user fees ($75–100/mo).

Sources: [Housecall Pro announcement](https://www.housecallpro.com/resources/trade-specific-software-hvac-plumbing-electrical/), [Contractor Magazine coverage](https://www.contractormag.com/technology/news/55391529/housecall-pro-launches-trade-specific-software-for-hvac-plumbing-and-electrical-contractors), [Housecall Pro HVAC pricing page](https://www.housecallpro.com/industries/hvac-software/)

**Jobber** — one product for 50+ industries including plumbing, HVAC, electrical, with no trade-specific packages found; pricing is Core $49/mo, Connect $149/mo, Grow $349/mo (team plans scale up), industry-agnostic. Jobber explicitly serves companies operating across multiple trades from a single account, but no dedicated multi-trade upsell mechanism was found.

Sources: [Jobber industries](https://www.getjobber.com/industries/), [Jobber FAQ](https://www.getjobber.com/faq/)

**BuildOps** — architecturally the most "single unified platform for multiple commercial trades" of the group: markets itself explicitly as one system for **HVAC, mechanical, refrigeration, electrical, and plumbing** commercial contractors, with construction-project data ("as-built equipment") flowing directly into service records/asset history shared across trades. This is the closest real-world precedent found for "one platform, trade modules, data flows between them" as opposed to bundled-separate-products.

Sources: [BuildOps commercial HVAC](https://buildops.com/lp/commercial-hvac-platform/), [Field Service Guide BuildOps review](https://fieldserviceguide.com/buildops/)

**Non-English-market equivalents:**
- **Germany**: HERO Software, sykasoft, Label Software (40 years in Sanitär/Heizung/Elektro/Kälte/Solar — explicitly multi-trade), ToolTime, Sage 50 Handwerk.
- **France**: Organilog, Batappli, Axonaut, XT-ERP (bundles gas-safety attestations specifically).
- **Spain**: Clavei, InstalWin (explicitly "electricidad, fontanería, calefacción" one ERP), Factur9, Praxedo (present in France/Germany/UK/Spain/Canada/US).
- **UK**: Checker (gas/electrical/plumbing/heating combined, ~19,600 UK trade users, 6.88M gas compliance reports logged), Commusoft, Clik (NICEIC cert-specific).
- **Brazil**: SIGE Cloud, Everflow (climatização/refrigeração focus), Tradify (present internationally).
- **Japan**: results were thin and mostly generic construction-management ("施工管理") apps (BUILDY NOTE) rather than trade-specific FSM equivalents to ServiceTitan/Jobber — flagging this as a genuine gap: no evidence found of a Japanese ServiceTitan-equivalent.

Sources: as cited inline above per country.

**Cross-cutting pattern across all multi-trade platforms found:** every one uses the **same underlying codebase/account with per-vertical configuration** (pricebooks, templates, business units) rather than genuinely forked products — except Housecall Pro's new packages, which are ambiguous (marketed as separate "packages" but built on the same platform). No evidence was found anywhere of a multi-trade vendor running truly separate codebases per trade under one brand.

---

## 3. The upgrade case: one trade → two or three trades

**Commercial mechanics found:**
- Housecall Pro's new trade packages are the only real precedent for "buy a specific trade package" — but the public materials are silent on what happens when a customer wants a second package. This is a genuine, confirmed gap: direct searching found no vendor documentation, help-center article, or press coverage describing the in-account "add a second trade" flow for any vendor.
- ServiceTitan and Jobber both handle multi-trade as **configuration within the same account** (extra pricebook categories, extra business units) rather than a distinct commercial product — implying the "upgrade" is more a sales conversation / pricebook setup exercise than a plan-tier unlock, but this is inferred from architecture, not confirmed by an explicit vendor "how to add a trade" document.
- Housecall Pro help-center search returned nothing on "second trade" — support staff would need to be asked directly; this is flagged as a real gap, not filled with a guess.

**Technical evidence found (adjacent, not exact):**
- The one concrete technical evidence found is about **switching vendors entirely**, not adding a trade within one vendor — but it's the best available signal on how seam-prone this category is: a ContractorTalk-documented case of an HVAC contractor moving Housecall Pro → ServiceTitan lost 200+ job records, equipment notes, warranty info, and maintenance history for long-term customers after Housecall Pro's data-retention policy purged the account three weeks post-cancellation. A cited (though unverified, third-party-sourced) claim: "field mapping errors cause 60% of data loss during CRM migrations" (attributed to a "National Association of Small Business 2024 technology survey" — could not independently verify this survey exists; treat with caution).
- Saved credit-card tokens cannot transfer between platforms at all (PCI constraint) — a genuine, verifiable technical seam.
- No evidence was found of a *documented* seam specifically for "existing single-trade customer adds a second trade in the same account" — this remains an open question the research did not resolve, worth flagging explicitly as not found rather than guessed at.

Sources: [Kore Komfort Solutions on migration](https://korekomfortsolutions.com/trapped-in-your-software-how-to-switch-from-jobber-to-housecall-pro-without-losing-data/), [PipelineOn migration guide](https://pipelineon.com/blog/crm-migration-without-losing-data/), [ServiceTitan HCP export docs](https://help.servicetitan.com/docs/export-your-housecall-pro-data)

**What this means for the decision at hand:** none of the three major platforms provide public, load-bearing evidence of a clean "add a trade" upgrade path, either commercially or technically. Whatever exists (if anything) appears to be handled ad hoc through sales/onboarding, not a documented self-serve flow.

---

## 4. Regulatory/licensing/code-compliance differences, worldwide

**United States — trade licensing is state/municipal, not federal, and diverges structurally per trade:**
- Plumbing: journeyman/master tiers almost everywhere; code adherence splits the country roughly in two — **Uniform Plumbing Code (UPC)**, published by IAPMO, dominates ~12 western states (CA, OR, WA, NV); **International Plumbing Code (IPC)** covers ~35 states/DC/territories. UPC is self-contained and prescriptive; IPC is performance-based and cross-references the International Residential Code. This is a genuine, code-level fork a shared platform would need to model (different fixture-unit tables, different venting rules).
- Electrical: near-universal **NEC (NFPA 70)** adoption with state-by-state amendment cycles and adoption-year lag (some states still on older NEC editions) — less forked than plumbing but still versioned per jurisdiction.
- HVAC: state licensing plus **EPA Section 608** (federal, Clean Air Act) — the one genuinely federal, trade-specific compliance regime among the three. As of the **AIM Act expansion effective January 2026**, the mandatory refrigerant-transaction-logging threshold dropped from 50 lbs to **15 lbs of HFC refrigerant**, materially expanding which jobs require documented leak-rate calculations, technician cert numbers, and 30-day-repair countdowns.
- Medical gas piping inside healthcare facilities requires **ASSE 6010** certification (a plumbing crossover — Texas's plumbing board has adopted it directly) — separate from standard plumbing licensure, tied to NFPA 99/NFPA 55.
- Water treatment/softener installation: **WQA Certified Installer** — plumbing-adjacent but a separate certification track referencing NSF/ANSI 44, not part of standard plumbing licensure.
- Fire sprinkler layout/design: **NICET** certification (Water-Based Systems Layout) — required by name in some states (e.g., Wisconsin requires NICET Level III for the fire-sprinkler contractor credential) — a genuinely separate trade track that borders plumbing/mechanical.

Sources: [IAPMO state-adopted codes](https://iapmo.org/codes-standards-development/code-development/state-adopted-codes), [Uniform Plumbing Code Wikipedia](https://en.wikipedia.org/wiki/Uniform_Plumbing_Code), [EPA 608 AIM Act threshold change](https://oxmaint.com/industries/hvac/hvac-epa-section-608-compliance-technician-certification), [ASSE 6010 / Texas board](https://aspe.org/pipeline/texas-state-plumbing-board-adopts-asse-professional-qualifications-standard-for-medical-gas-systems-personnel/), [WQA certification](https://wqa.org/certified-installer-ci-path/), [NICET Wisconsin requirement](https://contractorlicenserequirements.com/wisconsin/fire-sprinkler-license-requirements/)

**United Kingdom:**
- **Gas Safe Register** — legally mandatory for anyone working on gas appliances; this is a *compliance regime distinct from* general plumbing/heating licensing (a Gas Safe engineer is certified per specific appliance categories, e.g. domestic natural gas vs. LPG).
- **Part P of the Building Regulations** — governs notifiable domestic electrical work; contractors registered as "competent persons" (via **NICEIC** or similar) can self-certify; unregistered work must be notified to Building Control separately. This is a fundamentally different compliance shape than US electrical permitting (self-certification vs. inspector-driven).
- **BS 7671 (IET Wiring Regulations)** — the UK electrical installation standard, itself synthesizing CENELEC (European) and IEC (international) provisions — distinct document/numbering from NEC, with different certificate types (EIC, EICR, Minor Works Certificate).

Sources: [NICEIC](https://niceic.com/), [Gas Safe Register](https://www.gassaferegister.co.uk/gas-safety/gas-safety-certificates-records/), [BS 7671 Wikipedia](https://en.wikipedia.org/wiki/BS_7671)

**European Union:**
- **F-Gas Regulation (EU 2015/2067)** governs refrigerant handling EU-wide with **mutual recognition of certificates across member states** (unlike US, which is state-by-state with no such reciprocity structure) — split into Category I/II/III by equipment size and refrigerant charge. New EU-wide standardized training requirements are due by **March 12, 2026**, with all existing F-gas certifications required to be updated to the new standard by **March 11, 2027** — an active near-term regulatory change.
- **Germany**: electrical work is a licensed craft (**Meisterpflicht** — master-craftsman requirement) with registration in the local **Handwerksrolle**; a fallback "Altgesellenregelung" allows non-master journeymen with 6 years' experience (4 in a leadership role) to self-certify. Refrigeration work requires the separate **Kälteschein**, which notably has **no master-craftsman requirement** — a structural asymmetry between electrical and HVAC/refrigeration licensing within the same country.

Sources: [Business.gov.nl F-gas certificates](https://business.gov.nl/regulations/certificates-working-with-f-gases/), [Gluckman Consulting F-Gas guidance](http://www.gluckmanconsulting.com/wp-content/uploads/2016/08/IS-21-Training-and-Certification-RACHP-v2.pdf), [Kälteschein](https://www.streit-software.de/wissen/kaelteschein), [Meisterpflicht/Handwerksrolle](https://www.gewerbeanmeldung.de/gewerbe-anmelden/elektriker)

**Canada:**
- Regulation is provincial and structured around **Technical Safety Authorities** rather than trade-specific boards: Ontario's **ESA** (Electrical Safety Authority) issues electrical permits/inspections; Ontario's **TSSA** licenses gas fitting (furnaces, water heaters, gas fireplaces, pool heaters) *and* separately requires a Certificate of Qualification for refrigeration/AC work — meaning in Ontario, HVAC alone spans two different regulator relationships (TSSA for gas, a separate refrigeration C of Q for cooling). Saskatchewan's **TSASK** regulates boilers, gas, electrical, plumbing, and elevators all under one authority — a structurally different regulatory shape from Ontario's split model, in the same country.

Sources: [ESA](https://esasafe.com/contractor-licensing-master-electricians/), [TSSA](https://www.tssa.org/licensing-and-registration), [TSASK](https://www.tsask.ca/electrical/)

**What determines shared-core vs. separate-logic potential:** the research supports treating compliance logic as **inherently non-shareable across the three trades** — plumbing's fork is code-based (UPC/IPC) and regionally binary; electrical's is largely version/amendment-based (NEC editions) with the UK/EU using an entirely different standard family (BS 7671/IEC); HVAC's is the one with a genuine *federal* (EPA 608/AIM Act) and *EU-wide* (F-Gas) forcing function layered on top of state/provincial licensing. A shared platform could plausibly share generic "licensing/cert expiration tracking" infrastructure, but the actual compliance *content* (what data must be logged, on what threshold, under what regulator) is trade-specific and jurisdiction-specific in ways that don't reduce to one shared model.

---

## 5. Real named user complaints and pain points

**ServiceTitan:**
- Contract lock-in is the dominant complaint theme: **12-month minimum contracts (often 2–3 years for discounted rates)**; early termination requires paying the full remaining contract value. BBB complaints document specific buyout demands: **"$39,375" after 10 days of being unable to use the software properly**; **"$24,000... the full remaining contract value"** demanded when a customer tried to cancel within 30 days over implementation issues; another reported a cancellation quote **over $50,000 after 8 months**.
- A Reddit-sourced account (via secondary reporting) describes a 10-year customer struggling to get data exported and navigate cancellation even at contract end, despite giving 30+ days' written notice.
- General complaints: slow customer support, lengthy onboarding, unexpected pricing changes, overcomplicated interface.

Sources: [ServiceTitan pricing/complaints breakdown](https://projul.com/blog/servicetitan-pricing-analysis-2026/), [Get One Crew ServiceTitan reviews](https://www.getonecrew.com/post/servicetitan-reviews)

**Housecall Pro:**
- Capterra 4.7/5, G2 4.3/5 (2,890+ reviews) — but **BBB shows 76 complaints over three years with only a 21% resolution rate**, a notably worse picture than the review-site scores suggest.
- Mobile app described as "buggy and prone to crashes"; **payroll section specifically called out as "full of bugs."**
- System lag reported when managing multiple jobs or updating records in real time.
- Complaints about price increases over time and inconsistent support response times.

Sources: [Housecall Pro Capterra](https://www.capterra.com/p/140363/HouseCall-Pro/), [CheckThat.ai HCP reviews](https://checkthat.ai/brands/housecall-pro/reviews)

**Jobber:**
- Reddit sentiment (r/Contractor and general threads) skews more negative than formal review sites: **"expensive contracts with hidden fees"**, users feeling **"nickel-and-dimed,"** called **"kind of expensive"** relative to alternatives by general contractors.
- Pricing scales poorly past ~10–15 employees; limited workflow/document customization; QuickBooks sync issues and mobile app glitches reported.
- Notably: **targeted searches of r/Plumbing, r/HVAC, and r/electricians specifically turned up little substantive Jobber discussion** — flagging this as a real gap (trade-specific subreddits don't appear to discuss Jobber in depth, at least not surfaced by search), not evidence Jobber has no trade-specific problems, just that this research pass didn't find direct trade-community commentary on it.

Sources: [CheckThat.ai Jobber reviews](https://checkthat.ai/brands/jobber/reviews), [Get One Crew Jobber reviews](https://www.getonecrew.com/post/jobber-reviews)

**FieldEdge:**
- Mixed customer support; pricing "higher than mid-market alternatives but lacks the comprehensiveness of ServiceTitan."
- Concrete UX complaint: **customers have no in-product way to approve a quoted work order** — they must reply to an email saying they agree, rather than clicking approve.
- **No way to copy an existing estimate to another customer** (a repeatedly-cited missing feature).
- Multiple reports of full system downtime — office and techs both locked out simultaneously.

Sources: [FieldEdge Capterra](https://www.capterra.com/p/111740/FieldEdge/reviews/)

**Service Fusion:**
- Difficulty extracting/exporting customer data; no offline functionality; limited customization; reporting described as falling short of what's needed for informed business decisions.

Sources: [FieldCamp Service Fusion alternatives](https://fieldcamp.ai/alternatives/service-fusion/)

**Trade-community-specific complaints (r/HVAC, r/electricians):** search access did not surface direct Reddit thread content (Reddit's own search/API access is limited via general web search); secondary sources referencing these communities note HVAC users "looking for new programs due to unwanted new features" and frustration with being "forced to pay for items they don't need" (e.g., QuickBooks integration bundled as a paid add-on). This is a genuine gap — direct verbatim quotes from r/HVAC, r/electricians, or r/Plumbing threads were not retrievable through the tools available; what's reported above is secondhand characterization of those communities' sentiment, not direct quotes, and should be weighted accordingly.

---

## 6. Trade-specific technical needs that don't overlap

Confirmed and expanded beyond the three examples given in the prompt:

**HVAC:**
- Refrigerant tracking + **EPA 608** (US) / **F-Gas Category I–III** (EU, with March 2026/2027 regulatory update) / equivalents — leak-rate calculation, 30-day repair countdowns, per-technician cert-number logging, appliance-level charge tracking.
- **Manual J / Manual D / Manual S** load-calculation compliance — most US jurisdictions require Manual J on file for new construction/replacement systems, and many require it be generated by **ACCA-approved software specifically** (Wrightsoft Right-Suite, Cool Calc, Elite RHVAC/CHVAC, Adtek) — this is a *procurement-grade* requirement (a shared platform's internal load-calc tool would need ACCA approval to satisfy code officials, not just be "good enough").
- Geothermal crossover: sits across **three** licensing domains simultaneously — well-drilling license (for the bore), HVAC/mechanical license (for the heat pump), and the driller/HVAC contractor separately pull different permits (well-drilling permit vs. building/electrical permit) under their own license numbers. Certifications: IGSHPA Certified GeoExchange Designer, IGSHPA Accredited Installer, NATE with heat-pump specialization.

**Electrical:**
- **NEC Article 220** load calculations (continuous loads, demand factors per NEC Tables 220.42/220.55/220.54, neutral sizing) — a US-specific calculation engine, structurally different from HVAC's Manual J and from plumbing's fixture-unit sizing.
- Permit/inspection workflow differs by self-certification regime: UK **Part P** allows registered "competent persons" to self-certify without inspector visits, versus the US's inspector-driven permit/inspection model — a genuinely different *workflow shape*, not just different code content.
- **Low-voltage/fire-alarm/security crossover**: many US states carve this out as an entirely separate license track (e.g., North Carolina's "Special Restricted Fire Alarm/Low Voltage" license, defined by a 50-volt threshold) — meaning a general electrical license doesn't automatically cover smart-home/security/fire-alarm work, and vice versa.
- **Solar + EV charger crossover**: EV charger installation is explicitly described industry-wide as a natural extension for existing electrical contractors and solar installers (not a separate license in most jurisdictions), but software support is emerging as its own niche — e.g., **COIL iQ**, described as "designed by electricians, for electricians" specifically for EV charging network management, separate from general electrical FSM tools.

**Plumbing:**
- **Backflow testing / cross-connection control** — an entirely separate software category (SAMS, HydroSoft, iWorQ, SwiftComply, XC2) that is often *water-utility-facing* rather than contractor-facing — testers submit results into municipal/utility systems, meaning this isn't purely a contractor tool decision, it's a three-party data flow (contractor → utility/regulator → property owner).
- **Medical gas piping** (ASSE 6010, referencing NFPA 99/NFPA 55) — healthcare-facility-specific, requires 4 years' plumbing/mechanical experience plus a 32-hour course; adopted directly into some state plumbing boards' requirements (Texas).
- **Water treatment/softener installation** (WQA Certified Installer, NSF/ANSI 44) — a plumbing-adjacent certification track that's optional/supplementary, not baked into standard plumbing licensure.
- Code-level fork: **UPC vs. IPC** (see Area 4) means fixture-unit sizing tables and venting rules are genuinely different documents depending on region — this is plumbing's equivalent of HVAC's Manual J/EPA-608 split, i.e., a hard content fork a shared platform must model correctly per jurisdiction.

**Cross-trade / doesn't fit neatly in one bucket:**
- **Fire sprinkler design/layout** — NICET Water-Based Systems Layout certification, required explicitly by name in some state contractor credentialing (Wisconsin); sits adjacent to both plumbing (pipe systems) and general fire/life-safety, arguably a fourth quasi-trade.
- **Generator installation** — crosses electrical (NEC Article 700, emergency/standby power) and, for gas-fired units, gas-fitting/plumbing licensing simultaneously.

Sources: cited inline per topic above in Areas 4/6 search results.

---

## 7. Real industry associations/trade bodies per trade, worldwide

**US:**
- **PHCC** (Plumbing-Heating-Cooling Contractors—National Association, founded 1883) — plumbing + HVACR combined scope.
- **NECA** (National Electrical Contractors Association) — electrical contracting, standards development.
- **ACCA** (Air Conditioning Contractors of America) — HVAC/refrigeration, publishes the **Manual J/D/S technical manuals** that are referenced directly in code (ANSI standard) and maintains an **"Approved Software" list** (Wrightsoft, Cool Calc, Elite RHVAC/CHVAC, Adtek) that jurisdictions require compliance output to come from — this is the clearest real example found of a trade association functionally gatekeeping which software is acceptable for regulatory submission.
- PHCC and ACCA announced a **formal strategic collaboration** in 2026 to jointly advance workforce and energy priorities — worth noting as evidence the plumbing/HVAC bodies see enough overlap to formally coordinate, while NECA (electrical) was not part of this collaboration.
- **MCAA** (Mechanical Contractors Association of America) — spans HVAC, plumbing, and piping/service jointly, another sign these two trades cluster together institutionally more than electrical does.
- **ASSE** (publishes 6010 medical gas standard), **WQA** (water treatment), **NICET** (fire sprinkler + other disciplines), **AMCA**, **ASHRAE** (~50,000 members worldwide) — all HVAC/plumbing-adjacent specialty bodies.

**International:**
- **World Plumbing Council** — 200+ members across 30+ countries, the clearest global-federation body for plumbing specifically.
- **International Institute of Refrigeration (IIR)** — global HVAC/refrigeration forum.
- **UK**: Gas Safe Register (statutory), NICEIC (electrical certification body).
- **Australia**: Master Plumbers (est. 1891, state-chapter federated as Master Plumbers Australia and New Zealand/MPANZ), NECA Australia (6,000+ electrical/communications contractor members) — notably, the search found **NECA's Australian chapters each ran different CRM/marketing/accounting software** before some consolidation effort, direct evidence of software fragmentation even within one national trade body's own membership.
- **Canada**: no single national trade-software-endorsing body found; regulation is provincial via technical safety authorities (ESA, TSSA, TSASK) rather than membership associations.

**Software standards/endorsement:** ACCA's Approved Software list for Manual J/D/S is the one clear, verifiable case of a trade association functionally certifying specific software for regulatory compliance. No equivalent was found for NECA or PHCC — flagging this as a real asymmetry: HVAC has an association-gatekept software category (load-calc tools) that plumbing and electrical do not have direct equivalents of.

Sources: [PHCC](https://www.phccweb.org/), [ACCA/PHCC collaboration](https://www.phccweb.org/news/acca-and-phcc-poised-to-pursue-strategic-collaboration/), [ACCA Approved Software](https://basc.pnnl.gov/library/acca-approved-software), [World Plumbing Council Wikipedia](https://en.wikipedia.org/wiki/World_Plumbing_Council), [NECA Australia](https://www.neca.asn.au/), [Master Plumbers Australia](https://masterplumbers.com.au/)

---

## 8. Other real gaps/considerations worth flagging

- **Housecall Pro's 2026 trade-package launch is the single most directly relevant data point found for SAIRN's decision** — a major incumbent chose, in the same year as this research, to split into per-trade packages rather than staying one undifferentiated product, but did so *without* publishing how multi-trade customers are meant to use it. That gap in Housecall Pro's own public materials is itself informative: even a well-resourced incumbent hasn't solved (or hasn't publicly explained) the exact multi-trade-upgrade question SAIRN is now scoping.
- **BuildOps is the most architecturally instructive precedent** for "one platform, real per-trade modules, data flows between them" (project → service → asset record continuity across HVAC/electrical/plumbing/refrigeration) — worth a deeper follow-up look if SAIRN wants a concrete existing-platform architecture to study, since it's the closest real match to the "shared core + trade modules" model.
- **Fragmentation within one country's own trade association** (NECA Australia chapters each on different software before consolidation) is a small but real signal that even organized, resourced trade bodies don't converge on shared tooling naturally — worth weighing against any assumption that trade associations would push members toward one shared platform.
- **Data portability/lock-in is a bigger practical risk than trade-specific compliance logic across every vendor examined** — ServiceTitan's termination-fee complaints, the Housecall Pro→ServiceTitan 200+ lost job records case, and PCI-driven inability to transfer stored card tokens all point to migration/export friction as the dominant real-world pain point in this category, arguably more than any trade-specific technical gap.
- **Japan gap**: no evidence found of a Japan-specific ServiceTitan/Jobber equivalent — Japanese search results returned generic construction-management software (BUILDY NOTE and similar) rather than trade-specific field-service platforms. Flagging as a genuine unresolved gap rather than assuming none exists.
- **EU F-Gas regulatory deadline (training standardization by March 12, 2026; certification updates required by March 11, 2027)** is a live, near-term compliance change that would directly affect any HVAC module's cert-tracking logic if SAIRN targets EU customers — worth tracking as a moving target, not a static requirement.
- **AIM Act threshold change (50 lbs → 15 lbs HFC refrigerant, effective January 2026)** similarly just took effect and materially widens which US HVAC jobs require EPA 608 documentation — relevant to sizing how much of the customer base a refrigerant-tracking module would actually need to cover.
- Areas searched with **no solid finding** (explicitly flagged, not guessed): (a) any vendor's documented technical process for adding a second/third trade to an existing account; (b) verbatim r/HVAC, r/electricians, or r/Plumbing thread content (only secondhand characterizations of those communities were retrievable); (c) a Japanese-market multi-trade FSM platform; (d) any trade association (PHCC/NECA/WPC) publishing a software certification/endorsement program comparable to ACCA's Manual J Approved Software list.

---

**Status:** research only, no architecture decision made. No code written, no repository files touched other than this doc.
