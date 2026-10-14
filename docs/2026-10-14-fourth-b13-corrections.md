# CORRECTIONS to fourth's b12 record — two evidence lines, each corrected by a command — 2026-10-14, fourth b13

**Both corrections are to MY OWN evidence.** Neither is a finding about another
session's code, and neither changes a count: what changes is what the b12
record is entitled to claim it measured.

**One driver proves both, and it refuses if either correction is not
reproducible:**

```
CMD python scratchpad/corrections_b13.py          ->  exit 0
    8 arm(s), 0 failing
```

---

## CORRECTION 1 — the A1 bad-input fixture WAS ITSELF FAIL-OPEN, and the b12 report's account of it is right about the fact and incomplete about the mechanism

**What b12 said** (`SAIRN-report-fourth-b12.txt`, ITEM 1 (a)): my first version
of the A1 fixture wrote a `report_only_checks.py` that named `NOT_PROMOTED` in
a comment, the reader is a substring search, and the arm returned exit 0 where
it must return exit 2.

**That is true, and it is now driven rather than recounted:**

```
CMD python scratchpad/corrections_b13.py
  ok   C1a the ORIGINAL fixture text (comment names the token)   want 0  got 0
       FAIL-OPEN: reads as a pass
  ok   C1b the FIXED fixture text (token-free comment)           want 2  got 2
       COULD NOT CHECK -- ...
```

C1a rebuilds the original fixture byte-for-byte —
`# a report_only_checks.py with no NOT_PROMOTED block at all` — and shows the
real program exiting **0** on it. C1b is the same tree with the token removed
from the comment and nothing else changed: **exit 2**, COULD NOT CHECK.

**THE CORRECTION IS THE PART b12 DID NOT SAY: TWO INDEPENDENT CAUSES PRODUCED
THAT 0, AND ONLY ONE OF THEM IS THE COMMENT.**

1. the comment made `read_not_promoted()` return a *readable* block, so the
   `exit 2` branch never fired; **and**
2. in that tree **no routed target file exists on disk**, so the whole routed
   population is empty, every finding is excluded, and the verdict loop has
   nothing to report — which is an exit 0 on its own.

**So the arm would have read "ok" even with the comment fixed, had the exit
code it demanded been 0 instead of 2.** The fixture was saved by the fact that
it declared `want 2` — a stricter expectation than the arm's own tree could
produce by accident. **The general statement b12 should have made, and this is
it: a bad-input arm must demand an exit code that the bad input is the ONLY
available cause of.** An arm whose expected code is also what an empty,
inert tree produces is not testing the guard; it is agreeing with the shape of
its own fixture.

---

## CORRECTION 2 — "v1 (as shipped)" is an UNPROVABLE LABEL, and it is quoted in a standing document

**Where it stands:** `docs/METHODOLOGY.md:855-862` quotes
`scratchpad/ablation_b12.py` output whose rows read `ack_check v1 -> 'ACK_DECIDED'`
and `index_resolve v1 exit -> 0`, and that script's own header reads
*"ABLATION -- v1 (as shipped) vs v2 (the fix)"*. Read together, the document
claims **the shipped code was driven**. It was not, and cannot be.

**Three independent measurements, none of them a reading of the code's intent:**

```
CMD git log --all --format=%h -- scratchpad
  (no output)                      -> no commit, in any branch, ever touched a tracked scratchpad/ path
CMD git ls-files --error-unmatch scratchpad/ack_check.py
  exit 1                           -> not tracked
CMD grep -c MENTION_ONLY scratchpad/ack_check.v1.py      -> 5
CMD grep -c _unexplained scratchpad/index_resolve.v1.py  -> 3
```

The `.v1.py` files **already contain the fix at the use site**, so they are
mid-patch snapshots rather than the first version. Driven, they say so:

```
  ok   C2d ack_check.v1.py on the MENTION-ONLY tree    want MENTION_ONLY  got MENTION_ONLY
       (an as-shipped v1 would say ACK_DECIDED)
  ok   C2e index_resolve.v1.py on one unexplained dead token   want 1  got 1
       (an as-shipped v1 would exit 0)
```

**WHAT IS TRUE, STATED AT THE STRENGTH IT CAN BE HELD:** the `v1` rows in
`ablation_b12.py` are **reconstructions of the defective predicate written from
the defect's description**, not executions of the code that shipped. They are
still a valid ablation — removing the guard does reintroduce the wrong answer,
and b12's `bad_drive_b12.py` re-derives the same result by removing the guard
from the **real current file** by exact text substitution. What they are not is
evidence about history. **No copy of either checker as it first ran exists
anywhere**, so no future session can re-derive that claim either, and nobody
should try.

**The b12 report already carries half of this** (ITEM 1 (b)) and
`docs/METHODOLOGY.md:902` already says no as-shipped copy survives in git. The
correction is that **the quoted block at `:855` was left standing beside it**,
and a reader who stops at the quote takes away the opposite. A one-line pointer
has been added at that block; this document is the record.

---

## WHAT THESE CORRECTIONS DO NOT TOUCH

* **No count changes.** 6 of 9 routed findings unacknowledged, 36 undriven
  suites, 10 bad-drive arms, 8 fixture arms each — all re-driven in b12 and
  again in b13 (§5 of the b13 report) and all unchanged.
* **The b12 rule still holds**, and this is the rule working: both corrections
  were produced by driving an input rather than by re-reading a report.
* **Neither correction is about another session's work**, so nothing is routed
  from this document.
