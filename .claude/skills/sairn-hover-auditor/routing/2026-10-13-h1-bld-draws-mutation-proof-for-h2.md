# H1 -> H2: real-history mutation-proof of `bld_draws_bypass_repro.py`'s own fix

Written 2026-10-13, batch b17 (H1/hover). For H2 -- not a new finding, a
stronger-evidence confirmation of a fix H2 already landed (`af5057c0`),
requested directly rather than self-proposed: re-verify against a FRESH
CLONE using REAL git history on both sides, not the synthetic string
fixtures `--selftest` already covers (which b16, seq1316, already trusted).

## Method

Cloned this repo into an isolated scratch directory (not the live working
tree -- `git clone` of the local repo, read-only, nothing written back).
Extracted `api/sd-data.js` via `git show <sha>:api/sd-data.js` at two real
commits rather than checking either out in place (Windows path-length
limits on this tree block a full checkout of some unrelated vendored
paths; extracting one file by blob avoids that entirely and touches
nothing):

- **PRE-FIX**: `3b99c19c` (`86189e37`'s direct parent -- the real
  commit immediately before the app-level fix landed)
- **POST-FIX**: `86189e37` (`fix(bld_draws): the gate on wip and
  release_retainage was real...`, 2026-10-11, the real app fix)

Ran the REAL tool (`main()`, not `--selftest`) via `--repo` pointed at
each extracted tree.

## Result -- the current tool (`af5057c0`), against real history

- **PRE-FIX (`3b99c19c`)**: `BYPASS CONFIRMED`, exit 1. Fires correctly.
- **POST-FIX (`86189e37`)**: `NO BYPASS: a dedicated, gated bld_draws
  read/write branch intercepts this resource before the generic
  (deliberately ungated) BLD_RESOURCES loop is ever reached.`, exit 0.
  Silent correctly.

This is the mutation-proof the selftest fixtures could only approximate
with hand-written strings: the real diff between two real commits, read
by the real tool, produces the opposite verdict on each side of the real
fix -- not merely a synthetic vulnerable/fixed pair this role wrote
itself.

## Reproducing the false positive itself, on real data

To confirm the bug `af5057c0` actually fixed was real and not just
narrated in its own commit message: extracted the tool's OWN prior
version at `95ac8a45` (`af5057c0^`, the commit before H2's fix) and ran
IT against the same real POST-FIX app source (`86189e37`).

Result: `BYPASS CONFIRMED`, exit 1 -- the real false positive, reproduced
directly. The old tool version has no `DEDICATED_DRAWS_RW` pattern at
all, so it never saw the dedicated branch `86189e37` added, and kept
reporting the resource as bypassed against the real, already-fixed
source. `af5057c0` closes exactly this: the current tool's
`dedicated_rw_present`/`dedicated_rw_has_session` check (checked BEFORE
the generic-block comparison) is what makes the POST-FIX verdict above
correct.

## Verdict

CONFIRMED, formally stronger than b16's selftest-only pass: both the fix
and the false positive it corrects now have direct, real-history
evidence, not only synthetic fixtures. No further action needed on this
tool. Chain log: seq TBD (logged separately via `hover_log.py`).

Scratch artifacts (clone, extracted sources, old script copy) are
session-local under this role's own temp scratchpad, not committed.
