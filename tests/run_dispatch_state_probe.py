#!/usr/bin/env python
"""tests/run_dispatch_state_probe.py -- controls for tools/dispatch_state.py.

THE WAY THIS TOOL FAILS DANGEROUSLY IS BY SHOWING TOO SHORT A LIST. A row it
wrongly classifies as CLOSED, or wrongly attributes to a busy session, simply
stops appearing -- and an empty dispatch list looks identical to a finished
platform. So the arms are weighted toward the OPEN direction: an unknown status
must default to open, a strikethrough title must not hide a row that is still
open underneath, and the classifier must be shown to move when its input moves.

Exit 0 all arms passed, 1 otherwise.
"""

import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
SUBJECT = os.path.join(REPO, 'tools', 'dispatch_state.py')

FAILS, PASSES = [], [0]


def ok(label, cond, detail=''):
    if cond:
        PASSES[0] += 1
        print('    ok   %s' % label)
    else:
        FAILS.append(label)
        print('    FAIL %s' % label)
        if detail:
            print('         %s' % str(detail)[:400])


import dispatch_state as D   # noqa: E402


print('\nA. open vs closed, and the direction the default leans')
ok('the fixture table passes', not D.self_check(verbose=False))
ok('EVERY done-word closes a row',
   all(not D.is_open('**%s 2026-01-01 (x)**' % w) for w in D.DONE_WORDS),
   [w for w in D.DONE_WORDS if D.is_open('**%s 2026-01-01 (x)**' % w)])
# THE ARM THAT MATTERS MOST. A vocabulary this file has not seen must surface
# the row, never hide it -- the reverse would let one new status word retire a
# row silently and for ever.
for unknown in ('QUUXED', 'PARKED', 'DEFERRED', 'HELD', 'PENDING', 'WONTFIX'):
    ok('an unseen status %r defaults to OPEN' % unknown,
       D.is_open('**%s 2026-01-01**' % unknown))
ok('a done-word only counts at the START -- "not CLOSED" stays open',
   D.is_open('not CLOSED yet, see below'))


print('\nB. owner parsing')
ok('a single owner is found', D.owners_of('Hank') == ['hank'])
ok('two owners are both found',
   D.owners_of('CC (fixed) / **Fourth** (the five stale claims)') == ['cc', 'fourth'])
ok('Michael is not a session', D.owners_of('**Michael** to run the migration') == [])
ok('a word merely CONTAINING a session name does not match',
   D.owners_of('unassigned, blocked, ccache') == [],
   D.owners_of('unassigned, blocked, ccache'))
ok('an em-dash owner cell yields nobody', D.owners_of('&mdash;') == [])


print('\nC. the live inputs are real, and an absent one is COULD NOT RUN')
claims, cp = D.live_claims()
ok('claims parse', claims is not None, cp)
ok('...and there is at least one active claim to join against',
   claims and len(claims) >= 1, claims)
rs, rp = D.rows()
ok('the index parses', rs is not None, rp)
ok('...into a realistic number of rows', rs and len(rs) > 400, len(rs or []))
ok('every row has an app, an item and a status',
   all(len(r) == 4 for r in (rs or [])))

TMP = tempfile.mkdtemp(prefix='ds_')
try:
    src = io.open(SUBJECT, encoding='utf-8').read()
    ANCHOR = "CLAIM_DIR = os.path.join(REPO, '.claude', 'claims')"
    ok('the claims-path anchor is present', src.count(ANCHOR) == 1,
       'anchor stale -- the could-not-run arm below tests NOTHING')
    broken = os.path.join(TMP, 'broken.py')
    io.open(broken, 'w', encoding='utf-8').write(
        src.replace(ANCHOR, "CLAIM_DIR = os.path.join(REPO, '.claude', 'NOPE')"))
    r = subprocess.run([sys.executable, broken], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', cwd=REPO,
                       env=dict(os.environ, PYTHONPATH=os.path.join(REPO, 'tools')))
    ok('AN ABSENT CLAIMS DIRECTORY IS COULD NOT RUN (2), not an empty claim list',
       r.returncode == 2, 'exit %s\n%s' % (r.returncode, r.stdout[-300:]))
    ok('...and it says so rather than reporting everything unclaimed',
       'COULD NOT RUN' in r.stdout, r.stdout[:200])
finally:
    shutil.rmtree(TMP, ignore_errors=True)
    ok('the scratch directory is gone', not os.path.isdir(TMP))


print('\nD. the report itself')
r = subprocess.run([sys.executable, SUBJECT], capture_output=True, text=True,
                   encoding='utf-8', errors='replace', cwd=REPO)
ok('it runs to completion', r.returncode in (0, 1, 2), r.stderr[-400:])
# IT DIED HERE ON ITS FIRST REAL RUN. The index carries emoji in row titles and
# Windows encodes captured stdout as cp1252, so the tool computed the right
# answer and then raised UnicodeEncodeError printing it -- the exact defect
# fixed in tools/run_semgrep.py hours earlier and measured as unswept across 94
# of 138 files in tools/. This arm is why it cannot come back silently.
ok('NO UnicodeEncodeError when stdout is CAPTURED, which is every hook and CI '
   'step', 'UnicodeEncodeError' not in (r.stderr or ''), r.stderr[-300:])
for section in ('ACTIVE CLAIMS', 'CONTESTED', "MICHAEL'S",
                'OPEN AND UNOWNED', 'DOES NOT DECIDE'):
    ok('the report carries the %r section' % section, section in r.stdout)
ok('it states its own limit rather than implying a verdict',
   'same work' in r.stdout and 'second guesser' in r.stdout, r.stdout[-400:])
rj = subprocess.run([sys.executable, SUBJECT, '--json'], capture_output=True,
                    text=True, encoding='utf-8', errors='replace', cwd=REPO)
import json
body = json.loads(rj.stdout[rj.stdout.index('{'):])
ok('--json parses and carries every bucket',
   all(k in body for k in ('open', 'contested', 'michael', 'unclaimed',
                           'unowned', 'claims')), sorted(body))
ok('the buckets partition the open rows -- none is lost between them',
   body['open'] == len(body['contested']) + len(body['michael'])
   + len(body['unclaimed']) + len(body['unowned']),
   (body['open'], len(body['contested']), len(body['michael']),
    len(body['unclaimed']), len(body['unowned'])))


print('\nE. teeth -- a classifier that calls everything closed must not report '
      'an empty, tidy platform')
TMP2 = tempfile.mkdtemp(prefix='ds2_')
try:
    ANCHOR2 = '    return True\n'
    ok('the teeth anchor is present', src.count(ANCHOR2) >= 1)
    bp = os.path.join(TMP2, 'broken2.py')
    io.open(bp, 'w', encoding='utf-8').write(
        src.replace('def is_open(status):\n', 'def is_open(status):\n    return False\n', 1))
    rb = subprocess.run([sys.executable, bp], capture_output=True, text=True,
                        encoding='utf-8', errors='replace', cwd=REPO,
                        env=dict(os.environ, PYTHONPATH=os.path.join(REPO, 'tools')))
    ok('the broken copy runs', rb.returncode in (0, 1, 2), rb.stderr[-300:])
    # The fixtures run BEFORE any row is classified, so an always-closed
    # classifier is caught by the blind lock rather than producing a clean,
    # empty and completely wrong dispatch list.
    ok('TEETH: an always-closed classifier exits COULD NOT RUN (2), not 0',
       rb.returncode == 2, 'exit %s\n%s' % (rb.returncode, rb.stdout[-300:]))
    ok('...and names the rule that failed rather than printing a report',
       'open/closed rule failed' in rb.stdout, rb.stdout[:250])
finally:
    shutil.rmtree(TMP2, ignore_errors=True)
    ok('the second scratch directory is gone', not os.path.isdir(TMP2))


print('\n' + '=' * 66)
print('%d passed, %d failed' % (PASSES[0], len(FAILS)))
for f in FAILS:
    print('  FAILED: %s' % f)
sys.exit(1 if FAILS else 0)
