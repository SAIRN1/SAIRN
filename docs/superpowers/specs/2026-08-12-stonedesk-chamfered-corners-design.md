# StoneDesk — Chamfered 45° Inside Corners

## Problem

Carolyn's industry review flagged a real, missing capability: the drawing tool has no way to specify a chamfered (45°-clipped) inside corner. Stone counters commonly chamfer an inside corner to avoid a sharp point that's prone to chipping and unsafe to bump into. There is currently no angle-snap mechanism anywhere in the corner-drag code — every inside corner on an L-shape or U-shape preset is square, with no way to say otherwise.

## Scope, decided during brainstorming

- **Real fabrication instruction**, not a cosmetic draw option: shows on the cut sheet, adds real dollars to the quote via edge-LF pricing. A missing capability report from a real customer is about what the shop can actually build and bill, not how the canvas looks.
- **Preset shapes' inside corners only** — L-shape's one inside corner, U-shape's two. Custom Draw mode's polygon segments are explicitly out of scope for this pass (same scope-boundary pattern as the sink-fit validation feature earlier this session): Custom Draw carries no per-vertex angle/adjacent-edge-length data in the current model, and adding that is real, separate work.
- **Rep-adjustable setback size** (inches), not a fixed default — a numeric input per chamfered corner.
- **Full fill-clipped rendering**, not a diagonal-line-only overlay — the on-screen drawing should look like the real cut piece, not just carry a marker. (This was explicitly chosen over the lower-risk diagonal-overlay-only alternative after the trade-off — including that it requires reworking L/U shape fill geometry — was presented directly.)

## Data model

```js
var dcChamferedCorners = {};
// keyed 'lshape-AB' | 'ushape-BackLeft' | 'ushape-BackRight' -> { setbackIn: number }
// presence in the object = chamfered; absence = square corner (default, unchanged behavior)
```

Namespaced by shape+corner so switching shapes (or switching away from and back to a shape) can't carry stale corner state onto a shape it doesn't apply to. Reset alongside `dcCutouts`/`dcSeams` wherever those are cleared on a fresh draw.

## Corner geometry (traced from the existing renderer, not re-derived)

`drawCTPreview()` (stonedesk.html:11367) currently draws L/U shapes as 2–3 *independently filled* rects, with the outline drawn afterward as a sequence of `colorEdge()` stroke calls between explicit points. The corner points already exist in that code:

- **L-shape inside corner:** `(bx+bw, ay)` — where B's front edge (`bx+bw,by` → `bx+bw,ay`) meets A's back-wall edge (`bx+bw,ay` → `ax+aw,ay`). This point is already used today for the "Corner (inside)" edge-assignment dot marker (stonedesk.html:11543-11547) — an existing, unused-beyond-a-dot hook this feature extends into something real.
- **U-shape Left-Back inside corner:** `(lx+leftW, by+backH)` — where "Left end" (`lx+leftW,by+backH` → `lx+leftW,ly+leftH`) meets "Back front" (`rx,by+backH` → `lx+leftW,by+backH`).
- **U-shape Right-Back inside corner:** `(rx, by+backH)` — where "Right end" (`rx,ry+rightH` → `rx,by+backH`) meets "Back front" (same segment, other end).

## Rendering change

Replace each shape's multiple independent rect fills with **one unified fill polygon** built from the same outline points the existing stroke calls already use (in the same clockwise order). When a corner is *not* chamfered, that polygon's corner is the single existing point — mathematically identical to today's rendering, zero visual change. When a corner *is* chamfered, substitute that one point with two points, each offset by `setbackIn * scale` along one of the two edges meeting there (moving away from the corner, toward the adjacent named endpoint) — producing a real notch in the fill.

`colorEdge()`'s existing per-edge stroke calls are **not modified** — they still draw the named edges (A-Front, B-Front, Back wall, etc.) exactly as today, zero risk to the L-shape rotation-mismap and U-shape Back-run-drag fixes already landed this session in adjacent code. A new short diagonal stroke is added per chamfered corner, drawn between the same two substituted points, using the corner's own edge-color assignment (extending L-shape's existing `'Corner (inside)'` dropdown option from a dot marker to a real edge; adding the equivalent two new dropdown options for U-shape's `Corner (inside) — Left` / `Corner (inside) — Right`).

Placed cutouts/sinks are unaffected — cutout hit-testing already uses `window._ctRects` (the individual rects), which are unchanged; only the *fill* path is unified, not the rect registry other features depend on.

## Pricing — wired correctly the first time

Two real bugs this session (cutout costs, then seam polished-edge cost) shared the same shape: a dollar figure computed and displayed correctly in the Drawing Tool's own panel, never passed to `calc()`'s real total. This feature is built the same *correct* way from the start, following the seam-cost fix's pattern exactly:

```js
var DC_CHAMFER_EDGE_COST = 0; // synced from dcChamferedCorners via dcSyncLiveToQuoteEngine()
```

For each active chamfer: diagonal length = `setbackIn * Math.sqrt(2)` (equal-leg right triangle), converted to LF, ×2 (both sides of the cut are finished edge, same convention as the seam fix), × the same admin `edgeLfRate` used for seams. Summed across all active chamfers, computed once in `calcDrawing()` (mirroring how `seamEdgeCost` is computed there today), passed into `dcSyncLiveToQuoteEngine(grossSqFt, seamEdgeCost, chamferEdgeCost)`, which sets `DC_CHAMFER_EDGE_COST` before calling `calc()`. `calc()` adds it into `rawSubtotal` and a new `lines[]` entry ("Chamfered corner(s)"), same as `seamCost` was just added.

## Cut sheet

Add a "Chamfered corners" line to the printed cut sheet (`printDrawCutSheet()`), listing each active corner and its setback (e.g. "Inside corner (A-B): 1.5in chamfer") — same treatment as the existing Seams and Placed Cutouts lines, so the shop floor sees it, not just the on-screen quote.

## Edge cases (caught in spec self-review)

- **Setback larger than an adjacent run allows:** an unbounded setback could push a substituted point past the *other* end of that edge, producing a self-intersecting fill polygon instead of a clean notch. Clamp each corner's `setbackIn` input to a reasonable fraction (e.g. no more than ~40%) of the shorter of the two adjacent run lengths, checked live as the rep types — same "flag, don't silently corrupt the geometry" posture as the sink-fit check.
- **Zero/blank setback:** treated as not-chamfered (same as the checkbox being unchecked) rather than a zero-length degenerate chamfer — avoids a divide-by-zero or a zero-length diagonal edge rendering as a stray dot.
- **Corner toggled off after being priced:** `DC_CHAMFER_EDGE_COST`'s per-corner contribution must drop to 0 the same tick the checkbox is unchecked, via the same `calcDrawing()`-refires-on-any-edit path already relied on for the sink-fit staleness fix — not just at the next unrelated recompute.

## Explicitly out of scope for this pass

- Custom Draw mode corner chamfering (named limitation, not silently unhandled — matches the sink-fit check's precedent).
- Any angle other than 45° (a chamfer is specifically the 45°-equal-legs case; a differently-angled cut is a different, unrequested feature).
- Radius/rounded corners (a real but different alternative treatment; not what was asked).

## Testing / verification plan

Same full cycle as every other fix tonight: `node --check` via `tools/extract_scripts.py` (not the unreliable root `extract_scripts.js`) on every touched block, scoped Guardian checks (no new duplicate ids, no undefined function refs, no console.log), commit, push, then live-verify against `sairn.vercel.app/stonedesk` by driving the real deployed functions directly via Playwright (the same license-gate workaround already used and disclosed this session) — specifically: place a chamfer on L-shape's inside corner, confirm the fill polygon's corner point coordinates match the expected offset, confirm `DC_CHAMFER_EDGE_COST` and the quote total move by the expected dollar amount, confirm removing the chamfer returns both to their prior values, and confirm the two U-shape corners toggle independently of each other.
