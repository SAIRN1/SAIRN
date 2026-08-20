-- sql/sairncode_auth_requests_schema.sql
-- Real server-synced table for SAIRNcode's prior-authorization REQUEST
-- lifecycle (Phase 2a/2b of the 2026-08-20 BYO-credential expansion). Run
-- this once in the Supabase SQL editor before api/sd-data.js's
-- sc_auth_requests read/write/delete branch will work.
--
-- WHY THIS IS A NEW TABLE, NOT AN EXTENSION OF sc_auth (sairncode_data_
-- schema.sql): sc_auth records {authId, proc, exp, units} -- an
-- authorization the practice ALREADY HOLDS, with status derived from its
-- expiration date. It has no payer field and no submission lifecycle. A
-- prior-auth REQUEST is a different object entirely: submitted -> pending
-- -> approved/denied/more-info-needed, with a payer, a submission method, a
-- real regulatory clock, and a human sign-off record. Bolting that onto
-- sc_auth would repeat exactly the mistake the 2026-08-20 denial-pattern
-- work already fixed once (sc_denial had no payer, so sc_denial_events was
-- added alongside it rather than mangling the aggregate table). sc_auth
-- itself is untouched by this migration -- no columns added, no rows
-- migrated.
--
-- WHAT submittedVia CAN AND CANNOT MEAN TODAY: 'Portal', 'Fax', and 'Phone'
-- are real, honest submission methods a coder actually uses. There is no
-- 'FHIR PAS' option -- real automated FHIR Prior Authorization Support
-- submission does not exist in this app (see docs/superpowers/specs/
-- 2026-08-20-sairncode-prior-auth-phase2-design.md's Phase "2c", explicitly
-- deferred pending real payer registrations and a KMS-backed signing key
-- neither of which exist yet). Offering an FHIR option that always fails
-- would be exactly the false-capability class this codebase has spent weeks
-- removing, so it is absent from the UI entirely rather than shown disabled.
--
-- WHAT signedOffBy MEANS: every AI-assembled draft is DRAFT-only and can
-- never itself become "submission-ready" -- a real credentialed admin
-- session must explicitly sign off first. That gate is enforced SERVER-SIDE
-- in api/sd-data.js's sc_auth_requests write branch (mirrors the existing
-- Compliance-Admin delete gate exactly), not merely implied by a client-side
-- checkbox. See that file's own comment for the enforcement code.
--
-- Same generic shape as every other sc_* resource: one row per entry,
-- license_hash-scoped, a jsonb data column. entry_id is the client's own
-- locally-generated id ('ar'+Date.now()).

create table if not exists public.sc_auth_requests (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_auth_requests_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sc_auth_requests_license on public.sc_auth_requests(license_hash);

alter table public.sc_auth_requests enable row level security;
drop policy if exists "svc only sc_auth_requests" on public.sc_auth_requests;
create policy "svc only sc_auth_requests" on public.sc_auth_requests for all using (false) with check (false);

grant select, insert, update, delete on public.sc_auth_requests to service_role;
revoke all on public.sc_auth_requests from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sc_auth_requests;
