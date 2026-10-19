# HANDOFF — fourth / ted, batch b29, 2026-10-17

**READ THIS FILE ONLY.** It is the whole state.

**THIS IS A POST-PUSH HANDOFF AND NOTHING IS HALF-FINISHED AT THIS LINE.**
b28's handoff was a *pre-push* snapshot and the next session opened it and
read a closed batch as mid-flight. This one is written after the push landed
and after the live deployment was re-verified, so §1 is a state you can act on
rather than a plan. Items 4 (this file) and 6 (report/digest) are what remain
and neither can change a line above them.

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you mean
to quote, including out of this file.**

**FOUR THINGS TO READ FIRST:**

1. **b28's own LEFT UNPROVEN entry was the whole of b29 item 1, and it was
   right to be worried.** Rendering the app found **three defects**, one of
   them introduced by b28 itself. §2.
2. **`var(--accent)` IS NOT A TOKEN IN THIS APP AND NEVER WAS** — written by
   b28, defined nowhere, so the revise banner's stripe rendered at **0px**.
   b28's 22-arm green run could not have caught it *in principle*. §2, §5.
3. **41 WCAG AA contrast failures across all 23 panels, now 0** — including
   every primary button in the app. Nothing on this platform could measure
   that before today; the instrument is new and is `tools/wcag_contrast_check.py`.
   §2.
4. **F1 and F2 HOLD ON REAL SUPABASE DATA**, discriminating case included, with
   a screenshot of the ledger reading `D0120` while the catalogue dropdown
   reads `D0150`. §3.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\b621dce3-b1b4-4681-a633-54da35b654a4.jsonl`

**Working files (this session's scratchpad):**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\b621dce3-b1b4-4681-a633-54da35b654a4\scratchpad\`
`b29_segA_signin.py`, `b29_segA2_signin_diag.py`, `b29_segB_sweep.py`,
`b29_segC_f1f2_live.py`, `b29_segD_probes.py`, `b29_segE_public.py`,
`b29_segF_verify_fixes.py`, `b29_contrast.py`; evidence `b29_contrast_before.json`
(41 rows), `b29_contrast_live_after.json` (0 rows), `b29_f1f2_live.json`,
`b29_probes.json`, `b29_fix_ablation.json`, `b29_public.json`; screenshots
`b29_shots/` (pre-fix, 46 + 8 driven) and `b29_shots_after/` (46, post-deploy).
**`b29_visual_findings.json` holds the AFTER sweep only — the after-run
overwrote the before-run's copy.** The before state survives in
`b29_contrast_before.json`, which is the file the 41 is quoted from.

---

## 1. COMMITTED / PUSHED STATE, AS OF THIS LINE

| | | command |
|---|---|---|
| `HEAD` vs `origin/main` | **0 ahead, 0 behind — PUSHED AND LANDED** | `git rev-list --left-right --count origin/main...HEAD` |
| the fix commit | **`730a078c`** on `origin/main` | `git log --oneline origin/main` |
| other b29 commits | `14ca5638` register, `327bd001` tool owner, `d81d79d1` + `b7d8ed5a` sha re-seats | — |
| claim | **HELD** by fourth, published on `origin/main` | `sairn_claim.py own` |
| status row | `working` | `sairn_status.py` |
| uncommitted | **none** | `git status --porcelain` |
| `git stash` | **0** | `git stash list` |
| `SAIRN_SEED_GATE` / `GATE_EXEMPT` / `SAIRN_SKIP` | **none used, any form** | — |
| `.claude/settings.json` | **not edited** | — |
| hooks | **untouched** | — |
| files written under `api/` `sql/` `tests/` | **0** | `git status --porcelain` |
| auditor clones | **not entered** | — |
| b29 batch manifest | opened FIRST, `--new fourth b29 --items 6`; **5 done, 1 open** (item 6 is the report) | `batch_manifest.py --check --agent fourth --batch b29` |
| live deployment | **re-fetched after the push: 445,714 bytes, equal to the working tree; `--pdd` present; no live `var(--accent)` reference** | `tools/sairn_http.py` |
| post-push live re-verify | **`wcag_contrast_check.py --app sairndental` = 0 failures, exit 0** | that command |

**THE PUSH TOOK TWO REBASES** onto other sessions' work and each one rewrote my
shas, so the defect-register records were re-seated twice
(`bf63824c -> a52a6135 -> ce26270a -> 730a078c` as published). **The OWNER line
on the new tool was added as a SEPARATE commit rather than an amend, on
purpose**: the register records cited the fix commit and
`defect_register.py --check` requires every cited commit to resolve, so
amending to satisfy a push gate would have broken the ledger that documents the
push.

---

## 2. ITEM 1 — THE APP WAS RENDERED FOR THE FIRST TIME, AND IT COST THREE DEFECTS

**Driven against the LIVE deployment, signed in through the real gate with the
documented demo owner (`DNT-PINNACLE-2026` / `sairn-demo-owner`), on REAL
Supabase rows** — 5 patients, 3 providers, 5 procedure types, 0 charges at the
start. Not a fixture, not a stub, not a mock.

### F3 (b28 REGRESSION) — an accent that did not exist

`style="...border-left:3px solid var(--accent)"` on `#pc-edit-banner`, written
by b28's `9a0903e6`. **`--accent` appears exactly once in this file, is not in
`:root`, and is not a house token in any of the other sixteen apps.** A `var()`
that resolves to nothing makes the declaration invalid at computed-value time,
so the **whole `border-left` shorthand is dropped**. Measured in the browser
before the fix: `borderLeftWidth "0px"`, `borderLeftColor rgb(100,116,139)` —
`currentcolor`, the muted text colour. The stripe was not the wrong colour; it
was **not there**.

**FIXED** to `var(--p)`; ablated **red on HEAD, green on the fix**
(`0px -> 3px`, `rgb(100,116,139) -> rgb(14,165,233)`).

### F4 — 41 WCAG 2.2 AA contrast failures, across all 23 panels

Measured, not judged. The worst and the most repeated:

| ratio | needs | what | reach |
|---|---|---|---|
| **2.28** | 4.5 | `--ok` green badges at 11–13px (`On file`, `Active`) | 12 panels |
| **2.77** | 4.5 | **white on `--p` #0EA5E9 — EVERY primary button in the app** | 22 panels |
| **3.29** | 4.5 | header pills, white on the composited bar | 23 panels |
| **3.57** | 4.5 | the active sidebar item, `--pd` on `--pt` | 23 rows |
| **3.76** | 4.5 | `--danger` red (`Not linked`, `No email on file`) | 6 panels |
| 4.10–4.48 | 4.5 | `--pd` body text, `--muted` on tinted backgrounds | 5 places |

**FIXED by moving tokens, not by redesigning.** `--p` keeps the bright brand sky
for borders, focus and accents and is **never again a surface under white
text**; `--pd` darkened `#0284C7 -> #0369A1` (5.93:1 white-on, 5.17:1 sidebar);
`--pdd` **added** so `:hover` stays a visible state change; `--ok -> #15803D`,
`--danger -> #DC2626`, `--muted -> #556070`; the header pills now **darken**
the bar (`rgba(0,0,0,.14)`) because a white veil composites the wrong way and
raising it makes contrast worse, not better.

**ABLATION, same tool, same 23 panels, same code path: HEAD 41 failures exit 1
-> fixed tree 0 exit 0 -> live deployment after the push 0 exit 0.**

### F5 — a public booking link that could not work, and both screens were silent

The live `dnt_settings` row lists `publicly_bookable_procedure_type_ids =
["PC-1786416376504-314"]`; the catalogue holds `PC-DEMO-1..5`. **The server is
right and fails safe** — `api/sd-data.js` resolves against the real catalogue,
returns `procedure_types: []`, and the public page tells every patient *"Online
booking is not yet available for this practice."* **Driven live on
`/sairndental-book?slug=verify-test-slug`.**

What was wrong is that the owner's Booking Settings panel showed a *"Public
link: …"* preview and five unticked boxes and **said nothing about either
fact**. A practice could hand out a dead link indefinitely. **FIXED**: the
unresolved ids are named, and when nothing resolves the panel says the link is
dead. Ablated red-on-HEAD, green-on-fix.

### What the sweep found NOTHING on, and why that is worth something

* **The literal-markup assertion returned `[]` on all 23 panels × 2 viewports**
  — and that is only meaningful because it was **ablated**: a tag built by
  `['<','div',' class="x">'].join('')` **was caught**, removing it went clean
  again, and the same string inside `<code>` was correctly **ignored**. A
  checker that has only ever returned clean is unproven, not proven.
* **No clipped overflow at 390px on any panel.** Mobile layout holds.
* **One console error on every page load**: `_vercel/insights/script.js` 404s.
  Cosmetic, not mine, **not fixed, and named rather than dropped**.

---

## 3. ITEM 1 (CONT.) — F1 AND F2 HOLD ON REAL DATA

**19 checks, 18 pass.** The one failure was **my own harness**, disclosed below.

* A charge posted **through the real UI** carries `cdt_code: "D0120"` — server
  re-read confirms it.
* The catalogue row was then revised **in place** to `D0150`: **same row id**,
  no new row (5 -> 5), one revision **appended**, and the server re-read shows
  `revisions: 2` after the restore.
* **THE DISCRIMINATING CASE: the ledger still reads `D0120`** while the Add
  Charge dropdown reads `D0150`. Screenshot
  `b29_shots/C5-billing-after-revision-DISCRIMINATING.png`. `dntChargeCode()`
  on the real row returns `stamped: true`.
* The demo tenant's current code was **restored to D0120** afterwards.

**WRITES MADE TO THE DEMO TENANT, disclosed because `api/sd-data.js` has NO
DELETE VERB and the charge is therefore permanent:** one charge
`CH-1792248288879-870` ($65 against `PT-DEMO-1`), and two revisions of
`PC-DEMO-1` (the second restores the original code). Demo licence only; no
customer licence was touched.

**MY HARNESS DEFECT, second batch running:** check C1 asserted *"the charges
list grew by exactly 1"* and read 1 -> 1. The app was right — an empty charges
table renders **one placeholder row reading "No charges yet"** with
`colspan=5`, so the count was unchanged while the content was not. **A
row-count outcome check must exclude the empty-state row**, and b28's
colliding `newId()` was the same class of defect in the same place.

---

## 4. ITEM 2 — THE BEHAVIORAL-HEALTH AUDIT

`docs/cloud-research/behavioral-health-worldwide-competitive-gap-audit-2026-10-17.md`.
Second in the "vertical SAIRN has not built for" series.

* **THE UNIVERSE WAS RE-DERIVED AND IT CORRECTS b28.** `git ls-files '*.html'`
  filtered to root products gives **SEVENTEEN**, not the eighteen b28 asserted
  one day earlier. Every denominator in the new document is *n of 17* with its
  command.
* **The gap is the supervision layer**, not the EHR: whether an associate
  clinician's session is billable at all — who supervised it, were they
  credentialed that day, does this payer allow it in this state. Supervision-
  hour tracking is **not** a standard EHR feature (a cottage industry of
  standalone trackers is the market saying so), incident-to is narrow and
  payer-specific and is being **withdrawn** by some commercial payers, and
  Headway does not support it at all.
* **Two primary-source regulatory citations, pulled from the Federal Register
  API, not a summary:** 42 CFR Part 2 final rule **89 FR 12472** (doc
  `2024-02544`), **compliance date 2026-02-16, already passed**, now at
  HIPAA-level penalties; and the DEA fourth telemedicine extension **90 FR
  61301** (doc `2025-24123`), **flexibilities lapse 2026-12-31** with the
  special-registration final rule still at OIRA.
* **METHODOLOGICAL GAIN WORTH KEEPING: b28 recorded that a redirect blocked the
  Federal Register fetch. `WebFetch` is still blocked — it 302s to
  `unblock.federalregister.gov` — but the FR JSON API answers 200 through
  `tools/sairn_http.py`, because that module sends a browser User-Agent.** Use
  that route for any regulatory citation rather than re-discovering the block.
* **Platform fit measured, and read pessimistically:** a supervisory
  co-signature exists in **2 of 17** apps, a date-of-service concept in **4 of
  17**, CPT in **1 of 17**, and **in no single app together**. Three proven
  halves in three different products, not a reusable core.
* **NOT a build recommendation.** §7 of that document lists what would have to
  be true; none of it is. **Two audits have now named the same missing role —
  an owner for a 50-state rule matrix.** That is the finding about SAIRN rather
  than about the market.

---

## 5. ITEM 3 — CONVENTION 38, AND THE INSTRUMENT IT IS ABOUT

**`docs/2026-09-13-cross-domain-disciplines.md` § 38: A UNIT CHECK CANNOT SEE A
COMPOSITION DEFECT — verify at the layer where the layers actually combine.**

Paid for twice in one day, which is why it is a convention and not a note:

* **The app half.** b28's 22 arms were all sound, all still pass, and **none of
  them could ever have gone red** for F3, because the defect does not exist
  until a cascade resolves a custom property.
* **The checker half.** My contrast sweep's first draft took the first ancestor
  with alpha > 0.1 as opaque and reported **white on white, 1.00, on all 23
  panels** — a fabricated figure on elements that really render at 3.29. The
  real surface exists only after the compositor combines layers.

**The denominator was moved from thirty-seven to thirty-eight and the
cannot-fire group from TWELVE to THIRTEEN, with the membership question asked
and answered on BOTH halves: admitted on the app half, refused on the checker
half** (a measurement fault, which puts it beside 35, 21, 22 and 37).

**`tools/wcag_contrast_check.py` is new**, owned by fourth, **19 fixtures in
both directions**, every mode runs them first and refuses to report if they do
not classify, and it exits **2 COULD NOT RUN — never 0** when playwright,
chromium, the credential row or sign-in is missing, **because a signed-out app
renders a licence gate and would sweep clean**. It reads its demo credential
out of `docs/2026-09-03-demo-credentials.md` rather than storing a second copy.
**Its own fixtures caught two defects in it before it was committed** — the
composite above, and a colour parser that refused `rgb(1 2 3 / .5)`.

---

## 6. WHAT IS OPEN, BY OWNER

### fourth (me) — next batch

1. **WIRE THE CONTRAST CHECK INTO SOMETHING, OR IT WILL ROT.** It runs only
   when a person runs it, and `APPS` in it has **one profile** (sairndental).
   **Exact next step:** add a profile per app (url, file, nav function, panel
   prefix) and decide gate-vs-cadence. This is written in the F4 register
   record as a `planned` action and is therefore owed.
2. **The other sixteen apps have never been measured.** F4 was one app; the
   class is platform-wide. **Exact next step:** `--app <name>` once a profile
   exists; expect findings, because sairndental's palette is the house palette.
3. **`sairndental.html` has still never been through `sairn-visual-review`'s
   human half on a touch device**, and the 46 screenshots are emulated
   viewports, not real hardware.

### cc — `tools/`

**Unchanged from b28 and NOT re-verified this batch, which is why it is not
restated in detail — read b28's handoff for the bodies:**

1. **LAND THE TWO FUNCTION BODIES** from
   `docs/2026-10-16-fourth-b28-tier-a-shards-routed-to-cc.md`. Until then the
   b28 `bld_bids` discharge is recorded but **not authoritative** and
   `docs/tier-a-reviews.json` keeps being the contention it has been for four
   batches now.
2. `review_ledger_reseat.py` — named non-patch, a semantics decision.
3. **INSTALL THE BRANCH CENSUS** from
   `docs/2026-10-16-fourth-b27-branch-census-routed-to-cc.md`.
   `tools/branch_census.py` **still does not exist**; seventh batch.
4. `batch_manifest.py --check` should RESOLVE paths inside evidence strings.
5. Carried: `tier_a_review_gate.py --amend`; one anchor-rot tool into a gate;
   R3's 48 citation ranges; the convention-numbering check — **which b29 moved
   a prose denominator by hand instead of, for the fifth batch running** (§5).

### cody — `tests/`

**UNCHANGED AND UNTOUCHED BY ME, BY INSTRUCTION.** Both b28 findings stand
exactly as routed and I did not go near `tests/`:

1. **CHECK (4), HIGH — `tests/sairnbuild_server_wins.js:408` and `:418`.**
   `bld_bids` can lose its pending tracking entirely with the suite green.
   **Exact next step:** match over a comment-and-string-stripped copy, require
   the guard rather than the substring, **then re-run N1 and N4 and confirm
   BOTH go RED**.
2. **An arm for `bld_draws`**, which has none — flipping it alone is accepted
   at 25/0.
3. Carried from b27: arm Z's `else` branch then re-run the ablation;
   `known-red-suites.json` blob-scope row; b24 F1's re-anchoring; a
   failing-first arm driving `23514` and `42703`.

### hank — `api/`

**Carried from b26/b28 and NOT re-verified this batch.** H3 first (the
append-only closings resource and the named refusal of
`payroll_closed_periods` at the generic `sen_settings` path), then H2, then H1
with the 2×2 re-run confirming ARM A goes RED; then Q4's `partially_closed`,
Q(b)2's EVV basis, Q(c)'s two purity headers; then b24 F3 and F4. **Read b26's
handoff for those, not this paragraph.** And b28's addition stands:
`docs/tier-a-reviews.json` is a **read-only base layer** — append to
`docs/tier-a-reviews/hank.jsonl` once cc lands the routed change.

### Michael

**Nothing blocking from b29.** Three things named rather than acted on:

1. **The primary brand surface is a shade darker everywhere.** `--p` is
   untouched for borders and accents, so the app still reads as the same
   product, but every button, the header and the active sidebar item are
   deeper. It was an accessibility fix, not a design preference, and the exact
   revert is three token values in `:root`. **Say the word if you want it
   back** — and know that reverting restores 41 measured AA failures.
2. **The behavioral-health vertical is NOT recommended** by §7 of that
   document, for the same shortfall childcare had: no driven competitor
   account, nobody interviewed, and **no owner for a 50-state rule matrix**.
   Two audits have now named that same missing role.
3. Carried, unchanged from b28: the one-person-agency self-approval question;
   whether any real visit was underpaid is **not establishable from the repo**;
   and **no agency has a `payroll_closed_periods` row, so the freeze has never
   run on real data by anyone.**

---

## 7. WHAT IS STILL AHEAD OF THIS FILE

**Nothing is half-finished.** Two whole steps:

1. The report and the digest; upload this file plus both to Drive folder
   `14Xc5oT0xzSLa_rTSOSXWVK3Kko1Fbx09` and **verify each THROUGH THE DRIVE
   API**, not off the mount.
2. Close the manifest, **release the claim LAST**, then set the status row to
   `idle`.

---

## 8. WHAT b29 PROVED vs LEFT UNPROVEN

**PROVED, driven or measured:** that the live deployment serves exactly the
bytes in the repo; that the real licence gate and the real PIN gate admit the
documented demo owner and the app then loads 20+ resources from real Supabase;
that F1 and F2 hold on real rows including the discriminating case, with the
server agreeing on both the stamp and the revision history; that an undefined
custom property made a border render at 0px and that b28's green run could not
have seen it; that 41 distinct AA failures existed and that 0 remain, measured
three times on the same code path; that the literal-markup assertion can be
made to fire and correctly ignores `<code>`; that the public booking page
refuses a dangling procedure id and tells the patient so; and that the Federal
Register API is reachable from this platform when `WebFetch` is not.

**LEFT UNPROVEN, and none of it is recorded as checked:**

* **The contrast check is not wired into any gate and knows one app.** The
  **other sixteen are unmeasured** and the palette is shared, so the finding
  almost certainly generalises and has not been looked at.
* **No real device.** 46 screenshots at two emulated viewports is not a phone.
* **No keyboard-navigation, focus-order or screen-reader pass.** AA contrast is
  one criterion of many and the rest were not attempted.
* **Only the states the sweep put each panel into were seen** — a panel's error
  state, loading state and populated state are mostly not among them, and 13 of
  the 23 panels hold no data on the demo tenant at all.
* **The behavioral-health audit drove no competitor product** and interviewed
  nobody; its central claim rests on secondary, partly vendor-authored sources
  and its §5 says so. **No market-share table exists for that vertical** and the
  vendor counts were deliberately NOT combined into one.
* **`tests/` findings (2) and (4) from b28 are still reported and NOT fixed** —
  by instruction and by design; they are cody's.
* **Everything in §6 attributed to cc and hank is carried and was not
  re-verified this batch.**
