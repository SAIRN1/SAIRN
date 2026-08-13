# StoneDesk Texture-Only Stone Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Drawing Tool's single hardcoded flat-color shape fill with a representative, procedurally-drawn stone color/pattern (Stone Type × Color Tone, picked independently of the pricing `#material` dropdown), rendered identically across Preset mode's rects and Custom Draw mode's polygon, persisted with saved quotes — with zero image assets and zero reference to any specific slab/quarry/product, so it stays unambiguously clear of the patent family covering actual-slab-photo visualization.

**Architecture:** One new procedural texture engine (`dcApplyStoneFill()` + `dcDrawStoneTexture()`, a seeded PRNG for stable-across-redraws layout, a 12-entry base-color table) called from every one of the 5 places `drawCTPreview()`/`drawDCPolygon()` currently hardcode the same flat placeholder fill. A new small button-picker in the Drawing Tool's existing "Job Details" card sets the two new globals driving it. Two new fields on the saved-quote-drawing-state feature's existing snapshot/restore functions carry the selection through Save/Load, matching every other job-detail field's existing pattern exactly.

**Tech Stack:** Vanilla JS, HTML5 Canvas 2D. No dependencies, no image assets, no build step.

## Global Constraints

- **Legal boundary, non-negotiable:** no image assets, no `ctx.createPattern()` over a raster image, no reference anywhere in code/comments/UI copy to a specific quarry, slab, or named commercial stone product. Only the generic category labels Granite/Marble/Quartzite/Engineered Quartz and Light/Medium/Dark.
- `dcStoneType`/`dcColorTone` default to `null`. Every rendering call site must fall back to today's exact `rgba(232,133,10,0.1)` fill (or `0.12` for `drawDCPolygon`'s own historically slightly-different alpha — preserve that exact value, don't unify it) when either is `null` or unrecognized — zero visual regression for anyone who never touches the picker.
- Texture layout must be deterministic given identical inputs (same bounding box + stoneType + colorTone) — no `Math.random()` — so `drawCTPreview()`'s frequent re-renders (on every keystroke) don't visibly jitter.
- The raised-bar overhang's own decorative fill (`stonedesk.html:11968`, `dcDrawRaisedBarIfActive()`) is explicitly OUT of scope — not one of the 5 shape-fill call sites this plan touches. Do not modify it.
- `node --check` must pass on every touched script block before any commit — run `python tools/checkblocks.py stonedesk.html` and confirm `FAILED_BLOCKS:0` (baseline before this plan: `TOTAL_BLOCKS:128`, `FAILED_BLOCKS:0`).
- Never bulk find-replace. Every edit below is a targeted, unique-context change.
- Room Layout mode (`dcMode==='room'`) is out of scope — its own independent renderer, untouched.
- `dcSnapshotDrawingState()`/`dcLoadDrawingState()` (already shipped, `stonedesk.html:13804`/`13869`) must gain exactly two new fields (`stoneType`, `colorTone`) using their exact existing patterns — no new persistence mechanism, no schema version bump (old snapshots simply lack the fields, which is indistinguishable from "unset").

---

## File Structure

Single file touched: `stonedesk.html`. No new files.

| Region (function) | Responsibility for this feature |
|---|---|
| ~L11841 (new, before `drawCTPreview`) | `dcStoneType`/`dcColorTone` globals, `STONE_TONE_COLORS` table, `dcHashSeed()`, `dcDrawStoneTexture()`, `dcApplyStoneFill()`. |
| ~L3801 (HTML, Job Details card) | New Stone Appearance picker: 4 stone-type buttons + 3 color-tone buttons. |
| (new, after Task 1's block) | `dcSetStoneType(type)`, `dcSetColorTone(tone)` — set the globals, update button active-state, redraw. |
| ~L11984 (straight/island fill) | Replace flat fillStyle+fill with `dcApplyStoneFill()`. |
| ~L12038-12056 (L-shape fill, both hasStub branches) | Same replacement, with a computed bounding box. |
| ~L12127-12152 (U-shape fill) | Same replacement, with a computed bounding box. |
| ~L12210 (galley/custom section-loop fill) | Same replacement, per-section rect. |
| ~L12242 (`drawDCPolygon`, Custom Draw closed-polygon fill) | Same replacement, with a computed bounding box from `pts`. |
| ~L13839-13854 (`dcSnapshotDrawingState`) | Add `stoneType`/`colorTone` to the returned object. |
| ~L13869-13911 (`dcLoadDrawingState`) | Restore `stoneType`/`colorTone` via the Task 2 setter functions. |

Line numbers are as of this plan's base commit and will drift by a few lines as earlier tasks land — every edit below is anchored to unique surrounding code, not the raw number.

---

### Task 1: Texture engine — globals, color table, seeded PRNG, texture + fill functions

**Files:**
- Modify: `stonedesk.html` (new code before `drawCTPreview()`, ~L11841)

**Interfaces:**
- Produces: `var dcStoneType` (string|null), `var dcColorTone` (string|null), `var STONE_TONE_COLORS` (object, keyed `stoneType.colorTone` → hex color string), `function dcApplyStoneFill(ctx, x, y, w, h)` (void — caller must have already built the path to fill via `ctx.beginPath()`+path ops before calling). Consumed by Task 2 (picker) and Task 3 (the 5 render call sites).
- Consumes: nothing new — standard Canvas 2D API only.

- [ ] **Step 1: Add the texture engine**

Find (around line 11837-11843):

```js
  });
}

// Drawing canvas with color-coded edges
function gN(id) { const e=document.getElementById(id); return e ? (parseFloat(e.value)||0) : 0; }
function getCBV(id) { const e=document.getElementById(id); return e ? e.checked : false; }

function drawCTPreview() {
```

Replace with:

```js
  });
}

// Stone appearance (2026-08-13): representative color/pattern fills for the Drawing Tool's
// rendered shapes, keyed by stone TYPE (pattern) and TONE (base color) -- deliberately never tied
// to any specific photographed slab, quarry, or named product; procedural canvas drawing only, no
// image assets. Both default to unset (null), which dcApplyStoneFill() below treats as "render
// today's flat placeholder" -- zero visual change for anyone who never touches the picker.
var dcStoneType = null;   // 'granite' | 'marble' | 'quartzite' | 'quartz' | null
var dcColorTone = null;   // 'light' | 'medium' | 'dark' | null

var STONE_TONE_COLORS = {
  granite:   { light: '#C9C2B8', medium: '#8B8478', dark: '#3A3733' },
  marble:    { light: '#F3EFE8', medium: '#D8D2C6', dark: '#5C5A55' },
  quartzite: { light: '#EDEAE2', medium: '#B8B2A4', dark: '#4A4844' },
  quartz:    { light: '#EDEDED', medium: '#9C9C9C', dark: '#2E2E2E' }
};

// Tiny deterministic PRNG (mulberry32) seeded from a string hash, so texture layout is stable
// across re-renders of the same inputs -- drawCTPreview() fires on nearly every keystroke, and a
// true Math.random() texture would visibly jitter on every redraw. Returns a function that
// produces successive pseudo-random floats in [0,1) from the same seed every time it's called.
function dcHashSeed(str) {
  var h = 1779033703 ^ str.length;
  for (var i = 0; i < str.length; i++) {
    h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return function() {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    h ^= h >>> 16;
    return (h >>> 0) / 4294967296;
  };
}

// Draws speckle dots (Granite, Engineered Quartz) or soft vein strokes (Marble, Quartzite) within
// the bounding box (x,y,w,h) -- the caller has already clipped the canvas to the real shape (see
// dcApplyStoneFill below), so this can safely draw across the whole bounding rectangle without
// worrying about spilling outside an L-shape/U-shape/polygon's actual boundary. Pattern density
// and style differ by stone type to match each one's real typical character, not an arbitrary
// style choice: granite's speckle is denser/coarser than quartz's fine manufactured fleck; marble
// shows more/thicker veining than quartzite's subtler veining.
function dcDrawStoneTexture(ctx, x, y, w, h, stoneType, colorTone) {
  if (w <= 0 || h <= 0) return;
  var rand = dcHashSeed(x.toFixed(1)+'|'+y.toFixed(1)+'|'+w.toFixed(1)+'|'+h.toFixed(1)+'|'+stoneType+'|'+colorTone);
  var tones = STONE_TONE_COLORS[stoneType];
  var speckleColors = [tones.light, tones.medium, tones.dark];
  if (stoneType === 'granite' || stoneType === 'quartz') {
    var count = Math.max(1, Math.round((w*h) / (stoneType === 'granite' ? 90 : 260)));
    var maxR = stoneType === 'granite' ? 1.6 : 0.9;
    for (var i = 0; i < count; i++) {
      var px = x + rand()*w, py = y + rand()*h, r = 0.4 + rand()*maxR;
      ctx.fillStyle = speckleColors[Math.floor(rand()*speckleColors.length)];
      ctx.globalAlpha = 0.35 + rand()*0.25;
      ctx.beginPath(); ctx.arc(px, py, r, 0, Math.PI*2); ctx.fill();
    }
    ctx.globalAlpha = 1;
  } else {
    var veinCount = stoneType === 'marble' ? (2 + Math.floor(rand()*3)) : (1 + Math.floor(rand()*2));
    var lineW = stoneType === 'marble' ? 1.1 : 0.6;
    for (var v = 0; v < veinCount; v++) {
      var sx = x + rand()*w, sy = y + rand()*h;
      var cx1 = x + rand()*w, cy1 = y + rand()*h;
      var cx2 = x + rand()*w, cy2 = y + rand()*h;
      var ex = x + rand()*w, ey = y + rand()*h;
      ctx.strokeStyle = speckleColors[rand() < 0.5 ? 0 : 2];
      ctx.globalAlpha = 0.18 + rand()*0.15;
      ctx.lineWidth = lineW;
      ctx.beginPath(); ctx.moveTo(sx, sy); ctx.bezierCurveTo(cx1, cy1, cx2, cy2, ex, ey); ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }
}

// Replaces the flat placeholder fillStyle+fill() every shape branch in drawCTPreview() (and
// drawDCPolygon) currently calls directly. The caller MUST have already built the shape's real
// path via ctx.beginPath()+ctx.rect()/moveTo()/lineTo()/closePath() BEFORE calling this -- it only
// replaces the "set a fillStyle and fill()" portion. Uses ctx.clip() (on whatever path is
// currently set) so texture primitives, which draw across the full (x,y,w,h) bounding box for
// simplicity, never spill outside the real shape whether it's a simple rect or an arbitrary
// polygon. Falls back to today's exact flat placeholder when no appearance is selected.
function dcApplyStoneFill(ctx, x, y, w, h) {
  if (!dcStoneType || !dcColorTone || !STONE_TONE_COLORS[dcStoneType] || !STONE_TONE_COLORS[dcStoneType][dcColorTone]) {
    ctx.fillStyle = 'rgba(232,133,10,0.1)';
    ctx.fill();
    return;
  }
  ctx.save();
  ctx.clip();
  ctx.fillStyle = STONE_TONE_COLORS[dcStoneType][dcColorTone];
  ctx.fillRect(x, y, w, h);
  dcDrawStoneTexture(ctx, x, y, w, h, dcStoneType, dcColorTone);
  ctx.restore();
}

// Drawing canvas with color-coded edges
function gN(id) { const e=document.getElementById(id); return e ? (parseFloat(e.value)||0) : 0; }
function getCBV(id) { const e=document.getElementById(id); return e ? e.checked : false; }

function drawCTPreview() {
```

- [ ] **Step 2: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 3: Manual verification (browser console)**

Open `stonedesk.html`, log in past the PIN/trial gate, open the Drawing Tool with any preset shape drawn, then in devtools console:

```js
dcStoneType; dcColorTone;                          // -> null, null
var cv = document.getElementById('ct-canvas'), ctx = cv.getContext('2d');
ctx.beginPath(); ctx.rect(10,10,100,80);
dcApplyStoneFill(ctx, 10, 10, 100, 80);             // no throw -- unset falls back to flat placeholder

dcStoneType = 'granite'; dcColorTone = 'dark';
ctx.beginPath(); ctx.rect(10,10,100,80);
dcApplyStoneFill(ctx, 10, 10, 100, 80);             // no throw -- draws base color + speckle within the clipped rect

// Stability: identical inputs must produce an identical layout (no Math.random() drift)
var r1 = dcHashSeed('10.0|10.0|100.0|80.0|granite|dark')();
var r2 = dcHashSeed('10.0|10.0|100.0|80.0|granite|dark')();
r1 === r2;                                          // -> true

dcStoneType = null; dcColorTone = null;             // reset for the next task's testing
drawCTPreview();
```

Expected: matches every comment — no throws, unset selection is a no-op visually, and the seeded PRNG is genuinely deterministic.

- [ ] **Step 4: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- procedural stone-texture engine (dcApplyStoneFill, dcDrawStoneTexture)"
```

---

### Task 2: Picker UI — Stone Type + Color Tone buttons

**Files:**
- Modify: `stonedesk.html` (HTML ~L3798-3802; new JS immediately after Task 1's `dcApplyStoneFill()`)

**Interfaces:**
- Consumes: `dcStoneType`, `dcColorTone`, `STONE_TONE_COLORS` (Task 1).
- Produces: `function dcSetStoneType(type)`, `function dcSetColorTone(tone)` — both accept `null` (deselects all buttons in that row, sets the global to `null`) as well as a real value. Consumed by the button `onclick` handlers in this task and by Task 4's restore path.

- [ ] **Step 1: Add the picker to the Job Details card**

Find (around line 3798-3802):

```html
          <div class="dm-card-title">Job Details</div>
          <div class="dm-field"><label>Customer / Job Name</label><input type="text" id="draw-job-name" placeholder="e.g. Johnson Kitchen"></div>
          <div class="dm-field"><label>Material</label><input type="text" id="draw-material" placeholder="e.g. Calacatta Gold Quartz 3cm"></div>
          <div class="dm-field"><label>Edge Profile</label><input type="text" id="draw-edge" placeholder="e.g. Eased, Ogee, Mitered"></div>
        </div>
```

Replace with:

```html
          <div class="dm-card-title">Job Details</div>
          <div class="dm-field"><label>Customer / Job Name</label><input type="text" id="draw-job-name" placeholder="e.g. Johnson Kitchen"></div>
          <div class="dm-field"><label>Material</label><input type="text" id="draw-material" placeholder="e.g. Calacatta Gold Quartz 3cm"></div>
          <div class="dm-field"><label>Edge Profile</label><input type="text" id="draw-edge" placeholder="e.g. Eased, Ogee, Mitered"></div>
          <div class="dm-field">
            <label>Stone Appearance <span style="color:var(--muted);font-weight:400;font-size:10px">(optional — representative preview, not an actual slab)</span></label>
            <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px">
              <button type="button" class="dc-stone-type-btn" data-stone-type="granite" onclick="dcSetStoneType('granite')" style="font-size:11px;padding:5px 10px;border-radius:6px;border:1px solid var(--border);background:rgba(255,255,255,0.04);color:var(--muted);cursor:pointer">Granite</button>
              <button type="button" class="dc-stone-type-btn" data-stone-type="marble" onclick="dcSetStoneType('marble')" style="font-size:11px;padding:5px 10px;border-radius:6px;border:1px solid var(--border);background:rgba(255,255,255,0.04);color:var(--muted);cursor:pointer">Marble</button>
              <button type="button" class="dc-stone-type-btn" data-stone-type="quartzite" onclick="dcSetStoneType('quartzite')" style="font-size:11px;padding:5px 10px;border-radius:6px;border:1px solid var(--border);background:rgba(255,255,255,0.04);color:var(--muted);cursor:pointer">Quartzite</button>
              <button type="button" class="dc-stone-type-btn" data-stone-type="quartz" onclick="dcSetStoneType('quartz')" style="font-size:11px;padding:5px 10px;border-radius:6px;border:1px solid var(--border);background:rgba(255,255,255,0.04);color:var(--muted);cursor:pointer">Engineered Quartz</button>
            </div>
            <div style="display:flex;gap:6px;flex-wrap:wrap">
              <button type="button" class="dc-color-tone-btn" data-color-tone="light" onclick="dcSetColorTone('light')" style="font-size:11px;padding:5px 10px;border-radius:6px;border:1px solid var(--border);background:rgba(255,255,255,0.04);color:var(--muted);cursor:pointer">Light</button>
              <button type="button" class="dc-color-tone-btn" data-color-tone="medium" onclick="dcSetColorTone('medium')" style="font-size:11px;padding:5px 10px;border-radius:6px;border:1px solid var(--border);background:rgba(255,255,255,0.04);color:var(--muted);cursor:pointer">Medium</button>
              <button type="button" class="dc-color-tone-btn" data-color-tone="dark" onclick="dcSetColorTone('dark')" style="font-size:11px;padding:5px 10px;border-radius:6px;border:1px solid var(--border);background:rgba(255,255,255,0.04);color:var(--muted);cursor:pointer">Dark</button>
            </div>
          </div>
        </div>
```

- [ ] **Step 2: Add `dcSetStoneType()`/`dcSetColorTone()` right after `dcApplyStoneFill()`**

Find (the exact tail end of Task 1's new code — around line 11930-11934):

```js
  ctx.save();
  ctx.clip();
  ctx.fillStyle = STONE_TONE_COLORS[dcStoneType][dcColorTone];
  ctx.fillRect(x, y, w, h);
  dcDrawStoneTexture(ctx, x, y, w, h, dcStoneType, dcColorTone);
  ctx.restore();
}

// Drawing canvas with color-coded edges
```

Replace with:

```js
  ctx.save();
  ctx.clip();
  ctx.fillStyle = STONE_TONE_COLORS[dcStoneType][dcColorTone];
  ctx.fillRect(x, y, w, h);
  dcDrawStoneTexture(ctx, x, y, w, h, dcStoneType, dcColorTone);
  ctx.restore();
}

// Sets the selected Stone Type (or clears it with a null argument, used by dcLoadDrawingState()
// when restoring a snapshot saved before this feature existed), updates the picker buttons' active
// styling to match (same active/inactive style-toggle pattern selectDrawShape() already uses for
// its own shape buttons), and redraws.
function dcSetStoneType(type) {
  dcStoneType = type;
  document.querySelectorAll('.dc-stone-type-btn').forEach(function(btn){
    if (btn.getAttribute('data-stone-type') === type) { btn.style.background='var(--ar)'; btn.style.borderColor='var(--ab)'; btn.style.color='var(--a)'; }
    else { btn.style.background='rgba(255,255,255,0.04)'; btn.style.borderColor='var(--border)'; btn.style.color='var(--muted)'; }
  });
  if (typeof drawCTPreview === 'function') drawCTPreview();
}
// Mirror of dcSetStoneType() for Color Tone -- see that function's comment.
function dcSetColorTone(tone) {
  dcColorTone = tone;
  document.querySelectorAll('.dc-color-tone-btn').forEach(function(btn){
    if (btn.getAttribute('data-color-tone') === tone) { btn.style.background='var(--ar)'; btn.style.borderColor='var(--ab)'; btn.style.color='var(--a)'; }
    else { btn.style.background='rgba(255,255,255,0.04)'; btn.style.borderColor='var(--border)'; btn.style.color='var(--muted)'; }
  });
  if (typeof drawCTPreview === 'function') drawCTPreview();
}

// Drawing canvas with color-coded edges
```

- [ ] **Step 3: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 4: Manual verification (browser console)**

```js
document.querySelectorAll('.dc-stone-type-btn').length;   // -> 4
document.querySelectorAll('.dc-color-tone-btn').length;   // -> 3

dcSetStoneType('marble');
dcStoneType;                                                // -> 'marble'
document.querySelector('.dc-stone-type-btn[data-stone-type="marble"]').style.background;  // -> 'var(--ar)' (matches selectDrawShape's active-button convention)

dcSetColorTone('light');
dcColorTone;                                                // -> 'light'

dcSetStoneType(null);
dcStoneType;                                                // -> null
document.querySelector('.dc-stone-type-btn[data-stone-type="marble"]').style.background;  // -> 'rgba(255,255,255,0.04)' (deselected)

dcSetColorTone(null);
```

Expected: matches every comment — 4 stone-type buttons, 3 color-tone buttons, both setters toggle the right global and the right button's active styling, and `null` cleanly deselects.

- [ ] **Step 5: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- Stone Appearance picker (Stone Type + Color Tone buttons)"
```

---

### Task 3: Wire the texture engine into all 5 shape-fill call sites

**Files:**
- Modify: `stonedesk.html` (`drawCTPreview()`'s straight/island ~L11984, L-shape ~L12038-12056, U-shape ~L12127-12152, galley/custom ~L12210; `drawDCPolygon()` ~L12242)

**Interfaces:**
- Consumes: `dcApplyStoneFill(ctx, x, y, w, h)` (Task 1). No new interfaces produced — this task only changes rendering call sites, nothing else depends on it.

- [ ] **Step 1: Straight / Island**

Find (around line 11984):

```js
    ctx.fillStyle='rgba(232,133,10,0.1)'; ctx.beginPath(); ctx.rect(x,y,aL*sc,aD*sc); ctx.fill();
```

Replace with:

```js
    ctx.beginPath(); ctx.rect(x,y,aL*sc,aD*sc); dcApplyStoneFill(ctx, x, y, aL*sc, aD*sc);
```

- [ ] **Step 2: L-shape (both `hasStub` branches share one bounding box)**

Find (around line 12038-12056):

```js
    ctx.fillStyle='rgba(232,133,10,0.1)';
    if (hasStub) {
      ctx.beginPath();
      ctx.moveTo(bx,by);
      ctx.lineTo(bx+bw,by);
      if (chamferABOffPx > 0) {
        ctx.lineTo(bx+bw, ay-chamferABOffPx);
        ctx.lineTo(bx+bw+chamferABOffPx, ay);
      } else {
        ctx.lineTo(bx+bw, ay);
      }
      ctx.lineTo(ax+aw, ay);
      ctx.lineTo(ax+aw, ay+ah);
      ctx.lineTo(ax, ay+ah);
      ctx.closePath();
      ctx.fill();
    } else {
      ctx.beginPath(); ctx.rect(ax,ay,aw,ah); ctx.fill();
    }
```

Replace with:

```js
    // Stone appearance (2026-08-13): both branches share one bounding box covering the whole L
    // (A run + B stub when present), so the texture is one continuous pattern across the notch
    // rather than two independently-seeded regions that would visibly seam at the A/B join.
    const lshapeBoundsX = Math.min(ax, bx), lshapeBoundsY = Math.min(ay, by);
    const lshapeBoundsW = Math.max(ax+aw, bx+bw) - lshapeBoundsX;
    const lshapeBoundsH = Math.max(ay+ah, by+bh) - lshapeBoundsY;
    if (hasStub) {
      ctx.beginPath();
      ctx.moveTo(bx,by);
      ctx.lineTo(bx+bw,by);
      if (chamferABOffPx > 0) {
        ctx.lineTo(bx+bw, ay-chamferABOffPx);
        ctx.lineTo(bx+bw+chamferABOffPx, ay);
      } else {
        ctx.lineTo(bx+bw, ay);
      }
      ctx.lineTo(ax+aw, ay);
      ctx.lineTo(ax+aw, ay+ah);
      ctx.lineTo(ax, ay+ah);
      ctx.closePath();
      dcApplyStoneFill(ctx, lshapeBoundsX, lshapeBoundsY, lshapeBoundsW, lshapeBoundsH);
    } else {
      ctx.beginPath(); ctx.rect(ax,ay,aw,ah); dcApplyStoneFill(ctx, ax, ay, aw, ah);
    }
```

- [ ] **Step 3: U-shape**

Find (around line 12127-12152):

```js
    ctx.fillStyle='rgba(232,133,10,0.1)';
    ctx.beginPath();
    ctx.moveTo(lx, ly+leftH);
    ctx.lineTo(lx, by);
    ctx.lineTo(lx+backW, by);
    ctx.lineTo(rx+rightW, ry+rightH);
    ctx.lineTo(rx, ry+rightH);
    if (offBR > 0) {
      ctx.lineTo(rx, by+backH+offBR);
      // Fix (2026-08-12, caught in post-hoc review): this second substituted point must lie on
      // the "Back front" segment, which runs from rx toward lx+leftW -- i.e. DECREASING x from
      // rx (lx+leftW < rx). The original rx+offBR moved the wrong direction, off the actual
      // edge and into the right leg's own top boundary instead of a valid chamfer cut.
      ctx.lineTo(rx-offBR, by+backH);
    } else {
      ctx.lineTo(rx, by+backH);
    }
    if (offBL > 0) {
      ctx.lineTo(lx+leftW+offBL, by+backH);
      ctx.lineTo(lx+leftW, by+backH+offBL);
    } else {
      ctx.lineTo(lx+leftW, by+backH);
    }
    ctx.lineTo(lx+leftW, ly+leftH);
    ctx.closePath();
    ctx.fill();
```

Replace with:

```js
    // Stone appearance (2026-08-13): one bounding box covering all three runs (Back/Left/Right),
    // same reasoning as the L-shape above -- one continuous pattern across the whole U, not three
    // independently-seeded regions.
    const ushapeBoundsX = Math.min(bx, lx, rx), ushapeBoundsY = Math.min(by, ly, ry);
    const ushapeBoundsW = Math.max(bx+backW, lx+leftW, rx+rightW) - ushapeBoundsX;
    const ushapeBoundsH = Math.max(by+backH, ly+leftH, ry+rightH) - ushapeBoundsY;
    ctx.beginPath();
    ctx.moveTo(lx, ly+leftH);
    ctx.lineTo(lx, by);
    ctx.lineTo(lx+backW, by);
    ctx.lineTo(rx+rightW, ry+rightH);
    ctx.lineTo(rx, ry+rightH);
    if (offBR > 0) {
      ctx.lineTo(rx, by+backH+offBR);
      // Fix (2026-08-12, caught in post-hoc review): this second substituted point must lie on
      // the "Back front" segment, which runs from rx toward lx+leftW -- i.e. DECREASING x from
      // rx (lx+leftW < rx). The original rx+offBR moved the wrong direction, off the actual
      // edge and into the right leg's own top boundary instead of a valid chamfer cut.
      ctx.lineTo(rx-offBR, by+backH);
    } else {
      ctx.lineTo(rx, by+backH);
    }
    if (offBL > 0) {
      ctx.lineTo(lx+leftW+offBL, by+backH);
      ctx.lineTo(lx+leftW, by+backH+offBL);
    } else {
      ctx.lineTo(lx+leftW, by+backH);
    }
    ctx.lineTo(lx+leftW, ly+leftH);
    ctx.closePath();
    dcApplyStoneFill(ctx, ushapeBoundsX, ushapeBoundsY, ushapeBoundsW, ushapeBoundsH);
```

- [ ] **Step 4: Galley / Custom section loop**

Find (around line 12210):

```js
      ctx.fillStyle='rgba(232,133,10,0.1)'; ctx.beginPath(); ctx.rect(pad,cy,sl*sc,sd*sc); ctx.fill();
```

Replace with:

```js
      ctx.beginPath(); ctx.rect(pad,cy,sl*sc,sd*sc); dcApplyStoneFill(ctx, pad, cy, sl*sc, sd*sc);
```

- [ ] **Step 5: Custom Draw mode's closed polygon (`drawDCPolygon`)**

Find (around line 12242):

```js
  if (dcPolyClosed && pts.length>=3) {
    ctx.fillStyle='rgba(232,133,10,0.12)';
    ctx.beginPath(); ctx.moveTo(pts[0].x,pts[0].y);
    for (let i=1;i<pts.length;i++) ctx.lineTo(pts[i].x,pts[i].y);
    ctx.closePath(); ctx.fill();
  }
```

Replace with:

```js
  if (dcPolyClosed && pts.length>=3) {
    // Stone appearance (2026-08-13): bounding box of the real polygon points, same clip-based
    // dcApplyStoneFill() used by every preset-shape branch above -- works unmodified for an
    // arbitrary polygon since ctx.clip() accepts any path, not just rects.
    let polyMinX=pts[0].x, polyMinY=pts[0].y, polyMaxX=pts[0].x, polyMaxY=pts[0].y;
    for (let pi=1; pi<pts.length; pi++) {
      if (pts[pi].x < polyMinX) polyMinX = pts[pi].x;
      if (pts[pi].x > polyMaxX) polyMaxX = pts[pi].x;
      if (pts[pi].y < polyMinY) polyMinY = pts[pi].y;
      if (pts[pi].y > polyMaxY) polyMaxY = pts[pi].y;
    }
    // Falls back to this branch's own historical 0.12 alpha (not the 0.1 every preset-shape
    // branch uses) when unset -- dcApplyStoneFill() always uses 0.1, a pre-existing, deliberately
    // preserved inconsistency, not something this feature should silently unify.
    if (!dcStoneType || !dcColorTone || !STONE_TONE_COLORS[dcStoneType] || !STONE_TONE_COLORS[dcStoneType][dcColorTone]) {
      ctx.fillStyle='rgba(232,133,10,0.12)';
      ctx.beginPath(); ctx.moveTo(pts[0].x,pts[0].y);
      for (let i=1;i<pts.length;i++) ctx.lineTo(pts[i].x,pts[i].y);
      ctx.closePath(); ctx.fill();
    } else {
      ctx.beginPath(); ctx.moveTo(pts[0].x,pts[0].y);
      for (let i=1;i<pts.length;i++) ctx.lineTo(pts[i].x,pts[i].y);
      ctx.closePath();
      dcApplyStoneFill(ctx, polyMinX, polyMinY, polyMaxX-polyMinX, polyMaxY-polyMinY);
    }
  }
```

- [ ] **Step 6: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 7: Manual verification (browser console)**

```js
// Baseline: unset selection must render byte-identical to before this task.
dcStoneType = null; dcColorTone = null;
selectDrawShape('straight');
document.getElementById('da-len').value = 96; document.getElementById('da-dep').value = 25.5;
drawCTPreview();   // should look exactly as it always has -- flat placeholder fill

// Each shape, textured:
dcSetStoneType('granite'); dcSetColorTone('dark');
selectDrawShape('straight'); document.getElementById('da-len').value=96; document.getElementById('da-dep').value=25.5; drawCTPreview();
selectDrawShape('lshape'); document.getElementById('da-len').value=96; document.getElementById('da-dep').value=25.5; document.getElementById('db-len').value=72; document.getElementById('db-dep').value=25.5; drawCTPreview();
selectDrawShape('ushape'); document.getElementById('da-len').value=72; document.getElementById('da-dep').value=25.5; document.getElementById('db-len').value=84; document.getElementById('db-dep').value=25.5; document.getElementById('dc-len').value=72; document.getElementById('dc-dep').value=25.5; drawCTPreview();
// All three calls above must complete with no throw -- confirms the bounding-box math for the
// unified L-shape/U-shape fill polygons doesn't error at typical dimensions.

// Stability: re-rendering the identical shape twice must be pixel-identical (no jitter).
const cv = document.getElementById('ct-canvas'), ctx = cv.getContext('2d');
drawCTPreview();
const frame1 = ctx.getImageData(0,0,cv.width,cv.height).data.join(',');
drawCTPreview();
const frame2 = ctx.getImageData(0,0,cv.width,cv.height).data.join(',');
frame1 === frame2;   // -> true

dcSetStoneType(null); dcSetColorTone(null);
```

Expected: matches every comment — no regression when unset, no throws across straight/L/U-shape at real dimensions, and two consecutive renders of the identical shape+selection produce pixel-identical output.

- [ ] **Step 8: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- wire stone-texture fill into all 5 drawing-tool shape renderers"
```

---

### Task 4: Persistence — capture and restore with saved quotes

**Files:**
- Modify: `stonedesk.html` (`dcSnapshotDrawingState()` ~L13839-13854, `dcLoadDrawingState()` ~L13869-13911)

**Interfaces:**
- Consumes: `dcStoneType`, `dcColorTone` (Task 1); `dcSetStoneType()`, `dcSetColorTone()` (Task 2).
- Produces: two new fields (`stoneType`, `colorTone`) on the object `dcSnapshotDrawingState()` returns — consumed only by `dcLoadDrawingState()` and, indirectly, by the already-shipped History detail modal (which does not need to change — it doesn't currently display `stoneType`/`colorTone`, and this plan doesn't add that display; it only needs the fields to round-trip correctly).

- [ ] **Step 1: Add `stoneType`/`colorTone` to the snapshot**

Find (around line 13839-13854):

```js
    return {
      schemaVersion: 1,
      ctShape: (typeof ctShape !== 'undefined') ? ctShape : '',
      dims: dims,
      dcPoly: JSON.parse(JSON.stringify((typeof dcPoly !== 'undefined') ? dcPoly : [])),
      dcMode: (typeof dcMode !== 'undefined') ? dcMode : 'preset',
      dcPolyClosed: (typeof dcPolyClosed !== 'undefined') ? dcPolyClosed : false,
      dcCutouts: JSON.parse(JSON.stringify((typeof dcCutouts !== 'undefined') ? dcCutouts : [])),
      dcSeams: JSON.parse(JSON.stringify((typeof dcSeams !== 'undefined') ? dcSeams : [])),
      dcRaisedBar: (typeof dcRaisedBar !== 'undefined' && dcRaisedBar) ? JSON.parse(JSON.stringify(dcRaisedBar)) : null,
      dcChamferedCorners: JSON.parse(JSON.stringify((typeof dcChamferedCorners !== 'undefined') ? dcChamferedCorners : {})),
      dcEdgeTypes: JSON.parse(JSON.stringify((typeof dcEdgeTypes !== 'undefined') ? dcEdgeTypes : {})),
      extras: extras,
      jobDetails: jobDetails,
      summary: summary
    };
```

Replace with:

```js
    return {
      schemaVersion: 1,
      ctShape: (typeof ctShape !== 'undefined') ? ctShape : '',
      dims: dims,
      dcPoly: JSON.parse(JSON.stringify((typeof dcPoly !== 'undefined') ? dcPoly : [])),
      dcMode: (typeof dcMode !== 'undefined') ? dcMode : 'preset',
      dcPolyClosed: (typeof dcPolyClosed !== 'undefined') ? dcPolyClosed : false,
      dcCutouts: JSON.parse(JSON.stringify((typeof dcCutouts !== 'undefined') ? dcCutouts : [])),
      dcSeams: JSON.parse(JSON.stringify((typeof dcSeams !== 'undefined') ? dcSeams : [])),
      dcRaisedBar: (typeof dcRaisedBar !== 'undefined' && dcRaisedBar) ? JSON.parse(JSON.stringify(dcRaisedBar)) : null,
      dcChamferedCorners: JSON.parse(JSON.stringify((typeof dcChamferedCorners !== 'undefined') ? dcChamferedCorners : {})),
      dcEdgeTypes: JSON.parse(JSON.stringify((typeof dcEdgeTypes !== 'undefined') ? dcEdgeTypes : {})),
      // Stone appearance (2026-08-13): purely visual, doesn't affect pricing or the cut sheet, but
      // captured anyway so a reloaded quote's canvas looks the same as when it was saved -- same
      // reasoning and same pattern as every other job-detail field above.
      stoneType: (typeof dcStoneType !== 'undefined') ? dcStoneType : null,
      colorTone: (typeof dcColorTone !== 'undefined') ? dcColorTone : null,
      extras: extras,
      jobDetails: jobDetails,
      summary: summary
    };
```

- [ ] **Step 2: Restore `stoneType`/`colorTone`**

Find (around line 13898-13901):

```js
    dcEdgeTypes = JSON.parse(JSON.stringify(state.dcEdgeTypes || {}));
    dcHistory = [];

    if (state.dcMode === 'draw' && typeof setDCMode === 'function') setDCMode('draw');
```

Replace with:

```js
    dcEdgeTypes = JSON.parse(JSON.stringify(state.dcEdgeTypes || {}));
    dcHistory = [];

    // Stone appearance (2026-08-13): reuse the real setter functions (not a direct global
    // assignment) so the picker's button active-state stays in sync with the restored value --
    // an old snapshot with no stoneType/colorTone field passes `undefined`, which these setters
    // already treat as null-safe as any other falsy input.
    if (typeof dcSetStoneType === 'function') dcSetStoneType(state.stoneType || null);
    if (typeof dcSetColorTone === 'function') dcSetColorTone(state.colorTone || null);

    if (state.dcMode === 'draw' && typeof setDCMode === 'function') setDCMode('draw');
```

- [ ] **Step 3: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 4: Manual verification (browser console)**

```js
selectDrawShape('straight');
document.getElementById('da-len').value = 96; document.getElementById('da-dep').value = 25.5;
dcSetStoneType('marble'); dcSetColorTone('light');
drawCTPreview(); calcDrawing();
var snap = dcSnapshotDrawingState();
snap.stoneType;   // -> 'marble'
snap.colorTone;   // -> 'light'

dcSetStoneType('granite'); dcSetColorTone('dark');   // simulate a different live selection
dcLoadDrawingState(snap);                             // -> true
dcStoneType;   // -> 'marble'  (restored, not the pre-load 'granite')
dcColorTone;   // -> 'light'
document.querySelector('.dc-stone-type-btn[data-stone-type="marble"]').style.background;  // -> 'var(--ar)' (button UI back in sync)

// Old-format snapshot (no stoneType/colorTone field at all) must restore cleanly to unset:
var oldSnap = JSON.parse(JSON.stringify(snap));
delete oldSnap.stoneType; delete oldSnap.colorTone;
dcLoadDrawingState(oldSnap);   // -> true, no throw
dcStoneType;   // -> null
dcColorTone;   // -> null

dcSetStoneType(null); dcSetColorTone(null);
```

Expected: matches every comment — a real snapshot round-trips both fields exactly, a pre-feature-format snapshot (missing the fields) restores cleanly to unset with no throw, and the picker UI's active-button state stays in sync with whatever was actually restored.

- [ ] **Step 5: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- persist stone appearance selection with saved quotes"
```

---

### Task 5: Full verification sweep, live-verify, and push

**Files:** none (verification only)

- [ ] **Step 1: Full local syntax sweep**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0` across all blocks.

- [ ] **Step 2: Scoped Guardian checks**

Run: `python tools/duplicate_global_check.py stonedesk.html`
Expected: `DUPLICATE_NAMES:0`

Run: `python tools/div_balance_check.py stonedesk.html`
Expected: `RESULT:PASS`

Run: `python tools/nav_panel_check.py stonedesk.html`
Expected: `RESULT:PASS` (this feature doesn't touch panels/nav; a regression here would indicate an unintended change elsewhere).

Run: `python tools/sairn_dead_button_audit.py stonedesk.html`
Expected: no new findings referencing `dc-stone-type-btn`, `dc-color-tone-btn`, `dcSetStoneType`, `dcSetColorTone`, `dcApplyStoneFill`.

Search: grep `stonedesk.html` for `console.log` inside the diff introduced by this plan — confirm none was left in.

Search: grep `stonedesk.html`'s diff for the words `slab`, `quarry`, or any specific stone product name (e.g. `Calacatta`, `Carrara`) inside code/comments this plan ADDED — confirm none, per the legal-boundary Global Constraint (existing pre-feature uses like `draw-material`'s placeholder text are untouched and don't count).

- [ ] **Step 3: Run the full Guardian review before commit/push**

Invoke the `sairn-guardian-v2` skill's full Check 0 + numbered checks against the diff, per CLAUDE.md's standing Push Protocol.

- [ ] **Step 4: Combined end-to-end manual verification (browser console)**

```js
selectDrawShape('ushape');
document.getElementById('da-len').value = 72; document.getElementById('da-dep').value = 25.5;
document.getElementById('db-len').value = 84; document.getElementById('db-dep').value = 25.5;
document.getElementById('dc-len').value = 72; document.getElementById('dc-dep').value = 25.5;
dcSetStoneType('quartzite'); dcSetColorTone('medium');
drawCTPreview(); calcDrawing();
document.getElementById('client-name').value = 'Texture Round Trip QA';
sdQuoteSaveHistory();

var h = JSON.parse(localStorage.getItem('sd_quote_history'));
var saved = h[0];
saved.drawingState.stoneType;   // -> 'quartzite'
saved.drawingState.colorTone;   // -> 'medium'

selectDrawShape('straight'); dcSetStoneType(null); dcSetColorTone(null); drawCTPreview();  // simulate navigating away

sdHistoryRender();
sdHistoryView(saved.id);
window.confirm = () => true;
sdHistoryLoadIntoDrawingTool();
ctShape;         // -> 'ushape'
dcStoneType;     // -> 'quartzite'
dcColorTone;     // -> 'medium'
```

Expected: matches every comment — a real save/reload/load cycle through actual `localStorage` reproduces the exact original stone-appearance selection, same standard as every other field the prior feature's own Task 4 verified.

- [ ] **Step 5: Push**

```bash
git push origin main
```

- [ ] **Step 6: Live-verify against production**

Per CLAUDE.md's Push Protocol: confirm the deployed file hash matches the pushed commit (normalize line endings before comparing), and repeat Step 4's console checks against `sairn.vercel.app/stonedesk` directly.

- [ ] **Step 7: Write the session handoff**

Use the `sairn-session-handoff` skill to record this feature's landing in a new `STONEDESK-SESSION-N-HANDOFF.md` (next number in sequence).

---

## Self-Review Notes

- **Spec coverage:** the texture engine (Task 1), picker UI (Task 2), all 5 render call sites including both L-shape/U-shape's unified-fill-polygon bounding-box math (Task 3), and save/reload persistence (Task 4) together cover every section of the design spec — Architecture, Picker UI, Rendering, Stability, Persistence, and the explicit legal-boundary exclusions (no images, no slab/quarry references, Room Layout excluded, raised-bar's own fill excluded). The full save→reload→load round-trip (Task 5 Step 4) is the concrete proof of the spec's "reloaded quote's canvas looks the same as when it was saved" requirement.
- **Placeholder scan:** no TBD/TODO, no "add appropriate handling" — every step shows real code (matching the actual current file content, re-read immediately before writing this plan) or a real runnable console check with a stated expected result.
- **Type/name consistency:** `dcStoneType`/`dcColorTone`/`STONE_TONE_COLORS`/`dcHashSeed`/`dcDrawStoneTexture`/`dcApplyStoneFill` (Task 1), `dcSetStoneType`/`dcSetColorTone` (Task 2), and the `stoneType`/`colorTone` field names on the `dcSnapshotDrawingState()`/`dcLoadDrawingState()` object (Task 4) are spelled identically everywhere they're produced and consumed across all 5 tasks.
