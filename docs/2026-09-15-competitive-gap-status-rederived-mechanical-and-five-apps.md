# Competitive-gap status, re-derived — the two audits that never had one, and what the decay rates actually say

**Derived 2026-09-15 (Fourth) against the code at HEAD.** This is a STATUS
document, not an audit. Per the convention
`docs/2026-09-02-competitive-gap-status-rederived.md` established: *the audits
are for why an item matters and what the market does; a status file is for
whether it is still open.* Nothing here re-verifies a market claim, and nothing
here is a clearance for anything.

**Why now.** Four competitive-gap audits exist on disk. The 09-02 status file
supersedes the status column of exactly two of them (08-26 roofing/dental/senior
and 09-02 StoneDesk). **Two have never had a status re-derivation at all** —
`2026-08-27-sairnmechanical-shared-platform-competitive-research.md` and
`2026-09-03-competitive-gap-audit-build-vet-biz-grounds-cash.md` — and the
09-02 file itself is now thirteen days old and has already been corrected once
(Cody, 2026-09-14, StoneDesk #5).

---

## 0. The finding that generalises, stated first

**A gap row's decay rate is a function of how close the feature already was —
not of elapsed time.** Two audits were re-derived in the same pass, with the
same method, and they decayed at completely different rates:

| Audit | Age at re-derivation | Rows that moved |
|---|---|---|
| `2026-09-03` build/vet/biz/grounds/cash | 12 days | **0 of 33** |
| `2026-08-26` roofing/dental/senior | 20 days | **at least 19 of 20 in-house-buildable rows** |

Elapsed time does not explain that and cannot. What explains it is the SHAPE of
the row. The 09-03 rows are overwhelmingly *"zero occurrences of an entire
vocabulary"* — BIM, IFC, Davis-Bacon, tee sheet, Plaid, phantom wage. A row like
that can only move when somebody genuinely builds the feature, so it is stable
by construction. The 08-26 rows that moved were the ones where the feature
already half-existed: *"PARTIAL, and the gap is narrower than stated"*,
*"the built half is the harder half to notice"*, *"present as manual entry"*.

**So the useful question before trusting any gap row is not "how old is this
document" — it is "how far was this feature from existing when the row was
written".** A half-built row has a half-life measured in days. A
whole-vocabulary-absent row can be trusted for weeks. The 09-02 status file's
own closing lesson said a status document *"inherits the audit's decay rate,
not a better one"*; this is the mechanism behind that sentence.

---

## 1. `2026-09-03` — build / vet / biz / grounds / cash: **no row has moved**

Every "SAIRNx state" cell re-derived against the current app file, using the
same marker method the audit itself prescribes. **33 rows. Four produced a
non-zero count. Every one of the four was read by hand and every one is a false
positive**, which is the audit's own rule — *"a hit is a triage signal and not
proof"*:

| Row | Marker that fired | What it actually is |
|---|---|---|
| SAIRNbuild A4 — offline-first | `offline` × 2 | Two source COMMENTS: *"a merge exists so an offline device does not lose rows"* (`sairnbuild.html:2696`) and *"editable offline"* (`:2717`). No service worker, no IndexedDB, no `navigator.onLine`. The app is still `localStorage`-backed and therefore accidentally offline-tolerant and deliberately offline-*unaware* |
| SAIRNvet A2 — ambient scribe | `ambient` × 2 | A **ball python's** enclosure reading — *"Ambient gradient 75-90°F"* (`sairnvet.html:8476`) — and a dermatitis sign string in `VET_DIAGNOSES`. Zero occurrences of `scribe`. The gap is still *listening to a conversation*, not *producing a SOAP note* |
| SAIRNgrounds B1 — multi-property | `portfolio` × 2 | Two comments about *"the portfolio sweep"*, meaning a platform-wide CODE sweep (`sairngrounds.html:1689`, `:1691`). Not an operator's property portfolio. `property_id` is still the CUSTOMER's property, which the audit already flagged as the way this gap gets closed on paper without being closed |
| SAIRNbiz A1 — compliance thresholds | `wage base` × 8, `IRS` × 1 | Real, and **already recorded**: the wage-base limitation is now DISCLOSED in the UI and the FICA rate is a named constant (Fourth, 2026-09-14, `1af545e9`). The audit's row said *"the constants are scattered"*; they are less scattered and the gap — mid-year AUTO-UPDATE rather than a manual code push — is untouched |

**Everything else returns zero on every marker.** The audit's §9 corrections
(four supplied items that were already built) also still hold.

**Implication for dispatch:** the 09-03 document's status column can be used as
written today. That is unusual enough to be worth saying out loud, and the
reason is §0, not luck.

### 1.1 One row moved WHILE this pass was being written, and it is the thesis

**Corrected before this document was first pushed.** Between the measurement
above and the commit, Hank landed SAIRNbuild **B2 — retainage release**
(`eb80f6a2`). At HEAD now: `retainage_released` × 17, `releaseRetainage` × 3,
`retainage_releas*` × 24. **So the honest count is 1 of 33 moved in 12 days, not
0** — and the measurement above was taken against a HEAD that no longer exists,
which is the decay this whole document is about, arriving inside the document.

**It is also the single best confirmation of §0 available.** B2 is not one of
the whole-vocabulary-absent rows. It is the one row in the SAIRNbuild table the
audit explicitly marked **half-built** — *"HOLDBACK BUILT, RELEASE ABSENT …
Money can go in and never come out."* Every row that held steady for twelve days
was a row where the entire vocabulary was missing. The one row that moved was
the one where half the feature already existed, which is exactly what §0
predicts and is not a prediction this pass made after seeing the answer — the
§0 table was written before `eb80f6a2` was visible in this clone.

Do not read this as the 09-03 audit being unreliable. Read it as: **check the
half-built rows first, every time, and treat the vocabulary-absent rows as the
durable ones.** In that audit the half-built rows are named in terms —
SAIRNbuild B1/B2/B3, SAIRNvet A2, SAIRNbiz A3, SAIRNgrounds A1, SAIRNcash A3 —
because §9 lists them as corrections. That list is the re-derivation shortlist.

---

## 2. `2026-08-27` SAIRNmechanical — §5 Row 1 is closed, the correction exists, and **both headings a reader hits first still assert the false state**

The mechanical research is mostly market structure and a deferred build-order
decision, with one concrete cross-application finding in §5. That finding has
been overtaken, and — importantly — **somebody already caught it.**

**§5 Row 1 said:** *"StoneDesk Subcontractor Portal: no compliance layer at
all … a grep of the whole file for insurance/COI/W-9/licence fields on the
subcontractor record returns nothing."* Michael's call the same day was **leave
it alone for now**, logged as its own row in `SAIRN-BACKLOG.md`.

**Re-derived at HEAD: it is built, with a real server-side gate.**

| What the row asked for | State at HEAD |
|---|---|
| COI expiry on the roster record | `coi_expiry` — captured (`stonedesk.html:34077`), rendered (`:33996`) |
| Licence number + expiry | `licence_no`, `licence_expiry` (`:34078`) |
| W-9 on file | `w9_on_file` (`:34079`) |
| Expiry computation + Expiring/Expired badge | `subxCompliancePill()` — four real states: EXPIRED (blocking), EXPIRING, NOT TRACKED, COMPLIANT |
| **Assignment gated the way SAIRNbuild gates award** | **Yes, and at the endpoint rather than the UI**: `api/sd-sub-data.js` returns `409 SUB_NOT_COMPLIANT` — *"Cannot assign to … — expired certificate of insurance and licence."* |

Shipped **2026-09-01** in `c6dcb69f`, with `sql/sd_subs_compliance_2026-09-01.sql`.

### 2.1 The correction is already written, and it is better than mine

`SAIRN-BACKLOG.md` carries a **CORRECTION 2026-09-02, later the same day**,
headed *"THIS ROW WAS ALREADY CLOSED WHEN I UPDATED IT, AND MY UPDATE SAID THE
OPPOSITE"*. It names `c6dcb69`, dates it eighteen hours earlier, and goes
further than this pass did independently: it enumerates all three
implementations, identifies where they DISAGREE, and finds a defect this
re-derivation did not spot —

> *"They disagree on the clock. `sd-sub-data.js` defaults to the server clock
> (`nowISO().slice(0,10)`, UTC). The shared engine refuses to run without a
> caller-supplied `today`. **This one is not a tie** — the UTC default is the
> defect class fixed across nine SAIRNvet panels on 2026-09-01, and a
> contractor in Ohio gets a different answer than the server does for six hours
> of every day."*

It also records that SAIRNbuild's `eligibleToBid()` hard block is client-side
only, so it is *"a suggestion to anyone who calls the data endpoint directly"*.

**That correction is sound and this document does not improve on it. What is
left is narrow and is the actual finding.**

### 2.2 The finding: the fix is in the body, the false claim is in the heading

The correction sits roughly **100 lines into** the backlog row. Two pieces of
text a reader reaches FIRST still assert the superseded state, and neither was
touched:

1. **The backlog row's own `##` heading** —
   *"StoneDesk Subcontractor Portal has no compliance layer — no COI, no
   insurance, no licence, no expiry."* That is the line that appears in any
   outline, any grep of `^## `, and any skim. It is false.
2. **`2026-08-27-…-competitive-research.md` §5 Row 1** — still closes with
   *"Status — decided 2026-08-27: leave it alone for now … Nothing built."*
   No correction was appended there at all, and the audit is the document a
   session sent at SAIRNmechanical would read.

**This is a distinct failure mode from the stale status column the 09-02 file
exists to catch.** Nothing here is un-corrected; the correction simply does not
reach the two surfaces that get read. A reader who skims — which is the normal
way a 1,500-line backlog and a 1,267-line audit get used — sees only the false
claim. Both are fixed by this commit: the backlog heading is retitled and §5
Row 1 gets a pointer.

**Recorded, not acted on:** consolidating the three implementations. The backlog
correction already frames it as *"a real decision rather than the obvious
cleanup"* and names the two substantive disagreements. Repointing one gate at
another needs the target's behaviour re-qualified rather than a diff proving the
code matches — the byte-identical-is-not-safe-in-context rule from
`docs/2026-09-13-cross-domain-disciplines.md`, applied to a deletion rather than
a copy. The UTC-clock default it identifies is a separate, smaller, genuinely
open defect and is the part of that cluster worth fixing on its own.

---

## 3. `2026-08-26` roofing / dental / senior — comprehensively stale, beyond the two rows already corrected

The 09-02 status file superseded this audit's status column and corrected two
rows; Cody corrected a third on 09-14. **The decay is much wider than that.**

Twenty rows were selected — every row in the three tables that is buildable
in-house, i.e. excluding the clearinghouse / EPCS-PDMP / EVV-aggregator /
imaging-vendor rows the 09-02 file already labels vendor- or
certification-blocked. **Nineteen of the twenty now return substantial marker
counts against code that read zero or near-zero when the audit was written.**

**Hand-verified to the server and schema layer** (not marker counts):

| Row | Audit said | At HEAD |
|---|---|---|
| SAIRNroofing B1 — commercial roof asset registry | Absent | `api/_lib/roofing-asset-registry.js` + `.test.js`, `sql/sairnroofing_asset_registry_schema.sql`, a Buildings panel |
| SAIRNroofing B4 — safety / OSHA at scale | Absent | `api/_lib/roofing-safety.js` + `.test.js`, `sql/sairnroofing_safety_schema.sql`, `JHA` × 36 in-file |
| SAIRNdental A7 — good-faith estimates / No Surprises Act | Absent | `sql/sairndental_gfe_schema.sql` (*"45 CFR 149.610"*), `api/_lib/dental-gfe.js` + 34 test references, `GFE` × 89 in-file |
| SAIRNsenior B3 — franchise reporting and royalty calculation | Absent | `sql/sairnsenior_franchise_schema.sql`, `api/_lib/sairnsenior-franchise.test.js`, wired through `api/_resources/sairnsenior.js` |
| SAIRNsenior B1 — multi-branch / multi-state | *"Zero for `location_id`; branch 3 hits"* | `branch_id` × 25, `branch` × 74 |

**Marker counts only, NOT hand-read** — stated as such because this method's own
rule is that a hit is a triage signal and not proof: SAIRNroofing A2 (`crew` ×
39), A3 (`subcontractor` × 28, `coi_expiry`), B3 (`retainage` × 43, `WIP` × 10),
B7 (`prequal` × 32, `bonding` × 27); SAIRNdental A8 (`recall` × 49), A9
(`treatment plan` × 10), B3 (`denial` × 61, `appeal` × 59), B5 (`Tableau`,
`Power BI`, `Looker`, `data warehouse`, plus `api/_lib/dental-bi.js`);
SAIRNsenior A3 (`burn-down` × 17), A5 (`applicant` × 46), A6 (`training hour`,
`CareAcademy` × 3), A7 (`referral source` × 7), B2, B5.

**Do not treat the 2026-08-26 audit's status column as information.** Use it for
why a gap matters and what the market does — which is what it is good at and
what it was re-verified against primary sources for. Re-derive any status cell
before building.

### 3.1 The one row that is genuinely still open, in-house, and un-gated

**SAIRNdental B2 — cross-location roll-up reporting.** It is the only row of the
twenty that came back zero on every marker, and hand-reading confirms it is
half-open rather than absent:

- **Write-side capture SHIPS.** `api/_lib/dnt-location.js` stamps a
  `location_id` on every write, defaulting to `LOC-DEFAULT` so a
  single-location practice sees nothing change.
- **Server-side cross-location AGGREGATION is deliberately held**, and the file
  says so in its own NOT IN SCOPE list, with the reasoning: *"Consolidated
  reporting, a per-location booking page, and a client-side location selector
  can all be built later at the same cost. Attribution cannot — a charge,
  payment, AR entry or appointment recorded without a location can never be
  assigned to one afterwards."*

That is a held decision with a written rationale, not an oversight, and it is
already in `SAIRN-BACKLOG.md`. **It is nonetheless the only buildable, un-gated
competitive-gap item this pass found across all four audits** — every other
still-open row is vendor-gated, certification-gated, a product-positioning
decision, or refused on principle (SAIRNroofing declined certified payroll
rather than invent a wage-determination rate, and any SAIRNbuild B5 build must
clear the same bar).

---

## 4. What this document deliberately does not do

- **It does not verify any market claim.** No competitor name, segment size or
  willingness-to-pay figure in any of the four audits was re-checked here. The
  09-03 audit carries no citation URLs at all and says so.
- **It does not run a patent screen**, and the three rows flagged for one
  (SAIRNvet A1, SAIRNvet A2, SAIRNcash A4) are still flagged.
- **It does not claim its own status column will stay true.** Per §0, the 09-03
  rows should be durable and the 08-26 rows should not be trusted at all — but
  that is a prediction from a shape, tested once, on two documents. Re-derive
  before building. The grep is cheap and the wasted build is not.

---

## Spot-verified 2026-09-18 (Hank) — the four "Absent → built" rows

**THE CLAIMS HOLD, AND ONE NEEDED A SECOND LOOK TO SAY SO.** This document is
the oldest of the current re-derivations and the day since has been heavy, so
its four closures were checked against the tree rather than re-read:

| row | artefact cited | on disk |
|---|---|---|
| SAIRNroofing B1 | `api/_lib/roofing-asset-registry.js`, `sql/sairnroofing_asset_registry_schema.sql` | present |
| SAIRNroofing B4 | `api/_lib/roofing-safety.js`, `sql/sairnroofing_safety_schema.sql` | present |
| SAIRNdental A7 | `api/_lib/dental-gfe.js`, `sql/sairndental_gfe_schema.sql` | present |
| SAIRNsenior B3 | `sql/sairnsenior_franchise_schema.sql`, `api/_lib/sairnsenior-franchise.test.js` | present |

**SAIRNsenior B3 LOOKED LIKE A TEST WITH NO IMPLEMENTATION**, which would have
been a real finding — a suite citing a feature that does not exist. It is not:
the implementation lives in `sairnsenior.html` and the suite drives it verbatim
from the app file, which is this platform's normal shape for panel logic. **81 of
81 assertions pass**, run rather than assumed. Recording the near-miss because
the citation naming only a `.test.js` is exactly what a fabricated closure would
also look like, and the difference took a run to establish.

**AND THE RECONCILIATION IS NOW COMPLETE ACROSS EVERY AUDIT.** roofing, dental,
senior and mechanical were re-derived 2026-09-17; build/vet/biz/grounds/cash
here on 2026-09-15; StoneDesk on 2026-09-17. **No untouched rows remain.** What
is still open is open by decision or by hardware, not for want of a pass —
StoneDesk row 4 (slab-scanner, hardware) and row 6 (QuickBooks, Michael's call
of 2026-09-02) are the residue, and both are named in the open-work index.
