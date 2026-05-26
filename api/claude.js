// ═══════════════════════════════════════════════════════════════════
//  SAIRN Technologies — /api/claude  (v8 — Enterprise Token Engine)
//
//  TOKEN TIERS — no company ever crashes:
//
//  CONSUMER (SAIRN NEXUS):
//    trialing     →  100K tokens/mo
//    individual   →  500K tokens/mo
//    family       →  1.5M tokens/mo
//    legal        →  750K tokens/mo
//
//  B2B STANDARD:
//    b2b_starter  →  5M tokens/mo   (~$199/mo plans)
//    b2b_pro      →  15M tokens/mo  (~$299/mo plans)
//    b2b_business →  40M tokens/mo  (~$499/mo plans)
//
//  ENTERPRISE (Goodyear-scale):
//    enterprise_s →  100M tokens/mo  (~$2K/mo)
//    enterprise_m →  500M tokens/mo  (~$5K/mo)
//    enterprise_l →  UNLIMITED       (~$10K+/mo custom)
//
//  AUTO-SCALING:
//    - At 80% of budget → warning email + Slack alert
//    - At 95% of budget → soft cap + upgrade prompt
//    - At 100% → graceful degradation (shorter responses)
//      NOT a hard crash. Never a hard crash.
//    - Token Pack top-ups available at any tier
//    - Enterprise gets auto-scale by default (never cuts off)
//
//  9-LAYER SECURITY (all from v7):
//  1. CORS lockdown        6. Auth (JWT)
//  2. Method + headers     7. Subscription guard
//  3. Payload firewall     8. Anomaly detection
//  4. App ID allowlist     9. Security headers
//  5. Prompt injection
//
//  Michael L. Dibert · SAIRN Technologies · 2026
//  Patent Pending · All Rights Reserved
// ═══════════════════════════════════════════════════════════════════

import Anthropic from '@anthropic-ai/sdk';
import { createClient } from '@supabase/supabase-js';
import crypto from 'crypto';

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const supabase  = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
const MODEL     = 'claude-haiku-4-5-20251001';
const PRICING   = { in: 1.00, out: 5.00 };

// ── TOKEN BUDGETS ─────────────────────────────────────────────────
const TOKEN_BUDGETS = {
  // Consumer
  trialing:      100_000,
  individual:    500_000,
  family:      1_500_000,
  legal:         750_000,
  active:        500_000,

  // B2B Standard
  b2b_starter:   5_000_000,
  b2b_pro:      15_000_000,
  b2b_business: 40_000_000,

  // Enterprise
  enterprise_s: 100_000_000,
  enterprise_m: 500_000_000,
  enterprise_l: -1,           // -1 = unlimited (auto-scale billing)
  enterprise_custom: -1,
};

// Plans that NEVER get hard-cut off — auto-scale instead
const AUTO_SCALE_PLANS = new Set([
  'enterprise_l', 'enterprise_custom', 'enterprise_m'
]);

// Warning thresholds
const WARN_AT  = 0.80; // 80% → send alert
const SOFT_AT  = 0.95; // 95% → shorter responses
const HARD_AT  = 1.00; // 100% → graceful degradation (not crash)

// ── CORS ─────────────────────────────────────────────────────────
const ALLOWED_ORIGINS = [
  'https://sairn.vercel.app',
  'https://fabricor.vercel.app',
  'https://sairnscape.vercel.app',
  'https://sairnflow.vercel.app',
  'https://sairnvet.vercel.app',
  'https://sairnfix.vercel.app',
  'https://sairnfuneral.vercel.app',
  'https://www.sairntechnologies.com',
  process.env.SITE_URL,
  process.env.ENTERPRISE_DOMAIN_1, // e.g. https://ai.goodyear.com
  process.env.ENTERPRISE_DOMAIN_2,
  process.env.ENTERPRISE_DOMAIN_3,
  ...(process.env.NODE_ENV === 'development'
    ? ['http://localhost:3000','http://localhost:3001']
    : []),
].filter(Boolean);

function setCORSHeaders(req, res) {
  const origin = req.headers.origin;
  if (origin && ALLOWED_ORIGINS.includes(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Vary', 'Origin');
  }
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Access-Control-Max-Age', '86400');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
}

// ── APP ID ALLOWLIST ──────────────────────────────────────────────
const VALID_APP_IDS = new Set([
  // Consumer NEXUS
  'sairntype','lingual','health','money','legal','study','roam','senior',
  'mind','kitchen','family','career','home','shield','daily',
  'contractor','biz','pay','hr',
  // B2B
  'fabricor','sairnbuild','sairnscape','sairnflow',
  'sairnvet','sairnfix','sairnfuneral',
  // Enterprise custom
  'enterprise',
]);

// ── PAYLOAD VALIDATION ────────────────────────────────────────────
const MAX_PAYLOAD_BYTES  = 65_536; // 64KB for enterprise (larger docs)
const MAX_MESSAGES       = 40;
const MAX_MESSAGE_CHARS  = 12_000; // larger for B2B (paste documents)
const MAX_SYSTEM_CHARS   = 16_000;

function validatePayload(body, rawSize) {
  if (rawSize > MAX_PAYLOAD_BYTES) return { error: 'Payload too large', status: 413 };
  const { messages, app_id, max_tokens } = body || {};
  if (!Array.isArray(messages) || !messages.length) return { error: 'Messages required', status: 400 };
  if (!app_id) return { error: 'app_id required', status: 400 };
  if (!VALID_APP_IDS.has(app_id)) return { error: 'Invalid app_id', status: 400 };
  if (messages.length > MAX_MESSAGES) return { error: `Max ${MAX_MESSAGES} messages`, status: 400 };
  for (const msg of messages) {
    if (!msg || !['user','assistant'].includes(msg.role)) return { error: 'Invalid message', status: 400 };
    if (typeof msg.content !== 'string') return { error: 'Content must be string', status: 400 };
    if (msg.content.length > MAX_MESSAGE_CHARS) return { error: 'Message too long', status: 400 };
  }
  if (max_tokens && (max_tokens < 1 || max_tokens > 4000)) return { error: 'Invalid max_tokens', status: 400 };
  return null;
}

// ── PROMPT INJECTION DETECTION ────────────────────────────────────
const INJECTION_PATTERNS = [
  /ignore (all |previous |prior |above |your )?instructions/i,
  /you are now (a |an )?(different|new|evil|unrestricted|DAN)/i,
  /pretend (you|you're) (a |an )?(different|evil|unrestricted)/i,
  /\[system\]/i, /<<SYS>>/i, /\[INST\]/i, /<\|im_start\|>/i,
  /act as (if you have no|without) (restrictions|guidelines|rules)/i,
  /disregard (your|all|any) (training|instructions|guidelines)/i,
  /developer mode/i, /jailbreak/i, /do anything now/i,
];

function detectInjection(messages) {
  const last = [...messages].reverse().find(m => m.role === 'user');
  if (!last) return false;
  return INJECTION_PATTERNS.some(p => p.test(last.content));
}

// ── DEMO RATE LIMITING ────────────────────────────────────────────
const DEMO_LIMIT_IP    = 10;
const DEMO_LIMIT_BURST = 3;
const DEMO_LIMIT_TOTAL = 1000;

async function checkDemoLimits(req, app_id) {
  const raw    = req.headers['x-forwarded-for']?.split(',')[0]?.trim() || 'unknown';
  const ipHash = crypto.createHash('sha256').update(raw + (process.env.IP_SALT || 'sairn2026')).digest('hex').slice(0,24);
  const today  = new Date().toISOString().slice(0,10);
  const minute = new Date().toISOString().slice(0,16);

  const [{ count: ipDay }, { count: ipBurst }, { count: globalDay }] = await Promise.all([
    supabase.from('demo_calls').select('id',{count:'exact',head:true}).eq('ip_hash',ipHash).gte('created_at',`${today}T00:00:00Z`),
    supabase.from('demo_calls').select('id',{count:'exact',head:true}).eq('ip_hash',ipHash).gte('created_at',`${minute}:00Z`),
    supabase.from('demo_calls').select('id',{count:'exact',head:true}).gte('created_at',`${today}T00:00:00Z`),
  ]);

  if ((ipBurst||0)  >= DEMO_LIMIT_BURST) return { blocked:true, status:429, message:'Too many requests. Please wait a moment.' };
  if ((ipDay||0)    >= DEMO_LIMIT_IP)    return { blocked:true, status:429, message:`You have used your ${DEMO_LIMIT_IP} free questions today. Sign up for unlimited access.`, upgrade:true };
  if ((globalDay||0)>= DEMO_LIMIT_TOTAL) return { blocked:true, status:429, message:'Daily demo limit reached. Sign up for unlimited access.', upgrade:true };

  supabase.from('demo_calls').insert({ ip_hash:ipHash, app_id, created_at:new Date().toISOString() }).catch(()=>{});
  return { blocked: false };
}

// ── ANOMALY DETECTION ─────────────────────────────────────────────
async function checkAnomaly(userId, appId, plan) {
  try {
    const threshold = plan?.startsWith('enterprise') ? 2000 : 200;
    const oneHourAgo = new Date(Date.now() - 3600000).toISOString();
    const { count } = await supabase.from('usage_logs')
      .select('id',{count:'exact',head:true})
      .eq('user_id', userId).gte('created_at', oneHourAgo);

    if ((count||0) > threshold) {
      supabase.from('security_events').insert({
        user_id:userId, app_id:appId, event:'usage_spike',
        detail:`${count} calls in last hour (threshold: ${threshold})`,
        severity: count > threshold * 2 ? 'critical' : 'warning',
        created_at: new Date().toISOString()
      }).catch(()=>{});
    }
  } catch {}
}

// ── USAGE ALERT SYSTEM ────────────────────────────────────────────
// Fires when a company hits 80% or 95% of their token budget
// So they NEVER crash — they get warned and can upgrade first
async function checkAndFireUsageAlerts(userId, orgId, plan, monthlyUsed, budget) {
  if (budget <= 0) return; // unlimited plans skip this

  const pct = monthlyUsed / budget;

  if (pct >= WARN_AT && pct < SOFT_AT) {
    // Check if we've already sent the 80% alert this month
    const monthStart = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString();
    const { count } = await supabase.from('usage_alerts')
      .select('id',{count:'exact',head:true})
      .eq('user_id', userId).eq('alert_type', 'warn_80')
      .gte('created_at', monthStart);

    if ((count||0) === 0) {
      // Log the alert
      await supabase.from('usage_alerts').insert({
        user_id: userId, org_id: orgId, plan, alert_type: 'warn_80',
        tokens_used: monthlyUsed, budget,
        message: `Your account has used 80% of your monthly token budget. Consider upgrading to avoid interruption.`,
        created_at: new Date().toISOString()
      }).catch(()=>{});

      // In production: fire email + Slack webhook here
      // await sendAlertEmail(userId, '80% Token Warning', ...)
      // await sendSlackAlert(orgId, '⚠️ 80% tokens used')
    }
  }

  if (pct >= SOFT_AT && pct < HARD_AT) {
    const monthStart = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString();
    const { count } = await supabase.from('usage_alerts')
      .select('id',{count:'exact',head:true})
      .eq('user_id', userId).eq('alert_type', 'warn_95')
      .gte('created_at', monthStart);

    if ((count||0) === 0) {
      await supabase.from('usage_alerts').insert({
        user_id: userId, org_id: orgId, plan, alert_type: 'warn_95',
        tokens_used: monthlyUsed, budget,
        message: `URGENT: Your account has used 95% of your monthly token budget. Add tokens now to avoid reduced service.`,
        created_at: new Date().toISOString()
      }).catch(()=>{});
    }
  }
}

// ── MEMORY BUILDER ────────────────────────────────────────────────
async function buildMemoryInjection(userId) {
  try {
    const { data: mem } = await supabase
      .from('user_memory').select('facts,summary').eq('user_id',userId).single();
    if (!mem?.facts?.length) return '';
    const facts = mem.facts.slice(-20).map(f => `- ${f.fact}`).join('\n');
    return `\n\nWHAT YOU ALREADY KNOW ABOUT THIS USER:\n${facts}${mem.summary ? `\nSummary: ${mem.summary}` : ''}\n\nUse naturally — don't announce you remember things.`;
  } catch { return ''; }
}

// ── BACKGROUND MEMORY EXTRACTION ─────────────────────────────────
async function extractMemoryBackground(userId, appId, messages, aiText) {
  try {
    if (messages.length < 2) return;
    const transcript = messages.slice(-8).map(m => `${m.role==='user'?'User':'SAIRN'}: ${m.content}`).join('\n\n') + `\nSAIRN: ${aiText}`;
    if (transcript.length < 100) return;

    const extraction = await anthropic.messages.create({
      model: MODEL, max_tokens: 400,
      messages:[{role:'user',content:`Extract up to 8 concrete facts about the user from this conversation. Return ONLY JSON:\n{"facts":[{"category":"PERSONAL","fact":"lives in Columbus Ohio","confidence":"high"}],"summary":"one sentence"}\nIf nothing useful: {"facts":[],"summary":""}\n\nCONVERSATION (${appId}):\n${transcript.slice(0,2500)}`}]
    });

    const raw = extraction.content?.[0]?.text || '{}';
    let parsed;
    try { parsed = JSON.parse(raw.replace(/```json|```/g,'').trim()); } catch { return; }
    if (!parsed.facts?.length) return;

    const { data: existing } = await supabase.from('user_memory').select('facts,summary,total_conversations,apps_used').eq('user_id',userId).single();
    const merged = [...(existing?.facts||[])];
    for (const nf of parsed.facts.map(f=>({...f,app_id:appId,extracted_at:new Date().toISOString()}))) {
      const idx = merged.findIndex(ef => ef.category===nf.category && ef.fact.toLowerCase().split(' ').slice(0,3).join(' ')===nf.fact.toLowerCase().split(' ').slice(0,3).join(' '));
      if(idx>=0) merged[idx]=nf; else merged.push(nf);
    }

    await supabase.from('user_memory').upsert({
      user_id:userId, facts:merged.slice(-50),
      summary:parsed.summary||existing?.summary||'',
      last_updated:new Date().toISOString(),
      total_conversations:(existing?.total_conversations||0)+1,
      apps_used:[...new Set([...(existing?.apps_used||[]),appId])]
    },{onConflict:'user_id'});
  } catch(err) { console.error('[SAIRN Memory]',err.message); }
}

// ═══════════════════════════════════════════════════════════════════
// MAIN HANDLER
// ═══════════════════════════════════════════════════════════════════
export default async function handler(req, res) {

  // LAYER 1: CORS
  setCORSHeaders(req, res);
  if (req.method === 'OPTIONS') return res.status(200).end();

  // LAYER 2: METHOD + CONTENT-TYPE
  if (req.method !== 'POST') return res.status(405).json({ error:'Method not allowed' });
  if (!(req.headers['content-type']||'').includes('application/json'))
    return res.status(415).json({ error:'Content-Type must be application/json' });

  // LAYER 3: PAYLOAD FIREWALL
  const rawSize = parseInt(req.headers['content-length']||'0');
  const valErr  = validatePayload(req.body, rawSize);
  if (valErr) return res.status(valErr.status).json({ error:valErr.error });

  const { max_tokens, system, messages, app_id, is_demo, conversation_id, extract_memory } = req.body;
  const cap = Math.min(max_tokens||1000, 4000);

  // LAYER 4 + 5: APP ID + PROMPT INJECTION
  if (detectInjection(messages))
    return res.status(400).json({ error:'invalid_request', message:'Your message contains content that cannot be processed.' });

  // ── DEMO PATH ──────────────────────────────────────────────────
  if (is_demo) {
    const demoCheck = await checkDemoLimits(req, app_id);
    if (demoCheck.blocked) return res.status(demoCheck.status).json({ error:'demo_limit', message:demoCheck.message, upgrade:demoCheck.upgrade });

    const params = { model:MODEL, max_tokens:Math.min(cap,400), messages:messages.slice(-6) };
    if (system) params.system = system.slice(0,2000) + '\n\n[Demo mode — encourage signup for full access and unlimited usage.]';
    try {
      const response = await anthropic.messages.create(params);
      return res.status(200).json(response);
    } catch(err) { return res.status(err.status||500).json({ error:{message:err.message} }); }
  }

  // LAYER 6: AUTHENTICATION
  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith('Bearer ')) return res.status(401).json({ error:'auth_required' });
  const { data:{ user }, error:authError } = await supabase.auth.getUser(authHeader.slice(7));
  if (authError || !user) return res.status(401).json({ error:'session_expired' });

  // LAYER 7: SUBSCRIPTION + ENTERPRISE TOKEN ENGINE
  const { data:profile } = await supabase.from('users').select('plan,status,org_id,org_name').eq('id',user.id).single();
  const plan   = profile?.plan || profile?.status || 'trialing';
  const orgId  = profile?.org_id;
  const budget = TOKEN_BUDGETS[plan] ?? TOKEN_BUDGETS['trialing'];
  const isUnlimited   = budget === -1;
  const isEnterprise  = plan?.startsWith('enterprise');
  const isAutoScale   = AUTO_SCALE_PLANS.has(plan);

  // Get monthly usage
  const monthStart = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString();
  const { data:usageData } = await supabase.from('usage_logs').select('tokens_in,tokens_out').eq('user_id',user.id).gte('created_at',monthStart);
  const monthlyUsed = (usageData||[]).reduce((s,r)=>s+(r.tokens_in||0)+(r.tokens_out||0),0);

  // Check org-level usage for enterprise (whole company, not just one user)
  let orgUsed = monthlyUsed;
  if (orgId) {
    const { data:orgUsageData } = await supabase.from('usage_logs').select('tokens_in,tokens_out')
      .eq('org_id', orgId).gte('created_at', monthStart);
    orgUsed = (orgUsageData||[]).reduce((s,r)=>s+(r.tokens_in||0)+(r.tokens_out||0), 0);
  }

  // Top-up balance
  const { data:topupRows } = await supabase.from('token_topups').select('id,tokens_remaining')
    .eq('user_id',user.id).eq('expired',false).gt('tokens_remaining',0).order('created_at',{ascending:true});
  const topupBalance = (topupRows||[]).reduce((s,r)=>s+r.tokens_remaining, 0);
  const totalBudget  = isUnlimited ? Infinity : budget + topupBalance;
  const effectiveUsed = orgId ? orgUsed : monthlyUsed;

  // Fire usage alerts (non-blocking)
  if (!isUnlimited) {
    checkAndFireUsageAlerts(user.id, orgId, plan, effectiveUsed, totalBudget).catch(()=>{});
  }

  const usagePct = isUnlimited ? 0 : effectiveUsed / totalBudget;

  // Determine response cap based on usage level
  // NEVER hard crash — always degrade gracefully
  let responseCap = cap;
  let degraded    = false;

  if (!isUnlimited && usagePct >= HARD_AT && !isAutoScale) {
    // Hard limit reached — but still respond with a helpful message
    // NOT a crash — a graceful explanation with upgrade options
    return res.status(429).json({
      error: 'token_budget_reached',
      message: `Your ${plan} plan has used all ${(totalBudget/1_000_000).toFixed(1)}M tokens this month.`,
      used:     effectiveUsed,
      budget:   totalBudget,
      plan,
      resets:   new Date(new Date().getFullYear(), new Date().getMonth()+1, 1).toISOString(),
      upgrade_options: isEnterprise ? [
        { name:'Add Token Block',   tokens:'100M',  price:'Contact sales', action:'contact' },
        { name:'Upgrade to Enterprise M', tokens:'500M/mo', price:'Custom', action:'upgrade' },
        { name:'Unlimited Plan',    tokens:'Unlimited', price:'Custom contract', action:'contact' },
      ] : [
        { name:'Token Pack S', tokens:'500K',   price:'$2.99',  price_id:'price_topup_s' },
        { name:'Token Pack M', tokens:'1.5M',   price:'$6.99',  price_id:'price_topup_m' },
        { name:'Token Pack L', tokens:'5M',     price:'$14.99', price_id:'price_topup_l' },
        { name:'Upgrade Plan', tokens:'More monthly tokens', action:'upgrade' },
      ],
      support: 'support@sairntechnologies.com',
    });
  }

  if (!isUnlimited && usagePct >= SOFT_AT) {
    // 95%+ — reduce response length to conserve tokens
    responseCap = Math.min(responseCap, 600);
    degraded    = true;
  }

  // LAYER 8: ANOMALY DETECTION
  checkAnomaly(user.id, app_id, plan).catch(()=>{});

  // LOAD MEMORY
  const memoryInjection = await buildMemoryInjection(user.id);
  const fullSystem = system ? system + memoryInjection : memoryInjection || undefined;

  // CALL CLAUDE
  const params = { model:MODEL, max_tokens:responseCap, messages:messages.slice(-30) };
  if (fullSystem) params.system = fullSystem;
  if (degraded) {
    // Append conservation note
    params.system = (params.system||'') + '\n\n[Token conservation mode: keep response concise, under 400 tokens. User is near their monthly limit.]';
  }

  let response, retries = 0;
  while (retries < 3) {
    try { response = await anthropic.messages.create(params); break; }
    catch(err) {
      if (err.status === 529 && retries < 2) { retries++; await new Promise(r=>setTimeout(r,1000*retries)); continue; }
      // Log API error as security event
      supabase.from('security_events').insert({user_id:user.id,app_id,event:'api_error',detail:err.message,severity:'warning',created_at:new Date().toISOString()}).catch(()=>{});
      return res.status(err.status||500).json({ error:{message:err.message} });
    }
  }

  const aiText = response.content?.[0]?.text || '';
  const tokIn  = response.usage?.input_tokens  || 0;
  const tokOut = response.usage?.output_tokens || 0;
  const cost   = (tokIn/1e6 * PRICING.in) + (tokOut/1e6 * PRICING.out);
  const total  = tokIn + tokOut;

  // PERSIST ALL THE THINGS
  if (aiText) {
    const cid   = conversation_id || crypto.randomUUID();
    const title = messages[messages.length-1]?.content?.slice(0,60) || 'Conversation';

    await Promise.all([
      supabase.from('conversations').upsert(
        { id:cid, user_id:user.id, org_id:orgId||null, app_id, title, updated_at:new Date().toISOString() },
        { onConflict:'id' }
      ),
      supabase.from('messages').insert([
        { conversation_id:cid, user_id:user.id, role:'user',      content:messages[messages.length-1]?.content||'', tokens_used:tokIn  },
        { conversation_id:cid, user_id:user.id, role:'assistant', content:aiText, tokens_used:tokOut }
      ]),
      supabase.from('usage_logs').insert({
        user_id:user.id, org_id:orgId||null, app_id,
        tokens_in:tokIn, tokens_out:tokOut, cost_usd:cost,
        plan, created_at:new Date().toISOString()
      }),
    ]).catch(e=>console.error('[SAIRN Persist]',e.message));

    // Memory extraction
    if (extract_memory || messages.length % 3 === 0) {
      extractMemoryBackground(user.id, app_id, messages, aiText).catch(()=>{});
    }

    // Top-up deduction
    if (topupRows?.length && !isUnlimited && effectiveUsed >= budget) {
      let remaining = total;
      for (const row of topupRows) {
        if (remaining <= 0) break;
        const deduct = Math.min(remaining, row.tokens_remaining);
        remaining -= deduct;
        supabase.from('token_topups').update({
          tokens_remaining: row.tokens_remaining - deduct,
          expired: row.tokens_remaining - deduct <= 0,
          updated_at: new Date().toISOString()
        }).eq('id', row.id).catch(()=>{});
      }
    }

    return res.status(200).json({
      ...response,
      conversation_id: cid,
      // Usage info in response — so client can show progress bar
      usage_info: isUnlimited ? { unlimited:true } : {
        used:    effectiveUsed + total,
        budget:  totalBudget,
        pct:     Math.round(((effectiveUsed + total) / totalBudget) * 100),
        plan,
        degraded,
      }
    });
  }

  return res.status(200).json(response);
}
