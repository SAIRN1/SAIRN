#!/usr/bin/env python3
"""tests/conflict_marker_preflight_probe.py -- drive
tools/conflict_marker_preflight.py against fixtures whose right answer is known,
in both directions, including a REAL conflicted git repository built in a temp
directory.

Run:  python tests/conflict_marker_preflight_probe.py

── WHY A REAL REPO AND NOT A STUB ──────────────────────────────────────────
Check C reads the two sides of a conflict out of real git objects. A stub of that
stubs the exact thing most likely to be wrong -- which refs survive a resolution,
what `git add` clears, how a merge base behaves when only one side moved.
Cross-domain discipline 9: the real costly thing earns exhaustive verification,
and the whole value of check C is that it reads what git actually recorded. So
this builds a real repo, causes a real conflict, and resolves it the exact way
that caused the defect:

    git checkout --ours docs/tier-a-reviews.json

which leaves NO MARKERS and silently discards the other side.

── THE PROBE HAS FOUND FOUR REAL DEFECTS IN THE TOOL IT TESTS ──────────────
Recorded because a probe that never caught anything is indistinguishable from one
that cannot:

  1. CHECK C DETECTED NOTHING. It read stages from `git ls-files -u`, and `git add`
     clears those -- so at the exact moment a pre-flight runs, it had nothing to
     compare and returned clean with the defect in front of it.
  2. THE FAIL-CLOSED ARM EXITED 0. C:/Users/marsh/.git exists, so git's upward
     discovery answers about the WRONG repository from any scratch directory
     instead of failing.
  3. `--ours` IS INVERTED MID-REBASE. This file expected it to keep my side; it
     keeps the branch being rebased ONTO. Pinned as an arm below.
  4. CHECK A WAS A DUPLICATE. tools/conflict_marker_check.py already owned marker
     scanning and does it better. A is now delegated, and the arms below test the
     delegation and its FAIL-CLOSED rather than a second scanner.

── AND WHY THE FIXTURES ARE WRITTEN AT RUNTIME ─────────────────────────────
A committed fixture carrying a real conflict triad would be found by the marker
check's own sweep of this repo, and the usual answer -- a skip-list naming the
fixture -- is a hole that grows and eventually hides a real finding. Neither tool
has an exclusion list. These fixtures exist only for the length of this run.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import conflict_marker_preflight as cp  # noqa: E402


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

# Built from chr() for the same reason the tools avoid literals: a committed file
# containing the real triad would be a finding in every sweep of this repo.
_LT, _EQ, _GT = chr(60), chr(61), chr(62)
OURS, BASE, THEIRS = _LT * 7, _EQ * 7, _GT * 7

CONFLICTED = '\n'.join([
    '{', '  "reviews": [',
    '%s HEAD' % OURS,
    '    {"id": "a", "owner": "fourth"}',
    BASE,
    '    {"id": "a", "owner": "cody"}',
    '%s origin/main' % THEIRS,
    '  ]', '}'])

FAILURES = []
N = [0]


def expect(name, got, want):
    N[0] += 1
    if got != want:
        FAILURES.append('%s\n     wanted %r, got %r' % (name, want, got))
        print('  FAIL %s' % name)
    else:
        print('  ok   %s' % name)


def kinds(findings):
    return sorted({f[0] for f in findings})


def run(cwd, *args):
    r = subprocess.run(args, cwd=cwd, capture_output=True)
    return r.returncode, r.stdout.decode('utf-8', 'replace')


# ── A: DELEGATION, AND ITS FAIL-CLOSED ──────────────────────────────────────
# Check A is NOT implemented in the tool -- tools/conflict_marker_check.py owns it
# and is stronger at it (four shapes including diff3 `|||||||`, a MEASURED
# zero-false-positive baseline across 2,069 tracked files). So these arms test the
# DELEGATION, and above all what happens when the delegate is ABSENT: PR 1.11 says
# a check whose dependency is missing must name it and FAIL, never skip it and
# report the remaining checks as a pass.

def _delegate_on_fixture():
    """A real conflicted file, written into this repo for one call, then removed."""
    rel = 'docs/__probe_conflicted_delete_me.json'
    full = os.path.join(REPO, rel)
    io.open(full, 'w', encoding='utf-8', newline='\n').write(CONFLICTED + '\n')
    try:
        return cp.check_markers([rel])
    finally:
        os.remove(full)


def a_checks():
    print('A -- DELEGATION to tools/conflict_marker_check.py:')
    expect('the delegate exists (a required dependency, not an option)',
           os.path.isfile(cp.MARKER_TOOL), True)
    expect('a real conflicted file is reported THROUGH the delegate',
           kinds(_delegate_on_fixture()), ['MARKERS'])
    expect('a clean file is not reported',
           kinds(cp.check_markers(['tools/conflict_marker_preflight.py'])), [])
    expect('an empty path list asks the delegate nothing and invents nothing',
           kinds(cp.check_markers([])), [])

    # ── SCALE, WHICH EVERY OTHER ARM HERE MISSED ────────────────────────────
    # Delegation over the WHOLE working tree raised WinError 206: Windows caps a
    # command line at 32,768 chars and a clean tree is 2,644 paths. The tool
    # failed closed and was still unusable for its actual job. Every arm above
    # passes ONE path, so the first case worked, the real case did not, and
    # nothing tested the size in between. This arm is the size.
    tracked, _ = cp.git('ls-files')
    everything = [l.strip() for l in tracked.splitlines() if l.strip()]
    expect('the real tree is big enough for this arm to mean something',
           len(everything) > 500, True)
    expect('delegating over EVERY tracked file does not blow the argv limit',
           kinds(cp.check_markers(everything)), [])

    saved = cp.MARKER_TOOL
    cp.MARKER_TOOL = os.path.join(REPO, 'tools', '__no_such_marker_tool.py')
    try:
        raised = False
        try:
            cp.check_markers(['README.md'])
        except cp.CouldNotRun:
            raised = True
        expect('a MISSING delegate raises CouldNotRun -- A is never skipped',
               raised, True)
        expect('and main() turns that into exit 2, NOT 0', cp.main([]), 2)
    finally:
        cp.MARKER_TOOL = saved


# ── B: THE INDEPENDENT MECHANISM ────────────────────────────────────────────

def b_checks():
    print('')
    print('B -- PARSE, a mechanism A does not share:')
    expect('the conflicted JSON is refused by B TOO, independently of A',
           kinds(cp.check_parses('docs/tier-a-reviews.json', CONFLICTED)), ['PARSE'])
    expect('valid JSON passes',
           kinds(cp.check_parses('ok.json', '{"a": 1}')), [])
    expect('B does not judge a .md file',
           kinds(cp.check_parses('notes.md', 'not json at all {{{')), [])
    expect('a broken JSONL LINE is caught',
           kinds(cp.check_parses('r.jsonl', '{"a":1}\n{"b":\n')), ['PARSE'])
    # THE POINT OF B, and why it was kept rather than delegated too: none of
    # these are markers, and a marker scanner is structurally incapable of
    # seeing them.
    expect('JSON truncated with NO markers -- invisible to A, caught by B',
           kinds(cp.check_parses('t.json', '{"reviews": [{"id": "a"')), ['PARSE'])
    expect('a binary file is not guessed at',
           kinds(cp.check_parses('logo.png', None)), [])


# ── C: THE BLIND SIDE-PICK, IN A REAL REPO ──────────────────────────────────

def build_conflict(root):
    """A real two-branch conflict on a JSON file, left mid-rebase."""
    run(root, 'git', 'init', '-q', '-b', 'main')
    run(root, 'git', 'config', 'user.email', 'probe@example.invalid')
    run(root, 'git', 'config', 'user.name', 'probe')
    run(root, 'git', 'config', 'commit.gpgsign', 'false')
    os.makedirs(os.path.join(root, 'docs'), exist_ok=True)
    os.makedirs(os.path.join(root, 'tools'), exist_ok=True)
    for t in ('conflict_marker_preflight.py', 'conflict_marker_check.py'):
        shutil.copy(os.path.join(REPO, 'tools', t),
                    os.path.join(root, 'tools', t))
    f = os.path.join(root, 'docs', 'tier-a-reviews.json')

    def write(text):
        io.open(f, 'w', encoding='utf-8', newline='\n').write(text)

    write('{"reviews": ["base"]}\n')
    run(root, 'git', 'add', '-A')
    run(root, 'git', 'commit', '-qm', 'base')
    run(root, 'git', 'checkout', '-q', '-b', 'other')
    write('{"reviews": ["THEIR WORK -- another session obligation"]}\n')
    run(root, 'git', 'commit', '-qam', 'theirs')
    run(root, 'git', 'checkout', '-q', 'main')
    write('{"reviews": ["MY WORK"]}\n')
    run(root, 'git', 'commit', '-qam', 'ours')
    rc, _ = run(root, 'git', 'rebase', 'other')
    return f, rc


def c_checks():
    print('')
    print('C -- THE BLIND SIDE-PICK, in a real conflicted repository:')
    root = tempfile.mkdtemp(prefix='cmpf-probe-')
    saved_repo, saved_tool = cp.REPO, cp.MARKER_TOOL
    try:
        _, rc = build_conflict(root)
        if rc == 0:
            print('  FAIL the fixture rebase did NOT conflict -- nothing was tested')
            FAILURES.append('fixture rebase produced no conflict')
            N[0] += 1
            return
        cp.REPO = root
        cp.MARKER_TOOL = os.path.join(root, 'tools', 'conflict_marker_check.py')
        rel = 'docs/tier-a-reviews.json'

        expect('the in-progress rebase is detected', cp.in_progress()[0], 'rebase')

        # 1. Mid-conflict, nothing resolved yet.
        text = cp.read_text(rel)
        expect("git's OWN markers are found through the delegate",
               kinds(cp.check_markers([rel])), ['MARKERS'])
        expect('and B refuses the same file independently',
               kinds(cp.check_parses(rel, text)), ['PARSE'])
        expect('C reports it UNRESOLVED while it is still unmerged',
               kinds(cp.check_blind_pick({rel})), ['UNRESOLVED'])

        # 2. THE DEFECT ITSELF -- what was actually run on 2026-09-27.
        run(root, 'git', 'checkout', '--ours', rel)
        run(root, 'git', 'add', rel)
        after = cp.read_text(rel)
        expect('after --ours there are NO markers (A is blind here, correctly)',
               kinds(cp.check_markers([rel])), [])
        expect('and it parses cleanly (B is blind here too)',
               kinds(cp.check_parses(rel, after)), [])
        # THE INVERSION, PINNED. Mid-rebase, `--ours` keeps the branch being
        # rebased ONTO; `--theirs` is your own replayed commit. This probe was
        # written expecting the opposite and the fixture proved it wrong -- which
        # is exactly why the blind form is dangerous: it reads as "keep mine" and
        # does the reverse.
        expect('--ours mid-rebase kept the UPSTREAM side, not mine',
               ('THEIR WORK' in after, 'MY WORK' in after), (True, False))
        expect('C CATCHES IT: the resolution equals one whole side',
               kinds(cp.check_blind_pick({rel})), ['BLIND-PICK'])

        # 3. THE CONTROL. Without this, a check that flagged EVERY resolution
        #    would pass every arm above and be worthless.
        io.open(os.path.join(root, rel), 'w', encoding='utf-8',
                newline='\n').write(
            '{"reviews": ["MY WORK", "THEIR WORK -- another session obligation"]}\n')
        run(root, 'git', 'add', rel)
        expect('a real both-sides resolution is NOT flagged',
               kinds(cp.check_blind_pick({rel})), [])
    finally:
        cp.REPO, cp.MARKER_TOOL = saved_repo, saved_tool
        run(root, 'git', 'rebase', '--abort')
        shutil.rmtree(root, onerror=_rm_ro)


def d_checks():
    print('')
    print('D -- COULD NOT RUN is a third state, never a pass:')
    saved = cp.REPO
    cp.REPO = os.path.join(tempfile.gettempdir(), 'cmpf-not-a-repo-at-all')
    os.makedirs(cp.REPO, exist_ok=True)
    try:
        # C:/Users/marsh/.git EXISTS, so git discovery SUCCEEDS here and answers
        # about the home repository. assert_this_repo() is what turns that into a
        # refusal instead of a confident wrong CLEAN.
        expect('a scratch dir under $HOME exits 2, NOT 0', cp.main([]), 2)
    finally:
        cp.REPO = saved


def main():
    print('CONFLICT PRE-FLIGHT PROBE')
    print('')
    a_checks()
    b_checks()
    c_checks()
    d_checks()
    print('')
    if FAILURES:
        print('%d of %d FAILED:' % (len(FAILURES), N[0]))
        for f in FAILURES:
            print('  - %s' % f)
        return 1
    print('%d/%d passed.' % (N[0], N[0]))
    print('')
    print('WHAT THIS DOES NOT PROVE: that the tool is WIRED. It is not -- the hook')
    print('line belongs in .claude/settings.json, which cc holds. Until somebody')
    print('wires it or runs it by hand AT THE MOMENT OF RESOLUTION, this is a')
    print('correct check that nothing invokes.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
