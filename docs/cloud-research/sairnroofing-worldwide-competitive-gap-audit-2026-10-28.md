# Worldwide competitive-gap audit: SAIRNroofing

**fourth / b63, 2026-10-28.** This is the next app in the worldwide series, after sairndental (b36), sairnlaw (b37), sairncode (b38), sairndesign (b39) and sairnbiz (b41). b36 named three apps with **zero** audits; SAIRNroofing is one of them. sairnmechanical, another of the three, is under cody's active claim this batch, so it was left alone.

## Where this comes from

**It is built only from research already on file.** Nothing was fetched for this pass:

| source | what it contributes |
|---|---|
| `docs/superpowers/specs/2026-08-26-competitive-gap-audit-roofing-dental-senior.md` §0–§3 and §6–§8 | the gap list, the 13 non-US regimes, and the unverified register |
| `docs/2026-09-17-sairnroofing-competitive-gap-rederived.md` | the status re-derivation and the corrected FR/ES/PL dates |
| `docs/2026-09-29-competitive-gap-doc-inventory.md` and `docs/2026-10-06-gap-doc-verification-all-35.md` | the roofing rows |

**Every date and statutory claim below carries the confidence that research gave it.** None was re-checked against a regulator on 2026-10-28. §5 lists what is unverified.

**Audit only:** `sairnroofing.html` is in 0 of this batch's commits. Each status below comes from reading the code at `e40e86f3a`, and each names the function and line it was read at.

---

## 0. The result

> **Every US gap the August research named is now built, or refused with a disclosure on the panel. None of the thirteen non-US regimes it found is handled, and the app is US-only by construction.**

Evidence that the app is US-only by construction:
- `<html lang="en">`;
- one hard `en-US` format;
- one currency formatter, `rfCurrency()` `sairnroofing.html:2174`;
- an invoice record with no seller or buyer tax identifier.

**So the worldwide gap is not a missing feature. It is a missing *axis*:** no record says which country's rules it is under.

---

## 1. The US gaps: all closed or refused out loud

| # | the research's gap | status now | where |
|---|---|---|---|
| A1 | manufacturer warranty registration, cert-gated tiers | **built** | `saveTier()` `sairnroofing.html:4952`, `saveWarranty()` `sairnroofing.html:4998`, `api/_lib/roofing-warranties.js` |
| A2 | crew scheduling depth | **built** | `rfSaveSchedule()` `sairnroofing.html:5315`, `rfLoadCrewLoad()` `sairnroofing.html:5061`, `rfRouteOptimize()` `sairnroofing.html:5195` |
| A3 | subcontractor management | **built** (shared layer) | `saveSub()` `sairnroofing.html:3528`, `saveAssignment()` `sairnroofing.html:3622` |
| A5 | accounting integration | **export only**; the OAuth half is refused, and the panel says *"This is not a QuickBooks connection."* | `rfGlExport()` `sairnroofing.html:1688` |
| B1 | commercial roof asset registry | **built**; remaining service life is disclosed as not computed | `saveBuilding()` `sairnroofing.html:4744`, `saveSection()` `sairnroofing.html:4784`, `rfRenderForecast()` `sairnroofing.html:4662` |
| B3 | WIP/POC, retainage, certified payroll | WIP and retainage **built**; certified payroll **refused**, because *"inventing a rate would put a fabricated number in a federal filing"* | `saveDraw()` `sairnroofing.html:4521`, `rfRenderWip()` `sairnroofing.html:4451` |
| B4 | safety / OSHA programme | **built** | `saveEquip()` `sairnroofing.html:4311`, `saveJha()` `sairnroofing.html:4341` |
| B5 | multi-entity consolidation | **built** | `saveEntity()` `sairnroofing.html:3888`, `rfRenderConsolidation()` `sairnroofing.html:3761` |
| B6 | supplier EDI | document matching **built**; the panel says *"This is not an EDI connection."* | `rfSupplierAdd()` `sairnroofing.html:1844`, `rfSupplierMatch()` `sairnroofing.html:1794` |
| B7 | prequalification and bonding | **built** | `savePqDoc()` `sairnroofing.html:4086`, `saveBond()` `sairnroofing.html:4115` |

A4 (tool fragmentation) and B2 (no Tier A→B bridge) are positioning findings, not code. B1 shipping in the app is the bridge.

---

## 2. The non-US regimes: 0 of 13 handled

The August audit found thirteen regulation-driven categories with no US equivalent, and judged none a gap *"because v1 is US-only"*. That judgment still holds as a scope statement. This section records what each regime would need **from a record the app already writes**, so the cost of leaving the US is visible rather than assumed.

| jurisdiction | instrument (as the research names it) | what it asks of a record | the nearest record today | handled |
|---|---|---|---|---|
| DE | Gewährleistung, BGB + VOB/B | a statutory defect-liability period per job, separate from the manufacturer warranty | `rf_job_warranties`, which holds the **manufacturer** warranty only | no |
| DE | SOKA-BAU (VTV collective agreement) | social-fund contributions per worker hour | none | no |
| DE | XRechnung / ZUGFeRD, 2025–28 | a structured e-invoice | `rf_invoices`, with no tax ids and no structured format | no |
| DE | eANV (Nachweisverordnung) | a hazardous-waste tracking record, e.g. for old roofing | none | no |
| FR | garantie décennale (Code des assurances L241-1) | a 10-year insurer and policy per job | none | no |
| FR | Carte BTP (Loi Macron 2015; €4,000 per worker) | a site ID card per worker | `rf_certifications` (it has a `jurisdiction` field) | no |
| FR | Factur-X / Chorus Pro | e-invoicing: **in force 2026-09-01** for receipt; SME issuance from 2027-09-01 (09-17 re-derivation) | `rf_invoices` | no |
| ES | Verifactu / TicketBAI (AEAT) | certified invoicing software. **The August text said 2026-01-01.** 09-17 corrected this to 2027-01-01 for companies and 2027-07-01 for autónomos, on KPMG and Grant Thornton | `rf_invoices` | no |
| IT | DURC di congruità (Edilconnect) | a labour-cost congruity certificate per job | none | no |
| SE | ROT-avdrag (Skatteverket) | the customer's personal number and labour/material split on the invoice | `rf_invoices` (`line_items` only) | no |
| PL | KSeF | the national e-invoice system, phased Feb 2026 to Jan 2027 with no penalties in 2026 (09-17) | `rf_invoices` | no |
| JP | CCUS (MLIT) | a construction career registration per worker | `rf_certifications` | no |
| BR | SINAPI / ORSE | public-works budgeting against the reference price tables | `saveEstimate()` `sairnroofing.html:5708` | no |

**Five of the thirteen land on one record.** DE e-invoicing, FR, ES, SE and PL all ask the invoice for things it does not carry.

`rfCreateInvoiceFromProposal()` `sairnroofing.html:3085` writes `id, job_id, status, line_items, bill_to, terms, due_date, claim_id, tax_rate, tax`. It has:
- no seller tax id;
- no buyer tax id;
- no invoice number from a declared series;
- no structured-format export.

**If the app ever leaves the US, the invoice is the first record that has to change, and it is the one five regimes agree on.**

**Two records are already halfway there:**
- `rf_certifications` (`rfAddCertification()` `sairnroofing.html:2014`) has a `jurisdiction` field, so Carte BTP and CCUS have somewhere to go.
- The rule-table hooks (`rf_cert_rules`, `rf_contingency_rules`) are the pattern the August audit said these regimes would plug into.

**Not reached by the research at all:** UK, IE, AU, NZ, Canada, and Nordic/Polish Tier B. These are absent from the evidence, which is not the same as having no gap.

---

## 3. The write sites, for whoever builds next

| record | write site | fields |
|---|---|---|
| `rf_jobs` | `saveJobOverview()` `sairnroofing.html:5477` | id, name, address, job_class, status, assigned_employee_id, location_id |
| `rf_jobs` (estimate) | `saveEstimate()` `sairnroofing.html:5708` | base + estimate {material, line_items, status} |
| `rf_claims` | `rfSaveClaim()` `sairnroofing.html:2310` | carrier, claim_number, adjuster, date_of_loss, peril, policy_type, rcv, depreciation, acv, deductible, … |
| `rf_proposals` | `rfIssueProposal()` `sairnroofing.html:3020` | job_id, event_type, issued_on, line_items |
| `rf_invoices` | `rfCreateInvoiceFromProposal()` `sairnroofing.html:3085` | as listed in §2 |
| `rf_schedule` | `rfSaveSchedule()` `sairnroofing.html:5315` | job_id, scheduled_date, status, crew[], notes |

There is no separate inspection record. "Inspection" exists only as an equipment interval.

---

## 4. Corrections to the record on file

1. **The 2026-10-06 verification's "eight counts moved, all upward" is mostly a method change, not code growth.** At `762b084b`, the commit it measured, the word-boundary counts equal the 09-17 figures exactly (WIP 10, JHA 36, COI 14, EMR 5, crew 39). The new figures are case-insensitive substring counts. Its heading says eight, but its table lists seven.
2. **The August audit cites G2 for A2 and A5, while its own §7 says G2 was unreachable for the whole pass.** Those two citations cannot have been read first-hand.
3. The 09-17 re-derivation's "15 panels, 15 nav targets" is now **16 and 16**, because Accounting was added. The two sets still match.
4. **The A5 line numbers in the 09-17 doc and its 09-26 note have moved by 32–36 lines:** `:841→:873`, `:846→:882`, `:874→:910`, `:1652→:1688`. Those documents are dated reports and are not edited here; this row is the correction.

## 5. Unverified: read before quoting anything externally

- **Davis-Bacon** (B3) was never checked against DOL.gov (August §7).
- **"Over 80% of roofing fatalities are falls"** (B4) is unverified (August §3.3 and §7).
- **The AccuLynx supplier-EDI claim** (B6) is marked secondary and not verified in §3.3, and it is missing from §7.
- **Every §2 date** is the research's own, and the ES correction rests on secondary sources (KPMG, Grant Thornton). **No regulator was read for this document.**
- The PE-consolidation figures (17→56 platforms) come from M&A-advisory content that the August audit itself calls self-interested.

## 6. What this does not do

- It does not recommend leaving the US.
- It does not re-fetch any regulator.
- It does not edit the app.

What it does is state, in one place, which record each non-US regime would land on. That makes the cost of a market decision readable before the decision is made.
