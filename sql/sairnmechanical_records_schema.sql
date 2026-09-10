-- sql/sairnmechanical_records_schema.sql
-- SAIRNmechanical business records -- the last local-only collections on the
-- platform reach a server.
--
-- Run this once in the Supabase SQL editor. Every statement is idempotent
-- (create table if not exists), safe to re-run. Until it runs, every write
-- answers 503 NOT_PROVISIONED naming this file and every read answers
-- provisioned:false, so the app degrades honestly.
--
-- WHY, MEASURED. tools/local_only_collection_check.py reported sairnmechanical
-- as 5 of 5 collections with NO route to a server -- the only app left on the
-- platform with undeclared local-only collections after 2026-09-10's sweep.
-- The app HAS a working data layer (mechData(), mech_credentials,
-- mech_site_assets) and a real licence, so this is not a pre-server app: these
-- five were simply never wired.
--
-- THE CHECK REGISTER IS THE ONE TO LOOK AT FIRST. saveCheck() stores
-- {num, date, payee, amount, memo} -- a business's record of money it paid out,
-- on one browser, with the app's own comment noting that a lost write is how
-- two checks end up sharing a number. Losing the register loses the audit trail
-- for every cheque written.
--
-- FOUR BACKED UP, ONE DECLARED NOT-SYNCED. sairnmechanical_memory is an AI
-- conversation memory -- 30 truncated strings, no records and no ids -- and its
-- reason is in api/_resources/sairnmechanical.js rather than left as an absence.
--
-- RESOURCE NAMES ARE NOT THE STORAGE KEYS, and this app needed a pair list to
-- say so. Its keys are APP_ID + '_quotes' etc. while its resources carry the
-- established `mech_` prefix (mech_credentials, mech_site_assets), so
-- MECH_SYNCED in sairnmechanical.html is a [resource, storage-key] PAIR list --
-- the same shape SAIRNdental's DNT_SYNC_RESOURCES uses, and what makes the
-- coverage readable to the checker instead of a permanent could-not-tell.
--
-- ONE ID COLUMN IS NOT A MINTED ID. mech_checks keys on the CHECK NUMBER, which
-- is what the register has always keyed on and what makes a duplicate visible.
-- The client sends it through a per-resource id-field map rather than minting a
-- second identity for a document that already has one.
--
-- SECURITY MODEL: licence key only, matching mechData()'s existing calls. RLS
-- enabled with no anon policy -- api/sd-data.js is the only door in. 64KB per
-- row's data jsonb.
--
-- NO `delete` GRANT ANYWHERE IN THIS FILE. None of these four has a delete path
-- in the product; the quotes, docs and takeoffs lists are client-capped
-- (50, 50) for LOCAL storage only, which is a display bound and not a deletion
-- -- the server keeps every row, which is the point of an archive. `revoke all`
-- precedes each grant because a bare grant is additive and cannot remove what
-- the default ACL already handed over.

create extension if not exists pgcrypto;

-- Signed customer quotes -- scope, itemised pricing and the signature that closed it. id is the client's Date.now() stamp.
create table if not exists public.mech_quotes (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnmechanical',
  quote_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, quote_id),
  constraint mech_quotes_data_size check (octet_length(data::text) <= 65536)
);
alter table public.mech_quotes enable row level security;
drop policy if exists "svc only mech_quotes" on public.mech_quotes;
create policy "svc only mech_quotes" on public.mech_quotes
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.mech_quotes from service_role;
grant select, insert, update on public.mech_quotes to service_role;

-- THE CHECK REGISTER: payee, amount, memo and check number. check_id holds the check NUMBER, not a minted id -- see the id-column note.
create table if not exists public.mech_checks (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnmechanical',
  check_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, check_id),
  constraint mech_checks_data_size check (octet_length(data::text) <= 65536)
);
alter table public.mech_checks enable row level security;
drop policy if exists "svc only mech_checks" on public.mech_checks;
create policy "svc only mech_checks" on public.mech_checks
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.mech_checks from service_role;
grant select, insert, update on public.mech_checks to service_role;

-- Text extracted from a scanned document.
create table if not exists public.mech_docs (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnmechanical',
  doc_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, doc_id),
  constraint mech_docs_data_size check (octet_length(data::text) <= 65536)
);
alter table public.mech_docs enable row level security;
drop policy if exists "svc only mech_docs" on public.mech_docs;
create policy "svc only mech_docs" on public.mech_docs
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.mech_docs from service_role;
grant select, insert, update on public.mech_docs to service_role;

-- Blueprint takeoff results.
create table if not exists public.mech_takeoffs (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnmechanical',
  takeoff_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, takeoff_id),
  constraint mech_takeoffs_data_size check (octet_length(data::text) <= 65536)
);
alter table public.mech_takeoffs enable row level security;
drop policy if exists "svc only mech_takeoffs" on public.mech_takeoffs;
create policy "svc only mech_takeoffs" on public.mech_takeoffs
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.mech_takeoffs from service_role;
grant select, insert, update on public.mech_takeoffs to service_role;

grant usage on schema public to service_role;
