# SAIRNgrounds — AI Tool-Calling Foundation + `get_properties`

**Status:** Implemented and live-verified 2026-08-10. All 2 commits
(`4cefafe`, `b9b7483`) are on `origin/main` and confirmed live at
`sairn.vercel.app/sairngrounds` — `grdExecuteTool` present in the
deployed HTML. Real property-roster questions answered with tool-backed
data; no-tool path unaffected. Concurrency fix confirmed on the live
deployed code: second concurrent send rejected with a toast before
touching `aiHist`, `aiHist` stayed a clean 4-entry sequence for the
surviving call, `grdAiBusy` correctly reset to `false`. Role-gate
confirmed: `owner` allowed, `superintendent` blocked.
`sanitizeTools()` confirmed live for the `sairngrounds` app_id. Guardian
v2 pass clean except one pre-existing finding (`nav_panel_check.py`'s
sidebar-button convention mismatch, confirmed present on the pre-change
baseline).

This is SAIRNgrounds' first tool-calling work, porting the mechanism
already proven live in SAIRNbiz, SAIRNlaw, SAIRNvet, and SAIRNscape.
The two load-bearing design decisions are identical to SAIRNscape's
rollout because the same two real conditions hold here — confirmed by
reading the code, not assumed from precedent.

## 0. Why SAIRNgrounds, and why now (corrected assessment, 2026-08-10)

An earlier platform survey called this app's AI footprint "single
fetch" — an undercount, corrected here. `sairngrounds.html` has **6
real AI call sites**: `callAI()` (general chat, `sairngrounds.html:3543`),
`grdUploadProgressPhoto()` (`sairngrounds.html:2018`, vision-based
progress-photo QC — the *original* pattern SAIRNscape's own equivalent
was explicitly modeled on), `genEcosystemReport()`
(`sairngrounds.html:2695`, a genuinely well-built 7-layer property
ecosystem health report — layers 1-6 computed live from real data
(golf-zone condition, irrigation health, water features, invasive-
species pressure) or honest manual field notes, layer 7 is Claude's
synthesis strictly grounded in only those 6 layers), `dcAnalyze()`
(`sairngrounds.html:2780`, "DreamClose" vision-based landscape design
direction, honestly scoped as text description only), and two bar/
clubhouse inventory vision scanners (`msbScanBottle()`,
`sairngrounds.html:3280`, plus a food-scanner counterpart). All 5 of
these besides the general chat are already good, real, well-grounded
work — untouched by this spec.

`callAI()` grounds only on `props.length` (a count, not records) — the
same shallow shape SAIRNbiz/SAIRNscape had before their own item 1.
Real, completely unused data sits right there: `grd_properties` (name,
type, contact, phone, email, acreage, address, status, notes; seed at
`sairngrounds.html:1308-1312`), plus `grd_jobs`, `grd_schedule`,
`grd_quotes`, `grd_invoices`, `grd_golf_zones`, `grd_irr_*`,
`grd_invasive_sightings`, `grd_water_features`, `grd_training_*`,
`grd_vendors`. `propName(id)` (`sairngrounds.html:1335`) already
resolves a `property_id` to its real name for other features (not
needed by `get_properties` itself, which returns full records, not
id-references).

**The exact same concurrency bug already found and fixed in SAIRNlaw
and SAIRNscape exists here too.** `aiHist` (`sairngrounds.html:1111`)
is shared, persistent, multi-turn — and has zero concurrency guard of
any kind (confirmed by grep: no busy-flag, no sequence-number
anywhere in this file). A comment inside `callAI()` even notes that
this exact function's placeholder-by-DOM-position race was already
found and fixed here by "a fresh adversarial-review pass" — but that
fix only covers the "Thinking..." DOM node, not the `aiHist` array
itself, which remains exactly as vulnerable as SAIRNscape's
`scpAiHist` was before its own fix. Confirmed with the user: fixing
this is a **required part of this rollout**, not deferred — same
treatment SAIRNscape got.

**Real, server-verified auth already exists here too, and with richer
precedent than SAIRNscape.** `GRD_AUTH_API`, employee login, a real
server-issued `role`, `grdCurrentRole()` (`sairngrounds.html:1942`)
reading it. Two separate existing features already gate real authority
on real roles: `GRD_QC_AUTHORITY_ROLES=['owner','superintendent',
'manager']` (`sairngrounds.html:1950`) and
`MSB_VOID_AUTHORITY_ROLES=['owner','superintendent','manager']`
(`sairngrounds.html:3026`).

## 1. Design decisions (same as SAIRNscape's, because the same two conditions hold)

- **Concurrency fix: a busy-guard, `grdAiBusy`, same shape as
  `scpAiBusy`/`lawAiBusy`.** Not a discard pattern — `aiHist`'s shared,
  multi-turn shape is what actually needs protecting from concurrent
  writes, not just the UI symptom.
- **The dispatcher includes a `sensitive`/role-gate parameter now**,
  even though `get_properties` itself is non-sensitive — consistent
  with SAIRNscape's rollout and this file's own (even richer) existing
  real-role-gate precedent. The gate check is the same single-role
  `sensitive && role !== 'owner'` used by every prior rollout — not
  this file's own separate `GRD_QC_AUTHORITY_ROLES`/
  `MSB_VOID_AUTHORITY_ROLES` multi-role concepts, which belong to
  different features and are not inherited here.

## 2. Non-goals (explicitly deferred)

- **No real tool beyond `get_properties` in this pass.** Tools over
  `grd_jobs`/`grd_schedule`/`grd_quotes`/`grd_invoices`/golf-course or
  irrigation data are later, separate scope.
- **No write-capable tool.** Read-only, matching every other tool on
  this platform.
- **No new persistence.** Reads live from `ld('grd_properties', [])`
  — nothing new is stored.
- **No changes to `grdUploadProgressPhoto()`, `genEcosystemReport()`,
  `dcAnalyze()`, or the bar-inventory scanners.** All already real,
  correct features — untouched.
- **No changes to `api/claude.js`.** `sanitizeTools()` already passes
  custom tools through for every `app_id` in `KNOWN_APP_IDS`,
  `sairngrounds` included.

## 3. Architecture

- `GRD_TOOLS = {}` — plain object registry.
- `grdRegisterTool(name, description, inputSchema, sensitive, run)` —
  same shape as `sbRegisterTool`/`lawRegisterTool`/`scpRegisterTool`.
- `grdExecuteTool(name, role, input)` — unknown tool → honest error;
  `sensitive && role !== 'owner'` → access-restricted error, no
  execution; otherwise `tool.run(input || {})` inside try/catch, a
  thrown error becomes an honest `{ok:false}`, never a crash. `role`
  is supplied by the caller from `grdCurrentRole()`
  (`sairngrounds.html:1942`) at call time, matching this file's
  existing convention (same as SAIRNscape's `scpCurrentRole()` usage).
- `grdAiBusy` — new boolean guard. `sendAI()` checks it first and
  rejects with a `toast()` if busy; `callAI()` sets it `true` at start
  and clears it via a `finish()` helper covering every exit path
  (no-tool-use return, tool-use round-trip completion, and connection
  errors alike) — same shape as `scpCallAI()`'s fix.
- `callAI()` rewired: build `toolDefs` from `GRD_TOOLS`; first `fetch`
  sends `tools:toolDefs`. If a `tool_use` block comes back, call
  `grdExecuteTool(toolUse.name, grdCurrentRole(), toolUse.input)`,
  build a `tool_result` (error path includes the same "do not
  estimate" instruction already proven on every prior rollout), push
  the assistant tool-use turn and the tool-result turn onto `aiHist`,
  then make a second `fetch` (no `tools` field) for the final answer.
  If no `tool_use`, behave exactly as today. The existing placeholder-
  by-reference pattern (`thinkingEl`) is preserved unchanged — it
  already does the right thing per its own comment; only `aiHist` was
  unguarded, not the placeholder.

## 4. Tool: `get_properties`

- **Sensitive:** `false` — property contact/status data carries the
  same trust level as the rest of the app today; no panel in
  SAIRNgrounds is role-gated for viewing this data (only QC sign-off
  and bar-void authority are gated, different, action-based concerns).
- **Input:** `{}` — no arguments, matching every prior tool's v1 shape.
- **Backing function:** `ld('grd_properties', [])`, no new lookup
  logic needed.
- **Returns (per property):** `{name, type, contact, phone, email,
  acreage, address, status}`. Excludes `id` (not meaningful to the
  model) and `notes` (free text — same discipline as `get_matters`/
  `get_deadlines`/`get_customers` excluding their own notes fields).
- **Description discloses, up front:** this tool does not include job
  history, schedule, invoices, quotes, or any golf-course/irrigation/
  ecosystem data — those aren't tool-backed yet.

## 5. Testing

- **Pure dispatcher test:** `grdExecuteTool()` — unknown tool → honest
  error; sensitive tool + non-owner role → restricted error; thrown
  error inside `run()` → `{ok:false}`, never a crash.
- **Tool-level test:** `GRD_TOOLS.get_properties.run({})` against a
  stubbed `ld` — confirm `id`/`notes` never appear in the output.
- **Real interaction test:** ask "what properties do we manage," "what
  type is Fairview Golf Club" — confirm real names/types/contact info
  from `grd_properties`, not a refusal or a generic answer.
- **Concurrency test (the load-bearing one for this rollout):** send
  two questions back-to-back before the first resolves — confirm the
  second is rejected with a toast before it touches `aiHist`, exactly
  one message-bubble pair results, and `aiHist` stays a clean,
  correctly-ordered sequence for the first call. Direct regression test
  for the concurrency bug this spec fixes.
- **Role-gate mechanism test:** even with only `get_properties` (non-
  sensitive) in v1, confirm the gate mechanism itself: a temporary
  sensitive test tool correctly blocks `'superintendent'` and
  `'manager'` (real `grdCurrentRole()` values) and allows `'owner'` —
  same single-role check as every prior rollout.
- Standard structural checks (`tools/checkblocks.py sairngrounds.html`,
  `tools/div_balance_check.py sairngrounds.html`) after every change.
- Full Guardian v2 pass before push; live-verify against
  `sairn.vercel.app/sairngrounds` after push — both steps of the Push
  Protocol, neither optional.
