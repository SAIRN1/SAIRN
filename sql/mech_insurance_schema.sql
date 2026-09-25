-- sql/mech_insurance_schema.sql
-- SAIRNmechanical -- the BUSINESS's own insurance policies and the COI packet.
--
-- Run as the project owner in the Supabase SQL editor. Idempotent: safe to
-- re-run, and re-running is how a registry created before a column existed
-- gets it.
--
-- ── WHY THIS TABLE EXISTS ──────────────────────────────────────────────────
-- Measured 2026-09-25 before it was built: sairnmechanical.html had ZERO hits
-- for insurance, certificate of insurance, general liability, workers comp,
-- umbrella or COI. There was no insurance concept in the app at all.
--
-- It is NOT a second copy of mech_credentials. That table holds what an
-- EMPLOYEE holds -- an EPA 608 card, a NATE certificate -- and answers "who can
-- I dispatch". This one holds what the COMPANY holds and answers "may this
-- company be on that site at all". A technician with a current card working for
-- a business whose general liability lapsed last month is dispatchable under
-- one and refused at the gate by the other.
--
-- ── EVERY LIMIT IS NULLABLE WITH NO DEFAULT, AND THAT IS LOAD-BEARING ──────
-- The same argument mech_site_assets.refrigerant_charge_lb carries. A limit
-- defaulted to 0 would fail every requirement for a reason nobody typed, and
-- people learn to ignore a board that cries wolf. A limit defaulted to
-- anything else would tell a contractor they carry cover they have no evidence
-- of. NULL means "nobody has typed what the certificate says", which is a
-- third answer, and api/_lib/mech-insurance.js reports it as `unknown_limit`.
--
-- ── EXPIRY IS NULLABLE TOO, AND NULL IS NOT "FINE" ─────────────────────────
-- A policy with no expiry recorded reads `no_expiry_recorded`, NEVER `current`.
-- A certificate holder asking for proof of current coverage is asking a
-- question that record cannot answer.
--
-- ── THE ENDORSEMENTS ARE THREE-STATE BOOLEANS ──────────────────────────────
-- true = the certificate says so, false = it says not, NULL = nobody recorded
-- it. Only a recorded true satisfies a requirement. Defaulting any of them to
-- false would turn "we never checked" into "we checked and it is not there",
-- and defaulting to true would tell an owner the contractor has
-- additional-insured status they were never granted.
--
-- ── NOT APPEND-ONLY, AND THE SAME REASON mech_site_assets IS NOT ───────────
-- A policy record is a DESCRIPTION of a certificate: a policy number gets
-- corrected, a carrier name is re-read off the ACORD form. A renewal is a NEW
-- ROW with its own dates, which is how the engine can show "current cover"
-- while the prior term stays on the record.

create table if not exists public.mech_insurance_policies (
  id                    uuid primary key default gen_random_uuid(),
  license_hash          text not null,
  policy_key            text not null,        -- client-generated, stable, unique per licence
  kind                  text not null,        -- validated in api/_lib/mech-insurance.js (POLICY_KINDS)
  carrier               text,
  policy_no             text,
  effective_on          date,
  expires_on            date,                 -- NULL = no expiry recorded. NEVER "fine".
  -- Money, in DOLLARS as printed on the certificate. The engine converts to
  -- integer cents once, at its boundary, and every comparison after that is
  -- integer -- the IEEE754 lesson from api/_lib/dnt-rollup.js.
  each_occurrence       numeric(14,2),        -- NULL = not recorded. NEVER default 0.
  aggregate_limit       numeric(14,2),        -- NULL = not recorded. NEVER default 0.
  certificate_holder    text,
  -- Three-state, all of them. See the header.
  additional_insured        boolean,
  waiver_of_subrogation     boolean,
  primary_noncontributory   boolean,
  per_project_aggregate     boolean,
  status                text not null default 'active',   -- active | superseded
  notes                 text,
  recorded_by           text,                 -- employee_id from the verified session
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (license_hash, policy_key)
);

-- Idempotent for an install that ran an earlier version of this file.
alter table public.mech_insurance_policies
  add column if not exists certificate_holder      text,
  add column if not exists primary_noncontributory boolean,
  add column if not exists per_project_aggregate   boolean;

create index if not exists idx_mech_ins_license
  on public.mech_insurance_policies (license_hash, created_at desc);
-- "what expires next" is the question this table is asked most.
create index if not exists idx_mech_ins_expiry
  on public.mech_insurance_policies (license_hash, expires_on);
-- And "do I have a current X" -- the readiness comparison walks by kind.
create index if not exists idx_mech_ins_kind
  on public.mech_insurance_policies (license_hash, kind, expires_on desc);

alter table public.mech_insurance_policies enable row level security;

-- SELECT, INSERT and UPDATE. The UPDATE is the same considered exception
-- mech_site_assets carries -- a policy record is a description of a
-- certificate, not evidence in itself. Still NO DELETE: a lapsed policy is part
-- of the coverage history somebody may have to answer for.
grant select, insert, update on public.mech_insurance_policies to service_role;

-- ── VERIFY ──────────────────────────────────────────────────────────────────
-- Expect the columns below and ZERO rows.
select column_name, data_type, is_nullable, column_default
  from information_schema.columns
 where table_schema = 'public' and table_name = 'mech_insurance_policies'
 order by ordinal_position;

select count(*) as should_be_zero from public.mech_insurance_policies;

-- THE LIMITS AND THE EXPIRY MUST BE NULLABLE WITH NO DEFAULT. If any of these
-- says NO, or shows a default, the board is now reporting coverage nobody
-- recorded -- either failing every requirement against a defaulted 0, or
-- clearing one against a defaulted figure:
select column_name, is_nullable, column_default
  from information_schema.columns
 where table_schema = 'public' and table_name = 'mech_insurance_policies'
   and column_name in ('each_occurrence', 'aggregate_limit', 'expires_on')
 order by column_name;
-- Expect THREE rows, all is_nullable = YES, all column_default = NULL.

-- And the four endorsements, on the identical argument. A false default turns
-- "we never checked" into "we checked and it is not there"; a true default
-- tells an owner the contractor holds status they were never granted:
select column_name, is_nullable, column_default
  from information_schema.columns
 where table_schema = 'public' and table_name = 'mech_insurance_policies'
   and column_name in ('additional_insured', 'waiver_of_subrogation',
                       'primary_noncontributory', 'per_project_aggregate')
 order by column_name;
-- Expect FOUR rows, all is_nullable = YES, all column_default = NULL.
-- FOUR ROWS. Fewer means the ALTER above did not run and the readiness
-- comparison is reading columns that are not there.

-- And confirm the grant is select+insert+update, with NO delete:
select privilege_type
  from information_schema.role_table_grants
 where table_schema = 'public' and table_name = 'mech_insurance_policies'
   and grantee = 'service_role'
 order by privilege_type;
-- Expect exactly: INSERT, SELECT, UPDATE
