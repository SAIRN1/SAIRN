-- sql/sairncode_audit_log_credential_events.sql
-- Allow the credential-lifecycle event types in sairncode_audit_log.
--
-- ⚠ NOT YET RUN. Flagged for Michael.
--
-- WHY THIS IS NEEDED, and how it was found: api/sc-auth.js's new set_active
-- action writes three event types that the table's CHECK constraint does not
-- allow -- credential_deactivated, credential_reactivated and
-- credential_change_refused. The table was created 2026-08-20 for the AI
-- audit log and its CHECK lists only the four ai_* events, deliberately
-- narrow so a future caller could not invent an event name.
--
-- CAUGHT LIVE, NOT BY READING: every real set_active call on SC-PINNACLE-2026
-- returned audited:false. The action itself worked correctly every time --
-- per api/_lib/audit.js's contract a failed log write never blocks the
-- action -- but nothing was being recorded. This is exactly why that flag is
-- returned to the caller rather than swallowed: a silent audit failure on a
-- CREDENTIAL change is the kind of gap you only discover when you need the
-- log and it is empty.
--
-- Until this runs, credential changes on SAIRNcode succeed and honestly
-- report audited:false. After it runs they report audited:true and the
-- entries appear in sairncode_audit_log.

alter table sairncode_audit_log
  drop constraint if exists sairncode_audit_log_event_type_check;

alter table sairncode_audit_log
  add constraint sairncode_audit_log_event_type_check
  check (event_type in (
    -- AI audit log (2026-08-20, firewall audit layer 30) -- unchanged.
    'ai_call',
    'ai_call_blocked',
    'ai_injection_flagged',
    'ai_call_failed',
    -- Credential lifecycle (2026-08-23, api/sc-auth.js set_active).
    -- 'credential_change_refused' covers every refusal path -- SELF_DEACTIVATE,
    -- CREDENTIAL_INACTIVE and the quarantined LAST_ADMIN guard -- with the
    -- specific reason_code in detail. A refused attempt to remove someone's
    -- access is worth recording precisely because it did not happen.
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  ));

-- The list stays explicit rather than becoming free text: an open column
-- would let any future caller invent an event name and quietly change what
-- this log means. Adding a value should keep costing a reviewable migration.
--
-- Nothing else about the table changes -- same immutability posture, same
-- grants (select + insert to service_role only), same RLS. This alters the
-- CHECK constraint and nothing more.
--
-- Verify after running (expect the three new values to be accepted and a
-- bogus one rejected):
--   select conname from pg_constraint
--    where conrelid = 'sairncode_audit_log'::regclass and contype = 'c';
-- Then confirm end to end from the app: run a real set_active as a
-- Compliance Admin and check the response carries "audited": true.
