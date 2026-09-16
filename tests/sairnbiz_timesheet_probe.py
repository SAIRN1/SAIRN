"""The negative control for tests/sairnbiz_timesheet_hours.js.

    python tests/sairnbiz_timesheet_probe.py

WHY THIS SUITE. `tools/suite_control_triage.py` ranks the suites nobody has ever
tried to break by the criticality tier of the resources each one names. `sb_ts`
is Tier A and the register's own entry says why it is the worst of them to lose:
*"an invoice has a customer copy, a PO has a vendor, a week of somebody's hours
has neither."* The suite guarding it is 682 lines across ten sections and had
never been driven to prove it catches anything.

THAT IS THE CASE FOR DOING IT, NOT AN ARGUMENT THAT THE SUITE IS WEAK. A
thorough suite is the one whose green run reads most convincingly, which is
exactly why an unmeasured one is worth measuring: nothing about 682 lines says
any assertion depends on the thing it names.

── WHY THIS FILE IS PYTHON AND USES sabotage_harness ───────────────────────
It was first written as a standalone .js control that set up its own worktree,
ran its own baseline, and checked anchor uniqueness itself. That is a sixth copy
of five disciplines the harness already carries, and the harness's own header
says what a copied harness does: `tools/` held SEVEN `strip_comments`
implementations and three were destroying 90% of their input while reporting
clean. Rewritten onto the shared module before it was ever committed.

── THE THREE DEFECTS, TWO OF WHICH THIS APP ACTUALLY SHIPPED ───────────────
Each is a change that makes the code shorter and reads as a tidy-up, which is
the only kind worth planting:

  * the invented week returns -- `rTS()` built every cell and five KPIs from a
    hardcoded array when no record existed, so a REAL pay rate multiplied an
    INVENTED week and printed a plausible wrong dollar figure. Section 1 asserts
    that a week with nothing recorded says so instead of showing a number;
  * the validator coerces instead of refusing -- `Number('eight')` is NaN and
    `Number('')` is 0, so a typo becomes a zero-hour day, which is a real and
    payable statement about somebody's week. Section 5 asserts the refusal;
  * `sb_ts` leaves the synced list -- a one-token edit after which every
    recorded week stays on one workstation and the panel goes on looking
    correct. Section 9 asserts the hours reach a server.
"""
# REQUIREMENT: the 682-line sb_ts timesheet suite is proved to catch something,
#   because a week of somebody's hours has neither a customer copy nor a vendor
#   copy to reconstruct it from, and nothing about 682 lines says any assertion
#   depends on what it names
#
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'sairnbiz_timesheet_hours.js')
SRC = 'sairnbiz.html'

MUTATIONS = [
    ("1. THE INVENTED WEEK COMES BACK -- a missing record becomes a default "
     "week again, so a real pay rate multiplies hours nobody entered. This is "
     "the original defect, in its original shape",
     SRC,
     "var d=row&&row.hours;",
     "var d=(row&&row.hours)||[8,8,8,8,8,0];"),

    ("2. THE WRITE PATH COERCES RATHER THAN REFUSES -- an out-of-range or "
     "non-numeric entry silently becomes a 0-hour day instead of stopping the "
     "save, and a zero-hour day is a real statement about somebody's week",
     SRC,
     "if(!isFinite(v)||v<0||v>24){bad=bad||{i:i,raw:raw};out.push(null);continue;}",
     "if(!isFinite(v)||v<0||v>24){out.push(0);continue;}"),

    ("3. sb_ts LEAVES THE SYNCED LIST -- recorded hours never leave the "
     "workstation, nothing reports an error, and the panel still shows them",
     SRC,
     "'sb_recv','sb_ts']",
     "'sb_recv']"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='negative control for tests/sairnbiz_timesheet_hours.js -- '
              'sb_ts is Tier A and a lost week has no second copy'))
