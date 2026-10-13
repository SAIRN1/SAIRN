-- sql/audit_checkpoint_schema.sql
-- ---------------------------------------------------------------------------
-- DAILY CHECKPOINTS OVER ALL SIXTEEN AUDIT LOGS. Item 35, Michael's decision
-- 2026-09-14: daily cadence, over CLOSED windows. Widened from three logs to
-- sixteen on 2026-10-13 -- see the block headed THE COVERAGE WIDENING below,
-- which is the half that makes this file safe to run against a database where
-- the table ALREADY EXISTS carrying the original three-name CHECK.
--
-- THIS WHOLE FILE IS ONE IDEMPOTENT BLOCK. Run it top to bottom, as many times
-- as you like, in either of the two states it can meet:
--
--   * THE TABLE DOES NOT EXIST -- `create table if not exists` builds it with
--     the sixteen-name CHECK, and the widening block below is then a no-op that
--     drops and re-adds the identical constraint.
--   * THE TABLE EXISTS WITH THE OLD THREE-NAME CHECK -- `create table if not
--     exists` is the no-op, and the widening block is what actually acts.
--
-- `create table if not exists` does NOT amend an existing table's constraint,
-- and that is the trap this file used to contain: anyone who re-ran it to "fix
-- the coverage" would have got a clean run, no error, and the same three names.
-- The two halves are therefore BOTH required and neither is redundant.
--
-- WHAT THIS IS FOR, AND WHAT IT IS NOT.
-- The sixteen audit logs all carry `grant select, insert` and nothing else, so
-- through the API a row
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
-- WRITTEN 2026-09-14. WHETHER IT HAS EVER RUN COULD NOT BE TOLD FROM A CLONE
-- and `docs/AUDIT-CHECKPOINT-STATUS.md` has said so since that date -- there is
-- no database handle here. Both unrun states are handled rather than assumed:
-- if the table is absent api/audit-checkpoint.js answers 503 NOT_PROVISIONED
-- naming this file, and if the table is present with the narrow CHECK it
-- answers 503 CHECK_NOT_WIDENED naming this file. Neither reports an empty or
-- partial history as a clean one.
-- ---------------------------------------------------------------------------

create table if not exists sairn_audit_checkpoint (
  id uuid primary key default gen_random_uuid(),
  -- WHICH LOG. Stored rather than implied by a separate table per log, because
  -- the verifier has to iterate them and a three-table shape would mean three
  -- of everything below.
  -- ALL SIXTEEN, and the list is not a preference. It is every value in
  -- AUDIT_TABLE_BY_APP in api/_lib/audit.js, deduplicated -- `stonedesk` and
  -- `stonedesk_sub` deliberately share one log. api/audit-checkpoint.js derives
  -- its loop from that same map, and api/audit-checkpoint.test.js reads THIS
  -- FILE and compares, so a drift between the two fails a test rather than
  -- failing at 03:30 in production.
  --
  -- `sv_audit_log` IS DELIBERATELY ABSENT. It is SAIRNvet's OLD table, has no
  -- `event_type` column, and nothing writes to it; STEP 13 of the migration
  -- created `sairnvet_audit_log` precisely because of that.
  audit_table text not null check (audit_table in (
    'sairnbiz_audit_log',
    'sairnbuild_audit_log',
    'sairncare_audit_log',
    'sairncode_audit_log',
    'sairndental_audit_log',
    'sairndesign_audit_log',
    'sairnfreedom_audit_log',
    'sairngrounds_audit_log',
    'sairnlaw_audit_log',
    'sairnlegacy_audit_log',
    'sairnmechanical_audit_log',
    'sairnroofing_audit_log',
    'sairnscape_audit_log',
    'sairnsenior_audit_log',
    'sairnvet_audit_log',
    'stonedesk_audit_log'
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

-- ── THE COVERAGE WIDENING, 2026-10-13 ─────────────────────────────────────
-- THE HALF THAT ACTS ON AN ALREADY-CREATED TABLE. `create table if not exists`
-- above silently skips an existing table, constraint and all, so without these
-- two statements a re-run of this file against the database as it stands would
-- report success and leave thirteen audit logs uncheckpointable.
--
-- WHY THIRTEEN WERE UNCHECKPOINTABLE AND NOTHING SAID SO: a checkpoint is what
-- makes an audit log tamper-EVIDENT, and the only tamper mode the grants leave
-- open is INSERTION of a back-dated row. The daily job covered three logs and
-- passed; the other thirteen -- including credential grants for a dental
-- practice, an assisted-living facility and an ORC Chapter 2915 gaming post --
-- had no tamper-evidence at all, and a back-dated row in any of them was
-- undetectable. The migration was SQL, the covered list was a JavaScript
-- constant, and no check compared them.
--
-- IDEMPOTENT BY CONSTRUCTION, not by convention: `drop constraint if exists`
-- makes the `add` safe on a second run, and the name is the one Postgres
-- generates for the inline CHECK above, so this acts on a table built by either
-- printing of this file. The two statements are deliberately NOT wrapped in a
-- DO block -- a constraint violation inside PL/pgSQL would be caught and
-- reported as a NOTICE, and a widening that silently did nothing is the exact
-- failure this block exists to end.
--
-- SAFE AGAINST EXISTING ROWS. The new list is a strict SUPERSET of the old
-- three names, so every row already in the table satisfies the new constraint
-- and the `add` cannot fail on a validation scan.
alter table public.sairn_audit_checkpoint
  drop constraint if exists sairn_audit_checkpoint_audit_table_check;
alter table public.sairn_audit_checkpoint
  add constraint sairn_audit_checkpoint_audit_table_check
  check (audit_table in (
    'sairnbiz_audit_log',
    'sairnbuild_audit_log',
    'sairncare_audit_log',
    'sairncode_audit_log',
    'sairndental_audit_log',
    'sairndesign_audit_log',
    'sairnfreedom_audit_log',
    'sairngrounds_audit_log',
    'sairnlaw_audit_log',
    'sairnlegacy_audit_log',
    'sairnmechanical_audit_log',
    'sairnroofing_audit_log',
    'sairnscape_audit_log',
    'sairnsenior_audit_log',
    'sairnvet_audit_log',
    'stonedesk_audit_log'
  ));

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

-- 1. The table exists. Expect: any number, INCLUDING 0.
--    REWORDED 2026-10-13. This query used to say "Expect: 0" because the file
--    had never been run. On a re-run that is wrong, and a reader following the
--    old comment would have read a healthy history as a failed migration. What
--    the query proves is that the relation RESOLVES -- an absent table errors
--    rather than returning 0, and those are the two states worth telling apart.
select count(*) from sairn_audit_checkpoint;

-- 1b. THE WIDENING TOOK, and this is the one query that answers the thing this
--     printing exists for. Expect: 16
select count(*)
  from pg_constraint c,
       lateral regexp_matches(pg_get_constraintdef(c.oid), '''([a-z0-9_]+)''', 'g') m
 where c.conname = 'sairn_audit_checkpoint_audit_table_check';

-- 1c. And NAME the sixteen, because a count of 16 over the wrong names would
--     pass 1b. Expect: the sixteen `*_audit_log` names from the CHECK above,
--     one per row, and NO `sv_audit_log`.
select m[1] as audit_table
  from pg_constraint c,
       lateral regexp_matches(pg_get_constraintdef(c.oid), '''([a-z0-9_]+)''', 'g') m
 where c.conname = 'sairn_audit_checkpoint_audit_table_check'
 order by 1;

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
