# StoneDesk — Raised Bar (Overhang) Section Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a rep attach one real, priced, true-to-scale raised-bar overhang section to a horizontal front edge of any preset shape (straight, L-shape, U-shape, Island, Galley, "custom" preset), with a real fabrication cut sheet line and a corbel-support disclosure.

**Architecture:** Pure client-side addition to `stonedesk.html`. A single nullable `dcRaisedBar` object, namespaced by `<ctShape>:<edge label>`, drives three subsystems: `drawCTPreview()`'s per-shape rendering (a shared, purely-additive rect-drawing helper — no existing shape's fill or stroke calls are modified, unlike chamfer), `calcDrawing()` → `dcSyncLiveToQuoteEngine()` → `calc()`'s pricing pipeline (same proven pattern as seams/chamfer), and `printDrawCutSheet()`'s printed output.

**Tech Stack:** Vanilla JS, HTML5 Canvas 2D. No dependencies added.

## Global Constraints

- `node --check` must pass on every touched script block before any commit — run `python tools/checkblocks.py stonedesk.html` and confirm `FAILED_BLOCKS:0` (baseline before this plan: `TOTAL_BLOCKS:128`, `FAILED_BLOCKS:0`).
- Never bulk find-replace. Every edit below is a targeted, unique-context change.
- One raised bar per drawing, horizontal front edges only. Vertical front edges (L-shape's `B-Front`, U-shape's `Left front`/`Right front`) and freehand Custom Draw mode (`dcMode==='draw'`) are explicitly out of scope — do not add support for either.
- No existing `colorEdge()` call, fill call, or `window._ctRects` entry may be modified by this feature — the bar is purely additive (a new adjacent rect + 3 new edges), unlike chamfer which had to replace fills. If any task's diff touches a pre-existing line in `drawCTPreview()` outside the exact insertion points this plan specifies, stop and reconsider — that is a sign of scope drift, not a required change.
- Every consumer (rendering, pricing, cut sheet) MUST filter `dcRaisedBar` by `edgeKey.indexOf(ctShape + ':') === 0` before treating it as active — this is the exact Critical bug class chamfer's final review had to catch after the fact (`dcChamferActiveKeys()`); build it in correctly from the start here, in every task that reads `dcRaisedBar`, not just once.
- Length and offset are clamped to the edge's real current length at both input time and render time — clamp, never silently produce a bar hanging off the end of its run or corrupt the geometry.
- Zero/blank length or overhang depth = no bar (same as never having set one), never a degenerate zero-area bar.
- Pricing edge-LF is single-sided (no ×2 multiplier) — these are ordinary perimeter edges, not interior double-faced cuts like seams/chamfers.
- Toggling the bar off (or switching to a shape/edge it isn't on) must zero its cost contribution the same tick, via `calcDrawing()`'s existing re-fire-on-any-edit path.
- Corbel-support threshold default is 15in (quartz), admin-configurable, disclosed as material-specific — never presented as a universal number.

---

## File Structure

Single file touched: `stonedesk.html`. No new files.

| Region (function) | Responsibility for this feature |
|---|---|
| ~L10163 (`var DC_SEAM_EDGE_COST`) | New `var DC_BAR_EDGE_COST = 0;`. |
| ~L3893 (HTML, Waterfall card) | New "Raised Bar" card: edge-picker dropdown + 4 number inputs. |
| ~L11259 (`selectDrawShape`) | New `buildRaisedBarArea();` call alongside the existing `buildEdgeAssignmentArea();` call. |
| ~L11321 (chamfer data model region) | New `dcRaisedBar`, `DC_BAR_EDGE_CANDIDATES`, `dcRaisedBarEdgeLenIn()`, `buildRaisedBarArea()`. |
| ~L11609–11832 (`drawCTPreview`, all shape branches) | New nested `dcDrawRaisedBarIfActive()` helper + one call site per shape/section. |
| ~L11008 (`dcClearPoly`) | Reset `dcRaisedBar = null` alongside the existing chamfer/cutout/seam reset. |
| ~L13086 (`dcChamferPricingSummary` region) | New `dcRaisedBarPricingSummary()`. |
| ~L13144 (`calcDrawing`) | Compute bar sqft/edge cost, fold into `totalMat`, add its results-panel metric card, pass edge cost to `dcSyncLiveToQuoteEngine()`. |
| ~L13280 (`dcSyncLiveToQuoteEngine`) | Accept `barEdgeCost` param, assign `DC_BAR_EDGE_COST`. |
| ~L9895 (`calc`) | Read `DC_BAR_EDGE_COST`, add to `rawSubtotal`, `lastCalc`, `lines[]`. |
| ~L13363 (`printDrawCutSheet`) | New "Raised Bar" row + `totalMat` fold-in. |
| ~L14470 (admin Unit Pricing form) | New `sairn-unit-corbel_threshold` field. |

Line numbers are as of this plan's base commit and will drift by a few lines as earlier tasks land — every edit below is anchored to unique surrounding code, not the raw number.

---

### Task 1: Data model, edge-candidate map, clamp helpers, UI card + wiring

**Files:**
- Modify: `stonedesk.html` (five locations, all within the app's single main `<script>` block, plus one HTML insertion)

**Interfaces:**
- Produces: `var dcRaisedBar` (`null | {edgeKey, lengthIn, offsetIn, overhangDepthIn, heightIn}`), `var DC_BAR_EDGE_CANDIDATES` (`{[ctShape]: [{label, lenField}]}`), `function dcRaisedBarEdgeLenIn(edgeKey)`, `function buildRaisedBarArea()` — all consumed by Tasks 2–6.
- Consumes: existing globals `gN(id)`, `showToast(msg)`, `ctShape`, `drawCTPreview()`, `calcDrawing()`.

- [ ] **Step 1: Add the "Raised Bar" HTML card**

Find (around line 3893):

```html
        <!-- Waterfall -->
        <div class="dm-card">
          <div class="dm-card-title">Waterfall Ends</div>
          <div class="dm-cb-row"><input type="checkbox" id="dh-wf-left"><label for="dh-wf-left">Left waterfall end</label></div>
          <div class="dm-cb-row"><input type="checkbox" id="dh-wf-right"><label for="dh-wf-right">Right waterfall end</label></div>
          <div class="dm-field" style="margin-top:6px"><label>Waterfall panel height (in)</label><input type="number" id="dh-wf-ht" placeholder="e.g. 36 for island height"></div>
          <div style="font-size:10px;color:var(--muted);margin-top:6px;line-height:1.5">Waterfall ends are marked in red on the drawing preview. Each waterfall panel is a full slab height cut — typically 36in of stone per leg.</div>
        </div>

        <!-- Notes -->
```

Replace with:

```html
        <!-- Waterfall -->
        <div class="dm-card">
          <div class="dm-card-title">Waterfall Ends</div>
          <div class="dm-cb-row"><input type="checkbox" id="dh-wf-left"><label for="dh-wf-left">Left waterfall end</label></div>
          <div class="dm-cb-row"><input type="checkbox" id="dh-wf-right"><label for="dh-wf-right">Right waterfall end</label></div>
          <div class="dm-field" style="margin-top:6px"><label>Waterfall panel height (in)</label><input type="number" id="dh-wf-ht" placeholder="e.g. 36 for island height"></div>
          <div style="font-size:10px;color:var(--muted);margin-top:6px;line-height:1.5">Waterfall ends are marked in red on the drawing preview. Each waterfall panel is a full slab height cut — typically 36in of stone per leg.</div>
        </div>

        <!-- Raised Bar -->
        <div class="dm-card">
          <div class="dm-card-title">Raised Bar (Overhang)</div>
          <div class="dm-field">
            <label>Attach to edge</label>
            <select id="db-bar-edge" style="width:100%;background:rgba(255,255,255,0.04);border:1px solid var(--border);border-radius:6px;padding:7px 8px;color:var(--text);font-size:12px;font-family:Outfit,sans-serif;outline:none">
              <option value="">No raised bar</option>
            </select>
          </div>
          <div class="dm-field"><label>Bar length (in)</label><input type="number" id="db-bar-len" placeholder="e.g. 48"></div>
          <div class="dm-field"><label>Offset from left end (in)</label><input type="number" id="db-bar-offset" placeholder="e.g. 12"></div>
          <div class="dm-field"><label>Overhang depth (in)</label><input type="number" id="db-bar-depth" placeholder="e.g. 12"></div>
          <div class="dm-field"><label>Bar height (in)</label><input type="number" id="db-bar-height" placeholder="e.g. 42" value="42"></div>
          <div style="font-size:10px;color:var(--muted);margin-top:6px;line-height:1.5">A stepped-up overhang section for stool seating. Adds real sqft and finished edge to the quote. Overhang depths beyond the corbel-support threshold (Admin → Unit Pricing) are flagged, not blocked.</div>
        </div>

        <!-- Notes -->
```

- [ ] **Step 2: Add the data model, edge-candidate map, and helpers**

Find (around line 10163, right after `var DC_SEAM_EDGE_COST = 0;`):

```js
var DC_SEAM_EDGE_COST = 0;
```

Replace with:

```js
var DC_SEAM_EDGE_COST = 0;
// Raised bar (overhang) edge cost, synced from dcRaisedBar via dcSyncLiveToQuoteEngine() --
// same disconnect-bug-avoidance pattern as DC_SEAM_EDGE_COST/DC_CHAMFER_EDGE_COST.
var DC_BAR_EDGE_COST = 0;
```

Find (around line 11321, right before the chamfer data model comment block — `// Chamfered corners (2026-08-12): ...`):

```js
// Chamfered corners (2026-08-12): preset-shape inside-corner 45deg chamfers, keyed by
```

Replace with:

```js
// Raised bar / overhang section (2026-08-12): one real, priced, true-to-scale bar-height
// overhang attachable to any preset shape's HORIZONTAL front edges only (vertical fronts like
// L-shape's B-Front or U-shape's Left/Right front are out of scope this pass -- named
// limitation, same precedent as chamfer excluding Custom Draw). Namespaced by
// '<ctShape>:<edge label>' for the exact same reason dcChamferedCorners is namespaced by shape:
// chamfer's own final review found a real Critical bug from NOT filtering stale cross-shape
// state on the read side -- every consumer of dcRaisedBar below filters on this from the start.
var dcRaisedBar = null; // or { edgeKey, lengthIn, offsetIn, overhangDepthIn, heightIn }

// Every shape's real horizontal front edge(s), traced directly from drawCTPreview() (not
// assumed) -- the single source of truth for the edge-picker dropdown, the pricing/cut-sheet
// length lookup, and (Tasks 2-4) the render call sites. galley/custom share this same shape of
// entry (multiple candidate sections), matching their shared dynamic-loop renderer.
var DC_BAR_EDGE_CANDIDATES = {
  straight: [{ label: 'Front (exposed)', lenField: 'da-len' }],
  island:   [{ label: 'Front (exposed)', lenField: 'da-len' }],
  lshape:   [{ label: 'A-Front', lenField: 'da-len' }],
  ushape:   [{ label: 'Back front', lenField: 'db-len' }],
  galley:   [{ label: 'Front counter front', lenField: 'da-len' }, { label: 'Back counter front', lenField: 'db-len' }],
  custom:   [{ label: 'Section A front', lenField: 'da-len' }, { label: 'Section B front', lenField: 'db-len' }, { label: 'Section C front', lenField: 'dc-len' }],
};

// Real current length (inches) of the edge dcRaisedBar.edgeKey names, read live from the same
// dimension inputs drawCTPreview uses -- the single place this shape+edge-to-field mapping is
// expressed (DC_BAR_EDGE_CANDIDATES), consumed identically by the UI clamp, the render-time
// re-clamp, and pricing/cut-sheet, so none of them can drift out of sync with each other.
function dcRaisedBarEdgeLenIn(edgeKey) {
  if (!edgeKey) return 0;
  var sep = edgeKey.indexOf(':');
  if (sep < 0) return 0;
  var shape = edgeKey.slice(0, sep), label = edgeKey.slice(sep + 1);
  var candidates = DC_BAR_EDGE_CANDIDATES[shape] || [];
  for (var i = 0; i < candidates.length; i++) {
    if (candidates[i].label === label) return gN(candidates[i].lenField);
  }
  return 0;
}

// Builds/refreshes the "Attach to edge" dropdown for the CURRENT ctShape and syncs the four
// number inputs to dcRaisedBar's stored state (or blanks them if inactive/on a different
// shape) -- called from selectDrawShape() every time the shape changes, mirroring
// buildEdgeAssignmentArea()'s own rebuild-on-shape-select pattern.
function buildRaisedBarArea() {
  var sel = document.getElementById('db-bar-edge');
  if (!sel) return;
  var candidates = DC_BAR_EDGE_CANDIDATES[ctShape] || [];
  sel.innerHTML = '';
  var noneOpt = document.createElement('option');
  noneOpt.value = ''; noneOpt.textContent = 'No raised bar';
  sel.appendChild(noneOpt);
  candidates.forEach(function (c) {
    var o = document.createElement('option');
    o.value = ctShape + ':' + c.label;
    o.textContent = c.label;
    sel.appendChild(o);
  });
  var active = (dcRaisedBar && dcRaisedBar.edgeKey.indexOf(ctShape + ':') === 0) ? dcRaisedBar : null;
  sel.value = active ? active.edgeKey : '';

  var lenIn = document.getElementById('db-bar-len');
  var offIn = document.getElementById('db-bar-offset');
  var depIn = document.getElementById('db-bar-depth');
  var htIn = document.getElementById('db-bar-height');
  if (lenIn) lenIn.value = active ? active.lengthIn : '';
  if (offIn) offIn.value = active ? active.offsetIn : '';
  if (depIn) depIn.value = active ? active.overhangDepthIn : '';
  if (htIn) htIn.value = active ? active.heightIn : 42;

  function applyFromInputs() {
    var edgeKey = sel.value;
    if (!edgeKey) {
      dcRaisedBar = null;
      drawCTPreview();
      if (typeof calcDrawing === 'function') calcDrawing();
      return;
    }
    var lengthIn = parseFloat(lenIn.value) || 0;
    var overhangDepthIn = parseFloat(depIn.value) || 0;
    var heightIn = parseFloat(htIn.value) || 42;
    var offsetIn = parseFloat(offIn.value) || 0;
    if (!(lengthIn > 0) || !(overhangDepthIn > 0)) {
      dcRaisedBar = null;
      drawCTPreview();
      if (typeof calcDrawing === 'function') calcDrawing();
      return;
    }
    var edgeLenIn = dcRaisedBarEdgeLenIn(edgeKey);
    var clampedLen = edgeLenIn > 0 ? Math.min(lengthIn, edgeLenIn) : lengthIn;
    var maxOffset = Math.max(edgeLenIn - clampedLen, 0);
    var clampedOffset = Math.min(Math.max(offsetIn, 0), maxOffset);
    if ((clampedLen !== lengthIn || clampedOffset !== offsetIn) && typeof showToast === 'function') {
      showToast('Bar length/position clamped to fit the ' + edgeLenIn.toFixed(1) + 'in edge');
    }
    dcRaisedBar = { edgeKey: edgeKey, lengthIn: clampedLen, offsetIn: clampedOffset, overhangDepthIn: overhangDepthIn, heightIn: heightIn };
    lenIn.value = clampedLen;
    offIn.value = clampedOffset;
    drawCTPreview();
    if (typeof calcDrawing === 'function') calcDrawing();
  }
  sel.onchange = applyFromInputs;
  [lenIn, offIn, depIn, htIn].forEach(function (el) { if (el) el.oninput = applyFromInputs; });
}

// Chamfered corners (2026-08-12): preset-shape inside-corner 45deg chamfers, keyed by
```

- [ ] **Step 3: Call `buildRaisedBarArea()` from `selectDrawShape()`**

Find (around line 11312):

```js
  buildEdgeAssignmentArea();
  // Switching presets invalidates any in-progress or completed hand-drawn polygon from a
```

Replace with:

```js
  buildEdgeAssignmentArea();
  buildRaisedBarArea();
  // Switching presets invalidates any in-progress or completed hand-drawn polygon from a
```

- [ ] **Step 4: Reset `dcRaisedBar` alongside the fresh-draw reset**

Find (around line 11009):

```js
  dcCutouts = []; dcSeams = []; dcChamferedCorners = {};
```

Replace with:

```js
  dcCutouts = []; dcSeams = []; dcChamferedCorners = {}; dcRaisedBar = null;
```

- [ ] **Step 5: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `TOTAL_BLOCKS:128` (or current count), `FAILED_BLOCKS:0`

- [ ] **Step 6: Manual verification (browser console)**

Open `stonedesk.html`, log in past the PIN/trial gate, open the Drawing Tool, select the `straight` preset, then in devtools console:

```js
document.getElementById('db-bar-edge').value = 'straight:Front (exposed)';
document.getElementById('db-bar-len').value = 48;
document.getElementById('db-bar-depth').value = 12;
document.getElementById('db-bar-edge').dispatchEvent(new Event('change'));
dcRaisedBar; // -> { edgeKey:'straight:Front (exposed)', lengthIn:48, offsetIn:0, overhangDepthIn:12, heightIn:42 }
document.getElementById('db-bar-len').value = 9999;
document.getElementById('db-bar-len').dispatchEvent(new Event('input'));
dcRaisedBar.lengthIn; // -> clamped to da-len's current value (96 by default), a toast should have appeared
document.getElementById('db-bar-edge').value = '';
document.getElementById('db-bar-edge').dispatchEvent(new Event('change'));
dcRaisedBar; // -> null
```

Expected: matches the comments above at each line.

- [ ] **Step 7: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- raised bar data model, edge-candidate map, clamp helpers, UI card"
```

---

### Task 2: Rendering — straight/island and L-shape

**Files:**
- Modify: `stonedesk.html` (`drawCTPreview()`, straight/island branch and L-shape branch, ~L11609–11726)

**Interfaces:**
- Produces: `dcDrawRaisedBarIfActive(edgeKey, rectX, rectY, rectW, rectH, sc, edgeLenIn)`, a function nested inside `drawCTPreview()` (alongside `drawRect`/`colorEdge`/`dimLabel`/`ea`), consumed by every shape branch in Tasks 2–4.
- Consumes: `dcRaisedBar`, `DC_BAR_EDGE_CANDIDATES` (Task 1), the nested `colorEdge()`/`ctx` already in scope inside `drawCTPreview()`.

- [ ] **Step 1: Add the shared `dcDrawRaisedBarIfActive()` helper**

Find (around line 11602, right after the nested `ea()` function definition):

```js
  function ea(label, fallback) {
    return edgeAssignments[label] || fallback;
  }

  // Reset the placeable-rect registry used for sink/cutout click-placement + drag hit-testing
```

Replace with:

```js
  function ea(label, fallback) {
    return edgeAssignments[label] || fallback;
  }

  // Raised bar (2026-08-12): purely additive, unlike chamfer -- draws a second, separate filled
  // rect sharing one edge with the base shape/section's own rect, using the identical fill style,
  // so two adjacent same-alpha fills with no gap read as one continuous piece. Zero need to touch
  // any existing shape's fill call. Called once per candidate edge, after that edge's own
  // rect/fill/strokes are already drawn. edgeKey must match dcRaisedBar.edgeKey EXACTLY (already
  // shape-namespaced) or this is a no-op -- the caller doesn't need its own active/shape check.
  function dcDrawRaisedBarIfActive(edgeKey, rectX, rectY, rectW, rectH, sc, edgeLenIn) {
    if (!dcRaisedBar || dcRaisedBar.edgeKey !== edgeKey) return;
    var effLenIn = edgeLenIn > 0 ? Math.min(dcRaisedBar.lengthIn, edgeLenIn) : dcRaisedBar.lengthIn;
    var maxOffsetIn = Math.max(edgeLenIn - effLenIn, 0);
    var effOffsetIn = Math.min(Math.max(dcRaisedBar.offsetIn, 0), maxOffsetIn);
    if (!(effLenIn > 0)) return;
    var offsetPx = effOffsetIn * sc, lengthPx = effLenIn * sc, depthPx = dcRaisedBar.overhangDepthIn * sc;
    var barX = rectX + offsetPx, barY = rectY + rectH;
    ctx.fillStyle = 'rgba(232,133,10,0.1)';
    ctx.beginPath(); ctx.rect(barX, barY, lengthPx, depthPx); ctx.fill();
    colorEdge(barX, barY + depthPx, barX + lengthPx, barY + depthPx, 'polished');
    colorEdge(barX, barY, barX, barY + depthPx, 'polished');
    colorEdge(barX + lengthPx, barY, barX + lengthPx, barY + depthPx, 'polished');
  }

  // Reset the placeable-rect registry used for sink/cutout click-placement + drag hit-testing
```

- [ ] **Step 2: Call it from the straight/island branch**

Find (around line 11622):

```js
    window._ctRects.push({key:'A', x:x, y:y, w:aL*sc, h:aD*sc});
    // waterfall indicators
```

Replace with:

```js
    window._ctRects.push({key:'A', x:x, y:y, w:aL*sc, h:aD*sc});
    dcDrawRaisedBarIfActive(ctShape+':Front (exposed)', x, y, aL*sc, aD*sc, sc, aL);
    // waterfall indicators
```

- [ ] **Step 3: Call it from the L-shape branch**

Find (around line 11685):

```js
    window._ctRects.push({key:'A', x:ax, y:ay, w:aw, h:ah});
    if (hasStub) window._ctRects.push({key:'B', x:bx, y:by, w:bw, h:bh});
```

Replace with:

```js
    window._ctRects.push({key:'A', x:ax, y:ay, w:aw, h:ah});
    if (hasStub) window._ctRects.push({key:'B', x:bx, y:by, w:bw, h:bh});
    dcDrawRaisedBarIfActive('lshape:A-Front', ax, ay, aw, ah, sc, aL);
```

- [ ] **Step 4: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 5: Manual verification (browser console)**

On the `straight` preset (default 96in Length, 25.5in Depth):

```js
document.getElementById('db-bar-edge').value = 'straight:Front (exposed)';
document.getElementById('db-bar-len').value = 48;
document.getElementById('db-bar-offset').value = 24;
document.getElementById('db-bar-depth').value = 12;
document.getElementById('db-bar-edge').dispatchEvent(new Event('change'));
drawCTPreview();
```

Expected: the canvas visibly shows a second, adjacent filled rectangle extending below (in front of) the main counter rect, spanning roughly the middle third of the front edge, with three new polished-edge (green) strokes outlining it — no visible gap or seam between the base rect and the bar. Confirm by eye or screenshot. Repeat on the `lshape` preset with edge `lshape:A-Front` — same visual result on A's front edge, B's stub unaffected.

- [ ] **Step 6: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- raised bar rendering, straight/island and L-shape"
```

---

### Task 3: Rendering — U-shape

**Files:**
- Modify: `stonedesk.html` (`drawCTPreview()`, U-shape branch, ~L11780)

**Interfaces:**
- Consumes: `dcDrawRaisedBarIfActive()` (Task 2), `dcRaisedBar`, `DC_BAR_EDGE_CANDIDATES` (Task 1).

- [ ] **Step 1: Call `dcDrawRaisedBarIfActive()` from the U-shape branch**

Find (around line 11782):

```js
    window._ctRects.push({key:'Back', x:bx, y:by, w:backW, h:backH});
    window._ctRects.push({key:'Left', x:lx, y:ly, w:leftW, h:leftH});
    window._ctRects.push({key:'Right', x:rx, y:ry, w:rightW, h:rightH});
    // Outline as one continuous polygon (clockwise from top-left, around the U, back to start)
```

Replace with:

```js
    window._ctRects.push({key:'Back', x:bx, y:by, w:backW, h:backH});
    window._ctRects.push({key:'Left', x:lx, y:ly, w:leftW, h:leftH});
    window._ctRects.push({key:'Right', x:rx, y:ry, w:rightW, h:rightH});
    // Raised bar attaches to the Back run's own rect (bx,by,backW,backH) -- its front edge is
    // "Back front" (the nominal, un-chamfered full span from lx+leftW to rx), independent of
    // whether either inside corner is currently chamfered; the two features don't interact.
    dcDrawRaisedBarIfActive('ushape:Back front', lx+leftW, by, backFrontPx, backH, sc, bL);
    // Outline as one continuous polygon (clockwise from top-left, around the U, back to start)
```

- [ ] **Step 2: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 3: Manual verification (browser console)**

On the `ushape` preset (default Left 72in/25.5in, Back 84in/25.5in, Right 72in/25.5in):

```js
document.getElementById('db-bar-edge').value = 'ushape:Back front';
document.getElementById('db-bar-len').value = 40;
document.getElementById('db-bar-depth').value = 12;
document.getElementById('db-bar-edge').dispatchEvent(new Event('change'));
drawCTPreview();
```

Expected: a bar rectangle extends downward from the Back run's front edge (between the two legs), same visual treatment as Task 2's shapes. Switch to `lshape` — confirm the bar disappears (namespaced key no longer matches `ctShape`). Switch back to `ushape` — confirm it reappears with the same values.

- [ ] **Step 4: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- raised bar rendering, U-shape"
```

---

### Task 4: Rendering — Galley and "custom" preset (dynamic section loop)

**Files:**
- Modify: `stonedesk.html` (`drawCTPreview()`, galley/custom branch, ~L11811–11832)

**Interfaces:**
- Consumes: `dcDrawRaisedBarIfActive()` (Task 2), `dcRaisedBar`, `DC_BAR_EDGE_CANDIDATES` (Task 1).

- [ ] **Step 1: Call `dcDrawRaisedBarIfActive()` inside the `secs.forEach` loop**

Find (around line 11823):

```js
    secs.forEach(s=>{
      const [sl,sd]=s.dims;
      const frontColor = ea(s.lbl.front,'polished'), backColor = ea(s.lbl.back,'wall');
      ctx.fillStyle='rgba(232,133,10,0.1)'; ctx.beginPath(); ctx.rect(pad,cy,sl*sc,sd*sc); ctx.fill();
      colorEdge(pad,cy,pad+sl*sc,cy,backColor); colorEdge(pad,cy+sd*sc,pad+sl*sc,cy+sd*sc,frontColor);
      colorEdge(pad,cy,pad,cy+sd*sc,backColor); colorEdge(pad+sl*sc,cy,pad+sl*sc,cy+sd*sc,ea('Left end','wall'));
      window._ctRects.push({key:s.lbl.front||('Section'+window._ctRects.length), x:pad, y:cy, w:sl*sc, h:sd*sc});
      cy+=sd*sc+8;
    });
```

Replace with:

```js
    secs.forEach(s=>{
      const [sl,sd]=s.dims;
      const frontColor = ea(s.lbl.front,'polished'), backColor = ea(s.lbl.back,'wall');
      ctx.fillStyle='rgba(232,133,10,0.1)'; ctx.beginPath(); ctx.rect(pad,cy,sl*sc,sd*sc); ctx.fill();
      colorEdge(pad,cy,pad+sl*sc,cy,backColor); colorEdge(pad,cy+sd*sc,pad+sl*sc,cy+sd*sc,frontColor);
      colorEdge(pad,cy,pad,cy+sd*sc,backColor); colorEdge(pad+sl*sc,cy,pad+sl*sc,cy+sd*sc,ea('Left end','wall'));
      window._ctRects.push({key:s.lbl.front||('Section'+window._ctRects.length), x:pad, y:cy, w:sl*sc, h:sd*sc});
      if (s.lbl.front) dcDrawRaisedBarIfActive(ctShape+':'+s.lbl.front, pad, cy, sl*sc, sd*sc, sc, sl);
      cy+=sd*sc+8;
    });
```

- [ ] **Step 2: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 3: Manual verification (browser console)**

On the `galley` preset (default Front Counter 96in/25.5in, Back Counter 84in/25.5in):

```js
document.getElementById('db-bar-edge').value = 'galley:Front counter front';
document.getElementById('db-bar-len').value = 40;
document.getElementById('db-bar-depth').value = 12;
document.getElementById('db-bar-edge').dispatchEvent(new Event('change'));
drawCTPreview();
```

Expected: a bar extends below the Front Counter section only, Back Counter unaffected. Switch the dropdown to `galley:Back counter front` with the same length/depth — confirm the bar now shows on the Back Counter section instead, and the Front Counter reverts to plain. Repeat once on the `custom` preset with `custom:Section B front` to confirm the shared loop code also works for a middle section, not just the first.

- [ ] **Step 4: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- raised bar rendering, Galley and custom preset sections"
```

---

### Task 5: Pricing — sqft, edge-LF, corbel disclosure, wired into calc()'s real total

**Files:**
- Modify: `stonedesk.html` (`calc()` ~L9895, `dcChamferPricingSummary` region ~L13086, `calcDrawing()` ~L13144, `dcSyncLiveToQuoteEngine()` ~L13280, admin Unit Pricing form ~L14470)

**Interfaces:**
- Consumes: `dcRaisedBar`, `dcRaisedBarEdgeLenIn()` (Task 1), `DC_BAR_EDGE_COST` (Task 1).
- Produces: `function dcRaisedBarPricingSummary()` returning `{ active, sqFt, edgeLF, effLenIn, effDepthIn, corbelFlag }`, consumed by this task and Task 6.

- [ ] **Step 1: Add the corbel-threshold admin field**

Find (around line 14470):

```html
</div><div class="sairn-form-grp">
  <label class="sairn-form-lbl">Edge work ($/LF)</label>
  <input class="sairn-form-inp" id="sairn-unit-edge_lf" value="18" type="number" step="0.01">
</div><div class="sairn-form-grp">
  <label class="sairn-form-lbl">Sink cutout (each)</label>
```

Replace with:

```html
</div><div class="sairn-form-grp">
  <label class="sairn-form-lbl">Edge work ($/LF)</label>
  <input class="sairn-form-inp" id="sairn-unit-edge_lf" value="18" type="number" step="0.01">
</div><div class="sairn-form-grp">
  <label class="sairn-form-lbl">Corbel support threshold, raised bar (in) — quartz default</label>
  <input class="sairn-form-inp" id="sairn-unit-corbel_threshold" value="15" type="number" step="0.5">
</div><div class="sairn-form-grp">
  <label class="sairn-form-lbl">Sink cutout (each)</label>
```

- [ ] **Step 2: Add `dcRaisedBarPricingSummary()`**

Find (around line 13086):

```js
function dcChamferPricingSummary() {
  const active = dcChamferActiveKeys();
  const totalDiagLF = active.reduce((sum,k) => sum + (dcChamferEffectiveSetbackIn(k) * Math.SQRT2) / 12, 0);
  return { count: active.length, totalDiagLF: totalDiagLF };
}
```

Replace with:

```js
function dcChamferPricingSummary() {
  const active = dcChamferActiveKeys();
  const totalDiagLF = active.reduce((sum,k) => sum + (dcChamferEffectiveSetbackIn(k) * Math.SQRT2) / 12, 0);
  return { count: active.length, totalDiagLF: totalDiagLF };
}

// Sums the active raised bar's real footprint and new edge length. Filters on ctShape prefix
// (same fix class as dcChamferActiveKeys()) so a bar left over from a different shape never
// bills or prints here. Effective length is re-clamped against the edge's CURRENT length, same
// staleness fix chamfer's own pricing/cut-sheet needed after its final review.
function dcRaisedBarPricingSummary() {
  if (!dcRaisedBar || dcRaisedBar.edgeKey.indexOf(ctShape + ':') !== 0) {
    return { active:false, sqFt:0, edgeLF:0, effLenIn:0, effDepthIn:0, corbelFlag:false };
  }
  const edgeLenIn = dcRaisedBarEdgeLenIn(dcRaisedBar.edgeKey);
  const effLenIn = edgeLenIn > 0 ? Math.min(dcRaisedBar.lengthIn, edgeLenIn) : dcRaisedBar.lengthIn;
  const effDepthIn = dcRaisedBar.overhangDepthIn;
  if (!(effLenIn > 0) || !(effDepthIn > 0)) {
    return { active:false, sqFt:0, edgeLF:0, effLenIn:0, effDepthIn:0, corbelFlag:false };
  }
  const sqFt = (effLenIn * effDepthIn) / 144;
  const edgeLF = (effLenIn / 12) + (effDepthIn / 12) * 2; // front edge + both step edges, single-sided
  const threshold = parseFloat((document.getElementById('sairn-unit-corbel_threshold')||{}).value) || 15;
  const corbelFlag = effDepthIn > threshold;
  return { active:true, sqFt, edgeLF, effLenIn, effDepthIn, corbelFlag };
}
```

- [ ] **Step 3: Compute `barSqFt`/`barEdgeCost` in `calcDrawing()`, fold into `totalMat`, add the results-panel card**

Find (around line 13207):

```js
  const totalMat=(netSqFt+splashSqFt+wfSqFt)*1.15;
  const slabs=Math.ceil(totalMat/50);
  const thh=(totalMat/50*4).toFixed(1);

  // Seams: each one adds a fabrication piece (more labor/handling) and its full length is
  // finished/polished edge on both sides of the cut, priced at the same edge_lf rate used
  // elsewhere in the app's pricing settings — additive to the sqft pricing above, not a
  // replacement for it.
  const seamInfo = (typeof dcSeamPricingSummary === 'function') ? dcSeamPricingSummary() : {seamCount:0,pieceCount:1,totalSeamLF:0};
  const edgeLfRate = parseFloat((document.getElementById('sairn-unit-edge_lf')||{}).value) || 18;
  const seamEdgeCost = seamInfo.totalSeamLF * 2 * edgeLfRate; // both sides of every cut are finished edge
  const chamferInfo = (typeof dcChamferPricingSummary === 'function') ? dcChamferPricingSummary() : {count:0,totalDiagLF:0};
  const chamferEdgeCost = chamferInfo.totalDiagLF * 2 * edgeLfRate; // both sides of every chamfer cut are finished edge, same convention as seams
  const drainboardInfo = (typeof dcDrainboardPricingSummary === 'function') ? dcDrainboardPricingSummary() : {count:0,totalCost:0};
```

Replace with:

```js
  const barInfo = (typeof dcRaisedBarPricingSummary === 'function') ? dcRaisedBarPricingSummary() : {active:false,sqFt:0,edgeLF:0,corbelFlag:false};
  const totalMat=(netSqFt+splashSqFt+wfSqFt+barInfo.sqFt)*1.15;
  const slabs=Math.ceil(totalMat/50);
  const thh=(totalMat/50*4).toFixed(1);

  // Seams: each one adds a fabrication piece (more labor/handling) and its full length is
  // finished/polished edge on both sides of the cut, priced at the same edge_lf rate used
  // elsewhere in the app's pricing settings — additive to the sqft pricing above, not a
  // replacement for it.
  const seamInfo = (typeof dcSeamPricingSummary === 'function') ? dcSeamPricingSummary() : {seamCount:0,pieceCount:1,totalSeamLF:0};
  const edgeLfRate = parseFloat((document.getElementById('sairn-unit-edge_lf')||{}).value) || 18;
  const seamEdgeCost = seamInfo.totalSeamLF * 2 * edgeLfRate; // both sides of every cut are finished edge
  const chamferInfo = (typeof dcChamferPricingSummary === 'function') ? dcChamferPricingSummary() : {count:0,totalDiagLF:0};
  const chamferEdgeCost = chamferInfo.totalDiagLF * 2 * edgeLfRate; // both sides of every chamfer cut are finished edge, same convention as seams
  const barEdgeCost = barInfo.edgeLF * edgeLfRate; // single-sided -- ordinary perimeter edges, not an interior double-faced cut
  const drainboardInfo = (typeof dcDrainboardPricingSummary === 'function') ? dcDrainboardPricingSummary() : {count:0,totalCost:0};
```

Find (around line 13235, right after the Chamfered Corners metrics entry):

```js
    {n:chamferInfo.count>0?'+$'+chamferEdgeCost.toFixed(0):'None',l:'Chamfered Corners',s:chamferInfo.count>0?chamferInfo.count+' corner(s), '+chamferInfo.totalDiagLF.toFixed(2)+' LF diagonal edge':'No corners chamfered'},
    {n:drainboardInfo.count>0?'$'+drainboardInfo.totalCost.toFixed(0):'None',l:'Drainboard(s)',s:drainboardInfo.count>0?drainboardInfo.count+' side(s) attached':'No drainboards placed'},
```

Replace with:

```js
    {n:chamferInfo.count>0?'+$'+chamferEdgeCost.toFixed(0):'None',l:'Chamfered Corners',s:chamferInfo.count>0?chamferInfo.count+' corner(s), '+chamferInfo.totalDiagLF.toFixed(2)+' LF diagonal edge':'No corners chamfered'},
    {n:barInfo.active?barInfo.sqFt.toFixed(2)+' sqft':'None',l:'Raised Bar',s:barInfo.active?barInfo.effLenIn.toFixed(1)+'in x '+barInfo.effDepthIn.toFixed(1)+'in overhang'+(barInfo.corbelFlag?' -- corbel support recommended':''):'No raised bar'},
    {n:drainboardInfo.count>0?'$'+drainboardInfo.totalCost.toFixed(0):'None',l:'Drainboard(s)',s:drainboardInfo.count>0?drainboardInfo.count+' side(s) attached':'No drainboards placed'},
```

- [ ] **Step 4: Pass `barEdgeCost` into `dcSyncLiveToQuoteEngine()`**

Find (around line 13265):

```js
  drawCTPreview();
  dcSyncLiveToQuoteEngine(grossSqFt, seamEdgeCost, chamferEdgeCost);
}
```

Replace with:

```js
  drawCTPreview();
  dcSyncLiveToQuoteEngine(grossSqFt, seamEdgeCost, chamferEdgeCost, barEdgeCost);
}
```

- [ ] **Step 5: Accept the param and assign `DC_BAR_EDGE_COST` in `dcSyncLiveToQuoteEngine()`**

Find (around line 13280):

```js
function dcSyncLiveToQuoteEngine(grossSqFt, seamEdgeCost, chamferEdgeCost) {
```

Replace with:

```js
function dcSyncLiveToQuoteEngine(grossSqFt, seamEdgeCost, chamferEdgeCost, barEdgeCost) {
```

Find (around line 13328):

```js
  if (typeof seamEdgeCost === 'number') DC_SEAM_EDGE_COST = seamEdgeCost;
  if (typeof chamferEdgeCost === 'number') DC_CHAMFER_EDGE_COST = chamferEdgeCost;

  calc();
```

Replace with:

```js
  if (typeof seamEdgeCost === 'number') DC_SEAM_EDGE_COST = seamEdgeCost;
  if (typeof chamferEdgeCost === 'number') DC_CHAMFER_EDGE_COST = chamferEdgeCost;
  if (typeof barEdgeCost === 'number') DC_BAR_EDGE_COST = barEdgeCost;

  calc();
```

- [ ] **Step 6: Read `DC_BAR_EDGE_COST` in `calc()` — add to `rawSubtotal`, `lastCalc`, `lines[]`**

Find (around line 9903):

```js
  const seamCost = (typeof DC_SEAM_EDGE_COST === 'number') ? DC_SEAM_EDGE_COST : 0;
  const chamferCost = (typeof DC_CHAMFER_EDGE_COST === 'number') ? DC_CHAMFER_EDGE_COST : 0;
  const rawSubtotal = matFabSubtotal + finishCost + edgeCost + waterfallCost + sinkCost + cookCost + holeCost + outletCost + bsCost + bktCost + dwCost + seamCost + chamferCost + removal + delivery;
```

Replace with:

```js
  const seamCost = (typeof DC_SEAM_EDGE_COST === 'number') ? DC_SEAM_EDGE_COST : 0;
  const chamferCost = (typeof DC_CHAMFER_EDGE_COST === 'number') ? DC_CHAMFER_EDGE_COST : 0;
  const barCost = (typeof DC_BAR_EDGE_COST === 'number') ? DC_BAR_EDGE_COST : 0;
  const rawSubtotal = matFabSubtotal + finishCost + edgeCost + waterfallCost + sinkCost + cookCost + holeCost + outletCost + bsCost + bktCost + dwCost + seamCost + chamferCost + barCost + removal + delivery;
```

Find (around line 9914):

```js
  lastCalc = { mat, proj, tier, total, totalLF, impliedSF, impliedPPSF, bsRate, edgeRate, sinkFee, thick, finUpch, removal, delivery, waterfallCost, sinkCost, cookCost, holeCost, outletCost, bsCost, bktCost, dwCost, seamCost, chamferCost, matFabSubtotal, finishCost, edgeCost, tierAdj };
```

Replace with:

```js
  lastCalc = { mat, proj, tier, total, totalLF, impliedSF, impliedPPSF, bsRate, edgeRate, sinkFee, thick, finUpch, removal, delivery, waterfallCost, sinkCost, cookCost, holeCost, outletCost, bsCost, bktCost, dwCost, seamCost, chamferCost, barCost, matFabSubtotal, finishCost, edgeCost, tierAdj };
```

Find (around line 9935):

```js
    { name:'Chamfered corner(s)', val:chamferCost, show:chamferCost > 0 },
    { name:'Old countertop removal', val:removal, show:removal > 0 },
```

Replace with:

```js
    { name:'Chamfered corner(s)', val:chamferCost, show:chamferCost > 0 },
    { name:'Raised bar edge', val:barCost, show:barCost > 0 },
    { name:'Old countertop removal', val:removal, show:removal > 0 },
```

- [ ] **Step 7: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 8: Manual verification (browser console)**

On the `straight` preset with a valid material/project selected:

```js
document.getElementById('db-bar-edge').value = 'straight:Front (exposed)';
document.getElementById('db-bar-len').value = 48;
document.getElementById('db-bar-depth').value = 12;
document.getElementById('db-bar-edge').dispatchEvent(new Event('change'));
const before = lastCalc.total;
document.getElementById('db-bar-edge').value = '';
document.getElementById('db-bar-edge').dispatchEvent(new Event('change'));
lastCalc.barCost; // -> 0
document.getElementById('db-bar-edge').value = 'straight:Front (exposed)';
document.getElementById('db-bar-edge').dispatchEvent(new Event('change'));
lastCalc.barCost > 0; // -> true
document.getElementById('db-bar-depth').value = 20;
document.getElementById('db-bar-depth').dispatchEvent(new Event('input'));
lastCalc.corbelFlag; // undefined on lastCalc itself -- check the metrics card instead:
document.querySelector('#ct-results').textContent.includes('corbel support recommended'); // -> true (20in > 15in default threshold)
```

Expected: matches comments — cost zeroes on deactivation, reactivates correctly, corbel flag appears once overhang depth exceeds the 15in default.

- [ ] **Step 9: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- raised bar sqft/edge-LF pricing wired into calc()'s real quote total"
```

---

### Task 6: Cut sheet — print the raised bar

**Files:**
- Modify: `stonedesk.html` (`printDrawCutSheet()` ~L13404, ~L13436)

**Interfaces:**
- Consumes: `dcRaisedBarPricingSummary()`, `dcRaisedBar` (Task 1/5).

- [ ] **Step 1: Fold `barSqFt` into `totalMat`**

Find (around line 13404):

```js
  const totalMat=(netSqFt+splashSqFt+wfSqFt)*1.15;
```

Replace with:

```js
  const barInfo2 = (typeof dcRaisedBarPricingSummary === 'function') ? dcRaisedBarPricingSummary() : {active:false,sqFt:0,effLenIn:0,effDepthIn:0,corbelFlag:false};
  const totalMat=(netSqFt+splashSqFt+wfSqFt+barInfo2.sqFt)*1.15;
```

- [ ] **Step 2: Add the "Raised Bar" row**

Find (around line 13436):

```js
  if (typeof dcChamferedCorners !== 'undefined' && typeof dcChamferActiveKeys === 'function') {
    const chamferLabels = { 'lshape-AB':'Inside corner (A-B)', 'ushape-BackLeft':'Inside corner (Back-Left)', 'ushape-BackRight':'Inside corner (Back-Right)' };
    const activeChamfers = dcChamferActiveKeys();
    if (activeChamfers.length) {
      const chamferSummary = activeChamfers.map(k => (chamferLabels[k]||k) + ': ' + dcChamferEffectiveSetbackIn(k).toFixed(2) + 'in chamfer').join(', ');
      win.document.write('<div class="row"><span class="rl">Chamfered Corners</span><span class="rv">'+chamferSummary+'</span></div>');
    }
  }
  if (typeof dcCutouts !== 'undefined' && dcCutouts.length) {
```

Replace with:

```js
  if (typeof dcChamferedCorners !== 'undefined' && typeof dcChamferActiveKeys === 'function') {
    const chamferLabels = { 'lshape-AB':'Inside corner (A-B)', 'ushape-BackLeft':'Inside corner (Back-Left)', 'ushape-BackRight':'Inside corner (Back-Right)' };
    const activeChamfers = dcChamferActiveKeys();
    if (activeChamfers.length) {
      const chamferSummary = activeChamfers.map(k => (chamferLabels[k]||k) + ': ' + dcChamferEffectiveSetbackIn(k).toFixed(2) + 'in chamfer').join(', ');
      win.document.write('<div class="row"><span class="rl">Chamfered Corners</span><span class="rv">'+chamferSummary+'</span></div>');
    }
  }
  if (barInfo2.active) {
    const barEdgeLabel = dcRaisedBar.edgeKey.slice(dcRaisedBar.edgeKey.indexOf(':')+1);
    win.document.write('<div class="row"><span class="rl">Raised Bar</span><span class="rv">'+barEdgeLabel+': '+barInfo2.effLenIn.toFixed(1)+'in \xd7 '+barInfo2.effDepthIn.toFixed(1)+'in overhang, '+dcRaisedBar.heightIn+'in height'+(barInfo2.corbelFlag?' ⚠ corbel support recommended':'')+'</span></div>');
  }
  if (typeof dcCutouts !== 'undefined' && dcCutouts.length) {
```

- [ ] **Step 3: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 4: Manual verification (browser console)**

On the `straight` preset with a bar set (length 48, depth 20 — above the 15in default threshold):

```js
printDrawCutSheet();
```

Expected: the new tab's printed cut sheet shows a "Raised Bar" row reading `Front (exposed): 48.0in × 20.0in overhang, 42in height ⚠ corbel support recommended`, positioned between the Chamfered Corners row (if any) and the Placed Cutouts row. Set depth to 10 (below threshold) and reprint — confirm the `⚠ corbel support recommended` suffix disappears.

- [ ] **Step 5: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- raised bar listed on the printed cut sheet"
```

---

### Task 7: Full verification sweep, live-verify, and push

**Files:** none (verification only)

- [ ] **Step 1: Full local syntax sweep**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0` across all blocks.

- [ ] **Step 2: Scoped Guardian checks**

Run: `python tools/duplicate_global_check.py stonedesk.html`
Expected: `DUPLICATE_NAMES:0`

Run: `python tools/sairn_dead_button_audit.py stonedesk.html`
Expected: no new findings referencing `db-bar-edge`, `db-bar-len`, `db-bar-offset`, `db-bar-depth`, `db-bar-height`, `dcRaisedBar`, `dcDrawRaisedBarIfActive`, `dcRaisedBarPricingSummary`, `buildRaisedBarArea`, `dcRaisedBarEdgeLenIn`.

Run: `python tools/nav_panel_check.py stonedesk.html`
Expected: `RESULT:PASS` (this feature doesn't touch panels/nav; a regression here would indicate an unintended change elsewhere).

Search: grep `stonedesk.html` for `console.log` inside the diff introduced by this plan — confirm none was left in.

- [ ] **Step 3: Run the full guardian and adversarial review before commit/push**

Invoke the `sairn-guardian-v2` skill's full Check 0 + numbered checks against the diff, per CLAUDE.md's standing Push Protocol. Resolve any findings before proceeding.

- [ ] **Step 4: Combined end-to-end manual verification (browser console)**

Across all six shape families in one pass:

```js
selectDrawShape('straight');
document.getElementById('db-bar-edge').value = 'straight:Front (exposed)';
document.getElementById('db-bar-len').value = 40; document.getElementById('db-bar-depth').value = 12;
document.getElementById('db-bar-edge').dispatchEvent(new Event('change'));
dcRaisedBar.edgeKey; // -> 'straight:Front (exposed)'
lastCalc.barCost > 0; // -> true

selectDrawShape('ushape');
dcRaisedBar; // -> still the straight object in memory, but...
document.getElementById('db-bar-edge').value; // -> '' (buildRaisedBarArea correctly shows inactive for this shape)
lastCalc.barCost; // -> 0 (dcRaisedBarPricingSummary filtered it out)

selectDrawShape('straight');
document.getElementById('db-bar-edge').value; // -> 'straight:Front (exposed)' (reactivated, state preserved)

dcClearPoly();
dcRaisedBar; // -> null (fresh-draw reset)
```

Expected: matches each comment — this is the exact shape-scope-leak check chamfer's final review had to catch after the fact, verified here as part of the plan itself.

- [ ] **Step 5: Push**

```bash
git push origin main
```

- [ ] **Step 6: Live-verify against production**

Per CLAUDE.md's Push Protocol: drive `sairn.vercel.app/stonedesk`'s deployed functions directly (Playwright, using the license-gate workaround documented in `STONEDESK-SESSION79-HANDOFF.md` §3) and repeat Step 4's console checks against the live site. Confirm the deployed file hash matches the pushed commit.

- [ ] **Step 7: Write the session handoff**

Use the `sairn-session-handoff` skill to record this feature's landing in a new `STONEDESK-SESSION-N-HANDOFF.md` (next number after 80), per this project's standing convention.

---

## Self-Review Notes

- **Spec coverage:** data model + UI (Task 1), rendering across all three renderer families — fixed-single-rect (Task 2), fixed-multi-rect/U-shape (Task 3), dynamic-loop galley/custom (Task 4), pricing including corbel disclosure (Task 5), cut sheet (Task 6), the shape-scope-leak fix built in from the start and explicitly re-verified (Task 7 Step 4), full verification cycle (Task 7). Vertical-edge and Custom-Draw-mode exclusions are enforced by `DC_BAR_EDGE_CANDIDATES` simply never listing them — no task adds them, matching the spec's explicit scope cut.
- **Placeholder scan:** no TBD/TODO, no "add appropriate handling" — every step shows real code or a real runnable command with a stated expected result.
- **Type/name consistency:** `dcRaisedBar`, `DC_BAR_EDGE_CANDIDATES`, `dcRaisedBarEdgeLenIn`, `buildRaisedBarArea`, `dcDrawRaisedBarIfActive`, `dcRaisedBarPricingSummary`, `DC_BAR_EDGE_COST`, `barEdgeCost`/`barCost`/`barInfo`/`barInfo2` are spelled identically everywhere they're produced (Tasks 1/2/5) and consumed (Tasks 2–6).
