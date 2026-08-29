-- sql/sairnmechanical_access_panel_verify_cleanup_2026-08-28.sql
-- Teardown for the SAIRNmechanical Access-panel live round trip, 2026-08-28.
--
-- ╔════════════════════════════════════════════════════════════════════════╗
-- ║ NOT RUN by the session that wrote this file — it has no DB access.      ║
-- ║ That label has now been wrong FIVE times on this platform. Verify.      ║
-- ╚════════════════════════════════════════════════════════════════════════╝
--
-- ── THE LABEL DRIFT, AND THIS RUN IS ITSELF AN INSTANCE ──────────────────
-- sql/sairnmechanical_verify_auth_cleanup_2026-08-27.sql still says NOT RUN.
-- It HAD run: `bootstrap` succeeded on MECH-PINNACLE-2026 on 2026-08-28, which
-- is only possible when zero credential rows exist. That is the fifth confirmed
-- instance, after the SAIRNsenior cleanup, the 6-of-8 probe-row spot check, and
-- the SAIRNroofing admin seed whose account 401'd while its sibling foremen
-- seed's accounts worked. A "NOT RUN" note is a claim about the FILE; it stops
-- describing the DATABASE the moment anyone runs it.
--
-- Good news in it: that earlier cleanup did its job. The two credentials it
-- named (mech-verify-owner, mech-verify-tech) whose PINs sat in a session
-- transcript are gone, and the licence was clean when this run started.
--
-- ── WHAT THIS RUN CREATED ────────────────────────────────────────────────
-- Unlike the SAIRNroofing round trip, which reused pre-existing accounts, this
-- one had to CREATE both, because the licence was correctly empty:
--
--     mech-access-verify-20260828   role owner   (via bootstrap)
--     mech-access-verify-tech       role tech    (via setup)
--
-- Both are LIVE, WORKING credentials until this file runs. Their PINs were
-- randomly generated at run time and are deliberately NOT written here — a
-- cleanup script carrying the secrets it exists to retire is a worse artifact
-- than the debris, which is the reasoning the 2026-08-27 file already set and
-- this one inherits. The two employee_ids are enough to target them.
--
-- ── WHAT THE ROUND TRIP PROVED ───────────────────────────────────────────
-- All against the real deployed API. Every leg passed:
--   reason required to deactivate (400) · self-deactivation refused (409
--   SELF_DEACTIVATE) · deactivate the tech (200, remaining_owners 1) · repeat
--   returns unchanged:true · THE REAL CONSEQUENCE — the deactivated tech can no
--   longer sign in (401) · reactivate with no reason supplied (200, correctly
--   not required) · sign-in restored (200) · and from the tech's own session,
--   roster 403 and set_active 403.
--
-- LAST_OWNER was not reachable here either: with one owner, deactivating it
-- returns 409 SELF_DEACTIVATE because the self-check precedes the roster read.
-- Same quarantined-guard behaviour observed on SAIRNroofing. Recorded as
-- observed, not asserted.
--
-- ── DELETE, NEVER DEACTIVATE ─────────────────────────────────────────────
-- Do not "clean up" by setting active = false. SAIRNmechanical's
-- PROVISIONING_ROLES is ['owner'] ONLY, so deactivating the sole owner leaves a
-- licence where reactivating needs an owner (403), provisioning needs an owner
-- (403), and bootstrap refuses while any row exists (409). That is not
-- hypothetical — it was found live on RF-PINNACLE-2026 on 2026-08-28 and is one
-- of four apps with this exposure. See the Platform row in
-- docs/SAIRN-OPEN-WORK-INDEX.md.
--
-- Deleting BOTH rows re-arms bootstrap, which is the correct end state for a
-- demo licence: a real customer creates their own Owner.

begin;

delete from public.sairnmechanical_employee_auth
 where license_hash = encode(digest('MECH-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id in (
     'mech-access-verify-20260828',
     'mech-access-verify-tech'
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
-- ROLES BELOW ARE SAIRNmechanical's OWN PROVISIONING_ROLES, read from api/mech-auth.js:84.
-- Do not copy this block to another app without re-reading that app's list --
-- SAIRNcode's is `admin`, not `owner`.
do $$
declare
  lh   text := encode(digest('MECH-PINNACLE-2026', 'sha256'), 'hex');
  rows int;
  prov int;
begin
  select count(*) into rows
    from public.sairnmechanical_employee_auth where license_hash = lh;
  select count(*) into prov
    from public.sairnmechanical_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);

  if rows > 0 and prov = 0 then
    raise exception
      'ABORTED: this would leave MECH-PINNACLE-2026 with % credential row(s) and ZERO active provisioners. '
      'That is the unrecoverable state. Delete EVERY row for this licence, or leave at least one '
      'active provisioner. Never a subset of the provisioners.', rows;
  end if;

  raise notice 'Guard passed: % row(s) remain, % active provisioner(s).', rows, prov;
end $$;

commit;

-- ── VERIFY AFTER RUNNING ─────────────────────────────────────────────────
-- Expect 0:
--   select count(*) from public.sairnmechanical_employee_auth
--    where license_hash = encode(digest('MECH-PINNACLE-2026','sha256'),'hex');
--
-- Expect 1 — the licence itself is NOT removed:
--   select count(*) from public.license_keys where key = 'MECH-PINNACLE-2026';
--
-- Then confirm through the API, which is the real proof the rows are gone
-- rather than merely deactivated — a 200 means bootstrap is re-armed and the
-- licence is healthy; a 409 ALREADY_PROVISIONED means a row survived:
--   POST /api/mech-auth {"action":"bootstrap","employee_id":"...","pin":"12345678"}
