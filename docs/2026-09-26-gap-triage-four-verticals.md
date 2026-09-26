# Gap triage — StoneDesk, roofing, dental, senior, mechanical

**2026-09-26 (Cody). Scoping only. Nothing built.**

**HEADLINE: across these verticals there is essentially NOTHING left that is
buildable in-house and un-gated — and the two most recent status documents are
stale in the direction of UNDERSTATING what has been built.** Two rows they
record as open are closed, and I found that by re-deriving against the app files
rather than reading the rows.

That direction matters. A stale row that overstates progress gets caught the
moment somebody tries to use the feature. **A stale row that understates it sends
a session to build something that already exists** — which this platform has
recorded happening at least twice.

---

## 1. Method, and why I did not start from the 08-26/08-27 originals

The dispatch asked for a triage of the 2026-08-26 (roofing/dental/senior) and
2026-08-27 (mechanical) audits. **Four re-derivations of those audits already
exist** and are more recent than the originals:

- `docs/2026-09-17-sairnroofing-competitive-gap-rederived.md`
- `docs/2026-09-17-sairndental-competitive-gap-rederived.md`
- `docs/2026-09-17-senior-mechanical-competitive-gap-rederived.md`
- `docs/2026-09-15-competitive-gap-status-rederived-mechanical-and-five-apps.md`

So this pass reads those for the claimed status and then **re-derives each
still-open claim against the app file**, which is where the two corrections came
from. Re-deriving from the originals would have discarded a month of work.

---

## 2. TWO ROWS RECORDED AS OPEN THAT ARE CLOSED

### 2.1 SAIRNroofing A5 — accounting integration. **CLOSED, half-built and half-refused.**

The 09-17 re-derivation says, in its own §3: *"One row: A5, accounting
integration. Zero markers, no partial, no disclosure. It is the row still
standing."* Measured today in `sairnroofing.html`:

| marker | 09-17 recorded | today |
|---|---|---|
| `QuickBooks` | 0 | **4** |
| `chart of accounts` | 0 | **4** |
| `Xero` | 0 | **1** |

And it is not prose. `rfGlExport()` at `:1652` behind a **"Build journal"**
button at `:874`, a chart-of-accounts panel at `:850`, and `gl_export` appears
**3 times in `api/sd-data.js`** — so the write path is server-side too.

**AND THE DISCLOSURE THE 09-17 ROW SAYS IS ABSENT IS THE MOST IMPORTANT PART OF
IT.** At `:846`: *"**This is not a QuickBooks connection.** Nothing here signs in
to your accounting package or writes to it. It produces a journal file you…"*
That is the same buildable-half-built / vendor-half-refused-on-screen shape the
document credits **B6** with. A5 now has it too.

**So roofing's "one row still standing" is standing on a measurement that is
about nine days out of date.**

### 2.2 SAIRNdental B2 — the roll-up had no reader. **CLOSED.**

The 09-17 re-derivation calls B2 *"Needs a decision, not an estimate. Either a
panel (owner-gated, reusing `DNT_MANAGEMENT_ROLES`…) or a written deferral…
What must not persist is the current state."* Measured: `panel-rollup` exists in
`sairndental.html:1136` with an `rRollup()` refresh, an owner-only path, and a
comment recording that **the server is the real gate** —
*"api/sd-data.js refuses dnt_rollup from any role outside
DNT_MANAGEMENT_ROLES regardless of what this div does."*

**The decision was made and the panel was built.** The row should say so.

---

## 3. WHAT IS GENUINELY STILL OPEN — prioritised

Ordered by *whether anybody can act on it*, which is the only ordering that
helps.

### Tier 1 — open, and actionable WITHOUT a vendor: **none found.**

That is the finding, not an omission. Every remaining row below needs a
commercial relationship, a certification, or a decision nobody has made.

### Tier 2 — open, gated on a relationship somebody could go and get

| vertical | row | what it needs |
|---|---|---|
| **SAIRNsenior** | **A2 telephony EVV** | a telephony provider. The offline half is CLOSED (`offline` × 24). The 2 `telephony` hits are both COMMENTS explaining why telephony persists in rural/no-signal visits — the doc is correct that it is open. |
| **SAIRNsenior** | **A4** 837 / clearinghouse | a clearinghouse relationship |
| **SAIRNdental** | **A1** real-time eligibility, **A2/A3** 837D/835 | a clearinghouse relationship — one engagement could serve both apps |
| **SAIRNdental** | **A5** imaging / CBCT | a vendor API. My 2026-09-25 correction stands: DEXIS publishes public API docs, so this is no longer "only NexHealth" and the row moved from vendor-gated to buildable-in-principle. **Still not built.** |
| **SAIRNroofing** | **B6** supplier EDI transport | trading-partner agreements with ABC Supply, Beacon, SRS *individually* |

**One engagement unlocks four rows.** A single clearinghouse relationship reaches
SAIRNsenior A4 and SAIRNdental A1/A2/A3. If anything here is worth a business
conversation, it is that one.

### Tier 3 — open, and REFUSED for a reason, not pending

These should not be reopened as engineering work. The refusals are recorded and
right.

| vertical | row | why refused |
|---|---|---|
| **SAIRNroofing** | B3 certified payroll | would require asserting a prevailing-wage determination; a fabricated rate goes into a **federal filing** |
| **SAIRNdental** | A6 e-prescribing / EPCS | certification-gated — 21 CFR 1311 identity-proofing and DEA registration |
| **SAIRNdental** | B4 central call centre | the audit that raised it does not recommend it |
| **SAIRNmechanical** | G12 data portability | `mechNotLive('CSV export', 'exported')` × 3 — a **disclosed** refusal on screen, still present and still honest |

---

## 4. StoneDesk — the 8th gap, and the audit is wrong about StoneDesk's own side

Seven of eight are closed (GAP 5 found built 09-15; GAP 7 closed 09-03; GAPs 1,
2, 3 and the remnant half of 8 closed 09-02; GAP 6 is a standing decision not a
work item). **The 8th is GAP 4 — slab-scanner integration.**

**IT IS FURTHER BACK THAN THE AUDIT RECORDS, AND THE ERROR WOULD MISLEAD A
BUILDER.** GAP 4 says *"Vein Match works from photos… competes against a
higher-fidelity input it cannot currently accept."* Measured in the Vein Match
panel (`stonedesk.html:33420`):

- `type="file"` — **0**
- `accept="image` / `capture=` — **0**

`sdVeinAnalyze()` at `:33536` reads six **text and number** fields — project
name, a stone dropdown, a layout style, slab count, sq ft, a free-text
description — POSTs a prose prompt to `/api/claude` asking for *"vein matching
guidance"*, renders the answer, and saves `{proj, stone, style, date}`.

**Vein Match does not work from photos. It accepts no slab imagery of any
kind.** So closing GAP 4 is not one step (accept a scanner feed) but two — accept
an image at all, then accept a *calibrated* one — and **only the first is
un-gated.** A builder starting from the audit's sentence would be adding scanner
support to a panel with no image pipeline.

**ALREADY FIXED, RECORDED SO IT IS NOT RE-FOUND:** the three quantitative KPIs on
that panel — Match Quality %, Waste Reduction %, Material Savings $ — are set to
`'--'` at `:33501-33503`, not to numbers derived from a text description. The
fabricated-KPI half of this panel was closed by an earlier session. Only
`vein-jobs`, a real count, carries a figure.

**NOT BUILT HERE, deliberately.** An image-ingest pipeline into a 2MB file
touching the app's named differentiator is not a blind build, and the audit's own
premise needs correcting first so the next session does not start from a false
one.

---

## 5. What this pass did NOT do

- **It did not re-derive every row**, only the still-open ones plus the two that
  turned out closed. A row recorded as closed was taken on trust; that is the
  weaker half of this pass and is stated rather than glossed.
- **It did not verify any competitor claim.** Every vendor-gated conclusion is
  inherited from the earlier audits.
- **It built nothing**, per the dispatch.
- **It did not correct the source rows.** §2's two corrections and §4's are
  recorded here; folding them into the four re-derivation documents is a separate
  edit and those documents are not all mine.

---

## 6. Decay

Measured against the apps at `e57c2783`, 2026-09-26. §2 exists *because* a
nine-day-old measurement had moved. **Re-derive before acting on any row here**,
including §3's "none found" — that is the claim most likely to be wrong first.
