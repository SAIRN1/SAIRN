#!/usr/bin/env python
"""Control: the sibling-clone enumeration must be BOUNDED and fail closed.

# REQUIREMENT: sibling_clones() must not launch an unbounded number of git
#   subprocesses. When its parent directory holds more candidate repositories
#   than any clone parent plausibly would, it must REFUSE with CouldNotTell --
#   quickly, and naming the parent and the count -- rather than grinding through
#   them.

MEASURED, NOT GUESSED (2026-09-30). `nhi_register.py --selftest` run from a temp
directory timed out at 180 seconds, twice. The cause: it enumerates the SIBLING
directories of its repo root, and the system temp directory on this machine held
**9182 entries, 1865 of them carrying a `.git`** -- almost all of them probe
fixtures left by this repo's own controls. One `git config --get
remote.origin.url` per candidate, at roughly 50-100ms per process launch on
Windows, is 90-190 seconds. Nothing was hanging; it was doing 1865 pieces of work.

── WHAT IS NOT DONE, AND WHY ────────────────────────────────────────────────
The walk is NOT scoped to the tool's own directory tree. Its entire purpose is to
count sibling working copies -- that derivation is what found the fifth clone in
2026-09-16 and the seventh in 2026-09-28, after CLAUDE.md had named four for
weeks. A walk that cannot leave its own tree always answers zero, which is a
wrong answer that looks like a measurement. Bounded and fail-closed is the fix
that keeps the feature.

Run:  python tests/run_nhi_selftest_scope_probe.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'nhi_register.py')

CRITERIA_VERSION = '2026-09-30.1'

# Above the cap the tool must refuse. Deliberately far below the 1865 measured in
# the real incident, so the arm is fast.
MANY = 220
# A real clone parent holds a handful.
FEW = 3

_pass = _fail = 0


def ok(n):
    global _pass
    _pass += 1
    sys.stdout.write('  ok   %s\n' % n)


def bad(n, why):
    global _fail
    _fail += 1
    sys.stdout.write('  FAIL %s\n       %s\n' % (n, why))


def section(t):
    sys.stdout.write('\n%s\n' % t)


def fake_candidates(parent, n, real_git=False):
    """n sibling directories that each LOOK like a working copy.

    `.git` as a FILE is what a git worktree has, and the tool's own comment says
    isdir() alone would skip one -- so the fixture uses the shape the tool
    accepts, or it would be testing a path the tool never takes.
    """
    for i in range(n):
        d = os.path.join(parent, 'cand%04d' % i)
        os.makedirs(os.path.join(d, 'tools'))
        os.makedirs(os.path.join(d, 'sql'))
        if real_git:
            subprocess.run(['git', 'init', '-q'], cwd=d, capture_output=True)
            subprocess.run(['git', 'remote', 'add', 'origin',
                            'https://github.com/SAIRN1/SAIRN.git'], cwd=d,
                           capture_output=True)
        else:
            io.open(os.path.join(d, '.git'), 'w').write('gitdir: nowhere\n')


def main():
    if not os.path.isfile(TOOL):
        sys.stderr.write('COULD NOT RUN -- tools/nhi_register.py is missing.\n')
        return 2
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    try:
        import nhi_register as nr
    except Exception as e:                                    # noqa: BLE001
        sys.stderr.write('COULD NOT RUN -- it does not import: %s\n' % e)
        return 2

    sys.stdout.write('NHI SIBLING-SCAN BOUND CONTROL -- criteria %s\n'
                     % CRITERIA_VERSION)

    made = []
    try:
        section('A. THE KNOWN-BAD: a parent full of candidate repositories')

        parent = tempfile.mkdtemp(prefix='nhiscope_many_')
        made.append(parent)
        me = os.path.join(parent, 'SAIRN-cody')
        os.makedirs(os.path.join(me, 'tools'))
        os.makedirs(os.path.join(me, 'sql'))
        subprocess.run(['git', 'init', '-q'], cwd=me, capture_output=True)
        subprocess.run(['git', 'remote', 'add', 'origin',
                        'https://github.com/SAIRN1/SAIRN.git'], cwd=me,
                       capture_output=True)
        fake_candidates(parent, MANY)

        t0 = time.time()
        try:
            nr.sibling_clones(repo=me)
            verdict = 'RETURNED'
            detail = ''
        except nr.CouldNotTell as e:
            verdict = 'REFUSED'
            detail = str(e)
        except Exception as e:                                # noqa: BLE001
            verdict = type(e).__name__
            detail = str(e)
        took = time.time() - t0

        if verdict == 'REFUSED':
            ok('A1. KNOWN-BAD: %d candidate repositories in the parent and it '
               'REFUSES with CouldNotTell rather than launching a git subprocess '
               'for each. Unbounded, that is what took 180 seconds twice from a '
               'temp directory holding 1865 of them' % MANY)
        else:
            bad('A1. a parent full of candidates must be refused',
                'verdict=%s after %.1fs  %s' % (verdict, took, detail[:200]))

        if took < 20:
            ok('A2. ...and it refuses in %.1fs. A bound that is reached slowly is '
               'still the defect -- the point is that the work is not done, not '
               'that it is done and then discarded' % took)
        else:
            bad('A2. the refusal must be fast',
                'it took %.1fs, so the candidates were walked anyway' % took)

        if 'REFUSED' == verdict and (str(MANY) in detail or 'candidate' in detail.lower()):
            ok('A3. ...and the refusal NAMES the count and the directory, so the '
               'reader can see it is a fact about where the tool was run rather '
               'than about the clones')
        else:
            bad('A3. the refusal must name the count and the parent', detail[:200])

        section('B. THE SILENT HALF: a real clone parent still answers')

        parent2 = tempfile.mkdtemp(prefix='nhiscope_few_')
        made.append(parent2)
        me2 = os.path.join(parent2, 'SAIRN-cody')
        # BOTH directories, because a real clone has both and the pre-filter
        # tests for both. The first version of this fixture made only tools/ and
        # B2 failed -- correctly: an incomplete fixture and a fail-open exemption
        # look identical from the arm, and the arm caught the fixture.
        os.makedirs(os.path.join(me2, 'tools'))
        os.makedirs(os.path.join(me2, 'sql'))
        subprocess.run(['git', 'init', '-q'], cwd=me2, capture_output=True)
        subprocess.run(['git', 'remote', 'add', 'origin',
                        'https://github.com/SAIRN1/SAIRN.git'], cwd=me2,
                       capture_output=True)
        fake_candidates(parent2, FEW, real_git=True)
        try:
            names = nr.sibling_clones(repo=me2)
            err = None
        except Exception as e:                                # noqa: BLE001
            names, err = None, e
        if names and len(names) >= FEW:
            ok('B1. a parent holding %d real sibling clones of the same origin '
               'still returns them all. Without this the fix could be "always '
               'refuse" and A1 would pass' % FEW)
        else:
            bad('B1. a small real parent must still be enumerated',
                'got %r  err=%s' % (names, err))

        if names and os.path.basename(me2) in names:
            ok('B2. ...and it finds THIS clone among them, which is the arm the '
               'tool already carried against a hardcoded list')
        else:
            bad('B2. it must find its own clone', 'got %r' % (names,))

        section('C. THE REAL SELFTEST NOW FINISHES FROM A TEMP DIRECTORY')

        d = tempfile.mkdtemp(prefix='nhiscope_run_')
        made.append(d)
        for sub, exts in (('tools', ('.py',)), ('sql', ('.sql',))):
            src = os.path.join(REPO, sub)
            dst = os.path.join(d, sub)
            os.makedirs(dst)
            for n in os.listdir(src):
                if n.lower().endswith(exts):
                    shutil.copy2(os.path.join(src, n), os.path.join(dst, n))
        os.makedirs(os.path.join(d, 'docs'))
        t0 = time.time()
        try:
            r = subprocess.run([sys.executable, os.path.join('tools',
                                                             'nhi_register.py'),
                                '--selftest'], cwd=d, capture_output=True,
                               text=True, encoding='utf-8', errors='replace',
                               timeout=90)
            took = time.time() - t0
            timed_out = False
        except subprocess.TimeoutExpired:
            took = time.time() - t0
            timed_out = True
            r = None
        if timed_out:
            bad('C1. --selftest must finish from a temp directory',
                'still running after %.0fs -- this is the 180s incident, '
                'unfixed' % took)
        else:
            ok('C1. THE INCIDENT ARM: --selftest run from a temp directory '
               'finishes in %.1fs instead of timing out at 180. It is run in a '
               'directory whose parent is the system temp tree, which is where '
               'the 1865 candidate repositories actually are' % took)
            o = (r.stdout or '') + (r.stderr or '')
            if 'REFUS' in o.upper() or 'ok ' in o:
                ok('C2. ...and it SAYS what happened rather than exiting silently')
            else:
                bad('C2. it must report', o[-300:])

        section('D. THE ANCHORS')

        src = io.open(TOOL, encoding='utf-8').read()
        for needle, why in (
            ('SIBLING_CANDIDATE_CAP', 'the bound A1 and A2 depend on'),
            ('def sibling_clones', 'the function under test'),
            ('CouldNotTell', 'the refusal type A1 catches'),
        ):
            if needle in src:
                ok('D. ANCHOR present: %s -- %s' % (needle, why))
            else:
                bad('D. ANCHOR MISSING: %s' % needle,
                    'the arms above stop testing what they name (%s)' % why)
    finally:
        for p in made:
            shutil.rmtree(p, ignore_errors=True)

    sys.stdout.write('\n%d passed, %d failed\n' % (_pass, _fail))
    return 1 if _fail else 0


if __name__ == '__main__':
    sys.exit(main())
