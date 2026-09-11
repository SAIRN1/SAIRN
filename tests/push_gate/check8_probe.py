"""Push-gate check 8: a PROBE fixture commit must not reach origin.

WHY IT EXISTS. On 2026-09-09 `b909dbee "PROBE clean endpoint change"` -- arm 1
of tests/push_gate/check7_probe.py, a one-line comment planted in
api/sb-auth.js -- was the LIVE TIP of origin/main and shipped to production. No
probe published it: they dry-run only. It was stranded on the branch between a
probe's commit and its `git reset --mixed`, and the next ordinary `git push`
from that clone carried it.

WHY IT IS A GATE AND NOT A NOTE. That window used to be rare. It is not any
more: run_all_tests.py runs after every push, and check4_probe was repaired on
2026-09-09 after twelve days of silently skipping -- so both fixture-planting
probes now really run, in four clones, after every push. The window was watched
live the next morning, with HEAD sitting on `PROBE seam violation` for minutes.

THIS PROBE HOLDS BOTH DIRECTIONS AND THE EXEMPTION. A gate whose findings are
clean has, by construction, never denied anything, so nobody knows whether it
can -- the same standard check7_probe was written to.

Run: python tests/push_gate/check8_probe.py
"""
import atexit
import json
import os
import subprocess
import sys
import tempfile

MAIN = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()

# ── THE FIXTURE IS PLANTED IN A THROWAWAY WORKTREE (2026-09-11) ────────────
# THIS FILE WAS NOT ON THE LIST AND HAD THE DEFECT IT TESTS.
# `docs/2026-09-10-run-all-tests-hook-PAUSED.md` names check4_probe.py and
# check7_probe.py as the two probes that commit fixtures onto the working
# branch. There are THREE: this one plants `PROBE check8 planted fixture` the
# same way, on the same branch, and it is the probe for the gate that exists
# because a stranded PROBE commit shipped to production.
#
# Found by grepping every `tests/**/*.py` that runs `git commit` rather than
# trusting the document's list -- CLAUDE.md's standing lesson, that a fix
# verified on the copies somebody wrote down is not verified on the ones they
# did not. The other two hits (tests/claims/run_push_verify_probe.py and
# tests/push_gate/redaction_base_probe.py) build their own throwaway repos and
# were already safe.
#
# A detached worktree has no branch tip for a lost `reset` race to strand a
# commit on. The pre-push hook still fires from it -- `core.hooksPath` is
# `.githooks` and worktrees share the common git dir -- which this probe
# depends on absolutely, since its entire subject is what that hook decides.
WT = os.path.join(tempfile.gettempdir(), 'check8-probe-%d' % os.getpid())
_add = subprocess.run(['git', '-C', MAIN, 'worktree', 'add', '-q', '--detach',
                       WT, 'HEAD'], capture_output=True, text=True)
if _add.returncode != 0:
    print('SKIPPED: could not create the throwaway worktree this probe needs, so')
    print('nothing about check 8 was verified: %s' % (_add.stderr or '').strip()[:200])
    sys.exit(3)


@atexit.register
def _remove_worktree():
    subprocess.run(['git', '-C', MAIN, 'worktree', 'remove', '--force', WT],
                   capture_output=True)
    subprocess.run(['git', '-C', MAIN, 'worktree', 'prune'], capture_output=True)


REPO = WT
# THE HOOK IS LOADED FROM THE CLONE, NOT THE WORKTREE, and that is deliberate:
# the worktree is a checkout of HEAD, so a hook edit that is not yet committed
# would be invisible there and the probe would test the committed gate while
# reporting on the working one. Same reasoning redaction_base_probe.py states
# for its own clone.
HOOK = os.path.join(MAIN, 'tools', 'sairn_push_gate_hook.py')
FIXTURE = 'zz_check8_fixture.txt'

# Deliberately WITHOUT SAIRN_PROBE_PUSH: this probe's whole job is to see check
# 8 deny, so it must not declare itself the way check4/check7 do. The arms that
# test the exemption set it explicitly, one call at a time.
BARE_ENV = {k: v for k, v in os.environ.items() if k != 'SAIRN_PROBE_PUSH'}


def run(*a, **k):
    return subprocess.run(list(a), cwd=REPO, capture_output=True, text=True,
                          env=BARE_ENV, **k)


def clean_tree():
    return run('git', 'status', '--porcelain').stdout.strip()


# ── THE CLEAN-TREE PRECONDITION IS GONE -- SEE THE WORKTREE BLOCK ABOVE ────
# It was exit 3 for SKIPPED, the convention its two siblings use, and it
# existed because `git add` in the clone could sweep uncommitted work into the
# probe's commit. A worktree built from HEAD never contains the clone's
# uncommitted files. The guard had been skipping this probe -- the only proof
# check 8 can deny anything -- on every run in any clone with a modified
# tracked file, which is most of them most of the time.
MAIN_TREE_BEFORE = subprocess.run(
    ['git', '-C', MAIN, 'status', '--porcelain'],
    capture_output=True, text=True).stdout
MAIN_HEAD_BEFORE = subprocess.run(
    ['git', '-C', MAIN, 'rev-parse', 'HEAD'],
    capture_output=True, text=True).stdout.strip()

start = run('git', 'rev-parse', 'HEAD').stdout.strip()
START_UNTRACKED = {l for l in clean_tree().split('\n') if l.startswith('??')}
R = {}


def dry_push(probe_env=False):
    """A --dry-run push, which publishes nothing but still runs the pre-push hook."""
    env = dict(BARE_ENV)
    if probe_env:
        env['SAIRN_PROBE_PUSH'] = '1'
    r = subprocess.run(['git', 'push', '--dry-run', 'origin', 'HEAD:main'],
                       cwd=REPO, capture_output=True, text=True, env=env)
    err = (r.stderr or '') + (r.stdout or '')
    return {
        'exit': r.returncode,
        'blocked_by_check8': 'PROBE fixture commit' in err,
        'names_the_commit': R.get('sha', 'zzzz')[:8] in err,
        'err': err,
    }


def pretooluse(cmd):
    """Drive the hook the way Claude Code does: a JSON payload on stdin."""
    r = subprocess.run([sys.executable, HOOK], cwd=REPO, capture_output=True,
                       text=True, env=BARE_ENV,
                       input=json.dumps({'tool_input': {'command': cmd}}))
    try:
        out = json.loads(r.stdout) if r.stdout.strip() else {}
    except ValueError:
        out = {}
    hook = out.get('hookSpecificOutput', {}) or {}
    return {
        'decision': hook.get('permissionDecision'),
        'reason': hook.get('permissionDecisionReason', '') or '',
    }


try:
    # ── ARM 1: a NORMAL commit is not blocked by check 8 ────────────────────
    # The control comes FIRST, so a check-8 deny on the planted arm cannot be
    # confused with the gate denying everything for some unrelated reason.
    open(os.path.join(REPO, FIXTURE), 'w').write('check 8 fixture\n')
    run('git', 'add', FIXTURE)
    run('git', 'commit', '-q', '-m', 'test(check8): an ordinary commit subject')
    R['normal'] = dry_push()
    # ── `HEAD:main`, NOT `main`, SINCE THE WORKTREE CHANGE (2026-09-11) ─────
    # pushed_tip() resolves the tip from the COMMAND TEXT, and in a detached
    # worktree `main` is the CLONE's branch -- not this checkout's HEAD, which
    # is where the planted commit lives. Driving `git push origin main` here
    # diffs a range with no fixture in it, so the planted arm reported NOT
    # DENIED and the control arm reported ALLOWED for a reason that had nothing
    # to do with check 8. The control was passing for the wrong reason, which
    # is the more dangerous half.
    #
    # `HEAD:main` exercises the same code path -- pushed_tip() returns 'HEAD' --
    # and actually points at the commit under test. The refspec form is
    # incidental to what check 8 reads, which is the commit SUBJECT.
    R['normal_pretooluse'] = pretooluse('git push origin HEAD:main')
    run('git', 'reset', '--mixed', '-q', start)

    # ── ARM 2: a PROBE-subject commit IS blocked ────────────────────────────
    run('git', 'add', FIXTURE)
    run('git', 'commit', '-q', '-m', 'PROBE check8 planted fixture')
    R['sha'] = run('git', 'rev-parse', 'HEAD').stdout.strip()
    R['planted'] = dry_push()
    R['planted_pretooluse'] = pretooluse('git push origin HEAD:main')

    # ── ARM 3: the two exemptions, on the SAME commit ───────────────────────
    # Same planted commit, so any difference is the exemption and nothing else.
    R['declared'] = dry_push(probe_env=True)
    R['dry_run_pretooluse'] = pretooluse('git push --dry-run origin HEAD:main')
    R['dash_n_pretooluse'] = pretooluse('git push -n origin HEAD:main')
    run('git', 'reset', '--mixed', '-q', start)
finally:
    _f = os.path.join(REPO, FIXTURE)
    if os.path.exists(_f):
        os.remove(_f)
    run('git', 'reset', '--mixed', '-q', start)

R['restored'] = (
    not [l for l in clean_tree().split('\n') if l.strip() and not l.startswith('??')]
    and {l for l in clean_tree().split('\n') if l.startswith('??')} == START_UNTRACKED)
R['head_restored'] = (run('git', 'rev-parse', 'HEAD').stdout.strip() == start)

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


print('push-gate check 8 -- a PROBE fixture commit must not reach origin\n')

n = R['normal']
check('an ORDINARY commit is not blocked by check 8', not n['blocked_by_check8'],
      str(n['err'])[-200:])
check('...and not by the PreToolUse path either',
      R['normal_pretooluse']['decision'] != 'deny'
      or 'PROBE fixture commit' not in R['normal_pretooluse']['reason'],
      str(R['normal_pretooluse'])[:200])

p = R['planted']
check('a PROBE-subject commit IS blocked', p['blocked_by_check8'], str(p['err'])[-300:])
check('...and the refusal NAMES the commit', p['names_the_commit'], str(p['err'])[-300:])
check('...and the push exits non-zero', p['exit'] != 0, str(p['exit']))
check('...and the PreToolUse path denies it too',
      R['planted_pretooluse']['decision'] == 'deny'
      and 'PROBE fixture commit' in R['planted_pretooluse']['reason'],
      str(R['planted_pretooluse'])[:300])

# THE EXEMPTIONS. A dry run publishes nothing, so it cannot strand anything --
# and check4_probe and check7_probe both have arms whose whole point is that a
# CLEAN change is allowed through. If check 8 denied those, the arms would stop
# short of what they name.
d = R['declared']
check('SAIRN_PROBE_PUSH=1 exempts the SAME commit in pre-push mode',
      not d['blocked_by_check8'], str(d['err'])[-200:])
check('`git push --dry-run` is exempt in PreToolUse mode',
      'PROBE fixture commit' not in R['dry_run_pretooluse']['reason'],
      str(R['dry_run_pretooluse'])[:200])
check('`git push -n` is exempt too -- the short form is the same thing',
      'PROBE fixture commit' not in R['dash_n_pretooluse']['reason'],
      str(R['dash_n_pretooluse'])[:200])

check('the repo was restored', R['restored'])
check('...and HEAD is back where it started', R['head_restored'])
# ── AND THE CLONE ITSELF WAS NEVER TOUCHED (2026-09-11) ────────────────────
# The two above are about the WORKTREE. This is the claim check 8 exists
# because somebody violated -- a PROBE commit surviving in a real clone -- and
# it is the one this probe was quietly not making about itself.
check('and the CLONE was never touched -- no commit, no modified file',
      subprocess.run(['git', '-C', MAIN, 'status', '--porcelain'],
                     capture_output=True, text=True).stdout == MAIN_TREE_BEFORE
      and subprocess.run(['git', '-C', MAIN, 'rev-parse', 'HEAD'],
                         capture_output=True, text=True).stdout.strip()
      == MAIN_HEAD_BEFORE)

print('\n%s  check8_probe: %d failed' % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
