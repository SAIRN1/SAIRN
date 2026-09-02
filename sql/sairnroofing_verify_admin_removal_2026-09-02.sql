-- sql/sairnroofing_verify_admin_removal_2026-09-02.sql
--
-- Removes `rf-verify-admin` -- an account whose PIN is PUBLISHED IN THIS REPO
-- (sql/sairnroofing_verify_admin_seed.sql, line 21) -- from RF-PINNACLE-2026,
-- the real SAIRNroofing customer licence.
--
-- ── THIS IS NOT A NEW JUDGEMENT ─────────────────────────────────────────────
-- sql/stonedesk_recovery_admin_seed.sql already settled the identical question
-- for StoneDesk, in its own words:
--
--     "A published PIN cannot safely persist on SD-PINNACLE-2026 ... THE FIX IS
--      THE LICENCE, NOT THE PIN."
--     "A PIN in a public repo is a reason to DELETE the account, never to
--      rotate it quietly."
--
-- StoneDesk deleted its account and moved verification to SD-AUDIT-2026.
-- SAIRNroofing never got the same treatment, and the seed is still on disk
-- pointing at the customer licence. This closes that.
--
-- RUN sql/sairnroofing_audit_license_seed.sql FIRST. That mints RF-AUDIT-2026
-- so verification has somewhere to live before this takes its current home
-- away. Order matters only for convenience, not for safety -- but running this
-- alone leaves roofing with no verification account at all.
--
-- ── WHY IT IS SAFE TO DELETE THIS ROW SPECIFICALLY ──────────────────────────
-- The unrecoverable state is a licence with credential rows and ZERO active
-- provisioners: bootstrap refuses 409 while any row exists, and both `setup`
-- and `set_active` need an active provisioner. SQL is the only door into it,
-- which is why the guard below is in this file rather than in the app.
--
-- RF-PINNACLE-2026 carries a real `owner` account, created when Phases 1-2 were
-- verified -- sairnroofing_verify_admin_seed.sql:8-9 records that bootstrap
-- already refuses on this licence for exactly that reason. Deleting
-- `rf-verify-admin` therefore leaves that owner in place. The guard asserts it
-- rather than trusting it, and ABORTS the whole transaction if it is not true.
--
-- ROOFING'S PROVISIONING ROLE IS `owner` (api/rf-auth.js:101). Hardcoding
-- 'owner' is correct HERE and is wrong for SAIRNcode, whose provisioning role is
-- 'admin' -- the mistake tools/employee_auth_guard_check.py exists to catch.
--
-- I did NOT test whether this account still authenticates. A failed login
-- increments a lockout counter on a customer licence, and the answer changes
-- nothing: if it is live the row must go, and if it is not the delete is a
-- no-op. Deleting on the evidence in the repo is the cheaper of the two.

begin;

-- The deletion. Scoped to the one licence and the one employee_id.
delete from public.sairnroofing_employee_auth
 where license_hash = encode(digest('RF-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id  = 'rf-verify-admin';

-- ── RECOVERABILITY GUARD -- runs INSIDE the transaction, after the delete ───
-- Two end states are safe and only two: zero rows for the licence (which
-- re-arms bootstrap and is recovery, not lockout), or at least one ACTIVE
-- provisioner. Deleting a subset of the provisioners is the only dangerous
-- shape, and it is the one this asserts against.
do $$
declare
  lh   text := encode(digest('RF-PINNACLE-2026', 'sha256'), 'hex');
  rows int;
  owns int;
begin
  select count(*) into rows
    from public.sairnroofing_employee_auth where license_hash = lh;
  select count(*) into owns
    from public.sairnroofing_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);  -- rf PROVISIONING_ROLES, api/rf-auth.js:101

  if rows > 0 and owns = 0 then
    raise exception
      'ABORTED: this would leave RF-PINNACLE-2026 with % credential row(s) and ZERO active provisioners. '
      'That is the unrecoverable state -- bootstrap refuses (409) while any row exists, and setup '
      'and set_active both require an active owner. Either delete EVERY row for this licence, or '
      'leave at least one active owner. Never a subset of the owners.', rows;
  end if;

  raise notice 'Guard passed: % row(s) remain, % active owner(s).', rows, owns;
end $$;

commit;

-- ── VERIFY ──────────────────────────────────────────────────────────────────
-- Expect ZERO rows for rf-verify-admin, and at least one active owner.
select employee_id, role, active
  from public.sairnroofing_employee_auth
 where license_hash = encode(digest('RF-PINNACLE-2026', 'sha256'), 'hex')
 order by employee_id;

-- And confirm the account no longer authenticates:
--   curl -s -X POST https://sairn.vercel.app/api/rf-auth \
--     -H 'Content-Type: application/json' \
--     -H 'Authorization: Bearer RF-PINNACLE-2026' \
--     -d '{"action":"login","employee_id":"rf-verify-admin","pin":"481502"}'
-- Expect 401 INVALID_CREDENTIALS. Run this ONCE -- five failures lock the id
-- for fifteen minutes, and on a customer licence that is a real cost.
