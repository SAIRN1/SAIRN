# Worldwide competitive-gap audit — SAIRNbuild, SAIRNvet, SAIRNbiz, SAIRNgrounds/SAIRNscape, SAIRNcash

**Status: research supplied by Michael 2026-09-03 from real findings. Every
"current state" verdict below was re-derived against the code at HEAD by Cody
before being written down. Four of the supplied items turned out to be already
built and are recorded as corrections in §9 rather than shipped as gaps.**

---

## 0. What this document closes

This is the fifth real audit of its kind, and it exists to stop a recurring
false dispatch.

Three times now a session has been sent to "check the worldwide
competitive-gap audit" for these five apps and found **no such document**. The
correction is already on record twice — `f48c359` (2026-08-24) and §0.1 of
`2026-08-26-competitive-gap-audit-roofing-dental-senior.md`, which states it was
*"the second audit of its kind, not the eleventh."* On 2026-09-03 it happened a
third time and cost dispatch time again.

**The research was real; it had simply never been committed as a repo
document.** That is now fixed. The four prior audits are:

| Document | Apps |
|---|---|
| `2026-08-21-plumbing-electrical-hvac-worldwide-research.md` | trade research (mechanical / plumbing / electrical) |
| `2026-08-26-competitive-gap-audit-roofing-dental-senior.md` | SAIRNroofing, SAIRNdental, SAIRNsenior |
| `2026-08-27-sairnmechanical-shared-platform-competitive-research.md` | SAIRNmechanical |
| `2026-09-02-stonedesk-worldwide-competitive-gap-audit.md` | StoneDesk |

**Status columns in all of them are superseded by
`docs/2026-09-02-competitive-gap-status-rederived.md`**, per that file's own
rule: *the audits are for why an item matters and what the market does; the
status file is for whether it is still open.* This document's status column is
current as of 2026-09-03 and will go stale the same way. Treat the **verdicts**
as dated and re-derive before building.

## 1. Method, and the coverage limits that shape this pass

**What was verified here.** Every "SAIRNx state" cell. Marker terms were counted
against the app file and, where the app has one, its `api/_lib/*` and `sql/*`
surface — and **every non-zero result was read by hand**, because a hit is a
triage signal and not proof. That caution paid four times; see §9.

**What was NOT verified here, and this is the material limit.** The market
evidence — competitor names, segment sizes, pricing pressure, the willingness-
to-pay figures in §7 — is **supplied research, reproduced as given**. Unlike the
2026-08-26 audit, this pass did **not** re-check those against primary sources,
and it carries **no citation URLs**. Do not quote any market claim in this
document externally without verifying it first. The code column is evidence; the
evidence column is testimony.

**Two structural absences relative to the 2026-08-26 convention**, stated rather
than quietly skipped:

- **No non-English findings section.** The 08-26 audit's clearest cross-market
  pattern was that every non-English market examined has a government-mandated,
  software-relevant category with no US equivalent. No non-English research was
  supplied for these five apps, so there is no such section here. **That is a
  gap in this audit, not evidence of an absence in those markets.**
- **No patent screen** (§2).

## 2. Patent-safety posture

**No patent or IP screen was run for any of the five apps in this document.**

The 08-26 audit carried one, and the 08-28 narrow-verification pass resolved two
patents that mattered (`US 9,471,749` → WellSky; `US 11,915,806` → Therap
Services, expiring 2026-11-27). Neither of those touches these five apps, and
neither is a clearance for them.

**Three items below are the shape that warrants a screen before building**, and
are flagged in place: SAIRNvet A1 (AI radiology triage), SAIRNvet A2 (ambient
clinical scribe), and SAIRNcash A4 (agentic financial action). All three are
crowded, well-funded categories where method patents are plausible.

---

## 3. SAIRNbuild

**Built and verified at HEAD:** Draw Requests panel (progress billing — draw #,
period end, % complete, requested, retainage held, received); a real **WIP
Schedule** report (cost to date ÷ est. total cost → % complete → earned revenue →
over/under billing); Committed Cost KPIs; a change-order log (34 in-file
references); a Settings panel carrying default retainage and markup; `bld_draws`
with `retainage_pct` and `retainage_held`. **All client-side, in-file, over
`localStorage`.**

### 3.1 The finding that reframes SAIRNbuild's Tier B list

**Two of the six supplied Tier B items are substantially built, and a shared
server engine for a third already exists that SAIRNbuild does not call.**

`api/_lib/wip-accounting.js` is a **shared, app-agnostic** progress-billing
engine — draw requests, retainage, over/under billing, pure functions, no app
names — written for SAIRNroofing B3. Its own header says so explicitly:

> *"SAIRNbuild HAS retainage and WIP today — `jobWIP()`
> (sairnbuild.html:6263), a Draw Requests panel, `bld_draws` with
> retainage_pct/retainage_held, and a default retainage setting. It is
> CLIENT-SIDE, in-file, over localStorage, and it is untouched by this file. So
> this is the SECOND implementation on the platform, deliberately, because
> SAIRNbuild's is not a server engine and cannot be called."*

**So the real Tier B work for SAIRNbuild is repointing, not building.** That is
a different task, a different size, and a different risk profile from what the
supplied list implies — and it is exactly the check Michael asked for before
duplicating SAIRNroofing B3.

*(One line reference in that quoted header has drifted: `jobWIP()` is at `sairnbuild.html:6623` today, not 6263. The quote is reproduced as written and the current line is given here rather than silently editing someone else's header — same treatment the 08-26 audit gave its own drifted hit counts.)*

One substantive difference the repoint must resolve: the shared engine derives
`held = amount × pct` **on read and never stores it twice**, while `bld_draws`
stores both `retainage_pct` and `retainage_held`, which can disagree the moment
anyone edits one.

### 3.2 Gaps — Tier A (small business)

| # | Gap category | Evidence it matters *(supplied research, not re-verified)* | SAIRNbuild state (verified at HEAD) |
|---|---|---|---|
| A1 | **AI scope-gap detection with page/section-traced citations** — read a spec or drawing set and surface what is missing or contradictory, each finding traced to where it came from | The grounded-citation pattern is already proven in-house by SAIRNlaw's citator, which is the reason to believe this is buildable honestly rather than as plausible-sounding output | **Absent.** Zero occurrences of "scope gap". **Citation plumbing already exists but for a different purpose** — `sairnbuild.html:7205` collects `b.citations` from Claude web-search results. Nothing reads a document and traces a finding to a page |
| A2 | **Full 3D BIM viewing via open IFC** — `IfcOpenShell` / `web-ifc`, deliberately avoiding proprietary Autodesk formats | Format choice is the strategic half: an open-IFC path avoids a licensing dependency on the incumbent whose product you are competing with | **Absent.** Zero occurrences of BIM, IFC, IfcOpenShell, web-ifc or `.rvt`. **Note the app already runs WebXR/WebGL** (`sairnbuild.html:7768`), so the rendering surface is not starting from zero |
| A3 | **Bilingual English/Spanish field interface** | A field-crew requirement in US construction, not a localisation nicety | **Absent.** Zero occurrences of Spanish, bilingual, i18n or a language toggle. *(Three `espa` substring hits are `requestReferenceSpace` and "namespace" — a word-boundary search returns 0. Recorded because a naive count here would read as partial support.)* |
| A4 | **Offline-first field app** | Job sites lose signal; a field tool that needs connectivity is a field tool that gets abandoned | **Absent.** Zero occurrences of offline, service worker, IndexedDB or `navigator.onLine`. **The app is `localStorage`-backed today, so it is accidentally offline-tolerant and deliberately offline-*unaware*** — it cannot tell a user what did or did not sync |

### 3.3 Gaps — Tier B (mid-market, ~$5M+ revenue)

| # | Gap category | Evidence *(supplied)* | SAIRNbuild state (verified at HEAD) |
|---|---|---|---|
| B1 | **AIA progress billing — G702/G703 forms** | The standard artefact a GC and an owner both expect | **PARTIAL, and the gap is narrower than stated.** Progress billing itself is **built** — the Draw Requests panel is titled *"Progress billing — requested vs received, retainage held"*. What is absent is the **AIA form output**: zero occurrences of G702, G703 or AIA. **Check `api/_lib/wip-accounting.js` before building; see §3.1** |
| B2 | **Retainage holdback / release with a full audit trail** | Retainage is money owed that is deliberately withheld; release is a contractual event that gets disputed | **HOLDBACK BUILT, RELEASE ABSENT.** "Retainage Held" KPI, per-draw column, and a default retainage setting that pre-fills new draws — but **zero occurrences of any retainage release path, and no audit trail on it.** Money can go in and never come out |
| B3 | **WIP / cost-to-complete forecasting** | Standard construction accounting; the basis of every percentage-of-completion revenue figure | **WIP BUILT, FORECASTING ABSENT.** A real WIP schedule exists with cost-to-cost % complete, earned revenue and over/under billing (`sairnbuild.html:1207-1208`, `6624-6625`). **Zero occurrences of forecast, cost-to-complete or estimate-at-completion** — it reports the past accurately and projects nothing |
| B4 | **Multi-entity / multi-currency job cost accounting** | The mid-market contractor is increasingly a multi-entity rollup rather than one company with branches — the same structural finding the 08-26 audit reached for roofing (§3.1 there) | **Absent.** Zero occurrences of multi-entity, `entity_id`, currency, FX or exchange rate. **SAIRNbuild has no location or entity axis at all** — unlike StoneDesk and SAIRNroofing, which at least have `location_id` |
| B5 | **Certified / prevailing-wage payroll** | Davis-Bacon and state prevailing-wage law force this on any public-works job | **Absent.** Zero occurrences of certified payroll, prevailing wage, Davis-Bacon or WH-347. **Precedent worth reading first: SAIRNroofing REFUSED this deliberately** (`sairnroofing.html:613`) rather than shipping it, on the grounds that inventing a wage determination rate is worse than not offering the feature. Any SAIRNbuild build must clear the same bar |
| B6 | **Real-time two-way GL sync of committed costs and change orders** | Committed cost that lives only in the job tool is a number the accountant cannot reconcile | **CONCEPTS BUILT, SYNC ABSENT.** Committed Cost KPIs and a change-order log both exist in-app. **No general-ledger integration of any kind** — all seven `GL` matches are false positives (an insurance policy number, and WebGL). Note SAIRNbiz now has a real double-entry ledger at `/api/ledger`; that is the obvious counterparty and it is not connected |

---

## 4. SAIRNvet

**Built and verified at HEAD:** a SOAP Notes panel with AI generation; per-field
**voice dictation** (`sairnvet.html:7796`, with a comment at `:7773` explaining
the hands-occupied rationale); a Multi-Location panel; treatment and invoice
models; appointment handling; a "Needs radiologist read" pending count.

### 4.1 Gaps — Tier A (single practice)

| # | Gap category | Evidence *(supplied)* | SAIRNvet state (verified at HEAD) |
|---|---|---|---|
| A1 | **AI radiology triage** — tiered screening with specialist backup | The tiering is the product: AI screens, a specialist backstops, and the practice never has to choose between speed and a real read | **Absent as a capability; the workflow hook exists.** One `radiolog` occurrence total — a *"Needs radiologist read"* KPI at `sairnvet.html:2518`. Zero occurrences of DICOM or x-ray. **So the app already counts what is waiting for a read and does nothing about it**, which is the natural insertion point. ⚠ **Patent screen recommended before building (§2)** |
| A2 | **Ambient AI scribe** — auto-fill SOAP from the live consultation | Removes the documentation burden that drives veterinary burnout | **PARTIAL, and the built half is the harder half to notice.** SOAP notes are built (33 in-file references, a dedicated panel, AI generation) and **per-field voice dictation already ships**. What is absent is **ambient capture**: zero occurrences of "scribe"; the `transcri`/`dictat` hits are all push-to-dictate into a named field. The gap is *listening to a conversation*, not *producing a SOAP note*. ⚠ **Patent screen recommended (§2)** |
| A3 | **Treatment automatically triggers an invoice** | Charge capture is where independent practices lose revenue silently | **Absent.** Treatment (29) and invoice (15) both modelled; **zero occurrences of auto-invoice or charge capture.** The two models exist and nothing joins them |
| A4 | **True instant booking** vs. competitors' "requests" | The competitive claim is specifically that rivals sell a request queue and call it booking | **Needs a product decision before it is a gap.** Appointments are modelled (18 references) but there are **zero occurrences of "booking"** anywhere in the file, so there is no request-vs-confirm distinction to improve — the concept is absent rather than implemented badly. Compare SAIRNdental, which has a real public booking flow in `sairndental-book.html` and `api/sairndental/public-book.js` and `public-availability.js`; **that is the reusable precedent** |

### 4.2 Gaps — Tier B (multi-site groups)

> **Read `sairnvet.html:1386` before writing any Tier B row here.** The
> Multi-Location panel says of itself: *"Revenue and Patients Active are logged
> manually per location — not auto-linked to Invoicing or a shared [record]."*
> **The app already discloses that its multi-site view is a hand-typed
> scorecard.** That is more honest than most of what this audit surveys, and it
> means every row below is about replacing manual entry with a data model, not
> about building a panel.

| # | Gap category | Evidence *(supplied)* | SAIRNvet state (verified at HEAD) |
|---|---|---|---|
| B1 | **Unified patient/client chart across every location a pet has visited** | The whole clinical argument for a group: the animal's history follows the animal | **Absent.** Zero occurrences of `site_id` or "unified chart". Locations are a **manually-entered list with revenue and headcount**, carrying no relationship to a patient record |
| B2 | **Centrally-set vs. locally-set permission model** | A group needs some settings owned by HQ and others by the practice; one flat role list cannot express that | **Absent.** 51 `role` references but **zero occurrences of "permission" or "central"** — roles exist, the central/local axis does not |
| B3 | **Consolidated multi-site inventory purchasing** | Purchasing leverage is a primary reason practices join a group at all | **Absent.** One `inventory` occurrence in the entire file, 11 `purchas*`, **zero reorder logic**. Inventory is effectively unmodelled, so this is a build rather than an extension |
| B4 | **Rolled-up multi-site practice-intelligence dashboard** | HQ cannot manage what it can only read one practice at a time | **Absent as derived data, present as manual entry.** Zero occurrences of roll-up, consolidate, or "across all locations". The KPIs on the Multi-Location panel are **typed in by a human**, which is worse than absent for a decision-support surface — it looks derived |

---

## 5. SAIRNbiz

**Built and verified at HEAD:** pre-payroll validation (`checkPayrollAnomalies`,
with a design doc at `docs/superpowers/specs/2026-08-10-sairnbiz-pre-payroll-validation-design.md`);
per-employee pay frequency and prorated benefits (built 2026-09-03); a real
double-entry general ledger at `/api/ledger`; payroll-run history; benefits
enrolment; budget actuals derived from recorded expenses.

**Tier B was not researched for SAIRNbiz** and no Tier B table is offered. See §7
for the same disclosure applied to SAIRNcash.

### 5.1 Gaps — Tier A (small business)

| # | Gap category | Evidence *(supplied)* | SAIRNbiz state (verified at HEAD) |
|---|---|---|---|
| A1 | **Mid-year auto-update of compliance thresholds** rather than a manual code push | Wage bases, contribution limits and withholding thresholds move mid-year; a product that needs a deploy to stay legal is a product that is quietly wrong between deploys | **Absent, and the app is currently worse than "manual" — the constants are scattered.** One `threshold` occurrence; zero occurrences of wage base, contribution limit, IRS or auto-update. Rates live inline as literals (`0.0765`, `0.22`, `0.0399`, the `$520` benefit default). **The 2026-08-28 narrow-verification pass reached the same conclusion for SAIRNsenior from the regulatory side** — that payroll and compliance logic *"must be DATED AND CONFIGURABLE, never a constant"*, because both the FLSA companionship exemption and the CMS 80/20 rule have live rescission proceedings. That finding applies here verbatim |
| A2 | **"Phantom-wage" detection** — owed-but-unpaid overtime carrying real tax and insurance liability | The liability is real and accrues silently; nobody goes looking for it | **Absent.** Zero occurrences of phantom, unpaid overtime or off-the-clock. The 14 `OT` hits are ordinary overtime fields. **Blocked on a real dependency, and it should be recorded as such: `rTS()` drives timesheet hours from a HARDCODED array in source, not from any store** (found in the 2026-09-02 click-through). Detection built on fabricated hours would produce a fabricated liability |
| A3 | **Pre-submission AI payroll error detection** | Catching an error before submission is worth more than any report after it | **BUILT, and the gap is depth rather than existence.** `checkPayrollAnomalies()` runs before every payroll and **performs exactly two checks** — missing/zero pay rate, and started-within-14-days — which its own tool description states in terms and warns must never be read as "payroll is clean". **The honest gap is check coverage, not the mechanism**, and the mechanism already refuses to overclaim |
| A4 | **Tiered self-service / assisted / managed model** | A packaging and go-to-market decision, not a feature | **Not a code gap.** Zero occurrences of self-service or assisted. **Recorded as a positioning finding**, the same treatment the 08-26 audit gave SAIRNroofing A4 |

---

## 6. SAIRNgrounds / SAIRNscape

**Built and verified at HEAD:** SAIRNgrounds is golf-and-grounds by identity (42
in-file `golf` references, including the product title); properties are modelled
with `property_id` (89 references) and carry manual acreage; a QC photo-review
workflow with a completion gate; vendor and inventory concepts (37 `inventory`
references in grounds, **zero in scape**).

### 6.1 The two apps already disagree about the wedge

**SAIRNscape ships the flat-price positioning; SAIRNgrounds does not have a
pricing surface at all.**

`sairnscape.html:175` reads *"Flat monthly fee. Unlimited users. Cancel anytime.
Priced for real businesses."* with a matching `Unlimited users` price feature at
`:198`. SAIRNgrounds returns **zero** occurrences of flat fee, per-seat or
unlimited users.

So A1 below is **already built in one of the two apps** and the work is to bring
the other into line — not to discover the wedge.

### 6.2 Gaps — Tier A (small business)

| # | Gap category | Evidence *(supplied)* | State (verified at HEAD) |
|---|---|---|---|
| A1 | **Flat-price / no-per-seat-fee positioning** | A validated 2026 wedge — QuoteIQ markets directly against Jobber, Housecall Pro and ServiceTitan on exactly this | **BUILT IN SAIRNscape, ABSENT IN SAIRNgrounds.** See §6.1. Positioning, not a feature |
| A2 | **Satellite / aerial property measurement for instant quoting** | Removes the site visit from the quote, which is the whole sales cycle for lawn care | **Absent.** Zero occurrences of satellite, aerial or Nearmap in either app. **Acreage is a manually-typed property field** in SAIRNgrounds (20 references) — the destination field exists and nothing populates it |
| A3 | **Automated post-job review collection, and off-season win-back campaigns** | Reviews are the primary acquisition channel in residential services; win-back addresses the seasonal revenue trough | **Absent, both halves, both apps.** Zero occurrences of Google review, NPS or testimonial; zero occurrences of win-back, off-season, re-engage or dormant. *(All `review` hits in both apps are the internal QC photo-review queue — a different thing entirely, and an easy false positive.)* **The completion gate at `sairngrounds.html:591` is the natural trigger point**: a job cannot be marked Complete without a finished-product photo, which is precisely the moment to ask for a review |
| A4 | **Golf AI concierge / cancellation recovery** — turn a full tee sheet into an intelligent waitlist | A cancelled tee time is unrecoverable inventory | **Absent, and further from the model than the golf branding suggests.** Zero occurrences of tee sheet, tee time, cancellation, waitlist or concierge — in an app whose own title is *"Golf Course & Grounds Operations"*. **There is no tee-sheet model to build a waitlist on top of** |

### 6.3 Gaps — Tier B (mid-market)

| # | Gap category | Evidence *(supplied)* | State (verified at HEAD) |
|---|---|---|---|
| B1 | **Multi-property golf operators** — Troon operates 575+ courses | Same multi-brand-one-backend pattern already flagged platform-wide; see §8 | **Absent.** Zero occurrences of multi-property, multi-course or portfolio. **`property_id` is the CUSTOMER's property, not the operator's own site** — a different axis, and mistaking one for the other is how this gap gets closed on paper without being closed |
| B2 | **Multi-division operation** — maintenance + construction + snow under one roof, the segment Aspire (ServiceTitan-owned) owns as the enterprise ceiling, quoted at "25–200+ employees" | The named ceiling on this vertical | **Absent.** Zero occurrences of division; one `snow` reference in scape and one `construction` in each — incidental, not modelled |
| B3 | **Purchasing / inventory / vendor management at scale** | Part of the same Aspire ceiling | **PARTIAL IN GROUNDS, ABSENT IN SCAPE.** SAIRNgrounds has inventory (37) and vendor (22) concepts; SAIRNscape has vendor (10) and **zero inventory**. **Neither has purchase orders** — zero occurrences of "purchase order" in either |
| B4 | **Unlimited users at the mid-market tier** | The per-seat model is what the wedge attacks; it has to survive contact with a 200-employee operator | **Claimed in SAIRNscape's pricing copy, unverified against any seat-enforcement code.** Recorded because a pricing promise with no mechanism behind it is a commitment, not a feature |

---

## 7. SAIRNcash

**Built and verified at HEAD:** income and deduction logging with auto-suggested
categories (57 `deduction` references); a **Predictive Insights** panel
(`renderPredictiveInsights`, 2026-08-18); quarterly tax set-aside estimation;
Stripe subscription billing; an AI assistant with one tool.

### 7.1 Two scope facts that reshape three of the four Tier A items

**First: SAIRNcash has no invoice, client or receivables model at all.** Verified
— zero occurrences of "overdue" or "accounts receivable"; the four `invoice`
matches are a placeholder string (`"Description (e.g. client invoice)"`) and
comments about SAIRNcash's *own* Stripe subscription. It is an
income-and-deductions tool for the self-employed.

So A1 below is **a scope expansion, not a gap in an existing feature** — building
it means first building invoicing. That is a product decision and should not be
buried in a gap row.

**Second: the existing Predictive Insights panel deliberately refuses to
forecast.** Its own header (`sairncash.html:1154`) says it *"Deliberately does
NOT project a full-year total or claim any forward-looking certainty — both
signals describe the past only."* Both signals are backward-looking:
last-completed-month income versus the user's own prior-month average, and top
deduction categories.

**A2 therefore contradicts a live design decision rather than filling a hole.**
That is a decision to revisit explicitly, not a gap to close quietly — and the
refusal was written for a good reason.

### 7.2 Gaps — Tier A (small business)

| # | Gap category | Evidence *(supplied)* | SAIRNcash state (verified at HEAD) |
|---|---|---|---|
| A1 | **AI-timed and AI-toned overdue-invoice follow-up** | Timing and tone are the whole difficulty of chasing money from a client you want to keep | **Depends on a model that does not exist.** See §7.1. Zero occurrences of overdue or dunning. **Not costable as a gap until the invoicing decision is made** |
| A2 | **AI cash-flow prediction from a specific client's own payment history** | Forecast from this user's real history rather than a generic model | **Contradicts a live design decision.** See §7.1. Zero occurrences of cash-flow, forecast or payment history. The panel that would host it exists and currently declines to predict |
| A3 | **AI bank-scanning that proactively surfaces overlooked deductions** | The recurring finding is that self-employed filers miss deductions they already qualify for | **Absent, and the missing half is the bank connection.** Deduction categorisation is well built (57 references, auto-suggest on blur). **Zero occurrences of bank, Plaid or transaction** — there is no transaction feed to scan. The categoriser is the second half of this feature and it already exists |
| A4 | **Agentic autonomous action** — the real 2026 wedge, since passive categorisation is fully commoditised | If categorisation is table stakes, the differentiator is the product doing something | **Absent, and the app currently promises the opposite in writing.** `sairncash.html:378` tells the user *"it will never file anything on your behalf"*, and the system prompt forbids implying otherwise. The one `agentic` occurrence is a comment label on the AI tool-calling block. **Any move here is a product-positioning reversal that must be made deliberately, and the refusal language is correct for what the app does today.** ⚠ **Patent screen recommended (§2)** |

**Go-to-market note, supplied and reproduced as given, NOT verified:** employers
and banks are reported willing to pay **$5–20 per user per month** to offer this
as a 1099/gig-worker benefit. If that figure is load-bearing for any decision,
verify it against a primary source first — it is the kind of number that gets
quoted into a deck and never re-checked.

### 7.3 Tier B — not researched

**No mid-market research was supplied for SAIRNcash and none is invented here.**
Recorded as a known hole in this audit rather than left as an apparent absence
of gaps.

---

## 8. Cross-app: multi-brand / multi-site under one centralised backend

**The supplied finding is that this need is now confirmed independently across
six apps — StoneDesk, SAIRNlegacy, SAIRNgrounds, SAIRNsenior, SAIRNcare and
SAIRNbuild — making the case for the shared architecture already flagged as a
Tier 3 platform initiative rather than continued one-off builds.**

**Verified against the code, and the picture is stronger than "six instances of
the same thing" — because there are barely two of the same thing.**

| App | What exists today | Axis |
|---|---|---|
| StoneDesk | `location_id` (12 refs) + a locations panel | operator's own branches |
| SAIRNroofing | `location_id` (21 refs) | operator's own branches — **attribution only, deliberately not an access-control axis** (`api/_lib/roofing-locations.js`) |
| SAIRNlegacy | `facility_id` + a Facilities panel and `facilityLabel()` | operator's own chapels/rooms, booked against cases |
| SAIRNvet | a Multi-Location **panel** | **manually typed**, no relationship to any patient record (§4.2) |
| SAIRNgrounds | `property_id` (89 refs) | **the CUSTOMER's property, not the operator's site — a different axis entirely** |
| SAIRNsenior | nothing | — |
| SAIRNcare | `facility_id` — **and it is the only one that is SERVER-SIDE**: `sairncare.html:3511` records that the server table is keyed by `(license_hash, facility_id)` | operator's own facilities |
| SAIRNbuild | nothing | — |
| SAIRNdental | nothing | — |

**Four different names for the operator's own sites, one of them a manual
scorecard, one of them not that axis at all, and three apps with no axis
despite a confirmed market need.** Every implementation was built once, locally,
by whoever needed it that night.

**That is a stronger argument for the shared layer than the original framing**,
and it also warns what the shared layer must settle before any app adopts it:

1. **Is a site an attribution tag or an access-control boundary?** SAIRNroofing
   answered "attribution, deliberately" and wrote it down. Nobody else answered.
2. **Branch vs. entity.** The 08-26 audit's roofing finding (§3.1 there) and
   SAIRNbuild B4 above are the same finding: the mid-market buyer is
   increasingly a multi-entity rollup, and a branch axis will not model it.
3. **The customer's sites and the operator's sites are different things** and
   SAIRNgrounds already demonstrates how easily they get conflated.

---

## 9. Supplied findings that were already built — corrections

**Four items in the supplied research are wholly or substantially built. Every
one was caught by re-deriving against the code before writing, which is the same
check that produced the five stale-index corrections earlier the same day.**

| Supplied as a gap | Reality at HEAD |
|---|---|
| SAIRNbuild — *retainage holdback/release with audit trail* | **Holdback built** (KPI, per-draw column, default setting). Only **release** and the audit trail are missing |
| SAIRNbuild — *WIP / cost-to-complete forecasting* | **A full WIP schedule is built**, cost-to-cost, with earned revenue and over/under billing. Only **forecasting** is missing |
| SAIRNbuild — *AIA progress billing (G702/G703)* | **Progress billing built** as a Draw Requests panel. Only the **AIA forms** are missing — and a shared server engine for the accounting already exists (§3.1) |
| SAIRNbiz — *pre-submission AI payroll error detection* | **Built** (`checkPayrollAnomalies`), with a design doc. The gap is **check depth**, and the tool already discloses that it performs exactly two checks |
| SAIRNvet — *ambient AI scribe* | **SOAP notes and per-field voice dictation both built.** Only **ambient conversation capture** is missing |
| SAIRNgrounds/SAIRNscape — *flat-price positioning* | **Already shipped in SAIRNscape's pricing copy.** Missing only in SAIRNgrounds |

**None of these makes the supplied research wrong.** Each was a real gap when
observed; the platform moved. It is the same lesson
`docs/2026-09-02-competitive-gap-status-rederived.md` was created to carry, and
the reason this document's own status column will need the same treatment.

## 10. What this document deliberately does NOT do

- **It does not verify any market claim.** Competitor names, segment sizes,
  pricing pressure and the §7 willingness-to-pay figure are supplied research
  reproduced as given, with **no citation URLs**. Verify before quoting.
- **It carries no patent screen** (§2) and is not a clearance for anything.
- **It carries no non-English findings**, unlike the 08-26 audit — none were
  supplied. That is a hole in this pass, not an absence in those markets.
- **It does not set a build order.** Frequency of a gap across competitors
  measures where the market is weak, not what a customer needs first — the same
  caveat the SAIRNmechanical spec carries on its capability list.
- **It does not claim its status column will stay true.** It was accurate on
  2026-09-03 against the code at HEAD. Re-derive before building; four rows in
  the input to this very document had already gone stale (§9).
