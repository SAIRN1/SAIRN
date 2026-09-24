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

**One rule is repeated here rather than only linked, because it is the most
common defect shape on this platform after a silent failure and it is cheapest
to get right before the code exists:** a check that depends on another tool
**must fail CLOSED when that tool is absent** — say which tool, say the check
did not run, and fail. A gate wrapped in `if os.path.isfile(other_tool):` does
not skip one check, it **reports a pass it never performed**, and nothing
downstream can tell that from a real one. "Could not run" is a third state and
is never folded into "passed". Full statement and the five times it was fixed
piecemeal before being named: **PR §1.11**.

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
3. **Read the shared status registry.** It is handed to you automatically at
   session start by a `SessionStart` hook, so you should already have it --
   but if you did not, or you want it again mid-session:

       python tools/sairn_status.py

   It lives at `~/SAIRN-SESSION-LOCKS/status`, **outside every clone**, so it
   is current without a fetch -- unlike the claim record and the open-work
   index, which are only as fresh as your last pull. **Write your own row when
   your work changes:**

       python tools/sairn_status.py set --state working --task "<what>"
       python tools/sairn_status.py set --state blocked --task "<what>"                                         --blocked-on "<who or what you need>"
       python tools/sairn_status.py set --state idle

   `blocked` refuses without `--blocked-on`: a blocked row that does not say
   what it is waiting on is a silence wearing a status. **An empty registry is
   NOT evidence that nobody is working** -- it is indistinguishable from one
   nothing writes to, and the tool says so rather than reporting all-clear.
   Full account: `docs/2026-09-16-shared-status-registry.md`.
4. **Check the claim record**, then claim before you begin:

       python tools/sairn_claim.py check   <app> <task words>
       python tools/sairn_claim.py claim   <app> <task words>
       python tools/sairn_claim.py release <app>
       python tools/sairn_claim.py list

   Claim **before** you start, not after you finish. A claim that is not
   committed is invisible to every other clone (PR §2.2). A block is a claim to
   verify, not a fact — and never reword your task string to slip past the
   matcher (PR §4.3).
5. **Verify before you report.** A status report is a claim, not a fact, until
   checked against real current state (PR §5).

## Where things live

- **Branch:** `main`. All real work lands there. `master` is stale — re-verify
  independently rather than trusting this line indefinitely.
- **Clones**, each a separate clone of `SAIRN1/SAIRN` on `main`. **Do not count
  them from this list — count the directories.** This line said *"Four clones"*
  and named four for weeks after a fifth existed on disk and was pushing
  commits; corrected 2026-09-16 when `tools/landing_verification.py` discovered
  five. The list below is the registry corrected to match real state, which is
  the direction that correction always runs.

  | Session | Clone | Active-work file | Claim file | Role |
  |---|---|---|---|---|
  | Hank | `Documents\SAIRN-hank` | `SAIRN-ACTIVE-WORK-hank.md` | `.claude/claims/hank.json` | build |
  | CC | `Documents\SAIRN-cc` | `SAIRN-ACTIVE-WORK-cc.md` | `.claude/claims/cc.json` | build |
  | Cody | `Documents\SAIRN-cody` | `SAIRN-ACTIVE-WORK-cody.md` | `.claude/claims/cody.json` | build |
  | Fourth | `Documents\SAIRN-fourth` | `SAIRN-ACTIVE-WORK-fourth.md` | `.claude/claims/fourth.json` | build |
  | **Hover auditor** | `Documents\SAIRN-hover` | *none — it logs to its own skill, see below* | `.claude/claims/hover.json` | **audit, NOT build** |

  **Append only to your own active-work file.**

  **THE FIFTH IS NOT A FIFTH BUILD AGENT and the difference is structural, not
  a label.** `Documents\SAIRN-hover` is the hover auditor: it does not build,
  it adversarially checks what the four build agents built, and it keeps its
  own tamper-evident record rather than an `SAIRN-ACTIVE-WORK-*.md`. Its scope
  is `.claude/skills/sairn-hover-auditor/` and nothing else —
  `tools/hover_auditor_scope_gate.py` (prevent) and
  `tools/hover_separation_audit.py` (detect) enforce that, and
  `docs/2026-09-15-hover-auditor-separation-enforcement.md` is the full account.
  **A build agent must not reach into that clone**, including to arm those
  gates; that is the same boundary problem running the other way.

  Handoffs live only in a real clone — never write one to `C:\Users\marsh\`
  directly.

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
- **TLC (the TLA+ model checker) needs two things this repo does NOT carry,
  and both are ONE-TIME per clone.** `tools/run_tlc.py` exits **2 COULD NOT
  RUN** — never 0 — when either is missing, and prints these lines itself:

      winget install --id Microsoft.OpenJDK.17    # needs an elevated prompt
      curl -sSL -o tools/vendor/tla2tools.jar \
        https://github.com/tlaplus/tlaplus/releases/latest/download/tla2tools.jar

  `tools/vendor/` is **gitignored on purpose**: the jar is 2.3MB of third-party
  binary and vendoring it would put it in every clone and every diff. The cost
  is that a clone without network access cannot model-check, which is why
  `run_tlc.py` is **not** a push gate — `tools/role_gate_invariants.js` is the
  one that runs everywhere. A JRE is enough; `javac` is not needed.

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

**BEFORE BUILDING ANY CHECKER, PROBE, GATE OR TOOL, read
`docs/2026-09-13-cross-domain-disciplines.md`.** Ten standing conventions (the ninth, 2026-09-25: verification rigor follows what the artifact IS -- the real costly thing earns exhaustive verification, a cheap stand-in earns iteration; the tenth, 2026-09-24: segmented verification -- no long run whose first check is at the end), each
paid for by a real defect: lock a check's criteria against synthetic fixtures
before running it on real data; report accuracy and stability as two numbers,
never one; publish a named uncertainty table rather than a combined figure; set
the alarm tighter than the failure point; run the deep validation with its
subject NOT trusted; and require a structurally different method for
independence. **And a seventh, which is not about checks at all: byte-identical
is not safe-in-context** -- propagating a proven pattern needs the target's
scale, input range and criticality tier re-qualified, not just a diff proving
the code matches. Ariane 5 Flight 501 destroyed a vehicle with correct,
faithfully-copied software, and two identical redundant units failed identically
because a second copy is not a second opinion. **And an eighth, which is about
TIME rather than design: nothing announces the day a check stops testing
anything** -- a string anchor that no longer matches, a generator's `--check`
comparing a document to its own output, a snapshot whose verdicts are as of a
capture hours ago. Re-reference against the SOURCE, on a cadence taken from a
MEASURED drift rate. **Re-measured 2026-09-15: 6 of 50, down from 23 of 39 on
2026-09-13** (`python tools/sabotage_control_check.py`). Do not quote either
figure from here — run it. **Part of that improvement was the TOOL, not the
controls:** it did not recognise the UNIQUENESS guard (`count(anchor) != 1`),
which is *stronger* than the `anchor in src` shape it did accept, so five
well-written controls were being reported as unguarded and the signal was
inverted — a probe that did the harder thing scored worse. Criteria are now
stamped `CRITERIA_VERSION` and the blind lock carries fixtures for that shape in
both directions. **And a tenth (2026-09-24), which is about LENGTH: no long run
whose first check is at the end** -- break it into segments, each verified at
its boundary against something the run did not itself produce, the way the
Gotthard Base Tunnel's intermediate shafts let short surveyable drives replace
one 57km leap of faith. Paid for the day it was adopted: a stale plan snapshot
dispatched a rebuild of a tool that had existed for ten days, because nothing
between the snapshot's writing and its execution re-checked it against the
repo.

The other six exist because **the tools written to enforce them kept committing
the defects they were built to catch** — a risk scorer that
fabricated a 38% accuracy from false positives, a testability gate that read the
wrong column, a regex that shipped with a literal backspace and could never
match. None were caught by review; each was caught by a control built to make
the tool fail on purpose.

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
