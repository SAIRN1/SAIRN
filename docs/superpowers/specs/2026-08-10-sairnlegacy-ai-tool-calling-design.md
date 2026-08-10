# SAIRNlegacy — AI Tool-Calling Foundation + `get_cases`

**Status:** Implemented and live-verified 2026-08-10. `LEG_TOOLS`/
`legRegisterTool`/`legExecuteTool` + `get_cases` shipped, `sendAI()`
rewired with the object-identity splice fix from the start. Confirmed
live on `sairn.vercel.app/sairnlegacy`: real case data returned, no
family-contact/date leakage, concurrent-request ordering correct,
`generateObituary()` unaffected.

This is SAIRNlegacy's first tool-calling work, porting the mechanism
already proven live on every prior rollout — including a concurrency
fix ported *proactively*, from the start, rather than discovered live,
because the exact bug it prevents was just found and fixed on
SAIRNdesign's structurally identical code.

## 0. Why SAIRNlegacy, and what's already good here

SAIRNlegacy has 2 real AI features: `sendAI()` (general chat,
`sairnlegacy.html:1512`) and an obituary generator
(`generateObituary()`, `sairnlegacy.html:2438`, untouched by this
spec). The obituary generator is genuinely well-built: real case data
grounds it (decedent name, DOB/DOD, service type/date, family contact,
notes), it's explicitly instructed *"do not invent biographical
details not provided,"* and it has **dual concurrency protection** — a
sequence counter *and* a direct check that the case selector hasn't
changed underneath a slow response, preventing a stale draft for one
case from silently landing on another.

`sendAI()` grounds on nothing but a static persona. It carries the
**exact same 2026-08-09 splice-based `aiHist` reordering fix**
(`sairnlegacy.html:1520-1526`) that SAIRNdesign's chat had — and that
fix was just found, live, to have a real weakness: its captured-array-
index approach goes stale once a concurrent exchange's insertions land
first and shift the array, which a tool-use round-trip's longer
duration makes far more likely to manifest (confirmed on SAIRNdesign,
`docs/superpowers/specs/2026-08-10-sairndesign-ai-tool-calling-design.md`).
**This spec ports the object-identity-based fix (`aiHist.indexOf()` at
splice time) from the very first implementation, not as a follow-up
fix** — the bug class is already known, porting the broken version
here first would be repeating a mistake already made and corrected
elsewhere in this exact codebase tonight.

**No real auth exists.** `prole` comes from a client-side PIN match
(`sairnlegacy.html:1319` area) — no server backend. Same trust class
as every other non-real-auth app in this rollout series.

**Real, unused data**: `leg_cases` (`sairnlegacy.html:1401`) — `{id,
decedent_name, case_number, decedent_dob, decedent_dod,
family_contact_name, family_contact_phone, family_contact_email,
assigned_director, status, service_type, service_date, notes}`.

## 1. Design decisions

- **No sensitivity/role-gate parameter** — no real auth exists here.
- **The object-identity splice fix is ported from the start** (see §0)
  — `myUserTurn` object + `aiHist.indexOf(myUserTurn)` at splice time,
  not a captured index. This is not an optional hardening step; it is
  the baseline implementation for this rollout.
- **`get_cases` excludes `family_contact_phone` and
  `family_contact_email`** — a deliberate domain-sensitivity judgment
  call, confirmed with the user, departing from prior roster tools
  (`get_customers`, `get_clients`) which included contact phone/email
  for ordinary business contacts. This data involves grieving families
  and decedents, not generic business contacts; the assistant doesn't
  need direct contact details to answer status questions, and
  excluding them reduces exposure of a grieving family's personal
  contact information through an AI chat log.
- **`get_cases` is the v1 proof tool** — same roster-shape precedent
  as every prior tool, adapted for this domain's sensitivity.

## 2. Non-goals (explicitly deferred)

- **No real tool beyond `get_cases` in this pass.** Any future tool
  over dispatch, merchandise, death-record/permit, or document data is
  later, separate scope.
- **No write-capable tool.** Read-only, matching every other tool on
  this platform.
- **No new persistence.** Reads `cases()` (`sairnlegacy.html:1377`)
  directly — nothing new is stored.
- **No changes to `generateObituary()`** (`sairnlegacy.html:2438`) —
  already real, correct, carefully dual-guarded — untouched.
- **No changes to `api/claude.js`.** `sanitizeTools()` already passes
  custom tools through for every `app_id`, `sairnlegacy` included.

## 3. Architecture

- `LEG_TOOLS = {}` — plain object registry.
- `legRegisterTool(name, description, inputSchema, run)` — same shape
  as every non-real-auth app's dispatcher (no `sensitive` parameter).
- `legExecuteTool(name, input)` — unknown tool → honest error;
  otherwise `tool.run(input || {})` inside try/catch, a thrown error
  becomes an honest `{ok:false}`, never a crash.
- `sendAI()` rewired: build `toolDefs` from `LEG_TOOLS`; the existing
  fetch gains a `tools:toolDefs` field. If a `tool_use` block comes
  back, call `legExecuteTool(toolUse.name, toolUse.input)`, build a
  `tool_result`, make a second `fetch` (no `tools` field, built from
  this request's own local turn data, not the shared `aiHist`) for the
  final answer. **Concurrency: replace the captured-index splice
  (`var myUserIdx=aiHist.length`) with an object-identity approach from
  the start** — `var myUserTurn={role:'user',content:q};
  aiHist.push(myUserTurn);` and splice at
  `aiHist.indexOf(myUserTurn)+1` (both for the no-tool-use single-entry
  case and the tool-use 3-entry atomic-group case). If no `tool_use`
  block, behave exactly as today (aside from the concurrency-fix
  change, which applies to both paths).

## 4. Tool: `get_cases`

- **Input:** `{}` — no arguments, matching every prior tool's v1 shape.
- **Backing function:** `cases()` (`sairnlegacy.html:1377`), no new
  lookup logic.
- **Returns (per case):** `{decedent_name, case_number, status,
  assigned_director, service_type, service_date}`. Excludes `id`,
  `decedent_dob`/`decedent_dod` (not needed for a status/roster
  question — the obituary generator is the feature that legitimately
  needs birth/death dates, and it already has direct case-record
  access, not via this tool), `family_contact_name`,
  `family_contact_phone`, `family_contact_email` (§1 — domain-
  sensitivity exclusion, confirmed with the user), and `notes` (free
  text — same discipline as every prior tool's notes-exclusion).
- **Description discloses, up front:** this tool covers case status
  and assignment only — no family contact information, decedent dates,
  or case notes are available through it.

## 5. Testing

- **Pure dispatcher test:** `legExecuteTool()` — unknown tool → honest
  error; thrown error inside `run()` → `{ok:false}`, never a crash.
- **Tool-level test:** `LEG_TOOLS.get_cases.run({})` against a stubbed
  `cases()` — confirm `id`/`decedent_dob`/`decedent_dod`/
  `family_contact_name`/`family_contact_phone`/`family_contact_email`/
  `notes` never appear in the output.
- **Real interaction test:** ask "which cases are open," "who is
  assigned to the Halloway case" — confirm real decedent names/case
  numbers/statuses/directors from `leg_cases`, not a generic answer,
  and confirm no family contact info or dates ever appears even when
  not explicitly asked to exclude them.
- **No-regression test on the obituary generator:** confirm
  `generateObituary()` still works exactly as before — untouched code,
  but a live spot-check is warranted since it shares the same proxy
  and app_id.
- **Concurrency test (object-identity fix, verified from the start,
  not discovered as a bug):** send two questions back-to-back before
  the first resolves, at least one of which triggers `get_cases`
  (longer round-trip). Confirm `aiHist` ends up correctly alternating
  regardless of which response arrives first — this is the exact
  scenario that broke SAIRNdesign's captured-index approach, so it
  must be verified here as a pass, not assumed safe from code review
  alone.
- Standard structural checks (`tools/checkblocks.py sairnlegacy.html`,
  `tools/div_balance_check.py sairnlegacy.html`) after every change.
- Full Guardian v2 pass before push; live-verify against
  `sairn.vercel.app/sairnlegacy` after push — both steps of the Push
  Protocol, neither optional.
