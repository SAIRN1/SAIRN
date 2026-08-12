# StoneDesk — Drawing Canvas: Responsive Height + Zoom

## Problem

STONEDESK-SESSION79-HANDOFF.md's open items list gap #3 (the last of the three): "Canvas hardcoded to 480px height, no resize/zoom."

Investigated before brainstorming — the canvas (`id="ct-canvas"`) is not fully hardcoded. Its **width** already resyncs dynamically to its container (`dcCanvas.width = dcCanvas.offsetWidth || 640`, in both `initDCCanvas()` and `toggleDCLeftPanel()`), and CSS renders it `width:100%;height:auto`, so it already visually scales with the browser horizontally. The real fixed constant is the drawing-buffer **height**: `dcCanvas.height = 480` is hardcoded in exactly those same two places (plus a now-overwritten static `height="480"` HTML attribute), never adapting to available viewport height or to the shape being drawn. There is no zoom or pan mechanism anywhere in the file — confirmed by grep, this is ground-zero, same situation raised-bar was in.

Practical effect: `drawCTPreview()`'s per-shape scale formulas (e.g. `sc=Math.min((W-pad*3)/aL,(H-pad*3)/aD)`) and Custom Draw mode's `dcGetTransform()` are both bounded by this fixed 480px height, so any shape whose vertical/depth extent is large relative to its width (a U-shape, a multi-section galley layout, a tall custom polygon) renders small and cramped regardless of real available screen space, with no way to zoom in for precision work.

## Scope, decided during brainstorming

- **Both height-responsiveness and zoom** — the original gap names both, and they're genuinely separate problems worth fixing together.
- **Height: viewport-relative, capped.** Canvas height becomes a fraction of the browser's visible viewport height (~65vh), clamped to a floor (480px — today's fixed value, so nothing gets smaller than the current experience) and a ceiling (~900px, so it never dominates the page on an ultrawide monitor).
- **Zoom: buttons only** (Zoom In / Zoom Out / Fit to Screen). No scroll-wheel, no pinch-to-zoom — the canvas sits inside a scrollable side-panel-plus-canvas layout, and wheel/pinch gestures would risk fighting the page's own scroll or accidentally triggering while a rep scrolls past. Buttons are simple, discoverable, and identical on desktop and touch.
- **No manual pan.** Zoom is always anchored on the canvas's own center point — no drag-to-pan gesture, no dedicated pan mode. A rep who needs to see a different part of a zoomed-in drawing uses Fit to Screen to reset, then zooms again. This avoids a real interaction-routing risk: the canvas already routes mouse/touch drag into corner-drag, preset-edge-drag, cutout placement, and seam placement — a pan gesture would need its own mode toggle to avoid colliding with all of that, for a benefit most jobs won't need (Custom Draw mode already places points via typed exact measurements, not pixel-precision dragging).
- **Preset mode and Custom Draw mode only.** Room Layout mode (`dcMode==='room'`, a separate, newer "Phase 1" renderer with its own independent `dcRoomGetTransform()`) is explicitly out of scope for this pass — named limitation, same precedent as chamfer excluding Custom Draw and raised-bar excluding vertical edges.

## Architecture

The key finding from investigation: `dcCanvasCoords(e)` is the **single, universal** screen-to-canvas-pixel conversion point every mouse/touch handler in the file already goes through (corner-drag, preset-edge-drag, cutout/seam placement and dragging — everything). This means zoom can be implemented as one transform applied at exactly two boundary points, with **zero changes to any of the ~15+ existing hit-test/drag functions**, all of which have already been bug-fixed multiple times this session and are the highest-risk code in this file to touch directly.

```js
var dcZoomLevel = 1; // 1.0 = fit (today's behavior, unchanged); range [1, 3]
```

**Rendering side:** one new call, `dcApplyZoomTransform(ctx, W, H)`, invoked at the top of `drawCTPreview()` right after `ctx.clearRect(0,0,W,H)`, before the grid-drawing loop or any shape branch.

Found in this spec's own self-review: `ctx.clearRect(0,0,W,H)` must run while the canvas transform is still whatever the *previous* `drawCTPreview()` call left it at (since `setTransform` is absolute and persists across calls) — if a previous frame was zoomed and this frame's `clearRect` ran before resetting the transform, `(0,0,W,H)` would clear the wrong region (mapped through the stale zoom), leaving old content visible outside it. Fixed by resetting to identity immediately before the clear, every call:

```js
ctx.setTransform(1, 0, 0, 1, 0, 0);
ctx.clearRect(0, 0, W, H);
dcApplyZoomTransform(ctx, W, H); // sets the real (possibly zoomed) transform for everything drawn below
```

`dcApplyZoomTransform` itself calls `ctx.setTransform(dcZoomLevel, 0, 0, dcZoomLevel, W/2*(1-dcZoomLevel), H/2*(1-dcZoomLevel))`, which scales everything drawn afterward — grid, shapes, strokes, dimension text — uniformly around the canvas's own center point `(W/2, H/2)`.

**Why `setTransform`, not `save()`/`scale()`/`restore()`:** `drawCTPreview()` has several early-return paths (blank-dimensions guards per shape, the `dcMode==='draw'`/`dcMode==='room'` branches that hand off to separate renderers and `return` immediately). A `save()`/`restore()` pair requires matching every exit path, or the canvas transform stack corrupts silently and every *subsequent* `drawCTPreview()` call inherits a wrong, compounding transform — a real, easy-to-miss bug class for exactly this function's shape. `setTransform()` is absolute (it replaces the whole matrix, not push/pop), so it can be called once at the top with no matching call needed anywhere else, sidestepping the risk entirely regardless of which early return fires.

**Hit-testing side:** `dcCanvasCoords(e)` applies the matching inverse before returning `{px, py}`:

```js
function dcCanvasCoords(e) {
  const rect = dcCanvas.getBoundingClientRect();
  const scaleX = dcCanvas.width/rect.width, scaleY = dcCanvas.height/rect.height;
  const rawPx = (e.clientX-rect.left)*scaleX, rawPy = (e.clientY-rect.top)*scaleY;
  const W = dcCanvas.width, H = dcCanvas.height;
  const px = (rawPx - W/2*(1-dcZoomLevel)) / dcZoomLevel;
  const py = (rawPy - H/2*(1-dcZoomLevel)) / dcZoomLevel;
  return { px, py };
}
```

Every downstream consumer (`dcHitRect`, `dcHitPresetEdge`, corner-drag, `dcCanvasPlaceOrDrag`, the seam/cutout routers, touch translation) receives `{px, py}` in the exact same coordinate space it always has — the "pre-zoom" logical space `drawCTPreview()`'s own scale math already operates in — so none of them need to know zoom exists.

At `dcZoomLevel === 1` (the default/Fit state), the formula reduces to `px = rawPx`, `py = rawPy` — byte-for-byte today's behavior, zero regression when zoom isn't in use.

## Zoom controls

Three buttons above the canvas, in the same visual row style as the existing Preset/Draw/Room mode buttons:

- **Zoom In:** `dcZoomLevel = Math.min(dcZoomLevel * 1.25, 3)`, then `drawCTPreview()`.
- **Zoom Out:** `dcZoomLevel = Math.max(dcZoomLevel / 1.25, 1)`, then `drawCTPreview()`.
- **Fit to Screen:** `dcZoomLevel = 1`, then `drawCTPreview()`.

Buttons disable (or visually gray, per existing button-disable conventions elsewhere in the file) at the respective bound — Zoom In disabled at 3, Zoom Out disabled at 1 (equivalently, "at Fit").

**Reset-to-fit triggers** (in addition to the explicit Fit button): switching shapes (`selectDrawShape()`), switching modes (`setDCMode()`), and clearing the shape (`dcClearPoly()`) all set `dcZoomLevel = 1` — a rep should never end up zoomed in on a drawing that no longer matches what's showing, the same "don't leave stale state visible" posture chamfer's and raised-bar's own shape-switch fixes established.

## Height sizing

Replaces the two hardcoded `dcCanvas.height = 480` assignments (`initDCCanvas()`, `toggleDCLeftPanel()`) with a shared helper:

```js
function dcComputeCanvasHeight() {
  return Math.max(480, Math.min(window.innerHeight * 0.65, 900));
}
```

Both existing call sites use `dcCanvas.height = dcComputeCanvasHeight();` instead of the literal `480`. A new `window.addEventListener('resize', ...)` (none exists in the file today — confirmed by grep) recomputes height and re-syncs width the same way `initDCCanvas()` already does, then calls `drawCTPreview()`, debounced (a plain `setTimeout`/`clearTimeout` pattern, ~150ms) so a window-drag doesn't fire a full redraw on every intermediate resize event.

## Explicitly out of scope for this pass

- Room Layout mode (`dcMode==='room'`) — named limitation, its own independent renderer/transform (`dcRoomGetTransform()`) untouched.
- Manual pan / drag-to-scroll while zoomed in.
- Scroll-wheel or pinch-to-zoom.
- Persisting zoom level across a page reload or across shape/mode switches (it deliberately resets, per the design above).

## Edge cases

- **Zoom level must never let the drawing scale-to-zero or become huge enough to blow past canvas bounds silently.** The `[1, 3]` clamp on `dcZoomLevel` is the whole safeguard — bounded multiplicatively off the same base scale `drawCTPreview()`'s own per-shape math already computes to fit the canvas at 1x, so 3x is "3 times the already-fits-the-canvas size," never an unbounded raw value.
- **`window.innerHeight` at 0 or unavailable** (e.g. a headless/unusual environment): `Math.max(480, ...)` floors it back to today's known-safe value regardless.
- **Resize listener firing during an active drag** (corner-drag, preset-edge-drag mid-gesture): the debounce means a resize won't fire mid-drag from ordinary window-drag speed; if it somehow did, `drawCTPreview()` already handles being called during a drag via the existing `dcFrozenTransform` mechanism (Custom Draw mode) — Preset mode's drag functions read live DOM input values on every move regardless of canvas size, so a mid-drag height change doesn't corrupt any in-progress preset-edge drag.

## Testing / verification plan

Same cycle as chamfer and raised-bar: `node --check` via `tools/checkblocks.py` on every touched block, scoped Guardian checks, per-task review during implementation, commit, push, then live-verify against `sairn.vercel.app/stonedesk` — specifically: confirm the canvas is taller on a simulated large-viewport window than the previous fixed 480px, confirm Zoom In/Out/Fit visibly change the drawing's size around a fixed center point, confirm a corner-drag and a cutout placement both still land in the correct spot at a non-1x zoom level (the actual proof the `dcCanvasCoords()` inverse-transform is correct), and confirm switching shapes/modes/Clear Shape all reset zoom to 1.
