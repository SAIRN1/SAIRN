-- sql/sd_encryption_key_revoke_2026-09-24.sql
--
-- STEP 3 OF THE SD_ENCRYPTION_KEY REVOKE PROCEDURE.
-- Read docs/2026-09-24-sd-encryption-key-revoke.md first. Running this file on
-- its own, without steps 1 and 2, turns two-factor OFF for every attorney and
-- buys nothing.
--
-- ── WHAT THIS EXISTS TO BREAK ─────────────────────────────────────────────
-- Rotating SD_ENCRYPTION_KEY makes every v2 ciphertext undecryptable. That is
-- the POINT -- it is what a revoke means when the thing leaked is the key --
-- and both readers already fail closed and say so (law-auth.js:384 answers
-- 500 MFA_UNAVAILABLE, sc-eligibility.js:191 answers 503
-- CREDENTIAL_UNREADABLE). Neither ever skips the check.
--
-- BUT IT LEAVES A DEADLOCK THAT THE API CANNOT RESOLVE, and this file is the
-- only way out of it:
--
--   * `mfa_verify` cannot pass, so nobody with mfa_enabled completes a login.
--   * `mfa_setup` refuses with 409 MFA_ALREADY_ENABLED while mfa_enabled is
--     true (api/law-auth.js:421), so an attorney cannot re-enroll themselves.
--   * `mfa_reset` requires an OWNER SESSION -- and the Owner's own MFA is
--     equally broken, so no Owner session can be obtained.
--
-- Every route out of the state runs through a session that the state prevents.
-- A direct write is not a shortcut here; it is the only door.
--
-- ── THE RECOVERABILITY GUARD: TWO END STATES ARE SAFE, AND ONLY TWO ───────
--   SAFE  mfa_enabled = true  AND a secret that decrypts
--   SAFE  mfa_enabled = false AND the secret cleared -- MFA is off, the
--         security panel says so, and the user can re-enroll
--   UNSAFE mfa_enabled = true AND an undecryptable secret -- the lockout
--         above. This is where a key rotation leaves everyone.
--
-- This file moves rows from the unsafe state to the SECOND safe one. It does
-- NOT create a bypass: MFA genuinely is off for those accounts until each one
-- re-enrolls, which is visible rather than silent, and that is the trade a
-- revoke costs.
--
-- IT CANNOT REACH A ZERO-ACTIVE-PROVISIONER STATE: `active` and `role` are not
-- touched, only `mfa_enabled` and `mfa_secret_encrypted`.
--
-- ── SCOPE IT, DO NOT RUN IT WIDE ──────────────────────────────────────────
-- Replace :LICENSE_HASH. Running this without a WHERE on license_hash resets
-- two-factor for every firm on the platform, not the one that had an incident.

begin;

-- 1. WHAT WOULD CHANGE, READ BEFORE CHANGING IT. Expect a count you recognise
--    as "the attorneys at this firm with MFA on". A surprise here means the
--    hash is wrong; stop and do not continue the transaction.
select count(*) as will_be_reset
from public.sairnlaw_employee_auth
where license_hash = :'LICENSE_HASH'
  and mfa_enabled is true;

-- 2. The reset itself. The secret is CLEARED rather than left in place: a
--    ciphertext nobody can read is not evidence of anything, and leaving it
--    behind means the next person cannot tell a reset account from a
--    half-migrated one.
update public.sairnlaw_employee_auth
   set mfa_enabled = false,
       mfa_secret_encrypted = null
 where license_hash = :'LICENSE_HASH'
   and mfa_enabled is true;

-- 3. CONFIRM QUERIES, one per statement, with the expected answer beside it.
--    The Supabase SQL editor reports success for the statements it DID run, so
--    a partial apply is indistinguishable from a full one from the outside --
--    ask for these counts back rather than accepting "it ran".
select count(*) as still_enabled       -- expect 0
from public.sairnlaw_employee_auth
where license_hash = :'LICENSE_HASH' and mfa_enabled is true;

select count(*) as orphan_ciphertext   -- expect 0
from public.sairnlaw_employee_auth
where license_hash = :'LICENSE_HASH' and mfa_secret_encrypted is not null;

select count(*) as still_active        -- expect the SAME number as before
from public.sairnlaw_employee_auth     -- this file must not deactivate anyone
where license_hash = :'LICENSE_HASH' and active is true;

-- 4. THE RECOVERABILITY GUARD, MECHANICALLY RATHER THAN IN PROSE.
--    The header argues this file cannot reach the zero-active-provisioner
--    state, because it touches only mfa_enabled and mfa_secret_encrypted. That
--    argument is right and it is NOT CHECKABLE -- which is the whole reason the
--    push gate demands the block rather than a sentence. Here it is a POSITIVE
--    ASSERTION: it should pass trivially, and if it ever raises, this file did
--    something its own header says it cannot.
--
--    SAIRNlaw's PROVISIONING_ROLES is ['owner'] (api/law-auth.js:129) -- read
--    out of the app rather than assumed, because SAIRNcode's is `admin` and a
--    copied `owner` there would guard nothing.
do $$
declare
  lh   text := :'LICENSE_HASH';
  rows int; prov int;
begin
  select count(*) into rows from public.sairnlaw_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairnlaw_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);
  if rows > 0 and prov = 0 then
    raise exception
      'ABORTED: would leave % credential row(s) and ZERO active provisioners. '
      'Delete EVERY row for this licence, or leave at least one active '
      'provisioner. Never a subset of the provisioners.', rows;
  end if;
  raise notice 'Guard passed: % row(s), % active provisioner(s).', rows, prov;
end $$;

commit;

-- ── THE OTHER CIPHERTEXT IS NOT HERE, DELIBERATELY ───────────────────────
-- The stored Stedi API key lives in `sc_credentials.data->>'enc'` and needs no
-- SQL: it is rotated AT STEDI and re-entered through
-- api/sc-credentials.js, which encrypts it with whatever key is current. A row
-- holding an undecryptable `enc` answers 503 CREDENTIAL_UNREADABLE and blocks
-- nothing else, so there is no deadlock to break on that side. Deleting the
-- row would work equally well and is not required.
