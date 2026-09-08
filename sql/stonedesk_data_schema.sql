-- sql/stonedesk_data_schema.sql
-- StoneDesk application data -- Supabase schema
--
-- Run this once in the Supabase SQL editor. Every statement is idempotent
-- (create table if not exists), safe to re-run.
--
-- WHY THIS FILE EXISTS, measured rather than described. The open-work row said
-- TWELVE StoneDesk collections reached no server. That was an UNDERCOUNT taken
-- from tools/local_only_collection_check.py before the repair whose own commit
-- message reads "the checker could not read half of StoneDesk". Re-run after
-- that fix: 26 of 37 collections have NO route to a server. Twenty-one are
-- backed up by this file; seven are excluded on purpose, each with its reason
-- in api/_resources/stonedesk.js.
--
-- IT IS WORSE HERE THAN IN SAIRNbiz OR SAIRNbuild, for a reason specific to
-- this app. StoneDesk DOES sync slabs, customers, CRM and approvals. So the
-- records that look authoritative survive a browser-data clear and the
-- INVOICES that justify them do not. A uniformly local app at least fails
-- honestly; this one failed selectively, in the direction that looks fine.
--
-- Same generic jsonb-blob pattern as every prior app's schema file
-- (sql/sairnbuild_data_schema.sql is the direct template): license_hash +
-- app_id + <resource>_id + data jsonb + created_at/updated_at,
-- unique(license_hash, <resource>_id), 64KB cap matching api/sd-data.js's
-- uniform MAX_PAYLOAD_BYTES. Service-role only, RLS enabled with no anon
-- policy -- api/sd-data.js is the only door in.
--
-- GENERATED FROM api/sd-data.js's OWN SD_LOCAL_RESOURCES MAP, not retyped, so
-- the schema and the handler cannot disagree about a table name or an id
-- column. That drift is a class this repo has been caught by before.
--
-- NAMING COLLISION CHECK, run before writing rather than assumed: none of the
-- 21 resource names was already registered (`node -e` against
-- api/_resources, 283 resources at the time, zero clashes), and no table below
-- exists in any other schema file in sql/.
--
-- NO `delete` GRANT ANYWHERE IN THIS FILE, and do NOT add one when fixing a
-- missing grant. The platform removed explicit delete grants from every
-- non-sc_* schema on 2026-08-25. api/sd-data.js's generic block handles read
-- and write only; there is no delete path to grant for. Soft-delete, when it
-- arrives, is a flag inside `data` and needs no new privilege.

create extension if not exists pgcrypto;

-- Invoices. The record that justifies every ledger figure the app shows.
create table if not exists public.sd_invoices (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  invoice_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, invoice_id),
  constraint sd_invoices_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_invoices_license on public.sd_invoices(license_hash);
alter table public.sd_invoices enable row level security;
revoke all on public.sd_invoices from service_role;
grant select, insert, update on public.sd_invoices to service_role;
-- Saved drawing-tool state: shapes, dimensions, cutouts, the layout a job was quoted from.
create table if not exists public.sd_drawings (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  drawing_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, drawing_id),
  constraint sd_drawings_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_drawings_license on public.sd_drawings(license_hash);
alter table public.sd_drawings enable row level security;
revoke all on public.sd_drawings from service_role;
grant select, insert, update on public.sd_drawings to service_role;
-- Remake log -- what was refabricated, why, and what it cost.
create table if not exists public.sd_remakes (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  remake_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, remake_id),
  constraint sd_remakes_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_remakes_license on public.sd_remakes(license_hash);
alter table public.sd_remakes enable row level security;
revoke all on public.sd_remakes from service_role;
grant select, insert, update on public.sd_remakes to service_role;
-- Per-job financials: revenue, cost, margin.
create table if not exists public.sd_fin_jobs (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  fin_job_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, fin_job_id),
  constraint sd_fin_jobs_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_fin_jobs_license on public.sd_fin_jobs(license_hash);
alter table public.sd_fin_jobs enable row level security;
revoke all on public.sd_fin_jobs from service_role;
grant select, insert, update on public.sd_fin_jobs to service_role;
-- The shop's own pricing rules. Losing these changes what every future quote says.
create table if not exists public.sd_pricing_rules (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  pricing_rule_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, pricing_rule_id),
  constraint sd_pricing_rules_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_pricing_rules_license on public.sd_pricing_rules(license_hash);
alter table public.sd_pricing_rules enable row level security;
revoke all on public.sd_pricing_rules from service_role;
grant select, insert, update on public.sd_pricing_rules to service_role;
-- Negotiated per-customer or per-supplier prices.
create table if not exists public.sd_negotiated_prices (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  negotiated_price_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, negotiated_price_id),
  constraint sd_negotiated_prices_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_negotiated_prices_license on public.sd_negotiated_prices(license_hash);
alter table public.sd_negotiated_prices enable row level security;
revoke all on public.sd_negotiated_prices from service_role;
grant select, insert, update on public.sd_negotiated_prices to service_role;
-- Purchase order history.
create table if not exists public.sd_order_history (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  order_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, order_id),
  constraint sd_order_history_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_order_history_license on public.sd_order_history(license_hash);
alter table public.sd_order_history enable row level security;
revoke all on public.sd_order_history from service_role;
grant select, insert, update on public.sd_order_history to service_role;
-- Consumables and materials on hand.
create table if not exists public.sd_inventory (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  inventory_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, inventory_id),
  constraint sd_inventory_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_inventory_license on public.sd_inventory(license_hash);
alter table public.sd_inventory enable row level security;
revoke all on public.sd_inventory from service_role;
grant select, insert, update on public.sd_inventory to service_role;
-- Customer communication log.
create table if not exists public.sd_comms (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  comm_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, comm_id),
  constraint sd_comms_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_comms_license on public.sd_comms(license_hash);
alter table public.sd_comms enable row level security;
revoke all on public.sd_comms from service_role;
grant select, insert, update on public.sd_comms to service_role;
-- Outbound SMS record.
create table if not exists public.sd_sms_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  sms_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, sms_id),
  constraint sd_sms_log_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_sms_log_license on public.sd_sms_log(license_hash);
alter table public.sd_sms_log enable row level security;
revoke all on public.sd_sms_log from service_role;
grant select, insert, update on public.sd_sms_log to service_role;
-- Quote history. The unprefixed name is the real localStorage key -- see the NAMING note in api/_resources/stonedesk.js.
create table if not exists public.stonedesk_quote_history (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  quote_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, quote_id),
  constraint stonedesk_quote_history_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_stonedesk_quote_history_license on public.stonedesk_quote_history(license_hash);
alter table public.stonedesk_quote_history enable row level security;
revoke all on public.stonedesk_quote_history from service_role;
grant select, insert, update on public.stonedesk_quote_history to service_role;
-- Point-in-time business snapshots the BI panel trends against.
create table if not exists public.sd_business_snapshots (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  snapshot_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, snapshot_id),
  constraint sd_business_snapshots_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_business_snapshots_license on public.sd_business_snapshots(license_hash);
alter table public.sd_business_snapshots enable row level security;
revoke all on public.sd_business_snapshots from service_role;
grant select, insert, update on public.sd_business_snapshots to service_role;
-- Field service stops: who went where, and when.
create table if not exists public.sd_field_stops (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  field_stop_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, field_stop_id),
  constraint sd_field_stops_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_field_stops_license on public.sd_field_stops(license_hash);
alter table public.sd_field_stops enable row level security;
revoke all on public.sd_field_stops from service_role;
grant select, insert, update on public.sd_field_stops to service_role;
-- Executive messages.
create table if not exists public.sd_exec_msgs (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  exec_msg_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, exec_msg_id),
  constraint sd_exec_msgs_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_exec_msgs_license on public.sd_exec_msgs(license_hash);
alter table public.sd_exec_msgs enable row level security;
revoke all on public.sd_exec_msgs from service_role;
grant select, insert, update on public.sd_exec_msgs to service_role;
-- AI-generated quotes, kept as records rather than transcripts.
create table if not exists public.sd_aiquotes (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  aiquote_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, aiquote_id),
  constraint sd_aiquotes_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_aiquotes_license on public.sd_aiquotes(license_hash);
alter table public.sd_aiquotes enable row level security;
revoke all on public.sd_aiquotes from service_role;
grant select, insert, update on public.sd_aiquotes to service_role;
-- Saved slab nestings -- the yield plan a saw ticket was cut from.
create table if not exists public.sd_nesting_saved (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  nesting_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, nesting_id),
  constraint sd_nesting_saved_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_nesting_saved_license on public.sd_nesting_saved(license_hash);
alter table public.sd_nesting_saved enable row level security;
revoke all on public.sd_nesting_saved from service_role;
grant select, insert, update on public.sd_nesting_saved to service_role;
-- Vein-match analyses.
create table if not exists public.sd_veinmatch (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  veinmatch_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, veinmatch_id),
  constraint sd_veinmatch_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_veinmatch_license on public.sd_veinmatch(license_hash);
alter table public.sd_veinmatch enable row level security;
revoke all on public.sd_veinmatch from service_role;
grant select, insert, update on public.sd_veinmatch to service_role;
-- Seam placement analyses.
create table if not exists public.sd_seamai (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  seamai_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, seamai_id),
  constraint sd_seamai_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_seamai_license on public.sd_seamai(license_hash);
alter table public.sd_seamai enable row level security;
revoke all on public.sd_seamai from service_role;
grant select, insert, update on public.sd_seamai to service_role;
-- Job photo log. Reported COULD-NOT-TELL by the checker only because st('sd_customers', ...) sits on the line above; read by hand.
create table if not exists public.sd_photos (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  photo_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, photo_id),
  constraint sd_photos_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_photos_license on public.sd_photos(license_hash);
alter table public.sd_photos enable row level security;
revoke all on public.sd_photos from service_role;
grant select, insert, update on public.sd_photos to service_role;
-- Template Manager records: a 5-state workflow with a statusLog[] audit trail.
create table if not exists public.sd_templates (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  template_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, template_id),
  constraint sd_templates_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_templates_license on public.sd_templates(license_hash);
alter table public.sd_templates enable row level security;
revoke all on public.sd_templates from service_role;
grant select, insert, update on public.sd_templates to service_role;
-- Accumulated email-security findings. Not recomputed -- read before placing.
create table if not exists public.sd_email_threats (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'stonedesk',
  threat_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, threat_id),
  constraint sd_email_threats_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_email_threats_license on public.sd_email_threats(license_hash);
alter table public.sd_email_threats enable row level security;
revoke all on public.sd_email_threats from service_role;
grant select, insert, update on public.sd_email_threats to service_role;

-- CONTROL. Run this last: it should return 21 rows, one per table above. A
-- shorter result means a statement did not apply, which is the difference
-- between "the migration ran" and "the migration ran completely" -- and this
-- platform has shipped a row claiming the former while the latter was false.
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('sd_invoices', 'sd_drawings', 'sd_remakes', 'sd_fin_jobs', 'sd_pricing_rules', 'sd_negotiated_prices', 'sd_order_history', 'sd_inventory', 'sd_comms', 'sd_sms_log', 'stonedesk_quote_history', 'sd_business_snapshots', 'sd_field_stops', 'sd_exec_msgs', 'sd_aiquotes', 'sd_nesting_saved', 'sd_veinmatch', 'sd_seamai', 'sd_photos', 'sd_templates', 'sd_email_threats')
order by table_name;
