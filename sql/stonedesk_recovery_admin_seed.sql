-- sql/stonedesk_recovery_admin_seed.sql
-- A PERSISTENT StoneDesk verification credential. Not a disposable one.
--
-- ── WHY THIS IS DIFFERENT FROM THE FOUR SEEDS SHIPPED 2026-08-28/29 ──────
-- sql/stonedesk_verify_admin_seed.sql and its siblings for SAIRNroofing,
-- SAIRNmechanical, SAIRNdental and SAIRNcode all end with the same
-- instruction: DELETE the account when the verification is done, because the
-- PIN is published in the file. That is correct for those files and it is
-- exactly why the problem keeps coming back.
--
-- The loop, observed twice in two days: a session needs to verify something
-- against a live StoneDesk licence -> no credential exists -> a disposable
-- admin is seeded -> the work is verified -> the cleanup deletes it -> the
-- NEXT session needs a credential and there is none. On 2026-08-30 that loop
-- cost a live check of the new HR storage: `sd-verify-admin` returned
-- INVALID_CREDENTIALS because the 2026-08-28 cleanup had removed it, exactly
-- as designed, and `provisioned:true` went unconfirmed for want of any way to
-- sign in. api/sd-auth.js:304-308 already records the older, worse version of
-- this: three StoneDesk licences lost to untracked credential state.
--
-- ── THE FIX IS THE LICENCE, NOT THE PIN ─────────────────────────────────
-- A published PIN cannot safely persist on SD-PINNACLE-2026. That licence
-- holds REAL accounts -- `cmonsul` (Carolyn Monsul, a named person), `owner`
-- (Michael Dibert), and `hank-test` (another session's) -- confirmed in
-- sql/stonedesk_access_panel_verify_cleanup_2026-08-28.sql. Leaving a
-- repo-published admin PIN alongside those is not acceptable at any
-- convenience.
--
-- So this seeds a different licence. SD-AUDIT-2026 exists for precisely this
-- purpose -- sql/stonedesk_audit_license_seed.sql created it as "a second,
-- clean StoneDesk license dedicated to this kind of automated testing" --
-- and it is the one place a standing, publicly-known credential costs
-- nothing.
--
--   sha256('SD-AUDIT-2026')
--     = 8f1610119858d53f7deee8f975adf501b0ed1ee6dd57c674399743da7d6b76ea
--
-- Derivation method matches api/_lib/license.js:39 exactly
-- (`crypto.createHash('sha256').update(key).digest('hex')`), and is the same
-- method that produced the already-proven hash in
-- sql/stonedesk_verify_admin_seed.sql.
--
-- ── PRECONDITION, AND IT IS NOT OPTIONAL ────────────────────────────────
-- This is safe ONLY while SD-AUDIT-2026 holds no real business data. Anyone
-- reading this public repo can sign in to that licence. Confirm before
-- running, and treat a non-empty result as a reason to stop and reconsider
-- rather than a formality:
--
--   select 'jobs' src, count(*) from public.sd_jobs
--     where license_hash = '8f1610119858d53f7deee8f975adf501b0ed1ee6dd57c674399743da7d6b76ea'
--   union all select 'crm', count(*) from public.sd_crm
--     where license_hash = '8f1610119858d53f7deee8f975adf501b0ed1ee6dd57c674399743da7d6b76ea'
--   union all select 'slabs', count(*) from public.sd_slabs
--     where license_hash = '8f1610119858d53f7deee8f975adf501b0ed1ee6dd57c674399743da7d6b76ea';
--   -- expect 0 / 0 / 0. Any non-zero: STOP, this licence is in real use.
--
-- SD-AUDIT-2026 MUST NEVER BE GIVEN TO A CUSTOMER OR HOLD REAL DATA while
-- this row exists. That is the whole trade being made here, stated plainly.
--
-- ── THE CREDENTIAL ──────────────────────────────────────────────────────
--   licence     : SD-AUDIT-2026
--   employee_id : sd-recovery-admin
--   role        : admin
--   PIN         : 40318627
--
-- pin_hash/pin_salt were produced by the app's OWN hashPin() from
-- api/_lib/auth.js:211 (scrypt, 64-byte, 16-byte random salt) and then round-
-- tripped through the app's OWN verifyPin() before being written here:
-- correct PIN -> true, wrong PIN -> false. So this row is indistinguishable
-- from one the API created, and that claim rests on a check rather than on
-- the shape of the SQL.
--
-- ── ROLE: admin, NOT owner. SAME REASONING AS THE DISPOSABLE SEEDS. ─────
-- StoneDesk is the only app with two provisioning roles
-- (PROVISIONING_ROLES = ['owner','admin']), so an `admin` can exercise
-- roster, setup and set_active fully -- everything a verification needs. It
-- CANNOT mint an Owner: api/sd-auth.js refuses that specifically ("Only an
-- existing Owner can grant Owner access"). Lower of the two capable roles,
-- at no cost to the test.
--
-- ── IDEMPOTENT, AND SCOPED TO ONE ROW ───────────────────────────────────
-- The unique key is (license_hash, employee_id). 'sd-recovery-admin' is a NEW
-- id, absent from every SQL file in this repo, so re-running can only ever
-- touch this row and never a pre-existing credential on that licence. Adding
-- a provisioning-role account also makes the licence SAFER with respect to
-- set_active's last-admin guard, which blocks removing the last one and is
-- unaffected by adding.

-- ── TRANSACTION AND RECOVERABILITY GUARD, ADDED 2026-09-11 ──────────────
-- This file shipped UNGUARDED and was the only one of 228 SQL files that
-- tools/employee_auth_guard_check.py refuses: "no guard, no transaction (a
-- guard here could not roll back)". It was never grandfathered, because it is
-- not old enough to be -- the guard tool and push-gate check 2 both landed in
-- 4cada6a7 on 2026-08-29 and this file landed in bfd47c91 on 2026-08-30 05:01,
-- a day later, and nothing stopped it.
--
-- WHAT LET IT THROUGH CANNOT BE DETERMINED RETROACTIVELY and is not asserted
-- here. The push gate's own comments record that prepush mode was silently
-- failing open on an UnboundLocalError until 2026-09-01, which is the likeliest
-- explanation; SAIRN_SEED_GATE=off and the unresolvable-base fail-open closed in
-- d12ed127 are both candidates. It was found by that fix: widening an
-- unresolvable base from [] to the real range put this file in front of the
-- guard for the first time.
--
-- THE GUARD CANNOT REFUSE WHAT THIS FILE DOES, and that is worth stating rather
-- than discovering. The insert below ADDS an active `admin`, and StoneDesk's
-- PROVISIONING_ROLES is ['owner','admin'] -- read from api/sd-auth.js:46, not
-- from the comment above -- so this file can only ever raise the active
-- provisioner count. The guard exists for the opposite shape: a writer that
-- leaves credential rows behind with zero active provisioners, which is
-- unrecoverable through the API because bootstrap refuses 409 while any row
-- exists and both setup and set_active need an active provisioner.
--
-- THE ROLE ARRAY IS PER APP. A guard hardcoding `owner` would pass SAIRNcode
-- clean forever while checking nothing; StoneDesk genuinely has both.
--
-- Re-running remains safe and idempotent exactly as the header describes --
-- begin/commit changes nothing about the single upsert, it only gives the guard
-- something to roll back.
begin;

insert into public.sd_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '8f1610119858d53f7deee8f975adf501b0ed1ee6dd57c674399743da7d6b76ea',
  'sd-recovery-admin',
  'StoneDesk Recovery Admin',
  'admin',
  '252ad75c2353a47ad945644695f7c2e285223d95c92f1f9e2ae230c239bafb345d5f452a2d42932ce96d53809dc9e8790f5fc10d98dbba7fe6f20eb3e61f913d',
  '6db79d4327a0894f2dd5bd98525a3710',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- Run LAST, inside the transaction, so a refusal rolls the insert back.
do $$
declare
  lh   text;
  rows int;
  prov int;
begin
  lh := encode(digest('SD-AUDIT-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sd_employee_auth where license_hash = lh;
  select count(*) into prov from public.sd_employee_auth
   where license_hash = lh and active = true and role = any (array['owner','admin']);
  if rows > 0 and prov = 0 then
    raise exception
      'ABORTED: SD-AUDIT-2026 would be left with % credential row(s) and ZERO active provisioners. '
      'Delete EVERY row for this licence, or leave at least one active '
      'provisioner. Never a subset of the provisioners.', rows;
  end if;
  raise notice 'SD-AUDIT-2026: % row(s), % active provisioner(s).', rows, prov;
end $$;

commit;

-- ── CONFIRM IT LANDED ───────────────────────────────────────────────────
-- Run these SEPARATELY, not as one paste -- the Supabase editor reports
-- success for the statements it did run, so a partial apply looks identical
-- to a full one (SAIRNroofing cleanup, 2026-08-26).
--
-- 1. Exactly one row for this id, role admin, active t -- and every
--    pre-existing row on this licence still present:
--      select employee_id, role, active from public.sd_employee_auth
--       where license_hash = '8f1610119858d53f7deee8f975adf501b0ed1ee6dd57c674399743da7d6b76ea'
--       order by employee_id;
--
-- 2. Then through the DEPLOYED API, which is the only real proof -- a clean
--    insert is not evidence the app accepts it:
--      curl -s -X POST https://sairn.vercel.app/api/sd-auth \
--        -H 'Content-Type: application/json' \
--        -H 'Authorization: Bearer SD-AUDIT-2026' \
--        -d '{"action":"login","employee_id":"sd-recovery-admin","pin":"40318627"}'
--    Expect 200 with role "admin" and a token.
--
-- 3. That token then closes the check that prompted this file:
--      curl -s -X POST https://sairn.vercel.app/api/sd-data \
--        -H 'Content-Type: application/json' \
--        -H 'Authorization: Bearer SD-AUDIT-2026' \
--        -H 'X-SD-Auth: <token from step 2>' \
--        -d '{"action":"read","resource":"sd_hr_employees"}'
--    200 {"ok":true,"data":[],"provisioned":true}  -> sd_hr_schema.sql is live
--    200 ... "provisioned":false                   -> it has not been run
--
-- ── NO TEARDOWN. DELIBERATELY. ──────────────────────────────────────────
-- This is the one seed in this directory with no cleanup file, and that is
-- the point of it. Deleting it recreates the gap it exists to close. If it
-- ever needs to go, DEACTIVATE rather than delete only if another active
-- owner/admin remains on SD-AUDIT-2026 -- deactivating to zero is the exact
-- lockout found live on RF-PINNACLE-2026.
