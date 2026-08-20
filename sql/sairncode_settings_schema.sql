-- sql/sairncode_settings_schema.sql
-- Per-practice settings for SAIRNcode. Currently holds exactly one thing:
-- the practice's data-retention policy setting (firewall audit layer 26).
-- Run this once in the Supabase SQL editor before api/sd-data.js's
-- sc_settings read/write branch will work.
--
-- ── READ THIS BEFORE ASSUMING THIS TABLE DELETES ANYTHING ──
-- IT DOES NOT. Nothing in SAIRNcode purges, expires, or deletes records on a
-- schedule today, and this table does not change that. It records the
-- practice's stated retention POLICY so that a future, separately-designed
-- purge mechanism has a real per-practice value to act on. Deliberate
-- decision (Michael, 2026-08-20): scope the setting, leave the delete
-- unwired until a real written retention policy exists on its own track.
--
-- Wiring a purge to a setting nobody has written a policy for would be the
-- most destructive possible version of the fabrication problem this codebase
-- has spent weeks removing -- a number in a box silently deleting real
-- medical billing records. The UI says plainly that no automatic deletion
-- happens, so a practice cannot read the setting as coverage it does not have.
--
-- ── THE 10-YEAR FLOOR ──
-- retention_years may not be set below 10, enforced SERVER-SIDE in
-- api/sd-data.js's sc_settings write branch (not just in the UI, which is a
-- convenience). The floor matters precisely BECAUSE the purge is not built
-- yet: a tampered or mistaken value written today would be inherited by
-- whatever purge is built later and could delete records years early. A
-- policy value that will one day drive irreversible deletion has to be
-- validated where the client cannot reach it. 'indefinite' is also valid and
-- means exactly what it says -- never purge.
--
-- Same shape as every other sc_* resource, so it rides the existing generic
-- SC_RESOURCES handler with no bespoke read path. entry_id is always the
-- literal 'default' -- one settings row per license.

create table if not exists public.sc_settings (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_settings_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sc_settings_license on public.sc_settings(license_hash);

alter table public.sc_settings enable row level security;
drop policy if exists "svc only sc_settings" on public.sc_settings;
create policy "svc only sc_settings" on public.sc_settings for all using (false) with check (false);

grant select, insert, update, delete on public.sc_settings to service_role;
revoke all on public.sc_settings from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sc_settings;
