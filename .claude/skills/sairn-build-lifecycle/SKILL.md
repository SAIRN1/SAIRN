---
name: sairn-build-lifecycle
description: 'The complete, ordered script for building any SAIRN app — B2B or consumer — from zero to genuinely market-ready. Synthesizes every phase learned across 10 real B2B builds into one sequential process. Not a lessons-learned index (see sairn-master-orientation for that) — this is the actual build order, phase by phase, referencing the right specific skill at each stage. All branches (commercial and consumer) are internal to SAIRN Technologies and follow this same script.'
---

# SAIRN Build Lifecycle — Conception to Market-Ready

Six phases, in order. Skipping a phase or doing them out of order is exactly how tonight's real bugs got into 10 apps in the first place — this script exists so the next app never needs a night like tonight to reach the same standard.

## Phase 0 — Conception (before any code)

1. **`brainstorming`** — refine the raw idea through real, hard questions. Not rhetorical ones: "is AI actually needed here, or is deterministic code enough" (per `sairn-adversarial-reviewer`'s AI-guessing check), "what's the zero/negative/empty case" (per `sairn-forward-scan`), "does this collide with an existing color/signal meaning" — ask these at design time, they're far cheaper here than after shipping.
2. **`sairn-decision-gate`'s Bid/No-Bid** — for a new vertical or major commitment: is this real, do we meet the bar today, what's the true cost, what's the cost of a no.
3. **`writing-plans`** — convert the refined idea into a real implementation plan, task by task.
4. **Explicit "go" required** — standing rule, no exceptions: present the full plan, wait for actual approval, never start writing code on an assumed yes.

## Phase 1 — Architecture, decided before the first line of code

1. **`sairn-software-architect`'s reference architecture** — file structure, size ceiling awareness, the Bridge+Proxy pattern, data model conventions. Decide these now, not after 60 panels exist.
2. **The two preventive checks, baked in from day one, not retrofitted:** grep before creating any storage key (does it already exist), grep before wiring any function to a DOM target (does the container exist). This single habit prevented more real bugs tonight than any other rule.
3. **`sairn-mobile-sync`** — if the app is field/phone-facing, use the one proven pattern (client write + immediate bridge POST, honest polling-not-push framing) rather than inventing a new one per app.
4. **Assign a real, non-colliding brand color** — check `sairn-guardian-v2`'s App File Map before picking one; two collisions from earlier tonight (SAIRNhr/SAIRNvet, SAIRNcare/SAIRNacc) are still unresolved and shouldn't become a third or fourth.

## Phase 2 — Build

1. **`executing-plans`** — build the approved plan.
2. **Reuse proven patterns, don't reinvent per app.** Tonight reused: the trial-gate pattern (`checkTrialGate()`) across 9 apps from one proven original, the AI-response sequence guard across 15+ call sites in 4 different apps, the honest await+check save pattern everywhere. A second implementation of something that already works correctly elsewhere is waste at best, a new bug at worst.
3. **After every single edit, not just at a session's end:** `node --check`, div-balance, nav-panel checks. Catching a break immediately is cheap; three edits later means tracing back through all of them.

## Phase 3 — Full review, before calling anything "built"

Run all of these — not a subset, not "whichever seems relevant":

1. **`sairn-guardian-v2`** — Check 0 (syntax, fabrication, dormant-code, multi-codebase) + the 26 numbered checks.
2. **`sairn-portfolio-triage`'s 4 scanners** — duplicate-global, missing-DOM-target, panel-nesting, key-collision. Verify each scanner's portability to this specific app before trusting a raw count; treat an identical alarming result across two apps as a tool problem, not two real bugs. When a raw key-collision hit appears, trace whether it's real shape divergence or just the same backing variable referenced under two different local names before treating it as a finding.
3. **`sairn-silent-failure-sweep`** — every save/sync/submit's real failure path, every money/sync/external-system claim checked against real code behind it, the app-level data-durability question ("if this browser's data is lost, does anything survive, and was that disclosed").
4. **`sairn-adversarial-reviewer`'s 4 personas** — Saboteur, New Hire, Security Auditor, The Auditor (fabrication + AI-guessing-instead-of-calling-real-code).
5. **`ponytail-review`** — what should be deleted, not just what should be fixed.
6. **Infrastructure check, once per shared Vercel project, not per app** — deployment protection/SSO, environment variables, checked directly against the live dashboard, not inferred from application code. Tonight's SSO block was invisible to every code-level check across every app until this was done directly.

## Phase 4 — Market-readiness gate

1. **A real, working trial gate** — the proven `checkTrialGate()` pattern (timestamp-based, honest upgrade path, no fake hard-block) unless there's a specific reason to build differently.
2. **Real competitive pricing research** — not guessed, actually searched, per the category-specific real data (top competitor pricing, market gaps) the same way tonight's consumer/B2B market research was done.
3. **Real, current entry in the Portfolio Audit Status table** (`sairn-parallel-app-scaling`) — and this entry is only real if a corroborating commit exists; a checkmark with no commit backing it is not evidence, tonight found this exact gap costing a genuinely missed CRITICAL bug in two apps.

## Phase 5 — Independent re-verification (do not skip this even if Phase 3 felt thorough)

1. **Self-review is not independent review** — the same session that built the app checking its own work shares its own blind spot. Get a genuinely separate pass: a fresh subagent, a different session, or at minimum re-reading the shipped artifact against the plan line by line.
2. **"100% means 100%"** — every known item genuinely resolved, not just correctly prioritized. A known minor bug doesn't get to ride along under a "done" claim because it's low-severity.
3. **Re-check anything a tracking table claims is done** if there's no real commit backing the claim — this exact re-check found a genuinely missed CRITICAL bug tonight in two apps that were marked "done."

## Phase 6 — Handoff

1. **`sairn-session-handoff`** — write proactively, before capacity runs low, not mid-compaction. Section 3 (what was corrected, not just added) is the core discipline, not optional.
2. **`sairn-master-orientation`** stays the fast-entry-point for the next session; this skill (`sairn-build-lifecycle`) is the specific ordered script for building the next app, referenced from there.

## What this replaces

Nothing — every skill named above still exists and still matters on its own. This is the sequence they run in, for a real build from zero, so the next app follows this path deliberately instead of the fragmented, multi-session, retrofit-heavy path that produced tonight's real bugs across 10 existing apps.
