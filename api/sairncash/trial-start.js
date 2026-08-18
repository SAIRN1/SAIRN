// api/sairncash/trial-start.js
// Creates a real, server-authoritative 30-day trial -- no Stripe
// dependency (Michael's 2026-08-18 decision). One trial per email;
// the only anti-abuse control in v1 (confirmed acceptable by Michael --
// renewal is admin-approval-gated anyway, see trial-renew.js).
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// REQUIRES migration: sql/sairncash_trial_schema.sql.
// See docs/superpowers/specs/2026-08-18-sairncash-trial-flow-design.md.

const crypto = require('crypto');
const { computeExpiry } = require('../_lib/sairncash-trial.js');

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'POST only' } }); return; }

  const email = req.body && req.body.email;
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    res.status(400).json({ error: { message: 'Valid email required' } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  try {
    const trialToken = crypto.randomBytes(32).toString('hex');
    const startedAt = Date.now();
    const expiresAt = computeExpiry(startedAt);

    const r = await fetch(SUPABASE_URL + '/rest/v1/sairncash_trial', {
      method: 'POST',
      headers: {
        apikey: SERVICE_KEY,
        Authorization: 'Bearer ' + SERVICE_KEY,
        'Content-Type': 'application/json',
        Prefer: 'return=minimal'
      },
      body: JSON.stringify({
        email: email,
        trial_token: trialToken,
        started_at: new Date(startedAt).toISOString(),
        expires_at: expiresAt
      })
    });

    if (r.status === 404) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Trial table not set up yet -- run sql/sairncash_trial_schema.sql in Supabase first.' } });
      return;
    }
    if (r.status === 409) {
      res.status(409).json({ error: { code: 'ALREADY_EXISTS', message: 'This email already has a SAIRNcash trial. Contact support if you need help accessing it.' } });
      return;
    }
    if (!r.ok) {
      const bodyText = await r.text().catch(() => '');
      console.error('SAIRNcash trial-start insert failed:', r.status, bodyText);
      res.status(502).json({ error: { message: 'Could not start trial -- try again' } });
      return;
    }

    res.status(200).json({ trialToken: trialToken, expiresAt: expiresAt });
  } catch (e) {
    console.error('SAIRNcash trial-start error:', e.message);
    res.status(502).json({ error: { message: 'Could not start trial -- try again' } });
  }
};
