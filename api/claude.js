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

const { checkAiRateLimit } = require('./_lib/ai-rate-limit');

const KNOWN_APP_IDS = [
  'stonedesk', 'sairnbiz', 'sairnscape', 'sairncode', 'sairnbuild',
  'sairnlaw', 'sairndesign', 'sairncare', 'sairnvet', 'sairnfuneral',
  'sairnmechanical', 'sairnhr', 'sairnacc', 'sairngrounds', 'sairnlegacy',
  // SAIRNcash (2026-08-10) -- pivot from SAIRNtype. Its own callClaude()
  // calls this shared proxy directly (is_demo:false, gated upstream by
  // its own real Stripe subscription check) rather than a duplicate
  // per-app pass-through -- SAIRNtype's original api/claude.js had no
  // app_id allowlist, no rate limiting, and read the wrong env var name
  // (`mykey`); not ported.
  'sairncash',
  // SAIRNdental (2026-08-10) -- for the insurance-card capture flow
  // (docs/superpowers/specs/2026-08-10-sairndental-design.md §1) and
  // any future AI use. Standard license-key-gated B2B app, is_demo
  // used the same way every other non-SAIRNcash app on this platform
  // already does.
  'sairndental',
  // SAIRNsenior (2026-08-20) -- MISSED at build time despite having a real
  // AI Assistant panel calling this proxy with app_id:'sairnsenior' since
  // Phase 1 (3157ac9): every call has been 400ing with "unrecognized
  // app_id" and failing silently into the chat's generic "AI request
  // failed" message. Found while wiring the agentic ops-attention tool --
  // same missing-from-allowlist bug class as the 2026-07-26 correction
  // above, caught live via a direct curl against this proxy before
  // assuming the existing chat worked.
  'sairnsenior'
];

// Server tools a frontend is allowed to request. Server-executed tool TYPES
// are whitelisted by exact type string (not passed through unchecked)
// because this endpoint has no other auth beyond a client-supplied app_id --
// an unrestricted server-tool passthrough would let any caller run billed
// actions (web search) against our Anthropic key. max_uses is also
// server-capped below regardless of what the client sends.
//
// CUSTOM (client-executed) tools are a different risk category, added
// 2026-08-09: Anthropic never executes them -- the model only returns a
// tool_use request naming the tool + arguments, and the calling app decides
// locally whether and how to run it. No cost or external call happens from
// the tool definition alone, so these pass through unmodified rather than
// being type-whitelisted like server tools. A tool counts as "custom" if it
// has no `type` field, or an explicit `type: 'custom'` -- both are valid
// Anthropic custom-tool shapes.
const ALLOWED_SERVER_TOOL_TYPES = ['web_search_20250305'];
const MAX_TOOL_USES_CEILING = 5;

function sanitizeTools(tools) {
  if (!Array.isArray(tools)) return undefined;
  const clean = tools
    .filter((t) => t && (t.type === undefined || t.type === 'custom' || ALLOWED_SERVER_TOOL_TYPES.includes(t.type)))
    .map((t) => {
      if (t.type === undefined || t.type === 'custom') return t;
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

// Extracted (2026-08-13, SAIRNlaw AI Chain of Custody server-side capture) so
// api/law-auth.js's ai_generate action can call the real Anthropic API
// in-process -- one real server round trip that also writes the audit log,
// not a second HTTP hop back through this same endpoint. Returns a plain
// result object, never throws, so every caller (this file's own HTTP
// handler below, and api/law-auth.js) handles success/failure the same way.
async function callAnthropic({ system, messages, max_tokens, tools }) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    // Server misconfiguration — do not leak details to the client, but make it loud in logs.
    console.error('ANTHROPIC_API_KEY is not set in environment variables');
    return { ok: false, status: 500, error: { message: 'Server configuration error — contact support' } };
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
      return { ok: false, status: anthropicRes.status, error: { message } };
    }

    return { ok: true, status: 200, data };
  } catch (err) {
    console.error('api/claude proxy error:', err);
    return { ok: false, status: 502, error: { message: 'Upstream connection error — try again' } };
  }
}

async function claudeProxyHandler(req, res) {
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
    // In-memory pre-check, kept deliberately. It is unreliable on its own
    // (see the KNOWN LIMITATION note at the top of this file) but it is free
    // and catches repeat traffic hitting the same warm instance without a DB
    // round trip. It is no longer the only control -- see below.
    const key = getDemoKey(app_id);
    demoCallCounts[key] = (demoCallCounts[key] || 0) + 1;
    if (demoCallCounts[key] > DEMO_DAILY_LIMIT) {
      res.status(200).json({ error: 'demo_limit' });
      return;
    }

    // The real, persistent, cross-instance limit the KNOWN LIMITATION note
    // above has always asked for (added 2026-08-20, firewall audit layer 22).
    // Supabase-backed sliding window, same pattern as api/_lib/courtlistener.js.
    //
    // SHIPS IN OBSERVE MODE: 10 of 11 live apps send is_demo:true, and because
    // the in-memory counter kept resetting, this limit has effectively never
    // been enforced against real traffic. Enabling enforcement blind would risk
    // a platform-wide outage on a threshold nobody has measured. It records and
    // reports instead, until SAIRN_AI_RATE_LIMIT_MODE=enforce is set
    // deliberately. Fails open on any infrastructure problem.
    const rl = await checkAiRateLimit(app_id);
    if (!rl.allowed) {
      res.status(200).json({ error: 'demo_limit' });
      return;
    }
  }

  const result = await callAnthropic({ system, messages, max_tokens, tools });
  if (!result.ok) {
    res.status(result.status).json({ error: result.error });
    return;
  }
  res.status(200).json(result.data);
}

claudeProxyHandler.sanitizeTools = sanitizeTools;
claudeProxyHandler.callAnthropic = callAnthropic;
claudeProxyHandler.getDemoKey = getDemoKey;
claudeProxyHandler.demoCallCounts = demoCallCounts;
claudeProxyHandler.DEMO_DAILY_LIMIT = DEMO_DAILY_LIMIT;
module.exports = claudeProxyHandler;
