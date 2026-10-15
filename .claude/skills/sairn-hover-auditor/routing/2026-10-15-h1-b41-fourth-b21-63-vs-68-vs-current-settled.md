# h1 b41 -- fourth b21's "63 across 22 resources" is now STALE AT THE POPULATION LEVEL, not just the count; settled with the command that produces it

**For the record, not routed as a defect** -- the underlying bug this figure
described is substantially FIXED, not open. This closes the open
re-derivation thread carried from H1 b34 -> b39 -> b40.

## Chain of figures

- **H1 b34** (hover's own first measurement, log seq 1419): 63 branches,
  grouped into "22 distinct resource/app messages" (the exact wording in
  the log entry). This is the origin of "22" -- it was never fourth's own
  grouping unit, it was H1's, stated in fourth's own b21 report as "the
  22-resource breakdown is likewise H1's."
- **H1 b39** (log seq 1453): re-measured at its own HEAD with a proper
  brace-matching parser, found **68**, delta of 5 from b34's 63, attributed
  to ordinary file growth. Could not reproduce 22 by schema-file name (45)
  or app-prefix (~14) -- **did not try grouping by message text**, which is
  what b34's own wording specifies.
- **H1 b41 (this batch)**: re-measured at current HEAD. **Neither 63 nor 68
  is current. The real number is 53**, and it is not reachable from 68 by
  "further growth" -- the population was REWRITTEN, not merely extended.

## What actually happened, found in the file itself

`api/sd-data.js:18626-18681` carries a dated, self-measuring comment block
(`A 400 IS NOT A 404, AND 89 BRANCHES SAID IT WAS (2026-10-14)`) recording
that a build session, after b39's own measurement, converted **89 of a
then-98** unconditional-fold branches to call the existing
`notProvisionedDecide()`/`notProvisioned()` helper -- which is Population 1
in b39's own four-way classification (the SAFE population, not the
defect). The 9 left alone already discriminated on cause by reading the
response body themselves.

This means b39's 68 and fourth's original 63 were both real counts of a
population that has since been **substantially remediated**, not merely
grown by new code. Chasing "22" forward against current HEAD was never
going to resolve, because the branch SET it was counted over mostly no
longer exists in that form.

## Current HEAD, measured directly, with the method

313 real `if (VAR.status === 404 || VAR.status === 400) { ... }` blocks
(333 raw regex hits; 13 are ternaries, not if-blocks; 5 are brace-less or
inside the audit comment's own prose; excluded; **315 real if-blocks**),
same four-way classification b39 established:

```
grep -c "notProvisioned(res" api/sd-data.js          -> 90 (1 is the def, 89 call sites)
grep -c "status === 404 || .*status === 400" api/sd-data.js  -> 333 raw
```

  - Population 1 (calls notProvisionedDecide()/notProvisioned(), SAFE): **89**
    -- cross-checked independently via the grep above (90 - 1 def = 89).
  - Population 2 (folds to healthy 200 / provisioned:false, SAFE by design): **151**
  - Population 3 (conditional-on-cause or defers to a later flag): **22**
    (this 22 is COINCIDENTAL with the old "22 resources" figure -- it is a
    different population entirely, population 3 not population 4's
    grouping, and almost certainly not the same 22 b34 meant. Naming it so
    nobody mistakes the coincidence for a confirmation.)
  - **Population 4 (unconditional inline fold to 503 NOT_PROVISIONED --
    the real, current defect count): 53**

Message-text grouping of the 53 (templatizing variable-concatenated parts,
e.g. `'Slab ' + cfg.label + ' sync...'` -> `'Slab <VAR> sync...'`):
**43 distinct message texts.** Self-named-schema-file grouping (51 of the
53 name a `sql/*_schema.sql` file inside their own message; 3 don't):
**38 distinct schema filenames.** Neither is 22 or close to it.

Full script (brace/paren-matching, string- and comment-aware) at
`<session scratchpad>/classify_503_folds.py`, written by the agent that
ran this derivation; logic summarized in the hover chain entry.

## Conclusion -- the figure of record

**53 is the current, real count of the unconditional-fold defect
population in `api/sd-data.js` at this HEAD.** 63 (b34) and 68 (b39) were
both accurate measurements of their own HEAD at the time; neither is
current. **"22 resources" cannot be reproduced against current HEAD by any
grouping tried (message text: 43; self-named schema file: 38) and is
UNRESOLVABLE going forward** -- not because the method is wrong, but
because the branch population it was counted over has been substantially
rewritten since, not merely grown. Closing this sub-count as unresolvable
rather than leaving it open indefinitely, per the standing instruction.

**Not routed as a defect**: Population 4's remaining 53 branches are the
same class of defect fourth originally found and hank already fixed 89 of
98 instances of on 2026-10-14 -- this is the SAME open item continuing
(53 unconverted, not a new finding), not a regression. Worth a line to
whoever owns that cleanup next (hank, going by the 2026-10-14 commit) that
53 remain, with this doc's script as the reproducible count.

Logged to the hover chain alongside this note.
