-- hank b51, 2026-10-22: an owner credential on the AUDIT licence ALF-AUDIT-2026, so the
-- D1 fix (billing may not read a MAR through the assignment tier) can be
-- verified on the DEPLOYED API. docs/2026-09-29-alf-audit-licence-unusable.md:
-- zz-audit-owner is active and its PIN is recorded nowhere, so no session can
-- sign in. This ADDS a second owner, 'audit-owner'; zz-audit-owner is untouched.
--
-- The PIN is NOT in this file -- only its scrypt hash and salt, made with
-- api/_lib/auth.js hashPin(). hank holds the PIN in its session scratchpad.
-- AUDIT LICENCE ONLY. Recoverability guard below (PR 3.4): PROVISIONING_ROLES
-- for SAIRNcare is ['owner'] (api/alf-auth.js:52); the transaction aborts if the
-- licence would be left with rows and zero active owners.
begin;

insert into public.sairncare_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c',
  'audit-owner',
  'Audit Owner',
  'owner',
  'e91b4aa1f4f329a85633072713f33f96f8f6641a5f8f5513ffaafdd6c9a701c44c0c4715d298a157685a5ccef3df2ae2b130b8a5de59c4b4b86b83c06f4a791a',
  'f7193b85078b355d790d9773c9ee3e8c',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

do $$
declare
  lh   text;
  rows int;
  prov int;
begin
  lh := encode(digest('ALF-AUDIT-2026', 'sha256'), 'hex');
  if lh <> '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c' then
    raise exception 'ABORTED: the license_hash literal for ALF-AUDIT-2026 does not match sha256 of the key. Nothing has been committed.';
  end if;
  select count(*) into rows from public.sairncare_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairncare_employee_auth
   where license_hash = lh and active = true
     and role = any (array['owner']);
  if rows > 0 and prov = 0 then
    raise exception
      'ABORTED: ALF-AUDIT-2026 would be left with credential rows and ZERO active provisioners (% row(s)). Nothing has been committed.', rows;
  end if;
  if not exists (select 1 from public.sairncare_employee_auth
                  where license_hash = lh and employee_id = 'audit-owner'
                    and active = true and role = 'owner') then
    raise exception 'ABORTED: audit-owner is not an active owner after the upsert. Nothing has been committed.';
  end if;
  raise notice 'ALF-AUDIT-2026: % row(s), % active owner(s), audit-owner active.', rows, prov;
end $$;

commit;

-- AFTER: expect one row, active = true, role = owner.
select employee_id, role, active
  from public.sairncare_employee_auth
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c' and employee_id = 'audit-owner';
