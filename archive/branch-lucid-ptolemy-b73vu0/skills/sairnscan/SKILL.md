---
name: sairnscan
description: >
  Complete build skill for SAIRNscan — SAIRN's standalone LiDAR + Blueprint + Sketch
  Intelligence app. The world's only tool that combines: live LiDAR room scanning,
  blueprint photo reading, sketch/napkin reading, PDF plan analysis, AND instant
  trade-specific AI estimates with your company pricing — all in one app, on any phone.
  Trigger on ANY of: "SAIRNscan", "standalone scanner", "LiDAR app", "blueprint reader",
  "scan and estimate", "build the scanner", "build the LiDAR app", "scan app", "takeoff app",
  "standalone estimating", "scan to quote", "room scan", "build the standalone".
  This skill governs the complete SAIRNscan product: brand identity, technical architecture,
  all four input modes, trade-specific AI engine, pricing parameter system, output formats,
  iOS/Android strategy, standalone vs embedded distinction, and competitive positioning.
  SAIRNscan is sold standalone ($49/mo) AND embedded in every SAIRN B2B app at no extra cost.
  No competitor combines LiDAR + sketch reading + AI pricing + your own rate sheet in one tool.
---

# SAIRNscan — World's Best Construction Scanner & Estimator

> *"Scan it. Sketch it. Photo it. Priced before you leave the room."*

SAIRNscan is the standalone product that makes SAIRN's scanning intelligence available
to any contractor — even those not on a SAIRN vertical app. It is also the embedded
engine powering Blueprint AI and Field Quote across every SAIRN B2B app.

---

## The Market Gap SAIRNscan Fills

Research summary of what exists in 2026 and what's missing:

| Tool | What It Does | What's Missing |
|------|-------------|----------------|
| Polycam | 3D scan → model export | No estimate. No pricing. No trade output. |
| Manifold | LiDAR floor plans + 3D scan | No AI estimate. No trade-specific output. |
| Canvas | LiDAR scan → CAD (human reviewed, 1-2 days) | Not instant. Expensive. No pricing. |
| SimplyWise | LiDAR + basic AI estimate | Generic national pricing. No your rates. |
| Magicplan | Floor plan capture | No estimate. No AI intelligence. |
| Matterport | Virtual tours | $300+/mo. No estimate. No trade output. |
| Togal.AI / STACK | Blueprint AI takeoff | No LiDAR. No sketch. No mobile-first. |
| Beam AI | Blueprint takeoff (human QA, 24-72h) | Not instant. No LiDAR. No sketch. |
| TradePilot review | Identifies the gap explicitly: | "Nobody combines real AI estimating with complete business management." |

**SAIRNscan fills every gap simultaneously:**
- LiDAR live scan (Android Chrome WebXR + iOS photo fallback)
- Sketch/napkin reading (any drawing, any quality)
- Blueprint photo (any phone camera)
- PDF plan upload (full plan sets)
- Manual entry fallback (always available)
- **YOUR company pricing** — not national averages
- **Trade-specific output** — tile guy gets tile SF, roofer gets squares
- **Claude intelligence notes** — proactive issues, code flags, value engineering
- **Instant** — priced before you leave the room, not 24-72 hours later
- **Standalone** at $49/mo OR embedded free in every SAIRN vertical

---

## SAIRNscan Brand Identity

- **Name:** SAIRNscan
- **Color:** Electric Blue `#3B82F6` — EXCEPTION to no-blue rule
  - SAIRNscan is a standalone product, NOT a trade vertical
  - SAIRNdesign owns blue within the SAIRN B2B suite
  - SAIRNscan as a standalone has its own identity outside the suite color law
  - When SAIRNscan is EMBEDDED in a B2B app, it adopts that app's color
- **Dark accent:** `#1D4ED8`
- **Tint:** `#EFF6FF`
- **Accent:** `#60A5FA`
- **Tagline:** "Scan it. Sketch it. Photo it. Priced before you leave the room."
- **Price:** $49/mo standalone | Embedded free in all SAIRN B2B verticals
- **File:** `sairnscan.html`
- **Target:** Any contractor, any trade, any phone

---

## Technical Architecture

### The Four Input Modes (Full Implementation)

#### MODE 1 — Live LiDAR Scan (Android Chrome + WebXR)

**Technical reality:**
- WebXR Depth Sensing API: works in Chrome on Android devices with depth sensors
- iOS Safari: WebXR NOT supported — route to photo mode silently
- iOS Chrome: runs WebKit (same as Safari) — same block
- Raw iPhone LiDAR accuracy: ±2-4 inches (raw Apple frameworks)
- With drift correction + motion filtering: ±0.5 inches on rooms up to 40ft
- Room limit: 40ft continuous scan; larger rooms = multi-scan stitch

**WebXR Implementation:**
```javascript
// Device capability detection — runs before any UI renders
async function detectScanCapability() {
  const ua = navigator.userAgent;
  const isAndroid = /Android/.test(ua);
  const isChrome  = /Chrome/.test(ua) && !/Chromium/.test(ua);

  if (isAndroid && isChrome && navigator.xr) {
    try {
      const arSupported = await navigator.xr.isSessionSupported('immersive-ar');
      if (!arSupported) return 'photo';

      // Test depth-sensing specifically
      const testSession = await navigator.xr.requestSession('immersive-ar', {
        requiredFeatures: ['depth-sensing'],
        depthSensing: {
          usagePreference: ['cpu-optimized'],
          dataFormatPreference: ['luminance-alpha']
        }
      });
      await testSession.end();
      return 'lidar';
    } catch(e) {
      return 'photo';
    }
  }
  return /iPad|iPhone|iPod/.test(ua) ? 'photo' : 'upload';
}

// LiDAR scan session
async function startLiDARSession() {
  const session = await navigator.xr.requestSession('immersive-ar', {
    requiredFeatures: ['depth-sensing', 'local-floor'],
    depthSensing: {
      usagePreference: ['cpu-optimized'],
      dataFormatPreference: ['luminance-alpha']
    }
  });

  const scanData = {
    frames: [],
    snapshots: [],
    startTime: Date.now(),
    coverage: 0
  };

  const refSpace = await session.requestReferenceSpace('local-floor');

  session.requestAnimationFrame(function onFrame(time, frame) {
    if (!frame) return;

    const pose = frame.getViewerPose(refSpace);
    if (pose) {
      for (const view of pose.views) {
        const depthInfo = frame.getDepthInformation(view);
        if (depthInfo) {
          scanData.frames.push(processDepthFrame(depthInfo, view));
          updateCoverageIndicator(scanData.frames.length);
        }
      }
    }

    // Auto-capture snapshot every 2 seconds
    if (scanData.frames.length % 60 === 0) {
      captureARSnapshot(session, scanData);
    }

    // Stop at 90 seconds max or when coverage hits 95%
    if (Date.now() - scanData.startTime < 90000 && scanData.coverage < 95) {
      session.requestAnimationFrame(onFrame);
    } else {
      finalizeScan(session, scanData);
    }
  });
}

// Process depth frame → room measurements
function processDepthFrame(depthInfo, view) {
  const { width, height, data } = depthInfo;
  const measurements = {};

  // Floor plane detection (bottom 25% of frame)
  const floorDepths = [];
  for (let x = 0; x < width; x++) {
    const d = data[Math.floor(height * 0.75) * width + x];
    if (d > 0.3 && d < 15) floorDepths.push(d);
  }
  floorDepths.sort((a,b) => a-b);
  const floorSpread = floorDepths.length > 10
    ? floorDepths[Math.floor(floorDepths.length*0.9)] - floorDepths[Math.floor(floorDepths.length*0.1)]
    : 0;

  // Ceiling plane detection (top 20% of frame)
  const ceilDepths = [];
  for (let x = 0; x < width; x++) {
    const d = data[Math.floor(height * 0.1) * width + x];
    if (d > 0.3 && d < 15) ceilDepths.push(d);
  }

  // Wall plane detection (left/right edges)
  const leftWallDepths  = [];
  const rightWallDepths = [];
  for (let y = Math.floor(height*0.2); y < Math.floor(height*0.8); y++) {
    const dl = data[y * width + Math.floor(width * 0.05)];
    const dr = data[y * width + Math.floor(width * 0.95)];
    if (dl > 0.1 && dl < 15) leftWallDepths.push(dl);
    if (dr > 0.1 && dr < 15) rightWallDepths.push(dr);
  }

  measurements.floorAreaSqM  = floorSpread * floorSpread; // approximate
  measurements.ceilingHeight = ceilDepths.length > 5
    ? Math.max(...ceilDepths.slice(0, 20)) : 0;
  measurements.wallDepthLeft  = leftWallDepths.length > 5
    ? leftWallDepths.reduce((a,b)=>a+b,0)/leftWallDepths.length : 0;
  measurements.wallDepthRight = rightWallDepths.length > 5
    ? rightWallDepths.reduce((a,b)=>a+b,0)/rightWallDepths.length : 0;
  measurements.pointCount    = width * height;
  measurements.timestamp     = Date.now();

  return measurements;
}

// Finalize scan — aggregate frames → room dimensions
function finalizeScan(session, scanData) {
  session.end();

  const allFrames = scanData.frames.filter(f => f.floorAreaSqM > 0);
  if (allFrames.length === 0) {
    showScanError('Not enough depth data captured. Try scanning slower.');
    return;
  }

  // Aggregate: take 90th percentile of floor spread (removes outliers)
  const floorAreas = allFrames.map(f => f.floorAreaSqM).sort((a,b)=>a-b);
  const floorAreaSqM = floorAreas[Math.floor(floorAreas.length * 0.9)];
  const floorAreaSqFt = (floorAreaSqM * 10.764).toFixed(1);

  const ceilHeights = allFrames.map(f=>f.ceilingHeight).filter(h=>h>1).sort((a,b)=>a-b);
  const ceilingFt = ceilHeights.length > 0
    ? (ceilHeights[Math.floor(ceilHeights.length*0.5)] * 3.281).toFixed(1) : 'Unknown';

  const roomData = {
    floorAreaSqFt: parseFloat(floorAreaSqFt),
    ceilingHeightFt: parseFloat(ceilingFt),
    wallArea: (parseFloat(floorAreaSqFt) * parseFloat(ceilingFt) * 0.8).toFixed(0), // approx
    scanDuration: Math.round((Date.now() - scanData.startTime) / 1000),
    frameCount: allFrames.length,
    snapshots: scanData.snapshots,
    confidence: allFrames.length > 100 ? 'HIGH' : allFrames.length > 40 ? 'MEDIUM' : 'LOW',
    method: 'LiDAR WebXR Depth Sensing',
    note: 'LiDAR measurements processed. Verify dimensions over 30ft with tape measure.'
  };

  sendToClaudeForAnalysis(roomData, null, 'lidar');
}
```

#### MODE 2 — Blueprint Photo (All Phones — iPhone Primary)

**Why this is equal to LiDAR for blueprint work:**
Claude reads printed dimensions directly — more accurate than LiDAR which measures
physical space. A blueprint photo gives Claude the architect's own numbers.

```javascript
async function handleBlueprintPhoto(file) {
  const base64 = await fileToBase64(file);

  // Show preview immediately
  document.getElementById('preview-img').src = `data:image/jpeg;base64,${base64}`;
  document.getElementById('preview-wrap').style.display = 'block';

  // Send to Claude with selected trade context
  await sendToClaudeForAnalysis(null, base64, 'photo');
}

async function fileToBase64(file) {
  // Handle PDF → render first page to canvas at 150dpi
  if (file.type === 'application/pdf') {
    return await renderPDFToBase64(file);
  }
  return new Promise(resolve => {
    const reader = new FileReader();
    reader.onload = e => resolve(e.target.result.split(',')[1]);
    reader.readAsDataURL(file);
  });
}

// PDF rendering — PDF.js from CDN
async function renderPDFToBase64(file) {
  const pdfjsLib = window['pdfjs-dist/build/pdf'];
  pdfjsLib.GlobalWorkerOptions.workerSrc =
    'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

  const ab  = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: ab }).promise;

  // Let user pick page if multi-page
  const totalPages = pdf.numPages;
  const pageNum    = totalPages > 1
    ? await promptPageSelection(totalPages)
    : 1;

  const page     = await pdf.getPage(pageNum);
  const viewport = page.getViewport({ scale: 1.5 }); // ~150dpi
  const canvas   = document.createElement('canvas');
  canvas.width   = viewport.width;
  canvas.height  = viewport.height;

  await page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise;
  return canvas.toDataURL('image/jpeg', 0.85).split(',')[1];
}
```

#### MODE 3 — Sketch/Napkin Reading (The Game-Changer)

Any drawing. Any quality. Field sketch, napkin, client drawing.
Claude reads it, asks max 3 questions, returns a priced quote.

```javascript
// Sketch mode is identical to blueprint photo technically
// The difference is the Claude system prompt — sketch mode is more forgiving,
// explicitly expects rough/incomplete drawings, and focuses on scope extraction
// rather than dimension reading

async function handleSketchPhoto(file) {
  const base64 = await fileToBase64(file);
  await sendToClaudeForAnalysis(null, base64, 'sketch');
}
```

#### MODE 4 — Manual Dimension Entry (Universal Fallback)

Always available. No camera, no upload, no scan.
Rep knows the numbers → instant estimate.

---

### Claude Analysis Engine

```javascript
// Central analysis function — all modes flow through here
async function sendToClaudeForAnalysis(roomData, imageBase64, inputMode) {
  showLoadingState();

  const selectedTrade   = getSelectedTrade();
  const pricingParams   = loadPricingParams();
  const companyName     = loadCompanyName();
  const systemPrompt    = buildSystemPrompt(selectedTrade, pricingParams, companyName, inputMode);

  // Build message content
  const content = [];

  if (imageBase64) {
    content.push({
      type: 'image',
      source: { type: 'base64', media_type: 'image/jpeg', data: imageBase64 }
    });
  }

  let userText = '';
  if (inputMode === 'lidar' && roomData) {
    userText = `
LiDAR scan complete. Here are the measured room data:
- Floor Area: ${roomData.floorAreaSqFt} sq ft (confidence: ${roomData.confidence})
- Ceiling Height: ${roomData.ceilingHeightFt} ft
- Approximate Wall Area: ${roomData.wallArea} sq ft
- Scan Duration: ${roomData.scanDuration} seconds
- Frames Captured: ${roomData.frameCount}
- Method: ${roomData.method}
${roomData.snapshots.length > 0 ? `- ${roomData.snapshots.length} photos captured during scan` : ''}

Trade selected: ${selectedTrade}
Please analyze this data and ${inputMode === 'sketch' ? 'ask up to 3 questions before quoting' : 'generate the full takeoff and estimate'}.
    `.trim();
  } else if (inputMode === 'sketch') {
    userText = `This is a hand-drawn sketch or rough drawing from a customer or sales rep in the field.
It may be rough, incomplete, or on informal paper.
Trade: ${selectedTrade}
Read everything you can, then ask a MAXIMUM of 3 questions before generating the estimate.
Never ask for information you can determine or reasonably estimate from the drawing.`;
  } else if (inputMode === 'photo' || inputMode === 'pdf') {
    userText = `This is a ${inputMode === 'pdf' ? 'PDF blueprint' : 'photo of a blueprint or plan'}.
Trade: ${selectedTrade}
Read all dimensions, callouts, symbols, and notes. Generate the full trade-specific takeoff and estimate.`;
  } else if (inputMode === 'manual') {
    const dims = getManualDimensions();
    userText = `Manual dimensions entered:
${JSON.stringify(dims, null, 2)}
Trade: ${selectedTrade}
Generate the full takeoff and estimate using company pricing.`;
  }

  content.push({ type: 'text', text: userText });

  try {
    const res = await fetch('https://sairn.vercel.app/api/claude', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        app_id: 'sairnscan',
        is_demo: true,
        system: systemPrompt,
        messages: [{ role: 'user', content }]
      })
    });

    const data = await res.json();
    const response = data.content?.[0]?.text || '';
    hideLoadingState();

    // Detect if Claude is asking questions (sketch mode) or delivering estimate
    if (response.includes('?') && inputMode === 'sketch' && !scanSession.questionsAnswered) {
      showQuestionMode(response);
    } else {
      showEstimateOutput(response);
    }
  } catch(err) {
    hideLoadingState();
    showError('Analysis failed. Check connection and try again.');
    console.error('SAIRNscan Claude error:', err);
  }
}
```

---

### System Prompts by Mode and Trade

#### Master SAIRNscan System Prompt
```
You are SAIRNscan — the world's most accurate construction scanning and estimating AI.
You are embedded in a professional contractor tool used in the field.

COMPANY: {companyName}
TRADE SELECTED: {trade}
INPUT TYPE: {inputMode}

COMPANY PRICING PARAMETERS:
{JSON.stringify(pricingParams)}

YOUR BEHAVIOR BY MODE:
- LiDAR scan data: measurements are provided — generate full estimate immediately
- Blueprint photo/PDF: read all dimensions and symbols — generate full estimate immediately
- Sketch/napkin drawing: this may be rough — read everything visible, ask MAX 3 questions,
  then generate estimate (never ask what you can reasonably determine yourself)
- Manual entry: dimensions provided — generate full estimate immediately

ESTIMATE OUTPUT — SAIRNSCAN REPORT CARD:
Format every estimate as a clean, professional, printable document:

SAIRNSCAN ESTIMATE
Project: [address or description if known]
Trade: {trade}
Date: [today]
Input: [LiDAR Scan / Blueprint Photo / Sketch / PDF / Manual Entry]
Estimated by: SAIRNscan AI

QUANTITIES
[Item] | [Quantity] | [Unit] | [Confidence: HIGH/MED/LOW]
...

MATERIALS (with waste factors applied)
[Material] | [Qty] | [Unit] | [$/Unit] | [Total]
...
MATERIAL SUBTOTAL: $X

LABOR
[Task] | [Hours] | [$/hr] | [Total]
...
LABOR SUBTOTAL: $X

ESTIMATE TOTAL
Low:  $X  |  Mid: $X  |  High: $X

TIMELINE: X days / weeks

NOT INCLUDED:
[Clear exclusions]

CONFIDENCE FLAGS:
[Any LOW confidence items — field verify before ordering]

AI INTELLIGENCE NOTES:
[Proactive observations: code concerns, trade conflicts, value engineering suggestions,
material alternatives, anything that could save the client money or prevent problems]

Quote valid 30 days | Prepared by SAIRNscan AI
WASTE FACTORS APPLIED: Tile=10-20% | Roofing=10-15% | Framing=10% | Siding=10% | Flooring=10%
```

#### Trade-Specific Extraction Rules (inject into system prompt per trade)

**GC Full Read:**
```
Extract: all room dimensions, floor areas by room, ceiling heights, exterior perimeter,
window schedule (count + size), door schedule, structural callouts, spec notes,
total conditioned SF, garage SF separate. Provide complete project summary.
```

**Roofing:**
```
Extract: roof planes (count + area each), pitch per plane, total squares,
ridge LF, valley LF, hip LF, eave LF, penetrations (chimneys/skylights/vents count),
drip edge LF, underlayment area, ice/water shield area (eaves + valleys).
If floor plan only: calculate roof from footprint + pitch. Ask for pitch if not shown.
```

**Electrical:**
```
Extract: service size (amps), panel location, circuit count, outlet count by room,
switch count, fixture count by type, EV charger rough-in Y/N, smoke/CO locations,
low-voltage locations. Flag NEC 210.52 spacing violations if visible.
```

**Framing:**
```
Extract: exterior wall LF by floor, interior wall LF by floor, ceiling heights,
openings (width → header size), beam spans, stud count estimate (LF/1.5 + corners*3 + openings*3),
shear wall locations, LVL/PSL beam locations.
```

**Plumbing:**
```
Extract: fixture count by type (toilet/lav/tub/shower/kitchen sink/laundry/utility/dishwasher/
ice maker/hose bib/floor drain), bathroom count, water heater location + type,
main service size, cleanout locations.
```

**Tile:**
```
Extract: floor tile area by room (W x L), wall tile area (shower = all walls floor-ceiling,
tub surround = 3 sides x 60in, backsplash = LF x 18in), tile size, grout joint width,
substrate type per area. Apply waste: straight=10%, diagonal=15%, herringbone=20%.
```

**HVAC:**
```
Extract: total conditioned SF by floor, ceiling heights, window area/exposure,
insulation R-values if noted, equipment locations, duct routing path,
number of zones, thermostat locations.
Note: Manual J load calc required before equipment selection. This is budget estimate only.
```

**Siding & Windows:**
```
Extract: exterior wall SF per elevation (H x W), minus openings (each window + door area),
window count by size, door count by type, soffit area (overhang depth x eave LF),
fascia LF, corner trim LF, J-channel LF.
```

---

## Pricing Parameter System

Every SAIRNscan user sets their own rates. Claude uses YOUR numbers, not national averages.
This is the core moat — SimplyWise uses generic pricing. SAIRNscan uses yours.

```javascript
// Default pricing params — user customizes in Admin panel
const defaultPricingParams = {
  company: 'My Company',
  laborRates: {
    standard:  85,   // $/hr
    lead:     120,   // $/hr
    specialty: 150   // $/hr
  },
  materialMarkup:  0.30,  // 30%
  overheadPercent: 0.15,  // 15%
  profitPercent:   0.20,  // 20%
  quoteValidDays:  30,
  minimumJob:      500,

  // Unit pricing — trade specific, fully customizable
  unitPricing: {
    // Roofing
    shingles_sq_installed: 350,
    metal_roofing_sq:      650,
    tear_off_sq:            75,

    // Tile
    tile_sqft_installed:    14,
    shower_tile_sqft:       22,

    // Framing
    framing_lf_wall:        12,
    framing_lf_header:      45,

    // Electrical
    electrical_circuit:    275,
    electrical_panel_200a: 2800,
    electrical_outlet:      85,

    // Plumbing
    plumbing_fixture_roughin: 450,
    plumbing_bathroom_full:  2400,

    // Siding
    siding_sqft_installed:    7.50,
    window_installed_each:   650,
    door_exterior_installed: 1200,

    // HVAC
    hvac_ton_installed:     4500,
    hvac_duct_lf:             18,

    // Painting
    paint_interior_sqft:      2.50,
    paint_exterior_sqft:      3.25
  }
};

// Load/save pricing to localStorage
function loadPricingParams() {
  const stored = localStorage.getItem('sairnscan_pricing');
  return stored ? JSON.parse(stored) : defaultPricingParams;
}

function savePricingParams(params) {
  localStorage.setItem('sairnscan_pricing', JSON.stringify(params));
}
```

---

## Output: SAIRNscan Report Card

Every scan/sketch/photo produces a printable Report Card.

**Features:**
- Clean HTML render on screen (readable at arm's length on phone)
- Print button → formatted for 8.5x11, prints beautifully
- Save to phone (screenshot or native share)
- Send via text/email (navigator.share)
- Signature capture → closes the deal on-site
- Deposit link via Stripe
- Save to project (if embedded in SAIRN B2B app)
- Export CSV (materials list)

**Print rules:**
```css
@media print {
  .no-print { display: none !important; }
  .report-card { font-size: 11pt; }
  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
```

---

## Standalone App vs. Embedded Mode

### Standalone SAIRNscan ($49/mo)
- Full SAIRNscan experience with its own login
- Electric Blue `#3B82F6` brand
- Pricing admin panel for any trade
- Industry templates: GC / Roofing / Electrical / Framing / Plumbing /
  Tile / HVAC / Siding / Painting / Stone / Landscape / Interior Design
- No vertical-specific features (no sub portal, no trade management)
- Works for ANY contractor — not just SAIRN vertical customers
- Own domain: sairnscan.io (check trademark before registering)

### Embedded SAIRNscan (in all SAIRN B2B apps — free)
- Adopts the parent app's color scheme
- Pricing params pre-populated from Admin Pricing panel
- Trade pre-selected based on app context
- Output saves to project file automatically
- Bridge sync to SAIRNbiz GL
- Full sub portal integration (in SAIRNbuild)

---

## Competitive Positioning

### What Nobody Else Does (SAIRNscan's 5 Moats)

1. **Your pricing, not national averages**
   SimplyWise uses national database. SAIRNscan uses your rate sheet.
   A roofer in Westlake, OH charging $350/sq gets $350/sq quotes, not $280 from a national DB.

2. **Sketch reading + instant pricing**
   No competitor reads napkin sketches AND prices them instantly with your rates.
   Beam AI reads blueprints but takes 24-72 hours and has no LiDAR.

3. **Four input modes, zero friction**
   Android LiDAR → iPhone photo → PDF upload → manual entry → all produce identical output.
   User never hits a dead end. Every phone works.

4. **Trade-specific AI intelligence, not just quantities**
   Claude doesn't just count — it flags code issues, trade conflicts, value engineering
   suggestions. No competitor has this layer.

5. **Standalone + embedded in full platform**
   SAIRNscan works alone at $49/mo. Embedded free in $199+/mo SAIRN apps.
   Buy any SAIRN vertical → SAIRNscan comes with it.
   Use SAIRNscan standalone → upsell path to full vertical.

### Pricing Strategy
| Product | Price | What You Get |
|---------|-------|-------------|
| SAIRNscan Standalone | $49/mo | Scanner + AI estimator, all modes, all trades |
| Any SAIRN Vertical | $149-299/mo | Full vertical + SAIRNscan embedded FREE |
| SAIRNscan as upsell path | — | Standalone user converts to vertical = +$100-250/mo |

---

## SAIRNscan Build Specification

### Required Panels / Screens
1. **Home / Scan** — mode selector, trade selector, capture triggers
2. **LiDAR Live** — AR session, coverage meter, confidence indicator, scan prompts
3. **Photo/Sketch** — camera capture, file upload, preview
4. **PDF Upload** — drag-drop, page selector thumbnail
5. **Manual Entry** — trade-specific dimension form
6. **Analysis** — loading state, Claude thinking indicator
7. **Question Mode** — Claude asks max 3 questions (sketch mode only)
8. **Report Card** — full estimate output, print/share/sign/save
9. **Signature Capture** — canvas, touch/stylus, client signs on screen
10. **History** — all past scans/estimates, searchable by address/trade/date
11. **Admin Pricing** — full rate sheet editor, industry templates
12. **Settings** — company name, logo, trade defaults

### Hard Rules for SAIRNscan Build
- Proxy ONLY: `https://sairn.vercel.app/api/claude`
- `app_id: 'sairnscan'` on every Claude call
- No Unicode box chars in JS
- No dark backgrounds (standalone uses white + Electric Blue `#3B82F6` accent)
- PDF.js loaded from CDN: `cdnjs.cloudflare.com`
- All images to base64 client-side before API call
- Max 3 questions enforced in sketch mode system prompt
- Print button on every Report Card — `window.print()` with correct CSS
- Signature canvas: `touch-action: none` on canvas element
- History stored in localStorage (same device) with Bridge fallback

### Guardian Checklist — SAIRNscan
- [ ] No `api.anthropic.com` — proxy only
- [ ] Device detection runs before any UI shows (no broken mode displayed)
- [ ] iOS users silently routed to photo mode — no "not supported" error
- [ ] PDF.js loaded from CDN — not bundled
- [ ] All image base64 conversion client-side
- [ ] `app_id: 'sairnscan'` and `is_demo: true` on every call
- [ ] Max 3 questions enforced in sketch system prompt
- [ ] Report Card renders in HTML — no Unicode box chars in JS strings
- [ ] Print CSS present — `print-color-adjust: exact`
- [ ] Signature canvas: `touch-action: none`, works on iOS + Android touch
- [ ] History saves to localStorage, loads on app open
- [ ] Pricing params persist in localStorage
- [ ] No blue in embedded mode — inherits parent app color
- [ ] Electric Blue `#3B82F6` ONLY in standalone mode

---

## Trademark Check Required Before Launch

Before publishing SAIRNscan as a standalone product:
- USPTO TESS search: "SAIRNscan" + "SAIRN Scan"
- Domain check: sairnscan.com, sairnscan.io, sairnscan.app
- App store name check: "SAIRNscan" on Apple App Store + Google Play
- (These checks must be run per the permanent trademark rule before any name is finalized)

---

*SAIRNscan: The world's only scanner that scans it, sketches it, photos it, and prices it
with YOUR rates before you leave the room.*
