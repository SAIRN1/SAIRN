#!/usr/bin/env python3
"""tests/conflict_marker_preflight_probe.py -- drive
tools/conflict_marker_preflight.py against fixtures whose right answer is known,
in both directions, including a REAL conflicted git repository built in a temp
directory.

Run:  python tests/conflict_marker_preflight_probe.py

── WHY A REAL REPO AND NOT A STUB ──────────────────────────────────────────
Check C reads conflict STAGES out of the git index (`git ls-files -u`, then
`git cat-file -p` on each stage blob). A stub of that is a stub of the exact
thing most likely to be wrong -- the stage numbering, the tab-separated format,
the moment the stages stop existing. Cross-domain discipline 9: the real costly
thing earns exhaustive verification, and the whole value of check C is that it
reads what git actually recorded. So the probe makes a real repo, causes a real
conflict, and resolves it the exact way that caused the defect:

    git checkout --ours docs/tier-a-reviews.json

which leaves NO MARKERS and silently discards the other side.

── AND WHY THE FIXTURES ARE WRITTEN AT RUNTIME ─────────────────────────────
A committed fixture carrying a real conflict triad would be found by the tool's
own scan of this repo, and the usual answer -- a skip-list naming the fixture --
is a hole that grows and that eventually hides a real finding. The tool has NO
exclusion list anywhere; these fixtures exist only inside a temp directory for
the length of this run. That is also why the tool builds its marker constants
from chr().
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

OURS, BASE, THEIRS = cp.OURS_MARK, cp.BASE_MARK, cp.THEIRS_MARK

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


# ── A: THE TRIAD ────────────────────────────────────────────────────────────

CONFLICTED = '\n'.join([
    '{', '  "reviews": [',
    '%s HEAD' % OURS,
    '    {"id": "a", "owner": "fourth"}',
    BASE,
    '    {"id": "a", "owner": "cody"}',
    '%s origin/main' % THEIRS,
    '  ]', '}'])

# A single marker in prose. Documentation, a commit message quoted in a comment,
# a runbook showing what a conflict looks like. Flagging this is the false
# positive that makes a team add a skip-list, and the skip-list is what later
# hides a real one.
PROSE = '\n'.join([
    '# Resolving a conflict',
    'Git writes %s HEAD above your side and %s below it.' % (OURS, THEIRS),
    'Keep both sides; never take one wholesale.'])

# All three present but NOT in conflict order -- a diff pasted into a note.
OUT_OF_ORDER = '\n'.join([
    'notes:', '%s theirs-first' % THEIRS, BASE, '%s ours-last' % OURS])

# The triad inside an otherwise valid-looking file, ours-marker indented. Git
# writes markers at line start; an indented one is prose about a conflict.
INDENTED = '\n'.join([
    'text', '    %s HEAD' % OURS, '    a', '    ' + BASE, '    b',
    '    %s other' % THEIRS])


def a_checks():
    print('A -- THE ORDERED TRIAD:')
    expect('a real unresolved conflict is FOUND',
           kinds(cp.check_markers('x.json', CONFLICTED)), ['MARKERS'])
    expect('one marker in prose is NOT a conflict (no skip-list needed)',
           kinds(cp.check_markers('README.md', PROSE)), [])
    expect('all three out of order is NOT a conflict',
           kinds(cp.check_markers('notes.md', OUT_OF_ORDER)), [])
    expect('indented markers are prose, not what git wrote',
           kinds(cp.check_markers('doc.md', INDENTED)), [])
    expect('a binary file is skipped by A rather than guessed at',
           kinds(cp.check_markers('logo.png', None)), [])


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
    # THE POINT OF B. Truncation, a bad merge, a half-written file -- none of
    # these are markers, and A is structurally incapable of seeing them.
    expect('JSON truncated with NO markers -- invisible to A, caught by B',
           kinds(cp.check_parses('t.json', '{"reviews": [{"id": "a"')), ['PARSE'])


# ── C: THE BLIND SIDE-PICK, IN A REAL REPO ──────────────────────────────────

def run(cwd, *args):
    r = subprocess.run(args, cwd=cwd, capture_output=True)
    return r.returncode, r.stdout.decode('utf-8', 'replace')


def build_conflict(root):
    """A real two-branch conflict on a JSON file, left mid-rebase."""
    run(root, 'git', 'init', '-q', '-b', 'main')
    run(root, 'git', 'config', 'user.email', 'probe@example.invalid')
    run(root, 'git', 'config', 'user.name', 'probe')
    run(root, 'git', 'config', 'commit.gpgsign', 'false')
    os.makedirs(os.path.join(root, 'docs'), exist_ok=True)
    os.makedirs(os.path.join(root, 'tools'), exist_ok=True)
    shutil.copy(os.path.join(REPO, 'tools', 'conflict_marker_preflight.py'),
                os.path.join(root, 'tools', 'conflict_marker_preflight.py'))
    f = os.path.join(root, 'docs', 'tier-a-reviews.json')

    def write(obj):
        io.open(f, 'w', encoding='utf-8', newline='\n').write(obj)

    write('{"reviews": ["base"]}\n')
    run(root, 'git', 'add', '-A')
    run(root, 'git', 'commit', '-qm', 'base')
    run(root, 'git', 'checkout', '-q', '-b', 'other')
    write('{"reviews": ["THEIR WORK -- another session\'s obligation"]}\n')
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
    try:
        f, rc = build_conflict(root)
        if rc == 0:
            print('  FAIL the fixture rebase did NOT conflict -- nothing was tested')
            FAILURES.append('fixture rebase produced no conflict')
            N[0] += 1
            return
        cp.REPO = root

        kind, _ = cp.in_progress()
        expect('the in-progress rebase is detected', kind, 'rebase')

        # 1. Mid-conflict, before any resolution: markers on disk AND unmerged.
        text = cp.read_text('docs/tier-a-reviews.json')
        expect('git\'s own markers are FOUND by A (not a synthetic fixture)',
               kinds(cp.check_markers('docs/tier-a-reviews.json', text)), ['MARKERS'])
        expect('and B refuses the same file independently',
               kinds(cp.check_parses('docs/tier-a-reviews.json', text)), ['PARSE'])
        expect('C reports it UNRESOLVED while it is still unmerged',
               kinds(cp.check_blind_pick({'docs/tier-a-reviews.json'})), ['UNRESOLVED'])

        # 2. THE DEFECT ITSELF. This is what was actually run on 2026-09-27.
        #    It leaves a clean, parseable file with no markers -- and the other
        #    session's line is simply gone.
        run(root, 'git', 'checkout', '--ours', 'docs/tier-a-reviews.json')
        run(root, 'git', 'add', 'docs/tier-a-reviews.json')
        after = cp.read_text('docs/tier-a-reviews.json')
        expect('after --ours there are NO markers (A is blind here, correctly)',
               kinds(cp.check_markers('docs/tier-a-reviews.json', after)), [])
        expect('and it parses cleanly (B is blind here too)',
               kinds(cp.check_parses('docs/tier-a-reviews.json', after)), [])
        # THE INVERSION, PINNED. During a REBASE `--ours` is the branch being
        # rebased ONTO (here: `other`), and `--theirs` is your own replayed
        # commit. This probe was written expecting the opposite and the fixture
        # proved it wrong -- which is precisely why a blind `--ours` mid-rebase
        # is dangerous: it reads as "keep mine" and does the reverse.
        expect('--ours mid-rebase kept the UPSTREAM side, not mine (the inversion)',
               ('THEIR WORK' in after, 'MY WORK' in after), (True, False))
        expect('C CATCHES IT: the resolution equals one whole side',
               kinds(cp.check_blind_pick({'docs/tier-a-reviews.json'})), ['BLIND-PICK'])

        # 3. A genuine resolution keeping both sides is NOT flagged. Without this
        #    arm, a check that flagged every resolution would pass every arm
        #    above and be useless.
        io.open(os.path.join(root, 'docs', 'tier-a-reviews.json'), 'w',
                encoding='utf-8', newline='\n').write(
            '{"reviews": ["MY WORK", "THEIR WORK -- another session\'s obligation"]}\n')
        run(root, 'git', 'add', 'docs/tier-a-reviews.json')
        expect('a real both-sides resolution is NOT flagged (the control)',
               kinds(cp.check_blind_pick({'docs/tier-a-reviews.json'})), [])
    finally:
        cp.REPO = REPO
        run(root, 'git', 'rebase', '--abort')
        shutil.rmtree(root, ignore_errors=True)


# ── FAIL-CLOSED ─────────────────────────────────────────────────────────────

def d_checks():
    print('')
    print('D -- COULD NOT RUN is a third state, never a pass:')
    saved = cp.REPO
    cp.REPO = os.path.join(tempfile.gettempdir(), 'cmpf-not-a-repo-at-all')
    os.makedirs(cp.REPO, exist_ok=True)
    try:
        rc = cp.main([])
        expect('outside a git repository the tool exits 2, NOT 0', rc, 2)
    finally:
        cp.REPO = saved


def main():
    print('CONFLICT-MARKER PRE-FLIGHT PROBE')
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
    print('wires it or runs it by hand at the moment of resolution, this is a')
    print('correct check that nothing invokes.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
