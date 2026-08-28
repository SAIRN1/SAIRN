// /api/capture — email waitlist capture
import { createClient } from '@supabase/supabase-js';
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).end();
  const { email, app_id, source } = req.body || {};
  if (!email?.includes('@') || !app_id) return res.status(400).json({ error: 'Invalid' });
  await supabase.from('email_waitlist').upsert({ email: email.toLowerCase().trim(), app_id, source: source || 'unknown' }, { onConflict: 'email,app_id' }).catch(() => {});
  return res.status(200).json({ success: true });
}
