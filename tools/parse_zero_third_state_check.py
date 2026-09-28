#!/usr/bin/env python
"""Does a checker treat a ZERO-ITEM CORPUS as a clean sweep?

    python tools/parse_zero_third_state_check.py
    python tools/parse_zero_third_state_check.py --fixtures   # criteria lock alone
    python tools/parse_zero_third_state_check.py --all        # list the cleared too
    python tools/parse_zero_third_state_check.py --propose    # paste-ready guards
    python tools/parse_zero_third_state_check.py --quiet

Exit 0 clean, 1 findings, 2 COULD NOT RUN. REPORT ONLY -- it is not wired into
any hook and it proposes rather than applies (discipline 11: a detector that
blesses its own fix is the fail-open one step later).

── THE DEFECT ───────────────────────────────────────────────────────────────
A checker enumerates a corpus, iterates it, finds nothing, and prints

    read 0 file(s); 0 finding(s)
    CLEAN

That output is indistinguishable from a real clean sweep and it is the SAME
FAILURE the coverage-denominator work already names one level up -- "0 of 0" is
not 100%. The corpus is empty because the `git ls-files` pattern stopped
matching after a directory move, because the subprocess failed and returned '',
because the extension changed, or because the extraction regex went stale. None
of those is a repo with nothing wrong in it, and NONE OF THEM PRINTS AN ERROR.

PR 1.11 already settles what to do: **COULD NOT RUN is a third state and is never
folded into passed.** This tool is that rule applied to the corpus rather than to
a missing dependency.

── WHAT IT LOOKS FOR, AND WHY THE POPULATION IS SMALL ON PURPOSE ────────────
For each tool in `tools/` with a `main()`, it looks for a CORPUS VARIABLE:

  1. assigned in `main` from a call,
  2. whose callee enumerates a corpus -- `glob`, `iglob`, `os.walk`, `listdir`,
     or a module function that runs `git ls-files`, resolved to CORPUS_DEPTH,
  3. whose `len()` is PRINTED. A count that never reaches the reader cannot be
     misread as coverage, so it is not this defect.

Then it asks what happens when that variable is empty:

  GUARDED       `if not X:` (or `len(X) == 0`) reaching EXIT_COULD_NOT_RUN
  WRONG EXIT    the guard exists and returns something else -- usually 0, which
                is the defect wearing a check
  NO GUARD      nothing tests it at all

**THE COULD-NOT-TELL COUNT IS PUBLISHED, NOT SWALLOWED.** A tool where no corpus
variable could be located is NOT cleared -- it is counted and named under
`--all`, because "this tool has no corpus variable I could find" and "this tool
is safe" are different statements and the difference is the whole subject here.

── WHAT IT CANNOT SEE, stated rather than discovered later ──────────────────
  * A corpus enumerated INSIDE a scan function and never surfaced to `main`.
    Most of `tools/` is this shape, which is why the could-not-tell figure is the
    larger number and is printed first.
  * A guard written as `assert files`, as an early `return` from a helper, or as
    a `try/except` around the enumeration. Only the two `if` spellings count.
  * A corpus that is legitimately allowed to be empty. `conflict_marker_check`'s
    outgoing-file list is empty on a clean push and MUST NOT fail -- which is
    exactly why this proposes and does not apply.
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

CONTROLLED_BY = ['tests/run_parse_zero_third_state_probe.py']
CRITERIA_VERSION = '2026-09-29.1'

# ── THE CRITERIA ─────────────────────────────────────────────────────────────
# Calls that enumerate a corpus DIRECTLY. Deliberately not `open` or `read`: one
# file is not a corpus and a count of one file is not a coverage figure.
CORPUS_DIRECT = ('glob', 'iglob', 'walk', 'listdir', 'ls_files', 'rglob')
# The marker for the repo's own corpus call. Every corpus in tools/ that is not a
# glob comes from here.
CORPUS_MARKER = 'ls-files'
# How far to resolve through module functions looking for the enumeration. Two,
# because this repo writes `files = suite_files()` -> `tracked()` -> `git
# ls-files` and one level found neither assertion_label_shape_check nor
# checker_denominator.
CORPUS_DEPTH = 3

GUARDED = 'GUARDED -- empty corpus exits COULD NOT RUN'
WRONG_EXIT = 'GUARD PRESENT, WRONG EXIT -- an empty corpus is reported as a result'
NO_GUARD = 'NO GUARD -- a zero-item corpus reads as a clean sweep'
NO_CORPUS = 'COULD NOT TELL -- no corpus variable located in main()'


def _callee(node):
    f = node.func
    return f.attr if isinstance(f, ast.Attribute) else (
        f.id if isinstance(f, ast.Name) else None)


def _is_corpus_expr(node, tainted):
    """Is this expression an enumeration, or built from one?"""
    for s in ast.walk(node):
        if isinstance(s, ast.Call) and _callee(s) in CORPUS_DIRECT:
            return True
        if isinstance(s, ast.Constant) and isinstance(s.value, str) \
                and CORPUS_MARKER in s.value:
            return True
        if isinstance(s, ast.Name) and s.id in tainted:
            return True
    return False


# ── THE CALLEE MUST *RETURN* THE ENUMERATION, NOT MERELY CONTAIN ONE ─────────
# The first real run reported 28 findings and the majority were not this defect.
# `bad = run_fixtures()`, `res = scan()`, `found = classify()` -- every one of
# those functions reads a corpus somewhere inside, so "does this function touch
# an enumeration" matched all of them. But what they RETURN is a FINDINGS list,
# and a findings list that is empty is a clean sweep. That is the correct answer.
#
# THE DENOMINATOR IS THE THING READ; THE NUMERATOR IS THE THING FOUND, and only
# the denominator going to zero is a silent failure. So the callee qualifies only
# when the enumeration REACHES ITS RETURN VALUE -- tracked() returns a list
# comprehension over `git ls-files` output and qualifies; scan() returns rows it
# appended while looping over that same output and does not.
#
# The cost is stated rather than discovered: a real corpus assembled by appending
# inside a loop is MISSED. That is a false negative, it is locked as a fixture,
# and it is the direction to be wrong in for a report-only sweep -- 28 rows of
# which 6 are real is a checker nobody runs twice.
def _path_shaped(node, loop_names):
    """Is this appended value A PATH rather than a described defect?

    THE LINE BETWEEN A CORPUS BUILDER AND A FINDINGS BUILDER, and both are
    `out = []` plus `out.append(...)` inside a loop, so the loop shape cannot
    separate them. What is APPENDED can: `out.append(os.path.join(root, f))` is
    assembling a file list, and `out.append({'file': rel, 'why': msg})` or
    `out.append('%s:%d bad thing' % ...)` is assembling findings. Both
    checker_control_check.test_files() and probe_selector.corpus_probes() are the
    first shape and both were missed before this.
    """
    if isinstance(node, ast.Name) and node.id in loop_names:
        return True
    if isinstance(node, ast.Call) and _callee(node) == 'join':
        return True
    if isinstance(node, ast.Call) and _callee(node) in ('abspath', 'relpath',
                                                        'normpath', 'basename'):
        return True
    return False


def _returns_enumeration(fn, funcs, depth=CORPUS_DEPTH, seen=None):
    """Does the value `fn` RETURNS derive from a corpus enumeration?"""
    seen = seen if seen is not None else set()
    tainted = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and _is_corpus_expr(n.value, tainted):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    tainted.add(t.id)
        # `for f in glob(...)` taints the loop target the same way
        if isinstance(n, ast.For) and _is_corpus_expr(n.iter, tainted) \
                and isinstance(n.target, ast.Name):
            tainted.add(n.target.id)
    # ── THE APPEND-IN-A-LOOP CORPUS BUILDER ─────────────────────────────────
    # Run after the assignment pass so a loop over an already-tainted name counts.
    for n in ast.walk(fn):
        if not isinstance(n, ast.For):
            continue
        loop_names = set(t.id for t in ast.walk(n.target)
                         if isinstance(t, ast.Name))
        if not (_is_corpus_expr(n.iter, tainted)
                or any(isinstance(s, ast.Call) and _callee(s) in CORPUS_DIRECT
                       for s in ast.walk(n.iter))):
            continue
        for s in ast.walk(n):
            if (isinstance(s, ast.Call) and _callee(s) in ('append', 'extend')
                    and isinstance(s.func, ast.Attribute)
                    and isinstance(s.func.value, ast.Name)
                    and s.args and _path_shaped(s.args[0], loop_names)):
                tainted.add(s.func.value.id)
    for n in ast.walk(fn):
        if not isinstance(n, ast.Return) or n.value is None:
            continue
        if _is_corpus_expr(n.value, tainted):
            return True
        if depth > 0:
            for s in ast.walk(n.value):
                if isinstance(s, ast.Call):
                    nm = _callee(s)
                    if nm in funcs and nm not in seen:
                        seen.add(nm)
                        if _returns_enumeration(funcs[nm], funcs, depth - 1, seen):
                            return True
    return False


def _printed_lens(fn):
    """Names X where `len(X)` reaches a print or a format string."""
    out = set()
    for n in ast.walk(fn):
        emitted = ((isinstance(n, ast.Call) and getattr(n.func, 'id', None) == 'print')
                   or (isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod))
                   or isinstance(n, ast.JoinedStr))
        if not emitted:
            continue
        for s in ast.walk(n):
            if (isinstance(s, ast.Call) and getattr(s.func, 'id', None) == 'len'
                    and s.args and isinstance(s.args[0], ast.Name)):
                out.add(s.args[0].id)
    return out


def _exits_could_not_run(body_nodes, funcs, depth=1):
    """Does this branch body reach exit 2, directly or through one helper?

    `value=2` is the literal `return 2` / `sys.exit(2)` spelling several tools
    use instead of the named constant. THE HELPER HOP IS NOT A CONVENIENCE: the
    first real run reported tools/guard_ablation.py, whose guard reads

        if not S:
            fail('no suite loads api/sd-data.js -- nothing could observe ...')

    and whose fail() prints COULD NOT RUN and exits 2. That is the correct code,
    reported as the defect, because the checker looked only at the lexical body
    -- the same one-level blindness entry_point_scope_check shipped with.
    """
    dumped = ast.dump(ast.Module(body=list(body_nodes), type_ignores=[]))
    if 'EXIT_COULD_NOT_RUN' in dumped or 'value=2' in dumped:
        return True
    if depth <= 0:
        return False
    for n in body_nodes:
        for s in ast.walk(n):
            if isinstance(s, ast.Call):
                nm = _callee(s)
                if nm in funcs and _exits_could_not_run(funcs[nm].body, funcs,
                                                        depth - 1):
                    return True
    return False


def _guard_level(fn, name, funcs=None):
    """3 guarded to COULD NOT RUN, 1 guard with another exit, 0 no guard."""
    funcs = funcs or {}
    best = 0
    for n in ast.walk(fn):
        if not isinstance(n, ast.If):
            continue
        t, hit = n.test, False
        if isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not) \
                and getattr(t.operand, 'id', None) == name:
            hit = True
        if isinstance(t, ast.Compare) and isinstance(t.left, ast.Call) \
                and getattr(t.left.func, 'id', None) == 'len' \
                and t.left.args and getattr(t.left.args[0], 'id', None) == name:
            hit = True
        if not hit:
            continue
        best = max(best, 3 if _exits_could_not_run(n.body, funcs) else 1)
    return best


def classify(src):
    """[(variable, callee, verdict)] for one module's source, or [] if none."""
    tree = ast.parse(src)
    funcs = {n.name: n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    main = funcs.get('main')
    if main is None:
        return []
    printed, out, seen_vars = _printed_lens(main), [], set()
    for n in ast.walk(main):
        if not (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and isinstance(n.value, ast.Call)):
            continue
        var = n.targets[0].id
        if var not in printed or var in seen_vars:
            continue
        nm = _callee(n.value)
        if not (nm in CORPUS_DIRECT
                or (nm in funcs and _returns_enumeration(funcs[nm], funcs))):
            continue
        seen_vars.add(var)
        lvl = _guard_level(main, var, funcs)
        out.append((var, nm, {3: GUARDED, 1: WRONG_EXIT, 0: NO_GUARD}[lvl]))
    return out


# ── THE FIXTURE LOCK (discipline 1) ──────────────────────────────────────────
# Hand-built sources with an expected verdict each, classified FIRST, reading no
# real file.
FIXTURES = (
    ("""
def sources():
    return subprocess.run(['git', 'ls-files', '*.py']).stdout.split()
def main(argv):
    files = sources()
    print('read %d file(s)' % len(files))
    for f in files:
        scan(f)
""", NO_GUARD, 'THE DEFECT: a printed corpus count with nothing testing zero'),
    ("""
def sources():
    return subprocess.run(['git', 'ls-files', '*.py']).stdout.split()
def main(argv):
    files = sources()
    if not files:
        print('NO FILES MATCHED -- that is not a clean repo')
        return EXIT_COULD_NOT_RUN
    print('read %d file(s)' % len(files))
""", GUARDED, 'the fix: an empty corpus is the third state, not a pass'),
    ("""
def sources():
    return subprocess.run(['git', 'ls-files', '*.py']).stdout.split()
def main(argv):
    files = sources()
    if not files:
        print('nothing to do')
        return 0
    print('read %d file(s)' % len(files))
""", WRONG_EXIT,
     'THE GUARD WEARING A CHECK: it tests the empty case and then reports it as '
     'a pass, which is the defect with a branch in front of it'),
    ("""
def sources():
    return subprocess.run(['git', 'ls-files', '*.py']).stdout.split()
def main(argv):
    files = sources()
    if len(files) == 0:
        return EXIT_COULD_NOT_RUN
    print('read %d file(s)' % len(files))
""", GUARDED, 'the `len(X) == 0` spelling counts as the same guard'),
    ("""
def main(argv):
    files = glob.glob('*.py')
    print('read %d file(s)' % len(files))
""", NO_GUARD, 'a bare glob is a corpus enumeration too, with no helper to read'),
    ("""
def helper():
    return io.open(PATH).read()
def main(argv):
    src = helper()
    print('read %d byte(s)' % len(src))
""", None,
     'ONE FILE IS NOT A CORPUS. `open` is deliberately absent from the '
     'enumeration vocabulary, or every tool that reads a config joins the '
     'population and the finding list becomes unreadable'),
    ("""
def sources():
    return subprocess.run(['git', 'ls-files', '*.py']).stdout.split()
def main(argv):
    files = sources()
    for f in files:
        scan(f)
    return finish(findings)
""", None,
     'A COUNT THAT IS NEVER PRINTED CANNOT BE MISREAD AS COVERAGE. The corpus is '
     'still enumerated, but nothing tells a reader it was 811 or 0, so this is a '
     'different defect and not this one'),
    ("""
def fail(msg):
    print('COULD NOT RUN: ' + msg)
    sys.exit(2)
def sources():
    return subprocess.run(['git', 'ls-files', '*.py']).stdout.split()
def main(argv):
    files = sources()
    if not files:
        fail('the enumeration returned nothing')
    print('read %d file(s)' % len(files))
""", GUARDED,
     "A GUARD THAT DELEGATES TO A HELPER STILL COUNTS. guard_ablation.py writes "
     "`if not S: fail(...)` and fail() exits 2; reading only the lexical body "
     "reported correct code as the defect, which is the same one-level blindness "
     "this repo has now shipped twice"),
    ("""
def suite_files():
    return tracked('*.py')
def tracked(pat):
    return subprocess.run(['git', 'ls-files', pat]).stdout.split()
def main(argv):
    files = suite_files()
    print('read %d file(s)' % len(files))
""", NO_GUARD,
     'RESOLVED TWO HOPS: `files = suite_files()` -> `tracked()` -> git ls-files. '
     'At one level of resolution this repo\'s two biggest corpora were both '
     'invisible and the tool would have reported a small clean population'),
)


def run_fixtures(verbose=False):
    bad = []
    for src, want, why in FIXTURES:
        try:
            got = classify(src)
        except SyntaxError as e:
            bad.append('fixture does not parse (%s)' % e)
            continue
        verdict = got[0][2] if got else None
        if verdict != want:
            bad.append('EXPECTED %s, got %s -- %s' % (want, verdict, why))
        elif verbose:
            print('  ok   %-28s %s' % (want if want else 'NOT A CORPUS VAR', why))
    return bad


PROPOSAL = """    if not %(var)s:
        print('\\n%(msg)s')
        return EXIT_COULD_NOT_RUN"""
PROPOSAL_MSG = ('NO ITEM MATCHED. That is not a clean sweep -- the enumeration '
                'returned nothing,\\n  which is a different fact from a corpus '
                'with nothing wrong in it.')


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
                    help='also list the cleared tools and the could-not-tells')
    ap.add_argument('--propose', action='store_true',
                    help='print a paste-ready guard per finding. PROPOSES ONLY')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args(argv)

    if not a.quiet:
        print('ZERO-ITEM CORPUS AS A CLEAN SWEEP -- criteria %s' % CRITERIA_VERSION)

    bad = run_fixtures(verbose=(a.fixtures and not a.quiet))
    if bad:
        if not a.quiet:
            print('\nCRITERIA LOCK FAILED -- %d of %d fixtures misclassified.'
                  % (len(bad), len(FIXTURES)))
            for b in bad:
                print('  ! %s' % b)
            print('\nNOTHING REAL WAS JUDGED. Reporting a clean sweep from '
                  'criteria that cannot\nclassify a hand-built case is the very '
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
                  'from a repo with no tools in it.')
        return EXIT_COULD_NOT_RUN

    findings, cleared, no_corpus, unparsed = [], [], [], []
    for rel in files:
        try:
            src = io.open(os.path.join(REPO, rel), encoding='utf-8',
                          errors='replace').read()
        except OSError as e:
            unparsed.append('%s -- could not read: %s' % (rel, e))
            continue
        try:
            rows = classify(src)
        except SyntaxError as e:
            unparsed.append('%s -- does not parse: %s' % (rel, e))
            continue
        if not rows:
            no_corpus.append(rel)
            continue
        for var, callee, verdict in rows:
            if verdict == GUARDED:
                cleared.append((rel, var, callee))
            else:
                findings.append((rel, var, callee, verdict))

    checked = len(files) - len(no_corpus) - len(unparsed)
    if not a.quiet:
        print('read %d tool(s) in tools/' % len(files))
        print('\nCHECKED / UNIVERSE: %d of %d tools (%.0f%%) have a corpus '
              'variable this can\n  locate in main() and judge. THE OTHER %d ARE '
              'NOT CLEARED -- they are COULD NOT\n  TELL, and the commonest '
              'reason is the corpus being enumerated inside a scan\n  function '
              'and never surfaced to main(). "No corpus variable I could find" '
              'and\n  "safe" are different statements, which is the entire '
              'subject of this tool.'
              % (checked, len(files),
                 (100.0 * checked / len(files)) if files else 0, len(no_corpus)))
        print('  %d GUARDED, %d WRONG EXIT, %d NO GUARD, %d unreadable.'
              % (len(cleared),
                 len([f for f in findings if f[3] == WRONG_EXIT]),
                 len([f for f in findings if f[3] == NO_GUARD]), len(unparsed)))
        if a.all:
            print('\nGUARDED (%d) -- an empty corpus already exits COULD NOT RUN:'
                  % len(cleared))
            for rel, var, callee in cleared:
                print('  - %-44s %s <- %s()'
                      % (os.path.basename(rel), var, callee))
            print('\nCOULD NOT TELL (%d), named rather than counted:'
                  % len(no_corpus))
            for rel in no_corpus:
                print('  ? %s' % os.path.basename(rel))
        if a.propose:
            print('\n── PROPOSED GUARDS. THIS TOOL DOES NOT APPLY THEM ─────────'
                  '─────────────────\nDiscipline 11: a detector that applies its '
                  'own fix is the fail-open one step\nlater. Each of these needs '
                  'a human decision first, because SOME OF THESE\nCORPORA ARE '
                  'ALLOWED TO BE EMPTY -- an outgoing-file list is empty on a\n'
                  'clean push and must not fail.')
            if not findings:
                print('\nNOTHING TO PROPOSE -- every corpus variable this could '
                      'locate is already\nguarded. The template it WOULD emit, '
                      'printed so this flag is never silent:\n')
                print(PROPOSAL % {'var': '<corpus>', 'msg': PROPOSAL_MSG})
            for rel, var, callee, _v in findings:
                print('\n%s  (after `%s = %s(...)`)' % (rel, var, callee))
                print(PROPOSAL % {'var': var, 'msg': PROPOSAL_MSG})

    return finish(
        ['%s  `%s` <- %s()  %s' % (rel, var, callee, verdict)
         for rel, var, callee, verdict in findings],
        could_not_run=unparsed, quiet=a.quiet,
        clean_line='\nCLEAN -- every corpus variable this could locate exits '
                   'COULD NOT RUN when its\nenumeration returns nothing.')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
