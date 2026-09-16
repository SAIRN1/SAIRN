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

── EVIDENCE IS READ FROM A PARSE TREE, NOT FROM TEXT (rebuilt 2026-09-13) ───
This tool used to strip `#` comments and then run its patterns over whatever
was left. That left DOCSTRINGS, STRING LITERALS, PATH CONSTANTS, PRINT CALLS
and -- worst -- ITS OWN `CONTROLS_FOR` LINE standing, and it counted every one
of them as proof. Measured the day it was found:

    fail_open_check.py          BOTH EVIDENCED on SIX fires and TWO silents,
                                and NOT ONE was an assertion. The six were the
                                docstring's first line, the `Run:` line, the
                                TOOL path constant, a string literal, the
                                reporting loop's print('FAIL'), and
                                `CONTROLS_FOR = ['fail_open_check.py']`. The
                                checker's NAME contains "fail", so declaring it
                                created its own evidence.
    literal_drift_check.py      its entire SILENT half came from prose.
    traceability_matrix.py      fires=5, of which FOUR were prose or print and
                                one was real; silent=0, while the file asserts
                                exit 0 three separate times in a call shape no
                                pattern could read.

That is the defect this tool exists to catch, one level up: a checker producing
false reassurance about false reassurance. The fix is structural rather than
another pattern. Evidence now comes only from expressions that a parser says
are COMPARISONS OR ASSERTIONS:

  * Python -- `ast`. Comparisons, `assert` tests, and the repo's
    `check(label, actual, expected)` idiom rebuilt into a real comparison node.
    A docstring is an `Expr(Constant(str))` and is never any of those, so no
    amount of prose can contribute. Neither can a path constant, a list of
    strings, or a print call.
  * JavaScript -- comments stripped and STRING BODIES BLANKED
    (`jscomments.blank_string_bodies`), then only the argument lists of
    assertion calls are read. A test NAME and an assertion MESSAGE are string
    literals, so they are blanked before anything looks at them.

WHAT THIS STILL CANNOT TELL APART, stated rather than engineered away: a
comparison against an EXIT CODE and a comparison against a COUNT. Both are
real code. `check(rc == 1, ...)` and `check(total == 4, ...)` are the same
shape to a parser, and the second is not direction evidence at all. So the
verdict stays EVIDENCED rather than PROVEN, for the same reason it always did.

IT RUNS NOTHING. It parses.
"""
import ast
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import jscomments as _jscomments                              # noqa: E402

# ── THE PATTERNS, AND WHAT CHANGED UNDER THEM ────────────────────────────────
# These run over EXTRACTED ASSERTIONS now, never over raw source, so a word
# appearing in a docstring or a message cannot reach them. Two markers do the
# structural work and the rest are kept because a control may assert on the
# checker's OUTPUT TEXT rather than its exit code -- and after extraction, an
# output token can only appear inside a real comparison.
#
# CMP_ZERO / CMP_NONZERO are emitted by cmp_marker() below, not written by a
# human. They are how `check('label', rc, 0)` and `assert.strictEqual(r.code, 1)`
# become readable at all: the pattern list only ever knew the words
# `returncode`, `rc`, `status` and `exit`, so every control using a positional
# assert-equal idiom read as having NO evidence in that direction.
FIRES = [
    r'__CMP_NONZERO__',
    r'returncode\s*==\s*[1-9]', r'returncode\s*!=\s*0',
    r'\brc\s*==\s*[1-9]', r'\brc\s*!=\s*0',
    r'exit\s*(?:code)?\s*[=:]?\s*[1-9]\b',
    r'status\s*===?\s*[1-9]',
    r'FINDING', r'FAIL', r'must (?:be )?(?:deny|denied|block)', r'\bDENY\b',
]
# Evidence that a test expects the checker to stay SILENT on clean input.
SILENT = [
    r'__CMP_ZERO__',
    r'returncode\s*==\s*0', r'\brc\s*==\s*0', r'exit\s*(?:code)?\s*[=:]?\s*0\b',
    r'status\s*===?\s*0', r'\bCLEAN\b', r'0 finding', r'no finding',
    r'stays? (?:quiet|silent)', r'not (?:be )?(?:report|flagged)',
]
FIRES_RE = [re.compile(p, re.I) for p in FIRES]
SILENT_RE = [re.compile(p, re.I) for p in SILENT]

# Call names whose ARGUMENTS are an assertion, for the JavaScript side. Python
# does not need this list: `ast` reports comparisons directly, wherever they sit.
JS_ASSERT = re.compile(
    r'\b(?:assert(?:\.\w+)?|expect|check|should(?:\.\w+)?)\s*\(')

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
# ── A DECLARATION THAT DOES NOT PARSE IS A CONTROL THAT COUNTS FOR NOTHING ──
# This was `['\"]([\w.-]+\.py)['\"]`, which rejects a path separator and rejects
# `.js` outright. MEASURED 2026-09-16: NINE of seventy CONTROLS_FOR
# declarations under tests/ parsed to nothing.
#
#   FIVE wrote the path form -- CONTROLS_FOR = ['tools/subprocess_decode_check.py']
#     -- which reads perfectly to a human and matched nothing here.
#   FOUR are JavaScript controls naming JavaScript subjects. `.py` could never
#     match them, so a JS checker could not be declared as controlled AT ALL and
#     every one scored as though nobody had ever tried to break it.
#
# IT IS A FAIL-OPEN, WHICH IS WHY IT SURVIVED. The author writes the line, sees
# no error, and `tools/checker_confidence.py` goes on reporting "NO declared
# control: nothing has ever shown this checker can fire" about a checker whose
# control is sitting beside it. Found exactly that way: confidence rated
# subprocess_decode_check.py LOW on all three signals while its probe was
# driving it in both directions across eight arms. With the declaration read,
# the same tool rates it HIGH/HIGH/HIGH -- the control had always been there.
#
# Names normalise to a BASENAME because that is what every consumer compares
# against -- REGISTRY's `tool` field and the checker list are bare filenames --
# so `tools/x.py`, `./x.py` and `x.py` are one answer rather than three.
NAME_RE = re.compile(r"['\"]([\w./\\-]+\.(?:py|js))['\"]")


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
        for _name in NAME_RE.findall(m.group(1)):
            out.add(os.path.basename(_name.replace('\\', '/')))
    return out


def is_message(node):
    """A LABEL or MESSAGE argument, not a value under test.

    `check(rc == 1, 'a block that does not parse exits 1 (got %d)' % rc)` --
    the second argument is prose and must not be read. It is not a bare string
    Constant, so a naive test misses it; the `'...' % x`, f-string, `'a' + b`
    and `'sep'.join(...)` spellings are all how this repo writes a message.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return True
    if isinstance(node, ast.JoinedStr):                  # f'...'
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        return is_message(node.left)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return is_message(node.left) or is_message(node.right)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
            and node.func.attr in ('format', 'join'):
        return is_message(node.func.value)
    return False


_COLL = (ast.List, ast.Tuple, ast.Set, ast.Dict)


def _expected(node):
    """(kind, empty) for a literal a control compares an ACTUAL value against.

    Two literal shapes carry direction, and both say the same thing in
    different words -- nothing came back, or something did:

        check('...', len(clean), 0)                    a count
        check('...', kinds, ['BARE', 'UNREAD'])        a list of findings

    `True`/`False` are excluded deliberately -- `isinstance(True, int)` is True
    in Python, and `check('D2 and both tags are counted', ..., True)` is not a
    claim about anything being found.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, int) \
            and not isinstance(node.value, bool):
        return 'int', node.value == 0
    if isinstance(node, _COLL):
        items = node.keys if isinstance(node, ast.Dict) else node.elts
        return 'coll', not items
    return None, None


def cmp_marker(op, left, right):
    """__CMP_ZERO__ / __CMP_NONZERO__ for a comparison against a literal.

    THE ONE CONVENTION THIS RESTS ON, and it is written down in tool after tool
    in this repo: `Exit codes: 0 clean / 1 findings / 2 error`. So a control
    asserting `== 0` somewhere and `== 1` somewhere has driven both directions,
    whatever it happens to call its variables. An empty and a non-empty
    collection literal are the same statement made about a findings LIST rather
    than an exit code -- `tests/run_discarded_verdict_crossfile_probe.py`
    imports the checker and asserts on what `survey()` returns, never on a
    process exit, and read as ONE DIRECTION until this was added.
    """
    for side in (right, left):
        kind, empty = _expected(side)
        if kind is None:
            continue
        if isinstance(op, ast.Eq):
            return '__CMP_ZERO__' if empty else '__CMP_NONZERO__'
        if isinstance(op, ast.NotEq):
            return '__CMP_NONZERO__' if empty else None
        if isinstance(op, (ast.Gt, ast.GtE)) and kind == 'int' and empty:
            return '__CMP_NONZERO__'
    return None


def py_assertions(src):
    """Every comparison and assertion in a Python file, as (line, text).

    Three shapes, and nothing else is looked at:

      * an `ast.Compare` anywhere -- `rc == 1`, `'FAILED_BLOCKS:1' in out`
      * an `assert` statement's test
      * THE POSITIONAL ASSERT-EQUAL IDIOM this repo uses everywhere:
        `check('label', actual, expected)`. Rebuilt into a real comparison
        node, because otherwise a thorough control reads as having no evidence
        at all -- which is exactly what happened to
        tests/run_traceability_matrix_probe.py, whose three separate
        assertions of exit 0 were invisible.

    A docstring, a path constant, a `CONTROLS_FOR` list and a print call are
    none of these, structurally, and can never contribute.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None                     # caller reports it rather than guessing
    out = []

    def emit(node, text, marker=None):
        out.append((getattr(node, 'lineno', 0),
                    (text + (' ' + marker if marker else ''))[:200]))

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            marker = (cmp_marker(node.ops[0], node.left, node.comparators[0])
                      if len(node.ops) == 1 else None)
            emit(node, ast.unparse(node), marker)
        elif isinstance(node, ast.Assert):
            emit(node, ast.unparse(node.test))
        elif isinstance(node, ast.Call) and not node.keywords:
            # Exactly two values under test, alongside at least one message:
            # the assert-equal idiom. `os.path.join(REPO, 'tools', 'x.py')` has
            # two messages and ONE value, so it is not this and is skipped --
            # which is the line that used to supply half this tool's evidence.
            values = [a for a in node.args if not is_message(a)]
            if len(values) == 2 and len(values) < len(node.args):
                emit(node,
                     '%s == %s' % (ast.unparse(values[0]), ast.unparse(values[1])),
                     cmp_marker(ast.Eq(), values[0], values[1]))
    return out


def js_assertions(src):
    """Argument lists of assertion calls, from comment- and string-blanked JS.

    A test NAME and an assertion MESSAGE are string literals in JavaScript, so
    blanking the literal bodies removes the prose before anything reads it --
    `test('a verdict that IS read is not reported', ...)` is a label, and it
    was being counted as proof that a checker stays silent.

    WEAKER THAN THE PYTHON SIDE, AND SAID SO. This finds assertion calls by
    name over blanked source rather than from a parse tree; a JavaScript parser
    would need `node`, and this tool runs nothing. What it cannot see is an
    assertion made through a helper it does not recognise.
    """
    code = _jscomments.blank_string_bodies(_jscomments.strip_comments(src))
    out = []
    for m in JS_ASSERT.finditer(code):
        i = m.end() - 1                                  # at the '('
        depth, j, n = 0, i, len(code)
        while j < n:
            if code[j] == '(':
                depth += 1
            elif code[j] == ')':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        args_src = code[i + 1:j]
        line = code[:i].count('\n') + 1
        # Split on top-level commas only, so a nested call stays one argument.
        parts, depth, last = [], 0, 0
        for k, ch in enumerate(args_src):
            if ch in '([{':
                depth += 1
            elif ch in ')]}':
                depth -= 1
            elif ch == ',' and depth == 0:
                parts.append(args_src[last:k])
                last = k + 1
        parts.append(args_src[last:])
        parts = [p.strip() for p in parts]
        # A blanked string literal is now just its delimiters: that is a
        # message, and it is how the message is identified without a parser.
        values = [p for p in parts
                  if p and not re.fullmatch(r'''["'`]\s*["'`]''', p)]
        text = ', '.join(values)
        marker = None
        if len(values) == 2 and len(values) < len(parts):
            text = '%s == %s' % (values[0], values[1])
            marker = _js_marker(values[0], values[1])
        out.append((line, (text + (' ' + marker if marker else ''))[:200]))
    return out


def _js_marker(a, b):
    """Same 0-clean / non-zero-finding convention as cmp_marker, on JS text."""
    for side in (b, a):
        if re.fullmatch(r'-?\d+', side.strip()):
            return '__CMP_ZERO__' if int(side) == 0 else '__CMP_NONZERO__'
    return None


def evidence(path, src):
    """(fires, silent) ASSERTIONS in a declared control.

    File level is CORRECT here and was not before: the file has said, in its own
    source, which checkers it is a control for. What changed on 2026-09-13 is
    WHAT gets read -- assertions from a parse tree rather than lines of text.
    """
    items = py_assertions(src) if path.endswith('.py') else js_assertions(src)
    if items is None:
        return None, None
    fires, silent = [], []
    for line, text in items:
        if any(r.search(text) for r in FIRES_RE):
            fires.append((line, text.strip()[:90]))
        if any(r.search(text) for r in SILENT_RE):
            silent.append((line, text.strip()[:90]))
    return fires, silent


def main(argv):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:                                         # noqa: BLE001
        pass
    quiet = '--quiet' in argv
    checkers = promoted()
    tests = test_files()
    bodies, raws = {}, {}
    for t in tests:
        raw = io.open(t, encoding='utf-8', errors='replace').read()
        raws[t] = raw
        bodies[t] = strip(t, raw)

    # Declarations first, so attribution is a fact rather than a guess. This
    # half reads the comment-stripped TEXT, and correctly so: a declaration is
    # a statement about the file, not an assertion inside it.
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
    unparsed = []                       # a control this tool could not PARSE
    for c in checkers:
        ctrl = declares.get(c, [])
        fires = silent = 0
        broken = False
        for t in ctrl:
            f, s_ = evidence(t, raws[t])
            if f is None:
                # COULD NOT PARSE IS ITS OWN ANSWER. Reading zero assertions
                # out of a file that does not parse is indistinguishable from
                # reading zero out of one that has none, and the second is a
                # finding while the first is a broken control.
                broken = True
                unparsed.append((c, t))
                continue
            fires += len(f)
            silent += len(s_)
        if broken:
            verdict = 'CONTROL DOES NOT PARSE'
            rows.append({'checker': c, 'controls': len(ctrl),
                         'mentions': len(mentions.get(c, [])),
                         'fires': fires, 'silent': silent, 'verdict': verdict})
            continue
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
        for v in ('NO DECLARED CONTROL', 'CONTROL DOES NOT PARSE',
                  'DECLARED, NO ASSERTIONS',
                  'ONE DIRECTION', 'BOTH EVIDENCED', 'EXEMPT'):
            n = len([r for r in rows if r['verdict'] == v])
            print('  %-22s : %d' % (v, n))
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
        if unparsed:
            print('')
            print('  CONTROLS THIS TOOL COULD NOT PARSE -- nothing was read from')
            print('  them, which is NOT the same as reading no assertions:')
            for c, t in unparsed:
                print('    %-30s %s' % (c, os.path.relpath(t, REPO)
                                        .replace(os.sep, '/')))
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
        print('EVIDENCED, NOT PROVEN: direction is read from assertions -- PARSED ones as')
        print('of 2026-09-13, never prose. Only reading the fixture can tell a control that')
        print('plants a REAL defect from one that plants a shape the checker happens to')
        print('match, and nothing here separates a comparison against an EXIT CODE from one')
        print('against a COUNT. Both are code; only one is direction.')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
