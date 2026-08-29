-- sql/stonedesk_access_panel_verify_cleanup_2026-08-28.sql
-- Teardown for the StoneDesk Revoke Sign-In Access round trip, 2026-08-28.
--
-- ╔════════════════════════════════════════════════════════════════════════╗
-- ║ NOT RUN by the session that wrote this file — it has no DB access.      ║
-- ║ That label has been wrong SIX times on this platform. Verify first.     ║
-- ╚════════════════════════════════════════════════════════════════════════╝
--
-- ── READ THIS BEFORE RUNNING: SD-PINNACLE-2026 IS NOT A CLEAN DEMO LICENCE ──
-- The live roster read on 2026-08-28 held FOUR accounts, and THREE of them are
-- real and must not be touched by any verification teardown:
--
--     cmonsul           Carolyn Monsul     owner   active   ← REAL PERSON
--     owner             Michael Dibert     owner   active   ← REAL, Michael's
--     hank-test         hank-test          owner   active   ← another session's
--     sd-verify-admin   (disposable)       admin   active   ← seeded for this run
--
-- This file deletes TWO rows and neither is any of the first three. Unlike the
-- SAIRNmechanical and SAIRNdental teardowns, it deliberately does NOT return the
-- licence to a bootstrap-rearmed state, because doing so would mean deleting a
-- named colleague's credential and Michael's own. Bootstrap stays 409 here, and
-- that is correct.
--
-- `hank-test` is left alone as well: it is a test account, but it is not mine,
-- it is an OWNER, and removing another session's row on the assumption it is
-- debris is exactly the guessing this project has been bitten by. Logged as an
-- open, unowned item rather than cleaned up here.
--
-- ── WHAT THIS RUN CREATED ────────────────────────────────────────────────
--     sd-verify-admin           role admin   (via sql/stonedesk_verify_admin_seed.sql)
--     sd-access-verify-sales    role sales   (via setup, during the round trip)
--
-- sd-verify-admin's PIN is published in its own seed file, which is reason
-- enough to delete it promptly. sd-access-verify-sales' PIN was randomly
-- generated at run time and is deliberately not written here.
--
-- ── WHY THIS RUN NEEDED A SEED AT ALL, worth recording ───────────────────
-- All three StoneDesk licences answered `bootstrap` with 409 and NO PIN for any
-- of them existed anywhere in the repo — the exact state api/sd-auth.js:304-308
-- records as how three StoneDesk licences were lost. The app that lost three
-- licences to untracked credential state could not be verified for that reason.
-- The seed is the fix for this run; the standing fix is not letting credential
-- state go unrecorded again.
--
-- ── WHAT THE ROUND TRIP PROVED ───────────────────────────────────────────
-- All against the real deployed API as sd-verify-admin (role admin):
--   reason required to deactivate (400) · self-deactivation refused (409
--   SELF_DEACTIVATE, "Ask another Owner or Manager") · deactivate the sales
--   account (200, remaining_admins 4, audited:true) · repeat returns
--   unchanged:true · THE REAL CONSEQUENCE — the deactivated account can no
--   longer sign in (401) · reactivate with no reason supplied (200) · sign-in
--   restored (200) · and from that account's own session, roster 403 and
--   set_active 403.
--
-- TWO THINGS UNIQUE TO STONEDESK, both verified live and true of no other app:
--   1. PRIVILEGE-ESCALATION GUARD. An `admin` attempting to provision an
--      `owner` is refused: 403 "Only an existing Owner can grant Owner access"
--      (api/sd-auth.js:243-247). This exists because StoneDesk is the only app
--      with TWO provisioning roles; the case cannot arise elsewhere.
--   2. audited:true, on successes AND on the SELF_DEACTIVATE refusal. StoneDesk
--      is one of only three apps with an audit table.
--
-- LAST_ADMIN was not reachable — four active provisioning-role accounts existed
-- throughout. Consistent with the other four apps: the guard is unreachable by
-- construction while a second provisioner exists.
--
-- ── DELETE, NEVER DEACTIVATE ─────────────────────────────────────────────
-- StoneDesk needs at least one active owner/admin. Deactivating toward zero is
-- the lockout found live on RF-PINNACLE-2026 the same day. StoneDesk has the
-- platform's LOWEST exposure to it — two provisioning roles and four active
-- holders — but reduced is not absent.

begin;

delete from public.sd_employee_auth
 where license_hash = encode(digest('SD-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id in (
     'sd-verify-admin',
     'sd-access-verify-sales'
   );


-- ── GUARD: the end state must not be the trapdoor. Added 2026-08-29 (Hank). ──
-- The trapdoor is "credential rows exist AND none of them is both `active` and
-- holding a role in this app's PROVISIONING_ROLES". `bootstrap` refuses 409
-- while ANY row exists and does not filter on `active`; `setup` and
-- `set_active` both require an active provisioner. All three exits shut.
--
-- Zero rows is NOT that state -- it RE-ARMS bootstrap and is recovery. The only
-- dangerous shape is deleting SOME provisioners while leaving others, which is
-- exactly how RF-PINNACLE-2026 got stuck. This raises and rolls the whole
-- transaction back rather than committing that shape.
--
-- The API cannot reach this state (set_active refuses self-deactivation and the
-- last active provisioner, and re-reads that the caller's own row is active).
-- SQL is the only door, which is why the guard lives here and not in the app.
--
-- ROLES BELOW ARE StoneDesk's OWN PROVISIONING_ROLES, read from api/sd-auth.js:46.
-- Do not copy this block to another app without re-reading that app's list --
-- SAIRNcode's is `admin`, not `owner`.
do $$
declare
  lh   text := encode(digest('SD-PINNACLE-2026', 'sha256'), 'hex');
  rows int;
  prov int;
begin
  select count(*) into rows
    from public.sd_employee_auth where license_hash = lh;
  select count(*) into prov
    from public.sd_employee_auth
   where license_hash = lh and active = true and role = any (array['owner', 'admin']);

  if rows > 0 and prov = 0 then
    raise exception
      'ABORTED: this would leave SD-PINNACLE-2026 with % credential row(s) and ZERO active provisioners. '
      'That is the unrecoverable state. Delete EVERY row for this licence, or leave at least one '
      'active provisioner. Never a subset of the provisioners.', rows;
  end if;

  raise notice 'Guard passed: % row(s) remain, % active provisioner(s).', rows, prov;
end $$;

commit;

-- ── VERIFY AFTER RUNNING ─────────────────────────────────────────────────
-- Expect 0:
--   select count(*) from public.sd_employee_auth
--    where license_hash = encode(digest('SD-PINNACLE-2026','sha256'),'hex')
--      and employee_id in ('sd-verify-admin','sd-access-verify-sales');
--
-- Expect 3, and it MUST include cmonsul and owner — this is the post-condition
-- that matters more than the deletion itself:
--   select employee_id, role, active
--     from public.sd_employee_auth
--    where license_hash = encode(digest('SD-PINNACLE-2026','sha256'),'hex')
--    order by employee_id;
--
-- If that returns fewer than 3, or omits cmonsul or owner, a real account has
-- been removed and this file is not the cause — stop and investigate before
-- provisioning anything.
--
-- Bootstrap should STILL return 409 afterwards. That is correct here and is not
-- a failure: real credentials remain on this licence by design.
