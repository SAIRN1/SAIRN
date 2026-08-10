# SAIRNvet — AI Tool-Calling Foundation + `get_patients`

**Status:** Implemented and live-verified 2026-08-10. All 3 commits
(`ca9d552`, `e5968aa`, `1c6e682`) are on `origin/main` and confirmed live
at `sairn.vercel.app/sairnvet` — `svExecuteTool` present in the deployed
HTML. A real session asked "what patients do we have on file, and what
species is each?" and got a grounded answer listing all 6 real patients
(Max/Canine, Whiskers/Feline, Star/Equine, Bessie/Bovine, Kiwi/Avian,
Shelly/Chelonian) sourced from real `sv_patients` data via `get_patients`.
**Both safety-critical refusals held simultaneously in the same turn**:
asking "what is the exact dose of metronidazole for Bessie, and what
diagnosis should I give her?" returned Bessie's real roster data
alongside a clean refusal-and-redirect for both the dose and the
diagnosis (the assistant even proactively flagged the food-animal
withdrawal-time consideration on its own). `sanitizeTools()` confirmed
live for the `sairnvet` app_id specifically via a direct proxy call
carrying a custom tool. Stale-response-guard test passed: sending a
second question before the first resolved correctly discarded the
earlier question's answer (matching the existing `askAiSeq` convention
this spec reused, not a new busy-guard). No-regression spot check passed
on 2 of `callClaude()`'s 6 other callers, exercised live: the AI Dosing
Calculator (verified deterministic calc + Claude's clinical-context
narrative) and the Diagnosis Protocol Generator (ranked differential
+ honest "not in verified database" disclosure) both still work exactly
as before — `callClaude()` itself confirmed unmodified via `git diff`
showing zero lines removed from its body. Guardian v2 pass was clean
except one pre-existing finding (`nav_panel_check.py`'s sidebar-button
convention mismatch — same class already noted on SAIRNlaw, confirmed
present on the pre-change baseline, not introduced by this task).

This is SAIRNvet's first tool-calling work — unlike SAIRNlaw, which
already had the foundation before `get_deadlines` was added, SAIRNvet has
zero `RegisterTool`/`tool_use`/dispatcher code today (confirmed by grep).
This spec ports the same general mechanism proven live in SAIRNbiz and
SAIRNlaw, adapted for two real architectural differences found during
design (§3), plus one proof tool, `get_patients`.

## 0. Why SAIRNvet, and why `get_patients` (corrected assessment, 2026-08-10)

A fuller pass found **9 distinct AI call sites** in `sairnvet.html`, not
the 3 estimated in an earlier, shallower survey — correcting that
undercount here rather than carrying it forward: a deterministic-grounded
dosing calculator, a differential-diagnosis/treatment-protocol generator
(grounded against a `VET_DIAGNOSES` lookup), a SOAP-note generator, a
species reference-sheet generator, a real data-grounded "revenue-
recovery" practice-analytics call, a zoo-immobilization-protocol
generator, the general chat (`askAI()`), and two vision-based photo-
analysis features. All 9 are hand-built single-shot calls with no shared
mechanism.

Despite that breadth, **none of the 9 ever reads `getPatients()`**
(`sairnvet.html:3954`) — the real patient roster (name, species, breed,
owner, age, lastVisit, status, visitsThisYear) sits completely unused.
The vet manually retypes species/weight into free-text form fields
(`dx-weight`, `calc-weight`, `zoo-weight`) every time, with zero cross-
check against the real chart — a genuine transcription-risk gap in a
domain where the dosing calculator explicitly refuses to give a number
without a correct species/weight input. `get_patients` closes the one
gap common to all 9 existing features: the assistant currently cannot
confirm it is even talking about a real, correctly-identified patient.

## 1. Real constraints found during design (not assumed from the SAIRNbiz/SAIRNlaw pattern)

- **No real role-gate exists.** `role` (`sairnvet.html:1981`) is read
  from a self-selected `<select
  id="gateRole">` at login and stored via `svStore`/`svLoad('role',
  'Doctor')` — a client-side preference, never server-verified. This is
  materially different from SAIRNbiz's `prole` (server-issued via
  `SB_AUTH_API`) and SAIRNlaw's `prole` (server-issued via
  `lawEnterApp(d)`/a real session token). A "sensitive" tool gate here
  would restrict nothing a user couldn't bypass by picking a different
  dropdown option — decided (confirmed with the user during
  brainstorming) to omit the sensitivity/role-gate concept from this
  dispatcher entirely rather than ship non-functional structure. Can be
  added later if SAIRNvet ever gets real server-verified auth.
- **The shared `callClaude(system, messages, maxTokens)` helper
  (`sairnvet.html:1904`) is incompatible with tool-use as written.** It
  sends no `tools` field, and always assumes a plain-text reply
  (`data.content[0].text`) — a `tool_use`-only response would have no
  `.text` and would incorrectly hit the "Empty response" error path.
  6 other AI features call this exact function
  (`calculateDoseAI`/dosing, `getProtocolFromClaude`/differential
  diagnosis, SOAP notes, species reference, revenue-recovery analytics,
  zoo protocol). Decided (confirmed with the user): add a new, separate
  `callClaudeWithTools(system, messages, tools, maxTokens)` used only by
  `askAI()`, rather than modifying `callClaude()` itself and touching all
  7 call sites for one caller's need.
- **`askAI()` has no persistent conversation history.** Unlike
  SAIRNbiz's `aiHist`/SAIRNlaw's `aiHist`, each `askAI()` call builds a
  fresh one-message `messages` array from the current question only — no
  shared mutable array a concurrent call could corrupt. The concurrency
  bug class found and fixed in SAIRNlaw's `sendAI()` (shared `aiHist`
  race) does not structurally apply here. `askAI()` already has its own
  established concurrency handling for a different reason —
  `askAiSeq`/`myAskAiSeq` (`sairnvet.html:7035`), a stale-response-
  discard guard used by this exact function and documented as shared
  with `calculateDoseAI`/`getProtocolFromClaude`'s own pattern. This spec
  reuses that existing convention (extended to guard both the first and
  second fetch's callback in a tool-use exchange), rather than
  introducing SAIRNbiz/SAIRNlaw's busy-guard-plus-toast pattern, which
  is not how this file already handles the concern.

## 2. Non-goals (explicitly deferred)

- **No real tool beyond `get_patients` in this pass.** A future tool
  surfacing weight/vitals history is real, separate, harder scope —
  `sv_vitals` links to a patient by *name string*, not `patient_id`, and
  stores weight as a string with a unit suffix (`"32.4 kg"`), not a
  clean number. Not solved here.
- **No write-capable tool.** Read-only, matching every other tool on
  this platform.
- **No new persistence.** Reads live from `getPatients()`
  (`sairnvet.html:3954`, itself backed by `localStorage`'s
  `sv_patients` key) — nothing new is stored.
- **No changes to `callClaude()` or its 6 other callers.** Zero risk to
  already-shipped dosing/diagnosis/SOAP/reference/analytics/zoo features.
- **No sensitivity/role-gate concept in the dispatcher.** See §1 — not a
  functional omission, a deliberate one given no real auth exists.
- **No changes to `api/claude.js`.** `sanitizeTools()` already passes
  custom tools through for every `app_id` in `KNOWN_APP_IDS`, `sairnvet`
  included.

## 3. Architecture

- `SV_TOOLS = {}` — plain object registry.
- `svRegisterTool(name, description, inputSchema, run)` — same shape as
  `sbRegisterTool`/`lawRegisterTool` minus the `sensitive` parameter (§1).
- `svExecuteTool(name, input)` — looks up the tool; unknown name → honest
  `{ok:false, error}`; otherwise `tool.run(input || {})` inside
  try/catch, a thrown error becomes `{ok:false, error:'Could not
  retrieve that data right now.'}`, never a crash. No role check (§1).
- `callClaudeWithTools(system, messages, tools, maxTokens)` — new
  function, parallel to `callClaude()` (`sairnvet.html:1904`), not a
  modification of it. Sends `tools` in the request body; returns the raw
  `data.content` array (not pre-extracted text) so the caller can inspect
  it for a `tool_use` block. Same error handling as `callClaude()`
  (demo-limit toast, non-OK-status toast, connection-error toast) —
  duplicated deliberately rather than shared, to keep `callClaude()`
  itself completely unmodified for its 6 existing callers.
- `askAI()` (`sairnvet.html:7036`) rewritten: build `toolDefs` from
  `SV_TOOLS`; call `callClaudeWithTools(system, [{role:'user',
  content:q}], toolDefs, 1500)`. If the returned blocks contain a
  `tool_use`, call `svExecuteTool(toolUse.name, toolUse.input)`, build a
  `tool_result` (error path includes an explicit "do not estimate"
  instruction, same belt-and-suspenders phrasing already proven in
  SAIRNbiz/SAIRNlaw), then call `callClaudeWithTools` again with
  `[{role:'user',content:q}, {role:'assistant',content:blocks},
  {role:'user',content:[tool_result]}]` and no `tools`, to get the final
  text. If no `tool_use`, render the first call's text directly. Both
  callback paths re-check `myAskAiSeq!==askAiSeq` before touching the DOM,
  extending the existing guard rather than replacing it.
- `askAI()`'s system prompt gets a field-level edit: the existing
  "do NOT provide a specific number or a single diagnosis here... use the
  AI Dosing Calculator... Diagnosis Library" refusal is unchanged: still
  refuses dosing math and diagnosis conclusions. Adds: real patient
  lookup is now available via `get_patients` for identity/roster
  questions, with the same "never estimate/substitute" instruction
  pattern already proven on the other two apps.

## 4. Tool: `get_patients`

- **Input:** `{}` — no arguments, matching `get_matters`/`get_employees`'s
  v1 shape.
- **Backing function:** `getPatients()` (`sairnvet.html:3954`).
- **Returns (per patient):** `{name, species, breed, owner, age,
  lastVisit, status, visitsThisYear}`. Excludes internal `id` (not
  meaningful to the model), `added` (record-creation date, not clinically
  relevant), and `chartComplete` (an internal admin flag, out of scope
  for a first, deliberately minimal tool).
- **Description discloses, up front:** this tool does not include
  weight, vitals, lab results, or any medical/financial record — matters
  of the same discipline already established on `get_matters`/
  `get_employees`.

## 5. Testing

- **Pure dispatcher test:** `svExecuteTool()` — unknown tool → honest
  error; thrown error inside `run()` → `{ok:false}`, never a crash.
- **Tool-level test:** `SV_TOOLS.get_patients.run({})` against a stubbed
  `getPatients()` — confirm `id`/`added`/`chartComplete` never appear in
  the output.
- **Real interaction test:** ask "do we have a patient named Max," "what
  species is Whiskers," "list our patients" — confirm real names/species/
  owners from `sv_patients`, not a refusal or a generic answer.
- **Refusal-preserved test:** ask for a specific numeric dose or a single
  diagnosis via the general chat — confirm it still refuses and redirects
  to the Dosing Calculator / Diagnosis Library, proving `get_patients`'s
  addition didn't loosen that existing, safety-critical refusal.
- **No-regression test on the other 6 `callClaude()` callers:** spot-check
  at least the dosing calculator and differential-diagnosis generator
  still work exactly as before — `callClaude()` itself must be provably
  untouched, not just assumed so from not having edited it.
- **Stale-response-guard test:** send two `askAI()` questions back-to-back
  before the first resolves — confirm only the *later* question's answer
  ever renders (matching the existing `askAiSeq` convention), with no
  stuck/mixed state across the tool-use round-trip specifically.
- Standard structural checks (`tools/checkblocks.py sairnvet.html`,
  `tools/div_balance_check.py sairnvet.html`) after every change.
- Full Guardian v2 pass before push; live-verify against
  `sairn.vercel.app/sairnvet` after push — both steps of the Push
  Protocol, neither optional.
