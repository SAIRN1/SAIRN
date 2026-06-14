// ================================================================
// SAIRN Claude Proxy -- api/claude.js (v5 -- License Key Paywall)
// Demo: 50 calls/day per IP (B2B), 15/day (consumer)
// Licensed: unlimited calls with valid SAIRN-XXXX-XXXX-XXXX key
// Michael L. Dibert -- SAIRN Technologies -- 2026
// ================================================================

import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const HAIKU  = 'claude-haiku-4-5-20251001';
const SONNET = 'claude-sonnet-4-6';

// B2B apps get Sonnet (full Claude power)
const B2B_APPS = new Set([
  'stonedesk','fabricor','sairnbuild','sairnscape','sairnlaw',
  'sairncode','sairndesign','sairnvet','sairnvetglobal','sairncare',
  'sairnfuneral','sairnmechanical','sairntrade','sairnhr','sairnacc'
]);

// ── LICENSE KEY STORE ────────────────────────────────────────
// Keys are stored in SAIRN_LICENSE_KEYS env var as JSON:
// { "SAIRN-SD01-2025-ALPHA": { "app":"stonedesk", "shop":"Granite Works", "active":true } }
// Add new keys via Vercel dashboard -> Environment Variables -> SAIRN_LICENSE_KEYS
function getLicenseStore() {
  try {
    return JSON.parse(process.env.SAIRN_LICENSE_KEYS || '{}');
  } catch(e) {
    return {};
  }
}

function validateLicense(key, appId) {
  if (!key) return { valid: false };
  const store = getLicenseStore();
  const entry = store[key.toUpperCase()];
  if (!entry) return { valid: false, reason: 'key_not_found' };
  if (!entry.active) return { valid: false, reason: 'key_inactive' };
  // Key is valid for any SAIRN app (or check specific app if entry.app is set)
  if (entry.app && entry.app !== appId && entry.app !== 'all') {
    return { valid: false, reason: 'wrong_app' };
  }
  return { valid: true, shop: entry.shop, plan: entry.plan || 'standard' };
}

// ── RATE LIMITING (demo users only) ─────────────────────────
const calls = new Map();

function getKey(req, appId) {
  const ip = req.headers['x-forwarded-for']?.split(',')[0]?.trim() || 'unknown';
  const today = new Date().toISOString().slice(0, 10);
  return `${ip}_${appId}_${today}`;
}

const DEMO_LIMITS = { b2b: 50, consumer: 15 };

// ── KNOWN APPS ───────────────────────────────────────────────
const KNOWN_APPS = new Set([
  'sairntype','lingual','health','money','legal','study','roam','senior',
  'stonedesk','fabricor','sairnbuild','sairnscape','sairnlaw','sairncode',
  'sairndesign','sairnvet','sairnvetglobal','sairncare','sairnfuneral',
  'sairnmechanical','sairntrade','sairnhr','sairnacc','sairnbiz',
  'test','doc_analysis','followup_gen','memory_builder'
]);

export default async function handler(req, res) {
  const origin = req.headers.origin || '*';
  res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const {
    max_tokens, system, messages, app_id, is_demo,
    model: requestedModel, license_key
  } = req.body || {};

  if (!messages?.length) return res.status(400).json({ error: 'Messages required' });

  const appIdValid = !app_id || KNOWN_APPS.has(app_id) || app_id?.startsWith('sairn') || app_id === 'fabricor';
  if (!appIdValid) return res.status(400).json({ error: 'Invalid app_id' });

  const isB2B = B2B_APPS.has(app_id);

  // ── LICENSE CHECK ────────────────────────────────────────
  const licenseResult = validateLicense(license_key, app_id);
  const isLicensed = licenseResult.valid;

  if (!isLicensed) {
    // Demo mode: apply rate limit
    const limit = isB2B ? DEMO_LIMITS.b2b : DEMO_LIMITS.consumer;
    const key   = getKey(req, app_id || 'unknown');
    const count = calls.get(key) || 0;

    if (count >= limit) {
      return res.status(429).json({
        error: 'demo_limit',
        message: isB2B
          ? `You have used ${limit} free AI calls today. Enter your StoneDesk license key to unlock unlimited access. Email michael@sairn.com to get your key.`
          : 'Daily free limit reached. Sign up at sairn.vercel.app for unlimited access.',
        upgrade: true,
        limit,
        used: count,
        get_key: 'michael@sairn.com'
      });
    }
    calls.set(key, count + 1);
  }

  // ── MODEL SELECTION ──────────────────────────────────────
  const model = isB2B ? SONNET : HAIKU;

  // Licensed users get higher token limits
  const maxTok = isLicensed
    ? Math.min(max_tokens || 2000, 8000)
    : Math.min(max_tokens || 1000, isB2B ? 2000 : 1000);

  const params = {
    model,
    max_tokens: maxTok,
    messages: messages.slice(-20)
  };
  if (system) params.system = system.slice(0, 8000);

  try {
    const response = await anthropic.messages.create(params);
    const remaining = isLicensed ? 'unlimited' : (
      (isB2B ? DEMO_LIMITS.b2b : DEMO_LIMITS.consumer) - (calls.get(getKey(req, app_id || 'unknown')) || 0)
    );
    return res.status(200).json({
      ...response,
      _model: model,
      _licensed: isLicensed,
      _shop: licenseResult.shop || null,
      _remaining: remaining
    });
  } catch (err) {
    console.error('[Claude Proxy Error]', err.message);
    return res.status(err.status || 500).json({ error: { message: err.message } });
  }
}
