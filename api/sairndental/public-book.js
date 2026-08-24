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

const { resolveSlug, checkAndIncrementRateLimit } = require('../_lib/dental-public');
const { validatePhotosPayload, validatePatientNotes } = require('../_lib/dental-photo-validation');

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
    const procRows = procRes.ok ? await procRes.json() : [];
    const proc = procRows && procRows[0] && procRows[0].data;
    if (!proc) { res.status(404).json({ error: { code: 'UNKNOWN_PROCEDURE', message: 'Procedure type not found' } }); return; }
    const lengthMin = Number(proc.default_length_minutes) || 30;
    const endTime = new Date(new Date(startTime).getTime() + lengthMin * 60000).toISOString();

    const providerRes = await fetch(rest('dnt_providers?license_hash=eq.' + encodeURIComponent(licenseHash) + '&provider_id=eq.' + encodeURIComponent(providerId) + '&select=data'), { headers });
    const providerRows = providerRes.ok ? await providerRes.json() : [];
    const provider = providerRows && providerRows[0] && providerRows[0].data;
    if (!provider) { res.status(404).json({ error: { code: 'UNKNOWN_PROVIDER', message: 'Provider not found' } }); return; }
    const operatoryId = provider.operatory_id || '';

    // Match an existing patient by EXACT name+dob+phone only -- never
    // fuzzy -- to avoid accidentally attaching a stranger's booking to
    // the wrong patient's record. No match -> create a new patient.
    const patientsRes = await fetch(rest('dnt_patients?license_hash=eq.' + encodeURIComponent(licenseHash) + '&select=data,patient_id'), { headers });
    const patientsRows = patientsRes.ok ? await patientsRes.json() : [];
    const matched = (patientsRows || []).find((p) => p.data && p.data.name === patient.name && p.data.dob === patient.dob && p.data.phone === patient.phone);
    let patientId;
    if (matched) {
      patientId = matched.patient_id;
    } else {
      patientId = newId('PT');
      const newPatient = { id: patientId, name: patient.name, dob: patient.dob, phone: patient.phone, email: patient.email || '', insurance_payer: '', insurance_member_id: '', insurance_group_number: '', insurance_plan_type: '' };
      await fetch(rest('dnt_patients?on_conflict=license_hash,patient_id'), {
        method: 'POST', headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates' }),
        body: JSON.stringify({ license_hash: licenseHash, app_id: 'sairndental', patient_id: patientId, data: newPatient, updated_at: new Date().toISOString() })
      });
    }

    const appointmentId = newId('AP');
    const appointmentData = {
      id: appointmentId, patient_id: patientId, provider_id: providerId, operatory_id: operatoryId,
      procedure_type_id: procedureTypeId, start_time: startTime, end_time: endTime, status: 'Pending', source: 'self-scheduled',
      photos: Array.isArray(photos) ? photos : [], patient_notes: patientNotes
    };
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

    res.status(200).json({ ok: true, appointment_id: appointmentId, status: 'Pending' });
  } catch (err) {
    console.error('SAIRNdental public-book error:', err.message);
    res.status(502).json({ error: { message: 'Could not complete booking -- try again' } });
  }
};
