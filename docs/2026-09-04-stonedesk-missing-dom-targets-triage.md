# StoneDesk's 162 missing DOM targets — triaged

**2026-09-04 (Fourth).** Closes the index row that has read *"163 missing DOM
targets, never triaged"* since 2026-08-28. They are now triaged. **The headline
is that the list was never as bad as its size suggested, and the part that is
real is worse than the row implied** — it includes at least one button a
customer can click that silently does nothing.

Counts are as of this commit: `missing_dom_target_check.py` reported **162**
before this pass and **152** after it (160 after the Spend Report container,
152 after the Invoices retargeting below).

---

## The three classes that are NOT defects

Roughly a third of the list. Naming them matters, because a 162-line report
that nobody trusts is a report nobody reads — which is how this sat for a week.

### 1. Ids created by a builder that takes the id as an argument (8)

`da-len`, `da-dep`, `db-len`, `db-dep`, `dc-len`, `dc-dep`, `dd-len`, `dd-dep` —
the drawing tool's run dimensions. They are created by
`addNF('da-len', 'Run A — Length', 96)` and `addDepthNF(...)`, so the literal
`id="da-len"` never appears anywhere. **The checker searches for that literal.**

This is the same limitation `sairn-guardian-v2` documents for
`sairn_reachability_check.py`'s R3 detector, in a different tool: *a control
built from a JS template string exists nowhere a grep can read.* It applies
here too and is not written down anywhere until now.

`drawCTPreview()` (65 callers) and `calcDrawing()` (36 callers) read these on
every keystroke of the quote builder. If they were genuinely absent, the
drawing tool would not work at all — which is itself the cheapest way to
sanity-check a finding of this shape before acting on it.

### 2. Self-injecting containers (1)

`biz-ai-result`, read by `sdBizAI()`:

```js
var out=document.getElementById('biz-ai-result')||document.createElement('div');
if(!out.id){ out.id='biz-ai-result-injected'; …; document.getElementById('panel-business').appendChild(out); }
```

It creates its own container. Working as designed.

### 3. Dead code — 98 ids across 40 readers with zero callers and no wiring

`custSave`, `jcSaveJob`, `saveAlertSettings`, `dmgSave`, `saAnalyze`,
`bltnSave`, `sdRunEmailScan`, `commsSend`, `runEmailTriage`, `commsTpl`,
`commsAIDraft`, `pmImportCSV`, `pricingManagerOpen`, `photoBeforeAfter`,
`itaAddUser`, `vmAnalyze`, `sintAIAdvisor`, `piRunAnalysis`, `remakeAIAnalyze`,
`schedSetView`, `invSmartReorder`, `testAlertEmail`, `testAlertSMS`, and the
rest.

Unreachable by any user, so nothing is broken today — but this is exactly
Guardian's **Check 0d** situation, and 0d does not allow "leave it sitting
there": delete it, or quarantine it by name so that whoever wires it up later
knows it targets markup that does not exist. **Naming them here is the
quarantine.** They are file-size bloat against the 2MB ceiling and each one is
a trap for a future session that adds a nav entry.

---

## The part that is real: 60 ids read by reachable code

| reader | callers | wired to a control | absent ids |
|---|---:|:---:|---|
| `resetEmailTriage()` | 1 | **YES** | `email-paste-input`, `triage-input-zone`, `triage-results` |
| `esigCreateInvoice()` | 1 | **YES** | `inv-amount`, `inv-client`, `inv-desc` |
| `renderInventory()` | 10 | **YES** | `inv-low`, `inv-ok`, `inv-warn` |
| `showPage()` | 6 | **YES** | `main` |
| `getAIQuoteAdvice()` | 4 | **YES** | `messages` |
| `analyzeDocument()` | 0 | **YES** | `messages` |
| `sendMessage()` | 19 | **YES** | `userInput` |
| `s()` | 68 | no | `comms-kpi-*` (5), `inv2-*` (5), `safe-kpi-*` (5) |
| `sv()` | 85 | no | `dmg-kpi-*` (4), `nps-kpi-*` (5) |
| `npsSave()` | 2 | no | `nps-channel`, `nps-date`, `nps-feedback`, `nps-form`, `nps-project` |
| `intakeRender()` | 6 | no | `int-kpi-accepted`, `int-kpi-new`, `int-kpi-photos` |
| `remakeSave()` | 1 | no | `rm-cust`, `rm-mat`, `rm-type` |
| `renderCommsThreads()` | 1 | no | `comms-filter-cat`, `ctab-all` |
| `npsLog()` | 2 | no | `nps-date`, `nps-form` |
| `pmRenderOverrides()` | 5 | no | `pm-override-count`, `pm-overrides-list` |
| `renderTriageResults()` | 1 | no | `triage-input-zone`, `triage-results` |
| `renderThread()` | 3 | no | `comms-thread-list` |
| `renderHistory()` | 1 | no | `history-list` |
| `setMode()` / `addMessage()` / `sendToClaudeAndRender()` | 3 / 12 / 5 | no | `messages` |
| `bltnRender()` | 2 | no | `nps-score-btns` |
| `pmRenderCategoryDiscounts()` | 4 | no | `pm-category-discounts` |
| `pmRenderVendorDiscounts()` | 3 | no | `pm-vendor-discounts` |
| `renderSchedCrew()` / `renderSchedLanes()` | 2 / 2 | no | `sched-crew-board`, `sched-lanes` |
| `execAiSetTab()` | 1 | no | `triage-role` |
| `showApp()` | 9 | no | `uc` |

**`messages` and `userInput` are the legacy chat**, already flagged dead in the
file itself at `:12103` — *"a container that no longer exists anywhere in this
file"*. Several callers were already retargeted to `sdAIQuick()`;
`sendMessage()` and `analyzeDocument()` were not. **`showPage()`'s `main` is
null-guarded and harmless.**

Everything else in that table is a live code path writing to nothing.

---

## Fixed in this pass: the Vendor Spend Report

**A dead button that every existing tool passed.** The "📊 Spend Report" button
in the Vendors panel calls `vendorSpendReport()`, which computes the entire
report — vendor totals, category totals, month-by-month, YTD, realised savings —
and then writes it with:

```js
if(content) content.innerHTML = …
```

into `spend-report-content`, **which did not exist**. Null-guarded, so nothing
threw. A user clicked and nothing happened, with no error anywhere.

`vendorSpendAI()`, the button inside that report, then does an **unguarded**
`document.getElementById('vendor-spend-modal').style.display='none'`, which
threw a TypeError — after the AI hand-off had already run.

### Why no tool caught it, and this is the transferable part

- `sairn_dead_button_audit.py` reports **A=0** for this file. It checks that a
  handler is *defined* and that it is not toast-only. It does not check whether
  the handler's DOM target exists.
- `missing_dom_target_check.py` knew both ids were absent. It does not know a
  button is wired to them, so they sat in a 162-line list among 98 dead ones.

Neither tool is wrong. **The defect lives in the gap between them, and
`if(el)` is what turns the crash that would have exposed it into silence.**
That idiom is defensive against a *transient* null and is a silencer against a
*permanent* one, and nothing in the codebase distinguishes the two cases.

Only the container was missing — `vendorSpendReport()` builds every byte of the
inner HTML itself — so the fix is the container, marked
`data-auto-container="missing-dom-fix"`, the same marker `photo-ai-modal`
(`:6425`) carries from a previous instance of this class.

---

## What is left, in the order worth doing it

1. ~~**`esigCreateInvoice()`**~~ — **DONE 2026-09-04.** The fields were wrong,
   not the function: the panel was rebuilt as `inv2-*` and this was still
   writing to the old form. Retargeted, and it now opens the form (pre-filling
   one still behind `display:none` would have been the same no-op in a
   different disguise) and reports failure instead of toasting *"Invoice
   pre-filled with deposit amount"* over three blank fields. Two more defects
   in the same panel fell out of the same read: `invUpdateKPIs()` wrote all
   five of its figures to retired ids, so **Total Outstanding / Overdue / Open
   Invoices / Collected MTD had shown their hardcoded `$0 / $0 / 0 / $0` since
   the panel shipped** — a shop with real unpaid invoices was told it was owed
   nothing; and `invMarkPaid()` zeroed the balance *before* recording the
   payment, so every manual payment record said the customer paid **0**, which
   would also have held Collected MTD at zero forever. All three in
   `tests/invoice_panel_kpis.js`, 16 assertions.
2. **`renderInventory()`** — wired, 10 callers, and `inv-low` / `inv-ok` /
   `inv-warn` are stock-level counters. A live panel with three counters going
   nowhere. **Now the most likely next one**, and the Invoices result above is
   the reason to expect it is real: same shape, same cause, same panel-rebuild
   history.
3. ~~**`sendMessage()` / `analyzeDocument()`**~~ — **DONE 2026-09-04, and it was
   three live buttons rather than the one this line implied.**
   `safetyAIRootCause()`, `ecpGenerate()` and `safetyGenerateAttestation()` were
   all still routing through the dead chat, all wired, and **two of the three
   generate OSHA and Cal/OSHA compliance documents a shop is legally required to
   hold.** Each did `sbNav('ai')` and then `if(input){…sendMessage();}` against
   an element that no longer exists — so the panel opened and nothing happened.
   No request, no error, no message: an empty chat, which reads as *the AI had
   nothing to say* rather than *this button is not connected*. Retargeted to
   `sdAIQuick()`, matching the four earlier migrations. `sendMessage()` itself
   had the other half — `input.value.trim()` unguarded, throwing a TypeError for
   any caller that did reach it — and now reports instead of failing either way
   round. `tests/ai_shortcuts_reach_the_chat.js`, 17 assertions.
   `analyzeDocument()` targets `#messages`, part of the same removed chat, and
   is left for the deletion pass — it is the one remaining wired caller, and its
   fix is deletion rather than retargeting.
4. **The `s()` / `sv()` KPI clusters** — 24 ids across five panels (comms,
   inventory-2, safety, damage, NPS). Each needs its panel checked: a KPI
   element that was removed from the markup and left in the render is cosmetic;
   a whole KPI row that never rendered is a panel nobody has looked at.
5. **The 98 dead ids** — a deletion pass, sized against the 2MB ceiling. That is
   a scope/product call, not a bug fix.

## Recommended tool change, not made here

`missing_dom_target_check.py` should suppress class 1 by treating any id passed
as a string literal to a function that is not a known reader as *possibly
constructed*, and report those in a separate section rather than as MISSING.
That alone removes 8 findings and, more importantly, removes the reason to
distrust the other 154. Not done here because changing a Guardian tool's output
mid-audit would make this triage unreproducible.

---

## Follow-up pass, same day: the `s()` / `sv()` KPI clusters

Priority items 2 and 4 above, worked and **mostly closed as NOT the Invoices
defect.** Recording the negative result, because a prediction was made in the
previous commit and it was wrong.

**`renderInventory()` was predicted to be the same shape. It is not.** Its four
visible tiles (`inv-kpi1..4`: SKUs Tracked, Low Stock Items, Stock Value, Out of
Stock) are all written correctly on every render. `inv-low` / `inv-warn` /
`inv-ok` were three extra no-op writes left behind when that KPI row was
rebuilt, each appearing exactly once in the whole file. Removed; nothing else
changed. **The difference between this and Invoices is only visible in the
markup, not in the missing-id list** — which is the argument for checking the
panel rather than the report.

Same answer for **safety** (`safe-kpi1..5` all fed), **damage** (`dmg-open`,
`dmg-total-cost`, `dmg-recovered`, `dmg-ytd` all fed) and **NPS** (`nps-score`,
`nps-promoters`, `nps-passives`, `nps-detractors` all fed). The 24 ids in those
clusters are leftovers sitting beside live writes, not fabrication.

### One real finding: `comms-ai-gen`

A fifth visible tile in the Communications panel, labelled **"AI Drafted"**,
showing the hardcoded `0` from its own markup. **Nothing in the file ever wrote
it** — the id appeared exactly once, in that line. The only function that could
have fed it, `commsAIDraft()`, has zero callers and reads `msg-*` form ids that
do not exist, so the count could never have become anything but zero.

Guardian Check 0b, and the reason it read as real is that it sat beside four
tiles that *are* computed live. Removed rather than fed, per 0b's own rule:
feeding it means building the AI-drafting feature, and inventing a number for it
is the fabrication the check exists to stop.

### New, undocumented: a second complete DAMAGE module

Found while checking which function owned `dmg-kpi-*`. There are **two entire
damage-claim systems** in this file:

| | live module | orphan |
|---|---|---|
| storage key | `sd_damage` | `sd_damage_claims` |
| KPIs | `dmg-open`, `dmg-total-cost`, `dmg-recovered`, `dmg-ytd` | `dmg-kpi-*` (absent) |
| list target | `dmg-list` | **`dmg-list` — the same element** |
| entry point | `window.sdDmgAdd` | `dmgSave()` — zero callers |
| render | `render()` in its own IIFE | `dmgRender()` — reachable only from `dmgSave`, `dmgSetFilter`, `dmgUpdateStatus`, `dmgDelete`, **all of which have zero callers** |

**This is the same shape a previous session already found and documented for
NPS** at `:35905` — *"an orphaned parallel NPS-feedback system"*, whose dispatch
call that session removed. The damage twin was never written down.

**Nothing is broken today**, because every entry point into the orphan is
unreachable. The hazard is specific and worth stating: **both modules write
`dmg-list`.** Wiring up any one of those five functions — `dmgSetFilter()` looks
most like something a future session would connect to the panel's filter tabs —
makes the orphan's render overwrite the live claim list with its own empty
store. A shop would watch its damage claims vanish on a filter click.

Quarantined here by name per Check 0d. Deleting both orphans (damage and NPS) is
a sized cleanup, not a bug fix, and belongs with the 98-id deletion pass.
