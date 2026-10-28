#!/usr/bin/env python
"""run_core_bare_kill_probe.py -- a hard kill mid-fixture must not leave core.bare set.

    python tests/run_core_bare_kill_probe.py

tools/copy_exactly_gate.py runs its blind-lock fixtures on every pre-push, and
each one starts with `git -C <tempdir> init`. git exports GIT_DIR to the hook,
absolute when the push comes from a linked worktree, and GIT_DIR beats -C: the
init re-initialised the REAL repository and wrote core.bare=true into the
SHARED .git/config (cc b60). The gate now drops that env for the fixture run.

Everything here happens in a throwaway repo with a linked worktree. The real
gate is run as a subprocess under the exact GIT_DIR a worktree's pre-push hook
receives, and the observable is that throwaway repo's shared config -- the gate
itself never reads or writes it, so this clone cannot be touched even if the
fix is reverted.

── WHY A KILL AND NOT AN INTERRUPT ─────────────────────────────────────────
Popen.kill() on Windows is TerminateProcess: no finally runs, which is the same
death as the low-memory kill that cut short the b59 replay. A restore in a
finally cannot pass this; only a write that never reaches the shared config
can. The finally in the gate is the net for exceptions and Ctrl-C.

── THE ARMS ────────────────────────────────────────────────────────────────
A0  premise: a real `git push --dry-run` from the worktree hands the hook an
    ABSOLUTE GIT_DIR. Without it the rest is testing an env nothing produces.
A1  teeth: a stand-in doing exactly the gate's old first line under that
    GIT_DIR, hard-killed, DOES leave core.bare=true. Without it every pass
    below could be an observable that cannot see the leak.
A2  control: the real gate's --fixtures, run to completion under that GIT_DIR,
    exits 0 and leaves core.bare false.
A3  the kill: the real gate, hard-killed at several points while still running,
    leaves core.bare false every time.
A4  the hook: .githooks/pre-push unsets GIT_DIR before its first gate runs.
    Structural, because driving the real hook means running the whole gate.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(REPO, 'tools', 'copy_exactly_gate.py')
HOOK = os.path.join(REPO, '.githooks', 'pre-push')

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PASS, FAIL = [], []


def check(name, ok, detail=''):
    (PASS if ok else FAIL).append(name)
    print('  %-4s %s' % ('ok' if ok else 'FAIL', name))
    if not ok and detail:
        print('       %s' % str(detail)[:900])


def git(*a, cwd=None, env=None):
    r = subprocess.run(['git'] + list(a), cwd=cwd, env=env, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout + r.stderr).strip()


def bare(main):
    return git('config', '--get', 'core.bare', cwd=main)[1]


def killed_at(argv, env, delay):
    """Start argv, hard-kill it after `delay` seconds. Returns whether it was
    still running at the kill, so a kill that landed after exit is not counted."""
    p = subprocess.Popen(argv, env=env, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    time.sleep(delay)
    alive = p.poll() is None
    p.kill()
    p.wait()
    time.sleep(1.0)            # let any orphaned git child finish its write
    return alive


def main():
    base = tempfile.mkdtemp(prefix='core_bare_kill_')
    try:
        main_ = os.path.join(base, 'main')
        os.makedirs(main_)
        git('init', '-q', cwd=main_)
        git('-c', 'user.email=k@example.invalid', '-c', 'user.name=k',
            'commit', '-q', '--allow-empty', '-m', 'a', cwd=main_)
        remote = os.path.join(base, 'remote.git')
        git('init', '-q', '--bare', remote)
        git('remote', 'add', 'origin', remote, cwd=main_)
        wt = os.path.join(base, 'wt')
        git('worktree', 'add', '-q', '--detach', wt, cwd=main_)

        # A0 -- what git really hands a pre-push hook from a worktree.
        hooks = os.path.join(base, 'hooks')
        os.makedirs(hooks)
        envlog = os.path.join(base, 'hookenv.txt').replace('\\', '/')
        with io.open(os.path.join(hooks, 'pre-push'), 'w', newline='\n') as f:
            f.write('#!/bin/sh\nprintf "%%s" "$GIT_DIR" > "%s"\nexit 0\n' % envlog)
        git('config', 'core.hooksPath', hooks.replace('\\', '/'), cwd=main_)
        git('push', '--dry-run', 'origin', 'HEAD:refs/heads/x', cwd=wt)
        git('config', '--unset', 'core.hooksPath', cwd=main_)
        hook_gd = io.open(envlog).read().strip() if os.path.exists(envlog) else ''
        check('A0 a worktree pre-push hook receives an ABSOLUTE GIT_DIR',
              os.path.isabs(hook_gd) and 'worktrees' in hook_gd.replace('\\', '/'), hook_gd)
        check('...and core.bare starts false', bare(main_) == 'false', bare(main_))
        env = dict(os.environ, GIT_DIR=hook_gd or 'unset')

        # A1 -- teeth.
        td = os.path.join(base, 'td')
        os.makedirs(td)
        stand_in = [sys.executable, '-c',
                    'import subprocess,time;'
                    'subprocess.run(["git","-C",%r,"init","-q"]);time.sleep(30)' % td]
        alive = killed_at(stand_in, env, 3.0)
        check('A1 TEETH: the old first line, hard-killed, leaves core.bare=true',
              alive and bare(main_) == 'true', (alive, bare(main_)))
        git('config', 'core.bare', 'false', cwd=main_)

        # A2 -- control, and the timing the kills are placed against.
        t0 = time.time()
        r = subprocess.run([sys.executable, GATE, '--fixtures'], env=env,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace')
        dur = time.time() - t0
        check('A2 the real gate --fixtures under that GIT_DIR exits 0',
              r.returncode == 0, (r.returncode, (r.stdout + r.stderr)[-400:]))
        check('...and leaves core.bare false', bare(main_) == 'false', bare(main_))

        # A3 -- the kill, at several points inside the measured run.
        for frac in (0.15, 0.35, 0.55, 0.75):
            alive = killed_at([sys.executable, GATE, '--fixtures'], env, dur * frac)
            check('A3 hard kill at %d%% of a %.1fs run: still running at the kill, '
                  'core.bare still false' % (frac * 100, dur),
                  alive and bare(main_) == 'false', (alive, bare(main_)))
            git('config', 'core.bare', 'false', cwd=main_)

        # A4 -- the hook drops the env before any gate.
        lines = io.open(HOOK, encoding='utf-8').read().splitlines()
        unset = next((i for i, l in enumerate(lines)
                      if l.strip().startswith('unset ') and 'GIT_DIR' in l), None)
        first = next((i for i, l in enumerate(lines)
                      if '"$PY"' in l and not l.lstrip().startswith('#')), None)
        check('A4 .githooks/pre-push unsets GIT_DIR before its first gate',
              unset is not None and first is not None and unset < first, (unset, first))
    finally:
        shutil.rmtree(base, ignore_errors=True)

    print('\n%d passed, %d failed' % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
