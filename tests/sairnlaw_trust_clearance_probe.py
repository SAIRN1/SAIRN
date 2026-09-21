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
     # RE-AIMED 2026-09-21: the rollback now operates on `revertT`, read back
     # from storage AFTER the await, rather than on the `t` captured before it.
     # Unchanged in intent; the anchor follows the code rather than the code
     # being left alone to keep an anchor alive.
     "      if(prevOn===undefined)delete revertT.cleared_on; else revertT.cleared_on=prevOn;\n"
     "      if(prevFlag===undefined)delete revertT.cleared; else revertT.cleared=prevFlag;",
     "      if(prevFlag===undefined)delete revertT.cleared; else revertT.cleared=prevFlag;"),

    ("2. the rollback restores the DATE and not the FLAG -- a half-rollback, "
     "which is the shape a reviewer skims because the line above it is right",
     LAW,
     "      if(prevOn===undefined)delete revertT.cleared_on; else revertT.cleared_on=prevOn;\n"
     "      if(prevFlag===undefined)delete revertT.cleared; else revertT.cleared=prevFlag;",
     "      if(prevOn===undefined)delete revertT.cleared_on; else revertT.cleared_on=prevOn;"),

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

    # ── THE TWO-DEVICE HALF, ADDED 2026-09-21 ──────────────────────────────
    # Mutations 1-4 all drive ONE device. The defects below exist only in the
    # window where a SECOND one writes, so no fixture with one device in play
    # could plant them -- which is exactly why they survived a control that
    # was green.

    ("5. THE REVERT GOES BACK TO WRITING THE PRE-AWAIT ARRAY, so a failed "
     "single-row write erases everything that landed during the round trip -- "
     "not the row, the whole ledger. trustTransactions() is ld(), which parses "
     "localStorage fresh on every call, so the captured array really is stale",
     LAW,
     # ANCHOR WIDENED 2026-09-21 BEFORE THIS ARM WAS EVER GREEN. The bare line
     # matched TWICE: confirmVoid() thirty lines up re-reads the ledger with
     # the identical statement, which is precisely the function this fix was
     # mirroring. The harness reported ANCHOR-2 and REFUSED rather than
     # planting in whichever came first, so what could have been an arm
     # asserting something about the wrong function was a five-minute
     # correction instead.
     "    var revertList=trustTransactions();\n"
     "    var revertT=revertList.find(function(x){return x.id===id;});",
     "    var revertList=list;\n"
     "    var revertT=revertList.find(function(x){return x.id===id;});"),

    ("6. THE STAMP CHECK GOES and the revert fires unconditionally, so this "
     "device's pre-action value is written over a clearance ANOTHER device "
     "recorded mid-flight -- putting an item the bank HAS taken back into the "
     "outstanding set",
     LAW,
     "    if(revertT&&revertT.cleared_at===myClearedAt){",
     "    if(revertT){"),

    ("7. THE STAMP IS NEVER SET, so there is nothing for the check in mutation "
     "6 to compare and the rollback has no way to tell its own change from "
     "anybody else's",
     LAW,
     "  t.cleared_at=myClearedAt;\n  st('law_trusttx',list);",
     "  st('law_trusttx',list);"),

    ("8. THE STAMP OUTLIVES THE CHANGE IT STAMPED -- the rollback restores the "
     "two clearance fields and leaves cleared_at behind, so the NEXT failed "
     "write on that row thinks the record still carries its own change",
     LAW,
     "      if(prevAt===undefined)delete revertT.cleared_at; else revertT.cleared_at=prevAt;\n",
     ""),

    ("9. the ALREADY-IN-TARGET-STATE refusal goes, so a no-op re-sends the "
     "record -- risking a failure whose revert has nothing to revert, and "
     "toasting a change nobody made",
     LAW,
     "  if(outstanding ? (t.cleared===false&&t.cleared_on===undefined)\n"
     "                 : (t.cleared===true&&t.cleared_on===clearedOn)){",
     "  if(false){"),

    ("10. THE ONE THAT READS AS CORRECT: the already-in-target-state refusal is "
     "WIDENED to any already-cleared row, which looks tidier and silently "
     "breaks Re-date -- the button renders, says 'Re-date', and does nothing",
     LAW,
     "                 : (t.cleared===true&&t.cleared_on===clearedOn)){",
     "                 : (t.cleared===true)){"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='SAIRNlaw trust clearance -- the suite must refuse a clearing '
              'path that has stopped reverting, stopped refusing a void, or '
              'started recording outstanding as an absence',
        # BOTH the suite and sairnlaw.html are staged since 2026-09-21. The
        # worktree is at HEAD, and the two-device mutations below are anchored
        # on lines that only exist after the concurrency fix -- so without the
        # app file the baseline goes red for a reason that has nothing to do
        # with any mutation, which is what happened on the first run here.
        stage=(SUITE, LAW)))
