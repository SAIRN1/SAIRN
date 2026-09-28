-- sql/sairncare_incidents_recorded_by.sql
--
-- RUN THIS ONCE IN THE SUPABASE SQL EDITOR. Safe to re-run.
--
-- ── WHY ────────────────────────────────────────────────────────────────────
-- `alf_incidents` had NO server-recorded filer. Four sibling SAIRNcare tables
-- carry `recorded_by` (compliance, family_contacts, op_audit, and the remaining
-- migrations file); incidents was the one that did not. Two consequences, and
-- the second is a security finding in its own right:
--
--   1. A care role could not be shown "the reports I filed", because there was
--      nothing to filter on.
--   2. The schema's own comment documents `reported_by` INSIDE the `data` blob,
--      and that blob is `storedBlob(payload, ['id','resident_id','created_at'])`
--      -- a copy of the caller's payload with three keys deleted. So
--      the `reported_by` key inside the `data` blob is WHATEVER THE CALLER SENT. Combined with the write
--      being deliberately open to any authenticated employee (mandated
--      reporting), ANY EMPLOYEE COULD FILE AN INCIDENT ATTRIBUTED TO ANYONE
--      ELSE. The incident category list includes abuse, neglect and
--      exploitation allegations, so the reporter's identity is not cosmetic.
--
-- ── WHAT THIS DOES, AND WHAT IT DELIBERATELY DOES NOT ──────────────────────
-- Adds `recorded_by text`, which the sd-data endpoint sets from the verified session
-- and never from the payload.
--
-- IT DOES NOT BACKFILL. Existing rows keep recorded_by NULL. Michael's decision,
-- 2026-09-27, and the reasoning is the point: the only candidate source is
-- the `reported_by` key inside the `data` blob, which is caller-controlled and therefore untrustworthy --
-- back-filling from it would launder a forgeable field into an authoritative
-- column, which is worse than leaving it empty.
--
-- THE CONSEQUENCE IS STATED RATHER THAN DISCOVERED: legacy incidents are
-- UNREADABLE to the care role that filed them, because the server cannot tell
-- who that was. Management (owner / nursing / billing) reads all incidents as
-- before, so no report becomes unreachable -- only the self-service view is
-- empty for rows predating this migration.
--
-- IT IS NOT `not null`. A NOT NULL column with no default would refuse the
-- migration outright on a table with existing rows, and a default would invent
-- an author. NULL means "filed before this column existed", which is a true
-- statement and is the only honest value.

alter table public.alf_incidents
  add column if not exists recorded_by text;

-- ── THERE IS NO `comment on column` HERE, AND THAT IS NOT AN OVERSIGHT ─────
-- One was written and removed 2026-09-27. tools/sairn_sql_preflight.py cannot
-- parse `comment on column <t>.<c> is 'literal' 'literal';` -- the adjacent
-- string-literal concatenation is read as SQL, and a bare word out of the prose
-- ("the") is reported as MISSING_TABLE. The gate then blocks the push over a
-- table that exists only inside an English sentence.
--
-- THE GATE IS RIGHT TO BE STRICT and I did not override it: its whole argument
-- is that a wrong column in a WHERE matches nothing and reports success, which
-- is why it blocks before a file reaches the editor rather than after. So the
-- column documentation lives in this header instead, where nothing parses it,
-- and the parser gap is reported rather than worked around in silence.
-- DO NOT "helpfully" add the comment back without checking that first.


-- Supports the care-role self-scope read, which filters on
-- (license_hash, recorded_by).
create index if not exists idx_alfincidents_recorded_by
  on public.alf_incidents(license_hash, recorded_by);

-- ── VERIFY, rather than assuming the editor reported success ───────────────
-- Expect one row, data_type text, is_nullable YES.
select column_name, data_type, is_nullable
  from information_schema.columns
 where table_schema = 'public'
   and table_name   = 'alf_incidents'
   and column_name  = 'recorded_by';
