# SAIRNmechanical — Worldwide Competitive Research, Shared-Platform Framing

Research pass, 2026-08-27. **Findings only.** No code written, no architecture decision made, no
build-order recommendation. Three trades (plumbing, HVAC, electrical) researched in one pass, not
sequenced.

---

## 0. Read this first — relationship to the existing research doc, and what changed

A prior worldwide research doc on these same three trades already exists in this repo:
`docs/superpowers/specs/2026-08-21-plumbing-electrical-hvac-worldwide-research.md`, committed
2026-08-25 in `481be2b`. That commit message records its purpose explicitly:

> "it is finished research backing the active SAIRNmechanical plan (**three standalone trade apps**)"

**That premise is now reversed.** The assignment for this pass fixes two decisions as
non-negotiable: (1) one shared platform with trade-gated modules, a company on one trade must get a
second unlocked in its existing account — no migration, no second login; (2) build order deferred
until after research.

So the 08-21 doc is not wrong, but it was written to answer a different question. Its strongest
sections (per-trade regulatory divergence, vendor lock-in/termination-fee complaints, EPA 608 /
AIM Act / F-Gas timing) were built to justify *separation*. This pass deliberately runs the
opposite lens — **what repeats across the three trades**, because that is what a shared data model
is made of — plus the four things the 08-21 doc does not cover at all:

| Requirement in this assignment | Covered by the 08-21 doc? |
|---|---|
| Small-business **and** mid-market/100+ employee tier, separated | **No.** It is almost entirely SMB/residential. BuildOps is named but not tiered. |
| Cross-trade repeating patterns → shared data model | **No.** Its Area 6 is titled "trade-specific technical needs that **don't** overlap." Opposite lens. |
| Applicability to StoneDesk / SAIRNbuild subcontractor handling | **No.** Not mentioned anywhere. |
| Non-English sources with per-source citations | **Partial and weak.** Its non-English block ends with "Sources: as cited inline above per country" — but that section carries **no inline links at all**. Country claims there are effectively uncited. This pass re-runs them with real per-market citations. |

Everything below is new work. Where the 08-21 doc already established something well
(UPC/IPC fork, EPA 608 thresholds, ServiceTitan termination-fee complaints), it is referenced, not
re-derived.

### Method and honesty notes

- Search access is US-search-engine-mediated. Non-English queries were issued in the target
  language (German, French, Spanish, Italian, Dutch, Japanese, Chinese, Portuguese) and returned
  genuinely local vendors, but ranking is still US-mediated and skews toward comparison/SEO sites.
- **Two evidence tiers are marked throughout.** `[PRIMARY]` = I fetched the vendor's own page and
  read it. `[SNIPPET]` = derived from search-result summaries only, not opened. Treat `[SNIPPET]`
  as directional.
- Where a search summary made a specific claim that the primary page did **not** support, that is
  recorded as a correction in §7, not quietly dropped.
- "No coverage found" is stated explicitly in §7. It is never inferred from silence elsewhere.

---

## 1. Competitive map — per trade, split by customer tier

The single most important structural finding, and it holds in every market examined:

> **Genuinely trade-*native* software exists only where a hard regulatory forcing-function exists.
> Everywhere else, "plumbing software" / "electrical software" / "HVAC software" are the same core
> with a different marketing page and a different pricebook.**

This is consistent with the 08-21 doc's Area 1 conclusion and was re-confirmed independently.
It is directly load-bearing for decision (1): the market has already validated that one core can
serve all three. Nobody found is running three codebases.

### 1a. Small-business tier (roughly 1–25 field staff)

| Trade | Named players | Notes |
|---|---|---|
| **Plumbing** | Housecall Pro, Jobber, FieldPulse, Service Fusion, Workiz, QuoteIQ | QuoteIQ positions explicitly at "1–15 employees across any combination of home service trades" with **per-trade job costing** — the smallest vendor found that treats multi-trade as a first-class concept rather than an accident `[SNIPPET]` |
| **Electrical** | FieldPulse, Sera, Tradify, Housecall Pro, Jobber | Tradify (NZ origin) shows up even in Brazilian-market roundups — genuinely international SMB reach `[SNIPPET]` |
| **HVAC** | Housecall Pro, Jobber, FieldPulse, ThermoGrid, FieldCamp, Sera, Successware | HVAC is the only one of the three with a *separate* SMB sub-category (refrigerant-compliance tools) — see 08-21 doc Area 1 |

**Filling in the two thinner rows, as flagged at the end of the first pass.**

*Plumbing SMB.* The job-type vocabulary is the differentiator and it is shallow: drain cleaning,
hydro-jetting, sewer camera / sewer scope, water-heater swap and tankless installs, trenchless sewer
repair, emergency call-outs. **Workiz** markets specifically on handling drain-cleaning jobs and
water-heater installations; **QuoteIQ** goes further and exposes those as *customer self-quote*
forms — "InstaQuote" lets a homeowner price a drain cleaning, water heater install or recurring
service themselves — at a flat **$29.99–$699/month** for 1–15-employee shops, positioned as
replacing four to five separate tools (CRM, estimating, scheduling, invoicing, marketing automation)
`[SNIPPET]`. **The finding is the shallowness itself:** everything trade-specific here is a job-type
template and a price-book category. None of it is a different data model.

*Electrical SMB.* Same shape. **FieldPulse** targets 2–20 technicians upgrading from paper,
spreadsheets or Google-Calendar-plus-QuickBooks, and serves "HVAC, plumbing, electrical, and general
contracting" from one product; its differentiator, **ClearPath**, is a configurable job-stage
checklist engine — a *workflow* feature, not an electrical feature `[SNIPPET]`. **Sera** covers
HVAC, plumbing and electrical with scheduling, dispatch, pricebooks, estimates, invoicing and KPI
reporting. Neither publishes pricing.

**A pattern worth naming across the whole SMB tier: pricing opacity increases with trade
specificity.** Jobber, Housecall Pro and QuoteIQ publish rates. FieldPulse, Sera and Commusoft
require a sales conversation; ServiceTitan publishes nothing at all. The more a vendor positions on
trade depth, the less it will say about price — which is itself a signal about how the second-trade
question (G1) gets handled: in a sales call, not in a pricing table.

**Housecall Pro is still the most directly relevant SMB data point**, and it moved since the 08-21
pass. Trade-specific packages for HVAC, plumbing and electrical launched **15 July 2026** and are
reported to have added **$96,000 of new MRR** `[SNIPPET]`. Published pricing remains
plan-tier-based, not trade-based: Basic $59/mo annual ($79 monthly), Essentials $149 ($189), MAX
$299 ($329). **The cost of a second trade package is still not published anywhere.** That gap
persisted across a second independent research pass six weeks apart — it is not a search failure,
it is a deliberate non-disclosure.

**Successware** also belongs in this tier and was missed on the first pass — described as the most
established HVAC/plumbing/electrical business-management platform, with mature maintenance-contract
modules automating agreement tracking, recurring scheduling, renewals and customer notifications
`[SNIPPET]`. Another all-three-trades product, not three products.

**The flat-rate pricebook is bought, not built — and the product that sells it spans all three
trades in one SKU.** **Profit Rhino** (powered by Callahan Roach, merged 2019) ships **≈8,500
plumbing, HVAC and electrical tasks** in one book at **$179/month per user**, with 135+ built-in
good/better/best recommendations, cross-sells and upsells, and embedded financing options
`[SNIPPET]`. Housecall Pro's own pricebook is Profit-Rhino-powered. This matters for the shared-model
question: **the single densest piece of trade-specific content in this whole category — the priced
task catalogue — is already commercially packaged as one cross-trade dataset.** Nobody in the
supply chain treats the three trades as needing separate pricebook *products*, only separate
*categories*.

**Consumer financing is a cross-trade attachment, split by ticket size, not by trade:**
**Wisetack** to $25,000, 0–35.9% APR, 0% up to 24 months; **GreenSky** (Goldman Sachs) to $100,000
with >$30B originations, dominant in HVAC, roofing and windows `[SNIPPET]`. The $25K/$100K line is
where HVAC full-system replacement and electrical service upgrades fall out of the smaller product —
a ticket-size boundary, not a trade boundary.

### 1b. Mid-market / 100+ employee tier

This tier is a **different product category**, not a bigger version of the SMB one. The SMB
vendors above are essentially absent from it.

| Vendor | Scale claim | Trade coverage | Tier evidence |
|---|---|---|---|
| **BuildOps** | 10–200 technicians; ~500+ customers | HVAC, mechanical, refrigeration, electrical, plumbing — commercial MEP | Explicitly built to bridge service *and* projects for commercial MEP specialists `[SNIPPET]` |
| **Davisware GlobalEdge** (ECI) | "can support more than **1,000 technicians**" | Commercial HVAC/R, food equipment, petroleum, overhead door, air compressor | True ERP, not FSM. Multi-location warehouse w/ barcoding + automated replenishment; offline mobile; integrations incl. XOi, Profit Rhino, Partstown, ServiceChannel, Paylocity `[SNIPPET]` |
| **Simpro** (Simpro Premium) | 250,000+ users (vendor claim) | HVAC, electrical, plumbing, fire, security | Positioned as the step up for "$1M+ electrical business managing service calls, maintenance contracts and commercial projects simultaneously"; explicitly noted as *too much system* for very small contractors `[SNIPPET]` |
| **Joblogic** | — | Electrical, HVAC, fire & security, larger heating/gas | UK-centric; PPM contracts, assets, engineer app, customer portal `[SNIPPET]` |
| **Commusoft** | Publishes no self-serve pricing; states the product is for businesses with **6 or more staff**; from ~£59/mo | HVAC, plumbing, electrical, renewables | Explicitly reported to *break down* as customers move to commercial/multi-phase work — stock accuracy, basic reporting, rigid quoting templates, thin customer portal `[SNIPPET]` |
| **ServiceTrade** (founded 2010) | — | Commercial mechanical, HVAC, refrigeration, fire protection & life safety, **electrical** | Built around *recurring service, inspections and compliance-driven work*: inspections, service agreements, **deficiency tracking through to remediation**, branded service reports to facility managers, NFPA-standard inspection forms `[SNIPPET]` |

**Two mid-market shapes worth separating, because they imply different data models:**

- **ServiceTrade's shape is inspection → deficiency → quote → remediation.** The recurring
  inspection *finds* problems; each becomes a tracked deficiency; deficiencies become quoted work.
  That loop is trade-agnostic — it is identical for a fire-sprinkler inspection, an HVAC PM visit,
  and an electrical thermographic survey. Only the form differs.
- **BuildOps' shape is service + construction in one product.** Its project module carries
  submittals, RFIs, change orders and daily reports **alongside** the dispatch board, explicitly so
  commercial MEP contractors do not buy a crew-scheduling tool and a construction PM tool
  separately `[SNIPPET]`. Scheduling handles one-off, recurring and **multi-day** jobs on one board,
  with a crew assigned per day a job spans, reusable multi-day templates, and conflict detection
  across the whole multi-day plan before it saves `[SNIPPET]`.

**Neither shape is per-trade.** Same-day service call vs multi-day project is a *scheduling*
distinction that cuts across all three trades identically — it is not a reason to fork the model.

**The mid-market boundary is legible and repeatable.** Independently of trade, contractors outgrow
SMB tooling at the same list of capabilities: job costing, **retainage**, **AIA G702/G703 progress
billing**, **WIP / percent-complete reporting**, change-order integration that updates contract
value without breaking prior-period totals, **certified payroll**, and **lien-waiver tracking**
`[SNIPPET]`. Beyond that line the named destinations are Sage 100 Contractor, Foundation Software,
Acumatica Construction Edition — accounting-led, not dispatch-led.

**Union / prevailing-wage payroll is its own mid-market category** and is fully cross-trade:
Worklio, FOUNDATION, WageIQ (Points North), Miter, ADP Workforce Now. The complexity named is
identical for all three trades — multi-state projects with differing prevailing-wage law, employees
working across different locals and CBAs, and **fringe-benefit calculations that change by trade
classification** `[SNIPPET]`. That last clause is the key one: fringe varies *by trade*, on one
engine, off one rate table. It is a shared model with a trade key, not three models.

### 1b-i. The consolidator tier — the strongest market-structure evidence found for decision (1)

This was not on the map in either pass until now, and it is the single most direct external
validation of the one-platform decision. **`[PRIMARY]`, fetched and read:**

> *"Most plumbing-relevant PE money in the United States is deployed through **combined residential
> trades platforms (HVAC + plumbing + electrical)** rather than through pure-play plumbing
> roll-ups."*

Private equity has bought roughly **800 HVAC, plumbing and electrical companies since 2022** and now
accounts for about **half of all HVAC-services deals**, across roughly two dozen active platforms
`[SNIPPET]`. The named combined-trades platforms and their backers `[PRIMARY]`:

| Platform | Backer |
|---|---|
| Apex Service Partners | Alpine Investors |
| Sila Services | Goldman Sachs Alternatives |
| Wrench Group | Leonard Green & Partners |
| Champions Group | Blackstone BXPE |
| Redwood Services | Altas Partners |
| ResiXperts | FoW Partners |
| Ally Services | Watchtower Capital |
| Southern Home Services | Gryphon Investors |
| Authority Brands | Apax Partners |
| Legacy Service Partners | Gridiron Capital |

Pure-play plumbing platforms exist but are explicitly the exceptions — P3 Services (Stellex),
Repipe Specialists (Gryphon Heritage), Trades Holding Company `[PRIMARY]`. **Apex alone completed 60
add-on acquisitions in 2025 across HVAC, plumbing and electrical combined**; **Sila operates 40+
brands** spanning residential HVAC, plumbing, electrical, water treatment, IAQ and home performance
`[PRIMARY]` / `[SNIPPET]`.

**Why this matters more than any feature comparison in this document:** the most sophisticated,
best-capitalised buyers in this industry — people who have run the numbers on ~800 acquisitions —
have concluded that **the durable unit is the multi-trade platform, not the single-trade shop.**
Decision (1) is betting on the same structure they are, and it is the only evidence found in either
pass that comes from money rather than marketing.

It also implies a customer shape neither research pass had considered: **a consolidator is an
acquirer of trades, continuously.** It buys a plumbing company in March and an electrical company in
August, and needs both in one back office with per-brand and per-location separation preserved. That
is the "add a trade to a live account" flow (G1) as an *operating routine*, not a rare upgrade event
— and no vendor documents it (§4). Europe has the same shape: **Instalco** (Sweden) is a listed
installation group consolidating el / VVS / ventilation firms `[SNIPPET]`.

**Caveat, stated rather than buried:** the deal-count and share-of-deals figures come from M&A
advisory sites that make their living from this market, and the platform list is a snapshot that
will age fast. The *structural* claim — combined-trades platforms dominate over pure-play — is
verified from primary text and is the part worth relying on. The numbers are directional.

### 1b-ii. What the consolidators actually run — the open question, now answered

This was flagged at the end of the previous pass as "arguably the most valuable unanswered question
in this entire document." It is answered, and the answer is more useful than expected because it is
**not** what the framing assumed.

**They standardise on ServiceTitan, and they staff a dedicated role to onboard each acquisition
onto it.** The job-postings route was the fastest signal, exactly as predicted. Apex Service
Partners advertises a **ServiceTitan Integration Specialist** whose responsibilities read as a
literal description of the flow no vendor documents `[PRIMARY]`:

> "Own the setup, configuration, and deployment of ServiceTitan for **new acquisitions** and internal
> business units"
> "Work closely with **Mergers and Acquisitions** teams to support acquisition onboarding"
> "Work collaboratively with the data team to receive and validate required data; perform the
> hands-on work to **integrate, clean, and configure data** within ServiceTitan"
> — requiring "2-3+ years of hands-on ServiceTitan experience," and alignment "across all operating
> companies."

Corroborating across the tier: **Wrench Group**'s stack is ServiceTitan + Confluence + Azure Monitor,
with its CIO publicly partnering with ServiceTitan on AI for scenario planning and workforce
management `[SNIPPET]`. **Vertex Service Partners** runs a "model tenant" — a standardised workflow
replicated into each new acquisition `[SNIPPET]`. ServiceTitan has announced named strategic
partnerships with **Cobalt Service Partners** and **Galaxy Service Partners** `[SNIPPET]`.

**ServiceTitan sells to this segment deliberately, with a dedicated product.** From its own private-
equity page `[PRIMARY]`:

> **Enterprise Hub** — "centralized management across multiple entities for unified data,
> standardized operations, and consistent reporting"
> "**500+ add-on integrations facilitated for PE-backed customers last year**"
> "average of **under 2 months integration time**"
> "trusted by … **500+ customers with $100M+ in revenue**"

(Its EBITDA-multiple and growth claims on the same page are vendor marketing with no methodology —
do not repeat them.)

**And here is the part that matters architecturally.** Sila Services — 23 entities in the trades —
describes Enterprise Hub in the vendor's own case study as operating over **tenants**, plural
`[PRIMARY]`:

> "With Enterprise Hub, we were able to click one button and it would **adjust prices across all of
> our tenants**." — Alex Dukhin, manager of ERP and Business Development, Sila Services

Roll-up reporting runs report templates **across multiple tenants**, with per-tenant visibility
limits (a user in a region sees 7 of 50 tenants) `[SNIPPET]`.

**So the incumbent's architecture is: one tenant per acquired company, plus a roll-up/control layer
above them. Not one merged account.** That resolves G1 rather than contradicting it, and explains
*why* no vendor documents an "add a second trade to an existing account" flow:

> **The incumbent's answer to multi-trade growth is a new tenant. SAIRNmechanical's stated
> requirement — unlock in the existing account, no migration, no second login — is explicitly the
> opposite of that answer.**

Two consequences worth stating plainly, one favourable and one not:

- **Favourable:** the gap is real and now *explained*, not merely observed. A contractor who grows
  into a second trade organically — as opposed to acquiring a company that already does it — is
  served by nobody. Enterprise Hub is built for portfolio roll-up, and business units (§4) gate
  visibility inside a tenant; neither is an entitlement unlock.
- **Unfavourable, and it should not be soft-pedalled:** **the consolidator segment is not open
  ground.** ServiceTitan has a named product, a PE go-to-market motion, published onboarding
  throughput (500+ add-ons/year, sub-2-month integrations), and customers who employ full-time staff
  whose job title contains its product name. Treating the PE thesis (§1b-i) as a market opening for
  SAIRNmechanical would be a misread — it validates the *multi-trade platform structure*, it does
  not indicate an unserved buyer. The unserved buyer is the organically-growing independent, at both
  SMB and mid-market tier.

**Estimating is the one mid-market area that genuinely forks by trade** — and even there, one
vendor deliberately crosses:

- Electrical: Trimble **Accubid** / Accubid Anywhere, **ConEst** Electrical Bid Manager,
  **McCormick Systems** `[SNIPPET]`
- Mechanical/plumbing: Trimble **QuoteSoft Pipe**, **FastEST** `[SNIPPET]`
- **Wendes** — "covers HVAC, sheet metal, **and plumbing in one system** with SMACNA-based duct
  calculation behind it, which suits multi-trade mechanical shops that bid duct and pipe from the
  same desk" `[SNIPPET]`. This is the clearest existing proof that mechanical + plumbing estimating
  can live in one product; no equivalent was found spanning electrical *and* mechanical.

### 1c. Non-English markets (re-run with real citations)

| Market | Vendors found | Multi-trade posture |
|---|---|---|
| **Germany** | **STREIT V.1** — full ERP explicitly for *Elektro, SHK, Kälte/Klima, Bedachung*; **Label Software** — 40 years across *Sanitär, Heizung, Elektro, Kälte/Klima, Solar, Anlagenbau*; **Hottgenroth OPTIMUS** — SHK, Kälte-/Klimatechnik, TGA; also HERO, ToolTime, Sage 50 Handwerk | **Strongly multi-trade by default.** German Handwerk ERP treats Elektro + SHK + Kälte as sibling *Gewerke* inside one product — the single closest market precedent for SAIRN's shared-platform decision `[SNIPPET]` |
| **France** | Organilog, Extrabat (cheministes/chauffagistes/climaticiens, "gamme multi-métiers" for TPE/PME), Libel, ChaudièrePro, Trustup Pro, Anodos | Multi-métiers framing is common. Note: **French e-invoicing becomes mandatory in 2026** and vendors are already shipping it — a hard, dated market-entry requirement `[SNIPPET]` |
| **Spain** | **InstalWin** — one ERP for *electricidad, fontanería, calefacción*, with an IDM mobile module for field parts entry; **Vendomia** — electricidad + climatización; **Clavei**; myGESTIÓN; miboo; STEL Order; Programación Integral | Multi-gremio is the norm, not the exception `[SNIPPET]` |
| **Italy** | **Perfetto** — 400+ active clients, spans *impianti elettrici, idraulici, rinnovabili, sicurezza, antincendio, TLC* in one product; **iMio**; **Edison** (Exe Progetti, idraulico/termico); Dylog Impiantistica Elettrica; Eassistance | Same pattern — one product, many *settori* `[SNIPPET]` |
| **Netherlands** | Gripp, Veldwerk, Cobry (built for the technical sector); MoreApp, 123Formulier, Klippa for digital *werkbonnen* | A Dutch source states the divergence plainly: *"an electrical company works with different calculations and inspections than a plumber or climate and cooling installer"* — i.e. the shared part is the werkbon/planning/stock, the forked part is calculation + inspection. That is exactly the seam a trade-gated module system would cut on. **NEN 3140** is the load-bearing Dutch electrical-safety inspection regime `[SNIPPET]` |
| **Nordics** | **Admicom** (FI) — ERP for construction, **building services engineering** and real estate; product family Ultima, Flex, Vision, Estima, Planner, Tempo, Insite, BIM3; Visma (NO) for accounting/payroll layer | Admicom is modular by *function* (estimating, planning, field reporting), **not by trade** `[SNIPPET]` |
| **Sweden / Norway** | **Handyman** (GSGroup, HQ Norway) — **45,000+ service technicians and installers**, spanning *elinstallation, VVS, fastighetsförvaltning, bygg, industriell service, medicinteknik*; **"in Norway, every other electrician uses Handyman"**; **Fieldly** — projekt & arbetsorder for bygg och installation, 850,000+ projects | **The Nordic market leader is explicitly one product across el + VVS + more.** Note also the institutional signal: the Swedish trade body **Installatörsföretagen** covers el and VVS *together*, and **Instalco** is a listed consolidator of el/VVS/ventilation firms — trade-combination is normal here at association, software and ownership level simultaneously `[SNIPPET]` |
| **Portugal** | **ARTSOFT** (assistência técnica — pedidos, ordens de trabalho, recursos, execução, stock, análise); **Webcraft** (Folha de Obra, with a dedicated *climatização/AVAC* variant and a preventive-maintenance product); **Tradify** (10,000+ users worldwide, marketed for *eletricistas, canalizadores, climatização*); Deskero | Same one-product-many-trades pattern; Tradify's presence here and in Brazil confirms it as the most internationally mobile SMB product found `[SNIPPET]` |
| **Turkey** | **Ekibim Sahada** — mobile field-service management covering *klima bakımı, jeneratör bakımı, **elektrik ve su tesisatı** kontrolleri* with automatic periodic-maintenance reminders; **ESN Sistem** (iklimlendirme-specific: klima, kombi, chiller, brülör, HVAC); **FieldCo**; **TamirBank**; **Servis Programı** | **Skews to iklimlendirme (HVAC) like Poland**, but Ekibim Sahada explicitly spans AC + generator + electrical + water plumbing inspections in one product. Periodic-maintenance reminders are the organising concept, matching A3 `[SNIPPET]` |
| **Gulf (UAE / Saudi)** | **QuickAMC** (Dubai), **FieldWeb**, **Origami** (SA), plus US products sold in — FieldPulse, Service Fusion | **AMC (Annual Maintenance Contract) is the organising commercial object**, to the point that a local vendor is *named* after it. Every FSM marketed here leads with AMC modules — contract details, renewals, service history. Third region after India and the UK/commercial PPM market where the recurring multi-trade agreement, not the one-off call, is the centre of the product `[SNIPPET]` |
| **Poland** | **iService** (klimatyzacja/wentylacja/chłodnictwo — zlecenia, awarie, rentowność), **Integra Serwis**, **Serwisoft**, **Serwis Planner**, **TaskForce** (instalacje, przeglądy okresowe, gwarancja/pogwarancja, awarie — list or map view), **OptimRoute**, **RO App**, **Locatick** | **Skewed hard to HVAC/refrigeration**, not balanced across the three. Periodic-inspection (*przeglądy okresowe*) workflows are front-and-centre — consistent with EU F-Gas obligations driving the product shape. Plumbing/electrical-first Polish products did not surface `[SNIPPET]` |
| **Brazil** | **Everflow** — explicitly targets 15–50-employee service firms in *energia solar, segurança eletrônica, refrigeração, engenharia, telecom, instalação*; offline app, faturamento por medição; **SIGE Cloud**; **Mais Controle**; **Conta Azul** | Multi-segment by design; segment list is broader than the three trades `[SNIPPET]` |
| **LatAm (MX/CO/CL)** | **Fixner** (Spain-origin, serving the region), plus the Spanish vendors above reaching across; ComparaSoftware México for órdenes de trabajo | No distinct domestic category found separate from the Spanish one — Spain's *instaladoras* products are the regional standard. See §3 A3 for the Fixner line-item quote, which is `[PRIMARY]` and directly load-bearing |
| **South Korea** | 검색 returned **CMMS/EAM only** — EquipCare365, Visual FACILITY for Factory (설비자산관리), Yullin ECMS, SAP CMMS, plus Capterra Korea 배관/장비유지보수 listings and **Synchroteam** (a French product marketed into Korea for HVAC/전기/배관) | **No domestic trade-contractor FSM found.** Korea's category is plant/facility maintenance (설비보전), i.e. asset-owner-side, not contractor-side — structurally the same mismatch as China, for a different reason. Recorded as no-coverage-found in §7 `[SNIPPET]` |
| **India** | **Zoho FSM** (INR billing, to ₹1,800/user/mo), **FieldEZ** (45,000+ field staff), **ServiceMax** (asset-centric, AMC management) | Horizontal FSM, no trade specialisation found. AMC (Annual Maintenance Contract) is the dominant commercial shape `[SNIPPET]` |
| **China** | 泛普软件 (Fanpu) 机电安装工程管理软件, 建米软件, 斗栱云 ERP, 建文软件, hecom 机电工程管理方案 | **Structurally different market.** Everything found is 机电安装 (MEP *installation project*) management — contracts, cost control, materials, drawings, progress. **No residential/commercial service-dispatch FSM equivalent surfaced.** The Chinese category is project-ERP, not ServiceTitan-shaped `[SNIPPET]` |
| **Japan** | **ZAC** (Oro) — industry-specific cloud ERP explicitly for 設備工事・メンテナンス業, per-project P&L and contract management; **プロワン** — 設備工事/ビルメンテ, 顧客管理→施工→保全→経営分析 end to end; **ANDPAD**, **KANNA**, **サクミル**, **kintone**; 大塚商会 ERPナビ 設備工事業 category | **This partially closes the 08-21 doc's flagged Japan gap.** That doc concluded no Japanese ServiceTitan-equivalent was found and results were "generic construction-management." That is now too pessimistic: ZAC and プロワン are genuinely 設備-industry (mechanical/electrical building services) products covering maintenance and after-service, not generic 施工管理. What is *still* not found is a Japanese product organised around per-trade licensing compliance (e.g. 電気工事業者登録) the way UK/AU tools are around certificates `[SNIPPET]` |

**Cross-market conclusion:** in *every* non-English market examined except China, South Korea and
Poland, the dominant domestic pattern is **one product spanning electrical + plumbing/heating +
climate/refrigeration**. Germany, Spain and Italy are the most explicit about it. The three
exceptions are not counter-examples to the shared-platform model — they are markets where the
*contractor-side service* category barely exists (China is MEP-project ERP, Korea is asset-owner
CMMS/EAM) or where one trade dominates the tooling (Poland skews to HVAC/refrigeration under F-Gas
inspection obligations). **The three-separate-apps model has no international precedent found
anywhere, in either research pass.**

---

## 2. Gaps, categorised per trade

Each row: what is missing or weak, and which of the three trades it actually bites.

| # | Gap | Plumbing | HVAC | Electrical | Evidence |
|---|---|---|---|---|---|
| G1 | **No published "add a second trade" path at any vendor** | ● | ● | ● | Confirmed across two independent passes six weeks apart. HCP publishes trade packages but not second-trade cost; ST/Jobber handle it as configuration, undocumented as a product `[SNIPPET]` + §4 `[PRIMARY]` |
| G2 | **Sub/third-party compliance not integrated into dispatch** | ● | ● | ● | Fieldpoint's subcontractor-management page covers scheduling-board visibility, GPS, T&M entry, payment vouchers — and says **nothing** about insurance, licence or compliance-document tracking `[PRIMARY]`. That whole function lives in a *separate* vendor category (§5) |
| G3 | **Credential-expiry → dispatch-eligibility enforcement is claimed but not documented** | ● | ● | ● | Field Ascend's certification page records issue/expiry/renewal and offers "certification visibility alongside scheduling," but does **not** state expired credentials remove a tech from the dispatch pool `[PRIMARY]`. See §7 correction |
| G4 | **Regulatory content is genuinely non-shareable** (established 08-21, re-confirmed) | UPC vs IPC fork; backflow/cross-connection is a 3-party contractor→utility→owner flow | EPA 608 / AIM Act (15 lb threshold, Jan 2026); EU F-Gas Cat I–III, new training std due 12 Mar 2026, recerts by 11 Mar 2027; ACCA-approved Manual J software gatekeeping | NEC edition lag per state; UK Part P self-certification vs US inspector model; BS 7671; NL NEN 3140; low-voltage/fire-alarm carve-outs | 08-21 doc Areas 4 & 6 |
| G5 | **Mid-market financial layer absent from all SMB tools** | ● | ● | ● | Retainage, AIA G702/G703, WIP/percent-complete, change-order contract-value integrity, certified payroll, lien waivers — the named break-list `[SNIPPET]` |
| G6 | **Commusoft-class tools degrade at the commercial transition** | ● | ● | ● | Named failures: stock accuracy, basic reporting, rigid quoting templates, thin customer portal `[SNIPPET]` |
| G7 | **Estimating does not cross the mechanical↔electrical line** | Wendes covers it with HVAC | Wendes covers it with plumbing | **Isolated** — Accubid/ConEst/McCormick are electrical-only | `[SNIPPET]` |
| G8 | **Permit filing is fragmented by jurisdiction *and* by trade within one project** | ● | ● | ● | ~30,000 US permit-issuing local governments, each with its own portal/auth/forms; a single commercial project can need building + electrical + plumbing + HVAC + grading + encroachment permits `[SNIPPET]` |
| G9 | **China: no service-dispatch product for these trades** | ● | ● | ● | Entire domestic category is 机电安装 project ERP `[SNIPPET]` |
| G10 | **Japan: no licensing-compliance-organised product** | ● | ● | ● | ZAC/プロワン cover maintenance and after-service well; nothing found organised around 電気工事業者登録-style credential gating `[SNIPPET]` |
| G11 | **Refrigerant/F-gas ledger has no plumbing or electrical analogue** | — | ● only | — | The one regulated-consumable ledger of the three. 08-21 doc Area 1 |
| G12 | **Lock-in / data-portability is the dominant real-world pain, above any feature gap** | ● | ● | ● | 08-21 doc Area 5 & 8: ServiceTitan buyout demands ($24K, $39,375, >$50K), HCP→ST case losing 200+ job records, PCI-blocked card-token transfer |
| G13 | **Manufacturer warranty registration left as a manual step by the FSM platforms** | (water heaters only) | ● **primary** | — | ServiceTitan integrates select brands but post-install registration is not native; Lennox/Goodman largely manual portal entry `[SNIPPET]` |
| G14 | **Electrical certificate generation already lives outside FSM, in the instrument vendors' software** | — | — | ● **only** | Megger CertSuite and Fluke TruTest both import instrument results and emit finished certificates `[SNIPPET]`. An electrical module competes with an installed base it does not own |
| G15 | **Outbound compliance submission is nobody's modelled object** | ● backflow | ● refrigerant | ● Part P | Every instance found is handled by a dedicated external portal (SwiftComply/Tokay/XC2) or by the regulator's own site — no FSM was found modelling submission state, fee and receipt as a first-class record (§3 A7) |
| G16 | **South Korea: no contractor-side FSM at all** | ● | ● | ● | Category is asset-owner CMMS/EAM (설비보전). §1c, §7 |
| G17 | **Inspection intervals are treated as fixed lookups, not computed from risk** | ● | ● | ● **sharpest** | DGUV V3: *"Richtwerte sind keine Höchstgrenzen"* — the interval derives from a site hazard assessment (device type × environment × last-inspection failure rate), 3–24 months. German DGUV-specific tools ship a Prüffristen-Rechner; no general FSM found does `[PRIMARY]` / `[SNIPPET]` |
| G18 | **Customer intake / AI call handling is a bolt-on, native nowhere** | ● | ● | ● | Every AI-receptionist vendor found integrates *into* ServiceTitan/HCP/Jobber rather than being part of them `[SNIPPET]` |
| G19 | **Apprenticeship / OJT-RTI progression is a separate category from credential tracking, despite feeding it** | ● | ● | ● | Dedicated apprenticeship platforms track OJL hours, RTI, wage progression; no FSM examined joins that to its own credential registry (§3 A1) `[SNIPPET]` |
| G20 | **Test-instrument calibration validity is tracked nowhere in FSM** | — | ● | ● | Required as a mandatory protocol field in Germany (DGUV V3 field 5). It is a third dated-validity registry — contractor-owned, not customer-site, not person — and no FSM model found accounts for it `[PRIMARY]` |
| G21 | ~~Nobody serves the consolidator's acquire-a-trade routine~~ — **RESOLVED, and it inverts.** Consolidators are *well* served: ServiceTitan Enterprise Hub, one tenant per acquisition + roll-up, 500+ add-ons/yr at sub-2-month integration. The genuinely unserved buyer is the **organically-growing independent**, who needs a trade unlocked *in place* rather than a new tenant | ● | ● | ● | §1b-ii `[PRIMARY]`. Reframes G1 rather than duplicating it |

---

## 3. Cross-trade repeating patterns — the shared-data-model material

This is the section written specifically for decision (1). Each pattern below was observed
independently in **at least two** of the three trades, in at least two markets.

### Tier A — repeats across all three trades with the *same shape*; strong shared-model candidates

**A1. Credential registry (person → credential).**
Every market gates work on a per-person credential with an issuing authority, a number, a
jurisdiction and an expiry. Only the vocabulary changes: US state journeyman/master + EPA 608;
UK Gas Safe + NICEIC competent-person; DE Meisterpflicht/Handwerksrolle + Kälteschein; NL NEN 3140
responsible-person; AU/NZ licensed/certifying gasfitter and electrician; CA provincial C of Q.
The *record* is identical across all of them. Software already treats it that way — Kahuna,
Field Ascend and Salesforce all sell one credential store feeding dispatch, across
"HVAC, plumbing, electrical, elevator, facilities" as one list `[PRIMARY]` / `[SNIPPET]`.
**Implication: one credential table, trade-tagged rows, jurisdiction-tagged rows. Not three tables.**

**Extension found this pass — the credential registry has an upstream half nobody joins to it.**
Apprenticeship management is its own software category (GoSprout and peers), tracking **on-the-job
learning (OJL/OJT) hours, related technical instruction (RTI), wage progression, evaluations and
reporting** `[SNIPPET]`. That is the pipeline that *produces* the licence in A1, and in the US it is
becoming compliance-bearing in its own right — apprenticeship ratios and hours are conditions on
IRA-funded work, alongside prevailing wage (B3). The demand signal is not marginal: US construction
needs an estimated **349,000 net new workers in 2026**, only two entrants replace every five
retirees, DOL announced **$145M** for apprenticeship programmes in January 2026, and BlackRock
committed **$100M over five years to train 50,000 workers in electrical, HVAC and plumbing**
`[SNIPPET]` — note, once again, those exact three trades named together by an outside party with no
stake in this decision. **The shape is the same record as A1 with an added progression axis
(hours-accrued toward a target), and no FSM examined models it.** See G19.

**A2. Site asset registry (customer → site → asset).**
Named fields are the same everywhere: make, model, **serial number**, install date, warranty
status, open agreements, and a service-history chain of date/tech/work/parts. Vendors describe it
identically for HVAC, electrical and plumbing, and the same model is reused for elevators and
medical equipment `[SNIPPET]`. Only the *asset taxonomy* differs by trade.
**Implication: one asset table; trade affects the type vocabulary, not the schema.**

**A3. Recurring maintenance agreement (PPM / service contract). — CORE PLATFORM REQUIREMENT, EVERY TIER**

This is the **strongest single argument for a shared platform**, and it is an argument from the
customer's side, not the vendor's. A commercial PPM contract is *natively multi-trade*: the
"Hard FM / M&E" bundle sold in the market covers **HVAC, electrical systems, plumbing, lifts and
BMS together, plus PAT testing and water-hygiene checks — under one contract** `[SNIPPET]`.
Commercial pricing runs $500–$2,000+ per system per year across dozens of units and multiple sites,
requiring PPM schedules, SLA tracking, multi-site asset management and compliance documentation;
residential runs $120–$1,500/yr for 1–4 visits `[SNIPPET]`.

> **Requirement (decided 2026-08-27, not a research inference — Michael's call):**
> The contract/billing layer must support **one agreement spanning multiple trades, with per-trade
> line items and per-trade billing**. Not three per-trade agreements bundled and presented as one.
>
> **This holds at every tier, not just mid-market.** An earlier draft of this section framed it as
> a mid-market/commercial constraint. That framing was wrong and is corrected here: **small shops
> take commercial multi-trade work too** — a two-van shop servicing a strip mall or a small
> property-management portfolio signs the same shape of agreement as a 150-employee mechanical
> contractor. The tier changes the *volume* and the surrounding financial machinery (retainage,
> AIA, WIP — see G5), not the *shape of the agreement*. Treating multi-trade contracts as a
> mid-market feature would push the requirement behind a tier gate and reproduce, internally, the
> exact per-trade split decision (1) exists to avoid.
>
> Consequence for the data model: the agreement is the parent record and **trade is an attribute of
> the line item, not of the agreement**. Any model where trade sits on the contract header — or
> where a customer holds one agreement row per trade — fails this requirement, and fails it
> silently, because it still *looks* correct for a single-trade customer. That is the failure mode
> worth guarding against: it only surfaces on the first multi-trade renewal.
>
> The same rule propagates downstream to invoices, billing schedules and revenue reporting: per-trade
> line items must roll up to one agreement-level invoice *and* break out per trade for margin
> reporting. Both directions, from one record.

**Independent market corroboration for the line-item level, `[PRIMARY]`** — Fixner (Spain, serving
LatAm), fetched and read directly:

> *"Cada tipo de instalación (eléctrica, de fontanería, de climatización o fotovoltaica) responde a
> una tipología de **partidas** y **tiempos de ejecución** determinados."*

— each installation type has its own line-item typology **and** its own execution times, configured
inside **one** platform that consolidates work orders, material consumption and billing across all
of those types. That is the requirement above, stated by a shipping product, in a market that has
been doing multi-trade installers for years. It also adds a second per-trade attribute worth
carrying that the requirement above does not name: **estimated duration** is trade-specific too, not
just price.

Note the scope difference, and do not over-read the quote: Fixner's list includes *fotovoltaica* —
these markets treat solar/PV as a fourth sibling trade in the same model. That is evidence the
line-item-level split generalises beyond three, which is relevant if the trade set ever grows.

**Residential membership plans are the same engine at the small end.** ServiceTitan, Housecall Pro,
Successware and Field Ascend all ship service/membership-agreement management as *one* feature
across HVAC, plumbing and electrical — contract-expiration sorting for renewals, recurring
work-order generation, auto-updating expired cards before payment failure `[SNIPPET]`. This is the
concrete reason the requirement holds at every tier: the residential membership plan and the
commercial PPM contract are the **same record with different cadence and different money**, and
every incumbent already models them together.

**A4. Jurisdiction / permit authority.**
Permit *types* are trade-named (electrical, plumbing, mechanical) but the *authority*, portal,
fee schedule and submission are per-jurisdiction and shared. One project routinely pulls several
trade permits from the same authority `[SNIPPET]`. Permitio is explicitly built for
"HVAC, electrical, plumbing and solar contractors filing a steady stream of repeat residential and
light-commercial permits" — one product, four trades, gated by jurisdiction `[SNIPPET]`.
**Implication: jurisdiction is the primary key; trade is an attribute of the permit, not of the
authority.**

**A5. Compliance certificate issuance.**
UK: CP12, CP14, EICR, Minor Works, PAT, G3 unvented, WaterSafe — all issued from one product
(Commusoft) with offline mobile creation, auto-populated fields and digital signature `[SNIPPET]`.
AU/NZ: Certificate of Compliance is mandatory for gasfitting (NZ, since 2013 — *no gasfitting work
is complete until a CoC is issued*), for all plumbing and drainage work in NSW, and via the VBA
portal in Victoria `[SNIPPET]`.
**Implication: one certificate-instance engine + per-(trade, jurisdiction) form schema. The engine
is shared; the form definitions are exactly what "trade-gated module" should mean.**

**A worked instance, `[PRIMARY]` — Germany's DGUV V3 Prüfprotokoll**, fetched and read directly.
This is the most precisely specified certificate found anywhere in either pass, and it is worth
recording in full because it shows exactly what the shared engine must carry. The ten mandatory
fields (Pflichtangaben) for a court-proof protocol:

1. **Auftraggeber & Anlagenbetreiber** — company, address, contact
2. **Prüfobjekt** — device type, inventory number, location, manufacturer, serial number → *this is
   A2, the site asset registry, referenced by the certificate*
3. **Prüfer** — inspector name **and qualifications** → *this is A1, the credential registry,
   referenced by the certificate*
4. **Prüfdatum**
5. **Prüfverfahren & Messgerät** — standard applied, **and the calibration date of the measuring
   instrument**
6. **Messwerte** — protective-conductor resistance, insulation resistance, leakage current
7. **Sichtprüfung** — visual inspection of housing, cables, connectors
8. **Bewertung** — clear pass/fail with documented defects
9. **Nächster Prüftermin**
10. **Unterschrift des Prüfers** — paper or simple electronic signature per **eIDAS Art. 25**

Three things fall out of this that a naive certificate model would get wrong:

- **The certificate is a join, not a document.** Fields 2 and 3 are foreign keys into A2 and A1. A
  certificate engine that stores the tester's name as a string rather than a reference to the
  credential registry cannot answer "was this person qualified on the day they signed it."
- **Instrument calibration is a tracked object in its own right** (field 5). Nothing else in this
  research surfaced that requirement, and it does not fit the asset registry — the test instrument
  belongs to the contractor, not the customer site. It is a *third* dated-validity registry
  alongside person-credentials and customer-assets.
- **The next-due date is computed from a risk assessment, not looked up.** Vendor text, quoted:
  *"Richtwerte sind **keine Höchstgrenzen**. Die Gefährdungsbeurteilung kann kürzere Intervalle
  fordern."* Reference values run from **3 months** (Baustelle) to **24 months** (office IT), and
  German DGUV-specific tools ship a *Prüffristen-Rechner* deriving the interval per device from
  device type (ortsfest / ortsveränderlich), environment (Baustelle / Werkstatt / Büro /
  Außenbereich) and the failure rate at the last inspection `[SNIPPET]`. **A fixed
  `next_due = last + interval` field cannot express this.** See G17.

Norm caveat, kept honest: a search summary stated that DIN VDE 0701/0702 were withdrawn in 2021 and
replaced by DIN EN 50699 / DIN EN 50678. The page I actually fetched still references DIN VDE
0701/0702 and does not discuss withdrawal, citing DIN VDE 0100-600, DIN VDE 0105-100 and TRBS
1201/1203. **Treat the withdrawal claim as `[SNIPPET]`-tier and unconfirmed** — it does not change
the field list, but it would change which standard a German module names.

**A6. Skill/credential-constrained dispatch.**
Same engine everywhere; its input is A1. Dispatch selects "based on eligibility criteria,
customized rules and rankings" and is explicitly designed to assign across "third-party, employed,
or blended workforces" `[SNIPPET]`.

**A7. Outbound compliance submission to an external authority. — newly identified this pass**

This one was not visible until the trades were looked at side by side, and it is the pattern the
08-21 doc came closest to and still missed, because it treated each instance as a trade-specific
quirk rather than as one recurring shape. In all three trades, in multiple countries, completed work
generates a record that must be **submitted outward to a party that is not the customer** — and the
contractor's obligation is not discharged until that submission lands.

| Trade | Instance | Endpoint |
|---|---|---|
| Plumbing | Backflow / cross-connection test report | Water utility. **SwiftComply** is used by 700+ North American organisations; the **City of Dallas has required online submission through it since 14 Nov 2022**, charging **$10 for a passed test and nothing for a failed one**. Other portals: **Tokay**, **XC2** `[SNIPPET]` |
| Plumbing | Compliance certificate | AU: **VBA portal** (Victoria); NSW requires a CoC for all plumbing and drainage work `[SNIPPET]` |
| Electrical | Part P notifiable work | UK: registered competent person self-certifies via scheme (NICEIC/NAPIT); unregistered work is notified to Building Control (08-21 doc Area 4) |
| Gas / heating | Certificate of Compliance | NZ: **no general or high-risk gasfitting work is complete until a CoC is issued**; required since 2013 `[SNIPPET]` |
| HVAC | Refrigerant transaction / leak records | US EPA under §608 + AIM Act; EU F-Gas (08-21 doc Area 4) |

**Implication: this is one entity — an outbound compliance submission with a target authority, a
payload, a submission state, a fee, and a proof-of-receipt — instantiated per (trade, jurisdiction).
It is not five unrelated features.** The Dallas fee structure is the detail that proves it needs to
be a real modelled object rather than a PDF export: a submission can *cost money*, conditionally on
its own result, and something has to record that it happened.

### Tier B — repeats, but with a trade-keyed lookup behind it

**B1. Inventory / truck stock.** Same shape (per-vehicle stock, job consumption, restock,
serialised items, low-stock alerts, barcode, automated replenishment). What differs is the
**distributor catalogue** — Ferguson for plumbing/HVAC, and a different supply chain for
electrical. Ply, FieldPulse, eTurns, Aptora, QR Inventory all serve HVAC + plumbing + electrical
from one product `[SNIPPET]`.

**B2. Flat-rate pricebook.** Shared engine, per-trade categories — ServiceTitan does exactly this
today (§4). And the *content* is already sold cross-trade: Profit Rhino's ≈8,500 tasks cover
plumbing, HVAC and electrical in one book (§1a). Trade is a category on the task, not a separate
catalogue.

**B3. Union / prevailing-wage payroll.** One engine; fringe rates keyed by trade classification and
local `[SNIPPET]`.

**B4. Consumer financing attachment.** One integration surface; the split that matters is ticket
size ($25K Wisetack / $100K GreenSky), not trade (§1a).

**B5. Scheduling across job shapes.** One board handling one-off, recurring and multi-day work, with
per-day crew assignment and multi-day conflict detection — BuildOps ships exactly this for HVAC,
mechanical, electrical and plumbing simultaneously `[SNIPPET]`. Trade does not change the shape.

**B6. Distributor procurement.** The *protocol* is standardised and trade-neutral — **cXML** and
**OCI PunchOut**, **EDI 850 / 855 / 856 / 810** through gateways like SPS Commerce and TrueCommerce
— while the *counterparty* differs by trade `[SNIPPET]`. Punchout returns real-time contract and
matrix pricing plus available-to-promise by branch; Epicor **Eclipse** is described as the fit for
electrical **and** plumbing **and** HVAC distribution from one system, and CE PunchOut serves HVAC
parts specifically `[SNIPPET]`. So: one integration surface, a per-trade set of endpoints and
catalogues. Same shape as B1's truck stock, one layer up the supply chain.

**B7. Customer intake and communication.** By 2026 an entire bolt-on category exists — AI voice
agents answering, triaging, booking and dispatching after-hours calls, then **pushing structured
notes into ServiceTitan, Housecall Pro or Jobber** `[SNIPPET]`. Every vendor found markets to "HVAC,
plumbing, electrical" as one audience. Trade-neutral engine, trade-flavoured triage vocabulary
(a no-heat call, a burst pipe, a dead panel all mean "emergency"). See G18 — it is an *integration
boundary*, not a native capability, at every FSM examined.

**B8. Structured field capture at the asset.** **XOi** is the clearest example and is explicitly
cross-trade — HVAC, plumbing, electrical, MEP, construction and commercial kitchen from one product,
integrated into Davisware among others. What it captures is the interesting part: **instant dataplate
capture via OCR**, guided workflows, photo/video, AI-generated work summaries and structured service
history, feeding a searchable knowledge base built from a decade of technician-captured jobsite video
`[SNIPPET]`. **Dataplate OCR is the mechanism that populates A2** — make, model, serial — which is
otherwise the most error-prone manual field in the whole model. One capture engine, per-trade
equipment taxonomy behind it.

### Tier C — genuinely forked; must be trade-gated modules, not shared

- Calculation engines: **Manual J/D/S** (HVAC, and ACCA-approved-software-gated for code
  submission) vs **NEC Article 220** load calcs (electrical) vs **UPC/IPC fixture-unit + venting**
  (plumbing). Three unrelated engines. 08-21 doc Area 6.
- Estimating assemblies and labour databases (§1b, G7).
- Refrigerant / F-gas ledger — HVAC only (G11).
- Backflow / cross-connection — plumbing only as *content*. Note the split: the **submission
  mechanism** is shared (A7), the **test form and the utility's rules** are not.
- **Manufacturer warranty registration — HVAC-weighted, and left manual by the FSM platforms.**
  ServiceTitan integrates with registration portals for select brands (Carrier, Lennox, Trane), but
  post-install registration is **not a native workflow**; Carrier and Trane have the most mature
  bulk-registration tooling for high-volume dealers while Lennox and Goodman remain largely manual
  portal entry. Service Fusion (EverCommerce) announced a Trane/American Standard integration
  `[SNIPPET]`. There is no plumbing or electrical analogue of comparable weight — water heaters
  register, but nothing in electrical does at this scale.
- **Test-instrument certificate ecosystems — electrical only, and they are outside FSM entirely.**
  **Megger CertSuite** imports results directly from MFT-X1 / PAT400 instruments over Bluetooth and
  emails certificates; **Fluke TruTest** imports measurement results from instruments and formats
  them into printable test certificates with company logo and electronic signature `[SNIPPET]`.
  This is a real competitive boundary specific to electrical: **the certificate a UK/EU electrician
  produces may already be generated in the instrument vendor's own software**, not in their job
  management tool. No equivalent instrument→certificate ecosystem surfaced for HVAC (Testo,
  Fieldpiece) or plumbing — see §7.

### The seam this suggests

The pattern that fell out of every market, stated as an observation rather than a recommendation:
**the shared core is the record of who/what/where/when — people, credentials, sites, assets,
contracts, jurisdictions, stock, money. The trade-gated part is the calculation and the form.**
The Dutch source stated the identical split independently: same werkbon and planning, different
*calculations and inspections*.

---

## 4. Trade-gating precedent — what the market actually does

Decision (1) says trade-gated modules unlocked inside an existing account. Here is what exists.

**ServiceTitan `[PRIMARY]` — verified directly against ServiceTitan's own help docs, not marketing.**
A Business Unit carries an explicit **`Trade` field**. Vendor wording:

> "**Trade** — Select the trade attribute of the business unit. This allows for refined filtering."
> "**Division** — Select the division to which the business unit is attached. This is used for some
> KPI calculations and allows for refined filtering."

Business units also carry Name, Official Name, Email, Phone, **License Number**, Tags, Currency,
Warehouse settings, invoice/authorization fields, and payroll/QuickBooks fields. Pricebook
*categories* are assigned to business units, and that assignment controls what technicians see in
ServiceTitan Mobile — only techs in the assigned BUs see items in that category `[SNIPPET]`. There
is also a BU-level override that hides all pricing on a job and **overrides the technician's own
permission** even when they hold *View Item Prices* `[PRIMARY]`.

**The critical distinction, and it is the finding of this section:** ServiceTitan's Trade field is
an **attribute for filtering and reporting**. Pricebook gating runs off **business unit**, not off
trade, and it gates **visibility**, not **entitlement**. Nothing found gates *whether a customer
has bought a trade*.

**Simpro** sells add-ons (Takeoffs, mobile, fleet/GPS, SMS) at $49–$250+/user/month with pricing
"customized to include the add-ons you need" — modular, but modular by **function**, not by trade
`[SNIPPET]`. Admicom's Nordic product family is likewise modular by function `[SNIPPET]`.

**Housecall Pro** is the only vendor packaging by trade, and it does so as **separate SKUs with
preconfigured onboarding/templates/defaults on one platform** — with the second-trade path
undisclosed (G1).

**Conclusion for decision (1):** the market gates by *business unit*, *function-module*, or
*SKU-at-signup*. **A per-trade entitlement that unlocks inside an existing account was not found at
any vendor, in any market, in either research pass.** That is genuinely white space — and it is
also why there is no precedent to copy: the seam has to be designed, not borrowed. State it as an
opportunity with no external validation, not as a proven pattern.

---

## 5. Applicability to existing SAIRN apps — flagged as its own section, nothing built

The research turned up one clean cross-application finding. Both rows below were verified against
the real code in this clone, not assumed.

### Row 1 — StoneDesk Subcontractor Portal: no compliance layer at all

**Verified state.** `stonedesk.html:28823-28827` — the entire subcontractor roster payload is:

```
sub_id, name, trade, phone, email, active
```

Plus ID+PIN portal login (`:31260`), job assignment (`:28913`), and AI field-progress photo
inspection with a `sub` mode (`:34734`). A grep of the whole file for insurance/COI/W-9/licence
fields on the subcontractor record returns **nothing** — the four `insurance` hits in the file are
SAIRNbiz cost inputs and SAIRNcare/senior document-reading prompts, unrelated.

**What the market says.** Subcontractor insurance-compliance tracking is a mature, crowded
category: Certificial, MyCOI, TrustLayer, Jones, Billy, SmartCompliance, CertFocus, BCS,
Constrafor `[SNIPPET]`. Named table stakes are real-time expiry monitoring, automated renewal
alerts, and source verification. BCS syncs with Procore so compliance tracking starts automatically
the moment a subcontractor is added to a project `[SNIPPET]`.

**The honest nuance — this is a category-wide gap, not just StoneDesk's.** Fieldpoint, a real
commercial FSM product with a dedicated subcontractor-management page, covers scheduling-board
visibility, GPS, T&M/expense entry through a portal, and payment vouchers generated alongside the
customer invoice — and covers insurance, licence and compliance-document tracking **not at all**
`[PRIMARY]`. Field Ascend's subcontractor page likewise says nothing about certificates, licence
tracking, expiry or portals `[PRIMARY]`. So StoneDesk is not behind the FSM field here; it is
behind the *construction* field, which is where its subs actually come from.

**Status — decided 2026-08-27: leave it alone for now.** StoneDesk is an existing shipped app and
this was not in scope for this task. **Logged as its own backlog row** in `SAIRN-BACKLOG.md`
("StoneDesk Subcontractor Portal has no compliance layer…"), with the verified field list, the
category-wide-gap nuance, the SAIRNbuild contrast, and what "done" would look like. Nothing built.
StoneDesk already carries the two hooks this would need if it is ever picked up — an `active` flag
on the roster and a single assignment path at `subxAssign`.

### Row 2 — SAIRNbuild: already ahead of the commercial FSM products, and it enforces

**Verified state.** `sairnbuild.html` subcontractor records already carry
`w9_on_file`, `coi_expiry`, `licence_no`, `licence_expiry`, `prequal_status`,
`financial_capacity`, `safety_record`, `references_checked`, `bonding_capacity`,
`current_backlog_pct` (`:2455-2459`), plus company-level `insurance_carrier`,
`insurance_policy_no`, `insurance_expiry` (`:2571`, `:6084-6121`), and Lien Waivers.

And it **enforces**, which is the part that matters:

- `subComplianceIssue()` (`:6229`) flags COI or licence within 30 days.
- Dashboard attention feed surfaces expired/expiring COI and licence on first screen after login
  (`:4400-4406`).
- "Eligible to Bid" requires **both** halves — prequalified **and** compliant (`:5139`).
- Award is **hard-blocked**: `:3864` — *"Cannot award to … — not eligible to bid (…). Fix on the
  Subcontractors panel first."*

**Finding:** SAIRNbuild's subcontractor compliance model is **more complete than the two commercial
FSM subcontractor products examined**, and its award gate is the enforcement step G3 says the
market claims but does not document. Nothing here needs revisiting on the evidence found. If
anything, it is the reference implementation the other apps should be measured against — and it is
also directly reusable material for SAIRNmechanical's A1 credential registry, since prequal +
expiry + hard gate is the same shape a licensed-trade dispatch gate needs.

**Net:** one row to revisit (StoneDesk), one row confirmed sound (SAIRNbuild). No code changed.

---

## 6. Things that moved since the 2026-08-21 pass

- Housecall Pro's trade packages launched **15 July 2026** and are reported at **$96K new MRR** —
  the 08-21 doc had the launch but not the revenue signal `[SNIPPET]`.
- The Japan gap is **partially closed** (ZAC, プロワン are genuinely 設備-industry, not generic
  施工管理) — see §1c. The 08-21 doc's flat "no evidence found" is now too strong.
- ServiceTitan's Business Unit **Trade field is confirmed from primary vendor documentation**
  (§4). The 08-21 doc inferred multi-trade-as-configuration from architecture; it is now verified,
  and the *visibility vs entitlement* distinction it did not draw is the actionable part.
- China is newly characterised: 机电安装 project-ERP category, no service-dispatch equivalent (G9).
  Not covered at all on 08-21.
- French **e-invoicing mandate in 2026** surfaced as a dated market-entry requirement `[SNIPPET]`.
- **The consolidator/PE tier was absent from both the 08-21 doc and this document's first pass**
  (§1b-i). It is the single strongest external validation of decision (1) found anywhere, and it
  came from M&A sources rather than software sources — which is why two software-focused research
  passes both missed it. Worth remembering as a method note: the buyers of these businesses had
  evidence the vendors' marketing did not.

---

## 7. No coverage found — stated explicitly, and corrections

### Not found (searched, genuinely absent — not inferred)

1. **Any vendor's documented commercial or technical path for an existing customer to add a second
   trade to a live account.** Two independent passes, six weeks apart, English and non-English.
   Housecall Pro publishes trade packages and no second-trade pricing. This is a real hole in the
   public record, not a search failure.
2. **Any per-trade *entitlement* gate at any vendor.** ServiceTitan gates visibility by business
   unit; Simpro and Admicom gate by function-module. Nothing gates by purchased trade (§4).
3. **Any Chinese service-dispatch FSM for these trades.** All results were 机电安装 project ERP (G9).
4. **Any Japanese product organised around per-trade licensing compliance** (e.g. 電気工事業者登録)
   the way UK certificate tools are (G10).
5. **Cordel (Norway)** — queried by name alongside Admicom/Visma; returned nothing. Cannot confirm
   it exists in this segment.
6. **Klipboard** — queried by name in the UK compliance-certificate search; returned nothing.
   Present in the UK market per general knowledge, but this pass produced no citation for it, so it
   is not claimed above.
7. **Fergus, AroFlo, Tradify AU/NZ compliance-form specifics** — the AU/NZ query returned the
   *regulatory* requirements (NZ CoC, NSW plumbing CoC, VBA portal) but no vendor page detailing how
   those products implement them. The regulation is cited; the vendor implementation is not.
8. **Simpro's published tier/add-on breakdown** — `simprogroup.com/pricing` returned **HTTP 403** to
   direct fetch. Simpro pricing above is `[SNIPPET]`-tier only and should not be treated as firm.
9. **Salesforce contractor-management page** — returned **HTTP 403** to direct fetch. Its
   credential-blocking claim is therefore unverified; see correction C1.
10. **Direct trade-community verbatim** (r/HVAC, r/electricians, r/Plumbing) — same limitation the
    08-21 doc hit; not retrievable through available search. Unchanged, still a gap.
11. **Any South Korean contractor-side FSM for these trades.** Korean-language search returned
    CMMS/EAM (설비보전/설비자산관리) — asset-owner-side plant and facility maintenance — plus Capterra
    Korea listings of foreign products and Synchroteam (French) marketed in. The domestic category
    appears to be facility-owner software, not trade-contractor software (G16).
12. **Any HVAC instrument→certificate ecosystem comparable to electrical's.** Queried Testo and
    combustion analysers by name alongside Megger/Fluke; Megger and Fluke returned mature products,
    **Testo returned nothing in these results**. Whether an HVAC equivalent exists and simply did
    not rank, or genuinely does not exist, is unresolved — do not assume either.
13. **Any per-trade pricing at Profit Rhino / Callahan Roach.** The $179/user/month figure is for the
    product as a whole; no evidence found that the three trades are sold or priced separately.
    Stated as "not found separately," not as "confirmed bundled."
14. **The Housecall Pro second-trade path, again.** Re-searched this pass with different phrasing
    (pricing, cost, add second trade). Still nothing. This is now a twice-confirmed absence.
15. **Cordel (Norway), again.** Queried a second time in Swedish/Norwegian alongside Handyman,
    Next and Fieldly. Still nothing. Two failed attempts — stop looking unless someone has a
    first-hand reason to think it is relevant.
16. **FieldPulse and Sera published pricing.** Neither publishes; both require a sales conversation
    `[SNIPPET]`. Any figure quoted for them elsewhere should be treated as third-party estimate.
17. **Southeast Asia, Central/Eastern Europe beyond Poland, Greece, Czechia, Russia** — not searched
    this pass. Absent from this document by omission, not by finding. Do not read the gap as
    evidence of anything.
18. ~~Whether any consolidator platform runs a single shared system across its brands.~~
    **CLOSED 2026-08-27 — see §1b-ii.** They standardise on ServiceTitan, one tenant per acquired
    company plus an Enterprise Hub roll-up layer, and staff dedicated ServiceTitan integration roles
    to onboard each acquisition. Answered primarily from a **job posting**, which was the fastest
    signal by a wide margin — worth remembering as a method for the next time a private company's
    internal tooling matters.
19. **Whether any FSM anywhere supports an in-place trade *entitlement* unlock.** Now asked three
    times across two documents, including against the consolidator tier where the incentive would be
    strongest. Nothing. The absence is now explained (§1b-ii: the incumbent's answer is a new
    tenant), which is stronger than the earlier bare "not found."
20. **What the non-ServiceTitan consolidators run.** §1b-ii establishes ServiceTitan across Apex,
    Sila, Wrench, Vertex, Cobalt and Galaxy. It does **not** establish what the remaining platforms
    (Redwood, ResiXperts, Ally, Southern Home Services, Authority Brands, Legacy) run, and no source
    was found claiming ServiceTitan is universal in this tier. Do not generalise from six to
    twenty-plus.
21. **Whether Enterprise Hub can hold multiple trades in one tenant, or requires one per trade.**
    Business units carry a `Trade` attribute inside a tenant (§4) and tenants are per acquired
    company (§1b-ii) — but no source found addresses what happens when a single acquired company
    already runs two trades. The two mechanisms are documented separately and never together.

### Corrections to claims that search summaries asserted but primary sources did not support

**C1. "Expired credentials automatically remove the technician from the dispatch pool."**
A search summary attributed this to Field Ascend, along with a specific issuing-authority list
("state licensing board, EPA, NATE, manufacturer") and a "60 days before expiry" alert threshold.
**The primary page does not say any of it.** Fetched directly, it says only that Field Ascend
"records issue dates, expiration dates and renewal work so managers can see certificates that are
valid, expiring soon or expired," and offers "certification visibility alongside scheduling and
dispatch software" for "better allocation decisions." No named credentials, no named authorities,
no automatic dispatch exclusion `[PRIMARY]`. **Automatic credential-based dispatch blocking is a
claim I could not verify at any vendor.** That matters for §3 A6 and for G3 — treat it as unproven
market capability, not as a bar SAIRNmechanical must clear.

**C2. "Automated compliance checks reduce permit application rejections by 62–76%."**
This is vendor-blog marketing copy with no cited study. Do not repeat it in any proposal. The
underlying structural facts (≈30,000 permit-issuing jurisdictions; multiple trade permits per
project) are independently corroborated and usable; the percentage is not.

**C3. "60% of data loss during CRM migrations is caused by field mapping errors."**
Carried over from the 08-21 doc, which already flagged it — attributed to a "National Association
of Small Business 2024 technology survey" that could not be confirmed to exist. Re-flagging so it
does not get laundered into fact by being repeated across two documents. **Do not cite it.**

**C4. Clavei's "40% faster quoting / 25% higher project profitability."**
Vendor-published customer-outcome claim, no methodology. Directional only.

**C5. "15–25% of denied HVAC warranty claims trace back to a missed registration window."**
Sourced from a vendor blog selling registration automation. No study cited. The *structural* fact —
that registration windows exist and that FSM platforms leave the step manual — is corroborated
across several sources and is usable; the percentage is not. Do not repeat it.

**C6. "Contractors with 30%+ of revenue from membership programs outperform emergency-only
operations by 4–6 net margin points ($20K–$30K additional annual profit on $500K revenue)."**
Vendor-blog claim with no methodology and no sample. The underlying observation — that every
incumbent ships membership/agreement management as a core feature across all three trades — stands
on its own without the number. Do not use the figure in any proposal or pitch.

**C7. Guardian's app map claimed a SAIRNmechanical file that did not exist — RESOLVED 2026-08-28, and the resolution went the other way.**
The finding below was correct when written and is now closed: `sairnmechanical.html`
**exists on `origin/main`** (88,781 bytes), recovered from an unmerged branch in
`bb9dbb3` and de-fabricated in `4114e22`. Guardian's map was not drifting — it
was describing an app that existed on a branch nobody had merged. Kept as
written, because "the map is wrong" and "the file is missing" were
indistinguishable from where I stood, and the correct move at the time was still
to state what the read showed rather than to guess which.

Original finding, as recorded 2026-08-27:
Not a research claim, but found while verifying §9 and worth recording here because it is the same
class of error: `sairn-guardian-v2`'s App File Map lists `SAIRNmechanical | sairnmechanical.html |
#84CC16`, and `api/claude.js` allowlists the `sairnmechanical` app_id. **Neither the working tree
nor `origin/main` contains `sairnmechanical.html`** — `git cat-file -e origin/main:sairnmechanical.html`
returns *"path does not exist."* Guardian's own map has drifted, in exactly the way its description
says it is meant to catch.

---

## 8. Architecture-assumption check — asked for, and there is nothing on record to check against

I was asked to **confirm** that the shared platform's contract/billing layer supports one agreement
spanning multiple trades with per-trade line items and per-trade billing, "same shape as the
cross-trade billing requirement already on record."

**I cannot confirm it, because none of the three things that question presupposes exist. Reporting
that plainly rather than confirming against nothing.**

| Presupposed | Actual state, verified this pass |
|---|---|
| A cross-trade billing requirement already on record | **Not found.** `grep -rin "cross-trade\|multi-trade\|per-trade"` across every `.md` in the repo returns hits in **only two files** — the 2026-08-21 research doc and this one. Nothing in `SAIRN-BACKLOG.md`, `docs/SAIRN-OPEN-WORK-INDEX.md`, any handoff, or any of the four `SAIRN-ACTIVE-WORK-*.md` files. |
| A current SAIRNmechanical architecture assumption | **Not found.** No design doc, no spec, no schema file, no plan. |
| A SAIRNmechanical codebase to check it against | **Did not exist on 2026-08-27; DOES exist as of 2026-08-28** — `sairnmechanical.html`, 88,781 bytes on `origin/main`, recovered from an unmerged branch (`bb9dbb3`). Everything this section concludes still holds: the spec was written before any code existed, which was the cheap moment. |

What *does* exist, and is the whole of it:

- A row in `sairn-guardian-v2`'s App File Map asserting `sairnmechanical.html` / `#84CC16` — an
  assertion about a file that is not there (see §7 C7).
- `sairnmechanical` in the `KNOWN_APP_IDS` allowlist in `api/claude.js`.
- Two commits from an earlier era — `c12e8b1` *"SAIRNmechanical v1.0 — NEW AI platform for
  HVAC/Plumbing/Electrical, 16 pages, dispatch+agreements"* and `715d5c1` *"SAIRNmechanical v1 —
  HVAC & Mechanical, all patterns, Field Quote, Suite, Doc Scanner"*. Whatever those built is not on
  `origin/main` today. **I have not read them** and am not claiming what their agreement model was;
  if a prior contract/billing shape matters, that history is where to look, and it should be read
  before it is trusted.
- The 2026-08-21 research doc, written to back the now-reversed three-standalone-apps plan.

**So the honest answer is the good one: there is nothing built, and therefore nothing to unbuild.**
The requirement in §3 A3 is being recorded *before* the first line of schema exists, which is the
only cheap moment to record it. Nothing needs flagging as at-risk, because nothing is on top of it
yet.

**One thing genuinely does need flagging, though, and it is the reason this section exists rather
than a one-line "n/a":** a requirement that lives only in a research document is not on record in
any operative sense. The 08-21 doc proves the failure mode — it sat untracked and invisible in a
retired checkout for four days, and would have been deleted by a cleanup plan that only looked at
tracked files. If the one-agreement-many-trades rule is to bind whatever gets built, it needs to
land somewhere a build session will actually read: the SAIRNmechanical spec when one is written, or
`SAIRN-BACKLOG.md` / `docs/SAIRN-OPEN-WORK-INDEX.md` in the meantime. **I have not done that** — it
is a decision about where the platform's requirements live, not a research finding, and it is
Michael's call which of those is the right home.

---

## 9. Close-out — compiled structure and what the frequency data says

Research closed 2026-08-27. This section compiles what the document contains; it adds no new
findings. Everything here indexes back to a numbered section above.

### 9a. All gap rows, with frequency

Trades = how many of the three it bites. Regions = how many distinct markets the evidence spans.

| # | Gap | Trades | Regions | Evidence tier |
|---|---|:--:|:--:|---|
| G1 | No published "add a second trade" path at any vendor | 3 | global | `[PRIMARY]`+`[SNIPPET]` |
| G2 | Subcontractor compliance not integrated into dispatch | 3 | US | `[PRIMARY]` |
| G3 | Credential-expiry → dispatch-eligibility enforcement claimed, not documented | 3 | global | `[PRIMARY]` |
| G4 | Regulatory *content* genuinely non-shareable | 3 | global | 08-21 doc |
| G5 | Mid-market financial layer absent from SMB tools | 3 | US | `[SNIPPET]` |
| G6 | Commusoft-class tools degrade at the commercial transition | 3 | UK/EU | `[SNIPPET]` |
| G7 | Estimating does not cross the mechanical↔electrical line | 1 (elec) | US | `[SNIPPET]` |
| G8 | Permit filing fragmented by jurisdiction **and** trade | 3 | US (~30k jurisdictions) | `[SNIPPET]` |
| G9 | China: no service-dispatch product | 3 | CN | `[SNIPPET]` |
| G10 | Japan: no licensing-compliance-organised product | 3 | JP | `[SNIPPET]` |
| G11 | Refrigerant/F-gas ledger has no analogue in the other two | 1 (HVAC) | US+EU | 08-21 doc |
| G12 | Lock-in / data portability dominates real-world pain | 3 | global | 08-21 doc |
| G13 | Manufacturer warranty registration left manual | 1½ (HVAC) | US | `[SNIPPET]` |
| G14 | Electrical certificates already live in instrument-vendor software | 1 (elec) | UK/EU | `[SNIPPET]` |
| G15 | **Outbound compliance submission is nobody's modelled object** | 3 | **US/UK/AU/NZ/EU** | `[SNIPPET]` |
| G16 | South Korea: no contractor-side FSM | 3 | KR | `[SNIPPET]` |
| G17 | **Inspection intervals treated as fixed lookups, not computed from risk** | 3 (elec sharpest) | **DE/UK/NL/AU** | `[PRIMARY]` |
| G18 | Customer intake / AI call handling is a bolt-on everywhere | 3 | US | `[SNIPPET]` |
| G19 | Apprenticeship/OJT-RTI progression separate from credential tracking | 3 | US | `[SNIPPET]` |
| G20 | Test-instrument calibration validity tracked nowhere | 2 | DE | `[PRIMARY]` |
| G21 | *Resolved and inverted* — consolidators are well served; the **organically-growing independent** is not | 3 | global | `[PRIMARY]` |

### 9b. All cross-trade patterns

| ID | Pattern | Verdict |
|---|---|---|
| **A1** | Credential registry (person → credential → authority → jurisdiction → expiry), + apprenticeship progression upstream | Shared table, trade-tagged rows |
| **A2** | Site asset registry (customer → site → asset, make/model/serial/install/warranty/history) | Shared schema, per-trade taxonomy |
| **A3** | **Recurring agreement — PPM / AMC / membership. CORE REQUIREMENT, every tier** | One agreement, many trades; **trade on the line item, never the header** |
| **A4** | Jurisdiction / permit authority | Jurisdiction is the key; trade is an attribute of the permit |
| **A5** | Compliance certificate issuance (CP12/EICR/CoC/DGUV V3/…) | One engine + per-(trade, jurisdiction) form schema. The certificate is a **join** into A1 and A2 |
| **A6** | Skill/credential-constrained dispatch | Shared engine; input is A1 |
| **A7** | **Outbound compliance submission to an external authority** | One entity — authority, payload, state, fee, receipt — per (trade, jurisdiction) |
| **B1** | Inventory / truck stock | Shared shape, per-trade distributor catalogue |
| **B2** | Flat-rate pricebook | Shared engine; content already sold cross-trade (Profit Rhino, ~8,500 tasks) |
| **B3** | Union / prevailing-wage payroll | One engine; fringe keyed by trade classification |
| **B4** | Consumer financing | One surface; splits on ticket size, not trade |
| **B5** | Scheduling across job shapes (same-day / recurring / multi-day) | One board; trade-neutral |
| **B6** | Distributor procurement (cXML, OCI PunchOut, EDI 850/855/856/810) | One protocol, per-trade endpoints |
| **B7** | Customer intake / AI call handling | Trade-neutral engine, trade-flavoured triage |
| **B8** | Structured field capture (dataplate OCR → A2) | One capture engine, per-trade equipment taxonomy |
| **C** | **Forked — must be trade-gated:** Manual J/D/S vs NEC Art. 220 vs UPC/IPC fixture units; estimating assemblies; refrigerant/F-gas ledger; backflow test content; warranty registration; instrument-certificate ecosystems | Not shareable |

**The seam, restated:** the shared core is the record of who / what / where / when. The trade-gated
part is the calculation and the form.

### 9c. The two standout findings

1. **PE consolidator thesis (§1b-i, §1b-ii).** Combined HVAC+plumbing+electrical platforms dominate
   PE deployment over pure-play — verified primary. ~800 acquisitions since 2022. **But** the
   segment is already served: ServiceTitan Enterprise Hub, one tenant per acquisition plus roll-up,
   500+ add-ons/year at sub-2-month integration, customers staffing full-time ServiceTitan
   integration specialists. It validates the *structure* of decision (1); it is **not** an open
   market. Filed to memory as its own go-to-market entry.
2. **DGUV V3 as the reference certificate model (§3 A5).** Ten mandatory fields, primary-verified.
   Three modelling consequences a naive design gets wrong: the certificate is a **join** into A1 and
   A2, not a document; **instrument calibration is a third dated-validity registry** (contractor-
   owned, neither person nor customer-asset); and the next-due date is **computed from a hazard
   assessment**, not looked up — *"Richtwerte sind keine Höchstgrenzen."*

### 9d. Prioritised capability list, derived from frequency

**Scope note, so this is not misread:** this ranks **platform capabilities**, by how many trades and
regions each gap spans. **It is not a build order across the three trades** — that remains deferred
by decision (2) and nothing here bears on it.

**Read the caveat before the list.** Gap frequency measures *where competitors are weak*, not *what
customers need first*. Those are different questions and they disagree. G15 and G17 are the widest
gaps in the document precisely because nobody has built them — which also means no customer is
currently choosing a vendor on them. Table stakes must ship regardless of whether they appear as
gaps at all. The list below is ordered by **frequency × prerequisite depth**, with table-stakes
items called out as such even where their gap score is low.

| # | Capability | Why here | Gap frequency |
|:--:|---|---|---|
| 1 | **Credential registry + expiry + dispatch eligibility (A1 → A6)** | Underpins A5, A6, A7 and G2/G3/G19. Nothing else can be gated correctly until this exists. SAIRNbuild already ships a proven enforcement shape (prequal + expiry + hard block at award) to model on — see §5 Row 2 | 3 trades, every region |
| 2 | **Site asset registry (A2)** | Prerequisite for A3, A5, A7, B8, G13. Table stakes — every incumbent has it | 3 trades, every region |
| 3 | **Multi-trade agreement + per-trade line-item billing (A3)** | Already a fixed non-negotiable requirement, not a discretionary priority. Cheapest to get right before any schema exists; silently wrong if deferred | 3 trades, every region — PPM (UK/US), AMC (India/Gulf), membership (US) |
| 4 | **Trade entitlement model (G1 / G21)** | The differentiator, and **retrofitting entitlement is the expensive class of change**. Must be present in the data model from the first table even if no second trade ships for a year | 3 trades, global |
| 5 | **Compliance certificate engine, with computed intervals (A5 + G17 + G20)** | Highest-value *differentiating* gap. Requires 1 and 2 to exist first — the certificate is a join into both | 3 trades; DE/UK/NL/AU/NZ |
| 6 | **Outbound compliance submission (A7 + G15)** | Widest region breadth of any single gap in the document, and modelled by nobody. Depends on 5 | 3 trades; US/UK/AU/NZ/EU |
| 7 | **Pricebook categories (B2), job-shape scheduling (B5), truck stock (B1)** | Table stakes across the board; low gap score precisely *because* everyone has them. Not optional, just not differentiating | 3 trades, every region |
| 8 | **Mid-market financial layer (G5)** — retainage, AIA G702/G703, WIP, certified payroll, lien waivers | Hard boundary where SMB tools break. US-shaped; UK/EU analogues differ | 3 trades; US |
| 9 | **Integration surfaces — procurement (B6), intake (B7), field capture (B8)** | Established protocols and an existing bolt-on ecosystem. Integrate rather than rebuild | 3 trades; US/EU |
| 10 | **Per-trade forked content (Tier C)** — load calcs, estimating assemblies, refrigerant ledger, warranty registration, instrument imports | Genuinely trade-specific; the natural content of a trade-gated module. Sequencing here **is** the deferred build-order question and is deliberately not decided | 1–2 trades each |

**Two things this list deliberately does not do.** It does not recommend building the permit-filing
capability (G8) — that is a 30,000-jurisdiction problem with specialist vendors (Permitio,
PermitFlow) already on it, and it is an integration target, not a build. And it does not treat the
consolidator segment as a target (§1b-ii) — the frequency data points at the organically-growing
independent instead.

---

## 10. Sources

**Primary (fetched and read directly):**
[ServiceTitan — Add and edit business units](https://help.servicetitan.com/docs/add-and-edit-business-units) ·
[Fieldpoint — Subcontractor management](https://fieldpoint.net/subcontractor-management/) ·
[Field Ascend — Technician training & certification](https://field-ascend.com/en-us/technician-training-certification-software) ·
[Field Ascend — Subcontractor management](https://field-ascend.com/en-us/subcontractor-management-software) ·
[Fixner — partes de trabajo para empresas instaladoras](https://fixner.com/blog/partes-de-trabajo-instaladoras)

**Pricebook / financing / memberships / warranty / instruments (added 2026-08-27):**
[Profit Rhino (powered by Callahan Roach)](https://profitrhino.com/) ·
[Profit Rhino + Housecall Pro guide](https://help.housecallpro.com/en/articles/8754493-profit-rhino-with-housecall-pro-a-complete-guide) ·
[Profit Rhino / Callahan Roach merger (ACHR News)](https://www.achrnews.com/articles/141956-flat-rate-pricing-experts-profit-rhino-and-callahan-roach-join-forces) ·
[Wisetack vs GreenSky](https://www.wisetack.com/compare/wisetack-vs-greensky) ·
[ServiceTitan — service & membership agreement software](https://www.servicetitan.com/features/service-agreement-software) ·
[ServiceTitan — HVAC maintenance agreements](https://www.servicetitan.com/industries/hvac-software/maintenance-agreements) ·
[Housecall Pro — HVAC recurring service plans](https://www.housecallpro.com/resources/hvac-recurring-service-plan/) ·
[Trane warranty & registration](https://www.trane.com/residential/en/resources/warranty-and-registration/register/) ·
[Service Fusion × Trane / American Standard integration](https://www.stocktitan.net/news/EVCM/service-fusion-integrates-with-trane-and-american-standard-to-pce0raka9n2z.html) ·
[Megger CertSuite](https://www.megger.com/en/products/certsuite-installation) ·
[Fluke TruTest](https://www.fluke.com/en-us/product/fluke-software/trutest)

**What the consolidators run (added 2026-08-27, §1b-ii):**
[ServiceTitan — private equity solutions](https://www.servicetitan.com/market/private-equity-solutions-software) ·
[ServiceTitan — Sila Services Enterprise Hub success story](https://www.servicetitan.com/blog/success-story-sila-services-enterprise-hub) ·
[ServiceTitan — Sila Center of Excellence](https://www.servicetitan.com/blog/success-story-sila-services-center-of-excellence) ·
[ServiceTitan — Enterprise Hub](https://www.servicetitan.com/blog/enterprise-hub) ·
[ServiceTitan — rollup reporting docs](https://help.servicetitan.com/v1/docs/rollup-reporting-landing-page) ·
[Apex Service Partners — ServiceTitan Integration Specialist posting](https://simplify.jobs/p/0b99ce26-bc8f-4282-8166-3d6ef60e1149/Servicetitan-Integration-Specialist) ·
[CIO Dive — Wrench Group CIO](https://www.ciodive.com/news/incoming-CIO-tips-wrench-group/805180/) ·
[ServiceTitan × Cobalt Service Partners](https://www.servicetitan.com/press/servicetitan-strategic-partnership-cobalt-service-partners) ·
[ServiceTitan × Galaxy Service Partners](https://www.servicetitan.com/press/servicetitan-galaxy-partnership) ·
[ServiceTitan S-1 (SEC)](https://www.sec.gov/Archives/edgar/data/1638826/000119312524260611/d577298ds1.htm)

**Consolidator / PE tier (added 2026-08-27):**
[CT Acquisitions — private equity buying plumbing companies](https://ctacquisitions.com/guides/private-equity-plumbing-2026/) ·
[CT Acquisitions — 2026 plumbing PE roll-up tracker](https://ctacquisitions.com/plumbing-pe-rollup-tracker-2026/) ·
[DealSeam — HVAC PE roll-up tracker](https://dealseam.com/hvac-pe-rollup-tracker-2026) ·
[Beancount — HVAC/plumbing PE roll-up guide](https://beancount.io/blog/2026/07/11/hvac-plumbing-private-equity-roll-up-guide) ·
[Instalco](https://instalco.se/)

**Workforce / intake / procurement / field capture (added 2026-08-27):**
[GoSprout — apprenticeship management software](https://gosprout.app/best-apprenticeship-management-software-platforms-and-features/) ·
[GoSprout — apprenticeship compliance for IRA-ready projects](https://gosprout.app/apprenticeship-compliance-software-for-ira-ready-projects/) ·
[TradeColleges — skilled trades shortage outlook](https://tradecolleges.org/blog/skilled-trades-outlook/skilled-trades-shortage-opportunity) ·
[XOi — asset intelligence platform](https://xoi.io/) ·
[XOi — field service knowledge hub](https://xoi.io/field-service-knowledge-hub/) ·
[TradeCentric — how PunchOut integration works](https://tradecentric.com/blog/how-punchout-integration-works/) ·
[Ximple — electrical distributor PunchOut & EDI](https://www.ximplesolution.com/electrical-erp/ecommerce-punchout-edi/) ·
[CE PunchOut — HVAC parts procurement](https://ce-strategic.com/hvac-technology-tools/ce-punchout/) ·
[SuperDupr — AI answering services for home services](https://superdupr.com/blog/ai-answering-service-home-services)

**Germany — DGUV V3 (added 2026-08-27):**
[Operis — DGUV V3 Prüfprotokoll digital](https://www.operis-app.com/blog/dguv-v3-prufprotokoll-digital) ·
[ElektroPrüfManager](https://elektropruefung-software.de/) ·
[Prüfinstitut Bertsch — DGUV V3 Prüfprotokoll](https://www.bertsch-pruefinstitut.de/dguv-v3-pruefprotokoll/)

**Commercial mid-market (added 2026-08-27):**
[ServiceTrade](https://servicetrade.com/) ·
[ServiceTrade — mechanical contractor software](https://servicetrade.com/products/servicetrade-platform/features/mechanical-contractor-software/) ·
[ServiceTrade — electrical service contracting](https://servicetrade.com/industries/electrical-service-contracting/) ·
[ServiceTrade vs BuildOps](https://fieldservicesoftware.io/comparisons/servicetrade-vs-buildops/) ·
[BuildOps — field service scheduling](https://buildops.com/resources/field-service-scheduling-software/)

**Outbound compliance submission (added 2026-08-27):**
[SwiftComply — backflow prevention software](https://www.swiftcomply.com/backflow-prevention-software/) ·
[SwiftComply — backflow testers](https://www.swiftcomply.com/backflow-testers/) ·
[City of Dallas — backflow test reports](https://dallascityhall.com/departments/waterutilities/Pages/Backflow-Test-Reports.aspx) ·
[GreenLancer — PV interconnection](https://www.greenlancer.com/pv-interconnection) ·
[GreenLancer — EV permit design](https://www.greenlancer.com/ev-permit-design)

**US / multi-trade platforms:**
[ServiceTitan commercial playbook](https://www.servicetitan.com/commercial-playbook/services-and-departments) ·
[ServiceTitan plumbing flat rate](https://www.servicetitan.com/industries/plumbing-software/flat-rate) ·
[ServiceTitan — customize pricebook visibility](https://help.servicetitan.com/how-to/customize-views-for-techs) ·
[ServiceTitan pricing analysis](https://projul.com/blog/servicetitan-pricing-analysis-2026/) ·
[Housecall Pro pricing](https://www.housecallpro.com/pricing/) ·
[Housecall Pro pricing analysis](https://projul.com/blog/housecall-pro-pricing-analysis-2026/) ·
[Housecall Pro trade-package launch (GlobeNewswire)](https://www.globenewswire.com/news-release/2026/07/15/3327769/0/en/housecall-pro-launches-trade-specific-software-packages-for-hvac-plumbing-and-electrical-businesses.html) ·
[SaaSRise — HCP $96K MRR](https://www.saasrise.com/news/housecall-pro-adds-96k-mrr-with-tradespecific-saas-for-hvac-plumbing-and-electrical-a5f4591c-b035-4228-b070-69e732790528) ·
[Contractor Magazine — HCP trade software](https://www.contractormag.com/technology/news/55391529/housecall-pro-launches-trade-specific-software-for-hvac-plumbing-and-electrical-contractors) ·
[QuoteIQ — top CRMs for multi-trade contractors](https://myquoteiq.com/top-10-crms-for-multi-trade-contractors-in-2026/) ·
[FieldEx — multi-trade FSM platforms](https://www.fieldex.com/en/blog/best-multi-trade-field-service-software-platforms)

**Mid-market / enterprise:**
[ECI Davisware GlobalEdge](https://www.ecisolutions.com/products/globaledge/) ·
[Field Service Guide — BuildOps review](https://fieldserviceguide.com/buildops-2/) ·
[ServiceTrade — BuildOps competitors](https://servicetrade.com/resources/compare/buildops-competitors/) ·
[Simpro Premium](https://www.simprogroup.com/solutions/simpro-premium) ·
[Simpro — best electrical job management software](https://www.simprogroup.com/blog/best-electrical-job-management-software) ·
[Simpro vs Commusoft](https://www.simprogroup.com/comparisons/simpro-vs-commusoft) ·
[Joblogic vs Simpro (Software Advice)](https://www.softwareadvice.com/field-service/joblogic-profile/vs/simpro-enterprise/) ·
[ERP Research — construction accounting software](https://www.erpresearch.com/en-us/accounting-software-for-construction) ·
[CMiC — AIA billing guide](https://cmicglobal.com/resources/article/A-Contractors-Guide-to-AIA-Billing-Software) ·
[RedHammer — construction accounting buyer's guide](https://www.redhammer.io/blog/best-construction-accounting-software-for-contractors)

**Payroll / prevailing wage:**
[Worklio union payroll](https://worklio.com/solutions/union-payroll) ·
[FOUNDATION payroll](https://www.foundationsoft.com/software/payroll/) ·
[Points North WageIQ](https://www.points-north.com/wageiq) ·
[Miter — union payroll processing](https://www.miter.com/resources/union-payroll-processing/)

**Estimating:**
[Wendes](https://www.wendes.com/) ·
[McCormick Systems electrical](https://www.mccormicksys.com/industries/electrical/) ·
[Best electrical estimating software](https://softwareconnect.com/roundups/best-electrical-estimating-software/) ·
[Best mechanical estimating software](https://www.contravault.com/blog/10-best-mechanical-estimating-software-in-2026)

**Permits:**
[Permitio — best permit automation software](https://permitio.ai/blog/best-permit-automation-software) ·
[iPermit — permit management for contractors](https://www.ipermitusa.com/ipermit-blog/permit-management-for-contractors-field-service-software-2026) ·
[Skyvern — automate construction permits](https://www.skyvern.com/blog/automate-construction-permit-applications-inspection-forms/)

**Credentials / dispatch / assets / inventory / PPM:**
[Kahuna — field service skills tracking](https://kahunaworkforce.com/field-services/) ·
[Kahuna — skills-based dispatch](https://kahunaworkforce.com/field-service-dispatch-skills-management/) ·
[ServicePower — dispatch software guide](https://www.servicepower.com/resources/industry-guides/dispatch-software) ·
[cAction — asset tracking for field service](https://blog.caction.com/2026/08/13/asset-tracking-software-field-service-why-matters-how-choose-right-system/) ·
[Ply — truck inventory management](https://www.getply.com/blog/truck-inventory-management-software/) ·
[FieldPulse inventory](https://www.fieldpulse.com/features/inventory-management) ·
[eTurns service trucks](https://www.eturns.com/industries/service-trucks/) ·
[Commusoft — planned preventive maintenance](https://www.commusoft.com/en-us/blog/planned-preventive-maintenance/) ·
[Comparesoft — PPM](https://comparesoft.com/facilities-management-software/ppm/) ·
[Oxmaint — HVAC service agreement management](https://oxmaint.com/industries/hvac/hvac-service-agreement-management-software)

**Subcontractor compliance (COI category):**
[Certificial — COI tracking comparison](https://www.certificial.com/blog-post/we-compared-7-best-coi-tracking-software-in-depth-feedback-and-review) ·
[BCS — best COI tracking for construction](https://www.getbcs.com/blog/best-coi-tracking-software-for-construction) ·
[Vertikal — COI platforms compared](https://www.vertikalrms.com/article/best-coi-tracking-software-2026-top-coi-platforms-for-contractors/) ·
[SmartCompliance](https://smartcompliance.co/) ·
[Constrafor COI](https://www.constrafor.com/coi-certificates-of-insurance)

**UK / AU / NZ compliance:**
[Checker — best EICR & electrician software UK](https://checker.app/best-eicr-electrician-software-uk-2026/) ·
[Checker — Gas Safe records & certificates software](https://checker.app/best-software-gas-safe-records-certificates-uk-2026/) ·
[Checker — Joblogic alternative for compliance-heavy trades](https://checker.app/best-joblogic-alternative-for-compliance-heavy-trades-2026-guide/) ·
[Commusoft UK — best FSM software](https://www.commusoft.com/en-gb/blog/best-field-service-management-software-uk/) ·
[NZ Building Performance — energy work certificates](https://www.building.govt.nz/projects-and-consents/build-to-the-consent/energy-work-certificate) ·
[WorkSafe NZ — Certificate of Compliance](https://www.worksafe.govt.nz/topic-and-industry/gas/installations-and-networks/certification/certificate-of-compliance-coc/) ·
[Rules Mate — AU plumbing & gas licensing by state](https://rulesmate.com.au/insights/plumbing-gas-licensing-by-state-australia)

**Non-English markets:**
DE — [trusted.de Handwerkersoftware](https://trusted.de/handwerkersoftware) ·
[softwareabc24 SHK](https://www.softwareabc24.de/handwerker-software/shk/) ·
[softwareabc24 Elektriker](https://www.softwareabc24.de/handwerker-software/elektriker/) ·
[handwerk-digitalisieren SHK](https://handwerk-digitalisieren.de/handwerkersoftware-shk/)
FR — [Qonto — logiciels chauffagiste](https://qonto.com/fr/blog/gestion-entreprise/btp-construction/logiciel-chauffagiste) ·
[Adler — comparatif plombier/chauffagiste/clim 2026](https://www.adlertechnologies.eu/comparatif-logiciel-plombier-chauffagiste-climatisation-2026) ·
[ChaudièrePro comparatif](https://chaudierepro.com/meilleur-logiciel-chauffagiste) ·
[Organilog](https://organilog-chantier.com/les-5-meilleurs-logiciels-pour-plombiers-en-2024/)
ES — [SoftwareDoit — software instaladores](https://www.softwaredoit.es/software-construccion/software-gestion-empresas-instaladoras.html) ·
[Clavei ERP instaladoras](https://www.clavei.es/blog/software-de-gestion-erp-para-empresas-instaladoras-digitaliza-y-controla-tu-negocio-con-clavei/) ·
[Vendomia (caloryfrio)](https://www.caloryfrio.com/noticias/actualidad/vendomia-software-gestion-electricistas-climatizacion.html) ·
[Programación Integral](https://programacionintegral.es/software-erp-para-instaladores-y-mantenedores/)
IT — [Edilportale — 7 software commesse impiantistiche](https://www.edilportale.com/news/2026/05/aziende/7-software-per-la-gestione-delle-commesse-impiantistiche_110219_5.html) ·
[Perfetto](https://www.myperfetto.it/) ·
[iMio](https://www.imio.it/gestione-impianti-elettrici)
NL — [Red Factory — software installatiebedrijf](https://redfactory.nl/kennisbank/ai-automatisering/ai-installatiebedrijven/) ·
[NEN 3140](https://www.nen.nl/elektrotechniek/werkvoorschriften/laagspanninginstallaties) ·
[ArboTechniek NEN 3140](https://www.arbotechniek.nl/nen-3140/)
Nordics — [Admicom software portfolio](https://www.admicom.com/solutions/admicom-software) ·
[Admicom industries](https://www.admicom.com/industry)
BR — [Everflow — software hidráulica e instalações](https://everflow.com.br/blog/software-para-gestao/software-para-empresa-de-hidraulica-instalacoes/) ·
[Mais Controle ERP](https://maiscontroleerp.com.br/software-para-empresa-de-eletrica-e-instalacoes/) ·
[SIGE Cloud](https://sigecloud.com.br/sistema-para-instalacao-e-manutencao-eletrica)
IN — [Zoho FSM (PrecisionTech)](https://precisiontech.in/software/zoho/zoho-fsm/) ·
[Cloud FSM India roundup](https://constructionestimatorindia.com/6-best-cloud-based-field-service-management-software-in-india/)
PL — [iService HVAC](https://iservice.pl/branze/hvac/) ·
[Integra Serwis klimatyzacji](https://integra.com.pl/program-dla-serwisu-klimatyzacji-urzadzen-chlodniczych/) ·
[TaskForce HVAC](https://taskforce.guru/industries/hvac) ·
[Serwis Planner](https://serwisplanner.pl/program-do-serwisu-instalatorskiego) ·
[Serwisoft](https://www.serwisoft.pl/oferta/oprogramowanie/do-serwisu-klimatyzacji)
LatAm — [Fixner — partes de trabajo instaladoras](https://fixner.com/blog/partes-de-trabajo-instaladoras) ·
[ComparaSoftware México — órdenes de trabajo](https://www.comparasoftware.com/administracion-de-ordenes-de-trabajo)
SE/NO — [Handyman (GSGroup) fältservicesystem](https://handyman.gsgroup.se/) ·
[Handyman — elektrisk installation](https://handyman.gsgroup.se/bransch/elektrisk-installation/) ·
[Fieldly — projekt & arbetsorder](https://en.fieldly.com/product/projects-and-workorders) ·
[Installatörsföretagen](https://www.in.se/hitta-installator/)
PT — [ARTSOFT assistência técnica](https://www.artsoft.pt/solucao/software-assistencia-tecnica/) ·
[Webcraft — reparações climatização AVAC](https://webcraft.pt/software-assistencia-tecnica-gestao-reparacoes/software-reparacoes-climatizacao-avac)
TR — [Ekibim Sahada teknik servis programı](https://ekibimsahada.com/teknik-servis-programi/) ·
[ESN Sistem — iklimlendirme CRM](https://www.esnsistem.com/sektorler/iklimlendirme) ·
[FieldCo — iklimlendirme](https://www.fieldco.com.tr/sektorler/iklimlendirme/)
Gulf — [QuickAMC (Dubai)](https://quickamc.com/) ·
[FieldWeb UAE](https://www.thefieldweb.com/field-service-management-software-in-uae) ·
[Origami (SA) — FSM](https://origami.sa/en/blog/field-service-management-software-saudi-businesses/)
KR — [EquipCare365 CMMS](https://andami.co.kr/solution/cmms) ·
[XN Solution 설비자산관리시스템 (EAM)](https://www.xnsolution.co.kr/smart/eam_01.php) ·
[Capterra Korea 배관 소프트웨어](https://www.capterra.co.kr/directory/30673/plumbing/software)
CN — [泛普软件 机电安装工程管理](https://www.fanpusoft.com/jidian/824804.html) ·
[斗栱云 ERP](https://www.dougongyun.com/) ·
[建文软件](https://www.justwin.cn/) ·
[hecom 机电工程管理方案](https://hecom.cn/solution/index2_355.html)
JP — [ZAC 設備工事・メンテナンス業向け](https://www.oro.com/zac/industry/maintenance/) ·
[大塚商会 ERPナビ 設備工事業](https://www.otsuka-shokai.co.jp/erpnavi/category/construction/equipment/) ·
[プロワン 設備保全管理システム](https://pro-one-cloud.com/column/equipment-maintenance-management-system/) ·
[アスピック 工事管理システム比較](https://www.aspicjapan.org/asu/article/9049)

---

**Status: research CLOSED 2026-08-27.** Three passes, compiled in §9. No code written, no file
touched outside this doc, `SAIRN-BACKLOG.md` and the memory store. The StoneDesk row in §5 is logged
to the backlog and deliberately not built. Prior doc
`2026-08-21-plumbing-electrical-hvac-worldwide-research.md` is superseded in *framing* only — its
regulatory and lock-in content stands.

**One decision is recorded here rather than researched:** §3 A3, the one-agreement-many-trades
contract/billing requirement, **holding at every tier**. That is Michael's call of 2026-08-27,
including the explicit correction that it is a core platform requirement and not a mid-market
finding. See §8 for why it is not yet "on record" anywhere operative.

**Closed since the first pass of this document:** the thin plumbing and electrical SMB rows (§1a);
Turkey, the Gulf, Sweden/Norway, Portugal, Poland, Korea and LatAm (§1c); the consolidator/PE tier,
which turned out to be the strongest evidence in the document (§1b-i); and six further cross-trade
patterns — outbound compliance submission (A7), apprenticeship progression (A1 extension),
procurement/punchout (B6), customer intake (B7), consumer financing (B4) and job-shape scheduling
(B5).

**Closed in the final pass:** what the PE consolidators actually run (§1b-ii) — the last major open
question, answered from a job posting.

**Deliberately left open, and none of it blocks a build plan.** Recorded so nobody re-derives it or
mistakes the gaps for coverage:

1. **The two archived SAIRNmechanical v1 commits** (`c12e8b1`, `715d5c1`) — one mentions
   "dispatch+agreements". Nobody should assume what their agreement model was; read them before
   citing them (§8).
2. **What the other ~15 consolidator platforms run** (§7 item 20) — six are established on
   ServiceTitan; do not generalise from six to twenty-plus.
3. **Whether one Enterprise Hub tenant can hold multiple trades** (§7 item 21) — the two mechanisms
   are documented separately and never together.
4. **The HVAC instrument-integration question** (§7 item 12) — electrical has Megger/Fluke; whether
   HVAC has an equivalent is genuinely unresolved.
5. **Markets not searched at all:** Southeast Asia, Central/Eastern Europe beyond Poland, Greece,
   Czechia, Russia, Quebec-French Canada (§7 item 17).
6. **The DGUV norm-withdrawal question** (§3 A5 caveat) — cheap to settle, changes which standard a
   German module cites.

**Recorded to memory** (durable, outside this doc): the one-platform trade-gated decision, the
multi-trade contract/billing requirement, and the PE consolidator buyer profile.
