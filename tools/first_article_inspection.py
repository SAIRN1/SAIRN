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
    imports = [
        re.compile(r'^\s*import\s+%s\b' % re.escape(stem.replace('-', '_')), re.M),
        re.compile(r'^\s*from\s+%s\s+import' % re.escape(stem.replace('-', '_')), re.M),
        re.compile(r'require\([\'"][^\'"]*%s(?:\.js)?[\'"]\)' % re.escape(stem)),
        re.compile(r'from\s+[\'"][^\'"]*%s(?:\.js)?[\'"]' % re.escape(stem)),
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
        # The exclusion is narrow on purpose: `'name.py':` with a colon after
        # it. Requiring an invocation token on the same line was tried and
        # over-corrected, dropping two tools whose probes name them in prose and
        # cover them perfectly well.
        re.compile(r'[\'"]%s[\'"](?!\s*:)' % re.escape(base)),
    ]
    hits = []
    for t, txt in all_tests.items():
        if t.replace('\\', '/') in by_convention:
            hits.append(t)
            continue
        if any(rx.search(txt) for rx in imports):
            hits.append(t)
    return sorted(hits)


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
SELFTEST_RX = re.compile(
    r"['\"](--self-?check|--selftest)['\"]\s*in\s*(?:sys\.)?argv", re.I)


def selftest_of(subject):
    """(entry-point flag, arm count) when the artefact tests itself, else None.
    The arm count is read from the source, not by RUNNING it -- a tool that
    executed every artefact it inspected would be an arbitrary-code runner."""
    src = io.open(os.path.join(REPO, subject), encoding='utf-8',
                  errors='replace').read()
    m = SELFTEST_RX.search(src)
    if not m:
        return None
    flag = m.group(1)
    body = src[src.find('def _selftest'):] if 'def _selftest' in src else src
    got = arms(body)
    return {'flag': flag, 'arms': 0 if got is None else len(got)}


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
            print('    %-44s %s, %d arm(s), %d claim(s)'
                  % (r['subject'], r['selftest']['flag'],
                     r['selftest']['arms'], len(r['claims'])))
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
