-- sql/sairnfreedom_demo_owner_credential_2026-10-13.sql
-- ---------------------------------------------------------------------------
-- ONE DEMO SIGN-IN FOR SAIRNfreedom, so the app can be driven instead of
-- read. Written 2026-10-13 (hank b7).
--
-- WHY IT DID NOT EXIST AND WHAT THAT COST, MEASURED RATHER THAN ASSERTED.
-- docs/2026-09-03-demo-credentials.md carries a row for every app with a demo
-- employee credential and had NO SAIRNfreedom row, so there was no PIN for this
-- app anywhere in the repo. The consequence is on the record twice in one week:
--
--   * b6 locked five sf_* tables behind the session gate and built a 10-role x
--     36-resource policy matrix, and every one of those claims is
--     SOURCE-VERIFIED ONLY -- no session was ever driven against the live app,
--     because no session could be.
--   * the same batch drove SAIRNscape's gates in BOTH directions with
--     SCP-DEMO-2026 and found the half that source review cannot reach: a
--     session-bearing write answering 400 FROM THE HANDLER, which is what
--     proves the session passed the gate rather than the gate being absent.
--
-- The pattern this file follows is sql/demo_owner_credentials_2026-09-03.sql,
-- which exists because two production bugs on 2026-09-03 were found ONLY
-- because one licence happened to have a documented PIN -- both behind a full
-- green suite, neither findable without signing in.
--
-- ── THE PIN IS PUBLISHED, ON PURPOSE, AND THE PRECONDITION IS THE BASIS ────
-- Same trade the sibling file states plainly: a credential nobody can find is a
-- credential nobody uses. SF-PINNACLE-2026 is a DEMO licence
-- (`demo@pinnaclepost.example`, plan `demo`, seeded by
-- sql/sairnfreedom_license_seed.sql) and holds no real post's data. THE MOMENT
-- THIS LICENCE IS GIVEN TO A REAL POST OR LOADED WITH REAL MEMBER, LEDGER OR
-- ORC 2915 GAMING DATA, THIS ROW MUST BE DELETED AND THE PIN ROTATED. That is
-- not a style note: a VFW post's ledger and disbursement records are exactly
-- the material the sf_* locks exist to protect.
--
-- ── THE HASHES ARE REAL AND WERE ROUND-TRIPPED BEFORE BEING WRITTEN ────────
-- pin_hash / pin_salt were produced by the platform's OWN hashPin()
-- (api/_lib/auth.js -- scrypt, 64-byte derived key, 16-byte random salt) and
-- then passed back through its OWN verifyPin(): the correct PIN returns true
-- and a wrong PIN returns false. So this row is indistinguishable from one the
-- API created, and that claim rests on a check rather than on the shape of the
-- SQL. license_hash is hashLicense('SF-PINNACLE-2026') from
-- api/_lib/license.js, computed, never typed.
--
-- THE SAME ROUND TRIP WAS THEN RE-RUN AGAINST THE LITERALS AS THEY APPEAR IN
-- THIS FILE, not against the variables that produced them -- a transcription
-- error between the generator and the file would otherwise be invisible, and it
-- would present as 401 INVALID_CREDENTIALS with correct-looking SQL.
--
-- ── THE ROLE IS post.govern, READ OFF THE APP ──────────────────────────────
-- api/sf-auth.js: PROVISIONING_ROLES = ['post.govern', 'post.govern.deputy'],
-- SOLE_ROLE = 'post.govern'. There is NO `owner` role in this app, so a file
-- copied from a sibling without re-reading would insert a role the CHECK
-- constraint rejects. This is the trap CLAUDE.md names for SAIRNcode (`admin`,
-- not `owner`) arriving in a different app.
--
-- post.govern is deliberately the SOLE role: it is what `bootstrap` mints and
-- what the last-provisioner refusal in set_active keys on, so this credential
-- can both provision others and exercise the deactivation lifecycle.
--
-- ── WHAT IT DOES NOT DO ────────────────────────────────────────────────────
-- It deletes nothing and deactivates nothing. If the licence already has a
-- bootstrapped post.govern account from an earlier session, that account keeps
-- working; this adds one more. Adding an active provisioner also makes the
-- licence SAFER against the deactivate-to-zero trapdoor, never less safe.
--
-- ── PRECONDITION: THE LICENCE ROW MUST EXIST FIRST ─────────────────────────
-- `sql/sairnfreedom_license_seed.sql` inserts SF-PINNACLE-2026 into
-- license_keys. Whether it has been run COULD NOT BE TOLD FROM A CLONE. This
-- file does not depend on it to INSERT -- the employee_auth table is scoped by
-- license_hash and does not reference license_keys -- but /api/sf-auth will
-- refuse the login with an invalid-licence error until that row exists, and the
-- failure would look like a bad PIN. Run the licence seed first, or run the
-- confirm step at the bottom which tells the two apart.
-- ---------------------------------------------------------------------------

-- ONE TRANSACTION. The insert and the guard land together or not at all: a
-- guard that cannot roll back what it just objected to is a notice, not a
-- guard, and tools/employee_auth_guard_check.py refuses the file without one.
begin;

-- sairnfreedom  --  SF-PINNACLE-2026  --  PIN 64927108
insert into public.sairnfreedom_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '78a8517ee72db892008b29f116109b9cb2f03dcfef648a1a0bbc03df61b9045a',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'post.govern',
  'e845f935acf7c8cba1ef26db719830c84827e94a9dfae9b4904f1511f9051903578f40c20cc73f0b8e4a66d652fdd1ad4e57c50c8edf8a637d87bc1738341d4d',
  '31e985cf3708d5d90e874ed1b2ea7a82',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- ── RECOVERABILITY GUARD ───────────────────────────────────────────────────
-- Required by CLAUDE.md of any SQL that writes credential rows, and enforced by
-- tools/employee_auth_guard_check.py as check 2 of the push hook. A licence with
-- credential rows and ZERO rows that are both `active` and hold a provisioning
-- role is UNRECOVERABLE THROUGH THE API: `bootstrap` refuses 409 while any row
-- exists, and `setup` and `set_active` both need an active provisioner.
-- RF-PINNACLE-2026 sat in that state and nothing noticed.
--
-- THIS FILE ONLY ADDS AN ACTIVE PROVISIONER, so it cannot create that state --
-- which is exactly why the guard should PASS rather than be skipped. A guard
-- that is only written when somebody fears it will fail is not a guard.
--
-- THE ROLE ARRAY IS THIS APP'S OWN: post.govern and post.govern.deputy, from
-- api/sf-auth.js's PROVISIONING_ROLES. An array hardcoding 'owner' would pass
-- SAIRNfreedom clean forever while checking nothing, because no row can ever
-- hold that role here.
do $$
declare
  lh   text;
  rows int;
  prov int;
begin
  lh := encode(digest('SF-PINNACLE-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sairnfreedom_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairnfreedom_employee_auth
   where license_hash = lh and active = true
     and role = any (array['post.govern','post.govern.deputy']);
  if rows > 0 and prov = 0 then
    -- THE MARKER IS ON ONE LINE DELIBERATELY. tools/employee_auth_guard_check.py
    -- matches the contiguous string "ZERO active provisioners" in CODE, and a
    -- message wrapped between "ZERO" and "active" is invisible to it -- that
    -- exact wrap made it refuse a correct file on 2026-09-29, and it refused
    -- this one on first write for the same reason.
    raise exception
      'ABORTED: SF-PINNACLE-2026 would be left with credential rows and ZERO active provisioners (% row(s)). '
      'Delete EVERY row for this licence, or leave at least one active '
      'provisioner. Never a subset of the provisioners.', rows;
  end if;
  raise notice 'SF-PINNACLE-2026: % row(s), % active provisioner(s).', rows, prov;
  -- AND THE HASH MUST MATCH THE ONE THIS FILE JUST WROTE. Without this, a
  -- pre-existing `sairn-demo-owner` row whose ON CONFLICT update silently did
  -- not apply would leave the documented PIN wrong and the guard green.
  if not exists (
    select 1 from public.sairnfreedom_employee_auth
     where license_hash = lh and employee_id = 'sairn-demo-owner'
       and role = 'post.govern' and active = true
       and pin_salt = '31e985cf3708d5d90e874ed1b2ea7a82') then
    raise exception
      'ABORTED: the sairn-demo-owner row does not carry the PIN salt this file '
      'wrote, so the PIN documented in docs/2026-09-03-demo-credentials.md '
      'would not work. Nothing has been committed.';
  end if;
  raise notice 'Guard passed: the demo credential is present and is the one documented.';
end $$;

commit;

-- ── CONFIRM IT LANDED ──────────────────────────────────────────────────────
-- Run these SEPARATELY, not as one paste with the above. The Supabase editor
-- reports success for the statements it did run, so a partial apply looks
-- identical to a full one -- the failure the SAIRNroofing cleanup actually hit
-- on 2026-08-26.

-- 1. The row exists, with the right role, and is active. Expect exactly 1 row:
--    sairn-demo-owner | post.govern | t
select employee_id, role, active
  from public.sairnfreedom_employee_auth
 where license_hash = encode(digest('SF-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id = 'sairn-demo-owner';

-- 2. The licence row this credential signs in under exists. Expect 1 row,
--    status `active`, app_id `sairnfreedom`. ZERO ROWS means
--    sql/sairnfreedom_license_seed.sql has not been run and the login below
--    will fail for that reason rather than for a bad PIN -- which is the one
--    confusion this query exists to prevent.
select key, status, app_id, plan
  from public.license_keys
 where key = 'SF-PINNACLE-2026';

-- 3. THEN THROUGH THE DEPLOYED API, WHICH IS THE ONLY REAL PROOF. A clean
--    insert is not evidence the app accepts it -- that is the whole lesson of
--    the 2026-09-03 probe, where a licence with a perfectly good row answered
--    401 because the PIN, not the key, had died.
--
--      curl -s -X POST https://sairn.vercel.app/api/sf-auth \
--        -H 'Content-Type: application/json' \
--        -H 'Authorization: Bearer SF-PINNACLE-2026' \
--        -d '{"action":"login","employee_id":"sairn-demo-owner","pin":"64927108"}'
--
--    200 with role "post.govern" and a token -> this file has been run
--    401 INVALID_CREDENTIALS                 -> it has not, or the PIN differs
--    an invalid-licence refusal               -> the LICENCE SEED has not been
--                                                run; query 2 tells you which
--
-- 4. AND THEN DRIVE A GATED TABLE IN BOTH DIRECTIONS, because that is the half
--    source review cannot reach. With the token from step 3, a read of
--    `sf_officers` must answer 200; the same request with NO token must answer
--    403. One of those alone proves nothing -- a gate that refuses everybody
--    passes every negative arm, and a gate that is absent passes every positive
--    one.
