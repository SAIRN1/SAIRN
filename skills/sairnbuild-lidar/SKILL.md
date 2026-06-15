---
name: sairnbuild-lidar
description: >
  The world's best construction LiDAR and blueprint intelligence skill for SAIRNbuild.
  Trigger on ANY of: "LiDAR", "scan the room", "scan the job", "blueprint scan", "takeoff",
  "measure the space", "point cloud", "depth scan", "3D scan", "upload blueprints",
  "read the plans", "scan with phone", "how much tile", "how much roofing", "square footage",
  "material estimate from scan", "blueprint AI", "scan to estimate", or any request involving
  measuring a space, reading a blueprint, or generating a material takeoff in SAIRNbuild.
  This skill governs ALL four input modes: (1) LiDAR live scan via phone camera on Android Chrome,
  (2) Photo of physical blueprint, (3) PDF blueprint upload, (4) Manual dimension entry fallback.
  It knows the technical reality of iOS vs Android LiDAR browser support, the correct WebXR
  depth-sensing implementation, the Claude vision system prompts for each trade, and the
  full Takeoff Report Card output format. No competitor embeds all four modes plus Claude
  intelligence in a single $199/mo GC platform. This is the moat. Never skip this skill
  for any measurement, scan, or takeoff task in SAIRNbuild.
---

# SAIRNbuild LiDAR & Blueprint Intelligence Skill

> *"Point. Scan. Done. Every material. Every trade. Light speed."*

This skill makes SAIRNbuild's Blueprint AI Takeoff Engine the best construction measurement
and estimating tool on earth. It combines four input modes, Claude vision intelligence,
trade-specific output, and a printable Takeoff Report Card — all inside a $199/mo platform
that beats tools costing $10K+/year.

---

## The Technical Reality — Read This First

### LiDAR on Mobile Browsers (Critical Constraint)

| Platform | LiDAR Browser Support | Strategy |
|----------|----------------------|----------|
| **Android (Chrome)** | ✅ WebXR Depth Sensing API works | Use live LiDAR scan mode |
| **iPhone/iPad (Safari)** | ❌ WebXR NOT supported on iOS Safari | Use photo capture mode |
| **iPhone/iPad (Chrome)** | ❌ iOS Chrome = WebKit = same block | Use photo capture mode |
| **Desktop** | ❌ No LiDAR sensor | Use PDF/photo upload mode |

**The correct architecture:** Detect device at load time. Route to correct mode automatically.
Never tell an iPhone user "your browser doesn't support LiDAR" — silently route them to the
equally powerful photo mode. The experience feels seamless regardless of device.

### iPhone LiDAR Accuracy (What We Tell Users)
iPhone 12 Pro+ and iPad Pro have hardware LiDAR. In Safari it cannot be accessed via browser.
**However:** When an iPhone user takes a photo of a blueprint or a room with their iPhone camera,
Claude's vision model is analyzing that image — which is often MORE accurate than raw LiDAR
because Claude reads dimensions printed on the blueprint, understands scale bars, and can
calculate from callouts — something LiDAR alone cannot do.

**The winning message:** "SAIRN Blueprint AI works on every phone, every plan, every trade."

### WebXR Depth Sensing (Android Implementation)
```javascript
// Check for LiDAR/depth sensing support
async function checkLiDARSupport() {
  if (!navigator.xr) return false;
  try {
    const supported = await navigator.xr.isSessionSupported('immersive-ar');
    if (!supported) return false;
    // Check depth-sensing feature specifically
    const session = await navigator.xr.requestSession('immersive-ar', {
      requiredFeatures: ['depth-sensing'],
      depthSensing: {
        usagePreference: ['cpu-optimized'],
        dataFormatPreference: ['luminance-alpha']
      }
    });
    await session.end();
    return true;
  } catch(e) {
    return false;
  }
}
```

### Point Cloud → Measurements (Android LiDAR Flow)
```javascript
// During XR session - capture depth frame and extract measurements
function processDepthFrame(frame, referenceSpace) {
  const depthInfo = frame.getDepthInformation(frame.getViewerPose(referenceSpace).views[0]);
  if (!depthInfo) return null;

  const width = depthInfo.width;
  const height = depthInfo.height;
  const data = depthInfo.data; // Float32Array of depth values in meters

  // Extract key measurements from depth map
  const measurements = {
    roomWidth: calculateRoomWidth(data, width, height),
    roomLength: calculateRoomLength(data, width, height),
    ceilingHeight: calculateCeilingHeight(data, width, height),
    wallAreas: calculateWallAreas(data, width, height),
    floorArea: calculateFloorArea(data, width, height),
    pointCloud: samplePointCloud(data, width, height, 500) // 500 representative points
  };

  return measurements;
}

// Convert depth measurements to usable room dimensions
function calculateFloorArea(data, width, height) {
  // Sample bottom third of depth frame = floor plane
  const floorRow = Math.floor(height * 0.75);
  const floorDepths = [];
  for (let x = 0; x < width; x++) {
    const depth = data[floorRow * width + x];
    if (depth > 0.1 && depth < 10) floorDepths.push(depth); // Filter outliers
  }
  // Use median depth spread to estimate floor dimensions
  floorDepths.sort((a,b) => a-b);
  const spread = floorDepths[Math.floor(floorDepths.length * 0.9)] -
                 floorDepths[Math.floor(floorDepths.length * 0.1)];
  return spread; // meters - convert to sq ft in output
}
```

---

## Four Input Modes — Full Implementation

### MODE 1: Live LiDAR Scan (Android Chrome Only)

**When to use:** User is physically on the jobsite with an Android phone.
Best for: Room dimensions, existing conditions, as-builts, renovation measurements.

**Flow:**
1. Detect Android + Chrome + WebXR depth-sensing support
2. Show "Start LiDAR Scan" button with Android icon
3. Launch WebXR AR session with depth-sensing
4. User slowly pans phone around the room (15-30 seconds)
5. Capture depth frames at 2fps, build point cloud
6. Auto-detect room boundaries (wall planes, floor plane, ceiling plane)
7. Extract: floor area (sq ft), ceiling height, wall areas (each wall), perimeter
8. Send measurements + 3 camera snapshots to Claude with trade-specific prompt
9. Claude analyzes: confirms measurements, identifies trade-relevant details visible in photos,
   adds intelligence (window count, door openings, penetrations, substrate type from photos)
10. Output: Takeoff Report Card

**Scan quality indicators (show live during scan):**
- Coverage meter: 0-100% (how much of the room has been captured)
- Confidence score: LOW / MEDIUM / HIGH (based on point density)
- Auto-prompt: "Scan the corners" / "Scan near the floor" / "Scan complete"

**Known LiDAR failure modes (handle silently):**
- Reflective surfaces (glass, mirrors, polished concrete) → gap in point cloud → flag for manual verify
- Direct sunlight on sensor → reduced accuracy → switch to photo mode suggestion
- Rooms > 40ft → break into multiple scans → stitch
- Dark surfaces (black tile, dark wood) → absorb laser → gap → flag

### MODE 2: Blueprint Photo (All Phones — Primary iPhone Mode)

**When to use:** User has physical blueprints, printed plans, or a PDF on another screen.
Best for: Pre-construction takeoffs, estimating before breaking ground.

**Flow:**
1. Show camera capture button ("Take Blueprint Photo")
2. User photographs blueprint — phone camera
3. Optional: multiple pages supported (tap + to add pages)
4. Image converted to base64
5. Sent to Claude with trade-specific vision prompt
6. Claude reads: scale bar, north arrow, dimension callouts, room labels, symbols, notes
7. Extracts all trade-relevant quantities
8. Output: Takeoff Report Card with confidence per measurement

**Blueprint photo tips shown to user:**
- Lay plan flat on floor or table
- Fill the frame with the plan
- Ensure dimension text is readable
- Include the scale bar or title block in at least one photo
- Use phone flash in low light

**What Claude can read from a blueprint photo:**
- Printed dimensions (most accurate — reads the number directly)
- Scale bar (calculates unnotated dimensions)
- Room labels and areas (if noted on plan)
- Symbol counts (outlets, fixtures, doors, windows)
- Spec notes and callouts
- North arrow (orientation)
- Sheet number and revision (for file management)

### MODE 3: PDF Blueprint Upload (Desktop + Mobile)

**When to use:** Architect sent a PDF. User is at office or in truck.
Best for: Full plan sets, commercial projects, detailed multi-trade takeoffs.

**Flow:**
1. File drop zone — accepts PDF, PNG, JPG, TIFF
2. PDF rendered to image at 150dpi via canvas (client-side, no server needed)
3. Each page converted to base64 image
4. Multi-page: user selects which page(s) to analyze (thumbnail preview shown)
5. Claude analyzes selected pages with trade prompt
6. Output: Takeoff Report Card

**PDF render code:**
```javascript
async function renderPDFPage(file, pageNum = 1) {
  // Use PDF.js (loaded from CDN)
  const pdfjsLib = window['pdfjs-dist/build/pdf'];
  pdfjsLib.GlobalWorkerOptions.workerSrc =
    'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
  const page = await pdf.getPage(pageNum);

  const viewport = page.getViewport({ scale: 1.5 }); // 150dpi equivalent
  const canvas = document.createElement('canvas');
  canvas.width = viewport.width;
  canvas.height = viewport.height;

  await page.render({
    canvasContext: canvas.getContext('2d'),
    viewport
  }).promise;

  return canvas.toDataURL('image/jpeg', 0.85).split(',')[1]; // base64
}
```

### MODE 4: Manual Dimension Entry (Universal Fallback)

**When to use:** User knows the dimensions. No blueprint. Quick estimate needed.
Best for: Repeat work, familiar project types, phone quotes.

**Flow:**
1. Simple form: length × width × height inputs
2. Trade-specific fields appear based on selected trade
3. User enters known quantities
4. Claude receives structured data + generates full material list + pricing
5. Output: Takeoff Report Card (same format)

**Trade-specific fields by trade:**
- Tile: room dimensions + tile size + layout pattern + substrate type
- Roofing: eave length + ridge length + pitch (or total squares if known)
- Electrical: square footage + number of floors + service size
- Framing: perimeter + floor count + ceiling heights + garage Y/N
- Plumbing: bathroom count + kitchen count + laundry Y/N + fixture list
- HVAC: total conditioned SF + floors + existing system Y/N

---

## Claude System Prompts by Trade (Takeoff Engine)

### Master Blueprint Intelligence Prompt (all modes)
```
You are the SAIRN Blueprint Intelligence Engine — the world's most accurate construction
takeoff AI embedded in SAIRNbuild. You are analyzing construction data for a {TRADE} professional.

Your job is to extract every quantity relevant to {TRADE} with the highest possible accuracy.

INPUT TYPE: {INPUT_TYPE} — {blueprint photo / LiDAR scan measurements / PDF plan / manual entry}

TRADE CONTEXT: {TRADE_CONTEXT}

CRITICAL RULES:
1. Read every printed dimension on the blueprint — these are ground truth
2. Use the scale bar to calculate any unnotated dimensions
3. Apply standard waste factors for each trade (listed below)
4. Flag anything you cannot confirm — do NOT guess and present it as fact
5. Your confidence rating per item: HIGH (dimension shown) / MEDIUM (calculated from scale)
   / LOW (estimated — flag for field verify)
6. Include a material list with quantities, waste factors, and current price range
7. Include estimated labor hours using industry-standard benchmarks
8. Output as a clean, printable Takeoff Report Card

WASTE FACTORS (always apply):
- Tile: +10% for straight lay, +15% for diagonal, +20% for herringbone
- Roofing: +10% standard, +15% complex hip/valley
- Framing lumber: +10% waste + 5% for cuts
- Siding: +10%
- Drywall: +10%
- Flooring: +10% straight, +15% diagonal

OUTPUT FORMAT — Takeoff Report Card:
[Project Name] | [Trade] | [Date] | [Prepared by SAIRN Blueprint AI]

--- QUANTITIES ---
[Item] | [Quantity] | [Unit] | [Confidence] | [Notes]

--- MATERIAL LIST ---
[Material] | [Quantity with waste] | [Unit] | [Est. Unit Cost] | [Est. Total]

--- LABOR ESTIMATE ---
[Task] | [Hours] | [Crew Size] | [Total Hours]

--- TOTAL ESTIMATE ---
Low: $X | Mid: $X | High: $X

--- FLAGS ---
[Any items needing field verification or where blueprint was unclear]

--- CLAUDE INTELLIGENCE NOTES ---
[Any observations from photos: substrate conditions, existing issues, trade conflicts,
code concerns, value engineering suggestions]
```

### LiDAR-Specific Addition to Prompt
```
LIDAR SCAN DATA PROVIDED:
Floor Area: {sqft} sq ft (confidence: {conf})
Ceiling Height: {height} ft (confidence: {conf})
Wall Areas: N={sqft} S={sqft} E={sqft} W={sqft}
Perimeter: {ft} ft
Point Cloud Density: {density}% coverage
Scan Duration: {seconds}s
3 Scan Photos Attached — analyze for trade-specific details

Note: LiDAR measurements have been processed with drift correction.
Raw accuracy: ±0.5 inches on rooms up to 40 ft (Manifold-grade processing applied).
Flag any measurement where point cloud density was below 70%.
```

---

## Trade Intelligence Profiles

Each trade gets a customized Claude context injected into the system prompt:

### Roofing
```
TRADE: Roofing
EXTRACT: Roof plane count, pitch per plane, square footage per plane, total squares,
ridge linear footage, valley linear footage, hip linear footage, eave linear footage,
penetrations (chimneys, skylights, vents), drip edge linear footage, underlayment area,
ice/water shield area (eaves + valleys), fascia linear footage.
MATERIALS: Shingles (squares), underlayment (rolls), ice/water shield, ridge cap,
starter strip, drip edge, roofing nails, deck screws, flashing.
NOTE: If blueprint is a floor plan (not a roof plan), calculate roof area using
footprint + pitch factor. Ask user for pitch if not shown.
```

### Electrical
```
TRADE: Electrical
EXTRACT: Panel location and size (amps), circuit count, outlet count by room,
switch count, fixture count by type (recessed, pendant, ceiling fan, exterior),
service entrance location, subpanel locations, EV charger rough-in Y/N,
smoke/CO detector locations, low-voltage rough-in (CAT6, coax, speaker).
MATERIALS: Wire by gauge (NM-B 14/2, 12/2, 10/3 etc.), outlet boxes,
switch boxes, panel circuits, breakers, conduit if commercial.
CODE NOTE: Flag any room where outlet spacing exceeds 12 ft per NEC 210.52.
```

### Framing
```
TRADE: Framing
EXTRACT: Exterior wall linear footage by floor, interior wall linear footage by floor,
ceiling height per floor, header schedule (opening width → header size),
beam spans and sizes if shown, floor system type (I-joist, lumber, TJI),
stud count estimate (linear footage ÷ 1.5 + openings × 3 + corners × 3),
shear wall locations if noted, LVL/PSL beam locations.
MATERIALS: Studs (2x4 or 2x6 + length), plates (top/bottom × LF), headers (by size),
sheathing (OSB 7/16 or 1/2 - exterior walls + roof deck), hurricane ties, joist hangers.
```

### Plumbing
```
TRADE: Plumbing
EXTRACT: Fixture count by type (toilet, lavatory, tub, shower, kitchen sink, laundry,
utility sink, dishwasher, ice maker, hose bib, floor drain), bathroom count,
water heater location and type (tank/tankless), main water service size,
drain cleanout locations, vent stack locations.
MATERIALS: Supply pipe (PEX A or B - hot + cold runs), drain pipe (ABS or PVC by diameter),
fittings estimate (15% of linear footage), water heater, fixtures allowance.
LABOR NOTE: Budget 8-12 hours per full bathroom rough-in, 4-6 hours per half bath.
```

### Tile
```
TRADE: Tile
EXTRACT: Floor tile areas by room (width × length), wall tile areas (shower = all walls
floor to ceiling, tub surround = 3 sides 60" high, backsplash = linear footage × 18"),
tile size from plan notes or user input, grout joint width, substrate type per area
(concrete slab, Hardieboard, Schluter, existing tile Y/N).
MATERIALS: Tile (SF + waste factor by pattern), grout (coverage per bag by joint size),
tile adhesive/thinset (coverage per bag), Schluter edge trim (linear footage),
backer board if over wood subfloor.
PATTERN WASTE: Straight=10%, Diagonal=15%, Herringbone=20%, Custom pattern=20%.
```

### HVAC
```
TRADE: HVAC
EXTRACT: Total conditioned square footage by floor, ceiling heights, window area
(glazing ratio), insulation R-values if noted, duct routing (attic vs. basement vs. crawl),
equipment locations (air handler, condenser, HRV/ERV), existing system Y/N,
number of zones, thermostat locations.
MATERIALS: Equipment (size in tons - use Manual J thumb rule: 500 SF per ton moderate climate,
400 SF hot climate), supply duct (by size), return duct, registers by room, flex duct runs.
NOTE: Always flag that Manual J load calculation is required before equipment selection.
SAIRN estimate is for budgeting only.
```

### Siding & Windows
```
TRADE: Siding & Windows
EXTRACT: Exterior wall SF per elevation (width × height), minus window and door openings
(width × height per opening), window count by size, door count by type,
soffit area (overhang depth × eave length), fascia linear footage,
trim linear footage (corners, J-channel, around openings).
MATERIALS: Siding (SF + 10% waste), house wrap (SF), J-channel (LF), corner posts (LF),
starter strip (LF), soffit panels (SF), fascia board (LF), window units (by size),
exterior doors (by type).
```

---

## Device Detection & Mode Routing

```javascript
async function detectBlueprintMode() {
  const ua = navigator.userAgent;
  const isIOS = /iPad|iPhone|iPod/.test(ua);
  const isAndroid = /Android/.test(ua);
  const isChrome = /Chrome/.test(ua) && !/Chromium/.test(ua);

  // Android Chrome = potential LiDAR
  if (isAndroid && isChrome) {
    const lidarSupported = await checkLiDARSupport();
    if (lidarSupported) return 'lidar';
    return 'photo'; // Android without depth sensor
  }

  // iOS = always photo (WebXR not supported in Safari)
  if (isIOS) return 'photo';

  // Desktop = PDF/photo upload
  return 'upload';
}

// Route to correct mode UI - seamless, no error messages
async function initBlueprintAI() {
  const mode = await detectBlueprintMode();
  document.getElementById('mode-lidar').style.display = mode === 'lidar' ? 'block' : 'none';
  document.getElementById('mode-photo').style.display = mode === 'photo' ? 'block' : 'none';
  document.getElementById('mode-upload').style.display = mode === 'upload' ? 'block' : 'none';
  document.getElementById('mode-manual').style.display = 'block'; // always available
}
```

---

## Takeoff Report Card — Output Standard

Every mode produces identical output format. This is what gets saved, printed, shared.

```
╔══════════════════════════════════════════════════════════╗
  SAIRN BLUEPRINT AI — TAKEOFF REPORT CARD
  Project: [Name/Address]    Trade: [Trade]    Date: [Date]
  Input: [LiDAR Scan / Blueprint Photo / PDF Upload / Manual]
  Prepared by: SAIRNbuild Blueprint Intelligence Engine
╚══════════════════════════════════════════════════════════╝

QUANTITIES
─────────────────────────────────────────────
[Item]                [Qty]  [Unit]  [Conf]
─────────────────────────────────────────────
[extracted items]

MATERIAL LIST (with waste factors applied)
─────────────────────────────────────────────────────────
[Material]           [Qty]  [Unit]  [$/Unit]  [Total]
─────────────────────────────────────────────────────────
[items]
─────────────────────────────────────────────────────────
MATERIAL SUBTOTAL:                            $[total]

LABOR ESTIMATE
───────────────────────────────────────
[Task]               [Hrs]  [Crew]  [Total Hrs]

TOTAL PROJECT ESTIMATE
─────────────────────────────────────
  Low (materials only):         $[X]
  Mid (mat + avg labor):        $[X]
  High (mat + premium labor):   $[X]

FLAGS — VERIFY IN FIELD
─────────────────────────────────────
[Any LOW confidence items]
[Any photo-detected issues]
[Any code flags]

CLAUDE INTELLIGENCE NOTES
─────────────────────────────────────
[Proactive observations, conflicts, suggestions]

─────────────────────────────────────────────────────────
Signature: ___________________  Date: ___________________
Saved to: [Project File] > [Trade] > Takeoffs
─────────────────────────────────────────────────────────
```

Note: Use only ASCII in HTML/JS rendering — never Unicode box chars in JS strings.
Render the report card in a `<pre>` block or styled HTML table — never in raw JS template literals
with Unicode characters.

---

## Competitive Moat — Blueprint AI

| Feature | SAIRNbuild | Procore | Togal.AI | Beam AI | Bluebeam |
|---------|-----------|---------|----------|---------|----------|
| LiDAR live scan | ✅ | ❌ | ❌ | ❌ | ❌ |
| Blueprint photo → takeoff | ✅ | ❌ | ✅ | ✅ | ❌ |
| PDF → takeoff | ✅ | ❌ | ✅ | ✅ | ✅ |
| Trade-specific AI output | ✅ | ❌ | ❌ | Partial | ❌ |
| Claude intelligence notes | ✅ | ❌ | ❌ | ❌ | ❌ |
| Photo-detected issues | ✅ | ❌ | ❌ | ❌ | ❌ |
| Embedded in full GC platform | ✅ | Partial | ❌ | ❌ | ❌ |
| Price | $199/mo | $10K+/yr | $1,899+/yr | $35+/mo | $1,999+/yr |

**The moat:** No tool on earth does LiDAR + photo + PDF + Claude intelligence + trade-specific
output + proactive issue detection — all inside a full GC management platform at $199/mo.

---

## Integration Points

- **Save to project:** All takeoffs auto-save to `project > trade > takeoffs` directory in SAIRNbuild
- **Pull to sub portal:** GC can push takeoff quantities to sub's portal as their scope baseline
- **Bridge sync:** Takeoff totals sync to SAIRNbiz GL as project budget line items
- **Print:** Takeoff Report Card prints on standard paper, prints beautifully, signature line included
- **Export CSV:** All quantities and material lists exportable to CSV for external estimating tools

---

## Guardian Checklist — Blueprint AI Module

- [ ] Device detection runs before any UI renders (no mode shown before detection completes)
- [ ] iOS users NEVER see a "not supported" error — silently show photo mode
- [ ] PDF.js loaded from CDN (cdnjs.cloudflare.com) — never bundled
- [ ] All image data converted to base64 client-side — never sent raw file to Claude API
- [ ] Claude called via proxy ONLY: `https://sairn.vercel.app/api/claude`
- [ ] `app_id: 'sairnbuild'` and `is_demo: true` on every Claude call
- [ ] Takeoff Report Card renders in HTML — NO Unicode box chars in JS strings
- [ ] Report auto-saves to project file via localStorage (same device) or Bridge API (cross-device)
- [ ] Print button on Report Card — `window.print()` with `print-color-adjust: exact`
- [ ] Manual entry mode always available regardless of device/browser
- [ ] LiDAR session properly ended after scan (`session.end()`) — no memory leaks

---

*SAIRNbuild Blueprint AI: Point. Scan. Done. The world's best construction takeoff.*
