-- sql/sairnroofing_verify_admin_seed.sql
-- DISPOSABLE test admin for the Phase 3a live round trip. NOT RUN by this
-- session (no DB access). Run once in the Supabase SQL editor, then tell the
-- session to proceed; the cleanup delete at the bottom removes it afterward.
--
-- WHY THIS FILE INSTEAD OF action:bootstrap OR action:setup:
--   - bootstrap is refused (409 ALREADY_PROVISIONED): the RF-PINNACLE-2026
--     licence already has an owner ('owner'), created when Phases 1-2 were
--     verified. bootstrap deliberately cannot re-run on a provisioned licence
--     -- that anti-seizure rule is correct and must not be worked around.
--   - setup needs an EXISTING owner session, and this session does not hold the
--     'owner' PIN (it was set live during Phase 1-2 verification and, correctly,
--     never written to any committed file).
-- The bootstrap code's own comment names this exact path: "Recovery goes
-- through another owner, or a scoped SQL reset." This is that scoped reset,
-- narrowed to a single disposable row.
--
-- The credential below is a THROWAWAY for verification only:
--   employee_id : rf-verify-admin
--   role        : admin   (management -- can write rules and record credentials)
--   PIN         : 481502
-- The PIN hash was computed with the app's own hashPin() (scrypt, 64-byte,
-- per-credential salt -- api/_lib/auth.js), so login/verifyPin accept it with
-- no code change. license_hash is sha256('RF-PINNACLE-2026').
--
-- It is scoped so it can never collide with the real 'owner' account or any
-- crew row, and the cleanup targets it by exact employee_id.

insert into public.sairnroofing_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b',
  'rf-verify-admin',
  'RF Verify Admin (disposable)',
  'admin',
  'f10259e0314f5d4e9c9193ba6d12ec7f6bf7f946c3cc468d28f9a367f6e9c92777b3442324df070613469c4ac3b7ce0a5032ab9904873ad9da2b803eb57f1e09',
  'de0ce521b0f4c825a5ed93a43050c76e',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- Confirm it landed (expect one row, role = admin, active = t):
--   select employee_id, role, active from public.sairnroofing_employee_auth
--    where employee_id = 'rf-verify-admin';

-- ── CLEANUP, run after the round trip is reported ────────────────────────
-- The employee_auth table has no delete verb through the API by design, so
-- this row is removed the same way it was created -- directly.
--   delete from public.sairnroofing_employee_auth
--    where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
--      and employee_id  = 'rf-verify-admin';
--
-- The rf_certifications rows this admin writes during the round trip are
-- append-only and likewise need a scoped SQL delete -- that cleanup file is
-- written after the run, once the exact entry_ids are known, the same way the
-- SAIRNdental DCRED-VERIFY rows were handled.
