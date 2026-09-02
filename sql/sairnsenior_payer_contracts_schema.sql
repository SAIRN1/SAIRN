-- sql/sairnsenior_payer_contracts_schema.sql
-- SAIRNsenior payer contract management -- Supabase schema (2026-09-02)
--
-- Competitive-gap audit item B4 ("payer contract management across many
-- payers/states + MCO authorisation -- Tier-B-defining. Absent."). Additive
-- and idempotent; run after sql/sairnsenior_clients_schema.sql and
-- sql/sairnsenior_branches_schema.sql. Nothing in either is duplicated here.
--
-- WHAT THIS STORES. One table:
--
--   sen_payer_contracts  what a payer pays, per hour, for a stated period --
--                        optionally scoped to one state -- and whether that
--                        payer requires prior authorisation.
--
-- ── THE PROBLEM IT ACTUALLY SOLVES ──────────────────────────────────────
-- Before this, generateClaim() created every claim with `rate: 0` and the
-- biller typed the rate in by hand, one claim at a time, from memory or a
-- spreadsheet. That is not merely laborious: a rate typed from memory is how a
-- multi-payer agency under-bills for months without noticing, and there is
-- nothing in the record afterwards that says which rate was SUPPOSED to apply.
-- The contract is that record.
--
-- ── SCOPE RESOLUTION IS DECLARED, AND AMBIGUITY REFUSES ─────────────────
-- A contract with a `state` applies only in that state; a contract without one
-- is agency-wide. A state-scoped contract BEATS an agency-wide one for the same
-- payer -- specific beats general, stated here rather than emerging from row
-- order.
--
-- WHEN TWO CONTRACTS ARE EQUALLY SPECIFIC AND BOTH IN FORCE, THE ENGINE
-- REFUSES AND SAYS SO. It does not pick the newer, the higher, or the first
-- row. Billing at a rate nobody chose is worse than billing at zero, because a
-- zero is visible on the screen and a plausible wrong rate is not.
--
-- THE STATE COMES FROM THE CLIENT'S BRANCH, and a client with no branch has no
-- known state -- so a state-scoped contract does NOT match them. Matching it
-- anyway would be assuming the state, which is the whole thing this column
-- exists to stop.
--
-- ── DATES ARE THE SERVICE DATE, NEVER TODAY ─────────────────────────────
-- A claim is billed under the contract in force on the day the WORK was done.
-- Resolving against today would re-rate historical claims every time a contract
-- is renewed, and would silently change what an already-submitted claim says it
-- was worth.
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy -- matching
-- every other sen_* table. The API gate is MANAGEMENT ONLY for both read and
-- write, matching sen_claims rather than the referral family: a contracted rate
-- is financial data, and a caregiver, coordinator or scheduler has no
-- minimum-necessary reason to see what each payer pays.
--
-- NO DELETE GRANT. sql/unused_delete_grant_revoke_2026-08-24.sql revoked it
-- platform-wide and no code path here deletes. An expired contract is given a
-- term_on and keeps its history -- deleting it would leave every claim it
-- priced with no explanation of where the rate came from.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.sen_payer_contracts (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairnsenior',
  contract_id   text not null,
  data          jsonb not null default '{}'::jsonb,   -- payer, plan_name, state (2-letter or blank = agency-wide), rate_per_hour, effective_on, term_on, requires_authorization, auth_note, notes, created_at
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, contract_id),
  constraint senpc_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_senpc_license on public.sen_payer_contracts(license_hash);

alter table public.sen_payer_contracts enable row level security;

drop policy if exists "svc only sen_payer_contracts" on public.sen_payer_contracts;

create policy "svc only sen_payer_contracts" on public.sen_payer_contracts
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update on public.sen_payer_contracts to service_role;
revoke all on public.sen_payer_contracts from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sen_payer_contracts;
--
-- Confirm no delete grant took hold (expect SELECT, INSERT, UPDATE only):
--   select privilege_type from information_schema.role_table_grants
--    where grantee = 'service_role' and table_name = 'sen_payer_contracts';
