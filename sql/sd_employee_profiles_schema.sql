-- sql/sd_employee_profiles_schema.sql
-- StoneDesk per-employee AI personalization profile — Supabase schema
--
-- Run this once in the Supabase SQL editor before api/sd-data.js's
-- 'employee_profile' resource will work.
--
-- WHY THIS EXISTS, and how it differs from sd_shared_knowledge: shared
-- knowledge (sql/sd_shared_knowledge_schema.sql) is aggregate, inferred,
-- company-wide topic frequency -- nobody set it deliberately. This table
-- is the opposite: a real, structured record a MANAGER sets deliberately
-- per employee (experience level, preferred communication style), read
-- back to adjust the AI Assistant's tone for that specific person. The two
-- systems are complementary, not overlapping -- shared knowledge answers
-- "what does this shop talk about," this table answers "how should the AI
-- talk to THIS person."
--
-- KEYING: license_hash = sha256(license_key), same as every other
-- StoneDesk-owned table. Not customer_email-keyed (unlike the cross-app
-- `employees` table) -- this is StoneDesk-specific personalization data,
-- not shared HR data.
--
-- SECURITY MODEL: service-role only, RLS enabled with no anon policy.
-- api/sd-data.js is the only door in, and enforces at the application
-- layer that only an owner/admin session token may write or list every
-- profile -- any authenticated employee may only ever read their OWN
-- profile (derived server-side from their verified session token, never
-- a client-supplied employee_id on read).

create table if not exists public.sd_employee_profiles (
  id                   uuid primary key default gen_random_uuid(),
  license_hash         text not null,
  employee_id          text not null,
  experience_level     text not null default 'developing'
                         check (experience_level in ('new','developing','experienced','veteran')),
  communication_style  text not null default 'balanced'
                         check (communication_style in ('detailed','balanced','terse')),
  notes                text,
  updated_at           timestamptz not null default now(),
  unique (license_hash, employee_id),
  constraint sdempprof_notes_size check (notes is null or char_length(notes) <= 2000)
);
create index if not exists idx_sdempprof_license on public.sd_employee_profiles(license_hash);

alter table public.sd_employee_profiles enable row level security;
drop policy if exists "svc only sd_employee_profiles" on public.sd_employee_profiles;
create policy "svc only sd_employee_profiles" on public.sd_employee_profiles
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update, delete on public.sd_employee_profiles to service_role;
