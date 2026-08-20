-- sql/sairncare_activities_schema.sql
-- SAIRNcare Activities calendar + attendance -- Supabase schema
--
-- WHY THIS IS A SIMPLE, BROAD-READ RESOURCE, unlike alf_mar/alf_billing:
-- an activity (bingo, an exercise class, an outing) and who attended it is
-- operational/participation data, not clinical or financial data -- the
-- same reasoning that let SAIRNsenior's Compliance panel show caregiver
-- certification status broadly ("operational data... not client PHI").
-- Read is open to any authenticated employee (everyone benefits from
-- knowing the activity calendar, including coordinating care around it).
--
-- WHY WRITE IS Owner + Activities ONLY: planning and running activities is
-- the Activities Coordinator's actual defined role -- the same scope-of-
-- practice reasoning that restricted alf_mar to owner/nursing/med_aide,
-- applied here in the other direction (Activities' own real job, not
-- something nursing/med_aide/caregiver/billing need write access to).
--
-- Attendance is embedded directly in the activity record (an attendees
-- array of resident_ids) rather than a separate per-resident table --
-- deliberately simple: one activity, one list of who came, no per-
-- resident write path needed through the alf_clients four-tier gate at
-- all (Activities has no write access there, by design).
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.alf_activities (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncare',
  entry_id     text not null,                        -- client-generated (ACT-<timestamp>)
  data         jsonb not null default '{}'::jsonb,    -- name, category, date, time, description,
                                                        -- created_by, attendees (array of resident_id)
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint alfactivities_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfactivities_license on public.alf_activities(license_hash);

grant select, insert, update on public.alf_activities to service_role;
revoke all on public.alf_activities from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from alf_activities;
