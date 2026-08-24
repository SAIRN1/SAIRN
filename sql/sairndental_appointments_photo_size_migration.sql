-- sql/sairndental_appointments_photo_size_migration.sql
-- Run once in the Supabase SQL editor. Safe to re-run (idempotent).
--
-- ══ WHAT THIS FIXES ════════════════════════════════════════════════════════
-- public.dnt_appointments has carried a DB-level CHECK since it was created:
--
--     constraint dntap_data_size check (octet_length(data::text) <= 65536)
--
-- 64 KiB was right when an appointment was scheduling metadata. It stopped
-- being right the day self-scheduling with photo capture went live, and the
-- migration that was supposed to follow was never written. SAIRN-PLATFORM-
-- SESSION3 recorded that gap and called raising it "the single most important
-- thing to pick up next, before this reaches a real practice."
--
-- api/sairndental/public-book.js writes patient-submitted photos straight into
-- data.photos as base64 data URLs. A real phone photo, after the client's
-- compression, is a few hundred KB. A maximum-size booking is 19.2x over the
-- current ceiling -- and ONE maximum photo alone is already 19.2x over.
--
-- The failure mode is the bad one: a real patient submits a real photo, the
-- INSERT is rejected by the database, and the booking is lost. It compounds
-- with the separately-logged orphaned-patient-record bug on that same path,
-- because the patient row is written BEFORE the appointment row.
--
-- ══ HOW THE NEW NUMBER WAS DERIVED, NOT GUESSED ════════════════════════════
-- The bound is tied to the limits the code actually enforces, so the two
-- cannot drift apart silently. From api/_lib/dental-photo-validation.js:
--
--   MAX_PHOTOS                   = 3
--   MAX_PHOTOS_PAYLOAD_BYTES     = 1258291   (1.2 MiB, whole data URLs)
--   MAX_PATIENT_NOTES_JSON_BYTES = 8192
--
-- Measured worst case for octet_length(data::text), by building the largest
-- payload those limits permit and encoding it:
--
--   photos at the full budget ................... 1258291
--   JSON structure for the photos array .............. 19
--   all other appointment fields at max length ...... 491
--   patient_notes at its cap ....................... 8192
--                                                 ---------
--   worst case .................................... 1266993
--
-- NEW CEILING = MAX_PHOTOS_PAYLOAD_BYTES + 32768 = 1291059 bytes.
--
-- That is the photo budget plus 32 KiB for everything else, which leaves
-- ~24 KiB of real slack over the measured worst case and keeps the number
-- auditable: it is one constant plus one stated allowance, not a round figure
-- picked because it looked big enough. If MAX_PHOTOS_PAYLOAD_BYTES changes,
-- this must change with it -- see the drift check at the bottom.
--
-- ══ TWO PREREQUISITES THAT WERE FIXED IN THE SAME CHANGE ═══════════════════
-- A storage bound is only sound if every field it covers is itself bounded.
-- Two were not, and both are now capped in api/_lib/dental-photo-validation.js:
--
--   1. patient_notes had NO length check of any kind, on a fully
--      unauthenticated endpoint. Now capped at 8192 bytes of the JSON-ENCODED
--      value -- bytes, not characters, because one emoji is 4 UTF-8 bytes and
--      a control character becomes a 6-byte \uXXXX escape.
--   2. The photo budget counted only the base64 payload after "base64,". The
--      data-URL prefix was uncounted and its MIME subtype is unbounded by the
--      validating regex, so "data:image/<20000 chars>;base64,AAAA" passed.
--      The budget now counts the whole data URL.
--
-- Without those two, no number here would be a real bound.
--
-- ══ WHY ONLY THIS TABLE ════════════════════════════════════════════════════
-- The other eleven dnt_ tables keep their 64 KiB ceiling. None of them stores
-- an image; appointments is the only one on the photo path. Raising them all
-- "for consistency" would remove a guard that is doing its job.

-- ── The migration ─────────────────────────────────────────────────────────
-- Done as DROP + ADD ... NOT VALID + VALIDATE rather than a single ADD.
--
-- The new ceiling is strictly wider than the old one, so every existing row
-- already satisfies it and the validation scan cannot fail. The three-step
-- form is still worth using: a plain ADD CONSTRAINT holds ACCESS EXCLUSIVE for
-- the whole scan, while ADD ... NOT VALID takes that lock only briefly and the
-- separate VALIDATE takes the weaker SHARE UPDATE EXCLUSIVE, which does not
-- block concurrent reads or writes. On today's row counts the difference is
-- immaterial; the habit is what matters, and this file is the template the
-- next size migration will be copied from.

alter table public.dnt_appointments
  drop constraint if exists dntap_data_size;

alter table public.dnt_appointments
  add constraint dntap_data_size
  check (octet_length(data::text) <= 1291059) not valid;

alter table public.dnt_appointments
  validate constraint dntap_data_size;

-- ── Verify, do not assume ─────────────────────────────────────────────────
-- Run this after. It should return exactly one row showing the new ceiling.
-- A clean statement result is not evidence the constraint is what you think.
--
--   select conname,
--          pg_get_constraintdef(oid) as definition,
--          convalidated
--     from pg_constraint
--    where conrelid = 'public.dnt_appointments'::regclass
--      and conname  = 'dntap_data_size';
--
-- Expect: check ((octet_length((data)::text) <= 1291059)), convalidated = true.
--
-- Then confirm the real path end to end rather than trusting the DDL: submit a
-- booking through the public form with three photos near the client's size
-- target and check the row lands. A 400 from the endpoint means validation
-- rejected it (correct); a 500 or a lost booking means the constraint is still
-- biting and this migration did not take.

-- ── Drift check ───────────────────────────────────────────────────────────
-- This ceiling is derived from MAX_PHOTOS_PAYLOAD_BYTES in
-- api/_lib/dental-photo-validation.js. If that constant is ever raised and
-- this is not, bookings start failing at the database again with no code
-- change to point at. api/_lib/dental-photo-validation.test.js asserts the
-- relationship so the pair cannot drift silently.
