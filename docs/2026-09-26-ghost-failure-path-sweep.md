# The ghost failure path — a warning that reads as present and cannot fire

**Run 2026-09-26 (Hank), after catching three of one family in a single
afternoon.** Michael's dispatch named the class: *"a warning whose failure path
is unreachable, or a check reading the wrong field so it always returns the same
result. Find others."*

## The three, and what they actually have in common

| | Where | The ghost |
|---|---|---|
| 1 | `pcToggleSlab()` / `slabSyncOne()`, `stonedesk.html` | The caller tested `ok === false` to warn *"the catalog on the web has NOT changed"*. The callee returned `undefined` on every path. **A failed publish said "Slab published to the catalog."** |
| 2 | `tools/load_compliance_seed.py` | The before/after probe sent `payload.check` where the endpoint requires `payload.requirement_type`. Both probes answered 400, two identical 400s compare equal, so it printed *"UNCHANGED — nothing this app can use was loaded"* on **every run it had ever made** — including the one where all three WV rules landed. |
| 3 | same file | *"The answer must have CHANGED"* conflated **nothing loaded** with **already loaded**. The endpoint upserts, so an idempotent re-run is identical by design and the criterion called that a failure. |

**The common shape is not "a bug in a check". It is a VERDICT WHOSE TWO
OUTCOMES ARE COMPUTED FROM SOMETHING THAT CANNOT DIFFER.** In (1) the tested
value cannot occur. In (2) both operands are the same refusal. In (3) the two
cases produce the same observation. Every one of the three reads as a working
control on every future review of it, which is why none was found by reading the
code that was wrong — each was found by DRIVING the thing the control claimed to
make observable.

**And that is why this is worse than a missing check.** A missing check is a gap
somebody can see. A present, reviewed, unreachable check is evidence for the
wrong conclusion, and the reviewer who added it was not mistaken to add it. In
(1) nothing was wrong with `pcToggleSlab` — the defect was a **disagreement
between two functions**, which no single-file review catches by construction.

## What is mechanically decidable, and what is not

Only (1). `tools/unreachable_failure_path_scan.py` decides it: a function whose
every `return` is bare has exactly one possible value, so a caller comparing its
result against any other literal has a branch that cannot be taken.

(2) needs the endpoint's required-field list joined to every caller's payload,
across files and two languages. (3) is a judgement about what a comparison means.
**Both are named in the tool's own header so the gap is a decision rather than an
omission** — and (2) is worth building next, because it is the shape that hid a
successful load behind a failure report.

## The result, and why the zero is worth anything

    python tools/unreachable_failure_path_scan.py

**102 files, CONFIRMED 0, advisory 0.** `pcToggleSlab`/`slabSyncOne` was the only
instance on the platform and it is fixed.

**A ZERO FROM A SCAN THAT CANNOT SEE ITS OWN DEFECT IS WORTH NOTHING, so the
zero is ablated rather than asserted.**
`tests/run_unreachable_failure_path_probe.py` restores the **real pre-fix
`slabSyncOne` body into the real `stonedesk.html`** and demands the scan report
the pair. **The caller is not mutated** — `pcToggleSlab` is still in the file
exactly as it was when its branch could not fire, so the arm is one half of a
real disagreement rather than a synthetic fixture. Driven against the pre-fix
file from history, the scan prints:

    slabSyncOne() is BARE at :38889 -- every return is bare, so its only value is undefined
    :43004 bound to `ok`, then compared against false -- that branch CANNOT be taken

**34 bare functions are NOT JUDGED and the report says so.** Their name is
defined more than once in their file — `stonedesk.html` defines `render` 23 times
in 23 unrelated IIFEs — so which definition a caller reaches cannot be told from
position. Pairing a caller at `:30570` with a definition at `:38046` is
arithmetic, not analysis. **A scan silently declining to judge is
indistinguishable from one that judged and found nothing**, which is the same
defect class this document is about, so the refusal is printed.

## The scan's own first draft committed the defect three times

Recorded because it is the cheapest evidence that this class is not somebody
else's mistake.

1. **A wrapper that looked like it used the canonical tool and did not.** It
   tried `jscomments` for functions named `strip_preserving_length`,
   `strip_keep_length` and `blank_comments` — **none of which exist** — and fell
   through, silently, to a hand-rolled fallback. That fallback read the `//` in
   `fetch('https://…')` as a comment, desynchronised, and reported
   `subxCall()` — which has `return null;` and `return data;` — as having no
   returns at all. Now it imports `jscomments.strip_comments` and **fails closed
   (exit 2, naming the tool) with no fallback**, per PR §1.11: an eighth
   hand-rolled stripper is the defect that file exists to end.
2. **A blanking pass that erased the thing it was measuring.** Nested function
   bodies were blanked to spaces, so `return function(t){…}` left a bare
   `return` behind and every function returning a function read as bare.
   `computeTaskDates()` was reported on exactly that. Nested bodies become a
   `0` placeholder now.
3. **An expression-bodied arrow with no body to skip.** `dcPoly.map(p => p.x)`
   has no braces, so "find the next `{`" found the function's **own**
   `return { x:…, y:… }` two lines later and blanked it. All five advisory
   findings in the first real run were that, and **every one was a false
   positive.**

**And a fourth, in a different file, within the hour: `--static` on
`tools/mech_panels_live_check.py` printed *"no network, no writes"* and ran the
entire live half**, writing two rows. A flag that reads as gating and gates
nothing, committed by the author of this sweep while writing this sweep.

## Two more of the family, found while doing other work today

Neither is in the scan's scope; both are the same shape and are recorded here
rather than only in their commits.

- **A pin that counted itself.** The `sd_comms` retier cell quoted the
  not-yet-individually-read marker while explaining the row no longer carried
  it — and this register's re-count command anchors on a row-start marker plus
  that phrase, so a **corrected** row counted as still uncorrected and the figure
  did not move. Section 2 of `docs/CRITICALITY-TIERS.md` already records this
  with the PROSE matching its own count; this was a corrected ROW matching it.
- **A vacuous negative assertion.** In
  `tests/customer_delete_does_not_resurrect.js`, `!written.includes('C-1')`
  ("the deleted customer was not pushed back up") had been passing **trivially**
  since the batching change emptied `written` — the negative half of a stale pin
  keeps reporting a pass it is not testing. Now guarded by asserting the list is
  non-empty first.

## Where this sits

- `tools/unreachable_failure_path_scan.py` — the checker. REPORT ONLY and not a
  gate, by decision: it is brace matching rather than a parser, and a false
  positive that blocked a push would get it disabled, after which it protects
  nothing.
- `tests/run_unreachable_failure_path_probe.py` — the ablation, on the real file.
- `tools/sync_write_result_check.py` — the adjacent class, and the *advisory*
  half of this scan is deliberately its shape rather than a second opinion on it.
- `tools/discarded_verdict_check.py` — the mirror image: a refusal that is
  computed and ignored.
- `tools/optimistic_success_scan.py` — a success message shown before the thing
  succeeded.
