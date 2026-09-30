"""A deliberately trivial suite, existing only so the sabotage harness can be
driven against a subject whose baseline colour is CONTROLLABLE.

Used by tests/run_sabotage_harness_baseline_probe.py and by nothing else.

WHY A TRACKED FILE AND NOT A TEMP ONE: sabotage_harness builds a git worktree at
HEAD and copies the named suite into it, so a suite that is not tracked is not
there to copy. That is the harness working correctly, and it is why this fixture
lives in the repository rather than being written at run time.

GREEN unless SAIRN_HARNESS_FIXTURE_RED is set, so the control can drive both
baseline colours without editing anything.
"""
import os
import sys

ANCHOR = 'BASELINE-GATE-FIXTURE-ANCHOR'

if os.environ.get('SAIRN_HARNESS_FIXTURE_RED'):
    # NOT an error in this file. A deliberately red baseline, on demand, so the
    # harness's precondition can be exercised rather than argued about.
    sys.stderr.write('FIXTURE: red baseline requested via '
                     'SAIRN_HARNESS_FIXTURE_RED. This is not a defect.\n')
    sys.exit(1)

# THE ASSIGNMENT ABOVE IS THE MUTATION TARGET and this is the assertion that
# catches it. It compares against a SECOND, SPLIT spelling of the same literal,
# so a mutation rewriting the assignment is detected while the same edit cannot
# accidentally rewrite the expectation too.
#
# A FIRST DRAFT COUNTED OCCURRENCES OF THE LITERAL IN ITS OWN SOURCE and required
# three. The literal occurs once, so the fixture was red at EVERY baseline and the
# control's green arm could never pass -- a fixture failing for its own reasons,
# which is precisely the condition this fixture exists to let the harness refuse.
if ANCHOR != 'BASELINE' '-GATE-FIXTURE-ANCHOR':
    sys.stderr.write('FIXTURE: the anchor assignment was rewritten.\n')
    sys.exit(1)
print('FIXTURE: green, anchor intact')
sys.exit(0)
