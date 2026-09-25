# Worldwide external competitive-gap audit — SAIRNmechanical

**Sourcing caveat, read this before anything else below:** this session's
outbound network could not reach any vendor, trade-press, or patent-office
domain. Every vendor-attributed fact in this document is a `WebSearch`
index snippet of that vendor's own domain, not an opened page — one grade
below this series' normal standard. Full disclosure and the direct test
evidence are in §0.

**Research pass, 2026-09-25. No code written, no app file touched.** Written
by a standalone cloud session under `docs/cloud-research/` per instruction
(new files only, new branch, no PR). This is the app-specific companion to
`docs/cloud-research/plumbing-electrical-hvac-external-competitive-research-2026-09-25.md`
(the trade-wide market document) and anchors directly against
`docs/2026-09-17-trades-audit-rederived.md` (the internal code-facing
re-derivation of SAIRNmechanical's own state, current as of that date and
used here without re-deriving it).

**Method and standard**: the reference for this series is
`docs/superpowers/specs/2026-09-02-stonedesk-worldwide-competitive-gap-audit.md`
— every competitor claim read from the vendor's own site, not a comparison
article; aggregator pages used only to find vendors; a failed fetch recorded
as a failure, never filled in; pricing only from a vendor's own pricing page.

---

## 0. A material limitation, stated before anything else

**This session's outbound network cannot reach any vendor, trade-press, or
patent-office domain**, confirmed directly against a healthy proxy status
by a blocked `WebFetch` to `buildops.com` — the same result documented in
this series' three prior external audits (SAIRNvet, SAIRNlaw,
plumbing/electrical/HVAC trade research, all 2026-09-25). Every vendor-fact
cell below is a `WebSearch` result restricted to the named vendor's own
domain — the search engine's indexed excerpt, not the page itself — and is
one grade below this series' own standard. **Nothing here should be quoted
externally without a follow-up pass from a network that can reach these
domains.** Patent numbers are unverified third-party index snippets; no
infringement conclusion is drawn. Retrieval date for every row: 2026-09-25.

---

## 1. What SAIRNmechanical is, measured against the internal audit

Read from `docs/2026-09-17-trades-audit-rederived.md` (CC, re-derived
against code at HEAD) and `docs/CRITICALITY-TIERS.md` (rollup row
`sairnmechanical`), confirmed as the anchor for this pass:

- **HVAC-only, and deliberately so.** Fourteen job-type chips exist in the
  product and every one is HVAC (`ac-replacement`, `furnace`, `ductwork`,
  `water-heater`, `commercial-rtu`, and so on). No plumbing or electrical
  trade exists in the product. This is a scope boundary, not a bug, and the
  competitive question it raises is answered in the trade-wide companion
  document §2.6 and §5: no competitor has cracked plumbing- or
  electrical-native software either.
- **Six registered resources, three Tier A**: `mech_credentials` and
  `mech_quotes` and `mech_site_assets` are Tier A
  (`docs/CRITICALITY-TIERS.md:62`).
- **BUILT, and carefully**: EPA Section 608 refrigerant leak-repair (40 CFR
  82.157, 50 lb threshold), with an overridable `threshold_lb` parameter —
  and, closed 2026-09-17, the **AIM Act / 40 CFR 84.106 rule modelled as a
  second, independent rule** (15 lb threshold, GWP floor 53, a 30-day repair
  clock with a 10-day follow-up), reported side by side with the 82.157
  rule and never summed with it. EPA-608 technician certification
  (Type I/II/III/Universal) is a first-class, append-only credential field
  — a renewal is a new row, never an edit.
- **BUILT**: a technician credential registry (append-only) and a
  mutable site-asset registry — ranked as the top two prerequisite
  capabilities in the original 2026-08-27 platform research, on the
  reasoning that "nothing else can be gated correctly until this exists."
- **DISCLOSED BUT NOT BUILT**: Manual J/D/S load calculation. The app shows
  an on-screen note beside all three sizing outputs and appends a
  system-prompt disclaimer to all four AI prompts, so the model's own
  output does not present itself as an ACCA-approved calculation.
- **STILL OPEN**: leak-*rate* calculation specifically (the repair
  countdown clock exists; the percentage-rate math does not, deliberately —
  the app's own code states the rate differs by appliance category and
  refuses to hardcode one); backflow/cross-connection (only a credential-
  type dropdown option exists, no testing-and-submission workflow); permit
  and inspection workflow (absent entirely — all four `permit` hits in the
  file are one line of AI-prompt/document-type-list text, not a workflow);
  geothermal/IGSHPA licensing (absent).
  NEC Article 220, low-voltage/fire-alarm, EV-charger/solar and EU F-Gas are
  all correctly N/A — no such trade or jurisdiction exists in the product.
- **CORRECTION TO THE INTERNAL ANCHOR, caught in this pass's own re-check
  before it could ship as a second-hand overclaim**: `docs/2026-09-17-trades-audit-rederived.md`
  describes data portability as "a CSV export button exists and is
  explicitly disabled" as a single, blanket fact. Read at the caller level
  (this series' own standing method), that is true of exactly one surface
  — the SAIRN-Suite cross-app sync panel and the SAIRNbiz HR/GL connector
  panel, both wired to `mechNotLive('CSV export', 'exported')` — and false
  of the app's single most important resource. `mech_credentials` (Tier A)
  has a real, live, carefully engineered export: `mechExportDataset('credentials')`
  behind an "Export CSV" button in the credentials panel itself, built on a
  declared `MECH_EXPORTS.credentials` entry with tie-break logic for two
  records sharing a key and date, a preamble disclosing board-vs-full-history
  row counts, an explicit "status is the server's classification, not
  recomputed here" disclosure, and a stated `has_expiry` tri-state (yes / no
  — lifetime / unstated) carried into the file rather than inferred from a
  blank date. The other two Tier A resources, `mech_quotes` and
  `mech_site_assets`, have **no export declared at all** — not even a
  disabled button, which §2.6 below treats as the real, narrower gap.

---

## 2. What the market does, against each open item

### 2.1 Leak-rate calculation

| Vendor | What the vendor-domain snippet claims |
|---|---|
| RefriTrak | Calculates leak rates against 10/20/30% thresholds by name |
| RefriComply | "Automatically calculates annualized leak rates every time a technician logs a service using the exact EPA formula" — the formula is not shown in the snippet |
| Field Ascend | Logs refrigerant data with automatic CO2e calculation; does not explicitly state an automated leak-rate percentage in the snippet gathered |
| FieldCamp | Leak-rate calculation is a user-configured custom field, not a built-in formula |

**Only two of the four vendors most directly comparable to
SAIRNmechanical's own compliance posture claim a fully automated leak-rate
percentage, and neither exposes its methodology.** Both assert "the EPA
formula" as a black box. This is the single most useful fact this pass
produces for SAIRNmechanical's own decision: the market has not solved the
transparency problem SAIRNmechanical's own refusal is protecting against —
it has simply not disclosed how it computes the number. Building a
leak-rate feature that shows its formula and cites the specific EPA
guidance document it is derived from would be a **differentiator against
this category**, not merely parity with it, if SAIRN chooses to build one at
all.

### 2.2 Manual J/D/S

Across six general FSM platforms surveyed in the trade-wide companion
document, **only one (Service Fusion) has a named third-party Manual J
integration** (Amply Energy), and only two (ServiceTitan, Housecall Pro)
have their own calculator — and Housecall Pro's own site discloses it lands
"within 10–15% of a full Manual J" and states a real ACCA calculation is
still needed for permits or new construction. **No FSM vendor surveyed has
built a compliance-grade Manual J engine in-house.** SAIRNmechanical's
on-screen disclosure (`MECH_MANUAL_J_NOTE`, `MECH_MANUAL_J_SYS`) is
therefore closer to market practice than the alternative of building a
proprietary engine would be — the gap, if there is one, is not having a
named third-party integration the way Service Fusion has one, not the
absence of an in-house calculator.

### 2.3 Backflow/cross-connection

Confirmed as a mature, standalone category served by dedicated vendors
(BSI Online, SwiftComply, BRYCER, iWorQ, Inspect Point) running a genuine
three-party workflow — tester submits, utility approves, sometimes a
tester-pay pricing model. **No general FSM platform, including every one
surveyed against SAIRNmechanical's own peer set, has absorbed this
natively.** SAIRNmechanical's credential-type dropdown is roughly where the
rest of the FSM market also sits; the standalone category exists precisely
because a dropdown field is a data point and a utility relationship is a
different kind of product. This is a real gap only if SAIRN decides to
pursue backflow testing as a workflow, which is a business decision about
building relationships with individual water utilities, not a code gap in
the ordinary sense.

### 2.4 Permits and inspections

PermitFlow claims direct e-submission to the authority having jurisdiction,
not just document tracking. **No FSM vendor in the peer set surveyed
offers a native permit-submission module.** SAIRNmechanical's absence of any
permit workflow is a real gap against a purpose-built permitting product,
but is not a gap relative to its actual FSM peer set, which mostly doesn't
have this either.

### 2.5 Geothermal/IGSHPA

Confirmed absent industry-wide as a distinct software category — nobody has
built this, including the trade-wide leaders. SAIRNmechanical is not behind
the market here; the market has not moved.

### 2.6 Data portability — real, but narrower than the internal anchor states

CSV import/export is confirmed table stakes across essentially every FSM
vendor in the peer set (ServiceTitan, Housecall Pro, Service Fusion, Jobber
all state or strongly imply it) — that market fact is not in question.
**What is in question is which part of SAIRNmechanical it's a gap against**,
and a caller-level check (§1) finds the answer is not "all of it": the Tier
A `mech_credentials` export is built, live, and — on the evidence of its
tie-break and disclosure logic — more careful than anything a vendor
snippet in §2.2 claims for its own export. The real, narrower gap is the
other two Tier A resources, `mech_quotes` and `mech_site_assets`, which
have no export path at all, disabled or otherwise — a customer cannot get
their own quote or asset data out of the app in any form today. That is
still a real gap against the peer set's "CSV export" as a blanket
capability, just not the uniform one the internal anchor's wording implies,
and not the cheapest possible fix either: it is two new exports built to
the standard the credentials one already sets, not one button turned on.

### 2.7 The AIM Act penalty figure — resolved: $44,539/day is current; $59,114 is a single uncorroborated vendor figure

Traced against the primary regulatory chain (still WebSearch-snippet grade —
`ecfr.gov` and `federalregister.gov` were both `EGRESS_BLOCKED` on direct
`WebFetch`, so this is multiply-corroborated secondary-source reading of
those primary documents, not a page read of them):

- **The dollar figure is not set in 40 CFR Part 84 itself.** Part 84 (the
  AIM Act technology-transition and leak-repair rule SAIRNmechanical
  already models) defines the substantive threshold and repair-clock
  obligations; it does not carry a penalty schedule. Violations of Part 84
  and of Part 82 (the pre-existing §608 rule) are both enforced under Clean
  Air Act §113(d), and the dollar amount is set separately in **40 CFR Part
  19, Table 1 to §19.4** — the general EPA civil-monetary-penalty
  inflation-adjustment regulation. One table, cited by reference, covers
  both of SAIRNmechanical's two rules; this is itself a reason the app is
  right to report them as two separate rules with one shared enforcement
  ceiling, not to conflate the ceiling into either one specifically.
- **$44,539/day/violation is the correct, current figure.** It was set by
  the Federal Register's January 8, 2025 civil-penalty inflation
  adjustment (effective for violations assessed on or after that date; a
  ~2.6% CPI-U-based increase over the prior $37,500 figure it superseded),
  and it is independently repeated — not just by the vendor pages already
  in §2.1, but by multiple unrelated legal/compliance secondary sources
  (Williams Mullen, Wiley, J.J. Keller Compliance Network, Crowell &
  Moring, and two independent HVAC-compliance content sites) found across
  several separate searches in this pass.
- **It is still current as of today (2026-09-25), and there is a specific,
  sourced reason why**: OMB Memorandum M-26-11 (April 17, 2026) cancelled
  the 2026 civil-penalty inflation adjustment across every federal agency,
  because the government shutdown prevented the Bureau of Labor Statistics
  from producing the October 2025 CPI-U figure the multiplier is computed
  from. No 2026 Federal Register rule superseded the January 2025 EPA
  penalty table — agencies were instructed to keep the 2025 figures in
  force for 2026, which is exactly what every source found here does.
- **$59,114/day traces to exactly one source across every search variant
  run in this pass**: a single HVAC-compliance vendor's own marketing blog
  (Ref LeakLog, `refleaklog.app`, a page titled "EPA Fine Calculator 2026").
  No independent legal, trade-press, or regulatory source repeats this
  number. It cannot be explained as a routine one-year inflation step
  either — $59,114 is roughly **32.7% above** $44,539, far larger than any
  single annual CPI-U adjustment in this series (all found in the 1–3%
  range), and 2026 specifically had no adjustment at all per M-26-11 above.
  **The most defensible read of the evidence gathered is that this is a
  vendor error or an uncorrected pre-cancellation projection, not a real
  current figure** — this pass does not know which, and does not claim to;
  it only has enough to say the number is uncorroborated and the $44,539
  figure is not. Any customer-facing SAIRNmechanical material should cite
  $44,539/day, sourced to 40 CFR 19.4 Table 1, and should not repeat
  $59,114 without a primary-source page read confirming it first.
- A separate, distinct pair of figures — a judicial (court-assessed, CAA
  §113(b)) maximum reported inconsistently across sources as either
  $93,750 or $124,426/day — surfaced in the same searches and is **not**
  resolved here; it answers a different question (judicial vs.
  administrative penalties) than the vendor-page discrepancy this section
  was asked to reconcile, and reconciling it was not part of this pass's
  scope.

### 2.8 Adjacent-trade crossover — what two other SAIRN apps have already
built that SAIRNmechanical has not, read directly from their code (not a
web source; no egress-block caveat applies to this subsection)

A tunnel-vision check: the peer set in §2.1–§2.6 is entirely outside-vendor
FSM/compliance software. SAIRN already operates two apps closer to
SAIRNmechanical than any outside vendor — same platform, same auth model,
same append-only-registry conventions — and neither was checked against
SAIRNmechanical in the original internal audit. Marker counts, then a
hand-read of every non-zero hit, this series' own standing method:

- **SAIRNroofing has a subcontractor compliance GATE that SAIRNmechanical
  has no equivalent of.** `sairnroofing.html`'s Prequalification &
  Bonding panel evaluates each subcontractor's certificate of insurance,
  licence, and W-9 against a `compliant` / `blocking` / `unknown_requirements`
  verdict, rendering "ok to assign" only when every document is current —
  each document carries its own state (current/expiring/expired) and a
  `days_left` countdown, and a subcontractor whose compliance engine could
  not be evaluated shows the refusal reason instead of a blank or a false
  pass (`<td colspan="4"><span class="badge br">'+...compliance_error...+'</span></td>`).
  This is a real assignability gate, not a status board — the distinction
  the original SAIRNvet audit used against that app's own multisite panel
  applies here in SAIRNroofing's favor.
- **SAIRNroofing also checks bonding capacity against job value**
  (`rf_bonding`, "Job value to test against the bond"), with a specific,
  documented design decision worth carrying as a pattern: a missing
  `rf_bonding` config table renders "Not set up yet… **this is not the
  same as having no bond**," because a contractor reading a blank bonding
  panel as "you have no bond" in front of a surety is exactly the kind of
  honest-absence failure this codebase's own conventions (PR §1.11, the
  fail-closed-and-say-so rule) exist to prevent.
- **SAIRNgrounds has a generic per-state licence/permit tracker with
  expiry**, in its Bar & Compliance panel (State / Permit Type / Licence # /
  Expiry / Status), plus a live automated-enforcement example worth noting
  as a pattern independent of its specific trade: alcohol checkout is
  blocked outside configured sale hours "computed live against the current
  local time — not just a policy note," i.e. the rule is enforced in the
  transaction path, not merely displayed.
- **Correction caught before it could ship as a manufactured gap**: the
  obvious next claim — "SAIRNmechanical has no state-level HVAC contractor
  licence tracking" — is checked directly against the code and is **false**.
  `mech_credentials` already has a `state_license` credential type sitting
  alongside `epa_608`/`nate`/`manufacturer`/`safety_training`/`medical_gas`/
  `backflow`, a free-text `jurisdiction` field (placeholder `"OH"`), and the
  same issued/expires/status treatment as EPA-608 — the "Who can I
  dispatch?" panel queries against `(type, section-or-jurisdiction)`
  generically. This is a narrower, single-ledger design than SAIRNgrounds'
  dedicated table, but it is not a gap, and reporting it as one here would
  be exactly the capability-inflation-in-reverse this audit series exists
  to catch.
- **What the crossover check actually finds, confirmed at zero**:
  SAIRNmechanical has no equivalent of SAIRNroofing's compliance-gated
  assignment for anyone or anything, and — the specific, real, sourced gap
  — **no certificate-of-insurance or general-liability tracking at all**
  (`insurance` appears 0 times in `sairnmechanical.html`). Commercial HVAC
  work for property managers, GCs, and (given the app's own `medical_gas`
  credential type) hospital facilities routinely requires a contractor to
  furnish proof of its own general-liability coverage before dispatch —
  this is the business's own insurance status, distinct from a
  technician's individual credentials, and SAIRNmechanical currently has
  no field, panel, or registry for it at all, not even a manual one.
  Building SAIRNroofing's specific gate (subcontractor assignment) would be
  the wrong shape to copy here — SAIRNmechanical dispatches its own
  technicians, not subcontractors — but the underlying primitive
  (document + expiry + current/expiring/expired + a real consequence when
  it lapses) is a proven, in-platform pattern, not a novel build.

### 2.9 State-level regulatory layer — CARB R3, the one new real gap this
pass found, and it is confirmed at zero

A deliberate tunnel-vision re-pass (full sourcing in the trade-wide
companion document §2.7) found a state-level refrigerant-compliance regime
SAIRNmechanical does not model at all: **`CARB`, `California`, and `R3`
all appear 0 times in `sairnmechanical.html`.** California's CARB
Refrigerant Management Program is confirmed — directly on `arb.ca.gov` and
`rmpr3.arb.ca.gov`, not from a vendor claim — to be materially stricter
than either federal rule the app already carries: registration above
50lb, annual reporting above 200lb, **5-year on-site record retention**
against EPA's 3, an unrepairable leaker must be retrofitted or retired
within **6 months** against the AIM Act's 1 year, and CARB enforces
independently of EPA with its own penalty authority up to $10,000/day. A
vendor's own domain states plainly that federal AIM Act compliance is "not
a valid defense" under CARB — the regimes layer, they do not substitute.
At least one vendor already catalogued in this series (RefriTrak) sells
state-overlay logic today, naming six states with rules beyond the
federal floor. **Unlike §2.1's leak-rate math or §2.4's permit workflow,
this is not a case of the market being no further ahead than
SAIRNmechanical — CARB is a live, independently enforced regulatory
programme with a real, disclosed dollar penalty, and the app's own two
modeled rules (82.157, 84.106) currently have no third rule beside them
for any customer operating a covered system in California.** Whether to
build a third rule, and whether to gate it on a jurisdiction field already
present in `mech_credentials` or model it as its own compliance object, is
exactly the kind of decision this series declines to make (§5) — but the
absence itself is real, sourced from the regulator's own domain, and does
not depend on any vendor's marketing claim.

### 2.10 Insurance/liability, revisited — the FSM peer set has not solved
this either

§2.8 found `insurance` at zero hits in SAIRNmechanical and recommended
building on the in-platform pattern SAIRNroofing already proves. A direct
check of the same six FSM vendors already surveyed in §2.2 sharpens what
kind of gap this actually is: **a clean six-for-six negative on EMR
(experience-modification-rate) and OSHA-recordable tracking** — no
vendor's own domain advertises either. Certificate-of-insurance is more
nuanced than a flat gap: Housecall Pro ships a real, embedded feature
(Coverdash) that helps a contractor buy and *show their own* insurance,
which is a different problem than tracking documents belonging to others.
**BuildOps' own site states its COI/lien-waiver workflow is "currently
handled via manual attachments," with automation "planned for future
releases"** — i.e. the FSM vendor best-positioned to have solved inbound
COI tracking documents that it has not. The dedicated industry that has
solved COI tracking (myCOI, Certificial) is confirmed to operate entirely
outside any FSM software stack, pulling policy data from a contractor's
broker or carrier directly rather than integrating with field-service
software at all. **This changes how §4's insurance-tracking item should be
read**: it is a real, confirmed-absent capability worth building on a
proven in-platform pattern (SAIRNroofing), but it is closer to
market-parity than to catching up to a solved problem — nobody in the
peer set has this solved either, which is different from the leak-rate or
data-portability items where specific competitors demonstrably have.

### 2.11 Franchise/multi-location — confirms an already-known gap with
real detail, rather than discovering a new one

Ground truth already established (§1, and independently by grep): `SAIRN`
mechanical carries zero markers for multi-location, multi-site, franchise,
or royalty concepts — it is single-location by construction, same as its
HVAC-only scope is a construction choice rather than an oversight. This
pass's market check confirms what a multi-location HVAC operator actually
gets from the FSM vendors already surveyed, which is real and concrete
rather than a restatement: ServiceTitan's "Enterprise Hub" (cross-location
roll-up reporting, shared configuration, centralized contact center) and a
named Franchise Management product; Housecall Pro's parent/child account
model with an "account cloning" tool built specifically for onboarding new
franchise locations; Authority Brands (owner of the One Hour Heating & Air
Conditioning franchise, among 15 brands) running its own proprietary
Successware platform with a disclosed $100/month per-franchisee technology
fee; and, via ServiceTitan's own 2020 acquisition announcement, Neighborly
brands Aire Serv, Mr. Rooter and Mr. Electric confirmed running on
ServiceTitan since 2012 — a separate franchise umbrella from Authority
Brands, not the same family (a grouping error this pass's own research
brief made and its own research caught and corrected). **No source found a
named royalty-reporting feature in any platform surveyed** — this appears
unconfirmed industry-wide, not a SAIRNmechanical-specific absence, so it
should not be listed as a gap on the strength of this pass. Net effect:
this angle sharpens what "multi-location support" would concretely need
to look like if SAIRN ever pursued it (a parent/child account and
permission model, cross-location dispatch, roll-up reporting) but does
not change the priority ranking below — the scope boundary was already
known, and this pass found detail, not a new argument to cross it.

---

## 3. Patent screen — unverified, no conclusion drawn

Every entry is a third-party index snippet; no page was opened; no
infringement conclusion is drawn. The full patent list is in the trade-wide
companion document §3 and is not duplicated here. **The one finding most
relevant to SAIRNmechanical specifically**: no patent title or abstract
found in this pass claims the specific append-only, renewal-as-new-row data
model `mech_credentials` already implements — the closest matches are
generic credential-verification systems. The refrigerant leak-rate family is
dense and over a decade old and should be read before any leak-rate feature
is designed, regardless of what this pass could confirm about it.

---

## 4. What this means for SAIRNmechanical, in priority order

Reading §2 against the internal audit's own open-items list. The order
changed from this document's first draft: the tunnel-vision re-pass (§2.9)
surfaced a real regulatory exposure that the FSM-peer-set lens could not
have found, and it is ranked above the export/insurance items now on the
strength of being an independently enforced state programme with a
disclosed dollar penalty, not a UX or parity gap:

1. **The CARB R3 state-regulatory layer is the highest-stakes item in
   this document** (§2.9) — not because it is cheap (it is the least
   cheap item on this list; a third compliance rule is real design work),
   but because it is the one item here backed by an active regulator's own
   domain disclosing an independent penalty authority up to $10,000/day,
   for any SAIRNmechanical customer covered by the programme today,
   modeled nowhere in the app. Whether and how to build it is explicitly
   not decided here (§5) — the absence itself is what this pass adds.
2. **The `mech_quotes` / `mech_site_assets` export gap is the cheapest,
   most defensible fix left** — not "data portability" broadly, which is
   already half-built to a high standard: `mech_credentials` has a real,
   live export (§2.6). The other two Tier A resources have no export
   surface at all, disabled or otherwise, which is the actual, narrower gap
   against the market consensus that CSV export is table stakes.
3. **Business-level certificate-of-insurance tracking is a second,
   independent low-cost fix** (§2.8, sharpened by §2.10) — the primitive
   already exists elsewhere on the platform (SAIRNroofing's
   document+expiry+consequence pattern), `insurance` is confirmed at zero
   hits, and commercial/hospital HVAC work routinely requires furnishing
   proof of coverage before dispatch. Ranked below the export gap and CARB
   specifically because §2.10 confirms the FSM peer set has not solved
   this either — it is a parity opportunity, not a catch-up requirement.
4. **A transparent leak-rate calculation, if built, would be a real
   differentiator** rather than mere parity, because the two vendors
   closest to this category do not disclose their methodology and
   SAIRNmechanical's existing discipline (cite the exact CFR section, never
   silently combine two rules) is a stronger foundation to build a
   disclosed formula on than either competitor currently shows.
5. **Manual J and backflow are correctly left undisclosed-and-open rather
   than built** — the market's own leaders either partner (one vendor, one
   partner, across six surveyed) or disclaim (the two vendors with in-house
   calculators both disclose their limits). SAIRNmechanical's current
   posture already matches the more honest half of the market.
6. **Permits and geothermal remain genuinely low-priority** relative to the
   app's actual FSM peer set, whatever their value against a purpose-built
   permitting or geothermal-training product might be.
7. **The plumbing/electrical scope boundary remains correct** — see the
   trade-wide companion document §5 for the full reasoning; no competitor
   has solved this either, and the one regulatory candidate that could
   change that (the 2026 NEC) has not yet produced a comparable vendor
   category.
8. **The single-location scope boundary remains correct, now with concrete
   detail on what crossing it would require** (§2.11) — parent/child
   accounts, cross-location dispatch, roll-up reporting. This pass found
   texture, not a new argument to build it; it stays last.

---

## 5. What this document does NOT establish

- **No vendor page was opened directly, at all, in this pass.** The same
  is true of the regulator pages behind §2.9's CARB finding — `arb.ca.gov`
  and `rmpr3.arb.ca.gov` are WebSearch snippets of the regulator's own
  domain, not an opened page, the same evidence grade as every vendor
  claim in this document, just a different kind of source.
- **No patent claim was read.**
- **No competitor product was used, demoed, or tested.**
- **No pricing figure here should be quoted to a prospect** until re-read
  from the live page.
- §2.7's AIM Act penalty-figure resolution is a multiply-corroborated
  secondary-source read, not a primary-source page read (`ecfr.gov` and
  `federalregister.gov` were both `EGRESS_BLOCKED`) — re-confirm from
  `ecfr.gov` directly before this figure appears in anything contractual.
- This document does not decide whether SAIRNmechanical should build any of
  the items in §4, in what order, or at what cost — that is a
  `sairn-software-architect` and `sairn-decision-gate` question, same as
  this series' own precedent declines to decide the gaps it finds.

---

## 6. Decay

Every fact in this document is a search-index snapshot from 2026-09-25 of
pages this session could not open, layered on an internal anchor
(`docs/2026-09-17-trades-audit-rederived.md`) that itself predicts its own
decay and has already caught two regulatory dates moving later than an
earlier pass recorded them. **Do not treat any cell here as current without
re-reading the source page and re-deriving the internal state.** The one
action this document asks for, ahead of any competitive finding: run this
pass again from a network that can reach vendor and patent-office domains,
and only then decide what — if anything — to build.
