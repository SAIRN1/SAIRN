# StoneDesk — Session 73 Handoff

Written at a natural stopping point after the reachable-and-broken cleanup
pass. Claims below are independently verified against the actual repo and
live site, not assumed from memory — same standard as prior sessions in
this series.

## 1. Verified current state

- `main` HEAD (local and `origin/main`, confirmed matching): `4ad8929`
- Two commits this session (both pushed and live-verified):
  - `297ae20` — deleted 10 orphaned duplicate feature clusters (AP,
    Equipment, Employee Directory, Stone Yard Contacts, Subcontractor
    Mgmt, Bid Board, Training, Waste Tracker, HISTORY v2, plus the
    earlier CRM/exec-pipeline retarget), built 24 confirmed-real missing
    containers, retargeted `taxRender`/`sdTaxCalc`/`sdTaxPrint` off the
    deleted `apBills` onto the real `sd_ap` data.
  - `4ad8929` — built the Customer kanban toggle and the Admin-panel
    pricing-formula backtest tool, deleted the unbuilt QuickBooks
    integration.
- Local checks re-run fresh at this HEAD: `checkblocks.py` 118/118,
  `div_balance_check.py` 4529/4529 balanced, `nav_panel_check.py` 61/61
  PASS, `panel_nesting_check.py` 0/61 trapped, `duplicate_global_check.py`
  0 duplicates, `key_collision_check.py` unchanged at 4 (all pre-existing,
  traced and confirmed benign in `STONEDESK-SESSION72-HANDOFF.md` §3).
- `missing_dom_target_check.py` (extended this session to also resolve
  the `sv(id,v)` forwarding helper, previously a blind spot): 227 missing
  targets remain, down from 363 at the start of this session's cleanup.

## 2. What was CORRECTED, not just added

- The original scanner-reported "140 reachable-and-broken, 233 dormant"
  split (from extending `missing_dom_target_check.py`) had two real bugs
  in the triage script itself: an anonymous-IIFE misattribution (scope
  tracer grabbed the nearest *named* function textually instead of
  recognizing a self-executing `(function(){...})()`, so `nps-score-btns`
  showed as owned by `tmplRender`) and a comment-text false-positive
  (the reachability check matched function-name substrings inside `//`
  comments, so `npsLog` showed reachable when the *only* other mention
  of `npsLog(` in the file was inside a comment). Both fixed; corrected
  split was 130 reachable / 233 dormant, then 125 after excluding the
  already-known-dead NPS cluster (5 items) per `7c742bb`.
- Of the "40 confirmed-real" containers reported as safe to build, 3
  clusters turned out to be a **third** false-positive class: self-
  referential orphan clusters where every function calls another function
  in the same dead group, none of them reachable from any real UI —
  `fmRenderMyDay/Overview/Pipeline` (`fmSwitchTab`, the only entry point,
  has zero callers anywhere) and `renderCustKanban` (`custToggleView` had
  zero callers, now fixed — see §4). `qboLog` and `parseAndStress` and
  `safetyRenderChecklist` were excluded for a different, simpler reason:
  no panel/nav housing exists for them at all, confirmed via full-file
  grep, not assumed.
- One real deletion was caught and reverted **before** it was committed:
  Job Costing (`jcRender`/`jcJobs`/`jcAIAnalyze`) was initially treated as
  a 10th duplicate cluster, but `jc-list`/`jc-ai-result` and a real
  "Analyze My Job Margins" button already existed live in the canonical
  panel — this was a genuinely live secondary feature, not a duplicate.
  Restored before commit.
- Execution testing (not static checks) caught a real cross-cluster
  regression: deleting the AP orphan broke `taxRender`/`sdTaxCalc`/
  `sdTaxPrint`, which all read `apBills` for expense totals. Retargeted
  to the real `sd_ap` data instead of restoring the duplicate — see
  `297ae20`'s commit message for detail.

## 3. Open items, prioritized — QUARANTINED, not touched further tonight

1. **Field Map "My Day / Overview / Pipeline" system**
   (`fmRenderMyDay`/`fmRenderOverview`/`fmRenderPipeline` + 25 supporting
   functions, ~470 lines, `sd_field_stops`/`sd_field_order` storage).
   Real, working, sophisticated logic — per-crew daily stop lists with
   manual reordering, a multi-day pipeline view, route-optimization
   (`fmOptimizeDay`/`fmRunOptimize`), day-summary generation. Genuinely
   more capable in places than the real, live dispatch board
   (`sdFieldmapRender`) it sits beside. Zero UI exists: no tab bar, no
   view containers, its sole entry point (`fmSwitchTab`) has no caller
   anywhere in the file. **Not safe to delete** (real logic + real data,
   would lose genuine capability) and **not safe to build casually**
   (full tab UI, three views, nothing execution-tested yet). Same shape
   as the Vendor Ordering Catalog decision from `STONEDESK-SESSION72`.
   **Needs its own scoped session** — a real build/delete call, not a
   mechanical fix.
2. **Safety panel 5-tab system**
   (training/checklist/incidents/equipment/ecp — `safetyRenderChecklist`
   plus siblings for all 5 tabs). Bigger than the 2 ids originally
   flagged: **none** of the 5 tabs have any real `safety-tab-*` view
   container or `stab-*` tab button anywhere in the file, not just
   checklist. Sits beside a smaller, real, working Safety panel
   (`sdSafetyAdd`, incident logging, KPIs) that IS live. Checked for a
   duplicate-storage risk (the AP/CRM pattern): **none found** —
   `sdSafetyData` reads/writes the same `sd_safety` key the real panel
   uses, so this looks like the intended fuller expression of already-
   shared data (training/inspections/checklists/ecp fields the simple
   panel doesn't surface), not a wasteful duplicate. **Recommend: build**,
   but scoped as its own multi-tab project — a 5-tab UI build is closer
   in size to the Field Map item than to the small fixes done tonight.
3. **QuickBooks integration** — resolved this session (deleted, `4ad8929`).
   Listed here only so it isn't rediscovered as if still open: no panel/
   nav ever existed for it, confirmed via grep, no live product ask.
   If QuickBooks integration becomes a real ask, it's a fresh feature
   scope, not a "finish this" job — nothing usable was left behind.
4. **Vendor Ordering Catalog / CRM pipeline split** — carried forward
   unchanged from `STONEDESK-SESSION72-HANDOFF.md` §4 items 1 (Vendor)
   and the CRM item is now resolved (`855e360` retargeted the Exec
   Dashboard's Pipeline Funnel to the real `sd_crm` data and deleted the
   `crmLeads` orphan). Vendor Ordering Catalog itself: still untouched,
   still real multi-session scope, not re-estimated this session.
5. **`sd_slabs`/`sd_slab_tracker` unification**, **third quote-history
   store** (`stonedesk_quote_history`), **`saveSDProfile()` zero-caller
   status**, **`sairn-toast` duplicate DOM id** — carried forward
   unchanged from `STONEDESK-SESSION72-HANDOFF.md` §4 items 3-6, not
   examined this session.
6. **`missing_dom_target_check.py`'s remaining gap**: still string-
   literal-only (can't resolve `getElementById(someVariable)` or
   template-literal ids) — same accepted limitation as
   `key_collision_check.py`. The `sv()` forwarding-helper blind spot
   flagged in `STONEDESK-SESSION72` §4 item 9 is now fixed (this
   session). 227 remaining missing targets have NOT been individually
   triaged reachable-vs-dormant this session — that work stopped at the
   125-item (post-NPS-exclusion) working set, not the full 227.

## 4. This session's actual builds (not quarantined — done)

- `renderCustKanban`: built `cust-view-btn` toggle button +
  `cust-kanban`/`cust-kanban-cols` containers on the Customers panel.
  Live-tested: toggles correctly, populates real customer data by stage.
- `parseAndStress`: built a "Pricing Formula Backtest" card under
  Admin & Settings (deliberately not main nav — shop-owner/admin tool,
  not customer-facing), CSV upload + "Load Sample Data" button, reusing
  the function's existing `stress-metrics`/`stress-table` output targets.
  Live-tested: sample data produces real formula-vs-actual output.

## 5. Standard verification reminder for whoever reads this next

Verify `main` HEAD and `origin/main` match, re-run the local checks, and
live-verify against `sairn.vercel.app/stonedesk` before trusting any
specific claim above — including this one. In particular: re-confirm
Field Map and the Safety 5-tab system are still quarantined (not
accidentally built or deleted piecemeal) before picking either up, and
re-verify the "no duplicate-storage risk" finding on Safety still holds
if anything in `sd_safety`'s shape changes before that work starts.
