# The four 2026-09-17 gap-status documents, re-verified at HEAD 2026-09-25 — three were wrong about their own headline within the hour

**Derived 2026-09-25 (Fourth) against the repository at HEAD.** A re-verification
of four **status** documents, using the method of the SAIRNvet/SAIRNlaw redo
(`b0f3db19`): *every claim about our own code re-derived against HEAD, because
that half is checkable exactly and is where a document would most easily drift.*

The four subjects:

| # | Status doc | Written | Covers |
|---|---|---|---|
| 5 | `docs/2026-09-17-trades-audit-rederived.md` | 09-17 **17:52** | the 08-21 plumbing / electrical / HVAC research |
| 6 | `docs/2026-09-17-sairnroofing-competitive-gap-rederived.md`, `docs/2026-09-17-sairndental-competitive-gap-rederived.md`, §1 of the senior/mechanical file | 09-17 **09:54**, **19:29**, **11:15** | the 08-26 roofing / dental / senior audit |
| 7 | `docs/2026-09-17-senior-mechanical-competitive-gap-rederived.md` §0, §2, §4 | 09-17 **11:15** | the 08-27 SAIRNmechanical research |
| 8 | `docs/2026-09-17-caller-level-gap-check-senior-stonedesk.md` §2 | 09-17 **13:45** | the 09-02 StoneDesk worldwide audit |

---

## 0. The finding that generalises, stated first

**Three of the four documents named a single open item or a headline defect, and
that item was closed within 30–70 minutes, or the next morning, by a commit that
CITED the document. None of the four was updated.**

| Doc | What it said was open | When it closed | By |
|---|---|---|---|
| roofing, 09:54 | *"One row: A5, accounting integration. Zero markers, no partial, no disclosure."* | 11:03 — **69 minutes** | `325e1294` `api/_lib/roofing-gl-export.js` |
| senior/mechanical, 11:15 | §0 headline: *"SAIRNmechanical claims an enforcement it never invokes"*; §4: *"the one action this pass recommends"* | 11:45 — **30 minutes** | `155e5b8f` `mechEligibility()` |
| dental, 19:29 | §0 headline: *"`dnt_rollup` is SAIRNmechanical's defect again"* | next morning 08:29 | `b179d967` the roll-up gets a reader |

The trades document (17:52) is the exception and its verdicts all hold.

**This is the same shape the 09-15 pass named one level down.** That document's
§2.2 finding was *"the fix is in the body, the false claim is in the heading"* —
a correction written into a file while both headings a reader hits first still
asserted the false state. Here the fix is in the CODE and the false claim is the
whole document, and it happened three times in one day. A status document exists
to answer *"is this still open"*; these answered it correctly and then went on
saying it after the answer changed, in the direction that makes a reader think
there is work to do when there is none.

**Nobody did anything wrong at the time.** Each document was accurate when
written and each closure was the document being USED — which is the best possible
outcome for an audit and is why these are not defect records. What is missing is
the step that costs a minute: **the build that closes a row edits the row.** The
open-work index has that convention and these files do not.

---

## 1. Item 5 — the trades document holds, and one evidence clause does not

Every verdict in `docs/2026-09-17-trades-audit-rederived.md` is still correct at
HEAD. Five marker cells moved; each move was hand-read and none changes a
verdict.

| Marker | Published | HEAD | Why it moved |
|---|---|---|---|
| `608` | 15 | 17 | the AIM Act work §3 records closing |
| `Manual J` | 4 | 17 | `MECH_MANUAL_J_SYS` / `MECH_MANUAL_J_NOTE`, the disclosure §3 records shipping |
| `permit` | 0 | 1 | **not a feature** — the single hit is inside the Manual J disclosure, *"not … as permit-ready"* |
| `inspection` | 2 | 3 | **not a feature** — a new comment describing the doc scanner |
| `export` | 12 | 13 | incidental |

**§1's Manual J cell is now false in its evidence and right in its verdict.** It
reads *"NOT BUILT, and the four hits are all AI system-prompt text"*. There are
seventeen hits and they are not all prompt text — `MECH_MANUAL_J_NOTE` renders on
screen at three `.mech-mj-note` sites and `MECH_MANUAL_J_SYS` is appended to four
prompts. §3 of the same document records that closure. **The table was never
updated, so §1 and §3 of one document disagree about the same subject** — the
09-15 finding again, inside a file written to record it.

**Structural claims, all confirmed at HEAD:** `EPA_LEAK_THRESHOLD_LB = 50` and
`EPA_THRESHOLD_CITATION = '40 CFR 82.157'` unchanged; `AIM_LEAK_THRESHOLD_LB =
15`, `AIM_THRESHOLD_CITATION = '40 CFR 84.106'`, `AIM_GWP_FLOOR = 53`,
`AIM_REPAIR_DAYS = 30`, `AIM_VERIFY_FOLLOWUP_DAYS = 10`, `aimScope()` and
`aimRepairClock()` all present; the three nullable columns
(`hfc_gwp_over_53`, `leak_detected_on`, `leak_repair_verified_on`) present in
`sql/mech_site_assets_schema.sql` with the *"NULL = nobody stated it. NEVER
default false"* comment; the board disclaimer *"This app does not decide whether
leak-repair rules apply"* present exactly once; the CSV button still calls
`mechNotLive('CSV export','exported')` at three sites.

**One line reference drifted.** §2.1 cites `api/sd-data.js:1349` as the single
non-test caller forwarding `payload.threshold_lb`. It is **:1782** at HEAD. The
claim is right and the address is not, which is why a line number is the weakest
form of evidence this platform writes down.

**And §2.1's finding now extends further than it could when written.** It says
*"Nothing in the product passes one"* — no caller overrides the 50 lb threshold,
so the board always shows 50. Re-checked at HEAD: `sairnmechanical.html` sends
**neither** `threshold_lb` **nor** `aim_threshold_lb`. The AIM work landed the
same day and inherited the same property, so **both** rules are now permanently
displayed at their compiled-in defaults, and the observation is about two
thresholds rather than one.

**`refrigerant × 29` is not reproducible in any scope tried** — 20 in
`sairnmechanical.html`, 30 across the html plus `api/_lib/mech-assets.js`. Every
other figure in the document reproduces exactly under whole-word case-insensitive
counting (20 of 21). Stated rather than fitted: see §5.

**Nothing in §3's still-open list has closed.** `leak.rate` × 0, `backflow` × 6
(all one credential `<option>`), `geothermal` × 0, `IGSHPA` × 0, `portab` × 0,
`F-Gas` × 0. The twelve `data-trade` chip values are unchanged and all still HVAC,
so §0's framing fact holds.

---

## 2. Item 7 — SAIRNmechanical's headline finding was closed 30 minutes after it was written

This is the largest correction in this pass, and the document says nothing about
it.

`docs/2026-09-17-senior-mechanical-competitive-gap-rederived.md` §0 is headed
*"SAIRNmechanical claims an enforcement it never invokes"*. Its evidence was that
the engine, endpoint, registry and tests all existed and **the caller did not**:

> *"Every `mechData(...)` call in `sairnmechanical.html` is `read` (×3) or
> `write` (×3). The string `eligibility` appears **once** in the whole app file"*

**At HEAD:**

| Claim | Then | Now |
|---|---|---|
| `mechData` verbs sent | read ×3, write ×3 | read ×3, write ×3, **`mechData('eligibility', 'mech_credentials', …)` ×1** |
| `eligibility` in `sairnmechanical.html` | 1 | **15** |
| the caller | **NONE** | `window.mechEligibility` at **:2308**, wired to a `Check eligibility` button at **:871** |

Closed by `155e5b8f` — *"the panel now computes the dispatch eligibility its own
subtitle claimed"* — at 11:45, thirty minutes after the document was committed at
11:15. The panel subtitle *"the record dispatch eligibility is computed from"* is
still there, and that is now **correct** rather than an overclaim: §4 offered
three resolutions and the product took the first (call it and show the answer)
rather than the third (correct the sentence).

**So §4, *"The one action this pass recommends"*, is discharged, and §0 is a
historical record rather than a live finding.** A reader arriving at this file
today is told SAIRNmechanical carries an unreachable capability plus a UI
overclaim. It does not.

**Every ABSENT verdict in §2 holds**, re-counted over a deliberately WIDE scope —
24 tracked SAIRNmechanical-related source files rather than the app file alone,
because a zero over a wider scope implies a zero over every narrower one and the
original scope is not recorded:

`subcontractor` 0 · `COI` 0 · `WIP` 0 · `retainage` 0 · `job cost` 0 ·
`inspection interval` 0 · `apprentice` 0 · `OJT` 0 · `RTI` 0 · `calibrat*` 0 ·
`submission` 0. `permit` is 1 and it is the Manual J disclosure text, so G8 is
still Absent.

G11 (refrigerant ledger, *substantially built*) and G13 (warranty captured, no
registration clock) both still hold; `api/_lib/subcontractor-compliance.js` and
`api/_lib/wip-accounting.js` both still exist platform-side and still are not
wired here, so G2 and G5 are unchanged.

---

## 3. Item 6 — roofing's last open row closed in 69 minutes, dental's headline the next morning

### 3.1 SAIRNroofing A5 is CLOSED, not open

§3 of the roofing document is titled *"What is genuinely still open"* and names
exactly one row:

> *"**One row: A5, accounting integration.** Zero markers, no partial, no
> disclosure."*

**At HEAD:** `api/_lib/roofing-gl-export.js` and its `.test.js` exist, wired
through `api/_resources/sairnroofing.js` and `sairnroofing.html`. `QuickBooks` ×
14, `Intuit` × 4, `OAuth` × 3 across the roofing scope. Added by `325e1294` at
11:03 — sixty-nine minutes after the document was committed at 09:54, and the
module's own header quotes that document's re-derivation as its justification.

**Read what shipped before recording A5 as simply closed.** It is a
**general-ledger export, explicitly not a QuickBooks connection**, and the module
says so at length: *"A QuickBooks Online INTEGRATION means an Intuit developer
account, an OAuth 2.0 authorisation code flow, a refresh-token lifecycle, and a
per-app review… a screen headed 'QuickBooks' with a file download behind it would
be the same claim-without-substance this codebase keeps finding."* So A5 moved
from **Absent with no disclosure** to **the buildable half built, with the
unbuildable half disclosed on screen** — the same posture as B6's *"This is not
an EDI connection"*. That is the right resolution and it is not the integration
the audit row described. **Zero roofing rows are now open; twelve of twelve are
closed, refused, or built-and-disclosed.**

### 3.2 The two refused roofing rows are still refused, and their markers moved for the right reason

B3 certified payroll now returns `certified payroll` × 4 and `prevailing` × 3,
against a published zero. **Every hit is the refusal being written down** —
`sql/sairnroofing_draws_schema.sql`: *"Certified payroll is NOT here and is not
coming as a side effect: it needs Davis-Bacon and state prevailing-wage…"*, and
the same sentence in the registry and on screen. B6's `trading partner` × 2 is
the same shape. A marker moving off zero because a refusal was documented is the
one case where the count rises and the verdict gets stronger.

### 3.3 SAIRNdental — the headline finding closed the next morning

The dental document's §0 is headed *"`dnt_rollup` is SAIRNmechanical's defect
again, with the claim in the audit trail instead of the UI"* — a capability with
no reader.

**At HEAD it has a reader.** `sairndental.html:2492` runs
`await sdnData('read','dnt_rollup',{})` with a refusal path at :2498, and
`tests/sairndental_rollup_panel.js` exists. Closed by `b179d967` at 08:29 the
following morning — *"the roll-up gets a reader, a checker that finds the next
one, and money that refuses rather than rounds"*. `dnt_rollup` × 12 across the
dental scope, `rollup` × 99.

### 3.4 SAIRNsenior — all twelve rows hold

Every named artefact still exists: `panel-authorizations`, `panel-hiring`,
`panel-training`, `panel-referrals`, `panel-branches`, `panel-franchise`,
`panel-contracts`, and the seven `sql/sairnsenior_*_schema.sql` files and eight
`api/_lib/sairnsenior-*.test.js` suites named in the table.

**A4 is still open and still vendor-gated:** `837` × 0 and `clearinghouse` × 0
over the wide 50-file senior scope, so the zero is not an artefact of a narrow
one.

**A1's `transmit × 0` is now 2, and both hits are NEGATIONS** —
`api/_lib/sen-evv-readiness.js:11` *"This REPORTS. It does not transmit, does not
persist"* and `sql/sairnsenior_settings_schema.sql:28` *"…transmit anything to
any aggregator"*. The half-closed verdict is unchanged and the marker now
documents the missing half rather than contradicting it.

---

## 4. Item 8 — StoneDesk holds on every verdict, and one evidence cell measures the word "design"

**All eight gap rows in §2 still hold at HEAD.** GAP 4 is still zero on both
markers (`slab scanner` × 0, `LaserProducts` × 0; both `Slabsmith` hits still
prose). GAP 6 is still held and — the part worth re-checking, because it is a
claim about not claiming — the app still does not assert it:
`class="qbo-status"` appears **zero** times, `sdIntegQuickAdd('QuickBooks
Desktop', …)` is still a local tracker row, **"Mark Reviewed"** is still the
button label, and `api/_lib/exec-context.js` still carries both the real chart of
accounts (1010, 6020) and the instruction *"SAIRN does NOT connect to
QuickBooks"*.

**Under the document's own counting method, fourteen of its sixteen marker
figures are byte-for-byte unchanged at HEAD and only two moved — `esign` 55 → 56
and `signature` 54 → 55, both by one.** This is the least-drifted of the four
documents, which is the opposite of what an eight-day-old status file over the
platform's oldest audit would be expected to be.

**§2.2's flagged-and-not-acted note is still not acted on, correctly.** It raised
that roofing's GL-export posture would also close GAP 6 *as an export*, and said
it should not be built without a decision. At HEAD `stonedesk.html` has
`general ledger` × 0, `IIF` × 0, `gl_export` × 0. The decision has not been taken
and nothing was built on the assumption that it had.

### 4.1 `esign × 55` is fifty-five occurrences of the word "design"

GAP 5 (e-signature + deposit, **BUILT**) offers three markers as evidence:
`esign` × 55, `signature` × 54, `deposit` × 104.

**Measured at HEAD in `stonedesk.html`:**

```
esign   (substring)                      56
design  (substring)                      56
esign   NOT preceded by "d"               0
```

**Zero of those hits have ever been e-signature.** `esign` is a substring of
`design`, the figure reproduces exactly as a substring count at the document's own
commit, and a substring count of `esign` on this file can only ever return
`design`. The cell is noise presented as evidence.

**The verdict survives and that is why this is a method finding rather than a
status correction.** `signature` × 54 (50 whole-word) and `deposit` × 104 (69
whole-word) are real, and GAP 5 was independently corrected to BUILT on 09-15 by
a different pass. But one third of the evidence offered for a BUILT verdict
measures an unrelated English word, and nothing caught it.

**This is PR 1.2 on a different surface, and the same document family had already
recorded it twice.** The roofing pass's §2.2 records its own marker set producing
a **false NEGATIVE** on a hyphen. `tools/sairn_clickthrough_driver.js`'s lesson 3
records `Entry (` reading as a call because a regex could not see quotes. Both
are the same class: a pattern matching text that is not the thing. **This is the
first false POSITIVE of the three, and a false positive is worse**, because a
false negative sends somebody to look and a false positive tells them not to.

---

## 5. Why this pass does NOT publish a re-counted marker table

**Because the published figures cannot be re-derived, and fitting a method until
they match would be measuring the answer.**

Every marker figure in all four documents is written `` `marker` × N `` with
**no method and no file scope recorded**. Six candidate counting methods were run
against each document at its own commit:

* the **trades** document reproduces 20 of 21 figures under **whole-word,
  case-insensitive** counting of `sairnmechanical.html` alone;
* the **StoneDesk** document reproduces 14 of 16 under **substring** counting of
  `stonedesk.html` — which is what produced §4.1. **The other two are whole-word,
  in the same table**: `DXF` × 38 is 38 whole-word and **115** as a substring,
  `QBO` × 9 is 9 whole-word and **17** as a substring. So one table mixes two
  counting rules with nothing marking which cell uses which;
* the **senior/mechanical** document reproduces only 23 of 39 under the best
  single method, and the failures are not method failures: `applicant` × 46 is 12
  in `sairnsenior.html` and `appeal` × 114 is 60, so those rows were counted over
  a wider file set than the app, and **which set is not written down.**

Two documents in one family therefore use two different counting rules, one of
them mixes both rules inside a single table, and a third uses a per-row scope
nobody recorded. That makes the numbers **incomparable between documents and
unverifiable within them** — which is the platform's own rule about a fact needing
a single source, applied to a figure instead of a sentence.

**So the ZERO markers were re-counted and nothing else was.** A zero is the one
figure that survives not knowing the scope: counted over a deliberately WIDE
scope (every tracked `.html`/`.js`/`.sql`/`.py` whose path names the app — 24
files for mechanical, 50 for senior, 82 for roofing, 95 for dental, 119 for
StoneDesk), a zero implies a zero in every narrower scope the author might have
used. Every non-zero claim in this file is instead a named artefact, a wiring
check, or a verbatim quotation.

**The recommendation is one line per figure:** a marker cell should carry its
scope — `` `appeal` × 114 (sairnsenior.html + sql/ + tests/, substring) `` — or it
is a number nobody can check, including its author a week later.

---

## 6. What is genuinely open after this pass

| App | Item | Why it is open |
|---|---|---|
| StoneDesk | GAP 4 — slab-scanner integration | Vendor-gated (Slabsmith, LaserProducts). Zero markers over a 119-file scope |
| StoneDesk | GAP 6 — QuickBooks | **Held by decision.** The export option raised on 09-17 is still un-decided and still un-built |
| SAIRNsenior | A4 — 837 / clearinghouse | Needs a clearinghouse relationship. Zero over a 50-file scope |
| SAIRNsenior | A1 transmission half, A2 telephony half | Each needs a commercial agreement; A1 also needs the open credential-storage decision |
| SAIRNmechanical | G2, G5, G8, G15, G17, G19, G20 | Absent, confirmed zero over a 24-file scope. G2 and G5 have a platform module that is not wired |
| SAIRNmechanical | Leak RATE, backflow testing flow, geothermal, permits, data portability | Unchanged from 09-17 |
| SAIRNroofing | **none** | A5 closed 09-17. B3 and B6 are refused on business-development grounds, not engineering |
| SAIRNdental | see its own §2 | `dnt_rollup` closed 09-18; the rest of that document was not re-verified here beyond its headline |

**Nothing found in this pass is buildable in-house and un-gated.**

---

## 7. Limits

* **Three documents' headline corrections are the finding; their row-by-row
  tables were re-verified structurally, not exhaustively.** Named files,
  functions, panel ids, schemas, tests, verbatim quotations and every ZERO
  marker were checked. A non-zero marker cell was re-checked only where a
  verdict turned on it.
* **The dental document's §1 tables were not re-verified** beyond §0's headline.
  Its own §2 open list is carried forward unread. That is a gap in this pass, not
  a claim that those rows hold.
* **No market research was re-run**, in any of the four. The audits' market
  halves are the reference and re-verifying them would duplicate them.
* **No regulatory date was re-verified here.** The trades document's §2 re-verified
  two against primary sources on 09-17; that work is inherited, not repeated, and
  eight days is short for a commencement date to move.
* **No live check.** Every verdict is against the repository at HEAD, not the
  deployed apps.
* **No code was written and no app file was touched by this pass.**
* **Coverage is not depth.** The roofing document's own warning applies to this
  one: it was checked that each capability exists, is wired, and names the gap it
  answers — never that it would beat the competitor the audit named.
