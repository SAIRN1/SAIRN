# StoneDesk external competitive-gap audit — measurement, scheduling/RBAC, OSHA-silica, AI quote-review (2026-09-26)

**Research pass, 2026-09-26. No code, no claims, no tier registers touched —
new file only, under `docs/cloud-research/`, on its own branch, same lane as
the SOC2 and SAIRNvet research already in this directory.**

---

## 0. Scope, and a correction to how "likely drifted" undersells the existing audit

The task brief for this pass described the existing StoneDesk audit as
"dated 09-02, oldest on the platform, likely drifted." That framing is only
half right, and per this platform's own verify-before-report rule the actual
state is worth stating precisely rather than assumed: **the 2026-09-02
audit** (`docs/superpowers/specs/2026-09-02-stonedesk-worldwide-competitive-gap-audit.md`)
**has not been left to drift silently — it has been actively kept honest**
via in-place, dated correction blocks and a companion status document,
`docs/2026-09-02-competitive-gap-status-rederived.md`, itself updated as
recently as 2026-09-15. Read together, the two documents show that **7 of
the original 8 named gaps are now closed or deliberately decided**, not
"likely drifted" in the sense of having gone stale in a way that misleads —
the drift here mostly ran in StoneDesk's favor. §0.1 below states current
status precisely, gap by gap, because "the audit is old" and "the product
has closed most of its own gaps since" are different findings and this
document should not blur them.

**This document does not re-derive the 2026-09-02 audit's core market
research** — the ERP/business-management competitor landscape (Moraware,
ActionFlow, Stonify, Stone Profit Systems, SlabWise, iBlocky, DDL/Digital Dry
Layout, and the Brazilian/adjacent-tier vendors), their module lists, and the
original pricing table. That research is real, vendor-sourced, and still the
reference. This document covers the four angles the task brief actually
asked for that the existing audit did not cover in depth: AR/digital
measurement (StoneDesk's own named differentiator), scheduling/production
-workflow depth plus role-based access control, OSHA-silica compliance as
its own specialist software category (plus WebAuthn/passkey authentication
in this market), and AI-driven quote *review* specifically (as distinct from
AI-driven quote generation, which the existing audit already covered) — with
a pricing spot-check folded into the last section rather than a full
re-survey.

### 0.1 A network-egress caveat that applies to every section below

As with every research pass run from this environment, outbound `WebFetch`
(full-page retrieval) returned `EGRESS_BLOCKED` for essentially every vendor,
aggregator, and reference domain attempted across all four research angles
behind this document. This was confirmed environment-wide (vendor domains,
neutral controls like Wikipedia, even a fresh check against
`en.wikipedia.org` as a control), not domain-specific, and not routed around
per this environment's own instructions. Every finding below therefore rests
on `WebSearch`'s indexed **excerpt** of a page, not an independently opened
full read — the same limitation the 2026-09-02 audit itself did not have
(it fetched vendor pages directly) and the same one the SOC2 and SAIRNvet
research in this directory already disclose. Confidence flags per claim
reflect this. **Nothing pricing-specific, capability-specific, or
legally load-bearing below should be quoted externally — to a customer, a
prospect, or in sales material — without a follow-up read from a network
that can reach these domains.**

---

## 0.2 Internal grounding — what StoneDesk actually has today, verified against source

Read directly from the live `stonedesk.html` and the platform's own
status-rederivation documents, not from the task brief's "100% complete"
characterization taken at face value — consistent with the brief's own
instruction to treat an apparent internal claim with real skepticism before
using it externally. In this case, verification mostly **confirms** the
brief's confidence, with real, specific nuances worth carrying forward.

**AR square-footage measurement is real, built, and browser-native — with a
documented, current platform limitation.** It uses the WebXR Device API,
requires no external library, and the measured number is written directly
into a quote's square-footage input field. The code's own comment states the
limitation plainly: it "works in any WebXR-capable mobile browser" but "iOS
AR is ARKit-only... does not expose WebXR AR sessions as of this writing" —
independently corroborated by this pass's research (§1) as still true as of
September 2026, not a stale comment. In practice, this means the feature
currently works on WebXR-capable Android browsers and not on iOS
Safari/Chrome, since Apple does not expose WebXR AR sessions to the browser
at all (AR on iOS requires a native ARKit app).

**"AI Quote Review" is real, wired, and has a genuine debugging history** —
`getAIQuoteAdvice()` reviews an already-calculated quote and gives feedback
before it goes out. This is not a paper feature: the file's own comments
record a real "no response" bug that was found and fixed (a case where
`lastCalc.total` never got set because the calculation function never ran)
and a z-index click-blocking bug that was discovered and fixed while
investigating the first one. A feature with a real bug-fix trail is stronger
evidence of being genuinely exercised than one with none.

**WebAuthn/passkey authentication is real and built** — `api/sd-webauthn.js`
uses `@simplewebauthn/server` on the backend and the browser-native
`navigator.credentials` API on the client, offered explicitly as an
*additional* login method alongside the existing PIN-based sign-in, not a
replacement for it.

**Current status of the 2026-09-02 audit's original 8 gaps**, per the
2026-09-02/09-15 status-rederivation (verify independently before relying on
this for anything beyond this document's own framing, since it is itself now
11+ days old):

| Gap | 2026-09-02 said | Current status |
|---|---|---|
| 1 — Customer-facing portal | "Structural, and the largest" | **BUILT** 2026-09-02 — public catalog served from a separate file (`stonedesk-catalog.html`) so an anonymous visitor cannot reach internal data, plus revocable order-tracking links. ⚠ Schema (`stonedesk_public_surface_schema.sql`) was still pending a run in Supabase as of last verification |
| 2 — Nesting produces no machine output | "Highest operational risk" | **BUILT — DXF only; G-code permanently declined by design**, not a half-finish. G-code would require feeds/speeds/tool numbers/machine origin the app has never had visibility into |
| 3 — No barcode/scanner support | Absent | **BUILT** — SCAN/FIND, USB barcode path. Residual: **duplicate external barcodes are reported, not resolved** — a real, still-open polish item |
| 4 — No slab-scanner integration | Absent | **OPEN — the one gap still genuinely open**, and it is vendor-gated: no SideShot/Iride/Mapascan interface exists, and closing it depends on a hardware-vendor relationship, not an engineering task alone |
| 5 — No e-signature / deposit collection | Absent | **BUILT, both halves** — found already built on 2026-09-15 by re-deriving the row against the file; had been mislabeled open (and briefly mislabeled vendor-blocked) before that |
| 6 — No QuickBooks integration | Absent | **Held open on purpose** — a deliberate platform decision (StoneDesk routes accounting to SAIRNbiz instead), not an oversight or a build item |
| 7 — No multi-location support | Absent | **BUILT — attribution only, not access partitioning.** Yard/location tracking and rollup reporting exist, but the feature explicitly does **not** scope any employee's access to a single yard — a real distinction a shop should not be allowed to assume away. ⚠ Schema pending as of last verification |
| 8 — No remnant publishing to a public website | Absent | **BUILT** — public remnant catalog card, publish toggle, price published (unlike a slab's cost). ⚠ Schema pending as of last verification |

**Net: as of the last verification available to this pass, only one of the
original eight gaps remains genuinely open, and it is blocked on a vendor
relationship rather than being an engineering gap.** Three of the built
items (1, 7, 8) carry a "schema pending in Supabase" caveat as of their last
check — meaning the code path exists but production functionality should be
re-confirmed rather than assumed live before any of this is used in a sales
conversation. This document did not re-verify the schema status itself
(outside this pass's scope, which is external market research); flagging it
here is exactly the "real skepticism" the task brief asked for applied to
what is otherwise a genuinely strong internal position.

---

## 1. AR and digital measurement competitive landscape

This is the most important section in this pass, since it is closest to
StoneDesk's own named differentiator.

**Dedicated laser-templating hardware — real, expensive, and not self
-serve.** **Prodim Proliner**, **Laser Products LT-2D3D**, and **Flexijet**
are all real, currently-sold capital equipment in the $15,000–$40,000 range
new (with real used-market listings anchoring a lower bound around
$7,200–$20,000 for Proliner specifically), and every one of them requires a
trained technician to physically visit the site with the device and export a
DXF/CAD file to a CNC saw — there is no self-serve version of any of them.
Stated accuracy clusters from roughly 0.2mm (Proliner) to 1/16" (LT-2D3D,
Flexijet). A previously-unlisted fourth option, **Leica 3D Disto** (a
general-purpose survey laser, not stone-specific, adopted by some fabricators
for templating at $8,000–$15,000), has a more credibly-sourced spec (±1mm at
10m) since Leica is an established geospatial-instrument maker rather than a
stone-industry-only vendor. None of these figures should be treated as
precise — vendor-aggregator pages disagreed with each other on price for the
same product in more than one case, which is recorded rather than smoothed
over.

**General-purpose phone AR measurement apps exist, but none treats itself as
fabrication-grade.** Apple's own Measure app is independently reviewed at
roughly 2–5% typical error (worse in poor conditions), explicitly described
by reviewers as "not reliable enough for construction or precision design
work." Polycam claims ±0.5" (a vendor claim, not independently benchmarked).
RoomScan Pro is independently reviewed around 1–3cm accuracy, explicitly
pitched for site surveys and remodel scopes and explicitly **not** for
"permit-grade drawings" — it even ships a manual laser-measurer override
mode, itself evidence the vendor doesn't trust pure AR for final numbers.
Cambria's own AR app is a design *visualizer* for previewing a slab pattern,
not a measurement tool, and should not be conflated with one.

**Among StoneDesk's seven named incumbent competitors, none has built or
announced phone-camera/AR-based site measurement.** Moraware's CounterGo is
manual drag-and-draw; ActionFlow's mobile app logs measurements by photo but
shows no AR capture; Stonify's closest "phone" feature (branded **Slabkast**)
is a *static photo* with four manually-tapped corner points for perspective
correction, used to approve a slab's layout/vein-matching in inventory — a
real and clever feature, but it measures a slab, not a room, and is not live
AR. The laser-hardware vendors ship companion smartphone apps, but these are
remote controls for their own $15K–$40K hardware, not phone-camera
replacements for it.

**The one finding that changes the picture, and it is current — this
month.** **Novaclad**, a new St. Louis company founded by former stone-shop
owners (not one of the seven named incumbents), launched a free iOS app in
**September 2026** that uses the iPhone's LiDAR sensor (requiring an iPhone
12 Pro or newer *Pro* model, iOS 17+) to scan a kitchen and hand a fabricator
a pre-measured, pre-priced lead in about five minutes, drawing on the
receiving shop's own price book. This is corroborated across multiple
independent wire pickups, though every source traces back to the same
company press release, so it should be treated as credible-that-it-exists
but unverified-on-technical-claims (no independent accuracy figure was found
anywhere). **It is architecturally the mirror image of StoneDesk's own
approach**: Novaclad is a native app, LiDAR-hardware-gated, iOS-Pro-only;
StoneDesk is browser-based, no-install, WebXR-gated, Android-only. Neither
covers both platforms, for different underlying technical reasons — Novaclad
because LiDAR-grade scanning needs a dedicated sensor Android phones
generally lack in the same form, StoneDesk because Apple has not opened
WebXR AR sessions to Safari. Novaclad is also a different business model: a
homeowner-facing lead-generation layer sitting between the customer and one
exclusive fabricator per market — arguably as much a disintermediation risk
to fabricators generally as a direct feature-parity threat to StoneDesk
specifically, and worth tracking for that reason rather than dismissing as
"different platform, not a real competitor."

**No rigorous, stone-specific, independently-published accuracy comparison
between phone AR and dedicated templating hardware exists** — this is a
genuine research gap, not an oversight. The order-of-magnitude comparison has
to be argued indirectly: dedicated hardware sub-millimeter to ~1/16",
general-purpose phone AR/LiDAR apps at 2–5% of measured distance under good
conditions (worse with the glossy, reflective, or dark surfaces common on
stone — a real risk factor no source quantified specifically for this
material). Independent 2026 sources corroborate StoneDesk's own code
comment: Safari still does not implement handheld WebXR AR sessions on
iOS/iPadOS, confirming that platform gap is current and real, not a stale
comment left over from an earlier iOS version.

### Sources (§1)

1. SlabWise — "Proliner Review: Should You Buy at $30K?" —
   https://slabwise.com/reviews/proliner-review — accessed 2026-09-26 —
   competing-vendor content marketing, lower confidence; price figures
   inconsistent with source 2 on the same site.
2. SlabWise — "Prodim Proliner: The Complete Shop Owner's Guide" —
   https://slabwise.com/guides/digital-templating-measurement — accessed
   2026-09-26 — same caveat as source 1.
3. Laser Products US — "LT-2D3D Laser Templator" —
   https://www.laserproductsus.com/lt-2d3d/ — accessed 2026-09-26 —
   vendor-sourced; "9,000+ sold" and accuracy figures self-reported,
   uncorroborated.
4. SlabWise — "LT-2D3D Laser Templator Review 2026" —
   https://slabwise.com/reviews/lt-2d3d-review — accessed 2026-09-26 —
   competing-vendor content, lower confidence.
5. SlabWise — "Flexijet Review 2026" — https://slabwise.com/reviews/flexijet-review
   — accessed 2026-09-26 — competing-vendor content, lower confidence;
   internally inconsistent with another figure on the same site.
6. Leica Geosystems — "Leica 3D Disto: Countertop Digital Templating" —
   https://shop.leica-geosystems.com/measurement-tools/3d-disto/blog/video/leica-3d-disto-countertop-digital-templating
   — accessed 2026-09-26 — vendor-sourced, moderate confidence.
7. AAI Survey — "Leica 3D Disto Laser Measurer, Absolute Accuracy" —
   https://aaisurvey.com/products/leica-3d-disto — accessed 2026-09-26 —
   third-party dealer spec sheet, corroborates accuracy figure.
8. Stone Equipment Warehouse — "Used PRODIM PROLINER8 Digital Templating
   System" — https://stoneequipmentwarehouse.com/product/prodim-proliner-8-digital-templating-system/
   — accessed 2026-09-26 — real marketplace listing, higher confidence than
   a marketing estimate.
9. Machinio — "PRODIM Equipment listings" —
   https://www.machinio.com/manufacturer/prodim — accessed 2026-09-26 —
   independent equipment marketplace, higher confidence.
10. Stone Tech Fabrication — "Digital Templating Countertops: Cut Rework,
    Speed Installs" — https://stonetechfabrication.com/digital-templating-countertops/
    — accessed 2026-09-26 — industry trade content, moderate confidence.
11. PR Newswire — "Novaclad Launches AI-LiDAR Measurement Engine..." —
    http://www.prnewswire.com/news-releases/novaclad-launches-ai-lidar-measurement-engine-for-the-building-trades-starting-with-a-free-app-that-measures-a-kitchen-in-five-minutes-302888372.html
    — accessed 2026-09-26 — company press release; existence/positioning
    credible, no independent technical verification.
12. Novaclad — "About Us" — https://www.novaclad.com/about-us — accessed
    2026-09-26 — vendor-sourced, snippet only.
13. Trend Hunter — "Phone-Scanned Countertop Quotes: Novaclad" —
    https://www.trendhunter.com/trends/free-app-measures-kitchens — accessed
    2026-09-26 — independent outlet summarizing the same press release.
14. DeviceTests — "How Accurate Is iPhone Measure?" —
    https://devicetests.com/how-accurate-is-iphone-measure — accessed
    2026-09-26 — independent hands-on review.
15. SlashGear — "How Accurate Is The iPhone's Measuring App?" —
    https://www.slashgear.com/1884872/how-accurate-iphone-measuring-app/ —
    accessed 2026-09-26 — established tech publication, moderate-high
    confidence.
16. Polycam — "How Accurate Are Polycam Scans?" —
    https://learn.poly.cam/hc/en-us/articles/50434745985556-How-Accurate-Are-Polycam-Scans
    — accessed 2026-09-26 — vendor-stated accuracy, not independently
    verified.
17. illustrarch — "RoomScan Pro Review" —
    https://illustrarch.com/articles/design-softwares/110334-roomscan-pro-review.html
    — accessed 2026-09-26 — independent review, moderate confidence.
18. Apple App Store — "Twindo (formerly Canvas)" —
    https://apps.apple.com/us/app/twindo-formerly-canvas/id1169235377 —
    accessed 2026-09-26 — confirms rebrand and active status.
19. Coohom — "AR vs Laser Room Measurement: Why Apps Miss Inches" —
    https://www.coohom.com/article/ar-measuring-apps-vs-laser-distance-meters-which-is-more-accurate
    — accessed 2026-09-26 — vendor-adjacent, moderate confidence; compares
    AR to handheld laser tape measures, not CNC templating rigs — a lower
    bar than stone fabrication actually needs.
20. Builder Online — "Cambria Launches Augmented Reality App for Design
    Visualization" — https://www.builderonline.com/products/finishes-surfaces/cambria-launches-augmented-reality-app-for-design-visualization_o
    — accessed 2026-09-26 — independent trade publication, higher
    confidence; confirms Cambria AR is a visualizer, not a measurement tool.
21. Slabkast — https://slabkast.com/ — accessed 2026-09-26 — vendor-sourced,
    snippet only; describes a static-photo tool, not live AR.
22. XRDoctors — "WebXR on iOS — What Works in Safari in 2026" —
    https://xrdoctors.pro/blog/webxr-on-ios-what-actually-works — accessed
    2026-09-26 — independent WebXR-specialist source, corroborates
    StoneDesk's own code comment.
23. BrowserStack — "WebXR - Compatible Browsers & Implementation" —
    https://www.browserstack.com/guide/webxr-and-compatible-browsers —
    accessed 2026-09-26 — established dev-tooling reference, moderate-high
    confidence.
24. SciTePress — "Localization Limitations of ARCore, ARKit, and Hololens in
    Dynamic Large-scale Industry Environments" (2020) —
    https://www.scitepress.org/Papers/2020/89899/89899.pdf — accessed
    2026-09-26 — peer-reviewed but dated and not stone-specific; directional
    only.
25. Medium (woll-an) — "Augmented Reality Measure App with WebXR and
    Three.js" — https://woll-an.medium.com/augmented-reality-measure-with-webxr-and-three-js-a0c8355eb91a
    — accessed 2026-09-26 — single developer anecdote, low confidence, not
    a controlled study.

---

## 2. Scheduling/production workflow depth and role-based access control

**Scheduling/production depth is real and specific for two competitors —
this is not an area where the market is thin.** **Moraware Systemize** is
the best-documented: configurable "JobTracker" stages a shop maps to its own
process (Lead → Measure/Template → Fabrication → Installation → Balance Due
→ Complete), built-in autoscheduling, color-coded calendars, and crew
assignment. **Stone Profit Systems** is arguably deeper on one specific
axis — it names actual shop-floor resources (digitizing, cutting, CNC,
edging, polishing) and ties machine/staff capability to a job specifically
to prevent double-booking, though the product overall targets larger shops
(see below). **ActionFlow** and **Stonify** make close-to-identical
claims to each other (shared calendars spanning template/measure →
fabrication → installation, drag-and-drop reallocation) without Moraware's
level of published stage-by-stage detail. **SlabWise** claims real
cross-stage logic (install scheduling gated on fabrication/material
-readiness status) but this is self-described marketing with no independent
account found. **iBlocky is confirmed, not merely under-researched, to have
no production-scheduling function at all** — it is a slab-warehouse/sales
platform. **DDL** has genuine phase-based planning logic, but for large
one-off architectural stone projects rather than day-to-day crew dispatch.

**RBAC/permissions depth has a much wider spread, and the finding here cuts
against assuming this is uncontested ground.** **Moraware's** RBAC is real,
granular, and unusually well-documented for this category: one role per
user, per-functional-area (Accounts, Jobs/Quotes, Orders, Administration)
CRUD+Execute granularity, several clonable starter roles, and a distinct
read-only "External User" role scoped to an account or specific jobs —
confirmed across the vendor's own help documentation and an independent
third-party integration knowledge base. **Stone Profit Systems** names a
"Security & User Privileges" feature with some real substantiating detail
(group-level privileges, IP/session monitoring) but nothing close to a
published permissions matrix. **Stonify** documents role-customizable
permissions, though its "roles" are partly bundled into pricing tiers
(Standard/Drawing/Lite), blending real RBAC with seat-tier feature-gating.
One specific claim about **ActionFlow** — "role-based access and audit
logging" — could not be re-traced to any actual ActionFlow page on a second
search pass and is flagged unverified rather than reported as fact.
**SlabWise, iBlocky, and DDL show a genuine documented absence**: no search
surfaced a named role type or permissions description for any of the three,
despite targeted queries including Italian-language ones for iBlocky.

**Whether granular RBAC is actually wanted in this market could not be
answered conclusively, and that thinness is itself the finding.** No
forum post, review, or vendor statement from anyone in the stone/countertop
trade was found saying, in their own words, that granular permissions are
unnecessary for a shop their size — searched for specifically, not assumed
absent. The only related signal is indirect and about a different product's
overall complexity, not permissions specifically: a rival vendor's (SlabWise)
comparison content states Stone Profit Systems' real target buyer is a shop
"over 25 employees, a distributor handling slab wholesale, or a
multi-location operation," calling a 12-employee shop buying it "overkill"
that leads to "implementation purgatory" — self-interested competitor
content, low-to-medium confidence, and about ERP/accounting scope broadly,
not about permissions in isolation. Weighed against this: Moraware, the
long-standing default and largest-installed-base product in exactly this
small-to-mid shop segment, is also the one with by far the deepest
documented RBAC, and nothing found flags that depth as unwanted complexity.
**The evidence does not clearly support "granular RBAC is over-built for
this market" one way or the other** — this should be stated as a genuine
open question, not resolved by assumption in either direction.

### Comparison table

| Product | Scheduling/production depth | RBAC/permissions depth |
|---|---|---|
| Moraware Systemize | Named workflow stages, autoscheduling, crew assignment — deepest documented | Deepest documented: per-functional-area CRUD+Execute, clonable roles, scoped external-user role |
| Stone Profit Systems | Resource-level (machine + staff capability tied to jobs) — deepest on this one axis | Named feature, some detail, no published matrix |
| ActionFlow | Real-time shared schedule, drag-and-drop reallocation | Unverified specific claim; generic "secure cloud" language only |
| Stonify | Production calendars, cross-department job stages | Role-customizable, partly bundled into pricing tiers |
| SlabWise | Claimed cross-stage/readiness-gated scheduling, self-described | No RBAC feature found |
| iBlocky | Confirmed absent — inventory/sales tool only | No RBAC feature found |
| DDL | Phase-based, large one-off projects only | No RBAC feature found |

### Sources (§2)

1. Moraware — "Countertop Scheduling and Job Management Software" —
   https://www.moraware.com/countertop-software/systemize-job-scheduling-tracking/
   — accessed 2026-09-26 — vendor-sourced, moderate-high confidence.
2. Moraware Systemize Help — "Edit Or Create User Roles In Systemize" —
   https://systemizehelp.moraware.com/systemize-help/edit-or-create-user-roles-in-systemize
   — accessed 2026-09-26 — vendor help docs, snippet only, moderate-high
   confidence.
3. Moraware CounterGo Help — "Assign Administrator Permissions" —
   https://countergohelp.moraware.com/article/1530-assign-administrator-permissions
   — accessed 2026-09-26 — vendor help doc, snippet only.
4. PinPoint Status Knowledge Base — "Moraware Permissions" —
   https://support.pinpointstatus.com/article/75-moraware-permissions —
   accessed 2026-09-26 — independent third-party integration doc,
   corroborates vendor docs.
5. SlabWise — "How to use Moraware for countertop shop scheduling" —
   https://slabwise.com/guides/how-to-use-moraware-for-countertop-shop-scheduling
   — accessed 2026-09-26 — competitor-authored content, moderate
   confidence.
6. Stone Profit Systems — "Top Ten Features" —
   https://www.stoneprofits.com/vTopTenFeatures.aspx?tabmenu=3 — accessed
   2026-09-26 — vendor-sourced, moderate confidence.
7. ActionFlow — "Field & Fabrication Scheduling" —
   https://www.actionflow.net/solutions/field-fabrication-scheduling/ —
   accessed 2026-09-26 — vendor-sourced, moderate confidence.
8. ActionFlow — Solutions overview — https://www.actionflow.net/solutions/
   — accessed 2026-09-26 — vendor-sourced, moderate confidence.
9. Stonify — homepage, "What Is Stonify?", and "Stonify vs Stone Profit
   Systems" — https://www.stonify.io/ ,
   https://www.stonify.io/blog/what-is-stonify-the-all-in-one-erp-for-stone-fabrication-shops
   , https://www.stonify.io/compare/stone-profit-system — accessed
   2026-09-26 — vendor marketing, self-interested comparison page, moderate
   confidence.
10. Stone Profit Systems Help Manual — "Schedule" —
    https://help.stoneprofits.com/schedule.html — accessed 2026-09-26 —
    vendor help manual, snippet only, moderate-high confidence given
    specificity.
11. SlabWise — "Best Scheduling Software for Countertop Shop Crews" —
    https://slabwise.com/best/best-scheduling-software-for-countertop-shop-crews
    — accessed 2026-09-26 — self-authored "best-of" content, low-medium
    confidence.
12. SlabWise — "Best Job Tracking Software 2026" —
    https://slabwise.com/best/job-tracking-software — accessed 2026-09-26 —
    vendor marketing, low-medium confidence.
13. iBlocky — https://iblocky.it/en — accessed 2026-09-26 — vendor-sourced;
    basis for a negative finding.
14. DDL — "Digital Stone Planning Software for Architects & Suppliers" —
    https://drylayout.com/en/solutions/project-planning — accessed
    2026-09-26 — vendor-sourced; basis for a negative finding.
15. SlabWise — "Stone Profit Systems Review: ERP for Stone Shops Tested" —
    https://slabwise.com/reviews/stone-profit-systems-review — accessed
    2026-09-26 — **competitor-authored comparative content, low-to-medium
    confidence, single-sourced**; "implementation purgatory"/forum-regret
    claims not independently verified against any actual forum thread.
16. Stone Profit Systems — Distributor solution overview —
    https://stoneprofits.com/vSolutionDistributoroverview.aspx — accessed
    2026-09-26 — circumstantial corroboration only.
17. Stone Profit Systems — Fabricator solution overview —
    https://stoneprofits.com/vSolutionFabricatoroverview.aspx — accessed
    2026-09-26 — circumstantial corroboration only.
18. Frontegg — "Roles and Permissions Handling in SaaS Applications" —
    https://frontegg.com/guides/roles-and-permissions-handling-in-saas-applications
    — accessed 2026-09-26 — generic SaaS background, not stone-specific.

---

## 3. OSHA-silica compliance specialists and WebAuthn in this market

**The hazard StoneDesk's HR/safety module addresses is real, current, and
escalating — not a manufactured compliance angle.** OSHA's construction
silica standard, 29 CFR 1926.1153, sets an 8-hour TWA permissible exposure
limit of 50 µg/m³ with a 25 µg/m³ action level, paralleled by 29 CFR
1910.1053 for general industry. OSHA/NIOSH maintain a countertop-specific
hazard alert (reported updated as recently as February 2026) and have run a
targeted inspection initiative against engineered-stone fabrication shops
since September 2023. The severity is backed by peer-reviewed evidence: a
2026 *NEJM Evidence* study using California Department of Public Health
surveillance found **592 confirmed silicosis cases** among engineered-stone
countertop workers from 2019 through June 2026, with 65 lung transplants and
31 deaths. California's SB 20 (the STOP Act, in effect since October 2025)
responded to this, and Cal/OSHA has a draft emergency standard capping
engineered stone at 1% crystalline silica open for comment through September
30, 2026. (A higher, newer figure — 631 cases/35 deaths, August 2026 —
appears only in secondary news aggregation, not the primary CDPH/NEJM
sources; the escalation trend is real, that specific number is
lower-confidence.)

**A specialist software layer exists, but it splits into two tiers, and
neither matches a small stone shop well — which is exactly the gap
StoneDesk's built-in module sits in.** At the top: general industrial
-hygiene/EHS suites (VelocityEHS, Cority, Intelex) have genuine silica
functionality — similar-exposure-group management, sampling-plan scheduling,
automatic comparison against PELs — but are enterprise-priced and
enterprise-implemented (independent comparison sources describe $100k+/year
costs and 9–18 month rollouts for this tier, explicitly unsuited to small
business). At the bottom: narrow, often-free tools generate only the written
exposure-control-plan document (CPWR's NIOSH-funded "Create-A-Plan,"
BCCSA's Silica Control Tool) with no monitoring history, training-expiry
tracking, or OSHA 300 log attached. **Tellingly, SlabWise — one of
StoneDesk's own named ERP competitors — publishes its own guides on which
OSHA rules apply and how to write a safety plan for stone shops, explicitly
telling readers a physical binder remains the compliance standard** because
its own shop-management module is only "a natural home for equipment
checklists and training record links" — a competitor's own content
effectively conceding the gap StoneDesk's built-in module fills.

**On authentication, the market has almost nothing, and StoneDesk's WebAuthn
support is a genuine current differentiator in its actual competitive set.**
Direct checks of all seven named competitors found exactly one
authentication-hardening feature anywhere: **Moraware has real TOTP
two-factor authentication** (an authenticator app with QR-code enrollment)
live across CounterGo, Systemize, and Inventory — a materially different,
weaker security model than a phishing-resistant WebAuthn passkey. No
mention of 2FA, passkeys, or biometric login was found for ActionFlow,
Stonify, iBlocky, or DDL, and Stone Profit Systems' own login/security help
documentation covers session/IP monitoring with no mention of 2FA or
passkeys at all — for Moraware and Stone Profit Systems specifically, actual
security documentation was located and passkeys were confirmed absent from
it, a stronger negative signal than for the vendors where no dedicated
security documentation surfaced at all. The broader passkey/WebAuthn
adoption trend is real but sharply size-tiered: a FIDO Alliance-backed
survey found 87% of *500+-employee* enterprises deploying or planning
passkeys, but no evidence of passkey/WebAuthn adoption was found anywhere in
blue-collar-trade vertical SaaS more broadly (Jobber, ServiceTitan, Housecall
Pro, Buildertrend, Procore were checked and returned no evidence either
way — an inconclusive gap, not a confirmed absence). **Net: StoneDesk's
WebAuthn support currently reads as a real, still-rare differentiator in
its actual market, not a catch-up move into something already standard
there** — while the enterprise-layer trend is worth watching as a signal of
where the floor eventually moves.

### Sources (§3)

1. OSHA — 29 CFR 1926.1153, Respirable crystalline silica —
   https://www.osha.gov/laws-regs/regulations/standardnumber/1926/1926.1153
   — accessed 2026-09-26 — primary regulatory text, high confidence.
2. OSHA — 29 CFR 1910.1053, Respirable crystalline silica —
   https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.1053
   — accessed 2026-09-26 — primary regulatory text, high confidence.
3. Safety+Health Magazine — "OSHA and NIOSH update alert on silica and
   countertop workers" — https://www.safetyandhealthmagazine.com/osha-and-niosh-update-alert-on-silica-and-countertop-workers/
   — accessed 2026-09-26 — trade press, moderate-high confidence.
4. OSHA Standard Interpretation (2023-09-22) — "Respirable Crystalline
   Silica Focused Inspection Initiative in the Engineered Stone Fabrication
   and Installation Industries" —
   https://www.osha.gov/laws-regs/standardinterpretations/2023-09-22 —
   accessed 2026-09-26 — primary source, high confidence.
5. NEJM Evidence — "Silicosis among Workers Fabricating Engineered Stone
   ('Quartz') Countertops in California, 2019–2026" —
   https://evidence.nejm.org/doi/full/10.1056/EVIDpha2600187 — accessed
   2026-09-26 — peer-reviewed, high confidence.
6. CIDRAP — "Public Health Alerts: Silicosis among workers fabricating
   engineered stone ('quartz') countertops in California, 2019-2026" —
   https://www.cidrap.umn.edu/misc-emerging-topics/public-health-alerts-silicosis-among-workers-fabricating-engineered-stone
   — accessed 2026-09-26 — academic public-health reporting, corroborates
   NEJM figures, high confidence.
7. California DIR News Release 2026-45 — "Standards Board Advances Efforts
   to Protect Workers from Silicosis" — http://www.dir.ca.gov/DIRNews/2026/2026-45.html
   — accessed 2026-09-26 — state regulatory agency, high confidence on the
   headline fact; STOP Act provision details from an aggregated snippet, not
   independently re-verified.
8. Tech Times — "Quartz Countertops Have Sickened 592 Workers, Killed 31:
   Now Congress May Block Their Lawsuits" —
   https://www.techtimes.com/articles/324271/20260813/quartz-countertops-have-sickened-592-workers-killed-31-now-congress-may-block-their-lawsuits.htm
   — accessed 2026-09-26 — secondary news aggregator, lower confidence; used
   only to flag a rising-case-count trend, not as the primary figure.
9. VelocityEHS — "Understanding MSHA's 2024 Respirable Crystalline Silica
   Final Rule" — https://www.ehs.com/2024/10/understanding-mshas-2024-respirable-crystalline-silica-final-rule/
   — accessed 2026-09-26 — vendor content, moderate confidence.
10. Intelex — "Industrial Hygiene Software" —
    https://www.intelex.com/products/applications/industrial-hygiene-software
    — accessed 2026-09-26 — vendor marketing, moderate confidence.
11. Cority — "Industrial Hygiene Software & Monitoring Solutions" —
    https://www.cority.com/health-cloud/industrial-hygiene-software/ —
    accessed 2026-09-26 — vendor marketing, moderate confidence.
12. SmartQHSE — "VelocityEHS vs Cority 2026: Feature & Pricing Comparison" —
    https://www.smartqhse.com/safety-blog/velocityehs-vs-cority-feature-by-feature-2026
    — accessed 2026-09-26 — independent comparison site, moderate
    confidence; pricing not independently verified against vendor quotes.
13. CPWR Silica Safe — "Create-A-Plan Overview" —
    https://www.silica-safe.org/plan-overview/ — accessed 2026-09-26 —
    NIOSH-funded nonprofit, moderate-high confidence.
14. BCCSA — Silica Control Tool — https://www.silicacontroltool.com/ —
    accessed 2026-09-26 — Canadian construction-safety association tool,
    moderate confidence, not a US-OSHA product.
15. SafetyCulture — "Silica Task Risk Assessment Template for Construction"
    — https://safetyculture.com/library/construction/silica-task-risk-assessment-yivorx6lesniqecc
    — accessed 2026-09-26 — vendor platform hosting community templates,
    moderate confidence.
16. SlabWise — "What OSHA rules apply to stone countertop fabrication
    shops" — https://slabwise.com/guides/what-osha-rules-apply-to-stone-countertop-fabrication-shops
    — accessed 2026-09-26 — competitor's own content marketing, used as
    evidence of the competitor's product positioning, not as a neutral
    source.
17. Moraware CounterGo Help — "Two-Factor Authentication Login" —
    https://countergohelp.moraware.com/countergo-help/countergo-two-factor-authentication-login
    — accessed 2026-09-26 — vendor help doc, moderate-high confidence.
18. Moraware Systemize Help — "Two-Factor Authentication Login" —
    https://systemizehelp.moraware.com/systemize-help/systemize-two-factor-authentication-login
    — accessed 2026-09-26 — vendor help doc, moderate-high confidence.
19. ActionFlow — https://www.actionflow.net/ — accessed 2026-09-26 — no
    authentication-security feature found; absence-of-evidence only.
20. Stonify — https://www.stonify.io/ — accessed 2026-09-26 — no
    authentication-security feature found; absence-of-evidence only.
21. iBlocky — https://iblocky.it/en — accessed 2026-09-26 — no
    authentication-security feature found; absence-of-evidence only.
22. DDL — https://drylayout.com/ — accessed 2026-09-26 — no
    authentication-security feature found; absence-of-evidence only.
23. Stone Profits Help Manual — "Login/Logout" —
    https://help.stoneprofits.com/loginlogout — accessed 2026-09-26 —
    vendor help doc, moderate confidence; no 2FA/passkey mention.
24. FIDO Alliance — "New FIDO Alliance Research Shows 87% of U.S. and UK
    Workforces are Deploying Passkeys for Employee Sign-ins" —
    https://fidoalliance.org/new-fido-alliance-research-shows-87-percent-us-uk-workforces-are-deploying-passkeys-for-employee-sign-ins/
    — accessed 2026-09-26 — consortium-backed survey, high confidence for
    what it measures; explicitly a 500+-employee sample, not SMB.
25. DarkReading — "New Study: Enterprise Passkey Adoption Tops 85%" —
    https://www.darkreading.com/application-security/study-enterprise-passkey-adoption
    — accessed 2026-09-26 — independent trade press, moderate-high
    confidence.
26. Corbado — "Passkeys for B2B SaaS: Benefits & Challenges (2026)" —
    https://www.corbado.com/blog/passkeys-b2b-saas — accessed 2026-09-26 —
    single vendor-adjacent blog, lower confidence.
27. MojoAuth Blog — "Passkey Adoption Rates by Industry in 2026" —
    https://mojoauth.com/blog/passkey-adoption-rates-by-industry — accessed
    2026-09-26 — passwordless-auth vendor's own marketing blog, low
    confidence, no disclosed methodology.

---

## 4. AI quote-review tooling and a pricing refresh

**Among all eight named stone-fabrication competitors (including Marmo
IA/ERPedra), no vendor has a discrete feature that reviews an
already-calculated quote afterward for errors or pricing anomalies** — the
shape of StoneDesk's `getAIQuoteAdvice()`. What each has instead: Moraware's
CounterGo pricing is described by third-party comparisons as "purely
rule-based" with no AI at all; ActionFlow shows real-time margin feedback
*during* quote construction (rules math, not AI, and not a post-hoc review);
Stone Profit Systems reduces errors via templated "packages," no AI branding
found; DDL and Marmo IA apply AI to generation (contour digitization,
auto-pricing from a 2D drawing), not review; iBlocky has no AI feature at
all. **SlabWise is the closest stone-specific analog** — its own marketing
describes "quote-risk flagging for jobs that look under-priced relative to
historical margins" and "edge upcharge suggestions based on shop pricing
history," though the public text does not make clear whether this fires as a
discrete pass on a completed quote or concurrently while the quote is being
built (framing leans toward the latter), and it is entirely self-reported.

**The concept itself is real and marketed — just mostly outside stone.**
Among general-contractor/remodeling estimating tools, **Buildxact's "AI
Estimate Reviewer"** is the clearest true match found anywhere in this
research: explicitly described as double-checking an already-built estimate
for common mistakes and automatically flagging missing line items before a
bid is sent — the same before-it-goes-out shape as StoneDesk's feature, just
for remodeling rather than stone. InEight's AI benchmarking flags outlier
cost assumptions continuously during generation (not a discrete post-calc
pass), and Provision's Scope Agent reviews drawings/specs pre-bid for scope
nobody priced at all (upstream of pricing, closer to takeoff review).
**The gap itself is the finding: "AI reviews a completed estimate" is proven
and marketed in adjacent verticals (led by Buildxact), with SlabWise's
margin-flagging the nearest stone-specific approximation — but nothing found
matches StoneDesk's discrete post-calculation advice step exactly, in stone
or immediately adjacent to it.** This should be read as a real but not
indefinitely defensible differentiator: the pattern is already proven and
spreading in construction-adjacent software, which is a reasonable signal
for how soon a direct stone-specific copy could appear.

**Pricing spot-check: every 2026-09-02/09-04 figure held, unchanged, as of
2026-09-26.** Moraware CounterGo $100/user/month, Systemize $120/user/month
(3-user minimum, dropping to $50/user past the fifth user), Inventory
$50/user/month (requires Systemize) — the 5-user, three-module total remains
exactly $1,350/month. Stonify's $500/month base (with a $500 seat credit)
plus $50/$75/$35 per-user add-ons by tier is unchanged (a separate "$100/mo,
Drawing Only" SKU was found alongside it — an additional plan, not a
contradiction). iBlocky's €299/€399 tiers and SlabWise's $99/$299/$799 tiers
(now explicitly named Starter/Pro/Enterprise) are both unchanged. The
caveat that applied on 2026-09-02 still applies: Moraware publishes no
public price list and its own FAQ directs prospects to a sales demo, so its
figures rest on consistent third-party corroboration rather than a direct
vendor quote — the same limitation as before, not a new one.

### Sources (§4)

1. SlabOS — "SlabOS vs Moraware: Modern Countertop Software Compared
   (2026)" — https://slabos.com/vs-moraware — accessed 2026-09-26 —
   competitor comparison content, snippet only.
2. SlabWise — "Moraware CounterGo Review 2026: Pricing and Limits" —
   https://slabwise.com/reviews/countergo-review — accessed 2026-09-26 —
   competitor-authored review, snippet only.
3. ActionFlow — "Empowering Precision Quoting for Countertop Fabrication" —
   https://www.actionflow.net/empowering-precision-quoting-for-countertop-fabrication/
   — accessed 2026-09-26 — vendor-sourced, feature not branded "AI."
4. Stone Profit Systems — "Top Ten Features" —
   https://www.stoneprofits.com/vTopTenFeatures.aspx — accessed 2026-09-26 —
   vendor-sourced.
5. SlabWise — "Stone Profit Systems Review: ERP for Stone Shops Tested" —
   https://slabwise.com/reviews/stone-profit-systems-review — accessed
   2026-09-26 — competitor-authored review.
6. SlabWise — "AI Quote Generator for Countertop Fabricators" —
   https://slabwise.com/product/quoting — accessed 2026-09-26 — vendor
   primary source, self-reported.
7. SlabWise — "Best Countertop Quoting Software 2026" /
   "Best Countertop Estimating Software for Shops (2026)" —
   https://slabwise.com/best/countertop-quoting-software ,
   https://slabwise.com/best/estimating-software — accessed 2026-09-26 —
   competitor-authored comparison.
8. SlabWise — Features page — https://slabwise.com/features — accessed
   2026-09-26 — vendor primary source.
9. iBlocky — https://iblocky.it/en — accessed 2026-09-26 — vendor primary
   source; no AI feature found.
10. DDL — https://drylayout.com/en/ — accessed 2026-09-26 — vendor primary
    source.
11. DDL — "Stone Fabrication Software 2026: How to Choose" —
    https://drylayout.com/en/blog/stone-fabrication-software-guide/ —
    accessed 2026-09-26 — vendor primary source.
12. Marmo IA + ERPedra — https://marmoia.com.br/ — accessed 2026-09-26 —
    vendor primary source.
13. Stone Finder (BR) — "Melhor Sistema para Marmoraria: Conheça o ERPedra
    com IA..." — https://stonefinder.com.br/melhor-sistema-para-marmoraria-conheca-o-erpedra-com-ia-orcamentos-e-gestao-completa/
    — accessed 2026-09-26 — third-party Brazilian trade site.
14. SlabWise — "StoneApp Review" / StoneGrid official site —
    https://slabwise.com/reviews/stoneapp-review , https://stonegridusa.com/
    — accessed 2026-09-26 — low confidence, unconfirmed attribution, not
    one of the eight named competitors.
15. Buildxact — "How AI Construction Estimating Software Solves These
    Common Estimating Mistakes" — https://www.buildxact.com/us/blog/ai-tech-estimating/
    — accessed 2026-09-26 — vendor marketing; strongest true comparable
    found for "AI reviews a completed estimate."
16. InEight — "AI Benchmarking: Stop Construction Planning in the Dark" —
    https://ineight.com/news/ai-benchmarking/ — accessed 2026-09-26 —
    vendor-sourced.
17. InEight — "Construction Estimating Software" —
    https://ineight.com/products/ineight-estimate/ — accessed 2026-09-26 —
    vendor-sourced.
18. Techli — "Provision launches Scope Agent, AI tool to close
    construction's multibillion-dollar scope gap" —
    https://techli.com/provision-launches-scope-agent-ai-tool-to-close-constructions-multibillion-dollar-scope-gap/11217/
    — accessed 2026-09-26 — independent trade press.
19. 2cm.ai — "Countertop Quoting Software" —
    https://2cm.ai/countertop-quoting-software — accessed 2026-09-26 —
    vendor-sourced.
20. Exayard — "Countertop Estimating Software | AI-Powered" —
    https://exayard.com/countertop-estimating-software — accessed
    2026-09-26 — vendor-sourced.
21. Moraware — "Pricing" — https://www.moraware.com/pricing/ — accessed
    2026-09-26 — vendor primary source; not directly fetchable, figures via
    snippet, corroborated by sources 1, 2, 22.
22. Stonemagnet — "Countertop shop software: what exists and what each one
    is for (2026 prices)" — https://stonemagnet.com/blog/countertop-software/
    — accessed 2026-09-26 — independent blog.
23. Stonify — https://www.stonify.io/ — accessed 2026-09-26 — vendor
    primary source.
24. Stonify — Release notes v0.5.94 —
    https://www.stonify.io/release-notes/release-notes-v0.5.94 — accessed
    2026-09-26 — vendor primary source.
25. Moraware — "FAQ" — https://www.moraware.com/faq/ — accessed 2026-09-26
    — vendor primary source; confirms no published price list.

---

## 5. Synthesis — what actually changed and what's genuinely new

1. **Of the original 8 gaps, exactly one remains genuinely open, and it is
   vendor-gated, not an engineering task**: GAP 4, slab-scanner integration.
   This is a significant, real update to the 2026-09-02 audit's own framing,
   which called the (now-closed) customer portal gap "the largest and
   structural." Report the current picture, not the 2026-09-02 one.
2. **The single most important new finding in this pass is Novaclad** (§1)
   — a real, named, September-2026-launched threat sitting directly on
   StoneDesk's own AR-measurement differentiator, but on the opposite
   platform (native iOS/LiDAR vs. StoneDesk's browser/WebXR/Android) and
   with a different business model (a homeowner-facing lead-generation
   middleman, not a shop tool). It should be tracked as a disintermediation
   risk to the fabricator relationship generally, not dismissed as
   "different platform, therefore irrelevant," and not overstated as a
   direct feature-parity loss either.
3. **WebAuthn and the OSHA-silica module are both genuine, current,
   defensible differentiators** — no named competitor has anything close to
   either, and in the silica case a competitor's own content implicitly
   concedes the gap. Neither is guaranteed to stay that way (the enterprise
   passkey floor is moving; specialist EHS software exists at a tier that
   could theoretically move down-market).
4. **AI Quote Review is real and rare in stone specifically, but the
   pattern is already proven one vertical over** (Buildxact, general
   contracting) — a real but not indefinitely defensible differentiator,
   worth continued investment rather than treating as a permanent moat.
5. **Scheduling depth and RBAC are not clean wins the way the AI/compliance
   angles are.** Moraware in particular has real, well-documented depth on
   both axes. This document does not compare StoneDesk's own scheduling or
   RBAC implementation against these findings (that would require an
   internal audit outside this pass's external-research scope) — but
   whoever does make that comparison should not assume competitors are thin
   here.
6. **Two small residual items surfaced by re-reading the internal status
   docs, not by external research, worth carrying forward regardless of
   this document's own scope**: GAP 3's duplicate-external-barcode handling
   is still "reported not resolved," and GAPs 1/7/8 carry a "schema pending
   in Supabase" caveat as of their last verification — both are two-minute
   checks against current state that should happen before any of those
   three "BUILT" gaps are described as fully live to a customer.

---

## 6. What this document does not establish or decide

- **No claim in this document should be quoted externally** — to a
  customer, prospect, or in sales material — without a follow-up read from
  a network that can reach the underlying primary sources; every finding
  rests on search-engine snippets, per §0.1.
- **This document does not decide whether or how StoneDesk should respond
  to the Novaclad finding**, pursue iOS AR support, build a scanner-vendor
  integration to close GAP 4, or invest further in AI quote-review — that is
  a `sairn-software-architect` / `sairn-decision-gate` question, consistent
  with how the 2026-09-02 audit treats its own findings as "not a build
  decision."
- **It does not re-verify the Supabase schema status** for GAPs 1, 7, or 8,
  or the duplicate-barcode issue under GAP 3 — it only flags, from the
  platform's own status documents, that these should be re-checked.
- **It does not compare StoneDesk's own scheduling or RBAC implementation**
  against the competitor findings in §2 — that would require an internal
  audit outside this pass's external-market-research scope.

## 7. Decay

Every source above is a search-index snapshot from 2026-09-26 of pages this
session's sandboxed network could not open directly (§0.1). The Novaclad
finding (§1) is the single fastest-moving fact in this document — it is
one month old and should be re-checked before being treated as a stable
competitive fact rather than a fast-breaking one. Pricing (§4) and the
internal gap-status table (§0.2) are both time-sensitive in the ordinary
way this document series already treats them. **Do not treat any pricing
figure, competitive-feature claim, or "BUILT"/"OPEN" gap status here as
current without re-checking directly against the live source**, and re-run
the vendor-facing portion of this pass from a network that can reach the
underlying domains before any of it is used in a customer-, investor-, or
sales-facing statement.
