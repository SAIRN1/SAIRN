// ═══════════════════════════════════════════════════════════════════
//  SAIRN Technologies — /api/memory
//  The NEXUS Cross-Module Intelligence Engine
//
//  This is the patent. This is what no competitor can copy.
//
//  HOW IT WORKS:
//  1. After every conversation, extract key facts about the user
//  2. Store them in a structured memory profile per user
//  3. At the START of every new conversation, inject that memory
//     into Claude's system prompt — so Claude already knows them
//  4. Memory compounds across ALL 15 apps — what you tell SAIRN
//     Career, SAIRN Mind knows. What SAIRN Kitchen learns,
//     SAIRN Daily uses. One intelligence, fifteen faces.
//
//  Michael L. Dibert · SAIRN Technologies · 2026
//  Patent Pending: Cross-Module Intelligence Architecture
// ═══════════════════════════════════════════════════════════════════

import Anthropic from '@anthropic-ai/sdk';
import { createClient } from '@supabase/supabase-js';

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const supabase  = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
const MODEL     = 'claude-haiku-4-5-20251001';

// ── MEMORY EXTRACTION PROMPT ──────────────────────────────────────
const EXTRACTOR_PROMPT = `You are a memory extraction system for SAIRN, an AI platform for families.

Read the conversation below and extract ONLY concrete, useful facts about the user that would help any SAIRN app serve them better in the future.

Extract facts in these categories (only include categories where you learned something real):
- PERSONAL: name, age, location, family members, occupation, life situation
- HEALTH: conditions, medications, allergies, fitness goals, dietary needs
- FAMILY: children (names/ages), partner, caregiving responsibilities
- CAREER: job, industry, goals, salary situation, job search status
- HOME: owns/rents, location, housing issues, HOA, repairs needed
- FINANCE: budget concerns, debt, savings goals, financial stress
- LEGAL: ongoing legal matters, documents reviewed, rights questions
- MENTAL: stress levels, anxiety triggers, coping strategies that work, sleep issues
- FOOD: dietary restrictions, allergies, favorite cuisines, cooking skill level
- GOALS: what they're working toward, what they've asked for help with
- PREFERENCES: communication style, how detailed they want answers

Rules:
- Only extract FACTS, not opinions or guesses
- Only extract things that ACTUALLY CAME UP in the conversation
- Be specific: "has a 7-year-old daughter named Emma" not "has children"
- Skip trivial facts that won't help future conversations
- Maximum 10 facts per conversation

Respond ONLY with valid JSON. No markdown, no explanation. Format:
{
  "facts": [
    {"category": "PERSONAL", "fact": "lives in Columbus, Ohio", "confidence": "high"},
    {"category": "FAMILY", "fact": "has a 7-year-old daughter named Emma", "confidence": "high"}
  ],
  "summary": "One sentence describing this person based on what you learned today."
}

If nothing meaningful was learned, return: {"facts": [], "summary": ""}`;

// ── MEMORY PROMPT BUILDER (called by claude.js) ───────────────────
export function buildMemoryPrompt(memoryProfile) {
  if (!memoryProfile?.facts?.length) return '';

  const facts = memoryProfile.facts
    .filter(f => f.confidence !== 'low')
    .slice(-20)
    .map(f => `- ${f.fact}`)
    .join('\n');

  if (!facts) return '';

  return `\n\nWHAT YOU ALREADY KNOW ABOUT THIS USER (learned across all SAIRN apps):
${facts}
${memoryProfile.summary ? `\nWho they are: ${memoryProfile.summary}` : ''}

Use this naturally — don't announce that you remember things, just let it make your help more personal. If something has changed, update your understanding.`;
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', process.env.SITE_URL || '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();

  // ── AUTH ────────────────────────────────────────────────────────
  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith('Bearer ')) return res.status(401).json({ error: 'No session' });
  const { data: { user }, error: authError } = await supabase.auth.getUser(authHeader.slice(7));
  if (authError || !user) return res.status(401).json({ error: 'Invalid session' });

  // ── GET MEMORY ──────────────────────────────────────────────────
  if (req.method === 'GET') {
    const { data } = await supabase
      .from('user_memory').select('*').eq('user_id', user.id).single();
    return res.status(200).json({ memory: data || null });
  }

  // ── POST: extract or clear ──────────────────────────────────────
  if (req.method === 'POST') {
    const { action, messages, app_id } = req.body || {};

    // ── CLEAR ───────────────────────────────────────────────────
    if (action === 'clear') {
      await supabase.from('user_memory').delete().eq('user_id', user.id);
      return res.status(200).json({ cleared: true });
    }

    // ── EXTRACT ─────────────────────────────────────────────────
    if (action === 'extract' && messages?.length) {
      try {
        const transcript = messages
          .map(m => `${m.role === 'user' ? 'User' : 'SAIRN'}: ${m.content}`)
          .join('\n\n');

        if (transcript.length < 80) return res.status(200).json({ extracted: 0 });

        // Ask Claude Haiku to extract facts — cheap, fast
        const extraction = await anthropic.messages.create({
          model: MODEL,
          max_tokens: 600,
          messages: [{ role: 'user', content: `${EXTRACTOR_PROMPT}\n\n--- CONVERSATION (${app_id}) ---\n${transcript.slice(0, 3000)}` }]
        });

        const raw = extraction.content?.[0]?.text || '{}';
        let parsed;
        try { parsed = JSON.parse(raw.replace(/```json|```/g, '').trim()); }
        catch { return res.status(200).json({ extracted: 0 }); }

        if (!parsed.facts?.length) return res.status(200).json({ extracted: 0 });

        // Load existing memory
        const { data: existing } = await supabase
          .from('user_memory').select('*').eq('user_id', user.id).single();

        const existingFacts = existing?.facts || [];
        const newFacts = parsed.facts.map(f => ({
          ...f, app_id, extracted_at: new Date().toISOString()
        }));

        // Smart merge — update facts in same category when more specific
        const merged = [...existingFacts];
        for (const nf of newFacts) {
          const idx = merged.findIndex(ef =>
            ef.category === nf.category &&
            (ef.fact.toLowerCase().split(' ').slice(0,3).join(' ') ===
             nf.fact.toLowerCase().split(' ').slice(0,3).join(' '))
          );
          if (idx >= 0) merged[idx] = nf; // update existing
          else merged.push(nf);           // add new
        }

        const trimmed = merged.slice(-50); // keep 50 most recent facts

        await supabase.from('user_memory').upsert({
          user_id: user.id,
          facts: trimmed,
          summary: parsed.summary || existing?.summary || '',
          last_updated: new Date().toISOString(),
          total_conversations: (existing?.total_conversations || 0) + 1,
          apps_used: [...new Set([...(existing?.apps_used || []), app_id])]
        }, { onConflict: 'user_id' });

        return res.status(200).json({ extracted: newFacts.length, total_facts: trimmed.length });

      } catch (err) {
        console.error('[SAIRN Memory]', err.message);
        return res.status(500).json({ error: 'Memory extraction failed' });
      }
    }

    return res.status(400).json({ error: 'Unknown action' });
  }

  return res.status(405).json({ error: 'Method not allowed' });
}
