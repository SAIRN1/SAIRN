-- sql/full_crud_truncate_sweep_2026-08-24.sql
-- DIAGNOSTIC + DRAFT FIX ONLY. Nothing in this file has been run.
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
-- grep -n "^grant\|^revoke" across every sql/*.sql file (the same
-- structural technique that found the original 9 append-only tables,
-- extended to the whole platform rather than files tagged "append-only")
-- shows the SOUND `revoke all ... from service_role` pattern in exactly
-- 6 real schema files: sairncode_audit_log, stonedesk_audit_log, and this
-- session's own four SAIRNroofing schema files (already fixed tonight,
-- confirmed via `grep -l "revoke all.*from service_role" sql/*.sql`).
-- Every other schema file on the platform -- 151 of 158 total granted
-- tables, counted directly (`grep -rhE "^grant select" sql/*.sql | ...
-- sort -u | wc -l` = 158; the 6 sound files account for 7 of them) --
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
--     GROUP BY t.table_name
--     HAVING bool_or(g.privilege_type = 'TRUNCATE')
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
-- Re-run Section 1. Expect zero rows.

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
