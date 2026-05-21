// ═══════════════════════════════════════════════════════════════════
//  SAIRN Technologies — /api/claude  (v3 — Production)
//  Auth: Supabase JWT on every authenticated request
//  Storage: conversation history persisted per user per app
//  Privacy: no message content logged anywhere
//  Rate limiting: demo calls capped by IP, paid users unlimited
//  Michael L. Dibert · HONEY COMB Platform · 2026
// ═══════════════════════════════════════════════════════════════════

import Anthropic from '@anthropic-ai/sdk';
import { createClient } from '@supabase/supabase-js';
import crypto from 'crypto';

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const supabase  = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);

// Haiku pricing per million tokens
const PRICING = { in: 0.80, out: 4.00 };
const DEFAULT_MODEL    = 'claude-haiku-4-5-20251001';
const DEMO_LIMIT_IP    = 10;   // free demo calls per IP per day
const DEMO_LIMIT_TOTAL = 300;  // global demo cap per day

export default async function handler(req, res) {
  // ── CORS ────────────────────────────────────────────────────────
  res.setHeader('Access-Control-Allow-Origin', process.env.SITE_URL || '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST')    return res.status(405).json({ error: 'Method not allowed' });

  const { model, max_tokens, system, messages, app_id, is_demo, conversation_id } = req.body;

  if (!messages?.length) return res.status(400).json({ error: 'Messages required' });
  if (!app_id)           return res.status(400).json({ error: 'app_id required' });

  const useModel     = DEFAULT_MODEL;  // always haiku — cost control
  const useMaxTokens = Math.min(max_tokens || 1000, 2000);

  // ── DEMO PATH ────────────────────────────────────────────────────
  if (is_demo) {
    const raw    = req.headers['x-forwarded-for']?.split(',')[0] || req.socket?.remoteAddress || 'unknown';
    const ipHash = crypto.createHash('sha256').update(raw).digest('hex').slice(0, 20);
    const today  = new Date().toISOString().slice(0, 10);

    const [{ count: ipCount }, { count: globalCount }] = await Promise.all([
      supabase.from('demo_calls').select('id', { count: 'exact', head: true })
        .eq('ip_hash', ipHash).eq('app_id', app_id).gte('created_at', `${today}T00:00:00Z`),
      supabase.from('demo_calls').select('id', { count: 'exact', head: true })
        .gte('created_at', `${today}T00:00:00Z`)
    ]);

    if ((ipCount    || 0) >= DEMO_LIMIT_IP)    return res.status(429).json({ error: 'demo_ip_limit',    upgrade: true });
    if ((globalCount|| 0) >= DEMO_LIMIT_TOTAL) return res.status(429).json({ error: 'demo_total_limit', upgrade: true });

    supabase.from('demo_calls').insert({ ip_hash: ipHash, app_id }).then(() => {}).catch(() => {});
    return runClaude(res, null, null, app_id, useModel, Math.min(useMaxTokens, 400), system, messages, false);
  }

  // ── AUTHENTICATED PATH ───────────────────────────────────────────
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) return res.status(401).json({ error: 'auth_required' });

  const { data: { user }, error: authErr } = await supabase.auth.getUser(token);
  if (authErr || !user) return res.status(401).json({ error: 'session_expired' });

  // Check subscription
  const { data: sub } = await supabase.from('subscriptions')
    .select('status, current_period_end')
    .eq('user_id', user.id).eq('app_id', app_id)
    .in('status', ['active', 'trialing']).maybeSingle();

  if (!sub) return res.status(402).json({ error: 'subscription_required', app_id });
  if (sub.current_period_end && new Date(sub.current_period_end) < new Date())
    return res.status(402).json({ error: 'subscription_expired' });

  return runClaude(res, user.id, conversation_id || null, app_id, useModel, useMaxTokens, system, messages, true);
}

async function runClaude(res, userId, conversationId, appId, model, maxTokens, system, messages, track) {
  try {
    const params = { model, max_tokens: maxTokens, messages: messages.slice(-24) };
    if (system) params.system = system;

    const response = await anthropic.messages.create(params);
    const aiText   = response.content?.[0]?.text || '';

    // ── PERSIST CONVERSATION (authenticated users only) ───────────
    if (track && userId && aiText) {
      const convId = conversationId || crypto.randomUUID();
      const userMsg = messages[messages.length - 1];

      // Upsert conversation record
      await supabase.from('conversations').upsert({
        id: convId, user_id: userId, app_id: appId,
        updated_at: new Date().toISOString(),
        title: userMsg?.content?.slice(0, 80) || 'Conversation'
      }, { onConflict: 'id' });

      // Insert both messages — privacy: content stored only in user's own row
      await supabase.from('messages').insert([
        { conversation_id: convId, user_id: userId, role: 'user',      content: userMsg?.content || '', tokens_used: response.usage?.input_tokens  || 0 },
        { conversation_id: convId, user_id: userId, role: 'assistant', content: aiText,                 tokens_used: response.usage?.output_tokens || 0 }
      ]);

      // Track usage cost (no content — just token counts)
      const tokIn  = response.usage?.input_tokens  || 0;
      const tokOut = response.usage?.output_tokens || 0;
      supabase.from('usage_logs').insert({
        user_id: userId, app_id: appId,
        tokens_in: tokIn, tokens_out: tokOut,
        cost_usd: (tokIn / 1e6 * PRICING.in) + (tokOut / 1e6 * PRICING.out)
      }).then(() => {}).catch(() => {});

      // Return conversation_id so client can continue the thread
      return res.status(200).json({ ...response, conversation_id: convId });
    }

    return res.status(200).json(response);

  } catch (err) {
    console.error('[SAIRN Claude]', err.status, err.message);
    if (err.status === 529) return res.status(529).json({ error: { message: 'Claude overloaded. Try again in a moment.' } });
    return res.status(500).json({ error: { message: 'Claude API error. Please try again.' } });
  }
}
