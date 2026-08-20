-- sql/sairnsenior_clients_schema.sql
-- SAIRNsenior client (home-care recipient) data + HIPAA minimum-necessary
-- privacy gate -- Supabase schema
--
-- WHY THIS EXISTS: SAIRNsenior is built ground-up with real server sync
-- from day one, not retrofitted -- a client is home-care PHI (name,
-- address, diagnosis, authorized services), so it needs a real access
-- boundary from the first commit, not "added later."
--
-- assigned_employee_id is a REAL top-level column, not buried in the
-- jsonb `data` blob -- it's what the privacy gate actually filters and
-- checks ownership against server-side, so it has to be a real queryable
-- column. Same shape as every other assignment-based privacy gate this
-- session (StoneDesk's sd_crm, SAIRNdesign's sdn_clients, SAIRNbuild's
-- bld_bids/bld_tna).
--
-- HIPAA minimum-necessary framing: null assigned_employee_id means
-- unassigned -- treated as management-only-visible (owner/billing), same
-- confirmed-correct default as every prior app's assignment gate. A
-- caregiver never sees a client they are not personally assigned to.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.sen_clients (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnsenior',
  client_id    text not null,                        -- client-generated id (CL-<timestamp>)
  assigned_employee_id text,                          -- null = unassigned, management-only-visible
  data         jsonb not null default '{}'::jsonb,    -- name, phone, address, diagnosis, payer,
                                                        -- authorized_hours, status, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, client_id),
  constraint senclients_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_senclients_license on public.sen_clients(license_hash);
create index if not exists idx_senclients_assignee on public.sen_clients(license_hash, assigned_employee_id);

-- ---------------------------------------------------------------------------
-- GRANTS -- explicit up front, same reasoning as every other data table's
-- own header this session.
grant select, insert, update on public.sen_clients to service_role;
revoke all on public.sen_clients from anon, authenticated;
