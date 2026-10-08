#!/usr/bin/env python3
"""tests/run_staged_credential_probe.py -- the KNOWN-BAD control for
tools/staged_credential_check.py: a token-shaped file with an INNOCENT NAME,
staged, must be refused.

Run:  python tests/run_staged_credential_probe.py

-- THE POINT OF THE INNOCENT NAME -----------------------------------------
The 2026-09-28 incident was a file called `github_pat_*.txt`, and the fix
everyone reaches for first is a .gitignore rule on that name. That closes the
case that already happened. THE NEXT ONE WILL BE CALLED `notes.txt`. Arm 1
stages a token inside a file named exactly that, so the check can only pass by
reading content.

-- NO REAL CREDENTIAL, AND NO LITERAL ONE EITHER --------------------------
Every fixture is ASSEMBLED AT RUNTIME from a prefix and filler, so this file
contains no credential and no credential-shaped literal. That is not only
hygiene: writing a literal PEM header here was REFUSED by the platform's own
write-time credential guard, which is the correct behaviour and is worth
recording -- a control for a credential check must not itself be a file nobody
can save.

The probe asserts on the SHAPE NAMES the checker returns, never on the text it
matched. The checker's whole contract is that the match is discarded, and a
control that printed it would defeat the property it verifies.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import staged_credential_check as C  # noqa: E402


def _rm_ro(fn, path, _exc):
    """rmtree onerror: clear the read-only bit and retry once.

    git marks loose object files READ-ONLY and Windows will not unlink a
    read-only file, so `ignore_errors=True` leaves the object store behind and
    says nothing. Measured 2026-10-07: a cleanup that swallowed those refusals
    left 4,047 files, 38 of them read-only, in one abandoned clone.
    """
    import os as _os
    try:
        _os.chmod(path, 0o700)
        fn(path)
    except Exception:                                   # noqa: BLE001
        pass

FAILURES = []
N = [0]

# Assembled, never written down. The filler is repeated letters.
_DASH = b'-' * 5
FAKE = {
    'github_pat': b'github' + b'_pat_' + b'1' * 22 + b'_' + b'A' * 20,
    'github_token': b'ghp' + b'_' + b'B' * 36,
    'stripe_live': b'sk' + b'_live_' + b'C' * 24,
    'aws_access_key': b'AK' + b'IA' + b'D' * 16,
    'private_key': _DASH + b'BEGIN RSA PRIVATE KEY' + _DASH,
    'slack_token': b'xoxb' + b'-' + b'E' * 24,
}


def expect(name, got, want):
    N[0] += 1
    if got != want:
        FAILURES.append('%s -- wanted %r, got %r' % (name, want, got))
        print('  FAIL %s' % name)
    else:
        print('  ok   %s' % name)


def run(cwd, *args):
    return subprocess.run(args, cwd=cwd, capture_output=True)


def build():
    root = tempfile.mkdtemp(prefix='stagedcred-')
    os.makedirs(os.path.join(root, 'tools'))
    run(root, 'git', 'init', '-q', '-b', 'main')
    run(root, 'git', 'config', 'user.email', 'p@e.invalid')
    run(root, 'git', 'config', 'user.name', 'probe')
    io.open(os.path.join(root, 'README.md'), 'w').write('seed' + chr(10))
    run(root, 'git', 'add', '-A')
    run(root, 'git', 'commit', '-qm', 'seed')
    return root


def stage(root, rel, data):
    p = os.path.join(root, rel.replace('/', os.sep))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'wb') as f:
        f.write(data)
    run(root, 'git', 'add', '--', rel)


def check(root, worktree=False):
    saved = C.REPO
    C.REPO = root
    try:
        return C.main(['--worktree'] if worktree else [])
    finally:
        C.REPO = saved


def main():
    print('STAGED-CREDENTIAL PROBE -- an innocent NAME must not help')
    root = build()
    try:
        print('')
        print('1. THE KNOWN-BAD -- a token in a file called notes.txt')
        stage(root, 'notes.txt',
              b'meeting notes token: ' + FAKE['github_pat'] + b' thanks')
        expect('the commit is REFUSED on content, not on the name',
               check(root), 1)

        print('')
        print('2. THE CONTROL -- ordinary staged text is allowed')
        run(root, 'git', 'restore', '--staged', 'notes.txt')
        os.remove(os.path.join(root, 'notes.txt'))
        stage(root, 'docs/plan.md', b'# plan -- nothing unusual here at all.')
        expect('an ordinary file passes', check(root), 0)

        print('')
        print('3. every shape is recognised')
        for name, blob in sorted(FAKE.items()):
            got = C.shapes_in(b'prefix ' + blob + b' suffix')
            expect('  %-16s is detected' % name, name in got, True)

        print('')
        print('4. a file that DESCRIBES the shapes is exempt BY ITS CONTENT')
        exempt = (b'# SECRET_PATTERNS used by the scanner PATTERN = ' + FAKE['github_pat'])
        expect('a self-describing scanner is not a finding',
               C.shapes_in(exempt), [])
        expect('  ... and removing the marker makes it a finding again',
               C.shapes_in(b'x = ' + FAKE['github_pat']) != [], True)

        print('')
        print('5. THE STAGED BYTES ARE WHAT IS CHECKED, not what is on disk')
        stage(root, 'config.json', b'{"ok": true}')
        with open(os.path.join(root, 'config.json'), 'wb') as f:
            f.write(b'{"t": ' + FAKE['stripe_live'] + b'}')
        expect('a clean STAGED blob passes even when disk is dirty',
               check(root), 0)
        expect('and --worktree sees the disk copy and refuses',
               check(root, worktree=True), 1)

        print('')
        print('6. FAIL CLOSED -- an unreadable repository is 2, not 0')
        broken = tempfile.mkdtemp(prefix='stagedcred-broken-')
        try:
            expect('a non-repository exits 2', check(broken), 2)
        finally:
            shutil.rmtree(broken, ignore_errors=True)

        print('')
        print('7. THE MATCH IS NEVER RETURNED')
        got = C.shapes_in(b'token ' + FAKE['github_pat'])
        expect('shapes_in returns NAMES only', got, ['github_pat'])
        expect('  ... and no returned element contains the value',
               any(FAKE['github_pat'].decode() in s for s in got), False)
    finally:
        shutil.rmtree(root, onerror=_rm_ro)

    print('')
    if FAILURES:
        print('%d of %d FAILED:' % (len(FAILURES), N[0]))
        for f in FAILURES:
            print('  - %s' % f)
        return 1
    print('%d/%d passed.' % (N[0], N[0]))
    print('')
    print('WHAT THIS DOES NOT PROVE: that the shape list is complete. A bare API')
    print('key, a password or a connection string has no issuer prefix and is')
    print('invisible to the checker AND to this control, because both are built')
    print('from the same list. Zero findings is not proof of no secrets.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
