"""tests/run_new_checker_probe.py

Run:  python tests/run_new_checker_probe.py

The control for tools/new_checker.py -- item 28's scaffold generator.

CONTROLS_FOR = ['new_checker.py']

A GENERATOR IS A CHECKER-SHAPED RISK. Whatever it emits gets copied into the
repo and trusted, so the two things worth proving are the two a reader cannot
see by looking at the templates:

  1. THE THING IT EMITS REFUSES. A scaffold that starts out reporting CLEAN
     manufactures, on demand, the defect this platform keeps finding -- a check
     that reads as coverage and has never been able to fire. Arm B runs the
     freshly generated checker and demands exit 2.

  2. THE SCAFFOLD IS COMPLETABLE. A refusal that cannot be turned off is just a
     broken file. Arm D writes a real rule and real fixtures into the generated
     checker and demands the WHOLE thing go green -- lock, sweep and both arms
     of its own generated probe. Without this, arm B is satisfied by a generator
     that emits garbage.

Together those two are the pair. Either alone is passed by something useless:
a generator emitting a file that always refuses passes 1, and one emitting a
file that always exits 0 passes nothing but looks fine until somebody promotes
it.

EVERYTHING HAPPENS IN A THROWAWAY WORKTREE. The generator writes into the repo
it is run from, so running it here would leave two files in this clone -- and a
probe that leaves artefacts behind is one somebody eventually deletes.
"""
import io
import os
import subprocess
import sys
import tempfile

CONTROLS_FOR = ['new_checker.py']

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
FAIL = []
NAME = 'zzprobe_shape'


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else '\n        ' + str(detail)[:600]))
    if not cond:
        FAIL.append(name)


def git(cwd, *args):
    return subprocess.run(['git', '-C', cwd] + list(args), capture_output=True, text=True, encoding='utf-8', errors='replace')


def run(cwd, *args):
    r = subprocess.run([sys.executable] + list(args), capture_output=True,
                       text=True, encoding='utf-8', errors='replace', cwd=cwd, timeout=300)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def worktree():
    d = os.path.join(tempfile.gettempdir(), 'newchk-%d' % os.getpid())
    if os.path.isdir(d):
        git(REPO, 'worktree', 'remove', '--force', d)
    git(REPO, 'worktree', 'add', '-q', '--detach', d, 'HEAD')
    # THE GENERATOR IS COPIED FROM THIS CLONE, not taken from HEAD. A control
    # that only exercises the committed version cannot say anything about the
    # change being made, which is the one moment it is for.
    src = io.open(os.path.join(REPO, 'tools', 'new_checker.py'), encoding='utf-8').read()
    io.open(os.path.join(d, 'tools', 'new_checker.py'), 'w',
            encoding='utf-8', newline='').write(src)
    return d


print('new_checker -- the control')
wt = worktree()
try:
    GEN = os.path.join(wt, 'tools', 'new_checker.py')
    CHK = os.path.join(wt, 'tools', '%s_check.py' % NAME)
    PRB = os.path.join(wt, 'tests', 'run_%s_probe.py' % NAME)

    # ── A. it generates, and it refuses to clobber ─────────────────────────
    print('\n--- A. generation ---')
    rc, out = run(wt, GEN, NAME, 'a probe shape')
    ok('A1 it exits 0', rc == 0, 'rc=%d\n%s' % (rc, out))
    ok('A2 it wrote the checker', os.path.isfile(CHK), out)
    ok('A3 it wrote the control pair too, not just the checker', os.path.isfile(PRB), out)
    ok('A4 it prints the next steps IN ORDER rather than leaving it to memory',
       'fixtures' in out.lower() and 'rule()' in out, out)
    ok('A5 and says what it deliberately did NOT wire',
       'REGISTRY' in out and 'PURPOSES' in out, out)
    rc2, out2 = run(wt, GEN, NAME, 'again')
    ok('A6 A SECOND RUN REFUSES rather than clobbering a rule somebody wrote',
       rc2 == 2 and 'REFUSING' in out2, 'rc=%d\n%s' % (rc2, out2))
    rc3, out3 = run(wt, GEN, 'Bad-Name', 'x')
    ok('A7 a name that would break the derived filenames is refused',
       rc3 == 2 and 'lower_snake_case' in out3, 'rc=%d\n%s' % (rc3, out3))

    # ── B. THE PROPERTY THAT MATTERS: what it emits REFUSES ────────────────
    print('\n--- B. the generated checker cannot report clean ---')
    rc, out = run(wt, CHK)
    ok('B1 it exits 2 -- could-not-run, NOT clean', rc == 2, 'rc=%d\n%s' % (rc, out))
    ok('B2 and says nothing real was judged', 'NOTHING REAL WAS JUDGED' in out, out)
    ok('B3 it never prints a CLEAN line', 'CLEAN --' not in out, out)

    # ── C. the generated probe fails where it should ───────────────────────
    print('\n--- C. the generated control pair is honest about being unfinished ---')
    rc, out = run(wt, PRB)
    ok('C1 the generated probe FAILS while the rule is unwritten', rc == 1, 'rc=%d\n%s' % (rc, out))
    ok('C2 and the failing arms are the two DIRECTIONS, not the lock',
       'B1 the planted defect is REPORTED' in out and 'B2 THE PAIR' in out, out)

    # ── D. THE PAIR: implement the rule and the whole thing goes green ─────
    # Without this arm, B is satisfied by a generator that emits garbage.
    print('\n--- D. the scaffold is completable ---')
    src = io.open(CHK, encoding='utf-8').read()
    anchor = "    raise NotImplementedError('rule() has not been written yet')"
    if anchor not in src:
        raise AssertionError('the SABOTAGE did not land: the rule() stub anchor '
                             'is not in the generated file -- the template moved')
    src = src.replace(anchor,
                      "    return ['%s: says BANANA' % path] if 'BANANA' in src else []")
    old_fix = ("    ('REPLACE ME: a file that MUST be flagged', 'f.js',\n"
               "     'the shape this checker exists to catch', True),\n"
               "    ('REPLACE ME: a file that must NOT be flagged', 'f.js',\n"
               "     'an ordinary line with nothing wrong with it', False),")
    if old_fix not in src:
        raise AssertionError('the SABOTAGE did not land: the FIXTURES block anchor moved')
    src = src.replace(old_fix,
                      "    ('a file that says BANANA', 'f.js', 'var x = BANANA;', True),\n"
                      "    ('a file that does not', 'f.js', 'var x = 1;', False),")
    io.open(CHK, 'w', encoding='utf-8', newline='').write(src)
    if 'BANANA' not in io.open(CHK, encoding='utf-8').read():
        raise AssertionError('the SABOTAGE did not land: not on disk')

    rc, out = run(wt, CHK, '--fixtures')
    ok('D1 with a real rule the blind lock passes', rc == 0, 'rc=%d\n%s' % (rc, out))

    pb = io.open(PRB, encoding='utf-8').read()
    pb = pb.replace("'REPLACE ME: the shape this checker exists to catch'", "'var x = BANANA;'")
    pb = pb.replace("'REPLACE ME: an ordinary file with nothing wrong'", "'var x = 1;'")
    io.open(PRB, 'w', encoding='utf-8', newline='').write(pb)
    if 'BANANA' not in io.open(PRB, encoding='utf-8').read():
        raise AssertionError('the SABOTAGE did not land in the probe')

    rc, out = run(wt, PRB)
    ok('D2 AND THE GENERATED PROBE NOW PASSES BOTH DIRECTIONS -- the scaffold '
       'is completable, not merely refusing', rc == 0, 'rc=%d\n%s' % (rc, out))
    ok('D3 including the arm that plants the defect', 'PASS  B1' in out, out)
    ok('D4 and the arm that leaves clean code alone', 'PASS  B2' in out, out)
finally:
    git(REPO, 'worktree', 'remove', '--force', wt)
    git(REPO, 'worktree', 'prune')

print('')
if FAIL:
    print('new_checker: %d ARM(S) FAILED -- %s' % (len(FAIL), ', '.join(FAIL)))
    sys.exit(1)
print('new_checker: all arms pass')
