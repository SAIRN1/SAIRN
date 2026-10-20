-- sql/verify_sen_audit_2026.sql
--
-- CONCEPT. Say whether SEN-AUDIT-2026 exists AND is the right kind of row, as
-- named pass/fail lines, so "no rows came back" can never be read as a pass.
--
-- READ-ONLY: three selects, no insert, update, delete or DDL.
-- IF RUN TWICE: identical output both times (it reads current state only).
-- IF RUN BEFORE sql/mint_sen_audit_2026.sql: every check reads FAIL and
-- `found_rows` is 0 -- a result, not an error.
--
-- Expected after minting: 5 rows, all PASS.
-- ---------------------------------------------------------------------------

with sen as (
  select * from public.license_keys where key = 'SEN-AUDIT-2026'
),
ref as (
  select * from public.license_keys where key = 'SEN-PINNACLE-2026'
)
select check_name, case when ok then 'PASS' else 'FAIL' end as result, detail
from (
  select 1 as ord, 'exactly one SEN-AUDIT-2026 row' as check_name,
         (select count(*) from sen) = 1 as ok,
         'found_rows=' || (select count(*) from sen) as detail
  union all
  select 2, 'status is active',
         coalesce((select status = 'active' from sen), false),
         'status=' || coalesce((select status from sen), '<no row>')
  union all
  select 3, 'app_id is sairnsenior',
         coalesce((select app_id = 'sairnsenior' from sen), false),
         'app_id=' || coalesce((select app_id from sen), '<no row>')
  union all
  select 4, 'plan matches the demo licence it sits beside (SEN-PINNACLE-2026)',
         coalesce((select s.plan is not distinct from r.plan from sen s, ref r), false),
         'audit=' || coalesce((select plan from sen), '<no row>')
           || ' demo=' || coalesce((select plan from ref), '<no row>')
  union all
  select 5, 'key matches the audit-key shape tools/audit_licence.py accepts',
         coalesce((select key ~ '^[A-Z]{2,6}-AUDIT-[0-9]{4}$' from sen), false),
         'key=' || coalesce((select key from sen), '<no row>')
) c
order by ord;
