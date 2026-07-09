// api/agent/result.js
// The agent calls this after executing a delivered command, to report the
// result (or an error) back. SAIRN apps read completed results by querying
// sairn_agent_commands directly via the Supabase client already used elsewhere
// in the apps — no separate "fetch result" endpoint is needed for that side.
//
// REQUIRES: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY set as Vercel env vars.

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

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) {
      res.status(400).json({ error: { message: 'Invalid JSON body' } });
      return;
    }
  }
  const { command_id, ok, result, error } = body || {};
  if (!command_id) {
    res.status(400).json({ error: { message: 'command_id is required' } });
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
  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY };

  try {
    // Verify this token owns the agent that owns this command before accepting the result.
    const lookupRes = await fetch(
      SUPABASE_URL + '/rest/v1/sairn_agents?token_hash=eq.' + tokenHash + '&select=id,status',
      { headers }
    );
    const agents = await lookupRes.json();
    if (!lookupRes.ok || !Array.isArray(agents) || agents.length === 0 || agents[0].status === 'revoked') {
      res.status(401).json({ error: { message: 'Unknown or revoked agent token' } });
      return;
    }
    const agentId = agents[0].id;

    const cmdRes = await fetch(
      SUPABASE_URL + '/rest/v1/sairn_agent_commands?id=eq.' + command_id + '&agent_id=eq.' + agentId + '&select=id',
      { headers }
    );
    const cmds = await cmdRes.json();
    if (!cmdRes.ok || !Array.isArray(cmds) || cmds.length === 0) {
      res.status(404).json({ error: { message: 'Command not found for this agent' } });
      return;
    }

    const patchBody = ok
      ? { status: 'completed', result: result || {}, completed_at: new Date().toISOString() }
      : { status: 'failed', error: String(error || 'Unknown agent error'), completed_at: new Date().toISOString() };

    const updateRes = await fetch(SUPABASE_URL + '/rest/v1/sairn_agent_commands?id=eq.' + command_id, {
      method: 'PATCH',
      headers: { ...headers, 'Content-Type': 'application/json', Prefer: 'return=minimal' },
      body: JSON.stringify(patchBody)
    });
    if (!updateRes.ok) {
      const errText = await updateRes.text();
      console.error('agent result update failed:', errText);
      res.status(502).json({ error: { message: 'Result update failed — try again' } });
      return;
    }

    res.status(200).json({ ok: true });
  } catch (err) {
    console.error('api/agent/result error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
};
