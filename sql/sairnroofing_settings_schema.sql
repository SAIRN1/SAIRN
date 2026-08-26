-- sql/sairnroofing_settings_schema.sql
-- SAIRNroofing company-level settings. 2026-08-26.
--
-- Run this once in the Supabase SQL editor before api/sd-data.js's rf_settings
-- read/write branch or rf_claims' 'assess_damage' action will work. Until it
-- runs, both return a clear 503 NOT_PROVISIONED rather than a generic 500.
--
-- ── WHY THIS TABLE EXISTS AT ALL ─────────────────────────────────────────
-- SAIRNroofing had NO company-level settings home. That was found the hard way
-- on 2026-08-26: the repair-vs-replace engine
-- (api/_lib/roofing-damage-assessment.js) needs a per-company damage threshold,
-- and the two tables that sounded like they might hold one do not. Recording
-- both so nobody re-proposes them:
--   rf_company_programs -- manufacturer certification programmes, typed to
--     manufacturer/program_name/status. Its validator rejects a threshold row.
--   rf_contingency_rules -- per-state rescission rules, typed to
--     state/trigger_event/count/unit with a required citation.
-- Neither is a generic settings store, and making either polymorphic to avoid
-- one small migration is the "second copy of something" pattern
-- sairn-guardian-v2's Eliminate Duplication at the Source section warns about.
--
-- ── KEYED ROWS, NOT ONE 'default' ROW ────────────────────────────────────
-- SAIRNcode's sc_settings uses a single row per practice. That works, but every
-- future company-level setting reopens the migration. Keyed rows make this the
-- LAST settings migration SAIRNroofing needs. Decided deliberately on the same
-- night eleven never-run migrations were found across the platform -- the fix
-- for that is fewer future migrations, not avoiding this one.
--
-- ── WHAT GOES IN data, FOR setting_key = 'damage_threshold' ──────────────
-- Per PERIL, because the numbers are genuinely different -- a hail threshold
-- and a wind-crease threshold are not the same figure and are never summed:
--
--   { "hail": { "hits_per_test_square": 8, "source": "Company standard, 2026 field manual p.14" },
--     "wind": { "hits_per_test_square": 3, "source": "Carrier bulletin 2026-03" } }
--
-- `source` is REQUIRED by the engine and enforced server-side, not here -- a
-- threshold with no traceable origin is indistinguishable from a guess once
-- whoever configured it has moved on, and this number decides whether a slope
-- is called total. NOTHING IS SEEDED. The widely-cited 8-hits-per-10x10-square
-- convention is a convention, not a law: it varies by carrier, state and
-- policy. Seeding it would put a number on screen with nothing real behind it,
-- which is exactly Guardian Check 0b. The contractor enters their own, citing
-- their own authority, or the engine refuses to assess.
--
-- ── GRANTS: NO DELETE, DELIBERATELY ──────────────────────────────────────
-- A setting is overwritten, never removed. `revoke all` first then grant, per
-- sql/append_only_grant_audit.sql, matching all nine rf_* siblings and the
-- platform-wide 2026-08-24/25 sweep. Do NOT re-add `delete` here when fixing a
-- missing grant.

create table if not exists public.rf_settings (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnroofing',
  setting_key  text not null,                       -- 'damage_threshold', and whatever comes next
  data         jsonb not null default '{}'::jsonb,
  updated_by   text,                                -- employee_id, set SERVER-side from the verified
                                                    -- session, never from the client payload
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, setting_key),
  constraint rfset_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_rfset_license on public.rf_settings(license_hash);

alter table public.rf_settings enable row level security;
drop policy if exists "svc only rf_settings" on public.rf_settings;
create policy "svc only rf_settings" on public.rf_settings
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

revoke all on public.rf_settings from service_role;
grant select, insert, update on public.rf_settings to service_role;
revoke all on public.rf_settings from anon, authenticated;

-- Verify after running:
--   select count(*) from rf_settings;   -- expect 0 (empty table, no error)
--
-- Confirm the grants (expect exactly INSERT, SELECT, UPDATE -- no DELETE, no
-- TRUNCATE, no REFERENCES):
--   select string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name = 'rf_settings';
--
-- Then confirm live, which is the real proof -- a clean SQL run is not
-- evidence the app can reach it:
--   POST /api/sd-data {"action":"read","resource":"rf_settings","app_id":"sairnroofing"}
--   with a valid RF- licence and an employee session. 503 NOT_PROVISIONED means
--   this file has not run; 200 with an empty list means it has.
