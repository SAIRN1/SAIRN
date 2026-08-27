-- sql/sairnsenior_settings_schema.sql
-- SAIRNsenior agency-level settings. 2026-08-27.
--
-- Run this once in the Supabase SQL editor before api/sd-data.js's sen_settings
-- read/write branch will work. Until it runs, both return a clear 503
-- NOT_PROVISIONED rather than a generic 500.
--
-- ── WHY THIS TABLE EXISTS: A LIVE COMPLIANCE GAP, NOT A FEATURE REQUEST ──
-- Found 2026-08-27 during the worldwide competitive-gap audit
-- (docs/superpowers/specs/2026-08-26-competitive-gap-audit-roofing-dental-senior.md
-- section 5.1). SAIRNsenior's EVV configuration and agency profile lived ONLY
-- in localStorage:
--
--   sairnsenior.html:1452  senAgency()      -> ld('sen_agency', ...)
--   sairnsenior.html:1461  saveAgency()     -> st('sen_agency', a)
--   sairnsenior.html:1470  rSettings()      -> ld('sen_evv_config', {})
--   sairnsenior.html:1476  saveEvvConfig()  -> st('sen_evv_config', cfg)
--
-- Electronic Visit Verification is federally mandated by the 21st Century Cures
-- Act, and the state/aggregator pair is the configuration that decides where a
-- visit record is supposed to go. Holding it device-local means it does not
-- survive a browser-data clear, does not follow the user to a second machine,
-- and cannot be seen by anyone else at the agency -- while the Settings panel
-- reports it as saved. That is the same shape as SAIRNcare's alf_facility
-- finding (2026-08-21): a licensed-operator legal fact held in localStorage.
--
-- This migration closes the STORAGE half only. It does NOT make SAIRNsenior
-- transmit anything to any aggregator -- see the honesty note below, which is
-- the whole reason that distinction is written into the table.
--
-- ── KEYED ROWS, COPIED FROM rf_settings ──────────────────────────────────
-- Same shape as sql/sairnroofing_settings_schema.sql (2026-08-26), deliberately
-- and not re-derived: one row per setting_key, so this is the LAST settings
-- migration SAIRNsenior needs. Two keys ship today:
--
--   'agency_profile' -> { "agency_name": "...", "demo_company": "..." }
--   'evv_config'     -> { "state": "OH", "aggregator": "sandata" }
--
-- ── WHAT evv_config DOES AND DOES NOT MEAN ───────────────────────────────
-- STATED IN THE SCHEMA ON PURPOSE, because a column named `aggregator` reads
-- like an integration and is not one: storing 'sandata' here records WHICH
-- aggregator this agency is required to submit to. It does not submit anything.
-- SAIRNsenior has no transmission path to Sandata, HHAeXchange, Tellus or
-- CareBridge. Building that is a separate, scoped feature. Until it exists, this
-- row is a stated intent, and the UI must say so rather than implying a live
-- connection.
--
-- FORMAT NOTE CORRECTED 2026-08-27 (comment only -- no DDL changed; this file has
-- already been run). The original said "Sandata JSON over SFTP/REST,
-- HHAeXchange flat-file, Tellus/Netsmart XML -- vendor-documented, not verified
-- against primary state-Medicaid text". All three parts were wrong or imprecise:
--   * Sandata altEVV is REST/JSON ONLY for third-party visit submission. SFTP
--     exists elsewhere in the OpenEVV family but not for this.
--   * HHAeXchange is not one format but THREE live interfaces -- REST/JSON,
--     a V5 CSV flat file over SFTP, and SOAP for Texas -- split by state.
--   * The formats are NOT merely vendor-documented. Eight of nine families have
--     public specifications, most published by state Medicaid agencies.
-- Full verified picture, with per-claim source labels:
-- docs/superpowers/specs/2026-08-27-evv-transmission-groundwork.md
--
-- One finding there matters more than any format detail and should be read
-- before transmission is designed: WASHINGTON HAS NO AGGREGATOR. EVV elements
-- ride on the claim into ProviderOne. A model assuming every state has an
-- endpoint to POST to needs surgery, not configuration, to serve it.
--
-- ── GRANTS: NO DELETE, DELIBERATELY ──────────────────────────────────────
-- A setting is overwritten, never removed. `revoke all` first then grant, per
-- sql/append_only_grant_audit.sql -- the leading revoke is what strips the
-- default-ACL TRUNCATE/REFERENCES/TRIGGER, and TRUNCATE on a compliance-config
-- table would silently erase every agency's EVV state at once. Matches the
-- rf_settings sibling and the platform-wide 2026-08-24/25 sweeps. Do NOT
-- re-add `delete` here when fixing a missing grant.

create table if not exists public.sen_settings (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnsenior',
  setting_key  text not null,                       -- 'agency_profile', 'evv_config', and whatever comes next
  data         jsonb not null default '{}'::jsonb,
  updated_by   text,                                -- employee_id, set SERVER-side from the verified
                                                    -- session, never from the client payload
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, setting_key),
  constraint senset_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_senset_license on public.sen_settings(license_hash);

alter table public.sen_settings enable row level security;
drop policy if exists "svc only sen_settings" on public.sen_settings;
create policy "svc only sen_settings" on public.sen_settings
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

revoke all on public.sen_settings from service_role;
grant select, insert, update on public.sen_settings to service_role;
revoke all on public.sen_settings from anon, authenticated;

-- Verify after running:
--   select count(*) from sen_settings;   -- expect 0 (empty table, no error)
--
-- Confirm the grants (expect exactly INSERT, SELECT, UPDATE -- no DELETE, no
-- TRUNCATE, no REFERENCES):
--   select string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name = 'sen_settings';
--
-- Confirm anon and authenticated hold NOTHING (expect zero rows) -- this table
-- carries an agency's compliance configuration and the publishable key is
-- public by design:
--   select grantee, privilege_type
--     from information_schema.role_table_grants
--    where table_schema = 'public' and table_name = 'sen_settings'
--      and grantee in ('anon','authenticated');
--
-- Then confirm live, which is the real proof -- a clean SQL run is not evidence
-- the app can reach it:
--   POST /api/sd-data {"action":"read","resource":"sen_settings","app_id":"sairnsenior"}
--   with a valid SEN- licence and an employee session. 503 NOT_PROVISIONED
--   means this file has not run; 200 with an empty list means it has.
