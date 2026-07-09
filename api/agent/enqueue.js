// api/agent/enqueue.js
// Called BY SAIRN apps (browser-side, via the existing proxy pattern) to queue
// an operation for a specific customer's on-prem agent. The agent picks it up
// on its next poll (see api/agent/poll.js) and the app reads the result back by
// polling sairn_agent_commands for that command's id via the Supabase client
// already used elsewhere in the apps.
//
// SECURITY NOTE — READ BEFORE USING THIS BEYOND A CONTROLLED PILOT:
// This endpoint currently authorizes a request by nothing more than the caller
// knowing a valid agent_id (a UUID). There is no per-customer session/user auth
// layer here, because none of the current SAIRN apps have one yet — they're
// client-side, PIN-gated single-tenant demos, not backend-authenticated
// multi-tenant systems. That's fine for a single-customer pilot where the
// agent_id isn't guessable/shared, but it must NOT be treated as secure
// multi-tenant isolation. Before more than one customer relies on this in
// parallel, add real per-customer auth (e.g., a signed session token issued at
// login, checked here against the agent's customer_id) so one customer's app
// instance cannot enqueue commands against another customer's agent.
//
// REQUIRES: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY set as Vercel env vars.

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) {
      res.status(400).json({ error: { message: 'Invalid JSON body' } });
      return;
    }
  }
  const { agent_id, operation, params } = body || {};
  if (!agent_id || !operation) {
    res.status(400).json({ error: { message: 'agent_id and operation are required' } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }
  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };

  try {
    const agentRes = await fetch(SUPABASE_URL + '/rest/v1/sairn_agents?id=eq.' + agent_id + '&select=id,status', { headers });
    const agents = await agentRes.json();
    if (!agentRes.ok || !Array.isArray(agents) || agents.length === 0) {
      res.status(404).json({ error: { message: 'Unknown agent_id' } });
      return;
    }
    if (agents[0].status !== 'active') {
      res.status(409).json({ error: { message: 'Agent is not active (status: ' + agents[0].status + ')' } });
      return;
    }

    const insertRes = await fetch(SUPABASE_URL + '/rest/v1/sairn_agent_commands', {
      method: 'POST',
      headers: { ...headers, Prefer: 'return=representation' },
      body: JSON.stringify({ agent_id, operation, params: params || {} })
    });
    const inserted = await insertRes.json();
    if (!insertRes.ok) {
      console.error('enqueue insert failed:', inserted);
      res.status(502).json({ error: { message: 'Could not queue command — try again' } });
      return;
    }

    res.status(200).json({ ok: true, command_id: inserted[0].id });
  } catch (err) {
    console.error('api/agent/enqueue error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
};
