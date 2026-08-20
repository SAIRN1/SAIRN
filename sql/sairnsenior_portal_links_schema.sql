-- sql/sairnsenior_portal_links_schema.sql
-- SAIRNsenior family/client portal links -- Supabase schema
--
-- WHY THIS EXISTS: client/family is a DIFFERENT actor class from an
-- employee, per Michael's explicit instruction -- not a PIN account, not
-- an extension of sairnsenior_employee_auth. A portal link is a unique,
-- revocable, scoped-to-exactly-one-client bearer token. Possessing the
-- token IS the credential (same model as a calendar-share link or a
-- password-reset link) -- there is no login step, no PIN, no session.
--
-- SECURITY MODEL, stated explicitly since this is architecturally
-- different from every other table in this codebase:
-- - link_token is a 32-byte (256-bit) cryptographically random value,
--   crypto.randomBytes(32).toString('hex') -- 64 hex characters, not
--   guessable by brute force at any practical rate.
-- - The token is looked up directly (unique index) on every portal read
--   -- the client_id it resolves to is NEVER supplied by the caller and
--   NEVER trusted from anywhere except this table, so a family member
--   cannot access a different client's data by guessing or editing a
--   client_id parameter -- there isn't one to edit.
-- - revoked links stay in the table (active=false) rather than being
--   deleted, so staff can see revocation history -- same "no destructive
--   delete, deactivate instead" discipline as every *_employee_auth
--   table's active flag.
-- - Only api/sen-portal.js's 'view' action reads this table without a
--   normal employee session -- 'create'/'revoke'/'list' still require
--   the same real employee auth as everything else in this app.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.sen_portal_links (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnsenior',
  link_token   text not null,
  client_id    text not null,
  label        text,                                  -- e.g. "Jane's daughter" -- staff-entered, not required
  created_by_employee_id text,
  active       boolean not null default true,
  created_at   timestamptz not null default now(),
  last_accessed_at timestamptz,
  revoked_at   timestamptz,
  unique (link_token)
);

create index if not exists idx_senportallinks_license on public.sen_portal_links(license_hash);
create index if not exists idx_senportallinks_client on public.sen_portal_links(license_hash, client_id);

-- ---------------------------------------------------------------------------
-- GRANTS -- explicit up front, same reasoning as every other table's own
-- header this session. Even the public 'view' action goes through
-- api/sen-portal.js using SUPABASE_SERVICE_ROLE_KEY -- the anon key never
-- touches this table, so a leaked link_token alone (without the service
-- role key, which never leaves the server) cannot be used to query
-- Supabase directly, only through the narrowly-scoped API action.
grant select, insert, update on public.sen_portal_links to service_role;
revoke all on public.sen_portal_links from anon, authenticated;
