# Competitive-gap status — re-derived against the code, 2026-09-02

**This supersedes the STATUS COLUMNS of the two audits below. It does not
supersede their reasoning, their evidence, or their market analysis, which
remain the reference and are still accurate.**

- `docs/superpowers/specs/2026-08-26-competitive-gap-audit-roofing-dental-senior.md`
- `docs/superpowers/specs/2026-09-02-stonedesk-worldwide-competitive-gap-audit.md`

## Why this exists

The 2026-08-26 audit's state column said **"Absent"** about features that are
now shipped and live. That is not a criticism of the audit — it was correct
when written, and its own re-verification note (§3.2, Cody, 2026-09-02) already
warned *"treat the counts as dated and the verdicts as current."* **Seven days
and one very heavy build night later, the verdicts are dated too.**

This cost real time on 2026-09-02. Three sessions independently reached for
items the audit called Absent — SAIRNdental A8 (recall), A9 (treatment
planning), A4 (CDT versioning), A7 (GFE) and SAIRNroofing A1 (warranty) — **all
five of which were already built.** Every one was caught only because the
session grepped the code and the four `SAIRN-ACTIVE-WORK-*.md` files before
starting, rather than trusting the document. That is the gate working, but it is
the gate doing a job a current status list should have done first.

**The rule this produces:** the audits are for *why an item matters and what the
market does*. This file is for *whether it is still open*. Read both; trust this
one on status.

## Method, and what it does and does not prove

Marker terms were counted per item against the app file, all of `api/**.js`,
and the `sql/` filename list — word-boundary where the term is
substring-prone. **Every non-zero result was then read by hand.** A hit is not
proof of built and this pass treats it as a triage signal only.

That caution earned its keep four times in this pass:

- **SAIRNdental A1** (insurance eligibility verification) showed 4 hits for
  `eligibilit`. All four are `gfeEligibility` — whether a patient qualifies for
  a **Good Faith Estimate** under the No Surprises Act. Nothing to do with
  real-time payer eligibility. **Still open.**
- **SAIRNsenior A2** telephony showed 2 hits. Both are a comment *saying
  telephony is the half that was not built.*
- **SAIRNroofing B3** certified payroll showed 1 hit. It is the panel comment
  saying certified payroll **is deliberately not there.**
- **StoneDesk GAP 2** showed 20 hits for `dxf`. They are the Template/DXF file
  **manager** — customers' DXFs coming *in*. Line 9073 states in terms: *"It
  does not emit DXF or G-code to a specific CNC."*
  **That was true when this pass ran and stopped being true the same
  evening** -- DXF out shipped in `ee51217`; G-code remains declined on
  purpose. Left as written rather than edited, because the point of the
  paragraph is that 20 hits meant nothing, and that lesson survives the
  status change.

The reverse also held: **zero hits is strong evidence of open, and was not
treated as conclusive on its own** — panel ids, `api/_resources/*` registrations
and `sql/` schema files were checked for every item regardless of hit count.

---

## SAIRNroofing

| # | Item | 2026-08-26 said | **Verified 2026-09-02** | Evidence |
|---|---|---|---|---|
| A1 | Manufacturer warranty registration + certification-gated tiers | Absent (0 occurrences) | **BUILT** | `rf_warranty_tiers`, `rf_job_warranties`, `panel-warranties`, `sairnroofing_warranties_schema.sql` (Cody) |
| A2 | Crew / field-labour scheduling depth | Partially closed, depth unassessed | **BUILT** | Depth assessed then the missing half built: `api/_lib/roofing-crew-capacity.js` (Cody) |
| A3 | Subcontractor management | Not modelled, no `rf_subs`-class table | **BUILT** | `subcontractors`, `sub_assignments`, `panel-subs` (Cody) |
| A4 | Tool fragmentation | *Positioning finding, not a gap* | **N/A** | Unchanged — SAIRNroofing is already single-app; this is the wedge, not a work item |
| A5 | Accounting integration | Not present | **IN FLIGHT** | Cody holds an active claim: `accounting — fresh read-only quickbooks connector opt-in per customer` |
| B1 | Commercial roof asset registry | Absent — "single largest Tier B structural gap" | **BUILT** | `rf_buildings`, `rf_roof_sections`, `panel-assets`, `sairnroofing_asset_registry_schema.sql` (Cody) |
| B2 | No Tier A→B bridge | Open whitespace | **ADDRESSED BY B1** | Positioning finding that followed B1; B1 is the bridge |
| B3 | WIP / POC, retainage, certified payroll | 1 keyword hit, not modelled | **PARTIAL — DELIBERATELY** | Draws, retainage and over/under billing built (`rf_draws`, `panel-draws`). **Certified payroll explicitly refused** and said so on the panel: it needs external prevailing-wage determinations and *"inventing a rate would put a fabricated number in a federal filing."* |
| B4 | Safety / OSHA programme at scale | Only a credential type | **BUILT** | `rf_safety_equipment`, `rf_job_hazard_assessments`, `panel-safety` (Cody) |
| B5 | Multi-entity financial consolidation | `rf_locations` attribution-only | **BUILT** | `rf_entities`, `panel-entities`, `sairnroofing_entities_schema.sql` (Cody) |
| B6 | Supplier EDI (PO / ASN / invoice) | Absent | **PARTIAL — DELIBERATELY (CC, 2026-09-02)** | The three-way match is BUILT: `rf_supplier_documents`, `panel-supplier`, `api/_lib/roofing-supplier-match.js`, `sairnroofing_supplier_documents_schema.sql`. **EDI TRANSPORT IS NOT, and is refused as engineering** — an X12 850/856/810 exchange needs a trading-partner agreement and a per-partner certification cycle with ABC Supply / Beacon / SRS. The reconciliation those documents exist to enable is identical whether they arrive by EDI, PDF or paper, and the panel says so on screen rather than implying a connection. Re-verified absent before building: `supplier` and `vendor` each appeared **0 times** in `sairnroofing.html`. |
| B7 | Prequalification / bonding | Absent | **BUILT** | `rf_prequal_documents`, `rf_bonding`, `panel-prequal` (Cody) |

**SAIRNroofing genuinely open: nothing that is not vendor-gated.** B6's buildable
half shipped 2026-09-02; its EDI-transport half is refused for the same reason
B3's certified payroll was — it needs something outside this codebase, and
inventing it would put a number nobody verified into a supplier dispute. A5 is
in flight; B3 is complete except for the half refused on purpose.

---

## SAIRNdental

| # | Item | 2026-08-26 said | **Verified 2026-09-02** | Evidence |
|---|---|---|---|---|
| A1 | Real-time insurance eligibility verification | Absent | **OPEN** | 4 `eligibilit` hits are all `gfeEligibility` — No Surprises Act, not payer eligibility. Needs a vendor/clearinghouse connection |
| A2 | X12 837D + 835 ERA auto-posting | Absent | **OPEN — VENDOR-BLOCKED** | 0 hits on `837`, `835`, `x12`. Recorded as decision-gated by Fourth |
| A3 | Clearinghouse connection | Absent | **OPEN — VENDOR-BLOCKED** | 0 in-app hits. Same gate as A2 |
| A4 | CDT annual code maintenance | No versioned-catalogue concept | **BUILT** | `cdt_version` on `dnt_procedure_types` plus an effective-window check that refuses a code not in force on the service date |
| A5 | Imaging / sensor / CBCT / scanner | Absent | **OPEN — VENDOR-BLOCKED** | 0 hits on `imaging`, `radiograph`, `cbct`, `intraoral` |
| A6 | E-prescribing + EPCS + PDMP | No prescribing capability | **OPEN — CERTIFICATION-BLOCKED** | 0 hits. 21 CFR 1311 identity-proofing and DEA registration are the gate, not the code |
| A7 | Good-faith estimates / No Surprises Act | Zero occurrences | **BUILT** | `dnt_gfe`, `panel-gfe`, `sairndental_gfe_schema.sql` |
| A8 | Recall / reactivation | Zero occurrences | **BUILT** | `dnt_recall_outreach`, `panel-recall`, `sairndental_recall_schema.sql` (Fourth) |
| A9 | Treatment planning | Zero occurrences | **BUILT** | `dnt_txplans`, `panel-txplan`, `sairndental_treatment_plans_schema.sql` |
| B1 | Enterprise credentialing & payer-enrolment lifecycle — *"the clearest whitespace in the entire dental audit"* | Per-employee credentialing only, not payer enrolment | **BUILT** | `payer_enrollment` record type with its own effective/enrolment logic on `panel-credentials` (Hank) |
| B2 | Cross-location roll-up reporting | Write-side done, reporting deferred | **PARTIAL — DELIBERATELY DEFERRED** | `api/_lib/dnt-location.js` is real and server-side; reporting is in `SAIRN-BACKLOG.md` by decision, not by oversight |
| B3 | Consolidated RCM / denials & appeals | `dnt_denial` + `dnt_ar` exist, no appeals lifecycle | **BUILT** | `panel-denials` with the appeals workflow and receivable ageing (Fourth, `f856b38`) |
| B4 | Central call centre / missed-call leakage | *"recorded as a category, not a recommendation"* | **OPEN — NOT RECOMMENDED** | 0 hits. The audit itself declined to recommend it; it is not a backlog item |
| B5 | Open BI / data-warehouse connectors | Absent, CSV export only | **BUILT** | `api/dnt-bi.js`, `api/_lib/dental-bi.js`, `panel-bi`, `sql/sairndental_bi_tokens_schema.sql` (Fourth, `08bf7e0`). A generic pollable read-only JSON feed rather than a Power BI-specific `.mez` connector — all three named tools read a URL, so one feed serves all three. Eleven datasets of **stored facts**; derived measures (appeal deadlines, GFE due dates, recall standing, insurance estimates) are deliberately NOT duplicated out of the browser engines that own them. Inherits the minting employee's role, re-read live per poll; patient identifiers off by default behind a stable pseudonym. ⚠ SQL pending a run |

**SAIRNdental genuinely open and buildable in-house: A1 only (partly — the local
half without a vendor feed is limited).** A2/A3/A5/A6 are all gated on a vendor
contract or a federal certification, not on engineering. B4 was never
recommended. B5 closed 2026-09-02.

---

## SAIRNsenior

| # | Item | 2026-08-26 said | **Verified 2026-09-02** | Evidence |
|---|---|---|---|---|
| 5.1 | EVV config device-local | *The sharpest finding — a defect* | **CLOSED** | `sen_settings` is real and server-first; already annotated closed in the audit itself |
| A1 | Actual EVV transmission to a state aggregator | Named in a dropdown, no transmission | **OPEN — VENDOR-BLOCKED** | 0 hits on any submission path. Aggregator onboarding is the gate. Recorded as decision-gated by Fourth |
| A2 | Telephony EVV fallback **+ offline capture** | Zero occurrences of either | **PARTIAL** | **Offline capture BUILT** (`6ff2bc8`, Hank) — queue, real clock time, FIFO replay, refuse-at-cap. **Telephony still open**; the only 2 `telephony` hits are the comment saying so |
| A3 | Payer authorisation tracking with unit burn-down | Absent, `units` zero | **BUILT** | `sen_authorizations`, `panel-authorizations` (Hank, `c7613ec`). ⚠ SQL pending |
| A4 | Claims transmission (837) / clearinghouse | Absent | **OPEN — VENDOR-BLOCKED** | 0 hits. Same gate as SAIRNdental A2/A3 |
| A5 | Caregiver recruiting funnel / ATS | Zero occurrences | **BUILT** | `sen_applicants`, `panel-hiring` (Hank) |
| A6 | Training-hour and credential tracking | Zero occurrences | **BUILT** | `sen_training_rules`, `sen_training_records`, `panel-training` (Hank) |
| A7 | Referral-source CRM | Zero occurrences | **BUILT** | `sen_referral_sources`, `sen_referrals`, `panel-referrals` (Hank) |
| B1 | Multi-branch / multi-state operation | Absent | **BUILT** | `sen_branches`, `panel-branches` (Hank) |
| B2 | Denials management and appeals | `appeal` zero | **BUILT** | Appeals lifecycle on the Billing panel (Hank) |
| B3 | Franchise-network reporting and royalty | Absent | **BUILT** | `sen_franchise_agreements`, `panel-franchise` (Hank, 2026-09-02). The unit is the branch; a denied claim is excluded from the royalty base and an appealed one is reported in dispute. ⚠ SQL pending |
| B4 | Payer contract management + MCO authorisation | Absent | **BUILT** | `sen_payer_contracts`, `panel-contracts` (Hank, `517c47b`). ⚠ SQL pending |
| B5 | Consolidated + per-branch P&L | Absent | **BUILT — GROSS MARGIN ONLY, STATED** | `sen_pay_rates`, `panel-payrates`, margin columns on `panel-branches` (Hank, `e3f840e`). Direct labour only; the panel refuses the word *profit* and lists what is excluded. ⚠ SQL pending |

**SAIRNsenior genuinely open and buildable in-house: A2's telephony half.** A1
and A4 are vendor-gated. **B3 closed 2026-09-02, after this file was
written, and updated in the row above in the same commit as the build** — which is the maintenance rule at the
bottom of this document being followed rather than described.

> ⚠ **Four SAIRNsenior SQL files are written, committed and NOT YET RUN in
> Supabase**: `sairnsenior_payer_contracts_schema.sql`,
> `sairnsenior_authorizations_schema.sql`, `sairnsenior_pay_rates_schema.sql`,
> `sairnsenior_franchise_schema.sql`.
> Until each runs, that resource's write refuses with `NOT_PROVISIONED` naming
> the exact file; the panels otherwise work from local storage. **A panel that
> works locally is not a shipped feature.**

---

## StoneDesk

| # | Item | 2026-09-02 audit said | **Verified 2026-09-02, later same day** | Evidence |
|---|---|---|---|---|
| 1 | Customer-facing portal | *Structural, and the largest* | **BUILT** | `panel-publiccatalog`, `sd_public_shop`, `sd_quote_requests`, `stonedesk-catalog.html`, `stonedesk_public_surface_schema.sql` (Fourth, `987b679`), plus revocable order-tracking links (`fb94a0e`). Served from a SEPARATE file so an anonymous visitor cannot reach the chart of accounts, price book or patent deadlines. ⚠ `stonedesk_public_surface_schema.sql` is still pending a run in Supabase |
| 2 | Nesting produces no machine output | *Highest operational risk* | **BUILT — DXF ONLY, AND G-CODE IS REFUSED ON PURPOSE** | `nestingExportDXF` / `nestBuildDXF` on `panel-nesting`, `tests/nesting_dxf.js` (Fourth, `ee51217`). R12 ASCII, closed POLYLINE contours, inches, origin bottom-left, Y converted from the canvas convention. Kerf is deliberately NOT in the geometry — it is a CAM toolpath offset, and baking it in would change every part's finished size. **G-code is not emitted and will not be**: it needs feeds, speeds, tool numbers and a machine origin this app has never seen, which is fabrication with a saw on the other end. The paper half (saw/pick tickets, `tests/nesting_saw_ticket.js`) shipped the same day |
| 3 | No barcode / scanner support | Absent (`barcode` zero) | **BUILT** | `stonedesk.html:7087` — SCAN / FIND, USB barcode path, `externalBarcode` bound to slabs, duplicate external barcodes **reported not resolved** |
| 4 | No slab-scanner integration | Absent | **OPEN** | 3 `slabsmith` hits: one comment, two AI system prompts. No SideShot / Iride / Mapascan interface |
| 5 | No customer e-signature, no deposit collection | Absent | **OPEN** | `signedAt`/`signerName` are still only SAIRN's own service agreements. The 3 `stripe` hits are the price-book comment and the agreement text. "Deposit Required %" is a quote **term**, not payment processing |
| 6 | No QuickBooks integration | **HELD OPEN ON PURPOSE** | **HELD OPEN — UNCHANGED** | Michael's call, 2026-09-02. A known competitive disadvantage StoneDesk is choosing to carry. Reopening is a SAIRNbiz platform decision, not a StoneDesk feature request |
| 7 | No multi-location support | Absent | **OPEN** | Still 0 hits on `multi-location`, `multiLocation`, `locationId`, `location_id`, `sd_locations` |
| 8 | No remnant publishing to the public website | Absent | **BUILT** (was PARTIAL earlier the same day) | `sd_remnants`, `publicRemnantView`, remnant card on `stonedesk-catalog.html`, publish toggle on the shop panel (Hank, 2026-09-02). Only a published **and still Available** piece reaches the web; the price **is** published, unlike a slab's cost. ⚠ SQL pending |

**StoneDesk genuinely open: 4, 5 and 7.** GAP 1 (public catalog and order
tracking), GAP 2 (DXF machine output) and the remnant half of GAP 8 all closed
2026-09-02 -- 1 and 2 by Fourth, 8 by Hank. **GAP 2 is closed for DXF and
permanently declined for G-code**, which is a real distinction and not a
half-finish; see its row rather than reopening it. 6 is a standing decision, not
a work item.

---

## The genuinely open list, everything above collapsed

**Buildable in-house, no external dependency:**

| App | Item | Note |
|---|---|---|
| StoneDesk | GAP 7 — multi-location | Caps StoneDesk at single-yard shops |
| ~~StoneDesk~~ | ~~GAP 8 (remnant half)~~ | **Closed 2026-09-02** |
| SAIRNsenior | A2 telephony fallback | Offline half is done |
| ~~SAIRNsenior~~ | ~~B3 franchise royalty~~ | **Closed 2026-09-02** |
| SAIRNroofing | B6 supplier EDI -- **transport half only**; the three-way match shipped 2026-09-02 | Tier B procurement |
| ~~SAIRNdental~~ | ~~B5 BI / warehouse connectors~~ | **Closed 2026-09-02** |

**Blocked on a vendor contract, an integration partner, or a federal
certification — engineering is not the constraint:**

SAIRNdental A2, A3, A5, A6; SAIRNsenior A1, A4; StoneDesk GAP 4 (scanner
vendor), GAP 5 (payment processor). SAIRNdental A1 is partly here too.

**Standing decisions, not work items:** StoneDesk GAP 6 (QuickBooks, held open
deliberately), SAIRNdental B4 (call centre, never recommended), SAIRNroofing
A4/B2 (positioning findings), SAIRNroofing B3 certified payroll (refused to
avoid a fabricated federal filing), SAIRNdental B2 reporting half (deferred to
`SAIRN-BACKLOG.md`).

**In flight right now:** nothing. `python tools/sairn_claim.py list` is the live
source and this line is a snapshot -- at 2026-09-02 the only active claim was
Fourth's own SAIRNdental B5, released on this commit. StoneDesk GAP 1, StoneDesk
GAP 2 and SAIRNdental B5 closed that day (Fourth); StoneDesk GAP 8 remnant half
and SAIRNsenior B3 closed the same day (Hank); SAIRNroofing B6's three-way match
half closed the same day (CC).
**Check `python tools/sairn_claim.py list` before starting anything — this
column goes stale faster than any other in this file.**

---

## Two corrections to standing documents, found while doing this

1. **`CLAUDE.md` records the claim matcher's lexical-overlap defect as
   known-and-unfixed. It has since been fixed** — `3f9d50a`, Cody, 2026-09-02,
   with `tests/claims/run_matcher_probe.py`. Verified: the exact task string
   that was blocked earlier today on the preposition *"per"* now returns
   `CLEAR`. The CLAUDE.md paragraph should be updated; it is left alone here
   because editing it is a separate change with its own review.

2. **Three of the 2026-08-26 audit's own hit-COUNTS had already drifted** by its
   2026-09-02 re-verification, and more have drifted since. The counts are
   archaeology. Only the verdicts matter, and only in this file.

## How to keep this from going stale the same way

**Do not update the audit tables.** They are dated documents and rewriting them
loses the record of what was believed when. Update **this** file, in the row,
with the date and the commit — and when a build closes an item, the closing
session updates the row **in the same commit as the build**, exactly as a
handoff is not written until it is committed.

**And grep first anyway.** This file is a better starting point than the audits
and it is still a document rather than the code. Every verdict here has a
one-line evidence column precisely so the next reader can re-check it in
seconds instead of trusting it.
