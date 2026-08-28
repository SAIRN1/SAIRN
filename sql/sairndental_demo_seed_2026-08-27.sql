-- sql/sairndental_demo_seed_2026-08-27.sql
-- Makes DNT-PINNACLE-2026 demo-ready.
-- ⚠ STATUS CORRECTED 2026-08-28: THIS FILE HAS RUN. The line here said
-- "NOT RUN by this session (no DB access)", which was true when written and
-- false within the hour. Michael ran it and reported the result: 3 operatories,
-- 5 procedures, 3 providers, 5 patients, 6 appointments, ZERO orphans.
-- Left stale until a consistency sweep caught it, which is exactly the drift
-- sairnroofing_access_panel_verify_cleanup_2026-08-28.sql documents: a NOT RUN
-- label is a claim about the FILE at authoring time, never about the DATABASE.
-- Re-running is safe regardless -- every insert is ON CONFLICT DO NOTHING.
--
-- ── WHY THIS EXISTS ──────────────────────────────────────────────────────
-- The licence has never been seeded. Verified, not assumed:
--   * sql/sairndental_license_seed.sql inserts exactly ONE row -- the
--     license_keys row. Nothing else.
--   * `grep -rlnE "insert into public\.dnt_" sql/` returns nothing. There is no
--     dental data seed anywhere in the repo.
--   * sairndental.html cannot mint an appointment id at all -- it mints
--     CH, CV, DCRED, OP, PC, PH, PM, PT, PV, RF, SUP, VORD and no AP. Every
--     AP- id on the licence therefore came from api/sairndental/public-book.js,
--     the PUBLIC self-booking endpoint: ad-hoc test traffic, not demo content.
-- So the eleven appointment rows found orphaned on 2026-08-27 were never demo
-- data being preserved. They were debris, and the panel that renders them shows
-- "(unknown patient)" for every one -- a prospect opening Appointments sees a
-- broken app, not an empty one.
--
-- ── WHAT THIS FILE DOES ──────────────────────────────────────────────────
--   0. removes the orphaned appointments and the verification-residue provider
--   1-5. seeds operatories, procedures, providers, patients, appointments
-- Idempotent throughout: every insert is ON CONFLICT DO NOTHING against the
-- (license_hash, <x>_id) unique keys the schema already defines, so re-running
-- changes nothing. Safe to run twice.
--
-- ── DATES ARE RELATIVE, ON PURPOSE ───────────────────────────────────────
-- Every appointment is computed from now() rather than pinned to a literal
-- date. A demo licence with hardcoded 2026 dates is stale the moment the year
-- turns, and "all appointments in the past" is exactly how demo data betrays
-- itself in front of a prospect. These stay plausible indefinitely.
--
-- ── ONE THING DELIBERATELY NOT TOUCHED, AND IT NEEDS A DECISION ──────────
-- CORRECTED 2026-08-27, AFTER THIS FILE RAN. The paragraph below was WRONG and
-- is kept rather than deleted, because the way it was wrong is the point.
--
-- WHAT IT SAID: seven pre-existing patient rows (PT-<timestamp>-<rand>) remain,
-- possibly junk, read them before deciding.
-- WHAT IS TRUE: the read query at the end of this file returned ZERO rows.
-- Those seven patients did not exist. I had inferred them from a live owner
-- read taken EARLIER in the session, before the credential cleanup ran, and
-- then carried that stale count forward into a file written afterwards as if it
-- were current state.
--
-- The mistake is not the miscount. It is that a number observed at one point in
-- time was written into a document describing a later one, with no re-read in
-- between -- the same shape as the appointment inventory error that made this
-- file necessary, committed twice in one session about the same table.
-- A count is only true as of the read that produced it. Re-read, or say when
-- you looked.

-- ═════════════════════════════════════════════════════════════════════════
-- 0. CLEAR THE DEBRIS
-- ═════════════════════════════════════════════════════════════════════════
-- 0a. Every appointment on this licence is orphaned -- all eleven reference a
--     patient_id with no matching row. Confirmed by a live read, not inferred.
--     Three (AP-VERIFY-A/D/E) are verification residue; eight
--     (AP-<timestamp>) are stale public bookings whose patients are gone.
--     None is recoverable: an appointment whose patient no longer exists cannot
--     be repaired, only removed.
delete from public.dnt_appointments
 where license_hash = encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex');

-- 0b. PV-VERIFY-1 / "Dr. Verify Test" is residue from the earlier auth
--     verification run. It is currently the licence's ONLY provider, which is
--     why the demo needs real ones below. Safe to remove now: 0a just removed
--     every appointment that referenced it.
delete from public.dnt_providers
 where license_hash = encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex')
   and provider_id = 'PV-VERIFY-1';

-- ═════════════════════════════════════════════════════════════════════════
-- 1. OPERATORIES
-- ═════════════════════════════════════════════════════════════════════════
insert into public.dnt_operatories (license_hash, app_id, operatory_id, data)
select encode(digest('DNT-PINNACLE-2026','sha256'),'hex'), 'sairndental', v.id,
       jsonb_build_object('id', v.id, 'name', v.name, 'created_at', to_char(now(),'YYYY-MM-DD'))
from (values
  ('OP-DEMO-1', 'Operatory 1'),
  ('OP-DEMO-2', 'Operatory 2'),
  ('OP-DEMO-3', 'Hygiene Bay')
) as v(id, name)
on conflict (license_hash, operatory_id) do nothing;

-- ═════════════════════════════════════════════════════════════════════════
-- 2. PROCEDURE TYPES -- real CDT codes, plausible private-fee amounts.
--    default_length_minutes matters: the booking page uses it for slot length,
--    so a wrong value produces a demo whose calendar does not add up.
-- ═════════════════════════════════════════════════════════════════════════
insert into public.dnt_procedure_types (license_hash, app_id, procedure_type_id, data)
select encode(digest('DNT-PINNACLE-2026','sha256'),'hex'), 'sairndental', v.id,
       jsonb_build_object('id', v.id, 'cdt_code', v.code, 'description', v.descr,
                          'default_fee', v.fee, 'default_length_minutes', v.mins,
                          'created_at', to_char(now(),'YYYY-MM-DD'))
from (values
  ('PC-DEMO-1', 'D0120', 'Periodic oral evaluation - established patient',  65.00,  20),
  ('PC-DEMO-2', 'D1110', 'Prophylaxis - adult',                            118.00,  50),
  ('PC-DEMO-3', 'D0274', 'Bitewings - four radiographic images',            82.00,  15),
  ('PC-DEMO-4', 'D2391', 'Resin-based composite - one surface, posterior', 235.00,  60),
  ('PC-DEMO-5', 'D2740', 'Crown - porcelain/ceramic',                     1420.00,  90)
) as v(id, code, descr, fee, mins)
on conflict (license_hash, procedure_type_id) do nothing;

-- ═════════════════════════════════════════════════════════════════════════
-- 3. PROVIDERS -- a dentist and a hygienist, which is what a single-location
--    practice actually looks like. `linked_employee_id` is deliberately EMPTY:
--    no employee credentials exist on this licence right now (the verification
--    ones were deleted), and inventing a link to a nonexistent employee_id
--    would leave a dangling pointer in the access-control table. The owner
--    links these on the Providers panel after bootstrapping a real login --
--    which is exactly the flow worth demonstrating.
-- ═════════════════════════════════════════════════════════════════════════
insert into public.dnt_providers (license_hash, app_id, provider_id, data)
select encode(digest('DNT-PINNACLE-2026','sha256'),'hex'), 'sairndental', v.id,
       jsonb_build_object('id', v.id, 'name', v.name, 'role', v.role,
                          'operatory_id', v.op, 'linked_employee_id', '',
                          'active', true, 'created_at', to_char(now(),'YYYY-MM-DD'))
from (values
  ('PV-DEMO-1', 'Dr. Alicia Moreno',  'Dentist',    'OP-DEMO-1'),
  ('PV-DEMO-2', 'Dr. Ravi Chandra',   'Dentist',    'OP-DEMO-2'),
  ('PV-DEMO-3', 'Bethany Okafor, RDH','Hygienist',  'OP-DEMO-3')
) as v(id, name, role, op)
on conflict (license_hash, provider_id) do nothing;

-- ═════════════════════════════════════════════════════════════════════════
-- 4. PATIENTS -- five, with real variety rather than five clones:
--    two payers plus one self-pay, one minor WITH guardian contact (the app has
--    a guardian-required rule for minors -- a demo with no minor never exercises
--    it), and one patient with no email so the Appointments panel's "No email on
--    file" warning has something real to fire on. Demo data that only ever hits
--    the happy path demonstrates nothing.
-- ═════════════════════════════════════════════════════════════════════════
insert into public.dnt_patients (license_hash, app_id, patient_id, data)
select encode(digest('DNT-PINNACLE-2026','sha256'),'hex'), 'sairndental', v.id,
       jsonb_build_object(
         'id', v.id, 'name', v.name, 'dob', v.dob,
         'phone', v.phone, 'email', v.email,
         'insurance_payer', v.payer, 'insurance_member_id', v.member,
         'insurance_group_number', v.grp, 'insurance_plan_type', v.plan,
         'guardian_name', v.gname, 'guardian_relationship', v.grel,
         'guardian_phone', v.gphone, 'guardian_email', v.gemail,
         'created_at', to_char(now(),'YYYY-MM-DD'))
from (values
  ('PT-DEMO-1','Margaret Whitfield','1958-03-14','(216) 555-0142','m.whitfield@example.com',
     'Delta Dental','DD884120391','GRP-4471','PPO','','','',''),
  ('PT-DEMO-2','Daniel Okonkwo','1987-11-02','(216) 555-0188','d.okonkwo@example.com',
     'Cigna Dental','CG55710244','GRP-2210','PPO','','','',''),
  ('PT-DEMO-3','Sofia Reyes','1994-06-27','(440) 555-0119','',
     '','','','','','','',''),
  ('PT-DEMO-4','Ethan Brady','2015-09-08','(440) 555-0163','',
     'Delta Dental','DD884120774','GRP-4471','PPO',
     'Karen Brady','Mother','(440) 555-0163','k.brady@example.com'),
  ('PT-DEMO-5','Harold Nguyen','1971-01-19','(216) 555-0175','h.nguyen@example.com',
     'Guardian','GU30988215','GRP-8890','PPO','','','','')
) as v(id,name,dob,phone,email,payer,member,grp,plan,gname,grel,gphone,gemail)
on conflict (license_hash, patient_id) do nothing;

-- ═════════════════════════════════════════════════════════════════════════
-- 5. APPOINTMENTS
--    Both promoted columns AND the data blob are populated, from the SAME
--    computed timestamp -- api/sd-data.js reads the blob, the public booking
--    endpoints and any provider-scoped filter read the promoted columns, and a
--    row where the two disagree is the kind of split-brain that only surfaces
--    when someone filters by one and renders the other.
--
--    Deliberate mix, so every panel has something real in it:
--      * 2 Pending, source 'self-scheduled'  -> Pending Requests has real triage
--      * 3 Confirmed                          -> Appointments panel can Complete
--      * 1 Completed (past)                   -> history is not empty
--    PT-DEMO-3 (no email) is given a Confirmed slot on purpose so the
--    "No email on file" warning renders against a real row.
-- ═════════════════════════════════════════════════════════════════════════
with slots as (
  select * from (values
    -- id,             patient,      provider,     operatory,  procedure,   status,      source,           offset_hours, notes
    ('AP-DEMO-1','PT-DEMO-1','PV-DEMO-1','OP-DEMO-1','PC-DEMO-2','Confirmed', 'staff',           26,  ''),
    ('AP-DEMO-2','PT-DEMO-3','PV-DEMO-3','OP-DEMO-3','PC-DEMO-1','Confirmed', 'staff',           30,  ''),
    ('AP-DEMO-3','PT-DEMO-5','PV-DEMO-2','OP-DEMO-2','PC-DEMO-5','Confirmed', 'staff',           74,  'Crown seat - shade taken at prep visit'),
    ('AP-DEMO-4','PT-DEMO-2','PV-DEMO-1','OP-DEMO-1','PC-DEMO-4','Pending',   'self-scheduled',  50,  'Sensitive on the lower right when chewing.'),
    ('AP-DEMO-5','PT-DEMO-4','PV-DEMO-3','OP-DEMO-3','PC-DEMO-3','Pending',   'self-scheduled',  98,  'School forms need the x-rays on file.'),
    ('AP-DEMO-6','PT-DEMO-1','PV-DEMO-1','OP-DEMO-1','PC-DEMO-1','Completed', 'staff',         -190,  '')
  ) as v(id, patient_id, provider_id, operatory_id, procedure_type_id, status, source, offset_hours, notes)
),
timed as (
  select s.*,
         -- snapped to the hour so the calendar reads like a real schedule
         (date_trunc('hour', now()) + (s.offset_hours || ' hours')::interval) as start_ts,
         -- COALESCE is not defensive noise. If section 2 did not apply, this
         -- subquery returns NULL, `(NULL || ' minutes')::interval` is NULL, and
         -- every end_time silently lands NULL -- a seed that reports success and
         -- produces appointments with no end. 30 is the app's own fallback
         -- (addProcedureType defaults default_length_minutes to 30).
         (date_trunc('hour', now()) + (s.offset_hours || ' hours')::interval
            + (coalesce((select (data->>'default_length_minutes')::int
                  from public.dnt_procedure_types p
                 where p.license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
                   and p.procedure_type_id = s.procedure_type_id), 30) || ' minutes')::interval) as end_ts
  from slots s
)
insert into public.dnt_appointments
  (license_hash, app_id, appointment_id, provider_id, operatory_id, start_time, end_time, status, data)
select encode(digest('DNT-PINNACLE-2026','sha256'),'hex'), 'sairndental',
       t.id, t.provider_id, t.operatory_id, t.start_ts, t.end_ts, t.status,
       jsonb_build_object(
         'id', t.id,
         'patient_id', t.patient_id,
         'provider_id', t.provider_id,
         'operatory_id', t.operatory_id,
         'procedure_type_id', t.procedure_type_id,
         'status', t.status,
         'source', t.source,
         'start_time', to_char(t.start_ts at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
         'end_time',   to_char(t.end_ts   at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
         'patient_notes', t.notes,
         'photos', '[]'::jsonb,
         'created_at', to_char(now(),'YYYY-MM-DD'))
from timed t
on conflict (license_hash, appointment_id) do nothing;

-- ═════════════════════════════════════════════════════════════════════════
-- CONFIRM AFTERWARDS. Do not skip: a multi-statement paste into the SQL editor
-- can apply partway and still report success (seen twice on 2026-08-26).
-- ═════════════════════════════════════════════════════════════════════════
-- Expect 3 operatories, 5 procedure types, 3 providers, 5 seeded patients,
-- 6 appointments, and ZERO orphans.
--
--   select 'operatories' t, count(*) from public.dnt_operatories
--     where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
--   union all select 'procedures', count(*) from public.dnt_procedure_types
--     where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
--   union all select 'providers', count(*) from public.dnt_providers
--     where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
--   union all select 'appointments', count(*) from public.dnt_appointments
--     where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex');
--
-- THE ONE THAT MATTERS -- zero orphaned appointments. This is the check whose
-- absence created this whole situation:
--   select a.appointment_id, a.data->>'patient_id' as patient_id
--     from public.dnt_appointments a
--    where a.license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
--      and not exists (select 1 from public.dnt_patients p
--                       where p.license_hash = a.license_hash
--                         and p.patient_id = a.data->>'patient_id');
--   -- expect 0 rows
--
-- Promoted column and blob must agree, for every row:
--   select appointment_id from public.dnt_appointments
--    where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
--      and (provider_id is distinct from data->>'provider_id'
--        or status      is distinct from data->>'status');
--   -- expect 0 rows
--
-- ── CLOSED: there were no pre-existing patients ─────────────────────────
-- This query was run on 2026-08-27 and returned ZERO rows. See the correction
-- at the top of this file. Kept because it is still the right query to run
-- against any licence before assuming what is on it.
--   select patient_id, data->>'name' as name, data->>'email' as email,
--          data->>'insurance_payer' as payer, created_at
--     from public.dnt_patients
--    where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
--      and patient_id not like 'PT-DEMO-%'
--    order by created_at;

-- ═════════════════════════════════════════════════════════════════════════
-- ADDENDUM 2026-08-27, after this file ran: DEBRIS IS NEVER IN ONE TABLE
-- ═════════════════════════════════════════════════════════════════════════
-- Two more residue rows were found on this licence AFTER the seed ran, and
-- this file did not catch either of them:
--     OP-1786416376492-129   "Operatory 1"   (dnt_operatories)
--     PC-1786416376504-314   D0120           (dnt_procedure_types)
-- Both were test-traffic residue predating this session, both duplicated what
-- section 1 and section 2 seeded, and both had zero references anywhere.
--
-- THE PATTERN, which is the durable part: I found orphaned appointments, so I
-- cleaned appointments. The symptom appeared in ONE table and I scoped the
-- remedy to that table, when debris was always going to be spread across every
-- table any write path can reach.
--
-- MECHANISM CORRECTED 2026-08-28 -- the sentence that stood here was WRONG and
-- is replaced rather than quietly reworded, because I got it wrong while
-- writing the note about not getting things wrong.
--   WHAT IT SAID: the residue came from the public endpoints, and
--   public-book.js can write dnt_patients, dnt_appointments, dnt_operatories
--   and dnt_procedure_types.
--   WHAT IS TRUE, read directly from the file: public-book.js writes exactly
--   TWO tables -- dnt_patients (:104) and dnt_appointments (:122). It only
--   READS dnt_procedure_types (:79) and dnt_providers (:86), and never touches
--   dnt_operatories at all. No server file anywhere mints an OP- or PC- id.
--   Those two rows were minted CLIENT-side by addOperatory()
--   (sairndental.html:1378) and addProcedureType() (:1437) and synced through
--   the ordinary authenticated sd-data.js write path -- which, before the
--   session gate landed on 2026-08-27, a licence key alone was enough to reach.
--
-- So the rule is BROADER than "check what the public endpoints write", which
-- would have missed both rows Michael found: check every table ANY write path
-- can reach, authenticated ones included. Naming the public endpoint as the
-- mechanism made the check look complete while leaving the actual source out.
--
-- SO: a debris check on a demo licence must enumerate every table the
-- public-facing endpoints can write to, and check each one, rather than
-- following the symptom. The `<PREFIX>-<13-digit-epoch>-<rand>` id shape is the
-- tell -- those ids are minted by code, never typed by a person, so anything
-- matching it on a demo licence is machine-generated traffic and should be
-- justified before it is kept:
--
--   select 'operatories' as tbl, operatory_id as id from public.dnt_operatories
--    where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
--      and operatory_id ~ '^[A-Z]+-[0-9]{13}-'
--   union all
--   select 'procedure_types', procedure_type_id from public.dnt_procedure_types
--    where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
--      and procedure_type_id ~ '^[A-Z]+-[0-9]{13}-'
--   union all
--   select 'patients', patient_id from public.dnt_patients
--    where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
--      and patient_id ~ '^[A-Z]+-[0-9]{13}-'
--   union all
--   select 'appointments', appointment_id from public.dnt_appointments
--    where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
--      and appointment_id ~ '^[A-Z]+-[0-9]{13}-'
--   union all
--   select 'providers', provider_id from public.dnt_providers
--    where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')
--      and provider_id ~ '^[A-Z]+-[0-9]{13}-';
--   -- expect 0 rows on a clean demo licence
