-- sql/anon_authenticated_schema_usage_revoke_stage_b_2026-08-26.sql
--
-- STAGE B. One statement. Its own file and its own window, deliberately.
--
-- Stage A (sql/anon_authenticated_grant_revoke_2026-08-26.sql) ran and
-- verified clean on 2026-08-26: 3a empty, 3b six rows all LOST with zero
-- GAINED, 3c remaining_rows 0, 3d `postgres`'s default ACL clean for both
-- roles, 3e empty. This is the remaining half.
--
-- ══ WHY THIS IS NOT IN THE STAGE A FILE ═══════════════════════════════════
-- Every statement in Stage A was verifiable from the catalog: a baseline was
-- captured, the diff was computed, and the result could be stated exactly.
-- This one is not. `revoke usage on schema public` removes the ability of
-- `anon` and `authenticated` to resolve names in `public` at all, and its
-- blast radius is NOT knowable from this repo -- Supabase internals (Studio,
-- Realtime, PostgREST schema-cache reload, managed features) may touch
-- `public` as those roles in ways no file here describes.
--
-- Run together with Stage A, a failure would be unattributable: nobody could
-- say which half caused it. Run apart, the answer is free. That is the whole
-- reason for the split, and it is why this file exists rather than a section.
--
-- ══ WHY IT IS SAFE ENOUGH TO DO AT ALL -- the evidence, not a feeling ═════
--   * Section 1b of Stage A returned ZERO rows: neither role holds any
--     privilege on any table beyond the baseline Stage A removed.
--   * An independent GET probe as `anon` with the real shipped publishable key
--     across 228 tables returned 227 x 401 and 1 x 404. Zero 200s.
--   * There is no `grant ... to anon` statement anywhere in sql/, on any
--     table, ever.
--   * `authenticated` is UNREACHABLE, not merely unused: no Supabase Auth
--     exists anywhere on the platform (the only Auth is Firebase, in
--     sairncash.html, which mints a Firebase auth.uid and never a Supabase
--     JWT), and zero RLS policies reference auth.uid()/auth.jwt()/auth.email()
--     -- all 186 are `auth.role() = 'service_role'`.
--   * Every real data path on this platform runs as `service_role` through
--     api/sd-data.js, which this statement does not touch.
--
-- ══ THE ONE KNOWN COST, named rather than discovered later ════════════════
-- If a public intake form is ever built the right way, `anon` will need INSERT
-- on one table -- and this makes restoring that two steps (schema USAGE, then
-- the table grant) instead of one. Small and acceptable. Note the feature that
-- would need it is currently dead at both ends: `/stonedesk-intake` returns
-- 404 and the panel behind it cannot read its table.
--
-- ══ ROLLBACK -- HAVE THIS OPEN BEFORE RUNNING SECTION 2, NOT AFTER ════════
--
--     grant usage on schema public to anon, authenticated;
--
-- One line, immediate, no side effects. If the dashboard or any live path
-- misbehaves after Section 2, run it first and diagnose second.

-- ── SECTION R6: PRECONDITION. Must print `postgres`. ─────────────────────
select current_user, session_user;

-- ── SECTION 0: BEFORE-STATE ─────────────────────────────────────────────
-- Stage A's 3f already recorded this: both roles hold USAGE on `public`.
-- Re-run it here anyway. It is this file's only baseline -- there is no table
-- to capture, so the printed output IS the before-state, and a run without it
-- has nothing to compare against.
select n.nspname                     as schema,
       acl.grantee::regrole::text    as grantee,
       acl.privilege_type
from pg_namespace n
cross join lateral aclexplode(n.nspacl) as acl
where n.nspname = 'public'
  and acl.grantee::regrole::text in ('anon', 'authenticated')
order by 2, 3;

-- ── SECTION 1: CONFIRM STAGE A IS STILL CLEAN BEFORE WIDENING ───────────
-- Expect ZERO rows. If anything appears, someone granted one of these roles
-- something since Stage A verified, and that must be understood BEFORE
-- removing their ability to resolve names -- otherwise this statement hides a
-- real grant behind a schema-level block instead of removing it.
select table_name, grantee, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('anon', 'authenticated')
order by 1, 2, 3;

-- ── SECTION 2: THE FIX -- NOT RUN. Uncomment only after 0 and 1 reviewed ──
-- One statement. Rollback above should already be open in another tab.

-- revoke usage on schema public from anon, authenticated;

-- ── SECTION 3: VERIFY -- in this order, immediately after Section 2 ──────
--
-- 3a. Re-run Section 0's query. Expect ZERO rows.
select n.nspname                     as schema,
       acl.grantee::regrole::text    as grantee,
       acl.privilege_type
from pg_namespace n
cross join lateral aclexplode(n.nspacl) as acl
where n.nspname = 'public'
  and acl.grantee::regrole::text in ('anon', 'authenticated')
order by 2, 3;

-- 3b. NOT SQL -- do this outside the editor, and do it second, not last.
-- A real read through the proxy, which runs as `service_role` and MUST be
-- unaffected:
--
--     curl -s -X POST https://sairn.vercel.app/api/sd-data \
--       -H "Authorization: Bearer DNT-PINNACLE-2026" \
--       -H "Content-Type: application/json" \
--       -d '{"resource":"dnt_patients","action":"read"}'
--
-- Expect HTTP 200 with real rows and `"provisioned":true`. A failure here is
-- the signal to run the rollback IMMEDIATELY -- it would mean this statement
-- reached a path it was not supposed to touch.
--
-- 3c. NOT SQL -- load the Supabase dashboard's table view for `public`.
-- This is the part no query can predict and the actual reason Stage B does not
-- share a run with anything else. If the dashboard cannot list tables, roll
-- back and record what broke; that is a finding worth more than the fix.

-- ── SECTION 4: AFTER BOTH STAGES PASS -- the Stage A cleanup ────────────
-- Stage A's Section 4 was held for this moment. Take the count reading FIRST,
-- then drop, then take it again:
--
--   select count(*) from information_schema.tables
--    where table_schema = 'public' and table_type = 'BASE TABLE';
--
--   drop table if exists public._anon_grant_baseline_2026_08_26;
--   drop table if exists public._anon_nontable_baseline_2026_08_26;
--
-- THIS SETTLES AN OPEN PREDICTION, so record both numbers. Stage A argued that
-- the Section 1 count drift (~158 -> 159 -> 160) was this sweep's own baseline
-- tables acquiring the default ACL, not the platform growing. The falsifiable
-- form: the table count must fall by EXACTLY 2 across those drops.
--
-- Corroborating figure, and a trap to avoid: the provisioning gap check
-- measured `live_total` 248 earlier on 2026-08-25; the supabase_admin
-- ownership check measured 251 today. 248 + 2 baselines + rf_settings
-- (genuinely new, from sairnroofing_settings_schema.sql) = 251. So the
-- post-drop count should be **249, not 248** -- anyone expecting a return to
-- 248 will read a correct result as a discrepancy.
