"""tests/run_githook_install_probe.py

Run:  python tests/run_githook_install_probe.py

`install_git_hooks.py --check` ANSWERED A WEAKER QUESTION THAN `install` DID.

── WHY THIS EXISTS, AND IT ALREADY HAPPENED ──────────────────────────────────
.githooks/pre-push is what makes the push gate fire on the GIT OPERATION rather
than on the text of a Bash command -- the only thing that gates a push made by
subprocess, which is how tools/sairn_claim.py pushes.

On 2026-09-01 all four clones held a CRLF copy of that hook. A CRLF shebang names
an interpreter whose name ends in a carriage return, so git skipped the hook
SILENTLY on every push. Two of the four clones had core.hooksPath set correctly
the whole time -- and `--check` compared core.hooksPath and nothing else, so it
would have printed OK on a clone whose hook had never once executed.

That is the same shape as every other finding in this sweep: a verifier reporting
protected while the protection is dead. The install path already repaired CRLF,
ran the gate and ran the wrapper; --check saw none of it. It does now.

── WHY A THROWAWAY CLONE AND NOT A WORKTREE ──────────────────────────────────
core.hooksPath is REPOSITORY config, and `git worktree` shares .git/config with
the clone that created it. Breaking the config in a worktree would disarm the
real clone's push gate for as long as the probe ran. So every arm below runs in a
separate `git clone --local`, and section F asserts this clone's own config is
untouched at the end.

── THE ARM THAT MATTERS IS C ─────────────────────────────────────────────────
It asserts core.hooksPath is CORRECT in that clone and --check still fails. Any
arm can show "--check exits 1 on a broken clone"; only that one shows the check
now sees something core.hooksPath cannot.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

CONTROLS_FOR = ['install_git_hooks.py']

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
FAIL = []


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else '\n        ' + str(detail)[:400]))
    if not cond:
        FAIL.append(name)


def git(cwd, *args):
    return subprocess.run(['git', '-C', cwd] + list(args), capture_output=True, text=True)


def check(cwd):
    """Run THIS clone's install_git_hooks.py against `cwd`.

    Deliberately not the target clone's own copy. `git clone` carries committed
    HEAD, so a throwaway clone runs the tool as it was BEFORE the change under
    test -- the first version of this probe did that and reported four arms
    failing because it was exercising the old code. The tool resolves its subject
    from `git rev-parse --show-toplevel` under cwd, so pointing this clone's
    script at that directory checks that directory.
    """
    r = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'install_git_hooks.py'),
                        '--check'], capture_output=True, text=True, cwd=cwd,
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def rmtree(path):
    """Windows leaves git's object files read-only; plain rmtree leaves residue."""
    def onerror(fn, p, _exc):
        try:
            os.chmod(p, 0o700)
            fn(p)
        except Exception:
            pass
    shutil.rmtree(path, onerror=onerror)


def hookpath(cwd):
    return os.path.join(cwd, '.githooks', 'pre-push')


print('\nA. this clone answers, and the answer is read-only')
before = git(REPO, 'config', '--get', 'core.hooksPath').stdout.strip()
rc, out = check(REPO)
ok('--check passes in this clone', rc == 0, 'exit=%d\n%s' % (rc, out[-300:]))
ok('...and it names all three facts, not just the config',
   'hooksPath' in out and 'LF' in out and 'run' in out, out[-300:])

TMP = tempfile.mkdtemp(prefix='githook-probe-')
CLONE = os.path.join(TMP, 'clone')
try:
    c = subprocess.run(['git', 'clone', '--local', '--quiet', REPO, CLONE],
                       capture_output=True, text=True)
    ok('a throwaway clone was made', os.path.isfile(hookpath(CLONE)),
       c.stderr[-300:])

    print('\nB. a FRESH CLONE is not installed, and --check says so')
    # Nothing here is planted: `git clone` does not carry core.hooksPath, which
    # is the entire reason the install step exists per clone.
    rc, out = check(CLONE)
    ok('--check fails on a fresh clone', rc == 1, 'exit=%d\n%s' % (rc, out[-300:]))
    ok('...and the reason names core.hooksPath', 'core.hooksPath' in out, out[-300:])

    print('\nC. THE ONE THAT MATTERS -- hooksPath CORRECT, hook DEAD')
    git(CLONE, 'config', 'core.hooksPath', '.githooks')
    raw = io.open(hookpath(CLONE), 'rb').read()
    ok('the fresh clone checked the hook out as LF', b'\r\n' not in raw)
    io.open(hookpath(CLONE), 'wb').write(raw.replace(b'\n', b'\r\n'))
    cfg = git(CLONE, 'config', '--get', 'core.hooksPath').stdout.strip()
    ok('core.hooksPath is CORRECT in this clone', cfg == '.githooks', cfg)
    rc, out = check(CLONE)
    ok('--check STILL fails -- the old version would have printed OK here',
       rc == 1, 'exit=%d\n%s' % (rc, out[-400:]))
    ok('...and the reason names CRLF and says git skips it silently',
       'CRLF' in out and 'silently' in out.lower(), out[-400:])
    ok('...and --check REPAIRED NOTHING -- it is a check, not a fix',
       b'\r\n' in io.open(hookpath(CLONE), 'rb').read())

    print('\nD. a broken shell wrapper is caught too')
    io.open(hookpath(CLONE), 'wb').write(b'#!/bin/sh\nthis-interpreter-does-not-exist\n')
    rc, out = check(CLONE)
    ok('--check fails on a wrapper that does not execute', rc == 1,
       'exit=%d\n%s' % (rc, out[-400:]))
    ok('...and the reason names the WRAPPER, not the config',
       'WRAPPER' in out and 'core.hooksPath is' not in out, out[-400:])

    print('\nE. CONTROL -- a properly installed clone PASSES')
    # Without this, every arm above is "--check fails on anything".
    git(CLONE, 'checkout', '-q', '--', '.githooks/pre-push')
    raw = io.open(hookpath(CLONE), 'rb').read()
    if b'\r\n' in raw:
        io.open(hookpath(CLONE), 'wb').write(raw.replace(b'\r\n', b'\n'))
    rc, out = check(CLONE)
    ok('--check passes once the clone is really installed', rc == 0,
       'exit=%d\n%s' % (rc, out[-400:]))
finally:
    rmtree(TMP)
    print('\nF. this clone was never touched')
    after = git(REPO, 'config', '--get', 'core.hooksPath').stdout.strip()
    ok('core.hooksPath is unchanged in THIS clone', after == before,
       'before=%r after=%r' % (before, after))
    ok('this clone\'s own pre-push is still LF',
       b'\r\n' not in io.open(hookpath(REPO), 'rb').read())
    ok('the throwaway clone is gone', not os.path.isdir(TMP))

print('\n%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
