-- sql/sairnroofing_photos_schema.sql
-- SAIRNroofing measurement photos + Claude quantities read -- Supabase schema
--
-- Phase 2. Modelled directly on sql/sd_progress_photos_schema.sql -- same
-- reasoning: a real, job-linked, reviewable record of a photo plus the AI's
-- read of it, not a one-off chat response that vanishes.
--
-- WHY A SEPARATE TABLE FROM rf_jobs: rf_jobs.data is capped at 65536 bytes
-- (sql/sairnroofing_jobs_schema.sql) -- the right size for job fields, the
-- wrong shape for a photo. This table reuses the platform's existing 1.5MB
-- photo cap (sd_progress_photos' SUB_JOB_PAYLOAD_MAX_BYTES) rather than a
-- new one-off number.
--
-- captured_by is the employee_id from the caller's own verified session
-- token, never client-supplied -- same discipline as sd_progress_photos'
-- captured_by_id.
--
-- job_id is a free-text match against rf_jobs.job_id, not a DB foreign key
-- -- same loose coupling sd_progress_photos already uses for its job_id.
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy.
-- api/sd-data.js's rf_photos branch is the only door in, gated by the same
-- three-tier assignment rule as rf_jobs itself (see that branch's header).
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.rf_photos (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnroofing',
  job_id       text not null,
  captured_by  text not null,
  data         jsonb not null default '{}'::jsonb,  -- photo_base64, ai_analysis (raw
                                                       -- Claude text), parsed_quantities
  created_at   timestamptz not null default now(),
  constraint rfphotos_data_size check (octet_length(data::text) <= 1572864)
);

create index if not exists idx_rfphotos_license_job on public.rf_photos(license_hash, job_id);

alter table public.rf_photos enable row level security;
drop policy if exists "svc only rf_photos" on public.rf_photos;
create policy "svc only rf_photos" on public.rf_photos
  for all using (false) with check (false);

grant select, insert on public.rf_photos to service_role;
revoke all on public.rf_photos from anon, authenticated;
