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
import re
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN, finish                 # noqa: E402

# ── MODULE LEVEL AND GUARDED, BOTH, MOVED 2026-10-06 (cc) ───────────────────
# `report_only_checks.REGISTRY` refuses at import on an undocumented entry,
# and its message justifies that placement: "a suite tells you after the entry
# is on main, and five accumulated that way." MEASURED 2026-10-06: the promise
# held for only 7 of its 14 importers, and this was one of the seven -- the
# import sat inside `registry_tools()`, so the refusal arrived mid-run.
#
# A BARE MODULE-LEVEL IMPORT WOULD HAVE BEEN THE WRONG FIX HERE and the reason
# is the whole point of this file. Two of the fourteen (`checker_control_check`,
# `traceability_matrix`) have no third state, so hoisting their bare import
# costs nothing. This one DOES: it exits 2 COULD NOT RUN naming the raised
# cause. Hoisting it unguarded would replace that diagnosis with a traceback --
# trading a worse message for an earlier one, when both are available at once.
#
# So the import is EVALUATED at import time (the guarantee) and its outcome is
# CARRIED (the diagnosis). `_ROC_WHY` is None only when the module is usable.
try:
    import report_only_checks as _ROC                              # noqa: E402
    _ROC_WHY = None
except Exception as _e:                                            # noqa: BLE001
    _ROC, _ROC_WHY = None, '%s: %s' % (type(_e).__name__, _e)

CONTROLLED_BY = ['tests/run_checker_selftest_probe.py']
CRITERIA_VERSION = '2026-09-29.1'

# ── THE CRITERIA ─────────────────────────────────────────────────────────────
# Names a fixture runner goes by in this repo. Hand-kept, which is a known
# weakness, so --all prints every tool considered and the figure is published as
# CHECKED / UNIVERSE rather than implied.
SELFTEST_NAMES = ('run_fixtures', 'self_check', 'selftest', 'run_selftest',
                  'run_selftests', 'run_cases', 'fixtures')
# ── AND A SHAPE, BECAUSE THE NAME LIST WAS SHORT BY ONE (2026-09-29) ────────
# The first real run reported tools/metamorphic_check.py as having NO FIXTURE
# SET. It has one of the best in the repo: `blind_lock()` writes a SENSITIVE and
# a ROBUST fixture to disk, requires every SAME relation to catch the first and
# none to catch the second, runs on the default path, prints
# `blind lock: LOCKED (N fixture comparisons)` beside the real result, and
# REFUSES the measurement when it is not locked. It was invisible here for one
# reason: the function is called `blind_lock`, and a hand-kept name list is the
# weakness this file's own header already admits to.
#
# So a runner is ALSO any function that reads a module-level constant whose name
# says it holds hand-built cases. `LOCK` is deliberately NOT in the pattern --
# it matches ordinary locking code and would pull half the directory in.
# Measured before adding it: exactly ONE of the 46 NO-FIXTURE tools carries such
# a constant, so this widens by one and not by forty.
FIXTURE_CONST = re.compile(
    r'(^|_)(FIXTURE|FIXTURES|CASES|GOLDEN|KNOWN_BAD|KNOWN_GOOD)S?(_|$)', re.I)
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
    # A module-level constant holding hand-built cases makes any function that
    # READS it a fixture runner, whatever it is called. The constant must be a
    # literal collection or string -- a fixture set is DATA, and requiring that
    # keeps a same-named flag or counter out.
    fixture_consts = set()
    for n in tree.body:
        if not isinstance(n, ast.Assign):
            continue
        # A STRING counts (metamorphic writes its fixture source as one);
        # a NUMBER does not. `CONFIG_CASES = 3` made its whole module read
        # as having a fixture set on the first fixture run of this widening,
        # which is the widening turning into a false-clean machine.
        _v = n.value
        if not (isinstance(_v, (ast.List, ast.Tuple, ast.Dict))
                or (isinstance(_v, ast.Constant)
                    and isinstance(_v.value, str))):
            continue
        for tg in n.targets:
            if isinstance(tg, ast.Name) and FIXTURE_CONST.search(tg.id):
                fixture_consts.add(tg.id)
    if fixture_consts:
        for fname, fnode in funcs.items():
            if fname == 'main':
                continue
            if fixture_consts & set(x.id for x in ast.walk(fnode)
                                    if isinstance(x, ast.Name)):
                runners.append(fname)
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
_FIXTURE_SENSITIVE = "assert bad(x)"
_FIXTURE_ROBUST = "assert ok(x)"
def blind_lock():
    write(_FIXTURE_SENSITIVE)
    write(_FIXTURE_ROBUST)
    return True, [], []
def main(argv):
    locked, rows, problems = blind_lock()
    print('blind lock: %s (%d fixture comparisons)' % (locked, len(rows)))
    if not locked:
        return 2
    print('%d violation(s)' % len(measure()))
""", PUBLISHED,
     "A RUNNER NAMED NOTHING LIKE A RUNNER. metamorphic_check.py's blind_lock() "
     "writes a SENSITIVE and a ROBUST fixture, runs on the default path, prints "
     "its result and REFUSES when unlocked -- and the first real run called it "
     "NO FIXTURE SET, because the name list did not have `blind_lock` in it"),
    ("""
CONFIG_CASES = 3
def helper():
    return CONFIG_CASES + 1
def main(argv):
    print('%d finding(s)' % len(scan()))
""", NONE,
     "A SCALAR IS NOT A FIXTURE SET. The constant has to hold DATA -- a list, "
     "tuple, dict or string -- or a counter named CASES pulls its whole module "
     "in and the widening becomes a false-clean machine"),
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
    """The report-only registry, which is the population this is about.

    RETURNS `(tools, why)` AND NEVER A BARE `None`, because the caller has to
    tell THREE states apart and this function used to collapse two of them.

    ── THE DEFECT THIS SHAPE EXISTS FOR, MEASURED 2026-10-06 (cc) ────────────
    Both `except` arms returned `None`, so the caller could only say
    *"COULD NOT READ tools/report_only_checks.py, or its REGISTRY is empty"* --
    a disjunction, printed without knowing which disjunct was true. Driven: one
    entry was appended to `REGISTRY` missing only its `evidence` field, and the
    validator raised `RegistryIncomplete` naming the entry and the field. This
    tool then exited 2 -- the RIGHT code -- under a reason in which **neither
    disjunct held**: the file read fine, and the registry held 76 entries.

    THE EXIT CODE WAS NEVER THE PROBLEM. PR §1.11 is satisfied by refusing to
    fold COULD-NOT-RUN into a pass, and that was already right. What was wrong
    is that the message sent the reader to look for an unreadable file or an
    empty list -- the two places the answer was not -- while the real
    diagnosis, which named the offending tool AND the missing field, was
    discarded by the bare `except`. A third state that cannot say WHY costs the
    same round trip as no third state at all.

    `str(e)` IS CARRIED OUT RATHER THAN SUMMARISED. `RegistryIncomplete`'s own
    message is already the useful artefact; paraphrasing it here would put a
    second, staler wording of the same fact in a second file.

    THE IMPORT ITSELF NOW HAPPENS AT MODULE LEVEL -- see the guarded block at
    the top. This function reads its outcome; it no longer decides when the
    registry is first touched.
    """
    if _ROC is None:
        return None, _ROC_WHY
    try:
        return [e['tool'] for e in _ROC.REGISTRY if e.get('tool')], None
    except Exception as e:                                     # noqa: BLE001
        return None, ('the module imported, but its REGISTRY could not be '
                      'walked -- %s: %s' % (type(e).__name__, e))


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

    tools, why = registry_tools()
    # TWO REFUSALS, NOT ONE DISJUNCTION. Both still exit COULD NOT RUN -- what
    # changed is that each now states the cause it actually observed. See
    # registry_tools() for the run that found the old message saying something
    # false while its exit code was right.
    if tools is None:
        if not a.quiet:
            # NO CLAIM BEYOND THE EXCEPTION. The first draft of this message
            # appended "the file was NOT unreadable and the registry was NOT
            # empty" -- true of a RegistryIncomplete raise and FALSE of a
            # ModuleNotFoundError, which is the same defect this fix is about,
            # reintroduced one line lower. Driven in both directions before it
            # was deleted. The exception line already separates the cases.
            print('\nCOULD NOT READ the report-only registry. THE REAL CAUSE, '
                  'as raised:\n  %s\n\nThe population is that registry and '
                  'nothing else, so this is "could not\nrun", never "nothing '
                  'wrong". No cause beyond the line above is asserted.' % why)
        return EXIT_COULD_NOT_RUN
    if not tools:
        if not a.quiet:
            print('\nTHE REGISTRY READ FINE AND IS GENUINELY EMPTY -- 0 entries '
                  'carrying a `tool`\nkey. Nothing was judged, and that is a '
                  'fact about the registry rather than about\nthis tool. Not '
                  'folded into a pass: an empty population cannot clear '
                  'anything.')
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
