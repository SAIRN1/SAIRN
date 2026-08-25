-- sql/sairncode_verify_admin_seed.sql
-- DISPOSABLE test admin for SAIRNcode's delete-path verification and the
-- probe-row cleanup that follows it. NOT RUN by this session (no DB access).
-- Run once in the Supabase SQL editor, then tell the session to proceed; the
-- cleanup block at the bottom removes it afterward.
--
-- Deliberately modelled on sql/sairnroofing_verify_admin_seed.sql, which
-- solved the identical problem on RF-PINNACLE-2026. Same shape, same reasons.
--
-- WHY THIS FILE INSTEAD OF action:bootstrap OR action:setup:
--   - bootstrap is refused (409 ALREADY_PROVISIONED, confirmed live
--     2026-08-25): SC-PINNACLE-2026 already carries credentials. The guard at
--     api/sc-auth.js:128 short-circuits before any write, so that probe
--     created nothing. That anti-seizure rule is correct and is not being
--     worked around here -- this adds a row, it does not re-bootstrap.
--   - setup needs an EXISTING admin session (api/sc-auth.js:207), which is
--     circular: obtaining one is the thing being blocked.
--
-- WHY NOT RESET THE EXISTING ADMIN: the license's existing accounts are
-- 'hank-admin' and 'hank-coder' (SAIRN-ACTIVE-WORK-cc.md:52). They may be real
-- and in active use by another session, and their PIN is recorded nowhere on
-- purpose (docs/superpowers/specs/2026-08-20-sairncode-30-layer-firewall-audit
-- .md:173 says so explicitly). Resetting a credential to find out whether it
-- mattered is the wrong order of operations. This file touches neither.
--
-- The credential below is a THROWAWAY for verification only:
--   employee_id : sc-verify-admin
--   role        : admin   (the only role api/sd-data.js accepts for delete)
--   PIN         : 759533
--
-- PROVENANCE OF EVERY VALUE BELOW -- none of it hand-built:
--   pin_hash / pin_salt come from the app's OWN hashPin() (scrypt, 64-byte
--   digest, per-credential 16-byte salt -- api/_lib/auth.js:190), so
--   verifyPin() accepts them with no code change. Self-verified in both
--   directions before this file was written, using the app's own verifyPin():
--       correct PIN   -> true
--       wrong PIN     -> false
--       empty PIN     -> false
--       missing salt  -> false
--   license_hash is sha256('SC-PINNACLE-2026') per api/_lib/license.js:38-39,
--   which applies no trim/case normalisation -- the raw string is hashed.
--   That derivation was VALIDATED against a known-good production value rather
--   than trusted: sha256('RF-PINNACLE-2026') reproduces
--   47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b exactly,
--   the hash already living in sairnroofing_verify_admin_seed.sql and already
--   proven to work against the live login endpoint.
--
-- Scoped so it cannot collide with hank-admin, hank-coder, or any future row:
-- the unique key is (license_hash, employee_id) and 'sc-verify-admin' is new.
-- Adding a SECOND admin is also safe with respect to set_active's last-admin
-- refusal (api/sc-auth.js:388) -- that guard blocks removing the last one, and
-- this only ever adds.

insert into public.sairncode_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  'fce80ce1bc131249e98a7caf1235bc769ce703331775e4ba1c870c65c8a0e9ed',
  'sc-verify-admin',
  'SC Verify Admin (disposable)',
  'admin',
  'ec7e42bc1a1703a5e0139f9ec7e1266fb8c6ef9974f2348f1152286017584f7627f420ef2ddf639106342ec91d6adc5400b522e19f89ced636c6c29ab194d973',
  '24e5bde409865e35bd0dc82b51798b63',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- Confirm it landed (expect exactly one row, role = admin, active = t).
-- The other two rows on this licence must be untouched -- check that too:
--   select employee_id, role, active from public.sairncode_employee_auth
--    where license_hash = 'fce80ce1bc131249e98a7caf1235bc769ce703331775e4ba1c870c65c8a0e9ed'
--    order by employee_id;
--   -- expect: hank-admin, hank-coder, sc-verify-admin

-- ── CLEANUP, run after the delete-path verification is reported ──────────
-- sairncode_employee_auth is granted select/insert/update and NOT delete
-- (sql/sairncode_employee_auth_schema.sql:57), deliberately, so nothing in the
-- API can remove this row. It goes out the same way it came in -- directly, as
-- owner, scoped to the exact employee_id, never by license_hash alone:
--
--   delete from public.sairncode_employee_auth
--    where license_hash = 'fce80ce1bc131249e98a7caf1235bc769ce703331775e4ba1c870c65c8a0e9ed'
--      and employee_id  = 'sc-verify-admin';
--
-- The three sc_* probe rows this admin exists to remove
-- (entry_id 'verify-2026-08-25-*' in sc_pctc, sc_specialty_checks and
-- sc_anesthesia_base_units) go through the API's real delete path instead --
-- exercising that path IS the verification, so they must not be deleted here.
--
-- Separately and NOT covered by this file: the probe emails in
-- sairncash_waitlist. That table is granted select/insert only and its
-- endpoint has no delete action at all, so they need their own scoped SQL
-- delete as owner.
--
-- CORRECTION, counted rather than assumed: this session reported "four test
-- emails" earlier. That is wrong -- only TWO rows exist. Four addresses were
-- POSTed, but the first two hit the 502 this session was diagnosing and never
-- reached the table at all; a refused insert leaves nothing behind. Only the
-- addresses that returned 200 are real rows:
--     fresh-probe-b7f2e91a4c@sairn-verify.test  (502 pre-fix, 200 after)
--     live-confirm-9d4a1f@sairn-verify.test     (200, then 200 again on the
--                                                repeat that proved the
--                                                ON CONFLICT DO NOTHING path)
-- Both never-landed addresses are listed below anyway so the statement is
-- idempotent whichever way the count turns out -- they simply match nothing.
-- Verify before deleting rather than trusting either count:
--   select email, created_at from public.sairncash_waitlist
--    where email like '%sairn-verify%' or email like '%fresh-probe%'
--    order by created_at;
--
--   delete from public.sairncash_waitlist
--    where email in ('sairn-verify-2026-08-25@example.com',
--                    'sairn-verify-2026-08-25b@example.com',
--                    'fresh-probe-b7f2e91a4c@sairn-verify.test',
--                    'live-confirm-9d4a1f@sairn-verify.test');
