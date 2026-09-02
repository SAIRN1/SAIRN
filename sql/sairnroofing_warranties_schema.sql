-- sql/sairnroofing_warranties_schema.sql
-- SAIRNroofing gap A1 -- manufacturer warranty tiers and per-job registration.
-- Run once in the Supabase SQL editor. Safe to re-run (idempotent).
--
-- ══ WHY THIS IS APP-PREFIXED AND NOT SHARED ════════════════════════════════
-- The opposite call from sql/subcontractor_compliance_schema.sql, deliberately.
-- Subcontractor compliance is the same problem in every trade, so it was built
-- shared and app_id-scoped. A manufacturer shingle warranty gated on GAF Master
-- Elite standing is ROOFING, and it hangs off rf_company_programs, which is
-- already rf_-prefixed and roofing-only. Making it shared would mean carrying a
-- foreign key into a roofing table from a platform table, which is the wrong
-- direction of dependency. If a second app ever needs manufacturer warranties,
-- that is the moment to generalise -- not before, on speculation.
--
-- ══ NOTHING IS SEEDED, AND THAT IS THE POINT ═══════════════════════════════
-- Same decision as sql/sairnroofing_programs_schema.sql and its engine
-- (2026-08-25): real programme terms sit behind manufacturer contractor
-- portals, what is publicly reachable is marketing copy, and a contractor told
-- "you qualify for the Golden Pledge" on a third-hand number could act on it.
-- So there is no GAF tier list here, no CertainTeed mapping, and above all no
-- default registration window. The commonly-repeated "30 days" is wrong for
-- some products, and being wrong about it costs the homeowner the coverage.
--
-- Every tier carries a `source` the contractor names. api/_lib/roofing-
-- warranties.js reports an unsourced tier as UNUSABLE rather than evaluating
-- it -- the same rule roofing-programs.js already applies to a requirement.
--
-- ══ SIZE BOUNDS ARE NUMERIC ON PURPOSE ═════════════════════════════════════
-- tools/sairn_sql_preflight.py can only compare CHECK constraints where both
-- sides state a numeric bound; Postgres rewrites anything else beyond textual
-- recognition. Plain octet_length(...) <= N stays inside what it can verify.
-- See docs/2026-09-02-constraints-not-comparable.md.

-- ---------------------------------------------------------------------------
-- 1. The tiers this contractor can offer, and what each one is gated on.
-- ---------------------------------------------------------------------------
-- `requires_program_id` is a plain text reference to rf_company_programs.
-- program_id and NOT a foreign key, matching how rf_ tables already reference
-- each other here. The cost is stated rather than hidden: nothing at the
-- database level stops a tier naming a programme that does not exist, and the
-- engine is what catches it -- which it does, as 'unusable', never 'available'.
create table if not exists public.rf_warranty_tiers (
  id                  uuid primary key default gen_random_uuid(),
  license_hash        text not null,
  tier_id             text not null,                 -- client-generated
  manufacturer        text not null,
  tier_name           text not null,
  requires_program_id text,                          -- null = no certification condition
  -- The contractor's own citation for this tier and its condition. The engine
  -- refuses to evaluate a tier without one, so this is not decoration.
  source              text,
  notes               text,
  active              boolean not null default true,
  data                jsonb not null default '{}'::jsonb,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  updated_by          text,
  unique (license_hash, tier_id),
  constraint rfwt_data_size check (octet_length(data::text) <= 65536),
  constraint rfwt_source_size check (source is null or octet_length(source) <= 2048)
);

create index if not exists idx_rfwt_license on public.rf_warranty_tiers(license_hash);

-- ---------------------------------------------------------------------------
-- 2. One warranty per job, and its registration clock.
-- ---------------------------------------------------------------------------
-- REGISTER_WITHIN_DAYS IS STORED PER WARRANTY, NOT PER TIER, and that is a
-- deliberate call. The window is a term of the programme in force when the
-- roof was installed; a contractor who later renegotiates or moves tier must
-- not silently re-date every historical roof's deadline. Copying the figure
-- onto the row at creation freezes it, the same reason rf_claim_agreements
-- stores the rescission window it was written under rather than looking up
-- today's.
--
-- It is NULLABLE and there is no default. A null produces
-- 'no_deadline_stated', which is honest. A DEFAULT 30 here would be this file
-- inventing a manufacturer's term for every roof that ever gets entered.
create table if not exists public.rf_job_warranties (
  id                   uuid primary key default gen_random_uuid(),
  license_hash         text not null,
  warranty_id          text not null,                -- client-generated
  job_id               text,
  manufacturer         text,
  tier_id              text,
  tier_name            text,                         -- denormalised: what was SOLD, even if the tier is later renamed
  status               text not null default 'not_registered',
  installed_on         date,
  registered_on        date,
  register_within_days integer,
  registration_number  text,
  coverage_years       integer,
  coverage_expires_on  date,
  notes                text,
  data                 jsonb not null default '{}'::jsonb,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  updated_by           text,
  unique (license_hash, warranty_id),
  constraint rfjw_status_check check (status in ('not_registered','submitted','registered','registration_rejected','void')),
  constraint rfjw_within_days_sane check (register_within_days is null or (register_within_days >= 0 and register_within_days <= 3650)),
  constraint rfjw_coverage_years_sane check (coverage_years is null or (coverage_years >= 0 and coverage_years <= 100)),
  constraint rfjw_registered_needs_date check (status <> 'registered' or registered_on is not null),
  constraint rfjw_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_rfjw_license on public.rf_job_warranties(license_hash);
create index if not exists idx_rfjw_job on public.rf_job_warranties(license_hash, job_id);
-- The one query this table exists to answer quickly: what is about to lose its
-- enhanced coverage.
create index if not exists idx_rfjw_installed on public.rf_job_warranties(license_hash, status, installed_on);

-- ---------------------------------------------------------------------------
-- 3. RLS and grants.
-- ---------------------------------------------------------------------------
-- Service-role only, matching rf_company_programs exactly. SELECT/INSERT/
-- UPDATE and no DELETE: a warranty entered in error is voided, which a later
-- reader needs to see, not deleted.
alter table public.rf_warranty_tiers enable row level security;
drop policy if exists "svc only rf_warranty_tiers" on public.rf_warranty_tiers;
create policy "svc only rf_warranty_tiers" on public.rf_warranty_tiers
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.rf_warranty_tiers from service_role;
grant select, insert, update on public.rf_warranty_tiers to service_role;
revoke all on public.rf_warranty_tiers from anon, authenticated;

alter table public.rf_job_warranties enable row level security;
drop policy if exists "svc only rf_job_warranties" on public.rf_job_warranties;
create policy "svc only rf_job_warranties" on public.rf_job_warranties
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.rf_job_warranties from service_role;
grant select, insert, update on public.rf_job_warranties to service_role;
revoke all on public.rf_job_warranties from anon, authenticated;

-- ---------------------------------------------------------------------------
-- 4. Verify, do not assume.
-- ---------------------------------------------------------------------------
--   select count(*) from rf_warranty_tiers;   -- expect 0, nothing is seeded
--   select count(*) from rf_job_warranties;   -- expect 0
--
-- Grants (expect INSERT,SELECT,UPDATE on both; no DELETE, no TRUNCATE):
--   select table_name, string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name in ('rf_warranty_tiers','rf_job_warranties')
--    group by table_name;
--
-- Confirm the registered-needs-a-date constraint bites (expect an ERROR):
--   insert into public.rf_job_warranties (license_hash, warranty_id, status)
--   values ('test', 'RFJW-CHECK', 'registered');
--
-- Then re-run sql/schema_snapshot_query.sql so db/schema_snapshot.json carries
-- these tables. Until that happens the preflight reports them as undeclared
-- against live, which is correct and not a failure.
