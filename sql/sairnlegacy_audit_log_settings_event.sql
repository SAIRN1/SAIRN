-- sql/sairnlegacy_audit_log_settings_event.sql
-- ---------------------------------------------------------------------------
-- hank b46, 2026-10-21. Adds ONE event_type, 'settings_changed', to the CHECK on
-- public.sairnlegacy_audit_log (sql/sairnlegacy_audit_log_schema.sql), for the
-- owner's F2/F3 settings writes (resource leg_settings, api/sd-data.js).
--
-- The five existing values are restated unchanged. The constraint name is the
-- one Postgres gives an inline column CHECK: <table>_<column>_check.
--
-- NOT RUN. Until it runs, a settings save still succeeds and answers
-- `audited: false`, because the CHECK refuses the row -- the save is never
-- blocked by a logging failure, and the answer does not claim a trail exists.
-- After it runs, a changing save answers `audited: true`.
-- ---------------------------------------------------------------------------

alter table public.sairnlegacy_audit_log
  drop constraint if exists sairnlegacy_audit_log_event_type_check;

alter table public.sairnlegacy_audit_log
  add constraint sairnlegacy_audit_log_event_type_check
  check (event_type in (
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused',
    -- hank b46: an owner's leg_settings write that changed something. detail
    -- carries { resource, first_save, changed: { field: { from, to } } }.
    'settings_changed'
  ));

-- CONFIRM -- expect exactly one row, and its definition lists six values
-- including settings_changed.
select conname, pg_get_constraintdef(oid)
  from pg_constraint
 where conrelid = 'public.sairnlegacy_audit_log'::regclass
   and conname = 'sairnlegacy_audit_log_event_type_check';
