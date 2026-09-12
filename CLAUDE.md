# SAIRN Development Guidelines — the fresh-session primer

**This file is the concrete facts and what to check before you start work.**
The discipline and judgment half — how checks fail silently, how to edit a
standing document, what each push-protocol step actually means, why the claim
system is shaped the way it is — lives in **`docs/SAIRN-PROCESS-RULES.md`**.

Split 2026-09-12. One file was serving two audiences and the start-of-session
facts were buried inside incident narratives. Section numbers below in the form
**PR §x.y** point into the process rules.

**Read the process rules when:** you are about to write a check, probe, hook or
tool; you are editing a standing document; a gate blocked you; a check passed and
you are not sure it tested anything; or something failed and said nothing.

---

## Before you touch anything

1. **Read the most recent handoff.** This file is static and only reflects what
   was true when last edited; the handoff carries the latest verified state.
   Find it by **DATE**, not by a counter — handoffs are named
   `APP-YYYY-MM-DD-subject-handoff.md`. Sort by the date in the filename, then
   **confirm the subject matches the work you were actually sent to do**; if it
   does not, say so immediately rather than proceeding on the wrong document.
   (Why not a counter: PR §6.)
2. **Read all four `SAIRN-ACTIVE-WORK-*.md` files** for the app or subject you
   were sent at. Not for write conflicts — for *"is somebody already doing
   this."*
3. **Check the claim record**, then claim before you begin:

       python tools/sairn_claim.py check   <app> <task words>
       python tools/sairn_claim.py claim   <app> <task words>
       python tools/sairn_claim.py release <app>
       python tools/sairn_claim.py list

   Claim **before** you start, not after you finish. A claim that is not
   committed is invisible to every other clone (PR §2.2). A block is a claim to
   verify, not a fact — and never reword your task string to slip past the
   matcher (PR §4.3).
4. **Verify before you report.** A status report is a claim, not a fact, until
   checked against real current state (PR §5).

## Where things live

- **Branch:** `main`. All real work lands there. `master` is stale — re-verify
  independently rather than trusting this line indefinitely.
- **Four clones**, each a separate clone of `SAIRN1/SAIRN` on `main`:
  `Documents\SAIRN-hank`, `Documents\SAIRN-cc`, `Documents\SAIRN-cody`,
  `Documents\SAIRN-fourth`. Handoffs live only in a real clone — never write one
  to `C:\Users\marsh\` directly.
- **Active-work log — append only to your own file:**

  | Session | Clone | File |
  |---|---|---|
  | Hank | `Documents\SAIRN-hank` | `SAIRN-ACTIVE-WORK-hank.md` |
  | CC | `Documents\SAIRN-cc` | `SAIRN-ACTIVE-WORK-cc.md` |
  | Cody | `Documents\SAIRN-cody` | `SAIRN-ACTIVE-WORK-cody.md` |
  | Fourth | `Documents\SAIRN-fourth` | `SAIRN-ACTIVE-WORK-fourth.md` |

- **Open work:** `docs/SAIRN-OPEN-WORK-INDEX.md`. **Never edit a row by
  splitting on `|`** — rebuild the row whole (PR §2.1).
- **Claims:** `.claude/claims/<session>.json`, one file per clone. Expire after
  4 hours.
- **Tool inventory:** `docs/TOOLING-INVENTORY.md` — generated, not hand-written
  (PR §1.8).

## Project context

- **Codebase:** `stonedesk.html`, a single-file app around 2.0MB and growing.
- **Do not hardcode the script-block count or a known-broken list here.** Both
  change every session; a hardcoded list went stale within hours in 2026-07-26.
  Re-verify against the file directly using **HTML-parser-based extraction, not
  `grep -c '<script'`** — see `sairn-guardian-v2` Check 0a for why — and check
  the most recent StoneDesk handoff for current status.

## Tech stack

- Frontend: vanilla JavaScript
- Backend: SAIRN API Proxy (Claude integration)
- Deployment: Vercel

## Environment

- Use `python`, **not** `python3` — `python3` resolves to the Microsoft Store
  stub, not the real install at `C:\Python314\python.exe`.
- **Line endings, ONE-TIME per clone.** `.gitattributes` is repo-wide so stored
  blobs are LF, but the working-tree half is **not retroactive** and `git
  status` stays clean the whole time, so nothing will ever prompt you. Run once,
  with nothing uncommitted:

      git rm --cached -r -q . && git reset --hard

  Until you do, byte comparisons against anything outside the repo report
  phantom differences. **A CRLF-vs-LF difference is not drift** — compare after
  `tr -d '\r'` before reporting one. That mistake produced three separate false
  alarms in a single session on 2026-09-03.

## Syntax rule

**Run `node --check` before touching any file. Zero errors before any change,
zero errors before any push. Never bulk replace.**

1. Extract and check each script block individually.
2. Fix one error at a time, then recheck.
3. Verify zero errors before committing.
4. Targeted, precise edits — never bulk find-replace across the codebase.

## Push protocol — both directions, no exceptions

Full detail in **PR §3**. The short form:

1. **Before pushing** — run full Check 0 plus **every** `sairn-guardian-v2`
   check against the changed files. **Do not write the number of checks
   anywhere**; re-read the skill's own `## The N Checks` heading, which is the
   only source that moves when a check is added. That count has been wrong in
   three places at once before (PR §2.3). Syntax-clean is necessary, not
   sufficient.
2. **After pushing** — live-verify the specific fix against the real deployed
   URL. A clean `git push` is not proof. **Not with bare `curl`**: use
   `tools/sairn_http.py` from a script, or
   `mcp__claude_ai_Vercel__web_fetch_vercel_url` from a Claude turn. A 403 means
   **UNVERIFIED**, not verified-good (PR §3.2).
3. **Seed files** must already match the live licence — the push gate enforces
   this mechanically and DENIES on drift. "Could not tell" is not a pass.
   Override is `SAIRN_SEED_GATE=off` at the **front of the push command itself**,
   and **say so out loud when you use it** (PR §3.3).
4. **SQL that writes credential rows** must carry the recoverability guard — two
   end states are safe and only two. Read the app's own `PROVISIONING_ROLES`;
   SAIRNcode's is `admin`, not `owner` (PR §3.4).

Neither of the first two steps is optional, regardless of how small the change
looks.

## Skills — read them, don't rely on trigger-word matching

**Precedence when several skills cover one job:
`docs/2026-08-30-skill-precedence.md`.**

**Do not trust any skill count written down anywhere, including here.** That
number has been wrong more than once. Count the directories when you need the
figure. The repo mirrors the SAIRN skills from the user store; **compare after
`tr -d '\r'` before reporting a mirror as diverged** — the user store is CRLF
and the repo is LF, so a bare `diff` reports content-identical files as changed.
`grill-me` carries `disable-model-invocation: true`, so it is absent from the
model-facing list **by design** and is not missing.

Picking between overlapping skills:

- **Design** — `sairn-client-facing-design` wins on any existing SAIRN app;
  `frontend-design` for genuinely new UI; `design-taste-frontend` is scoped to
  marketing sites and rarely applies; `ui-ux-pro-max` is a lookup table, not a
  competitor.
- **Performance** — pick by layer: `perf-profiler` (backend/queries),
  `performance` (frontend broad), `core-web-vitals` (a named metric).
- **Security** — `sairn-guardian-v2` and `sairn-code-scrubber` run first;
  `owasp-security` is the canonical general layer.
- **Skill management** — a pipeline, not duplicates: `self-improving-agent`
  harvests → `skill-creator` authors → `skill-vetter` admits third-party skills.

Know these exist and read them when the situation matches, even if you arrived
here without a trigger word:

- `sairn-guardian-v2` — the full mechanical check: syntax, fabricated-KPI
  detection, coverage disclosure, dormant code, multi-codebase drift, safe
  editing. It replaced `sairn-code-guardian` entirely (PR §6).
- `sairn-decision-gate` — before any RFP or proposal, before claiming
  "production / complete / live" to anyone outside the team, and before any
  AI-governance question.
- `sairn-software-architect` — reference architecture: file-size ceiling, data
  model conventions, Bridge+Proxy, and the judgment layer above code quality.
- `sairn-code-scrubber` — SAIRN-specific bug-pattern scanner.
- `sairn-context-budget` — before reading or quoting from anything large. **A
  truncated read is indistinguishable from a complete one** (PR §1.7).
- `sairn-memory-curator` — before writing a fact into any standing document.
- `sairn-mobile-sync` — any phone/field/POS/real-time feature.
- `sairn-app-scaffold` — starting a new app from zero.
- `sairn-training-needs-assessment` — employee training-needs / skills-gap
  tooling. Per-app role vocabulary still needs an explicit judgment call each
  time, not a silent copy.

## Response style

- No narration before or after actions — act, then report only the result.
- No "let me check / good news / confirmed" commentary.
- On error: state what failed and what is needed, nothing more.
- No hook can mechanically block narration text, so this is self-checked every
  turn. Do not swap output styles to fix drift; it will not help.

## Model selection

- **Default: Sonnet 5 High** for routine work — implementation, debugging, most
  fixes.
- **Recommend Opus** for hard debugging with an unclear root cause, or
  security-critical code.
- **Recommend opusplan** for architecture and design decisions with real
  tradeoffs.
- When the hard part is done, **recommend switching back** to Sonnet 5 High for
  the routine implementation that follows.
- State the recommendation out loud rather than silently staying on whatever
  model is active.

---
*Primer last updated 2026-09-12. Process rules: `docs/SAIRN-PROCESS-RULES.md`.*
