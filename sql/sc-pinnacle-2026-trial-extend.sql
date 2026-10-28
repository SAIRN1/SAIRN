-- hank b58, 2026-10-28: the SC-PINNACLE-2026 demo licence's expired 30-day trial, which is
-- blocking the Stedi key backfill, and which licence owns the one legacy Stedi row.
--
-- ══ READ THIS FIRST: THE TRIAL THAT EXPIRED IS NOT IN THE DATABASE ══════════════════════════
-- MEASURED LIVE 2026-10-28 (read only):
--   * public.license_keys has NO trial_ends_at column. Its columns are id, key, app_id,
--     shop_name, customer_email, stripe_customer_id, stripe_subscription_id, plan, status,
--     created_at and updated_at.
--   * SC-PINNACLE-2026: app_id sairncode, status active, plan demo, no Stripe subscription,
--     created 2026-08-01.
--   * The server has no trial gate for this licence. api/_lib/license.js reads trial_ends_at
--     only if the column exists, so the value is always null.
-- The "Your 30-day trial has ended" screen comes from sairncode.html checkTrialGate()
-- (around line 3481). It counts 30 days from localStorage['sc_trial_start'], which is written
-- in THAT BROWSER the first time anyone signs in there. It runs after every successful sign-in
-- and hides the app, so a Compliance Admin cannot reach the eligibility panel to re-save the
-- Stedi key.
--
-- NO SQL CAN EXTEND OR EXEMPT IT. The unblock is a browser step, on the machine and browser
-- used for the backfill:
--   1. Open SAIRNcode, open DevTools (F12), go to Console, and run:
--        localStorage.setItem('sc_trial_start', String(Date.now()))
--   2. Reload and sign in. The app now opens for 30 more days, in that browser only.
--   3. Do the backfill: docs/2026-10-15-hank-b15-stedi-backfill-step.md. Re-save the SAME
--      Stedi key in Eligibility, and compare the last 4 characters before and after.
--   4. Run PART 3 below and expect legacy_rows = 0. Only then clear SD_AUTH_SECRET_PREVIOUS.
-- A DURABLE exemption for demo licences, where checkTrialGate() skips plan = 'demo', is a
-- code change to sairncode.html. It is NOT made here; it needs a decision first.
--
-- PART 2 below is still real SQL, written for the day a server-side trial column exists. It
-- does nothing today and says so.

-- ── PART 1. LOOK FIRST: confirm the state above has not changed ───────────────────────────
select column_name
  from information_schema.columns
 where table_schema = 'public' and table_name = 'license_keys' and column_name = 'trial_ends_at';
-- expect: 0 rows. If this returns a row, the server-side trial now exists, and PART 2 applies.

select key, app_id, status, plan, created_at, (stripe_subscription_id is not null) as has_subscription
  from public.license_keys
 where key = 'SC-PINNACLE-2026';
-- expect: sairncode | active | demo | 2026-08-01 | false

-- ── PART 2. SERVER-SIDE EXEMPTION, only if the column exists (a no-op today) ──────────────
-- A demo licence is not a trial, so the fix is to clear the date rather than push it out:
-- a pushed-out date will expire again. This touches SC-PINNACLE-2026 alone and aborts if
-- anything else would change.
begin;
do $$
declare n int;
begin
  if not exists (select 1 from information_schema.columns
                  where table_schema = 'public' and table_name = 'license_keys'
                    and column_name = 'trial_ends_at') then
    raise notice 'NO-OP: license_keys has no trial_ends_at column; the only trial gate is client-side (see header).';
    return;
  end if;
  execute $q$update public.license_keys set trial_ends_at = null
              where key = 'SC-PINNACLE-2026' and app_id = 'sairncode' and plan = 'demo'$q$;
  get diagnostics n = row_count;
  if n > 1 then
    raise exception 'ABORTED: % rows matched SC-PINNACLE-2026; expected at most 1. Nothing has been committed.', n;
  end if;
  raise notice 'SC-PINNACLE-2026: trial_ends_at cleared on % row(s).', n;
end $$;
commit;

-- ── PART 3. WHICH LICENCE OWNS THE LEGACY STEDI ROW (and the census to re-run after) ──────
-- MEASURED LIVE 2026-10-28: exactly one legacy row, owned by SC-PINNACLE-2026 ITSELF:
--   license_hash fce80ce1...0e9ed, credential_id 'default', service 'stedi', ciphertext
--   length 90, written 2026-08-23, and 0 rows in the v2 format.
-- So the agency to call is the demo licence, and the trial step above is the whole blocker.
-- The query returns no plaintext and no ciphertext, only a length.
select c.license_hash,
       k.key                 as licence_key,
       coalesce(k.app_id, c.app_id) as app_id,
       k.status, k.plan,
       c.credential_id,
       e.k                   as service,
       length(e.v->>'enc')   as ciphertext_len,
       c.updated_at
  from public.sc_credentials c
  cross join lateral jsonb_each(coalesce(c.data, '{}'::jsonb)) as e(k, v)
  left join public.license_keys k
         on encode(digest(k.key, 'sha256'), 'hex') = c.license_hash
 where jsonb_typeof(e.v) = 'object'
   and e.v->>'enc' is not null
   and e.v->>'enc' not like 'v2.%'
 order by c.license_hash, c.credential_id, e.k;
-- before the backfill: 1 row (above). After it: 0 rows. updated_at on that credential row must
-- have moved, or the re-save did not land.

select count(*) as legacy_rows
  from public.sc_credentials c
  cross join lateral jsonb_each(coalesce(c.data, '{}'::jsonb)) as e(k, v)
 where jsonb_typeof(e.v) = 'object' and e.v->>'enc' is not null and e.v->>'enc' not like 'v2.%';
-- expect after the backfill: 0. Only then may SD_AUTH_SECRET_PREVIOUS be cleared.
