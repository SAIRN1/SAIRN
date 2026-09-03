-- sql/demo_owner_credentials_2026-09-03.sql
-- ONE OWNER LOGIN PER DEMO/TEST LICENCE, ACROSS EVERY SAIRN APP
--
-- Run once in the Supabase SQL editor. Every statement is an idempotent upsert
-- on (license_hash, employee_id); safe to re-run, and it touches no row it does
-- not name.
--
-- ── WHY THIS EXISTS ────────────────────────────────────────────────────────
-- Nobody has ever held credentials for any SAIRN app's demo or test licence.
-- Every verification session for weeks has hit the same wall, and the work logs
-- record it repeatedly: "both licenses already have an owner account
-- bootstrapped from an earlier session and I don't have those PIN credentials".
-- The result is that live click-through verification has been substituted for,
-- worked around, or skipped -- and tonight two production bugs were found ONLY
-- because one licence (SB-TEST-2026) happened to have a documented PIN.
--
-- ── STATE MEASURED 2026-09-03 BEFORE WRITING THIS, NOT ASSUMED ─────────────
-- Every licence below was probed with `bootstrap`, which answers definitively:
-- 409 ALREADY_PROVISIONED means credential rows exist, 200 means there were
-- none, 401 INVALID_LICENSE means the licence key itself was never seeded.
--
--   13 licences   had credentials already, with nobody holding the PINs
--    3 licences   had NO CREDENTIAL ROWS AT ALL -- LAW-PINNACLE-2026,
--                 SDN-PINNACLE-2026 and SEN-PINNACLE-2026. Nobody could sign in
--                 to those three at all, and nothing had noticed.
--    1 licence    RF-AUDIT-2026, is NOT PROVISIONED -- the key does not exist,
--                 so sql/sairnroofing_audit_license_seed.sql was never run. Its
--                 row is included below anyway and is INERT until that seed
--                 runs; it does not error, it simply belongs to a licence hash
--                 nothing will ever present.
--
-- ── SAFE ONLY BECAUSE EVERY LICENCE HERE IS A DEMO ─────────────────────────
-- Checked in the seed files, not assumed from the names: every key below is
-- `plan = 'demo'` with a `*.example` customer_email. The "PINNACLE" keys are
-- named after the fictional demo company, not after a customer.
--
-- TWO LICENCES ARE DELIBERATELY ABSENT:
--   SD-PINNACLE-2026  -- appears in NO seed file and holds REAL NAMED ACCOUNTS
--                        (`cmonsul`, a named person; `owner`, Michael). A
--                        published PIN cannot safely live on it. That judgement
--                        is not new -- sql/stonedesk_recovery_admin_seed.sql
--                        made it, and moved StoneDesk's verification credential
--                        to SD-AUDIT-2026 for exactly this reason.
--   RF-PINNACLE-2026  -- also in no seed file, and the open-work index records
--                        real employee rows and a recoverability incident on
--                        it. Use RF-AUDIT-2026 once its licence seed is run.
--
-- ── THE PINS ARE PUBLISHED, ON PURPOSE ─────────────────────────────────────
-- Same trade sql/stonedesk_recovery_admin_seed.sql states plainly: a credential
-- nobody can find is a credential nobody uses, and the whole cost of the last
-- several weeks has been verification not happening. These licences hold no
-- real business data, so a published PIN costs nothing -- and that precondition
-- is the entire basis for it. THE MOMENT ANY LICENCE BELOW IS GIVEN TO A REAL
-- CUSTOMER OR LOADED WITH REAL DATA, ITS ROW HERE MUST BE DELETED AND ITS PIN
-- ROTATED.
--
-- ── HASHES ARE REAL, AND WERE ROUND-TRIPPED BEFORE BEING WRITTEN ───────────
-- pin_hash/pin_salt were produced by the platform's OWN hashPin()
-- (api/_lib/auth.js, scrypt, 64-byte, 16-byte random salt) and then passed back
-- through its OWN verifyPin(): correct PIN -> true, wrong PIN -> false, for
-- every row. So each row is indistinguishable from one the API created, and
-- that claim rests on a check rather than on the shape of the SQL.
--
-- license_hash values are sha256 of the licence key, computed with the same
-- hashLicense() api/_lib/license.js uses, not typed by hand.
--
-- ── ROLE ───────────────────────────────────────────────────────────────────
-- `owner` everywhere except SAIRNcode, whose provisioning role is `admin` and
-- which has no `owner` role at all. That is exactly the trap CLAUDE.md records:
-- "SAIRNcode's is `admin`, not `owner`. A guard that hardcodes `owner` passes
-- SAIRNcode clean forever while checking nothing." Read off each app's own
-- ROLES_BY_APP, not assumed.
--
-- ── WHAT IT DOES NOT DO ────────────────────────────────────────────────────
-- It does not delete or deactivate anything. Existing accounts on these
-- licences keep working; this adds one more, so nothing anybody is already
-- using breaks. Adding a provisioning-role account also makes each licence
-- SAFER against the deactivate-to-zero trapdoor, which blocks removing the last
-- active provisioner and is unaffected by adding one.

-- ONE TRANSACTION. The seventeen inserts and the guard below land together or
-- not at all: a guard that cannot roll back what it just objected to is a
-- notice, not a guard, and tools/employee_auth_guard_check.py refuses the file
-- without one for exactly that reason.
begin;

-- stonedesk  --  SD-AUDIT-2026
insert into public.sd_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '8f1610119858d53f7deee8f975adf501b0ed1ee6dd57c674399743da7d6b76ea',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'owner',
  'cb4de14a21adf0cc846ffbe0075f18db472158e1a59170edae81690dd7235e45cd4ba5e8c4349231905657f287c888a60180fd73cd0eb73b9ab2a585c5a4a01d',
  '75fbcb8e68ea32ed040012f5c8c2bcdc',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- stonedesk  --  SD-PARTNER-2026
insert into public.sd_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '0b42ea8d3d3b094e83feb088ef4839248e7d58db0bbe0416f3264fa6baa296b7',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'owner',
  'cc1e553599b489572ff55742e9cb8e9b3deb0e54d0606456e6e7be50f12db1dabbd5ea28569e96f690565fd10c76c9928b3ce5f07da8a2cc52eb8a298dac8668',
  '43577a4288848862966431d991b0d246',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- sairnbiz  --  SB-TEST-2026
insert into public.sb_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '87e7f2ee131c924eaa3bd282c9c207962d499dff151a00990d83482d291288fc',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'owner',
  '2060ac113ba5e987dccf7661280cffe7cad610f04a7784e9587b690fe585f21096b0562d02389379fc6908fac685f90b6eb431a9b2ce58242f108b8f805b53aa',
  '47b2292518ab83b48a9a9b64331442db',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- sairnbiz  --  SB-PINNACLE-2026
insert into public.sb_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '05c4e1e1fa05d6a1daeb294a5b2625c8d13929e017e2f504885cb48e9bc6cc4a',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'owner',
  '2867eb8e66ba98069b2cb16b9bc6a51d09b6b28cef9503053b67baae34bdae541c13acf0ab19044d7d3077ba2916e03605a32340c232a6ad16b9b9fdfe2a5b35',
  '4ca134bbb67ee26ef0293aecbe5b110c',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- sairngrounds  --  GRD-DEMO-2026
insert into public.grd_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '482766e1699964503e913c54b3f3b9c946c4024c014d75f49da12228bf666603',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'owner',
  'ebf70ecc4f887d748fd0615fc244b408557fcf4131e25b35ae557982c22d6529020b58844952615e69ab43b0b3e799b3ffee3474c62a1e0995f24663fa173646',
  '977f0a7d53c9f43cec0767999539bd7c',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- sairnscape  --  SCP-DEMO-2026
insert into public.scp_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  'c0a2acd922a66c034ec9f15ef89c49a825a78315076ed76d78c2de2fc5aca583',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'owner',
  'a161ca0e73f9c439e94c24fb89a50655ba70a47de8c5613e3a72f691ba03a0f5c39e04c0187234fcc488aa1d48d63c52b45c7af4f0ec59df8785cbd2ed460eca',
  '7848da27a2e53e7a38f3219211f0ccdb',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- sairncare  --  ALF-TEST-2026
insert into public.sairncare_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '6dd308f1270f2bd66d5be5f8815c09007390b16e7846bd2b6f27f65f8209c3dd',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'owner',
  'a8257448b4e6197d6c787eea1cc50eff5c7021b684f6e6f8bd8a863ec94f13b527a6b373b3cf975356bc7a0dee3521f882ebd7923e1e1d0841b1a28be9d01f31',
  '7c7dd5074aac7209d72e65c145faf269',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- sairnlaw  --  LAW-TEST-2026
insert into public.sairnlaw_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '7f3af3fb178dd299d686312431ef59d3f33e066d73db835c21cc25292c927198',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'owner',
  '6e63ac403d59b62793866756d2f68a544bd868eb7c75c78c19fd485ba7dd64047ca5f9246b9c7306f554d47d526ca61ac8f0dd29dca8711aa2489838ff61da7f',
  '0bd1c0c5c7108743c997360a9a9eb46a',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- sairnlaw  --  LAW-PINNACLE-2026
insert into public.sairnlaw_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '56c82eb727d6a71f1012d7fcf432bd44df099e70dc38de67698bd0c6366f374c',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'owner',
  'c97aa9f92244930f4035f1efa72202c32c88c1c4c9785b054ebc339dad26df95364dc4793de56d12d231e95936e3d8bc7147bd4b00988d664d848acaa9a50a43',
  '87ed35b4a27e799f4541c88d2b0b7192',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- sairndental  --  DNT-PINNACLE-2026
insert into public.sairndental_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  'df727f0be9ee424db34982787acc3ce4b48985529900326effe1be612f3e0f81',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'owner',
  'b90bbe8c9c7f7a7c22a41488ee77b34fcd6954d82b3a14f4d1c4c35b4454948b74e19a44bae88b7525b8a4b2f7b4bc9bf8623dba14b401c284f54631344989be',
  'e927611a84d7cc5b79a67538be1e8127',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- sairndesign  --  SDN-PINNACLE-2026
insert into public.sairndesign_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '91e03f656a7f2921df92aa01014b56454d7281c7ded1482444a664f0a713098c',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'owner',
  '457bc77dc330c9cf6e263f63117aadd2939d4a029f0a09ebe1a1c359753982dd3faad96f3523f6c381e99441c9cf430a274949f787f3a798b5ee59d8815cff0a',
  'a3b39ed03a8d2c0b0a004bf78a0d3c17',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- sairnlegacy  --  LEG-PINNACLE-2026
insert into public.sairnlegacy_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '6ad056108272393300476e38b5af5aa8138522c735d4789092e2236dba4448c8',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'owner',
  '623c3dddea8026081b93462e2c9a883c30420c7bc6e70a48a253c62b161d96580f558d3599269bd9a1420bdf98791f713c15477b7af3b14ca65ea5b68cb6a96d',
  'd6908921df0912671432f69ca6d7feb4',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- sairnmechanical  --  MECH-PINNACLE-2026
insert into public.sairnmechanical_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '6b08224ff1553f51cae487321265dcd99a599784eca3afe089e4fafdd3619b32',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'owner',
  '1861dfd6cb269f430027291fc2f94547b9c56e9280236736ab3bcd4d8642470b99c468c0edd9de9ab50da84c10056e52873c13a0e1967f291a9c5da9e1209156',
  'a57e85b55a2cfb0e0aa02652e0c3c930',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- sairnsenior  --  SEN-PINNACLE-2026
insert into public.sairnsenior_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '75bdc179a257a6688febcd88df11ab0efed12542eea6a8db29a3053ee817ac8f',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'owner',
  '63b6c23f165dce215fbad4a055ea63c2b7e04a27e54307aff7daab28381028a479e47692a9ad4b38f6c7452a764d035237d741ecaa5fcdae90ecbd4f347a9f89',
  '210a82f47b02f7ffe976af4e18975e53',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- sairnroofing  --  RF-AUDIT-2026
insert into public.sairnroofing_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '5a6a73bceb61845e6ef67210dfe6f5edd32b9fc18e07bab32fdefcdc05f2ae7e',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'owner',
  '4a1cbbbee3949c6b00a9db055a26e6e59cf3cce5c3852e2a32adf4965ee8f0fd19f711c00bf3af8b46f0bb49bd2ee6236dbc15b9cb4056e3190cd676f1df1a80',
  '59f6005905b5ad9379c7919e45f436aa',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- sairnbuild  --  BLD-PINNACLE-2026
insert into public.sairnbuild_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '4d70f83c4b3ed5d13218543e24b0e06f163d5546f6d1f9ffeed45b6c0d55a63d',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'owner',
  '9046e51818988766a9985ba017e24b63c52dfeb068865e5a289d7436486a01b0c45a9d9910b53e8981bbbe7cf0538629d703155a8aa1c04b1dc590d51c464a03',
  '9b16396d0dd986f482623e4de429b471',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- sairncode  --  SC-PINNACLE-2026
insert into public.sairncode_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  'fce80ce1bc131249e98a7caf1235bc769ce703331775e4ba1c870c65c8a0e9ed',
  'sairn-demo-owner',
  'SAIRN Demo Owner',
  'admin',
  'e6495130e757f91640d87aea6371799c3785a5090f5adc478f87f6050923e470f8705ca006e2696d274c13355c6c1a7c930a7d974a7f862de7745d6344b01861',
  'f2698cd5133c4a5de5752bd0193df149',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- ── RECOVERABILITY GUARD ───────────────────────────────────────────────────
-- Required by CLAUDE.md of any SQL that writes credential rows, and enforced by
-- tools/employee_auth_guard_check.py as check 2 of the push hook. It exists
-- because a licence with credential rows and ZERO rows that are both `active`
-- and hold a provisioning role is UNRECOVERABLE THROUGH THE API: `bootstrap`
-- refuses 409 while any row exists, and `setup` and `set_active` both need an
-- active provisioner. RF-PINNACLE-2026 sat in that state and nothing noticed.
--
-- THIS FILE ONLY ADDS ACTIVE OWNERS, so it cannot create that state -- which is
-- exactly why the guard should pass rather than be skipped. A guard that is
-- only written when somebody fears it will fail is not a guard.
--
-- THE ROLE ARRAY IS PER APP. SAIRNcode's provisioning role is `admin` and it has
-- no `owner` role at all; a guard hardcoding `owner` would pass SAIRNcode clean
-- forever while checking nothing. Read off each app's own ROLES_BY_APP.
--
-- Run this LAST, after the inserts above.
do $$
declare
  lh   text;
  rows int;
  prov int;
  bad  text := '';
begin
  lh := encode(digest('SD-AUDIT-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sd_employee_auth where license_hash = lh;
  select count(*) into prov from public.sd_employee_auth
   where license_hash = lh and active = true and role = any (array['owner','admin']);
  if rows > 0 and prov = 0 then bad := bad || ' SD-AUDIT-2026(' || rows || ' rows, 0 provisioners)'; end if;
  raise notice 'SD-AUDIT-2026: % row(s), % active provisioner(s).', rows, prov;

  lh := encode(digest('SD-PARTNER-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sd_employee_auth where license_hash = lh;
  select count(*) into prov from public.sd_employee_auth
   where license_hash = lh and active = true and role = any (array['owner','admin']);
  if rows > 0 and prov = 0 then bad := bad || ' SD-PARTNER-2026(' || rows || ' rows, 0 provisioners)'; end if;
  raise notice 'SD-PARTNER-2026: % row(s), % active provisioner(s).', rows, prov;

  lh := encode(digest('SB-TEST-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sb_employee_auth where license_hash = lh;
  select count(*) into prov from public.sb_employee_auth
   where license_hash = lh and active = true and role = any (array['owner','hr']);
  if rows > 0 and prov = 0 then bad := bad || ' SB-TEST-2026(' || rows || ' rows, 0 provisioners)'; end if;
  raise notice 'SB-TEST-2026: % row(s), % active provisioner(s).', rows, prov;

  lh := encode(digest('SB-PINNACLE-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sb_employee_auth where license_hash = lh;
  select count(*) into prov from public.sb_employee_auth
   where license_hash = lh and active = true and role = any (array['owner','hr']);
  if rows > 0 and prov = 0 then bad := bad || ' SB-PINNACLE-2026(' || rows || ' rows, 0 provisioners)'; end if;
  raise notice 'SB-PINNACLE-2026: % row(s), % active provisioner(s).', rows, prov;

  lh := encode(digest('GRD-DEMO-2026', 'sha256'), 'hex');
  select count(*) into rows from public.grd_employee_auth where license_hash = lh;
  select count(*) into prov from public.grd_employee_auth
   where license_hash = lh and active = true and role = any (array['owner','superintendent']);
  if rows > 0 and prov = 0 then bad := bad || ' GRD-DEMO-2026(' || rows || ' rows, 0 provisioners)'; end if;
  raise notice 'GRD-DEMO-2026: % row(s), % active provisioner(s).', rows, prov;

  lh := encode(digest('SCP-DEMO-2026', 'sha256'), 'hex');
  select count(*) into rows from public.scp_employee_auth where license_hash = lh;
  select count(*) into prov from public.scp_employee_auth
   where license_hash = lh and active = true and role = any (array['owner','crew_lead']);
  if rows > 0 and prov = 0 then bad := bad || ' SCP-DEMO-2026(' || rows || ' rows, 0 provisioners)'; end if;
  raise notice 'SCP-DEMO-2026: % row(s), % active provisioner(s).', rows, prov;

  lh := encode(digest('ALF-TEST-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sairncare_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairncare_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);
  if rows > 0 and prov = 0 then bad := bad || ' ALF-TEST-2026(' || rows || ' rows, 0 provisioners)'; end if;
  raise notice 'ALF-TEST-2026: % row(s), % active provisioner(s).', rows, prov;

  lh := encode(digest('LAW-TEST-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sairnlaw_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairnlaw_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);
  if rows > 0 and prov = 0 then bad := bad || ' LAW-TEST-2026(' || rows || ' rows, 0 provisioners)'; end if;
  raise notice 'LAW-TEST-2026: % row(s), % active provisioner(s).', rows, prov;

  lh := encode(digest('LAW-PINNACLE-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sairnlaw_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairnlaw_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);
  if rows > 0 and prov = 0 then bad := bad || ' LAW-PINNACLE-2026(' || rows || ' rows, 0 provisioners)'; end if;
  raise notice 'LAW-PINNACLE-2026: % row(s), % active provisioner(s).', rows, prov;

  lh := encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sairndental_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairndental_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);
  if rows > 0 and prov = 0 then bad := bad || ' DNT-PINNACLE-2026(' || rows || ' rows, 0 provisioners)'; end if;
  raise notice 'DNT-PINNACLE-2026: % row(s), % active provisioner(s).', rows, prov;

  lh := encode(digest('SDN-PINNACLE-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sairndesign_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairndesign_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);
  if rows > 0 and prov = 0 then bad := bad || ' SDN-PINNACLE-2026(' || rows || ' rows, 0 provisioners)'; end if;
  raise notice 'SDN-PINNACLE-2026: % row(s), % active provisioner(s).', rows, prov;

  lh := encode(digest('LEG-PINNACLE-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sairnlegacy_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairnlegacy_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);
  if rows > 0 and prov = 0 then bad := bad || ' LEG-PINNACLE-2026(' || rows || ' rows, 0 provisioners)'; end if;
  raise notice 'LEG-PINNACLE-2026: % row(s), % active provisioner(s).', rows, prov;

  lh := encode(digest('MECH-PINNACLE-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sairnmechanical_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairnmechanical_employee_auth
   where license_hash = lh and active = true and role = any (array['owner','admin']);
  if rows > 0 and prov = 0 then bad := bad || ' MECH-PINNACLE-2026(' || rows || ' rows, 0 provisioners)'; end if;
  raise notice 'MECH-PINNACLE-2026: % row(s), % active provisioner(s).', rows, prov;

  lh := encode(digest('SEN-PINNACLE-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sairnsenior_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairnsenior_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);
  if rows > 0 and prov = 0 then bad := bad || ' SEN-PINNACLE-2026(' || rows || ' rows, 0 provisioners)'; end if;
  raise notice 'SEN-PINNACLE-2026: % row(s), % active provisioner(s).', rows, prov;

  lh := encode(digest('RF-AUDIT-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sairnroofing_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairnroofing_employee_auth
   where license_hash = lh and active = true and role = any (array['owner','admin']);
  if rows > 0 and prov = 0 then bad := bad || ' RF-AUDIT-2026(' || rows || ' rows, 0 provisioners)'; end if;
  raise notice 'RF-AUDIT-2026: % row(s), % active provisioner(s).', rows, prov;

  lh := encode(digest('BLD-PINNACLE-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sairnbuild_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairnbuild_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);
  if rows > 0 and prov = 0 then bad := bad || ' BLD-PINNACLE-2026(' || rows || ' rows, 0 provisioners)'; end if;
  raise notice 'BLD-PINNACLE-2026: % row(s), % active provisioner(s).', rows, prov;

  lh := encode(digest('SC-PINNACLE-2026', 'sha256'), 'hex');
  select count(*) into rows from public.sairncode_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairncode_employee_auth
   where license_hash = lh and active = true and role = any (array['admin']);
  if rows > 0 and prov = 0 then bad := bad || ' SC-PINNACLE-2026(' || rows || ' rows, 0 provisioners)'; end if;
  raise notice 'SC-PINNACLE-2026: % row(s), % active provisioner(s).', rows, prov;

  if bad <> '' then
    raise exception
      'ABORTED: these licences would be left with credential rows and ZERO active provisioners:%. '
      'Delete EVERY row for such a licence, or leave at least one active '
      'provisioner. Never a subset of the provisioners.', bad;
  end if;
  raise notice 'Guard passed for all 17 licences.';
end $$;

commit;

-- ── CONFIRM IT LANDED ──────────────────────────────────────────────────────
-- Run these SEPARATELY, not as one paste. The Supabase editor reports success
-- for the statements it did run, so a partial apply looks identical to a full
-- one -- the failure mode sql/sairnroofing's 2026-08-26 cleanup actually hit.
--
-- 1. One row per licence, role as expected, active true:
--      select 'stonedesk' app, employee_id, role, active from public.sd_employee_auth where employee_id = 'sairn-demo-owner'
--      union all select 'sairnbiz', employee_id, role, active from public.sb_employee_auth where employee_id = 'sairn-demo-owner'
--      union all select 'sairngrounds', employee_id, role, active from public.grd_employee_auth where employee_id = 'sairn-demo-owner'
--      union all select 'sairnscape', employee_id, role, active from public.scp_employee_auth where employee_id = 'sairn-demo-owner'
--      union all select 'sairncare', employee_id, role, active from public.sairncare_employee_auth where employee_id = 'sairn-demo-owner'
--      union all select 'sairnlaw', employee_id, role, active from public.sairnlaw_employee_auth where employee_id = 'sairn-demo-owner'
--      union all select 'sairndental', employee_id, role, active from public.sairndental_employee_auth where employee_id = 'sairn-demo-owner'
--      union all select 'sairndesign', employee_id, role, active from public.sairndesign_employee_auth where employee_id = 'sairn-demo-owner'
--      union all select 'sairnlegacy', employee_id, role, active from public.sairnlegacy_employee_auth where employee_id = 'sairn-demo-owner'
--      union all select 'sairnmechanical', employee_id, role, active from public.sairnmechanical_employee_auth where employee_id = 'sairn-demo-owner'
--      union all select 'sairnsenior', employee_id, role, active from public.sairnsenior_employee_auth where employee_id = 'sairn-demo-owner'
--      union all select 'sairnroofing', employee_id, role, active from public.sairnroofing_employee_auth where employee_id = 'sairn-demo-owner'
--      union all select 'sairnbuild', employee_id, role, active from public.sairnbuild_employee_auth where employee_id = 'sairn-demo-owner'
--      union all select 'sairncode', employee_id, role, active from public.sairncode_employee_auth where employee_id = 'sairn-demo-owner';
--
--    Expect 17 rows (two licences each for stonedesk, sairnbiz and sairnlaw).
--
-- 2. Then through the DEPLOYED API, which is the only real proof -- a clean
--    insert is not evidence the app accepts it. One example; the full list of
--    keys and PINs is in docs/2026-09-03-demo-credentials.md:
--
--      curl -s -X POST https://sairn.vercel.app/api/scp-auth \
--        -H 'Content-Type: application/json' \
--        -H 'Authorization: Bearer SCP-DEMO-2026' \
--        -d '{"action":"login","employee_id":"sairn-demo-owner","pin":"73018452"}'
--
--    200 with role "owner" and a token  -> this file has been run
--    401 INVALID_CREDENTIALS            -> it has not
--
-- ── CLEAN-UP STILL OWED ────────────────────────────────────────────────────
-- The 2026-09-03 state probe bootstrapped an owner called
-- `zz-state-probe-do-not-use` on the three licences that had no credentials at
-- all (LAW-PINNACLE-2026, SDN-PINNACLE-2026, SEN-PINNACLE-2026), because
-- `bootstrap` is the only probe that can distinguish "no rows" from "rows I
-- cannot open" and it creates a row when the answer is the former. Those three
-- are DEACTIVATED through the API rather than deleted, once this file has run
-- and `sairn-demo-owner` exists to deactivate them with -- a licence must never
-- pass through zero active provisioners.
