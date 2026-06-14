// ================================================================
// SAIRN Claude Proxy -- api/claude.js (v6)
// License keys stored in SAIRN_KEYS env var (Vercel-safe, no hyphens)
// Format: "KEY1:app:shop:plan|KEY2:app:shop:plan"
// Example: "SD01_2025_ALPHA:stonedesk:Granite Works:founding"
// Michael L. Dibert -- SAIRN Technologies -- 2026
// ================================================================

import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const HAIKU  = 'claude-haiku-4-5-20251001';
const SONNET = 'claude-sonnet-4-6';

const B2B_APPS = new Set([
  'stonedesk','fabricor','sairnbuild','sairnscape','sairnlaw',
  'sairncode','sairndesign','sairnvet','sairnvetglobal','sairncare',
  'sairnfuneral','sairnmechanical','sairntrade','sairnhr','sairnacc'
]);

// ── LICENSE STORE ────────────────────────────────────────────
// Env var: SAIRN_KEYS (letters, digits, underscores only -- Vercel safe)
// Value format: "KEY:app:shop:plan|KEY2:app:shop:plan"
// Key format:   "SD01_2025_ALPHA" (underscores, no hyphens)
// To add a customer: append "|SD02_2025_BETA:stonedesk:Bay Stone:founding"
function getLicenses() {
  const raw = process.env.SAIRN_KEYS || '';
  const map = new Map();
  if (!raw.trim()) return map;
  raw.split('|').forEach(entry => {
    const parts = entry.trim().split(':');
    if (parts.length >= 2) {
      // parts: [key, app, shop, plan]
      map.set(parts[0].toUpperCase(), {
        app:  parts[1] || 'all',
        shop: parts[2] || 'Licensed Shop',
        plan: parts[3] || 'standard'
      });
    }
  });
  return map;
}

function validateLicense(key, appId) {
  if (!key || key.length < 4) return { valid: false };
  const store = getLicenses();
  const k = key.toUpperCase().replace(/-/g, '_'); // accept hyphens too, normalize
  const entry = store.get(k);
  if (!entry) return { valid: false };
  if (entry.app !== 'all' && entry.app !== appId) return { valid: false };
  return { valid: true, shop: entry.shop, plan: entry.plan };
}

// ── RATE LIMITING (demo only) ────────────────────────────────
const calls = new Map();
function getRLKey(req, appId) {
  const ip = (req.headers['x-forwarded-for'] || '').split(',')[0].trim() || 'unknown';
  return ip + '_' + appId + '_' + new Date().toISOString().slice(0, 10);
}
const DEMO_LIMITS = { b2b: 50, consumer: 15 };

const KNOWN_APPS = new Set([
  'sairntype','lingual','health','money','legal','study','roam','senior',
  'stonedesk','fabricor','sairnbuild','sairnscape','sairnlaw','sairncode',
  'sairndesign','sairnvet','sairnvetglobal','sairncare','sairnfuneral',
  'sairnmechanical','sairntrade','sairnhr','sairnacc','sairnbiz',
  'test','doc_analysis','followup_gen','memory_builder'
]);

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', req.headers.origin || '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { max_tokens, system, messages, app_id, is_demo, license_key } = req.body || {};
  if (!messages?.length) return res.status(400).json({ error: 'Messages required' });

  const appOk = !app_id || KNOWN_APPS.has(app_id) || app_id?.startsWith('sairn') || app_id === 'fabricor';
  if (!appOk) return res.status(400).json({ error: 'Invalid app_id' });

  const isB2B = B2B_APPS.has(app_id);
  const license = validateLicense(license_key, app_id);

  if (!license.valid) {
    // Demo: rate-limited
    const limit = isB2B ? DEMO_LIMITS.b2b : DEMO_LIMITS.consumer;
    const rlKey = getRLKey(req, app_id || 'unknown');
    const count = calls.get(rlKey) || 0;
    if (count >= limit) {
      return res.status(429).json({
        error: 'demo_limit',
        message: `Free demo limit reached (${limit} calls/day). Enter your SAIRN license key in Formula Editor to unlock unlimited access. Email michael@sairn.com to get your key.`,
        upgrade: true, limit, used: count
      });
    }
    calls.set(rlKey, count + 1);
  }

  const model = isB2B ? SONNET : HAIKU;
  const maxTok = license.valid
    ? Math.min(max_tokens || 2000, 8000)
    : Math.min(max_tokens || 1000, isB2B ? 2000 : 1000);

  const params = { model, max_tokens: maxTok, messages: messages.slice(-20) };
  if (system) params.system = system.slice(0, 8000);

  try {
    const r = await anthropic.messages.create(params);
    const rlKey = getRLKey(req, app_id || 'unknown');
    const remaining = license.valid ? 'unlimited' :
      Math.max(0, (isB2B ? DEMO_LIMITS.b2b : DEMO_LIMITS.consumer) - (calls.get(rlKey) || 0));
    return res.status(200).json({
      ...r,
      _model: model,
      _licensed: license.valid,
      _shop: license.shop || null,
      _remaining: remaining
    });
  } catch (err) {
    console.error('[Proxy Error]', err.message);
    return res.status(err.status || 500).json({ error: { message: err.message } });
  }
}
