# SAIRNcare v1 — Facility-Based Senior Care: scope (design only, nothing built)

**Status:** scope for review, per Michael's instruction. No code written.
Running parallel to Hank's SAIRNsenior build (home-care agency, distinct app,
distinct license namespace — see below).

## Real finding, independently corroborated before scoping anything

Checked the same conflict Hank found, and one layer past it. The three real,
signed-shaped documents literally titled "SAIRNcare" (Terms & Conditions,
Data Privacy Addendum, SOP User Guide — all dated June 2026, real $149/mo
pricing, extracted and read directly from the `.docx` files, not summarized
secondhand) describe a **home-care agency** — EVV, GPS caregiver clock-in,
Medicaid billing, care coordinator/scheduler/billing-manager/caregiver roles.
Zero mentions of assisted living, skilled nursing, hospice, retirement, or
"facility" anywhere across all three documents. **That is the exact content
Hank already built as SAIRNsenior.**

Separately, the stale 370KB draft (`sairncare UPLOAD TO GITHUB.html`,
Desktop) genuinely IS facility-shaped — its own storage keys (`sc_acp`,
`sc_adl`, `sc_admissions`, `sc_careplans`, `sc_behavioral`) are real clinical
terms (ADL = Activities of Daily Living, ACP = Advance Care Planning) — but
independently confirmed disqualified for the reasons Hank already found: 20
references to removed apps (SAIRNhr/SAIRNacc) and the abandoned
Fabricor/Railway infrastructure, and its `sc_` storage prefix collides
directly with SAIRNcode's live namespace. **Not resurrected as a foundation
— its key names are cited below only as a directional signal of what
functional areas a facility product needs, not as source code or verified
content.**

**Net result: there is no real internal source document for facility-based
SAIRNcare at all.** Everything below is either Michael's verbal framing or
independently verified external research — same standard as the CPT/ICD-10
vendor research and the ophthalmology checklist correction earlier this
session, not invented.

## Which facility type — v1 decision

"Assisted living, hospice, retirement/senior living" spans genuinely
different regulatory regimes:

| Type | Regulator | Core instrument |
|---|---|---|
| Assisted living | **State-licensed**, no single federal framework — confirmed live: "each state sets its regulations... licensing rules, admission standards, medication guidelines, and resident rights vary by location" | State-specific (varies) |
| Skilled nursing (SNF) | Federal — CMS Conditions of Participation | MDS (Minimum Data Set) assessment, PDPM billing |
| Hospice | Federal — separate CMS Conditions of Participation | Election statement, physician certification, per-diem levels of care (routine/continuous/GIP/respite) |

Per Michael's confirmed instruction (**build one real v1, defer the other
two explicitly rather than one undifferentiated app** — the same lesson as
the SAIRNcare/SAIRNsenior split itself), **v1 targets assisted living**:

- Lowest regulatory floor of the three — state-licensed, not a federal CMS
  Conditions-of-Participation program. SNF's MDS/PDPM and hospice's
  certification/election requirements are both federally strict, high-
  fabrication-risk domains to build a first pass against without much
  deeper, per-requirement verified research than this scoping pass did.
- **Reuses a pattern already proven working**: SAIRNsenior's per-state EVV-
  aggregator config (Sandata/HHAeXchange/Tellus/CareBridge/Other, because
  EVV is federally mandated but each state picks its own aggregator) is
  the same shape assisted living's state-by-state licensing variation
  needs — a per-state config value, not a hardcoded national assumption.
- Larger real addressable market than SNF or hospice by facility count.

**SNF and hospice are named, not silently dropped**: both would need their
own dedicated research/decision-gate pass before any build, given the real
federal compliance stakes (MDS/PDPM and hospice COPs are exactly the kind of
domain where an unverified checklist item could cause real harm, same
category of risk the ophthalmology correction just demonstrated). Revisit
either when there's real demand or a real facility partner to build against.

## Real, verified operational facts (external research, not internal docs)

- **Billing is structurally different from SAIRNsenior's Medicaid-EVV-
  centric model.** Assisted living billing is **primarily private-pay**
  (monthly rate for room/board + care level) — confirmed live: "Many
  assisted living communities do not accept Medicaid because the
  reimbursement rates are lower than private pay rates." Where Medicaid
  applies, it's via **state HCBS (Home and Community-Based Services)
  waivers that cover only the CARE portion, never room and board** — a
  materially different split than SAIRNsenior's single Medicaid-EVV
  pipeline. Not every facility accepts Medicaid at all.
- **Administrator licensure is state-specific and required** — e.g.
  California requires RCFE-specific certification, Alabama requires a state
  board license plus a 20-hour training program. Confirms the state-config
  pattern above extends to staff credentialing, not just billing.
- The stale draft's key names (ADL, ACP, admissions, care plans, behavioral,
  activities) line up with real, standard assisted-living operational areas
  — cited here only as a directional checklist of what v1 should cover, not
  as verified content.

## Real role vocabulary (v1)

Same discipline as SAIRNsenior pulling roles from its own real SOP guide —
since no such document exists here, this is scoped from the verified
research above plus standard assisted-living organizational structure, and
should be confirmed against a real facility contact before launch, same as
any new role list this session has introduced without a source document:

- **Administrator / Executive Director** — full management access, the
  state-licensed role of record.
- **Resident Care Director** (sometimes "Director of Nursing" depending on
  state licensing level) — clinical oversight, care plans, medication
  program oversight.
- **Med Aide / Med Tech** — medication administration record (MAR) access,
  scoped to assigned residents.
- **Caregiver / Resident Care Aide** — ADL support logging, own-assigned-
  residents-only, same visibility shape as every prior app's front-line role.
- **Business Office / Billing Manager** — private-pay billing, HCBS waiver
  claims where applicable, full resident-billing visibility.
- **Activities Coordinator** — activities scheduling/participation, lighter
  read access to resident roster, no clinical or billing write access.

## Architecture (settled now, cheap, per `sairn-software-architect`)

- **Storage prefix: `alf_`** (Assisted Living Facility) — checked, zero
  collisions in the current `RESOURCES`/`SC_RESOURCES` maps (unlike `sc_`,
  already SAIRNcode's; `sen_`, already SAIRNsenior's).
- **Ground-up build, real auth from day one** — same starting point as
  SAIRNlegacy/SAIRNlaw/SAIRNbuild/SAIRNsenior, never had a shared-PIN
  scaffold to replace. New `api/alf-auth.js`, modeled directly on
  `api/sen-auth.js`/`api/bld-auth.js` (check_license/whoami/bootstrap/
  login/setup/roster).
- **Resident privacy gate, assignment-based** — same shape as every prior
  app's real privacy gate this session (StoneDesk's `sd_crm`, SAIRNdesign's
  `sdn_clients`, SAIRNbuild's `bld_bids`, SAIRNsenior's `sen_clients`):
  Administrator/Business Office get facility-wide visibility; Resident Care
  Director gets facility-wide clinical visibility; Med Aide/Caregiver see
  only their own assigned residents; reassignment is management-only,
  enforced server-side. Built with the two real bugs already found and
  fixed on `sen_clients` (self-assign-on-create vs. existing-assignment
  comparison; a genuine three-tier gate, not a management/everyone-else
  binary) applied from the start, not rediscovered.
- **Per-state config**, same pattern as SAIRNsenior's EVV aggregator choice
  — state selection drives which Medicaid HCBS waiver rules (if any) apply,
  never a hardcoded single-state assumption.
- **`sairn-app-scaffold`'s required v1 component**: physician orders / MD
  order / medication-list photo capture → Claude extraction (resident name,
  diagnosis, medication list, care-level indicators) → pre-fills the intake
  form, staff reviews before saving, never auto-submitted — same proven
  baseline as StoneDesk's Field Sketch Quote and SAIRNsenior's own
  MD-order/authorization-letter intake, not a fragile JSON contract.

## Proposed v1 panel list (conservative, not over-scoped)

1. **Residents** — intake (with the photo→Claude assist above), care level,
   assigned staff, real privacy-gated visibility.
2. **Staff** — real server sync from day one (SAIRNsenior's Phase 1
   disclosed gap — caregiver/staff roster shipped local-only first, fixed
   in batch 2 — built correctly from the start here instead).
3. **Care Plans / ADL Tracking** — per-resident, care-level-driven.
4. **Medication Administration Record (MAR)** — Med Aide/Med Tech scoped
   write, same assignment-based gate as Residents.
5. **Billing** — private-pay monthly rate as the primary path; an optional,
   state-config-gated HCBS waiver claims path for care-portion-only billing,
   never conflated with room/board.
6. **Compliance / Incident Reporting** — state licensing requires it in
   some form virtually everywhere; exact requirements vary by state and
   need their own verification pass once a real state/facility partner is
   known, same as SNF/hospice above.
7. **Activities** — lighter-weight, matches the Activities Coordinator role.

Deliberately **not** in v1: anything SNF- or hospice-specific (MDS, PDPM,
election statements, levels of care) — those belong to their own future
scoped passes, not folded in here.

## Open question for Michael

The role vocabulary and panel list above are scoped from verified external
research, not a real facility SOP the way every other app's v1 got built —
worth a real facility contact's review before launch, the same way
SAIRNsenior's roles came from an actual signed SOP guide. Flagging this
gap explicitly rather than presenting research-derived scope as equivalent
to a real operator's sign-off.

## Verification plan (once confirmed and built)

Same Push Protocol as every app this session: `node --check` on the script
block and every new server file before any push, live curl verification of
every new resource passing the allowlist after push (contrast-tested
against a bogus resource name), real assignment-gate role tracing (all
roles × create/edit, by hand, since a logic bug in a privacy gate is
exactly the class `node --check` cannot catch — the SAIRNsenior batch-2 bug
is the concrete proof this matters). New migrations will queue behind the
existing pile from this session and degrade honestly until run, same as
every other app.
