-- sql/2026-10-27-cody-b52-dnt-residue-removal.sql
-- ---------------------------------------------------------------------------
-- WHAT: removes the ONE row cody b52's live staff-write verification left on
-- the SAIRNdental DEMO licence DNT-PINNACLE-2026:
--   public.dnt_appointments  appointment_id AP-B52-LIVE-C68954
-- Status Declined, patient PT-DEMO-1 (an existing demo patient, so NO new
-- dnt_patients row was created), two random-byte test "photos" (~96 KB).
-- Enumeration: docs/live-residue/2026-10-27-cody-b52-dnt-staff-write.json.
--
-- It is DECLINED, so it holds no slot and appears in no pending queue; leaving
-- it is harmless. If service_role has no DELETE on this table the delete
-- below fails loudly and nothing is removed -- that is the correct outcome.
--
-- HOW TO RUN: step 1 alone; expect 1. Then step 2. Then step 3; expect 0.
-- No credential rows are touched.
-- ---------------------------------------------------------------------------

-- STEP 1: blast radius (read-only) -- expect 1
select count(*) as expect_1 from public.dnt_appointments
 where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
   and appointment_id = 'AP-B52-LIVE-C68954' and status = 'Declined';

-- STEP 2: removal
delete from public.dnt_appointments
 where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
   and appointment_id = 'AP-B52-LIVE-C68954' and status = 'Declined';

-- STEP 3: confirm -- expect 0
select count(*) as expect_0 from public.dnt_appointments
 where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
   and appointment_id = 'AP-B52-LIVE-C68954';
