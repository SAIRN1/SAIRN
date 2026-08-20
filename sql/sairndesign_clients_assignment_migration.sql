-- sql/sairndesign_clients_assignment_migration.sql
-- Adds the real per-client assignment column to the EXISTING sdn_clients
-- table (sql/sairndesign_data_schema.sql, already live -- this is an
-- ALTER, not a fresh CREATE) -- Task 2 of the platform sales-lead-privacy
-- rule: a client/lead is visible only to management (Owner/Office) or the
-- designer it's assigned to.
--
-- assigned_employee_id is a REAL top-level column, not buried in the
-- jsonb `data` blob -- it's what api/sd-data.js's new sdn_clients
-- read/write gate actually filters and checks ownership against
-- server-side, so it has to be a real queryable column, not something
-- only the client could see and trust. Same reasoning, same shape as
-- sql/sd_crm_schema.sql's assigned_employee_id for StoneDesk's CRM
-- (built 2026-08-19, first app in this rollout).
--
-- Null means unassigned -- treated as management-only-visible by
-- api/sd-data.js's gate (confirmed correct behavior for this rule by
-- Michael on StoneDesk's build, same default applied here).
--
-- Run this once in the Supabase SQL editor. Safe to re-run (IF NOT
-- EXISTS / IF NOT EXISTS index).

alter table public.sdn_clients
  add column if not exists assigned_employee_id text;

create index if not exists idx_sdnclients_assignee
  on public.sdn_clients(license_hash, assigned_employee_id);
