# SAIRNbuild AI Budget Early Warning — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic 70/80/90% cost-overrun tier detection onto the
existing, live Job Costing panel in `sairnbuild.html`, surfaced on that
panel and on the Dashboard's existing "Needs Attention" list.

**Architecture:** Two new pure functions (`costLineTier`, `jobTierFromCosts`)
compute tiers from data `costs()`/`jobs()` already return — no new
Supabase table, no new fetch, no API call in the core feature. Two
existing render functions (`rCostTbl()`, `rDash()`) are extended to call
them and display the result, following each function's own existing
patterns rather than introducing new ones.

**Tech Stack:** Vanilla JS, single-file HTML (`sairnbuild.html`), no
build step, no test runner — this codebase's verification discipline is
`node --check` / `tools/checkblocks.py` (or the repo's live extraction
script) + div-balance + dead-button audit + real browser interaction
testing, not pytest/jest. Task 2's pure functions are the one part of
this plan genuinely unit-testable in isolation (no DOM); Tasks 3-4 use
this codebase's real verification method instead of a foreign template.

## Global Constraints

- No new Supabase table, no new persistence, no API call in the core
  feature (spec §2).
- `committed + actual`, not `actual` alone, is the ratio's numerator
  (spec §3).
- Tiers: `>=0.90` critical, `>=0.80` warning, `>=0.70` watch, else none
  (spec §3).
- Job-level tier = highest tier among that job's own cost lines, OR-
  rollup, not an average (spec §3).
- No push/toast notification (spec §2) — Dashboard visibility only.
- New tier colors must not reuse `--p`/`--warn` (both `#F59E0B`) or
  `--danger` (`#EF4444`) — three new custom properties (spec §6):
  `--tier-watch:#2563EB`, `--tier-warning:#7C3AED`, `--tier-critical:#991B1B`.
- Guardian pass (syntax, div-balance, dead-button audit, no forbidden
  patterns) before any push, same as every other change tonight — see
  Task 3/4's verification steps for the exact commands this repo uses.

## Deviation from spec — flagged for review before Task 4

**Spec §5 (Role gating) is not implementable as written.** The spec says
job-level tier/dollar figures should be "PM/owner/exec only, matching
the existing financial-data role gating already used elsewhere in the
platform." Checked directly: `sairnbuild.html` has **no per-employee
role system at all** — only a single whole-app license-key gate
(`#gate`, `bldLicenseKey()`), unlike SAIRNgrounds/SAIRNscape/StoneDesk,
which have real `_ROLE_KEY` per-employee auth. Building one is a
separate, much larger project, not part of this feature.

**Resolution used in this plan:** no new gating is added. Job-level tier
and dollar figures get exactly the same visibility Job Costing's budget/
committed/actual figures already have today (fully open to anyone who
opens the panel) — consistent with current reality rather than a
partial/fake gate that implies a security boundary that doesn't exist.
**This needs your explicit confirmation before Task 4 (Dashboard
integration) starts** — if you'd rather block this feature on building
real role gating first, say so and this plan pauses there.

## Refinement found while reading the real code — Dashboard integration

Spec §4 said "one new KPI" on Dashboard. Reading `rDash()` (line 3910)
shows the codebase already has an established mechanism for exactly this
kind of cross-cutting flag: the `att` array feeding `#d-attention`
("Needs Attention"), which blocked jobs, thin-margin jobs, and expiring
compliance certs already use — none of those are separate KPI tiles.
**Task 4 uses that existing pattern** (push at-risk jobs into `att`)
instead of adding a 6th KPI tile to the `krow`, since duplicating an
existing "attention list" mechanism as a new KPI would be the kind of
inconsistent, unnecessary addition this plan should avoid. Flagged here
since it's a real deviation from the literal spec wording, made for a
concrete reason, not silently.

---

### Task 1: Tier color CSS variables

**Files:**
- Modify: `sairnbuild.html:8` (the `:root{...}` line)

**Interfaces:**
- Produces: three new CSS custom properties — `--tier-watch`,
  `--tier-warning`, `--tier-critical` — consumed by Tasks 3 and 4 as
  `var(--tier-watch)` etc. in inline `style="color:..."`/
  `background:...` attributes, same convention this file already uses
  for `var(--danger)`/`var(--ok)`/`var(--warn)`.

- [ ] **Step 1: Edit the `:root` line**

Current line 8:
```css
:root{--p:#F59E0B;--pd:#B45309;--pt:#FFFBEB;--pb:#FCD34D;--bg:#F8FAFC;--card:#fff;--border:#E2E8F0;--text:#0F172A;--muted:#64748B;--danger:#EF4444;--warn:#F59E0B;--ok:#22C55E;--sh:0 1px 4px rgba(0,0,0,.08);}
```
New line 8:
```css
:root{--p:#F59E0B;--pd:#B45309;--pt:#FFFBEB;--pb:#FCD34D;--bg:#F8FAFC;--card:#fff;--border:#E2E8F0;--text:#0F172A;--muted:#64748B;--danger:#EF4444;--warn:#F59E0B;--ok:#22C55E;--sh:0 1px 4px rgba(0,0,0,.08);--tier-watch:#2563EB;--tier-warning:#7C3AED;--tier-critical:#991B1B;}
```

- [ ] **Step 2: Verify syntax**

Run: `python tools/checkblocks.py sairnbuild.html` (or this repo's
current equivalent extraction script — confirm the actual script name/
location hasn't changed since tonight's SAIRNgrounds/SAIRNscape work
before assuming `tools/checkblocks.py` is still current).
Expected: `FAILED_BLOCKS:0`, same as every other file tonight — CSS
edits inside a `<style>` block don't run through this JS-syntax check,
but confirm no adjacent script block broke from the edit.

- [ ] **Step 3: Visual check — Critical vs existing danger red**

Real check, not a hex-distance assumption (spec §6 flags this
explicitly): open `sairnbuild.html` in a browser, use the browser
devtools color picker or a quick inline `getComputedStyle` check to
render `#991B1B` and `#EF4444` as adjacent swatches. Confirm they read
as clearly different colors at a glance, not just different hex values.
If they don't, this is the point to pick a different Critical value
before Task 3 starts using it everywhere.

- [ ] **Step 4: Commit**

```bash
git add sairnbuild.html
git commit -m "feat: add tier color variables for AI Budget Early Warning"
```
(Standing project rule: use the GitHub REST API blob→tree→commit→ref
push method already established tonight, not a raw `git push` — see
`tools/gh_push.py`. `git commit` here is fine for the local commit
step; the actual push to `origin/main` follows this project's own
protocol, not a plain `git push`.)

---

### Task 2: Pure tier-computation functions

**Files:**
- Modify: `sairnbuild.html` — add near the existing `costScope()`
  function (line 3806), before `rCostTbl()` (line 3811).
- Test: standalone Node script (temporary, scratchpad — this codebase
  has no permanent test suite; the verification step below is the real
  check, not a committed test file).

**Interfaces:**
- Consumes: a cost-line object shape already used throughout this file
  — `{budget, committed, actual, job_id, cost_code, kind, ...}` (see
  `costScope()`/`rCostTbl()` for the exact shape already in use).
- Produces:
  - `costLineTier(c)` → `'critical' | 'warning' | 'watch' | null`
  - `jobTierFromCosts(jobId, allCosts)` → `'critical' | 'warning' | 'watch' | null`
  - Both consumed by Task 3 (`rCostTbl()`) and Task 4 (`rDash()`).

- [ ] **Step 1: Write the standalone verification script**

Save to scratchpad (not committed) as `tier_test.js`:
```javascript
function costLineTier(c){
  var budget=c.budget||0;
  if(budget<=0)return null;
  var ratio=((c.committed||0)+(c.actual||0))/budget;
  if(ratio>=0.90)return 'critical';
  if(ratio>=0.80)return 'warning';
  if(ratio>=0.70)return 'watch';
  return null;
}
function jobTierFromCosts(jobId, allCosts){
  var order={critical:3,warning:2,watch:1};
  var best=null;
  allCosts.filter(function(c){return c.job_id===jobId;}).forEach(function(c){
    var t=costLineTier(c);
    if(t&&(!best||order[t]>order[best]))best=t;
  });
  return best;
}

function assertEq(actual, expected, label){
  if(actual!==expected){
    console.error('FAIL: '+label+' -- got '+JSON.stringify(actual)+', expected '+JSON.stringify(expected));
    process.exitCode=1;
  } else {
    console.log('PASS: '+label);
  }
}

// costLineTier boundary tests
assertEq(costLineTier({budget:1000,committed:0,actual:0}), null, '0% -> null');
assertEq(costLineTier({budget:1000,committed:699,actual:0}), null, '69.9% -> null');
assertEq(costLineTier({budget:1000,committed:700,actual:0}), 'watch', 'exactly 70% -> watch');
assertEq(costLineTier({budget:1000,committed:799,actual:0}), 'watch', '79.9% -> watch');
assertEq(costLineTier({budget:1000,committed:800,actual:0}), 'warning', 'exactly 80% -> warning');
assertEq(costLineTier({budget:1000,committed:899,actual:0}), 'warning', '89.9% -> warning');
assertEq(costLineTier({budget:1000,committed:900,actual:0}), 'critical', 'exactly 90% -> critical');
assertEq(costLineTier({budget:1000,committed:1200,actual:0}), 'critical', '120% -> still critical, no separate "over" state');
assertEq(costLineTier({budget:1000,committed:500,actual:250}), 'watch', 'committed+actual summed: 750/1000=75% -> watch');
assertEq(costLineTier({budget:0,committed:500,actual:0}), null, 'zero budget -> null, not a divide-by-zero crash');

// jobTierFromCosts rollup tests
var mixedCosts=[
  {job_id:'J1',budget:1000,committed:500,actual:0},   // watch-adjacent, 50% -> null
  {job_id:'J1',budget:1000,committed:850,actual:0},    // 85% -> warning
  {job_id:'J1',budget:1000,committed:950,actual:0},    // 95% -> critical
  {job_id:'J2',budget:1000,committed:750,actual:0}     // 75% -> watch
];
assertEq(jobTierFromCosts('J1', mixedCosts), 'critical', 'job with mixed lines rolls up to the WORST tier (critical), not an average');
assertEq(jobTierFromCosts('J2', mixedCosts), 'watch', 'single-line job matches that line\'s tier');
assertEq(jobTierFromCosts('J3', mixedCosts), null, 'job with no cost lines -> null, no crash');
```

- [ ] **Step 2: Run it, confirm every line prints PASS**

Run: `node tier_test.js` (from the scratchpad directory)
Expected: 13 `PASS:` lines, exit code 0. Any `FAIL:` line means the
function implementation (copied into `sairnbuild.html` in Step 3) needs
to change before proceeding — this script is the source of truth for
the two functions' exact behavior at every boundary.

- [ ] **Step 3: Copy the verified functions into `sairnbuild.html`**

Insert immediately before `function rCostTbl(){` (currently line 3811):
```javascript
// AI Budget Early Warning -- deterministic, zero API calls (spec: no AI
// call for what arithmetic already computes reliably). committed+actual,
// not actual alone, per spec section 3: "early" means before the money
// moves, not after.
function costLineTier(c){
  var budget=c.budget||0;
  if(budget<=0)return null;
  var ratio=((c.committed||0)+(c.actual||0))/budget;
  if(ratio>=0.90)return 'critical';
  if(ratio>=0.80)return 'warning';
  if(ratio>=0.70)return 'watch';
  return null;
}
var TIER_LABEL={critical:'Critical',warning:'Warning',watch:'Watch'};
var TIER_COLOR={critical:'var(--tier-critical)',warning:'var(--tier-warning)',watch:'var(--tier-watch)'};
// Job-level = the WORST tier among that job's own lines (OR-rollup, not
// an average) -- a job with one critical line is a critical job, even
// if its other lines are fine.
function jobTierFromCosts(jobId, allCosts){
  var order={critical:3,warning:2,watch:1};
  var best=null;
  allCosts.filter(function(c){return c.job_id===jobId;}).forEach(function(c){
    var t=costLineTier(c);
    if(t&&(!best||order[t]>order[best]))best=t;
  });
  return best;
}
```

- [ ] **Step 4: Verify syntax**

Run: `python tools/checkblocks.py sairnbuild.html`
Expected: `FAILED_BLOCKS:0`.

- [ ] **Step 5: Commit**

```bash
git add sairnbuild.html
git commit -m "feat: add costLineTier/jobTierFromCosts pure functions for budget overrun detection"
```

---

### Task 3: Job Costing panel integration

**Files:**
- Modify: `sairnbuild.html:679` (table header)
- Modify: `sairnbuild.html:3835-3847` (row rendering inside `rCostTbl()`)
- Modify: `sairnbuild.html:3857-3863` (`#c-rollup` rendering)
- Modify: `sairnbuild.html:664` (the "Lines Over" KPI tile, repurposed)
- Modify: `sairnbuild.html:3817,3822,3827-3828` (the `over`/`c-over`
  computation feeding that tile)

**Interfaces:**
- Consumes: `costLineTier(c)`, `TIER_LABEL`, `TIER_COLOR` from Task 2.
- Produces: no new function names — this task only changes what
  `rCostTbl()` (already called by `rCost()`, already wired to
  `nav('jobcost')`) renders. Nothing outside this panel depends on
  this task's internals.

- [ ] **Step 1: Add the Tier column header**

Current line 679:
```html
<div class="tw"><table><thead><tr><th>Job</th><th>Cost Code</th><th>Kind</th><th>Vendor / Crew</th><th>Budget</th><th>Committed</th><th>Actual</th><th>Variance</th><th>Actions</th></tr></thead>
```
New line 679:
```html
<div class="tw"><table><thead><tr><th>Job</th><th>Cost Code</th><th>Kind</th><th>Vendor / Crew</th><th>Budget</th><th>Committed</th><th>Actual</th><th>Variance</th><th>Tier</th><th>Actions</th></tr></thead>
```

- [ ] **Step 2: Add the tier badge cell to each row**

Current (lines 3835-3847):
```javascript
    tb.innerHTML=list.map(function(c){
      var v=(c.budget||0)-(c.committed||0);
      var col=v<0?'var(--danger)':'var(--ok)';
      return '<tr><td>'+H(jobLabel(c.job_id))+'</td>'+
        '<td><strong>'+H(c.cost_code)+'</strong></td>'+
        '<td>'+H(KIND[c.kind]||c.kind||'')+'</td>'+
        '<td>'+H(c.vendor||'')+'</td>'+
        '<td>'+fmt(c.budget)+'</td>'+
        '<td>'+fmt(c.committed)+'</td>'+
        '<td>'+fmt(c.actual)+'</td>'+
        '<td><strong style="color:'+col+'">'+(v<0?'-':'')+fmt(Math.abs(v))+'</strong></td>'+
        '<td><button class="btn bo bs" onclick="editCost(\''+H(c.id)+'\')">Edit</button></td></tr>';
    }).join('');
```
New:
```javascript
    tb.innerHTML=list.map(function(c){
      var v=(c.budget||0)-(c.committed||0);
      var col=v<0?'var(--danger)':'var(--ok)';
      var tier=costLineTier(c);
      var tierCell=tier?('<span class="badge" style="background:'+TIER_COLOR[tier]+';color:#fff">'+TIER_LABEL[tier]+'</span>'):'<span style="color:var(--muted)">--</span>';
      return '<tr><td>'+H(jobLabel(c.job_id))+'</td>'+
        '<td><strong>'+H(c.cost_code)+'</strong></td>'+
        '<td>'+H(KIND[c.kind]||c.kind||'')+'</td>'+
        '<td>'+H(c.vendor||'')+'</td>'+
        '<td>'+fmt(c.budget)+'</td>'+
        '<td>'+fmt(c.committed)+'</td>'+
        '<td>'+fmt(c.actual)+'</td>'+
        '<td><strong style="color:'+col+'">'+(v<0?'-':'')+fmt(Math.abs(v))+'</strong></td>'+
        '<td>'+tierCell+'</td>'+
        '<td><button class="btn bo bs" onclick="editCost(\''+H(c.id)+'\')">Edit</button></td></tr>';
    }).join('');
```
Note: confirm `.badge` is an existing CSS class in this file (used
elsewhere for status pills, e.g. Change Orders' `COSTATUS` badges at
line 3709) before assuming this inline-style approach matches file
convention — if `.badge` already sets a background color via a class
modifier (like `.bg`/`.br`/`.bx` seen in `COSTATUS`), prefer adding
three new modifier classes (`.tier-watch`/`.tier-warning`/`.tier-critical`
in the `<style>` block) instead of inline `style=` on the badge, to
match how every other badge in this file is styled. Check this before
writing the code, don't assume the inline-style version above is final.

- [ ] **Step 3: Fix the Cost Code Roll-up's color logic to use the new tiers**

Current (lines 3857-3863):
```javascript
  $('c-rollup').innerHTML=keys.length?keys.map(function(k){
    var b=byCode[k].budget,cm=byCode[k].committed;
    var pct=b>0?Math.round(cm/b*100):0;
    var col=cm>b?'var(--danger)':pct>90?'var(--warn)':'var(--ok)';
    return '<div class="srow"><span class="slbl">'+H(k)+'</span><span class="sval" style="color:'+col+'">'+fmt(cm)+' / '+fmt(b)+' &middot; '+pct+'%</span></div>'+
      '<div class="pbar"><div class="pfill" style="width:'+Math.min(100,pct)+'%;background:'+col+'"></div></div>';
  }).join(''):'<div style="color:var(--muted);text-align:center;padding:12px;">No cost lines in scope</div>';
```
New (reuses `costLineTier` against a synthetic per-code aggregate line,
so the roll-up's severity coloring is driven by the exact same tier
logic as every other part of this feature, not a second, separately-
maintained threshold):
```javascript
  $('c-rollup').innerHTML=keys.length?keys.map(function(k){
    var b=byCode[k].budget,cm=byCode[k].committed;
    var pct=b>0?Math.round(cm/b*100):0;
    var tier=costLineTier({budget:b,committed:cm,actual:0});
    var col=tier?TIER_COLOR[tier]:'var(--ok)';
    return '<div class="srow"><span class="slbl">'+H(k)+'</span><span class="sval" style="color:'+col+'">'+fmt(cm)+' / '+fmt(b)+' &middot; '+pct+'%</span></div>'+
      '<div class="pbar"><div class="pfill" style="width:'+Math.min(100,pct)+'%;background:'+col+'"></div></div>';
  }).join(''):'<div style="color:var(--muted);text-align:center;padding:12px;">No cost lines in scope</div>';
```

- [ ] **Step 4: Retire "Lines Over" as a separate KPI — repurpose the same tile as "Critical Lines"**

Current line 664:
```html
    <div class="kpi"><div class="klbl">Lines Over</div><div class="kval" id="c-over">0</div><div class="kt" id="c-over-sub">Committed &gt; budget</div></div>
```
New line 664:
```html
    <div class="kpi"><div class="klbl">Critical Lines</div><div class="kval" id="c-over">0</div><div class="kt" id="c-over-sub">At or above 90% of budget</div></div>
```
(Same element IDs kept deliberately — no other code references `#c-over`/
`#c-over-sub` outside `rCostTbl()`, confirmed by grepping this file for
`c-over` before writing this step; reusing the IDs avoids an orphaned
element and a duplicate-ID risk from adding a new one instead.)

Current (line 3817, inside `rCostTbl()`):
```javascript
  var over=list.filter(function(c){return (c.committed||0)>(c.budget||0);});
```
New:
```javascript
  var over=list.filter(function(c){return costLineTier(c)==='critical';});
```
(Everything downstream of `over` — lines 3822, 3827-3828 — already
reads `over.length`/`over.length?...` and needs no further change; only
the definition of what counts as "over" changes, from a binary
`committed>budget` check to `costLineTier(c)==='critical'`, which is a
strict superset per spec §3.)

Current line 3828:
```javascript
  $('c-over-sub').textContent=over.length?'Committed > budget':'All lines within budget';
```
New:
```javascript
  $('c-over-sub').textContent=over.length?'Committed+actual at or above 90% of budget':'No lines at critical tier';
```

- [ ] **Step 5: Verify syntax**

Run: `python tools/checkblocks.py sairnbuild.html`
Expected: `FAILED_BLOCKS:0`.

- [ ] **Step 6: Div-balance and dead-button checks**

Run whatever this repo's current equivalent is to
`div_balance_check.py`/`sairn_dead_button_audit.py` (used on every
SAIRNgrounds/SAIRNscape change tonight) against `sairnbuild.html`.
Confirm the new `<th>Tier</th>` didn't break the table's column-count
symmetry and no new dead button/duplicate ID was introduced.

- [ ] **Step 7: Real browser interaction test**

Serve `sairnbuild.html` locally (same `python -m http.server` pattern
used all night), log in past the license gate with a real or mocked
license flow (check `bldLicenseKey()`/the `#gate` flow for how this
file's gate actually works before assuming SAIRNgrounds' client-side
mock-license pattern transfers directly — this file's gate may differ),
add cost lines at 65%, 75%, 85%, 95%, and 150% of their budget across
at least two different jobs, and confirm directly in the rendered DOM:
- Each row's Tier cell shows the correct badge (none/Watch/Warning/
  Critical/Critical) at each boundary.
- The Cost Code Roll-up card's bar color matches the same tier.
- "Critical Lines" KPI count matches the number of lines at ≥90%,
  including the 150% line (still counted once, not double-counted as a
  separate "over" state).
- Editing a critical line's committed amount down below 70% and re-
  rendering clears its badge (proves the live/ephemeral, no-stored-state
  design from spec §2 actually holds, not just claimed).

- [ ] **Step 8: Commit**

```bash
git add sairnbuild.html
git commit -m "feat: Job Costing panel shows tier badges per line and roll-up, retires Lines Over KPI in favor of Critical Lines"
```

---

### Task 4: Dashboard integration

**Requires:** explicit confirmation on the role-gating deviation
(see "Deviation from spec" section above) before starting this task.

**Files:**
- Modify: `sairnbuild.html:3910-3966` (`rDash()`, specifically the `att`
  array construction, around lines 3948-3963)

**Interfaces:**
- Consumes: `jobTierFromCosts(jobId, allCosts)`, `TIER_LABEL` from
  Task 2; `costs()`, `jobs()` (existing, lines 2395-2396).
- Produces: no new function or element ID — extends the existing `att`
  array / `#d-attention` rendering already used by blocked/thin-margin/
  compliance-expiry entries (same task, same output target, no new
  consumer elsewhere in the file).

**Important scoping note:** compute tiers against the FULL `costs()`
list, not `costScope()` (the Job Costing panel's currently-selected
job/kind filter) — the Dashboard must reflect true state regardless of
whatever filter happens to be selected on a different panel. `costScope()`
is Job Costing-panel-local state; `rDash()` must not depend on it.

- [ ] **Step 1: Add at-risk jobs into the existing attention list**

Current (lines 3948-3962, showing the relevant insertion point after the
existing `blocked`/`act`/`punch` pushes and before the `bldSubs()`
compliance block):
```javascript
  var att=[];
  blocked.forEach(function(j){att.push({t:H(j.client)+' - '+H(j.blocked||'blocked'),b:'Blocked',c:'br'});});
  act.forEach(function(j){var m=marginPct(j);if(m<10)att.push({t:H(j.client)+' margin at '+m+'%',b:m<0?'Losing':'Thin',c:m<0?'br':'bw'});});
  js.filter(function(j){return j.stage==='punch';}).forEach(function(j){att.push({t:H(j.client)+' in close-out',b:'Punch',c:'bw'});});
```
New (insert immediately after the `punch` line, before the `bldSubs()`
compliance block):
```javascript
  var att=[];
  blocked.forEach(function(j){att.push({t:H(j.client)+' - '+H(j.blocked||'blocked'),b:'Blocked',c:'br'});});
  act.forEach(function(j){var m=marginPct(j);if(m<10)att.push({t:H(j.client)+' margin at '+m+'%',b:m<0?'Losing':'Thin',c:m<0?'br':'bw'});});
  js.filter(function(j){return j.stage==='punch';}).forEach(function(j){att.push({t:H(j.client)+' in close-out',b:'Punch',c:'bw'});});
  // AI Budget Early Warning: watch-tier jobs deliberately excluded here
  // (spec section 4) -- this list is an "act now" surface, not a
  // low-priority FYI list. Computed against the FULL costs() list, not
  // costScope(), so this is correct regardless of Job Costing's own
  // current filter selection.
  var allCosts=costs();
  js.forEach(function(j){
    var t=jobTierFromCosts(j.id, allCosts);
    if(t==='warning'||t==='critical'){
      att.push({t:H(j.client)+' cost overrun risk ('+TIER_LABEL[t]+')',b:TIER_LABEL[t],c:t==='critical'?'br':'bw'});
    }
  });
```

- [ ] **Step 2: Verify syntax**

Run: `python tools/checkblocks.py sairnbuild.html`
Expected: `FAILED_BLOCKS:0`.

- [ ] **Step 3: Real browser interaction test**

Using the same seeded cost lines from Task 3 Step 7 (at least one job
with a critical-tier line, one with only a warning-tier line, one with
only a watch-tier line, one with no lines above 70%), navigate to
Dashboard and confirm directly in the rendered DOM:
- The warning-tier job and the critical-tier job both appear in
  "Needs Attention" with the correct badge label and color.
- The watch-only job does **not** appear (confirms the deliberate
  exclusion in Step 1's comment actually holds, not just claimed).
- The clean job does not appear.
- Existing attention-list entries (blocked/thin-margin/compliance) still
  render correctly alongside the new ones — this task must not break
  what was already there.

- [ ] **Step 4: Commit**

```bash
git add sairnbuild.html
git commit -m "feat: Dashboard Needs Attention list surfaces jobs at warning/critical budget-overrun tier"
```

---

### Task 5 (OPTIONAL — do not start without separate explicit go-ahead): "Explain this" Claude narrative

Per spec §7, this is explicitly not core and ships only if wanted. Do
not implement this task as part of the same approval as Tasks 1-4 —
ask separately once those are reviewed and working, since it's the one
task in this plan that adds a real API call and real Claude-output
handling (anti-fabrication system prompt, escaping the response before
render) that the other four tasks deliberately avoid.

**Files (if built):**
- Modify: `sairnbuild.html` — new button in the Job Costing panel (near
  the job filter, `#cjob`/`#ckind` at line ~666-677), new result-display
  element, new handler function following the exact pattern at
  `sairnbuild.html:2450-2485` (`fpAnalyze`, the Field Photo Analysis
  Claude call) — same `PROXY`/`APP_ID`/`fetch` shape, same try/catch
  network-failure handling, same "no response text returned" fallback.

**Interfaces (if built):**
- Consumes: `jobTierFromCosts`, `costs()` filtered to one job's lines,
  `PROXY`, `APP_ID` (all existing/Task 2).
- Produces: nothing consumed by any other task — this is a leaf feature.

Full steps intentionally not written out here — this task doesn't start
until Tasks 1-4 are reviewed, working, and Michael has given a separate,
explicit go-ahead specifically for this one, per spec §7 and the
standing "no code without explicit approval" rule.

---

## Self-Review

**1. Spec coverage:**
- §2 (no AI call, no persistence, no push notification) — Tasks 1-4
  introduce zero new fetch/API calls and zero new storage. ✓
- §3 (computation, tiers, job rollup, Lines Over retirement) — Task 2
  (functions) + Task 3 Step 4 (retirement). ✓
- §4 (surfacing on Job Costing + Dashboard) — Task 3 (panel) + Task 4
  (dashboard), with the attention-list refinement flagged above. ✓
  **Correction (2026-08-07, post-review fix wave):** this line originally
  claimed full coverage, but that claim was wrong. §4's third requirement
  — "wherever jobs are listed/filtered in this panel, each job shows its
  rolled-up tier flag" — was never actually implemented in Task 3. Task 3
  added the line-level tier badge and the roll-up card color, but not the
  job-level rolled-up flag on the Job Costing panel itself. This was an
  undisclosed gap: Task 3's own review passed it as "complete," and this
  Self-Review section incorrectly marked §4 as fully covered on top of
  that. It was caught by the final whole-branch review (Important #5,
  `.superpowers/sdd/2026-08-07-sairnbuild-ai-budget-early-warning/
  progress.md`) and fixed in the post-review fix wave (job-level
  `jobTierFromCosts(c.job_id, costs())` badge added next to `jobLabel()`
  in `rCostTbl()`'s row template). Leaving the original ✓ unedited would
  misstate this document's own history — noting the correction here
  instead, per this project's "corrections are not optional, name what
  changed" standard.
- §5 (role gating) — **not implementable as specified; flagged as a
  deviation requiring explicit confirmation before Task 4**, not
  silently dropped or silently faked. ✓ (as a disclosed gap, not a
  silent omission)
- §6 (colors) — Task 1, with the real visual-check step spec §6 itself
  demanded (not just a hex-distance claim). ✓
- §7 (optional narrative) — Task 5, explicitly gated behind a second,
  separate approval. ✓
- §8 (testing) — every task's real-interaction-test step maps directly
  to spec §8's boundary list (69/70/80/90/120%, Dashboard count,
  "Lines Over" actually removed not just hidden). ✓

**2. Placeholder scan:** No TBD/TODO. One deliberate "confirm before
assuming" note in Task 1 Step 2 and Task 3 Step 2/7 (tooling script name,
`.badge` CSS convention, license-gate flow) — these are real "verify
against actual current state before proceeding" instructions in the
same spirit as every check done tonight, not vague placeholders; each
names exactly what to check and where.

**3. Type/name consistency:** `costLineTier`, `jobTierFromCosts`,
`TIER_LABEL`, `TIER_COLOR` — defined once in Task 2, used identically
(same names, same call shape) in Tasks 3 and 4. No renamed variants.
