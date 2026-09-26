# SAIRNcash external competitive-gap audit (2026-09-26)

This audit covers five areas:
- **Competitors:** QuickBooks Self-Employed / Solopreneur, Bonsai, Found, Keeper and Lili.
- **Regulation:** quarterly estimated tax, 1099-K and 1099-NEC thresholds, IRS guidance.
- **Accuracy and liability.**
- **Bank-sync reliability.**
- **What freelancers say about these tools.**

**Research pass, dated 2026-09-26, in the isolated cloud-research lane.** It is
docs only: no app code and no tier registers were touched. The file is new,
lives under `docs/cloud-research/`, and lands on the same branch as the
SAIRNlaw, SAIRNvet, SAIRNcode, SAIRNbiz and SAIRNsenior passes.

**Claimed before starting,** as session `cloud`, in commit `2510590d` on
`origin/main`. The file is `.claude/claims/cloud.json` and the subject is
`sairncash`. `sairn_claim.py check` blocked the claim on `cody-q11`, because both
task strings contain the phrase "audit gap". The two claims share no file:
cody-q11's only cloud item is scoping a SAIRNcode audit. Per PR §4.3, the claim
was written directly with that note rather than reworded to get past the
matcher. The claim tool was not used to publish, because it pushes by rebasing
the current branch onto `main`. In this clone that branch carries unrelated
commits, so the claim was published from a clean worktree of `origin/main`
instead.

---

## 0. Read this before quoting anything

### 0.1 Why every page fetch failed: a standing environment setting, not this pass

The user asked for a diagnosis. It was made first, with the proxy's own status
endpoint.

| Probe, 2026-09-26 ~18:43 UTC | Result |
|---|---|
| `WebFetch https://www.irs.gov/...` | `EGRESS_BLOCKED`: *"Access to www.irs.gov is blocked by the network egress proxy."* |
| `curl` via `$HTTPS_PROXY` to `irs.gov`, `wellsky.com`, `found.com`, **`example.com`** | All `000`. The proxy's `recentRelayFailures` records each one as **`connect_rejected`, "gateway answered 403 to CONNECT (policy denial or upstream failure)"** |
| `git fetch`/`git push` to `github.com` | Works: this pass pushed `2510590d` to `main` |
| Earlier in this session | The same `connect_rejected` for `sairn.vercel.app:443`, at 18:18 and 18:39 UTC |

**Diagnosis.** This is the **environment's egress policy**, applied at the
upstream gateway. Even `example.com` is refused, so it is not tied to any site,
tool, pass or time of day. What is allowed is GitHub and the package registries
listed in the proxy's `noProxy` set (npm, PyPI, crates, Go proxy). General web
hosts are not. WebFetch and `curl` fail through the same gateway, so this is not
a WebFetch-specific restriction. **It will recur in every pass run from this
environment until the setting changes.**

**The fix is outside the repo.** In the cloud environment's settings (the
environment menu in the session title bar, then Edit, then Network access),
either choose a broader access level or add the needed domains to the allowed
list. The access levels are described at
<https://code.claude.com/docs/en/claude-code-on-the-web>. None of the blocks was
routed around.

**The two prior passes are affected the same way.** The SAIRNsenior doc's §0.1
recorded 38 of 39 fetches as `EGRESS_BLOCKED`, and put it down to "this session's
egress proxy". That description was accurate, but it did not say the cause is
standing. This section supplies that.

### 0.2 Evidence grade: every external claim is [SNIPPET]

Five research passes ran in parallel, one per lens. They exhausted this session's
**200-call WebSearch cap**, and the last lens had 3 calls refused at the cap.
**Zero WebFetch calls succeeded.** Every external claim below is therefore
graded **[SNIPPET]**: it is the search tool's model-written summary of a result
page, not the page itself. Wording in quotation marks is the snippet's
rendering of the page. It is **not verified as the page's own words**.

Source classes are marked where they matter:
- **STAT**: statute
- **REG**: regulation
- **IRS / SSA**: agency guidance
- **PRESS**: journalism
- **PRO**: law-firm or CPA commentary
- **VEND**: vendor
- **3P**: review or aggregator site

Vendor self-claims are marked as vendor claims.

### 0.3 Corrections to the brief's premises

1. **"Bank-sync reliability … SAIRNcash's own stated weak spot" is wrong.
   SAIRNcash has no bank sync at all.** At `origin/main` (`sairncash.html`,
   unchanged since `c0ae9a0a`):
   - `bank` × 0, `Plaid` × 0, `transaction` × 0.
   - The "sync" it has (`sync` × 64, Firebase × 32) is **cross-device sync of
     the user's own hand-typed entries**.

   The 2026-09-03 audit (`docs/superpowers/specs/2026-09-03-competitive-gap-audit-build-vet-biz-grounds-cash.md`
   §7.2 A3) already said so: "the missing half is the bank connection". So §5
   below is a **build-or-don't** lens, not a reliability lens on something
   that exists.
2. **"Billing flow incomplete" is a different weak spot, and it is not an
   engineering one.** `docs/2026-09-17-sairncash-stripe-readiness.md` records the
   live checks:
   - `checkout` returns 500 because the Stripe variables are missing;
   - `verify` returns 500 because Stripe refused an expired `sk_test_` key.

   The open-work index records a decision dated 2026-09-05: Stripe waits on the
   new LLC, "and nothing here should be 'fixed' to route around it". The paid
   path in `sairncash.html` is marked "PARKED 2026-08-24, NOT DELETED". **Bank
   sync and billing are two separate gaps, and neither blocks the other.**
3. **"Core math built" holds, and every 2026 constant checked against a primary
   source matches (§3.1).** However, this pass found a **logic** problem in how
   the math is applied. §1.2 covers it, and it is the most consequential
   finding in this document.

---

## 1. Internal grounding, measured first

`sairncash.html` at `origin/main` `3238bf61` (the file was last changed in
`c0ae9a0a`). Figures are grep counts plus a read of the tax-math block (about
lines 992–1240). **Nothing was run.**

### 1.1 What exists

| Area | State | Evidence |
|---|---|---|
| Tax math | Pure, deterministic functions: SE tax at 92.35% × (12.4% up to wage base + 2.9%), Additional Medicare 0.9%, brackets, standard deduction, SEP/Solo 401(k) room | `TAX_YEAR_2026`, `calcSeTax`, `calcTotalTax`, `calcQuarterlySetAside`, `calcRetirementEstimate` |
| Safe harbor | Takes the lesser of 90% of this year's tax or 100% of prior-year tax, or 110% of prior-year tax if prior-year AGI was over $150k. If no prior-year figure is entered, it is labelled "Partial estimate (90% of this year only)" | ~L1059–1076, ~L342, ~L1225 |
| Due dates | `QUARTERLY_DEADLINES_2026`: 04-15, 06-15, 09-15, 2027-01-15 | ~L1184 |
| AI | The Claude assistant "explains" results the calculator has already computed. It is told "Never recompute, restate a different number", and it has one tool (`get_attention_digest`) | `SYSTEM_PROMPT` ~L1348 |
| Disclaimers | Sidebar: "Estimates only. SAIRNcash does not file taxes -- review with your accountant or filing software before relying on any number here." Footer: "Not a tax filing product." Retirement panel: "not the exact IRS Publication 560 worksheet" | ~L269, sidebar |
| Scope | Federal only, self-employment income only, no W-2 interaction. These are confirmed design decisions (spec §5) | code header |
| Bank data / invoicing / receipts / state tax / filing | **None** (`bank` 0, `receipt` 0, state-tax logic 0, `1099` 0) | grep |

### 1.2 The finding: the safe-harbor comparison can recommend too little, early in the year

**What the code does** (~L1065–1076, ~L1207):

```
estAnnual       = calcTotalTax(ytdNetProfit, …).totalTax   // tax on YEAR-TO-DATE profit
ninetyPct       = 0.9 * estAnnual
safeHarborBasis = min(ninetyPct, (1.10 or 1.0) * priorYearTax)   // when a prior-year figure is entered
quarterlyAmount = safeHarborBasis / 4
```

**What the rule is.** IRC §6654(d)(1)(B) (STAT) sets the required annual payment
as the lesser of:
- 90% of **the tax shown on this year's return**, meaning the **full year**; or
- 100% of prior-year tax (110% above the AGI threshold).

IRS Pub 505 (2026) [SNIPPET] says the same, and the regulatory lens confirms it.

**The defect.** `estAnnual` is the tax on **year-to-date** profit. It is not a
full-year figure; the code does not annualize or project it. So in March,
"Estimated annual tax" is the tax on roughly one quarter's profit, and `min()`
then **picks that small figure over the prior-year safe harbor**. A user who has
entered last year's tax, which is the one input that would protect them, gets a
recommendation **below both** of the amounts the statute accepts. They would
under-pay Q1, and possibly Q2 and Q3, and incur the §6654 penalty the tool exists
to prevent.

The labels make it worse:
- the panel shows the YTD figure under "**Estimated annual tax**";
- the missing-prior-year note calls it "90% of this year's **projected** tax".

Nothing is projected.

**Why this matters more than an ordinary bug:**
- §6654 has **no general reasonable-cause waiver** (STAT §6654(e)(3); IRS FSA
  [SNIPPET]). A user who relied on the app has no software-reliance defence
  (§4.3).
- The tool's whole promise is "the number to set aside".
- It **contradicts a live design decision stated elsewhere in the same file**.
  The Predictive Insights panel (`sairncash.html:1154`, per the 09-03 audit)
  "Deliberately does NOT project a full-year total". The estimator is labelled
  as if it does, but it does not, and then compares the result against a
  full-year statutory basis.

**What a fix would decide, stated rather than made (no code was written):**
- **(a)** When a prior-year figure exists, recommend the **prior-year basis
  outright**. That is the only safe harbor knowable in advance, and it is what
  practitioners advise (PRO [SNIPPET]).
- **(b)** Otherwise, annualize explicitly, and say so.
- **(c)** Implement Form 2210 Schedule AI (§3.2).

Relabelling alone ("tax on profit so far") would be the minimum honest
correction.

**Confidence.** This is a read of the code, not a run. It needs a test before
anyone acts on it: January–March income with a prior-year figure entered,
comparing the recommendation against 25% of the prior-year tax. The platform's
own rule applies: a claim about code is a claim to verify.

### 1.3 Smaller internal findings

1. **The married-filing-separately 110% trigger is wrong.** The profile checkbox
   is fixed to "Last year's AGI was over $150k" (~L334). For MFS the statute's
   threshold is **$75,000** (§6654(d)(1)(C); IRS Pub 505 [SNIPPET]). `75000`
   appears 0 times. An MFS filer with prior-year AGI between $75k and $150k is
   told 100% instead of 110%, which **under-states**.
2. **Entries are never filtered by tax year.** `initFinanceSync` loads every
   income and deduction record (~L1150), and `ytdNetProfit()` sums them all
   (~L1178). From 2027-01-01, 2026 income counts toward the "year-to-date" total
   while `TAX_YEAR_2026` constants still apply. Entries are also always
   **stamped with the moment of entry** (`date: new Date().toISOString()`,
   ~L1167), so January income typed in in February carries a February date.
3. **The due-date list runs out, and has no disaster postponements.**
   `nextQuarterlyDeadline()` returns `null` ("N/A") after 2027-01-15. The four
   dates match the 2026 Form 1040-ES (§3.2), but 2026 IRS disaster relief moved
   them for some users (§3.2).
4. **§199A (QBI) is not applied.** OBBBA made it permanent, and the IRS's own
   2026 1040-ES worksheet includes it (§3.1). Leaving it out **over-states**
   income tax. That is the penalty-safe direction, but it is a real accuracy gap
   against the IRS method and against every filing competitor, and it is **not
   disclosed** (`QBI|199A` × 0).
5. **No state tax.** This is a confirmed design decision. The disclaimer says
   "Estimates only" but does not say "federal only". §6.1 shows this exact
   omission is a documented user complaint about the market leader.

---

## 2. Competitive / market lens

Every row below is [SNIPPET]. Publication dates were rarely shown in the search
results.

| | **QuickBooks Self-Employed → Solopreneur** (Intuit) | **Bonsai** | **Found** | **Keeper** | **Lili** |
|---|---|---|---|---|---|
| What it is | Bookkeeping for solo businesses: income, expenses, invoices, mileage, receipts, P&L, auto bank downloads. Filing goes through TurboTax | Freelancer client-management tool (proposals, contracts, invoicing, time) plus tax estimates | **A business checking account**, plus bookkeeping, tax estimates and invoicing. Does not file; generates a Schedule C | AI deduction tracker **plus tax filing** with pro review | **A business bank account** plus bookkeeping and tax prep (pre-filled forms); does not file |
| 2024–26 status | Solopreneur launched **Feb 2024**. QBSE **closed to new sign-ups May 2024**, and its app was pulled from the stores (reported as 2024-03-24, which conflicts with the sign-up date). Legacy accounts reportedly still worked "as of May 2026" | **Zoom acquisition announced 2025-11-05, closed Dec 2025.** Brand kept for now | Funded ($119M total, per an aggregator). Sponsor-bank change: **Piermont vs Lead Bank conflict**, not resolved | $13M Series A 2021-04-29; **no 2024–26 round found** | **Repositioned toward larger, multi-employee businesses in 2025** (Wikipedia snippet). No 2024–26 round found |
| Price, 2026 | **$20/mo** (Intuit). Annual price conflicts: **$215/yr** (Intuit) vs $120/yr (3P). A free QuickBooks tier exists | Basic $15 / Essentials $25 / Premium $39 / Elite $59 per month (3P). Tax is **conflicting**: a paid add-on per its help centre, or bundled per a 3P site; about $100/yr per competitor sources | **Free / Plus $35/mo / Pro $80/mo.** Plus was reportedly $19.99 before | Only Deductions **$20/mo**; filing $99–$399/yr (3P) | Core $0 / Pro $15 / Smart $35 / Premium $55 per month |
| Quarterly estimate | **Federal only.** Intuit's help page says QBSE "does not calculate state estimated taxes" (VEND). A "Tax Bundle" reportedly allows EFTPS payment in-app (not confirmed) | Estimates plus reminders; **no auto set-aside, no IRS payment** found | **Auto set-aside** of a share of each deposit into a "Taxes" pocket. **Pays the IRS in-app, federal only** (first payment free, then Plus). **No state payments** | Real-time estimates plus reminders; no set-aside or payment found | **Auto "Tax Bucket"** set-aside (Pro and above); no IRS payment |
| Bank sync | Yes; aggregator not established | **Plaid** | Is the bank; links outside accounts via **Plaid** | **Plaid**, read-only | Is the bank (Choice Financial / Sunrise); links outside accounts |
| AI, 2025–26 | Intuit Assist → AI agents (2025) → "Intuit Intelligence" (2026). The accounting agent reportedly helps with 1040-ES | Zoom AI Companion named; nothing Bonsai-specific confirmed | "Found assistant" in **beta**: moves cash and pays contractors **after the user approves** | "AI Accountant". Vendor claim: 96% accuracy vs 94% for a human pro | "Accountant AI" (2024) |
| Scale (vendor claims) | — | — | — | "More than 1M Americans" | "200,000+ businesses" |

Sources, all retrieved 2026-09-26 [SNIPPET]:
- **QuickBooks:** quickbooks.intuit.com/solopreneur/; [Intuit: state estimates](https://quickbooks.intuit.com/learn-support/en-us/help-article/state-taxes/need-pay-estimated-quarterly-taxes-state/L2IBRpEpC_US_en_US); [Intuit migration article](https://quickbooks.intuit.com/learn-support/en-us/help-article/migrate-services/switch-quickbooks-self-employed-quickbooks/L3pEGh1f5_US_en_US); [NerdWallet pricing](https://www.nerdwallet.com/article/small-business/quickbooks-pricing).
- **Bonsai:** [Zoom acquires Bonsai](https://www.zoom.com/en/blog/zoom-acquires-bonsai/); [Bonsai tax help](https://help.hellobonsai.com/en/articles/3670007); [Bonsai Plaid](https://help.hellobonsai.com/en/articles/1865131).
- **Found:** [Found Plus pricing](https://found.com/help/found-plus/how-much-does-found-plus-cost); [tax auto-saving](https://found.com/help/taxes/how-does-tax-auto-saving-work); [tax payments](https://found.com/help/taxes/how-do-i-make-tax-payments-through-found); [Found assistant](https://found.com/found-assistant).
- **Keeper:** [Keeper pricing (3P)](https://freelancerprofit.com/keeper-tax-review/).
- **Lili:** [Lili plans](https://lili.co/plans); [Lili tax bucket](https://support.lili.co/hc/en-us/articles/360039640591); [Lili BusinessWire 2025-11-17](https://www.businesswire.com/news/home/20251117293120/en/).

**Also relevant:**
- **Hurdlr** is about $10/mo (3P).
- **FlyFin Basic** is about $7/mo billed annually; it has a CPA filing tier.
- **Everlance** was acquired by **Motus, 2025-02-19**.
- **Catch** (tax withholding for freelancers) **shut down on 2023-04-06** and
  came back in Oct 2023 as insurance only
  ([TechCrunch 2023-03-06](https://techcrunch.com/2023/03/06/catch-insurtech-shutting-down/)).

### 2.1 What the competitive lens changes

1. **Only providers that are, or partner with, a bank offer automatic
   set-aside.** Found offers it on its free tier and Lili from $15. SAIRNcash can
   only **calculate** the number and never **move** money. Its copy must never
   imply saving. Found does pay the IRS in-app, but for federal only. A clear
   step-by-step guide to **IRS Direct Pay / EFTPS** closes most of that gap at no
   cost.
2. **At $9.99, SAIRNcash is the only product in its price band without bank
   data.** Hurdlr (about $10) and FlyFin (about $7) both link banks. Manual entry
   has to be **positioned as a choice**: no bank credentials shared, and none of
   the §6.4 freeze risk. Otherwise it reads as an omission.
3. **"Explains, never acts" is defensible but not a feature lead.** Intuit's
   agents, Found's approval-gated assistant and Keeper's AI Accountant all *do*
   things. SAIRNcash's refusal to act or file is correct for its scope (09-03
   audit, A4). It should be stated as a **safety commitment**, backed by §4.
4. **The standalone freelancer tax tool keeps failing to stand alone.** QBSE was
   folded into a $20 product; Bonsai went to Zoom; Everlance went to Motus; Lili
   moved upmarket; Catch shut its tax product. There is room for a new product,
   and also a warning about the business model.
5. **Not checked, and possibly a real differentiator: SEP / Solo 401(k) room
   estimation.** No competitor result mentioned it. That is absence of evidence
   on marketing pages only.

---

## 3. Regulatory / compliance lens

### 3.1 Every checked 2026 constant matches

| Constant | SAIRNcash | Verified | Source |
|---|---|---|---|
| SS wage base | $184,500 | **match** | [SSA 2025-10-24](https://www.ssa.gov/news/en/press/releases/2025-10-24.html); [IRS Topic 554](https://www.irs.gov/taxtopics/tc554) |
| SE tax structure (92.35% × 12.4% + 2.9%) | as coded | **match**; no OBBBA change found | IRS Topic 554 |
| Standard deduction S/MFS · MFJ · HOH | 16,100 · 32,200 · 24,150 | **match** | [IRS 2026 inflation adjustments, Rev. Proc. 2025-32](https://www.irs.gov/newsroom/irs-releases-tax-inflation-adjustments-for-tax-year-2026-including-amendments-from-the-one-big-beautiful-bill) |
| Single brackets (all 7) | as coded | **match** | same; [Rev. Proc. 2025-32 PDF](https://www.irs.gov/pub/irs-drop/rp-25-32.pdf) |
| MFJ brackets | $24,800 … $768,700 | **match**: 24,800 / 100,800 / 211,400 / 403,550 / 512,450 / 768,700 | same |
| HOH and MFS brackets | as coded | **NOT verified** in this pass | — |
| SEP cap / 401(k) deferral | $72,000 / $24,500 | **match** | [IRS Notice 2025-67 release](https://www.irs.gov/newsroom/401k-limit-increases-to-24500-for-2026-ira-limit-increases-to-7500) |
| Additional Medicare thresholds | 200k / 250k / 125k | **match**; not inflation-indexed | [IRS Topic 560](https://www.irs.gov/taxtopics/tc560) |
| Quarterly due dates | 4/15, 6/15, 9/15/2026, 1/15/2027 | **match**: Wed, Mon, Tue, Fri | [2026 Form 1040-ES](https://www.irs.gov/pub/irs-pdf/f1040es.pdf) |

The file's own sourcing note ("web-verified 2026-08-10 against IRS.gov + Tax
Foundation") holds up. **Not modelled, and needed if Solo 401(k) goes beyond
under-50:**
- catch-up at 50+: $8,000;
- catch-up at 60–63: $11,250;
- the 401(a)(17) compensation limit: $360,000.

Source: Notice 2025-67 (PRO [SNIPPET]).

**OBBBA (P.L. 119-21, signed 2025-07-04; STAT via IRS/CRS [SNIPPET]):**
- **QBI (§199A)** was made permanent at 20%, with a wider phase-in and a new
  $400 minimum from 2026. The **IRS 2026 1040-ES worksheet includes QBI plus a
  new Schedule 1-A line.** SAIRNcash models neither (§1.3 item 4).
- **Schedule 1-A deductions, 2025–2028:**
  - **Tips** (up to $25,000): the self-employed can qualify, but it **does not
    reduce SE tax**.
  - **Overtime:** employees only, so not Schedule C.
  - **Car-loan interest** (personal vehicle).
  - **Seniors 65+:** an extra $6,000.
- **SALT cap:** $40,400 for 2026, with a phase-down above $505k MAGI. This only
  matters to itemizers, and SAIRNcash models the standard deduction only.

### 3.2 Estimated-tax mechanics, 2026

- **Safe harbor** (STAT §6654(d); [IRS Pub 505](https://www.irs.gov/publications/p505)):
  the lesser of 90% of this year's tax or 100% of prior-year tax. It becomes
  110% if prior-year AGI was over $150,000, **or over $75,000 for MFS**. The
  prior year must be a full 12-month year.
  - SAIRNcash's "lesser" is correct in form (one summary said "greater of", which
    is a summariser error).
  - The **$75k MFS** trigger is missing (§1.3 item 1).
  - The comparison uses the wrong current-year figure (§1.2).
- **Annualized installment method** ([Form 2210 Schedule AI](https://www.irs.gov/instructions/i2210)):
  cumulative periods through 3/31, 5/31, 8/31 and 12/31; factors 4 / 2.4 / 1.5 / 1.
  **This is the main relief for lumpy freelancer income, and SAIRNcash does not
  offer it.** The applicable percentages (22.5 / 45 / 67.5 / 90%) were not
  confirmed by any snippet.
- **Q4 exception:** the 2027-01-15 payment is not required if the 2026 return is
  filed by 2027-02-01 with full payment (1040-ES [SNIPPET]).
- **2026 disaster postponements the hard-coded dates do not know about** (IRS
  newsroom [SNIPPET]; not exhaustive, see the
  [master list](https://www.irs.gov/newsroom/tax-relief-in-disaster-situations)):

  | Relief | Postponed to |
  |---|---|
  | Oglala Sioux Tribe, payments due on or after 2026-06-02 | **2027-02-01** |
  | Fort Peck Assiniboine & Sioux Tribes | **2026-09-28** |
  | San Carlos Apache Tribe | **2026-09-28** |
  | Washington State, 17 counties, deadlines from 2025-12-09 (covers Q1 2026) | **2026-05-01** |
  | Israel-events relief | **2026-09-30** |

- **Underpayment interest rate, 2026** (§6621): Q1 7%, **Q2 6%**, Q3 7%, Q4 7%
  (announced 2026-08-21), compounded daily.
  - [Q1](https://www.irs.gov/newsroom/interest-rates-remain-the-same-for-the-first-quarter-of-2026)
  - [Q2](https://www.taxnotes.com/research/federal/irs-guidance/revenue-rulings/interest-rates-decrease-second-quarter-2026/7tz7h)
  - [Q4](https://www.irs.gov/newsroom/interest-rates-remain-the-same-for-the-fourth-quarter-of-2026)

### 3.3 1099-K and 1099-NEC thresholds: the figure the brief asked to verify

- **1099-K for calendar-year 2026: more than $20,000 AND more than 200
  transactions.**
  - Legal basis: STAT, OBBBA §70432(a), amending §6050W(e).
  - It **restores** the pre-ARPA test **retroactively**. That cancels the IRS
    phase-down ($5,000 for 2024, $2,500 for 2025, $600 planned for 2026).
  - Sources: [IRS Notice 2025-62](https://www.irs.gov/pub/irs-drop/n-25-62.pdf);
    [IRS FAQ release](https://irs.gov/newsroom/irs-issues-faqs-on-form-1099-k-threshold-under-the-one-big-beautiful-bill-dollar-limit-reverts-to-20000).
  - PRO sources say "retroactive to 2022"; the primary effective-date wording
    was not seen.
  - Backup-withholding regulations aligned to this were proposed on 2026-01-09
    and reportedly finalized by August 2026 (PRO).
- **1099-NEC / 1099-MISC: $2,000 for payments after 2025-12-31** (up from $600).
  It is **indexed from 2027**. Legal basis: STAT, OBBBA §70433 (PRO:
  [NATP](https://www.natptax.com/news-insights/blog/new-1099-rules-under-obbba-what-tax-pros-need-to-know-for-2026-and-beyond)).
- **What this means for the product.** Many 2026 freelancer clients will send no
  1099 at all. Income is taxable whether or not a form arrives. **SAIRNcash
  should never reconcile income against 1099s received.** Today it has no 1099
  logic (`1099` × 0), which is correct. If any copy saying "you'll get a 1099" is
  ever written, it must use the figures above.

### 3.4 IRS guidance on freelancer tax tools

- **IRS Direct File is discontinued.** It was not offered for filing season 2026
  and has no relaunch date (PRESS:
  [Nextgov 2025-11](https://www.nextgov.com/digital-government/2025/11/direct-file-wont-happen-2026-irs-tells-states/409309/);
  [Tax Notes 2025-11-05](https://www.taxnotes.com/featured-news/irs-shutters-direct-file-citing-cost-and-low-uptake/2025/11/05/7t7q0)).
  SAIRNcash's "hand off to your accountant or filing software" copy (it names
  TurboTax, H&R Block and a CPA) should not point to Direct File.
- **The IRS 2026 "Dirty Dozen" names AI for the first time.** Per the IRS page
  summary: "Taxpayers should not rely on AI-generated responses to complex tax
  questions, and they should verify any calculations or information provided by
  artificial intelligence." It is filed under impersonation scams, but the
  sentence applies to any "AI co-pilot"
  ([IRS](https://www.irs.gov/newsroom/dirty-dozen-tax-scams-for-2026-irs-reminds-taxpayers-to-watch-out-for-dangerous-threats)).
- **Circular 230 governs "practice before the IRS"** (REG, 31 CFR Part 10).
  - *Loving v. IRS* (D.C. Cir. 2014) held that preparing a return is not
    practice.
  - An estimate-only tool that neither files nor represents anyone is outside
    it. **That is an inference, not a ruling.**
  - The December 2024 proposed rewrite was not seen finalized.
  - IRS OPR guidance (reported as June 2026) tells *practitioners* not to rely
    solely on AI ([JofA](https://www.journalofaccountancy.com/news/2026/jun/irs-outlines-ai-risks-circular-230-duties-for-tax-practitioners/)).
- **§7216** (disclosure and use of return information; REG 301.7216-1) reaches
  "auxiliary services in connection with" return preparation, including software
  developers. A non-filing estimator is **probably** outside it. **If SAIRNcash
  ever exports to a filing product or markets itself as return-prep help, §7216
  consent rules could apply**, including to data sent to an AI vendor. **That
  needs counsel, and is not established here.**

---

## 4. Accuracy / liability lens

### 4.1 Documented failures

| Date | Who | What | Amount | Status | Source |
|---|---|---|---|---|---|
| 2022-05-04 | 50 state AGs + DC v. Intuit | Low-income filers eligible for Free File steered into paid TurboTax | $141M | Settlement (AVC) | [TN AG](https://www.tn.gov/attorneygeneral/news/2022/5/4/pr22-14.html) |
| Jan 2024 → **2026-03-20** | FTC v. Intuit ("free" ads) | FTC opinion found the ads deceptive. The **Fifth Circuit vacated it on procedural grounds** (Jarkesy: the case belongs in an Article III court), not on truthfulness | — | Vacated | [FTC 2024](https://www.ftc.gov/news-events/news/press-releases/2024/01/ftc-issues-opinion-finding-turbotax-maker-intuit-inc-engaged-deceptive-practices); [CA5 No. 24-60040](https://www.ca5.uscourts.gov/opinions/pub/24/24-60040-CV0.pdf) |
| Jan 2025 | FTC v. H&R Block | Forced downgrades, data deletion on downgrade, "free" claims | $7M | Final order | [FTC](https://www.ftc.gov/news-events/news/press-releases/2025/01/ftc-finalizes-order-hr-block-requiring-them-pay-7-million-overhaul-advertising-customer-service) |
| Tax years 2020–24; suit filed 2025-05-05 | TurboTax (Ontario) | CARE credit computed on the lower earner only. The CRA reassessed with interest, and **Intuit offered to reimburse interest and penalties** | "thousands" per family | Proposed class action | [Globe and Mail](https://www.theglobeandmail.com/investing/personal-finance/article-intuit-turbotax-ontario-child-care-tax-credit/) |
| Suit filed 2023-01-24 | *Diedrich v. Wolters Kluwer* (TaxWise) | A preparer was fined **$287,640** by the IRS over a missing Form 8867 and blamed the software. **Dismissed**: the licence's one-year claim limit and its disclaimer were enforced | — | Dismissed | [CourtListener](https://www.courtlistener.com/opinion/9890991/diedrich-v-wolters-kluwer/) |
| 2025–26 | *Huang v. US* (N.D. Cal.); *Zhang v. IRS* | Form 3520 penalties where the taxpayer relied on TurboTax. In Huang, the **reasonable-cause claim survived dismissal**. Zhang: $723,993 in penalties; a bench trial reported for 2026-11-10 | see conflicts | Pending | [CFTD 2025-05-29](https://www.currentfederaltaxdevelopments.com/blog/2025/5/29/district-court-addresses-form-3520-penalties-reasonable-cause-and-irs-authority-in-huang-v-united-states-a-turbotax-defense-not-dismissed-out-of-hand); [Forbes 2026-08-11](https://www.forbes.com/sites/virginialatorrejeker/2026/08/11/can-you-blame-turbotax-for-a-tax-penalty-courts-are-starting-to-ask/) |

**No press investigation, regulator action or lawsuit was found about the
accuracy of Keeper or FlyFin.** Only anecdotal reviews were found.

### 4.2 AI tax assistants, tested

| Date | Tester | Finding |
|---|---|---|
| 2024-03-04 | Washington Post | Intuit Assist and H&R Block AI Tax Assist were "unhelpful or wrong as much as half the time" on 16 questions. **The split conflicts:** one secondary source says TurboTax got more than half wrong and H&R Block about 30% ([WaPo](https://www.washingtonpost.com/technology/2024/03/04/ai-taxes-turbotax-hrblock-chatbot/)) |
| 2024-06 | National Taxpayer Advocate | Taxpayers should "not solely rely" on AI tax advice ([TAS](https://taxpayeradvocate.irs.gov/news/tax-tips/is-ai-generated-tax-advice-making-the-grade/2024/06)) |
| 2025 | *J. Emerging Tech. in Accounting* (AAA) | ChatGPT answered 39–47% of questions correctly, and did worse on rules that changed after its training cutoff ([AAA](https://publications.aaahq.org/jeta/article/22/1/23/13402/Is-ChatGPT-an-Accurate-Source-of-Information-for)) |
| undated | NerdWallet | Chatbots **gave different answers when the same question was repeated** ([NerdWallet](https://www.nerdwallet.com/taxes/studies/doing-taxes-with-ai)) |

**Do not cite "17 models, 43% average accuracy."** It could not be tied to a
named study.

**Why this matters for SAIRNcash.** Its assistant is already built the way this
evidence argues for:
- the calculator is deterministic;
- the model only explains and is told "Never recompute";
- it has one tool, and must stop if that tool fails.

That is the strongest honest claim in the product, and **it is not stated
anywhere a customer would see it**.

The residual risk is the **explanation**. The areas where tested bots failed
(state residency, crypto, foreign items, multi-state) are outside SAIRNcash's
scope. The system prompt tells the assistant to ask for real figures and refer
out on filing. It does **not** list those topics as ones to refuse outright.

### 4.3 Who bears the penalty

- **§6654 has no general reasonable-cause exception.** Waivers are limited to
  casualty, disaster or "unusual circumstances", or retirement after 62 or
  disability (STAT §6654(e)(3);
  [IRS](https://www.irs.gov/payments/underpayment-of-estimated-tax-by-individuals-penalty)).
  **If SAIRNcash's number is wrong, the user pays the penalty, and "the app said
  so" does not get it waived.**
- *Bunney v. Commissioner*, 114 T.C. 259: "Tax preparation software is only as
  good as the information one inputs into it." Reliance on software is not
  reasonable cause *unless there was a programming flaw*.
- Huang is the first sign of a software-reliance defence. **§1.2 is the kind of
  flaw that defence is built on**, which is why it outranks every market finding
  in this document.
- **§6694 preparer penalties** attach to preparing "all or a substantial portion"
  of a return (Reg. 301.7701-15). **No authority was found applying them to
  estimate-only software. That is an inference, not a ruling.**

### 4.4 How competitors disclaim and what they guarantee

| Vendor | Guarantee | Scope and exclusions |
|---|---|---|
| TurboTax | "100% Accurate Calculations": pays IRS or state penalty and interest "because of a TurboTax calculation error" | **Calculation errors only, not advice.** The user pays any extra tax. Only penalties and interest on the first notice, claimed within 30 days. Intuit would not say whether AI answers are covered ([guarantees](https://turbotax.intuit.com/corp/guarantees/)) |
| H&R Block | "100% Accuracy": penalties and interest from its own errors | **Capped at $10,000 in aggregate.** Excludes information the user supplied, "positions taken by you", and law changes ([guarantees](https://www.hrblock.com/guarantees/)) |
| Keeper | Marketing: a tax pro reviews the return | ToS: "any understated tax and imposed interest and penalties are your responsibility… Keeper Tax assumes no liability." **Marketing and terms conflict** ([terms](https://www.keepertax.com/terms)) |
| FlyFin | Marketing: "ensure 100% accurate tax review and preparation" | ToS: "NEITHER FLYFIN OR ITS SUPPLIERS MAKE ANY REPRESENTATIONS, WARRANTIES OR GUARANTEES… REGARDING THE ACCURACY." **Marketing and terms conflict** ([ToS](https://flyfin.tax/terms-of-service)) |
| QuickBooks calculator | none | "not financial, legal, or tax advice". **Names its scope:** SE tax only, "does not include income or other taxes you may owe" |
| Found | none | "not intended to provide, and should not be relied on for, tax or legal advice". Ties the estimate to the user's own Tax Profile ([help](https://found.com/help/taxes/how-is-my-tax-bill-calculated)) |
| Bonsai | none | Does "not provide tax, legal or accounting advice… informational purposes only" |

**The pattern:**
- No product guarantees *advice*.
- The paid guarantees cover **only penalties and interest from the vendor's own
  calculation error**, never the tax itself.
- Every estimate-only product guarantees nothing, and the better ones **name
  what is excluded**.

SAIRNcash's "Estimates only… review with your accountant" is in line with the
market. It is weaker than QuickBooks on scope, because it does not say "federal
only" or "no state".

### 4.5 AI-claims enforcement: the risk that applies to a $9.99 co-pilot

- **FTC v. DoNotPay** (final order 2025-02, 5-0). DoNotPay "never tested" whether
  its "AI lawyer" matched a lawyer. It paid **$193,000**, and the order bars
  unsubstantiated professional-equivalence claims
  ([FTC](https://www.ftc.gov/news-events/news/press-releases/2025/02/ftc-finalizes-order-donotpay-prohibits-deceptive-ai-lawyer-claims-imposes-monetary-relief-requires)).
  It **survived** the 2025-12-22 rollback that vacated the Rytr order
  ([FTC](https://www.ftc.gov/news-events/news/press-releases/2025/12/ftc-reopens-sets-aside-rytr-final-order-response-trump-administrations-ai-action-plan)).
- **SEC "AI-washing" (2024-03-18):** Delphia and Global Predictions paid
  $225K and $175K ([SEC](https://www.sec.gov/newsroom/press-releases/2024-36)).
- **The lesson for SAIRNcash:**
  - **Never** write "accurate", "CPA-level" or "replaces your accountant".
  - Keep a **documented test suite of the calculator against the IRS 1040-ES
    worksheet**, so that any accuracy claim that is made has evidence behind it.
  - The FlyFin and Keeper marketing-versus-terms mismatches are exactly the
    shape DoNotPay was fined for.

---

## 5. Bank sync: whether and how to add bank data (SAIRNcash has none; see §0.3)

### 5.1 Cost

- **Plaid publishes no per-unit rates.** Its billing docs describe:
  - one-time per-account fees;
  - a **monthly fee per Item for Transactions, charged as long as the Item
    exists**;
  - per-request fees;
  - pay-as-you-go with **no minimum** ([Plaid billing](https://plaid.com/docs/account/billing/)).
- **Plaid Trial plan:** teams created on or after **2026-04-15** get **10 free
  Production Items**, Transactions included
  ([Plaid support](https://support.plaid.com/hc/en-us/articles/39994173227159)).
- **Third-party estimates, not Plaid's own, do not quote:** $0.25–$0.30 per Item
  per month. At 1–2 Items per user that is **roughly 3–6% of $9.99**, before
  support costs. This is our arithmetic on unverified figures.
- **Others:**
  - **Teller:** $0.10 per Transactions call; free for 100 live connections
    (source may not be Teller's own page).
  - **Stripe Financial Connections:** 2022 prices are stale; now custom.
  - **MX:** "$15k–$90k/yr" (weak blog).
  - **Akoya:** bank-owned; heavy legal review.
  - **SimpleFIN:** the **user** pays $1.50/mo, so the app carries no bill. Actual
    Budget uses it.

### 5.2 Reliability

- **Scraping is being replaced by bank APIs.** Plaid says **80% of traffic was on
  or moving to APIs as of September 2025**, and that Chase, Capital One, USAA and
  Wells Fargo are direct (vendor claim). **No overall failure rate was found.**
- **Re-authentication churn is structural:**
  - some banks (PNC is named) require US OAuth consent to be renewed **every 12
    months**;
  - **Bank of America Items are being migrated to a new API throughout 2026**,
    and every one needs update mode ([Plaid OAuth docs](https://plaid.com/docs/link/oauth)).
- **Pending-to-posted duplicates.** Plaid **removes** the pending transaction and
  **creates** a posted one linked by `pending_transaction_id`. In "rare cases" the
  link is missing. **An app that ignores the removal webhook shows duplicates**
  ([Plaid transactions data](https://plaid.com/docs/transactions/transactions-data)).
  Open-source trackers have filed exactly this bug.
- **Banks now charge for data access:**
  - Chase sent aggregators fee sheets in **July 2025**; the first estimate was
    about $300M/yr for Plaid (Forbes 2025-07-21; Fortune 2025-07-16; URLs not surfaced).
  - Plaid and JPMC renewed in **September 2025**; terms undisclosed.
  - By **2025-11-14**, Chase had deals covering more than 95% of its data pulls
    (CNBC).
  - Plaid says it won't pass the cost on. **That is intent, not a contract term.**
  - Wells Fargo and PNC are pressing for fees too.

### 5.3 Regulation: §1033

- **Timeline:**
  - Final rule **2024-10-22**; effective 2025-01-17.
  - *Forcht Bank / KBA / BPI v. CFPB* (E.D. Ky. 5:24-cv-00304) was filed the same
    day.
  - CFPB ANPR to reconsider: **2025-08-22**
    ([FR 2025-16139](https://www.federalregister.gov/d/2025-16139)).
  - **2025-10-29: the court enjoined enforcement** pending a new rulemaking.
  - A new NPRM went to OIRA in **early August 2026**; it reportedly **allows bank
    fees after a free allotment** (American Banker / Consumer Finance Monitor
    [SNIPPET]).
  - **Nothing had been published as of 2026-09-26.**
- **The 2024 rule's third-party duties show the likely shape even while
  unenforceable** (12 CFR 1033.421):
  - use only what is "reasonably necessary" for the product the user asked for;
  - re-authorise every 12 months;
  - no targeted ads, cross-selling or data sale without consent.

  A deduction-scanning use fits within that. **Cross-selling from bank data
  would not.**
- **FDX** was recognised as the first standard-setter on **2025-01-08**, for five
  years.

### 5.4 How competitors handle sync problems, and what every one of them keeps

- **QuickBooks:**
  - Reconnecting after an error can download duplicates, and linking twice
    downloads everything twice.
  - Solopreneur can **exclude but not delete** transactions.
  - Offers **PDF/image statement upload parsed by AI**, plus QBO/QFX/CSV upload.
- **Keeper:**
  - Plaid.
  - A relink prompt after bank or password changes; if transactions are still
    missing after 3 days, remove and re-add the account.
  - Texts the user to confirm a possible write-off.
- **Hurdlr:** bank data arrives 3–5 business days late; a duplicate-account merge
  prompt.
- **FlyFin:** Plaid plus Mastercard; **the fallback is the user emailing a CSV to
  support**.
- **Found and Lili:** being the bank removes sync problems **for their own
  account only**. Both still link outside accounts (Found via Plaid).

**Every competitor that syncs banks also keeps a manual or file path.**

**Becoming the bank adds counterparty risk:**
- **Synapse** filed Chapter 11 on 2024-04-22; about $85M is missing and more
  than 100k users were frozen.
- **Evolve's breach** (disclosed 2024-06-26) hit Affirm, Mercury, Wise and
  others.
- **Bonsai's business-account funds sat at Evolve via Stripe Treasury** and were
  moved to Fifth Third on 2025-02-11 ([Bonsai help](https://help.hellobonsai.com/en/articles/10435791)).
- Found's former sponsor bank Piermont was under a **consent order in February
  2024** (NYDFS).
- None of the five named competitors appears among named Synapse or Evolve
  victims.

### 5.5 Options, ordered cheapest first

1. **Upload a statement or CSV, and let the existing categoriser propose
   entries.** The user confirms each one.
   - This fills the 09-03 audit's A3 ("bank-scanning for overlooked deductions")
     **without an aggregator bill, a credential or a §1033 surface**.
   - Known failure modes: sign reversal on credit-card files, dates without a
     year, duplicates from overlapping ranges, image-only PDFs.
   - It needs a reconciliation check against the statement's closing balance.
   - QuickBooks ships this.
2. **SimpleFIN-style user-paid sync:** live data, no aggregator bill for SAIRN.
3. **A read-only aggregator link that keeps minimal data.**
   - Budget for re-auth flows and **handle the pending-to-posted removal webhook
     before launch**.
   - Delete Items on churn, because the fee runs as long as the Item exists.
   - Assume prices rise with bank fees.

**Not recommended at $9.99: becoming, or partnering with, a bank** (§5.4).

---

## 6. Practitioner-voice lens

**This is the thinnest lens.** Reddit was unreachable: WebSearch refuses it as a
domain filter, and no thread surfaced in plain queries. Review sites, BBB and the
app stores were snippet-only. Many results were **competitor or affiliate
blogs**: Plutio and Agiled (Bonsai rivals), TruMile, Keeper's own comparison
posts, and freelancerprofit.com (affiliate). Those are weighted below
first-person posts.

In the quotes below, text in quotation marks is a **thread title or reviewer
wording as the result presented it**; everything else is paraphrase.

### 6.1 Estimate accuracy

- **QBSE users do not understand their estimate:**
  - thread title: *"Tax Rate for Quarterly estimate is extremly high above 75% of my net earnings after expense's. Anyone know why this is?"* ([QB Community](https://quickbooks.intuit.com/learn-support/en-us/reports-and-accounting/tax-rate-for-quarterly-estimate-is-extremly-high-above-75-of-my/00/499532));
  - Intuit's answer: it projects the full year;
  - another user saw the estimate triple from Q1 to Q2 on flat income.
- **QBSE does not show a state estimate:** thread title *"My estimated state taxes do not show on any report - why not? The est. federal taxes show up."* ([QB Community](https://quickbooks.intuit.com/learn-support/en-us/account-management/my-estimated-state-taxes-do-not-show-on-any-report-why-not-the/00/1303764)).
  Intuit confirms QBSE is federal-only.
- **Keeper:** multi-state errors are "the most consistent complaint pattern"
  (affiliate summary of BBB and App Store reviews).
- **No practitioner post was found about safe-harbor confusion or penalties
  incurred despite using a tool.** Only CPA explainers were found. They warn that
  a skipped Q1 still incurs a penalty for Q1, and that meeting safe harbor can
  still leave a large April bill.

**Read against §1.2:** the one documented confusion (QBSE's projection) is the
*opposite* design to SAIRNcash's. QBSE projects the full year and surprises users
upward. SAIRNcash does **not** project, yet labels its figure as if it did, and
will surprise users downward. **Show the method; do not hide it.**

### 6.2 Bank sync

QBSE users report:
- thread title *"Why does Quicken Self-Employed suddenly stop syncing with my bank accounts? It hasn't updated in 9 days…"* ([QB Community](https://quickbooks.intuit.com/learn-support/en-us/banking/why-does-quicken-self-employed-suddenly-stop-syncing-with-my/00/1499819));
- thread title *"Why am I seeing duplicate transactions please? … I am seeing this often."* ([QB Community](https://quickbooks.intuit.com/learn-support/en-us/banking/why-am-i-seeing-duplicate-transactions-please-for-instance-it-s/00/838686));
- disconnecting a bank **removes all transactions already categorized** (per Intuit's own help text).

Other products:
- **Hurdlr:** bank connection lost after upgrading.
- **Keeper:** no Venmo, Zelle or Cash App link.
- **Mileage trackers:** trips silently dropped (source is a competitor summarising
  Reddit).

### 6.3 Billing trust

This is **the most repeated complaint about the tax apps.**
- **Keeper, BBB complaint dated 2025-12-01:** "the application ACH withdrew 199
  dollars for an annual renewal with no warning or notification" (paraphrase of a
  BBB complaint). Also reported: a $168 charge after a trial, and a $192 attempt
  on a low-balance card.
- **FlyFin:** a surprise annual charge is "the loudest complaint across
  Trustpilot, BBB, and the App Store" (affiliate).
- **QBSE → Solopreneur:** grandfathered prices end; Solopreneur is $20.
- **Bonsai:** price rises of more than 150%, and tax became a paid add-on
  (competitor sources).

### 6.4 Support, and the banks' own risk

- **Found:**
  - Trustpilot and BBB reports of accounts frozen over transfers, funds held,
    ignored emails, and closures.
  - **BBB grade conflicts:** F on 146 complaints vs A+ accredited.
- **Lili:** unexplained closures; funds returned only after an FDIC and BBB filing
  (Trustpilot).
- **Keeper:** email-only support; BBB customer rating 1.8 alongside an A+ grade.

**A tool with no deposit account cannot freeze anyone's money.** That is a real
and under-used positioning point for SAIRNcash.

### 6.5 Praise, and the QBSE migration

- **Praise centres on automation:**
  - Found's App Store reviews: "the pockets are really handy, especially when it
    comes to setting aside money for taxes";
  - Lili's tax bucket;
  - Keeper's auto-detected write-offs and confirm-by-text.

  **No one praised estimate accuracy.**
- **QBSE → Solopreneur migration is a recurring grievance:**
  - an Etsy community thread titled *"DO NOT switch to Intuit Quickbooks "Solopreneur" From…"* reports lost Etsy data, no way back, and "known since October 2024";
  - a failed auto-migration thread on the QB Community;
  - no accountant access in Solopreneur.

  **A displaced population that fears data loss** is an opening, but only if
  SAIRNcash's own import and **export** are real. Today there is no CSV in either
  direction (`CSV` × 0).

### 6.6 Ratings, as snippets showed them (not verified at source)

| Product | Ratings shown |
|---|---|
| Found | App Store 4.8 (23,183); Play 4.6 (1,330) |
| Lili | App Store 4.7 (6,000+); Play 4.3 (10,000+) |
| Keeper | App Store 4.8; BBB customer rating 1.8 |
| Bonsai | Trustpilot about 4.2 (617) |
| QB Solopreneur/QBSE | Capterra 4.0 (120) |

A high share of Keeper's Trustpilot reviews are marked "Invited". **App-store and
BBB figures differ because different people post on each, and neither is a clean
measure of satisfaction.**

---

## 7. Synthesis

### 7.1 Ordered by consequence to a paying user

1. **The safe-harbor comparison can recommend less than the law requires (§1.2).**
   It is a code read, not a run, so **test first.** If it holds, this outranks
   every market gap: it is the one failure where the user pays a penalty with no
   defence, and where a "programming flaw" is the very thing a
   software-reliance claim would be built on (§4.3).
2. **The MFS 110% trigger is missing, and entries have no tax-year boundary
   (§1.3 items 1–2).** Both are small fixes, and both matter from 2027-01-01.
3. **The disclaimer does not name its scope (§4.4).** Adding "federal only · no
   state · no QBI · depends on what you enter" is cheap. It matches the best
   practice in the market (QuickBooks, Found) and answers the documented QBSE
   complaint (§6.1).
4. **The "explain-only" AI design is SAIRNcash's strongest honest claim, and it
   is invisible (§4.2).** State it, and back any accuracy statement with a
   calculator test suite against the 1040-ES worksheet (§4.5). Consider an
   explicit list of topics the assistant must refer out (state, multi-state,
   crypto, foreign).
5. **No bank data (§5).** Statement or CSV upload into the existing categoriser
   is the cheapest route to A3, with no aggregator bill, no credential and no
   §1033 surface. It also gives the displaced QBSE users the import path they want
   (§6.5).
6. **No Schedule AI annualization (§3.2)** and **no QBI (§1.3 item 4).** These
   are real accuracy gaps against the IRS method. Neither is as urgent as item 1,
   because both err on the safe side (QBI) or are optional relief (AI).
7. **Billing trust (§6.3), not billing mechanics.** When Stripe is unblocked (LLC
   first; §0.3), monthly-only billing with renewal notice and in-app cancel
   answers the most repeated complaint about Keeper and FlyFin.

### 7.2 Where SAIRNcash is on the right side, and should say so

- Deterministic math, with an AI that is forbidden to compute (§4.2).
- It never moves money or files (§2.1 item 3).
- It holds no deposit account, so no freeze risk (§6.4).
- Every checked 2026 constant matches primary sources (§3.1).
- No 1099-matching logic, which is correct under the new $20,000/200 and $2,000
  thresholds (§3.3).
- It refuses to call the retirement figure exact (Pub. 560 note).

---

## 8. What this document does not establish or decide

- **No page was opened.** Every external claim is [SNIPPET] (§0.1–0.2).
- **§1.2 and §1.3 were not run.** They are reads of `origin/main` source and need
  a test before anyone acts on them. The HOH and MFS bracket tables were not
  verified.
- **Unresolved conflicts, kept as found:**
  - QB Solopreneur annual price ($215 vs $120) and the Self-Employed wind-down dates;
  - Bonsai tax add-on vs bundled;
  - Found's sponsor bank and its BBB grade;
  - the Washington Post error split;
  - the Huang penalty amount ($40k vs about $190k) and Zhang's status;
  - Lunch Money: SimpleFIN vs Plaid;
  - Stripe Financial Connections pricing (2022 vs custom).
- **Not established:**
  - any aggregator's real per-unit price or overall link-failure rate;
  - the 2026 §1033 NPRM text;
  - whether any competitor estimates SEP or Solo 401(k) room;
  - whether any competitor computes state estimates, beyond QBSE saying it does not;
  - GLBA / FTC Safeguards Rule reach to a non-filing estimator (budget exhausted);
  - California CTEC or other state preparer registration (budget exhausted);
  - the Schedule AI applicable percentages.
- **No SAIRNcash pricing decision** is made or implied.
- **No code was written, and no app file, claim-tier or register was touched.**
  The only write outside `docs/cloud-research/` is this session's own
  `.claude/claims/cloud.json` on `main`, which the user asked for.

## 9. Decay, and what to re-read first

This pass is dated by:
- Q4 2026 interest at 7% (announced 2026-08-21);
- the §1033 NPRM at OIRA (August 2026);
- Bonsai under Zoom (closed December 2025);
- the 2026 disaster postponements.

Anything here that disagrees with a page read after those events should be
re-fetched, not reconciled.

**Open these first, once the network policy allows (§0.1):**
1. IRS Pub 505 (2026) and IRC §6654(d). These confirm the basis for §1.2 and the
   $75k MFS trigger.
2. Rev. Proc. 2025-32 for the HOH and MFS tables.
3. Form 2210 instructions (Schedule AI percentages).
4. IRS Notice 2025-62 and the OBBBA §70432 effective-date text.
5. Found's tax help pages and Lili's plans page. These are the set-aside and
   payment claims behind §2.1.
6. Plaid's pricing, as a Production enrolment quote.

## Sources

Every source is linked inline where it is used. All were retrieved 2026-09-26
and all are [SNIPPET] (§0.2). Internal sources, read at `origin/main` `3238bf61`:
- `sairncash.html`
- `docs/superpowers/specs/2026-09-03-competitive-gap-audit-build-vet-biz-grounds-cash.md` §7
- `docs/2026-09-17-sairncash-stripe-readiness.md`
- `docs/cloud-research/sairnsenior-external-competitive-gap-audit-2026-09-26.md` §0.1
