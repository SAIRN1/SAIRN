# SAIRNsenior and SAIRNmechanical competitive-gap status, re-derived 2026-09-17 — and SAIRNmechanical has a capability the product never calls

**Derived 2026-09-17 (CC) against the code at HEAD.** A **status** document, per
the convention `docs/2026-09-02-competitive-gap-status-rederived.md` set, using
the method of `docs/2026-09-17-sairnroofing-competitive-gap-rederived.md`:
marker counts, then a hand-read of every ambiguous hit, then a **wiring check** —
does the capability have a panel, a nav target and a caller.

**SAIRNdental was requested in the same pass and was NOT started.** Fourth
claimed overlapping work 0.1h before this began: *"…sairndental CDT code
catalogue versioning"*, which is that audit's row **A4, CDT annual code
maintenance**. `sairn_claim.py` blocked on `same app: sairndental`, the block
is current rather than stale, and reconciling a row somebody is closing while
the file moves underneath would produce a status column wrong on arrival.
Flagged rather than reworded past the matcher. **SAIRNdental still needs this
pass.**

---

## 0. The finding, stated first: SAIRNmechanical claims an enforcement it never invokes

The 08-27 research names **G3** as a market-wide gap: *"Credential-expiry →
dispatch-eligibility enforcement claimed, not documented"* — vendors say they
gate dispatch on credentials and none of them shows the mechanism.
**SAIRNmechanical has reproduced that gap in its own product.**

Everything except the call exists:

| Layer | State at HEAD |
|---|---|
| Engine | `api/_lib/mech-credentials.js` → `evaluateEligibility()`, with the EPA-608 section rule (Universal covers all; otherwise an exact match) and a refusal on an empty requirement list rather than *"anyone may go"* |
| Endpoint | `api/sd-data.js:1452` dispatches `action === 'eligibility'`, compute-only, writes nothing |
| Registry | `api/_resources/sairnmechanical.js:90` — `mech_credentials: ['eligibility']` |
| Tests | 10+ arms in `api/_lib/mech-credentials.test.js` driving the engine directly |
| **Caller** | **NONE.** Every `mechData(...)` call in `sairnmechanical.html` is `read` (×3) or `write` (×3). The string `eligibility` appears **once** in the whole app file |

And that one occurrence is a claim:

> `sairnmechanical.html:757` — Technician Credentials · *"Licences,
> certifications and expiry — **the record dispatch eligibility is computed
> from**"*

**Nothing computes it.** A dispatcher reading that subtitle is told the
credential board feeds an eligibility decision; the app never asks for one, and
there is no dispatch gate to receive the answer. This is the `logDoseAudit`
shape exactly — the SAIRNvet finding where the only code reading the
controlled-substance audit trail was the function that appended to it — with a
UI sentence on top asserting the missing half.

**It is not a security hole**, and that distinction matters: the endpoint is
gated and nothing is being bypassed, because nothing is being called. It is an
overclaim plus an unreachable capability, and the fix is small — one call from
the credentials panel, or a scheduling-side gate, or the subtitle corrected.
**Which of those is a product decision and is not made here.**

---

## 1. SAIRNsenior — twelve rows, and the audit's own sharpest finding is half-closed

The 08-26 audit's §5.1 calls A1 *"a defect, not a gap"*: an EVV aggregator named
in a dropdown with no transmission behind it.

**18 panels, 18 nav targets, identical sets — nothing built is orphaned.**

| # | Audit said (2026-08-26) | At HEAD, 2026-09-17 | Evidence |
|---|---|---|---|
| **A1** EVV transmission to a state aggregator | *"Aggregator named in a dropdown, no transmission"* | **HALF-CLOSED, and the half that is missing is named** | `api/_lib/sen-evv-readiness.js` reports per-visit whether a submission would have the data it needs. Its own header states it *"does not transmit, does not persist"* and names the three blockers — a trading-partner agreement per aggregator, a place to hold per-agency credentials, and a wire format that could not be verified from primary sources. `EVV` × 70, `aggregator` × 14, **`transmit` × 0** |
| **A2** telephony EVV + offline capture | *"Zero occurrences of telephony or offline"* | **OFFLINE CLOSED, TELEPHONY OPEN** | `offline` × 20, including a real offline-EVV path and `sairnsenior-offline-evv.test.js`. `telephony` × 2, both in a comment explaining this is *"the half that does not need a phone system"* |
| **A3** authorisation tracking with unit burn-down | *"authorization 8 hits; units zero. No burn-down"* | **CLOSED** | `panel-authorizations`, `sql/sairnsenior_authorizations_schema.sql`, `sairnsenior-authorizations.test.js`. `authoriz*` × 88, `units` × 72, `burn-down` × 17 |
| **A4** 837 / clearinghouse | *"Zero for 837 or clearinghouse — the claim leaves by hand"* | **STILL OPEN, vendor-gated** | `837` × 0, `clearinghouse` × 0 |
| **A5** applicant tracking | *"Zero for applicant"* | **CLOSED** | `panel-hiring`, `sql/sairnsenior_applicants_schema.sql`, `sairnsenior-hiring.test.js`. `applicant` × 46 |
| **A6** training-hour / credential tracking | *"Zero occurrences of training"* | **CLOSED** | `panel-training`, `sql/sairnsenior_training_schema.sql`. `training` × 35, `in-service` × 16 |
| **A7** referral-source CRM | *"Zero occurrences of referral"* | **CLOSED** | `panel-referrals`, `sql/sairnsenior_referrals_schema.sql`. `referral` × 78 |
| **B1** multi-branch / multi-state | *"Zero for location_id; branch 3 hits"* | **CLOSED** | `panel-branches`, `sql/sairnsenior_branches_schema.sql`, `sairnsenior-branches.test.js`. `branch_id` × 25, `branch` × 74 |
| **B2** denials and appeals | *"denial 17 hits (Mark Denied); appeal zero"* | **CLOSED** | `sairnsenior-appeals.test.js`. `appeal` × 114 |
| **B3** franchise reporting and royalty | *"Absent"* | **CLOSED** | `panel-franchise`, `sql/sairnsenior_franchise_schema.sql`, `sairnsenior-franchise.test.js`. `royalt*` × 78 |
| **B4** payer contract management | *"Absent"* | **CLOSED** | `panel-contracts`, `sql/sairnsenior_payer_contracts_schema.sql`, `sairnsenior-payer-contracts.test.js`. `payer` × 136 |
| **B5** consolidated + per-branch P&L | *"Absent"* | **HALF BUILT AND HALF REFUSED, in writing** | `per-branch` × 3, `P&L` × 2 — and both `P&L` hits are the refusal: *"This app holds no payroll, no overhead and no cost of care, so a 'profit' figure here would be an invented number on a screen a Tier B buyer…"*. The direct-labour half ships; calling it profit is declined |

### 1.1 What is genuinely still open for SAIRNsenior

**Two rows, and both are blocked outside engineering.**

* **A4 — 837 / clearinghouse.** Zero on both markers. Same class as SAIRNdental
  A2/A3 and roofing B6: it needs a clearinghouse relationship, not a module.
* **A1's transmission half and A2's telephony half.** Each needs a commercial
  agreement (an aggregator trading-partner agreement; a telephony provider) and
  A1 additionally needs a credential-storage decision the open-work index
  already carries as open.

**Everything else is closed, and B5 is the one to read carefully**: it is
counted here as half-built because the app says so itself. An export of that
screen labelled "profit" would be the fabricated-KPI defect, and it was refused
on purpose.

---

## 2. SAIRNmechanical — a different kind of document, reconciled on its own terms

The 08-27 research is **not** a gap-state table. It is market structure plus a
21-row consolidated list (§9a) of what the MARKET lacks across three trades, and
a §5 of cross-application findings. So "is this row closed" is only a meaningful
question for the subset that is SAIRNmechanical-buildable at all.

**§5 Row 1 was re-derived on 2026-09-15 and is closed** (StoneDesk's
subcontractor compliance layer, shipped `c6dcb69f`). Not repeated here.

| # | The market gap | SAIRNmechanical at HEAD | Verdict |
|---|---|---|---|
| **G3** | credential-expiry → dispatch eligibility *claimed, not documented* | engine + endpoint + registry + tests, **and no caller**; the panel subtitle claims it | **REPRODUCED IN OUR OWN PRODUCT — see §0** |
| **G11** | refrigerant / F-gas ledger, no analogue in the other trades | `refrigerant` × 29, `EPA` × 22, `608` × 14; EPA-608 section is a first-class field with the Type I/II/III/Universal equipment rule, and Site Assets carries a refrigerant charge per unit | **Substantially built** |
| **G13** | manufacturer warranty registration left manual | `warrant*` × 24 — but hand-read, they are the doc-scanner's document-type list and a `warranty` field on a site asset. There is no registration deadline and no certification gate, which is what SAIRNroofing's A1 built | **PARTIAL: warranty data captured, registration clock absent** |
| **G2** | subcontractor compliance not integrated into dispatch | `subcontractor` × 0, `COI` × 0 | **Absent.** The shared layer exists platform-side (`api/_lib/subcontractor-compliance.js`, used by SAIRNroofing) and is not wired here |
| **G5** | mid-market financial layer absent from SMB tools | `WIP` × 0, `retainage` × 0, `job cost` × 0 | **Absent.** `api/_lib/wip-accounting.js` exists platform-side and is not wired here |
| **G8** | permit filing fragmented by jurisdiction and trade | `permit` × 0 (`jurisdiction` × 14 is the credential field) | **Absent** |
| **G17** | inspection intervals as fixed lookups, not computed from risk | `inspection interval` × 0; both `inspection` hits are the doc-scanner type list | **Absent** |
| **G19** | apprenticeship OJT/RTI progression | `apprentice` × 0, `OJT` × 0, `RTI` × 0 | **Absent** |
| **G20** | test-instrument calibration validity | `calibrat*` × 0 | **Absent** |
| **G15** | outbound compliance submission is nobody's modelled object | `submission` × 0 | **Absent** — and it is the audit's own strongest cross-market row (3 trades, US/UK/AU/NZ/EU) |
| **G12** | lock-in / data portability dominates real-world pain | `export` × 12 — and the CSV button calls `mechNotLive('CSV export','exported')`, which toasts *"CSV export is not live yet — nothing was exported"* | **NOT BUILT, and DISCLOSED rather than faked** |
| G1, G4, G6, G9, G10, G14, G16, G18, G21 | market-structure, content-licensing or other-vendor findings | not app-state rows | **Not applicable to a status column** |

### 2.1 G12 is the honest one and is worth naming

A CSV button that toasts *"not live yet — nothing was exported"* is the third
instance of this platform's disclosure pattern, after SAIRNroofing's *"This is
not an EDI connection"* and *"This is not a QuickBooks connection"*. It is the
correct behaviour for an unbuilt feature whose button already exists. **It is
still an unbuilt feature**, and on a gap the audit rates as dominating
real-world pain across all three trades and every region.

Recorded alongside it: `exportCSV()` was **deleted** on 2026-08-27 as a
toast-only orphan with zero callers — Guardian C2 — so the button and the
function were correctly split apart rather than one being wired to the other.

---

## 3. What this pass did not do

* **SAIRNdental was not started.** Blocked by fourth's active claim on that app,
  0.1h old at the time of checking. It is the one of the three requested apps
  still needing this.
* **No market research was re-run.** Both audits' market halves are the
  reference and re-verifying them would duplicate work the 09-15 pass confirms
  is sound. The exception in the roofing pass — three dated e-invoicing
  mandates, one of which had slipped a year — has no analogue here: neither of
  these audits turns on a commencement date.
* **No live check.** Every verdict is against the repository at HEAD, not the
  deployed apps.
* **"Closed" means the capability exists, is wired, and has a schema or a test
  behind it.** It does not mean it is deep enough to beat the named competitor.
  The roofing pass's §2.2 is the standing warning: a single hyphen produced a
  false negative there, and the counts in this file are a floor, not a ceiling.
* **No code was written and no app file was touched.**

## 4. The one action this pass recommends

**SAIRNmechanical's credentials subtitle should not claim an eligibility
computation the app never requests.** Three ways to resolve it, and the choice
is a product decision: call `eligibility` from the credentials panel and show
the answer; gate scheduling on it; or correct the sentence. The third is the
only one that is purely a correction — the first two are features. Doing
nothing leaves a claim in the UI that the product does not support, which is
the class of finding this platform treats as a defect rather than a gap.
