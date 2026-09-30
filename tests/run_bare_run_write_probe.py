#!/usr/bin/env python
"""Control for tools/bare_run_write_check.py -- built before it was believed.

# REQUIREMENT: the bare-run sweep must detect a tool that writes with no
#   arguments, must NOT flag one that writes only behind a flag, and must exit
#   2 COULD NOT RUN rather than 0 whenever it could not actually measure --
#   no scratch repo, a dirty tree, no tools found, or a tool that never
#   finished.

Every arm builds a THROWAWAY git repo with synthetic tools in it, so the arms
test the checker rather than the state of this repo on the day they run. The
checker's whole job is to distinguish "did not write" from "could not tell", and
a fixture is the only way to drive the second one on purpose.

Run:  python tests/run_bare_run_write_probe.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(REPO, 'tools', 'bare_run_write_check.py')

CRITERIA_VERSION = '2026-09-30.1'

_pass = _fail = 0


def ok(name):
    global _pass
    _pass += 1
    sys.stdout.write('  ok   %s\n' % name)


def bad(name, why):
    global _fail
    _fail += 1
    sys.stdout.write('  FAIL %s\n       %s\n' % (name, why))


def section(t):
    sys.stdout.write('\n%s\n' % t)


def git(cwd, *a):
    return subprocess.run(('git',) + a, cwd=cwd, capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def fixture(tools, commit=True):
    """A throwaway repo containing tools/<name> for each (name, body)."""
    d = tempfile.mkdtemp(prefix='barerun_')
    os.makedirs(os.path.join(d, 'tools'))
    io.open(os.path.join(d, 'tracked.txt'), 'w', encoding='utf-8').write('seed\n')
    for name, body in tools:
        io.open(os.path.join(d, 'tools', name), 'w', encoding='utf-8',
                newline='\n').write(body)
    git(d, 'init', '-q')
    git(d, 'config', 'user.email', 'probe@example.invalid')
    git(d, 'config', 'user.name', 'probe')
    if commit:
        git(d, 'add', '-A')
        git(d, 'commit', '-qm', 'fixture')
    return d


def run_check(repo, *extra):
    r = subprocess.run([sys.executable, CHECK, '--repo', repo] + list(extra),
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=180)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


# ── the synthetic tools ──────────────────────────────────────────────────────
WRITES_BARE = (
    'import io, sys\n'
    'if "--help" in sys.argv:\n'
    '    print("usage: writes_bare [--write]")\n'
    '    sys.exit(0)\n'
    'io.open("generated_by_bare_run.txt", "w").write("mutated\\n")\n'
    'print("wrote the document")\n'
)
WRITES_ONLY_WITH_FLAG = (
    'import io, sys\n'
    'if "--write" in sys.argv:\n'
    '    io.open("generated_on_request.txt", "w").write("asked for\\n")\n'
    '    print("wrote")\n'
    'else:\n'
    '    print("REPORT ONLY -- would write generated_on_request.txt; pass --write")\n'
)
WRITES_ON_HELP = (
    'import io, sys\n'
    'if "--help" in sys.argv:\n'
    '    io.open("written_while_explaining_itself.txt", "w").write("x\\n")\n'
    '    print("usage: ...")\n'
    '    sys.exit(0)\n'
    'print("report only")\n'
)
MODIFIES_TRACKED = (
    'import io\n'
    'io.open("tracked.txt", "a").write("appended by a bare run\\n")\n'
)
HANGS = (
    'import time\n'
    'time.sleep(600)\n'
)
CLEAN = (
    'print("REPORT ONLY -- nothing written")\n'
)


def main():
    if not os.path.isfile(CHECK):
        sys.stderr.write('tools/bare_run_write_check.py is missing -- the '
                         'control cannot run and that is not a pass.\n')
        return 2
    sys.stdout.write('BARE-RUN SWEEP CONTROL -- criteria %s\n' % CRITERIA_VERSION)

    made = []
    try:
        section('A. IT DETECTS A BARE RUN THAT WRITES')

        d = fixture([('a_writes_bare.py', WRITES_BARE),
                     ('b_clean.py', CLEAN)])
        made.append(d)
        code, o = run_check(d)
        if code == 1 and 'WRITES(bare)' in o and 'a_writes_bare.py' in o:
            ok('A1. KNOWN-BAD: a tool that writes a new file on a bare run is '
               'reported and the exit is 1')
        else:
            bad('A1. KNOWN-BAD: a bare run that writes must be reported',
                'exit=%s\n%s' % (code, o[-900:]))

        if 'generated_by_bare_run.txt' in o:
            ok('A1b. ...and the PATH it wrote is named, so the report is '
               'actionable rather than a count')
        else:
            bad('A1b. the written path must be named', o[-500:])

        d = fixture([('a_modifies_tracked.py', MODIFIES_TRACKED)])
        made.append(d)
        code, o = run_check(d)
        if code == 1 and 'a_modifies_tracked' in o:
            ok('A2. KNOWN-BAD: MODIFYING a tracked file counts too -- the '
               'incident that prompted this rewrote three documents that '
               'already existed, so an untracked-file-only check would have '
               'missed it entirely')
        else:
            bad('A2. a modified tracked file must be detected',
                'exit=%s\n%s' % (code, o[-700:]))

        section('B. THE SILENT HALF -- it does not flag a well-behaved tool')

        d = fixture([('b_flagged.py', WRITES_ONLY_WITH_FLAG),
                     ('b_clean.py', CLEAN)])
        made.append(d)
        code, o = run_check(d)
        if code == 0 and 'WRITES(bare)' not in o:
            ok('B1. a tool that writes ONLY behind --write is not flagged, and '
               'the sweep exits 0. Without this the checker could be "flag '
               'everything" and A1 would still pass')
        else:
            bad('B1. a flag-gated writer must not be flagged',
                'exit=%s\n%s' % (code, o[-700:]))

        section('C. --help IS ITS OWN COLUMN')

        d = fixture([('c_help_writes.py', WRITES_ON_HELP)])
        made.append(d)
        code, o = run_check(d)
        if code == 1 and 'WRITES(--help)' in o:
            ok('C1. KNOWN-BAD: a tool that writes while printing its own usage '
               'is reported separately. "--help" is the one invocation nobody '
               'reads as a command')
        else:
            bad('C1. a write on --help must be reported', 'exit=%s\n%s' % (code, o[-700:]))

        section('D. COULD NOT RUN IS A THIRD STATE AND IS NEVER A PASS')

        d = fixture([('d_hangs.py', HANGS), ('d_clean.py', CLEAN)])
        made.append(d)
        code, o = run_check(d, '--timeout', '3')
        if code == 2 and 'COULD NOT RUN' in o and 'd_hangs' in o:
            ok('D1. THE ARM THAT MATTERS: a tool that never finishes is COULD '
               'NOT RUN and the sweep exits 2. Folding it into "did not write" '
               'would report a tool nobody measured as clean')
        else:
            bad('D1. a hanging tool must exit 2, not 0',
                'exit=%s\n%s' % (code, o[-800:]))

        d = tempfile.mkdtemp(prefix='barerun_nogit_')
        made.append(d)
        os.makedirs(os.path.join(d, 'tools'))
        io.open(os.path.join(d, 'tools', 'x.py'), 'w').write(CLEAN)
        code, o = run_check(d)
        if code == 2 and 'COULD NOT RUN' in o:
            ok('D2. a target that is not a git repository is COULD NOT RUN -- '
               'without git there is no way to tell what a tool wrote, and '
               '"nothing detected" would be the wrong answer')
        else:
            bad('D2. a non-git target must exit 2', 'exit=%s\n%s' % (code, o[-500:]))

        d = fixture([('e_clean.py', CLEAN)])
        made.append(d)
        io.open(os.path.join(d, 'left_behind.txt'), 'w').write('dirt\n')
        code, o = run_check(d)
        if code == 2 and 'dirty' in o.lower():
            ok('D3. a tree that is ALREADY dirty is refused. A change the sweep '
               'did not cause is indistinguishable from one it did, which makes '
               'the result unattributable rather than merely wrong')
        else:
            bad('D3. a dirty tree must be refused', 'exit=%s\n%s' % (code, o[-500:]))

        d = fixture([('e_clean.py', CLEAN)])
        made.append(d)
        code, o = run_check(d, '--only', 'does_not_exist.py')
        if code == 2:
            ok('D4. a sweep that matched NO tool exits 2. "Nothing writes" over '
               'an empty population is a measurement that did not happen, and '
               'this repo has published that shape before')
        else:
            bad('D4. an empty population must exit 2', 'exit=%s\n%s' % (code, o[-400:]))

        section('E. IT REFUSES TO RUN WHERE RUNNING IT IS THE DAMAGE')

        code, o = run_check(REPO)
        if code == 2 and 'REFUS' in o.upper():
            ok('E1. pointed at THIS clone it refuses. The tool executes every '
               'tool it finds; in a working clone that is the defect it detects, '
               'performed 274 times')
        else:
            bad('E1. it must refuse a working clone', 'exit=%s\n%s' % (code, o[-500:]))

        # And the refusal must be about the PATH SHAPE, not about this one path,
        # or a sixth clone would not be covered.
        import re as _re
        src = io.open(CHECK, encoding='utf-8').read()
        m = _re.search(r"REAL_CLONE_RX = re\.compile\((.+)\)", src)
        if m and 'SAIRN-' in m.group(1):
            ok('E2. the refusal is a PATH-SHAPE rule (Documents/SAIRN-*), not a '
               'hardcoded list of the clones that existed today. The clone '
               'registry in CLAUDE.md was wrong for weeks after a fifth '
               'appeared; a list here would inherit that')
        else:
            bad('E2. the clone refusal must be a path-shape rule',
                'REAL_CLONE_RX not found or does not match the clone shape')

        section('F. THE ANCHORS')

        for needle, why in (
            ("'--repo'", 'the option the arms drive it with'),
            ('WRITES(bare)', 'the string A1 and A2 match on'),
            ('WRITES(--help)', 'the string C1 matches on'),
            ('COULD NOT RUN', 'the third state D1, D2 and D4 match on'),
        ):
            if needle in src:
                ok('F. ANCHOR present: %s -- %s' % (needle, why))
            else:
                bad('F. ANCHOR MISSING: %s' % needle,
                    'the arms above would stop testing the tool and pass '
                    'against nothing (%s)' % why)
    finally:
        for d in made:
            shutil.rmtree(d, ignore_errors=True)

    sys.stdout.write('\n%d passed, %d failed\n' % (_pass, _fail))
    return 1 if _fail else 0


if __name__ == '__main__':
    sys.exit(main())
