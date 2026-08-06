-- sql/sd_webauthn_credentials_schema.sql
-- StoneDesk WebAuthn/passkey credentials — Supabase schema
--
-- Run this once in the Supabase SQL editor before api/sd-webauthn.js's
-- reg-verify/auth-options/auth-verify actions will work.
--
-- WHAT THIS STORES: a public key and a small amount of metadata per
-- registered passkey. Never a password, never biometric data — the
-- device's own Face ID/Touch ID/Windows Hello does the biometric match
-- locally and never leaves the device. This table only ever sees the
-- cryptographic output of that local check (a signed challenge), the same
-- way TLS certificate verification never sees your private key.
--
-- KEYING: license_hash = sha256(license_key), same as every other
-- StoneDesk-owned table. employee_id ties a credential to a real,
-- already-provisioned sd_employee_auth row -- passkeys are an ADDITIONAL
-- login method registered by an already-PIN-authenticated employee, never
-- a way to create a new identity.
--
-- credential_id has its own global unique constraint (not just scoped to
-- license_hash) because WebAuthn credential IDs are cryptographically
-- unique by construction across the whole ecosystem -- a collision would
-- indicate something is badly wrong, not a legitimate two-tenant clash.
--
-- counter is used for clone-detection per the WebAuthn spec: if an
-- authenticator ever reports a counter value <= the stored one, that's a
-- signal the credential may have been cloned. api/sd-webauthn.js's
-- auth-verify action is responsible for checking this via the library's
-- own verifyAuthenticationResponse() return value, not this schema.
--
-- SECURITY MODEL: service-role only, RLS enabled with no anon policy.
-- api/sd-webauthn.js is the only door in.

create table if not exists public.sd_webauthn_credentials (
  id             uuid primary key default gen_random_uuid(),
  license_hash   text not null,
  employee_id    text not null,
  credential_id  text not null,
  public_key     text not null,               -- base64 of the raw COSE public key bytes
  counter        bigint not null default 0,
  transports     jsonb not null default '[]'::jsonb,
  device_type    text not null default 'single_device' check (device_type in ('single_device','multi_device')),
  backed_up      boolean not null default false,
  device_label   text,                          -- best-effort, human-friendly (e.g. "Chrome on Windows"), never security-relevant
  created_at     timestamptz not null default now(),
  last_used_at   timestamptz,
  unique (credential_id)
);
create index if not exists idx_sdwebauthn_license_emp on public.sd_webauthn_credentials(license_hash, employee_id);

alter table public.sd_webauthn_credentials enable row level security;
drop policy if exists "svc only sd_webauthn_credentials" on public.sd_webauthn_credentials;
create policy "svc only sd_webauthn_credentials" on public.sd_webauthn_credentials
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update, delete on public.sd_webauthn_credentials to service_role;
