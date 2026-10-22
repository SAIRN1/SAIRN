-- sql/zz_probe_residue_delete_b57_leg_f3.sql
-- THE WAY OUT for what fourth b57's LIVE F3 drive left on the SAIRNlegacy
-- DEMO licence (LEG-PINNACLE-2026). Michael approved the write (b57 dispatch).
-- Enumeration: docs/live-residue/2026-10-22-fourth-b57-leg-f3-ui-live.json.
--
-- The drive clicked the b56 countersign UI (3c574265f) in the deployed
-- sairnlegacy.html: a TEST apprentice staged a cremation record, a TEST
-- director countersigned it, the apprentice filed it. That landed THREE kinds
-- of row, and nothing here deletes anything until a person runs it:
--   1. public.leg_cremations         cremation_id 'CR-1792702765162-46'
--      crematory_name "b57 F3 LIVE UI TEST -- not a real authorisation",
--      attached to the demo case CS-1 (FH-2026-001, a seeded demo case).
--   2. public.sairnlegacy_countersign_tokens   1 row, prepared_by
--      'b57-f3-apprentice', countersigned by 'b57-f3-director', SPENT by the
--      filing (a replay of the same reference answered 409
--      COUNTERSIGN_ALREADY_SPENT).
--   3. public.sairnlegacy_employee_auth   'b57-f3-apprentice' and
--      'b57-f3-director', both DEACTIVATED by the drive (roster read back
--      active = false). PINs were random and never recorded.
-- NOT residue: leg_settings was restored to its prior countersign list ([])
-- and re-read; audit-log rows are kept by design and are not deleted here.
--
-- Run ONE section at a time: the blast-radius select first, read it, then
-- the delete, then the confirm. The licence hash is DERIVED, never pasted.
-- `delete from` on leg_cremations matters only if the demo should not show the
-- test record: it is append-only for the APP, which is why the app cannot
-- remove it itself.

-- ── 1. the filed TEST cremation record ─────────────────────────────────────
select count(*) as blast_radius_expect_1 from public.leg_cremations
 where license_hash = encode(digest('LEG-PINNACLE-2026', 'sha256'), 'hex')
   and cremation_id = 'CR-1792702765162-46';
delete from public.leg_cremations
 where license_hash = encode(digest('LEG-PINNACLE-2026', 'sha256'), 'hex')
   and cremation_id = 'CR-1792702765162-46';
select count(*) as confirm_expect_0 from public.leg_cremations
 where license_hash = encode(digest('LEG-PINNACLE-2026', 'sha256'), 'hex')
   and cremation_id = 'CR-1792702765162-46';

-- ── 2. the spent countersign token row ────────────────────────────────────
select count(*) as blast_radius_expect_1 from public.sairnlegacy_countersign_tokens
 where license_hash = encode(digest('LEG-PINNACLE-2026', 'sha256'), 'hex')
   and prepared_by = 'b57-f3-apprentice';
delete from public.sairnlegacy_countersign_tokens
 where license_hash = encode(digest('LEG-PINNACLE-2026', 'sha256'), 'hex')
   and prepared_by = 'b57-f3-apprentice';
select count(*) as confirm_expect_0 from public.sairnlegacy_countersign_tokens
 where license_hash = encode(digest('LEG-PINNACLE-2026', 'sha256'), 'hex')
   and prepared_by = 'b57-f3-apprentice';

-- ── 3. the two deactivated TEST credentials, WITH THE RECOVERABILITY GUARD ──
-- PROVISIONING_ROLES in api/leg-auth.js is ['owner'] (read from the file).
-- Neither row deleted here is an owner, and the demo owner (sairn-demo-owner)
-- stays -- but the guard is not optional: it rolls the delete back if the
-- licence would be left with credential rows and ZERO active owners.
begin;
select employee_id, role, active from public.sairnlegacy_employee_auth
 where license_hash = encode(digest('LEG-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id in ('b57-f3-apprentice', 'b57-f3-director');
-- expect 2 rows, active = false, roles apprentice and director.
delete from public.sairnlegacy_employee_auth
 where license_hash = encode(digest('LEG-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id in ('b57-f3-apprentice', 'b57-f3-director');
do $$
declare
  lh   text := encode(digest('LEG-PINNACLE-2026', 'sha256'), 'hex');
  rows int; prov int;
begin
  select count(*) into rows from public.sairnlegacy_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairnlegacy_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);
  if rows > 0 and prov = 0 then
    raise exception
      'ABORTED: would leave % credential row(s) and ZERO active owners. '
      'Delete EVERY row for this licence, or leave at least one active owner.', rows;
  end if;
  raise notice 'Guard passed: % row(s), % active owner(s).', rows, prov;
end $$;
commit;
select count(*) as confirm_expect_0 from public.sairnlegacy_employee_auth
 where license_hash = encode(digest('LEG-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id in ('b57-f3-apprentice', 'b57-f3-director');
