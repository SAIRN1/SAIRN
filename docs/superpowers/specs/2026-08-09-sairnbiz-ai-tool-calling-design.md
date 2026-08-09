# SAIRNbiz — AI Tool-Calling Foundation

**Status:** Implemented and live-verified 2026-08-09. All 5 commits
(ab09c3d, 20acdcb, b419c48, 909dd49, 4cbc8b6) are on `origin/main` and
confirmed live at `sairn.vercel.app/sairnbiz` — `sbExecuteTool` present
in the deployed HTML, and a real logged-in session against the live app
asked "Who is our shop foreman, and how many fabricators do we have?"
and got a grounded answer (Marcus Thompson; 2 fabricators, correctly
excluding the part-time delivery driver) sourced from real `sb_emps`
data via 3 real `POST /api/claude` round trips (all HTTP 200) — proof
the tool-use mechanism works end-to-end against the live Anthropic API,
not just in stubbed-fetch unit tests. Concurrency serialization
(`sbAiBusy`) and the role-gate (`sensitive:true` blocking a non-owner
role with the exact "restricted to the owner role" error) were also
confirmed live. Full detail in
`.superpowers/sdd/2026-08-09-sairnbiz-ai-tool-calling/task-5-report.md`.
This is item 1 of a 6-item AI-native roadmap for SAIRNbiz (payroll/P&L
copilot, pre-payroll validation, cross-domain attention digest, hiring
cost-impact, review narratives). With the foundation now proven live,
item 2 (Payroll/P&L Copilot) is unblocked as the next spec.

## 1. Problem

SAIRNbiz's entire AI footprint today is one feature: a free-text chat
panel (`callAI()`, `sairnbiz.html:1488`). Confirmed by exhaustive grep —
one `fetch(PROXY)` call in the whole file, no other AI-touching code
anywhere. Its system prompt contains only a static company description
and `emps.length` (a headcount number, not records) — none of the app's
real, computed HR/accounting data (payroll, P&L, AR/AP, budget,
performance, training, vendors, hiring pipeline) ever reaches the model.
Every answer is generic; the assistant cannot actually look anything up.
This spec builds the mechanism to fix that generally, not one prompt at
a time per feature.

## 2. Non-goals (explicitly deferred, confirmed during brainstorming)

- **No real tool definitions beyond `get_employees` in this pass.** The
  payroll/P&L tools, budget/AP/training/performance tools, and hiring
  tools are items 2–6 of the roadmap, each adding its own tool to this
  mechanism once proven. Building all ten domains' tools speculatively
  now would be scope creep on a spec whose actual job is the plumbing.
- **No write-capable tools.** Confirmed explicitly: every tool this
  mechanism exposes is read-only. Matches the standing rule used
  everywhere else in the platform tonight — deterministic code acts, AI
  explains, never guesses or acts on its own. Write/action tools are not
  ruled out forever, just out of scope for this foundation.
- **No new persistence.** Tool results are computed live from existing
  `localStorage` via existing getters (`ld('sb_emps', [])`, etc.) —
  nothing new is stored.
- **No change to `KNOWN_APP_IDS` or the demo daily-call-limit logic** in
  `api/claude.js` — unrelated to this change, not touched.

## 3. Platform-wide dependency: `api/claude.js`'s `sanitizeTools()`

**Real constraint found during design, not assumed.** `api/claude.js`
(the proxy shared by all 10 apps) already accepts a `tools` field, but
`sanitizeTools()` (`api/claude.js:45-56`) filters it against
`ALLOWED_TOOL_TYPES = ['web_search_20250305']` — an Anthropic
*server-executed* tool. Any custom client tool (`type:'custom'`, no
`type` field, or any type other than `web_search_20250305`) is silently
stripped before the request reaches Anthropic. Sending `tools:
[get_employees_definition]` today would result in `tools: undefined`
being forwarded — the model would never see the tool and could never
emit a `tool_use` block.

**The fix, and why it's safe:** the existing whitelist's stated
rationale (`api/claude.js:37-40`) is cost/abuse prevention — an
unrestricted server-tool passthrough would let any caller run billed
Anthropic-executed actions (web search) against the shared API key.
**Custom/client tools carry none of that risk** — the model only returns
a *request* to call a tool (a JSON blob describing name + arguments);
Anthropic never executes anything, and no cost or external call happens
until the browser's own dispatcher decides to run it locally against
`localStorage`. The change: allow tool definitions with `type:'custom'`
(or no `type` field, matching Anthropic's custom-tool schema) to pass
`sanitizeTools()` unmodified — no `max_uses` capping applies to them
(that's a server-tool-specific concept), and the existing
`web_search_20250305` handling is untouched.

**This is a platform-wide decision**, not a SAIRNbiz-only change — every
app sharing this proxy gains the ability to define custom tools the
moment this ships. Flagging explicitly per the standing rule (any new
server tool capability gets deliberately whitelisted, not silently
opened) rather than treating it as an implementation detail buried
inside the SAIRNbiz work.

## 4. Architecture

**Approach: true multi-turn tool-calling** (rejected alternative: a
deterministic keyword-router injecting data into a single-shot prompt —
cheaper, but each future feature would need its own router logic instead
of reusing one mechanism; doesn't satisfy "foundation everything else
needs").

Flow, replacing the current single `fetch(PROXY)` call in `callAI()`:

1. Send user message + `tools: [TOOL_DEFINITIONS]` + history to `PROXY`.
2. If the response's `content` contains a `tool_use` block: look up the
   requested tool name in a client-side dispatcher map. If the tool is
   marked `sensitive:true` and `prole !== 'owner'`, do not execute it —
   build a `tool_result` stating access is restricted. Otherwise execute
   the matching local function (wrapped in try/catch — a thrown error or
   unexpected shape becomes a `tool_result` saying the lookup failed,
   never a crash) and build a `tool_result` with its real output.
3. Send the `tool_result` back as the next message in the same
   conversation, request the final answer (no `tools` needed on this
   follow-up call — one round-trip of tool use is sufficient for v1;
   Claude's API does support multi-step tool loops, but nothing in the
   v1 tool set needs more than one lookup per question).
4. Render the final text response.

If no `tool_use` block is present (the model judged no tool was needed,
or the question isn't tool-answerable), behave exactly as today —
single call, direct text response.

**Concurrency:** one "Thinking..." placeholder spans the *entire*
exchange, including the extra round-trip. Reuses this session's own
placeholder-by-reference fix (`sairnbiz.html`'s `addMsg()` already
returns its DOM node) — the multi-turn logic must not reintroduce the
placeholder-by-DOM-position race just fixed in this exact function's
siblings across `sairngrounds.html`/`sairnscape.html` tonight. A second
question sent while a tool round-trip is in flight must still resolve
to its own placeholder, not the other request's.

## 5. v1 tool set (proves the mechanism, nothing more)

| Tool | Backing function | Sensitive? |
|---|---|---|
| `get_employees` | `ld('sb_emps', [])`, filtered to non-sensitive fields (name, role, dept, type, start, status — **rate/compensation excluded even here**, since payroll tools are item 2's job, not this one's) | No |

One tool, deliberately. It's enough to prove: tool definitions reach the
model past `sanitizeTools()`, the dispatcher executes and returns real
data, the round-trip renders a grounded answer, and the concurrency fix
holds under a slower two-request exchange. Item 2 adds
`get_payroll_summary`/`get_pl_summary` (both `sensitive:true`) directly
on top of this same dispatcher and role-gate check — no rework.

## 6. Role gating

**First role-based gate anywhere in SAIRNbiz's client code.** Confirmed
via grep: zero existing `role===` checks in the file today, despite
`prole` being a real, server-issued value (`owner`/`manager`/`employee`,
via `SB_AUTH_API`) available since login. The dispatcher's sensitivity
check (§4 step 2) is the first consumer of `prole` for an access
decision, not an extension of an existing pattern — worth a visible
comment in the code marking it as such, since other apps may want to
copy this pattern later and should know it's new, not established.

- **`get_employees` (this spec):** no gating — same trust level as the
  rest of the app today (roster data, no compensation fields).
- **Payroll/compensation tools (item 2, for reference only — not built
  here):** `owner` only, confirmed explicitly by Michael. A
  `manager`/`employee` asking a payroll question gets an honest "not
  authorized" answer from the model, not a wrong number and not a
  silent failure.

## 7. Bad/ambiguous query handling

Confirmed explicitly: the model should state plainly it doesn't have
the data rather than guess. Enforced two ways: (a) the system prompt
instructs this directly, and (b) any dispatcher failure (unknown tool
name, execution error, access-denied) returns a `tool_result` saying so
in plain terms, so the model's final answer is grounded in an honest
"no" rather than free-associating. No silent fallback to the old
generic-chat behavior — if a tool was attempted and failed, the user
sees that it failed.

## 8. Testing

- Real interaction test: ask a roster question ("who's on the team,"
  "how many employees do we have"), confirm the answer contains real
  names/counts from `sb_emps`, not the old generic-headcount-only
  response.
- Concurrency test: send two questions back-to-back before the first
  resolves (one tool-using, one not), confirm both answers land under
  their own bubble, no stuck "Thinking...", no misattribution — same
  live-test standard used to catch and fix this exact bug class earlier
  tonight.
- Role-gate test (even with only `get_employees` in v1, prove the gate
  mechanism itself): a temporary second tool or manual dispatcher call
  confirming a `sensitive:true` tool is actually blocked for a
  non-owner `prole`, not just assumed correct from reading the code.
- `sanitizeTools()` unit-level check: confirm a `web_search_20250305`
  request still passes through capped exactly as before (no regression
  to the existing behavior this change modifies) and a custom tool now
  survives sanitization unmodified.
- Guardian v2 pass (syntax, div-balance, dup-globals, no forbidden
  patterns) on `sairnbiz.html` before any push; the `api/claude.js`
  change gets its own direct verification against the live proxy
  (real request/response, not just code review) before considering it
  shipped, since it's shared infrastructure.
