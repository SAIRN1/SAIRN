-- sql/sairnbiz_timesheet_schema.sql
-- SAIRNbiz: recorded timesheet hours. Additive, idempotent
-- (create table if not exists), safe to re-run.
--
-- WHY THIS TABLE EXISTS, and it is not "one more collection". Until
-- 2026-09-15 the Timesheets panel had NO WRITE PATH AT ALL. rTS() built every
-- table cell and five KPIs from `td`, an eight-row array of hours written into
-- the source and indexed by each employee's POSITION in the filtered Active
-- list, with `|| [8,8,8,8,8,0]` for anyone past the eighth. The pay RATES are
-- real, so "Labor Cost (Week)" multiplied a real rate by an invented week.
-- Deactivating one employee moved another employee's overtime onto them. The
-- ninth hire got a full week nobody worked.
--
-- That was removed first and the panel told the truth about having no hours
-- (200aaba8). This is the other half: a way to record real ones.
--
-- ONE ROW IS ONE EMPLOYEE'S ONE WEEK, and `ts_id` is `<employee_id>|<week>`
-- rather than a generated id. That is deliberate and is the only interesting
-- decision in this file: a generated id would let the same employee-week be
-- saved twice, and two disagreeing timesheets for one week is a payroll
-- dispute with no tiebreaker. A deterministic id makes a re-save an UPDATE
-- through the existing on_conflict path, so correcting Tuesday is a correction
-- and not a second record.
--
-- NO DELETE GRANT, matching every other non-sc_* schema on this platform since
-- 2026-08-25. api/sd-data.js's generic SB_RESOURCES block handles read and
-- write only, so there is no delete path to grant for -- and recorded hours
-- are what wages are computed from, which is not a record to hand anybody a
-- destroy verb over by default. Correcting a week is a re-save.

create extension if not exists pgcrypto;

create table if not exists public.sb_ts (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbiz',
  ts_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, ts_id),
  constraint sb_ts_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sb_ts_license on public.sb_ts(license_hash);
alter table public.sb_ts enable row level security;
revoke all on public.sb_ts from service_role;
grant select, insert, update on public.sb_ts to service_role;
