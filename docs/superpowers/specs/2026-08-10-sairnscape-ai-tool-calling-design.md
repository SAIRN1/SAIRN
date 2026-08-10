# SAIRNscape — AI Tool-Calling Foundation + `get_customers`

**Status:** Design approved 2026-08-10, following brainstorming. Not yet
implemented.

This is SAIRNscape's first tool-calling work, porting the mechanism
already proven live in SAIRNbiz, SAIRNlaw, and SAIRNvet — with a real,
pre-existing concurrency bug found and fixed as part of the same
rollout, and real server-verified roles reused rather than a fresh
auth model invented.

## 0. Why SAIRNscape, and why now (corrected assessment, 2026-08-10)

An earlier platform survey called this app's AI footprint "single fetch"
— an undercount, corrected here. `sairnscape.html` has 2 real AI call
sites: `scpCallAI()` (general chat, `sairnscape.html:2672`) and
`scpUploadProgressPhoto()` (`sairnscape.html:2292`, a real, well-built
vision feature that honestly reports blur/incomplete work rather than a
fabricated verdict — already good, untouched by this spec).

`scpCallAI()` grounds only on `custs.length` (a count, not records) —
the same shallow shape SAIRNbiz had before its own item 1. Real,
completely unused data sits right there: `scp_customers` (name, service,
recurring, phone, email, address, notes), plus `scp_jobs`,
`scp_schedule`, `scp_invoices`, `scp_quotes` (seed data,
`sairnscape.html:1844-1864`). `scpCustName(id)`
(`sairnscape.html:1867`) already resolves a `customer_id` to its real
name for other features.

**A real, more serious finding, not present in any prior rollout:**
`scpCallAI()` maintains a persistent, shared `scpAiHist` array
(`sairnscape.html:1650`) — multi-turn conversation history, the same
shape as SAIRNlaw's `aiHist`, not SAIRNvet's stateless per-question
design. It has **zero concurrency guard of any kind** — no busy-flag, no
sequence-number. Only the "Thinking..." placeholder DOM node is
protected against a race (via an existing direct-reference comment);
`scpAiHist` itself is not. This is the exact architecture shape that
caused SAIRNlaw's live-observed bug (cross-topic answer contamination, a
permanently stuck bubble) before `lawAiBusy` was added. Confirmed with
the user during brainstorming: fixing this is a **required part of this
rollout**, not optional or deferred — shipping tool-calling on top of an
unguarded shared history would very likely reproduce that exact
incident, not discover something new.

**Also found, in the other direction:** unlike SAIRNvet, SAIRNscape
already has real, server-verified auth — `SCP_AUTH_API`, employee ID +
PIN login, a bearer license token, and a genuine server-issued `role`
(`sairnscape.html:1729`, `1755`, `1790`). Two of its three real roles
(`owner`, `crew_lead`) already gate real operational authority elsewhere
in this file (`SCP_QC_AUTHORITY_ROLES`, `sairnscape.html:2228`, QC
sign-off). `scpCurrentRole()` (`sairnscape.html:2218`) is the existing
helper that reads the current session's real role from
`sessionStorage` — reused as-is by this spec, not reinvented.

## 1. Design decisions (confirmed with the user during brainstorming)

- **Concurrency fix: a busy-guard, same shape as SAIRNlaw's
  `lawAiBusy`**, not SAIRNvet's stale-response-discard convention. The
  architecture match matters: SAIRNlaw's shared-multi-turn-history shape
  is what `scpAiHist` has too, and a busy-guard is what actually protects
  the shared array from concurrent corruption — a discard pattern would
  only hide the symptom in the UI, not fix the underlying race.
- **The dispatcher includes a `sensitive`/role-gate parameter now**, even
  though `get_customers` itself is non-sensitive. Unlike SAIRNvet (where
  this was deliberately omitted — a self-selected, non-verified role
  would make the gate purely cosmetic), SAIRNscape's roles are genuinely
  server-verified and already used for real authority elsewhere in this
  exact file. Including the gate now means it's immediately meaningful
  the moment a real sensitive tool is proposed, no retrofit required.

## 2. Non-goals (explicitly deferred)

- **No real tool beyond `get_customers` in this pass.** `scp_jobs`/
  `scp_schedule`/`scp_invoices`/`scp_quotes` tools are later, separate
  scope, following the same "one tool, deliberately" discipline used on
  every prior rollout.
- **No write-capable tool.** Read-only, matching every other tool on
  this platform.
- **No new persistence.** Reads live from `scpLd('scp_customers', [])`
  — nothing new is stored.
- **No changes to `scpUploadProgressPhoto()`.** Already a real, correct
  feature — untouched.
- **No changes to `api/claude.js`.** `sanitizeTools()` already passes
  custom tools through for every `app_id` in `KNOWN_APP_IDS`,
  `sairnscape` included.

## 3. Architecture

- `SCP_TOOLS = {}` — plain object registry.
- `scpRegisterTool(name, description, inputSchema, sensitive, run)` —
  same shape as `sbRegisterTool`/`lawRegisterTool`.
- `scpExecuteTool(name, role, input)` — unknown tool → honest error;
  `sensitive && role !== 'owner'` → access-restricted error, no
  execution (exact same single-role check as `sbExecuteTool`/
  `lawExecuteTool` — not SAIRNscape's separate, existing
  `SCP_QC_AUTHORITY_ROLES` multi-role concept, which is a different
  feature's own gate and not something this dispatcher inherits);
  otherwise `tool.run(input || {})` inside
  try/catch, a thrown error becomes an honest `{ok:false}`, never a
  crash. `role` is supplied by the caller from `scpCurrentRole()`
  (`sairnscape.html:2218`) at call time — not cached in a global
  variable the way SAIRNbiz/SAIRNlaw's `prole` is, since SAIRNscape
  already reads the role on-demand from `sessionStorage` via this
  existing helper and this spec doesn't change that convention.
- `scpAiBusy` — new boolean guard. `scpSendAI()` checks it first and
  rejects with a toast if busy; `scpCallAI()` sets it `true` at start and
  clears it in a `finally` block covering every exit path (no-tool-use
  return, tool-use round-trip completion, and thrown errors alike) —
  same shape as `lawAiBusy`.
- `scpCallAI()` rewired: build `toolDefs` from `SCP_TOOLS`; first
  `fetch` sends `tools:toolDefs`. If a `tool_use` block comes back, call
  `scpExecuteTool(toolUse.name, scpCurrentRole(), toolUse.input)`, build
  a `tool_result` (error path includes the same "do not estimate"
  instruction already proven on the other three apps), push the
  assistant tool-use turn and the tool-result turn onto `scpAiHist`, then
  make a second `fetch` (no `tools` field) for the final answer. If no
  `tool_use`, behave exactly as today. The existing placeholder-by-
  reference pattern (`thinkingEl`) is preserved unchanged — it already
  does the right thing, per its own comment; only `scpAiHist` was
  unguarded, not the placeholder.

## 4. Tool: `get_customers`

- **Sensitive:** `false` — customer contact/service data carries the
  same trust level as the rest of the app today; no panel in SAIRNscape
  is role-gated for viewing this data (only QC sign-off authority is
  gated, a different, action-based concern).
- **Input:** `{}` — no arguments, matching every prior tool's v1 shape.
- **Backing function:** `scpLd('scp_customers', [])`, no new lookup
  logic needed (`scpCustName` is for resolving an id elsewhere, not
  needed here since this tool returns the full customer records
  directly, not id-references).
- **Returns (per customer):** `{name, service, recurring, phone, email,
  address}`. Excludes `id` (not meaningful to the model) and `notes`
  (free text that may contain anything a customer told the company in
  confidence — same discipline as `get_matters`/`get_deadlines`
  excluding their own notes fields).
- **Description discloses, up front:** this tool does not include job
  history, schedule, invoices, or quotes — those aren't tool-backed yet.

## 5. Testing

- **Pure dispatcher test:** `scpExecuteTool()` — unknown tool → honest
  error; sensitive tool + disallowed role → restricted error; thrown
  error inside `run()` → `{ok:false}`, never a crash.
- **Tool-level test:** `SCP_TOOLS.get_customers.run({})` against a
  stubbed `scpLd` — confirm `id`/`notes` never appear in the output.
- **Real interaction test:** ask "what customers do we have," "what
  service does Diane Ferraro have" — confirm real names/services/contact
  info from `scp_customers`, not a refusal or a generic answer.
- **Concurrency test (the load-bearing one for this rollout):** send two
  questions back-to-back before the first resolves — confirm the second
  is rejected with a toast before it touches `scpAiHist`, exactly one
  message bubble pair results, and `scpAiHist` stays a clean, correctly-
  ordered sequence for the first call. This is the direct regression
  test for the concurrency bug this spec fixes.
- **Role-gate mechanism test:** even with only `get_customers` (non-
  sensitive) in v1, confirm the gate mechanism itself: a temporary
  sensitive test tool correctly blocks `'crew_lead'` and `'office'`
  (real `scpCurrentRole()` values) and allows `'owner'` — same
  single-role check as `sbExecuteTool`/`lawExecuteTool`.
- Standard structural checks (`tools/checkblocks.py sairnscape.html`,
  `tools/div_balance_check.py sairnscape.html`) after every change.
- Full Guardian v2 pass before push; live-verify against
  `sairn.vercel.app/sairnscape` after push — both steps of the Push
  Protocol, neither optional.
