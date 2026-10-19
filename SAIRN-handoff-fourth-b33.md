# HANDOFF — fourth / ted, batch b33, 2026-10-19

**READ THIS FILE ONLY.** It is the whole state.

**Written BEFORE the report, which is the standing instruction.** Nothing in
this batch is half-finished: every item is either done and landed, or named
below with exactly what is missing.

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you mean
to quote, including out of this file.**

**FOUR THINGS TO READ FIRST:**

1. **ROUTING CODE ALREADY EXISTS AND NOBODY KNEW.** b32 recorded the
   archaeology as a *false nil* — searched, never read. It was re-run and read
   this batch. A complete nearest-neighbour route optimiser over Google Route
   Matrix drive times exists at commit `35169ea2`, on a branch that is **not an
   ancestor of `main`**. §4.
2. **STONEDESK'S FIELD MAP ROUTE OPTIMISER IS BROKEN ON THE LIVE DEPLOYMENT,
   AND ITS ERROR MESSAGE BLAMES THE WRONG THING.** Live-verified, HTTP 401. §4.2.
3. **THE RENDERED PASS IS DONE — 13 of 13 — AND IT CARRIES A SCOPE LIMIT THAT
   MUST NOT BE DROPPED.** Every interior was reached by forcing display via
   JavaScript, never by authenticating. These screenshots prove CSS, markup and
   brand render. They prove nothing about the auth path or the data path. §3.
4. **I ALMOST ROUTED cc A TOOL BUG THAT WAS MY OWN TRUNCATED READ, AND THE
   PUSH GATE CAUGHT IT.** `tools/context_verify.py` is correct; I quoted a
   number out of a `tail -20` and left its ambiguity warning behind. §7 —
   **nothing is routed to cc.**

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\7114877e-14ff-4635-8129-799b043ea778.jsonl`
(a **fresh window** — not a continuation of b29–b32's `b621dce3…` session)

**Working files (this session's scratchpad):**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\7114877e-14ff-4635-8129-799b043ea778\scratchpad\b33\`
— holds `live_bridge.py` (the live 401 probe) and `httpd.log`.

---

## 1. COMMITTED / PUSHED STATE, AS OF THIS LINE

| | | command |
|---|---|---|
| `HEAD` vs `origin/main` | see §8 — this file precedes the push | `git rev-list --left-right --count origin/main...HEAD` |
| files written this batch | 3 docs + 1 manifest, **no app code, no `api/`, no `sql/`, no `tests/`** | `git status --porcelain` |
| `.html` files changed | **0** | `git diff --name-only HEAD \| grep -c '\.html$'` |
| `git stash` | **0** | `git stash list` |
| `SAIRN_SEED_GATE` / `GATE_EXEMPT` / `SAIRN_SKIP` | **none used, any form** | — |
| `.claude/settings.json`, `.githooks/` | **not touched** | — |
| auditor clones (`SAIRN-hover`, `SAIRN-hover2`) | **not entered** | — |
| claim | **HELD** by fourth, published, FILES list declared | `sairn_claim.py own` |
| status row | `working` at this line; set to `idle` after the report | `sairn_status.py` |
| b33 manifest | opened FIRST, `--new fourth b33 --items 6`, `id_lock=906816e5cf0d24f9`; **5 done, 1 open** (item 6, the push, which this file precedes) | `batch_manifest.py --check --agent fourth --batch b33` |

**NO GATE WAS SKIPPED AND NO OVERRIDE WAS USED.** Stated explicitly because
`docs/BYPASS-LOG.jsonl` shows 80 of 94 rows were taken because the blanket flag
was the only thing available; a batch that used nothing should say so as
loudly.

---

## 2. WHAT LANDED — SIX ITEMS, FIVE DONE

| # | item | state |
|---|---|---|
| 1 | orientation / pull / claim | **done** |
| 2 | rendered pass on the 13 recoloured apps | **done, 13/13, with a stated scope limit** |
| 3 | re-run item 5's three searches **and read them**, extended | **done — and it changed the answer** |
| 4 | routing primitive, phase 1 scope | **done** |
| 5 | the three recurring blockers, one page | **done** |
| 6 | push | §8 |

---

## 3. ITEM 2 — THE RENDERED PASS, 13 OF 13

**Nothing had been rendered since b29 while fourteen customer-facing apps
changed colour across b31 and b32 on the strength of arithmetic alone.** That
is closed.

**Method, stated because it bounds the result:** the clone was served at
`http://127.0.0.1:8733` (`python -m http.server`) and each app was opened in
Chrome and screenshotted. `file://` is refused by the extension, which is why a
local server was used.

| app | `--p` (or its brand token) | verdict |
|---|---|---|
| sairnbiz | `#14B8A6` / `--pd #0F766E` / `--pdd #0A524C` | **PASS** — gate + dashboard |
| sairnbuild | `#F59E0B` / `#B45309` / `#8D4107` | **PASS** |
| sairncare | `#0D9488` / `#115E59` / `#0B3B38` | **PASS** |
| sairncash | `--pulse #00E5C4` (dark theme, no `--p`) | **PASS** — landing, paywall **and** app interior |
| sairncode | **no CSS custom properties at all** | **PASS** — gate + dashboard |
| sairndesign | `#6366F1` / `#4338CA` / `#372EAC` | **PASS** |
| sairngrounds | `#16A34A` / `#15803D` / `#0F5D2C` | **PASS** |
| sairnlegacy | `#6B7280` / `#4B5563`, **no `--pdd`** | **PASS** |
| sairnmechanical | `--d #3F6212` (no `--p`), `page-*` not `panel-*` | **PASS** |
| sairnscape | dark `#060810`, `--d #404060` | **PASS** — consumer chat, business gate **and** business dashboard |
| sairnsenior | `#DB2777` / `#9D174D`, **no `--pdd`** | **PASS** |
| sairnvet | `--primary #7C3AED` (no `--p`), shell is `#appContainer` | **PASS** |
| stonedesk | `--navy #1B3A6B`, `--surface`/`--surface-2` **now defined** | **PASS** — and see below |

**THE SINGLE MOST USEFUL RESULT: b31's StoneDesk `--surface-2` FIX IS
VISUALLY CONFIRMED.** `getComputedStyle(document.documentElement)` resolves
`--surface-2` to `#f0f4fb`, and the four `.biz-kpi` tiles in `panel-business`
render with a visible pale-blue background (`rgb(240, 244, 251)`). Before b31
that token was undefined, the declaration was dropped at computed-value time,
and the tiles would have been white-on-white against the card. **That is the
first rendered proof of that fix and it is the one that most needed one** — 56
background declarations depended on it.

**THE SCOPE LIMIT, WHICH MUST TRAVEL WITH EVERY ONE OF THESE VERDICTS:**

* **Every interior was reached by forcing `display` via JavaScript. No app was
  authenticated into.** Four of them (sairnmechanical, sairnvet, sairncash and
  stonedesk) have server-backed credential gates that were deliberately not
  attempted.
* So a PASS here means: **the CSS, the markup and the brand identity render
  correctly.** It does **not** mean the gate works, the session works, the data
  loads, or any control functions.
* **No keyboard, focus-order or screen-reader pass was done, in any app, ever.**
  Unchanged from b32.

**THREE OBSERVATIONS WORTH CARRYING:**

1. **The b31 argument does not apply uniformly, and that is not a defect —
   it is a thing to stop repeating.** "`--p` keeps every border, accent and
   focus ring" is true of the eight apps that define `--p`. **Six of the
   thirteen do not define it at all**: sairncash (`--pulse`), sairnvet
   (`--primary`), sairnmechanical (`--d`), sairnscape, stonedesk (`--navy`),
   and **sairncode, which uses no CSS custom properties whatsoever** — its 62
   changed lines were literal hex edits. Anyone re-applying the house pattern
   must check which family an app is in first.
2. **Three apps have no `--pdd`** (sairnlegacy, sairnsenior, and sairnmechanical
   which has `--d` instead). Each had only ~2 lines changed in `8c5717d1`,
   consistent with needing no hover-state token.
3. **Honest empty states everywhere.** Every dashboard showed `0`, `$0`, `--`
   or an explicit sentence ("No operations data yet — nothing to analyse",
   "Not enough decided-proposal history yet (0 on record, need at least 6)",
   "Crew is read live from SAIRNbiz and is **not** stored here… the list is
   genuinely empty — not hidden, not seeded"). **Zero fabricated KPIs
   observed in thirteen rendered dashboards.** That is Check 0b passing in the
   place it is hardest to fake.

**ONE MEASUREMENT I ATTEMPTED AND COULD NOT COMPLETE, recorded rather than
quietly dropped:** I tried to compute real WCAG ratios in the browser, hoping
to resolve some of the **4,420 ancestor-dependent UNRESOLVED pairs** the static
checker cannot. It worked for flat backgrounds and **failed for gradients** —
StoneDesk's gate reported 1.07:1 on text that is plainly readable, because
`backgroundColor` is `rgba(0,0,0,0)` and the colour lives in
`linear-gradient(135deg, #1B3A6B, #2A5298)`. **No contrast finding is reported
from that attempt in either direction.** A gradient has no single background
colour to compare against; resolving it needs sampling rendered pixels, not
computed style. That is a real and tractable next step for the contrast tool
and it is **not** claimed as done.

---

## 4. ITEM 3 — THE ARCHAEOLOGY, RE-RUN AND **READ**

b32 left this as an explicit false nil: *"zero findings are recorded because
zero output was seen."* All three searches were re-run, **the output was read**,
and the search was extended to `git log -S` over deleted code and the
`archive/` tree as instructed.

### 4.1 Routing code exists — off-branch

Commit **`35169ea2`**, 2026-06-18, *"Add maps-optimize and maps-static actions
to SAIRN Data Bridge for StoneDesk Field Map"*, adds 105 lines to
`api/bridge.js`: a POST `?action=maps-optimize` taking `{addresses}`, a call to
Google's **Route Matrix** with `travelMode:'DRIVE'`, a **nearest-neighbour
ordering over real drive times** with an unreachable-pair fallback, and a
`savedMinutes` figure. Plus `?action=maps-static`, which fetches the preview
image server-side and returns a data URL so the key never appears in a
browser-visible URL.

```
git merge-base --is-ancestor 35169ea2 HEAD    # -> NOT an ancestor
git branch -a --contains 35169ea2             # -> remotes/origin/claude/lucid-ptolemy-b73vu0
grep -i "maps\|optimize\|GOOGLE_MAPS" api/bridge.js   # -> nothing at HEAD
grep -rln "maps-optimize" archive/            # -> nothing; the archive did NOT preserve it
```

`main`'s `api/bridge.js` was built fresh on 2026-07-31 (`df84b213`) and carries
only `proxy_get` and `push`.

### 4.2 The client half is on `main` and is calling into the void

`stonedesk.html:12547` sets `FM_API`; `:12927` (`fmRunOptimize`) POSTs
`?action=maps-optimize`; `:12814` (`fmRenderMap`) POSTs `?action=maps-static`.
Neither sends `Authorization`. On `main`, any POST that is not `proxy_get`
falls through to the licence-gated `handlePush`.

**Live-verified via `tools/sairn_http.py` against the real deployment** (not
bare `curl`, per PR §3.2):

```
POST /api/bridge?action=maps-optimize  -> HTTP 401 Unauthorized
POST /api/bridge?action=maps-static    -> HTTP 401 Unauthorized
GET  /api/bridge                       -> HTTP 405 NO_READ_SIDE (by design)
```

**And the catch arm blames the wrong thing:** *"Could not optimize route --
check the Maps API key is configured."* The key is irrelevant; the request never
reaches code that reads it. A person acting on that message goes and checks a
Vercel environment variable that is not the problem.

### 4.3 A latent hazard in the same fall-through

`handlePush` upserts `{license_hash, data}` into `bridge_data`. Today the maps
calls 401 because they carry no licence. **If a future change gave them the
licence header the rest of StoneDesk already holds, the fall-through would
accept them as a push and upsert `data:{addresses:[...]}` over that shop's row
— silently, with a 200 ok.** The defect is that an unknown `?action=` reaches a
*write*.

### 4.4 What does NOT exist, having now actually looked

* `route_order`, `stop_order`, `visit_order`, `waypoint`, `distance_matrix`,
  `dispatch_board` — zero real hits at HEAD.
* **Real geo primitives DO exist:** `sairngrounds.html:2793` `gcdHaversineM()`
  (WGS84 great-circle with an added-not-averaged accuracy band, and a refusal
  to report a distance at all when the combined band exceeds 25 m);
  `sairnsenior.html:3207` leaves `lat`/`lng` **null** rather than faked when
  permission is refused; `sairnlegacy` shares a live vehicle position.
* **The archived `sairntrade.html` `optimizeRoute()` is NOT prior art** — it is
  a Claude prompt with six hardcoded Westlake OH addresses in the user message.
  Named here so nobody mistakes it for one later.

---

## 5. ITEMS 4 AND 5 — THE TWO DOCUMENTS

**`docs/2026-10-19-fourth-b33-routing-primitive-scope.md`** — written **after**
§4 had a real answer, which is the sequencing b32 got right and was interrupted
inside. One shared module under `api/_lib/`, dispatched by `api/sd-data.js`
resource `routes` — **not** `api/bridge.js`, whose own header says it is
StoneDesk-only and is not the cross-app path other apps mean. `rt_routes` /
`rt_stops` schema; four actions (`read`, `upsert`, `reorder`, `optimize`) with
an explicit `basis:'unavailable'` third state so "could not run" is never folded
into a result. **StoneDesk named first**, because `fmRunOptimize()` already
builds the address list, already consumes `{order, savedMinutes}`, already
persists and re-renders, and already splits done from not-done — phase 1 there
is three edits. **Scope only; no app code was written.**

**`docs/cloud-research/2026-10-19-three-recurring-blockers.md`** — the three
blockers across four audits: **(A)** no owner for a standing 50-state
regulatory matrix (named by three of four), **(B)** SAIRN has never sold an
administered service (trucking), **(C)** the routing primitive (pest control).

**§4 of that page answers the required question plainly and in both
directions:**

> **The routing scope document DOES NOT close Blocker C.** No code, no schema
> run, no endpoint, nothing deployed, nothing tested. A design on disk is not a
> primitive.
>
> **It DOES close the unknown inside it:** routing code exists; this is a
> repair plus a shared module rather than a greenfield build; StoneDesk is the
> first app and why; and the schema and API surface are specified.

Four named closing conditions, **none done**: tier the two resources *before*
the code; land the shared module; repoint and live-verify StoneDesk; prove it
shared with a second app (SAIRNgrounds argued, because it already owns the only
real haversine on the platform).

---

## 6. WHAT IS OPEN, AND THE EXACT NEXT STEP FOR EACH

**Nothing below is partially applied anywhere. These are not-started items.**

### 6.1 The three repairs due regardless of any vertical decision

1. **`api/bridge.js` must refuse an unknown `?action=`** rather than falling
   through to `handlePush`. §4.3. **Not claimed, not started.** Owner: whoever
   next holds `api/` — hank's lane.
2. **StoneDesk's two Field Map error messages must stop naming
   `GOOGLE_MAPS_API_KEY`.** §4.2. `stonedesk.html:12944` and `:12818`.
3. **`maps-static` needs a decision, not a scope.** Until someone decides
   whether a map image is wanted at all, `fmRenderMap` should say *"Route
   preview is not available in this build."*

### 6.2 Routing phase 1 — the four closing conditions

In order, from the blockers page §4. The **first** is a register write that
must precede the code, not follow it: `rt_routes` and `rt_stops` into
`docs/CRITICALITY-TIERS.md`, expecting **A on confidentiality** (an address
joined to a named assignee and a date is the class that took `grd_cart_orders`
and `leg_processions` to A). **That file is contended — check the claim record
before touching it.**

### 6.3 The contrast tool's gradient blind spot

§3. Resolving `linear-gradient` backgrounds needs rendered-pixel sampling, not
computed style. **Nothing was changed in `wcag_contrast_check.py` this batch**
and no finding was filed from the failed attempt.

---

## 7. A "TOOL BUG" I WAS ABOUT TO ROUTE TO cc — AND IT WAS MY READING ERROR

**This section said `tools/context_verify.py` overstated this session's context
by five times and routed it to cc as a defect. THAT WAS WRONG, the push gate
caught it before it landed, and the correction is more useful than the claim
would have been.**

What happened. An early run printed:

```
  agent     REAL %       prompt      window   age h
  fourth     94.2%      188,338     200,000     0.0
```

I read `94.2%` as the tool's answer, concluded it had inferred a 200,000 window
for a 1,000,000-token session, and wrote it up as a five-fold overstatement.

**The tool had already said otherwise and I did not read it.** `--agent` sets
an `ambiguous` flag whenever more than one published window still fits the
observed maximum (`tools/context_verify.py:437-456`). At 188,338 tokens **both
200,000 and 1,000,000 fit**, so the row was flagged and carried a `why` naming
both candidate percentages and the fix — *"Declare it once: python
tools/context_verify.py --provision-window <tokens>"*. The file says the same
thing in its own header at lines 76-89: **the inference is a FLOOR, therefore
the percentage is a CEILING.** b21 built that guard on purpose.

**I truncated the output with `tail -20` and quoted the number without the
warning attached to it.** That is the exact failure CLAUDE.md names — *a
truncated read is indistinguishable from a complete one* — committed while
writing up a different session's measurement discipline.

**Nothing is wrong with the tool and nothing is routed to cc.** Later in the
same session the prompt passed 200,000, only one published size still fit, and
it resolved correctly and unprompted:

```
  fourth     30.9%      308,588   1,000,000     0.0   [window INFERRED]
```

**The one thing genuinely worth carrying forward** is not a defect report, it
is a usage rule: `--digest-line` is the command, its output is pasted
verbatim, and the push gate `context-digest` refuses anything hand-written —
which is precisely how this got caught. A figure read out of a truncated table
is not a measurement even when the tool that produced it is correct.

---

## 8. WHAT IS STILL AHEAD OF THIS FILE

**Nothing is half-finished.** Three whole steps:

1. The report and the digest, carrying the context line **exactly as
   `python tools/context_verify.py --digest-line` prints it** — the
   `context-digest` push gate refuses anything hand-written, and that refusal
   is what caught §7.
2. Upload this file, the report and the digest to Drive folder
   `14Xc5oT0xzSLa_rTSOSXWVK3Kko1Fbx09` and **verify each THROUGH THE DRIVE
   API**, not off the sync mount.
3. Push, confirm landed, **release the claim LAST**, set the status row to
   `idle`, and stop.

---

## 9. WHAT b33 PROVED vs LEFT UNPROVEN

**PROVED, driven or measured:**

* All 13 recoloured apps render, with their brand token resolving as intended;
  per-app table in §3.
* StoneDesk's `--surface-2` resolves to `#f0f4fb` at runtime and the
  `.biz-kpi` tiles paint it — b31's fix, visually confirmed for the first time.
* Zero fabricated KPIs observed across thirteen rendered dashboards.
* A working route optimiser exists at `35169ea2` and is **not** an ancestor of
  `main`; the archive did not preserve it.
* StoneDesk's two Field Map calls return **HTTP 401** against the real
  deployment, verified through `tools/sairn_http.py`.
* `tools/context_verify.py` is CORRECT and resolves the window unprompted
  once the prompt passes 200,000. §7 records my own misreading of it, caught
  by the `context-digest` push gate before it could be routed to cc as a
  defect.

**LEFT UNPROVEN, and none of it is recorded as checked:**

* **No app was authenticated into.** Every rendered verdict is display-forced.
  The auth paths, the session paths and the data paths are all untested here.
* **`GOOGLE_MAPS_API_KEY`'s state in Vercel was not checked.** The 401s prove
  the actions are refused, not that the key is missing.
* **The archived optimiser was read, not run.** It has never executed in this
  clone. Its `Math.max(0, …)` on `savedMinutes` is a defect the scope document
  corrects rather than inherits.
* **No contrast measurement was completed in the browser** — the gradient case
  defeated it and no finding is claimed either way.
* **The 4,420 ancestor-dependent UNRESOLVED pairs are unchanged.**
* **No keyboard, focus-order or screen-reader pass, in any app, ever.**
* **Everything carried in b32 §4** (cc's two Tier A function bodies and
  `tools/branch_census.py`; cody's `tests/sairnbuild_server_wins.js` check and
  the `bld_draws` no-arm gap; hank's api/ queue) **was not re-verified this
  batch and remains each owner's to report.**
