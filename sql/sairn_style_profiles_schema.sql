-- sql/sairn_style_profiles_schema.sql
--
-- NEXUS per-user style profile. ONE table, every app.
--
-- Design and the reasoning behind each decision:
--   docs/2026-09-02-nexus-style-profile-design.md
--
-- ── WHAT THIS IS, AND WHAT IT IS NOT ────────────────────────────────────────
-- It is OBSERVED. Every value is derived from how a person actually writes,
-- folded in one message at a time by api/_lib/style-profile.js.
--
-- It is NOT sd_employee_profiles, which that table's own header describes as
-- "a real, structured record a MANAGER sets deliberately". Declared intent and
-- observed behaviour are different things and both are useful; where they
-- disagree the manager's value wins, and renderStyleDirectives says so in the
-- prompt rather than silently picking one.
--
-- It is NOT sd_shared_knowledge, which is company-wide aggregate topic
-- frequency. This is per person.
--
-- ── NO RAW TEXT IS STORED, AND THAT IS ENFORCED BY SHAPE ────────────────────
-- `data` holds running counts and a bounded single-word term tally. There is no
-- column, and no key inside `data`, that a sentence could be reconstructed
-- from: word ORDER never leaves the browser. api/_lib/style-profile.test.js
-- asserts this against a sentence of deliberately rare words rather than
-- assuming it. The client analyses locally and posts the DELTA, so the user's
-- message text is never transmitted to this endpoint at all.
--
-- ── KEYING, AND THE HONEST LIMIT ON "SHARED" ────────────────────────────────
-- Keyed (license_hash, employee_id) -- the only identity a session token
-- carries. `app_id` is recorded and is deliberately NOT part of the key, so the
-- table is SHAPED for cross-app aggregation later.
--
-- But license_hash is per-app-LICENCE, so today the same human working in two
-- apps has two profiles. That is a real limit and is written here so nobody
-- reads "one shared table" as "one profile per person across the platform". The
-- only cross-app identity anchor on this platform is employees.customer_email,
-- which is not in the token; when a join for it exists, merging is a union over
-- these rows, not a migration of them.
--
-- ── SECURITY ────────────────────────────────────────────────────────────────
-- service_role only, RLS on with no anon policy, same as every other
-- SAIRN-owned table. api/sd-data.js is the only door, and a caller may only
-- ever read or write THEIR OWN profile -- employee_id is taken from the
-- verified session token, never from the request body. There is no
-- list-everyone action on purpose: how a colleague writes is not roster data,
-- and sd_employee_profiles already covers the manager-visible case.

create table if not exists public.sairn_style_profiles (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  employee_id   text not null,
  app_id        text not null,
  data          jsonb not null default '{}'::jsonb,
  samples       integer not null default 0,   -- mirrored out of data for cheap filtering
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_sairn_style_profiles_license
  on public.sairn_style_profiles (license_hash);
-- app_id is not part of the key but IS how a future cross-app rollup would
-- group, so it is indexed with the licence rather than alone.
create index if not exists idx_sairn_style_profiles_app
  on public.sairn_style_profiles (license_hash, app_id);

alter table public.sairn_style_profiles enable row level security;

grant select, insert, update on public.sairn_style_profiles to service_role;

-- ── VERIFY ──────────────────────────────────────────────────────────────────
select column_name, data_type, is_nullable
  from information_schema.columns
 where table_schema = 'public' and table_name = 'sairn_style_profiles'
 order by ordinal_position;
