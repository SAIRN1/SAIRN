# SAIRNcash AI-Advancement — 5-Capability Scope Check

**Status:** Read-only scoping. No app files touched. Nothing built yet.
**Date:** 2026-08-18
**Author:** CC

## What was checked

Read `sairncash.html` (1066 lines) in full and grepped for every pattern
the other four capability rollouts (SAIRNbiz, SAIRNcode, SAIRNvet, SAIRNlaw)
actually used to confirm presence: `SpeechRecognition`/voice-attach
handlers, `predictive`/`Insights` render functions, `shared_knowledge`/
`sd_shared_knowledge`, `tools:`/`tool_use`/attention-digest patterns, and
any AR/camera/measurement code. Also checked `api/claude.js`'s
`sairncash` entry and `api/sairncash/*` (checkout, trial-start/verify/
renew, waitlist — no data-sync endpoint there, unlike StoneDesk's
`sd-data.js`).

## Current real state: 0 of 5 already built

Unlike SAIRNbiz (3/5 already done) or SAIRNcode (found intact post-Pass-2),
SAIRNcash has none of the five standard capabilities. What exists today:
- A generic single-thread chat assistant (`callClaude()` / `SYSTEM_PROMPT`,
  sairncash.html:1009) — plain Q&A, no tool use, no `tools:` param sent.
- One narrow, separate AI call (`suggestDeductionCategory()`,
  sairncash.html:934) that pre-fills a category label — explicitly *not*
  the general chat path, single-purpose, never auto-saves.
- Real, solid core math and cross-device sync: `incomeCache`/
  `deductionCache` are Firebase-backed (sairncash.html:789-850), quarterly/
  annual tax estimates and retirement-contribution figures are computed
  client-side from real entries — confirmed real, not fabricated.

Data backend note: SAIRNcash is Firebase, not the Supabase/`license_hash`
pattern `sd-data.js` and `sd_shared_knowledge` use for StoneDesk/SAIRNbiz.
Any capability that assumes that schema (shared-knowledge in particular)
needs its own storage design, not a direct port.

## Per-capability fit check (per Michael's "check for genuine fit, don't
force it" standard — same as SAIRNbiz's AR-measurement call)

**1. Agentic follow-up — likely genuine fit.**
SAIRNcash already has real dated data (income/deduction entries, quarterly
deadlines computed via `nextQuarterlyDeadline()`). A narrow attention-item
set is plausible: upcoming quarterly deadline with no set-aside logged yet,
a deduction entry sitting with `category: 'Uncategorized'`, a large income
entry with no matching deduction activity that quarter. Same shape as
SAIRNbiz's `checkAttentionItems`/`get_attention_digest`, just single-user
scale (no employee/task-assignment dimension to it).

**2. Predictive business intelligence — likely genuine fit, narrowly scoped.**
Real history exists to reason over (income/deduction trend over the tax
year). Must follow the same rule already encoded in SAIRNcash's own
`SYSTEM_PROMPT` (sairncash.html:964): Claude narrates a trend or flags a
gap, it never recomputes or restates a number that conflicts with the
client-computed figure. E.g. "your last 2 months of income are trending
above your Q3 estimate's basis" as a plain-language flag, not a new number.

**3. Voice input — likely genuine fit.**
Same rationale as SAIRNvet/SAIRNbiz: quick hands-free entry (dictating an
income or deduction description) is a real freelancer workflow (e.g.
logging an expense between job sites). Would wire into `incDesc`/`dedDesc`
the same way SAIRNbiz wired `ivcust`/`ivamt`.

**4. Shared company-knowledge layer — questionable fit, flagging rather
than forcing.**
The existing `sd_shared_knowledge` design is explicitly "one row per shop,
not per employee" — built for multi-employee businesses where Claude
"learns the company" across different staff's questions. SAIRNcash is a
single-freelancer tool: there's no second employee's questions to
aggregate against, so the stated purpose of the feature (building a
shared vocabulary *across people*) doesn't clearly transfer to a
single-user product. It would also need a new storage design since
SAIRNcash's backend is Firebase, not the Supabase `license_hash` scheme
the existing implementation depends on. Recommend treating this as a real
open question for Michael rather than building a reduced version by
default — same posture SAIRNbiz used for AR measurement.

**5. AR measurement — no genuine fit.**
SAIRNcash has no physical/photographic subject to measure (no property,
vehicle, room, or material — it's income/deduction/tax figures only).
Same conclusion as SAIRNbiz reached for its own AR check, for the same
reason (no real panel this maps to). Recommend not building.

## Explicitly out of scope for this task

Bridge integration (pulling data from other SAIRN B2B apps into SAIRNcash)
is deferred per Michael's note — not touched, not scoped here. This
writeup covers only the 5 standard capabilities.

## Recommended build order, pending Michael's go-ahead

1. Voice input (smallest, most mechanical, matches an established pattern)
2. Agentic follow-up (real narrow attention-item set, listed above)
3. Predictive business intelligence (needs the narrate-don't-recompute
   guardrail built in from the start, same as item 2)
4. Shared company-knowledge layer — hold for Michael's call on whether a
   single-user vocabulary layer is worth building at all
5. AR measurement — recommend not building

No code changed. Report only.
