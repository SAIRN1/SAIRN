#!/usr/bin/env python3
"""tools/conflict_marker_preflight.py -- a rebase on a contested file cannot
ship an unresolved conflict, and cannot ship a BLIND side-pick either.

    python tools/conflict_marker_preflight.py            # check the working tree
    python tools/conflict_marker_preflight.py --staged   # only what is staged
    python tools/conflict_marker_preflight.py --paths a b

Exit 0 CLEAN, 1 FOUND SOMETHING, 2 COULD NOT RUN. Never 0 for "could not tell".

── THE DEFECT, AND WHY THE PUSH GATE CATCHING IT IS NOT GOOD ENOUGH ────────
2026-09-27: a `git checkout --ours` taken mid-rebase to clear a conflict shipped
SIX conflict markers into docs/tier-a-reviews.json. The push gate did catch it --
by luck, because that gate greps for markers as one of many things it does, at
the very end of the work. By then the bad resolution had been committed, carried
through the rest of the rebase, and was being reasoned about as if it were the
file's real content.

PRE-FLIGHT means at the moment of resolution, not at the end of the run. It is
the same lesson as cross-domain discipline 10 (no long run whose first check is
at the end): the Gotthard Base Tunnel's intermediate shafts exist so a 57km leap
of faith becomes several short surveyable drives. A conflict resolution is a
boundary, and this is the survey at that boundary.

── AND THE HALF A MARKER GREP CANNOT SEE, WHICH IS THE WORSE HALF ──────────
`git checkout --ours <file>` DOES NOT LEAVE MARKERS. It resolves cleanly, silently,
and throws away everything the other side changed. The six markers were the
VISIBLE symptom of a habit whose normal outcome is invisible: a file that parses,
passes every check, and is missing another session's work.

So check C compares each resolved file against BOTH stages recorded in the index.
Byte-identical to stage 2 or stage 3 means one side was taken wholesale and the
other discarded -- which is sometimes right and must never be silent. On a file
another session is actively editing, it is how their work disappears.

── THREE CHECKS, AND B IS DELIBERATELY A DIFFERENT MECHANISM ───────────────
  A  MARKERS     the conflict TRIAD in order, on masked-free raw lines
  B  PARSE       structured files must still parse (JSON, JSONL)
  C  BLIND PICK  a resolution byte-identical to one whole side

B shares no mechanism with A: a file can carry markers A misses (a marker shape
git never wrote, an encoding A read wrongly) and B still refuses it, and a file
can be corrupted in ways that are not markers at all and only B sees. Cross-domain
discipline 6 -- independence needs a structurally different method, not a second
copy of the same one. docs/tier-a-reviews.json is exactly the file where both
apply, and B would have caught it even if A had been written wrong.

── FAIL CLOSED (PR §1.11) ──────────────────────────────────────────────────
Every git invocation this makes is required, not optional. If `git` is absent, or
a command errors, or a path cannot be decoded, the answer is exit 2 with the
reason named -- never a pass. A check that skips when its dependency is missing
reports a pass it never performed.

── WIRING ──────────────────────────────────────────────────────────────────
NOT wired into .claude/settings.json here: that file is named in cc's active
claim (PR §4.3), so the hook line is left for its owner. To wire it, add to
PreToolUse on Bash, or install as .git/hooks/pre-commit:

    python tools/conflict_marker_preflight.py || exit 1

Run it by hand the moment a conflict is resolved and before `git rebase
--continue`, which is the point it exists for.
"""
import argparse
import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# BUILT FROM chr() ON PURPOSE. Written literally, this file would contain the
# very triad it looks for, and every run would report itself -- so the tool would
# need a skip-list naming itself, and a skip-list is a hole that grows. There is
# no exclusion list anywhere in this file, which is why the probe's fixtures are
# written to a temp directory at runtime rather than committed.
_LT, _EQ, _GT = chr(60), chr(61), chr(62)
OURS_MARK = _LT * 7
BASE_MARK = _EQ * 7
THEIRS_MARK = _GT * 7

TEXT_SKIP_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip',
                 '.woff', '.woff2', '.ttf', '.eot', '.jar', '.exe', '.dll'}


class CouldNotRun(Exception):
    pass


def git(*args, **kw):
    """Run git or raise CouldNotRun. There is no 'git was not available' pass."""
    try:
        r = subprocess.run(('git',) + args, cwd=REPO, capture_output=True,
                           timeout=kw.pop('timeout', 60))
    except FileNotFoundError:
        raise CouldNotRun('`git` is not on PATH, so NOTHING was checked')
    except Exception as exc:
        raise CouldNotRun('git %s did not run: %s' % (' '.join(args), exc))
    if r.returncode != 0 and not kw.get('allow_fail'):
        raise CouldNotRun('git %s exited %d: %s'
                          % (' '.join(args), r.returncode,
                             r.stderr.decode('utf-8', 'replace').strip()))
    return r.stdout.decode('utf-8', 'replace'), r.returncode


def assert_this_repo():
    """The git we are talking to must be THIS clone's git.

    ── C:/Users/marsh/.git EXISTS, AND THAT MAKES THE OBVIOUS CHECK FAIL OPEN ──
    Measured 2026-09-27: the user's HOME DIRECTORY is itself a git repository, so
    git's upward discovery succeeds from anywhere beneath it. `git rev-parse
    --git-dir` run in a scratch directory does not error -- it cheerfully returns
    C:/Users/marsh/.git, `ls-files` returns that repo's files, and a check that
    trusted it would report a confident CLEAN about a repository it was never
    pointed at. The probe caught exactly this: the fail-closed arm exited 0.

    This is the same shape as clone_name()'s cwd bug in
    tools/session_lock_check.py -- a tool that believed where it was standing
    instead of establishing it.
    """
    out, _ = git('rev-parse', '--show-toplevel')
    top = os.path.normcase(os.path.abspath(out.strip()))
    want = os.path.normcase(os.path.abspath(REPO))
    if top != want:
        raise CouldNotRun(
            'git resolved to %s, not %s. Nothing was checked against the intended '
            'clone -- git discovery walked UP and found a different repository '
            '(C:/Users/marsh/.git exists, so this succeeds from anywhere under '
            'the home directory instead of failing).' % (top, want))


def in_progress():
    """(kind, detail) -- 'rebase' / 'merge' / 'cherry-pick' / None."""
    gd, _ = git('rev-parse', '--git-dir')
    gd = os.path.join(REPO, gd.strip())
    for d, kind in (('rebase-merge', 'rebase'), ('rebase-apply', 'rebase')):
        if os.path.isdir(os.path.join(gd, d)):
            return kind, d
    for f, kind in (('MERGE_HEAD', 'merge'), ('CHERRY_PICK_HEAD', 'cherry-pick')):
        if os.path.isfile(os.path.join(gd, f)):
            return kind, f
    return None, None


def candidate_paths(args):
    """The files to check, and NEVER a silent empty set."""
    if args.paths:
        return [p.replace(os.sep, '/') for p in args.paths]
    if args.staged:
        out, _ = git('diff', '--cached', '--name-only', '--diff-filter=ACMR')
    else:
        out, _ = git('ls-files', '--modified', '--others', '--cached',
                     '--exclude-standard')
    seen, paths = set(), []
    for line in out.splitlines():
        p = line.strip()
        if not p or p in seen:
            continue
        seen.add(p)
        if os.path.splitext(p)[1].lower() in TEXT_SKIP_EXT:
            continue
        paths.append(p)
    return paths


def read_text(path):
    full = os.path.join(REPO, path)
    if not os.path.isfile(full):
        return None
    try:
        with io.open(full, 'rb') as f:
            raw = f.read()
    except OSError as exc:
        raise CouldNotRun('%s could not be read (%s) -- NOT a pass' % (path, exc))
    if b'\x00' in raw[:8000]:
        return None  # binary; check A does not apply and says so by omission
    return raw.decode('utf-8', 'replace')


# ── CHECK A: THE TRIAD, IN ORDER ────────────────────────────────────────────
# A single `<<<<<<<` is not a conflict. Documentation shows one, a test fixture
# carries one, a diff pasted into a comment has all three out of order. Requiring
# the ORDERED TRIAD -- ours, then base, then theirs, each at line start -- is what
# separates a real unresolved conflict from prose about one, and it is why this
# tool needs no skip-list.

def check_markers(path, text):
    if text is None:
        return []
    ours = base = None
    for i, line in enumerate(text.splitlines(), 1):
        s = line.rstrip('\r')
        if s.startswith(OURS_MARK):
            ours, base = i, None
        elif s.startswith(BASE_MARK) and s.strip(_EQ) == '' and ours:
            base = i
        elif s.startswith(THEIRS_MARK) and ours and base:
            return [('MARKERS', path,
                     'an unresolved conflict: %s at line %d, %s at %d, %s at %d'
                     % (OURS_MARK, ours, BASE_MARK, base, THEIRS_MARK, i))]
    return []


# ── CHECK B: DOES IT STILL PARSE ────────────────────────────────────────────
# A different mechanism from A on purpose -- see the module docstring. This is
# the check that would have refused docs/tier-a-reviews.json regardless of
# whether the marker scan was written correctly.

def check_parses(path, text):
    if text is None:
        return []
    low = path.lower()
    try:
        if low.endswith('.json'):
            json.loads(text)
        elif low.endswith('.jsonl') or low.endswith('.ndjson'):
            for n, line in enumerate(text.splitlines(), 1):
                if line.strip():
                    json.loads(line)
    except ValueError as exc:
        return [('PARSE', path, 'will not parse as %s: %s'
                 % (os.path.splitext(path)[1].lstrip('.').upper() or 'JSON', exc))]
    return []


# ── CHECK C: A WHOLE SIDE TAKEN, AND THE OTHER SIDE'S WORK DISCARDED ────────

def check_blind_pick(paths):
    """Resolutions byte-identical to one entire conflict stage.

    `git checkout --ours` and `--theirs` leave NO markers, so A and B both pass
    while the other session's changes are gone. The index still remembers both
    stages during a rebase, and after `git add` the staged blob can still be
    compared against them -- so this asks the question the marker grep cannot.

    NOT AN ERROR BY ITSELF. Taking one side whole is sometimes the correct
    resolution. It must simply never be SILENT, which is the whole difference
    between this and the habit that caused the defect.
    """
    kind, _ = in_progress()
    if kind is None:
        return []

    findings = []
    out, _ = git('diff', '--name-only', '--diff-filter=U', allow_fail=True)
    unmerged = {l.strip() for l in out.splitlines() if l.strip()}
    for p in sorted(unmerged):
        if paths and p not in paths:
            continue
        findings.append(('UNRESOLVED', p,
                         'still conflicted in the index during a %s -- resolve it '
                         'before continuing' % kind))

    # ── THE COMPARISON CANNOT COME FROM THE INDEX STAGES ────────────────────
    # The first cut read `git ls-files -u`. `git add` CLEARS those stages, so by
    # the time anyone would run a pre-flight -- after resolving, before
    # continuing -- there was nothing left to compare and the check silently
    # returned nothing. It passed every arm of the probe that mattered while
    # detecting the defect in none of them.
    #
    # HEAD and REBASE_HEAD/MERGE_HEAD survive resolution, so the two sides are
    # read from the COMMITS instead, and only where a genuine three-way conflict
    # existed: both sides changed the path relative to the merge base. A path
    # only one side touched resolves to that side legitimately and is not a
    # finding.
    other = None
    for ref in ('REBASE_HEAD', 'MERGE_HEAD', 'CHERRY_PICK_HEAD'):
        out, rc = git('rev-parse', '--verify', '--quiet', ref, allow_fail=True)
        if rc == 0 and out.strip():
            other = out.strip()
            break
    if other is None:
        raise CouldNotRun(
            'a %s is in progress but neither REBASE_HEAD, MERGE_HEAD nor '
            'CHERRY_PICK_HEAD resolves, so the two sides could not be read. '
            'Check C did NOT run -- this is not "no blind picks".' % kind)

    base, rc = git('merge-base', 'HEAD', other, allow_fail=True)
    base = base.strip() if rc == 0 else None

    def blob(ref, path):
        out, rc = git('cat-file', '-p', '%s:%s' % (ref, path), allow_fail=True)
        return out.replace('\r\n', '\n') if rc == 0 else None

    out, _ = git('diff', '--name-only', 'HEAD', other, allow_fail=True)
    for p in sorted({l.strip() for l in out.splitlines() if l.strip()}):
        if p in unmerged or (paths and p not in paths):
            continue
        cur = read_text(p)
        if cur is None:
            continue
        cur = cur.replace('\r\n', '\n')
        ours, theirs = blob('HEAD', p), blob(other, p)
        if ours is None or theirs is None or ours == theirs:
            continue
        if base is not None:
            was = blob(base, p)
            # Only ONE side changed it -- resolving to that side is correct, not
            # a blind pick. Flagging it would train people to ignore this check.
            if was is not None and (was == ours or was == theirs):
                continue
        for side, label in ((ours, 'ours'), (theirs, 'theirs')):
            if cur == side:
                findings.append(('BLIND-PICK', p, (
                    'resolved byte-identical to %s -- the other side was '
                    'discarded WHOLE, and both sides had changed it. Confirm '
                    'that is intended; on a file another session is editing it '
                    'is how their work disappears. NOTE THE INVERSION: during a '
                    'REBASE, `--ours` is the branch being rebased ONTO and '
                    '`--theirs` is your own replayed commit -- the opposite of '
                    'what the words suggest, which is half of why the blind '
                    'form is dangerous here.' % label)))
                break
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--staged', action='store_true',
                    help='check only what is staged, for a pre-commit hook')
    ap.add_argument('--paths', nargs='*', help='check these paths only')
    args = ap.parse_args(argv)

    try:
        assert_this_repo()
        kind, detail = in_progress()
        paths = candidate_paths(args)
        findings = []
        for p in paths:
            text = read_text(p)
            findings += check_markers(p, text)
            findings += check_parses(p, text)
        findings += check_blind_pick(set(paths))
    except CouldNotRun as e:
        sys.stderr.write('COULD NOT RUN -- %s\n' % e)
        sys.stderr.write('This is the THIRD STATE. It is NOT a clean pre-flight '
                         'and nothing downstream may treat it as one.\n')
        return 2

    print('CONFLICT-MARKER PRE-FLIGHT')
    print('%d path(s) examined%s.'
          % (len(paths), (' -- a %s is IN PROGRESS (%s)' % (kind, detail))
             if kind else ''))
    if not paths:
        print('')
        print('NOTHING TO CHECK is not the same as CLEAN. If that is a surprise,')
        print('the path selection is wrong, not the tree.')

    if not findings:
        print('')
        print('CLEAN -- no ordered conflict triad, every structured file parses,')
        print('and no resolution equals one whole side.')
        if not kind:
            print('No rebase/merge in progress, so check C had nothing to compare')
            print('against and proved nothing. That is a scope limit, not a pass.')
        return 0

    print('')
    for what, path, why in findings:
        print('  %-12s %s' % (what, path))
        print('               %s' % why)
    print('')
    print('DO NOT `git rebase --continue` OR COMMIT UNTIL THESE ARE SETTLED.')
    print('Resolve by keeping BOTH sides on purpose. A blind --ours/--theirs is')
    print("what put six markers in docs/tier-a-reviews.json, and its quiet")
    print('outcome -- a clean file missing another session\'s work -- is worse.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
