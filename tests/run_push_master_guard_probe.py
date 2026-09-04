"""tests/run_push_master_guard_probe.py -- the guard denies pushes to the
stale branch and nothing else.

    python tests/run_push_master_guard_probe.py

WHY THIS EXISTS. `tools/git_push_master_guard.py` tested one line:

    re.search(r'git push.*master', cmd)

`.*` spans the whole command string, so the word anywhere after a push
invocation tripped it. Found 2026-09-04 (Hank) and reproduced three times by
accident rather than theorised: a push to `HEAD:main` denied because this
script's own FILENAME was elsewhere on the line; the command adding the
open-work row denied because the row text quotes the pattern; and the COMMIT
of that row denied because the message did.

TWO PROPERTIES, AND THE SECOND IS THE ONE THAT MATTERS MORE. A guard that
stops over-refusing has obviously improved. A guard that has quietly started
UNDER-refusing has been hollowed out, and nothing on screen would say so --
the push simply succeeds. So the DENY list below is not a formality: every
entry is a shape that must still be blocked after the anchoring change, and
several of them were written specifically because a plausible implementation
of that change would let them through:

  * `git push origin master;echo hi` -- shlex splits on whitespace only, so
    a token-level separator scan sees `master;echo` and compares unequal.
  * `git push --force-with-lease origin master` -- if that option were listed
    as taking a separate value, the parser would eat the REMOTE and never
    read the ref.
  * `git -C /repo push origin master` -- the old regex missed this too; it is
    listed as a deny so the rewrite cannot regress it back to allowed.

Each case is run through the real `targets_master()`, not a copy.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import git_push_master_guard as guard   # noqa: E402

STALE = 'mas' + 'ter'   # assembled so this file's own text cannot trip the
                        # hook it is testing when the filename is on a
                        # command line -- the exact failure being fixed.

DENY = [
    'git push origin ' + STALE,
    'git push origin HEAD:' + STALE,
    'git push -u origin ' + STALE,
    'git push --force origin +HEAD:' + STALE,
    'git push origin refs/heads/' + STALE,
    'git push origin :' + STALE,                       # deleting it is touching it
    'git push origin --delete ' + STALE,
    'git -C /some/repo push origin ' + STALE,          # the old regex missed this
    'git push origin main && git push origin ' + STALE,  # second segment
    'git push origin ' + STALE + ';echo hi',           # separator with no spaces
    'git push --force-with-lease origin ' + STALE,     # must not eat the remote
    'git push origin "' + STALE + '"',                 # quoted ref
    'git push origin HEAD:refs/heads/' + STALE,
]

ALLOW = [
    'git push origin main',
    'git push -q origin main',
    'git push origin HEAD:main',
    # The three real denials that started this, in the shapes they occurred.
    'git push origin HEAD:main && cat tools/git_push_' + STALE + '_guard.py',
    'git push origin main -o "note mentioning ' + STALE + '"',
    'git add docs/' + STALE + '-plan.md && git push origin main',
    # A commit message quoting the pattern, then a clean push.
    'git commit -m "fix git push ' + STALE + ' guard" && git push origin main',
    # Branches merely NAMED like it are different branches.
    'git push origin ' + STALE + '-of-none:main',
    'git push origin archive/' + STALE,
    # Not a push at all.
    'cat tools/git_push_' + STALE + '_guard.py',
    'git log --oneline -5',
    'python tools/sairn_claim.py claim push-' + STALE + '-guard refspec anchoring',
    # The source half is explicitly out of scope -- see the module header.
    'git push origin ' + STALE + ':main',
    '',
]

fails = 0
for cmd in DENY:
    if not guard.targets_master(cmd):
        fails += 1
        print('FAIL  should DENY but allowed:\n        ' + cmd)
for cmd in ALLOW:
    if guard.targets_master(cmd):
        fails += 1
        print('FAIL  should ALLOW but denied:\n        ' + repr(cmd))

total = len(DENY) + len(ALLOW)
print(('FAILED  ' if fails else 'ok  ') +
      'push-' + STALE + '-guard: %d/%d cases, %d failed (%d deny, %d allow)'
      % (total - fails, total, fails, len(DENY), len(ALLOW)))
sys.exit(1 if fails else 0)
