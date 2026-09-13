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

  IT CAN SEE   that no file DECLARES itself a control for a checker. That is
               mechanical and certain, and it is the finding that matters most.

  IT INFERS    which DIRECTION a declared control exercises, from its
               assertions. That is a heuristic, so the report says EVIDENCED
               rather than PROVEN and never upgrades a guess into a guarantee.

  IT CANNOT    tell a control that plants a REAL defect from one that plants a
               shape the checker happens to match. Only reading the fixture can.

WHY A DECLARATION RATHER THAN INFERENCE: see declared_controls(). Three
inference models were tried and all three were wrong within an hour of being
written, each in a different direction.

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


DECL_RE = re.compile(
    r"CONTROLS_FOR\s*=\s*[\[\(]([^\]\)]*)[\]\)]", re.S)
NAME_RE = re.compile(r"['\"]([\w.-]+\.py)['\"]")


def declared_controls(code):
    """Which checkers this file declares itself a control for.

    ── WHY A DECLARATION, AFTER THREE INFERENCE MODELS ALL FAILED ────────────
    This tool tried to infer, from a test file's shape, which checker its
    assertions were about. Every model was wrong in a different direction and
    each was found within an hour:

      FILE LEVEL   over-credits. The first control file written against this
                   tool named five checkers in its DOCSTRING while testing
                   three, and all five came back proven -- the tool producing
                   false reassurance about false reassurance.

      PROXIMITY    under-credits. `tests/run_defect_register_probe.py` binds
                   `TOOL = 'tools/defect_register.py'` once at the top and
                   asserts both directions 150 lines below, so a thorough
                   control read as ONE DIRECTION.

      INVOCATION   under-credits differently. Real controls wrap the subprocess
                   call in a `run()` helper, so the checker's name never appears
                   inside the call span at all -- which marked the controls
                   written THAT MORNING as REFERENCED ONLY.

    Three models, three wrong answers, each plausible. The lesson is not that
    the fourth heuristic will work: it is that **which checker a test is a
    control for is a fact its author knows and nothing else reliably does**.

    So it is declared:

        CONTROLS_FOR = ['checkblocks.py', 'div_balance_check.py']

    One line, unambiguous, and philosophically the right shape for a tool whose
    whole job is to demand proof rather than infer it. An UNDECLARED control is
    exactly the "we think it is covered" state this tool exists to end.
    """
    out = set()
    for m in DECL_RE.finditer(code):
        out.update(NAME_RE.findall(m.group(1)))
    return out


def evidence(code):
    """(fires, silent) assertion lines in a declared control.

    File level is CORRECT here and was not before: the file has said, in its own
    source, which checkers it is a control for.
    """
    fires, silent = [], []
    for i, line in enumerate(code.splitlines(), 1):
        if any(r.search(line) for r in FIRES_RE):
            fires.append((i, line.strip()[:90]))
        if any(r.search(line) for r in SILENT_RE):
            silent.append((i, line.strip()[:90]))
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

    # Declarations first, so attribution is a fact rather than a guess.
    declares = {}                       # checker -> [control file, ...]
    mentions = {}                       # checker -> [file that names it, ...]
    for t, body in bodies.items():
        for c in declared_controls(body):
            declares.setdefault(c, []).append(t)
    for c in checkers:
        for t, body in bodies.items():
            if c in body and t not in declares.get(c, []):
                mentions.setdefault(c, []).append(t)

    rows = []
    for c in checkers:
        ctrl = declares.get(c, [])
        fires = silent = 0
        for t in ctrl:
            f, s_ = evidence(bodies[t])
            fires += len(f)
            silent += len(s_)
        if c in EXEMPT:
            verdict = 'EXEMPT'
        elif not ctrl:
            verdict = 'NO DECLARED CONTROL'
        elif fires and silent:
            verdict = 'BOTH EVIDENCED'
        elif fires or silent:
            verdict = 'ONE DIRECTION'
        else:
            verdict = 'DECLARED, NO ASSERTIONS'
        rows.append({'checker': c, 'controls': len(ctrl),
                     'mentions': len(mentions.get(c, [])),
                     'fires': fires, 'silent': silent, 'verdict': verdict})

    bad = [r for r in rows if r['verdict'] != 'BOTH EVIDENCED'
           and r['verdict'] != 'EXEMPT']
    if not quiet:
        print('CHECKER CONTROL CHECK -- nothing was executed')
        print('  promoted checkers : %d' % len(checkers))
        print('  test files read   : %d' % len(tests))
        for v in ('NO DECLARED CONTROL', 'DECLARED, NO ASSERTIONS',
                  'ONE DIRECTION', 'BOTH EVIDENCED', 'EXEMPT'):
            n = len([r for r in rows if r['verdict'] == v])
            print('  %-17s : %d' % (v, n))
        print('')
        for r in sorted(rows, key=lambda x: (x['verdict'] != 'NO DECLARED CONTROL',
                                             x['verdict'], x['checker'])):
            if r['verdict'] in ('BOTH EVIDENCED', 'EXEMPT'):
                continue
            note = ''
            if r['verdict'] == 'NO DECLARED CONTROL' and r['mentions']:
                note = ('  -- %d file(s) NAME it; if one is really its control, '
                        'add CONTROLS_FOR' % r['mentions'])
            print('  %-23s %-34s fires=%d silent=%d%s'
                  % (r['verdict'], r['checker'], r['fires'], r['silent'], note))
        if EXEMPT:
            print('')
            print('  EXEMPT, with a reason each:')
            for k, why in EXEMPT.items():
                print('    %-30s %s' % (k, why[:96]))
        print('')
        print('A CONTROL DECLARES ITSELF:  CONTROLS_FOR = [\'your_check.py\']')
        print('Three inference models were tried and all three were wrong within an hour,')
        print('each in a different direction -- see declared_controls() for what they were.')
        print('')
        print('EVIDENCED, NOT PROVEN: direction is read from assertions. Only reading the')
        print('fixture can tell a control that plants a REAL defect from one that plants a')
        print('shape the checker happens to match.')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
