#!/usr/bin/env python
"""Do a tool's SEVERAL ENTRY POINTS read the SAME POPULATION?

    python tools/entry_point_scope_check.py
    python tools/entry_point_scope_check.py --fixtures   # the criteria lock, alone
    python tools/entry_point_scope_check.py --all        # list the CLEARED tools too
    python tools/entry_point_scope_check.py --quiet

Exit 0 clean, 1 findings, 2 COULD NOT RUN. REPORT ONLY.

── THE DEFECT, WHICH COST A REAL SESSION A REAL PUSH ────────────────────────
`tools/tier_a_review_gate.py` had two entry points over one question. A bare run
read the WORKING TREE; the push hook read `merge-base origin/main HEAD..HEAD`. A
session committed a Tier A change, ran the tool to check before pushing, was told

    "No file in this change names a Tier A resource ... Nothing to record"

and was then DENIED by the same tool naming seven resources. **Both answers were
true about what they read and neither was about the question asked.** Recorded on
2026-09-28 as a rule-1.6 defect: the copy a human invokes is not the copy that
enforces.

THAT IS NOT A BUG IN ONE TOOL. It is a shape: a tool grows a second door --
`--explain`, `--check`, `--list`, `--report`, `--pre-push` -- and the new door
enumerates the population ITSELF instead of going through the one the old door
used. Nothing compares them, because each is individually correct.

── WHAT THIS CHECKS, AND WHY IT IS STATIC ───────────────────────────────────
For each tool with more than one REAL-DATA entry point, it reads the parse tree
and asks: does each entry-point branch reach the SAME population-enumerating
call? A branch with its own private enumeration is the finding.

It does NOT run the tools. Running both doors of 40 tools and diffing their
output would be a better check and a much slower one, and several doors WRITE --
`--fix`, `--propose`, `--fix-rollup-list`. A static answer that is honest about
being static beats a dynamic one nobody waits for.

── THE DISTINCTION THAT KEEPS THE POPULATION SMALL ──────────────────────────
**`--fixtures` and `--selftest` ARE NOT SECOND DOORS.** They read no real data --
that is their entire purpose, and it is discipline 5: the deep check runs with its
subject NOT trusted. A tool whose only extra flag is `--fixtures` has ONE door.
Counting them would have produced 70 candidates of which most are correct by
construction, and a checker reporting 70 rows of which 60 are right is one nobody
runs twice.

So the entry-point vocabulary below is deliberately the flags that read REAL
state. It is a hand-kept list, which is a known weakness this platform has paid
for before, so `--all` prints every tool it considered and the count is published
as CHECKED / UNIVERSE rather than implied.

── WHAT IT CANNOT SEE, stated rather than discovered later ──────────────────
  * A shared accessor that itself branches on the flag. Both doors then reach the
    same function name and this reports CLEAN while the divergence lives one level
    down. tier_a_review_gate's ORIGINAL defect was NOT of this shape, but its FIX
    is -- default_scope_diff() now reads both ranges deliberately -- so a tool
    doing it on purpose and a tool doing it by accident look identical here.
  * Dispatch through a table or a dict of handlers rather than an `if` on the
    flag. The branch is then not lexically inside a conditional and its calls are
    attributed to the whole function.
  * Anything a subprocess does. A door that shells out to another tool is a call
    this cannot follow.
"""
import argparse
import ast
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN, finish                 # noqa: E402

CONTROLLED_BY = ['tests/run_entry_point_scope_probe.py']
CRITERIA_VERSION = '2026-09-28.1'

# ── THE CRITERIA ─────────────────────────────────────────────────────────────
# Flags that open a door onto REAL state. See the header for why --fixtures and
# --selftest are deliberately absent.
REAL_DATA_FLAGS = (
    '--explain', '--check', '--list', '--report', '--pre-push', '--dry-run',
    '--fix', '--propose', '--apply', '--verify', '--audit', '--json',
    '--planned', '--all',
)
# Flags that read NO real state. Named, so the exclusion is auditable rather than
# an omission somebody has to notice.
ISOLATED_FLAGS = ('--fixtures', '--selftest', '--self-check', '--help')

# Calls that ENUMERATE A POPULATION. A door that calls one of these directly is
# deciding for itself what the universe is.
POPULATION_CALLS = (
    'tracked', 'all_tests', 'promoted', 'load_identities', 'load_reviews',
    'load_register', 'walk', 'listdir', 'glob', 'iglob', 'ls_files',
    'working_diff', 'push_range', 'default_scope_diff', 'outgoing_files',
    'changed_files', 'git_ls_files', 'suites', 'test_files', 'read_register',
    'registered_resources', '_registered_resources', '_mention_corpus',
)

FINDING = 'FINDING'
CLEAN_ONE_DOOR = 'only one real-data entry point'
CLEAN_SHARED = 'every entry point reaches the same population call'
CLEAN_NO_POP = 'no entry-point branch enumerates a population directly'


def _flag_of(test):
    """The entry-point flag a conditional is keyed on, or None.

    Reads the three shapes this repo actually uses: `args.check`,
    `'--check' in argv`, and `opt('--check')`.
    """
    out = []
    for node in ast.walk(test):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and node.value.startswith('--'):
            out.append(node.value)
        elif isinstance(node, ast.Attribute):
            out.append('--' + node.attr.replace('_', '-'))
    return out


def _calls_in(node):
    """(population calls, called module-level function names) inside `node`."""
    pop, called = set(), set()
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        f = sub.func
        name = f.id if isinstance(f, ast.Name) else (
            f.attr if isinstance(f, ast.Attribute) else None)
        if name is None:
            continue
        if name in POPULATION_CALLS:
            pop.add(name)
        else:
            called.add(name)
    return pop, called


# ── ONE LEVEL WAS NOT ENOUGH, AND THE FIRST REAL RUN PROVED IT ──────────────
# The first version read only the calls LEXICALLY inside an entry-point branch. It
# reported 9 candidate tools and CLEAN for all nine, every one of them with the
# reason "no entry-point branch enumerates a population directly" -- because this
# repo dispatches: `if '--check' in argv: return cmd_check()`, and the enumeration
# is inside cmd_check(). A checker that cannot see the shape it was built for
# reports clean for ever, which is the defect it exists to find, one level up.
#
# So calls are RESOLVED through module-level functions, to a bounded depth. Depth
# is bounded rather than full because a cycle would hang and a full call graph is
# a different tool; DEPTH is printed, so a reader knows how far it looked.
RESOLVE_DEPTH = 3


def _resolve(node, funcs, depth=RESOLVE_DEPTH, seen=None):
    """Population calls reachable from `node` through <= depth module functions."""
    seen = seen if seen is not None else set()
    pop, called = _calls_in(node)
    if depth <= 0:
        return pop
    for name in called:
        if name in seen or name not in funcs:
            continue
        seen.add(name)
        pop |= _resolve(funcs[name], funcs, depth - 1, seen)
    return pop


DEFAULT_DOOR = '(no flag -- the bare run)'


def doors(src):
    """{door: {population calls}} for one module's source.

    A door is an entry-point FLAG branch, plus DEFAULT_DOOR for the path a bare
    run takes -- which is the door that mattered most in the defect this exists
    for: tier_a_review_gate's bare run read the working tree while the push path
    read a commit range, and the bare run has no flag to key on.
    """
    tree = ast.parse(src)
    funcs = {n.name: n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    found, flagged_nodes = {}, []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        flags = [f for f in _flag_of(node.test) if f in REAL_DATA_FLAGS]
        if not flags:
            continue
        flagged_nodes.append(node)
        calls = _resolve(node, funcs)
        for fl in flags:
            found.setdefault(fl, set()).update(calls)

    # ── SHARED SETUP BELONGS TO EVERY DOOR, NOT TO THE BARE ONE ─────────────
    # The second real run reported probe_selector.py as a finding and it was not
    # one: `corpus_probes()` runs BEFORE the `--all` branch, so it is setup every
    # door goes through -- and attributing it to the bare run alone made the two
    # doors look like they read different things. A checker that flags shared
    # setup is a checker whose findings get ignored.
    #
    # So the calls outside every flag branch are SHARED, and each door's
    # population is `shared | its own`. The bare run is exactly `shared`.
    main = funcs.get('main')
    if main is not None:
        inside = set()
        for fn in flagged_nodes:
            for sub in ast.walk(fn):
                inside.add(id(sub))
        shared = set()
        for sub in ast.walk(main):
            if id(sub) in inside or not isinstance(sub, ast.Call):
                continue
            f = sub.func
            nm = f.id if isinstance(f, ast.Name) else (
                f.attr if isinstance(f, ast.Attribute) else None)
            if nm is None:
                continue
            if nm in POPULATION_CALLS:
                shared.add(nm)
            elif nm in funcs:
                shared |= _resolve(funcs[nm], funcs, RESOLVE_DEPTH - 1, {nm})
        for fl in list(found):
            found[fl] = found[fl] | shared
        if shared:
            found[DEFAULT_DOOR] = shared
    return found


# ── POPULATION FAMILIES, AND WHY THE CRITERION NEEDED THEM ──────────────────
# The second real run also reported tier_a_review_gate.py, correctly noting that
# `--list` reads only the review ledger while the bare run reads a diff. That is
# NOT the defect: the two doors answer DIFFERENT QUESTIONS -- "what is owed" and
# "what did this change touch" -- and a tool is allowed to have both.
#
# THE REAL DEFECT WAS TWO DOORS READING TWO DIFFERENT MEMBERS OF ONE FAMILY:
# working_diff() and push_range() are both "what changed", and that is why their
# disagreement was a contradiction rather than two facts. So a finding requires a
# family in which BOTH doors enumerate, and enumerate DIFFERENTLY. A door that
# reads no scope accessor at all is not disagreeing about scope.
FAMILIES = {
    'scope-of-change': ('working_diff', 'push_range', 'default_scope_diff',
                        'outgoing_files', 'changed_files'),
    'file-tree': ('walk', 'listdir', 'glob', 'iglob', 'tracked', 'git_ls_files',
                  'all_tests', 'test_files', 'suites'),
    'register': ('load_register', 'load_reviews', 'load_identities',
                 'read_register', 'promoted', 'registered_resources',
                 '_registered_resources', '_mention_corpus'),
}


def classify(door_map):
    """FINDING when two doors read DIFFERENT MEMBERS OF ONE population family."""
    with_calls = {k: v for k, v in door_map.items() if v}
    if len(door_map) < 2:
        return CLEAN_ONE_DOOR, {}
    if len(with_calls) < 2:
        return CLEAN_NO_POP, with_calls
    diverging = {}
    for fam, members in FAMILIES.items():
        per_door = {d: set(c for c in calls if c in members)
                    for d, calls in with_calls.items()}
        active = {d: c for d, c in per_door.items() if c}
        if len(active) < 2:
            continue                      # only one door reads this family
        sets = list(active.values())
        if not all(s2 == sets[0] for s2 in sets):
            diverging[fam] = active
    if diverging:
        return FINDING, diverging
    return CLEAN_SHARED, with_calls


# ── THE FIXTURE LOCK (discipline 1) ──────────────────────────────────────────
# Hand-built sources with an expected verdict each, classified FIRST, reading no
# real file. The criteria were written from the tier_a_review_gate defect before
# this tool was pointed at tools/.
FIXTURES = (
    ("""
def main(argv):
    if args.explain:
        d = working_diff()
    if args.pre_push:
        d = push_range()
""", FINDING, 'THE NAMED DEFECT: two doors, two different enumerations'),
    ("""
def main(argv):
    if args.explain:
        d = default_scope_diff()
    if args.pre_push:
        d = default_scope_diff()
""", CLEAN_SHARED, 'the fix for that defect: both doors, one accessor'),
    ("""
def main(argv):
    if args.check:
        print('x')
    if args.list:
        print('y')
""", CLEAN_NO_POP, 'two doors, neither enumerates anything itself'),
    ("""
def main(argv):
    if args.check:
        d = tracked('*.py')
""", CLEAN_ONE_DOOR, 'ONE real-data door cannot diverge from itself'),
    ("""
def main(argv):
    if args.fixtures:
        run_fixtures()
    if args.check:
        d = tracked('*.py')
""", CLEAN_ONE_DOOR,
     '--fixtures is NOT a second door -- it reads no real state, which is the '
     'whole point of an isolated validation'),
    ("""
def main(argv):
    if args.check or args.explain:
        d = working_diff()
    if args.pre_push:
        d = working_diff()
""", CLEAN_SHARED,
     'one branch serving two flags is one door for both, and all three agree'),
    ("""
def main(argv):
    if '--check' in argv:
        d = all_tests()
    if '--list' in argv:
        d = suites()
""", FINDING,
     'the `in argv` spelling must be read too -- half this repo uses it'),
    ("""
def main(argv):
    if args.report:
        rows = load_register()
    if args.fix:
        rows = load_register()
        write(rows)
""", CLEAN_SHARED,
     'a WRITING door is still fine when it reads the same population first'),
    # ── THE TWO FIXTURES THE REAL RUNS PAID FOR ──────────────────────────────
    ("""
def main(argv):
    probes = listdir(TESTS)
    if args.all:
        for p in probes:
            f = walk(p)
    for p in probes:
        f = walk(p)
""", CLEAN_SHARED,
     'SHARED SETUP BELONGS TO EVERY DOOR: corpus_probes() runs before the branch, '
     'and attributing it to the bare run alone made probe_selector.py read as a '
     'finding when both doors go through it'),
    ("""
def main(argv):
    if args.list:
        rows = load_reviews()
        return 0
    d = default_scope_diff()
    rows = load_reviews()
""", CLEAN_SHARED,
     'TWO DOORS MAY ANSWER DIFFERENT QUESTIONS: --list reads only the ledger and '
     'no scope accessor at all, so it is not DISAGREEING about scope -- this is '
     'tier_a_review_gate AFTER its fix and must not report'),
    ("""
def main(argv):
    rows = load_reviews()
    if args.explain:
        d = working_diff()
    if args.pre_push:
        d = push_range()
""", FINDING,
     '...but two doors reading DIFFERENT MEMBERS OF ONE FAMILY is the defect, and '
     'a shared register read alongside it must not mask that'),
)


def run_fixtures(verbose=False):
    bad = []
    for src, want, why in FIXTURES:
        try:
            got, _detail = classify(doors(src))
        except SyntaxError as e:
            bad.append('fixture does not parse (%s)' % e)
            continue
        if got != want:
            bad.append('EXPECTED %s, got %s -- %s' % (want, got, why))
        elif verbose:
            print('  ok   %-46s %s' % (want, why))
    return bad


# ── THE REAL RUN ─────────────────────────────────────────────────────────────
def tool_files():
    out = subprocess.run(['git', 'ls-files', 'tools/*.py'], cwd=REPO,
                         capture_output=True, text=True, encoding='utf-8',
                         errors='replace').stdout
    return [f.strip() for f in out.split('\n')
            if f.strip() and not f.endswith('__init__.py')]


def main(argv):
    ap = argparse.ArgumentParser(add_help=True,
                                 description=__doc__.split('\n')[0])
    ap.add_argument('--fixtures', action='store_true',
                    help='run the criteria lock alone -- reads no real file')
    ap.add_argument('--all', action='store_true',
                    help='also list every tool considered, with why it cleared')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args(argv)

    if not a.quiet:
        print('ENTRY-POINT SCOPE DIVERGENCE -- criteria %s' % CRITERIA_VERSION)

    bad = run_fixtures(verbose=(a.fixtures and not a.quiet))
    if bad:
        if not a.quiet:
            print('\nCRITERIA LOCK FAILED -- %d of %d fixtures misclassified.'
                  % (len(bad), len(FIXTURES)))
            for b in bad:
                print('  ! %s' % b)
            print('\nNOTHING REAL WAS JUDGED. Reporting a clean sweep from '
                  'criteria that cannot\nclassify a hand-built case is the '
                  'defect this tool exists to find.')
        return EXIT_COULD_NOT_RUN
    if not a.quiet:
        print('criteria lock: %d/%d fixtures classify correctly, on hand-built '
              'sources only' % (len(FIXTURES), len(FIXTURES)))
    if a.fixtures:
        return 0

    files = tool_files()
    if not files:
        if not a.quiet:
            print('\nNO TOOLS MATCHED. That is not a clean sweep -- the git call '
                  'failed or the\npattern is wrong, which is a different fact '
                  'from a clean repo.')
        return EXIT_COULD_NOT_RUN

    findings, cleared, unparsed, multi = [], [], [], 0
    for rel in files:
        try:
            src = io.open(os.path.join(REPO, rel), encoding='utf-8',
                          errors='replace').read()
        except OSError as e:
            unparsed.append('%s -- could not read: %s' % (rel, e))
            continue
        try:
            dm = doors(src)
        except SyntaxError as e:
            unparsed.append('%s -- does not parse: %s' % (rel, e))
            continue
        verdict, detail = classify(dm)
        if len(dm) >= 2:
            multi += 1
        if verdict == FINDING:
            findings.append((rel, sorted(dm), detail))
        else:
            cleared.append((rel, verdict, sorted(dm)))

    if not a.quiet:
        print('read %d tool(s); %d have TWO OR MORE real-data entry points and '
              'are the population this checks' % (len(files), multi))
        print('\nCHECKED / UNIVERSE: %d of %d tools in tools/ (%.0f%%) have more '
              'than one\n  real-data door and could diverge at all. The other %d '
              'have one door or none,\n  and a single door cannot disagree with '
              'itself -- that is not coverage, it is\n  the population being '
              'genuinely smaller than the directory.'
              % (multi, len(files), (100.0 * multi / len(files)) if files else 0,
                 len(files) - multi))
        print('  EXCLUDED BY NAME, not by omission: %s read no real state, so a '
              'tool whose\n  only extra flag is one of those has ONE door.'
              % ', '.join(ISOLATED_FLAGS[:3]))
        if a.all:
            print('\nCLEARED (%d), with the reason each cleared:' % len(cleared))
            for rel, why, dm in cleared:
                if len(dm) >= 2:
                    print('  - %-44s %s  doors=%s'
                          % (os.path.basename(rel), why, ' '.join(dm)))

    return finish(
        ['%s  doors %s enumerate DIFFERENT populations: %s'
         % (rel, ' '.join(dm),
            '; '.join('%s -> %s' % (k, ','.join(sorted(v)))
                      for k, v in sorted(detail.items())))
         for rel, dm, detail in findings],
        could_not_run=unparsed, quiet=a.quiet,
        clean_line='\nCLEAN -- no tool has two real-data entry points that '
                   'enumerate different populations.')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
