-- sql/sairnbiz_po_recv_migration.sql
-- Adds the two NEW tables sb_po and sb_recv to an EXISTING SAIRNbiz install
-- (sql/sairnbiz_data_schema.sql, already run). Nothing here alters an existing
-- table and nothing here drops anything. Safe to re-run.
--
-- If you have NOT yet run sql/sairnbiz_data_schema.sql, run that instead --
-- it now contains these two tables and the other ten. Running both is also
-- fine; every statement in each is `if not exists`.
--
-- ── WHAT THIS CLOSES ──────────────────────────────────────────────────────
-- `python tools/local_only_collection_check.py` reports sairnbiz.html as
-- 2 of 13 collections with NO route to a server, and names them: sb_po and
-- sb_recv. They are the OTHER TWO DOCUMENTS of the three-way match -- the
-- purchase order and the receipt -- built into the app on 2026-09-14, after
-- the pass that provisioned everything else, and so never provisioned.
--
-- ── WHY THESE TWO ARE WORSE TO LOSE THAN AN ORDINARY LOCAL-ONLY RECORD ────
-- The bill (sb_ap) is ALREADY backed up, and the double-entry ledger entry
-- that settles it is durable in Postgres. The PO and the receipt are the only
-- two documents that say the bill was ever entitled to be paid.
--
-- Clear that browser and what survives is a payable and a payment with
-- NOTHING LEFT THAT JUSTIFIES EITHER. Worse than the absence: sbThreeWayMatch
-- reads an empty sb_po and reports "no purchase order PO-2026-001 exists"
-- against a bill that WAS correctly matched when it was paid. The control
-- does not merely stop working -- it starts making a false accusation about
-- work that was done right, and the person reading it has no way to tell that
-- from a real finding.
--
-- ── THE ONE NON-MECHANICAL DECISION IN THIS FILE ──────────────────────────
-- po_id IS NOT THE PO NUMBER. `po_num` comes from a per-DEVICE sequence
-- (sairnbiz.html's `sb_po_seq` in localStorage), so two workstations raising
-- their first PO of the year both mint PO-2026-001. api/sd-data.js upserts
-- with `resolution=merge-duplicates` on (license_hash, po_id), so keying on
-- the PO number would make the second device's purchase order SILENTLY
-- OVERWRITE the first: one row, two real POs, no error anywhere, and the
-- three-way match would then validate bills against whichever one won.
--
-- po_id carries an internal minted string instead (SB_ID_PREFIX in
-- sairnbiz.html), so both POs survive as separate rows and a duplicated PO
-- NUMBER becomes a visible business problem somebody can correct. sairnbiz.html
-- refuses to match a bill against a duplicated PO number rather than silently
-- taking the first, for the same reason.
--
-- ── NO `delete` GRANT, AND DO NOT ADD ONE ─────────────────────────────────
-- Same rule as the rest of this app's schema: the platform removed explicit
-- delete grants from every non-sc_* schema on 2026-08-25, and re-adding delete
-- is the overcorrection that caused the 2026-08-06 incident. api/sd-data.js's
-- generic SB_RESOURCES block has a read path and a write path and no delete
-- path, so there is nothing to grant for.

create extension if not exists pgcrypto;

create table if not exists public.sb_po (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbiz',
  po_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, po_id),
  constraint sb_po_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sb_po_license on public.sb_po(license_hash);
alter table public.sb_po enable row level security;
revoke all on public.sb_po from service_role;
grant select, insert, update on public.sb_po to service_role;

create table if not exists public.sb_recv (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbiz',
  recv_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, recv_id),
  constraint sb_recv_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sb_recv_license on public.sb_recv(license_hash);
alter table public.sb_recv enable row level security;
revoke all on public.sb_recv from service_role;
grant select, insert, update on public.sb_recv to service_role;

-- ── VERIFY ────────────────────────────────────────────────────────────────
-- 1. THE GRANTS. Expect exactly TWO rows, each reading `INSERT, SELECT,
--    UPDATE` and nothing else. A row carrying DELETE, TRUNCATE, REFERENCES or
--    TRIGGER means the `revoke all` above did not take and should be
--    investigated before the app is pointed at these tables.
--
--      select table_name,
--             string_agg(privilege_type, ', ' order by privilege_type) as privs
--        from information_schema.role_table_grants
--       where grantee = 'service_role'
--         and table_schema = 'public'
--         and table_name in ('sb_po', 'sb_recv')
--       group by table_name
--       order by table_name;
--
--    Running the whole schema file instead? Then the broader check in
--    sql/sairnbiz_data_schema.sql expects THIRTEEN sb_ rows, not eleven.
--
-- 2. THROUGH THE DEPLOYED API, which is the only real proof -- a clean CREATE
--    is not evidence the app can use the table. NOTE the X-SD-Auth header:
--    every SAIRNbiz business resource requires a signed-in employee session,
--    so a licence-only call answers 401 NO_SESSION whether or not this file
--    has been run and IS NOT A TEST OF PROVISIONING.
--
--      curl -s -X POST https://sairn.vercel.app/api/sd-data \
--        -H 'Content-Type: application/json' \
--        -H 'Authorization: Bearer SD-PINNACLE-2026' \
--        -H 'X-SD-Auth: <session token from api/sb-auth.js login>' \
--        -d '{"action":"read","resource":"sb_po"}'
--
--      {"ok":true,"data":[],"provisioned":true}   -> this file has been run
--      {"ok":true,"data":[],"provisioned":false}  -> it has not (read side)
--      503 NOT_PROVISIONED (on a write)           -> it has not
--
--    `provisioned:false` and `data:[]` arrive TOGETHER and mean "never
--    migrated", not "nothing saved yet". Reading only the empty array is how
--    an unrun migration reads as a clean install.
--
-- 3. IN THE APP, which is the one that proves the round trip. Raise a PO in
--    SAIRNbiz, then open the SAME licence in a different browser profile and
--    sign in: the PO should appear, and the toast counts what was restored.
--    If the console instead says "SAIRNbiz server backup is unavailable: the
--    data tables do not exist", this file has not been run against the project
--    the app is actually pointed at.
