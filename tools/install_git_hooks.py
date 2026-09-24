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
    r = subprocess.run(['git'] + list(args), capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def git_actually_fires(hookdir):
    """Does GIT ITSELF invoke the hook? Not "does the file run when I run it".

    Returns (fired, detail). `fired` is True, False, or None for COULD NOT TELL
    -- which is a third state and is never folded into either of the others.

    ── WHY THE OTHER CHECKS DO NOT ANSWER THIS (added 2026-09-16) ─────────────
    --check already reads core.hooksPath, reads the file's bytes, and executes
    the wrapper with `sh <file>`. Every one of those is a statement about the
    FILE. None of them is a statement about GIT: hooksPath can be right and the
    file present and executable while git still does not run it -- a wrong file
    name, a permission bit, an interpreter git resolves differently from the
    shell this checker happens to be running under.
    `sh <file>` in particular never consults the shebang at all, which
    runs_cleanly() already says about itself.

    ── HOW IT IS ANSWERED, WITHOUT TOUCHING THIS CLONE OR ANY REAL REMOTE ─────
    A throwaway repo is created in a temp directory, its core.hooksPath is
    pointed at THIS clone's .githooks, and a DRY-RUN push is made to a
    throwaway BARE repo beside it. `git push --dry-run` runs pre-push -- checked
    on this platform rather than assumed.

    THE DETECTION IS UNAMBIGUOUS BECAUSE THE HOOK CANNOT SUCCEED THERE. The
    hook resolves ROOT from `git rev-parse --show-toplevel`, which in the
    scratch repo is the scratch repo, so `python $ROOT/tools/register_feed_gate.py`
    cannot be opened and the hook exits 1. So:

        push refused, with that failure in the output -> THE HOOK FIRED
        push succeeded                                 -> GIT DID NOT RUN IT

    Nothing is pushed anywhere real: the remote is a bare repo in the same temp
    directory, and --dry-run on top of that. This clone's config is untouched.
    """
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix='sairn-hookfire-')
    try:
        src = os.path.join(tmp, 'src')
        bare = os.path.join(tmp, 'remote.git')
        for cmd in (['init', '-q', '-b', 'main', src],
                    ['init', '-q', '--bare', bare]):
            if subprocess.run(['git'] + cmd, capture_output=True).returncode != 0:
                return (None, 'could not create the throwaway repos')
        def g(*a):
            return subprocess.run(['git', '-C', src] + list(a), capture_output=True,
                                  text=True, encoding='utf-8', errors='replace')
        g('config', 'user.email', 'hookfire@example.invalid')
        g('config', 'user.name', 'hookfire')
        g('config', 'core.hooksPath', hookdir.replace('\\', '/'))
        with open(os.path.join(src, 'f.txt'), 'w') as f:
            f.write('x\n')
        g('add', '-A')
        if g('commit', '-q', '-m', 'probe').returncode != 0:
            return (None, 'could not commit in the throwaway repo')
        r = g('push', '--dry-run', bare.replace('\\', '/'), 'main')
        out = (r.stdout or '') + (r.stderr or '')
        if r.returncode != 0 and 'register_feed_gate.py' in out:
            return (True, 'git ran .githooks/pre-push (it refused the dry-run '
                          'from the scratch repo, as it must)')
        if r.returncode == 0:
            return (False, 'git did NOT run .githooks/pre-push -- a dry-run push '
                           'with core.hooksPath pointed at it succeeded, and it '
                           'cannot succeed if the hook executes')
        return (None, 'the dry-run failed for a reason that is not the hook: '
                      + out.strip()[:200])
    except Exception as e:                                       # noqa: BLE001
        return (None, 'could not run the fire test: %s' % e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def runs_cleanly(repo, hookfile):
    """Do the gate script and the shell wrapper actually EXECUTE?

    Returns a list of reasons, empty if both run. Read-only: this repairs
    nothing, which is why --check can use it and install still repairs first.

    HONEST SCOPE, MEASURED RATHER THAN ASSUMED. This does NOT catch the CRLF
    failure -- `sh <file>` reads the file as a script and never consults the
    shebang, so a CRLF copy and an LF copy both exit 0 here. Verified both ways.
    The byte check is the authoritative one for that; this is a second, narrower
    net for a broken wrapper (shell syntax error, missing interpreter, bad path).
    """
    reasons = []
    gate = os.path.join(repo, 'tools', 'sairn_push_gate_hook.py')
    r = subprocess.run([sys.executable, gate, '--pre-push'],
                       input='', capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=repo)
    if r.returncode not in (0, 1):
        reasons.append('the gate script did not run cleanly (exit %d): %s'
                       % (r.returncode, r.stderr.strip()[:200]))
    try:
        w = subprocess.run(['sh', hookfile], input='', capture_output=True,
                           text=True, encoding='utf-8', errors='replace', cwd=repo)
        if ('not found' in (w.stderr or '').lower()
                or 'bad interpreter' in (w.stderr or '').lower()
                or w.returncode not in (0, 1)):
            reasons.append('the SHELL WRAPPER did not execute (exit %d): %s'
                           % (w.returncode, (w.stderr or '').strip()[:200]))
    except Exception as e:
        reasons.append('could not execute the shell wrapper: %s' % e)
    return reasons


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
        # ── --check ANSWERED A WEAKER QUESTION THAN install DID, AND THE
        # ── DIFFERENCE WAS THE FAILURE THIS FILE EXISTS FOR (2026-09-13) ──────
        # It compared core.hooksPath and stopped. The install path below then
        # went on to repair CRLF, run the gate and run the shell wrapper --
        # three facts --check could not see. So on 2026-09-01, when all four
        # clones held a CRLF .githooks/pre-push and git was skipping it silently
        # on every push, hank and cody had core.hooksPath set and this flag
        # would have printed OK. That is the whole shape of the incident in the
        # docstring above: reporting protected while the protection has never
        # once executed.
        #
        # It CHECKS rather than repairs -- the byte fix belongs to install, and
        # a --check that quietly rewrote a file would be worse than a weak one.
        problems = []
        if not installed:
            problems.append('core.hooksPath is %s, not .githooks' % (current or '<unset>'))
        try:
            if b'\r\n' in open(hookfile, 'rb').read():
                problems.append('.githooks/pre-push has CRLF endings -- the shebang names '
                                'an interpreter whose name ends in a carriage return, and '
                                'git SKIPS the hook silently on every push')
        except Exception as e:
            problems.append('could not read .githooks/pre-push: %s' % e)
        problems.extend(runs_cleanly(repo, hookfile))
        # ── AND THE ONLY QUESTION THAT MATTERS: DOES GIT RUN IT? ────────────
        # Everything above is a statement about the FILE. This one is about
        # GIT, and it is the difference between "installed" and "protected".
        # ── THE CONFIGURED PATH, NOT THE TRACKED ONE, AND THE PROBE CAUGHT ME
        # ── PASSING THE WRONG ONE (2026-09-16) ──────────────────────────────
        # The first version handed this the directory the tracked hook lives
        # in, which proves "git would fire .githooks/pre-push IF POINTED AT
        # IT" -- a fact about the repository, not about this clone. With
        # core.hooksPath pointed at a decoy directory named `.githooks` holding
        # no pre-push, every file-level check passed AND the fire test passed,
        # and --check printed OK on a clone git was not running any hook for.
        # Caught by arm 3 of tests/install_git_hooks_check_probe.py, which
        # exists to build exactly that state.
        hooks_cfg = current if os.path.isabs(current or '') else os.path.join(repo, current or '')
        fired, why = git_actually_fires(hooks_cfg)
        if fired is False:
            problems.append(why)
        elif fired is None:
            # COULD NOT TELL is a third state. It does not join the problems
            # list -- that would report a defect nobody found -- and it does not
            # pass silently either.
            print('COULD NOT TELL whether git fires the hook: %s' % why)
            print('That is not a pass. The checks below still ran.')
        if not problems:
            print('OK -- core.hooksPath = %s, hook is LF, gate and wrapper both '
                  'run, and GIT ITSELF FIRES IT%s'
                  % (current, '' if fired else ' (unverified -- see above)'))
            return 0 if fired else 2
        print('NOT INSTALLED, or installed and DEAD:')
        for p in problems:
            print('  - %s' % p)
        print('Run: python tools/install_git_hooks.py')
        return 1

    if not installed:
        rc, _, err = git('config', 'core.hooksPath', '.githooks')
        if rc != 0:
            print('Failed to set core.hooksPath: %s' % err)
            return 1

    # ── LINE ENDINGS: THE REASON THIS HOOK NEVER RAN ANYWHERE ──────────────
    # Added 2026-09-01 during the CC/Cody reconciliation. This repo runs
    # core.autocrlf=true. .githooks/pre-push is stored LF in the object
    # database, but with no attribute governing it git wrote CRLF into every
    # working tree on checkout -- which makes the shebang name an interpreter
    # whose name ends in a carriage return. git then skips the hook SILENTLY,
    # with no error, on every push.
    #
    # Measured across all four clones that day: hank CRLF, cody CRLF, fourth
    # CRLF, cc CRLF. hank and cody had already run this installer and had
    # core.hooksPath set, so both were reporting themselves protected while the
    # hook had never once executed. .gitattributes now pins `.githooks/* text
    # eol=lf`, but an attribute only takes effect on the NEXT checkout, so an
    # existing clone keeps its broken copy until something rewrites it. That is
    # what this does.
    #
    # Rewriting is safe and invisible to git status: the blob is already LF, so
    # with autocrlf=true a CRLF and an LF working file are both "unmodified".
    # -- EVERY HOOK IN THE DIRECTORY, NOT ONLY pre-push (2026-09-24) -----
    # core.hooksPath points git at .githooks/, so git runs EVERY hook it
    # finds there -- pre-commit and post-rewrite as well. This block
    # repaired ONE file, so a CRLF pre-commit or post-rewrite would be
    # skipped silently while the clone still reported itself installed.
    # That is the identical shape of the 2026-09-01 incident this whole
    # file exists for, one hook over: reporting protected while the
    # protection has never run.
    #
    # DISCOVERED, NOT LISTED. A hand-kept list of hook names goes stale the
    # first time somebody adds a fourth -- which is exactly how this one
    # went stale at three.
    try:
        for name in sorted(os.listdir(hookdir)):
            path = os.path.join(hookdir, name)
            if not os.path.isfile(path) or name.endswith('.sample'):
                continue
            raw = open(path, 'rb').read()
            if b'\r\n' in raw:
                open(path, 'wb').write(raw.replace(b'\r\n', b'\n'))
                print('REPAIRED: .githooks/%s had CRLF endings -- git was '
                      'skipping it silently. Rewritten with LF.' % name)
            try:
                os.chmod(path, os.stat(path).st_mode | 0o111)
            except Exception:
                pass
    except Exception as e:
        print('WARNING: could not check .githooks/ line endings: %s' % e)

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
    # resolved. The wrapper is a SEPARATE claim from the python, and is where
    # this failed once: the python was fine, the shell file was not executable
    # by git, and "Gate script runs. Installed." was true while the hook was
    # dead. Both live in runs_cleanly() now, so --check asks the same questions.
    problems = runs_cleanly(repo, hookfile)
    if problems:
        for p in problems:
            print('WARNING: %s' % p)
        print('git would skip this hook silently. Do not treat this as installed.')
        return 1
    print('Gate script runs. Shell wrapper executes.')
    print('Installed.')
    print('')
    print('Verify end to end with a real push from a NON-Bash caller:')
    print('    python tools/sairn_claim.py claim <subject> <task>')
    print('A push that touches sql/ with no db/schema_snapshot.json must now be')
    print('refused through that path too, not only through a typed git push.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
