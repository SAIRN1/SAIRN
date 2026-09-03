-- sql/sairndental_bi_tokens_schema.sql
-- SAIRNdental B5 -- open BI / data-warehouse feed. Token store.
--
-- Run once in the Supabase SQL editor. Every statement is idempotent
-- (create ... if not exists), safe to re-run. api/dnt-bi.js is the only door.
--
-- WHAT A ROW IS
-- One long-lived, revocable credential a practice hands to Power BI, Tableau or
-- Looker Studio so it can poll api/dnt-bi.js. It is NOT a login and NOT a
-- license key, and that separation is the point: a BI tool stores its
-- credential in a workspace other people can open, so the thing it stores must
-- be revocable on its own without disturbing anybody's sign-in.
--
-- ONLY THE HASH IS STORED. The token is shown once, at mint, and never again.
-- A dump of this table therefore yields no working feed. sha256 with no
-- per-row salt is correct here and would NOT be for a password: the token is
-- 256 bits of crypto.randomBytes, not something a human chose, so there is no
-- dictionary to run against it. See api/_lib/dental-bi.js hashToken().
--
-- THE ROLE IS NOT STORED HERE, DELIBERATELY.
-- The row carries employee_id; api/dnt-bi.js re-reads that employee's role and
-- active flag from sairndental_employee_auth on EVERY request. A role column
-- here would be a snapshot, and a snapshot survives the demotion or
-- deactivation it was supposed to respect -- the stale-credential shape this
-- platform has a standing rule about. Cost: one extra read per poll. Worth it.
--
-- KNOWN LIMITATION: A LAPSED LICENCE DOES NOT CLOSE A FEED BY ITSELF.
-- There is no license_hash column on the shared `license_keys` table (confirmed
-- absent by the live column probe in sql/demo_license_keys_seed.sql), so a poll
-- carrying only a hash cannot look the licence up. Every read is still filtered
-- by this practice's own license_hash, so it is not a cross-tenant hole -- but
-- cancelling a practice means revoking its feed tokens too, and nothing here
-- does that automatically.
--
-- REVOCATION IS A TIMESTAMP, NOT A DELETE.
-- revoked_at is set and the row stays. A deleted row cannot answer "was this
-- feed live on the day that report was wrong", and service_role is not granted
-- delete on this table so the question stays answerable.

create extension if not exists pgcrypto;

create table if not exists public.sairndental_bi_tokens (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairndental',

  -- sha256 of the token. Unique across ALL practices: a collision would let one
  -- practice's token authenticate against another's data, so this is a hard
  -- constraint rather than a per-license one.
  token_hash text not null unique,

  -- What the practice calls this connection ("Owner Power BI", "Hygiene
  -- dashboard"). Shown in the app's token list so a person can tell which one
  -- to revoke without having to recognise a hash.
  label text not null default '',

  -- Whose role and patient scope this feed inherits, re-read live on every
  -- request. Not a foreign key: sairndental_employee_auth is keyed
  -- (license_hash, employee_id) and a FK across a composite key buys nothing
  -- here that the live re-read does not already enforce -- an employee row that
  -- vanishes makes the token fail closed at the next poll.
  employee_id text not null,

  -- Direct patient identifiers (name, DOB, phone, email, member ID, guardian
  -- name) are omitted from the feed unless this is true. DEFAULT FALSE, and the
  -- app requires a separate deliberate action to turn it on. Every
  -- patient-bearing row still carries a stable pseudonym, so joins work either
  -- way and the off position costs the analyst nothing.
  include_identifiers boolean not null default false,

  created_by text not null default '',
  created_at timestamptz not null default now(),

  -- Revocation, and the two facts that make an unused token visible. A feed
  -- nobody has polled in months is one nobody will miss being revoked, and a
  -- revoked token that is still being polled says somebody's report just broke.
  revoked_at timestamptz,
  last_used_at timestamptz,
  use_count bigint not null default 0
);

create index if not exists idx_dntbi_license on public.sairndental_bi_tokens(license_hash);
-- The hot path: every poll looks a token up by hash and checks it is live.
create index if not exists idx_dntbi_live on public.sairndental_bi_tokens(token_hash) where revoked_at is null;

alter table public.sairndental_bi_tokens enable row level security;
-- No anon or authenticated policy, deliberately. PostgREST is not a door to
-- this table for anyone; api/dnt-bi.js holds the service-role key and is the
-- only caller. Same posture as every other SAIRNdental table.

-- GRANTS, narrowed on purpose (see the sairn-grant-sweep skill).
-- select  -- resolve a token on each poll, and list a practice's tokens.
-- insert  -- mint.
-- update  -- revoke (revoked_at) and stamp last_used_at / use_count.
-- NO delete: revocation is a timestamp, and the audit value of a revoked row is
--            the reason this table exists in the shape it does.
-- NO truncate, references, trigger: nothing here needs them.
revoke all on public.sairndental_bi_tokens from service_role;
grant select, insert, update on public.sairndental_bi_tokens to service_role;

-- Verify after running:
--   select grantee, privilege_type
--     from information_schema.role_table_grants
--    where grantee = 'service_role'
--      and table_schema = 'public'
--      and table_name = 'sairndental_bi_tokens'
--    order by privilege_type;
-- Expected exactly: INSERT, SELECT, UPDATE. Anything else is drift.
