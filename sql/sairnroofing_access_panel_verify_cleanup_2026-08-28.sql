-- sql/sairnroofing_access_panel_verify_cleanup_2026-08-28.sql
-- Teardown for the SAIRNroofing Access-panel live round trip, 2026-08-28.
-- REWRITTEN 2026-08-29 (Hank) on Michael's instruction. Scope narrowed to the
-- two foreman accounts, and a guard added that makes the file safe whichever
-- set it is pointed at. Read "THE CORRECTION" below before changing it back.
--
-- ╔════════════════════════════════════════════════════════════════════════╗
-- ║ NOT RUN as of 2026-08-29 — the session that rewrote it has no DB access. ║
-- ║ Read the drift warning below before trusting that label.                ║
-- ╚════════════════════════════════════════════════════════════════════════╝
--
-- ── DO NOT TRUST A "NOT RUN" LABEL, INCLUDING THIS ONE ───────────────────
-- This trap has sprung four times on this platform, twice on SAIRNroofing:
--   * sairnsenior_verify_cleanup_2026-08-25.sql says NOT RUN; it had run.
--   * A 2026-08-26 spot-check found 6 of 8 measurable probe rows GONE across
--     five other cleanup files, all still labelled NOT RUN.
--   * sairnroofing_verify_admin_seed.sql said its account existed; login
--     returned 401 while the sibling FOREMEN seed's accounts worked.
-- The label at the top of THIS file was itself confirmed accurate on
-- 2026-08-29 by a live roster read — all five accounts were still present —
-- which is the only reason it is repeated rather than deleted.

-- ═════════════════════════════════════════════════════════════════════════
-- THE CORRECTION, 2026-08-29 — and the distinction the original blurred
-- ═════════════════════════════════════════════════════════════════════════
-- The version this replaces deleted ALL FIVE accounts. That was flagged as
-- recreating the zero-owner lockout. The precise position is worth writing
-- down, because BOTH the original file and the objection are half right and
-- the difference decides what is safe to run here ever again:
--
--   THE TRAPDOOR IS "ROWS EXIST, NONE OF THEM AN ACTIVE OWNER."
--   It is not "no owners". `bootstrap` refuses with 409 while ANY row exists,
--   because its existence probe deliberately does not filter on `active`
--   (api/rf-auth.js:227-232). `setup` and `set_active` both need an active
--   owner. So a licence with rows and no active owner has all three exits
--   closed — that is the state found on 2026-08-28.
--
--   DELETING EVERY ROW IS THEREFORE **RECOVERY**, NOT LOCKOUT. Zero rows
--   re-arms bootstrap and the licence is healthy again. The original file's
--   reasoning was sound on its own terms.
--
--   DELETING **SOME** OWNERS AND LEAVING OTHERS IS THE ONLY DANGEROUS SHAPE,
--   and it is exactly how this licence got stuck: the older three-account
--   cleanup would have removed rf-verify-admin while leaving rf-verify-owner
--   and rf-verify-ui behind as inactive owner rows.
--
-- SO THE FILE NO LONGER RELIES ON ANYONE HOLDING THAT DISTINCTION IN THEIR
-- HEAD. The guard at the bottom asserts the END STATE is one of the two safe
-- ones and rolls back otherwise. Point it at any subset you like; it can no
-- longer leave this licence in the trapdoor.
--
-- ── WHAT THIS VERSION ACTUALLY DELETES, and why that set ─────────────────
-- The two foreman accounts only. Michael's call 2026-08-29, and the
-- conservative choice: RF-PINNACLE-2026 currently has TWO active owners
-- (rf-verify-admin, promoted to `owner`, and rf-verify-owner, verified
-- `active: true` by a live roster read on 2026-08-29 — the open-work index
-- had both of those facts wrong until that read). Removing only the foremen
-- cannot reduce the active-owner count at all, so it is safe without needing
-- the guard to be right.
--
-- ── WHAT IS DELIBERATELY LEFT, AND THE COST OF LEAVING IT ────────────────
-- All three owner rows survive, and two of them are loggable-in with PINs
-- COMMITTED TO THIS REPO (sairnroofing_verify_admin_seed.sql). That is a real
-- standing exposure on a live licence and it is the price of the conservative
-- option, not an oversight. The original file's argument for deleting
-- everything was precisely this, and it still stands.
--
-- TO TAKE THE OTHER PATH LATER: delete all five in one transaction, never a
-- subset of the owners. The guard permits it (end state = zero rows) and
-- bootstrap is re-armed, which is the correct end state for a demo licence —
-- a real customer creates their own Owner rather than inheriting a disposable
-- one. Do NOT do it while any un-run script or session depends on
-- rf-verify-admin, which is currently the account the recovery rests on.
--
-- ── DELETE, NEVER DEACTIVATE ─────────────────────────────────────────────
-- Do not "clean up" by setting active = false. Deactivating the last active
-- owner is what creates the trapdoor, and it is how SD-AUDIT-2026 was lost
-- (api/sd-auth.js:304-308). Delete, or leave alone.
--
-- ── WHAT THE ROUND TRIP DID, so the rows are attributable ────────────────
-- All through the real deployed API as rf-verify-admin. Every leg passed:
--   reason required to deactivate (400) · self-deactivate refused (409
--   SELF_DEACTIVATE) · deactivate fmB (200, remaining_owners 2) · repeat is
--   unchanged:true · the deactivated foreman can no longer sign in (401) ·
--   deactivate the second owner (200, remaining_owners 1) · reactivate both
--   (200) · sign-in restored (200).
-- NO NEW ROWS WERE CREATED. Every account predates that session.
--
-- LAST_OWNER WAS NOT REACHED, and that is documented correct behaviour, not a
-- missed test: with one active owner left, deactivating it returns 409
-- SELF_DEACTIVATE because the self-check runs before the roster read. See
-- sairn-employee-auth-scaffold §7 — the quarantined guard.

begin;

-- ── 1. The disposable FOREMAN accounts. Neither is an owner, so this cannot
--       change the active-owner count. ─────────────────────────────────────
delete from public.sairnroofing_employee_auth
 where license_hash = encode(digest('RF-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id in ('rf-verify-fmA', 'rf-verify-fmB');

-- ── 2. THE GUARD. Structural, not advisory. ─────────────────────────────
-- Asserts the END STATE is one of the two safe shapes and aborts the whole
-- transaction otherwise. This is what makes the file safe to edit later: a
-- future pass that widens the delete list cannot leave the licence
-- unrecoverable, whether or not it read the essay above.
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

  -- Safe shape A: no credential rows at all -> bootstrap is re-armed.
  -- Safe shape B: at least one ACTIVE owner -> setup and set_active both work.
  -- Anything else is the trapdoor and must not be committed.
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

-- ── VERIFY AFTER RUNNING ─────────────────────────────────────────────────
-- Expect 3 rows (rf-verify-admin, rf-verify-owner, rf-verify-ui) and 2 active
-- owners. If the guard raised, NOTHING was deleted -- the whole transaction
-- rolled back, which is the intended behaviour:
--   select employee_id, role, active
--     from public.sairnroofing_employee_auth
--    where license_hash = encode(digest('RF-PINNACLE-2026','sha256'),'hex')
--    order by employee_id;
--
-- Expect 1 -- the licence itself is never removed:
--   select count(*) from public.license_keys where key = 'RF-PINNACLE-2026';
--
-- Then confirm through the API, which is the real proof and the only thing
-- that distinguishes deleted from merely deactivated:
--   POST /api/rf-auth {"action":"login","employee_id":"rf-verify-fmA","pin":"..."}
--     -> 401 INVALID_CREDENTIALS  (the row is gone)
--   POST /api/rf-auth {"action":"login","employee_id":"rf-verify-admin","pin":"481502"}
--     -> 200 with role owner      (recovery path intact)
-- Do NOT probe with action:bootstrap. It is a WRITE: on a licence with no rows
-- it CREATES a real owner credential. That mistake already left a junk row in
-- the live deadline store (see tools/load_deadline_seed.py's header).
--
-- NOTE: no roofing table grants DELETE to service_role -- all fourteen grant
-- lines are select/insert(/update) -- so this must run in the SQL editor as the
-- owner role. The app cannot perform this teardown, by design.
