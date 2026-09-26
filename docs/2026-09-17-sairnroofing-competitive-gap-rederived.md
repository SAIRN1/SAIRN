# SAIRNroofing competitive-gap status, re-derived 2026-09-17 — the audit exists, eleven of twelve rows have closed, and one foreign deadline moved a year the wrong way

**Derived 2026-09-17 (CC) against the code at HEAD.** A **status** document, per
the convention `docs/2026-09-02-competitive-gap-status-rederived.md` set: *the
audits are for why an item matters and what the market does; a status file is
for whether it is still open.* §4 is the exception and says so.

---

## 0. The premise correction, first, because it is the one this audit has already made twice

**This pass was requested as "the worldwide competitive-gap research pass — not
yet done for this app." It has been done.** It is on disk as

> `docs/superpowers/specs/2026-08-26-competitive-gap-audit-roofing-dental-senior.md`
> — titled, verbatim, **"Worldwide competitive-gap audit — SAIRNroofing,
> SAIRNdental, SAIRNsenior"**

and it is thorough: market structure, named competitors, PE-consolidation
data, twelve gap rows across two tiers, thirteen non-English regulation-driven
categories, a patent-safety section, and a §7 register of what it had *not*
verified.

**That file's own §0.1 is a correction of this exact premise**, and it records
that it was the *second* time: the 08-26 request also said "the same treatment
every other app got", and the audit checked rather than accepted, finding no
such document for any of the ten apps named. Its closing note explains why the
correction matters — *"a commit-message claim ('audit complete') with no
artefact behind it"*. **This is the third instance.** The pattern is that gap
work gets re-requested because nobody can find the artefact, not because it was
never done.

So no fresh market research was run against §3.1–§3.3: it would duplicate a
document the 09-15 pass re-confirms is *"still good and still the reference"*.
What was missing — and what this file is — is a **full re-derivation of the
SAIRNroofing rows against current code**, which has never been done in one pass.
`2026-09-02` did it as of that date; `2026-09-15` §3 declared the column
"comprehensively stale" and hand-verified only **two** roofing rows, leaving
four on marker counts it explicitly labelled *"NOT hand-read"* and six untouched.

---

## 1. Method

Two passes, in this order, because the audit's own rule is that *a hit is a
triage signal and not proof*:

1. **Marker counts** over `sairnroofing.html` at HEAD, word-boundary anchored.
2. **Hand-read** of every ambiguous hit, plus the module header of every
   `api/_lib/roofing-*.js` that names a gap letter, plus a wiring check:
   does the capability have a **panel**, a **nav target** and a **registered
   resource** — the three ways a built feature is still unreachable on this
   platform.

The wiring check came back clean and is worth stating as a negative: **15
panels, 15 nav targets, identical sets.** Nothing built is orphaned.

---

## 2. Every SAIRNroofing row, re-derived

| # | Audit said (2026-08-26) | At HEAD, 2026-09-17 | Evidence |
|---|---|---|---|
| **A1** warranty registration + certification-gated tiers | *"Zero occurrences of 'warranty' anywhere"* | **CLOSED** | `api/_lib/roofing-warranties.js` + `.test.js`, `sql/sairnroofing_warranties_schema.sql`, `panel-warranties`. `warrant*` × 51. Header names gap A1 and carries the seeding refusal: no GAF tier list, no guessed 30-day window — *"being wrong here costs the homeowner the coverage"* |
| **A2** crew / field-labour scheduling depth | *"Partially closed — depth vs. the complaint not assessed here"* | **CLOSED**, and it assessed the thing the audit deferred | `api/_lib/roofing-crew-capacity.js` + `.test.js`. `crew` × 39, `double-book` × 4. Reports overlaps rather than refusing them, with the reasoning written down: two jobs in a day is a normal roofing day |
| **A3** subcontractor management | *"23 keyword hits, but no `rf_subs`-class table. Not modelled"* | **CLOSED** via the **shared** layer, not a roofing copy | `panel-subs`, `subcontractors` + `sub_assignments` registered unprefixed, `api/_lib/subcontractor-compliance.js`. `subcontractor` × 28, `COI` × 14, `W-9` × 3 |
| **A4** tool fragmentation as the buying trigger | *"a positioning finding, not a gap"* | **Still not a gap** — and stronger now: nine capabilities that were separate purchases in the audit now ship in one app | — |
| **A5** accounting integration (QuickBooks) | *"Not present"* | **STILL OPEN — the only one** | `QuickBooks`, `QBO`, `Xero`, `general ledger`, `IIF`, `chart of accounts`: **0 each**. No partial, no disclosure banner, nothing |
| **B1** commercial roof asset registry | *"Absent. The single largest Tier B structural gap"* | **CLOSED** | `api/_lib/roofing-asset-registry.js`, `sql/sairnroofing_asset_registry_schema.sql`, `panel-assets`, `rf_roof_sections`. `roof section` × 10 |
| **B2** no product bridges Tier A → Tier B | *"Open whitespace"* | **Structurally addressed**, by B1 shipping inside a Tier A app — which is precisely the bridge the row described as missing from the market | — |
| **B3** WIP/POC, retainage, **certified payroll** | *"1 keyword hit total. Not modelled"* | **TWO THIRDS CLOSED, one third REFUSED ON PRINCIPLE** | `retainage` × 22, `WIP` × 10, `draw request` × 10; `sql/sairnroofing_draws_schema.sql`, `api/_lib/wip-accounting.js`, `panel-draws`. `certified payroll` × 1 — **and that single hit is the comment saying it is NOT here**: it needs external prevailing-wage determinations and *"inventing a wage rate would put a fabricated number in a federal filing"* |
| **B4** safety / OSHA programme at scale | *"OSHA appears only as a credential type"* | **CLOSED** | `api/_lib/roofing-safety.js`, `sql/sairnroofing_safety_schema.sql`, `panel-safety`, `rf_job_hazard_assessments` + `rf_safety_equipment`. `JHA` × 36, `fall-protection` × 4 (hyphenated — see §2.2). Deliberately **not** an incident log: SAIRNbuild and StoneDesk both already have one |
| **B5** multi-entity consolidation for PE rollups | *"`rf_locations` is attribution-only. Branch ≠ entity"* | **CLOSED**, and it answers the audit's objection directly | `api/_lib/roofing-consolidation.js`, `sql/sairnroofing_entities_schema.sql`, `panel-entities`, `rf_entities`. `entity_id` × 16. `entity_id` lives on the LOCATION only, so moving a branch moves its whole history — attribution derived on read, never stamped |
| **B6** supplier EDI (PO / ASN / invoice) | *"Absent."* 09-02 called it the **only** genuinely open item | **BUILDABLE HALF CLOSED, transport REFUSED and DISCLOSED ON SCREEN** | `api/_lib/roofing-supplier-match.js`, `panel-supplier`, `rf_supplier_documents`. `three-way match` × 4, `purchase order` × 4, `supplier` × 26 |
| **B7** prequalification / bonding | *"Absent."* | **CLOSED**, facing the opposite way from SAIRNbuild's | `api/_lib/roofing-prequal.js`, `sql/sairnroofing_prequal_schema.sql`, `panel-prequal`, `rf_prequal_documents` + `rf_bonding`. `prequal` × 32, `bonding` × 27, `surety` × 12, `EMR` × 5. EMR is recorded and **never judged** — "under 1.0" is each GC's criterion, not a rule this app may assert |

### 2.1 Every ambiguous marker was hand-read, and all six are honest

The method's own rule, applied. **Not one is a false positive in the usual
direction** — and two are the opposite, which is worth naming:

| Marker | Count | What it actually is |
|---|---|---|
| `EDI`, `850`, `856` | 6 / 3 / 3 | **All disclaimers.** An on-screen banner reading *"This is not an EDI connection"*, and comments explaining that X12 needs a trading-partner agreement per supplier. The app refuses the claim in the UI rather than implying it |
| `certified payroll` | 1 | The comment stating it is **not** included and why |
| `anchor point` | 1 | A JHA form placeholder — the safety capability itself is real (`JHA` × 36) |
| `remaining service life` | 1 | A disclosure that the app does **not** compute a blended condition-adjusted RSL, because that adjustment is a model it does not have |

### 2.2 And my own marker set produced a false NEGATIVE, on a hyphen

Recorded rather than quietly fixed, because it is the audit's own recorded trap
running in the other direction. The audit notes that a naive `grep -i edi`
returns 16 hits — all `edit`/`edited` — and that a word-boundary search returns
0: a substring producing a false **positive**.

**Mine did the opposite.** I searched `fall protection` with a literal space and
got **0**, and drafted the line *"zero occurrences of 'fall protection', on a
roof"* as the sharpest criticism in this document. The file spells it
**`fall-protection`**, hyphenated, four times — and they are not comments:

* a card headed **"Fall-protection equipment"** in `panel-safety`;
* `rfRenderEquipment()`, which renders that equipment with expiry urgency;
* two headers stating the scope — *"fall-protection equipment that EXPIRES, and
  a hazard assessment the crew on the roof today has or has not signed"*, and
  deliberately **not** an incident log, because SAIRNbuild and StoneDesk both
  already have one.

So **B4 is closed more completely than §2 first credited it**: JHA plus
fall-protection equipment with expiry tracking, cross-checked against the crew
actually scheduled that day. The criticism was wrong and is withdrawn.

**A word-boundary search is not a safe default either.** It fixes the
false-positive direction and creates this one. The only thing that caught this
was running a second spelling of the same idea; the counts in §2 should be read
as a floor, never as a ceiling.

**A gap that is disclosed on screen is not a gap that is closed, and it is not a
gap that is hidden either.** B6 and B3's certified-payroll third are both in
that third state. Counting them as closed would overstate; counting them as
absent would miss that the product tells the user the truth about them.

---

> **CORRECTED 2026-09-26 (Cody): A5 IS CLOSED AND THIS SECTION IS NINE DAYS OUT
> OF DATE.** See `docs/2026-09-26-gap-triage-four-verticals.md` §2.1. Measured in
> `sairnroofing.html`: `QuickBooks` 0 -> **4**, `chart of accounts` 0 -> **4**,
> `Xero` 0 -> **1**, and it is not prose -- `rfGlExport()` at `:1652` behind a
> "Build journal" button at `:874`, a chart-of-accounts panel at `:850`, and
> `gl_export` three times in `api/sd-data.js`. The on-screen disclosure this
> section says is absent is at `:846`: *"This is not a QuickBooks connection."*
> **So A5 now has the same buildable-half-built / vendor-half-refused shape this
> document credits B6 with, and roofing has no un-gated row left.** The text below
> is left as it stood, because a status document that edits its own history is
> worse than one that is late.

## 3. What is genuinely still open

**One row: A5, accounting integration.** Zero markers, no partial, no
disclosure. It is not vendor-gated in the way the audit's blocked rows are —
QuickBooks Online has a public API — but it is not free either: it needs an
Intuit developer account, OAuth, and a token-refresh lifecycle, which is an
integration with an external identity, not a pure module like every other
capability listed above. That distinction is why it is the row still standing.

**Two rows are refused rather than open, and the refusals are the right ones:**

* **B3 certified payroll** — would require asserting a prevailing-wage
  determination. A fabricated rate here goes into a federal filing.
* **B6 EDI transport** — would require a trading-partner agreement and a
  certification cycle with ABC Supply, Beacon and SRS individually.

Neither should be reopened as engineering work. Both are business-development
questions: the first needs a wage-determination data source somebody will stand
behind, the second needs three commercial agreements.

**Direction of travel, stated because it inverts the usual finding.** The 09-15
pass established that a gap row's decay rate tracks *how close the feature
already was*, and predicted the 08-26 rows would move. They did — but further
than "moved": eleven of twelve are now closed or deliberately refused, each by a
module whose own header cites the gap letter it answers. The audit was used as a
build queue and worked through. **The risk with this document is therefore the
opposite of staleness: it is that a reader treats "eleven of twelve closed" as a
quality claim. It is not. It is a COVERAGE claim, and coverage is not depth.**
This file checked that each capability exists, is wired, and names the gap it
answers. It did not check that any of them would beat the competitor the audit
named — and §2.2 is a live demonstration that even the coverage half can be got
wrong by one hyphen.

---

## 4. The worldwide half, re-verified against primary reporting — and one date moved

§3.4 of the audit lists thirteen regulation-driven categories with no US
equivalent, each with a commencement date. Those dates are the one part of a
competitive audit that decays on a **schedule** rather than on code, so the
three e-invoicing mandates were re-checked. **This is the only section here that
is research rather than status.**

| Market | Audit said (2026-08-26) | Verified 2026-09-17 | Change |
|---|---|---|---|
| **France** — Factur-X / Chorus Pro | *"National e-invoicing, from 2026-09-01"* | **Correct, and now IN FORCE — 16 days ago.** Reception of structured e-invoices is mandatory for **every** VAT-registered business from 2026-09-01; issuance from that date for large enterprises and ETI, and from **2027-09-01** for SMEs and micro-enterprises | **Commenced** |
| **Poland** — KSeF | *"Phased Feb 2026 → Jan 2027"* | **Correct, and phase 1 has run.** 2026-02-01 for large taxpayers (>PLN 200m), 2026-04-01 for all other VAT-registered businesses, 2027-01-01 for micro-enterprises. **And a detail the audit did not have: no penalties apply during the whole of 2026**, with penalties from 2027-01-01 of up to 100% of the invoice VAT | **Commenced, unpenalised until 2027** |
| **Spain** — Verifactu / TicketBAI | *"2026-01-01 companies / 2027-07-01 autónomos"* | **The company date is WRONG — it was postponed a year.** Now **2027-01-01** for corporate-income-tax companies and **2027-07-01** for autónomos | **Slipped 12 months** |

**The Spanish row is the finding, and it moves the wrong way for the usual
assumption.** A regulatory date in an audit is normally treated as a floor that
only gets closer. This one receded, and a build scheduled off the 08-26 figure
would have shipped a year early into a market with no obligation yet — the
mirror image of shipping late.

**Bearing on SAIRNroofing: still none today, and the v1 US-only decision stands.**
These are recorded so the *shape* of the decay is visible: §3.4's value is a
list of dated forcing functions, and a dated list is the one kind of finding
that can be wrong without anybody touching the code.

**Explicitly NOT re-verified:** the other ten rows of §3.4 (Germany ×4, France
Carte BTP and garantie décennale, Italy, Sweden, Japan, Brazil). They inherit
the 08-26 audit's verification status and its §7 unverified register. Do not
quote them externally without checking, which is what that register says.

---

## 5. Limits of this pass

* **Marker counts are dated the moment they are written.** The audit's own
  counts drifted (A3's "23 hits" → 0, B3's "1 hit" → 0) without a single verdict
  changing. Treat the counts here the same way and the verdicts as current.
* **"Closed" here means the capability exists, is wired, and its own module
  states the gap it answers.** It does not mean the capability is deep enough to
  beat the named competitor — that is what the audit's market analysis is for,
  and re-running it was out of scope. B4 is the clearest case: real, wired, and
  narrower than its row describes.
* **No live check.** Every verdict is against the repository at HEAD, not
  against the deployed app.
* **No code was written and no app file was touched.**

## Sources

- [TrueCommerce — E-Invoicing in France: guide to the 2026–2027 French mandate](https://www.truecommerce.com/blog/e-invoicing-in-france-a-guide-to-the-french-mandate/)
- [Thomson Reuters — E-invoicing in France: meet the mandate and stay compliant](https://europe.thomsonreuters.com/blog/a-guide-to-e-invoicing-in-france)
- [EU E-Invoicing Hub — France e-invoicing mandate 2026](https://www.eu-einvoicing.com/france/regulations/france-e-invoicing-mandate-2026-complete-guide)
- [KPMG — Spain: Verifactu invoicing system delayed to 2027](https://kpmg.com/us/en/taxnewsflash/news/2025/12/tnf-spain-verifactu-invoicing-system-delayed-to-2027.html)
- [Grant Thornton — Verifactu postpones its entry into force to 2027](https://www.grantthornton.es/en/insights/tax/verifactu-postpones-its-entry-into-force-to-2027/)
- [EDICOM — Poland implements mandatory B2B e-invoicing with KSeF from 2026](https://edicomgroup.com/blog/poland-will-make-b2b-electronic-invoicing-mandatory)
- [Sovos — KSeF: a timeline of Poland's e-invoicing mandate](https://sovos.com/blog/vat/poland-e-invoicing-via-ksef/)
