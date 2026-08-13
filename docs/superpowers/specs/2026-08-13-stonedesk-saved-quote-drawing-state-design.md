# StoneDesk — Saved Quote History: Drawing Tool State

## Problem

Logged in `SAIRN-BACKLOG.md` (2026-08-13, from the adversarial-review completeness check on the chamfered-corners/raised-bar/canvas-zoom feature series): `sdQuoteSaveHistory()` (`stonedesk.html:3405-3426`) persists only `{customer, project (material name), amount (final total), date, status}` to `sd_quote_history`. Verified: no code path serializes `dcPoly` (the drawn/edited shape), `dcCutouts` (sinks/cooktops/holes), `dcSeams`, `dcRaisedBar`, or `dcChamferedCorners`. The saved `amount` is correct — `calc()` genuinely sums every drawing-tool cost into it — but nothing about *what was actually drawn* survives a save. A rep reopening a saved quote next week has only a flat dollar figure to work from, no way to reconstruct or explain what generated it, and no way to resume editing it.

## Scope, decided during brainstorming

- **Full load, not read-only.** Reopening a saved quote genuinely re-populates the live Drawing Tool (canvas, all inputs, every `dc*` detail object) so a rep can keep editing from exactly where they left off — not just a static breakdown.
- **Overwrite guard:** loading a saved quote confirms first only if the live canvas currently holds real unsaved work (non-empty `dcPoly`, non-blank shape dimensions, or any non-empty `dc*` detail object). Proceeds immediately onto a blank/untouched canvas.
- **Serialize everything that affects the total or the printed cut sheet** — not just geometry. This includes the job-detail text fields (job name, material, edge profile, sink/cooktop selection, notes) alongside the shape/dimensions/cutouts/seams/chamfers/bar, so reopening a saved quote reproduces both the exact total and an exact reprint of the original cut sheet.
- **Storage: one new field on the existing `sd_quote_history` entry** (`x.drawingState`), not a second localStorage key. The extra payload is small (numbers and short label strings, no images) — no meaningful change to the existing quota picture, and it keeps every existing consumer of `sd_quote_history` (list render, search/filter, KPIs, CSV export, print) working against the one key it already knows, unchanged.
- **Legacy quotes degrade visibly, not silently.** An entry saved before this ships (or a future entry with a `schemaVersion` this build doesn't recognize) still renders its existing fields normally; the new Load action is present but disabled, with a note explaining why. Never a crash, never a silently-missing feature with no explanation.

## Architecture

Pure client-side addition to `stonedesk.html`. No new files, no build step, no server/API changes — matches every other drawing-tool feature shipped this session. Two new functions, mirror images of each other:

- `dcSnapshotDrawingState()` — capture. Reads the exact same DOM elements and globals `calc()`/`printDrawCutSheet()` already read (no parallel re-derivation of what counts as "the drawing" — avoids reintroducing the class of bug already fixed once this session, where a second copy of the same lookup table silently drifted from the original). Returns a plain object:

```js
{
  schemaVersion: 1,
  ctShape: ctShape,
  dims: { 'da-len': gN('da-len'), 'da-dep': gN('da-dep'), /* ...through dd-dep */ },
  dcPoly: JSON.parse(JSON.stringify(dcPoly)),
  dcCutouts: JSON.parse(JSON.stringify(dcCutouts)),
  dcSeams: JSON.parse(JSON.stringify(dcSeams)),
  dcRaisedBar: dcRaisedBar ? JSON.parse(JSON.stringify(dcRaisedBar)) : null,
  dcChamferedCorners: JSON.parse(JSON.stringify(dcChamferedCorners)),
  extras: { /* dh-* splash/waterfall/holes/outlets fields, same set printDrawCutSheet() reads */ },
  jobDetails: { jobName, material, edgeProfile, sinkType, ctType, notes }
}
```

  `JSON.parse(JSON.stringify(...))` matches the existing deep-copy idiom already used for `dcHistory`'s undo-stack snapshots (`stonedesk.html:10706` etc.) — same pattern, not a new one.

- `dcLoadDrawingState(state)` — restore. Sets `ctShape` and every `dims`/`extras`/`jobDetails` field directly onto their DOM inputs, sets `dcPoly`/`dcCutouts`/`dcSeams`/`dcRaisedBar`/`dcChamferedCorners` from the snapshot, then calls the same real rebuild chain `selectDrawShape()` already calls on an ordinary shape switch — `buildEdgeAssignmentArea()`, `buildRaisedBarArea()`, `drawCTPreview()`, `calcDrawing()` — so every existing rendering/pricing function does the actual work. No shape-specific restore logic is written; the function's whole job is populating state and then invoking code that already knows what to do with it. Finally switches the active panel to the Drawing Tool (`sbNav`'s existing panel-switch mechanism) so the rep lands looking at what was just loaded.

Both wrapped in `try/catch`, matching this file's existing `localStorage`/JSON-parsing discipline (Guardian Check 20/21) — a malformed or corrupted snapshot degrades to "no detail available" rather than breaking Save or breaking the History panel's render.

## Save flow

One new line in `sdQuoteSaveHistory()` (`stonedesk.html:3405`), guarded by `typeof dcPoly !== 'undefined'` so a call from a page state where the drawing tool hasn't initialized can't throw:

```js
h.unshift({
  id: Date.now(), date: sdLocalToday(), customer: name, project: stone,
  amount: total, status: 'Pending',
  drawingState: (typeof dcPoly !== 'undefined' && typeof dcSnapshotDrawingState === 'function')
    ? dcSnapshotDrawingState() : null
});
```

Everything else in `sdQuoteSaveHistory()` — the `loadQH()`/200-entry-cap/`localStorage.setItem` sequence, the field-naming compatibility with panel-history's own schema — is unchanged.

## Restore flow (History panel)

`sdHistoryView(id)` (`stonedesk.html:4198-4203`) currently only shows a toast (`customer — $amount — status`) — a stub. It becomes a real modal:

- **Header:** customer, date, status (unchanged from today's toast content).
- **Detail body:** shape type + dimensions, and the same itemized cutout/seam/chamfer/raised-bar breakdown `printDrawCutSheet()` already produces — reusing that function's existing label-building logic against the loaded snapshot rather than writing a second copy of it.
- **Load into Drawing Tool button:** present only if `x.drawingState` exists and its `schemaVersion` is one this build recognizes. On click:
  1. Check whether the live canvas holds real unsaved work (non-empty `dcPoly`, any non-blank shape dimension, or any non-empty `dc*` detail object).
  2. If so, confirm ("Loading this quote will replace your current drawing — continue?") before proceeding. If the canvas is blank/untouched, proceed immediately.
  3. Call `dcLoadDrawingState(x.drawingState)`.

## Legacy / degraded entries

If `x.drawingState` is absent (every quote saved before this ships) or its `schemaVersion` doesn't match what this build expects: the modal still shows customer/total/status/date exactly as today, and the Load button renders **disabled** with a note ("No drawing detail saved — quotes saved before [date] show total only."). The row in the History table itself is unaffected either way — this only changes what `sdHistoryView()`'s modal shows.

## Explicitly out of scope for this pass

- Editing a saved quote's snapshot in place / re-saving over the same history entry (loading always lands in the live Drawing Tool as a fresh editing session; saving again creates a new history entry the same way it does today — no "update existing entry" concept introduced).
- Any change to CSV export or the printed History list (`stonedesk.html:4225`, `4239`) — those continue to read only `customer`/`project`/`amount`/`status`/`date`, unchanged.
- Any server-side persistence of `drawingState` — this is a localStorage-only feature, matching how `sd_quote_history` itself already works.
- Room Layout mode's own state (`dcMode==='room'`) — out of scope, same precedent as chamfer/raised-bar/zoom before it.

## Edge cases

- **Saving a blank/unstarted drawing** (rep fills in customer info and hits Save before drawing anything): `dcSnapshotDrawingState()` still runs and captures whatever's there (likely an empty `dcPoly`, blank dims) — not treated as an error. Loading it back later reproduces the same blank state faithfully, which is correct (nothing was drawn, nothing to lose).
- **A snapshot's shape no longer exists as a valid preset** (only relevant if `ctShape`'s valid value set ever changes in a future release): `dcLoadDrawingState()`'s `schemaVersion` check is the intended guard for this class of drift — a version bump is required any time the snapshot's meaning changes incompatibly, not silently reinterpreted by newer code.
- **Loading a quote onto a canvas that's mid-drag or mid-edit-pass**: the unsaved-work check (`dcPoly` non-empty, etc.) already catches this — the confirm dialog covers it the same as any other in-progress state.

## Testing / verification plan

Same cycle as every feature shipped this session: `node --check` via `tools/checkblocks.py` on every touched block, scoped Guardian mechanical checks, per-task review during implementation, commit, push, then live-verify against `sairn.vercel.app/stonedesk`. Specifically: save a quote with a real chamfer + raised bar + seam + cutout combination and non-empty job-detail fields; reload the page (simulating a return visit); open History, open that entry, confirm the itemized breakdown matches what was drawn; click Load, confirm the canvas, all inputs, and the recomputed total exactly match the original; print the cut sheet from the reloaded state and confirm it matches what the original session would have printed. Separately: confirm an entry saved before this ships (no `drawingState`) opens with Load disabled and the explanatory note, and that neither Save nor the History panel's list/search/CSV/print paths throw on a mix of old and new entries in the same history array.
