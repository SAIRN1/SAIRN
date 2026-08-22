// api/alf-alerts.js
// SAIRNcare Phase 3 item 4: missed/late-care alerting.
//
// TWO MODES, one code path for the computation:
//   POST {action:'check'}  -- an authenticated employee asks "what is late right
//                             now". Computes and returns; sends nothing.
//   Cron (Bearer CRON_SECRET) -- the scheduled sweep. Computes the same way and
//                             EMAILS the facility when something is late.
//
// OUTBOUND REALITY, verified rather than assumed before building:
//   EMAIL -- real. api/sairndental/send-reminder.js already sends through Resend
//            on a real hourly Vercel cron, so this reuses that proven path
//            (RESEND_API_KEY + RESEND_FROM_ADDRESS) rather than inventing one.
//   SMS   -- DOES NOT EXIST anywhere in this repo. There is no Twilio or other
//            SMS provider wired up, so this endpoint does not claim to text
//            anyone. A text-message channel is a real piece of infrastructure
//            somebody has to buy and configure; pretending otherwise would put
//            a "resident's medication is late" notification into a channel that
//            silently goes nowhere, which is worse than not offering it.
//   The response always reports which channels actually delivered, so the UI
//   can never imply a text was sent.
//
// The lateness computation itself is PURE and lives in api/_lib/med-schedule.js.

'use strict';

const { validateLicenseKey } = require('./_lib/license');
const { verifySessionToken, tokenFromRequest } = require('./_lib/auth');
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
function bad(res, status, code, message) { res.status(status).json({ error: { code: code, message: message } }); }

// Roles allowed to see who is late on medications. Same scope-of-practice
// boundary alf_mar itself uses -- billing/activities/caregiver have no business
// in a medication-administration exception report.
const ALERT_ROLES = { owner: true, nursing: true, med_aide: true };

async function loadFacility(licHash) {
  const r = await fetch(rest('alf_facility?license_hash=eq.' + enc(licHash) + '&select=facility_id,data'), { headers: supabaseHeaders() });
  if (!r.ok) return null;
  const rows = await r.json().catch(() => []);
  return (Array.isArray(rows) && rows[0] && rows[0].data) || null;
}

// Pull the active, reviewed medication orders and the day's administrations.
async function loadMar(licHash, dayStr) {
  const r = await fetch(rest('alf_mar?license_hash=eq.' + enc(licHash) + '&select=entry_id,resident_id,entry_type,data'), { headers: supabaseHeaders() });
  if (r.status === 404 || r.status === 400) return { provisioned: false, orders: [], administrations: [] };
  if (!r.ok) return null;
  const rows = await r.json().catch(() => []);
  const orders = [];
  const administrations = [];
  (rows || []).forEach((row) => {
    const d = row.data || {};
    if (row.entry_type === 'medication_order') {
      // A pharmacy order awaiting clinical review is NOT active on the MAR, so
      // it must not generate a "late" alert -- nobody was supposed to give it yet.
      if (d.pharmacy_status && d.pharmacy_status !== 'accepted') return;
      if (d.discontinued) return;
      orders.push(Object.assign({}, d, { id: row.entry_id, resident_id: row.resident_id }));
    } else if (row.entry_type === 'administration') {
      const at = String(d.administered_at || d.recorded_at || '');
      administrations.push({
        id: row.entry_id,
        medication_id: d.medication_id || d.med_id || null,
        day: at.slice(0, 10),
        time: at.slice(11, 16),
        matched_dose_time: d.scheduled_time || null
      });
    }
  });
  return { provisioned: true, orders: orders, administrations: administrations.filter((a) => a.day === dayStr) };
}

async function sendResendEmail(to, subject, text) {
  const r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + process.env.RESEND_API_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ from: process.env.RESEND_FROM_ADDRESS, to: [to], subject: subject, text: text })
  });
  if (!r.ok) {
    const t = await r.text().catch(() => '');
    return { sent: false, error: 'Resend returned ' + r.status + ' ' + t.slice(0, 200) };
  }
  return { sent: true };
}

function buildAlertText(facilityName, result) {
  const lines = [];
  lines.push((facilityName || 'Your facility') + ' — late medication administrations as of ' + result.checked_at);
  lines.push('');
  result.late.forEach((f) => {
    lines.push('- ' + f.medication + ' for resident ' + f.resident_id +
      ' — scheduled ' + f.scheduled_time + ', now ' + f.minutes_late + ' minute(s) past the administration window' +
      (f.high_priority ? ' [HIGH PRIORITY]' : '') + (f.controlled_substance ? ' [CONTROLLED]' : ''));
  });
  if (result.unschedulable && result.unschedulable.length) {
    lines.push('');
    lines.push('Not checked (' + result.unschedulable.length + ' order(s) have no explicit clock times and cannot be tracked):');
    result.unschedulable.forEach((u) => lines.push('- ' + u.medication + ' for resident ' + u.resident_id));
  }
  lines.push('');
  lines.push('This is an automated exception report from SAIRNcare. It reflects only what has been recorded in the MAR.');
  return lines.join('\n');
}

async function computeForFacility(licHash, nowDate) {
  const facility = await loadFacility(licHash);
  const dayStr = nowDate.toISOString().slice(0, 10);
  const nowMinutes = (nowDate.getUTCHours() * 60) + nowDate.getUTCMinutes();
  // The administration window is the FACILITY'S policy, not a number this app
  // invents. No ALF regulation surveyed sets a universal window, so with no
  // policy recorded the engine refuses rather than assuming one -- a guessed
  // window would generate false "late" findings against real nurses.
  const grace = facility && facility.med_window_minutes;
  if (grace === undefined || grace === null || grace === '') {
    return {
      ok: false,
      error: {
        code: 'NO_WINDOW_POLICY',
        message: 'No medication administration window has been set for this facility. Set one in Settings — this app will not assume a window, because a guessed one would produce false late-medication alerts.'
      }
    };
  }
  const mar = await loadMar(licHash, dayStr);
  if (mar === null) return { ok: false, error: { code: 'UPSTREAM', message: 'Could not read the MAR.' } };
  if (!mar.provisioned) {
    return { ok: false, error: { code: 'NOT_PROVISIONED', message: 'MAR tracking is not set up yet — run sql/sairncare_mar_schema.sql in Supabase first.' } };
  }
  const result = medSchedule.facilityAlerts({
    orders: mar.orders, administrations: mar.administrations,
    day: dayStr, now_minutes_of_day: nowMinutes, grace_minutes: Number(grace)
  });
  result.checked_at = nowDate.toISOString();
  result.window_minutes = Number(grace);
  result.facility_name = (facility && facility.name) || '';
  result.alert_email = (facility && facility.alert_email) || '';
  return Object.assign({ ok: true }, result);
}

module.exports = async (req, res) => {
  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
    bad(res, 503, 'NOT_CONFIGURED', 'Server storage is not configured.'); return;
  }

  const auth = req.headers.authorization || '';
  const isCron = !!process.env.CRON_SECRET && auth === 'Bearer ' + process.env.CRON_SECRET;

  // METHOD GATE, and the reason it is not a blanket POST-only check:
  // VERCEL CRONS ISSUE A **GET**, not a POST. An earlier version of this file
  // rejected everything but POST, so the scheduled sweep returned 405 on every
  // firing and this whole feature silently never delivered a single alert --
  // found only by reading the real production cron log, since no unit test
  // exercises the HTTP method Vercel actually uses. The sibling cron
  // (api/sairndental/send-reminder.js) has no method check at all for exactly
  // this reason. The interactive path stays POST-only.
  if (!isCron && req.method !== 'POST') {
    bad(res, 405, 'METHOD', 'POST only for the interactive check');
    return;
  }

  // ── CRON SWEEP ─────────────────────────────────────────────────────────
  if (isCron) {
    if (!process.env.RESEND_API_KEY || !process.env.RESEND_FROM_ADDRESS) {
      // Reported, not silently skipped: a sweep that computes alerts and cannot
      // deliver them is a broken alerting system, and it should say so loudly.
      bad(res, 503, 'EMAIL_NOT_CONFIGURED',
        'Alerting is scheduled but no email sender is configured (RESEND_API_KEY / RESEND_FROM_ADDRESS). No notifications were sent.');
      return;
    }
    const fr = await fetch(rest('alf_facility?select=license_hash,data'), { headers: supabaseHeaders() });
    if (fr.status === 404 || fr.status === 400) {
      res.status(200).json({ ok: true, facilities_checked: 0, note: 'No facility profiles are provisioned yet.' });
      return;
    }
    const facilities = fr.ok ? await fr.json().catch(() => []) : [];
    const now = new Date();
    const out = [];
    for (const f of (facilities || [])) {
      const r = await computeForFacility(f.license_hash, now);
      if (!r.ok) { out.push({ license_hash: f.license_hash, skipped: r.error.code }); continue; }
      if (!r.late.length) { out.push({ license_hash: f.license_hash, late: 0, emailed: false }); continue; }
      if (!r.alert_email) {
        out.push({ license_hash: f.license_hash, late: r.late.length, emailed: false, skipped: 'NO_ALERT_EMAIL' });
        continue;
      }
      const sendRes = await sendResendEmail(
        r.alert_email,
        'SAIRNcare: ' + r.late.length + ' late medication administration(s)',
        buildAlertText(r.facility_name, r)
      );
      out.push({ license_hash: f.license_hash, late: r.late.length, emailed: sendRes.sent, error: sendRes.error || null });
    }
    res.status(200).json({ ok: true, facilities_checked: out.length, results: out });
    return;
  }

  // ── INTERACTIVE CHECK ──────────────────────────────────────────────────
  const licenseKey = auth.indexOf('Bearer ') === 0 ? auth.slice(7).trim() : '';
  if (!licenseKey) { bad(res, 401, 'NO_LICENSE', 'Missing bearer license key'); return; }
  let lic;
  try { lic = await validateLicenseKey(licenseKey); }
  catch (e) { bad(res, 502, 'LICENSE_CHECK_FAILED', 'Could not verify the license key.'); return; }
  if (!lic || !lic.valid || !lic.active) { bad(res, 401, 'INVALID_LICENSE', 'Unknown or inactive license key'); return; }
  if (lic.app_id && lic.app_id !== 'sairncare') { bad(res, 403, 'WRONG_APP', 'This license is not issued for sairncare'); return; }

  const session = verifySessionToken(tokenFromRequest(req), lic.license_hash, 'sairncare');
  if (!session) { bad(res, 401, 'NO_SESSION', 'Sign in first'); return; }
  if (!ALERT_ROLES[session.role]) {
    bad(res, 403, 'FORBIDDEN', 'Medication exception reports are not available to your role');
    return;
  }

  const result = await computeForFacility(lic.license_hash, new Date());
  if (!result.ok) { res.status(200).json(result); return; }
  // Channel honesty: an interactive check never sends anything, and says so,
  // so the UI cannot imply that looking at the screen notified anybody.
  result.channels = {
    in_app: true,
    email: 'not sent — email is delivered by the scheduled sweep, not by this check',
    sms: 'unavailable — no SMS provider is configured on this deployment'
  };
  res.status(200).json(result);
};
