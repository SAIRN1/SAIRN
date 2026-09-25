# Worldwide external competitive-gap audit — SAIRNroofing

**Sourcing caveat, read this before anything else below:** this session's
outbound network could not reach any vendor, trade-press, or patent-office
domain. Every vendor-attributed fact in this document is a `WebSearch`
index snippet of that vendor's own domain, not an opened page — one grade
below this series' normal standard. Full disclosure and the direct test
evidence are in §0.

**Second and more important caveat, also read before anything else:**
SAIRNroofing already carries **extensive, dated, cited internal patent
analysis** on aerial roof measurement —
`docs/superpowers/specs/2026-08-24-sairnroofing-v1-scope.md` §1 and
`docs/superpowers/specs/2026-08-26-ip-screen-roofing-delta-and-deadline-engine.md`.
This document does not re-derive that analysis and does not recommend
crossing the boundary it sets. Where this pass's external research touches
measurement or aerial imagery (§2.2), it is reported as market fact only.

**Research pass, 2026-09-25. No code written, no app file touched.**
Written by a standalone cloud session under `docs/cloud-research/` per
instruction (new files only, new branch, no PR). This is the first
external competitor document for SAIRNroofing — a real, thorough internal
worldwide audit exists
(`docs/superpowers/specs/2026-08-26-competitive-gap-audit-roofing-dental-senior.md`)
and a full re-derivation against the code exists
(`docs/2026-09-17-sairnroofing-competitive-gap-rederived.md`), but neither
is an *external* document in this series' sense — both are internal,
code-facing status checks. §1 below anchors to both rather than
duplicating them.

**Method and standard**: the reference for this series is
`docs/superpowers/specs/2026-09-02-stonedesk-worldwide-competitive-gap-audit.md`
— every competitor claim read from the vendor's own site, not a comparison
article; aggregator pages used only to find vendors; a failed fetch
recorded as a failure, never filled in; pricing only from a vendor's own
pricing page, and where a vendor gates pricing behind a sales contact,
that absence is reported as a market fact, not filled in from an
aggregator's guess.

---

## 0. A material limitation, stated before anything else

**This session's outbound network cannot reach any vendor, trade-press, or
patent-office domain**, confirmed directly by a blocked `WebFetch` to
`acculynx.com` against a healthy proxy status (`enabled: true`,
`bundleCoversEveryHost: true`, zero recent relay failures, port 37503 —
the same fresh-instance pattern seen in this series' other sessions
today, confirming a persistent destination-level policy, not a one-off
fault). Per the proxy documentation's own instruction on a blocked host —
*"Do not retry or route around it — report the blocked host"* — that
instruction is followed here.

**Evidence grade**: every vendor-fact cell below is a `WebSearch` result
restricted to the named vendor's own domain via `allowed_domains` — the
search engine's indexed excerpt of that page, not the page itself. Court
opinions and litigation reporting in §3 are treated the same way: cited to
named outlets (Law360, Bloomberg Law, IPWatchdog) and, where possible, to
the court's own opinion, but none were opened directly either. **Nothing
here should be quoted externally — to a contractor, in a pitch, in a
proposal, or into the existing patent analysis — without a follow-up pass
from a network that can reach these domains and a real page read, not a
snippet.** A small number of figures below (marked individually) could
not be traced to a primary source at all and are reported as
discrepancies or open items, not resolved.

Retrieval date for every row below: 2026-09-25.

---

## 1. What SAIRNroofing is, anchored to the existing internal work — not
re-derived here

From `docs/2026-09-17-sairnroofing-competitive-gap-rederived.md` (a full
re-derivation of the original 2026-08-26 worldwide audit against the code
at HEAD) and `docs/CRITICALITY-TIERS.md:63` (27 resources, 24 Tier A):

- **Every material type shipped except one.** `RF_MATERIALS_LIST` covers
  Asphalt Shingle, Metal, Slate, Copper, Wood Shake, TPO, EPDM, Modified
  Bitumen, and three named solar-shingle products (GAF Timberline Solar,
  Tesla Solar Roof, CertainTeed SolarShingle) — eleven materials,
  server-enforced (`RF_MATERIALS` in `api/sd-data.js`), with a real
  certification gate on the Tesla product specifically. **Clay/concrete
  tile has no line item at all.**
- **Warranty registration and certification-gated pricing tiers are
  BUILT** (row A1, closed) — `api/_lib/roofing-warranties.js`, its own
  test suite, and a schema that deliberately refuses to seed a guessed
  manufacturer-tier list or a guessed renewal window, on the stated
  reasoning that *"being wrong here costs the homeowner the coverage."*
- **Multi-entity/multi-location consolidation is BUILT** (row B5, closed)
  — `api/_lib/roofing-consolidation.js`, `rf_entities`, with `entity_id`
  stored on the location rather than stamped onto historical records, so
  moving a branch between entities moves its whole history rather than
  splitting it.
- **Subcontractor compliance, safety/JHA with fall-protection-equipment
  expiry tracking, prequalification and bonding-capacity checking, a
  commercial roof asset registry, and WIP/retainage/draw-request
  accounting are all BUILT** (rows A3, B4, B7, B1, two-thirds of B3
  respectively) — this series' own adjacent-trade-crossover finding for
  SAIRNmechanical (§2.8 of that document) already drew on the
  subcontractor-compliance and bonding-capacity pieces as a proven
  in-platform pattern.
- **The one item still genuinely open across the entire original
  twelve-row audit: accounting-software integration.** Zero markers for
  QuickBooks, Xero, general ledger, IIF, or chart of accounts — no
  partial implementation, no disclosure banner.
- **Two items are refused rather than open, deliberately**: certified
  payroll (would require asserting a prevailing-wage determination the
  app has no authority to invent) and supplier EDI transport (disclosed
  on screen as not a real EDI connection, pending trading-partner
  agreements with individual suppliers).
- **Aerial/CV roof measurement is deliberately not built, and this is a
  legal decision, not an oversight** — see §2.2.
- **Xactimate (the dominant insurance-restoration estimating tool) is
  deliberately not integrated**, treated instead as an external artifact
  the contractor already owns: import, reconcile line items against
  SAIRNroofing's own measured scope, export a supplement worksheet the
  contractor submits themselves. The stated reason is as much legal as
  technical: Xactware/Verisk owns both Xactimate and the aerial-CV patent
  family SAIRNroofing's measurement feature is designed around, and
  entering a formal integration relationship with them was judged a
  business-and-legal decision, not a scope-doc engineering call
  (`docs/superpowers/specs/2026-08-24-sairnroofing-v1-scope.md` §5.4).

---

## 2. What the market does, against each open item

### 2.1 Fresh competitor check — pricing and features, re-verified against
a 2026-08-24 internal snapshot, plus SumoQuote (previously unresearched)

| Vendor | Fresh finding (2026-09-25) | vs. 2026-08-24 snapshot |
|---|---|---|
| JobNimbus | No flat published price (Admin/Sales/Field role-tiered quote); aggregator figures suggest Essentials from ~$299/mo annually. Two-way QuickBooks sync (Desktop/Online/Server) confirmed. | Roughly consistent with the ~$350/mo team figure on file; still avoids a public rate card. |
| AccuLynx | Still "Pricing Request" only, no public number found even on their own domain this pass. Two-way QuickBooks sync confirmed; free-to-use ordering integration for EagleView, Hover, Geospan, and GAF QuickMeasure (reports priced separately); a GAF Master Elite email-verification gate tracks certified-tier pricing (§2.4). | Could not re-verify the $250–500+/mo figure on file this pass — neither confirmed nor contradicted. |
| Roofr | Three named tiers now: Starter (3 seats, free/pay-as-you-go), Essentials (5 seats), Scale (unlimited seats). Measurement reports a fixed **$13 each**, 2-hour delivery on paid plans. QuickBooks Online export confirmed. | "Free tier" still true, but three named paid tiers and a fixed report price are new specificity versus the snapshot. |
| Leap | (Not on the original competitor list; surfaced here as an EagleView/Hover/GAF-QuickMeasure integrator.) Pricing only found via non-vendor-restricted aggregators (~$79–298+/mo) — **lower confidence, flagged as such rather than treated as verified.** | No prior baseline. |
| SubcontractorHub | Confirmed via own domain: modular suite covering job management, billing, dispatch, invoicing, insurance claims/supplements, and job costing for roofing/solar/HVAC, "500+ teams." No pricing surfaced. | Consistent with the snapshot; no pricing was found there either. |
| iRoofing | **Correction worth carrying forward**: the real US product lives at `iroofing.org`; `iroofing.com` resolves to an unrelated Australian roofing contractor, a genuine false-positive risk for anyone researching this vendor. Confirmed: DIY measurement from satellite/aerial/drone/blueprint imagery, pitch detection, an estimator, digital material catalogs, in-app distributor ordering. | Domain correction, not previously on file. |
| ServiceTitan | QuickBooks Online + Desktop (Premier/Enterprise) confirmed; a named "Roofing Pricebook Pro"; warranty/contract e-signature in the mobile field app. No public per-seat price found this pass. | Consistent with the $1,225–2,000+/mo-for-5-crews figure on file; not re-confirmed numerically. |
| **SumoQuote** (previously unresearched — the user's own task named it) | **Acquired by JobNimbus, deal closed Dec 20 2023 / announced Jan 29 2024** — it now runs as a standalone-usable product, not a separate company. Markets a direct EagleView integration: order or pull an existing EagleView report from inside SumoQuote, auto-populating a quote's line items in "under 60 seconds" (its own named "Level 3" workflow). Only a "Heavy" plan is sold to new users now; Enterprise is custom/multi-location. No dollar figures found on-domain. | New coverage. |

**The single most important correction this section makes**: SumoQuote is
not an independent competitor to benchmark against JobNimbus — it is a
JobNimbus-owned product with its own aerial-measurement-integration
angle. Any future competitive framing that treats "JobNimbus vs.
SumoQuote" as two separate market participants would be wrong.

### 2.2 Aerial/CV measurement in the market — reported as fact, not a
build recommendation

| Vendor | What's marketed |
|---|---|
| AccuLynx | In-platform ordering of EagleView, Hover, Geospan, and GAF QuickMeasure reports, auto-populating estimates; integration itself free, reports priced separately |
| Roofr | Markets its **own** aerial/satellite/drone measurement tool (not a third-party pass-through) — a claimed 1–2 inch accuracy, $13/report, 2-hour delivery |
| SumoQuote | Markets an EagleView integration specifically, order-in-app plus auto-populated quote line items |
| Leap (lower-confidence, non-vendor-restricted source) | Lists EagleView, Hover, and GAF QuickMeasure among 35+ integrations at no extra platform fee |
| JobNimbus | No aerial-measurement integration surfaced on its own domain this pass — its named integrations were distributor-ordering (Beacon PRO+, SRS), not measurement |
| Hover | Markets itself as an end-to-end "Measure, Design, Estimate" platform, a claimed 285 measurements/property average and 2–5% accuracy, integrating outward into JobNimbus, JobProgress, AccuLynx, and CoreLogic |
| EagleView | Still positions itself as the measurement-of-record layer other CRMs plug into; a 2026 product push branded "EagleView Horizon," described in its own press material as an "agentic geospatial intelligence engine" |

**This is reported strictly as a market observation: aerial/CV
measurement is not only still a headline differentiator, it has broadened
— it is no longer just AccuLynx and JobNimbus bundling EagleView, it is
now something nearly every named vendor markets in some form, either as
an owned build (Roofr) or a pass-through integration (AccuLynx, SumoQuote,
Leap).** This document draws no conclusion from that fact about what
SAIRNroofing should build. The app's own code carries a dated, specific,
cited legal boundary against rendering any facet or slope diagram or
building a scan-rotate-scan pipeline (§1, and the source documents named
at the top of this document) — that boundary is unaffected by how
prominently competitors market the capability, and this pass surfaces
nothing that should reopen it outside a fresh legal review.

### 2.3 Litigation and patent freshness — the highest-value finding in
this pass, genuine movement since the last internal check

The internal analysis (2026-08-26) had EagleView/Pictometry's patents
9,183,538 and 10,648,800 invalidated by PTAB in July 2024, on appeal. That
appeal has now resolved, and one further, previously untracked item
surfaced:

- **Federal Circuit affirmed both PTAB invalidations — decisions issued
  May 22–23, 2026** (CAFC case numbers 24-2321 and 24-2322). The July
  2024 PTAB rulings against Pictometry's footprint-area-estimation patent
  (9,183,538) and its address-to-satellite-image-to-marker-selection
  patent (10,648,800) now stand at the appellate level.
- **New to this pass, not in the existing internal file**: a *different*
  EagleView patent, **US 9,135,737** ("Concurrent display systems and
  methods for aerial roof estimation") — the USPTO Director reversed a
  separate 2024 PTAB invalidation of this patent, reinstating it. This
  runs in the opposite direction from the Roofr appeal: here the patent
  owner won a validity reinstatement via Director-level review rather
  than losing. This is a different patent number than either one already
  tracked in the internal analysis and should be flagged to whoever owns
  that file, not treated as covered by the existing screen.
- **EagleView v. Nearmap**, a separate ongoing dispute, was reported
  settled in May 2026 after the Federal Circuit had affirmed an
  invalidity finding for EagleView in that matter too.
- **Xactware/Verisk's US 9,501,700 — the specific patent SAIRNroofing's
  own design-around is built against — returned no 2025–2026 news in this
  pass.** What did surface is older context worth carrying forward if it
  is not already on file: the 2019 jury verdict against Xactware/Verisk
  ($125M, later reported growing to $375M, with an injunction against
  several Xactware/Geomni products) and a **November 2021 settlement**
  establishing a commercial "strategic alliance" giving Xactware/Verisk
  customers integrated access to EagleView technology — meaning Xactware
  and EagleView are now commercially aligned rather than adversarial.
  **This specific patent's post-2024 prosecution and litigation status is
  a genuine gap in what search surfaced, not a clean bill of health, and
  should be checked directly against USPTO/PACER records rather than
  news search.**
- **EagleView's own financial position**: its owners (Clearlake/Vista)
  were reported in amend-and-extend talks with lenders in March 2025 over
  a roughly $600M term loan maturing August 2025; no bankruptcy filing
  was found. A financially stressed patent enforcer may behave
  differently than a stable one, in either direction.
- **No new patents filed 2024–2026 in aerial roof measurement or
  facet-diagram rendering surfaced beyond what is already named above.**

**Net read, stated carefully**: the core fact already on file — EagleView
weakening at PTAB — is now confirmed at the appellate level, which is
directionally reassuring but not a green light on its own; a different
EagleView patent was simultaneously *reinstated*, and the one patent
SAIRNroofing's design-around is actually built against (Xactware's
9,501,700) has an unconfirmed 2025–2026 status. **None of this changes
the existing design-around's validity as analyzed — no fact here
contradicts the 2026-08-26 screen's finding that SAIRNroofing clears six
of Family A's eight elements and one of Family B's five on independent
grounds — but "no contradiction found" is not the same as "re-cleared,"
and the stated caveat in the original screen (a real patent attorney is
required before launch, unchanged by any amount of further research)
applies exactly as much after this pass as before it.**

### 2.4 Warranty and manufacturer-certification tracking — SAIRNroofing
appears to be ahead of the market, not behind it

| Vendor | Comparable to SAIRNroofing's certification-gated pricing tiers? |
|---|---|
| AccuLynx | **Closest match found**: a contractor must link the email tied to their current GAF Master Elite account inside AccuLynx, or GAF QuickMeasure orders bill at the non-discounted Standard rate instead of Master Elite pricing — a real certification-gated pricing mechanic, not just a document template |
| ServiceTitan | Warranty documents are presentable and e-signable in the field, and a "Roofing Warranty Template" exists — document/contract handling, not a certification-gated pricing or eligibility tier |
| JobNimbus | Pre-built GAF and other manufacturer templates, and marketing content explaining GAF Master Elite / Owens Corning Platinum eligibility — no JobNimbus-side software mechanism found that gates a price or workflow on certification status |
| Roofr | Similar to JobNimbus: content advising buyers to verify contractor certification for warranty coverage, no certification-gated product feature found |
| SumoQuote | Not found in this pass |

**AccuLynx is the only vendor with anything structurally comparable, and
even that is narrower** — one manufacturer, one tier, gating one
integration's pricing, not a general certification-gated-tier system
across manufacturers the way SAIRNroofing's own build (row A1, closed)
does. This is one of the more defensible positive findings in this
document: SAIRNroofing's already-shipped feature reads as ahead of the
market on this specific axis, not merely at parity.

### 2.5 Tile roofing — a real but regionally concentrated gap

No competitor's own domain confirmed a tile-specific line item in this
pass (inconclusive, not a confirmed absence — a logged-in product tour
would be needed to settle it either way). Market-report aggregators
(moderate confidence, not traced to one named primary report) put clay
and concrete tile combined at roughly **5–8% of the US roofing market
nationally**, but concentrated regionally — Florida, California, Arizona,
Texas, and New Mexico, with tile reportedly exceeding **40% of homes** in
parts of Arizona and the Southwest, tied to Mediterranean/Spanish
Colonial architectural convention. **This reads as a real, defensible gap
for a multi-location contractor operating in those specific states, and a
low-priority one nationally** — whether it is worth closing depends on
SAIRNroofing's actual customer geography, which this pass has no
visibility into.

### 2.6 Accounting integration — confirmed as genuine table stakes, not a
soft gap

| Vendor | QuickBooks named on-domain? |
|---|---|
| JobNimbus | Yes — two-way sync (jobs, contacts, estimates, invoices, payments, credit memos), Desktop/Online/Server |
| AccuLynx | Yes — two-way sync, Desktop and Online |
| Roofr | Yes — QuickBooks Online, invoices/payments export, "no double entry" |
| ServiceTitan | Yes — QuickBooks Online + Desktop Premier/Enterprise |
| SumoQuote | Not confirmed either way in this pass |

**Xero was not named by any vendor searched — this market's standard is
QuickBooks specifically, not "accounting software" generically.** Four of
five vendors checked confirm it independently on their own domains, which
is about as strong a table-stakes signal as this series' method produces.
SAIRNroofing's zero-markers accounting gap (§1, row A5) is therefore a
high-confidence, high-priority finding, not a soft one — consistent with
the internal re-derivation's own read that this is "the only one" row
still genuinely open.

### 2.7 The German *Aufmaß* pattern — still not found in the US market

Targeted search for a live field-measurement-correction-flows-into-takeoff
mechanic, attributed to a named US vendor, returned nothing beyond
generic 2026 marketing language about mobile measurement-and-estimate
workflows (AccuLynx). **This should be read as "still not found," not
"confirmed absent"** — a negative search result is weak evidence for a
true absence of a specific UX mechanic that would need a logged-in
product walkthrough to properly rule out, the same caveat §2.5 carries
for tile. Consistent with the original 2026-08-24 finding.

### 2.8 Pricing landscape

Confirmed consistent with this series' general finding for B2B trade
software: **only Roofr publishes real numbers on its own domain**
($13/measurement report, named tier structure). JobNimbus, AccuLynx,
ServiceTitan, and SumoQuote all gate pricing behind a sales contact. Any
figure attributed to those four in this document, or in the 2026-08-24
internal snapshot, is an aggregator estimate and should not be quoted to
a prospect as a real price.

---

## 3. Patent screen — unverified beyond §2.3's litigation-freshness
check, no conclusion drawn

§2.3 above is this document's patent-and-litigation content; it is
placed inside §2 rather than in a separate numbered section because it is
explicitly a *freshness check* on the existing internal screen
(`docs/superpowers/specs/2026-08-26-ip-screen-roofing-delta-and-deadline-engine.md`),
not a new independent screen. No patent page, court opinion, or PTAB
decision was opened directly in this pass — every claim in §2.3 is a
news-outlet or aggregator snippet, one grade below even this series'
normal vendor-snippet standard, since court and patent-office documents
were not accessed at all, directly or via search-indexed snippet of the
primary document itself.

---

## 4. Market signals, 2025–2026 (third-party unless the URL is a named
company's own site; none independently fetched in this pass)

- **Verisk agreed to acquire AccuLynx for $2.35B cash (announced July 30,
  2025), then terminated the deal** on December 29, 2025, after the FTC
  did not complete its review by the December 26, 2025 deadline in the
  agreement. AccuLynx reportedly disputes the termination's validity;
  Verisk says it will defend against that — **unresolved and contested as
  of this pass.** This is arguably the single largest roofing-software
  signal in the whole window, and it directly involves the same company
  (Verisk, owner of Xactware) already central to SAIRNroofing's own
  patent design-around — a business fact worth carrying alongside the
  legal one in §2.3, not a substitute for it.
- **JobNimbus raised $330M** (Sumeru Equity Partners, closed November 13,
  2024; total raised to date roughly $383M across two rounds), alongside
  a new wholesale-distributor partnership with ABC Supply — JobNimbus
  reads as the best-capitalized pure-play roofing-software company right
  now, on top of already owning SumoQuote (§2.1).
- **ServiceTitan went public** (NASDAQ: TTAN, priced December 12, 2024 at
  $71/share, jumped roughly 42% on debut). Its FY2026 10-K reports
  revenue of $961.0M and a net loss of $159.9M, narrowed roughly 56%
  year-over-year — SEC filings are now a real, citable transparency
  source for this one vendor going forward, distinct from every other
  privately-held name in this document.
- **EagleView's financial and legal position is mixed, not simply
  declining**: debt-extension talks with lenders (March 2025, ~$600M term
  loan) alongside a settled Nearmap dispute and a reinstated patent
  (§2.3), plus a 2026 AI-branded product push ("EagleView Horizon").
- **Roofr closed a Series B** led by TCV (January 29, 2025); the amount
  is not disclosed on Roofr's own domain, and two aggregator sources
  conflict on total funding raised ($65.4M vs. $43.9M) — reported as an
  unresolved discrepancy rather than picked one way.

---

## 5. What this means for SAIRNroofing, in priority order

Reading §2 against §1's own internal grounding:

1. **Accounting integration (QuickBooks) is the highest-confidence,
   highest-priority item in this document** (§2.6) — the internal
   re-derivation already identified it as the one genuinely open row from
   the original audit, and this pass confirms it independently as real
   market table stakes across four separate vendors, not a soft or
   optional feature.
2. **The litigation-freshness findings in §2.3 do not reopen the
   measurement design-around, but they do identify two specific
   follow-up items worth routing to whoever owns that file**: the newly
   surfaced EagleView patent (US 9,135,737, reinstated) was not in the
   original screen and should be read against SAIRNroofing's own
   position; and Xactware's US 9,501,700 — the patent the design-around
   is actually built against — has an unconfirmed post-2024 status that
   this pass could not resolve from news search and should be checked
   directly against USPTO/PACER records.
3. **The Verisk/AccuLynx acquisition attempt and its contested
   termination (§4) is a business-relationship signal worth tracking
   alongside the legal one**, precisely because it involves the same
   company whose patent underlies SAIRNroofing's own design-around —
   whether Verisk ultimately owns AccuLynx changes the competitive and
   legal landscape around that patent family in ways this pass cannot
   predict.
4. **Certification-gated warranty tiers are a genuine, evidenced
   strength, not a gap** (§2.4) — this is one of the few findings in this
   series where the app reads as ahead of its named competitors on the
   evidence gathered, not merely at parity with them.
5. **Tile roofing (§2.5) is a real but geography-dependent gap** — worth
   closing if SAIRNroofing's actual customer base skews toward
   Florida/California/Arizona/Texas/New Mexico, and low priority
   otherwise; this pass has no visibility into that customer geography.
6. **The Aufmaß-style live-field-correction pattern (§2.7) remains
   unconfirmed either way** and should not be treated as a settled
   finding in either direction without a deeper, logged-in check of at
   least one major vendor's actual product.

---

## 6. What this document does NOT establish

- **No vendor page, court opinion, or patent document was opened
  directly, at all, in this pass.** Every claim above is a search-engine
  snippet, including the litigation reporting in §2.3.
- **No patent claim was read.** §2.3 is a freshness check on litigation
  news, not a new claims-level screen — the original screen's own stated
  limits (maintenance-fee/assignment status not checked, no file-wrapper
  review) are unchanged by anything found here.
- **No competitor product was used, demoed, or tested.**
- **No pricing figure here should be quoted to a prospect** — most
  vendors named gate pricing behind a sales contact, and the few numbers
  found (Roofr's report price, ALIS-style aggregator estimates elsewhere
  in this series) carry their own caveats stated inline.
- **Xactware/Verisk's US 9,501,700 post-2024 status is explicitly an open
  item, not a researched-and-clear finding** (§2.3) — this is the single
  most important thing in this document not to over-read.
- **This document does not decide whether SAIRNroofing should build any
  of the items in §5**, in what order, at what cost, or (for anything
  touching measurement) whether to revisit the existing legal boundary —
  that is a `sairn-software-architect`, `sairn-decision-gate`, and, for
  anything patent-adjacent, an actual attorney's question, exactly as the
  original 2026-08-24/08-26 documents already state.
- **This document does not, under any framing, recommend building a
  facet/slope diagram renderer or a scan-rotate-scan measurement
  pipeline.** Nothing in §2.2's market findings is evidence that the
  existing patent boundary should move.

---

## 7. Decay

Every fact in this document is a search-index snapshot from 2026-09-25 of
pages and litigation reporting this session could not open, in a market
§4 shows is genuinely volatile — a $2.35B acquisition that collapsed
within six months, a $330M raise, an IPO, and a patent reinstatement all
inside one eighteen-month window. **Do not treat any cell here as current
without re-reading the source**, and treat §2.3 specifically as requiring
a direct USPTO/PACER check, not a re-run of this same search-based method,
before any legal conclusion is drawn from it. The one action this
document asks for, ahead of any competitive or legal finding: run this
pass again from a network that can reach vendor and patent-office domains
— and route §2.3's two open items (the newly surfaced EagleView patent,
and Xactware's unconfirmed post-2024 status) to whoever owns the existing
IP-screen document specifically, since both fall inside that document's
scope, not this one's.
