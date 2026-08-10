# SAIRNcode — AI Tool-Calling Foundation + `get_providers`

**Status:** Design approved 2026-08-10, following brainstorming. Not yet
implemented.

This is SAIRNcode's first tool-calling work, porting the mechanism
already proven live in SAIRNbiz, SAIRNlaw, SAIRNvet, SAIRNscape,
SAIRNgrounds, and StoneDesk — the simplest rollout so far, since two of
the recurring design questions on other apps don't apply here at all.

## 0. Why SAIRNcode, and why the design is simpler here

Confirmed (not an undercount, unlike several other apps this platform
survey corrected): SAIRNcode has **exactly 1 real AI call site**,
`sendChatMessage()` (`sairncode.html:2548`). It is single-shot — no
shared history array is ever built (`messages:[{role:'user',
content:message}]`, one message per call, nothing accumulated across
turns) — grounded only in a static `SAIRNCODE_SYSTEM_PROMPT` persona
("certified medical coding expert"). Two consequences follow directly:

- **No concurrency bug exists here.** There is no shared mutable state
  a second concurrent call could corrupt — the same safe shape as
  SAIRNvet's `askAI()` before tool-calling was added there. No busy-
  guard is needed.
- **No real server-verified auth exists.** `sc_role` comes from a
  purely client-side PIN gate (`PINS[role]`, a hardcoded map checked at
  login, `sairncode.html:1411-1425`) — confirmed by grep that no
  `SC_AUTH_API` or equivalent backend exists anywhere in this file.
  Same trust class as SAIRNvet's self-selected dropdown — a sensitivity/
  role-gate here would restrict nothing a user couldn't bypass by
  picking a different PIN-role combination. The dispatcher omits the
  concept entirely, same decision already made for SAIRNvet.

**Real, unused data**: `sc_providers` (`sairncode.html:2465-2476`) — a
clean roster: `{id, name, specialty, license, cred, perf}`. Plus a much
larger medical-coding/billing data model sitting untouched:
`sc_ar`, `sc_denial`, `sc_drg`, `sc_hcc`, `sc_rac`, `sc_compliance`,
`sc_fraud`, `sc_revenue`, `sc_prebill`, `sc_telehealth`,
`sc_anesthesia` — all separate, later scope.

## 1. Design decisions

- **No sensitivity/role-gate parameter** — confirmed above, no real
  auth exists to enforce it meaningfully.
- **No concurrency guard** — confirmed above, nothing shared to
  corrupt in a single-shot, stateless chat.
- **`get_providers` is the v1 proof tool** — same roster-shape
  precedent as `get_employees`/`get_matters`/`get_patients`/
  `get_customers`/`get_properties`.

## 2. Non-goals (explicitly deferred)

- **No real tool beyond `get_providers` in this pass.** Tools over
  `sc_ar`/`sc_denial`/`sc_drg`/`sc_hcc`/`sc_rac`/`sc_compliance`/
  `sc_fraud`/`sc_revenue`/`sc_prebill`/`sc_telehealth`/`sc_anesthesia`
  are later, separate scope.
- **No write-capable tool.** Read-only, matching every other tool on
  this platform.
- **No new persistence.** Reads `getProviderEntries()`
  (`sairncode.html:2465`) directly — nothing new is stored.
- **No changes to `api/claude.js`.** `sanitizeTools()` already passes
  custom tools through for every `app_id` in `KNOWN_APP_IDS`,
  `sairncode` included.

## 3. Architecture

- `SC_TOOLS = {}` — plain object registry.
- `scRegisterTool(name, description, inputSchema, run)` — same shape
  as SAIRNvet's `svRegisterTool` (no `sensitive` parameter, per §1).
- `scExecuteTool(name, input)` — unknown tool → honest error;
  otherwise `tool.run(input || {})` inside try/catch, a thrown error
  becomes an honest `{ok:false}`, never a crash. No role check.
- `sendChatMessage()` rewired: build `toolDefs` from `SC_TOOLS`; the
  existing single `fetch` call gains a `tools:toolDefs` field. If a
  `tool_use` block comes back, call `scExecuteTool(toolUse.name,
  toolUse.input)`, build a `tool_result`, make a second `fetch` (no
  `tools` field) with `[{role:'user',content:message},
  {role:'assistant',content:blocks}, {role:'user',content:
  [tool_result]}]` for the final answer. If no `tool_use`, render the
  first call's text directly, exactly as today.

## 4. Tool: `get_providers`

- **Input:** `{}` — no arguments, matching every prior tool's v1 shape.
- **Backing function:** `getProviderEntries()` (`sairncode.html:2465`),
  no new lookup logic.
- **Returns (per provider):** `{name, specialty, license, cred,
  perf}`. Excludes `id` (not meaningful to the model).
- **Description discloses, up front:** this tool only covers the
  provider roster — no A/R, denials, DRG, HCC, RAC, compliance, fraud,
  revenue, prebill, telehealth, or anesthesia data is available.

## 5. Testing

- **Pure dispatcher test:** `scExecuteTool()` — unknown tool → honest
  error; thrown error inside `run()` → `{ok:false}`, never a crash.
- **Tool-level test:** `SC_TOOLS.get_providers.run({})` against a
  stubbed `getProviderEntries()` — confirm `id` never appears in the
  output.
- **Real interaction test:** ask "who are our credentialed providers,"
  "what's Dr. Chen's specialty" — confirm real names/specialties/
  credentialing status from `sc_providers`, not a generic answer.
- **No-tool-use regression test:** ask a generic medical-coding
  question unrelated to providers — confirm it still answers directly
  from the persona, exactly as today, with no tool invoked.
- Standard structural checks (`tools/checkblocks.py sairncode.html`,
  `tools/div_balance_check.py sairncode.html`) after every change.
- Full Guardian v2 pass before push; live-verify against
  `sairn.vercel.app/sairncode` after push — both steps of the Push
  Protocol, neither optional.
