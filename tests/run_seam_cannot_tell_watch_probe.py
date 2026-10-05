"""Holds tools/seam_cannot_tell_watch.py, in BOTH directions.

A watch that cannot fail is a watch nobody can trust, and a watch that fails on
a clean tree is one that gets ignored. Both halves are driven here.

NOTHING IS MUTATED IN THE REPO. Every arm runs the watch against a TEMPORARY
copy of the baseline and, where a mutant tool is needed, a temporary copy of
`sairn_seam_check.py` -- via the two environment overrides the arms set below.
The 2026-09-25 ablation lesson applies: a mutant that does not PARSE scores as
CAUGHT for the wrong reason, so the stand-in tools here are real, running
Python and each is executed once on its own first.
"""
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCH = os.path.join(REPO, 'tools', 'seam_cannot_tell_watch.py')

passed = 0
failed = 0


def check(name, got, want):
    global passed, failed
    if got == want:
        print('  ok   ' + name)
        passed += 1
    else:
        print('  FAIL ' + name)
        print('       expected %r, got %r' % (want, got))
        failed += 1


def run(seam_src=None, baseline=None, args=()):
    """Run the watch with a stand-in dependency and/or baseline.

    The watch resolves both from module-level constants, so the arms rewrite a
    COPY of the watch with those two paths substituted. That keeps the real
    tool untouched and keeps the substitution visible instead of relying on an
    env var the tool would have to grow for the test's benefit.
    """
    src = open(WATCH, encoding='utf-8').read()
    d = tempfile.mkdtemp(prefix='seamwatch_')
    if seam_src is not None:
        p = os.path.join(d, 'stand_in_seam.py')
        open(p, 'w', encoding='utf-8').write(seam_src)
        src = src.replace(
            "SEAM = os.path.join(REPO, 'tools', 'sairn_seam_check.py')",
            'SEAM = %r' % p)
    if baseline is not None:
        p = os.path.join(d, 'baseline.json')
        if baseline is not False:        # False means "do not create it"
            open(p, 'w', encoding='utf-8').write(json.dumps(baseline))
        src = src.replace(
            "BASELINE = os.path.join(REPO, 'docs', 'seam-cannot-tell-baseline.json')",
            'BASELINE = %r' % p)
    w = os.path.join(d, 'watch_under_test.py')
    open(w, 'w', encoding='utf-8').write(src)
    r = subprocess.run([sys.executable, w] + list(args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=600)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


# A stand-in that prints the real tool's output shape with a controllable set.
def seam_stub(rows):
    body = '\n'.join(
        '  CANNOT TELL %-30s -> %-28s %s' % (c, dep, why) for c, dep, why in rows)
    return (
        'print(%r)\n' % body +
        'print("")\n' +
        'print("%d clean, 0 not-forwarded, %d could-not-tell")\n'
        % (96, len(rows)))


ROWS2 = [('api/a.js', 'api/_lib/auth.js', 'reason one'),
         ('api/b.js', 'api/_lib/auth.js', 'reason two')]


def key(c, dep, why):
    return '%s -> %s :: %s' % (c, dep, why)


BASE2 = {'counts': {'clean': 96, 'not_forwarded': 0, 'could_not_tell': 2,
                    'total_seams': 98},
         'seams': sorted(key(*r) for r in ROWS2)}

print('tools/seam_cannot_tell_watch.py')
print()
print('A. the paired POSITIVE -- it must pass on an unchanged set, or it will be ignored')
rc, out = run(seam_src=seam_stub(ROWS2), baseline=BASE2)
check('A1 same set, name for name -> exit 0', rc, 0)
check('A2 ...and it says so rather than printing nothing',
      'No change' in out, True)
check('A3 the DENOMINATOR is published, not implied',
      '96 clean, 0 not-forwarded, 2 could-not-tell' in out, True)

print()
print('B. a RISE is caught and the new seam is NAMED')
rc, out = run(seam_src=seam_stub(ROWS2 + [('api/c.js', 'api/_lib/auth.js', 'reason three')]),
              baseline=BASE2)
check('B1 one more unreadable seam -> exit 1', rc, 1)
check('B2 the NEW seam is named, not just counted', 'api/c.js' in out, True)
check('B3 and the unchanged two are NOT reported as new',
      out.count('    + ') == 1, True)

print()
print('C. CHURN AT A CONSTANT COUNT -- the case a count-only watch cannot see')
churn = [ROWS2[0], ('api/zz.js', 'api/_lib/auth.js', 'reason nine')]
rc, out = run(seam_src=seam_stub(churn), baseline=BASE2)
check('C1 total still 2, one swapped -> STILL exit 1', rc, 1)
check('C2 the arrival is named', 'api/zz.js' in out, True)
check('C3 the departure is named too, not silently absorbed',
      'api/b.js' in out and '    - ' in out, True)

print()
print('D. it FAILS CLOSED, four ways, and never answers 0')
# D1 points the watch at a path that does not exist, which is the
# missing-dependency case. Built by hand rather than through run() because
# run() has to CREATE the stand-in file to pass it.
src = open(WATCH, encoding='utf-8').read()
d = tempfile.mkdtemp(prefix='seamwatch_missing_')
w = os.path.join(d, 'w.py')
open(w, 'w', encoding='utf-8').write(src.replace(
    "SEAM = os.path.join(REPO, 'tools', 'sairn_seam_check.py')",
    "SEAM = %r" % os.path.join(d, 'does_not_exist.py')))
r = subprocess.run([sys.executable, w], cwd=REPO, capture_output=True,
                   text=True, encoding='utf-8', errors='replace', timeout=120)
check('D1 dependency MISSING -> exit 2 COULD NOT RUN, not 0', r.returncode, 2)
check('D2 ...and it NAMES the tool it could not run',
      'does_not_exist.py' in (r.stdout or '') or 'not on disk' in (r.stdout or ''), True)

rc, out = run(seam_src='print("no summary line here at all")\n', baseline=BASE2)
check('D3 summary line UNPARSEABLE -> exit 2, not a silent zero', rc, 2)

rc, out = run(seam_src='import sys; sys.stderr.write("boom\\n"); sys.exit(3)\n',
              baseline=BASE2)
check('D4 dependency CRASHES -> exit 2', rc, 2)

rc, out = run(seam_src=seam_stub(ROWS2), baseline=False)
check('D5 baseline MISSING -> exit 2 with the write command', rc, 2)
check('D6 ...and it prints the command rather than inventing a baseline',
      '--propose' in out, True)

print()
print('E. the COUNT and the NAMES must agree, or neither is reported')
# Summary claims 5, only 2 rows printed. A watch that trusted either would be
# reporting about a set it cannot see.
lying = ('print(%r)\nprint("")\nprint("96 clean, 0 not-forwarded, 5 could-not-tell")\n'
         % '\n'.join('  CANNOT TELL %-30s -> %-28s %s' % r for r in ROWS2))
rc, out = run(seam_src=lying, baseline=BASE2)
check('E1 summary says 5, two rows parsed -> exit 2 rather than a guess', rc, 2)

print()
print('F. --propose PRINTS and must NOT write the baseline itself')
rc, out = run(seam_src=seam_stub(ROWS2), baseline=BASE2, args=('--propose',))
check('F1 --propose exits 0', rc, 0)
check('F2 it emits parseable JSON carrying the seams',
      'seams' in out and 'api/a.js' in out, True)
check('F3 the output says the file is never self-updated',
      'never updated by the watch itself' in out or 're-baselines' in out, True)

print()
print('%d passed, %d failed' % (passed, failed))
sys.exit(1 if failed else 0)
