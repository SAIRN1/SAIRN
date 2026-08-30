---
name: sairn-guardian-v2
description: 'The permanent mechanical guardian for ALL 16 SAIRN apps (corrected 2026-08-13 — SAIRNhr and SAIRNacc removed, they were speculative planning-table entries, not real or needed apps; corrected again 2026-08-19 — SAIRNcash and SAIRNgrounds added, both real live deployed apps missing from this map despite substantial work already done on each; see App File Map). Expanded from the original sairn-code-guardian to cover every app in the platform. Trigger this skill automatically on every build session start, every file push, every code review, and every time the user says "check", "scan", "push", "fix", "audit", "is this ready", "before I push", "something broke", "Guardian", "Guardian v2", or "scan all apps". Covers StoneDesk, SAIRNbiz, SAIRNscape, SAIRNcode, SAIRNbuild, SAIRNlaw, SAIRNdesign, SAIRNcare, SAIRNvet, SAIRNlegacy, SAIRNmechanical, SAIRNcash, SAIRNgrounds, SAIRNdental, SAIRNroofing, SAIRNsenior — count corrected 2026-08-30 from 13 to 16, and DERIVED rather than counted by hand: run `python tools/sairn_app_map_check.py --live`, which diffs this file's App File Map against git ls-files, vercel.json and a live request per route. Do not trust this sentence's number either — the tool is the source that moves when an app is added. Runs Check 0 (syntax/fabrication/coverage/dormant-code/multi-codebase, four sub-checks) plus 31 numbered checks per file. Zero bugs shipped. This is the skill that catches what human eyes miss — including, as of this update, drift in its own app map and check count.'
---

# SAIRN Guardian v2

Platform-wide code quality enforcement for all 13 SAIRN apps. Mechanical. Automatic. Zero tolerance.

## The 31 Checks

### Architecture (5)
1. **Proxy rule** — every Claude API call goes through sairn.vercel.app/api/claude, never api.anthropic.com directly.
   **FALSE-POSITIVE WARNING, added 2026-08-25.** The mechanical form of this
   check (`grep -n "api.anthropic.com"` … "should be 0 results") is wrong as
   written and was firing on clean code. In stonedesk.html the 2 hits are a
   **guard** (`if (url.includes('api.anthropic.com'))`) and a comment — i.e.
   the enforcement of this rule, not a violation of it. **Read every hit before
   calling it a failure.** A hit is a real violation only if it is the URL an
   actual request is sent to (`fetch`/`XMLHttpRequest`/axios target, or a
   base-URL constant). Guards, comments, and error strings pass.
2. **Bridge rule — CORRECTED 2026-08-24. "The SAIRN Bridge" means TWO
   DIFFERENT THINGS in this codebase, and this rule named the wrong one.**
   Before citing "the Bridge" anywhere, say which:

   - **`api/sd-data.js` shared resources** — the REAL, working cross-app
     data path, used by 10 apps. Resources like `employees` and
     `shared_knowledge` are license-scoped, session-gated, and genuinely
     read by other apps. This is what SAIRNsenior and SAIRNcare shipped
     under the name "SAIRN Data Bridge" ("reads the employee roster from
     SAIRNbiz via the existing generic 'employees' resource — zero new
     server code"). **This is what a new app should use for cross-app data.**

   - **`api/bridge.js`** — a separate, much smaller StoneDesk-only
     endpoint with three actions. `proxy_get` is a CORS relay to allowlisted
     external hosts (FRED etc.) and is genuinely useful and in use. `push`
     upserts a `{shopId, jobs, invoices, employees}` snapshot into
     `bridge_data`. `pull` reads it back — and **has zero callers across
     all 13 app files**, verified 2026-08-24, so `bridge_data` is written
     and never read. `push` also requires **no Authorization header at
     all**, deliberately, because its live callers send none: anyone can
     write to any `shop_id`. That is defensible for shop metadata a shop
     pushes about itself and is NOT defensible for personal or financial
     data, which bounds what this endpoint can ever safely carry.

   The old wording — "all cross-app data uses sairn.vercel.app/api/bridge,
   never rebuilt inline" — is what caused the conflation, and pointed new
   work at the endpoint with no read side rather than the one that works.
   It also made `api/bridge.js` look more built than it is: two of its three
   StoneDesk push callers were dead code with zero callers (deleted
   2026-08-24), and the one live caller wrote to a table nothing reads while
   the UI claimed a completed sync.

   **The rule, restated:** cross-app data goes through `api/sd-data.js`'s
   shared resources. Do not rebuild that inline. `api/bridge.js` is for the
   external-host CORS relay; do not add new consumers of its `push`/`pull`
   without first building a real read side and deciding whether it should
   authenticate.
3. **App ID present** — every API fetch includes app_id matching the file's app
4. **is_demo flag** — every API fetch includes is_demo:true
5. **No service_role key** — Supabase anon key only in browser code

### JavaScript Safety (7)
6. **No Unicode box-drawing chars** — no ─ │ ╔ ═ └ in JS strings (breaks silently).
   **FALSE-POSITIVE WARNING, added 2026-08-25.** The rule says *in JS strings*
   but the mechanical scan below greps the **whole file**, so it fires on
   comments and HTML text too. In stonedesk.html all 4 U+2500 hits are in
   comments, and Check 0a parses 128/128 blocks clean — proof they do not break
   anything. **A hit is a failure only if the character sits inside a JS string
   literal.** If 0a passes, a box-char hit in a comment is not a finding.
7. **Regex newlines escaped** — all \n in regex are \\n not literal newlines
8. **No duplicate IDs** — each HTML id= appears exactly once
9. **No undefined functions called** — every onclick/onchange function is defined
10. **No const/let redeclaration** — no variable declared twice in same scope
11. **No APP_ID redeclaration** — platform-wide constants declared once
31. **A function must never mutate a parameter and then forward `arguments`
    under `'use strict'`. The mutation is silently discarded.** (added
    2026-08-30)

    **The incident.** Six `window.fetch` patches in `stonedesk.html` all had
    this shape:

        opts = Object.assign({}, opts, { body: JSON.stringify(body) });
        return _orig.apply(this, arguments);

    Under `'use strict'` the arguments object is **not** linked to the
    parameters, so reassigning `opts` never reached the wrapped fetch. **Three
    of the six were on live features and every one had been doing nothing since
    it shipped** — Session Memory ("the AI stops forgetting what it told you two
    questions ago" reached zero requests), Tone & Style (the
    Simple/Detailed/Formal/Casual/Expert setting never affected a response), and
    the personalization / shared-knowledge / employee-profile injector. No
    error, no failed request, nothing wrong on screen.

    **Why no prior check caught it, and why this one is different.** The code
    reads correctly, so review misses it. Nothing renders wrong, so
    `sairn-visual-review` misses it. It is valid JavaScript, so Check 0a passes
    it. **This class is only provable by execution** — the same reason the
    rendered-DOM assertion lives in the visual pass rather than in a static
    scanner. Do not reason about it from the spec; run it.

    **The trap that hides it.** The functions carry **no `'use strict'` of their
    own** — they inherit it from an enclosing IIFE dozens of lines above. Read
    in isolation the function looks fine. So strictness must be judged at
    **block** level, not function level; a function-level check finds nothing.

    **Mechanical check — two tools, run both:**

        python tools/sairn_strict_args_check.py        # find candidate sites
        node   tools/strict_args_harness.js            # prove the behaviour

    The scanner reports sites; the harness is the standing proof that the engine
    really behaves this way (4 strictness cases + the real three-injector chain:
    forwarding via `apply` delivers **0** layers, via `call` delivers **3**).
    Both are reconciled against a true positive rather than only ever having
    returned clean — the scanner was run against a probe file containing one real
    instance, one non-strict block (correctly ignored, since `arguments` *is*
    linked there) and one block whose comment quotes the old code (correctly
    ignored).

    **The fix is to forward explicitly:** `return _orig.call(this, url, opts);`

    **Do not "fix" a forward that has nothing to forward.** A pass-through that
    never mutates its parameters is correct as `apply(this, arguments)` and is
    *better* that way, because it preserves extra arguments. Two such forwards
    were deliberately left in place in `stonedesk.html` (`:2115` Layer 1
    allowlist, `:19132` Smart Retry's non-Claude branch).

    **Known false positive, seen in the wild:** the scanner matches the text
    `.apply(this, arguments)` and the fix commit for the original six added an
    explanatory comment *quoting the old line*. The re-scan flagged it. The tool
    now strips comments before matching, but read every hit before believing it.

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

### Security (2 — one live, one retired)
22. **No API keys in HTML** — no Anthropic, Stripe, or Supabase keys hardcoded in HTML files
23. ~~**SAIRN_INTERNAL_KEY** — API files check for internal auth header~~
    **RETIRED 2026-08-23. Do not run this check; do not report it as failing.**
    A Guardian pass on SAIRNlaw scored 0 for every one of its four API files
    and went looking for the gap. There is no gap: `grep -rl
    "SAIRN_INTERNAL_KEY\|INTERNAL_KEY" api/` returns **zero files across the
    entire platform**. **Zero code reads it.** That is the accurate claim, and
    it is the one the retirement rests on.
    **Wording corrected 2026-08-25.** This paragraph previously read "the
    mechanism this check describes does not exist anywhere and has not for some
    time." That is a stronger claim than the evidence supports, and it is
    false: `SAIRN_INTERNAL_KEY` **is real and provisioned**, present in the
    Vercel project on both Production and Preview (~67 days before this
    correction), confirmed by `vercel env ls production --project sairn`, which
    prints names only and no values. So the variable exists and nothing reads
    it — two different facts, and the difference is not pedantic. An
    unread-but-provisioned secret is live configuration to retire deliberately,
    not evidence a mechanism was never built; a session acting on the old
    wording would conclude there was nothing to clean up. Same class as every
    other claim-vs-reality drift this file already documents against itself —
    the grep was over `api/`, and a grep of code can only ever prove something
    about code.
    **What actually gates the API surface**, and what to check instead, is
    Check 28: a license key as `Authorization: Bearer`, plus
    `verifySessionToken(token, license_hash, expectedApp)` with the third
    argument present. That is strictly stronger than a single shared internal
    header — a shared secret proves the caller is inside the platform, while
    the session token proves *which app and which employee*, which is the
    property the 2026-08-03 cross-app collision incident actually needed.
    Retiring rather than deleting, so a future session that finds this number
    missing does not "restore" a check against a mechanism that was never
    replaced because it was superseded. Security is therefore **one** live
    check (22) plus 28; the section header keeps its count for numbering
    stability, the same disclosure convention as the 16/16 and 27/26
    collisions already flagged elsewhere in this file.

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

### Non-functional buttons (1, added 2026-07-30 — numbered 27, not 26, since
26 above already exists; noted here rather than silently colliding with it
the same way the Navigation section's own 16/16 collision is already
flagged below as a known open item)
27. **sairn_dead_button_audit.py clean** — run tools/sairn_dead_button_audit.py
    against every app file before declaring it done. Catches: handler
    targets with no definition (Section A), inline handlers whose only
    action is a toast (Section B), toast-only function bodies split by
    caller count — C1 = has callers = live button, wire up or relabel;
    C2 = zero callers = orphan, delete (these are OPPOSITE fixes, never
    guess, always check the caller list first) — and same-scope
    duplicate definitions (D1; D2 is cross-scope and informational
    only). The tool strips comments via a real state machine, not a
    regex — a naive `/\*.*?\*/` blanks strings/URLs/regex-literals too
    and produces false "never defined" findings (cost 58 phantom
    findings on StoneDesk before this was fixed). Section E (bare
    "placeholder" text scan) was cut after going 0-for-7 real findings;
    the phrase-list scan (`coming next build`, `TODO`, etc.) stays —
    it's 6-true/1-false and catches real fabricated-honesty gaps.

### Environment-variable name drift (1, added 2026-08-24 — numbered 30,
continuing the same disclosure pattern rather than renumbering)

30. **Every `process.env.X` read must name a variable that actually exists in
    the Vercel project. Check the Resend sender pair specifically — it is the
    one that has already cost months.**

    **The incident, twice.** `api/alf-alerts.js` (SAIRNcare) and
    `api/sairndental/send-reminder.js` both read `RESEND_FROM_ADDRESS`. **That
    variable has never existed in this project.** The sender has been
    configured as **`RESEND_FROM_EMAIL`** since 2026-06-19, alongside
    `RESEND_API_KEY`, on both Production and Preview.

    Consequence: each file's env-completeness guard failed on *every* firing
    since it shipped. SAIRNdental's reminder cron **never sent a single
    reminder** — a 500 in the production log every hour, for months, from a
    feature everyone believed was working.

    **The mechanical check.** Run against every `api/**/*.js`:

    ```bash
    grep -rn "RESEND_FROM_ADDRESS" api/          # must return ZERO code hits
    grep -rn "process\.env\.RESEND" api/         # every hit must be
                                                 # RESEND_API_KEY or RESEND_FROM_EMAIL
    ```

    Both known instances are fixed as of 2026-08-24, each with its own
    regression test (`api/sairndental/send-reminder.test.js`,
    `tests/sairncare/test-alf-alerts-endpoint.js`). This check is therefore
    **preventive** — it exists so a third app does not reintroduce it, which is
    exactly how the second one happened: the design doc for SAIRNdental's email
    reminders specifies `RESEND_FROM_ADDRESS` throughout, so anyone building
    from that doc will write the wrong name again.
    **Comment mentions are fine and expected — the check is on `process.env`
    reads, not on prose.**

    **The general rule this is an instance of.** A misnamed env var does not
    fail loudly; it reads as *undefined*, and an
    `if (!process.env.X) return 500` guard then reports it as a *missing
    secret*. So the symptom points at infrastructure while the cause is a typo
    in code, and a previous session spent real time hunting for a
    `RESEND_API_KEY` that was present and correct the whole time. Before
    concluding any env var is "not set in Vercel", **grep the code for the name
    first and confirm it matches what is actually configured** — `vercel env ls
    production` is the authority, not the design doc and not the guard's own
    error message.

    **Two things that make this class findable rather than lucky:**
    - **Name only the variable that is actually missing.** Both files
      originally listed all four unconditionally, which is precisely what made
      a typo look like an absent secret. Build the missing list by filtering.
    - **A new env var is a two-place change** — the code read and the Vercel
      project — and only one of them is in the diff. Same shape as Check 29's
      *two files, one change, one updated*.

### Storage-validator changes need a real load, not unit tests (1, added
2026-08-24 — numbered 29, continuing the same disclosure pattern as 27/26
and 28/27 rather than silently renumbering)

29. **Any change that touches a storage validator, a schema constraint, or the
    shape of what gets persisted MUST be proven with a real write against the
    real endpoint. Unit tests that call the compute/business function directly
    do not exercise the storage layer at all, and will pass while the write
    path is broken.**

    **The incident, 2026-08-24, SAIRNlaw.** California's service extensions
    needed a new shape: the amount depends on the service method, so the rule
    row carries no `add` and the standard supplies `amount(method)` instead.
    `api/_lib/deadline-engine.js` was taught that shape. Its validator, in the
    separate file `api/legal-deadlines.js`, was not — it still required `add`
    unconditionally.

    **84 of 84 isolation tests passed the whole time.** They call
    `computeDeadline()` directly and never touch the storage validator, so
    every one of them was green while all seven California civil rows were
    unstorable. The real load found it immediately and precisely:

    ```
    400 INVALID_RULE  "service_extension.add must be a number of days."
    ```

    The tests were not weak. They were *aimed at the wrong layer* — and the
    green bar made that invisible, which is the part worth remembering. High
    unit coverage on one side of a two-file change reads exactly like coverage
    of the whole change.

    **The mechanical check.** When a diff touches any of these:
    - a validator or schema-guard function (`validateRule`, `validate*Payload`,
      anything that returns `INVALID_*` before a write),
    - a SQL `CHECK`, `unique`, `not null` or column type,
    - the shape of a payload that gets stored (a new/removed/renamed field, a
      field becoming optional, a value moving from the row to a shared table),

    then before the change is called done:
    1. **Perform a real write** through the real endpoint against the real
       store — `add_rule`, `add_holidays`, a real booking, whatever the
       production path is. Not a mock. Not the function in isolation.
    2. **Read it back** and confirm the stored value is what you sent.
    3. **Try the boundary in both directions** — one payload that must be
       accepted and one that must be rejected, and check the rejection carries
       the right code rather than a generic 500.
    4. If the change RELAXES a bound, confirm the previously-rejected payload
       now lands; if it TIGHTENS one, confirm the previously-accepted payload
       is now refused *with a clear message*, and say so in the commit, because
       that is a behaviour change someone downstream may be relying on.

    **Two files, one change, one updated is the shape to watch for.** Engine
    and validator, client cap and DB constraint, seed file and migration. Ask
    explicitly: *what else has to agree with this for the write to succeed?*
    Then check that thing rather than assuming it followed.

    **A derived constraint needs a drift tripwire.** Where a stored bound is
    computed from a code constant — as `dnt_appointments`' size ceiling is
    derived from `MAX_PHOTOS_PAYLOAD_BYTES` — add a test asserting the
    relationship, so raising one without the other fails loudly instead of
    surfacing later as real users losing real data.

### Cross-app identifier collisions (1, added 2026-08-03 — numbered 28, not
27, since 27 above already exists; same known-collision-disclosure pattern
as the Navigation section's 16/16 and the Non-functional-buttons section's
27/26 above, not silently overwritten)
28. **Anywhere a role name, table name, or token/credential value is shared
    across more than one SAIRN app, verify it's explicitly scoped — not
    just "the value happens to match."** Found building StoneDesk's
    per-employee RBAC: `api/sd-data.js`'s employees WRITE branch trusted a
    client-supplied `body.app_id==='sairnbiz'` string with zero
    verification (any bearer of a shop's license key could set that field).
    The real fix (`api/_lib/auth.js`'s `verifySessionToken(token,
    license_hash, expectedApp)`) still shipped with the SAME bug class
    twice more in the same session: `api/sd-auth.js`'s `setup` action and
    `api/sd-data.js`'s employees READ gate both called `verifySessionToken`
    *without* the `expectedApp` argument — since `'owner'` is a valid role
    in both StoneDesk's and SAIRNbiz's role vocabularies, a valid SAIRNbiz
    owner token could have silently passed StoneDesk-only checks. Caught
    only by manual self-review before push, not by any automated check —
    hence this entry, plus the companion Semgrep rule
    (`.semgrep/verify-session-token-app-scope.yml`) that now blocks any
    `verifySessionToken($TOKEN, $HASH)` call missing the third argument.
    **Mechanical check:** grep every cross-app-shared table/role/constant
    name for each call site that reads or checks it, and confirm each site
    also checks an app-scoping value (an `app_id`/`expectedApp`/equivalent
    parameter that's cryptographically or structurally tied to a specific
    app) — not just that the shared name/value matched. A value shared
    across apps without an explicit scope check is a collision waiting to
    be found by an attacker instead of a review.

---

## Check 0 — Run BEFORE the 31 checks, every time, non-negotiable

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

**0e. Pre-build duplication check — run BEFORE any CREATE TABLE or new API
route/handler, not after.**
Added 2026-08-01 after a real near-miss: a new `bridge_pushes` table and its
migration were fully designed and built for `api/bridge.js` before anyone
checked whether existing Supabase infrastructure already covered the same
need. It did — a `bridge_data` table, already provisioned, was discovered
only by accident (a PostgREST error hint on the *new* table happened to
name it: `"Perhaps you meant the table 'public.bridge_data'"`). Had that
hint not fired, `bridge_pushes` would have shipped as a second, redundant
table with nothing ever forcing anyone to notice the overlap — exactly the
"second copy of something" pattern already flagged in *Eliminate
Duplication at the Source* below, just caught one step earlier than usual
(before ship, not after).

**The rule:** before running any `CREATE TABLE` or writing a new API
route/handler function, search first:
- **Existing tables:** grep any known schema files (`sql/*.sql`) AND, where
  reachable, the live Supabase schema itself for a table name or column
  shape that already serves the same purpose. A hint in a failed-query
  error message (like the one that caught this) is a real signal, not
  noise — always follow it up before dismissing it.
- **Existing API routes:** grep `api/*.js` for a handler that already talks
  to the resource in question, or a URL the frontend already calls that
  might just need a route built behind it (that's exactly what
  `api/bridge.js` itself was — a URL every caller assumed already existed).
- **Existing code call sites:** grep app HTML files for the literal name
  under consideration (e.g. `bridge_data`, `bridge_pushes`) — zero hits
  doesn't prove the *table* doesn't exist, but it does prove nothing in the
  live apps is already using the *new* name you're about to create, which
  is itself worth knowing before you commit to it.

Only proceed to `CREATE TABLE` / a new handler once this search comes back
genuinely empty. If something close-but-not-exact turns up, that's a
judgment call (reuse with a shape change vs. build new) — log the
reasoning per the Auto-Fix Protocol's judgment-call rule below, the same
way the `bridge_data` vs. `bridge_pushes` decision itself was logged.

---

## Known Scope Limitation: Auth-Gated Content (added 2026-07-27)

Guardian v2 and `sairn-adversarial-reviewer` both read source code — neither actually runs the app. For a PIN-gated app like StoneDesk (`#app` stays `display:none` until login succeeds), that means every code-level pass this session, no matter how thorough, never actually saw the authenticated app state — only the login screen and whatever the code implies happens after. The visual-review pass, using Playwright to actually log in, surfaced 4 completely inaccessible panels and a permanent full-page overlay that no code-level check ever caught, because none of them ever got past the PIN screen. **A clean Guardian/adversarial-review pass on an auth-gated app is not the same claim as "the real app works" — it's "the code looks right assuming the gate opens correctly." Always run `sairn-visual-review` (or an equivalent real-login test) at least once per major change, not just code-level checks, on anything auth-gated.**

## App File Map

**Corrected 2026-07-26** — this table was missing SAIRNhr and SAIRNacc despite
Check 0a's own text already naming SAIRNhr as a large file needing raw.
githubusercontent.com treatment. An app referenced elsewhere in this same skill
but absent from its own map is exactly the kind of internal drift Check 0c
warns against applied to this skill itself — fixed, not left inconsistent.

**Corrected again 2026-08-09** — the same drift class recurred: this table
still listed a planned `SAIRNfuneral -> sairnfuneral.html` placeholder row
while the real funeral-home-operations app had already been built, fully
treated (`sairn-parallel-app-scaling`'s Portfolio Audit Status table), and
deployed live under a different name, `SAIRNlegacy -> sairnlegacy.html`
(confirmed via the file's own `<title>` and `git ls-tree` — no
`sairnfuneral.html` exists anywhere in the repo). Renamed the row rather
than adding a new one; the color (`#6B7280`) carries over since it was
never actually in use and doesn't collide with anything else in the table.
Full-inventory lesson: a real, live, deployed app can go undetected in this
table indefinitely if nothing ever cross-checks the map against `git
ls-tree` — the map is a claim about the repo, not derived from it, so it
drifts exactly like any other unverified claim in this skill set.

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
| SAIRNlegacy | sairnlegacy.html | #6B7280 | sairnlegacy |
| SAIRNmechanical | sairnmechanical.html | #84CC16 | sairnmechanical |
| SAIRNcash | sairncash.html | #7C6FFF | sairncash |
| SAIRNgrounds | sairngrounds.html | #16A34A | sairngrounds |
| SAIRNdental | sairndental.html | #0EA5E9 | sairndental |
| SAIRNroofing | sairnroofing.html | #C2410C | sairnroofing |
| SAIRNsenior | sairnsenior.html | #DB2777 | sairnsenior |

**Corrected 2026-08-30, the SIXTH correction, and this time the map is DERIVED
rather than argued.** Added **SAIRNdental**, **SAIRNroofing** and **SAIRNsenior**
— three real, tracked, routed apps, all returning **200 live**, all absent from
this table. This is the identical failure to 2026-08-19 (SAIRNcash, SAIRNgrounds)
repeating eleven days later, which is the argument for a tool rather than another
promise to be careful.

`tools/sairn_app_map_check.py` now derives the verifiable half from three
sources — `git ls-files`, `vercel.json`, and a live HTTP request per route — and
diffs them against this table. It **does not rewrite the table**: brand colour
and `app_id` are real decisions that cannot be derived, and a regenerator would
destroy them. It reports drift and exits non-zero. Run it before trusting any
"all apps" claim, including this file's own description.

Colour and `app_id` for the three new rows were read out of each app's own
source (`--brand`/`--p` custom property and the `APP_ID` constant), not assigned.
**Two pre-existing colour collisions stand and are not resolved here** —
`#0D9488` and `#7C6FFF`/`#7C3AED` are near-neighbours flagged in earlier
corrections; re-theming a live app is a product decision, not a map fix.

**Header count note:** this file's own description says "ALL 13 SAIRN apps" and
lists 13 by name. **There are 16.** The description is now wrong in the same way
the table was, and is left as evidence rather than silently patched — a count
carried in prose is exactly the thing the tool exists to replace.

**Corrected 2026-08-13** — removed the planned `SAIRNhr -> hr.html` and
`SAIRNacc -> sairnaccounting.html` rows entirely. Neither is a real or
needed app; both were speculative planning-table entries with no file ever
built and no product decision behind them, unlike SAIRNcare (above, in the
table), which is a real, needed future app (extended-care facilities) just
not yet built. Removing the two rows also resolves the previously-flagged
SAIRNcare/SAIRNacc `#0D9488` color collision by elimination — SAIRNcare's
`#0D9488` is now unique in this table, confirmed against every other row
above. If SAIRNhr or SAIRNacc becomes a real planned app later, treat that
as a fresh addition with its own color decision, not a restoration of
these rows.

**CORRECTED AGAIN 2026-08-30 — SAIRNmechanical IS now a live app, and the
2026-08-27 correction below is itself superseded.** `bb9dbb3
feat(sairnmechanical): recover the app from an unmerged branch, with real auth
first` landed the file on `main` on **2026-08-28**; `vercel.json` routes it; and
`https://sairn.vercel.app/sairnmechanical` returns **200**, re-verified
2026-08-30 by curling every app route. The map row above is restored.

**The 2026-08-27 correction is kept below rather than deleted**, because it is
the reason the recovery happened and because this table has now been wrong about
this one app in *both* directions — first asserting a live app that did not
exist, then asserting a missing app that had been recovered. **That is the
argument for deriving the row (`git ls-files` + a live curl) rather than reading
it.** The 2026-08-30 sweep found all 19 app routes returning 200.

**Superseded — corrected 2026-08-27 — SAIRNmechanical is NOT a live app and its
file has never been on `main`.** The row above claimed `sairnmechanical.html`; that file
does not exist in `main`'s tree, is on disk in no clone, and `vercel.json`
carries no route for it. `https://sairn.vercel.app/sairnmechanical` returns
**404**, correctly — there is nothing to serve.

The file is real and finished (84 KB, "16 pages, dispatch+agreements") but lives
**only on the unmerged branch `origin/claude/lucid-ptolemy-b73vu0`**, added
2026-06-14 (`c12e8b1`) and last touched 2026-06-19 (`77979be`). Three real fixes
to it are stranded there too, including `eb4a17e` — a cross-script-tag
`APP_ID`/`PROXY` redeclaration that was *a hard SyntaxError in real browsers,
crashing the whole page at parse time*. **That is the commit Guardian Check 13
came from.** The check survived; the app it was found on did not.

**Do not treat this row as coverage.** Every Guardian pass that reported "all 13
apps" was reporting on twelve. Found 2026-08-27 by curling every app route
during a click-through audit — nothing in this file or any prior pass had ever
checked that the mapped filenames exist, which is the same *"the map is a claim
about the repo, not derived from it"* failure this table has now corrected four
times about itself. **Derive it: `git ls-files | grep -i <app>` before trusting
any row here.**

Recovery is a separate, authorised task and is not a merge — an 84 KB file last
touched in June predates this platform's auth, grant-sweep and
silent-failure discipline entirely, so it needs a real review pass, not a
cherry-pick and a route.

**Corrected 2026-08-19** — added SAIRNcash and SAIRNgrounds, both real,
live, deployed apps with substantial work already done this session (a
full Firebase real-auth sync build on SAIRNcash; an agentic-follow-up tool
on SAIRNgrounds) that were entirely absent from this table despite that.
Found independently, not from any list, during a skill-inventory ground-
truth check (comparing this file's user-level and project-level copies) --
the map is a claim about the repo, not derived from it, so it drifts
exactly like this file's own prior corrections already warned it would.
Colors pulled from each app's own real CSS (SAIRNcash's `--glow`,
SAIRNgrounds' `--p` root variable), not invented — SAIRNcash's `#7C6FFF`
is visually close to (but not identical to, so not a strict collision by
this table's own hex-match definition) SAIRNvet's `#7C3AED`; SAIRNgrounds'
`#16A34A` is likewise close to but distinct from SAIRNscape's `#22C55E`.
Flagging the near-similarity rather than silently re-theming either real
app to avoid it -- this table's job is to reflect the real deployed color,
not to guarantee visual distinctness after the fact.

---

## Scan Procedure

**CORRECTED 2026-07-26:** The Contents API silently fails on files over ~1MB — it
returns HTTP 200 with an empty/null `content` field, no error. This was discovered
against stonedesk.html (2,049,441 bytes) which decoded to 0 bytes with zero warning.
Any file this size or larger (StoneDesk, SAIRNvet, likely others) MUST use
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
grep -n "api.anthropic.com" file.html          # Check 1 — READ EVERY HIT, do not
                                               # assume 0. Guards (if url.includes(...))
                                               # and comments are the rule being enforced,
                                               # not broken. Fail only on a real request target.
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
        # REVIEW, not FAIL — this greps the whole file but Check 6 is about JS
        # STRINGS. Open each line: only a box char inside a string literal fails.
        # In comments/HTML text it is fine, and a passing Check 0a proves it parses.
        print(f'REVIEW: Unicode box char {repr(ch)} found at lines {lines[:5]}')
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
6. Push only when all 27+1 checks pass

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
- Check 28 (cross-app identifier collision, added 2026-08-03) — same
  severity class as 22/25/26: an unscoped shared role/table/token check is
  an auth bypass waiting to be found, not a style nit.
- `vercel.json` config check (see below) — a `buildCommand` over Vercel's
  256-char schema limit doesn't just fail loudly, it takes the whole
  production site down while looking like nothing happened.

All others are warnings that must be fixed but don't hard-block if minor.

**`vercel.json` config check, added 2026-07-30 after a real incident.**
Adding one more app's `cp` line to `buildCommand` pushed it from 296 chars
over Vercel's 256-char schema ceiling. The deploy failed (state `ERROR`),
but Vercel's default behavior on a failed production deploy is to keep
serving the *last successful* build rather than erroring the site —
so every push after that point (several StoneDesk mobile fixes, a
SAIRNbuild fix) reported a clean commit and a clean local Guardian pass,
while production silently stayed on old code. It was only caught because
a post-push spot-check queried the Vercel API directly instead of trusting
`git push`'s own success. Run `python tools/vercel_config_check.py` before
every push that touches `vercel.json` — it checks `buildCommand` length
against the 256-char limit and cross-checks every route's destination
file actually appears in `buildCommand` (the Iron Law's file/route
pairing, checked mechanically instead of just by convention).

**After pushing a fix, live-verify that specific thing against the deployed
site — not a full-site scan, just what changed.** Added 2026-07-26, following
a real success: Claude Code curled the live production proxy with a real
app_id and got a real response back, confirming a fix worked in production,
not just in source. All 27 checks + Check 0 passing is necessary but not
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

**A CLEANUP, MIGRATION OR PUSH IS NOT DONE WHEN THE COMMAND EXITS CLEAN. It is
done when the destination is queried back. Added 2026-08-26 after two
independent failures the same night; widened 2026-08-27 to cover pushes after
two more.**

**The push case, added 2026-08-27.** The paragraph above already required
live-verifying a *fix* after a *push* — but it assumed the push itself landed.
Twice in one night it had not, and both times the report was given in good
faith:

- **A push to a brand-new remote reported as succeeded, byte-identical, all
  files present.** `GET /repos/<owner>/<repo>/commits` returned
  **409 `Git Repository is empty`**, zero branches, and `pushed_at` identical
  to `created_at` — GitHub stamping repo creation, not a push. Every file
  404'd on `main` and `master`.
- **The same push reported as fixed and landed a second time.** Same three
  queries, same empty result, `pushed_at` unchanged from the previous check.
  Root cause was a Windows credential-manager collision between two GitHub
  accounts plus a `cp` that never ran — neither visible from the pushing end.

**Why a push hides this better than a cleanup does.** `git push` to the wrong
remote, or from a directory that was never populated, can exit 0. A credential
manager can serve a *different* account's token and fail in a way that scrolls
past. And unlike a migration, there is no obvious downstream symptom — the
repo simply stays empty while everyone believes it is live.

**The rule for pushes:**

1. **Query the remote, not the command.** For GitHub:
   `GET /repos/<owner>/<repo>/commits` → the expected SHA must be there.
   `409 Git Repository is empty` and an empty `/branches` array are the two
   signals that catch a total non-arrival.
2. **`pushed_at == created_at` means nothing has ever been pushed.** It is the
   single cheapest tell and it is not obvious.
3. **Fetch a real file over `raw.githubusercontent.com` and compare bytes** —
   not just an HTTP 200 on the repo. Normalise line endings before calling a
   hash mismatch a content mismatch: a Windows checkout adds one CR per line,
   so a file with 239 lines differs by exactly 239 bytes for a completely
   benign reason.
4. **When a push targets a NEW remote or a different account**, check
   `git remote -v` and `git status -sb` *before* believing the push, and expect
   the credential helper to offer the wrong identity. On Windows,
   `git config credential.https://github.com.username <account>` or
   `git -c credential.helper= push` bypasses the cached one.
5. **"Pushed" is a claim about a command. "Present on the remote" is a fact.**
   Report the second, and say which query produced it.

The paragraph above covers verifying a *fix* after a *push*. It says nothing
about verifying a *cleanup* or a *migration* after a *run*, and that gap bit
twice on 2026-08-26:

- **`sairncash_waitlist`.** The table was created and reported provisioned.
  Every public signup then returned 502 for hours. The create had landed; the
  `grant` had not been exercised in the way the code needed (the endpoint used
  `ON CONFLICT DO UPDATE`, which requires UPDATE privilege at PLAN time, and
  the grant was `select, insert`). A privilege check that asked only "is
  INSERT present?" came back clean.
- **The SAIRNroofing damage-verification cleanup.** Reported run and clean.
  Both `rf_claims` rows and the `rf_jobs` row were still live — the
  multi-statement paste had applied only partway. **The Supabase SQL editor
  returns success for the statements it did run.** A partial apply is
  indistinguishable from a full one from the outside.

**Why this is its own rule and not covered by anything above.** Nothing in the
round trip surfaces it. The editor reports success. The session that wrote the
file has no DB access to check. And "confirmed run" from a human is a true
statement *about the paste*, not about what landed. So the failure is silent in
exactly the way `sairn-silent-failure-sweep` describes, wearing a different
disguise — and both times, the thing that caught it was a query, not a report.

**The rule, mechanically:**

1. **Every cleanup or migration file ends with a per-statement confirm query**,
   with the expected answer written next to it —
   `select count(*) from public.x where id = 'Y';  -- expect 0`. One per
   statement, not one for the file: a single count at the end cannot tell a
   full apply from a partial one.
2. **Ask for those counts back.** Do not accept "it ran." The counts are the
   evidence; the confirmation is not.
3. **Where an API path exists, prefer the live endpoint over a re-select** —
   it proves the *app* can see the change, which a `select` as owner does not.
   `sairncash_waitlist` re-selected fine as owner the whole time it was 502ing
   for every real user.
4. **A grant check must name the verbs the CODE calls**, not just the ones the
   schema file granted. Read the endpoint first: `merge-duplicates` means
   `ON CONFLICT DO UPDATE` means UPDATE is required even when no conflict ever
   occurs. See `sairn-grant-sweep` for the sweep discipline; this is the
   opposite direction — a grant that is MISSING relative to what the code does.
5. **Do not report a cleanup or migration as closed on the strength of the run
   alone**, in a handoff, an index row, or to a human. Say which query you ran
   and what it returned, the same standard the Verification Discipline section
   of `CLAUDE.md` already applies to migrations — extended here to deletes,
   which had no rule at all.

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
27+1 checks catch code-level defects; they don't automatically catch a true-
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

Before declaring any app "not built" or "doesn't exist," check local
disk (e.g. `dir /s /b appname.html` under the user's Downloads/project
folders) in addition to GitHub and Vercel. sairnscape.html was
genuinely absent from the repo and from Vercel, but existed locally
across ~24 old snapshot folders, never pushed — GitHub-only checking
would have wrongly logged it as a ground-up rebuild. When multiple
local candidates exist, don't assume the newest-numbered or
"FINAL"-labeled folder wins — diff them. A file explicitly named
"FINAL" can still be the regressed copy (a botched find-replace can
corrupt a later snapshot); check node --check / div-balance on every
candidate before trusting the name.

## Known Environment Limitations

Some tools silently no-op instead of failing loudly, which is worse
than an outright error because it produces false confidence. Document
each one here as it's found, with the working alternative:

- **resize_window** (browser viewport resize in this sandboxed
  environment): reports success but does not actually change
  `window.innerWidth` or affect `matchMedia()` — media queries never
  evaluate. Confirmed via `innerWidth` staying at the desktop value
  after a reported-successful resize to 390px. Do not use for any
  mobile/responsive verification claim.
  **Working alternative:** a headless browser tool with real device
  emulation (Playwright/Puppeteer viewport emulation), or a real
  device/BrowserStack-style check. Verify the alternative actually
  moves `innerWidth` before trusting any result from it.
- **document.body.style.width** as a stand-in for viewport width: sets
  layout width but does NOT change the viewport, so CSS media queries
  still evaluate against the real (desktop) viewport. Structural
  findings gathered this way can still be valid (a fixed-px element
  overflowing is true at any width) but never claim "verified at
  390px" from this method alone.

When a tool in this list is the only option available, report the
limitation explicitly in the handoff rather than upgrading a partial
check to "verified."

## Verify Aggregate Stats Before Reporting Them

A summary number like "0-for-7 false positives" can silently combine
two different measurements with opposite records — e.g. one sub-check
that's 6-true/1-false and another that's 0-true/7-false average out
to "0-for-7," which reads as "this whole check is useless" when really
only one half of it is. Before reporting or acting on an aggregate
finding (a total count, a pass rate, a "clean" summary line), break it
down by what actually composes it. This applies to Guardian's own
summary lines too — "checkblocks 119/119" is fine to report as-is
because it's one homogeneous check, but a combined score across
different check types should be reported per-type, not just as one
number.

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

## Verification Discipline — six lessons from 2026-08-21/22 (three parallel sessions)

Every one of these came from a real failure or near-failure caught during the
SAIRNcode gap-closure arc, the SAIRNlaw deadline engine, and StoneDesk Phase 1.
They are listed here rather than left in transcripts because each one is a
repeatable check, not a war story.

**1. Seed-and-recheck: distinguish an honest empty state from a real defect.**
Independently arrived at by all three sessions the same night. When a gate,
panel or lookup returns "nothing here," that is ambiguous — it can mean the
feature works and the store is genuinely empty, or it can mean the feature is
broken. **Do not report either without seeding one real record and re-running.**
StoneDesk's PC/TC-equivalent case: SAIRNcode's `sc_pctc` gate returned "not in
your reference" on every code, which looked like a defect and was not — seeding
two rows flipped it to correct answers immediately. The same method proved the
opposite on StoneDesk's Slabs panel, where an empty store was rendering
fabricated inventory. One method, both verdicts.

**2. Verify against the most specific marker, not any string that matches.**
A live-verification grep for a KX colour fix returned a hit and looked like
confirmation. The hit was a *different, pre-existing* code path that happened to
contain the same substring; the actual change had not deployed yet. **Grep for
something that exists only in the change you just made** — a new function name,
a distinctive comment fragment — never a generic pattern the file already
contained. A false green here is worse than no check, because it stops you
looking.

**3. Fail-closed in the wrong direction is still wrong.**
Every gate on this platform is built to fail closed, and that is right — but
"closed" has a direction. SAIRNcode's DMEPOS Standard Written Order gate was
briefed as requiring seven elements. CMS's own policy article A55426 lists
**six**; the commonly repeated seventh ("start date") is not required. A
seven-element gate would have demanded a field CMS never asked for and
**blocked compliant orders**. Strictness is not automatically safety. Verify the
threshold itself against a primary source, not just the direction of the guard.

**4. Check the diff SHAPE before committing, not just that syntax passes.**
`git add <shared file>` in a tree where other sessions are working can sweep in
work that is not yours. This happened: a commit intended to add one array entry
to `api/sd-data.js` landed **88 insertions**, 87 of them another session's
uncommitted handler branch, and was pushed before anyone noticed. `node --check`
passed the whole time — syntax was never the problem. **Always run
`git diff --cached --numstat` (or `--stat`) and confirm the line counts match
what you meant to change, before `git commit`.** If the number surprises you,
stop.

**5. This repo has mixed line endings, file-by-file. `sed -i` is unsafe here.**
`api/sd-data.js` is CRLF; `sairncare.html` is LF; `stonedesk.html` is CRLF.
There is no single convention to rely on. An in-place stream edit that
normalises line endings rewrites every line of a 2MB file, producing a diff
that is impossible to review and that can mask a real change inside 34,000
lines of noise. **Detect the file's existing ending first** (`b'\r\n' in data`)
and preserve it explicitly — a Python read/modify/write in binary mode is the
safe pattern. Verify after writing: `CRLF count` and `bare LF count` should
match what the file started with.

**6. A panel that falls back to seed data when its real store is empty is a
fabricated-KPI risk, not a display convenience.**
This is Check 0b, but the fallback form is easy to miss because the code looks
defensive rather than dishonest. **Primary example, StoneDesk's Slabs panel,
2026-08-22:** its backing key `sd_slab_tracker` was absent, so `load()` fell
through to an in-file `SEED` constant and rendered **8 invented slabs**,
computing all four KPIs from them — Total 8 / Available 5 / Allocated 2 /
Inventory Value **$4,420**, every figure fabricated — while a genuinely real,
server-synced slab written through Bulk Slab Upload was invisible and excluded
from every count. The panel did not show *stale* data. It **invented** data
when its real store was empty, and then did arithmetic on the invention.

A `demoCleared()`-style guard is **not sufficient on its own**. StoneDesk had
exactly such a guard and this still happened, because the guard only suppresses
seeds once a user has explicitly cleared demo data — a user who never did, on a
panel whose real store is empty, sees invented records presented as real stock.

**What to check, per site:** *can this panel's real store be empty while the
demo-cleared flag is false, and does the panel compute any number from what it
renders?* Where both are true, it is the same defect. The fix is to delete the
seed fallback outright and render an honest empty state — **not** to put the
seed behind another flag, which leaves the same landmine one boolean away.

**Sized, not estimated — and this is a platform-wide pattern, not one panel:**
`stonedesk.html` contains **29 `SEED` constants** and **56
`sdDemoCleared() ? [] : SEED` fallback sites**. Only the Slabs panel has been
fixed (Phase 1a, `501d15b`). Most of the remaining 28 are probably behaving as
intended — but "probably" is what the Slabs panel was, right up until someone
actually looked.

> **OPEN FOLLOW-ON TASK, not yet done:** audit the other 28 `SEED` sites in
> `stonedesk.html` against the two-part test above, and then check whether
> other SAIRN apps carry the same fallback shape. Find it the way this one was
> found — by reaching each panel with a genuinely empty real store and looking
> at what renders — not by assuming the guard holds because it held once you
> looked. StoneDesk is unlikely to be the only app with this shape.

---

## Cross-Session Handoff Protocol

Chat/session context does not persist reliably across long sessions or tool switches
(this chat interface vs. Claude Code are separate contexts entirely). The fix that's
worked: **every significant session ends by writing a handoff file directly in the
repo** — not just relying on chat memory or summaries. Every new session (in either
tool) reads the latest handoff doc FIRST, before touching any code, and independently
re-verifies its claims against GitHub rather than trusting them at face value (branch
HEAD, file sizes, "complete" claims — all of it). A handoff doc that turns out to be
wrong about something (like the master/main branch claim above) should be treated as a
normal, expected occurrence to re-verify against, not a failure — state changes between
sessions and the doc can't always keep up.

**Naming and lookup — CORRECTED 2026-08-23.** This section previously said to write
`SAIRN-SESSION-N-HANDOFF.md` and, by implication, to find the latest one by its number.
Both are now wrong:

- **Write `APP-YYYY-MM-DD-subject-handoff.md`** (e.g. `SAIRNLAW-2026-08-23-lemaj-handoff.md`).
- **Find the latest by DATE, then confirm the subject matches the task you were given** —
  never by taking the highest `N`.
- **A handoff is not written until it is committed in the same action**, inside a real
  clone. A local-only handoff is invisible to every other clone and can block its next pull.

The counter failed in production: two different real `SAIRNLAW-SESSION6-HANDOFF.md` files
existed simultaneously (trust-disbursement 2026-08-18, LeMAJ 2026-08-23) and a fresh
session read the wrong one. Neither session was wrong — a counter cannot stay unique
across concurrent sessions in separate clones. Older files keep their existing names, so
both patterns are on disk; that is expected, not drift. `sairn-session-handoff` carries
the full convention and the reasoning; this pointer exists because that skill and this one
disagreed for several hours after the change, which is the exact same
claim-in-two-places drift Check 0c and the "Eliminate Duplication at the Source" section
below already warn about — applied, again, to this file itself.
