-- CONTROL for tools/sairn_sql_preflight.py -- every construct here is CORRECT
-- and must produce ZERO findings. Each line is a shape that produced a false
-- positive in an earlier draft of the tool; they are kept so a future change
-- that reintroduces one fails loudly.

-- C1: a correct INSERT, every column real.
insert into public.sairnmechanical_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values ('deadbeef', 'e1', 'Owner', 'owner', 'h', 's', true);

-- C2: a CTE with a column list -- `declared(table_name)` was reported as a
--     missing table until the CTE pattern allowed one.
with declared(employee_id) as (values ('e1'), ('e2'))
select d.employee_id from declared d;

-- C3: IS DISTINCT FROM -- the word FROM with no table after it.
select employee_id
  from public.sairnmechanical_employee_auth
 where display_name is distinct from role;

-- C4: GRANT/REVOKE objects that are not tables. `anon` and `service_role` were
--     reported as missing tables on the very first file this tool was run on.
revoke all on public.sairnmechanical_employee_auth from anon, authenticated;
grant select, insert, update on public.sairnmechanical_employee_auth to service_role;
revoke all on all tables in schema public from anon;

-- C5: unqualified system catalogs, which are never schema-qualified in this repo.
select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace;

-- C6: a scratch table created with CTAS, no column list.
create temp table _probe_baseline as
  select employee_id from public.sairnmechanical_employee_auth;
select employee_id from _probe_baseline;

-- C7: a string literal that contains SQL. Must not be parsed as code.
insert into public.sairnmechanical_employee_auth (license_hash, employee_id, role, pin_hash, pin_salt)
values ('deadbeef', 'note: update public.nonexistent_table set bogus_column = 1', 'tech', 'h', 's');
