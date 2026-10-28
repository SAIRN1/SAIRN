# Worldwide competitive-gap audit: SAIRNmechanical

**fourth / b64, 2026-10-28.** This continues the worldwide series after roofing, senior and vet (b63). SAIRNmechanical was the third app b36 named with **zero** audits. It was skipped in b63 while cody held a claim on it, and that claim has since cleared.

## Where this comes from

**It is built only from research already on file.** Nothing was fetched for this pass:

| source | read | its evidence grade, as it states it |
|---|---|---|
| `docs/superpowers/specs/2026-08-27-sairnmechanical-shared-platform-competitive-research.md` | lines 1–730 and 839–1132; §4–§5 (other apps) and §10 (sources) skipped | primary [P] where the page was read; search snippet [S] otherwise |
| `docs/superpowers/specs/2026-08-21-plumbing-electrical-hvac-worldwide-research.md` | in full | cited; the EU F-gas dates corrected on 09-17 |
| `docs/2026-09-15-…-mechanical-and-five-apps.md` §2 and `docs/2026-09-17-senior-mechanical-competitive-gap-rederived.md` | the mechanical parts | status re-derivations |

**Audit only:** `sairnmechanical.html` is in 0 of this batch's commits. Each status below comes from reading the code at `8259a6dd2`.

---

## 0. The result

> **SAIRNmechanical is a compliance registry, not yet a field-service app.** It holds what US federal refrigerant and credential rules ask about. There is no job record, no invoice record and no inspection record, so **every non-US regime the research names has nothing to attach to.**

The registry side:
- credentials, append-only on the server;
- site assets, carrying the AIM Act and CARB scope engine;
- insurance.

The missing side:
- jobs: `mechNotLive('Job entry')` at `sairnmechanical.html:732`;
- invoices: `mechNotLive('Invoice entry')` at `sairnmechanical.html:1091`;
- inspections: none at all.

**The worldwide gap is two layers deep.** First the records, then the axis.

---

## 1. What is built, and how far

| gap | status | where |
|---|---|---|
| A1 credential registry (US state licence, EPA 608, NATE, ASSE 6010, backflow) | **built, US types only.** The server refuses any other type with `UNKNOWN_RECORD_TYPE` | `RECORD_TYPES` `api/_lib/mech-credentials.js:73`; `mechCredAdd` `sairnmechanical.html:2730` |
| G3 / A6 credential expiry drives dispatch | **advisory, not a gate.** The eligibility call exists, and the code says outright it is "not a gate" | `mechEligibility` `sairnmechanical.html:2672` |
| A2 site asset registry | **built, with no service history** (the comment at `sairnmechanical.html:915` says so) | `mechAssetAdd` `sairnmechanical.html:2986` |
| G11 refrigerant | **scope and AIM repair clock built; leak rate deliberately refused; no transaction ledger; lb only** (`kg`, `tCO2e` ×0) | `evaluateRegistry()` `api/_lib/mech-assets.js:463`, `aimRepairClock()` `api/_lib/mech-assets.js:398` |
| G13 warranty | **expiry tracked; no registration deadline** | `classifyWarranty()` `api/_lib/mech-assets.js:202` |
| G12 data portability | **partial:** two registers export to CSV. Three `mechNotLive('CSV export')` buttons remain, and jobs, invoices and contracts cannot be exported because they do not exist | `mechExportDataset` `sairnmechanical.html:2613` |
| Tier C Manual J/D/S | **disclosed, not built** (ACCA-approved software required) | `MECH_MANUAL_J_SYS` `sairnmechanical.html:1400` |
| insurance | **built** | `mechInsAdd` `sairnmechanical.html:3173` |

**Absent in the code** (grep counts in brackets):
- G1/G21: add a second trade in place (`entitlement`×0);
- G2: subcontractor compliance (`subcontractor`×0);
- A3: one agreement spanning trades (`PPM`, `AMC` ×0);
- A4/G8: permit filing;
- A5/G17/G20: certificate engine, intervals and instrument calibration (`DGUV`, `CP12`, `EICR`, `calibrat` ×0);
- A7/G15: outbound compliance submission;
- G5: the mid-market financial layer (`retainage`, `G702` ×0). `api/_lib/wip-accounting.js` exists on the platform but is not wired into this app;
- G19: apprenticeship hours;
- Tier B: truck stock, pricebook (one flat rate card), financing, punchout/EDI and dataplate OCR.

## 2. One defect found while reading: the quote does not store its client

`saveQuote()` `sairnmechanical.html:1467` stores `{id, date, trade, text}`. The client typed into `fq-client` is **not saved**, so a saved quote cannot say who it was for. Unlike the gaps above, this is a defect in a record the app already writes. It is not fixed here: audit only.

---

## 3. Outside the US

| jurisdiction | regime (as the research names it) | the record it would land on | present |
|---|---|---|---|
| EU | F-gas certification Categories I–III (EU 2015/2067). Dates corrected 09-17 to 11/12 Mar 2027 and 12 Mar 2029. **The research never names 2024/573** | credential type; asset charge in kg and tCO2e | no |
| UK | Gas Safe register, Part P self-certification, BS 7671 certificates (EICR) | credential type; inspection or certificate record (none exists) | no |
| DE | Meisterpflicht / Handwerksrolle, Kälteschein, DGUV V3 inspection | credential type; inspection record with interval | no |
| CA | ESA, TSSA, TSASK provincial authorities | credential `jurisdiction` (the field exists) | no |
| NZ / AU | Certificate of Compliance (NZ, NSW, VBA) | certificate record and outbound submission | no |
| FR | e-invoicing, said to be "mandatory 2026", **[S] and never re-verified** | invoice (none exists) | no |

**What the app would need before any of these, in order:**
1. a credential type list that is not US-only. `RECORD_TYPES` is the single place, and the server enforces it;
2. **an inspection or certificate record.** UK, DE and NZ/AU all land there, and it does not exist;
3. an invoice, for FR. Neither the invoice nor a tax-id field exists.

**Locale:**
- `<html lang="en">`;
- `en-US` appears twice;
- `$` is hard-coded, and there is no currency formatter;
- temperatures are °F and wind is mph;
- charge is in lb;
- there is no `country` field anywhere.

The research **never mentions** Schornsteinfeger or BImSchV. That is a coverage gap in the research, not a finding about the app.

---

## 4. Write sites

| record | write site | fields |
|---|---|---|
| quote | `saveQuote()` `sairnmechanical.html:1467` | id, date, trade, text. **No client** |
| cheque | `saveCheck()` `sairnmechanical.html:1552` | id, num, date, payee, amount, memo |
| site asset | `mechAssetAdd` `sairnmechanical.html:2986` | asset_id, customer_name, site_name, site_address, asset_type, make, model, serial_no, installed_on, has_warranty, warranty_expires_on, refrigerant_type, refrigerant_charge_lb, hfc_gwp_over_53, site_state (`^[A-Z]{2}$`), gwp_over_150, leak_detected_on, leak_repair_verified_on |
| credential | `mechCredAdd` `sairnmechanical.html:2730` | credential_id, technician_id, record_type, epa_section, jurisdiction, credential_no, issuer, issued_on, has_expiry, expires_on. **Append-only on the server** |
| insurance | `mechInsAdd` `sairnmechanical.html:3173` | policy_key, kind, carrier, policy_no, effective/expires, limits, certificate_holder, endorsements |

**Records that do not exist:** job, invoice, inspection, refrigerant transaction.

**The roster has no add-employee caller in the HTML.** `api/mech-auth.js` has `setup`; the page calls only roster, set_active, login, bootstrap and whoami.

## 5. Corrections to the record on file

1. **G3 "no caller" (09-17) is overtaken.** The eligibility call is `sairnmechanical.html:2685`. The 09-26 header's `:2474` has drifted.
2. **G12 "NOT BUILT" (09-17, 08-27 header) is wrong.** Two registers export.
3. **G11 "substantially built" overstates it** against the 08-21 research's own definition, which includes leak rate. The code refuses to compute leak rate, on purpose.
4. **The French e-invoicing date is not re-verified.** It is [S] in 08-27 and nobody re-checked it. The roofing pass (b63) found a comparable mandate (ES Verifactu) that had slipped a year.
5. **The 2026-10-06 verification's §5 citations for mechanical point into `stonedesk.html`.** It inferred the app from the filename.
6. **Stale server comments.** They say `mech_checks` keys on the check number; the client mints an `id`, stored as `check_id`.

## 6. Unverified: read before quoting anything externally

- Every [S] claim in 08-27.
- The research's own do-not-cite figures: C2's "62–76%" permits, C3's "60%" lock-in and C5's warranty percentage.
- The C1 note that **no vendor was verified to auto-block dispatch** on an expired credential.
- The DIN VDE withdrawal (unconfirmed).
- **No regulator was read for this document.**

## 7. What this does not do

It changes no code. The quote-client defect (§2) is the cheapest real fix and needs a claim on `sairnmechanical.html`. Everything in §3 waits on a decision that SAIRNmechanical will have **job and inspection records at all**, which is a product decision, not a gap fix.
