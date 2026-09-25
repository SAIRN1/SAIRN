# Worldwide external competitive-gap audit — SAIRNmechanical

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
  and inspection workflow (absent entirely); geothermal/IGSHPA licensing
  (absent); data portability (a CSV export button exists and is explicitly
  disabled, toasting "CSV export is not live yet — nothing was exported").
  NEC Article 220, low-voltage/fire-alarm, EV-charger/solar and EU F-Gas are
  all correctly N/A — no such trade or jurisdiction exists in the product.

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

### 2.6 Data portability

CSV import/export is confirmed table stakes across essentially every FSM
vendor in the peer set (ServiceTitan, Housecall Pro, Service Fusion, Jobber
all state or strongly imply it). **This is the one item in this pass where
the gap against SAIRNmechanical's actual competitive peer set is
unambiguous**, and the app already has the button — it is disabled with an
honest toast rather than silently broken, which is the right interim state,
but the underlying gap is real and the fix is not novel engineering.

### 2.7 The AIM Act penalty figure — a discrepancy worth carrying to any customer-facing material

Vendor pages in §2.1 cite a $44,539/day/violation penalty ceiling; trade
press (ACHR News) cites $59,114/day as the current, 2025-inflation-adjusted
figure. **This pass does not reconcile the two figures** and neither should
any customer-facing SAIRNmechanical material until one is confirmed from a
primary EPA source — the same standard this platform already holds itself
to on the 82.157/84.106 threshold distinction its own code carries.

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

Reading §2 against the internal audit's own open-items list:

1. **Data portability is the cheapest, most defensible fix** — the market
   consensus is unambiguous and the app already has the disabled control.
2. **A transparent leak-rate calculation, if built, would be a real
   differentiator** rather than mere parity, because the two vendors
   closest to this category do not disclose their methodology and
   SAIRNmechanical's existing discipline (cite the exact CFR section, never
   silently combine two rules) is a stronger foundation to build a
   disclosed formula on than either competitor currently shows.
3. **Manual J and backflow are correctly left undisclosed-and-open rather
   than built** — the market's own leaders either partner (one vendor, one
   partner, across six surveyed) or disclaim (the two vendors with in-house
   calculators both disclose their limits). SAIRNmechanical's current
   posture already matches the more honest half of the market.
4. **Permits and geothermal remain genuinely low-priority** relative to the
   app's actual FSM peer set, whatever their value against a purpose-built
   permitting or geothermal-training product might be.
5. **The plumbing/electrical scope boundary remains correct** — see the
   trade-wide companion document §5 for the full reasoning; no competitor
   has solved this either, and the one regulatory candidate that could
   change that (the 2026 NEC) has not yet produced a comparable vendor
   category.

---

## 5. What this document does NOT establish

- **No vendor page was opened directly, at all, in this pass.**
- **No patent claim was read.**
- **No competitor product was used, demoed, or tested.**
- **No pricing figure here should be quoted to a prospect** until re-read
  from the live page.
- The AIM Act penalty-figure discrepancy in §2.7 is stated, not resolved.
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
