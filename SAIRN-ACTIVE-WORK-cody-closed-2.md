# SAIRN Active Work -- Cody: ARCHIVE part 2 of 2

Split out of `SAIRN-ACTIVE-WORK-cody.md` on **2026-10-20** (cody, batch
b30 item 3), which was 795,238 bytes against a 400,000-byte ceiling.
`python tools/tooling_inventory.py --standing-doc-sizes` had been listing
it and exiting 1 since b28; b29's handoff section 4.7 recorded it as
owed and said the remedy was a decision about where the cut goes.

**WHERE THE CUT WENT, AND WHY IT IS NOT ARBITRARY.** This log has TWO
formats in it. The oldest 88 entries are bullets in the original format
(425,249 bytes); the newer 127 are `## <date> (Cody) -- <subject>`
sections (369,862 bytes). The bullets are archived here and the sections
stay in the live file -- which is the right size split AND the right
editorial one, because the recent work is what a fresh session needs.

**TWO EARLIER ATTEMPTS REFUSED, AND THE SECOND FOUND THAT STRUCTURE.**
The first tried one archive part and refused: no single cut leaves both
files under the ceiling -- fourth hit the identical wall on 2026-10-12.
The second treated everything before the first `## ` as a document header
and refused on "not even one section fits the live file", because that
"header" was 425,249 bytes. A script that had guessed instead of refusing
would have written a live file still over the ceiling and reported
success.

**THIS IS AN ARCHIVE, NOT A SUMMARY.** Every entry below is the original
text, moved whole, in its original append order. Nothing was rewritten,
shortened or merged.

**THE MOVE IS PROVEN, NOT ASSUMED.** The sha256 of the sorted multiset of
entry texts was taken before the split and re-taken over the UNION of all
3 files afterwards, from disk, and the write only happened because they
matched -- so no entry was lost, none duplicated and none silently
edited. **Byte counts would not have been enough:** two files that sum to
the original size can still have lost one entry and gained a copy of
another. Same verification fourth recorded for its own split.

**If an entry here turns out to be live, MOVE it back rather than copying
it.** Two homes for one entry is the drift this platform keeps paying for.

Range: bullet entries 80-88 of 88.
First: `- docs/2026-09-05-anon-amplification-limiter-scoping.md (Cody, 2026-09-05) -- **SCOPING ONLY`
Last:  `- sql/dead_bare_tables_evidence_2026-09-05.sql + docs/SAIRN-OPEN-WORK-INDEX.md (Cody, 2026-0`

---

- docs/2026-09-05-anon-amplification-limiter-scoping.md (Cody, 2026-09-05) -- **SCOPING ONLY, nothing built. The real rate-limiting fix for the unauthenticated licence lookup. Skills used: `sairn-decision-gate` (Premortem), `sairn-software-architect`.**

  **RECOMMENDATION: the WAF rate-limit rule AND `checkRateLimit()`, in that order, and DELETE the in-memory Map.** The rule is the fix -- it is the only option that stops the request before it reaches compute or the database, so it REMOVES the amplification where the other two only bound it, and it is global by construction so scale-out cannot defeat it. `checkRateLimit()` from `@vercel/firewall` is the precision layer that buys back what the rule costs.

  **THE COST OF THE RULE IS THE PART THAT MATTERS AND I AM NOT BURYING IT: a WAF rule matches on REQUEST attributes only, so it cannot know whether the licence turned out valid, and it therefore counts real customers.** That is exactly the load-bearing property Fourth's design had -- only FAILED validations counted, so a valid key accumulated nothing and it could never refuse a working customer. `checkRateLimit()` restores it: same platform-global counter, but called only on the failed-validation path, keyed by address. One substitution -- a global counter for a per-instance `Map` -- fixes the measured defect without redesigning the intent.

  **CONFIRMED, not assumed:** team plan is `pro`, so WAF custom rules with the `rate_limit` action are available. Window 10-3600s, 1-10,000,000 requests, keys `ip`/`ja4`/`header:<name>`, `fixed_window` or `token_bucket`, action `rate_limit|deny|challenge|log`. `package.json` already exists so a dependency is routine.

  **A THIRD OPTION REJECTED ON THE RECORD** rather than left to be re-proposed: fusing the limiter into the licence lookup as one Postgres RPC (the `sairn_ai_rate_limit_consume` advisory-lock pattern). One round trip, globally exact, no new vendor -- but it does not reduce database load AT ALL, every request still contacts Postgres, so it bounds what an attacker achieves rather than what the platform pays. And it puts rate-limit state inside `api/_lib/license.js`, the "single source of truth -- do NOT fork this" module every app authenticates through. Worst blast radius for the least benefit.

  **PREMORTEM SURFACED THE SEQUENCING, which is the real output.** The rule ships in `log` action first for a full week, with the ceiling set from MEASURED traffic rather than a guess -- because "the WAF refused a real practice" is the most likely failure and the app cannot even explain a 429 that comes from an origin it does not control. And `tools/waf_rule_check.py` ships in the SAME pass as the rule, not after: dashboard config is invisible to git, so a disabled rule is **the `anon-rate-limit` failure repeating one layer up** -- a protection nobody verifies is not a protection.

  **THE ACCEPTANCE TEST IS THE PROBE THAT EXPOSED THE LAST ONE** -- 40 concurrent junk-token requests must produce observed 429s. Not "the rule is configured". That distinction is the whole reason the previous limiter was inert for a day while looking fine.

  **FOUR THINGS I COULD NOT VERIFY FROM HERE and named as unknowns rather than assumed:** whether WAF-mitigated requests are billed or count as invocations (the doc corpus does not say, and it changes the headline benefit); the project's current firewall config (no Vercel API token in this environment); real per-IP traffic volume, which is the GATING unknown because the ceiling cannot be chosen without it; and whether `checkRateLimit()` adds a per-invocation network call. **If the observed anonymous volume turns out trivial, the honest recommendation may shrink to "the rule in log mode plus the checker" -- and that is a legitimate outcome of scoping, not a failure of it.** 2026-09-05
- tools/waf_rule_check.py + tools/waf_rules_expected.json + tests/run_waf_rule_check_probe.py + docs/SAIRN-OPEN-WORK-INDEX.md (Cody, 2026-09-05) -- **THE LOG-MODE WAF RULES ARE LIVE ON PRODUCTION, and the checker shipped in the same pass. Observation window runs to 2026-09-12. Skills used: `sairn-decision-gate`, `sairn-software-architect`.**

  **PUBLISHED, not staged:** `anon-api-observe-100` and `anon-api-observe-600` -- both `rate_limit` on path prefix `/api/`, keyed by `ip`, `fixed_window`, 60s, **`action: log`** on exceed. **TWO thresholds on purpose: one threshold for a week yields one bit of information, two yield a distribution.** 100/60s is set deliberately LOW because the question is *how often would a plausible enforce ceiling have fired, and on whom* -- a threshold nothing ever crosses teaches nothing.

  **I VERIFIED LIVE THAT IT DOES NOT BLOCK RATHER THAN TRUSTING THE FLAG.** 130 concurrent requests well over the 100/60s threshold against production: **130 x 401, zero 429s.** The CLI prints a generic "legitimate traffic may be throttled" warning on any rate-limit rule, and reading that warning and reasoning about it is not the same as measuring it.

  **THE PROJECT HAD NO CUSTOM FIREWALL RULES AT ALL BEFORE THIS** -- read off the live config. That closes one of the scoping document's four named unknowns by measurement instead of research, which is also what Michael's "don't wait on a token, the log-mode deploy IS the measurement" call bought.

  **THE CHECKER SHIPPED IN THE SAME PASS AND THE ORDERING IS THE WHOLE POINT.** Dashboard config is invisible to `git log`, so a rule somebody disables in March is **the `anon-rate-limit` failure repeating one layer up** -- and that one looked like protection for a full day while being measured completely inert. `tools/waf_rules_expected.json` is the declared intent in git. The checker diffs live against it AND separately refuses any on-exceed action other than `log` **against a constant in the tool, not against the spec** -- so flipping the rule to blocking and editing the spec to agree still trips a loud, distinct failure. That case is asserted, and asserted to be the ONLY problem raised, so I know the per-field comparison was genuinely satisfied rather than passing by accident.

  **15/15 in `tests/run_waf_rule_check_probe.py`, and it is a real negative-control suite, not decoration** -- deleted rule, disabled rule, re-scoped path, changed limit, changed window, changed key, disabled firewall, undeclared extra rule, and the spec-edit-to-deny case each go red, with a clean baseline first so the negatives prove something.

  **COULD-NOT-TELL EXITS 2, WHICH IS NOT A PASS, and its FIRST RUN proved that by failing correctly.** An unquoted CLI argument on Windows made `vercel` read the config path as a deploy target; the tool reported UNVERIFIED rather than green. That is the one thing that went right about the bug, and it is the standard the seed gate's loud note already set.

  **DELIBERATELY NOT WIRED INTO THE PUSH GATE, stated as a decision rather than left as an omission.** It needs a network round trip and Vercel credentials, and a hook running unattended in four clones is precisely what this repo has been bitten by twice (the `git checkout origin/main` hook that staged files, found only by a stray `git status`). Run it by hand while the window is open; decide on wiring when the rule goes to enforce and actually protects something. 2026-09-05
- docs/SAIRN-OPEN-WORK-INDEX.md (Cody, 2026-09-05) -- **AUDIT of the 26 handlers with NO AUTH BOUNDARY. ONE REAL FINDING, confirmed live: `api/claude.js` is an open Anthropic proxy. Skill used: `owasp-security`.**

  **This closes a question my own tooling raised and nobody had answered.** `tools/preauth_oracle_check.py` reports 26 handlers where neither `validateLicenseKey` nor `verifySessionToken` appears at all, and its header says explicitly that *"no boundary found" and "nothing above the boundary" are different answers and only one of them is good news* -- so those had to be read, not assumed public.

  **`api/claude.js`: no credential of any kind.** POST to `https://sairn.vercel.app/api/claude` with **no `Authorization` header**, `is_demo:false`, `max_tokens:1` returned **HTTP 200 and a real `claude-sonnet-4-6` completion.** Proven live with deliberately minimal spend -- this was to establish reachability, not to use it. A second probe with `max_tokens:64000` also returned 200, so the value reaches Anthropic unmodified. The only gates are POST-only, an `app_id` from a fixed allowlist, and a non-empty `messages` array -- **and every app's `app_id` and the proxy URL are both in its own downloadable client JS.**

  **THE `is_demo` FLAG IS THE ATTACKER'S TO SET, which is the part that turns a known design into a hole.** Both cost controls live INSIDE `if (is_demo)`: the in-memory counter and the Supabase `checkAiRateLimit()`. Sending `is_demo:false` skips both. And on the `true` path the Supabase limiter ships in OBSERVE mode and fails open, so it would not have refused anything either.

  **I ALMOST REPORTED A SECOND FINDING THAT WAS NOT ONE.** I first read the comment *"server-capped below regardless of what the client sends"* as a false claim about `max_tokens`. Re-reading the surrounding block, it is about tool **`max_uses`**, and it is TRUE -- `MAX_TOOL_USES_CEILING` really does clamp it. **The file's own comment also states the missing auth out loud** (*"this endpoint has no other auth beyond a client-supplied app_id"*), so this is a KNOWN DESIGN that was reasoned about when the server-tool allowlist was added. What that reasoning does NOT cover is the `is_demo` bypass and the genuinely uncapped `max_tokens`. Reporting the comment as a lie would have been wrong and would have buried the two things that are real.

  **WHY I DID NOT JUST FIX IT: all 17 apps call this proxy with `headers: { 'Content-Type': 'application/json' }` and nothing else.** Requiring a bearer licence key breaks every one until each is updated, and some AI surfaces may be reachable before a licence is entered. That is a platform-wide design decision, not a one-file edit. The cheaper half -- capping `max_tokens` server-side and moving the limiter OUT of the `is_demo` branch so a client cannot opt out -- changes no caller and could ship immediately.

  **THE OTHER 25 WERE READ AND ARE NOT THIS.** `api/sd-agent.js` is properly gated through `store.validateAndGate(licenseKey)` -- **a THIRD instance of the detector's bespoke-boundary limitation**, after `dnt-bi`'s feed token and `alf-alerts`'s cron secret, and not a defect. `public-book.js` is public by design and its rate limiter fails CLOSED. The rest reach only this platform's own database. **None of the other 25 reaches a metered third-party spend with no credential.**

  **A note on my own index edit:** the row I wrote was malformed on first write -- `max_tokens || 1000` inside a code span is TWO unescaped column separators, and `md_table_check.py` caught it. The never-split-a-row rule exists for editing; this is the same trap from the WRITING side, and the checker caught it because it runs per table rather than per file. 2026-09-05
- api/claude.js + api/claude-cost-controls.test.js + docs/2026-09-05-claude-proxy-auth-rollout.md (Cody, 2026-09-05) -- **INTERIM FIX SHIPPED AND LIVE-VERIFIED (`8fe970a9`); PHASE 1 OF THE FULL FIX SHIPPED (`209e9802`, observe mode). BOTH FLAGGED FOR INDEPENDENT REVIEW. Phases 2-4 blocked on two decisions. Skills used: `owasp-security`, `sairn-software-architect`, `sairn-decision-gate`.**

  **INTERIM, non-breaking, no caller changed.** `max_tokens` now clamped to 4096 in `callAnthropic()` -- **measured not guessed**: the largest any app sends is 2000 and `sd-agent.js` uses 4096, so nothing legitimate is refused. **The cap is in `callAnthropic()` rather than the HTTP handler on purpose**: `law-auth.js:596` and `sc-ai.js:259` both pass a client-supplied `body.max_tokens` through it, so capping the handler alone would have fixed the copy that is easiest to see and left two others open -- this repo's own standing lesson. **LIVE-VERIFIED on production: a request asking 64000 returned `stop_reason: max_tokens`, `output_tokens: 4096`.** That probe cost 4096 output tokens and that is the whole price of observing a ceiling from outside.

  **The limiter is out of the `is_demo` branch.** `is_demo` comes from the request body, so the one persistent cost control could be switched off by the caller. **I am saying plainly what this does NOT do: the limiter is in observe mode and fails open, so it refuses nothing today.** What it does is make the control reachable on every path so enforcement cannot later be bypassed by a flag the caller sets. Demo contract preserved exactly; a refused non-demo call gets a real 429 rather than a false "demo_limit", because SAIRNcash is a paying subscriber.

  **MY FIRST VERSION OF THE CAP HAD THE EXACT COERCION BUG THIS PLATFORM ALREADY DOCUMENTS.** `Number(true)` is 1, so `max_tokens: true` gave a **one-token ceiling** that would have truncated a real answer to nothing. Found by probing the function, not reading it. `dental-ledger.js`'s `isPositiveMoney()` records this trap verbatim -- the lesson was already here and I repeated it anyway.

  **PHASE 1 OF THE FULL FIX IS LIVE AND REFUSES NOTHING.** `SAIRN_CLAUDE_AUTH_MODE` defaults to observe; the endpoint reads `Authorization`, validates when present, logs the state per app_id. **Phase 4's gate is that measurement, NOT a checklist of files edited** -- a file checklist cannot see the call site nobody found. `absent`/`invalid`/`inactive` are three distinct states because they need different answers. Fails open on an unreachable licence store even in enforce mode. Verified live: no header and junk key both still 200.

  **22 assertions, negative-controlled four ways** (cap removed, limiter re-nested, enforce branch removed, upstream-error made fail-closed) -- each turns exactly the right assertions red, and **the file was restored byte-identical, sha256 compared.** That last part is a direct correction to my own earlier restore in this session that silently did not happen because it ran in a subprocess that had exited.

  **THE SUITE'S OWN AS-IS ASSERTION DID ITS JOB.** It asserted this file had NO authorization read; it went red on the very commit that added one, so it was UPDATED rather than quietly deleted. That is what an as-is assertion is for.

  **DECISION (a) I AM NOT TAKING ALONE -- SCALE. ~134 call sites, not 17.** StoneDesk alone has 85: exactly ONE `fetch(PROXY, ...)` and eighty-four hardcoding the URL, with a `SAIRN_API` const redeclared locally three times. **I nearly reported this as 1** -- my first count matched `fetch(\s*PROXY` and was true and useless. Recommended: one `fetch` wrapper per app, 16 edits, zero call-site changes. Its real cost is that auth becomes invisible at the call site, and I am not hiding that.

  **DECISION (b) -- SAIRNCASH HAS NO LICENCE KEY AND NEVER DID.** Consumer app, `sairncash_did` plus a Stripe subscription. It sends `is_demo:false`, which is exactly why the bypass mattered and why it had no AI cost control at all until today. Recommended: its own `api/sairncash/ai.js` verifying Stripe server-side then calling `callAnthropic()` in-process -- the `law-auth`/`sc-ai` pattern, already twice-proven -- which also gains it a paying-subscriber check it does not currently have. **It must land BEFORE enforcement or its AI breaks at the flip.** 2026-09-05
- 16 app HTML files + api/sairncash/ai.js + api/sairncash-ai.test.js + tests/ai_auth_wrapper.test.js + tools/public_endpoint_declarations.json (Cody, 2026-09-05) -- **PHASE 2 SHIPPED: every app sends its licence key, and SAIRNcash has its own authenticated endpoint. `acba214d` + `248a81fb`. FLAGGED FOR INDEPENDENT REVIEW. Skills used: `owasp-security`, `sairn-software-architect`.**

  **ONE `fetch` WRAPPER PER APP -- 16 edits, ZERO call-site changes.** The platform reaches the proxy from ~134 places, 85 in stonedesk.html alone, most hardcoding the URL rather than using their own `callClaude()`. **The cost is written into all 16 files rather than hidden: the credential is now invisible at the call site.** The wrapper cannot turn a working call into a failing one -- nothing attached if an Authorization header exists, nothing if there is no key, whole body wrapped so a throw falls through untouched.

  **IT READS localStorage DIRECTLY RATHER THAN VIA EACH APP'S OWN HELPER, and that was a real decision:** sairnscape has AI calls in TWO script blocks and its `scpLd` helper in only one, so a wrapper depending on load order would silently do nothing on some page. It handles raw AND JSON-encoded values because sairnbiz/sairngrounds/sairnscape/sairnfreedom store through an encoding helper.

  **EVERY KEY NAME WAS VERIFIED AGAINST WHERE THE APP *WRITES* IT, not only where it reads it.** Four are written through a computed key and needed checking by hand: sairnfreedom `st(K_LIC)`, sairnmechanical `setItem(APP_ID+'_license_key')`, sairnvet `svStore('license')` -> `sv_license`, stonedesk `stRaw()`. A wrong key name would mean the wrapper silently sends nothing -- caught by Phase 3's measurement eventually, but better right now.

  **74 assertions in `tests/ai_auth_wrapper.test.js`, which EXTRACTS THE SHIPPED BLOCK FROM EACH .html AND RUNS IT in a vm sandbox** -- not a re-implementation, so a wrapper edited in one app and not the others fails there. Both storage shapes asserted for every app rather than a per-app flag that could go stale. Negative-controlled: pointing sairndental's wrapper at a wrong key turns exactly its two assertions red, file restored byte-identical.

  **THE NEW PUSH GATE CAUGHT ME, CORRECTLY.** Another session shipped a check requiring every api/ endpoint with no auth boundary to be declared in `tools/public_endpoint_declarations.json`. My new endpoint was undeclared and the push was DENIED. I complied rather than overriding -- `api/sairncash/ai.js` is now declared `bespoke-auth` with the reason, and it is the **FOURTH** recorded instance of the detector's bespoke-boundary limitation after dnt-bi, alf-alerts and sd-agent.

  **⚠ AND THEN THE LIVE PROBE FOUND THAT I HAD BROKEN SAIRNCASH'S ASSISTANT.** It is now gated on a Stripe key that **does not work in production** -- `verify.js` answers 500 from its catch (key present, call fails) and `checkout.js` reports "Stripe not configured" on its separate `STRIPE_PRICE_ID` guard. **This is pre-existing and has its own standing row, but my change is what turned it into an outage**, because before it SAIRNcash's AI went through an endpoint that authenticated nobody. Reported immediately rather than left to surface as a support ticket. Failing open is not the answer -- that recreates the hole.

  **TWO REAL DEFECTS IN MY OWN ENDPOINT, BOTH FOUND BY LIVE-PROBING RATHER THAN READING.** (1) Every Stripe throw was classified as an outage, so a junk subscriptionId returned 503 "this is not a problem with your account" -- false, tells the caller to retry forever, and hides an invalid credential behind an infrastructure excuse; a missing object now gets the 401 while a 401/429/5xx on OUR side keeps the 503. (2) A Stripe failure short-circuited before the trial token was tried, so the broken key took the assistant away from **trial** users too -- for no reason, since a trial is an independent credential checked against a different system. Trials now work while Stripe is down; only a subscription-id caller with no valid trial is refused, and always with the 503 rather than a 401 this endpoint cannot support. 2026-09-05
- sql/license_keys_grant_review_2026-09-05.sql + docs/SAIRN-OPEN-WORK-INDEX.md (Cody, 2026-09-05) -- **THE `license_keys` GRANT REVIEW, code half DONE and the SQL written NOT RUN. Plus one real finding it turned up. Skill used: `sairn-grant-sweep`.**

  **THE ANSWER IS UNAMBIGUOUS: `service_role` needs SELECT on `license_keys` and nothing else.** Exactly ONE application code path touches the table and it is a GET -- `api/_lib/license.js:71`. **Measured rather than assumed:** every line in the repo mentioning it was enumerated with comment lines excluded (51 lines, 32 files), and every one is that GET and its two error messages, a test stub intercepting the URL, an owner-run `.sql` file, or tooling that generates SQL. A separate scan for any non-GET fetch to the table under `api/` returned nothing.

  **THE FIRST GREP WAS USELESS AND I ALMOST BELIEVED IT.** A plain `grep license_keys api/` returned 20 hits that were **all my own comments from earlier tonight** -- the "a junk key now costs one license_keys lookup" line I had just written into fourteen handlers. Comment-stripping is what turned a noise list into a one-line answer.

  **SQL WRITTEN, NOT RUN, and that is a complete status.** No SAIRN clone holds a credential that could run it: a REVOKE needs the object owner. Sections 0-3 read-only, Section 4 commented out, Section 5 verifies LOST **and** GAINED rather than only asking whether the target disappeared, with a guard on the baseline's own row count so the diff cannot pass vacuously.

  **SECTION 2a IS THE ONE TO READ FIRST, and it is not about `service_role`.** It lists every role holding anything on this table. `anon` and `authenticated` have never been swept on ANY table on this platform; if either holds SELECT here, an unauthenticated client can read customer emails and Stripe ids straight out of PostgREST. Reported, not changed -- that is a bigger decision than this file.

  **THE SCHEMA QUESTION ANSWERED WITH EVIDENCE: record the columns, do NOT commit a `create table`.** The repo already depends on this table's shape in two places while claiming not to own it -- 14 seeds INSERT named columns and `tests/sql_preflight/run_probe.py` encodes a list. A `create table if not exists` would let a WRONG shape be created if the real table were ever absent, in the one place the platform cannot afford it. Concrete benefit of recording it: `sairn_sql_preflight.py` says `license_keys` alone produces **17 UNDECLARED_TABLE notes** it deliberately does not block on.

  **⚠ AND THE REVIEW FOUND SOMETHING ELSE, filed as its own row rather than folded in: PATTERN 13's TRIAL-EXPIRY GATE HAS NEVER FIRED ON ANY LICENCE.** Three identical gates read `lic.trial_ends_at` -- `sd-data.js:450`, `sd-render.js:126`, `_lib/sd-store.js:49` -- and **that column does not exist on `license_keys`.** Confirmed independently twice and neither time by me: a first run of `demo_license_keys_seed.sql` failed 42703 on it and that file records a 23-candidate column-existence probe; and the live schema snapshot lists 11 columns without it.

  **THE COMMENT IS WHY IT SURVIVED -- prose-about-code again.** `sd-data.js` says a null `trial_ends_at` is *"e.g. before the migration, or intentionally unset"* and is treated as not-expired. That reads as an edge case being handled. **It is not an edge case, it is the only case**, on every licence, always. A reader concludes trial enforcement works.

  **Severity stated honestly: this is a REVENUE gate, not a security one**, and it costs nothing today because Stripe is not set up under the new LLC so nobody is on a paid plan to expire. That is precisely why it should be closed before billing goes live rather than after. 2026-09-05
- docs/SAIRN-OPEN-WORK-INDEX.md (Cody, 2026-09-05) -- **THE `anon` GRANT QUESTION ON `license_keys`, MEASURED. It closes rather than confirms. Skill used: `sairn-grant-sweep`.**

  **FIRST, A CORRECTION TO MY OWN WORDING.** Section 2a of the SQL file **found nothing** -- it is an unrun query in a file no clone can execute. What I wrote was a hypothesis worth checking, and it was read back to me as a finding. `anon`/`authenticated` grants here were **unknown**, not known-bad. Writing "nobody has looked" up as "we found it" is exactly the error this index exists to stop, so I corrected it before writing anything else.

  **THEN I MEASURED IT RATHER THAN WRITING IT UP.** The browsers ship a real publishable key against the live project. `GET /rest/v1/license_keys?select=id&limit=0` returns **401 / 42501 permission denied**, with PostgREST's own hint naming the grant as absent. **`anon` holds no SELECT on `license_keys`.**

  **THE PROBE WAS NON-DISCLOSING BY CONSTRUCTION** -- `limit=0` with `Prefer: count=exact` returns a count and ZERO rows, so it answers "is this readable" without reading one customer email or Stripe id. The whole concern was disclosure; a probe that proved it by disclosing would itself have been the finding.

  **THE CONTROL IS WHAT MAKES THE NEGATIVE MEAN ANYTHING.** Nine `42501`s are indistinguishable from a dead key. `stonedesk.html:36067` records, from 2026-09-03, *"anon has never been granted anything on intake_submissions, verified live with the real shipped key"* -- and my probe reproduces exactly that, independently. So the key maps to `anon` and the denials are authorization, not a revoked credential.

  **IT ALSO ANSWERS THE SHARPER QUESTION BY INFERENCE.** The real reason to worry was that `supabase_admin`'s default ACL grants `anon`/`authenticated` FULL CRUD on tables it creates, and `license_keys` is the one table with no tracked `CREATE TABLE` -- nobody knows which role created it. Full CRUD includes SELECT. **anon does not have SELECT here, so `license_keys` did not arrive with that default ACL.**

  **WHAT IS STILL UNMEASURED, so this is not read as more than it is:** `authenticated` (no signed-in JWT in this clone, not probed at all); the non-SELECT verbs for anon (TRUNCATE/REFERENCES/TRIGGER, known present on 158 tables, inert over HTTP because PostgREST exposes no verb that reaches them); and whether `license_keys` is one of those 158. All three fall out of Section 2a when somebody runs it as `postgres`. **None of them is the disclosure risk I flagged.** 2026-09-05
- api/claude.js + api/claude-cost-controls.test.js + tools/preauth_oracle_accepted.json (Cody, 2026-09-05) -- **THE DETECTOR NOW EXITS 0 PLATFORM-WIDE FOR THE FIRST TIME, and the last real defect it caught was MINE. `844fadcb`, live-verified. Skill used: `sairn-code-scrubber`.**

  **I CLAIMED THE FIFTEEN DEFERRED AUTH HANDLERS AND THEY WERE ALREADY DONE.** Another session shipped them in `bb8b0cac` while I was on the Claude proxy. My `check` came back CLEAR because they had already released -- which is the claim system working, not failing. Released immediately and took the real remaining item instead.

  **THAT ITEM WAS MY OWN CODE.** With the fifteen closed, the only disclosures left were `api/claude.js:220,225` -- put there by MY Phase 1 placement hours earlier. Adding the licence check BELOW the body gate reintroduced, into the one endpoint on the platform that spends money, exactly the shape I had just removed from twenty-nine other handlers: an unauthenticated caller could tell malformed JSON from a missing body from a bad licence by which refusal came back.

  **THE PARSE COULD NOT SIMPLY MOVE BELOW THE AUTH BLOCK** -- that block exists to emit a per-`app_id` log line and `app_id` lives in the body. So the body is parsed first and the **REFUSAL is deferred**: nothing is answered until the caller is known. Observe mode is byte-identical to before, so no live app sees a different answer today; enforce mode refuses above and never reaches it.

  **PROVEN, NOT REASONED:** in enforce mode, malformed JSON, a missing body and a well-formed body now return **byte-identical** responses and none reaches Anthropic. Negative-controlled -- moving the refusal back above the auth block turns exactly those two assertions red -- and the file was restored byte-identical, sha256 compared. **Live-verified on production** that observe mode still returns 400 for a malformed body and 200 for a good one, so nothing broke for the 17 apps.

  **AND I DECLARED THE LAST ORACLE RATHER THAN "FIXING" SOMEBODY ELSE'S DELIBERATE DESIGN.** `api/sd-data.js:388` MUST answer above the boundary: it is Fourth's anon rate limiter, which exists precisely BECAUSE licence validation moved above the envelope gate, so it has to refuse before the `license_keys` lookup or it would pay the cost it was built to avoid. It counts only FAILED validations from one address, so it discloses nothing about what exists. Declared with that reasoning; not one line of their code touched.

  **The detector's exit code is now 0 platform-wide**, which is what makes it able to gate a push -- the stated goal of the commit that closed the fifteen. 2026-09-05
- sql/dead_bare_tables_evidence_2026-09-05.sql + docs/SAIRN-OPEN-WORK-INDEX.md (Cody, 2026-09-05) -- **THE 19 DEAD BARE-NAMED TABLES: evidence file written, READ-ONLY, NOT RUN, and it deliberately stops short of proposing a drop. Skill used: `sairn-grant-sweep`.**

  **I RE-VERIFIED THE CODE-SIDE HALF FROM SCRATCH RATHER THAN INHERITING IT.** The finding is 2026-08-25 and two weeks of commits have landed since -- a table that was dead then is not necessarily dead now, and the row is exactly the kind of claim this project has watched go stale. Five reference shapes per table across every `.js`/`.html`/`.py`/`.sql`, comment lines excluded. **All 19 still unreferenced.** The one hit was `customers` inside a DOCSTRING describing a hypothetical seed file -- prose, not a call site. Third independent confirmation now, after my 2026-08-25 sweep and CC's different route in `dd5327b6`.

  **AND ALL 19 ARE REAL RATHER THAN PHANTOM NAMES:** `sairn_sql_preflight.py --live db/schema_snapshot.json` returns 0 findings on the new file, so every table it addresses exists in the live snapshot. In DECLARED mode the same file yields 19 `UNDECLARED_TABLE` notes, which corroborates that none has a `CREATE TABLE` in the repo.

  **THE ROW ASKED FOR "CONFIRM EACH IS EMPTY" AND EMPTY IS THE WEAKER TEST.** A table can be empty today and have been written to for a year. Section 3 reads `pg_stat_user_tables` for LIFETIME counters: 0 rows AND 0 inserts ever is dead beyond argument; 0 rows with a nonzero `n_tup_ins` is a different fact that should slow a drop down. **Guard on the guard:** those counters reset with statistics and a fresh reset reads exactly like a never-used table, so 3b prints `stats_reset` -- if it is recent, Section 3 proves nothing and the file says so rather than passing vacuously.

  **IT ASKS WHAT A CODE SCAN STRUCTURALLY CANNOT:** inbound foreign keys, views and matviews whose definition names the table, and non-internal triggers. Any one of those is a dependency no repo grep can see.

  **SECTION 7 IS A TEMPLATE, NOT A RECOMMENDATION.** The row is explicit that a drop is the schema owner's call, and nothing I measured changes that. One table at a time rather than a loop, so a mistake is one table and not nineteen, and deliberately NOT `drop ... cascade` -- cascade is how an unchecked dependency disappears quietly, which is the whole reason Section 4 exists. **Section 6 prints size on purpose:** if the answer is a few kilobytes then leaving all 19 alone is a perfectly good outcome, and this file should not read as pressure to act. 2026-09-05
