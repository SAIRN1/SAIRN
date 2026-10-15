# hank b12 — the captured red, the green, and the ablations

Every file here is a run's real stdout. **The red is kept because a green suite
proves nothing about what it would have caught.**

| item | red | green | ablation |
|---|---|---|---|
| 2+3 — sd_photos size, the 400 misattribution, T17 | `b12-item2-red.log` — 6 passed / **13 failed** / 4 unproven, run against HEAD in a detached worktree | `b12-item2-green.log` — 26 / 0 / 0 | `b12-item2-ablation.log` — eight layers |
| 4 — N1–N4 and the SAIRNfreedom deletes | `b12-item4-red.log` — 10 passed / **10 failed** | `b12-item4-green.log` — 21 / 0 / 0 | `b12-item4-ablation.log` — six layers |
| 5 — the role picker vs the DB CHECK | — (a new check, not a fix) | `b12-item5.log` — 6 clean / 0 failed / **11 UNPROVEN** | `b12-item5-ablation.log` — two layers |

`b12-np-rewrite.log` is the mechanical rewrite's own output: **89 targets, 9
skipped**, each skipped site named with the reason (it already reads the body
and discriminates, and a `Response` body can be consumed once).

`b12-item4b-before.log` is b11's third-state suite re-run clean at the start of
this batch, so the b12 changes can be told from a pre-existing red.

## THREE ABLATIONS SURVIVED AND ALL THREE WERE SUITE DEFECTS, NOT CODE ONES

That is the finding worth keeping from this batch's methodology, and each is
recorded in its own ablation log rather than quietly fixed:

* **`D1`** was a source grep for `showToast(` and could not see an early
  `return`. The function is now extracted and **run against a stub**.
* **`A3`** survived because the FIXTURE served `text()` after `json()` had
  already been called — which a real `fetch` Response never does. The mock now
  models single consumption, and `A8` fails without the pre-read argument.
* **the `sfDeleteEvent` toast** survived because the two F6 fixes are each
  sufficient alone, so neither was individually *necessary* for any arm. New
  arm **`F6e`** builds the stale-pointer state directly — the state every row
  written before today is in.

## And two defects the arms found in my own work

* `A6` reported `routed=0` as a failure against correct code, because the
  detector tested for `NOT_PROVISIONED` — the string of the **unfixed** shape.
  A detector that can only see the defect cannot see the fix.
* The role-picker check's first draft was **permissive**: it collected every
  `check (role in (...))` from any file *mentioning* the table, so sairncare
  reported 18 allowed roles drawn partly from sairnroofing's schema. Found by
  reading the output, not the exit code — the run already said "0 with a
  refused role".

`../b12_live_gate_probe.py` / `.out` is the post-push live verification:
**fail=0 couldnot=1**, and the could-not-run is named with the five candidates
tried. Its one written row is enumerated with its removal SQL in
`../live-residue/2026-10-14-hank-b12-sd-photos-probe.json`.
