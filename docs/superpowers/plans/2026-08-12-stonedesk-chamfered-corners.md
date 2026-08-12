# StoneDesk — Chamfered 45° Inside Corners Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a rep chamfer (45°-clip) the inside corner(s) of an L-shape or U-shape preset countertop, with a real setback in inches, a fill-clipped canvas render, real edge-LF pricing wired into `calc()`'s total, and a line on the printed cut sheet.

**Architecture:** Pure client-side addition to the single `stonedesk.html` app. One new keyed data object (`dcChamferedCorners`) drives three existing subsystems it plugs into: `drawCTPreview()`'s L-shape/U-shape rendering (rect fills → one unified fill polygon with a notch), `calcDrawing()` → `dcSyncLiveToQuoteEngine()` → `calc()`'s pricing pipeline (mirrors the just-landed seam-cost fix exactly), and `printDrawCutSheet()`'s printed output. No new files, no build step, no server/API changes.

**Tech Stack:** Vanilla JS, HTML5 Canvas 2D. No dependencies added.

## Global Constraints

- `node --check` must pass on every touched script block before any commit — run `python tools/checkblocks.py stonedesk.html` and confirm `FAILED_BLOCKS:0` (baseline before this plan: `TOTAL_BLOCKS:128`, `FAILED_BLOCKS:0`).
- Never bulk find-replace. Every edit below is a targeted, unique-context change.
- Preset shapes only (L-shape's one inside corner, U-shape's two). Custom Draw mode is explicitly out of scope — do not touch `drawDCPolygon()`.
- Any angle other than 45° and any radius/rounded-corner treatment are out of scope — do not add configurability for those.
- `colorEdge()`'s existing per-edge stroke calls in `drawCTPreview()`'s L-shape and U-shape branches must NOT be modified — only new code is added around them (unified fill polygon, new diagonal stroke calls). This is a deliberate constraint from the design spec to keep zero risk to the L-shape rotation-mismap and U-shape Back-run-drag fixes already live in that same code.
- Zero/blank setback = not chamfered (same as unchecked), never a zero-length degenerate chamfer.
- Setback is clamped to 40% (`DC_CHAMFER_MAX_FRACTION = 0.4`) of the shorter of the two adjacent run lengths, both at input time (rep typing) and at render time (defensive re-clamp in case dimensions later shrink) — clamp, never silently let the fill polygon self-intersect.
- Toggling a corner off must zero its cost contribution the same tick (`calcDrawing()`'s existing re-fire-on-any-edit path), not just at the next unrelated recompute.
- Before the final push: full `sairn-guardian-v2` Check 0 (per CLAUDE.md's standing Push Protocol) and live-verification against `sairn.vercel.app/stonedesk`, not just a clean local syntax check.

---

## File Structure

Single file touched: `stonedesk.html`. No new files.

| Region (function) | Responsibility for this feature |
|---|---|
| ~L10161 (`var DC_SEAM_EDGE_COST`) | New `var DC_CHAMFER_EDGE_COST = 0;` — the pricing hand-off variable `calc()` reads. |
| ~L11316 (`buildEdgeAssignmentArea`) | New data model (`dcChamferedCorners`), clamp/key helper functions, and the per-corner checkbox+setback UI controls. |
| ~L11506 (`drawCTPreview`, L-shape branch) | Unified fill polygon with chamfer notch + diagonal stroke, L-shape's one inside corner. |
| ~L11555 (`drawCTPreview`, U-shape branch) | Same, U-shape's two inside corners. |
| ~L11002 (`dcClearPoly`) | Reset `dcChamferedCorners = {}` alongside the existing `dcCutouts`/`dcSeams` reset. |
| ~L12852 (`dcSeamPricingSummary`) | New `dcChamferPricingSummary()` sibling function. |
| ~L12909 (`calcDrawing`) | Compute `chamferEdgeCost`, add its results-panel metric card, pass it to `dcSyncLiveToQuoteEngine()`. |
| ~L13042 (`dcSyncLiveToQuoteEngine`) | Accept `chamferEdgeCost` param, assign `DC_CHAMFER_EDGE_COST`. |
| ~L9864 (`calc`) | Read `DC_CHAMFER_EDGE_COST`, add to `rawSubtotal`, `lastCalc`, and the `lines[]` quote breakdown. |
| ~L13124 (`printDrawCutSheet`) | New "Chamfered Corners" row. |

Line numbers are as of this plan's base commit (`702acff`) and will drift by a few lines as earlier tasks land — every edit below is anchored to unique surrounding code, not the raw number, so this is fine to execute in order.

---

### Task 1: Data model, clamp helpers, and edge-assignment UI controls

**Files:**
- Modify: `stonedesk.html` (four locations, all within the app's single main `<script>` block)

**Interfaces:**
- Produces: `var dcChamferedCorners` (`{ [cornerKey]: { setbackIn: number } }`), `var DC_CHAMFER_MAX_FRACTION` (`0.4`), `function dcChamferKeyFor(shape, edgeName)`, `function dcChamferAdjacentRunsIn(cornerKey)`, `function dcChamferMaxSetbackIn(cornerKey)`, `function dcSetChamferSetback(cornerKey, rawVal, cbEl, inputEl)` — all consumed by Tasks 2–5.
- Consumes: existing globals `gN(id)`, `showToast(msg)`, `ctShape`, `drawCTPreview()`, `calcDrawing()`, `EDGE_COLORS`.

- [ ] **Step 1: Add the data model and helper functions**

In `stonedesk.html`, find (around line 10161):

```js
var DC_SEAM_EDGE_COST = 0;
var TYPICAL = {
```

Replace with:

```js
var DC_SEAM_EDGE_COST = 0;
// Chamfered-corner edge cost, synced from dcChamferedCorners via dcSyncLiveToQuoteEngine() --
// same disconnect-bug-avoidance pattern as DC_SEAM_EDGE_COST above, built in correctly from the
// start rather than fixed after the fact.
var DC_CHAMFER_EDGE_COST = 0;
var TYPICAL = {
```

Then find (around line 11314, right before `buildEdgeAssignmentArea`):

```js
// Build edge assignment selectors
function buildEdgeAssignmentArea() {
```

Replace with:

```js
// Chamfered corners (2026-08-12): preset-shape inside-corner 45deg chamfers, keyed by
// shape+corner so switching shapes (or away and back) can't carry stale corner state onto a
// shape it doesn't apply to. Key absence = square corner (default, unchanged behavior).
var dcChamferedCorners = {}; // keyed 'lshape-AB' | 'ushape-BackLeft' | 'ushape-BackRight' -> { setbackIn: number }
// A setback can't exceed this fraction of the shorter adjacent run, or the substituted fill
// point would pass the run's far end and produce a self-intersecting notch instead of a clean
// one -- same "flag, don't silently corrupt the geometry" posture as the sink-fit check.
var DC_CHAMFER_MAX_FRACTION = 0.4;

function dcChamferKeyFor(shape, edgeName) {
  if (shape === 'lshape' && edgeName === 'Corner (inside)') return 'lshape-AB';
  if (shape === 'ushape' && edgeName === 'Corner (inside) — Left') return 'ushape-BackLeft';
  if (shape === 'ushape' && edgeName === 'Corner (inside) — Right') return 'ushape-BackRight';
  return null;
}

// Returns [runA, runB], the two adjacent run lengths (inches) that meet at this corner, read
// from the same dimension inputs drawCTPreview uses (gN('da-len') etc.) -- kept in inches so
// this needs no canvas scale factor, unlike drawCTPreview's render-time re-clamp of the same
// 0.4x-of-shorter-run bound in pixel space. The 'ushape-BackRight' fallback (dc-len || da-len)
// mirrors drawCTPreview's own cLv=cL||aL fallback for a blank Right Run field.
function dcChamferAdjacentRunsIn(cornerKey) {
  if (cornerKey === 'lshape-AB') return [gN('db-len'), gN('da-len') - gN('db-dep')];
  if (cornerKey === 'ushape-BackLeft') return [gN('da-len'), gN('db-len')];
  if (cornerKey === 'ushape-BackRight') return [(gN('dc-len') || gN('da-len')), gN('db-len')];
  return [0, 0];
}

function dcChamferMaxSetbackIn(cornerKey) {
  var runs = dcChamferAdjacentRunsIn(cornerKey);
  var shorter = Math.min(runs[0], runs[1]);
  return shorter > 0 ? shorter * DC_CHAMFER_MAX_FRACTION : 0;
}

// Applies a rep-typed setback, clamping (never silently corrupting the fill geometry) if it
// exceeds the max for this corner's current adjacent runs, and treating zero/blank/invalid
// input -- or a corner whose adjacent runs aren't valid yet -- as "not chamfered" (same as
// unchecking the box) rather than a degenerate zero-length or geometrically-impossible chamfer.
function dcSetChamferSetback(cornerKey, rawVal, cbEl, inputEl) {
  if (!dcChamferedCorners[cornerKey]) return;
  var val = parseFloat(rawVal);
  var max = dcChamferMaxSetbackIn(cornerKey);
  if (!(val > 0) || !(max > 0)) {
    delete dcChamferedCorners[cornerKey];
    if (cbEl) cbEl.checked = false;
    if (inputEl) { inputEl.value = ''; inputEl.style.display = 'none'; }
    if (!(max > 0) && val > 0 && typeof showToast === 'function') showToast('Enter valid run dimensions before chamfering this corner');
    drawCTPreview();
    if (typeof calcDrawing === 'function') calcDrawing();
    return;
  }
  var finalVal = val;
  if (val > max) {
    finalVal = Math.round(max * 100) / 100;
    if (inputEl) inputEl.value = finalVal;
    if (typeof showToast === 'function') showToast('Chamfer setback clamped to ' + finalVal.toFixed(2) + 'in (max for this corner)');
  }
  dcChamferedCorners[cornerKey].setbackIn = finalVal;
  drawCTPreview();
  if (typeof calcDrawing === 'function') calcDrawing();
}

// Build edge assignment selectors
function buildEdgeAssignmentArea() {
```

- [ ] **Step 2: Add the two new U-shape corner labels**

Find (around line 11324):

```js
    ushape:   ['Left front','Back front','Right front','Left back (wall)','Back wall','Right back (wall)','Left end','Right end'],
```

Replace with:

```js
    ushape:   ['Left front','Back front','Right front','Left back (wall)','Back wall','Right back (wall)','Left end','Right end','Corner (inside) — Left','Corner (inside) — Right'],
```

- [ ] **Step 3: Add the chamfer checkbox + setback control to each corner row**

Find (around line 11358, the end of the `edges.forEach` loop body):

```js
    row.appendChild(swatch); row.appendChild(lbl); row.appendChild(sel);
    area.appendChild(row);
  });
```

Replace with:

```js
    row.appendChild(swatch); row.appendChild(lbl); row.appendChild(sel);
    area.appendChild(row);

    // Chamfer control (2026-08-12): setback-inches input, shown only for the corner-type edge
    // labels this shape actually defines an inside corner for.
    const chamferKey = dcChamferKeyFor(ctShape, edgeName);
    if (chamferKey) {
      const crow = document.createElement('div');
      crow.style.cssText = 'display:flex;align-items:center;gap:8px;margin:-3px 0 10px 20px';
      const cb = document.createElement('input');
      cb.type = 'checkbox'; cb.id = 'chamfer-cb-' + chamferKey;
      cb.checked = !!dcChamferedCorners[chamferKey];
      const clbl = document.createElement('label');
      clbl.textContent = 'Chamfer 45°'; clbl.htmlFor = cb.id;
      clbl.style.cssText = 'font-size:10px;color:var(--muted)';
      const sbIn = document.createElement('input');
      sbIn.type = 'number'; sbIn.id = 'chamfer-sb-' + chamferKey; sbIn.step = '0.25'; sbIn.placeholder = 'in';
      sbIn.style.cssText = 'width:52px;background:rgba(255,255,255,0.04);border:1px solid var(--border);border-radius:5px;padding:3px 5px;color:var(--text);font-size:10px;font-family:DM Mono,monospace;outline:none';
      sbIn.style.display = cb.checked ? '' : 'none';
      sbIn.value = cb.checked ? dcChamferedCorners[chamferKey].setbackIn : '';
      cb.onchange = () => {
        if (cb.checked) {
          dcChamferedCorners[chamferKey] = { setbackIn: 0 };
          sbIn.style.display = '';
          sbIn.value = 1.5;
          dcSetChamferSetback(chamferKey, '1.5', cb, sbIn);
        } else {
          delete dcChamferedCorners[chamferKey];
          sbIn.value = ''; sbIn.style.display = 'none';
          drawCTPreview();
          if (typeof calcDrawing === 'function') calcDrawing();
        }
      };
      sbIn.oninput = () => dcSetChamferSetback(chamferKey, sbIn.value, cb, sbIn);
      crow.appendChild(cb); crow.appendChild(clbl); crow.appendChild(sbIn);
      area.appendChild(crow);
    }
  });
```

- [ ] **Step 4: Reset chamfer state alongside cutouts/seams on a fresh draw**

Find (around line 11003):

```js
  dcCutouts = []; dcSeams = [];
```

Replace with:

```js
  dcCutouts = []; dcSeams = []; dcChamferedCorners = {};
```

- [ ] **Step 5: Run node --check on all script blocks**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `TOTAL_BLOCKS:128` (or current count), `FAILED_BLOCKS:0`

- [ ] **Step 6: Manual verification (browser console)**

Open `stonedesk.html` locally (or the dev deployment), log in past the PIN/trial gate (see `STONEDESK-SESSION79-HANDOFF.md` §3 for the known license-gate workaround if testing against the live/staging site), open the Drawing Tool, select the L-shape preset, then in devtools console:

```js
document.getElementById('chamfer-cb-lshape-AB').click();
dcChamferedCorners['lshape-AB'];              // -> { setbackIn: 1.5 }
document.getElementById('chamfer-sb-lshape-AB').value = 999;
document.getElementById('chamfer-sb-lshape-AB').dispatchEvent(new Event('input'));
dcChamferedCorners['lshape-AB'].setbackIn;    // -> clamped value, well under 999, a toast should have appeared
document.getElementById('chamfer-cb-lshape-AB').click();
dcChamferedCorners['lshape-AB'];              // -> undefined
```

Expected: matches the comments above at each line — object appears on check, clamps (not 999) on an oversized value with a visible toast, disappears on uncheck.

- [ ] **Step 7: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- chamfered-corner data model, clamp helpers, edge-assignment UI controls"
```

---

### Task 2: L-shape unified fill polygon + chamfer stroke

**Files:**
- Modify: `stonedesk.html` (`drawCTPreview()`, L-shape branch, ~L11516–11547)

**Interfaces:**
- Consumes: `dcChamferedCorners['lshape-AB']`, `DC_CHAMFER_MAX_FRACTION` (Task 1), `EDGE_COLORS`, `colorEdge()`, `ea()` (all pre-existing in this function's scope).

- [ ] **Step 1: Replace the two separate rect fills with one unified fill polygon**

Find (around line 11516):

```js
    const ax=ox, ay=oy+(bL||0)*sc, aw=aL*sc, ah=aD*sc;
    const hasStub = bL && bD;
    const bx=ox, by=oy, bw=(bD||25)*sc, bh=bL*sc;
    ctx.fillStyle='rgba(232,133,10,0.1)';
    ctx.beginPath(); ctx.rect(ax,ay,aw,ah); ctx.fill();
    if (hasStub) { ctx.beginPath(); ctx.rect(bx,by,bw,bh); ctx.fill(); }
    window._ctRects.push({key:'A', x:ax, y:ay, w:aw, h:ah});
    if (hasStub) window._ctRects.push({key:'B', x:bx, y:by, w:bw, h:bh});
```

Replace with:

```js
    const ax=ox, ay=oy+(bL||0)*sc, aw=aL*sc, ah=aD*sc;
    const hasStub = bL && bD;
    const bx=ox, by=oy, bw=(bD||25)*sc, bh=bL*sc;
    // Chamfered inside corner (2026-08-12): unify A/B's two independent rect fills into one
    // polygon so a chamfer produces a real notch, not just a diagonal line drawn on top of a
    // still-square fill. offPx is re-clamped here (not just at input time in
    // buildEdgeAssignmentArea) so a setback valid when typed can never self-intersect the fill
    // if the rep later shrinks A or B's dimensions -- same defensive posture as the sink-fit
    // staleness re-check.
    const chamferAB = dcChamferedCorners['lshape-AB'];
    const chamferABMaxPx = Math.max(Math.min(bh, aw-bw) * DC_CHAMFER_MAX_FRACTION, 0);
    const chamferABOffPx = (hasStub && chamferAB && chamferAB.setbackIn > 0) ? Math.min(chamferAB.setbackIn * sc, chamferABMaxPx) : 0;
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
    window._ctRects.push({key:'A', x:ax, y:ay, w:aw, h:ah});
    if (hasStub) window._ctRects.push({key:'B', x:bx, y:by, w:bw, h:bh});
```

- [ ] **Step 2: Replace the corner dot-marker with a real chamfer stroke when chamfered**

Find (around line 11543):

```js
      const cornerColor = ea('Corner (inside)', null);
      if (cornerColor) {
        ctx.fillStyle = EDGE_COLORS[cornerColor].color;
        ctx.beginPath(); ctx.arc(bx+bw, ay, 5, 0, Math.PI*2); ctx.fill();
      }
```

Replace with:

```js
      const cornerColor = ea('Corner (inside)', null);
      if (chamferABOffPx > 0) {
        // Real fabrication edge now that the corner is chamfered -- a new diagonal stroke
        // between the same two substituted points the fill notch above uses, drawn on top of
        // (not replacing) the unmodified B-Front/A-Back(wall) strokes above, per the design spec.
        colorEdge(bx+bw, ay-chamferABOffPx, bx+bw+chamferABOffPx, ay, cornerColor || 'polished');
      } else if (cornerColor) {
        ctx.fillStyle = EDGE_COLORS[cornerColor].color;
        ctx.beginPath(); ctx.arc(bx+bw, ay, 5, 0, Math.PI*2); ctx.fill();
      }
```

- [ ] **Step 3: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 4: Manual verification (browser console)**

With the L-shape preset selected and default dims (Run A 96in/25.5in, Run B 72in/25.5in):

```js
document.getElementById('chamfer-cb-lshape-AB').click();          // check the box (default 1.5in)
drawCTPreview();
// Sanity: with these dims the L-shape scale (sc) is deterministic per drawCTPreview's own
// totL/totD math -- rather than hand-computing sc, confirm behaviorally instead:
document.getElementById('chamfer-sb-lshape-AB').value = 6;
document.getElementById('chamfer-sb-lshape-AB').dispatchEvent(new Event('input'));
dcChamferedCorners['lshape-AB'].setbackIn;   // -> clamped to <= 0.4 * min(72, 96-25.5) = 27.4 (so 6 survives unclamped)
document.getElementById('chamfer-sb-lshape-AB').value = 200;
document.getElementById('chamfer-sb-lshape-AB').dispatchEvent(new Event('input'));
dcChamferedCorners['lshape-AB'].setbackIn;   // -> clamped to 27.4 (0.4 * min(72, 70.5))
```

Expected: values match the clamp math in the comments; canvas visibly shows a diagonal notch at the inside corner (not a square corner) once checked, confirmed by eye or a screenshot.

- [ ] **Step 5: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- L-shape chamfered inside corner (fill notch + diagonal edge)"
```

---

### Task 3: U-shape unified fill polygon + chamfer strokes (two corners)

**Files:**
- Modify: `stonedesk.html` (`drawCTPreview()`, U-shape branch, ~L11567–11585)

**Interfaces:**
- Consumes: `dcChamferedCorners['ushape-BackLeft']`, `dcChamferedCorners['ushape-BackRight']`, `DC_CHAMFER_MAX_FRACTION`, `EDGE_COLORS`, `colorEdge()`, `ea()`.

- [ ] **Step 1: Replace the three separate rect fills with one unified fill polygon, and add the two chamfer strokes**

Find (around line 11567):

```js
    const bx=ox, by=oy;
    const lx=ox, ly=oy+backH;
    const rx=ox+backW-rightW, ry=oy+backH;
    ctx.fillStyle='rgba(232,133,10,0.1)';
    ctx.beginPath(); ctx.rect(bx,by,backW,backH); ctx.fill();
    ctx.beginPath(); ctx.rect(lx,ly,leftW,leftH); ctx.fill();
    ctx.beginPath(); ctx.rect(rx,ry,rightW,rightH); ctx.fill();
    window._ctRects.push({key:'Back', x:bx, y:by, w:backW, h:backH});
    window._ctRects.push({key:'Left', x:lx, y:ly, w:leftW, h:leftH});
    window._ctRects.push({key:'Right', x:rx, y:ry, w:rightW, h:rightH});
    // Outline as one continuous polygon (clockwise from top-left, around the U, back to start)
    colorEdge(lx,ly+leftH, lx,by, ea('Left back (wall)','wall'));                 // left leg outer (left wall)
    colorEdge(lx,by, bx+backW,by, ea('Back wall','wall'));                       // back wall
    colorEdge(bx+backW,by, rx+rightW,ry+rightH, ea('Right back (wall)','wall'));  // right leg outer (right wall)
    colorEdge(rx+rightW,ry+rightH, rx,ry+rightH, ea('Right front','polished'));   // right leg front
    colorEdge(rx,ry+rightH, rx,by+backH, ea('Right end','wall'));                // right leg inner end
    colorEdge(rx,by+backH, lx+leftW,by+backH, ea('Back front','polished'));      // back run front (between the legs)
    colorEdge(lx+leftW,by+backH, lx+leftW,ly+leftH, ea('Left end','wall'));      // left leg inner end
    colorEdge(lx+leftW,ly+leftH, lx,ly+leftH, ea('Left front','polished'));      // left leg front
```

Replace with:

```js
    const bx=ox, by=oy;
    const lx=ox, ly=oy+backH;
    const rx=ox+backW-rightW, ry=oy+backH;
    // Chamfered inside corners (2026-08-12): same unified-fill-polygon approach as the L-shape
    // above, extended to U-shape's two inside corners (Back-Left, Back-Right). backFrontPx is
    // the "Back front" segment's full pixel length (rx to lx+leftW) -- the second adjacent edge
    // for BOTH corners, since they share that one segment.
    const chamferBL = dcChamferedCorners['ushape-BackLeft'];
    const chamferBR = dcChamferedCorners['ushape-BackRight'];
    const backFrontPx = backW - leftW - rightW;
    const chamferBLMaxPx = Math.max(Math.min(leftH, backFrontPx) * DC_CHAMFER_MAX_FRACTION, 0);
    const chamferBRMaxPx = Math.max(Math.min(rightH, backFrontPx) * DC_CHAMFER_MAX_FRACTION, 0);
    const offBL = (chamferBL && chamferBL.setbackIn > 0) ? Math.min(chamferBL.setbackIn * sc, chamferBLMaxPx) : 0;
    const offBR = (chamferBR && chamferBR.setbackIn > 0) ? Math.min(chamferBR.setbackIn * sc, chamferBRMaxPx) : 0;
    ctx.fillStyle='rgba(232,133,10,0.1)';
    ctx.beginPath();
    ctx.moveTo(lx, ly+leftH);
    ctx.lineTo(lx, by);
    ctx.lineTo(lx+backW, by);
    ctx.lineTo(rx+rightW, ry+rightH);
    ctx.lineTo(rx, ry+rightH);
    if (offBR > 0) {
      ctx.lineTo(rx, by+backH+offBR);
      ctx.lineTo(rx+offBR, by+backH);
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
    window._ctRects.push({key:'Back', x:bx, y:by, w:backW, h:backH});
    window._ctRects.push({key:'Left', x:lx, y:ly, w:leftW, h:leftH});
    window._ctRects.push({key:'Right', x:rx, y:ry, w:rightW, h:rightH});
    // Outline as one continuous polygon (clockwise from top-left, around the U, back to start)
    colorEdge(lx,ly+leftH, lx,by, ea('Left back (wall)','wall'));                 // left leg outer (left wall)
    colorEdge(lx,by, bx+backW,by, ea('Back wall','wall'));                       // back wall
    colorEdge(bx+backW,by, rx+rightW,ry+rightH, ea('Right back (wall)','wall'));  // right leg outer (right wall)
    colorEdge(rx+rightW,ry+rightH, rx,ry+rightH, ea('Right front','polished'));   // right leg front
    colorEdge(rx,ry+rightH, rx,by+backH, ea('Right end','wall'));                // right leg inner end
    colorEdge(rx,by+backH, lx+leftW,by+backH, ea('Back front','polished'));      // back run front (between the legs)
    colorEdge(lx+leftW,by+backH, lx+leftW,ly+leftH, ea('Left end','wall'));      // left leg inner end
    colorEdge(lx+leftW,ly+leftH, lx,ly+leftH, ea('Left front','polished'));      // left leg front
    // Chamfer diagonal strokes + not-yet-chamfered corner markers (2026-08-12), mirroring the
    // L-shape's 'Corner (inside)' dot-to-stroke pattern above.
    const cornerColorBL = ea('Corner (inside) — Left', null);
    if (offBL > 0) {
      colorEdge(lx+leftW+offBL, by+backH, lx+leftW, by+backH+offBL, cornerColorBL || 'polished');
    } else if (cornerColorBL) {
      ctx.fillStyle = EDGE_COLORS[cornerColorBL].color;
      ctx.beginPath(); ctx.arc(lx+leftW, by+backH, 5, 0, Math.PI*2); ctx.fill();
    }
    const cornerColorBR = ea('Corner (inside) — Right', null);
    if (offBR > 0) {
      colorEdge(rx, by+backH+offBR, rx+offBR, by+backH, cornerColorBR || 'polished');
    } else if (cornerColorBR) {
      ctx.fillStyle = EDGE_COLORS[cornerColorBR].color;
      ctx.beginPath(); ctx.arc(rx, by+backH, 5, 0, Math.PI*2); ctx.fill();
    }
```

- [ ] **Step 2: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 3: Manual verification (browser console)**

Select the U-shape preset (default dims: Left 72in/25.5in, Back 84in/25.5in, Right 72in/25.5in):

```js
document.getElementById('chamfer-cb-ushape-BackLeft').click();
document.getElementById('chamfer-cb-ushape-BackRight').click();
dcChamferedCorners;  // -> both 'ushape-BackLeft' and 'ushape-BackRight' present, setbackIn: 1.5 each
document.getElementById('chamfer-cb-ushape-BackLeft').click();  // uncheck just the left one
dcChamferedCorners;  // -> only 'ushape-BackRight' remains -- confirms the two corners toggle independently
```

Expected: matches comments; canvas shows independent notches at each Back-corner as they're toggled.

- [ ] **Step 4: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- U-shape chamfered inside corners, Back-Left and Back-Right independently"
```

---

### Task 4: Pricing — wire chamfer cost into calc()'s real total

**Files:**
- Modify: `stonedesk.html` (`calc()` ~L9864, `dcSeamPricingSummary` region ~L12852, `calcDrawing()` ~L12909, `dcSyncLiveToQuoteEngine()` ~L13042)

**Interfaces:**
- Consumes: `dcChamferedCorners` (Task 1), `DC_CHAMFER_EDGE_COST` (Task 1).
- Produces: `function dcChamferPricingSummary()` returning `{ count: number, totalDiagLF: number }`, consumed only within this task.

- [ ] **Step 1: Add `dcChamferPricingSummary()`**

Find (around line 12852):

```js
function dcSeamPricingSummary() {
  const totalSeamLF = dcSeams.reduce((sum,s)=> sum + Math.hypot(s.x2-s.x1, s.y2-s.y1)/12, 0);
  return { seamCount: dcSeams.length, pieceCount: dcSeams.length + 1, totalSeamLF: totalSeamLF };
}
```

Replace with:

```js
function dcSeamPricingSummary() {
  const totalSeamLF = dcSeams.reduce((sum,s)=> sum + Math.hypot(s.x2-s.x1, s.y2-s.y1)/12, 0);
  return { seamCount: dcSeams.length, pieceCount: dcSeams.length + 1, totalSeamLF: totalSeamLF };
}

// Sums active chamfers into a single diagonal-LF figure, mirroring dcSeamPricingSummary above.
// Diagonal length per chamfer = setbackIn * sqrt(2) (the hypotenuse of the equal-leg right
// triangle a 45deg chamfer cuts) -- the rate (edgeLfRate, both-sides-finished x2) is applied by
// the caller in calcDrawing(), same as seams, so there's exactly one place that owns the rate.
function dcChamferPricingSummary() {
  const active = Object.keys(dcChamferedCorners).filter(k => dcChamferedCorners[k].setbackIn > 0);
  const totalDiagLF = active.reduce((sum,k) => sum + (dcChamferedCorners[k].setbackIn * Math.SQRT2) / 12, 0);
  return { count: active.length, totalDiagLF: totalDiagLF };
}
```

- [ ] **Step 2: Compute `chamferEdgeCost` in `calcDrawing()` and add its results-panel card**

Find (around line 12980):

```js
  const seamInfo = (typeof dcSeamPricingSummary === 'function') ? dcSeamPricingSummary() : {seamCount:0,pieceCount:1,totalSeamLF:0};
  const edgeLfRate = parseFloat((document.getElementById('sairn-unit-edge_lf')||{}).value) || 18;
  const seamEdgeCost = seamInfo.totalSeamLF * 2 * edgeLfRate; // both sides of every cut are finished edge
  const drainboardInfo = (typeof dcDrainboardPricingSummary === 'function') ? dcDrainboardPricingSummary() : {count:0,totalCost:0};
```

Replace with:

```js
  const seamInfo = (typeof dcSeamPricingSummary === 'function') ? dcSeamPricingSummary() : {seamCount:0,pieceCount:1,totalSeamLF:0};
  const edgeLfRate = parseFloat((document.getElementById('sairn-unit-edge_lf')||{}).value) || 18;
  const seamEdgeCost = seamInfo.totalSeamLF * 2 * edgeLfRate; // both sides of every cut are finished edge
  const chamferInfo = (typeof dcChamferPricingSummary === 'function') ? dcChamferPricingSummary() : {count:0,totalDiagLF:0};
  const chamferEdgeCost = chamferInfo.totalDiagLF * 2 * edgeLfRate; // both sides of every chamfer cut are finished edge, same convention as seams
  const drainboardInfo = (typeof dcDrainboardPricingSummary === 'function') ? dcDrainboardPricingSummary() : {count:0,totalCost:0};
```

Find (around line 12997):

```js
    {n:seamInfo.seamCount>0?seamInfo.pieceCount+' pieces':'1 piece',l:'Seams',s:seamInfo.seamCount>0?seamInfo.seamCount+' seam(s), '+seamInfo.totalSeamLF.toFixed(1)+' LF, +$'+seamEdgeCost.toFixed(0)+' polished edge':'No seams placed'},
    {n:drainboardInfo.count>0?'$'+drainboardInfo.totalCost.toFixed(0):'None',l:'Drainboard(s)',s:drainboardInfo.count>0?drainboardInfo.count+' side(s) attached':'No drainboards placed'},
```

Replace with:

```js
    {n:seamInfo.seamCount>0?seamInfo.pieceCount+' pieces':'1 piece',l:'Seams',s:seamInfo.seamCount>0?seamInfo.seamCount+' seam(s), '+seamInfo.totalSeamLF.toFixed(1)+' LF, +$'+seamEdgeCost.toFixed(0)+' polished edge':'No seams placed'},
    {n:chamferInfo.count>0?'+$'+chamferEdgeCost.toFixed(0):'None',l:'Chamfered Corners',s:chamferInfo.count>0?chamferInfo.count+' corner(s), '+chamferInfo.totalDiagLF.toFixed(2)+' LF diagonal edge':'No corners chamfered'},
    {n:drainboardInfo.count>0?'$'+drainboardInfo.totalCost.toFixed(0):'None',l:'Drainboard(s)',s:drainboardInfo.count>0?drainboardInfo.count+' side(s) attached':'No drainboards placed'},
```

- [ ] **Step 3: Pass `chamferEdgeCost` into `dcSyncLiveToQuoteEngine()`**

Find (around line 13027):

```js
  dcSyncLiveToQuoteEngine(grossSqFt, seamEdgeCost);
}
```

Replace with:

```js
  dcSyncLiveToQuoteEngine(grossSqFt, seamEdgeCost, chamferEdgeCost);
}
```

- [ ] **Step 4: Accept the param and assign `DC_CHAMFER_EDGE_COST` in `dcSyncLiveToQuoteEngine()`**

Find (around line 13042):

```js
function dcSyncLiveToQuoteEngine(grossSqFt, seamEdgeCost) {
```

Replace with:

```js
function dcSyncLiveToQuoteEngine(grossSqFt, seamEdgeCost, chamferEdgeCost) {
```

Find (around line 13090):

```js
  if (typeof seamEdgeCost === 'number') DC_SEAM_EDGE_COST = seamEdgeCost;

  calc();
```

Replace with:

```js
  if (typeof seamEdgeCost === 'number') DC_SEAM_EDGE_COST = seamEdgeCost;
  if (typeof chamferEdgeCost === 'number') DC_CHAMFER_EDGE_COST = chamferEdgeCost;

  calc();
```

- [ ] **Step 5: Read `DC_CHAMFER_EDGE_COST` in `calc()` — add to `rawSubtotal`, `lastCalc`, and `lines[]`**

Find (around line 9903):

```js
  const seamCost = (typeof DC_SEAM_EDGE_COST === 'number') ? DC_SEAM_EDGE_COST : 0;
  const rawSubtotal = matFabSubtotal + finishCost + edgeCost + waterfallCost + sinkCost + cookCost + holeCost + outletCost + bsCost + bktCost + dwCost + seamCost + removal + delivery;
```

Replace with:

```js
  const seamCost = (typeof DC_SEAM_EDGE_COST === 'number') ? DC_SEAM_EDGE_COST : 0;
  const chamferCost = (typeof DC_CHAMFER_EDGE_COST === 'number') ? DC_CHAMFER_EDGE_COST : 0;
  const rawSubtotal = matFabSubtotal + finishCost + edgeCost + waterfallCost + sinkCost + cookCost + holeCost + outletCost + bsCost + bktCost + dwCost + seamCost + chamferCost + removal + delivery;
```

Find (around line 9913):

```js
  lastCalc = { mat, proj, tier, total, totalLF, impliedSF, impliedPPSF, bsRate, edgeRate, sinkFee, thick, finUpch, removal, delivery, waterfallCost, sinkCost, cookCost, holeCost, outletCost, bsCost, bktCost, dwCost, seamCost, matFabSubtotal, finishCost, edgeCost, tierAdj };
```

Replace with:

```js
  lastCalc = { mat, proj, tier, total, totalLF, impliedSF, impliedPPSF, bsRate, edgeRate, sinkFee, thick, finUpch, removal, delivery, waterfallCost, sinkCost, cookCost, holeCost, outletCost, bsCost, bktCost, dwCost, seamCost, chamferCost, matFabSubtotal, finishCost, edgeCost, tierAdj };
```

Find (around line 9933):

```js
    { name:'Seam polished edge', val:seamCost, show:seamCost > 0 },
    { name:'Old countertop removal', val:removal, show:removal > 0 },
```

Replace with:

```js
    { name:'Seam polished edge', val:seamCost, show:seamCost > 0 },
    { name:'Chamfered corner(s)', val:chamferCost, show:chamferCost > 0 },
    { name:'Old countertop removal', val:removal, show:removal > 0 },
```

- [ ] **Step 6: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 7: Manual verification (browser console)**

With the L-shape preset selected and a valid material/project selected so `calc()` produces a real total:

```js
calcDrawing();
const before = lastCalc.total;
document.getElementById('chamfer-cb-lshape-AB').click();   // adds a 1.5in chamfer
const edgeLfRate = parseFloat(document.getElementById('sairn-unit-edge_lf').value) || 18;
const expectedDelta = Math.round(((1.5 * Math.SQRT2 / 12) * 2 * edgeLfRate) / 5) * 5; // total rounds to nearest $5
lastCalc.chamferCost > 0;                    // -> true
lastCalc.total - before;                     // -> roughly expectedDelta (may shift by up to $5 from the total's own rounding)
document.getElementById('chamfer-cb-lshape-AB').click();   // remove it
lastCalc.total === before;                   // -> true, cost returns to exactly its prior value
```

Expected: chamfer cost is a real, nonzero addition to `lastCalc.total` while active, and removing the chamfer returns the total to its exact prior value (the toggle-off staleness edge case from the spec).

- [ ] **Step 8: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- chamfered-corner edge-LF cost wired into calc()'s real quote total"
```

---

### Task 5: Cut sheet — print the chamfered corners

**Files:**
- Modify: `stonedesk.html` (`printDrawCutSheet()` ~L13193)

**Interfaces:**
- Consumes: `dcChamferedCorners` (Task 1).

- [ ] **Step 1: Add the "Chamfered Corners" row**

Find (around line 13193):

```js
  if (typeof dcSeams !== 'undefined' && dcSeams.length) {
    const seamSummary = dcSeams.map(s => s.label + ' (' + (Math.hypot(s.x2-s.x1,s.y2-s.y1)/12).toFixed(1) + ' LF)').join(', ');
    win.document.write('<div class="row"><span class="rl">Seams</span><span class="rv">'+dcSeams.length+' — '+seamSummary+'</span></div>');
  }
  if (typeof dcCutouts !== 'undefined' && dcCutouts.length) {
```

Replace with:

```js
  if (typeof dcSeams !== 'undefined' && dcSeams.length) {
    const seamSummary = dcSeams.map(s => s.label + ' (' + (Math.hypot(s.x2-s.x1,s.y2-s.y1)/12).toFixed(1) + ' LF)').join(', ');
    win.document.write('<div class="row"><span class="rl">Seams</span><span class="rv">'+dcSeams.length+' — '+seamSummary+'</span></div>');
  }
  if (typeof dcChamferedCorners !== 'undefined') {
    const chamferLabels = { 'lshape-AB':'Inside corner (A-B)', 'ushape-BackLeft':'Inside corner (Back-Left)', 'ushape-BackRight':'Inside corner (Back-Right)' };
    const activeChamfers = Object.keys(dcChamferedCorners).filter(k => dcChamferedCorners[k].setbackIn > 0);
    if (activeChamfers.length) {
      const chamferSummary = activeChamfers.map(k => (chamferLabels[k]||k) + ': ' + dcChamferedCorners[k].setbackIn + 'in chamfer').join(', ');
      win.document.write('<div class="row"><span class="rl">Chamfered Corners</span><span class="rv">'+chamferSummary+'</span></div>');
    }
  }
  if (typeof dcCutouts !== 'undefined' && dcCutouts.length) {
```

- [ ] **Step 2: Run node --check**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0`

- [ ] **Step 3: Manual verification (browser console)**

With the L-shape preset, chamfer checked at 1.5in:

```js
document.getElementById('chamfer-cb-lshape-AB').click();
printDrawCutSheet();
```

Expected: the new tab's printed cut sheet shows a "Chamfered Corners" row reading `Inside corner (A-B): 1.5in chamfer`, positioned between the Seams row (if any) and the Placed Cutouts row.

- [ ] **Step 4: Commit**

```bash
git add stonedesk.html
git commit -m "feat: StoneDesk -- chamfered corners listed on the printed cut sheet"
```

---

### Task 6: Full verification sweep, live-verify, and push

**Files:** none (verification only)

- [ ] **Step 1: Full local syntax sweep**

Run: `python tools/checkblocks.py stonedesk.html`
Expected: `FAILED_BLOCKS:0` across all blocks (not just the touched ones).

- [ ] **Step 2: Scoped Guardian checks**

Run: `python tools/duplicate_global_check.py stonedesk.html`
Expected: `DUPLICATE_NAMES:0`

Run: `python tools/missing_dom_target_check.py stonedesk.html`
Expected: no new findings referencing any of `chamfer-cb-`, `chamfer-sb-`, `dcChamferedCorners`, `dcChamferPricingSummary`, `dcChamferKeyFor`, `dcChamferAdjacentRunsIn`, `dcChamferMaxSetbackIn`, `dcSetChamferSetback` (pre-existing backlog findings unrelated to this feature are expected and not a blocker per the tool's own documented baseline).

Search: grep `stonedesk.html` for `console.log` inside the diff introduced by this plan (Tasks 1–5's added code) — confirm none was left in.

- [ ] **Step 3: Run the full guardian and adversarial review before commit/push**

Invoke the `sairn-guardian-v2` skill's full Check 0 + numbered checks against the diff, per CLAUDE.md's standing Push Protocol ("run full Check 0 + all 26 sairn-guardian-v2 checks locally against the changed file(s) — do not push on syntax passed alone"). Resolve any findings before proceeding.

- [ ] **Step 4: Combined end-to-end manual verification (browser console)**

On the L-shape preset:

```js
document.getElementById('chamfer-cb-lshape-AB').click();
dcChamferedCorners['lshape-AB'].setbackIn;   // -> 1.5
lastCalc.chamferCost > 0;                    // -> true
```

On the U-shape preset (switch shapes, then back to confirm namespacing):

```js
selectDrawShape('ushape');
dcChamferedCorners['lshape-AB'];             // -> still present (namespaced, not wiped by switching shapes)
document.getElementById('chamfer-cb-ushape-BackLeft').click();
document.getElementById('chamfer-cb-ushape-BackRight').click();
selectDrawShape('lshape');
document.getElementById('chamfer-cb-lshape-AB').checked;  // -> true, rebuilt correctly from persisted state
dcClearPoly();
dcChamferedCorners;                          // -> {} (fresh-draw reset clears everything)
```

Expected: matches each comment.

- [ ] **Step 5: Push**

```bash
git push origin main
```

- [ ] **Step 6: Live-verify against production**

Per CLAUDE.md's Push Protocol ("After pushing: live-verify... via real curl or equivalent, never assumed from the push itself succeeding") and the spec's own testing plan: drive `sairn.vercel.app/stonedesk`'s deployed functions directly (Playwright, using the license-gate workaround documented in `STONEDESK-SESSION79-HANDOFF.md` §3) and repeat Step 4's console checks against the live site. Confirm the deployed file hash matches the pushed commit (`git hash-object` on a fresh curl of the deployed file, same method used in prior session handoffs).

- [ ] **Step 7: Write the session handoff**

Use the `sairn-session-handoff` skill to record this feature's landing (commits, live-verification result, any findings from Step 3) in a new `STONEDESK-SESSION-N-HANDOFF.md`, per this project's standing convention.

---

## Self-Review Notes

- **Spec coverage:** data model (Task 1), corner geometry / rendering for both shapes (Tasks 2–3), pricing wired the same tick as the seam-cost fix (Task 4), cut sheet (Task 5), clamp + zero/blank + toggle-off-staleness edge cases (Task 1 + defensive re-clamp in Tasks 2–3), Custom Draw / other-angle / radius exclusions (Global Constraints, untouched by any task), full verification cycle from the spec's own testing plan (Task 6). No spec section without a task.
- **Placeholder scan:** no TBD/TODO, no "add appropriate handling," every step shows real code or a real runnable command with a stated expected result.
- **Type/name consistency:** `dcChamferedCorners`, `DC_CHAMFER_MAX_FRACTION`, `dcChamferKeyFor`, `dcChamferAdjacentRunsIn`, `dcChamferMaxSetbackIn`, `dcSetChamferSetback`, `dcChamferPricingSummary`, `DC_CHAMFER_EDGE_COST`, `chamferEdgeCost`/`chamferCost`/`chamferInfo` are spelled identically everywhere they're produced (Task 1/4) and consumed (Tasks 2–5).
