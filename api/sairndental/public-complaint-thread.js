// api/sairndental/public-complaint-thread.js
// Genuinely public, unauthenticated endpoint. {token} loads a thread;
// {token, reply} also appends the patient's reply. Always does a
// fresh read of the current row immediately before writing (never
// trusts a client-supplied prior message list) -- the "server-side
// append" half of design spec §0's race-handling decision. Reopens a
// Resolved/Awaiting Patient thread back to 'New' on any patient reply
// -- the one uniform state rule from design spec §0, no special-
// casing per prior status.

const { checkAndIncrementRateLimit } = require('../_lib/dental-public');

function supabaseHeaders(extra) {
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  return Object.assign({ apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' }, extra || {});
}
function rest(path) {
  return process.env.SUPABASE_URL + '/rest/v1/' + path;
}
const MAX_MESSAGE_LEN = 4000;

async function fetchByToken(token) {
  const r = await fetch(rest('dnt_complaints?access_token=eq.' + encodeURIComponent(token) + '&select=license_hash,complaint_id,data'), { headers: supabaseHeaders() });
  if (!r.ok) return null;
  const rows = await r.json();
  return (Array.isArray(rows) && rows[0]) || null;
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

  const body = req.body || {};
  const token = body.token;
  const reply = typeof body.reply === 'string' ? body.reply.trim() : '';
  if (!token) { res.status(400).json({ error: { message: 'token is required' } }); return; }
  if (reply && reply.length > MAX_MESSAGE_LEN) { res.status(400).json({ error: { code: 'MESSAGE_TOO_LONG', message: 'Message is too long -- please keep it under ' + MAX_MESSAGE_LEN + ' characters' } }); return; }

  try {
    if (reply) {
      const rl = await checkAndIncrementRateLimit(req, 60, 20, 'complaint-reply'); // 20 replies per hour per IP
      if (!rl.allowed) { res.status(429).json({ error: { code: 'RATE_LIMITED', message: 'Too many messages -- please try again later' } }); return; }
    }

    // Fresh read, right before writing -- never the pre-request snapshot.
    const row = await fetchByToken(token);
    if (!row) { res.status(404).json({ error: { code: 'UNKNOWN_TOKEN', message: "This link isn't valid -- check that you copied it correctly" } }); return; }

    let data = row.data;
    if (reply) {
      const nowISO = new Date().toISOString();
      data = Object.assign({}, data, {
        messages: (data.messages || []).concat([{ from: 'patient', text: reply, at: nowISO }]),
        status: 'New'
      });
      const writeRes = await fetch(rest('dnt_complaints?on_conflict=license_hash,complaint_id'), {
        method: 'POST',
        headers: Object.assign({}, supabaseHeaders(), { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: row.license_hash, app_id: 'sairndental', complaint_id: row.complaint_id, access_token: token, data: data, updated_at: nowISO })
      });
      if (!writeRes.ok) {
        const errBody = await writeRes.json().catch(() => null);
        console.error('SAIRNdental public-complaint-thread write error:', errBody);
        res.status(502).json({ error: { message: 'Could not send -- try again' } });
        return;
      }
      const writtenRows = await writeRes.json();
      data = (Array.isArray(writtenRows) && writtenRows[0] && writtenRows[0].data) || data;
    }

    res.status(200).json({ ok: true, status: data.status, patient_name: data.patient_name, messages: data.messages });
  } catch (err) {
    console.error('SAIRNdental public-complaint-thread error:', err.message);
    res.status(502).json({ error: { message: 'Could not load -- try again' } });
  }
};
