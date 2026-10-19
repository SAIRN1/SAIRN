# HANDOFF — fourth / ted, batch b34, 2026-10-19

**READ THIS FILE ONLY.** It is the whole state.

**Written BEFORE the report, which is the standing instruction.**

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you mean
to quote, including out of this file.**

**FOUR THINGS TO READ FIRST:**

1. **ONE ITEM IS BLOCKED AND WAS FLAGGED BACK RATHER THAN WORKED AROUND.**
   `api/sd-data.js` is claimed by **cody** on b26. The routing primitive's
   single handler branch lives there. It is **not written**, it is **routed in
   full and pasteable**, and until it lands the endpoint cannot answer. §4.
2. **WRITING THE TIER ROWS FOUND A FAIL-OPEN SKIP IN THE TIER CHECKER.** Seven
   registered resources in `api/_resources/shared.js` have no row in the
   register and the completeness arm reports nothing about any of them,
   because `apps_with_registries()` skips that file by name. **Recorded, not
   closed.** §3.2.
3. **NOTHING LIVE WAS VERIFIED AND NOTHING LIVE IS CLAIMED.** The probe could
   not distinguish a registered resource from a nonsense one — both answer 401
   because the licence gate fires ahead of resource dispatch. §6.
4. **I TOUCHED ONE THING THE BATCH DECLARED NOT MINE, AND SAY SO IN §7** —
   StoneDesk's `fmRunOptimize` catch message, which is inside the function
   item 3 asked me to repoint. `fmRenderMap` and `api/bridge.js` were left
   alone.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\7114877e-14ff-4635-8129-799b043ea778.jsonl`
(the same session as b33 — a continuation, not a fresh window)

**Working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\7114877e-14ff-4635-8129-799b043ea778\scratchpad\b34\`
— `probe_routes.py` (the live probe that could not tell), `httpd.log`.

---

## 1. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| `HEAD` vs `origin/main` | **0 ahead, 0 behind — PUSHED AND LANDED** | `git rev-list --left-right --count origin/main...HEAD` |
| the four b34 commits | `f4208738` routing · `4153a2eb` regenerated derived docs · `13f5bf6d` Tier A review obligation · `e0007269` the gate's scrutiny row | `git log --oneline origin/main` |
| each confirmed on origin | all four pass `merge-base --is-ancestor` | — |
| **`api/sd-data.js`** | **NOT TOUCHED — 0 occurrences in the whole outgoing range** | `git diff --name-only 1c6e3acb..13f5bf6d \| grep -c api/sd-data.js` |
| uncommitted | **none** | `git status --porcelain` |
| `git stash` | **0** | `git stash list` |
| force push | **none** | — |
| `SAIRN_SKIP` / `GATE_EXEMPT` / `SAIRN_SEED_GATE` | **none used, any form** | — |
| `.claude/settings.json`, `.githooks/` | **not touched** | — |
| auditor clones | **not entered** | — |
| temporary worktree | created to test clean HEAD, **removed**; `git worktree list` shows no b34 entry | `git worktree list` |
| b34 manifest | `--new fourth b34 --items 6`; **5 done, 1 blocked** | `batch_manifest.py --check --agent fourth --batch b34` |

**TWO GATES REFUSED THIS PUSH AND BOTH WERE RIGHT.** Neither was overridden.

* **`derived-docs`** — a new registry module and a new test file made
  `docs/MASTER-PLAN.md` and `docs/traceability-matrix.md` stale. Regenerated
  with `python tools/master_plan.py` and
  `python tools/traceability_matrix.py` rather than hand-edited. Every moved
  figure is what the change implies: apps owning a resource 17 → 18, test files
  996 → 997, traced 771 → 772, declared fault probes 341 → 342, **traced rate
  unchanged at 77.4%**.
* **`tier-a`** — this change serves Tier A resources, so an independent-review
  obligation had to exist. **That refusal is the direct consequence of this
  batch's own item 1**: writing the rows is what made the code a Tier A change.
  Recorded via `tier_a_review_gate.py --open` and **assigned to cc**; the gate
  refuses any record whose reviewer is its own author, so I cannot discharge
  it.

---

## 2. CLAIMS HELD

**`fourth` holds one claim**, declaring exactly the files touched:

```
docs/CRITICALITY-TIERS.md  api/_lib/routes.js  api/_lib/routes.test.js
api/_resources/routes.js   api/_resources/index.js  sql/rt_routes_schema.sql
stonedesk.html  sairngrounds.html
docs/2026-10-19-fourth-b34-routing-phase1.md  docs/batch-manifest-fourth-b34.json
SAIRN-handoff/report/digest-fourth-b34
```

**Released at the end of this batch, LAST, after the push.**

**A NOTE ON HOW THAT CLAIM WAS WORDED, because it is a trap worth naming.** My
first attempt put `api/sd-data.js` in the task string as an explicit
*exclusion* — "NOT CLAIMED AND NOT TOUCHED: api/sd-data.js". **The matcher read
the path and refused the whole claim.** The fix was to declare only what I
would touch and put the exclusion in the status note instead. That is **not**
rewording to slip past the matcher (PR §4.3) — the task genuinely excluded that
file — but the two look identical from outside, so it is written down here
rather than left to be re-derived.

**Other active claims at the time of writing:** cc on `cc` (b22, wcag stems +
status board), cody on `platform` (b26, `api/sd-data.js` + tier reads), hank on
`hank` (b20, `api/_lib/law-roles.js`, `sairnlaw.html`).

---

## 3. ITEM 1 — THE TIER ROWS, WRITTEN BEFORE ANY CODE

**The claim record was checked first, as instructed, and the b33 flag had
lapsed.** `docs/CRITICALITY-TIERS.md` is in **nobody's** declared FILES list,
and `git status --porcelain docs/CRITICALITY-TIERS.md` in the **cody clone**
shows it unmodified there. So it was **CLEAR, not contended** — checked in two
independent ways rather than inferred from the claim tool alone.

### 3.1 The rows

`rt_routes` and `rt_stops`, both **Tier A / Confidentiality A**, in a new
`### routes` section. The argument, in one line: **`rt_stops` joins a street
address to a NAMED assignee and a DATE, which is a record of where an
identifiable person was at a known time** — the same class that took
`grd_cart_orders` and `leg_processions` from B to A. **Integrity is B on its
own merits** for both rows (operational scheduling, no money, no regulated
record); the A is inherited from the confidentiality axis under the stated
worse-of-the-two rule, and the rows say so rather than implying the money test
was met.

**It cannot be designed away.** An ordering with no addresses is not an
ordering, so the address is not incidental to the feature — it IS the feature,
and the only available response is to protect it.

### 3.2 Writing them found a fail-open skip — THIS IS THE REAL FINDING

The obvious home for a cross-app resource was `api/_resources/shared.js`.
**It would have been invisible there.** `apps_with_registries()` in
`tools/criticality_tier_check.py` skips that file by name:

```python
if app in ('index', 'shared'):
    continue
```

**Measured: all seven of its resources — `profile`, `memory`, `employees`,
`slabs`, `render_usage`, `shared_knowledge`, `employee_profile` — have no row
in the register, and the checker raises nothing about any of them.** The
completeness arm that caught `sairnsenior/sen_period_closings` reports CLEAN
over seven resources it was never shown, which reads exactly like a pass.

**Two of the seven are not obviously B:** `employees` is the cross-app HR
roster and `employee_profile` is a manager-set record about a named person.
**No tier is asserted for any of them** — that needs each read at its write
site. **Recorded in the register's gaps section as work; NOT closed.**

So `rt_routes`/`rt_stops` registered as their own `api/_resources/routes.js`,
inside the checker's enumeration. **`APPS_WITH_REGISTRIES` now reads 18 for 17
apps and that discrepancy is the point, not an error.**

### 3.3 A contradiction flagged and deliberately NOT fixed

`stonedesk/sd_field_stops` sits at **B / B** on the boilerplate *"Classified by
the stated B rule rather than individually read"*. It is StoneDesk's existing
Field Map stop store and it holds **the same shape `rt_stops` is A for**. Either
that row is wrong or these two are.

**Not retiered.** The honest answer needs a read of StoneDesk's own write site,
and a retier by analogy to a neighbouring row is the move this register exists
to stop. **The deciding test is written into the gaps section** so the next
reader does not re-derive the question.

### 3.4 Checker, before and after

```
before: RESOURCE_ROWS:391  TIER_A:276  PROBLEMS:6
after : RESOURCE_ROWS:393  TIER_A:278  PROBLEMS:4
```

**Zero new problems.** The two that went away are pre-existing HEADLINE drifts
in a sentence this edit had to move anyway — re-derived from the checker's own
`RESOURCE_ROWS`/`TIER_A`, not adjusted by the size of the edit. **A baseline run
on clean HEAD before any row was written read 391/276/115 against a stated
391/275/116, so one of the two figures corrected was already wrong when I
arrived.** The remaining **4 are not mine**: three `sairnscape` rollup drifts
and `sairnsenior/sen_period_closings` having no row.

---

## 4. ITEM 2 — THE MODULE IS DONE; THE DISPATCH IS BLOCKED

### 4.1 What landed

| file | what |
|---|---|
| `api/_lib/routes.js` | the module — pure core, injected edges |
| `api/_lib/routes.test.js` | **56 arms, 56 passing**, two sabotage controls |
| `sql/rt_routes_schema.sql` | **NOT RUN against Supabase** |
| `api/_resources/routes.js` + one line in `index.js` | the registry |

**It is a RECOVERY plus three corrections, not an invention.** `35169ea2`
(2026-06-18, never an ancestor of `main`) already had a nearest-neighbour over
Google Route Matrix drive times. The three corrections:

1. **`saved_seconds` is nullable and NULL MEANS NOT COMPUTED.** The original
   floored it at `Math.max(0, …)`, so an unmeasurable route and an
   already-optimal one both rendered *"0 min"*. §1 of the test suite drives
   both and proves they now differ.
2. **`basis` is a THREE-state answer.** `drive-matrix`, `great-circle`, and
   `unavailable` — where unavailable **leaves the stored order untouched and
   returns `order: null`**, so *unchanged* can never be read as *confirmed
   optimal*. Eight distinct `reason` values, because "could not optimise" with
   no reason is what sent a reader to the wrong environment variable.
3. **`locked`.** A real day has fixed appointments.

**Also deliberate:** no assumed speed appears anywhere in the file, so a
straight-line distance can never become a fabricated drive time; the
great-circle basis carries **no** `saved_seconds` at all.

### 4.2 What is blocked

**`api/sd-data.js` — cody holds it on b26.** `sairn_claim.py check` answers
**BLOCKED — same file or resource: api/sd-data.js**, and the tool's own
instruction is *"DO NOT start this. Flag it back."*

**The full handler branch is written out and pasteable** in
`docs/2026-10-19-fourth-b34-routing-phase1.md` §3, together with the
`extraActions` declaration that **must land WITH it and not before it** —
`api/_resources/index.js` asserts extra actions at load, so declaring
`optimize`/`upsert`/`reorder` with no handler would make the registry assert a
capability that answers 400.

---

## 5. ITEMS 3 AND 4 — BOTH CONSUMERS, DRIVEN IN A REAL BROWSER

**StoneDesk** `fmRunOptimize` repointed off the dead
`api/bridge.js?action=maps-optimize` onto `sdData('optimize','rt_routes')`,
which already carries the licence, the session token, the 15 s abort signal and
the failure reporter.

**SAIRNgrounds** gets a *Route order for a crew's day* card on the Scheduling
panel, sending **its own shape** — `grd_schedule` crew + `next`, addresses off
`grd_properties`. **That is what proves the module is shared rather than
StoneDesk-shaped**: two different app data models, one `{job_ref, address,
locked, status}` seam.

**Driven live in Chrome over every answer path**, with a stubbed transport:

| path | StoneDesk | SAIRNgrounds |
|---|---|---|
| `unavailable` | toast names the reason, *"Your stop order is unchanged"* | *"Not reordered — no routing key is configured on the server"* |
| `drive-matrix` | banner *"saves ~10 min"*, stored order reversed | table reordered, *"saves about 9 min"* |
| **`saved_seconds: null`** | banner *"route updated."* — **no time claim at all** | **"drive-time saving not computed"** |
| `great-circle` | *"(straight-line order; drive times were unavailable)"* | explicit straight-line note with the reason |
| no response | *"the server did not answer"* | *"Nothing was changed"* |

**And SAIRNgrounds' exclusion path:** a scheduled visit whose property has no
address is **listed as excluded by name**, never silently dropped — the same
rule the Pace of Play panel already applies to incomplete holes.

`checkblocks`: **stonedesk 131 blocks / 0 failed**, **sairngrounds 5 / 0**.

---

## 6. WHAT IS NOT VERIFIED — STATED, NOT SOFTENED

**The live probe could not answer the question, and the controls are what prove
it.** Via `tools/sairn_http.py` against the deployed `api/sd-data`:

```
rt_routes           -> 401 NO_LICENSE
rt_stops            -> 401 NO_LICENSE
employees           -> 401 NO_LICENSE   (control: definitely exists)
zzz_not_a_resource  -> 401 NO_LICENSE   (control: definitely does not)
```

**Both controls answer identically.** The licence gate fires ahead of resource
dispatch, so an unauthenticated probe cannot distinguish registered from
unregistered **in either direction**. Going further means entering a real
licence key, which this session does not do.

**So no live verification of items 3 or 4 is claimed.** Closing condition 3
from the blockers page is **still open**.

**`sql/rt_routes_schema.sql` HAS NOT BEEN RUN.** Both tables are absent from
Supabase, so even with the handler branch applied the endpoint would answer
`provisioned: false`.

**Pre-existing, verified against a clean-HEAD worktree rather than assumed:**
`api/_resources/extra-actions.test.js` is **41 passed / 7 failed both with and
without my change — the same seven `sc_` arms, compared by name.**

---

## 7. ONE THING TOUCHED THAT THE BATCH DECLARED NOT MINE

The instruction placed *"StoneDesk's two wrong Field Map error messages"* out of
scope as `api/`, hank's lane. **Two corrections, offered rather than assumed:**

1. **Those messages are not in `api/`.** They are in `stonedesk.html`, at the
   `.catch` arms of `fmRunOptimize` (`:12944`) and `fmRenderMap` (`:12818`).
2. **One of them is inside the function item 3 asked me to repoint.** Changing
   where `fmRunOptimize` sends its request necessarily rewrites its catch arm.
   Leaving the old text would have meant a call to the *new* endpoint failing
   under a message about a Maps API key that is now doubly irrelevant.

**`fmRenderMap` was NOT touched** — it still names `GOOGLE_MAPS_API_KEY` and
still calls the dead bridge action. **`api/bridge.js`'s
unknown-`?action=`-reaches-a-WRITE hazard was NOT touched** — that is the real
`api/` item and it remains routed to hank, unclaimed and unstarted.

---

## 8. ITEM 5 — NOT STARTED, AND THE REASON

The pixel-sampling contrast resolver was the explicit *if time allows* item.
**Its natural home is `tools/wcag_contrast_check.py`, which cc holds on an
active b22 claim**, so it would have to land either in that file or as a second
tool duplicating its criteria lock. **Neither was attempted** — this is
not-started, not partially-applied.

The b33 finding it would act on is unchanged and re-derivable: a computed-style
read returns **1.07:1** on StoneDesk's gate because the colour lives in
`linear-gradient(135deg, rgb(27,58,107), rgb(42,82,152))` while
`backgroundColor` is `rgba(0,0,0,0)`.

**Next step:** agree with cc whether the resolver goes in their file or a
sibling, then sample rendered pixels rather than computed style.

---

## 9. EXACT NEXT STEP, PER ITEM

1. **cody** (or whoever next holds `api/sd-data.js`): paste the branch and the
   `extraActions` line from `docs/2026-10-19-fourth-b34-routing-phase1.md` §3.
   Nothing else in that file changes.
2. **Michael:** run `sql/rt_routes_schema.sql` in the Supabase SQL editor.
3. **After 1 and 2:** live-verify against the deployed URL with a real session.
   That is the only open closing condition for Blocker C.
4. **cc:** discharge the Tier A review obligation on `rt_routes`/`rt_stops`.
   The record names what to attack first and in what order.
5. **Anyone:** the seven untiered `shared.js` resources (§3.2), and
   `sd_field_stops` at B/B against `rt_stops` at A/A (§3.3).
6. **hank:** `api/bridge.js`'s write-hazard; `fmRenderMap`'s message and the
   `maps-static` decision.
7. **fourth or cc:** item 5, the gradient contrast resolver (§8).

---

## 10. WHAT b34 PROVED vs LEFT UNPROVEN

**PROVED, driven or measured:**

* The tier rows are in and **mechanically enforced** — checker rows 391 → 393,
  `TIER_A` 276 → 278, `PROBLEMS` 6 → 4 with zero new problems.
* Seven `shared.js` resources are untiered and invisible to the checker.
* `node api/_lib/routes.test.js` → **56 passed, 0 failed**, including two
  controls that fail if the defects are reinstated.
* Both consumers behave correctly across all five answer paths **in a real
  browser**, including `saved_seconds: null` rendering no claim at all.
* `checkblocks`: stonedesk **131/0**, sairngrounds **5/0**.
* `api/sd-data.js` is untouched across the entire outgoing range — **0**.
* `extra-actions.test.js`'s 7 failures are pre-existing, compared by arm name
  against a clean-HEAD worktree.

**LEFT UNPROVEN, and none of it is recorded as checked:**

* **Nothing live.** The probe cannot tell registered from unregistered; both
  controls answer 401.
* **The schema has never been run.** No table exists.
* **The pasteable handler branch in §3 of the routing doc is covered by no
  suite** — it is not applied, so nothing executes it. It is the least-tested
  artefact this batch produced and it is the one somebody will paste.
* **`sd_field_stops` vs `rt_stops`** — one of the two tiers is wrong and which
  is not established.
* **No keyboard, focus-order or screen-reader pass**, in any app, ever.
* **The seam check reported COULD NOT TELL** for at least one endpoint/engine
  pair on this push; nothing about that seam was verified.
