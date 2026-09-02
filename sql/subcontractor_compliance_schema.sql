-- sql/subcontractor_compliance_schema.sql
-- SHARED subcontractor directory, compliance and assignment tables.
-- Run once in the Supabase SQL editor. Safe to re-run (idempotent).
--
-- ══ WHY THESE ARE UNPREFIXED ═══════════════════════════════════════════════
-- Almost every table on this platform is app-prefixed (rf_, sd_, sen_) because
-- almost every table belongs to one app. These do not. The worldwide
-- competitive-gap audit names subcontractor management as a Tier-A gap for
-- SAIRNroofing (A3), StoneDesk has already built its own (sd_subs /
-- sd_sub_auth / sd_sub_jobs, 2026-09-01), and SAIRNbuild is the obvious third.
-- Building it a third time per app is the duplication CLAUDE.md records as
-- SAIRNsenior's root cause.
--
-- So these follow the SHARED convention already on the platform -- `employees`,
-- `business_profiles`, `ai_memories`, `network_insights` -- and carry `app_id`
-- so one table serves every consumer while keeping tenants and apps apart.
--
-- ══ WHAT THIS DOES NOT TOUCH, DELIBERATELY ═════════════════════════════════
-- StoneDesk's sd_subs / sd_sub_auth / sd_sub_jobs are LEFT ALONE. sd_sub_auth
-- is a live credential table -- pin_hash, pin_salt, failed_attempts,
-- locked_until, confirmed in the 2026-09-02 schema snapshot -- and re-keying it
-- is a credential migration in its own right, the class push-gate check 2 and
-- the recoverability guard exist for. StoneDesk repointing onto these tables is
-- a separate, guarded change. Until it happens two implementations coexist:
-- a stated, temporary cost, not an accident.
--
-- AUTHENTICATION IS NOT MODELLED HERE. There is no pin_hash column and no
-- lockout state, because sub login stays in each app's *-sub-auth endpoint
-- against api/_lib/auth.js. A shared identity table that also held credentials
-- would put every app's sub PINs in one row set on the strength of a feature
-- refactor, and that is not a trade to make quietly.
--
-- ══ SIZE BOUNDS ARE NUMERIC ON PURPOSE ═════════════════════════════════════
-- tools/sairn_sql_preflight.py compares CHECK constraints against the live
-- database only where both sides state a numeric bound -- Postgres rewrites
-- everything else beyond textual recognition. Writing these as plain
-- octet_length(...) <= N keeps them inside what the drift check can actually
-- verify. See docs/2026-09-02-constraints-not-comparable.md for what falls
-- outside it.

-- ---------------------------------------------------------------------------
-- 1. The directory. One row per subcontractor per app per licence.
-- ---------------------------------------------------------------------------
create table if not exists public.subcontractors (
  id              uuid primary key default gen_random_uuid(),
  license_hash    text not null,
  app_id          text not null,
  sub_id          text not null,                    -- client-generated
  name            text not null,
  trade           text,
  phone           text,
  email           text,
  active          boolean not null default true,
  -- Compliance documents get REAL COLUMNS, not jsonb keys, because they are
  -- queried and sorted on ("who expires this month") and because a typo in a
  -- jsonb key is invisible while a typo in a column name is an error. Same
  -- shape StoneDesk already proved in sd_subs.
  coi_carrier     text,
  coi_policy_no   text,
  coi_expiry      date,
  licence_no      text,
  licence_expiry  date,
  w9_on_file      boolean not null default false,
  data            jsonb not null default '{}'::jsonb,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (license_hash, app_id, sub_id),
  constraint subs_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_subs_license_app
  on public.subcontractors(license_hash, app_id);
-- Supports the only query this table exists to answer quickly: who is out of
-- compliance, or about to be.
create index if not exists idx_subs_coi_expiry
  on public.subcontractors(license_hash, app_id, coi_expiry);
create index if not exists idx_subs_licence_expiry
  on public.subcontractors(license_hash, app_id, licence_expiry);

-- ---------------------------------------------------------------------------
-- 2. Assignments -- scheduling and payment against a job.
-- ---------------------------------------------------------------------------
-- `job_id` is deliberately a plain text reference and NOT a foreign key. Each
-- consuming app keeps its own jobs table (rf_jobs, sd_crm, bld_bids), so a real
-- FK here would either bind this shared table to one app or need one FK per
-- app. The cost is stated rather than hidden: nothing at the database level
-- stops an assignment naming a job that does not exist, and the consuming
-- endpoint is what must check it.
create table if not exists public.sub_assignments (
  id              uuid primary key default gen_random_uuid(),
  license_hash    text not null,
  app_id          text not null,
  assignment_id   text not null,                    -- client-generated
  sub_id          text not null,
  job_id          text,
  scheduled_date  date,
  status          text not null default 'scheduled',
  -- What was agreed. Payments are appended, and what is OUTSTANDING is derived
  -- at read time by api/_lib/subcontractor-compliance.js -- never stored, the
  -- same rule sairnroofing_billing_schema.sql already applies to invoices.
  amount          numeric(12,2),
  payments        jsonb not null default '[]'::jsonb,
  data            jsonb not null default '{}'::jsonb,
  created_by      text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (license_hash, app_id, assignment_id),
  constraint subasg_status_check check (status in ('scheduled','in_progress','complete','cancelled')),
  constraint subasg_payments_is_array check (jsonb_typeof(payments) = 'array'),
  constraint subasg_amount_not_negative check (amount is null or amount >= 0),
  constraint subasg_data_size check (octet_length(data::text) <= 65536),
  constraint subasg_payments_size check (octet_length(payments::text) <= 65536)
);

create index if not exists idx_subasg_license_app
  on public.sub_assignments(license_hash, app_id);
create index if not exists idx_subasg_sub
  on public.sub_assignments(license_hash, app_id, sub_id);
create index if not exists idx_subasg_date
  on public.sub_assignments(license_hash, app_id, scheduled_date);

-- ---------------------------------------------------------------------------
-- 3. Grants.
-- ---------------------------------------------------------------------------
-- SELECT, INSERT, UPDATE and no DELETE, matching every other operational table
-- on this platform: a wrong assignment is cancelled, which a bookkeeper needs
-- to see, not deleted. Granting explicitly here rather than relying on the
-- Table Editor's auto-grant -- sql/network_schema.sql shipped with no grant
-- statement at all and the disagreement between source and live went unnoticed
-- for a month.
grant usage on schema public to service_role;
grant select, insert, update on public.subcontractors to service_role;
grant select, insert, update on public.sub_assignments to service_role;

-- No RLS policy, same reasoning as bridge_data and network_insights: read and
-- write happen exclusively through api/sd-data.js using SUPABASE_SERVICE_ROLE_KEY,
-- which bypasses RLS regardless. The anon key is never used against these.

-- ---------------------------------------------------------------------------
-- 4. Verify, do not assume.
-- ---------------------------------------------------------------------------
--   select conname, pg_get_constraintdef(oid)
--     from pg_constraint
--    where conrelid in ('public.subcontractors'::regclass,
--                       'public.sub_assignments'::regclass)
--      and contype = 'c';
--
-- Then re-run sql/schema_snapshot_query.sql so db/schema_snapshot.json carries
-- these tables. Until that happens the preflight reports them as undeclared
-- against live, which is correct and not a failure.
