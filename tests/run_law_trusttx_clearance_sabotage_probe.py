"""api/sd-data-law-trusttx-clearance.test.js must REFUSE, not merely agree.

Run: python tests/run_law_trusttx_clearance_sabotage_probe.py

# REQUIREMENT: the suite must go RED when api/sd-data.js goes back to
#   answering ok:true over a clearance the disbursement path never stored,
#   when the comparison narrows to some of the three fields, or when it starts
#   reading them by truthiness -- because `cleared:false` is how an uncleared
#   CHEQUE is recorded, a cheque is a Disbursement, and that is the commonest
#   outstanding item in an attorney trust reconciliation

WHY THE GUARD IS A COMPARISON AND NOT A RULE. The obvious implementation is
"the disbursement RPC cannot carry clearances, so refuse one". That would be a
second copy of the SQL's behaviour kept in step by nobody, and it would have
to be found and removed by hand on the day the RPC learns to carry them. The
shipped guard compares WHAT WAS ASKED FOR against WHAT CAME BACK, so it
retires itself -- and arm "it stops complaining the moment the store DOES
carry the clearance" is what pins that property.

MUTATION 3 IS THE ONE THAT READS AS CORRECT, and it is the reason the suite
has an OUTSTANDING arm at all. `payload[k] !== undefined` and `payload[k]`
look interchangeable and differ on exactly one value: `false`. Marking a
cheque outstanding sends `cleared:false` with `cleared_on` DELETED -- two
keys, one of them falsy -- so the truthiness form lets the whole
outstanding case through while every cleared-case arm stays green.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                          # noqa: E402

SUITE = os.path.join('api', 'sd-data-law-trusttx-clearance.test.js')
SRC = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    ("1. THE ORIGINAL DEFECT, RESTORED: the guard goes and every re-send of an "
     "existing disbursement is ok:true again, carrying the stored row that "
     "never took the clearance",
     SRC,
     "        if (notStored.length) {",
     "        if (false) {"),

    ("2. the comparison narrows to cleared_on, so the FLAG and the stamp are "
     "confirmed over a write that did not happen -- and `cleared:false` with "
     "no date is exactly how an outstanding cheque is recorded",
     SRC,
     "        const CLEARANCE_KEYS = ['cleared_on', 'cleared', 'cleared_at'];",
     "        const CLEARANCE_KEYS = ['cleared_on'];"),

    ("3. THE ONE THAT READS AS CORRECT: the asked-for test becomes truthiness, "
     "so `cleared:false` is treated as not-asked-for -- every marked-cleared "
     "arm stays green and the OUTSTANDING case walks straight through",
     SRC,
     "        const askedFor = CLEARANCE_KEYS.filter((k) => payload[k] !== undefined);",
     "        const askedFor = CLEARANCE_KEYS.filter((k) => payload[k]);"),

    ("4. the comparison only fires when the STORED row already has the field, "
     "so a row carrying no clearance at all -- which is every row this can "
     "happen to -- passes the check",
     SRC,
     "          (k) => JSON.stringify(row.data[k]) !== JSON.stringify(payload[k]));",
     "          (k) => row.data[k] !== undefined && JSON.stringify(row.data[k]) !== JSON.stringify(payload[k]));"),

    ("5. the refusal fires on EVERY disbursement, so posting a new cheque is "
     "refused -- the guard stops being about the clearance and starts being "
     "about the resource",
     SRC,
     # ANCHOR RE-AIMED before this arm was ever green: the refusal gained a
     # `fields` line between the `if` and the `res.status`, so the two-line
     # anchor went ANCHOR-0. Widened to the `if` plus the line that now follows
     # it rather than shortened to the bare `if`, which mutation 1 already owns.
     "        if (notStored.length) {\n          // `fields` IS THE MACHINE-READABLE HALF",
     "        if (true) {\n          // `fields` IS THE MACHINE-READABLE HALF"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='law_trusttx clearance -- the suite must refuse a handler that '
              'confirms a clearance the disbursement path never stored',
        # The suite is new and api/sd-data.js's guard is not committed when
        # this first runs, so both are staged; the worktree is at HEAD.
    # api/_lib/auth.js is staged 2026-09-24 because the file(s) above now
    # call roleSet() from it -- the platform-wide null-prototype role-map
    # sweep. The worktree is at HEAD, so an UNSTAGED DEPENDENCY of a staged
    # file dies at require() and the BASELINE goes red before any mutation
    # is planted. Same gap as an unstaged file. Full account: api/_lib/auth.js.
        stage=(SUITE, SRC, os.path.join('api', '_lib', 'auth.js'))))
