"""Every tool that HAS a selftest must have it RUN by the suite.

    python tests/run_tool_selftest_probe.py
    python tests/run_tool_selftest_probe.py --list

── WHY THIS EXISTS, AND IT WAS FOUND BY TURNING ITEM 47 ON MY OWN WORK ───────
`tools/first_article_inspection.py` was pointed at four tools built on 2026-09-15
and reported two of them as NO SUITE AT ALL -- 10 and 12 unverified claims. Both
have a `--selftest` with every arm passing. The FAI tool was right anyway, and the
reason is the whole point of this file:

    `tools/run_all_tests.py` discovers `tests/**` plus `api/*.test.js`.
    IT DOES NOT RUN ANYTHING UNDER `tools/`.

So an internal `--selftest` runs when a human types it and never otherwise. That
is exactly the failure this platform already has a sentence for -- *"A tool that
exists is not a mechanism; a tool that RUNS is"* -- written about
`sairn_app_map_check.py`, which was built so a seventh correction could not happen
and then never invoked again until the seventh correction happened.

MEASURED 2026-09-16: FORTY-SIX tools carrying a `--selftest`, `--fixtures` or
`--self-check`. It was THIRTY-SIX the previous evening -- the set grows by
several a night across four clones, which is the whole argument for deriving the
list rather than writing it down. When this file landed, NONE of them was
discovered by the suite. Their criteria were locked
against fixtures, their refusals were driven in both directions, and none of it
would have been noticed going red.

**THAT NUMBER WAS WRONG THREE TIMES BEFORE IT WAS RIGHT, AND EACH WRONG VERSION
LOOKED EXACTLY AS CONFIDENT AS THIS ONE.** SEVEN, then TWENTY-THREE, then
TWENTY-FIVE. None of the three was a measurement of the tools; each was a
measurement of what the detector could see:

  * a regex over the source counted a GENERATOR's template as live code and
    missed three tools whose selftests it had no pattern for;
  * the AST that replaced it recognised `'--selftest' in argv` and could not see
    `argparse`, so ten more tools -- including `suite_control_coverage.py`, whose
    `--self-check` runs an end-to-end arm through `survey()` -- were reported as
    having nothing.

Both misses have the same shape and it is the shape worth carrying away: **a
detector that knows one spelling reports every other spelling as ABSENT, and
absent is indistinguishable from clean.** Neither was found by the tool going
red. Both were found by reading the tools it called empty and noticing one
plainly was not.

── WHY IT DERIVES THE LIST INSTEAD OF NAMING THE FILES ──────────────────────
A hardcoded list of thirty-six would be true today and quietly wrong at
thirty-seven. This parses `tools/*.py` for a tool that ACCEPTS a selftest flag and
runs each one it finds, so:

  * a NEW tool with a selftest is covered the moment it lands, with no edit here;
  * a tool that LOSES its selftest shows up as a shrinking count rather than as
    silence -- see the floor below, which is the same ratchet
    `run_all_tests.py` uses on its own file count and for the same reason.

── THE THIRD STATE IS REAL AND IS NOT A PASS ────────────────────────────────
A selftest that times out, cannot launch, or exits 2 is reported COULD-NOT-RUN,
separately from PASS and FAIL. Folding it into either would be the fail-open shape
PR 1.11 names: "could not run" is not "ran and was fine". Exit 1 covers a real
failure; a could-not-run is reported and also fails, because a selftest nobody can
execute verifies nothing.

── WHAT IT DOES NOT DO ─────────────────────────────────────────────────────
It does not judge whether a selftest is any GOOD -- a tool whose selftest asserts
nothing passes here. That is item 47's worksheet half and
`tools/sabotage_control_check.py`'s job. This answers the narrower question that
was silently false for all thirty-six: does the thing RUN.
"""
# REQUIREMENT: a tool carrying its own --selftest has that selftest RUN by the
#   suite, because run_all_tests.py discovers tests/** and api/*.test.js and
#   nothing under tools/, so an internal selftest otherwise runs only when a
#   human types it
#
import ast
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(REPO, 'tools')

# A floor, not an equality, for the same reason tools/run_all_tests.py gives: a
# rebase from another clone legitimately ADDS tools, and failing a session that
# added nothing is how a gate gets switched off out of annoyance. A DROP still
# fails immediately, which is the half worth protecting.
MIN_SELFTESTS = 46
PER_TOOL_TIMEOUT = 180

# Flags a tool may expose. Ordered by preference: a dedicated selftest first, then
# the blind-lock convention several checkers use instead, then the argparse
# spelling. `--self-check` was ADDED after the first real run reported 25 and the
# true figure was 35 -- see the note on argparse in selftest_flags().
FLAGS = ('--selftest', '--fixtures', '--self-check')


def _is_argv(node):
    """`argv`, `sys.argv`, `argv[1:]`, `sys.argv[1:]` -- the thing being tested."""
    if isinstance(node, ast.Attribute):
        return node.attr == 'argv'
    if isinstance(node, ast.Name):
        return node.id.endswith('argv')
    if isinstance(node, ast.Subscript):
        return _is_argv(node.value)
    return False


def _is_add_argument(node):
    """`p.add_argument(...)` / `parser.add_argument(...)` -- argparse declaring a flag."""
    return (isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'add_argument')


def selftest_flags(tree):
    """Every flag this MODULE's own code offers: tested against argv, or declared.

    ── TWO SHAPES, AND THE SECOND ONE WAS MISSED ON THE FIRST REAL RUN ──────
    This first looked only for `'--selftest' in argv`. It reported 25 tools. The
    true figure is 35: ten tools use `argparse` and never touch `sys.argv`
    themselves, so a rule written around the manual idiom could not see them --
    including `tools/suite_control_coverage.py`, whose `--self-check` has an
    end-to-end arm through `survey()` and had never been run by anything.

    That is the SAME defect this file was already written about, one shape
    further out: a detector that recognises one spelling of a thing reports the
    other spelling as absent, and absent is indistinguishable from clean. It was
    found the only way it could be -- by reading the tools the probe said had no
    selftest and noticing one plainly did.

    ── WHY AN AST AND NOT A REGEX, WHICH IS HOW THIS SHIPPED FIRST ───────────
    The first version matched the text `'--fixtures' in argv` with a regex over
    the source, after stripping comment lines. It reported `tools/new_checker.py`
    as carrying a selftest. It does not. new_checker.py is a GENERATOR: that line
    lives inside the template string it WRITES INTO the checker it scaffolds. The
    probe was reading the code a tool emits as if it were the code a tool runs,
    then executing `new_checker.py --fixtures`, getting a usage message, and
    reporting COULD-NOT-RUN against a tool that was never in scope.

    That is the same defect the docstring above warns about one step further in:
    not prose counted as logic, but TEMPLATE counted as logic. A regex cannot
    tell the difference, because at the character level there IS no difference --
    only the parse says whether those characters are an expression or the inside
    of a string. So the parse is what decides.

    A file that will not parse is returned as a parse failure, not as "no
    selftest". Absent and unreadable are different answers (PR 1.11).
    """
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            sides = [node.left] + list(node.comparators)
            if any(_is_argv(s) for s in sides):
                for s in sides:
                    if isinstance(s, ast.Constant) and isinstance(s.value, str):
                        found.add(s.value)
        elif _is_add_argument(node):
            # Only the positional option strings. A keyword like
            # dest='selftest' is not a flag a caller can type.
            for a in node.args:
                if (isinstance(a, ast.Constant) and isinstance(a.value, str)
                        and a.value.startswith('-')):
                    found.add(a.value)
    return found


def discover():
    """(name, flag) per tool, plus the tools whose source would not parse.

    Detected by looking for the flag being TESTED against argv in this module's
    own syntax tree, not merely appearing in its bytes -- a tool that documents
    `--selftest` in prose, or emits it inside a template, is not a tool that has
    one.
    """
    out, unparsed = [], []
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith('.py') or name.startswith('_'):
            continue
        p = os.path.join(TOOLS, name)
        try:
            src = io.open(p, encoding='utf-8', errors='replace').read()
        except OSError as e:                                    # noqa: BLE001
            unparsed.append((name, 'unreadable: %r' % e))
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            unparsed.append((name, 'does not parse: %s' % e))
            continue
        tested = selftest_flags(tree)
        for flag in FLAGS:
            if flag in tested:
                out.append((name, flag))
                break
    return out, unparsed


def run_one(name, flag):
    try:
        r = subprocess.run([sys.executable, os.path.join(TOOLS, name), flag],
                           capture_output=True, encoding='utf-8', errors='replace',
                           timeout=PER_TOOL_TIMEOUT, cwd=REPO)
    except subprocess.TimeoutExpired:
        return 'COULD-NOT-RUN', 'timed out after %ds' % PER_TOOL_TIMEOUT
    except Exception as e:                                  # noqa: BLE001
        return 'COULD-NOT-RUN', 'could not launch: %r' % e
    tail = ((r.stdout or '') + (r.stderr or '')).strip().split('\n')
    tail = tail[-1][:150] if tail else ''
    if r.returncode == 0:
        return 'PASS', tail
    if r.returncode == 2:
        # A tool's own could-not-tell. Not a failing selftest, and not a pass.
        return 'COULD-NOT-RUN', 'exit 2 (the tool could not tell): ' + tail
    return 'FAIL', 'exit %d: %s' % (r.returncode, tail)


# ── THE BLIND LOCK ───────────────────────────────────────────────────────────
# Both directions, because the defect this probe shipped with was a FALSE
# POSITIVE, not a miss: it is the must-NOT-match arms below that were failing
# silently, and a fixture set with only must-match arms would have passed while
# the tool was wrong. The template arm is `new_checker.py` reduced to its shape.
FIXTURES = (
    ('bare argv',        "if '--selftest' in argv: pass",                 True),
    ('sys.argv',         "if '--selftest' in sys.argv: pass",             True),
    ('sliced',           "if '--selftest' in sys.argv[1:]: pass",         True),
    ('equality',         "if argv[1] == '--selftest': pass",              True),
    ('reversed operands', "if '--selftest' == argv[1]: pass",             True),
    ('assigned',         "only = '--selftest' in argv",                   True),

    # argparse, which ten tools use and the first version could not see at all.
    ('argparse declared', "p.add_argument('--selftest', action='store_true')", True),
    ('argparse short+long', "p.add_argument('-s', '--selftest')",          True),
    # A dest= is not a flag anyone can type, so it must NOT be reported as one.
    ('argparse dest only', "p.add_argument('--other', dest='--selftest')", False),

    # The one that was wrong. A generator EMITS this text; it never runs it.
    ('inside a template', "TPL = '''\\nif '--selftest' in argv: pass\\n'''", False),
    ('prose in a docstring', '"""Run with --selftest to check."""',       False),
    # WAS `p.add_argument('--selftest')` until argparse became a recognised
    # shape, at which point this arm was asserting the OPPOSITE of the rule and
    # was the only thing that went red. A declared argparse flag IS a flag a
    # caller can type; "mentioned, never tested" has to be something else, so it
    # is now a bare string in a message.
    ('mentioned, never tested', "print('pass --selftest to check')",      False),
    ('a different flag',  "if '--verbose' in argv: pass",                 False),
    ('not argv at all',   "if '--selftest' in flags: pass",               False),
)


def run_fixtures():
    wrong = []
    for label, src, should_match in FIXTURES:
        try:
            got = '--selftest' in selftest_flags(ast.parse(src))
        except SyntaxError as e:
            wrong.append('%-24s fixture itself does not parse: %s' % (label, e))
            continue
        if got != should_match:
            wrong.append('%-24s expected %s, got %s' %
                         (label, 'MATCH' if should_match else 'no match',
                          'MATCH' if got else 'no match'))
    if wrong:
        print('REFUSING: the criteria do not classify their own fixtures.')
        for w in wrong:
            print('  ' + w)
        return 2
    print('  %d/%d fixtures correct (%d must match, %d must not).' % (
        len(FIXTURES), len(FIXTURES),
        sum(1 for f in FIXTURES if f[2]), sum(1 for f in FIXTURES if not f[2])))
    return 0


def main(argv):
    if '--fixtures' in argv:
        return run_fixtures()

    found, unparsed = discover()
    if '--list' in argv:
        for name, flag in found:
            print('%-40s %s' % (name, flag))
        for name, why in unparsed:
            print('%-40s !! %s' % (name, why))
        return 0

    print('TOOL SELFTESTS -- every tool that HAS one, RUN by the suite')
    print('  tools exposing a selftest : %d   (floor %d)' % (len(found), MIN_SELFTESTS))
    print('')
    fails, cnr = [], []
    for name, flag in found:
        verdict, detail = run_one(name, flag)
        mark = {'PASS': '  ok   ', 'FAIL': '  FAIL ', 'COULD-NOT-RUN': '  ???  '}[verdict]
        print('%s%-40s %s' % (mark, name + ' ' + flag, '' if verdict == 'PASS' else detail))
        if verdict == 'FAIL':
            fails.append(name)
        elif verdict == 'COULD-NOT-RUN':
            cnr.append((name, detail))

    print('')
    if unparsed:
        # Not "no selftest". The question was not answered for these files at all,
        # and a scan that silently drops what it cannot read reports a coverage
        # figure it did not earn.
        print('  COULD NOT BE SCANNED (%d) -- these were not searched for a '
              'selftest at all,' % len(unparsed))
        print('  which is not the same answer as not having one:')
        for name, why in unparsed:
            print('    %-38s %s' % (name, why))
    shrunk = len(found) < MIN_SELFTESTS
    if shrunk:
        print('  THE SET HAS SHRUNK: %d found, %d expected at minimum. A tool did '
              'not lose' % (len(found), MIN_SELFTESTS))
        print('  its selftest by accident -- find out which, and do not lower the '
              'floor to clear this.')
    if cnr:
        print('  COULD NOT RUN (%d) -- reported apart from both other answers, '
              'because' % len(cnr))
        print('  "could not run" is not "ran and was fine" (PR 1.11):')
        for name, why in cnr:
            print('    %-38s %s' % (name, why))
    if fails:
        print('  FAILING (%d): %s' % (len(fails), ', '.join(fails)))
    if not fails and not cnr and not shrunk and not unparsed:
        print('  every discovered selftest ran and passed.')
        print('')
        print('  THIS DOES NOT SAY THEY ARE GOOD SELFTESTS. A tool whose selftest')
        print('  asserts nothing passes here. That is item 47\'s worksheet half and')
        print('  sabotage_control_check.py\'s job; this answers only the narrower')
        print('  question that was silently false for all of them -- does it RUN.')
    return 1 if (fails or cnr or shrunk or unparsed) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
