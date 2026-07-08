// api/claude.js
// Shared Claude proxy for all SAIRN apps (StoneDesk, SAIRNbiz, SAIRNcode, SAIRNvet, and any future app).
// Every app's frontend calls this via PROXY = 'https://sairn.vercel.app/api/claude' — never api.anthropic.com directly.
//
// Request body (from frontend callClaude()): { app_id, is_demo, system, messages, max_tokens }
// Response shape matches the real Anthropic Messages API response so the frontend's existing
// `data.content[0].text` parsing works unchanged: { content: [{ type: "text", text: "..." }], ... }
// On error: { error: "demo_limit" } or { error: { message: "..." } } — frontend already checks both shapes.
//
// REQUIRES: ANTHROPIC_API_KEY set as a Vercel environment variable (Project Settings > Environment
// Variables). Never hardcode the key here — Guardian check 22 blocks any push with a hardcoded key.
//
// KNOWN LIMITATION (flagged, not hidden): demo_limit checking below is a best-effort, in-memory,
// per-instance counter. Serverless functions can run as multiple concurrent instances and reset on
// cold start, so this does NOT reliably cap usage or cost across real traffic. Before this proxy is
// exposed to real demo/customer traffic at scale, replace this with a persistent counter (Vercel KV
// or the Supabase project already used elsewhere in SAIRN) keyed by app_id + day.

const KNOWN_APP_IDS = ['stonedesk', 'sairnbiz', 'sairncode', 'sairnvet'];

// Best-effort only — see limitation note above. Resets on cold start / differs per instance.
const demoCallCounts = {};
const DEMO_DAILY_LIMIT = 200;

function getDemoKey(appId) {
  const day = new Date().toISOString().slice(0, 10);
  return appId + '|' + day;
}

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
  if (!body || typeof body !== 'object') {
    res.status(400).json({ error: { message: 'Missing request body' } });
    return;
  }

  const { app_id, is_demo, system, messages, max_tokens } = body;

  if (!app_id || !KNOWN_APP_IDS.includes(app_id)) {
    res.status(400).json({ error: { message: 'Missing or unrecognized app_id' } });
    return;
  }
  if (!messages || !Array.isArray(messages) || messages.length === 0) {
    res.status(400).json({ error: { message: 'messages array is required' } });
    return;
  }

  if (is_demo) {
    const key = getDemoKey(app_id);
    demoCallCounts[key] = (demoCallCounts[key] || 0) + 1;
    if (demoCallCounts[key] > DEMO_DAILY_LIMIT) {
      res.status(200).json({ error: 'demo_limit' });
      return;
    }
  }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    // Server misconfiguration — do not leak details to the client, but make it loud in logs.
    console.error('ANTHROPIC_API_KEY is not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  try {
    const anthropicRes = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-6',
        max_tokens: max_tokens || 1000,
        system: system || undefined,
        messages: messages
      })
    });

    const data = await anthropicRes.json();

    if (!anthropicRes.ok) {
      const message = (data && data.error && data.error.message) ? data.error.message : ('Anthropic API error ' + anthropicRes.status);
      res.status(anthropicRes.status).json({ error: { message } });
      return;
    }

    res.status(200).json(data);
  } catch (err) {
    console.error('api/claude proxy error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
};
