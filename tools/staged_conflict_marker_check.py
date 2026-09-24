"""tools/staged_conflict_marker_check.py -- refuse a COMMIT that stages a
conflict marker, regardless of how it got staged.

    python tools/staged_conflict_marker_check.py            # --cached, the index
    python tools/staged_conflict_marker_check.py --worktree # what is on disk

Wired into `.githooks/prepare-commit-msg`, NOT pre-commit. That is not a style
choice: `git rebase --continue` -- the operation that has produced every
instance of this defect -- does not fire pre-commit at all. The hook file
carries the measured firing table.

── WHY THIS EXISTS AND WHY IT IS NOT THE PUSH GATE ────────────────────────
The push gate already refuses a conflict marker, and its message names the
cause exactly: "`git add -A` during a rebase is what put these here, and it
cannot tell a resolved file from an unmerged one." That gate is correct and it
is the LAST line, not the first -- by the time it fires the marker is in a
commit, the commit is in the history being pushed, and clearing it means
rewriting or reverting.

MEASURED, AND IT IS WHY THIS IS A SEPARATE CHECK: the push gate's own text
records that a marker "has reached origin/main three times in five days -- once
into a Tier A source file." On 2026-09-24 a retry loop in this repo staged one
a fourth time. Every instance had the same shape: a blanket `git add -A` while
a rebase was mid-conflict.

THE FIX IS TO REFUSE AT THE COMMIT, because that is the moment the marker
becomes durable and the moment it is cheapest to undo -- nothing has been
rewritten yet, the conflict is still in front of the person, and `git reset`
costs nothing.

── WHAT COUNTS AS A MARKER, AND WHAT DELIBERATELY DOES NOT ────────────────
Only the three git writes, at the START of a line, in a STAGED blob:

    <<<<<<<     =======     >>>>>>>

A `=======` underline is ordinary markdown and this file would be unusable if
it refused one, so `=======` alone is NOT a finding: it is counted only when
the same file also carries a `<<<<<<<` or a `>>>>>>>`. That pairing is what
makes it a merge artefact rather than a heading rule.

── WHAT IT CANNOT SEE ─────────────────────────────────────────────────────
A marker inside a string literal that a program writes on purpose -- this file
itself contains the three sequences and is excluded BY PATH rather than by
guessing, because a content rule that tried to tell "quoted" from "real" would
be the regex-over-a-construct mistake three tools in this repo have already
paid for. Any other file that legitimately contains one has to say so here.
"""
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OPEN_RE = re.compile(r'^<{7}(?:\s|$)')
SPLIT_RE = re.compile(r'^={7}\s*$')
CLOSE_RE = re.compile(r'^>{7}(?:\s|$)')

# Files that contain the sequences ON PURPOSE. By path, never by content
# sniffing -- see the header. A new entry here is a decision somebody makes,
# which is the point.
ALLOWED = {
    'tools/staged_conflict_marker_check.py',
    'tools/sairn_push_gate_hook.py',
    'tools/sairn_rebase_resolve.py',
}


def staged_paths():
    r = subprocess.run(['git', '-C', REPO, 'diff', '--cached', '--name-only',
                        '--diff-filter=ACMR'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if r.returncode != 0:
        return None
    return [p for p in (r.stdout or '').split('\n') if p.strip()]


def staged_blob(path):
    r = subprocess.run(['git', '-C', REPO, 'show', ':' + path],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return r.stdout if r.returncode == 0 else None


def worktree_blob(path):
    try:
        with open(os.path.join(REPO, path), encoding='utf-8', errors='replace') as fh:
            return fh.read()
    except OSError:
        return None


def scan_text(text):
    opens, splits, closes = [], [], []
    for i, line in enumerate(text.split('\n'), 1):
        if OPEN_RE.match(line):
            opens.append(i)
        elif CLOSE_RE.match(line):
            closes.append(i)
        elif SPLIT_RE.match(line):
            splits.append(i)
    if not opens and not closes:
        # A bare `=======` is a markdown underline. Not a finding on its own,
        # and saying so is the difference between a usable check and one people
        # turn off.
        return []
    return ([('<<<<<<<', n) for n in opens]
            + [('=======', n) for n in splits]
            + [('>>>>>>>', n) for n in closes])


def main(argv):
    worktree = '--worktree' in argv
    paths = staged_paths()
    if paths is None:
        print('COULD NOT RUN: git diff --cached failed. A commit check that '
              'cannot read the index has not checked anything, and that is not '
              'a pass.')
        return 2
    findings = []
    for p in paths:
        if p in ALLOWED:
            continue
        text = worktree_blob(p) if worktree else staged_blob(p)
        if text is None:
            print('COULD NOT RUN: %s is staged and could not be read.' % p)
            return 2
        for marker, line in scan_text(text):
            findings.append((p, line, marker))
    if not findings:
        return 0

    print('')
    print('REFUSED: this commit stages an unresolved conflict marker.')
    print('')
    for p, line, marker in findings[:40]:
        print('  %s:%d  %s' % (p, line, marker))
    if len(findings) > 40:
        print('  ... and %d more' % (len(findings) - 40))
    print('')
    print('A MARKER MEANS THE FILE IS NOT FINISHED. The push gate already')
    print('refuses these, and by then the marker is in a commit and clearing it')
    print('means a rewrite. This refuses at the moment it becomes durable and')
    print('the moment it is cheapest to undo.')
    print('')
    print('THE USUAL CAUSE IS `git add -A` DURING A CONFLICTED REBASE, which')
    print('cannot tell a resolved file from an unmerged one. Resolve the file,')
    print('check BOTH sides survived where both were real, and stage it by name.')
    print('')
    print('For the two ledgers, use the resolver rather than resolving by hand:')
    print('    python tools/sairn_rebase_resolve.py')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
