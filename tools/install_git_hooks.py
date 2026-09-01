#!/usr/bin/env python
"""tools/install_git_hooks.py -- point this clone's git at .githooks/

WHY A SEPARATE INSTALL STEP EXISTS AND CANNOT BE AVOIDED. Git hooks live in
.git/hooks/, which is not versioned, so a hook committed to the repo does
nothing until each clone opts in. `core.hooksPath` is the supported way to
point git at a tracked directory instead. That config is per-clone, so this
must be run once in each of the four clones (SAIRN-hank, SAIRN-cc,
SAIRN-cody, SAIRN-fourth).

WHAT IT GUARDS. tools/sairn_push_gate_hook.py used to fire only as a Claude
Code PreToolUse hook matching the Bash command text \\bgit\\s+push\\b.
tools/sairn_claim.py pushes via subprocess from Python, so that regex never
matched and every claim/release call skipped all three push-gate checks. The
pre-push hook keys on the git operation instead, which no caller can spell
its way around.

Idempotent. Run it as often as you like:

    python tools/install_git_hooks.py            # install and verify
    python tools/install_git_hooks.py --check    # verify only, exit 1 if not installed
"""

import os
import subprocess
import sys


def git(*args):
    r = subprocess.run(['git'] + list(args), capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def main():
    check_only = '--check' in sys.argv

    rc, repo, _ = git('rev-parse', '--show-toplevel')
    if rc != 0:
        print('Not inside a git repository.')
        return 1
    repo = repo.replace('\\', '/')

    hookdir = os.path.join(repo, '.githooks')
    hookfile = os.path.join(hookdir, 'pre-push')
    if not os.path.isfile(hookfile):
        print('MISSING: .githooks/pre-push is not in this clone.')
        print('Fetch the branch that carries it before installing.')
        return 1

    rc, current, _ = git('config', '--get', 'core.hooksPath')
    installed = (rc == 0 and current.replace('\\', '/').rstrip('/').endswith('.githooks'))

    if check_only:
        if installed:
            print('OK -- core.hooksPath = %s' % current)
            return 0
        print('NOT INSTALLED -- core.hooksPath is %s' % (current or '<unset>'))
        print('Run: python tools/install_git_hooks.py')
        return 1

    if not installed:
        rc, _, err = git('config', 'core.hooksPath', '.githooks')
        if rc != 0:
            print('Failed to set core.hooksPath: %s' % err)
            return 1

    # On Windows+Git-Bash the executable bit is not what decides whether a hook
    # runs, but set it where the filesystem supports it so the same checkout
    # works on macOS and Linux.
    try:
        mode = os.stat(hookfile).st_mode
        os.chmod(hookfile, mode | 0o111)
    except Exception:
        pass

    rc, current, _ = git('config', '--get', 'core.hooksPath')
    print('core.hooksPath = %s' % current)

    # Prove the hook actually RUNS rather than reporting that a file exists --
    # the whole failure being fixed here was a gate that was present and never
    # asked. --pre-push with no stdin refs exits 0 (nothing outgoing to check),
    # so a clean exit here means the interpreter, the path and the script all
    # resolved.
    gate = os.path.join(repo, 'tools', 'sairn_push_gate_hook.py')
    r = subprocess.run([sys.executable, gate, '--pre-push'],
                       input='', capture_output=True, text=True, cwd=repo)
    if r.returncode not in (0, 1):
        print('WARNING: the gate script did not run cleanly (exit %d).' % r.returncode)
        print(r.stderr.strip()[:400])
        return 1
    print('Gate script runs. Installed.')
    print('')
    print('Verify end to end with a real push from a NON-Bash caller:')
    print('    python tools/sairn_claim.py claim <subject> <task>')
    print('A push that touches sql/ with no db/schema_snapshot.json must now be')
    print('refused through that path too, not only through a typed git push.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
