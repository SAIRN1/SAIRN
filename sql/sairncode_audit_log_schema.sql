-- sql/sairncode_audit_log_schema.sql
-- SAIRNcode immutable AI audit log — Supabase schema.
-- Run this once in the Supabase SQL editor before api/sc-ai.js will log.
--
-- WHY THIS EXISTS: the 2026-08-20 audit of the 30-layer Universal Security
-- Firewall spec found layer 30 (local audit log of every AI call) genuinely
-- missing from SAIRNcode. That matters more here than the layer's placement
-- on a checklist suggests: SAIRNcode sends real clinical notes (PHI) to a
-- third-party LLM and, before this table, kept no record that it had done so.
--
-- Modelled directly on sql/sairnlaw_audit_log_schema.sql, which is the proven
-- pattern on this platform. Same immutability guarantee, same reasoning.
--
-- HONEST SCOPE, stated rather than implied: this logs AI calls that actually
-- cross the server boundary through api/sc-ai.js. It is a record that a call
-- happened, by whom, and what was screened — NOT a copy of the clinical note.
-- See the "deliberately not stored" note below.
--
-- IMMUTABLE BY DESIGN, enforced at the DATABASE level. service_role (the only
-- role that ever reaches this table) is granted SELECT and INSERT and nothing
-- else, so an UPDATE or DELETE fails with a Postgres permission error even if
-- code is later written that attempts one. Per the correction already recorded
-- in SAIRNlaw's schema header: service_role BYPASSES RLS, so the RLS policy
-- below is NOT what enforces immutability — the grants are. RLS is kept only
-- as a second layer against anon/authenticated, which have no grants at all.

create table if not exists sairncode_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text,
  role text,
  event_type text not null check (event_type in (
    'ai_call',
    'ai_call_blocked',
    'ai_injection_flagged',
    'ai_call_failed'
  )),
  detail jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_sairncode_audit_log_license_time
  on sairncode_audit_log (license_hash, created_at desc);

-- DELIBERATELY NOT STORED: the clinical note text, the assembled prompt, or
-- the model's response. Logging PHI into an append-only table that can never
-- be corrected or deleted would create a larger, permanent PHI exposure than
-- the one this log exists to make accountable. `detail` carries only
-- non-PHI metadata: which feature made the call, message/character counts,
-- which screening rules fired, and whether the call succeeded.

alter table sairncode_audit_log enable row level security;
drop policy if exists "svc insert only sairncode_audit_log" on sairncode_audit_log;
create policy "svc insert only sairncode_audit_log" on sairncode_audit_log for insert with check (true);

-- THE ACTUAL IMMUTABILITY CONTROL: select + insert only, no update, no delete.
revoke all on sairncode_audit_log from anon, authenticated;
revoke all on sairncode_audit_log from service_role;
grant select, insert on sairncode_audit_log to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sairncode_audit_log;
-- Confirm immutability (both should FAIL with permission denied):
--   update sairncode_audit_log set role = 'x';
--   delete from sairncode_audit_log;
