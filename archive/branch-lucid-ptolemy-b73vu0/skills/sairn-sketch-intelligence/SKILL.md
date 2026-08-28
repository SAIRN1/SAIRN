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

---

## FIELD SALES MODE — Salesperson Sketch-to-Quote

> *"Rep draws it on a notepad in the driveway. Claude prices it before they ring the doorbell."*

This is the field sales use case. A salesperson is at a prospect's location.
They sketch the scope on any paper. They photograph it with their phone.
SAIRNbuild (or any SAIRN app) reads the sketch, applies the company's pricing parameters,
and generates a professional quote — ready to present, sign, and collect a deposit.
No office. No laptop. No waiting.

---

### Field Sales Flow — Step by Step

**1. Rep opens the app on their phone**
Any SAIRN B2B app. Tap "Quick Quote" or "Field Quote" from the home screen.
This is a persistent shortcut — always one tap from anywhere in the app.

**2. Rep selects industry/trade scope**
Pre-set by the company in Admin settings. Examples:
- StoneDesk: Kitchen Counters / Bathroom Vanity / Fireplace Surround / Custom
- SAIRNbuild: Roofing / Siding / Bathroom Remodel / Addition / Full Build
- SAIRNscape: Full Landscape / Patio / Lawn Install / Cleanup / Irrigation
- SAIRNmechanical: AC Replace / Furnace / Full HVAC / Water Heater
- SAIRNvet: Clinic Build-Out / Equipment Install / Kennel Addition

**3. Rep sketches scope on any paper**
- Notepad, napkin, back of a business card, whiteboard, customer's paper
- Dimensions if known, arrows, labels — whatever they have
- Even a rough shape with one or two numbers is enough

**4. Rep photographs the sketch**
- One tap: "Take Photo of Sketch"
- No special lighting, no flat surface required
- Multiple photos accepted if sketch is on multiple pages

**5. Claude analyzes + asks max 3 field questions**
In field sales mode, question limit drops from 5 to 3. Rep is standing in front of a
customer — Claude asks only what absolutely cannot be estimated:

```
I can see [scope]. Quick questions before your quote:
1. [Single most critical missing dimension or material]
2. [Second most critical — skip if estimable]
3. [Material tier — budget / standard / premium — if not specified]
```

Rep answers by voice-to-text or typing. 30 seconds total.

**6. Claude generates the quote using company pricing parameters**
This is the key. Claude does NOT use generic price ranges.
It applies the company's own pricing that the owner/admin set in the app.

**7. Quote displays on screen — ready to show the client**
Professional. Branded. Itemized. Signature line at the bottom.
Rep turns the phone to the client. "Here's your quote."

**8. Client signs on screen (or prints via AirPrint)**
Digital signature captured. Quote saved to client file. Deposit link sent via text.

---

### Company Pricing Parameters — Admin Setup

Every SAIRN B2B app has a Pricing Admin panel where the owner sets:

```javascript
// Pricing parameter structure — stored per company in localStorage / Supabase
const pricingParams = {
  // Labor rates
  laborRates: {
    standard: 85,        // $ per hour — standard crew
    lead: 120,           // $ per hour — lead/foreman
    specialty: 150       // $ per hour — specialty trade
  },

  // Material markup
  materialMarkup: 0.30,  // 30% markup on material cost

  // Overhead + profit
  overheadPercent: 0.15, // 15% overhead
  profitPercent: 0.20,   // 20% profit margin

  // Unit pricing (trade-specific — owner sets these)
  unitPricing: {
    // StoneDesk example
    granite_sqft: 65,          // installed $/sqft
    quartz_sqft: 75,
    quartzite_sqft: 95,
    marble_sqft: 110,
    edge_linear_ft: 18,        // per LF of edge work
    sink_cutout: 150,
    cooktop_cutout: 125,

    // SAIRNbuild roofing example
    shingles_square_installed: 350,
    metal_roofing_square: 650,
    tear_off_square: 75,

    // SAIRNscape example
    paver_patio_sqft: 22,
    sod_sqft: 1.25,
    mulch_yard: 65,
    plant_install_each: 45
  },

  // Minimums
  minimumJobValue: 500,

  // Tax
  taxRate: 0.0,          // 0 = owner handles tax separately

  // Quote validity
  quoteValidDays: 30
};
```

**Admin Pricing Panel UI:**
- Owner sets all rates once during onboarding
- Can update anytime (price increases, market changes)
- Changes apply to all future quotes immediately
- Historical quotes preserve the rates they were generated with
- Import from CSV for large price lists

---

### Claude Field Sales System Prompt

```
You are the SAIRN Field Sales Intelligence Engine embedded in {APP_NAME}.
A salesperson is standing in front of a customer and has photographed a rough sketch
of the project scope.

COMPANY PRICING PARAMETERS:
{JSON.stringify(pricingParams, null, 2)}

YOUR JOB:
1. Read the sketch — extract every dimension, label, and scope indicator visible
2. Identify what you can price immediately using the company's parameters
3. Ask MAXIMUM 3 questions — rep is in the field, customer is watching
4. Never ask what you can estimate or determine from the sketch
5. After answers: generate a complete, professional, itemized quote
6. Apply the company's exact pricing parameters — not generic market ranges
7. Show line items so the customer sees the value, not just a lump sum
8. Include a "What's Included" and "What's Not Included" section
9. Add a quote validity date ({quoteValidDays} days from today)

FIELD SALES QUOTE FORMAT:
- Clean, professional, easy to read on a phone screen
- Company branded (use app color scheme)
- Line items with quantities and unit prices
- Subtotal, any applicable fees, total
- "Quote valid for {X} days"
- Signature line: "I authorize this work: _____________ Date: _____"
- Deposit line: "Deposit to schedule: $_______ (____% of total)"

TONE: Confident. Professional. Fast. This is a closing document.
```

---

### Field Quote UI Requirements (All Apps)

```html
<!-- Field Quote button — persistent, always one tap away -->
<button class="field-quote-btn" onclick="startFieldQuote()">
  📷 Field Quote
</button>

<!-- Field Quote flow panels -->
<div id="field-quote-panel">

  <!-- Step 1: Trade selector -->
  <div id="fq-trade-select">
    <h3>What are you quoting?</h3>
    <!-- Dynamic from company's configured trades -->
  </div>

  <!-- Step 2: Camera capture -->
  <div id="fq-capture">
    <button onclick="captureSketch()">📷 Photo Your Sketch</button>
    <input type="file" accept="image/*" capture="environment" id="sketch-input">
    <p>Any drawing works — notepad, napkin, anything</p>
  </div>

  <!-- Step 3: Claude questions (max 3, displayed conversationally) -->
  <div id="fq-questions">
    <div id="claude-response"></div>
    <textarea id="rep-answers" placeholder="Type your answers..."></textarea>
    <button onclick="submitAnswers()">Generate Quote →</button>
  </div>

  <!-- Step 4: Quote display -->
  <div id="fq-quote">
    <div id="quote-output"></div>
    <button onclick="showToClient()">Show Client</button>
    <button onclick="captureSignature()">Get Signature</button>
    <button onclick="sendDepositLink()">Send Deposit Link</button>
    <button onclick="printQuote()">Print / AirPrint</button>
    <button onclick="saveToFile()">Save to Client File</button>
  </div>

</div>
```

---

### Signature Capture (Field Close)

```javascript
// Canvas-based signature capture — works on any touchscreen
function initSignatureCanvas() {
  const canvas = document.getElementById('sig-canvas');
  const ctx = canvas.getContext('2d');
  let drawing = false;

  canvas.addEventListener('touchstart', (e) => {
    drawing = true;
    ctx.beginPath();
    ctx.moveTo(e.touches[0].clientX - canvas.offsetLeft,
               e.touches[0].clientY - canvas.offsetTop);
  });

  canvas.addEventListener('touchmove', (e) => {
    if (!drawing) return;
    e.preventDefault();
    ctx.lineTo(e.touches[0].clientX - canvas.offsetLeft,
               e.touches[0].clientY - canvas.offsetTop);
    ctx.stroke();
  });

  canvas.addEventListener('touchend', () => { drawing = false; });
}

function captureSignature() {
  const canvas = document.getElementById('sig-canvas');
  return canvas.toDataURL('image/png'); // save to quote record
}
```

---

### Deposit Link (Close the Deal)

```javascript
// After signature — send deposit request via text
async function sendDepositLink(quoteTotal, clientPhone, depositPercent = 0.33) {
  const depositAmount = (quoteTotal * depositPercent).toFixed(2);
  const stripeLink = `https://buy.stripe.com/[configured_link]?amount=${depositAmount * 100}`;

  // Send via SMS (Twilio if configured, or native share)
  if (navigator.share) {
    await navigator.share({
      title: 'Deposit to Schedule Your Project',
      text: `Your quote is approved! Submit your deposit of $${depositAmount} to get on the schedule: ${stripeLink}`,
      url: stripeLink
    });
  }
}
```

---

### Industries + Parameter Templates (Pre-Built)

When a company first sets up, they pick their industry and get pre-filled pricing
they can adjust — not start from scratch:

| Industry | Pre-Filled Unit Prices |
|----------|----------------------|
| Stone Fabrication | Granite/quartz/marble per sqft installed, edges, cutouts |
| General Contractor | Per-trade labor rates, overhead, material markup |
| Landscaping | Paver, sod, plant, irrigation per unit |
| HVAC/Mechanical | Equipment + labor by system type |
| Roofing | Per square by material type |
| Electrical | Per circuit, per panel, per fixture |
| Plumbing | Per fixture rough-in, per linear foot |
| Painting | Per sqft interior/exterior |
| Flooring | Per sqft by material type |
| Tile | Per sqft installed by tile size |

---

### Guardian Checklist — Field Sales Mode

- [ ] "Field Quote" button visible from home screen — one tap, always
- [ ] Camera opens directly to rear camera (not front-facing)
- [ ] `capture="environment"` on file input (rear camera on mobile)
- [ ] Max 3 questions enforced in field sales system prompt
- [ ] Company pricing parameters loaded before Claude call
- [ ] Pricing params passed in Claude system prompt as JSON
- [ ] Quote displays cleanly on phone screen (readable at arm's length)
- [ ] Signature canvas works on touchscreen
- [ ] "Show Client" mode hides rep-facing UI elements
- [ ] Deposit link uses native share sheet (navigator.share)
- [ ] Quote saved to client file on submit
- [ ] All Claude calls via proxy — never api.anthropic.com
- [ ] Works offline for display (quote cached) — only Claude call needs connection

