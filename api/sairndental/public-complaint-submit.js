// api/sairndental/public-complaint-submit.js
// Genuinely public, unauthenticated endpoint -- no license key
// anywhere in this file, same category as public-book.js/
// public-availability.js. Creates a new dnt_complaints thread and
// returns the one-time access_token the patient must save to
// view/reply later -- there is no recovery path if it's lost (design
// spec §0, disclosed, not a bug).

const crypto = require('crypto');
const { resolveSlug, checkAndIncrementRateLimit } = require('../_lib/dental-public');

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
const MAX_MESSAGE_LEN = 4000;

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'POST only' } }); return; }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) { res.status(500).json({ error: { message: 'Server configuration error' } }); return; }

  const body = req.body || {};
  const slug = body.slug;
  const message = typeof body.message === 'string' ? body.message.trim() : '';
  const patientName = typeof body.patient_name === 'string' ? body.patient_name.trim() : '';
  if (!slug || !message) { res.status(400).json({ error: { message: 'slug and message are required' } }); return; }
  if (message.length > MAX_MESSAGE_LEN) { res.status(400).json({ error: { code: 'MESSAGE_TOO_LONG', message: 'Message is too long -- please keep it under ' + MAX_MESSAGE_LEN + ' characters' } }); return; }

  try {
    const rl = await checkAndIncrementRateLimit(req, 60, 5, 'complaint-submit'); // 5 submissions per hour per IP
    if (!rl.allowed) { res.status(429).json({ error: { code: 'RATE_LIMITED', message: 'Too many attempts -- please call the office or try again later' } }); return; }

    const licenseHash = await resolveSlug(slug);
    if (!licenseHash) { res.status(404).json({ error: { code: 'UNKNOWN_SLUG', message: 'Practice link not found' } }); return; }

    const complaintId = newId('COMP');
    const accessToken = crypto.randomBytes(32).toString('hex');
    const nowISO = new Date().toISOString();
    const data = {
      id: complaintId, patient_name: patientName, status: 'New',
      messages: [{ from: 'patient', text: message, at: nowISO }],
      created_at: nowISO.slice(0, 10)
    };

    const insertRes = await fetch(rest('dnt_complaints'), {
      method: 'POST',
      headers: Object.assign({}, supabaseHeaders(), { Prefer: 'return=representation' }),
      body: JSON.stringify({
        license_hash: licenseHash, app_id: 'sairndental', complaint_id: complaintId,
        access_token: accessToken, data: data, updated_at: nowISO
      })
    });
    if (insertRes.status === 404 || insertRes.status === 400) {
      const bodyText = await insertRes.text().catch(function () { return ''; });
      if (/relation .* does not exist|does not exist/i.test(bodyText)) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNdental complaint tables are not set up yet.' } });
        return;
      }
      console.error('SAIRNdental public-complaint-submit insert error:', bodyText);
      res.status(502).json({ error: { message: 'Could not submit -- try again' } });
      return;
    }
    if (!insertRes.ok) {
      const errBody = await insertRes.json().catch(() => null);
      console.error('SAIRNdental public-complaint-submit insert error:', errBody);
      res.status(502).json({ error: { message: 'Could not submit -- try again' } });
      return;
    }

    res.status(200).json({ ok: true, token: accessToken });
  } catch (err) {
    console.error('SAIRNdental public-complaint-submit error:', err.message);
    res.status(502).json({ error: { message: 'Could not submit -- try again' } });
  }
};
