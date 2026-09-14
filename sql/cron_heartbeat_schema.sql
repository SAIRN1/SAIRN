-- sql/cron_heartbeat_schema.sql
-- ---------------------------------------------------------------------------
-- ONE ROW PER SCHEDULED JOB, SAYING WHEN IT LAST FINISHED AND HOW. Item 54.
--
-- ── THE GAP THIS CLOSES, STATED ACCURATELY ─────────────────────────────────
-- api/sairndental/send-reminder.js ALREADY logs `sweep complete -- scanned N,
-- sent N, ...` on every run, and its own comment says why: without it a sweep
-- that found nothing due would be indistinguishable from one that never ran,
-- because Vercel discards a cron's response body. That log line is correct and
-- it does distinguish those two cases -- a sweep that sent reminders and one
-- that found nothing carry different counts.
--
-- WHAT IS MISSING IS THAT NOTHING WATCHES FOR THE LINE'S ABSENCE. A cron that
-- stops firing, times out, or 500s writes NO line at all, and no log is
-- searched for a thing that is not there. Absence is the one signal a log
-- cannot volunteer.
--
-- ── WHY A TABLE AND NOT A LOG QUERY ────────────────────────────────────────
-- Reading Vercel's logs needs a Vercel API token and a retention window that is
-- not ours to control. A heartbeat row is readable by anything holding the
-- service key, survives log rotation, and -- the part that matters -- can be
-- read from OUTSIDE Vercel entirely, which is what makes an out-of-band check
-- possible at all.
--
-- ── THIS TABLE IS UPDATED IN PLACE, UNLIKE THE AUDIT LOGS ──────────────────
-- Deliberate, and the difference is the point. An audit log is a record of what
-- happened and gets `select, insert` only. A heartbeat is a CURRENT-STATE
-- marker: the question is "when did this job last finish", and keeping every
-- beat forever would make the table grow without bound while answering the same
-- question worse. So this one carries UPDATE, and it is NOT an audit surface --
-- a reader wanting history reads the audit log, not this.
--
-- ── EXPECTED INTERVAL LIVES WITH THE JOB, NOT HERE ─────────────────────────
-- `expected_interval_seconds` is written by the job itself on every beat rather
-- than configured in this table. A schedule changed in vercel.json and not here
-- would make the watchdog alarm on a healthy job or stay silent on a dead one,
-- and there is no mechanism that would ever catch the drift. One source: the
-- job states its own cadence every time it runs.
--
-- WRITTEN 2026-09-14. NOT RUN. Until it is, api/_lib/heartbeat.js fails quietly
-- (it is best-effort by design) and api/cron-watchdog.js answers 503
-- NOT_PROVISIONED naming this file rather than reporting "no stale jobs" over a
-- table that does not exist -- which would be the cheeriest possible way to say
-- nothing is being watched.
-- ---------------------------------------------------------------------------

create table if not exists sairn_cron_heartbeat (
  -- The job's own name, matching the vercel.json cron path it is invoked by.
  -- PRIMARY KEY so an upsert is a single statement and two concurrent beats
  -- from the same job cannot produce two rows -- which would make the watchdog
  -- read the older one half the time and alarm at random.
  job text primary key,
  last_run_at timestamptz not null,
  -- 'ok' | 'partial' | 'failed'. A job that ran and FAILED is a different fact
  -- from a job that did not run, and collapsing them would make the watchdog
  -- unable to tell "it is dead" from "it is alive and unhappy" -- which need
  -- different responses.
  outcome text not null check (outcome in ('ok', 'partial', 'failed')),
  -- Whatever the job wants the next reader to know: counts, the first error,
  -- how much it skipped. Free-form on purpose; the watchdog does not parse it.
  detail jsonb,
  -- DECLARED BY THE JOB, on every beat. See the header for why it does not live
  -- in a config table.
  expected_interval_seconds integer not null check (expected_interval_seconds > 0),
  updated_at timestamptz not null default now()
);

create index if not exists idx_sairn_cron_heartbeat_last
  on sairn_cron_heartbeat (last_run_at desc);

-- SELECT, INSERT and UPDATE. No DELETE: removing a heartbeat row is how a dead
-- job stops being noticed, and there is no legitimate product reason to do it.
-- A job that is retired should have its row left behind and its cron entry
-- removed -- the watchdog then says so loudly, which is the correct outcome for
-- a job somebody forgot to finish decommissioning.
grant select, insert, update on public.sairn_cron_heartbeat to service_role;
revoke delete on public.sairn_cron_heartbeat from service_role;
revoke all on public.sairn_cron_heartbeat from anon, authenticated;

alter table sairn_cron_heartbeat enable row level security;

drop policy if exists sairn_cron_heartbeat_service_write on sairn_cron_heartbeat;
create policy sairn_cron_heartbeat_service_write
  on sairn_cron_heartbeat for all
  to service_role
  using (true) with check (true);

-- ── VERIFY, one query per statement with the answer it must give ───────────

-- 1. The table exists and is empty. Expect: 0
select count(*) from sairn_cron_heartbeat;

-- 2. service_role holds SELECT, INSERT and UPDATE -- and NOT DELETE.
--    Expect exactly three rows: INSERT, SELECT, UPDATE.
select privilege_type
  from information_schema.role_table_grants
 where table_name = 'sairn_cron_heartbeat'
   and grantee = 'service_role'
 order by privilege_type;

-- 3. anon and authenticated hold nothing. Expect: 0
select count(*)
  from information_schema.role_table_grants
 where table_name = 'sairn_cron_heartbeat'
   and grantee in ('anon', 'authenticated');

-- 4. `job` is the primary key, so an upsert cannot fork into two rows.
--    Expect: 1
select count(*)
  from pg_constraint
 where conrelid = 'sairn_cron_heartbeat'::regclass
   and contype = 'p';

-- 5. RLS is on. Expect: t
select relrowsecurity from pg_class where relname = 'sairn_cron_heartbeat';
