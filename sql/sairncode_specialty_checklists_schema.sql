-- sql/sairncode_specialty_checklists_schema.sql
-- Real server-synced table for SAIRNcode's specialty documentation
-- checklists (2026-08-20, pre-SAIRNcare gap pass). Run this once in the
-- Supabase SQL editor before api/sd-data.js's sc_specialty_checklists
-- read/write/delete branch will work.
--
-- WHY THIS TABLE STARTS EMPTY, DELIBERATELY, WITH NO SEEDED CHECKLIST
-- ITEMS: same discipline as sql/sairncode_scrubrules_schema.sql. This
-- session has no live, authoritative per-specialty documentation-
-- requirement source to verify specific checklist items against.
-- Hardcoding even one plausible-sounding but unverified requirement into a
-- medical-billing compliance tool would be a real fabrication risk. A
-- coder or compliance admin populates this with requirements THEY have
-- personally verified, required Source field included so every item is
-- traceable -- not this app's own claim about what a specialty requires.
--
-- Same shape as every other sc_* resource: one row per entry, license_
-- hash-scoped, a jsonb data column. entry_id is the client's own locally-
-- generated id ('scl'+Date.now()).

create table if not exists public.sc_specialty_checklists (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_specialty_checklists_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sc_specialty_checklists_license on public.sc_specialty_checklists(license_hash);

alter table public.sc_specialty_checklists enable row level security;
drop policy if exists "svc only sc_specialty_checklists" on public.sc_specialty_checklists;
create policy "svc only sc_specialty_checklists" on public.sc_specialty_checklists for all using (false) with check (false);

grant select, insert, update, delete on public.sc_specialty_checklists to service_role;
revoke all on public.sc_specialty_checklists from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sc_specialty_checklists;
