"""Does accepted_risk_scan find an acceptance, and does it know when one is registered?

    python tests/run_accepted_risk_probe.py

The arm that matters most is 2c: registering a file must CHANGE the answer. A
cross-check that reports everything unregistered forever would look identical to
a working one on day zero, when the register is empty.
"""
# REQUIREMENT: every accepted risk carries a trigger and an owner, because a risk
#   accepted with no re-read condition is indistinguishable from one nobody
#   noticed
#
import contextlib
import io as _io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
os.chdir(REPO)

import accepted_risk_scan as ars   # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('  ok   ' if cond else '  FAIL ') + name
          + (('\n        ' + str(detail)[:280]) if (detail and not cond) else ''))


def run(files, registers):
    real_read, real_sources = ars.read, ars.sources

    def fake_read(rel):
        if rel in ars.REGISTERS:
            return registers
        return files.get(rel)
    ars.read = fake_read
    ars.sources = lambda: sorted(files)
    buf = _io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = ars.main([])
    finally:
        ars.read, ars.sources = real_read, real_sources
    return rc, buf.getvalue()


ACCEPT = "// It is not a perfect gate -- a leaked id is a real credential.\nvar x=1;\n"
PLAIN = "// this file does an ordinary thing\nvar y=2;\n"

print('--- 1. it finds acceptance language, and only that ---')
rc, out = run({'api/a.js': ACCEPT}, 'nothing here')
check('1a  a file that accepts a risk is found', 'carrying acceptance language : 1' in out, out)
rc, out = run({'api/b.js': PLAIN}, 'nothing here')
check('1b  CONTROL: an ordinary file is not -- 1a is not passing because it '
      'flags everything', 'carrying acceptance language : 0' in out, out)

print('\n--- 2. the register cross-check ---')
rc, out = run({'api/a.js': ACCEPT}, 'nothing here')
check('2a  an unregistered acceptance is reported as unregistered',
      'NOT named in any register: 1' in out, out)
rc, out = run({'api/a.js': ACCEPT}, 'see api/a.js, accepted 2026-09-14')
check('2b  naming the file in a register clears it',
      'NOT named in any register: 0' in out, out)
check('2c  CONTROL: registering CHANGES the answer, so 2a is not passing '
      'because the cross-check always says unregistered',
      'NOT named in any register: 1' in run({'api/a.js': ACCEPT}, 'x')[1]
      and 'NOT named in any register: 0' in out, out)
rc, out = run({'api/deep/a.js': ACCEPT}, 'a.js is fine')
check('2d  the BASENAME counts too -- a register rarely writes a full path',
      'NOT named in any register: 0' in out, out)

print('\n--- 3. weights order the read-list ---')
rc, out = run({'api/strong.js': ACCEPT, 'api/weak.js': "// done on purpose\nvar z=3;\n"},
              'nothing')
check('3a  the strong phrase outranks the weak one',
      out.index('WEIGHT 3') < out.index('WEIGHT 1'), out)

print('\n--- 4. it refuses rather than reporting a clean platform ---')
real_read = ars.read
ars.read = lambda rel: None
buf = _io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = ars.main([])
ars.read = real_read
check('4a  NO readable register exits 2 -- otherwise every file looks '
      'unregistered and the report is loudest when it knows least', rc == 2, rc)

rc, out = run({}, 'a register')
check('4b  zero source files exits 2, because zero targets is not a clean sweep',
      rc == 2, rc)

print('\n--- 5. it says a count is not a score ---')
rc, out = run({'api/a.js': ACCEPT}, 'x')
check('5a  the output refuses to be read as a score',
      'NOT A SCORE' in out and 'zero is not the goal' in out.lower(), out)

print('\n%d passed, %d failed' % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
