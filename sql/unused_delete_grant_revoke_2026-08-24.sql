-- sql/unused_delete_grant_revoke_2026-08-24.sql
-- Revokes service_role's DELETE on every public table EXCEPT the SAIRNcode
-- sc_* family, which is the only app with a real, reachable delete path.
--
-- Same three-section shape as sql/full_crud_truncate_sweep_2026-08-24.sql:
-- discover live, review, then fix. The table list is NEVER hand-written --
-- it is pulled from information_schema at run time, so a table added after
-- this file was written is still covered.
--
-- ── WHY ───────────────────────────────────────────────────────────────────
-- Exactly ONE piece of code in the entire repo issues a DELETE:
-- api/sd-data.js, inside the SC_RESOURCES branch (line 5029 as of
-- 2026-08-25 -- the line number drifts as that file grows, the branch
-- does not; it was 4980 when this file was first written), gated by a
-- server-side re-check that the caller holds a valid SAIRNcode *admin*
-- session (a forged client claim of admin-ness is rejected there). Verified
-- by grepping every .js/.cjs/.mjs/.ts/.html in the repo, not just api/ --
-- one hit, no others.
--
-- Every other table's DELETE grant is a default copied forward through
-- schema files. Nothing built or planned needs it:
--   * erroneous-entry correction -> upsert on (license_hash, <entry>_id),
--     which is how every sd_*/grd_*/msb_* resource already works
--   * job/appointment cancellation -> a status ('Cancelled', 'INACTIVE'),
--     because a cancelled job you cannot see is indistinguishable from one
--     that never existed
--   * GDPR erasure -> the platform's own design (SAIRNcare) KEEPS the
--     identifier plus a suppression flag and reason code and deletes the
--     surrounding personal data. That is field-level redaction inside a
--     retained row -- an UPDATE, not a DELETE. These tables hold stone
--     inventory, landscaping jobs and beverage sales, not the personal-data
--     surface an erasure request targets anyway.
--
-- The grant is also the ONLY layer here. Every one of these tables has RLS
-- `for all using (false) with check (false)`, and service_role bypasses RLS
-- entirely -- so the grant is the sole thing between a leaked service key,
-- or a future coding mistake, and irreversible row loss.
--
-- One table makes the contradiction explicit: sd_slab_history is documented
-- in sql/sd_slab_lineage_schema.sql as "one row per event, append-only in
-- practice" and is granted DELETE. That is the provenance trail someone
-- reads when auditing a high-value slab.
--
-- ── NOTHING INTERNAL RELIES ON THIS, CHECKED NOT ASSUMED ──────────────────
-- The cleanup scripts that DO issue real deletes against in-scope tables
-- (sql/rbac_test_artifact_cleanup.sql -> msb_sales, grd_progress_photos;
-- sairndesign_*_cleanup.sql; sairncash_verification_trial_cleanup.sql;
-- sairndental_credentials_verify_cleanup.sql) run in the Supabase SQL
-- editor as the owner role, NOT as service_role. rbac_test_artifact_cleanup
-- says so in its own header: "This needs direct Supabase access -- same
-- hand-off as every other provisioning/schema step." Revoking service_role's
-- DELETE does not affect them. Neither Vercel cron
-- (/api/sairndental/send-reminder, /api/alf-alerts) deletes anything.
--
-- ── REVERSAL ──────────────────────────────────────────────────────────────
-- One line per table: GRANT DELETE ON public.<t> TO service_role.
-- This does NOT foreclose the deferred test/demo-data cleanup capability in
-- SAIRN-BACKLOG.md -- that item is explicitly undecided between soft- and
-- hard-delete. Revoking forces the decision to be made deliberately rather
-- than inherited from a copied grant.

-- ── SECTION 1: DISCOVER -- run this first, review the real output ─────────
-- Every table service_role can DELETE from that is NOT SAIRNcode's.
-- These are the rows Section 2 will change.

select
  t.table_name,
  string_agg(distinct g.privilege_type, ', ' order by g.privilege_type) as current_privs
from information_schema.tables t
join information_schema.role_table_grants g
  on g.table_name = t.table_name and g.table_schema = t.table_schema
where t.table_schema = 'public'
  and g.grantee = 'service_role'
  and t.table_name not like 'sc\_%'
group by t.table_name
having bool_or(g.privilege_type = 'DELETE')
order by t.table_name;

-- Sanity counterpart -- the sc_* tables that must be LEFT ALONE.
-- Expect the SAIRNcode family here, and expect Section 2 not to touch them.
--
-- select t.table_name
-- from information_schema.tables t
-- join information_schema.role_table_grants g
--   on g.table_name = t.table_name and g.table_schema = t.table_schema
-- where t.table_schema = 'public' and g.grantee = 'service_role'
--   and t.table_name like 'sc\_%'
-- group by t.table_name
-- having bool_or(g.privilege_type = 'DELETE')
-- order by t.table_name;

-- ── SECTION 2: DRAFT FIX -- NOT RUN. Review Section 1's real output first. ──
-- Revoke-then-grant, so nothing regresses: strips ALL of service_role's
-- privileges on the table, then re-grants exactly whichever of
-- SELECT/INSERT/UPDATE it already held -- never more, never fewer, and
-- never DELETE. A table that somehow held only DELETE ends with no grant,
-- which is reported rather than silently done.
--
-- Excludes sc_* by the same pattern Section 1 uses, so the 29 SAIRNcode
-- grants are untouched. Idempotent and safe to re-run. Touches no row data.
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
--     WHERE t.table_schema = 'public'
--       AND g.grantee = 'service_role'
--       AND t.table_name NOT LIKE 'sc\_%'
--     GROUP BY t.table_name
--     HAVING bool_or(g.privilege_type = 'DELETE')
--   LOOP
--     SELECT string_agg(priv, ', ') INTO keep_privs
--     FROM unnest(string_to_array(r.all_privs, ', ')) AS priv
--     WHERE priv IN ('SELECT', 'INSERT', 'UPDATE');
--
--     EXECUTE format('REVOKE ALL ON public.%I FROM service_role', r.table_name);
--     IF keep_privs IS NOT NULL THEN
--       EXECUTE format('GRANT %s ON public.%I TO service_role', keep_privs, r.table_name);
--     END IF;
--
--     RAISE NOTICE 'Revoked DELETE on %: kept %', r.table_name,
--       coalesce(keep_privs, '(nothing -- this table held ONLY DELETE, check it)');
--   END LOOP;
-- END $$;

-- ── SECTION 3: VERIFY, after Section 2 is actually run ───────────────────
-- Re-run SECTION 1. Expect ZERO rows.
--
-- And confirm SAIRNcode was untouched -- expect its full family back,
-- every row still showing DELETE:
--
-- select t.table_name,
--        string_agg(distinct g.privilege_type, ', ' order by g.privilege_type) as privs
-- from information_schema.tables t
-- join information_schema.role_table_grants g
--   on g.table_name = t.table_name and g.table_schema = t.table_schema
-- where t.table_schema = 'public' and g.grantee = 'service_role'
--   and t.table_name like 'sc\_%'
-- group by t.table_name
-- having bool_or(g.privilege_type = 'DELETE')
-- order by t.table_name;
--
-- Then confirm the app still works where it must: SAIRNcode's delete path
-- (api/sd-data.js SC_RESOURCES branch, admin session) must still succeed,
-- and a normal read/write round-trip on any sd_*/grd_*/dnt_* resource must
-- still succeed. A 403 from PostgREST on a WRITE would mean the re-grant
-- dropped a privilege -- that is what Section 2's keep_privs exists to
-- prevent, and what this check exists to catch if it failed anyway.

-- ── WHAT THIS DOES NOT COVER ──────────────────────────────────────────────
-- * The `anon` and `authenticated` roles. This file only touches
--   service_role. Those roles are locked out by RLS on these tables, but
--   their grants were not audited here.
-- * Schemas other than public.
-- * The DEFAULT PRIVILEGES that made this recur -- a new table created by a
--   schema file that copies the usual `grant select, insert, update, delete`
--   line will reintroduce a DELETE grant. The durable fix is to stop writing
--   `delete` into new schema files; this sweep only cleans what exists now.
