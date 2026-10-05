-- sql/restore_sairnvet_demo_pin_2026-10-05.sql
-- Restore the ONE demo credential that is actually broken: SAIRNvet.
-- SELECT first, then the UPSERT, then the guard, then CONFIRM. In that order.
--
-- ═══ WHY THIS FILE EXISTS AND restore_demo_pins_2026-09-29.sql DOES NOT ═══
-- That file was never committed and MUST NOT BE RUN AS IT STANDS. It writes
-- TWO credentials, and the SAIRNbiz half would cause the outage it was
-- written to repair:
--
--   * its SAIRNbiz row's pin_hash/pin_salt recompute, under the platform's own
--     scryptSync(pin, salt, 64), to the PIN that docs/2026-09-03-demo-
--     credentials.md records as "DEAD 2026-09-25" (struck through in the
--     table).
--   * the SAIRNbiz credential WORKS RIGHT NOW. Driven 2026-10-05 against
--     https://sairn.vercel.app/api/sb-auth with the documented working PIN:
--     200, token issued.
--
--   So running it would overwrite a working credential with a dead one.
--
-- AND THE LOCAL FILE IS WHY, which matters for the next person who regenerates
-- this. The 2026-09-29 header says its hashes came from
-- .demo-credentials.local.json, and that is TRUE: apps[1].pin in that file
-- still holds the dead SAIRNbiz PIN. The value moved ON THE SERVER and the
-- local file was never updated. The SQL was a faithful copy of a stale source.
-- **Fix .demo-credentials.local.json before trusting it to mint another.**
--
-- SO THIS FILE TOUCHES ONLY SAIRNvet. Not "fixed by re-hashing SAIRNbiz from
-- the current PIN", which was the other option: SAIRNbiz needs no repair, and
-- rewriting a working credential to tidy up a file buys nothing and risks the
-- thing it is trying to protect.
--
-- ── WHAT IS PRINTED HERE, AND WHAT IS NOT ────────────────────────────────
-- pin_hash and pin_salt are carried over UNCHANGED from the 2026-09-29 file's
-- SAIRNvet row. They were produced by the platform's own hashPin()
-- (api/_lib/auth.js:520 -- scrypt, 64-byte digest, 16-byte random salt).
-- NO PIN, AND NO FRAGMENT OF ONE, APPEARS ANYWHERE IN THIS FILE.
--
-- VERIFIED 2026-10-05, not assumed, and in two directions:
--   * scryptSync(<the PIN at apps[3].pin in .demo-credentials.local.json>,
--     pin_salt, 64) == pin_hash below. The hash really is that PIN's.
--   * sha256('SV-PINNACLE-2026') == the license_hash below. The licence hash
--     is derived, not copied.
--
-- ── TABLE AND COLUMNS, VERIFIED AGAINST THE SCHEMA ───────────────────────
--   public.sairnvet_employee_auth   sql/sairnvet_employee_auth_schema.sql:43
-- Carries: license_hash, employee_id, display_name, role, pin_hash, pin_salt,
-- active, failed_attempts, locked_until, created_at, updated_at, and
-- unique (license_hash, employee_id).
--
-- ── WHY SAIRNvet CANNOT RECOVER ITSELF ───────────────────────────────────
-- `bootstrap` is permanently refused on this licence: it deliberately does not
-- filter on `active`, so a deactivated credential cannot be bootstrapped
-- around. Further accounts go through `setup`, which needs a signed-in
-- provisioner. A lost owner here is recoverable ONLY by direct database
-- access, which is what this file is.
--
-- ── CURRENT STATE, DRIVEN 2026-10-05 ─────────────────────────────────────
-- /api/sv-auth login with the documented PIN answered 401 INVALID_CREDENTIALS
-- (positive controls on the same probe: SAIRNbiz 200, StoneDesk 200, so the
-- probe itself works). A later attempt answered 429 LOCKED -- the earlier
-- failures pushed the counter over the threshold. The UPSERT below RESETS
-- failed_attempts and locked_until for that reason: a correct PIN behind a
-- tripped counter still refuses, and would make this fix look like it failed.

-- ═══ 1. SELECT -- which of the three states is it in? ════════════════════
-- A row with active = false -> deactivated, not re-PINned.
-- A row with active = true  -> the stored PIN disagrees with the local file.
-- NO row at all             -> never created, or removed. The UPSERT handles it.
select 'SV-PINNACLE-2026' as licence, employee_id, role, active,
       failed_attempts, locked_until, updated_at
  from public.sairnvet_employee_auth
 where license_hash = '25413f81bcd80cce36e57a0d72c6547e5368a3f84a2aee2bf34bd90af533c740'
   and employee_id  = 'sairn-demo-owner';

-- ═══ 2. UPSERT -- set the PIN, and CREATE the row if it is missing ═══════
-- AN UPDATE ALONE WOULD SILENTLY MATCH NOTHING if the row does not exist, and
-- an update that matches nothing reports success. This is an INSERT with
-- ON CONFLICT on the (license_hash, employee_id) unique key, so it is correct
-- in all three states above and idempotent if re-run.
--
-- ── ONE TRANSACTION, AND THE GUARD IS INSIDE IT ─────────────────────────
-- The push gate refused the 2026-09-29 file twice: once with no guard, and
-- once with a guard but NO TRANSACTION -- "a guard here could not roll back".
-- That is not a formality. Without begin/commit the upsert lands, THEN the
-- guard raises, and the write it was meant to prevent is already durable.
begin;

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

-- ═══ 3. RECOVERABILITY GUARD (PR 3.4) ═══════════════════════════════════
-- REQUIRED BY THE PUSH GATE ON ANY SQL THAT WRITES CREDENTIAL ROWS. Two end
-- states are safe and only two: zero rows for a licence (which re-arms
-- bootstrap and is RECOVERY, not lockout), or at least one ACTIVE row holding
-- the role that licence cannot lose.
--
-- THE ROLE IS THE APP'S OWN, read out of its endpoint rather than assumed:
--   sairnvet  api/sv-auth.js:110  PROVISIONING_ROLES = [owner]
--
-- THIS FILE CAN ONLY ADD AN ACTIVE OWNER -- the upsert sets role owner and
-- active true and removes nothing -- so the guard should never fire. It is
-- present because a guard that is only written when somebody expects it to
-- fire is a guard nobody has when they are wrong.
do $$
declare
  lh   text := '25413f81bcd80cce36e57a0d72c6547e5368a3f84a2aee2bf34bd90af533c740';   -- sha256(SV-PINNACLE-2026)
  rows int; prov int;
begin
  select count(*) into rows from public.sairnvet_employee_auth where license_hash = lh;
  select count(*) into prov from public.sairnvet_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);
  if rows > 0 and prov = 0 then
    raise exception
      'ABORTED: SV-PINNACLE-2026 would be left with % credential row(s) and ZERO active provisioners. Delete EVERY row for this licence, or leave at least one active provisioner. Never a subset.', rows;
  end if;
  raise notice 'SV-PINNACLE-2026 guard passed: % row(s), % active provisioner(s).', rows, prov;
end $$;

commit;

-- If the guard raised, NOTHING above was written -- the whole transaction
-- rolled back, and the CONFIRM below shows the old state rather than a
-- half-applied one.

-- ═══ 4. CONFIRM -- one row, active, counters clear ══════════════════════
-- Expect exactly one row, active = true, failed_attempts = 0, locked_until
-- null, updated_just_now = true. A missing row here means the insert did not
-- run -- do not assume it did.
select 'SV-PINNACLE-2026' as licence, employee_id, role, active, failed_attempts,
       locked_until,
       (updated_at > now() - interval '10 minutes') as updated_just_now
  from public.sairnvet_employee_auth
 where license_hash = '25413f81bcd80cce36e57a0d72c6547e5368a3f84a2aee2bf34bd90af533c740'
   and employee_id  = 'sairn-demo-owner';

-- ═══ THEN, AND THIS IS THE REAL CONFIRMATION ════════════════════════════
--   python tools/demo_credentials_check.py
-- The SQL above only proves the ROW changed. Only a sign-in proves the
-- credential works, and that is the thing SAIRNvet's third of the
-- click-through audit is blocked on.
