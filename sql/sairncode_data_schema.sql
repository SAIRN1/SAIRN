-- sql/sairncode_data_schema.sql
-- Real server-synced tables for all 15 SAIRNcode business resources.
-- Run this once in the Supabase SQL editor before api/sd-data.js's
-- sc_* read/write/delete branches will work.
--
-- WHY THIS EXISTS: every one of these 15 resources (denials, revenue,
-- compliance, fraud alerts, pre-bill scrub, HCC gaps, DRG cases,
-- physician queries, RAC audits, telehealth claims, anesthesia cases,
-- prior authorizations, A/R, providers, encoder reference codes) was
-- localStorage-only until now -- no cross-device sync, and (closed
-- separately, 2026-08-18 fabrication audit, Pass 1) several shipped with
-- hardcoded fake-name fallback data. This is Pass 2: give every one of
-- them a real per-practice table, matching every other resource on this
-- shared endpoint -- one row per entry, license_hash-scoped, a jsonb
-- data column rather than one column per field (these 15 resources'
-- fields differ from each other but the storage/access pattern is
-- identical, same shape grd_progress_photos already uses).
--
-- entry_id is the client's own locally-generated id (e.g. 'dn'+Date.now())
-- carried over unchanged so the existing add/remove UI logic needs no id
-- scheme change, only a storage-location change.

create table if not exists public.sc_denial (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_denial_data_size check (octet_length(data::text) <= 65536)
);

create table if not exists public.sc_revenue (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_revenue_data_size check (octet_length(data::text) <= 65536)
);

create table if not exists public.sc_compliance (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_compliance_data_size check (octet_length(data::text) <= 65536)
);

create table if not exists public.sc_fraud (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_fraud_data_size check (octet_length(data::text) <= 65536)
);

create table if not exists public.sc_prebill (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_prebill_data_size check (octet_length(data::text) <= 65536)
);

create table if not exists public.sc_hcc (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_hcc_data_size check (octet_length(data::text) <= 65536)
);

create table if not exists public.sc_drg (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_drg_data_size check (octet_length(data::text) <= 65536)
);

create table if not exists public.sc_query (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_query_data_size check (octet_length(data::text) <= 65536)
);

create table if not exists public.sc_rac (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_rac_data_size check (octet_length(data::text) <= 65536)
);

create table if not exists public.sc_telehealth (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_telehealth_data_size check (octet_length(data::text) <= 65536)
);

create table if not exists public.sc_anesthesia (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_anesthesia_data_size check (octet_length(data::text) <= 65536)
);

create table if not exists public.sc_auth (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_auth_data_size check (octet_length(data::text) <= 65536)
);

create table if not exists public.sc_ar (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_ar_data_size check (octet_length(data::text) <= 65536)
);

create table if not exists public.sc_providers (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_providers_data_size check (octet_length(data::text) <= 65536)
);

create table if not exists public.sc_encoder (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_encoder_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sc_denial_license on public.sc_denial(license_hash);
create index if not exists idx_sc_revenue_license on public.sc_revenue(license_hash);
create index if not exists idx_sc_compliance_license on public.sc_compliance(license_hash);
create index if not exists idx_sc_fraud_license on public.sc_fraud(license_hash);
create index if not exists idx_sc_prebill_license on public.sc_prebill(license_hash);
create index if not exists idx_sc_hcc_license on public.sc_hcc(license_hash);
create index if not exists idx_sc_drg_license on public.sc_drg(license_hash);
create index if not exists idx_sc_query_license on public.sc_query(license_hash);
create index if not exists idx_sc_rac_license on public.sc_rac(license_hash);
create index if not exists idx_sc_telehealth_license on public.sc_telehealth(license_hash);
create index if not exists idx_sc_anesthesia_license on public.sc_anesthesia(license_hash);
create index if not exists idx_sc_auth_license on public.sc_auth(license_hash);
create index if not exists idx_sc_ar_license on public.sc_ar(license_hash);
create index if not exists idx_sc_providers_license on public.sc_providers(license_hash);
create index if not exists idx_sc_encoder_license on public.sc_encoder(license_hash);

alter table public.sc_denial      enable row level security;
alter table public.sc_revenue     enable row level security;
alter table public.sc_compliance  enable row level security;
alter table public.sc_fraud       enable row level security;
alter table public.sc_prebill     enable row level security;
alter table public.sc_hcc         enable row level security;
alter table public.sc_drg         enable row level security;
alter table public.sc_query       enable row level security;
alter table public.sc_rac         enable row level security;
alter table public.sc_telehealth  enable row level security;
alter table public.sc_anesthesia  enable row level security;
alter table public.sc_auth        enable row level security;
alter table public.sc_ar          enable row level security;
alter table public.sc_providers   enable row level security;
alter table public.sc_encoder     enable row level security;

drop policy if exists "svc only sc_denial" on public.sc_denial;
create policy "svc only sc_denial" on public.sc_denial for all using (false) with check (false);
drop policy if exists "svc only sc_revenue" on public.sc_revenue;
create policy "svc only sc_revenue" on public.sc_revenue for all using (false) with check (false);
drop policy if exists "svc only sc_compliance" on public.sc_compliance;
create policy "svc only sc_compliance" on public.sc_compliance for all using (false) with check (false);
drop policy if exists "svc only sc_fraud" on public.sc_fraud;
create policy "svc only sc_fraud" on public.sc_fraud for all using (false) with check (false);
drop policy if exists "svc only sc_prebill" on public.sc_prebill;
create policy "svc only sc_prebill" on public.sc_prebill for all using (false) with check (false);
drop policy if exists "svc only sc_hcc" on public.sc_hcc;
create policy "svc only sc_hcc" on public.sc_hcc for all using (false) with check (false);
drop policy if exists "svc only sc_drg" on public.sc_drg;
create policy "svc only sc_drg" on public.sc_drg for all using (false) with check (false);
drop policy if exists "svc only sc_query" on public.sc_query;
create policy "svc only sc_query" on public.sc_query for all using (false) with check (false);
drop policy if exists "svc only sc_rac" on public.sc_rac;
create policy "svc only sc_rac" on public.sc_rac for all using (false) with check (false);
drop policy if exists "svc only sc_telehealth" on public.sc_telehealth;
create policy "svc only sc_telehealth" on public.sc_telehealth for all using (false) with check (false);
drop policy if exists "svc only sc_anesthesia" on public.sc_anesthesia;
create policy "svc only sc_anesthesia" on public.sc_anesthesia for all using (false) with check (false);
drop policy if exists "svc only sc_auth" on public.sc_auth;
create policy "svc only sc_auth" on public.sc_auth for all using (false) with check (false);
drop policy if exists "svc only sc_ar" on public.sc_ar;
create policy "svc only sc_ar" on public.sc_ar for all using (false) with check (false);
drop policy if exists "svc only sc_providers" on public.sc_providers;
create policy "svc only sc_providers" on public.sc_providers for all using (false) with check (false);
drop policy if exists "svc only sc_encoder" on public.sc_encoder;
create policy "svc only sc_encoder" on public.sc_encoder for all using (false) with check (false);

grant select, insert, update, delete on public.sc_denial      to service_role;
grant select, insert, update, delete on public.sc_revenue     to service_role;
grant select, insert, update, delete on public.sc_compliance  to service_role;
grant select, insert, update, delete on public.sc_fraud       to service_role;
grant select, insert, update, delete on public.sc_prebill     to service_role;
grant select, insert, update, delete on public.sc_hcc         to service_role;
grant select, insert, update, delete on public.sc_drg         to service_role;
grant select, insert, update, delete on public.sc_query       to service_role;
grant select, insert, update, delete on public.sc_rac         to service_role;
grant select, insert, update, delete on public.sc_telehealth  to service_role;
grant select, insert, update, delete on public.sc_anesthesia  to service_role;
grant select, insert, update, delete on public.sc_auth        to service_role;
grant select, insert, update, delete on public.sc_ar          to service_role;
grant select, insert, update, delete on public.sc_providers   to service_role;
grant select, insert, update, delete on public.sc_encoder     to service_role;

revoke all on public.sc_denial     from anon, authenticated;
revoke all on public.sc_revenue    from anon, authenticated;
revoke all on public.sc_compliance from anon, authenticated;
revoke all on public.sc_fraud      from anon, authenticated;
revoke all on public.sc_prebill    from anon, authenticated;
revoke all on public.sc_hcc        from anon, authenticated;
revoke all on public.sc_drg        from anon, authenticated;
revoke all on public.sc_query      from anon, authenticated;
revoke all on public.sc_rac        from anon, authenticated;
revoke all on public.sc_telehealth from anon, authenticated;
revoke all on public.sc_anesthesia from anon, authenticated;
revoke all on public.sc_auth       from anon, authenticated;
revoke all on public.sc_ar         from anon, authenticated;
revoke all on public.sc_providers  from anon, authenticated;
revoke all on public.sc_encoder    from anon, authenticated;

-- Verify after running (expect 0 rows, no error, for each):
--   select count(*) from sc_denial;
--   select count(*) from sc_providers;
--   (etc. for the remaining 13 tables)
