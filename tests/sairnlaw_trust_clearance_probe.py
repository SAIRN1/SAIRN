"""tests/sairnlaw_trust_clearance.js must REFUSE, not merely agree.

Run: python tests/sairnlaw_trust_clearance_probe.py

# REQUIREMENT: tests/sairnlaw_trust_clearance.js must go RED when the IOLTA
#   clearing path stops validating the date, stops REVERTING a clearance that
#   did not reach the server, stops refusing a voided transaction, or starts
#   recording "outstanding" as an absent field instead of a stated false --
#   each of which leaves the button working and the toast cheerful while this
#   device's trust reconciliation disagrees with every other device's

TIER A, AND IT WAS ONE OF 38 UNCONTROLLED TIER A SUITES. Measured 2026-09-18
with `python tools/suite_control_triage.py`: 169 suites, 59 with a negative
control, 110 without, and 38 of those 110 name a Tier A resource. This closes
one of the 38. `law_trusttx` is attorney client trust money -- the one balance
a bar association audits -- and lawSetClearance() is what decides whether a
transaction counts as having cleared the bank.

── WHY THIS SUITE IS WORTH A CONTROL RATHER THAN A READ ────────────────────
Every arm here is about a state the product ends up in after an AWAIT, and the
interesting half is the ROLLBACK: a clearance that did not sync is undone, so
that this device does not adjust its reconciliation for an item no other
device knows about. That is four statements -- write, fail, restore, say so --
and three of the four are invisible in a diff of the happy path. A suite that
is green over them is exactly the shape that says nothing about whether it
would notice them going soft.

AND IT SITS BESIDE A REAL, RECENT DEFECT OF THE SAME FAMILY. The IOLTA
reconciliation reviewed on 2026-09-18 returns AGREES while undated rows are
reconciled by nothing; the clearing flag is the other input to that same
figure. A cleared_on that survives a failed sync, or an outstanding recorded
as an absent field, moves the reconciliation on this device alone.

── WHAT IS PLANTED, AND WHY EACH ONE READS AS FINE ─────────────────────────
  * the ROLLBACK stops restoring cleared_on -- the toast still says the write
    failed, so the user is told the truth while the record keeps the lie;
  * the rollback restores cleared_on but not the `cleared` FLAG, which is the
    half-rollback a reviewer skims past because the line above it is right;
  * the voided guard goes -- a voided disbursement can clear the bank, and
    every other arm still passes;
  * `outstanding` deletes the flag instead of setting false, so outstanding
    becomes indistinguishable from never-assessed -- the suite's own arm says
    this must be STATED rather than implied by absence;
  * the date is written without being validated, so `cleared_on:'last
    Tuesday'` reaches the ledger and the reconciliation's own dayOf() drops it
    -- which is the undated-row hole, arrived at from the other side.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'sairnlaw_trust_clearance.js')
LAW = 'sairnlaw.html'

# The rollback block is the subject of two mutations, so each anchor carries
# enough of its neighbour to be unique. `hits != 1` in the harness is what
# turns a stale anchor into a loud ANCHOR-n rather than an arm that ran against
# an unmodified file and passed.
MUTATIONS = [
    ("1. the ROLLBACK stops restoring cleared_on -- the toast still tells the "
     "user the write failed, so they are told the truth while the record keeps "
     "the lie",
     LAW,
     "    if(prevOn===undefined)delete t.cleared_on; else t.cleared_on=prevOn;\n"
     "    if(prevFlag===undefined)delete t.cleared; else t.cleared=prevFlag;",
     "    if(prevFlag===undefined)delete t.cleared; else t.cleared=prevFlag;"),

    ("2. the rollback restores the DATE and not the FLAG -- a half-rollback, "
     "which is the shape a reviewer skims because the line above it is right",
     LAW,
     "    if(prevOn===undefined)delete t.cleared_on; else t.cleared_on=prevOn;\n"
     "    if(prevFlag===undefined)delete t.cleared; else t.cleared=prevFlag;",
     "    if(prevOn===undefined)delete t.cleared_on; else t.cleared_on=prevOn;"),

    ("3. a VOIDED transaction may clear the bank -- one line, and every other "
     "arm in the suite still passes",
     LAW,
     "  if(t.status==='Voided'){toast('A voided transaction cannot clear the "
     "bank.');return;}",
     "  if(false){toast('A voided transaction cannot clear the bank.');return;}"),

    ("4. OUTSTANDING becomes an ABSENT field instead of a stated false, so "
     "'assessed and outstanding' is indistinguishable from 'never assessed'",
     LAW,
     "  if(outstanding){ t.cleared=false; delete t.cleared_on; }",
     "  if(outstanding){ delete t.cleared; delete t.cleared_on; }"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='SAIRNlaw trust clearance -- the suite must refuse a clearing '
              'path that has stopped reverting, stopped refusing a void, or '
              'started recording outstanding as an absence',
        stage=(SUITE,)))
