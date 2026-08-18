// api/sairncash/trial-renew.js
// Admin-only: grants the next real 30-day trial window. Gated by
// Authorization: Bearer SAIRNCASH_ADMIN_SECRET, same shape as
// api/sairndental/send-reminder.js's CRON_SECRET gate -- fails closed
// (500) if the env var itself is unset, 401 if the header is
// missing/wrong. Never callable from sairncash.html; confirmed by
// Michael 2026-08-18 that renewal is a manual-approval action, not
// self-service -- this is the only write path that can extend
// expires_at.
//
// Sets a fresh 30-day window from the moment of approval (not
// additive -- doesn't stack onto whatever time was left).
//
// REQUIRES env: SAIRNCASH_ADMIN_SECRET, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// See docs/superpowers/specs/2026-08-18-sairncash-trial-flow-design.md.

const { computeExpiry } = require('../_lib/sairncash-trial.js');

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'POST only' } });
    return;
  }
  if (!process.env.SAIRNCASH_ADMIN_SECRET) {
    console.error('SAIRNCASH_ADMIN_SECRET not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error' } });
    return;
  }
  if (req.headers.authorization !== 'Bearer ' + process.env.SAIRNCASH_ADMIN_SECRET) {
    res.status(401).json({ error: { message: 'Unauthorized' } });
    return;
  }

  const email = req.body && req.body.email;
  const note = (req.body && req.body.note) || null;
  if (!email) {
    res.status(400).json({ error: { message: 'Missing email' } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error' } });
    return;
  }

  try {
    const lookupR = await fetch(
      SUPABASE_URL + '/rest/v1/sairncash_trial?email=eq.' + encodeURIComponent(email) + '&select=renewal_count',
      { headers: { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY } }
    );
    if (!lookupR.ok) {
      res.status(502).json({ error: { message: 'Could not look up trial' } });
      return;
    }
    const rows = await lookupR.json();
    if (!rows || rows.length === 0) {
      res.status(404).json({ error: { message: 'No trial found for that email' } });
      return;
    }

    const now = Date.now();
    const expiresAt = computeExpiry(now);
    const nextRenewalCount = (rows[0].renewal_count || 0) + 1;

    const patchR = await fetch(
      SUPABASE_URL + '/rest/v1/sairncash_trial?email=eq.' + encodeURIComponent(email),
      {
        method: 'PATCH',
        headers: {
          apikey: SERVICE_KEY,
          Authorization: 'Bearer ' + SERVICE_KEY,
          'Content-Type': 'application/json',
          Prefer: 'return=minimal'
        },
        body: JSON.stringify({
          status: 'active',
          expires_at: expiresAt,
          renewal_count: nextRenewalCount,
          last_renewed_at: new Date(now).toISOString(),
          last_renewed_note: note
        })
      }
    );
    if (!patchR.ok) {
      const bodyText = await patchR.text().catch(() => '');
      console.error('SAIRNcash trial-renew patch failed:', patchR.status, bodyText);
      res.status(502).json({ error: { message: 'Could not renew trial' } });
      return;
    }

    res.status(200).json({ ok: true, expiresAt: expiresAt, renewalCount: nextRenewalCount });
  } catch (e) {
    console.error('SAIRNcash trial-renew error:', e.message);
    res.status(502).json({ error: { message: 'Could not renew trial' } });
  }
};
