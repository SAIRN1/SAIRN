# SAIRNvet external competitive-gap audit — pricing, clinical decision support, exotics, telemedicine (2026-09-26)

**Research pass, 2026-09-26. No code, no claims, no tier registers touched —
new file only, under `docs/cloud-research/`, on its own branch, same lane as
the SAIRNlaw/SAIRNvet external audits already in this directory.**

---

## 0. Scope, and a correction to the task brief before anything else

The task brief for this pass stated "no fresh external competitor audit doc
exists for this vertical yet." That is not correct, and per this platform's
own verify-before-report rule it is stated plainly rather than silently
worked around: **`docs/cloud-research/SAIRNvet-external-competitive-gap-audit-2026-09-25.md`
already exists, written the previous day**, covering four angles in real
depth — radiograph AI screening, treatment-to-invoice/charge capture,
client-facing booking, and mid-market multi-location/inventory — each
against real, named PIMS and point-solution vendors (Shepherd, Instinct,
ezyVet, Covetrus Pulse, Provet Cloud, Digitail, Vetstoria, PetDesk, IDEXX
Vello, SignalPET, Vetology, Antech RapidRead, Radimal, and others), plus a
patent screen and 2025–2026 market-signals section.

**This document does not re-derive any of that.** It covers the four angles
the task brief actually asked for that the sibling document did not: PIMS
pricing-model gaps (specifically AVImark and Vetspire, which the sibling
document left unpublished), clinical decision support depth for drug dosing
and interaction checking (SAIRNvet's own stated differentiator, only touched
tangentially in the sibling document's imaging-gap discussion), exotic and
non-standard species coverage across named PIMS and specialist products, and
telemedicine/photo-video-consult feature parity. Where this document's
findings bear on the sibling document's four gaps, it says so and points
there rather than repeating the research.

### 0.1 A network-egress caveat that applies to every section below

As with every research pass run from this environment, outbound `WebFetch`
(full-page retrieval) returned `EGRESS_BLOCKED` for essentially every vendor,
aggregator, and reference domain attempted across all four research angles
behind this document — vendor sites, help centers, Capterra/G2/TrustRadius,
Student Doctor Network, PubMed, and even Wikipedia. This was confirmed
tool-wide, not domain-specific, and not routed around per this environment's
own instructions. Every finding below therefore rests on `WebSearch`'s
indexed **excerpt** of a page, not an independently opened full read — one
grade below the standard this document series holds itself to for exactly
the same reason the 2026-09-25 sibling document states in its own §0.
Confidence flags per claim reflect this. **Nothing pricing-specific,
capability-specific, or legally load-bearing below should be quoted
externally — to a customer, a prospect, or in sales material — without a
follow-up read from a network that can reach these domains.**

---

## 0.2 Internal grounding — what SAIRNvet actually has today

Read directly from the live `sairnvet.html` on `main` (confirmed via `git
log` to be the actively-updated branch for this file — its last touch is
2026-09-25 10:20:34, versus `master`'s last touch of 2026-07-21 — independent
verification rather than trusting either branch's reputation), not from
memory or from the task brief's own description, so the external findings
below are compared against real capability rather than an assumed one.

**Species-aware dose calculator.** The dosing panel's species dropdown lists
24 options: Dog, Cat, Horse, Cattle, Sheep, Goat, Llama/Alpaca, Bird,
Emu/Ratite, Reptile, Chelonian, Tortoise, Turtle, Deer, Rabbit, Guinea Pig,
Ferret, Hamster, Chinchilla, Swine, Poultry, Aquatic/Fish, Amphibian,
Exotic, and Zoo/Wildlife. It is backed by a reference dataset
(`VET_SPECIES_REF`, 59 hits) carrying 121 recorded toxicity/lethality flags,
including explicit refusals to dose certain Schedule II
wildlife-immobilization drugs at all; a dose-safety banner and a **separate**
food-animal-specific banner (`dose-foodsafety-banner`) for
withdrawal-time/residue concerns on cattle/swine/poultry; a "verified
calculation" display; and a required veterinarian sign-off gate
(`dose_signoff`) writing to an audit trail before a calculated dose is
final. The 2026-09-24 internal competitive-gap re-derivation independently
confirmed this as BUILT (not aspirational), and specifically flagged the
**deterministic, model-independent contraindication gate** — the dangerous
-combination check runs as real application logic, not inside an AI call,
and cannot be silently bypassed by an AI suggestion — as something no vendor
-domain snippet gathered in that pass described anywhere else in the market.

**Exotic species support is architecturally first-class, not bolted on.**
Beyond the dose calculator, SAIRNvet has dedicated navigation and patient
-hub panels for Companion Animals, Equine, Large Animals/Herds, **Exotic &
Small Mammals**, Avian, and Reptile & Amphibian, plus separate
aquatic-species and zoo/wildlife patient panels — i.e., exotic and
non-standard species are a structural part of the navigation, not a generic
"other" field on a companion-animal-first product.

**Two different features live under "telemedicine," and they should not be
conflated.** `panel-teleconsult` ("Telemedicine") is the client-facing
feature, and it is currently thin: a "Copy Consult Link" button that
generates a placeholder link for staff to paste into whatever external video
platform the clinic already uses (Zoom, Google Meet, etc.) — the app
explicitly states "This app doesn't host video itself," with no in-app video
or real scheduling integration. **`panel-photoconsult` ("Photo/Video
Consult")** is a separate, real, more developed feature: **internal,
staff-to-staff only** (explicitly not client-facing) — camera capture with a
viewfinder/canvas/preview UI, AI-guided real-time coaching during capture, an
optional AI suggestion on the captured photo/video, and routing to a
colleague on staff for a second opinion, logged as consult notes. It is
explicitly scoped as "Phase 1" — no video-calling infrastructure, scheduling,
or payments — a peer clinical second-opinion tool for staff, not a client
telehealth product.

**Also built and verified in the 2026-09-24 internal audit:** an ambient
scribe with per-visit consent and provenance tracking; a DEA
controlled-substance register with a two-person witness lock on Schedule II
entries and a Dosing Audit Trail panel readable in-product; and per-employee
PIN authentication with a server-side session gate across all synced
resources.

**Real gaps, still open as of the 2026-09-24 re-derivation** (covered in
depth by the 2026-09-25 sibling document, not repeated here): radiograph AI
screening is not built (an imaging-status tracker, not an image reader);
treatment-to-invoice is not wired (a completed procedure does not carry into
an invoice line); client-facing booking does not exist (the "Client
Requests" panel is a staff-entered log, not a client-facing portal); and the
mid-market location/inventory tier is a status board, not an operations
layer (no stock levels, par levels, or reorder path).

**Ongoing panel-by-panel hardening, and a caveat that matters for this
document specifically.** A live internal handoff (Session 62) records 10
panels fixed in that session alone — mostly dropping fabricated/hardcoded
KPIs (invented revenue figures, fake retention percentages, a fabricated
"Genetic Diversity Index") in favor of real, computed values — bringing the
running total to 25 panels hardened across two sessions. **20 panels remain
explicitly listed as not yet audited, and `exotic-patients` is one of
them.** This does not cast doubt on the dose calculator's own real,
independently-verified safety logic described above (a different panel,
already checked), but it does mean the exotic-species **patient-record**
panel's own content has not yet been through the same fabrication sweep the
financial panels just received — worth fixing before this panel's depth is
used in any external-facing claim. `panel-photoconsult`'s and
`panel-teleconsult`'s audit status is not stated one way or the other in the
Session 62 handoff and is not asserted here.

---

## 1. PIMS pricing models — filling the gaps

The 2026-09-25 sibling document already found: ezyVet US "starts at $260.50
per month" (tiered monthly, vendor's own pricing page); Digitail "starts from
$300 per full-time DVM, additional vets $150"; IDEXX Neo priced as
base-plus-per-user-plus-per-location with exact figures not published; and
explicitly no published pricing found for Provet, Shepherd, VIA, Vetspire,
Antech, or Radimal. This pass went back specifically for AVImark, Vetspire,
and Covetrus Pulse, and for anything more specific on IDEXX Neo.

**AVImark** (Covetrus) publishes no pricing; a quote requires contacting the
company. Every source checked agrees the primary model is a **one-time
perpetual license plus annual support**, not a subscription, with no
per-seat fee — consistent with AVImark's long-standing reputation as one of
the oldest still-sold PIMS codebases (Covetrus's own release-note archive
runs back to at least 2010). Covetrus's own product page does now describe
"both cloud-based and on-premise deployment options," so the honest read is
**hybrid, not a clean migration to subscription** — perpetual-license remains
the default, a cloud path now exists alongside it, and nothing found says
which practices get which. A "$7,400 startup package" figure recurs
verbatim across six-plus SEO directory sites, which is itself evidence of one
uncredited, undated number being copied between sites rather than
independent confirmation — **aggregator-sourced, lower confidence, unknown
vintage.** A separate aggregator's "$150–$400/user/month" figure directly
contradicts the no-per-seat-fee claim made everywhere else and is
uncorroborated — not usable as a number. No real practice-owner dollar figure
for AVImark specifically was found on Reddit or elsewhere.

**Vetspire** confirms on its own pricing page that it publishes no numbers.
The recurring third-party estimate is **~$349 per full-time DVM/month**
(varies by size/features/contract) — **aggregator-sourced, lower
confidence**, never appearing on Vetspire's own site. One real, named
-practice review (via the Veterinary Hospital Managers Association's member
review platform, a roughly two-year Vetspire user) gives a concrete add-on
figure: Vetspire raised per-text SMS pricing from $0.03/text to $0.10/text —
a genuine data point, but an add-on, not the base plan. **Covetrus Pulse**
pricing is likewise unpublished across every aggregator checked, but real
customer reviews on Capterra surface two genuine billing complaints worth
noting as market color (not resolved further here): one practice quoted
$240/month and billed $276/month with no explanation given after repeated
follow-up, and another reporting a 3-year contracted price lock not honored
past year one.

**IDEXX Neo** has its own pricing page (`software.idexx.com/products/neo/pricing`)
whose existence suggests it may publish more than "contact us," but its
content could not be independently confirmed this pass (fetch blocked).
Aggregators agree on structure — a base tier covering 3 users, then
per-user and per-location adders — but disagree on the actual numbers by
6–14%, which is itself evidence of independent scraping rather than one
verified price (one aggregator: $290/mo base, $19/mo per user, $145/mo per
location, $2,375 one-time setup; another: $273/mo base, $18/mo per user,
$125/mo per location). One aggregator estimates 10+-staff practices should
expect "$1,000+/month," roughly consistent with the per-user math.

**Market context.** Single-doctor starting prices across every vendor found
in this pass and the sibling one cluster mostly at **$100–$350/month**
(Hippo Manager $119/mo, DaySmart Vet from $116/mo, ezyVet quoted variously as
$245/$260.50/$299/month across different aggregator snapshots — a 20%+
spread for the *same* vendor, a caution against trusting any single scraped
"starting price" — Shepherd and Digitail both roughly $299–300/mo/doctor).
Notably, the evidence found here runs opposite the usual SaaS
discount-from-list pattern: AVImark, Vetspire, and Pulse withhold a public
list price entirely — there is nothing to discount *from* — and the two
concrete real-billing data points found (Pulse's $240-quoted/$276-billed
mismatch, its unhonored 3-year lock) show a *negotiated* number failing to
hold, which is a different and arguably more relevant risk for a prospective
customer evaluating trust in a vendor's pricing than a list-price comparison
would be.

### Sources (§1)

1. Costbench — "AVImark Pricing 2026: 2 Plans from $150–$400/user/mo" —
   https://costbench.com/software/veterinary-software/avimark/ — accessed
   2026-09-26 — aggregator-sourced, lower confidence, contradicted elsewhere.
2. VetSoftwareHub — "Avimark pricing, plans, and costs" —
   https://www.vetsoftwarehub.com/product/avimark/pricing — accessed
   2026-09-26 — aggregator-sourced, lower confidence.
3. VetSoftwareHub — "What Is Avimark? A Plain-Language Guide (2026)" —
   https://www.vetsoftwarehub.com/article/what-is-avimark-a-plain-language-guide-2026
   — accessed 2026-09-26 — aggregator-sourced; source of the "perpetual +
   support" classification.
4. SaaSCounter — "AVImark Pricing, Features & More 2026" —
   https://www.saascounter.com/products/avimark — accessed 2026-09-26 —
   aggregator-sourced; repeats the $7,400 startup-package figure verbatim.
5. Capterra — Covetrus AVImark — https://www.capterra.com/p/92887/AVImark/ —
   accessed 2026-09-26 — aggregator-sourced.
6. Covetrus — AVImark product page —
   https://covetrus.com/covetrus-platform/workflow-and-productivity-tools/avimark/
   — accessed 2026-09-26 — vendor-sourced; snippet only, fetch blocked.
7. Covetrus — "Adding It Up: Total Cost of Ownership for Veterinary
   Software" — https://covetrus.com/insights/adding-it-up-total-cost-of-ownership-for-veterinary-software/
   — accessed 2026-09-26 — vendor-sourced, self-interested framing; snippet
   only.
8. Vetspire — pricing page — https://vetspire.com/pricing — accessed
   2026-09-26 — vendor-sourced (primary); confirms no numeric pricing is
   published.
9. VetSoftwareHub — "Vetspire pricing, plans, and costs" —
   https://www.vetsoftwarehub.com/product/vetspire/pricing — accessed
   2026-09-26 — aggregator-sourced; source of the ~$349/DVM/month estimate.
10. VHMA Product & Service Reviews — "We've been using Vetspire for almost 2
    years now" — https://reviews.vhma.org/operations/vetspire/reviews/429 —
    accessed 2026-09-26 — real practice-owner review; source of the
    $0.03→$0.10/text figure.
11. Capterra — Covetrus Pulse reviews —
    https://www.capterra.com/p/130107/Covetrus-Pulse/reviews/ — accessed
    2026-09-26 — real customer reviews (hosted on an aggregator); source of
    the $240-quoted/$276-billed and unhonored 3-year lock claims; reviewer
    identity/date not resolvable from the search snippet alone.
12. TrustRadius — Covetrus Pulse Pricing —
    https://www.trustradius.com/products/covetrus-pulse/pricing — accessed
    2026-09-26 — aggregator-sourced; confirms pricing unpublished.
13. G2 — Covetrus Pulse Pricing —
    https://www.g2.com/products/covetrus-pulse/pricing — accessed
    2026-09-26 — aggregator-sourced; confirms pricing unpublished.
14. IDEXX — "Neo Veterinary Software Plans and Pricing" —
    https://software.idexx.com/products/neo/pricing — accessed 2026-09-26 —
    vendor page confirmed to exist via search-result title only; content not
    independently verified (fetch blocked).
15. ITQlick — "IDEXX Neo Pricing 2026: Hidden Costs & Total ROI" —
    https://www.itqlick.com/idexx-neo/pricing — accessed 2026-09-26 —
    aggregator-sourced, lower confidence; source of the "$1,000+/month at
    10+ staff" estimate.
16. Capterra — "IDEXX Neo Pricing 2026" —
    https://www.capterra.com/p/145988/IDEXX-Neo/pricing/ — accessed
    2026-09-26 — aggregator-sourced, lower confidence; disagrees with source
    15 by 6–14%.
17. Student Doctor Network Forums — "Veterinary Clinic Software" thread —
    https://forums.studentdoctor.net/threads/veterinary-clinic-software.1375171/
    — accessed 2026-09-26 — real practitioner forum; fetch blocked, so a
    "$5,000/month at ~$2M revenue" figure attributed to it by search-engine
    synthesis is unconfirmed/indicative only.

**Gaps that remain genuinely unfilled:** no independently-verified current
AVImark or Covetrus Pulse base price in dollars; no real-practitioner dollar
figure for IDEXX Neo from Reddit or Student Doctor Network (none was
findable in searchable form, not merely unfound); IDEXX's own Neo
pricing-page content is unconfirmed due to the egress block, not because it
does not exist.

---

## 2. Clinical decision support depth — drug dosing and interaction checking

This is the most important section in this pass, since it is the angle
closest to SAIRNvet's own stated differentiator.

**Platform by platform, none was found to own a from-scratch dosing or
interaction dataset comparable to SAIRNvet's `VET_SPECIES_REF`.**

- **ezyVet**: no native drug-drug interaction checker or licensed formulary.
  Dosage/"safe range" data is manually typed in per-practice, per-drug.
  Actual dose calculation and range-warning display happen in **Vet Radar**,
  a companion inpatient-whiteboard product ezyVet's own site frames as an
  integration rather than a built-in module. A warning on an out-of-range
  dose rate is soft/informational, using whatever range that practice typed
  in — not a pre-populated toxicity dataset. No interaction logic or
  exotic-species content found.
- **Covetrus Pulse**: the strongest native showing of the five — ships
  native "smart" and CRI (constant-rate-infusion) calculators, and
  separately integrates **Veterinary Pharmacy Reference Cloud (VPR Cloud)**
  for a full formulary plus a drug-interaction checker that alerts on
  interactions.
- **AVImark**: Covetrus's own marketing foregrounds scheduling, EMR/SOAP,
  and prescription/inventory management. The specific claim that AVImark
  itself contains "a comprehensive drug formulary with... interactions and
  contraindications" traces only to a third-party review site, not to
  Covetrus's own copy in the results retrieved — **lower confidence,
  unconfirmed at vendor-primary standard.**
- **IDEXX Neo**: documented native feature set is prescription
  creation/editing/voiding and label printing — prescription *management*,
  not dose calculation or interaction checking. VPR is listed as an
  available Neo integration, but the deep VPR feature set (a species/weight
  calculator with a feline-specific toggle, a species-selectable
  antiparasitic matrix, an interaction matrix) is documented for **IDEXX
  Cornerstone** (the older, sibling on-premise PIMS) specifically, not
  confirmed at the same depth for Neo.
- **Vetspire**: no native interaction-checker or formulary surfaced in its
  own user manual or API docs (the API's "Medication" object carries no
  documented interaction logic). A third-party product, **VetScript**,
  advertises interaction screening and dose-range validation as a layer
  sitting on top of Vetspire (and ezyVet, Cornerstone, and AVImark) rather
  than inside any of them. Of the five, Vetspire shows the least evidence of
  native clinical decision-support logic of its own.

**The real competitive benchmark is not the PIMS layer at all — it is three
named, licensed third-party formulary products.** Every real dosing or
interaction capability found across this market traces to one of:

1. **Veterinary Pharmacy Reference (VPR / VPR Cloud)** — the formulary
   inside Cornerstone, offered as a Neo add-on, and the product Covetrus
   Pulse calls "VPR Cloud." Documented features: drug search, a
   species/weight calculator with a feline-specific carve-out, a
   species-selectable antiparasitic chart, and an interaction matrix
   requiring manual setup. No source described VPR's content reaching
   reptile, avian, or wildlife species — only a feline/canine split was
   documented.
2. **Plumb's Veterinary Drugs** — the long-standing Plumb's Veterinary Drug
   Handbook, now owned by Instinct Science after its January 2024
   acquisition of VetMedux. Plumb's has a dedicated interaction checker
   covering "more than 25,000 interactions" on a five-tier severity scale.
   **Critically, Plumb's own help center states the interaction checker
   itself is centered on dogs and cats**, including other species only "when
   relevant" primary research exists — narrower than Plumb's broader
   monograph library, which does cover horses/donkeys, cattle, sheep/goats,
   camelids, pigs, birds, ferrets, rabbits, small mammals, and reptiles at
   the reference-text level.
3. **FDB Vela / FDB Pet MedKnowledge** (First Databank) — a newer entrant
   (opened to veterinary medicine March 2022) from the company behind much
   of U.S. human-medicine e-prescribing/interaction infrastructure. Its
   underlying veterinary drug database is described on FDB's own page as
   covering **"dogs, cats and horses"** — three species. FDB's own white
   paper on the veterinary market states industry-wide, drug-interaction
   checks "serve a watchdog function only" and that "[n]either PIMS nor
   PSAOs have these capabilities today" — a self-interested claim (FDB sells
   into that gap) but directionally corroborating everything found above.

**Cross-cutting finding, and the sharpest available benchmark for
SAIRNvet's own claim:** every interaction-checking capability found across
this entire research pass — VPR's matrix, Plumb's checker, FDB's decision
support — is described as an alert or flag a veterinarian reviews, **never
as a mechanism that blocks completion of a prescription.** No source
describes a hard, application-level, model-independent gate comparable to
SAIRNvet's `dose_signoff`-gated, contraindication-refusing calculator. And
exotic-species coverage is the thinnest point industry-wide **even at the
licensed-reference layer**: Plumb's own interaction checker is
documented as dog/cat-centered, and FDB's veterinary database — from a major
cross-industry drug-data vendor — stops at dogs, cats, and horses. Nothing
found in this pass extends species-specific interaction or toxicity-flag
data to reptiles, chelonians, or zoo/wildlife, or addresses Schedule II
wildlife-immobilization drugs specifically, at either the PIMS or the
licensed-formulary layer.

**This cuts both ways, and the second half matters as much as the first.**
SAIRNvet's dose calculator claiming toxicity/lethality flags across 24
species including the exotic tail (chelonian, tortoise, rabbit, guinea pig,
hamster, chinchilla, amphibian, zoo/wildlife) is, on this evidence, going
further than any established industry reference — which is a genuine,
real differentiator. But it also means there is **no authoritative
third-party source to validate that exotic-species reference data against**:
where Plumb's or FDB's dog/cat/horse data can be checked against a
25,000-interaction, professionally maintained dataset, SAIRNvet's own
exotic-species entries currently cannot be cross-checked against any
comparable industry benchmark. That is a real risk worth carrying forward
internally, not just a marketing point — see §5.

*(Correction to the original research brief for this pass: "VIN's
SafetyNet" was searched for specifically and does not appear to exist under
that name. VIN's actual, verifiable named drug-reference product is the VIN
Veterinary Drug Handbook, a reference app — not a PIMS-integrated
interaction-checking service. Treat "SafetyNet" as unconfirmed.)*

### Comparison table

| Platform | Native calculator/formulary? | Interaction checking? | Mechanism | Exotic-species evidence |
|---|---|---|---|---|
| ezyVet | No; per-drug "safe range" manually typed, via companion product Vet Radar | Not found | Soft warning, practice-defined range | None found |
| Covetrus Pulse | Native smart/CRI calculators; full formulary via VPR Cloud | Yes, via VPR Cloud | Alert (advisory) | Not documented beyond feline/canine split |
| AVImark | Formulary claimed — third-party source only | Claimed by third party; unconfirmed on Covetrus's own copy | Unclear/unverified | Not documented |
| IDEXX Neo | No confirmed native formulary; VPR offered as add-on | Via VPR (documented for sibling Cornerstone, not confirmed at same depth for Neo) | Alert/matrix, manually mapped to invoice items | Not documented |
| Vetspire | None found natively | None native; via third-party VetScript/vRxPro layered on top | Alert/screening outside the PIMS itself | Not documented |
| Plumb's (reference layer) | Formulary + calculator | Yes — 25,000+ interactions, 5-tier severity | Advisory, vet-reviewed | Broad monographs; interaction checker itself dog/cat-centered |
| FDB Vela/Pet MedKnowledge (reference layer) | Formulary + e-prescribing network | Yes | Advisory, explicitly overridable per FDB's own white paper | Dogs, cats, horses only |
| **SAIRNvet (internal, for reference)** | Native, 24-species calculator | Deterministic contraindication gate + 121 toxicity/lethality flags | **Hard, model-independent gate; vet sign-off required** | Broadest species list found in this pass, unvalidated against any external reference |

### Sources (§2)

1. ezyVet Knowledge Center — "Configuration of a product's dosage
   properties" —
   https://docs.ezyvet.com/en/browse-documentation/ezyvet/products/product-configuration/product-configuration-for-medications/configuration-of-a-products-dosage-properties
   — accessed 2026-09-26 — vendor-primary, snippet only.
2. ezyVet Knowledge Center — "Medications" —
   https://docs.ezyvet.com/en/browse-documentation/ezyvet/veterinary-care/medications
   — accessed 2026-09-26 — vendor-primary, snippet only.
3. ezyVet — "Vet Radar" integration page —
   https://www.ezyvet.com/integration/vet-radar — accessed 2026-09-26 —
   vendor-primary, snippet only.
4. ezyVet Knowledge Center — "About Vet Radar" —
   https://docs.ezyvet.com/en/browse-documentation/vet-radar/getting-started/about-vet-radar
   — accessed 2026-09-26 — vendor-primary, snippet only.
5. ezyVet Knowledge Center — "Medication safe ranges" —
   https://docs.ezyvet.com/en/browse-documentation/vet-radar/reference-information/medication-safe-ranges
   — accessed 2026-09-26 — vendor-primary, snippet only.
6. ezyVet partner directory (Online Pharmacy / Reference Labs / Patient
   Care) — https://www.ezyvet.com/partners/all-countries/all-categories/p2 —
   accessed 2026-09-26 — vendor-primary, snippet only; absence-of-evidence,
   not exhaustive.
7. Covetrus — "Covetrus Pulse" product page —
   https://covetrus.com/covetrus-platform/workflow-and-productivity-tools/covetrus-pulse/
   — accessed 2026-09-26 — vendor-primary, snippet only.
8. Covetrus Pulse Help — "Veterinary Pharmacy Reference (VPR) Cloud
   Integration" —
   https://cvet.my.site.com/pulse/s/article/218746537-Veterinary-Pharmacy-Reference-VPR-Cloud-Integration
   — accessed 2026-09-26 — vendor-primary help article, snippet only.
9. Covetrus — "AVImark" product page —
   https://covetrus.com/covetrus-platform/workflow-and-productivity-tools/avimark/
   — accessed 2026-09-26 — vendor-primary, snippet only.
10. TradeTechGuide — "AVImark software review for Veterinarians" —
    https://tradetechguide.com/p/avimark-software-review-for-veterinarians —
    accessed 2026-09-26 — third-party review blog, lower confidence, not
    independently corroborated.
11. Covetrus — AVImark version 2010.5.0 / 2016.1.1 release notes —
    https://software.covetrus.com/wp-content/uploads/dlm_uploads/2021/03/AVImark-version-2010.5.0-release-notes.pdf
    — accessed 2026-09-26 — vendor-primary, confirms product longevity only.
12. IDEXX Software — "Neo Software Integrations" —
    https://software.idexx.com/neo-integrations — accessed 2026-09-26 —
    vendor-primary, snippet only.
13. IDEXX Software — "Veterinary Pharmacy Reference (VPR)" —
    https://software.idexx.com/integration/veterinary-pharmacy-reference-vpr
    — accessed 2026-09-26 — vendor-primary, snippet only.
14. IDEXX Neo Support — "Create a prescription" —
    https://idexxneosupport.zendesk.com/hc/en-us/articles/115005412428-Create-a-prescription
    — accessed 2026-09-26 — vendor-primary support doc, snippet only.
15. Cornerstone Help Hub — "Using Veterinary Pharmacy Reference" —
    https://cornerstonehelphub.com/docs/using-veterinary-pharmacy-reference/
    — accessed 2026-09-26 — vendor-primary, snippet only; describes
    Cornerstone, not confirmed identical for Neo.
16. Vetspire Developer Docs — "Medication" object —
    https://developer.vetspire.com/object/Medication/ — accessed 2026-09-26
    — vendor-primary, snippet only.
17. Vetspire User Manual — "Covetrus (vRxPro)" —
    https://manual.vetspire.com/vetspire-user-manual/ok/Commercial/covetrus-vrxpro
    — accessed 2026-09-26 — vendor-primary, snippet only.
18. urSynergy — "VetScript — Veterinary Prescription Origination" —
    https://vetscript.net/ — accessed 2026-09-26 — vendor-primary
    (third-party product to the PIMS), snippet only.
19. VPR Cloud — https://vprcloud.com/tools/ — accessed 2026-09-26 —
    vendor-primary, snippet only.
20. GlobeNewswire — "Instinct Science Acquires VetMedux, Owner of... Plumb's
    Veterinary Drugs" (Jan. 2024) —
    https://www.globenewswire.com/news-release/2024/01/29/2818776/0/en/Leading-Veterinary-Software-Company-Instinct-Science-Acquires-VetMedux-Owner-of-Fast-Growing-Clinician-s-Brief-and-Plumb-s-Veterinary-Drugs.html
    — accessed 2026-09-26 — press release, high confidence for the
    acquisition fact.
21. Plumb's — "Our Story" — https://plumbs.com/about/our-story/ — accessed
    2026-09-26 — vendor-primary, snippet only.
22. Plumb's — "Check for Drug Interactions in Animal Patients" —
    https://plumbs.com/features/drug-interaction-checker/ — accessed
    2026-09-26 — vendor-primary, snippet only.
23. Plumb's — "3 Benefits of a Veterinary-Specific Drug Interaction Checker"
    — https://plumbs.com/blog/reasons-veterinary-drug-checker/ — accessed
    2026-09-26 — vendor-primary blog, snippet only.
24. Plumb's Help Center — "What species does the drug interaction checker
    cover?" —
    https://help.plumbs.com/en/articles/10572259-what-species-does-the-drug-interaction-checker-cover
    — accessed 2026-09-26 — vendor-primary help doc, snippet only — key
    source for the dog/cat-centered finding.
25. Plumb's — "Drug Information" — https://plumbs.com/why-plumbs/drug-information/
    — accessed 2026-09-26 — vendor-primary, snippet only.
26. FDB (First Databank) — "FDB Announces that New FDB Vela ePrescribing
    Network is Open to the Veterinary Industry" (Mar. 2022) —
    https://www.fdbhealth.com/about-us/press-releases/2022-03-22-fdb-announces-that-new-fdb-vela-eprescribing-network-is-open-to-the-veterinary-industry
    — accessed 2026-09-26 — vendor press release.
27. FDB — "Veterinary ePrescribing" —
    https://www.fdbhealth.com/applications/veterinary-eprescribing —
    accessed 2026-09-26 — vendor-primary, snippet only.
28. FDB — "Veterinary Drug Database | FDB Pet Meds" —
    https://www.fdbhealth.com/solutions/pet-medknowledge-veterinary-drug-database
    — accessed 2026-09-26 — vendor-primary, snippet only — key source for
    the "dogs, cats and horses" limitation.
29. FDB — "A problem unleashed" (FDB Vela veterinary white paper) —
    https://www.fdbhealth.com/-/media/documents/form-not-required/us/white-papers/fdb-vela-veterinary-white-paper.ashx
    — accessed 2026-09-26 — vendor white paper, self-interested framing,
    flagged accordingly.
30. USPTO — veterinary medication monitoring system patent filing
    (background section) —
    https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6397190
    — accessed 2026-09-26 — government-hosted document; describes prior art
    generally, exact authorship/date context not independently confirmed
    beyond the PDF.
31. Apple App Store — "VIN Veterinary Drug Handbook" —
    https://apps.apple.com/us/app/vin-veterinary-drug-handbook/id1668332990
    — accessed 2026-09-26 — used only to confirm VIN's actual named product
    differs from "SafetyNet."

---

## 3. Exotic and non-standard species coverage

**Mainstream PIMS platforms** (ezyVet, Covetrus AVImark, Covetrus Pulse,
IDEXX Neo, IDEXX Cornerstone, Vetspire, Shepherd, Provet Cloud, Digitail,
ImproMed) all use a single, admin-configurable "species" field or tag applied
to one generic patient-record type, not distinct per-species navigational
hubs. ezyVet's own documentation describes adding a species as typing a name
into a flat list under Admin > Patients > Species. Real exotics-only
practices do run on general PIMS — ezyVet has named customer case studies of
exotics-only practices (one migrating off DVMAX after 15 years) using
species-specific SOAP templates tied to billing triggers, which is
templating within one generic record architecture, not a separate hub
structure. IDEXX Neo's own support docs describe the same flat-list
pattern with deduplication tooling for species/breed entries. AVImark is
characterized by third-party reviews as best suited to established
small-animal general practice, with no exotic/zoo-specific features found.
**Vetspire is the strongest counter-evidence** among the mainstream PIMS: its
own support documentation lists a notably broad species set (amphibian,
arachnid, avian, bovine, camelid, canine, caprine, guinea pig, cervidae,
cetacea, and more) and its marketing describes a specialty iPad app suite for
point-of-care charting — though this could not be verified beyond the search
snippet, and nothing found describes it as separate navigational hubs rather
than an extended list plus exam-type apps. Shepherd explicitly markets to
exotic practices and partners with labs accepting avian/reptile/exotic
samples. Provet Cloud, ImproMed, and Cornerstone showed no exotic/zoo
-specific evidence despite direct searching. Digitail has at least one real,
named all-exotics adopter (a Charleston, SC exotics hospital, per the
practice's own blog) with species-configurable wellness plans, but no
documented dedicated exotic module.

**Net finding for the mainstream-PIMS layer:** no product surveyed shows
public evidence of dedicated per-species-group navigational hubs; all use
variants of a generic, extensible species field. SAIRNvet's architecture —
separate hubs for Companion, Equine, Large Animals, Exotic & Small Mammals,
Avian, Reptile & Amphibian, plus dedicated aquatic and zoo/wildlife
panels — was not matched by any general PIMS checked.

**This should not be read as "no one else serves these species" — real,
more developed specialist competitors exist outside the general-PIMS
category.** **Species360's ZIMS** is a mature, well-resourced, long
-established system (1,400+ institutions, 100+ countries); "ZIMS for
Medical" is a genuine veterinary medical-records module with
anesthesia/treatment/diagnostic records, species-specific physiologic
reference and drug-dosage/risk data for "thousands of wildlife species," and
a shared Global Medical Resources library. It is a serious, credible, named
competitor — but scoped to institutional zoos, aquariums, sanctuaries, and
rescue centers, not general private clinical practice, and any claim
SAIRNvet makes about exotic-species depth should explicitly avoid implying
competitiveness with ZIMS's population-management/studbook depth at the
institutional-zoo tier. Wildlife rehabilitation has its own real, named
tools — **WRMD** (free, hosted, 2,000+ organizations, 5,000+ users, 45+
countries) and **RAVEN** (International Wildlife Rehabilitation Council) —
oriented to case tracking and permitting-agency reporting rather than full
clinical/billing PIMS. Aquarium/collection management is served by **Tracks
Software** and **ZIMS for Aquatics**, again institutional and
population/husbandry-focused. No broadly-adopted, named, full clinical PIMS
built specifically for *private* exotic-animal veterinary practices turned
up; such practices instead run on general PIMS, per above.

**On the reference/formulary side** (relevant alongside §2): Carpenter's
*Exotic Animal Formulary* (Elsevier) is the closest thing to an industry
-standard reference and has a digital edition, but remains a searchable text,
not an interactive, patient-linked dosing engine. No dosing-software position
or product was found from the Association of Exotic Mammal Veterinarians,
the Association of Avian Veterinarians, or the Association of Reptilian and
Amphibian Veterinarians — these bodies publish care sheets, journals, and
member reference pages, not formulary software. Independent digital
references exist outside the associations (Vetstream's Vetlexicon "Exotis"
module, VIN's member-gated exotic/reptile formulary pages, Plumb's — see
§2) but are reference lookups, not embedded calculators. Most substantively,
a **peer-reviewed 2022 JAVMA survey of 936 exotic-treating veterinarians**
found formularies are the dominant dosing source (72.9% of respondents),
while 43.5% sometimes or never verify the cited source behind a dosage; a
companion 2022 JSAP paper independently found gaps between a formulary's
stated exotic-mammal dosages and the sources actually cited for them. This
documents a real, peer-reviewed, unmet clinical need around verified,
individualized exotic-species dosing — directly relevant context for a dose
-calculator feature, though it is evidence of a market gap, not an
endorsement of any specific software.

**Overall assessment, stated as evenly as the evidence supports:** native,
multi-hub exotic/zoo/wildlife/aquatic coverage built into one general
-purpose PIMS looks like a genuine, comparatively rare combination among the
specific mainstream competitors checked. This is a real differentiator
claim, not an overstated one — but it is narrower than "nobody else serves
these species": Species360's ZIMS is a mature specialist competitor at the
institutional tier, and Vetspire shows at least one mainstream PIMS actively
investing in species breadth. The defensible claim is specifically about
architecture (separately-designed hubs vs. one shared species field) among
general-purpose PIMS serving private practices, not about being the only
software that touches exotic medicine at all.

### Sources (§3)

1. ezyVet Knowledge Center — "Add a new species to an ezyVet site" —
   https://docs.ezyvet.com/en/browse-documentation/ezyvet/patients/species-configuration/add-a-new-species-to-an-ezyvet-site
   — accessed 2026-09-26 — vendor-primary, snippet only.
2. ezyVet Knowledge Center — "Species configuration" —
   https://docs.ezyvet.com/en/browse-documentation/ezyvet/patients/species-configuration
   — accessed 2026-09-26 — vendor-primary, snippet only.
3. ezyVet customer story — "multi-site exotics-only veterinary practice" —
   https://www.ezyvet.com/customer-stories/upv — accessed 2026-09-26 —
   vendor case study, lower confidence.
4. ezyVet customer story — "Exotics practice transitions to ezyVet after 15
   years on DVMAX" —
   https://www.ezyvet.com/customer-stories/exotics-practice-transitions-to-ezyvet-after-15-years-on-dvmax
   — accessed 2026-09-26 — vendor case study, lower confidence.
5. Software Advice — AVImark profile —
   https://www.softwareadvice.com/veterinary/avimark-profile/ — accessed
   2026-09-26 — third-party review aggregator.
6. IDEXX Neo Support — "Manage patient species, breeds, and sexes" —
   https://idexxneosupport.zendesk.com/hc/en-us/articles/1500008669381-Manage-patient-species-breeds-and-sexes
   — accessed 2026-09-26 — vendor-primary, snippet only.
7. Vetspire Support — "List of Species in Vetspire" —
   https://support.vetspire.com/support/solutions/articles/70000635026-list-of-species-in-vetspire
   — accessed 2026-09-26 — vendor-primary, snippet only, full list
   unverified.
8. Vetspire — "Unrivaled Veterinary Software Features" —
   https://www.vetspire.ai/features/all — accessed 2026-09-26 — vendor
   marketing; specialty-app functions not independently confirmed.
9. Shepherd Veterinary Software — homepage/features — https://www.shepherd.vet/
   ; https://www.shepherd.vet/features/ — accessed 2026-09-26 — vendor
   marketing.
10. Shepherd — Laboratories page —
    https://www.shepherd.vet/category/laboratories/ — accessed 2026-09-26 —
    vendor page re: avian/reptile/exotic lab sample support.
11. Digitail adopter blog — "Exotic Vet Care is Going DigiTail!" —
    https://birdsandexotics.com/blog/exotic-vet-care-is-going-digitail/ —
    accessed 2026-09-26 — customer-authored, names a real adopting hospital,
    moderate confidence.
12. Species360 — "Wildlife Management Software for Zoos & Aquariums" —
    https://species360.org/wildlife-management-software/ — accessed
    2026-09-26 — nonprofit consortium's own site, widely corroborated
    elsewhere, moderate-high confidence.
13. Species360 — "ZIMS for Medical" — https://species360.org/zims-for-medical/
    — accessed 2026-09-26 — moderate-high confidence.
14. Species360 — "ZIMS for Aquatics" — https://species360.org/zims-for-aquatics/
    — accessed 2026-09-26.
15. Wildlife Rehabilitation MD (WRMD) — About — https://wrmd.org/about —
    accessed 2026-09-26 — nonprofit/vendor site.
16. International Wildlife Rehabilitation Council — RAVEN —
    https://theiwrc.org/product/raven/ — accessed 2026-09-26 — association
    product page.
17. Tracks Software — https://trackssoftware.com/ — accessed 2026-09-26 —
    vendor site.
18. Elsevier — Carpenter's Exotic Animal Formulary product page —
    https://www.us.elsevierhealth.com/carpenters-exotic-animal-formulary-9780323833929.html
    — accessed 2026-09-26 — publisher page, high confidence on content
    description.
19. AEMV — Membership Information — https://aemv.org/membership-information/
    — accessed 2026-09-26 — association site via snippet; "coming soon"
    formulary language may reflect a stale cached snapshot, flagged
    low-confidence on currency.
20. AAV — Position Statements — https://www.aav.org/page/positionstatements
    — accessed 2026-09-26 — page existence confirmed only, content not
    independently verified.
21. ARAV — https://arav.org/ ; https://arav.org/for-owners/ — accessed
    2026-09-26 — association site; no formulary product found.
22. VIN — "Reptile Formulary" —
    https://www.vin.com/apputil/content/defaultadv1.aspx?id=3843985 —
    accessed 2026-09-26 — member-gated resource, snippet only.
23. VIN THIS WEEK archive — "VIN Formulary for Exotic Animals" —
    https://www.vin.com/vtw/archives/tw011916.htm — accessed 2026-09-26 —
    dated 2016 launch announcement, not current-state evidence.
24. VetClick — "Exotis Added to Vetlexicon" —
    https://www.vetclick.com/news/exotis-added-to-vetlexicon-p4598.php —
    accessed 2026-09-26 — trade press, moderate confidence.
25. Wiley — Plumb's Veterinary Drug Handbook 10th ed. product page —
    https://www.wiley.com/en-us/Plumb%27s+Veterinary+Drug+Handbook,+10th+Edition-p-9781394172207
    — accessed 2026-09-26 — publisher page.
26. PubMed — Golden et al., "Most veterinarians treating exotic animals use
    formularies to select drug dosages without consistently checking their
    sources" (JAVMA, 2022) — https://pubmed.ncbi.nlm.nih.gov/35201996/ —
    accessed 2026-09-26 — peer-reviewed, read via search-tool summary,
    moderate-high confidence.
27. PubMed — "Evaluation of sources cited by an exotic animal formulary for
    supporting drug dosages and reference intervals in mammals" (JSAP, 2022)
    — https://pubmed.ncbi.nlm.nih.gov/35843599/ — accessed 2026-09-26 —
    peer-reviewed, existence/title confirmed via search, moderate
    confidence.
28. ExoHub — "ExoCalc — Free Avian & Exotic Clinical Calculator" —
    https://calc.avianexotics.vet/ — accessed 2026-09-26 — snippet only, low
    -moderate confidence; a calculator, not a PIMS.
29. co.vet — "Custom SOAP Notes for Exotic Pets" — https://co.vet/exotics/ —
    accessed 2026-09-26 — vendor marketing for an AI-scribe add-on, not a
    PIMS, snippet only.
30. Market.us — "Veterinary Software Market Size, Growth" —
    https://market.us/report/veterinary-software-market/ — accessed
    2026-09-26 — commercial market report, single-source, not independently
    cross-checked.

---

## 4. Telemedicine and photo/video consult parity

**Client-facing telemedicine: almost nobody at the PIMS layer hosts its own
video.** Across every major PIMS checked, none appears to have built and
self-hosts its own video-calling infrastructure — each embeds Zoom directly
or resells a dedicated third-party telehealth vendor, with the "telemedicine
feature" really a scheduling/write-back layer on top of someone else's
video. **ezyVet** integrates directly with Zoom (a Zoom account is
required); virtual appointments launch from the ezyVet calendar with
recordings/transcripts writing back into the clinical record — deeper than a
bare link, but the video itself is Zoom's, not ezyVet's. ezyVet also offers
an alternate integration with **Otto** (formerly branded TeleVet). **IDEXX
Neo/Vello** has no native video; Vello is a scheduling/engagement layer, and
real video consults require bolting on TeleVet/Otto separately. **Vetspire**
integrates with a third-party portal, **TeleTails**, for video visits —
scheduled in Vetspire, with the client receiving a TeleTails link by text —
**structurally identical to SAIRNvet's current teleconsult placeholder.**
**AVImark** has no single native video mechanism, separately layering
Covetrus Comms, Otto, or Vetstoria depending on what the practice buys. The
products that DO appear to host video natively are standalone,
direct-to-consumer telehealth vendors, not PIMS platforms: **Airvet** (native
on-demand/membership video inside its own app) and **Vetster** (a telehealth
marketplace handling booking, payment, and video together).

**This is worth stating plainly rather than dressing up as a SAIRNvet
weakness relative to competitors: SAIRNvet's thin link-generation panel sits
at the common end of an existing spectrum, not an outlier.** Vetspire +
TeleTails is structurally the same pattern. What the more built-out
competitors add is not self-hosted video (almost none of the PIMS players
have that either) but deeper calendar/record integration around a
third-party video call, which is a real, buildable gap if SAIRNvet wants to
close it, not a case of the market having already solved something SAIRNvet
uniquely lacks.

**Internal staff-to-staff AI-coached peer consult: searched for
specifically, and not found anywhere in named veterinary software.** No
product — PIMS or standalone — was found combining real-time AI coaching
during photo/video capture with internal, staff-to-staff-only routing for a
second opinion, across multiple search phrasings. The closest adjacent
products each differ in a specific, material way: **Butterfly Network's
iQ+ Vet** handheld ultrasound has "TeleGuidance" (a live human colleague
guides a novice via AR overlays — human, not AI, and locked to Butterfly's
own hardware); veterinary teleradiology/second-opinion services (Vetology,
VET-CT, IDEXX's own Diagnostic Imaging Telemedicine Consultants) route an
already-captured study to an external paid specialist, with no AI
capture-coaching step; and a September 2026 pilot announcement
(**MediCapture's aiScope**) runs real-time AI object detection during
capture, but is hardware-bound to MediCapture's own endoscopy/ultrasound
equipment and aimed at identifying anatomy mid-procedure, not peer routing —
known from a single press release with no independent trade-press coverage
found, so treat as an early pilot, not a proven shipped product. The
underlying mechanism — AI coaching a non-specialist to capture a
diagnostic-quality photo/video in real time — is a proven, even FDA-cleared
pattern in *human* healthcare (Caption Health's AI-guided cardiac
ultrasound capture, now part of GE HealthCare; peer-reviewed work on
AI-guided smartphone capture for teledermatology). Based on a genuinely
broad search across multiple phrasings, the specific combination SAIRNvet
built — capture coaching plus internal peer routing — looks like a real,
currently empty niche in veterinary-specific software.

**Regulatory context is a real, sourced reason client telemedicine stays
thin industry-wide, not just at SAIRNvet.** US veterinary telemedicine is
bottlenecked by veterinarian-client-patient-relationship (VCPR) law: most
states still require an in-person exam before any telemedicine visit can
legally support diagnosis, treatment, or prescribing, and only a minority of
states allow the VCPR itself to be established virtually (trackers disagree
slightly on the exact count — one 2026 tracker lists nine states, reflecting
how fast and inconsistently this is tracked). Even where virtual VCPR is
legal, restrictions bite (Arizona caps telehealth prescribing to a 14-day
supply plus one refill before an in-person exam is required). Reported
veterinary telehealth usage among practices reportedly *fell* from 38%
(2023) to 29.2% (2024) as pandemic-era habits receded, per a secondary
source citing AVMA data — this could not be independently verified against
AVMA's primary report this session (fetch blocked) and should be confirmed
before being cited further. Together, this is real, sourced support for
treating a thin client-telemedicine feature as a defensible product
decision rather than an oversight: the legally riskiest, highest-effort use
case (establishing a VCPR and prescribing purely over video) is unavailable
or capped in most states regardless of what any vendor builds.

### Sources (§4)

1. ezyVet — Zoom integration page — https://www.ezyvet.com/integration/zoom
   — accessed 2026-09-26 — vendor page.
2. ezyVet — Telemedicine feature page —
   https://www.ezyvet.com/features/telemedicine — accessed 2026-09-26 —
   vendor marketing.
3. ezyVet — Otto integration page — https://www.ezyvet.com/integration/otto
   — accessed 2026-09-26 — vendor page; confirms Otto = rebranded TeleVet.
4. IDEXX — Vello product page — https://software.idexx.com/vello —
   accessed 2026-09-26 — vendor page.
5. IDEXX — "Deliver Virtual Care to Clients with TeleVet" —
   https://software.idexx.com/resources/blog/deliver-virtual-care-to-clients-with-televet
   — accessed 2026-09-26 — vendor blog.
6. Vetstoria — Vetspire integration page —
   https://www.vetstoria.com/integrations/vetspire/ — accessed 2026-09-26 —
   third-party vendor page describing the TeleTails link-out.
7. Covetrus — AVImark product page —
   https://covetrus.com/covetrus-platform/workflow-and-productivity-tools/avimark/
   — accessed 2026-09-26 — vendor page.
8. Otto — AVImark integrations page —
   https://otto.vet/integrations/avimark/ — accessed 2026-09-26 — vendor
   page.
9. Covetrus — RoboVet Virtual Visits —
   https://solutions.covetrus.com/en/emea/robovet-telemedicine — accessed
   2026-09-26 — vendor marketing; underlying video tech undisclosed, low
   confidence on native-vs-third-party.
10. Covetrus — "Introducing virtual visits in RoboVet" —
    https://software.covetrus.com/emea/veterinary-insights/article/client-solutions/use-virtual-visits-in-robovet/
    — accessed 2026-09-26 — vendor blog.
11. Airvet — "How does Airvet work?" —
    https://airvet.zendesk.com/hc/en-us/articles/360055349812-How-does-Airvet-work
    — accessed 2026-09-26 — vendor support doc.
12. Vetster — For Vets page — https://vetster.com/en-us/for-vets —
    accessed 2026-09-26 — vendor page.
13. Vetster — "Introducing the Vetster for Vets mobile app" —
    https://vetster.com/en/blog/for-vets/introducing-the-vetster-for-vets-mobile-app-practice-virtually-on-the-go
    — accessed 2026-09-26 — vendor blog.
14. Otto — "The Best Veterinary Telemedicine Services" —
    https://otto.vet/the-best-veterinary-telemedicine-services/ — accessed
    2026-09-26 — vendor marketing, self-interested comparison vs. Zoom, low
    confidence on that specific claim.
15. GuardianVets — Telemedicine Consultations page —
    https://guardianvets.com/telemedicine-consultations-empower-your-practice-enhance-client-care/
    — accessed 2026-09-26 — vendor page; native-vs-embedded video not
    independently confirmed.
16. Butterfly Network — iQ+ Vet page —
    https://vet.butterflynetwork.com/iq-plus — accessed 2026-09-26 — vendor
    page describing TeleGuidance.
17. Vetology — Teleradiology page — https://vetology.net/teleradiology/ —
    accessed 2026-09-26 — vendor page.
18. VET-CT — homepage — https://us.vet-ct.com/ — accessed 2026-09-26 —
    vendor page.
19. IDEXX — Diagnostic Imaging Telemedicine Consultants page —
    https://www.idexx.com/en/veterinary/diagnostic-imaging-telemedicine-consultants/telemedicine-consultants/
    — accessed 2026-09-26 — vendor page.
20. dvm360 — "Comparison: Veterinary telemedicine and smartphone apps" —
    https://www.dvm360.com/view/comparison-veterinary-telemedicine-and-smartphone-apps
    — accessed 2026-09-26 — trade publication, snippet only; mentions
    BabelVet's staff photo-messaging portal.
21. VitusVet — Two-Way Text & Picture messaging page —
    https://vitusvet.com/features/two-way-text-messaging/ — accessed
    2026-09-26 — vendor page.
22. PR Newswire / MediCapture — "MediCapture Launches aiScope Pilot for
    Veterinary Sciences at VMX 2026" —
    https://www.prnewswire.com/news-releases/medicapture-launches-aiscope-pilot-for-veterinary-sciences-at-vmx-2026-302661534.html
    — accessed 2026-09-26 — single press release, wire-syndicated only, no
    independent verification found, low confidence, pilot stage.
23. Caption Care — Technology page — https://www.caption-care.com/technology
    — accessed 2026-09-26 — vendor page; FDA clearance referenced via
    search snippet, not independently fetched.
24. PMC — "Development and Clinical Evaluation of an Artificial Intelligence
    Support Tool for Improving Telemedicine Photo Quality" —
    https://pmc.ncbi.nlm.nih.gov/articles/PMC10018405/ — accessed
    2026-09-26 — peer-reviewed, snippet only.
25. NCBI PMC — "Wound Image Quality From a Mobile Health Tool... Real-Time
    Quality Feedback" — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8367165/
    — accessed 2026-09-26 — peer-reviewed, snippet only.
26. GetVetWise — "Veterinary Telemedicine Regulations 2026: State-by-State
    VCPR Guide" — https://www.getvetwise.com/posts/veterinary-telemedicine-regulations-2026
    — accessed 2026-09-26 — industry tracker, moderate confidence; state
    counts should be re-verified given how fast this law is moving.
27. AAHA — "The patchwork quilt of state veterinary telehealth laws" —
    https://www.aaha.org/newstat/publications/the-patchwork-quilt-of-state-veterinary-telehealth-laws/
    — accessed 2026-09-26 — trade association publication, moderate-high
    confidence, snippet only.
28. co.vet — "Veterinarian Facts: Key Stats, Trends, and Insights in 2026" —
    https://co.vet/post/veterinarian-facts/ — accessed 2026-09-26 —
    secondary blog citing AVMA data; primary AVMA report not independently
    confirmed this session — lower confidence pending primary-source check.
29. market.us — "Veterinary Telehealth Market Projected to Reach US$2.4
    Billion by 2034" — https://market.us/press-release/veterinary-telehealth-market/
    — accessed 2026-09-26 — paid market-research press release, low
    confidence.
30. AVMA — "VCPR requirements fuel state legislative activity" —
    https://www.avma.org/news/vcpr-requirements-fuel-state-legislative-activity
    — accessed 2026-09-26 — primary trade-association source per search
    snippet; direct fetch blocked this session.
31. Texas Legislature — Bill Analysis, SB 1442 —
    https://capitol.texas.gov/tlodocs/89R/analysis/html/SB01442S.htm —
    accessed 2026-09-26 — primary legislative source per search snippet,
    not independently fetched.

Also checked and found **not to be real telemedicine comparables**, recorded
rather than dropped silently: Anivive (a veterinary drug-discovery company,
unrelated to telehealth); Whiskercloud (a veterinary marketing/website
platform, now under PetDesk/Petvisor); Chronos/Chronos Vet (a remote
-staffing service for virtual receptionists/technicians, not a video-hosting
platform); no product named "Dutkiewicz" was found under any search — it
does not appear to be a real, findable product.

---

## 5. Synthesis — real gaps and real risks, combined across both documents

**Already known, from the 2026-09-25 sibling document (not re-derived
here):** no radiograph image reading (imaging panel tracks paperwork, not
images); treatment does not flow into an invoice line automatically; no
client-facing booking portal; multi-location/inventory is a status board,
not an operations layer.

**New from this pass:**

1. **Client-facing telemedicine is thin, but this is not a competitive gap
   in the usual sense — it's a market-wide pattern SAIRNvet already
   matches.** Every named PIMS checked (ezyVet, IDEXX Neo, Vetspire, AVImark)
   either links out to Zoom or resells a third-party telehealth product; none
   self-hosts video. VCPR law gives a real, sourced reason the highest
   -stakes use case (prescribing over video) is capped in most states
   regardless. Deeper calendar/record integration around a third-party call
   (as ezyVet+Zoom shows) is a buildable improvement, not a case of catching
   up to something competitors have already solved.
2. **The internal AI-coached staff-to-staff photo/video peer consult
   (`panel-photoconsult`) is, on a genuinely broad search, a real and
   currently unmatched feature in named veterinary software.** This is worth
   stating confidently externally — with the caveat that "Phase 1" scope
   (no video-calling infra, scheduling, or payments) should be described
   accurately rather than oversold as full telehealth.
3. **Exotic-species dosing/interaction depth is a genuine differentiator,
   and simultaneously a real internal risk that has not been resolved.**
   Every named PIMS and even the two best industry-licensed formulary
   products (Plumb's, FDB) stop their interaction-checking coverage at
   dog/cat or dog/cat/horse. SAIRNvet's own reference data reaching into
   chelonians, rabbits, and zoo/wildlife species has, on this evidence, no
   external authoritative source to be checked against — unlike the
   dog/cat data every competitor and reference product can validate against
   Plumb's 25,000-interaction dataset. A peer-reviewed 2022 survey found
   43.5% of exotic-treating veterinarians sometimes or never verify the
   source behind a formulary dose, and a companion study found real gaps
   between a formulary's stated exotic-mammal doses and its cited sources —
   this is exactly the failure mode SAIRNvet's own toxicity-flag data should
   not be assumed immune to just because no external vendor was found doing
   it better. This belongs with whoever owns `VET_SPECIES_REF`'s data
   provenance, not just in a competitive-positioning deck.
4. **The exotic-patients panel itself has not yet been through the
   fabrication-hardening pass** that just caught invented KPIs across ten
   other panels (§0.2). Before any external claim trades on SAIRNvet's
   exotic-species architecture, that specific panel's content should get
   the same audit its financial panels just received.
5. **AVImark's perpetual-license opacity and Covetrus Pulse's real
   quoted-vs-billed and broken-price-lock complaints are market color worth
   knowing, not a SAIRNvet feature gap.** Two named competitors in this
   space have documented pricing-trust problems from their own real
   customers. This is not a claim SAIRNvet can make about itself by default
   — it would need its own pricing to actually be transparent and honored to
   turn this into a real point of contrast.

---

## 6. What this document does not establish or decide

- **No claim in this document should be quoted externally** — to a customer,
  prospect, or in sales material — without a follow-up read from a network
  that can reach the underlying primary sources; every finding rests on
  search-engine snippets, per §0.1.
- **This document does not decide whether or how SAIRNvet should market any
  of the differentiators identified**, nor whether the identified gaps
  (telemedicine depth, the unvalidated exotic-species reference data) are
  worth building or fixing next, in what order, or at what cost — that is a
  `sairn-software-architect` / `sairn-decision-gate` question, consistent
  with how the 2026-09-25 sibling document treats its own four gaps.
- **It does not resolve AVImark's or Covetrus Pulse's actual current base
  price** — both remain genuinely unpublished as of this pass.
- **It does not audit `exotic-patients`, `panel-photoconsult`, or
  `panel-teleconsult` for the fabricated-KPI/non-functional-button pattern**
  the ongoing internal hardening pass is finding elsewhere — it only reports
  which of those panels the most recent internal handoff confirms is
  outstanding.
- **The "VIN SafetyNet" reference in the original research brief for this
  pass does not appear to be a real, named product** — flagged in §2 so the
  assumption is not repeated elsewhere without a check.

## 7. Decay

Every source above is a search-index snapshot from 2026-09-26 of pages this
session's sandboxed network could not open directly (§0.1). Pricing (§1),
the specific competitive feature claims in §2–§4, and the internal
panel-audit status in §0.2 are all time-sensitive and will go stale faster
than the general market patterns described. **Do not treat any pricing
figure, feature-parity claim, or "not yet audited" panel status here as
current without re-checking directly against the live source**, and re-run
the vendor-facing portion of this pass from a network that can reach the
underlying domains before any of it is used in a customer-, investor-, or
sales-facing statement.
