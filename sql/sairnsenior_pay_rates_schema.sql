-- sql/sairnsenior_pay_rates_schema.sql
-- SAIRNsenior caregiver pay rates -- Supabase schema (2026-09-02)
--
-- Competitive-gap audit item B5 ("consolidated + per-branch P&L",
-- Tier-B-defining). Additive and idempotent; run after
-- sql/sairnsenior_branches_schema.sql and
-- sql/sairnsenior_payer_contracts_schema.sql. Nothing in either is duplicated
-- here.
--
-- WHAT THIS STORES. One table:
--
--   sen_pay_rates   what ONE employee is paid per hour, for a stated period,
--                   and the employer burden carried on top of that wage.
--
-- ── THIS CLOSES A GAP THIS PLATFORM DECLARED ON ITSELF ──────────────────
-- The Branches panel (B1, 2026-09-02) shipped with this printed on it:
--
--   "No cost, overhead or payroll data is held by this app, so no margin or
--    profit figure is computed here -- the revenue half is real and the other
--    half is absent rather than estimated."
--
-- That was the correct call at the time: a margin computed with no cost data is
-- an invented number on a screen a Tier B buyer decides from. This table is the
-- missing half, so the figure can be computed from something real rather than
-- filled in.
--
-- ── SYMMETRIC TO sen_payer_contracts, ON PURPOSE ────────────────────────
-- A payer contract says what an hour EARNS; a pay rate says what an hour COSTS.
-- Both are effective-dated, both resolve against the SERVICE DATE rather than
-- today, and both REFUSE when two equally applicable records are in force
-- instead of picking one. A visit worked in March is costed at March's wage,
-- not at the wage the caregiver was moved to in July -- resolving against today
-- would silently restate every historical margin the next time anyone got a
-- rise.
--
-- ── KEYED ON employee_id, WHICH IS WHAT A VISIT ACTUALLY CARRIES ────────
-- sen_visits stores `assigned_employee_id` from the auth roster, NOT a
-- sen_caregivers row id. Keying pay on the caregiver record would join to
-- nothing, and a cost of zero that comes from a failed join looks exactly like
-- a cost of zero that is real.
--
-- ── THE MISSING-RATE CASE IS COUNTED, NEVER TREATED AS FREE LABOUR ──────
-- A visit whose employee has no rate in force contributes HOURS but no COST.
-- Left silent, that understates cost and therefore OVERSTATES margin -- the
-- branch with the worst record-keeping looks like the most profitable one.
-- Every uncosted visit is counted, reported per branch, and the margin is
-- labelled overstated wherever the count is above zero. The direction of the
-- error is known, so it is stated rather than hedged.
--
-- ── burden_pct SITS ON THE RATE, NOT ON THE AGENCY ──────────────────────
-- Employer payroll taxes, workers' compensation and benefits are real money and
-- they differ by worker: a W-2 aide carries burden and a 1099 contractor does
-- not. One agency-wide percentage would be wrong for any agency running both.
-- It DEFAULTS TO ZERO and zero is not a claim that burden is zero -- it means
-- burden is not modelled for that worker, and the panel says the margin is
-- overstated by whatever it really is.
--
-- ── WHAT THIS STILL IS NOT: THIS IS GROSS MARGIN, NOT PROFIT ────────────
-- Direct labour is the only cost here. No office rent, no supervision, no
-- mileage, no software, no insurance beyond the burden percentage, no
-- administrative salaries. Calling the result "profit" or "P&L" would be the
-- fabrication this table exists to avoid, so the panel calls it gross margin
-- and says what is excluded. The audit asks for per-branch P&L; this delivers
-- the direct-labour half honestly rather than the whole thing dishonestly.
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy -- matching
-- every other sen_* table. The API gate is MANAGEMENT-ONLY for read AND write,
-- the narrowest gate in this app, matching sen_payer_contracts. A wage is the
-- most sensitive record SAIRNsenior holds: a coordinator or scheduler has no
-- minimum-necessary reason to know what a colleague earns, and unlike an
-- authorisation's units it is not scheduling capacity.
--
-- NO DELETE GRANT. sql/unused_delete_grant_revoke_2026-08-24.sql revoked it
-- platform-wide and no code path here deletes. A superseded rate is given a
-- term_on and keeps its history -- deleting it would leave every visit costed
-- under it with no explanation of where the figure came from, and would
-- silently change a margin that has already been reported.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.sen_pay_rates (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairnsenior',
  rate_id       text not null,
  data          jsonb not null default '{}'::jsonb,   -- employee_id, employee_name, rate_per_hour, burden_pct, effective_on, term_on, notes, created_at
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, rate_id),
  constraint senpr_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_senpr_license on public.sen_pay_rates(license_hash);

alter table public.sen_pay_rates enable row level security;

drop policy if exists "svc only sen_pay_rates" on public.sen_pay_rates;

create policy "svc only sen_pay_rates" on public.sen_pay_rates
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update on public.sen_pay_rates to service_role;
revoke all on public.sen_pay_rates from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sen_pay_rates;
--
-- Confirm no delete grant took hold (expect SELECT, INSERT, UPDATE only):
--   select privilege_type from information_schema.role_table_grants
--    where grantee = 'service_role' and table_name = 'sen_pay_rates';
