-- sql/2026-10-22-cody-b49-leg-f3-residue-removal.sql
-- ---------------------------------------------------------------------------
-- WHAT: removes what cody b49's live F3 verification left on the SAIRNlegacy
-- DEMO licence LEG-PINNACLE-2026, and nothing else:
--   1 test cremation   public.leg_cremations                   cremation_id CR-B49-F3-LIVE-F3D9FB
--   1 spent token      public.sairnlegacy_countersign_tokens   prepared_by b49-f3-apprentice
--   2 test credentials public.sairnlegacy_employee_auth        b49-f3-apprentice, b49-f3-director
--                                                              (both already DEACTIVATED via set_active)
-- The enumeration it comes from: docs/live-residue/2026-10-22-cody-b49-leg-f3-live.json.
--
-- NOT TOUCHED, ON PURPOSE: public.sairnlegacy_settings (restored to its prior
-- value by the run, confirmed by re-read) and public.sairnlegacy_audit_log
-- (an audit ledger records that the test happened; it is not residue).
--
-- HOW TO RUN: step 1 alone first and read the counts. Expected: 1, 1, 2.
-- Anything else -> STOP; do not run step 2. Then step 2 as ONE paste (it is
-- one transaction). Then step 3; expected 0, 0, 0, and owners_active >= 1.
--
-- RECOVERABILITY (PR 3.4): SAIRNlegacy's PROVISIONING_ROLES is ['owner']
-- (api/leg-auth.js:80). The two rows deleted are an apprentice and a director,
-- never an owner, and the guard below aborts the whole transaction if the
-- licence would be left with credential rows and no active owner.
-- ---------------------------------------------------------------------------

-- ── STEP 1: blast radius (read-only) ──────────────────────────────────────
select
  (select count(*) from public.leg_cremations
    where license_hash = encode(digest('LEG-PINNACLE-2026','sha256'),'hex')
      and cremation_id = 'CR-B49-F3-LIVE-F3D9FB')                          as cremations_expect_1,
  (select count(*) from public.sairnlegacy_countersign_tokens
    where license_hash = encode(digest('LEG-PINNACLE-2026','sha256'),'hex')
      and prepared_by = 'b49-f3-apprentice')                               as tokens_expect_1,
  (select count(*) from public.sairnlegacy_employee_auth
    where license_hash = encode(digest('LEG-PINNACLE-2026','sha256'),'hex')
      and employee_id in ('b49-f3-apprentice','b49-f3-director')
      and role in ('apprentice','director') and active = false)            as creds_expect_2;

-- ── STEP 2: removal, one transaction ──────────────────────────────────────
begin;

delete from public.leg_cremations
 where license_hash = encode(digest('LEG-PINNACLE-2026','sha256'),'hex')
   and cremation_id = 'CR-B49-F3-LIVE-F3D9FB';

delete from public.sairnlegacy_countersign_tokens
 where license_hash = encode(digest('LEG-PINNACLE-2026','sha256'),'hex')
   and prepared_by = 'b49-f3-apprentice';

delete from public.sairnlegacy_employee_auth
 where license_hash = encode(digest('LEG-PINNACLE-2026','sha256'),'hex')
   and employee_id in ('b49-f3-apprentice','b49-f3-director')
   and role in ('apprentice','director')
   and active = false;

do $$
declare
  lh   text := encode(digest('LEG-PINNACLE-2026','sha256'),'hex');
  rows int;
  prov int;
begin
  select count(*) into rows from public.sairnlegacy_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairnlegacy_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);
  if rows > 0 and prov = 0 then
    raise exception
      'ABORTED: LEG-PINNACLE-2026 would be left with credential rows and ZERO active provisioners (% row(s)). Nothing was removed.', rows;
  end if;
  raise notice 'LEG-PINNACLE-2026: % credential row(s), % active owner(s).', rows, prov;
end $$;

commit;

-- ── STEP 3: confirm ───────────────────────────────────────────────────────
select
  (select count(*) from public.leg_cremations
    where license_hash = encode(digest('LEG-PINNACLE-2026','sha256'),'hex')
      and cremation_id = 'CR-B49-F3-LIVE-F3D9FB')                          as cremations_expect_0,
  (select count(*) from public.sairnlegacy_countersign_tokens
    where license_hash = encode(digest('LEG-PINNACLE-2026','sha256'),'hex')
      and prepared_by = 'b49-f3-apprentice')                               as tokens_expect_0,
  (select count(*) from public.sairnlegacy_employee_auth
    where license_hash = encode(digest('LEG-PINNACLE-2026','sha256'),'hex')
      and employee_id in ('b49-f3-apprentice','b49-f3-director'))          as creds_expect_0,
  (select count(*) from public.sairnlegacy_employee_auth
    where license_hash = encode(digest('LEG-PINNACLE-2026','sha256'),'hex')
      and active = true and role = 'owner')                                as owners_active_expect_ge_1;
