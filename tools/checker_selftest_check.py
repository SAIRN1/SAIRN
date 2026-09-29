#!/usr/bin/env python
"""Does a checker prove IT STILL WORKS, on the same run that reports clean?

    python tools/checker_selftest_check.py
    python tools/checker_selftest_check.py --fixtures   # criteria lock alone
    python tools/checker_selftest_check.py --all        # list the cleared too
    python tools/checker_selftest_check.py --quiet

Exit 0 clean, 1 findings, 2 COULD NOT RUN. REPORT ONLY.

── THE DEFECT ───────────────────────────────────────────────────────────────
A checker prints CLEAN. Nothing in that output distinguishes

    (a) it looked and there was nothing wrong, from
    (b) it stopped being able to see the thing it looks for.

This repo has shipped (b) more than once and each time it was found by
accident: a regex with a literal backspace that could never match, a string
anchor that no longer matched after a rename, a criteria lock that could not
classify the shape the tool was built for and reported clean for every tool in
the directory. **A checker that has never been seen to FIRE is a checker whose
clean line is evidence for the wrong conclusion.**

A CONTROL FILE IS NOT THE ANSWER TO THIS. Controls are real and this repo has
many, but a control runs when somebody runs it, and the person reading a clean
line at 2am is not running it. The question here is narrower and it is about
the REAL RUN:

    On the run that just told me CLEAN, did the tool demonstrate -- in its own
    output -- that it still reports a known-positive?

── THE SHAPE THAT PASSES ────────────────────────────────────────────────────
    criteria lock: 48/48 fixtures classify correctly, on hand-built sources only
    read 347 Python and 464 JavaScript suite file(s)
    CLEAN -- ...

Three properties, and all three are required:

  1. a KNOWN-POSITIVE FIXTURE SET exists -- hand-built sources with an expected
     verdict each, including at least one the tool must REPORT;
  2. it runs on the DEFAULT PATH, not only under `--fixtures` or `--selftest`;
  3. its outcome is PRINTED, on a passing run, beside the real result.

(3) is the one that gets dropped. A self-test that runs and says nothing when it
passes is invisible exactly when it matters: the reader sees the clean line and
has no way to tell it was earned. A self-test that only runs under a flag is a
control with a shorter name.

── WHAT IT CANNOT SEE, stated rather than discovered later ──────────────────
  * WHETHER THE FIXTURES ARE ANY GOOD. This reads structure: a fixture set
    exists, runs, and reports. A fixture set of one trivially-true case passes
    here. That is `tools/sabotage_control_check.py`'s question, not this one.
  * A self-test whose runner is not a module-level function -- inlined in
    `main`, or reached through a dispatch table.
  * The generators in the registry. `master_plan.py`, `traceability_matrix.py`,
    `tooling_inventory.py` and `defect_register.py` are not criteria-based
    checkers; their `--check` mode compares a document to their own output,
    which is a self-test in a different shape and is NOT recognised here. They
    are reported like everything else rather than silently excluded, because a
    quiet exemption list is how a population shrinks without anybody deciding.
"""
import argparse
import ast
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN, finish                 # noqa: E402

CONTROLLED_BY = ['tests/run_checker_selftest_probe.py']
CRITERIA_VERSION = '2026-09-29.1'

# ── THE CRITERIA ─────────────────────────────────────────────────────────────
# Names a fixture runner goes by in this repo. Hand-kept, which is a known
# weakness, so --all prints every tool considered and the figure is published as
# CHECKED / UNIVERSE rather than implied.
SELFTEST_NAMES = ('run_fixtures', 'self_check', 'selftest', 'run_selftest',
                  'run_selftests', 'run_cases', 'fixtures')
# Flags whose branch is the ISOLATED path. A self-test reachable only from here
# runs when somebody asks, which is a control, not a self-test.
ISOLATED_FLAGS = ('fixtures', 'selftest', 'self_check', 'self-check')
# Words that mean a printed line IS the self-test's outcome, for tools that call
# the runner without binding its result to a name.
SELFTEST_WORDS = ('criteria lock', 'self-test', 'selftest', 'fixtures classify',
                  'known-positive', 'fixture')

PUBLISHED = 'SELF-TEST RUNS AND IS PRINTED on every real run'
SILENT = 'SELF-TEST RUNS BUT PRINTS NOTHING when it passes -- invisible exactly when it matters'
FLAG_ONLY = 'SELF-TEST IS FLAG-ONLY -- a control with a shorter name, not a self-test'
NONE = 'NO KNOWN-POSITIVE FIXTURE SET AT ALL'


def _callee(node):
    f = node.func
    return f.attr if isinstance(f, ast.Attribute) else (
        f.id if isinstance(f, ast.Name) else None)


def _isolated_nodes(main):
    """ids of every node inside an `if args.fixtures:`-shaped branch."""
    out = set()
    for n in ast.walk(main):
        if not isinstance(n, ast.If):
            continue
        # ── NORMALISED, AND THE FIRST REAL RUN IS WHY ──────────────────────
        # The first version matched `attr='fixtures'` and `'fixtures'` and
        # missed `if '--selftest' in argv:` -- because the dump carries
        # `value='--selftest'` and the leading quote never lines up with the
        # dashes. tools/ai_action_approval_audit.py was reported as SILENT when
        # its self-test is FLAG-ONLY: a wrong verdict, in the harsher direction,
        # on a tool whose self-test is one of the better ones in the repo.
        # Dashes and underscores are stripped from both sides so the three
        # spellings this repo uses are one spelling here.
        dumped = ast.dump(n.test).replace('-', '').replace('_', '')
        if any(f.replace('-', '').replace('_', '') in dumped
               for f in ISOLATED_FLAGS):
            for s in ast.walk(n):
                out.add(id(s))
    return out


def _printed_names(main):
    """Names referenced inside a print() call anywhere in main."""
    out = set()
    for n in ast.walk(main):
        if not (isinstance(n, ast.Call) and getattr(n.func, 'id', None) == 'print'):
            continue
        for s in ast.walk(n):
            if isinstance(s, ast.Name):
                out.add(s.id)
    return out


def _prints_selftest_words(main, isolated):
    """A print on the DEFAULT path whose literal names the self-test."""
    for n in ast.walk(main):
        if not (isinstance(n, ast.Call) and getattr(n.func, 'id', None) == 'print'):
            continue
        if id(n) in isolated:
            continue
        for s in ast.walk(n):
            if isinstance(s, ast.Constant) and isinstance(s.value, str):
                low = s.value.lower()
                if any(w in low for w in SELFTEST_WORDS):
                    return True
    return False


def classify(src):
    """One verdict for one module's source."""
    tree = ast.parse(src)
    funcs = {n.name: n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    runners = [n for n in SELFTEST_NAMES if n in funcs]
    main = funcs.get('main')
    if not runners or main is None:
        return NONE
    isolated = _isolated_nodes(main)
    on_default, bound = False, set()
    for n in ast.walk(main):
        if isinstance(n, ast.Call) and _callee(n) in runners and id(n) not in isolated:
            on_default = True
    # What the default-path call was assigned to, so a print of it can be found.
    for n in ast.walk(main):
        if not (isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
                and _callee(n.value) in runners and id(n.value) not in isolated):
            continue
        for t in n.targets:
            if isinstance(t, ast.Name):
                bound.add(t.id)
    if not on_default:
        return FLAG_ONLY
    # ── PRINTED, BY EITHER OF TWO MECHANISMS, AND BOTH ARE NAMED ───────────
    # A tool either binds the result and prints it (`bad = run_fixtures()` ...
    # `print(... len(bad) ...)`) or calls it bare and prints a line that says
    # what it did (`criteria lock: 48/48 fixtures classify correctly`). Only
    # accepting the first would report the better-written half of the repo.
    if (bound & _printed_names(main)) or _prints_selftest_words(main, isolated):
        return PUBLISHED
    return SILENT


# ── THE FIXTURE LOCK (discipline 1) ──────────────────────────────────────────
# Hand-built sources with an expected verdict each, classified FIRST, reading no
# real file. This tool's own subject applied to itself: the lock below runs on
# every real run and its result is printed beside the finding count.
FIXTURES = (
    ("""
def run_fixtures():
    return []
def main(argv):
    bad = run_fixtures()
    if bad:
        return 2
    print('criteria lock: %d/%d fixtures classify correctly' % (N, N))
    rows = scan()
    print('%d finding(s)' % len(rows))
""", PUBLISHED, 'THE SHAPE THAT PASSES: a known-positive set, run on the default '
                'path, and its result printed beside the real one'),
    ("""
def run_fixtures():
    return []
def main(argv):
    if args.fixtures:
        bad = run_fixtures()
        print('%d wrong' % len(bad))
        return 0
    rows = scan()
    print('%d finding(s)' % len(rows))
""", FLAG_ONLY,
     'A SELF-TEST BEHIND A FLAG IS A CONTROL WITH A SHORTER NAME. It runs when '
     'somebody asks, and the person reading a clean line at 2am is not asking'),
    ("""
def run_fixtures():
    return []
def main(argv):
    bad = run_fixtures()
    if bad:
        return 2
    rows = scan()
    print('%d finding(s)' % len(rows))
""", SILENT,
     'IT RUNS AND SAYS NOTHING WHEN IT PASSES. The refusal path is real and is '
     'not the point: a reader of the CLEAN line still cannot tell the tool '
     'demonstrated anything'),
    ("""
def main(argv):
    rows = scan()
    print('%d finding(s)' % len(rows))
""", NONE, 'no fixture set at all -- the commonest state, and the honest name '
           'for it is not "clean"'),
    ("""
def self_check():
    return []
def main(argv):
    bad = self_check()
    print('self-test: %d case(s) wrong' % len(bad))
    rows = scan()
    print('%d finding(s)' % len(rows))
""", PUBLISHED, 'self_check() is the other name the repo uses for the same thing'),
    ("""
def run_fixtures():
    return []
def main(argv):
    bad = run_fixtures()
    print('%d wrong' % len(bad))
    if args.fixtures:
        return 0
    rows = scan()
""", PUBLISHED,
     'THE RUNNER OUTSIDE THE FLAG BRANCH AND THE EARLY RETURN INSIDE IT is how '
     'three tools in this repo are written, and it passes: the self-test runs '
     'and prints on BOTH paths, which is the property, not the layout'),
    ("""
def selftest():
    print('  ok   a planted case is reported')
    return 0
def main(argv):
    if '--selftest' in argv:
        return selftest()
    rows = scan()
    print('%d finding(s)' % len(rows))
""", FLAG_ONLY,
     "THE `in argv` SPELLING OF THE ISOLATED FLAG. The first version matched "
     "`attr='fixtures'` and missed `'--selftest' in argv`, and reported "
     "ai_action_approval_audit.py as SILENT when its self-test is flag-only -- "
     "a wrong verdict in the harsher direction on one of the better self-tests "
     "in the repo"),
    ("""
def run_fixtures():
    return []
def helper():
    return run_fixtures()
def main(argv):
    rows = scan()
    print('%d finding(s)' % len(rows))
""", FLAG_ONLY,
     'A RUNNER MAIN NEVER CALLS is not a self-test on the real run, even though '
     'the fixture set exists. Reported as flag-only rather than as NONE, '
     'because the fixtures are real and the wiring is what is missing'),
)


def run_fixtures(verbose=False):
    bad = []
    for src, want, why in FIXTURES:
        try:
            got = classify(src)
        except SyntaxError as e:
            bad.append('fixture does not parse (%s)' % e)
            continue
        if got != want:
            bad.append('EXPECTED %s, got %s -- %s' % (want, got, why))
        elif verbose:
            print('  ok   %-28s %s' % (want.split(' --')[0][:28], why))
    return bad


def registry_tools():
    """The report-only registry, which is the population this is about."""
    try:
        import report_only_checks
    except Exception:                                          # noqa: BLE001
        return None
    try:
        return [e['tool'] for e in report_only_checks.REGISTRY if e.get('tool')]
    except Exception:                                          # noqa: BLE001
        return None


def main(argv):
    ap = argparse.ArgumentParser(add_help=True,
                                 description=__doc__.split('\n')[0])
    ap.add_argument('--fixtures', action='store_true',
                    help='run the criteria lock alone -- reads no real file')
    ap.add_argument('--all', action='store_true',
                    help='also list the cleared tools')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args(argv)

    if not a.quiet:
        print('KNOWN-POSITIVE SELF-TEST ON THE REAL RUN -- criteria %s'
              % CRITERIA_VERSION)

    bad = run_fixtures(verbose=(a.fixtures and not a.quiet))
    if bad:
        if not a.quiet:
            print('\nCRITERIA LOCK FAILED -- %d of %d fixtures misclassified.'
                  % (len(bad), len(FIXTURES)))
            for b in bad:
                print('  ! %s' % b)
            print('\nNOTHING REAL WAS JUDGED. A tool that asks every other tool '
                  'to prove it still\nworks does not get to skip the question.')
        return EXIT_COULD_NOT_RUN
    if not a.quiet:
        print('criteria lock: %d/%d fixtures classify correctly, on hand-built '
              'sources only' % (len(FIXTURES), len(FIXTURES)))
    if a.fixtures:
        return 0

    tools = registry_tools()
    if not tools:
        if not a.quiet:
            print('\nCOULD NOT READ tools/report_only_checks.py, or its REGISTRY '
                  'is empty. The\npopulation is that registry and nothing else, '
                  'so there is nothing to report\nrather than nothing wrong.')
        return EXIT_COULD_NOT_RUN

    findings, cleared, unparsed = [], [], []
    for name in tools:
        path = os.path.join(REPO, 'tools', name)
        if not os.path.isfile(path):
            unparsed.append('%s -- in the registry and not on disk' % name)
            continue
        try:
            src = io.open(path, encoding='utf-8', errors='replace').read()
            verdict = classify(src)
        except (OSError, SyntaxError) as e:
            unparsed.append('%s -- %s' % (name, e))
            continue
        if verdict == PUBLISHED:
            cleared.append(name)
        else:
            findings.append((name, verdict))

    checked = len(tools) - len(unparsed)
    if not a.quiet:
        print('read %d tool(s) named in the report-only registry' % len(tools))
        print('\nCHECKED / UNIVERSE: %d of %d registry tools (%.0f%%). The '
              'population is the\n  REGISTRY, not tools/ -- a tool nothing runs '
              'on a cadence has a different\n  problem, and conflating the two '
              'would let this figure read as a platform verdict.'
              % (checked, len(tools),
                 (100.0 * checked / len(tools)) if tools else 0))
        for v, label in ((PUBLISHED, 'printed on every real run'),
                         (SILENT, 'runs, prints nothing'),
                         (FLAG_ONLY, 'flag-only'),
                         (NONE, 'no fixture set')):
            n = len(cleared) if v == PUBLISHED else len(
                [f for f in findings if f[1] == v])
            print('  %3d  %s' % (n, label))
        if a.all:
            print('\nCLEARED (%d):' % len(cleared))
            for n in cleared:
                print('  - %s' % n)

    return finish(
        ['%s  %s' % (name, verdict) for name, verdict in findings],
        could_not_run=unparsed, quiet=a.quiet,
        clean_line='\nCLEAN -- every checker in the report-only registry '
                   'demonstrates a known-positive\non the same run that reports '
                   'its real result.')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
