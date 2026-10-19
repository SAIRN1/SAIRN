# cc b19 — the concept for each fix, stated BEFORE the code

**Committed before the commits that implement it**, so the ordering is provable
from `git log`. Both items are measured first, and in both cases the
measurement changed what the fix should be.

---

## Item 1 — the board's label set

**One line: a digest field must end where its own section ends — so the parse
stops at the next DOCUMENT-LEVEL heading rather than running into the next
section's prose, and where it cannot safely stop it SAYS the field contains
another heading instead of silently slicing 900 characters out of the middle.**

### The correction the measurement forces, stated before the code

**`STATUS`, `DECISION-NEEDED`, `CHANGED`, `EVIDENCE-path`, `UNVERIFIED`,
`NEXT`, `CONTEXT`, `SHA256` and `END-OF-REPORT` are ALREADY in the label set**
— read out of `digest_fields()` itself, not remembered. The decision as written
("add explicit STATUS/DECISION-NEEDED/NEXT") is already done, and saying so is
cheaper than implementing it twice.

What is NOT in the set, measured against the six live digests on the mount:
`IDENTITY` (hank's first line) and `DIGEST` (cc's and fourth's first line).

### Why a blanket "stop at any heading" is the wrong fix, and this is the half that needed measuring first

The run-on has exactly one live instance: **hank b17's `CONTEXT` body is 4,673
characters**, because `CONTEXT` sits at offset 1506 and the next *recognised*
label is at 6193, with three of hank's own section headings in between
(`WHAT LANDED --`, `THE METHODOLOGY ITEM CAUGHT ITS OWN AUTHOR…`,
`AND THREE SUITES WENT RED…`). Each is a real heading: own line, column 0,
preceded by a blank line.

**But the same shape appears INSIDE fields that are supposed to contain it.**
cody b23's `CHANGED` carries `ITEM 1 --`, `ITEM 2 --`, `ITEM 3 --`,
`A DEFECT RECORD WAS WRITTEN`; its `NEXT` carries `WHOEVER TAKES THE NEXT
SWEEP REPAIR`, `HANK --`, `CC --`. All blank-line-preceded, all column 0, all
upper case — and all genuinely part of the field a reader wants. **Terminating
there would cut cody's CHANGED to one paragraph and call it the whole field.**

So the rule is scoped by what the field IS:

- **`CONTEXT` is a figure field.** Its content is a few words, so a
  blank-line-preceded heading inside it is always the next section. It
  terminates there.
- **`STATUS`, `NEXT` and the rest are prose fields.** They legitimately
  contain their author's headings, so they still end only at a known label or
  at end of file — and when such a field contains a blank-line-preceded
  heading, the board **reports that** rather than slicing silently. Same
  pattern as b18's tolerance note: a bound nobody can see is a bound that
  widens.

**The honest limit:** this does not make a 1,416-character STATUS fit in 900.
That slice is a DISPLAY bound and stays; what changes is that a reader is told
when the 900 they are reading has another section's heading inside it.

---

## Item 2 — the publisher race

**One line: a publish must refuse to overwrite a board that was written by a
NEWER publisher than this clone is running, or from FRESHER rows than this
clone can see — so a stale clone reverting a corrected board is a refusal with
a named cause instead of a silent last-write-wins.**

### What the race actually is, measured in b18

cc's clone published a corrected board at 08:34. **fourth's clone republished
at 08:55 with its own pre-fix copy of the publisher**, and the broken cells
came back with no error anywhere. It resolved itself twenty minutes later when
other clones pulled — which is luck, not a mechanism.

### Why "timestamp of the data" is not enough, and this is why the concept is stated before the code

**The data was not stale. The CODE was.** Every clone renders from the same
registry outside git, so fourth's rows were as fresh as cc's — a
last-write-wins check on row timestamps would have let that publish through.
What differed is the publisher each clone was running.

So the check needs **two** comparisons, and the first is the one the dispatch's
wording would have missed:

1. **PUBLISHER REVISION.** The board carries the revision of the publisher that
   wrote it. A clone whose own revision is LOWER refuses: it would be replacing
   a newer rendering with an older one. Monotonic and compared as a tuple, not
   a string — `2026-10-19.10` is not less than `2026-10-19.9`.
2. **ROW RECENCY.** Per agent, the board's rendered `row written` stamp against
   the stamp this process would render. If the board is showing a row NEWER
   than the one this clone can see, the registry read is behind and the publish
   refuses.

**Refuse, not merge.** Merging two renderings of six agents' state produces a
board that describes no moment that ever existed; "reject" is the branch of the
decision that can be made correct.

**And refusing must not break the caller.** Publishing is a side effect of a
status or claim write. The write must still succeed, the board is reported
`NOT PUBLISHED` with the reason and the command to fix it (`git pull`) — the
existing non-fatal path, which already prints "your status/claim write
succeeded; the Drive board is stale".

**The limit, stated now:** a clone running a publisher that pre-dates the
revision field entirely cannot be stopped by this — it does not write the
field and does not read it. The check protects against every clone from this
revision forward, and the first push is the thing that distributes it.
