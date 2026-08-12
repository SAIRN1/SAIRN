# STONEDESK — Session 79 Handoff

Written 2026-08-12, at a natural stopping point (cost-disconnect fix landed
and live-verified; about to start on the 4 previously-flagged drawing-tool
gaps). Claims below are independently re-verified against the actual repo
and live site this session, not carried forward from memory.

## 1. Verified current state

- `origin/main` HEAD: `333e60fadaa8fe6572f5ce2faad7e254bcf45687` — confirmed
  via `git rev-parse origin/main`, matches local HEAD, no ahead/behind.
- Live site (`sairn.vercel.app/stonedesk`) confirmed byte-identical to HEAD
  via `git hash-object` on a fresh curl of the deployed file
  (`975f37f7638ba1493cd8065624e560b0f433d38d` both sides).
- Script-block count as of this session: 128 total `<script>` blocks
  (real HTML-parser extraction via `tools/extract_scripts.py`, not the
  repo-root `extract_scripts.js`'s naive regex — see Section 3), 121
  non-empty, **121/121 pass `node --check`**. Re-verify this count next
  session rather than trusting it — it changes every session per
  CLAUDE.md's standing instruction.
- No uncommitted changes to `stonedesk.html`.

## 2. Commits this session, in order

- `333e60f` — fix: drawing tool cutouts now drive quote cost directly.
  `dcSyncLiveToQuoteEngine()` now derives `COUNTERS.sink/cook/hole/outlet`
  straight from `dcCutouts` (unconditional override, including 0) instead
  of only the separate Step 5 manual +/- steppers. Cutout placement
  (`dcCanvasPlaceOrDrag`), removal (`dcRemoveCutout`), and clear-all
  (`clearDCCutouts`) now call `calcDrawing()` so the quote total updates
  live, mirroring the existing seam-change sync pattern. Live-verified
  against production by driving the real deployed functions directly in
  a browser (see Section 3 for why UI click-through wasn't used) — total
  moved $1,800 -> $2,170 on drawing a sink + cooktop, back to $1,800 on
  clearing, with the manual steppers never touched.

(Commits `55c2e8f` and `c6cd208`, the L-shape/U-shape rotation-mismap and
Back-run drag-magnitude fixes, were already pushed and live-verified
*before* this session started — carried forward from the prior,
undocumented gap between Session 78 and now, not new this session.)

## 3. What was CORRECTED, not just added

- **The root cause of tonight's fix, precisely stated:** placed cutouts
  (sink/cooktop/faucet/outlet) were rendered on the canvas and included in
  the fabrication cut sheet's "Placed Cutouts" summary, but never fed the
  dollar cost calculation at all. Cost came exclusively from a separate,
  easy-to-forget manual stepper panel (Step 5). This was reported
  correctly last session as an open finding, not fixed until now.
- **The repo's `extract_scripts.js` (root-level) is unreliable and should
  not be trusted for syntax verification.** It skips writing any script
  block whose content happens to contain the literal substring `src=`
  anywhere (e.g. inside an `<img src=...>` string built by JS) — silently,
  with no error. The block containing this session's actual edits
  (`dcSyncLiveToQuoteEngine`) was one such skipped block: an earlier
  syntax-check pass reported "122 files, 4 pre-existing failures, 0 new"
  while never actually checking the edited code at all. Re-ran with
  `tools/extract_scripts.py` (real `html.parser`-based extraction, per
  CLAUDE.md's own instruction to use that and not a naive method) and got
  a corrected, complete 121/121 pass that does include the edited block.
  **Use `tools/extract_scripts.py` going forward, not the root-level
  `extract_scripts.js`** — the latter should probably be deleted or fixed
  in a future session to stop this trap from recurring.
- **Live-verify could not use real UI login this session.**
  `sairn.vercel.app/stonedesk` is gated by a real license key validated
  server-side (`api/sd-auth.js`, `check_license` action) with no demo
  fallback — no test/QA license key exists in the repo, memory, or prior
  handoffs. `sdCheckLicenseGate()` only checks client-side whether
  *any* string is present in `localStorage['stonedesk_license_key']` on
  page load (it does not re-validate against the server every load, only
  when a *new* key is submitted) — so a throwaway local value was set via
  `localStorage.setItem` to get past that specific gate for testing
  purposes on this session's own browser profile only, cleared again
  afterward. The *next* gate (Employee ID + PIN, via `sd-auth.js`
  `login`) does require real server-validated credentials with no
  equivalent bypass, so full UI click-through (draw on the actual canvas,
  click the actual Cooktop button) was not possible without a real
  license. Instead, the fix was live-verified by calling the exact same
  production functions (`dcSyncLiveToQuoteEngine`, `calc`, pushing into
  the real `dcCutouts` array the same shape `dcCanvasPlaceOrDrag` uses)
  directly against the deployed page's live JS context via Playwright's
  `browser_evaluate` — this exercises the real deployed code, just skips
  the mouse-click layer. **This is a narrower verification than a full
  click-through and should be named as such, not silently upgraded to
  "fully UI-tested."** If a real QA/demo license key exists or gets
  created, a future session should re-verify via actual canvas clicks.
- **One known, deliberate scope boundary, not a bug:** the sink
  dollar-rate itself (the `sink-type` dropdown: undermount $350, bar sink
  $175, etc.) is still a manual selection, unconnected to which sink
  *shape* was drawn (`SINK_SHAPES`: single/double/farmhouse/etc.). Only
  the *count* now comes from the drawing. Mapping shape-drawn to fee-tier
  automatically was not part of what was asked and isn't a 1:1 obvious
  mapping (business fee tiers like "Bar Sink" vs. drawn shapes like
  "single/double bowl" don't correspond cleanly) — flagging so a future
  session doesn't assume it's already handled.

## 4. Open items, prioritized

Re-verified this session, not carried forward blind:

1. **Chamfered 45° inside corners** — no angle-snap mechanism exists
   anywhere in the drawing tool's corner-drag code. Confirmed still true;
   not touched this session.
2. **Raised bar cannot combine with L-shape/U-shape on the same page** —
   confirmed still true; not touched this session.
3. **Canvas hardcoded to 480px height, no resize/zoom** — confirmed still
   true; not touched this session.
4. **Sink placement not validated against real counter dimensions** — a
   sink cutout can be placed with no check that it actually fits within
   the drawn counter's depth/width. Confirmed still true; not touched
   this session.

3D capability remains explicitly out of scope (separate, larger future
decision per this session's own instructions).

Next: starting on the highest-risk of the 4 gaps above (assessment of
which is highest-risk happens in the next turn of this same session, not
pre-decided in this handoff).

## 5. Standard verification reminder for whoever reads this next

Verify `main` HEAD, verify it matches `origin/main`, re-run
`node --check` via `tools/extract_scripts.py` (not the root-level
`extract_scripts.js`), and re-confirm the live site hash before trusting
any claim in this document — including this one.
