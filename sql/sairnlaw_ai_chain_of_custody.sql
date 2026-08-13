-- sql/sairnlaw_ai_chain_of_custody.sql
-- SAIRNlaw AI Chain of Custody (Phase 1) — extends the existing immutable
-- audit log (sql/sairnlaw_audit_log_schema.sql) with 4 new event types,
-- rather than creating a second, parallel audit table. That file's own
-- grant/revoke statements (`grant select, insert ... to service_role;
-- revoke update, delete ... from service_role;`) already govern every row
-- in this table regardless of event_type -- no new grant is needed here.
--
-- Event shapes (all live in the existing jsonb `detail` column):
--   ai_interaction  { prompt, response, matter_id, tools_used: [names] }
--     -- the record of one real sendAI() exchange. employee_id/role (top-
--     -- level columns, already on this table) identify who triggered it.
--   ai_reviewed     { log_entry_id }
--     -- log_entry_id references the id of the ai_interaction row being
--     -- reviewed. employee_id/role identify the reviewer.
--   ai_rejected     { log_entry_id, reason }
--     -- reason is required at the application layer (enforced in
--     -- api/law-auth.js, not by a DB constraint -- this table's `detail`
--     -- column has no per-event-type shape validation, matching every
--     -- other event type already in this table).
--   ai_used_in_filing { log_entry_id }
--     -- the attorney's formal attestation that they verified this output
--     -- before relying on it in a filing. Only ever inserted after a
--     -- prior ai_reviewed event for the same log_entry_id exists --
--     -- enforced server-side (api/law-auth.js), not by a DB constraint.
--
-- An entry's CURRENT status is derived, not stored: the most recent of
-- {ai_reviewed, ai_rejected, ai_used_in_filing} whose detail->>'log_entry_id'
-- matches a given ai_interaction row's id, or 'unreviewed' if none exists.
-- This is a real event-sourcing model, not a mutable status column -- it
-- means the full review history (including a correction, if one is ever
-- needed) is itself part of the immutable record, not overwritten.
--
-- Safe to re-run.

alter table sairnlaw_audit_log drop constraint if exists sairnlaw_audit_log_event_type_check;
alter table sairnlaw_audit_log add constraint sairnlaw_audit_log_event_type_check
  check (event_type in (
    'login_success', 'login_failed', 'lockout',
    'pin_bootstrap', 'pin_setup',
    'mfa_enrolled', 'mfa_verified', 'mfa_failed',
    'sso_login', 'sso_link',
    'citator_lookup',
    'ai_interaction', 'ai_reviewed', 'ai_rejected', 'ai_used_in_filing'
  ));

-- Query pattern this feature relies on (ai_list, api/law-auth.js): fetching
-- all ai_interaction rows plus all status-event rows for a license, most
-- recent status event per log_entry_id wins. No new index is added this
-- pass -- (license_hash, created_at desc) already exists from the base
-- schema and is sufficient at expected single-firm volume; add a
-- dedicated index on detail->>'log_entry_id' if this becomes a real
-- bottleneck, not preemptively.
