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

── A DOOR IS NOT ALWAYS A FLAG (added 2026-09-29) ───────────────────────────
Version 1's door vocabulary was flags only, and `tools/claim_provenance.py` has
no flag anywhere -- it dispatches `cmds[argv[0]](argv[1:])` over four `cmd_`
handlers. It was reported as having ONE real-data entry point. It has four.

So a DISPATCH TABLE is now read two ways:
  * as a DOOR VOCABULARY -- each key of a table called through with a key that
    came from the command line is an entry point in its own right; and
  * as a RESOLUTION PATH -- a door that reaches a table reaches what the table
    dispatches to, which is how `checker_denominator.py`'s `spec['universe']()`
    became visible after reading as "enumerates nothing at all".
Both are ABLATED on every real run: the file is read twice, once with table
resolution off, and the run prints the doors and verdicts that only exist
because of it rather than asserting the extension is worth something.

── WHAT IT CANNOT SEE, stated rather than discovered later ──────────────────
  * A shared accessor that itself branches on the flag. Both doors then reach the
    same function name and this reports CLEAN while the divergence lives one level
    down. tier_a_review_gate's ORIGINAL defect was NOT of this shape, but its FIX
    is -- default_scope_diff() now reads both ranges deliberately -- so a tool
    doing it on purpose and a tool doing it by accident look identical here.
  * A subcommand table whose dispatch key is named outside CALLER_KEY_NAMES, or
    reached through a helper that takes the key as a parameter. That is a FALSE
    NEGATIVE and it is deliberate: the looser rule read completeness_check.py's
    `SHAPES[shape](...)` fixture runner as three entry points. Both directions
    are locked as fixtures, so loosening the rule has to change one of them.
  * A table built at runtime, by comprehension, or from `globals()`. Only a dict
    LITERAL assigned to a name is read.
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
CRITERIA_VERSION = '2026-09-29.1'

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

# ── SUBCOMMAND DOORS, ADDED 2026-09-29 ──────────────────────────────────────
# Half this repo's doors are not flags at all. `claim_provenance.py` dispatches
#     cmds = {'scope': cmd_scope, 'types': cmd_types, 'add': cmd_add,
#             'list': cmd_list}
#     return cmds[argv[0]](argv[1:])
# and version 1 reported it as having ONE real-data entry point, because it has
# no `if '--x' in argv` anywhere. It has FOUR. A door vocabulary that only knows
# flags cannot count the doors of a tool that does not use flags.
#
# The same names as ISOLATED_FLAGS, minus the dashes: a `selftest` subcommand is
# no more a real-data door than `--selftest` is.
ISOLATED_SUBCOMMANDS = ('fixtures', 'selftest', 'self-check', 'help', 'version')
SUBCOMMAND_DOOR = '%s (subcommand)'

# A dict literal needs at least this many function values before it is read as a
# dispatch table. One is an assignment, not a table, and treating it as one would
# pull ordinary config dicts into the resolution graph.
HANDLER_TABLE_MIN = 2

# Calls that ENUMERATE A POPULATION. A door that calls one of these directly is
# deciding for itself what the universe is.
POPULATION_CALLS = (
    'tracked', 'all_tests', 'promoted', 'load_identities', 'load_reviews',
    'load_register', 'walk', 'listdir', 'glob', 'iglob', 'ls_files',
    'working_diff', 'push_range', 'default_scope_diff', 'outgoing_files',
    'changed_files', 'git_ls_files', 'suites', 'test_files', 'read_register',
    'registered_resources', '_registered_resources', '_mention_corpus',
    # Added 2026-09-29 with subcommand doors. claim_provenance.py's four doors
    # became visible and every one of them read as "enumerates nothing", which
    # was the vocabulary being short rather than the doors being empty:
    # load_ledger() reads the provenance ledger and load_tier_a() reads the Tier
    # A resource set out of CRITICALITY-TIERS.md. Both are registers.
    'load_ledger', 'load_tier_a',
)

FINDING = 'FINDING'
CLEAN_ONE_DOOR = 'only one real-data entry point'
# REWORDED 2026-09-29. It read "every entry point reaches the same population
# call", which was never quite what classify() decided and got further from it
# with subcommand doors: tier_a_review_gate AFTER its fix clears with --list
# reading only the ledger and the bare run reading a diff as well, and
# claim_provenance clears with four doors reading three different registers.
# The verdict is, and always was, the absence of a disagreement INSIDE one
# family -- so it now says that instead of something stronger it never checked.
CLEAN_SHARED = 'no two doors enumerate different members of one population family'
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


# ── AND FUNCTION RESOLUTION WAS NOT ENOUGH EITHER (2026-09-29) ───────────────
# `_resolve` follows a call to a NAMED function. It cannot follow a call through
# a table, and version 1 said so in "what it cannot see" -- which is the right
# way to ship a gap and the wrong place to leave it. Two real tools sat behind it:
#
#   tools/claim_provenance.py    cmds = {'scope': cmd_scope, ...}
#                                return cmds[argv[0]](argv[1:])
#   tools/checker_denominator.py TOOLS = [{'universe': _apps, 'checked': ...}]
#                                for spec in TOOLS: spec['universe']()
#
# Neither has a `cmds[...]`-shaped call the old resolver could name, so both read
# as "no entry-point branch enumerates a population directly" -- clean, for ever,
# for the same reason version 1 read clean for ever.
#
# A HANDLER TABLE is a dict literal whose string keys map to MODULE-LEVEL
# FUNCTIONS, with at least HANDLER_TABLE_MIN of them. Dicts inside a list count:
# that is exactly checker_denominator's shape. Resolution is ANCHORED ON THE
# TABLE'S NAME -- a region reaches the handlers only if it loads the name the
# table is bound to, directly or through a function it calls. It does NOT
# resolve every table in the module into every door, because over-approximating
# would make two doors look alike and MASK a divergence, which is a worse
# failure than the one being fixed.
def _handler_tables(tree, funcs):
    """{bound name: {key: {function names}}} for every dispatch table in a module.

    A dict literal contributes when its string keys map to module-level functions
    BY NAME; the binding is a table once >= HANDLER_TABLE_MIN DISTINCT FUNCTIONS
    are reachable through it. `X = {...}` and `X = [{...}, {...}]` are both read,
    because this repo writes both.

    COUNTED BY FUNCTION, NOT BY KEY, and the first fixture run is why. In
    checker_denominator's shape every dict in the list carries the SAME key --
    `[{'universe': a}, {'universe': b}]` -- so a key-keyed count collapsed six
    real handlers to one and the table was not recognised at all. The table with
    the most handlers in the repo was the one the threshold discarded.
    """
    tables = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if not targets:
            continue
        dicts = []
        if isinstance(node.value, ast.Dict):
            dicts = [node.value]
        elif isinstance(node.value, (ast.List, ast.Tuple)):
            dicts = [e for e in node.value.elts if isinstance(e, ast.Dict)]
        pairs, distinct = {}, set()
        for d in dicts:
            for k, v in zip(d.keys, d.values):
                if (isinstance(k, ast.Constant) and isinstance(k.value, str)
                        and isinstance(v, ast.Name) and v.id in funcs):
                    pairs.setdefault(k.value, set()).add(v.id)
                    distinct.add(v.id)
        if len(distinct) >= HANDLER_TABLE_MIN:
            for t in targets:
                for k, v in pairs.items():
                    tables.setdefault(t, {}).setdefault(k, set()).update(v)
    return tables


def _table_handlers(table):
    """Every function name any key of `table` dispatches to."""
    out = set()
    for v in table.values():
        out |= v
    return out


def _names_loaded(node):
    """Every bare name READ inside `node`. The anchor for table resolution."""
    return set(n.id for n in ast.walk(node)
               if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load))


def _resolve(node, funcs, depth=RESOLVE_DEPTH, seen=None, tables=None):
    """Population calls reachable from `node` through <= depth module functions.

    `tables` is the handler-table map. When the region loads a table's name, the
    table's handlers join the call set at this level -- so a door that reaches a
    dispatch table reaches what the table dispatches to, bounded by the same
    depth as every other hop.
    """
    seen = seen if seen is not None else set()
    pop, called = _calls_in(node)
    if tables:
        loaded = _names_loaded(node)
        for tname, handlers in tables.items():
            if tname in loaded:
                called |= _table_handlers(handlers)
    if depth <= 0:
        return pop
    for name in called:
        if name in seen or name not in funcs:
            continue
        seen.add(name)
        pop |= _resolve(funcs[name], funcs, depth - 1, seen, tables)
    return pop


# A function whose name is one of these IS an isolated path. A table dispatched
# only from inside one of them is not a door vocabulary -- it is the fixture
# runner picking which fixture to run.
ISOLATED_FUNCTIONS = ('run_fixtures', 'fixtures', 'selftest', 'run_selftest',
                      'self_check', 'run_self_check', 'run_selftests')
# Names that mean THE KEY CAME FROM THE CALLER. `cmds[argv[0]]` is a door
# vocabulary; `SHAPES[shape]` inside a loop over fixtures is not.
CALLER_KEY_NAMES = ('argv', 'args', 'sys', 'opts', 'namespace', 'cmdline')


def _dispatch_tables(tree, tables):
    """Table names used as `T[key-from-the-caller](...)` -- a subcommand dispatch.

    THREE THINGS HAVE TO HOLD, and the first real run paid for the second and
    third. A table that is only READ (`', '.join(sorted(cmds))` in a usage
    message) is not a door vocabulary -- the call is what makes a key an entry
    point. And completeness_check.py's `SHAPES[shape](...)` is a call through a
    table that is NOT a door: it sits inside run_fixtures() and its key is a loop
    variable over the fixture list, so reading it as three subcommands invented
    S1/S2/S3 as entry points on a tool that has none.

      1. something CALLS through the table;
      2. the call site is not inside an ISOLATED_FUNCTIONS body;
      3. the key expression mentions a CALLER_KEY_NAMES name, so the key comes
         from the command line rather than from the tool's own loop.

    Requiring all three is deliberately conservative: a real subcommand table
    keyed by a name outside that vocabulary is MISSED rather than a fixture
    runner being reported as four doors. Stated in the header, not discovered.
    """
    isolated = set()
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and fn.name in ISOLATED_FUNCTIONS:
            for sub in ast.walk(fn):
                isolated.add(id(sub))
    used = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or id(node) in isolated:
            continue
        f = node.func
        if not (isinstance(f, ast.Subscript) and isinstance(f.value, ast.Name)
                and f.value.id in tables):
            continue
        if _names_loaded(f.slice) & set(CALLER_KEY_NAMES):
            used.add(f.value.id)
    return used


DEFAULT_DOOR = '(no flag -- the bare run)'


def doors(src, tables=True):
    """{door: {population calls}} for one module's source.

    A door is an entry-point FLAG branch, a SUBCOMMAND of a dispatch table, plus
    DEFAULT_DOOR for the path a bare run takes -- which is the door that mattered
    most in the defect this exists for: tier_a_review_gate's bare run read the
    working tree while the push path read a commit range, and the bare run has no
    flag to key on.

    `tables=False` disables handler-table resolution AND subcommand doors. It is
    not a user flag; it is how the run reports what the 2026-09-29 extension
    actually resolved, by asking the same question of the same source both ways.
    """
    tree = ast.parse(src)
    funcs = {n.name: n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    tbl = _handler_tables(tree, funcs) if tables else {}
    found, flagged_nodes = {}, []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        flags = [f for f in _flag_of(node.test) if f in REAL_DATA_FLAGS]
        if not flags:
            continue
        flagged_nodes.append(node)
        calls = _resolve(node, funcs, tables=tbl)
        for fl in flags:
            found.setdefault(fl, set()).update(calls)

    # ── SUBCOMMAND DOORS ────────────────────────────────────────────────────
    # Only for a table that is actually CALLED through, and only for keys that
    # are not in the isolated vocabulary. Each key's population is what its
    # handler reaches; shared setup is added below with every other door's.
    for tname in _dispatch_tables(tree, tbl):
        for key, fns in sorted(tbl[tname].items()):
            if key.lower() in ISOLATED_SUBCOMMANDS:
                continue
            calls = set()
            for fn in fns:
                if fn in funcs:
                    calls |= _resolve(funcs[fn], funcs, tables=tbl)
            found.setdefault(SUBCOMMAND_DOOR % key, set()).update(calls)

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
                shared |= _resolve(funcs[nm], funcs, RESOLVE_DEPTH - 1, {nm},
                                   tables=tbl)
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
    # ── AND THE FIRST SUBCOMMAND RUN PAID FOR THESE TWO BEING SEPARATE ──────
    # `load_ledger` and `load_tier_a` were put in `register` alongside the rest
    # and claim_provenance.py reported instantly: `scope` reads the tier doc,
    # `list` reads the provenance ledger, `add` reads both. That is not the
    # defect -- it is the tier_a_review_gate `--list` exemption again. A family
    # is ONE QUESTION with SEVERAL ACCESSORS (working_diff vs push_range, both
    # "what changed"); two doors reading two DIFFERENT registers are answering
    # two different questions and are allowed to. So each is its own family and
    # neither can diverge from the other, which is the true answer and not the
    # convenient one.
    'tier-register': ('load_tier_a',),
    'provenance-ledger': ('load_ledger',),
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
    # ── THE 2026-09-29 TABLE-DISPATCH FIXTURES ───────────────────────────────
    ("""
def cmd_check(argv):
    return working_diff()
def cmd_verify(argv):
    return push_range()
def main(argv):
    cmds = {'check': cmd_check, 'verify': cmd_verify}
    return cmds[argv[0]](argv[1:])
""", FINDING,
     'SUBCOMMAND DOORS: the named defect spelled with a dispatch table and no '
     'flag anywhere. Version 1 read this as ONE door and CLEAN, because its door '
     'vocabulary was flags only'),
    ("""
def cmd_check(argv):
    return default_scope_diff()
def cmd_verify(argv):
    return default_scope_diff()
def main(argv):
    cmds = {'check': cmd_check, 'verify': cmd_verify}
    return cmds[argv[0]](argv[1:])
""", CLEAN_SHARED,
     'THE SILENT HALF of the subcommand shape: the same table with both handlers '
     'on one accessor must not report, or the criterion is "has a table"'),
    ("""
def cmd_check(argv):
    print('x')
def cmd_verify(argv):
    print('y')
def main(argv):
    cmds = {'check': cmd_check, 'verify': cmd_verify}
    return cmds[argv[0]](argv[1:])
""", CLEAN_NO_POP,
     'two subcommand doors, neither enumerating anything -- a table is a door '
     'vocabulary, not a finding'),
    ("""
def cmd_check(argv):
    return working_diff()
def cmd_selftest(argv):
    return push_range()
def main(argv):
    cmds = {'check': cmd_check, 'selftest': cmd_selftest}
    return cmds[argv[0]](argv[1:])
""", CLEAN_ONE_DOOR,
     'a `selftest` SUBCOMMAND is no more a real-data door than --selftest is, so '
     'this has ONE door and the isolated vocabulary is spelled both ways'),
    ("""
def cmd_check(argv):
    print('x')
def cmd_verify(argv):
    print('y')
def main(argv):
    cmds = {'check': cmd_check, 'verify': cmd_verify}
    print('commands: ' + ', '.join(sorted(cmds)))
    return 0
""", CLEAN_ONE_DOOR,
     'A TABLE THAT IS ONLY PRINTED IS NOT A DOOR VOCABULARY. The keys become '
     'entry points when something CALLS through the table, not when a usage '
     'message lists them'),
    ("""
def a_universe():
    return tracked('*.py')
def b_universe():
    return walk('.')
SPECS = [{'universe': a_universe}, {'universe': b_universe}]
def measure():
    return [s['universe']() for s in SPECS]
def main(argv):
    if args.report:
        return measure()
    if args.json:
        return tracked('*.py')
""", FINDING,
     "HANDLER-TABLE RESOLUTION, checker_denominator's shape: the accessors are "
     'behind `s[key]()` in a list of dicts, and without following the table the '
     '--report door reads as enumerating nothing at all'),
    ("""
def a_universe():
    return tracked('*.py')
def b_universe():
    return tracked('*.js')
SPECS = [{'universe': a_universe}, {'universe': b_universe}]
def measure():
    return [s['universe']() for s in SPECS]
def main(argv):
    if args.report:
        return measure()
    if args.json:
        return tracked('*.py')
""", CLEAN_SHARED,
     '...and its silent half: resolving the table must not report when the '
     'handlers agree with the other door'),
    ("""
def helper():
    return tracked('*.py')
CONFIG = {'name': 'x', 'mode': 'y'}
def main(argv):
    if args.report:
        return CONFIG
    if args.json:
        return helper()
""", CLEAN_NO_POP,
     'A DICT OF STRINGS IS NOT A HANDLER TABLE. Values must be module-level '
     'FUNCTIONS, or every config dict in the repo joins the resolution graph'),
    ("""
def s1(src, path):
    return []
def s2(src, path):
    return []
SHAPES = {'S1': s1, 'S2': s2}
def run_fixtures():
    for name, src, shape, want in FIXTURES:
        got = SHAPES[shape](src, '<fixture>')
def main(argv):
    if args.json:
        return walk('.')
""", CLEAN_ONE_DOOR,
     "THE FIXTURE RUNNER IS NOT A DOOR VOCABULARY. completeness_check.py's "
     "SHAPES[shape](...) sits inside run_fixtures() and is keyed by a loop "
     "variable, and the first real run invented S1/S2/S3 as three entry points "
     "on a tool that has one"),
    ("""
def cmd_check(argv):
    return working_diff()
def cmd_verify(argv):
    return push_range()
CMDS = {'check': cmd_check, 'verify': cmd_verify}
def dispatch(name):
    return CMDS[name](())
def main(argv):
    return dispatch(argv[0])
""", CLEAN_ONE_DOOR,
     'AND THE COST OF THAT CONSERVATISM, STATED AS A FIXTURE RATHER THAN FOUND '
     'LATER: a real subcommand table reached through a helper whose key name is '
     'not in the caller vocabulary is MISSED. This is a false NEGATIVE and it is '
     'locked, so the day the rule is loosened this fixture is what changes'),
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
    # ── WHAT THE TABLE EXTENSION ACTUALLY RESOLVED, MEASURED NOT ASSERTED ───
    # Every file is read TWICE -- once with table dispatch resolved and once
    # with it off -- and the delta is printed. This is discipline 12: remove the
    # one named layer on already-clean code and measure what it alone catches.
    # Without it "we added table resolution" is a claim about the diff; with it
    # the run publishes the doors and the verdicts that only exist because of it.
    gained = []
    for rel in files:
        try:
            src = io.open(os.path.join(REPO, rel), encoding='utf-8',
                          errors='replace').read()
        except OSError as e:
            unparsed.append('%s -- could not read: %s' % (rel, e))
            continue
        try:
            dm = doors(src)
            dm_notables = doors(src, tables=False)
        except SyntaxError as e:
            unparsed.append('%s -- does not parse: %s' % (rel, e))
            continue
        verdict, detail = classify(dm)
        v_old, _ = classify(dm_notables)
        new_doors = sorted(set(dm) - set(dm_notables))
        new_pop = sorted(set().union(*dm.values()) - set().union(*dm_notables.values())
                         if dm else [])
        if new_doors or new_pop or verdict != v_old:
            gained.append((rel, new_doors, new_pop, v_old, verdict))
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

        # ── THE ABLATION: what table dispatch alone is worth ────────────────
        print('\nTABLE-DISPATCH RESOLUTION, ABLATED (2026-09-29): %d tool(s) '
              'read DIFFERENTLY with it\n  off. Version 1 resolved calls through '
              'named functions only, so a tool that\n  dispatches through a dict '
              'of handlers -- `cmds[argv[0]](...)`, `spec[k]()` -- had\n  its '
              'doors and its enumerations attributed to nothing at all.'
              % len(gained))
        if not gained:
            print('  NOTHING GAINED. That is a real result and not a good one: '
                  'either no tool in\n  tools/ dispatches through a table, or '
                  'the resolver is not seeing the ones that\n  do. Read it '
                  'before treating the extension as load-bearing.')
        for rel, nd, npop, v_old, v_new in gained:
            print('  + %s' % os.path.basename(rel))
            if nd:
                print('      doors only this resolution sees: %s'
                      % ' '.join(nd))
            if npop:
                print('      populations only this resolution reaches: %s'
                      % ' '.join(npop))
            if v_old != v_new:
                print('      VERDICT MOVED: %s  ->  %s' % (v_old, v_new))
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
