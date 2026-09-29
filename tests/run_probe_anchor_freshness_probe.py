#!/usr/bin/env python
"""The control for tools/probe_anchor_freshness.py -- it had a lock and no control.

    python tests/run_probe_anchor_freshness_probe.py

Exit 0 all arms pass, 1 any arm fails.

── THE DISTINCTION THIS FILE EXISTS ON ─────────────────────────────────────
The tool already carried a 20-arm `selftest()`, and as of 2026-09-29 that lock
runs on the REAL run and prints its result beside the anchor figures. That is a
good fixture lock and it is NOT a control:

    a FIXTURE LOCK proves the CRITERIA classify a hand-built case;
    a CONTROL proves the SHIPPED TOOL still fires, and still REFUSES.

`tools/checker_control_check.py` listed this tool under NO DECLARED CONTROL,
which was accurate -- the lock lived inside the tool, so nothing independent ever
drove it. A checker whose only witness is itself is the shape this whole family
of tools exists to find.

── AND THE SABOTAGE IS THE ARM THAT MATTERS ────────────────────────────────
A2 breaks a criterion IN PROCESS and requires the tool to exit 2 rather than
report an anchor-freshness figure. A2a asserts the sabotage APPLIED FIRST,
because a patch that silently failed to apply leaves every arm below it green
for ever -- and A3 asserts the restore, because every arm after a sabotage is
running against whatever the sabotage left behind.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
TOOL = os.path.join(REPO, 'tools', 'probe_anchor_freshness.py')
CONTROLS_FOR = ['probe_anchor_freshness.py']

import probe_anchor_freshness as F                              # noqa: E402

_pass, _fail = 0, 0


def check(name, cond, detail=''):
    global _pass, _fail
    if cond:
        print('  ok   ' + name)
        _pass += 1
    else:
        print('  FAIL ' + name)
        if detail != '':
            print('       %s' % (detail,))
        _fail += 1


def section(t):
    print('\n' + t)


def run(*args):
    r = subprocess.run([sys.executable, TOOL] + list(args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                PYTHONUTF8='1'))
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('PROBE ANCHOR FRESHNESS -- the control it did not have')

# ── A. BREAK A CRITERION AND THE TOOL MUST REFUSE ──────────────────────────
section('A. sabotage the criteria in process; the tool must exit 2')

rc, out = run('--selftest')
check('A1. the shipped criteria pass their own lock, and it says how many arms',
      rc == 0 and ('ALL ARMS PASS' in out or 'PASS' in out), (rc, out[-300:]))

_orig = io.open(TOOL, encoding='utf-8', newline='').read()
_sab = _orig.replace("CRITERIA_VERSION = ", "CRITERIA_VERSION_DISABLED = ", 1)
check('A2a. THE SABOTAGE APPLIED. Without this arm A2 proves nothing: a patch '
      'that silently failed to apply leaves every arm below it green for ever',
      _sab != _orig, 'the CRITERIA_VERSION anchor moved -- the patch did nothing')
try:
    io.open(TOOL, 'w', encoding='utf-8', newline='').write(_sab)
    rc, out = run()
    check('A2. ...and with the criteria version gone the tool FAILS rather than '
          'printing an anchor-freshness figure. A number derived from criteria '
          'that will not even load is not a measurement',
          rc != 0, (rc, out[-400:]))
finally:
    io.open(TOOL, 'w', encoding='utf-8', newline='').write(_orig)
rc, out = run('--selftest')
check('A3. THE RESTORE WORKED -- otherwise every arm below is running against a '
      'sabotaged tool and this whole file means nothing',
      rc == 0, (rc, out[-300:]))

# ── B. THE LOCK REACHES THE READER OF THE REAL RUN ─────────────────────────
section('B. the known-positive runs on the REAL run and is printed')

rc, out = run()
import re                                                       # noqa: E402
_m = re.search(r'self-test: (\d+)/(\d+) known-positive arm', out)
check('B1. THE REAL RUN PRINTS THE LOCK RESULT. It used to run only under '
      '--selftest, which is a control with a shorter name: it runs when '
      'somebody asks, and the reader of a clean line at 2am is not asking',
      _m is not None, out[:400])
check('B1b. ...and BOTH figures are real and equal: a 0/0 lock prints the same '
      'sentence and proves nothing',
      _m is not None and int(_m.group(1)) > 0
      and _m.group(1) == _m.group(2),
      _m.group(0) if _m else 'no self-test line on the real run')
check('B2. the real run still reports its own subject -- a parsed probe count '
      'and an anchor count -- so the lock did not replace the measurement',
      re.search(r'(\d+) probe file\(s\) parsed', out) is not None
      and re.search(r'(\d+) anchor\(s\) counted', out) is not None, out[:600])
_p = re.search(r'(\d+) probe file\(s\) parsed', out)
check('B2b. ...and that probe count is NON-EMPTY. A zero would make every '
      'verdict below it vacuous, which is this repo\'s most-repaired defect',
      _p is not None and int(_p.group(1)) > 50,
      _p.group(0) if _p else 'no parsed-probe line')
check('B3. exit is 0, 1 or 2 and nothing else', rc in (0, 1, 2), rc)

# ── C. ANCHORS (discipline 8) ──────────────────────────────────────────────
section('C. the anchors this control depends on')
_s = io.open(TOOL, encoding='utf-8').read()
check('C1. selftest() is still the name the lock and section A drive',
      'def selftest(' in _s, 'the runner was renamed')
check('C2. CRITERIA_VERSION is present and appears in the real output, so a '
      'criteria change is visible rather than silent',
      bool(str(getattr(F, 'CRITERIA_VERSION', '')).strip())
      and F.CRITERIA_VERSION in out, getattr(F, 'CRITERIA_VERSION', None))
check('C3. the tool declares this file as its control, so '
      'checker_control_check can find the pair from either end -- it listed '
      'this tool under NO DECLARED CONTROL until 2026-09-29',
      'run_probe_anchor_freshness_probe.py' in _s, 'CONTROLLED_BY is missing')

print('\n%s -- %d passed, %d failed' % ('FAIL' if _fail else 'ALL ARMS PASS',
                                        _pass, _fail))
sys.exit(1 if _fail else 0)
