#!/usr/bin/env python
# -*- coding: utf-8 -*-
# OWNER: cody
"""git_config_isolation.py -- run a probe so it CANNOT leave this clone's git
administrative state changed, and prove it rather than trust it.

    python tools/git_config_isolation.py -- <command> [args ...]
    python tools/git_config_isolation.py --selftest

WHY. hank's b5 bare-run sweep found eleven tools that WRITE when run, and the
worktree/git-config family is the half that writes OUTSIDE the working tree,
where `git status` never shows it:
`condition_coverage.py`, `dead_rule_sweep.py`, `guard_ablation.py`,
`run_all_tests.py`, `install_git_hooks.py`, `run_semgrep.py`,
`invisible_in_pattern_check.py --help`. Four of the eleven fired on `--help`.

THE PREMISE WAS CHECKED BEFORE THIS WAS BUILT, AND IT WAS HALF WRONG.
MEASURED on this git version, in a throwaway repo, `git worktree add -q
--detach` leaves `.git/config` BYTE-IDENTICAL (sha unchanged, 168 bytes
unchanged) and instead creates `.git/worktrees/<name>/`; `git worktree remove`
removes it again. So "the worktree probes corrupt .git/config" is not the
mechanism. The mechanisms this guard actually has to cover are three, and they
are different problems with the same consequence:

  1. `.git/worktrees/` -- created by `worktree add`, and LEFT BEHIND when a
     probe dies between add and remove. That is the state that makes the next
     `worktree add` refuse, which is how a stale entry blocks an unrelated run.
  2. `.git/config` -- written by an explicit `git config <key> <value>` with no
     `-C <tempdir>`. In this repo the live-config writer is
     `install_git_hooks.py`, which does it BY DESIGN. This guard does not
     second-guess that; it makes an UNINTENDED write visible and reversible.
  3. THE USER'S GLOBAL CONFIG, which no probe should ever touch and which is
     invisible to every repo-scoped check in this tree. Hardened by env rather
     than by inspection: GIT_CONFIG_GLOBAL is pointed at a throwaway file and
     GIT_CONFIG_NOSYSTEM=1 is set, so a `git config --global` inside the
     wrapped command lands in the temp file and the real ~/.gitconfig is not
     reachable at all.

HOW IT FAILS. Snapshot, run, compare, and on ANY difference: RESTORE what it
can, report what it restored, and exit 1. A guard that only reports is a
notification; this one puts the bytes back. Restoration is limited to the two
things it snapshotted and it says so -- it is not a general undo.

EXIT CODES. Deliberately distinct from the wrapped command's, because folding
them is how "the probe passed" gets read off a guard's zero:
  0   the command ran AND the live git state is unchanged. The command's own
      exit code is printed and also written to the --rc-file if given.
  1   the live git state CHANGED. Restored where possible. THIS IS A FINDING
      ABOUT THE COMMAND, whatever the command itself returned.
  2   COULD NOT RUN -- no command given, this is not a git clone, or the
      snapshot could not be read. Never folded into 0: a guard that cannot
      snapshot has not guarded anything.
  3   the command could not be started at all (not found / not executable).

WHAT IT DOES NOT DO, so the zero is not overread: it does not watch the index,
HEAD, refs, the object store, or the working tree. Those are visible to
`git status` and to this repo's existing checks; the whole point of this wrapper
is the state that ISN'T.
"""

import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile

CRITERIA_VERSION = '2026-10-13.1'

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _git_dir(repo):
    """The real .git DIRECTORY, resolving the `gitdir:` file a worktree uses."""
    p = os.path.join(repo, '.git')
    if os.path.isdir(p):
        return p
    if os.path.isfile(p):
        with io.open(p, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                if line.startswith('gitdir:'):
                    g = line.split(':', 1)[1].strip()
                    return g if os.path.isabs(g) else os.path.join(repo, g)
    return None


def snapshot(repo):
    """Return (snap, error). snap is None on error -- never a partial dict."""
    g = _git_dir(repo)
    if not g or not os.path.isdir(g):
        return None, '%s is not a git clone (no readable .git)' % repo
    cfg = os.path.join(g, 'config')
    try:
        with open(cfg, 'rb') as fh:
            raw = fh.read()
    except (IOError, OSError) as exc:
        return None, 'cannot read %s -- %s' % (cfg, exc)
    wt_dir = os.path.join(g, 'worktrees')
    try:
        wt = sorted(os.listdir(wt_dir)) if os.path.isdir(wt_dir) else []
    except (IOError, OSError) as exc:
        return None, 'cannot list %s -- %s' % (wt_dir, exc)
    return {
        'git_dir': g,
        'config_path': cfg,
        'config_bytes': raw,
        'config_sha': hashlib.sha256(raw).hexdigest(),
        'worktrees': wt,
    }, None


def hardened_env(tmp):
    """Env that makes the user's global and system config unreachable."""
    env = dict(os.environ)
    env['GIT_CONFIG_GLOBAL'] = os.path.join(tmp, 'throwaway-global-gitconfig')
    env['GIT_CONFIG_SYSTEM'] = os.path.join(tmp, 'throwaway-system-gitconfig')
    env['GIT_CONFIG_NOSYSTEM'] = '1'
    # THE OPT-IN TOKEN the three adopting tools look for. Set ONLY here, so a
    # tool that checks it is checking "am I inside this guard" and cannot be
    # satisfied by anything a bare run does. Documented in require_isolation().
    env['SAIRN_GIT_ISOLATION'] = '1'
    # A probe that reads these to find "the repo" must not be handed the live
    # one by inheritance from this wrapper's own invocation.
    for k in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
        env.pop(k, None)
    return env


_REFUSAL = '''
COULD NOT RUN -- %s wants to add a git worktree to the LIVE clone
  %s
and that writes .git/worktrees/, which git status never shows and which is
left behind if this run dies before its cleanup. A stale entry makes the NEXT
worktree add refuse, so one dead probe blocks an unrelated run.

Run it through the guard instead, which snapshots and restores:

  python tools/git_config_isolation.py -- python tools/%s <args>

Exit 2 COULD NOT RUN, deliberately: a refusal that exited 0 would be
indistinguishable from a sweep that found nothing.
'''


def require_isolation(repo=None, who=None):
    """Refuse to mutate the LIVE clone's git admin state outside this guard.

    Called by the three tools that run `git worktree add` against the live
    repo -- condition_coverage.py, dead_rule_sweep.py, guard_ablation.py.
    FAILS CLOSED: prints what to run instead and exits 2 (COULD NOT RUN), so
    a refusal can never be read as a clean sweep.

    IT IS SILENT FOR A THROWAWAY CLONE. The check is not "is a worktree being
    added" -- it is "is the TARGET the live clone". A tool driving a temp repo
    is not this guard's business, and refusing it would make the guard the
    thing that breaks selftests.

    WHY exit 2 AND NOT A WARNING: three of these tools leave a
    .git/worktrees/<name> entry behind when they die between add and remove,
    and a stale entry makes the NEXT `worktree add` refuse -- so one dead
    probe blocks an unrelated run, in a directory `git status` never shows.
    A warning does not stop that; a refusal does.
    """
    if os.environ.get('SAIRN_GIT_ISOLATION') == '1':
        return
    target = os.path.realpath(repo or REPO)
    if target != os.path.realpath(REPO):
        return
    name = who or os.path.basename(sys.argv[0] or 'this tool')
    sys.stdout.write(_REFUSAL % (name, target, name))
    sys.stdout.flush()
    raise SystemExit(2)


def compare(before, after):
    """Return a list of human-readable differences. Empty means unchanged."""
    out = []
    if before['config_sha'] != after['config_sha']:
        out.append('.git/config CHANGED -- %d bytes (sha %s) -> %d bytes '
                   '(sha %s)' % (len(before['config_bytes']),
                                 before['config_sha'][:12],
                                 len(after['config_bytes']),
                                 after['config_sha'][:12]))
    gained = [w for w in after['worktrees'] if w not in before['worktrees']]
    lost = [w for w in before['worktrees'] if w not in after['worktrees']]
    if gained:
        out.append('.git/worktrees GAINED %d entry(ies): %s'
                   % (len(gained), ' '.join(gained)))
    if lost:
        out.append('.git/worktrees LOST %d entry(ies): %s'
                   % (len(lost), ' '.join(lost)))
    return out


def restore(before, after, repo):
    """Put back what we snapshotted. Returns a list of actions taken."""
    done = []
    if before['config_sha'] != after['config_sha']:
        try:
            with open(before['config_path'], 'wb') as fh:
                fh.write(before['config_bytes'])
            done.append('.git/config RESTORED from the snapshot (%d bytes)'
                        % len(before['config_bytes']))
        except (IOError, OSError) as exc:
            done.append('.git/config COULD NOT BE RESTORED -- %s' % exc)
    gained = [w for w in after['worktrees'] if w not in before['worktrees']]
    for w in gained:
        path = os.path.join(before['git_dir'], 'worktrees', w)
        try:
            shutil.rmtree(path, ignore_errors=True)
            done.append('.git/worktrees/%s REMOVED' % w)
        except (IOError, OSError) as exc:
            done.append('.git/worktrees/%s COULD NOT BE REMOVED -- %s'
                        % (w, exc))
    if gained:
        subprocess.run(['git', '-C', repo, 'worktree', 'prune'],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        done.append('git worktree prune run')
    return done


def run_guarded(cmd, repo, rc_file=None, quiet=False):
    def say(s):
        if not quiet:
            print(s)

    before, err = snapshot(repo)
    if before is None:
        say('COULD NOT RUN: %s' % err)
        say('A guard that cannot snapshot has not guarded anything, so this is')
        say('exit 2 and NOT a clean run.')
        return 2

    tmp = tempfile.mkdtemp(prefix='git_iso_')
    try:
        env = hardened_env(tmp)
        say('GIT CONFIG ISOLATION -- criteria %s' % CRITERIA_VERSION)
        say('  repo                %s' % repo)
        say('  .git/config sha     %s  (%d bytes)'
            % (before['config_sha'][:16], len(before['config_bytes'])))
        say('  .git/worktrees      %s'
            % (' '.join(before['worktrees']) or '(none)'))
        say('  GIT_CONFIG_GLOBAL   %s' % env['GIT_CONFIG_GLOBAL'])
        say('  GIT_CONFIG_NOSYSTEM 1')
        say('  command             %s' % ' '.join(cmd))
        say('')
        try:
            proc = subprocess.run(cmd, cwd=repo, env=env)
            inner = proc.returncode
        except (OSError, ValueError) as exc:
            say('COULD NOT START the command: %s' % exc)
            return 3

        after, err2 = snapshot(repo)
        if after is None:
            say('')
            say('COULD NOT RUN: the AFTER snapshot failed -- %s' % err2)
            say('The command ran (exit %d) and this guard cannot say whether it'
                % inner)
            say('changed anything. That is exit 2, not a pass.')
            return 2

        diffs = compare(before, after)
        say('')
        say('  wrapped command exit %d' % inner)
        if rc_file:
            try:
                with io.open(rc_file, 'w', encoding='utf-8') as fh:
                    fh.write('%d\n' % inner)
            except (IOError, OSError) as exc:
                say('  (could not write --rc-file: %s)' % exc)

        gl = env['GIT_CONFIG_GLOBAL']
        if os.path.exists(gl):
            say('  THE COMMAND WROTE A GLOBAL CONFIG, and it went to the')
            say('  throwaway file rather than the real one. Contents:')
            try:
                with io.open(gl, encoding='utf-8', errors='replace') as fh:
                    for line in fh.read().split('\n'):
                        if line.strip():
                            say('      %s' % line.rstrip())
            except (IOError, OSError):
                pass

        if not diffs:
            say('')
            say('UNCHANGED. .git/config and .git/worktrees are byte-for-byte '
                'what they were.')
            say('NOT a statement that the command is correct, and NOT a '
                'statement about the')
            say('index, HEAD, refs, objects or the working tree -- those are '
                'visible to git')
            say('status and are deliberately out of scope here.')
            return 0

        say('')
        say('CHANGED -- %d difference(s). THIS IS A FINDING ABOUT THE COMMAND,'
            % len(diffs))
        say('whatever the command itself returned (it returned %d).' % inner)
        for d in diffs:
            say('  ! %s' % d)
        say('')
        for a in restore(before, after, repo):
            say('  > %s' % a)
        final, _ = snapshot(repo)
        if final is not None:
            still = compare(before, final)
            say('')
            if still:
                say('  STILL DIFFERENT after restoration -- %d:' % len(still))
                for d in still:
                    say('    ! %s' % d)
            else:
                say('  verified: the live state now matches the snapshot again.')
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# SELFTEST. Runs entirely inside a throwaway clone -- it never drives the
# live repo, because a selftest that proves isolation by mutating the thing it
# is protecting has already failed.
# ---------------------------------------------------------------------------

def _mk_repo(tmp):
    r = os.path.join(tmp, 'r')
    os.makedirs(r)
    def g(*a):
        return subprocess.run(['git'] + list(a), cwd=r,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    g('init', '-q', '.')
    g('config', 'user.email', 'iso@example.invalid')
    g('config', 'user.name', 'iso')
    with io.open(os.path.join(r, 'a.txt'), 'w', encoding='utf-8') as fh:
        fh.write('hi\n')
    g('add', 'a.txt')
    g('commit', '-q', '-m', 'init')
    return r


def selftest():
    print('GIT CONFIG ISOLATION SELFTEST -- criteria %s' % CRITERIA_VERSION)
    passed = failed = 0
    results = []

    def arm(name, fn):
        nonlocal passed, failed
        try:
            fn()
            print('  ok   %s' % name)
            passed += 1
        except AssertionError as exc:
            print('  FAIL %s\n       %s' % (name, exc))
            failed += 1
            results.append(name)

    tmp = tempfile.mkdtemp(prefix='git_iso_selftest_')
    try:
        # 1. THE NEGATIVE CONTROL FIRST. If an unguarded config write does not
        # register, every "unchanged" below is vacuous.
        def control_config():
            r = _mk_repo(tmp + os.sep + 'c1') if False else _mk_repo(
                tempfile.mkdtemp(prefix='iso_c1_', dir=tmp))
            b, e = snapshot(r)
            assert b is not None, e
            subprocess.run(['git', '-C', r, 'config', 'sairn.planted', 'yes'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            a, e2 = snapshot(r)
            assert a is not None, e2
            d = compare(b, a)
            assert any('.git/config CHANGED' in x for x in d), (
                'an unguarded `git config` write did NOT register as a '
                'difference, so this guard cannot see the thing it exists to '
                'see and every UNCHANGED verdict is decoration. diffs=%r' % d)
        arm('1. CONTROL -- an unguarded `git config` write IS detected',
            control_config)

        def control_worktree():
            r = _mk_repo(tempfile.mkdtemp(prefix='iso_c2_', dir=tmp))
            b, _ = snapshot(r)
            wt = os.path.join(os.path.dirname(r), 'wt')
            subprocess.run(['git', '-C', r, 'worktree', 'add', '-q',
                            '--detach', wt, 'HEAD'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            a, _ = snapshot(r)
            d = compare(b, a)
            assert any('GAINED' in x for x in d), (
                'an unguarded `worktree add` did NOT register. MEASURED NOTE: '
                'it does NOT touch .git/config on this git version -- it '
                'creates .git/worktrees/<name>, which is why this guard '
                'snapshots both. diffs=%r' % d)
        arm('2. CONTROL -- an unguarded `worktree add` IS detected '
            '(.git/worktrees, NOT .git/config)', control_worktree)

        # 2. THE GUARD ITSELF, driven over a throwaway clone.
        def guarded_config_write_is_caught_and_restored():
            r = _mk_repo(tempfile.mkdtemp(prefix='iso_g1_', dir=tmp))
            b, _ = snapshot(r)
            rc = run_guarded(['git', 'config', 'sairn.planted', 'yes'],
                             r, quiet=True)
            assert rc == 1, ('the guard returned %d for a command that wrote '
                             '.git/config; 1 is the finding code' % rc)
            a, _ = snapshot(r)
            assert a['config_sha'] == b['config_sha'], (
                'the guard reported the change but did NOT restore the bytes. '
                'A guard that only reports is a notification.')
        arm('3. a guarded `git config` write is CAUGHT (exit 1) and the bytes '
            'are RESTORED', guarded_config_write_is_caught_and_restored)

        def guarded_worktree_is_caught_and_cleaned():
            r = _mk_repo(tempfile.mkdtemp(prefix='iso_g2_', dir=tmp))
            b, _ = snapshot(r)
            wt = os.path.join(os.path.dirname(r), 'wt2')
            rc = run_guarded(['git', 'worktree', 'add', '-q', '--detach',
                              wt, 'HEAD'], r, quiet=True)
            assert rc == 1, ('the guard returned %d for a command that created '
                             'a worktree entry' % rc)
            a, _ = snapshot(r)
            assert a['worktrees'] == b['worktrees'], (
                'the worktree entry was left behind: %r -> %r. A stale entry '
                'is exactly what makes the NEXT `worktree add` refuse.'
                % (b['worktrees'], a['worktrees']))
        arm('4. a guarded `worktree add` is CAUGHT and .git/worktrees is '
            'CLEANED', guarded_worktree_is_caught_and_cleaned)

        def guarded_clean_command_is_zero():
            r = _mk_repo(tempfile.mkdtemp(prefix='iso_g3_', dir=tmp))
            rc = run_guarded(['git', 'status', '--porcelain'], r, quiet=True)
            assert rc == 0, ('a read-only command returned %d. A guard that '
                             'reports a finding on every run is a guard '
                             'nobody reads.' % rc)
        arm('5. a read-only command passes CLEAN (exit 0)',
            guarded_clean_command_is_zero)

        def global_config_is_unreachable():
            r = _mk_repo(tempfile.mkdtemp(prefix='iso_g4_', dir=tmp))
            home = os.path.expanduser('~')
            real = os.path.join(home, '.gitconfig')
            before = None
            if os.path.isfile(real):
                with open(real, 'rb') as fh:
                    before = hashlib.sha256(fh.read()).hexdigest()
            rc = run_guarded(['git', 'config', '--global', 'sairn.planted',
                              'yes'], r, quiet=True)
            assert rc == 0, ('a --global write changed the REPO state, which '
                             'this arm did not expect (rc=%d)' % rc)
            after = None
            if os.path.isfile(real):
                with open(real, 'rb') as fh:
                    after = hashlib.sha256(fh.read()).hexdigest()
            assert before == after, (
                'THE USER\'S REAL ~/.gitconfig CHANGED. GIT_CONFIG_GLOBAL '
                'did not hold, and this is the one failure here that reaches '
                'outside the repo entirely.')
        arm('6. `git config --global` inside the guard does NOT touch the '
            'real ~/.gitconfig', global_config_is_unreachable)

        def not_a_clone_is_exit_2():
            d = tempfile.mkdtemp(prefix='iso_g5_', dir=tmp)
            rc = run_guarded(['git', 'status'], d, quiet=True)
            assert rc == 2, ('a directory that is not a git clone returned %d; '
                             'COULD NOT RUN is 2 and must never be folded into '
                             '0' % rc)
        arm('7. a directory that is not a clone is exit 2 COULD NOT RUN',
            not_a_clone_is_exit_2)

        def missing_command_is_exit_3():
            r = _mk_repo(tempfile.mkdtemp(prefix='iso_g6_', dir=tmp))
            rc = run_guarded([os.path.join(r, 'no-such-binary-xyzzy')], r,
                             quiet=True)
            assert rc == 3, ('a command that cannot start returned %d, not 3. '
                             'A command that never ran is not a clean run.'
                             % rc)
        arm('8. a command that cannot start is exit 3, not 0',
            missing_command_is_exit_3)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('')
    if failed:
        print('%d ARM(S) FAILED:' % failed)
        for n in results:
            print('  - %s' % n)
    print('%d passed, %d failed' % (passed, failed))
    return 1 if failed else 0


def main(argv):
    if '--selftest' in argv:
        return selftest()
    repo = REPO
    rc_file = None
    cmd = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--repo' and i + 1 < len(argv):
            repo = os.path.abspath(argv[i + 1]); i += 2; continue
        if a == '--rc-file' and i + 1 < len(argv):
            rc_file = argv[i + 1]; i += 2; continue
        if a == '--':
            cmd = argv[i + 1:]
            break
        i += 1
    if not cmd:
        print(__doc__.split('\n\n')[0])
        print('')
        print('COULD NOT RUN: no command. Usage:')
        print('  python tools/git_config_isolation.py -- <command> [args ...]')
        print('  python tools/git_config_isolation.py --selftest')
        print('')
        print('Exit 2, because a wrapper with nothing to wrap has not '
              'guarded anything.')
        return 2
    return run_guarded(cmd, repo, rc_file=rc_file)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
