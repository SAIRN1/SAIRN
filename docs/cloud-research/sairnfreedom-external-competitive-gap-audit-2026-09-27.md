# SAIRNfreedom external competitive-gap audit (2026-09-27)

This pass covers five lenses:
- **Competitive / market:** MemberClicks, Wild Apricot, GrowthZone and ClubExpress.
- **Regulatory:** the app's Ohio liquor and charitable-gaming citations, checked against current law.
- **Accuracy / liability:** documented penalties and thefts at posts and lodges.
- **Adjacent industry:** member dues and canteen/bar POS.
- **Practitioner voice:** what officers and small-club admins say about their tools.

**Scope and rules.** This is a research pass dated 2026-09-27, in the isolated
cloud-research lane. It is docs only: no app code, and no tier register was
touched. The file is new, under `docs/cloud-research/`, on the PR SAIRN1/SAIRN#18
branch.

**Claim.** Session `cloud` claimed the work before starting (`9752c1d1` on
`origin/main`, subject `sairnfreedom`); `sairn_claim.py check` returned CLEAR.
**One adjacent claim, with no file overlap:** `cody-q14` is writing
`docs/2026-09-27-sf-events-tier-cell.md`, a criticality cell for the `sf_events`
table. This document touches neither that file nor the tier register.

**This is not a first pass.** SAIRNfreedom already has four primary-source
research documents from 2026-08-30. They were read against codes.ohio.gov and
vendor pages while the network allowed it:
- `docs/2026-08-30-sairnfreedom-competitive-and-patent-scan.md`
- `docs/2026-08-30-sairnfreedom-ohio-liquor-permits.md`
- `docs/2026-08-30-sairnfreedom-four-research-items.md`
- `docs/superpowers/specs/2026-08-30-sairnfreedom-research.md` (the canonical
  one, including the ORC 2915 re-verification)

This pass **does not repeat them**. It adds what they did not cover: the four
named vendors, 2025–2026 legislation, enforcement cases, and the practitioner
lens. It also re-checks the app's own citations against the snippets gathered
today.

---

## 0. Read this before quoting anything

### 0.1 Network: broader access was approved but is not live yet

Michael approved widening this environment's Network access. **As of this pass
it had not taken effect:**
- At 02:41 UTC on 2026-09-27 the proxy's `recentRelayFailures` recorded
  `connect_rejected`, "gateway answered 403 to CONNECT", for `example.com`,
  `codes.ohio.gov` and `www.irs.gov`.
- `WebFetch` of `codes.ohio.gov` returned `EGRESS_BLOCKED`.
- A re-test at write time was still refused.
- Each of the five research agents also tried one fetch before starting:
  `codes.ohio.gov`, `wildapricot.com`, `ohioattorneygeneral.gov`,
  `squareup.com` and `capterra.com`. **All five were blocked.**

The diagnosis is unchanged from the SAIRNcash doc §0.1: it is a standing egress
policy, not a fault of this pass.

**So every external claim below is [SNIPPET]:** the search tool's
model-written summary of a result page, not the page itself.

**The two 2026-08-30 documents are graded higher.** They quote codes.ohio.gov
and vendor pages that were opened. Where this pass agrees with them, the higher
grade is theirs. Where this pass *disagrees* with them or with the app, the
disagreement is snippet-grade until the page is opened. §9 lists exactly which
pages to open.

**Re-verifying the SAIRNsenior and SAIRNbiz sources is still pending, not
skipped.** The request was to go back through their flagged sources "once you
have access". Access was not live, so nothing was re-verified. §9.2 lists what
to fetch first when it is.

**Budget.** Five lenses used 190 WebSearch calls (38 each). 5 WebFetch probes
were made, all blocked.

### 0.2 Corrections to the brief

1. **"OAC 4301" is the wrong code for the liquor rules.** The liquor
   administrative rules are **OAC Chapter 4301:1-1**. The statutes are **ORC
   Chapters 4301 and 4303**, and the D-4 club permit itself is **ORC 4303.17**.
   The app cites all three correctly (§1).
2. **"Gaming-session limits (ORC 2915)" are mostly a definition, not a conduct
   rule.** The 5 + 2 + 2 hour window is the *definition* of "bingo session" at
   §2915.01(S). The canonical research doc (CORRECTION 1) already records this.
   The conduct limits are in §2915.09(C): 3 sessions per 7 days, a $6,000 prize
   cap, and the 2 a.m.–10 a.m. blackout.
3. **"The app already gates bookings on both" holds**, with qualifications
   given in §1.2:
   - `liquorServiceCheck()` refuses service in the OAC 4301:1-1-49(B) hours.
   - The F-2 checks refuse more than four days, and more than one F-2 per
     renter in thirty days.
   - The session checks cite §2915.09(C)(4), (C)(5) and (C)(6).

---

## 1. Internal grounding: the app's citations, measured first

**What was read:**
- `sairnfreedom.html` at `origin/main` `9752c1d1` (the file was last changed in
  `c0ae9a0a`); 403,571 bytes and 27 panels.
- `api/_resources/sairnfreedom.js`.
- Counts are grep floors. The gate functions were read, not run.

**What the app cites:**
- Chapter 2915 × 139.
- 4301 × 40.
- about 30 distinct `cite:` strings on refusal and flag paths.

The most-cited sections:
- 2915.101 (×16)
- 2915.10(C) (×13)
- 2915.01(V) (×11, split between (V)(2) and (V)(3))
- 4301.22 (×5)
- 2915.09(C)(6) and (C)(7) (×5 each)
- OAC 4301:1-1-53(D), -49(B) and -36(B) (×4 each)

### 1.1 The citation check, claim by claim

Verdicts come from the regulatory lens, all [SNIPPET]. Where a 2026-08-30 primary
read exists, it is noted.

| App's claim (where) | Verdict today | Note |
|---|---|---|
| §2915.01(S)(1)/(2): 5 h, plus 2 h before and 2 h after for instant bingo | **Match** | 2915.01 was amended by **HB 96, effective 2025-09-30**; the authenticated PDF path `2915.01-9-30-2025` exists. The (S) text was primary-read on 2026-08-30 |
| §2915.09(C)(4): at most 3 sessions in any 7 days | **Match (substance)** | The volunteer fire/rescue exception does not reach posts |
| §2915.09(C)(5): $6,000 prize cap per session | **Match** | Applies to traditional bingo ((O)(1)) only; **instant bingo prizes are excluded** |
| §2915.09(C)(6): no session 2 a.m.–10 a.m.; instant bingo sales from 9 a.m. for a 10 a.m. session | **Match** | Primary-read on 2026-08-30 |
| §2915.09(C)(7)/(C)(8)/(D)(1): who may work a game | **Match (substance)** | Operators must be **18 or older** (also §2915.11). No felony or gambling conviction. No compensation of any kind |
| §2915.09(A)(1): equipment "owned or leased from licensed sources" (vendor tile) | **Partly** | The snippet reads: supplies may be bought or leased only from "a distributor issued a license under section 2915.081". **The source is a licensed *distributor*.** The app's wording, "licensed sources", is looser than the statute but not wrong in effect. Whether the division is (A)(1) was not confirmed |
| §2915.10(A) records list, 3-year retention; (C) exclusive bingo checking account | **Partly (snippet); Match (2026-08-30 primary)** | Snippets confirm the exclusive account, the SSN rule for prizes of $600 or more, and 3-year retention. The full (A)(1)–(7) list, including food and beverage receipts, was primary-read on 2026-08-30 and is not contradicted |
| §2915.101 tiers: 25% of the first $250,000; above that, 50% distributed, 5% to own purposes, 45% retained | **Structure match. The threshold figure may be stale** | The app correctly makes the threshold **configuration**, citing the AG's CPI adjustment (`getP4Config`, default `250000`). **One snippet phrases the first tier as "the first three hundred thirty thousand dollars"**, which suggests the indexed amount is now about **$330,000**. Where that is set (possibly OAC 109:1-4-21, version dated 2023-11-01) was not confirmed. **See §1.3 for why the default matters more than it looks** |
| §2915.01(V)(2) veteran / (V)(3) fraternal limbs; 15 years' continuous existence | **Match** | (V)(3) was quoted in the snippet. Primary-read on 2026-08-30 |
| "75% veteran membership test" (canonical research doc, attributed to (V)(2)) | **Location questioned** | The snippet places the 75% wording in the ***veteran's organization* definition** (§2915.01(J) per the 2026-08-30 doc), not in the (V)(2) purpose limb. It matches the IRC §501(c)(19) test. Worth a primary re-read before any UI cites a division for it |
| §2915.01(GG)(11), (T), (EE): canteen expense; gross receipts; gross profit | **Match** | (GG) and (EE) lettering confirmed by snippet; (GG)(11) primary-read on 2026-08-30 |
| ORC 4303.17: D-4 "to its members only, in glass or container, for consumption on the premises where sold"; officer certification of initiation fee and yearly dues | **Match** | Effective **2021-09-30**; D-4 fee **$469**; the club must have existed 3+ years. **The "(A)(1)" subdivision did not appear.** The text read as undivided, so the app's `ORC 4303.17(A)(1)` cite (×4) needs a primary check. **No guest rule** in the statute, which matches the 2026-08-30 finding |
| OAC 4301:1-1-49(B): D-4 in the 1 a.m. group; Sunday closed without a D-6; consumption barred too | **Match** | Rule PDF dated **2024-05-01**. **D-4A sits in the 2:30 a.m. group (C).** The app's `HOURS_1AM_GROUP=['D-4']` and its disclosed conservative default for other classes are correct. ORC 4303.182 (D-6) is effective 2022-03-23; start times of 10 a.m. or 11 a.m. per the local question (older version) |
| ORC 4301.22(A)(2)/(A)(3): beer at 19, wine/spirits at 21 (`minSellAge`) | **Match for sales across the bar** | "No person under nineteen years of age shall sell beer across a bar"; under 21, no wine, mixed beverages or spirits across a bar. **Nuance not modelled:** a person 19 or over may *handle open containers as a server* in a club. The app's 21 for spirits is the conservative reading. Division numbers were not confirmed |
| F-2: four consecutive days; one per thirty days per renter; notify the chief peace officer; record proceeds | **Match on days and frequency; partly on the rest** | "No F-2 permit shall be effective for more than four consecutive days"; one per 30 days per organisation; fee $150 ($160 in one snippet when joint). **F-2 hours conflict:** D-3 hours versus 1 a.m. This is the same unresolved item as §10.7 of the liquor doc. The statutory basis for the peace-officer notice was not found (it is in the Division's guide) |
| OAC 4301:1-1-36(B): joint F-2 issuance | **Match (substance)** | The F-2 may issue jointly with a D-3, D-4 or D-5 holder. Paragraph (B) not confirmed |
| OAC 4301:1-1-53(D)–(E): a Chapter 2915 violation is a liquor-permit exposure | **Match** | (D) and (E) exempt charitable games only "so long as there is strict compliance with Chapter 2915". A 2915 violation leaves the safe harbour. **ORC 4301.03** separately bars any rule that stops a D-4 charity serving in part of its premises "merely because" bingo is held there |
| **OAC 4301:1-1-43(J)(2): beer "sale must be for cash"** (vendor tile text) | **MISMATCH in wording** | The snippet says wholesale purchases "may be paid for by cash, check, debit card, credit card, money order, or electronic funds transfer". **Only *credit terms* are banned** (ORC 4301.24; the payment-method list is probably OAC 4301-9-01). An officer reading "must be for cash" will take it as currency only. **Copy correction, not a gate change:** the tile is advisory and blocks nothing |
| **OAC 4301:1-1-46(B): discounts and rebates banned both ways** | **Likely mis-cited** | The snippet puts discounts and rebates in **OAC 4301:1-1-45**, not -46. The substance is not disputed |
| OAC 4301:1-1-72(B)(3): 25% minimum markup, off-premises only | **Match** | "not for consumption on the premises where sold and in sealed containers". The app already says it does not bind a D-4 bar |
| ORC 4301.25(A)(3) false material statement; ORC 4301.99(C) first-degree misdemeanour | **Partly** | False material statement in a permit application is grounds for suspension or revocation: confirmed. **Whether 4301.99(C) reaches a false application statement was not confirmed.** Its listed sections are 4301.21, .251, .58–.60 and others. The app pairs the two in its fee-schedule warning, so this needs a primary check |

**Net:** of the roughly 19 distinct statutory claims checked, there are:
- **no substantive mismatches in any gate that refuses something**;
- **one wording mismatch in advisory copy** ("for cash");
- **two likely mis-citations** (-46 for -45; 4303.17 "(A)(1)");
- **one possibly stale default** (the 2915.101 threshold).

The 2026-08-30 primary-source discipline shows.

### 1.2 Two things the law changed after the app's research, which the app does not reflect

1. **HB 96 (effective 2025-09-30), per the LSC summary [SNIPPET]:**
   - It **clarifies that a charity holding a D-4 may serve alcohol while
     conducting instant bingo, electronic instant bingo or a raffle**.
   - It **adds online raffles**, distributed on the veteran/fraternal formula.

   The app does not block alcohol during sessions: `alcohol` is a flag on the
   event record and no refusal was found. So it is **not in conflict** with the
   clarification. But `HB 96` × 0 and `raffle` × 0: **online raffles are
   unmodelled**.
2. **SB 197 (introduced 2025-05-13; enactment NOT confirmed) [SNIPPET]:**
   - It would move all charitable gaming licensing and enforcement **from the
     Ohio Attorney General to the Ohio Casino Control Commission on
     2027-01-01**.
   - AG licences and rules would carry over.

   The app hard-codes "Ohio AG" as the regulator in its instant-bingo
   quarterly-report copy and deadlines ("Ohio AG deadlines are 28 February, 31
   May, 31 August and 30 November"). `Casino Control` × 0. **If SB 197 is
   enacted, the regulator's name, and possibly the deadlines, move on a known
   date.** Check its status first (§9.1).

### 1.3 A compliance-critical setting is held on the device only, by documented design

**What is kept off the server.** `api/_resources/sairnfreedom.js` lists **seven
keys deliberately excluded** from the server backup, each with a reason. Among
them:
- `sf_post`: "the post's own identity/config object";
- `sf_fees`: "configuration";
- `sf_phase4_config`: "configuration".

`SF_SYNCED` in the app matches that list: 35 keys are synced, and none of these
three is among them.

**What those three keys control:**
- `sf_post.liquor` and `sf_post.d6` choose the liquor-hours rule
  `liquorServiceCheck()` applies. They decide whether Sunday is closed.
- `sf_fees.perCapita` drives the national per-capita liability recorded at
  admission.
- **`sf_phase4_config.threshold`** is the §2915.101 tier boundary. **If it is
  $330,000 today, the $250,000 default overstates the 25% tier's reach, and the
  required distribution with it.** A second device, a cleared browser or a new
  quartermaster falls back to the default without warning.

**Precedent.** This is the class of finding the 2026-08-26 audit raised for
SAIRNsenior's `sen_evv_config`: "a compliance-critical, state-mandated
configuration held device-local". SAIRNsenior closed it on 2026-08-27 by moving
the configuration to a server table.

**Why this is not a defect finding.** The exclusion here is **written down with
a reason, not accidental**, and the reason ("configuration") is defensible for
a rate card. It is weaker for a setting that decides:
- whether a sale is lawful (permit class, D-6);
- how much must go to charity (the threshold).

**Recorded as a design decision to revisit, not a defect.** The same audit trail
that makes the gates trustworthy should cover the settings they read.

### 1.4 Stale copy inside the app

`sfRenderProfitChain()` (~L3588) tells the user:

> "Those rules are Phase 4 and are **not built**. ORC 2915.101 is tiered…"

But Phase 4 **is** built:
- `TIER1_MIN_DISTRIBUTION`, `TIER2_MIN_DISTRIBUTION` and
  `TIER2_OWN_PURPOSE_ALLOWANCE` are at ~L4813;
- `tieredRequirement()` is at ~L4860;
- a shortfall computation (`shortfall=req.required-distributedTiered`) is at
  ~L5067.

A treasurer reading the profit-chain panel is told the distribution test does
not exist. **§4 shows that test is the one the AG enforces most often.** This is
a one-line copy fix, flagged rather than made (this lane touches no app code).

---

## 2. Competitive / market lens

All rows are [SNIPPET]. **VSC** marks a vendor's claim about its own product.

### 2.1 The market event: Momentive now owns Wild Apricot and MemberClicks

- **Momentive Software announced on 2026-01-06 that it had acquired
  Personify.** Terms were undisclosed. Momentive claims more than 37,000
  organisations and "287M members" (VSC)
  ([GlobeNewswire](https://www.globenewswire.com/news-release/2026/01/06/3214006/0/en/);
  [Momentive](https://momentivesoftware.com/press-releases/personify-acquisition/)).
  A third-party source says Momentive is a TA Associates portfolio company.
- **Personify brought three relevant products into that deal:**
  - Wild Apricot, bought September 2017;
  - MemberClicks, reportedly bought September 2021, date unconfirmed;
  - **Personify eBusiness, which runs the American Legion's national MyLegion.org**
    (§6.3; seen in the URL path `mylegion.org/PersonifyEbusiness/…`).

  **One owner now sits on both sides for a Legion post:** the national roster
  system and the generic small-club tool.
- A competitor blog says the deal also brought in **MIP Accounting** (a fund
  accounting product). This was not confirmed from Momentive.
- **Momentive's AI:** MomentiveIQ, then "Agentic Workers" in **August 2026**
  (Membership Assistant, Community Assistant) (VSC).

### 2.2 The four named products

| | **Wild Apricot** | **MemberClicks** | **GrowthZone** | **ClubExpress** |
|---|---|---|---|---|
| Owner | Momentive (via Personify, 2026-01) | Momentive (via Personify) | **Lead Edge Capital** (closed 2023-05-10; Greenridge from 2019). Acquired MemberSuite on 2023-09-21 and JUNO in May 2024 | **Lumaverse Technologies** (2022-06-14) |
| Segment | Small nonprofits, clubs, associations | Individual-member orgs (MC Professional, formerly Oasis) and trade/chambers (MC Trade, formerly Atlas) | Chambers of commerce, associations | Clubs, including multi-tier ones |
| Price | By contacts; every tier has every feature. **Conflicting figures:** 500 contacts at $120, $140 or $154/mo across sources | From **$3,500/yr** (Trade) and **$4,500/yr** (Professional); quote above that. About +20% reported July 2023 | Quote; from about **$3,900/yr** | **Vendor PDF dated 2023-03-30:** 42¢ per member per month up to 200 members, 38¢ for 201–300, 34¢ for 301–500, 30¢ for 501–1,000; minimum $24/mo (another source says $35) |
| POS | **None** beyond in-app card taking via Personify Payments | None found | "POS capabilities" in one unattributed summary; **unverified** | **Through partner Addmi** (member ID at the register, house tab) |
| Accounting | No fund accounting; QuickBooks only via third parties (NewPath, Zapier) | QuickBooks and Dynamics GP integration (VSC) | Native QuickBooks Online sync (VSC) | "not a full accounting system" (2026-08-30 scan); QuickBooks export +$20/mo |
| Hierarchy | **Each chapter is a separate account**; volume discount at 5+; **no rollup, no dues split** | Not established | Not established | **Chapter → district → region, with automatic dues split into separate bank accounts at each level** (VSC). **The closest match found to SAIRNfreedom's district rollup and per-capita flow** |
| Facility booking | None found | None found | Conference-room booking (VSC) | None found |
| AI | None native found | "Data Insights" (2024-10-22); "Smart Newsletter" (April 2025) | AI-drafted reminders, reviewed by staff (2026-09-17 post) | Vague "AI-powered workflows" |

Sources:
- **Wild Apricot:** [Capterra pricing](https://www.capterra.com/p/76116/WildApricot/pricing/); [multi-chapter](https://www.wildapricot.com/multi-chapter-accounts); [mobile app](https://www.wildapricot.com/features/mobile-app).
- **MemberClicks:** [MemberClicks Professional](https://memberclicks.com/products/professional/).
- **GrowthZone:** [William Blair](https://www.williamblair.com/News/GrowthZone-and-Lead-Edge-Capital-Transaction); [GrowthZone QBO](https://www.growthzone.com/quickbooks-online-integration).
- **ClubExpress:** [pricing PDF](https://s3.amazonaws.com/ClubExpressDocument/What_Is_ClubExpress_Pricing.pdf); [hierarchy help](https://help.clubexpress.com/hc/en-us/articles/24780850974235-Adding-Regions-Districts-and-Chapters).

**Also found.** re:Members (formerly Billhighway / ChapterSpot / greekbill /
Impexium) renamed itself in **January 2025** and describes itself as serving
"fraternal and chapter-based organizations". That means Greek-letter and
professional societies; **no evidence was found that it serves veterans posts or
lodges**.

### 2.3 Wild Apricot's price and support history: the switching pitch

- **Price rises:**
  - +20% in 2021 and +25% in 2023, per Kessler Freedman, a web-development firm;
  - an unstated rise in 2025;
  - **about +5% in April 2026**, around 80 days after the takeover.
  - One competitor figure of "up to 65%" is marketing and low confidence.
- **Surcharge:** 20% on the subscription for using Stripe, PayPal or
  Authorize.Net instead of Personify Payments, reportedly now AffiniPay.
- **Ratings:**
  - Trustpilot **1.6/5** (147–159 reviews) against Capterra **4.5/5** (513+),
    where Capterra runs gift-card incentive campaigns (§6.4).
  - Support is reported as chat or email only, with no phone.
- Sources:
  - [Kessler Freedman 2021](https://www.kesslerfreedman.com/2021/05/the-wild-apricot-price-increase-of-2021/)
  - [Kessler Freedman 2023](https://www.kesslerfreedman.com/2023/02/another-odd-numbered-year-another-wild-apricot-price-increase/)
  - [Trustpilot](https://www.trustpilot.com/review/wildapricot.com)

### 2.4 Arrow Tab King is still the direct competitor, and it has more endorsement than known

The 2026-08-30 scan named Tab King as the one product covering membership, bar
and gaming. This pass adds three things:
- **A VFW National release, 2021-03-15:** "Tab King to Offer Digital Solutions
  for VFW Posts". It describes POS with membership-dues tracking, sales,
  inventory and reporting, plus a VFW-specific site `vfw.tabkingusa.com`
  ([VFW](https://www.vfw.org/media-and-events/latest-releases/archives/2021/3/tab-king-to-offer-digital-solutions-for-vfw-posts)).
  **VFW National has therefore endorsed a POS vendor, as well as EO M.A.P.S. for
  accounting.**
- **Every Moose lodge in Vermont runs Tab King**, via the Northeast Moose
  Association. The release is dated 2021-04-23 per one snippet
  ([Tab King](https://www.tabkingusa.com/press-release/nema-vt)).
- **Tab King's Moose card swipe** shows Lifetime, Current, Expiring Soon or
  Expired, can renew at the register, and flags underage customers on an ID
  swipe ([Tab King NEMA](https://www.tabkingusa.com/press-release/nema)).
  **Whether it reads Moose International's live data or a local roster was not
  established.**
- The only price found is third-party and low confidence: $49 / $79 / $129 per
  user per month. **No 2024–2026 product news, and no evidence either way on
  ORC 2915 fund segregation or district rollup.**

### 2.5 What the competitive lens changes

1. **Membership software is not the contest.** Wild Apricot, MemberClicks and
   GrowthZone have no bar POS, no bingo accounting and no fund segregation. The
   contest for a post is **Tab King** (POS + gaming + membership, endorsed by
   VFW National and a Moose association) plus **M.A.P.S. or QuickBooks** for the
   books.
2. **ClubExpress's three-level hierarchy with an automatic dues split** is the
   only rival shape for SAIRNfreedom's district rollup. It is a general
   org-chart feature, not a regulatory rollup, as the 2026-08-30 scan found, but
   it is closer than anything else.
3. **The Momentive consolidation** (price rises, a payment surcharge, support
   cuts) is a real switching pitch for posts on Wild Apricot. **It is also a
   warning:** the same owner now runs the Legion's national roster system.

---

## 3. Regulatory lens beyond the citation check

§1.1 and §1.2 carry the substance. This section records only what is not in
them.

- **Charitable bingo licensing: the AG still licenses it.** From the January
  2026 fee list [SNIPPET]:
  - **Type I (traditional, 26–52 weeks): $200 a year**;
  - **Type II (instant bingo at a session, initial): $500**;
  - Type III fee not found.

  Source: [LSC 2026 AG fees](https://www.lsc.ohio.gov/assets/organizations/legislative-service-commission/files/2026-state-agency-fees-ago.pdf);
  [AG Charitable Bingo](https://charitable.ohioago.gov/Charitable-Bingo).
- **The Liquor Control Commission's 2026 five-year rule review is in progress.**
  Hearings moved to 1970 W. Broad St. from 2025-07-01
  ([LCC](https://lcc.ohio.gov/laws-and-rules)). **Any OAC 4301:1-1 paragraph the
  app cites could be renumbered during 2026–27.** The app cites down to the
  paragraph, so this review is the date its citations are most likely to go
  stale.
- **No 2024–2026 change was found** to DORA rules, D-4 permit types, liquor fees
  or Division guidance on clubs. **No skill-games enactment was found.**
- **OAC 109:1-5-14**, the electronic instant bingo quarterly report, is the rule
  the AG cites in the §4 cases. The app computes and flags the report due date
  but **does not cite the rule** (`109:1-5-14` × 0). The four due dates in the
  app were not re-verified in this pass.

---

## 4. Accuracy / liability lens: what actually gets Ohio posts penalised

All rows are [SNIPPET]; **none of the AG PDFs was opened.** In the status column,
*notice* means a notice of intent (an allegation), and *order* and *settlement*
are outcomes.

### 4.1 Ohio AG charitable-bingo enforcement, 2024–2026: mostly records, not theft

| Date | Organisation | What | Amount | Status | Source |
|---|---|---|---|---|---|
| 2026-04-15 (hearing 04-29) | **American Legion No. 243** (Galion) | Notice of intent to deny its 2026 licence: **underpaid its contracted charity** contrary to §2915.101(A)(1) | $23,945.70 short | Notice; outcome not established | [AG PDF](https://charitable.ohioago.gov/Charitable-Bingo/Bingo-Enforcement/Notices-of-Intent/Notice-of-Intent-American-Legion-No-243.pdf) |
| 2025–2026 | **FOE No. 316** (Salem) | **Materially misrepresented** on its 2025 application that its charity received $61,012.36 | **$2,500 penalty + $106,529.91** shortage repaid over 24 months | Notice, then settlement (settlement URL not confirmed) | [AG PDF](https://charitable.ohioago.gov/Charitable-Bingo/Bingo-Enforcement/Notices-of-Intent/The-Fraternal-Order-of-Eagles-Post-No-316.pdf) |
| 2025-11 | **FOE No. 213** (Youngstown) | Revocation. The absent president "led to theft"; **blank checks signed without the two required signatures**; an officer not on the application managed bingo; a former officer sold tickets illegally | Revocation | Notice, then adjudication order | [Notice](https://charitable.ohioago.gov/Charitable-Bingo/Bingo-Enforcement/Notices-of-Intent/Fraternal-Order-of-Eagles-Post-No-213.pdf) |
| 2025-11-10 | **AMVETS No. 24** (Dayton) | Revocation sought: **incomplete quarterly electronic instant bingo reports** (OAC 109:1-5-14), Q1–Q3 | Revocation sought; later settlement | Notice, then settlement | [Notice](https://charitable.ohioago.gov/Charitable-Bingo/Bingo-Enforcement/Notices-of-Intent/Amvets-Post-No-24.pdf) |
| 2025-07-23 | **American Legion Post 52** | Q1 and Q2 reports incomplete | Settled Nov 2025 | Settlement | [Notice](https://charitable.ohioago.gov/Charitable-Bingo/Bingo-Enforcement/Notices-of-Intent/American-Legion-Post-52.pdf) |
| 2024–2025 | **American Legion Post 178** | Reports not filed complete or on time; an inspection had to request them | Settlement (terms not established) | Settlement | [Notice](https://charitable.ohioago.gov/Charitable-Bingo/Bingo-Enforcement/Notices-of-Intent/American-Legion-Post-178.pdf) |
| 2023–2024 | **American Legion Post 366** (Flushing) | Late or incomplete reports, plus distribution shortages | **$1,000; revised internal controls within 60 days** | Settlement | [AG PDF](https://charitable.ohioago.gov/Charitable-Bingo/Bingo-Enforcement/Settlement-Agreements/Settlement-Agreement-Flushing-American-Legion-Post.pdf) |
| 2022–2024 | **FOE Circleville No. 685** | Electronic instant bingo **outside licensed hours on at least 279 occasions**, proved by time-stamped play data | **$10,000 (Scioto Post) or $15,000 (one summary of the AG PDF), unresolved**; training for all officers | Settlement | [Scioto Post](https://www.sciotopost.com/circleville-eagles-reach-10000-settlement-with-ohio-attorney-general-over-bingo-violations/) |
| 2025-03-18 | FOE No. 760 | Licence denied because the **IRS revoked its exemption** (the cause was not stated; auto-revocation usually follows three years of unfiled 990s) | Denial | Notice | [AG PDF](https://charitable.ohioago.gov/Charitable-Bingo/Bingo-Enforcement/Notices-of-Intent/Fraternal-Order-of-Eagles-760.pdf) |

### 4.2 Thefts from posts: every one is a segregation-of-duties failure

| Case | Amount / outcome | The control that failed | Source |
|---|---|---|---|
| **AMVETS Post 24, Dayton**: the commander moved money out of the fundraising and scholarship accounts, then made **1,900+ card and ATM transactions**, 2022–2024 | About **$622,000**; **41 months** federal prison (plea). The same post drew the AG notice above | Transfers between accounts and card use unreconciled for about 2.5 years | [DOJ SDOH](https://www.justice.gov/usao-sdoh/pr/former-commander-local-amvets-post-sentenced-more-3-years-prison-embezzling-hundreds) |
| **VFW Post 4044**: the quartermaster wrote charitable-account checks with memos like "help veterans in need" and split the money with the VFW of Ohio Charities executive director, 2017–2019 | $35,007.30; both pleaded (2025) | **False purposes on charitable checks passed review for about 2 years** | [Ohio AG Jan 2025](https://www.ohioattorneygeneral.gov/Media/News-Releases/January-2025/Former-Quartermaster-Sentenced-for-Theft-From-Cent) |
| **Miamisburg Moose**: the administrator's card spending and **unauthorised raises and bonuses**, 2022–2024 | Restitution $119,420.67 (plea) | No board review of card statements or payroll changes | [Dayton Daily News](https://www.daytondailynews.com/crime/former-miamisburg-moose-lodge-admin-pleads-guilty-gets-sentence-in-embezzling-case/GEX54UJK2FAGTHADUYIF66TZH4/) |
| **Piqua American Legion Post 184**: money from bank accounts to play Keno, 2017–2020 | Over $122–124K (outlets disagree) (plea) | Undetected for nearly 4 years | [Dayton Daily News](https://www.daytondailynews.com/local/woman-who-embezzled-124k-from-american-legion-sentenced-in-court/CDCVZQKAOFE5RASMAEUGVS5PZM/) |

### 4.3 The liquor side: older cases only

**No 2015–2026 Liquor Control Commission order was found against a named Ohio
fraternal D-4 club** for non-member sales, after-hours sales or sales to minors.
What was found:
- The 2020 **Ohio Investigative Unit raid on American Legion Post 328, Dayton**:
  unlicensed alcohol and gambling machines, outcome not established.
- Pre-2001 Regulation 53 appeals. The instructive one is **American Legion Post
  0046, Bellevue (1995)**: a **180-day suspension** upheld, where **"payoff
  records"** for tip tickets and machines were themselves among the charged
  violations ([CourtListener](https://www.courtlistener.com/opinion/3986859/american-legion-post-0046-bellevue-v-ohio-liquor-control-commission/)).

**No case blamed software or a POS.** Every failure cited was a human control.

### 4.4 Mapping the failures to SAIRNfreedom

| What the cases show | SAIRNfreedom at `origin/main` | Gap |
|---|---|---|
| **Distribution shortfall against the contracted charity is the AG's lead issue** (Legion 243, FOE 316, Flushing) | **Built:** `tieredRequirement()` plus `shortfall = required − distributedTiered` | **On the right side.** Two things undermine it: the panel copy says Phase 4 is "not built" (§1.4), and the threshold default may be stale and held on the device only (§1.3) |
| **Application figures must reconcile to the ledger** (FOE 316: a material misrepresentation) | Not checked in this pass | Any figure the app pre-fills for an application should be traceable to ledger rows and locked once filed. **Candidate; not verified whether the app pre-fills applications** |
| **Missing quarterly electronic instant bingo reports** (AMVETS 24, Legion 52, 178, 366) | **Built:** due-date flag and an overdue block ("…quarterly report overdue by N days") | On the right side. Missing: the rule cite (OAC 109:1-5-14), a record of the *filed* status, and re-verification of the four dates |
| **Hours proved by time stamps** (Circleville: 279 violations) | **Built:** the §2915.09(C)(6) blackout and §2915.01(S) window checks | On the right side. It guards **booking**; whether it also flags **recorded** electronic instant bingo play outside hours was not checked |
| **Dual signatures bypassed** (FOE 213); **false purposes on charitable checks** (VFW 4044) | `two signatures|countersign` × 0. Disbursements are tagged to per-organisation-type purpose lists (§2915.01(V)(2)/(3)), a real control on *purpose* | **Gap:** no second-approver step on disbursements from the bingo account. The purpose tag stops the wrong *category*, not a false *memo* |
| **Unreconciled transfers and card use** (AMVETS 24: $622K) | Reconciliation × 14; the nightly canteen close-out exists | Not established whether transfers *between* the bingo and general accounts are logged and flagged. **§2915.10(C) makes any transfer out of the bingo account an exception that should always surface** |
| **Trustee audit by someone other than the quartermaster** (VFW Manual of Procedure: quarterly, trustees individually liable, the quartermaster must not prepare it, and a missed audit can void the bond) | Trustees are mentioned for the liquor inventory; `bond` × 2 | **Gap:** no trustee-audit packet with a separation-of-duties check (refuse the quartermaster as signer) and no bond-coverage check |
| **Gambling payoffs recorded in the bar's books are evidence** (Bellevue) | Canteen and bingo money are separated by design (§2915.10(C)) | **On the right side.** Keep payouts out of the canteen ledger entirely |

---

## 5. Adjacent industry: dues and canteen POS

### 5.1 No national body gives up control of dues, and none publishes an API

| Organisation | Who collects | National system | What the post controls | Source [SNIPPET] |
|---|---|---|---|---|
| **VFW** | The post sets its dues and remits "only the National and Department portion"; **members can also renew themselves through OMS "Quick Renew"**, going around the post | **OMS** (inside My VFW); dues year July–June | Its own ledger, reconciled against the OMS "Post Query" roster | [Transmittal form](https://www.vfw.org/-/media/VFWSite/Files/MY_VFW/Training-and-Support/Member-and-Officer-Training/Post-Quartermaster-Transmittal-Summary-Form.pdf); [OMS Quick Renew](https://oms.vfw.org/quickrenew.aspx) |
| **American Legion** | Post, then department, then national. **National per-capita went from $18.50 to $23.50 from 2024-07-01** (2025 membership year). **Three-year memberships are national-only**; online renewal and auto-renew exist | **MyLegion.org** (on Personify eBusiness) | Records its own dues rate in MyLegion; card handling after an online renewal is manual | [legion.org 2023-11](https://www.legion.org/information-center/news/dispatch/2023/november/national-dues-adjustment-for-2025-membership-year) |
| **Elks** | **Grand Lodge per-capita and state fees "are not adjustable"**; year-end dues processing is automatic, and corrections need a ticket | **CLMS2** (web plus a Windows desktop client) | Dues statements; an optional Grand Secretary billing program | [CLMS dues PDF](https://www.elks.org/sharedelksorg/clms2/files/MaintainingCLMSDues.pdf) |
| **Moose** | **Members pay Moose International directly**; MI "electronically remits half of received fees to the Lodge" (dues or enrolment fees? unclear) | **LCL Web**, plus the member app with QR cards. **QuickBooks Online was "selected by Moose International" for lodges, with a preset chart of accounts** | Books the MI share as a liability (acct 2515) and its own as income (acct 4005) | [MI dues](https://www.mooseintl.org/dues-payments-2/); [LCL Web QBO](https://www.mooseintl.org/lcl-web-quickbook-online-tips/) |

**Ohio Legion figures conflict:**
- a 2024-02-06 department letter says post dues must be at least **$32.50**;
- Resolution 23-07 sets the department per-capita at **$14 for 2026**.

These do not reconcile under one year's rates.

**What it means for SAIRNfreedom.** The app already models **per-capita as a
pass-through liability** and states "A dues waiver never waives the national
per-capita" (~L415, L467, L5657). **That is right for all four organisations.**

**What it cannot do is be the membership system of record:**
- No national system exposes a third-party API in anything found.
- Moose and Elks bill centrally.
- VFW and Legion members can renew around the post.

**The durable job is reconciliation.** The app should track what the post
collected and what it owes upward, check that against a roster *imported* from
the national system, and prepare re-keying.

**For Moose lodges specifically,** the accounting must **export to Moose
International's preset QuickBooks Online chart**, not replace it.

### 5.2 Member standing at the bar is becoming free, and SAIRNfreedom's opening is recording it

The national bodies now issue **free digital cards showing live standing**:
- **Elks:** Resolution 2025-04 requires lodges to accept electronic cards, and
  validity is "checked each time you click on the icon"
  ([Elks](https://www.discoverelks.org/card)).
- **Legion:** membership app with current status (October 2024).
- **Moose:** app and QR card.
- **VFW:** wallet pass.
- **Moose lodge rules require the card "before making a purchase each day"**,
  and a member in arrears "may not enter any lodge, even as a guest"
  ([Moose rules](https://www.mooseintl.org/wp-content/uploads/2021/05/Lodge-Rules-and-Regulations.pdf)).

**So a plain "is this person current" check at the door is commoditising.** What
no one showed was **recording the standing check against each D-4 sale**, which
is what ORC 4303.17's "members only" condition would have an auditor ask for.

SAIRNfreedom's `duesCurrent()` gate on canteen sales does exactly that, from the
post's own ledger. **It does not read the national standing.** A member who
renewed nationally but not at the post reads "not current". A post-side
"renewed nationally" waiver, or a roster import, closes that.

### 5.3 POS prices: the band SAIRNfreedom has to sit in

| POS | Software | Club-relevant | Source |
|---|---|---|---|
| Tab King | $49 / $79 / $129 per user per month (**third-party, low confidence**) | Pull-tabs, "complete state reports", dues tracking, QuickBooks, rewards; built for posts | itqlick; [tabkingusa.com](https://www.tabkingusa.com/clubs-and-veterans-organizations) |
| Square for Restaurants | Plus $49 per location per month; 2.5% + 15¢ | House accounts; membership only via the third-party Submatic | aggregators 2026 |
| Toast | Starter $0 (3.09–3.69% + 15¢); POS plan $69/mo; hardware $449–1,024 | ID scan via WE SCAN ID | aggregators 2026 |
| Clover | Counter $59.95; Table $84.95 or $89.95 (conflict); hardware $49–1,899 | ID prompt only; scanning needs an add-on app | aggregators 2026 |

**None of the mainstream POS showed any bar-versus-gaming fund separation.**
Ohio requires it (§2915.10(C)), and it is SAIRNfreedom's by design.

**At the top of the market,** private-club suites (Jonas, Clubessential) are
quote-only, estimated at "$10,000–$50,000+ annually" (third-party). They are the
wrong price band for posts.

**Accounting alternatives:**
- MoneyMinder: $299 a year.
- QuickBooks via TechSoup: $80–170 a year, **but the snippet says 501(c)(3)
  only**. Posts are commonly 501(c)(19) or other 501(c) types, so eligibility is
  not established.

---

## 6. Practitioner voice

**This is the thinnest lens.** No first-hand post-officer thread surfaced from
Reddit, and Facebook group content was visible as titles only. What exists:
- generic small-association reviews (Wild Apricot, MemberClicks, ClubExpress,
  GrowthZone, MoneyMinder);
- national and department acknowledgements (Legion, VFW).

Quotation marks mean the result presented the words as the reviewer's or
source's own.

### 6.1 Records are kept in spreadsheets, and the department says so

The **VFW Department of South Carolina Quartermaster Training Guide (2024–25 and
2025–26)** says:
- quartermasters can track accounts in Excel;
- some posts use Google Sheets;
- "some Posts have found success with QuickBooks".

([VFW SC guide](https://vfwsc.org/uploads/documents/Quartermaster/2025-2026VFWSCQuartermasterTrainingGuide.pdf))

**It also recommends one Gmail account "passed from one Quartermaster to the
next using the same account name and logins to all things financial".** That is
a department-endorsed **shared-credential handoff**. The bar for SAIRNfreedom's
per-officer accounts is therefore "easier than changing the password".

### 6.2 Trustee audits are quarterly and fixed

VFW trustees must audit the quartermaster's, adjutant's, clubroom's, bar's and
bingo's books by **Apr 30, Jul 31, Oct 31 and Jan 31**
([VFW Post Inspection form](https://www.vfw.org/-/media/VFWSite/Files/MY_VFW/Training-and-Support/Member-and-Officer-Training/Post-Inspection-Form-and-Instructions.pdf)).
This ties to the §4.4 gap.

### 6.3 Friction at the national handoff is documented, but dated

**The Legion's April 2021 MyLegion rollout** is documented by national and
department sources themselves:
- renewals did not carry over;
- users were locked out of "myGroups";
- reports went missing;
- transfers produced duplicate lines on transmittals.

Sources: [Florida Legion](https://www.floridalegion.org/membership/membership-notifications/new-mylegion-org-issues/);
[legion.org 2021-05](https://www.legion.org/information-center/news/membership/2021/may/how-to-training-on-mylegionorg-gives-answers).

After an online renewal, the member must tell the post, and the card stays at
the post. **Whether this friction persists in 2026 was not established.**

### 6.4 Tools and ratings

| Product | Shown in snippets | Signal |
|---|---|---|
| Wild Apricot | Capterra 4.5 (513+, incentive campaigns); G2 3.9 (41); **Trustpilot 1.6** (147–159) | Declined after Personify; price rises; chat-only support |
| MemberClicks | Capterra 4.3 (469) | Mixed: a sharp price rise and slow support in some years; improved support in others |
| GrowthZone | Capterra 4.4 (276) | "world-class support"; cluttered interface |
| ClubExpress | Capterra 4.0 | "a little klugey to use"; bugs; **vendor-hosted review page** |
| MoneyMinder | Capterra 4.9 (120) | Treasurer-friendly: no "degree in accounting" needed |
| M.A.P.S., Tab King, CLMS2, LCL Web, MyLegion | No independent reviews found | Vendor or national documentation only |

**No practitioner evidence of hall-rental double-booking pain was found.** Posts
use a contract-plus-deposit policy. A vertical competitor exists: **Check
Cherry**, which offers club and lodge hall-rental CRM with contracts, deposits
and calendar sync ([Check Cherry](https://www.checkcherry.com/club-lodge-crm)).
**Do not pitch double-booking as a known pain without first-hand evidence.**

---

## 7. Synthesis

### 7.1 Ordered by consequence to a post

1. **Stale "Phase 4 not built" copy (§1.4), and a threshold default that may be
   stale and held on the device only (§1.3).**
   - The distribution-shortfall test is what the AG enforces most (§4.1).
   - SAIRNfreedom has built it and then tells the user it has not.
   - The copy fix is one line.
   - The threshold needs a primary check (possibly $330,000) and a decision on
     server-side storage.
2. **Separation of duties on bingo money (§4.4).** Add a second approver for
   disbursements from the bingo account, a flag on every transfer out of it,
   and a trustee-audit packet that refuses the quartermaster as signer. Every
   Ohio theft case in §4.2 is one of these.
3. **SB 197 (§1.2).** If enacted, the regulator changes on 2027-01-01. Check its
   status before the app's "Ohio AG" copy and deadlines are relied on into 2027.
4. **Copy corrections (§1.1):**
   - "sale must be for cash" should say credit terms are banned, not
     non-currency payment;
   - -46 should be -45;
   - "4303.17(A)(1)" should be verified;
   - whether 4301.99(C) covers false statements should be verified.
5. **Reconciliation against the national roster (§5.1–5.2).**
   - A roster import and a "renewed nationally" basis for `duesCurrent()`, so a
     national renewal does not block a member at the bar.
   - A Moose QuickBooks Online chart export.
6. **HB 96 online raffles (§1.2)** are unmodelled. Whether raffles are in scope
   is a product decision.
7. **The OAC 4301:1-1 five-year review (§3).** Paragraph-level citations are
   most likely to go stale during 2026–27. Re-read them when the review closes.

### 7.2 Where SAIRNfreedom is on the right side, and should say so

- **No substantive mismatch in any refusing gate** across roughly 19 statutory
  claims (§1.1).
- **Separate distribution lists for the (V)(2) and (V)(3) limbs**, a subtlety a
  bolt-on competitor would likely miss.
- **Per-capita modelled as a pass-through liability** that a waiver cannot
  waive, which is correct for all four national bodies.
- **Bar and bingo money separated by design**, which no mainstream POS shows.
- **A distribution-shortfall computation**, which answers the AG's most common
  2025–2026 action.
- **Every unresolved legal point disclosed rather than guessed:** guests, D-5
  hours, officer re-certification.

---

## 8. What this document does not establish or decide

- **No page was opened.** Every external claim is [SNIPPET] (§0.1). Where this
  pass disagrees with the 2026-08-30 primary reads or with the app, the
  disagreement is not yet authoritative.
- **Internal findings (§1.3, §1.4, §4.4) are code reads at `origin/main`, not
  runs.** In particular:
  - whether the electronic instant bingo hours check covers *recorded* play;
  - whether the app pre-fills licence applications;
  - whether transfers between accounts are flagged.

  All three were not checked.
- **Unresolved conflicts, kept as found:**
  - Circleville $10K vs $15K;
  - Wild Apricot's 500-contact price;
  - ClubExpress's minimum;
  - Ohio Legion $32.50 vs $14 + $23.50;
  - F-2 hours;
  - F-2 joint fee $150 vs $160;
  - Clover Table price;
  - the MemberClicks acquisition date;
  - MIP Accounting ownership.
- **Not established:**
  - SB 197 enactment;
  - the current 2915.101 indexed threshold and the rule that sets it;
  - Type III licence fee;
  - D-4 guest rules (still → counsel, per the 2026-08-30 doc);
  - 4301.22 supervision conditions;
  - any national-organisation API;
  - Tab King's live-versus-local standing check and its fund handling;
  - current VFW national dues;
  - TechSoup eligibility for 501(c)(19) posts.
- **No legal advice, no pricing decision, and no code change.** The only write
  outside `docs/cloud-research/` is this session's own `.claude/claims/cloud.json`,
  which the user asked for.

## 9. Decay, and what to re-read first

This pass is dated by four things:
- HB 96 (effective 2025-09-30);
- the Momentive–Personify close (2026-01-06);
- the Wild Apricot April 2026 increase;
- the in-progress LCC five-year review.

### 9.1 Open first for this document, once the network allows

1. **legislature.ohio.gov, SB 197 status.** Decides §1.2 item 2.
2. **codes.ohio.gov 2915.101 and OAC 109:1-4-21, plus the AG distribution
   form.** The current threshold (§1.3).
3. **codes.ohio.gov 4303.17** (is there an (A)(1)?), **4301.99** (does (C) cover
   false statements?), **OAC 4301:1-1-43, -45, -46** and **OAC 4301-9-01** (the
   cash wording).
4. **OAC 109:1-5-14.** The four quarterly electronic instant bingo due dates the
   app hard-codes.
5. **The AG enforcement PDFs in §4.1.** Outcomes and exact amounts.
6. **The Tab King and ClubExpress feature pages.** The competitive claims in
   §2.4 and §2.2.

### 9.2 Carried from earlier documents in this session: pending re-verification, not skipped

**`sairnsenior-external-competitive-gap-audit-2026-09-26.md` §9:**
- CMS HHCS and PCS EVV compliance tables;
- PA MA Bulletin 05-25-03;
- HHS-OIG A-07-24-03260;
- Ohio SB 315 as enrolled, and ODM's alternate-vendor pause;
- the CO, CT and PA Sandata alternate-vendor pages;
- Virginia DMAS FFS EVV-in-837;
- Alora's pricing page.

**`sairnbiz-external-competitive-gap-audit-2026-09-26.md`:**
- 213 snippet-grade markers across seven lenses. Its "What this document does
  not establish or decide" and "Decay" sections are the re-fetch list. It
  was written by an earlier session, and that list was not re-read for this
  pass.

**`sairncash-external-competitive-gap-audit-2026-09-26.md` §9:**
- IRS Pub 505 (2026) and §6654(d);
- Rev. Proc. 2025-32 HOH/MFS;
- Form 2210 Schedule AI;
- Notice 2025-62;
- Found and Lili help pages;
- a Plaid quote.

## Sources

Every source is linked inline where it is used. All were retrieved on 2026-09-27
and all are [SNIPPET] (§0.1).

Internal sources, read at `origin/main` `9752c1d1`:
- `sairnfreedom.html`
- `api/_resources/sairnfreedom.js`
- `docs/2026-08-30-sairnfreedom-competitive-and-patent-scan.md`
- `docs/2026-08-30-sairnfreedom-ohio-liquor-permits.md`
- `docs/2026-08-30-sairnfreedom-four-research-items.md`
- `docs/superpowers/specs/2026-08-30-sairnfreedom-research.md`
