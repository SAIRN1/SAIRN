#!/usr/bin/env python
"""Known-bad control for the report-only default in tools/nhi_register.py.

# REQUIREMENT: a bare `python tools/nhi_register.py` must not write
#   docs/NHI-REGISTER.md. Writing requires --write. And the bare run must still
#   answer the question it was being run for -- whether the document is stale --
#   or the flag has only moved the cost of finding out.

WHY. `python tools/nhi_register.py` with no arguments wrote the document. Running
a tool with no arguments is how you ask it what it is, and here it was the same
keystroke as telling it to go: one such run in this repo rewrote three generated
documents, and tools/bare_run_write_check.py then found 22 tools with the same
shape. This is the one of the 22 whose owner is derivable from the claim record,
which is why it is the one fixed here.

THE ARMS DRIVE A COPY, NOT THIS REPO. Each arm works in a throwaway clone of
tools/ + docs/ so the known-bad arm can DELIBERATELY leave the document stale and
watch what a bare run does to it. Running these arms against the live repo would
be the defect they test for.

Run:  python tests/run_nhi_register_write_flag_probe.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL_REL = os.path.join('tools', 'nhi_register.py')
DOC_REL = os.path.join('docs', 'NHI-REGISTER.md')

CRITERIA_VERSION = '2026-09-30.1'

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


def sandbox():
    """A throwaway tree with everything nhi_register.py reads, and nothing else.

    SELECTIVE, not a copytree of three directories: docs/ alone is hundreds of
    files and copying it made this control take minutes per arm. The tool reads
    tools/*.py (it imports secrets_inventory), sql/*.sql (for `create role`) and
    exactly one file under docs/.
    """
    d = tempfile.mkdtemp(prefix='nhiflag_')
    for sub, exts in (('tools', ('.py',)), ('sql', ('.sql',))):
        src = os.path.join(REPO, sub)
        dst = os.path.join(d, sub)
        os.makedirs(dst)
        for n in os.listdir(src):
            if n.lower().endswith(exts):
                shutil.copy2(os.path.join(src, n), os.path.join(dst, n))
    os.makedirs(os.path.join(d, 'docs'))
    live = os.path.join(REPO, DOC_REL)
    if os.path.isfile(live):
        shutil.copy2(live, os.path.join(d, DOC_REL))
    return d


def run(root, *args):
    r = subprocess.run([sys.executable, TOOL_REL] + list(args), cwd=root,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=180)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def read(root):
    try:
        return io.open(os.path.join(root, DOC_REL), encoding='utf-8',
                       newline='').read()
    except OSError:
        return None


def main():
    if not os.path.isfile(os.path.join(REPO, TOOL_REL)):
        sys.stderr.write('tools/nhi_register.py is missing -- COULD NOT RUN, '
                         'not a pass.\n')
        return 2
    sys.stdout.write('NHI REGISTER WRITE-FLAG CONTROL -- criteria %s\n'
                     % CRITERIA_VERSION)

    made = []
    try:
        section('A. THE KNOWN-BAD: a STALE document must survive a bare run')

        d = sandbox()
        made.append(d)
        # Make the document deliberately wrong. Before the fix, a bare run
        # silently repaired this -- which is the same act as silently rewriting
        # three generated documents, just with a benign outcome.
        io.open(os.path.join(d, DOC_REL), 'w', encoding='utf-8',
                newline='\n').write('THIS DOCUMENT IS DELIBERATELY STALE\n')
        code, o = run(d)
        after = read(d)
        if after == 'THIS DOCUMENT IS DELIBERATELY STALE\n':
            ok('A1. KNOWN-BAD: a bare run left a stale document untouched. '
               'Before the fix this arm failed -- the bare run rewrote it')
        else:
            bad('A1. a bare run must not write',
                'the document changed. exit=%s\n%s' % (code, o[-500:]))

        if 'REPORT ONLY' in o and 'DIFFERS' in o:
            ok('A2. ...and it still ANSWERS: it says the document differs, so '
               'the flag did not just move the cost of finding out')
        else:
            bad('A2. the bare run must report the staleness it declined to fix',
                o[-400:])

        if '--write' in o:
            ok('A3. ...and it names the command that would apply it. A refusal '
               'that does not say what to run next is a dead end')
        else:
            bad('A3. the bare run must name --write', o[-300:])

        if code == 0:
            ok('A4. and the bare run exits 0 -- report-only is not a failure. '
               'If it exited non-zero every caller would treat a clean repo as '
               'broken')
        else:
            bad('A4. a report-only run must exit 0', 'exit=%s' % code)

        section('B. THE SILENT HALF: --write still writes')

        code, o = run(d, '--write')
        after = read(d)
        if code == 0 and after and 'DELIBERATELY STALE' not in after \
                and 'NON-HUMAN IDENT' in after.upper():
            ok('B1. --write regenerates the document. Without this arm the fix '
               'could be "never write" and A1 would still pass')
        else:
            bad('B1. --write must write', 'exit=%s len=%s\n%s'
                % (code, after and len(after), o[-400:]))

        code, o = run(d)
        if 'already matches' in o:
            ok('B2. a bare run on an up-to-date document says so, rather than '
               'reporting a difference it cannot see')
        else:
            bad('B2. a bare run on a matching document must say it matches',
                o[-300:])

        section('C. THE OTHER MODES STILL BEHAVE, AND STILL DO NOT WRITE')

        io.open(os.path.join(d, DOC_REL), 'w', encoding='utf-8',
                newline='\n').write('STALE AGAIN\n')
        code, o = run(d, '--check')
        if code == 1 and read(d) == 'STALE AGAIN\n':
            ok('C1. --check reports stale (exit 1) and writes nothing')
        else:
            bad('C1. --check must report without writing',
                'exit=%s doc=%r' % (code, (read(d) or '')[:40]))

        code, o = run(d, '--json')
        if code == 0 and read(d) == 'STALE AGAIN\n' and o.strip().startswith('['):
            ok('C2. --json prints the identities and writes nothing')
        else:
            bad('C2. --json must not write', 'exit=%s' % code)

        # --selftest IS DRIVEN IN THE REAL CLONE, NOT THE SANDBOX, and the
        # reason is a measured finding rather than a convenience: it enumerates
        # the SIBLING DIRECTORIES of its repo root looking for other clones of
        # the same remote. From a temp directory the siblings are the whole
        # system temp tree and the arm TIMED OUT at 180 seconds, twice. So it is
        # exercised where it has a real parent, and what is asserted is that it
        # exits 0 and does not touch the document -- checkable from git.
        r = subprocess.run([sys.executable, TOOL_REL, '--selftest'], cwd=REPO,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=180)
        dirty = subprocess.run(['git', 'status', '--porcelain', DOC_REL],
                               cwd=REPO, capture_output=True, text=True,
                               encoding='utf-8', errors='replace').stdout.strip()
        if r.returncode == 0 and not dirty:
            ok('C3. --selftest passes in the real clone and leaves '
               'docs/NHI-REGISTER.md untouched (git status is empty for it)')
        else:
            bad('C3. --selftest must pass without touching the document',
                'exit=%s dirty=%r' % (r.returncode, dirty))

        section('D. THE ANCHOR, and THE SWEEP AGREES')

        src = io.open(os.path.join(REPO, TOOL_REL), encoding='utf-8').read()
        if "if '--write' not in argv:" in src:
            ok("D1. ANCHOR: the guard is still `if '--write' not in argv:`. If "
               'it is renamed every arm above stops testing the tool')
        else:
            bad('D1. ANCHOR MISSING: the --write guard',
                'the arms above would pass against a different mechanism')

        if 'python tools/nhi_register.py --write' in src:
            ok('D2. the docstring documents --write, so the file and its own '
               'usage line cannot disagree about which invocation writes')
        else:
            bad('D2. the docstring must document --write', 'not found')

        sweep = os.path.join(REPO, 'tools', 'bare_run_write_check.py')
        if os.path.isfile(sweep):
            r = subprocess.run(
                [sys.executable, sweep, '--repo', d, '--only',
                 'nhi_register.py', '--timeout', '90'],
                capture_output=True, text=True, encoding='utf-8',
                errors='replace', timeout=300)
            o2 = (r.stdout or '') + (r.stderr or '')
            # The sandbox is not a git repo, so the sweep must REFUSE rather
            # than report a clean bill -- which is itself the right answer and
            # is asserted here rather than worked around.
            if r.returncode == 2 and 'COULD NOT RUN' in o2:
                ok('D3. the sweep refuses to measure a non-git sandbox (exit 2, '
                   'COULD NOT RUN) rather than reporting this tool clean. The '
                   'two tools agree about what cannot be measured')
            else:
                bad('D3. the sweep must refuse a non-git target',
                    'exit=%s\n%s' % (r.returncode, o2[-400:]))
        else:
            bad('D3. tools/bare_run_write_check.py is missing',
                'the sweep this fix came out of is gone; COULD NOT RUN')
    finally:
        for d in made:
            shutil.rmtree(d, ignore_errors=True)

    sys.stdout.write('\n%d passed, %d failed\n' % (_pass, _fail))
    return 1 if _fail else 0


if __name__ == '__main__':
    sys.exit(main())
