"""The negative control for tests/run_tool_selftest_probe.py.

    python tests/run_tool_selftest_probe_control.py

A SUITE THAT HAS ONLY EVER BEEN GREEN IS A SUITE WHOSE BEHAVIOUR NOBODY KNOWS.
The probe this controls reports "every discovered selftest ran and passed" and
exits 0. A probe that discovered nothing, or that could not tell a failing
selftest from a passing one, prints a line that looks the same.

So every branch that is supposed to make it go RED is driven here on purpose,
and the arm fails if the probe stays quiet.

── WHAT THIS DOES NOT DO ────────────────────────────────────────────────────
It does not re-check the probe's DISCOVERY criteria -- that is the probe's own
`--fixtures` blind lock, 14 arms in both directions, and duplicating it here
would be a second answer to a question that already has one. This drives the
RUNNER: the exit-code contract, the floor ratchet, and the third state.

The last two arms are the pair that matters. A control that only plants defects
proves the check can fire; one that only runs clean proves it can stay quiet.
Neither alone says the check DISCRIMINATES, which is the only useful property.
"""
# REQUIREMENT: every branch that should make run_tool_selftest_probe.py go RED
#   is driven on purpose, because a probe that discovered nothing prints the
#   same green line as one that discovered everything and passed
#
import io
import os
import sys

CONTROLS_FOR = ['tests/run_tool_selftest_probe.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tests'))
TOOLS = os.path.join(REPO, 'tools')

import run_tool_selftest_probe as P                              # noqa: E402

# PID-suffixed. Two clones running the suite at the same second would otherwise
# write, read and delete the SAME scratch file in tools/, and the loser would
# see the winner's cleanup as its own mutation failing to apply -- the exact
# shape recorded on 2026-09-14 when two probes restored each other's snapshot
# and both reported byte-identical success.
TAG = 'zzz_probe_control_%d_' % os.getpid()

FAILS = []


def arm(label, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + label
          + ('' if cond else '\n         ' + str(detail)[:300]))
    if not cond:
        FAILS.append(label)


def plant(suffix, body):
    """Write a throwaway tool and return its basename. Caller must remove it."""
    name = TAG + suffix + '.py'
    io.open(os.path.join(TOOLS, name), 'w', encoding='utf-8').write(body)
    return name


def unplant(name):
    try:
        os.remove(os.path.join(TOOLS, name))
    except OSError:
        pass


def quiet(fn, *a, **kw):
    """Run something that prints a 36-line report and keep only its return."""
    real = sys.stdout
    sys.stdout = io.StringIO()
    try:
        return fn(*a, **kw)
    finally:
        sys.stdout = real


def aggregate_only(fn, *a, **kw):
    """Run `main()` with `run_one` stubbed to an instant PASS.

    ── WHY THE STUB, AND WHAT IT DELIBERATELY STOPS TESTING ─────────────────
    `main()` calls `run_one` once per discovered tool. Three arms below exercise
    main()'s AGGREGATION -- the floor ratchet, the unparseable third state, the
    exit code -- and each unstubbed call would spawn 36 real selftests. Four
    sweeps to assert three booleans is how a control becomes the slowest thing
    in the suite and then gets deleted for it.

    So these arms test the aggregation with the subprocess half stubbed, and
    arms 4-7 test `run_one` itself DIRECTLY against real planted tools. Between
    them both halves are covered; neither arm pretends to cover the other's.
    The stub returns PASS on purpose: a stub that returned FAIL would make the
    floor arm pass for the wrong reason.
    """
    real = P.run_one
    P.run_one = lambda name, flag: ('PASS', '')
    try:
        return quiet(fn, *a, **kw)
    finally:
        P.run_one = real


def main():
    # 1. THE FLOOR RATCHET. A tool silently losing its selftest must fail, not
    #    shrink quietly.
    real_floor = P.MIN_SELFTESTS
    P.MIN_SELFTESTS = 10 ** 6
    try:
        rc = aggregate_only(P.main, [])
    finally:
        P.MIN_SELFTESTS = real_floor
    arm('a floor nothing can satisfy makes the probe FAIL', rc == 1,
        'exit %r' % rc)

    # 2. AND IT PASSES AT THE REAL FLOOR -- the other half. Without this, arm 1
    #    is satisfied by a probe that fails unconditionally.
    arm('...and at the real floor it passes', aggregate_only(P.main, []) == 0)

    # 3. A TOOL THAT WILL NOT PARSE IS A THIRD STATE. Reported, and not folded
    #    into "has no selftest", which would be a coverage figure it did not earn.
    n = plant('unparseable', 'def broken(:\n')
    try:
        _found, unparsed = P.discover()
        arm('an unparseable tool is REPORTED, not silently dropped',
            any(u[0] == n for u in unparsed), unparsed)
        arm('...and it makes the run fail rather than pass with a gap',
            aggregate_only(P.main, []) == 1)
    finally:
        unplant(n)

    # 4. A SELFTEST THAT FAILS MUST BE CAUGHT. This is the arm the whole file
    #    exists for: if it does not hold, every green run above means nothing.
    n = plant('failing', "import sys\nif '--selftest' in sys.argv:\n    sys.exit(1)\n")
    try:
        verdict, detail = P.run_one(n, '--selftest')
        arm('a FAILING selftest is reported FAIL', verdict == 'FAIL',
            '%s / %s' % (verdict, detail))
    finally:
        unplant(n)

    # 5. EXIT 2 IS NEITHER. A tool's own could-not-tell must not be laundered
    #    into a pass by the thing running it (PR 1.11).
    n = plant('cnr', "import sys\nif '--selftest' in sys.argv:\n    sys.exit(2)\n")
    try:
        verdict, _ = P.run_one(n, '--selftest')
        arm('exit 2 is COULD-NOT-RUN, not PASS and not FAIL',
            verdict == 'COULD-NOT-RUN', verdict)
    finally:
        unplant(n)

    # 6. A PASSING SELFTEST IS STILL REPORTED PASS. Arms 4 and 5 are both
    #    satisfied by a runner that calls everything broken.
    n = plant('passing', "import sys\nif '--selftest' in sys.argv:\n    sys.exit(0)\n")
    try:
        verdict, _ = P.run_one(n, '--selftest')
        arm('...and a PASSING selftest is still reported PASS', verdict == 'PASS',
            verdict)
    finally:
        unplant(n)

    # 7. THE BLIND LOCK REFUSES WHEN ITS CRITERIA ARE BROKEN. Stub the detector
    #    to match everything: the must-NOT-match fixtures have to bite.
    real = P.selftest_flags
    P.selftest_flags = lambda tree: {'--selftest'}
    try:
        rc = quiet(P.run_fixtures)
    finally:
        P.selftest_flags = real
    arm('a match-everything detector makes --fixtures REFUSE (exit 2)', rc == 2,
        'exit %r' % rc)
    arm('...and the unmodified detector passes its own lock',
        quiet(P.run_fixtures) == 0)

    # 8. NOTHING WAS LEFT BEHIND. A control that mutates a real directory and
    #    dies halfway leaves a tool the next run will try to execute.
    leftovers = [f for f in os.listdir(TOOLS) if f.startswith(TAG)]
    arm('no scratch tool was left in tools/', not leftovers, leftovers)

    print('\n%d failure(s)' % len(FAILS))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
