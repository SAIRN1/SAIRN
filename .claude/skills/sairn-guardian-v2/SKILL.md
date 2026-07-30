---
name: sairn-guardian-v2
description: 'The permanent mechanical guardian for ALL 13 SAIRN apps (corrected 2026-07-26 — was listed as 11, missing SAIRNhr and SAIRNacc). Expanded from the original sairn-code-guardian to cover every app in the platform. Trigger this skill automatically on every build session start, every file push, every code review, and every time the user says "check", "scan", "push", "fix", "audit", "is this ready", "before I push", "something broke", "Guardian", "Guardian v2", or "scan all apps". Covers StoneDesk, SAIRNbiz, SAIRNscape, SAIRNcode, SAIRNbuild, SAIRNlaw, SAIRNdesign, SAIRNcare, SAIRNvet, SAIRNfuneral, SAIRNmechanical, SAIRNhr, SAIRNacc. Runs Check 0 (syntax/fabrication/coverage/dormant-code/multi-codebase, four sub-checks) plus 26 numbered checks per file. Zero bugs shipped. This is the skill that catches what human eyes miss — including, as of this update, drift in its own app map and check count.'
---

# SAIRN Guardian v2

Platform-wide code quality enforcement for all 13 SAIRN apps. Mechanical. Automatic. Zero tolerance.

## The 26 Checks

### Architecture (5)
1. **Proxy rule** — every Claude API call goes through sairn.vercel.app/api/claude, never api.anthropic.com directly
2. **Bridge rule** — all cross-app data uses sairn.vercel.app/api/bridge, never rebuilt inline
3. **App ID present** — every API fetch includes app_id matching the file's app
4. **is_demo flag** — every API fetch includes is_demo:true
5. **No service_role key** — Supabase anon key only in browser code

### JavaScript Safety (6)
6. **No Unicode box-drawing chars** — no ─ │ ╔ ═ └ in JS strings (breaks silently)
7. **Regex newlines escaped** — all \n in regex are \\n not literal newlines
8. **No duplicate IDs** — each HTML id= appears exactly once
9. **No undefined functions called** — every onclick/onchange function is defined
10. **No const/let redeclaration** — no variable declared twice in same scope
11. **No APP_ID redeclaration** — platform-wide constants declared once

### Design (5)
12. **No dark backgrounds** — no background:#000, #111, #1a1a1a, #2d2d2d on outer containers
13. **App color correct** — primary color matches app's color system entry
14. **Print-first** — print-color-adjust:exact on colored sections
15. **Light tint backgrounds** — card backgrounds use var(--card) not hardcoded dark values
16. **No inline style="display:none" on panel containers** (added 2026-07-27) — an inline style always beats a class-based CSS rule, so a panel with `style="display:none"` baked into its markup stays hidden even after nav correctly applies an `.active` class. Found on 4 of 61 panels this session, completely inaccessible despite nav dispatch working correctly. Grep for `style="display:none"` or `style="display: none"` on any element that's also a nav target.

### Navigation (3) — NOTE: numbering collides with #16 above, needs renumbering to 17-19 in a future pass
16. **All panels have nav buttons** — every panel-X has a corresponding sb-X sidebar button
17. **All sbNav calls map to panels** — no sbNav('x') call without a panel-x div
18. **Active section logic** — SB_PANEL_SECTION map includes every panel

### Data (3)
19. **localStorage keys namespaced** — all keys start with app prefix (sd_, sb_, sc_, etc.)
20. **sdLoad/sdStore pattern** — localStorage access wrapped in try/catch
21. **No raw JSON.parse without try/catch** — all JSON parsing protected

### Security (2)
22. **No API keys in HTML** — no Anthropic, Stripe, or Supabase keys hardcoded in HTML files
23. **SAIRN_INTERNAL_KEY** — API files check for internal auth header

### Quality (2)
24. **No console.log left in production** — no debug logs in final push
25. **escHtml on all user-generated content** — no raw innerHTML injection of user data

### AI Output Handling (1, added 2026-07-26 — cross-referenced from sairn-decision-gate's NIST AI RMF section)
26. **AI-generated content gets the same escaping discipline as user content.**
    Check 25 already covers user-generated content; Claude's own responses
    rendered into the DOM (chat panels, AI-generated summaries, quote text)
    need the same treatment — an AI response is untrusted output the same way
    user input is, and should never be trusted to be safe markup without
    escaping. This is also the mechanical half of NIST AI RMF's "Measure"
    function (`sairn-decision-gate`): if AI output is rendered directly with
    no sanitization, there's no real control between what the model returns
    and what a user's browser executes.

---

## Check 0 — Run BEFORE the 25 checks, every time, non-negotiable

Added 2026-07-26 after finding SAIRNbiz was entirely non-functional in production
(a parse error broke the whole app's JS) and after finding 14 of ~18 "remaining"
SAIRNvet panels were fully static/fabricated with zero backing logic. Both would
have been caught immediately if this had run first.

**0a. Syntax validity — hard blocks everything else.**
For single-script-block files: extract the inline `<script>` and run `node --check`
on it directly. For multi-script-block files (StoneDesk has 116 separate `<script>`
tags), a naive `grep -c '<script'` count is WRONG — JS string literals inside the
code can contain the literal text `<script`, inflating the count. Use a real
HTML-parser-based extraction (BeautifulSoup or similar) to get each actual script
block, then `node --check` each one independently. Do this even on apps marked
"complete" in a prior handoff — completeness claims are not self-verifying.

**0b. Fabricated KPI / unfounded capability claims — the most common real bug found.**
Before trusting ANY number or badge on a panel, find the `render<n>()`/`get<n>()`
function that's supposed to back it. If none exists, the panel is fully static —
every number on it is fabricated, not just "possibly stale." Also check every
claimed integration (SMS, e-signature, GPS/live-tracking, cloud storage, user
accounts/portals, automated notifications) actually has code behind it somewhere
in the file before letting a KPI imply it exists. Found and removed this session:
"SMS Enabled: Yes" with zero SMS integration anywhere, "892 portal users / 74%
adoption" with no user-account system, "18 specialist network / 88% return rate"
with no referral system, live-GPS/ETA claims with no tracking system. Never
re-fabricate a replacement number — compute it live from real data, or show 0/--.

**0b-coverage. What counts as "done" on a check this size, and disclosing it.**
A true line-by-line manual read of every panel in a 60+ panel, 100+ script-block
file is not realistically completable in one session — pretending otherwise
produces either a session that never ships or a false "fully audited" claim.
The accepted methodology: (1) file-wide keyword sweeps for every named
integration category the app could plausibly claim (SMS, e-signature, GPS,
storage, user-accounts, uptime, security-score, sync, and whatever else is
specific to that app), (2) a full-file scan of every KPI-classed element
(`kpi-val` or equivalent) for hardcoded non-placeholder values, (3) targeted
fixes wherever those sweeps hit. This is real coverage, not a shortcut — but
it is coverage of *patterns*, not a guarantee that every individual panel was
personally read. **State this distinction explicitly at the end of every
Check 0b pass** — which sweeps ran, what they found, and which panels (if any)
were excluded from sweep coverage and why. A session that did this well:
2026-07-26, StoneDesk — disclosed full 118-block/63-panel structural coverage,
full keyword+KPI-element sweep coverage, and explicitly named ~25 dormant
zero-caller panels as not individually re-verified for fabrication content
beyond what the sweeps caught. That disclosure is the standard to match, not
an exception.

**0d. Dormant/orphaned panel rule.**
A panel with zero nav callers (confirmed via nav-panel reconciliation, not
guessed) is dead code — unreachable by any user, so a fabricated KPI inside it
displays to nobody today. That does NOT make it low-priority forever: the
moment someone adds a nav entry pointing to it later, whatever's inside goes
live with zero warning, potentially including fabricated content nobody
re-checked at that point. Two acceptable resolutions, no third option of
"leave it silently sitting there":
  (a) **Delete it.** If there's no near-term plan to wire it up, dead code is
      pure file-size bloat working against the 1MB ceiling — removing it is a
      clean win with no downside.
  (b) **Quarantine it explicitly.** If there's a real reason to keep it (a
      near-term feature), log it by name in the next session handoff doc as
      "known-dormant, NOT audited for fabrication — run full Check 0b on this
      specific panel before adding any nav entry that makes it reachable."
Never let a dormant panel just continue existing unmentioned — that's exactly
how a fabricated-KPI panel goes live undetected months later.

**0d-multi-function. When a panel has more than one candidate function, check
nav-trigger status on EACH one, not just whichever you check first.** Found
2026-07-26 on panel-tax: an earlier dormant-classification pass checked
`taxAddEntry()`'s nav status and stopped there — but `taxRender()`, a
*different* function in the same panel, was the one actually wired to nav and
actually shown to users, and it was the one carrying real fabrication (a
hardcoded 6-month fake sales trend, a fake filing date, three fictional 1099
contractors). Checking only one function's nav status let a live, user-facing
fabricated panel get miscategorized as dormant. The fix: when a panel has an
add/create function and a separate render/display function (a very common
shape — see the invoices schema-consolidation pattern), verify nav-trigger
status independently for each one. A panel is only safely "dormant" if every
function that could plausibly back its visible content has zero nav callers,
not just the first one checked.

**0c. Multi-codebase drift check — do this once per app, first time you touch it.**
Before assuming a single canonical codebase, check whether more than one repo or
deployment target claims to be the same product. Found this session: StoneDesk had
a full separate React/Node/Express/Drizzle app on GitHub (SAIRN1/Fabricor -> Railway)
that was abandoned since June 12 while all real work had moved to a single-HTML file
on a different repo (SAIRN1/SAIRN -> Vercel). Compare commit recency across every
candidate location before trusting which one is "live." Flag and recommend archiving
the abandoned one — don't let it silently rot and confuse a future session.

---

## Known Scope Limitation: Auth-Gated Content (added 2026-07-27)

Guardian v2 and `sairn-adversarial-reviewer` both read source code — neither actually runs the app. For a PIN-gated app like StoneDesk (`#app` stays `display:none` until login succeeds), that means every code-level pass this session, no matter how thorough, never actually saw the authenticated app state — only the login screen and whatever the code implies happens after. The visual-review pass, using Playwright to actually log in, surfaced 4 completely inaccessible panels and a permanent full-page overlay that no code-level check ever caught, because none of them ever got past the PIN screen. **A clean Guardian/adversarial-review pass on an auth-gated app is not the same claim as "the real app works" — it's "the code looks right assuming the gate opens correctly." Always run `sairn-visual-review` (or an equivalent real-login test) at least once per major change, not just code-level checks, on anything auth-gated.**

## App File Map

**Corrected 2026-07-26** — this table was missing SAIRNhr and SAIRNacc despite
Check 0a's own text already naming SAIRNhr as a large file needing raw.
githubusercontent.com treatment. An app referenced elsewhere in this same skill
but absent from its own map is exactly the kind of internal drift Check 0c
warns against applied to this skill itself — fixed, not left inconsistent.

| App | File | Color | App ID |
|-----|------|-------|--------|
| StoneDesk | stonedesk.html | #16C762 | stonedesk |
| SAIRNbiz | sairnbiz.html | #14B8A6 | sairnbiz |
| SAIRNscape | sairnscape.html | #22C55E | sairnscape |
| SAIRNcode | sairncode.html | #F87171 | sairncode |
| SAIRNbuild | sairnbuild.html | #F59E0B | sairnbuild |
| SAIRNlaw | sairnlaw.html | #15803D | sairnlaw |
| SAIRNdesign | sairndesign.html | #6366F1 | sairndesign |
| SAIRNcare | sairncare.html | #0D9488 | sairncare |
| SAIRNvet | sairnvet.html | #7C3AED | sairnvet |
| SAIRNfuneral | sairnfuneral.html | #6B7280 | sairnfuneral |
| SAIRNmechanical | sairnmechanical.html | #84CC16 | sairnmechanical |
| SAIRNhr | hr.html | #7C3AED | sairnhr |
| SAIRNacc | sairnaccounting.html | #0D9488 | sairnacc |

Note the color collisions in this corrected table: SAIRNhr and SAIRNvet both
show #7C3AED, and SAIRNcare and SAIRNacc both show #0D9488. This needs a real
resolution pass the next time either pair is touched — flagging here rather
than silently picking one, since guessing which app should move is a product
decision, not a mechanical one this skill should make unilaterally.

---

## Scan Procedure

**CORRECTED 2026-07-26:** The Contents API silently fails on files over ~1MB — it
returns HTTP 200 with an empty/null `content` field, no error. This was discovered
against stonedesk.html (2,049,441 bytes) which decoded to 0 bytes with zero warning.
Any file this size or larger (StoneDesk, SAIRNvet, SAIRNhr, likely others) MUST use
raw.githubusercontent.com instead — the opposite of what this skill said before today.

```bash
# For files under ~1MB: Contents API is fine
curl -H "Authorization: token PAT" \
  "https://api.github.com/repos/SAIRN1/SAIRN/contents/FILENAME" \
  | python3 -c "import sys,json,base64; d=json.load(sys.stdin); open('file.html','wb').write(base64.b64decode(d['content'].replace('\n','')))"

# For files over ~1MB (check size first via the Contents API response's 'size' field,
# or just default to this path for stonedesk.html/sairnvet.html/any file that's grown large):
curl -s "https://raw.githubusercontent.com/SAIRN1/SAIRN/main/FILENAME" -o file.html
wc -c file.html   # sanity check — if this is suspiciously small, something's still wrong
```

Always verify the downloaded size roughly matches the size reported by a directory
listing (`/repos/SAIRN1/SAIRN/contents/` on the parent dir) before trusting the file.

```bash
# Run checks
grep -n "api.anthropic.com" file.html          # Check 1 — should be 0 results
grep -n "app_id" file.html | wc -l             # Check 3 — should be >0
grep -n "is_demo" file.html | wc -l            # Check 4 — should be >0
grep -n "service_role" file.html               # Check 5 — should be 0 results
python3 -c "
import re
with open('file.html') as f: content = f.read()
# Check for Unicode box chars
box_chars = '─│╔╗╚╝═║╠╣╦╩╬'
for ch in box_chars:
    if ch in content:
        lines = [i+1 for i,l in enumerate(content.split('\n')) if ch in l]
        print(f'FAIL: Unicode box char {repr(ch)} found at lines {lines[:5]}')
# Check duplicate IDs
ids = re.findall(r'id=[\"\\']([^\"\\']+)[\"\\']', content)
from collections import Counter
dupes = [id for id,count in Counter(ids).items() if count > 1]
if dupes: print(f'FAIL: Duplicate IDs: {dupes[:10]}')
print('Checks complete')
"
```

---

## Auto-Fix Protocol

When a check fails:
1. Log the exact line number and issue
2. Apply the fix programmatically (str_replace or sed)
3. Re-run the check to confirm fix
4. Log "FIXED: [check name] at line [N]"
5. Continue to next check
6. Push only when all 25+1 checks pass

**For judgment calls, not mechanical fixes** (delete-vs-quarantine on a
dormant panel, which of two colliding app colors to change, whether a file's
grown large enough to need splitting per `sairn-software-architect`'s size
ceiling) — log the reasoning at the time, not just the action taken, the same
way `session-stack`'s Decision Log now does. A judgment call that used the
best information available is a good log entry regardless of how it plays
out later; recording only the mechanical "did X" loses the "why," which is
the part a future session actually needs when re-evaluating whether that call
still holds.

## Push Only When Clean

Guardian v2 blocks the push if any of these fail:
- Check 1 (direct API call)
- Check 5 (service_role key)
- Check 8 (duplicate IDs)
- Check 22 (API keys in HTML)
- Check 25 (unescaped user content)
- Check 26 (unescaped AI-generated content)

All others are warnings that must be fixed but don't hard-block if minor.

**After pushing a fix, live-verify that specific thing against the deployed
site — not a full-site scan, just what changed.** Added 2026-07-26, following
a real success: Claude Code curled the live production proxy with a real
app_id and got a real response back, confirming a fix worked in production,
not just in source. All 26 checks + Check 0 passing is necessary but not
sufficient — a panel can pass every mechanical check and still be broken in a
way that only shows up against the real deployed site (a timeout, a wiring
error only triggered by real browser conditions, a route that 404s). Claude
Code has real network access to the live domain that this chat's sandboxed
bash_tool does not (see `sairn-software-architect`'s tool-completeness
section) — use it, scoped narrowly: after fixing panel-X, check panel-X's
actual live behavior, not the whole site. This is a targeted spot-check tied
to what just changed, not a standing background monitor — running it
constantly would slow real work down for no added confidence beyond the
first check.

**Automated deploy-mismatch check, added 2026-07-29:** a `PostToolUse` hook
(`tools/deploy_verify_notify.py`, wired in `.claude/settings.json`, filtered
to `git push*`) now runs automatically after every push — waits ~60s, hashes
`stonedesk.html` at `HEAD` against a fresh curl of `sairn.vercel.app/
stonedesk`, and surfaces a mismatch (via `asyncRewake`) if the live site
still doesn't match. Built after a real incident this session where Vercel's
GitHub webhook silently didn't fire for a push; a trivial re-trigger commit
fixed it. Notify-only by design — it never commits or pushes anything
itself, that decision was asked and answered explicitly. This automates
catching *"did the deploy even happen"*, not *"does the feature actually
work"* — the manual targeted spot-check above is still required for that;
the hook is a mechanical safety net underneath it, not a replacement for it.

**Before pushing anything that touches mobile/bridge event code**, confirm it
matches `sairn-mobile-sync`'s standard event shape (`app_id`, `event_type`,
`source_device`, `timestamp`, `payload`) rather than a one-off shape invented
for that app — a bridge event that doesn't match the standard shape breaks
the office-side polling pattern silently, since nothing hard-errors on an
unexpected payload shape, it just fails to render.

**Before pushing anything that will be described as "complete," "production,"
or "live" to someone outside the team** (a customer, a proposal, a status
update), run `sairn-decision-gate`'s Premortem: assume that specific claim
gets challenged and found false — what would the challenger find? Guardian's
25+1 checks catch code-level defects; they don't automatically catch a true-
but-misleading status claim (all checks passing on a feature nobody has
actually used yet is not the same as that feature being "production").

---

## Exhaustive Root-Cause Diagnosis (added 2026-07-26, real recurring failure)

When troubleshooting a live problem, list EVERY candidate cause matching
the exact symptom before concluding — not the first plausible one. This
failed twice tonight, both traced back to stopping too early:

- **Output-style not activating:** the first check (does the settings key
  exist, is it valid JSON) said yes — correct, but incomplete. It took
  several escalating rounds to reach the real cause (a stale local git
  checkout that never fetched the fix). The right first pass would have
  checked: does the key exist AND is this session's working directory
  actually current with origin, in the same pass.
- **A hook error citing "PreToolUse:Bash" specifically:** the first
  response checked the redaction hook (matcher: Write|Edit) — a real,
  relevant candidate, but the WRONG one; the error explicitly named the
  Bash-matched hook (the git-push-master guard), which went unchecked
  in the same pass because a plausible-looking answer arrived first.

**The rule:** before reporting a root cause, enumerate every hook/setting/
config file that could produce the exact observed symptom (matching the
specific event name, matcher, or error text — not just "something in this
category"), check each one, THEN report. A diagnosis that turns out
incomplete isn't a minor miss — it costs another full round-trip, and on
a metered session, that round-trip has a real dollar cost.

## Eliminate Duplication at the Source (added 2026-07-26 — the deeper pattern)

Exhaustive diagnosis (above) is reactive — it helps once something's already
broken. The actual recurring root cause tonight, across several unrelated-
looking incidents, was the same shape every time: **the same kind of
information existing in two places with nothing forcing them to match.**
User-level settings.json vs. project-level settings.json (both the output-
style bug and the hook-duplication bug). Four separate git checkouts on one
machine. Two competing handoff-naming conventions before one was resolved.

**The standing rule:** whenever a second copy of something is discovered
(a second settings file, a second checkout, a second naming convention, a
second implementation of the same tool), that discovery itself is the
finding — don't just patch the immediate symptom, resolve which copy is
authoritative and eliminate or clearly quarantine the other, the same day
it's found. A structural duplication left "for now" is exactly what
produces the next surprising bug in a different disguise.

**Applied now:** project-level `.claude/settings.json` should be the single
authoritative source for hooks/permissions going forward. The user-level
file should be reduced to the bare minimum (outputStyle only, or empty) —
not left as a second place hooks can independently exist. This is worth
doing now, not deferred.

## Session Start Protocol

At the start of every build session:
1. **Verify which branch is actually live.** Do not trust a prior session's note
   about which branch is "stale" — that claim can itself go stale. Check the repo's
   `default_branch` setting directly (`GET /repos/SAIRN1/SAIRN`) and compare HEAD
   commits on both `master` and `main` (`GET /git/refs/heads/{branch}`). Found
   2026-07-25: an earlier handoff said "main is stale, don't use" — by the next day
   the opposite was true; every real fix for two days had landed on `main` while
   `master` fell behind. The default branch (verified: `main`) is what Vercel deploys
   from — confirm this in the Vercel dashboard's Production Branch setting too if
   there's ever doubt, since a repo default and a Vercel project setting can disagree.
2. Pull current SHA for all files being modified
3. Run Guardian v2 (Check 0 first, then the 25) on each file before making any changes
4. Log baseline findings
5. Fix any pre-existing issues before adding new code
6. Run Guardian v2 again before every push

This ensures we never ship degraded code and we always know the baseline health of every file.

---

## Safe-Editing Rules (added 2026-07-26, after real near-misses)

1. **Anchor insertions on a line that will never itself be edited.** A `var x = null;`
   declaration is a bad anchor — if a later edit touches nearby text and the anchor
   line gets swept into `old_str` without being reproduced in `new_str`, it silently
   disappears. Anchor on something structurally stable instead, like a function
   declaration line that appears exactly once and is never itself modified (e.g.
   `function getCogginsTests(){`). After any insertion near a `var`/`const`/`let`
   declaration, re-grep for that declaration immediately to confirm it survived.
2. **Never copy-adapt an old buggy pattern while fixing it elsewhere in the same file.**
   A quote-collision bug was fixed in one place and accidentally reintroduced in two
   new locations by adapting the original (buggy) code as a starting template instead
   of the corrected version. `node --check` after every single edit is what catches
   this — not a final check at the end of a session.
3. **Never use a bash heredoc to write a multi-megabyte file that contains emoji or
   other multi-byte Unicode.** A heredoc write of this kind truncated a 2MB file to
   1.7KB with no error this session — caught immediately by re-checking file size
   after write, but it could have destroyed hours of work. Use `create_file`/
   `str_replace` tool calls or a Python-based write for large files instead.
4. **If a spoken/voice-transcribed instruction names something ambiguous** (e.g. "Claude
   code" could mean the Claude Code tool or the SAIRNcode app), pause and ask in one
   line rather than guessing and burning a chunk of session on the wrong target.
5. **After every single edit, not just at the end of a session:** re-run `node --check`,
   `div_balance_check.py`, and `nav_panel_check.py`. Catching a break immediately is
   cheap; finding it three edits later means tracing back through all of them.

---

## Cross-Session Handoff Protocol

Chat/session context does not persist reliably across long sessions or tool switches
(this chat interface vs. Claude Code are separate contexts entirely). The fix that's
worked: **every significant session ends by writing/updating a `SAIRN-SESSION-N-
HANDOFF.md` file directly in the repo** — not just relying on chat memory or summaries.
Every new session (in either tool) reads the latest handoff doc FIRST, before touching
any code, and independently re-verifies its claims against GitHub rather than trusting
them at face value (branch HEAD, file sizes, "complete" claims — all of it). A handoff
doc that turns out to be wrong about something (like the master/main branch claim
above) should be treated as a normal, expected occurrence to re-verify against, not
a failure — state changes between sessions and the doc can't always keep up.
