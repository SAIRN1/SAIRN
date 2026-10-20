-- sql/zz_probe_residue_delete_b23.sql
-- THE WAY OUT for what tools/law_trust_lock_live_probe.py leaves behind.
--
-- That probe proves SAIRNlaw's trust HARD-LOCK against the deployed endpoint,
-- and a role refusal cannot be proved without a credential in that role. So it
-- provisions two employee rows on the AUDIT licence (`LAW-AUDIT-2026`, never a
-- demo-facing one) and reuses the SAME TWO IDS on every run, so the row count
-- does not grow with the number of runs.
--
-- IT ALSO DEACTIVATES THE PARALEGAL AT THE END and reads the deactivation back
-- by attempting a login (which must then answer 401). So the residue after a
-- clean run is two rows that cannot sign in as an active paralegal, not a live
-- credential. This file exists for the case where the probe dies between the
-- setup and the teardown -- and because a named residue with no way out is not
-- a declaration, it is a note.
--
-- ── THE RECOVERABILITY GUARD IS NOT BOILERPLATE ON THIS FILE ──────────────
-- The push gate refused this file without it, and the gate was right. The two
-- rows this deletes include `hank-b23-owner`, which is an OWNER -- and
-- `PROVISIONING_ROLES` in api/law-auth.js is `['owner']`, read from that file
-- rather than assumed. So a future run that adds a THIRD credential on this
-- licence would turn this delete into "remove the only active provisioner and
-- leave the rest stranded": nobody could sign in, and `bootstrap` would refuse
-- because credential rows still exist.
--
-- TWO END STATES ARE SAFE AND ONLY TWO:
--   (a) ZERO rows for this licence -- `bootstrap` is re-armed. This is RECOVERY,
--       not lockout, and it is the state this file produces today.
--   (b) at least one ACTIVE row whose role is in PROVISIONING_ROLES.
-- The guard below refuses anything else, inside the transaction, so the delete
-- rolls back rather than half-applying.

begin;

-- WHICH LICENCE: the audit one. The hash is DERIVED here rather than pasted, so
-- this file carries no hash literal that could drift from the app's own.
-- Run the select FIRST and read the rows before letting the delete run.

select employee_id, role, active, created_at
  from public.sairnlaw_employee_auth
 where license_hash = encode(digest('LAW-AUDIT-2026', 'sha256'), 'hex')
   and employee_id in ('hank-b23-owner', 'hank-b23-paralegal');
-- expect at most 2 rows. If you see a row with any OTHER employee_id on this
-- licence, STOP and read the guard below -- the delete is scoped by id, and
-- that row is not this probe's.

delete from public.sairnlaw_employee_auth
 where license_hash = encode(digest('LAW-AUDIT-2026', 'sha256'), 'hex')
   and employee_id in ('hank-b23-owner', 'hank-b23-paralegal');
-- expect DELETE 0, 1 or 2.

-- ── THE GUARD. Runs BEFORE the commit so it can roll the delete back. ─────
do $$
declare
  lh   text := encode(digest('LAW-AUDIT-2026', 'sha256'), 'hex');
  rows int; prov int;
begin
  select count(*) into rows from public.sairnlaw_employee_auth
   where license_hash = lh;
  select count(*) into prov from public.sairnlaw_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);
  if rows > 0 and prov = 0 then
    raise exception
      'ABORTED: would leave % credential row(s) and ZERO active provisioners. '
      'Delete EVERY row for this licence, or leave at least one active '
      'provisioner. Never a subset of the provisioners.', rows;
  end if;
  raise notice 'Guard passed: % row(s), % active provisioner(s).', rows, prov;
end $$;

commit;

-- ── VERIFY AFTER COMMITTING, because a delete that affected nothing and a
-- ── delete that affected the wrong thing both report a number.
select count(*) as should_be_zero
  from public.sairnlaw_employee_auth
 where license_hash = encode(digest('LAW-AUDIT-2026', 'sha256'), 'hex')
   and employee_id in ('hank-b23-owner', 'hank-b23-paralegal');
-- expect 0.

select count(*) as rows_left_on_this_licence
  from public.sairnlaw_employee_auth
 where license_hash = encode(digest('LAW-AUDIT-2026', 'sha256'), 'hex');
-- expect 0 as well today. A NON-ZERO answer here is not an error, but it means
-- somebody else now holds credentials on the audit licence and the guard above
-- is the thing that kept them able to sign in.
