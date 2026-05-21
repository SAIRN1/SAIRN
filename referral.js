// /api/referral — get user's referral code + stats
import { createClient } from '@supabase/supabase-js';
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) return res.status(401).json({ error: 'auth_required' });
  const { data: { user }, error } = await supabase.auth.getUser(token);
  if (error || !user) return res.status(401).json({ error: 'session_expired' });
  const { data: profile } = await supabase.from('profiles').select('referral_code, referral_credits').eq('id', user.id).maybeSingle();
  const { count: pending } = await supabase.from('referrals').select('id', { count: 'exact', head: true }).eq('referrer_id', user.id).eq('status', 'pending');
  const { count: credited } = await supabase.from('referrals').select('id', { count: 'exact', head: true }).eq('referrer_id', user.id).eq('status', 'credited');
  return res.status(200).json({
    referral_code: profile?.referral_code,
    referral_url: `https://sairn.vercel.app?ref=${profile?.referral_code}`,
    credits_earned: profile?.referral_credits || 0,
    pending_referrals: pending || 0,
    credited_referrals: credited || 0,
  });
}
