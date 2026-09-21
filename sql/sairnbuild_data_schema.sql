-- sql/sairnbuild_data_schema.sql
-- SAIRNbuild application data -- Supabase schema
--
-- Run this once in the Supabase SQL editor. Every statement is idempotent
-- (create table if not exists), safe to re-run.
--
-- WHY THIS FILE EXISTS, measured rather than described. On 2026-09-03
-- sairnbuild.html wrote THIRTY-SEVEN localStorage collections and had server
-- sync for exactly TWO of them (bld_bids, bld_tna). Everything else -- jobs,
-- job costs, change orders, draw schedule, LIEN WAIVERS, safety incidents,
-- daily logs, RFIs, submittals, timesheets -- existed in one browser and
-- nowhere else. Clearing that browser lost the company's records, permanently,
-- with no copy on any server. docs/SAIRN-OPEN-WORK-INDEX.md carried this as
-- "Zero server-side backup for any real business data", size L, unassigned.
--
-- Same generic jsonb-blob pattern as every prior app's schema file
-- (sql/sairnlegacy_data_schema.sql is the direct template): license_hash +
-- app_id + <resource>_id + data jsonb + created_at/updated_at,
-- unique(license_hash, <resource>_id), 64KB size cap matching
-- api/sd-data.js's uniform MAX_PAYLOAD_BYTES. Service-role only, RLS enabled
-- with no anon policy -- api/sd-data.js is the only door in.
--
-- ID COLUMN NAMING: mechanical singularisation of the resource name (strip
-- bld_, singularise), the same rule sairnlegacy's schema documents and
-- applies uniformly -- including its -ies -> -y handling, so bld_deliveries
-- is delivery_id rather than the deliverie_id a naive strip-the-s would give.
--
-- NAMING COLLISION CHECK: every table here carries the bld_ prefix, and the
-- only pre-existing bld_ tables are bld_bids and bld_tna, neither of which
-- appears below. Checked before writing, not assumed.
--
-- NO `delete` GRANT ANYWHERE IN THIS FILE, and do NOT add one when fixing a
-- missing grant. The platform removed explicit delete grants from every
-- non-sc_* schema on 2026-08-25, and re-adding delete is precisely the
-- overcorrection that caused the 2026-08-06 incident. api/sd-data.js's
-- generic block handles read and write only; there is no delete path to grant
-- for.

create extension if not exists pgcrypto;

-- The spine. Every other record below references a job_id.
create table if not exists public.bld_jobs (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  job_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, job_id),
  constraint bld_jobs_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_jobs_license on public.bld_jobs(license_hash);
alter table public.bld_jobs enable row level security;
revoke all on public.bld_jobs from service_role;
grant select, insert, update on public.bld_jobs to service_role;
-- Job costing: budget / committed / actual per cost code.
create table if not exists public.bld_costs (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  cost_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, cost_id),
  constraint bld_costs_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_costs_license on public.bld_costs(license_hash);
alter table public.bld_costs enable row level security;
revoke all on public.bld_costs from service_role;
grant select, insert, update on public.bld_costs to service_role;
-- Contract modifications. Money and scope, in writing.
create table if not exists public.bld_change_orders (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  change_order_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, change_order_id),
  constraint bld_change_orders_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_change_orders_license on public.bld_change_orders(license_hash);
alter table public.bld_change_orders enable row level security;
revoke all on public.bld_change_orders from service_role;
grant select, insert, update on public.bld_change_orders to service_role;
-- Payment applications and retainage.
create table if not exists public.bld_draws (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  draw_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, draw_id),
  constraint bld_draws_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_draws_license on public.bld_draws(license_hash);
alter table public.bld_draws enable row level security;
revoke all on public.bld_draws from service_role;
grant select, insert, update on public.bld_draws to service_role;

-- ── ATOMIC RETAINAGE-RELEASE WRITE (2026-09-21) ────────────────────────────
-- Closes a real lost-update race in api/sd-data.js's release_retainage branch
-- (hover_log #315): the handler read bld_draws' jsonb `data`, computed a new
-- retainage_released figure and appended one entry to
-- retainage_release_log CLIENT-SIDE, then PATCHed the whole `data` blob back
-- with only license_hash+draw_id in the WHERE clause -- no version/CAS
-- predicate. Two concurrent release_retainage calls on the SAME draw_id each
-- read the same starting `data`, and whichever PATCH lands second silently
-- WINS, overwriting the first PATCH's write -- including its audit-trail
-- entry -- with no error.
--
-- NOT modelled on law_check_and_insert_disbursement()'s exact shape: that
-- function embeds its own business rule (the balance check) IN the SQL. The
-- release-legality rule here is bwip.summariseDraw() in
-- api/_lib/wip-accounting.js, real JS logic the platform's own convergence
-- doctrine says must not be duplicated into a second language -- two
-- independently-maintained copies of the same rule are free to drift, the
-- exact class of defect item 92/94's own material warns against.
--
-- So this keeps the SAME underlying mechanism (pg_advisory_xact_lock scoped
-- to the row, held across a check-then-write inside one transaction, same
-- READ-COMMITTED precondition) but the "check" is a plain optimistic-CAS
-- comparison rather than embedded business logic: the caller reads the
-- current retainage_released, runs bwip.summariseDraw() in JS exactly as
-- before, and passes what it read back in as p_expected_prior_released. If
-- another release landed between the caller's read and this call, the
-- comparison fails and the caller is told to re-fetch and retry rather than
-- overwriting blind.
create or replace function public.bld_release_retainage_atomic(
  p_license_hash text, p_draw_id text, p_expected_prior_released numeric, p_next_data jsonb
) returns public.bld_draws
language plpgsql
as $$
declare
  v_row public.bld_draws;
  v_current numeric;
  v_iso text;
begin
  v_iso := current_setting('transaction_isolation');
  if v_iso <> 'read committed' then
    raise exception
      'bld_release_retainage_atomic requires READ COMMITTED; this '
      'transaction is %. The advisory lock serialises acquisition, not the '
      'snapshot, so under % a waiting caller''s CAS re-read can still see a '
      'pre-lock value and pass a comparison it should have failed, with the '
      'lock held correctly the whole time.',
      v_iso, v_iso
      using errcode = 'invalid_transaction_state';
  end if;

  -- Scoped to (license_hash, draw_id) -- the exact pair the real unique
  -- constraint covers (unique (license_hash, draw_id), above) -- so two
  -- callers racing the SAME draw serialise here and different draws never
  -- contend with each other.
  perform pg_advisory_xact_lock(hashtext(p_license_hash || ':' || p_draw_id));

  -- Re-read the LATEST committed value under the lock (READ COMMITTED,
  -- asserted above, is what makes this a fresh read rather than the waiting
  -- caller's own stale transaction snapshot).
  select (data->>'retainage_released')::numeric into v_current
    from public.bld_draws
    where license_hash = p_license_hash and draw_id = p_draw_id;

  if not found then
    raise exception
      'NO_SUCH_DRAW: % is not on file', p_draw_id
      using errcode = 'P0001';
  end if;

  if coalesce(v_current, 0) <> coalesce(p_expected_prior_released, 0) then
    raise exception
      'RETAINAGE_RELEASE_CONFLICT: draw % was updated by another release '
      'between read and write (expected prior %, found %) -- re-fetch and retry',
      p_draw_id, p_expected_prior_released, v_current
      using errcode = 'P0001';
  end if;

  update public.bld_draws
    set data = p_next_data, updated_at = now()
    where license_hash = p_license_hash and draw_id = p_draw_id
  returning * into v_row;

  -- NO PATH ABOVE CAN RETURN NULL. Asserted rather than assumed, same
  -- discipline as law_check_and_insert_disbursement's own closing guard: the
  -- row was just confirmed to exist and matched under the SAME held lock, so
  -- a null here means a future edit broke that invariant, not a real race.
  if v_row.id is null then
    raise exception
      'RETAINAGE_RELEASE_NOT_WRITTEN: no bld_draws row was produced for % -- nothing was recorded',
      p_draw_id
      using errcode = 'P0001';
  end if;

  return v_row;
end;
$$;

revoke all on function public.bld_release_retainage_atomic from public;
grant execute on function public.bld_release_retainage_atomic to service_role;

-- Legal instruments. A lost waiver is a real financial exposure.
create table if not exists public.bld_lien_waivers (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  lien_waiver_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, lien_waiver_id),
  constraint bld_lien_waivers_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_lien_waivers_license on public.bld_lien_waivers(license_hash);
alter table public.bld_lien_waivers enable row level security;
revoke all on public.bld_lien_waivers from service_role;
grant select, insert, update on public.bld_lien_waivers to service_role;
-- The contemporaneous site record -- what construction disputes turn on.
create table if not exists public.bld_daily_logs (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  daily_log_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, daily_log_id),
  constraint bld_daily_logs_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_daily_logs_license on public.bld_daily_logs(license_hash);
alter table public.bld_daily_logs enable row level security;
revoke all on public.bld_daily_logs from service_role;
grant select, insert, update on public.bld_daily_logs to service_role;
-- Safety incidents. OSHA-relevant.
create table if not exists public.bld_incidents (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  incident_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, incident_id),
  constraint bld_incidents_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_incidents_license on public.bld_incidents(license_hash);
alter table public.bld_incidents enable row level security;
revoke all on public.bld_incidents from service_role;
grant select, insert, update on public.bld_incidents to service_role;
-- Inspection results and re-inspection dates.
create table if not exists public.bld_inspections (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  inspection_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, inspection_id),
  constraint bld_inspections_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_inspections_license on public.bld_inspections(license_hash);
alter table public.bld_inspections enable row level security;
revoke all on public.bld_inspections from service_role;
grant select, insert, update on public.bld_inspections to service_role;
-- Toolbox talks delivered, with attendance.
create table if not exists public.bld_toolbox_talks (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  toolbox_talk_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, toolbox_talk_id),
  constraint bld_toolbox_talks_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_toolbox_talks_license on public.bld_toolbox_talks(license_hash);
alter table public.bld_toolbox_talks enable row level security;
revoke all on public.bld_toolbox_talks from service_role;
grant select, insert, update on public.bld_toolbox_talks to service_role;
-- Requests for information -- the contract-administration trail.
create table if not exists public.bld_rfis (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  rfi_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, rfi_id),
  constraint bld_rfis_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_rfis_license on public.bld_rfis(license_hash);
alter table public.bld_rfis enable row level security;
revoke all on public.bld_rfis from service_role;
grant select, insert, update on public.bld_rfis to service_role;
-- Submittals and their approval state.
create table if not exists public.bld_submittals (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  submittal_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, submittal_id),
  constraint bld_submittals_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_submittals_license on public.bld_submittals(license_hash);
alter table public.bld_submittals enable row level security;
revoke all on public.bld_submittals from service_role;
grant select, insert, update on public.bld_submittals to service_role;
-- Punch items at closeout.
create table if not exists public.bld_punchlist (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  punchlist_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, punchlist_id),
  constraint bld_punchlist_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_punchlist_license on public.bld_punchlist(license_hash);
alter table public.bld_punchlist enable row level security;
revoke all on public.bld_punchlist from service_role;
grant select, insert, update on public.bld_punchlist to service_role;
-- Warranty claims after handover.
create table if not exists public.bld_warranty (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  warranty_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, warranty_id),
  constraint bld_warranty_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_warranty_license on public.bld_warranty(license_hash);
alter table public.bld_warranty enable row level security;
revoke all on public.bld_warranty from service_role;
grant select, insert, update on public.bld_warranty to service_role;
-- Subcontractor roster.
create table if not exists public.bld_subs (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  sub_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, sub_id),
  constraint bld_subs_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_subs_license on public.bld_subs(license_hash);
alter table public.bld_subs enable row level security;
revoke all on public.bld_subs from service_role;
grant select, insert, update on public.bld_subs to service_role;
-- Bids received FROM subs (distinct from bld_bids, which is bids OUT).
create table if not exists public.bld_sub_bids (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  sub_bid_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, sub_bid_id),
  constraint bld_sub_bids_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_sub_bids_license on public.bld_sub_bids(license_hash);
alter table public.bld_sub_bids enable row level security;
revoke all on public.bld_sub_bids from service_role;
grant select, insert, update on public.bld_sub_bids to service_role;
-- Supplier roster.
create table if not exists public.bld_suppliers (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  supplier_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, supplier_id),
  constraint bld_suppliers_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_suppliers_license on public.bld_suppliers(license_hash);
alter table public.bld_suppliers enable row level security;
revoke all on public.bld_suppliers from service_role;
grant select, insert, update on public.bld_suppliers to service_role;
-- Purchase orders.
create table if not exists public.bld_pos (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  po_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, po_id),
  constraint bld_pos_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_pos_license on public.bld_pos(license_hash);
alter table public.bld_pos enable row level security;
revoke all on public.bld_pos from service_role;
grant select, insert, update on public.bld_pos to service_role;
-- Material deliveries received.
create table if not exists public.bld_deliveries (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  delivery_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, delivery_id),
  constraint bld_deliveries_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_deliveries_license on public.bld_deliveries(license_hash);
alter table public.bld_deliveries enable row level security;
revoke all on public.bld_deliveries from service_role;
grant select, insert, update on public.bld_deliveries to service_role;
-- Payments issued.
create table if not exists public.bld_checks (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  check_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, check_id),
  constraint bld_checks_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_checks_license on public.bld_checks(license_hash);
alter table public.bld_checks enable row level security;
revoke all on public.bld_checks from service_role;
grant select, insert, update on public.bld_checks to service_role;
-- Labour hours -- what job costing is computed from.
create table if not exists public.bld_timesheet (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  timesheet_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, timesheet_id),
  constraint bld_timesheet_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_timesheet_license on public.bld_timesheet(license_hash);
alter table public.bld_timesheet enable row level security;
revoke all on public.bld_timesheet from service_role;
grant select, insert, update on public.bld_timesheet to service_role;
-- Task assignments.
create table if not exists public.bld_tasks (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  task_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, task_id),
  constraint bld_tasks_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_tasks_license on public.bld_tasks(license_hash);
alter table public.bld_tasks enable row level security;
revoke all on public.bld_tasks from service_role;
grant select, insert, update on public.bld_tasks to service_role;
-- The build schedule.
create table if not exists public.bld_schedule_entries (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  schedule_entry_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, schedule_entry_id),
  constraint bld_schedule_entries_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_schedule_entries_license on public.bld_schedule_entries(license_hash);
alter table public.bld_schedule_entries enable row level security;
revoke all on public.bld_schedule_entries from service_role;
grant select, insert, update on public.bld_schedule_entries to service_role;
-- Client selections and their deadlines.
create table if not exists public.bld_selections (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  selection_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, selection_id),
  constraint bld_selections_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_selections_license on public.bld_selections(license_hash);
alter table public.bld_selections enable row level security;
revoke all on public.bld_selections from service_role;
grant select, insert, update on public.bld_selections to service_role;
-- Document register with version history. Metadata only, no file bytes.
create table if not exists public.bld_documents (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  document_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, document_id),
  constraint bld_documents_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_documents_license on public.bld_documents(license_hash);
alter table public.bld_documents enable row level security;
revoke all on public.bld_documents from service_role;
grant select, insert, update on public.bld_documents to service_role;
-- Equipment register.
create table if not exists public.bld_equipment (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  equipment_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, equipment_id),
  constraint bld_equipment_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_equipment_license on public.bld_equipment(license_hash);
alter table public.bld_equipment enable row level security;
revoke all on public.bld_equipment from service_role;
grant select, insert, update on public.bld_equipment to service_role;
-- Client and sub communication log.
create table if not exists public.bld_comm_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  comm_log_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, comm_log_id),
  constraint bld_comm_log_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_comm_log_license on public.bld_comm_log(license_hash);
alter table public.bld_comm_log enable row level security;
revoke all on public.bld_comm_log from service_role;
grant select, insert, update on public.bld_comm_log to service_role;
-- Referral sources.
create table if not exists public.bld_referrals (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  referral_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, referral_id),
  constraint bld_referrals_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_referrals_license on public.bld_referrals(license_hash);
alter table public.bld_referrals enable row level security;
revoke all on public.bld_referrals from service_role;
grant select, insert, update on public.bld_referrals to service_role;
-- Client reviews.
create table if not exists public.bld_reviews (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  review_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, review_id),
  constraint bld_reviews_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_reviews_license on public.bld_reviews(license_hash);
alter table public.bld_reviews enable row level security;
revoke all on public.bld_reviews from service_role;
grant select, insert, update on public.bld_reviews to service_role;
-- The price book estimates are built from.
create table if not exists public.bld_price_points (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  price_point_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, price_point_id),
  constraint bld_price_points_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_price_points_license on public.bld_price_points(license_hash);
alter table public.bld_price_points enable row level security;
revoke all on public.bld_price_points from service_role;
grant select, insert, update on public.bld_price_points to service_role;
-- AI site-photo findings. Text only -- no image bytes are stored.
create table if not exists public.bld_photo_analyses (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbuild',
  photo_analysis_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, photo_analysis_id),
  constraint bld_photo_analyses_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_bld_photo_analyses_license on public.bld_photo_analyses(license_hash);
alter table public.bld_photo_analyses enable row level security;
revoke all on public.bld_photo_analyses from service_role;
grant select, insert, update on public.bld_photo_analyses to service_role;

-- Verify after running. Expect exactly 32 rows, each with
-- INSERT / SELECT / UPDATE and nothing else:
--
--   select table_name, string_agg(privilege_type, ', ' order by privilege_type) as privs
--     from information_schema.role_table_grants
--    where grantee = 'service_role'
--      and table_schema = 'public'
--      and table_name like 'bld\_%'
--    group by table_name
--    order by table_name;
--
-- Then through the DEPLOYED API, which is the only real proof -- a clean
-- create is not evidence the app can use it:
--
--   curl -s -X POST https://sairn.vercel.app/api/sd-data \
--     -H 'Content-Type: application/json' \
--     -H 'Authorization: Bearer BLD-PINNACLE-2026' \
--     -d '{"action":"read","resource":"bld_jobs"}'
--
--   {"ok":true,"data":[],"provisioned":true}   -> this file has been run
--   503 NOT_PROVISIONED                        -> it has not
