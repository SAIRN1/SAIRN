-- sql/restore_demo_pins_2026-09-29.sql
-- Restore the two demo credentials that stopped signing in.
-- SELECT first, then the UPSERT, then CONFIRM. Run in that order.
--
-- ── WHAT IS PRINTED HERE, AND WHAT IS NOT ────────────────────────────────
-- pin_hash and pin_salt were produced by the platform's OWN hashPin()
-- (api/_lib/auth.js:520 -- scrypt, 64-byte digest, 16-byte random salt) over
-- the value already in .demo-credentials.local.json, which is gitignored and
-- never committed. NO PIN, AND NO FRAGMENT OF ONE, APPEARS ANYWHERE IN THIS
-- FILE. Same shape and same reason as sql/demo_owner_credentials_2026-09-03.sql,
-- which states it at its own line 58.
--
-- license_hash is sha256(licence key), DERIVED by the same routine the
-- platform uses and not copied: the derivation was confirmed against a real
-- stored row on ALF-AUDIT-2026 on 2026-09-29 before this file was written.
--
-- ── TABLE AND COLUMN NAMES, VERIFIED AGAINST THE SCHEMA ──────────────────
--   public.sb_employee_auth            sql/sb_employee_auth_schema.sql:32
--   public.sairnvet_employee_auth      sql/sairnvet_employee_auth_schema.sql:43
-- Both carry: license_hash, employee_id, display_name, role, pin_hash,
-- pin_salt, active, failed_attempts, locked_until, created_at, updated_at,
-- and unique (license_hash, employee_id). NOTE sql/sb_employee_auth_schema.sql
-- declares its table WITHOUT the public. prefix; public is the default schema
-- and the qualified name below resolves to the same table.
--
-- ── WHY THE API CANNOT TELL YOU WHICH SIDE IS WRONG ──────────────────────
-- /login collapses "no such employee", "wrong PIN" and "credential inactive"
-- into ONE 401 INVALID_CREDENTIALS, deliberately: the query filters
-- &active=eq.true (api/sb-auth.js:196) and api/_lib/auth.js carries a dummy
-- salt purely to keep the cost constant when no row exists. Driven
-- 2026-09-29: sairn-demo-owner and a name that certainly does not exist
-- answered IDENTICALLY on both licences.
--
-- LOCKOUT IS RULED OUT, and that is measured rather than assumed: a locked
-- credential answers 429 LOCKED (api/sb-auth.js:201-202), and both licences
-- answered 401. The remaining candidates are a wrong stored PIN, a missing
-- row, or active = false. THE SELECT BELOW IS WHAT DISTINGUISHES THEM.

-- ═══ 1. SELECT -- which of the three is it? ══════════════════════════════
-- A row with active=false  -> the credential was deactivated, not re-PINned.
-- A row with active=true   -> the stored PIN disagrees with the local file.
-- NO row at all            -> never created, or removed. The UPSERT handles it.
select 'SB-PINNACLE-2026' as licence, employee_id, role, active,
       failed_attempts, locked_until, updated_at
  from public.sb_employee_auth
 where license_hash = '05c4e1e1fa05d6a1daeb294a5b2625c8d13929e017e2f504885cb48e9bc6cc4a'
   and employee_id  = 'sairn-demo-owner';

select 'SV-PINNACLE-2026' as licence, employee_id, role, active,
       failed_attempts, locked_until, updated_at
  from public.sairnvet_employee_auth
 where license_hash = '25413f81bcd80cce36e57a0d72c6547e5368a3f84a2aee2bf34bd90af533c740'
   and employee_id  = 'sairn-demo-owner';

-- ═══ 2. UPSERT -- set the PIN, and CREATE the row if it is missing ═══════
-- AN UPDATE ALONE WOULD SILENTLY MATCH NOTHING if the row does not exist,
-- and an update that matches nothing reports success. This is an INSERT with
-- ON CONFLICT on the (license_hash, employee_id) unique key, so it is correct
-- in both states and idempotent if re-run.
--
-- failed_attempts and locked_until are RESET as part of the restore: a PIN
-- that is right but a counter that is not still refuses, and leaving them
-- would make this fix look like it had not worked.
-- SB-PINNACLE-2026 (sairnbiz)
insert into public.sb_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt,
   active, failed_attempts, locked_until)
values ('05c4e1e1fa05d6a1daeb294a5b2625c8d13929e017e2f504885cb48e9bc6cc4a',
        'sairn-demo-owner',
        'SAIRN demo owner',
        'owner',
        '40e2e31ef8bf2a978769f00dbedd8f58d491fabb946bae1276a97d17e4c114a2608b6baaaf8ba0ab1422b3ff82ead3a55a54fb6fc3227d51dc09c439b2f967b9',
        'b3e42b2b73028bf867e7b0f342a45eac',
        true, 0, null)
on conflict (license_hash, employee_id) do update
   set pin_hash        = excluded.pin_hash,
       pin_salt        = excluded.pin_salt,
       active          = true,
       failed_attempts = 0,
       locked_until    = null,
       updated_at      = now();

-- SV-PINNACLE-2026 (sairnvet)
insert into public.sairnvet_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt,
   active, failed_attempts, locked_until)
values ('25413f81bcd80cce36e57a0d72c6547e5368a3f84a2aee2bf34bd90af533c740',
        'sairn-demo-owner',
        'SAIRN demo owner',
        'owner',
        '4f01816e078f4509dccd9ceca28551abb74c4eeb120dd8ec7d59b3d2328497413911ff1a6c4fa0f0356253ed1b24b200ba0f1f515652b77c6d7250b2bee731e2',
        'be2686ae4b21e803441a5731bdfaca7e',
        true, 0, null)
on conflict (license_hash, employee_id) do update
   set pin_hash        = excluded.pin_hash,
       pin_salt        = excluded.pin_salt,
       active          = true,
       failed_attempts = 0,
       locked_until    = null,
       updated_at      = now();

-- ═══ 3. CONFIRM -- one row per licence, active, counters clear ═══════════
-- Expect exactly one row from each, active = true, failed_attempts = 0,
-- locked_until null, and updated_just_now = true. A missing row here means
-- the insert did not run -- do not assume it did.
select 'SB-PINNACLE-2026' as licence, employee_id, role, active, failed_attempts,
       locked_until,
       (updated_at > now() - interval '10 minutes') as updated_just_now
  from public.sb_employee_auth
 where license_hash = '05c4e1e1fa05d6a1daeb294a5b2625c8d13929e017e2f504885cb48e9bc6cc4a'
   and employee_id  = 'sairn-demo-owner';

select 'SV-PINNACLE-2026' as licence, employee_id, role, active, failed_attempts,
       locked_until,
       (updated_at > now() - interval '10 minutes') as updated_just_now
  from public.sairnvet_employee_auth
 where license_hash = '25413f81bcd80cce36e57a0d72c6547e5368a3f84a2aee2bf34bd90af533c740'
   and employee_id  = 'sairn-demo-owner';

-- ═══ THEN, AND THIS IS THE REAL CONFIRMATION ════════════════════════════
--   python tools/demo_credentials_check.py
-- Both must move from WRONG-PIN to OK. The SQL above only proves the row
-- changed; only a sign-in proves the credential works.
