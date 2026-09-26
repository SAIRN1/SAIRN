#!/usr/bin/env python
"""run_gh_push_gate_probe.py -- the REST push must not be able to skip the gate.

    python tests/run_gh_push_gate_probe.py

── WHAT THIS IS ABOUT ──────────────────────────────────────────────────────
`tools/gh_push.py` pushes through the GitHub REST API. git is never invoked, so
`.githooks/pre-push` never fires -- which meant the seed gate, the Tier A
review gate, the generated-document check and every other check in
`tools/sairn_push_gate_hook.py` had no effect on that path at all. A commit
could reach origin/main having passed nothing.

AND THERE WAS A SECOND HOLE UNDERNEATH IT, which is the one these arms exist
for as much as the first: a REST push sends WORKING-TREE BYTES. Before the fix,
gh_push.py could publish content that existed in no local commit -- so even a
gate that DID run would have had nothing to judge.

The fix INVOKES the hook rather than copying its checks, and pre-flights the
working tree so the range it hands over is real. These arms drive the refusals.

── EVERY ARM IS A REFUSAL ARM, AND THAT IS THE POINT ──────────────────────
A gate is only worth what it refuses. Each case below builds a REAL throwaway
git repository, puts it in the exact state the check is about, and asserts
gh_push.py REFUSES -- plus one arm that asserts it does NOT refuse a clean
state, because a function that refuses everything passes every other arm here.

NOTHING TOUCHES THE NETWORK. `run_the_real_gate` is driven directly; the token
lookup and the GitHub calls are never reached.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import gh_push  # noqa: E402

PASS = []
FAIL = []


def check(name, ok, detail=''):
    if ok:
        PASS.append(name)
        print('  ok   %s' % name)
    else:
        FAIL.append(name)
        print('  FAIL %s\n       %s' % (name, detail))


def git(cwd, *args):
    r = subprocess.run(['git', '-C', cwd] + list(args), capture_output=True,
                       text=True, encoding='utf-8', errors='replace', timeout=120)
    return r.returncode, (r.stdout or ''), (r.stderr or '')


def make_repo(td, hook_exit=0, with_hook=True):
    """A real repo with one commit and a stub .githooks/pre-push."""
    git(td, 'init', '-q')
    git(td, 'config', 'user.email', 'probe@example.invalid')
    git(td, 'config', 'user.name', 'probe')
    io.open(os.path.join(td, 'app.html'), 'w', encoding='utf-8',
            newline='').write('<html>one</html>\n')
    if with_hook:
        os.makedirs(os.path.join(td, '.githooks'), exist_ok=True)
        # The stub RECORDS ITS STDIN, so an arm can prove the ref line git would
        # have supplied is what the hook actually received -- a hook invoked with
        # an empty stdin treats it as nothing to check, which is the exact shape
        # the real shell hook's own header warns about.
        io.open(os.path.join(td, '.githooks', 'pre-push'), 'w', encoding='utf-8',
                newline='\n').write(
            '#!/bin/sh\ncat > "$(dirname "$0")/../stdin-seen.txt"\nexit %d\n' % hook_exit)
    git(td, 'add', '-A')
    git(td, 'commit', '-q', '-m', 'one')
    rc, head, _e = git(td, 'rev-parse', 'HEAD')
    return head.strip()


def refuses(td, files, remote_sha, branch='main'):
    """(refused, exit_code, stderr_text) from run_the_real_gate."""
    err = io.StringIO()
    real_err, sys.stderr = sys.stderr, err
    try:
        gh_push.run_the_real_gate(td, files, branch, remote_sha)
        return False, 0, err.getvalue()
    except SystemExit as e:
        return True, e.code, err.getvalue()
    finally:
        sys.stderr = real_err


def main():
    print('GH_PUSH REST GATE -- the bypass path must run the same hook')
    if not (shutil.which('sh') or shutil.which('bash')):
        print('COULD NOT RUN: no sh/bash on PATH, so the hook cannot be invoked')
        print('at all and these arms would pass by never reaching it. That is a')
        print('third state, not a pass (PR 1.11).')
        return 2

    # ── A1 CONTROL FIRST. Without it, every refusal arm below is satisfied by a
    #    function that refuses unconditionally.
    with tempfile.TemporaryDirectory() as td:
        head = make_repo(td)
        refused, code, err = refuses(td, ['app.html'], head)
        check('A1 CONTROL: a clean, committed, fast-forward state is ALLOWED',
              not refused, 'refused with exit %r:\n%s' % (code, err))
        seen = os.path.join(td, '.githooks', '..', 'stdin-seen.txt')
        txt = io.open(seen, encoding='utf-8').read().strip() if os.path.isfile(seen) else ''
        parts = txt.split()
        check('A2 the hook received git\'s OWN ref-line format, 4 fields',
              len(parts) == 4 and parts[1] == head and parts[3] == head,
              'hook stdin was %r' % txt)

    # ── A3 the second hole: working-tree bytes that are in no commit ──────────
    with tempfile.TemporaryDirectory() as td:
        head = make_repo(td)
        io.open(os.path.join(td, 'app.html'), 'w', encoding='utf-8',
                newline='').write('<html>EDITED, NEVER COMMITTED</html>\n')
        refused, code, err = refuses(td, ['app.html'], head)
        check('A3 an UNCOMMITTED edit is refused -- a REST push sends the tree',
              refused and 'UNCOMMITTED' in err,
              'refused=%r exit=%r err=%s' % (refused, code, err))

    # ── A3b STAGED BUT NOT COMMITTED -- the sharpest form of the second hole ─
    #    The index is not a commit. Bytes staged and not committed exist in no
    #    reachable object, so a REST push would publish content that no reviewer
    #    and no future bisect could ever see -- and `git status --porcelain`
    #    reports it as `M ` with the M in the INDEX column, which a check
    #    written against the worktree column alone would miss.
    with tempfile.TemporaryDirectory() as td:
        head = make_repo(td)
        io.open(os.path.join(td, 'app.html'), 'w', encoding='utf-8',
                newline='').write('<html>STAGED ONLY, NEVER COMMITTED</html>' + chr(10))
        git(td, 'add', 'app.html')
        refused, code, err = refuses(td, ['app.html'], head)
        check('A3b a STAGED but uncommitted change is refused -- the index is '
              'not a commit',
              refused and 'UNCOMMITTED' in err,
              'refused=%r exit=%r err=%s' % (refused, code, err))

    # ── A4 a file git has never seen ─────────────────────────────────────────
    with tempfile.TemporaryDirectory() as td:
        head = make_repo(td)
        io.open(os.path.join(td, 'new.html'), 'w', encoding='utf-8',
                newline='').write('<html>untracked</html>\n')
        refused, code, err = refuses(td, ['app.html', 'new.html'], head)
        check('A4 an UNTRACKED file is refused and named',
              refused and 'NOT TRACKED' in err and 'new.html' in err,
              'refused=%r err=%s' % (refused, err))

    # ── A5 a remote tip this clone does not hold: could-not-tell, not a pass ─
    with tempfile.TemporaryDirectory() as td:
        make_repo(td)
        refused, code, err = refuses(td, ['app.html'], 'f' * 40)
        check('A5 a remote tip absent from this clone REFUSES rather than guessing',
              refused and 'NOT IN THIS CLONE' in err,
              'refused=%r err=%s' % (refused, err))

    # ── A6 origin ahead: the range would be wrong ────────────────────────────
    with tempfile.TemporaryDirectory() as td:
        head = make_repo(td)
        io.open(os.path.join(td, 'app.html'), 'w', encoding='utf-8',
                newline='').write('<html>two</html>\n')
        git(td, 'add', '-A')
        git(td, 'commit', '-q', '-m', 'two')
        rc, two, _e = git(td, 'rev-parse', 'HEAD')
        two = two.strip()
        git(td, 'checkout', '-q', head)          # HEAD is now BEHIND `two`
        refused, code, err = refuses(td, ['app.html'], two)
        check('A6 HEAD not descending from the remote tip is refused',
              refused and 'DOES NOT DESCEND' in err,
              'refused=%r err=%s' % (refused, err))

    # ── A7 the hook itself refusing must stop the push, with ITS exit code ───
    with tempfile.TemporaryDirectory() as td:
        head = make_repo(td, hook_exit=1)
        refused, code, err = refuses(td, ['app.html'], head)
        check('A7 a hook that exits 1 stops the push and propagates the code',
              refused and code == 1, 'refused=%r exit=%r' % (refused, code))

    # ── A8 the hook MISSING is could-not-run, never a pass ───────────────────
    #    This is the arm that matters most on a fresh clone: .git/ is not
    #    versioned and install_git_hooks.py is per-clone, so "the hook is not
    #    there" is a real state and must not read as clean.
    with tempfile.TemporaryDirectory() as td:
        head = make_repo(td, with_hook=False)
        refused, code, err = refuses(td, ['app.html'], head)
        check('A8 a MISSING .githooks/pre-push refuses (could-not-run != pass)',
              refused and 'COULD NOT RUN' in err,
              'refused=%r err=%s' % (refused, err))

    # ── A9 the gate is wired into the real script, not just defined ──────────
    #    A9 is the arm that would have caught the whole original defect: the
    #    function can be perfect and never called.
    src = io.open(os.path.join(REPO, 'tools', 'gh_push.py'), encoding='utf-8').read()
    body = src[src.index('def main('):]
    gate_at = body.find('run_the_real_gate(')
    blob_at = body.find('git/blobs')
    patch_at = body.find('"PATCH"')
    check('A9 main() CALLS the gate, and does so before any GitHub write',
          gate_at != -1 and blob_at != -1 and patch_at != -1
          and gate_at < blob_at < patch_at,
          'gate=%d blob=%d patch=%d' % (gate_at, blob_at, patch_at))

    print('\n%d passed, %d failed' % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
