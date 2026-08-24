-- sql/sairnroofing_verify_foremen_seed.sql
-- Two disposable FOREMAN accounts for the Phase 3b assignment-gate live test.
-- NOT RUN by this session. Run once in the Supabase SQL editor.
--
-- WHY THIS IS NEEDED: the 3b round trip must prove the narrow-role gate live --
-- "an assigned foreman can edit their own claim, a different foreman is 403'd".
-- rf-verify-admin (the 3a disposable) is role 'admin', which is management and
-- sees everything, so it cannot exercise the narrow path. Two real foreman
-- sessions are required, and only role 'owner' may provision through the API
-- (PROVISIONING_ROLES = ['owner']); rf-verify-admin cannot. So this is the same
-- scoped-SQL path as the admin seed.
--
-- Both PINs were hashed with the app's own hashPin() (scrypt, 64-byte,
-- per-credential salt) and self-verified against verifyPin before committing:
--   rf-verify-fmA  role foreman  PIN 311501
--   rf-verify-fmB  role foreman  PIN 311502
-- license_hash is sha256('RF-PINNACLE-2026').

insert into public.sairnroofing_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values
  ('47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b',
   'rf-verify-fmA', 'RF Verify Foreman A (disposable)', 'foreman',
   'fbfc0ec56691501a8632b18f841917b008c4c8c55286fead82964ee4801211cf150eadabe977b9ade2df6f42c333725c3431f5acad846da29f97b54e877f4b49',
   '0d7ebfff92a2b911978a39919054baf6', true),
  ('47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b',
   'rf-verify-fmB', 'RF Verify Foreman B (disposable)', 'foreman',
   '8cd4e58a3883e189ed7beb890757dda947a5ee3317e253f240aa7a67b4fda1e85a1e24b7b3e3d31bb730eabd266bd87b4d6ccc2a37ed09bcf8a5b45e3a575cbb',
   'c7a7d3b35ed919ce67b50abbad553532', true)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash, pin_salt = excluded.pin_salt,
      role = excluded.role, active = true;

-- Confirm (expect two rows, role = foreman, active = t):
--   select employee_id, role, active from public.sairnroofing_employee_auth
--    where employee_id in ('rf-verify-fmA','rf-verify-fmB');

-- ── CLEANUP, after the round trip is reported ────────────────────────────
--   delete from public.sairnroofing_employee_auth
--    where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
--      and employee_id in ('rf-verify-fmA','rf-verify-fmB');
