# SAIRNbiz Hiring Cost-Impact Reasoning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the AI assistant answer "what does filling this role do to our labor cost and margin" with real, computed numbers — reusing the existing payroll and P&L tools rather than duplicating their logic, and taking an explicit numeric rate instead of trying to parse the Hiring pipeline's unparseable free-text pay-range field.

**Architecture:** `computeHiringCostImpact(hourlyRate, employmentType, payrollSummary, plSummary)` — a new, pure function taking already-fetched data as arguments (no `SB_TOOLS`/`rPay()`/DOM dependency, fully Node-testable). A new tool, `get_hiring_cost_impact`, is a thin wrapper: fetches `SB_TOOLS['get_payroll_summary'].run()` and `SB_TOOLS['get_pl_summary'].run()` directly (zero duplication, zero changes to either existing tool), optionally looks up a named `sb_hire` position for reference context, then calls the pure function.

**Tech Stack:** Vanilla JS (`sairnbiz.html`), same `SB_TOOLS` dispatcher items 1-4 built.

## Global Constraints

- `hourly_rate` and `employment_type` are required tool arguments — the math NEVER parses `sb_hire.rate`'s free-text range (e.g. `"$18-22/hr"`). A matched position's stored range may appear in the response as unparsed reference text only. (Spec §2, §4)
- `get_hiring_cost_impact` calls `SB_TOOLS['get_payroll_summary'].run()` and `SB_TOOLS['get_pl_summary'].run()` directly for current figures — no reimplementation of either tool's computation. (Spec §3)
- `new_role_hours` = 80 for Full Time, 32 for Part Time — matches `rPay()`'s existing convention. `new_role_fica` uses the same 7.65% FICA rate, `new_role_benefit` uses the same flat $520 — both matching `get_payroll_summary`'s existing, already-disclosed assumptions. (Spec §4)
- Company-wide cost only — no new per-department aggregation. (Spec §3)
- `get_hiring_cost_impact` is `sensitive:true` (owner-only, matching every other financial tool). (Spec §4)
- The tool description must disclose, up front, that this is a "nothing else changes" projection (zero assumed revenue increase, simplified tax/benefit assumptions, excludes one-time hiring costs) — matching the disclosure discipline items 2-4 each needed a fix round to reach. (Spec §4)
- No changes to `rPay()`, `get_payroll_summary`, `get_pl_summary`, `checkPayrollAnomalies()`, `checkAttentionItems()`, `rDash()`, `sbExecuteTool()`, or `callAI()` — purely additive.
- Every modified script block must pass `python tools/checkblocks.py sairnbiz.html` (`FAILED_BLOCKS:0`) and `python tools/div_balance_check.py sairnbiz.html` (`PASS`).
- Before push: Guardian v2 pass. After push: live-verify against `sairn.vercel.app`, per the project's standing Push Protocol.

---

### Task 1: `sairnbiz.html` — `computeHiringCostImpact()`

**Files:**
- Modify: `sairnbiz.html` (insert immediately before `function rDash(){` — currently at line 1416; confirm this line number is still accurate before inserting, alongside its siblings `checkPayrollAnomalies()`/`checkAttentionItems()`)

**Interfaces:**
- Consumes: nothing external — pure function, arguments only.
- Produces: `computeHiringCostImpact(hourlyRate, employmentType, payrollSummary, plSummary)` — where `payrollSummary` is the exact shape `get_payroll_summary` returns (`{gross_payroll, taxes_fica, benefits, total_labor_cost, ytd_payroll}`) and `plSummary` is the exact shape `get_pl_summary` returns (`{revenue, cogs, gross_profit, operating_expenses, net_income, revenue_by_category, expense_by_category, gross_margin_pct, net_margin_pct, industry_avg_gross_margin_pct, industry_avg_net_margin_pct}`). Returns `{new_role_gross, new_role_fica, new_role_benefit, new_role_fully_loaded_cost, current_total_labor_cost, projected_total_labor_cost, current_net_income, current_net_margin_pct, projected_net_income, projected_net_margin_pct}`. Used by Task 2.

- [ ] **Step 1: Write the implementation**

Insert immediately before `function rDash(){` (`sairnbiz.html:1416`):

```js
// Hiring cost-impact reasoning (2026-08-10) -- pure math, takes
// already-fetched payroll/P&L data as arguments (no SB_TOOLS/rPay()/DOM
// dependency), fully Node-testable in isolation. "Nothing else changes"
// projection: assumes zero revenue increase from the hire, applies the
// same FICA-only-tax (7.65%)/flat-$520-benefit assumptions
// get_payroll_summary already uses and discloses as incomplete, and
// excludes one-time hiring costs (recruiting, onboarding, ramp-up).
// See docs/superpowers/specs/2026-08-10-sairnbiz-hiring-cost-impact-design.md
function computeHiringCostImpact(hourlyRate, employmentType, payrollSummary, plSummary) {
  var newRoleHours = employmentType === 'Full Time' ? 80 : 32;
  var newRoleGross = hourlyRate * newRoleHours;
  var newRoleFica = newRoleGross * 0.0765;
  var newRoleBenefit = 520;
  var newRoleFullyLoadedCost = newRoleGross + newRoleFica + newRoleBenefit;

  var projectedTotalLaborCost = payrollSummary.total_labor_cost + newRoleFullyLoadedCost;
  var projectedNetIncome = plSummary.net_income - newRoleFullyLoadedCost;
  var projectedNetMarginPct = plSummary.revenue > 0 ? Math.round(projectedNetIncome / plSummary.revenue * 100) : 0;

  return {
    new_role_gross: newRoleGross,
    new_role_fica: newRoleFica,
    new_role_benefit: newRoleBenefit,
    new_role_fully_loaded_cost: newRoleFullyLoadedCost,
    current_total_labor_cost: payrollSummary.total_labor_cost,
    projected_total_labor_cost: projectedTotalLaborCost,
    current_net_income: plSummary.net_income,
    current_net_margin_pct: plSummary.net_margin_pct,
    projected_net_income: projectedNetIncome,
    projected_net_margin_pct: projectedNetMarginPct
  };
}
```

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairnbiz.html`
Expected: `TOTAL_BLOCKS:2` / `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnbiz.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Behavioral verification with a temporary Node harness**

No DOM/global dependency, so real logic can be tested directly by passing plain object arguments. Scratch file (not committed):

```js
var assert = require('assert');

function computeHiringCostImpact(hourlyRate, employmentType, payrollSummary, plSummary) {
  var newRoleHours = employmentType === 'Full Time' ? 80 : 32;
  var newRoleGross = hourlyRate * newRoleHours;
  var newRoleFica = newRoleGross * 0.0765;
  var newRoleBenefit = 520;
  var newRoleFullyLoadedCost = newRoleGross + newRoleFica + newRoleBenefit;
  var projectedTotalLaborCost = payrollSummary.total_labor_cost + newRoleFullyLoadedCost;
  var projectedNetIncome = plSummary.net_income - newRoleFullyLoadedCost;
  var projectedNetMarginPct = plSummary.revenue > 0 ? Math.round(projectedNetIncome / plSummary.revenue * 100) : 0;
  return {
    new_role_gross: newRoleGross, new_role_fica: newRoleFica, new_role_benefit: newRoleBenefit,
    new_role_fully_loaded_cost: newRoleFullyLoadedCost,
    current_total_labor_cost: payrollSummary.total_labor_cost, projected_total_labor_cost: projectedTotalLaborCost,
    current_net_income: plSummary.net_income, current_net_margin_pct: plSummary.net_margin_pct,
    projected_net_income: projectedNetIncome, projected_net_margin_pct: projectedNetMarginPct
  };
}

// Case 1: full-time $25/hr against realistic current figures
var payroll1 = { gross_payroll: 40000, taxes_fica: 3060, benefits: 4160, total_labor_cost: 47220, ytd_payroll: 520000 };
var pl1 = { revenue: 100000, net_income: 15000, net_margin_pct: 15 };
var r1 = computeHiringCostImpact(25, 'Full Time', payroll1, pl1);
assert.strictEqual(r1.new_role_gross, 2000); // 25 * 80
assert.strictEqual(r1.new_role_fica, 153);   // 2000 * 0.0765
assert.strictEqual(r1.new_role_benefit, 520);
assert.strictEqual(r1.new_role_fully_loaded_cost, 2673); // 2000+153+520
assert.strictEqual(r1.projected_total_labor_cost, 49893); // 47220+2673
assert.strictEqual(r1.projected_net_income, 12327); // 15000-2673
assert.strictEqual(r1.projected_net_margin_pct, 12); // round(12327/100000*100)

// Case 2: part-time $18/hr, confirms 32-hour convention
var r2 = computeHiringCostImpact(18, 'Part Time', payroll1, pl1);
assert.strictEqual(r2.new_role_gross, 576); // 18 * 32

// Case 3: zero revenue -- projected_net_margin_pct must not divide by zero
var pl3 = { revenue: 0, net_income: 0, net_margin_pct: 0 };
var r3 = computeHiringCostImpact(25, 'Full Time', payroll1, pl3);
assert.strictEqual(r3.projected_net_margin_pct, 0);

// Case 4: zero current labor cost -- projected cost equals just the new role's cost
var payroll4 = { gross_payroll: 0, taxes_fica: 0, benefits: 0, total_labor_cost: 0, ytd_payroll: 0 };
var r4 = computeHiringCostImpact(20, 'Full Time', payroll4, pl1);
assert.strictEqual(r4.projected_total_labor_cost, r4.new_role_fully_loaded_cost);

console.log('computeHiringCostImpact: all 4 cases passed');
```

Run: `node <scratch-file>.js`
Expected: `computeHiringCostImpact: all 4 cases passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add sairnbiz.html
git commit -m "feat: SAIRNbiz -- computeHiringCostImpact() pure function

Takes already-fetched payroll/P&L summaries as arguments -- no
SB_TOOLS/rPay()/DOM dependency, fully Node-testable. Same FICA
rate/flat-benefit assumptions get_payroll_summary already uses and
discloses. Not yet wired to anything -- Task 2 consumes it."
```

---

### Task 2: `sairnbiz.html` — `get_hiring_cost_impact` AI tool

**Files:**
- Modify: `sairnbiz.html` (insert immediately after `get_attention_digest`'s closing `);` — currently at line 1058; confirm still accurate)

**Interfaces:**
- Consumes: `computeHiringCostImpact(...)` (Task 1), `SB_TOOLS['get_payroll_summary'].run()`, `SB_TOOLS['get_pl_summary'].run()` (both existing, unmodified), `ld(k,d)` (existing), `sbRegisterTool(...)` (existing).

- [ ] **Step 1: Write the implementation**

Insert after `get_attention_digest`'s closing `);` (`sairnbiz.html:1058`):

```js
sbRegisterTool(
  'get_hiring_cost_impact',
  'Calculate the real cost impact of filling an open position: if hired at a given hourly rate, what happens to total labor cost and net margin. Optionally name a real open position (matching the Hiring pipeline) to include its department, stage, and posted pay range as reference context -- the math itself always uses the hourly_rate argument you provide, never the position\'s free-text posted range (which cannot be reliably parsed -- e.g. "$18-22/hr"). IMPORTANT CAVEATS: this is a "nothing else changes" projection -- it assumes ZERO revenue increase from the hire (a real hire may of course grow revenue; this tool cannot predict that), applies the same simplified FICA-only tax (7.65%) and flat $520 benefit assumptions get_payroll_summary already uses and discloses as incomplete, and excludes one-time hiring costs entirely (recruiting, onboarding, ramp-up time to full productivity). Present the result as an estimate of ongoing fully-loaded cost, not a complete hiring-decision analysis.',
  {
    type: 'object',
    properties: {
      position: { type: 'string', description: 'Optional: an open position title from the Hiring pipeline, e.g. "Senior Fabricator", to include as reference context.' },
      hourly_rate: { type: 'number', description: 'The hourly pay rate to model, in dollars.' },
      employment_type: { type: 'string', enum: ['Full Time', 'Part Time'], description: 'Full Time computes 80 hours/period, Part Time computes 32 hours/period, matching this app\'s existing payroll convention.' }
    },
    required: ['hourly_rate', 'employment_type']
  },
  true,
  function (input) {
    var payrollSummary = SB_TOOLS['get_payroll_summary'].run();
    var plSummary = SB_TOOLS['get_pl_summary'].run();
    var result = computeHiringCostImpact(input.hourly_rate, input.employment_type, payrollSummary, plSummary);
    if (input.position) {
      var match = ld('sb_hire', []).find(function (h) { return h.pos === input.position; });
      if (match) {
        result.position_context = { dept: match.dept, stage: match.stage, posted_rate_range: match.rate };
      }
    }
    return result;
  }
);
```

- [ ] **Step 2: Syntax-check**

Run: `python tools/checkblocks.py sairnbiz.html`
Expected: `TOTAL_BLOCKS:2` / `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnbiz.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Behavioral verification**

`computeHiringCostImpact()` was already verified in Task 1; `SB_TOOLS['get_payroll_summary']`/`['get_pl_summary']` are already-shipped, already-tested tools. Confirm registration and reuse mechanics only: `grep -n "get_hiring_cost_impact" sairnbiz.html` shows the tool registered exactly once with `true` as the 4th argument; confirm by reading the code (not executing) that `run()` calls `SB_TOOLS['get_payroll_summary'].run()`/`SB_TOOLS['get_pl_summary'].run()` directly rather than reimplementing any of their logic, and that `sb_hire` lookup uses `.find()` on `h.pos`, matching the real field name `saveHire()` writes (`sairnbiz.html`, search `function saveHire`).

- [ ] **Step 4: Commit**

```bash
git add sairnbiz.html
git commit -m "feat: SAIRNbiz -- get_hiring_cost_impact AI tool

Owner-gated. Reuses SB_TOOLS['get_payroll_summary']/['get_pl_summary']
directly for current figures (zero duplication, zero changes to either
existing tool), wraps computeHiringCostImpact() (Task 1) for the math.
Takes an explicit hourly_rate argument rather than parsing sb_hire's
unparseable free-text pay-range field. Optional position lookup for
reference context only, never used in the math."
```

---

### Task 3: End-to-end verification, push, live-verify

**Files:** none modified — verification only.

- [ ] **Step 1: Full local re-check**

```bash
python tools/checkblocks.py sairnbiz.html
python tools/div_balance_check.py sairnbiz.html
```

Expected: both clean.

- [ ] **Step 2: Guardian v2 pass**

Run the relevant `sairn-guardian-v2` checks against the changed sections of `sairnbiz.html`.

- [ ] **Step 3: Reuse-not-drift test (primary, live)**

Against the LIVE deployed app, in the same session: ask the AI Assistant for the current payroll summary and P&L summary (exercising `get_payroll_summary`/`get_pl_summary` directly), note the real `total_labor_cost`/`net_income`/`revenue` figures. Then ask a hiring cost-impact question (e.g. "what would it cost to hire a Senior Fabricator at $28/hour full time"). Confirm the tool's `current_total_labor_cost`/`current_net_income`/`current_net_margin_pct` in its response match the numbers from the direct payroll/P&L queries exactly — proving genuine reuse, not a second independently-computed (and potentially drifting) version of the same numbers.

- [ ] **Step 4: Math and position-context test (live)**

Confirm the projected figures in the AI's answer are internally consistent with the input (hourly rate × 80 or 32 hours, plus 7.65% FICA, plus $520 benefit, added to the current total). Ask about a real open position by name (e.g. "Senior Fabricator") and confirm department/stage/posted-range context appears in the answer. Ask a hypothetical with no real position match and confirm the tool still answers with no error.

- [ ] **Step 5: Role-gate test (live)**

Verify a non-owner role gets the restricted-access message for `get_hiring_cost_impact`, not a number.

- [ ] **Step 6: Push**

```bash
git push origin main
```

- [ ] **Step 7: Live-verify**

```bash
curl -s https://sairn.vercel.app/sairnbiz | grep -c "computeHiringCostImpact"
curl -s https://sairn.vercel.app/sairnbiz | grep -c "get_hiring_cost_impact"
```

Expected: both non-zero. Repeat Steps 3-5's tests against this confirmed-deployed version specifically.

- [ ] **Step 8: Update the spec's status line**

Edit `docs/superpowers/specs/2026-08-10-sairnbiz-hiring-cost-impact-design.md`'s `**Status:**` line to note implementation complete and live-verified, naming which specific tests passed live (reuse-not-drift test, math/position-context test) — not "tests passed" generically. Commit this doc-only change separately, push it.
