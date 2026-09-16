"""tests/run_sabotage_control_probe.py -- the no-op-control detector can itself
be shown to fire and to stay quiet.

    python tests/run_sabotage_control_probe.py

This tool exists because a negative control that silently stops breaking its
target is indistinguishable from one that works. A detector for that failure
which could itself go quiet would be the same defect one level up, so the arms
here are deliberately about the detector's own blind spots:

  * a GUARD IN A COMMENT must not count -- that is the comment-quoting class
    (docs/SAIRN-PROCESS-RULES.md 1.2) and it would let a probe pass by
    describing a check it does not perform;
  * a probe that writes a FRESH FIXTURE must not be judged at all -- it has no
    anchor to go stale, and counting it would inflate the denominator with
    probes that cannot have the defect;
  * the fire rate must be neither 0% nor 100% of the tree.

AND THE ONE THAT MATTERS MOST: arm 4 plants BOTH shapes on throwaway files and
demands the detector separate them. A detector that answered UNGUARDED to
everything would satisfy every positive arm above.
"""
# REQUIREMENT: the detector that measures whether negative controls still break
#   their target can itself be shown to fire AND to stay quiet, because a
#   meta-detector that goes silent hides every unguarded control beneath it
#
import io
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import sabotage_control_check as S                              # noqa: E402

failures = []


def check(label, ok, detail=''):
    print(('  PASS ' if ok else '  FAIL ') + label + (('   ' + str(detail)) if detail else ''))
    if not ok:
        failures.append(label)


print('1. the blind lock')
check('1a  every hand-decided fixture classifies as written', S.run_fixtures() == [],
      S.run_fixtures())
p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'sabotage_control_check.py'),
                    '--fixtures'], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
check('1b  the lock runs alone and passes', p.returncode == 0, 'exit %d' % p.returncode)
check('1c  it states it ran before the tree was read',
      'before the tests tree was read' in (p.stdout or ''))

print('2. a guard in a COMMENT does not count')
commented = ("# assert old in src\n# m != src\n"
             "src = open(p).read()\nopen(p,'w').write(src.replace('a','b'))\n")
check('2a  a probe that only DESCRIBES a guard is still UNGUARDED',
      S.analyse('x.py', commented)['guarded'] is False)
real = ("src = open(p).read()\nm = src.replace('a','b')\nassert m != src\n"
        "open(p,'w').write(m)\n")
check('2b  CONTROL: the same guard in CODE does count -- or 2a passes on a '
      'detector that never sees a guard at all',
      S.analyse('x.py', real)['guarded'] is True)

print('3. a probe with no anchor to rot is not judged')
fresh = "open(p,'w').write('| A | B |\\n| 1 | 2 |\\n')\n"
check('3a  writing a FRESH fixture is not a sabotage', S.analyse('x.py', fresh) is None)
readonly = "src = open(p).read()\nassert 'x' in src\n"
check('3b  a read-only probe is not a sabotage', S.analyse('x.py', readonly) is None)

print('4. THE CONTROL THAT MATTERS -- both shapes, side by side')
tmp = tempfile.mkdtemp(prefix='sabctl-')
bad_p = os.path.join(tmp, 'unguarded_probe.py')
good_p = os.path.join(tmp, 'guarded_probe.py')
io.open(bad_p, 'w', encoding='utf-8', newline='\n').write(
    "src = io.open(t).read()\nio.open(t,'w').write(src.replace('needle','xxx'))\n")
io.open(good_p, 'w', encoding='utf-8', newline='\n').write(
    "src = io.open(t).read()\nm = src.replace('needle','xxx')\nassert m != src\n"
    "io.open(t,'w').write(m)\n")
a_bad = S.analyse('unguarded_probe.py', io.open(bad_p, encoding='utf-8').read())
a_good = S.analyse('guarded_probe.py', io.open(good_p, encoding='utf-8').read())
check('4a  the unguarded one is reported', a_bad and a_bad['guarded'] is False)
check('4b  the guarded one is NOT -- the detector discriminates rather than '
      'answering UNGUARDED to everything', a_good and a_good['guarded'] is True)
import shutil
shutil.rmtree(tmp, ignore_errors=True)

print('5. the real tree -- reported as a measurement, not an expectation')
rows = []
for root, _d, files in os.walk(os.path.join(REPO, 'tests')):
    for f in sorted(files):
        if not (f.endswith('.py') or f.endswith('.js')):
            continue
        rel = os.path.relpath(os.path.join(root, f), REPO).replace(os.sep, '/')
        a = S.analyse(rel, io.open(os.path.join(root, f), encoding='utf-8',
                                   errors='replace').read())
        if a:
            rows.append(a)
un = [r for r in rows if not r['guarded']]
check('5a  it found sabotaging probes at all', len(rows) > 5, len(rows))
check('5b  it does NOT report every one as unguarded -- that would be a detector '
      'stuck on one answer', len(un) < len(rows), '%d of %d' % (len(un), len(rows)))
check('5c  and it does not report every one as guarded either -- there really are '
      'unguarded controls in this repo today', len(un) > 0, len(un))
print('    MEASURED NOW: %d sabotaging probes, %d unguarded' % (len(rows), len(un)))

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  ' + f)
sys.exit(1 if failures else 0)
