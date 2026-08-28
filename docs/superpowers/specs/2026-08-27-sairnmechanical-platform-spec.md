# SAIRNmechanical — Platform Spec (OPERATIVE)

**Status: operative spec. This is the document a build or a review is checked against.**
Created 2026-08-27.

This is **not** a research document. It states requirements and verdicts. It deliberately carries
**no citations, no vendor evidence and no sourcing** — all of that lives in the research doc, and
duplicating it here would create the two-copies-that-drift problem this platform has been bitten by
repeatedly.

> **Evidence for every item below:**
> `docs/superpowers/specs/2026-08-27-sairnmechanical-shared-platform-competitive-research.md`
> Section references (§3 A5, §9a, §1b-ii, …) in this spec point into that document. If an item here
> and that document ever disagree, **the research doc holds the evidence and this doc holds the
> decision** — reconcile explicitly, do not silently pick one.

**Two prior-decision documents this rests on, both non-negotiable and neither re-opened here:**

1. **One shared platform with trade-gated modules** for plumbing, HVAC and electrical — not three
   codebases.
2. **Build order across the three trades is deferred.** Nothing in this spec decides it, and §4's
   capability list is explicitly not it.

---

## 1. BINDING REQUIREMENT — multi-trade agreements and per-trade billing

**This is a requirement, not a finding. It binds any schema, API or UI that touches agreements,
invoices or billing.**

### 1.1 The requirement

**One agreement MUST be able to span multiple trades, carrying per-trade line items and per-trade
billing.** It MUST NOT be modelled as three per-trade agreements bundled and presented as one.

### 1.2 The rule that makes it testable

> **Trade is an attribute of the LINE ITEM. Trade MUST NOT appear on the agreement header.**

A model where trade sits on the contract header — or where a customer holds one agreement row per
trade — **fails this requirement.**

### 1.3 Why this is stated as a hard rule rather than a guideline

**It fails silently.** A header-level `trade` field still looks correct for a single-trade customer,
and every test written against a single-trade fixture will pass. The defect surfaces on the first
multi-trade renewal, by which point live agreement data is already in the wrong shape and the
migration is a data migration, not a schema change.

### 1.4 Scope — every tier, no exceptions

This holds for **small-business, mid-market and every size in between.** It is **not** a
mid-market-only or commercial-only requirement.

Small shops take commercial multi-trade work. A two-van shop servicing a strip mall or a small
property-management portfolio signs the same *shape* of agreement as a 150-employee mechanical
contractor. Tier changes the **volume** and the **surrounding financial machinery** (retainage,
AIA G702/G703, WIP — see G5), never the **shape of the agreement**.

Gating multi-trade agreements behind a tier would reproduce, internally, the exact per-trade split
that decision (1) exists to avoid.

### 1.5 Additional per-trade attributes required on the line item

- **Price** (obvious, stated for completeness)
- **Estimated duration.** Execution time is trade-specific, independently of price. A line item
  carrying price-by-trade but not duration-by-trade is incomplete.

### 1.6 Downstream propagation — both directions, from one record

Per-trade line items MUST:

- **roll up** to a single agreement-level invoice, **and**
- **break out** per trade for margin and revenue reporting.

Both directions MUST derive from the same record. Two separately-maintained representations of the
same agreement is a defect.

### 1.7 The same record covers three commercial shapes

Residential **membership plans**, commercial **PPM** contracts and **AMC** (Annual Maintenance
Contract) markets are **the same record with different cadence and different money.** They MUST NOT
be three separate models.

### 1.8 What a review MUST check

- [ ] No `trade` column, field or enum on the agreement/contract header entity.
- [ ] `trade` present on the line-item entity.
- [ ] Line item carries an estimated-duration attribute, per trade.
- [ ] A single agreement can hold line items of two different trades — demonstrated, not asserted.
- [ ] Invoicing rolls multiple trades' line items into one agreement-level invoice.
- [ ] Reporting can break the same agreement out per trade.
- [ ] Membership / PPM / AMC are one entity, not three.
- [ ] No tier gate, plan gate or feature flag restricts multi-trade agreements to larger accounts.

---

## 2. BINDING REQUIREMENT — the trade entitlement model

*(Derived from §9a G1 and G21, and §1b-ii of the research doc.)*

### 2.1 The requirement

A company holding one trade MUST be able to have a second trade **unlocked inside its existing
account**:

- **no migration**
- **no second login**
- **no new tenant**
- **no re-onboarding**

### 2.2 The market contrast that defines what NOT to build

Two mechanisms exist in the market. **Neither one satisfies §2.1, and both are easy to mistake for
it:**

| Mechanism | What it actually gates | Why it fails §2.1 |
|---|---|---|
| Business units with a `Trade` attribute | **Visibility** — which pricebook categories a technician sees | Not entitlement. Everything is present; some of it is hidden |
| One tenant per acquired company + a roll-up/control layer above them | **Separation between companies** | The answer to "add a trade" here is *spin up another tenant* — which is precisely a migration and a second login |

> **The incumbent's answer to multi-trade growth is a new tenant. This platform's answer MUST be an
> in-place unlock. These are opposites, and it is the clearest single differentiator to come out of
> the research.**

### 2.3 The timing constraint

**The entitlement model MUST exist in the data model from the first table**, even if no second trade
ships for a year.

Entitlement is the expensive class of change to retrofit: it touches every read path, every gate and
every existing row simultaneously. Adding it later is not a feature addition, it is a rewrite of the
authorisation surface.

### 2.4 What a review MUST check

- [ ] An entitlement concept exists and is distinct from visibility/filtering.
- [ ] Entitlement is per-account, per-trade, and grantable without creating a new account or tenant.
- [ ] No code path requires a second login, a new tenant, or a data migration to add a trade.
- [ ] Trade-gated content (see §3 Tier C) checks entitlement, not just a UI filter.

---

## 3. The pattern table — shared core vs trade-gated

*(Full table, from research doc §9b. Verdicts are decisions; evidence is in §3 of the research doc.)*

**The seam, stated once:** the **shared core is the record of who / what / where / when** — people,
credentials, sites, assets, contracts, jurisdictions, stock, money. The **trade-gated part is the
calculation and the form.**

### Tier A — shared, same shape across all three trades

| ID | Pattern | Verdict |
|---|---|---|
| **A1** | Credential registry (person → credential → issuing authority → jurisdiction → number → expiry), plus apprenticeship progression (OJL/OJT hours, RTI, wage progression) upstream of it | **Shared table**, trade-tagged and jurisdiction-tagged rows. **Not three tables** |
| **A2** | Site asset registry (customer → site → asset; make, model, **serial**, install date, warranty, open agreements, service history) | **Shared schema**, per-trade asset taxonomy only |
| **A3** | **Recurring agreement — membership / PPM / AMC** | **Shared. BINDING — see §1.** One agreement, many trades; trade on the line item, never the header |
| **A4** | Jurisdiction / permit authority | **Shared.** Jurisdiction is the primary key; trade is an attribute of the *permit*, not of the authority |
| **A5** | Compliance certificate issuance (CP12, CP14, EICR, Minor Works, PAT, G3, CoC, DGUV V3, …) | **Shared engine + per-(trade, jurisdiction) form schema.** The certificate is a **join** into A1 and A2, not a document. See §3.1 |
| **A6** | Skill/credential-constrained dispatch | **Shared engine.** Its input is A1 |
| **A7** | **Outbound compliance submission to an external authority** | **Shared entity** — authority, payload, submission state, fee, proof-of-receipt — instantiated per (trade, jurisdiction). Not five unrelated features |

### Tier B — shared engine, trade-keyed lookup behind it

| ID | Pattern | Verdict |
|---|---|---|
| **B1** | Inventory / truck stock | Shared shape; per-trade distributor catalogue |
| **B2** | Flat-rate pricebook | Shared engine; trade is a **category on the task**, not a separate catalogue |
| **B3** | Union / prevailing-wage payroll | One engine; fringe rates keyed by trade classification and local |
| **B4** | Consumer financing | One integration surface; splits on **ticket size**, not trade |
| **B5** | Scheduling across job shapes (same-day / recurring / multi-day, per-day crew assignment, multi-day conflict detection) | One board; trade-neutral |
| **B6** | Distributor procurement (cXML, OCI PunchOut, EDI 850/855/856/810) | One protocol; per-trade endpoints and catalogues |
| **B7** | Customer intake / call handling | Trade-neutral engine; trade-flavoured triage vocabulary |
| **B8** | Structured field capture (dataplate OCR → populates A2) | One capture engine; per-trade equipment taxonomy |

### Tier C — genuinely forked, MUST be trade-gated modules

| Item | Trade |
|---|---|
| Manual J / D / S load calculations (and ACCA-approved-software gatekeeping for code submission) | HVAC |
| NEC Article 220 load calculations | Electrical |
| UPC / IPC fixture-unit sizing and venting (a hard regional content fork) | Plumbing |
| Estimating assemblies and labour databases | All three, mutually incompatible |
| Refrigerant / F-gas ledger (EPA 608, AIM Act, EU F-Gas Cat I–III) | HVAC only |
| Backflow / cross-connection test content | Plumbing only |
| Manufacturer warranty registration | HVAC-weighted |
| Test-instrument certificate import | Electrical only |

**Tier C is the natural content of a trade-gated module.** Sequencing *within* Tier C **is** the
deferred build-order question and is deliberately not decided here.

### 3.1 A5 — three modelling rules that a naive certificate design gets wrong

Derived from the DGUV V3 protocol, the most precisely specified certificate found in the research
(research doc §3 A5 carries the full ten mandatory fields and the primary source).

1. **The certificate is a JOIN, not a document.** The tester field is a reference into **A1**; the
   device field is a reference into **A2**. Storing the tester's name as a string cannot answer *"was
   this person qualified on the day they signed it."*
2. **Test-instrument calibration validity is a THIRD dated-validity registry.** It is
   contractor-owned — neither a person-credential (A1) nor a customer-site asset (A2). It has no
   home in either and needs its own.
3. **The next-due date is COMPUTED, not looked up.** Intervals derive from a site hazard assessment
   (device type × environment × failure rate at last inspection), ranging 3–24 months, and reference
   values are explicitly *not* maximum limits. **A fixed `next_due = last + interval` field cannot
   express this.**

---

## 4. Prioritised capability list

*(From research doc §9d, reproduced with its scope note and caveat intact.)*

> **SCOPE NOTE — read before using this list.** This ranks **platform capabilities**. **It is NOT a
> build order across the three trades.** Trade build order remains deferred by decision (2) and
> nothing in this list bears on it.

> **CAVEAT — read before using this list.** Gap frequency measures **where competitors are weak**,
> not **what customers need first.** Those are different questions and they disagree. G15 and G17 are
> the widest gaps in the research precisely *because* nobody has built them — which also means no
> customer is currently choosing a vendor on them. **Table stakes must ship regardless of whether
> they appear as gaps at all.** The list is ordered by **frequency × prerequisite depth**, with
> table-stakes items called out as such even where their gap score is low.

| # | Capability | Why here | Frequency |
|:--:|---|---|---|
| 1 | **Credential registry + expiry + dispatch eligibility (A1 → A6)** | Underpins A5, A6, A7 and G2/G3/G19. Nothing else can be gated correctly until it exists. SAIRNbuild already ships a proven enforcement shape (prequal + expiry + hard block at award) to model on | 3 trades, every region |
| 2 | **Site asset registry (A2)** | Prerequisite for A3, A5, A7, B8, G13. **Table stakes** — every incumbent has it | 3 trades, every region |
| 3 | **Multi-trade agreement + per-trade line-item billing (A3)** | **Already binding (§1), not discretionary.** Cheapest to get right before any schema exists; silently wrong if deferred | 3 trades, every region |
| 4 | **Trade entitlement model (§2, G1/G21)** | The differentiator, and retrofitting entitlement is the expensive class of change. **Must be in the data model from the first table** | 3 trades, global |
| 5 | **Compliance certificate engine with computed intervals (A5 + G17 + G20)** | Highest-value *differentiating* gap. Requires 1 and 2 first — the certificate is a join into both | 3 trades; DE/UK/NL/AU/NZ |
| 6 | **Outbound compliance submission (A7 + G15)** | Widest region breadth of any single gap, modelled by nobody. Depends on 5 | 3 trades; US/UK/AU/NZ/EU |
| 7 | **Pricebook categories (B2), job-shape scheduling (B5), truck stock (B1)** | **Table stakes.** Low gap score precisely *because* everyone has them. Not optional, just not differentiating | 3 trades, every region |
| 8 | **Mid-market financial layer (G5)** — retainage, AIA G702/G703, WIP, certified payroll, lien waivers | Hard boundary where SMB tools break. US-shaped; UK/EU analogues differ | 3 trades; US |
| 9 | **Integration surfaces — procurement (B6), intake (B7), field capture (B8)** | Established protocols and an existing bolt-on ecosystem. **Integrate rather than rebuild** | 3 trades; US/EU |
| 10 | **Per-trade forked content (Tier C)** | Genuinely trade-specific; the natural content of a trade-gated module. **Sequencing here is the deferred build-order question** | 1–2 trades each |

**Two exclusions, deliberate:**

- **Permit filing (G8) is not on this list as a build.** It is a ~30,000-jurisdiction problem with
  specialist vendors already on it. Treat as an **integration target**.
- **The consolidator segment is not a target.** It is already served (research doc §1b-ii). The
  frequency data points at the **organically-growing independent**, at both SMB and mid-market tier.

---

## 5. Gap register — all 21, with frequency

*(From research doc §9a. Trades = how many of the three it bites. Regions = distinct markets the
evidence spans. Evidence and citations are in the research doc, not here.)*

| # | Gap | Trades | Regions |
|---|---|:--:|:--:|
| G1 | No published "add a second trade" path at any vendor | 3 | global |
| G2 | Subcontractor compliance not integrated into dispatch | 3 | US |
| G3 | Credential-expiry → dispatch-eligibility enforcement claimed, not documented | 3 | global |
| G4 | Regulatory *content* genuinely non-shareable | 3 | global |
| G5 | Mid-market financial layer absent from SMB tools | 3 | US |
| G6 | Commusoft-class tools degrade at the commercial transition | 3 | UK/EU |
| G7 | Estimating does not cross the mechanical↔electrical line | 1 (elec) | US |
| G8 | Permit filing fragmented by jurisdiction **and** trade | 3 | US |
| G9 | China: no service-dispatch product | 3 | CN |
| G10 | Japan: no licensing-compliance-organised product | 3 | JP |
| G11 | Refrigerant/F-gas ledger has no analogue in the other two | 1 (HVAC) | US+EU |
| G12 | Lock-in / data portability dominates real-world pain | 3 | global |
| G13 | Manufacturer warranty registration left manual | 1½ (HVAC) | US |
| G14 | Electrical certificates already live in instrument-vendor software | 1 (elec) | UK/EU |
| G15 | **Outbound compliance submission is nobody's modelled object** | 3 | **US/UK/AU/NZ/EU** |
| G16 | South Korea: no contractor-side FSM | 3 | KR |
| G17 | **Inspection intervals treated as fixed lookups, not computed from risk** | 3 (elec sharpest) | **DE/UK/NL/AU** |
| G18 | Customer intake / AI call handling is a bolt-on everywhere | 3 | US |
| G19 | Apprenticeship/OJT-RTI progression separate from credential tracking | 3 | US |
| G20 | Test-instrument calibration validity tracked nowhere | 2 | DE |
| G21 | *Resolved and inverted* — consolidators are well served; the **organically-growing independent** is not | 3 | global |

---

## 6. Using this spec to review an existing or recovered `sairnmechanical.html`

This spec was written to be checked against, including against code that predates it. A review of an
older or recovered file should treat every mismatch as a **finding to report, not a defect to fix**
— the old file was built before these requirements existed, so a mismatch is expected and the
finding is *where* and *how expensive*.

**The three highest-value checks, in order:**

1. **§1.8 in full — the agreement/billing model.** This is the one requirement that fails silently
   and gets more expensive with every live row. If the recovered file has a `trade` on the agreement
   header, or one agreement per trade, that is the single most important thing the review can
   surface.
2. **§2.4 — is there any entitlement concept at all**, or only visibility filtering? "No entitlement
   model present" is a legitimate and useful finding.
3. **§3 Tier A vs Tier C** — is anything in Tier A implemented *per trade* (three credential tables,
   three asset tables, three agreement models)? That is the shape decision (1) rejects.

**UPDATED 2026-08-28 — the file is now real and pushed.** When this section was written,
`sairnmechanical.html` existed in neither this clone nor `origin/main`, and the note here warned
that any recovered copy was invisible until pushed. It was pushed: 88,781 bytes on `origin/main`,
recovered from an unmerged branch in `bb9dbb3` and de-fabricated in `4114e22`. Guardian's App File
Map was therefore right all along — it described an app living on a branch nobody had merged, not a
phantom.

**What a reviewer should carry now:** a Guardian scan of that file on 2026-08-28 came back clean on
every mechanical check — 6/6 script blocks parse, div balance 485/485, 0 duplicate ids, 0 duplicate
function names, 0 undefined handlers, 0 `console.log`, no box characters in string literals, and its
single `api.anthropic.com` hit is the comment `// NEVER api.anthropic.com`, i.e. the rule being
stated rather than broken. **One real finding:** `page-sairnbiz-connector` is an unreachable panel —
the div exists, and nothing anywhere calls `showPage('sairnbiz-connector')` or otherwise references
it. That is a live gap in the recovered app, not a scanning artefact.

---

**Change discipline for this document:** it is operative, so amendments are decisions, not edits.
Record what changed and why in the commit message. When a requirement here is superseded, mark it
superseded in place rather than deleting it — a silently removed requirement is indistinguishable
from one that was never made.
