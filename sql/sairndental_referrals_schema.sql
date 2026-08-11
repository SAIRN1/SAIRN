-- sql/sairndental_referrals_schema.sql
-- New table for SAIRNdental's referral-tracking feature (2026-08-11).
-- Matches every existing dnt_* table's exact shape (see
-- sql/sairndental_data_schema.sql for the pattern this mirrors) --
-- license_hash-scoped, jsonb data payload, 64KB size cap (this
-- resource has no photos/large payloads, the standard cap is
-- appropriate here unlike dnt_appointments' still-open oversized-data
-- question). See
-- docs/superpowers/specs/2026-08-11-sairndental-referral-tracking-design.md.

create table if not exists public.dnt_referrals (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  referral_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, referral_id), constraint dntrf_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntrf_license on public.dnt_referrals(license_hash);

-- ── RLS: service-role only, matching sql/sairndental_data_schema.sql's
-- established pattern for every other dnt_* table (that file's own RLS
-- block predates this table, so it isn't covered there — this closes
-- the gap for dnt_referrals specifically). ──
alter table public.dnt_referrals enable row level security;
drop policy if exists "svc only dnt_referrals" on public.dnt_referrals;
create policy "svc only dnt_referrals" on public.dnt_referrals for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
grant select, insert, update, delete on public.dnt_referrals to service_role;
