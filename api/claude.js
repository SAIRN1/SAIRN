import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const MODEL = 'claude-haiku-4-5-20251001';
const calls = new Map();

function getKey(req) {
  const ip = req.headers['x-forwarded-for']?.split(',')[0]?.trim() || 'unknown';
  return ip + '_' + new Date().toISOString().slice(0, 10);
}

const APPS = new Set([
  'sairntype','lingual','health','money','legal','study','roam','senior',
  'mind','kitchen','family','career','home','shield','daily',
  'contractor','biz','pay','hr','fabricor','sairnbuild',
  'sairnscape','sairnflow','sairnvet','sairnfix','sairnfuneral','enterprise'
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
  if (!app_id || !APPS.has(app_id)) return res.status(400).json({ error: 'Invalid app_id' });

  const key = getKey(req);
  const count = calls.get(key) || 0;
  if (count >= 10) {
    return res.status(429).json({
      error: 'demo_limit',
      message: 'You have used your free questions today. Sign up at sairn.vercel.app for unlimited access.',
      upgrade: true
    });
  }
  calls.set(key, count + 1);

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
