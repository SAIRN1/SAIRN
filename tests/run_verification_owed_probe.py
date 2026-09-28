#!/usr/bin/env python3
"""tests/run_verification_owed_probe.py -- the KNOWN-BAD control for
tools/verification_owed_report.py: a commit saying a live run is owed, with no
follow-up, MUST appear.

Run:  python tests/run_verification_owed_probe.py

── WHY THIS NEEDS A CONTROL MORE THAN MOST ───────────────────────────────
The tool currently reports ZERO still-owed. A report of zero is the single
easiest output to produce by accident: a phrase regex that stopped matching, a
clearance rule that is too generous, or a git format that changed all produce it,
and all three look identical to "the debt is paid".

ITS FIRST RUN WAS EXACTLY THAT FAILURE. Overlap was computed on the raw file
list, and docs/defect-density-register.json is touched by almost every commit on
this platform -- so ANY later commit mentioning a live run cleared EVERY open
debt. Six of eight "cleared" lines rested on it. Arm 3 plants that case
specifically.

── A REAL REPOSITORY, NOT A STUB ─────────────────────────────────────────
The tool reads `git log --name-only` with a custom format. Stubbing that stubs
the part most likely to break, so the probe builds a real repository and makes
real commits whose messages carry the real phrases.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import verification_owed_report as V  # noqa: E402

FAILURES = []
N = [0]


def expect(name, got, want):
    N[0] += 1
    if got != want:
        FAILURES.append('%s\n     wanted %r, got %r' % (name, want, got))
        print('  FAIL %s' % name)
    else:
        print('  ok   %s' % name)


def run(cwd, *args, **kw):
    env = dict(os.environ)
    env.update({'GIT_AUTHOR_DATE': kw.get('when', '2026-09-28T12:00:00'),
                'GIT_COMMITTER_DATE': kw.get('when', '2026-09-28T12:00:00')})
    subprocess.run(args, cwd=cwd, capture_output=True, env=env)


def commit(root, path, body, when='2026-09-28T12:00:00'):
    full = os.path.join(root, path.replace('/', os.sep))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    io.open(full, 'a', encoding='utf-8', newline='\n').write('x\n')
    run(root, 'git', 'add', '-A', when=when)
    run(root, 'git', 'commit', '-q', '-m', body, when=when)


def build():
    root = tempfile.mkdtemp(prefix='vowed-')
    run(root, 'git', 'init', '-q', '-b', 'main')
    run(root, 'git', 'config', 'user.email', 'p@e.invalid')
    run(root, 'git', 'config', 'user.name', 'probe')
    run(root, 'git', 'config', 'commit.gpgsign', 'false')
    return root


def analyse(root, days=3650):
    saved = V.REPO
    V.REPO = root
    try:
        return V.analyse(days)
    finally:
        V.REPO = saved


def owed_shas(rows):
    # The commit TYPE is enough to identify a fixture and cannot be
    # mangled by a slice, which is what the first version of this helper
    # did -- it sliced here AND in every expectation, so four arms failed
    # on their own arithmetic rather than on the tool.
    return sorted(r['subject'].split(':')[0] for r in rows if not r['cleared_by'])


def main():
    print('VERIFICATION-OWED PROBE -- a debt with no follow-up must appear')
    root = build()
    try:
        # ── 1. THE PLAIN CASE ────────────────────────────────────────────
        print('')
        print('1. a commit saying a live run is owed, and nothing after it')
        commit(root, 'api/thing.js',
               'fix(thing): close the gap\n\nLIVE VERIFICATION IS STILL OWED: '
               'the arms are in-process.')
        rows = analyse(root)
        expect('it is reported as still owed', owed_shas(rows), ['fix(thing)'])

        # ── 2. A REAL FOLLOW-UP CLEARS IT ────────────────────────────────
        print('')
        print('2. THE CONTROL -- a later commit on the SAME file clears it')
        commit(root, 'api/thing.js',
               'verify(thing): live-verified against the deployed endpoint',
               when='2026-09-28T13:00:00')
        rows = analyse(root)
        expect('the debt is cleared', owed_shas(rows), [])

        # ── 3. THE FALSE CLEARANCE THE FIRST VERSION SHIPPED ─────────────
        print('')
        print('3. a live run on an UNRELATED file must NOT clear a debt')
        commit(root, 'api/other.js',
               'fix(other): something else\n\nLive verification is still owed '
               'here too.', when='2026-09-28T14:00:00')
        commit(root, 'api/unrelated.js',
               'verify(unrelated): live-verified, observed values recorded',
               when='2026-09-28T15:00:00')
        rows = analyse(root)
        expect('the unrelated live run does NOT clear it',
               owed_shas(rows), ['fix(other)'])

        # ── 4. THE BOOKKEEPING FALSE CLEARANCE, PLANTED ──────────────────
        print('')
        print('4. sharing only docs/defect-density-register.json clears NOTHING')
        commit(root, 'docs/defect-density-register.json',
               'chore(register): a record\n\nlive-verified',
               when='2026-09-28T16:00:00')
        rows = analyse(root)
        expect('the register touch does NOT clear the open debt',
               owed_shas(rows), ['fix(other)'])

        # ── 5. PROSE ABOUT WORK IS NOT WORK ──────────────────────────────
        print('')
        print('5. a claim entry quoting the phrase owes nothing')
        commit(root, '.claude/claims/fourth.json',
               'chore(claims): fourth claims the verification-owed register -- '
               'commits whose message says live verification is owed',
               when='2026-09-28T17:00:00')
        rows = analyse(root)
        expect('the claim commit is not counted as a debt',
               owed_shas(rows), ['fix(other)'])

        # ── 6. CITING THE SHA CLEARS IT ──────────────────────────────────
        print('')
        print('6. a later commit CITING the owing sha clears it')
        out = subprocess.run(['git', 'log', '--format=%H', '-n', '20'],
                             cwd=root, capture_output=True)
        shas = out.stdout.decode().split()
        owing = [s for s in shas][-3]   # the fix(other) commit
        commit(root, 'docs/note.md',
               'chore(note): recorded the run for %s' % owing[:8],
               when='2026-09-28T18:00:00')
        rows = analyse(root)
        expect('citing the sha clears the debt', owed_shas(rows), [])

        # ── 7. FAIL CLOSED ───────────────────────────────────────────────
        print('')
        print('7. a repository git cannot log is COULD NOT RUN, not "no debts"')
        # THE FIRST VERSION OF THIS ARM WAS WRONG: it used --days 0, and
        # `git log --since=0.days` still returns today's commits, so nothing
        # raised and the arm failed on its own premise rather than on the tool.
        # An EMPTY repository is the real case -- git log exits non-zero with
        # no commits, and the tool must say COULD NOT RUN rather than report a
        # clean zero.
        empty = build()
        try:
            raised = False
            try:
                analyse(empty)
            except V.CouldNotRun:
                raised = True
            expect('an unloggable repository raises CouldNotRun', raised, True)
        finally:
            shutil.rmtree(empty, ignore_errors=True)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print('')
    if FAILURES:
        print('%d of %d FAILED:' % (len(FAILURES), N[0]))
        for f in FAILURES:
            print('  - %s' % f)
        return 1
    print('%d/%d passed.' % (N[0], N[0]))
    print('')
    print('WHAT THIS DOES NOT PROVE: that the phrase lists are complete. A commit')
    print('owing a live run in words the regex does not know is invisible to the')
    print('tool AND to this probe, because both are built from the same list.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
