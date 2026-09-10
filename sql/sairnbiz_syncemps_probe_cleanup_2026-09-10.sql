-- sql/sairnbiz_syncemps_probe_cleanup_2026-09-10.sql
--
-- Removes the ONE row written by the 2026-09-10 live verification of
-- syncEmps()'s authenticated write path.
--
-- ── WHY A ROW WAS WRITTEN AT ALL ──────────────────────────────────────────
-- The open-work row on syncEmps() said, in its own words: "no session has ever
-- observed a full authenticated write succeed end-to-end -- every probe used
-- the anon key, which is permission-blocked by design, so a real 200 with a row
-- written has never been seen... Do not close on the strength of the code
-- reading alone."
--
-- Everything BEFORE the database was verified without writing anything: an
-- empty roster returns 200 written:0 and never reaches PostgREST, which proves
-- the session verified as `sairnbiz`, the role passed
-- EMPLOYEES_WRITE_ALLOWED_ROLES, and lic.customer_email was present (a missing
-- one answers 409 NO_TENANT). Only the upsert itself could not be observed that
-- way, and one row is the smallest thing that observes it.
--
-- ── WHY IT IS SAFE WHERE IT SITS, AND WHY IT STILL NEEDS DELETING ─────────
-- It was written under SB-TEST-2026, the licence the demo-credentials doc
-- labels a TEST key, not a customer's. It was then re-written with
-- status='Inactive', and api/sd-data.js's employees READ branch filters
-- `status=eq.Active`, so the product cannot surface it on any device.
--
-- Invisible is not absent. This platform has an open row about live write-path
-- verification leaving rows the product cannot delete -- fifteen hand-written
-- cleanup files across eleven apps and still growing -- and a probe row that
-- nobody can see is exactly how that list grows quietly. So it is written down
-- here, with the identifier, on the day it was made.
--
-- Run as the object owner in the Supabase SQL editor. Statement by statement.

-- ── SECTION 0: WHAT IS THERE NOW, before anything is deleted ──────────────
-- Expected: exactly 1 row, status 'Inactive', source_app 'sairnbiz'.
-- ZERO rows means somebody has already run this -- stop, do not "fix" it.
select customer_email, employee_id, source_app, status, updated_at
from public.employees
where employee_id = 'zz-probe-syncemps-2026-09-10';

-- ── CONTROL, and it is not optional ───────────────────────────────────────
-- A delete that reports 0 rows proves nothing unless something proves the
-- predicate could ever have matched. This counts the REAL rows beside it under
-- the same tenant, so a zero below can be told apart from a predicate that was
-- never going to match anything.
-- Expected: some number >= 0. Write the number down before deleting.
select count(*) as real_sairnbiz_rows_beside_the_probe
from public.employees
where source_app = 'sairnbiz'
  and employee_id <> 'zz-probe-syncemps-2026-09-10';

-- ── SECTION 1: THE DELETE ─────────────────────────────────────────────────
-- Scoped to the probe id alone. No wildcard, no status predicate: a status
-- filter here would silently spare the row if somebody had set it back to
-- Active, which is the one case where you would most want it gone.
delete from public.employees
where employee_id = 'zz-probe-syncemps-2026-09-10';
-- Expected: DELETE 1.

-- ── SECTION 2: CONFIRM, per statement ─────────────────────────────────────
-- 2a. The probe row is gone.
-- Expected: 0.
select count(*) as probe_rows_remaining
from public.employees
where employee_id = 'zz-probe-syncemps-2026-09-10';

-- 2b. NOTHING ELSE WENT WITH IT. Compare against the control above: this must
-- be the SAME number. A smaller one means the delete reached further than its
-- predicate says it can, and that is a finding, not a rounding error.
-- Expected: identical to the control's count.
select count(*) as real_sairnbiz_rows_after
from public.employees
where source_app = 'sairnbiz'
  and employee_id <> 'zz-probe-syncemps-2026-09-10';
