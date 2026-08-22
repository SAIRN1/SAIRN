// api/alf-pharmacy.js
// SAIRNcare Phase 3 item 1: pharmacy-initiated eMAR intake.
//
// THE POINT OF THIS ENDPOINT: a medication order arrives from the dispensing
// pharmacy as structured data instead of being read off a fax and retyped into
// the MAR by a nurse. Manual transcription is where medication errors originate,
// so removing the retyping step is the actual safety win.
//
// WHAT IT DELIBERATELY DOES **NOT** REMOVE: clinical review. An order arriving
// here lands as pharmacy_status:'pending_review' and is NOT active on the MAR
// until a nurse or owner accepts it. "No manual transcription" and "no human
// checks the order" are different claims, and only the first one is safe --
// an unreviewed pharmacy feed writing directly to a live MAR would mean a
// pharmacy-side error reaches a resident with nobody in between. The review
// step costs a click and removes that whole failure class, so it stays.
//
// AUTH IS TWO-FACTOR AND FAILS CLOSED:
//   1. Authorization: Bearer <facility license key>  -- identifies the facility
//   2. X-ALF-Pharmacy-Key: <ALF_PHARMACY_SECRET>     -- proves the caller is the
//      integration, not just anyone holding a license key
// Both are required. The shared secret lives in an env var rather than in
// alf_facility, deliberately: alf_facility is readable by every authenticated
// employee (only the rate card is redacted), so a secret stored there would be
// readable by every med aide in the building. If the env var is not configured
// the endpoint refuses every request rather than degrading to license-key-only,
// because degrading would mean any license-key holder could write med orders.

'use strict';

const { validateLicenseKey } = require('./_lib/license');
const medSchedule = require('./_lib/med-schedule');

function supabaseHeaders() {
  return {
    apikey: process.env.SUPABASE_SERVICE_ROLE_KEY,
    Authorization: 'Bearer ' + process.env.SUPABASE_SERVICE_ROLE_KEY,
    'Content-Type': 'application/json'
  };
}
function rest(path) { return process.env.SUPABASE_URL + '/rest/v1/' + path; }
function enc(s) { return encodeURIComponent(s); }
function nowISO() { return new Date().toISOString(); }

function bad(res, status, code, message) {
  res.status(status).json({ error: { code: code, message: message } });
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') { bad(res, 405, 'METHOD', 'POST only'); return; }

  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
    bad(res, 503, 'NOT_CONFIGURED', 'Server storage is not configured.');
    return;
  }
  // Fails closed, and says which side is unconfigured rather than returning a
  // generic 401 that reads like a bad key.
  if (!process.env.ALF_PHARMACY_SECRET) {
    bad(res, 503, 'PHARMACY_NOT_CONFIGURED',
      'The pharmacy integration is not enabled on this deployment (ALF_PHARMACY_SECRET is not set). Orders cannot be accepted until it is.');
    return;
  }
  const presented = req.headers['x-alf-pharmacy-key'];
  if (!presented || presented !== process.env.ALF_PHARMACY_SECRET) {
    bad(res, 401, 'BAD_PHARMACY_KEY', 'A valid pharmacy integration key is required.');
    return;
  }

  const auth = req.headers.authorization || '';
  const licenseKey = auth.indexOf('Bearer ') === 0 ? auth.slice(7).trim() : '';
  if (!licenseKey) { bad(res, 401, 'NO_LICENSE', 'Missing bearer license key'); return; }
  let lic;
  try { lic = await validateLicenseKey(licenseKey); }
  catch (e) { bad(res, 502, 'LICENSE_CHECK_FAILED', 'Could not verify the license key.'); return; }
  if (!lic || !lic.valid || !lic.active) { bad(res, 401, 'INVALID_LICENSE', 'Unknown or inactive license key'); return; }
  // App scoping, matching the WRONG_APP pattern the legal endpoints already use.
  // This endpoint has no employee session to scope against, so the license's own
  // app_id is the only thing standing between a license issued for another SAIRN
  // app and the ability to write medication orders here -- exactly the cross-app
  // identifier collision sairn-guardian-v2 Check 28 exists to catch.
  if (lic.app_id && lic.app_id !== 'sairncare') {
    bad(res, 403, 'WRONG_APP', 'This license is not issued for sairncare');
    return;
  }
  const licHash = lic.license_hash;

  const body = req.body || {};
  const action = body.action || 'submit_order';
  if (action !== 'submit_order') { bad(res, 400, 'BAD_ACTION', "action must be 'submit_order'"); return; }

  const o = body.order || {};
  const missing = ['pharmacy_order_id', 'resident_id', 'name'].filter((f) => !o[f]);
  if (missing.length) {
    bad(res, 400, 'MISSING_FIELDS', 'The pharmacy order is missing required field(s): ' + missing.join(', '));
    return;
  }

  // Schedule times, if supplied, must be real HH:MM values. A pharmacy feed
  // sending garbage times is refused rather than stored -- a bad time here
  // becomes a false "late medication" alert against a real nurse later.
  let scheduleTimes = [];
  if (o.schedule_times !== undefined) {
    if (!Array.isArray(o.schedule_times)) {
      bad(res, 400, 'BAD_SCHEDULE', 'schedule_times must be an array of HH:MM strings');
      return;
    }
    const invalid = o.schedule_times.filter((t) => !medSchedule.isValidTime(t));
    if (invalid.length) {
      bad(res, 400, 'BAD_SCHEDULE', 'These schedule_times are not valid 24-hour HH:MM values: ' + invalid.join(', '));
      return;
    }
    scheduleTimes = o.schedule_times.slice().sort();
  }

  // The resident must actually exist at this facility. A pharmacy order for an
  // unknown resident is refused rather than parked against a dangling id --
  // otherwise it would sit invisible in the MAR forever.
  const rr = await fetch(rest('alf_clients?license_hash=eq.' + enc(licHash) + '&client_id=eq.' + enc(String(o.resident_id)) + '&select=client_id'), { headers: supabaseHeaders() });
  if (rr.status === 404 || rr.status === 400) {
    bad(res, 503, 'NOT_PROVISIONED', 'Resident tracking is not set up yet — run sql/sairncare_clients_schema.sql in Supabase first.');
    return;
  }
  const rrows = await rr.json().catch(() => []);
  if (!Array.isArray(rrows) || !rrows.length) {
    bad(res, 404, 'UNKNOWN_RESIDENT', 'No resident with id ' + o.resident_id + ' exists at this facility.');
    return;
  }

  // Idempotent on the pharmacy's own order id: a retried delivery must not
  // create a second order for the same prescription. entry_id is derived from
  // it rather than generated, so a duplicate POST resolves to the same row.
  const entryId = 'RXIN-' + String(o.pharmacy_order_id);
  const dupe = await fetch(rest('alf_mar?license_hash=eq.' + enc(licHash) + '&entry_id=eq.' + enc(entryId) + '&select=entry_id,data'), { headers: supabaseHeaders() });
  const dupeRows = dupe.ok ? await dupe.json().catch(() => []) : [];
  if (Array.isArray(dupeRows) && dupeRows.length) {
    const existing = dupeRows[0].data || {};
    res.status(200).json({
      ok: true, duplicate: true, entry_id: entryId,
      pharmacy_status: existing.pharmacy_status || 'pending_review',
      message: 'This pharmacy order was already received and is not duplicated.'
    });
    return;
  }

  const record = {
    id: entryId,
    name: String(o.name),
    dose: o.dose ? String(o.dose) : '',
    route: o.route ? String(o.route) : '',
    schedule: o.schedule ? String(o.schedule) : (scheduleTimes.join(', ')),
    schedule_times: scheduleTimes,
    prn: !!o.prn,
    prn_instructions: o.prn_instructions ? String(o.prn_instructions) : '',
    controlled_substance: !!o.controlled_substance,
    high_priority: !!o.high_priority,
    prescriber: o.prescriber ? String(o.prescriber) : '',
    start_date: o.start_date || null,
    notes: o.notes ? String(o.notes) : '',
    discontinued: false,
    // PROVENANCE, and the whole reason this is safe to trust later: the order
    // records that it came from a pharmacy feed, which pharmacy, and under
    // which of the pharmacy's own identifiers. A hand-entered order has none of
    // these, so the two can always be told apart in an audit.
    source: 'pharmacy',
    pharmacy_name: o.pharmacy_name ? String(o.pharmacy_name) : '',
    pharmacy_order_id: String(o.pharmacy_order_id),
    received_at: nowISO(),
    // NOT ACTIVE UNTIL A CLINICIAN ACCEPTS IT.
    pharmacy_status: 'pending_review',
    reviewed_by: null,
    reviewed_at: null
  };

  const w = await fetch(rest('alf_mar?on_conflict=license_hash,entry_id'), {
    method: 'POST',
    headers: Object.assign({}, supabaseHeaders(), { Prefer: 'resolution=merge-duplicates,return=representation' }),
    body: JSON.stringify({
      license_hash: licHash, app_id: 'sairncare', entry_id: entryId,
      resident_id: String(o.resident_id), assigned_employee_id: null,
      entry_type: 'medication_order', data: record, updated_at: nowISO()
    })
  });
  if (w.status === 404 || w.status === 400) {
    bad(res, 503, 'NOT_PROVISIONED', 'MAR tracking is not set up yet — run sql/sairncare_mar_schema.sql in Supabase first.');
    return;
  }
  if (!w.ok) {
    const t = await w.text().catch(() => '');
    bad(res, 502, 'UPSTREAM', 'Could not store the pharmacy order. ' + t.slice(0, 200));
    return;
  }

  res.status(200).json({
    ok: true,
    entry_id: entryId,
    pharmacy_status: 'pending_review',
    schedule_trackable: scheduleTimes.length > 0,
    message: scheduleTimes.length
      ? 'Order received and is awaiting clinical review before it becomes active on the MAR.'
      : 'Order received and is awaiting clinical review. No explicit schedule times were supplied, so this order cannot be tracked for late administration until times are entered.'
  });
};
