-- sql/sairncode_access_panel_verify_cleanup_2026-08-28.sql
-- Teardown for the SAIRNcode Sign-In Access panel live round trip, 2026-08-28.
--
-- ╔════════════════════════════════════════════════════════════════════════╗
-- ║ NOT RUN by the session that wrote this file — it has no DB access.      ║
-- ║ That label has now been wrong SIX times tonight. Verify before acting.  ║
-- ╚════════════════════════════════════════════════════════════════════════╝
--
-- ── SCOPE: ONE ROW. DELIBERATELY NARROW. ─────────────────────────────────
-- This file removes exactly ONE account, the only thing this session created
-- on SC-PINNACLE-2026:
--
--     sc-access-verify-coder   role coder   (created via setup, 2026-08-28)
--
-- Its PIN was randomly generated at run time and is deliberately NOT written
-- here: a cleanup script carrying the secret it exists to retire is a worse
-- artifact than the debris.
--
-- ── WHAT THIS FILE DELIBERATELY DOES *NOT* TOUCH, AND WHY ────────────────
-- Three things were proposed for this cleanup and all three were declined,
-- because none of them is traceable to an artifact this session wrote or
-- verified. Recorded here so the decision is visible rather than looking like
-- an omission:
--
--   1. `owner` — display_name "Michael", role admin, active. Read live from the
--      roster on 2026-08-28. This is a REAL, CURRENT account, not stale test
--      debris, and it is what makes `bootstrap` return 409 on this licence.
--      Deleting it would be destroying the licence's only permanent credential.
--      NEVER remove it as part of a verification teardown.
--
--   2. `sc-verify-admin` — the disposable seed account from
--      sql/sairncode_verify_admin_seed.sql, restored by Michael so this round
--      trip could run. LEFT IN PLACE on his call: `owner` remains active so
--      nothing depends on removing it, and deleting it is a low-value cleanup
--      carrying a small real risk if traced wrong. If it is ever removed, do it
--      through that seed file's own documented teardown, not this one.
--
--   3. `sc_*` probe rows and `sairncash_waitlist` rows. NOT MINE. This session
--      created no such rows and has no file naming them. `hank-admin` and
--      `hank-coder`, referenced in sairncode_verify_admin_seed.sql's comment,
--      do NOT exist on this licence — the live roster held exactly two accounts
--      before this run, `owner` and `sc-verify-admin`. Deleting rows on a
--      description that cannot be traced to a verified artifact is precisely
--      how real data is lost, and tonight already produced six files whose
--      labels no longer described the database. These remain OPEN, UNOWNED
--      cleanup items for whichever session actually created them.
--
-- ── WHAT THE ROUND TRIP PROVED ───────────────────────────────────────────
-- All against the real deployed API, as sc-verify-admin (role admin):
--   reason required to deactivate (400) · self-deactivation refused (409
--   SELF_DEACTIVATE) · deactivate the coder (200, remaining_admins 2) · repeat
--   returns unchanged:true · THE REAL CONSEQUENCE — the deactivated coder can
--   no longer sign in (401) · reactivate with no reason supplied (200) ·
--   sign-in restored (200) · and from the coder's own session, roster 403 and
--   set_active 403.
--
-- EVERY ONE OF THOSE WAS UNREACHABLE FROM THIS CLIENT BEFORE TODAY. scAuthCall
-- never sent X-SD-Auth, so roster/setup/set_active could not be called at all
-- regardless of server support. The transport fix shipped in the same commit as
-- the panel and this run is its proof.
--
-- AUDITED:TRUE, and unlike the other three apps that is real here. SAIRNcode is
-- one of only three apps with an audit table (api/_lib/audit.js allowlists
-- sairnlaw, sairncode and stonedesk). `audited:true` came back on the successful
-- changes AND on the SELF_DEACTIVATE refusal — the "audited is reported on
-- refusals too" design in api/sc-auth.js:331-334, observed working live.
--
-- LAST_ADMIN was not reachable: two active admins existed throughout, and with
-- one the self-check fires first. Same quarantined-guard behaviour seen on the
-- other three apps, observed independently rather than assumed.
--
-- ── DELETE, NEVER DEACTIVATE ─────────────────────────────────────────────
-- SAIRNcode's PROVISIONING_ROLES is ['admin'] ONLY — one of the four
-- single-provisioning-role apps (CC, 2026-08-28). Deactivating the last active
-- admin leaves a licence where reactivating needs an admin (403), provisioning
-- needs an admin (403), and bootstrap refuses while any row exists (409). Found
-- live on RF-PINNACLE-2026 the same day. See the Platform row in
-- docs/SAIRN-OPEN-WORK-INDEX.md.

begin;

delete from public.sairncode_employee_auth
 where license_hash = encode(digest('SC-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id = 'sc-access-verify-coder';


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
-- ROLES BELOW ARE SAIRNcode's OWN PROVISIONING_ROLES, read from api/sc-auth.js:50.
-- Do not copy this block to another app without re-reading that app's list --
-- SAIRNcode's is `admin`, not `owner`.
do $$
declare
  lh   text := encode(digest('SC-PINNACLE-2026', 'sha256'), 'hex');
  rows int;
  prov int;
begin
  select count(*) into rows
    from public.sairncode_employee_auth where license_hash = lh;
  select count(*) into prov
    from public.sairncode_employee_auth
   where license_hash = lh and active = true and role = any (array['admin']);

  if rows > 0 and prov = 0 then
    raise exception
      'ABORTED: this would leave SC-PINNACLE-2026 with % credential row(s) and ZERO active provisioners. '
      'That is the unrecoverable state. Delete EVERY row for this licence, or leave at least one '
      'active provisioner. Never a subset of the provisioners.', rows;
  end if;

  raise notice 'Guard passed: % row(s) remain, % active provisioner(s).', rows, prov;
end $$;

commit;

-- ── VERIFY AFTER RUNNING ─────────────────────────────────────────────────
-- Expect 0:
--   select count(*) from public.sairncode_employee_auth
--    where license_hash = encode(digest('SC-PINNACLE-2026','sha256'),'hex')
--      and employee_id = 'sc-access-verify-coder';
--
-- Expect 2 — `owner` and `sc-verify-admin` must BOTH survive:
--   select employee_id, role, active
--     from public.sairncode_employee_auth
--    where license_hash = encode(digest('SC-PINNACLE-2026','sha256'),'hex')
--    order by employee_id;
--
-- If that second query returns fewer than 2, or does not include `owner`,
-- something removed a real account and this file is not the cause — stop and
-- investigate before provisioning anything new.
