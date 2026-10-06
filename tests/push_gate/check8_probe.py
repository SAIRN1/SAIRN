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
import shutil
import subprocess
import sys
import tempfile

MAIN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── THIS PROBE USED TO LEAVE THE CLONE'S .git/config CORRUPTED, AND THE
#    CAUSE IS FIXED BELOW -- THIS BLOCK IS NOW A NET, NOT THE MECHANISM ───
# MEASURED, THREE TIMES, DETERMINISTICALLY. After a run of this file that is
# killed by a per-suite ceiling, `.git/config` carries
#
#     [core]  bare = true
#     [user]  email = fx@example.invalid   name = fx
#
# and from that moment EVERY git command in the clone fails with
# `fatal: this operation must be run in a work tree`. It was first seen during
# a whole-tree run on 2026-10-06, attributed to this file by digesting
# .git/config after every suite, and reproduced on demand with
# `timeout 240 python tests/push_gate/check8_probe.py`.
#
# PINNED TO ONE STEP, NOT TO ONE COMMAND, AND THE DIFFERENCE IS STATED.
# The per-step reassertion below labels the step the drift is seen after, and
# it reports the same one every time:
#
#     dry_push(probe_env=False)
#
# -- the FIRST real `git push --dry-run` from the worktree, which is the one
# whose outgoing range is READABLE, because the fixture sits on top of
# FETCH_HEAD. So the writer is inside the .githooks/pre-push chain, on a path
# reached only when the range resolves.
#
# THAT ALSO EXPLAINS WHY SIX ISOLATIONS CAME BACK CLEAN, and the explanation
# matters more than the list: every manual reproduction hit "the outgoing
# range ... could not be read" -- origin/main moves hourly here -- so the gate
# chain exited BEFORE the path that writes. A negative result from an
# isolation that never reached the code is not evidence about that code. The
# six were: copy_exactly_gate --fixtures; copy_exactly_gate --range from a
# worktree (its _fx_repo() is the ONLY place in this repo that writes
# `fx@example.invalid`); each of the four pre-push gates driven separately
# with a crafted refs line; sairn_push_gate_hook in PreToolUse mode; a real
# dry-run push from a worktree; and `git worktree add` alone.
#
# NOT CHASED FURTHER, DELIBERATELY. The remaining suspects are inside
# tools/sairn_push_gate_hook.py's check-12 path, which builds a
# `sairn-gate-base-*` worktree and runs GENERATORS FROM THE BASE COMMIT --
# i.e. older copies of tools, with cwd inside a worktree, where a `git config`
# write lands in the SHARED config. That is a plausible mechanism and it is
# NOT a measurement; it is recorded as the next place to look, by the session
# that owns that gate.
#
# THIS WAS CONTAINMENT. THE ROOT CAUSE IS FIXED further down -- the fixture
# is a CLONE now, not a linked worktree, so nothing inside it shares this
# clone's config. The snapshot/restore below is kept as a belt-and-braces
# net and as the repair path for a clone corrupted by the OLD code:
# The config bytes are copied before anything runs, restored on every ordinary
# exit, and left as a RESTORABLE BACKUP for the one path a process cannot
# defend against -- being killed. `--check-residue` finds that backup, says
# the clone may be corrupt, and restores it.
# ── RESOLVED WITH `git rev-parse --git-common-dir`, NOT `MAIN/.git` ───────
# `MAIN/.git` is a DIRECTORY in a clone and a FILE in a linked worktree, so
# the hardcoded join found nothing when this probe was driven from a worktree
# and the whole file SKIPPED with "config could not be read". That skip was
# correct -- it refused rather than guessing -- but it meant the probe could
# not be developed anywhere safe. `--git-common-dir` answers both cases, and
# it answers with the SHARED dir, which is the one a worktree write would
# reach.
def _common_git_dir():
    r = subprocess.run(['git', '-C', MAIN, 'rev-parse', '--git-common-dir'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if r.returncode != 0:
        return None
    d = r.stdout.strip()
    return d if os.path.isabs(d) else os.path.normpath(os.path.join(MAIN, d))


_GITDIR = _common_git_dir()
CONFIG = os.path.join(_GITDIR, 'config') if _GITDIR else os.path.join(MAIN, '.git', 'config')
CONFIG_BACKUP = CONFIG + '.check8-probe-backup'


def _read_config():
    try:
        with open(CONFIG, 'rb') as fh:
            return fh.read()
    except OSError:
        return None


def check_config_residue(restore=False):
    """-> exit code. Did a killed run leave this clone's config corrupted?"""
    if not os.path.exists(CONFIG_BACKUP):
        print('no backup: no run of this probe died before restoring .git/config.')
        return 0
    try:
        with open(CONFIG_BACKUP, 'rb') as fh:
            saved = fh.read()
    except OSError as e:
        print('COULD NOT READ the backup (%s). That is not a clean result.' % e)
        return 2
    now = _read_config()
    if now is None:
        print('COULD NOT READ .git/config. That is not a clean result.')
        return 2
    if now == saved:
        print('a run died before removing its backup, but .git/config is '
              'byte-identical to it -- nothing to repair.')
        if restore:
            os.remove(CONFIG_BACKUP)
        return 0
    print('A RUN OF THIS PROBE DIED AND .git/config DIFFERS FROM ITS BACKUP.')
    try:
        txt = now.decode('utf-8', 'replace')
        for key in ('bare = true', 'fx@example.invalid'):
            if key in txt:
                print('    present now and NOT in the backup: %s' % key)
    except Exception:
        pass
    if restore:
        with open(CONFIG, 'wb') as fh:
            fh.write(saved)
        os.remove(CONFIG_BACKUP)
        print('    RESTORED from %s' % os.path.relpath(CONFIG_BACKUP, MAIN))
        return 0
    print('    Restore it with:  python %s --restore-config'
          % os.path.relpath(os.path.abspath(__file__), MAIN))
    return 1


if '--check-residue' in sys.argv or '--restore-config' in sys.argv:
    sys.exit(check_config_residue(restore='--restore-config' in sys.argv))

_CONFIG_BEFORE = _read_config()
if _CONFIG_BEFORE is None:
    print('SKIPPED: .git/config could not be read, so this probe cannot '
          'guarantee it will hand the clone back the way it found it. Nothing '
          'about check 8 was verified.')
    sys.exit(3)
with open(CONFIG_BACKUP, 'wb') as _fh:
    _fh.write(_CONFIG_BEFORE)


_CONFIG_DRIFTED = []


def _reassert_config(step='(exit)'):
    """Put the config back NOW, and remember that it had moved.

    Called after every push-shaped step rather than only at exit. The write
    happens somewhere inside one of those steps, and between it and process
    exit this clone is BARE -- every `git` command in it, including another
    session's, fails outright. Restoring immediately bounds that window to one
    step instead of the whole run. The drift is recorded, not swallowed: the
    arm at the end still fails, because a config this probe had to put back is
    a config it should never have moved.
    """
    now = _read_config()
    if now == _CONFIG_BEFORE:
        return
    _CONFIG_DRIFTED.append('%s (%s bytes)' % (step, len(now) if now is not None else 'unreadable'))
    try:
        with open(CONFIG, 'wb') as fh:
            fh.write(_CONFIG_BEFORE)
    except OSError:
        pass


@atexit.register
def _restore_config():
    """Hand the clone back byte-identical, on every exit this process controls."""
    _reassert_config()
    try:
        if os.path.exists(CONFIG_BACKUP):
            os.remove(CONFIG_BACKUP)
    except OSError:
        pass

# ── THE FIXTURE IS PLANTED IN A THROWAWAY CLONE (2026-10-06) ──────────────
# IT WAS A LINKED WORKTREE UNTIL TODAY, AND THAT WAS THE ROOT CAUSE OF THE
# CLONE CORRUPTION THIS FILE CARRIED. A linked worktree SHARES `.git/config`
# with the clone that owns it. So a `git config` write made by anything
# running with cwd inside the worktree -- a gate, a gate's fixture, a tool run
# from a base commit -- lands in the REAL clone's config, and this probe's
# first dry-run push was reliably leaving `core.bare = true` behind. The class
# is cody's `SHARED_CONFIG_WRITE_FROM_WORKTREE`.
#
# Containment (snapshot, reassert, restore, backup) was the previous answer and
# it is kept below as a NET. It is no longer the mechanism: a clone has its own
# `.git/config`, so the write cannot reach this clone at all -- regardless of
# who makes it, and regardless of whether this process lives long enough to put
# anything back. THAT is the difference between containing and fixing, and it
# is why the config arm at the end can now be green rather than failing on
# purpose.
#
# `git clone --local` HARDLINKS the object store (68 MiB pack here), so this
# costs no measurable time and no disk. The clone is removed with
# `shutil.rmtree`, which also ends this probe's contribution to the leaked
# `%TEMP%` worktrees -- there is no worktree registration left behind to prune.
#
# ── THE ORIGINAL NOTE, KEPT, BECAUSE ITS REASON STILL HOLDS ────────────────
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
#
# ── AND IT IS BUILT ON THE FETCHED REMOTE TIP, NOT ON LOCAL HEAD (2026-09-16) ─
# This said `HEAD`, and in a five-clone repo local HEAD is behind origin/main
# most of the time. The gate then refuses with "the outgoing range
# <remote>..<local> could not be read" -- CORRECTLY, since the remote tip is not
# an object this clone has yet -- and that refusal lands before check 8 is ever
# reached. Measured 2026-09-16: "a PROBE-subject commit IS blocked" failed with
# a bare "failed to push some refs", so the arm could not tell check 8 blocking
# the push from anything else blocking it, which is the whole thing it exists
# to establish.
_fetch = subprocess.run(['git', '-C', MAIN, 'fetch', '--quiet', 'origin', 'main'],
                        capture_output=True, text=True, encoding='utf-8', errors='replace')
if _fetch.returncode != 0:
    print('SKIPPED: could not fetch origin/main, so the fixture below could not be')
    print('built on the tip the gate compares against, and nothing about check 8')
    print('was verified: %s' % (_fetch.stderr or '').strip()[:200])
    sys.exit(3)
BASE = subprocess.run(['git', '-C', MAIN, 'rev-parse', 'FETCH_HEAD'],
                      capture_output=True, text=True, encoding='utf-8',
                      errors='replace').stdout.strip()
WT = os.path.join(tempfile.gettempdir(), 'check8-probe-%d' % os.getpid())


def _setup_clone():
    """-> None on success, or a reason string. Never half-builds silently."""
    r = subprocess.run(['git', 'clone', '--quiet', '--local', '--no-checkout',
                        MAIN, WT], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        return 'clone failed: %s' % (r.stderr or '').strip()[:200]
    # The real remote, so `push --dry-run origin HEAD:main` exercises exactly
    # the path it did before. A clone of a local path points origin at that
    # path, and pushing there would test a different thing.
    url = subprocess.run(['git', '-C', MAIN, 'remote', 'get-url', 'origin'],
                         capture_output=True, text=True, encoding='utf-8',
                         errors='replace').stdout.strip()
    if not url:
        return 'could not read origin url from %s' % MAIN
    for args in (['remote', 'set-url', 'origin', url],
                 # hooksPath is CONFIG, not a tracked file, so a clone does not
                 # inherit it -- and without it the pre-push hook never fires
                 # and this probe would report "not blocked" about a gate that
                 # was never asked. Set explicitly, and asserted below.
                 ['config', 'core.hooksPath', '.githooks'],
                 ['config', 'user.email', 'check8-probe@example.invalid'],
                 ['config', 'user.name', 'check8-probe'],
                 ['checkout', '--detach', '--quiet', BASE]):
        rr = subprocess.run(['git', '-C', WT] + args, capture_output=True,
                            text=True, encoding='utf-8', errors='replace')
        if rr.returncode != 0:
            return '%s failed: %s' % (' '.join(args[:2]), (rr.stderr or '').strip()[:160])
    # origin/main inside the clone must be the tip the gate compares against.
    subprocess.run(['git', '-C', WT, 'fetch', '--quiet', 'origin', 'main'],
                   capture_output=True)
    hp = os.path.join(WT, '.githooks', 'pre-push')
    if not os.path.isfile(hp):
        return 'the clone has no .githooks/pre-push, so the gate could not fire'
    return None


_why = _setup_clone()
if _why:
    shutil.rmtree(WT, ignore_errors=True)
    print('SKIPPED: could not create the throwaway clone this probe needs, so')
    print('nothing about check 8 was verified: %s' % _why)
    sys.exit(3)


def _rmtree_loud(path):
    """Remove it, and SAY SO if it survives.

    `shutil.rmtree(..., ignore_errors=True)` was the first version and it
    leaked a 68 MiB hardlinked clone per run, silently: on Windows a cloned
    object store carries READ-ONLY pack files and rmtree cannot unlink them,
    so ignore_errors swallowed the failure. Measured on the first three runs
    of this fix -- three clone directories left in %TEMP% while the probe
    reported ok. A cleanup that cannot fail loudly is the same defect class
    this probe exists for, one layer out.
    """
    def _chmod_retry(func, p, _exc):
        try:
            os.chmod(p, 0o700)
            func(p)
        except OSError:
            pass
    shutil.rmtree(path, onerror=_chmod_retry)
    if os.path.isdir(path):
        print('WARNING: could not remove the throwaway clone at %s -- it is '
              "hardlinked to this repo's object store and will sit in TEMP "
              'until somebody deletes it.' % path)
        return False
    return True


@atexit.register
def _remove_clone():
    _rmtree_loud(WT)


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
    return subprocess.run(list(a), cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace',
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
    capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
MAIN_HEAD_BEFORE = subprocess.run(
    ['git', '-C', MAIN, 'rev-parse', 'HEAD'],
    capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()

start = run('git', 'rev-parse', 'HEAD').stdout.strip()
START_UNTRACKED = {l for l in clean_tree().split('\n') if l.startswith('??')}
R = {}


# The gate's own words when it cannot compute what is being pushed. Matched
# rather than inferred from the exit code, because "could not tell" and "no" are
# different answers and this probe must not read one as the other.
RANGE_UNREADABLE = 'could not be read'


def dry_push(probe_env=False):
    """A --dry-run push, which publishes nothing but still runs the pre-push hook."""
    env = dict(BARE_ENV)
    if probe_env:
        env['SAIRN_PROBE_PUSH'] = '1'
    r = subprocess.run(['git', 'push', '--dry-run', 'origin', 'HEAD:main'],
                       cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
    err = (r.stderr or '') + (r.stdout or '')
    # ── THE REMOTE TIP MOVES UNDER THIS PROBE, SO ONE RETRY AFTER A FETCH ────
    # Five clones push to this branch and a run takes a minute. When origin/main
    # advances between one arm and the next, the sha git hands the hook is an
    # object this clone does not have yet and the gate refuses -- correctly --
    # before check 8 is reached. The fetch puts the new tip in the object store
    # the worktree shares; BASE is an ancestor of it, so the range is the
    # fixture commit again. If it persists, `could_not_run` says so rather than
    # letting an arm report it as check 8 failing to block.
    if r.returncode != 0 and RANGE_UNREADABLE in err:
        # ── THE RETRY FETCHES THE CLONE, NOT MAIN (2026-10-06) ──────────
        # It fetched MAIN, which worked while the fixture was a linked
        # WORKTREE sharing MAIN's object store. A clone has its own, so
        # fetching MAIN put the new tip somewhere this push cannot see and
        # the retry was a no-op: three consecutive runs SKIPPED with "the
        # gate could not read the outgoing range". Measured, then fixed --
        # the switch to a clone is what broke it.
        subprocess.run(['git', '-C', REPO, 'fetch', '--quiet', 'origin', 'main'],
                       capture_output=True)
        r = subprocess.run(['git', 'push', '--dry-run', 'origin', 'HEAD:main'],
                           cwd=REPO, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', env=env)
        err = (r.stderr or '') + (r.stdout or '')
    _reassert_config('dry_push(probe_env=%s)' % probe_env)
    return {
        'exit': r.returncode,
        'could_not_run': r.returncode != 0 and RANGE_UNREADABLE in err,
        'blocked_by_check8': 'PROBE fixture commit' in err,
        'names_the_commit': R.get('sha', 'zzzz')[:8] in err,
        'err': err,
    }


def pretooluse(cmd):
    """Drive the hook the way Claude Code does: a JSON payload on stdin."""
    r = subprocess.run([sys.executable, HOOK], cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace', env=BARE_ENV,
                       input=json.dumps({'tool_input': {'command': cmd}}))
    try:
        out = json.loads(r.stdout) if r.stdout.strip() else {}
    except ValueError:
        out = {}
    hook = out.get('hookSpecificOutput', {}) or {}
    _reassert_config('pretooluse(%s)' % cmd)
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

# ── COULD-NOT-RUN IS THE THIRD STATE AND IS NOT FOLDED INTO EITHER OTHER ───
# If the gate could not read the outgoing range even after the retry, it never
# reached check 8, and `blocked_by_check8: False` means "not asked" rather than
# "not blocked". An arm that calls that a check-8 failure is a verdict written
# on evidence that carries none -- which is what the raw "failed to push some
# refs" was doing here before the range was fixed.
_unattributable = [k for k, v in R.items()
                   if isinstance(v, dict) and v.get('could_not_run')]
if _unattributable:
    print('SKIPPED: the gate could not read the outgoing range for %s, so it never'
          % ', '.join(sorted(_unattributable)))
    print('reached check 8. Nothing about check 8 was verified.')
    print('  the refusal: %s' % str(R[_unattributable[0]]['err'])[-400:])
    sys.exit(3)

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
                     capture_output=True, text=True, encoding='utf-8', errors='replace').stdout == MAIN_TREE_BEFORE
      and subprocess.run(['git', '-C', MAIN, 'rev-parse', 'HEAD'],
                         capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
      == MAIN_HEAD_BEFORE)


# ── AND NEITHER WAS .git/config (2026-10-06) ───────────────────────────────
# `git status --porcelain` above says NOTHING about .git/config -- it is not a
# tracked file, so a clone whose config has been switched to `bare = true`
# reports a clean tree right up until the next git command fails outright.
# That is exactly how this went unnoticed: the probe's own "the CLONE was never
# touched" arm was true and the clone was unusable.
#
# This arm compares BYTES, not keys, so it also catches a write nobody
# predicted -- which matters here, because the writing command is not pinned.
_cfg_now = _read_config()
check('...and neither was .git/config -- byte-identical to the pre-run copy',
      _cfg_now == _CONFIG_BEFORE and not _CONFIG_DRIFTED,
      ('config was changed %d time(s) DURING this run (in: %s) and put back '
       'each time. The clone is usable; the writer is still unknown and this '
       'arm is the alert for it. Manual repair, if a run is ever killed: '
       'python tests/push_gate/check8_probe.py --restore-config'
       % (len(_CONFIG_DRIFTED), '; '.join(str(n) for n in _CONFIG_DRIFTED)))
      if _CONFIG_DRIFTED else
      ('config differs at exit. Expected %d bytes, found %s.'
       % (len(_CONFIG_BEFORE),
          'unreadable' if _cfg_now is None else '%d bytes' % len(_cfg_now))))

print('\n%s  check8_probe: %d failed' % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
