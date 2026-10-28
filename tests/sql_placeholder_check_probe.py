"""Probe for tools/sql_placeholder_check.py, using real data in both directions.

  P1  the locked fixtures classify correctly (exit 0).
  P2  THE REAL DEFECT: sql/alf-audit-owner-recovery.sql as committed at a93a74cb7
      (hank b58, the file Michael's run aborted on) is refused, exit 1.
  P3  the same file as fixed in b59 (b676e7e79) is clean, exit 0.
  P4  a path that never existed is COULD NOT RUN, exit 2, not clean.
  P5  an unresolvable ref is COULD NOT RUN, exit 2.

If a93a74cb7 or b676e7e79 is not an object in this clone, the probe says so and
exits 2. A probe whose subject is missing has not passed.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, 'tools', 'sql_placeholder_check.py')
F = 'sql/alf-audit-owner-recovery.sql'


def run(*a):
    p = subprocess.run([sys.executable, TOOL] + list(a), cwd=ROOT, capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout + p.stderr


def have(sha):
    return subprocess.run(['git', 'cat-file', '-e', sha + '^{commit}'], cwd=ROOT, capture_output=True).returncode == 0


def main():
    for sha in ('a93a74cb7', 'b676e7e79'):
        if not have(sha):
            print('COULD NOT RUN: %s is not an object in this clone' % sha)
            return 2
    arms = [
        ('P1 fixtures', ('--fixtures',), 0),
        ('P2 the b58 shipped file is refused', ('--ref', 'a93a74cb7', F), 1),
        ('P3 the b59 fixed file is clean', ('--ref', 'b676e7e79', F), 0),
        ('P4 a path that never existed is could-not-run', ('--ref', 'b676e7e79', 'sql/zz-never-existed.sql'), 2),
        ('P5 an unresolvable ref is could-not-run', ('--ref', 'zz-not-a-ref', F), 2),
    ]
    bad = 0
    for name, args, want in arms:
        got, out = run(*args)
        ok = got == want
        bad += not ok
        print('  %s  %-50s want %d got %d' % ('ok  ' if ok else 'FAIL', name, want, got))
        if not ok:
            print('       ' + out.strip().replace('\n', '\n       ')[:800])
    print('%d/%d arms' % (len(arms) - bad, len(arms)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
