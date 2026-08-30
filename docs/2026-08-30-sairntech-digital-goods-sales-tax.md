# sairntech.com — digital-goods sales tax

**Researched 2026-08-30 from primary sources** — codes.ohio.gov, the Ohio
Administrative Code, state departments of revenue, the Streamlined Sales Tax
Governing Board, and Stripe's own documentation.

**Not tax or legal advice.** A primary-source read by a non-professional, to the
same standard as the ORC 2915 and 38 U.S.C. 5901 passes. Three items must go to
a CPA regardless — see the last section.

Flagged as a real research item in
`2026-08-30-sairntech-corporate-site-scoping.md` §10. This closes it.

---

## THE HEADLINE: SaaS licences and ebooks are NOT the same product for tax

This is the crux of the catalog build and it has to be in the data model from
day one.

| | **App licences (SaaS)** | **Ebooks** |
|---|---|---|
| **Ohio statutory hook** | ORC 5739.01(B)(3)(e) — ADP / computer services / electronic information services | ORC 5739.01(B)(12) — specified digital products |
| **Business-use gate?** | **YES** — taxable only *"for use in business"* | **NO** — taxable to everyone |
| **Subscription vs permanent** | n/a (a service) | **Irrelevant**: *"permanent use or less than permanent use, regardless of whether continued payment is required"* |
| **Sold to an individual consumer** | Arguably **not** taxable in Ohio | **Taxable** |
| **"True object" test** | **Yes** — *Cincinnati Fed. S. & L. Co. v. McClain* (2022) | No |

**They diverge nationally too, in both directions.** New York taxes SaaS and
exempts ebooks. Georgia taxes ebooks and exempts SaaS. This is structural, not
accident: **SSUTA § 332(A)** forbids a member state from including digital books
within its definition of *"computer software"* or *"tangible personal
property"* — so the two are pulled by different statutory levers and never move
together.

**A single "is it taxable" boolean per state gives wrong answers in both
directions.**

---

## 1. Ohio — home state, certain physical nexus

### SaaS: taxable, but only *for use in business* — and "business" includes nonprofits

**ORC 5739.01(B)(3)(e)** taxes transactions where ADP, computer services or
electronic information services are provided *"**for use in business** when the
true object of the transaction is the receipt by the consumer of"* those
services rather than personal or professional services.

**ORC 5739.01(Y)(1)(c)** — *"'Electronic information services' means providing
access to computer equipment by means of telecommunications equipment for the
purpose of either… examining or acquiring data stored in or accessible to the
computer equipment… placing data into the computer equipment."*

A browser-accessed app running against SAIRN's servers sits squarely inside
that.

**But the business-use gate is narrower relief than it sounds.**
**OAC 5703-9-46(A)(7)** defines "business" as an ongoing enterprise
*"**whether or not the person or persons conducting such enterprise are
for-profit or nonprofit entities**."*

> **A nonprofit lodge using the app is engaged in "business" for this test.**
> Nonprofit status does not remove the sale from (B)(3)(e).

### THE WORDING RISK — "licence" is a decision, not cosmetics

Ohio taxes **prewritten software as tangible personal property** with **no
business-use gate at all**: ORC 5739.01(WW) includes prewritten software in
"tangible personal property", and (B)(1) taxes *"a license to use or consume
tangible personal property."*

If the customer never receives software and only accesses our servers, the
ADP/EIS analysis should control. **But invoicing it as a "software licence"
invites the other characterization — which would make it taxable to individual
consumers too.**

**Product consequence:** if it is hosted access, describe it as hosted access.
This is a naming decision with a tax outcome.

### Ebooks: taxable to everyone, no gate

**ORC 5739.01(B)(12)** — *"All transactions by which a specified digital product
is provided for permanent use or less than permanent use, **regardless of
whether continued payment is required**."* (OOO) defines "specified digital
product" to include a *"digital book."*

The Ohio Department of Taxation's taxability page (dated **2025-10-14**) lists
*"Downloadable Content (e-books, music, and movies)"* among items *"typically
purchased for personal use that are generally subject to sales tax."*

### Custom development: generally NOT taxable — if separately stated

Two independent grounds. **ORC 5739.01(Y)(2)(e)** names *"**custom software**"*
among nontaxable personal and professional services. And **ORC 5739.01(BBB)**
excludes from "prewritten computer software" any modification where *"there is a
**reasonable, separately stated charge**"* for it.

**ODT's own bundling warning:** *"Sales of mixed taxability items/services
without itemization of the mixed taxable/nontaxable items/services makes the
entire purchase taxable."*

> **Line-item every invoice.** Bundling is the most avoidable way to make
> non-taxable revenue taxable.

**Caution from *Cincinnati Federal*:** the BTA rejected a custom-software
argument because the taxpayer was buying services that *used* software.
**Calling something "custom development" does not make it custom development.**

### Rate

**5.75% state** (ORC 5739.02(A)(1)), with county and transit permissive rates
stacking on top. Combined rates were **not verified** — ODT's rate tables
returned 403/404. Use Ohio's "The Finder" per address.

---

## 2. Stripe — the assumption was right, and there is a fork underneath it

### Stripe-as-processor is NOT a marketplace facilitator. SAIRN stays liable.

**Confirmed against Ohio's own statutory test.** ORC 5741.01(T) requires
**(T)(1) AND (T)(2) AND (T)(3)**. (T)(1) is marketplace-side — listing the
product, owning the marketplace, setting the price, branding the sale as the
facilitator's. (T)(2) is payment-side, including *"provides payment processing
services for the sale."*

**Stripe satisfies (T)(2)(b) and fails (T)(1) entirely.** It does not list our
products, own the marketplace, set our prices, or brand the sale as Stripe's.
**We own the marketplace. We are the seller.**

Stripe says so itself: *"**You must register with the tax authority in a location
to collect taxes there**"* and *"**You must file and remit the tax you collect
for every location where you're registered.**"*

**Stripe Tax is a separate product** — calculation, threshold monitoring,
optional filing partners. **It does not assume liability.**

### ⚠️ THE FORK: Stripe Managed Payments IS merchant of record and DOES take the burden

Different product, materially different answer. From Stripe's Managed Payments
tax documentation, it *"registers and files tax returns with local tax
authorities"* and *"remits collected taxes"*, with **"No action is required from
you to satisfy indirect tax compliance requirements on the sale of digital
products in these countries."* The US is supported. Sales are branded *"Sold
through Link, LLC"* — which would itself satisfy Ohio's (T)(1)(i)
branding limb.

> **"Stripe" is not one answer.** Processor + Stripe Tax → **we are liable**.
> Managed Payments → **Stripe is merchant of record.** This is a genuine
> architectural fork and it is cheapest to decide before anything is built.

*(Merchant-of-record and marketplace-facilitator are legally distinct concepts
with similar economic effect here. Do not use them interchangeably in any
document.)*

**Contrast worth knowing:** Amazon KDP or Gumroad list the product in a
marketplace they own *and* collect the price — both limbs — so they are
facilitators and collect/remit for us. **The same PDF sold from sairntech.com
via Stripe checkout is entirely our burden.** Same file, same buyer, completely
different compliance load. That is a real channel decision for the ebook line.

---

## 3. The nonprofit exemption — the answer is mostly NO, and it kills a pricing assumption

**ORC 5739.02(B)(12)** exempts sales to churches, **501(c)(3)** organizations,
and nonprofits *"operated exclusively for charitable purposes"* — then defines
charitable purposes narrowly and exhaustively (relief of poverty, improvement of
health, homes for the aged, educational broadcasting, animal adoption,
institutions of learning, PTAs, community arts centres, performances, scientific
research).

**Our named customers are fraternal lodges and veterans posts** — typically
**501(c)(8), (c)(10), (c)(19) or (c)(4)**, *not* (c)(3), and outside the
enumerated purposes.

**The only veterans provision is ORC 5739.02(B)(33)**, and it reaches
*"the **state headquarters** of any veterans' organization… **for use by the
headquarters**"* — **state headquarters only. A local VFW or Legion post does
not qualify.**

Corroborating: the Streamlined exemption certificate Ohio accepts offers
*"Charitable organization"*, *"Religious or educational organization"* and
*"Educational Organization"* — **there is no fraternal or veterans category.**

> **Assume fraternal-lodge and veterans-post customers are TAXABLE in Ohio**
> unless a specific one holds 501(c)(3) status. Some lodges run a separate
> 501(c)(3) foundation — the exemption attaches to *that entity as buyer*, not
> to the lodge. **Do not build pricing around a nonprofit discount that may not
> exist.**

This lands on the same veterans/fraternal fault line as ORC 2915.01 (V)(2)/(V)(3),
the officer titles, and IRC § 170(c)(3)/(c)(4). **Fourth independent legal
regime splitting on that axis.**

---

## 4. The exemption certificate is still a real product requirement

For customers who *do* qualify, and for resale claims. All statutory, from
**ORC 5739.03(B)**:

- *"the vendor **must obtain** from the consumer, a certificate specifying the
  reason that the sale is not legally subject to the tax"*, **in hard copy or
  electronic form** — so capture it in-app.
- *"A vendor that obtains a **fully completed** exemption certificate… is
  relieved of liability."* **A partially filled form protects nothing** —
  validate required fields.
- *"**If no certificate is provided or obtained within ninety days** after the
  date on which such sale is consummated, it shall be presumed that the tax
  applies."* **A hard 90-day clock. Build an alert, not a hope.**
- *"The vendor shall **maintain records**, including exemption certificates… and
  provide them to the tax commissioner on request."* **Store the artifact, not a
  boolean.**

**Multiple points of use — ORC 5739.033(D)(1)(a).** A business consumer buying
software or a service that *"will be concurrently available for use in more than
one taxing jurisdiction"* delivers an MPU certificate, and *"the vendor is
relieved of its obligation to collect, pay, or remit the tax due."* **For any
multi-location customer, this is the field that saves us from apportioning their
tax ourselves.** It remains in effect until revoked in writing.

**Stripe explicitly will not do this:** *"Stripe Tax **doesn't validate required
documentation** for supporting an exemption, such as customer exemption
certificates. **You're responsible**…"* It gives a flag
(`Customer.tax_exempt`). **The flag is not the compliance artifact — the
retained certificate is.**

---

## 5. What to do, in order

### Before the first sale — none of this is threshold-dependent

1. **Register for an Ohio vendor's license.** Physical nexus exists today.
   OAC 5703-9-46(C) requires it for anyone in Ohio selling ADP/computer/EIS for
   use in business.
2. **Decide the Stripe architecture** (§2). Highest-leverage decision here and
   cheapest to make now.
3. **Decide what we are selling and name it accordingly** (§1, the wording risk).
4. **Three product classes in the schema** — SaaS access / specified digital
   product / professional services — each with its own tax code. **Retrofitting
   means re-running historical tax on every past order.**
5. **Build the exemption-certificate feature** with reason code, required-field
   validation, 90-day alert, indefinite retention, produce-on-demand export, and
   an MPU option.
6. **Capture business-vs-individual buyer status at checkout for SaaS** —
   dispositive in Ohio, rate-determinative in Connecticut.
7. **Enforce line-item itemization on every invoice.**
8. **Turn on Stripe Tax threshold monitoring.** Free to monitor. **Do not
   register anywhere else yet** — registering without nexus creates a permanent
   filing obligation for no benefit.

### Ohio filing, once registered

**ORC 5739.12(A)(1)** — returns due *"on or before the twenty-third day of each
month"*, filed electronically. **ORC 5739.12(B)(1)** gives a **0.75% discount**
for timely filing. **File even in zero-revenue months** — registration creates
the duty, not revenue.

### After crossing thresholds

Register **prospectively**, only where nexus exists. Use **free CSP services in
Streamlined member states** where we are a *remote* seller (not Ohio). Two traps:
most thresholds read *"current or preceding calendar year"*, so crossing in 2026
keeps you registered through 2027; and discovering a crossing months late is a
**Voluntary Disclosure Agreement** conversation, not a self-help fix — you
generally cannot collect retroactively, so it comes out of margin.

**Re-examine the ebook channel if volume trips transaction-count thresholds.**
Selling ebooks through a facilitator while keeping SaaS direct may beat
registering in a dozen states.

### Calendar

- **2027-01-01 — CALIFORNIA SB 122** (chaptered 2026-06-29) adds
  *"prewritten computer software transferred on tangible storage media,
  transferred electronically, **or accessed remotely**"* to the digital-product
  definition. **Every guide dated before mid-2026 saying "California doesn't tax
  SaaS" is about to be wrong.** Threshold $500,000, so a scale trigger — but
  implementing regulations do not exist yet.
- **Washington ESSB 5814** made IT services retail sales as of **2025-10-01** —
  may reach custom development, which Ohio does not tax.

---

## 6. Nexus — do not maintain a table, and do not trust the states' own pages

Full detail in the researcher's nexus addendum. The operational finding:

**Five official government sources currently publish a superseded threshold
rule** — the SST board's Kentucky and Maine pages, Kentucky DOR (two pages still
citing 2018 HB 487), Maine Revenue Services **citing a repealed statute**, and
Louisiana's Remote Sellers Commission still stating a transaction prong repealed
three years ago. Kentucky removed its transaction prong **2026-08-01**, four
weeks ago. **Illinois DOR is actively de-registering sellers who registered under
the old rule.**

Every one of those errs toward **over-registration** — safe for liability,
expensive in filing obligations that are hard to unwind.

> **Do not reproduce a threshold list, and do not trust a state's own summary
> page either. Go to the statute, or delegate to a tax engine contractually on
> the hook for being current.** At zero revenue this costs nothing to adopt.

**14 states have independently verified removals of the transaction-count prong**
with statutory authority (NC S.L. 2024-28, WY Enrolled Act 38, UT S.B. 47 (2025),
WI 2021 Act 1, IL P.A. 104-0006, IA H.F. 779, LA Act 15, KY 2026 Acts ch. 161,
among others).

---

## 7. UNVERIFIED — generous on purpose

**Ohio:** specific combined county rates (ODT rate tables 403/404); ODT
Information Release ST 2003-06 (URL 404s, substance is in the statute);
**Ohio's SST Taxability Matrix was never read** — the live matrix is
JS-rendered, and it is the one document that would cleanly settle the
SaaS-vs-prewritten characterization; whether ODT would accept the EIS
characterization for *our specific product* (the "true object" test is
expressly fact-specific and *Cincinnati Federal* was **remanded** rather than
decided); filing-frequency assignment rules; and whether any of our actual
customers holds 501(c)(3) status.

**Multi-state:** **no authoritative count of SaaS-taxing or digital-goods-taxing
states exists from any primary source.** Vendor tallies say ~24–26 for SaaS and
30–45 for digital goods. **Do not quote a digital-goods count.** New York's ebook
exemption rests on **2011** guidance that says the Department "is currently
reviewing" the issue. Massachusetts ebooks, South Carolina ebooks, and
California's *current* exemption were not confirmed at source. Colorado
home-rule cities, Louisiana parishes and Chicago's Lease Transaction Tax are
real exposure entirely outside this analysis.

**A methodology warning worth carrying platform-wide:** during this research an
automated read of Nevada's NAC 372.880 returned **the opposite** of the correct
answer, and a first read of NY TSB-M-11(5)S claimed ebooks were taxable when the
source says the reverse. **Both were caught only by re-reading the same source.**
Treat any single automated read of a tax page as unverified until confirmed
twice.

---

## Must go to a CPA or state-tax professional regardless

**Three, none optional.**

1. **The characterization call** — is our hosted "licence" an electronic
   information service, a prewritten software licence, or a specified digital
   product? That single determination decides whether individual consumers pay
   tax, and it is fact-specific enough that the Ohio Supreme Court **remanded
   rather than decide it**.
2. **The exempt status of our actual lodge and post customers** — Ohio's
   exemption is 501(c)(3)-and-charitable-purposes only, and the veterans
   provision reaches state headquarters alone.
3. **Any nexus threshold already crossed without registering** — a Voluntary
   Disclosure Agreement conversation, not a self-help fix.
