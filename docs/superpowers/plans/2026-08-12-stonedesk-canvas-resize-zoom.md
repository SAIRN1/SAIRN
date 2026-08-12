# StoneDesk — Drawing Canvas Responsive Height + Zoom Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the drawing canvas's fixed 480px height with a viewport-relative, capped height, and add button-only zoom (In/Out/Fit) anchored on the canvas center — covering Preset and Custom Draw modes, with zero changes to any existing hit-test/drag function.

**Architecture:** Two independent additions to `stonedesk.html`. Height: a shared `dcComputeCanvasHeight()` helper replacing the two hardcoded `480` assignments, plus a new debounced `resize` listener. Zoom: a single `dcZoomLevel` variable applied as one `ctx.setTransform()` call at the top of `drawCTPreview()` (rendering) and its exact inverse inside `dcCanvasCoords()` (the one function every existing mouse/touch handler already calls to convert a click into canvas-pixel space) — so corner-drag, preset-edge-drag, cutout/seam placement, and every other interaction keep working completely unchanged.

**Tech Stack:** Vanilla JS, HTML5 Canvas 2D. No dependencies added.

## Global Constraints

- `node --check` must pass on every touched script block before any commit — run `python tools/checkblocks.py stonedesk.html` and confirm `FAILED_BLOCKS:0` (baseline before this plan: `TOTAL_BLOCKS:128`, `FAILED_BLOCKS:0`).
- Never bulk find-replace. Every edit below is a targeted, unique-context change.
- Zoom covers Preset and Custom Draw modes only. Room Layout mode (`dcMode==='room'`) is out of scope — its own independent renderer (`drawDCRoom`/`dcRoomGetTransform`) must not be touched.
- `dcApplyZoomTransform()` must use `ctx.setTransform(...)` (absolute), never `ctx.save()`/`ctx.scale()`/`ctx.restore()` — `drawCTPreview()` has multiple early-return paths, and a save/restore pair would need matching every one of them or the canvas transform stack corrupts silently across frames.
- `ctx.setTransform(1,0,0,1,0,0)` must run immediately before `ctx.clearRect(0,0,W,H)` on every `drawCTPreview()` call, so the clear always covers the full buffer regardless of the previous frame's zoom state.
- No existing hit-test/drag function (`dcHitRect`, `dcHitPresetEdge`, corner-drag, `dcCanvasPlaceOrDrag`, the seam/cutout routers, touch translation) may be modified — the zoom inverse lives entirely inside `dcCanvasCoords()`, which they already all call.
- Zoom range is `[1, 3]`, step ×1.25 per click. No manual pan, no scroll-wheel, no pinch-to-zoom.
- Zoom resets to 1 on: the Fit button, switching shapes (`selectDrawShape()`), switching modes (`setDCMode()`), and clearing the shape (`dcClearPoly()`).
- Canvas height: `Math.max(480, Math.min(window.innerHeight * 0.65, 900))` — never smaller than today's fixed value, never larger than 900px.

---

## File Structure

Single file touched: `stonedesk.html`. No new files.

| Region (function) | Responsibility for this feature |
|---|---|
| ~L10317 (module vars near `dcMode`) | New `var dcZoomLevel = 1;` and zoom-bound constants. |
| ~L10329 (`initDCCanvas`) | Use `dcComputeCanvasHeight()` instead of literal `480`; wire the new debounced `resize` listener. |
| ~L10369 (`toggleDCLeftPanel`) | Use `dcComputeCanvasHeight()` instead of literal `480`. |
| ~L10465 (`dcCanvasCoords`) | Apply the zoom inverse before returning `{px, py}`. |
| ~L11664 (`drawCTPreview`) | Reset-then-clear-then-apply-zoom-transform at the top. |
| ~L11029 (`dcClearPoly`) | Reset `dcZoomLevel = 1`. |
| ~L11280 (`selectDrawShape`) | Reset `dcZoomLevel = 1`. |
| ~L10484 (`setDCMode`) | Reset `dcZoomLevel = 1`; show/hide the new zoom toolbar row (hidden in Room mode). |
| ~L3937 (HTML, mode toolbar) | New zoom toolbar row: Zoom Out / Fit to Screen / Zoom In buttons + a live `%` label. |

Line numbers are as of this plan's base commit and will drift by a few lines as earlier tasks land — every edit below is anchored to unique surrounding code, not the raw number.

---

### Task 1: Canvas height — viewport-relative, capped

**Files:**
- Modify: `stonedesk.html` (`initDCCanvas()`, `toggleDCLeftPanel()`, both ~L10329–10382)

**Interfaces:**
- Produces: `function dcComputeCanvasHeight()` returning a number, consumed by both call sites in this task and available for Task 2/3's reset paths if ever needed (not required by them).

- [ ] **Step 1: Add `dcComputeCanvasHeight()` and use it in both existing call sites**

Find (around line 10329):

```js
function initDCCanvas() {
  dcCanvas = document.getElementById('ct-canvas');
  if (!dcCanvas) return;
  dcCtx = dcCanvas.getContext('2d', { willReadFrequently: true });
  dcCanvas.width = dcCanvas.offsetWidth || 640;
  dcCanvas.height = 480;
  dcCanvas.onmousedown = dcCanvasClick;
  dcCanvas.onmousemove = dcCanvasHover;
  dcCanvas.oncontextmenu = e => e.preventDefault();
  initDCCutoutEvents();
  initDCSeamEvents();
  initDCTouchEvents();
```

Replace with:

```js
// Canvas height (2026-08-12): replaces the old fixed 480px with a viewport-relative, capped
// value -- 65% of the browser's visible height, floored at 480 (never smaller than today's
// experience) and capped at 900 (never dominates the page on an ultrawide monitor). Width was
// already responsive (dcCanvas.width = offsetWidth, both call sites below); this was the one
// real fixed constant.
function dcComputeCanvasHeight() {
  return Math.max(480, Math.min(window.innerHeight * 0.65, 900));
}

function initDCCanvas() {
  dcCanvas = document.getElementById('ct-canvas');
  if (!dcCanvas) return;
  dcCtx = dcCanvas.getContext('2d', { willReadFrequently: true });
  dcCanvas.width = dcCanvas.offsetWidth || 640;
  dcCanvas.height = dcComputeCanvasHeight();
  dcCanvas.onmousedown = dcCanvasClick;
  dcCanvas.onmousemove = dcCanvasHover;
  dcCanvas.oncontextmenu = e => e.preventDefault();
  initDCCutoutEvents();
  initDCSeamEvents();
  initDCTouchEvents();
  // Debounced window-resize re-sync (2026-08-12): no resize listener existed for this canvas
  // before -- width only ever re-synced on load and on the side-panel collapse toggle. Guarded
  // so it only wires once per canvas lifetime, same pattern as the mouseup listener below.
  // Debounced (~150ms) so a window-drag doesn't fire a full redraw on every intermediate event.
  if (!dcCanvas._resizeWired) {
    dcCanvas._resizeWired = true;
    var dcResizeDebounce = null;
    window.addEventListener('resize', function () {
      clearTimeout(dcResizeDebounce);
      dcResizeDebounce = setTimeout(function () {
        if (!dcCanvas) return;
        dcCanvas.width = dcCanvas.offsetWidth || dcCanvas.width;
        dcCanvas.height = dcComputeCanvasHeight();
        if (typeof drawCTPreview === 'function') drawCTPreview();
      }, 150);
    });
  }
```

- [ ] **Step 2: Use `dcComputeCanvasHeight()` in `toggleDCLeftPanel()`**

Find (around line 10369):

```js
function toggleDCLeftPanel() {
  var col = document.getElementById('draw-left-col');
  var btn = document.getElementById('dc-collapse-btn');
  if (!col) return;
  var collapsed = col.classList.toggle('dc-collapsed');
  if (btn) btn.textContent = collapsed ? '▶ Show Panel' : '◀ Hide Panel';
  setTimeout(function(){
    if (dcCanvas) {
      dcCanvas.width = dcCanvas.offsetWidth || dcCanvas.width;
      dcCanvas.height = 480;
    }
    if (typeof drawCTPreview === 'function') drawCTPreview();
  }, 220);
}
```

Replace with:

```js
function toggleDCLeftPanel() {
  var col = document.getElementById('draw-left-col');
  var btn = document.getElementById('dc-collapse-btn');
  if (!col) return;
  var collapsed = col.classList.toggle('dc-collapsed');
  if (btn) btn.textContent = collapsed ? '▶ Show Panel' : '◀ Hide Panel';
  setTimeout(function(){
    if (dcCanvas) {
      dcCanvas.width = dcCanvas.offsetWidth || dcCanvas.width;
      dcCanvas.height = dcComputeCanvasHeight();
    }
    if (typeof drawCTPreview === 'function') drawCTPreview();
  }, 220);
}
```

- [ ] **Step 3: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `TOTAL_BLOCKS:128` (or current count), `FAILED_BLOCKS:0`

- [ ] **Step 4: Manual verification (browser console)**

Open `stonedesk.html`, log in past the PIN/trial gate, open the Drawing Tool, then in devtools console:

```js
dcComputeCanvasHeight();                          // -> a number between 480 and 900
window.innerHeight * 0.65 < 480 ? 'floors to 480' : window.innerHeight * 0.65 > 900 ? 'caps to 900' : 'uses the raw value';
document.getElementById('ct-canvas').height;       // -> matches dcComputeCanvasHeight()'s current return value
window.dispatchEvent(new Event('resize'));
// wait ~200ms, then:
document.getElementById('ct-canvas').height;       // -> still matches dcComputeCanvasHeight() (resize listener fired)
```

Expected: matches comments — canvas height is real, viewport-derived, and re-syncs on resize (not just on load).

- [ ] **Step 5: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- drawing canvas height, viewport-relative and capped, replacing fixed 480px"
```

---

### Task 2: Zoom transform — render-side and hit-test-side

**Files:**
- Modify: `stonedesk.html` (module vars ~L10317, `drawCTPreview()` ~L11664, `dcCanvasCoords()` ~L10465)

**Interfaces:**
- Produces: `var dcZoomLevel` (number, default `1`), `function dcApplyZoomTransform(ctx, W, H)` — consumed by Task 3's zoom buttons and reset points.
- Consumes: nothing new — `dcCanvas.width`/`dcCanvas.height` (existing globals).

- [ ] **Step 1: Add `dcZoomLevel` and the zoom bound constants**

Find (around line 10317):

```js
var dcCanvas = null, dcCtx = null;
var dcMode = 'preset';        // 'preset' = show the active preset's rectangle math (legacy renderer) | 'draw' = polygon mode active
```

Replace with:

```js
var dcCanvas = null, dcCtx = null;
// Zoom (2026-08-12): covers Preset and Custom Draw modes only -- Room Layout has its own
// independent renderer/transform and is out of scope. No manual pan: zoom is always anchored on
// the canvas's own center point (see dcApplyZoomTransform below), so there is no pan offset to
// track, just this one multiplier.
var dcZoomLevel = 1;          // 1.0 = fit (today's unzoomed behavior); range [DC_ZOOM_MIN, DC_ZOOM_MAX]
var DC_ZOOM_MIN = 1, DC_ZOOM_MAX = 3, DC_ZOOM_STEP = 1.25;
var dcMode = 'preset';        // 'preset' = show the active preset's rectangle math (legacy renderer) | 'draw' = polygon mode active
```

- [ ] **Step 2: Add `dcApplyZoomTransform()` and wire it into `drawCTPreview()`**

Find (around line 11673):

```js
  const ctx = cv.getContext('2d', { willReadFrequently: true });
  const W=cv.width, H=cv.height;
  ctx.clearRect(0,0,W,H);
```

Replace with:

```js
  const ctx = cv.getContext('2d', { willReadFrequently: true });
  const W=cv.width, H=cv.height;
  // Zoom (2026-08-12): reset to identity BEFORE clearing -- clearRect(0,0,W,H) must run in
  // untransformed space, or after a previously-zoomed frame it would only clear the region that
  // maps to (0,0,W,H) under the STALE transform, leaving old content visible outside it.
  ctx.setTransform(1,0,0,1,0,0);
  ctx.clearRect(0,0,W,H);
  dcApplyZoomTransform(ctx, W, H);
```

Find (around line 10469, right after `dcCanvasCoords`'s closing brace):

```js
function dcCanvasCoords(e) {
  const rect = dcCanvas.getBoundingClientRect();
  const scaleX = dcCanvas.width/rect.width, scaleY = dcCanvas.height/rect.height;
  return { px:(e.clientX-rect.left)*scaleX, py:(e.clientY-rect.top)*scaleY };
}
```

Replace with:

```js
// Sets the CURRENT (absolute, not stacked) canvas transform to scale everything drawn
// afterward -- grid, shapes, strokes, dimension text -- uniformly around the canvas's own
// center point (W/2, H/2). Uses setTransform, not save()/scale()/restore(): drawCTPreview() has
// several early-return paths (blank-dimensions guards, the draw/room mode branches), and a
// save/restore pair would need matching every single one or the transform stack corrupts
// silently across frames. setTransform is absolute -- called once here, nothing else needed.
function dcApplyZoomTransform(ctx, W, H) {
  ctx.setTransform(dcZoomLevel, 0, 0, dcZoomLevel, W/2*(1-dcZoomLevel), H/2*(1-dcZoomLevel));
}

function dcCanvasCoords(e) {
  const rect = dcCanvas.getBoundingClientRect();
  const scaleX = dcCanvas.width/rect.width, scaleY = dcCanvas.height/rect.height;
  const rawPx = (e.clientX-rect.left)*scaleX, rawPy = (e.clientY-rect.top)*scaleY;
  // Zoom (2026-08-12): exact inverse of dcApplyZoomTransform()'s setTransform above, so every
  // existing hit-test/drag function downstream of this call (dcHitRect, dcHitPresetEdge,
  // corner-drag, dcCanvasPlaceOrDrag, the seam/cutout routers, touch translation) keeps working
  // in the exact same coordinate space it always has -- zero changes needed to any of them. At
  // dcZoomLevel===1 (the default) this reduces to px=rawPx, py=rawPy: byte-identical to today.
  const W = dcCanvas.width, H = dcCanvas.height;
  const px = (rawPx - W/2*(1-dcZoomLevel)) / dcZoomLevel;
  const py = (rawPy - H/2*(1-dcZoomLevel)) / dcZoomLevel;
  return { px, py };
}
```

- [ ] **Step 3: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 4: Manual verification (browser console)**

With the `straight` preset selected and default dimensions:

```js
dcZoomLevel;                       // -> 1
drawCTPreview();                   // canvas should look exactly as before this change

dcZoomLevel = 2;
drawCTPreview();
// The drawing should now visibly appear 2x larger, still centered in the canvas.

// Hit-test correctness proof: place a sink cutout at zoom 1, remember its canvas position,
// then confirm a click at the CENTER of the canvas maps to the same logical point at any zoom:
const W = document.getElementById('ct-canvas').width, H = document.getElementById('ct-canvas').height;
const centerScreenEvent = { clientX: 0, clientY: 0 }; // placeholder, real check below uses dcCanvasCoords math directly
// Direct inverse-transform check instead of simulating a real mouse event:
dcZoomLevel = 1;
const raw = { px: W/2, py: H/2 };
const invAt1 = { px: (raw.px - W/2*(1-dcZoomLevel))/dcZoomLevel, py: (raw.py - H/2*(1-dcZoomLevel))/dcZoomLevel };
invAt1;                            // -> { px: W/2, py: H/2 } (identity at zoom 1)
dcZoomLevel = 2;
const invAt2 = { px: (raw.px - W/2*(1-dcZoomLevel))/dcZoomLevel, py: (raw.py - H/2*(1-dcZoomLevel))/dcZoomLevel };
invAt2;                            // -> { px: W/2, py: H/2 } (canvas CENTER maps to the same logical point at any zoom -- the anchor property)
dcZoomLevel = 1;
drawCTPreview();
```

Expected: matches comments — zoom 1 is visually and numerically identical to today; the canvas center point is invariant across zoom levels (proving the transform and its inverse are true mirrors of each other).

- [ ] **Step 5: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- zoom transform (render-side setTransform + dcCanvasCoords inverse)"
```

---

### Task 3: Zoom UI — buttons, wiring, and reset-on-state-change

**Files:**
- Modify: `stonedesk.html` (HTML toolbar ~L3937, `setDCMode()` ~L10484, `dcClearPoly()` ~L11029, `selectDrawShape()` ~L11280, plus new zoom-control functions near `dcApplyZoomTransform`)

**Interfaces:**
- Consumes: `dcZoomLevel`, `DC_ZOOM_MIN`, `DC_ZOOM_MAX`, `DC_ZOOM_STEP` (Task 2).
- Produces: `function dcZoomIn()`, `function dcZoomOut()`, `function dcZoomFit()`, `function dcUpdateZoomUI()` — consumed only within this task (button `onclick` handlers and the three reset points).

- [ ] **Step 1: Add the zoom toolbar row to the HTML**

Find (around line 3937):

```html
          <div class="draw-toolbar">
            <span style="font-size:10px;color:var(--muted);margin-right:2px">Mode:</span>
            <button class="draw-btn dc-mode-btn active" id="dc-mode-preset" onclick="setDCMode('preset')">📐 Preset Shape</button>
            <button class="draw-btn dc-mode-btn" id="dc-mode-draw" onclick="setDCMode('draw')">✏️ Custom Draw</button>
            <button class="draw-btn dc-mode-btn" id="dc-mode-room" onclick="setDCMode('room')">🏠 Room Layout</button>
            <span style="font-size:10px;color:var(--muted);margin-left:4px" id="dc-mode-hint">In Preset Shape, drag any edge of the drawing to stretch it — type to set the exact length while dragging. Switch to Custom Draw for irregular shapes: click and drag toward the next point (snaps to 45°), type to set the exact length while dragging, release to place it. Click near the start to close the shape, drag any corner once closed.</span>
          </div>
```

Replace with:

```html
          <div class="draw-toolbar">
            <span style="font-size:10px;color:var(--muted);margin-right:2px">Mode:</span>
            <button class="draw-btn dc-mode-btn active" id="dc-mode-preset" onclick="setDCMode('preset')">📐 Preset Shape</button>
            <button class="draw-btn dc-mode-btn" id="dc-mode-draw" onclick="setDCMode('draw')">✏️ Custom Draw</button>
            <button class="draw-btn dc-mode-btn" id="dc-mode-room" onclick="setDCMode('room')">🏠 Room Layout</button>
            <span style="font-size:10px;color:var(--muted);margin-left:4px" id="dc-mode-hint">In Preset Shape, drag any edge of the drawing to stretch it — type to set the exact length while dragging. Switch to Custom Draw for irregular shapes: click and drag toward the next point (snaps to 45°), type to set the exact length while dragging, release to place it. Click near the start to close the shape, drag any corner once closed.</span>
          </div>

          <div class="draw-toolbar" id="dc-zoom-tools" style="margin-top:6px">
            <span style="font-size:10px;color:var(--muted);margin-right:2px">Zoom:</span>
            <button class="draw-btn" id="dc-zoom-out-btn" onclick="dcZoomOut()">− Zoom Out</button>
            <button class="draw-btn" id="dc-zoom-fit-btn" onclick="dcZoomFit()">⤢ Fit to Screen</button>
            <button class="draw-btn" id="dc-zoom-in-btn" onclick="dcZoomIn()">+ Zoom In</button>
            <span style="font-size:10px;color:var(--muted);margin-left:4px" id="dc-zoom-label">100%</span>
          </div>
```

- [ ] **Step 2: Add the zoom-control functions**

Find (around line 10469, right after `dcApplyZoomTransform()`'s closing brace, before `dcCanvasCoords`):

```js
function dcApplyZoomTransform(ctx, W, H) {
  ctx.setTransform(dcZoomLevel, 0, 0, dcZoomLevel, W/2*(1-dcZoomLevel), H/2*(1-dcZoomLevel));
}

function dcCanvasCoords(e) {
```

Replace with:

```js
function dcApplyZoomTransform(ctx, W, H) {
  ctx.setTransform(dcZoomLevel, 0, 0, dcZoomLevel, W/2*(1-dcZoomLevel), H/2*(1-dcZoomLevel));
}

// Syncs the zoom toolbar's live %-label and each button's disabled state to the current
// dcZoomLevel. Called after every zoom change AND after every reset-to-1 point (shape switch,
// mode switch, Clear Shape) so the UI never shows a stale percentage or an enabled button at a
// bound that's already been reached.
function dcUpdateZoomUI() {
  const label = document.getElementById('dc-zoom-label');
  if (label) label.textContent = Math.round(dcZoomLevel * 100) + '%';
  const outBtn = document.getElementById('dc-zoom-out-btn');
  const inBtn = document.getElementById('dc-zoom-in-btn');
  if (outBtn) outBtn.disabled = dcZoomLevel <= DC_ZOOM_MIN;
  if (inBtn) inBtn.disabled = dcZoomLevel >= DC_ZOOM_MAX;
}
function dcZoomIn() {
  dcZoomLevel = Math.min(dcZoomLevel * DC_ZOOM_STEP, DC_ZOOM_MAX);
  dcUpdateZoomUI();
  drawCTPreview();
}
function dcZoomOut() {
  dcZoomLevel = Math.max(dcZoomLevel / DC_ZOOM_STEP, DC_ZOOM_MIN);
  dcUpdateZoomUI();
  drawCTPreview();
}
function dcZoomFit() {
  dcZoomLevel = 1;
  dcUpdateZoomUI();
  drawCTPreview();
}

function dcCanvasCoords(e) {
```

- [ ] **Step 3: Reset zoom (and show/hide the toolbar) in `setDCMode()`**

Find (around line 10501):

```js
  const toolsRow = document.getElementById('dc-draw-tools');
  if (toolsRow) toolsRow.style.display = (mode==='draw') ? 'flex' : 'none';
  const roomToolsRow = document.getElementById('dc-room-tools');
  if (roomToolsRow) roomToolsRow.style.display = (mode==='room') ? 'flex' : 'none';
```

Replace with:

```js
  const toolsRow = document.getElementById('dc-draw-tools');
  if (toolsRow) toolsRow.style.display = (mode==='draw') ? 'flex' : 'none';
  const roomToolsRow = document.getElementById('dc-room-tools');
  if (roomToolsRow) roomToolsRow.style.display = (mode==='room') ? 'flex' : 'none';
  // Zoom (2026-08-12): out of scope for Room Layout (its own independent renderer) -- hide the
  // toolbar there, and always reset to 1 on any mode switch so a rep never lands on a mode with
  // a stale zoom level from whatever they were doing before.
  const zoomToolsRow = document.getElementById('dc-zoom-tools');
  if (zoomToolsRow) zoomToolsRow.style.display = (mode==='room') ? 'none' : 'flex';
  dcZoomLevel = 1;
  if (typeof dcUpdateZoomUI === 'function') dcUpdateZoomUI();
```

- [ ] **Step 4: Reset zoom in `dcClearPoly()`**

Find (around line 11031):

```js
  dcCutouts = []; dcSeams = []; dcChamferedCorners = {}; dcRaisedBar = null;
```

Replace with:

```js
  dcCutouts = []; dcSeams = []; dcChamferedCorners = {}; dcRaisedBar = null;
  dcZoomLevel = 1;
  if (typeof dcUpdateZoomUI === 'function') dcUpdateZoomUI();
```

- [ ] **Step 5: Reset zoom in `selectDrawShape()`**

Find (around line 11339):

```js
  drawCTPreview();
  // Fix (2026-08-12, caught in final review): a shape switch can deactivate a raised bar (or a
```

Replace with:

```js
  dcZoomLevel = 1;
  if (typeof dcUpdateZoomUI === 'function') dcUpdateZoomUI();
  drawCTPreview();
  // Fix (2026-08-12, caught in final review): a shape switch can deactivate a raised bar (or a
```

- [ ] **Step 6: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 7: Manual verification (browser console)**

With the `straight` preset selected:

```js
document.getElementById('dc-zoom-label').textContent;   // -> '100%'
document.getElementById('dc-zoom-out-btn').disabled;     // -> true (already at the floor)
dcZoomIn();
document.getElementById('dc-zoom-label').textContent;    // -> '125%'
document.getElementById('dc-zoom-out-btn').disabled;      // -> false
dcZoomIn(); dcZoomIn(); dcZoomIn(); dcZoomIn();           // repeated clicks clamp at the ceiling
dcZoomLevel;                                              // -> 3 (clamped, not runaway)
document.getElementById('dc-zoom-in-btn').disabled;       // -> true
dcZoomFit();
dcZoomLevel;                                              // -> 1
document.getElementById('dc-zoom-label').textContent;     // -> '100%'

dcZoomIn();
selectDrawShape('ushape');
dcZoomLevel;                                              // -> 1 (shape switch reset it)

dcZoomIn();
setDCMode('draw');
dcZoomLevel;                                              // -> 1 (mode switch reset it)
setDCMode('room');
document.getElementById('dc-zoom-tools').style.display;   // -> 'none' (hidden in Room mode)
setDCMode('preset');
document.getElementById('dc-zoom-tools').style.display;   // -> 'flex' (visible again)

dcZoomIn();
dcClearPoly();
dcZoomLevel;                                              // -> 1 (Clear Shape reset it)
```

Expected: matches every comment.

- [ ] **Step 8: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- zoom UI (In/Out/Fit buttons) + reset-on-shape/mode/clear"
```

---

### Task 4: Full verification sweep, live-verify, and push

**Files:** none (verification only)

- [ ] **Step 1: Full local syntax sweep**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0` across all blocks.

- [ ] **Step 2: Scoped Guardian checks**

Run: `python tools/duplicate_global_check.py stonedesk.html`
Expected: `DUPLICATE_NAMES:0`

Run: `python tools/nav_panel_check.py stonedesk.html`
Expected: `RESULT:PASS` (this feature doesn't touch panels/nav; a regression here would indicate an unintended change elsewhere).

Run: `python tools/sairn_dead_button_audit.py stonedesk.html`
Expected: no new findings referencing `dc-zoom-out-btn`, `dc-zoom-fit-btn`, `dc-zoom-in-btn`, `dcZoomIn`, `dcZoomOut`, `dcZoomFit`, `dcUpdateZoomUI`, `dcApplyZoomTransform`, `dcComputeCanvasHeight`.

Search: grep `stonedesk.html` for `console.log` inside the diff introduced by this plan — confirm none was left in.

- [ ] **Step 3: Run the full guardian review before commit/push**

Invoke the `sairn-guardian-v2` skill's full Check 0 + numbered checks against the diff, per CLAUDE.md's standing Push Protocol. Resolve any findings before proceeding.

- [ ] **Step 4: Combined end-to-end manual verification (browser console)**

The critical proof this plan needs that no console-only check above fully covers: **an actual hit-test lands correctly at a non-1x zoom**, driven through the real event path, not just the inverse-transform arithmetic.

```js
selectDrawShape('straight');
dcZoomLevel = 2; drawCTPreview();
// A raw screen-space click at the canvas's exact center pixel (its zoom-invariant anchor point,
// per Task 2's own proof) should, after dcCanvasCoords()'s inverse transform, land at the SAME
// logical point regardless of zoom -- and since drawCTPreview's own pad-based centering puts the
// straight run's rect roughly at the canvas center, that logical point should hit the rect.
const cv = document.getElementById('ct-canvas');
const rawPx = cv.width/2, rawPy = cv.height/2;
const logicalPx = (rawPx - cv.width/2*(1-dcZoomLevel)) / dcZoomLevel;
const logicalPy = (rawPy - cv.height/2*(1-dcZoomLevel)) / dcZoomLevel;
const hit = dcHitRect(logicalPx, logicalPy);
hit;                                    // -> a real, non-null rect (the straight run's own 'A' rect)
dcZoomFit();
```

Expected: `dcHitRect` returns a real, non-null rect at zoom 2x using coordinates run through the same inverse-transform formula `dcCanvasCoords()` uses internally — confirming the hit-test math is correct end-to-end, not just symmetric in isolation.

- [ ] **Step 5: Push**

```bash
git push origin main
```

- [ ] **Step 6: Live-verify against production**

Per CLAUDE.md's Push Protocol: drive `sairn.vercel.app/stonedesk`'s deployed functions directly (Playwright, using the license-gate workaround documented in `STONEDESK-SESSION79-HANDOFF.md` §3) and repeat Step 4's console checks against the live site, plus a visual screenshot at zoom 2x confirming the drawing visibly enlarges around the canvas center. Confirm the deployed file hash matches the pushed commit.

- [ ] **Step 7: Write the session handoff**

Use the `sairn-session-handoff` skill to record this feature's landing in a new `STONEDESK-SESSION-N-HANDOFF.md` (next number in sequence), per this project's standing convention. This closes out all three drawing-tool gaps from STONEDESK-SESSION79-HANDOFF.md's original open-items list (chamfer, raised bar, this one) — note that explicitly in the handoff.

---

## Self-Review Notes

- **Spec coverage:** height sizing (Task 1), zoom transform architecture — the highest-risk, most novel part of this plan (Task 2), zoom UI + all four reset triggers (Task 3), full verification including the one check that actually exercises the real hit-test path at a non-1x zoom (Task 4). Room Layout exclusion is enforced structurally (the toolbar hides there, and `dcZoomLevel` is always 1 by the time a rep is actually in that mode) rather than needing a guard inside `drawDCRoom()` itself — matches the spec's own reasoning.
- **Placeholder scan:** no TBD/TODO, no "add appropriate handling" — every step shows real code or a real runnable command with a stated expected result.
- **Type/name consistency:** `dcZoomLevel`, `DC_ZOOM_MIN`, `DC_ZOOM_MAX`, `DC_ZOOM_STEP`, `dcApplyZoomTransform`, `dcComputeCanvasHeight`, `dcZoomIn`/`dcZoomOut`/`dcZoomFit`, `dcUpdateZoomUI` are spelled identically everywhere they're produced (Tasks 1/2/3) and consumed (Tasks 2/3/4).
