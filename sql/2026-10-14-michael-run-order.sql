-- sql/2026-10-14-michael-run-order.sql
-- ===========================================================================
-- SIX BLOCKS, IN ORDER, ONE AT A TIME. Paste ONE block into the Supabase SQL
-- editor, run it, run its VERIFY, check the answer against the expected result
-- printed beside it, and only then move to the next.
--
-- Assembled 2026-10-14 (hank b10) because the work it applies was written
-- across five separate files over two batches and nothing said what order to
-- run them in or how to tell a block that worked from one that silently did
-- nothing.
--
-- ── EVERY BLOCK IS INDEPENDENTLY RUNNABLE AND IDEMPOTENT ──────────────────
-- No block depends on an earlier one. Running any of them twice is safe and
-- changes nothing the second time. If a block fails, the ones after it are
-- still valid to run -- they do not share a transaction.
--
-- ── WHY A VERIFY ON EVERY BLOCK, AND WHY ITS ANSWER IS PRINTED ────────────
-- `create table if not exists` SKIPS an existing table, constraint and all,
-- and the Supabase editor reports SUCCESS for it. Several blocks below exist
-- precisely because an earlier run of their source file looked like it worked
-- and changed nothing. A clean run is NOT evidence; the verify's answer is.
-- "Could not tell" is a third state and is never the same as "done".
--
-- ── THIS FILE IS AN EXTRACTION, NOT A SECOND AUTHORING ────────────────────
-- Every statement below was taken verbatim from the file named in its block
-- header, not retyped -- a transcription error in a credential insert or a
-- CHECK list is invisible and presents as a 23514 or a 401 with
-- correct-looking SQL. api/sql-run-order-agreement.test.js re-reads each
-- source and FAILS if a block here is no longer a verbatim substring of it, so
-- this file cannot quietly drift from the files it copies.
--
-- THE SOURCES, AND THEIR SHA256 AT ASSEMBLY (LF-normalised):
--   c8c14e1ebe8b08328e0ec2eec3f8e981e1f64efc860e7107cc2a14e89c2f08a5  sql/2026-10-14-hank-b9-ai-safeguards.sql
--   d98242cfd7ad98816f4970c2b01e93799ec66e381bfb9ba09f63223fb7786f25  sql/audit_checkpoint_schema.sql
--   83a86e3a8c2594308722d7411806630485abd83e4b70a92fb84eca41b97940eb  sql/sairncare_employee_auth_schema.sql
--   0f4d0571ce189c2f9d165624266b1899b9287d8d635b495cf1c07d260209e6bf  sql/sairnfreedom_demo_owner_credential_2026-10-13.sql
--   24eb03f9481ad81d340b858b9d1c8716e3cb350ac5d93e3bc15fb3f9786a5a1b  sql/sairnlaw_audit_log_schema.sql
--   f1917c75af45c8919056cef36e7ddb7c2521d41cfee6112fc625a596b81b81c7  sql/sairnlegacy_employee_auth_schema.sql
--
-- ── WHAT IS BROKEN UNTIL EACH BLOCK RUNS ──────────────────────────────────
--   1  api/ai-notice.js answers 503 AI_NOTICE_NOT_PROVISIONED and NO employee
--      ever sees the AI notice.
--   2  thirteen of the sixteen audit logs have NO tamper-evidence: the daily
--      checkpoint job cannot write a row for them and a back-dated insert in
--      any of them is undetectable.
--   3  every credential deactivation, reactivation and refusal in SAIRNlaw
--      writes NO audit row. The insert is refused 23514, writeAuditLog is
--      non-fatal, the caller gets its 200, and nothing says the row is
--      missing.
--   4  SAIRNfreedom cannot be signed into at all, so every claim about its
--      gates is source-verified only.
--   5  SAIRNcare's office_manager role is minted by the server and REJECTED by
--      the database -- credential creation fails at the last step while the
--      app believes the role exists.
--   6  SAIRNlegacy's five new task roles are rejected the same way, so the
--      36-resource role matrix cannot be USED: nobody can be given a role
--      other than owner/director/staff.
--
-- BLOCK 6 IS NOT IN THE ORIGINAL FIVE-ITEM LIST and is here on purpose. It is
-- the exact counterpart of block 5 for the SAIRNlegacy role matrix that landed
-- in the same batch; leaving it out would have shipped a gate nobody could
-- populate. Flagged rather than folded in silently.
--
-- ── NONE OF THIS IS A DEPLOY ──────────────────────────────────────────────
-- These blocks change the DATABASE. The code that uses them is already
-- deployed, which is why blocks 1, 3, 5 and 6 are the thing currently
-- failing rather than a preparation for something later.
-- ===========================================================================


-- ===========================================================================
-- BLOCK 1 -- THE AI-NOTICE ACKNOWLEDGEMENT COLUMNS
-- source: sql/2026-10-14-hank-b9-ai-safeguards.sql
-- ===========================================================================
-- Adds two NULLABLE columns -- ai_notice_version (text) and ai_notice_acked_at
-- (timestamptz) -- to EVERY %_employee_auth table. NULL means "has not
-- acknowledged yet", which is where every existing row starts and is not an
-- error.
--
-- DERIVED FROM information_schema, NOT A LIST OF SIXTEEN NAMES. An app added
-- after this runs is covered by re-running the block, which is the whole
-- reason it is a loop. The selection is BY SUFFIX (`%_employee_auth`, public
-- schema) and that is the one thing to check: if a future app's table does not
-- end that way, the loop will not reach it and nothing will say so -- which is
-- what the verify below is for.
--
-- A LOOP THAT MATCHED NOTHING RAISES. Without that, an empty match prints
-- nothing, exits clean, and is indistinguishable from a successful run.
--
-- NO ROW IS WRITTEN, so PR 3.4's recoverability guard does not apply. Said
-- explicitly because "does not apply" and "was forgotten" look identical in a
-- file that simply lacks it. Nothing is granted or revoked: a new column
-- inherits the table's grants.

do $$
declare
  t record;
  n int := 0;
begin
  for t in
    select table_name
      from information_schema.tables
     where table_schema = 'public'
       and table_name like '%\_employee\_auth'
     order by table_name
  loop
    execute format(
      'alter table public.%I
         add column if not exists ai_notice_version text,
         add column if not exists ai_notice_acked_at timestamptz',
      t.table_name);
    n := n + 1;
    raise notice 'ai-notice columns ensured on %', t.table_name;
  end loop;

  -- A LOOP THAT MATCHED NOTHING IS A FAILURE, NOT A NO-OP. Without this an
  -- empty match prints nothing, exits clean, and reads exactly like a
  -- successful run on a database where the credential tables have not been
  -- created yet -- which is the silent pass this platform keeps paying for.
  if n = 0 then
    raise exception 'NO %%_employee_auth TABLE MATCHED. Nothing was altered. '
      'Either the credential schemas have not been run in this database, or '
      'the naming convention has changed and this file can no longer find '
      'them. Do not treat this as done.';
  end if;

  raise notice 'ai-notice columns ensured on % table(s)', n;
end $$;

-- ── VERIFY BLOCK 1 ─────────────────────────────────────────────────────────
-- EXPECTED: 16 rows. One per credential table, each with has_version = 1 and
-- has_acked_at = 1.
--
-- 16 is the number of entries in api/_lib/auth.js's AUTH_TABLE_BY_APP as of
-- 2026-10-14. RE-DERIVE IT rather than trusting this line -- it is the figure
-- that moves:
--
--   node -e "console.log(Object.keys(require('./api/_lib/auth').AUTH_TABLE_BY_APP).length)"
--
-- FEWER ROWS THAN THAT NUMBER -> an app's credential schema has not been run
--   in this database; that app gets 503 AI_NOTICE_NOT_PROVISIONED and nothing
--   else will mention it.
-- MORE ROWS -> there is a credential table in the database that the code does
--   not know about. That is a stale table, not a success.
-- ANY ROW WITH A 0 -> the ALTER did not reach that table. Re-run the block.

select c.table_name,
       count(*) filter (where c.column_name = 'ai_notice_version')  as has_version,
       count(*) filter (where c.column_name = 'ai_notice_acked_at') as has_acked_at
  from information_schema.columns c
 where c.table_schema = 'public'
   and c.table_name like '%\_employee\_auth'
   and c.column_name in ('ai_notice_version', 'ai_notice_acked_at')
 group by c.table_name
 order by c.table_name;


-- ===========================================================================
-- BLOCK 2 -- THE AUDIT CHECKPOINT TABLE, COVERING ALL SIXTEEN LOGS
-- source: sql/audit_checkpoint_schema.sql
-- ===========================================================================
-- Creates sairn_audit_checkpoint if it is absent, AND widens its audit_table
-- CHECK to all sixteen logs if it already exists carrying the original
-- three-name list.
--
-- BOTH HALVES ARE REQUIRED AND NEITHER IS REDUNDANT. `create table if not
-- exists` does not amend an existing table's constraint -- so anyone who
-- re-ran the schema file to "fix the coverage" got a clean run, no error, and
-- the same three names. That is why the ALTER pair below is not wrapped in a
-- DO block: a constraint violation inside PL/pgSQL would be caught and
-- reported as a NOTICE, and a widening that silently did nothing is the exact
-- failure it exists to end.
--
-- SAFE AGAINST EXISTING ROWS: the sixteen-name list is a strict superset of
-- the old three, so every stored row satisfies it and the validation scan
-- cannot fail.
--
-- WHAT IT BUYS: the audit logs already carry `grant select, insert` only, so
-- a row cannot be altered or removed through the API. The mode the grant
-- leaves OPEN is INSERTION of a back-dated row, and a daily digest chain is
-- what makes that detectable.

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

-- ── VERIFY BLOCK 2 ─────────────────────────────────────────────────────────
-- Run these three. Each answer is stated; a different answer means the block
-- did NOT do what it says.

-- 2a. The table exists. EXPECTED: any number, INCLUDING 0. An empty
--     checkpoint table is the correct state before the first daily run.
select count(*) from sairn_audit_checkpoint;

-- 2b. The CHECK permits SIXTEEN log names. EXPECTED: exactly 16.
--     A 3 here means the table pre-existed and the widening did not run --
--     which is the silent no-op this block exists to close.
select count(*)
  from pg_constraint c,
       lateral regexp_matches(pg_get_constraintdef(c.oid), '''([a-z0-9_]+)''', 'g') m
 where c.conname = 'sairn_audit_checkpoint_audit_table_check';

-- 2c. Write is INSERT-only for service_role. EXPECTED: exactly 2 rows,
--     INSERT and SELECT. An UPDATE or DELETE row here means a checkpoint can
--     be rewritten, and a rewritable checkpoint proves nothing.
select privilege_type
  from information_schema.role_table_grants
 where table_name = 'sairn_audit_checkpoint'
   and grantee = 'service_role'
 order by 1;

-- ===========================================================================
-- BLOCK 3 -- THE sairnlaw_audit_log CREDENTIAL-LIFECYCLE WIDENING
-- source: sql/sairnlaw_audit_log_schema.sql
-- ===========================================================================
-- Adds credential_deactivated, credential_reactivated and
-- credential_change_refused to the event_type CHECK.
--
-- MEASURED ACROSS THE WHOLE POPULATION: eleven api/*-auth.js files call
-- lifecycle.setActive and SAIRNlaw was the ONLY ONE of the eleven whose CHECK
-- rejected these three. That is why this is a one-table fix and the
-- denominator is stated rather than implied.
--
-- THE FULL LIST IS RESTATED, not appended to, because `add constraint`
-- replaces the whole predicate -- dropping a value here would REVOKE it.
--
-- SAFE AGAINST EXISTING ROWS: strict superset of the old seventeen.

alter table public.sairnlaw_audit_log
  drop constraint if exists sairnlaw_audit_log_event_type_check;
alter table public.sairnlaw_audit_log
  add constraint sairnlaw_audit_log_event_type_check
  check (event_type in (
    'login_success',
    'login_failed',
    'lockout',
    'pin_bootstrap',
    'pin_setup',
    'mfa_enrolled',
    'mfa_verified',
    'mfa_failed',
    'sso_login',
    'sso_link',
    'citator_lookup',
    'ai_interaction',
    'ai_rejected',
    'ai_reviewed',
    'ai_used_in_filing',
    'deadline_engine',
    'legal_reference_lookup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  ));

-- ── VERIFY BLOCK 3 ─────────────────────────────────────────────────────────
-- 3a. TWENTY event types are permitted. EXPECTED: 20.
--     17 means this block has not run.
select count(*)
  from pg_constraint c,
       lateral regexp_matches(pg_get_constraintdef(c.oid), '''([a-z0-9_]+)''', 'g') m
 where c.conname = 'sairnlaw_audit_log_event_type_check';

-- 3b. And the three new ones are among them. EXPECTED: exactly 3 rows --
--     credential_change_refused, credential_deactivated,
--     credential_reactivated.
select m[1] as event_type
  from pg_constraint c,
       lateral regexp_matches(pg_get_constraintdef(c.oid), '''([a-z0-9_]+)''', 'g') m
 where c.conname = 'sairnlaw_audit_log_event_type_check'
   and m[1] in ('credential_deactivated', 'credential_reactivated',
                'credential_change_refused')
 order by 1;

-- 3c. A PERMITTED VALUE IS NOT A WRITTEN ROW, and only one of these two
--     proves the feature works. After deactivating a non-provisioning
--     SAIRNlaw credential through the API, run:
--     EXPECTED: one or more rows -> the widening landed AND the emission path
--     works. ZERO rows -> either this block has not run or the emission never
--     fired, and 3a tells those two apart.
select event_type, employee_id, created_at
  from public.sairnlaw_audit_log
 where event_type like 'credential_%'
 order by created_at desc
 limit 5;

-- ===========================================================================
-- BLOCK 4 -- THE SAIRNfreedom DEMO SIGN-IN
-- source: sql/sairnfreedom_demo_owner_credential_2026-10-13.sql
-- ===========================================================================
-- Licence SF-PINNACLE-2026, employee sairn-demo-owner, role post.govern,
-- PIN 64927108.
--
-- THE PIN IS PUBLISHED ON PURPOSE and the precondition is the basis: a
-- credential nobody can find is a credential nobody uses. SF-PINNACLE-2026 is
-- a DEMO licence (demo@pinnaclepost.example, plan `demo`) and holds no real
-- post's data. THE MOMENT THIS LICENCE IS GIVEN TO A REAL POST OR LOADED WITH
-- REAL MEMBER, LEDGER OR ORC 2915 GAMING DATA, THIS ROW MUST BE DELETED AND
-- THE PIN ROTATED.
--
-- THE ROLE IS post.govern, READ OFF THE APP. There is no `owner` role in
-- SAIRNfreedom, so a file copied from a sibling would insert a role the CHECK
-- rejects.
--
-- ONE TRANSACTION, insert and guard together: a guard that cannot roll back
-- what it just objected to is a notice, not a guard. The recoverability guard
-- is PR 3.4's -- a licence with credential rows and ZERO active provisioners
-- is unrecoverable through the API, and this file is required to prove it does
-- not create that state even though it only ADDS an active provisioner.
--
-- PRECONDITION: sql/sairnfreedom_license_seed.sql must have been run, or
-- /api/sf-auth refuses the login with an invalid-licence error that LOOKS like
-- a bad PIN. Verify 4b is what tells those apart.

begin;

-- sairnfreedom  --  SF-PINNACLE-2026  --  PIN 64927108
insert into public.sairnfreedom_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '78a8517ee72db892008b29f116109b9cb2f03dcfef648a1a0bbc03df61b9045a',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'post.govern',
  'e845f935acf7c8cba1ef26db719830c84827e94a9dfae9b4904f1511f9051903578f40c20cc73f0b8e4a66d652fdd1ad4e57c50c8edf8a637d87bc1738341d4d',
  '31e985cf3708d5d90e874ed1b2ea7a82',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- ── RECOVERABILITY GUARD ───────────────────────────────────────────────────
-- Required by CLAUDE.md of any SQL that writes credential rows, and enforced by
-- tools/employee_auth_guard_check.py as check 2 of the push hook. A licence with
-- credential rows and ZERO rows that are both `active` and hold a provisioning
-- role is UNRECOVERABLE THROUGH THE API: `bootstrap` refuses 409 while any row
-- exists, and `setup` and `set_active` both need an active provisioner.
-- RF-PINNACLE-2026 sat in that state and nothing noticed.
--
-- THIS FILE ONLY ADDS AN ACTIVE PROVISIONER, so it cannot create that state --
-- which is exactly why the guard should PASS rather than be skipped. A guard
-- that is only written when somebody fears it will fail is not a guard.
--
-- THE ROLE ARRAY IS THIS APP'S OWN: post.govern and post.govern.deputy, from
-- api/sf-auth.js's PROVISIONING_ROLES. An array hardcoding 'owner' would pass
-- SAIRNfreedom clean forever while checking nothing, because no row can ever
-- hold that role here.
do $$
declare
  lh   text;
  rows int;
  prov int;
begin
  lh := encode(digest('SF-PINNACLE-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sairnfreedom_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairnfreedom_employee_auth
   where license_hash = lh and active = true
     and role = any (array['post.govern','post.govern.deputy']);
  if rows > 0 and prov = 0 then
    -- THE MARKER IS ON ONE LINE DELIBERATELY. tools/employee_auth_guard_check.py
    -- matches the contiguous string "ZERO active provisioners" in CODE, and a
    -- message wrapped between "ZERO" and "active" is invisible to it -- that
    -- exact wrap made it refuse a correct file on 2026-09-29, and it refused
    -- this one on first write for the same reason.
    raise exception
      'ABORTED: SF-PINNACLE-2026 would be left with credential rows and ZERO active provisioners (% row(s)). '
      'Delete EVERY row for this licence, or leave at least one active '
      'provisioner. Never a subset of the provisioners.', rows;
  end if;
  raise notice 'SF-PINNACLE-2026: % row(s), % active provisioner(s).', rows, prov;
  -- AND THE HASH MUST MATCH THE ONE THIS FILE JUST WROTE. Without this, a
  -- pre-existing `sairn-demo-owner` row whose ON CONFLICT update silently did
  -- not apply would leave the documented PIN wrong and the guard green.
  if not exists (
    select 1 from public.sairnfreedom_employee_auth
     where license_hash = lh and employee_id = 'sairn-demo-owner'
       and role = 'post.govern' and active = true
       and pin_salt = '31e985cf3708d5d90e874ed1b2ea7a82') then
    raise exception
      'ABORTED: the sairn-demo-owner row does not carry the PIN salt this file '
      'wrote, so the PIN documented in docs/2026-09-03-demo-credentials.md '
      'would not work. Nothing has been committed.';
  end if;
  raise notice 'Guard passed: the demo credential is present and is the one documented.';
end $$;

commit;

-- ── VERIFY BLOCK 4 ─────────────────────────────────────────────────────────
-- 4a. EXPECTED: exactly 1 row -- sairn-demo-owner | post.govern | t
select employee_id, role, active
  from public.sairnfreedom_employee_auth
 where license_hash = encode(digest('SF-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id = 'sairn-demo-owner';

-- 4b. The licence row this credential signs in under. EXPECTED: 1 row, status
--     `active`, app_id `sairnfreedom`. ZERO ROWS means the licence seed has
--     not been run and the login will fail for THAT reason, not a bad PIN.
select key, status, app_id, plan
  from public.license_keys
 where key = 'SF-PINNACLE-2026';

-- 4c. THEN THROUGH THE DEPLOYED API, which is the only real proof -- a clean
--     insert is not evidence the app accepts it. Not SQL; run it in a shell:
--
--       curl -s -X POST https://sairn.vercel.app/api/sf-auth \
--         -H 'Content-Type: application/json' \
--         -H 'Authorization: Bearer SF-PINNACLE-2026' \
--         -d '{"action":"login","employee_id":"sairn-demo-owner","pin":"64927108"}'
--
--     EXPECTED: 200 with role "post.govern" and a token.
--     401 INVALID_CREDENTIALS   -> this block has not run, or the PIN differs.
--     an invalid-licence refusal -> the LICENCE SEED has not been run (4b).

-- ===========================================================================
-- BLOCK 5 -- SAIRNcare: THE office_manager ROLE CHECK
-- source: sql/sairncare_employee_auth_schema.sql
-- ===========================================================================
-- Michael's decision, 2026-10-14: add the role rather than declare `owner` to
-- BE the office manager. The server already mints it; until this runs the
-- database refuses it 23514 and credential creation fails at the last step
-- while the app believes the role exists.
--
-- THE FULL LIST IS RESTATED because `add constraint` replaces the whole
-- predicate. Strict superset of the old six, so existing rows all satisfy it.
--
-- sql/sairncare_all_remaining_migrations.sql declares the SAME table with the
-- same widened inline list. This ALTER acts on the table by name, so running
-- it once is enough whichever file built it -- it is deliberately not
-- duplicated.

alter table public.sairncare_employee_auth
  drop constraint if exists sairncare_employee_auth_role_check;
alter table public.sairncare_employee_auth
  add constraint sairncare_employee_auth_role_check
  check (role in ('owner','nursing','med_aide','caregiver','billing',
                  'activities','office_manager'));

-- ── VERIFY BLOCK 5 ─────────────────────────────────────────────────────────
-- EXPECTED: exactly 1 row, and its text must contain 'office_manager'
-- alongside the six existing roles. If 'office_manager' is absent, the ALTER
-- did not run.
-- VERIFY. Expect exactly 1 row, and the definition must contain
-- 'office_manager'.
select pg_get_constraintdef(c.oid) as role_check
  from pg_constraint c
 where c.conname = 'sairncare_employee_auth_role_check';


-- ===========================================================================
-- BLOCK 6 -- SAIRNlegacy: THE FIVE TASK ROLES
-- source: sql/sairnlegacy_employee_auth_schema.sql
-- ===========================================================================
-- NOT IN THE ORIGINAL FIVE-ITEM LIST. It is here because the SAIRNlegacy role
-- matrix landed in the same batch and without this block nobody can be given
-- any role other than owner/director/staff -- a 36-resource gate that cannot
-- be populated.
--
-- 'staff' IS IN THE LIST AND MUST STAY. It is deprecated, not removed: every
-- existing credential row holds it, and dropping the value would make all of
-- them violate the constraint and the ALTER itself would fail on the
-- validation scan. The deprecation is enforced in api/_lib/leg-roles.js, which
-- maps it to the narrowest band, and in sairnlegacy.html's provisioning
-- picker, which no longer offers it.

alter table public.sairnlegacy_employee_auth
  drop constraint if exists sairnlegacy_employee_auth_role_check;
alter table public.sairnlegacy_employee_auth
  add constraint sairnlegacy_employee_auth_role_check
  check (role in ('owner','director','arranger','prep','office',
                  'apprentice','livery','staff'));

-- ── VERIFY BLOCK 6 ─────────────────────────────────────────────────────────
-- EXPECTED: exactly 1 row, and its text must contain all EIGHT roles --
-- owner, director, arranger, prep, office, apprentice, livery, staff.
-- If only three appear, the ALTER did not run.
-- VERIFY. Expect exactly 1 row, and the definition must contain all eight.
select pg_get_constraintdef(c.oid) as role_check
  from pg_constraint c
 where c.conname = 'sairnlegacy_employee_auth_role_check';


-- ===========================================================================
-- AFTER ALL SIX
-- ===========================================================================
-- Nothing here reports on the set. Each block's verify is the only statement
-- that says anything about it, and a block whose verify was not read is a
-- block whose result is unknown rather than good.
