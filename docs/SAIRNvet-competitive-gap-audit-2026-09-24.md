# SAIRNvet competitive-gap status, re-derived 2026-09-24 — four "gaps" from the original research list are BUILT, and one of them was still wearing an in-app notice denying it

**Derived 2026-09-24 (Fourth) against the code at HEAD**, using the convention
`docs/2026-09-02-competitive-gap-status-rederived.md` set and the method the
2026-09-17 documents used: marker counts, then a hand-read of every non-zero
hit, then a caller-level check — does the capability have a panel, a nav
target, and something that actually sends it.

**PROVENANCE, because this document replaces a stranded one.** A cloud session
produced this audit on 2026-09-24 and could not land it: the push gate's check
9 runs `tests/session_lock_liveness_probe.py`, which is Windows-only and exits
COULD NOT SET UP on the Linux container, and the gate read that as a failing
seam — so the commit sat local-only on `claude/jolly-gauss-uropwz` behind an
override the auto-mode classifier correctly refuses. That gate defect is fixed
(docs-only pushes skip check 9; see the register record on the fix commit) and
this document is **recreated from the cloud session's actual findings,
re-verified against HEAD here** — not from the original research list, which
is the distinction that matters: the research list predates the last three
weeks of building and calls four SHIPPED capabilities gaps.

---

## 1. BUILT — four items the research list still calls gaps

Each verified by markers and by the caller-level check, not by memory.

### 1.1 Ambient scribe — BUILT
81 `scribe` hits, 14 `transcrib`, a dedicated endpoint
(`api/sairnvet-transcribe.js` — audio goes there and nowhere else), per-visit
consent recorded to `sv_scribe_consent` (registered 2026-09-23), and accepted
notes filed with `drafted_by: 'ambient_scribe'`, the model recorded, and the
consent id attached. The caller exists and writes real rows.

### 1.2 Species dosing safety — BUILT
`VET_SPECIES_REF` / `speciesref` (59 hits), a dose-safety banner and a
separate food-animal banner in the calculator markup, 121 toxicity/lethality
flags in the reference data (including Schedule II wildlife-immobilization
entries the app refuses to dose), a verified-calculation line, and a vet
sign-off gate (`dose_signoff`) that writes to the audit trail.

### 1.3 DEA controlled-substance register — BUILT, with its trail readable in-product
`sv_controlled` (12), the Controlled Substances panel with running balance and
Schedule-II witness field, and — the part the earlier audits flagged as
missing — the **Dosing Audit Trail panel** (69 `doseaudit` hits): every dose
calculated, refused, signed off or witnessed, readable through the product,
with UTC named beside local time and, since 2026-09-24, completeness verified
against the server's own Content-Range count rather than asserted.

### 1.4 Per-employee auth — BUILT, and the app was still denying it
Employee ID + PIN gate (`svGateSignIn`), signed 12h session, role served by
`whoami` from the server row, server-side session gate on all 41 `SV_RESOURCES`
(2026-09-21). **The finding this audit adds: the SOAP panel's authorship card
still told every user "SAIRNvet has no per-employee sign-in … chosen from a
dropdown and is never verified" — eleven days after that stopped being true.**
Fixed 2026-09-24 with five stale code comments carrying the same expired
premise; the card keeps its narrower true half (the stored field is a ROLE,
not a named person, and a ticked box is not an electronic signature).

---

## 2. REAL GAPS — what the caller-level check actually finds open

### 2.1 Radiograph AI screening — NOT BUILT, and the word "radiograph" flatters the search
27 `radiograph` hits, and a hand-read of all of them shows they are: a
modality dropdown option, an imaging status LOG (study → status → click to
update), a pre-purchase-exam CHECKBOX ("Radiographs Included"), and reference
data. `x-ray` 0, `dicom` 0. Nothing reads an image, nothing screens one,
nothing routes one to an AI. The imaging panel is tracking paperwork about
studies, not the studies. This is the mid-market differentiator the research
list correctly identifies and the app genuinely lacks.

### 2.2 Treatment-to-invoice — NOT WIRED
`treatment` appears 29 times and `sv_invoicing`/`sv_billing` exist as their
own panels, but no path carries a completed procedure into an invoice line —
the same capability-without-a-caller shape `dnt_rollup` had in SAIRNdental.
A treatment is recorded in one panel and billed by re-typing it in another.

### 2.3 Client-facing booking — NOT BUILT, and the app already renamed the panel honestly
Zero markers for online/self-service booking. The panel once called "Client
Portal" was renamed "Client Requests" on 2026-09-04 with the comment "There is
no portal" — it is a staff-entered log of phone/email requests and how fast
each was answered. Nothing a client touches.

### 2.4 The mid-market location/inventory tier — a STATUS BOARD, not an operations layer
`panel-multisite` is a KPI row and a table with a CSV export — a per-location
status readout. `inventory` appears ONCE in the whole file; `reorder` zero.
No stock levels, no par levels, no reorder path, no per-location inventory at
all. A multi-site practice group can SEE its sites here and cannot RUN them.

---

## 3. German items — idea source only

The German-market entries on the research list (GOT fee schedule alignment,
Praxismanagement conventions) are retained as idea sources for feature shapes
and are **not build tasks**: SAIRNvet has no German licence row, no locale, and
no regulatory driver on this platform. Recorded so the next reader does not
promote them to gaps.

---

## 4. Method limits, stated

Marker counts and hand-reads of the single file plus its api/ modules. No live
driving of the deployed app in this pass; the click-through record is
`docs/2026-09-23-wave3-click-through-reverification.md` (nav-only, one role).
"BUILT" here means the capability exists with a real caller at HEAD — it is
not a statement that any of it has been exercised by a paying practice.
