"""tests/sairncare_payer_routing_integration.js must REFUSE, not merely agree.

Run: python tests/run_payer_routing_integration_sabotage_probe.py

WHY IT EXISTS AT ALL. The suite it drives was written to close a coverage gap
hover found: deleting `prRenderRecorded();` from rPayerRouting() left
tests/sairncare_route_record.js at ALL ARMS PASS and its ten-mutation probe
untouched, because neither ever executes rPayerRouting(). A suite written to
close a hole is the LAST thing that should be trusted on its own word -- it was
written by someone who already knew the answer.

MUTATION 1 IS THE ONE THE SUITE EXISTS FOR and is the exact defect hover
reported. The rest attack the arms rather than the product: a suite that only
catches a deleted line, and misses the line being moved behind the guard or
called conditionally, has pinned one spelling of the defect instead of the
property.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'sairncare_payer_routing_integration.js')
APP = 'sairncare.html'

CALL = "  prRenderRecorded();\n"

MUTATIONS = [
    ("1. HOVER'S DEFECT, RESTORED: the real call site is deleted. The rules and "
     "the coverage line still render, the recorded determinations silently stop "
     "appearing, and nothing errors anywhere",
     APP,
     CALL + "  if(_prRules===null){",
     "  if(_prRules===null){"),

    ("2. THE CALL MOVES BEHIND THE RULES GUARD -- it still exists, it is still "
     "one line, and it stops running in the two states that matter most: a "
     "FAILED rules read and a never-loaded panel, which are exactly when a "
     "biller most needs to see what was already determined",
     APP,
     CALL + "  if(_prRules===null){",
     "  if(_prRules!==null)prRenderRecorded();\n  if(_prRules===null){"),

    ("3. THE TRAIL IS RENDERED PER RULE instead of once -- the panel looks right "
     "with one rule and repaints N times with N, which is how a render that "
     "should be idempotent becomes a flicker nobody can reproduce",
     APP,
     CALL + "  if(_prRules===null){",
     "  prRenderRecorded();prRenderRecorded();\n  if(_prRules===null){"),

    ("4. THE PANEL GUARD IS DROPPED, so the trail renders into a page that has "
     "no Payer Routing panel on it -- the opposite direction, and a suite that "
     "only asserted the call HAPPENS would pass it",
     APP,
     "  if(!box||!cov)return;\n",
     "  if(false)return;\n"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='sairncare rPayerRouting() -- the suite must refuse four ways of '
              'losing the recorded-determinations render, including the one '
              'hover found',
        # The suite is new and sairncare.html is where every mutation lands; the
        # worktree is built at HEAD, so without staging both the baseline is
        # measuring a file that does not have the suite and a page the suite has
        # not been checked against.
        stage=(APP,)))
