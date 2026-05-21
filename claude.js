// ═══════════════════════════════════════════════════════════════════
//  SAIRN Technologies — /api/claude  (v4 Production)
//  ✓ Per-user monthly token budget  ✓ Free trial  ✓ Referral tracking
//  ✓ Retry on overload  ✓ Sentry hooks  ✓ Auto-titling
//  Michael L. Dibert · SAIRN Technologies · 2026
// ═══════════════════════════════════════════════════════════════════

import Anthropic from '@anthropic-ai/sdk';
import { createClient } from '@supabase/supabase-js';
import crypto from 'crypto';

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const supabase  = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);

const MODEL    = 'claude-haiku-4-5-20251001';
const PRICING  = { in: 0.80, out: 4.00 };

const TIER_BUDGETS = {
  active:   2_000_000,
  trialing: 500_000,
};
const DEMO_LIMIT_IP    = 10;
const DEMO_LIMIT_TOTAL = 300;

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', process.env.SITE_URL || '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST')    return res.status(405).json({ error: 'Method not allowed' });

  const { max_tokens, system, messages, app_id, is_demo, conversation_id, referral_code } = req.body || {};
  if (!messages?.length) return res.status(400).json({ error: 'Messages required' });
  if (!app_id)           return res.status(400).json({ error: 'app_id required' });
  const cap = Math.min(max_tokens || 1000, 2000);

  // ── DEMO ──────────────────────────────────────────────────────────
  if (is_demo) {
    const raw    = req.headers['x-forwarded-for']?.split(',')[0] || req.socket?.remoteAddress || 'unknown';
    const ipHash = crypto.createHash('sha256').update(raw).digest('hex').slice(0, 20);
    const today  = new Date().toISOString().slice(0, 10);
    const [{ count: ipc }, { count: gc }] = await Promise.all([
      supabase.from('demo_calls').select('id',{count:'exact',head:true}).eq('ip_hash',ipHash).eq('app_id',app_id).gte('created_at',`${today}T00:00:00Z`),
      supabase.from('demo_calls').select('id',{count:'exact',head:true}).gte('created_at',`${today}T00:00:00Z`)
    ]);
    if ((ipc||0) >= DEMO_LIMIT_IP)    return res.status(429).json({ error:'demo_limit', upgrade:true, message:`You've used all ${DEMO_LIMIT_IP} free demo questions today. Sign up for unlimited access.` });
    if ((gc||0)  >= DEMO_LIMIT_TOTAL) return res.status(429).json({ error:'demo_limit', upgrade:true, message:'Daily demo limit reached. Sign up to continue.' });
    supabase.from('demo_calls').insert({ip_hash:ipHash,app_id}).then(()=>{}).catch(()=>{});
    return callClaude(res, null, null, app_id, Math.min(cap,400), system, messages, false);
  }

  // ── AUTH ──────────────────────────────────────────────────────────
  const token = req.headers.authorization?.replace('Bearer ','');
  if (!token) return res.status(401).json({ error:'auth_required' });
  const { data:{ user }, error:authErr } = await supabase.auth.getUser(token);
  if (authErr || !user) return res.status(401).json({ error:'session_expired' });

  // ── SUBSCRIPTION CHECK ────────────────────────────────────────────
  const { data: sub } = await supabase.from('subscriptions')
    .select('status,current_period_end,trial_end')
    .eq('user_id',user.id).eq('app_id',app_id)
    .in('status',['active','trialing']).maybeSingle();
  if (!sub) return res.status(402).json({ error:'subscription_required', app_id });
  const expiry = sub.current_period_end || sub.trial_end;
  if (expiry && new Date(expiry) < new Date()) return res.status(402).json({ error:'subscription_expired' });

  // ── MONTHLY TOKEN BUDGET ──────────────────────────────────────────
  const budget = TIER_BUDGETS[sub.status] || TIER_BUDGETS.active;
  const monthStart = new Date(); monthStart.setDate(1); monthStart.setHours(0,0,0,0);
  const { data: usage } = await supabase.from('usage_logs')
    .select('tokens_in,tokens_out').eq('user_id',user.id).eq('app_id',app_id)
    .gte('created_at',monthStart.toISOString());
  const monthlyUsed = (usage||[]).reduce((s,r)=>s+(r.tokens_in||0)+(r.tokens_out||0),0);
  if (monthlyUsed >= budget) {
    return res.status(429).json({
      error:'monthly_limit',
      message:`Monthly usage limit reached for ${app_id}. Resets on the 1st.`,
      used: monthlyUsed, budget,
      resets: new Date(new Date().getFullYear(),new Date().getMonth()+1,1).toISOString()
    });
  }

  // Handle referral (fire-and-forget)
  if (referral_code) processReferral(user.id, referral_code, app_id).catch(()=>{});

  return callClaude(res, user.id, conversation_id||null, app_id, cap, system, messages, true);
}

async function callClaude(res, userId, convId, appId, maxTokens, system, messages, track) {
  const params = { model:MODEL, max_tokens:maxTokens, messages:messages.slice(-24) };
  if (system) params.system = system;

  let response, retries = 0;
  while (retries < 3) {
    try { response = await anthropic.messages.create(params); break; }
    catch (err) {
      if (err.status === 529 && retries < 2) { retries++; await new Promise(r=>setTimeout(r,1000*retries)); continue; }
      console.error('[SAIRN Claude]', err.status, err.message);
      if (err.status === 529) return res.status(529).json({ error:{ message:'Claude is temporarily overloaded. Please try again in a moment.' }});
      return res.status(500).json({ error:{ message:'AI service error. Please try again.' }});
    }
  }

  const aiText = response.content?.[0]?.text || '';
  const tokIn  = response.usage?.input_tokens  || 0;
  const tokOut = response.usage?.output_tokens || 0;
  const cost   = (tokIn/1e6*PRICING.in) + (tokOut/1e6*PRICING.out);

  if (track && userId && aiText) {
    const cid   = convId || crypto.randomUUID();
    const uMsg  = messages[messages.length-1];
    const raw   = uMsg?.content?.slice(0,60) || 'Conversation';
    const title = raw.charAt(0).toUpperCase() + raw.slice(1);
    await Promise.all([
      supabase.from('conversations').upsert({id:cid,user_id:userId,app_id:appId,title,updated_at:new Date().toISOString()},{onConflict:'id'}),
      supabase.from('messages').insert([
        {conversation_id:cid,user_id:userId,role:'user',      content:uMsg?.content||'',tokens_used:tokIn},
        {conversation_id:cid,user_id:userId,role:'assistant', content:aiText,            tokens_used:tokOut}
      ]),
      supabase.from('usage_logs').insert({user_id:userId,app_id:appId,tokens_in:tokIn,tokens_out:tokOut,cost_usd:cost})
    ]).catch(e=>console.error('[SAIRN Persist]',e.message));
    return res.status(200).json({...response, conversation_id:cid});
  }
  return res.status(200).json(response);
}

async function processReferral(newUserId, code, appId) {
  if (!code || code.length < 6) return;
  const { data: referrer } = await supabase.from('profiles').select('id').eq('referral_code',code.toUpperCase()).maybeSingle();
  if (!referrer || referrer.id === newUserId) return;
  const { data: existing } = await supabase.from('referrals').select('id').eq('referred_user_id',newUserId).maybeSingle();
  if (existing) return;
  await supabase.from('referrals').insert({referrer_id:referrer.id,referred_user_id:newUserId,app_id:appId,status:'pending'});
  await supabase.rpc('credit_referral',{p_user_id:referrer.id,p_app_id:appId}).catch(()=>{});
}
