# Worldwide competitive-gap audit — StoneDesk

Research pass, 2026-09-02. **No code written, no app file touched.** Findings only.
Nothing here is a build decision; §7 lists what a build pass would need to settle
first.

Method: every competitor claim below was read from the **vendor's own site**, not
from a comparison article. Aggregator and "best software 2026" pages were used
only to *find* vendors — several of them (SlabWise, SlabOS, Stone Project) are
themselves competitors publishing comparison content about their rivals, and
their claims about other vendors are marketing, not evidence. Where a claim comes
from a third party it is labelled as such. Where a fetch failed it is recorded as
a failure rather than filled in.

---

## 0. The premise this audit was requested under is correct

Unlike the 2026-08-26 roofing/dental/senior audit — which opened by correcting a
false claim that ten apps had already been audited — this one needs no such
correction. `2026-08-26-competitive-gap-audit-roofing-dental-senior.md` §0.1
explicitly recorded that **StoneDesk has never had its own competitive audit**,
and `SAIRN-ACTIVE-WORK-cc.md` recorded the same finding again on 2026-09-02,
noting that commissioning one "is a research gate, not a continuation."

This is that gate. It is the **third** audit of its kind on the platform, not the
eleventh.

---

## 1. The market, as it actually is

Twenty-two products across seven categories. Verified vendor-by-vendor.

### 1.1 US business-management / ERP (StoneDesk's direct tier)

| Product | What it is | Pricing (from vendor site) |
|---|---|---|
| **Moraware** (CounterGo + Systemize + Inventory) | Category incumbent. ~2,600 customers (third-party claim, not verified on Moraware's own site). Modules: Drag-and-Draw, Estimates, Slab Layouts / Calendars, Digital Job Packets, Job Tracking / Purchase Orders, Inventory Management, Slab Allotment. QuickBooks + slab-scanner integrations. | CounterGo **$100/user/mo**; Systemize **$120/user/mo, 3-user minimum**, +$50/user past 5; Inventory **$50/user/mo** (requires Systemize) |
| **ActionFlow** | Azure-hosted. Modules: CRM, Cloud Data Storage, Reporting, **ActionPay**, **E-Signature**, Countertop Drawing, Mobile Application, ActionForms, **Barcoding**, **Dealer Portal**, Process Development & Automation, Quoting, Field & Fabrication Scheduling, Inventory Management. | Three packages, no contract (amounts not published) |
| **Stonify** | Full ERP. Calendar, Reporting, Finance, Installation, Fabrication, Drawing, Quoting, Digital Documents, Mobile Field App, **route planning**. AI: "ask about your sales," "build reports on request," "turn a purchase order into a complete project, automatically." Names **Claude and Codex** integrations. | **$500/mo base** (incl. $500 seat credit), +$50 standard / +$75 drawing / +$35 lite per user |
| **Stone Profit Systems** | Distributor-and-fabricator ERP with its own accounting. Inventory, Purchasing, Quotations, Estimates, Holds, Sales, Scheduling, **Accounting**, Reports, **Inventory & Bar-coding**, Security & User Privileges, **Multiple Locations**. Block-yield analysis and inspection reports for quarry/manufacturer tier. No AI features on the page. | Not published |
| **SlabWise** | 2024 entrant. Nesting (multi-job batching, vein-aware placement, remnant auto-listing, rotation + book-match), **Middleware** ("every templater in, every machine out"), Quoting (auto SF/LF/cutouts, Good/Better/Best, **e-sign + Stripe deposit**, branded PDF), **Contractor portal**, cutting presets. AI: photo-to-template dimension estimation, AI verification of template against sold scope. | **$99 / $299 / $799** per month; $1 for 14 days |
| **StoneGrid StoneApp**, **VISCO** | Named by DDL's market survey as US ERP-tier. Not independently fetched this pass. | — |

### 1.2 Non-US — and this is where the audit changes the picture

| Product | Region | What is verified |
|---|---|---|
| **iBlocky** (We Make Code) | **Italy** — Carrara district | Vertical 100% on stone. Third-party/vendor claim: **70 million slabs/year**, customers incl. Black Eagle, Planet Stone, Mondial Granit, Bassi & Bellotti. Modules: digital slab+block warehouse, double-sale prevention, share-with-clients-and-architects, always-correct price lists, **AI Render Studio** (turns a real slab photo into a photorealistic kitchen/bath/stair render, incl. **digital bookmatch**), iOS app with **offline mode**, **branded public catalogue with QR codes** and WhatsApp sharing, **no login required** for the client/architect. **€299/mo Base, €399/mo Elite** (unlimited users). |
| **DDL / Digital Dry Layout** | **Europe** | Project Planning, **Slab Digitization** ("AI-powered contour recognition for true-to-scale slab images" from a smartphone or scanner), StoneSync, Warehouse Management, **Customer Portal** (slab selection + offer overview + real-time inventory in a dedicated customer area), **Barcode & Labels**, Digital Cutting, **Handheld Scanner App**, Quality Management, Offers, Contact Management, Marketing Tools. Pricing by consultation. |
| **Marmo IA + ERPedra** | **Brazil** | ERP with **native AI** for marmorarias: quoting with 2D drawing, slab optimisation, production, finance. Real-time technical drawing assembly with holes, cutouts and prices auto-calculated. ⚠️ **Vendor site returned HTTP 403 to this pass** — these claims come from Brazilian third-party coverage (Stone Finder), not from the vendor, and should be re-verified before being relied on. |
| **Sistrom ERP** | Brazil | Built exclusively for ornamental stone. **Per-slab ID + barcode + exact measurements**; selling a slab blocks that specific batch. |
| **Marmu**, **Gransoft**, **Conesoft**, **ERP Suite** | Brazil | Measurement→technical-drawing→quote, slab-yield control, service orders, AP/AR. Not individually fetched. |
| **SlabWare** | International | Listed by DDL's survey in the ERP tier. Not fetched. |
| **EasyCo**, **O.C.V.M. Marmo**, **V.A.R.P. Marmo** | Italy | SME stone-sector management suites (Visual Studio / SQL Server era). Not fetched. |

### 1.3 Adjacent tiers StoneDesk does not compete in (but must interoperate with)

- **Slab imaging / matching** — **Slabsmith** (Slab Maker™, **Perfect Match™**, Slab Manager, Job Manager, Slab Consumer, Slab Scanner Interface, Live Scan, Image Enhancement, Locator, Layout; auto-generated remnants, remnant labels, saw/pick tickets; saw-overtravel visualisation; per-slab/per-job/per-material yield statistics; **automated live slab and remnant inventory published to the shop's own website**). Also Slabcloud.
- **Slab scanners** — Park Industries SideShot, Iride, Mapastone Mapascan.
- **Digital templating** — Prodim Proliner, Laser Products LT-2D3D, Flexijet.
- **CAD/CAM & nesting** — EasySTONE (DDX), Alphacam (Hexagon), Cutwise.
- **Drawing/estimating point tools** — QuickQuote, iCounterSoft, Easy Stone Shop.

---

## 2. What StoneDesk has that no competitor on this list has

Checked against `stonedesk.html` (62 panels + 3 pages), not assumed.

1. **Six AI features that are operational domain tools, not chat.** Vein Match, Seam AI, Sintered, Executive Suite, Field Map, Stone Hub. The AI in Stonify is *reporting* ("ask about your sales"); in SlabWise it is *template verification*; in iBlocky it is *rendering*; in Marmo IA it is *drawing/optimisation*. **Nobody else has a seam-placement or sintered-material advisor.** This is real and it is unclaimed territory.
2. **Breadth no competitor attempts.** Safety/OSHA silica, training, HR, warranty, remakes, damage, NPS, reviews, referral, bid board, price intelligence, market intel, tax, AP, check register, email security, IT admin. Moraware and ActionFlow are job-management systems. Stone Profits adds accounting. **None of them touch compliance, workforce or reputation.**
3. **Supplier lead-time risk correlation** ([0072], shipped 2026-09-02). No competitor site mentions lead-time-driven job risk at all. Stonify's AI turns a PO into a project; it does not tell you which jobs are going to be late because of it.
4. **Subcontractor compliance layer** (`api/sd-sub-auth.js`, shared platform layer). ActionFlow has a Dealer Portal; nobody has subcontractor insurance/compliance gating.

---

## 3. The gaps — verified against the file, ordered by risk

Every gap below was confirmed by grepping `stonedesk.html` and `api/`, not inferred.

### GAP 1 — There is no customer-facing portal. **Structural, and the largest.**

`panel-client` is a **print/PDF estimate view rendered inside the shop's own
app** (`stonedesk.html:5422`, "← Back to quote", `printEstimate()`). There is no
external URL, no customer login, no `api/*-portal.js` for StoneDesk
(`api/sen-portal.js` is SAIRNsenior's).

Who has one: **iBlocky** (branded public catalogue, QR, WhatsApp, *no login
required*), **DDL** (Customer Portal with slab selection and real-time
inventory), **ActionFlow** (Dealer Portal), **SlabWise** (Contractor portal),
**Slabsmith** (live slab/remnant inventory auto-published to the shop's website).

That is five of the strongest products in three regions independently converging
on the same thing. The homeowner picking their own slab from a phone link is
now the industry's default expectation, and StoneDesk cannot do it at all.

### GAP 2 — Nesting produces no machine output. **Highest operational risk.**

> **CORRECTED 2026-09-02, and the correction is worse than the original
> finding.** This section said "there is no export function of any kind." That
> was wrong in the specific and I found it by trying to build the missing
> feature. **Two exports existed** — `nestingExport()` (Export CSV) and
> `nestingPrint()` (Print), both wired to real buttons in the panel. The grep
> below missed them because it searched for the names a reader would *expect*
> (`nestExport`, `sawTicket`, `pickTicket`) rather than reading the panel's own
> markup for what its buttons actually call. **A grep for the name you assume
> is not a search for the thing.**
>
> What they did is the point. `nestingExport()` wrote a CSV of **exactly two
> rows** — a header and one row of slab width, height, material and cost — and
> **exported not one cutout**. `nestingPrint()` printed the material, slab size,
> yield, waste cost, an empty AI line and a signature line: **no pieces, no
> positions, no dimensions, and not even the canvas.** A cover sheet for a
> layout it did not contain. A fabricator printed it, carried it to the saw and
> had nothing to cut from, with nothing on the page saying so.
>
> **That is strictly worse than the absence this section reported**, and it is
> the same failure class as a fabricated KPI: a plausible artefact that is
> quietly empty. **Fixed the same day** — both now emit the full cut list in saw
> order with a stated origin corner, and the print embeds the layout image or
> says why it could not. 16 assertions in `tests/nesting_saw_ticket.js`. The
> machine half of this gap (DXF/G-code out to a specific CNC) is untouched and
> everything below still stands.

`panel-nesting` has `nestingInit / UpdateSlab / Scale / Draw / MouseDown /
MouseMove / AddCutout / UpdateKPIs / RenderList / Remove / Clear / Save / Load /
AIOptimize`, plus the two exports named in the correction above.
`g-code` and `gcode` appear **zero times in the entire file**, and that part
was and remains true.

DXF is **inbound only** — `panel-template` accepts `.dxf,.dwg,.pdf,...` uploads
from LT-2D3D / Proliner / Flexijet / Leica (`stonedesk.html:8899-8900, 8969`).
Nothing goes back out to a saw.

Slabsmith auto-generates saw and pick tickets. SlabWise's entire Middleware pitch
is "every templater in, **every machine out**." StoneDesk is currently half of
that sentence.

Note: the AI system prompt claims expertise in "CNC programming, DXF export"
(`stonedesk.html:9640`, `:25416`). That is a claim about the *advisor's domain
knowledge*, and it is defensible — but a shop owner reading it will reasonably
infer the product does DXF export, and it does not.

### GAP 3 — No barcode / scanner support anywhere.

`barcode` appears **zero times**. The only trace is `externalBarcode:''` at
`stonedesk.html:32793` — an empty placeholder field on a slab record, wired to
nothing. A `qrcode.min.js` library is loaded (`:25127`) but not for slabs.

Who has it: ActionFlow (Barcoding), Stone Profit Systems (Inventory &
Bar-coding), Slabsmith (barcode scanner inventory reconciliation), DDL (Barcode &
Labels **plus a Handheld Scanner App**), Sistrom (per-slab barcode; selling
blocks the batch).

This is the mechanism the entire industry uses to stop the **double-sale** — the
error iBlocky puts second on its own homepage ("Niente più doppie vendite"). It
is a yard-floor problem that a screen cannot solve.

### GAP 4 — No slab-scanner integration, and this undercuts Vein Match.

`slabsmith` appears **zero times** in the file (the AI prompt mentions "Slabsmith
and Horace integration" as *knowledge*, not as a code path). No SideShot, Iride
or Mapascan interface.

Vein Match works from photos. Slabsmith's Perfect Match™ works from calibrated
scanner imagery and matches **colour as well as vein, including across remnants**.
StoneDesk's differentiator is real but competes against a higher-fidelity input
it cannot currently accept. Accepting a scanner feed would strengthen Vein Match
rather than replace it.

### GAP 5 — No customer e-signature and no deposit collection.

E-signature **exists** (`ag.signedAt`, `ag.signerName`, executed-agreement
banner, `stonedesk.html:31306, 31566-31602`) — but only on **SAIRN's own service
agreements in `panel-agreements`**, i.e. SAIRN selling StoneDesk to a shop. The
shop cannot get its own customer to e-sign a quote.

`Stripe` appears 4 times: twice in AI advisor context strings, twice in the
service-agreement text. **No payment processing in the product.**

Who has it: SlabWise (e-sign + Stripe deposit on the quote), ActionFlow
(E-Signature + ActionPay).

### GAP 6 — No QuickBooks integration. **HELD OPEN ON PURPOSE — decided 2026-09-02, not to be closed.**

> **Status: real gap, deliberately not being built.** Michael's call, 2026-09-02:
> a direct QuickBooks connector would contradict the SAIRNbiz-routing decision
> already shipped in the AI system prompt, so it is on hold rather than in the
> backlog. This paragraph exists so the gap is never mistaken for an oversight,
> a missed finding, or something quietly dropped — it is a known competitive
> disadvantage that StoneDesk is choosing to carry. Reversing it is a platform
> decision about SAIRNbiz, not a StoneDesk feature request, and it should be
> reopened at that level or not at all.

`sdIntegQuickAdd('QuickBooks Desktop','Accounting')` (`:6358`) adds a **row to an
integrations registry** — it is a catalogue entry, not a connector. The other hit
(`:30120`) is a software-licence inventory row.

This is intentional: `stonedesk.html:25416` routes payroll/HR/accounting to
**SAIRNbiz**, explicitly telling the user "not QuickBooks/Gusto/ADP."

That is a coherent platform strategy and it should not be quietly reversed. But
it is still a **sales gap**, because Moraware, ActionFlow and Stone Profits all
integrate QuickBooks and the prospect already runs QuickBooks today. The
counter-argument ("SAIRNbiz is included free") is only persuasive if SAIRNbiz can
actually replace their existing books — a claim this audit did not test.

### GAP 7 — No multi-location support.

`multi-location`, `multiLocation`, `locationId` all appear **zero times**. Stone
Profit Systems ships "Multiple Locations." This caps StoneDesk at single-yard
shops and excludes exactly the consolidating multi-branch fabricator that has the
budget.

### GAP 8 — No remnant publishing to the shop's public website.

`panel-remnant` exists internally. Slabsmith publishes **live slab and remnant
inventory to the customer's own website automatically**; SlabWise auto-lists
remnants out of nesting. Remnant sale is margin recovery on material already paid
for — this is revenue, not a feature.

---

## 4. Two findings that are not competitive gaps but were found while looking

Recorded here because suppressing them until a tidier moment is how they get
lost. **Neither was fixed in this pass** — both are orthogonal to a research gate.

### 4.1 The Executive Suite advisors are primed with SAIRN's internal business data, and any customer can open them.

`panel-executive` is a plain sidebar button (`stonedesk.html:3476`) with a
**self-selected** role picker (`:8008`, `:24046`) — not gated on employee role.

The CFO advisor's context string (`:24775-24784`) contains **SAIRN Technologies'
own chart of accounts**, and **StoneDesk's own price book: "Starter $199/mo,
Professional $299/mo, Enterprise $599/mo. Stripe price IDs on file."** The CTO
string (`:24788-24793`) contains **patent filing dates and the non-provisional
deadline (May 21 2027)**.

A paying shop owner can read SAIRN's pricing tiers and IP calendar out of the
product they bought. Worth a decision.

### 4.2 The CTO advisor describes the wrong codebase.

`stonedesk.html:24788` states the stack as *"React 18 + TypeScript frontend,
Express backend, Drizzle ORM, PostgreSQL on Railway"* and `:24790` as *"each app
is a standalone HTML file... authenticated against Railway backend. All 21 apps
share one Railway PostgreSQL instance."*

Per `CLAUDE.md`, the real stack is vanilla JS single-file HTML on Vercel with
**Supabase**, and *"the old SAIRN1/Fabricor repo on Railway is an abandoned
duplicate codebase."* The advisor is describing Fabricor. It will give
confidently wrong architectural advice, and `:24792` compounds it with
"QuickBooks Online (UI built, OAuth pending)" — §3 GAP 6 shows no such UI exists.

---

## 5. What the honest competitive position is

**StoneDesk is not competing where it thinks it is.** Moraware, ActionFlow and
Stonify are *job-management* systems that do one workflow deeply — template →
draw → nest → schedule → install → machine. StoneDesk does **that workflow more
shallowly** (no machine output, no scanner, no barcode) and **the surrounding
business far more deeply** (compliance, workforce, reputation, risk, six real AI
tools).

Those are different products. The danger is pitching StoneDesk against Moraware
on Moraware's axis, where GAP 2, 3 and 4 are disqualifying on a demo floor —
a fabricator will ask "does it drive my saw" in the first ten minutes.

**Price context, since it is now verified rather than assumed.** A 5-user
Moraware shop running CounterGo + Systemize + Inventory pays roughly
**$1,350/month**. Stonify starts at **$500/mo**. iBlocky is **€299–399/mo flat**.
SlabWise is **$99–799/mo**. StoneDesk's own tiers (from `:24781`) are
**$199 / $299 / $599**. StoneDesk is priced at or below the market's floor while
carrying more surface area than anything above it — which is a positioning
problem in *both* directions and is worth a deliberate decision rather than a
default.

---

## 6. Premortem — run per `sairn-decision-gate` Framework 2

*"It is six months from now. A stone fabricator evaluated StoneDesk against
Moraware and chose Moraware. What decided it?"*

1. **"It doesn't talk to my saw."** GAP 2. Asked in the first ten minutes of
   every demo. There is no answer today.
2. **"How does my customer pick their slab?"** GAP 1. Five competitors in three
   countries have this; the honest answer is a PDF.
3. **"We scan every slab in."** GAP 3 + 4. The yard already runs on barcodes.
4. **"My bookkeeper needs QuickBooks."** GAP 6 — and the SAIRNbiz answer requires
   the prospect to change accounting systems during a software evaluation, which
   is the single hardest ask in the conversation.
5. **They opened Executive AI and read SAIRN's own pricing and patent dates.**
   §4.1. Not a competitive loss — a trust loss.

*"It is six months from now and someone checked a claim StoneDesk made. What did
they find false?"* — Most likely candidate: **"DXF export"** in the AI system
prompt (§3 GAP 2), because the product accepts DXF and a reader will assume the
arrow points both ways.

---

## 7. What a build pass would need to settle first — NOT decided here

Per the prioritisation principle (risk first, not scope first), and per the rule
that real feature/scope decisions are the correct thing to defer to fresh
judgment:

1. ~~**§4.1 and §4.2 are not competitive work and should not wait on this
   audit.**~~ **§4.1 CLOSED 2026-09-02** — treated as a live data-exposure bug,
   not a research-adjacent curiosity, and fixed ahead of everything else in this
   list. `showPanel()` now refuses `executive` for any role but owner/admin,
   `#sb-executive` carries `admin-only` (and `.sb-btn.admin-only` CSS now exists
   — it never did, which is why the button was visible to everyone),
   `applyExecRole()` checks the server-verified session role **before** the
   `localStorage` preference and clears a stale one, and `setExecRoleAndClose()`
   refuses unprivileged callers instead of writing the preference they would
   later be trusted on. 16 assertions in `tests/exec_role_gate.js`, driven
   against the real functions extracted from the real file; mutation-tested by
   disabling the gate, which fails 3 of them.
   **The residual is stated rather than closed: the advisor strings are still IN
   the HTML.** Gating the panel stops UI access; it does not stop View Source.
   Anyone served `stonedesk.html` can still read SAIRN's chart of accounts, the
   `$199/$299/$599` price book and the May 21 2027 patent deadline. **Removing
   or relocating those strings is the actual fix and is a separate decision**,
   because it changes what the Executive Suite does for SAIRN's own internal use.
   §4.2 (the CTO advisor describing Fabricor's Railway stack) is still open and
   is a factual correction to a prompt, not a feature decision.
2. **GAP 1 (customer portal) is the largest and is a genuine architecture
   decision** — a public, unauthenticated-or-tokenised surface on a platform
   whose entire auth model is per-employee session tokens. That is a
   `sairn-software-architect` question, not a panel build.
3. **GAP 2 (machine output) needs a scope call before any code**: saw/pick
   tickets as PDF is days; true DXF-out to a specific CNC is a per-machine
   integration with no generic answer.
4. **GAP 3 (barcode) is the cheapest real win on this list** — the field already
   exists and is empty. But "cheapest" is not "most valuable," and it should not
   be picked *because* it is easy.
5. **GAP 6 (QuickBooks) — ASKED AND ANSWERED 2026-09-02: hold, do not build.**
   The connector would contradict the SAIRNbiz routing already shipped in the AI
   prompt. It stays in §3 as a real, named competitive disadvantage that is being
   carried knowingly — see the status block on GAP 6. Do not quietly reopen it as
   an engineering task; it is a platform decision about SAIRNbiz.
6. **§5's pricing observation is a business decision and is only raised, not
   recommended.**

Nothing in this document should be read as approved work.

---

## 8. Sources

Primary (vendor's own site, fetched this pass): [Moraware](https://www.moraware.com/) ·
[Moraware pricing](https://www.moraware.com/pricing) ·
[ActionFlow solutions](https://www.actionflow.net/solutions/) ·
[Stonify](https://www.stonify.io/) ·
[Slabsmith](https://slabsmith.com/) ·
[Stone Profit Systems](https://www.stoneprofits.com/) ·
[SlabWise](https://slabwise.com/) ·
[iBlocky](https://iblocky.it/gestionale-per-marmisti) ·
[DDL / Digital Dry Layout](https://drylayout.com/)

Market survey (third party): [DDL's stone-industry software guide](https://drylayout.com/en/blog/software-natural-stone-industry/) ·
[Stone Finder on ERPedra](https://stonefinder.com.br/melhor-sistema-para-marmoraria-conheca-o-erpedra-com-ia-orcamentos-e-gestao-completa/) ·
[Sistrom](https://sistrom.com.br/ERP/site/) · [Marmu](https://www.marmu.com.br/) ·
[Gransoft](http://www.gransoft.net/)

**Fetches that failed, recorded rather than filled in:** `actionflow.com`
(returned a bare LiteSpeed directory listing — the live site is
`actionflow.net`); `marmoia.com.br` (HTTP 403); `stoneproject.app` (HTTP 403);
`easystoneshop.com` (TLS SNI error). Not fetched at all: StoneGrid StoneApp,
VISCO, SlabWare, EasyCo, O.C.V.M. Marmo, Conesoft, ERP Suite.
