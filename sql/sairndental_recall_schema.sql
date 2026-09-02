-- sql/sairndental_recall_schema.sql
-- SAIRNdental recall & reactivation outreach -- Supabase schema (2026-09-02)
--
-- Competitive-gap audit item A8. Additive and idempotent; run after
-- sql/sairndental_data_schema.sql. Nothing in that file is duplicated here.
--
-- WHAT THIS STORES, AND WHAT IT DOES NOT. One row per contact ACTUALLY MADE
-- with a patient about being due back: when, by what channel, what the outcome
-- was, and a free note. That is all.
--
-- IT IS NOT A SEND QUEUE. SAIRNdental sends nothing from this panel -- no
-- email, no text, no call. A table that looked like a queue would invite a
-- future reader to assume something dispatched from it, which is precisely the
-- silent failure that left api/sairndental/send-reminder.js returning a 500
-- every hour for months while everyone believed reminders were going out. A
-- row here means a person made contact.
--
-- WHY THERE IS NO "DUE DATE" COLUMN. Who is due is COMPUTED at render time from
-- the last completed appointment for that patient and that procedure, plus the
-- interval the practice set on the procedure type (or the override set on the
-- patient). Storing a due date would create a second source of truth that goes
-- stale the moment a patient is seen, and the whole point of the worklist is
-- that it is derived from appointments that really happened.
--
-- THE INTERVALS THEMSELVES ARE NOT HERE EITHER. recall_months lives on the
-- dnt_procedure_types row and recall_months_override on the dnt_patients row,
-- because they are properties of the procedure and the patient. There is
-- deliberately NO DEFAULT ANYWHERE: a six-month recall is a convention, not a
-- rule, and the profession's own guidance is that intervals should be
-- risk-based and set per patient. A practice that has set none is told there is
-- nothing to compute rather than shown a worklist resting on a number this
-- software invented.
--
-- ACCESS. Registered in api/_resources/sairndental.js and handled by the
-- generic DNT_RESOURCES block in api/sd-data.js, where it is listed as
-- patient-scoped (DNT_PATIENT_SCOPED_RESOURCES on patient_id) -- the row names
-- a patient and records what they said -- and deliberately NOT financial. It
-- carries no charge and no estimate, and the hygiene side works the recall list
-- as much as the front desk does, so putting it behind the owner/front-desk
-- money gate would hide the worklist from the people who work it.
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy -- matching
-- every other dnt_* table. api/sd-data.js is the only door in.
--
-- NO DELETE GRANT. sql/unused_delete_grant_revoke_2026-08-24.sql revoked it
-- platform-wide across 134 tables; the only reachable delete path anywhere is
-- api/sd-data.js's SC_RESOURCES branch. This file is `create table if not
-- exists` and safe to re-run, so granting delete here would silently restore
-- what that sweep removed. Do not add it.
--
-- SIZE CAP: 64KB of jsonb, matching api/sd-data.js's uniform MAX_PAYLOAD_BYTES.

create extension if not exists pgcrypto;

create table if not exists public.dnt_recall_outreach (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndental',
  outreach_id  text not null,
  data         jsonb not null default '{}'::jsonb,   -- patient_id, procedure_type_id, on, channel (phone|email|text|mail|in_person), outcome (no_answer|booked|declined|bad_contact|other), note, created_at
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, outreach_id),
  constraint dntrc_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntrc_license on public.dnt_recall_outreach(license_hash);

alter table public.dnt_recall_outreach enable row level security;
drop policy if exists "svc only dnt_recall_outreach" on public.dnt_recall_outreach;
create policy "svc only dnt_recall_outreach" on public.dnt_recall_outreach
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update on public.dnt_recall_outreach to service_role;
