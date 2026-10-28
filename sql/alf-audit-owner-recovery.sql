-- hank b58, 2026-10-28: RECOVERY for the owner credential on the AUDIT licence ALF-AUDIT-2026.
-- hank b59, 2026-10-28: RUN-READY. The b58 version shipped with placeholders and aborted on its own guard (P0001) when
-- Michael ran it. That was correct fail-closed behaviour on a file that should not have shipped that way. The real
-- hash and salt are now written below.
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
-- THE PIN IS NOT IN THIS FILE. Only its scrypt hash and salt are, made with api/_lib/auth.js hashPin()
-- (64-byte scrypt, giving 128 hex characters; a 16-byte salt, giving 32 hex characters).
-- The 8-digit PIN was generated in b59. It is held in ONE place, outside every commit:
--   C:\Users\marsh\Documents\SAIRN-hank\.git\sairn-alf-audit-owner-pin
-- Move it into your password manager, then delete that file.
-- ALF accepts PINs of 6 to 8 digits (api/alf-auth.js:221).
-- The well-formedness guard below still aborts if the values are ever replaced with something that is not hex.
--
-- STATED RISK: this repository is PUBLIC, so the scrypt hash of an 8-digit PIN is now readable by anyone and can be
-- attacked offline, past the server-side lockout. b51's file carried the same exposure. It is acceptable here only
-- because ALF-AUDIT-2026 is an audit licence with synthetic data. Re-key with a fresh PIN after the verification
-- that needs it, and never use this pattern on a customer licence.
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
  if 'e529b565c8fcb696ad8aec59e603d5de86cd8363c430c5f4caaff99c1996592af65714e277a0a26f25f70498ead338f80cff60c587e59b8b6dd8c4ab62fc6baa' !~ '^[0-9a-f]{128}$' or 'f472b00650e10f440859b2f1b0e282d1' !~ '^[0-9a-f]{32}$' then
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
  'e529b565c8fcb696ad8aec59e603d5de86cd8363c430c5f4caaff99c1996592af65714e277a0a26f25f70498ead338f80cff60c587e59b8b6dd8c4ab62fc6baa', 'f472b00650e10f440859b2f1b0e282d1',
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
