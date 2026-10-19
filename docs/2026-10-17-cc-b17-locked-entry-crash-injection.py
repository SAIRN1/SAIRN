#!/usr/bin/env python
# OWNER: cc
# written 2026-10-17, batch b17 item 3 -- evidence, not a gate
"""END-TO-END: does `sairn_push_gate_hook.py --selftest` report a CRASHED
criteria lock as a pass?

The selftest has an in-process arm for this (`_locked_entry` driven directly),
and that arm cannot reach `__main__` -- which is where the defect lived. This
driver reaches it: it takes the real hook, injects `raise RuntimeError` as the
first line of `selftest()`, writes TWO copies to a scratch directory -- one
with the current wiring and one with the pre-fix wiring restored -- and runs
each as a real subprocess.

    python docs/2026-10-17-cc-b17-locked-entry-crash-injection.py

Expected, and measured 2026-10-17:

    POST-FIX exit 2, and stdout names COULD NOT RUN
    PRE-FIX  exit 0, and stdout is EMPTY

The pre-fix pair is the finding: exit 0 with no output at all is what every
caller of this lock has been reading as "the gate's criteria are sound". It was
found because a NameError in one of b17's own new arms printed 23 of 50 arms,
no summary line, and exited 0.

NOTHING IS WRITTEN OUTSIDE THE SCRATCH DIRECTORY and the real hook is never
modified -- the injection is done on text in memory and written to copies.

Exit 0 both measurements as expected, 1 if either does not reproduce,
2 if the hook could not be read.
"""
import io
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HOOK = os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')

CRASH = "    raise RuntimeError('INJECTED: the lock crashed')\n"

# The post-fix wiring, verbatim from __main__. If this text is not found the
# driver says so rather than silently measuring one arm: a rewrite that no
# longer matches means the wiring moved, which is the thing being watched.
POST = ("    if '--selftest' in sys.argv:\n"
        "        sys.exit(_locked_entry('--selftest', selftest))\n"
        "    if '--preflight' in sys.argv:\n"
        "        sys.exit(_locked_entry('--preflight', preflight))\n"
        "    try:\n")
PRE = ("    try:\n"
       "        if '--selftest' in sys.argv:\n"
       "            sys.exit(selftest())\n")


def main():
    try:
        src = io.open(HOOK, encoding='utf-8').read()
    except OSError as exc:
        print('COULD NOT RUN: %s is not readable (%s).' % (HOOK, exc))
        return 2

    needle = 'def selftest():'
    if needle not in src:
        print('COULD NOT RUN: %r is not in the hook, so the crash cannot be '
              'injected where it matters.' % needle)
        return 2
    i = src.index(needle)
    j = src.index('\n', i) + 1
    crashed = src[:j] + CRASH + src[j:]

    if POST not in crashed:
        print('COULD NOT RUN: the post-fix __main__ wiring this driver quotes '
              'is no longer in the file. Re-read __main__ and update POST '
              'before trusting any verdict from here.')
        return 2
    prefix = crashed.replace(POST, PRE)

    sandbox = tempfile.mkdtemp(prefix='b17-locked-entry-')
    results = {}
    for label, blob in (('POST-FIX', crashed), ('PRE-FIX', prefix)):
        p = os.path.join(sandbox, 'hook_%s.py' % label.lower().replace('-', '_'))
        io.open(p, 'w', encoding='utf-8', newline=chr(10)).write(blob)
        r = subprocess.run([sys.executable, p, '--selftest'],
                           capture_output=True, text=True,
                           env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                    PYTHONUTF8='1'))
        results[label] = (r.returncode, r.stdout)
        print('%-9s exit = %s   stdout %d byte(s)'
              % (label, r.returncode, len(r.stdout)))
        for line in [l for l in r.stdout.splitlines() if l.strip()][-2:]:
            print('            | %s' % line[:150])

    bad = 0
    post_rc, post_out = results['POST-FIX']
    pre_rc, pre_out = results['PRE-FIX']
    if not (post_rc == 2 and 'COULD NOT RUN' in post_out):
        print('DID NOT REPRODUCE: the current wiring should exit 2 and say '
              'COULD NOT RUN.')
        bad += 1
    if pre_rc != 0:
        print('DID NOT REPRODUCE: the pre-fix wiring should exit 0 -- that is '
              'the defect. If it no longer does, this driver is measuring '
              'something else.')
        bad += 1
    if not bad:
        print('')
        print('BOTH MEASUREMENTS REPRODUCE. A crashed lock is exit 2 now and '
              'was exit 0 with empty output before, which is the one failure '
              'that silently disarms every arm in the file at once.')
    print('scratch: %s' % sandbox)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
