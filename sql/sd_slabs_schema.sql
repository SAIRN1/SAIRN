-- sql/sd_slabs_schema.sql
-- RETROACTIVE DOCUMENTATION, added 2026-08-22 during StoneDesk Phase 1.
--
-- This table already exists in production and has since before the repo kept
-- SQL files per resource. It had no checked-in schema, so its shape and --
-- more importantly -- its 65536-byte CHECK constraint lived only inside a
-- comment in api/sd-data.js. That is the wrong place for a constraint that
-- has already caused one real failure, so it is written down here.
--
-- The column list below was read from Supabase information_schema on
-- 2026-08-22, not reconstructed from the API code. The two constraints are
-- documented from the code that enforces them plus an empirical rejection
-- (see below) rather than from pg_constraint.
--
-- `create table if not exists` is deliberate: running this against the live
-- database must be a no-op, not a redefinition. It exists so a fresh
-- environment can be stood up and so the constraint set is greppable.

create table if not exists public.sd_slabs (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'stonedesk',
  slab_id      text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, slab_id),
  constraint sdslabs_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sd_slabs_license on public.sd_slabs(license_hash);

alter table public.sd_slabs enable row level security;
drop policy if exists "svc only sd_slabs" on public.sd_slabs;
create policy "svc only sd_slabs" on public.sd_slabs for all using (false) with check (false);

grant select, insert, update, delete on public.sd_slabs to service_role;
revoke all on public.sd_slabs from anon, authenticated;

-- THE 64KB CEILING IS REAL AND IS NOT RAISABLE LOCALLY.
-- Recorded here because it has already been learned the expensive way once,
-- and because Phase 1b's design turns on it. On 2026-08-04, while building
-- the bulk slab photo upload, a slabs-specific 500KB override was added at
-- the API layer. It passed the API fine and was then rejected by Postgres
-- with a much less clear error -- the DB-level CHECK is the real ceiling and
-- there is no per-resource override at that layer. The fix lives client-side
-- instead: stonedesk.html's bsuCompressUnderBudget() downscales each photo to
-- BSU_PHOTO_BUDGET_BYTES (55KB) before it is ever sent.
--
-- Practical consequence, and the reason Phase 1b put block/bundle/history in
-- sibling tables rather than in this blob: 55KB of the 64KB budget is photo,
-- leaving roughly 9KB per slab for everything else. Unbounded per-slab
-- history in `data` would make a record more likely to fail the longer it is
-- used. See sql/sd_slab_lineage_schema.sql.

-- Verify after running (expect the real current row count, no error):
--   select count(*) from sd_slabs;
