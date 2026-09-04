// api/sairndental/complaint-respond.js
// Authenticated (Bearer license key), but NOT part of
// api/sd-data.js's generic RESOURCES dispatch -- dnt_complaints is
// enforced read-only there (design spec §1). This is the dedicated,
// atomic (fresh read-then-write) endpoint for the owner's side of the
// thread: reply and/or resolve. Owner-only enforcement is UI-level
// only in the staff app (design spec §0) -- this endpoint itself only
// checks that the caller holds a valid, active license for this
// practice, same trust boundary as every other authenticated write on
// this platform.

const { validateLicenseKey } = require('../_lib/license');

function supabaseHeaders(extra) {
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  return Object.assign({ apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' }, extra || {});
}
function rest(path) {
  return process.env.SUPABASE_URL + '/rest/v1/' + path;
}
const MAX_MESSAGE_LEN = 4000;

async function fetchByComplaintId(licenseHash, complaintId) {
  const r = await fetch(rest('dnt_complaints?license_hash=eq.' + encodeURIComponent(licenseHash) + '&complaint_id=eq.' + encodeURIComponent(complaintId) + '&select=complaint_id,access_token,data'), { headers: supabaseHeaders() });
  if (!r.ok) {
    const e = new Error('dnt_complaints lookup read failed: HTTP ' + r.status);
    e.code = 'UPSTREAM';
    throw e;
  }
  const rows = await r.json();
  return (Array.isArray(rows) && rows[0]) || null;
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'POST only' } }); return; }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) { res.status(500).json({ error: { message: 'Server configuration error' } }); return; }

  const authz = req.headers['authorization'] || '';
  const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : null;
  if (!licenseKey) { res.status(401).json({ error: { code: 'NO_LICENSE', message: 'Missing bearer license key' } }); return; }

  let lic;
  try {
    lic = await validateLicenseKey(licenseKey);
  } catch (err) {
    console.error('complaint-respond license validation error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error -- try again' } });
    return;
  }
  if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }

  const body = req.body || {};
  const complaintId = body.complaint_id;
  const action = body.action;
  const text = typeof body.text === 'string' ? body.text.trim() : '';
  if (!complaintId) { res.status(400).json({ error: { message: 'complaint_id is required' } }); return; }
  if (action !== 'reply' && action !== 'resolve') { res.status(400).json({ error: { message: "action must be 'reply' or 'resolve'" } }); return; }
  if (action === 'reply' && !text) { res.status(400).json({ error: { message: 'text is required for a reply' } }); return; }
  if (text.length > MAX_MESSAGE_LEN) { res.status(400).json({ error: { code: 'MESSAGE_TOO_LONG', message: 'Message is too long -- please keep it under ' + MAX_MESSAGE_LEN + ' characters' } }); return; }

  try {
    // Fresh read, right before writing -- the other half of design
    // spec §0's race-handling decision. Scoped by license_hash +
    // complaint_id together -- a valid key must never reach another
    // practice's record.
    const row = await fetchByComplaintId(lic.license_hash, complaintId);
    if (!row) { res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Complaint not found' } }); return; }

    const nowISO = new Date().toISOString();
    let messages = row.data.messages || [];
    if (action === 'reply' || (action === 'resolve' && text)) {
      messages = messages.concat([{ from: 'owner', text: text, at: nowISO }]);
    }
    const status = action === 'resolve' ? 'Resolved' : 'Awaiting Patient';
    const data = Object.assign({}, row.data, { messages: messages, status: status });

    const writeRes = await fetch(rest('dnt_complaints?on_conflict=license_hash,complaint_id'), {
      method: 'POST',
      headers: Object.assign({}, supabaseHeaders(), { Prefer: 'resolution=merge-duplicates,return=representation' }),
      body: JSON.stringify({ license_hash: lic.license_hash, app_id: 'sairndental', complaint_id: row.complaint_id, access_token: row.access_token, data: data, updated_at: nowISO })
    });
    if (!writeRes.ok) {
      const errBody = await writeRes.json().catch(() => null);
      console.error('SAIRNdental complaint-respond write error:', errBody);
      res.status(502).json({ error: { message: 'Could not save -- try again' } });
      return;
    }
    const writtenRows = await writeRes.json();
    const savedData = (Array.isArray(writtenRows) && writtenRows[0] && writtenRows[0].data) || data;
    res.status(200).json({ ok: true, status: savedData.status, messages: savedData.messages });
  } catch (err) {
    console.error('SAIRNdental complaint-respond error:', err.message);
    res.status(502).json({ error: { message: 'Could not save -- try again' } });
  }
};
