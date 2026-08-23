-- sql/sairncare_all_remaining_migrations.sql
-- SAIRNcare: the TEN migrations that have never been run, combined into one paste.
--
-- WHY THIS FILE EXISTS. A full table listing of the live database on 2026-08-22
-- showed only FOUR alf_ tables present: alf_payer_rules, alf_claim_routes,
-- alf_compliance_rules, alf_staff_credentials. Those come from exactly two
-- migration files (sairncare_payer_rules_schema.sql and
-- sairncare_compliance_schema.sql). Every other SAIRNcare table -- residents,
-- staff, MAR, billing, incidents, activities, facility, signals, op audits, and
-- the employee-credentials table -- does not exist, because its migration was
-- never run.
--
-- THE CONSEQUENCE, stated plainly: there is NO generic fallback store. Every
-- handler in api/sd-data.js targets a literal same-named table
-- (rest('alf_clients?...') -> SUPABASE_URL + '/rest/v1/alf_clients'); there are
-- zero bridge_data references in sd-data.js and zero alf_ references in
-- bridge.js. So until this runs, resident records, medication administration,
-- and billing persist in ONE BROWSER'S localStorage and nowhere else.
--
-- The app degrades honestly rather than lying about it -- reads return
-- provisioned:false, writes return 503 NOT_PROVISIONED naming the missing SQL
-- file, and all 21 client write paths show "Saved on this device only -- server
-- sync failed" -- but that is a gap to close, not a state to leave.
--
-- SAFE TO RUN EVEN IF SOMETHING PARTIALLY LANDED. Every statement below is
-- idempotent as written in its source file: create table if not exists, create
-- index if not exists, alter ... enable row level security (a no-op when already
-- enabled), and drop policy if exists before create policy. Re-running changes
-- nothing that is already correct.
--
-- DDL BELOW IS COPIED VERBATIM FROM THE TEN SOURCE FILES BY SCRIPT, not
-- retyped, so a column, constraint or grant cannot be mistyped in transcription.
-- The per-file explanatory headers were trimmed for length; each source file
-- remains in the repo and is the place to read WHY a table is shaped the way it
-- is.
--
-- ORDER IS DEPENDENCY ORDER, not alphabetical.


-- =====================================================================
-- 1 of 10 -- sairncare_employee_auth_schema.sql
-- Employee credentials (RBAC). FIRST because nothing else works without login -- api/alf-auth.js bootstrap/login/setup all read this table.
-- =====================================================================

create table if not exists sairncare_employee_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text not null,
  display_name text,
  role text not null check (role in ('owner','nursing','med_aide','caregiver','billing','activities')),
  pin_hash text not null,
  pin_salt text not null,
  active boolean not null default true,
  failed_attempts integer not null default 0,
  locked_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_sairncare_employee_auth_license
  on sairncare_employee_auth (license_hash);

alter table sairncare_employee_auth enable row level security;
drop policy if exists "svc only sairncare_employee_auth" on sairncare_employee_auth;
create policy "svc only sairncare_employee_auth" on sairncare_employee_auth
  for all using (false) with check (false);

-- No DELETE grant, matching every other employee_auth table on this
-- platform -- deactivation is active=false, not a row delete.
grant select, insert, update on sairncare_employee_auth to service_role;
revoke all on sairncare_employee_auth from anon, authenticated;


-- =====================================================================
-- 2 of 10 -- sairncare_clients_schema.sql
-- Residents. The four-tier privacy gate in api/sd-data.js keys off this table's assigned_employee_id.
-- =====================================================================

create table if not exists public.alf_clients (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncare',
  client_id    text not null,                        -- client-generated id (RES-<timestamp>)
  assigned_employee_id text,                          -- null = unassigned, management-only-visible
  data         jsonb not null default '{}'::jsonb,    -- name, room, DOB, diagnosis, care_level,
                                                        -- payer_type, emergency_contact, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, client_id),
  constraint alfclients_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfclients_license on public.alf_clients(license_hash);
create index if not exists idx_alfclients_assignee on public.alf_clients(license_hash, assigned_employee_id);

grant select, insert, update on public.alf_clients to service_role;
revoke all on public.alf_clients from anon, authenticated;


-- =====================================================================
-- 3 of 10 -- sairncare_staff_schema.sql
-- Staff roster.
-- =====================================================================

create table if not exists public.alf_staff (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncare',
  staff_id     text not null,                        -- client-generated id (ST-<timestamp>)
  data         jsonb not null default '{}'::jsonb,    -- name, phone, position, cert_expiry,
                                                        -- bgcheck_date, status, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, staff_id),
  constraint alfstaff_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfstaff_license on public.alf_staff(license_hash);

-- ---------------------------------------------------------------------------
-- GRANTS -- explicit up front, same reasoning as every other data table's
-- own header this session.
grant select, insert, update on public.alf_staff to service_role;
revoke all on public.alf_staff from anon, authenticated;


-- =====================================================================
-- 4 of 10 -- sairncare_mar_schema.sql
-- Medication Administration Record. Referenced by alf_clients for the live assignment lookup.
-- =====================================================================

create table if not exists public.alf_mar (
  id                    uuid primary key default gen_random_uuid(),
  license_hash          text not null,
  app_id                text not null default 'sairncare',
  entry_id              text not null,                 -- client-generated (MAR-<timestamp> or a
                                                          -- stable medication id for medication_order)
  resident_id           text not null,                  -- references alf_clients.client_id
  assigned_employee_id  text,                            -- denormalized from alf_clients at write
                                                          -- time (live-looked-up, never trusted from
                                                          -- the client) -- null = resident unassigned
  entry_type            text not null,                   -- medication_order | administration | count |
                                                          -- reconciliation | assessment_refusal
  data                  jsonb not null default '{}'::jsonb,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint alfmar_entry_type_check check (entry_type in
    ('medication_order','administration','count','reconciliation','assessment_refusal')),
  constraint alfmar_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfmar_license on public.alf_mar(license_hash);
create index if not exists idx_alfmar_resident on public.alf_mar(license_hash, resident_id);
create index if not exists idx_alfmar_assignee on public.alf_mar(license_hash, assigned_employee_id);

grant select, insert, update on public.alf_mar to service_role;
revoke all on public.alf_mar from anon, authenticated;


-- =====================================================================
-- 5 of 10 -- sairncare_billing_schema.sql
-- Billing / invoices.
-- =====================================================================

create table if not exists public.alf_billing (
  id                    uuid primary key default gen_random_uuid(),
  license_hash          text not null,
  app_id                text not null default 'sairncare',
  entry_id              text not null,                 -- stable per resident+month
                                                          -- (INV-<resident_id>-<YYYY-MM>) so
                                                          -- regenerating a month's invoice
                                                          -- corrects it in place, real mutable
                                                          -- record, not an append-only log.
  resident_id           text not null,                  -- references alf_clients.client_id
  data                  jsonb not null default '{}'::jsonb,    -- month, room_board_amount,
                                                          -- care_amount, private_total,
                                                          -- private_status, hcbs_claim_amount,
                                                          -- hcbs_status, generated_by, notes
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint alfbilling_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfbilling_license on public.alf_billing(license_hash);
create index if not exists idx_alfbilling_resident on public.alf_billing(license_hash, resident_id);

grant select, insert, update on public.alf_billing to service_role;
revoke all on public.alf_billing from anon, authenticated;


-- =====================================================================
-- 6 of 10 -- sairncare_incidents_schema.sql
-- Compliance incident reports.
-- =====================================================================

create table if not exists public.alf_incidents (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncare',
  entry_id     text not null,                        -- client-generated (INC-<timestamp>)
  resident_id  text,                                  -- nullable -- not every incident involves
                                                        -- a specific resident (e.g. a facility or
                                                        -- staff-safety event)
  data         jsonb not null default '{}'::jsonb,    -- category, date, time, description,
                                                        -- severity, reported_by, residents_involved,
                                                        -- action_taken, status, state_reported,
                                                        -- state_reported_date, state_reported_method,
                                                        -- follow_up_notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint alfincidents_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfincidents_license on public.alf_incidents(license_hash);

grant select, insert, update on public.alf_incidents to service_role;
revoke all on public.alf_incidents from anon, authenticated;


-- =====================================================================
-- 7 of 10 -- sairncare_activities_schema.sql
-- Activities calendar.
-- =====================================================================

create table if not exists public.alf_activities (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncare',
  entry_id     text not null,                        -- client-generated (ACT-<timestamp>)
  data         jsonb not null default '{}'::jsonb,    -- name, category, date, time, description,
                                                        -- created_by, attendees (array of resident_id)
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint alfactivities_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfactivities_license on public.alf_activities(license_hash);

grant select, insert, update on public.alf_activities to service_role;
revoke all on public.alf_activities from anon, authenticated;


-- =====================================================================
-- 8 of 10 -- sairncare_facility_schema.sql
-- Facility profile + licensing jurisdiction + rate card + alert policy.
-- =====================================================================

create table if not exists public.alf_facility (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncare',
  facility_id  text not null,                        -- 'FAC-DEFAULT' for single-facility operators
  data         jsonb not null default '{}'::jsonb,   -- name, company, licensing_state, license_number,
                                                     -- cs_policy, incident_deadline, and the rate card
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, facility_id),
  constraint alffacility_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alffacility_license on public.alf_facility(license_hash);

grant select, insert, update on public.alf_facility to service_role;
revoke all on public.alf_facility from anon, authenticated;


-- =====================================================================
-- 9 of 10 -- sairncare_signals_schema.sql
-- Passive-monitoring signal log (Phase 0 item 3).
-- =====================================================================

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


-- =====================================================================
-- 10 of 10 -- sairncare_op_audit_schema.sql
-- Operational audit: food safety, sanitation, emergency drills (Phase 3 item 5).
-- =====================================================================

create table if not exists public.alf_op_audits (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairncare',
  entry_id      text not null,                  -- client-generated (OPA-<timestamp>)
  record_type   text not null,                   -- food_temp | sanitation | emergency_drill
  -- Denormalised so the compliance view can filter without unpacking jsonb.
  observed_on   date,
  passed        boolean,                         -- null = not evaluated against a threshold
  data          jsonb not null default '{}'::jsonb,
  recorded_by   text,                            -- server-stamped from the real session
  -- Sign-off is deliberately separate from recording: the person who takes the
  -- reading is not the person who attests the log was reviewed.
  reviewed_by   text,
  reviewed_at   timestamptz,
  created_at    timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint alfopa_type_check check (record_type in ('food_temp','sanitation','emergency_drill')),
  constraint alfopa_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfopa_license on public.alf_op_audits(license_hash);
create index if not exists idx_alfopa_type on public.alf_op_audits(license_hash, record_type);
create index if not exists idx_alfopa_date on public.alf_op_audits(license_hash, observed_on);

grant select, insert, update on public.alf_op_audits to service_role;
revoke all on public.alf_op_audits from anon, authenticated;


-- =====================================================================
-- VERIFY AFTER RUNNING -- do not assume the paste succeeded
-- =====================================================================
-- Expect 13 rows (the 10 created here plus the 3 already present):
--
--   select table_name from information_schema.tables
--   where table_schema = 'public'
--     and (table_name like 'alf\_%' or table_name = 'sairncare_employee_auth')
--   order by table_name;
--
-- Expected: alf_activities, alf_billing, alf_claim_routes, alf_clients,
-- alf_compliance_rules, alf_facility, alf_incidents, alf_mar, alf_op_audits,
-- alf_payer_rules, alf_signals, alf_staff, alf_staff_credentials,
-- sairncare_employee_auth.
--
-- Then, and only then, does an end-to-end write test mean anything.
