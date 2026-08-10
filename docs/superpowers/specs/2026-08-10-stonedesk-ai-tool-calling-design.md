# StoneDesk — AI Tool-Calling Foundation + `get_job_profitability`

**Status:** Design approved 2026-08-10, following brainstorming (including
a real mid-brainstorming correction — see §0). Not yet implemented.

This is StoneDesk's first tool-calling work, porting the mechanism
already proven live in SAIRNbiz, SAIRNlaw, SAIRNvet, SAIRNscape, and
SAIRNgrounds — targeted at the app's actual live chat, not the dead
code an earlier pass of this same design mistakenly recommended.

## 0. Why StoneDesk, why this target, and a correction made during design

StoneDesk has roughly 15 real AI-invoking features — the richest
footprint on the platform, including a genuine SSE-streaming chat
override (`installStreamingHook()`) that no other app has. That
streaming path is explicitly **out of scope** for this spec (see §2) —
tool-use interacts with streaming differently (partial content-block
events, not one parsed response) and this pass targets a lower-risk
integration point first.

**A real correction happened during this design, not before it.** The
first draft of this recommendation targeted `sendMessage()`/
`sendToClaudeAndRender()` (`stonedesk.html:9445-9513`), reasoning that
it already had a correct concurrency guard (`isTyping`) other apps
lacked. Further reading found an explicit comment in the file itself
(`stonedesk.html:3235-3239`): *"DEAD CODE FLAG: sendMessage/handleKey/
autoResize/toggleVoice/addMessage/sendToClaudeAndRender (~L7738-7864)
back a #messages container that no longer exists anywhere in this file
-- leftover from before panel-ai was rebuilt with its own self-contained
chat widget (sdAISend/ai-chat/ai-input)."* That target would have been
unreachable code — flagged and corrected before any spec was written,
not discovered after implementation.

**The real, live chat is `sdAISend()`/`sdAIQuick()`/`sendMsg()`**
(`stonedesk.html:3173-3232`, the `panel-ai` self-contained widget). Its
`history` array (`stonedesk.html:3173`) is shared, persistent, and
multi-turn — same shape as every other app's chat — and, unlike what
was first assumed, **it has zero concurrency guard**: `sendMsg()`
(`stonedesk.html:3189`) goes straight from the empty-check to appending
and fetching, no busy-flag anywhere. It also sends **no system prompt at
all** — just `{app_id, is_demo, messages:history}`. Its only grounding
today is ad-hoc: callers like `finAIJobAdvice()`
(`stonedesk.html:21823`) and `finAskCFO()` (`stonedesk.html:21844`)
pre-format real computed numbers (a job's margin, YTD vendor spend,
tracked revenue) directly into canned question *text* before calling
`sdAIQuick(text)` — real, but only for those specific buttons; a
free-typed question in the chat box gets no grounding at all.

**Real, unused, already-computed data**: `sdFinJobs`
(`stonedesk.html:21644`, loaded once from `localStorage`'s
`sd_fin_jobs` key) — real per-job profitability records:
`{customer, quote, sqft, material, cogs, profit, margin, date}`,
computed by `finSaveJob()` (`stonedesk.html:21697`). None of it is
tool-accessible; the two AI features that reference job financials at
all (`finAIJobAdvice`, `finAskCFO`) only ever see one job or a
hand-rolled aggregate at the moment of a button click.

**Real, server-verified auth exists**, separate from a cosmetic
self-selected layer that could be confused for it. `api/sd-auth.js` is
a real per-employee login backend; `currentRole` is set `ONLY` from its
response (per an existing comment at `stonedesk.html:29278`), and a
real gate already exists on it (`currentRole === 'owner' ||
currentRole === 'admin'`, `stonedesk.html:29714`). This is a different,
real thing from `sd_exec_role` (`stonedesk.html:21927` area), which is
a self-selected ceo/cfo/cto/admin picker gating only a cosmetic
"Executive Suite" UI layer — the same non-verified trust class as
SAIRNvet's dropdown. **The real role lives in `sessionStorage` under
`sd_session_role`** (`SD_ROLE_KEY`, `stonedesk.html:29284`) — readable
from any scope in the file without needing access to the auth module's
internal `currentRole` variable, which is not exposed globally today.

## 1. Design decisions

- **Target `sdAISend()`/`sendMsg()`, not the dead chat.** Confirmed
  live-reachable (called from the visible `panel-ai` widget and from
  at least 6 other real features via `sdAIQuick()`).
- **Concurrency fix is required, not optional** — same shape as every
  prior rollout's fix (`sdAiBusy`): `sendMsg()`'s shared `history` had
  no guard, contrary to what was first assumed about this app.
- **The dispatcher includes a `sensitive`/role-gate parameter**,
  consistent with every app except SAIRNvet — real server-verified
  auth exists here. A new, minimal `sdCurrentRole()` helper is added
  (reads `sessionStorage.getItem('sd_session_role')` directly) rather
  than reaching into the auth module's internal `currentRole` variable,
  which isn't exposed outside its own scope — this avoids any coupling
  to or modification of existing auth code.
- **`get_job_profitability` is non-sensitive.** Job cost/margin data
  is not gated by any real role check anywhere in the app today (the
  Financials panel itself isn't role-gated) — gating the tool more
  tightly than the panel it reads from would be a new, unexplained
  restriction.

## 2. Non-goals (explicitly deferred)

- **The streaming chat (`installStreamingHook()`) is untouched.**
  Tool-use over a streaming response is a materially different, harder
  integration (partial content-block events vs. one parsed JSON
  response) — explicitly separate, later scope, not folded in here.
- **No real tool beyond `get_job_profitability` in this pass.** Tools
  over `sd_jobs`, `sd_intake`, `sd_ap`, `sd_slabs`, `sd_vendors`, or any
  other of StoneDesk's many data domains are later, separate scope.
- **No write-capable tool.** Read-only, matching every other tool on
  this platform.
- **No new persistence.** Reads the existing in-memory `sdFinJobs`
  global (already loaded from `localStorage` at script-parse time,
  kept in sync by `finSaveJob()`/`finDeleteJob()`) — nothing new is
  stored.
- **No changes to any of StoneDesk's other ~14 AI features**
  (`scanDoc`, `sdRunEmailScan`, `getAIDrawingAdvice`, `fqAnalyze`/
  `fqGenQuote`, `finAIJobAdvice`, `finAskCFO`, etc.) or to
  `api/sd-auth.js`/`api/claude.js`.

## 3. Architecture

- `SD_TOOLS = {}` — plain object registry.
- `sdRegisterTool(name, description, inputSchema, sensitive, run)` —
  same shape as every prior rollout.
- `sdCurrentRole()` — new, minimal helper:
  `sessionStorage.getItem('sd_session_role')||''` in a try/catch,
  mirroring the exact convention SAIRNscape's `scpCurrentRole()`/
  SAIRNgrounds' `grdCurrentRole()` already use, adapted to StoneDesk's
  own real session-storage key (`sd_session_role`) rather than a new
  one.
- `sdExecuteTool(name, role, input)` — unknown tool → honest error;
  `sensitive && role !== 'owner'` → access-restricted error, no
  execution (same single-role check as every prior rollout — not
  `currentRole === 'owner' || currentRole === 'admin'`'s two-role
  check used elsewhere in this file for a different feature; kept
  consistent with the platform-wide dispatcher convention instead);
  otherwise `tool.run(input || {})` inside try/catch, a thrown error
  becomes an honest `{ok:false}`, never a crash.
- `sdAiBusy` — new boolean guard. `sdAISend()`/`sdAIQuick()` check it
  first; `sendMsg()` sets it `true` at start and clears it on every
  exit path via a `finish()`-style helper.
- `sendMsg(msg)` rewired: build `toolDefs` from `SD_TOOLS`; add a real
  system prompt for the first time (currently none exists) —
  StoneDesk's stone-fabrication persona plus the standard anti-
  fabrication instruction already proven on every prior rollout. First
  `fetch` sends `tools:toolDefs`. If a `tool_use` block comes back,
  call `sdExecuteTool(toolUse.name, sdCurrentRole(), toolUse.input)`,
  build a `tool_result`, push the assistant tool-use turn and the
  tool-result turn onto `history`, then a second `fetch` (no `tools`)
  for the final answer. If no `tool_use`, behave as today (render the
  first call's text directly).

## 4. Tool: `get_job_profitability`

- **Sensitive:** `false`.
- **Input:** `{}` — no arguments, matching every prior tool's v1 shape.
- **Backing function:** reads the existing `sdFinJobs` global directly
  (no new lookup logic, no localStorage re-read — this array is
  already kept live-in-sync by `finSaveJob()`/`finDeleteJob()`).
- **Returns (per job):** `{customer, quote, material, sqft, cogs,
  profit, margin, date}`. All fields already non-sensitive numeric/text
  data the Financials panel itself displays ungated.
- **Description discloses, up front:** this tool only covers jobs
  logged in the Job Financials tracker — it does not cover `sd_jobs`
  (production/scheduling records), quotes, or any other job-adjacent
  data domain in the app.

## 5. Testing

- **Pure dispatcher test:** `sdExecuteTool()` — unknown tool → honest
  error; sensitive tool + non-owner role → restricted error; thrown
  error inside `run()` → `{ok:false}`, never a crash.
- **Tool-level test:** `SD_TOOLS.get_job_profitability.run({})` against
  a stubbed `sdFinJobs` array — confirm the shape matches exactly and
  no extra fields leak through.
- **Real interaction test:** ask "which jobs were most profitable,"
  "what's my average margin" — confirm real customer names/margins from
  `sdFinJobs`, not a refusal or a generic answer.
- **No-regression spot check:** confirm `finAIJobAdvice()` and
  `finAskCFO()` still work exactly as before (they call `sdAIQuick()`,
  now wired to the tool-aware `sendMsg()` — must not break their
  existing canned-question flow).
- **Concurrency test (load-bearing):** send two questions back-to-back
  before the first resolves — confirm the second is rejected before it
  touches `history`, and `history` stays a clean, correctly-ordered
  sequence for the surviving call.
- **Role-gate mechanism test:** confirm a temporary sensitive test tool
  correctly blocks a non-owner `sdCurrentRole()` value and allows
  `'owner'`.
- **Streaming-path regression check:** confirm `installStreamingHook()`
  and its override of `window.sendMessage` are completely unaffected —
  this spec never touches that code path.
- Standard structural checks appropriate to this file's HTML-parser-
  based script-block extraction (per project `CLAUDE.md`, never a
  `grep -c '<script'` count) after every change.
- Full Guardian v2 pass before push; live-verify against
  `sairn.vercel.app/stonedesk` after push — both steps of the Push
  Protocol, neither optional, and especially load-bearing on this
  specific 2MB file per the project's own standing fragility warnings.
