// api/sairncash/trial-verify.js
// Re-verifies a SAIRNcash trial against the real server-side record --
// called once per app load (mirrors verify.js's subscriptionId
// re-verification branch). Never trusts a client-supplied date; expiry
// is always computed from this table's own expires_at compared to this
// request's own server clock.
//
// Side effect: if a trial is found expired but its status column still
// says 'active', flips it to 'expired' here (best-effort, does not fail
// the response if this write fails) -- keeps the table honest for
// direct Supabase-dashboard inspection instead of silently staying
// 'active' forever after the real expiry passes.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// See docs/superpowers/specs/2026-08-18-sairncash-trial-flow-design.md.

const { isTrialValid, daysLeft } = require('../_lib/sairncash-trial.js');

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'POST only' } }); return; }

  const trialToken = req.body && req.body.trialToken;
  if (!trialToken) {
    res.status(400).json({ error: { message: 'Missing trialToken' } });
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
    const r = await fetch(
      SUPABASE_URL + '/rest/v1/sairncash_trial?trial_token=eq.' + encodeURIComponent(trialToken) + '&select=id,status,expires_at',
      { headers: { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY } }
    );
    if (r.status === 404) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Trial table not set up yet -- run sql/sairncash_trial_schema.sql in Supabase first.' } });
      return;
    }
    if (!r.ok) {
      const bodyText = await r.text().catch(() => '');
      console.error('SAIRNcash trial-verify lookup failed:', r.status, bodyText);
      res.status(502).json({ error: { message: 'Could not verify trial' } });
      return;
    }
    const rows = await r.json();
    if (!rows || rows.length === 0) {
      res.status(200).json({ valid: false });
      return;
    }
    const row = rows[0];
    const now = Date.now();
    const valid = isTrialValid(row, now);

    if (!valid && row.status === 'active') {
      // Best-effort write-back; a failure here doesn't change the real
      // answer this response already computed.
      fetch(
        SUPABASE_URL + '/rest/v1/sairncash_trial?trial_token=eq.' + encodeURIComponent(trialToken),
        {
          method: 'PATCH',
          headers: {
            apikey: SERVICE_KEY,
            Authorization: 'Bearer ' + SERVICE_KEY,
            'Content-Type': 'application/json',
            Prefer: 'return=minimal'
          },
          body: JSON.stringify({ status: 'expired' })
        }
      ).catch((e) => console.error('SAIRNcash trial-verify status write-back failed:', e.message));
    }

    // customerId (2026-08-18 sync fix): the trial row's own real uuid,
    // same role Stripe's customer id plays for a paid subscriber -- this
    // is what lets a trial user get real Firebase sync at all. Only
    // returned when valid, matching the same trust boundary
    // reverifySubscription() already uses for paid customerId (an
    // expired/unknown trial gets no sync identity either).
    res.status(200).json({
      valid: valid,
      expiresAt: row.expires_at,
      daysLeft: daysLeft(row.expires_at, now),
      customerId: valid ? row.id : null
    });
  } catch (e) {
    console.error('SAIRNcash trial-verify error:', e.message);
    res.status(502).json({ error: { message: 'Could not verify trial' } });
  }
};
