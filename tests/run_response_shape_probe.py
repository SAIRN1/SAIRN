#!/usr/bin/env python
"""Control for tools/response_shape_check.py.

    python tests/run_response_shape_probe.py      (exit 0 pass, 1 fail)

THE ARM THAT MATTERS IS THE RETROACTIVE ONE. A sweep written after the defects
were already fixed reports CLEAN on its first run, and a clean first run is
indistinguishable from a sweep that looks at nothing. So this drives the
checker over the REAL historical content of the two files that carried the
bug -- read out of git, not retyped -- and demands it find them.

Both directions throughout: every arm that asserts a finding is paired with one
that asserts the same code says nothing about a correct call site.

Exit 0 pass, 1 fail, 2 could not run (git unavailable -- the historical arms
cannot be faked, so they are COULD NOT RUN and never a silent pass).
"""
# Declares, for tools/checker_control_check.py, which checker this file holds.
CONTROLS_FOR = ['response_shape_check.py']

import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
import response_shape_check as R                                  # noqa: E402

FAILS, PASSES = [], [0]


def ok(label, cond, detail=''):
    if cond:
        PASSES[0] += 1
        print('  ok   %s' % label)
    else:
        FAILS.append(label)
        print('  FAIL %s\n       %s' % (label, str(detail)[:400]))


def git(*args):
    try:
        r = subprocess.run(['git'] + list(args), cwd=REPO, capture_output=True,
                           text=True, encoding='utf-8', errors='replace')
        return r.stdout if r.returncode == 0 else None
    except Exception:                                              # noqa: BLE001
        return None


print('1. the checker holds its own fixtures, both directions')
_bad = R.self_check(verbose=False)
ok('every fixture classifies as declared (%d fixtures)' % len(R.FIXTURES),
   not _bad, 'failing: %s' % _bad)
ok('there are fixtures in BOTH directions -- a one-sided lock proves nothing',
   any(m for _l, m, _s in R.FIXTURES) and any(not m for _l, m, _s in R.FIXTURES))

print('')
print('2. THE RETROACTIVE ARM -- the two real defects, read out of git')
# tools/cron_liveness_check.py as it stood before d8d000e0 fixed it. The sha is
# resolved by SUBJECT rather than hard-coded, because a rebase moves it and a
# hard-coded sha would turn this arm into a silent skip the first time main is
# rewritten.
_fix = git('log', '--format=%H', '-1', '--grep',
           'could NEVER have returned anything but COULD NOT TELL')
if not _fix or not _fix.strip():
    print('  COULD NOT RUN: the fix commit was not found by subject.')
    print('  The historical arms cannot be faked, so this is exit 2, not a pass.')
    sys.exit(2)

_before = git('show', '%s~1:tools/cron_liveness_check.py' % _fix.strip())
ok('the pre-fix source was readable out of git', bool(_before),
   'git show returned nothing')
if _before:
    _f = R.scan_source(_before, 'tools/cron_liveness_check.py')
    ok('the checker FINDS the cron_liveness defect in its real historical form',
       len(_f) > 0, 'found nothing in the version that shipped the bug')
    ok('...and names the isinstance line specifically, not just "something here"',
       any('isinstance' in x['why'] for x in _f),
       [x['why'] for x in _f])

# And the other direction on the SAME file: the fixed version must be silent.
_after = git('show', '%s:tools/cron_liveness_check.py' % _fix.strip())
if _after:
    ok('...and says NOTHING about the fixed version of that same file',
       len(R.scan_source(_after, 'tools/cron_liveness_check.py')) == 0,
       R.scan_source(_after, 'tools/cron_liveness_check.py'))

print('')
print('3. the sweep reports a third state rather than folding it into clean')
_findings, _unreadable = R.sweep()
ok('the live sweep runs at all', isinstance(_findings, list))
# A file it could not parse must not be counted as clean. Driven rather than
# asserted about the source, because a comment saying so has never kept a tool
# honest on this platform.
_bad_src = 'def f(:\n    pass\n'
try:
    R.scan_source(_bad_src, '<broken>')
    ok('a syntactically broken file raises rather than returning []', False,
       'scan_source swallowed a SyntaxError')
except SyntaxError:
    ok('a syntactically broken file raises rather than returning []', True)

print('')
print('4. TEETH -- a checker that always says the same thing is caught')
# If scan_source ever returns [] for everything, arm 2 goes red. If it ever
# returns a finding for everything, THIS goes red. Neither direction can pass
# quietly.
_always = R.scan_source('x = 1\n', '<empty>')
ok('a file with no fetch call at all produces no finding', _always == [],
   _always)

print('')
print('=' * 66)
print('%d passed, %d failed' % (PASSES[0], len(FAILS)))
for f in FAILS:
    print('  FAILED: %s' % f)
sys.exit(1 if FAILS else 0)
