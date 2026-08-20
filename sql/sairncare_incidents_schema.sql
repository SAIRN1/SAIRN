-- sql/sairncare_incidents_schema.sql
-- SAIRNcare Compliance / Incident Reporting -- Supabase schema
--
-- REAL RESEARCH RUN BEFORE BUILDING (2026-08-20, see SAIRN-ACTIVE-WORK.md
-- for full sourcing), matching the v1 scope doc's own flag that this
-- "needs its own per-state verification pass, not guessed": no single
-- federal or uniform ALF incident-reporting standard exists. Reporting
-- DEADLINES vary widely and are real, sourced examples, not a complete
-- list: Virginia 24 hours (22VAC40-73-70), Massachusetts 24 hours,
-- California 7 days, Florida 15 days, Washington initial report +
-- 5-working-day follow-up. Reportable CATEGORIES converge much more than
-- deadlines do across the sourced states: falls with injury, medication
-- errors causing/likely-to-cause harm, elopement/wandering, injuries of
-- unknown origin, abuse/neglect/exploitation allegations, unexpected
-- death, unexpected hospitalization, and behavioral incidents posing risk.
--
-- ASYMMETRIC READ/WRITE, a deliberately different shape from alf_mar/
-- alf_billing: ANY authenticated employee may FILE a new incident report
-- (matches real mandatory-reporting-by-whoever-witnessed-it practice --
-- gating this behind a role would create a real incentive to under-report
-- if the person who saw something can't easily log it) but only
-- management/nursing/billing (compliance-oversight roles) may READ the
-- log or UPDATE an existing report after it's filed (add follow-up,
-- change status, mark state-reported) -- a frontline filer cannot go back
-- and alter their own report once submitted, same integrity reasoning as
-- alf_mar's append-only administration log, enforced differently here
-- because THIS record type legitimately needs later updates from a
-- different, more restricted set of roles.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.alf_incidents (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncare',
  entry_id     text not null,                        -- client-generated (INC-<timestamp>)
  resident_id  text,                                  -- nullable -- not every incident involves
                                                        -- a specific resident (e.g. a facility or
                                                        -- staff-safety event)
  data         jsonb not null default '{}'::jsonb,    -- category, date, time, description,
                                                        -- severity, reported_by, residents_involved,
                                                        -- action_taken, status, state_reported,
                                                        -- state_reported_date, state_reported_method,
                                                        -- follow_up_notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint alfincidents_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfincidents_license on public.alf_incidents(license_hash);

grant select, insert, update on public.alf_incidents to service_role;
revoke all on public.alf_incidents from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from alf_incidents;
