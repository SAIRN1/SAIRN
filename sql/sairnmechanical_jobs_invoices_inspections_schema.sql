-- sql/sairnmechanical_jobs_invoices_inspections_schema.sql  (fourth b67)
--
-- CONCEPT. SAIRNmechanical had no job, no invoice and no inspection record:
-- 'Job entry' and 'Invoice entry' were mechNotLive() placeholders and nothing
-- held an inspection at all (b64 worldwide audit). These three tables carry
-- them, in exactly the shape of sql/sairnmechanical_records_schema.sql's
-- mech_quotes: one jsonb record per row keyed by (license_hash, <id>), a 64KB
-- row cap, service-role only, and select/insert/update -- NO delete grant, so
-- a removal path is a separate decision, as it is for the other mech_* records.
--
-- IDEMPOTENT. `create table if not exists`, `drop policy if exists` then
-- create, and the grant lines are safe to re-run. Touches nothing else.
--
-- AFTER RUNNING: the app's Jobs, Invoices and Inspections forms back up to the
-- server; until then api/sd-data.js answers read with provisioned:false and
-- the records stay on the device, which the app says.

create table if not exists public.mech_jobs (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnmechanical',
  job_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, job_id),
  constraint mech_jobs_data_size check (octet_length(data::text) <= 65536)
);
alter table public.mech_jobs enable row level security;
drop policy if exists "svc only mech_jobs" on public.mech_jobs;
create policy "svc only mech_jobs" on public.mech_jobs
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.mech_jobs from service_role;
grant select, insert, update on public.mech_jobs to service_role;

create table if not exists public.mech_invoices (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnmechanical',
  invoice_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, invoice_id),
  constraint mech_invoices_data_size check (octet_length(data::text) <= 65536)
);
alter table public.mech_invoices enable row level security;
drop policy if exists "svc only mech_invoices" on public.mech_invoices;
create policy "svc only mech_invoices" on public.mech_invoices
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.mech_invoices from service_role;
grant select, insert, update on public.mech_invoices to service_role;

create table if not exists public.mech_inspections (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnmechanical',
  inspection_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, inspection_id),
  constraint mech_inspections_data_size check (octet_length(data::text) <= 65536)
);
alter table public.mech_inspections enable row level security;
drop policy if exists "svc only mech_inspections" on public.mech_inspections;
create policy "svc only mech_inspections" on public.mech_inspections
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.mech_inspections from service_role;
grant select, insert, update on public.mech_inspections to service_role;
