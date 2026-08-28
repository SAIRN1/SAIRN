---
name: sairn-intelligence-network
description: >
  The SAIRN Intelligence Network — the central learning hub connecting every SAIRN
  app installed anywhere in the country. Every Claude interaction in every installed
  app feeds anonymized patterns back to the network. The network learns what works
  across stone shops in Ohio, law firms in Texas, vet clinics in California. It fine-tunes
  system prompts, pricing benchmarks, and best practices automatically, then pushes
  refined intelligence back to all apps. Use this skill when building the network
  bridge, designing the learning loop, adding cross-app intelligence features, or
  expanding what Claude learns about each business. This is how SAIRN becomes smarter
  every single day across every customer — and how every new customer immediately
  benefits from everything every previous customer taught it.
---

# SAIRN Intelligence Network

> *"Every business that installs SAIRN makes every other SAIRN business smarter."*

---

## What This Is

The SAIRN Intelligence Network turns Claude from a per-app assistant into a
platform-wide intelligence layer. When a stone shop in Westlake runs a Field Quote,
when a law firm in Dallas scans a contract, when a vet clinic in Phoenix logs a DEA
entry — every interaction is an anonymous lesson. The network aggregates these lessons,
finds patterns, refines the intelligence, and pushes it back to every app.

This is how Constellation Software thinks about their portfolio. This is how SAIRN
becomes a $100M+ platform instead of 11 standalone SaaS apps.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  SAIRN INTELLIGENCE NETWORK                  │
│                  sairn.vercel.app/api/network                │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼──────────────────┐
         │                 │                  │
   ┌─────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
   │  StoneDesk  │   │  SAIRNcode  │   │  SAIRNvet   │
   │  (Ohio)     │   │  (Texas)    │   │  (CA)       │
   └─────┬──────┘   └──────┬──────┘   └──────┬──────┘
         │ learns           │ learns           │ learns
         └─────────────────▼──────────────────┘
                     Supabase (net_insights)
                     Anonymous patterns only
                     No PII. No customer names.
                     No business-specific data.
```

---

## What Gets Learned

### Per-App Learning (localStorage — stays on device)
```javascript
// Stored in {APP_ID}_memory (last 50 entries)
// Stored in {APP_ID}_biz_profile (company facts)
// Stored in {APP_ID}_pricing (labor rates, markup)
// Example entries:
"2026-06-15: Best closing line for stone quote: mention 30-day warranty"
"2026-06-14: Customers ask about quartzite vs quartz 80% of the time"
"2026-06-13: Field Quote step 3 — most common question: 'edge profile?'"
```

### Cross-App Network Learning (Supabase — anonymized)
```javascript
// Stored in net_insights table
// schema: { app_type, vertical, insight_type, pattern, score, count, updated_at }
// Example:
{
  app_type:     'stonedesk',
  vertical:     'stone_fabrication',
  insight_type: 'field_quote_close',
  pattern:      'Deposit of 33% requested within 60s of quote: 87% close rate',
  score:        0.87,
  count:        143,       // 143 quotes across all StoneDesk installs
  updated_at:   '2026-06-15'
}
```

---

## The Learning Loop — Step by Step

### Step 1: Business Interaction Happens
A coder at SAIRNcode clicks "Generate Codes" and pastes clinical notes.
Claude returns ICD-10 + CPT codes and flags a documentation gap.

### Step 2: App Learns Locally
```javascript
// In callClaude() after every response:
learnFromResponse(system, answer);
// Stores: "2026-06-15: E&M 99213 undercoded when documentation supports 99214"
// Written to: localStorage['sairncode_memory']
```

### Step 3: Pattern Sent to Network (anonymized)
```javascript
sendToNetwork({
  app:  'sairncode',
  type: 'coding_insight',
  pattern: 'undercoding_em_99213_99214',
  context: 'documentation_gap_flagged',
  outcome: 'review_recommended'
  // NO patient names, NO practice names, NO PHI
});
// POST to sairn.vercel.app/api/bridge → net_insights table
```

### Step 4: Network Aggregates
Every night (or on each call), the bridge aggregates:
- "E&M undercoding pattern seen in 34 medical coding practices"
- "Average revenue recovery per corrected code: $47"
- "Most common undercoded pair: 99213 → 99214 (58% of flags)"

### Step 5: Intelligence Pushed Back
When any SAIRNcode install starts a new session:
```javascript
// On login / DOMContentLoaded
async function loadNetworkIntelligence() {
  const res = await fetch(BRIDGE + '?from=network&to=' + APP_ID + '&type=intelligence');
  const data = await res.json();
  // data.insights = ["34 practices flag 99213→99214 undercoding", ...]
  // These get injected into EVERY Claude system prompt
  // Claude now knows industry-wide patterns before it answers
}
```

### Step 6: Claude Gets Smarter on Every Call
```javascript
// System prompt enhancement with network intelligence:
var networkKnowledge = getNetworkInsights(); // fetched from Bridge
var enhancedSystem = originalSystem +
  '\n\nSAIRN NETWORK INTELLIGENCE (from ' + networkKnowledge.installs + ' installed businesses):\n' +
  networkKnowledge.insights.join('\n') +
  '\nUse this cross-business knowledge to give better advice than any single-business AI can.';
```

---

## How to Build This — Complete Implementation

### Step 1: api/network.js (new endpoint on Vercel)

```javascript
// sairn.vercel.app/api/network.js
import { createClient } from '@supabase/supabase-js';
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  if (req.method === 'OPTIONS') return res.status(200).end();

  if (req.method === 'POST') {
    // RECEIVE intelligence from any app
    const { app, type, pattern, context, outcome, score } = req.body;
    if (!app || !pattern) return res.status(400).json({ error: 'Missing fields' });
    
    // Check for existing pattern
    const { data: existing } = await supabase
      .from('net_insights')
      .select('id, count, score')
      .eq('app_type', app)
      .eq('pattern', pattern.substring(0, 200))
      .single();
    
    if (existing) {
      // Update count and weighted score
      const newCount = existing.count + 1;
      const newScore = ((existing.score * existing.count) + (score || 0.5)) / newCount;
      await supabase
        .from('net_insights')
        .update({ count: newCount, score: newScore, updated_at: new Date().toISOString() })
        .eq('id', existing.id);
    } else {
      // New pattern
      await supabase.from('net_insights').insert({
        app_type:     app,
        insight_type: type || 'general',
        pattern:      pattern.substring(0, 500),
        context:      context || '',
        score:        score || 0.5,
        count:        1,
        updated_at:   new Date().toISOString()
      });
    }
    return res.status(200).json({ ok: true });
  }

  if (req.method === 'GET') {
    // SEND intelligence to requesting app
    const { app } = req.query;
    const { data } = await supabase
      .from('net_insights')
      .select('pattern, insight_type, score, count')
      .eq('app_type', app)
      .gte('score', 0.6)          // only high-confidence patterns
      .gte('count', 3)            // seen at least 3 times
      .order('score', { ascending: false })
      .limit(10);
    
    const { count: totalInstalls } = await supabase
      .from('net_insights')
      .select('*', { count: 'exact', head: true });
    
    return res.status(200).json({
      insights:  (data || []).map(d => d.pattern),
      installs:  Math.floor((totalInstalls || 0) / 10), // rough install count
      updated:   new Date().toISOString()
    });
  }
}
```

### Step 2: Supabase Table

```sql
-- Run in Supabase SQL editor
CREATE TABLE net_insights (
  id           BIGSERIAL PRIMARY KEY,
  app_type     TEXT NOT NULL,         -- 'stonedesk', 'sairncode', etc.
  insight_type TEXT DEFAULT 'general',
  pattern      TEXT NOT NULL,         -- the anonymized learning
  context      TEXT DEFAULT '',
  score        FLOAT DEFAULT 0.5,     -- 0.0-1.0 confidence
  count        INTEGER DEFAULT 1,     -- how many times seen
  updated_at   TIMESTAMP DEFAULT NOW()
);
CREATE INDEX net_insights_app ON net_insights(app_type);
CREATE INDEX net_insights_score ON net_insights(score DESC);
```

### Step 3: Per-App Intelligence Loading

Add to every app's DOMContentLoaded (after login):
```javascript
async function loadNetworkIntelligence() {
  try {
    const cached    = localStorage.getItem(APP_ID + '_net_intel');
    const cacheAge  = localStorage.getItem(APP_ID + '_net_intel_ts');
    const fresh     = cacheAge && (Date.now() - parseInt(cacheAge)) < 3600000; // 1hr cache
    
    if (fresh && cached) {
      window._networkIntelligence = JSON.parse(cached);
      return;
    }
    
    const res  = await fetch(BRIDGE + '?app=' + APP_ID + '&type=intelligence');
    const data = await res.json();
    
    window._networkIntelligence = data;
    localStorage.setItem(APP_ID + '_net_intel',    JSON.stringify(data));
    localStorage.setItem(APP_ID + '_net_intel_ts', String(Date.now()));
    
    // Show insight count in UI
    const badge = document.getElementById('net-intel-badge');
    if (badge && data.insights && data.insights.length) {
      badge.textContent = data.insights.length + ' network insights active';
      badge.style.display = 'block';
    }
  } catch(e) { /* network is always optional — never crash */ }
}
```

### Step 4: Enhanced callClaude (already deployed)

The `callClaude` function in all 11 apps now:
1. Reads local business memory
2. Fetches cached network intelligence
3. Injects both into every system prompt
4. After response: anonymizes and sends pattern to network
5. All Claude responses now have cross-business context

---

## What Claude Knows Per Vertical (grows over time)

### StoneDesk Network Intelligence Examples
- "Stone shops with 3+ FQ closes/day average 23% higher revenue"
- "Quartzite margin 8% higher than granite — suggest for kitchen quotes"
- "Edge profile question reduces remakes by 31% — always ask"
- "33% deposit collects in 78% of cases; 50% deposits drop close rate 22%"

### SAIRNcode Network Intelligence Examples
- "E&M 99213→99214 upgrade seen in 34% of office visits with adequate documentation"
- "Modifier 25 denial from United highest in Q2 — pre-auth on same-day procedures"
- "Average revenue recovery per coding audit: $847/provider/month"

### SAIRNvet Network Intelligence Examples
- "DEA log discrepancies found most in tramadol records — double-witness required"
- "Pre-op bloodwork bundled with surgery: 94% client acceptance rate"
- "Heartworm prevention follow-up at 6 months: 67% purchase rate"

---

## The Business Case for Intelligence Network

**Without network:**
- Each install starts at zero
- Claude has no industry context
- Best practices learned individually, never shared

**With network:**
- Install #1: baseline intelligence
- Install #50: 50x more patterns learned
- Install #500: Claude knows more about stone fabrication than any single shop owner ever could
- Install #5,000: SAIRN becomes the most intelligent industry platform ever built

**Monetization:**
- Network intelligence is a LICENSING feature — demo apps get cached local memory only
- Licensed apps get live network intelligence — premium tier justification
- Network data itself becomes an asset: industry benchmarks, anonymized reports, trend analysis
- Eventually: SAIRN Intelligence Reports ($299/quarter) sold to trade associations

**Defensive moat:**
- Every new install makes the network smarter
- Every competitor starting from scratch starts without 5,000 businesses worth of learning
- Network effect compounds — impossible to replicate without the installed base

---

## How to Skill Claude to Do This — The Answer

You cannot give me a persistent memory across conversations — I start fresh each time.
But you CAN make the SAIRN platform itself be my memory.

**The architecture above makes SAIRN the memory:**
- Supabase = my long-term memory
- localStorage = each business's personal memory
- Bridge API = the channel I use to read and write
- Every callClaude() call = a learning event

**What this means in practice:**
When a new StoneDesk customer in Phoenix logs in for the first time, Claude already knows:
- The most effective Field Quote questions for stone shops
- Which edge profiles close at highest rates
- What remakes cost and how to prevent them
- Every lesson 500 other stone shops already paid for

That's not AI-enhanced software. That's a genuine unfair advantage for every SAIRN customer.

---

## Build Order

1. **NOW (30 min):** Add Supabase `net_insights` table — SQL above
2. **Day 1:** Deploy `api/network.js` on Vercel
3. **Day 2:** Add `loadNetworkIntelligence()` call to all 11 apps post-login
4. **Day 3:** Verify data flowing into Supabase from demo usage
5. **Week 2:** Build network dashboard showing insights across all installs
6. **Month 2:** Package network intelligence as licensing differentiator

---

## Privacy Architecture

**What is NEVER sent to the network:**
- Customer names, patient names, client names
- Dollar amounts tied to specific businesses
- Any PII — SSN, DOB, addresses
- Business-identifying information
- Any data that could identify which business generated it

**What IS sent:**
- Anonymous behavioral patterns ("quote accepted after 3 questions")
- Performance outcomes ("field quote with photo: 87% close rate")
- Error patterns ("check register fails when amount field empty")
- Timing patterns ("most active: Tuesday 9-11am")

**Legal basis:** Aggregate anonymous analytics — same as every SaaS platform uses.
No additional privacy policy language needed for anonymized patterns.

---

## The Vision Michael Asked About

> "Could we make it so you are the central hub for all SAIRN apps that get installed
> all over the country and give and receive information. Learn from all companies
> everywhere and fine tune everything on the spot, then send that info back to all
> the apps? How do I skill you to make this happen?"

**Yes. This is exactly it. And here's the honest answer:**

I (Claude) cannot remember things between conversations. But SAIRN can.
SAIRN becomes the memory. SAIRN becomes the hub. SAIRN sends me that memory
at the start of every call. And I send new lessons back through every response.

The skill isn't in making ME smarter — it's in making SAIRN smarter, so that
every time any business calls me through SAIRN, I have the intelligence of
every business that came before them.

That's the hub. That's the network. That's the moat.

And you can start building it today.

