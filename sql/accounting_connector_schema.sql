-- sql/accounting_connector_schema.sql
-- SHARED read-only accounting connector: consent records and connection state.
-- Run once in the Supabase SQL editor. Safe to re-run (idempotent).
--
-- ══ WHY THESE ARE UNPREFIXED ═══════════════════════════════════════════════
-- Same convention and same reasoning as sql/subcontractor_compliance_schema.sql:
-- a customer's connection to their own accounting package belongs to the
-- LICENCE, not to one vertical. SAIRNroofing, SAIRNbuild and StoneDesk all
-- want to read the same books for the same customer, and three per-app copies
-- would mean three OAuth registrations, three consent records and three chances
-- to disagree about whether the customer had opted in. They carry `app_id` only
-- where an app-specific fact genuinely differs; the connection itself does not.
--
-- ══ WHAT THIS REPLACES ═════════════════════════════════════════════════════
-- Nothing. Verified 2026-09-02: api/accounting.js has NEVER been on main
-- (created 2026-06-16 on the unmerged lucid-ptolemy branch, reachable only from
-- the archive tag), /api/accounting returns 404, and there is no connection
-- table among the 258 in the schema snapshot. Its companion
-- db/schema_quickbooks.sql was 24 lines and was never run either. The archived
-- `qb_connections` shape stored access_token and refresh_token as bare text;
-- this does not.
--
-- ══ CONSENT IS A RECORD, NOT A COLUMN ON THE CONNECTION ════════════════════
-- THE decision this file turns on. A boolean `consented` on the connection row
-- cannot answer "who agreed, when, and to what" -- which is the only question
-- that matters if a customer ever asks why this platform holds a token for
-- their books. So consent is its own table, it is APPEND-ONLY in practice
-- (revocation sets revoked_on rather than deleting the row), and the
-- connection is meaningless without one.
--
-- Scopes are stored; the ENTITIES they expand to are NOT. api/_lib/
-- accounting-connector.js derives entities from scopes on every read, so
-- changing the scope map moves existing consents with it rather than leaving
-- yesterday's expansion frozen in a column. Same rule as entity attribution in
-- roofing-consolidation.js and document requirements in the compliance engine.
--
-- ══ TOKENS ARE ENCRYPTED AT REST AND THE COLUMN NAME SAYS SO ═══════════════
-- access_token_enc / refresh_token_enc hold AES-256-GCM ciphertext produced by
-- api/_lib/token-vault.js, never bare tokens. The `_enc` suffix is not
-- decoration: a future reader inserting a plaintext token into a column called
-- `refresh_token` would be making an easy mistake, and into one called
-- `refresh_token_enc` a deliberate one.
--
-- The vault REFUSES to operate without ACCOUNTING_TOKEN_KEY rather than
-- falling back to plaintext, so a missing key produces no row at all instead of
-- a row that looks fine and is not.
--
-- HONEST BOUNDARY: this protects tokens against someone reading the table. It
-- does not protect against someone who already holds the environment, because
-- they hold the key. Stated so "encrypted" is not read as a stronger claim.
--
-- ══ NO FINANCIAL DATA IS STORED HERE, AND NONE SHOULD BE ═══════════════════
-- There is no table for invoices, bills, accounts or reports pulled from a
-- customer's books, deliberately. Reads are pass-through. A cached ledger is a
-- second copy that can leak, go stale, and disagree with the source -- and the
-- customer consented to us READING their books, not to us keeping them.
--
-- ══ SIZE BOUNDS ARE NUMERIC ON PURPOSE ═════════════════════════════════════
-- See docs/2026-09-02-constraints-not-comparable.md.

-- ---------------------------------------------------------------------------
-- 1. Consent. One row per grant. Revocation is a new state, never a delete.
-- ---------------------------------------------------------------------------
create table if not exists public.accounting_consents (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  consent_id    text not null,                     -- client-generated
  provider      text not null,                     -- 'quickbooks_online'
  -- WHO agreed. Not nullable: a consent that cannot name a person is not a
  -- consent, and the engine refuses it. Stored as the employee id from the
  -- VERIFIED session, never from a request body.
  granted_by    text not null,
  granted_on    date not null,
  -- Coarse, human-readable scopes. The entity list they expand to is derived
  -- at read time and deliberately not stored -- see the header.
  scopes        jsonb not null default '[]'::jsonb,
  -- Kept because "they clicked agree on this screen" is the evidence, and an
  -- audit that cannot show what was on the screen is not much of one.
  consent_text  text,
  ip            text,
  user_agent    text,
  revoked_on    date,
  revoked_by    text,
  notes         text,
  data          jsonb not null default '{}'::jsonb,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, consent_id),
  constraint acccon_provider_check check (provider in ('quickbooks_online')),
  constraint acccon_scopes_is_array check (jsonb_typeof(scopes) = 'array'),
  constraint acccon_revoked_needs_who check (revoked_on is null or revoked_by is not null),
  constraint acccon_data_size check (octet_length(data::text) <= 65536),
  constraint acccon_text_size check (consent_text is null or octet_length(consent_text) <= 16384)
);

create index if not exists idx_acccon_license on public.accounting_consents(license_hash, provider);
-- The query the gate runs on every read: is there a live consent right now.
create index if not exists idx_acccon_live on public.accounting_consents(license_hash, provider, revoked_on);

-- ---------------------------------------------------------------------------
-- 2. The connection. At most one live one per licence per provider.
-- ---------------------------------------------------------------------------
-- consent_id is a plain text reference and NOT a foreign key, matching the
-- convention across this platform. The cost is stated rather than hidden:
-- nothing at the database level stops a connection naming a consent that does
-- not exist, and api/_lib/accounting-connector.js is what catches it -- which
-- it does by refusing every read, never by assuming consent.
create table if not exists public.accounting_connections (
  id                 uuid primary key default gen_random_uuid(),
  license_hash       text not null,
  provider           text not null,
  consent_id         text not null,                -- the grant this connection was made under
  realm_id           text,                         -- the customer's company id at the provider
  status             text not null default 'pending_consent',
  -- CIPHERTEXT ONLY. See the header: the _enc suffix is load-bearing.
  access_token_enc   text,
  refresh_token_enc  text,
  expires_on         date,                         -- of the ACCESS token; the refresh token outlives it
  last_read_at       timestamptz,                  -- for showing the customer what we have actually done
  last_error         text,
  data               jsonb not null default '{}'::jsonb,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  updated_by         text,
  unique (license_hash, provider),
  constraint accconn_provider_check check (provider in ('quickbooks_online')),
  constraint accconn_status_check check (status in ('pending_consent','connected','revoked','expired','error')),
  -- A connection claiming to be connected with no refresh token cannot survive
  -- its access token expiring. Refused at the database as well as in the
  -- engine, because this one is cheap to state and expensive to discover.
  constraint accconn_connected_needs_refresh check (status <> 'connected' or refresh_token_enc is not null),
  constraint accconn_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_accconn_license on public.accounting_connections(license_hash, provider);

-- ---------------------------------------------------------------------------
-- 3. RLS and grants.
-- ---------------------------------------------------------------------------
-- Service-role only. NO DELETE on either table, and here that is not the usual
-- bookkeeping argument: a consent record is the evidence that a customer agreed,
-- and a revocation is the evidence that they changed their mind. A feature able
-- to erase either is a feature that will be asked why it did.
alter table public.accounting_consents enable row level security;
drop policy if exists "svc only accounting_consents" on public.accounting_consents;
create policy "svc only accounting_consents" on public.accounting_consents
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.accounting_consents from service_role;
grant select, insert, update on public.accounting_consents to service_role;
revoke all on public.accounting_consents from anon, authenticated;

alter table public.accounting_connections enable row level security;
drop policy if exists "svc only accounting_connections" on public.accounting_connections;
create policy "svc only accounting_connections" on public.accounting_connections
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.accounting_connections from service_role;
grant select, insert, update on public.accounting_connections to service_role;
revoke all on public.accounting_connections from anon, authenticated;

-- ---------------------------------------------------------------------------
-- 4. Verify, do not assume.
-- ---------------------------------------------------------------------------
--   select count(*) from accounting_consents;     -- expect 0, nothing is seeded
--   select count(*) from accounting_connections;  -- expect 0
--
-- Grants (expect INSERT,SELECT,UPDATE on both; no DELETE, no TRUNCATE):
--   select table_name, string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name in ('accounting_consents','accounting_connections')
--    group by table_name;
--
-- Confirm the connected-needs-a-refresh-token constraint bites (expect ERROR):
--   insert into public.accounting_connections
--     (license_hash, provider, consent_id, status)
--   values ('test', 'quickbooks_online', 'C1', 'connected');
--
-- Confirm a revocation cannot be anonymous (expect ERROR):
--   insert into public.accounting_consents
--     (license_hash, consent_id, provider, granted_by, granted_on, revoked_on)
--   values ('test', 'C2', 'quickbooks_online', 'someone', current_date, current_date);
--
-- AFTER RUNNING THIS, THE CONNECTOR IS STILL NOT USABLE. It also needs
-- ACCOUNTING_TOKEN_KEY set in Vercel (64 hex characters -- generate it with
-- node -e "console.log(require('./api/_lib/token-vault').generateKeyHex())")
-- and an Intuit application providing QB_CLIENT_ID, QB_CLIENT_SECRET and
-- QB_REDIRECT_URI. Neither exists yet, and the endpoint reports that rather
-- than pretending otherwise.
--
-- Then re-run sql/schema_snapshot_query.sql so db/schema_snapshot.json carries
-- these tables.
