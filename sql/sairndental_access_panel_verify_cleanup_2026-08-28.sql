-- sql/sairndental_access_panel_verify_cleanup_2026-08-28.sql
-- Teardown for the SAIRNdental Sign-In Access panel live round trip, 2026-08-28.
--
-- ╔════════════════════════════════════════════════════════════════════════╗
-- ║ NOT RUN by the session that wrote this file — it has no DB access.      ║
-- ║ That label has now been wrong FIVE times on this platform. Verify with  ║
-- ║ the SELECTs at the bottom before acting on anything here.               ║
-- ╚════════════════════════════════════════════════════════════════════════╝
--
-- ── WHAT THIS RUN CREATED ────────────────────────────────────────────────
-- DNT-PINNACLE-2026 was clean when this started — `bootstrap` succeeded, which
-- is only possible with zero credential rows — so both accounts below were
-- created by this run and neither predates it:
--
--     dnt-access-verify-20260828   role owner       (via bootstrap)
--     dnt-access-verify-staff      role frontdesk   (via setup)
--
-- Both are LIVE, WORKING credentials until this file runs. Their PINs were
-- randomly generated at run time and are deliberately NOT written here: a
-- cleanup script carrying the secrets it exists to retire is a worse artifact
-- than the debris. The two employee_ids are enough to target them.
--
-- ── WHAT THE ROUND TRIP PROVED ───────────────────────────────────────────
-- All against the real deployed API. Every leg passed:
--   reason required to deactivate (400) · self-deactivation refused (409
--   SELF_DEACTIVATE) · deactivate the frontdesk account (200,
--   remaining_owners 1) · repeat returns unchanged:true · THE REAL CONSEQUENCE
--   — the deactivated account can no longer sign in (401) · reactivate with no
--   reason supplied (200, correctly not required) · sign-in restored (200) ·
--   and from that account's own session, roster 403 and set_active 403.
--
-- NOT_FOUND (404) was also exercised, by accident and worth recording: the first
-- `setup` attempt used role 'hygienist', which this app does not have — its
-- roles are owner|frontdesk|provider — so setup 400'd, the account never
-- existed, and the following set_active calls correctly returned 404 "No such
-- employee on this license". An unplanned but real verification of that path,
-- and a reminder that role vocabulary is per-app and must be read, not assumed.
--
-- LAST_OWNER was not reachable here either: with one owner, deactivating it
-- returns 409 SELF_DEACTIVATE because the self-check precedes the roster read.
-- Third app showing the same quarantined-guard behaviour, observed rather than
-- carried over.
--
-- ── DELETE, NEVER DEACTIVATE ─────────────────────────────────────────────
-- SAIRNdental's PROVISIONING_ROLES is ['owner'] ONLY — one of the four apps
-- with this exposure (CC, 2026-08-28). Deactivating the sole owner leaves a
-- licence where reactivating needs an owner (403), provisioning needs an owner
-- (403), and bootstrap refuses while any row exists (409). That is not
-- hypothetical: it was found live on RF-PINNACLE-2026 the same day. See the
-- Platform row in docs/SAIRN-OPEN-WORK-INDEX.md.
--
-- Deleting BOTH rows re-arms bootstrap, the correct end state for a demo
-- licence: a real customer creates their own Owner.

begin;

delete from public.sairndental_employee_auth
 where license_hash = encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id in (
     'dnt-access-verify-20260828',
     'dnt-access-verify-staff'
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
-- ROLES BELOW ARE SAIRNdental's OWN PROVISIONING_ROLES, read from api/dnt-auth.js:150.
-- Do not copy this block to another app without re-reading that app's list --
-- SAIRNcode's is `admin`, not `owner`.
do $$
declare
  lh   text := encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex');
  rows int;
  prov int;
begin
  select count(*) into rows
    from public.sairndental_employee_auth where license_hash = lh;
  select count(*) into prov
    from public.sairndental_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);

  if rows > 0 and prov = 0 then
    raise exception
      'ABORTED: this would leave DNT-PINNACLE-2026 with % credential row(s) and ZERO active provisioners. '
      'That is the unrecoverable state. Delete EVERY row for this licence, or leave at least one '
      'active provisioner. Never a subset of the provisioners.', rows;
  end if;

  raise notice 'Guard passed: % row(s) remain, % active provisioner(s).', rows, prov;
end $$;

commit;

-- ── VERIFY AFTER RUNNING ─────────────────────────────────────────────────
-- Expect 0:
--   select count(*) from public.sairndental_employee_auth
--    where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
--      and employee_id like 'dnt-access-verify-%';
--
-- Expect 1 — the licence itself is NOT removed:
--   select count(*) from public.license_keys where key = 'DNT-PINNACLE-2026';
--
-- Then confirm through the API, which is the real proof the rows are gone
-- rather than merely deactivated. A 200 means bootstrap is re-armed and the
-- licence is healthy; a 409 ALREADY_PROVISIONED means a row survived:
--   POST /api/dnt-auth {"action":"bootstrap","employee_id":"...","pin":"12345678"}
