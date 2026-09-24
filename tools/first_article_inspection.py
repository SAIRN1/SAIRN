"""Item 47 -- is a NEW artefact verified against EVERY claim it makes, or spot-checked?

    python tools/first_article_inspection.py                  # everything new in the window
    python tools/first_article_inspection.py --since 2026-09-15
    python tools/first_article_inspection.py --subject tools/x.py
    python tools/first_article_inspection.py --fixtures       # blind lock, reads no history
    python tools/first_article_inspection.py --json

Exit 0 when every new artefact has a suite, 1 when one does not, 2 when the
history could not be read. REPORT ONLY.

── WHAT FIRST ARTICLE INSPECTION IS ───────────────────────────────────────────
From manufacturing: before a production run is accepted, the FIRST part off the
line is measured against EVERY dimension on the drawing -- not a sample, not the
dimensions somebody thinks are risky. All of them, once, on article one.

`docs/2026-09-14-first-article-inspection.md` applied that by hand to two
artefacts and found both clean. This is the same method, mechanised as far as it
can honestly go and no further.

── THE TWO LAYERS, AND ONLY ONE OF THEM GETS A VERDICT ────────────────────────
  MECHANICAL, AND IT DOES GET A VERDICT
      Does the artefact have a suite AT ALL? Zero arms verify zero claims. No
      matching is needed to know that, so it is answered outright.

  THE WORKSHEET, AND IT DOES NOT
      Both lists -- the claims the artefact's own header makes, and the arms its
      suite contains -- printed side by side and DELIBERATELY NOT MATCHED.

THE REFUSAL TO MATCH IS LOAD-BEARING. Pairing a prose claim to a prose arm label
is word-overlap scoring, and on this platform that returned 38% accuracy with
FIVE false positives out of five. The FAI document says so in as many words:
"The two lists are not matched automatically, and must not be." A tool that
scored the mapping would produce a percentage nobody could act on and everybody
would quote.

── WHERE A CLAIM COMES FROM ───────────────────────────────────────────────────
On this platform a new artefact's requirements ARE the claims its own header
makes about itself -- "fails closed", "refuses when X", "never Y". That is the
drawing it will be measured against, and it is the only spec that exists.

── WHAT IT CANNOT DO ──────────────────────────────────────────────────────────
  * Tell you a claim is verified. That is the human mapping, on purpose.
  * See a requirement the header does not state. An artefact that claims little
    passes this trivially, and a SHORT claim list is itself worth a look rather
    than a relief.
  * Judge arm quality. An arm that asserts True passes every count here. That is
    what mutation-testing is for, and it is a different tool.
"""
import ast
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SINCE = '2026-09-15'

# A claim is an assertion the artefact makes ABOUT ITS OWN BEHAVIOUR. These are
# the markers this platform's headers actually use, taken from real files rather
# than invented: capitals are how emphasis is written here.
CLAIM_MARKERS = re.compile(
    r'\b(refuses?|refusing|never|always|must|cannot|fails? closed|does not|'
    r'do not|will not|is not|are not|only|every|no \w+ (?:is|are|may)|'
    r'REFUSES?|NEVER|ALWAYS|MUST|CANNOT|NOT)\b')

# ── ARMS ARE FOUND BY DISCOVERING THE DIALECT, NOT BY NAMING IT ───────────────
# A hardcoded list of helper names (check/ck/test/it) was written first and
# UNDER-COUNTED SILENTLY: api/_lib/safe-number.test.js declares
# `function t(name, fn)` and every one of its arms is `t('...')`, so the file
# reported ZERO arms while being a real suite. That is the anchor-stops-matching
# failure with no announcement, on the first real run.
#
# So the helper is inferred per file: a short identifier called at statement
# start with a STRING LITERAL first argument, at least MIN_ARM_CALLS times. And
# when no identifier reaches that bar in a file that IS a suite, the answer is
# COULD NOT TELL -- not zero. Those are different facts and only one of them is
# a finding about the suite.
ARM_CALL_RX = re.compile(r"^[ \t]*([A-Za-z_$][\w$]*)\(\s*(['\"])((?:[^'\"\\]|\\.)*?)\2",
                         re.M)
NOT_ARM_HELPERS = {
    'require', 'import', 'print', 'console', 'log', 'describe', 'section',
    'open', 'json', 'io', 'os', 're', 'sys', 'path', 'write', 'append',
    'push', 'setattr', 'getattr', 'parse', 'header', 'suites', 'if', 'for',
    'while', 'return', 'raise', 'sys.stderr',
}
MIN_ARM_CALLS = 3


def git(*args):
    p = subprocess.run(['git'] + list(args), cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return p.stdout if p.returncode == 0 else None


def added_since(since):
    """Artefacts ADDED (not modified) in the window. Returns None when git could
    not answer -- an empty list would report "nothing new, all clear"."""
    out = git('log', '--since=' + since + 'T00:00', '--name-status',
              '--diff-filter=A', '--pretty=format:', '--', 'tools/', 'api/')
    if out is None:
        return None
    files = sorted({l.split('\t')[1] for l in out.splitlines()
                    if l.startswith('A\t') and '\t' in l})
    return [f for f in files
            if (f.endswith('.py') or f.endswith('.js'))
            and not f.endswith('.test.js')
            and '/test' not in f and not os.path.basename(f).startswith('test_')]


def header(path):
    """The artefact's own header -- the module docstring, or the leading block
    comment. Everything after the first blank line following it is code."""
    src = io.open(os.path.join(REPO, path), encoding='utf-8',
                  errors='replace').read()
    if path.endswith('.py'):
        # SKIP THE SHEBANG AND ANY LEADING COMMENTS FIRST. Three tools shipped
        # tonight start `#!/usr/bin/env python` and a regex anchored at the top
        # of the file read their claim count as ZERO -- a tool reporting that
        # somebody's header makes no claims, because of its own anchor.
        body = re.sub(r'\A(?:\s*#[^\n]*\n)+', '', src)
        m = re.match(r'\s*(?:[rubRUB]{0,2}["\']{3})(.*?)["\']{3}', body, re.S)
        return m.group(1) if m else ''
    lines, out = src.splitlines(), []
    for l in lines:
        s = l.strip()
        if s.startswith('//') or s.startswith('/*') or s.startswith('*'):
            out.append(re.sub(r'^\s*(?://+|/\*+|\*+/?)\s?', '', l))
        elif not s and out:
            continue
        elif out:
            break
    return '\n'.join(out)


def claims(text):
    """Sentences in the header that assert behaviour. Bullets and prose both;
    this platform writes requirements as both."""
    flat = re.sub(r'\s+', ' ', re.sub(r'[─-╿]+', ' ', text))
    out = []
    for s in re.split(r'(?<=[.;:])\s+(?=[A-Z`*•])|\n', flat):
        s = s.strip(' -*•')
        if len(s) < 25 or len(s) > 400:
            continue
        if CLAIM_MARKERS.search(s):
            out.append(s)
    return out


def suites(subject, all_tests):
    """Test files that verify THIS artefact, matched STRICTLY.

    A substring search is not good enough and that was measured rather than
    assumed: `tools/sabotage.py` matched 34 files on a loose search because the
    word appears everywhere on this platform. So a suite counts only when it
    names the artefact by CONVENTION or IMPORTS it.
    """
    base = os.path.basename(subject)
    stem = base.rsplit('.', 1)[0]
    by_convention = {
        'tests/run_%s_probe.py' % stem.replace('-', '_'),
        'tests/run_%s_probe.py' % stem.replace('_', '-'),
        os.path.dirname(subject) + '/' + stem + '.test.js',
    }
    # TWO CLASSES, AND THEY ARE SEPARATE NOW (2026-09-24). They used to be one
    # list, and folding them cost 19 artefacts their suites the first time the
    # named-only rule was applied -- api/_lib/auth.js alone lost 51 real test
    # files. A `.test.js` requires './_lib/auth' WITHOUT the extension, so a
    # rule asking whether the string 'auth.js' appears free in the text answered
    # "no" for every one of them. The named-only question is only meaningful for
    # a hit that came from the BARE NAME; an explicit import is not a mention,
    # it is a dependency, and nothing about cataloguing applies to it.
    strong = [
        re.compile(r'^\s*import\s+%s\b' % re.escape(stem.replace('-', '_')), re.M),
        re.compile(r'^\s*from\s+%s\s+import' % re.escape(stem.replace('-', '_')), re.M),
        re.compile(r'require\([\'"][^\'"]*%s(?:\.js)?[\'"]\)' % re.escape(stem)),
        re.compile(r'from\s+[\'"][^\'"]*%s(?:\.js)?[\'"]' % re.escape(stem)),
    ]
    bare_name = [
        # A python tool driven as a SUBPROCESS rather than imported -- several
        # probes here shell out to the tool instead of importing it, and
        # excluding that shape would report those tools as unverified.
        #
        # BUT NOT AS A DICTIONARY KEY. Being NAMED by a test file is not being
        # TESTED by it, and there is one shape where that difference is total:
        # tests/run_selftest_sweep_probe.py lists
        # `sc_tier_a_write_gate_live_probe.py` as a declared EXCLUSION with a
        # reason, and the bare-name rule read that as coverage -- reporting a
        # PRODUCTION WRITE PATH as verified by the one file that deliberately
        # refuses to run it.
        #
        # THE COLON RULE IS GONE, 2026-09-24. It was narrow on purpose -- only
        # `'name.py':`, a dict KEY -- and cody's review of it drove four more
        # spellings of the identical semantics, every one of which counted as
        # coverage: a set `EXCLUDE = {'w.py', 'x.py'}`, a list `SKIP = ['w.py']`,
        # a tuple `('w.py',)`, and a dict VALUE `{'why': 'w.py'}`. The file that
        # motivated the original fix is one refactor from restoring the defect:
        # tests/run_selftest_sweep_probe.py's EXCLUDE is a dict ONLY because
        # each entry carries a reason string. Drop the reasons, it becomes a
        # set, and a production write path goes back to being reported as
        # verified by the one file that deliberately refuses to run it.
        #
        # The rule encoded now is the PRINCIPLE the old comment stated one
        # paragraph above the narrow regex and did not implement: being NAMED
        # by a test file is not being TESTED by it. See named_only_mention().
        re.compile(r'[\'"]%s[\'"]' % re.escape(base)),
    ]
    hits = []
    for t, txt in all_tests.items():
        if t.replace('\\', '/') in by_convention:
            hits.append(t)
            continue
        if any(rx.search(txt) for rx in strong):
            hits.append(t)
            continue
        if not any(rx.search(txt) for rx in bare_name):
            continue
        if named_only_mention(t, txt, base):
            continue
        hits.append(t)
    return sorted(hits)


# ── NAMED IS NOT TESTED, AND IT IS DECIDED STRUCTURALLY (2026-09-24) ──────────
# The previous rule was a negative lookahead for a colon, so it answered a
# question about PUNCTUATION when the question is about POSITION: is this the
# name of a thing the file drives, or an entry in a list of things it declines
# to drive? Four spellings of "declines" had different punctuation and all four
# read as coverage.
#
# For a PYTHON test file the position is decidable exactly, with ast: a string
# literal that is only ever an element of a set/list/tuple or a key/value of a
# dict is a catalogue entry, not a call. That also closes cody's SECOND finding
# for free and by construction rather than by another pattern -- ast does not
# see comments at all, so a test file containing nothing but
# `# 'w.py' is not driven here` no longer returns w.py as a suite. It was
# returning it, and that is the shape most likely to say the exact opposite of
# what it is read as.
#
# For anything else -- a .js suite -- the comments are stripped first (using the
# canonical stripper, which as of the same day parses regex literals) and the
# bare-name search runs on what is left. There is no AST for that half and this
# says so rather than implying one.
#
# WHAT IT DELIBERATELY DOES NOT DO: decide that a NAME plus an invocation token
# is required. That was tried, measured, and over-corrected -- it dropped two
# tools whose probes name them in prose and cover them perfectly well.
def named_only_mention(test_path, text, base):
    """True when `base` appears in this test file ONLY as a catalogue entry.

    False when it appears anywhere a caller would actually reach it, and False
    when this cannot be decided -- a could-not-tell must not silently remove a
    suite, because the direction that loses a real suite is the expensive one.
    """
    if test_path.endswith('.py'):
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return False           # COULD NOT TELL -> keep the suite
        catalogued, free = 0, 0
        inside = set()
        # A DECLARED container, not any container. The first version of this
        # marked every element of every collection literal and immediately
        # failed its own fixture: `subprocess.run([exe, 'widget.py'])` puts the
        # name in a LIST, and that list is an argument to a call -- the file is
        # driving the tool, which is the opposite of cataloguing it. So only a
        # collection that is the VALUE OF AN ASSIGNMENT counts, which is what
        # `EXCLUDE = {...}` / `SKIP = [...]` actually are.
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            val = getattr(node, 'value', None)
            if not isinstance(val, (ast.Set, ast.List, ast.Tuple, ast.Dict)):
                continue
            for sub in ast.walk(val):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    inside.add(id(sub))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            if base not in node.value:
                continue
            if id(node) in inside:
                catalogued += 1
            else:
                free += 1
        # `free == 0` covers BOTH catalogue-only shapes at once: every string
        # occurrence sits in a declared collection (catalogued > 0), or ast saw
        # no string occurrence at all -- and since this function only runs on a
        # bare-name regex hit, no-occurrence-in-the-AST means the mention lives
        # in a COMMENT, which ast does not see. That closes cody's finding 2 by
        # construction rather than by another pattern. This function is never
        # reached for a convention or import hit, so there is no third source.
        return free == 0
    stripped = _strip_comments(text)
    return not re.search(r'[\'"]%s[\'"]' % re.escape(base), stripped)


def _strip_comments(text):
    """The canonical stripper, or the text unchanged if it cannot be imported.

    NOT a local reimplementation. tools/comment_quote_check.py owns this
    question and has been wrong about it twice -- `https://` read as a comment,
    then a quote inside a regex literal handing real comments to callers as
    code. A second copy here would be a third chance to be wrong differently.
    """
    try:
        sys.path.insert(0, os.path.join(REPO, 'tools'))
        from comment_quote_check import strip_comments
        return strip_comments(text)
    except Exception:
        return text


def arm_helpers(text):
    """Which identifier this file uses for an arm. Empty when none qualifies."""
    counts = {}
    for m in ARM_CALL_RX.finditer(text):
        name = m.group(1)
        if name in NOT_ARM_HELPERS or len(name) > 12:
            continue
        counts[name] = counts.get(name, 0) + 1
    return sorted(n for n, c in counts.items() if c >= MIN_ARM_CALLS)


def arms(text):
    """Arm labels, or None when the dialect could not be identified.

    None is NOT zero. A suite whose helper this cannot recognise has an unknown
    number of arms; reporting that as 0 would turn a tool limitation into a
    finding about somebody else's work."""
    helpers = arm_helpers(text)
    if not helpers:
        return None
    out = []
    for m in ARM_CALL_RX.finditer(text):
        if m.group(1) in helpers:
            out.append(re.sub(r'\s+', ' ', m.group(3))[:160])
    return out


def load_tests():
    """Every test file on disk, by path. None if the tree is missing."""
    found = {}
    for root in ('tests', 'api'):
        base = os.path.join(REPO, root)
        if not os.path.isdir(base):
            continue
        for dp, _dn, fn in os.walk(base):
            for f in fn:
                if f.endswith('.test.js') or (root == 'tests'
                                              and f.endswith(('.py', '.js'))):
                    p = os.path.join(dp, f)
                    rel = os.path.relpath(p, REPO).replace('\\', '/')
                    found[rel] = io.open(p, encoding='utf-8',
                                         errors='replace').read()
    return found or None


# ── AN IN-FILE SELF-TEST IS A SUITE, AND IT IS A WEAKER KIND ──────────────────
# THE THIRD TIME THIS TOOL MISTOOK ITS OWN BLIND SPOT FOR A FACT ABOUT SOMEBODY
# ELSE'S WORK. It looked for arms only in `tests/` and `*.test.js`, so a tool
# carrying `--selftest` inside itself reported NO SUITE AT ALL. Measured
# 2026-09-15: of the seven artefacts this reported as having nothing, FIVE had a
# working self-test -- 48 arms between them -- that simply nothing in the suite
# runs. "Unverified" and "unwired" are different states and only one is a gap in
# the work.
#
# IT IS STILL REPORTED SEPARATELY, because it is genuinely weaker on two counts
# and merging them would hide both:
#   * NOT INDEPENDENT. `docs/2026-09-13-cross-domain-disciplines.md` §5: the
#     deep check runs with its subject NOT trusted. A self-test imports nothing
#     and is edited in the same commit as the thing it checks.
#   * NOT RUN. tools/run_all_tests.py discovers tests/ and *.test.js. A
#     `--selftest` nobody invokes is a control that passes in a drawer.
# THE FLAG MUST BE COMPARED AGAINST argv, not merely PRESENT in the file --
# the same tightening tests/run_selftest_sweep_probe.py needed, and for the same
# reason: this file's own source contains the string `--self-check` inside this
# very regex, so a bare substring search reports THIS tool as having a self-test
# it does not have.
# BOTH LANGUAGES, 2026-09-24. The python form compares against sys.argv; the JS
# form against process.argv (`includes` or `indexOf`). The JS half was simply
# absent, so a JS tool with a working self-test was reported UNVERIFIED rather
# than UNWIRED -- the exact conflation the UNWIRED state exists to end,
# surviving in the other language. cody's review said it was not live that day;
# adding the branch is cheaper than re-measuring that claim every time a JS
# tool lands.
SELFTEST_RX = re.compile(
    r"['\"](--self-?check|--selftest)['\"]\s*in\s*(?:sys\.)?argv", re.I)
SELFTEST_JS_RX = re.compile(
    r"argv\s*\.\s*(?:includes|indexOf)\s*\(\s*['\"](--self-?check|--selftest)['\"]", re.I)

# THE BODY ANCHOR TAKES ANY SPELLING, 2026-09-24. It was the literal
# 'def _selftest', and cody's review measured 2 of the 7 real self-tests naming
# theirs `def selftest(` with no underscore -- both were counted over their
# ENTIRE source, right that day only because those two tools had no arm-helper
# calls outside the self-test. Right by luck is the anchor-stops-matching shape
# this file's own arms() comment names.
SELFTEST_DEF_RX = re.compile(
    r'^[ \t]*(?:def\s+_?self_?test\w*\s*\(|function\s+_?self_?test\w*\s*\('
    r'|(?:const|let|var)\s+_?self_?test\w*\s*=)', re.M | re.I)


def selftest_of(subject):
    """(entry-point flag, arm count) when the artefact tests itself, else None.
    The arm count is read from the source, not by RUNNING it -- a tool that
    executed every artefact it inspected would be an arbitrary-code runner."""
    src = io.open(os.path.join(REPO, subject), encoding='utf-8',
                  errors='replace').read()
    m = SELFTEST_RX.search(src) or SELFTEST_JS_RX.search(src)
    if not m:
        return None
    flag = m.group(1)
    d = SELFTEST_DEF_RX.search(src)
    if d:
        body = src[d.start():]
        narrowed = True
    else:
        # NO NAMED SELF-TEST FUNCTION FOUND, so the count below is over the
        # WHOLE FILE and may include arm-helper calls that are not the
        # self-test's. Said in the result rather than silently coinciding --
        # which is what the old fallback did, and it was right by luck.
        body = src
        narrowed = False
    got = arms(body)
    return {'flag': flag, 'arms': 0 if got is None else len(got),
            'whole_file_count': not narrowed}


def inspect(subject, all_tests):
    h = header(subject)
    ss = suites(subject, all_tests)
    self_t = selftest_of(subject)
    a, unknown = [], []
    for s in ss:
        got = arms(all_tests[s])
        if got is None:
            unknown.append(s)
        else:
            a.extend(got)
    return {'subject': subject, 'claims': claims(h), 'suites': ss,
            'arms': None if (unknown and not a) else a,
            'selftest': self_t,
            'dialect_unknown': unknown, 'header_chars': len(h)}


# ── THE BLIND LOCK ────────────────────────────────────────────────────────────
def fixtures():
    import shutil
    import tempfile
    out, bad = [], 0

    def ck(name, cond, detail=''):
        nonlocal bad
        out.append(('  ok   ' if cond else '  FAIL ') + name
                   + ('' if cond else '  <- ' + str(detail)[:220]))
        if not cond:
            bad += 1

    PY_HEADER = '"""A widget.\n\nIt REFUSES to run when the input is absent.\n' \
                'It never writes outside its own directory.\n' \
                'Ordinary prose that asserts nothing at all here.\n"""\nimport os\n'
    JS_HEADER = '// A gadget.\n//\n// It must fail closed on a missing key.\n' \
                '// Plain description with no assertion in it.\n\nconst x = 1;\n'

    d = tempfile.mkdtemp(prefix='fai-fixture-')
    try:
        py = os.path.join(d, 'widget.py')
        io.open(py, 'w', encoding='utf-8', newline='\n').write(PY_HEADER)
        js = os.path.join(d, 'gadget.js')
        io.open(js, 'w', encoding='utf-8', newline='\n').write(JS_HEADER)

        sh = os.path.join(d, 'shebanged.py')
        io.open(sh, 'w', encoding='utf-8', newline='\n').write(
            "#!/usr/bin/env python\n# a note\nr'''A widget.\n\n"
            "It REFUSES to run when shebanged.\n'''\n")

        global REPO
        real_repo = REPO
        REPO = d
        try:
            hp = header('widget.py')
            hj = header('gadget.js')
            hsh = header('shebanged.py')
        finally:
            REPO = real_repo

        ck('a python module docstring is read as the header',
           'REFUSES to run' in hp, hp[:100])
        ck('A SHEBANG AND LEADING COMMENTS DO NOT HIDE THE HEADER. Three tools '
           'shipped tonight start `#!/usr/bin/env python`, and an anchor at the '
           'top of the file read their claim count as ZERO -- this tool '
           'reporting that somebody else wrote no requirements, because of its '
           'own regex', 'REFUSES to run when shebanged' in hsh, repr(hsh)[:120])
        ck('...and an r-prefixed docstring is a docstring',
           hsh.strip().startswith('A widget'), repr(hsh)[:80])
        ck('CONTROL: the header STOPS at the code -- an import line is not a '
           'requirement', 'import os' not in hp, hp[-60:])
        ck('a javascript leading comment block is read as the header',
           'must fail closed' in hj, hj[:100])
        ck('CONTROL: and it stops at the code there too',
           'const x' not in hj, hj[-60:])

        cl = claims(hp)
        ck('an assertive sentence is a claim', any('REFUSES' in c for c in cl), cl)
        ck('...and so is a second one, so it is not just the first line',
           any('never writes' in c for c in cl), cl)
        ck('CONTROL: a sentence asserting nothing is NOT a claim. A claim '
           'extractor that takes every sentence turns a long header into a low '
           'score and rewards writing less',
           not any('asserts nothing at all' in c for c in cl), cl)
        ck('CONTROL: a header with no assertions yields no claims, rather than '
           'one empty claim', claims('Just a description of a thing here.') == [])

        CHECKS = ("check('the gate refuses', x)\n"
                  "check('and it says why', y)\n"
                  "check('and the control passes', z)\n")
        TESTS = ("test('it fails closed', f)\n"
                 "test('it reopens', g)\n"
                 "test('and the control', h)\n")
        HOUSE = ("t('a real number survives', f)\n"
                 "t('whitespace is fine', g)\n"
                 "t('a real ZERO survives', h)\n")
        ck('a python check() arm label is extracted',
           arms(CHECKS) == ['the gate refuses', 'and it says why',
                            'and the control passes'], arms(CHECKS))
        ck('a node test() arm label is extracted',
           arms(TESTS) == ['it fails closed', 'it reopens', 'and the control'],
           arms(TESTS))
        ck('THE ARM THAT MADE THIS DISCOVER THE DIALECT: a suite whose helper '
           'is a house-local `t()` is counted too. Hardcoding check/ck/test/it '
           'made api/_lib/safe-number.test.js report ZERO arms while being a '
           'real suite -- an anchor that stopped matching and said nothing',
           arms(HOUSE) == ['a real number survives', 'whitespace is fine',
                           'a real ZERO survives'], arms(HOUSE))
        ck('CONTROL: a bare assert with no label is not counted as an arm -- '
           'counting them would inflate the arm column with things that have no '
           'stated intent',
           arms('assert x == 1\nassert y == 2\nassert z == 3\n') is None)
        ck('CONTROL: an unrecognised dialect is None, NOT zero. Zero is a '
           'finding about the suite; None is a limitation of this tool, and '
           'folding one into the other is how a tool blames somebody else for '
           'its own blind spot', arms('mystery_helper_name_thing(1, 2)\n') is None)
        ck('CONTROL: one call is not a dialect -- a helper must be used at '
           'least %d times, or any function taking a string first argument '
           'becomes an arm' % MIN_ARM_CALLS,
           arms("check('only once', x)\n") is None)
        ck('CONTROL: require() and print() are never arms however often they '
           'appear', arms("require('a')\nrequire('b')\nrequire('c')\n") is None)

        tests = {'tests/run_widget_probe.py': "check('a', 1)\ncheck('b', 2)\n",
                 'tests/unrelated_probe.py': "check('c', 3)\n",
                 'tests/mentions_sabotage.py': 'the word sabotage appears here\n'}
        ck('the conventional probe name is matched',
           suites('tools/widget.py', tests) == ['tests/run_widget_probe.py'],
           suites('tools/widget.py', tests))
        ck('CONTROL: a file that merely CONTAINS the stem as a word is NOT a '
           'suite -- a loose search matched tools/sabotage.py to 34 files, '
           'which is the measurement that made this strict',
           suites('tools/sabotage.py', tests) == [], suites('tools/sabotage.py', tests))
        ck('a probe that IMPORTS the module counts even without the naming '
           'convention',
           suites('tools/widget.py', {'tests/other.py': 'import widget\n'})
           == ['tests/other.py'])
        ck('a .test.js beside the module counts',
           suites('api/_lib/gadget.js', {'api/_lib/gadget.test.js': "test('a', 1)"})
           == ['api/_lib/gadget.test.js'])
        ck('CONTROL: an artefact with NO suite gets an empty list, which is the '
           'one verdict this tool is allowed to reach',
           suites('tools/orphan.py', tests) == [])
        ck('CONTROL: a test file that names the tool as a DICTIONARY KEY does '
           'not count as a suite. tests/run_selftest_sweep_probe.py lists a '
           'production write path as a declared EXCLUSION, and the bare-name '
           'rule read that as coverage -- the one file that refuses to run it '
           'reported as the file that verifies it',
           suites('tools/widget.py',
                  {'tests/excl.py': "EXCLUDE = {'widget.py': 'writes to prod'}"})
           == [])
        ck('CONTROL: and a test file that DRIVES it by name still counts, so '
           'the exclusion is about the colon and not about the quotes',
           suites('tools/widget.py',
                  {'tests/drives.py': "subprocess.run([exe, 'widget.py'])"})
           == ['tests/drives.py'])
        # ── CODY'S FOUR SPELLINGS OF THE SAME EXCLUSION (obligation 69755622,
        # findings 1 and 2, fixed 2026-09-24). The colon rule keyed on
        # PUNCTUATION; a declared exclusion does not need a colon. All four
        # counted as coverage when driven against the shipped regex, and the
        # file that motivated the original fix is one refactor from restoring
        # it -- drop EXCLUDE's reason strings and the dict becomes a set.
        ck("a SET exclusion -- EXCLUDE = {'widget.py', 'x.py'} -- is not a "
           'suite',
           suites('tools/widget.py',
                  {'tests/e1.py': "EXCLUDE = {'widget.py', 'x.py'}"}) == [])
        ck("a LIST exclusion -- SKIP = ['widget.py'] -- is not a suite",
           suites('tools/widget.py',
                  {'tests/e2.py': "SKIP = ['widget.py']"}) == [])
        ck("a TUPLE exclusion -- ('widget.py',) assigned -- is not a suite",
           suites('tools/widget.py',
                  {'tests/e3.py': "SKIP = ('widget.py',)"}) == [])
        ck("a dict VALUE -- {'why': 'widget.py'} -- is not a suite",
           suites('tools/widget.py',
                  {'tests/e4.py': "NOTES = {'why': 'widget.py'}"}) == [])
        ck('a COMMENT is not a suite. A test file containing only '
           "# 'widget.py' is not driven here was returned as the suite that "
           'verifies it -- the shape most likely to say the exact opposite of '
           'what it is read as',
           suites('tools/widget.py',
                  {'tests/c.py': "# 'widget.py' is not driven here\npass\n"})
           == [])
        ck('...and a JS comment neither, which is decided by the CANONICAL '
           'stripper rather than a second local one',
           suites('tools/widget.js',
                  {'tests/c.test.js': "// 'widget.js' is declined here\n"
                                      'const x = 1;\n'}) == [])
        ck('CONTROL: a catalogue entry BESIDE a real drive still counts -- the '
           'question is whether ANY use reaches the tool, not whether every '
           'use does',
           suites('tools/widget.py',
                  {'tests/both.py': "SKIP = ['widget.py']\n"
                                    "subprocess.run([exe, 'widget.py'])\n"})
           == ['tests/both.py'])
        ck('CONTROL: an unparseable python test file KEEPS the suite -- a '
           'could-not-tell must not silently remove one, because losing a real '
           'suite is the expensive direction',
           suites('tools/widget.py',
                  {'tests/broken.py': "subprocess.run([exe, 'widget.py'\n"})
           == ['tests/broken.py'])
        ck('CONTROL: an explicit IMPORT is never subjected to the named-only '
           'test. Folding the two classes cost api/_lib/auth.js all 51 of its '
           'real suites on the first measured run, because a require() names '
           'the module WITHOUT its extension',
           suites('api/_lib/gizmo.js',
                  {'api/thing.test.js':
                   "const g = require('./_lib/gizmo');\ntest('a', 1);\n"
                   "test('b', 2);\ntest('c', 3);\n"})
           == ['api/thing.test.js'])
        # ── FINDINGS 3 AND 4: the self-test anchor and the missing JS half ──
        st_py = os.path.join(d, 'st_plain.py')
        io.open(st_py, 'w', encoding='utf-8', newline='\n').write(
            '"""T. It REFUSES bad input always."""\nimport sys\n'
            'def selftest():\n'
            "    ck('one', 1)\n    ck('two', 2)\n    ck('three', 3)\n"
            "if '--selftest' in sys.argv:\n    selftest()\n")
        st_js = os.path.join(d, 'st_tool.js')
        io.open(st_js, 'w', encoding='utf-8', newline='\n').write(
            '// A tool. It must fail closed.\n'
            'function selfTest() {\n'
            "  ck('one', 1);\n  ck('two', 2);\n  ck('three', 3);\n}\n"
            "if (process.argv.includes('--selftest')) selfTest();\n")
        st_anon = os.path.join(d, 'st_anon.py')
        io.open(st_anon, 'w', encoding='utf-8', newline='\n').write(
            '"""T. It REFUSES bad input always."""\nimport sys\n'
            "ck('outside-a', 1)\nck('outside-b', 2)\nck('outside-c', 3)\n"
            "if '--selftest' in sys.argv:\n    pass\n")
        # REBOUND VIA globals() AND SNAPSHOTTED FIRST. The first version of
        # this arm also wrote `REPO = d` on the line above the snapshot --
        # inside a function that declares `global REPO` for the header arms --
        # so the snapshot read the ALREADY-CLOBBERED value and the restore
        # restored the temp dir. Every real run then reported COULD NOT READ
        # THE TEST TREE: the fixture lock leaking state into the measurement it
        # locks, which is this file's own temporary-state lesson in miniature.
        real_repo2 = globals()['REPO']
        globals()['REPO'] = d
        try:
            got_py = selftest_of('st_plain.py')
            got_js = selftest_of('st_tool.js')
            got_anon = selftest_of('st_anon.py')
        finally:
            globals()['REPO'] = real_repo2
        ck('a self-test named WITHOUT the underscore is narrowed to its own '
           'body -- def selftest( was counted over the whole file, right only '
           'by luck in 2 of the 7 real tools',
           bool(got_py) and got_py['arms'] == 3
           and not got_py['whole_file_count'], got_py)
        ck('a JS self-test (process.argv.includes) is detected at all -- the '
           'python-only detector reported a JS tool with a working self-test '
           'as UNVERIFIED rather than UNWIRED',
           bool(got_js) and got_js['arms'] == 3
           and not got_js['whole_file_count'], got_js)
        ck('CONTROL: a flag with NO named self-test function is counted over '
           'the whole file AND SAYS SO, instead of the two numbers silently '
           'coinciding',
           bool(got_anon) and got_anon['whole_file_count'], got_anon)
        ck('CONTROL: the tool NEVER pairs a claim to an arm -- the FAI document '
           'says the two lists must not be matched automatically, and a scoring '
           'function here would be the 38%-with-five-false-positives result '
           'wearing a new name',
           not any(n in globals() for n in ('match_claims', 'score_coverage',
                                            'coverage_pct')))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return out, bad


def main(argv):
    if '--fixtures' in argv:
        lines, bad = fixtures()
        print('FIRST ARTICLE INSPECTION -- blind lock, %d arms, no history read'
              % len(lines))
        for l in lines:
            print(l)
        print('  %s' % ('ALL FIXTURES PASS' if not bad
                        else '%d FIXTURE(S) FAILED' % bad))
        return 1 if bad else 0

    lines, bad = fixtures()
    if bad:
        print('THE FIXTURE LOCK FAILED -- no artefact was inspected.')
        for l in lines:
            print(l)
        return 2

    all_tests = load_tests()
    if all_tests is None:
        print('COULD NOT READ THE TEST TREE -- nothing was inspected. NOT a pass.')
        return 2

    since = DEFAULT_SINCE
    if '--since' in argv:
        since = argv[argv.index('--since') + 1]
    if '--subject' in argv:
        subs = [argv[argv.index('--subject') + 1].replace('\\', '/')]
    else:
        subs = added_since(since)
        if subs is None:
            print('COULD NOT READ THE HISTORY -- nothing was inspected. NOT a pass.')
            return 2

    results = [inspect(s, all_tests) for s in subs
               if os.path.exists(os.path.join(REPO, s))]
    unverified = [r for r in results if not r['suites'] and not r['selftest']]
    unwired = [r for r in results if not r['suites'] and r['selftest']]

    if '--json' in argv:
        print(json.dumps({'since': since, 'results': results}, indent=2))
        return 1 if unverified else 0

    print('FIRST ARTICLE INSPECTION -- item 47')
    print('  %d fixture arms passed before any artefact was read.' % len(lines))
    print('  %d artefact(s) added since %s.' % (len(results), since))
    print('')
    print('  THE MECHANICAL HALF -- zero arms verify zero claims, and knowing')
    print('  that needs no matching, so it is the one verdict here:')
    if unverified:
        for r in unverified:
            # STATED, NOT EXCLUDED. A file whose own name says probe or harness
            # may legitimately have no probe-of-a-probe -- but this platform's
            # recorded defect class is precisely "the tools written to enforce a
            # rule kept committing the defect they were built to catch", so it
            # is flagged for a human rather than filtered out of the count.
            name = os.path.basename(r['subject'])
            note = '  (itself a test artefact -- judgement, not an exemption)' \
                if re.search(r'probe|harness|sabotage', name) else ''
            print('    NO SUITE AT ALL   %-44s %2d claim(s) in its own header%s'
                  % (r['subject'], len(r['claims']), note))
        print('    %d claim(s) across %d artefact(s), none of them verified by '
              'anything.' % (sum(len(r['claims']) for r in unverified),
                             len(unverified)))
    if unwired:
        print('')
        print('  UNWIRED, WHICH IS NOT THE SAME STATE -- these carry a working')
        print('  self-test that NOTHING IN THE SUITE RUNS. A control that')
        print('  passes in a drawer is not a gap in the work; it is a gap in')
        print('  the wiring, and it is also WEAKER: a self-test is edited in')
        print('  the same commit as its subject, so it is not independent of')
        print('  it (disciplines section 5).')
        for r in unwired:
            print('    %-44s %s, %d arm(s)%s, %d claim(s)'
                  % (r['subject'], r['selftest']['flag'],
                     r['selftest']['arms'],
                     ' COUNTED OVER THE WHOLE FILE -- no named self-test '
                     'function found, so calls outside it may be included'
                     if r['selftest'].get('whole_file_count') else '',
                     len(r['claims'])))
    else:
        print('    every new artefact has at least one suite.')
    print('')
    unknown = [r for r in results if r['dialect_unknown']]
    if unknown:
        print('  COULD NOT TELL, and this is NOT folded into the arm count --')
        print('  these suites exist and their arm dialect was not recognised,')
        print('  which is a limitation of THIS tool, not a finding about them:')
        for r in unknown:
            print('    %-46s %s' % (r['subject'][:46],
                                    ', '.join(os.path.basename(s)
                                              for s in r['dialect_unknown'])))
        print('')

    print('  %-52s %6s %6s  %s' % ('artefact', 'claims', 'arms', 'suite(s)'))
    for r in sorted(results, key=lambda x: (len(x['suites']), -len(x['claims']))):
        n = '   ?' if r['arms'] is None else '%4d' % len(r['arms'])
        print('  %-52s %6d   %s  %s'
              % (r['subject'][:52], len(r['claims']), n,
                 ', '.join(os.path.basename(s) for s in r['suites']) or '-'))
    print('')
    print('  THE COLUMNS ARE NOT A SCORE AND MUST NOT BE READ AS ONE. An')
    print('  artefact with 40 claims and 40 arms may have forty arms on one')
    print('  claim. Mapping claim to arm is a HUMAN pass, on purpose: doing it')
    print('  by word overlap returned 38% accuracy on this platform with five')
    print('  false positives out of five, which is why the FAI document says')
    print('  the two lists must not be matched automatically.')
    print('')
    print('  AND A SHORT CLAIM LIST IS NOT GOOD NEWS. This measures an artefact')
    print('  against the drawing it supplied. One that claims little passes')
    print('  trivially, and nothing here can see a requirement nobody wrote.')
    print('')
    print('  Worksheet for one artefact:')
    print('    python tools/first_article_inspection.py --subject <path>')
    if '--subject' in argv and results:
        r = results[0]
        print('')
        print('  CLAIMS IN ITS OWN HEADER (%d):' % len(r['claims']))
        for c in r['claims']:
            print('    - %s' % c[:150].encode('ascii', 'replace').decode('ascii'))
        print('')
        if r['arms'] is None:
            print('  ARMS IN ITS SUITE: COULD NOT TELL -- the suite exists and '
                  'its dialect was not recognised.')
            return 1
        print('  ARMS IN ITS SUITE (%d):' % len(r['arms']))
        for a in r['arms']:
            print('    * %s' % a[:150].encode('ascii', 'replace').decode('ascii'))
        print('')
        print('  MAP THEM BY HAND. That is the inspection.')
    return 1 if unverified else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
