-- sql/sairndental_public_booking_seed_2026-09-04.sql
--
-- Makes SAIRNdental's PUBLIC booking surface reachable for the first time.
-- Run once in the Supabase SQL editor. Safe to re-run (idempotent).
--
-- ══ WHY THIS EXISTS ════════════════════════════════════════════════════════
-- On 2026-09-04, after fixing nine fail-open reads in
-- api/sairndental/public-availability.js and public-book.js, those fixes could
-- not be verified end to end against production. The reason is worth writing
-- down, because it is a finding and not just an inconvenience:
--
--   resolveSlug() runs BEFORE all nine reads. Seven plausible slugs were tried
--   against the live endpoint and every one returned 404 UNKNOWN_SLUG. Then
--   `grep -rl booking_slug sql/` showed why: THREE files mention the column and
--   ALL THREE ARE SCHEMA. No seed anywhere in this repository has ever written
--   one.
--
-- So a whole patient-facing feature -- availability, booking, and the four
-- public endpoints built on them -- has no reachable practice on production.
-- Not broken; unreachable. That is exactly the shape the reachability checker
-- exists to catch in HTML, and nothing checks it for a database row.
--
-- ══ WHAT THIS DOES AND DOES NOT CREATE ═════════════════════════════════════
-- It creates the TWO things the demo seed left out and nothing else:
--   1. a dnt_settings row carrying the booking_slug and the list of procedure
--      types the practice is willing to be booked for publicly, and
--   2. dnt_provider_hours for one provider, because with no hours the
--      availability endpoint correctly returns zero slots and the test proves
--      nothing.
--
-- It DEPENDS ON sql/sairndental_demo_seed_2026-08-27.sql having been run --
-- providers PV-DEMO-*, procedure types PC-DEMO-* and operatories OP-DEMO-*
-- come from there. It does not recreate them, and the verification block at
-- the bottom refuses to pretend if they are absent.
--
-- ══ NO CREDENTIAL ROWS ═════════════════════════════════════════════════════
-- This file writes no *_employee_auth rows, so the recoverability guard
-- (tools/employee_auth_guard_check.py) has nothing to check here. Stated
-- rather than left for a reader to work out.
--
-- ══ A DEMO LICENCE, DELIBERATELY ═══════════════════════════════════════════
-- DNT-PINNACLE-2026 is the existing demo licence the rest of the dental demo
-- data already hangs off. No real practice's data is touched, and the slug is
-- named so nobody can mistake it for a customer's.

set search_path to public, extensions;

-- ---------------------------------------------------------------------------
-- 1. THE SETTINGS ROW -- the thing that makes the practice reachable at all.
-- ---------------------------------------------------------------------------
-- `booking_slug` is a REAL unique column, not a jsonb field: the public page
-- resolves a practice by it on every request. It is NOT a secret and must
-- never be confused with the licence key -- see the schema file's own header.
--
-- publicly_bookable_procedure_type_ids is the whitelist the listing mode
-- filters by. A crown (PC-DEMO-5, 90 min, $1,420) is deliberately NOT in it:
-- a practice publishes the routine appointments it is happy for a stranger to
-- take, not its longest chair-time procedure. That is the realistic shape, and
-- a seed that whitelisted everything would not exercise the filter at all.
insert into public.dnt_settings (license_hash, app_id, settings_id, booking_slug, data)
values (
  encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex'),
  'sairndental',
  'ST-DEMO-1',
  'pinnacle-dental-demo',
  jsonb_build_object(
    'id', 'ST-DEMO-1',
    'practice_name', 'Pinnacle Family Dental (demo)',
    'timezone', 'America/New_York',
    'publicly_bookable_procedure_type_ids',
      jsonb_build_array('PC-DEMO-1', 'PC-DEMO-2', 'PC-DEMO-3'),
    'created_at', to_char(now(), 'YYYY-MM-DD')
  )
)
on conflict (license_hash, settings_id) do update
  set booking_slug = excluded.booking_slug,
      data         = excluded.data,
      updated_at   = now();

-- ---------------------------------------------------------------------------
-- 2. PROVIDER HOURS -- without these the calendar is honestly empty.
-- ---------------------------------------------------------------------------
-- dnt_provider_hours has NO promoted provider_id column; provider_id lives
-- inside `data` and public-availability.js filters client-side. That is not an
-- oversight to fix here -- the endpoint's own comment records that filtering on
-- a nonexistent real column is what caused the silent zero-slots failure in the
-- first place. Match the shape the reader expects.
--
-- Times are plain 'HH:MM' strings, which is what the endpoint splits on.
-- Mon-Thu only, with a genuinely closed Friday: a seed where every day looks
-- identical cannot catch a day-of-week bug.
insert into public.dnt_provider_hours (license_hash, app_id, provider_hour_id, data)
select encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex'), 'sairndental', v.id,
       jsonb_build_object(
         'id', v.id,
         'provider_id', v.pv,
         'day_of_week', v.dow,
         'start_time', v.st,
         'end_time', v.en,
         'created_at', to_char(now(), 'YYYY-MM-DD')
       )
from (values
  ('PH-DEMO-1', 'PV-DEMO-1', 'Monday',    '09:00', '17:00'),
  ('PH-DEMO-2', 'PV-DEMO-1', 'Tuesday',   '09:00', '17:00'),
  ('PH-DEMO-3', 'PV-DEMO-1', 'Wednesday', '09:00', '13:00'),
  ('PH-DEMO-4', 'PV-DEMO-1', 'Thursday',  '09:00', '17:00'),
  ('PH-DEMO-5', 'PV-DEMO-3', 'Monday',    '08:00', '16:00'),
  ('PH-DEMO-6', 'PV-DEMO-3', 'Wednesday', '08:00', '16:00')
) as v(id, pv, dow, st, en)
on conflict (license_hash, provider_hour_id) do update
  set data = excluded.data, updated_at = now();

-- ---------------------------------------------------------------------------
-- 3. VERIFICATION -- run this after, and read it.
-- ---------------------------------------------------------------------------
-- Every count below must be non-zero. A zero on providers or procedure types
-- means sql/sairndental_demo_seed_2026-08-27.sql has NOT been run, and the
-- public endpoints will answer 200 with an empty list rather than an error --
-- which is precisely the "nothing to show" that reads like "nothing exists"
-- this whole line of work has been about.
--
--   select 'settings'    as what, count(*) from public.dnt_settings
--     where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
--       and booking_slug = 'pinnacle-dental-demo'
--   union all select 'provider_hours', count(*) from public.dnt_provider_hours
--     where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
--   union all select 'providers', count(*) from public.dnt_providers
--     where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
--   union all select 'procedure_types', count(*) from public.dnt_procedure_types
--     where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex');
--
-- Then, from anywhere:
--   POST https://sairn.vercel.app/api/sairndental/public-availability
--     {"slug":"pinnacle-dental-demo"}
-- must return 200 with providers and exactly THREE procedure types -- three,
-- not five, is the whitelist doing its job.
