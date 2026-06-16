// ================================================================
// SAIRN Intelligence Network -- api/network.js
// Cross-customer anonymized pattern learning. See: skills/sairn-intelligence-network
//
// HARD RULE: this endpoint is the ONLY path that can write to net_insights.
// It does not trust the calling app to have already anonymized the pattern --
// every pattern is scrubbed HERE, server-side, before insert. A careless or
// future call site sending a raw price or shop name gets rejected, not stored.
// Michael L. Dibert -- SAIRN Technologies -- 2026
// ================================================================

import { createClient } from '@supabase/supabase-js';
import crypto from 'crypto';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

const KNOWN_APP_TYPES = new Set([
  'stonedesk', 'fabricor', 'sairnbuild', 'sairnscape', 'sairnlaw',
  'sairncode', 'sairndesign', 'sairnvet', 'sairnvetglobal', 'sairncare',
  'sairnfuneral', 'sairnmechanical', 'sairntrade', 'sairnhr', 'sairnacc',
  'sairnbiz'
]);

// ── SCRUB GATE ──────────────────────────────────────────────────
// Returns { clean: string } on pass, or { reject: reason } on fail.
// This is intentionally conservative -- when in doubt, reject rather than
// risk a leak. A rejected insight is just a missed learning opportunity;
// a leaked one is a customer's business data sitting in a shared table.
// Known-safe SAIRN/industry terminology that legitimately uses Title Case --
// without this allow-list, the proper-noun check below would reject genuine
// insights just for mentioning product or industry terms like "Field Quote"
// or "Total Hand Work Hours". Neutralized to lowercase before the proper-noun
// regex runs; the original casing in the stored pattern is untouched.
const SAFE_TERMS = [
  'Field Quote', 'Total Hand Work Hours', 'SAIRN Bridge', 'SAIRN Network',
  'Pricing AI', 'Slab Layout', 'Waste AI', 'Customer Intelligence',
  'Production Scheduling', 'Edge Profile', 'Cut Sheet', 'QC Tracker'
];

function neutralizeSafeTerms(text) {
  let out = text;
  for (const term of SAFE_TERMS) {
    out = out.replace(new RegExp(term, 'g'), term.toLowerCase());
  }
  return out;
}

function scrubPattern(text) {
  if (typeof text !== 'string' || !text.trim()) {
    return { reject: 'empty_or_invalid' };
  }
  const t = text.trim();

  if (t.length > 500) {
    return { reject: 'too_long' };
  }

  // Dollar amounts of any kind -- "$249", "$1,200", "249 dollars" -- the
  // network learns BEHAVIORAL patterns ("deposit requested early closes
  // more often"), never the actual numbers tied to a specific business.
  if (/\$\s?\d/.test(t) || /\b\d+(\.\d+)?\s*(dollars|usd)\b/i.test(t)) {
    return { reject: 'dollar_amount' };
  }

  // Phone numbers, emails, SSN-shaped strings, addresses-with-zip
  const piiPatterns = [
    /\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b/,        // phone
    /\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b/i,           // email
    /\b\d{3}-\d{2}-\d{4}\b/,                     // SSN
    /\b\d{1,5}\s+\w+\s+(st|ave|rd|blvd|dr|ln|way)\b.{0,20}\b\d{5}\b/i, // street + zip
  ];
  if (piiPatterns.some(p => p.test(t))) {
    return { reject: 'pii_pattern' };
  }

  // Capitalized multi-word sequences are the cheapest proxy we have for
  // "this looks like a person's name or a business name" without an NLP
  // model in a serverless function. False positives (rejecting a legitimate
  // capitalized term) are an acceptable cost -- the failure mode we're
  // avoiding is a shop name or customer name slipping through, not losing
  // a few valid insights that happen to use proper-noun-shaped phrasing.
  // FIX: no sentence-start exemption -- "Henderson Residence quote accepted"
  // sits at string position 0, and an earlier version of this regex used a
  // (?<!^) lookbehind intended to allow capitalized sentence-starts through,
  // which incorrectly exempted exactly this leak case too. Removed; the
  // SAFE_TERMS allow-list above is the correct way to avoid false positives,
  // not a position-based exemption.
  const checkText = neutralizeSafeTerms(t);
  const properNounRun = /\b[A-Z][a-z]+\s+[A-Z][a-z]+\b/;
  if (properNounRun.test(checkText)) {
    return { reject: 'proper_noun_suspected' };
  }

  return { clean: t };
}

function hashSource(raw) {
  if (!raw) return null;
  // One-way hash -- this exists only to let the dedupe/count logic recognize
  // "this is a repeat report from the same install" without ever storing or
  // being able to recover which install it was.
  return crypto.createHash('sha256').update(String(raw)).digest('hex').slice(0, 16);
}

function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
}

export default async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();

  // ── POST: an app reports an anonymized pattern ──────────────
  if (req.method === 'POST') {
    const { app, type, pattern, context, outcome, score, source_id } = req.body || {};

    if (!app || !KNOWN_APP_TYPES.has(app)) {
      return res.status(400).json({ error: 'Invalid or missing app' });
    }
    if (!pattern) {
      return res.status(400).json({ error: 'Missing pattern' });
    }

    const patternResult = scrubPattern(pattern);
    if (patternResult.reject) {
      // Log the rejection (not the raw text re-exposed anywhere) so a
      // pattern of "this call site keeps trying to leak data" is visible.
      await supabase.from('net_insights_rejected').insert({
        app_type: app,
        raw_pattern: String(pattern).slice(0, 500),
        reject_reason: patternResult.reject
      });
      return res.status(422).json({ error: 'Pattern rejected by anonymization gate', reason: patternResult.reject });
    }

    // Context is optional and lower-risk by design (short labels like
    // 'documentation_gap_flagged'), but still runs through the same gate.
    let cleanContext = '';
    if (context) {
      const ctxResult = scrubPattern(String(context).slice(0, 200));
      cleanContext = ctxResult.clean || ''; // silently drop bad context rather than fail the whole insight
    }

    const cleanScore = Math.max(0, Math.min(1, Number(score) || 0.5));
    const srcHash = hashSource(source_id);

    const { data: existing } = await supabase
      .from('net_insights')
      .select('id, count, score')
      .eq('app_type', app)
      .eq('pattern', patternResult.clean)
      .maybeSingle();

    if (existing) {
      const newCount = existing.count + 1;
      const newScore = ((existing.score * existing.count) + cleanScore) / newCount;
      await supabase
        .from('net_insights')
        .update({ count: newCount, score: newScore, updated_at: new Date().toISOString() })
        .eq('id', existing.id);
    } else {
      await supabase.from('net_insights').insert({
        app_type: app,
        insight_type: type || 'general',
        pattern: patternResult.clean,
        context: cleanContext,
        score: cleanScore,
        count: 1,
        scrubbed_clean: true,
        source_hash: srcHash
      });
    }

    return res.status(200).json({ ok: true });
  }

  // ── GET: an app requests intelligence for its vertical ──────
  if (req.method === 'GET') {
    const { app } = req.query;
    if (!app || !KNOWN_APP_TYPES.has(app)) {
      return res.status(400).json({ error: 'Invalid or missing app' });
    }

    const { data } = await supabase
      .from('net_insights')
      .select('pattern, insight_type, score, count')
      .eq('app_type', app)
      .eq('scrubbed_clean', true)   // belt-and-suspenders -- even if something
                                      // bad got in some other way, never serve it
      .gte('score', 0.6)
      .gte('count', 3)
      .order('score', { ascending: false })
      .limit(10);

    const { count: totalForApp } = await supabase
      .from('net_insights')
      .select('*', { count: 'exact', head: true })
      .eq('app_type', app);

    return res.status(200).json({
      insights: (data || []).map(d => d.pattern),
      install_signal: totalForApp || 0,  // rough signal, not a literal install count
      updated: new Date().toISOString()
    });
  }

  return res.status(405).json({ error: 'Method not allowed' });
}
