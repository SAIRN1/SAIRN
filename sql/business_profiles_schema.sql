-- sql/business_profiles_schema.sql
-- The migration file for public.business_profiles, written 2026-08-26.
--
-- ══ THIS TABLE HAS BEEN LIVE IN PRODUCTION SINCE LONG BEFORE THIS FILE ═════
-- This is NOT a new table. `business_profiles` has been serving every
-- StoneDesk profile read and write for months with no migration file anywhere
-- in the repo. It was found on 2026-08-25 from two directions at once: Cody
-- reached it from the code side (the registered resource `profile` has no
-- same-named table, and `grep -rl "create table.*business_profiles" sql/`
-- returned nothing), and it came back as one of the 25 `live_but_not_declared`
-- rows from sql/provisioning_gap_check_2026-08-25.sql. A rebuild from sql/
-- alone would have silently omitted the table StoneDesk's profile path
-- depends on entirely.
--
-- EVERY COLUMN, CONSTRAINT AND INDEX BELOW WAS READ OUT OF THE LIVE DATABASE
-- via sql/introspect_undeclared_tables_2026-08-26.sql on 2026-08-26 -- not
-- inferred from the code. The code-side prediction recorded in that file got
-- the shape right and the surface wrong: it named license_hash, app_id, data,
-- shop_id and updated_at, and correctly derived UNIQUE(license_hash, app_id)
-- from `?on_conflict=license_hash,app_id` at api/sd-data.js:288 -- but it had
-- no way to see `id`, `created_at`, the defaults, or the size CHECK. That gap
-- is exactly why this file was not written from the code.
--
-- Safe to re-run: `create table if not exists`, and every constraint, index
-- and policy below is guarded. See the DISCLOSED FINDINGS section for the one
-- statement in this file that is NOT inert.
--
-- ══ DISCLOSED FINDING -- anon/authenticated hold TRUNCATE, and this file's ══
-- ══ revoke line is the ONLY statement here that changes live state ═════════
-- Live grants as introspected 2026-08-26:
--     service_role   INSERT, SELECT, UPDATE          <- correct, no DELETE
--     anon           TRUNCATE, REFERENCES, TRIGGER   <- default-ACL baseline
--     authenticated  TRUNCATE, REFERENCES, TRIGGER   <- default-ACL baseline
--
-- service_role is already correct: it holds no DELETE, so this table was NOT
-- missed by the 2026-08-25 DELETE sweep. The anon/authenticated verbs are the
-- Supabase default-ACL baseline that `sql/append_only_grant_audit.sql` and the
-- 2026-08-24 TRUNCATE sweep removed elsewhere -- this table was never in scope
-- for either run, because neither could see a table with no schema file. That
-- is the same blind spot this whole file exists to close, showing up one level
-- down.
--
-- The `revoke all ... from anon, authenticated` line below is written in
-- because it is the house idiom (see sql/sairnroofing_billing_schema.sql, the
-- newest schema file on the platform) and because a table re-provisioned from
-- this file should not inherit the problem going forward. But it is called out
-- here rather than buried: on the EXISTING live table it is not a no-op, it
-- removes privileges that are there right now. Whether to run it against live
-- is a scope decision for the platform-wide privilege work, NOT a decision
-- this migration makes on its own. Run the file without that line if you want
-- the declaration without the change; the table is fully described either way.
--
-- ══ ONE MORE THING WORTH KNOWING BEFORE ANYONE EDITS THIS ══════════════════
-- `shop_id` defaults to `(gen_random_uuid())::text`, so a profile row invents
-- its own shop identity on insert if the caller does not supply one -- and
-- api/sd-data.js's profile write does not supply one (:288). ai_memories then
-- reads that shop_id back to stamp memories (:303-:317). Changing this default
-- would silently re-parent existing memories.

--
-- ══ TWO SMALL THINGS THAT ARE INFERRED, NOT REPORTED -- stated so they can be ══
-- ══ checked rather than trusted ════════════════════════════════════════════
-- 1. `default gen_random_uuid()` on the primary key. The introspection summary
--    gave the column as `id uuid pk` without quoting its default. The default
--    is inferred, and inferred on solid ground: no writer on any path sends
--    `id`, and every insert succeeds, which cannot both be true unless the
--    column defaults server-side. Confirm against section 1's `column_default`
--    and correct this line if it differs -- the database wins.
-- 2. The CHECK constraint NAME below is this file's own, since the summary
--    reported the constraint's definition rather than its identifier. That is
--    harmless by construction: the guard around it matches on the definition,
--    not the name, so re-running cannot duplicate an existing differently-named
--    constraint. A fresh provision simply gets this name.

-- ---------------------------------------------------------------------------
-- 1. Table
-- ---------------------------------------------------------------------------
create table if not exists public.business_profiles (
  id           uuid        primary key default gen_random_uuid(),
  license_hash text        not null,
  app_id       text        not null default 'stonedesk',
  -- Self-assigning; see the note above before changing this default.
  shop_id      text        not null default (gen_random_uuid())::text,
  data         jsonb       not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- 2. Constraints
-- ---------------------------------------------------------------------------
-- UNIQUE(license_hash, app_id) is load-bearing, not decorative: the profile
-- write at api/sd-data.js:288 posts with
-- `?on_conflict=license_hash,app_id` and `Prefer: resolution=merge-duplicates`.
-- Without this constraint that request fails outright -- it does not silently
-- insert a duplicate.
do $$
begin
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.business_profiles'::regclass
       and contype  = 'u'
       and pg_get_constraintdef(oid) = 'UNIQUE (license_hash, app_id)'
  ) then
    alter table public.business_profiles
      add constraint business_profiles_license_hash_app_id_key
      unique (license_hash, app_id);
  end if;
end $$;

-- 64 KB ceiling on the JSON payload. Same bound as every other data-carrying
-- table on the platform, and the same one MAX_PAYLOAD_BYTES enforces in
-- api/_lib/sd-store.js -- the app-side check and this one must move together.
do $$
begin
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.business_profiles'::regclass
       and contype  = 'c'
       and pg_get_constraintdef(oid) like '%65536%'
  ) then
    alter table public.business_profiles
      add constraint business_profiles_data_size
      check (octet_length(data::text) <= 65536);
  end if;
end $$;

-- ---------------------------------------------------------------------------
-- 3. Indexes
-- ---------------------------------------------------------------------------
-- The primary key and the unique constraint bring their own indexes. This is
-- the third one that exists live and would otherwise be lost in a rebuild --
-- it backs the license_hash-only lookups in api/_lib/sd-store.js:84 and
-- api/sd-data.js:315, which do not filter on app_id.
create index if not exists idx_bp_license
  on public.business_profiles (license_hash);

-- ---------------------------------------------------------------------------
-- 4. RLS -- service-role only
-- ---------------------------------------------------------------------------
alter table public.business_profiles enable row level security;
drop policy if exists "svc only business_profiles" on public.business_profiles;
create policy "svc only business_profiles" on public.business_profiles
  for all using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

-- ---------------------------------------------------------------------------
-- 5. Grants -- revoke first, then grant only the verbs the code uses
-- ---------------------------------------------------------------------------
-- `revoke all` before `grant` is the platform idiom for a reason recorded in
-- sql/append_only_grant_audit.sql: ALTER DEFAULT PRIVILEGES in this project
-- grants service_role a baseline on every new relation in public, so a bare
-- `grant select, insert` never describes the real end state. Revoking first
-- makes the grant line authoritative.
--
-- Verbs: SELECT, INSERT, UPDATE. No DELETE -- api/sd-data.js's profile branch
-- implements read and write only, and the platform's sole reachable delete
-- path is the SC_RESOURCES (SAIRNcode) branch. Do NOT re-add `delete` here
-- when fixing a missing grant; that is precisely the 2026-08-06
-- overcorrection sql/sairnscape_data_schema.sql documents against itself.
revoke all on public.business_profiles from service_role;
grant select, insert, update on public.business_profiles to service_role;

-- THE ONE NON-INERT STATEMENT IN THIS FILE. See DISCLOSED FINDING above.
-- On a fresh provision this is a no-op that keeps the default ACL out.
-- On the EXISTING live table it removes TRUNCATE/REFERENCES/TRIGGER that anon
-- and authenticated hold right now. Comment it out to declare without changing.
revoke all on public.business_profiles from anon, authenticated;

-- ---------------------------------------------------------------------------
-- 6. Verify after running
-- ---------------------------------------------------------------------------
--   select count(*) from public.business_profiles;
--     -- expect the real row count, NOT 0. This table has live data; if this
--     -- returns 0 you are not looking at the table this file describes.
--
--   select grantee, string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where table_schema = 'public' and table_name = 'business_profiles'
--    group by grantee order by grantee;
--     -- expect service_role -> INSERT, SELECT, UPDATE
--     -- and, if the anon/authenticated revoke was run, no other rows
--
--   select indexname from pg_indexes
--    where schemaname = 'public' and tablename = 'business_profiles'
--    order by indexname;
--     -- expect 3: the pkey, the unique constraint's index, and idx_bp_license
