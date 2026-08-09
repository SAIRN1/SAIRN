# SAIRNbiz — Payroll/P&L Copilot

**Status:** Design approved by Michael 2026-08-09. Not yet implemented —
no code written under this spec. This is item 2 of the 6-item AI-native
roadmap for SAIRNbiz, building directly on the tool-calling foundation
from item 1 (`docs/superpowers/specs/2026-08-09-sairnbiz-ai-tool-calling-design.md`,
`docs/superpowers/plans/2026-08-09-sairnbiz-ai-tool-calling.md`) — the
`SB_TOOLS`/`sbRegisterTool`/`sbExecuteTool` dispatcher and `callAI()`'s
multi-turn round-trip already exist and are live-verified end-to-end.

## 1. Problem

The foundation shipped with exactly one tool, `get_employees` — a proof
of the mechanism, deliberately excluding compensation data. SAIRNbiz's
own Payroll and P&L panels already compute real, correct figures
(`rPay()`, `sairnbiz.html:1373`) — gross payroll, tax withholding,
benefits cost, revenue, COGS, gross profit, operating expenses, net
income, category breakdowns, and margin vs. a static industry
benchmark — but none of it is reachable by the AI assistant. This spec
adds two real, owner-gated tools so the assistant can answer financial
questions grounded in the business's actual numbers.

## 2. Non-goals (confirmed during brainstorming)

- **No per-employee payroll detail.** `get_payroll_summary` returns
  aggregate totals only (gross/tax/benefits/YTD) — matches the "Copilot"
  framing (period totals, tax breakdown) and keeps compensation data
  scoped the same deliberate way `get_employees` already excludes it.
  Per-employee pay lookup (`rPay()`'s per-row table, `sairnbiz.html:1376-1380`,
  rendered as an HTML string, not structured data) is a real scope
  increase explicitly deferred, not silently out of reach forever.
- **No refactor of `rPay()`.** It stays exactly as it is — a
  DOM-rendering function with real, working, money-calculating logic
  that the Payroll/P&L panels depend on today. The tools call it and
  read its rendered output rather than extracting a parallel pure
  computation path, trading a small amount of indirection for zero
  regression risk to working code (see §4).
- **No new arguments/periods.** Both tools take no input — same "current
  state, right now" scope as `get_employees`. A period-selectable
  version ("payroll for March") is real future work, not this pass's.
- **No write-capable tools, no new persistence** — same platform-wide
  rule as item 1, restated because every item in this roadmap restates it.

## 3. Tools

### `get_payroll_summary`

- **Sensitive:** `true` (owner-only — same role-gate `sbExecuteTool`
  already enforces, `sairnbiz.html:909-920`).
- **Input:** none (`{type:'object', properties:{}, required:[]}`).
- **Returns:** `{gross_payroll, taxes_fica, benefits, total_labor_cost, ytd_payroll}`,
  all real numbers (not currency-formatted strings — the model reasons
  over numbers, formats them in its own reply).
- **Description text** (goes to the model verbatim) discloses these are
  aggregate totals for active employees this period, no individual pay
  data included.

### `get_pl_summary`

- **Sensitive:** `true` (owner-only — same as above; aggregate business
  financials are treated as sensitive, matching item 1's original §5
  table, not re-litigated here).
- **Input:** none.
- **Returns:** `{revenue, cogs, gross_profit, operating_expenses, net_income, revenue_by_category, expense_by_category, gross_margin_pct, net_margin_pct, industry_avg_gross_margin_pct, industry_avg_net_margin_pct}`.
  `revenue_by_category`/`expense_by_category` are `{category: amount}`
  objects. The two `industry_avg_*` fields are static reference
  constants (45%/18%, same values `rPay()` already hardcodes at
  `sairnbiz.html:1402`) — the tool's description text explicitly states
  these are fixed industry-reference figures, not computed from this
  business's own data, so the model never presents them as if they were.

## 4. Data sourcing — read-back, not recompute

`rPay()` is `void` — it writes into `#py-gross`, `#pl-rev`, etc.
(`sairnbiz.html:1373-1403`) and returns nothing. The app already has an
established, working pattern for getting real numbers out of it:
`genReport('pl')` (`sairnbiz.html:1576-1582`) calls `rPay()`, then reads
back the rendered KPI `textContent` values and parses them with a local
helper (`pf`). This spec reuses that exact pattern rather than
refactoring `rPay()` into a computation-plus-render split — refactoring
a working, real-money-calculating function purely for architectural
cleanliness is a real regression risk the brainstorming discussion
explicitly rejected in favor of the lower-risk, precedent-matching
option.

**Shared helper, new:** `sbReadKpiNumber(elId)` — combines the DOM read
and the numeric parse in one call (`parseFloat(String($(elId).textContent).replace(/[^0-9.-]/g,''))||0`,
identical parsing logic to `genReport`'s local `pf`, but as a small
shared function both new tools use instead of each duplicating the
one-liner). Does not touch or replace `genReport`'s own local `pf` —
zero risk to that existing code path.

**Category breakdowns are re-derived, not read back.** `revenue_by_category`/
`expense_by_category` come from directly re-running the same trivial
grouping `rPay()` does inline (`sairnbiz.html:1391,1394`: group
`ld('sb_invs',[])`/`ld('sb_exps',[])` by `.cat`, sum `.amt`) rather than
parsing the rendered `#pl-revbk`/`#pl-expbk` HTML blocks. This is a
deliberate split: the *tax-rate math* (22% federal / 3.99% state / 7.65%
FICA, the $520 flat benefit assumption) is genuinely complex and
drift-prone, so those numbers get read back from `rPay()`'s own output,
never recomputed independently. The *category grouping* is a 3-line
reduce with no rate constants to drift — re-running it directly is
simpler than HTML-parsing and carries negligible duplication risk.
`expense_by_category`'s `Labor` entry is seeded from the same
`gross_payroll` value `get_payroll_summary` reads back (`rPay()`'s own
`expCats={Labor:gross}` at `sairnbiz.html:1394`), keeping the two tools'
numbers internally consistent even though they're separate calls.

**Margins are recomputed arithmetically**, not scraped from `#pl-margin`'s
rendered HTML (`sairnbiz.html:1402`, a multi-row innerHTML block) —
`gross_margin_pct = revenue>0 ? round(gross_profit/revenue*100) : 0`,
`net_margin_pct` the same shape with `net_income`. Identical formula to
`rPay()`'s own `gpm`/`npm`, applied to the same already-extracted
rev/gp/net numbers — no HTML parsing needed for this part either.

**The "cold call" risk, and why `run()` calls `rPay()` first, always.**
Every KPI element (`#py-gross`, `#pl-rev`, etc.) defaults to the literal
string `"$0"` in the static HTML (confirmed: `sairnbiz.html:517-521,611-615`)
until `rPay()` actually renders real values into them. If either tool's
`run()` read these elements *without* calling `rPay()` first, and the
user had never opened the Payroll or P&L panel this session, the tool
would return an honest-looking `{gross_payroll: 0, ...}` — a "blind
zero," the exact failure class `sairn-portfolio-triage` warns about
(a scanner or tool returning 0 that looks like a clean result but is
actually "never ran"). Both tools' `run()` therefore call `rPay()` as
their first line, unconditionally, every time — this is the one
non-negotiable detail in this spec's implementation.

## 5. Role gating

Both tools reuse the existing gate exactly as built in item 1 — no new
gating mechanism, no changes to `sbExecuteTool`. A `manager`/`employee`
asking either question gets `"This data is restricted to the owner
role."` (the same string already shipped), not a wrong number and not
a silent failure.

## 6. Testing

- **The cold-call test (primary, dedicated live test):** with a fresh
  page load — Payroll and P&L panels never manually opened this
  session — log in as owner and ask the AI Assistant a payroll or P&L
  question directly. Confirm the answer contains real, non-zero numbers
  matching what the Payroll/P&L panels show when opened afterward, not
  the static `"$0"` defaults. This is the one failure mode most likely
  to look like success (a plausible-sounding but wrong zero) and the
  one this spec's design section exists to prevent — verify it was
  actually prevented, don't assume the code review is sufficient.
- **Role-gate test:** ask the same questions as a non-owner role (or
  verify directly via `sbExecuteTool('get_payroll_summary', 'manager')`
  in console), confirm the restricted-access message, not a number.
- **Consistency test:** compare a tool's returned numbers against the
  same panel's on-screen KPIs after manually opening it — they must
  match exactly (same source, same read-back), not just be "close."
- **Multi-tool-use exercise:** ask a question that plausibly triggers
  both tools in one turn (e.g. "give me a full financial and payroll
  picture") — this is the first real-world exercise of the multi-tool-use
  path item 1's fix wave built and only unit-tested; confirm both tools'
  results appear correctly attributed in one answer.
- Standard structural checks (`checkblocks.py`, `div_balance_check.py`)
  after every `sairnbiz.html` change, per this project's standing rule.
