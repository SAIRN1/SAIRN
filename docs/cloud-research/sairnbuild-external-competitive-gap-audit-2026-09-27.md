# SAIRNbuild external competitive-gap audit (2026-09-27)

This audit covers five areas: competitors, Ohio law, liability, payments and billing, and what practitioners say.

- **Competitors:** Buildertrend, CoConstruct, JobTread, Houzz Pro, Procore, Knowify, Contractor Foreman, Buildxact, Builder Prime and Fieldwire.
- **Ohio regulation:** lien law (ORC 1311), the home-construction contract statute (ORC 4722), prompt pay and retainage, licensing, the EPA lead-paint renovation rule (RRP), and OSHA.
- **Accuracy and liability:** EPA, OSHA, lien and Attorney General cases.
- **Adjacent industry:** owner payments, AIA billing, lien waivers, accounting sync, and what sureties expect from a work-in-progress (WIP) schedule.
- **Practitioner voice.**

**Research pass, dated 2026-09-27, in the isolated cloud-research lane.** It is docs only. It lands on the PR SAIRN1/SAIRN#18 branch, not on `main`.

**Claimed before starting** as session `cloud`, commit `741dd426` on `origin/main`, subject `sairnbuild`. `check` returned CLEAR.

**Internal code findings are in §1.2, apart from everything else, and they are written up for the owning build session.** This pass fixed none of them. §1.2 marks the ones already tracked in `docs/SAIRN-OPEN-WORK-INDEX.md` so they are not raised twice.

---

## 0. Read this before quoting anything

### 0.1 Network and evidence grade

**Page fetches are still blocked.**
- At 03:40 UTC on 2026-09-27, `example.com` was refused with `connect_rejected` (gateway 403).
- Each of the five research lenses tried one fetch before starting. `buildertrend.com`, `codes.ohio.gov`, `epa.gov`, `procore.com` and `capterra.com` all returned `EGRESS_BLOCKED`.
- The diagnosis is unchanged from the SAIRNcash doc §0.1: the environment's standing egress policy blocks them. **The broader access approved earlier had not taken effect by this pass.**

**Every external claim below is therefore graded [SNIPPET]:** it is the search tool's model-written summary of a result page, not the page itself. Quotation marks show the snippet's own rendering, not the page's verified wording. §9 lists what to open first.

**Budget used:** 191 WebSearch calls across five lenses, plus 5 blocked WebFetch probes.
- Four lenses stayed within their 38-call caps (38, 37, 36, 38).
- **The regulatory lens made 42 calls, 4 over its cap.** It disclosed the overrun itself. The overrun is recorded here, not rounded away.

### 0.2 Corrections to premises, including this pass's own brief

1. **The Ohio home-construction statute, the Home Construction Service Suppliers Act (HCSSA, ORC 4722), dates from 2012. It was extended to remodeling in 2024.**
   - It first took effect on 2012-08-31.
   - **HB 50 (135th General Assembly)** extended it to "repair, improvement, remodel, or renovation" and took effect on **2024-09-19 or 2024-09-20**. Secondary sources disagree by a day.
   - This pass's regulatory brief said "effective 2020". That was wrong.
   - [SNIPPET: [KJK 2024-11-14](https://kjk.com/2024/11/14/changes-to-ohios-home-construction-law/); [Taft](https://www.taftlaw.com/news-events/law-bulletins/hb-383-cspa-revisions-a-new-home-for-consumer-remedies-for-home-construction-services/)]
2. **"Lowe's 2021" RRP settlement: there is none.** This pass's liability brief named one.
   - Lowe's had a **2014** consent decree.
   - A **$12.5M** settlement was announced around December 2025. It covers more than 250 jobs from 2019–2021 and was found in Lowe's own compliance reports under the 2014 decree (§4.1).
3. **"Online payments" are not a SAIRNbuild feature.**
   - `Stripe` appears 3 times in `sairnbuild.html`: two platform-billing comments and one demo row reading "Stripe … not_connected".
   - There is no path for a homeowner to pay (§1.1).
   - This corrects no stated claim. It is recorded because the competitive lens treats portal payments as the table stakes (§2.2).

---

## 1. Internal grounding

This section was measured before any searching, from `sairnbuild.html` at `origin/main` `3adf4ebd` (the file was last changed in `c0ae9a0a`; it is 583,123 bytes). All counts come from grep and are floors. The functions named were read, not run.

### 1.1 Where the 2026-09-03 audit's rows stand now

Source: `docs/superpowers/specs/2026-09-03-competitive-gap-audit-build-vet-biz-grounds-cash.md` §3.

| Row | Then | At `3adf4ebd` | Evidence |
|---|---|---|---|
| A1 AI scope-gap detection with page citations | Absent | **Absent** | unchanged |
| A2 BIM / open IFC | Absent | **Absent** | `IFC\|BIM\|web-ifc` × 0 |
| A3 Spanish / bilingual | Absent | **Absent** | × 0 |
| A4 Offline-first | Absent | **Partly addressed, but offline-unaware** | The `bld_sync_pending` merge exists "so an offline device does not lose rows the server has not seen". There is still no offline state shown to the user (`offline` × 2, both in comments) |
| B1 AIA G702/G703 | Partial | **Unchanged** | `G702\|G703\|AIA` × 0. Draws, retainage and WIP are built |
| B2 Retainage release | Built 2026-09-15 | **Built. Its SQL was run on 2026-09-21** per the open-work index ("SAIRNcare MAR recording and SAIRNbuild retainage release … CLEARED, the SQL has been run") | One open defect is already tracked; see §1.2 |
| B3 Cost-to-complete forecasting | Absent | **Absent**, and there is a correctness problem underneath it; see §1.2 I-1 | `forecast\|cost.to.complete\|EAC` × 0 |
| B4 Multi-entity | Absent | **Absent** | × 0 |
| B5 Certified / prevailing wage | Absent | **Absent** | × 0 |
| B6 GL sync | Absent | **Absent.** QuickBooks appears only as a row in a demo integrations list; see §1.2 I-2 | `general ledger\|/api/ledger` × 0 |

**Built since, or not examined in the 09-03 pass:**
- lien waivers (`lien waiver` etc. × 22);
- submittals (× 61);
- RFIs (× 24);
- daily logs (× 21);
- punch list (× 75);
- safety and toolbox talks (`safety\|OSHA\|toolbox talk` × 72);
- selections and allowances (× 42);
- warranty (× 42);
- subcontractor compliance, gated server-side at award (`COI\|W-9\|1099` × 48; see the 09-15 re-derivation);
- a "Client Portal" panel;
- a CSV export (`csv(type)`).

### 1.2 Internal findings for the owning build session (not fixed here)

> Every item is a read of `origin/main`, not a run. "Owner" means whichever
> build session next holds a claim on `sairnbuild.html`. **None of this was
> changed.**

**I-1: The WIP schedule's percent-complete has the wrong denominator. The error is in what the numbers say, not only in what is missing.**
- `jobWIP()` (~L7434) computes `pct = min(1, actualFor(job) / budgetFor(job))`. It then computes `earned = pct × revisedValue(job)`.
- `budgetFor()` (~L3555) sums the **original cost-line budgets**.
- `revisedValue()` (~L3562) is the contract value **plus accepted change orders**.

Three consequences follow:
- **(a) Change orders inflate revenue but not the cost base.** An accepted change order raises `revised` and leaves `estTotal` alone, so any cost spent on change-order work pushes `pct` up as if the base scope were further along.
- **(b) The `min(1, …)` clamp hides cost overruns.** A job 20% over budget reads **100% complete** and **fully earned** while it is still running. The over/under-billing column then shows it as under-billed or even. The fade in profit that a surety reads a WIP schedule to find (§5.5) is therefore invisible.
- **(c) There is no re-forecast field.** Buildertrend ("Projected Costs") and JobTread ("Estimated final cost") both have one (§5.5).

The 09-03 audit filed B3 as "forecasting absent". **This goes further: the existing figure is a misstatement whenever cost runs over budget or a change order adds scope.** That is the fabricated-KPI class, where a number is shown with nothing real behind its meaning. **Suggested first step for the owner:** a regression test with one over-budget job and one change-order job, before any fix.

**I-2: Demo data is seeded for every licence type, including a false "QuickBooks: connected".**
- `bldEnterApp()` (~L2934) calls `init()` on every sign-in. `init()` calls `seed()`.
- `seed()` checks **only** the `bld_seeded` flag. It does not check whether the key is a `DEMO-` licence (`VALID=['BLD-','DEMO-','SAIRN-']`).
- So the first sign-in of a paying `BLD-` customer on each new device loads the "Pinnacle Industries LLC" demo into the customer's app. That demo includes:
  - jobs, costs and change orders;
  - **`bld_integrations`, with QuickBooks Online and DocuSign marked `status:'connected'`**.
- The rows are not pushed during seeding, because `bldSeeding` suppresses the push. **Whether a demo row the customer later edits gets pushed to their server backup was not checked.** If `st()` pushes changed rows, it would be.
- The toast "Demo data loaded - Pinnacle Industries LLC" is the only disclosure. No "clear demo data" path was found.
- The "connected" status is the part that matters most. **It tells a paying customer that an integration exists when none does** (B6 above; the payments lens flagged the same risk from outside).

**I-3: The "Client Portal" is described as shared, but it has no way to share.**
- The panel's subtitle is "Shared view for the homeowner — status, photos, approved changes, selections, and messages".
- `rClientPortal()` renders inside the signed-in app. It carefully leaves out cost, margin and internal notes.
- **No share link, token or homeowner login was found** (`portal_link\|share link\|shareable` × 0). Compare SAIRNsenior's scoped portal links, which can be revoked (`sen_portal_links`).
- As built, the homeowner can only see it on the contractor's screen. Competitors give homeowners a login or a link, usually free and unlimited (JobTread; §2).
- **Owner decision:** either build the share path, or change the subtitle to what the panel is: a "homeowner-safe view".

**I-4: Some compliance-relevant configuration is kept on the device only. This is documented.**
- `bld_settings` holds `default_retainage_pct: 10`, `default_markup_pct: 18` and `cost_codes`.
- `bld_company_profile` and `bld_integrations` are also kept locally.
- All three are **deliberately excluded** from the server backup (`api/_resources/sairnbuild.js` L118–119: "app configuration, not a business record").
- The default retainage percentage pre-fills every new draw. Cost codes are what QuickBooks mapping would key on (§5.4).
- This is the same design choice as SAIRNfreedom's `sf_phase4_config`, and the same argument applies. **A setting that decides a contractual figure is not like a rate card.** It is recorded as a decision to revisit, not as a defect.

**Already tracked, so not raised again** (see the SAIRNbuild rows in `docs/SAIRN-OPEN-WORK-INDEX.md`):
- **There is no three-way match between POs, deliveries and checks.** Found 2026-09-23 (Hank).
- **`release_retainage` records a re-release of the same total as a new release.** Found 2026-09-21 (Cody).

---

## 2. Competitive / market lens

All figures are [SNIPPET]. Vendor claims are marked **VSC**. Prices conflict between sources, and every conflict is listed.

### 2.1 The field

| Product | Segment | 2026 price (as reported) | Ownership / capital, 2023–26 | Notable |
|---|---|---|---|---|
| **Buildertrend** | Residential builders and remodelers; the incumbent | **Quote-only**, reportedly across "11 annual construction volume brackets" (Projul, a competitor, Apr 2026). Aggregators list $339 / $499 / $829 per month on annual plans, or $499 / $799 / $1,099 month-to-month. Onboarding $400–1,500 | Bain Capital Tech Opportunities and HGGC (Dec 2020). Acquired **CoConstruct**. Acquired **BizJet AI** (late July 2026) | AI Client Updates ("97% faster", VSC). **AI Bill Pay** (IBS, Feb 2026). "Bailey" chatbot (Feb 2026) |
| **CoConstruct** | Owned by Buildertrend; being wound down | — | — | Per Buildertrend's migration page: new projects allowed **through 2027-03-31**; migration must **begin by 2027-06-30**; then a read-only archive. One source says files, photos and proposals do **not** transfer. A competitor says "no public sunset date" (conflict) |
| **JobTread** | Residential and remodel, small to mid | $199/mo first user plus $20 per extra user; $159 + $18 billed annually. **Customer, vendor and sub users are free and unlimited** | Unfunded (Tracxn) | 5,000 customers (Feb 2025) → 7,500+ (Aug 2025) (VSC). AIA-style pay apps. Two-way QuickBooks Online sync. "AI connector" |
| **Houzz Pro** | Remodel, design-build, designers | Conflicting: Starter about $55; Essential $99–149; Pro $159–249, **or** a top "Ultimate" tier at $250–400 | Private; about $1.2B raised | Houzz AI takeoffs and estimates ("2.5x faster", VSC). Client dashboard with payments. **Class action *Carr v. Houzz*, 3:25-cv-503, alleging illegal auto-renewal (an allegation)** |
| **Procore** | Commercial; says it fits "$20M+ residential" | Priced per product by **annual construction volume**; about $15–30K/yr at $10–50M (third party) | Public (PCOR). Acquired **Datagrid** (Jan 2026). New CEO Ajei Gopal | Q2 2026 revenue $375M (+15.8%). Agent Builder. **The only product in this set with lien-notice deadline tooling (via Levelset)** |
| **Knowify** | Small to mid contractors, commercial-leaning | Core $99/mo (includes AIA invoicing). Advanced $249 **or** $329 (conflict) | $8.45M raised; last round July 2023 | **Official G702/G703 through an AIA Contract Documents partnership.** WIP. **Prevailing-wage / certified-payroll add-on** |
| **Contractor Foreman** | Cost-sensitive small GCs | $49 / $105 / $166 / $221 / $332 per month (annual) | — | **Spanish (set per user), 700+ bilingual safety topics, offline mode**, client portal |
| **Buildxact** | Small residential; estimating-led | Go free; Foundation $169–199; Pro $339–399; Master $509–599 | About $27M raised; merged with Goodwork around 2023 | Blu AI (June 2025). Reported price rise from **$49 to $169** in 2026 ("backlash", third party, unverified) |
| **Builder Prime** | Home-improvement CRM and sales | Conflicting: a $79 / $159 / $239 tier model **or** a per-seat model | **Series B, Blueprint Equity, 2025-09-24** | "500+ contractors" (VSC) |
| **Fieldwire (Hilti)** | Field execution; not homeowner-facing | $0 / $39 / $64 / $89 per user (annual) | Hilti | Field Intelligence AI (photo tagging, 2025-10-14). **Offline; about 21 languages including Spanish** |

Sources:
- **Buildertrend:** [payments](https://buildertrend.com/financial-tools/payments/); [BizJet AI, Silicon Prairie News 2026-08](https://siliconprairienews.com/2026/08/buildertrend-furthers-its-ai-ambitions-with-the-acquisition-of-early-stage-startup-bizjet-ai/)
- **CoConstruct:** [migration](https://www.coconstruct.com/migration)
- **JobTread:** [pricing](https://www.jobtread.com/pricing); [7,500 customers](https://www.jobtread.com/news/jobtread-surpasses-7500-customers-achieving-2025-goal-four-months-early)
- **Houzz:** [class action](https://www.classaction.org/news/class-action-lawsuit-claims-houzz-illegally-renews-customer-subscriptions-automatically)
- **Procore:** [Q2 2026 results](https://www.businesswire.com/news/home/20260729106137/en/Procore-Announces-Second-Quarter-2026-Financial-Results)
- **Knowify:** [AIA billing](https://knowify.com/aia-billing/)
- **Contractor Foreman:** [features](https://contractorforeman.com/features/)
- **Buildxact:** [pricing](https://www.buildxact.com/us/pricing/)
- **Builder Prime:** [Series B](https://natlawreview.com/press-releases/builder-prime-secures-series-b-funding-accelerate-growth-and-innovation-home)
- **Fieldwire:** [offline](https://help.fieldwire.com/hc/en-us/articles/202631944-Q-A-Can-I-use-Fieldwire-while-offline)

### 2.2 What the competitive lens changes

1. **Homeowner payment inside the portal is expected in this market.** Buildertrend, JobTread, Houzz Pro and Builder Prime all take ACH and card payments through it. SAIRNbuild has neither the payment nor a portal the homeowner can reach (I-3).
2. **The realistic price band is about $50–$1,100 a month, and Procore sits outside it.** For an owner-operator with 4–12 jobs, the comparison is **JobTread and Buildertrend**, with Contractor Foreman at the low end.
3. **The CoConstruct wind-down creates a switching window with dates attached:** new projects end 2027-03-31, and migration must start by 2027-06-30. JobTread is already marketing to these users. A CoConstruct import plus local outreach fits the window. **Check the dates against Buildertrend's own notice** (§9).
4. **AIA billing is cheap at the low end,** from $99 at Knowify, and JobTread includes AIA-style billing. **Lien-notice deadlines are almost unserved** below Procore/Levelset. That is the one compliance feature where SAIRNbuild could lead instead of catch up (§3.1).
5. **Every competitor shipped AI in 2025–26.** To stand out, SAIRNbuild's AI needs a specific job to do. Homeowner update drafting is the one Buildertrend markets hardest.

---

## 3. Regulatory lens: Ohio and federal

Every row is [SNIPPET] and **not legal advice**. **STAT** means statute, **REG** means regulation, **SEC** means a secondary source.

### 3.1 Mechanic's liens, ORC Chapter 1311

| Rule | Citation | Summary | Source |
|---|---|---|---|
| Notice of Commencement | 1311.04 | **The owner records it** with the county recorder before work begins | STAT; [1311.04](https://codes.ohio.gov/ohio-revised-code/section-1311.04) |
| Notice of Furnishing | 1311.05 | Subs and suppliers must serve it within **21 days** of first furnishing. Late service keeps rights only for the preceding 21 days. **Carve-outs exist for 1–2 family dwellings.** | STAT; [1311.05](https://codes.ohio.gov/ohio-revised-code/section-1311.05) |
| Lien affidavit | 1311.06 | **60 days for residential; 75 days for other projects.** ⚠ **The two lenses disagree on when the residential clock starts.** One quotes "first furnished"; the other says "last", and adds that punch-list work counts but warranty work does not. **Do not compute a residential lien deadline until the primary text is read.** | STAT; [1311.06](https://codes.ohio.gov/ohio-revised-code/section-1311.06) |
| Service on the owner | 1311.07 | Within 30 days of filing | STAT |
| Notice to commence suit | 1311.11 | The lien is void if suit is not filed within 60 days of this notice | STAT |
| Paid-in-full defense | 1311.011 | Protects the owner of a home construction contract who paid the original contractor in full before receiving the affidavit | STAT |
| Lender affidavit | 1311.04 | A lender may not pay the original contractor until that contractor swears subs and suppliers have been paid | STAT (subsection not confirmed) |
| Waiver form | — | **Ohio has no statutory lien-waiver form**, so custom wording is allowed | SEC, consistent across sources |
| 2024–26 amendments | — | None found | — |

**SAIRNbuild has none of this** (`notice of commencement\|notice of furnishing\|1311` × 0). §2.2 item 4 explains why this is the opening.

### 3.2 Home construction contracts: HCSSA, the Consumer Sales Practices Act (CSPA), and cancellation rights

| Rule | Citation | Summary |
|---|---|---|
| Scope | 4722.01(B), as amended by HB 50 | Now covers "repair, improvement, remodel, or renovation of an existing structure" |
| **Written contract of $25,000 or more** | 4722.03 | Must include: supplier name, address, phone and **taxpayer ID**; owner and property details; a description of the work; **anticipated start and completion dates**; **total estimated cost** and the costs it excludes; and a **certificate of insurance showing at least $250,000 in general liability** |
| **Excess-cost notice** | 4722.03 | Once unforeseen extra costs pass **$5,000 cumulative**, the owner must get an estimate **before** that work. Cost-plus contracts are exempt |
| **Down payment cap** | 4722.04 | **"not more than ten per cent of the contract price"** before work starts. Up to 75% is allowed for non-returnable special orders. Cost-plus and construction-loan draws are excepted |
| Remedies | 4722.07 | Rescission, or economic damages plus up to $5,000 non-economic. No treble damages |
| Under $25K, or GL below $250K | CSPA, 1345.01/.09 | Treble damages remain available |
| **Three-day cancellation for in-home sales** | 1345.21–.23; 16 CFR 429 | The buyer may cancel until midnight of the third business day. **The contractor may not start work during that period.** Two copies of the notice are required |

**SAIRNbuild has none of these fields or gates.** It has no deposit field (`deposit` × 0), no cost-plus type, and no cancellation-window lock. Its change-order log **does not total excess costs against a $5,000 threshold.** §4.3 shows these are the violations the Ohio Attorney General actually sues over.

### 3.3 Prompt pay and retainage

- **ORC 4113.61:** a GC must pay a sub within **10 days** of the owner paying the GC; late amounts carry **18%** interest. **A secondary source says it does not apply to 1–3 family dwellings.** If that holds, a prompt-pay clock on a residential job would track a law that does not apply to it. **Verify before building.**
- **Private retainage:** there is no statutory cap; the contract governs. **Pending: HB 568 (136th General Assembly)** would add ORC 4113.63, **capping retainage at 5% on private contracts over $1M**. It was not confirmed as enacted.
- **Public retainage** (ORC 153.13 / 153.63):
  - 8% until the job is 50% complete, then 0%;
  - escrow required above $15K;
  - 153.63 has a version dated **2025-09-30**, with unknown changes.
- **Statutory interest for 2026: 7%.**

SAIRNbuild's retainage default is a single percentage, 10%, and it lives on the device (I-4). A per-contract setting already exists on `bld_draws`. **What is missing is a public/private flag and the 50% step-down.**

### 3.4 Licensing

- **OCILB (the Ohio Construction Industry Licensing Board)** licenses only electrical, HVAC, plumbing, hydronics and refrigeration contractors. **There is no state general contractor license.**
- Cities require registration. **Cleveland requires a $25,000 bond**, expiring 31 December.
- **Unverified, and probably wrong:** two vendor sites claim a statewide home-improvement registration from 2026-01-01 "under HB 614". **No ohio.gov page corroborates it**, and it contradicts a 2025 Legislative Service Commission (LSC) statement. **Do not build to it.**

### 3.5 EPA lead renovation rule (RRP): the remodeler's recordkeeping obligation

**EPA runs RRP directly in Ohio.** Ohio is not an authorized state.

The obligations (40 CFR 745 Subpart E):
- **firm certification**, valid for up to 5 years (745.89);
- **the *Renovate Right* pamphlet within 60 days before work, with a written acknowledgment**, or a certificate of mailing at least 7 days before (745.84);
- **records kept 3 years after completion** (745.86).

**The dust-lead reconsideration rule** (89 FR 89416, published 2024-11-12) took effect 2025-01-13, with **compliance from 2026-01-12**. It introduces the terms "dust-lead reportable level" and "dust-lead action level". **How it changes RRP cleaning verification was not established.**

SAIRNbuild has none of this (`RRP\|lead.safe\|pre-1978\|renovate right` × 0). **For a NE Ohio remodeler this is the most enforced federal recordkeeping duty in the trade** (§4.1).

### 3.6 OSHA

- **Fall protection (1926.501)** was the #1 most-cited standard for the **15th straight year** in FY2025, with 5,914 citations. **Fall-protection training (1926.503) was #7.**
- **Silica (1926.1153)** requires a written exposure control plan, reviewed at least once a year.
- **The PPE-fit rule (1926.95(c))** took effect on 2025-01-13.
- **The heat illness rule is still only proposed.** Comments closed 2025-10-30.
- **2026 maximum penalties are unchanged:** $16,550 for a serious violation and $165,514 for willful or repeat. Per an OSHA memo dated 2026-05-21, the inflation adjustment was skipped because of the shutdown.
- **The OSHA 300 log applies to construction employers with more than 10 employees.** Establishments with 20–249 employees must also submit the 300A electronically.

SAIRNbuild has safety records and toolbox talks (× 72), but **no training log tied to 1926.503, no silica plan and no OSHA 300** (`silica` × 0). §4.2 shows why a training log is worth money.

### 3.7 Federal and industry forms

- **Davis-Bacon 2023 rule:** three provisions were vacated and the rest stands. It only matters for federally funded work.
- **AIA G702/G703** are still the **1992** editions and are copyrighted (§5.2).

---

## 4. Accuracy / liability lens

In the tables below, **Status** separates allegations, proposed penalties, settlements and judgments.

### 4.1 EPA RRP: missing records are a violation in themselves

| Date | Party | Amount | What drove it | Status |
|---|---|---|---|---|
| 2020-12-17 | **Home Depot** | **$20.75M**, the largest TSCA penalty ever | Subcontractors were uncertified; the pamphlet was not delivered; **compliance records were not kept**. A company-wide program to verify firms was imposed | Consent decree |
| ~2025-12 | **Lowe's** | **$12.5M** | Violations at more than 250 jobs, **found in Lowe's own reports** under its 2014 decree: no pre-work lead information, and uncertified or untrained workers | Proposed. Court entry not confirmed |
| 2018–2020 | TV renovators: Magnolia, Rehab Addict, Bargain Mansions, Fixer to Fabulous, Maine Cabin Masters, Texas Flip N Move | **$16.5K–$40K each** (Magnolia also had $160K of abatement) | No firm certification; failures in work practices | Settlements |
| 2024-07/08 | **Sciarappa Construction Co., Avon Lake OH** | Amount not visible | EPA Region 5 case, TSCA-05-2024-0017, closed with "payment received" | Consent agreement and final order |

- An **EPA enforcement alert names Ohio franchises** for failing to "retain RRP Rule records". [SNIPPET]
- Sources: [Home Depot](https://www.epa.gov/newsreleases/home-depot-pay-20750000-penalty-nationwide-failure-follow-rules-conducting-renovations); [Lowe's](https://www.epa.gov/newsreleases/lowes-home-centers-pay-125m-penalty-lead-paint-violations-during-home-renovations); [TV renovators](https://www.epa.gov/newsreleases/epa-reaches-settlement-renovators-rehab-addict-and-bargain-mansions-television-shows); [Sciarappa filing](https://yosemite.epa.gov/OA/RHC/EPAAdmin.nsf/Filings/B984528486FFA1FB85258B6A00528221/$File/TSCA-05-2024-0017_CAFO_SciarappaConstructionCompany_AvonLakeOhio_21PGS.pdf)

**Lesson for design (Lowe's): self-reported records are used as evidence.** A form that lets a field be left blank or defaulted produces proof of noncompliance.

### 4.2 OSHA in NE Ohio: training records carry a dollar value

| Date | Party | Proposed penalty | Documentation angle |
|---|---|---|---|
| 2022-02-25 | ILS Construction, Stow OH residential roof | **$237,013** (3 willful); 6th citation since 2018 | **No training** cited alongside no fall protection |
| 2022-10-06 | Charm Builders, OH | **$1,090,231**; placed in the Severe Violator Enforcement Program | **Failure to train on fall hazards** |
| 2023-03-07 | Geis Construction (GC) and J.C. Jones (sub), Cleveland residential, fatal fall | $154,696 and $31,252 | **No documented assessment** of the balcony structure; **the GC and sub were cited together** |

**The July 2025 revision of OSHA's Field Operations Manual** allows reductions of up to 60% for small firms. It ties the good-faith reduction to a **"written and implemented safety and health program"** and to prompt production of documents ([DOL 2025-07-14](https://www.dol.gov/newsroom/releases/osha/osha20250714)). **A training and toolbox-talk log that can be exported during an inspection has a direct dollar value.**

### 4.3 Ohio Attorney General consumer actions against home improvement contractors

| Date | Party | Amount / status | Pattern |
|---|---|---|---|
| 2024-04-30 | Jones / Veritas Home Refinishing (Cuyahoga) | **$556,185.15 restitution + $125,000 penalties; judgment** | CSPA |
| 2025-09-16 | Building with Faith Construction; Ryan Construction & Roofing | $131,792 sought (lawsuits) | Substandard or incomplete work |
| 2026-03 | Acme Restoration; Atlas Exteriors; others | **$564K across 4 suits** | **Large deposits, no work, no right-to-cancel notice** |
| 2026-05 | SNT Roofing & Landscaping (Trumbull, **NE Ohio**) | Lawsuit, plus an earlier theft plea | Down payments, **then stacked add-on agreements** for work never done |

Sources: [AG 2024 annual report](https://www.ohioattorneygeneral.gov/Files/Reports/Consumer-Annual-Reports/2024-Consumer-Protection-Annual-Report_WEB); [AG 2026-03](https://www.ohioattorneygeneral.gov/Media/News-Releases/March-2026/AG-Yost-Sues-Businesses-for-$564K-in-Damages); [AG 2026-05](https://www.ohioattorneygeneral.gov/Media/News-Releases/May-2026/Yost-Sues-Northeast-Ohio-Contractor-Accused-of-Sho).

**Every recurring pattern maps to an HCSSA or HSSA control from §3.2:**
- the 10% deposit cap;
- the three-day lock;
- the $5,000 excess-cost estimate.

### 4.4 Liens and change orders

- ***Nieman v. Tucker*, 2020-Ohio-4704 (6th Dist.)**
  - The contractor filed a lien for a charge the owner never authorized, for **$3,917.05 against an invoice of $3,096.98**.
  - The result was a **treble CSPA judgment of $8,103**.
  - **A lien amount that does not match authorized records becomes consumer-fraud liability** ([Ohio S.Ct.](https://www.supremecourt.ohio.gov/rod/docs/pdf/6/2020/2020-Ohio-4704.pdf)).
- ***Speedy Maintenance v. Windsor Tower*, 2024-Ohio-5841 (2d Dist.)**
  - This was a commercial job on an **oral** contract. The contractor could not prove its terms.
  - **The owner was awarded $44,300.**
- **An 8th District residential case** held that a written-change-order clause was **waived by knowledge and consent**, and commentary says an email or text can serve as the writing. **The case name and date were not established.**
- ***Pursuit Commercial Door* (9th Dist., 2019):** a Notice of Furnishing is valid if served after the Notice of Commencement and within 21 days of first work.

**No case was found where software records were central evidence, or where a software failure caused a dispute.** Buildertrend's terms reportedly disclaim data loss.

---

## 5. Adjacent industry: payments, billing and accounting

### 5.1 Owner payments

| Tool | ACH | Card | Who pays the fee |
|---|---|---|---|
| Buildertrend | 0.5%, $1.99 minimum, $15 maximum | 2.99% + $0.30 + $1.49 platform fee (**conflicting:** 2.95%; Amex 3.95%) | **Conflicting.** Help-center text says the payee pays; marketing says it can be passed to the client in one click |
| JobTread (Stripe) | 1% + $1, capped at $15 | 2.95% + $0.30 | — |
| Houzz Pro | 1% | 3.5% if absorbed, 3.6% if passed on; instant payout +1.5% | Three options |

- **Ohio card surcharging** is reportedly allowed within card-network rules: Visa caps it at 3%, and debit cards cannot be surcharged. These figures come from processor pages, not legal sources.
- **Construction-loan draws are a separate channel from homeowner payments** (Built, Land Gorilla, Rabbet).
- A lender releases money in proportion to the percent complete its inspector verifies. The package is:
  - a schedule of values;
  - **conditional waivers from everyone paid out of the previous draw**;
  - invoices;
  - certificates of insurance.

  **Lenders accept "a pay application (AIA 702/703) or sworn statement"** (Rabbet).
- **SAIRNbuild's draws and lien waivers are most of that package already.** What is missing is the export.

### 5.2 AIA billing: build an "AIA-style" version, not the official form

- **G702/G703 are copyrighted by AIA.** There are two ways vendors provide them:
  - **official forms through a partnership:** GCPay and Knowify;
  - **"AIA-style" look-alikes:** Siteline, PayAppPro and most others.
- **No survey data was found on how many residential jobs use AIA forms.** Guides call it a commercial format.
- **The recommendation for the owner is an AIA-style continuation-sheet export, built from the existing draw, schedule-of-values and retainage data.** Do not use the "AIA" or "G702" names in marketing without legal review; Siteline writes "AIA®-style".

### 5.3 Lien waivers

- **Ohio has no statutory form.** Statutory-form states number **8, 11 or 12**, depending on the source:
  - union of the lists: AZ, CA, FL, GA, MA, MI, MS, MO, NV, TX, UT, WY.
- **What competitors share is making payment depend on the waiver:** a conditional waiver before payment, and an unconditional waiver released when payment is made (Buildertrend, Procore Pay, GCPay).
- **Not checked in this pass:** whether SAIRNbuild's 22 lien-waiver references block payment to a sub or only record the waiver.

### 5.4 Accounting sync

Buildertrend, JobTread and Knowify all ship **real two-way QuickBooks Online sync** with clear rules for which way each object flows. Buildertrend's sync runs every 2 hours, and the QuickBooks copy wins after an edit there.

**The commonly reported failures:**
- duplicate customers or vendors created from small name differences;
- **cost codes mapped to the wrong accounts**;
- retainage needing its own receivable account.

**Relevant market changes:**
- **QuickBooks Desktop Pro and Premier stopped selling to new US buyers after 2024-09-30.** QuickBooks Online is the target.
- **Intuit Enterprise Suite Construction Edition** (February 2026) moves Intuit itself into this space. Whether it produces a G702 **conflicts** between sources.

SAIRNbuild today has no sync. I-2 means it currently *displays* a sync status it does not have.

### 5.5 WIP and what sureties expect

**What sureties read** (commercialsurety.com; peasebell.com; [Surety Bond Quarterly 2026-07-08](https://suretybondquarterly.org/2026/07/08/making-cpas-and-contractors-surety-underwriting-savvy/)):
- the WIP schedule is **the second document after the financial statements**;
- it must show **estimated cost to complete**, billings, and recognized profit;
- sureties look for **profit fade** and heavy **over-billing**;
- they want it updated quarterly, or monthly when seeking more bonding capacity.

**Rule-of-thumb thresholds** (secondary sources, not policy):
- compiled statements up to about $0.5–1M single-job capacity;
- reviewed statements for about $1–5M;
- audited statements above about $5–10M.

**Who this applies to:**
- **Ohio has no statewide residential bond;** local bonds are about $5–25K.
- **Home-construction contracts are exempt from percentage-of-completion (POC) accounting for tax.**
- **So I-1 matters mostly for light-commercial jobs, bank credit lines and anyone seeking surety capacity.** For those users, a WIP schedule that hides fade is worse than having none.

---

## 6. Practitioner voice

This lens was thin:
- **No Reddit thread surfaced.**
- **No homeowner (portal user) voice was found at all.**
- Many quotes reached this pass through competitor pages (Projul, JobTread, Connecteam), which are flagged as [via vendor].
- Quotation marks show only words the result presented as a reviewer's own.

### 6.1 Price trust is the loudest complaint, and it lands on SAIRNbuild's buyer

**13 statements across 7 products.**
- **Buildertrend on ContractorTalk:**
  - a Core plan at $299 was told it would rise **122% to $699**, called "this absurd increase";
  - another user reported a **65%** rise ([thread](https://www.contractortalk.com/threads/buildertrend-price-hike.447579/)).
- "After being with BuilderTrend since 2014 we were hit with a 75% price increase without notice" [via vendor].
- **"not your friend unless your volume exceeds two million dollars"** [via vendor]. This is SAIRNbuild's under-$2M owner-operator.
- **A BBB complaint:** no refund after renewal "even if missed by just one day", and a suspension clause the vendor refused to apply ([BBB](https://www.bbb.org/us/ne/omaha/profile/computer-software/buildertrend-0714-300027310/complaints)).
- **No bulk export**, so users keep paying to keep access to their records [via vendor].
- **A switcher's reason:** "the price of buildertrend was about to triple" ([JobTread Capterra](https://capterra.com/p/218503/JobTread/reviews/)).
- **Houzz Pro:** a 12-month auto-renewal, a 4-month early-exit fee, and a class action.

### 6.2 The client-facing money moment is where users get frustrated

- **Buildertrend:**
  - the Selections tab is "not very user friendly", and "clients seem unclear on approval" (paraphrase);
  - change orders confuse the bill;
  - "lots of duplicate entry with allowances and selections";
  - online pay is "cumbersome to setup and use" (paraphrase).
- **What CoConstruct users praised consistently:** turning the estimate into selections **without double entry**.

### 6.3 Complexity, mobile and QuickBooks

- Buildertrend has "like 10x more clicking than there needs to be" ([G2](https://www.g2.com/products/buildertrend/reviews?qs=pros-and-cons)).
- Subs get "flooded with notifications for unrelated work".
- Subs and clients need logins "just to see dates" (paraphrase).
- Buildertrend's offline mode covers only the time clock and daily logs.
- **A ContractorTalk user dropped Buildertrend because of double entry into QuickBooks** ([thread](https://www.contractortalk.com/threads/buildertrend-quickbooks.225273/)).

### 6.4 Ratings as shown

| Product | Rating |
|---|---|
| Buildertrend | Capterra 4.5 (~2,480) |
| JobTread | Capterra 4.9 (~141) and G2 5.0 (65): small samples, and the vendor promotes its awards |
| Houzz Pro | 4.3 (1,088) |
| Contractor Foreman | 4.5 (~800) |
| Knowify | 4.5 (109) |
| Buildxact | 4.6 (~178) |

**Buildertrend's 4.5 on Capterra sits beside sharply negative forum and BBB comments.** Treat aggregate ratings as a weak signal.

---

## 7. Synthesis

### 7.1 External gaps, ordered by what an Ohio remodeler would feel

1. **Ohio home-construction contract controls (§3.2, §4.3).** A contract builder with the 4722.03 fields, a deposit cap of 10%, a running excess-cost total that triggers the $5,000 estimate, and a three-day cancellation lock for in-home sales. **These are the patterns the Attorney General sues over, and the checks are mechanical.**
2. **An RRP job file for pre-1978 homes (§3.5, §4.1).** Firm and renovator certification with expiry dates, the pamphlet acknowledgment timed within the 60-day window, and 3-year retention. **This is the most enforced federal recordkeeping duty in remodeling, and SAIRNbuild has zero coverage.**
3. **A lien deadline engine (§3.1), once the "first vs last furnished" question is settled.** Below Procore/Levelset the market does not have this. **It is the one compliance feature where SAIRNbuild could lead.** Tie every lien amount to authorized invoice and change-order records (*Nieman*).
4. **Homeowner payment and a reachable portal (§2.2, §5.1; I-3).** This is table stakes in the category.
5. **An AIA-style pay-app export and a lender draw package (§5.1–5.2),** built from draws, retainage and waivers that already exist.
6. **A safety training log with export, and a silica plan (§3.6, §4.2).** The good-faith penalty reduction depends on them.
7. **Spanish and an offline state shown to the user (§2.1).** Contractor Foreman and Fieldwire have both. The two leading residential tools reportedly do not; that claim is competitor-sourced.

### 7.2 Internal, for the owning session (repeats §1.2 so it is not missed)

1. **I-1:** the WIP percent-complete misstates jobs with cost overruns or change orders. Write a regression test first.
2. **I-2:** demo data, including "QuickBooks: connected", seeds for every licence type.
3. **I-3:** the "Client Portal" says "shared" but cannot be shared.
4. **I-4:** default retainage, markup and cost codes live on the device only. This is a documented decision to revisit.

### 7.3 Where SAIRNbuild is on the right side, and should say so

- **Server-side retainage release with an audit trail,** delegated to the shared `wip-accounting.js` engine.
- **Subcontractor award gated server-side on COI, licence and W-9.** This is a control the market markets but rarely shows.
- **A client view that leaves out cost, margin and internal notes by design.**
- **A CSV export exists**, which answers the "no bulk export" complaint about Buildertrend in part. Whether it covers every collection was not checked.
- **One place for jobs, costs, change orders, draws and waivers**, with no separate per-seat price for subs or clients (none exists today).

---

## 8. What this document does not establish or decide

- **No page was opened** (§0.1).
- **§1.2 was read, not run.** Four points in particular were not checked:
  - whether edited demo rows are pushed to the server;
  - whether lien waivers gate sub payment;
  - how complete the CSV export is;
  - whether `budgetFor` is ever updated by change-order cost lines in practice.
- **Unresolved conflicts, kept as found:**
  - the residential lien clock ("first" vs "last");
  - the HB 50 effective date (09-19 vs 09-20);
  - the CoConstruct sunset (the vendor page vs "no public date");
  - Buildertrend's card fee and who pays it;
  - Buildertrend's price tiers;
  - Houzz Pro's tier names and prices;
  - Knowify Advanced ($249 vs $329);
  - Builder Prime's pricing model;
  - the count of statutory lien-waiver states (8, 11 or 12);
  - whether Intuit's G702 support is in Enterprise Suite Construction Edition or in QuickBooks Online Advanced.
- **Not established:**
  - whether HB 568 was enacted;
  - what HB 614 contains;
  - whether 4113.61 excludes 1–3 family homes (secondary source only);
  - the content of the 153.63 amendment;
  - how the dust-lead rule affects RRP cleaning verification;
  - the Sciarappa penalty amount;
  - whether the Lowe's decree has been entered;
  - the name of the 8th District change-order case;
  - any evidence from homeowners who use client portals;
  - E-Verify rules for Ohio private employers.
- **No legal advice, no pricing decision and no code change.** The only write outside `docs/cloud-research/` is this session's own `.claude/claims/cloud.json`.

## 9. What to re-read first, once the network allows

1. **codes.ohio.gov 1311.06.** Settles whether the residential lien clock runs from first or last furnishing, which blocks §7.1 item 3.
2. **codes.ohio.gov 4722.03 and 4722.04, and the HB 50 status page.** Confirms the contract fields, the deposit cap and the effective date.
3. **codes.ohio.gov 4113.61.** Confirms whether 1–3 family dwellings are excluded.
4. **ecfr.gov 40 CFR 745.84 and 745.86, and EPA's dust-lead compliance page.**
5. **Buildertrend's CoConstruct migration page.** Confirms the dates.
6. **The pricing pages** for Buildertrend, JobTread, Knowify and Houzz Pro.
7. **The EPA Region 5 Sciarappa consent order and final order.** Gives the amount and the violations.

**Carried from earlier docs in this session, still pending:**
- SAIRNfreedom §9.1;
- SAIRNsenior §9;
- SAIRNcash §9;
- SAIRNbiz "Decay".

## Sources

Every source is linked inline where it is used. All were retrieved 2026-09-27 and all are [SNIPPET] (§0.1).

Internal sources, read at `origin/main` `3adf4ebd`:
- `sairnbuild.html`
- `api/_resources/sairnbuild.js`
- `SAIRNBUILD-SCOPE.md`
- `docs/superpowers/specs/2026-09-03-competitive-gap-audit-build-vet-biz-grounds-cash.md` §3
- `docs/2026-09-21-sairnbuild-server-wins-conversion-plan.md`
- `docs/SAIRN-OPEN-WORK-INDEX.md` (the SAIRNbuild rows)
