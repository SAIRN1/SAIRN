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

  // -- THE RETRY KEY. Item 6, 2026-09-14. --------------------------------
  // This insert had no key, no unique constraint and no read-before-write, so
  // a retry after a lost response queued a SECOND command and api/agent/poll.js
  // handed it to the agent to execute again. What gets duplicated here is an
  // arbitrary OPERATION, not a log line, which is why this was the sharpest of
  // the unguarded writes triaged on 2026-09-14.
  //
  // OPTIONAL, because this endpoint has live pilot callers. Without a key the
  // behaviour is exactly what it was, duplicate-on-retry included. Requiring
  // one would break every existing caller to fix a failure they may not hit.
  //
  // NOT HASHED, unlike sairncash_trial's key, and the difference is the reason
  // rather than the shape: that key retrieves a trial token, so holding it is
  // holding a credential. This one retrieves nothing -- enqueue already
  // authorises on agent_id alone, as this file's own security note says.
  const idem = body && body.idempotency_key;
  if (idem !== undefined && idem !== null && idem !== '') {
    // Refused rather than ignored: a caller who sends a malformed key and gets
    // a 200 would believe their retry is protected when it is not.
    if (typeof idem !== 'string' || !/^[A-Za-z0-9_.:-]{16,128}$/.test(idem)) {
      res.status(400).json({ error: { code: 'BAD_IDEMPOTENCY_KEY',
        message: 'idempotency_key must be 16-128 characters of [A-Za-z0-9_.:-]. It is optional; a malformed one is refused rather than ignored, because a caller who thinks their retry is protected and is not would queue the command twice.' } });
      return;
    }
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
    const agentRes = await fetch(SUPABASE_URL + '/rest/v1/sairn_agents?id=eq.' + agent_id + '&select=id,status,plan_status,trial_ends_at', { headers });
    const agents = await agentRes.json();
    if (!agentRes.ok || !Array.isArray(agents) || agents.length === 0) {
      res.status(404).json({ error: { message: 'Unknown agent_id' } });
      return;
    }
    const agent = agents[0];
    if (agent.status !== 'active') {
      res.status(409).json({ error: { message: 'Agent is not active (status: ' + agent.status + ')' } });
      return;
    }
    if (agent.plan_status === 'trial' && new Date(agent.trial_ends_at) < new Date()) {
      res.status(402).json({
        error: { code: 'TRIAL_EXPIRED', message: 'This agent\'s 30-day trial has ended. Activate a paid plan to resume access.' }
      });
      return;
    }
    if (agent.plan_status === 'canceled') {
      res.status(402).json({ error: { code: 'PLAN_CANCELED', message: 'This agent\'s plan has been canceled.' } });
      return;
    }

    const insertRes = await fetch(SUPABASE_URL + '/rest/v1/sairn_agent_commands', {
      method: 'POST',
      headers: { ...headers, Prefer: 'return=representation' },
      // THE COLUMN IS SENT ONLY WHEN THERE IS A KEY. PostgREST answers an
      // unknown column with 400, so sending `idempotency_key: null` before
      // sql/sairn_agent_commands_idempotency_2026-09-14.sql has run would
      // break EVERY enqueue, including callers who never asked for this.
      // Two files, one change, one deployed -- Guardian check 29's shape, and
      // the deploy order is code first, so the code must work without it.
      body: JSON.stringify(Object.assign(
        { agent_id, operation, params: params || {} },
        // The conditional is kept even though JSON.stringify would DROP an
        // `undefined` value on its own: `idem` is undefined here, not null,
        // and the two serialise differently. sairncash/trial-start.js holds a
        // null and genuinely needs this; someone reading both should not
        // "simplify" this one and then copy the simplification there, where it
        // sends the column and 400s every call before the migration runs.
        idem ? { idempotency_key: idem } : {}))
    });
    const inserted = await insertRes.json().catch(() => null);
    if (!insertRes.ok) {
      // -- THE RETRY PATH ---------------------------------------------------
      // 409 means this (agent_id, idempotency_key) is already queued. Return
      // the ORIGINAL command_id: the caller then polls the same command rather
      // than a duplicate, which is the whole point.
      if (insertRes.status === 409 && idem) {
        const look = await fetch(SUPABASE_URL + '/rest/v1/sairn_agent_commands'
          + '?agent_id=eq.' + encodeURIComponent(agent_id)
          + '&idempotency_key=eq.' + encodeURIComponent(idem)
          + '&select=id&limit=1', { headers });
        // A FAILED LOOKUP IS NOT "NO SUCH COMMAND". Falling through to the
        // generic 502 would be honest but would lose the one fact the caller
        // needs, so the message says the command IS queued.
        if (look.ok) {
          const rows = await look.json().catch(() => null);
          if (Array.isArray(rows) && rows[0] && rows[0].id) {
            res.status(200).json({ ok: true, command_id: rows[0].id, retried: true });
            return;
          }
        }
        res.status(502).json({ error: { code: 'ALREADY_QUEUED_LOOKUP_FAILED',
          message: 'This command is already queued under that idempotency key, but its id could not be read back. Do NOT retry with a new key -- that would queue it twice. Retry with the same key.' } });
        return;
      }
      // An unknown column is not an outage, and it is reachable only for a
      // caller who sent a key. Name the migration rather than telling them to
      // try again forever.
      const detail = JSON.stringify(inserted || '');
      if (idem && /idempotency_key/.test(detail)) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED',
          message: 'Retry-safe enqueue is not set up yet -- run sql/sairn_agent_commands_idempotency_2026-09-14.sql in Supabase. Retry without idempotency_key to queue the command the old way.' } });
        return;
      }
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
