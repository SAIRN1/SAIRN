# SAIRNroofing — v1 Scope

**Status:** scope only. Nothing built. Written 2026-08-24 after a competitive-gap
and patent audit; supersedes nothing, because SAIRNroofing had no prior artifact
of any kind (confirmed: zero files in the repo mentioned it).

**Decided by Michael before this doc:** mid-market tier (20–100 employees),
US-only, single-inference/quantities-schedule measurement, solar shingles
prioritised early, storm/insurance restoration **in v1**.

---

## 0. Two premise corrections carried into this doc

Recorded here because both were wrong in the sources that prompted the work,
and a scope doc built on them would have inherited the errors.

**0.1 — No prior competitive-gap audit exists for any SAIRN app.** The request
described this as "the same audit every other app already got." Searched: 54
spec docs, 48 of them feature-design; zero filenames matching
competit/market/gap-audit/landscape; zero hits across all docs for ServiceTitan,
JobNimbus, AccuLynx, Roofr, EagleView, Jobber or Housecall. The only substantive
competitive paragraph anywhere is in `2026-08-10-sairncash-pivot-design.md`
(names Keeper, QuickBooks Self-Employed, FlyFin). `sairn-build-lifecycle` Phase 4
asks for "real competitive pricing research — not guessed, actually searched,"
and no artifact shows it was ever run. **This document is the first of its kind
on the platform, not a copy of an established template.**

**0.2 — The platform's own patent note has the parties backwards.**
`sairn-forward-scan` states US 9,501,700 is "litigated aggressively by its owner
(a $125M verdict against a competitor in this exact category)." The assignee of
9,501,700 is **Xactware Solutions (Verisk)** — the party that **lost** that
verdict. EagleView won $125M against Xactware/Verisk (D.N.J., Sept 2019),
trebled to $375M. There are **two** hostile families in roofing, not one. The
note also says "five continuations through 11,727,163"; the family has since
added 12,265,758 (2023) and a pending 2025 continuation, so it is still growing.

Neither correction changes the *guardrail* that note gives — it described the
claim shape accurately — only who holds it and how many there are.

---

## 1. Patent position

### 1.1 Family A — Xactware/Verisk, US 9,501,700, active to 2032

Claim 1 is an **AND of eight elements**. All must be present to infringe:

1. receive at least one **aerial image**
2. process with a **filter computing a per-point likelihood the point is a roof line**
3. **scan at a first angle** → intensity data
4. **rotate** to a second angle
5. **scan at the second angle** → intensity data
6. process both to **automatically identify lines**
7. construct a **2D model** from those lines
8. convert 2D→3D by superimposing on an **oblique image** and letting **the user
   click and drag** perimeter/interior points onto it

Continuations: 10,503,842 · 11,210,433 · 11,727,163 · 12,265,758 · pending 2025.

This is a specific classical-CV pipeline, not "photo → estimate" in general.

### 1.2 Family B — EagleView/Pictometry

The aggressive enforcer, but weakening. Won $125M→$375M vs Xactware/Verisk. Sued
Roofr (D. Del. 21-1852); PTAB then held **9,183,538** and **10,648,800** obvious
and invalid (July 2024), affirmed on appeal.

### 1.3 The design-around v1 is built to

**Option 1 + 2 combined: single inference producing a quantities schedule,
never a manipulable geometric model.**

- One LLM call: photo(s) in → structured quantities out. No per-point roof-line
  filter, no scan/rotate/scan, no automatic line identification. Defeats
  elements 2–6 at once. This is precisely why StoneDesk's photo feature was
  cleared — a single inference, not a CV pipeline.
- Output is a **quantities schedule** (squares, ridge/hip/valley LF, eave/rake,
  penetrations, pitch class, stories, waste factor), reviewed and edited by the
  estimator before it becomes an estimate. No wireframe, no oblique
  superimposition, no click-drag fitting. Defeats elements 7–8.
- Element 8 is a *user-interaction* limitation and is the single easiest element
  to stay clear of. v1 stays clear of it absolutely.

Distance from **six of eight elements on independent grounds**.

**HARD BOUNDARY, to be written into the source file itself in
`sairn-forward-scan` style at build time:** any future move toward multi-angle
scan-rotate-scan, per-pixel roofline/edge filters, or manipulable 2D→3D geometry
fitted to oblique imagery **voids this analysis** and requires a fresh legal
check. Not a quiet extension of this one. Same discipline as StoneDesk's
texture-visualization boundary (`2026-08-13`), which is the real precedent here.

### 1.4 What this is not

**This identifies a defensible design path. It does not clear it legally.**
A real patent attorney is required before launch — same standing caveat as
StoneDesk's and the Session 64 note. Unchanged by any amount of further research.

**Trademark: inconclusive, not cleared.** A public-web search for a "SAIRN" mark
returned nothing relevant, which is *not* a clearance — it was not TESS, EUIPO or
WIPO, and a real screen needs Class 42 (SaaS) **and** Class 9 (downloadable
software). Attorney work.

---

## 2. Competitive position

**Tier 1 (small business, crowded — not the target):** JobNimbus (~$350/mo team),
AccuLynx ($250–500+/mo), Roofr (free tier), Leap, SubcontractorHub, iRoofing.

**Tier 2 (enterprise):** ServiceTitan ($1,225–2,000+/mo for 5 crews).

**The gap v1 targets:** the market is barbelled — cheap-and-shallow or
enterprise-and-expensive. The 20–100-employee, often multi-location roofer is
squeezed between them.

**Borrowed technical idea, not a market:** the German *Aufmaß* pattern
(plancraft, desk4, smartDach, WIN DACH) — structured on-site measurement that
flows directly into the material list, so a foreman's field correction updates
the takeoff instead of living in a note. Absent from US tools. Germany is **not**
a target market; US-only stands.

**Stated, not inferred:** no verifiable French, Spanish/LATAM, Japanese or Nordic
roofing-specific products were found in this pass. That is **no coverage found**,
not evidence of absence.

---

## 3. Phase structure

### Phase 1 — Foundation
- `api/rf-auth.js`: bootstrap/login/setup/check_license/roster/**set_active**.
  The credential lifecycle ships **built in**, not retrofitted — this app must
  not become the fourth instance of that gap (StoneDesk, SAIRNcode, SAIRNcash
  trials were the first three).
- Roles: `owner` / `admin` / `estimator` / `foreman` / `crew`.
  **INVENTED, NOT RESEARCHED — flagged for Michael's trade contacts to confirm
  before Phase 1 is written.** Every app that went well had a real source
  document; SAIRNcare had none and needed a scope correction.
- `rf_` storage prefix — **collision-checked 2026-08-24, zero hits** against the
  19 prefixes in use (alf, bld, dnt, fab, law, leg, sa, sairn, sairncash, sb, sc,
  sd, sdn, sen, sh, sl, stondesk, stonedesk, sv).
- `'sairnroofing'` must be added to `KNOWN_APP_IDS` in `api/claude.js` or every
  AI call 400s — the exact gap that hit 9 of 13 apps before the 2026-07-26 fix,
  and hit SAIRNsenior again on 2026-08-20.
- Assignment-based privacy gate, three-tier, with SAIRNsenior's and SAIRNbuild's
  two known bugs designed in from the start rather than rediscovered.
- Dashboard + AI Assistant scoped to what the signed-in role can see.

### Phase 2 — Measurement → estimate
Built to §1.3 exactly. Includes the *Aufmaß*-style field-correction path.

### Phase 3 — Materials — **SHIPPED INSIDE PHASE 2, 2026-08-24**
Verified against the built file, not assumed: `RF_MATERIALS_LIST` in
`sairnroofing.html` carries all eleven materials below, including the three
solar shingles and the commercial-flat set, and `RF_MATERIALS` in
`api/sd-data.js` enforces the same list server-side. The Tesla capability gate
is real (`sql/sairnroofing_employee_auth_certifications_migration.sql` +
`api/rf-auth.js`'s `set_certifications`).

This heading is kept rather than renumbered so the phase numbers in earlier
commits still resolve. **The work referred to as "Phase 3" from 2026-08-24
onward is Phase 4 + Phase 5 below**, split 3a/3b/3c:
  3a — certifications & licensing (§4)
  3b — claim record + photo evidence (§5.3)
  3c — supplement reconciliation (§5.2, deterministic, no LLM opinion)

1. **Solar shingles** — the differentiator, and patent-clean because it is
   *material-specific estimating logic*, a different inventive space from
   measurement. Three products, genuinely different mechanics:
   **GAF Timberline Solar** (nailable, standard pneumatic gun),
   **Tesla Solar Roof** (glass tile; installable only by Tesla Energy crews or
   Tesla Certified Installers — a *capability gate*, not merely a price line),
   **CertainTeed SolarShingle** (clip-in). Energy-production estimate is
   entangled with the takeoff. No roofing-management product found treats solar
   shingles as a first-class material type.
2. **Standard set** — asphalt, metal, slate, copper, wood shake.
3. **Commercial-flat** — TPO, EPDM, modified bitumen. Not on the original list,
   but every real competitor covers it and mid-market shops do commercial work.

Per-material labor modelling for copper/slate craft is **flagged unverified** —
how deeply existing tools model it was not confirmed, so no gap is claimed.

### Phase 4 — Operations
Jobs & scheduling (crew assignment, multi-location) · Estimates → proposals →
invoicing · Reports with real CSV export inheriting the read gates ·
**Licensing & Compliance** and **Certifications**, see §4.

### Phase 5 — Storm & Insurance Restoration
Promoted to its own phase, see §5.

### Phase 6 — Deliberately excluded, recorded as closed decisions
Written into the source file the way SAIRNcash's Bridge exclusion is, so they
cannot quietly reappear:
- **Aerial imagery integration** (EagleView / Hover / GAF QuickMeasure).
  AccuLynx's breadth here is real parity and is exactly the patent-hostile
  surface. Revisit only with counsel.
- **SAIRN Bridge / cross-app.** Same finding as SAIRNcash: `?action=pull` has
  zero callers platform-wide; `bridge_data` is written and never read.

---

## 4. Licensing & certifications — two independent compliance axes

Researched, not assumed.

**State licensing genuinely varies.** Most states require a roofing licence;
**Texas and Wyoming have no state-level requirement**. California, Florida and
Illinois are heavily regulated with roofing-specific classifications. Common
requirements: 2–4 years' experience, trade and/or business exam, financial
qualification, general liability minimums, and in some states (California) a
bond. Renewal is annual or biennial; **Florida requires continuing education**.
A multi-state mid-market roofer therefore runs several different compliance
clocks — the same per-state-config pattern SAIRNsenior used for EVV aggregators
and SAIRNcare for ALF licensing. **State deadline values are facility-entered
with a named source, never hardcoded as if universal.**

**Manufacturer certifications are a separate axis and commercially
load-bearing** — they are what lets a contractor sell the warranty, which is how
mid-market bids are won. **GAF Master Elite** requires an active state licence,
≥$1M general liability plus workers' comp, and **7 years** in business.
**Owens Corning Platinum Preferred** is held by roughly **1%** of OC contractors
and gates on customer-satisfaction scores. **CertainTeed SELECT** is the third.
These are voluntary manufacturer programmes, not state mandates — the app must
not present them as regulatory.

---

## 5. Storm & Insurance Restoration (Phase 5)

Researched before design, per instruction. It is substantial enough to warrant
its own phase rather than folding into Operations.

### 5.1 The real lifecycle — 7 steps, 45–90 days

1. Homeowner reports the loss to the carrier
2. Carrier assigns a field adjuster
3. Contractor meets the adjuster **on the roof**
4. Adjuster writes the scope **in Xactimate**
5. Contractor signs a **contingency agreement**; files **supplements** for code
   upgrades and hidden damage (deck rot, ice-and-water shield, drip edge)
6. Install completes **at carrier-approved scope**
7. **ACV cheque** funds the work; **recoverable depreciation** releases after
   the final invoice

### 5.2 The finding that shapes the whole design

Xactimate is used by the vast majority of North American property adjusters. Its
line-item database carries unit costs **updated quarterly by ZIP code**. Because
both sides use the same software and the same price list:

> supplements and negotiations are **not about opinion**. They are about whether
> a specific line item was included in the estimate or not, and whether the
> quantity is correct.

**This makes supplement recovery a deterministic line-item reconciliation
problem, not a persuasion problem.** That matters enormously for this platform:
it is exactly the class of thing SAIRN builds well — a mechanical check against
real data — and exactly the class of thing that must **not** be handed to an LLM
to opine on. The app should compute *which line items are present, absent, or
quantity-mismatched* against the measured scope, and let the human argue it.

Money at stake: the average contractor-recovered supplement is **$7,000–$8,000
per claim**, on top of a first-adjuster estimate that is "almost always
incomplete on code items and hidden damage."

### 5.3 Proposed v1 shape

- **Claim record** — carrier, claim number, adjuster contact, date of loss, peril,
  policy type (ACV vs RCV), deductible.
- **Money lifecycle as real, separate fields** — RCV, depreciation, ACV, deductible,
  ACV cheque received, final invoice submitted, recoverable depreciation released.
  Never one collapsed "amount": conflating them is precisely how a contractor
  loses the depreciation release.
- **Photo evidence** — per-claim, tagged by elevation/slope and damage type,
  captured at adjuster meeting and again at tear-off. Tear-off photos are the
  evidentiary basis for the hidden-damage supplement.
- **Supplement worksheet** — line items with reason codes (code upgrade / hidden
  damage / quantity correction / omitted item), each tied to the photo(s) and the
  measured quantity supporting it. Deterministic comparison against the
  quantities schedule from Phase 2, **not** an AI opinion about what the adjuster
  "should" have included.
- **Contingency agreement** tracked as a real document with a signature state.
- **Status pipeline** mirroring the seven real steps, with an honest "waiting on
  carrier" state rather than a fake progress bar.

### 5.4 Xactimate integration — flagged, NOT in v1

Xactware does support third-party integration: estimate data can be sent from
Xactimate/XactAnalysis to third-party programs, via a Data Export Request form
and Verisk's Third-Party Integrations Team.

**Two reasons it stays out of v1, both stated plainly:**

1. It is a commercial-relationship gate, not an engineering task. It requires
   approval from Verisk, and nothing about that is under our control or
   schedulable.
2. **Verisk owns both.** Xactimate is Xactware, and Xactware Solutions is the
   assignee of US 9,501,700 (§1.1). Entering a formal integration relationship
   with the holder of the measurement patent family, while shipping a
   deliberately designed-around measurement feature, is a business and legal
   decision for Michael and an attorney — **not one an engineering scope doc
   should make quietly.**

v1 therefore treats Xactimate as an **external artifact the contractor already
has**: import/attach the estimate, reconcile line items against our own measured
scope, export a supplement worksheet the contractor submits themselves. No API
dependency, no Verisk relationship required, no capability claimed that depends
on someone else's approval.

---

## 6. Open items this document does NOT resolve

Unchanged by further research, and deliberately not closed here:

1. **Role vocabulary** — invented. Needs Michael's trade contacts before Phase 1.
2. **Patent design-around** — defensible, not cleared. Attorney before launch.
3. **Trademark** — inconclusive. Real TESS/EUIPO/WIPO screen, Classes 42 and 9.
4. **Per-material labor modelling** for copper/slate — unverified, no gap claimed.
5. **Non-English markets beyond German** — no coverage found, not researched.

---

## Sources

Patent: [US9501700B2](https://patents.google.com/patent/US9501700B2/en) ·
[EagleView v. Xactware $125M](https://www.roofingcontractor.com/articles/93946-jury-orders-xactware-verisk-to-pay-125-million-for-infringing-eagleviews-patents) ·
[trebled to $375M](https://www.randrmagonline.com/articles/89375-eagleview-awarded-375m-in-lawsuit-against-verisk-analytics-parent-company-to-xactware) ·
[Roofr invalidates '538/'800](https://news.bloomberglaw.com/ip-law/roofr-wipes-out-patents-underlying-delaware-infringement-suit) ·
[Eagle View v. Roofr](https://case-law.vlex.com/vid/eagle-view-techs-inc-1034396960)

Competitive: [Roofing software guide](https://roofingsoftwareguide.com/roundups/best-roofing-software/) ·
[AccuLynx alternatives](https://www.getexterio.com/resources/the-5-best-acculynx-alternatives-for-roofing-contractors-2026-exterio) ·
[plancraft](https://plancraft.com/de-de/gewerke/dachdecker-software) ·
[desk4](https://www.desk4.de/handwerk/dachdecker/) ·
[Softguide Dachdecker](https://www.softguide.de/software/dachdecker)

Materials: [GAF Energy contractors](https://www.gaf.com/en-us/plan-design/solar-roof/roofers) ·
[Solar shingles 2026](https://shinglescalculator.com/guides/solar-shingles-guide/)

Licensing/certs: [Jobber roofing licence by state](https://www.getjobber.com/academy/roofing-license/) ·
[Fixr state breakdown](https://www.fixr.com/articles/roofing-license-requirements-by-state) ·
[Certifications explained](https://mplsroofing.com/blog/roofing-certifications-explained/)

Insurance: [Claims process 2026](https://pipelineon.com/blog/roofing-insurance-claims-process/) ·
[Xactimate/RCV/ACV decoded](https://rooftechnologies.com/blog-xactimate-rcv-acv-depreciation-explained.php) ·
[Xactware third-party integrations](https://xactware.helpdocs.io/l/enUS/article/e1xxl3na8h-available-third-party-integrations)
