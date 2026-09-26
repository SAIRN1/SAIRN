# SAIRNvet — external competitive-gap audit, the three axes the 2026-09-25 pass could not survey

**Derived 2026-09-26 (Fourth).** Retrieval date for every external row: **2026-09-26**.

> **THIS IS A COMPLEMENT, NOT A REPLACEMENT, AND THE BRIEF'S PREMISE WAS WRONG.**
> The brief for this pass said *"No fresh external competitor audit doc exists for
> this vertical yet."* One does:
> `docs/cloud-research/SAIRNvet-external-competitive-gap-audit-2026-09-25.md`,
> 362 lines, landed yesterday. It is not superseded and nothing in it is
> re-litigated here. What it does **not** survey is exactly what this pass was
> asked for, which is why this document exists rather than a second copy of that
> one.

**What the 09-25 pass covered:** AI radiograph screening, treatment-to-invoice
charge capture, client-facing booking, mid-market/multi-location, inventory, a
pricing landscape, a patent screen, market signals.

**What it did not, measured against it rather than asserted:** grep it for the
three axes this pass was asked about and the result is `dos(e|ing)|interaction`
— nine hits, **eight about SAIRNvet's own side and one saying every AI-dosing
claim found sits inside imaging**; `exotic|avian|reptil` — three incidental
hits; `telemedicine|photo.?consult` — **one** incidental hit. Two of the
competitors the brief names, **Vetter and AVImark, appear zero times in it.**

---

## 0. THE EVIDENCE GRADE IS ONE HIGHER THAN THE 09-25 PASS, AND THAT WAS ITS OWN TOP ACTION ITEM

That document's §0 records that its session's egress could not reach any vendor
domain — every `WebFetch` returned `EGRESS_BLOCKED` — so every cell in it is a
**search-engine snippet of a vendor page, not the page**. It called a follow-up
from a network that can reach those domains *"the single most important action
item this document produces, ahead of any competitive finding in it."*

**This session can reach them.** Every row marked **[OPENED]** below is a page
this session fetched and read. Rows marked **[SNIPPET]** or **[BLOCKED]** are
graded down and say why. One host refused outright and is reported rather than
routed around:

| Host | Result |
|---|---|
| `ezyvet.com/pricing` | **[OPENED]** |
| `instinct.vet` | **[OPENED]** |
| `plumbs.com` | **[OPENED]** |
| `vetspire.com` → `vetspire.ai` | **[OPENED]** (301, see §5) |
| `covetrus.com/.../avimark/` | **[OPENED]** |
| `digitail.com` | **[OPENED]** |
| `software.idexx.com/products/neo/pricing` | **[OPENED]** |
| `ca.idexx.com/.../neo-faqs/` | **[OPENED]** |
| `vetster.com` | **[SNIPPET]** — domain-restricted search only |
| `airvet.com` | **[BLOCKED]** — HTTP 403. Not retried, not routed around |

**Still not established, and it bounds everything below:** an absence on a
marketing page is not an absence in a product. "ABSENT from the page" below means
exactly that and never "the product cannot do this." Demo-gated feature matrices
were not obtained; no vendor was contacted.

---

## 1. INTERNAL GROUNDING FIRST, MEASURED FROM THE FILE

Done before any external search, per the brief, so nothing below re-litigates
what is built. Every figure here is parsed from `sairnvet.html` at HEAD, not read
off a prior document.

**The formulary — 485 entries across 26 distinct species values:**

| | | | |
|---|---|---|---|
| dog 156 | cat 122 | horse 59 | cattle 38 |
| **exotic (unspecified) 20** | bird 15 | swine 13 | **reptile 10** |
| sheep 9 | other/exotic/zoo 6 | goat 6 | poultry 5 |
| llama/alpaca 5 | **rabbit 3** | zoo/wildlife 3 | emu/ratite 3 |
| **ferret 1** | zoo (unspecified) 2 | zoo large mammals 2 | + 7 more |

* **201 of 485 (41%) carry `needsReview`**; 377 carry a non-empty clinical flag;
  35 are controlled substances.
* **The exotic entries refuse to give a number.** Verbatim from the data:
  *"Dose varies significantly by taxon — consult exotic-specific formulary (e.g.
  Carpenter's Exotic Animal Formulary), do not extrapolate from dog/cat dose."*
* **`INTERACTION_MATRIX` — 15 deterministic rules** (6 major, 9 moderate) over 44
  drug tokens, evaluated *before any AI involvement*, with the non-exhaustiveness
  stated twice: in the panel copy (*"This is NOT an exhaustive interaction
  database — absence of a result here does not mean no interaction exists"*) and
  again in the no-result message (*"This does NOT confirm safety"*).
* **Seven species hubs are first-class navigation:** Companion Animals, Equine
  Hub, Large Animals / Herds, Exotic & Small Mammals, Avian, Reptile & Amphibian,
  Aquatic.
* **Telemedicine and Photo/Video Consult are two different panels**, and the
  Telemedicine one discloses its own limit: *"This app doesn't host video itself —
  it generates a placeholder link to paste into whatever video platform your
  clinic uses (Zoom, Google Meet, etc)."*
* **Photo/Video Consult is vet-to-colleague, not client-to-vet:** *"Capture a
  photo for an AI-guided suggestion, or send it straight to a colleague on staff
  for their input"*, under a hard disclosure that *"AI suggestions and colleague
  responses here are input, not a diagnosis or prescription… Colleague responses
  are logged as consult notes and are never auto-applied to a patient record."*
  Its species selector includes Avian, Reptile and Exotic/Other.

**ONE DRAFT FINDING DIED ON THIS STEP AND IT IS WHY THE STEP IS FIRST.** Reading
Plumb's "industry's only" interaction claim, this pass had drafted *"SAIRNvet has
no drug-drug interaction checker at all."* It has one — `INTERACTION_MATRIX`,
deterministic, pre-AI, 15 rules. The internal grounding instruction caught a
false external finding before it was written down.

---

## 2. AXIS 1 — CLINICAL DECISION SUPPORT DEPTH, DRUG DOSING AND INTERACTIONS

### 2.1 The structural finding: no practice-management system in this pass claims dosing CDS at all

| Product | Dosing calculation | Dose-range check | Interaction check | Contraindication check | Evidence |
|---|---|---|---|---|---|
| **Vetspire** | ABSENT | ABSENT | ABSENT | ABSENT | **[OPENED]** `vetspire.ai` |
| **AVImark** (Covetrus) | ABSENT | ABSENT | ABSENT | ABSENT | **[OPENED]** `covetrus.com` |
| **Digitail** | ABSENT | ABSENT | ABSENT | ABSENT | **[OPENED]** `digitail.com` |
| **IDEXX Neo** | ABSENT | ABSENT | ABSENT | ABSENT | **[OPENED]** pricing page |
| **ezyVet** | not claimed on the pricing page | — | — | — | **[OPENED]** pricing page only |
| **Plumb's / Instinct** | "prescribing support" | not specified | **YES, dogs and cats** | not as a species gate | **[OPENED]** both |

**Clinical decision support in this market is a SEPARATE SUBSCRIPTION, not a PIMS
feature.** Vetspire's own page is entirely AI-scribe and workflow — *"AI Scribe"*,
*"AI Summary"*, *"save up to 90 minutes per day"* — with no pharmacological claim
of any kind. AVImark's page carries no clinical-decision claim and mentions
telemedicine only *"Linked with Covetrus Comms"*. Digitail advertises *"20+ AI
Workflows"* including *"AI SOAP dictation"* and names no drug check.

**That is SAIRNvet's real structural differentiator and it is not the one the
09-25 pass named.** That pass said the differentiator is a model-independent
contraindication gate, which is true. The sharper version is **where it lives**:
the gate is inside the record system, so the check cannot be skipped by not
opening a second product. Everyone else's dosing intelligence is one
subscription away from the prescribing moment.

### 2.2 The market's only claimed veterinary interaction checker is DOG AND CAT ONLY

Instinct markets Plumb's as *"Trusted drug information with the industry's only
veterinary-specific drug interaction checker"* **[OPENED]**. Plumb's own page
states what it checks: *"Check for potential drug-to-drug interactions in **dogs
and cats**"* **[OPENED]**.

**No exotic, avian, reptile or small-mammal species is named anywhere on that
page.** So the one product in this market that claims to be the only veterinary
interaction checker covers two species.

**AND THE TWO CHECKS ARE NOT THE SAME CHECK — conflating them would overstate
SAIRNvet and is the error this section exists to avoid.** Plumb's does
**drug↔drug** interactions with commercial monograph depth behind it. SAIRNvet
does **species↔drug** contraindication plus a **15-rule** drug↔drug matrix.
Neither substitutes for the other, and the honest read is a gap in **both**
directions:

* **In SAIRNvet's favour:** species breadth. 26 species values against two, and a
  deterministic gate no model can bypass.
* **Against it, and disclosed in product:** interaction depth. 15 curated rules
  over 44 drug tokens is not a monograph database and the panel says so in two
  places. An exotics practice needs Plumb's *or* Carpenter's alongside SAIRNvet,
  and SAIRNvet's own flags say so by name.

### 2.3 Instinct's third product is the nearest thing to a direct competitor found

*"Attending"* — *"Evidence-based AI assistant for clinical decision support. Ask
a clinical question and receive reasoned, cited answers in seconds"*, drawing on
*"over 30 years of peer-reviewed, trusted veterinary resources"* **[OPENED]**.
That is the same shape as SAIRNvet's Ask-AI panel, with a citation corpus
SAIRNvet does not have. **SAIRNvet's Ask-AI panel already disclaims exactly this
gap** in its own copy: it tells the user the dosing calculator and diagnosis
library *"are connected to the verified database and contraindication checks;
this one isn't."* No competitor page read in this pass carries a comparable
sentence about its own AI.

---

## 3. AXIS 2 — EXOTIC AND NON-STANDARD SPECIES

**Not one competitor page opened in this pass makes a species-coverage claim of
any kind.** Not Vetspire, AVImark, Digitail, IDEXX Neo or ezyVet's pricing page.
Plumb's states two species. The 09-25 pass's only species datapoints were
incidental and remain the only ones: Vetology's **radiologist** (not AI) reads
covering *"dogs, cats, small mammals, avian, reptile and equine"*, and a July 2026
acquisition signal described as adding 25+ species — both **[SNIPPET]** there and
not re-verified here.

**Telemedicine is where the exotic demand is visibly acknowledged.** Vetster's own
domain describes birds, rabbits, ferrets and reptiles as *"underserved animals,
with limited access to knowledgeable veterinary care"* and lists exotic-only
practitioners **[SNIPPET]**. So the market recognises the gap in the *consult*
channel while the *software* channel says nothing about it.

**THE GAP RUNS BOTH WAYS AND SAIRNvet IS ON THE HONEST SIDE OF IT.** SAIRNvet has
seven species hubs and 26 species values — and for exotics it deliberately
**refuses to state a dose**, naming Carpenter's instead. That is a coverage
*limit*, published as a limit. The competitive fact is not that SAIRNvet doses
exotics better; it is that **nobody in this pass doses exotics at all, and
SAIRNvet is the only product read here that tells the user so at the point of
use.**

**The real unmet need this surfaces** — stated as a market observation, not a
build recommendation — is that an exotics practice today needs a PIMS with no
species intelligence, plus a dog-and-cat interaction checker, plus a paper
formulary. SAIRNvet collapses two of those three.

---

## 4. AXIS 3 — TELEMEDICINE AND PHOTO/VIDEO CONSULT PARITY

**SAIRNvet is NOT in the same category as the telemedicine platforms, and any
parity claim would be false.** Established from the internal read in §1, before
any comparison:

| | SAIRNvet | Vetster / Airvet class | PIMS class |
|---|---|---|---|
| Who consults whom | **vet → colleague on staff**, plus AI triage | **pet owner → vet** | varies |
| Live video hosted | **NO, and disclosed** — generates a link for Zoom/Meet | yes | Digitail "remote consultations", unspecified |
| Asynchronous photo | **yes**, captured into the record | varies | not specified on any page opened |
| Output status | *"input, not a diagnosis or prescription"*, never auto-applied | a real consult, prescribing where lawful | — |
| Species | selector includes Avian, Reptile, Exotic/Other | Vetster names exotics **[SNIPPET]** | ABSENT everywhere |

**The genuine gap, stated plainly: client-to-vet video is not built and is not
claimed.** SAIRNvet's Telemedicine panel is a link generator with a sentence
saying so. Digitail claims *"Telemedicine … remote consultations"* with no detail
**[OPENED]**; AVImark reaches it only through a separate Covetrus Comms product
**[OPENED]**; Vetspire's page does not mention it at all **[OPENED]**. So among
the PIMS products read here, telemedicine is either absent, outsourced, or
one undetailed line — **SAIRNvet's disclosure is more specific than three of its
competitors' claims.**

**And the peer-consult channel it DID build has no competitor in this pass.** No
page opened here describes a vet-to-colleague image consult logged as a consult
note inside the record. That is either a real unclaimed position or a category
these vendors put in a demo rather than on a page; this pass cannot tell which,
and `airvet.com`'s 403 is precisely where that answer would have been.

---

## 5. PRICING — MOSTLY UNPUBLISHED, AND TWO FIGURES ARE REAL

| Product | Published price | Grade |
|---|---|---|
| **ezyVet** | *"Get started for as little as **$260.50 per month**"*; one feature set for everyone — *"whether you're a single veterinarian practice or you have hundreds of staff members, you'll always have access to all our features and latest updates"*; enterprise pricing on request | **[OPENED]** |
| **IDEXX Neo (Canada)** | **$355 CAD/month** base, *"All Neo features"* + *"First three (3) active and logged in users"*; **$26 CAD/month** per additional active user; **$185 CAD/month** per additional location | **[OPENED]** `ca.idexx.com` |
| **IDEXX Neo (US)** | **NOTHING.** The US pricing page publishes no figure at all — only *"Get started for free"* | **[OPENED]** |
| **Plumb's** | no figure on the homepage; *"discounts are available starting at groups of 5 or more"* | **[OPENED]** |
| **Vetspire** | no figure; *"Cut $200+ in monthly costs"* is a saving claim, not a price | **[OPENED]** |
| **Instinct, AVImark, Digitail** | no figure published | **[OPENED]** |

**A SOURCING CORRECTION WORTH RECORDING.** A domain-restricted search surfaced
*"$199 per month"* for Neo and attributed it to IDEXX. That figure is **not on the
pricing page** — it traces to a newsroom-archive announcement, and the only
currently-published Neo figures are the Canadian ones above. **Do not quote
"$199/month" for Neo.** This is the same trap the 09-25 pass flagged on Vetology,
where two snippets gave conflicting prices and neither page was opened.

**One datable market signal:** `vetspire.com` now issues a **301 to
`vetspire.ai`** — observed 2026-09-26. A domain move to `.ai` is a repositioning,
and it matches a page that is now entirely AI-scribe messaging with no clinical
claim.

---

## 6. WHAT SAIRNvet DOES NOT COVER TODAY — the brief's actual question

Ordered by how much a real buyer would feel it. Every one is **already disclosed
in product**, which is the finding rather than a caveat on it.

1. **Interaction-database depth.** 15 curated rules against a commercial
   monograph set. Disclosed twice in the panel. An exotics or referral practice
   still needs Plumb's or Carpenter's alongside.
2. **Client-to-vet video.** Not built, not claimed, link generator only.
3. **Exotic dosing numbers.** A deliberate refusal naming Carpenter's. Correct,
   and it means SAIRNvet cannot be the only reference on an exotic case.
4. **41% of the formulary is `needsReview`.** An honesty feature and a coverage
   statement at once. No competitor publishes an equivalent figure, so it cannot
   be benchmarked — the absence of comparison is not evidence of parity.
5. **No citation corpus behind Ask-AI**, where Instinct's *"Attending"* claims 30
   years of peer-reviewed sources. SAIRNvet's own copy already points users away
   from that panel toward the verified database.

## 7. WHAT THIS DOCUMENT DOES NOT ESTABLISH

* **An absence on a marketing page is not an absence in a product.** Every
  "ABSENT" above is about a page. Demo-gated matrices were not obtained and no
  vendor was contacted.
* **`airvet.com` returned 403 and was not routed around**, so the client-facing
  photo-consult comparison is one major player short.
* **Vetster is snippet-grade only.** Its exotic-species statements are indexed
  excerpts, not opened pages.
* **Vetter was not reached at all** — named in the brief, zero coverage in the
  09-25 pass, and still zero. It is the clearest single gap in this series.
* **No pricing for SAIRNvet itself** is compared here; that is a commercial
  decision and out of scope for an external audit.
* **Nothing about legal telemedicine scope** — VCPR rules, state-by-state
  prescribing limits — was researched. A client-to-vet video build would turn on
  exactly that and this document is not evidence about it.
* **No patent work.** §5 of the 09-25 pass stands unchanged and unverified.
* **No code was written and no app file was touched.**

## 8. Decay

The two published prices and the Plumb's two-species scope are the cells most
worth re-reading; a pricing page and a feature scope both move without notice.
The `vetspire.ai` move dates this pass precisely, which is convenient: anything
here that disagrees with a page after that date should be re-fetched rather than
reconciled.

## Sources

- [ezyVet — Pricing](https://www.ezyvet.com/pricing)
- [Instinct — products, including Plumb's, Standards and Attending](https://www.instinct.vet/)
- [Plumb's](https://plumbs.com/)
- [Vetspire](https://www.vetspire.ai/)
- [Covetrus — AVImark](https://covetrus.com/covetrus-platform/workflow-and-productivity-tools/avimark/)
- [Digitail](https://digitail.com/)
- [IDEXX Veterinary Software — Neo plans and pricing (US)](https://software.idexx.com/products/neo/pricing)
- [IDEXX Canada — Neo FAQs, including published CAD pricing](https://ca.idexx.com/en-ca/veterinary/software-services/neo/neo-faqs/)
- [Vetster — virtual services for exotics](https://vetster.com/en/blog/for-vets/virtual-services-for-exotics-on-vetster)
- [Vetster — top telemedicine cases by species](https://vetster.com/en/wellness/top-veterinary-telemedicine-appointment-cases-by-species)
- `airvet.com` — HTTP 403, not retrieved
