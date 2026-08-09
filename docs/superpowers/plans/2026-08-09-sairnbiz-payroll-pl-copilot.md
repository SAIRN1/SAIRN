# SAIRNbiz Payroll/P&L Copilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give SAIRNbiz's AI Assistant two real, owner-gated tools — `get_payroll_summary` and `get_pl_summary` — grounded in `rPay()`'s real computed numbers, so financial questions get real answers instead of the generic responses every other question type still gets.

**Architecture:** Both tools call `rPay()` first (forces a fresh render, preventing the "cold call" blind-zero failure where KPI elements still hold their static `"$0"` HTML defaults), then read back the rendered aggregate KPI values via a new shared helper, `sbReadKpiNumber(elId)`. `get_pl_summary` additionally re-derives category breakdowns directly from `ld('sb_invs',[])`/`ld('sb_exps',[])` (cheap, low-drift re-derivation of a 3-line grouping) and recomputes margin percentages arithmetically from the already-extracted revenue/gross-profit/net-income numbers. No changes to `rPay()`, `genReport()`, `sbExecuteTool()`, or `callAI()` — this plan is purely additive on top of item 1's proven foundation.

**Tech Stack:** Vanilla JS (`sairnbiz.html`), same `SB_TOOLS`/`sbRegisterTool`/`sbExecuteTool` dispatcher item 1 built. No server-side changes this time (unlike item 1, which needed `api/claude.js`).

## Global Constraints

- Both tools are read-only, take no arguments, and are `sensitive:true` (owner-only via the existing gate in `sbExecuteTool`, `sairnbiz.html:909-920` — not modified by this plan). (Spec §3, §5)
- `run()` must call `rPay()` unconditionally as its first statement, every time — this is the one non-negotiable implementation detail; skipping it produces a plausible-looking but wrong `0` for a user who never opened the Payroll/P&L panel this session. (Spec §4)
- Payroll's tax/benefit figures are READ BACK from `rPay()`'s rendered output, never independently recomputed. Category breakdowns ARE independently re-derived (cheap, no rate constants to drift). Margins are recomputed arithmetically from already-extracted values, not parsed from rendered HTML. (Spec §4)
- No refactor of `rPay()`, `genReport()`, or any existing function — purely additive. (Spec §2)
- `get_payroll_summary` returns aggregate totals only — no per-employee detail. (Spec §2)
- Every modified script block in `sairnbiz.html` must pass `node --check` / `python tools/checkblocks.py sairnbiz.html` (FAILED_BLOCKS:0) and `python tools/div_balance_check.py sairnbiz.html` (PASS).
- Before push: Guardian v2 pass on the changed file. After push: live-verify against `sairn.vercel.app`, with the cold-call scenario as the primary live test (per project Push Protocol and this spec's own emphasis).

---

### Task 1: `sairnbiz.html` — `sbReadKpiNumber()` helper + `get_payroll_summary`

**Files:**
- Modify: `sairnbiz.html` (insert immediately after the `get_employees` registration block, which currently ends at line 934 with `);`, before `function $(s){return document.getElementById(s);}` at line 936 — confirm these line numbers are still accurate before inserting, since other work may have touched this file)

**Interfaces:**
- Consumes: `rPay()` (`sairnbiz.html:1373`, void, renders into `#py-gross`/`#py-tax`/`#py-ben`/`#py-total`/`#py-ytd`/`#pl-rev`/etc.), `$(s)` (existing DOM getter), `sbRegisterTool(name, description, inputSchema, sensitive, run)` (existing, from item 1).
- Produces: `sbReadKpiNumber(elId)` — used by this task and Task 2.

- [ ] **Step 1: Write the implementation**

Insert after the `get_employees` registration (`sairnbiz.html:934`):

```js
// Shared by every KPI-backed AI tool from here on: rPay() renders real
// numbers into KPI elements as formatted text ("$12,345"), it doesn't
// return them. This reads one back and parses it to a real number --
// same parsing logic genReport('pl')'s local `pf` helper already uses
// (sairnbiz.html's genReport function), as a small shared function
// instead of each tool duplicating the one-liner. Does not touch or
// replace genReport's own local pf -- zero risk to that existing path.
function sbReadKpiNumber(elId) {
  var el = $(elId);
  if (!el) return 0;
  return parseFloat(String(el.textContent).replace(/[^0-9.-]/g, '')) || 0;
}

sbRegisterTool(
  'get_payroll_summary',
  'Get the current payroll summary: gross payroll, employer taxes, benefits cost, total fully-loaded labor cost, and year-to-date payroll, for active employees. Aggregate totals only -- does not include any individual employee\'s pay.',
  { type: 'object', properties: {}, required: [] },
  true,
  function (input) {
    // input intentionally unused -- no arguments in v1, same interface
    // consistency note as get_employees.
    // rPay() MUST run first, unconditionally, every call -- without it,
    // these KPI elements still hold their static "$0" HTML default if
    // the Payroll panel was never opened this session, and this would
    // return a plausible-looking but completely wrong zero.
    rPay();
    return {
      gross_payroll: sbReadKpiNumber('py-gross'),
      taxes_fica: sbReadKpiNumber('py-tax'),
      benefits: sbReadKpiNumber('py-ben'),
      total_labor_cost: sbReadKpiNumber('py-total'),
      ytd_payroll: sbReadKpiNumber('py-ytd')
    };
  }
);
```

- [ ] **Step 2: Syntax-check the modified script block**

Run: `python tools/checkblocks.py sairnbiz.html`
Expected: `TOTAL_BLOCKS:2` / `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnbiz.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Behavioral verification with a temporary Node harness**

`sbReadKpiNumber`'s parsing logic has no DOM dependency and can be checked directly; the full tool (which calls `rPay()` and real `$()`) cannot be meaningfully stubbed this way (rPay() does real DOM rendering across many elements) — that verification happens live in Task 3. For this step, verify just the parsing logic. Scratch file (not committed):

```js
var assert = require('assert');
function sbReadKpiNumber(elId, STORE) {
  var text = STORE[elId];
  if (text === undefined) return 0;
  return parseFloat(String(text).replace(/[^0-9.-]/g, '')) || 0;
}
// (Node harness version takes a stub-store second arg since there's no
// real $()/DOM here -- the real sairnbiz.html version takes only elId
// and calls the real $(). This harness checks the parsing math only.)

var STORE = { 'py-gross': '$12,345', 'py-tax': '$944', 'missing-el': undefined };
assert.strictEqual(sbReadKpiNumber('py-gross', STORE), 12345);
assert.strictEqual(sbReadKpiNumber('py-tax', STORE), 944);
assert.strictEqual(sbReadKpiNumber('missing-el', STORE), 0);
assert.strictEqual(sbReadKpiNumber('nonexistent-key', STORE), 0);

console.log('sbReadKpiNumber parsing: all 4 checks passed');
```

Run: `node <scratch-file>.js`
Expected: `sbReadKpiNumber parsing: all 4 checks passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add sairnbiz.html
git commit -m "feat: SAIRNbiz -- get_payroll_summary tool + sbReadKpiNumber helper

Owner-gated aggregate payroll totals (gross/tax/benefits/total/YTD).
rPay() called unconditionally first to prevent the cold-call blind-zero
case (KPI elements default to static \$0 until rPay() actually renders).
No per-employee detail, no changes to rPay()/genReport()/sbExecuteTool()."
```

---

### Task 2: `sairnbiz.html` — `get_pl_summary`

**Files:**
- Modify: `sairnbiz.html` (insert immediately after Task 1's `get_payroll_summary` registration)

**Interfaces:**
- Consumes: `sbReadKpiNumber(elId)` (Task 1), `rPay()`, `ld(k,d)` (existing), `sbRegisterTool(...)` (existing).
- Produces: nothing new consumed elsewhere — leaf registration, same as `get_employees`.

- [ ] **Step 1: Write the implementation**

Insert after Task 1's `get_payroll_summary` registration:

```js
sbRegisterTool(
  'get_pl_summary',
  'Get the current profit & loss summary: revenue, cost of goods sold, gross profit, operating expenses, net income, revenue broken down by category, expenses broken down by category, and gross/net margin percentages. Also includes static industry-average margin benchmarks (45% gross, 18% net) for comparison -- these are fixed reference figures, NOT computed from this business\'s own data, and must never be presented as if they were.',
  { type: 'object', properties: {}, required: [] },
  true,
  function (input) {
    // rPay() MUST run first, unconditionally -- same cold-call reason as
    // get_payroll_summary. Also seeds the KPI elements this tool reads.
    rPay();
    var revenue = sbReadKpiNumber('pl-rev');
    var cogs = sbReadKpiNumber('pl-cogs');
    var grossProfit = sbReadKpiNumber('pl-gp');
    var operatingExpenses = sbReadKpiNumber('pl-opex');
    var netIncome = sbReadKpiNumber('pl-net');
    // Category breakdowns: re-derived directly (cheap, no rate constants
    // to drift), not parsed from rendered HTML. Mirrors rPay()'s own
    // grouping exactly (sairnbiz.html's rPay function, revCats/expCats).
    var invs = ld('sb_invs', []);
    var exps = ld('sb_exps', []);
    var revenueByCategory = {};
    invs.forEach(function (i) {
      var c = i.cat || 'Uncategorized';
      revenueByCategory[c] = (revenueByCategory[c] || 0) + i.amt;
    });
    // Labor seeded from the same gross-payroll figure get_payroll_summary
    // reads back, keeping the two tools' numbers internally consistent
    // even though they're separate calls -- matches rPay()'s own
    // expCats={Labor:gross} seed exactly.
    var expenseByCategory = { Labor: sbReadKpiNumber('py-gross') };
    exps.forEach(function (e) {
      expenseByCategory[e.cat] = (expenseByCategory[e.cat] || 0) + e.amt;
    });
    // Margins recomputed arithmetically from the already-extracted
    // numbers above, not parsed from #pl-margin's rendered HTML.
    var grossMarginPct = revenue > 0 ? Math.round(grossProfit / revenue * 100) : 0;
    var netMarginPct = revenue > 0 ? Math.round(netIncome / revenue * 100) : 0;
    return {
      revenue: revenue,
      cogs: cogs,
      gross_profit: grossProfit,
      operating_expenses: operatingExpenses,
      net_income: netIncome,
      revenue_by_category: revenueByCategory,
      expense_by_category: expenseByCategory,
      gross_margin_pct: grossMarginPct,
      net_margin_pct: netMarginPct,
      industry_avg_gross_margin_pct: 45,
      industry_avg_net_margin_pct: 18
    };
  }
);
```

- [ ] **Step 2: Syntax-check**

Run: `python tools/checkblocks.py sairnbiz.html`
Expected: `TOTAL_BLOCKS:2` / `FAILED_BLOCKS:0`.

Run: `python tools/div_balance_check.py sairnbiz.html`
Expected: `RESULT:PASS`.

- [ ] **Step 3: Behavioral verification with a temporary Node harness**

The category-grouping and margin-arithmetic logic has no DOM dependency and can be checked directly. Scratch file (not committed):

```js
var assert = require('assert');

function computeCategoryBreakdown(invs, exps, grossPayroll) {
  var revenueByCategory = {};
  invs.forEach(function (i) {
    var c = i.cat || 'Uncategorized';
    revenueByCategory[c] = (revenueByCategory[c] || 0) + i.amt;
  });
  var expenseByCategory = { Labor: grossPayroll };
  exps.forEach(function (e) {
    expenseByCategory[e.cat] = (expenseByCategory[e.cat] || 0) + e.amt;
  });
  return { revenueByCategory: revenueByCategory, expenseByCategory: expenseByCategory };
}

function computeMargins(revenue, grossProfit, netIncome) {
  return {
    grossMarginPct: revenue > 0 ? Math.round(grossProfit / revenue * 100) : 0,
    netMarginPct: revenue > 0 ? Math.round(netIncome / revenue * 100) : 0
  };
}

var invs = [{ cat: 'Countertops', amt: 10000 }, { cat: 'Countertops', amt: 5000 }, { cat: 'Repair', amt: 2000 }];
var exps = [{ cat: 'Materials', amt: 4000 }, { cat: 'Overhead', amt: 1000 }];
var out = computeCategoryBreakdown(invs, exps, 8000);
assert.deepStrictEqual(out.revenueByCategory, { Countertops: 15000, Repair: 2000 });
assert.deepStrictEqual(out.expenseByCategory, { Labor: 8000, Materials: 4000, Overhead: 1000 });

var uncat = computeCategoryBreakdown([{ amt: 500 }], [], 0);
assert.deepStrictEqual(uncat.revenueByCategory, { Uncategorized: 500 });

var m1 = computeMargins(17000, 13000, 4000);
assert.strictEqual(m1.grossMarginPct, 76);
assert.strictEqual(m1.netMarginPct, 24);

var m2 = computeMargins(0, 0, 0);
assert.strictEqual(m2.grossMarginPct, 0);
assert.strictEqual(m2.netMarginPct, 0);

console.log('get_pl_summary category/margin logic: all 6 checks passed');
```

Run: `node <scratch-file>.js`
Expected: `get_pl_summary category/margin logic: all 6 checks passed`. Delete the scratch file afterward.

- [ ] **Step 4: Commit**

```bash
git add sairnbiz.html
git commit -m "feat: SAIRNbiz -- get_pl_summary tool

Owner-gated P&L summary (revenue/COGS/gross profit/opex/net income,
category breakdowns, margin vs. static industry benchmark). Category
breakdowns re-derived directly from real data; margins recomputed
arithmetically; tax-rate-derived payroll figures read back via
sbReadKpiNumber, not independently recomputed. rPay() called
unconditionally first, same cold-call guard as get_payroll_summary."
```

---

### Task 3: End-to-end verification, push, live-verify

**Files:** none modified — verification only.

- [ ] **Step 1: Full local re-check**

```bash
python tools/checkblocks.py sairnbiz.html
python tools/div_balance_check.py sairnbiz.html
```

Expected: both clean (0 failures / PASS).

- [ ] **Step 2: Guardian v2 pass**

Run the full `sairn-guardian-v2` check (Check 0 + numbered checks) against the changed sections of `sairnbiz.html` before push, per the project's standing Push Protocol.

- [ ] **Step 3: The cold-call test (primary, dedicated live test)**

Against the LIVE deployed app at `https://sairn.vercel.app/sairnbiz`, with a genuinely fresh session (do not navigate to the Payroll or P&L panels first — this is the entire point of the test): log in as owner, immediately ask the AI Assistant a payroll or P&L question ("what's our gross payroll this period" / "how's our net income looking"). Confirm the answer contains real, non-zero, non-generic numbers. Only after getting that answer, manually open the Payroll and P&L panels and confirm the numbers match exactly — same source, same read-back, must be identical, not just plausible.

- [ ] **Step 4: Role-gate test**

Ask the same questions as (or verify directly via browser console as) a non-owner role. Confirm the restricted-access message (`"This data is restricted to the owner role."`), not a number and not a crash.

- [ ] **Step 5: Multi-tool-use exercise**

Ask a question plausibly triggering both tools in one turn ("give me a full financial and payroll picture" or similar). Confirm both tools' results appear correctly attributed in one coherent answer — this is the first real-world (not stubbed-fetch) exercise of the multi-tool-use path item 1's fix wave built.

- [ ] **Step 6: Push**

```bash
git push origin main
```

- [ ] **Step 7: Live-verify**

```bash
curl -s https://sairn.vercel.app/sairnbiz | grep -c "get_payroll_summary"
curl -s https://sairn.vercel.app/sairnbiz | grep -c "get_pl_summary"
```

Expected: both non-zero. Then repeat Step 3's cold-call test against this confirmed-deployed live version specifically (not a pre-deploy local copy), per the project's standing rule that a clean push is not proof the live app reflects the change.

- [ ] **Step 8: Update the spec's status line**

Edit `docs/superpowers/specs/2026-08-09-sairnbiz-payroll-pl-copilot-design.md`'s `**Status:**` line to note implementation is complete and live-verified, including explicit confirmation the cold-call test passed (not just "tests passed" generically — name what was verified), with today's date. Commit this doc-only change separately, push it.
