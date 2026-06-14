// ================================================================
// SAIRN Claude Proxy — api/claude.js (v4)
// Unified proxy for all SAIRN apps
// Consumer: claude-haiku-4-5 (cost-efficient)
// B2B: claude-sonnet-4-6 (full power)
// Michael L. Dibert · SAIRN Technologies · 2026
// ================================================================

import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const HAIKU  = 'claude-haiku-4-5-20251001';
const SONNET = 'claude-sonnet-4-6';

// B2B apps get Sonnet (full Claude power, higher limit)
const B2B_APPS = new Set([
  'stonedesk','fabricor','sairntrade','sairnbuild','sairnscape',
  'sairnhr','sairnacc','sairnlaw','sairncode','sairndesign',
  'sairnvet','sairnvetglobal','sairncare','sairnfuneral'
]);

// Rate limiting: separate buckets for B2B vs consumer
const calls = new Map();

function getKey(req, appId) {
  const ip = req.headers['x-forwarded-for']?.split(',')[0]?.trim() || 'unknown';
  const today = new Date().toISOString().slice(0, 10);
  return `${ip}_${appId}_${today}`;
}

const LIMITS = {
  b2b:      50,   // 50 calls/day for B2B (generous for demo)
  consumer: 15    // 15 calls/day for consumer apps
};

const KNOWN_APPS = new Set([
  // Consumer
  'sairntype','lingual','health','money','legal','study','roam','senior',
  'mind','kitchen','family','career','home','shield','daily',
  // B2B
  'stonedesk','fabricor','sairntrade','sairnbuild','sairnscape',
  'sairnhr','sairnacc','sairnlaw','sairncode','sairndesign',
  'sairnvet','sairnvetglobal','sairncare','sairnfuneral',
  // Platform
  'contractor','biz','pay','hr','sairnlearn','sairnhope','sairnfriend',
  'sairnflow','sairnfix','sairngrow','sairngive','sairngov',
  'sairniq','enterprise','sairnhealth','sairncomm','sairnvets',
  // Internal
  'test','doc_analysis','followup_gen','memory_builder'
]);

export default async function handler(req, res) {
  const origin = req.headers.origin || '*';
  res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { max_tokens, system, messages, app_id, is_demo, model: requestedModel } = req.body || {};
  if (!messages?.length) return res.status(400).json({ error: 'Messages required' });

  // Validate app_id
  const appIdValid = !app_id || KNOWN_APPS.has(app_id) || app_id?.startsWith('sairn') || app_id === 'fabricor';
  if (!appIdValid) return res.status(400).json({ error: 'Invalid app_id' });

  const isB2B = B2B_APPS.has(app_id);
  const limit = isB2B ? LIMITS.b2b : LIMITS.consumer;
  const key   = getKey(req, app_id || 'unknown');
  const count = calls.get(key) || 0;

  if (count >= limit) {
    return res.status(429).json({
      error: 'demo_limit',
      message: isB2B
        ? 'Daily demo limit reached. Sign up at sairn.vercel.app for unlimited access.'
        : 'You have used your free questions today. Sign up for unlimited access.',
      upgrade: true,
      limit,
      used: count
    });
  }
  calls.set(key, count + 1);

  // Model selection: B2B gets Sonnet, consumer gets Haiku
  // Allow explicit override but always use sonnet for B2B
  const model = isB2B ? SONNET : (requestedModel === SONNET ? HAIKU : HAIKU);

  const params = {
    model,
    max_tokens: Math.min(max_tokens || 1000, isB2B ? 4000 : 1000),
    messages: messages.slice(-20)
  };
  if (system) params.system = system.slice(0, 8000);

  try {
    const response = await anthropic.messages.create(params);
    // Add model used to response for debugging
    return res.status(200).json({ ...response, _model: model, _remaining: limit - count - 1 });
  } catch (err) {
    console.error('[Claude Proxy Error]', err.message);
    return res.status(err.status || 500).json({ error: { message: err.message } });
  }
}
