# Worldwide external competitive research — plumbing, electrical, HVAC

**Research pass, 2026-09-25. No code written, no app file touched.** Written
by a standalone cloud session under `docs/cloud-research/` per instruction
(new files only, new branch, no PR). This is the trade-wide companion to
`docs/superpowers/specs/2026-08-21-plumbing-electrical-hvac-worldwide-research.md`
(the original research report) and
`docs/2026-09-17-trades-audit-rederived.md` (its code-facing re-derivation).
It updates the market picture rather than re-deriving SAIRNmechanical's own
state, which the companion document
`docs/cloud-research/SAIRNmechanical-external-competitive-gap-audit-2026-09-25.md`
does directly.

**Method and standard**: the reference for this series is
`docs/superpowers/specs/2026-09-02-stonedesk-worldwide-competitive-gap-audit.md`
— every competitor claim read from the vendor's own site, not a comparison
article; aggregator pages used only to find vendors; a failed fetch recorded
as a failure, never filled in; pricing only from a vendor's own pricing page.

---

## 0. A material limitation, stated before anything else

**This session's outbound network cannot reach any vendor, trade-press, or
patent-office domain**, confirmed directly against a healthy proxy status
(`enabled: true`, `bundleCoversEveryHost: true`, zero recent relay failures)
by attempting `WebFetch` to `buildops.com` and receiving `EGRESS_BLOCKED` —
the same result found and documented in this series' two prior external
audits (SAIRNvet, SAIRNlaw, both 2026-09-25). This is a destination-level
policy block, not a proxy fault, and the proxy documentation's own
instruction on a blocked host — *"Do not retry or route around it — report
the blocked host"* — is followed here rather than worked around.

**Evidence grade**: every vendor-fact cell below is a `WebSearch` result
restricted to the named vendor's own domain, i.e. the search engine's
*indexed excerpt* of that page, not the page itself. This is one grade below
this series' own standard and is marked as such throughout. **Nothing here
should be quoted externally — to a contractor, in a pitch, in a proposal —
without a follow-up pass from a network that can reach these domains.**
Patent-office domains were equally blocked; §5 records patent numbers as
unverified third-party index snippets with no infringement conclusion drawn.

Retrieval date for every row below: 2026-09-25.

---

## 1. What the internal research already established, as the anchor

From `docs/superpowers/specs/2026-08-21-plumbing-electrical-hvac-worldwide-research.md`
and its 2026-09-17 re-derivation: no single-trade-native FSM vendor has real
market weight in plumbing or electrical — every "plumbing software" or
"electrical software" product found is a generic field-service core with
trade-flavored marketing. **HVAC is the one trade with a genuinely separate
software sub-category**, because it has a hard regulatory forcing function
(EPA refrigerant compliance) that plumbing and electrical do not have
equivalents of. Backflow/cross-connection testing is a second, narrower,
genuinely separate category, forced by the same pattern — a three-party
utility workflow that generic FSM does not model.

## 2. What has changed since 2026-08-21 / 2026-09-17

### 2.1 The refrigerant-compliance vendor set is confirmed live and has moved

`RefriTrak`, `RefriComply`, `Field Ascend` and `FieldCamp` — all four named
in the original research — are confirmed still actively marketing as of this
pass, and **all four now reference the AIM Act's 15 lb / GWP-over-53
threshold by name**, which took effect 2026-01-01 during the interval
between the two research passes. Two newer entrants surfaced in this pass
that were not in the original list:

| Vendor | What the vendor-domain snippet states |
|---|---|
| **RefriTrak** | States AIM Act "Subpart C" compliance by name; claims to calculate leak rates against 10%/20%/30% thresholds; QR-scan cylinder/equipment logging; AI extraction from emailed work orders |
| **RefriComply** | States it "automatically calculates annualized leak rates every time a technician logs a service using the exact EPA formula" (the formula itself is not shown in the snippet); QR-code no-login field form; one-click PDF compliance report; pricing $29–$99/month by tier |
| **Field Ascend** | Refrigerant logging tied to per-asset records with automatic CO2e calculation and a force-rule requiring the log before job close; $13/user/month, three-user minimum, no setup fee — the only vendor in this set with a published flat per-user price |
| **FieldCamp** | A custom-objects engine lets a customer *configure* refrigerant logs, EPA-cert records, leak-rate calculations and repair countdowns as user-defined fields rather than shipping a purpose-built compliance engine; top tier roughly $1,499/month for 20+ technicians |
| **Oxmaint** (new, CMMS-flavored) | States it automates "the entire compliance lifecycle" from asset tracking to leak-inspection logs; cites the 10/20/30% thresholds and a $44,539/day penalty figure |
| **Fexa Trakref** (new, facilities-flavored) | States automatic leak-rate calculation and deadline tracking, covering both EPA 608 and California's CARB R3, and now cites the 2026 AIM Act threshold; three tiers, contact-sales pricing; oriented to multi-site facility owners rather than independent contractors |

**A genuinely new finding**: only two of the six vendors gathered
(RefriTrak, RefriComply) explicitly claim to compute a leak-rate
*percentage* against threshold as a fully automated, non-configurable
feature, and neither snippet shows the underlying methodology — both assert
compliance with "the EPA formula" without exposing it. **None of the six
cites a specific EPA guidance document number for the formula in the
snippet gathered.** This matters directly for any future SAIRNmechanical
leak-rate feature: the market's own vendors are not transparently sourcing
their math either, which is the same caution SAIRNmechanical's own refusal
to hardcode a rate is already built on.

A separate finding outside the FSM-adjacent set: **Axiom Cloud**, an
EPA-listed Automatic Leak Detection vendor serving grocery and cold-storage
chains, claims AI-based early-leak detection with a stated 9% false-positive
rate and 1–14 day detection window, auto-generating AIM Act-formatted
per-system leak-rate reports. This is a different buyer (facility owners,
not field-service contractors) and a materially more sophisticated
detection method (sensor-based, not manually logged) than anything in the
contractor-facing set — included because it shows where the technology
ceiling in this category currently sits.

### 2.2 General FSM platforms: credential and asset tracking, checked directly

| Vendor | EPA-608/refrigerant | Credential tracking | Asset registry | Manual J/D/S | Data export | Pricing |
|---|---|---|---|---|---|---|
| ServiceTitan | No dedicated compliance module found; a state-by-state licensing content hub, not a compliance engine | Not stated as append-only | "Equipment History" — model/serial/age/service history, QR/barcode scan, real-time asset location | Own branded load calculator citing "ACCA-certified load calculation accuracy"; no named third-party partner | CSV/XLSX for job-costing reports | Not published, per-technician custom quote |
| Housecall Pro | Not stated | Stores license/cert documents with expiration reminders — mutable, not append-only | Equipment history importable via price-book/CSV tooling | Own free calculator, **explicitly disclosed as landing "within 10–15% of a full Manual J"** and states a full ACCA Manual J is still needed for permits/new construction | CSV import/export confirmed | $59–79+/month entry tiers, published |
| FieldEdge | Informational blog content on EPA rules, not a stated product feature | Not stated | Not stated | Blog content only, no stated built-in tool | Not stated | Dedicated pricing page, figures not returned in snippet |
| BuildOps | Advisory content on asset-level EPA logging for appliances over 50 lb; not confirmed as a shipped feature | Dispatch "optimizes by tech certification and skill" — implies a field, not stated as append-only | Explicit "asset history tracking ties every action to a specific asset" language across several pages | Blog content with the Manual J formula itself; named ERP integrations (Viewpoint, Sage Intacct, NetSuite, QuickBooks); no Manual J partner named | Not stated | Custom pricing page, no published figures |
| **Service Fusion** | Not stated | Not stated as append-only | Not stated | **States integration with Amply Energy for "ACCA-approved Manual J load calculations"** — the one explicit third-party Manual J integration found across the entire FSM set | CSV export confirmed for payment/accounting history | $208–627/month across three flat tiers depending on annual/monthly billing, published, unlimited users |
| Jobber | Not stated | Not stated | Not stated (customer/job-centric, not asset-centric) | Not in stated scope | CSV export of products/services and job-costing lines, batched at 1,500 rows/file | $29–$529+/month, published tiers |

**On Manual J/D/S integration specifically**: Cool Calc publishes a
documented REST API and states it works with "OEMs, distributors, and
software providers" as embedding partners, but **no snippet from any of the
six primary FSM vendors names Cool Calc, Wrightsoft, or Elite Software
(Rhvac/Manual D Ductsize) as an actual integration partner.** Service
Fusion's tie-up with Amply Energy is the only concrete named Manual J
integration found in this entire pass, across the entire FSM peer set —
which reframes SAIRNmechanical's disclosure-only posture (§2 of the
companion document) as closer to market practice than a gap: **no FSM
vendor surveyed has built a compliance-grade Manual J engine in-house**, and
only one has a named partner for it.

### 2.3 Backflow/cross-connection remains a genuinely separate, mature category

| Vendor | Workflow, as stated | Pricing |
|---|---|---|
| **BSI Online** (Backflow Solutions, Inc.) | Testers "submit annual backflow test reports directly to the software", with automatic pass/fail computed "per state or provincial standard" and automatic tester credential verification; the site states it holds "the US Patent for the concept" (number not given in the snippet, unverified) | Not stated |
| **SwiftComply** | An explicit three-party structure: utility, certified tester, and the system itself; a "tester-pay" model (per-test fee charged to testers) as an alternative to a utility-funded subscription; a tester's profile changes require utility-manager approval before going live | Priced per solution (backflow, FOG, pretreatment, stormwater are separate products), typically a one-time implementation fee plus an annual subscription |
| BRYCER / The Compliance Engine | A cloud portal for third-party testing companies to submit reports with "immediate validation" | Not stated |
| iWorQ Systems | Tester portal login, configurable test forms, results recorded instantly | Not stated |
| Inspect Point | Lists backflow as one of several inspection trades on a shared platform | Three tiers by technician count and trade count, minimum three technicians or 400+ inspections/year |

**No FSM platform surveyed in §2.2 has absorbed this workflow natively** —
ServiceTitan's own search returned no backflow-specific module. The category
remains served entirely by standalone vendors running a genuine three-party
utility workflow, which confirms the original 2026-08-21 research's
separation and gives it sharper detail: the reason a generic FSM credential
dropdown cannot substitute for this category is that the product on the
other side is a relationship with individual water utilities, not a data
field.

### 2.4 Permit and inspection workflow: one vendor now claims direct e-submission

**PermitFlow** states it can "complete forms, attach supporting documents,
and file directly with the city or authority having jurisdiction… whether
the jurisdiction wants digital files, physical papers, or both" — a step
beyond document tracking, though the snippet does not distinguish a true
API-level submission from a staffed expediting service behind the same
interface. **None of the six primary FSM vendors in §2.2 surfaced a native
permit-submission module.** GovOS is the municipality-facing receiving
system some future e-permitting integration would target, not a contractor
tool.

### 2.5 Geothermal/IGSHPA: confirmed absent as a software category

IGSHPA itself (the training body) publishes certification programmes with
physical installer cards and three-year renewal, but no snippet — from
IGSHPA's own site or any vendor searched — names a dedicated geothermal
compliance or tracking software product. This is handled, where handled at
all, as a generic credential-type field inside general FSM products. This
confirms the original research's finding with no change.

### 2.6 No comparable forcing-function has yet emerged for plumbing or electrical

The clearest regulatory analogue found for the electrical trade is the
**2026 National Electrical Code**, described by trade press as bringing
expanded GFCI requirements, new EV-supply-equipment rules, and revised
service-disconnect marking — language trade press frames as touching "nearly
every facet of the electrical industry", structurally similar to how the AIM
Act reshaped HVAC software demand. **No dedicated "NEC-compliance software"
sub-category has formed around it in this pass's search.** The one visible
market move for plumbing and electrical specifically is packaging rather
than engineering: Housecall Pro is reported to have "recently launched its
HVAC, Plumbing and Electrical Packages" — preconfigured onboarding,
templates and workflows layered on one shared generic core, not separate
trade-native products. This matches the original research's central
conclusion exactly and extends it with a concrete, current example.

---

## 3. Patent screen — unverified, no conclusion drawn

Google Patents and USPTO domains were blocked identically to vendor domains.
Every entry below is a **third-party index snippet**, not an opened patent
page. No infringement conclusion is drawn from any of them.

**Refrigerant leak-rate / EPA compliance**: a family of grants spanning over
a decade — US 7,640,758 B2 ("Refrigerant tracking/leak detection system and
method"), a pair of older grants (US 8,005,648 and US 7,512,523) whose index
snippets describe a system computing a leak rate from an asset database
(full-charge weight, days since last refrigerant addition) across a single
unit or an aggregated site, compared against an EPA threshold with
notification, and two more recent grants (US 11,326,798 B2 and a 2024
publication) on leak detection and mitigation and on remote refrigeration
monitoring. **The prior-art picture here is dense and old enough that any
SAIRNmechanical leak-rate feature should be read against this family before
design, not after.**

**Append-only technician credential/license verification**: the closest
match found is US 2018/0330385 A1, "Automated and distributed verification
for certification and license data", describing automated
verification/monitoring across certifying organisations. Several other
grants cover credential-verification intermediary services generally (US
11,456,876 B2, WO 2020/176691 A1, a cluster around "interdependent
identity-based credential collection validation"). **None of the indexed
titles or abstracts specifically claims an append-only, renewal-as-new-row
data model** — the closest hits are generic verification/validation
systems, not the specific immutability property SAIRNmechanical's
`mech_credentials` registry already implements. This is a narrower risk
picture than the leak-rate family, on the evidence gathered, but is equally
unread at the claims level.

---

## 4. Market signals, 2025–2026 (third-party unless the URL is a named
company's own site; none independently fetched in this pass)

- **AIM Act enforcement is real and contractor-facing, not only
  equipment-owner-facing**: trade press cites 41 contractor enforcement
  actions totalling roughly $2.7M against a reported ~$100M total (87% of
  which fell on equipment owners), including one settlement over $1.3M and
  a criminal charge against a Georgia HVAC company's CEO for illegally
  importing 500 HFC cylinders — reported as the second criminal prosecution
  under the AIM Act and the first against a corporate executive. This is
  directly relevant to how seriously a SAIRNmechanical customer should be
  expected to take the compliance surface the app already models.
- **A penalty-figure discrepancy, unresolved in this pass**: trade press
  cites a current per-day-per-violation ceiling of $59,114 (a 2025
  inflation-adjusted figure), while multiple vendor pages in §2.1 cite
  $44,539/day. **These are two different figures from sources gathered in
  the same pass and this document does not reconcile them** — flagged
  rather than silently picking one, in the same spirit as this series'
  refusal to fill in a fact it cannot verify.
- **The regulatory picture on R-410A specifically is still moving**: trade
  press reports the EPA both offering "temporary relief" on R-410A
  installations and separately removing an R-410A installation deadline,
  with a "revised refrigerant rule" drawing lawsuits from multiple
  directions — the refrigerant regulatory environment is in flux, not
  settled, which argues for SAIRNmechanical's existing refusal-to-guess
  posture over a confident hardcoded rule.
- **FSM market consolidation continues**: ECI Software Solutions acquired
  Davisware (field service) in April 2025; Totalmobile and Solvares Group
  merged in February 2026 (Europe/UK/Australasia-focused).
- **2026 NEC changes** are described by trade press as touching "nearly
  every facet of the electrical industry" — see §2.6.

---

## 5. What this means for the platform, beyond SAIRNmechanical specifically

The trio's market shape has not changed since 2026-08-21 in its central
conclusion — plumbing and electrical remain served by relabeled generic FSM,
HVAC remains the one trade with a genuine regulatory-forcing-function
software category — but three things sharpened in this pass and are worth
carrying forward to any future SAIRN decision about this vertical:

1. **The refrigerant-compliance vendor set is not more rigorous than
   SAIRNmechanical's own posture**, it is only more confident-sounding. Two
   of six vendors claim automated leak-rate computation and neither shows
   its formula; SAIRNmechanical's refusal to hardcode one is defensible on
   the evidence gathered, not merely cautious.
2. **Data portability (CSV import/export) is confirmed table stakes**
   across essentially every general FSM vendor surveyed — this is the one
   item in this pass where the market gap is unambiguous and the fix is not
   novel engineering, only building what the disabled button already
   promises.
3. **No forcing function has yet emerged for plumbing or electrical the way
   the AIM Act did for HVAC.** The 2026 NEC is the nearest candidate and has
   not (yet) produced a comparable vendor category. This is evidence, not a
   prediction, and should be re-checked on the same cadence as the AIM Act
   date itself was — this series has now twice found a regulatory date
   moving *later* than an earlier pass recorded it (Spain's Verifactu, the
   EU F-Gas certification deadline), so a "not yet" here should not be read
   as permanent.

---

## 6. What this document does NOT establish

- **No vendor page was opened directly, at all, in this pass.** Every claim
  above is a search-engine snippet of a vendor's own domain.
- **No patent claim was read.** §3 names candidates for a real screen and
  performs none.
- **No competitor product was used, demoed, or tested.**
- **No pricing figure here should be quoted to a prospect** until re-read
  from the live page.
- The penalty-figure discrepancy in §4 is stated, not resolved.
- This document does not decide whether SAIRN should build a plumbing or
  electrical trade into SAIRNmechanical, or any specific feature named
  above — that is a `sairn-software-architect` and `sairn-decision-gate`
  question.

---

## 7. Decay

Every fact in this document is a search-index snapshot from 2026-09-25 of
pages this session could not open, in a regulatory area (§4) that is itself
described by trade press as still moving. **Do not treat any cell here as
current without re-reading the source page.** The one action this document
asks for, ahead of any competitive finding: run this pass again from a
network that can reach vendor and patent-office domains, and only then
decide what — if anything — to build.
