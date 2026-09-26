# SAIRNsenior external competitive-gap audit: competitors, EVV regulation, enforcement, aggregator onboarding, practitioner voice (2026-09-26)

**Research pass, 2026-09-26. Cloud-research lane: docs only.** No code, claims or
tier registers were touched. This is a new file under `docs/cloud-research/`,
committed to the same branch as the SAIRNlaw, SAIRNvet, SAIRNcode and SAIRNbiz
passes, and it uses the same wide-lens scope as they do.

This pass covers five lenses:
- **Competitive/market:** Alora, WellSky Personal Care, AlayaCare, MatrixCare,
  Homecare Homebase.
- **Regulatory/compliance:** EVV by state, the Cures Act, recent CMS guidance.
- **Accuracy/liability:** documented EVV failures and penalties.
- **Adjacent-industry:** how vendors handle trading-partner agreements and
  getting onto state aggregators.
- **Practitioner voice.**

**Cody holds an active claim on the adjacent file**
`docs/superpowers/specs/2026-08-26-competitive-gap-audit-roofing-dental-senior.md`,
to correct that audit. This document does not touch it. Its findings are an
input for that correction, not an edit to it.

---

## 0. Read this before quoting anything

### 0.1 Evidence grade: every external claim is SNIPPET, and none is OPENED

Five research passes ran in parallel, one per lens. Together they used **190
WebSearch calls** out of a 200 budget, 38 per lens.

**Of 39 WebFetch attempts, 38 were refused by this session's egress proxy with
`EGRESS_BLOCKED`, and the 39th (`reddit.com`) returned "unable to fetch".**
`EGRESS_BLOCKED` means the request never left the container. It is not an HTTP
code from the site. The refused domains included:
- vendor sites: `alorahealth.com`, `wellsky.com`, `hchb.com`, `hhaexchange.com`,
  `knowledge.sandata.com`
- CMS: `medicaid.gov`
- `oig.hhs.gov`, `justice.gov`, `federalregister.gov`, `ecfr.gov`
- state sites: `ohioauditor.gov`, `hcpf.colorado.gov`, `dhs.wisconsin.gov`,
  `tmhp.com`, `ctdssmap.com`, `hfs.illinois.gov`
- trade press: `mcknightshomecare.com`
- the review sites: Capterra, G2, Software Advice, TrustRadius, GetApp
- `reddit.com`

The WebSearch tool also refuses `reddit.com` as a domain filter (400). None of
these blocks was routed around.

So **every external claim below is graded [SNIPPET]**: the search tool's
model-written summary of the result pages, not the page. This is one grade
lower than Fourth's SAIRNvet pass, which opened eight vendor pages directly.
Words in quotation marks are the snippet's wording. They are **not verified as
the page's wording**. Nothing here is fit to quote to a customer or regulator
until the source page is opened and read. §9 lists the specific figures to
re-read first.

Source types are marked where it matters:
- **STAT** statute
- **REG** regulation
- **SRG** CMS sub-regulatory guidance
- **STATE** state agency
- **VEND** vendor or vendor blog
- **LAW** law firm or consultancy
- **PRESS** trade or general press

### 0.2 Corrections to the brief's premises

1. **"21st Century Cures Act status" dates.** The HHCS (home health care
   services) EVV deadline in statute is **January 1, 2023**, not 2024. January 1,
   2024 is that date plus the one-year good-faith-effort (GFE) exemption. The PCS
   (personal care services) deadline was set as January 1, 2019 and moved to
   January 1, 2020 by later statute; January 1, 2021 is the GFE date. Several
   vendor blogs mix these up. One of them (ShiftCare) attributes EVV to a
   "PROMIIS Act", which is wrong; the source is Cures Act §12006. The wrong date
   pairs would propagate into any compliance copy that repeats them.
   *(Statutory dates: from 42 U.S.C. §1396b(l), as recorded in this repo's
   `api/_lib/sen-evv-readiness.js` header and snippet-corroborated against
   `medicaid.gov/federal-policy-guidance/downloads/cib051618.pdf`.)*
2. **"CareTime / HHAeXchange's own agency software."** The snippets tie
   **CareTime to Alora**, not to HHAeXchange: "CareTime now selling under Alora
   name", "no forced migration" (`caretime.us/alora-health` [SNIPPET]). HHAeXchange
   does sell its own agency software, but CareTime is not it.
3. **"Trading-partner agreement per aggregator."** This is the first of the
   three blockers named in `api/_lib/sen-evv-readiness.js`, and it is **the
   wrong instrument for the aggregator layer.** At the aggregator, the gate is
   **agency-sponsored vendor certification**. The formal trading-partner
   agreement belongs to the **837 claims** layer, which is a separate track.
   See §5. This is a finding about SAIRNsenior's own blocker list, not only about
   the market.

---

## 1. Internal grounding, measured first

This was measured from `sairnsenior.html` at `origin/main` `e560d97d`
(367,286 bytes) and from `api/`, before any external search. That order means
nothing below re-argues something the product already has. Counts are grep
floors, not ceilings.

The 2026-09-17 status pass
(`docs/2026-09-17-senior-mechanical-competitive-gap-rederived.md`) found:
- 18 panels, all wired;
- the 08-26 audit's rows A3, A5–A7 and B1–B4 closed;
- B5 half-built, with the half that computes a profit figure refused.

Re-checked here: **18 panels** (`dashboard`, `ai`, `clients`, `scheduling`,
`billing`, `caregivers`, `training`, `branches`, `contracts`,
`authorizations`, `payrates`, `franchise`, `hiring`, `compliance`,
`referrals`, `reports`, `security`, `settings`).

What bears on this pass:

| Area | At `origin/main` | Evidence |
|---|---|---|
| EVV readiness | **Built.** It checks each visit against the six items in 42 U.S.C. §1396b(l)(5)(A). A state with no verified rule set is reported as `state_rules: 'not_verified'`, never as compliant | `api/_lib/sen-evv-readiness.js` |
| EVV transmission | **None.** `transmit` × 0. Four aggregators are named (Sandata, HHAeXchange, Tellus ×3 each; CareBridge), and data goes to none of them | grep |
| Offline capture | **Built.** The clock event is queued with the time it was captured and replayed unchanged. The queue is FIFO and stops at the first failure. Visits are flagged `evv_offline` | `sairnsenior.html` ~L2884–2960; `api/_lib/sairnsenior-offline-evv.test.js` |
| Telephony / IVR | **None.** `telephony` × 2, both in a comment; `IVR` × 0 | grep |
| Location | Point-in-time `navigator.geolocation` at clock-in and clock-out. If permission is refused, the fields stay null and the refusal is disclosed. **No geofence** (`geofenc` × 0) and **no distance-from-client-address check** found | grep |
| **Visit maintenance (office-side correction of clock times)** | **Not found.** `clock_in_at` and `clock_out_at` are set in exactly two places (~L2994, ~L3001), both at the caregiver's own clock action. `reason code` × 0, `edit reason` × 0, `visit maintenance` × 0 | grep |
| **Device vs server time** | **The device clock is trusted.** Both timestamps are `new Date().toISOString()` on the device. No server-side comparison against receipt time was found in `api/` (`clock_in_at` appears in `api/` only in tests and the readiness/payroll engines) | `git grep clock_in_at origin/main -- api/` |
| 837 / clearinghouse | **None.** `837` × 0, `clearinghouse` × 0 | grep |
| Live-in handling | Named once, as **excluded from payroll computation** ("live-in arrangements … are not computed"). There is no EVV live-in exemption path | grep |
| 80/20, CMS-2442-F, HCBS | `80/20` × 0, `2442` × 0, `HCBS` × 0; `waiver` × 9 | grep |
| Family portal | **Built.** Scoped links that can be revoked (`sen_portal_links`) | 08-26 audit §5, reconfirmed by `portal` × 56 |

**Two of these rows are new findings, and §4 is why they matter.** They are
**no visit-maintenance path** and a **trusted device clock**. Neither was in the
08-26 or 09-17 passes.

The first is **not a defect today**, because there is nothing to transmit to.
It becomes the first thing an aggregator requires on the day transmission
exists: every aggregator in §5 has an "exceptions must be resolved before the
claim pays" workflow. It is also a regulated metric in at least one state
(Pennsylvania, §3.3).

The second is a design choice that preserves offline accuracy, and the code
comment explains why. What is missing is a **signal** when device time and
server receipt time disagree by more than the offline-queue explains.

---

## 2. Competitive / market lens

Every row is [SNIPPET]. Vendor figures are the vendor's own claims.

### 2.1 The five named competitors

| | **Alora** | **WellSky Personal Care** | **AlayaCare** | **MatrixCare** | **HCHB** |
|---|---|---|---|---|---|
| Segment | Home health, personal care, hospice | Non-medical personal care / private duty (a separate WellSky product line from its home health) | Personal care, private duty, HCBS, VA; mid-market to enterprise; US/CA/AU | SNF, senior living, home health, hospice, **private duty** | Medicare home health and hospice. **Has now extended into personal care** ("HCHB Personal Care … an extension of the Homecare Homebase platform"), launch date not established |
| Ownership, 2024–26 | **Acquired by LivTech (PSG-backed), 2026-04-09**, price undisclosed. Alora itself absorbed CareTime | TPG + Leonard Green since 2020; **no sale found**. Still acquiring (Corridor, Aug 2025; Bonafide, Oct 2024) | Independent, venture-backed. **$50M CIBC growth facility, 2026-02-19**, partly for M&A. Acquired Nightingale (AU, NDIS); the date conflicts (2025-10-28 vs 2025-11-20) | **Sold by ResMed to Frazier Healthcare Partners for $490M cash.** Agreed 2026-07-07, closed about 2026-09-01 (Jonathan Lujan CEO). ResMed-stated FY26: about $220M revenue, about $55M operating profit | Hearst Health; no change found |
| Published price | **The only one with a pricing page:** $295–$800/mo (small), $800–$2,000 (medium), $2,000–$8,000 (large), "unlimited users or unlimited patients". **Conflicts** with a third-party "$150 per user/month" | Not published. Third-party figures conflict: "$100 per active client, monthly" vs "$12 per user, per month" | Not published. Third-party: "starts at $1000/month" + "$5,000" setup, unsourced | Not found | Not published |
| EVV aggregators claimed | "approved alternate EVV vendor in many states"; Sandata, HHAeXchange, Netsmart, CareBridge; **GPS and telephony** | HHAeXchange, Sandata, Netsmart, AuthentiCare; "compatible with 85% of the state EVV systems" (flyer dated 10.27.23); **telephony via client's home phone** | GPS, "an offline mode". HHAeXchange/Sandata integration is evidenced **only by a job posting** | "mobile and telephony EVV"; Sandata, HHAeXchange, Tellus; "native mobile offline apps" | EVVLink (home health). A "40+ states … GPS and telephony … 7+ languages … offline" list for HCHB Personal Care is **unattributed and did not repeat on a narrower search. Treat as unverified** |
| Claims to be a *state-selected* aggregator? | No | No | No | No (positions as alternate vendor) | No |
| Clearinghouse | Inovalon (Ability), Availity. Stated for **home health**; personal care not confirmed | Change Healthcare (current status unverified) | "clearing house integration", partner unnamed | Not named | Not established |
| Family portal | Not established | **Family Room**: calendar, shift notes, "pay or split a portion of the bill" | **Family Portal**: schedules, care updates, forms, requests, payments | "client and family portal" | Not established |
| 2025–26 product direction | AI documentation, phase 1 announced 2025-10-15; phases 2/3 due spring and fall 2026, shipping not confirmed | **WellSky Summarize for Personal Care** (2026-02-05); **Ambient Documentation for Personal Care** with AutoMynd (2026-04-30, "first … purpose-built for personal care") | **Vacant Visit Scheduling Agent** (2026-03-03, "operates 24/7", "up to 80%" less manual work); **AlayaFlow** agentic roadmap (2026-09-16) | nVoq voice/AI documentation (2026-03) | HCHB Intelligence Suite (2025-09-30); **Curate: Scribe** with StenoHealth (2026-03-12) |
| Scale claim | "Serving agencies across the United States" | 2020 deal: "more than 4,000 personal care agencies … 600,000 caregivers"; 8 of 10 largest franchise networks (known from 08-26) | Not found | "more than 15,000 providers" (all segments) | **These conflict:** 44% (July 2025), about 45% (HHCN, June 2025), 43.8% of HHAs / 38.7% of hospices (2024 YE), "more than one-third" |

Sources:
- **Alora:** `alorahealth.com/personal-care-software/`, `/pricing/`, `/evv-software/`,
  `/evv/`, `/home-health-billing-services/`;
  [GlobeNewswire 2026-04-09](https://www.globenewswire.com/news-release/2026/04/09/3271014/0/en/livtech-acquires-alora-healthcare-systems-further-expanding-leadership-in-home-based-care-technology.html);
  [HIT Consultant](https://hitconsultant.net/2026/04/09/livtech-acquires-alora-healthcare-systems/);
  [Alora AI launch](https://www.alorahealth.com/alora-healthcare-systems-launches-first-wave-of-ai-solutions-for-home-based-care/).
- **WellSky:** [EVV Ready flyer](https://info.wellsky.com/rs/596-FKF-634/images/WS-PC020-WSPC_EVV_Ready.pdf);
  [Hospice News 2020](https://hospicenews.com/2020/07/20/tpg-capital-leonard-green-partners-to-share-ownership-of-wellsky/);
  BusinessWire 2026-02-05 and 2026-04-30;
  [HIT Consultant 2026-04-30](https://hitconsultant.net/2026/04/30/wellsky-automynd-ambient-ai-personal-care/).
- **AlayaCare:** [BusinessWire 2026-02-19](https://www.businesswire.com/news/home/20260219050585/en/);
  [family portal](https://alayacare.com/family-portal/);
  [EVV FAQ](https://alayacare.com/faq/evv-questions-answers/);
  [GlobeNewswire 2026-03-03](https://www.globenewswire.com/news-release/2026/03/03/3248776/0/en/);
  [2026-09-16](https://www.globenewswire.com/news-release/2026/09/16/3363421/0/en/).
- **MatrixCare:** [ResMed release](https://investor.resmed.com/news-events/press-releases/detail/426/);
  [McKnight's Senior Living, close](https://www.mcknightsseniorliving.com/news/frazier-closes-490m-matrixcare-acquisition-names-lujan-ceo/);
  [private duty page](https://www.matrixcare.com/private-duty-software/);
  [nVoq](https://www.prnewswire.com/news-releases/nvoq-expands-ai-powered-clinical-documentation-capabilities-to-matrixcare-users-302722484.html).
- **HCHB:** [HCHB Personal Care](https://hchb.com/hchb-personal-care/);
  [2024 wrap](https://hchb.com/homecare-homebase-wraps-2024-with-growth-product-innovation-and-industry-leadership/);
  [company profile](https://hchb.com/hchb-company-profile/);
  [Curate: Scribe](https://www.prnewswire.com/news-releases/homecare-homebase-announces-curate-scribe-302711581.html).

All accessed 2026-09-26, [SNIPPET].

### 2.2 Others, briefly

- **AxisCare** (personal care): 2026-06-02 strategic investment from **LLR
  Partners** ([BusinessWire](https://www.businesswire.com/news/home/20260602076414/en/)).
  It publishes per-state EVV pages naming aggregators; for example NY lists
  HHAeXchange, CareBridge and eMedNY
  ([axiscare.com/newyork-medicaid-evv/](https://axiscare.com/newyork-medicaid-evv/)).
  Vendor claims: 2026 Best in KLAS and G2 number one. [SNIPPET]
- **HHAeXchange** is **both a state aggregator and a competing
  agency-management product**. Its 2026 survey of 465 HCBS agencies was
  published 2026-08-04
  ([HIT Consultant](https://hitconsultant.net/2026/08/04/hhaexchange-releases-2026-homecare-insights-provider-survey/)).
  [SNIPPET]
- **Netsmart** is the *state-selected* aggregator in Georgia ("at no cost",
  [medicaid.georgia.gov](https://medicaid.georgia.gov/programs/all-programs/georgia-electronic-visit-verification-evv-0/evv-third-party-information)),
  and per snippets in KY, NE and FL. [SNIPPET]
- **KanTime** is the one vendor found **disclosing a state it is not integrated
  with**: West Virginia (HHAeXchange), "KanTime EVV is not integrated at this
  time" (`kantime.com/electronic-visit-verification/`, exact page uncertain).
  This matches the 08-26 finding. [SNIPPET]

### 2.3 What the competitive lens changes

1. **2026 is a consolidation year, and three of the five named competitors
   changed hands or took capital within it:**
   - Alora went to LivTech (April);
   - MatrixCare went to Frazier (closed about September 1);
   - AlayaCare took a $50M facility for M&A (February);
   - AxisCare took LLR money (June), which makes four.

   Ownership changes are the usual trigger for renewal-price and support
   changes. §6 found **no practitioner evidence yet** of price rises after an
   acquisition, so this is an **inference, not a finding**.
2. **The feature race in 2025–26 is AI documentation and AI scheduling, not
   EVV.** Every named competitor announced an AI documentation or scheduling
   product in the window. None was found leading with franchise royalty,
   denials/appeals or authorisation unit burn-down. **That is absence of
   evidence on marketing pages, not proof SAIRNsenior is unique on those rows.**
3. **Telephony EVV is openly claimed by Alora, WellSky and MatrixCare.**
   SAIRNsenior's A2 telephony half stays a visible gap. The 09-17 pass already
   carries it.
4. **HCHB entering personal care** puts the Medicare home-health EHR with
   roughly 40% share into SAIRNsenior's segment. It is worth a dated re-check
   once HCHB Personal Care's launch date and feature list can be read from the
   page itself.

---

## 3. Regulatory / compliance lens

### 3.1 Federal: statute, guidance, and what is moving

- **EVV statute** (STAT). This is Cures Act §12006, 42 U.S.C. §1396b(l). The six
  items are already primary-verified in `api/_lib/sen-evv-readiness.js` and are
  not re-litigated here. The FMAP reduction for HHCS as snippets give it:
  "0.25 percentage points for calendar quarters in 2024, 0.5 … in 2025, …
  0.75 … in 2026, and … 1 percentage point for calendar quarters in 2027 and
  each year thereafter". **This is not checked against the statute text.**
  [SNIPPET, search summary citing the medicaid.gov HHCS compliance-status page]
- **CMS publishes per-state EVV compliance tables** (SRG), one for PCS and one
  for HHCS. The HHCS table is "as of January 1, 2024" with fully / partially /
  not compliant, plus per-state determination letters (for example Georgia,
  dated 02/27/2024). **Which states are currently partial or non-compliant was
  NOT established; the pages were blocked.**
  [medicaid.gov … evv-compliance-status-for-home-health-care-services-state-or-territory](https://www.medicaid.gov/medicaid/home-community-based-services/home-community-based-services-guidance-additional-resources/electronic-visit-verification/evv-compliance-status-for-home-health-care-services-state-or-territory)
  [BLOCKED, SNIPPET]
- **No CMS EVV guidance after 2019 was found.** The one targeted search returned
  only the 2019-08-08 CIB and the 2019-10-22 EVV Certification v1.0. The
  **December 2022 GFE guidance and the May 2022 1915(c) note, both already
  listed as unread in the readiness module header, were not surfaced either.**
  So that module's residual-gap disclosure stands unchanged.
- **CMS-2442-F** (REG), the Ensuring Access to Medicaid Services final rule,
  published 2024-05-10
  ([Federal Register](https://www.federalregister.gov/documents/2024/05/10/2024-08363/medicaid-program-ensuring-access-to-medicaid-services)):
  - **80/20 pass-through.** 80% of Medicaid payments for homemaker, home
    health aide and personal care must go to direct-care worker compensation,
    effective **2030**. **Two conflicts:**
    - *reporting start*: "by 2028" vs "Reporting begins in 2026" (LAW snippets);
    - *scope*: Rhode Island EOHHS adds *habilitation* to the list; law-firm
      summaries do not.

    A state readiness report is due "Beginning July 9, 2027"
    ([Sellers Dorsey](https://www.sellersdorsey.com/insights/cms-special-coverage/sellers-dorsey-summary-ensuring-access-to-medicaid-services-rules-cms-2442-f/)).
  - **Rate disclosure, 42 CFR 447.203(b)(2):** average hourly FFS rates for
    personal care, home health aide, homemaker and habilitation, published from
    **July 1, 2026**
    ([Myers and Stauffer](https://myersandstauffer.com/insights/client-alerts/payment-rate-transparency-standards/)).
    A Rhode Island file titled "HCBS Payment Rate Disclosure" sits under a
    2026-07 path, which is evidence it went live.
  - **HCBS Quality Measure Set:** reporting "every other year, beginning in
    2028". A Federal Register notice for the "2028 Medicaid Home and
    Community-Based Services Quality Measure Set" is dated **2026-04-28**
    ([doc 2026-08190](https://www.federalregister.gov/documents/2026/04/28/2026-08190/medicaid-program-2028-medicaid-home-and-community-based-services-quality-measure-set),
    title only).
  - **Possible rescission.** McKnight's Home Care, dated 2026-07-08 in the
    summary, reports CMS developing a proposed rule "including rescinding or
    revising provisions finalized in the 2024 final rules", "now residing at the
    Office of Management and Budget"
    ([mcknightshomecare.com](https://www.mcknightshomecare.com/news/cms-soon-to-drop-proposed-rule-that-may-involve-rescinding-80-20-provision/),
    BLOCKED). **No published proposed rule was found as of 2026-09-26.**
- **OBBBA / H.R. 1 (2025 reconciliation law)** (STAT). It creates a new
  stand-alone 1915(c) waiver option for people **below** institutional level of
  care, "beginning July 1, 2028", with $50M FY2026 and $100M FY2027
  ([Rockefeller Institute](https://www.rockinst.org/blog/initial-considerations-for-adopting-the-new-1915c-waiver-design-as-enacted-in-the-one-big-beautiful-bill-act-hr1/);
  [NHeLP](https://healthlaw.org/resource/new-1915c-waiver-opportunity-under-obbba/)).
  **No EVV provision found in it.**
- **Federal EVV legislation 2025–26: none found.** That is not proof none
  exists.
- **Adjacent, not EVV.** CMS announced a **nationwide 6-month enrollment
  moratorium on new HHAs and hospices on 2026-05-13**, extendable
  ([CMS press release](https://www.cms.gov/newsroom/press-releases/cms-announces-aggressive-nationwide-crackdown-fraud-six-month-hospice-home-health-agency-enrollment);
  [QSO-26-11](https://www.cms.gov/files/document/qso-26-11-hha-hospice-original-release-2026-05-20.pdf)).
  **Scope conflict:** law firms say Medicare only, with states "encouraged" to
  act in parallel
  ([Mintz](https://www.mintz.com/insights-center/viewpoints/2146/2026-05-18-cms-imposes-nationwide-enrollment-freeze-home-health));
  the Federal Register notice title names "Medicare, Medicaid, and Children's
  Health Insurance Programs" (doc 2026-09717). **This bears on SAIRNsenior's
  addressable market for new Medicare-certified agencies, not on non-medical
  personal care.**

### 3.2 State EVV table, 2026

"Open" means the provider picks the capture tool and sends data to a state
aggregator. "State + alt" means a free state tool, with third-party systems
allowed if they integrate. Every row is [SNIPPET]. **STATE** marks rows whose
snippet came from a state host.

This deliberately repeats nothing already verified in the 2026-08-27
groundwork: WA's claim-embedded model, IN = Sandata, LA LaSRS open, and the
MI/MN/TX/CO/CA/WI/LA open-model confirmations. Where a row below refines one of
those, it says so.

| State | Model | Aggregator | Enforcement on claims | Notable | Source |
|---|---|---|---|---|---|
| **AZ** | **Moved from a free state vendor to provider choice + a state aggregator on 2025-10-01** (Sandata dropped). Agencies staying on Sandata "will need to contract directly … and will be responsible for the cost" | AHCCCS's own aggregator | **Hard edits from DOS 2023-01-01** (moved from 2022-11-01 under a CMS extension) | Every vendor must pass AHCCCS testing | [AHCCCS aggregator announcement](https://www.azahcccs.gov/AHCCCS/Downloads/EVV/AHCCCS_GeneralEVV_AggregatorImplementationAnnouncement.pdf) (STATE) |
| **OH** | State vendor + alternate | Sandata | Claims pend 3 business days, then "finalize and deny" | **SB 315, signed 2026-07-09, effective about October 2026, rewrites EVV rules** (snippets: "can include GPS tracking"). **Alternate-vendor applications "temporarily paused"**. Ohio lists "75+ approved alternate EVV vendors" | [Ohio Medicaid EVV](https://medicaid.ohio.gov/resources-for-providers/special-programs-and-initiatives/electronic-visit-verification) (STATE); [WOSU](https://www.wosu.org/2026-07-09/dewine-signs-bill-requiring-ohio-medicaid-home-health-workers-electronically-check-in) (PRESS); [Shumaker](https://www.shumaker.com/insight/client-alert-ohio-enacts-sweeping-medicaid-fraud-reforms-through-sb-315/) (LAW) |
| **MA** | State vendor + alternate | Sandata | **FFS hard edits "September 2026"** for HH, GAFC, ABI and MFP waivers; a vendor says "no earlier than July 2026" | Denial without a matching Verified visit | [mass.gov hard-edits cheat sheet](https://www.mass.gov/doc/ma-evv-fee-for-service-hh-gafc-and-abimfp-waivers-programs-hard-edits-cheat-sheet-0/download) (STATE) |
| **MO** | Open vendor | Sandata EAS | Soft launch 2026-01-07 (code N363); **hard launch Phase I 2026-04-01** for provider types 26/28 | — | [mydss.mo.gov](https://mydss.mo.gov/mhd/hot-tips/evv-claims-validation-non-compliant-claims-will-deny-beginning-april-1-2026) (STATE); [mmac.mo.gov](https://mmac.mo.gov/evv-hard-launch-phase-i-on-april-1-2026/) (STATE) |
| **NC** | **Three aggregators, split by payer** | Sandata (Medicaid Direct/FFS); HHAeXchange (Standard and Tailored Plans); CareBridge (Healthy Blue) | **Managed-care HHCS hard launch DOS ≥ 2025-10-01**: claims "without the required EVV data will be denied" | "15% manual-entry ceiling" is vendor-only | [NC Medicaid blog 2025-09-09](https://medicaid.ncdhhs.gov/blog/2025/09/09/managed-care-electronic-visit-verification-home-health-implementation-hard-launch-effective-oct-1) (STATE) |
| **MI** | Open capture, **but all data through HHAeXchange** (refines the known "open") | HHAeXchange (5-year MDHHS contract, March 2023) | Managed-care HHCS "hard cutover" 2026-01-01; compliance policy 2026-04-01 (vendor/MCO snippets) | — | [michigan.gov FAQ](https://www.michigan.gov/mdhhs/assistance-programs/medicaid/portalhome/electronic-visit-verification/electronic-visit-verification-who/caregivers-and-providers-faqs) (STATE); [Meridian MI](https://www.mimeridian.com/providers/bulletins/112025-medicaid-evv-updates.html) (MCO) |
| **IL** | State (HHAeXchange, free) + third-party EDI | HHAeXchange | **Threshold-and-penalty regime, not an automatic denial**: from 2026-04-01, 75% compliance checked quarterly, then training, a corrective action plan, and referral to the HFS Inspector General | **Requires full caregiver SSN** | [HFS FAQ](https://hfs.illinois.gov/medicalproviders/electronicvisitverification/ievvfrequentlyaskedquestions.html) (STATE); [notice PRN260210a](https://hfs.illinois.gov/medicalproviders/notices/notice.prn260210a.html) (STATE) |
| **PA** | "Open Choice Model" | Sandata | PCS "subject to denial or recoupment" if visit maintenance is incomplete | **Manual-edit rate is an enforcement metric**: see §3.3 | [pa.gov alternate EVV](https://www.pa.gov/agencies/dhs/resources/for-providers/evv/alternate-evv) (STATE) |
| **TX** | Open (known) | State EVV Aggregator; claims via TMHP | HHCS claims matching "resumes Jan. 1, 2024 – Claims Without Matching EVV Visits Will Deny". **Conflict:** an MCO snippet cites a bypass from 2024-01-01 to 2024-03-31 | — | [TMHP 2023-12-11](https://www.tmhp.com/news/2023-12-11-evv-claims-matching-resumes-jan-1-2024-claims-without-matching-evv-visits-will-deny) (STATE) |
| **WI** | Open (known) | Sandata | Deny without a matching record from DOS 2023-05-01 after a 10-day hold (probably PCS); 2024-10-01 consequences date (probably HHCS) | **Conflict:** one snippet says the DHS-provided Sandata system "must be used" | [WI DHS forum deck](https://www.dhs.wisconsin.gov/evv/hhcsand99509evvforumjune2024.pdf) (STATE) |
| **TN** | MCO-run | Per MCO (vendor not established) | MCO denials from 2024-01-01 for intermittent HH without EVV | — | [TennCare memo](https://www.tn.gov/content/dam/tn/tenncare/documents/FinalMemoToHHAProviders5-25-2023.pdf) (STATE) |
| **FL** | **Split**: FFS uses the state vendor; SMMC plans use their own | HHAeXchange (AHCA FFS from 2024-10-01) | SMMC plans deny PCS/HH not submitted through plan EVV vendors (DOS from 2021-06-21) | "a minimum 85% EVV submission rate" | [AHCA HH EVV](https://ahca.myflorida.com/medicaid/medicaid-home-health-hh-services/home-health-services-electronic-visit-verification-evv.html) (STATE) |
| **CA** | State + alt (CalEVV free; AltEVV allowed) | Sandata runs the CalEVV Aggregator | "delayed or denied"; no hard-edit date found | — | [DHCS CalEVV](https://www.dhcs.ca.gov/providers-partners/california-electronic-visit-verification/) (STATE) |
| **NY** | Provider Choice; data to the NYS Aggregator via eMedNY | NYS DOH; CareBridge and HHAeXchange as secondary aggregators (vendor text) | One snippet: "no automatic claim denial or pending if the claim does not match"; source document and date not visible | DOH FAQ dated 2026-06-17 exists | [health.ny.gov EVV FAQ](https://www.health.ny.gov/health_care/medicaid/redesign/evv/faqs.htm) (STATE) |
| **NJ** | Open capture; aggregator mandatory | HHAeXchange | Denial date unclear (vendor only) | — | [NJ DMAHS newsletter](https://www.nj.gov/humanservices/dmahs/documents/providers-stakeholders/EVV_Provider_Newsletter_Vol%2032_No_20.pdf) (STATE) |
| **VA** | Provider choice; MCO-specific aggregators; **FFS EVV data rides in the 837** (same shape as WA) | Per MCO; DMAS MES | — | Live-in exemption by modifier **"UB"**. **Conflict:** another bulletin says from **2026-10-01** "all consumer-direction personal care attendants regardless of live in status" must use EVV | [DMAS live-in bulletin](https://vamedicaid.dmas.virginia.gov/bulletin/electronic-visit-verification-live-caregiver-exemption-and-consumer-directed-personal-care) (STATE) |
| **GA** | Open vendor, state aggregator | Netsmart Mobile Caregiver+ (formerly Tellus) | PCS "fully implemented"; HHCS phase 2 status not confirmed | — | [medicaid.georgia.gov](https://medicaid.georgia.gov/programs/all-programs/georgia-electronic-visit-verification-evv-0) (STATE) |
| **MD** | State system (LTSSMaryland / ISAS) | State | Not established | **Conflict:** "closed model" vs "any EVV vendor … must integrate with ISAS". The 08-27 groundwork already carries MD as NOT VERIFIED; this does not close it | [MDH LTSSMaryland EVV](https://health.maryland.gov/mmcp/provider/Pages/ltssmaryland_EVV.aspx) (STATE) |

**Virginia is a second claim-embedded state.** The 08-27 groundwork's §3 said
the correct abstraction is "a visit becomes a submitted artifact, which may be
an API call, a file drop, *or a claim line*", on the strength of Washington
alone. If the snippet holds, Virginia FFS is a second instance. That makes the
claim-line branch of the abstraction more than a single-state accommodation,
and it **couples EVV to the 837 gap (A4)**: in those states there is no EVV
submission without a claim.

### 3.3 Enforcement has moved from "was EVV used" to "how clean was it"

Three states now measure EVV **quality**, not just presence:

- **Pennsylvania, MA Bulletin 05-25-03, issued 2025-08-29:**
  - from 2025-01-01, at least **85% of visits verified with no manual edits**;
  - from January 2026, providers over **15% manual edits in a quarter** get
    alerts;
  - **two consecutive quarters** over the limit bring a formal noncompliance
    notice and a required **corrective action plan**;
  - continued noncompliance can mean involuntary termination from the
    participant-directed model.

  ([pa.gov MAB 2025-08-29](https://www.pa.gov/content/dam/copapwp-pagov/en/dhs/documents/docs/publications/documents/forms-and-pubs-omap/mab2025082901.pdf);
  [ODP 2025-09-05](https://home.myodp.org/2025/09/05/medical-assistance-ma-bulletin-05-25-03-electronic-visit-verification-evv-manual-edits-noncompliance-in-the-fee-for-service-delivery-and-managed-care-delivery-systems/),
  [SNIPPET])
- **Illinois:** a 75% quarterly compliance threshold from 2026-04-01, with an
  escalation ladder that ends at the Inspector General (above).
- **Florida:** "a minimum 85% EVV submission rate" (above).

**This is the finding with the most direct product consequence in this pass.**
SAIRNsenior's readiness engine already reports per visit what is missing. The
next unit of value is **per agency, per quarter, against the state's
threshold**:
- the share of visits verified without edits;
- the manual-edit rate;
- the submission rate.

That is a report over data the readiness engine already builds. **It does not
need transmission**, so it is the rare EVV feature not gated by blocker (a).
It does need the visit-maintenance path §1 found missing, because an edit rate
cannot be computed when edits leave no record.

---

## 4. Accuracy / liability lens

Every row is [SNIPPET]. The status column distinguishes **allegation**
(indictment or charge) from **settlement** (no admission) and **conviction**.

### 4.1 Cases where EVV was the evidence or the instrument

| Date | Actor | What | EVV mechanism | Status | Source |
|---|---|---|---|---|---|
| 2025 (**date conflicts**: 2025-10-16 vs June 2025 National Takedown) | Favorite Home Care LLC and four owners/managers, E.D. Pa. | Billed Medicaid and an MCO for home care not rendered | "Each defendant personally completed electronic visit verification calls … despite not being present with the client". **The EVV record was the false statement** | **Indictment**: 1 conspiracy + 20 fraud counts | [USAO-EDPA](https://www.justice.gov/usao-edpa/pr/bucks-county-home-care-company-and-its-owners-and-managers-charged-alleged-health-care); [HHS-OIG](https://oig.hhs.gov/fraud/enforcement/bucks-county-home-care-company-and-its-owners-and-managers-charged-in-alleged-health-care-fraud-scheme) |
| 2026-08-04 | Benevolent Home Health Care LLC and others; DOJ Fraud Division, EDPA, PA AG | Services billed while the caregiver or client was jailed, hospitalized, at another job or abroad | "hundreds of false and fraudulent clock-ins and clock-outs" | **Charges**. **Counts conflict:** 19 defendants / >$4M (DOJ) vs $5.76M (parallel announcement) vs 18 people (Inquirer) | [DOJ OPA](https://www.justice.gov/opa/pr/fraud-division-announces-charges-against-19-defendants-medicaid-home-health-aid-schemes); [DEA](https://www.dea.gov/press-releases/2026/08/04/dozens-charged-health-care-fraud-federal-and-state-cases-involving-576) |
| 2026-08 (same sweep) | Pizzo/Taormina; Coccia, PA | Care logged while the caregiver was in Bucks County jail, working construction, or driving for rideshare | Inquirer: "The caregiver or the client behind closed doors simply can tap a button on their smartphone app or call in, and that record doesn't actually establish that the person was actually there." | **Charges**, at least $160,000 | [Inquirer 2026-08-08](https://www.inquirer.com/health/home-care-fraud-electronic-health-human-services-medicare-medicaid-20260808.html) |
| 2025-11 | Arkansas AG MFCU v. Jacqueline Small (caregiver) | PCS not provided, $11,576.32 | "Electronic visit verification records indicate that Small was not at or near beneficiary residences". **EVV location was the prosecution's evidence** | **Arrest and charge**, Class B felony | [HHS-OIG enforcement](https://oig.hhs.gov/fraud/enforcement/attorney-general-griffin-announces-2-convictions-and-an-arrest-made-by-his-medicaid-fraud-control-unit/) |

**Not EVV cases, listed so they are not over-counted:**
- Blessings 4 Ever: $1M FCA settlement, "falsified documentation", EVV not
  mentioned.
- Bronx "War Room": $12M, alleged **GPS-spoofing app**, but this is
  **non-emergency medical transportation, not home care**.
- HHS-OIG MFCU FY2025 report: PCS attendants had the most convictions (326) of
  any provider type, with no EVV tie in the snippet.

**No DOJ False Claims Act settlement with EVV data as the stated mechanism was
found, and no GPS-spoofing prosecution in home care.**

### 4.2 Audits: claims that bypassed EVV

| Date | Report | Finding | Amount | Source |
|---|---|---|---|---|
| 2026-07-17 | HHS-OIG **A-07-24-03260**, Colorado | The state did not verify all PCS visits were in EVV; no edits matching paid services to approved services; some attendants averaged more than 24 h/day. **Single-source, lower confidence:** of 160 sampled claims, 17 were never in EVV, 18 lacked location, 18 had unreviewed GPS exceptions. HCPF disputes "many of the key conclusions" | **$8.0M refund recommended; $45.7M set aside** | [HHS-OIG](https://oig.hhs.gov/reports/all/2026/colorado-could-improve-its-electronic-visit-verification-system-and-claimed-federal-medicaid-reimbursement-for-millions-of-dollars-in-personal-care-services-that-did-not-comply-with-federal-and-state-requirements/); [HCPF response](https://hcpf.colorado.gov/press-release/response-to-oig-audit-of-colorados-electronic-visit-verification-system) |
| 2024-08-20 | HHS-OIG **A-07-23-03255**, Kansas | Not all in-home PCS visits required through EVV; no procedure to stop claims outside EVV; **no edit checking recorded tasks against the plan of care** | not in snippet | [HHS-OIG](https://oig.hhs.gov/reports/all/2024/kansass-implemented-electronic-visit-verification-system-could-be-improved) |
| 2024-11-14 | NY State Comptroller **2022-S-31** | Only **56% of PCS** and **11% of home health** services had a matching EVV record; $11.6M paid for visits under 8 minutes; $9.7M paid while the patient was hospitalized | **$14.5B** PCS unmatched (wording conflicts: "44% of more than $14.5B" in one summary; the release title reads as $14.5B unmatched) | [OSC NY](https://osc.ny.gov/state-agencies/audits/2024/11/13/medicaid-program-provider-compliance-electronic-visit-verification-program) |
| 2024-11 | Ohio Auditor of State, report No. 117 (CY2022 data) | **56%** of tested claims had no matching EVV visit; edits flagged but **did not deny**; 37 of 100 sampled providers submitted no EVV data | about $1.1B of about $2B unmatched | [ohioauditor.gov report 117](https://ohioauditor.gov/Auditsearch/Reports/2024/117_Electronic_Visit_Verification_Report_FINAL.pdf) (BLOCKED) |
| 2024-09 | HHS-OIG **A-06-22-02000**, New Mexico | **Not an EVV finding:** attendants on 194 of 300 sampled PCS claims did not meet qualification rules (training, competency, abuse registry, CPR) | — | [HHS-OIG](https://oig.hhs.gov/reports/all/2024/new-mexico-did-not-ensure-attendants-were-qualified-to-provide-personal-care-services-putting-medicaid-enrollees-at-risk/) |
| Ongoing | HHS-OIG work plan **W-00-24-31564** and OEI **OEI-09-24-00290**, "Use of EVV Data for Medicaid PCS" (announced 2024-06-17, expected FY2026) | Not yet published as far as found | — | [OIG work plan](https://oig.hhs.gov/reports/work-plan/browse-work-plan-projects/use-of-electronic-visit-verification-data-for-medicaid-personal-care-services) |

**The states' own audits say "pay-on-match" was missing.** Ohio, New York,
Kansas and Colorado each turned on claims paid without a verified visit. That
is the reason for the hard-edit wave in §3.2. Once a state has closed that gap,
the next audit question is the one the Colorado report reportedly asked: **were
the exceptions reviewed?**

### 4.3 System failures that hurt caregivers, and privacy

- **Arkansas, 2021.** The self-directed PCS go-live on AuthentiCare had "more
  issues than anticipated" (joint Palco/DHS statement). Caregivers went unpaid;
  one reported an eviction notice. The same source says EVV there cost $5.7M
  and recovered $1,930 across 7 charged and 3 convicted.
  ([economichardship.org](https://economichardship.org/2021/07/we-dont-deserve-this-new-app-places-us-caregivers-under-digital-surveillance/),
  advocacy source)
- **Ohio, 2018.** The state-issued device had a camera, GPS and microphone.
  Families reported **seeing strangers' health and contact information in the
  Sandata portal**. Disability Rights Ohio asked twice for a halt.
  ([DRO letter](https://www.disabilityrightsohio.org/assets/documents/00543560.pdf);
  the portal exposure is advocacy-sourced and not independently confirmed)
- **Colorado 2019, national commentary 2023** (Slate, Rooted in Rights): GPS,
  periodic client photos, facial recognition, and GPS revealing where clients
  go. **No filed EVV privacy lawsuit was found.**
- **Vendor-side:** Doctor's Choice Home Care & Hospice (Houston) disclosed that
  compromised credentials gave access to one clinical account in its **WellSky**
  EMR, 2026-06-05 to 07-24, affecting 14,333 people
  ([teiss](https://www.teiss.co.uk/news/doctors-choice-home-care-discloses-data-breach-tied-to-wellsky-vendor-18210)).
  It is a disclosure only, with no EVV data involved. **No litigation or
  regulatory action against any aggregator over EVV accuracy or outages was
  found.**

### 4.4 What the liability lens argues for, mapped to SAIRNsenior

| What the failures show | SAIRNsenior today | Gap |
|---|---|---|
| A clock-in is not presence: every EVV prosecution above is about it | Point-in-time GPS at clock-in/out; refusal disclosed | **No distance-to-client-address check and no flag when the same caregiver clocks two clients at once.** Both could run over data already captured. Record them as signals for a reviewer, never as findings of fraud |
| Device time can be wrong or manipulated | Device clock trusted by design (offline accuracy) | **No flag when device time and server receipt time disagree** by more than the offline queue explains. This is additive, and it must not "correct" the recorded time: the offline code's own rule forbids re-stamping, correctly |
| Exceptions must be reviewed (Colorado), and edits are a regulated rate (Pennsylvania) | **No visit-maintenance path at all** (§1) | When transmission exists this becomes mandatory: an append-only edit record (original value, editor, time, **reason code**) plus an exception queue |
| Tasks against the plan of care (Kansas); units against the authorization (Colorado) | **Units against authorization: built** (A3 burn-down). Tasks against the plan: not found | Partly closed already. The authorization burn-down is directly on point for the Colorado finding |
| Implausible durations (New York: under 8 minutes; while hospitalized) | Readiness rejects clock-out ≤ clock-in; no minimum-duration or hospitalization check found | Minor, and it needs a per-state threshold that must not be invented |
| Caregiver qualifications (New Mexico) | Training panel and credentials exist (A6) | **Whether scheduling is gated on them was not checked in this pass.** SAIRNmechanical's 09-17 finding (an engine with no caller) is the reason to check, not assume |
| Privacy (Ohio portal cross-exposure, GPS objections) | Point-in-time location only; family portal links scoped and revocable | **Already on the right side.** Minimum location capture is a defensible design position and is worth stating in product copy |

---

## 5. Adjacent-industry lens: how vendors actually get onto aggregators

This addresses SAIRNsenior's three named blockers directly. Wire formats are
**not** repeated here; they are in the 2026-08-27 groundwork §4.

### 5.1 Blocker (a): the gate is agency-sponsored certification, not a vendor-signed TPA

- **Sandata altEVV needs a named agency before a vendor can begin.**
  - Colorado: vendors "must have a sponsoring Colorado provider before access to
    onboarding and testing activities can be granted"
    ([HCPF](https://hcpf.colorado.gov/electronic-visit-verification-alternate-vendors)).
  - Connecticut: the vendor "will register for Connecticut and select one
    Provider Agency which has named them", then uses Sandata's Vendor
    Registration Portal for test credentials, scenarios and production
    credentials
    ([CT DSS](https://www.ctdssmap.com/CTPortal/Portals/0/StaticContent/Publications/Alt_EVV_Registration_Process.pdf)).
  - Indiana: the **provider** emails to request vendor certification, then
    passes test credentials to the vendor
    ([in.gov](https://www.in.gov/medicaid/providers/business-transactions/electronic-visit-verification/)).
  - **No signed trading-partner agreement was found at this layer.** What
    exists is registration, testing, certification and, for Tellus, a "Third
    Party Attestation".
- **Certification is once per vendor per state; later agencies are add-ons.**
  - Ohio, from 2021-09-15, requires "only … new vendors to pass certification"
    ([ODM process change](https://dam.assets.ohio.gov/image/upload/medicaid.ohio.gov/Providers/EVV/Outreach/Alt_EVV_Process_Change_08202021.pdf)).
    **Conflict:** another Ohio snippet says certification "for each provider
    Medicaid ID". Possibly per-ID registration rather than re-testing;
    unresolved.
  - Pennsylvania: "Vendors can pass certification by testing successfully with
    one agency account". Production credentials come "within 5 business days"
    and go "to providers only via secure email"
    ([PA quick reference](https://www.pa.gov/content/dam/copapwp-pagov/en/dhs/documents/providers/documents/evv/ALT%20EVV%20Provider%20Testing%20Quick%20Reference%20Guide%20Updated%2012-2020%20v2.pdf)).
- **HHAeXchange:** a state Provider Onboarding Form and attestation, then an
  "API Onboarding Request" with the vendor name, Tax ID and agency name.
  Production API credentials come "within 1-2 business days"
  ([HHAX KB](https://knowledge.hhaexchange.com/edi/Content/Documentation/EDI/API-Onboarding-Integration-P.htm)).
- **Timelines for the first agency in a state:**
  - Wisconsin: "Providers should allow up to three months", and the provider
    "cannot record EVV information using that system" meanwhile
    ([WI DHS](https://www.dhs.wisconsin.gov/evv/alternateevv.htm)).
  - Netsmart: "anywhere from 6-8 weeks from initial contact"
    ([implementation guide](https://mobilecaregiverplus.com/wp-content/uploads/2023/06/Netsmart-Alternate-EVV-Vendor-Implementation-Guide-MT-20230622.pdf)).
- **Ohio's pause and Arizona's testing requirement (§3.2)** both apply on top.

**What this means for SAIRNsenior's blocker list.** Blocker (a) as written, "a
trading-partner agreement per aggregator", describes a document SAIRN would
sign. The real gate is **a pilot agency per state that names SAIRNsenior as its
vendor**. That is a **go-to-market dependency, not a legal one**, and it cannot
be pre-cleared speculatively. The practical consequence: **the first state is
chosen by where the first Medicaid customer is**, not by which spec is
cleanest. The 08-27 groundwork ranked NY, LA and TX by spec quality. That
ranking still holds for learning, but not for sequencing.

### 5.2 Blocker (b): credential custody — the market uses three models

| Model | Who holds it | Where seen |
|---|---|---|
| **The agency obtains the credentials and enters them in the vendor's software** | Agency | **Sandata norm.** Axxess asks for "Business Entity ID, Business Entity Medicaid Identifier, User ID and Password. (This information must be requested from Sandata.)" ([Axxess help](https://www.axxess.com/help/axxess-homecare/integrations/sandata-evv-integration/)). ShiftCare: "Once approved, the aggregator will issue credentials that are entered into ShiftCare" ([ShiftCare help](https://help.shiftcare.com/en/articles/11173417-understanding-shiftcare-and-the-medicaid-technical-ecosystem)) |
| **The agency generates a delegated, revocable credential in the aggregator portal** | Agency, revocable | **HHAeXchange** provider self-service: OAuth2 client id/secret. "Providers can Add and Remove credential sets" ([HHAX KB](https://knowledge.hhaexchange.com/provider/Content/Documentation/Admin/Admin-C-Provider-Self-Service-Client-P.htm)). One Client ID may serve several agencies if EVVMSID is unique |
| **One vendor-level credential; each agency's data in a separate file** | Vendor | **CareBridge** SFTP: "credentials are typically set up at the vendor level"; public SSH key; separate DEV/PROD users ([CareBridge FAQ](https://support.carebridgehealth.com/hc/en-us/articles/1500000864922-Third-Party-EVV-Vendor-Integration-FAQs)) |

**Conflict inside Sandata:** in Connecticut the vendor pulls production
credentials itself ("Get Prod Creds"); in Pennsylvania they go "to providers
only".

**No state guidance on how a vendor must store per-agency credentials
(encryption, rotation) was found.**

**For the open decision in `docs/SAIRN-OPEN-WORK-INDEX.md`:** the market norm
means SAIRN would hold **per-tenant secrets entered by the agency**. That is
the harder of the three models for a platform whose tenants share one backend
(see `docs/2026-09-15-item93-shared-backend-tenancy-scoping.md`). CareBridge's
vendor-level model is the easy exception. HHAeXchange's revocable
agency-generated credential is the safest shape to copy where it is offered.
**This is information for the decision, not the decision.**

### 5.3 Fees: mostly none at the aggregator, and one number that should not be quoted

- **Stated as no charge:**
  - CareBridge "does not charge to integrate with your Third-Party EVV Vendor".
  - HHAeXchange (MN): "MN DHS and HHAeXchange are not responsible for any costs
    related to implementation of a third party EVV system".
  - Alora on Florida: "no additional fees in transmitting EVV data".
- **Costs pushed to the provider or vendor:**
  - Ohio: "Neither ODM nor Sandata are responsible for any costs".
  - Wisconsin: "providers are responsible for any costs".
  - California: providers "will likely incur fees from their EVV vendor".
- **The reported HHAeXchange integration fee could not be verified.** Three
  searches found nothing.
- **Do not quote "$3,360".** One summariser answer said "EVV vendors are asked
  to pay a one-time fee of $3,360 … to assist with testing integrations",
  **without attributing it to any single result** among the Hawaii, DC, Sandata
  and Indiana FAQs. The state and its currency are unknown.
- **Only one competitor discloses a pass-through fee:** Generations, "$25/month
  for EVV, with additional visit verification fees … for state EVV aggregator
  interfaces"
  ([homecaresoftware.com](https://www.homecaresoftware.com/pricing-generations/)).

**The real cost is engineering and support time per state, not fees.**

### 5.4 The TPA belongs to the 837 layer, and that is where blocker (a) actually lives

- A Medicaid EDI trading partner can be "any Provider, billing service,
  software vendor, … clearinghouse"
  ([WI ForwardHealth TPA](https://www.forwardhealth.wi.gov/WIPortal/Subsystem/SW/content/trading%20partner/tradingpartnerprofile_agreement.pdf.spage)).
- Rhode Island: the trading partner "must register all RI Medicaid providers,
  for whom the Trading Partner submits"
  ([EOHHS RI](https://eohhs.ri.gov/providers-partners/billing-and-claims/electronic-data-interchange-edi/trading-partner-enrollment)).
- Minnesota: a trading partner may act "as an agent on behalf of the provider".

The shape is one submitter ID with providers registered under it. Office Ally
publishes per-state Medicaid EDI enrolment packets, so the **clearinghouse
route** absorbs the per-state TPA work. That is why every competitor in §2
names a clearinghouse rather than direct state connections.

**Does EVV ride behind a clearinghouse? Not established.** The evidence shows
EVV and 837 as separate channels. The exceptions are claim-embedded states (WA,
and per §3.2 VA FFS) and aggregators that generate claims themselves
(CareBridge, HHAeXchange).

### 5.5 How competitors present coverage

- **Per-state landing pages naming the aggregator:** AxisCare. For example, PA
  lists HHAeXchange, Tellus/Netsmart and Sandata; NC lists HHAeXchange, Sandata
  and CareBridge.
- **"Certified alternate EVV" claims only where the state certifies:** Alora in
  MA and CA; ShiftCare, which "holds state-issued Alt-EVV certification" in CA.
- **"45+ states"** with a few named: CareSmartz360.
- **A disclosed non-integration:** KanTime, West Virginia.

**Precedent for honesty exists.** A per-state status table with "not certified"
rows is what KanTime does, and it is what `sen-evv-readiness.js`'s
`state_rules: 'not_verified'` already does for rules.

### 5.6 The analogy from adjacent industries

| Industry | Mechanism | Shape |
|---|---|---|
| Payroll | IRS **Form 8655** Reporting Agent Authorization, signed per client, "indefinitely until you revoke it", 2–4 weeks ([IRS](https://www.irs.gov/forms-pubs/about-form-8655)) | One agent identity + a signed, revocable per-customer authorization on file |
| Pharmacy | Bamboo Health PMP Clearinghouse: one submitter account, "add your state to your existing account", multi-pharmacy files ([MO dispenser guide](https://pdmp.mo.gov/wp-content/uploads/2025/09/mo-data-submission-dispenser-guide.pdf)) | One multi-state hub, one vendor account for many customers |
| Medical/dental | Clearinghouse setup "one to two weeks"; payer enrollment "two to four weeks per payer" (low-authority blog) | A clearinghouse absorbs the per-payer work |

**The lesson carries over unchanged:** the durable per-customer artifact is a
**signed, revocable authorization**, not a stored password. Where an aggregator
lets the agency issue a revocable credential (HHAeXchange), that is the
Form-8655 shape. Where it only issues a user/password (Sandata), SAIRN would be
holding a password and not an authorization. That difference belongs in the
credential-storage decision.

---

## 6. Practitioner-voice lens

**Reach was the thinnest of the five lenses.** Review pages (Capterra, G2,
Software Advice, TrustRadius, GetApp, app stores) were all blocked, and Reddit
was refused at both the search and the fetch layer.

Quotation marks below are the snippet's own. Unmarked lines are the snippet's
paraphrase. The counts are **distinct statements in snippets**, not confirmed
independent reviewers. Ratings are as shown on 2026-09-26.

### 6.1 EVV is the loudest and most repeated theme, and it lands on the aggregators' own apps

- **The HHAeXchange caregiver app is the most repeated complaint (at least 6
  statements).**
  - Quoted: "by far the worst clock-in app", "takes forever to load", GPS
    "laughable at best".
  - Paraphrased: clocking in and out at once while closing yesterday's visit;
    15–20 minute waits; a paycheck short by 6 hours; near-weekly outages.
  - Sources: Google Play `com.hhaexchange.caregiver`; justuseapp.
- **Sandata Mobile Connect (about 4 statements):** GPS "never tracks the right
  location"; logs out on every swipe; the same problems unfixed for more than a
  year. **3.18/5 from 520 ratings**
  (justuseapp.com/en/app/1313423167/sandata-mobile-connect/reviews).
- **HHAeXchange agency/portal side:** freezes, 10-minute logins. Agencies say
  they are "forced to use it" because the state only allows HHAeXchange to
  collect EVV data (paraphrase).
- **Double entry is structural, by the aggregator's own guidance.**
  HHAeXchange via TMHP: an agency scheduling in third-party software must not
  also schedule in HHAeXchange, because it creates duplicates
  ([TMHP 2023-11-30](https://www.tmhp.com/news/2023-11-30-evv-third-party-software-system-integration-hhaexchange)).
- **WellSky Personal Care:** lag since Tennessee's Open EVV model began on
  2025-08-01 (September 2025 reviews); clock-in failures; location accuracy
  affecting payroll.
- **Operator testimony, Ohio Senate Medicaid subcommittee, 2026.** Kimberly
  King (COO, Home Care Network; acting treasurer, Ohio Council for Home Care and
  Hospice) testified:
  - phase-1 EVV claim edits from March produced denials providers cannot
    correct quickly;
  - the Gainwell portal is malfunctioning;
  - in one segment, "1 in 13" providers is profitable on Medicaid;
  - a provider survey cited 260,000+ visits and 5,800 patients affected.

  An EVV consultant told the same panel that the Cures Act does not require
  claim denials (citizenportal.ai, BLOCKED).
- **Trade press:** [Home Health Care News, 2024-10](https://homehealthcarenews.com/2024/10/years-after-implementation-evv-remains-inconsistent-paint-point-for-home-care-providers/),
  "Years After Implementation, EVV Remains Inconsistent Pain Point": cost,
  cross-state inconsistency, caregiver technology, **no rural cell service**.

### 6.2 Billing, support, price

- **Billing complaints appear for 7 of 10 products, mostly one statement
  each:**
  - Alora: same code and date on different shifts produce a duplicate claim
    line that is denied;
  - KanTime: clearinghouse setup corrections;
  - AxisCare: payroll miscalculations, QuickBooks Desktop export formatting;
  - WellSky: no QuickBooks Online payroll link;
  - HHAeXchange: weak AR and payment posting;
  - AlayaCare: weak billing;
  - MatrixCare: billing lags clinical.
- **Support is the most repeated retention factor and the most repeated
  defection factor at the same time.**
  - Praised: Alora, AxisCare, WellSky, CareSmartz360.
  - Complaints:
    - HHAeXchange: waits over two hours, bot chat;
    - HCHB: days, poor training; **Software Advice 2.8/5 (53)**;
    - MatrixCare: tier-2 dead end;
    - AlayaCare: consultants "very costly"; price increases "out of control",
      competitors "45 to 65% cheaper" (G2 snippet, not in quotation marks at
      source, unverified).
- **No practitioner complaint about price rises after the 2024–26 acquisitions
  was found.**

### 6.3 Ratings as snippets showed them

| Product | Rating |
|---|---|
| AxisCare | Capterra 4.7/5 (728) |
| Alora | Capterra 4.5/5 (151) |
| WellSky PC | Capterra 4.4/5 (271) |
| AlayaCare | G2 4.1/5 (72) |
| HHAeXchange | Capterra 3.6/5 (100) |
| Sandata Mobile Connect | 3.18/5 (520) |
| HCHB | Software Advice 2.8/5 (53) |

**Capterra runs gift-card incentive programmes and G2 tags incentivised
reviews.** High counts may be solicitation-driven, and which reviews were
incentivised could not be seen.

### 6.4 What the practitioner lens changes

1. **Offline capture is a real differentiator, not parity.** Rural no-signal
   areas are named in trade press and complained about across three vendors'
   apps. SAIRNsenior's replay-unchanged rule is exactly what the "paycheck
   short by 6 hours" and "auto time adjustments" complaints are about. **It
   only pays off once there is something to sync to (§7.1).**
2. **An agency on SAIRNsenior today would re-key visits into the free
   aggregator portal.** HHAeXchange's own guidance warns that this creates
   duplicates, and in Pennsylvania re-keyed visits risk counting as manual
   entries against the 15% ceiling (§3.3). **Readiness without transmission can
   make an agency's regulated edit rate worse.** That is the sharpest single
   argument for transmission in this pass.
3. **Shift-fill matching and in-app open-shift acceptance** are the scheduling
   features agencies praise (AxisCare, WellSky). `open shift` × 0 in
   SAIRNsenior. **Not investigated further here; recorded as a candidate
   gap.**

---

## 7. Synthesis: what SAIRNsenior does not cover, ordered by what a Medicaid HCBS buyer would feel

### 7.1 The real gaps

1. **EVV transmission (A1), now sharpened.** Hard claim edits are live or
   landing in at least AZ, WI, TX, TN, NC, MI, MO and MA. In those states a
   "ready" visit is not a billable one. §6.4 shows that readiness-only can
   *raise* an agency's edit rate by forcing re-keying. **The gate is a pilot
   agency per state (§5.1), not a signed TPA.**
2. **Visit maintenance with reason codes. This is new in this pass.** It does
   not exist (§1). Every aggregator requires exception resolution. Pennsylvania
   regulates the edit rate; Colorado's OIG audit reportedly faulted unreviewed
   exceptions. **It is a prerequisite of transmission, not a follow-on.**
3. **837 / clearinghouse (A4).** Every competitor names a clearinghouse.
   Billing is where 7 of 10 products draw complaints, which is an opening and a
   requirement at once. **In claim-embedded states (WA, and VA FFS if the
   snippet holds), A4 and A1 are the same gap.**
4. **Telephony (A2's second half).** Openly claimed by Alora, WellSky and
   MatrixCare. It covers caregivers without smartphones and clients with only a
   landline.
5. **Per-state, per-quarter EVV quality reporting against the state threshold.
   New in this pass, and the one EVV item that does not need transmission.**
   §3.3. It needs item 2 first to compute an edit rate.

### 7.2 Where SAIRNsenior is on the right side and should say so

- **`state_rules: 'not_verified'`** is the KanTime-style honesty the market
  rarely shows (§5.5).
- **Offline replay-unchanged** addresses the most repeated caregiver complaint
  in §6.1.
- **Point-in-time location, with refusal disclosed**, is the privacy posture
  the §4.3 advocates argue for.
- **Authorization unit burn-down** is directly on point for Colorado's OIG
  finding: units paid above approved (§4.2).
- **The refused profit figure (B5)** is still correct. The 80/20 rule, if it
  survives, will make per-agency *compensation share* a reported number
  (2027–2030). A number SAIRNsenior invents would be worse than none.

### 7.3 Candidate items this pass recorded but did not investigate

- **Scheduling gated on caregiver credentials:** New Mexico OIG; SAIRNmechanical
  09-17 precedent. **Check before claiming.**
- **Open-shift broadcast / shift-fill matching** (`open shift` × 0).
- **Tasks-against-plan-of-care** (Kansas OIG).
- **Device-vs-server time signal** (§4.4).
- **80/20 compensation-share reporting.** **Do not build until the rescission
  question resolves.** Record the cost and compensation components flexibly if
  touched at all.

---

## 8. What this document does not establish or decide

- **No page was opened.** Every external claim is [SNIPPET] (§0.1).
- **CMS's per-state EVV compliance tables were blocked.** Which states are
  under FMAP reduction in 2025–26 is unknown.
- **The December 2022 GFE guidance and the May 2022 1915(c) note were not
  found.** The readiness module's residual-gap disclosure stands unchanged.
- **Whether the CMS-2442-F rescission was published** by 2026-09-26 is unknown.
- **The actual EVV text of Ohio SB 315** was not read, including GPS.
- **Unresolved conflicts, kept rather than reconciled:**
  - Ohio certification per vendor vs per Medicaid ID;
  - Sandata production credentials to vendor (CT) vs provider only (PA);
  - Virginia live-in exemption vs the 2026-10-01 change for consumer-directed
    attendants;
  - Wisconsin "must use DHS Sandata" vs open;
  - Maryland closed vs integrate;
  - Texas 2024 bypass;
  - HHS moratorium scope;
  - 80/20 reporting start and scope;
  - Alora pricing model;
  - WellSky and AlayaCare third-party prices;
  - HCHB market share;
  - Favorite Home Care date;
  - PA August 2026 defendant counts;
  - NY $14.5B framing.
- **Does not establish:**
  - an HHAeXchange integration fee;
  - the state behind "$3,360";
  - MatrixCare, HCHB or CareTime state lists;
  - HCHB Personal Care's launch date or feature list;
  - whether AlayaCare has telephony.
- **No Reddit, KLAS, Home Care Pulse or association comment letter** was
  reached.
- **No SAIRNsenior pricing is compared.** That is a commercial decision.
- **The credential-storage decision and the pilot-agency decision are not
  made.** §5.2 and §5.1 are information for them.
- **No code was written and no app file was touched.** The §1 findings about
  visit maintenance and device time are **grep floors against `origin/main`
  `e560d97d`**, not a full read of `sairnsenior.html`. The first move on either
  is to confirm by reading, not to build.

## 9. Decay, and what to re-read first

This pass is dated by three events:
- the MatrixCare close (about 2026-09-01);
- Ohio SB 315's effective date (about October 2026);
- Massachusetts FFS hard edits ("September 2026").

Anything here that disagrees with a page read after those dates should be
re-fetched rather than reconciled.

**The figures most worth opening first, from a network that can reach them:**
1. CMS HHCS and PCS EVV compliance-status tables (medicaid.gov). These are the
   only source for current FMAP-reduction states.
2. PA MA Bulletin 05-25-03. This is the 85% / 15% thresholds, the basis of
   §3.3.
3. HHS-OIG A-07-24-03260, Colorado. This is the 160-claim breakdown and the
   $45.7M set-aside.
4. Ohio SB 315 as enrolled, and ODM's alternate-vendor pause notice.
5. The CO, CT and PA Sandata alternate-vendor pages. These are the
   sponsoring-agency rule and the custody conflict, the basis of §5.1 and §5.2.
6. The Virginia DMAS FFS EVV-in-837 rule. This decides whether §3.2's second
   claim-embedded state is real.
7. Alora's pricing page. It is the only published competitor price in this
   pass.

## Sources

Every source is linked inline where it is used. All were accessed 2026-09-26.
All are [SNIPPET]: WebFetch to each was refused (§0.1) or was not attempted.

Internal sources, read from the repository at `origin/main` `e560d97d`:
- `sairnsenior.html`
- `api/_lib/sen-evv-readiness.js`
- `sql/sairnsenior_visits_schema.sql`
- `api/_lib/sairnsenior-offline-evv.test.js`
- `docs/2026-09-17-senior-mechanical-competitive-gap-rederived.md`
- `docs/superpowers/specs/2026-08-26-competitive-gap-audit-roofing-dental-senior.md`
  §5
- `docs/superpowers/specs/2026-08-27-evv-transmission-groundwork.md` §§3, 4, 7
