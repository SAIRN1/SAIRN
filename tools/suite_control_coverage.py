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


# ── A CONTROL DOES NOT HAVE TO LIVE IN ITS OWN FILE (2026-09-17) ───────────
# The hover auditor found this counter blind to a whole SHAPE of control: a
# suite that carries its own mutation probes INLINE. Two confirmed --
# tests/sairnbiz_server_backup.js (a `probes` table of [name, mutate, check]
# triples, each asserting the arm goes red) and tests/quote_history_
# duplication.js -- and both are strong. So the 48-of-163 headline was an
# UNDERCOUNT, and every suite it named was named wrongly.
#
# THE DETECTOR WAS EXTENDED RATHER THAN THE SUITES REWRITTEN, and the choice is
# not a preference. An inline control is not the weaker form: it sits beside the
# assertion it protects and cannot drift away from the harness it needs, which
# is the failure mode a separate file actually has. Standardising seven working
# suites onto a file-naming convention so that a COUNTER can see them is the
# tool dictating the code -- the same inversion this platform has now recorded
# twice, in sabotage_control_check scoring the stronger guard worse and in
# csv_formula_injection_check reporting the fix as the only defect. The tally is
# what has to be true. The counter was what was wrong.
#
# ── AND THERE IS A THIRD STATE, WHICH IS THE POINT ────────────────────────
# `str.replace` on an anchor that no longer matches does NOTHING, silently, and
# the control then runs the suite against an UNMODIFIED file and passes. That is
# sabotage_control_check.py's entire subject. So an inline control counts only
# when it VERIFIES THE MUTATION APPLIED -- sairnbiz asserts
# `probeSrc !== SYNC_SRC` and quote_history asserts
# `notStrictEqual(out, src, 'save() was not found -- this mutation asserts
# nothing')`. One that mutates without checking is reported SEPARATELY and is
# NOT counted as covered: it is not a control, it is a control-shaped thing.
# THE WINDOW CROSSES LINES ON PURPOSE. The first version kept the keyword and
# the `.replace(` on ONE line, and both of the real instances this was written
# for failed their own fixtures: sairnbiz announces `// MUTATION PROBES.` and
# mutates three lines later, quote_history writes `section('MUTATION: ...')`
# and mutates on the next line. A criterion that cannot match the two cases it
# was built from is not a strict criterion, it is a broken one -- caught by the
# lock before the real tree was read, which is the entire point of locking
# first.
#
# AND THE WINDOW ALONE WAS TOO LOOSE, caught by spot-checking the output rather
# than by the lock -- which is worth recording, because it means the lock did
# not cover it. `tests/sairnvet_controlled_export.js` says "mutation" somewhere
# and then normalises line endings with `.replace(/\r\n/g, '\n')` 800 characters
# later, and was named as a control-shaped thing on that basis. A FORMATTING
# replace is not a mutation. So two more conditions:
#
#   * the receiver must LOOK LIKE LIFTED SOURCE (src / source / html / code /
#     probeSrc), or the replace must sit inside a mutate-table -- an arrow
#     function in a `probes`/`MUTATIONS` array, which is sairnbiz's shape and
#     whose receiver is a one-letter parameter;
#   * a pure line-ending or whitespace normalisation does not count at all.
_INLINE_KEYWORD = re.compile(r'mutation|sabotage|negative control', re.I)
_INLINE_ON_SOURCE = re.compile(
    r'\b\w*(?:src|source|html|code)\w*\s*\.\s*replace\s*\(', re.I)
_INLINE_MUTATE_TABLE = re.compile(
    r'(?:probes|MUTATIONS)\s*=\s*\[[\s\S]{0,4000}?=>\s*\w+\.replace\s*\(', re.I)
# `.replace(/\r\n/g, ...)` and friends -- normalising, never sabotage.
_INLINE_NORMALISE = re.compile(
    r'\.replace\s*\(\s*/\s*(?:\\r\\n|\\r|\\s\+|\\n|<!--\[\\s\\S\]\*\?-->)\s*/')
# The applied-check: the mutated text compared against the original, either way
# round, with or without an assertion helper.
_INLINE_APPLIED = re.compile(
    r'notStrictEqual\s*\(|'
    r'assert(?:\.\w+)?\s*\(\s*[A-Za-z_$][\w$.]*\s*!==\s*[A-Za-z_$][\w$.]*|'
    r'!==\s*(?:SRC|SOURCE|ORIG|ORIGINAL)\b')


def inline_control(src):
    """(mutates_its_own_source, verifies_the_mutation_applied).

    Deliberately crude and deliberately conservative: it must not credit a
    suite that merely prints the word MUTATION. Under-claiming is the safe
    direction here for the same reason it is in the probe scan -- a suite
    wrongly called controlled is one nobody will ever come back to.
    """
    s = src or ''
    if not _INLINE_KEYWORD.search(s):
        return (False, False)
    # Strip the normalising replaces before asking whether any mutation remains,
    # so a suite whose ONLY replace is a line-ending fix cannot qualify on it.
    stripped = _INLINE_NORMALISE.sub('.__normalise__(', s)
    if not (_INLINE_ON_SOURCE.search(stripped)
            or _INLINE_MUTATE_TABLE.search(stripped)):
        return (False, False)
    return (True, bool(_INLINE_APPLIED.search(s)))


# ── A THIRD SHAPE: THE MODULE STUB (2026-09-18) ────────────────────────────
# `api/sd-data-dental-ledger-validation.test.js` carries FORTY-SEVEN mutation
# arms and this counter could not see one of them. It does not sabotage source
# TEXT at all -- there is no `.replace(` to find. It replaces a module's
# EXPORTS in `require.cache` with a permissive stub, re-requires the handler so
# it binds the stub, and asserts that each bad row now REACHES THE STORE. That
# is a negative control in the only sense that matters: it proves the refusal
# the suite above it asserts is coming from the validator and not from
# somewhere incidental.
#
# THE ASSIGNMENT IS THE MUTATION; THE DELETE IS NOT. Measured across
# tests/*.js and api/*.test.js before writing a line of this: TWENTY-TWO files
# install something into require.cache and TEN more only `delete` from it. A
# delete is cache hygiene -- re-require this module so it picks up new env --
# and crediting it would hand a control badge to a third of the api/ suites.
# Even the assignment alone is not enough: of those 22, TWENTY-ONE are stubbing
# a dependency to make the handler testable at all, which is scaffolding, not
# sabotage. Exactly ONE also announces a mutation. That is the discrimination
# doing the work, and the fixtures below pin both must-not-fire cases because
# over-claiming here would be worse than the blindness it replaces -- a suite
# wrongly called controlled is one nobody will ever come back to.
#
# THE APPLIED-CHECK HAS TO BE BEHAVIOURAL, AND THAT IS NOT A WEAKER STANDARD.
# For a `str.replace` control the applied-check is textual: compare the mutated
# copy with the original and see that they differ. A module stub has no "before"
# string to diff -- the swap either bound or it did not, and Node reports a
# failed bind as a warning, not an error. This file's own header records that
# exact defect: an early version installed an UNDEFINED validator instead of a
# permissive one, Node said only "non-existent property ... inside circular
# dependency", and the arms would have died on a TypeError while looking like
# they had proved something. So the check is an assertion that the NEUTERED run
# behaves differently from the real one, carrying a message that says the arm
# proves nothing if the mutation did not take. That is the same guarantee the
# textual diff gives, obtained the only way this shape allows.
# ── THE SENTINELS LIVE HERE, BECAUSE A SECOND COPY WENT STALE IMMEDIATELY ──
# `tests/run_suite_control_coverage_probe.py` carried the literal `'(inline)'`
# in three places to mean "this credit is a sentinel, not a filename". Adding a
# SECOND sentinel broke all three arms at once -- the probe read
# `(inline: module stub)` as a probe FILENAME, went looking for a file by that
# name, and reported the tool as over-claiming. The set is defined once, here,
# beside the code that emits it, and the probe imports it. A third shape added
# later cannot repeat this.
INLINE_SENTINELS = ('(inline)', '(inline: module stub)')

_STUB_INSTALL = re.compile(
    r'require\s*\.\s*cache\s*\[\s*require\s*\.\s*resolve\s*\([^)]*\)\s*\]\s*=')
_STUB_APPLIED = re.compile(
    r'proves? nothing|asserts? nothing|did not restore|mutation did not', re.I)


def module_stub_control(src):
    """(mutates_a_module, verifies_the_mutation_applied) for the stub shape.

    Same contract and the same conservative bias as inline_control(): a suite
    that merely re-requires a module is NOT a control, and one that stubs
    without a behavioural check is reported separately rather than credited.
    """
    from checker_kit import strip_comments
    s = strip_comments(src or '')
    if not _INLINE_KEYWORD.search(s):
        return (False, False)
    if not _STUB_INSTALL.search(s):
        return (False, False)
    return (True, bool(_STUB_APPLIED.search(s)))


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

    # The inline pass. Runs over the SUITES, not the probes, because the file
    # being examined is both at once.
    inline_unverified = []
    for s in suites:
        b = os.path.basename(s)
        try:
            ssrc = io.open(s, encoding='utf-8', errors='replace').read()
        except Exception as e:                                   # noqa: BLE001
            unreadable.append((b, '%s: %s' % (type(e).__name__, e)))
            continue
        mutates, applied = inline_control(ssrc)
        sm, sa = module_stub_control(ssrc)
        if not mutates and not sm:
            continue
        if applied or sa:
            # Credited under a sentinel rather than a filename, so a reader can
            # never mistake it for a probe file that does not exist. The two
            # shapes carry DIFFERENT sentinels: a reader looking at a coverage
            # figure should be able to see which kind of control is behind it
            # without opening the suite, because they fail in different ways.
            controllers.setdefault(b, []).append(
                '(inline)' if applied else '(inline: module stub)')
        elif b not in controllers:
            inline_unverified.append(b)
    return ([os.path.basename(s) for s in suites], controllers, unreadable,
            inline_unverified)


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

    # ── THE INLINE CONTROL, LOCKED IN THREE DIRECTIONS (2026-09-17) ────────
    # Criteria fixed against synthetic sources BEFORE the real tree is read.
    # The third fixture is the one that matters: a suite that mutates and never
    # checks the mutation APPLIED must NOT be credited, because str.replace on
    # a stale anchor does nothing silently and the arm then passes against an
    # unmodified file.
    INLINE_OK = (
        "// MUTATION PROBES. Each reverts a fix and asserts the arm goes red.\n"
        "const probes = [['id minting removed', (s) => s.replace(/X/, ''), fn]];\n"
        "for (const [name, mutate] of probes) {\n"
        "  probeSrc = mutate(SRC);\n"
        "  assert.ok(probeSrc !== SRC, 'probe did not change the source: ' + name);\n"
        "}\n")
    INLINE_OK2 = (
        "section('MUTATION: the pre-fix save, restored, inflates the panel');\n"
        "const out = src.replace(/function save\\(/, 'function save2(');\n"
        "assert.notStrictEqual(out, src, 'save() was not found');\n")
    INLINE_UNVERIFIED = (
        "// MUTATION: put the old branch back\n"
        "const out = src.replace('if (guard)', 'if (false && guard)');\n"
        "runAgainst(out);\n")
    INLINE_NONE = (
        "// This suite asserts a lot and breaks nothing.\n"
        "assert.strictEqual(fmt(1), '1.00');\n"
        "const label = name.replace(/_/g, ' ');\n")
    # THE REAL FALSE POSITIVE, verbatim in shape from
    # tests/sairnvet_controlled_export.js: the word appears, and the only
    # replace 800 characters later is a line-ending normalisation on the lifted
    # source. It was named by the first criterion and is not a control.
    #
    # ⚠ THE FIRST VERSION OF THIS FIXTURE COULD NOT FAIL, which is the defect
    # this file's own docstring records about the docstring fixture, reproduced
    # by the same author one screen further down. It read
    # `const SRC = fs.readFileSync(APP,'utf8').replace(/\r\n/g,'\n')` -- and the
    # receiver there is a CALL, not a name, so _INLINE_ON_SOURCE never matched
    # it and the arm passed whether the normalise-strip worked or not. The
    # mutation that removes the strip came back SILENT and that is how it was
    # found. The receiver is a named variable now, exactly as in the real
    # tests/sairnlaw_csp.js that produced the false positive.
    INLINE_NORMALISE_ONLY = (
        "// The export is compared byte for byte; no mutation is attempted here.\n"
        "const CODE = src.replace(/<!--[\\s\\S]*?-->/g, '');\n"
        "assert.ok(CODE.length > 0);\n")

    # ── THE MODULE-STUB SHAPE, LOCKED IN BOTH DIRECTIONS ──────────────────
    # Reduced from api/sd-data-dental-ledger-validation.test.js. The two
    # must-NOT-fire fixtures are the important ones: 21 of the 22 files that
    # install into require.cache are stubbing a dependency to make a handler
    # testable, and 10 more only delete from it. Crediting either would hand a
    # control badge to a third of api/.
    STUB_OK = (
        "// MUTATION: the validator is stubbed to null so the bad row is stored.\n"
        "delete require.cache[require.resolve('./_lib/dental-ledger')];\n"
        "require.cache[require.resolve('./_lib/dental-ledger')] = { exports: stub };\n"
        "assert.strictEqual(res.statusCode, 200,\n"
        "  'the mutation did not restore the pre-fix behaviour -- the arm above proves nothing');\n")
    STUB_UNVERIFIED = (
        "await test('MUTATION (validator stubbed): the bad row is stored', async () => {\n"
        "  require.cache[require.resolve('./_lib/dental-ledger')] = { exports: stub };\n"
        "  assert.strictEqual(res.statusCode, 200);\n"
        "});\n")
    # ── THE ANNOUNCEMENT MUST SURVIVE COMMENT-STRIPPING, AND THAT WAS
    #    MEASURED RATHER THAN PREFERRED ─────────────────────────────────────
    # The keyword is looked for in the STRIPPED source, so a suite that says
    # MUTATION only in a comment is not recognised. That is under-claiming and
    # it is deliberate: reading the keyword from RAW source instead admits FIVE
    # more files immediately -- sd-agent-budget, dental-financial-tier,
    # dental-provider-scope, employees-refusal, sairnlaw-resources -- and I read
    # all five. Every one is PROSE: a comment narrating that some SEPARATE
    # negative control found a defect, or that an arm survived a probe. Not one
    # is a stub control. Crediting them would be precisely the over-claim this
    # file's docstring says it must never make, so the cost is paid the other
    # way: a real stub control announced only in a comment reads as
    # uncontrolled until the word appears in the arm's own label.
    #
    # THIS FIXTURE ALSO CARRIES AN APPLIED-CHECK PHRASE, on purpose. It must
    # fail on the KEYWORD rule alone, so it cannot pass by accidentally missing
    # two conditions at once.
    STUB_COMMENT_ONLY = (
        "// MUTATION: the validator is stubbed to null.\n"
        "require.cache[require.resolve('./_lib/dental-ledger')] = { exports: stub };\n"
        "assert.strictEqual(res.statusCode, 200, 'otherwise the arm proves nothing');\n")
    # SCAFFOLDING, NOT SABOTAGE. The real shape of the other 21.
    STUB_SCAFFOLD = (
        "// Stub the licence check so the handler can be driven at all.\n"
        "require.cache[require.resolve('./_lib/license')] = { exports: fakeLicense };\n"
        "assert.strictEqual(res.statusCode, 200);\n")
    # CACHE HYGIENE, NOT A MUTATION. The real shape of the other 10.
    #
    # ⚠ THE FIRST VERSION OF THIS FIXTURE COULD NOT FAIL, and it was caught by
    # mutating this file rather than by reading it. It announced the mutation
    # in a COMMENT, which strip_comments removes, so it never reached the
    # assignment-vs-delete rule at all -- it was stopped one gate earlier by the
    # keyword. Loosening _STUB_INSTALL to match any `require.cache[` left the
    # self-check GREEN, which is the whole defect this platform records as a
    # control that cannot fail. The announcement is in a test LABEL now, so the
    # fixture reaches the rule it is named after.
    #
    # IT IS LOAD-BEARING AGAINST REAL FILES: of the ten suites that only delete
    # from require.cache, sairnbiz_timesheet_hours.js and
    # claude-guardrail-metamorphic.test.js DO announce a mutation in code, so a
    # loosened shape rule would credit both of them on cache hygiene alone.
    STUB_DELETE_ONLY = (
        "await test('MUTATION arms re-require the handler for a clean state',\n"
        "  async () => {\n"
        "    delete require.cache[require.resolve('./sd-data.js')];\n"
        "    const handler = require('./sd-data.js');\n"
        "  });\n")

    ck('a module-stub control that checks the mutation BEHAVED counts',
       module_stub_control(STUB_OK) == (True, True), module_stub_control(STUB_OK))
    ck('...with no behavioural check it is MUTATES-BUT-UNVERIFIED',
       module_stub_control(STUB_UNVERIFIED) == (True, False),
       module_stub_control(STUB_UNVERIFIED))
    ck('MUST NOT FIRE: stubbing a dependency to make a handler testable is '
       'scaffolding, not sabotage',
       module_stub_control(STUB_SCAFFOLD) == (False, False),
       module_stub_control(STUB_SCAFFOLD))
    ck('MUST NOT FIRE: a bare delete from require.cache is cache hygiene, '
       'even with the word MUTATION in the file',
       module_stub_control(STUB_DELETE_ONLY) == (False, False),
       module_stub_control(STUB_DELETE_ONLY))
    ck('MUST NOT FIRE: an announcement living only in a COMMENT -- reading the '
       'keyword raw would admit five prose mentions, measured and read today',
       module_stub_control(STUB_COMMENT_ONLY) == (False, False),
       module_stub_control(STUB_COMMENT_ONLY))
    ck('MUST NOT FIRE: the replace-shape fixtures are not module stubs',
       module_stub_control(INLINE_OK) == (False, False),
       module_stub_control(INLINE_OK))

    ck('an inline control that VERIFIES the mutation applied counts',
       inline_control(INLINE_OK) == (True, True), inline_control(INLINE_OK))
    ck('...and the notStrictEqual spelling of the same check counts',
       inline_control(INLINE_OK2) == (True, True), inline_control(INLINE_OK2))
    ck('an inline mutation with NO applied-check is MUTATES-BUT-UNVERIFIED',
       inline_control(INLINE_UNVERIFIED) == (True, False),
       inline_control(INLINE_UNVERIFIED))
    ck('a suite that merely uses .replace() for FORMATTING is not a control -- '
       'this is the over-claim the whole file must not make',
       inline_control(INLINE_NONE) == (False, False), inline_control(INLINE_NONE))
    ck('...nor is one whose only replace on the SOURCE normalises line endings '
       '-- the real false positive the first criterion produced',
       inline_control(INLINE_NORMALISE_ONLY) == (False, False),
       inline_control(INLINE_NORMALISE_ONLY))

    # END TO END, because the arms above test the predicate and a wiring
    # mistake in survey() would leave every one of them green.
    import tempfile
    tmpi = tempfile.mkdtemp(prefix='suite_inline_')
    io.open(os.path.join(tmpi, 'selfcontrolled.js'), 'w',
            encoding='utf-8').write(INLINE_OK)
    io.open(os.path.join(tmpi, 'unverified.js'), 'w',
            encoding='utf-8').write(INLINE_UNVERIFIED)
    io.open(os.path.join(tmpi, 'plain.js'), 'w', encoding='utf-8').write(INLINE_NONE)
    io.open(os.path.join(tmpi, 'stubcontrolled.js'), 'w',
            encoding='utf-8').write(STUB_OK)
    io.open(os.path.join(tmpi, 'stubscaffold.js'), 'w',
            encoding='utf-8').write(STUB_SCAFFOLD)
    io.open(os.path.join(tmpi, 'stubunverified.js'), 'w',
            encoding='utf-8').write(STUB_UNVERIFIED)
    _ni, _ci, _bi, _ii = survey(sorted(glob.glob(os.path.join(tmpi, '*.js'))), [])
    ck('end to end: the self-controlled suite is CREDITED, tagged (inline)',
       _ci.get('selfcontrolled.js') == ['(inline)'], _ci)
    ck('end to end: the module-stub suite is CREDITED under its OWN sentinel',
       _ci.get('stubcontrolled.js') == ['(inline: module stub)'], _ci)
    ck('end to end: dependency scaffolding is credited by NEITHER shape and is '
       'not even named as unverified',
       'stubscaffold.js' not in _ci and 'stubscaffold.js' not in _ii, (_ci, _ii))
    ck('end to end: a stub with no behavioural check is NOT credited and IS named',
       'stubunverified.js' not in _ci and 'stubunverified.js' in _ii, (_ci, _ii))
    ck('end to end: the unverified one is NOT credited and IS named',
       'unverified.js' not in _ci and 'unverified.js' in _ii, (_ci, _ii))
    ck('end to end: the plain suite appears in neither',
       'plain.js' not in _ci and 'plain.js' not in _ii, (_ci, _ii))

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
    names, ctl, bad, inl = survey(
        sorted(glob.glob(os.path.join(tmp, '*.js'))),
        sorted(glob.glob(os.path.join(tmp, '*.py'))))
    ck('end to end: the controlled suite is reported controlled',
       ctl.get('target_suite.js') == ['p_probe.py'], ctl)
    ck('end to end: the uncontrolled suite is reported uncontrolled',
       'lonely_suite.js' in names and 'lonely_suite.js' not in ctl, (names, ctl))

    # A PROBE THAT WILL NOT PARSE IS A THIRD STATE. Folding it into "no control"
    # would report a suite as uncovered on the strength of a syntax error.
    io.open(os.path.join(tmp, 'broken_probe.py'), 'w', encoding='utf-8').write('def (\n')
    _n2, _c2, bad2, _i2 = survey(sorted(glob.glob(os.path.join(tmp, '*.js'))),
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
        names, ctl, unreadable, inline_unverified = survey()
    except Exception as e:                                       # noqa: BLE001
        print('COULD NOT RUN: %s: %s' % (type(e).__name__, e))
        return EXIT_COULD_NOT_RUN

    uncontrolled = [n for n in names if n not in ctl]
    # ── COUNT BOTH SENTINELS, AND SAY WHICH ─────────────────────────────────
    # This read `'(inline)' in ctl[b]` and nothing else, so the module-stub
    # suite was credited in the headline total and then invisible in the line
    # that breaks that total down -- 62 controlled, 9 inline, and one suite
    # inline-but-not-counted-as-inline. That is this file's own docstring
    # defect, "a census whose universe is one spelling of a thing reports every
    # other spelling as absent", reproduced by me one screen below where it is
    # written down. Both shapes are counted and they are counted SEPARATELY,
    # because they fail differently: a replace-shape control goes quiet when
    # its anchor rots, a module stub goes quiet when the bind does not take.
    inline_n = len([b for b in ctl if '(inline)' in ctl[b]])
    stub_n = len([b for b in ctl if '(inline: module stub)' in ctl[b]])

    if args.json:
        print(json.dumps({'suites': len(names), 'controlled': sorted(ctl),
                          'uncontrolled': uncontrolled,
                          'inline_unverified': inline_unverified,
                          'unreadable_probes': unreadable}, indent=1))
        return 1 if uncontrolled else 0

    if not args.quiet:
        print('SUITE CONTROL COVERAGE -- report only, nothing gates on this')
        print('  %d suite(s) -- tests/*.js and api/*.test.js' % len(names))
        print('  %d have a negative control (a probe that BREAKS the source and '
              'asserts' % len(ctl))
        print('  the suite goes red); %d have never been sabotaged at all.'
              % len(uncontrolled))
        print('  of the controlled ones, %d carry the control INLINE rather than in\n  a separate probe file -- invisible to this counter until 2026-09-17,\n  which is why every earlier headline was an undercount.' % inline_n)
        print('  and %d sabotage a MODULE rather than source text -- a require.cache\n  stub, invisible here until 2026-09-18. The two are counted apart because\n  they go quiet differently: a replace when its anchor rots, a stub when the\n  bind does not take.' % stub_n)
        if inline_unverified:
            print('')
            print('  MUTATES WITH NO VISIBLE APPLIED-CHECK -- not counted as')
            print('  controlled, and READ THESE rather than fixing them blind.')
            print('  str.replace on an anchor that stopped matching does NOTHING,')
            print('  silently, and the arm then runs against an unmodified file and')
            print('  passes -- which is what an applied-check exists to stop.')
            print('  BUT THE CHECK CAN BE IMPLICIT AND THIS CANNOT SEE THAT:')
            print('  tests/base_prompt_single_source.js asserts the mutated copy')
            print('  counts TWO, which is only true if the replace applied, so it is')
            print('  sound and is listed here anyway. Under-claiming on purpose:')
            for b in inline_unverified:
                print('    *** %s' % b)
        print('')
        for s in sorted(ctl):
            tag = 'SELF-CONTROLLED' if '(inline)' in ctl[s] else 'CONTROLLED'
            print('  %-15s %-46s %s' % (tag, s, ', '.join(ctl[s])))
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
