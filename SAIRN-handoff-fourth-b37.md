# HANDOFF — fourth / ted, batch b37, 2026-10-19

**READ THIS FILE ONLY.** It is the whole state.

**Written BEFORE the report, at a point where nothing is half-finished.** All
committed work is on `origin/main`; the only uncommitted files at this moment
are this handoff, the batch manifest and the two deliverables, all complete.

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you mean
to quote, including out of this file.**

**FOUR THINGS TO READ FIRST:**

1. **ITEMS 1 AND 2 ARE CLAIM-BLOCKED AND FLAGGED BACK, NOT SKIPPED — AND I WAS
   WRONG ABOUT THE BLOCK BEFORE I WAS RIGHT.** I told Michael it was a
   substring false positive, re-checked, and **corrected myself in the same
   session: the block is substantively right.** Both stonedesk items are the
   client half of hank's active b22 `api/bridge.js` work. §3.
2. **THE TIER REVIEW'S PREMISE DID NOT HOLD, AND THE RESULT INVERTS IT.** The
   two rows whose grounds are genuinely mis-attributed are **not** the two that
   were named. §5.
3. **THE SAIRNLAW AUDIT'S HEADLINE IS A COMPLIANCE GAP IN SHIPPED CODE, NOT A
   MARKET GAP** — and it was only findable by reading regulators. §6.
4. **THE SAIRNLAW AUDIT CORRECTED ITS OWN FIRST DRAFT** rather than leaving it
   standing, and found two staleness defects on the way. §6.2.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\ea7d41f7-de8c-4e21-afd3-fc6d47e335b9.jsonl`
(a NEW session — b33–b36 were `7114877e-…`, this is not a continuation of it)

**Working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\ea7d41f7-de8c-4e21-afd3-fc6d47e335b9\scratchpad\b37\`
— `a11y_b37.py` (the §4 edits, each with a counted assertion),
`count_unlabelled.py` (the HTML-parse counter, re-runnable),
`fill_manifest.py`, `httpd.log`.

**NO SQL WAS PRODUCED THIS BATCH**, so nothing was written to `sql/`.

---

## 1. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| `HEAD` vs `origin/main` | **0 ahead, 0 behind — PUSHED AND LANDED** | `git rev-list --left-right --count origin/main...HEAD` |
| the b37 commits | **`a52311fa`** (a11y) and **`4938f432`** (docs) | `git log --oneline -3` |
| confirmed on origin | **both pass `merge-base --is-ancestor`** | per commit |
| **files touched** | **exactly 3** — `sairndental.html`, `docs/2026-10-19-fourth-b37-tier-a-review.md`, `docs/cloud-research/sairnlaw-worldwide-competitive-gap-audit-2026-10-19.md` | `git show --name-only --format="" <sha>` |
| **forbidden paths** | **0** — no `api/sd-data.js`, no `tools/`, no `.githooks`, no `settings.json`, no `sql/`, no `.claude/claims/` beyond the claim tool's own commits | same command piped to `grep -cE` |
| uncommitted | this handoff, the manifest, the two deliverables — **all complete** | `git status --porcelain` |
| `git stash` | **0** | `git stash list` |
| **force push** | **none. No `--force`, no `--force-with-lease`.** Three attempts; the first two were rejected by the remote moving (five sessions pushing) and resolved with `git pull --rebase` both times | — |
| overrides | **none, any form.** No `SAIRN_GATE_EXEMPT`, no `SAIRN_SKIP`, no `SAIRN_SEED_GATE` | — |
| auditor clones | **not entered** | — |
| b37 manifest | **4 done, 2 blocked**, validates | `batch_manifest.py --check --agent fourth --batch b37` |

**The forbidden-path check is scoped to MY OWN two commits, not a range.** b35
recorded why: a range answers *"did anybody touch this in this window"*, which
is a different question and answered **1** for somebody else's commit.

---

## 2. CLAIMS HELD

**`fourth` holds ONE claim**, declaring `sairndental.html`,
`docs/cloud-research/`, the notes doc, and the three deliverables — and
declaring **two negatives on purpose**:

* `NOT-stonedesk-html-BLOCKED-pending-go-ahead`
* `NOT-docs-tier-a-reviews-json-cc-holds-it`

**THE CLAIM IS RELEASED IN FULL AT THE END OF THIS BATCH.** Nothing is
mid-edit: every file in it is either committed and landed or was never
modified.

**Other active claims at the stop, none touched:** cc on `cc`
(`tools/criticality_tier_check.py`, `docs/tier-a-reviews.json`), cody on
`platform` (`api/sd-data.js`), hank on `hank` (`api/bridge.js`,
`api/claude.js`), hover2 on `hover2`.

**I did NOT write to `docs/tier-a-reviews.json`** — cc holds it. The six item-4
verdicts are in `docs/2026-10-19-fourth-b37-tier-a-review.md` in the shape that
append needs, which is a routed obligation and not a done one.

---

## 3. ITEMS 1 AND 2 — BLOCKED, FLAGGED, AND THE FLAG WAS CORRECTED

### 3.1 What happened, in order, including the part I got wrong

    python tools/sairn_claim.py check fourth "<the b37 task string>"
    # -> BLOCKED -- another session already claimed overlapping work
    #    session: hank   blocked by: same app: stonedesk

**I flagged it to Michael as a substring false positive** — hank's own FILES
token is literally `NOT-stonedesk-html-claimed`, a negative declaration that
the file is *un*claimed, and the matcher had hit the word inside it. That
reading of the *mechanism* was right.

**The conclusion drawn from it was wrong, and I corrected it in the same
session rather than letting it stand.** Reading the two call sites read-only
showed that items 1 and 2 **are** hank's b22 work seen from the client, so the
block was substantively correct by accident. **Worth knowing before anybody
loosens that matcher on the strength of the `NOT-` token.**

### 3.2 Item 1 — the Field Map catch arm. READ-ONLY EVIDENCE, nothing edited

* `stonedesk.html:12814` POSTs `FM_API + '?action=maps-static'`, and
  `FM_API = 'https://sairn.vercel.app/api/bridge'` (`:12547`).
* **That action does not exist, and two files already say so:**
  `api/bridge.js:228` and hank's own
  `api/b21-bridge-unknown-action.test.js:15`, both naming
  *"stonedesk.html:12814  ?action=maps-static  -- no such action"*.
* The catch arm at **`:12818`** renders *"Map unavailable -- check
  GOOGLE_MAPS_API_KEY is set."* **`grep -rn GOOGLE_MAPS_API_KEY api/` returns
  exactly one site — `api/_lib/routes.js:304` — which this request never
  reaches.**
* **This is the identical defect b34 already fixed on the sibling call**, whose
  comment at `:12933` says the old message *"told the reader to go and check a
  Maps API key the request never reached."*

**EXACT NEXT STEP:** replace `:12818`'s message with the real cause — the
request did not reach anything that reads a Maps key — and live-verify the
rendered string. **The honest message depends on what hank's absent-action
refusal returns**, so doing this before that lands would hard-code a cause
that is about to change.

### 3.3 Item 2 — `stonedesk.html:7795`. READ-ONLY, nothing edited

The call POSTs to the same endpoint with **no `action` field at all**:

    {app_id:'stonedesk', event_type:'pos_sale', source_device:'mobile',
     timestamp:…, payload:inv}

`grep -n "action ===" api/bridge.js` returns **one** line, `:217`, which tests
`proxy_get` only. So this falls through dispatch exactly like item 1. The
`.catch` is annotated *"bridge sync optional -- sale is already saved
locally"*, which is true and is also why nobody noticed.

**EXACT NEXT STEP:** Michael's instruction, verbatim, is *"send a real action
or delete the dead call."* **Recommend DELETE**, because the only candidate
action is `push`, which `api/bridge.js` itself documents as requiring no
Authorization at all and therefore *"NOT defensible for personal or financial
data"* — and an invoice with a signature is exactly that. **That is a judgment
to confirm, not a conclusion to act on without hank.**

### 3.4 Both are routed, not abandoned

`python tools/sairn_status.py` carries the full routing note to hank with
every line number above. **Neither item was edited. `stonedesk.html` appears in
0 of my commits.**

---

## 4. ITEM 3 — SAIRNDENTAL A11Y: THE b36 REMAINDER, CLOSED AND DRIVEN

**The concepts were stated before the code, as instructed.**

* **Trap** — one document-level mechanism with zero per-modal code: a
  `MutationObserver` on each `.modal`'s `class` records `document.activeElement`
  as the return target when the modal gains `.on` and restores it when `.on` is
  removed, while a single `keydown` handler cycles Tab inside whichever
  `.modal.on` is open, **recomputing the focusable list at keypress time rather
  than caching first/last**.
* **Announcement** — `nav()` writes the newly-shown panel's **own visible
  `.ptitle` text** into one `aria-live="polite"` region, so the spoken name is
  derived from the heading the sighted user sees and cannot drift as panels are
  added.

**b36's stated reason for not building the trap was that it "needs per-modal
first/last bookkeeping". It does not — if the list is recomputed at keypress
time.** That is also the only version that stays correct for the modals here
whose controls appear while they are open.

| | fix | measured |
|---|---|---|
| E | 3 labels | unlabelled **3 → 0** of 155 controls, by HTML parse before/after **and** recounted in the live DOM |
| F/G | one `.sronly` live region | `position/width/clip-path` confirmed `absolute / 1px / inset(50%)` in the browser |
| H | panel-change announcement | **23 of 23** panels announce their own `.ptitle` |
| I | focus trap + return focus | **7 of 7** modals full pass |

**DRIVEN WITH REAL KEY PRESSES, NOT SYNTHETIC EVENTS:** 20 × `Tab` and 20 ×
`shift+Tab` inside a 13-focusable modal both stayed inside; a real `Escape`
closed it and returned focus to `sb-dashboard`.

**NEGATIVE CONTROL, and it is the arm that makes the rest mean anything:** with
no modal open, 6 real `Tab` presses visited **6 distinct** elements and none
inside a modal. **Without it, a trap that fired unconditionally would have
passed every assertion above.**

**Two things that would have shipped wrong without the counted assertions:**

1. The three named inputs needed **three different fixes**, not one. `#gkey`
   has no visible label to point at and `#icap-file` is `display:none` so a
   `<label for>` would be unreachable — both take `aria-label`. Only
   `#tp-item-planned` gets a real programmatic association, and it is the one
   the b36 note described correctly.
2. The live region had to go **outside `#app`**. `#app` has `on` toggled on
   sign-out, and a live region inside a subtree that gets hidden stops
   announcing.

**Gates:** `checkblocks` **6/0**; `wcag_contrast_check --gate` **0 findings**;
373 ids / 373 unique / **0 duplicates** by parse; `sairn_strict_args_check`
clean. Only console errors are two `Failed to fetch` from `dntAuth`, which this
clone has no backend for.

**STILL NOT PROVEN, unchanged from b36: NO SCREEN READER WAS RUN.** NVDA, JAWS
and VoiceOver were not used. Asserting on `textContent` and
`document.activeElement` is a mechanical DOM check and a real screen-reader
pass is a different and stronger claim.

---

## 5. ITEM 4 — SIX TIER A ROWS, AND THE PREMISE INVERTED

Full detail: **`docs/2026-10-19-fourth-b37-tier-a-review.md`**.

| resource | tier (I/C) | verdict |
|---|---|---|
| `invoices` | A / B | **CONFIRMED** |
| `law_trusttx` | A / A | **CONFIRMED**, grounds UNDERSTATED |
| `leg_cremations` | A / A | **CONFIRMED on tier, GROUNDS WRONG** |
| `employees` | A / A | **CONFIRMED on tier, GROUNDS WRONG** |
| `rf_claims` | A / B | **CONFIRMED**; the declared defect is FIXED |
| `rf_jobs` | A / B | **CONFIRMED**; the declared shape is STILL PRESENT, inert |

**6 confirmed, 0 wrong tier, 0 unreadable.**

**THE PREMISE DID NOT HOLD.** The instruction named `rf_claims` and `rf_jobs` as
*"the 2 declared mis-attributions."* The declaration exists — in
`docs/defect-density-register.json` — and it is about **acting-employee
attribution on the write**, not about tier.
`grep -n "mis-attribut\|misattribut" docs/CRITICALITY-TIERS.md` returns
**nothing**, and both rows are properly registered.

**AND THE TWO ROWS WHOSE GROUNDS ARE GENUINELY MIS-ATTRIBUTED ARE THE TWO THAT
WERE NOT NAMED:**

* **`leg_cremations`** — the confidentiality-A grounds name *"a deceased
  person's identity, cause or circumstances, or the government identifiers
  attached to them"*. **None of the 13 fields carries any of them.** The row
  holds `case_id`, a reference, and `authorization_on_file` as a **boolean**,
  not the authorisation. The tier stands as an **A-by-chain** argument through
  `case_id` plus the free-text `disposition_details`, and the register should
  say so the way the `rf_jobs` row does.
* **`employees`** — the register quotes the 13-field `saveEmp()` shape as *"the
  stored `data` blob"*. **The stored blob is NINE fields** from `syncEmps()`
  (`sairnbiz.html:5072`). **Emergency contact and notes are cited as grounds
  and are not on the row.** C-A still holds on `hourly_rate` alone.

**ONE CHAIN THAT LOOKS BROKEN AND IS NOT, checked because both ends alone are
indistinguishable from a break:** `saveEmp()` writes `rate`, StoneDesk reads
`hourly_rate`. On those two lines the average would be `$0.00` for every
roster. It works because `syncEmps()` renames on the way out. **And the
integrity-A citation `stonedesk.html:43148` holds exactly, unmoved.**

**`rf_jobs` is the one finding worth routing:** both projections put the blob
**last** (`:9190` read, `:9375` write response) where `rf_claims`' read puts the
real column last. **It is not an access-control bypass** — the privacy filter at
`:9188` reads the real column before the overlay — and it is inert **only**
because `storedBlob`'s strip list covers all four keys. **Measured for a
historical window: there is none.** `assigned_employee_id` has been stripped
since `2c349af8`; `location_id` was stripped in `68668ece`, the same commit that
introduced it. **Still worth fixing**, because the strip list and the projection
order are one point of failure in two directions at once, on the row whose A
tier exists *because* branch attribution decides an invoice's legal entity.

**NOT re-reported as new:** the `employees` `NOT A RESOURCE` finding is cc's
known tool defect — `tools/criticality_tier_check.py:236` skips `shared.js` by
name. **Measured: that one skip accounts for 7 of 14 `PROBLEMS` plus the `GONE`
line = 8, matching cc's b35 figure exactly.**

---

## 6. ITEM 5 — SAIRNLAW, AUDITED AGAINST REGULATORS

Full detail:
**`docs/cloud-research/sairnlaw-worldwide-competitive-gap-audit-2026-10-19.md`**.

**The instruction was explicit about what b36 got wrong — *"Pull primary
regulation sources this time, not vendor pages"* — and it was followed
mechanically: every search was DOMAIN-RESTRICTED at query time, not filtered
afterwards.** Eight regulator/legislature sources across six jurisdictions plus
the standard-setter. **Zero vendor pages, zero analyst reports.**

### 6.1 The headline is a compliance gap in SHIPPED CODE

    grep -n "law_trust_reconcile" api/sd-data.js
    # -> :18747   ONE action, `read`. No write branch.
    grep -n "trust_reconcile" sql/*.sql
    # -> nothing. No table.

**SAIRNlaw has a genuinely good three-way IOLTA reconciliation — server-side,
integer-cents, four-outcome, refuses a boolean — and it is computed and thrown
away.** SRA Accounts Rules **r.8.3** requires the record be *signed off by the
COFA or a manager*; LSO **By-Law 9** requires it created by the **25th**,
signed, and retained **10 years plus the current year**; NY **22 NYCRR 1200
r.1.15** puts **seven years** on the same records.

**A firm can run it correctly every month and have nothing to produce on
inspection, and nothing in the app says so.** That is the platform's own
silent-failure class, not a missing feature.

**Also measured:** **0** AML/CDD/beneficial-owner content in `sairnlaw.html`
against **EU AMLR 2024/1624 applying 10 July 2027**; **33** US state deadline
calendars and **0** non-US; the international case-law footprint is a
deliberate **US + England & Wales only** scope decision.

### 6.2 THE AUDIT CORRECTED ITS OWN DRAFT, AND FOUND TWO STALENESS DEFECTS

The first draft said the client used the tautological `reconcileTrust()`,
quoting the reconcile module's own header. **It does not** — that function was
removed; `trustFigures()` (`sairnlaw.html:3315`) displays the figures and is
forbidden from deciding agreement, and the real server reconciler is called.
**The draft was corrected rather than left standing.**

**Two staleness defects, reported NOT fixed** (discipline #8 — *nothing
announces the day a reference stops matching*):

1. `api/_lib/law-trust-reconcile.js`'s header describes
   `sairnlaw.html:3134 reconcileTrust()` **in the present tense** and that
   function no longer exists. The one hit for the name in `sairnlaw.html` is a
   comment at `:3288` saying it is gone.
2. **The branch is cited at three line numbers in three places and two are
   wrong.** `api/sd-data.js:1352` says `:11690` (a SAIRNcare roster `.map()`);
   `sairnlaw.html:3339` says `:12439` (an `alf_compliance_rules` comment). The
   real location is `api/sd-data.js:18747`.

### 6.3 One roadmap risk no vendor page would have disclosed

**The SRA consulted in 2025 on whether solicitors should hold client money at
all, and in December 2025 decided not to decide** — strengthening the current
regime now and returning to the wider question later. The most valuable thing
SAIRNlaw has in E&W is a trust-accounting engine, and the E&W regulator has an
open question about whether the firms will hold the money. **That is the single
clearest argument in the audit for pulling primary sources.**

---

## 7. WHAT IS OPEN — EXACT NEXT STEP PER ITEM

1. **Items 1 and 2 (§3).** Blocked on the claim, routed to hank with every
   line number. **Next step: Michael's go-ahead to me, or hank takes them
   alongside `api/bridge.js`.** Item 1's honest message depends on what hank's
   refusal returns, so order matters.
2. **`rf_jobs`' inverted projections (§5).** Flip both `Object.assign` calls so
   the real columns are the last source, matching `rf_claims`/read, plus a test
   arm that plants `assigned_employee_id` and `location_id` in the payload.
   **cody holds `api/sd-data.js`** — routed, not taken.
3. **`leg_cremations` and `employees` grounds cells (§5).** Rewrite as traced
   chains; do **not** retier. Needs whoever next holds
   `docs/CRITICALITY-TIERS.md`. **Never edit a row by splitting on `|`.**
4. **`docs/tier-a-reviews.json` append (§2).** The six verdicts are ready. cc
   holds the file.
5. **SAIRNlaw B1 — persist and sign the reconciliation (§6.1).** Small, highest
   value per line in the audit, and the four regimes are its specification. A
   stored reconciliation record is a **new Tier A resource** and will need a
   register row and a review obligation.
6. **The two reconcile staleness defects (§6.2).** One comment tense, two wrong
   line numbers. Cheap; nobody holds them.
7. **sairndental: a real screen-reader test (§4).** The one thing in the a11y
   work still unproven.
8. **cc: the `shared.js` skip (§5)** — measured again here at 8 findings.
9. ~~**`rtroutes_saved_sane` vs negative savings**~~ — **CLOSED 2026-10-19
   (fourth b38). Michael ran `sql/rt_routes_schema.sql` in Supabase WITH THE
   CONSTRAINT REMOVED**, which is the outcome this item argued for; the repo
   file is reconciled to what actually ran and the column now carries the
   reason as a comment so nobody re-adds it. **AND THE FILE HAS NOW RUN, WHICH
   CHANGES WHAT EDITING IT MEANS** — `create table if not exists` makes a
   re-run a no-op, so a further change to a column or key in that file changes
   nothing in the database. Anything else needs an `ALTER TABLE` in its own
   `sql/` file. **That makes cc's composite-foreign-key recommendation on
   `rt_stops.license_hash` (open-work index row, `docs/SAIRN-OPEN-WORK-INDEX.md`
   line 454) A MIGRATION RATHER THAN AN EDIT**, and it is not re-scoped here
   because the schema is mine and the handler is cody's.
10. **Carried from b36, unchanged:** `mech_schedule`; the `rt_routes` handler
   branch cody holds, which leaves all four wired consumers unreachable at
   runtime; the dental clearinghouse decision; sairnmechanical and sairnroofing
   still have zero audits.

---

## 8. EACH b37 ITEM: DONE / BLOCKED

| # | item | state | exact next step |
|---|---|---|---|
| 1 | Field Map catch arms stop naming the Maps key | **BLOCKED — flagged back, read-only evidence gathered** | §3.2; after hank's refusal lands |
| 2 | `stonedesk.html:7795` real action or delete | **BLOCKED — same claim** | §3.3; recommend DELETE |
| 3 | sairndental a11y remainder | **DONE** — 3→0 labels, 7/7 trap, 23/23 announced, real key presses, negative control | a real screen-reader test |
| 4 | Tier A review of six rows | **DONE** — 6 confirmed, 0 wrong tier, 0 unreadable; premise corrected and inverted | §7 items 2–4 |
| 5 | sairnlaw worldwide audit, primary sources | **DONE** — 8 primary sources, 6 jurisdictions, 0 vendor pages | §7 items 5–6 |
| 6 | push without force, confirm landed | **DONE** — `0 0`, both commits ancestors of `origin/main`, 3 files, 0 forbidden paths, no force | — |

**Both blocked items are blocked on the SAME claim and were flagged, not
reworded past the matcher.**

---

## 9. WHAT b37 PROVED vs LEFT UNPROVEN

**PROVED, measured or driven:**

* sairndental: unlabelled 3→0 of 155 by two independent methods; 7/7 modals
  trapped and returning focus; 23/23 panels announced; **real** Tab, shift+Tab
  and Escape; a negative control that would have caught an unconditional trap
* six Tier A rows read at the write site; the `employees` cross-app citation
  re-derived and unmoved; the `rf_jobs` location chain re-traced at HEAD; the
  absence of a historical leak window measured with `git log -S`
* `law_trust_reconcile` has one action and no table; `sairnlaw.html` has zero
  AML content; 33 state calendars and 0 non-US — all by command
* my two commits touch 3 files and **0** forbidden paths, pushed without force

**LEFT UNPROVEN:**

* **No screen reader was run.** §4 is a mechanical DOM audit.
* **The `rf_jobs` inversion is reasoned from `Object.assign` semantics and the
  strip list, not reproduced.** No row was written.
* **The `employees` `|| emp` fallback's reachability was read, not exercised.**
* **Nothing live.** No deployed URL was driven this batch — unchanged from
  b34/b35/b36 and for the same measured reason.
* **The sairnlaw audit drove no competitor product and interviewed nobody, and
  it says so twice.** Most primary sources were read via domain-restricted
  search snippets rather than the full instrument; `WebFetch` on the EUR-Lex
  summary returned an empty body and **that failure is reported rather than
  silently replaced with a secondary source**. No consolidated-text/amendment
  check on SI 2017/692 or the NSW rules.
* **Items 1 and 2 were read, not fixed.** The read-only evidence in §3 is a
  scope statement, not a verified fix.
