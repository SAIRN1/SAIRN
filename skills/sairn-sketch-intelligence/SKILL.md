---
name: sairn-sketch-intelligence
description: >
  Platform-wide SAIRN skill that gives EVERY B2B app the ability to read any hand-drawn sketch,
  rough client drawing, napkin plan, field measurement photo, or professional blueprint —
  and turn it into a scoped quote in seconds. Trigger on ANY of: "sketch", "drawing",
  "client drew", "rough plan", "napkin drawing", "hand drawing", "photo of a drawing",
  "client sent a picture", "rough sketch", "field sketch", "upload a photo", "take a picture",
  "quick quote", "rough estimate", "ballpark", "client wants a price", "scope from this",
  "read this plan", "what does this cost", or any request to extract scope or pricing from
  a visual input that is NOT a formal blueprint. This skill applies to ALL SAIRN B2B apps:
  StoneDesk (countertop slabs from kitchen sketches), SAIRNbuild (any trade scope from any drawing),
  SAIRNscape (landscape layout from property sketch), SAIRNlaw (property sketch for legal desc),
  SAIRNdesign (room layout from client sketch), SAIRNvet (floor plan for clinic layout),
  SAIRNcare (home layout for care planning), SAIRNfuneral (floor plan for service layout),
  SAIRNmechanical (equipment layout from sketch). If a user uploads, photographs, or describes
  any drawing — formal or informal — this skill activates. It is the universal visual intelligence
  layer across the entire SAIRN platform.
---

# SAIRN Sketch Intelligence — Universal Visual Quote Engine

> *"Client drew it on a napkin. SAIRN priced it in 30 seconds."*

This skill is the platform-wide visual intelligence layer for every SAIRN B2B app.
It enables any app to accept ANY drawing — professional blueprint, rough client sketch,
napkin plan, field photo, whiteboard photo — analyze it with Claude vision, ask smart
clarifying questions, and produce a scoped, printable quote.

This is not a blueprint reader. It is a **universal drawing interpreter** that works on
the worst input imaginable and still produces professional output.

---

## Apps That Use This Skill

| App | Primary Sketch Use Case |
|-----|------------------------|
| **StoneDesk** | Client kitchen/bath sketch → countertop slab layout + quote |
| **SAIRNbuild** | Any trade sketch → full scope + material takeoff + quote |
| **SAIRNscape** | Property sketch / aerial photo → landscape scope + quote |
| **SAIRNdesign** | Client room sketch → design scope + finish schedule + quote |
| **SAIRNmechanical** | Equipment room sketch → HVAC/plumbing layout + quote |
| **SAIRNvet** | Clinic floor sketch → exam room layout + equipment quote |
| **SAIRNcare** | Home floor plan photo → care environment assessment + quote |
| **SAIRNfuneral** | Facility sketch → service layout + capacity + quote |
| **SAIRNlaw** | Property sketch → legal description assist + area calc |

---

## The Sketch Intelligence Flow (Universal — All Apps)

### STEP 1 — Capture
Accept any of these inputs (all apps, no exceptions):
- Photo taken with phone camera (sketch on paper, whiteboard, napkin)
- Photo of a printed plan or blueprint
- Uploaded image file (PNG, JPG, TIFF, PDF)
- Screenshot of a digital drawing
- Multiple photos of the same sketch from different angles

UI elements required in every app:
```html
<!-- Sketch Intelligence capture UI — embed in every app's quote/estimate panel -->
<div class="sketch-capture">
  <button onclick="openCamera()">📷 Take Photo of Drawing</button>
  <button onclick="openFilePicker()">📁 Upload Drawing / PDF</button>
  <p class="hint">Any drawing works — professional plans, rough sketches, napkin drawings</p>
</div>
```

### STEP 2 — First Pass Analysis (Silent, Immediate)
Claude receives the image and silently determines:
- What type of drawing is this? (professional plan / rough sketch / napkin / photo of space / aerial)
- What is the app context? (StoneDesk = countertops, SAIRNscape = landscape, etc.)
- What can be confidently read? (dimensions, labels, symbols, areas, materials noted)
- What is unclear or missing? (no dimensions, illegible text, partial drawing)
- What questions MUST be answered before a quote is possible?

Claude does NOT output a full analysis yet. It outputs ONLY the smart questions.

### STEP 3 — Smart Question Dialog
Claude asks the minimum number of questions needed to complete the quote.
Maximum 5 questions. Never more. Never ask what Claude can figure out from the drawing.

**Question format — conversational, not a form:**
```
I can see [what Claude read clearly]. To give you an accurate quote, I need a few things:

1. [Most critical missing piece]
2. [Second most critical]
3. [Material/finish preference if not shown]

If you have any dimensions written on the drawing, those help — but if not,
I can work from what I can see and flag where I estimated.
```

**Smart question examples by app:**

*StoneDesk — kitchen sketch:*
```
I can see an L-shaped counter layout with what looks like a sink cutout on the left run.
A few quick questions:
1. What are the overall dimensions of the two runs? (Even approximate — "about 8 feet" works)
2. What edge profile are you thinking? (Eased, beveled, ogee, etc.)
3. What material — granite, quartz, quartzite, marble, or something else?
```

*SAIRNbuild — rough room sketch:*
```
I can see a rectangular room with what looks like a bathroom addition on one end.
To scope this accurately:
1. What's the approximate overall size? (footsteps work if no tape — "about 20 steps long")
2. Is this new construction or a renovation?
3. Which trades are in scope for this quote — framing, plumbing, electrical, tile, all of them?
```

*SAIRNscape — property sketch:*
```
I can see a property outline with what looks like a patio area on the back left
and some kind of bed along the front.
1. What's the approximate lot size or backyard dimensions?
2. Is the patio new or existing — and if new, what material (pavers, concrete, stamped)?
3. Are the beds new installs or cleanup/refresh of existing?
```

### STEP 4 — Quote Generation
Once questions are answered, Claude generates the full quote immediately.
No second round of questions. If something is still unclear, Claude estimates and flags it.

**Quote must include:**
- Scope summary (what is included, what is excluded)
- Line item breakdown by trade/material/task
- Material quantities (with waste factors)
- Labor estimate (hours + cost range)
- Total: Low / Mid / High
- Timeline estimate
- What's NOT included (assumptions)
- Confidence note: "Based on a rough sketch — field verify before ordering materials"

### STEP 5 — Save, Print, Convert to Job
Every quote:
- Auto-saves to client file
- Printable with signature line ("Client Approval: ___________")
- One-click convert to active job/project
- One-click request deposit (Stripe link if connected)

---

## App-Specific Intelligence Contexts

### StoneDesk — Countertop Sketch Intelligence

**What Claude looks for in ANY kitchen/bath sketch:**
- Counter runs (L-shape, U-shape, straight, island)
- Sink location (undermount, drop-in, farmhouse)
- Cooktop/range cutout
- Dishwasher panel
- Any radius corners or special shapes
- Backsplash height if noted
- Overhang for seating

**Even from a napkin sketch, Claude extracts:**
- Approximate slab count (standard slab = ~55 sq ft usable)
- Linear footage of edge work
- Cutout count
- Suggested slab layout (how many slabs, how to orient for grain matching)

**StoneDesk Claude System Prompt — Sketch Mode:**
```
You are the StoneDesk Stone Intelligence Engine analyzing a client's countertop drawing.
This may be a professional kitchen plan, a rough hand sketch, or a napkin drawing.
Your job is to extract every piece of information needed to quote countertop fabrication.

FIRST: Tell me what you can confidently see in this drawing.
THEN: Ask the minimum questions needed (max 5) to complete the quote.
NEVER ask for something you can determine from the drawing.
NEVER produce a quote until you have enough information.

When you have enough:
OUTPUT a StoneDesk Countertop Quote including:
- Slab count and layout recommendation
- Square footage (gross and net after cutouts)
- Linear footage of exposed edge
- Cutout count and type
- Material recommendation (if client noted a preference)
- Fabrication complexity rating: Standard / Complex / Premium
- Price range: Low (builder grade) / Mid (standard) / High (premium material + edges)
- Lead time estimate
- What's excluded (installation, demo, plumbing reconnect)
```

### SAIRNscape — Landscape Sketch Intelligence

**What Claude looks for:**
- Property outline / lot shape
- House footprint position
- Existing features (trees, fences, existing beds, driveway)
- Proposed features (patio, pool, beds, walls, lighting, irrigation zones)
- Any dimensions or scale indicators
- North arrow or sun orientation notes
- Drainage arrows

**SAIRNscape Claude System Prompt — Sketch Mode:**
```
You are the SAIRNscape Landscape Intelligence Engine analyzing a property sketch.
This may be a professional landscape plan, a client's rough sketch, or a hand drawing.

Read the sketch and identify: property boundaries, house footprint, existing features,
proposed work areas, hardscape vs softscape zones, any drainage or grading notes.

Ask minimum questions to determine: square footage of each work zone, material selections,
plant preferences, any specific features (fire pit, water feature, lighting Y/N).

OUTPUT a SAIRNscape Landscape Quote including:
- Zone-by-zone scope (patio, beds, lawn, trees, irrigation, lighting)
- Square footage and linear footage per zone
- Material list with quantities
- Plant list (quantity × type if specified, or allowance if not)
- Labor breakdown by zone
- Total: Low / Mid / High
- Phasing recommendation if budget is a concern
```

### SAIRNdesign — Room Sketch Intelligence

**What Claude looks for:**
- Room shape and approximate dimensions
- Window and door locations
- Existing furniture layout (if shown)
- Proposed changes noted
- Finish notes (flooring type, wall color, etc.)
- Traffic flow arrows

### SAIRNmechanical — Equipment Sketch Intelligence

**What Claude looks for:**
- Equipment locations (furnace, AC unit, water heater, boiler)
- Duct runs or pipe routes sketched
- Electrical panel location
- Access points
- Any load or BTU notes

---

## Universal Claude API Call — Sketch Mode

```javascript
async function analyzeSketch(imageBase64, appId, appContext) {
  const systemPrompts = {
    stonedesk: `You are the StoneDesk Stone Intelligence Engine...`,  // full prompt above
    sairnbuild: `You are the SAIRNbuild Construction Intelligence Engine...`,
    sairnscape: `You are the SAIRNscape Landscape Intelligence Engine...`,
    sairndesign: `You are the SAIRNdesign Interior Intelligence Engine...`,
    sairnmechanical: `You are the SAIRNmechanical HVAC Intelligence Engine...`,
    sairnvet: `You are the SAIRNvet Clinic Layout Intelligence Engine...`,
    sairncare: `You are the SAIRNcare Home Assessment Intelligence Engine...`,
    sairnfuneral: `You are the SAIRNfuneral Facility Intelligence Engine...`
  };

  const res = await fetch('https://sairn.vercel.app/api/claude', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      app_id: appId,
      is_demo: true,
      system: systemPrompts[appId],
      messages: [{
        role: 'user',
        content: [
          {
            type: 'image',
            source: { type: 'base64', media_type: 'image/jpeg', data: imageBase64 }
          },
          {
            type: 'text',
            text: `Analyze this drawing for ${appContext}. 
                   First tell me what you can confidently read.
                   Then ask the minimum questions needed to produce a complete quote.
                   Maximum 5 questions. Never ask what you can determine from the drawing.`
          }
        ]
      }]
    })
  });

  const data = await res.json();
  return data.content?.[0]?.text || '';
}

// Follow-up call — after user answers questions
async function generateQuoteFromAnswers(imageBase64, appId, appContext, conversation) {
  const res = await fetch('https://sairn.vercel.app/api/claude', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      app_id: appId,
      is_demo: true,
      system: systemPrompts[appId],
      messages: [
        ...conversation, // full back-and-forth history
        {
          role: 'user',
          content: 'Now generate the full quote based on everything we discussed.'
        }
      ]
    })
  });
  const data = await res.json();
  return data.content?.[0]?.text || '';
}
```

---

## Conversation State Management

The sketch intelligence flow is multi-turn (analysis → questions → answers → quote).
State must persist across turns in the same session.

```javascript
// Sketch session state
let sketchSession = {
  appId: null,
  imageBase64: null,
  conversation: [],      // full message history for Claude
  phase: 'capture',      // capture → analysis → questions → answering → quote → saved
  questionCount: 0,
  quoteData: null
};

// Add message to conversation
function addToConversation(role, content) {
  sketchSession.conversation.push({ role, content });
}

// User answers a question — add to history, re-call Claude
async function submitAnswers(userText) {
  addToConversation('user', userText);
  sketchSession.phase = 'quote';
  const quote = await generateQuoteFromAnswers(
    sketchSession.imageBase64,
    sketchSession.appId,
    appContexts[sketchSession.appId],
    sketchSession.conversation
  );
  addToConversation('assistant', quote);
  renderQuote(quote);
}
```

---

## Quote Output Standard (All Apps)

Every sketch quote produces this structure regardless of app:

```
[APP NAME] SKETCH QUOTE
─────────────────────────────────────────────────────
Client: _______________    Date: _______________
Project: _______________   Prepared by: SAIRN AI
Input: Hand sketch / Rough drawing / Field photo
─────────────────────────────────────────────────────

SCOPE SUMMARY
[What is included in plain English]

LINE ITEM BREAKDOWN
─────────────────────────────────────────
[Item]                    [Qty]    [Est. Cost]
─────────────────────────────────────────
[items]
─────────────────────────────────────────
SUBTOTAL:                          $[X]
Tax (if applicable):               $[X]
TOTAL ESTIMATE:                    $[X]

PRICE RANGE
Low:  $[X]   |   Mid: $[X]   |   High: $[X]

TIMELINE ESTIMATE: [X] days / weeks

NOT INCLUDED
[Clear exclusions — what client needs to know]

ASSUMPTIONS & FLAGS
[What Claude estimated vs. confirmed — field verify before ordering]

─────────────────────────────────────────────────────
This quote is based on a sketch or rough drawing.
Verify all dimensions in the field before material orders.
─────────────────────────────────────────────────────
Client Approval: _______________________ Date: _______
[Authorized Signature]: ________________ Date: _______
─────────────────────────────────────────────────────
```

---

## Guardian Checklist — Sketch Intelligence Module

- [ ] Camera capture works on mobile (iOS and Android)
- [ ] File upload accepts PNG, JPG, TIFF, PDF (PDF → canvas rendered)
- [ ] Image converted to base64 client-side before Claude call
- [ ] Claude called via proxy ONLY — never api.anthropic.com
- [ ] `app_id` matches the app this is embedded in
- [ ] Conversation history passed on every follow-up Claude call
- [ ] Maximum 5 questions enforced in prompt — no interrogating the client
- [ ] Quote renders in HTML — no Unicode box chars in JS strings
- [ ] Quote auto-saves to client file in app
- [ ] Print button works — print-color-adjust: exact
- [ ] "Convert to Job" button present on every quote
- [ ] Confidence note present on every sketch-based quote
- [ ] Signature line on printed quote

---

## Deployment — Which Apps Get This Now

**Priority 1 (immediate — highest revenue impact):**
- StoneDesk — client kitchen sketch → countertop quote (closes jobs on the spot)
- SAIRNbuild — any trade sketch → full scope quote
- SAIRNscape — property sketch → landscape quote

**Priority 2 (next build cycle):**
- SAIRNdesign, SAIRNmechanical, SAIRNvet, SAIRNcare, SAIRNfuneral

---

*SAIRN Sketch Intelligence: Any drawing. Any app. Quoted in 30 seconds.*
