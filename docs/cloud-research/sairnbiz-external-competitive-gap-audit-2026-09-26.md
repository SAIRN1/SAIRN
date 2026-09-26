# SAIRNbiz — External Competitive-Gap Audit, Wide Lens (2026-09-26)

**What this is:** SAIRNbiz measured against the SMB HR + payroll + accounting
market through five lenses — competitive/market, regulatory/compliance,
accuracy/liability, adjacent-industry ("free with subscription"), and
practitioner voice — each grounded first in what `sairnbiz.html` actually does.
Same wide-lens convention as
`docs/cloud-research/sairncode-autonomous-coding-wide-lens-supplement-2026-09-26.md`.

---

## 0. Scope, and a correction to the brief

The brief describes SAIRNbiz as "the unified HR+Accounting backbone, free with
every SAIRN subscription", names Gusto, ADP RUN, QuickBooks Payroll, BambooHR,
Rippling and Paylocity as the competitive set, and frames the regulatory lens
around "embedded payroll products".

**Correction, stated first because every lens depends on it: SAIRNbiz is not a
payroll processor, and by explicit, documented design it refuses to become one
by accident.** Read from the code (§0.2): "Run Payroll" computes gross pay and
FICA only. It refuses to compute income-tax withholding or net pay (the column
reads "needs a W-4"), refuses FUTA and SUTA, sends no payment ("No payment is
sent from this app", `sairnbiz.html:666`), files nothing, remits nothing, and has
no Form I-9 or E-Verify function. All six named competitors perform the half
SAIRNbiz refuses (§1.2). So the honest frame is two separate comparisons, not
one:

1. **As payroll, SAIRNbiz is a pre-payroll calculator and records layer.**
   Against full-service payroll it is a category mismatch: a SAIRNbiz customer
   with employees still needs a processor.
2. **As accounting + HR, SAIRNbiz bundles something none of the six sells in one
   subscription:** a native double-entry general ledger with invoicing, AP/AR,
   vendor/1099 tracking, timesheets, benefits records and a hiring pipeline, at
   no additional charge inside a vertical subscription (§1.4, §6).

**Relationship to prior internal work.** A real internal audit already covers
SAIRNbiz: `docs/superpowers/specs/2026-09-03-competitive-gap-audit-build-vet-biz-grounds-cash.md`
§5 (Tier A gaps A1–A4), whose status column was re-derived on 2026-09-15 with
zero rows moved (`docs/2026-09-15-competitive-gap-status-rederived-mechanical-and-five-apps.md`).
That audit says in its own §1 and §10 that its market evidence was "supplied
research, reproduced as given" with "no citation URLs". **This document is the
sourced external evidence that audit lacked.** It does not re-derive that
audit's status column, except where the code has moved since (§0.3, F2). No
SAIRNbiz document existed in `docs/cloud-research/` before this one.

### 0.1 Network-egress and search-cap caveat

- `WebFetch` returned `EGRESS_BLOCKED` on nearly every domain across all seven
  research passes: irs.gov, ssa.gov, dol.gov, uscis.gov, federalregister.gov,
  sec.gov, vendor sites, review sites and court-record sites. The only direct
  page reads were six SourceForge product pages (§7). Every other finding rests
  on `WebSearch` result snippets and the search tool's model-written summaries,
  which sometimes blend several pages. Where a figure could not be pinned to
  one URL, its source note says so.
- **New in this pass: the session-wide `WebSearch` cap (200 calls) ran out part
  way through**, with seven research passes running in parallel. Each pass
  stopped after 24–38 searches. The sub-questions that were never researched
  are named in each section and collected under "What this document does not
  establish". Raising the cap is a session-configuration decision for the user;
  this pass did not change it.

### 0.2 Internal grounding — what SAIRNbiz actually does

Read from `sairnbiz.html` at this branch's HEAD. The file is byte-identical to
`origin/main` at `f7d1eba0` (checked 2026-09-26), so the line numbers hold
against main.

| Area | What the code does | Where |
|---|---|---|
| Payroll run | Calculation only. Gross = pay rate × **scheduled** hours (40 h/week Full Time, 16 otherwise), spread over each employee's pay cycle; a basis sentence is saved with every run | `:3347`, `:3360`, `:3516` |
| Payment | None. The run-history card says "No payment is sent from this app"; the GL entry memo reads "Payroll accrual — … (calculation only, no payment sent)" | `:666`, `:3579` |
| FICA | Employer and employee halves each at a flat 7.65%, with an on-screen caveat that the 6.2% Social Security half stops at the annual wage base, which the app cannot apply (no per-employee year-to-date wages) | `:3967`, `:3972`, `:4058` |
| Withholding / net pay | Refused; the column reads "needs a W-4". The app holds no W-4, filing status or dependants | `:3417-3464` |
| FUTA, SUTA, income tax, sales tax | Refused, each with a stated reason. The Tax & Compliance panel was rewritten on 2026-09-03 after five of its six figures were found to be invented | `:655`, `:3920-3990` |
| Pre-payroll validation | Exactly two checks: missing or zero pay rate (blocks the run) and started within 14 days (warning) | `:3258-3280` |
| Timesheets | Store-backed (`sb_ts`, `sql/sairnbiz_timesheet_schema.sql`). Overtime at 1.5× above a **hardcoded 40 h/week**. The Settings "Overtime Threshold" field is saved but unused, and the save toast says so | `:3113`, `:1035`, `:4849` |
| Vendors / 1099 | Paid-YTD is derived from paid bills for the current calendar year. "1099 Required" means paid **≥ $600**. Undated prior-year payments are disclosed as undecidable rather than guessed | `:3756`, `:3804`, `:968`, `:3774-3833` |
| General ledger | Real double-entry posting to `/api/ledger` (`api/ledger.js`, `api/_lib/ledger.js`, `sql/ledger_schema.sql`, `sql/ledger_balance_trigger.sql`) | `:2303` onward |
| Other panels | Employees, hiring, performance, training, P&L, invoices, expenses, AP, AR, budget, tax, company, vendors, reports | panel ids |
| I-9, E-Verify, new-hire reporting, worker classification | None. Zero occurrences of I-9, E-Verify, employment eligibility or new-hire reporting. Contractors are vendors with a W-9 flag | vocabulary count |
| Hiring pipeline | A free-text "Target Rate" per position (the demo seed holds ranges such as "$26-30/hr"). No structured range and no benefits-description field. The pipeline tracks hiring internally and publishes no postings | `:607-620`, `:1992-1996` |
| "Free" wording | The only in-repo statement found is StoneDesk's AI system prompt: payroll, HR and accounting "are handled by SAIRNbiz, included free with this subscription". There is no SAIRNbiz service agreement and no pricing page in `docs/legal/` | `stonedesk.html:12427` |

### 0.3 Internal findings surfaced by the external research

These are recorded here and **not fixed**, because this lane touches
`docs/cloud-research/` only. Each needs its owning build session to re-derive
it and decide.

**F1 — The "1099 Required" count uses a threshold that stopped being the law on
2026-01-01.**
- OBBBA raised the Form 1099-NEC/1099-MISC threshold from $600 to $2,000 for
  payments made after December 31, 2025, CPI-indexed from 2027. IRS
  instructions and proposed regulations say so, and backup withholding moved
  with it (§3.1a).
- `sairnbiz.html:3804` counts a vendor as required when current-calendar-year
  (2026) payments are ≥ $600. The tile reads "$600+ paid" (`:968`), and the
  code comment names "the IRS $600 1099 threshold" (`:3774`). The undated-bill
  disclosure at `:3830` uses the same 600.
- **Direction: it over-counts.** Vendors paid $600–$1,999.99 in 2026 are
  labelled "1099 Required" when they are not. Over-filing is the lower-harm
  direction, but the tile asserts a legal requirement that does not exist for
  that band.
- This is the live instance of the 09-03 audit's row A1 ("compliance thresholds
  must be dated and configurable, never a constant"): a statutory threshold
  moved and the constant did not. The fix shape the research supports is a
  threshold keyed to the **payment date**, so 2025 payments stay at $600 (§3,
  bottom line).

**F2 — Overtime is weekly-only, and the payroll run never sees it.**
- The timesheet panel computes overtime only above 40 hours per week (`:3113`).
  California (daily over 8, double time over 12, seventh-day rules), Alaska
  (daily over 8), Nevada (daily over 8 for workers paid under 1.5× minimum
  wage) and Colorado (over 12 in a day) all have daily triggers (§4.4). The
  panel undercounts overtime in those states.
- The payroll run's gross uses scheduled hours, not recorded ones (disclosed in
  its basis sentence), so **recorded overtime reaches no payroll figure at
  all.**
- The 09-03 audit said phantom-wage detection (its A2) was blocked because
  timesheet hours came from a hardcoded array. **That blocker is gone:**
  timesheets are now store-backed. The gap is now that payroll gross does not
  read them.
- The liability lens shows this exact shape producing real money. Software
  overtime/regular-rate and rounding logic led to employer class settlements,
  and then to employers suing the vendor: *DrinkPAK v. Paylocity* and
  *Nor-Cal Moving v. Paylocity* (§5.6).
- From tax year 2026, any product supplying W-2 data must also separate the
  FLSA overtime premium (box 12 code TT, §3.1c). SAIRNbiz supplies no W-2 data,
  so this is a boundary note, not a defect.

**F3 — Employee FICA omits the Additional Medicare Tax, silently.**
- Employers must withhold an extra 0.9% on wages over $200,000 in a calendar
  year; the threshold is not indexed (§3.2).
- `sairnbiz.html` has no reference to it, so the "Employee FICA" figure
  understates for anyone past $200,000. That runs the opposite way to the
  wage-base overstatement, which the app does disclose.
- Exposure is low for most SAIRN verticals' staff. It is still an undisclosed
  error in a computed figure, which is the class this platform treats as worst.

**F4 — The Benefits panel's plan cards are static HTML showing invented figures
to every licence.**
- `sairnbiz.html:684-710` renders four cards: Health, 401(k), Dental & Vision,
  and Other Benefits. Every value is a literal in markup. Each string occurs
  once in the file, and no script targets `.sval`.
- Examples: "Medical Mutual of Ohio · PPO Gold", "Employee Premium $180/mo",
  "Fidelity Investments", "Employer Match 4% dollar-for-dollar", "Employee
  Contrib. Avg 5.2%", "Plan Assets (est.) $284,000", "Workers Comp — Active ·
  BWC Ohio", and "PTO Accrual 1.5 days/month".
- Two things make this worse than stale demo copy:
  - an average and an asset figure that look computed but are not;
  - a workers'-compensation status shown identically to every customer in every
    state, which is a compliance statement the app cannot know.
- Only the $520 employer-cost line carries a "default" disclosure.
- This is the fabricated-KPI class. It should go through the owning session's
  normal re-derivation before anyone acts on it.

**F5 — "Free" is claimed in an AI prompt and nowhere in a contract.**
- The only "included free" wording found is StoneDesk's AI system prompt
  (`stonedesk.html:12427`).
- The FTC's Guide Concerning Use of the Word "Free" (16 CFR 251) asks that the
  conditions of a "free" offer tied to a purchase be set out clearly and
  conspicuously, at the outset and in close conjunction with the offer (§6.4).
- §6 records the adjacent-industry research's wording suggestion but does not
  adopt it. The suggestion: say the module is included in every subscription at
  no additional charge, and state its calculation-only scope next to the claim.

---

## 1. Competitive lens A — capabilities and 2026 pricing

Researched by a dedicated pass (38 searches before the cap; two fetches, both
blocked). Pricing-guide sites copy each other, so agreement among them is weak
corroboration. Vendor-domain results are treated as vendor-published, but they
are still snippet-only. **NF means "not found or not researched", not
"absent".**

### 1.1 Published pricing (US, captured 2026-09-26)

| Vendor | Tier | Base $/mo | Per-employee $/mo | Notes |
|---|---|---|---|---|
| Gusto | Simple | $49 | $6 | Vendor page [1]. Single-state. The rise from $40 appears only in secondary guides, which date it 2026-03-01 [9]; §7's pass found a pricing-guide claim dating it March **2025** (unconfirmed; conflict preserved) |
| Gusto | Plus | $80 | $12 | Vendor page [1]. Multi-state, next-day pay, time tracking |
| Gusto | Premium | $180 | $22 | Secondary only [9] |
| Gusto | Contractor Only | $35 | $6 per contractor | Secondary only [9] |
| ADP RUN | Essential | Quote (estimates $79 or $59) | Quote (est. $4) | ADP publishes no rates; estimates conflict [17]. W-2/1099 creation costs extra (secondary) [17] |
| ADP RUN | Enhanced / Complete / HR Pro | Quote | Quote | [10][17] |
| QuickBooks Workforce | Payroll (formerly Core) | $50 | $6.50 | Per-employee fee from Intuit's page (undated snapshot, old tier names) [18]; base from a secondary source dated Aug 2026 [20]. Intuit announced new Workforce pricing effective 2026-07-01 [19]; whether these figures include it is unconfirmed. Older, conflicting figures in [29] |
| QuickBooks Workforce | Premium | $88 | $10 | Same sources [18][20] |
| QuickBooks Workforce | Elite | $134 | $12 | Base corroborated by two secondary sources [20][21] |
| QuickBooks Online (the ledger, a separate subscription) | Simple Start / Essentials / Plus / Advanced | $38 / $85 / $140 / $340 | — | Intuit says Essentials, Plus and Advanced changed for renewals on or after 2026-08-01 [23]; the dollar figures are secondary [21][22] |
| BambooHR | Core / Pro / Elite | ≤25 employees: flat rate from $250 | from $10 / $17 / $25 | Vendor page [30] |
| BambooHR | Payroll add-on | Not published | est. $4–6 | Secondary estimate [37]. 15% off when Payroll and Benefits are bundled (US only) [30] |
| Rippling | Payroll module | — | $8 annual / $10 monthly | Rippling's own blog, self-reported [38]. Platform base est. $35–40 plus about $8 per employee for the core, from secondary sources that call pricing quote-based [41] |
| Paylocity | All | Quote (est. $200–250) | Quote (estimates conflict widely) | No published small-business price [48][55] |

Fees captured: +$12 per additional state on QuickBooks Workforce Payroll and
Premium [20]; an estimated $5–10 per employee for ADP year-end forms
(secondary) [17]. Setup fees were not captured for any vendor.

### 1.2 Capabilities matrix — with SAIRNbiz in the first column

Key: **Y** stated in a source · **Y†** implied by a broader vendor statement ·
**T** limited to higher tiers · **A** paid add-on · **N** no (integration only) ·
**?** sources conflict · **NF** not found or not researched. The SAIRNbiz column
is read from the code (§0.2), not from research.

| Function | SAIRNbiz | Gusto | ADP RUN | QuickBooks Workforce | BambooHR (+Payroll) | Rippling | Paylocity |
|---|---|---|---|---|---|---|---|
| (a) Withholding & net pay | **N — refused (no W-4)** | Y† [1] | Y [17] | Y† [20] | Y [31][35] | Y [38] | Y [46] |
| (b) Direct deposit | **N — no money movement** | Y; next-day on Plus and up [1][2] | Y; next-day "on most plans" [17] | Y; same-day on Premium and up [20] | Y [35] | NF | NF |
| (c) File & remit payroll taxes | **N** | Y [1][4] | Y [10] | Y† [20][25] | Y [31][32] | Y [38] | Y [46] |
| (d) 941 / 940 / W-2 / 1099 | **N** (counts 1099-required vendors only, at a stale threshold — F1) | Y† [1] | Y† (extra fee on Essential) [17] | Y† (1099 e-filing) [20] | Y† [33] | Y [38][39] | Y [46] |
| (e) Tax-filing guarantee | n/a (files nothing) | Y, narrow [4] | Y, with exclusions [12][13] | T: Elite only, ≤ $25k/yr [25] | NF | Y†, terms NF [45] | Y, terms NF [46] |
| (f) I-9 / E-Verify | **N** | I-9 Y; E-Verify ? [5][7] | A: partner app [16] | I-9 T (Premium and up) [20] | NF | Y† (low confidence) [44] | E-Verify Y; I-9 Y† [49] |
| (g) State new-hire reporting | **N** | Y [8] | Y [10][11] | NF | NF | Y [38][39] | NF |
| (h) Contractor pay & 1099 | W-9 flag and a 1099 count; no pay, no filing | Y [9] | Y [17] | Y [20] | Y [33][36] | Y† [38] | Y† [46] |
| (i) PTO / time tracking | Timesheets Y (weekly-only overtime, F2); PTO only as static text (F4) | PTO Y; time T [1] | Y† [17] | Time T [20] | PTO Y; time A [30] | NF | NF |
| (j) Benefits admin | Enrolment records and employer cost; plan cards static (F4) | Y [1] | NF | A [20] | A [30] | A [41] | A† [55] |
| (k) HRIS | Y: records, hiring, performance, training | T [1][9] | T [10] | T [20] | Y [30] | Y [41] | Y [53][55] |
| (l) Native general ledger | **Y — included** (`/api/ledger`) | NF (none found) | **N**: exports to QuickBooks Online [14][15] | **Y via QuickBooks Online, a separate subscription** [23][26] | **N**: integrations [35][36] | **N**: sends journal entries out [43] | **N**: Airbase syncs to an outside ledger [50–52] |
| (m) Invoicing / AP / AR | **Y** | NF | NF | Y in QuickBooks Online (Bill Pay Elite now in Advanced) [23][24] | NF | Bill pay (finance products) [42] | AP automation feeding an outside ledger [50] |
| Multi-state | n/a (computes no state tax) | T: Plus and up [1] | Y [17] | 1 state included, +$12 per extra [20] | NF | NF | Y [47] |

### 1.3 Guarantee terms, and what they do not cover

- **Gusto:** the Payroll Service Terms define a "Gusto Error" as failing to pay
  taxes or submit filings on time when the employer funded payroll as required
  [4]. Gusto's liability is to pay the tax and to cover penalties that arise
  directly from the failure. The captured text names penalties, not interest.
  Gusto accepts no liability for penalties, interest or claims caused by
  inaccurate or incomplete employer data [4].
- **ADP RUN** excludes three things [12]:
  - penalties or interest from data before the customer's ADP start date;
  - penalties from ID numbers not received on time;
  - any case without enough cleared funds by ADP's deadline.

  A review site says ADP pays penalties caused by its own errors [13].
- **QuickBooks:** Tax Penalty Protection is **Elite-only**. It reimburses
  penalties and interest up to $25,000 a year "no matter who made the error" if
  the customer sends the full notice within 15 days. The customer still owes
  any extra tax, and cases already with IRS Collections are excluded [25]. No
  guarantee terms were found for Workforce Payroll or Premium.
- **Rippling and Paylocity** claim to cover their own errors; limits were not
  found [45][46]. **BambooHR's** guarantee was not researched (search cap).

Gusto's and ADP's guarantees cover penalties from the vendor's own failure on
correct, timely data. QuickBooks Elite's is broader ("no matter who made the
error") but capped and conditional. **None transfers the underlying tax
liability:** under IRS rules the employer stays liable in every case (§3.5).

### 1.4 Does any of the six ship a native ledger and full-service payroll in one subscription?

**No, on the evidence found.** Intuit is the only one that owns both a native
ledger (QuickBooks Online) and full-service payroll (QuickBooks Workforce), and
they are two subscriptions [23][26]. At the secondary prices captured, a
10-employee shop on QuickBooks Online Essentials ($85) plus Workforce Payroll
($50 + 10 × $6.50) pays about $200/month, before extra-state fees and any
unconfirmed July 2026 change. The other five connect to a ledger only by export
or sync: ADP RUN to QuickBooks Online [14][15], Rippling by journal entries
[43], Paylocity's Airbase-derived layer to an outside ERP [50–52], and BambooHR
through integrations [35][36]. No native ledger was found for Gusto.

**For SAIRNbiz this cuts both ways.** None of the six matches "HR plus a native
double-entry ledger included in the subscription". Every one of them
calculates, files and pays payroll taxes, which is the half SAIRNbiz refuses.
SAIRNbiz is therefore a companion to a payroll processor, not a replacement for
one.

**Not researched (search cap):** BambooHR's guarantee, I-9/E-Verify, new-hire
reporting and multi-state support; setup fees for all six; Rippling's and
Paylocity's direct-deposit speed.

### Sources (§1)

All sources were accessed 2026-09-26. None was read in full: page fetches were blocked, so every entry is snippet-only unless it says "title only".

1. Gusto Pricing, Plans & Fees (2026) — https://gusto.com/product/pricing — accessed 2026-09-26 — primary, vendor-published prices; fetch blocked, snippet-only.
2. Gusto Help Center: Direct deposit payment speeds in Gusto — https://support.gusto.com/article/999752211000000/direct-deposit-payment-speeds-in-gusto — accessed 2026-09-26 — primary; in the vendor-domain result set that carried the next-day-pay details, exact page not attributed.
3. Gusto Help Center: Understanding Gusto plans — https://support.gusto.com/article/178093167290313/understanding-gusto-plans — accessed 2026-09-26 — primary; fetch blocked; appeared in vendor-domain result sets only.
4. Payroll Service Terms | Gusto — https://gusto.com/legal/terms/payroll — accessed 2026-09-26 — primary (contract); source of the "Gusto Error" remedy wording.
5. Gusto Help Center: Complete Form I-9 and E-Verify for new hires — https://support.gusto.com/article/100165395100000/Complete-Form-I-9-and-E-Verify-for-new-hires — accessed 2026-09-26 — primary; title only (the same article ID also appears titled "Complete Form I-9 for new hires").
6. How to Verify I-9 for Remote Employees | Gusto — https://gusto.com/resources/articles/hr/hiring/i-9-remote-employees — accessed 2026-09-26 — primary; possible source of the $20 remote-verification figure, not confirmed.
7. Does Gusto Do E-Verify? What Payroll Leaves Out (2026) — https://www.i-9intelligence.com/articles/gusto-e-verify — accessed 2026-09-26 — secondary; third-party site focused on I-9, may have a commercial interest; probable source of "I-9 on all plans / E-Verify in no plan".
8. Gusto Help Center: Add new employees to Gusto — https://support.gusto.com/article/210728164125837/Add-employees — accessed 2026-09-26 — primary; probable source of the new-hire-report checkbox statement, not confirmed.
9. Secondary Gusto pricing guides: https://rivermate.com/blog/gusto-pricing ; https://www.spotsaas.com/blog/gusto-pricing ; https://gustopricing.com/ ; https://www.g2.com/products/gusto/pricing ; https://casrai.org/guides/gusto-pricing — accessed 2026-09-26 — secondary; the tool did not say which page carried each figure; likely copied from one another; sole support for the $40→$49 date, Premium and Contractor Only prices, and the Employer of Record increase.
10. RUN Powered by ADP payroll packages comparison — https://www.adp.com/what-we-offer/payroll/payroll-for-1-49-employees/payroll-packages.aspx — accessed 2026-09-26 — primary.
11. ADP Payroll and HR Packages (PDF) — https://www.adp.com/-/media/pdf/adp-run-payroll-packages.pdf — accessed 2026-09-26 — primary; undated and possibly stale (a variant PDF URL contains "091620").
12. RUN Powered by ADP activation terms — https://ngapps.adp.com/apps/run_activation/api/provisioning/runtos — accessed 2026-09-26 — primary (contract); exclusion wording may be mixed with [13]'s paraphrase.
13. ADP Payroll Review 2026 — https://www.business.com/reviews/adp-enhanced/ — accessed 2026-09-26 — secondary; probable source of "ADP pays penalties for its errors", not confirmed.
14. RUN Powered by ADP General Ledger & QuickBooks Online (guide PDF) — https://support.adp.com/adp_payroll/content/hybrid/GL/RUN_GL_Guide_QBO.pdf — accessed 2026-09-26 — primary; title and snippet only.
15. ADP RUN payroll product now integrates with QuickBooks Online (Accounting Today) — https://www.accountingtoday.com/news/adp-run-payroll-product-now-integrates-with-quickbooks-online — accessed 2026-09-26 — secondary trade press; publication date not captured.
16. Onboard by HR Cloud for RUN Powered by ADP (ADP Marketplace) — https://apps.adp.com/en-us/apps/175560/onboard-by-hr-cloud-for-run-powered-by-adp/features — accessed 2026-09-26 — primary listing of a third-party partner app.
17. Secondary ADP pricing and features: https://tech.co/hr-software/adp-pricing-guide ; https://peoplemanagingpeople.com/tools/adp-run-pricing/ ; https://www.hireinsouth.com/post/adp-pricing ; https://www.payrolldetective.com/payroll-providers/adp-pricing ; https://startupowl.com/reviews/adp-run (title says "$59 Base Plus $4") ; https://gusto.com/resources/guides/switch-payroll-providers/adp-pricing (written by a competitor) ; https://www.nerdwallet.com/business/software/learn/adp (2023, stale) — accessed 2026-09-26 — secondary; the tool did not say which page carried each figure; estimates conflict.
18. Payroll Services Pricing | QuickBooks Workforce Pricing — https://quickbooks.intuit.com/payroll/pricing/ — accessed 2026-09-26 — primary; snapshot date unknown (uses the old tier names).
19. QuickBooks Payroll pricing changes (Firm of the Future, Intuit-owned) — https://www.firmofthefuture.com/product-update/quickbooks-payroll-price-changes/ — accessed 2026-09-26 — primary; source of the 2026-07-01 change, 6-month price protection and QuickBooks Time +$2.
20. QuickBooks Workforce Payroll vs Premium vs Elite: 2026 Comparison (FitSmallBusiness) — https://fitsmallbusiness.com/quickbooks-payroll-core-vs-premium-vs-elite/ — accessed 2026-09-26 — secondary; described by the tool as Aug 2026; feature sentences were sometimes not attributed between this and [29].
21. QuickBooks Price Increase August 2026 (Certum Solutions) — https://www.certumsolutions.com/library/quickbooks-price-increase-august-2026 — accessed 2026-09-26 — secondary; says Workforce Elite is not included in Advanced.
22. QuickBooks Price Increase 2026: Plus Now $140, Advanced $340 (BizBooks Pro) — https://www.bizbooks.pro/blog/quickbooks-price-increase-2026.html — accessed 2026-09-26 — secondary; its "Advanced bundles Workforce Elite" claim is contradicted.
23. QuickBooks Online August pricing changes and product updates (Intuit) — https://quickbooks.intuit.com/r/product-update/quickbooks-price-changes/ — accessed 2026-09-26 — primary.
24. What's new in QuickBooks Online Advanced: August 2026 (Intuit) — https://quickbooks.intuit.com/r/product-update/whats-new-quickbooks-advanced-august-2026/ — accessed 2026-09-26 — primary.
25. Payroll Tax Penalty Protection (QuickBooks) — https://quickbooks.intuit.com/payroll/tax-penalty-protection/ (also in the result set: https://quickbooks.intuit.com/payroll/disclosure/) — accessed 2026-09-26 — primary, vendor terms.
26. Add Payroll – Payroll Services Pricing (QuickBooks) — https://quickbooks.intuit.com/payroll/pricing/bundle/ — accessed 2026-09-26 — primary; title only.
27. Intuit unveils QuickBooks Workforce — https://quickbooks.intuit.com/r/news/intuit-unveils-quickbooks-workforce/ — accessed 2026-09-26 — primary; title only.
28. QuickBooks Payroll billing: What's changing (Intuit UK) — https://quickbooks.intuit.com/learn-support/en-uk/help-article/mobile-apps/quickbooks-payroll-billing-whats-changing-prepare/L2XuyYA25_GB_en_GB — accessed 2026-09-26 — primary but UK-only; excluded from US figures.
29. Secondary and older QuickBooks sources: https://thepayperiod.com/blog/quickbooks-payroll-core-vs-premium-vs-elite ; https://paygration.com/navigating-quickbooks-online-payroll-core-vs-premium-vs-elite-choosing-the-best-payroll-solution-for-your-business/ ; https://peopleopsclub.com/software/quickbooks-payroll/pricing ; https://gusto.com/resources/guides/switch-payroll-providers/quickbooks-pricing (written by a competitor) ; Intuit lineup PDF from July 2022 (stale) https://quickbooks.intuit.com/oidam/intuit/sbseg/en_us/quickbooks-online/web/content/Payroll-Lineup-PDF_July%202022.pdf — accessed 2026-09-26 — secondary or stale; sources of the older conflicting prices; the tool did not say which page carried each figure.
30. BambooHR Plans and Pricing — https://www.bamboohr.com/pricing/ — accessed 2026-09-26 — primary, vendor-published.
31. BambooHR Payroll — https://www.bamboohr.com/platform/payroll/ — accessed 2026-09-26 — primary.
32. BambooHR Managed Payroll — https://www.bamboohr.com/solutions/managed-payroll — accessed 2026-09-26 — primary.
33. BambooHR Help: FAQ – Tax Documents — https://help.bamboohr.com/s/article/1406708 — accessed 2026-09-26 — primary.
34. BambooHR Payroll Services Agreement (prior to 3-17-2026) — https://www.bamboohr.com/legal/payroll-services-agreement/prior/payroll-services-agreement-prior-to-3-17-2026 — accessed 2026-09-26 — primary; URL and title only, content not read.
35. BambooHR Payroll Software Review 2025 (U.S. News) — https://www.usnews.com/360-reviews/business/payroll-software/bamboohr — accessed 2026-09-26 — secondary; 2025, may be stale.
36. BambooHR Payroll Services Review 2026 (Sonary) — https://sonary.com/b/bamboohr/bamboohr+payroll-services/ — accessed 2026-09-26 — secondary.
37. Secondary BambooHR sources: https://www.outsail.co/post/bamboohr-unveils-new-features-and-revamps-pricing-structure ; https://www.pin.com/blog/bamboohr-pricing/ ; https://peoplemanagingpeople.com/tools/bamboohr-pricing/ ; https://www.hireinsouth.com/post/bamboohr-pricing — accessed 2026-09-26 — secondary; the tool did not say which page carried each figure; add-on prices are estimates.
38. Honest Rippling Payroll Review 2026 (Rippling blog) — https://www.rippling.com/blog/rippling-payroll-review — accessed 2026-09-26 — written by the vendor, self-reported.
39. How to Hire Employees in the US (2026 Guide) (Rippling) — https://www.rippling.com/country-hiring/united-states-employees — accessed 2026-09-26 — vendor.
40. Rippling pricing and payroll pages — https://www.rippling.com/pricing ; https://www.rippling.com/products/payroll — accessed 2026-09-26 — vendor; appeared in results but no figures were captured.
41. Secondary Rippling pricing: https://peoplemanagingpeople.com/tools/rippling-pricing/ ; https://www.hireinsouth.com/post/rippling-pricing ; https://www.vendr.com/marketplace/rippling ; https://cloudappcritic.com/human-resources/rippling-pricing/ ; https://gusto.com/resources/guides/switch-payroll-providers/rippling-pricing (written by a competitor) — accessed 2026-09-26 — secondary; the tool did not say which page carried each figure.
42. Bill Pay Software (Rippling) — https://www.rippling.com/products/finance/bill-pay — accessed 2026-09-26 — vendor; title only.
43. Rippling vs Gusto: Accounting Workflow Integration 2026 — https://ustechautomations.com/resources/blog/rippling-vs-gusto-integration-accounting-workflow-2026 ; Best Accounting Software That Integrates With Rippling — https://thedigitalmerchant.com/best-accounting-software-that-integrates-with-rippling/ — accessed 2026-09-26 — secondary; source of "no native ledger, sends coded journal entries".
44. Rippling Automates I-9 Forms & E-Verify Checks — https://ripplingdocs.com/automate-i9-everify-onboarding-tool — accessed 2026-09-26 — link to Rippling unconfirmed; low confidence.
45. Rippling Payroll Review 2026 (StartupOwl) — https://startupowl.com/reviews/rippling — accessed 2026-09-26 — secondary; probable source of the penalty-reimbursement statement, not confirmed.
46. Payroll Tax Services (Paylocity) — https://www.paylocity.com/products/hr/payroll/tax-services/ — accessed 2026-09-26 — vendor, self-reported.
47. Multi-State Payroll Processing (Paylocity) — https://www.paylocity.com/who-we-serve/multi-state-payroll/ — accessed 2026-09-26 — vendor.
48. Payroll Software for Small Business (Paylocity) — https://www.paylocity.com/who-we-serve/company-size/small/payroll/ — accessed 2026-09-26 — vendor; title only, no price.
49. Payroll Compliance Laws and Best Practices (Paylocity) — https://www.paylocity.com/resources/learn/articles/payroll-compliance/ — accessed 2026-09-26 — vendor; possible source of the E-Verify and earned-wage statements, which came from a vendor-domain result set without page attribution.
50. Spend Management Software / Paylocity for Finance — https://www.paylocity.com/products/finance/ — accessed 2026-09-26 — vendor.
51. Airbase, a Paylocity Company — https://www.airbase.com/ — accessed 2026-09-26 — vendor.
52. Paylocity case studies (Heap; Fountain) — https://www.paylocity.com/why-paylocity/case-studies/heap/ ; https://www.paylocity.com/why-paylocity/case-studies/fountain/ — accessed 2026-09-26 — vendor; the tool did not say which one carried the NetSuite-sync description.
53. Paylocity Announces Completion of Acquisition of Airbase Inc. — https://www.paylocity.com/company/about-us/newsroom/press-releases/paylocity-announces-completion-of-acquisition-of-airbase-inc/ — accessed 2026-09-26 — primary.
54. HR and payroll tech firm Paylocity buys Airbase (Accounting Today) — https://www.accountingtoday.com/news/hr-and-payroll-tech-firm-paylocity-buys-airbase — accessed 2026-09-26 — secondary; source of the $325M figure.
55. Secondary Paylocity pricing: https://www.outsail.co/post/how-much-does-paylocity-cost-in-2026-pricing ; https://softwarefinder.com/resources/paylocity-pricing ; https://peoplemanagingpeople.com/tools/paylocity-pricing/ ; https://marketplace.workology.com/paylocity/ — accessed 2026-09-26 — secondary; ranges conflict; the tool did not say which page carried each figure.

---

## 2. Competitive lens B — market scale, concentration and 2025–2026 moves

Researched by a dedicated pass (34 searches before the cap; the fetches to SEC
EDGAR and ADP investor relations were blocked). **Every figure is snippet-only.**
Figures attributed to 10-Ks are the most reliable here but were still not read
at source. Tags: **[10-K]** audited filing · **[PR]** press release ·
**[self]** company marketing · **[press]** journalism reporting company-confirmed
figures · **[agg]** aggregator estimate.

### 2.1 Scale by vendor

| Vendor | Clients / customers | Revenue | Valuation / funding | As of |
|---|---|---|---|---|
| ADP | Over 1.1M clients worldwide, all segments [1] [10-K]; "900,000+" small-business (RUN) clients [4] [self] | FY2026 $21.9B, +7% [3] [PR]; Small Business segment about $3.4B [5] [self; which deck is not pinned] | Public | FY ended 2026-06-30 |
| Paychex (context) | About 840K customers, about 800K of them payroll clients [6] (possibly analyst wording, verify) | FY2026 $6.5B, +17%, about 12 points of it from Paycor [8] [PR] | Public | FY ended 2026-05-31 |
| Intuit QuickBooks payroll | **No payroll customer count disclosed.** Online Ecosystem paying customers +3% [9] [10-K]; "nearly 8M online paid customers, +4%" in investor-day coverage [10] conflicts with that | Payroll added $266M of Online Services revenue growth in FY2026, "due to mix shift, customer growth, and higher effective prices" [9] [10-K] | Public | FY ended 2026-07-31 |
| Gusto | 500,000+ small businesses [16] [press] | Passed $1B trailing-12-month revenue in Feb 2026; cash-flow positive [16][17] [press] | "Over $9 billion" [16]; $9.3B in a June 2025 employee tender (snippet only) [61] | 2026-05-07 |
| Rippling | 20,000+ customers (May 2025) [26] [agg] | ARR "over $1 Billion", +78% (CEO post, undated) [25] [self] | $16.8B on a $450M Series G, May 2025 [23][24] [press] | 2025–2026 |
| BambooHR | 30,000+ customers (HR software, not payroll) [34] [self] | Not disclosed; an aggregator estimate is not used [36] | Not verified | 2026 |
| Paylocity | About 44,400 clients, +7% [37] [10-K] | FY2026 $1.771B, +11.0% [37] [10-K] | Public | FY ended 2026-06-30 |

These counts cannot be compared directly. ADP's is global and covers all
segments; Gusto's counts "small businesses"; BambooHR's counts HR-software
customers; Intuit discloses none.

### 2.2 Market share — what can and cannot be said

**No credible SMB payroll market-share estimate with a disclosed method was
found, and that absence is the finding.** Each candidate failed:
- Apps Run The World gives global, all-size payroll *software* revenue, not SMB
  clients [43].
- Mordor Intelligence's "12%" for Paychex is ambiguous (share or growth?) and
  comes from a paid report with an opaque method [44].
- 6sense detects software on company websites [45].
- Outsourcing-rate statistics (39% / 61% / 73%) come from aggregator pages
  that state no method [59].

**What can be said is ordinal only:**
- ADP and Paychex are the two largest by client count (both FY2026 10-Ks).
- Gusto (500K+, self-reported) is the largest venture-backed SMB player.
- Intuit is material but undisclosed.
- Paylocity, BambooHR and Rippling are about ten times smaller by count.

No penetration percentage is computed, because a count of US employer firms
could not be confirmed. The SBA's 36,207,130 small businesses includes
non-employers [46].

**Primary sources show the incumbents raising prices.** Intuit's 10-K credits
part of its payroll growth to "higher effective prices" [9]; Paychex's 10-K
cites "price realization" [6].

### 2.3 Strategic moves 2024–2026 (selected)

| Date | Vendor | Move | Src |
|---|---|---|---|
| 2024-10-01 | Paylocity | Closed its Airbase (spend management / AP) acquisition, about $325M | [38] |
| 2024-10-15 | ADP | Closed WorkForce Software, about $1.2B | [39] |
| 2025-03-17 | Rippling | Sued Deel in N.D. Cal. (RICO, trade secrets) | [62][29] |
| 2025-04 | Paychex | Closed Paycor, about $4.1B | [6][44] |
| 2025-05-09 | Rippling | $450M Series G at $16.8B; IPO "not imminent" | [23] |
| 2025-07-01 | Intuit | Began rolling out QuickBooks AI agents, including a Payroll Agent | [14] |
| 2025-08-27 | Gusto | Agreed to buy Guideline (SMB 401(k)); price conflicts: "$600M" vs "$1B+" | [18] |
| 2025-09-29 | ADP | Launched **ADP Embedded Payroll** (Clover is the launch partner) | [56] |
| 2026-02 | Gusto | Passed $1B trailing-12-month revenue | [16][17] |
| 2026-04-09 | Gusto | Acquired Mosey (state/local compliance automation) | [19] |
| 2026-05-06 | Intuit | Unveiled **QuickBooks Workforce** (the HR/payroll rebrand) | [11] |
| 2026-07-21 | BambooHR | Launched Bamboo AI | [35] |
| 2026-09-25 | Rippling v. Deel | Court refused to strike key testimony; Deel's most serious counterclaims sent to arbitration. No trial date found | [31][32][33] |

Neither Gusto nor Rippling has a verified public IPO filing. A claim that Gusto
filed publicly appears only on a low-quality tracker [22], and EDGAR could not
be reached to check.

### 2.4 Embedded payroll — how vertical SaaS adds real payroll without becoming a payroll company

| Provider | Funding (as found) | Named platform customers | Src |
|---|---|---|---|
| Check | $119M over 4 rounds, last in Dec 2021 [agg]. Self-reported "nearly $1 billion" payroll volume in Q1 2025 | Hourly, SocialSchedules, Miter; Housecall Pro (§6.2) | [48][49][50] |
| Gusto Embedded | Part of Gusto | Vagaro, Archy (dental), Heard, Novo; JPMorgan Chase | [51][52] |
| Salsa | $20M Series A, Apr 2025 ($30M total) | Jane, DaySmart, Mangomint, GlossGenius, HoneyBook | [53] |
| Zeal | About $29.6M across rounds (reported total $27.6M; conflict) | Staffing and gig platforms | [54] |
| Everee | About $13–14M | Not captured | [55] |
| ADP Embedded Payroll | ADP | Fiserv Clover | [56] |
| Rollfi (Priority Technology) | Not captured | Not captured | [58] |

**Why this matters for SAIRNbiz.** At least seven providers now sell
full-service payroll to software platforms as an API or white-label layer:
tax calculation, filing, remittance, W-2s and money movement. ADP entered in
September 2025, and named adopters span beauty and wellness, healthcare,
dental, construction, hospitality, point-of-sale and SMB banking. A vertical
competitor to any SAIRN app can ship real payroll as a paid add-on, which
SAIRNbiz's calculation-only payroll does not match (§6.3 has the price points).

**Open (search cap or not found):** average client size for Paychex and
Paylocity; Intuit's payroll customer count; Gusto's total funding; BambooHR's
funding; the Guideline price and completion date; Zeal's Series B date;
Everee's customers; the Rippling v. Deel trial date.

### Sources (§2)

1. ADP, Form 10-K FY2026 (fiscal year ended 2026-06-30) — https://www.sec.gov/Archives/edgar/data/0000008670/000000867026000030/adp-20260630.htm — accessed 2026-09-26 — primary, audited; snippet-only (fetch blocked).
2. Last10K, ADP SEC filings ("10-K Annual Report Wed Aug 05 2026") — https://last10k.com/sec-filings/adp — accessed 2026-09-26 — secondary; used only for the filing date; snippet-only.
3. ADP, "ADP Reports Fourth Quarter and Fiscal 2026 Results" (2026-07-29) — https://mediacenter.adp.com/2026-07-29-ADP-Reports-Fourth-Quarter-and-Fiscal-2026-Results (8-K Exhibit 99: https://www.sec.gov/Archives/edgar/data/0000008670/000000867026000025/q4fy26exhibit99.htm) — accessed 2026-09-26 — primary press release; snippet-only.
4. ADP, RUN Powered by ADP product page and small-business (1–49 employees) page — https://www.adp.com/what-we-offer/products/run-powered-by-adp.aspx ; https://www.adp.com/who-we-serve/by-business-size/1-49-employees.aspx — accessed 2026-09-26 — self-reported marketing; snippet-only; which page carries "900,000+" was not pinned.
5. ADP, Investor Overview May 2026 and Investor Presentation May 2025 — https://investors.adp.com/files/doc_presentation/2026/ADP_Investor_Overview_May2026.pdf ; https://www.investors.adp.com/files/doc_presentations/2025/05/ADP-Investor-Presentation-May-2025-vF.pdf — accessed 2026-09-26 — self-reported investor decks (unaudited); snippet-only; which deck carries "$3.4B" was not pinned.
6. Paychex, Form 10-K FY2026 (fiscal year ended 2026-05-31) — https://www.sec.gov/Archives/edgar/data/0000723531/000119312526307785/payx-20260531.htm — accessed 2026-09-26 — primary, audited; snippet-only; the client-count wording may come from [7].
7. PitchBook, Paychex company profile — https://pitchbook.com/profiles/company/34697-17 — accessed 2026-09-26 — aggregator; listed because the search summary's wording resembles profile text.
8. Paychex, "Paychex Reports Fourth Quarter and Full-Year 2026 Results" (2026-06-24) — https://www.nasdaq.com/press-release/paychex-reports-fourth-quarter-and-full-year-2026-results-2026-06-24 — accessed 2026-09-26 — primary press release; snippet-only.
9. Intuit, Form 10-K FY2026 (fiscal year ended 2026-07-31; filed 2026-09-09) — https://investors.intuit.com/sec-filings/all-sec-filings/content/0000896878-26-000037/intu-20260731.htm — accessed 2026-09-26 — primary, audited; snippet-only.
10. Yahoo Finance, "Intuit Investor Day Puts AI at Center of Growth Reset After Customer Misses" — https://finance.yahoo.com/technology/ai/articles/intuit-investor-day-puts-ai-210208852.html — accessed 2026-09-26 — secondary; snippet-only; the article date and the fiscal period of its figures are unconfirmed.
11. Intuit, "Intuit Unveils QuickBooks Workforce" (2026-05-06), and Accounting Today coverage — https://investors.intuit.com/_assets/_f846a5f5d254e6139bb6691134938154/intuit/news/2026-05-06_Intuit_Unveils_QuickBooks_Workforce_Radically_1310.pdf ; https://www.accountingtoday.com/news/intuit-launches-quickbooks-workforce-for-hcm-payroll — accessed 2026-09-26 — primary press release plus trade press; snippet-only.
12. TechCrunch, "Intuit launches generative AI-powered digital assistant for small businesses and consumers" (2023-09-06) — https://techcrunch.com/2023/09/06/intuit-assist-generative-ai-assistant/ — accessed 2026-09-26 — secondary; snippet-only; pre-2025, context only.
13. Business Wire, "Intuit Launches AI-Powered Intuit Assist for QuickBooks…" (2024-11-20) — https://www.businesswire.com/news/home/20241120869309/en/Intuit-Launches-AI-Powered-Intuit-Assist-for-QuickBooks-Giving-Millions-of-Businesses-a-Competitive-Edge — accessed 2026-09-26 — primary press release; title and date only.
14. CPA Practice Advisor, "Intuit Rolls Out AI Agents for QuickBooks" (2025-06-27) — https://www.cpapracticeadvisor.com/2025/06/27/intuit-rolls-out-ai-agents-for-quickbooks/163868/ — accessed 2026-09-26 — trade press; snippet-only.
15. School of Bookkeeping, "QuickBooks Introduces AI Agents along with a Price Increase," and Gusto's "QuickBooks Payroll Pricing" guide — https://www.schoolofbookkeeping.com/blog/quickbooks-introduces-ai-agents-along-with-a-price-increase ; https://gusto.com/resources/guides/switch-payroll-providers/quickbooks-pricing — accessed 2026-09-26 — third-party blog plus a competitor-written page; snippet-only; the size of the increase was not captured.
16. TechCrunch, "Gusto hits $1B revenue, a figure that brings it closer to public markets" (2026-05-07) — https://techcrunch.com/2026/05/07/gusto-hits-1b-revenue-a-figure-that-brings-it-closer-to-public-markets/ — accessed 2026-09-26 — secondary, reporting company-confirmed figures; snippet-only.
17. Fortune, "Exclusive: Gusto crosses $1 billion in 12-month trailing revenue" (2026-05-07) — https://fortune.com/2026/05/07/exclusive-gusto-crosses-1-billion-12-month-trailing-revenue/ — accessed 2026-09-26 — secondary, company-confirmed; snippet-only.
18. Gusto–Guideline: Gusto Help Center FAQ; Guideline, "It's Official"; WealthTech Strategy, "Gusto Buys 401(k) Platform Guideline for $1B+"; Comrise — https://support.gusto.com/article/250827085750957/gusto-and-guideline-acquisition-faqs ; https://www.guideline.com/education/articles/its-official-guideline-and-gusto ; https://www.wealthtechstrategy.com/post/gusto-buys-401-k-platform-guideline-for-1b ; https://comrise.com/news/whats-happening-in-the-401k-market-guideline-split-and-sold-from-gustos-acquisition-to-vestwells-takeover-what-hr-needs-to-know/ — accessed 2026-09-26 — company help pages (primary) plus secondary; snippet-only; the price figures conflict.
19. PR Newswire, "Gusto Acquires Mosey to Close the Compliance Gap for Small Businesses" (2026-04-09), and Axios — https://www.prnewswire.com/news-releases/gusto-acquires-mosey-to-close-the-compliance-gap-for-small-businesses-302737584.html ; https://www.axios.com/pro/fintech-deals/2026/04/09/gusto-acquires-mosey-compliance-startup — accessed 2026-09-26 — primary press release plus press; snippet-only.
20. PYMNTS, "Gusto Opens Waitlist for AI Assistant for Small Business Owners" (2024); CPA Practice Advisor (2024-09-16); Gusto company news — https://www.pymnts.com/news/artificial-intelligence/2024/gusto-opens-waitlist-ai-assistant-small-business-owners/ ; https://www.cpapracticeadvisor.com/2024/09/16/gusto-introduces-gus-ai-assistant-for-small-businesses/110546/ ; https://gusto.com/company-news/gus-ai-assistant — accessed 2026-09-26 — press plus primary; snippet-only.
21. Workstream, "Gusto Pricing: How Much Does Gusto Really Cost in 2026" — https://www.workstream.us/blog/gusto-pricing — accessed 2026-09-26 — third-party blog; single source; snippet-only.
22. Gusto IPO trackers: TechStackIPO and Forge — https://www.techstackipo.com/ipo/gusto ; https://forgeglobal.com/gusto_ipo/ — accessed 2026-09-26 — TechStackIPO is low quality and unverified, Forge is secondary; snippet-only; their S-1 claims conflict.
23. CNBC, "Rippling valued at $16.8 billion in $450 million funding round" (2025-05-09) — https://www.cnbc.com/2025/05/09/rippling-valued-at-16point8-billion-in-450-million-funding-round.html — accessed 2026-09-26 — secondary; snippet-only.
24. Rippling, "Rippling Announces Series G Fundraising and Tender Offer" — https://www.rippling.com/blog/series-g-fundraising-tender-offer — accessed 2026-09-26 — self-reported; title only.
25. Parker Conrad on X (Rippling AI; ARR over $1B, +78%) — https://x.com/parkerconrad/status/2044221628343824717 — accessed 2026-09-26 — self-reported executive statement; snippet-only; undated in snippet.
26. Sacra, "Rippling revenue, valuation & funding" — https://sacra.com/c/rippling/ — accessed 2026-09-26 — aggregator estimate; snippet-only.
27. PitchBook, Rippling company profile — https://pitchbook.com/profiles/company/178355-71 — accessed 2026-09-26 — aggregator; snippet-only (Lekko deal).
28. The Information, "Rippling CEO Confirms an IPO Ahead" — https://www.theinformation.com/briefings/rippling-ceo-confirms-an-ipo-ahead — accessed 2026-09-26 — paywalled; title only; undated.
29. Bloomberg Law, "Rippling to Advance Corporate Espionage Suit Against Deel," and the National Today mirror (2026-02-13) — https://news.bloomberglaw.com/litigation/rippling-to-advance-corporate-espionage-lawsuit-against-deel ; https://nationaltoday.com/us/ca/san-francisco/news/2026/02/13/rippling-to-advance-corporate-espionage-lawsuit-against-deel/ — accessed 2026-09-26 — secondary; snippet-only.
30. The Information, "Deel Loses Motion to Dismiss Rippling Racketeering Case" — https://www.theinformation.com/briefings/deel-loses-motion-dismiss-rippling-racketeering-case — accessed 2026-09-26 — paywalled; title only.
31. Bloomberg, "Deel Dealt Fresh Setbacks in Rippling Case Over Alleged Spying" (2026-09-26) — https://www.bloomberg.com/news/articles/2026-09-26/deel-dealt-fresh-setbacks-in-rippling-case-over-alleged-spying — accessed 2026-09-26 — secondary; snippet-only; the latest dated source on the case.
32. Rippling, "Federal Court Rejects Deel's Ploy to Evade American Justice" — https://www.rippling.com/blog/federal-court-rejects-deels-ploy-to-evade-american-justice — accessed 2026-09-26 — party to the litigation; title only.
33. Deel, "Deel's Counterclaims Against Rippling" — https://www.deel.com/blog/deel-files-lawsuit/ — accessed 2026-09-26 — party to the litigation; title only.
34. BambooHR, "BambooHR Announces BambooHR Connect 2026…" (company boilerplate) — https://www.bamboohr.com/about-bamboohr/press-release/bamboohr-announces-bamboohr-connect-2026 — accessed 2026-09-26 — self-reported; snippet-only.
35. GlobeNewswire, "BambooHR Introduces Bamboo AI™…" (2026-07-21) — https://www.globenewswire.com/news-release/2026/07/21/3330490/0/en/bamboohr-introduces-bamboo-ai-a-connected-intelligence-platform-built-to-work-while-leaders-focus-on-empowering-people.html — accessed 2026-09-26 — primary press release; snippet-only.
36. Getlatka, BambooHR — https://getlatka.com/companies/bamboohr — accessed 2026-09-26 — aggregator estimate, low quality; snippet-only.
37. Paylocity, Form 10-K FY2026 (fiscal year ended 2026-06-30) and Q4/FY2026 results release — https://www.sec.gov/Archives/edgar/data/0001591698/000159169826000069/pcty-20260630.htm ; https://investors.paylocity.com/news-releases/news-release-details/paylocity-announces-fourth-quarter-and-fiscal-2026-financial — accessed 2026-09-26 — primary (the 10-K is audited); snippet-only.
38. Paylocity, Airbase definitive agreement (2024-09-04) and completion (2024-10-01); CPA Practice Advisor (2024-09-05) — https://www.paylocity.com/company/about-us/newsroom/press-releases/paylocity-announces-definitive-agreement-to-acquire-airbase-inc/ ; https://www.globenewswire.com/news-release/2024/10/01/2956151/29665/en/paylocity-announces-completion-of-acquisition-of-airbase-inc.html ; https://www.cpapracticeadvisor.com/2024/09/05/paylocity-to-buy-airbase-in-325-million-deal/110015/ — accessed 2026-09-26 — primary press releases plus trade press; snippet-only.
39. "ADP Acquires WorkForce Software" (2024-10-15), and Accounting Today, "ADP announces acquisition of WorkForce Software" — https://www.nasdaq.com/press-release/adp-acquires-workforce-software-2024-10-15 ; https://www.accountingtoday.com/news/adp-announces-acquisition-of-workforce-software — accessed 2026-09-26 — primary press release plus trade press; snippet-only.
40. PR Newswire, "ADP® Assist with Generative AI Features Makes HCM Decisions Easy, Smart and Human" (2024-01-31) — https://www.prnewswire.com/news-releases/adp-assist-with-generative-ai-features-makes-hcm-decisions-easy-smart-and-human-302049418.html — accessed 2026-09-26 — primary press release; snippet-only.
41. ADP, "ADP® Accelerates AI Leadership with Launch of New AI Agents…" (2026-01-28) — https://mediacenter.adp.com/2026-01-28-ADP-R-Accelerates-AI-Leadership-with-Launch-of-New-AI-Agents-Designed-to-Solve-Workforce-Challenges — accessed 2026-09-26 — primary press release; title and date only.
42. CPA Practice Advisor, "ADP Announces New AI-Powered Product Enhancements at Innovation Day" (2025-09-03) — https://www.cpapracticeadvisor.com/2025/09/03/adp-announces-new-ai-powered-product-enhancements-at-innovation-day/168408/ — accessed 2026-09-26 — trade press; title and date only.
43. Apps Run The World, "Top 10 Payroll Software Vendors, Market Size and Forecast 2024-2029" — https://www.appsruntheworld.com/top-10-hcm-software-vendors-in-payroll-market-segment/ — accessed 2026-09-26 — analyst firm, proprietary model; snippet-only.
44. Mordor Intelligence, "United States Payroll Services Market" — https://www.mordorintelligence.com/industry-reports/united-states-payroll-services-market — accessed 2026-09-26 — paid report, opaque method; snippet-only; the 12% figure is ambiguous.
45. 6sense, "Paychex – Market Share, Competitor Insights in Payroll And Benefits" — https://6sense.com/tech/payroll-and-benefits/paychex-market-share — accessed 2026-09-26 — website technology detection; low quality.
46. SBA Office of Advocacy, "Frequently Asked Questions About Small Business 2026" (released 2026-02-03) — https://advocacy.sba.gov/wp-content/uploads/2026/02/FINAL_FAQsAboutSmallBusiness_2026_012826.pdf ; https://advocacy.sba.gov/2026/02/03/advocacy-releases-frequently-asked-questions-about-small-businesses-2026/ — accessed 2026-09-26 — primary, government; snippet-only.
47. IRS, "Outsourcing payroll duties" — https://www.irs.gov/businesses/small-businesses-self-employed/outsourcing-payroll-duties — accessed 2026-09-26 — primary, government; no statistic confirmed.
48. Business Wire, "Check Strengthens Market Leadership as Demand for Embedded Payroll Accelerates" (2025-05-21) — https://www.businesswire.com/news/home/20250521490831/en/Check-Strengthens-Market-Leadership-as-Demand-for-Embedded-Payroll-Accelerates — accessed 2026-09-26 — self-reported press release; snippet-only.
49. Check, "Introducing Check: Empowering Payroll Infrastructure" — https://www.checkhq.com/resources/blog/introducing-check — accessed 2026-09-26 — self-reported; snippet-only; stale (2020–21 funding).
50. Tracxn, Check company profile — https://tracxn.com/d/companies/check/__GZDinaqe3OdfjztES7p13dv0rkLJDm6QDGpyqlRofOg — accessed 2026-09-26 — aggregator; snippet-only.
51. Gusto Embedded site, vertical-SaaS page, Vagaro blog post and launch post — https://embedded.gusto.com/ ; https://embedded.gusto.com/solutions/vertical-saas ; https://embedded.gusto.com/blog/embedded-payroll-vertical-saas/ ; https://gusto.com/company-news/introducing-gusto-embedded-payroll — accessed 2026-09-26 — self-reported; snippet-only; which page carries "500,000 businesses" was not pinned.
52. Payments Dive, "JPMorgan taps Gusto to offer embedded payroll" — https://www.paymentsdive.com/news/jpmorgan-gusto-embedded-payroll-services-fintech/694349/ — accessed 2026-09-26 — secondary; title only; date not captured.
53. Salsa: Axios (2025-04-22); fintech.global (2025-04-23); Salsa blog; PYMNTS; TheSaaSNews ("Series B") — https://www.axios.com/pro/fintech-deals/2025/04/22/exclusive-embedded-payroll-startup-salsa-20m ; https://fintech.global/2025/04/23/embedded-payroll-platform-salsa-raises-20m-series-a-to-fuel-expansion/ ; https://www.salsa.dev/blog-post/our-20m-series-a-will-make-embedded-payroll-even-easier ; https://www.pymnts.com/payroll/2025/salsa-raises-20m-to-expand-embedded-payroll-services-across-us-and-canada/ ; https://www.thesaasnews.com/news/salsa-raises-20-million-in-series-b/ — accessed 2026-09-26 — press plus self-reported; snippet-only; growth claims are self-reported.
54. Zeal: Business Wire Series A announcement (2021-08-27) and Tracxn — https://www.businesswire.com/news/home/20210827005003/en/Zeal-Raises-%2413-Million-Series-A-to-Scale-API-Infrastructure-Allowing-Companies-to-Build-Custom-Payroll-Products ; https://tracxn.com/d/companies/zeal/__dH-Qc8hCUuqQiaCmwZaKXQAeVUp5v4kue06s5CtLe9I — accessed 2026-09-26 — primary press release (stale) plus aggregator; snippet-only.
55. Everee: PR Newswire (Flex Platform); PR Newswire (Onboarding+); Payments Dive; HRTechCube (Fast Company 2026 list); CB Insights — https://www.prnewswire.com/news-releases/everee-launches-the-flex-platform-real-time-payroll-with-no-pay-cycle-302599827.html ; https://www.prnewswire.com/news-releases/everee-launches-onboarding-a-premium-i-9-compliance-and-onboarding-tool-for-flexible-workforces-and-embedded-payroll-partners-302791061.html ; https://www.paymentsdive.com/news/everee-takes-on-ewa-providers/650060/ ; https://hrtechcube.com/everee-named-to-fast-companys-2026-most-innovative-companies/ ; https://www.cbinsights.com/investor/everee-1 — accessed 2026-09-26 — self-reported press releases plus press and aggregator; snippet-only; release dates not captured.
56. ADP, "ADP® Embedded Payroll Gives Partners a Competitive Edge with Integrated HCM Solution" (2025-09-29), and Investing.com — https://mediacenter.adp.com/2025-09-29-ADP-R-Embedded-Payroll-Gives-Partners-a-Competitive-Edge-with-Integrated-HCM-Solution ; https://www.investing.com/news/company-news/adp-launches-embedded-payroll-solution-for-small-business-software-93CH-4261482 — accessed 2026-09-26 — primary press release plus press; snippet-only.
57. ADP, "ADP Launches Roll™ by ADP® Mobile App…" (2021-02-25), and the Roll by ADP site — https://mediacenter.adp.com/2021-02-25-ADP-Launches-Roll-TM-by-ADP-R-Mobile-App-a-Completely-Reimagined-Way-for-Small-Businesses-to-Do-Payroll ; https://www.rollbyadp.com/ — accessed 2026-09-26 — primary; stale (2021); snippet-only.
58. Open Banking Tracker, embedded-finance listings (Rollfi) — https://www.openbankingtracker.com/embedded-finance/recently-added — accessed 2026-09-26 — directory; snippet-only; the Rollfi description came from a search summary whose results included this page, so the attribution is not certain.
59. Statistics-aggregator pages on payroll outsourcing (B2B Reviews; Digital Minds BPO) — https://www.b2breviews.com/what-percentage-of-companies-outsource-payroll/ ; https://digitalmindsbpo.com/blog/payroll-outsourcing-statistics-and-trends/ — accessed 2026-09-26 — low quality, no stated method; snippet-only; cited only to show why they were excluded.
60. TechEdge AI, "Gusto Launches Cofounder, an AI Teammate…" — https://techedgeai.com/gusto-launches-cofounder-an-ai-teammate-that-automates-small-business-payroll-and-compliance/ — accessed 2026-09-26 — low-quality outlet; title only; unverified.
61. Sacra, Gusto profile, and Wikipedia, "Gusto, Inc." — https://sacra.com/c/gusto/ ; https://en.wikipedia.org/wiki/Gusto,_Inc. — accessed 2026-09-26 — aggregator and tertiary; appeared in the result set that produced the $9.3B / $200M / June 2025 tender snippet; the primary announcement was not seen.
62. Wikipedia, "Rippling (company)" — https://en.wikipedia.org/wiki/Rippling_(company) — accessed 2026-09-26 — tertiary; appeared in the result set that gave the 2025-03-17 N.D. Cal. filing date; corroborate against the docket.

---

## 3. Regulatory lens A — payroll tax compliance (IRS/SSA/Treasury), 2025–2026

Researched by a dedicated pass (25 searches, mostly restricted to irs.gov,
ssa.gov, treasury.gov and eftps.gov; fetches blocked). IRS pages now file the
OBBBA provisions under **"Working Families Tax Cuts"** [1]; search under that
name.

**Bottom line (analysis):** the 2025–2026 calendar confirms the 09-03 audit's
rule ("dated and configurable, never a constant") and sharpens it. Each value
must be keyed to the date that legally governs it:
- 1099s: the **payment date**.
- Social Security wage base: the **calendar year of the wages**.
- Roth catch-up: **prior-year FICA wages**.

SAIRNbiz's hardcoded $600 is right for 2025 payments and wrong for 2026
payments (F1). Values with no scheduled indexing also changed by statute this
cycle.

### 3.1 One Big Beautiful Bill Act (P.L. 119-21, signed 2025-07-04)

**a. 1099-NEC / 1099-MISC threshold: $600 → $2,000.**
- IRS: "The reporting threshold in section 6041(a) increased to a base
  threshold of $2,000 for payments made after December 31, 2025, with the
  threshold indexed for inflation for calendar years after 2026" [2][3][4].
- 2025 payments, filed in early 2026, stay at $600.
- Backup withholding follows the §6041(a) threshold [4][5].
- Proposed regulations REG-113229-25 were published 2026-04-17 [5]; no final
  regulations were found.
- *Changes on a schedule:* a one-time step on 2026-01-01, then annual CPI
  indexing from 2027 (rounded to the nearest $100, per secondary sources)
  [6][7].

**b. Form 1099-K** reverted, retroactively, to the pre-ARPA threshold: gross
payments over $20,000 **and** more than 200 transactions [9][10]. No indexing
was found.

**c. "No tax on tips" / "no tax on overtime" (tax years 2025–2028).**
- Employees claim both as income-tax deductions.
- Qualified overtime is **only the FLSA §7 premium**, the "half" of
  time-and-a-half [12].
- Tax year 2025 was a transition year. Notice 2025-62 waives penalties for not
  separately reporting these amounts, provided the return is otherwise correct
  [17][18].
- **The 2026 Form W-2 adds** [20]:
  - box 12 **code TP**: cash tips reported to the employer;
  - box 12 **code TT**: qualified overtime compensation;
  - box 12 **code TA**: Trump-account employer contributions;
  - **box 14b**: Treasury Tipped Occupation Codes.
- The 2026 Form W-4 adds these items to its Deductions Worksheet [21].
- *Relevance (analysis):* from tax year 2026, any product that supplies W-2
  data must carry the FLSA overtime premium as its own figure (F2).

**d. Other payroll-relevant items:**
- Dependent-care exclusion rises to $7,500 for 2026 [22][23].
- The §45F childcare credit rises to a $500K cap ($600K for small businesses)
  at 40%/50% from tax year 2026 [24].
- Employer Trump-account contributions of up to $2,500 are allowed from
  2026-07-04 [25][26].

### 3.2 Wage base, Additional Medicare Tax, FUTA credit reductions

- **Social Security wage base:** $176,100 for 2025 and **$184,500 for 2026**
  [27][28][29]. It rises every year, announced in October. Applying the cap
  needs per-employee year-to-date wages, which SAIRNbiz does not store; it
  discloses this on screen.
- **Additional Medicare Tax:** 0.9% withheld on wages over **$200,000** in a
  calendar year; not indexed [30]. SAIRNbiz does not model it and does not say
  so (F3).
- **FUTA credit reductions for 2025,** paid with the 2025 Form 940 (due
  2026-02-02): **California 1.2%** (up to $126 per employee) and **U.S. Virgin
  Islands 4.5%** [31][32]. DOL redetermines the list every November.

### 3.3 SECURE 2.0 §603: mandatory Roth catch-up

- Final regulations: 2025-09-16 [34].
- In practice the rule applies from 2026-01-01: catch-up contributions must be
  Roth if the employee's **2025 FICA wages from the plan sponsor exceeded
  $150,000** [33][37][38].
- Payroll must look up prior-year wages for each participant aged 50 or over,
  and route catch-up deferrals as after-tax Roth [35][36].

### 3.4 E-filing and 2026 forms

- **The 10-return rule:** since 2024, filers of 10 or more information returns
  in total, **W-2s included**, must e-file. W-2s go to SSA [39][40].
- **FIRE retirement:** the last FIRE filing is **2026-11-19, 3 p.m. ET**. From
  **2027-01-01, IRIS is the only e-file system** for information returns, and
  filing tax-year-2026 returns needs an IRIS TCC [41][42].
- **Form 941 (Rev. March 2026):** refunds by direct deposit, and a new
  aggregate-filer section for §3504 agents and CPEOs. Which revision first
  introduced each item is unconfirmed [29].
- **Pub 15-T (2026):** carries the percentage-method withholding tables that
  automated payroll uses. It is reissued every year [44].

### 3.5 When a payroll provider fails, the employer stays liable

- IRS: "In the event of default by a third party, the employer remains
  responsible for the deposit of the federal tax liabilities and timely filing
  of returns" [46][47].
- A **reporting agent** (Form 8655) files and deposits under the client's EIN
  and "assumes no liability" [48].
- A **§3504 agent** (Form 2678) shares liability with the employer [48][49].
- A **CPEO** takes responsibility for employment taxes on the wages it pays
  [47][48].
- *Design implication (analysis):* an embedded payroll product that files
  under the client's EIN is at most a reporting agent, so its failures fall on
  its customers. Only a §3504 or CPEO arrangement shares or moves liability.
  SAIRNbiz holds none of these roles today.

### 3.6 Other Treasury/IRS changes

- Executive Order 14247 (2025-03-25) ended most paper refund checks to
  individuals after 2025-09-30, and direct deposit is being added to business
  returns [52][53].
- Businesses keep EFTPS for deposits [56].
- Net effect: no change to how employers make deposits.

### 3.7 Summary table

| Value | 2025 | 2026 | Changes how often | Src |
|---|---|---|---|---|
| 1099-NEC/MISC threshold (by payment date) | $600 | **$2,000** | Annually from 2027 (CPI) | 2–7 |
| Social Security wage base | $176,100 | $184,500 | Annually | 27–29 |
| Additional Medicare Tax threshold | $200,000 | $200,000 | Not indexed | 30 |
| FUTA credit reductions | CA 1.2%, USVI 4.5% | Set Nov 2026 | Annually | 31, 32 |
| Roth catch-up threshold (prior-year FICA wages) | transition | $150,000 | Annually | 33–38 |
| W-2 box 12 TP/TT/TA and box 14b | not on form (relief) | required | Annual form revision | 17, 18, 20 |
| Information-return e-file threshold | 10 (all forms) | 10 (all forms) | By regulation | 39, 40 |
| Information-return e-file channel | FIRE or IRIS | FIRE ends 2026-11-19; IRIS-only from 2027-01-01 | One-time | 41, 42 |

**Not researched (search cap):** tip-reporting boxes on the 2026
1099-NEC/MISC/K; the e-file waiver form; a primary source for the tips window;
the 2027 wage base.

### Sources (§3)

All were accessed 2026-09-26. None was opened directly: fetches to irs.gov, ssa.gov and federalregister.gov were blocked. Everything below is snippet-only unless marked "title only".

1. IRS — Working Families Tax Cuts — https://www.irs.gov/newsroom/working-families-tax-cuts — primary; title only.
2. IRS — Instructions for Forms 1099-MISC and 1099-NEC (Rev. Dec 2026) — https://www.irs.gov/instructions/i1099mec — primary; snippet.
3. IRS — Publication 1099 (2026) — https://www.irs.gov/publications/p1099 — primary; snippet.
4. IRS — Internal Revenue Bulletin 2026-19 (May 4, 2026) — https://www.irs.gov/irb/2026-19_IRB — primary; snippet; that it contains REG-113229-25 is inferred.
5. Federal Register — "Increase in Threshold for Requiring Information Reporting With Respect to Certain Payees…" (REG-113229-25, FR Doc. 2026-07519, Apr 17, 2026) — https://www.federalregister.gov/documents/2026/04/17/2026-07519/increase-in-threshold-for-requiring-information-reporting-with-respect-to-certain-payees-extension — primary; fetch blocked; snippet.
6. TaxBandits — "The $2,000 Backup Withholding Threshold…" — https://blog.taxbandits.com/the-2000-backup-withholding-threshold-what-changed-for-w-9-collection-in-2026/ — secondary; snippet.
7. Beancount.io — "Backup Withholding Threshold Jumped to $2,000 in 2026" — https://beancount.io/blog/2026/08/06/backup-withholding-threshold-600-to-2000-contractor-payments-guide — secondary; snippet.
8. WhippleWood — "$2,000 1099 Threshold for 2026" — https://whipplewood.com/insights/new-2000-1099-threshold-2026/ — secondary; snippet; the §70433 citation came from this result set but is not pinned to this page.
9. IRS news release — "IRS issues FAQs on Form 1099-K threshold under the OBBB; dollar limit reverts to $20,000" — https://www.irs.gov/newsroom/irs-issues-faqs-on-form-1099-k-threshold-under-the-one-big-beautiful-bill-dollar-limit-reverts-to-20000 — primary; snippet.
10. IRS — Form 1099-K FAQs: General information — https://www.irs.gov/newsroom/form-1099-k-faqs-general-information — primary; snippet.
11. IRS news release — proposed regulations on the backup-withholding threshold for payments made through third parties — https://www.irs.gov/newsroom/treasury-irs-issue-proposed-regulations-reflecting-changes-from-the-one-big-beautiful-bill-to-the-threshold-for-backup-withholding-on-certain-payments-made-through-third-parties — primary; title only.
12. IRS — Q&A about the new deduction for qualified overtime compensation — https://www.irs.gov/newsroom/questions-and-answers-about-the-new-deduction-for-qualified-overtime-compensation — primary; snippet.
13. IRS news release — final regulations listing occupations that customarily receive tips — https://www.irs.gov/newsroom/treasury-irs-issue-final-regulations-listing-occupations-where-workers-customarily-and-regularly-receive-tips-under-the-one-big-beautiful-bill — primary; snippet; issue date not captured.
14. U.S. Treasury press release sb0258 — "No Tax on Tips" proposed regulations — https://home.treasury.gov/news/press-releases/sb0258 — primary; snippet; not pinned.
15. HR Morning — "TY 2026 W-2: IRS Finalizes New Box 12 Codes, Box 14 Tweak" — https://www.hrmorning.com/news/w-2-box-codes-irs-update/ — secondary; snippet; not pinned.
16. WhippleWood — "W-2 Box 12 Code TT and TP: 2026 Employer Reporting Rules" — https://whipplewood.com/insights/tips-overtime-2026-employer-reporting-w2-box12/ — secondary; snippet; not pinned.
17. IRS news release — penalty relief for TY2025 information reporting on tips and overtime — https://www.irs.gov/newsroom/treasury-irs-provide-penalty-relief-for-tax-year-2025-for-information-reporting-on-tips-and-overtime-under-the-one-big-beautiful-bill — primary; snippet.
18. IRS Notice 2025-62 — https://www.irs.gov/pub/irs-drop/n-25-62.pdf — primary; snippet.
19. IRS Notice 2025-69 — https://www.irs.gov/pub/irs-drop/n-25-69.pdf — primary; title only.
20. IRS — General Instructions for Forms W-2 and W-3 (2026) — https://www.irs.gov/instructions/iw2w3 (PDF: https://www.irs.gov/pub/irs-pdf/iw2w3.pdf) — primary; snippet.
21. IRS — Form W-4 (2026) — https://www.irs.gov/pub/irs-pdf/fw4.pdf — primary; snippet.
22. IRS — Publication 15-B (2026) — https://www.irs.gov/pub/irs-prior/p15b--2026.pdf — primary; snippet; not pinned.
23. IRS — Internal Revenue Bulletin 2026-37 — https://www.irs.gov/irb/2026-37_irb — primary; snippet; not pinned.
24. IRS — Employer-provided child care credit: tax year 2026 and later — https://www.irs.gov/businesses/small-businesses-self-employed/employer-provided-child-care-credit-tax-year-2026-and-later — primary; snippet.
25. IRS news release — Trump Accounts guidance (Notice 2025-68: https://www.irs.gov/pub/irs-drop/n-25-68.pdf) — https://www.irs.gov/newsroom/treasury-irs-issue-guidance-on-trump-accounts-established-under-the-working-families-tax-cuts-notice-announces-upcoming-regulations — primary; snippet.
26. IRS news release — proposed regulations on employer contributions to Trump Accounts — https://www.irs.gov/newsroom/treasury-irs-issue-proposed-regulations-on-employer-contributions-to-trump-accounts-under-the-working-families-tax-cuts — primary; snippet; the Aug 11, 2026 date comes from the search summary.
27. SSA — 2026 COLA Fact Sheet — https://www.ssa.gov/news/en/cola/factsheets/2026.html — primary; snippet.
28. SSA press release (Oct 24, 2025) — "Social Security Announces 2.8 Percent Benefit Increase for 2026" — https://www.ssa.gov/news/en/press/releases/2025-10-24.html — primary; title/snippet.
29. IRS — Instructions for Form 941 (Rev. March 2026) — https://www.irs.gov/instructions/i941 — primary; snippet.
30. IRS — Questions and answers for the Additional Medicare Tax — https://www.irs.gov/businesses/small-businesses-self-employed/questions-and-answers-for-the-additional-medicare-tax — primary; snippet.
31. Federal Register — Notice of FUTA Credit Reductions Applicable for 2025 (FR Doc. 2026-00342, Jan 12, 2026) — https://www.federalregister.gov/documents/2026/01/12/2026-00342/notice-of-the-federal-unemployment-tax-act-futa-credit-reductions-applicable-for-2025 — primary; title only.
32. American Payroll Association — "California, Virgin Islands Face FUTA Credit Reduction for 2025" (Nov 11, 2025) — https://payroll.org/news-resources/news/news-detail/2025/11/11/california-virgin-islands-face-futa-credit-reduction-for-2025 — secondary; snippet.
33. IRS news release (eitc.irs.gov mirror) — final regulations on the new Roth catch-up rule — https://www.eitc.irs.gov/newsroom/treasury-irs-issue-final-regulations-on-new-roth-catch-up-rule-other-secure-2point0-act-provisions — primary; snippet.
34. Federal Register — "Catch-Up Contributions" final rule (FR Doc. 2025-17865, Sept 16, 2025) — https://www.federalregister.gov/documents/2025/09/16/2025-17865/catch-up-contributions — primary; title only.
35. ASPPA — "Final Roth Catch-Up Regulations Issued by IRS" — https://www.asppa-net.org/news/2025/9/final-roth-catch-up-regulations-issued-by-irs/ — secondary; snippet; not pinned.
36. Groom Law Group — "IRS Issues Final Regulations on Catch-Up Rule Changes" — https://www.groom.com/resources/irs-issues-final-regulations-on-catch-up-rule-changes/ — secondary; snippet; not pinned.
37. IRS Notice 2025-67 (2026 retirement plan amounts) — https://www.irs.gov/pub/irs-drop/n-25-67.pdf — primary; title only.
38. IRS news release — "401(k) limit increases to $24,500 for 2026" — https://www.irs.gov/newsroom/401k-limit-increases-to-24500-for-2026-ira-limit-increases-to-7500 — primary; title/snippet.
39. IRS — E-file information returns — https://www.irs.gov/filing/e-file-information-returns — primary; snippet.
40. IRS — Topic no. 801 — https://www.irs.gov/taxtopics/tc801 — primary; snippet.
41. IRS news release — "IRS reminder: Information return e-file system transitioning to a new platform" — https://www.irs.gov/newsroom/irs-reminder-information-return-e-file-system-transitioning-to-a-new-platform — primary; snippet.
42. IRS — Filing Information Returns Electronically (FIRE) — https://www.irs.gov/e-file-providers/filing-information-returns-electronically-fire — primary; snippet.
43. IRS — Publication 1220 (Rev. 5-2026) — https://www.irs.gov/pub/irs-pdf/p1220.pdf — primary; title only.
44. IRS — Publication 15-T (2026) — https://www.irs.gov/publications/p15t — primary; snippet.
45. IRS — Publication 1141 / Rev. Proc. 2026-27 — https://www.irs.gov/pub/irs-pdf/p1141.pdf — primary; title only.
46. IRS — Outsourcing payroll duties — https://www.irs.gov/Businesses/Small-Businesses-&-Self-Employed/Outsourcing-Payroll-Duties — primary; snippet.
47. IRS — Outsourcing payroll and third-party payers — https://www.irs.gov/businesses/small-businesses-self-employed/outsourcing-payroll-and-third-party-payers — primary; snippet.
48. IRS — Third party payer arrangements: payroll service providers and reporting agents — https://www.irs.gov/government-entities/third-party-payer-arrangements-payroll-service-providers-and-reporting-agents — primary; snippet.
49. IRS — Third party payer arrangements: Section 3504 agents — https://www.irs.gov/government-entities/federal-state-local-governments/third-party-payer-arrangements-section-3504-agents — primary; snippet.
50. IRS — IRM 5.1.24, Third-Party Payer Arrangements — https://www.irs.gov/irm/part5/irm_05-001-024r — primary; title only.
51. IRS news — "Picking the right third-party payroll service provider helps protect businesses" — https://www.irs.gov/newsroom/picking-the-right-third-party-payroll-service-provider-helps-protect-businesses — primary; title only.
52. IRS — Q&A about Executive Order 14247 (also FS-2026-02: https://www.irs.gov/pub/taxpros/fs-2026-02.pdf) — https://www.irs.gov/newsroom/questions-and-answers-about-executive-order-14247-modernizing-payments-to-and-from-americas-bank-account — primary; snippet; not pinned.
53. IRS — Modernizing payments to and from America's bank account — https://www.irs.gov/newsroom/modernizing-payments-to-and-from-americas-bank-account — primary; snippet.
54. Thomson Reuters — "IRS phaseout of paper refund checks" — https://tax.thomsonreuters.com/blog/irs-phaseout-of-paper-check-refund/ — secondary; snippet.
55. Brown Plus — "Federal Electronic Payments: An Update… for 2026" — https://www.brownplus.com/blog/federal-electronic-payments-2026/ — secondary; snippet.
56. EFTPS (Treasury) — Welcome to EFTPS online — https://www.eftps.gov/eftps/ — primary; snippet.

---

## 4. Regulatory lens B — employment-law compliance (DOL, USCIS/E-Verify, states), 2025–2026

Researched by a dedicated pass (24 searches; all four fetches blocked; **no page
read directly**). Item 4.6 is essentially unresearched because the cap was hit.

### 4.1 Form I-9

- **Current edition:** 01/20/25, released 2025-04-03, expiring **05/31/2027**
  [1][2][4]. The 08/01/23 printing that expires 07/31/2026 is **no longer
  valid** [2][5].
- **Remote examination:** DHS's alternative procedure is still in effect, but
  only for employers enrolled in **and in good standing with** E-Verify. It
  requires a live video interaction [6][7][8].
- **Penalties** (DHS inflation rule, effective 2025-01-02):
  - paperwork violations: **$288–$2,861 per form**;
  - knowingly hiring, first offense: $716–$5,724 per worker;
  - third or later offense: $8,586–$28,619 per worker [10][11][12].

  **No 2026 adjustment:** OMB M-26-11 (April 2026) cancelled the 2026
  inflation adjustments [13] (title and search summary only).
- **ICE reclassification, 2026-03-16:** ICE updated its inspection fact sheet,
  without rulemaking, to move **more than ten error types from "technical" to
  "substantive"** [14][15][16][9]. A technical error could be fixed within the
  statutory 10-day window. A substantive one is fined immediately. For an HR
  product, errors caught at entry are now worth far more than errors found
  later.
- **Enforcement volume:** secondary figures (for example 12,000–15,000 audits in
  2025, "10x" 2024) **do not reconcile with each other** and are not used
  [17][18][19][20].

### 4.2 E-Verify

States requiring it of private employers (from secondary 2026 guides):

| States | Threshold | Src |
|---|---|---|
| Alabama, Arizona, Mississippi, South Carolina | All employers | [21][24] |
| Florida | 25+ employees | [21][22][23] |
| Georgia | More than 10 employees | [21][22][23] |
| North Carolina | 25+ employees | [21][22][23] |
| Tennessee | 35+ employees | [21][22][23] |
| Utah | 150+ employees | [21][22][23] |

- **New: Ohio's E-Verify Workforce Integrity Act,** effective **2026-03-19.**
  It covers contractors, subcontractors and labor brokers **of any size** doing
  nonresidential construction in Ohio [26][27]. This is relevant to SAIRN's
  construction and trade verticals. SAIRNbiz's own demo content assumes an
  Ohio employer ("BWC Ohio", `sairnbiz.html:708`).
- **E-Verify+** has been available nationwide since 2025-08-26, but **not
  through Web Services or E-Verify Employer Agents** [28][29]. A third-party HR
  product can integrate only classic E-Verify.
- **October 2025 shutdown:** E-Verify was offline from 2025-10-01 to 2025-10-07.
  Those days did not count toward the three-business-day limit, and affected
  cases were due by 2025-10-14 [30]–[34].
- **February 2026 DHS funding lapse:** sources conflict on whether E-Verify
  stayed up. This is unresolved [35][36][37].

### 4.3 Worker classification

- **FAB 2025-1 (2025-05-01):** WHD stopped applying the 2024
  independent-contractor rule in its own enforcement. **The 2024 rule still
  binds in private lawsuits** [38][39][40].
- **Proposed replacement** published 2026-02-27 at **91 FR 9932**
  (RIN 1235-AA46). It restores a modified "core factors" test and applies it
  to the FLSA, FMLA and MSPA [41]–[45]. **No final rule was found.**
- **New Jersey's ABC-test regulations** (N.J.A.C. 12:11) take effect
  **2026-10-01**. A worker is presumed to be an employee unless the business
  proves all three prongs [47][48][49].
- A W-9 flag on a vendor record is a tax-form fact, not a classification.

### 4.4 Overtime

- **Federal exempt salary floor: $684/week.** The 2024 rule was vacated
  nationwide on 2024-11-15 (*Texas v. DOL* / *Plano Chamber v. DOL*, E.D.
  Tex.) [51][52][53]. The appeals were stayed or dismissed [54][55][56].
- **Daily-overtime states** (confirmed; the list may not be complete):

| State | Rule |
|---|---|
| California | 1.5× over 8 h/day; **2× over 12 h/day**; 2× beyond 8 h on the **seventh consecutive day** [57][58] |
| Alaska | 1.5× over 8 h/day or 40 h/week [58] |
| Nevada | 1.5× over 8 h in 24 h, only for employees paid under 1.5× minimum wage; a written 4×10 agreement removes the trigger [59][60] |
| Colorado | 1.5× over 40 h/week, **12 h/day**, or 12 consecutive hours, whichever pays more [61] |

SAIRNbiz's hardcoded 40-hour weekly rule undercounts in all four (F2).

### 4.5 State programs with 2026 payroll impact

- **Paid family and medical leave:**
  - **Minnesota:** contributions and benefits both started 2026-01-01, premium
    **0.88%** [62][63].
  - **Delaware:** benefits started 2026-01-01; **0.8%** for employers with 25+
    staff, 0.32% (parental leave only) for 10–24 [64][65][66][67].
  - **Maine:** benefits start 2026-05-01; **1.0%** for 15+ employees, 0.5% below
    that [65][66][67].
  - **Maryland:** delayed to 2027 contributions and 2028 benefits [66][67].
- **Minimum wage:** **19 states** raised theirs on 2026-01-01 (EPI; Axios)
  [68][69].
- **Pay transparency in postings** (secondary; check the dates before quoting):
  Illinois, Minnesota, New Jersey, Vermont and Massachusetts in 2025; Virginia
  and Maine reported for 2026 [70][71][72]. SAIRNbiz publishes no postings, so
  these bind it only if it ever does.

### 4.6 DOL guidance on timekeeping software

**Not researched** (search cap). None of these was checked: whether FAB 2024-1
(AI and automated timekeeping) is still in effect; the 2025 revival of opinion
letters; the PAID program; guidance on auto-deduction and rounding. The only
lead is a title: "US Department of Labor Rolls Back Biden-Era FLSA Practices"
(Morgan Lewis, July 2025) [73]. **Do not cite any of these as fact from this
section.**

**Also not re-verified:** the FAR E-Verify clause; California AB5; the I-9
second-offense penalty range; any primary ICE count of Notices of Inspection.

### Sources (§4)

All sources are **snippet-only; none were read directly** (WebFetch was blocked).
1. SHRM, "USCIS Releases New Form I-9" — https://www.shrm.org/topics-tools/news/talent-acquisition/uscis-releases-new-form-i9 — accessed 2026-09-26 — secondary; snippet-only.
2. USCIS I-9 Central, "Minor Changes to Form I-9 and E-Verify Updates" — https://www.uscis.gov/i-9-central/form-i-9-related-news/minor-changes-to-form-i-9-and-e-verify-updates — accessed 2026-09-26 — primary; snippet-only (uscis.gov fetch blocked).
3. E-Verify, "Minor Changes to Form I-9 and E-Verify Updates" — https://www.e-verify.gov/about-e-verify/whats-new/minor-changes-to-form-i-9-and-e-verify-updates — accessed 2026-09-26 — primary; snippet-only.
4. McGuireWoods, "Employers Take Note: USCIS Issues New Form I-9 Edition" (Apr 2025) — https://www.mcguirewoods.com/client-resources/alerts/2025/4/employers-take-note-uscis-issues-new-form-i-9-edition/ — accessed 2026-09-26 — secondary; snippet-only.
5. Workwise Compliance, "Agency Publishes Updated Form I-9 Guidance For Employers" — https://www.workwisecompliance.com/blog/agency-publishes-form-i-9-updates-previous-versions-still-valid.html — accessed 2026-09-26 — secondary; snippet-only.
6. USCIS, "New Form I-9 Now Includes Alternative Procedure for E-Verify Employers to Remotely Examine Employee Documents" — https://www.uscis.gov/i-9-central/form-i-9-related-news/new-form-i-9-now-includes-alternative-procedure-for-e-verify-employers-to-remotely-examine-employee — accessed 2026-09-26 — primary; snippet-only.
7. USCIS Handbook M-274 §4.5, "Remote Document Examination (Optional Alternative Procedure)" — https://www.uscis.gov/i-9-central/form-i-9-resources/handbook-for-employers-m-274/40-completing-section-2-employer-review-and-verification/45-remote-document-examination-optional-alternative-procedure-to-physical-document-examination — accessed 2026-09-26 — primary; snippet-only.
8. EMP Trust HR, "Remote Form I-9 Verification in 2026" — https://www.emptrust.com/remote-form-i-9-verification-in-2026-requirements-e-verify-rules-and-compliance-changes/ — accessed 2026-09-26 — secondary; snippet-only.
9. i-9intelligence, "Form I-9 in 2026: The Current Edition and What ICE Changed" — https://www.i-9intelligence.com/articles/i-9-form-2026 — accessed 2026-09-26 — secondary (vendor); snippet-only.
10. Federal Register, DHS "Civil Monetary Penalty Adjustments for Inflation" (Jan 2, 2025; FR Doc. 2024-31204) — https://www.federalregister.gov/documents/2025/01/02/2024-31204/civil-monetary-penalty-adjustments-for-inflation — accessed 2026-09-26 — primary; snippet-only (federalregister.gov fetch blocked).
11. eCFR, 8 CFR 274a.10 "Penalties" — https://www.ecfr.gov/current/title-8/chapter-I/subchapter-B/part-274a/subpart-A/section-274a.10 — accessed 2026-09-26 — primary; snippet-only.
12. i-9intelligence, "I-9 Penalty Amounts 2026: $288 to $28,619 Per Violation" — https://www.i-9intelligence.com/articles/i-9-penalties-2026 — accessed 2026-09-26 — secondary; title/snippet.
13. OMB M-26-11, "Cancellation of Penalty Inflation Adjustments for 2026" — https://www.whitehouse.gov/wp-content/uploads/2026/04/M-26-11-Cancellation-of-Penalty-Inflation-Adjustments-for-2026-Regarding-the-Federal-Civil-Penalties-Inflation-Adjustment-Act-Improvements-Act-of-2015.pdf — accessed 2026-09-26 — primary; title plus search summary only.
14. ICE, "Form I-9 Inspection Under Immigration and Nationality Act § 274A" — https://www.ice.gov/factsheets/i9-inspection — accessed 2026-09-26 — primary; snippet-only.
15. Morgan Lewis, "ICE Rewrites the Rules on Form I-9 Violations" (Apr 2026) — https://www.morganlewis.com/pubs/2026/04/ice-rewrites-the-rules-on-form-i-9-violations — accessed 2026-09-26 — secondary; snippet-only.
16. Quarles, "Top 5 Things Employers Should Know About ICE's Recent Form I-9 Enforcement Changes" — https://www.quarles.com/newsroom/publications/top-5-things-employers-should-know-about-ices-recent-form-i-9-enforcement-changes — accessed 2026-09-26 — secondary; snippet-only.
17. Greenspoon Marder, "U.S. Immigration Compliance Statistics for 2025-2026" — https://www.gmlaw.com/news/u-s-immigration-compliance-statistics-for-2025-2026/ — accessed 2026-09-26 — secondary; snippet-only, figures not pinned.
18. i-9intelligence, "ICE Raids & I-9 Audits 2025-2026" — https://www.i-9intelligence.com/articles/ice-worksite-enforcement-tracker — accessed 2026-09-26 — secondary; snippet-only, figures not pinned.
19. OnBlick, "ICE I-9 Audits in 2026: Higher Penalties and Stricter Rules" — https://www.onblick.com/blogs/ice-i-9-audit-risk-rising-higher-penalties-and-new-rules-in-2026 — accessed 2026-09-26 — secondary; snippet-only, figures not pinned.
20. ICE (archived), "ICE delivers more than 5,200 I-9 audit notices to businesses across the US in 2-phase nationwide operation" — https://www.ice.gov/news/releases/ice-delivers-more-5200-i-9-audit-notices-businesses-across-us-2-phase-nationwide — accessed 2026-09-26 — primary; title only, undated in snippet.
21. Lattice, "2026 E-Verify Requirements by State" — https://lattice.com/articles/e-verify-requirements-by-state — accessed 2026-09-26 — secondary; snippet-only.
22. WorkBright, "E-Verify requirements by State" — https://workbright.com/blog/e-verify-requirements-by-state-a-complete-guide-for-employers/ — accessed 2026-09-26 — secondary; snippet-only.
23. Jimerson Birr, "E-Verify Update: Changing State Rules You Should Watch in 2026" (June 2026) — https://www.jimersonfirm.com/blog/2026/06/e-verify-update-changing-state-rules-you-should-watch-in-2026/ — accessed 2026-09-26 — secondary; snippet-only.
24. Experian, "E-Verify State-by-State Requirements" — https://www.experian.com/blogs/employer-services/e-verify-state-by-state-requirements/ — accessed 2026-09-26 — secondary; snippet-only.
25. i-9intelligence, "E-Verify Requirements by State (2026)" — https://www.i-9intelligence.com/e-verify-requirements-by-state — accessed 2026-09-26 — secondary; snippet-only.
26. Vorys, "Ohio Enacts New E-Verify Law for Nonresidential Construction Contractors Effective March 19, 2026" — https://www.vorys.com/publication-ohio-enacts-new-e-verify-law-for-nonresidential-construction-contractors-effective-march-19-2026 — accessed 2026-09-26 — secondary; snippet-only.
27. Littler, "Ohio's E-Verify Law for Nonresidential Construction Contractors Takes Effect Soon" — https://www.littler.com/news-analysis/asap/ohios-e-verify-law-nonresidential-construction-contractors-takes-effect-soon — accessed 2026-09-26 — secondary; snippet-only.
28. E-Verify, "E-Verify+" — https://www.e-verify.gov/plus — accessed 2026-09-26 — primary; snippet-only.
29. E-Verify, "E-Verify+: the 'Plus' Means More for Employment Eligibility Verification!" — https://www.e-verify.gov/about-e-verify/whats-new/e-verify-the-plus-means-more-for-employment-eligibility-verification — accessed 2026-09-26 — primary; snippet-only.
30. DeWitt LLP, "E-Verify Temporarily Unavailable During Government Shutdown" (Oct 2, 2025) — https://dewittllp.com/news/2025/10/02/e-verify-temporarily-unavailable-during-government-shutdown — accessed 2026-09-26 — secondary; snippet-only.
31. Seyfarth Shaw, "USCIS Suspends E-Verify Amid Government Shutdown" — https://www.seyfarth.com/news-insights/uscis-suspends-e-verify-amid-government-shutdown.html — accessed 2026-09-26 — secondary; snippet-only.
32. Ogletree, "E-Verify Resumes Operations After Government Shutdown Hiatus" — https://ogletree.com/insights-resources/blog-posts/e-verify-resumes-operations-after-government-shutdown-hiatus/ — accessed 2026-09-26 — secondary; snippet-only.
33. Experian, "E-Verify Resumes Operation During Government Shutdown: Employer Guidance" — https://www.experian.com/blogs/employer-services/navigating-e-verify-during-government-shutdown/ — accessed 2026-09-26 — secondary; snippet-only.
34. i-9intelligence, "Is E-Verify Back Up? Shutdown Status Updates (2025–2026)" — https://www.i-9intelligence.com/articles/e-verify-government-shutdown-2025 — accessed 2026-09-26 — secondary; snippet-only.
35. Equifax Workforce Solutions, "Government Shutdown 2026: E-Verify Availability and Practical Takeaways for Employers" — https://workforce.equifax.com/all-blogs/-/post/government-shutdown-2026-e-verify-availability-and-practical-takeaways-for-employers — accessed 2026-09-26 — secondary; snippet-only, conflicting summary.
36. VisaPro, "DHS Shutdown Immigration Services 2026: USCIS, PERM, and E-Verify Impact" — https://www.visapro.com/2026/dhs-shutdown-immigration-services-2026/ — accessed 2026-09-26 — secondary; snippet-only.
37. DHS, "Lapse in Funding for DHS" — https://www.dhs.gov/publication/lapse-funding-dhs — accessed 2026-09-26 — primary; title only.
38. DOL WHD, Field Assistance Bulletin No. 2025-1 (May 1, 2025) — https://www.dol.gov/sites/dolgov/files/WHD/fab/fab2025-1.pdf — accessed 2026-09-26 — primary; snippet-only (dol.gov fetch blocked).
39. DOL news release, "US Department of Labor issues guidance on independent contractor misclassification enforcement" (May 1, 2025) — https://www.dol.gov/newsroom/releases/whd/whd20250501 — accessed 2026-09-26 — primary; title/snippet.
40. WTW, "DOL pauses enforcement of Biden-era independent contractor regulations" (June 2025) — https://www.wtwco.com/en-us/insights/2025/06/dol-pauses-enforcement-of-biden-era-independent-contractor-regulations — accessed 2026-09-26 — secondary; snippet-only.
41. Federal Register, proposed rule "Employee or Independent Contractor Status Under the FLSA, FMLA, and MSPA" (Feb 27, 2026; FR Doc. 2026-03962) — https://www.federalregister.gov/documents/2026/02/27/2026-03962/employee-or-independent-contractor-status-under-the-fair-labor-standards-act-family-and-medical — accessed 2026-09-26 — primary; snippet-only (fetch blocked).
42. DOL WHD, proposed rule page, RIN 1235-AA46 — https://www.dol.gov/agencies/whd/flsa/misclassification/2026rulemaking — accessed 2026-09-26 — primary; snippet-only.
43. Regulations.gov, docket WHD-2026-0001-0001 — https://www.regulations.gov/document/WHD-2026-0001-0001 — accessed 2026-09-26 — primary; title only.
44. Mayer Brown, "DOL Proposes New Independent Contractor Rule to Replace Biden-Era Regulation" (Mar 2026) — https://www.mayerbrown.com/en/insights/publications/2026/03/dol-proposes-new-independent-contractor-rule-to-replace-biden-era-regulation — accessed 2026-09-26 — secondary; snippet-only.
45. Paul Hastings, "DOL Proposes to Rescind Biden-Era Independent Contractor Rule and Restore 'Core Factor' Analysis" — https://www.paulhastings.com/insights/client-alerts/dol-proposes-to-rescind-biden-era-independent-contractor-rule-and-restore-core-factor-analysis — accessed 2026-09-26 — secondary; snippet-only.
46. Evening Star Bookkeeping, "Employee or Independent Contractor? The 2026 DOL Test" — https://www.eveningstarbookkeeping.com/insights/independent-contractor-vs-employee-2026 — accessed 2026-09-26 — secondary (low weight); snippet-only; the "still a proposal as of Sept 1, 2026" line is not pinned to this page.
47. Morgan Lewis, "New Jersey Adopts Final Independent Contractor Regulations" (May 2026) — https://www.morganlewis.com/pubs/2026/05/new-jersey-adopts-final-independent-contractor-regulations — accessed 2026-09-26 — secondary; snippet-only.
48. Ogletree, "New Jersey Issues Controversial Final Regulations on 'ABC Test'" — https://ogletree.com/insights-resources/blog-posts/new-jersey-issues-controversial-final-regulations-on-abc-test-for-independent-contractor-status/ — accessed 2026-09-26 — secondary; snippet-only.
49. Akin, "NJDOL Adopts Regulations Clarifying Application of New Jersey's Existing ABC Test" — https://www.akingump.com/en/insights/alerts/new-jersey-department-of-labor-and-workforce-development-adopts-regulations-clarifying-application-of-new-jerseys-existing-independent-contractor-abc-test — accessed 2026-09-26 — secondary; snippet-only.
50. ABC SoCal, "Independent Contractor Rule 2026: Federal Shift vs California Reality" — https://abcsocal.org/independent-contractor-rule-2026-federal-shift-vs-california-reality-for-abc-socal-contractors/ — accessed 2026-09-26 — secondary (trade association); title only.
51. Davis Wright Tremaine, "Texas Federal Court Overturns DOL's 2024 Overtime Rule Nationwide" (Nov 2024) — https://www.dwt.com/blogs/employment-labor-and-benefits/2024/11/texas-court-overturns-2024-dol-overtime-rule — accessed 2026-09-26 — secondary; snippet-only.
52. FindLaw, *Plano Chamber of Commerce v. DOL* (E.D. Tex. 2024) — https://caselaw.findlaw.com/court/us-dis-crt-e-d-tex-she-div/116694763.html — accessed 2026-09-26 — primary (hosts the opinion); title only.
53. Employment Law Worldview, "Blocked DOL Overtime Rule Set for Review in the Fifth Circuit" — https://www.employmentlawworldview.com/blocked-dol-overtime-rule-set-for-review-in-the-fifth-circuit-us/ — accessed 2026-09-26 — secondary; snippet-only.
54. Higher Ed Dive, "Trump administration court filing may spell end of overtime final rule" — https://www.highereddive.com/news/trump-5th-circuit-overtime-rule-appeals-on-hold/747311/ — accessed 2026-09-26 — secondary; snippet-only (year of the May 9 stay inferred).
55. Law360, "DOL, OT Rule Challenger Ask 5th Circ. To Toss Case" — https://www.law360.com/employment-authority/articles/2474235/dol-ot-rule-challenger-ask-5th-circ-to-toss-case — accessed 2026-09-26 — secondary; headline only (paywalled, date not visible).
56. Law360, "5th Circ. Tosses Another DOL Overtime Rule Appeal" — https://www.law360.com/employment-authority/wage-hour/articles/2476146/5th-circ-tosses-another-dol-overtime-rule-appeal — accessed 2026-09-26 — secondary; headline only.
57. California DIR, "Overtime" FAQ — https://www.dir.ca.gov/dlse/faq_overtime.htm — accessed 2026-09-26 — primary; summary-level only.
58. Bloomberg Law, "State Overtime Laws Chart" — https://pro.bloomberglaw.com/insights/labor-employment/overtime-pay-laws-by-state/ — accessed 2026-09-26 — secondary; snippet-only.
59. Nevada Legislature, NRS Chapter 608 (incl. 608.018) — https://www.leg.state.nv.us/nrs/nrs-608.html — accessed 2026-09-26 — primary; snippet-only.
60. Homebase, "Nevada Overtime Laws: The Employer's Guide (2026)" — https://www.joinhomebase.com/blog/nevada-overtime-laws — accessed 2026-09-26 — secondary; snippet-only ($18/$12 figures not pinned).
61. Colorado CDLE, COMPS Order #38 (7 CCR 1103-1) — https://cdle.colorado.gov/sites/cdle/files/7%20CCR%201103-1%20COMPS%20Order%20%2338%20%5Baccessible%5D.pdf — accessed 2026-09-26 — primary; snippet-only (quoted language).
62. Minnesota Paid Leave, "Premium rate and contributions" — https://pl.mn.gov/resources/calculators/premium-rate-and-contributions — accessed 2026-09-26 — primary; snippet-only.
63. American Payroll Association (payroll.org), "Minnesota's New Paid Leave Program Takes Effect" (Jan 23, 2026) — https://payroll.org/news-resources/news/news-detail/2026/01/23/minnesota-s-new-paid-leave-program-takes-effect — accessed 2026-09-26 — secondary; snippet-only.
64. Delaware DOL, "Employers & Third Party Administrators Guide to Delaware Paid Leave" — https://laborfiles.delaware.gov/main/pfl/Employer_and_TPAs_Guide_to_DPL.pdf — accessed 2026-09-26 — primary; snippet-only.
65. Toast, "Toast Payroll: Delaware and Maine Paid Family Medical Leave" — https://support.toasttab.com/en/article/Toast-Payroll-Delaware-and-Maine-Paid-Family-Medical-Leave — accessed 2026-09-26 — secondary; snippet-only.
66. Epstein Becker Green, "2026 Family and Medical Leave Law Updates: What Employers in Seven States Need to Know" — https://www.ebglaw.com/insights/publications/2026-family-and-medical-leave-law-updates-what-employers-in-seven-states-need-to-know — accessed 2026-09-26 — secondary; snippet-only.
67. HR Dive, "State paid family leave benefit changes in 2026" — https://www.hrdive.com/news/state-paid-family-leave-benefit-changes-in-2026/809625/ — accessed 2026-09-26 — secondary; snippet-only.
68. Economic Policy Institute, "Over 8.3 million workers will benefit from minimum wage increases on January 1: Nineteen states will raise their minimum wages" — https://www.epi.org/blog/over-8-3-million-workers-will-benefit-from-minimum-wage-increases-on-january-1-nineteen-states-will-raise-their-minimum-wages-heres-where/ — accessed 2026-09-26 — secondary (think tank); snippet-only. Not to be confused with EPI's differently dated "Twenty-two states" post.
69. Axios, "2026 minimum wage: New Year's hikes are set for these 19 states" (Dec 28, 2025) — https://www.axios.com/2025/12/28/2026-new-year-minimum-wage — accessed 2026-09-26 — secondary; title/snippet.
70. Hunton, "Several States Enact Pay Transparency Laws: What Employers Need to Know in 2026" — https://www.hunton.com/hunton-retail-law-resource/several-states-enact-pay-transparency-laws-what-employers-need-to-know-in-2026 — accessed 2026-09-26 — secondary; snippet-only.
71. Rippling, "Pay Transparency Laws by State" — https://www.rippling.com/blog/pay-transparency-laws-state-by-state-guide — accessed 2026-09-26 — secondary; snippet-only.
72. LOIO, "Pay Transparency Laws by State: 2026 Tracker" — https://loio.com/guides/pay-transparency-laws-by-state/ — accessed 2026-09-26 — secondary; snippet-only.
73. Morgan Lewis, "US Department of Labor Rolls Back Biden-Era FLSA Practices" (July 2025) — https://www.morganlewis.com/pubs/2025/07/us-department-of-labor-rolls-back-biden-era-flsa-practices — accessed 2026-09-26 — secondary; title only (fetch blocked, body not read).
74. DOL WHD, "Field Assistance Bulletins" index — https://www.dol.gov/agencies/whd/field-assistance-bulletins — accessed 2026-09-26 — primary; title only (fetch blocked).

---

## 5. Accuracy/liability lens — documented failures, lawsuits and regulatory actions

Researched by a dedicated pass (25 searches; all three fetches blocked; **every
finding is snippet-only**). **Not searched** because of the cap: BambooHR (item
7), payroll-provider collapses such as MyPayrollHR (item 8), and PEO failures
(item 9). "Not searched" means no finding either way.

### 5.1 Kronos / UKG Private Cloud ransomware (December 2021)

- **What happened:** timekeeping and payroll were interrupted, "resulting in
  workers not being paid, being paid late, or being paid incorrectly" [1][2][3].
- **The vendor as defendant:** *In re UKG Inc. Cybersecurity Breach
  Litigation*, N.D. Cal. No. 3:22-cv-00346, settled for **up to $6M**, pleaded
  as data-security negligence. Final approval came on 2023-11-22
  [1][3][4][5][6][7].
- **Employers as defendants** paid more:
  - PepsiCo: **$12.75M** [9];
  - T-Mobile: **$7M** [13];
  - Cargill: **$2.4M** [11];
  - Frito-Lay and Honda also settled; amounts not captured [10][14].

  Bloomberg Law quotes the principle: employers "can outsource the payroll
  function" but "cannot outsource liability for violations of the FLSA or
  state or local laws" [18].

### 5.2 Gusto

- **No class actions, agency actions, data-breach settlements or acknowledged
  major outages found** in four searches.
- One documented incident: on 2022-10-19 the Colorado Treasury said Gusto had
  emailed clients the wrong agency for Q3 unemployment filings [19]. That was a
  misdirected notice, not a mis-filing.
- **Contract terms** (snippet-only) [20][21][22]:
  - no liability for penalties caused by inaccurate employer data;
  - tax notices must reach Gusto at least 30 days before any response date;
  - a defined "Gusto Error" for its own remittance or filing failure.

### 5.3 ADP, plus BIPA across vendors

- ***Goonewardene v. ADP, LLC*** (Cal. Supreme Court No. S238941, 2019-02-07,
  unanimous): a payroll provider owes its customers' employees **no** duty in
  contract or negligence, and the employer stays liable [23][24][25]. **This
  is the most important vendor-liability precedent found.**
- **Illinois BIPA biometric time-clock suits** are the one area where vendors
  paid large sums directly:
  - ADP: **$25M** (final approval February 2021) [26][27][28];
  - Kronos: **$15.3M** (*Figueroa v. Kronos*, N.D. Ill.) [29][30][31];
  - Paychex: about **$3.4M** [32];
  - Paylocity: dismissed with prejudice 2025-04-22, per its 10-Q [34][35].
- No ADP data breach in 2019–2026 was found [36].

### 5.4 Intuit

- **QuickBooks Payroll direct deposits:** Community threads report same-day
  deposits stuck at "scheduled". Intuit blamed planned maintenance and said
  there was "no actual impact to the money movement". The date (probably
  August 2025) is unconfirmed [40][41][42].
- **"Free" advertising precedent** (tax-preparation software, included because
  SAIRNbiz is marketed as free):
  - Intuit agreed on 2022-05-04 to pay **$141M** to all 50 states and DC over
    misleading "free" TurboTax ads [43][44][45].
  - The FTC's January 2024 order found the ads deceptive [46][47].
  - On **2026-03-20 the Fifth Circuit** (*Intuit v. FTC*, No. 24-60040) set the
    order aside on separation-of-powers grounds and sent it back. It did not
    rule the ads accurate [49]–[52].

### 5.5 Rippling

- *Rippling v. Deel* is about espionage, not accuracy [53].
- **SVB collapse, 2023-03-10:** Rippling's payments ran through SVB, some
  paychecks were delayed, and Rippling moved its payments infrastructure to
  JPMorgan Chase [54][55][56].
- An unverified BBB complaint alleges a calculation bug paid overtime nobody
  worked [57].
- No class or agency actions over Rippling's payroll accuracy were found.

### 5.6 Paylocity — the closest analogue to SAIRNbiz's own computed figures

- ***DrinkPAK, LLC v. Paylocity Corp.*** (L.A. Superior No. 24CHCV02154; C.D.
  Cal. No. 2:24-cv-06369), filed June 2024 [58]–[61].
  - An **employer is suing the vendor**. It alleges Paylocity's software got
    the overtime regular rate and the meal/rest premiums wrong.
  - DrinkPAK settled two wage-and-hour class actions it traces to those errors,
    and wants reimbursement.
  - Outcome not found.
- ***Nor-Cal Moving Services v. Paylocity Corp.*** (N.D. Cal. No.
  3:25-cv-02085) [62]–[65].
  - Alleges unlawful time rounding, including on meal-break punches.
  - On **2025-07-23** the court kept the **breach-of-contract claim** and a
    misrepresentation claim based on one account manager's statement. The
    contribution claim failed.

### 5.7 Synthesis (from the liability research, lightly edited)

**The duty to pay wages and taxes stays with the employer.**
- The largest Kronos-outage payouts came from employers [9][13][11].
- California's Supreme Court has held that a payroll processor cannot be sued
  by its customers' employees [23].
- A vendor's exposure therefore runs mainly to its own customer, in contract,
  and its terms narrow even that [20][22].

**That contract route is not closed.** Two employers have sued Paylocity to
recover class settlements they blame on the vendor's overtime, premium and
rounding logic, and a contract claim survived dismissal [58]–[65].

**What the design does and does not protect (analysis):**
- A calculation-only design that never moves money, files or remits keeps
  SAIRNbiz off the failure paths that dominate the vendor record: outages that
  delay pay, a bank-partner failure (Rippling/SVB), and missed deposits or
  filings.
- Refusing to compute withholding and net pay also avoids handing an employer a
  confident wrong number to rely on. That reliance is the factual core of
  DrinkPAK and Nor-Cal.
- It does **not** protect the figures SAIRNbiz does compute: overtime, gross,
  FICA and the 1099 count (F1–F3). Those have exactly the regular-rate and
  rounding shape that produced the employer settlements and then the vendor
  suits.
- **No disclaimer cancels compliance assurances given in sales or support**:
  the one account-manager statement kept Nor-Cal's misrepresentation claim
  alive [62].

**Leads for a follow-up pass** (names only, nothing asserted):
- DOJ releases on the MyPayrollHR prosecution;
- *Mobley v. Workday* (the HR-vendor-as-agent theory);
- *Donohue v. AMN Services* and *Camp v. Home Depot* (California rounding and
  meal periods).

### Sources (§5)

1. In re UKG Inc. Cybersecurity Breach Litigation, 3:22-cv-00346 (docket), CourtListener — https://www.courtlistener.com/docket/62606788/in-re-ukg-inc-cybersecurity-breach-litigation/ — accessed 2026-09-26 — primary; snippet-only
2. In re UKG…, Document 80 (N.D. Cal. 2023), Justia — https://law.justia.com/cases/federal/district-courts/california/candce/3:2022cv00346/390703/80/ — accessed 2026-09-26 — primary; snippet-only
3. In re UKG Inc. Cybersecurity Litigation settlement site — https://www.kronosprivatecloudsettlement.com/ — accessed 2026-09-26 — court-approved notice site; WebFetch blocked; snippet-only
4. UKG agrees to pay up to $6M in lawsuit tied to 2021 breach, Cybersecurity Dive — https://www.cybersecuritydive.com/news/ukg-settles-6M-lawsuit-ransomware-attack/688265/ — accessed 2026-09-26 — secondary; snippet-only
5. Kronos Reaches $6M Settlement Over Ransomware Attack, TechTarget — https://www.techtarget.com/healthtechsecurity/news/366594264/Kronos-Reaches-6M-Settlement-Over-Ransomware-Attack — accessed 2026-09-26 — secondary; snippet-only
6. UKG to settle class action lawsuit with workers affected by Kronos outage, HR Dive — https://www.hrdive.com/news/ukg-to-settle-class-action-lawsuit-with-workers-affected-by-kronos-outage/647753/ — accessed 2026-09-26 — secondary; headline-only
7. Kronos Agrees to $6 Million Settlement…, Baker Botts (May 2023) — https://www.bakerbotts.com/thought-leadership/publications/2023/may/kronos-agrees-to-$6-million-settlement-for-2021-ransomware-attack — accessed 2026-09-26 — law-firm alert; headline-only
8. Tesla, PepsiCo workers bring lawsuit over UKG payroll outage, TechTarget — https://www.techtarget.com/searchhrsoftware/news/252512253/Tesla-PepsiCo-workers-bring-lawsuit-over-UKG-payroll-outage — accessed 2026-09-26 — secondary; snippet-only
9. $13M Pepsi settlement over unpaid wages following Kronos hack approved, Top Class Actions — https://topclassactions.com/lawsuit-settlements/employment-labor/13m-pepsi-settlement-over-unpaid-wages-following-kronos-hack-approved/ — accessed 2026-09-26 — promotional; snippet-only
10. Frito-Lay becomes latest employer to settle Kronos outage wage-and-hour claims, HR Dive — https://www.hrdive.com/news/frito-lay-settle-kronos-overtime-settlement/719013/ — accessed 2026-09-26 — secondary; headline-only
11. Court approves Cargill's $2.4M settlement of Kronos outage wage claims, Cybersecurity Dive — https://www.cybersecuritydive.com/news/cargill-kronos-ransomware-outage-settlement/702269/ — accessed 2026-09-26 — secondary; snippet-only
12. Worker sues Cargill for lost pay due to Kronos outage, Legal Dive — https://www.legaldive.com/news/worker-sues-cargill-lost-pay-due-kronos-outage-alleges-negligence-ellis-flsa/633099/ — accessed 2026-09-26 — secondary; headline-only
13. T-Mobile $7M Settlement for Kronos Outage Wage Claims, ClaimDepot — https://www.claimdepot.com/settlements/tmobile-kronos-outage-settlement — accessed 2026-09-26 — promotional; snippet-only
14. Honda moves to settle Kronos outage-related timekeeping lawsuit, HR Dive — https://www.hrdive.com/news/honda-kronos-outage-lawsuit-survives/754237/ — accessed 2026-09-26 — secondary; headline-only
15. Lawsuit alleges Honda improperly estimated employee hours following Kronos outage, Legal Dive — https://www.legaldive.com/news/lawsuit-alleges-honda-improperly-estimated-employee-hours-following-kronos-whatley-flsa/628474/ — accessed 2026-09-26 — secondary; headline-only
16. NYC transit worker alleges pay violations after Kronos ransomware disruption, Cybersecurity Dive — https://www.cybersecuritydive.com/news/kronos-ransomware-MTA-lawsuit/618812/ — accessed 2026-09-26 — secondary; headline-only
17. Goodyear lawsuit claims Kronos hack led to failure to pay wages, Top Class Actions — https://topclassactions.com/lawsuit-settlements/employment-labor/goodyear-lawsuit-claims-kronos-hack-led-to-companys-failure-to-pay-wages-earned/ — accessed 2026-09-26 — promotional; headline-only
18. Kronos Hack Wage Suits Show Legal Risks of Payroll Outsourcing, Bloomberg Law — https://news.bloomberglaw.com/daily-labor-report/kronos-hack-wage-suits-show-legal-risks-of-payroll-outsourcing — accessed 2026-09-26 — secondary; snippet-only
19. Payroll firm Gusto sends Colorado businesses incorrect information for tax, Colorado Dept. of the Treasury (19 Oct 2022) — https://treasury.colorado.gov/press-release/10192022-payroll-firm-gusto-sends-colorado-businesses-incorrect-information-for-tax — accessed 2026-09-26 — primary (state agency); snippet-only
20. Payroll Service Terms, Gusto — https://gusto.com/legal/terms/payroll — accessed 2026-09-26 — primary (vendor contract); WebFetch blocked; snippet-only
21. Embedded Payroll Service Agreement, Gusto Flows — https://flows.gusto.com/terms — accessed 2026-09-26 — primary (vendor contract); title plus tool summary only
22. Gusto Terms of Service summary, ConductAtlas — https://conductatlas.com/platform/gusto/gusto-terms-of-service/ — accessed 2026-09-26 — third-party summary; unverified against source
23. Goonewardene v. ADP, S238941, Supreme Court of California — https://www4.courts.ca.gov/opinions/archive/S238941.PDF — accessed 2026-09-26 — primary; snippet-only
24. ADP Isn't Liable for Employer's Alleged Wage Violations, SHRM — https://www.shrm.org/topics-tools/employment-law-compliance/adp-isnt-liable-employers-alleged-wage-violations — accessed 2026-09-26 — secondary; snippet-only
25. California Supreme Court Holds that Payroll Services Provider ADP Cannot Be Sued…, Weintraub Tobin/JD Supra — https://www.jdsupra.com/legalnews/california-supreme-court-holds-that-23163/ — accessed 2026-09-26 — law-firm alert; snippet-only
26. Judge Grants Final Approval to $25M Settlement in BIPA Class Action against ADP, Chicago Business Litigation Lawyer Blog — https://www.chicagobusinesslitigationlawyerblog.com/judge-grants-final-approval-to-25m-settlement-in-bipa-class-action-against-adp/ — accessed 2026-09-26 — law-firm blog; snippet-only
27. ADP BIPA Class Action Settlement, Top Class Actions — https://topclassactions.com/lawsuit-settlements/closed-settlements/adp-bipa-class-action-settlement/ — accessed 2026-09-26 — promotional; snippet-only
28. ADP BIPA final-approval brief, Cook County Circuit Court (1 Feb 2021) — https://s3.amazonaws.com/jnswire/jns-media/46/a8/11539416/adp_bipa_settlement_final_brief_2-1-21.pdf — accessed 2026-09-26 — primary filing; title-only
29. Figueroa v. Kronos Inc. settlement site — https://www.kronosbipasettlement.com/ — accessed 2026-09-26 — settlement administrator; snippet-only
30. Kronos Reaches $15.3 Million Settlement in Biometric Privacy Suit, Bloomberg Law — https://news.bloomberglaw.com/privacy-and-data-security/kronos-reaches-15-3-million-settlement-in-biometric-privacy-suit — accessed 2026-09-26 — secondary; headline-only
31. Timeclock vendor Kronos agrees to pay $15M…, Cook County Record — https://www.legalnewsline.com/cook-county-record/timeclock-vendor-kronos-agrees-to-pay-15m-to-end-fingerprint-scan-class-action-lawyers-to/article_707e06e3-f1b7-5c63-9b3a-f19234576165.html — accessed 2026-09-26 — secondary; headline-only
32. Paychex Biometric Privacy $3.4M Class Action Settlement, Top Class Actions — https://topclassactions.com/lawsuit-settlements/closed-settlements/paychex-biometric-privacy-3-4m-class-action-settlement/ — accessed 2026-09-26 — promotional; snippet-only
33. Microsoft Trims BIPA Suit Over Cloud Storage For Paychex, Law360 — https://www.law360.com/articles/1564010/microsoft-trims-bipa-suit-over-cloud-storage-for-paychex — accessed 2026-09-26 — secondary; headline-only
34. Paylocity Holding Corp Form 10-Q (period ending 30 Sep 2025), SEC — https://www.sec.gov/Archives/edgar/data/1591698/000159169825000113/pcty-20250930.htm — accessed 2026-09-26 — primary; snippet-only
35. Paylocity Holding Corp Form 10-Q (period ending 30 Sep 2021), SEC — https://www.sec.gov/Archives/edgar/data/1591698/000155837021014749/pcty-20210930x10q.htm — accessed 2026-09-26 — primary; snippet-only
36. ADP Payroll Services Compromised by Data Breach, Top Class Actions — https://topclassactions.com/lawsuit-settlements/lawsuit-news/adp-payroll-services-compromised-data-breach/ — accessed 2026-09-26 — promotional; snippet-only (2016 incident)
37. Paychex sued for negligence after data breach exposes workers' names and SSNs, HR Dive — https://www.hrdive.com/news/paychex-sued-for-negligence-after-data-breach/721768/ — accessed 2026-09-26 — secondary; headline-only
38. ADP Form 10-Q (period ending 31 Mar 2025), SEC — https://www.sec.gov/Archives/edgar/data/8670/000000867025000015/adp-20250331.htm — accessed 2026-09-26 — primary; snippet-only
39. ADP Form 10-Q (period ending 30 Sep 2024), SEC — https://www.sec.gov/Archives/edgar/data/8670/000000867024000030/adp-20240930.htm — accessed 2026-09-26 — primary; snippet-only
40. "Is there a delay with payroll deposits today?", QuickBooks Community — https://quickbooks.intuit.com/learn-support/en-us/account-management/is-there-a-delay-with-payroll-deposits-today/00/1573165 — accessed 2026-09-26 — user forum with Intuit replies; snippet-only; undated
41. "Why are my direct deposits late?", QuickBooks Community — https://quickbooks.intuit.com/learn-support/en-us/employees-and-payroll/why-are-my-direct-deposits-late/00/1573168 — accessed 2026-09-26 — user forum; snippet-only
42. "Direct Deposits Didn't Run Today", QuickBooks Community — https://quickbooks.intuit.com/learn-support/en-us/employees-and-payroll/direct-deposits-didn-t-run-today/00/1573228 — accessed 2026-09-26 — user forum; snippet-only
43. Intuit Form 8-K, FY22 Q3 earnings release, SEC — https://www.sec.gov/Archives/edgar/data/896878/000089687822000019/fy22q3earningspressrelease.htm — accessed 2026-09-26 — primary; snippet-only
44. Attorney General Jennings announces $141 million TurboTax settlement, Delaware (4 May 2022) — https://news.delaware.gov/2022/05/04/attorney-general-jennings-announces-141-million-turbotax-settlement — accessed 2026-09-26 — primary; title-only
45. AG Nessel announces distribution of $141 million settlement, Michigan AG (9 May 2023) — https://www.michigan.gov/ag/news/press-releases/2023/05/09/ag-nessel-announces-distribution-of-141-million-settlement-to-millions-of-low-income-americans — accessed 2026-09-26 — primary; snippet-only
46. FTC Issues Opinion Finding that TurboTax Maker Intuit Inc. Engaged in Deceptive Practices, FTC (Jan 2024) — https://www.ftc.gov/news-events/news/press-releases/2024/01/ftc-issues-opinion-finding-turbotax-maker-intuit-inc-engaged-deceptive-practices — accessed 2026-09-26 — primary; snippet-only
47. Intuit Inc., In the Matter of (TurboTax), FTC case page — https://www.ftc.gov/legal-library/browse/cases-proceedings/192-3119-intuit-inc-matter-turbotax — accessed 2026-09-26 — primary; title-only
48. Commission order, D-9408 (29 Feb 2024), FTC — https://www.ftc.gov/system/files/ftc_gov/pdf/d9408_20240229_commission_order_unsigned.pdf — accessed 2026-09-26 — primary; truncated title only
49. Intuit v. FTC, No. 24-60040, opinion, U.S. Court of Appeals for the Fifth Circuit — https://www.ca5.uscourts.gov/opinions/pub/24/24-60040-CV0.pdf — accessed 2026-09-26 — primary; snippet-only
50. Intuit v. Federal Trade Commission, No. 24-60040 (5th Cir. 2026), Justia — https://law.justia.com/cases/federal/appellate-courts/ca5/24-60040/24-60040-2026-03-20.html — accessed 2026-09-26 — primary mirror; title-only
51. US Appeals Court Tosses FTC Order Over Intuit's "Free" TurboTax Ads, PYMNTS — https://www.pymnts.com/cpi-posts/u-s-appeals-court-tosses-ftc-order-over-intuits-free-turbotax-ads/ — accessed 2026-09-26 — secondary; snippet-only
52. Intuit Applauds Fifth Circuit Decision in its Favor vs FTC, Intuit — https://www.intuit.com/blog/news-social/intuit-applauds-fifth-circuit-decision-in-its-favor-vs-ftc/ — accessed 2026-09-26 — party statement; title-only
53. Deel scores a lawsuit win, but not against Rippling, TechCrunch (19 Aug 2025) — https://techcrunch.com/2025/08/19/deel-scores-a-lawsuit-win-but-not-against-rippling — accessed 2026-09-26 — secondary; snippet-only
54. Rippling needed $545 million for paychecks when SVB collapsed, Washington Post (2 Apr 2023) — https://www.washingtonpost.com/us-policy/2023/04/02/rippling-svb-payroll-collapse/ — accessed 2026-09-26 — secondary; snippet-only
55. Silicon Valley Bank customers scramble to meet payroll, pay bills, CNBC (10 Mar 2023) — https://www.cnbc.com/2023/03/10/silicon-valley-bank-customers-scramble-to-meet-payroll-pay-bills.html — accessed 2026-09-26 — secondary; snippet-only
56. Rippling calls on FDIC to release payments, Rippling blog — https://www.rippling.com/blog/rippling-calls-on-fdic-to-release-payments — accessed 2026-09-26 — vendor statement; title-only
57. Rippling complaints, BBB — https://www.bbb.org/us/ca/san-francisco/profile/payroll-services/rippling-1116-919641/complaints — accessed 2026-09-26 — customer-submitted, unverified; snippet-only
58. Employer's lawsuit aims to hold Paylocity responsible for wage and hour settlements, HR Dive — https://www.hrdive.com/news/paylocity-drinkpak-software-error-lawsuit/719073/ — accessed 2026-09-26 — secondary; snippet-only
59. Drinkpak, LLC v. Paylocity Corp., 2:2024cv06369 (C.D. Cal.), Justia Dockets — https://dockets.justia.com/docket/california/cacdce/2:2024cv06369/934986 — accessed 2026-09-26 — docket index; title-only
60. Drinkpak v. Paylocity, L.A. Superior Court 24CHCV02154, Trellis — https://trellis.law/case/24chcv02154/drinkpak-llc-a-california-limited-liability-company-vs-paylocity-corp-an-illinois-corporation — accessed 2026-09-26 — docket aggregator; title-only
61. DrinkPAK Sues Paylocity Over Payroll Software Errors, B2Bdaily — https://b2bdaily.com/hrtech/drinkpak-sues-paylocity-over-payroll-software-errors-compliance-breaches/ — accessed 2026-09-26 — secondary; snippet-only
62. Nor-Cal Moving Services v. Paylocity Corp., No. 3:2025cv02085, Document 30 (N.D. Cal. 2025), Justia — https://law.justia.com/cases/federal/district-courts/california/candce/3:2025cv02085/445459/30/ — accessed 2026-09-26 — primary court order; snippet-only
63. Nor-Cal Moving Services v. Paylocity Corp., CourtListener — https://www.courtlistener.com/opinion/10640087/nor-cal-moving-services-v-paylocity-corp/ — accessed 2026-09-26 — primary; snippet-only
64. USCOURTS-cand-3_25-cv-02085-0 (order PDF), govinfo — https://www.govinfo.gov/content/pkg/USCOURTS-cand-3_25-cv-02085/pdf/USCOURTS-cand-3_25-cv-02085-0.pdf — accessed 2026-09-26 — primary; snippet-only
65. Nor Cal Moving Services v. Paylocity Corp (2025), FindLaw — https://caselaw.findlaw.com/court/us-dis-crt-n-d-cal/117989388.html — accessed 2026-09-26 — primary mirror; snippet-only
66. Employer's Liability for Payroll Company Failures, BTLG — https://btlg.us/an-employers-liability-for-payroll-companys-failure-to-remit-taxes/ — accessed 2026-09-26 — law-firm page; snippet-only

---

## 6. Adjacent-industry lens — "free with subscription" backbones and how they are priced

Researched by a dedicated pass (24 searches; all seven fetches blocked).
**Three dates corrected** against assumptions in the research prompt:
- Wave's paid Pro tier arrived in **2024**.
- Free legacy Wave users lost bank feeds on **2026-06-01**.
- The FTC's 2024 Intuit order was **set aside in March 2026** (§5.4).

### 6.1 Free and freemium backbones, and what pays for them

| Product | Free | Paid | Price | Src |
|---|---|---|---|---|
| Wave | Starter: invoicing, manual bookkeeping | Pro: bank connections, receipt scanning, extra users | $19/mo, or about $16 annual (conflict) | [1]–[5] |
| Wave Payroll | — | Add-on | $40 + $6 per worker | [6] |
| Zoho Books | 1 user, 1,000 invoices/yr, **revenue under $50K** | Paid plans above that | from $20/mo | [7]–[10] |
| Homebase | Basic: **10 employees at 1 location** (official) or 20 (third parties) | Payroll add-on | $49 + $6 (official) or $39 + $6 | [11][12] |
| Deel HR | Free HRIS **under 200 people** (since 2023-01) | EOR, contractors, global payroll | EOR from $599/employee/mo | [13][14] |
| Connecteam | All features, **up to 10 users** | Per-hub plans | from $29/mo | [15][16] |
| Square | free tier not verified | Payroll | $35 + $6 | [17] |
| Toast Payroll | — | Payroll | from $69 + $9 PEPM | [18][19] |
| Payroll4Free | Core payroll, **up to 9–10 employees**, ad-supported | Tax filing service, direct deposit | $15–25/mo (conflict) | [20][21] |
| Bambee Guided Payroll | Free under 20 employees inside an HR subscription (2022 launch; possibly stale) | $4/employee at 20+ | — | [22][23] |

**The pattern: every free tier is capped** by revenue, headcount, users or
features, **and an adjacent paid product pays for it.** Bambee (2022) is the
only "free *with* a subscription" case found.

### 6.2 Vertical SaaS: bundle or integrate?

| Vendor (vertical) | Accounting | Payroll | Src |
|---|---|---|---|
| CosmoLex (legal) | **Bundled** native trust and operating ledger. A reported 2026 repricing puts the operating ledger in the Pro tier only, **$129/user/mo** (secondary; verify) | not checked | [24] |
| Clio (legal) | Integrates with QuickBooks/Xero; now sells **Clio Accounting as a paid add-on**. Launch date conflicts: July 2024 vs "early 2026"; Canadian launch 2026-09-25 | not checked | [25]–[28] |
| ServiceTitan (home services) | Integrates | No native payroll found | [29]–[31] |
| Jobber (home services) | Integrates with QuickBooks Online | Runs in QuickBooks Online Payroll | [32] |
| Housecall Pro (home services) | not checked | **Embedded paid add-on, powered by Check: $40 + $6** | [33][34] |
| Vagaro (salon/spa) | QuickBooks/Xero sync is itself a paid add-on | Embedded paid add-on; price conflicts | [35][36] |
| Buildertrend, Procore (construction) | Integrate (QuickBooks, Xero, ERPs) | not checked | [38][39] |
| ezyVet (veterinary) | Integrates with Xero | not checked | [40] |

**The usual pattern is integration.** Vertical vendors connect to QuickBooks or
Xero and sell embedded payroll as a paid per-employee add-on. A native ledger
appeared only in legal software, where trust-accounting (IOLTA) rules force it
into the product, and even there it is sold as a top tier or a paid add-on.
**No vertical vendor was found that includes a general ledger, AP/AR and HR at
no extra charge.** That is what the search turned up, not proof that none
exists.

### 6.3 Embedded payroll economics

- **Reported structure** (aggregator; providers do not publish it): platforms
  charge customers **$35–70/mo base plus $6–10 PEPM**. The **platform keeps
  about two-thirds** and the provider about one-third [41][42].
- Tidemark calls embedded payroll a revenue expansion "on the same order of
  magnitude as payments" [43].
- **What providers charge platforms is mostly not public.** Everee is the
  exception: $0.50 per payment or $10 per worker per month [44]–[47].

Published end-customer prices ($6 PEPM recurs across four unrelated brands):

| Platform | Base/mo | PEPM | Src |
|---|---|---|---|
| Housecall Pro (via Check) | $40 | $6 | [33][34] |
| Wave | $40 | $6 | [6] |
| Square | $35 | $6 | [17] |
| Homebase | $49 (or $39) | $6 | [11][12] |
| Vagaro | $34 (or $20) | $5 (or $6) | [36] |
| Toast | $69 | $9 | [19] |

**None of these prices compares to SAIRNbiz's payroll.** They pay for
withholding, paying staff, and filing and remitting taxes, and SAIRNbiz does
none of those.

### 6.4 Cautionary precedents

- **Wave narrowed its free tier.** It introduced a free Starter plan and a paid
  Pro plan in January/February 2024 and kept existing users on "Legacy" terms.
  On **2026-06-01** Legacy users were moved over, and bank-connection imports
  now need Pro [1][3].
- **FTC v. Intuit:** a 2024 order on "free" claims, vacated on procedure in
  March 2026 (§5.4) [49]–[52].
- **16 CFR Part 251**, the FTC Guide Concerning Use of the Word "Free", covers
  "free" **and similar wording** [53][54][55]. As the search summary rendered
  it:
  - when the free item depends on a purchase, "all the terms, conditions and
    obligations … should be set forth clearly and conspicuously **at the
    outset** of the offer", "in **close conjunction** with the offer";
  - a single kind of service should not carry a "Free" offer in one trade area
    for **more than 6 months in any 12-month period**.

  The Guide's other paragraphs were not retrieved.
- **Not verified** (search cap): the Mint shutdown and the end of the Google
  Workspace legacy free edition.

### 6.5 Synthesis

**Giving away a capped backbone to anchor a paid relationship is a
well-established model:** Wave, Zoho Books, Homebase, Connecteam and Deel all do
it. What was found nowhere is SAIRNbiz's specific combination — a double-entry
ledger, AP/AR with 1099 tracking, and HR — **included at no extra charge
inside a vertical subscription, and uncapped.**

- That is a real differentiator against the integrate-and-charge pattern of
  §6.2.
- It is also, as analysis, an uncapped cost SAIRN has to model.
- The payroll half should be compared with a free calculation tier such as
  Payroll4Free's, which does more, not with the $35–69 + $5–9 PEPM products.

**Wording suggestions the research supports** (not adopted here; counsel
should review the final wording):
1. Describe the bundle — "HR and accounting included in every SAIRN
   subscription at no additional charge" — rather than a price that has been
   waived.
2. Put the conditions next to the claim, as 16 CFR 251.1 asks: an active paid
   subscription, and payroll calculations only, with no withholding, payment,
   filing or remittance.
3. Avoid "free forever". Wave narrowed its free tier for existing users within
   about two years. That the Guide's 6-months-in-12 frequency paragraph fits
   poorly with a permanent purchase-conditioned "free" claim is an inference,
   not a ruling.

### Sources (§6)

1. Wave Help Center, "FAQ: Plans for legacy businesses" — https://support.waveapps.com/hc/en-us/articles/26449863006612-FAQ-Plans-for-legacy-businesses — accessed 2026-09-26 — primary; summary-only (WebFetch blocked); result metadata shows it was updated 2026-07-10.
2. Wave, "Wave's Pro Plan helps you keep your books organized" — https://www.waveapps.com/pro — accessed 2026-09-26 — primary; appeared in results, content via summary only.
3. Beancount.io, "Wave Accounting's Bank Feeds and Collaborator Paywall: What Changed in June 2026" (2026-08-05) — https://beancount.io/blog/2026/08/05/wave-accounting-bank-feeds-collaborator-paywall-guide ; HelloBooks, "Migrate from Wave Accounting — June 2026 Plan…" — https://hellobooks.ai/migrate/from-wave — accessed 2026-09-26 — secondary; both sell competing products (possible bias); summary-only / title-only.
4. ERP Research, "Wave Accounting Pricing 2026: Free + $19/mo Pro" — https://www.erpresearch.com/pricing/wave-accounting ; G2, "Wave Pricing 2026" — https://www.g2.com/products/wave/pricing — accessed 2026-09-26 — secondary; summary-only; attribution not isolated.
5. Tech.co, "Wave Invoicing Pricing: Plans, Add-ons, and Fees Explained" — https://tech.co/accounting-software/wave-invoicing ; Sonary, "Wave Review 2026" — https://sonary.com/reviews/wave/ ; Startup Owl, "Wave Bookkeeping Review 2026, Free Starter and $16 Pro" — https://startupowl.com/reviews/wave — accessed 2026-09-26 — secondary; summary-only; attribution not isolated.
6. SaaSrat, "Wave Payroll Review 2026" — https://saasrat.com/products/wave-payroll ; The CFO Club, "Wave Accounting Pricing Tiers & Costs" — https://thecfoclub.com/tools/wave-accounting-pricing/ ; HamsterStack, "Wave pricing, tiers and limits in 2026" — https://hamsterstack.com/pricing/wave/ — accessed 2026-09-26 — secondary; summary-only; attribution not isolated.
7. Zoho, "Pricing | Zoho Books" — https://www.zoho.com/us/books/pricing/ — accessed 2026-09-26 — primary; content via summary only.
8. Zoho Blog, "Unveiling the Free Plan of Zoho Books for Businesses" — https://www.zoho.com/blog/books/unveiling-the-free-plan-of-zoho-books-for-businesses.html — accessed 2026-09-26 — primary; undated in results, may predate 2025.
9. Costbench, "Is Zoho Books Free? Free Plan Limits & Upgrade Triggers (2026)" — https://costbench.com/software/accounting/zoho-books/free-plan/ — accessed 2026-09-26 — secondary; summary-only.
10. Comparedge, "Zoho Books Pricing 2026: Free & Standard Plans from $20/mo" — https://comparedge.com/tools/zoho-books/pricing — accessed 2026-09-26 — secondary; title only.
11. Homebase, "Official Homebase Pricing" — https://www.joinhomebase.com/pricing — accessed 2026-09-26 — primary; summary-only.
12. Connecteam, "Homebase Review 2026" — https://connecteam.com/reviews/homebase/ ; Costbench, "Homebase Pricing 2026" — https://costbench.com/software/employee-scheduling/homebase/ — accessed 2026-09-26 — secondary (Connecteam is a direct competitor); summary-only; attribution not isolated.
13. Business Wire, "Deel Simplifies Global HR with New Full-Stack Platform" (2023-01-23) — https://www.businesswire.com/news/home/20230123005215/en/Deel-Simplifies-Global-HR-with-New-Full-Stack-Platform — accessed 2026-09-26 — primary press release; summary-only.
14. Pin, "Deel Pricing 2026" — https://www.pin.com/blog/deel-pricing/ ; Gloroots — https://www.gloroots.com/blog/deel-pricing ; People Managing People — https://peoplemanagingpeople.com/tools/deel-pricing/ — accessed 2026-09-26 — secondary; summary-only; attribution not isolated.
15. Connecteam, "Pricing" — https://connecteam.com/pricing/ — accessed 2026-09-26 — primary; summary-only.
16. People Managing People, "Connecteam Pricing Tiers & Costs" — https://peoplemanagingpeople.com/tools/connecteam-pricing/ ; Costbench, "Connecteam Pricing 2026" — https://costbench.com/software/employee-scheduling/connecteam/ — accessed 2026-09-26 — secondary; summary-only.
17. Tech.co, "Square Payroll: Pricing Guide and Review" — https://tech.co/hr-software/square-payroll-pricing ; Merchant Maverick — https://www.merchantmaverick.com/square-payroll-pricing-explained/ ; U.S. News — https://business.usnews.com/payroll-software/square — accessed 2026-09-26 — secondary; summary-only; Square's own pricing page not reached.
18. Toast, "Toast Payroll: Invoice and Billing Information" — https://support.toasttab.com/en/article/Toast-Payroll-Invoice-and-Billing-Information — accessed 2026-09-26 — primary; summary-only.
19. Workstream, "Toast Payroll Pricing… 2026" — https://www.workstream.us/blog/toast-payroll-pricing ; UpMenu — https://www.upmenu.com/blog/toast-pricing/ ; CheckThat.ai — https://checkthat.ai/brands/toast/pricing — accessed 2026-09-26 — secondary; summary-only; attribution not isolated.
20. Payroll4Free, "Features" — https://payroll4free.com/features.html — accessed 2026-09-26 — primary; content via summary only.
21. FitSmallBusiness, "Payroll4Free Review" — https://fitsmallbusiness.com/payroll4free-review/ ; Merchant Maverick, "Payroll4Free Review" — https://www.merchantmaverick.com/reviews/payroll4free-review/ — accessed 2026-09-26 — secondary; summary-only; the two conflict on the tax-service fee.
22. Business Wire, "Bambee Launches New Guided Payroll Product for Small Business with Built in HR Manager Guidance for Free" (2022-01-12) — https://www.businesswire.com/news/home/20220112005448/en/Bambee-Launches-New-Guided-Payroll-Product-for-Small-Business-with-Built-in-HR-Manager-Guidance-for-Free — accessed 2026-09-26 — primary; summary-only; 2022, possibly stale.
23. Business News Daily, "Bambee Review and Pricing Plans in 2026" — https://www.businessnewsdaily.com/hr/bambee-review ; Business.com, "Bambee HR Software Review" — https://www.business.com/reviews/bambee-hr-software/ — accessed 2026-09-26 — secondary; summary-only; attribution not isolated.
24. CaseAgent, "CosmoLex Pricing: CosmoLex Cost vs Clio, Plans and Fees" — https://caseagent.com/blog/cosmolex-pricing ; CheckThat.ai — https://checkthat.ai/brands/cosmolex/pricing ; CounselStack — https://www.counselstack.io/reviews/cosmolex — accessed 2026-09-26 — secondary; summary-only; describes a 2026 repricing, verify with the vendor.
25. LawSites (LawNext), "Clio Launches Its Own Legal-Specific Accounting and Bookkeeping Software as Add-On to Clio Manage" (URL dated 2024-07) — https://www.lawnext.com/2024/07/clio-launches-its-own-legal-specific-accounting-and-bookkeeping-software-as-add-on-to-clio-manage.html — accessed 2026-09-26 — secondary trade press; summary-only.
26. Clio, "Clio Makes Law Firm Finances Approachable With a Centralized Accounting Solution" — https://www.clio.com/about/press/clio-accounting/ — accessed 2026-09-26 — primary; summary-only.
27. LeanLaw, "Clio Alternative: LeanLaw vs Clio for Law Firm Billing (2026)" — https://www.leanlaw.co/blog/comparison/clio-alternative/ — accessed 2026-09-26 — secondary, competitor; summary-only; its "early 2026" launch date conflicts with #25.
28. T-Net News, "Clio Launches Legal Accounting in Clio Manage for Canadian Law Firms" (2026-09-25) — https://www.bctechnology.com/news/2026/9/25/Clio-Launches-Legal-Accounting-in-Clio-Manage-for-Canadian-Law-Firms.cfm?id=50935 — accessed 2026-09-26 — secondary; title/summary only.
29. ServiceTitan Help, "Accounting Integrations Home" — https://help.servicetitan.com/docs/accounting-integrations-overview — accessed 2026-09-26 — primary; summary-only.
30. Field Service Guide, "ServiceTitan QuickBooks Integration Guide (2026)" — https://fieldserviceguide.com/servicetitan-quickbooks-integration-guide-2026/ — accessed 2026-09-26 — secondary; summary-only; attribution not isolated.
31. Tight, "What would it look like if ServiceTitan embedded accounting?" — https://www.tight.com/blog/servicetitan-embedded-accounting — accessed 2026-09-26 — secondary; Tight sells embedded accounting (interested party); title only.
32. Jobber Help, "How Items Sync Between Jobber and QuickBooks Online" — https://help.getjobber.com/hc/en-us/articles/10487017203223-How-Items-Sync-Between-Jobber-and-QuickBooks-Online-NEW-QuickBooks-Integration ; CapForge — https://capforge.com/post/from-field-to-the-ledger-the-definitive-guide-to-jobber-and-quickbooks-integration/ — accessed 2026-09-26 — primary + secondary; summary-only; attribution not isolated.
33. Check, "Housecall Pro" partner page — https://www.checkhq.com/partners/housecall-pro — accessed 2026-09-26 — primary (the payroll provider's own page); summary-only.
34. Housecall Pro, "Payroll Software for Small Businesses" — https://www.housecallpro.com/features/payroll/ ; "What is Payroll Software?" — https://www.housecallpro.com/resources/what-is-payroll-software/ — accessed 2026-09-26 — primary; summary-only; which page gave the price not isolated.
35. Vagaro, "Payroll Services for Small Business" — https://www.vagaro.com/en-ca/pro/payroll — accessed 2026-09-26 — primary (Canadian page); appeared in results only.
36. GlossGenius, "Vagaro pricing: plans, processing fees, and add-ons" — https://glossgenius.com/blog/vagaro-cost ; CheckThat.ai — https://checkthat.ai/brands/vagaro/pricing ; The SMB Guide — https://www.thesmbguide.com/vagaro — accessed 2026-09-26 — secondary (GlossGenius is a competitor); summary-only; figures conflict.
37. Pembee, "Mindbody vs Vagaro" — https://www.pembee.app/blog/mindbody-vs-vagaro — accessed 2026-09-26 — secondary; summary-only.
38. Buildertrend, "Xero Integration" — https://buildertrend.com/integration/xero/ ; "QuickBooks Online Integration" — https://buildertrend.com/help-article/quickbooks-online-integration-overview/ — accessed 2026-09-26 — primary; summary-only.
39. Procore Support, "Accounting Integrations" — https://support.procore.com/integrations/category-accounting — accessed 2026-09-26 — primary; summary-only.
40. ezyVet, "Xero" — https://www.ezyvet.com/integration/xero ; Vet Practice Magazine, "Profitdiagnostix and ezyVet join forces…" — https://www.vetpracticemag.com.au/profitdiagnostix-and-ezyvet-join-forces-to-help-boost-the-profitability-of-vet-practices/ — accessed 2026-09-26 — primary + secondary; summary-only.
41. Open Banking Tracker, "Embedded Payroll Providers 2026 – Payroll APIs for Platforms" — https://www.openbankingtracker.com/embedded-finance/category/payroll — accessed 2026-09-26 — secondary aggregator; summary-only.
42. Sacra, "Gusto vs. Rippling vs. Deel vs. Check" — https://sacra.com/p/gusto-vs-rippling-vs-deel-vs-check/ — accessed 2026-09-26 — secondary research; appeared in results; whether it is the source of the one-third figure is not isolated.
43. Tidemark, "Payroll" (VSKP chapter) — https://www.tidemarkcap.com/vskp-chapter/payroll — accessed 2026-09-26 — secondary (venture-firm research); summary-only.
44. Gusto Embedded Blog, "Pricing for embedded finance SaaS products" — https://embedded.gusto.com/blog/pricing-for-embedded-finance-saas-products-infographic/ — accessed 2026-09-26 — primary; summary-only.
45. Check, "Embed Payroll for Your Customers" — https://www.checkhq.com/platform/payroll ; Check home page — https://www.checkhq.com/ — accessed 2026-09-26 — primary; summary-only; no public price found; the Bambee case came from Check's site according to the summary, exact page not isolated.
46. Everee, "Everee payroll pricing" — https://www.everee.com/pricing/ ; SaaSworthy — https://www.saasworthy.com/product/everee-payroll/pricing — accessed 2026-09-26 — primary + aggregator; summary-only; attribution not isolated.
47. HR.software, "Zeal Review 2026" — https://www.hr.software/reviews/zeal — accessed 2026-09-26 — secondary; summary-only.
48. Zeal, "Why More Software Platforms Are Offering Payroll" — https://www.zeal.com/guides/why-more-software-platforms-are-offering-payroll — accessed 2026-09-26 — primary (vendor); appeared in results only.
49. FTC, "FTC Issues Opinion Finding that TurboTax Maker Intuit Inc. Engaged in Deceptive Practices" (Jan 2024) — https://www.ftc.gov/news-events/news/press-releases/2024/01/ftc-issues-opinion-finding-turbotax-maker-intuit-inc-engaged-deceptive-practices — accessed 2026-09-26 — primary; summary-only (WebFetch blocked).
50. U.S. Court of Appeals for the Fifth Circuit, No. 24-60040, opinion — https://www.ca5.uscourts.gov/opinions/pub/24/24-60040-CV0.pdf — accessed 2026-09-26 — primary; summary-only; the March 2026 date comes from the summaries.
51. PYMNTS, "US Appeals Court Tosses FTC Order Over Intuit's 'Free' TurboTax Ads" — https://www.pymnts.com/cpi-posts/u-s-appeals-court-tosses-ftc-order-over-intuits-free-turbotax-ads/ — accessed 2026-09-26 — secondary; summary-only.
52. Intuit Blog, "Intuit Applauds Fifth Circuit Decision in its Favor vs FTC" — https://www.intuit.com/blog/news-social/intuit-applauds-fifth-circuit-decision-in-its-favor-vs-ftc/ — accessed 2026-09-26 — primary, but Intuit is a party to the case; appeared in results only.
53. eCFR, 16 CFR Part 251 and § 251.1 — https://www.ecfr.gov/current/title-16/chapter-I/subchapter-B/part-251 ; https://www.ecfr.gov/current/title-16/chapter-I/subchapter-B/part-251/section-251.1 — accessed 2026-09-26 — primary; summary-only (WebFetch blocked); the quoted phrases are as the summary rendered them, not read directly.
54. LII, "16 CFR § 251.1 – The guide." — https://www.law.cornell.edu/cfr/text/16/251.1 — accessed 2026-09-26 — mirror of the primary text; summary-only.
55. Library of Congress, "Code of Federal Regulations: Guide Concerning Use Of The Word 'Free' And Similar Representations, 16 C.F.R. (1973)" — https://www.loc.gov/item/cfr1973037-T16CIP251 — accessed 2026-09-26 — primary archival record; title only.

---

## 7. Practitioner-voice lens — small-business owners and bookkeepers on competitor reliability

Researched by a dedicated pass (30 searches; two refused because the search
tool cannot reach reddit.com, and two more by the cap). SourceForge was read
directly; Trustpilot, BBB, Capterra, TrustRadius, the QuickBooks Community,
ConsumerAffairs and irs.gov were all blocked. **This section has no Reddit
evidence at all.** Summary quotes are marked as such. **No source gave a
tax-filing error rate for any vendor**, and complaint counts have no
denominators, so they are not error rates.

| Vendor | Ratings found | Recurring complaints | Positive signal | Confidence |
|---|---|---|---|---|
| Gusto | BBB A+, accredited 2024; 321 complaints in 3 years [4]. Trustpilot about 2,300–2,450 reviews, score unconfirmed [3]. G2 4.6 [8] | State-level filing errors left for the customer to fix (wrong EIN on 940/941; unfiled state taxes); "I spent no less than 30 hours on the phone with them…" (search-summary quote) [3][4]; chat-first support; Simple price rise [6] | Documented tax-notice upload process [5]; the 2022 Colorado notice was a communication error, not a mis-filing [1][2] | medium-low |
| ADP RUN | Trustpilot covers all of adp.com, about 3,000 reviews; "1.2/5" probable but unconfirmed [11][14]. BBB A+ [12] | Filing failures surfacing years later — one review cites 2018–2020 notices arriving in 2025, with penalties over $200,000 [10]; hard to cancel; no public pricing [14][15] | ADP says it pays penalties caused by its own errors (page not pinned; probably [14]) | low-medium (RUN not separable from Workforce Now) |
| QuickBooks Payroll | Trustpilot about 1,500 reviews [25]; other figures untraced | Late tax payments followed by penalty notices [17]; a $50 "investigation fee" despite the guarantee [18]; repeated price rises [22][24]; direct-deposit delays [20][21] | Written penalty-coverage policy (≤ $25k/yr, conditions apply) [23] | medium that it happens; low on how often |
| BambooHR Payroll | No payroll-specific rating found [29][32] | Thin; aggregator summaries of tax and 401(k) errors, untraced [30][31] | SourceForge 4.7 from 37 reviews (whole product) [32] | low — absence is the finding |
| Rippling | **Trustpilot 4.5/5, about 2,100 reviews** [33]; BBB A+, 92 complaints in 3 years [34] | Double-paid quarterly tax during implementation, about 6 months to recover [34]; module pricing adds up [36] | Best scores and fewest complaints of the six; its review-invitation practice was not checked | medium-low |
| Paylocity | **Trustpilot 1.3/5, about 110–140 reviews** [37] | Unfiled taxes found years late, blamed on customer setup, fixed for a fee [37][39]; one undated finance-forum user reports about 30% quarterly-report errors across 60 accounts [38] | Long BBB accreditation [39] | low-medium |

**Structural to the category** (seen at every vendor with enough evidence):
1. Errors surface late.
2. The customer does the chasing.
3. Blame turns on the customer's inputs.
4. Changeovers are the riskiest time.
5. **Liability stays with the employer** — the IRS says so, and so does the
   trade press [42]–[46].

"They file your taxes for you" swaps filing yourself for catching and disputing
the provider's mistakes, and the employer stays liable either way. **Nothing
here measures an error rate**, so it supports neither "full-service is less
reliable than doing it yourself" nor the reverse.

### Sources (§7)

1. Colorado Treasury press release "10192022 payroll firm gusto sends colorado businesses incorrect information for tax" — https://treasury.colorado.gov/press-release/10192022-payroll-firm-gusto-sends-colorado-businesses-incorrect-information-for-tax — accessed 2026-09-26 — fetch blocked; summary only; government source, dated 10/19/2022 per URL.
2. Denver Gazette "Gusto sent false tax filing information to Colorado businesses" — https://denvergazette.com/news/business/gusto-sent-false-tax-filing-information-to-colorado-businesses/article_034e4aca-518b-11ed-af9c-3b307820789d.html — accessed 2026-09-26 — title only.
3. Trustpilot, Gusto — https://www.trustpilot.com/review/gusto.com (also ?page=3, ?page=6; uk./ca. variants) — accessed 2026-09-26 — fetch blocked; titles and summary; leans negative.
4. BBB, Gusto — https://www.bbb.org/us/ca/san-francisco/profile/payroll-services/gusto-1116-451512 (and /complaints) — accessed 2026-09-26 — fetch blocked; summary; leans negative.
5. Gusto Help Center, handling a tax notice — https://support.gusto.com/article/106621962100000/What-to-do-if-you-get-a-tax-notice-from-an-agency — accessed 2026-09-26 — vendor; summary.
6. Gusto pricing guides — https://rivermate.com/blog/gusto-pricing ; https://www.tinyteam.io/blog/gusto-pricing ; https://www.tarmack.com/blog/gusto-pricing — accessed 2026-09-26 — summary; which site gave the figure not confirmed.
7. SourceForge, Gusto — https://sourceforge.net/software/product/Gusto/ — accessed 2026-09-26 — read directly; 6 reviews; leans positive.
8. G2, Gusto vs Rippling — https://www.g2.com/compare/gusto-vs-rippling — accessed 2026-09-26 — summary; vendor-invited reviews, lean positive.
9. Fortune video (URL wording only) — https://fortune.com/videos/watch/gusto-ceo%3A-1-in-3-companies-fined-for-incorrectly-doing-payroll-taxes/2c8d697f-1331-44a0-a53a-7c835b1c2abe — accessed 2026-09-26 — not viewed; vendor claim.
10. ConsumerAffairs, ADP — https://www.consumeraffairs.com/business/adp.html (and ?page=7) — accessed 2026-09-26 — fetch blocked; summary; complaint venue.
11. Trustpilot, ADP — https://www.trustpilot.com/review/adp.com ; https://ca.trustpilot.com/review/adp.com?page=3 — accessed 2026-09-26 — titles and summary; leans negative; covers all of ADP.
12. BBB, ADP, Inc. — https://www.bbb.org/us/nj/roseland/profile/payroll-services/adp-inc-0221-12001629/accreditation-information — accessed 2026-09-26 — summary.
13. Business News Daily, ADP review — https://www.businessnewsdaily.com/16058-adp-review.html — accessed 2026-09-26 — summary; probable source of untraced figures.
14. StartupOwl, ADP RUN review — https://startupowl.com/reviews/adp-run — accessed 2026-09-26 — fetch blocked; summary; review site.
15. PayrollDetective, ADP pricing — https://www.payrolldetective.com/payroll-providers/adp-pricing — accessed 2026-09-26 — fetch blocked; summary.
16. SourceForge, RUN Powered by ADP — https://sourceforge.net/software/product/RUN-Powered-by-ADP/ — accessed 2026-09-26 — read directly; 0 reviews.
17. QuickBooks Community "Quickbooks Screwed up my IRS Tax Payment" — https://quickbooks.intuit.com/learn-support/en-us/taxes/quickbooks-screwed-up-my-irs-tax-payment/00/1600651 — accessed 2026-09-26 — summary; user forum.
18. QuickBooks Community "QB Full-Service Payroll Tax Notice Fee" — https://quickbooks.intuit.com/learn-support/en-us/employees-and-payroll/qb-full-service-payroll-tax-notice-fee/00/475309 — accessed 2026-09-26 — summary; older thread.
19. QuickBooks Community "QB forcing users to use their payroll tax filing and removing manual payments for payroll" — https://quickbooks.intuit.com/community/employees-and-payroll-2/qb-forcing-users-to-use-their-payroll-tax-filing-and-removing-manual-payments-for-payroll-375419 — accessed 2026-09-26 — title only.
20. QuickBooks Community "Direct Deposit Status 08/29/2025" — https://quickbooks.intuit.com/learn-support/en-us/employees-and-payroll/direct-deposit-status-08-29-2025/00/1573921 — accessed 2026-09-26 — summary.
21. QuickBooks Community "Is there a delay with payroll deposits today?" — https://quickbooks.intuit.com/learn-support/en-us/account-management/is-there-a-delay-with-payroll-deposits-today/00/1573165 — accessed 2026-09-26 — summary.
22. QuickBooks Community "Price increase 2025" — https://quickbooks.intuit.com/learn-support/en-us/other-questions/price-increase-2025/00/1546802 — accessed 2026-09-26 — title only.
23. Intuit, Tax Penalty Protection — https://quickbooks.intuit.com/payroll/tax-penalty-protection/ — accessed 2026-09-26 — vendor; summary.
24. 2026 QuickBooks price posts — https://stephsbooks.com/news/quickbooks-online-price-increase-2026 ; https://www.schoolofbookkeeping.com/blog/2026QBOPriceIncrease ; https://www.kempercpa.com/news/upcoming-changes-to-quickbooks-desktop-pricing-effective-february-2026 ; https://www.bradymartz.com/quickbooks-desktop-pricing-update-what-businesses-should-expect-in-2026/ — accessed 2026-09-26 — titles and summary; accountant/bookkeeper voices.
25. Trustpilot, Intuit (quickbooks.com) — https://www.trustpilot.com/review/quickbooks.com (and ?page=8) — accessed 2026-09-26 — title only.
26. QuickBooks Payroll reviews — https://www.business.org/finance/accounting/quickbooks-payroll-review/ ; https://www.businessnewsdaily.com/payroll/intuit-quickbooks-review — accessed 2026-09-26 — summary; untraced figures.
27. BBB, Intuit, Inc. — https://www.bbb.org/us/ca/mountain-view/profile/computer-hardware/intuit-inc-1216-202832/customer-reviews — accessed 2026-09-26 — title only.
28. SourceForge, QuickBooks Payroll — https://sourceforge.net/software/product/QuickBooks-Payroll/ — accessed 2026-09-26 — read directly; 1 review.
29. Trustpilot, BambooHR — https://www.trustpilot.com/review/bamboohr.com — accessed 2026-09-26 — title only.
30. BambooHR Payroll aggregator reviews — https://sonary.com/b/bamboohr/bamboohr+payroll-services/ ; https://top10payrollservice.com/bamboohr-review/ — accessed 2026-09-26 — summary; second-hand.
31. hr.university, BambooHR — https://hr.university/tools/bamboohr/ — accessed 2026-09-26 — summary.
32. SourceForge, BambooHR — https://sourceforge.net/software/product/BambooHR/ — accessed 2026-09-26 — read directly; 37 reviews; lean positive.
33. Trustpilot, Rippling — https://www.trustpilot.com/review/rippling.com (and ?page=2) — accessed 2026-09-26 — titles.
34. BBB, Rippling — https://www.bbb.org/us/ca/san-francisco/profile/computer-software-developers/rippling-1116-919641 (and /complaints) — accessed 2026-09-26 — summary.
35. Rippling review round-ups — https://saasflags.com/products/rippling ; https://www.b2breviews.com/reviews/rippling/ — accessed 2026-09-26 — summary; untraced.
36. SourceForge, Rippling — https://sourceforge.net/software/product/Rippling/ — accessed 2026-09-26 — read directly.
37. Trustpilot, Paylocity — https://www.trustpilot.com/review/paylocity.com (and ?page=3, ?page=5) — accessed 2026-09-26 — titles and summary; leans negative.
38. Proformative "Paylocity complaints?" — https://www.proformative.com/questions/paylocity-complaints/ — accessed 2026-09-26 — summary; practitioner forum; undated.
39. BBB, Paylocity Corporation — https://www.bbb.org/us/il/schaumburg/profile/payroll-services/paylocity-corporation-0654-53000465 — accessed 2026-09-26 — summary.
40. Workology marketplace, Paylocity — https://marketplace.workology.com/paylocity/ — accessed 2026-09-26 — summary.
41. SourceForge, Paylocity — https://sourceforge.net/software/product/Paylocity/ — accessed 2026-09-26 — read directly.
42. IRS "Outsourcing payroll duties" — https://www.irs.gov/businesses/small-businesses-self-employed/outsourcing-payroll-duties — accessed 2026-09-26 — fetch blocked; summary; primary source.
43. IRS, Trust Fund Recovery Penalty — https://www.irs.gov/businesses/small-businesses-self-employed/employment-taxes-and-the-trust-fund-recovery-penalty-tfrp — accessed 2026-09-26 — summary.
44. Guides on switching mid-year — https://www.opstart.co/mid-year-payroll-provider-changes/ ; https://apspayroll.com/blog/switching-payroll-companies-mid-quarter/ — accessed 2026-09-26 — summary; vendor blogs.
45. Thomson Reuters "Outsourcing payroll does not necessarily transfer employment tax risk, executive says" — https://tax.thomsonreuters.com/news/outsourcing-payroll-does-not-necessarily-transfer-employment-tax-risk-executive-says/ — accessed 2026-09-26 — title only; undated.
46. TWR blog "IRS Warns Employers to Choose Carefully When Selecting a Payroll Service Provider" — https://www.twrblog.com/2020/08/irs-warns-employers-to-choose-carefully-when-selecting-a-payroll-service-provider/ — accessed 2026-09-26 — title only; Aug 2020 per URL.

---

## Synthesis

**1. The brief's frame is a category mismatch, and correcting it is the most
useful finding here.**
- SAIRNbiz is accounting + HR records with **calculation-only** payroll.
- All six named competitors process payroll. None bundles a native general
  ledger in the same subscription: Intuit sells two, about $200/month for 10
  employees at secondary prices (§1.4).
- SAIRNbiz's defensible position is the ledger, AP/AR, vendor/1099 and HR
  records at **$0 incremental, uncapped, inside the vertical app**. No
  competitor found does this. Vertical SaaS integrates with QuickBooks/Xero,
  and the legal vendors with native ledgers charge for them (§6.2).
- Its indefensible position would be any claim that it replaces a payroll
  processor.

**2. On payroll, the market is moving the other way, and fast.**
- At least seven embedded providers now let vertical SaaS ship full-service
  payroll as a paid add-on: Check, Gusto Embedded, Salsa, Zeal, Everee, ADP
  Embedded Payroll (September 2025) and Rollfi.
- Typical pricing is $35–69/month plus $5–9 PEPM, and the platform keeps about
  two-thirds (§2.4, §6.3). Housecall Pro's Check-powered payroll ($40 + $6) is
  the clearest worked example.
- A competitor to any SAIRN vertical can add real payroll without becoming a
  payroll company.
- If SAIRN wants payroll parity or revenue, embedding is the known route. The
  catch (§3.5): a reporting-agent-style provider takes on **no** IRS liability,
  so failures land on the employer, and employers then pursue the vendor in
  contract (§5.6).
- Whether to embed is a product decision this document does not make.

**3. The refusal-to-compute design is vindicated, with one boundary that
matters.**
- It keeps SAIRNbiz off the failure paths that dominate the liability record:
  missed deposits, filing errors, outages and a bank-partner failure (§5).
- It does not protect the four figures SAIRNbiz *does* compute:
  - overtime (weekly-only; F2);
  - gross (scheduled hours; F2);
  - FICA (no wage-base cap, no Additional Medicare; F3);
  - the 1099 count (stale threshold; F1).
- **Those four are exactly where the 2025–2026 regulatory calendar moved** (§3,
  §4), and exactly the regular-rate/rounding shape the Paylocity suits are
  about.

**4. The 09-03 audit's row A1 now has evidence, not just an argument.**
- In 2025–2026 all of these moved:
  - the 1099 threshold (by payment date; indexed from 2027);
  - the Social Security wage base (annually);
  - FUTA credit reductions (annually);
  - the Roth catch-up threshold (prior-year keyed);
  - W-2 codes (new for 2026);
  - the I-9 edition (a printing expired 2026-07-31);
  - state paid-leave rates;
  - 19 state minimum wages;
  - the daily-overtime states' rules.
- None of the thresholds SAIRNbiz touches is dated or configurable, and one is
  already wrong (F1).

**5. The HR-compliance obligations SAIRNbiz does not touch are real, and one got
sharper in 2026.** Those obligations are I-9, E-Verify, new-hire reporting,
worker classification and leave-program contributions.
- ICE's 2026-03-16 reclassification makes more than ten I-9 error types
  immediately fineable (§4.1).
- Ohio added an any-size E-Verify mandate for nonresidential construction
  (§4.2).
- This is a positioning finding rather than a build list: **SAIRNbiz should not
  be described as HR-compliance coverage.** Competitors vary here: Gusto
  reportedly includes I-9 on every plan, QuickBooks on Premium and up, ADP
  through a partner app, and Paylocity integrates E-Verify (§1.2).

**6. No one has measured reliability.**
- Practitioner complaints are the same across full-service providers: late
  surfacing, customer chasing, and blame on inputs.
- **No error rate exists for any vendor** (§7). Neither SAIRNbiz nor a
  competitor can claim superiority on reliability from this evidence.

**7. "Free" is a known model with a known legal edge.**
- Capped freemium backbones funded by an adjacent paid product are common
  (§6.1). SAIRNbiz's version is uncapped and bundled, which is distinct.
- Its only "free" wording sits in an AI prompt (F5).
- The FTC Guide wants purchase conditions stated at the outset (§6.4).
- The Intuit precedent shows the enforcement appetite even though the order
  fell on procedure (§5.4).
- The Wave precedent shows why "free forever" is a promise best not made
  (§6.4).

## What this document does not establish or decide

- **It is not legal advice.** That covers the 1099 threshold, "free" wording,
  I-9/E-Verify, classification and overtime. Counsel should review any
  customer-facing wording.
- **It does not fix F1–F5.** Each needs the owning build session to re-derive
  it and decide. This lane is `docs/cloud-research/` only.
- **It does not establish SMB payroll market share.** No credible estimate with
  a disclosed method was found (§2.2).
- **It does not fully establish competitor guarantee terms.** Gusto's remedy was
  only partly captured; BambooHR's, Rippling's and Paylocity's limits were not
  found.
- **It does not decide whether SAIRNbiz should add or embed real payroll.** That
  is a product decision, within `sairn-decision-gate`'s scope.
- **It does not establish SAIRN's cost to serve an uncapped free SAIRNbiz.**
- **Unresearched because the session search cap was exhausted:**
  - BambooHR: guarantee, I-9/E-Verify, new-hire reporting, multi-state support,
    and litigation.
  - Collapses and PEOs: MyPayrollHR, and PEO failures.
  - DOL and E-Verify: FAB 2024-1 status, opinion letters and the PAID program,
    auto-deduction and rounding guidance, the FAR E-Verify clause, the
    California AB5 re-source, the I-9 second-offense range, E-Verify's status
    during the February 2026 lapse, and ICE counts of Notices of Inspection.
  - IRS: tip reporting on the 2026 1099s, the e-file waiver form, and the 2027
    wage base.
  - Adjacent industries: the Mint shutdown, the Google Workspace legacy
    edition, Square's free tier, H&R Block's ownership of Wave, the Clio
    Accounting price, IDEXX Neo, Salsa's pricing, Mindbody's payroll, and
    Vagaro's payroll provider.
  - Market: Rippling renewal lock-in, Intuit's payroll customer count, Gusto's
    total funding, BambooHR's funding, a count of US employer firms, the
    Guideline price and completion date, Zeal's Series B date, Everee's
    customers, and a Rippling v. Deel trial date.

## Decay

- **Prices** move every quarter. The Gusto Simple rise (2026, date disputed),
  the QuickBooks Workforce and QuickBooks Online changes (July and August 2026)
  and the CosmoLex repricing (July–September 2026) all happened inside this
  research window.
- **Regulatory dates falling due soon:**
  - New Jersey ABC regulations: 2026-10-01;
  - the next Social Security wage base: announced October 2026;
  - FUTA credit reductions: November 2026;
  - last FIRE filing: 2026-11-19;
  - IRIS-only e-filing: 2027-01-01;
  - 1099 threshold indexing: from 2027;
  - Form I-9 edition expiry: 2027-05-31.
- **Still pending:** DOL's independent-contractor final rule, and *Rippling v.
  Deel*.
- **Treat this document as current only through 2026-09-26.** Re-verify any
  figure before quoting it outside the team. Almost everything here rests on
  search snippets rather than full-page reads (§0.1).
