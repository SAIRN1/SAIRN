-- sql/sairnsenior_applicants_schema.sql
-- SAIRNsenior caregiver hiring funnel -- Supabase schema (2026-09-02)
--
-- Competitive-gap audit item A5. Additive and idempotent; run after
-- sql/sairnsenior_caregivers_schema.sql. Nothing in that file is duplicated
-- here.
--
-- WHAT THIS STORES. One table:
--
--   sen_applicants  one person who applied to work here, the source that sent
--                   them, the stage they reached, and -- once hired -- the
--                   sen_caregivers row they became.
--
-- WHY THE OUTCOME IS A LINK AND NOT A NUMBER, the same reasoning the referral
-- schema beside this one gives: every figure the app reports against a source
-- is computed from records that already exist. A hired applicant carries a
-- caregiver_id, and retention is then measured from sen_visits -- did that
-- caregiver actually complete work on or after the ninety-day mark. Storing a
-- "retention rate" on the source row would be a number that drifts away from
-- the visits it came from the first time a visit is edited.
--
-- ── WHY THIS IS WORTH A TABLE AT ALL ────────────────────────────────────
-- The audit records A5 as BASELINE in this vertical rather than an enterprise
-- extra -- applicant tracking is native in both AxisCare and Aaniie at Tier A
-- -- and names caregiver turnover as "the market's defining operational
-- problem". A bolt-on ATS can count applications. It cannot say which sources
-- produce caregivers who are still working three months later, because that
-- needs the applicant joined to the caregiver joined to the visit history, and
-- only the system of record holds all three.
--
-- ── NO DERIVED DATES AND NO DERIVED OUTCOMES ────────────────────────────
-- hired_on is the date the agency records, not the date the row was written.
-- An applicant hired before this feature existed can therefore be entered with
-- their real hire date and measured correctly, which a created_at-based
-- inference would get wrong for every historical row.
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy -- matching
-- every other sen_* table. The API gate is the INTAKE role set (management +
-- coordinator + scheduler), not management alone: an applicant record is
-- employment data about someone who is not yet staff, so a caregiver is out,
-- but the coordinator who screens the call is in. Same gate and same server
-- branch as sen_referral_sources.
--
-- NO DELETE GRANT. sql/unused_delete_grant_revoke_2026-08-24.sql revoked it
-- platform-wide and no code path here deletes. This file is `create table if
-- not exists` and safe to re-run, so granting delete would silently restore
-- what that sweep removed.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.sen_applicants (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairnsenior',
  applicant_id  text not null,
  data          jsonb not null default '{}'::jsonb,   -- name, phone, email, source, stage (applied|screened|interviewed|offered|hired|rejected|withdrawn), applied_on, hired_on, caregiver_id, role, notes, created_at
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, applicant_id),
  constraint senap_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_senap_license on public.sen_applicants(license_hash);

alter table public.sen_applicants enable row level security;

drop policy if exists "svc only sen_applicants" on public.sen_applicants;

create policy "svc only sen_applicants" on public.sen_applicants
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update on public.sen_applicants to service_role;
revoke all on public.sen_applicants from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sen_applicants;
--
-- Confirm no delete grant took hold (expect SELECT, INSERT, UPDATE only):
--   select privilege_type from information_schema.role_table_grants
--    where grantee = 'service_role' and table_name = 'sen_applicants';
