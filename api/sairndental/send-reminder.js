// api/sairndental/send-reminder.js
// Cron-only endpoint (Vercel Cron -> CRON_SECRET check below), never
// publicly callable. Cross-tenant by design: scans every practice's
// Confirmed appointments directly against Supabase using the
// service-role key, the same posture as public-availability.js --
// there is no per-practice license key available to a scheduled job,
// so this bypasses api/sd-data.js's Bearer-license layer entirely and
// talks to Supabase REST directly. See
// docs/superpowers/specs/2026-08-11-sairndental-email-reminders-design.md.

const { buildReminderEmail } = require('../_lib/dental-reminder-copy.js');
const { needsStage } = require('../_lib/dental-reminder-window.js');

function supabaseHeaders() {
  return {
    apikey: process.env.SUPABASE_SERVICE_ROLE_KEY,
    Authorization: 'Bearer ' + process.env.SUPABASE_SERVICE_ROLE_KEY,
    'Content-Type': 'application/json'
  };
}
function rest(path) {
  return process.env.SUPABASE_URL + '/rest/v1/' + path;
}
function enc(s) { return encodeURIComponent(s); }

async function fetchOne(resource, idCol, licenseHash, id) {
  var r = await fetch(rest(resource + '?license_hash=eq.' + enc(licenseHash) + '&' + idCol + '=eq.' + enc(id) + '&select=data'), { headers: supabaseHeaders() });
  if (!r.ok) return null;
  var rows = await r.json();
  return (Array.isArray(rows) && rows[0]) ? rows[0].data : null;
}

// NOTE ON THE VARIABLE NAME, corrected 2026-08-24: this file read
// RESEND_FROM_ADDRESS, a name that has never existed in this Vercel project.
// The sender address has been configured as RESEND_FROM_EMAIL since 2026-06-19
// (alongside RESEND_API_KEY, both Production + Preview). Because of that, the
// env-completeness guard below failed on EVERY hourly firing since this file
// shipped and it has never sent a single reminder -- a 500 in the production
// log every hour, for months, from a feature everyone assumed was working.
// Identical defect to api/alf-alerts.js, found in the same sweep and fixed
// there first. Verified with `vercel env ls production`, not assumed.
async function sendResendEmail(to, subject, text, html) {
  var r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + process.env.RESEND_API_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ from: process.env.RESEND_FROM_EMAIL, to: [to], subject: subject, text: text, html: html })
  });
  if (!r.ok) {
    var bodyText = await r.text().catch(function () { return ''; });
    throw new Error('Resend ' + r.status + ': ' + bodyText);
  }
  // The provider's message id is returned so a SUCCESSFUL send is positively
  // observable in the production log rather than inferred from the absence of
  // an error. A cron's response body goes nowhere -- Vercel keeps the status
  // code and discards it -- so a sweep that delivered and a sweep that found
  // nothing due both produce an identical, silent 200.
  var okBody = await r.json().catch(function () { return {}; });
  return (okBody && okBody.id) || null;
}

async function stampReminderSent(row, stage, nowISO) {
  var data = row.data;
  if (stage === '48h') data.reminder_48h_sent_at = nowISO; else data.reminder_2h_sent_at = nowISO;
  var r = await fetch(rest('dnt_appointments?on_conflict=license_hash,appointment_id'), {
    method: 'POST',
    headers: Object.assign({}, supabaseHeaders(), { Prefer: 'resolution=merge-duplicates,return=representation' }),
    body: JSON.stringify({
      license_hash: row.license_hash, app_id: 'sairndental', appointment_id: row.appointment_id, data: data,
      provider_id: row.provider_id || null, operatory_id: row.operatory_id || null,
      start_time: row.start_time || null, end_time: row.end_time || null, status: row.status || null,
      updated_at: nowISO
    })
  });
  if (!r.ok) {
    var bodyText = await r.text().catch(function () { return ''; });
    throw new Error('stamp write ' + r.status + ': ' + bodyText);
  }
}

module.exports = async (req, res) => {
  if (!process.env.CRON_SECRET) {
    console.error('CRON_SECRET not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error' } });
    return;
  }
  if (req.headers.authorization !== 'Bearer ' + process.env.CRON_SECRET) {
    res.status(401).json({ error: { message: 'Unauthorized' } });
    return;
  }
  // Names ONLY the variable actually missing. The original guard listed all
  // four unconditionally, which is what made the RESEND_FROM_ADDRESS typo look
  // like an absent secret and sent a previous session hunting for a
  // RESEND_API_KEY that was present and correct the whole time.
  var missing = [
    !process.env.SUPABASE_URL ? 'SUPABASE_URL' : null,
    !process.env.SUPABASE_SERVICE_ROLE_KEY ? 'SUPABASE_SERVICE_ROLE_KEY' : null,
    !process.env.RESEND_API_KEY ? 'RESEND_API_KEY' : null,
    !process.env.RESEND_FROM_EMAIL ? 'RESEND_FROM_EMAIL' : null
  ].filter(Boolean);
  if (missing.length) {
    console.error('send-reminder: not fully configured, missing: ' + missing.join(', '));
    res.status(500).json({ error: { message: 'Server configuration error' } });
    return;
  }

  var nowMs = Date.now();
  var nowISO = new Date(nowMs).toISOString();
  var rangeStartISO = nowISO;
  var rangeEndISO = new Date(nowMs + 48 * 60 * 60 * 1000).toISOString();

  var summary = { sent: 0, skippedNoEmail: 0, skippedNotDue: 0, failed: 0 };

  try {
    var listRes = await fetch(rest('dnt_appointments?status=eq.Confirmed&start_time=gt.' + enc(rangeStartISO) + '&start_time=lte.' + enc(rangeEndISO) + '&select=license_hash,appointment_id,data,provider_id,operatory_id,start_time,end_time,status'), { headers: supabaseHeaders() });
    if (!listRes.ok) {
      var errBody = await listRes.text().catch(function () { return ''; });
      console.error('send-reminder: dnt_appointments list failed', listRes.status, errBody);
      res.status(502).json({ error: { message: 'Could not list appointments' } });
      return;
    }
    var rows = await listRes.json();

    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];
      var stage = null;
      if (needsStage(row, '48h', nowMs)) stage = '48h';
      else if (needsStage(row, '2h', nowMs)) stage = '2h';
      if (!stage) { summary.skippedNotDue++; continue; }

      try {
        var patientId = row.data.patient_id;
        var patient = await fetchOne('dnt_patients', 'patient_id', row.license_hash, patientId);
        if (!patient || !patient.email) { summary.skippedNoEmail++; continue; }

        var settings = await fetchOne('dnt_settings', 'settings_id', row.license_hash, 'default');
        var provider = row.provider_id ? await fetchOne('dnt_providers', 'provider_id', row.license_hash, row.provider_id) : null;
        var procedureTypeId = row.data.procedure_type_id;
        var procedure = procedureTypeId ? await fetchOne('dnt_procedure_types', 'procedure_type_id', row.license_hash, procedureTypeId) : null;

        var copy = buildReminderEmail({
          practiceName: (settings && settings.practice_name) || '',
          practicePhone: (settings && settings.practice_phone) || '',
          practiceAddress: (settings && settings.practice_address) || '',
          patientName: patient.name || '',
          providerName: (provider && provider.name) || '',
          procedureLabel: procedure ? (procedure.cdt_code + ' -- ' + procedure.description) : '',
          startTimeISO: row.start_time,
          stage: stage
        });

        var resendId = await sendResendEmail(patient.email, copy.subject, copy.text, copy.html);
        await stampReminderSent(row, stage, nowISO);
        summary.sent++;
        console.log('send-reminder: Resend send OK for appointment ' + row.appointment_id +
          ' stage ' + stage + ' -- resend_id ' + (resendId || 'none returned'));
      } catch (perAppointmentErr) {
        console.error('send-reminder: failed for appointment', row.appointment_id, 'stage', stage, '-', perAppointmentErr.message);
        summary.failed++;
      }
    }

    // Logged, not just returned. Without this a sweep that found nothing due
    // is indistinguishable in the production log from a sweep that never ran,
    // because the cron's response body is discarded either way.
    console.log('send-reminder: sweep complete -- scanned ' + rows.length +
      ', sent ' + summary.sent + ', skippedNoEmail ' + summary.skippedNoEmail +
      ', skippedNotDue ' + summary.skippedNotDue + ', failed ' + summary.failed);
    res.status(200).json({ ok: true, summary: summary });
  } catch (err) {
    console.error('send-reminder: fatal error', err);
    res.status(500).json({ error: { message: 'Internal error' } });
  }
};
