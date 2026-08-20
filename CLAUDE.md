# StoneDesk Development Guidelines

## SYNTAX RULE
**Run Node --check before touching any file. Zero errors before any changes. Zero errors before any push. Never bulk replace.**

Always:
1. Extract and test each script block with `node --check` individually
2. Fix one error at a time, then recheck
3. Verify zero errors before committing changes
4. Use targeted, precise edits — never bulk find-replace across the codebase

## Project Context
- Codebase: stonedesk.html (~2.0MB single-file app, grows over time)
- Script block count and pass-rate change every session — **do not hardcode
  a number here.** Re-verify against the file directly (HTML-parser-based
  extraction, not `grep -c '<script'` — see sairn-guardian-v2 Check 0a for why)
  and check the most recent `SAIRN-SESSION-N-HANDOFF.md` for current status
  before assuming anything about pass rate or known-broken script indices.
  A hardcoded "known issues" list here went stale within hours once already
  (2026-07-26) — this file listing specific broken script numbers is exactly
  the kind of claim that needs re-verification, not trust.

## Branch — resolved 2026-07-26
Repo default branch is **main**. All real work lands there. `master` fell
behind and should be treated as stale unless independently re-verified —
and re-verify that independently each session rather than trusting this
line indefinitely, the same way this line itself corrects an earlier wrong
claim about which branch was stale.

## Session Handoffs
Before starting any work, check the repo root for the most recent
`SAIRN-SESSION-N-HANDOFF.md` (highest N) and read it first — CLAUDE.md
is static and only reflects what was true when last edited; the
handoff carries the latest verified state, open items, and corrections.
See the `sairn-session-handoff` skill for the template and naming
convention.

## Known resolved issues (don't rediscover these)
- `sairn-app-scaffold` was falsely claimed built in an earlier session's
  handoff (before 2026-07-30); it was actually created 2026-07-30 and is
  real and active in `.claude/skills/` as of 2026-08-07 — re-verify its
  existence before trusting either the old "false" claim or this update.
- The old `SAIRN1/Fabricor` repo on Railway is an abandoned duplicate
  codebase — StoneDesk's real, current code lives only in `stonedesk.html`
  on `SAIRN1/SAIRN` (Vercel). Don't resurrect or reference Fabricor without
  a specific new reason to.

## Skills — read these, don't just rely on trigger-word matching
This project has a full skill set covering more than syntax. At minimum,
be aware these exist and read them when the situation matches, even if you
arrived here through this file rather than a trigger word:
- `sairn-guardian-v2` — the full mechanical check (syntax, fabricated-KPI
  detection, coverage-disclosure standard, dormant-code rule, multi-codebase
  drift, safe-editing rules). This supersedes the old `sairn-code-guardian`
  entirely — that one is now a deprecation stub.
- `sairn-decision-gate` — run before any RFP/proposal work, before claiming
  "production/complete/live" to anyone outside the team, or before any
  AI-governance-related question (uses NIST AI RMF, Shipley Bid/No-Bid,
  Gary Klein's Premortem).
- `sairn-software-architect` — the reference architecture standard (file
  size ceiling, data model conventions, Bridge+Proxy pattern) and the
  judgment layer above code quality.
- `sairn-mobile-sync` — the standard pattern for any phone/field/POS/
  real-time feature, used identically across every SAIRN app.
- `sairn-training-needs-assessment` — the standard pattern for an employee
  training-needs / skills-gap tool (Hennessy-Hicks-style importance/
  performance-gap methodology, two-perspective self+management structure,
  optional DISC-style module), extracted from SAIRNbuild's real,
  live-verified build. Reusable across every SAIRN app; per-app role
  vocabulary and item-bank wording still need an explicit judgment call
  each time, not silently copied.
- `code-scrubber` — generic (non-SAIRN) code quality pass, now with the
  same Step 0 reality-check additions as Guardian.

## Tech Stack
- Frontend: Vanilla JavaScript
- Backend: SAIRN API Proxy (Claude integration)
- Deployment: Vercel

## Environment Notes
- Use `python`, not `python3`, on this machine — python3 resolves to the
  Microsoft Store stub, not the real install at C:\Python314\python.exe.

## Response Style
- No narration before or after actions — act, then report only the result
- No "let me check / good news / confirmed" commentary
- On error: state what failed and what's needed, nothing more
- Enforcement note (2026-07-29): silent output style stays active — no
  hook can mechanically block narration text, so compliance is self-checked
  every turn; don't swap styles (e.g. caveman) to fix drift, it won't help.

## Push Protocol — standing rule, both directions, no exceptions
1. **Before pushing:** run full Check 0 + all 26 sairn-guardian-v2 checks
   locally against the changed file(s). Do not push on a partial check or
   on "syntax passed" alone — syntax-clean is necessary, not sufficient.
2. **After pushing:** live-verify the specific fix against
   `sairn.vercel.app/stonedesk` directly (real `curl` or equivalent), never
   assumed from the push itself succeeding. A clean `git push` output is
   not proof the live app reflects the change.
Neither step is optional, going forward, regardless of how small the change looks.

## Verification Discipline (added 2026-08-18)
A status report is a claim, not a fact, until checked against the real current state:
- Never report a migration, config change, or prior fix as "already done" from memory or a prior session's summary — verify it live (query the DB, curl the real deployed endpoint, re-read the current file) before saying so.
- When re-confirming something already marked done, check the CURRENT file/state, not a cached read from earlier in the session — code can change between when you last saw it and now, including from a parallel session.
- A claim of "verified" needs the actual evidence in the report (the command run, the real output), not just the conclusion.
- If a discrepancy between assumed and actual state turns up, report it plainly rather than downplaying or auto-correcting silently — the correction itself is often the most valuable part of the report.

## Model Selection
- Default: Sonnet 5 High for all routine work (implementation, debugging, most fixes)
- Proactively recommend switching to Opus 4.8 for: hard debugging with an unclear root cause, or security-critical code
- Proactively recommend opusplan mode for: architecture/design decisions (new systems, schema design, anything with real tradeoffs to weigh)
- Once the Opus/opusplan-level work is done, proactively recommend switching back to Sonnet 5 High for the routine implementation that follows — don't stay on Opus by default
- State the recommendation clearly (e.g. "This looks like a hard-debugging case — worth switching to Opus 4.8") rather than silently staying on whatever model is currently active

---
*Last Updated: 2026-08-20*
