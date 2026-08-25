-- sql/full_crud_truncate_sweep_2026-08-24.sql
-- DIAGNOSTIC + DRAFT FIX ONLY. Nothing in this file has been run.
--
-- ── FULL EXPORT RECEIVED, 227 TABLES -- FINDINGS BEFORE SECTION 2 RUNS ────
-- Michael's SQL client had a row limit; the first export (100 rows) was
-- confirmed truncated by cross-checking against tables already known to
-- exist (SAIRNlegacy alone continues well past where that export stopped).
-- The real export surfaced two separate classes of finding, checked
-- against the actual codebase rather than assumed:
--
-- (1) ~20 tables show ZERO select/insert/update/delete for service_role
-- (only TRUNCATE/REFERENCES/TRIGGER/MAINTAIN) -- Section 2's keep_privs
-- would be NULL for every one, stripping them to zero grants entirely.
-- CONFIRMED EXACTLY, 2026-08-25: the real Section 1 export shows 20 such
-- tables, and they are this list name for name. The count and the members
-- both hold.
-- ONE MEMBER'S DESCRIPTION IS WRONG, THOUGH ITS PRESENCE IS NOT --
-- intake_submissions is NOT "unreferenced by any live SAIRN code path".
-- StoneDesk reads it on every Intake panel load (stonedesk.html:31943,
-- :31982), straight to Supabase on the ANON key, never through api/ --
-- which is why an api/-only sweep could not see it. It still belongs on
-- this list, because an anon-key path uses no service_role at all, so its
-- service_role grants really are dead weight; "unused by service_role" and
-- "unreferenced by any code" are different claims and this entry merged
-- them. Full detail in Correction B further down.
-- Checked each against every real dispatch mechanism in api/sd-data.js
-- (literal table-name calls, the generic resource===tablename pattern
-- SD_LINEAGE uses, and the full RESOURCES/action registry) -- CONFIRMED
-- unreferenced by any live SAIRN code path: conversations, customers
-- (bare -- the real 'customers' RESOURCE maps to scp_customers, a
-- different physical table, already covered), demo_calls, gl_entries,
-- intake_submissions, invoices (bare -- real resource maps to
-- scp_invoices), jobs (bare -- real resource maps to grd_jobs), licenses
-- (distinct from license_keys, see below), messages, parts, payments,
-- profiles, projects, shop_users, shops, slabs (bare -- real resource
-- maps to sd_slabs), subscriptions, usage_logs, user_storage.
-- Two of these were ALREADY flagged once before, not newly found here:
-- sql/network_schema.sql's own header records that webhook_events and
-- demo_calls surfaced via PostgREST's "perhaps you meant" hint while
-- probing for an unrelated table, explicitly states neither was assumed
-- to be SAIRN's, and recommended "a human check in the Supabase
-- dashboard" that was never followed up. That caution stands: unused by
-- this codebase is not the same as safe to touch with certainty, since a
-- table on the same Supabase project outside this repo's visibility
-- can't be ruled out. In practice the risk is low regardless -- Section 2
-- never touches SELECT/INSERT/UPDATE/DELETE, and these already have none
-- for service_role, so nothing with real read/write access today loses
-- any -- but the dashboard check is still the honest way to close this,
-- not a formality.
--
-- (2) network_insights -- CORRECTED 2026-08-25. THIS ENTRY WAS WRONG.
-- It previously read: "service_role has held only the TRUNCATE/REFERENCES/
-- TRIGGER/MAINTAIN default baseline since the table was created, meaning
-- api/network.js has never been able to actually select or insert on it.
-- This is a live, currently-broken, previously-unnoticed bug -- the same
-- class as the StoneDesk fe730e2 incident." The quote is kept because the
-- claim was acted on -- it is what put a network_insights exclusion into
-- Section 2 -- and deleting it would hide why that exclusion ever existed.
--
-- THERE IS NO BUG. service_role holds SELECT and INSERT on this table
-- today. Three independent proofs, in increasing order of authority:
--   1. LIVE ENDPOINT. GET /api/network?app=stonedesk returns HTTP 200
--      {"ok":true,"insights":[]}, three consecutive calls, no credential.
--   2. THE ERROR SURFACE THAT DID NOT FIRE. A missing grant is Postgres
--      42501, which api/network.js:121 converts to a NAMED 503
--      PERMISSION_DENIED; a missing table is 42P01/PGRST205 -> 503
--      NOT_PROVISIONED at :115. Neither appeared, so the 200 is a
--      completed SELECT and not a fallback path.
--   3. THE GRANT TABLE ITSELF, which is decisive. The 2026-08-25 Section 1
--      export lists network_insights as
--      "INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE".
--
-- WHY THE ORIGINAL INFERENCE FAILED, since the reasoning was sound and the
-- conclusion still wrong: sql/network_schema.sql genuinely contains no
-- GRANT of any kind -- that part was correct and independently re-checked.
-- The unstated assumption was that a table's grants can only come from its
-- own schema file. They can also come from Supabase's Table Editor, which
-- auto-grants on creation where a raw SQL migration does not -- the exact
-- mechanism entry (4) below already invokes for ai_memories, bridge_data,
-- sairn_agents and sairn_agent_commands. Applied there and not here, by
-- the same author, in the same block. That is the reusable lesson: absence
-- of a grant in a schema file is not evidence of absence in the database.
-- It is the same shape as the error corrected further down this file --
-- reading one file per table and stopping.
--
-- CONSEQUENCES, both already applied:
--   * Section 2 no longer excludes network_insights. Keeping the exclusion
--     would leave TRUNCATE standing on a working table for no reason and
--     make Section 3 report a leftover row that looks like a failure.
--     Section 2 will take it from "INSERT, REFERENCES, SELECT, TRIGGER,
--     TRUNCATE" to "INSERT, SELECT" -- confirmed by offline simulation
--     against the real export.
--   * The follow-up this entry called for -- "the real fix is a normal
--     `grant select, insert on network_insights to service_role`" -- must
--     NOT be run. Those grants already exist. Running it would be
--     harmless, but chasing it would be time spent on a bug that does not
--     exist, which is precisely what this correction is here to prevent.
-- STILL GENUINELY OPEN, and small: INSERT is confirmed only by the grant
-- table, never by an observed successful write. Proving that needs a real
-- production POST, which was not worth firing to settle an argument the
-- catalog already settles.
--
-- (3) license_keys deserves its own caution, not blanket trust: it has NO
-- tracked CREATE TABLE anywhere in this repo. api/_lib/license.js's own
-- header already documents this -- the real table is "owned by a
-- separate, not-yet-built generation system" -- and
-- sql/demo_license_keys_seed.sql works around it with WHERE NOT EXISTS
-- specifically because no committed schema means no constraint to check.
-- It is almost certainly fine (every license check on the platform
-- depends on it working today), but with no file to cross-reference its
-- expected grants against, Section 2's correctness here can't be verified
-- the way it can for tables with a real schema file. Recommend excluding
-- it from an initial run and confirming it by hand afterward, given how
-- much depends on it.
--
-- (4) ai_memories, bridge_data, sairn_agents, sairn_agent_commands also
-- have NO tracked CREATE TABLE anywhere in this repo, but ARE real and
-- used (api/sd-data.js, api/_lib/sd-store.js, api/bridge.js respectively)
-- and are NOT in the zero-CRUD list, meaning service_role already has
-- real access to them today -- most likely created via Supabase's Table
-- Editor UI, which (per .claude/skills/sairn-infra-debugger/SKILL.md)
-- auto-grants correctly unlike raw SQL migrations. Section 2 is safe for
-- these the same way it is for every table with a real schema file: it
-- reads and re-asserts whatever they already have, so having no file to
-- check against doesn't create the same risk (1) and (3) do, since their
-- CURRENT grants (not an absent expectation) are what gets preserved.
-- Still worth a follow-up to write real schema files for all four so a
-- future session isn't left guessing again.
--
-- The broader sweep deliberately deferred while closing the append-only
-- gap tonight (sql/append_only_grant_audit.sql), logged as a named
-- follow-up in docs/SAIRN-OPEN-WORK-INDEX.md. Same root cause, confirmed
-- there and not re-litigated here: Postgres's default ACL for schema
-- public grants service_role TRUNCATE/REFERENCES/TRIGGER/MAINTAIN on
-- every table `postgres` creates, and a plain GRANT can only add
-- privileges, never strip that baseline. The source-level fix (ALTER
-- DEFAULT PRIVILEGES ... REVOKE ...) already applied tonight means every
-- table created FROM NOW ON is clean -- this file is only about the
-- ~150 tables that already existed before that fix ran.
--
-- ── SCALE, MEASURED NOT GUESSED ──────────────────────────────────────────
-- RE-MEASURED 2026-08-25 -- the numbers below were 6 files / 7 tables /
-- 158 total / 151 candidates when this header was written at 3d48403.
-- They drifted the same night: SAIRNroofing Phase 3b (148bd80) and 3c
-- (c27f5a2) added more schema files carrying the sound pattern. Re-derived
-- with the same commands rather than trusted, which is the whole point of
-- this file's method.
--
-- grep -n "^grant\|^revoke" across every sql/*.sql file (the same
-- structural technique that found the original 9 append-only tables,
-- extended to the whole platform rather than files tagged "append-only")
-- shows the SOUND `revoke all ... from service_role` pattern in exactly
-- 7 real schema files: sairncode_audit_log, stonedesk_audit_log, and FIVE
-- SAIRNroofing schema files (certifications, claims, employee_auth, jobs,
-- photos -- already fixed, confirmed via
-- `grep -l "revoke all.*from service_role" sql/*.sql`, excluding this file
-- and append_only_grant_audit.sql which are audit/fix files, not schema).
-- Those 7 files cover 9 tables: rf_cert_rules, rf_certifications,
-- rf_claim_photos, rf_claims, rf_jobs, rf_photos,
-- sairnroofing_employee_auth, sairncode_audit_log, stonedesk_audit_log.
-- Every other schema file on the platform -- 154 of 163 total granted
-- tables, counted directly (`grep -rhoiE "^grant [a-z, ]+ on
-- (public\.)?[a-z_]+" sql/*.sql | grep -oE "[a-z_]+$" | sort -u | wc -l`
-- = 163; the 7 sound files account for 9 of them) --
-- across StoneDesk, SAIRNcode, SAIRNcare, SAIRNdesign, SAIRNgrounds/MSB,
-- SAIRNscape, SAIRNlaw, SAIRNsenior, SAIRNbuild, SAIRNlegacy, SAIRNdental,
-- SAIRNcash -- only ever GRANTs, never revokes-all-first, and is
-- therefore structurally a candidate for the same excess baseline. This
-- is a code-level candidate count, not a confirmed live one -- Section 1
-- below is what actually confirms it against the real database.
--
-- ── STONEDESK SLABS / SAIRNGROUNDS-MSB, CHECKED RATHER THAN ASSUMED ──────
-- Per instruction: confirmed live in api/sd-data.js what these tables'
-- real write paths actually do, rather than trusting each schema file's
-- grant line at face value (sairnlaw_audit_log's own grant line was
-- already found to be incomplete once tonight).
--   UPDATE: sd_slabs, sd_blocks, sd_bundles, sd_slab_history all write via
--   `?on_conflict=...` upserts (sd_slabs at api/sd-data.js:517; the other
--   three follow "the sd_slabs read/write shape exactly" per that file's
--   own comment). grd_schedule, grd_invasive_sightings, msb_products,
--   msb_sales (sampled) all confirmed the same on_conflict upsert shape.
--   All genuinely need UPDATE -- narrowing it would break real writes.
--   DELETE: a platform-wide grep for `method: 'DELETE'` in api/sd-data.js
--   returns exactly ONE occurrence, and it is the SC_RESOURCES
--   (SAIRNcode) branch's Compliance-Admin-gated delete -- confirmed by
--   reading that call site directly, not assumed from the open-work-index
--   row that already claimed this (a claim re-verified here, not trusted).
--   StoneDesk slabs and every SAIRNgrounds/MSB table are granted DELETE at
--   the DB level but NO live code path ever issues one. That is a real,
--   separate finding -- unused DELETE grant is a different, narrower kind
--   of excess than the unused TRUNCATE/REFERENCES/TRIGGER/MAINTAIN this
--   sweep is about, and narrowing it would be a functional capability
--   change, not just removing dead default baggage. DELIBERATELY NOT
--   BUNDLED into the fix below -- flagged as its own decision, not
--   silently folded in.
--
-- ── 19 BARE-NAMED TABLES ARE UNREACHABLE FROM ANY CODE PATH (2026-08-25) ──
-- Twenty un-prefixed table names carry the excess baseline and were
-- suspected dead. Checked from code, not from the grant export, because
-- the export is a claim like any other (see the caveat block below).
--
-- Reached independently and by a different route from the SAIRN-cc block
-- (1) above, which is why both are kept: two methods, same 19 names, is
-- worth more than one method asserted twice. Where they DISAGREE, the
-- disagreements are resolved below and neither claim was quietly dropped.
--
-- METHOD -- the reachable-table set was enumerated exhaustively, not
-- sampled. FOUR channels can put a table name in front of PostgREST in
-- this codebase, all four walked:
--   1. `rest('literal')` string constants        -- extracted, 107 names
--   2. `const TABLE = '...'` / `*_TABLE` consts  -- 21 sites, all prefixed
--   3. `rest(resource + ...)` dynamic sites      -- 12 sites, every one of
--      them keyed on an explicit map of PREFIXED names (SD_LINEAGE,
--      SDN_RESOURCES, the 28-name SC_RESOURCES, etc.), so `resource` can
--      never be a bare name at those call sites
--   4. THE BROWSER, going straight to Supabase with the ANON key and
--      never touching api/ at all -- `sb.from('table')` in the app HTML
--
-- CHANNEL 4 IS A REAL GAP THIS CHECK ORIGINALLY HAD, and it is recorded
-- rather than silently patched: the first pass enumerated api/ only, and
-- an api/-only sweep cannot see a table the browser reads directly. It
-- was caught by cross-checking against the SAIRN-cc block, which listed
-- `intake_submissions` -- a name absent from api/ entirely. Re-running
-- with channel 4 included (`grep -rhoE "\.from\(['\"]?[a-z_]+" *.html`)
-- returns exactly TWO real client-side tables platform-wide: `employees`
-- and `intake_submissions` (via `INTAKE_TABLE`, stonedesk.html:31943).
-- Neither is among the 19, so the conclusion below survives the wider
-- method -- but it survives because it was re-checked, not because the
-- first method was sound.
--
-- RESULT: 19 of the 20 are reachable by nothing.
--   conversations, demo_calls, gl_entries, licenses, messages, parts,
--   payments, profiles, projects, shop_users, shops, subscriptions,
--   usage_logs, user_storage, webhook_events  -- absent from api/ entirely
--   and with no `create table` anywhere in sql/.
--   customers, invoices, jobs, slabs -- these four ARE registered resource
--   keys, which is the trap. Every branch that handles them maps to a
--   PREFIXED table: 'customers' -> scp_customers (sd-data.js:1356),
--   'invoices' -> scp_invoices (:1440), 'jobs' -> grd_jobs (:690),
--   'slabs' -> sd_slabs (:508). The bare tables of the same name are
--   never addressed. sd-data.js's own comment at :1355 records that the
--   prefixed resource names were chosen "specifically to avoid the
--   collision", so this is by design, not coincidence.
--
-- ── TWO CORRECTIONS TO BLOCK (1)/(2) ABOVE, BOTH EVIDENCED ───────────────
--
-- CORRECTION A -- network_insights is NOT currently broken. Block (2)
-- above states that service_role "has held only the TRUNCATE/REFERENCES/
-- TRIGGER/MAINTAIN default baseline since the table was created, meaning
-- api/network.js has never been able to actually select or insert on it,"
-- and calls it a live bug of the fe730e2 class. SELECT, at least, works.
-- Disproved live, three consecutive calls, no credential used:
--     curl -s -w " [HTTP %{http_code}]" \
--       "https://sairn.vercel.app/api/network?app=stonedesk"
--     -> {"ok":true,"insights":[]} [HTTP 200]   (x3)
-- A missing grant is Postgres 42501, which api/network.js:121 turns into
-- a NAMED 503 PERMISSION_DENIED, and a missing table is 42P01/PGRST205 ->
-- 503 NOT_PROVISIONED (:115). Neither fired. A 200 with ok:true is a
-- completed SELECT against network_insights, so service_role holds SELECT.
-- HOW, given sql/network_schema.sql really does contain no grant: block
-- (4) above supplies the mechanism -- a table created through Supabase's
-- Table Editor auto-grants, unlike a raw SQL migration. That is the
-- likeliest explanation and it is a hypothesis, not a finding.
-- WHAT IS STILL OPEN: INSERT is UNVERIFIED. Proving it needs a real POST
-- that writes a row, which is not something to fire at production to win
-- an argument, so it was not done. The honest statement is: SELECT
-- confirmed present, INSERT unknown. Do not upgrade that to "the table is
-- fine" without checking the write path.
-- WHY IT MATTERS BEYOND ONE TABLE: network_insights was on the ~20
-- zero-CRUD list, and it demonstrably has CRUD. The zero-CRUD list is
-- therefore not reliable per-row, which is the same defect as the
-- truncated export it came from.
--
-- CORRECTION B -- intake_submissions is NOT unreferenced. Block (1) lists
-- it as "CONFIRMED unreferenced by any live SAIRN code path." StoneDesk
-- reads it on every Intake panel load: `INTAKE_TABLE` is declared at
-- stonedesk.html:31943 and `sb.from(INTAKE_TABLE).select('*')` runs in
-- intakeRefresh() at :31982. It is invisible to an api/-only sweep
-- because it never goes through api/ -- it is channel 4, the browser's
-- own Supabase client on the ANON key. Both sweeps had the same blind
-- spot in opposite directions, which is precisely why this is written
-- down rather than corrected in place.
-- NUANCE THAT CUTS THE OTHER WAY, stated so nobody over-reads this: an
-- anon-key path does not use service_role at all, so intake_submissions'
-- service_role grants may genuinely be dead weight even though the TABLE
-- is very much alive. "Unused by service_role" and "unreferenced by any
-- code" are different claims and block (1) merged them.
-- SEPARATE, NOT CHASED HERE: intakeRefresh()'s catch falls back to
-- localStorage silently, so if that anon read is failing today the panel
-- shows stale cached rows and reports nothing. That is a silent-failure
-- candidate for sairn-silent-failure-sweep, not a grant question.
--
-- WHAT NONE OF THIS CHANGES: Section 2 reads each table's OWN live grants
-- and never consults any list in this file. That is exactly why two
-- wrong list entries could not have caused harm -- had Section 2 been
-- driven by the derived list it would have stripped network_insights'
-- real SELECT and silently killed StoneDesk's Intelligence Network panel.
-- Recorded because the near-miss is the argument for the list-free
-- design, not a footnote to it.
--
-- ── THE 11 "MISSING" TABLES: SETTLED 2026-08-25. NOT A TRUNCATION. ───────
-- RETRACTION FIRST. An earlier version of this block argued the export had
-- been truncated a second time, on the strength of 11 tables that were
-- code-reachable, had real schema files, and appeared to use the UNSOUND
-- grant pattern -- so they "MUST" carry the excess baseline and "MUST"
-- appear in a TRUNCATE-filtered list. That inference was WRONG, and the
-- export is right. Both halves of it are now explained, from the repo and
-- from one live probe, and neither half is a missing row.
--
-- THE METHOD ERROR, stated plainly because it is the reusable part: for
-- each table I read that table's OWN schema file, found
-- `revoke all on public.X from anon, authenticated` -- no service_role --
-- and concluded the baseline survived. I never checked whether a LATER
-- file had already fixed it. One did, and this very file names it in its
-- own opening paragraph. Reading one file per table and stopping is how a
-- structurally-plausible claim gets built on a real gap in the evidence.
--
-- FIVE OF ELEVEN -- possibility (2), already revoked, no longer unsound.
-- sql/append_only_grant_audit.sql does an explicit
-- `revoke all ... from service_role` followed by a narrow re-grant on
-- dnt_credentials (:118), dnt_cred_rules (:120), alf_staff_credentials
-- (:124), alf_signals (:126) and alf_claim_routes (:128). That file was
-- RUN live -- 6776f99 reports two of its tables failing with a real 42P01
-- from the actual database, which only happens to a script that executed.
-- CORROBORATED BY THE EXPORT ITSELF, which is the part worth keeping: that
-- file revokes from service_role on NINE tables in total -- the five above
-- plus sairnlaw_audit_log (:134), rf_photos (:172), rf_jobs (:174) and
-- sairnroofing_employee_auth (:176) -- and ALL NINE are absent from the
-- export. 9 for 9. A truncation does not select exactly the nine rows a
-- known REVOKE touched. sairnlaw_audit_log is the cleanest single case,
-- because it has no sound schema file of its own; its absence is
-- attributable to nothing but that audit having run.
--
-- SIX OF ELEVEN -- possibility (1), never migrated. The whole SAIRNsenior
-- family: sen_caregivers, sen_claims, sen_clients, sen_portal_links,
-- sen_visits, sairnsenior_employee_auth. Not touched by the audit file
-- (zero `sen_` matches in it), and their schema files are dated 2026-08-20,
-- four days BEFORE the ALTER DEFAULT PRIVILEGES fix -- so had they been run
-- they would carry the baseline and would have to appear. They do not,
-- because the tables are not there.
--   REPO EVIDENCE, from the build sessions' own logs at the time:
--   SAIRN-ACTIVE-WORK.md:153 "SEN- license still not provisioned, both new
--   migrations still queued, not run"; :155 "Same blocker as every
--   SAIRNsenior entry so far, unchanged: ... a third migration queued,
--   none run yet". No later entry ever reverses that.
--   LIVE PROOF, and it needed no credential and wrote nothing --
--   api/sen-portal.js's `view` action is deliberately auth-free (:92-95),
--   and a bogus token cannot reach the last_accessed_at write at :107:
--     curl -sX POST https://sairn.vercel.app/api/sen-portal \
--       -H 'Content-Type: application/json' \
--       -d '{"action":"view","token":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'
--     -> HTTP 503 {"error":{"code":"NOT_PROVISIONED",
--                  "message":"Portal links are not set up yet."}}
--   A table that EXISTS returns 404 INVALID_LINK for an unknown token
--   (:104). 503 NOT_PROVISIONED is the 42P01/PGRST205 branch at :100.
--   sen_portal_links does not exist in production. Same failure mode Cody
--   found for sairncash_waitlist and sairnscape_org_intel: schema file in
--   the repo, migration never run against production.
--
-- WHAT IS STILL UNRESOLVED, and it is small: the count. Enumerating the
-- pasted list, with the shorthand families taken at their stated sizes
-- (leg_* 34, msb_* 9, sc_* 29, scp_* 14, sdn_* 17), totals 215 against a
-- 227 label. The raw jsonb_agg result was offered but the message carried
-- the placeholder text "[same JSON dataset as above]" in place of the
-- data, so it could not be recounted and the 12-table gap is NOT settled.
-- It no longer bears on the 11, which are fully accounted for above, and
-- the likeliest reading is that a shorthand family size is off by a few.
-- Do not treat 215 as a defect in the export on the strength of this file.
--
-- THE REAL, ACTIONABLE FINDING UNDERNEATH ALL OF THIS: SAIRNsenior has SIX
-- unrun migrations in production and an unprovisioned SEN- license. Every
-- endpoint degrades honestly to NOT_PROVISIONED rather than crashing, so
-- it has been failing quietly since 2026-08-20. That is an app-readiness
-- item, not a grant item, and it is tracked as its own row in
-- docs/SAIRN-OPEN-WORK-INDEX.md rather than fixed here -- running another
-- app's migrations as a side effect of a privilege audit is precisely the
-- scope creep 6776f99 refused, and this file refuses it for the same reason.
--
-- CONSEQUENCE FOR THIS SWEEP: none of the 11 needs anything from Section 2.
-- Five are already correctly narrowed; six do not exist. Section 1 remains
-- the thing to run and read first, for the ordinary reason that it queries
-- information_schema live and no pasted list is a substitute.
--
-- ── WHY THE FIX BELOW IS DYNAMIC, NOT 150 HAND-WRITTEN LINES ─────────────
-- Hand-enumerating ~150 REVOKE/GRANT pairs is exactly the kind of manual
-- transcription that introduces the next bug (a copy-paste privilege
-- dropped or added by mistake). Section 2 instead reads each table's OWN
-- CURRENT select/insert/update/delete grants from the database itself and
-- re-asserts exactly that same set -- it cannot add or remove any
-- functional capability, by construction, because it never invents a
-- privilege that was not already there. It only ever strips
-- TRUNCATE/REFERENCES/TRIGGER/MAINTAIN, which no schema file on this
-- platform ever explicitly grants (confirmed: zero explicit `references`
-- or `trigger` or `maintain` grants anywhere in sql/*.sql) -- so stripping
-- them is safe everywhere, unconditionally, without per-table judgment.

-- ── SECTION 1 HAS NOW BEEN RUN. REAL OUTPUT ANALYSED 2026-08-25. ─────────
-- Received as a single jsonb_agg cell, which cannot be row-capped the way
-- the two earlier exports were. Measured facts, counted not eyeballed
-- (the artifact is small enough to check by machine and was):
--
--   214 rows, NOT 227. The 227 figure elsewhere in this file and in the
--   open-work index describes something else -- most plausibly the count
--   of public tables overall -- and the two must stop being used
--   interchangeably. 214 is the number of tables where service_role holds
--   TRUNCATE, which is the only number this sweep acts on.
--
--   MAINTAIN appears NOWHERE in the output. Only DELETE, INSERT,
--   REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE are ever present. This
--   Postgres predates the MAINTAIN privilege (PG18) or never grants it.
--   Every mention of MAINTAIN in this file is therefore harmless but
--   moot -- REVOKE ALL covers it if it ever appears, and nothing needs
--   changing.
--
--   REFERENCES and TRIGGER are present on ALL 214 rows, always alongside
--   TRUNCATE. That does NOT retire finding R2 below: this query filters on
--   TRUNCATE, so a REFERENCES-only table is invisible to it BY
--   CONSTRUCTION and could not have shown up here however many exist.
--   Section 1b was added to look for exactly that; it has not been run.
--
--   FIVE distinct privilege shapes, which is a tighter spread than the
--   "~150 hand-written lines" framing implied:
--     158  DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
--      32  INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
--      20  REFERENCES, TRIGGER, TRUNCATE                  <- zero CRUD
--       3  DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE
--       1  INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE
--
--   THE 20 ZERO-CRUD TABLES ARE EXACTLY THE PREDICTED SET, name for name:
--   conversations, customers, demo_calls, gl_entries, intake_submissions,
--   invoices, jobs, licenses, messages, parts, payments, profiles,
--   projects, shop_users, shops, slabs, subscriptions, usage_logs,
--   user_storage, webhook_events. Section 2 leaves each with NO grants,
--   which is correct: 19 are reachable by no code path, and
--   intake_submissions is reached only by the browser on the ANON key,
--   so its service_role grants are dead weight even though the table is
--   live. The dashboard check block (1) asks for still stands.
--
--   network_insights: "INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE".
--   It has real SELECT and real INSERT. This is the third independent
--   confirmation, after the live curl and the endpoint's own error
--   surface, that it was never grant-broken -- and it is the decisive one,
--   because it is the grant table itself. Correction A is settled and the
--   Section 2 exclusion built on the opposite claim is REMOVED below.
--
-- SECTION 2 SIMULATED AGAINST THIS REAL OUTPUT, offline, before any run:
-- applying the loop's own logic to all 214 rows preserves the CRUD subset
-- EXACTLY on 214 of 214, strips only TRUNCATE/REFERENCES/TRIGGER, and
-- leaves precisely the 20 zero-CRUD tables with nothing. That is a
-- verified property of this real data, not a restatement of the comment's
-- claim -- but it validates the LOGIC against a SNAPSHOT, which is not
-- the same as verifying the RUN. R1 still applies and Sections 0 and 3
-- below are what close it.
--
-- NOT RUN BY THIS SESSION, AND IT CANNOT BE: there is no database
-- credential in this clone, and service_role could not do it anyway --
-- REVOKE requires the object owner, which is postgres. Section 2 is
-- prepared, hardened and simulated; executing it needs a Supabase SQL
-- editor session as postgres.
--
-- ── RUN ORDER ────────────────────────────────────────────────────────────
--   Section R6  -> confirm you are postgres
--   Section R4  -> pre-flight, expect zero rows from both queries
--   Section 0   -> capture the baseline (creates a real table on purpose)
--   Section 1   -> the discovery query, already run once
--   Section 1b  -> the R2 gap: REFERENCES/TRIGGER without TRUNCATE
--   Section 2   -> the fix (uncomment deliberately; nothing else in this
--                  file mutates anything)
--   Section 3   -> the diff that proves nothing was lost
--   Section 4   -> drop the baseline table once Section 3 is clean

-- ── SECTION R6: PRECONDITION. Must print `postgres`. ─────────────────────
select current_user, session_user;

-- ── SECTION R4: PRE-FLIGHT. Both queries must return ZERO rows. ──────────
-- If either returns anything, STOP: Section 2's REVOKE ALL would destroy
-- a column-level grant or a WITH GRANT OPTION that its re-GRANT cannot
-- restore. The repo has neither, but the repo is not the database.
select table_name, column_name, privilege_type
from information_schema.role_column_grants
where table_schema = 'public' and grantee = 'service_role';

select table_name, privilege_type
from information_schema.role_table_grants
where table_schema = 'public' and grantee = 'service_role'
  and is_grantable = 'YES';

-- ── SECTION 0: BASELINE CAPTURE -- closes R1. Run BEFORE Section 2. ──────
-- A REAL table, deliberately, not a temp one. The Supabase SQL editor does
-- not guarantee that two "Run" clicks share a session, and a temp table
-- would silently vanish between them -- taking the only proof with it and
-- leaving Section 3 to compare against nothing. Section 4 drops it.
-- Writes no application data and touches no application table.
drop table if exists public._grant_baseline_2026_08_25;
create table public._grant_baseline_2026_08_25 as
select table_name, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee = 'service_role'
  and privilege_type in ('SELECT', 'INSERT', 'UPDATE', 'DELETE');

-- ── SECTION 1: DISCOVERY -- run this first, read the output before Section 2 ──
-- Every public table where service_role holds TRUNCATE, with its full
-- current privilege set alongside. List-free: does not depend on the
-- ~150-table candidate list above, so it will also catch anything that
-- list missed.
select
  t.table_name,
  string_agg(distinct g.privilege_type, ', ' order by g.privilege_type) as current_privs,
  bool_or(g.privilege_type = 'TRUNCATE')   as has_truncate,
  bool_or(g.privilege_type = 'REFERENCES') as has_references,
  bool_or(g.privilege_type = 'TRIGGER')    as has_trigger,
  bool_or(g.privilege_type = 'UPDATE')     as has_update,
  bool_or(g.privilege_type = 'DELETE')     as has_delete
from information_schema.tables t
join information_schema.role_table_grants g
  on g.table_name = t.table_name and g.table_schema = t.table_schema
where t.table_schema = 'public' and g.grantee = 'service_role'
group by t.table_name
having bool_or(g.privilege_type = 'TRUNCATE')
order by t.table_name;

-- ── SECTION 1b: THE R2 GAP -- REFERENCES/TRIGGER WITHOUT TRUNCATE ────────
-- Section 1 filters on TRUNCATE, so it can never surface a table that
-- carries REFERENCES or TRIGGER but had TRUNCATE revoked separately. The
-- 214-row output cannot confirm or refute that such tables exist; only
-- this query can. Run it once. If it returns rows, widen Section 2's
-- HAVING (it is already widened below) and expect Section 3 to cover them.
select
  t.table_name,
  string_agg(distinct g.privilege_type, ', ' order by g.privilege_type) as current_privs
from information_schema.tables t
join information_schema.role_table_grants g
  on g.table_name = t.table_name and g.table_schema = t.table_schema
where t.table_schema = 'public' and g.grantee = 'service_role'
group by t.table_name
having bool_or(g.privilege_type in ('REFERENCES', 'TRIGGER', 'MAINTAIN'))
   and not bool_or(g.privilege_type = 'TRUNCATE')
order by t.table_name;

-- ── SECTION 2 REVIEW, 2026-08-25 -- 6 FINDINGS, NOTHING CHANGED YET ──────
-- Section 2 was reviewed line by line rather than approved on the strength
-- of its own comment. The central claim -- "cannot add or remove
-- functional capability, by construction" -- holds for the code path as
-- written: keep_privs is filtered to a fixed IN-list, so the re-GRANT can
-- only ever restore a subset of what the table already had. The findings
-- below are about coverage, verification and blast radius, not about that
-- claim being false. Ordered by how much they matter. NONE of them are
-- applied -- the DO block is untouched, because whoever actually runs this
-- against the live database should decide, and one of the six is a
-- decision, not a defect.
--
-- (R1) THE "CANNOT CHANGE CAPABILITY" CLAIM IS UNPROVEN FOR THE ACTUAL
-- RUN, and this is the biggest gap. It is proven for the LOGIC; it is not
-- proven for the EVENT. There is no before-capture step anywhere in this
-- file, so after Section 2 runs there is no artifact to diff against and
-- the only verification (Section 3) checks that TRUNCATE is GONE, never
-- that SELECT/INSERT/UPDATE/DELETE SURVIVED. A bug in the loop that
-- dropped a privilege would pass Section 3 silently. The index row for the
-- verb-gate change already demands baseline-replay proof for exactly this
-- class of change; this file should meet the same bar. Recommended, as a
-- new Section 0 run BEFORE Section 2 in the same editor session:
--     create temp table grant_baseline as
--     select table_name, privilege_type
--     from information_schema.role_table_grants
--     where table_schema='public' and grantee='service_role'
--       and privilege_type in ('SELECT','INSERT','UPDATE','DELETE');
-- and then, as the real Section 3, a full-outer-join of that snapshot
-- against the post-run state expecting ZERO rows on either side. Note the
-- temp table dies with the session, so Sections 0, 2 and 3 must be one
-- editor session -- which is a feature: it makes the proof and the change
-- inseparable.
--
-- (R2) BOTH SECTIONS FILTER ON TRUNCATE ALONE, SO A REFERENCES-ONLY OR
-- TRIGGER-ONLY TABLE IS INVISIBLE TO THE SWEEP AND TO ITS VERIFICATION.
-- `having bool_or(privilege_type = 'TRUNCATE')` is the filter in Section
-- 1, Section 2 and (by reference) Section 3. This file is titled for four
-- privileges and only searches for one of them. The defence is that the
-- default ACL grants all four together so they co-occur -- but that
-- coupling is precisely what append_only_grant_audit.sql and the
-- ALTER DEFAULT PRIVILEGES fix have already been breaking on purpose, and
-- any hand-run REVOKE breaks it too. Section 3 would then report "zero
-- rows, clean" over tables still holding REFERENCES. Recommended filter,
-- all three places:
--     having bool_or(privilege_type in
--       ('TRUNCATE','REFERENCES','TRIGGER','MAINTAIN'))
--
-- (R3) THE EXCLUSION OF network_insights RESTS ON A CLAIM DISPROVED
-- ABOVE. The comment excludes it because it "already has zero real CRUD
-- for service_role today." Correction A shows SELECT works live, three
-- consecutive 200s. So the exclusion does not protect anything -- it just
-- leaves one table's excess baseline in place, and Section 3 will then
-- correctly report a leftover row that looks like a failure. Do not
-- silently delete the exclusion either: read network_insights' actual row
-- in Section 1's live output first, and drop the exclusion only if that
-- row shows real CRUD to preserve. The license_keys exclusion is
-- UNAFFECTED by this and remains well-reasoned -- no tracked schema,
-- platform-wide blast radius, exclude it and hand-check after.
--
-- (R4) COLUMN-LEVEL GRANTS AND GRANT OPTION WOULD BE DESTROYED SILENTLY.
-- `REVOKE ALL ON <table>` strips column-level privileges too, and the
-- re-GRANT only restores TABLE-level ones; likewise `WITH GRANT OPTION`
-- is not carried across. Neither is visible in role_table_grants -- the
-- first lives in role_column_grants, the second in that view's
-- is_grantable column, and Section 1 selects neither. The repo is clean
-- on both (`grep` finds zero column grants and zero `with grant option`
-- in sql/*.sql), but the repo is not the database -- this file already
-- documents five real tables with no tracked CREATE TABLE, and a table
-- on the same Supabase project from outside this repo cannot be ruled
-- out. Cheap pre-flight, expect zero rows:
--     select * from information_schema.role_column_grants
--     where table_schema='public' and grantee='service_role';
--     select table_name, privilege_type from information_schema.role_table_grants
--     where table_schema='public' and grantee='service_role' and is_grantable='YES';
--
-- (R5) THE WHOLE LOOP IS ONE TRANSACTION HOLDING A LOCK PER TABLE. A DO
-- block is a single statement, so all ~150 REVOKE/GRANT pairs commit
-- together -- good, because a partial application is the one outcome
-- nobody could reason about afterwards, and it means no window exists
-- where a table has been revoked but not re-granted. The cost is that
-- every relation it touches is locked until the block commits, against
-- live API traffic. It is catalog-only work and should be fast, but
-- "should be" is not a measurement. Run it in a quiet window, the same
-- way the .gitattributes row demands one. Not a defect -- a scheduling
-- constraint that is currently written down nowhere.
--
-- (R6) PRECONDITION NEVER STATED: THIS MUST RUN AS THE TABLE OWNER.
-- information_schema.role_table_grants only shows grants where the
-- current user is grantor, grantee, or a member of one of them, and
-- REVOKE only removes grants the executing role has authority over. Run
-- as postgres in the Supabase SQL editor both hold. Run as anything less
-- and the loop silently iterates a SHORT list, changes less than it
-- claims, and Section 3 reports clean because it is filtered by the same
-- blind spot. Add `select current_user;` as the first line of the run and
-- confirm it says postgres before executing anything.
--
-- ALSO CHECKED AND CLEAN, so nobody re-derives them: no partitioned
-- tables anywhere in sql/*.sql (REVOKE on a parent would not cascade to
-- partitions), and zero explicit REFERENCES/TRIGGER/MAINTAIN grants
-- anywhere in the repo, which is what makes stripping them unconditionally
-- safe rather than a per-table judgment.
--
-- ── SECTION 2: DRAFT FIX -- NOT RUN. Review Section 1's real output first. ──
-- For every table service_role holds TRUNCATE on, strips
-- TRUNCATE/REFERENCES/TRIGGER/MAINTAIN and re-grants exactly whichever of
-- SELECT/INSERT/UPDATE/DELETE it already had -- never more, never fewer.
-- Idempotent and safe to re-run; touches no row data; changes no
-- functional capability of any table.
--
-- DO $$
-- DECLARE
--   r RECORD;
--   keep_privs TEXT;
-- BEGIN
--   FOR r IN
--     SELECT t.table_name,
--            string_agg(DISTINCT g.privilege_type, ', ') AS all_privs
--     FROM information_schema.tables t
--     JOIN information_schema.role_table_grants g
--       ON g.table_name = t.table_name AND g.table_schema = t.table_schema
--     WHERE t.table_schema = 'public' AND g.grantee = 'service_role'
--       -- EXCLUSION LIST, 2026-08-25. network_insights was REMOVED from
--       -- it: the exclusion rested on "already has zero real CRUD", and
--       -- the live grant table says INSERT, REFERENCES, SELECT, TRIGGER,
--       -- TRUNCATE. Keeping it excluded would have left TRUNCATE standing
--       -- on a working table for no reason, and made Section 3 report a
--       -- leftover row that looks like a failure.
--       -- license_keys STAYS excluded, unchanged and for its own reasons:
--       -- no tracked CREATE TABLE to verify the result against, and every
--       -- license check on the platform depends on it. The simulation says
--       -- it would come through intact (DELETE, INSERT, SELECT, UPDATE
--       -- before and after), so this is caution, not a known risk -- drop
--       -- the exclusion by choice if you would rather sweep it too.
--       AND t.table_name NOT IN ('license_keys')
--     GROUP BY t.table_name
--     -- R2: widened from `= 'TRUNCATE'`. A table holding REFERENCES or
--     -- TRIGGER without TRUNCATE was previously invisible to the fix AND
--     -- to its verification. Section 1b is what tells you whether any
--     -- exist; this clause makes the fix cover them either way.
--     HAVING bool_or(g.privilege_type in
--            ('TRUNCATE', 'REFERENCES', 'TRIGGER', 'MAINTAIN'))
--   LOOP
--     SELECT string_agg(priv, ', ') INTO keep_privs
--     FROM unnest(string_to_array(r.all_privs, ', ')) AS priv
--     WHERE priv IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE');
--
--     EXECUTE format('REVOKE ALL ON public.%I FROM service_role', r.table_name);
--     IF keep_privs IS NOT NULL THEN
--       EXECUTE format('GRANT %s ON public.%I TO service_role', keep_privs, r.table_name);
--     END IF;
--
--     RAISE NOTICE 'Fixed %: kept %', r.table_name, coalesce(keep_privs, '(nothing -- had only TRUNCATE/REFERENCES/TRIGGER)');
--   END LOOP;
-- END $$;

-- ── SECTION 3: VERIFY, after Section 2 is actually run ───────────────────
-- Three checks. ALL THREE must pass. The old instruction -- "re-run
-- Section 1, expect zero rows" -- was only check 3a, and 3a alone proves
-- the excess is gone while saying nothing about whether the real
-- privileges survived. 3b is the one that matters (R1).

-- 3a. NOTHING EXCESS REMAINS. Expect zero rows, except license_keys if it
--     is still excluded from Section 2. Widened per R2, so this now also
--     catches REFERENCES/TRIGGER left behind without TRUNCATE.
select
  t.table_name,
  string_agg(distinct g.privilege_type, ', ' order by g.privilege_type) as leftover
from information_schema.tables t
join information_schema.role_table_grants g
  on g.table_name = t.table_name and g.table_schema = t.table_schema
where t.table_schema = 'public' and g.grantee = 'service_role'
group by t.table_name
having bool_or(g.privilege_type in
       ('TRUNCATE', 'REFERENCES', 'TRIGGER', 'MAINTAIN'))
order by t.table_name;

-- 3b. NOTHING FUNCTIONAL WAS LOST OR GAINED. Expect ZERO rows.
--     A full outer join of the Section 0 baseline against the current
--     state. `side` names which direction any discrepancy went, so a
--     failure is legible without a second query: LOST means a real
--     privilege disappeared, GAINED means the fix granted something that
--     was not there before. Either is a bug and both are silent under 3a.
select
  coalesce(b.table_name, a.table_name) as table_name,
  coalesce(b.privilege_type, a.privilege_type) as privilege_type,
  case when a.table_name is null then 'LOST' else 'GAINED' end as side
from public._grant_baseline_2026_08_25 b
full outer join (
  select table_name, privilege_type
  from information_schema.role_table_grants
  where table_schema = 'public'
    and grantee = 'service_role'
    and privilege_type in ('SELECT', 'INSERT', 'UPDATE', 'DELETE')
) a
  on a.table_name = b.table_name and a.privilege_type = b.privilege_type
where a.table_name is null or b.table_name is null
order by 1, 2;

-- 3c. THE BASELINE ITSELF WAS REAL. If Section 0 ran against an empty or
--     partial catalog read, 3b compares against nothing and passes
--     vacuously -- the one way 3b can lie. This is the guard against that.
--     EXPECTED: a LOWER BOUND of 739 rows across 194 tables. That is the
--     exact CRUD contribution of the 214 tables in the 2026-08-25 export
--     (158*4 + 32*3 + 3*3 + 1*2 = 739; the 20 zero-CRUD tables contribute
--     nothing, so 214 - 20 = 194). The real figure MUST be higher, because
--     Section 0 captures every table service_role has CRUD on, while
--     Section 1 only listed those that also hold TRUNCATE -- the ~15
--     already-clean tables (the append_only_grant_audit.sql set, the two
--     audit logs, the rf_* family) contribute rows here and appeared in
--     neither. Anything AT or BELOW 739 means Section 0 under-read; treat
--     it as a failed capture and do not trust 3b.
select count(*) as baseline_rows,
       count(distinct table_name) as baseline_tables
from public._grant_baseline_2026_08_25;

-- ── SECTION 4: CLEANUP -- only after Section 3 passes all three ──────────
-- drop table public._grant_baseline_2026_08_25;

-- ── WHAT THIS DOES NOT COVER ──────────────────────────────────────────────
-- Same ownership caveat as every other grant file tonight: postgres owns
-- these tables and holds every privilege implicitly regardless of any
-- REVOKE here. This closes the service_role/API surface only.
--
-- The unused-DELETE finding above (StoneDesk slabs, SAIRNgrounds/MSB, and
-- likely most non-SC_RESOURCES full-CRUD tables) is NOT addressed here --
-- narrowing it is a real, separate, functional-capability decision, not
-- a mechanical strip-the-unused-default fix, and deserves its own review
-- rather than riding along on this one.
