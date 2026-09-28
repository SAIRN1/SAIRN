#!/usr/bin/env python3
"""tools/conflict_marker_preflight.py -- the half of a bad conflict resolution
that leaves NO MARKERS: a whole side taken and the other side's work discarded.

    python tools/conflict_marker_preflight.py            # the working tree
    python tools/conflict_marker_preflight.py --paths a b

Exit 0 CLEAN, 1 FOUND SOMETHING, 2 COULD NOT RUN. Never 0 for "could not tell".

── THIS TOOL ALMOST SHIPPED AS A DUPLICATE, AND THAT IS RECORDED HERE RATHER
── THAN QUIETLY FIXED ──────────────────────────────────────────────────────
It was first written with its own marker scanner. `tools/conflict_marker_check.py`
HAS EXISTED SINCE 2026-09-15, is already a push gate, and is STRICTLY STRONGER at
that job: four marker shapes including diff3 `|||||||` (which my version missed
entirely), anchored at column zero, with a MEASURED zero-false-positive baseline
across 2,069 tracked files, plus --outgoing and --json. I built a weaker second
copy because I did not read docs/TOOLING-INVENTORY.md first, which is the one step
this platform's own rules put before building any checker.

So the marker half is DELEGATED to that tool, not reimplemented. What is left is
the part it says it cannot do -- and its header says so in as many words:

    "A conflict resolved WRONGLY. A file with no markers can still have had the
     wrong side kept, and nothing mechanical can tell."

The first clause is right. The last clause is too strong, and check C is the
counter-example: a resolution BYTE-IDENTICAL to one entire side, on a path where
both sides changed, is mechanically detectable. Not every wrong resolution -- a
hand-merge that drops one line is still invisible -- but the blind `--ours` /
`--theirs` form, which is the one that caused the damage, is not.

── THE DEFECT ──────────────────────────────────────────────────────────────
2026-09-27: a `git checkout --ours` taken mid-rebase put six conflict markers
into docs/tier-a-reviews.json. The markers were the VISIBLE symptom. `--ours`
normally leaves no markers at all: it resolves cleanly, parses cleanly, passes
the push gate, and another session's work is simply gone.

AND `--ours` IS INVERTED DURING A REBASE. It keeps the branch you are rebasing
ONTO; `--theirs` is your own replayed commit. This file's probe was written
expecting the opposite and the fixture proved it wrong. That inversion is half of
why the blind form is dangerous here: it reads as "keep mine" and does the
reverse.

── WHAT THIS ADDS, AND NOTHING ELSE ────────────────────────────────────────
  A  MARKERS     DELEGATED to tools/conflict_marker_check.py. Absent => exit 2.
  B  PARSE       structured files must still parse. A different mechanism from A
                 (discipline 6): it catches a truncated or half-merged JSON with
                 no markers in it, which A is structurally incapable of seeing.
  C  BLIND PICK  a resolution byte-identical to one whole side, where BOTH sides
                 had changed the path. THE NEW ONE.

── FAIL CLOSED (PR §1.11) ──────────────────────────────────────────────────
Check A's delegate is a REQUIRED dependency. If tools/conflict_marker_check.py is
missing or will not run, this exits 2 and names it -- it does not skip check A and
report the other two as a pass. That is the single most common defect shape on
this platform and wrapping the call in `if os.path.isfile(...)` would commit it.

── WIRING ──────────────────────────────────────────────────────────────────
NOT wired: the hook line belongs in .claude/settings.json, which cc holds under an
active claim (PR §4.3). Run it by hand the moment a conflict is resolved and
BEFORE `git rebase --continue`, which is the point it exists for -- the push gate
already runs the marker half at the end, and the end is too late to be a
pre-flight.
"""
import argparse
import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKER_TOOL = os.path.join(REPO, 'tools', 'conflict_marker_check.py')


class CouldNotRun(Exception):
    pass


def git(*args, **kw):
    """Run git or raise CouldNotRun. There is no 'git was not available' pass."""
    allow_fail = kw.pop('allow_fail', False)
    try:
        r = subprocess.run(('git',) + args, cwd=REPO, capture_output=True,
                           timeout=60)
    except FileNotFoundError:
        raise CouldNotRun('`git` is not on PATH, so NOTHING was checked')
    except Exception as exc:
        raise CouldNotRun('git %s did not run: %s' % (' '.join(args), exc))
    if r.returncode != 0 and not allow_fail:
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
    C:/Users/marsh/.git, `ls-files` answers with THAT repository's files, and a
    check that trusted it would print a confident CLEAN about a repository it was
    never pointed at. This tool's own probe caught exactly that: the fail-closed
    arm exited 0.

    Same shape as clone_name()'s cwd bug in tools/session_lock_check.py -- a tool
    that believed where it was standing instead of establishing it. Swept
    platform-wide by tools/git_discovery_anchoring_check.py.
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
    for d in ('rebase-merge', 'rebase-apply'):
        if os.path.isdir(os.path.join(gd, d)):
            return 'rebase', d
    for f, kind in (('MERGE_HEAD', 'merge'), ('CHERRY_PICK_HEAD', 'cherry-pick')):
        if os.path.isfile(os.path.join(gd, f)):
            return kind, f
    return None, None


def candidate_paths(args):
    if args.paths:
        return [p.replace(os.sep, '/') for p in args.paths]
    out, _ = git('ls-files', '--modified', '--others', '--cached',
                 '--exclude-standard')
    seen, paths = set(), []
    for line in out.splitlines():
        p = line.strip()
        if p and p not in seen:
            seen.add(p)
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
        return None
    return raw.decode('utf-8', 'replace')


# ── CHECK A: DELEGATED, AND A REQUIRED DEPENDENCY ───────────────────────────

def check_markers(paths):
    """Ask tools/conflict_marker_check.py. Its absence is exit 2, not a skip."""
    if not os.path.isfile(MARKER_TOOL):
        raise CouldNotRun(
            'tools/conflict_marker_check.py is MISSING, so the marker half of '
            'this pre-flight DID NOT RUN. Check A is not optional and is not '
            'reimplemented here -- that tool owns the measured zero-false-'
            'positive baseline and the diff3 marker shape. Restore it.')
    if not paths:
        return []
    # ── THE PATH LIST MUST BE CHUNKED, AND THE PROBE COULD NOT SEE WHY ──────
    # Passing the whole working tree as argv raised WinError 206, "The filename or
    # extension is too long": Windows caps a command line at 32,768 characters and
    # a clean tree here is 2,644 paths. The tool FAILED CLOSED and reported COULD
    # NOT RUN rather than a pass, which is the right behaviour -- and it was still
    # unusable for its actual job.
    #
    # IT WAS INVISIBLE TO THE PROBE FOR THE SAME REASON THE DELEGATION INTRODUCED
    # IT: every probe arm passes ONE path. The first case worked, the real case did
    # not, and nothing in between tested the size. That is the shape
    # tools/second_pass_coverage_scan.py exists to find, landing in the tool
    # committed beside it.
    #
    # Chunked by MEASURED BUDGET rather than a round number of files, because path
    # lengths vary and a fixed count is the same guess as a fixed window.
    findings, chunk, budget = [], [], 0
    batches = []
    for p in paths:
        if chunk and budget + len(p) + 3 > 24000:
            batches.append(chunk)
            chunk, budget = [], 0
        chunk.append(p)
        budget += len(p) + 3
    if chunk:
        batches.append(chunk)

    for batch in batches:
        try:
            r = subprocess.run(
                [sys.executable, MARKER_TOOL, '--json', '--files'] + list(batch),
                cwd=REPO, capture_output=True, timeout=300)
        except Exception as exc:
            raise CouldNotRun('tools/conflict_marker_check.py did not run over a '
                              'batch of %d path(s): %s' % (len(batch), exc))
        try:
            got = json.loads(r.stdout.decode('utf-8', 'replace'))
        except ValueError:
            raise CouldNotRun(
                'tools/conflict_marker_check.py --json did not return JSON (exit '
                '%d) for a batch of %d path(s). Check A produced no answer for '
                'that batch and a PARTIAL scan is NOT a pass: %s'
                % (r.returncode, len(batch),
                   r.stderr.decode('utf-8', 'replace')[:200]))
        if got.get('unreadable'):
            raise CouldNotRun('the marker check could not read %d file(s): %s'
                              % (len(got['unreadable']), got['unreadable'][:2]))
        findings += [('MARKERS', h['file'],
                      'unresolved %s marker at line %d -- %s'
                      % (h['kind'], h['line'], h['text'].strip()))
                     for h in got.get('findings', [])]
    return findings


# ── CHECK B: A MECHANISM A DOES NOT SHARE ───────────────────────────────────

def check_parses(path, text):
    """Structured files must still parse.

    Kept rather than delegated because the marker check reads bytes and looks for
    four line shapes -- it is structurally incapable of seeing a JSON truncated
    mid-object, a half-applied hand merge, or an encoding mangled on the way in.
    None of those are markers and all of them are unfinished files.
    """
    if text is None:
        return []
    low = path.lower()
    try:
        if low.endswith('.json'):
            json.loads(text)
        elif low.endswith('.jsonl') or low.endswith('.ndjson'):
            for line in text.splitlines():
                if line.strip():
                    json.loads(line)
        else:
            return []
    except ValueError as exc:
        return [('PARSE', path, 'will not parse: %s' % exc)]
    return []


# ── CHECK C: A WHOLE SIDE TAKEN, AND THE OTHER SIDE'S WORK DISCARDED ────────

def check_blind_pick(paths):
    """Resolutions byte-identical to one entire side of a real three-way conflict.

    ── THE COMPARISON CANNOT COME FROM THE INDEX STAGES ────────────────────
    The first cut read `git ls-files -u`. `git add` CLEARS those stages, so by the
    moment a pre-flight is actually run -- after resolving, before continuing --
    there was nothing left to compare and this returned clean with the defect in
    front of it. Its probe caught that; nothing else would have.

    HEAD and REBASE_HEAD/MERGE_HEAD survive resolution, so the two sides are read
    from the COMMITS. And only where a GENUINE three-way conflict existed: both
    sides changed the path relative to the merge base. A path only one side
    touched resolves to that side legitimately, and flagging it would train
    people to ignore this check -- which is the failure mode that matters most
    for a check nothing yet invokes.

    NOT AN ERROR BY ITSELF. Taking one side whole is sometimes the right
    resolution. It must simply never be SILENT.
    """
    kind, _ = in_progress()
    if kind is None:
        return []

    findings = []
    out, _ = git('diff', '--name-only', '--diff-filter=U', allow_fail=True)
    unmerged = {l.strip() for l in out.splitlines() if l.strip()}
    for p in sorted(unmerged):
        if not paths or p in paths:
            findings.append(('UNRESOLVED', p,
                             'still conflicted in the index during a %s -- '
                             'resolve it before continuing' % kind))

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
            if was is not None and (was == ours or was == theirs):
                continue  # only one side changed it; resolving to that side is right
        for side, label in ((ours, 'ours'), (theirs, 'theirs')):
            if cur == side:
                findings.append(('BLIND-PICK', p, (
                    'resolved byte-identical to %s -- the other side was '
                    'discarded WHOLE, and both sides had changed it. Confirm '
                    'that is intended; on a file another session is editing it '
                    'is how their work disappears. NOTE THE INVERSION: during a '
                    'REBASE `--ours` is the branch being rebased ONTO and '
                    '`--theirs` is your own replayed commit -- the opposite of '
                    'what the words suggest.' % label)))
                break
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--paths', nargs='*', help='check these paths only')
    args = ap.parse_args(argv)

    try:
        assert_this_repo()
        kind, detail = in_progress()
        paths = candidate_paths(args)
        findings = check_markers(paths)
        for p in paths:
            findings += check_parses(p, read_text(p))
        findings += check_blind_pick(set(paths))
    except CouldNotRun as e:
        sys.stderr.write('COULD NOT RUN -- %s\n' % e)
        sys.stderr.write('This is the THIRD STATE. It is NOT a clean pre-flight '
                         'and nothing downstream may treat it as one.\n')
        return 2

    print('CONFLICT PRE-FLIGHT (markers delegated to conflict_marker_check.py)')
    print('%d path(s)%s.' % (len(paths),
                             (' -- a %s is IN PROGRESS (%s)' % (kind, detail))
                             if kind else ''))
    if not paths:
        print('')
        print('NOTHING TO CHECK is not the same as CLEAN. If that is a surprise,')
        print('the path selection is wrong, not the tree.')

    if not findings:
        print('')
        print('CLEAN -- no markers, every structured file parses, and no')
        print('resolution equals one whole side.')
        if not kind:
            print('No rebase/merge in progress, so CHECK C HAD NOTHING TO COMPARE')
            print('AGAINST and proved nothing. That is a scope limit, not a pass --')
            print('this tool is only meaningful mid-operation.')
        return 0

    print('')
    for what, path, why in findings:
        print('  %-12s %s' % (what, path))
        print('               %s' % why)
    print('')
    print('DO NOT `git rebase --continue` OR COMMIT UNTIL THESE ARE SETTLED.')
    print('Keep BOTH sides on purpose. A blind --ours/--theirs is what put six')
    print('markers in docs/tier-a-reviews.json, and its QUIET outcome -- a clean,')
    print("parseable file missing another session's work -- is the worse half.")
    return 1


if __name__ == '__main__':
    sys.exit(main())
