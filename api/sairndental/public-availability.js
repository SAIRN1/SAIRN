// api/sairndental/public-availability.js
// Genuinely public, unauthenticated endpoint -- no license key anywhere in
// this file. Real availability computed server-side; the response is
// EXACTLY {start_time, end_time, provider_id} per slot, never the raw
// appointments array or any other patient's data (design spec §2's hard
// requirement -- sending the full appointments array to an anonymous
// browser, even just to filter client-side, would leak other patients'
// visit times and, via patient_id, enough to correlate identity).
//
// This is a UX-level pre-filter only -- the REAL double-booking guarantee
// is the Postgres EXCLUDE constraints (sql/sairndental_availability_booking_schema.sql),
// enforced at write time by public-book.js's insert, not by anything here.

const { resolveSlug, checkAndIncrementRateLimit } = require('../_lib/dental-public');

const DAY_NAMES = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];

function supabaseHeaders() {
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  return { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };
}
function rest(path) {
  return process.env.SUPABASE_URL + '/rest/v1/' + path;
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
    const rl = await checkAndIncrementRateLimit(req, 10, 30); // 30 reads per 10 min per IP -- looser than booking writes
    if (!rl.allowed) { res.status(429).json({ error: { code: 'RATE_LIMITED', message: 'Too many requests -- try again shortly' } }); return; }

    const body = req.body || {};
    const slug = body.slug, providerId = body.provider_id, procedureTypeId = body.procedure_type_id;
    const dateFrom = body.date_from, dateTo = body.date_to;
    if (!slug) { res.status(400).json({ error: { message: 'slug is required' } }); return; }

    const licenseHash = await resolveSlug(slug);
    if (!licenseHash) { res.status(404).json({ error: { code: 'UNKNOWN_SLUG', message: 'Booking link not found' } }); return; }

    const headers = supabaseHeaders();

    // Listing mode: {slug} only -- the public page's first real read,
    // discovering which providers/procedure types it can even offer,
    // before it knows enough to ask for real slots. Public-safe fields
    // only (never anything from dnt_patients or dnt_appointments here).
    if (!providerId || !procedureTypeId || !dateFrom || !dateTo) {
      const settingsRes = await fetch(rest('dnt_settings?license_hash=eq.' + encodeURIComponent(licenseHash) + '&select=data&limit=1'), { headers });
      const settingsRows = settingsRes.ok ? await settingsRes.json() : [];
      const settings = (settingsRows && settingsRows[0] && settingsRows[0].data) || {};
      const bookableIds = settings.publicly_bookable_procedure_type_ids || [];

      const provRes = await fetch(rest('dnt_providers?license_hash=eq.' + encodeURIComponent(licenseHash) + '&select=data'), { headers });
      const provRows = provRes.ok ? await provRes.json() : [];
      const providersOut = (provRows || []).map((x) => x.data).map((p) => ({ id: p.id, name: p.name, role: p.role }));

      const allProcRes = await fetch(rest('dnt_procedure_types?license_hash=eq.' + encodeURIComponent(licenseHash) + '&select=data'), { headers });
      const allProcRows = allProcRes.ok ? await allProcRes.json() : [];
      const proceduresOut = (allProcRows || []).map((x) => x.data)
        .filter((p) => bookableIds.indexOf(p.id) !== -1)
        .map((p) => ({ id: p.id, code: p.cdt_code, description: p.description, default_length_minutes: p.default_length_minutes }));

      res.status(200).json({ ok: true, providers: providersOut, procedure_types: proceduresOut, timezone: settings.timezone || '' });
      return;
    }

    const hoursRes = await fetch(rest('dnt_provider_hours?license_hash=eq.' + encodeURIComponent(licenseHash) + '&provider_id=eq.' + encodeURIComponent(providerId) + '&select=data'), { headers });
    const hoursRows = hoursRes.ok ? await hoursRes.json() : [];
    const providerHours = (hoursRows || []).map((x) => x.data);

    const procRes = await fetch(rest('dnt_procedure_types?license_hash=eq.' + encodeURIComponent(licenseHash) + '&procedure_type_id=eq.' + encodeURIComponent(procedureTypeId) + '&select=data'), { headers });
    const procRows = procRes.ok ? await procRes.json() : [];
    const proc = procRows && procRows[0] && procRows[0].data;
    if (!proc) { res.status(404).json({ error: { code: 'UNKNOWN_PROCEDURE', message: 'Procedure type not found' } }); return; }
    const lengthMin = Number(proc.default_length_minutes) || 30;

    // Real promoted columns -- no jsonb scan, and the response we build
    // from this never leaves this function (only used for the local
    // overlap filter below).
    const apptRes = await fetch(rest(
      'dnt_appointments?license_hash=eq.' + encodeURIComponent(licenseHash) +
      '&provider_id=eq.' + encodeURIComponent(providerId) +
      '&status=in.(Pending,Confirmed)' +
      '&start_time=gte.' + encodeURIComponent(dateFrom) +
      '&start_time=lte.' + encodeURIComponent(dateTo) +
      '&select=start_time,end_time'
    ), { headers });
    const existing = apptRes.ok ? await apptRes.json() : [];

    function overlaps(startA, endA) {
      return existing.some((e) => {
        const s = new Date(e.start_time).getTime(), en = new Date(e.end_time).getTime();
        return startA.getTime() < en && endA.getTime() > s;
      });
    }

    const slots = [];
    const dayStart = new Date(dateFrom + 'T00:00:00Z');
    const dayEnd = new Date(dateTo + 'T00:00:00Z');
    for (let d = new Date(dayStart); d <= dayEnd; d.setUTCDate(d.getUTCDate() + 1)) {
      const dayName = DAY_NAMES[d.getUTCDay()];
      const blocksForDay = providerHours.filter((h) => h.day_of_week === dayName);
      blocksForDay.forEach((block) => {
        const [sh, sm] = String(block.start_time).split(':').map(Number);
        const [eh, em] = String(block.end_time).split(':').map(Number);
        let cursor = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate(), sh, sm));
        const blockEnd = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate(), eh, em));
        while (cursor.getTime() + lengthMin * 60000 <= blockEnd.getTime()) {
          const slotEnd = new Date(cursor.getTime() + lengthMin * 60000);
          if (!overlaps(cursor, slotEnd)) {
            slots.push({ start_time: cursor.toISOString(), end_time: slotEnd.toISOString(), provider_id: providerId });
          }
          cursor = new Date(cursor.getTime() + lengthMin * 60000);
        }
      });
    }

    res.status(200).json({ ok: true, slots: slots });
  } catch (err) {
    console.error('SAIRNdental public-availability error:', err.message);
    res.status(502).json({ error: { message: 'Could not compute availability -- try again' } });
  }
};
