---
name: sairn-app-scaffold
description: 'The starting-point checklist for scaffolding a new SAIRN app from zero. Created 2026-07-30 -- a prior session referenced this skill in a handoff before it actually existed on disk; this is the first real version, not a restoration. Currently covers one required component (photo-capture -> Claude analysis -> structured app output, generalized from StoneDesk''s Field Sketch Quote) rather than a full scaffold from A to Z. Trigger when starting a new SAIRN app from scratch, or when deciding what a new app''s v1 must include before the first panel gets built.'
---

# SAIRN App Scaffold

This file does not yet cover everything a new app needs (data model conventions, licensing setup, etc. live in `sairn-software-architect` and `SAIRNBUILD-SCOPE.md`-style scoping docs for now). What it does cover is a single standing requirement, added 2026-07-30 as a product decision: **every new SAIRN app's v1 scope must include the photo-to-Claude-suggestion pattern**, not bolt it on after the fact.

## Required component: Photo Capture → Claude Analysis → Structured Output

### Why this is required, not optional

StoneDesk's Field Sketch Quote (a rep photographs a hand-drawn sketch on a jobsite, Claude reads it, asks up to 3 clarifying questions, then generates a priced quote) is a proven, working pattern — real code, live in production, not a concept. The standing product rule: every new SAIRN app should carry the same *shape* of feature from day one, with the output adapted to that app's vertical. What changes per app is only the output; the photo-capture → Claude-call plumbing is identical and should not be reinvented per app.

### The generic 3-stage pattern

1. **Photo capture UI** — a tap-to-photograph zone, camera-first on mobile:
   ```html
   <input type="file" accept="image/*" capture="environment">
   ```
   `capture="environment"` opens the rear camera directly on a phone instead of a generic file picker — this is what makes it a field tool, not a desktop upload form. Show a preview (`<img>`) after capture, and encode the file to base64 client-side before sending it anywhere (`FileReader.readAsDataURL`).

2. **Claude analysis call, through the proxy — never direct**. Per the platform's standing Proxy rule (Guardian Check 1), this must go through `sairn.vercel.app/api/claude`, never `api.anthropic.com` directly, and the request body must include `app_id` and `is_demo:true` (Guardian Checks 3–4). The image goes in as a multimodal content block alongside a text instruction:
   ```js
   const msgs = [{
     role: 'user',
     content: [
       {type:'image', source:{type:'base64', media_type:'image/jpeg', data: img64}},
       {type:'text', text: 'Analyze this photo for <app-specific task>.'}
     ]
   }];
   const res = await fetch('https://sairn.vercel.app/api/claude', {
     method:'POST', headers:{'Content-Type':'application/json'},
     body: JSON.stringify({app_id: APP_ID, is_demo:true, system, messages: msgs})
   });
   ```
   The system prompt is where the app-specific behavior lives — StoneDesk's says "read the drawing, ask MAXIMUM 3 questions, be fast, the customer is watching." Cap the clarifying questions explicitly in the prompt; an open-ended back-and-forth is not what a field rep standing in front of a customer needs.

3. **App-specific structured output.** This is the one piece that must NOT be copy-pasted between apps — the shape of what Claude returns should match the vertical:
   - **StoneDesk / trades (built, live)** — photo → up to 3 questions → itemized quote (line items, Low/Mid/High total, exclusions, 30-day validity, signature line)
   - **SAIRNbuild** — photo of a jobsite issue → cost/scope suggestions (not yet built — flag this as a gap against the current 4-panel scope, not an existing feature)
   - **SAIRNvet** — photo → diagnosis suggestions (not yet built — same caveat; SAIRNvet's current build status should be re-verified independently before assuming this is a gap vs. already covered)
   - Any new app — pick the output shape that matches what that app's user actually needs from a photo, don't default to "generate a quote" if the vertical isn't sales-facing.

### Honest note on "structured output" — read the real implementation before overclaiming

StoneDesk's actual implementation is **not** strict JSON-schema output. Both Claude calls (`sairnFQAnalyze`, `sairnFQGenQuote` in `stonedesk.html`) return free-text (`data.content[0].text`), and the app extracts what it needs with a targeted regex against that text (e.g. `r.match(/Mid[:\s]+\$?([\d,]+)/i)` to pull one dollar figure for a deposit calculation) rather than parsing a JSON object. That is the proven baseline — free text plus light, targeted extraction, not a fragile full-JSON contract. A new app is free to ask Claude for stricter JSON if its output genuinely needs it (e.g. a diagnosis-suggestions list with confidence scores), but should treat that as an enhancement on top of the proven pattern, not assume the reference implementation already works that way.

### Reference implementation (the one real one — verify current line numbers before citing, `stonedesk.html` grows)

- DOM: `#sairn-fq-modal` and children (`#sairn-fq-p1`–`p5` — the 5 steps: trade select, photo capture, AI Q&A, quote output, close/deposit)
- Photo capture + preview: `~L12265-12280`, file input handler ending `reader.readAsDataURL(file)` at `L12557`
- Analysis call: `window.sairnFQAnalyze` at `L12560`
- Quote generation call: `window.sairnFQGenQuote` at `L12592`
- Shared proxy helper: `async function sairnCallClaude(system, messages)` at `L12740` — POSTs to `SAIRN_PROXY = 'https://sairn.vercel.app/api/claude'` with `{app_id, is_demo:true, system, messages}`, returns `data.content?.[0]?.text || ''`

New apps should write their own equivalent of `sairnCallClaude` (or literally reuse the same shape) rather than inventing a different request/response contract — one proxy-call convention across the platform, not one per app.

## What still needs to be added to this scaffold (not done tonight)

This file currently covers only the photo→Claude→output requirement. A complete new-app scaffold checklist (data model prefix convention, licence gate pattern, Vercel route + `vercel.json` wiring per the Iron Law, demo-seed conventions) is not yet consolidated here — those live piecemeal in `sairn-software-architect`, `sairn-guardian-v2`, and per-app `*-SCOPE.md` docs today. Flagging so a future session doesn't assume this file is comprehensive just because it exists.
