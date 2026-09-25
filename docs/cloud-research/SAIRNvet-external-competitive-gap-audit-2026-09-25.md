# Worldwide external competitive-gap audit — SAIRNvet

**Research pass, 2026-09-25. No code written, no app file touched.** Written
by a standalone cloud session under `docs/cloud-research/` per instruction
(new files only, new branch, no PR). This is the *external market* companion
to the internal re-derivation already on `main`
(`docs/SAIRNvet-competitive-gap-audit-2026-09-24.md`, recreated 2026-09-24 by
Fourth from a stranded cloud session's findings and re-verified against
HEAD). That document is the anchor for what SAIRNvet actually has; this
document is the market this platform sells into.

**Method, and the standard it was held to**: the reference for this series is
`docs/superpowers/specs/2026-09-02-stonedesk-worldwide-competitive-gap-audit.md`
— every competitor claim read from the vendor's own site, not a comparison
article; aggregator pages used only to find vendors; a failed fetch recorded
as a failure, never filled in; pricing only from a vendor's own pricing page.

---

## 0. A material limitation, stated before anything else

**This session's outbound network cannot reach any vendor, trade-press, or
patent-office domain.** Every `WebFetch` attempted against a vendor page in
this pass — including one made directly by this session, not a subagent, to
`www.shepherd.vet/pricing`, immediately after confirming the egress proxy
itself is healthy (`curl .../__agentproxy/status`: `enabled: true`,
`bundleCoversEveryHost: true`, zero recent relay failures) — returned
`EGRESS_BLOCKED`. The proxy's own status output shows no certificate or
routing fault; the block is a destination-level policy decision the session
cannot see the reason for, and the README's own instruction on a 403/407 is
explicit: *"Do not retry or route around it — report the blocked host."* That
instruction is followed here rather than worked around.

**What this means for evidence grade.** Every vendor-fact cell below was
obtained by `WebSearch` restricted to the named vendor's own domain
(`allowed_domains`), which returns the search engine's indexed *excerpt* of
that vendor's page, not the page itself. That is the correct fallback under
the constraint and it is **one grade below the audit standard this series set
for itself**: a snippet can be stale, truncated, or the wrong page version,
and cannot be cross-checked against the page's full context. Every claim
below is a **vendor-domain snippet, not independently opened**, and is marked
as such rather than presented as a direct read. **Nothing here should be
quoted externally — to a customer, in a pitch, in a proposal — without a
follow-up pass from a network that can reach these domains.** That follow-up
is the single most important action item this document produces, ahead of
any competitive finding in it.

Patent-office and Google Patents domains were equally blocked; §5 records
patent numbers as they appear in third-party index snippets (Justia, USPTO
Gazette excerpts), explicitly unverified, with no infringement conclusion
drawn from any of them — the same caution the StoneDesk audit's own
sources section models for a fetch that fails.

Retrieval date for every row below: 2026-09-25.

---

## 1. What SAIRNvet has, measured against the internal audit

Read from `docs/SAIRNvet-competitive-gap-audit-2026-09-24.md` (the
Fourth-verified HEAD document) and confirmed as the anchor for this pass:

**BUILT, verified with a real caller, not just a marker hit:**
- An ambient AI scribe: consent recorded per visit to `sv_scribe_consent`,
  ends in a server refusal until a self-hosted transcription host is
  configured (no third-party ASR vendor named in the code), and the
  clinician must accept every draft before it is filed, with the draft's
  provenance (`drafted_by`, model, consent id) recorded on the SOAP row.
- A 485-entry, species-bounded drug formulary with a deterministic
  contraindication gate (independent of the model, cannot be silently
  bypassed) and a dose-audit trail.
- A DEA Schedule II–IV controlled-substance register with a two-person
  witness lock and a readable-in-product dosing audit trail, verified against
  the server's own row count since 2026-09-24.
- Per-employee PIN authentication with six roles and a server-side session
  gate on all 42 synced resources.

**REAL GAPS, confirmed by the internal audit's caller-level check (a marker
hit is not proof; every non-zero hit was hand-read):**
1. **Radiograph AI screening** — the imaging panel is a study-status tracker
   (patient, study, modality, ordering doctor, status). No image attaches to
   a study row, nothing reads one, nothing screens one. `x-ray`: zero;
   `dicom`: zero.
2. **Treatment-to-invoice** — invoices are one hand-typed total per record.
   No line items, no link from a SOAP note, a dose calculation, a lab result
   or a surgery record to a charge.
3. **Client-facing booking** — none. The panel once called "Client Portal"
   was renamed "Client Requests" on 2026-09-04 with the comment "There is no
   portal"; it is a staff-entered log of phone and email requests.
4. **Mid-market location/inventory** — `panel-multisite` is a hand-typed
   per-location revenue table with no link to any other record; `inventory`
   appears once in the entire file; `reorder` appears zero times.

---

## 2. The market, as far as this session could establish it

Twenty-plus vendors across five categories, every claim a vendor-domain
**snippet, unopened** unless marked third-party.

### 2.1 AI radiograph screening (Gap 1)

| Vendor | What the vendor-domain snippet states | Retrieval evidence |
|---|---|---|
| **SignalPET** (standalone) | "trusted by 2,500+ active clinics"; average result turnaround **3 minutes**; AI trained on "50+" (elsewhere "63+") clinically relevant pathologies across thoracic, abdominal, spine, pelvis and limb views; **a low-confidence case is automatically routed to a board-certified veterinary radiologist at no extra charge**; three tiers — Immediate Report (AI, pay-as-you-go), Complete Report (AI plus clinical context, under 30 min), Radiologist Report (STAT under 60 min "starts at $100", Routine under 12 h "starts at $60"); states native integration into Provet and Vetspire, DICOM/PACS for everything else | `signalpet.com`, `docs.signalpet.com` snippets |
| **Vetology** (standalone, also Patterson-resold) | AI "screens the radiograph for 91+ canine and feline conditions" in "five to ten minutes"; a pricing snippet states an "AI 50" tier at **$200/month ($2,000/year)** for 50 AI reads/month, no contract; a separate snippet said "$200/month for unlimited studies" — **the two figures conflict and neither was confirmed by opening the page**; radiologist reads (not AI) cover dogs, cats, small mammals, avian, reptile and equine; states its AI is "decision support, not a verdict… the veterinarian can disagree, edit, or set aside any finding" | `vetology.net` snippets, internally inconsistent, unresolved |
| **Antech RapidRead** (Mars; standalone service) | "Reports are generated in 10 minutes or less"; dogs and cats; emergent findings auto-route to a board-certified specialist for a STAT review "at no additional cost" (~2 hours), fee credited if a radiologist review is requested; a Dental variant launched for canine May 2025 and feline January 2026; FAQ states results are "designed to be used in conjunction with a clinical examination, patient history… and these reports do not replace the clinical judgment of the treating veterinarian" | `antechdiagnostics.com` snippets |
| **Radimal** (standalone) | "instant AI-powered assessments for every case… board-certified specialist consultations"; guaranteed turnaround "1 hour for STAT and 48 hours for Standard"; states integration with "popular practice management systems"; per-case price not stated, enterprise pricing "on request" | `radimal.ai` snippet |
| **IDEXX Web PACS** (PIMS-adjacent, serves ezyVet/Neo/Cornerstone) | States an AI-powered *viewer* that aligns images to hanging protocols and calculates a vertebral heart score with a trend chart, and an "AI-enabled case submission workflow" for telemedicine — **no AI pathology read is claimed**, only viewer and case-prep automation | `idexx.com`, `software.idexx.com` snippets |
| **Vetspire** (PIMS) | The only PIMS-domain snippet stating a native in-chart AI read: "Vetspire integrates with SignalPET to display radiology results and X-ray imaging in Vetspire patient charts" | `manual.vetspire.com`, `support.vetspire.com` snippets |

**Pattern across every vendor found**: a study is pushed as DICOM to a cloud
service; a classifier returns a structured findings list within minutes;
low-confidence or emergent studies are auto-routed to a boarded radiologist
whose signed report is a separately priced tier; every vendor frames the AI
output as decision support, not a diagnosis. Only one PIMS (Vetspire) shows
the read natively in the chart; every other integration is a DICOM/PACS
side-channel, which is a materially smaller build than a native classifier.

### 2.2 Treatment-to-invoice / charge capture (Gap 2)

| Vendor | Mechanism as the vendor-domain snippet describes it |
|---|---|
| **Shepherd** | "As treatments or products are logged in the SOAP, the corresponding charges are automatically added to the invoice. If it's documented, it's billed." States 96.5% charge capture against a stated "industry standard" of 90% |
| **Instinct** | Completion-triggered posting: "Once the treatment is completed on the Tx sheet, the cost of the service goes to the Instinct Invoice… items are not actually sent to the invoice until they are completed." A second path posts timed charges (fluid pumps, hospitalisation) on an interval |
| **ezyVet** | "clinical decisions and actions automatically drive the invoice in real-time… no more double handling of information already entered into the clinical record" |
| **Covetrus Pulse** | "The Pulse Treatment Board captures charges automatically… The patient medical record… automatically updates to reflect all associated charges from the board" |
| **Provet Cloud** | "charge capture tied directly to administered treatments and products"; a February 2026 release adds an AI "Scribe" the snippet says handles "notes and charge capture" |
| **Digitail** | "Voice to Invoice: as the veterinarian documents the visit, Tails AI reviews the medical record and suggests invoice items before checkout" — note the word *suggests*: a review step, not deterministic posting |

Two distinct mechanisms recur: **completion-triggered posting** (a treatment
item posts a line the instant it is marked done, with timed items accruing
on an interval) and **record-driven posting** (adding an item to the SOAP
plan creates the invoice line, estimate → plan → invoice). Both need an
invoice line item that carries a foreign key back to the clinical event.

### 2.3 Client-facing booking (Gap 3)

| Vendor | Instant vs. request | Writes to schedule | Price (vendor-domain snippet) |
|---|---|---|---|
| **Vetstoria** (standalone) | Instant — "when a slot is selected… Vetstoria instantly updates the clinic's schedule" | Yes, real-time, 30+ PMS | €149 / €249 / €349 per month by clinician-count tier (EU pricing page); the snippet states the US operates under the **PetDesk** brand, with no US price published |
| **PetDesk Direct Booking** | Instant — syncs to the PIMS calendar on booking | Yes, 25+ systems | Not published on the booking product's own pricing page (only a forms sub-product is priced, $29.90–$79.90/mo) |
| **Vet Hero SchedulingHero** | Request-then-confirm by design: "you can choose to accept or deny it before it goes into your PIMS" | Only after acceptance | Not published |
| **IDEXX Vello** (for ezyVet/Neo/Cornerstone) | Both modes, configurable per practice | Real-time sync either way | Add-on subscription, price not published |
| **Digitail** (native) | Both; default is request ("Pending Confirmation") | Yes | Included in PIMS price |
| **Shepherd** (native) | Both — "Direct Booking" and "appointment requests" modes named separately | Yes | No extra cost, included |
| **ezyVet** (native) | Vendor wording is "clients can make appointments online, directly into the calendar schedule" — read as instant | Yes | Included |

The market draws a real line between **instant** (the client's pick is the
final answer) and **request-then-confirm** (staff accept before it lands),
and several products let a practice choose per visit type. SAIRNvet's
"Client Requests" panel is the back half of request-then-confirm — the
staff-side accept queue — with no client-facing front half at all.

### 2.4 Mid-market / multi-location (Gap 4)

| Vendor | What the vendor-domain snippet states |
|---|---|
| **VIA** (Antech/Mars) | "utilize one patient chart no matter how many locations a patient visits"; inventory "tracked by individual location but receive centrally… maintain individual price structures per location"; roll-up or per-location reporting |
| **Provet Cloud Enterprise** | Central catalogue push ("update a medicine price… push it to every clinic instantly") with location-specific permissions and four default permission groups; "real-time inventory visibility across all sites and automated low-stock alerts" |
| **Shepherd Multi-Location** | "group-level administration, inventory control, and reporting, all from one centralized admin portal", stated as included "at no extra cost" |
| **ezyVet Enterprise** | "standardize system-wide changes across multiple locations at the push of a button"; a "centralized inheritance" configuration controls how data syncs to sites |
| **Digitail Vet Groups** | A cited case study: "centralized inventory… stock-level tracking from the main pharmacy… Each facility can manage its stock independently, while… leadership can see the big picture across all units" |
| **Instinct Corporate Groups** | States it lets a group "standardize digital treatment sheets, patient boards, anesthesia monitoring, and charge capture while keeping their current PIMS" — a layer *over* existing systems, not a replacement |

A consistent shape across every vendor: one patient chart followed across
sites; a central catalogue (products, prices, forms) pushed to sites with
location-level overrides and location-scoped permissions; inventory tracked
per location but received or purchased centrally with reorder points; and
roll-up or drill-down reporting. Pricing language is moving toward **no
per-site penalty** (Provet's own phrase), which removes a lever a smaller
entrant could otherwise compete on.

### 2.5 Inventory, specifically

`ezyVet`, `Covetrus Pulse`, `Provet Cloud`, `Shepherd` and `Vetspire`
vendor-domain snippets all state reorder points, low-stock alerts and at
least one named supplier integration (Covetrus, Vetcove, MWI, CUBEX
cabinets). A standalone product, **Inventory Ally**, states integration with
nine named PIMS including Shepherd, ezyVet, Digitail, Vetspire and Provet,
and "recalculates optimal reorder points and safety stock weekly" — evidence
that inventory-with-reorder is now table stakes even for PIMS that do not
build it natively.

### 2.6 Pricing landscape (vendor-domain pricing-page snippets only)

| Vendor | Model | Published figure |
|---|---|---|
| Digitail | Per full-time DVM | "starts from $300 per full-time DVM, additional vets $150" |
| ezyVet (US) | Tiered monthly | "starts at $260.50 per month" |
| IDEXX Neo | Base + per user + per location | Base includes first 3 users; additional charge per user and per location; figures not published |
| Weave (comms add-on) | Flat | "$199/mo" |
| Vetology AI | Flat, per report tier | "$200/month ($2,000/year)" for 50 AI reads (see §2.1 caveat) |
| SignalPET | Per report | Radiologist Routine "starts at $60", STAT "starts at $100"; AI tier price not published |
| Provet, Shepherd, VIA, Vetspire, Antech, Radimal | — | **Not published** on the vendor domain as retrievable in this pass |

---

## 3. What this means against SAIRNvet's four gaps

**Gap 1 — radiograph screening.** Building a classifier is the wrong first
move on two counts: it is the most patent-dense category surveyed (§5), and
every credible competitor's own posture is decision-support-with-a-human-
backstop, which the market's own July-2026 clinical-fitness scrutiny (§6) is
now actively testing. The cheap, defensible, market-matching step is
plumbing, not modelling: attach the actual image to the existing study
record, add a DICOM/PACS hand-off so a study can be sent to a third-party
reader and the signed result returned into the record, and gate the result
behind a clinician-acceptance step in the same shape as the scribe's. That
is the shape every vendor above actually ships underneath its AI marketing.

**Gap 2 — treatment-to-invoice.** The two mechanisms vendors describe both
depend on one structural change SAIRNvet does not have: an invoice line item
that references the clinical event it came from. SAIRNvet already has the
source events — the dose-audit trail, lab results, surgery records — so the
missing piece is a line-item invoice model and a completion hook, not new
clinical data collection.

**Gap 3 — client-facing booking.** A request-mode portal that writes a
pending row into the real schedule is the smallest build that the market
would recognise as "online booking" at all; instant mode requires exposing
live per-resource availability, which SAIRNvet's 42 synced resources could
plausibly support once a booking record exists. Standalone booking products
are priced flat per location in the one region with published pricing
(€149–€349/month), which is evidence this could be sold as an add-on rather
than bundled if SAIRN chooses.

**Gap 4 — mid-market.** The sequence every vendor's architecture implies:
a location key on every clinical record, an owner-to-patient relation, then
per-location inventory with reorder points, then a central catalogue with
site overrides, then roll-up reporting. SAIRNvet has none of the first two,
which is why nothing above them is buildable yet — this matches the internal
audit's own framing exactly. Supplier-ordering integration is an ecosystem
dependency and is concentrating: the Covetrus–MWI merger (§6) reduces the
number of nationwide distributors to two, which narrows who a future
inventory feature would need to integrate with rather than widening it.

---

## 4. What SAIRNvet has that this pass found no competitor stating

Two items, checked against every vendor-domain snippet gathered:

1. **A deterministic, model-independent contraindication gate** on the drug
   formulary. Every AI-dosing claim found in this market sits inside imaging
   or documentation; no vendor-domain snippet in this pass described a
   species-and-drug contraindication check that runs *outside* the model and
   cannot be silently bypassed by it. SignalPET's radiograph routing and
   Vetology's "the veterinarian can disagree, edit, or set aside any finding"
   are both post-hoc human review, not a hard gate before a dangerous
   combination reaches the record.
2. **A two-person witness lock on a controlled-substance write**, keyed to a
   prescriber tier rather than a role string. No vendor-domain snippet
   gathered for this pass described a second-signature requirement on a
   controlled-substance entry; the closest analogue is IDEXX's or Antech's
   human-radiologist review of an AI finding, which is a different control
   on a different kind of record.

Neither of these should be treated as confirmed unique without the same
follow-up pass this document already asks for in §0 — but they did not
surface once across roughly twenty vendor domains searched.

---

## 5. Patent screen — unverified, no conclusion drawn

Google Patents and USPTO domains were blocked identically to vendor domains.
Every entry below is a **third-party index snippet** (Justia, USPTO Gazette
excerpts surfaced via search), not an opened patent page. No infringement
conclusion is drawn from any of them; each needs a direct read before it
informs a build decision.

**AI veterinary radiograph classification** (the family most relevant to Gap
1): a cluster of related US grants (10,593,041; 10,949,970; 11,735,314 B2;
11,545,267) titled around "methods and apparatus for the application of
machine learning to radiographic images of animals", with one continuation
(12,046,357, an explainability mechanism highlighting which images drove a
classification) indexed to assignee **SignalPET, LLC**. A separate grant
(12,488,462, from a 2021 filing) indexes to assignee **Mars, Incorporated**.
A University of California grant (12,068,077 B2) covers AI detection of
canine left atrial enlargement specifically. **The assignee attribution
across this cluster is not internally consistent in the snippets gathered
and must be resolved by opening the actual patent family tree before any
design decision** — this document deliberately does not resolve it.

**Ambient clinical documentation**: no veterinary-specific ambient-scribe
patent surfaced for any named vendor in this search. The dense prior art
found is entirely human-medicine (Nuance Communications, later assigned to
Microsoft Technology Licensing — several grants on "automated clinical
documentation" and "capturing structured note content from recorded audio").
Whether any of that family's claims reach a veterinary ambient-scribe
implementation is exactly the kind of question this session cannot answer
without opening the claims themselves.

---

## 6. Market signals, 2025–2026 (third-party unless the URL is the named
company's own site; none independently fetched in this pass)

- **IDEXX acquired CoVetAI** (an ambient-scribe vendor), announced
  2026-09-16; the acquirer's own release states CoVet "will also keep
  working with non-IDEXX practice management systems" — a scribe vendor
  choosing to stay PIMS-agnostic even after acquisition by a PIMS vendor.
- **Instinct Science acquired ScribbleVet**, 2026-01-16, positioning a
  combined "clinical intelligence platform" (scribe plus a drug-reference
  tool plus PIMS).
- **Covetrus and MWI Animal Health announced a merger**, 2026-02-18 (a
  reported $3.5B enterprise value for MWI); third-party coverage notes this
  would leave two nationwide veterinary distributors rather than three,
  pending regulatory approval — directly relevant to any future SAIRNvet
  supplier-ordering integration (§2.5).
- **Zoetis agreed to acquire VitalRADS**, a teleradiology service covering
  25+ species, closing reported July 2026, described as adding
  "AI-assisted report generation" to a "Virtual Reference Lab".
- **A JAVMA study, reported by VIN**, evaluated six AI radiology platforms
  (including RapidRead, SignalPET and Radimal by name) and concluded the
  group was "unfit for clinical use overall" on the study's own criteria,
  with vendors disputing the conclusion; the same coverage states AI is
  measurably better at confirming normal studies than at detecting
  abnormalities — a caution worth carrying into any SAIRNvet radiograph
  design, not just a market fact.
- **AVMA's House of Delegates, reported July 2026**, is described as
  stating that members are "not comfortable when AI is positioned as an
  independent clinical decision maker", alongside forming a Task Force on
  Emerging Technologies — the professional body's own body language matches
  every vendor's "decision support" framing in §2.1, which suggests that
  framing is now closer to a requirement than a marketing choice.
- **VIN member polling**, cited third-party, shows AI-scribing use among
  respondents rising from roughly 3.5% (July 2024) to 17.5% (September
  2025) — directional evidence that SAIRNvet's own scribe is arriving on
  the early side of adoption, not the late side.

---

## 7. What this document does NOT establish

- **No vendor page was opened directly, at all, in this pass.** Every claim
  above is a search-engine snippet of a vendor's own domain. This is stated
  once in §0 and repeated here because it is the single fact that most
  changes how this document should be used: as a map of what to verify, not
  as verified fact to quote externally.
- **No patent claim was read.** §5 names candidates for a real screen; it
  performs none.
- **No competitor product was used, demoed, or tested.**
- **No pricing figure here should be quoted to a prospect** until re-read
  from the live page.
- This document does not decide whether SAIRNvet should build any of the
  four gaps, in what order, or at what cost — that is a
  `sairn-software-architect` and `sairn-decision-gate` question, same as the
  StoneDesk reference audit's own §7 declines to decide its gaps.

---

## 8. Decay

Every fact in this document is a search-index snapshot from 2026-09-25 of
pages this session could not open. It will decay faster than a normal
competitive audit for that reason alone, independent of the market moving.
**Do not treat any cell here as current without re-reading the source page.**
The one action this document asks for, ahead of any competitive finding: run
this pass again from a network that can reach vendor and patent-office
domains, and only then decide what — if anything — to build.
