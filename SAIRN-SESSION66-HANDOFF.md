# SAIRN — Session 66 Handoff

Built from a fresh session with no memory of Session 66 itself — everything below was re-derived from `git log`, file contents, and one live `curl` against production, per the standing Guardian v2 rule that handoff claims get independently re-verified, not trusted at face value. Several claims that were relayed at the start of this task did **not** survive verification — those are called out explicitly rather than silently repeated.

## 1. Verified current state

- **`origin/main` HEAD:** `5f8b16ab0d7e63116516f58ea53ffd8ab018d173` ("sairn-guardian-v2: add Check 0d-multi-function..."), 2026-07-26 15:06:21 -0400. Confirmed via `git fetch origin` + `git log origin/main`. (Local working copy is on `master` and is a stale, unrelated checkout of the whole home directory — do not treat local files as source of truth; everything here was read via `git show origin/main:<path>`.)
- **Script blocks in `stonedesk.html`:** ran `tools/checkblocks.py` (HTML-parser-based extraction, not `grep -c`) against the `origin/main` copy of `stonedesk.html` (2,053,600 bytes) — **118 total blocks, 0 failed** (`TOTAL_BLOCKS:118` / `FAILED_BLOCKS:0`). No tool in `tools/` computes panel or nav counts directly; these were derived by grep:
  - **Panel divs:** `id="panel-*"` → **60 unique panels**.
  - **Nav targets:** `onclick="sbNav('*')"` → **62 unique nav call sites** (the nav function is `sbNav()`, not a name assumed going in — confirmed by grep before counting).
- **Live proxy check (real `curl`, not assumed):**
  - `POST https://sairn.vercel.app/api/claude` with `app_id:"stonedesk"` → **HTTP 200**, real Claude response ("Pong! 🏓 How can I help you?", model `claude-sonnet-4-6`). The proxy is live and the `stonedesk` app_id works end-to-end.
  - Same call with `app_id:"sairnbuild"` → **also HTTP 200** — confirms `KNOWN_APP_IDS` in `api/claude.js` does list `sairnbuild` server-side (matches commit `8076517`). This only proves the *allowlist string* is present, not that a SAIRNbuild frontend exists (see §4).
  - `GET https://sairn.vercel.app/sairnbuild` → **HTTP 404**. `GET https://sairn.vercel.app/` → HTTP 200.

## 2. The 10 commits, straight from `git log` (newest first)

1. `5f8b16a` — sairn-guardian-v2: add Check 0d-multi-function — verify nav-trigger status independently for every candidate function on a panel before calling it dormant, straight from the panel-tax catch (taxAddEntry() checked and cleared, taxRender() never checked and was live+fabricating)
2. `bbbc7be` — sairn-guardian-v2 Check 3: split into two checks — app_id present in frontend code vs. app_id actually registered in api/claude.js's KNOWN_APP_IDS. Only the first was covered before; the second is what let 9 of 13 apps silently 400 on their own AI proxy.
3. `5f896b5` — Remove panel-tax's fabricated YTD tax/1099 data; consolidate onto the real taxRender() system
4. `8076517` — api/claude.js: fix KNOWN_APP_IDS allowlist — was missing 9 of 13 live apps (SAIRNscape, SAIRNbuild, SAIRNlaw, SAIRNdesign, SAIRNcare, SAIRNfuneral, SAIRNmechanical, SAIRNhr, SAIRNacc), all getting 400 unrecognized app_id
5. `9330347` — Make schema B canonical for panel-invoices; build its missing create-form and print-modal UI
6. `6207d67` — Add .gitignore (created earlier this session but never actually committed) — protects .claude/settings.local.json and .env.local from accidental commit
7. `68f04dd` — Add sairn-guardian-v2 skill: full content provided directly (26 checks + Check 0's 4 sub-checks, 13-app map, Auto-Fix Protocol with judgment-call logging, mobile-sync/decision-gate push-gate cross-references)
8. `575be72` — Add .claude/settings.json — permissions (reduce approval friction on safe ops) and hooks (auto node --check after edits, block git push to master)
9. `7c2e8a9` — CLAUDE.md: remove stale script-count/known-issues claims, add branch resolution, resolved-issues log, skill pointers
10. `989d1f5` — Fix panel-market: mortgage rate fetch failure silently fell back to hardcoded stale rates

## 3. Skill-set state — verified against the actual files, not the prose that describes them

**Only two skill directories exist in `.claude/skills/` at HEAD:**
- `sairn-guardian-v2/SKILL.md`
- `sairn-infra-debugger/SKILL.md`

That's it. Confirmed with `git ls-tree -r origin/main -- .claude/skills`.

**`sairn-guardian-v2` internal state (real, read directly, 347 lines):**
- Its **frontmatter description** claims 26 checks ("Check 0 ... plus 26 numbered checks per file") and 13 apps — this is the most recently edited part.
- Its **body** still says `## The 25 Checks` and "Platform-wide code quality enforcement for all 11 SAIRN apps" — both stale. The skill's own description brags about catching "drift in its own app map and check count," which is accurate self-diagnosis: the update to 26/13 was only partially propagated. **Check 0 does have four sub-checks** (0a syntax, 0b fabrication + 0b-coverage disclosure, 0c multi-codebase drift, 0d dormant-panel rule + 0d-multi-function) — that part is fully consistent with what was asked to verify.
- **Two color collisions are real and confirmed unresolved**, straight from its own App File Map table (lines 164–184): SAIRNhr and SAIRNvet both `#7C3AED`; SAIRNcare and SAIRNacc both `#0D9488`. The skill explicitly flags this as needing "a real resolution pass" and deliberately does not auto-pick a winner, since it calls that a product decision.

**`sairn-decision-gate`, `sairn-mobile-sync`, `sairn-software-architect` — do NOT exist as skill files.** They are referenced only as prose bullet points in `CLAUDE.md` ("read these, don't just rely on trigger-word matching") and inside `sairn-guardian-v2`'s own description text ("mobile-sync/decision-gate push-gate cross-references"). No `.claude/skills/sairn-decision-gate/`, `sairn-mobile-sync/`, or `sairn-software-architect/` directory exists anywhere in the `origin/main` tree. This is the same failure mode already logged in `CLAUDE.md`'s "Known resolved issues" section for `sairn-app-scaffold`, and in Session 65's own handoff for `sairn-app-scaffold`/`sairn-software-architect` — a skill gets *described* as existing (in a commit message, in another skill's prose, in a session handoff) without an actual file ever being created. **Do not treat these three as available skills until a file actually exists at that path.**

## 4. Broader platform context — could not confirm; flagging rather than repeating

The task brief for this handoff asserted: SAIRNbuild v2.0 built+deployed+recolored to Amber this session, SAIRNdesign started but not finished, and a Cleveland Metroparks RFP #7045 (due 2026-08-11) as a live pursuit blocked on a missing "production, not pilot" example.

None of this is corroborated by the repository:
- **No `sairnbuild.html`, `sairndesign.html`, or any of the other 9 claimed app files exist anywhere in the tree.** `git ls-tree -r origin/main -- '*.html'` returns exactly four files: `stonedesk.html`, `sairnbiz.html`, `sairncode.html`, `sairnvet.html`.
- **`vercel.json`'s build command and routes only cover those same 4 apps** — nothing builds or routes SAIRNbuild, SAIRNdesign, or any other app. `GET /sairnbuild` on the live deployment 404s.
- The 13-app roster (including SAIRNbuild, SAIRNdesign, etc.) exists only as entries in `sairn-guardian-v2`'s App File Map and in `api/claude.js`'s `KNOWN_APP_IDS` allowlist — i.e., planned/allowlisted, not built. `KNOWN_APP_IDS` including `'sairnbuild'` explains why the live-proxy curl above returned 200 for that app_id even though no such app exists — the allowlist is just a string check, not proof of a built frontend.
- **No mention of "Cleveland Metroparks RFP," "RFP 7045," "#7045," or "August 11, 2026" anywhere in the repo.** The only Cleveland Metroparks reference found is a single row of fictional demo data in `sairnvet.html` (a demo patient record, "Cleveland Metroparks Zoo / Amur Leopard"), which is unrelated to a real business RFP.

Given `CLAUDE.md`'s explicit, self-documented history of exactly this kind of claim (false app/skill existence carried forward across handoffs), the honest status is: **this platform/RFP context could not be verified and should not be repeated as fact until confirmed from a source outside this repo** (e.g. directly with the user, or wherever the RFP itself is actually tracked).

## 5. Standing instructions (repo-visible, real)

- Perfection standard / zero-tolerance is real and explicit in `sairn-guardian-v2`'s own description ("Zero bugs shipped").
- Live-verify-after-fix is a real, repeated pattern in the skill text — e.g. Check 3's text: "After any fix here, verify live against the real endpoint... rather than trusting the allowlist edit alone — a passing code review is not the same as a 200 from the actual proxy." This session followed that pattern for the `stonedesk` app_id (§1).
- **0d-multi-function is real** (§3) and directly traces to the `panel-tax` incident in commit `5f8b16a`/`5f896b5`: `taxAddEntry()` was checked and correctly cleared, but `taxRender()` — a second candidate function on the same panel — was never independently checked and turned out to be live and fabricating data. The rule this produced: on any panel with more than one candidate function, every function must be checked independently before the panel can be called dormant.

## 6. Open items

- **`panel-ap`'s re-check status:** no commit, handoff note, or skill-check log in the repo references a pending re-check for `panel-ap` specifically. `panel-ap` does exist (`id="panel-ap"`, `apRender()`, wired to `apMarkPaid`/`apDelete`/`apSetFilter`) and a quick look shows no obvious fabricated-data smell, but this was not run through a full Check 0b pass — treat its status as **unconfirmed, not clean**, until it's actually run.
- **Fabrication sweep:** real and ongoing — `panel-market` (989d1f5), `panel-invoices` (9330347), `panel-tax` (5f896b5), and per Session 65's own log, `panel-executive`, `panel-financial`, `panel-reviews`, `panel-integrations` were fixed in the runup to this session. No evidence the sweep has covered all 60 panels; assume more remain unaudited.
- **The two color collisions** (SAIRNhr/SAIRNvet `#7C3AED`, SAIRNcare/SAIRNacc `#0D9488`) — confirmed unresolved, needs a product decision on which app moves, not a mechanical fix.
- **StoneDesk's real production status:** confirmed live and functioning (118/118 script blocks passing, live proxy returns real Claude output for `app_id:"stonedesk"`). Whether it meets a "production, not pilot" bar for any external audience (RFP or otherwise) is a judgment call outside what this repo can answer — that determination should go through `sairn-decision-gate`'s intended purpose once that skill actually exists as a file, not be asserted here.
