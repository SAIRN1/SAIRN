"""Probe tools/index_duplicate_check.py, by attacking it.

The tool now reports ZERO pairs against the real index, which is only worth
saying because every arm below plants a duplicate in a throwaway index and
demands it be found. A checker that reports nothing is indistinguishable from
one that looks at nothing.

ARM 2 IS THE ONE THE REAL CASE NEEDED. Two rows for one subject whose only
difference is a moving COUNT -- "56 TIER A resources" against "53 TIER A
resources (was 56)" -- must match, which is why numbers are stripped before
comparing. A comparison that kept them would have scored the pair as different
and missed the case that prompted the tool.

ARM 3 IS THE CONTROL THAT MATTERS. A tool that flagged every pair of rows would
pass arms 1 and 2 and be useless, so two genuinely different subjects under the
same app must come back silent.

Run: python tests/run_index_duplicate_probe.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'index_duplicate_check.py')

failures = []


def check(name, ok, detail=''):
    print('  %-4s %-62s %s' % ('PASS' if ok else 'FAIL', name, detail))
    if not ok:
        failures.append(name)


HEAD = ('| App | Item | Status | Owner | Blocked on | Notes | Sz |\n'
        '|---|---|---|---|---|---|---|\n')


def run(body):
    tmp = tempfile.mkdtemp(prefix='idxdup_probe_')
    os.makedirs(os.path.join(tmp, 'docs'))
    io.open(os.path.join(tmp, 'docs', 'SAIRN-OPEN-WORK-INDEX.md'), 'w',
            encoding='utf-8', newline='\n').write(HEAD + body)
    shim = os.path.join(tmp, '_runner.py')
    io.open(shim, 'w', encoding='utf-8', newline='\n').write(
        'import sys, os\n'
        'sys.path.insert(0, %r)\n' % os.path.join(REPO, 'tools') +
        'import index_duplicate_check as I\n'
        "I.INDEX = os.path.join(%r, 'docs', 'SAIRN-OPEN-WORK-INDEX.md')\n" % tmp +
        'sys.exit(I.main(["x"]))\n')
    p = subprocess.run([sys.executable, shim], capture_output=True, text=True,
                       encoding='utf-8', errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
    shutil.rmtree(tmp, ignore_errors=True)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def row(app, item, status='Open'):
    return '| **%s** | %s | %s | unassigned | -- | notes here | S |\n' % (app, item, status)


print('INDEX DUPLICATE PROBE -- every fixture has a known answer\n')

# -- 1. two identical subjects
rc, out = run(row('Platform', 'the widget registry has no removal path for any resource') +
              row('Platform', 'the widget registry has no removal path for any resource'))
check('1a  an exact duplicate is reported', 'UNDECLARED               : 1' in out, '')
check('1b  exit code is non-zero', rc == 1, 'exit %d' % rc)

# -- 2. THE REAL CASE: same subject, moving count
rc, out = run(row('Platform', '**56 TIER A resources have no removal path** and here is the burn-down order') +
              row('Platform', '**53 TIER A resources have no removal path** (was 56) and here is the burn-down order'))
check('2a  a pair differing only by a COUNT is reported',
      'UNDECLARED               : 1' in out,
      'numbers are stripped before comparing -- the case that prompted the tool')
check('2b  and both line numbers are named', 'lines 3 and 4' in out, '')

# -- 3. CONTROL: two genuinely different subjects
rc, out = run(row('Platform', 'the widget registry has no removal path for any resource') +
              row('Platform', 'a licence key appears in a customer-facing URL query string'))
check('3a  CONTROL: different subjects are NOT reported',
      'UNDECLARED               : 0' in out, '')
check('3b  CONTROL: and it exits 0', rc == 0, 'exit %d' % rc)
check('3c  CONTROL: and it really compared them -- 2 rows',
      'rows compared            : 2' in out, 'a tool comparing 0 rows also reports 0 pairs')

# -- 4. the same subject under DIFFERENT apps is normal, not a duplicate
rc, out = run(row('StoneDesk', 'the write path reports success before the server answers') +
              row('SAIRNdental', 'the write path reports success before the server answers'))
check('4a  CONTROL: one defect in two apps is not a duplicate',
      'UNDECLARED               : 0' in out, 'two apps, two real pieces of work')

# -- 5. a closed row and its open twin still count
# A struck-through row is history, but it is still a second answer to
# "what needs doing" if the subject is live elsewhere.
rc, out = run(row('Platform', '~~the widget registry has no removal path for any resource~~', 'CLOSED') +
              row('Platform', 'the widget registry has no removal path for any resource'))
check('5a  strikethrough does not hide a duplicate',
      'UNDECLARED               : 1' in out, 'markup is normalised away before comparing')

# -- 6. a missing index is exit 2, not a pass
tmp = tempfile.mkdtemp(prefix='idxdup_probe_')
shim = os.path.join(tmp, '_runner.py')
io.open(shim, 'w', encoding='utf-8', newline='\n').write(
    'import sys, os\n'
    'sys.path.insert(0, %r)\n' % os.path.join(REPO, 'tools') +
    'import index_duplicate_check as I\n'
    "I.INDEX = os.path.join(%r, 'nope.md')\n" % tmp +
    'sys.exit(I.main(["x"]))\n')
p = subprocess.run([sys.executable, shim], capture_output=True, text=True,
                   encoding='utf-8', errors='replace',
                   env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
check('6a  a missing index exits 2, not 0', p.returncode == 2, 'exit %d' % p.returncode)
check('6b  and says nothing was checked', 'NOT a pass' in p.stdout, '')
shutil.rmtree(tmp, ignore_errors=True)

# -- 7. the real index
p = subprocess.run([sys.executable, TOOL], capture_output=True, text=True,
                   encoding='utf-8', errors='replace', cwd=REPO,
                   env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
check('7a  the real index has no undeclared duplicate pairs', p.returncode == 0,
      'exit %d' % p.returncode)
check('7b  and it compared a real number of rows',
      'rows compared            : 0' not in p.stdout and 'rows compared' in p.stdout,
      [l.strip() for l in p.stdout.split('\n') if 'rows compared' in l][:1])

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  %s' % f)
sys.exit(1 if failures else 0)
