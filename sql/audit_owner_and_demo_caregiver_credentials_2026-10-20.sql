-- sql/audit_owner_and_demo_caregiver_credentials_2026-10-20.sql
--
-- CONCEPT. Three employee credentials, each written with the platform's own
-- hashPin(), each guarded so the licence it lands on can never be left with
-- credential rows and no active provisioner, and each checked after the write
-- so the documented PIN is proven to be the one stored.
--
-- WRITTEN BY hank b31 ON MICHAEL'S INSTRUCTION. NOT RUN BY ME -- Michael runs it
-- in the Supabase SQL editor. Same shape as
-- sql/sairnfreedom_demo_owner_credential_2026-10-13.sql (the newest credential
-- seed on the platform), which is the pattern CLAUDE.md PR 3.4 enforces through
-- tools/employee_auth_guard_check.py.
--
-- ── THE THREE ACCOUNTS, AND THE PINS ARE PUBLISHED ON PURPOSE ─────────────
--   SEN-AUDIT-2026     sairnsenior_employee_auth  audit-owner     role owner     PIN 83816873
--   LAW-AUDIT-2026     sairnlaw_employee_auth     audit-owner     role owner     PIN 75380237
--   SEN-PINNACLE-2026  sairnsenior_employee_auth  demo-caregiver  role caregiver PIN 79948511
--
-- WHY PUBLISHING THEM IS ACCEPTABLE, AND THE CONDITION THAT ENDS IT: the two
-- *-AUDIT-2026 licences exist to be written to by tests and hold no customer data
-- (sql/audit_license_seed_mech_law_2026-09-28.sql makes the same argument), and
-- SEN-PINNACLE-2026 is a DEMO licence. The day any of the three holds a real
-- client's records, delete its row here and rotate the PIN.
--
-- HOW THE HASHES WERE MADE: api/_lib/auth.js hashPin() (scrypt, 64-byte key,
-- 16-byte random salt), then passed back through its own verifyPin(): the PIN
-- returned true and 00000000 returned false, for all three. license_hash is
-- api/_lib/license.js hashLicense(key) = sha256(key), and the guard below
-- recomputes it in SQL from the key so a typo in the literal is caught.
--
-- PIN SHAPE: 8 digits, inside the 6-8 digit rule sen-auth/law-auth enforce.
--
-- PROVISIONING ROLES READ FROM THE APPS, NOT ASSUMED: api/sen-auth.js:68 and
-- api/law-auth.js:130 both say PROVISIONING_ROLES = ['owner'].
--
-- IF RUN TWICE: the second run re-applies the same hash and salt to the same three
-- rows (ON CONFLICT ... DO UPDATE) and every guard passes again -- no new rows, the
-- same PINs. If someone changed one of these PINs through the app in between, the
-- re-run puts the PIN in this file back, which is what a seed file is for.
--
-- WHAT THIS DOES NOT DO: it does not create SEN-AUDIT-2026 (sql/mint_sen_audit_2026.sql
-- did, measured live b28) or LAW-AUDIT-2026 (sql/audit_license_seed_mech_law_2026-09-28.sql).
-- It touches no other employee row: hank-b23-owner and hank-b24-attorney on
-- LAW-AUDIT-2026 and the demo owner on SEN-PINNACLE-2026 are left as they are.
--
-- AFTER RUNNING:
--   SEN-AUDIT-2026 audit-owner  -> the straight-time-floor probe's SEN_OWNER_PIN
--     (it provisions its own caregiver, hank-b27-caregiver, with SEN_CAREGIVER_PIN)
--   LAW-AUDIT-2026 audit-owner  -> NOT the owner tools/law_trust_lock_live_probe.py
--     signs in as; that probe uses hank-b23-owner. See the b31 handoff.
-- ---------------------------------------------------------------------------

begin;

-- SEN-AUDIT-2026  --  sairnsenior_employee_auth  --  audit-owner / owner
insert into public.sairnsenior_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  'ad779c1ccfee3bbc5111670f8d2cb1751175da1995ba5fe2968e9efd5e22f8b0',
  'audit-owner',
  'Audit Owner',
  'owner',
  '41d157f6636a37f566d19824cadb639a2b2de6e5c2a2b86551c5327fd3c2c34f75d8fa99f1b29a80b879b65fb81d051e567953fc087ff188871271a4ad4eebdd',
  '4025dc53485e8855f795cc2284c8e6b6',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- LAW-AUDIT-2026  --  sairnlaw_employee_auth  --  audit-owner / owner
insert into public.sairnlaw_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '5126af3a36e4681c66194dcadc7f3a25a084867c4c2eb58674561d796da6cb6d',
  'audit-owner',
  'Audit Owner',
  'owner',
  '034f410a54f98e4339578684de56a8c52e7fb20ffa28812e4c28e1b383cc7255a2308e87ba90ed6943a8680e4926e7406c469f73b8a59a7396c7fb4bf83fe5d2',
  '8d51f009a63f097683e1ebc2d8f26184',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- SEN-PINNACLE-2026  --  sairnsenior_employee_auth  --  demo-caregiver / caregiver
insert into public.sairnsenior_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '75bdc179a257a6688febcd88df11ab0efed12542eea6a8db29a3053ee817ac8f',
  'demo-caregiver',
  'Demo Caregiver',
  'caregiver',
  'dc3742783bc625c2a8917a6d0a3c83530ed9de9b4670e0e6d833dc8be84caa43d50591ea899d3c2462cacda40a62b55109ba16abbfd1027ae6554dc391bb6107',
  '6ad3e55b9c6bf6ccfe6c15890d330354',
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
  lh := encode(digest('SEN-AUDIT-2026', 'sha256'), 'hex');
  if lh <> 'ad779c1ccfee3bbc5111670f8d2cb1751175da1995ba5fe2968e9efd5e22f8b0' then
    raise exception 'ABORTED: the license_hash literal for SEN-AUDIT-2026 does not match sha256 of the key. Nothing has been committed.';
  end if;
  select count(*) into rows from public.sairnsenior_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairnsenior_employee_auth
   where license_hash = lh and active = true
     and role = any (array['owner']);
  if rows > 0 and prov = 0 then
    raise exception
      'ABORTED: SEN-AUDIT-2026 would be left with credential rows and ZERO active provisioners (% row(s)). Delete EVERY row for this licence, or leave at least one active provisioner. Never a subset of the provisioners.', rows;
  end if;
  raise notice 'SEN-AUDIT-2026: % row(s), % active provisioner(s).', rows, prov;
  if not exists (
    select 1 from public.sairnsenior_employee_auth
     where license_hash = lh and employee_id = 'audit-owner'
       and role = 'owner' and active = true
       and pin_salt = '4025dc53485e8855f795cc2284c8e6b6') then
    raise exception 'ABORTED: audit-owner on SEN-AUDIT-2026 does not carry the PIN salt this file wrote, so the published PIN would not work. Nothing has been committed.';
  end if;
end $$;

do $$
declare
  lh   text;
  rows int;
  prov int;
begin
  lh := encode(digest('LAW-AUDIT-2026', 'sha256'), 'hex');
  if lh <> '5126af3a36e4681c66194dcadc7f3a25a084867c4c2eb58674561d796da6cb6d' then
    raise exception 'ABORTED: the license_hash literal for LAW-AUDIT-2026 does not match sha256 of the key. Nothing has been committed.';
  end if;
  select count(*) into rows from public.sairnlaw_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairnlaw_employee_auth
   where license_hash = lh and active = true
     and role = any (array['owner']);
  if rows > 0 and prov = 0 then
    raise exception
      'ABORTED: LAW-AUDIT-2026 would be left with credential rows and ZERO active provisioners (% row(s)). Delete EVERY row for this licence, or leave at least one active provisioner. Never a subset of the provisioners.', rows;
  end if;
  raise notice 'LAW-AUDIT-2026: % row(s), % active provisioner(s).', rows, prov;
  if not exists (
    select 1 from public.sairnlaw_employee_auth
     where license_hash = lh and employee_id = 'audit-owner'
       and role = 'owner' and active = true
       and pin_salt = '8d51f009a63f097683e1ebc2d8f26184') then
    raise exception 'ABORTED: audit-owner on LAW-AUDIT-2026 does not carry the PIN salt this file wrote, so the published PIN would not work. Nothing has been committed.';
  end if;
end $$;

do $$
declare
  lh   text;
  rows int;
  prov int;
begin
  lh := encode(digest('SEN-PINNACLE-2026', 'sha256'), 'hex');
  if lh <> '75bdc179a257a6688febcd88df11ab0efed12542eea6a8db29a3053ee817ac8f' then
    raise exception 'ABORTED: the license_hash literal for SEN-PINNACLE-2026 does not match sha256 of the key. Nothing has been committed.';
  end if;
  select count(*) into rows from public.sairnsenior_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairnsenior_employee_auth
   where license_hash = lh and active = true
     and role = any (array['owner']);
  if rows > 0 and prov = 0 then
    raise exception
      'ABORTED: SEN-PINNACLE-2026 would be left with credential rows and ZERO active provisioners (% row(s)). Delete EVERY row for this licence, or leave at least one active provisioner. Never a subset of the provisioners.', rows;
  end if;
  raise notice 'SEN-PINNACLE-2026: % row(s), % active provisioner(s).', rows, prov;
  if not exists (
    select 1 from public.sairnsenior_employee_auth
     where license_hash = lh and employee_id = 'demo-caregiver'
       and role = 'caregiver' and active = true
       and pin_salt = '6ad3e55b9c6bf6ccfe6c15890d330354') then
    raise exception 'ABORTED: demo-caregiver on SEN-PINNACLE-2026 does not carry the PIN salt this file wrote, so the published PIN would not work. Nothing has been committed.';
  end if;
end $$;

commit;

-- VERIFY (read-only). Expect three rows, each active with the role named above.
select 'SEN-AUDIT-2026' as licence, employee_id, role, active
  from public.sairnsenior_employee_auth
 where license_hash = encode(digest('SEN-AUDIT-2026', 'sha256'), 'hex')
   and employee_id = 'audit-owner';
select 'LAW-AUDIT-2026' as licence, employee_id, role, active
  from public.sairnlaw_employee_auth
 where license_hash = encode(digest('LAW-AUDIT-2026', 'sha256'), 'hex')
   and employee_id = 'audit-owner';
select 'SEN-PINNACLE-2026' as licence, employee_id, role, active
  from public.sairnsenior_employee_auth
 where license_hash = encode(digest('SEN-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id = 'demo-caregiver';
