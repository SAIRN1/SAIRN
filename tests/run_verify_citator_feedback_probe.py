"""Does verify_citator_feedback.py refuse to call a partial run a pass?

    python tests/run_verify_citator_feedback_probe.py

The tool writes real rows to a real table, so this probe never lets it reach
the network: `call()` is replaced with a stub that answers like PostgREST.
Nothing is read from or written to any database.

The defect this pins (b55 M2): check-only is the DEFAULT mode, and it stops
before sections C-E -- the Guardian Check 29 write and read-back. `_verdict`
printed PARTIAL and then returned 0, so a run that never did the part the
script exists for exited as a pass.
"""
import contextlib
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import verify_citator_feedback as V                              # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def drive(argv, status):
    """Run main() with every call answered `status`, no network, no env leak."""
    V.RESULTS.clear()
    real_call, real_env = V.call, V.env
    V.call = lambda *a, **k: (status, [])
    V.env = lambda name: 'stub-' + name
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            rc = V.main(argv)
    finally:
        V.call, V.env = real_call, real_env
    return rc, out.getvalue()


print('\n1. CHECK-ONLY IS NOT A PASS OF THE WHOLE SCRIPT')
rc, out = drive([], 200)
check('default mode (check-only), every read arm green -> exit 2, not 0. '
      'Sections C-E never ran', rc == 2, 'rc=%r' % rc)
check('...and it still says PARTIAL', 'PARTIAL' in out, out[-300:])
rc, out = drive(['--check-only'], 200)
check('explicit --check-only, every read arm green -> exit 2', rc == 2,
      'rc=%r' % rc)

print('\n2. THE OTHER STATES ARE UNCHANGED')
rc, _ = drive(['--check-only'], 400)
check('columns missing -> exit 1 (a finding outranks partial)', rc == 1,
      'rc=%r' % rc)
rc, _ = drive(['--check-only'], None)
check('table unreachable -> exit 2', rc == 2, 'rc=%r' % rc)
V.RESULTS.clear()
with contextlib.redirect_stdout(io.StringIO()):
    V.arm('synthetic', True)
    rc = V._verdict()
check('a complete all-green run (partial=False) -> exit 0', rc == 0,
      'rc=%r' % rc)

print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
