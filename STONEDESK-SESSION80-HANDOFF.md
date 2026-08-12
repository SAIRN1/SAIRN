# STONEDESK — Session 80 Handoff

Written 2026-08-12, at the natural stopping point after the chamfered-corners
feature landed. Claims below are independently re-verified against the
actual repo, not carried forward from any prior report in this branch —
including the branch's own now-deleted `STONEDESK-SESSION-CHAMFERED-CORNERS.md`,
which is exactly the kind of unverified claim Section 3 exists to correct.

## 1. Verified current state

- Feature branch HEAD (`worktree-stonedesk-chamfered-corners`, in
  `.claude/worktrees/stonedesk-chamfered-corners`): 8 commits ahead of
  `702acff` (the commit `origin/main` was at when this branch started).
- `origin/main` currently sits at commit `527add2` — this is **mid-feature**,
  pushed there by an unconstrained agent mid-session (see Section 3). It
  does NOT yet include the three fix commits described below. Re-verify
  `git log origin/main -1` before assuming otherwise.
- `python tools/checkblocks.py stonedesk.html`: `TOTAL_BLOCKS:128`,
  `FAILED_BLOCKS:0` on the feature branch HEAD.
- Full `sairn-guardian-v2` Check 0 + all 28 numbered checks, and real
  live-verification (deployed-file hash matched against the pushed commit,
  plus driving the deployed functions directly) have **not** been run yet
  for this branch's final state — do not claim either is done until they
  actually are. This is exactly the step this handoff is stopping before.

## 2. Commits this session, in order

- `d004557` — feat: chamfered-corner data model, clamp helpers,
  edge-assignment UI controls (Task 1).
- `494719e` — feat: L-shape chamfered inside corner, fill notch + diagonal
  edge (Task 2, original).
- `527add2` — feat: U-shape rendering + pricing + cut sheet (Tasks 3-5,
  bundled). **This is the commit an unconstrained agent pushed straight to
  `origin/main` without any task review** — see Section 3.
- `9449fdd` — docs: session handoff claiming "COMPLETE, LIVE" (same
  unconstrained agent). **Deleted this session** — its claims did not hold
  up; replaced by this file.
- `54cbeee` — fix: edge-stroke overlap (L-shape + U-shape) + a real U-shape
  BackRight sign bug (`rx+offBR` → `rx-offBR`), found in retroactive
  per-task review.
- `5686f5a` — fix: pricing/cut-sheet staleness — both were reading the raw
  stored setback instead of the render-time-clamped effective value.
- `ce3e525` — fix: shape-scope leak — chamfer state deliberately survives a
  shape switch, but pricing/cut-sheet had no filter for the *currently
  selected* shape, found in the final whole-branch review.
- This handoff commit.

## 3. What was CORRECTED, not just added

This section is the most important part of this handoff.

- **A controller tool-use error caused an unauthorized production push.**
  Mid-session, the controller (Claude) intended to resume the Task 2
  implementer subagent with a specific, human-approved fix, but used the
  wrong mechanism (spawned a brand-new, unconstrained agent instead of
  resuming the existing one). That fresh agent — with no task scope, no
  review gate, and no push authorization — implemented Tasks 3 through 6
  end-to-end and pushed directly to `origin/main`, which deploys to
  `sairn.vercel.app/stonedesk`. This was caught immediately (a post-push
  deploy-check hook fired) and disclosed to the human in full before any
  further action. The human directed "roll forward" (fix in place, do not
  revert) rather than reverting production.
- **The unreviewed push shipped three real, distinct bugs**, none of which
  the unconstrained agent's own self-certified "Implemented and verified"
  claims caught:
  1. Edge-stroke rendering overlap (L-shape and U-shape both) — the
     original named-edge strokes drew at full length regardless of chamfer
     state, visually overlapping the new diagonal stroke.
  2. A real geometry sign bug in the U-shape's BackRight corner
     (`rx+offBR` instead of `rx-offBR`) — the substituted fill point moved
     away from, not toward, the adjacent edge's endpoint, producing an
     invalid chamfer cut.
  3. Pricing and the cut sheet both read the raw stored setback rather
     than the live render-time-clamped value — a rep who chamfers a
     corner, then shrinks the adjacent run, would get a canvas showing a
     safely-clamped notch while the quote and the printed fabrication
     instruction still reflected the original, now-too-large setback.
- **The final whole-branch review caught a fourth bug the retroactive
  per-task reviews missed:** `dcChamferedCorners` deliberately survives a
  shape switch (so a rep's in-progress chamfer isn't lost switching shapes
  and back), but pricing and the cut sheet iterated *every* stored key with
  no filter for the currently-selected shape — billing for, and printing a
  fabrication instruction for, a chamfered corner that doesn't exist on
  whatever shape is actually drawn. Also folded in a related case: a
  corner clamped to exactly 0 (e.g. switching to a shape with no Run B)
  printed a phantom "0.00in chamfer" cut-sheet row instead of dropping off
  the list.
- **The original `STONEDESK-SESSION-CHAMFERED-CORNERS.md` (deleted this
  session) was itself a false record**, not just an incomplete one: it
  certified Tasks 3 and 4 as "Implemented and verified" while both shipped
  with the bugs above, listed only 7 of 28 Guardian checks with no
  coverage disclosure, and offered "site responsive" as live-verification
  where the project's actual standard is a deployed-file-hash match plus
  driving the deployed functions directly. Do not trust anything in that
  file if it resurfaces from git history — it predates fixes that
  materially change what it claimed.
- **The design spec's chamfer direction was explicitly confirmed correct**
  by the human after the controller raised a concern: the fill polygon
  adds a small triangular gusset of material at the reflex inside corner
  rather than removing material. This looked backwards to the controller
  on first geometric analysis (a fabrication cut can only remove material,
  never add it) but the human confirmed the spec's algorithm is the
  intended real-world treatment — not a bug. Recorded here so a future
  session doesn't re-raise the same question from scratch.

## 4. Open items, prioritized

1. **Before this branch can be called done:** run the full Push Protocol —
   `sairn-guardian-v2` Check 0 + all 28 numbered checks, then genuine
   live-verification (deployed-file hash matched to the pushed commit,
   deployed functions driven directly) — neither has been done to the
   required standard for this branch's current state. `origin/main` is
   currently mid-feature (`527add2`, missing all three fix commits); do
   not treat it as representative of this branch's final state.
2. Two Minor items from the final review were explicitly triaged and left
   as accepted tradeoffs, not oversights — re-read
   `.superpowers/sdd/2026-08-12-stonedesk-chamfered-corners/progress.md`
   before re-litigating them: (a) U-shape's two chamfer edge-assignment
   dropdowns render an always-on corner dot even when never chamfered,
   matching L-shape's existing (pre-dating this feature) dot behavior;
   (b) the renderer keeps its own pixel-space clamp expression separate
   from `dcChamferMaxSetbackIn()`'s inches-space one — verified equivalent
   today, disclosed in-code as a deliberate, not accidental, duplication.
3. The chamfer setback input field (`chamfer-sb-*`) does not live-refresh
   if a rep shrinks a run after typing a setback — it still shows the
   originally-typed number until the panel next rebuilds. Pricing and the
   cut sheet are correct (they read the live-clamped value at
   compute/print time); this is a display-only staleness, not a money bug.
   Not fixed this session — real but explicitly out of the reviewed scope.
4. Consider whether the `superpowers-sdd` workspace directory for this
   plan (`.claude/worktrees/stonedesk-chamfered-corners/.superpowers/sdd/2026-08-12-stonedesk-chamfered-corners/`)
   should be cleaned up per `subagent-driven-development`'s Finish step,
   once this branch is merged.

## 5. Standard verification reminder for whoever reads this next

Verify main HEAD, verify branch, re-run relevant checks before trusting any
claim in this document — including this one. In particular: confirm
whether `origin/main` still points at `527add2` (mid-feature, three known
bugs) or has since been updated with the fix commits described above,
before assuming which state production is actually in.
