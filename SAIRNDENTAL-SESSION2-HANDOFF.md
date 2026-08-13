# SAIRNdental — Session 2 Handoff

Written at natural stopping point (plan fully executed, pushed, all review
rounds clean). Claims below are independently verified against the actual
repo, not assumed from memory.

## 1. Verified current state

- `origin/main` HEAD: `c6ca92f1cf7005d353185c286316d8e17835f864` — confirmed
  via `git fetch origin main && git rev-parse origin/main`.
- `python tools/checkblocks.py sairndental.html` — `TOTAL_BLOCKS:1`,
  `FAILED_BLOCKS:0`, re-confirmed at HEAD before push.
- This app has no automated test runner — all verification is
  syntax-check plus hand-traced/manual code-path tracing, matching this
  file's established convention (confirmed: no `.test.js` file exists
  anywhere referencing `sairndental.html`).

## 2. Commits this session, in order

1. `d0d1e37` — docs: spec — SAIRNdental pediatric fields (guardian/parent
   contact for minors)
2. `ca9fa07` — docs: plan — SAIRNdental pediatric fields
3. `78f3d25` — feat: pediatric guardian/parent contact fields, auto-shown
   and required for minor patients (Task 1)
4. `e13456d` — fix: `guardian_relationship` blank for non-minor patients,
   not silently defaulted to first dropdown option *(caught in Task 1's
   own task-scoped review)*
5. `b8ee59f` — fix: local-date parsing for minor detection (UTC boundary
   bug), gate all four guardian fields consistently, fix empty-state
   colspan *(caught in the final whole-branch review — see Section 3,
   this is the important one)*
6. `c6ca92f` — feat: guardian display keys off stored data, not live age
   *(human-directed change after the final review, made and pushed
   post-merge-approval — see Section 3)*

Executed via `superpowers:brainstorming` → `superpowers:writing-plans` →
`superpowers:subagent-driven-development` (one implementer + one
task-scoped reviewer for the single task, one final whole-branch reviewer
on Opus across the full range, one fix wave, one scoped re-review, then
one additional human-requested change with its own review). Ledger:
`.superpowers/sdd/2026-08-13-sairndental-pediatric-fields/progress.md`
(workspace not yet deleted — see Section 4).

## 3. What was CORRECTED, not just added

- **A real Critical bug: `isMinorPatient()` used `new Date(dob)` (UTC
  parsing) then read it back with local getters, misclassifying a genuine
  17-year-old as an 18-year-old adult the day before their actual
  birthday, in any negative-UTC-offset timezone (i.e. every US practice).**
  This is the exact same bug class this project already root-caused and
  fixed platform-wide on 2026-08-06 (the "fdate" UTC bug) — it recurred
  here because this is new code in a file whose own existing
  `dntLocalToday()` helper already avoids the bug correctly, but the new
  `isMinorPatient()` didn't reuse that pattern. Caught by the final
  whole-branch review (Opus), not by the task-scoped implementer or
  reviewer, and not by the plan's own hand-traced verification steps —
  the reviewer explicitly noted the plan's own Scenario 5 boundary test
  used `new Date(...).toISOString().slice(0,10)` to construct its test
  date, the same UTC round-trip as the bug, so it could never have caught
  this. Fixed in `b8ee59f` by parsing DOB into local y/m/d components
  before constructing the `Date`, matching `dntLocalToday()`'s existing
  convention. **Lesson for future date-boundary verification on this
  platform: constructing a test date via `.toISOString()` re-introduces
  the exact UTC round-trip most local-date bugs hide inside — build test
  dates from local `Date` component setters instead, the same way the
  fix itself must.**
- **A partial fix that only covered 1 of 4 fields.** Task 1's own review
  caught `guardian_relationship` defaulting to `"Mother"` for every
  patient (adults included) and that got fixed in `e13456d` — but the fix
  only gated that one field; `guardian_name`/`guardian_phone`/
  `guardian_email` still leaked stale hidden-input values onto an adult's
  record if a DOB was corrected from a minor date to an adult date before
  saving. Caught by the final whole-branch review, not the task reviewer
  that approved the first partial fix. Fixed in `b8ee59f` by gating all
  four fields on one shared `isMinor` variable instead of re-deriving (or
  half-deriving) the check per field.
- **A spec-mandated display behavior that turned out not to be what was
  actually wanted, once its real consequence was made concrete.** The
  design spec explicitly specified the Patients table's Guardian column
  re-checks `isMinorPatient(p.dob)` live at render time. The final
  reviewer surfaced (as a Recommendation, not a bug — the spec was
  followed correctly) that this means a patient's stored guardian info
  visually disappears from the table AND from CSV export the moment they
  turn 18, even though nothing is deleted. Presented to Michael as an
  explicit decision rather than silently changed or silently left as
  spec'd; he chose to key display off stored data (`guardian_name`
  non-empty) instead. Fixed in `c6ca92f`, its own small review cycle,
  after the rest of the feature was already "ready to merge."

## 4. Open items, prioritized

1. **This plan's SDD workspace has not been deleted.**
   `.superpowers/sdd/2026-08-13-sairndental-pediatric-fields/` (ledger,
   briefs, reports, diff packages) still exists in the worktree. Per
   `subagent-driven-development`'s own Finish step, delete it once this
   handoff is confirmed accurate.
2. **This session's worktree
   (`worktree-sairndental-pediatric-fields`) has not been
   finished/merged via `finishing-a-development-branch`.** All commits
   are already fast-forward-merged onto `main` directly (confirmed:
   `origin/main` HEAD equals this branch's HEAD) — nothing left to merge,
   but the branch/worktree itself should still be cleaned up rather than
   left indefinitely.
3. **`onPtDobChange()` is not called at page `init()`.** Logged as a new
   `SAIRN-BACKLOG.md` entry this session ("SAIRNdental pediatric guardian
   fields — `onPtDobChange()` not called at page init") — a browser that
   restores a previously-typed DOB value on reload can leave the guardian
   field group visually hidden while save-time validation still correctly
   requires it, producing a confusing (but not unsafe) UX. The actual
   safety property — no minor patient record saves without guardian
   info — is unaffected, since `addPatient()` re-evaluates
   `isMinorPatient(dob)` independently of the group's visibility state.
4. **No live-browser verification happened this session** — every
   verification step (implementer, task reviewer, final reviewer, fix-wave
   re-reviewer) was a hand-traced code walkthrough, because no browser
   was available in this environment. This matches the plan's own explicit
   fallback instruction, but a real browser session/Playwright check
   (matching the standard `sairn-visual-review` practice used elsewhere on
   this platform) would upgrade the verification from "the code trace says
   this is correct" to "observed working."
5. **No SQL/server-side validation of the minor-requires-guardian rule** —
   unchanged from the spec's explicit scope decision (matches
   `dnt_patients`' existing JSONB-blob, client-enforced-only convention
   for every field, not a new gap introduced by this feature).

## 5. Standard verification reminder for whoever reads this next

Verify `origin/main` HEAD, verify which branch/worktree you're actually
in, and re-run `python tools/checkblocks.py sairndental.html` before
trusting any claim in this document — including this one. In particular,
if you're about to touch date/age logic anywhere else in this file (or
any other SAIRN app), re-read Section 3's UTC-parsing lesson first — this
is the second time this exact bug class has shipped on this platform.
