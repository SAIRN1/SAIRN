// api/sairndental/public-book.js
// Genuinely public, unauthenticated endpoint -- no license key anywhere in
// this file, same as public-availability.js. Real, atomic double-booking
// prevention is the Postgres EXCLUDE constraints
// (sql/sairndental_availability_booking_schema.sql) firing on THIS
// function's own insert -- a 23P01 exclusion_violation maps to a clean
// 409 SLOT_TAKEN below, not trusted to an application-level pre-check
// that could itself race.
//
// New bookings always land as status:'Pending' -- never auto-confirmed
// (design spec's firm decision: an anonymous, unauthenticated submitter
// must never be able to permanently lock a real slot without staff
// review).

const { resolveSlug, checkAndIncrementRateLimit, readRows } = require('../_lib/dental-public');
const { validatePhotosPayload, validatePatientNotes } = require('../_lib/dental-photo-validation');
// One implementation of the minor/guardian rule, shared with api/sd-data.js's
// generic dnt_patients write. It used to live in this file alone, which is how
// the rule ended up enforced on one server path and not the other.
const { guardianProblem, isMinorDob } = require('../_lib/dental-guardian');
const dntLocation = require('../_lib/dnt-location');

function supabaseHeaders(extra) {
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  return Object.assign({ apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' }, extra || {});
}
function rest(path) {
  return process.env.SUPABASE_URL + '/rest/v1/' + path;
}
function newId(prefix) {
  return prefix + '-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'POST only' } }); return; }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) { res.status(500).json({ error: { message: 'Server configuration error' } }); return; }

  try {
    // Rate-limit check first -- fail fast, before any DB work.
    const rl = await checkAndIncrementRateLimit(req, 60, 5); // 5 booking attempts per hour per IP
    // A store we could not reach is NOT the same answer as a limit that was
    // exceeded. Saying "too many requests" for an unreachable database is a
    // wrong reason given confidently, and it hides an outage as user error.
    if (rl.unavailable) {
      console.error('SAIRNdental public-book: rate-limit store unavailable -- refusing rather than allowing an uncounted request');
      res.status(503).json({ error: { code: 'UNAVAILABLE', message: 'Booking is temporarily unavailable -- please call the office or try again shortly' } });
      return;
    }
    if (!rl.allowed) { res.status(429).json({ error: { code: 'RATE_LIMITED', message: 'Too many booking attempts -- please call the office or try again later' } }); return; }

    const body = req.body || {};
    const slug = body.slug;
    const patient = body.patient || {};
    const providerId = body.provider_id, procedureTypeId = body.procedure_type_id, startTime = body.start_time;
    const photos = body.photos;
    const patientNotes = typeof body.patient_notes === 'string' ? body.patient_notes.trim() : '';
    if (!slug || !patient.name || !patient.dob || !patient.phone || !providerId || !procedureTypeId || !startTime) {
      res.status(400).json({ error: { message: 'slug, patient (name/dob/phone), provider_id, procedure_type_id, start_time are required' } });
      return;
    }

    // ── A MINOR NEEDS A GUARDIAN HERE TOO (2026-09-04) ────────────────────
    // sairndental.html's Add Patient form has always refused to save a minor
    // without a guardian name and at least one guardian contact method, and a
    // comment at rcReachable() asserted it as a property of the system:
    // "this form already enforces that -- a minor cannot be saved without a
    // guardian phone or email."
    //
    // TRUE OF THAT FORM, FALSE OF THE SYSTEM. This endpoint is the other way
    // in -- public, unauthenticated, and the one a parent actually uses -- and
    // it created the patient row with no guardian fields at all. The record
    // did not merely lack them; the object written at the bottom of this file
    // did not contain the keys.
    //
    // Two consequences, neither visible from the response. A paediatric
    // patient existed with no guardian contact, so rcReachable() fell back to
    // whatever phone number was typed into a public form -- possibly the
    // child's. And the practice believed the rule was enforced, because the
    // form they look at every day does enforce it.
    //
    // Refusing matches the in-app rule exactly rather than inventing a second,
    // looser one for the public path. A parent booking for their child is the
    // ordinary case here, so asking is expected rather than an obstacle.
    const guardian = body.guardian || {};
    const guardianGap = guardianProblem({ dob: patient.dob, guardian: guardian });
    if (guardianGap) {
      res.status(400).json({ error: { code: 'GUARDIAN_REQUIRED', message: guardianGap } });
      return;
    }

    const photosCheck = validatePhotosPayload(photos);
    if (!photosCheck.ok) {
      res.status(400).json({ error: { code: photosCheck.code, message: photosCheck.message } });
      return;
    }

    // patient_notes was trimmed and stored with NO length check of any kind,
    // on a fully unauthenticated endpoint. dnt_appointments' size constraint
    // is derived from these limits, and a bound over an unbounded field is
    // not a bound -- so this cap is a prerequisite of that migration, not a
    // separate nicety. See sql/sairndental_appointments_photo_size_migration.sql.
    const notesCheck = validatePatientNotes(patientNotes);
    if (!notesCheck.ok) {
      res.status(400).json({ error: { code: notesCheck.code, message: notesCheck.message } });
      return;
    }

    const licenseHash = await resolveSlug(slug);
    if (!licenseHash) { res.status(404).json({ error: { code: 'UNKNOWN_SLUG', message: 'Booking link not found' } }); return; }

    const headers = supabaseHeaders();

    const procRes = await fetch(rest('dnt_procedure_types?license_hash=eq.' + encodeURIComponent(licenseHash) + '&procedure_type_id=eq.' + encodeURIComponent(procedureTypeId) + '&select=data'), { headers });
    const procRows = await readRows(procRes, 'dnt_procedure_types');
    const proc = procRows && procRows[0] && procRows[0].data;
    if (!proc) { res.status(404).json({ error: { code: 'UNKNOWN_PROCEDURE', message: 'Procedure type not found' } }); return; }
    const lengthMin = Number(proc.default_length_minutes) || 30;
    const endTime = new Date(new Date(startTime).getTime() + lengthMin * 60000).toISOString();

    const providerRes = await fetch(rest('dnt_providers?license_hash=eq.' + encodeURIComponent(licenseHash) + '&provider_id=eq.' + encodeURIComponent(providerId) + '&select=data'), { headers });
    const providerRows = await readRows(providerRes, 'dnt_providers');
    const provider = providerRows && providerRows[0] && providerRows[0].data;
    if (!provider) { res.status(404).json({ error: { code: 'UNKNOWN_PROVIDER', message: 'Provider not found' } }); return; }
    const operatoryId = provider.operatory_id || '';

    // Match an existing patient by EXACT name+dob+phone only -- never
    // fuzzy -- to avoid accidentally attaching a stranger's booking to
    // the wrong patient's record. No match -> create a new patient.
    const patientsRes = await fetch(rest('dnt_patients?license_hash=eq.' + encodeURIComponent(licenseHash) + '&select=data,patient_id'), { headers });
    const patientsRows = await readRows(patientsRes, 'dnt_patients');
    const matched = (patientsRows || []).find((p) => p.data && p.data.name === patient.name && p.data.dob === patient.dob && p.data.phone === patient.phone);
    // ── THE PATIENT ROW IS NOT WRITTEN YET (2026-09-03) ──────────────────
    // It used to be written HERE, before the appointment. That created an
    // ORPHAN PATIENT RECORD on every booking that then failed -- and the most
    // common failure is the 409 slot race two people hit on purpose by
    // clicking the same popular time.
    //
    // This is an ANONYMOUS, UNAUTHENTICATED endpoint. Anyone who can load the
    // booking page could therefore mint an unbounded number of dnt_patients
    // rows carrying name, date of birth, phone and email, simply by racing a
    // slot or retrying a failing one. AND THE PRACTICE CANNOT DELETE THEM:
    // dnt_patients carries no delete grant (revoked platform-wide by
    // sql/unused_delete_grant_revoke_2026-08-24.sql), so every orphan is
    // permanent PHI debris in a dental record system.
    //
    // Cleaning up afterwards is therefore NOT AVAILABLE as a fix -- there is
    // no delete to roll back with. The only fix is not to create the row until
    // the thing that can fail has succeeded, so the order is reversed: claim
    // the SLOT first, then record the patient.
    let patientId = matched ? matched.patient_id : newId('PT');

    const appointmentId = newId('AP');
    // Self-scheduled bookings are stamped with a location for the same
    // reason staff writes are (api/_lib/dnt-location.js): attribution can
    // only be captured at write time. The public booking page resolves one
    // slug to one license and cannot yet name a location, so every booking
    // lands on the implicit default until dnt_settings is split per
    // location -- held work, logged in SAIRN-BACKLOG.md.
    const appointmentData = dntLocation.stampLocation({
      id: appointmentId, patient_id: patientId, provider_id: providerId, operatory_id: operatoryId,
      procedure_type_id: procedureTypeId, start_time: startTime, end_time: endTime, status: 'Pending', source: 'self-scheduled',
      photos: Array.isArray(photos) ? photos : [], patient_notes: patientNotes,
      // THE CONTACT DETAILS RIDE ON THE APPOINTMENT TOO, and that is not
      // duplication for its own sake. The patient row is written AFTER this
      // one now, so a booking can exist for a moment -- or permanently, if
      // that second write fails -- whose patient_id resolves to nothing. An
      // appointment nobody can identify is worse than a duplicated name: the
      // practice cannot ring the person back. These two fields make the
      // booking actionable on its own.
      //
      // Same tenant, same record class as the patient_notes and photos already
      // on this row, so it is not a new exposure surface.
      patient_name: patient.name, patient_phone: patient.phone
    });
    const insertRes = await fetch(rest('dnt_appointments?on_conflict=license_hash,appointment_id'), {
      method: 'POST',
      headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
      body: JSON.stringify({
        license_hash: licenseHash, app_id: 'sairndental', appointment_id: appointmentId, data: appointmentData,
        provider_id: providerId, operatory_id: operatoryId, start_time: startTime, end_time: endTime, status: 'Pending',
        updated_at: new Date().toISOString()
      })
    });

    if (insertRes.status === 409) {
      res.status(409).json({ error: { code: 'SLOT_TAKEN', message: 'This time slot was just taken by someone else -- please pick a different time.' } });
      return;
    }
    if (!insertRes.ok) {
      const errBody = await insertRes.json().catch(() => null);
      console.error('SAIRNdental public-book insert error:', errBody);
      res.status(502).json({ error: { message: 'Could not complete booking -- try again' } });
      return;
    }

    // ── THE PATIENT ROW, WRITTEN ONLY NOW THAT THE SLOT IS SECURED ───────
    // Nothing above this line created one, so a 409 or a 502 leaves no trace
    // at all -- which is the whole point of the reordering.
    //
    // AND THIS WRITE IS CHECKED, which it was not before. The old code did a
    // bare `await fetch(...)` and never looked at the result: if it failed,
    // patientId still pointed at a row that did not exist and the appointment
    // was written referencing a phantom patient, reported as a clean success.
    let patientWritten = true;
    if (!matched) {
      // The guardian keys are written for EVERY patient, not only minors, and
      // that is deliberate: the in-app record carries them unconditionally, so
      // omitting them here would produce two shapes of dnt_patients row and a
      // reader would have to know which door the record came through.
      const isMinor = isMinorDob(patient.dob);
      const newPatient = { id: patientId, name: patient.name, dob: patient.dob, phone: patient.phone, email: patient.email || '', insurance_payer: '', insurance_member_id: '', insurance_group_number: '', insurance_plan_type: '',
        guardian_name: isMinor ? String(guardian.name || '').trim() : '',
        guardian_relationship: isMinor ? String(guardian.relationship || '').trim() : '',
        guardian_phone: isMinor ? String(guardian.phone || '').trim() : '',
        guardian_email: isMinor ? String(guardian.email || '').trim() : '' };
      const patientRes = await fetch(rest('dnt_patients?on_conflict=license_hash,patient_id'), {
        method: 'POST', headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates' }),
        body: JSON.stringify({ license_hash: licenseHash, app_id: 'sairndental', patient_id: patientId, data: newPatient, updated_at: new Date().toISOString() })
      });
      patientWritten = patientRes.ok;
      if (!patientWritten) {
        // THE BOOKING IS REAL AND IS REPORTED AS REAL. The slot is taken and
        // the appointment carries the caller's name and phone, so the practice
        // can act on it -- telling the visitor it failed would send them to
        // book a second time into a slot they already hold.
        //
        // What is NOT true is that a patient record exists, so that is logged
        // loudly rather than swallowed. Silence here is what let the phantom
        // patient_id ship in the first place.
        console.error('SAIRNdental public-book: appointment', appointmentId,
          'was written but its patient record was NOT -- patient_id', patientId,
          'resolves to nothing. Contact details are on the appointment row.');
      }
    }

    res.status(200).json({
      ok: true, appointment_id: appointmentId, status: 'Pending',
      // Reported rather than hidden: a caller that wants to know whether the
      // record is complete can, and the practice's own tooling can surface it.
      patient_record: patientWritten ? 'saved' : 'not_saved'
    });
  } catch (err) {
    console.error('SAIRNdental public-book error:', err.message);
    res.status(502).json({ error: { message: 'Could not complete booking -- try again' } });
  }
};
