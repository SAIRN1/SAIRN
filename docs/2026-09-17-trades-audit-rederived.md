# The 2026-08-21 plumbing / electrical / HVAC research, re-derived 2026-09-17 — one regulation arrived and nothing moved

**Derived 2026-09-17 (CC) against the code at HEAD**, using the method of the
roofing, senior/mechanical and StoneDesk passes: markers, then a hand-read of
every ambiguous hit, then a wiring check. §2 is research rather than status and
says so.

---

## 0. What this document is, because it changes what "reconcile" means

`docs/superpowers/specs/2026-08-21-plumbing-electrical-hvac-worldwide-research.md`
is a **research report, not a gap-state table.** It has no "SAIRNx state" column
and never claimed one. Eight sections: competitive landscape per trade,
multi-trade platforms, the upgrade case, worldwide regulatory differences, named
user complaints, trade-specific technical needs, trade bodies, and flagged gaps.

So most of it is **not reconcilable against code** — a finding about what
Housecall Pro shipped or what NECA Australia chapters run does not go stale
because SAIRNmechanical changed. Two halves *are* reconcilable and both were
re-derived:

* **§6, trade-specific technical needs** — against SAIRNmechanical, the only one
  of the three trades that has an app.
* **§8, the dated regulatory items** — which is the half that decays on a
  schedule rather than on code, and is where this pass found something.

**One framing fact first.** SAIRNmechanical offers **fourteen job-type chips and
every one is HVAC** (`ac-replacement`, `furnace`, `ductwork`, `water-heater`,
`commercial-rtu`…). There is no plumbing or electrical trade in the product. So
§6's electrical and plumbing rows are **scoping for a trade that has not been
unlocked**, not gaps in a shipped feature, and are reported that way below.

---

## 1. §6 trade-specific needs, against SAIRNmechanical at HEAD

| Need | Markers | State |
|---|---|---|
| **EPA 608 / refrigerant tracking** | `608` × 15, `refrigerant` × 29 | **BUILT, and carefully.** `api/_lib/mech-assets.js` classifies each unit `at_or_above` / `below` / `unknown_charge` against a cited threshold; a unit never weighed is `unknown_charge` and **never** `below`. The EPA-608 section (Type I/II/III/Universal) is a first-class credential field with the equipment-not-ranks rule |
| **Leak-rate calculation + 30-day repair countdown** | `leak.rate` × **0** | **ABSENT.** The charge is recorded; the leak rate and the repair clock are not |
| **Manual J / D / S load calculation** | `Manual J` × 4, `Manual D` × 0, `Manual S` × 0 | **NOT BUILT, and the four hits are all AI system-prompt text** — *"Apply Manual J principles for sizing"*. §6 is explicit that this is a **procurement-grade** requirement: many jurisdictions require the calculation come from **ACCA-approved software specifically**. An assistant told to apply the principles produces a number no code official has to accept, and that distinction is not stated anywhere near the prompt |
| **F-Gas Category I–III (EU)** | `F-Gas` × 0 | **ABSENT.** Consistent with a US-only product; see §2 |
| **NEC Article 220 load calculations** | `NEC` × 0, `Article 220` × 0 | **N/A — no electrical trade in the product** |
| **Low-voltage / fire-alarm carve-out** | `low-voltage` × 0, `fire alarm` × 0 | **N/A — same** |
| **EV charger / solar crossover** | `EV charger` × 0, `solar` × 0 | **N/A — same** |
| **Backflow / cross-connection** | `backflow` × 6, `cross-connection` × 0 | **CREDENTIAL TYPE ONLY.** All six hits are one `<option value="backflow">` in the credential dropdown. That is a technician holding a backflow cert, not the three-party testing-and-submission flow §6 describes — the same shape OSHA had in SAIRNroofing before B4 was built |
| **Geothermal / IGSHPA three-licence crossover** | `geothermal` × 0, `IGSHPA` × 0 | **ABSENT** |
| **Permit / inspection workflow** | `permit` × 0 | **ABSENT.** `inspection` × 2, both in the doc-scanner's document-type list |
| **Data portability / lock-in** | `export` × 12, `portab` × 0 | **NOT BUILT AND DISCLOSED** — the CSV button calls `mechNotLive('CSV export','exported')`, which toasts *"CSV export is not live yet — nothing was exported"*. §8 rates lock-in the dominant real-world pain across every vendor examined |

---

## 2. §8's dated items — the half that decays on a schedule

The research flagged two regulatory changes and told the reader to treat them as
*"a moving target, not a static requirement."* Both dates have now passed. Both
were re-verified against primary reporting rather than quoted.

### 2.1 The AIM Act threshold is IN FORCE, and it is not modelled

**§8 said:** *"AIM Act threshold change (50 lbs → 15 lbs HFC refrigerant,
effective January 2026) … materially widens which US HVAC jobs require EPA 608
documentation."*

**Verified:** correct, and in force since **2026-01-01**. Appliances containing
**15–49 lb of HFCs with GWP > 53** are now subject to leak detection and repair
under **40 CFR 84.106 / Part 84 subpart C**, with a 30-day repair window, an
initial verification test inside it, a follow-up within 10 days, and a
retrofit-or-retire plan if the repair cannot be verified.

**At HEAD:** `api/_lib/mech-assets.js` carries

```
const EPA_LEAK_THRESHOLD_LB = 50;
const EPA_THRESHOLD_CITATION = '40 CFR 82.157';
```

**This is not a stale constant, and calling it one would be the easy wrong
answer.** 40 CFR 82.157 is the **Section 608** leak-repair rule, and 50 lb is
**correct for the rule the code cites**. The AIM Act rule is a *different
regulation* — Part 84 — and the app does not model it at all: no second
threshold, no GWP field, no leak rate, no repair clock.

The practical consequence is narrow and precise. A 20 lb R-410A unit is
correctly reported `below` the 82.157 threshold, and has been in scope under
84.106 since January.

**THE APP ALREADY DISCLAIMS EXACTLY THIS, and the disclaimer is why this is a
gap rather than a false statement.** The board's note ends:

> *"This app does not decide whether leak-repair rules apply; confirm against
> the current rule."*

That is the third instance of this platform's disclosure posture, after
SAIRNroofing's *"This is not an EDI connection"* and *"This is not a QuickBooks
connection"*. It is the right sentence. **It is also doing a great deal of
work**: the screen shows a count computed against one named threshold while a
second now applies, and the only thing standing between that and a wrong
conclusion is a shop reading the last clause.

**`threshold_lb` is overridable** — `evaluateRegistry(..., { threshold_lb })`,
exported *"so a caller can see the number the answer depends on"*, which is good
design. **Nothing in the product passes one.** The single non-test caller is
`api/sd-data.js:1349` forwarding `payload.threshold_lb`, and `sairnmechanical.html`
never sends it, so the board always shows 50.

**The reconciliation finding is not that the research was wrong. It is that the
research was right, dated it correctly, the date arrived eight months ago, and
nothing moved.**

### 2.2 The EU F-Gas dates are a YEAR LATER than recorded

**§8 said:** *"training standardization by March 12, 2026; certification updates
required by March 11, 2027."*

**Verified:** Member States must establish or adapt certification programmes by
**11 March 2027**; refresher training becomes mandatory (at least every seven
years) from **12 March 2027**; and holders of certificates under the old
517/2014 regime have until **12 March 2029**.

So the 2026 date in the audit does not match current primary reporting, and the
2027 date lines up with the *programme* obligation rather than a later one. **The
direction is later than recorded, not sooner.**

This is the second time this reconciliation method has caught a regulatory date
moving **away**: `docs/2026-09-17-sairnroofing-competitive-gap-rederived.md` §4
found Spain's Verifactu postponed a full year. A date in an audit is habitually
read as a floor that only gets closer. Twice now it has not been.

**Bearing on SAIRNmechanical: none today** — there is no EU customer and no
F-Gas field. Recorded because §6 lists F-Gas Category I–III as a trade-specific
need, and anyone building to it should read the regulation rather than this
line or the 08-21 line.

---

## 3. What is genuinely open

| Item | Why it is open |
|---|---|
| **AIM Act / 40 CFR 84.106 not modelled** | In force since 2026-01-01. Needs a second threshold, a GWP > 53 test, and the 30-day repair clock. **Buildable in-house and un-gated** — the only one in this pass |
| Leak-rate calculation + repair countdown | The other half of the same row |
| Manual J as a compliance artefact | **Not buildable as such** — jurisdictions require ACCA-approved software, which is a certification, not an engineering task. What IS available is saying so on screen next to the assistant that offers to apply the principles |
| Backflow testing flow, geothermal, permits | Real §6 needs, none built |
| Electrical and plumbing needs (NEC 220, Part P, low-voltage, EV/solar) | **Not gaps** — no such trade is unlocked in the product |
| Data portability | Disclosed, not built. §8 rates it the dominant pain in the category |

---

## 4. Limits

* **Markers are a floor, never a ceiling.** The roofing pass's §2.2 stands as the
  warning: one hyphen produced a false negative there, and it was caught only by
  running a second spelling of the same idea.
* **§§1–5 and §7 were not reconciled and cannot be** — competitor behaviour,
  user complaints and trade-body structure are not properties of this codebase.
  They are also the half the research is best at, and re-running them would
  duplicate it.
* **Two regulations were re-verified; the rest of §4's worldwide licensing
  content was not.** It inherits the 08-21 report's own standing.
* **No live check.** Against the repository at HEAD, not the deployed app.
* **No code was written and no app file was touched.**

## Sources

- [EPA — Leak Repair Requirements for Appliances Containing Regulated Substances (fact sheet, 2026-01)](https://www.epa.gov/system/files/documents/2026-01/er-r-fact-sheet-leak-repair-2026-01-13_1.pdf)
- [ACHR News — Leak Rules Tighten as Threshold Drops to 15 Pounds](https://www.achrnews.com/articles/166298-leak-rules-tighten-as-threshold-drops-to-15-pounds)
- [HVAC School — The EPA's 15-Pound Refrigerant Threshold in 2026](http://www.hvacrschool.com/the-epas-15-pound-refrigerant-threshold-in-2026/)
- [European Heat Pump Association — The new F-gas Regulation: detailed guidelines](https://www.ehpa.org/wp-content/uploads/2024/11/F-Gas-regulation-guidelines_European-Heat-Pump-Association_November-2024.pdf)
- [AREA — F-Gas Guide 2024](https://area-eur.be/sites/default/files/2024-10/guide-fgas-2024.pdf)
- [Compliance & Risks — Regulation (EU) 2024/573 reviewed](https://www.complianceandrisks.com/blog/regulation-eu-2024-573-european-commission-adopts-new-f-gas-regulation/)
