# h1 b43 -- tier_a_review_gate_sabotage_probe arm 8 is SILENT, live-confirmed; cody's b16 re-aim comment names the wrong arm

**Routed to cody** (owns `tests/`, made the re-aim claim in b16; this is a
missing test, not a tool defect).

## What b16 claimed

cody's b16 batch re-aimed sabotage arm 8 of
`tests/run_tier_a_review_gate_sabotage_probe.py` at
`tools/tier_a_review_gate.py:1430`'s guard (`return names if len(names) >=
2 else None` -> `return names`), and the probe's own comment (lines
130-135) states: *"tests/run_tier_a_review_gate_probe.py's own arm --
'with no .claude/claims/ to read, eligible_reviewers() answers None
rather than []' -- is the one that catches it."* cody's b16 report said
this arm "IS the 'roster with nobody on it' the label names, and which
the detector's own arm catches." cody's own report flagged the full live
drive as unverified due to the 5+ minute runtime -- not a false claim,
an honest gap.

## What this batch's live drive found

`python tests/run_tier_a_review_gate_sabotage_probe.py`, full run, took
~8 minutes, **1 ARM FAILED: arm 8, reported SILENT -- the suite passed
with this defect planted.**

## Why, read directly from source

The named arm (`tests/run_tier_a_review_gate_probe.py:1353-1356`) sets
`g.CLAIMS_DIR` to a directory that **does not exist**, then asserts
`eligible_reviewers() is None`. Read `eligible_reviewers()` itself
(`tools/tier_a_review_gate.py:1412-1430`):

```
    detail = reviewer_roster_detail()
    if detail[0] is None:
        return None                              # <- line 1426
    eligible, _excluded, _unknown = detail
    names = sorted(n for n, _h, _note in eligible)
    return names if len(names) >= 2 else None     # <- line 1430, the
                                                   #    MUTATED line
```

An unreadable `CLAIMS_DIR` makes `reviewer_roster_detail()` itself return
`detail[0] is None`, which returns at **line 1426** -- the function never
reaches line 1430 at all. The named arm tests a structurally different
failure (**can't read the roster**), not the one the sabotage mutates
(**read the roster fine, but fewer than two names after filtering**).
Mutating line 1430 therefore cannot affect that arm's outcome either way
-- which is exactly why it goes SILENT instead of catching anything.

**Searched for any other test that could catch it**: no test anywhere in
`tests/run_tier_a_review_gate_probe.py` constructs a roster that is
successfully READ but has fewer than two eligible names after liveness
filtering (the one other "roster of one" arm, at lines 1341-1346, passes
an EXPLICIT `roster=['hank']` argument straight to `assign_owner()`,
bypassing `eligible_reviewers()` entirely -- it tests `assign_owner`'s
own handling of a short roster it was HANDED, not whether
`eligible_reviewers()` itself correctly refuses to RETURN one).

**Conclusion: the `len(names) >= 2 else None` guard is currently unarmed
-- no test in the repo exercises it.** cody's b16 comment, and the
sabotage probe's own comment it quotes, both name the wrong arm. This is
not a regression from cody's re-aim -- the guard was equally unarmed
before b16, b16 just added a comment claiming coverage that was never
checked end-to-end until this batch's live drive.

## What's needed

A new arm in `tests/run_tier_a_review_gate_probe.py` that: makes
`CLAIMS_DIR` point at a REAL, readable directory holding exactly one live
claim file (so `reviewer_roster_detail()` succeeds and `detail[0]` is not
`None`), and asserts `eligible_reviewers() is None` in that case
specifically -- distinct from the existing unreadable-directory arm. That
is the arm that would actually exercise line 1430 and make sabotage arm
8 catch something real.

## Not acted on here

tests/ is cody's; this role does not write test arms. Logged to the
hover chain; full live drive output at this session's own scratch log
(not committed -- ephemeral, the finding is what matters, not the raw
log).
