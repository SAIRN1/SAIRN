"""Which test suites has anybody ever tried to BREAK?

    python tools/suite_control_coverage.py
    python tools/suite_control_coverage.py --json
    python tools/suite_control_coverage.py --self-check

Exit 0 when every suite has a negative control, 1 when one does not, 2 when the
question could not be answered. REPORT ONLY -- nothing gates on this.

── THE ROOT CAUSE THIS CLOSES, NAMED RATHER THAN IMPLIED ───────────────────
Defect cluster `5b98fd27` carried two test-layer defects and they are ONE root
cause: an assertion that does not depend on what the mutation changed. Three
source assertions in tests/dnt_vendor_write_confirmation.js matched text that
came AFTER the guard rather than the guard's own position, so injecting
`if(false && dntIsUnconfirmed(...))` left every one of them green.

That was caught, and it was caught by the one mechanism that can catch it: a
mutation probe reintroduced the defect and asserted the suite went RED. The
machinery works. THE GAP IS THAT ALMOST NOTHING IS POINTED AT IT.

`tests/dnt_vendor_write_confirmation_probe.py` says it in its own first line --
"a suite that has only ever been green is a suite whose behaviour nobody knows"
-- and that sentence has never been measured across the tree. This measures it.

── WHY THE TWO EXISTING TOOLS CANNOT ANSWER THIS ───────────────────────────
Both name this gap in their own docstrings and neither closes it:

  tools/sabotage_control_check.py  asks whether a control VERIFIES ITS SABOTAGE
                                   APPLIED. It cannot see "a control whose
                                   assertion is simply wrong about what the
                                   checker should do", and it only looks at
                                   probes that already sabotage something.
  tools/mutation_anchor_check.py   asks whether an anchor matches EXACTLY ONCE.
                                   It cannot see "an anchor pointing at the
                                   WRONG branch while matching exactly once".

Applied, unique, EFFECTIVE. The first two are checked. This is the third, and
the only form it can take at this level is coverage: a suite with no control at
all has no measured assertion power, and no amount of green says otherwise.

── WHAT IT COUNTS AS A CONTROL, AND THE DIRECTION IT ERRS IN ───────────────
A suite is CONTROLLED when some `tests/*.py` file defining a `MUTATIONS` list
names it in a string literal outside a docstring. Docstring text is excluded
deliberately: a probe that merely MENTIONS a suite in prose would otherwise be
counted as controlling it, and OVER-claiming coverage is the one direction this
tool must never fail in -- it would report a suite as tested-for-power when
nobody has ever tried to break it.

Under-claiming is possible and is the safe direction: a probe that builds its
suite path from pieces is not recognised, and the suite reads as uncontrolled.
That cries wolf, which is visible; the other way round is silent.

── WHAT IT DOES NOT CLAIM ──────────────────────────────────────────────────
  * That a controlled suite is a GOOD suite. One arm is a control; it is not
    coverage of the suite's assertions, and this tool counts files, not arms.
  * That every suite NEEDS one. A pure-function unit test over a table of
    inputs has little to sabotage. The list is a starting point for that
    judgement, not the judgement.
  * Anything about python or shell tests. JavaScript suites only, because that
    is where the cluster's defect lived and where the SUITE convention exists.

THE UNIVERSE IS `tests/*.js` AND `api/*.test.js`, and the second half was added
the moment the first run under-reported: two of the five controlled suites live
in `api/` and a `tests/`-only sweep counted neither, so the tool would have said
five were controlled while naming three. Widening it also brings in 42 api
suites that are NOT controlled, which moves the headline the wrong way -- and
that is the direction a coverage number has to be allowed to move.

── AND THE PROBE UNIVERSE WAS WRONG IN BOTH DIRECTIONS AT ONCE (2026-09-15) ──
The probe universe was `tests/*.py`. **Not every control on this platform is
written in Python**, and `docs/MASTER-PLAN.md` already says so in the fault
census: a probe counts if it declares a parseable `MUTATIONS` block, is named
`*_fault_probe.py`, **is named `*_mutation_control.js`**, or lives under
`tests/faults/`. This tool knew only the first spelling, so:

  * `tests/sairncode_gates_mutation_control.js` and
    `tests/sairnbiz_void_mutation_control.js` -- both real, both declaring
    `const MUTATIONS = [`, the first asserting its sabotage applied in four
    parts -- were INVISIBLE as controls, and the suites they control were
    reported uncontrolled;
  * worse, being `tests/*.js` they were counted in the SUITE denominator, so
    each control made the headline look one suite worse instead of one better.

Found on 2026-09-15 by `tools/suite_control_triage.py`, which ranked
`sairncode_gates_mutation_control.js` as a Tier A suite needing a control -- a
control needing a control, which is the shape that made it obvious. **A census
whose universe is one spelling of a thing reports every other spelling as
absent**, and the miss was in the OVER-claiming direction this file's own
docstring says it must never fail in: it claimed suites were uncontrolled when
they were not.
"""
import argparse
import ast
import glob
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN                       # noqa: E402


def probe_literals(src, path='<probe>'):
    """(defines MUTATIONS, {string literals outside docstring position}).

    PARSED, NEVER IMPORTED. Most probes in tests/ have no `__main__` guard, so
    importing one RUNS it: it mutates a live source file, shells out to node,
    and restores it at the end. tools/mutation_anchor_check.py learned that the
    expensive way -- its first version was killed mid-probe and left a source
    file modified on disk. A read-only checker must not be able to change the
    thing it inspects.
    """
    tree = ast.parse(src, path)
    doc_nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = getattr(node, 'body', None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                doc_nodes.add(id(body[0].value))
    has_mutations = any(
        isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'MUTATIONS' for t in n.targets)
        for n in ast.walk(tree))
    lits = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in doc_nodes):
            lits.add(node.value)
    return has_mutations, lits


_JS_STRING = re.compile(r"""'([^'\\\n]*(?:\\.[^'\\\n]*)*)'|"([^"\\\n]*(?:\\.[^"\\\n]*)*)"|`([^`\\]*(?:\\.[^`\\]*)*)`""")
_JS_MUTATIONS = re.compile(r'\bMUTATIONS\s*=')


def js_probe_literals(src, path='<probe>'):
    """(declares MUTATIONS, {string literals}) for a JavaScript control.

    The Python half of this question is answered by `ast`, which is exact. There
    is no stdlib JS parser, so this is a lexer-grade approximation and it is
    deliberately the WEAKER of the two:

      * comments are stripped through `checker_kit.strip_comments`, the
        canonical implementation, so the `// THE NEGATIVE CONTROL FOR
        tests/foo.js` header line in every one of these files cannot be mistaken
        for a live reference -- that is the JS equivalent of the docstring
        exclusion and it is the same over-claiming risk;
      * a template literal with `${...}` interpolation is captured whole, so a
        path built from pieces is not recognised. That under-claims, which is
        this tool's declared safe direction.

    It is not a parser and does not pretend to be. What it buys is that the two
    real `*_mutation_control.js` files stop being invisible, which is a larger
    error than anything this approximation can introduce.
    """
    from checker_kit import strip_comments
    code = strip_comments(src)
    lits = set()
    for m in _JS_STRING.finditer(code):
        for g in m.groups():
            if g is not None:
                lits.add(g)
    return bool(_JS_MUTATIONS.search(code)), lits


def _default_probes():
    """Python probes, plus the JS spellings MASTER-PLAN already counts as probes."""
    return (sorted(glob.glob(os.path.join(REPO, 'tests', '*.py')))
            + sorted(glob.glob(os.path.join(REPO, 'tests', '*_mutation_control.js')))
            + sorted(glob.glob(os.path.join(REPO, 'tests', 'faults', '*.js'))))


def survey(suite_paths=None, probe_paths=None):
    """{suite basename: [probe basenames]} plus the probes that were parsed."""
    # BOTH DIRECTORIES. A tests/-only universe silently excluded api/, where
    # two of the controlled suites actually live -- an under-count that reads
    # as "nobody controls api" when in fact nobody LOOKED at api.
    probes = probe_paths if probe_paths is not None else _default_probes()
    # A JS CONTROL IS NOT ALSO A SUITE NEEDING ONE. Before this, every
    # `*_mutation_control.js` was counted in the denominator, so writing a
    # control moved the headline DOWN. Derived from the probe list rather than
    # re-globbed, so the two can never disagree about which files are probes.
    _probe_names = set(os.path.basename(p) for p in probes)
    suites = (suite_paths if suite_paths is not None
              else [s for s in (sorted(glob.glob(os.path.join(REPO, 'tests', '*.js')))
                                + sorted(glob.glob(os.path.join(REPO, 'api', '*.test.js'))))
                    if os.path.basename(s) not in _probe_names])
    # Basenames must stay unique across the two directories, or a control on
    # one would be credited to the other. Asserted rather than assumed.
    _seen = {}
    for _s in suites:
        _b = os.path.basename(_s)
        if _b in _seen and _seen[_b] != _s:
            raise ValueError('two suites share the basename %r (%s, %s) -- '
                             'control attribution would be ambiguous'
                             % (_b, _seen[_b], _s))
        _seen[_b] = _s
    controllers, unreadable = {}, []
    for p in probes:
        try:
            src = io.open(p, encoding='utf-8', errors='replace').read()
            reader = js_probe_literals if p.endswith('.js') else probe_literals
            has_mut, lits = reader(src, p)
        except Exception as e:                                   # noqa: BLE001
            unreadable.append((os.path.basename(p), '%s: %s' % (type(e).__name__, e)))
            continue
        if not has_mut:
            continue
        for s in suites:
            b = os.path.basename(s)
            if any(l == b or l.endswith('/' + b) or l.endswith(os.sep + b)
                   for l in lits):
                controllers.setdefault(b, []).append(os.path.basename(p))
    return ([os.path.basename(s) for s in suites], controllers, unreadable)


def _fixtures():
    """Both directions, and the docstring exclusion in both directions too."""
    return {
        # Controlled: defines MUTATIONS and names the suite in a real literal.
        'controlled': ('MUTATIONS = [("a", "x", "y")]\n'
                       'SUITE = "tests/target_suite.js"\n'),
        # Names the suite but has NO MUTATIONS -- not a control.
        'no_mutations': ('SUITE = "tests/target_suite.js"\n'
                         'print("runs the suite, never breaks it")\n'),
        # Has MUTATIONS but only MENTIONS the suite in its docstring. This is
        # the over-claim this tool must not make.
        #
        # THE DOCSTRING ENDS EXACTLY WITH THE SUITE PATH, on purpose. The first
        # version of this fixture read "... target_suite.js, eventually." and
        # therefore could not fail: endswith() would miss it whether the
        # docstring exclusion worked or not. A mutant that counted docstrings
        # survived both this self-check and the probe. A fixture that cannot
        # fail is not a fixture.
        'docstring_only': ('"""Controls for tests/target_suite.js"""\n'
                           'MUTATIONS = [("a", "x", "y")]\n'
                           'SUITE = "tests/other_suite.js"\n'),
        # Names it in a subprocess arg rather than a SUITE constant.
        'inline_literal': ('MUTATIONS = [("a", "x", "y")]\n'
                           'run(["node", "tests/target_suite.js"])\n'),
    }


def self_check():
    f = _fixtures()
    fails = []

    def ck(name, cond, detail=''):
        print(('  ok   ' if cond else '  FAIL ') + name
              + ('' if cond else '\n         ' + str(detail)[:300]))
        if not cond:
            fails.append(name)

    def controls(key):
        has_mut, lits = probe_literals(f[key])
        return has_mut and any(l.endswith('target_suite.js') for l in lits)

    ck('a probe with MUTATIONS naming the suite COUNTS as a control',
       controls('controlled'), f['controlled'])
    ck('a probe with NO MUTATIONS does not count, however it names the suite',
       not controls('no_mutations'), f['no_mutations'])
    ck('a suite named only in a DOCSTRING does not count -- over-claiming '
       'coverage is the one direction this must never fail in',
       not controls('docstring_only'), f['docstring_only'])
    ck('...and that probe is still recognised as HAVING mutations, so the '
       'exclusion is the docstring and not the whole file',
       probe_literals(f['docstring_only'])[0] is True)
    ck('...and the suite it really controls IS seen',
       any(l.endswith('other_suite.js')
           for l in probe_literals(f['docstring_only'])[1]))
    ck('a suite named in a subprocess argument counts, not only a SUITE constant',
       controls('inline_literal'), f['inline_literal'])

    # ── THE JAVASCRIPT READER, both directions. Added 2026-09-15 with the probe
    # universe. The comment arm is the JS equivalent of the docstring exclusion
    # and is the over-claiming direction: EVERY real *_mutation_control.js opens
    # with `// THE NEGATIVE CONTROL FOR tests/<suite>.js`, so a reader that did
    # not strip comments would credit a control to a suite on the strength of a
    # header line -- and would do it for the right suite, which is what makes it
    # undetectable by eye.
    def js_controls(src):
        has_mut, lits = js_probe_literals(src)
        return has_mut and any(l.endswith('target_suite.js') for l in lits)

    ck('JS: MUTATIONS plus the suite in a real literal COUNTS',
       js_controls("const MUTATIONS = [{a:1}];\n"
                   "const SUITE = 'tests/target_suite.js';\n"))
    ck('JS: no MUTATIONS does not count, however it names the suite',
       not js_controls("const SUITE = 'tests/target_suite.js';\n"
                       "run(SUITE);\n"))
    ck('JS: a suite named only in a COMMENT does not count -- the over-claiming '
       'direction, and the shape every real control actually has',
       not js_controls("// THE NEGATIVE CONTROL FOR tests/target_suite.js\n"
                       "const MUTATIONS = [{a:1}];\n"
                       "const SUITE = 'tests/other_suite.js';\n"))
    ck('JS: ...and that probe is still recognised as HAVING mutations, so the '
       'exclusion is the comment and not the whole file',
       js_probe_literals("// controls tests/target_suite.js\n"
                         "const MUTATIONS = [{a:1}];\n")[0] is True)
    ck('JS: a double-quoted literal is read too, not only single',
       js_controls('const MUTATIONS = [];\nrun("tests/target_suite.js");\n'))
    ck('JS: a block comment naming the suite does not count either',
       not js_controls("/* tests/target_suite.js */\nconst MUTATIONS = [];\n"))

    # AND THE REAL FILES, because a correct reader pointed at the wrong universe
    # reports the same numbers as no reader at all -- which is exactly what was
    # wrong before today.
    for real_ctl, real_suite in (
            ('sairncode_gates_mutation_control.js', 'sairncode_gates.js'),
            ('sairnbiz_void_mutation_control.js', 'sairnbiz_void_not_delete.js')):
        rp = os.path.join(REPO, 'tests', real_ctl)
        if not os.path.isfile(rp):
            ck('the real control %s is present' % real_ctl, False, rp)
            continue
        hm, ls = js_probe_literals(io.open(rp, encoding='utf-8',
                                           errors='replace').read(), rp)
        ck('%s declares MUTATIONS and is seen as a probe' % real_ctl, hm)
        ck('...and it names %s outside a comment' % real_suite,
           any(l.endswith(real_suite) for l in ls),
           sorted(l for l in ls if l.endswith('.js'))[:8])

    ck('a *_mutation_control.js is NOT also counted as a suite needing a control',
       not any(n.endswith('_mutation_control.js') for n in survey()[0]),
       [n for n in survey()[0] if n.endswith('_mutation_control.js')])

    # END TO END through survey(), because the arms above test the parser and a
    # correct parser wired up wrongly reports the same numbers as a broken one.
    import tempfile
    tmp = tempfile.mkdtemp(prefix='suite_cov_')
    io.open(os.path.join(tmp, 'target_suite.js'), 'w', encoding='utf-8').write('//\n')
    io.open(os.path.join(tmp, 'lonely_suite.js'), 'w', encoding='utf-8').write('//\n')
    io.open(os.path.join(tmp, 'p_probe.py'), 'w', encoding='utf-8').write(f['controlled'])
    names, ctl, bad = survey(
        sorted(glob.glob(os.path.join(tmp, '*.js'))),
        sorted(glob.glob(os.path.join(tmp, '*.py'))))
    ck('end to end: the controlled suite is reported controlled',
       ctl.get('target_suite.js') == ['p_probe.py'], ctl)
    ck('end to end: the uncontrolled suite is reported uncontrolled',
       'lonely_suite.js' in names and 'lonely_suite.js' not in ctl, (names, ctl))

    # A PROBE THAT WILL NOT PARSE IS A THIRD STATE. Folding it into "no control"
    # would report a suite as uncovered on the strength of a syntax error.
    io.open(os.path.join(tmp, 'broken_probe.py'), 'w', encoding='utf-8').write('def (\n')
    _n2, _c2, bad2 = survey(sorted(glob.glob(os.path.join(tmp, '*.js'))),
                            sorted(glob.glob(os.path.join(tmp, '*.py'))))
    # THE DUPLICATE-BASENAME GUARD, exercised. It cannot fire on today's tree,
    # so without this arm it is a branch nobody has ever run -- and a guard that
    # has never run is a guard nobody knows works. Control attribution is keyed
    # on the basename, so two suites sharing one would credit a control to the
    # wrong suite, silently.
    dup = None
    try:
        survey([os.path.join(REPO, 'tests', 'same.js'),
                os.path.join(REPO, 'api', 'same.js')], [])
    except ValueError as e:
        dup = str(e)
    ck('two suites sharing a basename REFUSE rather than mis-attributing a '
       'control', dup is not None and 'same.js' in dup, dup)

    ck('a probe that will not parse is reported as UNREADABLE, not silently '
       'treated as absent',
       any(b[0] == 'broken_probe.py' for b in bad2), bad2)
    ck('...and it does not take the readable probes down with it',
       _c2.get('target_suite.js') == ['p_probe.py'], _c2)

    print('\n%d failure(s)' % len(fails))
    return 1 if fails else 0


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--self-check', action='store_true', dest='selfcheck')
    args = ap.parse_args(argv)

    if args.selfcheck:
        return self_check()

    try:
        names, ctl, unreadable = survey()
    except Exception as e:                                       # noqa: BLE001
        print('COULD NOT RUN: %s: %s' % (type(e).__name__, e))
        return EXIT_COULD_NOT_RUN

    uncontrolled = [n for n in names if n not in ctl]

    if args.json:
        print(json.dumps({'suites': len(names), 'controlled': sorted(ctl),
                          'uncontrolled': uncontrolled,
                          'unreadable_probes': unreadable}, indent=1))
        return 1 if uncontrolled else 0

    if not args.quiet:
        print('SUITE CONTROL COVERAGE -- report only, nothing gates on this')
        print('  %d suite(s) -- tests/*.js and api/*.test.js' % len(names))
        print('  %d have a negative control (a probe that BREAKS the source and '
              'asserts' % len(ctl))
        print('  the suite goes red); %d have never been sabotaged at all.'
              % len(uncontrolled))
        print('')
        for s in sorted(ctl):
            print('  CONTROLLED    %-46s %s' % (s, ', '.join(ctl[s])))
        if unreadable:
            print('')
            print('  COULD NOT READ -- these probes did not parse, so whatever')
            print('  they control is NOT counted either way:')
            for p, why in unreadable:
                print('    %-40s %s' % (p, why))
        print('')
        print('  A SUITE THAT HAS ONLY EVER BEEN GREEN IS A SUITE WHOSE')
        print('  BEHAVIOUR NOBODY KNOWS. That sentence is the first line of')
        print('  tests/dnt_vendor_write_confirmation_probe.py and it had never')
        print('  been measured across the tree until now.')
        print('')
        print('  THIS IS NOT A LIST OF BAD SUITES. A pure-function unit test')
        print('  over a table of inputs has little to sabotage, and one control')
        print('  arm is not coverage of a suite\'s assertions. It says where')
        print('  assertion power is UNMEASURED, which is a different claim.')
        print('')
        print('  uncontrolled (%d):' % len(uncontrolled))
        for s in uncontrolled:
            print('    %s' % s)

    return 1 if uncontrolled else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
