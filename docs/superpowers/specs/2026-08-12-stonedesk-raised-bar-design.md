# StoneDesk — Raised Bar (Overhang) Section

## Problem

STONEDESK-SESSION79-HANDOFF.md's open items list gap #2: "Raised bar cannot combine with L-shape/U-shape on the same page." Investigated before brainstorming: **no raised-bar drawing-tool feature exists at all today** — no checkbox, no shape option, no geometry, no pricing hook. The only related code is the AI shape-description parser (~stonedesk.html:11163-11188), which maps the free-text phrase "bar top" onto the ordinary `straight` preset shape at standard depth — a rough natural-language approximation, not a real stepped-height feature. This is a missing capability, not a combination bug.

A raised bar is a stepped-up, bar-height overhang section on one edge of a counter run — elevated above the main counter (typically ~42in vs. ~36in counter height), overhanging the base cabinets for stool seating. Real stone, real added footprint, real fabrication instruction — same bar the chamfer feature set.

## Scope, decided during brainstorming

- **One raised bar per drawing**, attachable to **any preset shape** (straight, L-shape, U-shape, Island, Galley, and the "custom" preset shape — the 4-section preset option, not freehand Custom Draw mode).
- **Horizontal front edges only.** Every shape's front-facing edges that run horizontally on screen (extending in the +y/"downward" screen direction, away from the material) are in scope. Vertical front edges (L-shape's `B-Front`, U-shape's `Left front`/`Right front`) are explicitly **out of scope** for this pass — named limitation, same precedent as chamfer excluding Custom Draw entirely. Freehand Custom Draw mode (`dcMode==='draw'`) is also out of scope, same reasoning.
- **Real added footprint**, not a label: the bar has a real length and overhang depth, extends the drawn shape, and adds real sqft to the order quantity — same "real fabrication instruction, not cosmetic" bar as chamfer.
- **True-to-scale rendering**: a real, accurately-scaled rectangular extension at the drawing's actual scale — not a schematic marker strip (the existing waterfall-panel convention, rejected for this feature since a raised bar's footprint is genuinely in the same horizontal plane as the rest of the counter, unlike a waterfall panel which represents a vertical side panel).
- **Partial-length, positioned segment** — the bar can be shorter than its edge (the common real case: a bar section partway along an island run, not spanning the whole thing), with a rep-entered length and offset along the edge.
- **Pricing**: sqft at the counter's own material rate (folds into the order-quantity total the same way splash/waterfall sqft already do) + new finished-edge-LF cost for the bar's own new edges, via the existing `edgeLfRate` — **single-sided** (not the ×2 both-sides-finished convention chamfer/seams use), since these are ordinary perimeter edges with one exposed face, not interior cuts exposing two faces.
- **No automatic seam.** The rep's existing manual seam tool already covers this if a specific job needs one; auto-placing a seam would bake in a fabrication assumption (continuous slab vs. separately-seamed piece) that varies by job and isn't this feature's call to make.
- **Corbel/support disclosure**: a non-blocking flag (toast + persistent cut-sheet marker) when the entered overhang depth exceeds a new admin-configurable threshold, default **15in** (quartz, per real manufacturer engineering guidance) — disclosed as a real, material-specific number, not a universal one, same honesty precedent as the sink-fit check's 1.5in clearance default.
- **Height is informational only** — stored and printed on the cut sheet, no formula impact (this is a top-down plan view; bar height doesn't change footprint).

## Data model

```js
var dcRaisedBar = null; // or { edgeKey, lengthIn, offsetIn, overhangDepthIn, heightIn }
// edgeKey format: '<ctShape>:<edge label>', e.g. 'lshape:A-Front', 'ushape:Back front',
// 'galley:Front counter front' -- namespaced by shape exactly like dcChamferedCorners,
// for the exact same reason: the chamfer feature shipped a real Critical bug (found in
// its own final review) from NOT filtering by current shape on the read side. Built in
// correctly from the start here instead of retrofitted after the fact.
```

Unlike `dcChamferedCorners` (a dict, since a shape can have up to two chamfered corners at once), this is a single nullable object since only one bar exists per drawing. It survives a shape switch in memory (so switching away and back doesn't lose a rep's work, same as chamfer), but every consumer (rendering, pricing, cut sheet) must independently confirm `dcRaisedBar.edgeKey.startsWith(ctShape + ':')` before treating it as active — mirroring chamfer's `dcChamferActiveKeys()` fix exactly, not chamfer's original (buggy) unfiltered read.

## Edge candidates (traced from the real renderer, not assumed)

Confirmed by reading `drawCTPreview()` directly: every shape's front-facing edge draws as a **horizontal** `colorEdge()` call at the bottom of that shape/section's own rect (`rectY + rectH`), extending further in +y ("downward," away from the material) is uniformly "outward" for every one of these — a single shared geometry rule covers all of them:

| Shape (`ctShape`) | Candidate edge label(s) | Edge length field |
|---|---|---|
| `straight` | `Front (exposed)` | `da-len` |
| `island` | `Front (exposed)` | `da-len` |
| `lshape` | `A-Front` | `da-len` |
| `ushape` | `Back front` | `db-len` |
| `galley` | `Front counter front`, `Back counter front` (rep picks one) | `da-len` / `db-len` respectively |
| `custom` (preset) | `Section A front`, `Section B front`, `Section C front` (rep picks one) | `da-len` / `db-len` / `dc-len` respectively |

Galley/custom's sections are built in a dynamic loop (`secs.forEach`, ~stonedesk.html:11812-11831), not fixed variables — but every section's front edge is still horizontal and drawn the same way, so the same shared geometry rule applies inside that loop too.

## Rendering

A key simplification versus chamfer: the bar is purely **additive**. Chamfer had to replace each shape's rect fill(s) with one unified polygon because the notch cuts *into* the existing boundary. A raised bar sits entirely *outside* the existing boundary, sharing one edge with it — so it renders as a second, separate filled rect drawn immediately after the base shape, using the identical fill style (`rgba(232,133,10,0.1)`). Two adjacent same-alpha fills with no gap between them read as one continuous piece, with zero need to touch any existing shape's fill call.

For the active bar's rect `{rectX, rectY, rectW, rectH}` (the section it's attached to) and edge length `edgeLenIn`, in that section's own scale `sc`:

```
offsetPx = dcRaisedBar.offsetIn * sc
lengthPx = dcRaisedBar.lengthIn * sc
depthPx  = dcRaisedBar.overhangDepthIn * sc
barX = rectX + offsetPx
barY = rectY + rectH
// fill: rect(barX, barY, lengthPx, depthPx), same fillStyle as the base shape
// new edges (all ADDITIONS, zero modification to any existing colorEdge() call):
//   front: colorEdge(barX, barY+depthPx, barX+lengthPx, barY+depthPx, ...)
//   left step:  colorEdge(barX, barY, barX, barY+depthPx, ...)
//   right step: colorEdge(barX+lengthPx, barY, barX+lengthPx, barY+depthPx, ...)
```

`offsetIn` and `lengthIn` are clamped so the bar can never extend past either end of its edge (`offsetIn >= 0`, `offsetIn + lengthIn <= edgeLenIn`) — clamp, don't silently produce a bar hanging off the end of its run, same "flag, don't corrupt the geometry" posture as chamfer's setback clamp. Re-clamped at render time against the edge's *current* length, not just at input time, for the same staleness reason chamfer's final review caught (a run can shrink after the bar was sized).

`offsetIn` is always measured from the edge's screen-left (smaller-x) end, regardless of which literal endpoint a given shape's `colorEdge()` call happens to start drawing from — resolves an ambiguity found in this spec's own self-review: U-shape's `Back front` is drawn `colorEdge(rx, ..., lx+leftW, ...)`, i.e. right-to-left, but `offsetIn` still means "distance from the left side of that edge as drawn on screen" for every shape, so the UI's offset input behaves identically no matter which shape is selected.

"Effective" length/depth (used throughout the Pricing section below) means the post-clamp values — the same numbers actually rendered, never the raw typed-in values if those exceeded the edge's current length.

## Pricing — wired correctly from the start

Same proven pattern as chamfer/seams: computed once in `calcDrawing()`, passed through `dcSyncLiveToQuoteEngine()`, assigned to a module-level variable, read by `calc()`.

```js
var DC_BAR_EDGE_COST = 0; // synced from dcRaisedBar via dcSyncLiveToQuoteEngine()
```

- `barSqFt = (effectiveLengthIn * effectiveOverhangDepthIn) / 144` — folds into the order-quantity total the same way `splashSqFt`/`wfSqFt` already do (`totalMat = (netSqFt + splashSqFt + wfSqFt + barSqFt) * 1.15`), **not** into gross/net sqft (those stay pure run-dimension figures, matching splash/waterfall's existing precedent — sink/cooktop deductions are never applied against bar sqft).
- `barEdgeLF = (effectiveLengthIn / 12) + (effectiveOverhangDepthIn / 12) * 2` (front edge + both step edges) — `barEdgeCost = barEdgeLF * edgeLfRate`, **single-sided**, no ×2 multiplier (unlike seam/chamfer's both-sides-finished convention — these are ordinary single-face perimeter edges).
- `calc()` adds `barEdgeCost` into `rawSubtotal`, `lastCalc`, and a new `lines[]` entry ("Raised bar edge"), same as `seamCost`/`chamferCost`.
- "Effective" values use the same render-time re-clamp as the geometry (never bill for more bar than what's actually drawn).

## Corbel/support disclosure

```js
var DC_BAR_CORBEL_THRESHOLD_IN = 15; // default; admin-configurable via a new sairn-unit-corbel_threshold field, same convention as edgeLfRate. Quartz-specific figure, disclosed as such -- other materials (granite, marble) commonly cite different real thresholds, not modeled this pass.
```

Non-blocking: if `overhangDepthIn` exceeds the threshold, show a toast on entry/change and carry a persistent flag into the bar's label and the cut-sheet line (same UX pattern as `dcApplySinkFitCheck()`'s "⚠" marker) — never blocks the rep from entering a real value, just discloses a real structural consideration on the document a fabricator/installer will actually read.

## Cut sheet

New "Raised Bar" row in `printDrawCutSheet()`, positioned with the other Drawing Tool feature rows (Seams, Chamfered Corners, Placed Cutouts): edge, length, overhang depth, height, and the corbel flag if applicable (e.g. "A-Front: 48in × 12in overhang, 42in height ⚠ corbel support recommended").

## Explicitly out of scope for this pass

- Vertical front edges (L-shape's `B-Front`, U-shape's `Left front`/`Right front`) — named limitation, not silently unhandled.
- Freehand Custom Draw mode (`dcMode==='draw'`) — same reasoning as chamfer.
- Automatic seam placement at the bar's transition line — rep uses the existing manual seam tool if their job needs one.
- Multiple raised bars per drawing.
- Material-specific corbel thresholds (granite/marble vs. quartz) — one flat, admin-configurable default (15in, quartz) for this pass.

## Edge cases (anticipated from chamfer's real findings — build these in correctly from the start, not retrofit after a review catches them)

- **Shape-scope leak (the Critical bug chamfer's final review found):** every consumer (rendering, pricing, cut sheet) must filter on `dcRaisedBar.edgeKey.startsWith(ctShape + ':')` before treating it as active — built into the design from the start this time.
- **Length/offset exceeding the edge's real length:** clamp both at input time and re-clamp at render time against the edge's current length (a run can shrink after the bar was sized) — same staleness class chamfer's pricing/cut-sheet fix addressed.
- **Zero/blank length or overhang depth:** treated as "no bar" (same as never having set one), not a degenerate zero-area bar.
- **Bar toggled off (or shape switched away) after being priced:** `DC_BAR_EDGE_COST` and `barSqFt` must drop to 0 the same tick, via `calcDrawing()`'s existing re-fire-on-any-edit path.
- **Galley/custom's dynamic section loop:** the shared geometry rule (front edge always horizontal, extends outward) applies inside `secs.forEach` the same as the fixed-variable shapes — one shared rendering helper, not five separately-written copies of the same math.

## Testing / verification plan

Same full cycle as chamfer: `node --check` via `tools/checkblocks.py` on every touched block, scoped Guardian checks, per-task review during implementation (not retroactive this time), commit, push, then live-verify against `sairn.vercel.app/stonedesk` — specifically: place a bar on a straight shape's front edge, confirm the fill/stroke geometry matches the expected offset/length, confirm `DC_BAR_EDGE_COST` and the quote total move by the expected dollar amount, confirm switching shapes correctly deactivates the bar (and switching back reactivates it), confirm the corbel flag appears past 15in and not before, and confirm the same on at least one shape from each of the three renderer families (fixed-variable: L-shape or U-shape; dynamic-loop: galley or custom preset).
