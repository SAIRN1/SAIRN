"""Do `--pinned` and `--out` in tools/run_all_tests.py fail CLOSED, and does a
pinned run actually execute somewhere the clone cannot reach?

WHY THIS EXISTS. Both flags were added on 2026-09-25 because a 2h11m run of
that file produced nothing usable, for two independent reasons:

  1. it was launched through `| tail -45`, so the footer said
     `59 FAILING TEST FILE(S)` and forty-two names survived -- SEVENTEEN were
     gone, and a truncated list is indistinguishable from a complete one;
  2. `discover()` snapshots the file LIST once but `_run()` executes each file
     when it reaches it, so CONTENTS are read live. Over those two hours the
     tree took three commits, a rebase across twenty-four upstream commits and
     a `git checkout`. The result was not a stale snapshot, it was a smear, and
     no failure in it could be attributed to a commit.

THE RISK THE FLAGS THEMSELVES CREATE is the reason this probe exists rather
than a line in a commit message. A `--pinned` that silently fell back to the
live checkout would be WORSE than no flag: the caller would have evidence the
run was pinned when it was not, which is the fabricated-assurance shape this
platform keeps paying for. Same for `--out`: a run that could not open its file
and carried on would leave the caller believing a complete copy exists.

So every arm below drives a REFUSAL and checks it is exit 2 -- "could not run"
as a third state (PR 1.11) -- and the last arm drives the HAPPY path far enough
to prove the worktree is real, is at the requested commit, and is not the
clone.

NO ARM RUNS THE FULL SUITE. That takes hours and would make this probe
unrunnable in practice, which is how a probe stops being run at all. The happy
path is proved by driving `pinned_main` with an inner command that reports
where it landed, not by letting it run 590 files.
"""
import io
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RUNNER = os.path.join(REPO, 'tools', 'run_all_tests.py')

sys.path.insert(0, os.path.join(REPO, 'tools'))

ok = 0
bad = []


def check(label, cond, detail=''):
    global ok
    if cond:
        ok += 1
        print('  ok   ' + label)
    else:
        bad.append(label + (' -- ' + detail if detail else ''))
        print('  FAIL ' + label + (('\n       ' + detail) if detail else ''))


def run(args, cwd=REPO):
    r = subprocess.run([sys.executable, RUNNER] + args, cwd=cwd,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('run_all_tests --pinned / --out: do they fail CLOSED?\n')

print('1. --out refuses rather than running without its file')
rc, out = run(['--out', os.path.join(REPO, 'no', 'such', 'dir', 'x.txt'), '--pinned'])
check('an unopenable --out path exits 2, not 0 and not 1',
      rc == 2, 'exit was %d' % rc)
check('...and says COULD NOT RUN rather than naming a test failure',
      'COULD NOT RUN' in out, out[:200])
# THE ARM THAT MATTERS: it must not have run the suite anyway. A runner that
# carried on would print its own verdict line, and the caller would believe a
# complete copy of that verdict was on disk.
check('...and the suite did NOT run behind the refusal',
      'EXIT 0' not in out and 'EXIT 1' not in out and 'RAN:' not in out,
      out[:200])

print('\n2. --rev refuses a commit-ish this clone cannot resolve')
rc, out = run(['--pinned', '--rev', 'deadbeefdeadbeefdeadbeefdeadbeefdeadbeef',
               '--pinned-ignore-dirty'])
check('an unresolvable --rev exits 2', rc == 2, 'exit was %d' % rc)
check('...and names the rev rather than failing anonymously',
      'does not resolve' in out, out[:200])
check('...and no worktree was left behind for it',
      'worktree was left behind' not in out, out[:200])

print('\n3. a DIRTY tree refuses, because --pinned tests a COMMIT')
# THE HONESTY ARM. --pinned cannot see uncommitted work, so a green pinned run
# on a dirty tree would be a true sentence about something the caller did not
# ask about -- and would look exactly like one that covered their change.
scratch = os.path.join(REPO, 'zz_pinned_probe_scratch.txt')
created = False
try:
    if not os.path.exists(scratch):
        io.open(scratch, 'w', encoding='utf-8').write('probe scratch\n')
        created = True
    rc, out = run(['--pinned'])
    check('an uncommitted path makes --pinned exit 2', rc == 2, 'exit was %d' % rc)
    check('...and the refusal NAMES the untested path rather than just counting',
          'zz_pinned_probe_scratch.txt' in out, out[:400])
    check('...and says the pinned run would not have tested it',
          'NOT be tested' in out and 'would look exactly like' in out, out[:400])
    # AND THE OTHER DIRECTION, or the arm above only proves it refuses always.
    rc2, out2 = run(['--pinned', '--pinned-ignore-dirty', '--rev',
                     'deadbeefdeadbeefdeadbeefdeadbeefdeadbeef'])
    check('--pinned-ignore-dirty really does get PAST the dirty check',
          'uncommitted' not in out2, out2[:300])
finally:
    if created:
        try:
            os.remove(scratch)
        except OSError:
            pass

print('\n4. the happy path really lands in a worktree, at the right commit,')
print('   and NOT in the clone')
# Driven through the module rather than the CLI so the inner command can be one
# that reports where it landed instead of running 590 files for two hours. The
# thing under test is pinned_main's worktree setup and teardown, and that is
# exactly what this exercises.
import run_all_tests as R                                          # noqa: E402

head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO, capture_output=True,
                      text=True).stdout.strip()
landed = {}
real_run = subprocess.run


def spy(cmd, **kw):
    # The inner invocation is the one whose cwd is the worktree.
    if isinstance(cmd, list) and cmd and str(cmd[0]) == sys.executable \
            and any('run_all_tests.py' in str(c) for c in cmd[1:]):
        landed['cwd'] = kw.get('cwd')
        landed['sha'] = subprocess.run(
            ['git', 'rev-parse', 'HEAD'], cwd=kw.get('cwd'),
            capture_output=True, text=True).stdout.strip()
        landed['has_tests'] = os.path.isdir(os.path.join(kw.get('cwd'), 'tests'))

        class _R(object):
            returncode = 0
        return _R()
    return real_run(cmd, **kw)


subprocess.run = spy
try:
    rc = R.pinned_main(['--pinned', '--pinned-ignore-dirty', '--quiet'])
finally:
    subprocess.run = real_run

check('pinned_main returned the inner run\'s code', rc == 0, 'got %r' % rc)
check('the suite ran with cwd set to a worktree, NOT the clone',
      landed.get('cwd') and os.path.abspath(landed['cwd']) != os.path.abspath(REPO),
      'cwd was %r' % landed.get('cwd'))
check('...and that worktree is a real checkout with a tests/ directory',
      landed.get('has_tests') is True, repr(landed.get('has_tests')))
check('...pinned to the requested commit',
      landed.get('sha') == head, '%r != %r' % (landed.get('sha'), head))
# TEARDOWN IS PART OF THE CONTRACT: a probe that leaves a worktree behind every
# run is a disk leak and a stale `git worktree list` entry somebody else has to
# explain.
check('...and the worktree was removed afterwards',
      landed.get('cwd') and not os.path.exists(landed['cwd']),
      'still present: %r' % landed.get('cwd'))

print('')
if bad:
    print('%d ARM(S) FAILED' % len(bad))
    for b in bad:
        print('  ' + b)
    sys.exit(1)
print('ALL %d PINNED/OUT ASSERTIONS PASS' % ok)
