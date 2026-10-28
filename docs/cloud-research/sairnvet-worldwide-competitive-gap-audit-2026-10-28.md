# Worldwide competitive-gap audit: SAIRNvet

**fourth / b63, 2026-10-28.** The third app in this batch, after sairnroofing and sairnsenior. SAIRNvet already has four audits:
- the 09-03 supplied-research pass;
- the 09-24 internal pass;
- the 09-25 external pass;
- the 09-26 pricing/CDS pass.

**This one does not refresh the market. It puts their findings against the code, and it finds two things none of them saw.**

## Where this comes from

**It is built only from research already on file.** Nothing was fetched for this pass:

| source | its evidence grade, as it states it |
|---|---|
| `docs/superpowers/specs/2026-09-03-competitive-gap-audit-build-vet-biz-grounds-cash.md` §4 | "supplied research… testimony"; no URLs, no patent screen |
| `docs/SAIRNvet-competitive-gap-audit-2026-09-24.md` | internal |
| `docs/cloud-research/SAIRNvet-external-competitive-gap-audit-2026-09-25.md` | vendor-domain snippets, not opened (egress blocked). Patent numbers are third-party index snippets, unverified |
| `docs/cloud-research/sairnvet-external-competitive-gap-audit-pricing-cds-2026-09-26.md` | snippets; pricing is aggregator figures, low confidence |
| the 09-26 companion, on branch `fourth/sairnvet-external-gap-audit-2026-09-26` (`f3cfb56ea`), **never merged to main** | the only rows graded [OPENED] |

**None of the five names a non-US instrument as a gap.** The following return zero hits in all of them: the EU Veterinary Medicines Regulation 2019/6, the UK VMD, the cascade, antimicrobial-use reporting, VFD, PDMP, rabies certificates and GDPR. Section 4 says what that means for a *worldwide* audit.

**Audit only:** `sairnvet.html` is in 0 of this batch's commits. Each status below comes from reading the code at `e40e86f3a`.

---

## 0. The result

> **SAIRNvet's clinical safety layer is real: the contraindication gate blocks before any AI call. Two records the audits count as built are not what they say. The SOAP note keeps no note, and the controlled-drug register is neither append-only nor, as far as the code shows, witnessed.**

---

## 1. Two findings none of the four audits saw

### 1.1 The SOAP record does not store the SOAP note

`generateSOAP()` `sairnvet.html:8916` asks the model for a full Subjective / Objective / Assessment / Plan note. It writes the result **to the screen only** (`soap-result`). What it then saves, at `sairnvet.html:8955`, is:

    {id, date, patient, complaint: subj.slice(0,60), recorded_by_role, author, status: 'Draft'}

So the stored record holds **the first 60 characters of the complaint**, with no objective, no assessment and no plan:
- the vet's sign-off (`onSoapSignoff()` `sairnvet.html:8870`) marks *that* record "Reviewed";
- the scribe path (`scribeAcceptDraft()` `sairnvet.html:10525`) adds provenance fields, not a body.

**Every audit on file counts SOAP notes as built.** Medical-record retention law is not in the research on file, so this document cites no instrument. It does not need one to say that **a reviewed medical record with no content is not a medical record.**

### 1.2 The controlled-drug register: append-only in the server's own words, rewritten in place by the client

- **What the server says.** `api/sv-witness.js` describes the register as append-only: *"a correction is a SECOND row"*. Its `requireWitness()` `api/sv-witness.js:356` requires an `X-SV-Witness` token. Two-person signing is a per-licence setting, off by default (Michael's 2026-09-13 decision, in that file's header).
- **What the client does.** `logControlledUse()` `sairnvet.html:7837` **rewrites one row per drug in place**: `{drug, schedule, onHand, unit, lastTransaction, witness}`. The witness is a **free-text name**. The export comment near `sairnvet.html:9597` says, correctly, that the log is *"NOT APPEND-ONLY"*.
- **The gap between them.** `sairnvet.html` contains **no** `x-sv-witness`, `witness_token` or `sv-witness` reference (0 hits), so the client never obtains the token the server requires.
- **Inference, NOT live-verified:** the server backup write of `sv_controlled` is probably refused with WITNESS_REQUIRED on every sync, which would leave the register only in the browser. **This is the first thing to drive live.**

The 09-25 audit describes *"a two-person witness lock… keyed to a prescriber tier"* as a SAIRN advantage over competitors. **The lock exists on the server. The app does not use it.**

---

## 2. The audits' gaps, status now

| # | gap | status | where |
|---|---|---|---|
| 1 | AI radiograph triage | **absent**: imaging stores no image (`dicom`, `x-ray` ×0) | `addImagingStudy()` `sairnvet.html:3928` |
| 2 | ambient scribe | **built**, with consent recorded. It refuses unless a transcription host is configured | `scribeClientAnswer()` `sairnvet.html:10339`, `api/sairnvet-transcribe.js:149` |
| 3 | treatment → invoice (charge capture) | **absent**: an invoice is one typed total with no line items, and it can be hard-deleted | `addInvoice()` `sairnvet.html:7090` |
| 4 | client online booking | **absent**: "Client Requests" is a staff-entered log (`booking`×0) | `addPortalRequest()` `sairnvet.html:5933` |
| B1 | one chart across sites | **absent**: no `site_id` or `location_id`, and the owner is a free-text string on the patient | `addPatient()` `sairnvet.html:5627` |
| B2 | central vs local permissions | **partial**: a per-resource server role table now exists (`api/_lib/sv-roles.js`), but there is no central/local axis | `api/sd-data.js:16255` |
| B3 | inventory / reorder | **absent** (`reorder`×0) | n/a |
| B4 | roll-up dashboard | **absent**: a manual-entry panel, disclosed as such | `addLocation()` `sairnvet.html:7753` |
| 9 | contraindication gate / species dosing | **built, and it blocks before any AI call**. The green "Verified" tick was withdrawn from 284 rows on 2026-09-26, and a code comment says 480 of 485 rows cite no source | `calculateDoseAI()` `sairnvet.html:8458`, `onDoseVetSignoff()` `sairnvet.html:8363` |
| 10 | interaction checking | **advisory only**: 15 rules, which warn and do not block. The 09-26 table calls this part of a "hard gate"; it is not | `INTERACTION_MATRIX` `sairnvet.html:8389` |
| 13 | DEA controlled-substance register | **partial**: see §1.2 | `logControlledUse()` `sairnvet.html:7837` |
| 15 | client telemedicine | **partial by design** ("doesn't host video"). VCPR appears 0 times in the code, against a research note that most US states require an in-person exam | `addTeleconsult()` `sairnvet.html:4489` |
| 16 | staff photo/video peer consult | **built** (phase 1). Images stay local | `savePeerConsults()` `sairnvet.html:9757` |
| 17 | food-animal withdrawal | **built as a banner**. By design it states no withdrawal figure | `calculateDoseAI()` `sairnvet.html:8458` |
| 14 | per-employee auth | **built** | `api/sd-data.js:16233` |

**Still open from 09-26, not re-checked here:** exotic dosing has no external reference to validate against. Exotic rows refuse to give a number and name Carpenter's formulary instead.

---

## 3. Records the app does not have

| record | status |
|---|---|
| **prescription** | no write site anywhere |
| **vaccination** | no write site. Vaccination exists only as an appointment or reminder type (`addReminder()` `sairnvet.html:6053`), and rabies only as a seed reminder |
| dose audit | `logDoseAudit()` `sairnvet.html:8290` stores a timestamp and an id, **not who acted** |

---

## 4. Outside the US: the research never looked

The other worldwide audits in this series could list the non-US regimes their research found. **For SAIRNvet the research on file found none**, and that is a coverage hole, not a clean result:

- The EU Veterinary Medicines Regulation 2019/6, the UK VMD, the cascade, antimicrobial-use reporting and GDPR are named **nowhere** in the five sources.
- In the code, `2019/6`, `VMD`, `cascade`, `PDMP` and `GDPR` return 0 hits. `antimicrob`, `FARAD` and `extra-label` appear only inside the drug data line (`VET_DRUGS` `sairnvet.html:2056`).
- The 09-24 pass mentions the German GOT fee schedule as an *idea source, not a gap*. The app has no German locale; the seven "GOT" hits are the English word "got".

**What a worldwide pass would have to research first, as a list rather than a finding:**
1. prescription records under 2019/6. No article is cited here, because none was read;
2. antimicrobial sales and use reporting;
3. the UK cascade;
4. rabies and pet-passport certificates;
5. veterinary records under GDPR.

**Every one of them lands on a record that §3 says does not exist:** the prescription and the vaccination. Whatever any of them says in detail, SAIRNvet would need those two records before it could answer.

---

## 5. Write sites

All writes go through `st()` `sairnvet.html:2169`, then `svSyncCollection()` `sairnvet.html:2532`, then the 42-entry `SV_RESOURCES` map in `api/sd-data.js`.

| record | write site | fields |
|---|---|---|
| patient | `addPatient()` `sairnvet.html:5627` | id, name, species, breed, owner (free text), age, lastVisit, status, added, visitsThisYear, chartComplete |
| appointment | `addScheduleAppt()` `sairnvet.html:3480` | id, time, patient, type, doctor, room, status |
| SOAP note | `generateSOAP()` `sairnvet.html:8916` | as in §1.1: **no note body** |
| scribe consent | `scribeClientAnswer()` `sairnvet.html:10339` | asked_at, patient, answer, statement_version, asked_by_role, asked_by_employee_id |
| controlled drug | `logControlledUse()` `sairnvet.html:7837` | drug, schedule, onHand, unit, lastTransaction, witness. **Rewritten in place** |
| invoice | `addInvoice()` `sairnvet.html:7090` | id, num, client, amount, status, date |

## 6. Corrections to the record on file

1. **SOAP notes:** counted as built everywhere. The stored record has no body (§1.1).
2. **The 09-25 witness lock:** it is on the server and unused by the client. The register is rewritten in place (§1.2).
3. **The 09-24 and 09-26 "verified calculation" / "Verified" language:** overtaken on 2026-09-26, when the ticks were withdrawn.
4. **The 09-26 "hard gate" for interactions:** only the contraindication check blocks.
5. **09-24 §1.4's "41 SV_RESOURCES":** the map holds **42**.
6. **The 09-03 line citations have moved:** `:2518` → `:3870`, and `:1386` → `:1612`.
7. **A stale comment in the app:** `sairnvet.html:10655` still says no `api/sv-*.js` file exists and login is entirely client-side. `api/sv-auth.js` and `api/sv-witness.js` both exist. The comment is wrong, not the code.

## 7. Unverified: read before quoting anything externally

- **Every competitor and pricing claim** is a snippet (09-25, 09-26), or testimony (09-03).
- **The SignalPET and Mars patents** (09-25) are third-party index snippets.
- **The VCPR state counts and the AVMA 38%→29.2% telemedicine figure** are flagged unverified in 09-26.
- **The WITNESS_REQUIRED outcome in §1.2 is an inference from the code**, not a live result.
- **No regulator was read for this document.**

## 8. What this does not do

**It changes no code.** §1.1 and §1.2 are defects in records the platform already claims, not market gaps. Each needs:
- its own claim on `sairnvet.html`;
- a live drive of the `sv_controlled` sync, before anyone believes §1.2's inference in either direction;
- a register record.
