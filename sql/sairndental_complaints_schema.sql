-- sql/sairndental_complaints_schema.sql
-- New table for SAIRNdental's anonymous-optional patient complaint
-- feature (2026-08-12). Matches every existing dnt_* table's shape
-- (see sql/sairndental_referrals_schema.sql for the closest
-- precedent) -- license_hash-scoped, jsonb data payload, 64KB size
-- cap -- but with one deliberate deviation: access_token is a real,
-- promoted, unique, indexed column (same reasoning as
-- dnt_settings.booking_slug in
-- sql/sairndental_availability_booking_schema.sql), because the
-- public thread endpoint must resolve a token directly to a record
-- without already knowing which practice it belongs to. See
-- docs/superpowers/specs/2026-08-12-sairndental-complaint-design.md §1.

create table if not exists public.dnt_complaints (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  complaint_id text not null, access_token text not null unique, data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, complaint_id), constraint dntcp_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntcp_license on public.dnt_complaints(license_hash);
create index if not exists idx_dntcp_token on public.dnt_complaints(access_token);

-- ── RLS: service-role only, matching sql/sairndental_referrals_schema.sql's
-- established pattern for every dnt_* table. ──
alter table public.dnt_complaints enable row level security;
drop policy if exists "svc only dnt_complaints" on public.dnt_complaints;
create policy "svc only dnt_complaints" on public.dnt_complaints for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
grant select, insert, update, delete on public.dnt_complaints to service_role;
