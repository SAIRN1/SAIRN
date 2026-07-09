// api/agent/poll.js
// The agent calls this in a loop (see agent/sairn-agent.js) to receive pending
// commands. Returns the single oldest pending command for this agent, or
// { command: null } if there's nothing waiting.
//
// TIMING NOTE (honest limitation, not hidden): this does a short bounded poll
// inside the function itself (checking every 1s for up to ~8s) to reduce empty
// round-trips, but it is NOT a true long-lived connection — Vercel serverless
// functions have hard execution time limits (10s on Hobby, up to 300s on Pro
// with config). The agent is written to re-call this endpoint immediately after
// each response, so the end-to-end behavior is "poll every ~8-10s," not instant
// push. That's a fine v1 latency for background sync jobs; it is NOT suitable
// for anything needing sub-second delivery — flag that clearly if this gets used
// for something more time-sensitive later.
//
// REQUIRES: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY set as Vercel env vars.

const crypto = require('crypto');

function hashToken(token) {
  return crypto.createHash('sha256').update(token).digest('hex');
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

module.exports = async (req, res) => {
  if (req.method !== 'POST' && req.method !== 'GET') {
    res.status(405).json({ error: { message: 'Method not allowed — GET or POST only' } });
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
  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY };

  let agent;
  try {
    const lookupRes = await fetch(
      SUPABASE_URL + '/rest/v1/sairn_agents?token_hash=eq.' + tokenHash + '&select=id,status',
      { headers }
    );
    const rows = await lookupRes.json();
    if (!lookupRes.ok || !Array.isArray(rows) || rows.length === 0) {
      res.status(401).json({ error: { message: 'Unknown or revoked agent token' } });
      return;
    }
    agent = rows[0];
    if (agent.status === 'revoked') {
      res.status(403).json({ error: { message: 'This agent has been revoked' } });
      return;
    }
  } catch (err) {
    console.error('api/agent/poll lookup error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }

  // Update last_seen_at (fire-and-forget; not critical to block the poll on this).
  fetch(SUPABASE_URL + '/rest/v1/sairn_agents?id=eq.' + agent.id, {
    method: 'PATCH',
    headers: { ...headers, 'Content-Type': 'application/json', Prefer: 'return=minimal' },
    body: JSON.stringify({ last_seen_at: new Date().toISOString() })
  }).catch((e) => console.error('poll heartbeat update failed:', e));

  const deadline = Date.now() + 8000;
  try {
    while (Date.now() < deadline) {
      const cmdRes = await fetch(
        SUPABASE_URL +
          '/rest/v1/sairn_agent_commands?agent_id=eq.' + agent.id +
          '&status=eq.pending&expires_at=gt.' + encodeURIComponent(new Date().toISOString()) +
          '&order=created_at.asc&limit=1',
        { headers }
      );
      const cmds = await cmdRes.json();
      if (Array.isArray(cmds) && cmds.length > 0) {
        const cmd = cmds[0];
        await fetch(SUPABASE_URL + '/rest/v1/sairn_agent_commands?id=eq.' + cmd.id, {
          method: 'PATCH',
          headers: { ...headers, 'Content-Type': 'application/json', Prefer: 'return=minimal' },
          body: JSON.stringify({ status: 'delivered', delivered_at: new Date().toISOString() })
        });
        res.status(200).json({
          command: { id: cmd.id, operation: cmd.operation, params: cmd.params }
        });
        return;
      }
      await sleep(1000);
    }
    res.status(200).json({ command: null });
  } catch (err) {
    console.error('api/agent/poll error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
};
