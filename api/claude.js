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
//
// CORRECTED 2026-07-26: KNOWN_APP_IDS was missing 9 of 13 live apps (SAIRNscape, SAIRNbuild,
// SAIRNlaw, SAIRNdesign, SAIRNcare, SAIRNfuneral, SAIRNmechanical, SAIRNhr, SAIRNacc) — those apps'
// AI features were returning a 400 "unrecognized app_id" error against this proxy. Cross-referenced
// against sairn-guardian-v2's App File Map (the platform's own source of truth for which apps exist)
// rather than guessing. Guardian's Check 3 now also verifies an app_id exists in THIS list, not just
// that the app's own frontend code includes an app_id — the two are different checks, and only the
// first one was covered before.
//
// Accepts image content blocks in `messages` unmodified — this proxy has always forwarded `messages`
// straight through to the Anthropic API without inspecting shape, so vision (base64 image + text in a
// message) works with zero changes here once an app's frontend sends it in the standard API format.

const KNOWN_APP_IDS = [
  'stonedesk', 'sairnbiz', 'sairnscape', 'sairncode', 'sairnbuild',
  'sairnlaw', 'sairndesign', 'sairncare', 'sairnvet', 'sairnfuneral',
  'sairnmechanical', 'sairnhr', 'sairnacc', 'sairngrounds', 'sairnlegacy'
];

// Server tools a frontend is allowed to request. Whitelisted by exact type
// string (not passed through unchecked) because this endpoint has no other
// auth beyond a client-supplied app_id -- an unrestricted `tools` passthrough
// would let any caller run billed web searches against our Anthropic key.
// max_uses is also server-capped below regardless of what the client sends.
const ALLOWED_TOOL_TYPES = ['web_search_20250305'];
const MAX_TOOL_USES_CEILING = 5;

function sanitizeTools(tools) {
  if (!Array.isArray(tools)) return undefined;
  const clean = tools
    .filter((t) => t && ALLOWED_TOOL_TYPES.includes(t.type))
    .map((t) => {
      const out = { type: t.type, name: t.name || 'web_search' };
      const requested = Number(t.max_uses) || MAX_TOOL_USES_CEILING;
      out.max_uses = Math.max(1, Math.min(requested, MAX_TOOL_USES_CEILING));
      return out;
    });
  return clean.length ? clean : undefined;
}

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

  const { app_id, is_demo, system, messages, max_tokens, tools } = body;

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
        messages: messages,
        tools: sanitizeTools(tools)
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
