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
  and check the most recent StoneDesk handoff for current status (find it
  by date — see Session Handoffs below, not by a counter)
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

## Session Handoffs — lookup rule CORRECTED 2026-08-23
Before starting any work, read the most recent handoff first — CLAUDE.md
is static and only reflects what was true when last edited; the handoff
carries the latest verified state, open items, and corrections.

**Find it by DATE, not by a counter.** Handoffs are named
`APP-YYYY-MM-DD-subject-handoff.md` (e.g.
`SAIRNLAW-2026-08-23-lemaj-handoff.md`). Sort by the date in the filename,
then **confirm the subject matches the work you were actually sent to
do** — if the content doesn't match your task, say so immediately rather
than proceeding on the wrong document.

**Do not take the highest N.** This file previously said to find the
latest handoff as the highest-numbered `SAIRN-SESSION-N-HANDOFF.md`. That
rule failed in production on 2026-08-23: two different real
`SAIRNLAW-SESSION6-HANDOFF.md` files existed at once (trust-disbursement
2026-08-18, LeMAJ 2026-08-23), and a session sent to continue the second
read the first and found none of its work. A counter cannot stay unique
across concurrent sessions in separate clones. Older files keep their
existing names and are **not** renamed — so both patterns are on disk;
that is expected, not drift.

Handoffs live only in a real clone — there are **four**, corrected
2026-08-24 (this line previously listed three and omitted
`SAIRN-fourth`): `Documents\SAIRN-hank`, `Documents\SAIRN-cc`,
`Documents\SAIRN-cody`, `Documents\SAIRN-fourth`. All four verified on
disk that date as separate clones of `SAIRN1/SAIRN` on `main`. Handoffs
are **not written until committed in the same action** — a local-only
handoff is invisible to every other clone. Never write one to
`C:\Users\marsh\` directly.

## Active work is logged per session — 2026-08-24

`SAIRN-ACTIVE-WORK.md` is no longer an append target. Four sessions
appending to one file's end produced repeated merge conflicts in a single
night, so each clone now has its own file:

| Session | Clone | File |
|---|---|---|
| Hank   | `Documents\SAIRN-hank`   | `SAIRN-ACTIVE-WORK-hank.md` |
| CC     | `Documents\SAIRN-cc`     | `SAIRN-ACTIVE-WORK-cc.md` |
| Cody   | `Documents\SAIRN-cody`   | `SAIRN-ACTIVE-WORK-cody.md` |
| Fourth | `Documents\SAIRN-fourth` | `SAIRN-ACTIVE-WORK-fourth.md` |

Append only to your own file; **read all four** before starting work — the
split removes the write collision, not the need to know what another
session is touching. The shared file keeps every pre-split entry as the
historical record (code comments and SQL headers cite it by name).

See the `sairn-session-handoff` skill for the full convention, the
reasoning, and the template.

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
  drift, safe-editing rules). This replaced the old `sairn-code-guardian`
  entirely. **Corrected 2026-08-24:** that skill is not a deprecation stub —
  there is no `sairn-code-guardian` directory in `~/.claude/skills/`, in
  `C:/SAIRN/skills/sairn/`, or in any clone's `.claude/skills/`.
  **Corrected again 2026-08-28 — the 2026-08-24 line said "do not go looking
  for it" and that was wrong.** It was true of the skill stores and false of
  the repo: 1,230 lines of it were on an unmerged branch the whole time. It is
  now at `archive/branch-lucid-ptolemy-b73vu0/skills/sairn-code-guardian/` on
  `main`, with its full history under the tag `archive/lucid-ptolemy-b73vu0`.
  **Completed 2026-08-28 (CC), verified against the files on disk:** that
  directory holds TWO artefacts, not one — `SKILL.md` (1,230 lines, 81,757
  bytes) **and `sairn_static_checks.py` (32,555 bytes)**, the executable half.
  The earlier description named only the skill, so a reader looking for the
  ancestor's actual check implementations would not have known they survived.
  **The tag is the only thing preserving the history** — it reaches 901 commits,
  every one of them unreachable from `main`, so deleting the source branch was
  safe *because* that tag exists and for no other reason. It is not fetched by
  default: run `git fetch origin tag archive/lucid-ptolemy-b73vu0` before
  expecting to see it locally.
  It is Guardian v2's ancestor and the origin of the duplicate-global check
  now numbered 13, *"added after the June 2026 StoneDesk outage."*
  **Still do not recreate or run it** — v2 supersedes it and the archived copy
  predates every current discipline. Read it for provenance, nothing else.
  The lesson worth keeping: "it does not exist" was a claim about three
  directories, stated as a claim about the whole repo.
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
- `sairn-code-scrubber` — SAIRN-specific bug-pattern scanner, with the same
  Step 0 reality-check additions as Guardian. **Name corrected 2026-08-24:**
  this line previously said `code-scrubber` and described it as the generic
  non-SAIRN pass. No skill by that name exists on disk; the real directory is
  `sairn-code-scrubber`, and its content is SAIRN-specific, not generic.

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
1. **Before pushing:** run full Check 0 + all 30 sairn-guardian-v2 checks
   (**count corrected 2026-08-25** — this line said 26, the loaded global
   copy of the skill said 28, and the committed skill said 30. Three live
   numbers at once. **Do not trust this number either** — re-read the
   skill's own heading, `## The N Checks`, which is the only source that
   moves when a check is added.)
   locally against the changed file(s). Do not push on a partial check or
   on "syntax passed" alone — syntax-clean is necessary, not sufficient.
2. **After pushing:** live-verify the specific fix against
   `sairn.vercel.app/stonedesk` directly (real `curl` or equivalent), never
   assumed from the push itself succeeding. A clean `git push` output is
   not proof the live app reflects the change.
Neither step is optional, going forward, regardless of how small the change looks.

3. **If the push touches a reference SEED file, the live licence must already
   match it.** Added 2026-08-29 after the failure that made it necessary: on
   2026-08-27 two committed SAIRNlaw corrections were never LOADED, and
   `LAW-PINNACLE-2026` — the canonical customer licence — computed federal
   answer deadlines three days late for a day. Step 2 above covers deployed
   CODE; a seed-file change is **inert until a loader runs**, and nothing
   covered that.

   This step is **mechanical, not remembered.** `tools/seed_load_gate_hook.py`
   runs as a PreToolUse Bash hook on every `git push`, looks at the commits
   actually being pushed, and only acts if one touches a seed file. Then:
   - live matches the repo → allows silently (the normal case if you loaded
     first, which is why a correct workflow feels no friction);
   - **drift → the push is DENIED**, naming the app, the rule id, and the
     reload command;
   - could not tell (no key, endpoint unreachable) → allows with a loud note.
     **That is not a pass.** Run
     `python tools/sairn_load_state_check.py --app <app> --key <key>` and
     report the real result rather than treating silence as agreement.

   Load-then-push and push-then-load both end with live == repo; the hook only
   cares that they agree by the time you push. Load first anyway — a denied
   push costs nothing, a shipped-but-unloaded correction costs a wrong legal
   date.

   `SAIRN_SEED_GATE=off` overrides it. **Say so out loud when you use it** — an
   override nobody mentions is how a gate gets hollowed out. The hook fails
   OPEN on any internal error, same standard as the other hooks, because one
   that crashes closed gets disabled and then protects nothing.

   The gate itself is `tools/sairn_load_state_check.py` (`--app sairnlaw |
   sairncare | sairndental | sairnroofing`), which reads the seed files at run
   time so it cannot go stale. **Do not reintroduce a GENERATED gate** — a file
   that must be regenerated after every seed edit reproduces this exact
   silent-failure shape inside the thing meant to catch it. See the superseded
   header on `tools/sairn_build_load_gates.py`.

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
*Last Updated: 2026-08-24*
