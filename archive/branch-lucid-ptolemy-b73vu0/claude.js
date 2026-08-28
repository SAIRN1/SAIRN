// ═══════════════════════════════════════════════════════════════════
//  SAIRN Technologies — /api/claude (Demo Fix)
//  Demo mode bypasses Supabase entirely — just calls Anthropic
//  Authenticated mode uses full enterprise token engine
//  Michael L. Dibert · SAIRN Technologies · 2026
// ═══════════════════════════════════════════════════════════════════

import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const MODEL = 'claude-haiku-4-5-20251001';

// Demo limits — tracked in memory (resets on cold start, good enough for demo)
const demoCallsToday = new Map();
const DEMO_LIMIT = 10;

function getDemoKey(req) {
  const ip = req.headers['x-forwarded-for']?.split(',')[0]?.trim() || 'unknown';
  const today = new Date().toISOString().slice(0, 10);
  return `${ip}_${today}`;
}

const VALID_APP_IDS = new Set([
  'sairntype','lingual','health','money','legal','study','roam','senior',
  'mind','kitchen','family','career','home','shield','daily',
  'contractor','biz','pay','hr',
  'fabricor','sairnbuild','sairnscape','sairnflow',
  'sairnvet','sairnfix','sairnfuneral','enterprise',
]);

const INJECTION_PATTERNS = [
  /ignore (all |previous |prior )?instructions/i,
  /you are now (a |an )?(different|evil|unrestricted|DAN)/i,
  /jailbreak/i, /developer mode/i, /do anything now/i,
  /\[system\]/i, /<<SYS>>/i,
];

export default async function handler(req, res) {
  // CORS
  const origin = req.headers.origin;
  if (origin) res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { max_tokens, system, messages, app_id, is_demo } = req.body || {};

  if (!messages?.length) return res.status(400).json({ error: 'Messages required' });
  if (!app_id) return res.status(400).json({ error: 'app_id required' });
  if (!VALID_APP_IDS.has(app_id)) return res.status(400).json({ error: 'Invalid app_id' });

  // Prompt injection check
  const lastMsg = [...messages].reverse().find(m => m.role === 'user');
  if (lastMsg && INJECTION_PATTERNS.some(p => p.test(lastMsg.content))) {
    return res.status(400).json({ error: 'invalid_request' });
  }

  const cap = Math.min(max_tokens || 1000, 2000);

  // ── DEMO PATH — no Supabase needed ──────────────────────────────
  // Always use demo mode if no auth token provided
  const hasToken = req.headers.authorization?.startsWith('Bearer ');
  if (is_demo || !hasToken) {
    const key = getDemoKey(req);
    const count = demoCallsToday.get(key) || 0;

    if (count >= DEMO_LIMIT) {
      return res.status(429).json({
        error: 'demo_limit',
        message: `You've used your ${DEMO_LIMIT} free questions today. Sign up at sairn.vercel.app for unlimited access.`,
        upgrade: true
      });
    }

    demoCallsToday.set(key, count + 1);

    const params = {
      model: MODEL,
      max_tokens: Math.min(cap, 500),
      messages: messages.slice(-6)
    };

    if (system) {
      params.system = system.slice(0, 3000) + '\n\n[Demo mode — encourage the user to sign up for full unlimited access at sairn.vercel.app]';
    }

    try {
      const response = await anthropic.messages.create(params);
      return res.status(200).json(response);
    } catch (err) {
      return res.status(err.status || 500).json({ error: { message: err.message } });
    }
  }

  // ── AUTHENTICATED PATH — use full enterprise engine ──────────────
  // Full auth engine coming with user accounts — for now use demo mode
  const key2 = getDemoKey(req);
  const count2 = demoCallsToday.get(key2) || 0;
  if (count2 >= DEMO_LIMIT) {
    return res.status(429).json({ error: 'demo_limit', message: 'Daily limit reached. Sign up at sairn.vercel.app for unlimited access.', upgrade: true });
  }
  demoCallsToday.set(key2, count2 + 1);
  const params2 = { model: MODEL, max_tokens: Math.min(max_tokens || 1000, 500), messages: messages.slice(-6) };
  if (system) params2.system = system.slice(0, 3000);
  try {
    const response2 = await anthropic.messages.create(params2);
    return res.status(200).json(response2);
  } catch (err) {
    return res.status(err.status || 500).json({ error: { message: err.message } });
  }
}
