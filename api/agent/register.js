// api/agent/register.js
// Confirms an agent's bearer token is valid and marks it active. Called once by
// the agent on first startup (and harmlessly on every later startup too).
//
// Provisioning flow (v1, no UI yet — see scripts/create-agent.js):
//   1. SAIRN ops runs scripts/create-agent.js locally, which inserts a row into
//      sairn_agents and prints a one-time bearer token.
//   2. That token is given to the customer and placed in their agent/config.json.
//   3. The agent calls this endpoint on startup with that token; if it matches
//      a 'pending' or 'active' row, status flips to 'active' and last_seen_at updates.
//
// REQUIRES: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY set as Vercel env vars
// (same pair used by SAIRN's other Supabase-backed apps). Never hardcode either —
// Guardian check 22 blocks any push with a hardcoded key.

const crypto = require('crypto');

function hashToken(token) {
  return crypto.createHash('sha256').update(token).digest('hex');
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  const auth = req.headers['authorization'] || '';
  const token = auth.startsWith('Bearer ') ? auth.slice(7).trim() : null;
  if (!token) {
    res.status(401).json({ error: { message: 'Missing bearer token' } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  const tokenHash = hashToken(token);

  try {
    const lookupRes = await fetch(
      SUPABASE_URL + '/rest/v1/sairn_agents?token_hash=eq.' + tokenHash + '&select=id,customer_id,agent_name,status,plan_status,trial_ends_at',
      { headers: { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY } }
    );
    const rows = await lookupRes.json();
    if (!lookupRes.ok || !Array.isArray(rows) || rows.length === 0) {
      res.status(401).json({ error: { message: 'Unknown or revoked agent token' } });
      return;
    }
    const agent = rows[0];
    if (agent.status === 'revoked') {
      res.status(403).json({ error: { message: 'This agent has been revoked' } });
      return;
    }

    const updateRes = await fetch(
      SUPABASE_URL + '/rest/v1/sairn_agents?id=eq.' + agent.id,
      {
        method: 'PATCH',
        headers: {
          apikey: SERVICE_KEY,
          Authorization: 'Bearer ' + SERVICE_KEY,
          'Content-Type': 'application/json',
          Prefer: 'return=minimal'
        },
        body: JSON.stringify({ status: 'active', last_seen_at: new Date().toISOString() })
      }
    );
    if (!updateRes.ok) {
      const errText = await updateRes.text();
      console.error('agent register update failed:', errText);
      res.status(502).json({ error: { message: 'Registration update failed — try again' } });
      return;
    }

    res.status(200).json({
      ok: true,
      agent_id: agent.id,
      agent_name: agent.agent_name,
      customer_id: agent.customer_id,
      plan_status: agent.plan_status,
      trial_ends_at: agent.trial_ends_at
    });
  } catch (err) {
    console.error('api/agent/register error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
};
