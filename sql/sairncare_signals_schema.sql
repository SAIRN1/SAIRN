-- sql/sairncare_signals_schema.sql
-- SAIRNcare alf_signals -- passive-monitoring signal log (Phase 0 item 3)
--
-- APPEND-ONLY, same shape as alf_mar's administration/count entry types:
-- a fresh id every time, never edited or deleted after the fact (server
-- rejects reusing an id -- see api/sd-data.js). No update/delete path
-- exists for this resource at all.
--
-- DELIBERATELY NO risk_score COLUMN AND NO DERIVED-SCORE FIELD OF ANY KIND.
-- No passive-monitoring device or integration is wired up anywhere in this
-- app yet (verified: zero matches for fall_signal/motion/wandering/vitals
-- in sairncare.html before this table was added) -- so there is no real
-- data to derive a score from, and adding one now would be exactly the
-- fabricated-KPI pattern sairn-guardian-v2 Check 0b exists to catch. The
-- read endpoint instead returns a {have, need} COVERAGE contract: have =
-- how many of the signal types this table is designed to hold actually
-- have at least one real row for this facility; need = the fixed count of
-- signal types this table supports (see ALF_SIGNAL_TYPES in api/sd-data.js).
-- Both numbers are computed live from real rows, never hardcoded. A future
-- derived view (an actual risk indicator) can be built once have > 0 for
-- enough types to mean something -- this table's job today is only to give
-- that future view somewhere real to read from.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.alf_signals (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairncare',
  entry_id      text not null,                 -- client-generated (SIG-<timestamp>)
  resident_id   text not null,                  -- references alf_clients.client_id
  signal_type   text not null,                  -- fall_detection | bed_exit | wandering_alert | activity_baseline
  data          jsonb not null default '{}'::jsonb,
  recorded_at   timestamptz not null default now(),  -- when the signal itself occurred
  created_at    timestamptz not null default now(),  -- when the row was written (append time)
  unique (license_hash, entry_id),
  constraint alfsig_signal_type_check check (signal_type in
    ('fall_detection','bed_exit','wandering_alert','activity_baseline')),
  constraint alfsig_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfsig_license on public.alf_signals(license_hash);
create index if not exists idx_alfsig_resident on public.alf_signals(license_hash, resident_id);
create index if not exists idx_alfsig_type on public.alf_signals(license_hash, signal_type);

grant select, insert on public.alf_signals to service_role;
revoke all on public.alf_signals from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from alf_signals;
