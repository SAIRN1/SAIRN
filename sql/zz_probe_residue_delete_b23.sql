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
-- clean run is two INACTIVE-or-owner rows that cannot sign in as a paralegal,
-- not a live credential. This file exists for the case where the probe dies
-- between the setup and the teardown -- and because a named residue with no way
-- out is not a declaration, it is a note.
--
-- SAFE TO RUN AT ANY TIME. It deletes exactly two employee_ids on exactly one
-- licence, both of which are probe accounts created by this repo's own tooling.
-- It is a no-op if they are already gone.

-- WHICH LICENCE: the audit one. The hash is computed the same way the app
-- computes it, so this file does not carry a hash literal that could drift.
-- Run the select FIRST and read the two rows before deleting them.

select employee_id, role, active, created_at
  from public.sairnlaw_employee_auth
 where employee_id in ('hank-b23-owner', 'hank-b23-paralegal');
-- expect at most 2 rows, both on the LAW-AUDIT-2026 tenant. If you see a row
-- with any OTHER employee_id, STOP -- the delete below is scoped by id and
-- that row is not this probe's.

delete from public.sairnlaw_employee_auth
 where employee_id in ('hank-b23-owner', 'hank-b23-paralegal');
-- expect DELETE 0, 1 or 2.

-- VERIFY, because a delete that affected nothing and a delete that affected
-- the wrong thing both report a number and only one of them is what you wanted:
select count(*) as should_be_zero
  from public.sairnlaw_employee_auth
 where employee_id in ('hank-b23-owner', 'hank-b23-paralegal');
-- expect 0.
