-- sql/audit_checkpoint_schema.sql
-- ---------------------------------------------------------------------------
-- DAILY CHECKPOINTS OVER THE THREE AUDIT LOGS. Item 35, Michael's decision
-- 2026-09-14: daily cadence, over CLOSED windows.
--
-- WHAT THIS IS FOR, AND WHAT IT IS NOT.
-- `sairnlaw_audit_log`, `sairncode_audit_log` and `stonedesk_audit_log` all
-- carry `grant select, insert` and nothing else, so through the API a row
-- CANNOT be altered in place and CANNOT be removed. Those two tamper modes are
-- already closed by construction and this table does not re-buy them.
--
-- The mode the grant leaves OPEN is INSERTION. The grant is table-level, so it
-- covers every column, and `api/_lib/audit.js` lets `created_at` take its
-- `default now()` -- so anyone holding the service key can insert a row with
-- ANY timestamp under ANY license_hash. A forged sign-in, backdated into last
-- month, under another practice's licence, is one INSERT and nothing notices.
-- THAT is what a checkpoint detects.
--
-- WHY CHECKPOINTS AND NOT A PER-ROW HASH CHAIN. A per-row chain needs the
-- previous row's hash, which puts a READ on `api/_lib/audit.js` -- a function
-- whose stated contract is that it must never block and whose seven callers all
-- ignore its return value. Worse: two concurrent audit writes read the same
-- previous hash and FORK the chain, and with no UPDATE grant on those tables
-- NOTHING CAN REPAIR THE FORK. Every verification from that moment would report
-- a broken chain on a correct log. A detector that cries wolf on a correct
-- audit log is worse than no detector -- it teaches everyone to ignore it, and
-- the one real alarm arrives into that habit. The window here is CLOSED before
-- it is hashed, so concurrency inside it is irrelevant.
--
-- THE RESIDUAL, STATED RATHER THAN DISCOVERED: an insertion into the CURRENT,
-- not-yet-closed window is invisible until that window closes. Bounded by the
-- cadence (one day), not open-ended.
--
-- AND WHAT NO CHECKPOINT CAN DO: anyone with direct database access -- the
-- Supabase dashboard, a superuser -- can rewrite rows AND recompute every
-- checkpoint over them. Detection binds someone limited to the API. An external
-- anchor is the only thing that changes that, and where an anchor would live is
-- not decided.
--
-- SAME IMMUTABILITY TREATMENT AS THE TABLES IT PROTECTS. A checkpoint table the
-- application can rewrite protects nothing: an attacker who inserts a backdated
-- audit row and then updates the covering checkpoint has defeated the whole
-- mechanism in two statements. SELECT + INSERT only, and the revoke is explicit
-- rather than assumed from the grant -- the sibling audit schema records a real
-- live 42501 that proved Supabase's default privileges had not been applied.
--
-- WRITTEN 2026-09-14. NOT RUN. Until it is, api/audit-checkpoint.js answers
-- 503 NOT_PROVISIONED naming this file rather than reporting an empty history
-- as a clean one.
-- ---------------------------------------------------------------------------

create table if not exists sairn_audit_checkpoint (
  id uuid primary key default gen_random_uuid(),
  -- WHICH LOG. Stored rather than implied by a separate table per log, because
  -- the verifier has to iterate them and a three-table shape would mean three
  -- of everything below.
  audit_table text not null check (audit_table in (
    'sairnlaw_audit_log', 'sairncode_audit_log', 'stonedesk_audit_log'
  )),
  -- THE WINDOW IS HALF-OPEN: created_at >= window_start AND < window_end.
  -- Written out rather than left to the reader, because an inclusive upper
  -- bound would double-count every row landing exactly on midnight and the two
  -- adjacent digests would both be wrong in a way that looks like tampering.
  window_start timestamptz not null,
  window_end   timestamptz not null,
  row_count    integer not null,
  -- sha256 over the canonical serialisation of every row in the window, in a
  -- deterministic order, WITH prev_digest folded in. See api/audit-checkpoint.js
  -- for the canonical form; changing it invalidates every prior checkpoint and
  -- that is a migration, not an edit.
  digest       text not null,
  -- The previous checkpoint for THIS audit_table, or the genesis string. This
  -- is what makes wholesale recomputation of the checkpoint table detectable
  -- rather than merely laborious.
  prev_digest  text not null,
  created_at   timestamptz not null default now(),
  -- ONE CHECKPOINT PER TABLE PER WINDOW. With INSERT-only grants there is no
  -- upsert to fall back on, so a second run for the same window must FAIL
  -- LOUDLY rather than quietly appending a second, differently-chained row --
  -- which would fork the checkpoint chain in exactly the way this design exists
  -- to avoid.
  constraint sairn_audit_checkpoint_one_per_window unique (audit_table, window_end)
);

create index if not exists idx_sairn_audit_checkpoint_table_time
  on sairn_audit_checkpoint (audit_table, window_end desc);

grant select, insert on public.sairn_audit_checkpoint to service_role;
revoke update, delete on public.sairn_audit_checkpoint from service_role;
revoke all on public.sairn_audit_checkpoint from anon, authenticated;

alter table sairn_audit_checkpoint enable row level security;

drop policy if exists sairn_audit_checkpoint_service_insert on sairn_audit_checkpoint;
create policy sairn_audit_checkpoint_service_insert
  on sairn_audit_checkpoint for insert
  to service_role
  with check (true);

-- ── VERIFY, one query per statement with the answer it must give ───────────
-- Run these after applying the file. A statement whose answer differs from the
-- comment beside it means the migration did NOT do what this file says.

-- 1. The table exists and is empty. Expect: 0
select count(*) from sairn_audit_checkpoint;

-- 2. service_role holds SELECT and INSERT and NOTHING ELSE.
--    Expect exactly two rows: INSERT and SELECT. Any UPDATE or DELETE row here
--    means the revoke did not take and the checkpoint is rewritable, which
--    makes the whole mechanism decorative.
select privilege_type
  from information_schema.role_table_grants
 where table_name = 'sairn_audit_checkpoint'
   and grantee = 'service_role'
 order by privilege_type;

-- 3. anon and authenticated hold nothing at all. Expect: 0
select count(*)
  from information_schema.role_table_grants
 where table_name = 'sairn_audit_checkpoint'
   and grantee in ('anon', 'authenticated');

-- 4. The uniqueness that stops a second run forking the chain exists.
--    Expect: 1
select count(*)
  from pg_constraint
 where conname = 'sairn_audit_checkpoint_one_per_window';

-- 5. RLS is on. Expect: t
select relrowsecurity from pg_class where relname = 'sairn_audit_checkpoint';
