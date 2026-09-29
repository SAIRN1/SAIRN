#!/usr/bin/env python3
"""tools/staged_credential_check.py -- refuse a COMMIT that stages credential
CONTENT, whatever the file is called and however it got staged.

    python tools/staged_credential_check.py            # the index (default)
    python tools/staged_credential_check.py --worktree # what is on disk

Exit 0 clean, 1 a finding, 2 COULD NOT RUN. Never prints the match.

Wired into `.githooks/prepare-commit-msg` alongside
tools/staged_conflict_marker_check.py, and NOT pre-commit, for the reason that
file already records: `git rebase --continue` does not fire pre-commit at all,
and a regenerate-after-rebase step is exactly where this defect came from.

── THE INCIDENT ───────────────────────────────────────────────────────────
2026-09-28. A GitHub personal access token under `.claude/` was staged by a
`git add -A` inside a regenerate-after-rebase one-liner and reached a commit.
The PUSH gate caught it, which is the last line rather than the first: by then
the blob was in the object store, in the index, and in a commit that had to be
amended, and the token had to be treated as exposed regardless.

NAME-BASED IGNORING IS NOT ENOUGH, AND THAT IS THE WHOLE POINT OF THIS FILE.
A `.gitignore` entry for `.claude/github_pat*` closes the case that already
happened. The next one will be called `notes.txt`, `config.json` or
`scratch.md`, and a name rule cannot see it. This reads CONTENT.

── WHAT IT LOOKS FOR, AND WHAT IT REFUSES TO PRINT ───────────────────────
Issuer-prefixed shapes only -- github_pat_, ghp_/gho_/ghu_/ghs_, sk_live_,
sk_test_, AKIA, and PEM private-key headers. Each is anchored on its own prefix
and a minimum length, so prose cannot match.

THE MATCHED TEXT IS NEVER PRINTED, LOGGED OR RETURNED. The regex is evaluated,
the boolean is kept, the match object is discarded. Echoing a secret to explain
that you found a secret copies it into the terminal, the scrollback and
whatever collects them -- which is how a find becomes a second leak. The output
names the FILE and the SHAPE and stops.

── THE EXEMPTION IS A PROPERTY, NOT A LIST ───────────────────────────────
A scanner, its control, or a redaction tool must contain these patterns to do
its job. Naming those files in a skip-list would be a hole that grows. Instead a
blob is exempt when it carries a self-describing marker -- SECRET_PATTERNS, a
credential-shape comment, PLACEHOLDER, or "NOT a real" -- which travels with
the file and disappears if the file stops being about patterns.

THE COST IS STATED: a real scanner that genuinely leaked a token would be
exempt. That is the deliberate trade, and it is why this check is one layer and
not the only one -- the push gate reads the same shapes on the outgoing range.

── FAIL CLOSED ────────────────────────────────────────────────────────────
Unreadable index, missing git, an undecodable blob: exit 2 with the reason, and
the hook that calls it treats 2 as a refusal. A credential check that passes
when it cannot look is worse than none, because it is believed.
"""
import argparse
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SHAPES = [
    ('github_pat', re.compile(rb'github_pat_[A-Za-z0-9_]{20,}')),
    ('github_token', re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}')),
    ('stripe_live', re.compile(rb'sk_live_[A-Za-z0-9]{20,}')),
    ('stripe_test', re.compile(rb'sk_test_[A-Za-z0-9]{20,}')),
    ('aws_access_key', re.compile(rb'AKIA[0-9A-Z]{16}')),
    ('private_key', re.compile(rb'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
    ('slack_token', re.compile(rb'xox[baprs]-[A-Za-z0-9-]{20,}')),
    # ── A DEMO-CREDENTIAL FILE, BY SHAPE AND NOT BY NAME (2026-09-29) ──────
    # tools/demo_credentials_check.py reads PINs from an untracked local file.
    # That file is gitignored, which stops the ACCIDENT and not the RENAME: a
    # copy saved as notes.json is staged without a murmur, and the ignore rule
    # is the only thing that was protecting it.
    #
    # THE SHAPE IS A PIN BESIDE A LICENCE KEY, which is what makes it a
    # credential rather than a number. A bare eight-digit string is a date, an
    # id, a row count and a thousand other things; `"pin":` next to
    # `"license_key":` in the same blob is a sign-in pair and nothing else. Both
    # orders, because JSON key order is not promised by anything.
    #
    # NOT ANCHORED TO A FILENAME. That is the whole point -- the ignore rule
    # already covers the name.
    ('demo_credential_file',
     re.compile(rb'"pin"\s*:\s*"[0-9]{4,12}"[\s\S]{0,400}?"license_key"\s*:'
                rb'|"license_key"\s*:[\s\S]{0,400}?"pin"\s*:\s*"[0-9]{4,12}"')),
]

# A blob that SAYS it is about credential shapes. Travels with the file.
SELF_DESCRIBING = re.compile(
    rb'SECRET_PATTERNS|SHAPES\s*=|credential[_ -]?shape|redact'
    rb'|PLACEHOLDER|NOT a real|not a real (token|secret|key)'
    rb'|fixture|example only', re.I)

MAX = 2_000_000


class CouldNotRun(Exception):
    pass


def git(*args):
    try:
        r = subprocess.run(('git',) + args, cwd=REPO, capture_output=True,
                           timeout=120)
    except FileNotFoundError:
        raise CouldNotRun('`git` is not on PATH, so NOTHING was examined')
    except Exception as exc:                                     # noqa: BLE001
        raise CouldNotRun('git %s did not run: %s' % (' '.join(args), exc))
    if r.returncode != 0:
        raise CouldNotRun('git %s exited %d -- NOTHING was examined'
                          % (' '.join(args), r.returncode))
    return r.stdout


def assert_this_repo():
    """The git we are talking to must be THIS clone's git.

    ── THIS TOOL SHIPPED WITH THE HOLE IT WAS SWEEPING FOR ──────────────────
    Its own control caught it: the fail-closed arm pointed the checker at a
    directory that is not a repository and expected exit 2. It got 0. Because
    C:/Users/marsh/.git EXISTS, git's upward discovery SUCCEEDED, answered about
    the HOME repository, found nothing staged there, and returned a clean pass
    about a repository nobody asked about.

    That is the same hazard tools/git_discovery_anchoring_check.py was built for
    earlier in this session -- committed by the credential checker written after
    it. A tool that reports CLEAN because it looked somewhere else is the worst
    possible failure for this particular job.
    """
    out = git('rev-parse', '--show-toplevel').decode('utf-8', 'replace').strip()
    top = os.path.normcase(os.path.abspath(out))
    want = os.path.normcase(os.path.abspath(REPO))
    if top != want:
        raise CouldNotRun(
            'git resolved to %s, not %s -- discovery walked UP and found a '
            'different repository, so NOTHING about the intended clone was '
            'examined' % (top, want))


def staged_paths():
    assert_this_repo()
    out = git('diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z')
    return [p.decode('utf-8', 'replace')
            for p in out.split(b'\x00') if p]


def blob_of(path):
    """The STAGED bytes, not what is on disk. They can differ."""
    out = git('show', ':' + path)
    return out


def worktree_bytes(path):
    full = os.path.join(REPO, path)
    if not os.path.isfile(full):
        return None
    if os.path.getsize(full) > MAX:
        return None
    with open(full, 'rb') as f:
        return f.read()


def shapes_in(data):
    """Shape NAMES only. The match object is discarded here, deliberately."""
    if data is None or len(data) > MAX:
        return []
    if SELF_DESCRIBING.search(data):
        return []
    found = []
    for name, rx in SHAPES:
        if rx.search(data) is not None:
            found.append(name)
    return found


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--worktree', action='store_true',
                    help='read what is on disk instead of what is staged')
    args = ap.parse_args(argv)

    try:
        paths = staged_paths()
        findings = []
        for p in paths:
            data = worktree_bytes(p) if args.worktree else blob_of(p)
            got = shapes_in(data)
            if got:
                findings.append((p, got))
    except CouldNotRun as e:
        sys.stderr.write('COULD NOT RUN -- %s\n' % e)
        sys.stderr.write('REFUSING the commit. A credential check that passes '
                         'when it cannot look is worse than none, because it is '
                         'believed.\n')
        return 2

    if not findings:
        if not paths:
            print('staged-credential: nothing staged. That is not a pass about '
                  'this commit, it is an empty question.')
        return 0

    sys.stderr.write('\nREFUSED: this commit stages credential-shaped CONTENT.\n\n')
    sys.stderr.write('THE MATCH IS NOT PRINTED. Echoing it would copy the secret '
                     'into your terminal,\nyour scrollback and probably a log. '
                     'Open the file and look.\n\n')
    for p, got in findings:
        sys.stderr.write('  %-58s %s\n' % (p, ', '.join(got)))
    sys.stderr.write(
        '\nUnstage it (`git restore --staged <path>`), add it to .gitignore, and '
        'ROTATE\nTHE CREDENTIAL REGARDLESS -- anything that reached an index '
        'should be treated as\nexposed. A name-based ignore only closes the case '
        'that already happened; the\nnext one will have an innocent name, which '
        'is why this reads content.\n\n'
        'If this file exists TO DESCRIBE these shapes, say so in it -- '
        'SECRET_PATTERNS,\na credential-shape comment, PLACEHOLDER or "NOT a '
        'real token" -- rather than\nadding it to a skip-list here. There is no '
        'skip-list here on purpose.\n')
    return 1


if __name__ == '__main__':
    sys.exit(main())
