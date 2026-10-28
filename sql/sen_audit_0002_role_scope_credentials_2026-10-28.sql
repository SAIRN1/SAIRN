-- sql/sen_audit_0002_role_scope_credentials_2026-10-28.sql
--
-- CONCEPT. A second SAIRNsenior audit licence, SEN-AUDIT-0002, with one credential
-- for each sairnsenior role and two fixture caregiver rows. It exists so the
-- DEPLOYED role scope of sen_caregivers (H1 #965) can be read live, role by
-- role, with `python tools/sairn_field_scope_check.py --live`.
--
-- WRITTEN AND RUN BY cc b62 ON MICHAEL'S INSTRUCTION ("provision a new SEN audit
-- license with role-scoped accounts ... write the SQL, rehearse it, run it for
-- real"). It copies two existing files:
--   - sql/mint_sen_audit_2026.sql for the licence row (`on conflict do nothing`);
--   - sql/audit_owner_and_demo_caregiver_credentials_2026-10-20.sql for the
--     credential rows: the platform's own hashPin(), a PR 3.4 recoverability
--     guard, and a salt check that proves each published PIN is the one stored.
--
-- WHY A NEW LICENCE AND NOT SEN-AUDIT-2026.
--   - SEN-AUDIT-2026 is the payroll probe's licence. It holds permanent
--     sen_visits writes (that table has no delete verb).
--   - It also holds three credentials: audit-owner, hank-b27-caregiver and
--     hank-b49-caregiver (measured 2026-10-28).
--   - A live role-scope read needs a roster in which every row is KNOWN.
--     Otherwise a caregiver seeing "its own record only" cannot be told apart
--     from "the only record there is".
--   - This licence holds exactly the two fixture rows below.
--
-- WHY THE DIGITS ARE 0002. Two rules fix the key's shape:
--   - tools/audit_licence.py AUDIT_KEY_RE is ^[A-Z]{2,6}-AUDIT-\d{4}$;
--   - sairnsenior.html accepts only keys that start SEN-, DEMO- or SAIRN-.
-- SEN-AUDIT-2026 is taken, so the four digits are a SERIAL: this is the second
-- SEN audit licence. They are not a year, and nothing expires.
--
-- ── THE ACCOUNTS. THE PINS ARE PUBLISHED ON PURPOSE ────────────────────────
--   licence SEN-AUDIT-0002 (app sairnsenior, plan demo)
--   fs-owner       owner        PIN 74816982
--   fs-billing     billing      PIN 52958575
--   fs-scheduler   scheduler    PIN 54401975
--   fs-coordinator coordinator  PIN 34513907
--   fs-caregiver   caregiver    PIN 70654769
-- The reason, and the condition, are the same as in the 2026-10-20 file. An
-- *-AUDIT-* licence exists to be read and written by tests, and it holds no
-- customer data. The day it holds a real person's record, rotate every PIN.
--
-- HOW THE HASHES WERE MADE.
--   - Each PIN went through api/_lib/auth.js hashPin(): scrypt, 64-byte key,
--     16-byte random salt.
--   - Each hash was passed back through its own verifyPin(). The PIN returned
--     true and 00000000 returned false, for all five.
--   - license_hash is sha256(key). The guard recomputes it from the key, so a
--     typo in the literal is caught.
--   - PROVISIONING_ROLES, read from api/sen-auth.js: ['owner'].
--
-- FIXTURE ROWS (sen_caregivers):
--   - CG-FS-SELF belongs to fs-caregiver.
--   - CG-FS-PEER belongs to fs-peer, an employee with no credential.
-- Every value is synthetic and says so.
--
-- IF RUN TWICE: no new rows are created. The same hashes, salts and fixture data
-- are written again (ON CONFLICT DO UPDATE), and the licence row is left exactly
-- as it is. If any guard fails, the whole transaction rolls back and nothing is
-- committed.
-- ---------------------------------------------------------------------------

begin;

insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
values ('SEN-AUDIT-0002', 'active', 'audit@sairnsenior.example', 'sairnsenior', 'demo', null)
on conflict (key) do nothing;

insert into public.sairnsenior_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values ('f179514cf3acba9f6626ceb8f9e9b65c34eed3ec181b44dc4c27881b2417165c', 'fs-owner', 'Field-Scope Owner', 'owner',
  '3fa966b046ec75cda91dc50f6ebee714e18f0530731cf7efb6ed8d762bc60cc377596da4d2053dd4f0c963a5ddf61a45cc3ad4247a2037eb51d3809e51fef5fa',
  'c491ec932a053178d1cf6a5ca24fbeac', true)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash, pin_salt = excluded.pin_salt,
      role = excluded.role, active = true;

insert into public.sairnsenior_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values ('f179514cf3acba9f6626ceb8f9e9b65c34eed3ec181b44dc4c27881b2417165c', 'fs-billing', 'Field-Scope Billing', 'billing',
  '75f2348236b77d1bbed2ccf2186ecfa069151c6776ea6ed817410f85c82f60b4f0b17e41e410d759877c908d8c4240891c945b432bde90449602cb806bce3487',
  '6fee9a34cfd8ab8f58f8e68c93e0ceae', true)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash, pin_salt = excluded.pin_salt,
      role = excluded.role, active = true;

insert into public.sairnsenior_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values ('f179514cf3acba9f6626ceb8f9e9b65c34eed3ec181b44dc4c27881b2417165c', 'fs-scheduler', 'Field-Scope Scheduler', 'scheduler',
  'f22999cb870d08791792793ffca7abf92ac991f86e614fed31695cdaf2b73106f47cdaf52356843deb852f8dbfb34e30bcbd640091265ec0984fec2f38dfa32b',
  '901d61858bdcd10ed7d145b32b9cb81d', true)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash, pin_salt = excluded.pin_salt,
      role = excluded.role, active = true;

insert into public.sairnsenior_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values ('f179514cf3acba9f6626ceb8f9e9b65c34eed3ec181b44dc4c27881b2417165c', 'fs-coordinator', 'Field-Scope Coordinator', 'coordinator',
  'cdc59f8ac19f2ea7716a9a678db97cf2fc6b287515b723aaea770095d6efe9222f73c9a7ebf3e95dab85279f12812161919dc3ddd5559c7e7572eee9d19fa68c',
  '92edb9a655d37d14521afa04b9f99901', true)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash, pin_salt = excluded.pin_salt,
      role = excluded.role, active = true;

insert into public.sairnsenior_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values ('f179514cf3acba9f6626ceb8f9e9b65c34eed3ec181b44dc4c27881b2417165c', 'fs-caregiver', 'Field-Scope Caregiver', 'caregiver',
  '67508fc7fd691451b3ff16d34930e2ef80fb5157b0e7e19a2a9ca091f9a706a69fade4a7070da482add6a699107fd0ce86c22a540326b86b520171f44e819594',
  '08bbea7ba5488b2ff96cb75e998a5ff2', true)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash, pin_salt = excluded.pin_salt,
      role = excluded.role, active = true;

insert into public.sen_caregivers (license_hash, app_id, caregiver_id, data)
values ('f179514cf3acba9f6626ceb8f9e9b65c34eed3ec181b44dc4c27881b2417165c', 'sairnsenior', 'CG-FS-SELF', jsonb_build_object(
    'name', 'ZZ Field-Scope Self', 'phone', '000-555-0101', 'cpr_expiry', '2099-01-01',
    'bgcheck_date', '2099-01-02', 'status', 'active', 'notes', 'ZZ FIELD-SCOPE FIXTURE SELF -- not a person',
    'aide_type', 'STNA', 'program', 'PASSPORT', 'state_caregiver_id', 'ZZ-FS-SELF',
    'employee_id', 'fs-caregiver', 'branch_id', 'ZZ-FS-BRANCH')),
       ('f179514cf3acba9f6626ceb8f9e9b65c34eed3ec181b44dc4c27881b2417165c', 'sairnsenior', 'CG-FS-PEER', jsonb_build_object(
    'name', 'ZZ Field-Scope Peer', 'phone', '000-555-0102', 'cpr_expiry', '2099-01-01',
    'bgcheck_date', '2099-01-02', 'status', 'active', 'notes', 'ZZ FIELD-SCOPE FIXTURE PEER -- not a person',
    'aide_type', 'STNA', 'program', 'PASSPORT', 'state_caregiver_id', 'ZZ-FS-PEER',
    'employee_id', 'fs-peer', 'branch_id', 'ZZ-FS-BRANCH'))
on conflict (license_hash, caregiver_id) do update set data = excluded.data, updated_at = now();

do $$
declare
  lh   text;
  rows int;
  prov int;
  cgs  int;
begin
  lh := encode(digest('SEN-AUDIT-0002', 'sha256'), 'hex');
  if lh <> 'f179514cf3acba9f6626ceb8f9e9b65c34eed3ec181b44dc4c27881b2417165c' then
    raise exception 'ABORTED: the license_hash literal does not match sha256(SEN-AUDIT-0002). Nothing committed.';
  end if;
  if not exists (select 1 from public.license_keys
                  where key = 'SEN-AUDIT-0002' and app_id = 'sairnsenior' and status = 'active') then
    raise exception 'ABORTED: SEN-AUDIT-0002 is not an active sairnsenior licence. Nothing committed.';
  end if;
  select count(*) into rows from public.sairnsenior_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairnsenior_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);
  if rows > 0 and prov = 0 then
    raise exception 'ABORTED: SEN-AUDIT-0002 would have % credential row(s) and ZERO active provisioners. Delete EVERY row for this licence, or leave at least one active provisioner. Nothing committed.', rows;
  end if;
  if not (exists (select 1 from public.sairnsenior_employee_auth where license_hash = lh and employee_id = 'fs-owner' and role = 'owner' and active and pin_salt = 'c491ec932a053178d1cf6a5ca24fbeac')
      and exists (select 1 from public.sairnsenior_employee_auth where license_hash = lh and employee_id = 'fs-billing' and role = 'billing' and active and pin_salt = '6fee9a34cfd8ab8f58f8e68c93e0ceae')
      and exists (select 1 from public.sairnsenior_employee_auth where license_hash = lh and employee_id = 'fs-scheduler' and role = 'scheduler' and active and pin_salt = '901d61858bdcd10ed7d145b32b9cb81d')
      and exists (select 1 from public.sairnsenior_employee_auth where license_hash = lh and employee_id = 'fs-coordinator' and role = 'coordinator' and active and pin_salt = '92edb9a655d37d14521afa04b9f99901')
      and exists (select 1 from public.sairnsenior_employee_auth where license_hash = lh and employee_id = 'fs-caregiver' and role = 'caregiver' and active and pin_salt = '08bbea7ba5488b2ff96cb75e998a5ff2')) then
    raise exception 'ABORTED: a credential does not carry the salt this file wrote, so its published PIN would not work. Nothing committed.';
  end if;
  select count(*) into cgs from public.sen_caregivers where license_hash = lh;
  if cgs <> 2 then
    raise exception 'ABORTED: SEN-AUDIT-0002 has % sen_caregivers rows, not exactly the 2 fixtures; the live own-row check needs a fully known roster. Nothing committed.', cgs;
  end if;
  raise notice 'SEN-AUDIT-0002: % credential row(s), % active provisioner(s), % fixture caregiver row(s).', rows, prov, cgs;
end $$;

commit;
