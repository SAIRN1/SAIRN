# Worldwide competitive-gap audit: SAIRNbuild

**fourth / b64, 2026-10-28.** This follows SAIRNmechanical (also b64). Two audits exist and this one replaces neither:
- the 09-03 supplied-research pass, `docs/superpowers/specs/2026-09-03-competitive-gap-audit-build-vet-biz-grounds-cash.md`;
- the 09-27 Ohio/US-federal external pass, `docs/cloud-research/sairnbuild-external-competitive-gap-audit-2026-09-27.md`.

This one puts both against the code. It also found **one defect neither recorded**: the subcontractor award button does nothing.

## Where this comes from

**It is built only from research already on file.** Nothing was fetched for this pass:

| source | its evidence grade, as it states it |
|---|---|
| 09-03 §0–§3, §8–§10 | "supplied research, not re-verified, no citation URLs"; no non-English section; no patent screen |
| 09-27, in full | **[SNIPPET] throughout**, because fetches were blocked. Its regulatory lens is **Ohio and US federal only** |
| `docs/2026-09-15-…-mechanical-and-five-apps.md`, the build rows | status re-derivation |

**No research on file covers any non-US jurisdiction for construction.** Section 3 says what that means.

**Audit only:** `sairnbuild.html` is in 0 of this batch's commits. Each status below comes from reading the code at HEAD. The file was last changed in `e137c3bc1`.

---

## 0. The result

> **SAIRNbuild's money records are the strongest in the series.** Draws, retainage released atomically on the server, lien waivers, and change orders. Two of those records **record a fact and gate nothing**:
> - **the lien waiver never stops a payment;**
> - **the subcontractor award never awards.**
>
> Outside the US the research never looked, and the code has no VAT, GST or reverse-charge field to look with.

---

## 1. One defect neither audit recorded: "Awarded to X" awards nothing

`awardSubBid()` `sairnbuild.html:4915` does two things:
1. it checks eligibility (client-side only, `eligibleToBid()` `sairnbuild.html:6410`);
2. it saves the bid list, and toasts *"Awarded to X"*.

**It never marks any bid awarded.** The line `x.awarded=(x.id===id)` was removed in `66cf7b930` (2026-08-09), and the list is saved unchanged. So:
- every award since then is a toast over no state change;
- the 09-27 audit's claim that award is "gated server-side" is also wrong. `award` appears in `api/sd-data.js` only for SAIRNfreedom donor rows.

`awardSubBid` appears 0 times in the open-work index. **This is a real defect in a record the app writes, and it needs its own claim, fix and register record.**

## 2. The gaps, status now

| # | gap | status | where |
|---|---|---|---|
| B2 | retainage release with an audit trail | **built**, atomic on the server | `releaseRetainage()` `sairnbuild.html:5794`; `release_retainage` in `api/sd-data.js` |
| B3 | WIP cost-to-complete | **calculation fixed (`25d1c0009`), but nothing writes `forecast`.** The cost modal has no forecast field and `saveCost()` only carries an existing one forward. **Every job with an accepted change order is flagged stale for good** | `jobWIP()` `sairnbuild.html:7610`, `forecastFor()` `sairnbuild.html:3674`, `saveCost()` `sairnbuild.html:5405` |
| B1 | AIA G702/G703 | **partial:** draws built; no schedule of values. G702/G703 are copyrighted, so 09-27 recommends an "AIA-style" export | `saveDraw()` `sairnbuild.html:5727` |
| X8 | lien waivers that gate payment | **record only:** the missing-waiver flag is display-only, and a payment records with no waiver check | `saveLw()` `sairnbuild.html:5908`, `drawsMissingWaiver()` `sairnbuild.html:5619`, `saveChk()` `sairnbuild.html:6302` |
| X6 | OSHA training and safety | **partial:** toolbox talks store an attendee *count*, with no names and no 1926.503 tie (`silica`, `OSHA 300` ×0) | `saveTalk()` `sairnbuild.html:6896` |
| A4 | offline-first | **partial:** failed pushes are queued, but the user is never shown an offline state | `bld_sync_pending` |
| I-2 | demo data seeds on every licence, including a "QuickBooks: connected" row | **still true** | `seed()` `sairnbuild.html:3217` |
| I-3 | the "Client Portal" cannot be shared | **still true**: no link or token | `rClientPortal()` `sairnbuild.html:6924` |

**Absent:**
- A1: scope-gap detection with page citations;
- A2: IFC/BIM;
- A3: English/Spanish UI;
- B4: multi-entity/currency;
- B5: certified payroll (Davis-Bacon, WH-347);
- B6: GL sync;
- X1: Ohio home-construction contract controls (ORC 4722: the 10% deposit cap and 3-day cancellation);
- X2: lead RRP (40 CFR 745);
- X3: lien deadline engine (ORC 1311);
- X4: homeowner payment;
- X5: lender draw package;
- X7: prompt pay and public/private retainage.

All of the X rows are [SNIPPET].

---

## 3. Outside the US: the research never looked

`VAT`, `reverse charge`, `CIS`, `GST`, `e-invoic`, `Peppol`, `Construction Act`, `pay less` and `payment notice` all return 0 hits, in the code **and** in the research on file.

**Unknown, not clean.** The regimes a construction app meets first outside the US are:
- the UK Construction Industry Scheme;
- the UK Construction Act payment and pay-less notices;
- EU e-invoicing;
- the VAT domestic reverse charge for construction services.

**None of these was researched,** so this document makes no claim about any of them. It names them only as the list a worldwide pass would have to research first.

**What the code shows regardless.** Every one of those regimes lands on records SAIRNbuild has: the draw, the payment to a subcontractor, and the company profile. Those records carry:
- a company **EIN**;
- a W-9 flag on the subcontractor.

They carry no VAT or GST number, no sales-tax rate and no currency. `fmt()` `sairnbuild.html:2267` hard-codes `$` with `en-US`, and voice input is `en-US`.

## 4. Write sites

| record | write site | fields |
|---|---|---|
| job | `saveJob()` `sairnbuild.html:5578` | id, address, client, phone, value, stage, start, target, permit, blocked, notes |
| change order | `saveCO()` `sairnbuild.html:5166` | id, job_id, description, amount, labour_hrs, status, requested_by, sent_at, accepted_at, reason, linked_task_id, schedule_impact_days. **No cost field** |
| cost | `saveCost()` `sairnbuild.html:5405` | id, job_id, cost_code, kind, vendor, budget, committed, actual. **No forecast** |
| draw | `saveDraw()` `sairnbuild.html:5727` | id, job_id, draw_no, period_end, pct_complete, amount, retainage_pct, retainage_held, status, requested_at, received_at, amount_received |
| lien waiver | `saveLw()` `sairnbuild.html:5908` | id, job_id, draw_id, party, type, amount, status, date |
| payment to sub | `saveChk()` `sairnbuild.html:6302` | id, job_id, check_no, payee, amount, category, status, issued_at, cleared_at |
| subcontractor | `saveSub()` `sairnbuild.html:6536` | company, trade, w9_on_file, coi_expiry, licence_no, licence_expiry, prequal_status, bonding_capacity, … |
| RFI / submittal / daily log | `saveRfi()` `sairnbuild.html:4513`, `saveSubmittal()` `sairnbuild.html:4599`, `saveLog()` `sairnbuild.html:4264` | per their panels |

There is no invoice record: billing is the draw.

## 5. Corrections to the record on file

1. **09-27 §1.1 / §7.3, "sub award gated server-side": wrong.** It is client-side only, and the award itself is a no-op (§1).
2. **09-03 and 09-27 B3/I-1 "wrong denominator, forecasting absent": out of date.** The calculation was fixed in `25d1c0009`; the forecast has no writer.
3. **Line numbers have drifted:**
   - `jobWIP` 6623 / ~7434 → **7610**;
   - `budgetFor` ~3555 → 3661;
   - `bldEnterApp` ~2934 → 3029.

## 6. Unverified: read before quoting anything externally

- **Every 09-27 statute citation** is [SNIPPET]: ORC 4722, 1311, 4113 and 153, 40 CFR 745, and OSHA 1926. The Ohio residential lien clock ("first vs last furnishing") is flagged unresolved there, and pending HB 568 is unconfirmed.
- **Every 09-03 market claim** is supplied testimony.
- **No regulator was read for this document.**

## 7. What this does not do

It changes no code. Two items are defects in records the app already writes:
- §1 (the award);
- §2 B3 (the forecast field nothing writes).

Each needs a claim on `sairnbuild.html`, a fix and a register record. Making the lien waiver gate a payment (X8) **changes what gets paid**, so it is Michael's decision.
