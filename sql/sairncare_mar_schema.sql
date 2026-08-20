-- sql/sairncare_mar_schema.sql
-- SAIRNcare Medication Administration Record (MAR) -- Supabase schema
--
-- WHY THIS IS A SEPARATE TABLE, NOT folded into alf_clients.data like ADL
-- assessments: ADL assessments are low-frequency (periodic reassessment),
-- bounded growth. Medication administration events are high-frequency (one
-- row per dose, potentially several times a day per resident, ongoing for
-- the length of the stay) -- folding that into alf_clients.data would blow
-- past its 64KB per-resident size cap within weeks for an active resident.
-- Same reasoning sen_visits used for the identical high-vs-low-frequency
-- split against sen_clients.
--
-- WHY THIS IS A SEPARATE GATE, NOT the alf_clients four-tier gate: medication
-- data carries real scope-of-practice sensitivity that resident-record edit
-- access does not. alf_clients' narrow tier (med_aide AND caregiver) can
-- edit any field of their own assigned resident -- appropriate for ADL/
-- general notes, NOT appropriate for medication orders or administration
-- records, which only a medication-certified role (or clinical/management
-- oversight) should be able to touch. This table is gated to owner/
-- nursing/med_aide ONLY -- caregiver, billing, and activities get a real
-- 403 on every alf_mar action, never silent access via the general
-- resident-write path.
--
-- entry_type discriminates five real sub-shapes, researched before
-- building (2026-08-20 MAR research pass, no single uniform ALF standard
-- found -- see SAIRN-ACTIVE-WORK.md for full sourcing):
--   medication_order    -- the standing order (name, dose, route, schedule,
--                          prn flag, controlled-substance flag, prescriber).
--                          Mutable-in-place: payload.id stays the same
--                          across edits/discontinue, same upsert shape as
--                          alf_clients itself. owner/nursing only.
--   administration       -- one real dose event (given/refused/held/not
--                          available). Append-only -- a fresh id every
--                          time, never edited after the fact (server
--                          rejects reusing an id already used for this
--                          type -- see api/sd-data.js). owner/nursing
--                          facility-wide, med_aide own-assigned-only.
--   count                 -- controlled-substance count (the one genuinely
--                          converged best practice found in research: a
--                          joint count with a second signature). Append-
--                          only, same as administration.
--   reconciliation        -- admission/transfer/discharge medication
--                          reconciliation. Borrowed from Joint Commission
--                          NPSG.03.06.01 (a hospital accreditation
--                          standard, NOT an ALF regulatory requirement --
--                          labelled as such in the client UI). owner/
--                          nursing only, append-only.
--   assessment_refusal    -- refusal of a medication-management
--                          ASSESSMENT specifically (distinct from refusing
--                          a routine dose, which is an 'administration'
--                          entry with status:'refused'). Modelled on
--                          Minnesota Stat. 144G.71's real requirement to
--                          document refusal of this specific assessment
--                          type. owner/nursing only, append-only.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.alf_mar (
  id                    uuid primary key default gen_random_uuid(),
  license_hash          text not null,
  app_id                text not null default 'sairncare',
  entry_id              text not null,                 -- client-generated (MAR-<timestamp> or a
                                                          -- stable medication id for medication_order)
  resident_id           text not null,                  -- references alf_clients.client_id
  assigned_employee_id  text,                            -- denormalized from alf_clients at write
                                                          -- time (live-looked-up, never trusted from
                                                          -- the client) -- null = resident unassigned
  entry_type            text not null,                   -- medication_order | administration | count |
                                                          -- reconciliation | assessment_refusal
  data                  jsonb not null default '{}'::jsonb,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint alfmar_entry_type_check check (entry_type in
    ('medication_order','administration','count','reconciliation','assessment_refusal')),
  constraint alfmar_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfmar_license on public.alf_mar(license_hash);
create index if not exists idx_alfmar_resident on public.alf_mar(license_hash, resident_id);
create index if not exists idx_alfmar_assignee on public.alf_mar(license_hash, assigned_employee_id);

grant select, insert, update on public.alf_mar to service_role;
revoke all on public.alf_mar from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from alf_mar;
