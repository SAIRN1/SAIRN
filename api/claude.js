import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const MODEL = 'claude-haiku-4-5-20251001';
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
  'contractor','biz','pay','hr','fabricor','sairnbuild',
  'sairnscape','sairnflow','sairnvet','sairnfix','sairnfuneral','enterprise',
]);

export default async function handler(req, res) {
  const origin = req.headers.origin;
  if (origin) res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { max_tokens, system, messages, app_id } = req.body || {};

  if (!messages?.length) return res.status(400).json({ error: 'Messages required' });
  if (!app_id) return res.status(400).json({ error: 'app_id required' });
  if (!VALID_APP_IDS.has(app_id)) return res.status(400).json({ error: 'Invalid app_id' });

  const key = getDemoKey(req);
  const count = demoCallsToday.get(key) || 0;

  if (count >= DEMO_LIMIT) {
    return res.status(429).json({
      error: 'demo_limit',
      message: 'You have used your free questions today. Sign up at sairn.vercel.app for unlimited access.',
      upgrade: true
    });
  }

  demoCallsToday.set(key, count + 1);

  const params = {
    model: MODEL,
    max_tokens: Math.min(max_tokens || 1000, 500),
    messages: messages.slice(-6)
  };

  if (system) params.system = system.slice(0, 3000);

  try {
    const response = await anthropic.messages.create(params);
    return res.status(200).json(response);
  } catch (err) {
    return res.status(err.status || 500).json({ error: { message: err.message } });
  }
}
Paste that → Commit changes → wait 60 seconds → test. 🍯
