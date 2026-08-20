-- sql/sairncode_specialty_checks_schema.sql
-- Real server-synced table for SAIRNcode's specialty spot-check harness
-- (2026-08-20, pre-SAIRNcare gap pass). Run this once in the Supabase SQL
-- editor before api/sd-data.js's sc_specialty_checks read/write/delete
-- branch will work.
--
-- WHY THIS EXISTS INSTEAD OF A CLAIMED COVERAGE VERDICT: this session
-- found zero real per-specialty coverage findings anywhere -- no repo
-- record, no credentialed coder's review. Manufacturing a "SAIRNcode
-- covers behavioral health" verdict from a couple of AI-answered questions
-- would repeat the exact AAPC-65%-score fabrication class this whole audit
-- arc exists to remove. This table stores the MECHANISM instead: a real
-- coder asks a real specialty question, reviews the AI's real answer, and
-- records THEIR OWN pass/fail/needs-review judgment. The verdict is never
-- computed or inferred by this app -- it is always a human's stated call.
--
-- Same shape as every other sc_* resource: one row per entry, license_
-- hash-scoped, a jsonb data column. entry_id is the client's own locally-
-- generated id ('spc'+Date.now()).

create table if not exists public.sc_specialty_checks (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_specialty_checks_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sc_specialty_checks_license on public.sc_specialty_checks(license_hash);

alter table public.sc_specialty_checks enable row level security;
drop policy if exists "svc only sc_specialty_checks" on public.sc_specialty_checks;
create policy "svc only sc_specialty_checks" on public.sc_specialty_checks for all using (false) with check (false);

grant select, insert, update, delete on public.sc_specialty_checks to service_role;
revoke all on public.sc_specialty_checks from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sc_specialty_checks;
