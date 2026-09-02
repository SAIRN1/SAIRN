-- sql/sairnsenior_branches_schema.sql
-- SAIRNsenior multi-branch / multi-state operation -- Supabase schema (2026-09-02)
--
-- Competitive-gap audit item B1, and the enabler for B3 and B5. Additive and
-- idempotent; run after sql/sairnsenior_clients_schema.sql and
-- sql/sairnsenior_caregivers_schema.sql. Nothing in either is duplicated here.
--
-- WHAT THIS STORES. One table:
--
--   sen_branches  an office the agency operates from: its name, the STATE it
--                 operates in, and whether it is still open.
--
-- ── THE STATE IS THE POINT, NOT THE ADDRESS ──────────────────────────────
-- The audit calls multi-branch/multi-state the defining Tier B requirement and
-- records that SAIRNroofing and SAIRNdental both capture location while
-- SAIRNsenior captures none. But a branch in this vertical is not a label on a
-- report: EVV aggregators, Medicaid programmes and caregiver training-hour
-- requirements are all set PER STATE, and this app already scopes two of those
-- three by a state it currently holds in exactly one place --
-- sen_settings.evv_config.state, a single agency-wide value.
--
-- A two-state agency therefore has one EVV state today and it is wrong for one
-- of them. Recording state on the branch is what makes that fixable. This file
-- does NOT rewire the EVV or training selection onto it -- that is a separate,
-- deliberate change with its own verification -- so the state stored here is
-- captured and reported and is not yet consulted by those two. Said plainly so
-- nobody reads the column as already-enforced.
--
-- ── ASSIGNMENT LIVES ON THE ROWS THAT ALREADY EXIST ──────────────────────
-- branch_id is a field on sen_clients and sen_caregivers, not a join table.
-- Both already store free-form jsonb, so no migration is needed for them: an
-- existing row simply has no branch_id and reads as UNASSIGNED. Unassigned is
-- reported as its own bucket everywhere, never folded into the first branch and
-- never dropped from a total -- a rollup that silently omits rows is how a
-- shortfall looks like an all-clear.
--
-- A visit and a claim inherit their branch from the CLIENT rather than storing
-- their own. The alternative -- stamping the branch onto every visit at
-- creation -- would freeze it, so moving a client to another office would leave
-- their history attributed to the old one forever, and correcting it would mean
-- rewriting historical rows. Deriving costs a lookup and cannot go stale.
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy -- matching
-- every other sen_* table. The API gate is deliberately split, matching
-- sen_settings rather than the referral family: READ is open to any signed-in
-- employee, because a caregiver's own roster row names a branch and the name
-- has to resolve or the screen shows a raw id; WRITE is management-only,
-- because opening or closing an office is not a scheduling decision.
--
-- NO DELETE GRANT. sql/unused_delete_grant_revoke_2026-08-24.sql revoked it
-- platform-wide and no code path here deletes. A closed office is `active:
-- false` and keeps its history; deleting it would orphan every client and
-- caregiver ever assigned to it.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.sen_branches (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairnsenior',
  branch_id     text not null,
  data          jsonb not null default '{}'::jsonb,   -- name, state (2-letter), address, phone, active, notes, created_at
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, branch_id),
  constraint senbr_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_senbr_license on public.sen_branches(license_hash);

alter table public.sen_branches enable row level security;

drop policy if exists "svc only sen_branches" on public.sen_branches;

create policy "svc only sen_branches" on public.sen_branches
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update on public.sen_branches to service_role;
revoke all on public.sen_branches from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sen_branches;
--
-- Confirm no delete grant took hold (expect SELECT, INSERT, UPDATE only):
--   select privilege_type from information_schema.role_table_grants
--    where grantee = 'service_role' and table_name = 'sen_branches';
