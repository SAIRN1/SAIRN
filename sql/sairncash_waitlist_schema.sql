-- sql/sairncash_waitlist_schema.sql
-- Real backing table for SAIRNcash's pre-launch waitlist -- closes the
-- 2026-08-10 audit finding that handleWaitlist() showed a fabricated
-- success toast while discarding the submitted email entirely.
-- Run this in Supabase's SQL editor.
create table if not exists public.sairncash_waitlist (
  id         uuid primary key default gen_random_uuid(),
  email      text not null,
  created_at timestamptz not null default now(),
  unique (email)
);
alter table public.sairncash_waitlist enable row level security;
drop policy if exists "svc only sairncash_waitlist" on public.sairncash_waitlist;
create policy "svc only sairncash_waitlist" on public.sairncash_waitlist
  for all using (false) with check (false);
grant select, insert on public.sairncash_waitlist to service_role;

-- Verify after running:
--   select * from sairncash_waitlist limit 5;
-- should return 0 rows (empty table, no error).
