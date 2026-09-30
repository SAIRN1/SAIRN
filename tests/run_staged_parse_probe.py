#!/usr/bin/env python
"""Control for tools/staged_parse_check.py -- and for the gate that calls it.

# REQUIREMENT: a push that ships a .py or .js under tools/, tests/ or api/ which
#   does not PARSE must be refused, and a file the checker could not examine must
#   exit 2 COULD NOT RUN rather than 0. The push gate syntax-checked api/ and
#   stonedesk.html and not tools/, so a tools/tooling_inventory.py that does not
#   parse reached origin/main.

THE KNOWN-BAD IS THE REAL SHAPE, NOT AN INVENTED ONE. The apostrophe-broken
heredoc: a python file written through `cat > f.py <<'EOF'` where a word like
`don't` inside a single-quoted string closes it early. That is the exact way the
tooling_inventory.py breakage was produced, and it is the way this repo produces
almost all of them, because the shell, python's quoting and the heredoc all use
the same character.

Run:  python tests/run_staged_parse_probe.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(REPO, 'tools', 'staged_parse_check.py')
HOOK = os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')

CRITERIA_VERSION = '2026-09-30.1'

SQ = chr(39)
BS = chr(92)

# ── the fixtures ─────────────────────────────────────────────────────────────
# An apostrophe inside a single-quoted python string, exactly as a heredoc leaves
# it. Valid-looking, and a SyntaxError.
BROKEN_PY = (
    "PURPOSES = {\n"
    "    " + SQ + "x.py" + SQ + ": (" + SQ + "CHECKER" + SQ + ", " + SQ
    + "the tool does not know what it doesn" + SQ + "t own" + SQ + "),\n"
    "}\n"
)
GOOD_PY = (
    "PURPOSES = {\n"
    "    " + SQ + "x.py" + SQ + ": (" + SQ + "CHECKER" + SQ + ", "
    + SQ + "the tool does not know what it does not own" + SQ + "),\n"
    "}\n"
)
BROKEN_JS = "function f(  { return 1; }\n"
GOOD_JS = "function f() { return 1; }\n"
# A file with a NULL byte -- python raises ValueError, not SyntaxError, and a
# checker that only catches SyntaxError reports it as parsing fine.
NUL_PY = "x = 1\n" + chr(0) + "y = 2\n"

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


def write(d, rel, body):
    p = os.path.join(d, rel)
    dd = os.path.dirname(p)
    if dd and not os.path.isdir(dd):
        os.makedirs(dd)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(body)
    return p


def run(*paths):
    r = subprocess.run([sys.executable, CHECK] + list(paths),
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=180)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def main():
    if not os.path.isfile(CHECK):
        sys.stderr.write('tools/staged_parse_check.py is missing -- COULD NOT '
                         'RUN, which is not a pass.\n')
        return 2
    sys.stdout.write('STAGED PARSE CONTROL -- criteria %s\n' % CRITERIA_VERSION)

    d = tempfile.mkdtemp(prefix='stagedparse_')
    try:
        section('A. THE KNOWN-BAD: the apostrophe-broken heredoc')

        bp = write(d, 'tools/inventory_broken.py', BROKEN_PY)
        gp = write(d, 'tools/inventory_good.py', GOOD_PY)
        code, o = run(bp)
        if code == 1 and 'DOES NOT PARSE' in o and 'SyntaxError' in o:
            ok('A1. KNOWN-BAD: a .py whose single-quoted string is closed early '
               'by an apostrophe is reported as not parsing, exit 1. This is the '
               'exact shape that put a broken tools/tooling_inventory.py on '
               'origin/main')
        else:
            bad('A1. the apostrophe-broken heredoc must be caught',
                'exit=%s\n%s' % (code, o[-600:]))

        if 'line' in o.lower():
            ok('A1b. ...and it names the line, so the report is actionable')
        else:
            bad('A1b. the failure must name a line number', o[-300:])

        code, o = run(gp)
        if code == 0 and 'All 1 checked' in o:
            ok('A2. THE SILENT HALF: the same file with the apostrophe removed '
               'passes. Without this the checker could be "reject everything"')
        else:
            bad('A2. a correct file must pass', 'exit=%s\n%s' % (code, o[-400:]))

        section('B. .js GOES THROUGH node --check')

        bj = write(d, 'tests/broken.js', BROKEN_JS)
        gj = write(d, 'tests/good.js', GOOD_JS)
        if shutil.which('node'):
            code, o = run(bj)
            if code == 1 and 'DOES NOT PARSE' in o:
                ok('B1. KNOWN-BAD: a .js with an unclosed parameter list is '
                   'reported')
            else:
                bad('B1. a broken .js must be caught',
                    'exit=%s\n%s' % (code, o[-400:]))
            code, o = run(gj)
            if code == 0:
                ok('B2. a correct .js passes')
            else:
                bad('B2. a correct .js must pass', 'exit=%s' % code)
        else:
            bad('B. node is not on PATH',
                'the .js half of this control COULD NOT RUN, which is not a '
                'pass -- and the checker is required to say the same thing')

        section('C. COULD NOT RUN IS A THIRD STATE')

        code, o = run()
        if code == 2:
            ok('C1. no files given is exit 2. An empty run reporting "everything '
               'parses" is a measurement that did not happen, and this tool is '
               'called from a gate where exit 0 means ALLOW')
        else:
            bad('C1. an empty run must exit 2', 'exit=%s' % code)

        code, o = run(os.path.join(d, 'tools', 'does_not_exist.py'))
        if code == 2 and 'COULD NOT CHECK' in o:
            ok('C2. a file that is not there is COULD NOT CHECK, not a pass')
        else:
            bad('C2. a missing file must exit 2', 'exit=%s\n%s' % (code, o[-300:]))

        np = os.path.join(d, 'tools', 'nul.py')
        io.open(np, 'w', encoding='utf-8', newline='\n').write(NUL_PY)
        code, o = run(np)
        if code == 1:
            ok('C3. a NULL byte in a .py is reported. python raises ValueError '
               'rather than SyntaxError for it, so a checker catching only '
               'SyntaxError would call this file fine -- and a raw control byte '
               'in source is already a known defect class here')
        else:
            bad('C3. a NULL byte must be reported', 'exit=%s\n%s' % (code, o[-300:]))

        section('D. NOTHING IS SILENTLY SKIPPED, AND NOTHING IS WRITTEN')

        md = write(d, 'docs/notes.md', '# not source\n')
        code, o = run(gp, md)
        if code == 0 and 'SKIPPED' in o and 'notes.md' in o:
            ok('D1. a non-source file is SKIPPED and NAMED. A silent skip reads '
               'as coverage it did not have')
        else:
            bad('D1. skips must be named', 'exit=%s\n%s' % (code, o[-400:]))

        before = set()
        for root, _dirs, files in os.walk(d):
            for f in files:
                before.add(os.path.join(root, f))
        run(gp, bp, gj, md)
        after = set()
        for root, _dirs, files in os.walk(d):
            for f in files:
                after.add(os.path.join(root, f))
        new = sorted(x[len(d):] for x in (after - before))
        if not new:
            ok('D2. the checker WRITES NOTHING. `python -m py_compile` would '
               'have left a __pycache__/*.pyc beside every file it checked -- a '
               'gate mutating the tree it inspects, which would then show up in '
               'git status as though the push had produced it')
        else:
            bad('D2. the checker must not write', 'it created: %s' % new)

        section('E. THE GATE ACTUALLY CALLS IT, AND FAILS CLOSED WITHOUT IT')

        hooksrc = io.open(HOOK, encoding='utf-8', errors='replace').read()
        if 'staged_parse_check.py' in hooksrc:
            ok('E1. tools/sairn_push_gate_hook.py references the checker')
        else:
            bad('E1. the gate must call the checker',
                'a checker no gate invokes is a file, not a check')
        if 'not os.path.isfile(_sp)' in hooksrc and 'deny(' in hooksrc:
            ok('E2. and it DENIES when the checker is absent rather than '
               'skipping -- PR 1.11, the rule five other checks in this gate '
               'were each corrected to one at a time')
        else:
            bad('E2. a missing checker must deny, not skip',
                'the absent-checker branch is not a deny')
        if "('tools', 'tests', 'api')" in hooksrc:
            ok('E3. the scope is tools/, tests/ and api/ -- tools/ being the one '
               'that was not checked at all')
        else:
            bad('E3. the gate must scope to tools/, tests/ and api/',
                'the directory tuple is not there')
        if "files given" in hooksrc:
            ok('E4. the gate cross-checks the count the checker reports, so an '
               'OLDER copy that ignored the file list is a COULD-NOT-TELL '
               'rather than a clean pass')
        else:
            bad('E4. the gate must verify the checker honoured its file list',
                'no count cross-check')
    finally:
        shutil.rmtree(d, ignore_errors=True)

    sys.stdout.write('\n%d passed, %d failed\n' % (_pass, _fail))
    return 1 if _fail else 0


if __name__ == '__main__':
    sys.exit(main())
