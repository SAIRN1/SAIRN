# SAIRNlaw — `get_deadlines` AI Tool

**Status:** Design approved 2026-08-10, following brainstorming. Not yet
implemented — this spec precedes the implementation plan and explicit
go-ahead, per the user's request to gate this one on an explicit approval
before any code (unlike `get_matters`, which was pre-approved straight
through to execution).

This is the second tool on SAIRNlaw's AI tool-calling foundation
(`docs/superpowers/specs/2026-08-10-sairnlaw-ai-tool-calling-design.md`,
live at `sairn.vercel.app/sairnlaw`), and the highest-value tool
explicitly deferred from that first pass (its §2 Non-goals named
`get_deadlines` as the "arguably highest-value tool" left for later).
Real stakes, not hypothetical: a missed filing or statute-of-limitations
deadline is a malpractice exposure, not an inconvenience — this is
explicitly why the user wants this tool next rather than any other.

## 1. Problem

`LAW_FIRM_DATA_RULE` (`sairnlaw.html:1403`) currently tells the AI
assistant it has no access to this firm's deadlines and must refuse and
redirect to the Deadlines/Calendar panel. `rDash()` (`sairnlaw.html:1575`)
already computes real overdue and "due this week" deadline counts for the
dashboard, but that logic is dashboard-only — the AI assistant has no way
to answer "what's coming up" or "what's overdue" despite the firm's own
real deadline data sitting in `law_deadlines`, unused by the assistant.

## 2. Design decisions (confirmed with the user during brainstorming)

- **Urgency tiers reuse `rDash()`'s own existing convention verbatim, not
  a new one.** `rDash()` already defines two thresholds for its own
  dashboard cards: overdue is `status==='Pending' && due_date < today`
  (string comparison against `lawLocalToday()`, `sairnlaw.html:1577-1579`
  area), and "due this week" is `status==='Pending' && due_date` within 7
  days of `Date.now()` (millisecond comparison against
  `Date.now()+7*24*60*60*1000`, `sairnlaw.html:1578`). This tool computes
  `urgency` the same two ways, for the same two thresholds — "Overdue" /
  "Due soon" (within 7 days) / "Upcoming" (later) — not a redesigned
  scheme. Reuses the app's own definition of urgency rather than
  inventing a competing one the dashboard and the AI could disagree on.
- **No type-based severity weighting.** `type` (Statute of Limitations,
  Court Deadline, Hearing, Filing Deadline, Other) stays in the tool's
  output as plain data, but urgency is purely date-driven — the tool does
  not decide that one deadline *type* matters more than another at the
  same due date. That's a legal-practice judgment, not a data question,
  and not this tool's place to encode.
- **`status:'Pending'` only.** Matches `rDash()`'s own attention/upcoming
  cards, which never surface `Complete` deadlines. This tool answers
  "what needs action," not a historical log — a completed-deadlines
  history tool (if ever wanted) is separate, later scope.
- **Non-sensitive**, same trust level as `get_matters`. Confirmed via
  grep: zero panels or data are role-gated in SAIRNlaw except one
  unrelated admin/security-card visibility check
  (`s.role==='owner'`, `sairnlaw.html:2975`) — nothing gates the
  Deadlines/Calendar panel itself, so gating this tool would be a new,
  unexplained restriction relative to the rest of the app.

## 3. Non-goals (explicitly deferred)

- **No write-capable tool.** Marking a deadline complete, rescheduling,
  or creating one via AI is out of scope — read-only, matching every
  other tool on this platform.
- **No new persistence.** Reads live from `ld('law_deadlines', [])` via
  the existing `deadlines()` helper (`sairnlaw.html:1297`) — nothing new
  is stored.
- **No completed-deadline history tool.** If ever wanted, that's separate
  scope with its own explicit decision, not folded in here by default.
- **No trust-accounting, billing, or time-entry tool.** Still no tool and
  no data for those — `LAW_FIRM_DATA_RULE`'s refusal for them is
  unchanged by this spec.
- **No optional filter arguments** (e.g., by matter, by date range) in
  this pass — `{}`, argument-free, same v1-minimalism as `get_matters`.
  A filtered variant is easy to add later once the unfiltered tool is
  proven, not before.

## 4. Architecture

Reuses the existing dispatcher (`LAW_TOOLS`/`lawRegisterTool`/
`lawExecuteTool`, `sairnlaw.html:1420-1444` area) with zero changes to
it — this is purely a second `lawRegisterTool(...)` call plus one
`LAW_FIRM_DATA_RULE` edit. No changes to `sendAI()`, `api/claude.js`, or
the concurrency guard (`lawAiBusy`) — all already generic across however
many tools `LAW_TOOLS` holds.

**New pure function, `computeDeadlineUrgency(dueDate, today, weekAheadMs)`**
— takes already-known values as arguments (not global lookups), so it's
fully Node-testable with no `ld()`/DOM stubbing needed, following the
same pattern `computeHiringCostImpact()` used in SAIRNbiz's hiring-cost
spec. The tool's `run()` is a thin wrapper: read `deadlines()`, filter to
`status==='Pending'`, map each to the output shape below, calling this
pure function once per deadline for its `urgency` value.

## 5. Tool: `get_deadlines`

- **Sensitive:** `false`.
- **Input:** `{}` — no arguments, matching `get_matters`'s v1 shape.
- **Backing function:** `deadlines()` (`sairnlaw.html:1297`) filtered to
  `status==='Pending'`, plus `matterLabel()` (`sairnlaw.html:1304`) to
  resolve `matter_id` to a real matter number + name rather than exposing
  a raw ID the model has no way to interpret (same convention
  `get_matters` used for `client_id`).
- **Returns (per pending deadline):** `{matter, type, title, due_date,
  due_time, location, urgency}`. `matter` is `matterLabel(d.matter_id)`.
  `urgency` is one of `"Overdue"`, `"Due soon"`, `"Upcoming"` per §2.
  Excludes `notes` (free text, same discipline as `get_matters` excluding
  its own `notes` field — may contain case-strategy detail out of scope
  for a first, deliberately minimal tool) and `end_time`/`created_at`
  (not useful to a consumer of this tool).
- **Description discloses, up front:** this tool only returns `Pending`
  deadlines (not completed ones), and urgency is computed live from the
  due date, not from any stored status — matching the edited
  `LAW_FIRM_DATA_RULE` so the model's own behavior stays consistent with
  what the tool actually returns.

## 6. `LAW_FIRM_DATA_RULE` edit

Same precise field-level edit pattern as the `get_matters` rollout — not
a blanket rewrite. Deadlines move from "not available" to "available via
`get_deadlines`, Pending only, urgency computed live." Trust account
balances, invoices, time entries, and billing records remain genuinely
unavailable, and the refusal instruction for those stays exactly as
strict as it is today.

## 7. Testing

- **Pure-function test (primary):** `computeDeadlineUrgency()` takes
  plain arguments — verify directly against hand-computed values: a date
  before today → `"Overdue"`, a date within 7 days → `"Due soon"`, a date
  further out → `"Upcoming"`, plus the boundary case (exactly 7 days out)
  matching whichever side `rDash()`'s own `<=` comparison falls on.
- **Tool-level test:** `LAW_TOOLS.get_deadlines.run({})` against a
  stubbed `deadlines()`/`matterLabel()` — confirm `Complete` deadlines
  are excluded, `matter` is a resolved label not a raw ID, and `notes`
  never appears in the output.
- **Real interaction test:** ask "what deadlines are coming up" / "is
  anything overdue" — confirm the answer contains real matter names,
  titles, and due dates from `law_deadlines`, not the old refusal.
- **Refusal-preserved test:** ask a trust-balance or billing question —
  confirm the model still refuses and redirects, proving this tool's
  addition didn't loosen the refusal for still-unavailable data.
- **Consistency-with-dashboard spot check:** compare the tool's Overdue/
  Due-soon counts against `rDash()`'s own `k-deadlines` dashboard number
  for the same real data, at the same moment — they should agree, since
  both now use the same thresholds. A mismatch would mean the port
  diverged from `rDash()`'s actual logic somewhere.
- **Concurrency regression check:** confirm `lawAiBusy` still correctly
  blocks a second send while a `get_deadlines`-triggering exchange is in
  flight — this tool doesn't change the guard, but a second tool
  existing is the first real chance to confirm the guard generalizes
  past the single-tool case it was fixed and verified against.
- Standard structural checks (`tools/checkblocks.py sairnlaw.html`,
  `tools/div_balance_check.py sairnlaw.html`) after every change.
- Full Guardian v2 pass before push; live-verify against
  `sairn.vercel.app/sairnlaw` after push — both steps of the Push
  Protocol, neither optional.
