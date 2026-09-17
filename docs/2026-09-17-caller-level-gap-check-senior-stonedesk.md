# Caller-level gap check — SAIRNsenior and StoneDesk, 2026-09-17

**Derived 2026-09-17 (CC) against the code at HEAD.** A **status** document.

This is the check that caught SAIRNmechanical, applied to the two apps that had
not had it: **does every server capability have a client caller, and does every
UI claim have code behind it.** Marker counts and a panel census cannot see
either — SAIRNmechanical had a wired panel, a registered action, an endpoint and
ten engine test arms, and the app never sent the action while its own subtitle
said it did.

**This closes a gap in my own earlier pass.** `docs/2026-09-17-senior-mechanical-competitive-gap-rederived.md`
checked SAIRNsenior with markers, panels, schemas and tests, and reported ten of
twelve rows closed. It did **not** check callers. That pass is not wrong, but it
was not sufficient to catch the one thing that turned out to matter next door.

---

## 1. SAIRNsenior — passes, and the negative is worth stating

| Check | Result |
|---|---|
| Registered `extraActions` | one: `sen_visits: ['readiness']` |
| Is it sent by the app? | **Yes** — `senData('readiness','sen_visits',{},true)` in `renderReadinessView()` |
| Is it reachable by a user? | **Yes** — an `EVV Readiness` tab, role-gated to schedulers, with `vsShowTab('readiness')` |
| Is the gate real or cosmetic? | **Real, and the app says so**: *"Cosmetic only — the server gate in sd-data.js's 'readiness' branch is the real boundary"*. The tab is hidden for a caregiver **and** re-checked on every render so a role that lost access mid-session cannot land back on it |
| Panels with no render hook in `nav()` | one, `panel-ai`, which is the chat panel and needs none |
| 18 panels / 18 nav targets | identical sets |

**No unreachable capability and no UI claim without code behind it.** That is a
verified negative rather than an absence of looking, and it is the useful half
of running the check: the same method that found a real defect in one app found
none here.

### 1.1 One platform-level fact, found while sweeping and not a SAIRNsenior gap

**`api/_lib/biometric-consent.js` has no consumer anywhere on the platform.**
The only file that requires it is its own test. `sd-data.js` does not; no
`api/*.js` does; `biometric` appears **0 times** in `sairnsenior.html`.

**This is not the SAIRNmechanical shape and should not be filed as one.** The
difference is the claim: SAIRNmechanical's panel *told a dispatcher* that
eligibility was computed. Nothing anywhere claims SAIRN collects biometric
identifiers. StoneDesk's five `biometric` hits are a PII-redaction pattern and
WebAuthn copy that says the opposite — *"Not facial recognition, not biometric
data collection … deliberately avoids BIPA-class biometric-privacy exposure"*.

So it is **built-ahead groundwork**, which its own header states it is: *"Built
once, cross-app … every future biometric feature inherits the legal machinery
instead of doing its own scramble."* Recorded here only so that its existence is
not later read as evidence that the platform HANDLES biometric consent today.
Nothing does, because nothing collects one.

---

## 2. StoneDesk — the 2026-09-02 audit re-derived, and it holds up

Eight gap rows. The 09-02 status file records six BUILT, one OPEN, one HELD OPEN
on purpose, with GAP 5 corrected to BUILT on 2026-09-15.

| # | 09-02 verdict | At HEAD, 2026-09-17 | Evidence |
|---|---|---|---|
| **1** customer-facing portal | BUILT | **holds** | `public catalog` × 17, `publiccatalog` × 8, `panel-publiccatalog` with a role gate in `showPanel` |
| **2** machine output | BUILT — DXF only, G-code refused | **holds, and the refusal is on screen** | `DXF` × 38, `nestBuildDXF`. All four `G-code` hits are the stated refusal: *"DXF IS GEOMETRY. G-CODE IS A MACHINE PROGRAM … no feed rate, no spindle speed, no tool number, no blade thickness"* |
| **3** barcode / scanner | BUILT | **holds** | `barcode` × 29 |
| **4** slab-scanner integration | OPEN | **STILL OPEN, vendor-gated** | `slab scanner` × 0, `LaserProducts` × 0. Both `Slabsmith` hits are prose — a competitor list and an AI expertise string |
| **5** e-signature + deposit | BUILT (corrected 09-15) | **holds** | `esign` × 55, `signature` × 54, `deposit` × 104 |
| **6** QuickBooks | HELD OPEN on purpose | **HELD, and the app does not claim otherwise — see §2.1** | Michael's call, 2026-09-02 |
| **7** multi-location | BUILT — attribution, not access partitioning | **holds** | `location_id` × 12 |
| **8** remnant publishing | BUILT | **holds** | `remnant` × 195, `publish` × 72 |

**Caller check: clean.** `soft_delete` is registered on 22 resources and the app
sends it (`sdData('soft_delete', …)`); `slabs: reserve` is sent. Every one of
**64 panels** has a sidebar button; the seven sidebar ids without a panel are UI
chrome (`collapse-btn`, `navtog`, `scrim`, `search`…), not nav targets.

### 2.1 GAP 6 is the row worth reading carefully, because it LOOKS like the mechanical defect and is not

`QuickBooks` × 9 and `QBO` × 9 in `stonedesk.html`, against a gap that is
deliberately not built. Every one was hand-read:

* **`.qbo-status` / `.qbo-dot` are dead CSS.** `class="qbo-status"` appears
  **zero** times. The integration itself was deleted on 2026-07-29 and the
  comment recording it is precise about why: *"no panel/nav entry ever existed …
  no caller anywhere in the file besides itself."* Leftover styling for removed
  code, claiming nothing.
* **The QuickBooks tile is a TRACKER, not a connection.**
  `sdIntegQuickAdd('QuickBooks Desktop','Accounting')` adds a local row with
  status `"Pending Setup"` and toasts *"added — complete setup to activate"*.
  The panel calls itself *"Track which outside apps you use and their setup
  status"*.
* **And the field that could have been a fabricated status is not one.** The
  stored property is `sync`, but every user-facing string says **reviewed**:
  the row renders *"Last reviewed:"* and the button reads **"Mark Reviewed"**.
  A button labelled *Sync* that only stamps a timestamp would be exactly the
  fabricated-status defect; somebody already named it correctly.
* **The CFO advisor greeting is TRUE, and I checked before believing it.**
  *"I have your Chart of Accounts loaded, payroll tax rates current for 2026"* —
  `api/_lib/exec-context.js:99` carries a real SAIRN chart with literal account
  codes (1010 Cash-Checking, 1100 AR, 4010 Service, 6020 Payroll Taxes…) and
  :100 carries the 2026 rates. It is SAIRN's own internal chart, not a
  customer's, and the same file at :116 instructs the model: *"SAIRN does NOT
  connect to QuickBooks, Gusto, Xero … If asked about pulling data from an
  accounting package, say it is not built rather than describing it as pending
  or on the roadmap."* The CTO greeting says it outright on screen.

**Three places on this platform once asserted a QuickBooks integration that did
not exist** — the CTO greeting, `exec-context.js`, and a SAIRNscape pricing
tier — and all three were corrected on 2026-09-02, with the verification
recorded in the file: `/api/accounting` returned 404, no connection table among
258 in the snapshot, no `QB_*` env var anywhere. **That correction has held.**

### 2.2 The cross-app note, flagged and NOT acted on

SAIRNroofing's A5 shipped today as a **general-ledger export** — explicitly not
an integration, with an on-screen banner saying so. That posture would also
close StoneDesk's GAP 6 as an *export* without touching the thing Michael held
open, which was an *integration*.

**It was not built, and should not be without a decision.** The 09-02 row says
reopening GAP 6 is *"a SAIRNbiz platform decision, not a StoneDesk feature
request"*, and an export that lands in the same panel a held decision points at
is not obviously outside that call. Raised here so the option is visible.

---

## 3. What is genuinely open after this pass

| App | Item | Why it is open |
|---|---|---|
| StoneDesk | GAP 4 — slab-scanner integration | Vendor-gated (Slabsmith, LaserProducts). Zero markers |
| StoneDesk | GAP 6 — QuickBooks | **Held by decision**, not by engineering. See §2.2 |
| SAIRNsenior | A4 — 837 / clearinghouse | Needs a clearinghouse relationship |
| SAIRNsenior | A1 transmission half, A2 telephony half | Each needs a commercial agreement; A1 also needs an open credential-storage decision |

**Nothing found in this pass is buildable in-house and un-gated.**

## 4. Limits

* **Caller checks are textual.** "The app sends this action" is a search for the
  action literal plus a read of the call site. A caller behind a feature flag
  that never evaluates true would pass.
* **No live check.** Against the repository at HEAD, not the deployed apps.
* **Marker counts are a floor.** The roofing pass's §2.2 stands as the warning:
  one hyphen produced a false negative there.
* **SAIRNdental was not touched** — fourth's claim on that app is still active.
* **No code was written and no app file was touched by this pass.**
