# Worldwide competitive-gap audit: SAIRNsenior

**fourth / b63, 2026-10-28.** The next app in the worldwide series, after sairnroofing, also b63. Two audits already exist, and this one does not replace either:
- the August worldwide pass, `docs/superpowers/specs/2026-08-26-competitive-gap-audit-roofing-dental-senior.md` §5;
- the September competitor-facing pass, `docs/cloud-research/sairnsenior-external-competitive-gap-audit-2026-09-26.md`.

What this one does is put both against the code as it stands, because **five of the September findings have since been overtaken by code.**

## Where this comes from

**It is built only from research already on file.** Nothing was fetched for this pass:

| source | read | its evidence grade |
|---|---|---|
| August audit §0–§2, §5–§8 | in full | vendor synthesis; §7 lists the unverified items |
| `docs/2026-09-17-senior-mechanical-competitive-gap-rederived.md` | in full | status re-derivation |
| September external audit | in full | **[SNIPPET] throughout.** 38 of its 39 page fetches were blocked by egress, so no source page was ever opened (its §0.1) |

**So every statutory and market claim below is, at best, as strong as a search snippet.** None was re-checked against CMS, a state Medicaid agency or the OIG on 2026-10-28.

**Audit only:** `sairnsenior.html` is in 0 of this batch's commits. Each status below comes from reading the code at `e40e86f3a`.

---

## 0. The result

> **SAIRNsenior now records most of what a US Medicaid EVV auditor asks about, and holds it in the right shape. Three of those records are kept but never shown to a reviewer, and the claim it bills from does not ask whether the visit passed EVV. It has no non-US axis at all: every regime the August pass found outside the US is absent.**

---

## 1. Five September findings the code has overtaken

| September finding | now | where |
|---|---|---|
| no visit-maintenance path with reason codes | **built** on 2026-10-15: a fixed reason list, propose-then-approve, and self-approval refused except for the owner | `CORRECTION_REASONS` `api/_lib/sen-evv-clock.js:94`, `proposeCorrection()` `api/_lib/sen-evv-clock.js:241`, `approveCorrection()` `api/_lib/sen-evv-clock.js:340`, `renderCorrectionsView()` `sairnsenior.html:3018` |
| device clock trusted, no server comparison | **partial**: the server refuses a time more than 2 minutes in the future and flags a replay older than 7 days. It stores `*_received_at` and `*_skew_ms` beside the claimed time | `checkClockEvent()` `api/_lib/sen-evv-clock.js:149` |
| credential gate on scheduling not checked | **partial**: a CPR-expiry gate on save, **client-side only** | `senCertGate()` `sairnsenior.html:2507`, called from `saveVisit()` `sairnsenior.html:3371` |
| tasks against the plan of care | **partial**: `care_tasks` is stored on the client, but clock-out records only free-text `services_notes`, and nothing compares the two | `saveClient()` `sairnsenior.html:2433`, `vsClockOut()` `sairnsenior.html:3353` |
| clock writes at ~L2994 / L3001 | **moved** to `vsClockIn()` `sairnsenior.html:3347` and `vsClockOut()` `sairnsenior.html:3353` | n/a |

## 2. What is recorded and not shown, and what billing does not ask

**These are the findings in this document that cost the least to close.** In each case the data already exists.

1. **The skew and replay flags are written and never read.** `clock_flags`, `*_skew_ms` and `*_received_at` appear **0 times** in `sairnsenior.html`, and the readiness engine does not read them. The server records exactly the signal the September audit said was missing, and no reviewer can see it.
2. **Billing does not ask whether the visit passed EVV.** `readyToBillVisits()` `sairnsenior.html:4223` takes any completed, unbilled visit, with no readiness check. The September pass names hard claim edits ("pay-on-match") in AZ, OH, MA, MO, NC, MI, TX, WI, TN and FL, all graded [SNIPPET]. In those states, a claim for a visit that failed EVV is a denied claim.
3. **The credential gate is client-side and checks CPR only.** The server write for `sen_visits` (`api/sd-data.js:7773`) carries no certification check. A direct API write schedules an uncertified caregiver.
4. **The quarterly EVV quality report is now buildable and not built.** It is PA bulletin MAB 05-25-03 (85% clean, 15% manual edits), with IL at 75% and FL at 85%, all [SNIPPET]. The correction trail that report counts now exists, but there is no edit-rate figure anywhere (`edit rate`×0, `quarter`×0).

---

## 3. The US gaps, status now

| # | gap (August §5.2 / §5.3) | status | where |
|---|---|---|---|
| A1 | EVV transmission to a state aggregator (Cures Act §12006) | **readiness built; transmit absent.** The panel says *"This is a report. It submits nothing"* | `renderReadinessView()` `sairnsenior.html:3110`, `saveEvvConfig()` `sairnsenior.html:6295` |
| A2 | offline capture | **built** (FIFO queue that stops at the first failure) | `evvQueueAdd()` `sairnsenior.html:3264`, `senFlushEvvQueue()` `sairnsenior.html:3280` |
| A2 | telephony / IVR fallback | **absent** (`IVR`×0) | n/a |
| A3 | authorisation unit burn-down | **built** | `rAuthBurnDown()` `sairnsenior.html:2648`, `saveAuthorization()` `sairnsenior.html:5515` |
| A4 | 837 / clearinghouse | **absent** (`x12`×0; the one `837` hit is a line reference) | n/a |
| A5 | applicant tracking | **built** | `saveHrApplicant()` `sairnsenior.html:5992` |
| A6 | training hours and credentials | **built** | `saveTrRule()` `sairnsenior.html:3973`, `saveTrRecord()` `sairnsenior.html:4012` |
| A7 | referral-source CRM | **built** | `saveRfSource()` `sairnsenior.html:3531`, `saveRfReferral()` `sairnsenior.html:3585` |
| B1 | multi-branch | **built** | `saveBranch()` `sairnsenior.html:5774` |
| B2 | denials and appeals | **built** | `blMarkDenied()` `sairnsenior.html:4528`, `blStartAppeal()` `sairnsenior.html:4537` |
| B3 | franchise royalty | **built** | `saveFranchiseAgreement()` `sairnsenior.html:5150` |
| B4 | payer contracts | **built** | `savePayerContract()` `sairnsenior.html:4785` |
| B5 | consolidated and per-branch P&L | **revenue and hours only; profit refused** (there is no overhead or cost-of-care data) | `brRollup()` `sairnsenior.html:5681` |

**Still absent from the September list:**
- distance check, geofence, and the same caregiver at two clients at once (location is a single reading, `vsGetPosition()` `sairnsenior.html:3229`);
- minimum duration and hospitalisation checks (NY Comptroller 2022-S-31);
- open-shift broadcast;
- the live-in exemption (VA DMAS "UB"). It is listed as not computed in payroll.

**Not built, on purpose:** 80/20 / CMS-2442-F. The September pass says rescission may be pending: *"do not build"*.

**On the aggregator list:**
- The selector (`sairnsenior.html:1268`) has **no Netsmart option**, although the September pass names Netsmart as Georgia's state-selected aggregator.
- The readiness header still names *"a trading-partner agreement per aggregator"* as the gate (`api/_lib/sen-evv-readiness.js:29`). The September pass says the gate is a **sponsoring pilot agency** per state (CO, CT, IN, PA). **That makes the code's own explanation the stale part, not the research.**

---

## 4. Outside the US: every regime absent

The August §5.5 regimes. Not one is present (`SGB`, `Pflegegrad`, `kokuhoren`, `GIR`, `Vecozo`, `kjernejournal`, `€`, `¥` and `i18n` all ×0):

| jurisdiction | regime (as the research names it) | the record it would land on |
|---|---|---|
| DE | SGB V/XI data exchange (DTA), Pflegegrade, SIS documentation | the client (care level) and the visit (billing record) |
| JP | 国保連 (kokuhoren) claims; 要介護度 care-level certification | the client and the claim |
| FR | APA / GIR, télégestion | the client (GIR level) and the visit: télégestion *is* EVV |
| NL | WLZ / WMO / ZVW over Vecozo | the claim |
| SE | LOV | the agency (provider choice) |
| NO | kjernejournal (vendor-sourced only) | the client |

**FR télégestion is the closest fit to what is already built.** It is visit verification by phone or device, which is the A1/A2 machinery. **DE and JP both need a care-level field on the client that does not exist.**

Denmark, Poland and Brazil were never searched, because the research ran out of quota. There is no evidence either way.

---

## 5. Write sites

| record | write site | fields |
|---|---|---|
| client | `saveClient()` `sairnsenior.html:2433` | id, name, phone, address, diagnosis, payer, authorized_hours, status, notes, care_tasks, member_id, assigned_employee_id, branch_id |
| caregiver | `saveCaregiver()` `sairnsenior.html:2758` | id, name, phone, cpr_expiry, bgcheck_date, status, aide_type, program, state_caregiver_id, employee_id, branch_id |
| visit (schedule) | `saveVisit()` `sairnsenior.html:3371` | client_id, scheduled_date, scheduled_start, scheduled_end, service_type, assigned_employee_id, status |
| visit (EVV) | `vsClockIn()` `sairnsenior.html:3347`, `vsClockOut()` `sairnsenior.html:3353` | clock_in/out_at, lat, lng, status, services_notes. **The server splits the fields by role** and turns a changed time into a correction |
| claim | `generateClaim()` `sairnsenior.html:4363` | visit_id, payer, service_date, hours_billed, rate, amount, rate_source, auth_status, auth_id, auth_number, status |

## 6. Corrections to the record on file

1. September §1 says there is no visit-maintenance path, and §4.4 says the device clock is trusted. Both are **overtaken** (§1 above).
2. The August §5 header says "5 tables, 10 nav panels". There are now **18 panels** and **21** `sql/sairnsenior_*` files.
3. **Two places where the code is stale, not the research:**
   - The readiness header names the wrong gate (§3).
   - A comment at `sairnsenior.html:5677` says *"This app holds no payroll"*, but `runPayroll()` `sairnsenior.html:2926` computes gross payroll. The B5 refusal itself still holds.
4. Marker counts have moved, with `EVV` at 70, then 154, then **172**. The counts are floors.

## 7. Unverified: read before quoting anything externally

- **Every September claim** is [SNIPPET]: the state edits, the PA, IL and FL thresholds, the OIG and Comptroller citations, and Netsmart in Georgia.
- **August §7** lists the per-state EVV models, the state training rules and 80/20 as unverified.
- The two video-EVV patents (US 9,471,749 and US 11,915,806) are **flags only, with the assignees unconfirmed.** The app has no video check-in.
- **No regulator was read for this document.**

## 8. What this does not do

It changes no code. The §2 items are the cheapest to close, because the data already exists, but each needs its own claim on `sairnsenior.html` or `api/sd-data.js` and its own record. A billing gate on EVV readiness (§2 item 2) **changes what gets paid**, so it is a decision for Michael, not a default.
