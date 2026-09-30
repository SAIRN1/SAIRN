r"""AN ARM THAT ASSERTS ON A MESSAGE PASSES WHEN THE BEHAVIOUR IS GONE.

    python tools/message_assertion_audit.py
    python tools/message_assertion_audit.py --file tests/run_x_probe.py
    python tools/message_assertion_audit.py --json
    python tools/message_assertion_audit.py --selftest

REPORT ONLY. Exit 0 clean, 1 findings, 2 COULD NOT RUN. Writes nothing anywhere.

── WHY, AND IT IS THREE CRITERIA WRONG IN ONE SESSION ──────────────────────
On 2026-09-29 three checks of mine had criteria aimed at TEXT rather than at
behaviour, each caught before it was reported and none caught by review:

  * `tests/sairncare_transport_refusal.js` asserted WHICH FUNCTION a caller
    called and not WHAT IT READ off the result -- and passed against a synthetic
    caller reading the old shape.
  * `tools/hedge_carry_check.py` matched hedge WORDS with word boundaries only,
    so `appears` meaning *occurs* produced a false finding against a commit with
    nothing to answer for.
  * `tools/citation_no_source_report.py` decided "this row cites nothing" with
    `:\d{3,5}`, which cannot see a line number under 100.

Ted's was the same class. So this asks one question of every arm in `tests/`:

> does this arm assert on anything OTHER than a string?

An arm that does not is not thereby wrong -- some behaviour is only observable
as text, and a refusal MESSAGE a human reads is a real requirement. What is wrong
is a text-only arm that nobody has mutated in both directions, because it cannot
tell you whether the behaviour it names still exists.

── THE UNIT IS THE ASSERTION, NOT THE ARM, AND THAT IS A DELIBERATE CHOICE ──
Grouping assertions into "arms" needs a label, and the label conventions in this
repo are four different shapes (`ok(cond, 'label')`, `arm('label', cond)`,
`t('label', fn)`, `test('label', fn)`) plus bare `assert`. A parse that guessed
arm boundaries would mis-attribute, and a mis-attributed finding is worse than a
coarse one. So each ASSERTION is classified, and the FILE is the reported unit:
the number that matters is whether a file's assertions are ALL text.

── PYTHON IS PARSED, JAVASCRIPT IS PATTERN-MATCHED, AND THE TWO ARE REPORTED
   SEPARATELY BECAUSE THEY ARE NOT THE SAME EVIDENCE ──────────────────────
Python goes through `ast`, so "the first argument is a string-in-container
comparison" is a fact about the tree. JavaScript has no parser here, so its half
is regex and is labelled WEAKER in the output -- not folded in.
"""
import argparse
import ast
import io
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN  # noqa: E402

CRITERIA_VERSION = '2026-09-29.2'

TESTS = os.path.join(REPO, 'tests')

# The assertion-bearing call names this repo actually uses, plus `assert`.
ASSERT_CALLS = {'ok', 'arm', 'assert_', 'expect', 'check'}
# Attribute calls: assert.strictEqual, self.assertIn, assert.ok ...
# `search` and `match` are NOT in this set for Python. They are re methods, not
# assertion helpers, and including `search` made `assert re.search('lit', out)`
# count TWICE -- once as the Assert and once as the inner Call -- which is how a
# double-counted total silently inflates a denominator. Caught by the fixture arm.
ASSERT_ATTRS = {'ok', 'strictEqual', 'notStrictEqual', 'deepStrictEqual',
                'assertIn', 'assertEqual', 'assertTrue', 'assertRegex',
                'assertRaises', 'throws'}

# String-shaped predicates. A call to one of these WITH a constant string is a
# text assertion.
TEXT_METHODS = {'startswith', 'endswith', 'count', 'find', 'index',
                'search', 'match', 'fullmatch', 'findall'}


def _is_str(node):
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _mentions_str_const(node):
    """Does this expression contain a string constant anywhere?"""
    for n in ast.walk(node):
        if _is_str(n) and len(n.value) >= 3:
            return True
    return False


def classify_py_expr(node):
    """'TEXT' | 'VALUE' | 'UNKNOWN' for the thing an assertion asserts."""
    if node is None:
        return 'UNKNOWN'
    # THE CRITERION IS CONTAINMENT, NOT "a string is involved", AND THE FIRST
    # VERSION GOT THAT WRONG (corrected 2026-09-29, before anything was reported).
    # v1 called any equality against a string literal TEXT, and one corpus run
    # showed what that costs: nine mutation controls came back as message-only,
    # when what they assert is a WHOLE-FILE BYTE COMPARISON against a saved
    # baseline. And strictEqual(handle(null), 'REFUSED') is an assertion about a
    # RETURN VALUE that happens to be spelled with letters.
    #
    # The defect class is a check that some WORDS APPEAR IN captured output or in
    # a source file. So CONTAINMENT, REGEX and COUNT are TEXT; EQUALITY is VALUE.
    #
    # THE LIMIT, STATED: `assert out == 'the exact expected report'` is a message
    # assertion and this rule calls it VALUE. It is rare here -- reports in this
    # repo are long and nobody pins one whole -- and the alternative, guessing
    # which identifiers hold captured output, mis-sorts more than it fixes.
    if isinstance(node, ast.Compare):
        for op, comp in zip(node.ops, node.comparators):
            if isinstance(op, (ast.In, ast.NotIn)) and _is_str(node.left):
                return 'TEXT'
            if isinstance(op, (ast.Lt, ast.Gt, ast.LtE, ast.GtE, ast.Is,
                               ast.IsNot, ast.Eq, ast.NotEq)):
                return 'VALUE'
        return 'VALUE'
    # re.search('lit', x) / x.startswith('lit') / 'lit' in ...
    if isinstance(node, ast.Call):
        fn = node.func
        name = (fn.attr if isinstance(fn, ast.Attribute)
                else (fn.id if isinstance(fn, ast.Name) else ''))
        if name in TEXT_METHODS and any(_is_str(a) for a in node.args):
            return 'TEXT'
        if name in ('len', 'int', 'float', 'sum', 'sorted', 'isinstance',
                    'callable', 'bool'):
            return 'VALUE'
        return 'UNKNOWN'
    if isinstance(node, ast.BoolOp):
        kinds = [classify_py_expr(v) for v in node.values]
        if 'VALUE' in kinds:
            return 'VALUE'          # any non-text limb makes the arm behavioural
        if 'TEXT' in kinds:
            return 'TEXT'
        return 'UNKNOWN'
    if isinstance(node, ast.UnaryOp):
        return classify_py_expr(node.operand)
    if isinstance(node, ast.Subscript) or isinstance(node, ast.Attribute):
        return 'VALUE'
    if isinstance(node, ast.Name):
        return 'UNKNOWN'
    return 'UNKNOWN'


def scan_py(path):
    """[(lineno, kind, snippet)] for one Python test file, or None."""
    try:
        src = io.open(path, encoding='utf-8', errors='replace').read()
        tree = ast.parse(src)
    except Exception:
        return None
    lines = src.split(chr(10))
    out = []

    def snip(n):
        i = getattr(n, 'lineno', 1) - 1
        return ' '.join(lines[i].split())[:118] if 0 <= i < len(lines) else ''

    # THE TEST EXPRESSION OF AN `assert` IS NOT COUNTED AGAIN AS A CALL.
    # `assert ok(...)` and `assert re.search(...)` are ONE assertion, and walking
    # the tree naively counted the Assert and its inner Call separately.
    inner = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assert):
            for m in ast.walk(n.test):
                if isinstance(m, ast.Call):
                    inner.add(id(m))
    for n in ast.walk(tree):
        if isinstance(n, ast.Assert):
            out.append((n.lineno, classify_py_expr(n.test), snip(n)))
        elif isinstance(n, ast.Call) and id(n) not in inner:
            fn = n.func
            nm = (fn.attr if isinstance(fn, ast.Attribute)
                  else (fn.id if isinstance(fn, ast.Name) else ''))
            if nm in ASSERT_CALLS or nm in ASSERT_ATTRS:
                first = n.args[0] if n.args else None
                kind = classify_py_expr(first)
                # `arm(label, cond)` puts the label first
                if nm == 'arm' and len(n.args) > 1 and _is_str(first):
                    kind = classify_py_expr(n.args[1])
                out.append((n.lineno, kind, snip(n)))
    return out


# ── JAVASCRIPT: REGEX, AND LABELLED WEAKER IN THE OUTPUT ──────────────────
JS_TEXT = re.compile(
    r"""assert\.match\(|"""                      # assert.match(x, /re/)
    r"""\.includes\(\s*['"]|"""                  # src.includes('literal')
    r"""\.indexOf\(\s*['"]|"""                   # src.indexOf('literal')
    r"""\.split\(\s*['"][^'"]{3,}['"]\s*\)\.length|"""   # count-by-split
    r"""/[^/\n]{3,}/\s*\.test\(|"""              # /re/.test(x)
    r"""\.match\(\s*/""")                        # x.match(/re/)
# THE CATCH-ALL THAT USED TO END THIS ALTERNATION IS GONE, and it had to be. It
# was `assert\.(?:ok|strictEqual)\(...['"]<4+ chars>['"]` -- any assertion with a
# literal near it -- and the first corpus run showed the cost immediately: NINE
# mutation controls came back "every assertion is a string check", when what they
# assert is `strictEqual(fs.readFileSync(clean,'utf8'), ORIGINAL)`, a whole-file
# byte comparison against a saved baseline and the strongest behavioural check in
# this repository. Equality against a literal is an assertion about a VALUE. See
# classify_py_expr.
JS_VALUE = re.compile(
    r"""assert\.strictEqual\([^;\n]{0,60}(?:,\s*-?\d+|,\s*(?:true|false|null|undefined))|"""
    r"""assert\.deepStrictEqual\(|"""
    r"""\.length\s*(?:===|!==|>=|<=|>|<)\s*\d+|"""
    r"""assert\.ok\(\s*[A-Za-z_$][\w$.]*\s*(?:===|!==|>=|<=|>|<)""")
JS_ASSERT = re.compile(r"""\bassert(?:\.\w+)?\(""")


def scan_js(path):
    try:
        src = io.open(path, encoding='utf-8', errors='replace').read()
    except Exception:
        return None
    out = []
    for i, line in enumerate(src.split(chr(10)), 1):
        if not JS_ASSERT.search(line):
            continue
        if JS_VALUE.search(line):
            kind = 'VALUE'
        elif JS_TEXT.search(line):
            kind = 'TEXT'
        else:
            kind = 'UNKNOWN'
        out.append((i, kind, ' '.join(line.split())[:118]))
    return out


def audit(only=None):
    """[(rel, lang, total, text, value, unknown, [(line, snippet)])]"""
    rows = []
    if not os.path.isdir(TESTS):
        return None
    for root, dirs, files in os.walk(TESTS):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.pytest_cache')]
        for f in sorted(files):
            if not (f.endswith('.py') or f.endswith('.js')):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, REPO).replace(chr(92), '/')
            if only and rel != only.replace(chr(92), '/'):
                continue
            hits = scan_py(path) if f.endswith('.py') else scan_js(path)
            if hits is None:
                rows.append((rel, 'py' if f.endswith('.py') else 'js',
                             None, None, None, None, []))
                continue
            text = [(l, s) for l, k, s in hits if k == 'TEXT']
            value = [h for h in hits if h[1] == 'VALUE']
            unk = [h for h in hits if h[1] == 'UNKNOWN']
            rows.append((rel, 'py' if f.endswith('.py') else 'js', len(hits),
                         len(text), len(value), len(unk), text))
    return rows


def selftest():
    """Fixtures first, in both directions, before the corpus."""
    bad = 0

    def arm(name, cond, detail=''):
        nonlocal bad
        print('  %s %s' % ('ok  ' if cond else 'FAIL', name))
        if not cond:
            bad += 1
            if detail:
                print('       %s' % str(detail)[:300])

    import tempfile
    d = tempfile.mkdtemp(prefix='sairn_maa_')
    try:
        # TEXT-ONLY fixture
        p = os.path.join(d, 'f_text.py')
        io.open(p, 'w', encoding='utf-8', newline=chr(10)).write(chr(10).join([
            'out = run()',
            "assert 'NOT PROVISIONED' in out",
            "ok('could not tell' in out, 'it says so')",
            '']))
        hits = scan_py(p)
        kinds = [k for _l, k, _s in hits]
        arm('a string-in-output assertion is TEXT',
            kinds.count('TEXT') == 2 and 'VALUE' not in kinds, hits)

        # VALUE fixture
        p = os.path.join(d, 'f_value.py')
        io.open(p, 'w', encoding='utf-8', newline=chr(10)).write(chr(10).join([
            'assert rc == 2',
            'ok(len(rows) >= 3, "three rows")',
            'assert isinstance(v, dict)',
            '']))
        hits = scan_py(p)
        arm('KNOWN-BAD THE OTHER WAY: an exit code, a length and a type are '
            'VALUE, so this tool cannot report every arm as a message assertion',
            all(k == 'VALUE' for _l, k, _s in hits), hits)

        # MIXED: one limb is a value -> the arm is behavioural
        p = os.path.join(d, 'f_mixed.py')
        io.open(p, 'w', encoding='utf-8', newline=chr(10)).write(
            "ok(rc == 1 and 'DROPPED' in out, 'exit and wording')" + chr(10))
        hits = scan_py(p)
        arm('an arm with ONE non-text limb is VALUE -- a message check beside a '
            'behaviour check is not a message-only arm',
            [k for _l, k, _s in hits] == ['VALUE'], hits)

        # re.search with a literal is TEXT
        p = os.path.join(d, 'f_re.py')
        io.open(p, 'w', encoding='utf-8', newline=chr(10)).write(
            "assert re.search('NOT PROVISIONED', out)" + chr(10))
        arm('re.search with a string literal is TEXT',
            [k for _l, k, _s in scan_py(p)] == ['TEXT'], scan_py(p))

        # JS, both ways
        p = os.path.join(d, 'f.js')
        io.open(p, 'w', encoding='utf-8', newline=chr(10)).write(chr(10).join([
            "assert.match(r.error.message, /not available to your role/);",
            "assert.strictEqual(r.status, 403);",
            "assert.ok(src.includes('if(_crRecords===null)return null;'));",
            "assert.deepStrictEqual(r.problems, []);",
            '']))
        hits = scan_js(p)
        kinds = [k for _l, k, _s in hits]
        arm('JS: assert.match and .includes are TEXT; a numeric strictEqual and '
            'a deepStrictEqual are VALUE',
            kinds.count('TEXT') == 2 and kinds.count('VALUE') == 2, hits)

        # KNOWN-BAD THE OTHER WAY, and it is the correction this tool needed
        # before it reported anything.
        p = os.path.join(d, 'f_baseline.js')
        io.open(p, 'w', encoding='utf-8', newline=chr(10)).write(chr(10).join([
            "assert.strictEqual(fs.readFileSync(clean, 'utf8'), ORIGINAL,",
            "  'the mutation control did not restore the file');",
            "assert.strictEqual(handle(null), 'REFUSED', 'an unreadable body');",
            '']))
        arm('KNOWN-BAD THE OTHER WAY: a whole-file byte comparison against a '
            'saved baseline, and an equality against an enum-shaped return '
            'value, are NOT message assertions -- v1 reported NINE mutation '
            'controls as message-only because of exactly that',
            'TEXT' not in [k for _l, k, _s in scan_js(p)], scan_js(p))

        p = os.path.join(d, 'f_eq.py')
        io.open(p, 'w', encoding='utf-8', newline=chr(10)).write(
            "assert out == 'REFUSED'" + chr(10))
        arm('and the python side agrees: equality against a literal is VALUE',
            [k for _l, k, _s in scan_py(p)] == ['VALUE'], scan_py(p))

        # A FILE WITH NO ASSERTIONS AT ALL must not read as clean coverage
        p = os.path.join(d, 'f_empty.py')
        io.open(p, 'w', encoding='utf-8', newline=chr(10)).write('x = 1' + chr(10))
        arm('a file with NO assertions reports zero of everything rather than '
            'looking like a passing file', scan_py(p) == [], scan_py(p))

        # AN UNPARSEABLE FILE IS A COULD-NOT-TELL, NEVER A ZERO
        p = os.path.join(d, 'f_broken.py')
        io.open(p, 'w', encoding='utf-8', newline=chr(10)).write('def (' + chr(10))
        arm('an UNPARSEABLE file is None -- a could-not-tell -- and not an empty '
            'list, because zero text assertions out of a file nobody could read '
            'is the vacuous pass this repo names most often',
            scan_py(p) is None, scan_py(p))
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    print('  %s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
    return EXIT_CLEAN if not bad else EXIT_FINDING


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--file', default=None)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--show', type=int, default=12,
                    help='how many text-only files to name in full')
    args = ap.parse_args(argv)

    if args.selftest:
        print('MESSAGE ASSERTION AUDIT -- selftest, fixtures before the corpus')
        return selftest()

    print('MESSAGE ASSERTION AUDIT -- an arm that asserts on a message passes '
          'when the behaviour is gone')
    print('  criteria : %s' % CRITERIA_VERSION)
    print()
    print('  FIXTURE GATE -- run before the corpus so a vacuous pass is '
          'impossible:')
    if selftest() != EXIT_CLEAN:
        print()
        print('COULD NOT RUN: the fixture arms did not pass, so nothing below '
              'would mean anything.')
        return EXIT_COULD_NOT_RUN
    print()

    rows = audit(args.file)
    if rows is None:
        print('COULD NOT RUN: %s is not a directory, so no arm was examined. '
              'Zero message assertions out of zero files reads as clean.' % TESTS)
        return EXIT_COULD_NOT_RUN
    if not rows:
        print('COULD NOT RUN: no test file matched%s. An empty corpus is not a '
              'clean one.' % ('' if not args.file else ' --file %s' % args.file))
        return EXIT_COULD_NOT_RUN

    unreadable = [r for r in rows if r[2] is None]
    readable = [r for r in rows if r[2] is not None]
    total = sum(r[2] for r in readable)
    text = sum(r[3] for r in readable)
    value = sum(r[4] for r in readable)
    unk = sum(r[5] for r in readable)
    py = [r for r in readable if r[1] == 'py']
    js = [r for r in readable if r[1] == 'js']

    print('  test files read      : %d  (%d python, %d javascript)'
          % (len(readable), len(py), len(js)))
    print('  UNPARSEABLE          : %d -- counted, never folded into clean'
          % len(unreadable))
    for r in unreadable:
        print('      ? %s' % r[0])
    print('  assertions classified: %d' % total)
    print('      on a STRING only  : %d' % text)
    print('      on a VALUE        : %d' % value)
    print('      COULD NOT CLASSIFY: %d -- a third state, not a pass' % unk)
    print()
    print('  THE JAVASCRIPT HALF IS WEAKER AND IS NOT FOLDED IN. Python goes')
    print('  through `ast`, so the classification is a fact about the tree.')
    print('  JavaScript is regex, so its numbers are an estimate:')
    print('      python assertions : %d, of which %d string-only'
          % (sum(r[2] for r in py), sum(r[3] for r in py)))
    print('      js assertions     : %d, of which %d string-only  (ESTIMATE)'
          % (sum(r[2] for r in js), sum(r[3] for r in js)))
    print()

    # ── THE FINDING UNIT, AND THE FIRST TWO CHOICES WERE BOTH WRONG.
    # v1 asked for a file whose EVERY assertion is text. Over the real corpus that
    # returns ZERO -- every file has at least one value or unclassified assertion --
    # so a tool sitting on 1,464 string assertions reported no findings. A criterion
    # that cannot fire on its own corpus has not been validated, it has been
    # flattered.
    #
    # The unit is now the file's RATIO over its CLASSIFIED assertions: a file where
    # string checks are at least half of (TEXT + VALUE) is one whose evidence is
    # mostly words. UNKNOWN is excluded from the denominator on purpose -- it is a
    # could-not-tell and folding it either way would decide the ratio by how much
    # this tool failed to parse.
    #
    # THE NUMBER IS A POPULATION TO MUTATE, NOT A DEFECT COUNT. Said again in the
    # closing text, because "N findings" reads as N bugs.
    scored = [r for r in readable if (r[3] + r[4]) > 0]
    all_text = [r for r in scored if r[3] > 0 and r[3] >= r[4]]
    print('FILES WHERE STRING CHECKS ARE AT LEAST HALF THE CLASSIFIED '
          'ASSERTIONS: %d of %d scoreable' % (len(all_text), len(scored)))
    print('  These are the ones whose evidence is mostly words. NOT thereby wrong')
    print('  -- some behaviour is only observable as text, and a refusal message a')
    print('  human reads is a real requirement. What is missing is a both-ways')
    print('  mutation, and this is the population to run it on.')
    print()
    for rel, lang, tot, txt, _v, _u, hits in sorted(
            all_text, key=lambda r: (-(r[3]), r[0]))[:args.show]:
        print('  ! %-52s %d text / %d value / %d unclassified [%s]'
              % (rel, txt, _v, _u, lang))
        for line, snippet in hits[:3]:
            print('        :%-5d %s' % (line, snippet))
        if len(hits) > 3:
            print('        ... and %d more' % (len(hits) - 3))
    if len(all_text) > args.show:
        print('  ... and %d more file(s); pass --show to see them'
              % (len(all_text) - args.show))
    print()
    print('  WHAT THIS DOES NOT DO, so nothing reads it as more than it is:')
    print('  * it does not mutate anything. Whether an arm SURVIVES having its')
    print('    behaviour removed is a question only a mutation answers, and this')
    print('    tool names the population to mutate rather than doing it.')
    print('  * a text-only file is not a defect. A file with 40 value assertions')
    print('    and one fragile message check is invisible here, by design: the')
    print('    unit is the file, because guessing arm boundaries across four')
    print('    label conventions would mis-attribute findings.')
    print('  * UNKNOWN is a real bucket. An assertion on a bare name, or on a')
    print('    helper call this tool cannot follow, is not counted as either.')

    if args.json:
        print(json.dumps({
            'criteria': CRITERIA_VERSION,
            'files': len(readable), 'unparseable': [r[0] for r in unreadable],
            'assertions': total, 'text': text, 'value': value, 'unknown': unk,
            'all_text_files': [{'file': r[0], 'lang': r[1], 'assertions': r[2],
                                'lines': [h[0] for h in r[6]]}
                               for r in all_text],
        }, indent=2))

    return EXIT_FINDING if all_text or unreadable else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
