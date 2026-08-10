# SAIRNbiz — Hiring Cost-Impact Reasoning

**Status:** Implementation complete 2026-08-10. **A real output-integrity
issue was found during Task 3's live verification (the AI fabricating
substitute financial figures instead of relaying a tool denial/error, in
two separate live scenarios) and has been fixed, platform-wide, in the
same commit range** (`b189b38`, pushed to main and live-verified against
sairn.vercel.app/sairnbiz) — see "Findings from live testing" and "Fix
and re-verification" below before trusting any status claim past this
line. This is item 5 of the 6-item AI-native roadmap for SAIRNbiz,
building on items 1-2 (tool-calling foundation,
`get_payroll_summary`/`get_pl_summary`).

Specific tests that passed live, against the confirmed-deployed app, via
a real owner-role chat session (login bypassed via `sbApplyLoggedIn`,
same technique as items 2-4):
- **Reuse-not-drift test:** direct `get_payroll_summary`/`get_pl_summary`
  calls in-session returned `total_labor_cost:18680`,
  `net_income:18028`, `net_margin_pct:41`; a subsequent hiring-cost
  question in the same session invoked `get_hiring_cost_impact`, whose
  response carried `current_total_labor_cost:18680`,
  `current_net_income:18028`, `current_net_margin_pct:41` — an exact
  match, confirmed genuine reuse rather than a second computed copy.
- **Math/position-context test:** `$28/hr` Full Time → `28×80=2240`
  gross, `2240×0.0765=171.36` FICA, `+520` benefit → `2931.36` fully
  loaded, added/subtracted correctly against the real current totals
  (`projected_total_labor_cost:21611.36`, `projected_net_income:15096.64`,
  `projected_net_margin_pct:34`) — all arithmetic verified by hand.
  Asking about the real open "Senior Fabricator" requisition
  (`sairnbiz.html:1347`) correctly surfaced `dept:Fabrication`,
  `stage:Interviewing`, `posted_rate_range:$26-30/hr` in the tool result
  and the AI's rendered answer. A hypothetical non-matching position
  ("Junior Welder Apprentice") answered correctly with no error and no
  `position_context` field.
- **Role-gate test (tool level, passed):** `sbExecuteTool` correctly
  returned `{ok:false, error:"This data is restricted to the owner
  role."}` for a `manager` role, both via direct call and via the live
  chat's actual tool_result.

**Findings from live testing (both fixed 2026-08-10, see below) — two
separate incidents, not one:**
1. **Non-owner-role denial fabrication.** The AI's rendered reply to a
   denied `manager`-role request did not always just relay the
   restriction — in 2 of 2 live runs it followed the restriction message
   with a self-generated, non-tool-backed cost estimate (invented
   workers'-comp rate, FUTA/SUTA, benefit range), despite the system
   prompt's then-existing "say so plainly instead of guessing an answer"
   instruction.
2. **Owner-role tool-skip free-hand arithmetic (separate incident, not
   previously promoted out of the Task 3 report).** In an owner-role
   session with the tool fully available, a differently-phrased
   follow-up question ("give me the exact figures you used in the
   calculation," asked after payroll+P&L+hiring-cost tool results were
   already in the conversation history) caused the model to skip calling
   `get_hiring_cost_impact` again and instead answer from its own
   arithmetic — which in the original Task 3 test run was wrong. This is
   arguably more concerning than incident 1: it happened on the *owner*
   role, with no access restriction in play at all, purely from question
   phrasing / conversational state.

Root cause (diagnosed during the fix wave, corrects an earlier
diagnosis that assumed the issue was specific to this tool's
description): `callAI()` makes two proxy calls per exchange. Only the
FIRST sends the `tools` array; the SECOND — the one that generates the
actual rendered reply after a tool_result comes back — sends no `tools`
field at all, so a tool's description has zero influence on that turn.
The trigger is question phrasing / conversational state, not which tool
was involved, so this affects every current and future sensitive tool,
not just `get_hiring_cost_impact`.

**Fix and re-verification (2026-08-10, commit `b189b38`):** `callAI()`'s
system prompt now explicitly forbids ANY substitute figure (not just "an
answer"), positioned at the end of system-prompt construction; the
tool_result error string built for denials/errors now also carries an
adjacent, explicit "do not estimate" instruction. Re-tested live against
the deployed fix:
- Non-owner-role denial (incident 1 scenario): 2/2 clean — both runs
  stated the restriction plainly with zero fabricated numbers.
- Owner-role "give me the exact figures" follow-up (incident 2
  scenario): 2/2 improved — the model still did not call the tool again
  on this specific follow-up, but both times it correctly relayed the
  real numbers already present in conversation history instead of
  free-handing new (and previously wrong) arithmetic.
This is a prompt-level mitigation, not a structural guarantee — it
reduces the frequency and severity of fabrication but cannot
mechanically eliminate it, since the underlying two-call/no-tools-on-
the-second-call architecture is unchanged. Small live sample size (2
runs per scenario); treat as directional evidence, not proof.

## 1. Problem

`sb_hire` (the hiring pipeline) and `sb_emps`/payroll data have never
been reasoned over together. An owner reviewing an open requisition has
no way to ask "what does filling this role actually do to our labor
cost and margin" and get a real, computed answer — only two separate
panels (Hiring, Payroll) with no connection between them.

## 2. Real constraint found during design

`sb_hire.rate` (the requisition's posted pay range) is genuinely
unparseable free text — the input field's own placeholder is
`"$18-22/hr"`, and real seed data holds `'$26-30/hr'`, `'$17-20/hr'`,
`'$18-22/hr'` (`sairnbiz.html:1320-1322`). There is no validation on
this field; a user could type anything. Rather than regex-parsing a
free-text field that was never designed to be machine-read (fragile,
breaks the moment someone types "TBD" or "$50k/yr"), the tool takes an
explicit numeric `hourly_rate` argument. The requisition's own stored
range can still be surfaced as unparsed reference text when a position
is named, but the real math never depends on parsing it.

## 3. Architecture

**Reuse, not duplication — confirmed feasible during design.**
`get_payroll_summary`'s and `get_pl_summary`'s computations
(`sairnbiz.html:960-976`, `983-1027`) are defined inline inside their
`sbRegisterTool` calls, not extracted into standalone functions the way
`checkPayrollAnomalies()`/`checkAttentionItems()` were. But `SB_TOOLS`
(the tool registry, `sairnbiz.html:888`) is a top-level `var`, so this
new tool's `run()` can call `SB_TOOLS['get_payroll_summary'].run()` and
`SB_TOOLS['get_pl_summary'].run()` directly — reusing their exact real
output with zero duplication and zero changes to either already-shipped,
already-final-reviewed tool. This is an internal, same-privilege-level
call (the caller already passed the owner-only gate to reach this new
tool's own `run()` in the first place), not a role-gate bypass.

**New pure function, `computeHiringCostImpact(hourlyRate, employmentType, payrollSummary, plSummary)`** —
takes already-fetched data as arguments (not global lookups), so it's
fully Node-testable with no `SB_TOOLS`/`rPay()`/DOM stubbing needed. The
new tool's `run()` is a thin wrapper: look up `SB_TOOLS`'s two other
tools, optionally look up a named position in `sb_hire`, call this pure
function, return the result.

**Computation:**
```
new_role_hours = employment_type === 'Full Time' ? 80 : 32   // matches rPay()'s own convention
new_role_gross = hourly_rate * new_role_hours
new_role_fica  = new_role_gross * 0.0765                     // same FICA rate get_payroll_summary already uses/discloses
new_role_benefit = 520                                        // same flat assumption get_payroll_summary already uses/discloses
new_role_fully_loaded_cost = new_role_gross + new_role_fica + new_role_benefit

projected_total_labor_cost = payrollSummary.total_labor_cost + new_role_fully_loaded_cost
projected_net_income = plSummary.net_income - new_role_fully_loaded_cost   // assumes zero revenue increase
projected_net_margin_pct = plSummary.revenue > 0 ? round(projected_net_income / plSummary.revenue * 100) : 0
```

**Scope, decided explicitly during brainstorming:**
- **Company-wide cost only.** No new per-department cost aggregation —
  `rEmps()` only counts headcount per department today, nothing sums
  `rate×hours` by department anywhere in the app. Building that is a
  real, separate scope increase; this tool reuses `get_payroll_summary`'s
  existing company-wide `total_labor_cost` as-is.
- **Margin impact included.** The roadmap explicitly names "labor cost
  / margin," and the reuse pattern already established for payroll
  extends cheaply to P&L — `get_pl_summary` reused the same way.

## 4. Tool: `get_hiring_cost_impact`

- **Sensitive:** `true` (owner-only — consistent with every other
  financial tool: `get_payroll_summary`, `get_pl_summary`,
  `get_payroll_anomalies`, `get_attention_digest`).
- **Input:** `{position?: string, hourly_rate: number (required), employment_type: 'Full Time'|'Part Time' (required)}`.
  If `position` matches a real open `sb_hire` record (by `pos`), include
  that record's `dept`, `stage`, and posted `rate` range (as unparsed
  reference text, never used in the math) in the response. Gracefully
  omitted if not provided or no match — this tool is not required to
  reference a real open requisition to answer a hypothetical question.
- **Returns:** `{position_context?, new_role_gross, new_role_fica, new_role_benefit, new_role_fully_loaded_cost, current_total_labor_cost, projected_total_labor_cost, current_net_income, current_net_margin_pct, projected_net_income, projected_net_margin_pct}`.
- **Description discloses, explicitly, up front (learning from items
  2-4's pattern of needing a fix round for exactly this):** this is a
  "nothing else changes" projection — assumes zero revenue increase
  from the hire, applies the same simplified FICA-only-tax/flat-$520-
  benefit assumptions `get_payroll_summary` already discloses as
  incomplete, and excludes one-time hiring costs (recruiting,
  onboarding, ramp-up time to full productivity).

## 5. Testing

- **Pure-function test (primary):** `computeHiringCostImpact()` takes
  plain arguments, no live data needed — verify the arithmetic directly
  against hand-computed values for a few realistic rate/type
  combinations, including the "zero revenue" and "zero current labor
  cost" edge cases (division-by-zero guards).
- **Reuse-not-drift test:** confirm the tool's `current_total_labor_cost`
  and `current_net_income`/`current_net_margin_pct` genuinely match what
  `get_payroll_summary`/`get_pl_summary` return when called directly in
  the same session — not a second, independently-computed (and
  potentially drifting) version of the same numbers.
- **Position-context test:** ask about a real open requisition by name
  → confirm department/stage/posted-range context appears. Ask with no
  `position` or a non-matching one → confirm the tool still answers
  (hypothetical-only), no error, no missing-context failure.
- **Role-gate test:** confirm a non-owner role gets the restricted-access
  message, not a number.
- Standard structural checks (`checkblocks.py`, `div_balance_check.py`)
  after every `sairnbiz.html` change.
