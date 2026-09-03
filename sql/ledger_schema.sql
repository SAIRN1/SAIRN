-- sql/ledger_schema.sql
-- SHARED double-entry general ledger: journal entries and their lines.
-- Run once in the Supabase SQL editor. Safe to re-run (idempotent).
--
-- ══ THIS DOES NOT TOUCH gl_entries, AND HERE IS WHY ════════════════════════
-- Verified 2026-09-02 before any of this was designed. `gl_entries` exists in
-- the live database with debit/credit/account_code/posted columns and NOTHING
-- WRITES IT -- zero references across all of api/ and every *.html, which
-- sql/full_crud_truncate_sweep_2026-08-24.sql had already recorded as
-- "CONFIRMED unreferenced by any live SAIRN code path". It is not an
-- unenforced ledger; it is an empty table with accounting-shaped names.
--
-- It is left exactly as it is, untouched, for two reasons that are not
-- preferences:
--   * IT IS KEYED ON shop_id WITH A FOREIGN KEY TO public.shops -- the
--     Fabricor/StoneDesk shape. Every B2B app here is licence-keyed and never
--     touches `shops`, so adopting it would mean dropping a live FK or
--     inventing a shop row per licence.
--   * IT CANNOT EXPRESS A TRANSACTION. There is no grouping column: no
--     journal-entry id that two lines belong to. Without one, "debits equal
--     credits" is not a rule anything can check. That single missing column
--     is the whole reason for a new model rather than a validator bolted on.
--
-- ══ WHY UNPREFIXED AND SHARED ══════════════════════════════════════════════
-- Debits equal credits in every trade. Same call as subcontractor_compliance
-- and the WIP engine: one model, licence- and app-scoped, SAIRNbiz as the
-- first consumer because it is the accounting backbone the other B2B apps
-- already include. SAIRNbiz today has no general ledger at all -- zero
-- occurrences of debit, account_code, journal or double-entry in its file.
--
-- ══ WHAT THE DATABASE CAN AND CANNOT ENFORCE, STATED PLAINLY ═══════════════
-- A Postgres CHECK cannot span rows, so the database CANNOT enforce that an
-- entry's debits equal its credits -- that lives across many ledger_lines
-- rows. The guarantee this build makes is "no code path writes an unbalanced
-- entry": api/_lib/ledger.js validates and api/ledger.js writes nothing until
-- it passes. That is a real guarantee and it is not the same as the database
-- refusing one, so it is written down rather than implied.
--
-- A TRIGGER COULD CLOSE THAT GAP and is deliberately not added here: a
-- deferred constraint trigger firing at COMMIT is the correct shape, it cannot
-- be exercised from this environment, and shipping an untested trigger on the
-- financial write path is the same mistake as shipping an untested OAuth leg.
-- Named as the next step instead.
--
-- WHAT THE DATABASE DOES ENFORCE, per row and worth having:
--   * a line carries EXACTLY ONE side (ledger_lines_one_side)
--   * neither side is negative -- post the other side instead
--   * a posted entry has a posted_at, and a voided one has a reason
--
-- ══ A POSTED ENTRY IS IMMUTABLE ════════════════════════════════════════════
-- No DELETE grant on either table, and correction is by REVERSING entry, not
-- by editing. That is not bookkeeping fussiness: the history of what was
-- believed and when is the thing an auditor is actually asking for, and an
-- edit destroys it. `void` exists only for an entry that was never posted.
--
-- ══ SIZE BOUNDS ARE NUMERIC ON PURPOSE ═════════════════════════════════════
-- See docs/2026-09-02-constraints-not-comparable.md.

-- ---------------------------------------------------------------------------
-- 1. The journal entry. This is the grouping gl_entries never had.
-- ---------------------------------------------------------------------------
create table if not exists public.ledger_entries (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null,
  entry_id      text not null,                    -- client-generated (JE-<stamp>)
  entry_date    date not null,
  memo          text not null,                    -- not nullable: a line nobody can explain later cannot be audited
  status        text not null default 'draft',
  -- Where it came from, so a ledger line can always be traced back to the
  -- business event that caused it. source_id is a plain text reference and NOT
  -- a foreign key: the causing row lives in a different app's table, and in
  -- SAIRNbiz's case in the browser.
  source_app    text,
  source_kind   text,                             -- 'invoice_issued', 'bill_paid', 'expense', 'payroll_run'...
  source_id     text,
  -- Set when the entry posts, by the server, from the CALLER's date. Never a
  -- server clock: a posting date is a local-date fact about somebody's books.
  posted_at     date,
  posted_by     text,
  void_reason   text,
  data          jsonb not null default '{}'::jsonb,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint le_status_check check (status in ('draft','posted','void')),
  constraint le_posted_needs_date check (status <> 'posted' or posted_at is not null),
  constraint le_void_needs_reason check (status <> 'void' or void_reason is not null),
  constraint le_memo_not_blank check (length(btrim(memo)) > 0),
  constraint le_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_le_license on public.ledger_entries(license_hash, app_id);
create index if not exists idx_le_date on public.ledger_entries(license_hash, app_id, entry_date);
-- The query that makes a posting idempotent: has this business event already
-- produced an entry? Without it, a double-click posts revenue twice.
create index if not exists idx_le_source on public.ledger_entries(license_hash, app_id, source_kind, source_id);

-- ---------------------------------------------------------------------------
-- 2. The lines. Two or more per entry, and each carries exactly one side.
-- ---------------------------------------------------------------------------
-- entry_id references ledger_entries.entry_id as plain text, matching the
-- convention across this platform. The cost is stated rather than hidden:
-- nothing at the database level stops a line naming an entry that does not
-- exist, and the endpoint is what prevents it by writing the header first and
-- the lines in the same call.
create table if not exists public.ledger_lines (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null,
  entry_id      text not null,
  line_no       integer not null,
  account_code  text not null,
  debit         numeric(14,2) not null default 0,
  credit        numeric(14,2) not null default 0,
  memo          text,
  created_at    timestamptz not null default now(),
  unique (license_hash, entry_id, line_no),
  -- EXACTLY ONE SIDE. A line carrying both is ambiguous about what it means; a
  -- line carrying neither is noise that still has to be stored and reconciled.
  -- This one the database CAN enforce, so it does.
  constraint ledger_lines_one_side check (
    (debit > 0 and credit = 0) or (credit > 0 and debit = 0)
  ),
  constraint ll_no_negative check (debit >= 0 and credit >= 0)
);

create index if not exists idx_ll_entry on public.ledger_lines(license_hash, entry_id);
-- The trial balance reads by account across the whole book.
create index if not exists idx_ll_account on public.ledger_lines(license_hash, app_id, account_code);

-- ---------------------------------------------------------------------------
-- 3. RLS and grants.
-- ---------------------------------------------------------------------------
-- Service-role only. SELECT/INSERT/UPDATE and NO DELETE on either table, and
-- here that is the point rather than a habit: a ledger you can delete from is
-- not a ledger. UPDATE is granted on entries so a draft can be posted or
-- voided; the endpoint refuses to modify a posted one.
alter table public.ledger_entries enable row level security;
drop policy if exists "svc only ledger_entries" on public.ledger_entries;
create policy "svc only ledger_entries" on public.ledger_entries
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.ledger_entries from service_role;
grant select, insert, update on public.ledger_entries to service_role;
revoke all on public.ledger_entries from anon, authenticated;

alter table public.ledger_lines enable row level security;
drop policy if exists "svc only ledger_lines" on public.ledger_lines;
create policy "svc only ledger_lines" on public.ledger_lines
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.ledger_lines from service_role;
-- NO UPDATE on lines at all. A posted line is never edited, and a draft's
-- lines are rewritten by deleting-and-reinserting the entry, which cannot
-- happen either -- so a draft is corrected by voiding it and posting a new
-- one. Narrower than entries on purpose.
grant select, insert on public.ledger_lines to service_role;
revoke all on public.ledger_lines from anon, authenticated;

-- ---------------------------------------------------------------------------
-- 4. Verify, do not assume.
-- ---------------------------------------------------------------------------
--   select count(*) from ledger_entries;  -- expect 0, nothing is seeded
--   select count(*) from ledger_lines;    -- expect 0
--
-- Grants (entries: INSERT,SELECT,UPDATE / lines: INSERT,SELECT -- no DELETE):
--   select table_name, string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name in ('ledger_entries','ledger_lines')
--    group by table_name;
--
-- Confirm the one-side constraint bites (expect an ERROR, not a row):
--   insert into public.ledger_lines
--     (license_hash, app_id, entry_id, line_no, account_code, debit, credit)
--   values ('test','sairnbiz','JE-CHECK',1,'1100',100,40);
--
-- Confirm a posted entry cannot exist without a posting date (expect ERROR):
--   insert into public.ledger_entries
--     (license_hash, app_id, entry_id, entry_date, memo, status)
--   values ('test','sairnbiz','JE-CHECK2',current_date,'x','posted');
--
-- THE BOOK-LEVEL CHECK, run against real data rather than trusted. These two
-- must be equal; the endpoint's 'trial_balance' action derives the same thing:
--   select sum(debit) as debits, sum(credit) as credits
--     from ledger_lines where license_hash = '<hash>';
--
-- Then re-run sql/schema_snapshot_query.sql so db/schema_snapshot.json carries
-- these tables.
