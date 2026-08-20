-- sql/sairncode_credentials_schema.sql
-- Per-practice (per-license) storage for the practice's OWN third-party
-- service credentials -- the "bring your own credential" layer behind
-- SAIRNcode's eligibility, prior-auth, and code-data-licensing
-- integrations. Run this once in the Supabase SQL editor before
-- api/sc-credentials.js or api/sc-eligibility.js will work.
--
-- WHY THIS IS NEW INFRASTRUCTURE, NOT AN EXTENSION OF AN EXISTING PATTERN:
-- Verified 2026-08-20 against the whole repo -- no per-tenant credential
-- storage existed anywhere on this platform before this table. Every
-- third-party API key in api/ (COURTLISTENER_API_TOKEN, STABILITY_API_KEY,
-- RESEND_API_KEY, ANTHROPIC_API_KEY, ...) is a single PLATFORM-WIDE Vercel
-- env var shared by every customer. SAIRNlaw's citator in particular is
-- often described as "bring your own" -- it is not; api/courtlistener.js's
-- own header says the token is "Shared by every SAIRNlaw firm."
--
-- The deliberate difference here: an eligibility (270/271) request carries
-- real patient identifiers. Using one SAIRN-owned clearinghouse account for
-- every practice would make SAIRN the business associate for every
-- practice's PHI traffic. Each practice using its own clearinghouse account
-- keeps that relationship (and its BAA) between the practice and the
-- clearinghouse, where it already exists.
--
-- HOW SECRETS ARE STORED: values in `data` are NEVER plaintext. Each is
-- encrypted with api/_lib/auth.js's existing AES-256-GCM encryptSecret()
-- (same helper already used for MFA/TOTP secrets), keyed off SD_AUTH_SECRET.
-- This is defense in depth on top of RLS + service-role-only access, not a
-- replacement for it -- the same reasoning sql/sairnlaw_employee_auth_
-- schema.sql documents for mfa_secret_encrypted.
--
-- LIMITATION, STATED PLAINLY: all tenants' credentials are encrypted under
-- one key derived from a single platform-wide SD_AUTH_SECRET. Compromise of
-- that secret plus database read access would expose every stored
-- credential. Per-tenant key derivation or a real KMS would be the stronger
-- posture and is a deliberate, documented future step -- not silently
-- assumed to be already handled.
--
-- One row per license (singleton), same shape convention as dnt_settings:
-- credential_id is always the literal 'default'.

create table if not exists public.sc_credentials (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairncode',
  credential_id text not null default 'default',
  data          jsonb not null default '{}'::jsonb,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, credential_id),
  constraint sc_credentials_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sc_credentials_license on public.sc_credentials(license_hash);

alter table public.sc_credentials enable row level security;
drop policy if exists "svc only sc_credentials" on public.sc_credentials;
create policy "svc only sc_credentials" on public.sc_credentials for all using (false) with check (false);

grant select, insert, update, delete on public.sc_credentials to service_role;
revoke all on public.sc_credentials from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sc_credentials;
