# SAIRNbuild — AI Tool-Calling Foundation + `get_jobs`

**Status:** Implemented and live-verified 2026-08-10. Both commits
(`34c2ba2`, `448c389`) are on `origin/main` and confirmed live at
`sairn.vercel.app/sairnbuild` — `bldExecuteTool` present in the
deployed HTML. A real interaction test asked "what is the value of the
Hartley job, and what stage is it in?" and got a correct, tool-backed
answer from real `bld_jobs` data. The existing `web_search_20250305`
path was confirmed unaffected (a residential-electrical-code question
still returned real search-grounded content). The existing `aiAskSeq`
concurrency guard was confirmed to correctly extend across the new
tool-use round-trip: two back-to-back questions produced only the
later question's answer, matching the pre-existing convention.
`sanitizeTools()` confirmed live for a mixed `web_search_20250305` +
`get_jobs` array on the `sairnbuild` app_id specifically. Guardian v2
pass clean except 2 pre-existing findings (a duplicate `rBids`
declaration, a "work in progress" placeholder string elsewhere in the
file), both confirmed present on the pre-change baseline.

This is SAIRNbuild's first custom-tool-calling work, porting the
mechanism already proven live on every prior rollout — merged
alongside a real Anthropic server tool (`web_search_20250305`) this
app's chat already uses, not replacing it.

## 0. Why SAIRNbuild, and what's already good here

SAIRNbuild has 7 real AI features: `fpAnalyze`, `claimGeneratePacket`,
`costExplain`, `ssaAnalyze`, `aiAsk` (general chat,
`sairnbuild.html:6410`), `disRespond`, `mktBriefing`. All except `aiAsk`
are already real, task-specific, well-grounded features — untouched by
this spec.

`aiAsk()` is more mature than most apps' starting chat:
- **It already has a correct concurrency guard** —
  `aiAskSeq`/`myAiAskSeq` (`sairnbuild.html:6447-6448, 6457, 6481`), a
  stale-response-discard pattern, same shape as SAIRNvet's
  `askAiSeq`. No new concurrency fix is needed — this spec only
  extends the existing guard to also cover the tool-use round-trip's
  second fetch.
- **It already sends a real Anthropic server tool** —
  `{type:'web_search_20250305',name:'web_search',max_uses:3}`
  (`sairnbuild.html:6453`) — and already handles the resulting
  interleaved text/citation content blocks correctly
  (`sairnbuild.html:6460-6471`). The new custom tool must be **merged**
  into this array, not replace it.
- It injects one job's context (`client`/`address`/`stage`) only if
  manually selected from a dropdown (`$('ai-job').value`,
  `sairnbuild.html:6413-6414`) — there's no way to ask a cross-job
  question ("which jobs are blocked") grounded in real data today.
- Each call is a single, standalone question — no persistent
  multi-turn history array (answers are logged to `bld_ai_chat` for
  history *display*, but not sent back as conversation context on the
  next question) — same stateless shape as SAIRNvet's/SAIRNcode's chat.

**No real auth exists.** `prole` comes from a client-side PIN gate
(`PINS` object matched at login, `sairnbuild.html:1956-1960`) — no
server backend. Same trust class as SAIRNvet/SAIRNcode.

**Real, unused data**: `bld_jobs` (`sairnbuild.html:2047`), accessed via
the existing `jobs()` helper (`sairnbuild.html:2473`) — rich records:
`{id, address, client, phone, value, stage, start, target, permit,
blocked, notes}`, including a real `blocked` reason field (e.g.
*"Failed rough electrical - re-inspection 8/6"*).

## 1. Design decisions

- **No sensitivity/role-gate parameter** — no real auth exists here.
- **No new concurrency guard** — `aiAskSeq`/`myAiAskSeq` already exists
  and is extended, not replaced.
- **The new tool definitions are merged into the existing `tools`
  array alongside `web_search_20250305`**, not sent as a separate
  request or a replacement array. `sanitizeTools()` (`api/claude.js`)
  already handles a mixed array of one server tool + custom tools
  correctly — this exact scenario was proven during SAIRNbiz's
  original tool-calling foundation spec, not assumed here.
- **`get_jobs` is the v1 proof tool**, including the native `blocked`
  field — it's a real field on the roster record itself, not a
  separate cross-referenced attention digest, so including it doesn't
  expand scope beyond a plain roster tool.

## 2. Non-goals (explicitly deferred)

- **No real tool beyond `get_jobs` in this pass.** Tools over
  `bld_subs`, `bld_rfis`, `bld_submittals`, `bld_change_orders`,
  `bld_bids`, `bld_punchlist`, or any other data domain are later,
  separate scope.
- **No write-capable tool.** Read-only, matching every other tool on
  this platform.
- **No new persistence.** Reads `jobs()` (`sairnbuild.html:2473`)
  directly — nothing new is stored.
- **No changes to `fpAnalyze`, `claimGeneratePacket`, `costExplain`,
  `ssaAnalyze`, `disRespond`, or `mktBriefing`.** Already real, correct
  features — untouched.
- **No changes to the existing `web_search_20250305` handling** —
  citation/source-joining logic (`sairnbuild.html:6460-6471`) stays
  exactly as it is for that tool's own responses.
- **No changes to `api/claude.js`.** `sanitizeTools()` already passes
  a mixed server-tool + custom-tool array through correctly for every
  `app_id`, `sairnbuild` included.

## 3. Architecture

- `BLD_TOOLS = {}` — plain object registry.
- `bldRegisterTool(name, description, inputSchema, run)` — same shape
  as SAIRNvet's/SAIRNcode's (no `sensitive` parameter).
- `bldExecuteTool(name, input)` — unknown tool → honest error;
  otherwise `tool.run(input || {})` inside try/catch, a thrown error
  becomes an honest `{ok:false}`, never a crash.
- `aiAsk()` rewired: build `toolDefs` from `BLD_TOOLS`; the existing
  `tools` array becomes
  `[{type:'web_search_20250305',name:'web_search',max_uses:3}].concat(toolDefs)`.
  If the response's `content` contains a custom `tool_use` block (a
  block whose `name` matches a key in `BLD_TOOLS` — distinct from any
  `server_tool_use`/`web_search_tool_result` block the existing
  web-search handling already parses), call
  `bldExecuteTool(toolUse.name, toolUse.input)`, build a `tool_result`,
  and make a second `fetch` (no `tools` field, matching every prior
  rollout's single-round-trip contract) with
  `[{role:'user',content:q}, {role:'assistant',content:blocks},
  {role:'user',content:[tool_result]}]` for the final answer. The
  existing `aiAskSeq` check (`myAiAskSeq!==aiAskSeq`) is checked again
  after this second fetch resolves, exactly as it already is after the
  first. If no custom `tool_use` block is present, behave exactly as
  today (including the existing web-search text/citation handling,
  unchanged).

## 4. Tool: `get_jobs`

- **Input:** `{}` — no arguments, matching every prior tool's v1 shape.
- **Backing function:** `jobs()` (`sairnbuild.html:2473`), no new
  lookup logic.
- **Returns (per job):** `{address, client, value, stage, start,
  target, blocked}`. Excludes `id` (not meaningful to the model),
  `phone` (contact info, out of scope for a first minimal tool),
  `permit` (a separate, narrower data point not core to a roster
  view), and `notes` (free text — same discipline as every prior
  tool's notes-exclusion).
- **Description discloses, up front:** this tool only covers the job
  roster — no subcontractor, RFI, submittal, change-order, bid, or
  punch-list data is available.

## 5. Testing

- **Pure dispatcher test:** `bldExecuteTool()` — unknown tool → honest
  error; thrown error inside `run()` → `{ok:false}`, never a crash.
- **Tool-level test:** `BLD_TOOLS.get_jobs.run({})` against a stubbed
  `jobs()` — confirm `id`/`phone`/`permit`/`notes` never appear in the
  output.
- **Real interaction test:** ask "which jobs are blocked and why,"
  "what's the value of the Hartley job" — confirm real addresses/
  clients/values/blocked-reasons from `bld_jobs`, not a generic answer.
- **No-regression test on the existing web-search tool:** ask a
  question that should trigger web search ("what's the current price
  of 2x4 lumber") and confirm it still works exactly as before —
  interleaved text/citation blocks parsed correctly, sources listed.
- **Concurrency test (extending the existing guard, not introducing a
  new one):** send two questions back-to-back before the first
  resolves — confirm only the *later* question's answer ever renders
  (matching the existing `aiAskSeq` convention), with no stuck/mixed
  state across the new tool-use round-trip specifically.
- Standard structural checks (`tools/checkblocks.py sairnbuild.html`,
  `tools/div_balance_check.py sairnbuild.html`) after every change.
- Full Guardian v2 pass before push; live-verify against
  `sairn.vercel.app/sairnbuild` after push — both steps of the Push
  Protocol, neither optional.
