# SAIRNlaw — AI Tool-Calling Foundation

**Status:** Approved for implementation 2026-08-10, following brainstorming
that surveyed AI-integration depth across all 10 live SAIRN apps (see
platform survey below). This ports the exact mechanism proven live in
SAIRNbiz's AI Tool-Calling Foundation
(`docs/superpowers/specs/2026-08-09-sairnbiz-ai-tool-calling-design.md`)
to SAIRNlaw — same architecture, same dispatcher shape, same role-gate
pattern, same anti-fabrication discipline. No new platform-level work is
needed: `api/claude.js`'s `sanitizeTools()` already allows custom
client tools through for every app_id, SAIRNlaw's included.

## 0. Why SAIRNlaw, not another app (platform survey, 2026-08-10)

Surveyed all 10 apps' actual AI code (not marketing claims) for real
data-grounding depth:

- **SAIRNbiz:** deep — the only app with a real tool-calling dispatcher
  (6 tools, role-gated, anti-fabrication hardened). Reference pattern.
- **SAIRNvet:** deep per-feature reasoning discipline (dosing calculator
  and differential-diagnosis tool both inject real verified/computed
  data into the prompt and explicitly forbid restating a different
  number), but no general mechanism — every feature hand-rolls its own
  grounding string, and none can pull a specific patient's own record
  automatically.
- **SAIRNlaw (this spec):** moderate — one feature (`runAiDraft`) already
  interpolates real per-matter fields into a prompt, but the general
  chat (`sendAI()`, `sairnlaw.html:1406`) has an explicit, deliberately
  written `LAW_FIRM_DATA_RULE` (`sairnlaw.html:1403`) telling the model
  it has **not** been given the firm's real matters/deadlines/trust
  data and must refuse and redirect rather than guess. This is a
  diagnosed gap already, not an undiscovered one — this spec is the fix
  for a limitation the team already wrote an explicit refusal rule
  around.
- **StoneDesk, SAIRNbuild:** moderate feature depth (StoneDesk's
  multimodal document scanner; SAIRNbuild's specialized prompts + real
  `web_search_20250305` tool) but no local-data tool dispatcher.
- **SAIRNdesign, SAIRNlegacy:** light-moderate, narrower personas, no
  confirmed per-record grounding.
- **SAIRNcode, SAIRNscape, SAIRNgrounds:** surface — single generic
  chat call, grounded on nothing more than a record count (or nothing
  at all). SAIRNscape and SAIRNgrounds are the easiest ports of this
  exact pattern but lowest business stakes.

**Decision:** SAIRNlaw next, because (a) real structured data
(`law_matters`, `law_deadlines`) sits completely unused by the AI today,
(b) the stakes are real — a missed filing deadline is a malpractice
exposure, not an inconvenience, so a grounded "what needs attention"
answer has genuine value (SAIRNbiz's `get_attention_digest` precedent
applies directly to a future item here), (c) the team already has
anti-fabrication discipline in this exact file (`LAW_CITATION_RULE`,
tightened after a real live-testing gap on Miranda v. Arizona), and (d)
a real `prole` role concept (owner/etc., set at login) already exists,
so the sensitivity-gate pattern ports with zero new auth plumbing.

## 1. Problem

SAIRNlaw's general AI chat (`sendAI()`, `sairnlaw.html:1406`) is one
`fetch(PROXY)` call with no `tools`. Its system prompt is built from two
static rule strings (`LAW_CITATION_RULE`, `LAW_FIRM_DATA_RULE`) — the
second of which exists specifically to tell the model it has no real
firm data and must refuse rather than guess. `runAiDraft()`
(`sairnlaw.html:2218`) manually interpolates one matter's fields for
document drafting, but that's a single-purpose, user-selects-the-matter
workflow, not something the general assistant can do for an arbitrary
question ("which matters are open," "who's the responsible attorney on
the Reyes case"). This spec builds the same general mechanism SAIRNbiz
built, so this and future firm-data questions get a real, grounded
answer instead of the current honest-but-unhelpful refusal.

## 2. Non-goals (explicitly deferred, same discipline as SAIRNbiz item 1)

- **No real tool beyond `get_matters` in this pass.** `get_deadlines`
  (arguably the highest-value tool, given `rDash()`'s own overdue-
  deadline attention logic) and any trust-accounting tool
  (`law_trusttx` — real regulatory sensitivity, needs its own explicit
  owner-gate decision, not assumed) are follow-on items once this
  mechanism is proven, exactly as SAIRNbiz sequenced payroll/P&L tools
  after `get_employees`.
- **No write-capable tools.** Every tool this mechanism exposes is
  read-only, matching the standing platform rule.
- **No new persistence.** `get_matters` reads live from
  `ld('law_matters', [])` via the existing `matters()`/`clientLabel()`
  helpers — nothing new is stored.
- **No change to `api/claude.js`.** `sanitizeTools()` already passes
  custom tools through for every `app_id` in `KNOWN_APP_IDS`, `sairnlaw`
  included — confirmed by reading the current file, not assumed from
  the SAIRNbiz spec's claim.
- **`runAiDraft()` is untouched.** It has its own single-purpose,
  already-correct per-matter grounding; this spec only changes the
  general chat (`sendAI()`).

## 3. Architecture

Direct port of SAIRNbiz's mechanism (`sairnbiz.html:889-940, 1958-2027`):

- `LAW_TOOLS = {}` — plain object registry.
- `lawRegisterTool(name, description, inputSchema, sensitive, run)` —
  same shape as `sbRegisterTool`.
- `lawExecuteTool(name, role, input)` — same shape as `sbExecuteTool`:
  unknown tool → honest error; `sensitive && role !== 'owner'` → access-
  restricted error, no execution; otherwise `tool.run(input || {})`
  inside try/catch, a thrown error becomes a `tool_result` saying the
  lookup failed, never a crash. `run()` must be synchronous, same
  documented constraint as `sbExecuteTool`.
- `sendAI()` changes: build `toolDefs` from `LAW_TOOLS`, send
  `tools: toolDefs` on the first `fetch(PROXY)` call. If the response
  contains a `tool_use` block, call `lawExecuteTool(name, prole, input)`,
  build a `tool_result` (real result JSON on success; on failure, the
  error string plus an explicit "do not estimate or substitute" — same
  belt-and-suspenders phrasing SAIRNbiz uses at `sairnbiz.html:2016`),
  push both the assistant tool-use turn and the user tool-result turn
  onto `aiHist`, then make the second `fetch(PROXY)` call (no `tools`
  field) to get the final rendered reply. If no `tool_use` block is
  present, behave exactly as today.
- **Concurrency:** `sendAI()` currently builds its "Thinking..." node
  via `document.createElement` and holds a direct reference (`thinking`,
  `sairnlaw.html:1415`) rather than querying the DOM for "the last
  `.ama`" — this already matches the placeholder-by-reference fix
  SAIRNbiz/SAIRNgrounds/SAIRNscape needed to add. Confirmed by reading
  the function: no change needed here, but the multi-turn logic must
  preserve this — the tool round-trip must keep updating the same
  `thinking` node, not create or query for a new one.
- **`LAW_FIRM_DATA_RULE` must be edited, not just left in place.** It
  currently states blanket "you have NOT been given this firm's actual
  matters..." — false the moment `get_matters` exists. Rewritten to:
  matters data (name, client, practice area, status, responsible
  attorney, opposing parties) is now available via tool lookup; deadline,
  trust-balance, invoice, and time-entry data is still not available and
  must still be refused-and-redirected exactly as before. This is a
  precise, field-level edit — not a blanket removal of the rule, since
  most of what it lists is still genuinely inaccessible after this spec.

## 4. Tool: `get_matters`

- **Sensitive:** `false` — matter metadata (name, client, practice area,
  status, responsible attorney, opposing parties) carries the same trust
  level as the rest of the app today; no panel in SAIRNlaw is role-gated
  (confirmed by grep, same finding pattern SAIRNbiz's spec documented for
  its own app). Trust balances and billing are excluded from this tool
  entirely (not merely gated) — they need their own tool and their own
  explicit sensitivity decision later, not a default here.
- **Input:** `{}` — no arguments, matching `get_employees`'s v1 shape.
- **Backing function:** `matters().map(...)`, reusing the existing
  `matters()` (`sairnlaw.html:1278`) and `clientLabel()`
  (`sairnlaw.html:1288`) helpers — no duplicated lookup logic.
- **Returns (per matter):** `{matter_number, matter_name, client,
  practice_area, status, responsible_attorney, opposing_parties}`.
  `client` is `clientLabel(m.client_id)` (resolved name, not a raw ID
  the model has no way to interpret). Excludes `notes` (free text that
  may contain anything a client told the firm in confidence — out of
  scope for a first, deliberately minimal tool) and all
  dates/trust/billing fields.
- **Description discloses, up front:** this tool does not include
  deadlines, trust balances, invoices, or time entries — matches the
  edited `LAW_FIRM_DATA_RULE` so the model's own refusal-and-redirect
  behavior for those topics stays consistent with what the tool
  actually returns.

## 5. Testing

- **Real interaction test:** ask "what matters do we have open" / "who's
  the responsible attorney on the Delacroix matter" — confirm the answer
  contains real matter numbers/names/attorneys from `law_matters`, not a
  refusal.
- **Refusal-preserved test:** ask a deadline or trust-balance question
  ("what's overdue," "what's the trust balance on the Ostrander matter")
  — confirm the model still refuses and redirects to the relevant panel,
  proving the `LAW_FIRM_DATA_RULE` edit didn't over-grant access it
  doesn't actually have.
- **Concurrency test:** send two questions back-to-back before the first
  resolves (one tool-using, one not) — confirm both land under their own
  bubble, no stuck "Thinking...", no misattribution.
- **Role-gate mechanism test:** even though `get_matters` itself is
  non-sensitive, confirm `lawExecuteTool` correctly blocks a
  `sensitive:true` tool for a non-owner role (temporary test tool or
  direct function call) — proves the gate works before a real sensitive
  tool depends on it.
- **`sanitizeTools()` regression check:** confirm a `sairnlaw`-originated
  custom-tool request still passes through unmodified (already true,
  platform-wide, but verify against the live proxy for this app_id
  specifically rather than assuming SAIRNbiz's verification covers it).
- Standard structural checks (`node --check` on the extracted script
  block, `tools/checkblocks.py sairnlaw.html`,
  `tools/div_balance_check.py sairnlaw.html`) after every change, per
  project CLAUDE.md.
- Full Guardian v2 pass before push; live-verify against
  `sairn.vercel.app/sairnlaw` after push — both steps of the Push
  Protocol, neither optional.
