"""A deliberately trivial suite, existing only so the sabotage harness can be
driven against a subject whose baseline colour is CONTROLLABLE.

Used by tests/run_sabotage_harness_baseline_probe.py and by nothing else.

WHY A TRACKED FILE AND NOT A TEMP ONE: sabotage_harness builds a git worktree at
HEAD and copies the named suite into it, so a suite that is not tracked is not
there to copy. That is the harness working correctly and it is why this fixture
lives in the repository rather than being written at run time.

GREEN unless SAIRN_HARNESS_FIXTURE_RED is set, so the control can drive both
baseline colours without editing anything.

THE ANCHOR BELOW IS THE MUTATION TARGET. The control plants a change that
removes it and requires this suite to go red, which is what makes the harness's
"the planted defect was refused" verdict mean something on this fixture.
"""
import io
import os
import sys

ANCHOR = 'BASELINE-GATE-FIXTURE-ANCHOR'

if os.environ.get('SAIRN_HARNESS_FIXTURE_RED'):
    # NOT an error in this file -- a deliberately red baseline, on demand, so
    # the harness's precondition can be exercised rather than argued about.
    sys.stderr.write('FIXTURE: red baseline requested via '
                     'SAIRN_HARNESS_FIXTURE_RED. This is not a defect.\n')
    sys.exit(1)

src = io.open(os.path.abspath(__file__), encoding='utf-8').read()
# Two occurrences are expected: the assignment above and this comparison. The
# mutation the control plants removes the assignment, leaving one.
if src.count(ANCHOR) < 3:
    sys.stderr.write('FIXTURE: the anchor was removed from this file.\n')
    sys.exit(1)
print('FIXTURE: green, anchor present')
sys.exit(0)
