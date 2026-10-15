# hank — latest. batch b12, 2026-10-15

**CHAIN TIP** `906903f3` · `HEAD == origin/main`, 0/0, clean, **not forced** ·
b12 range `9f488101..906903f3` · neither override form used · four gate
refusals, four satisfied.

**CONTEXT** 70% of 1000k used, measured from this session's own transcript
(cache_read 690,013). Above the ~60% threshold — **this batch stopped on
instruction, not on completion.**

## DIGEST

All six dispatched items **done**. Live probe `fail=0 couldnot=1`.

1. **b11 sha disagreement** — all three shas exist; the **handoff** was the
   wrong one (it quoted a HEAD *earlier than its own commit*). Corrected,
   re-uploaded, verified Drive-side.
2. **sd_photos** — every real photograph failed to back up (65,536-byte cap vs
   the whole data URL) and the server blamed a migration. 11-rung downscale with
   **each rung's length checked**; `null`, never the original, when none fits.
3. **The 400 misattribution — the dispatch said 12, measured 89 of 98.** One
   `notProvisioned()` with **four** answers, including a third state for an
   unclassifiable 400 that does *not* say "run the migration". **The first draft
   broke five sites** that read the body before the guard.
4. **T17** — `ai_source` on the photo row, `sd_photos` into `AI_SCANNED_TEXT`,
   "Written by AI" on both renders. Not-high-risk **because** `sd_photos` is not
   in `SD_SESSION_GATED` — promoting it is a session decision first.
5. **F1 census SQL** — read `data->>'enc'`, always NULL, and **that zero gates
   clearing the old encryption key**. Fixed to walk `jsonb_each`, plus a new
   part 0 shape guard.
6. **N1–N4 + F6** — a clock time that could be overwritten, a last Owner that
   could be demoted, an exclusion nobody could see, three comments claiming arms
   that do not exist, and a delete that announced a removal that never happened.
7. **New check over 17 apps**: 6 clean, 0 failed, **11 UNPROVEN — the 11 is the
   finding.**

## DECISION-NEEDED

* **MICHAEL — three SQL runs, in this order.** (1) `legacy_ciphertext_census.sql`
  **part 0 first** (both-zero ≠ the precondition); (2)
  `2026-10-14-hank-b11-mar-grant.sql` blocks 1 and 2, **block 2 pasted whole**;
  (3) b10 run-order **block 5** — now reachable from the SAIRNcare UI and failing
  23514.
* **MICHAEL or fourth — T16.** cody's arm wants a replaced clock time **kept or
  appended**; my N1 fix **refuses** the second write. Both close the overwrite;
  pick one. My refusal leaves only a **scheduler-only** route, so a caregiver
  cannot fix their own mistyped clock-in at all.

## OPEN

Eleven items with next steps in `SAIRN-handoff-hank-b12.md`. The live ones:
both b11 SQL blocks and b10's block 5 **unrun**; the census **correct and
unrun**; the 11 UNPROVEN apps; nothing invokes the three new suites; five FMEA
drafts owed; the seam check said COULD NOT TELL; `ZZ-B12-SIZE-PROBE` still in
production (removable without the SQL editor).

## ROUTED

* **cc** — wire the three new `api/` suites into the gate driver; the
  role-picker one **exits 3 by design**, so treat 3 as could-not-run. Plus
  `fmea_draft --save` for five files.
* **cody** — the three compliance arms N4 names.
* **fourth** — the Tier A obligation (3 resources) and its three
  "review hardest" questions.
* **TO ME, UNFIXED** — cody's **T18** (validate `applies_to_positions`
  *contents*; an unmatchable list is UNDECIDED, not a confident no) and their
  **N4** (a comment cites `api/sd-data-grd-session-gate.test.js`, which does not
  exist). I had started reading both and edited neither.

## CLAIMS / STASHES

**b12 ran with NO CLAIM at all** — verified (hover2, hover, cc active; no hank
row). A real deviation, named not inferred. **b13: claim first.**
`stash@{0}` (b10-settings-park) **untouched**; no hook restored;
`settings.json` never committed.
