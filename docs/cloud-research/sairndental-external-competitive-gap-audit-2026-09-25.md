# Worldwide external competitive-gap audit — SAIRNdental

**Sourcing caveat, read this before anything else below:** this session's
outbound network could not reach any vendor, trade-press, or patent-office
domain. Every vendor-attributed fact in this document is a `WebSearch`
index snippet of that vendor's own domain, not an opened page — one grade
below this series' normal standard. Full disclosure and the direct test
evidence are in §0.

**Correction to this document's own request, stated first because it
shapes everything below:** the task that produced this document described
the existing internal dental competitive work as a "combined
roofing+dental+senior audit from Aug 26, dated and shallow on dental
specifically." Having now read it in full
(`docs/superpowers/specs/2026-08-26-competitive-gap-audit-roofing-dental-senior.md`
§4), **that is not an accurate description.** The dental section is
substantive: seventeen named tables checked against nine Tier A and five
Tier B gap categories, real named competitors (tab32, Archy, CareStack,
Curve, Denticon, Dentrix Ascend, DentalXChange, Vyne Trellis, NexHealth,
Weave, RevenueWell, Solutionreach, Planet DDS), and thirteen non-English
regulation-driven findings including a genuinely surprising one (Italy
*prohibits* routing patient healthcare invoices through its SdI
e-invoicing system, the opposite of what an engineer might assume from
that country's general e-invoicing mandate). **It is dated — a month old
as of this pass — and it is genuinely thin on four specific vendors this
task named by name** (Dentrix's classic/on-premise product specifically,
as opposed to Dentrix Ascend which it does cover; Eaglesoft; Open Dental;
and a deeper Curve Dental profile), **and on patient-portal depth, which
it does not cover at all.** This document's real job is those four gaps
and a freshness check, not a re-audit of ground already covered well.

**Research pass, 2026-09-25. No code written, no app file touched.**
Written by a standalone cloud session under `docs/cloud-research/` per
instruction (new files only, new branch, no PR).

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
`opendental.com` against a healthy proxy status (`enabled: true`,
`bundleCoversEveryHost: true`, zero recent relay failures — a fresh proxy
instance, the same pattern seen in every other session in this series
today, confirming a persistent destination-level policy, not a fault).
Per the proxy documentation's own instruction on a blocked host — *"Do not
retry or route around it — report the blocked host"* — that instruction is
followed here.

**Evidence grade**: every vendor-fact cell below is a `WebSearch` result
restricted to the named vendor's own domain via `allowed_domains` — the
search engine's indexed excerpt of that page, not the page itself. **This
matters more than usual in this document specifically, because it covers
HIPAA-adjacent claims (minimum-necessary access, PHI handling) — nothing
below should be read as legal or compliance advice, and nothing here
substitutes for the counsel review `docs/SAIRN-OPEN-WORK-INDEX.md`
already flags as required before any SAIRNdental customer agreement is
signed.** Pricing figures are taken only from a vendor's own published
page; where none exists, that absence is reported as fact.

Retrieval date for every row below: 2026-09-25.

---

## 1. What SAIRNdental is, anchored to the existing internal work — not
re-derived here, with two live corrections

From `docs/2026-09-17-sairndental-competitive-gap-rederived.md` (a full
caller-level re-derivation against the code at HEAD) and a direct check of
`api/sd-data.js` performed for this pass specifically:

- **CDT annual code maintenance is BUILT and hardened beyond what the
  original 08-26 audit found.** That audit found *"no
  versioned-code-catalogue-with-effective-dates concept."* The 09-17
  re-derivation found it closed: `cdt_version` is a real field, and — the
  harder, more recent piece — **posted charges are now also versioned**,
  so a historical charge re-reads the CDT code as it stood at the time it
  was posted, not whatever the catalogue says today. This is the specific
  mechanism §2.4 below checks against the market.
- **Good-faith estimates, recall/reactivation, treatment planning,
  consolidated RCM/denials, and open BI connectors are all BUILT**, each
  with a real panel, schema, and (for GFE specifically) 237 markers —
  this app is not a thin shell against a market with real depth.
- **Enterprise credentialing has a real foundation but is not payer
  enrolment.** `dnt_cred_rules` + `dnt_credentials` (state licences,
  DEA/MATE, CE pacing) are built and wired — but that is per-employee
  credentialing, which is a different problem from getting a provider
  onto an insurance panel. The original audit called this distinction out
  explicitly and it still holds.
- **Cross-location roll-up reporting is a genuinely unusual state, not an
  ordinary open gap.** The aggregation engine is fully built server-side
  — reviewed twice, both findings closed, real tests — but has **zero
  callers**: `dnt_rollup` is the one resource, of twenty-five registered,
  that no client file names anywhere. `docs/SAIRN-OPEN-WORK-INDEX.md`
  currently says BUILT for this feature with no caller and no note that
  there isn't one — the 09-17 document treats this as a decision to make
  (build the one remaining panel, or write the deferral down), not a
  defect to silently carry.
- **Real-time insurance eligibility, X12 837D/835/clearinghouse
  integration, imaging/CBCT/intraoral integration, and e-prescribing/
  EPCS/PDMP all remain genuinely absent** — zero markers, confirmed
  unchanged from the original audit. Three of these four are gated by a
  vendor relationship or federal certification, not an engineering
  decision the app can make alone.
- **First correction this document makes to a standing record**:
  `docs/SAIRN-OPEN-WORK-INDEX.md`'s dental BAA row, last substantively
  updated 2026-08-27, states *"minimum-necessary tiering is deliberately
  deferred — all three roles can currently reach all patient data."*
  **That is no longer true, checked directly against `api/sd-data.js` for
  this pass.** A real, live scoping mechanism (`DNT_PATIENT_SCOPED_RESOURCES`,
  covering `dnt_patients`, `dnt_referrals`, `dnt_gfe`,
  `dnt_recall_outreach`, `dnt_txplans`, and `dnt_denial`) restricts a
  `provider` role's reads to only the patients linked to that specific
  provider — via `dntPatientIdsForProvider` — while owner and front-desk
  roles keep practice-wide visibility, a deliberate and justified
  exception (*"the front desk has to be able to find any patient to book
  or check one in, which is the job"*). A provider whose sign-in is not
  yet linked to a provider record gets an explicit `PROVIDER_NOT_LINKED`
  error rather than a silent empty result. **This is a real
  minimum-necessary-style access control, live in the code, that the
  standing open-work record has not caught up to** — worth a one-line
  update there independent of this document, since a BAA reviewer reading
  that row today would be told something the code no longer does.
- **Second correction, smaller**: the referral-visibility fix
  (`docs/SAIRN-OPEN-WORK-INDEX.md`, closed 2026-09-11) is the concrete
  shape of "provider link/edit paths" this task's own brief referenced —
  an unlinked referral is deliberately visible to every scoped provider
  role rather than invisible to all of them, with a per-row Link control
  that resolves it, and linking never overwrites the front desk's typed
  name.

---

## 2. What the market does, against each open item

### 2.1 Four fresh vendor profiles — Dentrix (classic), Eaglesoft, Open
Dental, Curve Dental

| Vendor | Pricing model | CDT annual updates | Imaging integration |
|---|---|---|---|
| **Dentrix** (Henry Schein, classic/on-premise — distinct from Dentrix Ascend, already covered internally) | Not published; bundles described without dollar figures. A separate Dentrix Ascend API-access add-on is priced at $47/month per location, which is Ascend, not classic Dentrix. | **Automatic** — an in-product CDT updater (since Dentrix G7.5) installs ADA changes automatically for customers with an active service plan; manual entry otherwise. No evidence found of historical-charge code preservation as a named feature. | Curated-partner model: named "Smart Image" connectors for DEXIS and Planmeca (Romexis), a "Dentrix Connected" 3Shape TRIOS integration; Carestream not prominently documented in what was found. |
| **Eaglesoft** (Patterson Dental) | Not itemized; bundled into a 24-month "Service Club" membership, license included at no extra line-item cost. True per-seat cost is quote-gated. | **Not found.** No specific CDT-update-mechanism page surfaced — genuinely unknown, not confirmed absent. | Broad partner-bridge model: direct bridges to Dentsply Sirona Sidexis and KaVo Kerr DEXIS, plus Planmeca, Air Techniques, Instrumentarium, Soredex, Progeny — vendor-provided/vendor-supported bridges, not an open API. |
| **Open Dental** | **Published**: $199/month per location (first 12 months, reduced month-to-month after), covering up to 3 dentists per location, all computers at that location, updates, and support. The most concretely published price found in this entire pass. | Version-driven, semi-manual: new CDT codes ship in the year's last stable release; users then run "Procedure Code Tools" to pull ADA descriptions in — ADA text auto-updates in place through that tool. No evidence of as-posted historical preservation; the in-place update mechanic is closer to the failure mode SAIRNdental's own fix addresses, though this is inferred from the mechanism described, not a directly confirmed gap. | **The strongest hybrid found**: published bridges (Carestream, including a distinct Ortho/OMS bridge; Dexis Integrator; Patterson Imaging; ClioSoft/SOTA) plus a stated developer API that "authorized vendors use," persisting across version updates — closer to a real documented API than any other PM vendor covered in this pass, though still partner-gated for write access. |
| **Curve Dental** | **Published**: $200/month for 1 dentist, +$100 per additional dentist, with a custom quote for more complex configurations. Second-most concretely published price in this pass. | **Automatic, cloud-native** — vendor states updates happen "quietly overnight" with no downtime, framed as a cloud-native advantage over on-premise patching. No specific as-posted-preservation claim found. | Broad compatibility claimed (DEXIS, Planmeca Dimaxis/Romexis, Kodak/Carestream, Patterson Imaging, Sirona Sidexis, Air Techniques Visix) via "direct integrations and TWAIN driver support" — a partner network, not an open developer API. |

**Only Open Dental and Curve Dental publish real prices; Dentrix and
Eaglesoft are both quote-gated behind bundled service plans**, consistent
with a legacy-on-premise-vendor pattern this series has now seen in other
verticals (roofing's AccuLynx/JobNimbus versus Roofr's published tiers is
the closest parallel). All four use a curated-partner/bridge model for
imaging rather than a genuinely open API — §2.3 below has an important,
freshly surfaced exception to that general pattern.

### 2.2 Patient portal depth — a genuinely new area this pass covers, not
in the original internal audit at all

| Vendor | Online scheduling | Secure messaging | Digital intake | Bill pay | Treatment-plan visibility | Patient imaging access |
|---|---|---|---|---|---|---|
| Dentrix | Yes, 24/7 (Patient Engage) | Two-way texting | Implied via Patient Engage suite | Yes (Dentrix eCentral, tokenized card-on-file) | Not found | Not found |
| Eaglesoft | Yes, via Vyne Trellis | Two-way text via Vyne Trellis | Yes (Vyne Trellis / RevenueWell Forms) | Via Vyne Trellis billing | Not found | Not found |
| Open Dental | Yes (Web Sched) | Secure WebMail | Yes (Web Forms, e-signature) | Yes (Payment Portal, free with active support) | Yes — patients can view saved treatment plans | Not found |
| Curve Dental | Yes (self-scheduling platform) | Not explicit (magic-link access) | Yes (Smart Forms) | Not explicit | Not explicit | Not found |
| tab32 | Yes (auto-book or request-based) | Not explicit | Yes (HelloPatient digital intake) | Yes (itemized bill, tap-to-pay, installments) | Not explicit | Not found |
| CareStack | Yes | Yes, 2FA-secured | Yes (form-signing, medical history) | Yes | Yes — patients can view and **sign** treatment plans | Insurance card/EOB *upload* only — the inverse capability |
| Archy | Yes (book new visits) | Not explicit | Not explicit | Yes | Not explicit | Not found; login via Google OAuth |

**Online scheduling, digital intake, and bill pay are confirmed table
stakes — all seven vendors checked have all three.** SAIRNdental has none
of this: zero markers for a patient-facing surface of any kind. Secure
messaging and treatment-plan e-signature are real differentiators at some
vendors (Dentrix, Eaglesoft/Vyne, Open Dental, CareStack) and
unconfirmed at others. **The single most interesting finding in this
section**: patient-facing x-ray/imaging *viewing* access was not found as
a named feature at any of the seven vendors checked — CareStack's closest
analog is patients *uploading* an insurance card or EOB image, the
opposite capability. This reads as a possible market-wide whitespace, not
a SAIRNdental-specific gap, and should be treated as a moderate-confidence
finding (seven vendors, a limited per-vendor query set) rather than a
settled one.

### 2.3 Freshness check — the imaging-API claim has genuinely moved since
2026-08-26, and this is the most important correction in this document

The original audit's finding — *"the only genuinely open documented API
found anywhere in dental was NexHealth's; everything else is a curated
partner marketplace"* — needs a specific, sourced update. A public,
versioned API documentation page now exists for **DEXIS**:
`openapi.cloud.dexis.com/doc/index.html`, "DEXIS Public API documentation
V4.7.11.2," using OIDC/OAuth 2.0 token authentication — real
endpoint-level documentation, publicly browsable, not merely a partner
marketplace listing. **Caveat that keeps this from being a clean
reversal**: obtaining actual credentials still requires emailing DEXIS's
integration team, so access remains gated behind a business relationship
— the API's *shape* is public even though its *use* is not self-service.
3Shape's PMSWEB module (part of 3Shape Unite, a January 2026 release) also
has real API infrastructure — REST endpoints, RFC-9457-compliant error
handling — but its documentation requires engaging 3Shape as a potential
integration partner first, which is more gated than DEXIS's public doc
page. Carestream and Planmeca show no evidence of a public API
documentation page in this pass; Planmeca's Romexis is described only in
terms of older interoperability standards (DICOM/TWAIN/VDDS/PMBridge).
**Revised framing**: NexHealth remains the only fully self-serve open
API; DEXIS is now a step above the pure curated-partner model every other
imaging vendor still uses, with real public docs behind a
still-gated credentialing step.

### 2.4 CDT catalogue-versioning market depth — SAIRNdental appears ahead
of the market, moderate confidence

HIPAA's actual requirement (confirmed via a CMS documentation snippet) is
that the procedure code on a claim be from the CDT version effective on
the *date of service* — the regulatory basis this feature answers, not a
discretionary nicety. Against that requirement: Dentrix updates its
catalogue automatically going forward; Open Dental's ADA descriptions
auto-update **in place** through a tool, which — inferred from the
mechanism, not directly confirmed — would not necessarily preserve what a
historical charge actually said at posting time; Curve Dental's updates
are framed purely as overnight convenience. **No vendor's own marketing
describes "historical charges preserve the code as it existed at posting
time" as a named, marketed feature.** This is an absence-of-evidence
finding, not a positive confirmation the market gets this wrong — a
vendor could have the mechanism without marketing it — and should be
carried as moderate confidence, not proof. On the evidence gathered,
though, SAIRNdental's now-built discipline here (§1) reads as ahead of
what any of the four freshly profiled vendors visibly do.

### 2.5 Freshness check — enterprise credentialing/payer enrolment, the
whitespace is narrowing, not closed

Real 2025–2026 movement exists and should soften the original audit's
"nobody has won this category" framing:

- **Overjet** launched a credentialing-automation suite in late 2025,
  bundled with its existing imaging/AI platform — a new, well-funded
  entrant, not a scrappy point solution.
- **Sy.Med**, a general healthcare-credentialing vendor, expanded into
  dental with "Sy.Med OneApp," signing large accounts including Aspen
  Dental Management and Heartland Dental Care — a healthcare-credentialing
  incumbent crossing into dental specifically at the DSO tier.
- **Fluent Dental** acquired Delegated DDS (2024) for full-outsource
  delegated credentialing; a newer entrant, **OneExpert**, surfaced
  marketing multi-payer (Delta Dental, Cigna, MetLife, Aetna) credentialing.
- Secondary trade-press sources (not vendor-domain, lower confidence)
  frame verification automation as reaching "commodity status" with
  competitive action shifting to credentialing specifically, and note
  CAQH's June 2026 rebrand to "DataSpring, powered by CAQH."

**No evidence found that any core PM vendor (tab32, CareStack, Curve,
Archy, Dentrix, Eaglesoft) has natively absorbed payer enrolment** —
still fragmented, still served by a specialist layer, but that layer now
includes a credible, well-capitalized new entrant that did not exist in
the original audit's picture.

### 2.6 Pricing landscape

| Vendor | Published price | Model |
|---|---|---|
| Open Dental | $199/month per location (first year), reduced month-to-month after; up to 3 dentists | Flat per-location subscription |
| Curve Dental | $200/month for 1 dentist, +$100/additional dentist | Per-provider subscription |
| tab32 | "From $125/month" per its own pricing page title | Subscription, low published entry point |
| Archy | No per-seat figure; vendor states pricing is per-location, quote-gated | Flat per-location, quote-gated |
| Dentrix (classic) | Not published; only the Ascend API add-on ($47/mo/location) surfaced | Quote-gated, bundled |
| Eaglesoft | Not published; bundled into a 24-month Service Club term; one promo bundle at $349 (billing frequency unclear from the source) | Quote-gated, bundled |

**Confirms a clear split**: cloud-native/newer entrants (Open Dental,
Curve, tab32) publish real numbers; legacy on-premise incumbents
(Dentrix, Eaglesoft) do not. Open Dental's transparency is the most
concrete pricing found anywhere in this document.

### 2.7 Patent screen

Every entry is a third-party index snippet; no page was opened; no
infringement conclusion is drawn, and this was a shallow index-level
pass, not a clearance search. No patent surfaced covering CDT-code
versioning with historical-charge preservation, provider-scoped
minimum-necessary PHI access modeled the way SAIRNdental implements it, or
dental-imaging-to-PM integration in a way that obviously reads on
SAIRNdental's architecture. What did surface: **US 10,572,625**,
"Combination dental imaging system and dental practice management and
charting system with a bi-directional communication interface" — the
closest hit to imaging-integration architecture generally, not
code-versioning or access-tiering specifically; **US 2022/0304646 A1**, a
cloud/SaaS dental-image-processing patent, imaging-adjacent only; and a
general (non-dental-specific) healthcare "dynamic access control to
electronic patient records" patent family, broader than and not
specifically matching SAIRNdental's provider-linked-patient scoping
mechanism. No patent surfaced for CDT effective-dating or as-posted
historical preservation specifically, consistent with this being a narrow
operational/compliance mechanism rather than a typically patented one.

---

## 3. Market signals, 2025–2026 (third-party unless the URL is a named
company's own site; none independently fetched in this pass)

- **Patterson Companies (Eaglesoft's parent) was taken private**,
  completed April 17, 2025 — acquired by Patient Square Capital for
  roughly $4.1B ($31.35/share cash), a new CEO installed, financed via a
  syndicate of major banks. Multiply-sourced including SEC 8-K filings
  and Patterson's own newsroom — the strongest-sourced single fact in
  this document.
- **Henry Schein** (Dentrix's parent) reportedly has KKR & Co. holding a
  roughly 12% stake with an option toward 15%, its largest non-index-fund
  shareholder — found via general search, not a vendor domain; carry as
  secondary-source, moderate confidence.
- **Archy raised a $50M Series C on September 11, 2026** (JMI Equity led;
  TCV, Bessemer, CRV, Entrée Capital, Alven participating), bringing its
  total funding to roughly $97M since a 2021 founding — recent, specific,
  and well-sourced.
- **Planet DDS (Denticon) is the most product-active vendor found in this
  entire pass for 2025–2026**: "DentalOS AI Agents" (February 2026), "AI
  Voice Perio" (February 2026), "MyTooth" — a native patient-experience
  layer (January 2026) — and a Truro AI integration (July 2026); roughly
  $298M total raised at a roughly $3.1B valuation (Aquiline Capital,
  Level Equity backed); won a 120-location DSO account (Smile Partners
  USA) in May 2026.
- **CareStack's most recent clearly-dated funding figure (roughly $60M)
  traces to December 2024** — just outside this pass's 2025–2026 window;
  nothing more recent surfaced, and this should be flagged as
  stale/unconfirmed for the current period rather than restated as
  current.
- **tab32, Curve, and Open Dental**: no funding or M&A news surfaced in
  this pass — either genuinely quiet, or simply outside what
  search-indexed press covers for smaller/bootstrapped vendors.

---

## 4. What this means for SAIRNdental, in priority order

Reading §2 against §1's own internal grounding:

1. **The cross-location roll-up's missing caller is the highest-priority
   item this pass reconfirms, unchanged from the internal 09-17
   document** — a fully built, twice-reviewed server engine with zero UI
   reachability is a decision waiting to be made (build the one panel, or
   write the deferral down), not a new finding this external pass adds,
   but nothing here softens its urgency either.
2. **A patient portal is a genuine, high-confidence gap this pass newly
   surfaces** (§2.2) — online scheduling, digital intake, and bill pay
   are confirmed table stakes across every vendor checked, and
   SAIRNdental has zero markers for any patient-facing surface. This is
   the single clearest net-new finding in this document.
3. **The two corrections to standing records (§1) are worth acting on
   independent of any build decision** — the BAA row's "minimum-necessary
   deferred" language is now inaccurate against the live code and should
   be updated so a counsel reviewer isn't told something the app no
   longer does; this is a documentation fix, not an engineering one.
4. **CDT catalogue-versioning (§2.4) is a real, evidenced strength**,
   though moderate-confidence rather than proven, since it rests on an
   absence of competitor marketing rather than a positive failure
   confirmed at a named vendor.
5. **The imaging-API landscape has genuinely shifted (§2.3)** and the
   internal record's "only NexHealth" framing should be updated to
   reflect DEXIS's new public (though still credential-gated) API
   documentation — this doesn't change SAIRNdental's own posture, but it
   changes what a future imaging-integration decision would actually be
   choosing between.
6. **Enterprise credentialing/payer enrolment (§2.5) remains correctly
   un-built** — still fragmented market-wide, though a well-capitalized
   new entrant (Overjet) means "nobody has won this" is no longer quite
   accurate and should be watched rather than treated as permanently
   settled whitespace.
7. **Real-time eligibility, X12/clearinghouse, full imaging integration,
   and e-prescribing remain correctly out of scope for an engineering
   decision alone** — each is gated by a vendor relationship or federal
   certification the original audit already identified correctly.

---

## 5. What this document does NOT establish

- **No vendor page was opened directly, at all, in this pass.** Every
  claim above is a search-engine snippet of a vendor's own domain,
  including the DEXIS API-documentation finding in §2.3 — the
  documentation page's *existence and URL* were confirmed via search
  index, not by opening and reading the API spec itself.
- **No patent claim was read.** §2.7 is an index-level screen, not a
  clearance search.
- **No competitor product was used, demoed, or tested.**
- **No pricing figure here should be quoted to a prospect** without
  re-confirming from the live page — Open Dental's and Curve Dental's
  figures are the most concrete found, and even those should be
  re-verified before being repeated in a proposal.
- **Nothing in this document is legal or compliance guidance.** The
  minimum-necessary-tiering correction in §1 describes what the code
  currently does; it is not a HIPAA compliance opinion, and the standing
  requirement for counsel review before any SAIRNdental agreement is
  signed (`docs/SAIRN-OPEN-WORK-INDEX.md`, the BAA row) is unaffected by
  anything found here.
- **§2.2's patient-imaging-access whitespace finding and §2.4's
  CDT-versioning finding are both absence-of-evidence findings**, not
  positive confirmations — a vendor could have either capability without
  marketing it, and both are stated as moderate confidence for that
  reason.
- This document does not decide whether SAIRNdental should build any of
  the items in §4, in what order, or at what cost — that is a
  `sairn-software-architect` and `sairn-decision-gate` question, same as
  this series' own precedent declines to decide the gaps it finds.

---

## 6. Decay

Every fact in this document is a search-index snapshot from 2026-09-25 of
pages this session could not open, layered on internal documents that are
themselves dated (2026-08-26 and 2026-09-17) and have already been shown
in this pass to need at least two corrections (the imaging-API landscape,
the minimum-necessary-tiering status). **Do not treat any cell here as
current without re-reading the source page and re-deriving the internal
state.** The one action this document asks for, ahead of any competitive
finding: run this pass again from a network that can reach vendor and
patent-office domains, and separately, route the minimum-necessary-tiering
correction in §1 to whoever owns `docs/SAIRN-OPEN-WORK-INDEX.md`'s dental
BAA row, since it is a factual correction independent of anything this
document recommends building.
