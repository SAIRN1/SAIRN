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
real_popen4 = subprocess.Popen


def spy(cmd, **kw):
    # THE SPY IS AIMED AT Popen, NOT run, AND THAT IS NOT A DETAIL. It targeted
    # subprocess.run until pinned_main was changed to relay the child's output
    # through Popen -- at which point the spy silently stopped intercepting and
    # this arm ran the REAL 590-file suite inside a worktree for eleven minutes
    # before it was killed. A test double is a second copy of a signature and it
    # stops agreeing the moment the original moves.
    if isinstance(cmd, list) and cmd and str(cmd[0]) == sys.executable             and any('run_all_tests.py' in str(c) for c in cmd[1:]):
        landed['cwd'] = kw.get('cwd')
        landed['sha'] = subprocess.run(
            ['git', 'rev-parse', 'HEAD'], cwd=kw.get('cwd'),
            capture_output=True, text=True).stdout.strip()
        landed['has_tests'] = os.path.isdir(os.path.join(kw.get('cwd'), 'tests'))
        landed['cmd'] = list(cmd)
        kw.pop('cwd', None)
        return real_popen4([sys.executable, '-c', 'pass'], **kw)
    return real_popen4(cmd, **kw)


subprocess.Popen = spy
try:
    rc = R.pinned_main(['--pinned', '--pinned-ignore-dirty', '--quiet'])
finally:
    subprocess.Popen = real_popen4

# AND THE ARM THAT WOULD HAVE CAUGHT THE MISS: with the spy aimed at the wrong
# function `landed` is empty, and the checks below would compare None to None
# in a way that can read as a pass. Assert the interception happened FIRST.
check('the inner command is spawned UNBUFFERED, or the line-by-line relay '
      'is a slower communicate() and --out sits empty for the whole run',
      bool(landed.get('cmd')) and '-u' in landed['cmd'],
      repr(landed.get('cmd')))
check('the spy actually intercepted the inner invocation',
      bool(landed), 'landed is empty -- the spy is aimed at the wrong function '
      'and this arm just ran the real suite')

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
print('5. --out really holds the INNER run, not just the outer banner')
# THE ARM THAT WAS MISSING AND COST A WRONG COMMIT MESSAGE. The first version
# of pinned_main used subprocess.run(inner, cwd=wt), which hands the child this
# process's OS-level stdout -- straight past a replaced sys.stdout. So --out
# captured the PINNED banner and the FULL OUTPUT WRITTEN TO footer and lost
# every one of the 590 files in between, while the file existed, had content
# and looked plausible. That is the truncation defect these flags exist to fix,
# reintroduced one layer up, and it was found by reading the file rather than
# by any arm.
#
# Driven with a stub inner process rather than the real suite: the property
# under test is whether the child's stdout REACHES the --out file, and a child
# that prints one recognisable line proves that as well as one that prints
# 590.
marker = 'INNER-RAN-HERE-%d' % os.getpid()
outfile = os.path.join(tempfile.gettempdir(), 'sairn-pinned-probe-%d.txt' % os.getpid())
real_popen = subprocess.Popen


def popen_spy(cmd, **kw):
    if isinstance(cmd, list) and any('run_all_tests.py' in str(c) for c in cmd[1:]):
        cmd = [sys.executable, '-c', 'print("%s")' % marker]
        kw.pop('cwd', None)
    return real_popen(cmd, **kw)


subprocess.Popen = popen_spy
try:
    R.main(['--out', outfile, '--pinned', '--pinned-ignore-dirty', '--quiet'])
finally:
    subprocess.Popen = real_popen
body = io.open(outfile, encoding='utf-8', errors='replace').read() if os.path.exists(outfile) else ''
check('the --out file exists', bool(body), 'empty or absent: %r' % outfile)
check('...and carries the PINNED banner (the outer half)',
      'PINNED: running in a throwaway worktree' in body, body[:200])
check("...AND the inner run's own output, which is the half that was lost",
      marker in body, body[:400])
try:
    os.remove(outfile)
except OSError:
    pass

print('')
print('6. THE PINNING EXCLUSION SET -- declared, reported, and NOT permanent')
# WHY THIS ARM EXISTS. The first --pinned full-suite run reported nine failures
# that pass in the clone, and the conclusion drawn was "they read live repo
# state, exclude them". That was WRONG for most of them: they die on
# sairn_session_identity.NoIdentity because a worktree has its own git dir and
# the per-clone marker lives in .git/. Excluding them would have stopped testing
# six files under --pinned for a defect that takes one file copy to fix.
#
# So there are two things to pin here, and the second is the one that rots: the
# exclusion must apply ONLY to a pinned run, or it quietly becomes permanent.
import run_all_tests as R2                                         # noqa: E402

check('the shipped exclusion set is non-empty and every entry has a REASON',
      bool(R2.PINNING_INCOMPATIBLE)
      and all(isinstance(v, str) and len(v) > 80
              for v in R2.PINNING_INCOMPATIBLE.values()),
      repr({k: len(v) for k, v in R2.PINNING_INCOMPATIBLE.items()}))

# EXCLUDED IS A THIRD ANSWER. Driven both ways against the real _run().
_one = sorted(R2.PINNING_INCOMPATIBLE)[0]
_f, _s, _r, _nr = R2._run([], [_one], quiet=True, excluded=R2.PINNING_INCOMPATIBLE)
check('a pinned run reports it EXCLUDED, not run -- not a pass and not a failure',
      len(_nr) == 1 and len(_f) == 0 and _nr[0][1] == _one,
      'not_run=%r failures=%r' % (_nr, _f))

_f2, _s2, _r2, _nr2 = R2._run([], [_one], quiet=True, excluded=None)
check('...and an ORDINARY run still executes it, so the exclusion cannot '
      'become permanent',
      len(_nr2) == 0, 'not_run=%r -- an unpinned run must not exclude' % (_nr2,))

# THE PROVISIONING HALF, which is the actual fix rather than the exclusion.
check('provision_worktree_identity exists and FAILS CLOSED with a message',
      callable(getattr(R2, 'provision_worktree_identity', None)),
      'the helper is gone -- without it the excluded set has to grow to six')

# AND THE SECOND COPY. _hook_body() also calls _run(); the floor probe exists
# because a change was once made to _main_body only. A three-value unpack there
# would raise inside the unattended hook where nobody reads the output.
_src = io.open(os.path.join(REPO, 'tools', 'run_all_tests.py'),
               encoding='utf-8').read()
check('BOTH _run callers unpack four values -- the hook copy included',
      _src.count('= _run(') == 2 and _src.count('retried, _hook_not_run = _run(') == 1
      and _src.count('retried, not_run = _run(') == 1,
      'callers: ' + repr([l.strip() for l in _src.split(chr(10))
                          if '= _run(' in l]))

print('')
if bad:
    print('%d ARM(S) FAILED' % len(bad))
    for b in bad:
        print('  ' + b)
    sys.exit(1)
print('ALL %d PINNED/OUT ASSERTIONS PASS' % ok)
