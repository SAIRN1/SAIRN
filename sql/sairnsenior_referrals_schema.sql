-- sql/sairnsenior_referrals_schema.sql
-- SAIRNsenior referral-source CRM -- Supabase schema (2026-09-02)
--
-- Competitive-gap audit item A7. Additive and idempotent; run after
-- sql/sairnsenior_clients_schema.sql. Nothing in that file is duplicated here.
--
-- WHAT THIS STORES. Two tables:
--
--   sen_referral_sources  the relationship: a hospital, skilled nursing
--                         facility, physician practice, discharge planner,
--                         community organisation or family contact, with the
--                         named person the agency actually deals with.
--   sen_referrals         one referred person and what happened to them --
--                         referred on a date by a source, then Pending,
--                         Admitted, Declined or Lost, and when admitted, the
--                         sen_clients row they became.
--
-- WHY THE OUTCOME IS A LINK AND NOT A NUMBER. Every figure the app reports
-- against a source (conversion, time to admission, hours delivered, revenue) is
-- computed from records that already exist -- sen_clients, sen_visits,
-- sen_claims -- by following client_id. A referral marked Admitted with no
-- client_id contributes NOTHING to those figures and is reported as unlinked
-- rather than estimated. Storing an attributed revenue figure on this row would
-- create a second source of truth that drifts from the claims it came from.
--
-- ACCESS. Registered in api/_resources/sairnsenior.js and served by a bespoke
-- branch in api/sd-data.js gated on SEN_CLIENT_BROAD_READ_ROLES -- owner,
-- billing, coordinator, scheduler -- for BOTH read and write.
--   * Not management-only (the sen_claims gate): coordinators and schedulers
--     are the people who take the referral call, and putting the pipeline out
--     of their reach is how a pipeline goes stale.
--   * Not every employee (the sen_caregivers read gate): a referral row names a
--     PROSPECTIVE client and the reason they were referred. That is PHI about
--     someone who is not yet a client, and a caregiver has no part in it.
--   * Read and write are the same set deliberately: whoever can see a referral
--     is whoever records its outcome.
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy -- matching
-- every other sen_* table. api/sd-data.js is the only door in.
--
-- NO DELETE GRANT. sql/unused_delete_grant_revoke_2026-08-24.sql revoked it
-- platform-wide across 134 tables; the only reachable delete path anywhere is
-- api/sd-data.js's SC_RESOURCES branch. This file is `create table if not
-- exists` and safe to re-run, so granting delete here would silently restore
-- what that sweep removed. Do not add it.
--
-- SIZE CAP: 64KB of jsonb per row, matching api/sd-data.js's uniform
-- MAX_PAYLOAD_BYTES.

create extension if not exists pgcrypto;

create table if not exists public.sen_referral_sources (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnsenior',
  source_id    text not null,
  data         jsonb not null default '{}'::jsonb,   -- name, type (hospital|snf|physician|community|family|other), contact_name, contact_role, phone, email, address, notes, active, created_at
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, source_id),
  constraint senrs_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_senrs_license on public.sen_referral_sources(license_hash);

create table if not exists public.sen_referrals (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnsenior',
  referral_id  text not null,
  data         jsonb not null default '{}'::jsonb,   -- source_id, referred_name, referred_on, payer, reason, status (pending|admitted|declined|lost), decided_on, client_id, decline_reason, touches[{on, kind, note}], notes, created_at
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, referral_id),
  constraint senrf_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_senrf_license on public.sen_referrals(license_hash);

alter table public.sen_referral_sources enable row level security;
alter table public.sen_referrals        enable row level security;

drop policy if exists "svc only sen_referral_sources" on public.sen_referral_sources;
drop policy if exists "svc only sen_referrals"        on public.sen_referrals;

create policy "svc only sen_referral_sources" on public.sen_referral_sources
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sen_referrals" on public.sen_referrals
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update on public.sen_referral_sources to service_role;
grant select, insert, update on public.sen_referrals        to service_role;
