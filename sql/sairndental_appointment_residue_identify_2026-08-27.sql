-- sql/sairndental_appointment_residue_identify_2026-08-27.sql
-- READ-ONLY. Nothing here deletes, updates or grants anything.
--
-- PURPOSE: identify the provenance of the three dnt_appointments rows left on
-- DNT-PINNACLE-2026 -- AP-VERIFY-A, AP-VERIFY-D, AP-VERIFY-E -- BEFORE anything
-- is deleted. Same discipline as the credential cleanup: identify by a live
-- read, never by guessing from the naming pattern.
--
-- ── WHY THE PATTERN IS NOT EVIDENCE, WITH THIS SESSION AS THE PROOF ──────
-- My own verification run named its provider `PV-VERIFY-A` (letter) and its
-- appointment `AP-VERIFY-1` (digit) -- inconsistently, in the same script, five
-- minutes apart. The earlier auth-verification run left `PV-VERIFY-1` (digit).
-- So "letters are his, digits are theirs" is exactly the inference that would
-- be wrong here. Read the rows.
--
-- ── WHAT I CAN STATE WITHOUT A READ, AND WHAT I CANNOT ───────────────────
-- CAN: my run issued exactly ONE appointment write, `AP-VERIFY-1`, and the
-- live provider-scoped read immediately afterwards returned exactly
-- ['AP-VERIFY-1']. I never issued A, D or E in any call. They are not mine.
-- CANNOT: what they actually are. That needs a read, and the verification
-- credentials have now been deleted, so there is no session to read with.
-- Re-bootstrapping to get one would mint another owner credential on a
-- PHI-holding licence -- the exact mistake this session already made once.
-- Hence SQL, run by someone with DB access, rather than a new credential.
--
-- ── THE LIKELY ANSWER, FLAGGED AS UNCONFIRMED ───────────────────────────
-- The earlier auth-verification run's cleanup file
-- (sql/sairndental_verify_auth_cleanup_2026-08-27.sql) deletes ONLY its two
-- credential rows. It never touched dnt_* data at all, and it did leave
-- `PV-VERIFY-1` behind in dnt_providers -- confirmed present in a live read
-- during this session. So an earlier run leaving appointment rows behind is
-- consistent with what is already known. That is a hypothesis for query 1 to
-- confirm or kill, not a conclusion.

-- ─────────────────────────────────────────────────────────────────────────
-- 1. THE DECISIVE QUERY. What do these rows point at, and when were they made?
--    A row referencing PV-VERIFY-1 is the earlier verification run's.
--    A row referencing a real demo provider is app-generated demo data and
--    should NOT be deleted.
--    created_at also settles it independently: this session's writes all
--    landed within a few minutes of each other; anything materially older
--    predates this session entirely.
-- ─────────────────────────────────────────────────────────────────────────
select
  appointment_id,
  provider_id,                       -- promoted column
  data->>'patient_id'  as patient_id,
  data->>'status'      as status,
  start_time,
  created_at,
  updated_at,
  octet_length(data::text) as data_bytes   -- a photo-bearing real booking is
                                           -- orders of magnitude larger than a
                                           -- scripted fixture; another
                                           -- independent provenance signal
from public.dnt_appointments
where license_hash = encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex')
order by created_at;

-- ─────────────────────────────────────────────────────────────────────────
-- 2. CONTEXT: do the patients and providers these rows reference still exist?
--    A row pointing at a patient_id that no longer exists is orphaned and is
--    almost certainly verification residue -- the patient rows PT-VERIFY-1 and
--    PT-VERIFY-2 were deleted in the cleanup that just ran.
-- ─────────────────────────────────────────────────────────────────────────
select
  a.appointment_id,
  a.provider_id,
  (select count(*) from public.dnt_providers p
     where p.license_hash = a.license_hash and p.provider_id = a.provider_id) as provider_row_exists,
  a.data->>'patient_id' as patient_id,
  (select count(*) from public.dnt_patients pt
     where pt.license_hash = a.license_hash and pt.patient_id = a.data->>'patient_id') as patient_row_exists
from public.dnt_appointments a
where a.license_hash = encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex')
order by a.appointment_id;

-- ─────────────────────────────────────────────────────────────────────────
-- 3. Confirm AP-VERIFY-1 really is gone -- i.e. that the cleanup's appointment
--    delete matched nothing because the row was never there under that id,
--    rather than silently failing. If this returns a row, the earlier delete
--    did not apply and that is a different problem.
-- ─────────────────────────────────────────────────────────────────────────
select appointment_id, created_at
from public.dnt_appointments
where license_hash = encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex')
  and appointment_id = 'AP-VERIFY-1';        -- expect 0 rows

-- ── WHAT TO DO WITH THE ANSWER ──────────────────────────────────────────
-- If query 1 shows all three referencing PV-VERIFY-1 (or an orphaned
-- provider/patient), they are verification residue and a delete by exact
-- appointment_id is safe -- but write that delete against the ids the query
-- ACTUALLY returned, not against the three ids at the top of this file, which
-- came to me second-hand and have not been read by anyone writing SQL.
--
-- If any of them references a live demo provider and a live demo patient, that
-- one is demo data. Leave it. It predates both verification runs, in the same
-- category as the seven PT-<timestamp> patient rows already flagged.
--
-- ── ONE OPEN QUESTION THIS RAISES ───────────────────────────────────────
-- My cleanup file listed AP-VERIFY-1 as the only appointment created, drawn
-- from my own run. It was correct about my run and incomplete about the table.
-- I never read dnt_appointments as the owner -- only as the scoped provider,
-- which by design returns just that provider's rows. So my enumeration was of
-- what I created, not of what was there. That is the narrow lesson: a cleanup
-- file's inventory should come from an UNSCOPED read of the table, and a
-- scoped read cannot serve as one no matter how carefully it is checked.
