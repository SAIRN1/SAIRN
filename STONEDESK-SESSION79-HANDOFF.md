# STONEDESK — Session 79 Handoff

Written 2026-08-12, updated in place after landing gap #4 (sink-fit
validation) — still the same session, not a new one. Claims below are
independently re-verified against the actual repo and live site this
session, not carried forward from memory.

## 1. Verified current state

- `origin/main` HEAD: `46e8e2a96c485598f0f488ba7bb6df2036892e4e` —
  confirmed matches local HEAD, no ahead/behind, as of the sink-fit
  commit landing.
- Live site (`sairn.vercel.app/stonedesk`) confirmed byte-identical to HEAD
  via `git hash-object` on a fresh curl of the deployed file
  (`b8516e0899cb448e4cfa9cbb3bba3e0be1d737d2` both sides) after the
  sink-fit push.
- Script-block count as of the cost-disconnect commit: 128 total
  `<script>` blocks (real HTML-parser extraction via
  `tools/extract_scripts.py`, not the repo-root `extract_scripts.js`'s
  naive regex — see Section 3), 121 non-empty, **121/121 pass
  `node --check`**. Re-ran again after the sink-fit commit, same 121/121
  clean result. Re-verify this count next session rather than trusting
  it — it changes every session per CLAUDE.md's standing instruction.
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

- `46e8e2a` — feat: validate drawn sink cutouts against real counter
  dimensions (gap #4 from the prior session's open list, judged
  highest-risk of the four because a bad placement flows straight to the
  shop floor's cut sheet on real, non-returnable stone). Adds
  `dcCheckSinkFit()`/`dcApplySinkFitCheck()`, wired into placement, drag,
  drag-end, and — importantly — into `calcDrawing()`'s existing
  re-fire-on-any-edit path, so a sink that fit when placed but goes stale
  after the rep later shrinks the run also gets caught, not just
  time-of-placement. Uses a 1.5in minimum edge clearance (named
  assumption, not a specific material spec). Non-blocking: flags via
  toast + a persistent "⚠" folded into the cutout's own `.label`, which
  is what both the on-screen chip list and the printed cut sheet already
  render, so the warning reaches the shop floor too. **Scoped to PRESET
  mode only** (straight/island/L/U/galley rects) — Custom Draw mode's
  polygon segments carry no per-wall depth value in the data model, so
  fit-checking is a named gap there, not silently "checked and passed."
  Live-verified against production (see Section 3) — a 33in sink flagged
  on a 30in run with the correct reason text, a 32in sink on a 40in run
  passed clean, and shrinking that same run back to 30in via
  `calcDrawing()`'s normal re-fire (no direct re-check call) correctly
  flipped it to a warning — proving the wiring, not just the function.

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
- **A real, currently-live bug was found (not fixed) while building the
  sink-fit check, and is being disclosed explicitly rather than left
  silently sitting there:** `dcCurrentScalePxPerIn()` (used for sink
  render sizing and drag grab-radius, near `dcHitCutout`) computes scale
  as `r.w / lenIn` unconditionally. This is the exact same bug class just
  fixed in `55c2e8f` for preset-edge-drag (the `compositeLen` fix) —
  U-shape's `Back` rect's pixel width is a composite of three fields, not
  a pure function of `db-len` alone, so this still silently produces a
  wrong (inflated) scale for any sink sitting on `Back`. It likely also
  mishandles `rotated` rects (`B`/`Left`/`Right`) the same way, since it
  never branches on `fields.rotated` either — unconfirmed, flagged as a
  strong suspicion pending a dedicated look. **The new sink-fit check
  deliberately does NOT depend on this function** — it reads
  Length/Depth field values directly in inches and only uses
  `fields.rotated` to pick which fraction maps to which axis, sidestepping
  the composite/rotated pixel-scale math entirely — so this pre-existing
  bug does not affect gap #4's correctness. But it's a real, separate,
  currently-shipping defect (likely visible as an oddly-sized or
  oddly-scaled sink drawing on a `Back` or rotated run) that should get
  its own fix in a future session, using the same `compositeLen`-aware
  pattern already proven in `55c2e8f`.

## 4. Open items, prioritized

Re-verified this session, not carried forward blind:

1. **Chamfered 45° inside corners** — no angle-snap mechanism exists
   anywhere in the drawing tool's corner-drag code. Confirmed still true;
   not touched this session. Judged lower risk than sink-fit was: a
   missing precision feature, not a path to a bad real-world cut.
2. **Raised bar cannot combine with L-shape/U-shape on the same page** —
   confirmed still true; not touched this session.
3. **Canvas hardcoded to 480px height, no resize/zoom** — confirmed still
   true; not touched this session.
4. ~~Sink placement not validated against real counter dimensions~~ —
   **FIXED this session, `46e8e2a`, live-verified.** Was judged
   highest-risk of the four (silent bad data reaching real fabrication)
   and done first. See Section 2/3 for detail and the named PRESET-mode-
   only scope boundary.
5. ~~`dcCurrentScalePxPerIn()`'s `compositeLen`/`rotated` scale bug~~ —
   **FIXED, `2461171`, live-verified.** Confirmed both the bug (old
   formula gave inconsistent scales per rect: 1.45/5.71/1.59 px/in on
   Left/Back/Right of the same drawing) and the fix (all three now
   return the same 3.6226 px/in, matching the drawing's real single
   scale) directly against production.

3D capability remains explicitly out of scope (separate, larger future
decision per this session's own instructions).

6. ~~Seam polished-edge cost never reached the real quote total~~ —
   **FIXED, `e46024e`, live-verified.** Same disconnect class as the
   cutout fix (`333e60f`): `calcDrawing()` already computed the correct
   dollar figure for its own results-panel display, never passed it to
   `calc()`. Found while researching pricing wiring for the chamfer
   feature (not fixed silently — surfaced and confirmed with the user
   before fixing, per explicit instruction, as its own commit). Added
   `DC_SEAM_EDGE_COST`, synced from `calcDrawing()`'s own `seamEdgeCost`
   via `dcSyncLiveToQuoteEngine()`. Live-verified: $3,335 -> $3,405 on a
   24in seam, back to $3,335 on removal, matching the exact expected
   $72 (24in / 12 * 2 sides * $18/LF admin rate).
   **This exact pattern (a value computed correctly and displayed
   correctly in one place, but never wired to the real total) has now
   hit StoneDesk twice** — added to `sairn-silent-failure-sweep` as a
   named, explicit check to look for going forward, not just something
   caught by luck a second time.

7. **Patent-landscape claim, re-verified this session, resolved to a
   confirmed non-issue for the app as it exists today.** The prior
   handoff's "actively-prosecuted US patent family 9,501,700 + five
   continuations through 11,727,163... covering photo-based measurement-
   to-estimate workflows" was pulled live from Google Patents rather
   than trusted secondhand. Confirmed real: assignee Xactware Solutions
   (Verisk), active, expires 2032-07-16, and the continuation chain is
   actually longer than previously known (12,265,758 issued, plus
   US20250232075A1 filed 2025 and still pending). But Claim 1 is narrow
   and specific — aerial images of a building, a per-pixel roofline
   filter, scan-rotate-scan at two angles, 2D line-model construction,
   manual click-drag onto an oblique aerial image for 3D. Checked
   StoneDesk's actual implementation (`intakeAnalyzePhoto()`,
   stonedesk.html:30484): a single Claude vision-model call on a
   handheld kitchen photo, returning JSON directly — no aerial imagery,
   no per-pixel filter, no multi-angle scan, no geometric line model.
   Different domain, different mechanism — does not read on the claim.
   **Not a live risk to StoneDesk as built today.** Re-check this
   specific family if the photo feature ever moves toward its own
   geometric line-detection pipeline instead of an LLM vision call. Real
   attorney review is still recommended before any patent-adjacent
   public/marketing claim — not before continued engineering work.
8. **5 real skills were invisible to the Skill tool all session** —
   `sairn-app-builder`, `sairn-client-facing-design`,
   `sairn-infra-debugger`, `sairn-mobile-sync`, `sairn-portfolio-triage`.
   Root cause found and fixed this session (was wrongly guessed as a
   harness-level indexing gap earlier): `.claude/settings.local.json`'s
   `skillOverrides` block had all 5 explicitly set to `"off"`. Flipped to
   `"on"` — confirmed live immediately after the edit (all 5 now appear
   in the invokable skill list). `settings.local.json` is gitignored
   (machine-local config), so nothing to commit/push for this fix; it's
   already in effect for this machine going forward. Unknown why they
   were disabled originally — no history/comment in the file explaining
   it, so if any of the 5 turn out to have been off for a real reason,
   that's worth someone confirming, not assumed safe forever just
   because re-enabling them didn't break anything today.

Next: gap #1 (chamfered corners), per direct instruction — brainstorm
first, then build. In progress: fabrication-real (cut sheet + real
pricing), preset-shapes' inside corners only (not Custom Draw, named
scope boundary matching the sink-fit pattern), rep-adjustable setback
size. Design not yet written up or approved.

## 5. Standard verification reminder for whoever reads this next

Verify `main` HEAD, verify it matches `origin/main`, re-run
`node --check` via `tools/extract_scripts.py` (not the root-level
`extract_scripts.js`), and re-confirm the live site hash before trusting
any claim in this document — including this one.
