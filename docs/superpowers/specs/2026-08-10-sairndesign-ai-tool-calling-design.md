# SAIRNdesign — AI Tool-Calling Foundation + `get_clients`

**Status:** Design approved 2026-08-10, following brainstorming. Not yet
implemented.

This is SAIRNdesign's first tool-calling work, porting the mechanism
already proven live on every prior rollout — extending an already
unusually sophisticated concurrency fix rather than replacing it.

## 0. Why SAIRNdesign, and what's already good here

SAIRNdesign has 2 real AI features: `sendAI()` (general chat,
`sairndesign.html:1212`) and a genuinely excellent Spec Sheet
compliance-review feature (`sairndesign.html:1378`, untouched by this
spec). The compliance feature computes real deterministic findings
(budget overage, lead-time-vs-install-date conflicts) *before* calling
Claude, and explicitly instructs the model to *"NEVER invent or suggest
alternative furniture/products"* — one of the better anti-fabrication
patterns on this platform. It already has its own correct concurrency
guard (`complianceCheckSeq`) and is not touched here.

`sendAI()` grounds on nothing but a static persona — no real business
data reaches it. Its concurrency handling is more sophisticated than
most apps' starting chat: a live 2026-08-09 fix
(`sairndesign.html:1220-1230`) records each request's own user-turn
index (`myUserIdx`) at push time and splices the assistant reply back
in at `myUserIdx+1` when it resolves — correctly re-ordering `aiHist`
regardless of which of two concurrent requests' responses arrives
first, rather than a simple discard-stale or block-second-send
approach. This spec extends that exact mechanism rather than replacing
it with a different pattern.

**No real auth exists.** `prole` comes from a client-side PIN match
(`sairndesign.html:1019` area) — no server backend. Same trust class as
SAIRNbuild/SAIRNvet/SAIRNcode.

**Real, unused data**: `sdn_clients` (`sairndesign.html:1100`) — `{id,
name, company, phone, email, address, status, notes}` — plus
`sdn_projects`, `sdn_specitems`, `sdn_vendors`, `sdn_contracts`,
`sdn_invoices`, `sdn_proposals`, `sdn_team`, `sdn_schedule` — all
separate, later scope.

## 1. Design decisions

- **No sensitivity/role-gate parameter** — no real auth exists here.
- **No new concurrency mechanism** — the existing `myUserIdx`-splice
  fix is extended to splice a group of entries (not just one) at the
  same recorded index, preserving its exact intent.
- **`get_clients` is the v1 proof tool** — same roster-shape precedent
  as `get_employees`/`get_matters`/`get_patients`/`get_customers`/
  `get_properties`/`get_jobs`/`get_providers`.

## 2. Non-goals (explicitly deferred)

- **No real tool beyond `get_clients` in this pass.** Tools over
  `sdn_projects`/`sdn_specitems`/`sdn_vendors`/`sdn_contracts`/
  `sdn_invoices`/`sdn_proposals`/`sdn_team`/`sdn_schedule` are later,
  separate scope.
- **No write-capable tool.** Read-only, matching every other tool on
  this platform.
- **No new persistence.** Reads `clients()` (`sairndesign.html:1077`)
  directly — nothing new is stored.
- **No changes to the Spec Sheet compliance-review feature**
  (`sairndesign.html:1378`) — already real, correct, untouched.
- **No changes to `api/claude.js`.** `sanitizeTools()` already passes
  custom tools through for every `app_id`, `sairndesign` included.

## 3. Architecture

- `SDN_TOOLS = {}` — plain object registry.
- `sdnRegisterTool(name, description, inputSchema, run)` — same shape
  as SAIRNvet's/SAIRNcode's/SAIRNbuild's (no `sensitive` parameter).
- `sdnExecuteTool(name, input)` — unknown tool → honest error;
  otherwise `tool.run(input || {})` inside try/catch, a thrown error
  becomes an honest `{ok:false}`, never a crash.
- `sendAI()` rewired: build `toolDefs` from `SDN_TOOLS`; the existing
  fetch gains a `tools:toolDefs` field. If a `tool_use` block comes
  back, call `sdnExecuteTool(toolUse.name, toolUse.input)`, build a
  `tool_result`, make a second `fetch` (no `tools` field) for the final
  answer. **The existing splice-based reordering fix is preserved**:
  instead of splicing a single `{role:'assistant',content:text}` entry
  at `myUserIdx+1`, the tool-use path splices the full three-entry
  group (`{role:'assistant',content:blocks}`,
  `{role:'user',content:[tool_result]}`,
  `{role:'assistant',content:finalText}`) as one unit at that same
  `myUserIdx+1` — preserving the fix's exact "insert relative to this
  request's own recorded position" behavior rather than introducing a
  different ordering mechanism for this path. If no `tool_use` block,
  behave exactly as today (single-entry splice, unchanged).

## 4. Tool: `get_clients`

- **Input:** `{}` — no arguments, matching every prior tool's v1 shape.
- **Backing function:** `clients()` (`sairndesign.html:1077`), no new
  lookup logic.
- **Returns (per client):** `{name, company, phone, email, address,
  status}`. Excludes `id` (not meaningful to the model) and `notes`
  (free text — same discipline as every prior tool's notes-exclusion).
- **Description discloses, up front:** this tool only covers the
  client roster — no project, spec-item, vendor, contract, invoice,
  proposal, team, or schedule data is available.

## 5. Testing

- **Pure dispatcher test:** `sdnExecuteTool()` — unknown tool → honest
  error; thrown error inside `run()` → `{ok:false}`, never a crash.
- **Tool-level test:** `SDN_TOOLS.get_clients.run({})` against a
  stubbed `clients()` — confirm `id`/`notes` never appear in the
  output.
- **Real interaction test:** ask "who are our clients," "what's Marcus
  Delgado's company" — confirm real names/companies/contact info from
  `sdn_clients`, not a generic answer.
- **No-regression test on the Spec Sheet compliance feature:** confirm
  it still runs and produces correct deterministic-findings-plus-AI-
  review output exactly as before — untouched code, but worth a live
  spot-check since it shares the same proxy and app_id.
- **Concurrency test (extending the existing fix, not replacing it):**
  send two questions back-to-back before the first resolves — one that
  triggers `get_clients` and one that doesn't. Confirm `aiHist` ends up
  correctly ordered (alternating roles, no corruption) regardless of
  which response arrives first, and both answers render under their
  correct message bubble.
- Standard structural checks (`tools/checkblocks.py sairndesign.html`,
  `tools/div_balance_check.py sairndesign.html`) after every change.
- Full Guardian v2 pass before push; live-verify against
  `sairn.vercel.app/sairndesign` after push — both steps of the Push
  Protocol, neither optional.
