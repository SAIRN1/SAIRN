-- sql/sd_hr_schema.sql
-- Durable storage for StoneDesk HR onboarding (stonedesk-hr.html)
--
-- WHY THIS EXISTS: the HR module shipped 2026-06-10 on commit ca55a7c and was
-- never merged. Its only persistence was two localStorage keys --
-- sd_hr_employees and sd_hr_certs -- which means every record lived in ONE
-- browser profile on ONE machine. Clearing site data, switching browsers, or
-- opening it on the shop iPad lost the lot, silently and with no error.
--
-- THAT IS A COMPLIANCE PROBLEM, NOT JUST AN INCONVENIENCE. One of the six
-- forms is a Crystalline Silica Hazard Communication & Training Record. OSHA's
-- respirable crystalline silica standard for general industry, 29 CFR
-- 1910.1053(k)(3), requires the employer to MAKE AND MAINTAIN a record of
-- employee training and to retain it -- a record held in one browser's
-- localStorage is not maintained in any sense an inspector would accept, and
-- its loss is undetectable until someone goes looking for it. sd_hr_certs is
-- the key that was carrying it.
--
-- TWO TABLES, NOT ONE, AND NOT A NESTED BLOB. localStorage stored
-- certifications as a nested object keyed employee -> cert type. Flattened
-- here to one ROW PER TRAINING EVENT, because that is what a retained record
-- is: each row carries its own trainer, date and recorded-at stamp, and adding
-- a second training for the same employee cannot overwrite the first by
-- accident the way a nested key assignment does.
--
-- CHECK 0e (pre-build duplication) RUN BEFORE WRITING THIS, not after: the
-- only existing sd_employee* tables are sd_employee_auth (PIN credentials) and
-- sd_employee_profiles (AI communication style -- experience level and tone).
-- Neither stores personnel or training records, and neither should: auth is a
-- credential table and profiles feeds the AI assistant. Confirmed by reading
-- api/_resources/stonedesk.js and sql/sd_employee_profiles_schema.sql, and by
-- grepping every sd_* schema file in this directory.
--
-- SESSION-GATED, MANAGEMENT-ONLY -- see api/sd-data.js's SD_HR branch. Unlike
-- the sd_slab_lineage tables (which are deliberately unauthenticated because
-- the slab record they describe is), this is personnel data: name, pay rate,
-- phone, email, and training history about identifiable people. It requires a
-- real StoneDesk session AND an owner/admin role, the same pair that already
-- gates the Grant/Revoke Sign-In Access cards.

create table if not exists public.sd_hr_employees (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  employee_key  text not null,   -- the module's own emp.id
  data          jsonb not null default '{}'::jsonb,  -- firstName, lastName, role, startDate, pay, status, phone, email, addedAt
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, employee_key),
  constraint sdhremp_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_hr_emp_license on public.sd_hr_employees(license_hash);

create table if not exists public.sd_hr_certs (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  cert_key      text not null,   -- employee_key || '::' || cert_type
  data          jsonb not null default '{}'::jsonb,  -- employee_key, cert_type, trainer, date, recordedAt
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, cert_key),
  constraint sdhrcert_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_hr_cert_license on public.sd_hr_certs(license_hash);

alter table public.sd_hr_employees enable row level security;
drop policy if exists "svc only sd_hr_employees" on public.sd_hr_employees;
create policy "svc only sd_hr_employees" on public.sd_hr_employees
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

alter table public.sd_hr_certs enable row level security;
drop policy if exists "svc only sd_hr_certs" on public.sd_hr_certs;
create policy "svc only sd_hr_certs" on public.sd_hr_certs
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
-- NO DELETE, deliberately, and for two independent reasons. (1) The platform
-- sweep sql/unused_delete_grant_revoke_2026-08-24.sql revoked service_role's
-- DELETE on 134 tables (verified 134 LOST / 0 GAINED); this file is
-- `create table if not exists` and safe to re-run, so granting delete here
-- would silently restore it. (2) A retained training record should not have a
-- reachable delete path at all -- removing an employee from the roster must
-- not take their silica training record with it.
grant select, insert, update on public.sd_hr_employees to service_role;
grant select, insert, update on public.sd_hr_certs to service_role;

-- ── VERIFY AFTER RUNNING, one step at a time ────────────────────────────────
-- Run these separately, not as one paste: the Supabase SQL editor reports
-- success for the statements it did run, so a partial apply is
-- indistinguishable from a full one from the outside (SAIRNroofing cleanup,
-- 2026-08-26).
--
-- 1. Both tables exist -- expect 2 rows:
--    select table_name from information_schema.tables
--    where table_schema='public' and table_name in ('sd_hr_employees','sd_hr_certs');
--
-- 2. Grants are exactly select/insert/update, NO delete -- expect 6 rows,
--    3 per table, and no row where privilege_type='DELETE':
--    select table_name, privilege_type from information_schema.role_table_grants
--    where table_schema='public' and grantee='service_role'
--      and table_name in ('sd_hr_employees','sd_hr_certs')
--    order by table_name, privilege_type;
--
-- 3. Then verify against the DEPLOYED endpoint, not by re-selecting -- a
--    select as owner reads fine on a table the app cannot reach:
--    curl -s -X POST https://sairn.vercel.app/api/sd-data \
--      -H 'Content-Type: application/json' \
--      -H 'Authorization: Bearer SD-PINNACLE-2026' \
--      -H 'X-SD-Auth: <a real owner/admin session token>' \
--      -d '{"action":"read","resource":"sd_hr_employees"}'
--
--    200 {"ok":true,"data":[],"provisioned":true}  -> this file has been run
--    200 {"ok":true,"data":[],"provisioned":false} -> NOT run yet
--    401 NO_SESSION / 403 FORBIDDEN                -> token missing or not owner/admin
