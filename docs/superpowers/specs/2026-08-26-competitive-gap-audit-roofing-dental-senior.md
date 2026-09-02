# Worldwide competitive-gap audit — SAIRNroofing, SAIRNdental, SAIRNsenior

Research pass, 2026-08-26. **No code written, no app file touched.** Findings only.
Nothing here is a build decision; §7 lists what a build pass would need to settle
first.

---

## 0. Two corrections to the premise this audit was requested under

**0.1 — "the same treatment every other app got" is not accurate, and this is the
second time it has been corrected.**

The request named ten apps (StoneDesk, SAIRNbuild, SAIRNvet, SAIRNlaw,
SAIRNlegacy, SAIRNbiz, SAIRNgrounds/SAIRNscape, SAIRNcash, SAIRNcode, SAIRNcare)
as having already received a worldwide competitive-gap audit. Checked rather than
accepted:

- 59 spec docs in `docs/superpowers/specs/`. Exactly **three** name any real
  competitor product: `2026-08-21-plumbing-electrical-hvac-worldwide-research.md`,
  `2026-08-24-sairnroofing-v1-scope.md`, `2026-08-26-ip-screen-roofing-delta-and-deadline-engine.md`.
  Two more files outside specs/ do (`SAIRNBUILD-SCOPE.md`, `SAIRN-BACKLOG.md`).
- Commit `e94fce0` (SAIRNcare v2.0) ends with "Worldwide competitive audit
  complete." **No such document exists on disk**, in this clone or in
  `SAIRN-hank`, `SAIRN-cc`, or `SAIRN-cody` (all four checked).
- The identical correction is already recorded in `f48c359` (2026-08-24):
  *"the request described it as 'the same audit every other app already got,' and
  no such audit exists for any app."*

So this is the **second** audit of its kind, not the eleventh. The first was
SAIRNroofing's own scope doc. Recording it again because a commit-message claim
("audit complete") with no artefact behind it is exactly the tracking-table-cell
failure `sairn-master-orientation` rule 11 describes, and it has now survived two
sessions.

**0.2 — SAIRNroofing has already had a partial pass; it is not untreated.**

`2026-08-24-sairnroofing-v1-scope.md` §2 contains a real competitive section
(JobNimbus, AccuLynx, Roofr, Leap, SubcontractorHub, iRoofing, ServiceTitan, the
German *Aufmaß* pattern) and §1 contains a genuine patent screen. It is **thin
against the standard asked for here** — one tier, US-only, no per-gap
categorisation, and it says so itself: *"no verifiable French, Spanish/LATAM,
Japanese or Nordic roofing-specific products were found in this pass."* This
audit extends it rather than replacing it. SAIRNdental and SAIRNsenior have had
nothing.

---

## 1. Method, and the coverage limit that shaped this pass

Six parallel research lanes: {roofing, dental, senior} × {English, non-English}.
Both tiers required in every lane (Tier A = small business; Tier B = mid-market /
100+ employees).

**A hard tooling limit hit five of six lanes and must be read before anything
below is quoted externally.** WebSearch runs on a **session-wide shared budget**
that was exhausted (200/200) partway through. Consequences, stated rather than
smoothed:

| Lane | Search coverage | Effect |
|---|---|---|
| Roofing EN | Full | Clean |
| Roofing non-EN | Full | Clean |
| Dental EN | Exhausted in 3 of 4 sub-streams | Forum sentiment + patents thin |
| Dental non-EN | Exhausted mid-pass | **Nordic + Polish native search never ran at all** |
| Senior EN | ~20 queries then cut | State-by-state regulation **not covered** |
| Senior non-EN | ~9 native queries then cut | **Denmark, Poland, Brazil are gaps**; zero patent search |

Additionally blocked to automated fetch across lanes: **CMS.gov, DOL.gov, Federal
Register, USPTO Patent Public Search, Google Patents, CourtListener, Justia,
Reddit, Dentaltown, G2, NACHC, KLAS.**

Throughout, **"no coverage found" means not searched or not reachable**, and is
kept distinct from *searched and absent*. Nothing was filled in from memory.

**Gap computation is local and verified, not inferred from the research.** Every
"SAIRN* does not have X" claim below was checked against the real files at HEAD.
Two false findings were caught and killed this way and are recorded in §6.

---

## 2. Patent-safety posture

Per standing rule, every gap below is named as a **functional capability
category** a buyer would recognise. No competitor UI flow, algorithm, data model,
or screenshot is described anywhere in this document, and none was requested from
the research lanes. Anything built from this must be built from scratch.

Live IP hazards found are in §5 and are **flagged, not analysed** — no
infringement opinion is offered or implied.

---

## 3. SAIRNroofing

**Built and verified at HEAD:** 14 tables (`rf_jobs`, `rf_photos`, `rf_cert_rules`,
`rf_certifications`, `rf_claims`, `rf_claim_photos`, `rf_contingency_rules`,
`rf_claim_agreements`, `rf_locations`, `rf_schedule`, `rf_company_programs`,
`rf_proposals`, `rf_invoices`, `rf_settings`); 6 nav panels + jobs/measurement/
estimate/proposal flows. US-only, Ohio seeded. `location_id` is **attribution
only, deliberately not an access-control axis** (`api/_lib/roofing-locations.js`).

### 3.1 Market structure — the finding that reframes the target

The v1 scope doc targets "the 20–100-employee multi-location roofer squeezed
between cheap-and-shallow and enterprise-and-expensive." The research materially
sharpens who that buyer now *is*: **PE-backed roofing platforms grew from 17
(start 2023) to 56 (end 2024), and PE-backed firms are now 7 of the top 10 largest
US roofing contractors.** Named consolidators: Tecta America, Nations Roof,
Infinity Home Services, Omnia Exterior Solutions (CCMP), Peak Roofing Partners
(Exuma). *(Source type: M&A-advisory content, self-interested — directional, not
authoritative.)* ServiceTitan already markets "M&A integration built for
high-growth operators" at exactly this buyer.

**Consequence for the v1 target:** the mid-market roofer is increasingly a
multi-entity rollup, not a single company with branches. That is a different
data-model problem from `location_id`-as-attribution.
[Roofing Contractor](https://www.roofingcontractor.com/articles/101235-tariffs-talent-and-tech-the-new-rules-of-roofing-consolidation)

### 3.2 Gaps — Tier A (small business)

> **RE-VERIFIED IN FULL 2026-09-02 (Cody). The column holds. The doubt raised
> against it did not, and that correction is the useful part.**
>
> I reported to Michael that A1 and A2 "look mislabeled as gaps when they're
> built", on the strength of a two-item spot check: `api/_lib/roofing-programs.js`
> and `rf_schedule` both exist and both predate this audit. **That was my error,
> not the audit's.** Reading the state column properly, it already says
> `rf_company_programs` models company programmes and distinguishes that from
> warranty registration, and it already says `rf_schedule` exists and marks A2
> **partially closed**. I had conflated "a related table exists" with "the gap
> is closed" — the same shape as every stale-premise finding this session, run
> in reverse.
>
> All twelve roofing rows were then checked against the current file rather than
> the two: **A1 warranty 0 occurrences, A3 no `rf_subs`-class table** (confirmed
> against the full `rf_*` table list), **A5 accounting 0, B1 asset registry 0,
> B3 retainage/POC/certified-payroll 0, B4 safety-programme terms 0, B6 EDI/ASN/
> punchout 0, B7 prequalification/bonding 0.** Every "Absent" is still absent.
>
> One counting nuance, recorded because it is the kind of thing that becomes a
> false finding later: a naive `grep -i edi` returns 16 hits, all of them
> `edit`/`edited`/`editingJobId`. A word-boundary search returns **0**. The
> audit's "Absent" is right; the substring count is not evidence of anything.
> Two of the audit's own hit-COUNTS have since drifted (A3's "23 keyword hits"
> is now 0, B3's "1 keyword hit" is now 0) without changing a single verdict.
> **Treat the counts as dated and the verdicts as current.**


| # | Gap category | Evidence it matters | SAIRNroofing state (verified) |
|---|---|---|---|
| A1 | **Manufacturer warranty registration + certification-gated warranty tiers** | Enhanced/extended warranties are *contractually gated* behind manufacturer certification status (GAF Master Elite / Certified Plus, CertainTeed SELECT ShingleMaster). A real industry forcing-function, not a nice-to-have. [GAF registration](https://www.gaf.com/en-us/resources/warranties/register), [GAF verify](https://www.gaf.com/en-us/roofing-contractors/verify) | **Zero occurrences of "warranty" anywhere in `sairnroofing.html`.** `rf_company_programs` already models company-level manufacturer programmes — this is the natural hook and it is unused for warranty. |
| A2 | **Crew / field-labour scheduling depth** | Named as the market's loudest hole: Roofr called out by name for "zero crew management or scheduling"; SubcontractorHub exists specifically to fill it. Independent confirmation from two directions. [G2 Roofr](https://www.g2.com/products/roofr/reviews?qs=pros-and-cons) | `rf_schedule` exists (Phase 4a, mutable crew days). **Partially closed** — depth vs. the complaint not assessed here. |
| A3 | **Subcontractor management** — scheduling, compliance/insurance-cert tracking, payment | Repeatedly described industry-wide as an afterthought. | 23 keyword hits in-file, but **no `rf_subs`-class table exists**. Not modelled. |
| A4 | **Tool fragmentation as the actual buying trigger** | Tier A roofers stack 3–4 paid tools (measurement + photo doc + proposal + CRM) at a combined ~$400–700/mo because no single product does all of it. *(Third-party estimate.)* | This is a **positioning finding, not a gap** — SAIRNroofing is already single-app. Worth naming because it is the wedge. |
| A5 | **Accounting integration** | QuickBooks-integration absence is a named G2 complaint against Roofr specifically. | Not present. |

### 3.3 Gaps — Tier B (mid-market / 100+)

| # | Gap category | Evidence | SAIRNroofing state |
|---|---|---|---|
| B1 | **Commercial roof asset registry** — multi-building portfolio inventory, condition/remaining-service-life, per-roof service history, **warranty-expiry alerting**, capital/lifecycle budget forecasting | An entire Tier-B-only product category exists for this: Garland RAMP, Tecta TectaTracker, Nations Roof AM, RoofManager, Roof Hoss RoofTrack. **Completely absent from every Tier A product surveyed.** Different data model — many roofs per customer, one contractor servicing hundreds of buildings. [Tecta](https://www.tectaamerica.com/service/roof-asset-management/), [RoofManager](https://www.roofmanager.com/features) | **Absent.** `rf_jobs` is one-job-at-a-time. This is the single largest Tier B structural gap. |
| B2 | **No product bridges Tier A → Tier B here** | The asset-registry tools are commercial-owner/large-contractor only. There is **no "starter" version a growing roofer can adopt when it wins its first maintenance-contract commercial customer.** A real product-tier gap, independently identified. | Open whitespace. |
| B3 | **WIP / percentage-of-completion accounting, retainage, certified payroll** | Present only in general construction ERP (Sage 300 CRE, Viewpoint Vista); **essentially absent from every roofing-specific product surveyed.** Davis-Bacon + state prevailing-wage force certified payroll on any public-works roofing job. | 1 keyword hit total. Not modelled. |
| B4 | **Safety / OSHA programme at scale** — fall-protection plans, anchor-point inspection logs, JHA templates, citation-ready audit trail (photo + timestamp + GPS + signature), training verification | Roofing is a top-3 deadliest US occupation; >80% of roofing fatalities are falls *(secondary, **not verified** against BLS/OSHA primary)*. Dedicated vendors exist (SafetyLoop, SafetyCulture). | OSHA appears **only as a credential type** in the certifications panel (`osha_card`, "OSHA 30"). No safety-programme capability. |
| B5 | **Multi-entity financial consolidation** for PE rollups | See §3.1. ServiceTitan markets M&A-integration tooling directly at this buyer. | `rf_locations` is attribution-only by design. Branch ≠ entity. |
| B6 | **Supplier EDI** (electronic PO / ASN / invoice) vs. simple "order from within the app" | Tier B procurement is EDI-grade. AccuLynx is reported as the only roofing CRM natively connected to all three majors (ABC Supply, SRS, Beacon/QXO) — *secondary source, not verified against the distributors' own partner pages*. [SRS SIPS docs](https://apidocs.roofhub.pro/srs-integration-partner-services-sips-1613923m0) | Absent. |
| B7 | **Prequalification / bonding** | A Tier-B-only category (TradeTapp, Highwire, Constrafor) that exists because GCs and owners require it of bonded subs. | Absent. |

### 3.4 Non-English findings — regulation-driven categories with no US equivalent

The clearest cross-market pattern in the entire audit: **every non-English market
examined has at least one government-mandated, software-relevant category that
simply does not exist in US roofing software.** The forcing function is always a
named law or collective-bargaining structure.

| Market | Capability category | Forcing function |
|---|---|---|
| Germany | Statutory defect-liability (**Gewährleistung**) period tracking per project | BGB civil code + VOB/B contract standard |
| Germany | **SOKA-BAU** pooled social-fund payroll (vacation-pay pooling across employers) | Sector-wide VTV collective agreement |
| Germany | **XRechnung / ZUGFeRD** structured e-invoicing | Federal mandate, phased 2025–2028 |
| Germany | Hazardous-waste electronic manifest (**eANV**) | Nachweisverordnung |
| France | **Garantie décennale** attestation attached to every devis | Code des assurances L241-1; criminal penalty for operating without |
| France | **Carte BTP** worker-identity capture | Loi Macron 2015; €4,000/worker fine |
| France | **Factur-X / Chorus Pro** | National e-invoicing, from 2026-09-01 |
| Spain | **Verifactu / TicketBAI** tamper-evident invoice chaining, regionally forked | AEAT; 2026-01-01 companies / 2027-07-01 autónomos |
| Italy | **DURC di congruità** — per-site labour-cost proportionality filing | National labour-congruity accord, Edilconnect portal |
| Sweden | **ROT-avdrag** 30% labour deduction + XML filing to Skatteverket *by the contractor* | Skatteverket scheme |
| Poland | **KSeF** mandatory e-invoice API | Phased Feb 2026 → Jan 2027 |
| Japan | **CCUS** — national portable worker-credential ledger, cross-employer | MLIT policy; super-generals mandate 100% registration |
| Brazil | **SINAPI / ORSE** official government unit-cost table integration | Public-works budgeting regulation |

**Bearing on SAIRNroofing:** v1 is deliberately US-only and that decision is
recorded. None of the above is a gap *today*. They are listed because (a) the
`rf_cert_rules` / `rf_contingency_rules` "versioned rules as data with a real
citation" pattern already built is **exactly the right shape** to carry any of
them, and (b) the German *Aufmaß* idea already borrowed in the scope doc came
from precisely this well.

**Explicit non-coverage:** no roofing-specific product was found for UK, Ireland,
Australia or New Zealand — general trades platforms (Tradify, Fergus, Simpro)
fill that space. No distinct Canadian product surfaced. Norwegian/Danish and
Polish Tier B were not reached.

---

## 4. SAIRNdental

**Built and verified at HEAD:** 17 tables (`dnt_patients`, `dnt_providers`,
`dnt_operatories`, `dnt_provider_hours`, `dnt_procedure_types`,
`dnt_coverage_rules`, `dnt_appointments`, `dnt_charges`, `dnt_payments`,
`dnt_denial`, `dnt_ar`, `dnt_revenue`, `dnt_settings`, `dnt_referrals`,
`dnt_complaints`, `dnt_cred_rules`, `dnt_credentials`); 17 nav panels.
Multi-location **write-side capture is real and server-side**
(`api/_lib/dnt-location.js`), with reporting/selector deliberately deferred to
`SAIRN-BACKLOG.md`.

### 4.1 Gaps — Tier A (single-location practice)

| # | Gap category | Evidence | SAIRNdental state (verified) |
|---|---|---|---|
| A1 | **Real-time insurance eligibility verification** | Consistently positioned as premium/upper-tier across the market — i.e. a paid differentiator, not baseline. Present in tab32, Archy, CareStack, Curve. | **Zero occurrences of "eligibility".** `dnt_coverage_rules` models coverage but not live verification. |
| A2 | **X12 837D claim submission + 835 ERA auto-posting** | 837D is the dental-specific claim transaction (tooth number / surface / oral-cavity fields + CDT); 835 is the remittance that auto-posts payments *and denials*. HIPAA-mandated transaction set. [Indiana Medicaid 837D](https://www.in.gov/medicaid/providers/files/837d-health-care-claim-dental-transaction.pdf), [CGS 837D](https://www.cgsmedicare.com/pdf/edi/837D_compguide.pdf) | **Zero for 837, 835, ERA, clearinghouse.** (The 130 "ERA" hits were substring noise — see §6.) `dnt_denial` exists but is fed by hand, not by an 835. |
| A3 | **Clearinghouse connection** | Vyne Trellis (800+ payers, ~112M claims/yr), DentalXChange (~1,400 payers, 30+ named PM partners incl. CareStack, Curve, Open Dental, Planet DDS). This is how claims actually leave a practice. [DentalXChange](https://www.dentalxchange.com/) | Absent. |
| A4 | **CDT annual code maintenance** | CDT is republished annually (2026: 60 code changes per trade source). Stale codes create reimbursement *and* audit liability because payment ties to the exact code reported. [ADA CDT](https://www.ada.org/publications/cdt) | `dnt_procedure_types` is practice-entered. No versioned-code-catalogue-with-effective-dates concept. **The `rf_cert_rules` / SAIRNcare payer-rules pattern is the in-house precedent.** |
| A5 | **Imaging / sensor / CBCT / intraoral-scanner integration** | The single most expected integration surface in dentistry. DEXIS, Carestream, Planmeca, 3Shape TRIOS. Notably: **the only genuinely open documented API found anywhere in dental was NexHealth's**; everything else is a curated partner marketplace. | **Zero for imaging / radiograph.** SAIRNdental has photo capture, which is not the same category. |
| A6 | **E-prescribing + EPCS + PDMP** | 21 CFR 1311 requires 2FA, identity-proofing, and 2-year audit trails for controlled substances; PDMP query mandates are state-by-state (~39 states). [DEA EPCS FAQ](https://www.deadiversion.usdoj.gov/faq/epcs-faq.html), [21 CFR 1311](https://www.ecfr.gov/current/title-21/chapter-II/part-1311) | DEA appears **9 times, all credentialing** (DEA/MATE registration tracking, shipped `876bd84`). **No prescribing capability at all** — so the credential is tracked and the act it authorises is not supported. |
| A7 | **Good-faith estimates / No Surprises Act** | Uninsured/self-pay patients must get a written GFE within 3 business days. No federal law mandates specific software, and the ADA has said the standardised-transmission side is still immature for dentistry. *(Trade press covering ADA statements — verify against CMS primary.)* | Zero occurrences. |
| A8 | **Recall / reactivation** | Table stakes in every product surveyed; also the reason the entire bolt-on category (Weave, NexHealth, RevenueWell, Solutionreach) exists — **native PM communication tooling is widely perceived as inadequate**, so practices buy a second product. | **Zero occurrences of "recall".** |
| A9 | **Treatment planning** | Table stakes. Distinct from charging a completed procedure. | Zero occurrences of "treatment plan". `perio` appears 4×. |

### 4.2 Gaps — Tier B (DSO / multi-location / institutional)

| # | Gap category | Evidence | SAIRNdental state |
|---|---|---|---|
| B1 | **Enterprise credentialing & payer-enrolment lifecycle** | **The clearest whitespace in the entire dental audit.** No core PM vendor does it natively — Denticon, Dentrix Ascend, CareStack and tab32 all lack it. The specialist layer (Copliancy, TheCredentialing.com, Fluent Dental, DentalXChange CredentialConnect, I-Enroll) is fragmented, mostly without published pricing or named large-DSO case studies. **Nobody has won this category.** | **Closest thing on the platform already exists**: `dnt_cred_rules` + `dnt_credentials` (state licences, DEA/MATE, CE pacing) shipped `876bd84`. That is per-employee credentialing, **not payer enrolment** — but it is the right foundation and it is already live. |
| B2 | **Cross-location roll-up reporting** | Claimed by every Tier B vendor, **reliably delivered by none**, per their own customers' enterprise-segment reviews. Dentrix Ascend Power Reporting called "a NIGHTMARE" by a multi-location reviewer. Structural to the category, not one vendor's weakness. | Write-side location capture is **done and correct**; reporting is the explicitly deferred half (`SAIRN-BACKLOG.md`). This gap is already scoped in-house. |
| B3 | **Consolidated RCM / denials & appeals workflow** | ~30% of claims across DSOs sit in 90+ day aged receivables *(trade-press podcast claim)*. Every enterprise vendor claims "RCM"/"claim scrubbing"; **none published a concrete denials-and-appeals workflow.** Market-wide gap. | `dnt_denial` + `dnt_ar` exist. No appeals lifecycle. |
| B4 | **Central call centre / missed-call revenue leakage** | Active DSO pain point. Notably, **generic enterprise contact-centre platforms have no evidenced dental presence** — the field is small AI-native startups (VoiceStack, Arini, Viva AI). | Out of scope today; recorded as a category, not a recommendation. |
| B5 | **Open BI / data-warehouse connectors** | tab32 Summit's Tableau/Power BI/Looker connectors are a genuine Tier B differentiator. | Absent. CSV export only. |

### 4.3 Non-English findings

The deepest structural divergence found anywhere in this audit:

- **Germany — dual statutory/private billing.** BEMA (statutory) and GOZ
  (private) are two parallel code catalogues, two pricing mechanisms, two
  submission channels, in one clinic. Plus **KZV quarterly settlement** (batched
  claims on a quarterly cycle with hard deadlines and per-period point values),
  **HKP insurer pre-approval** as the *default legal pathway* for prosthetics
  (not a prior-auth edge case), and a GOZ duty to notify the patient if actual
  cost exceeds the estimate by >15%. US dental uses one CDT set across all payers.
  [KZV Berlin](https://www.kzv-berlin.de/fuer-praxen/abrechnung/allgemeine-informationen),
  [KZVN](https://www.kzvn.de/starterpaket/ihre-abrechnung-mit-der-kzvn/)
- **National claim rails with government approval gates.** France **SESAM-Vitale**
  — the software itself must hold CNDA agrément and GIE homologation; a product
  cannot legally transmit without passing a government body. Japan **レセコン** →
  SSK/国保連, plus mandatory オンライン資格確認. Netherlands **Vecozo** with
  Vektis MZ301/MZ302. Korea **HIRA** (mandatory status unconfirmed).
- **Germany TI / gematik.** TI connector or gateway, **KIM** secure messaging,
  and **ePA integration mandatory for dental practices since October 2025**.
  Reimbursement is conditional on maintaining current mandatory-application
  versions. [gematik](https://www.gematik.de/anwendungen/epa-fuer-alle/zahnarztpraxen), [KZBV](https://www.kzbv.de/zahnaerzte/digitales/telematikinfrastruktur-ti/)
- **France Ségur.** State *co-funds* compliant upgrades (SONS), covering 38,000+
  dentists: DMP/Mon espace santé, INS national patient identifier, MSSanté,
  e-prescription, ProSanté Connect. DMP referential legally binding by arrêté
  2023-10-26. [esante.gouv.fr](https://esante.gouv.fr/segur/chirurgiens-dentistes)
- **Health-data hosting certification as an infrastructure prerequisite.** France
  **HDS** is mandatory, COFRAC-audited, 3-year validity — every French vendor
  found claims it. No US analogue.
- **The Italy trap — most counterintuitive finding in the audit.** Do **not**
  assume "Italy requires SdI e-invoicing" applies to patient billing. There is a
  **standing prohibition on routing healthcare invoices for private individual
  patients through SdI**, to keep health data out of the central exchange. The
  actual requirement is annual transmission to **Sistema Tessera Sanitaria**. An
  engineer assuming SdI would build something legally prohibited. *(Rests on
  Italian tax-advisory and trade sources — **confirm with a commercialista
  before any build**.)*
- **Radiation dosimetry logging — a genuine product white space.** Italy
  (D.Lgs. 101/2020, dose data to regional authorities, **6mo–1yr imprisonment +
  €20k–60k fines**), Spain (RD 1085/2009 — [BOE primary](https://www.boe.es/buscar/doc.php?id=BOE-A-2009-11932)),
  Germany (StrlSchG/StrlSchV), France (PCR + nominative dosimeters). **Essentially
  no dental PMS surveyed markets a dosimetry capability** — what they ship instead
  is *sterilisation-cycle traceability*, a legally distinct domain. Handled
  outside the PMS entirely today.
- **EU MDR Rule 11 is the build-scope decision point.** Administrative PM software
  is generally Class I; software informing diagnostic or therapeutic decisions
  escalates to Class IIa+ with full QMS and conformity assessment. Governing
  guidance **MDCG 2019-11 rev.1**. [European Commission](https://health.ec.europa.eu/medical-devices-sector/new-regulations/guidance-mdcg-endorsed-documents-and-other-guidance_en)
  **Live market signal:** the Italian product **MedicHub was withdrawn from sale
  as of August 2026**, the vendor citing the new European regulatory framework on
  software and healthcare data. A real competitor exited on regulatory grounds.
- **Canada is a hard build gate, not a format.** PM software must be **CDA-certified**
  to reach CDAnet/ITRANS; access is gated by provincial association membership.
  Implementing 837D-style transactions does not get you in. [CDA](https://www.cda-adc.ca/en/services/cdanet/)
- **UK NHS UDA** and **Australia HICAPS** are the two other named regional gates.

**Vendor that does not exist — flagged before it reaches a matrix.** "DenPro"
surfaced independently in the Dutch (`denpro.nl`) and Italian (`denpro.it`)
searches with the same incoherence: enterprise DSO positioning for 10+ locations
alongside a €19/month solo plan, one US LLC, 30+ country domains. Two lanes
reaching the same contradiction from different languages reads as a templated
multi-domain shell. **Do not enter it as a Tier B competitor without human
verification.**

---

## 5. SAIRNsenior

**Built and verified at HEAD:** 5 tables (`sen_clients`, `sen_caregivers`,
`sen_visits`, `sen_claims`, `sen_portal_links`); 10 nav panels. Family/client
portal is real (scoped revocable links, `973e247`). End-to-end verified 30/30
against production (`392ac37`).

### 5.1 The sharpest finding — and it is a defect, not a gap

> **CLOSED 2026-09-02 (Cody) — verified against the code, not assumed.** This
> was fixed on 2026-08-27, the day after this audit was written.
> `sql/sairnsenior_settings_schema.sql` creates `public.sen_settings`, it is
> registered in `api/_resources/sairnsenior.js`, and `senLoadSettings()` in
> `sairnsenior.html` reads the server FIRST — `agency_profile` and
> `evv_config` both come from `sen_settings`. The remaining `ld('sen_agency')`
> / `ld('sen_evv_config')` calls are a **flagged legacy-migration fallback**
> used only when the server has no row, and each sets a `migrated` flag so the
> panel can say the value is device-local rather than presenting it as saved.
> `saveAgency()` is server-first with no optimistic local write. The table is
> also live: `db/schema_snapshot.json` (2026-09-02) contains `sen_settings`.
> **What is still open is the separate, larger item — actual EVV transmission
> to an aggregator (§5.2 A1). Naming four aggregators and transmitting to none
> remains true.** The configuration being device-local does not.


**`sen_evv_config` and `sen_agency` are `localStorage`-only.** Verified at
`sairnsenior.html:1452`, `:1461`, `:1470`, `:1476` — both read via `ld()` and
written via `st()`, never server-synced.

The EVV Aggregator selector at `:491` offers Sandata, HHAeXchange, Tellus,
CareBridge and Other/State-Specific. So the app **names the four real aggregators
and transmits to none of them**, and the selection is not even durable across
devices or a browser-data clear.

This is the same class as SAIRNcare's `alf_facility` finding (Cody, 2026-08-21):
a **compliance-critical, state-mandated configuration held device-local**. Under
the Cures Act EVV mandate this is the single highest-consequence item in this
audit — see §5.3 for why the enforcement posture makes it worse.

### 5.2 Gaps — Tier A (single office, 5–40 caregivers)

| # | Gap category | Evidence | SAIRNsenior state (verified) |
|---|---|---|---|
| A1 | **Actual EVV transmission to a state aggregator** | Table stakes — every serious product has it. Submission formats differ by aggregator (Sandata JSON over SFTP/REST; HHAeXchange flat-file; Tellus XML). *(Vendor/industry synthesis, **not** primary CMS text — spot-check per state before building.)* | Aggregator **named in a dropdown**, no transmission. See §5.1. |
| A2 | **Telephony EVV fallback + offline capture** | GPS-plus-telephony is the table-stakes pairing; rural/no-signal visits are the reason telephony persists. | **Zero occurrences of telephony or offline.** |
| A3 | **Payer authorisation tracking with unit burn-down** | Named as a genuine Tier-B-only capability by the research, and **not found described in any Tier A product** — so this is a differentiator, not catch-up. | "authorization" 8 hits; **"units" zero.** No burn-down. |
| A4 | **Claims transmission (837) / clearinghouse** | Same structural gap as SAIRNdental A2/A3. | `sen_claims` exists with Generate Claim / Mark Paid / Mark Denied. **Zero for 837 or clearinghouse** — the claim is generated and then leaves by hand. |
| A5 | **Caregiver recruiting funnel / applicant tracking** | Built natively into both AxisCare and Aaniie at Tier A — i.e. baseline in this vertical, not an enterprise extra. Caregiver turnover is the market's defining operational problem. | **Zero for applicant.** "background check" 4 hits only. |
| A6 | **Training-hour and credential tracking** | State licensure sets caregiver training-hour rules; CareAcademy exists as a dedicated add-on category. | **Zero occurrences of "training".** Note the platform already has this pattern built twice (`rf_certifications`, `dnt_credentials`). |
| A7 | **Referral-source CRM** (hospital / discharge-planner relationships) | Mosai is built entirely around this and claims 10/10 of the top US home-health providers. **Notably absent** from AxisCare, Aaniie, Alora and KanTime feature lists — so it is a real differentiator at Tier A. | **Zero occurrences of "referral".** SAIRNdental has `dnt_referrals`; SAIRNsenior has nothing. |

### 5.3 Gaps — Tier B (multi-branch, multi-state, franchise, MCO)

| # | Gap category | Evidence | SAIRNsenior state |
|---|---|---|---|
| B1 | **Multi-branch / multi-state operation** | Defining Tier B requirement. | **Zero for `location_id`; "branch" 3 hits.** SAIRNroofing and SAIRNdental both have location capture; SAIRNsenior has none. |
| B2 | **Denials management and appeals** | **No vendor in the market published a concrete denials-and-appeals workflow** despite universal "RCM" claims. Market-wide gap, and "Medicaid billing opacity" is the loudest single Tier A complaint too (AxisCare reviewers: no in-system claim-status visibility, batch rejections discovered weeks later). | "denial" 17 hits (Mark Denied); **"appeal" zero.** |
| B3 | **Franchise-network reporting and royalty calculation** | WellSky's claim of 8 of the 10 largest personal-care franchise networks is a real moat. Most Tier A tools do not attempt it. | Absent. |
| B4 | **Payer contract management across many payers/states + MCO authorisation** | Tier-B-defining. | Absent. |
| B5 | **Consolidated + per-branch P&L** | Tier-B-defining. | Absent. |

### 5.4 Market-structure finding that should inform any EVV work

> **CORRECTED 2026-08-27.** Two claims in the paragraph below were checked
> against primary sources during the EVV transmission groundwork pass and did not
> survive. **(1) The acquisition closed 2024-10-03, not September 2024** — per
> [HHAeXchange's own press release](https://www.hhaexchange.com/press-releases/hhaexchange-acquires-sandata-technologies).
> **(2) The state counts below ("~10 directly", "~25 more") are secondary-sourced
> and should not be relied on.** HHAeXchange's own Provider Info Hub lists 15
> states; Indiana — which a secondary source placed under HHAeXchange — is
> **Sandata**, verified against
> [in.gov](https://www.in.gov/medicaid/providers/business-transactions/electronic-visit-verification/).
> Georgia, Kansas, Tennessee and Arkansas are unconfirmed either way.
> **(3) The "one company, therefore a consolidated map" implication is also
> wrong**: the two formats have NOT converged. Different auth models, different
> field casing, different batch limits, and states were still publishing
> Sandata-branded specs under 2026 paths. See
> `docs/superpowers/specs/2026-08-27-evv-transmission-groundwork.md` §6.
> The original paragraph is kept below unedited, as the record of what was
> claimed and on what basis.

**HHAeXchange acquired Sandata in September 2024**, on top of Cashé and
Generations. That means one company is simultaneously **(a)** a state EVV
aggregator covering ~10 states directly *and*, via Sandata, the dominant
closed-model aggregator across ~25 more, and **(b)** a paid competing agency
software vendor selling to the same providers who are *mandated* to submit
through its aggregator. Anyone still holding a "two competing aggregators" mental
model is working from a stale map.
[Cressey & Company](https://www.cresseyco.com/news/hhaexchange-acquires-sandata-technologies-enhancing-ability-to-serve-homecare-providers-payers-and-caregivers-nationwide),
[HHAeXchange FAQ](https://www.hhaexchange.com/hhaexchange-sandata-faq)

Also relevant: **even self-described enterprise EMRs do not claim uniform
multi-state aggregator coverage** — KanTime's own site distinguishes states with
full integration from states where it "works independently of state EVV systems."
Uniform coverage is genuinely hard, and claiming it would be a fabrication.

### 5.5 Non-English findings

| Market | Capability category | Forcing function |
|---|---|---|
| Germany | **SGB V / SGB XI dual billing** via electronic DTA (§302 / §105 SGB V) | Statutory dual-track long-term-care insurance |
| Germany | **Pflegegrade 1–5** care-level classification driving reimbursement | SGB XI |
| Germany | **Strukturmodell / SIS** standardised documentation; MD/MDK quality audits | National care-documentation standard |
| Japan | **国保連 (kokuhoren)** centralised monthly LTC claims clearinghouse | 介護保険 |
| Japan | **要介護度** care-level certification driving both care plan and reimbursement; periodic **介護報酬改定** fee revisions vendors must push | MHLW |
| France | **APA / GIR** levels; **télégestion mandated by département** as a precondition of fund disbursement; **CPOM**; prestataire vs mandataire dual operating modes; CCN BAD collective-bargaining payroll | Departmental funders + sector agreements |
| Netherlands | **WLZ / WMO / ZVW triple funding-stream routing**, each with its own declaratie standard (iWlz/iWmo) over **Vecozo** (45,000+ providers) | Three separate statutes |
| Sweden | **Beställare–utförare** purchaser–provider split + **LOV** free-choice systems | SoL / LOV |
| Norway | Mandatory **kjernejournal** integration in nursing homes and home care **from 2026-01-01** | National mandate *(vendor-page sourced, not cross-checked against Helsedirektoratet)* |

**Explicit gaps in this lane:** Denmark, Poland and Brazil returned **no verified
agency-facing product at all** — search quota and bot-blocking, not evidence of
absence. Zero patent search was performed in this lane.

---

## 6. Two false findings caught locally before they reached this document

Recording these because the mechanism matters more than the findings.

1. **"SAIRNdental has no multi-location support."** A client-side grep for
   `location_id` in `sairndental.html` returns **zero**. The claim would have been
   wrong: capture is real, server-side, and stamped in `api/_lib/dnt-location.js`,
   wired at `api/sd-data.js:5336`, `:5371`, `:5456`. Commit `2a74e00` is an
   ancestor of HEAD and touched 5 files. **A grep of the client can only prove
   something about the client** — the same lesson already written into Guardian
   Check 23 this week about grepping `api/`.

2. **"SAIRNdental supports ERA."** A naive grep for `ERA` returned **130 hits**.
   Word-boundary `\bERA\b` returns **zero** — every hit was a substring
   (`operatories`, `general`, …). Had this gone in as "ERA present," it would have
   been a fabricated capability claim in a competitive document.

Both were caught by re-checking a surprising number rather than reporting it.

---

## 7. Unverified register — read before quoting anything externally

These are **not findings**. They are things the pass could not confirm, listed so
they are not mistaken for confirmed.

**Regulatory — senior care (highest consequence):**
- **CMS Access Rule 80/20 provision** — last confirmed finalised (2024) with a
  July 2030 compliance deadline, **not rescinded** as of the retrievable sources.
  CMS.gov and Federal Register were **403 to automated fetch** and no search
  budget remained to check for 2025–26 deregulatory action. This is a plausible
  rescission/delay target. **Do not make a compliance claim on it without a live
  CMS.gov / Federal Register check.**
- **FLSA companionship exemption / 2013 Home Care Final Rule** — **not verified
  this session at all.** DOL.gov 403'd. Load-bearing for any payroll-overtime
  logic.
- **PDGM / OASIS-E1 dates, Medicare Advantage supplemental benefits / VBID
  status** — not verified; CMS pages 403'd.
- **State-by-state licensure, training-hour, background-check, minimum-wage and
  sick-leave variation** — **not covered.** Largest single remaining gap in the
  senior lane.
- EVV state-by-state open/closed model assignments are **vendor/industry
  synthesis, not primary CMS or state-Medicaid text.**

**Regulatory — other:**
- Davis-Bacon and OSHA roofing fall-fatality statistics: commonly cited, **not
  checked against DOL.gov / OSHA.gov** this pass.
- Germany **BSI C5 Typ 2** as legally required for health-data cloud since
  2025-07-01: **single vendor-blog source**, not cross-verified.
- Austria **ELDA**, Switzerland's dental tariff structure, France ADELI/RPPS,
  Korea mandatory-e-submission status: unverified or never searched.
- Italy's SdI healthcare carve-out (§4.3): **secondary sources only, and it is the
  highest-consequence single finding in the dental lane.**

**Patents — the section is materially incomplete and is not a cleared landscape:**
- Roofing: **EagleView v. Xactware/Verisk** is real and live — 7 EagleView + 2
  Pictometry patents, named **US 8,209,152** ("Concurrent Display Systems and
  Methods for Aerial Roof Estimation"), Alice challenge rejected, several IPRs
  denied, **$125M awarded**. Confirmed and consistent with the existing
  `2026-08-24` scope doc and `2026-08-26` IP screen.
  [Timeline](https://www.eagleview.com/insurance/eagleview-xactware-verisk-litigation-timeline/)
- Senior care: **US 9,471,749** ("Healthcare verification system and method") and
  **US 11,915,806** (video-camera-based recording combined with *"automated
  electronic visit verification records"*, issued 2024-02-27). **Assignees could
  not be confirmed for either.** The second directly overlaps any video-based
  check-in feature. Flag only.
- Dental: **US 11,037,671** (Softech Inc, voice-driven charting);
  **US 20140350963** (Carestream, **abandoned** 2018) ; Japan **特許第7501883号**
  (株式会社オプテック, AI voice-to-chart). Denti.AI *claims* **US 11,389,131** —
  **vendor claim, not USPTO-verified.**
- **No European, Spanish, Italian, Brazilian or Japanese patent database was
  searched in any lane.** Absence of European hazards in this document reflects
  that no European database was searched, **not that none exist.**
- **In re Dental Supplies Antitrust Litigation** — could not be verified at all;
  **do not cite case number, court or outcome from this document.**

**Sources unreachable across the whole pass:** Reddit, Dentaltown, G2,
CourtListener, Justia, Google Patents, USPTO Patent Public Search, CMS.gov,
DOL.gov, Federal Register, NACHC, KLAS, HRSA UDS, Naver.

The brief prioritised forum sentiment. **That is under-delivered** — complaints in
this document come from Capterra/Software Advice and trade press, which worked
reliably, not from Reddit or Dentaltown.

---

## 8. What this document deliberately does NOT do

- It **recommends no build.** This was requested as a research pass and stops
  there.
- It assigns no priority ordering across the three apps.
- It offers **no infringement analysis** on any patent named in §5 or §7.
- It does not treat any competitor's implementation as a design input; every gap
  is a functional category only, per §2.
