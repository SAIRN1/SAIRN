-- TRUE-POSITIVE PROBE for tools/sairn_sql_preflight.py.
--
-- A checker that has only ever returned clean is unproven, not proven. Across
-- all 174 files in sql/ this tool's only finding is `license_keys` (a real
-- table with no tracked CREATE TABLE), which is a limitation of the DECLARED
-- source rather than a defect it caught. So the defects it is meant to catch
-- are written down here on purpose and asserted against.
--
-- NOT VALID SQL TO RUN. Never paste this into the editor.

-- D1: column that does not exist, in an INSERT column list.
--     sairnmechanical_employee_auth has no `pin_plaintext`.
insert into public.sairnmechanical_employee_auth
  (license_hash, employee_id, role, pin_hash, pin_salt, pin_plaintext)
values ('deadbeef', 'e1', 'owner', 'h', 's', '1234');

-- D2: table that does not exist anywhere.
insert into public.sairnmechanical_employee_authz (license_hash) values ('x');

-- D3: column that does not exist, in an UPDATE SET.
--     This is the dangerous one: a typo here can update the wrong thing or
--     nothing at all, and "0 rows" reads as "nothing needed changing".
update public.sairnmechanical_employee_auth
   set is_active = false
 where employee_id = 'e1';

-- D4: qualified reference to a column that does not exist.
select a.employee_id
  from public.sairnmechanical_employee_auth a
 where a.last_login_at < now();
