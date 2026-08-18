-- sql/sairncash_trial_schema.sql
-- Real backing table for SAIRNcash's 30-day free trial (no Stripe
-- dependency -- Michael's 2026-08-18 decision to hold off on a real
-- Stripe account and build a trial instead). Same server-authoritative
-- standard the 2026-08-10 audit already enforced for isSubscribed()
-- (real expiresAt, never a client-only timer), extended to a
-- trial-expiry field instead of a subscription-expiry field. See
-- docs/superpowers/specs/2026-08-18-sairncash-trial-flow-design.md.
--
-- trial_token is the bearer credential the client holds (mirrors
-- subscriptionId's role in the existing Stripe flow) -- not the email.
-- Renewal is admin-approval-only (api/sairncash/trial-renew.js, gated
-- by SAIRNCASH_ADMIN_SECRET) -- never self-service.
--
-- Run this in Supabase's SQL editor.
create table if not exists public.sairncash_trial (
  id                 uuid primary key default gen_random_uuid(),
  email              text not null unique,
  trial_token        text not null unique,
  started_at         timestamptz not null default now(),
  expires_at         timestamptz not null,
  status             text not null default 'active' check (status in ('active','expired','revoked')),
  renewal_count      integer not null default 0,
  last_renewed_at    timestamptz,
  last_renewed_note  text,
  created_at         timestamptz not null default now()
);
create index if not exists idx_sairncash_trial_token on public.sairncash_trial (trial_token);
alter table public.sairncash_trial enable row level security;
drop policy if exists "svc only sairncash_trial" on public.sairncash_trial;
create policy "svc only sairncash_trial" on public.sairncash_trial
  for all using (false) with check (false);
grant select, insert, update on public.sairncash_trial to service_role;
revoke all on public.sairncash_trial from anon, authenticated;

-- Verify after running:
--   select * from sairncash_trial limit 5;
-- should return 0 rows (empty table, no error).
