-- hank b58, 2026-10-28: RECOVERY for the owner credential on the AUDIT licence ALF-AUDIT-2026.
--
-- WHY THIS EXISTS. docs/2026-09-29-alf-audit-licence-unusable.md: zz-audit-owner is active
-- and its PIN is recorded nowhere. hank b51 (sql/alf_audit_owner_credential_2026-10-22.sql)
-- added 'audit-owner', but that PIN is held ONLY in hank's session scratchpad, a temp folder
-- that ends with the session. That is the same single point of failure one step later. This
-- file re-keys 'audit-owner' to a PIN that YOU hold, and clears any lockout on it, without
-- deleting anything.
--
-- MEASURED LIVE 2026-10-28 (read only, before writing this). ALF-AUDIT-2026 has 5 rows:
--   audit-owner (owner, active, 0 failed, unlocked)
--   zz-audit-owner (owner, active)
--   hank-b51-billing (billing, active)
--   zz-audit-caregiver and zz-audit-nursing (inactive)
-- So the licence is HEALTHY today. This is the recovery for when the scratchpad PIN is gone
-- or the account is locked, not a fix for a broken state.
--
-- THE PIN IS NEVER IN THIS FILE. Generate the hash pair yourself, from the repo root:
--
--   node -e "const c=require('crypto');let p='';for(let i=0;i<8;i++)p+=c.randomInt(10);const h=require('./api/_lib/auth.js').hashPin(p);console.log('PIN (record it in your password manager, then clear the terminal):',p);console.log('__PIN_HASH__ ->',h.pin_hash);console.log('__PIN_SALT__ ->',h.pin_salt)"
--
-- Paste the two values over __PIN_HASH__ and __PIN_SALT__ below. The PIN is 8 digits; ALF
-- accepts 6 to 8 (api/alf-auth.js:221). The hash is api/_lib/auth.js hashPin(): scrypt with
-- 64 bytes, giving 128 hex characters, and a 16-byte salt, giving 32 hex characters.
-- The guard aborts if either placeholder is still in place or malformed.
--
-- AUDIT LICENCE ONLY: scoped by sha256('ALF-AUDIT-2026') and checked against the literal.
-- Recoverability guard (PR 3.4): SAIRNcare PROVISIONING_ROLES = ['owner'] (api/alf-auth.js:52).
-- The transaction aborts if the licence would be left with rows and ZERO active provisioners.
begin;

-- 0. LOOK FIRST. You should see audit-owner, active, role owner.
select employee_id, role, active, failed_attempts, locked_until
  from public.sairncare_employee_auth
 where license_hash = encode(digest('ALF-AUDIT-2026', 'sha256'), 'hex')
 order by employee_id;

do $$
begin
  if '__PIN_HASH__' !~ '^[0-9a-f]{128}$' or '__PIN_SALT__' !~ '^[0-9a-f]{32}$' then
    raise exception 'ABORTED: the PIN hash and salt placeholders were not replaced with the generator output (128 and 32 hex characters). Nothing has been committed.';
  end if;
end $$;

-- 1. RE-KEY AND UNLOCK audit-owner. This is an upsert, so it also recreates the row if it was
--    removed. Nothing is deleted, and no other employee row is touched.
insert into public.sairncare_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active, failed_attempts, locked_until)
values (
  '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c',
  'audit-owner', 'Audit Owner', 'owner',
  '__PIN_HASH__', '__PIN_SALT__',
  true, 0, null
)
on conflict (license_hash, employee_id) do update
  set pin_hash        = excluded.pin_hash,
      pin_salt        = excluded.pin_salt,
      role            = 'owner',
      active          = true,
      failed_attempts = 0,
      locked_until    = null,
      updated_at      = now();

-- 2. GUARD.
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
   where license_hash = lh and active = true and role = any (array['owner']);
  if rows > 0 and prov = 0 then
    raise exception
      'ABORTED: ALF-AUDIT-2026 would be left with credential rows and ZERO active provisioners (% row(s)). Nothing has been committed.', rows;
  end if;
  if not exists (select 1 from public.sairncare_employee_auth
                  where license_hash = lh and employee_id = 'audit-owner'
                    and active = true and role = 'owner'
                    and failed_attempts = 0 and locked_until is null
                    and pin_salt ~ '^[0-9a-f]{32}$') then
    raise exception 'ABORTED: audit-owner is not an active, unlocked owner with a real salt after the upsert. Nothing has been committed.';
  end if;
  raise notice 'ALF-AUDIT-2026: % row(s), % active owner(s); audit-owner re-keyed and unlocked.', rows, prov;
end $$;

commit;

-- 3. AFTER: expect one row: owner, active, 0 failed attempts, not locked, and updated_at = now.
select employee_id, role, active, failed_attempts, locked_until, updated_at
  from public.sairncare_employee_auth
 where license_hash = '7b110bcc4441c548b9479aad6610cc4ee6973c747453725dc904626f805fb99c'
   and employee_id = 'audit-owner';
--
-- 4. LIVE CHECK, then RECORD WHERE THE PIN LIVES. Sign in through the product with
--    POST /api/alf-auth {action:'login', employee_id:'audit-owner', pin:<yours>} on licence
--    ALF-AUDIT-2026. It should answer ok. Then name the place where the PIN is held, but
--    never the value, in docs/2026-09-29-alf-audit-licence-unusable.md. Without that note the
--    next recovery starts from zero again.
