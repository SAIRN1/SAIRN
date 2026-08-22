-- sql/sairncare_op_audit_schema.sql
-- SAIRNcare Phase 3 item 5: operational-audit layer.
-- Food safety, sanitation, and emergency-preparedness drills.
--
-- WHY THIS IS A SEPARATE TABLE AND A SEPARATE GATE FROM THE CLINICAL eMAR,
-- stated plainly because the separation is the design decision, not an
-- accident of layout:
--
--   DIFFERENT RECORD CLASS. A refrigerator temperature log and a fire-drill
--   record are FACILITY-compliance records. They are not resident health
--   information. Folding them into alf_mar would put non-PHI operational data
--   behind a scope-of-practice gate built for medication records, and would
--   drag facility maintenance logs into the retention and disclosure posture
--   that resident clinical data carries.
--
--   DIFFERENT REVIEWERS. alf_mar is gated to owner/nursing/med_aide because
--   medication data carries scope-of-practice sensitivity. The people who
--   actually take a walk-in cooler temperature or run an evacuation drill are
--   dietary, housekeeping and maintenance staff -- who have no business in the
--   MAR, and who must not be locked out of their own compliance logs to keep
--   them out of it. So recording is open to any authenticated employee, and
--   MANAGEMENT SIGN-OFF is the separate privileged act.
--
--   DIFFERENT RETENTION. Clinical records and facility-compliance records are
--   retained on different schedules under different authorities. Keeping them
--   in one table would force one retention rule onto both.
--
-- APPEND-ONLY. A temperature reading or a completed drill asserts what was
-- observed at a moment in time. A correction is a NEW entry that supersedes,
-- never an overwrite -- the same rule alf_mar's administration entries and
-- alf_staff_credentials already follow, for the same reason.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.alf_op_audits (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairncare',
  entry_id      text not null,                  -- client-generated (OPA-<timestamp>)
  record_type   text not null,                   -- food_temp | sanitation | emergency_drill
  -- Denormalised so the compliance view can filter without unpacking jsonb.
  observed_on   date,
  passed        boolean,                         -- null = not evaluated against a threshold
  data          jsonb not null default '{}'::jsonb,
  recorded_by   text,                            -- server-stamped from the real session
  -- Sign-off is deliberately separate from recording: the person who takes the
  -- reading is not the person who attests the log was reviewed.
  reviewed_by   text,
  reviewed_at   timestamptz,
  created_at    timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint alfopa_type_check check (record_type in ('food_temp','sanitation','emergency_drill')),
  constraint alfopa_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfopa_license on public.alf_op_audits(license_hash);
create index if not exists idx_alfopa_type on public.alf_op_audits(license_hash, record_type);
create index if not exists idx_alfopa_date on public.alf_op_audits(license_hash, observed_on);

grant select, insert, update on public.alf_op_audits to service_role;
revoke all on public.alf_op_audits from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from alf_op_audits;
