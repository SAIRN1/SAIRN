-- sql/sairncare_clients_schema.sql
-- SAIRNcare resident (assisted-living) data + privacy gate -- Supabase
-- schema. Run this once in the Supabase SQL editor before api/sd-data.js's
-- alf_clients read/write branch will work.
--
-- Same shape and same reasoning as sql/sairnsenior_clients_schema.sql --
-- ground-up app, real server sync from day one, assigned_employee_id is a
-- real top-level queryable column (not buried in the jsonb data blob)
-- because it's what the privacy gate actually filters against server-side.
--
-- WHY THE GATE HAS FOUR TIERS, NOT SAIRNsenior's THREE: SAIRNsenior's
-- broad-read tier (coordinator/scheduler) can both READ and EDIT every
-- client. SAIRNcare's confirmed role scope explicitly gives Activities
-- Coordinator READ-ONLY roster access with "no clinical or billing write
-- access" (docs/superpowers/specs/2026-08-20-sairncare-v1-scope.md) --
-- that is a genuinely different tier than nursing's broad-read-AND-edit,
-- so the server-side gate (api/sd-data.js) implements it as a real fourth
-- tier rather than collapsing it into an existing one. NULL
-- assigned_employee_id means unassigned -- management-only-visible, same
-- confirmed-correct default as every prior app's assignment gate.

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

-- Verify after running (expect 0 rows, no error):
--   select count(*) from alf_clients;
