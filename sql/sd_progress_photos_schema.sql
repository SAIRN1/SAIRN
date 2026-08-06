-- sql/sd_progress_photos_schema.sql
-- StoneDesk progress-report photos with AI scope analysis — Supabase schema
--
-- Run this once in the Supabase SQL editor before api/sd-sub-data.js's
-- 'progress_photos' resource will work.
--
-- WHAT THIS IS: a real, job-linked record of a progress photo plus Claude's
-- analysis of whether the work matches what was scoped -- captured by
-- either an employee or a subcontractor. Deliberately a real, reviewable
-- record (not a one-off chat response that vanishes after the interaction)
-- -- that's the whole point of the feature.
--
-- KEYING: license_hash = sha256(license_key), same as every other
-- StoneDesk-owned table. job_id ties it to a job but is NOT a foreign key
-- to a specific job table -- StoneDesk's job records live in several
-- different shapes across panels (Job Board, Field Map, Daily Logs), so
-- job_id here is a free-text/identifier match against whatever the caller
-- is using, same loose-coupling already used elsewhere in this file for
-- sd_sub_jobs.
--
-- captured_by_type distinguishes an employee submission from a
-- subcontractor submission -- captured_by_id is the employee_id or sub_id
-- from their own verified session token, never client-supplied (enforced
-- in api/sd-sub-data.js, same discipline as the existing 'jobs' resource's
-- sub-can-only-see-their-own-jobs rule).
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy.
-- api/sd-sub-data.js is the only door in.
--
-- SIZE CAP: reuses api/sd-sub-data.js's existing SUB_JOB_PAYLOAD_MAX_BYTES
-- (1.5MB) uniformly rather than a new one-off cap -- see that file's own
-- comment for why a compressed photo needs real headroom.

create table if not exists public.sd_progress_photos (
  id               uuid primary key default gen_random_uuid(),
  license_hash     text not null,
  job_id           text not null,
  captured_by_type text not null check (captured_by_type in ('employee','sub')),
  captured_by_id   text not null,
  data             jsonb not null default '{}'::jsonb,  -- photo_base64, scope_notes, ai_analysis, match_status
  created_at       timestamptz not null default now(),
  constraint sdprogphoto_data_size check (octet_length(data::text) <= 1572864)
);
create index if not exists idx_sdprogphoto_license_job on public.sd_progress_photos(license_hash, job_id);

alter table public.sd_progress_photos enable row level security;
drop policy if exists "svc only sd_progress_photos" on public.sd_progress_photos;
create policy "svc only sd_progress_photos" on public.sd_progress_photos
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update, delete on public.sd_progress_photos to service_role;
