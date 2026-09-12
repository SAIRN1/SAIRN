"""Does every promoted checker have a control that PROVES it can fire?

    python tools/checker_control_check.py
    python tools/checker_control_check.py --quiet     # exit code only

Exit 0 when every promoted checker has both directions evidenced, 1 otherwise.

── WHY THIS EXISTS ──────────────────────────────────────────────────────────
A checker that has never been seen to fail is a checker whose behaviour nobody
knows. Its clean line is then evidence for the wrong conclusion -- the most
expensive shape this platform keeps finding, and the one the whole report-only
registry rests on.

`checkblocks.py` is the case that prompted this: it always exited 0. Nothing
noticed, because a checker that always passes looks exactly like a codebase
that is always clean. It was found when somebody thought to test it by hand.
**Thinking to test it by hand is not a mechanism.** This is.

THE STANDARD IT ENFORCES IS THE ONE `packages/testint` ALREADY PROVES OUT:
a control pair, both directions, on file --

    plant the defect  -> the checker must REPORT it
    plant clean code  -> the checker must STAY SILENT

A check that always reports passes the first half alone. A check that never
reports passes the second alone. **Only the pair says anything**, and this tool
exists to ask every checker in the registry for both.

── WHAT IT CAN AND CANNOT SEE, said plainly ─────────────────────────────────

  IT CAN SEE   that NOTHING anywhere in tests/ references a checker at all --
               which is mechanical, certain, and the finding that matters most.

  IT INFERS    which direction a referencing test exercises, by reading the
               assertions near the reference. That is a heuristic, so the
               report says EVIDENCED rather than PROVEN, quotes the line it
               read, and never upgrades a guess into a guarantee.

  IT CANNOT    tell a control that plants a REAL defect from one that plants a
               shape the checker happens to match. Only reading the fixture can,
               which is why the evidence is quoted rather than counted.

IT RUNS NOTHING. It reads test source with comments stripped -- because a test
whose COMMENT says "expect exit 1" while its code asserts nothing would
otherwise be read as proof, which is the exact defect class this platform
recorded three times in two days.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import jscomments as _jscomments                              # noqa: E402

# Evidence that a test expects the checker to FIND something: a non-zero exit,
# or an assertion naming a failure state.
FIRES = [
    r'returncode\s*==\s*[1-9]', r'returncode\s*!=\s*0',
    r'\brc\s*==\s*[1-9]', r'\brc\s*!=\s*0',
    r'exit\s*(?:code)?\s*[=:]?\s*[1-9]\b',
    r'status\s*===?\s*[1-9]',
    r'FINDING', r'FAIL', r'must (?:be )?(?:deny|denied|block)', r'\bDENY\b',
]
# Evidence that a test expects the checker to stay SILENT on clean input.
SILENT = [
    r'returncode\s*==\s*0', r'\brc\s*==\s*0', r'exit\s*(?:code)?\s*[=:]?\s*0\b',
    r'status\s*===?\s*0', r'\bCLEAN\b', r'0 finding', r'no finding',
    r'stays? (?:quiet|silent)', r'not (?:be )?(?:report|flagged)',
]
FIRES_RE = [re.compile(p, re.I) for p in FIRES]
SILENT_RE = [re.compile(p, re.I) for p in SILENT]

# Checkers exempt from the control requirement, with a REASON each. An exemption
# with a reason beside it is a decision; one without is a silence.
EXEMPT = {
    'npm_audit_check.py':
        'its subject is the public npm advisory database, not this repo. A '
        'control would have to pin an advisory that will be fixed upstream, and '
        'a fixture that expires is worse than none. It exits 3 when it cannot '
        'reach the registry, which is the property that actually matters.',
}


def promoted():
    """The checkers the registry actually runs, read from the registry itself."""
    import report_only_checks as R
    return [e['tool'] for e in R.REGISTRY]


def test_files():
    out = []
    for root, dirs, files in os.walk(os.path.join(REPO, 'tests')):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in files:
            if f.endswith(('.py', '.js')):
                out.append(os.path.join(root, f))
    api = os.path.join(REPO, 'api')
    for f in sorted(os.listdir(api)):
        if f.endswith('.test.js'):
            out.append(os.path.join(api, f))
    return sorted(out)


def strip(path, src):
    """Comment-stripped source. A COMMENT saying "expect exit 1" is not a test."""
    if path.endswith('.py'):
        return '\n'.join('' if l.lstrip().startswith('#') else l
                         for l in src.splitlines())
    return _jscomments.strip_comments(src)


# How far from a mention of the checker an assertion may sit and still count as
# evidence about THAT checker.
#
# ── WHY A WINDOW, AND WHY THIS TOOL NEEDED ONE WITHIN AN HOUR OF SHIPPING ────
# The first version attributed evidence at FILE level: once a test file
# mentioned a checker anywhere, every fires/silent assertion in that file
# counted for it. Then the very first control file written against this tool
# named five checkers in its DOCSTRING while actually testing three -- and all
# five came back BOTH EVIDENCED. NO CONTROL went 5 -> 0 and two of those were a
# lie.
#
# That is this tool producing false reassurance ABOUT false reassurance, which
# is the worst outcome available to it. A Python docstring is a STRING, not a
# comment, so comment-stripping does not remove it and never would have.
#
# 15 lines is deliberately tight: a control's assertions sit beside the call
# that produced them. A mention with no assertion within 15 lines is a MENTION,
# and the verdict for that is REFERENCED ONLY -- which does not pass.
WINDOW = 15


def evidence(code, checker):
    """(fires, silent) evidence lines attributable to ONE checker.

    Attribution is by proximity to a line naming the checker. See WINDOW.
    """
    lines = code.splitlines()
    at = [i for i, l in enumerate(lines) if checker in l]
    if not at:
        return [], []
    near = set()
    for i in at:
        near.update(range(max(0, i - WINDOW), min(len(lines), i + WINDOW + 1)))
    fires, silent = [], []
    for i in sorted(near):
        line = lines[i]
        if any(r.search(line) for r in FIRES_RE):
            fires.append((i + 1, line.strip()[:90]))
        if any(r.search(line) for r in SILENT_RE):
            silent.append((i + 1, line.strip()[:90]))
    return fires, silent


def main(argv):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:                                         # noqa: BLE001
        pass
    quiet = '--quiet' in argv
    checkers = promoted()
    tests = test_files()
    bodies = {}
    for t in tests:
        raw = io.open(t, encoding='utf-8', errors='replace').read()
        bodies[t] = strip(t, raw)

    rows = []
    for c in checkers:
        refs = [t for t, b in bodies.items() if c in b]
        fires = silent = 0
        quotes = []
        for t in refs:
            f, s = evidence(bodies[t], c)
            fires += len(f)
            silent += len(s)
            if f and not quotes:
                quotes.append((os.path.relpath(t, REPO).replace(os.sep, '/'), f[0]))
        if c in EXEMPT:
            verdict = 'EXEMPT'
        elif not refs:
            verdict = 'NO CONTROL'
        elif fires and silent:
            verdict = 'BOTH EVIDENCED'
        elif fires or silent:
            verdict = 'ONE DIRECTION'
        else:
            verdict = 'REFERENCED ONLY'
        rows.append({'checker': c, 'refs': len(refs), 'fires': fires,
                     'silent': silent, 'verdict': verdict, 'quotes': quotes})

    bad = [r for r in rows if r['verdict'] in
           ('NO CONTROL', 'ONE DIRECTION', 'REFERENCED ONLY')]
    if not quiet:
        print('CHECKER CONTROL CHECK -- nothing was executed')
        print('  promoted checkers : %d' % len(checkers))
        print('  test files read   : %d' % len(tests))
        for v in ('NO CONTROL', 'REFERENCED ONLY', 'ONE DIRECTION',
                  'BOTH EVIDENCED', 'EXEMPT'):
            n = len([r for r in rows if r['verdict'] == v])
            print('  %-17s : %d' % (v, n))
        print('')
        for r in sorted(rows, key=lambda x: (x['verdict'] != 'NO CONTROL',
                                             x['verdict'], x['checker'])):
            if r['verdict'] in ('BOTH EVIDENCED', 'EXEMPT'):
                continue
            print('  %-17s %-34s %d test file(s), fires=%d silent=%d'
                  % (r['verdict'], r['checker'], r['refs'], r['fires'], r['silent']))
        if EXEMPT:
            print('')
            print('  EXEMPT, with a reason each:')
            for k, why in EXEMPT.items():
                print('    %-30s %s' % (k, why[:96]))
        print('')
        print('EVIDENCED, NOT PROVEN. Direction is inferred from assertions near the')
        print('reference; only reading the fixture can tell a control that plants a REAL')
        print('defect from one that plants a shape the checker happens to match.')
        print('')
        print('NO CONTROL is the one that is mechanical and certain: nothing anywhere')
        print('in tests/ names that checker, so nothing has ever seen it fail.')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
