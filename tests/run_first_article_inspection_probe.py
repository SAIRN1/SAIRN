"""Does the FAI worksheet see what is there -- and does it refuse to score?

    python tests/run_first_article_inspection_probe.py

Item 47. Two opposite failures, and this tool committed BOTH in its first hour,
which is why each has an arm here rather than a sentence in a docstring:

  UNDER-COUNTING SILENTLY. Arm helpers were hardcoded as check/ck/test/it.
  api/_lib/safe-number.test.js declares `function t(name, fn)` and every arm is
  `t('...')`, so a real suite reported ZERO arms. And a `#!/usr/bin/env python`
  shebang put the docstring out of reach of a top-anchored regex, so three
  tools reported ZERO claims. In both cases the tool was reporting a finding
  about somebody else's work that was actually a fact about its own regex.

  OVER-COUNTING LOOSELY. A substring search for the artefact's stem matched
  tools/sabotage.py to 34 test files, because the word appears everywhere here.

And the thing it must never start doing: pairing a claim to an arm. The FAI
document says the two lists must not be matched automatically -- word-overlap
scoring returned 38% on this platform with five false positives out of five.
Section 6 asserts no scoring function exists, by name.
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import first_article_inspection as F                             # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = F.main(argv)
    return rc, buf.getvalue()


print('\n1. THE TOOL\'S OWN BLIND LOCK RUNS IN THE SUITE')
lines, bad = F.fixtures()
check('every fixture arm passes', bad == 0,
      [l for l in lines if l.startswith('  FAIL')])
check('the lock is not empty', len(lines) >= 20, len(lines))
rc, out = run(['--fixtures'])
check('--fixtures reads no history', 'no history read' in out and rc == 0)

print('\n2. THE HEADER IS FOUND WHEREVER IT ACTUALLY IS')
d = tempfile.mkdtemp(prefix='fai-probe-')
real_repo = F.REPO
try:
    F.REPO = d
    cases = {
        'plain.py': '"""It REFUSES on absence."""\nimport os\n',
        'shebang.py': '#!/usr/bin/env python\n"""It REFUSES on absence."""\n',
        'raw.py': "#!/usr/bin/env python\nr'''It REFUSES on absence.'''\n",
        'comments.py': '#!/usr/bin/env python\n# note\n# note 2\n'
                       '"""It REFUSES on absence."""\n',
        'block.js': '// It must fail closed.\n\nconst a = 1;\n',
    }
    for n, body in cases.items():
        io.open(os.path.join(d, n), 'w', encoding='utf-8', newline='\n').write(body)
    for n in cases:
        h = F.header(n)
        check('the header is found in %s' % n,
              'REFUSES on absence' in h or 'must fail closed' in h, repr(h)[:120])
    io.open(os.path.join(d, 'nohead.py'), 'w', encoding='utf-8',
            newline='\n').write('import os\nx = 1\n')
    check('CONTROL: a file with no header yields an EMPTY header rather than '
          'the first lines of code', F.header('nohead.py') == '',
          repr(F.header('nohead.py')))
    check('CONTROL: the header stops before the code',
          'import os' not in F.header('plain.py'), F.header('plain.py'))
finally:
    F.REPO = real_repo
    shutil.rmtree(d, ignore_errors=True)

print('\n3. CLAIMS ARE ASSERTIONS, NOT EVERY SENTENCE')
check('an assertive sentence is a claim',
      F.claims('It REFUSES to run without a key.') != [])
check('CONTROL: a descriptive sentence is not',
      F.claims('This module formats dates for the reporting page.') == [],
      F.claims('This module formats dates for the reporting page.'))
check('CONTROL: a header of pure description yields ZERO claims, not one -- a '
      'claim extractor that always finds something makes every artefact look '
      'specified', F.claims('A helper. It takes a date and gives a string back '
                            'in a readable form for the page.') == [],
      F.claims('A helper. It takes a date and gives a string back in a '
               'readable form for the page.'))
check('a very short fragment is not a claim, so box-drawing rules and headings '
      'do not inflate the count', F.claims('NEVER') == [])
check('CONTROL: claims are counted from REAL headers -- a tool shipped tonight '
      'with a shebang has a non-zero claim count, which was zero before the '
      'header fix', len(F.claims(F.header('tools/nhi_register.py'))) > 0,
      len(F.claims(F.header('tools/nhi_register.py'))))

print('\n4. ARMS: THE DIALECT IS DISCOVERED, AND UNKNOWN IS NOT ZERO')
HOUSE = "t('one', f)\nt('two', g)\nt('three', h)\n"
check('a house-local helper is discovered', F.arms(HOUSE) == ['one', 'two', 'three'],
      F.arms(HOUSE))
check('CONTROL: a single call is not a dialect', F.arms("t('one', f)\n") is None)
check('CONTROL: an unrecognised file gives None, NOT zero. Zero is a finding '
      'about the suite; None is a limitation of this tool',
      F.arms('nothing_recognisable_here = 1\n') is None)
check('CONTROL: require/print are excluded however often they appear',
      F.arms("require('a')\nrequire('b')\nrequire('c')\n") is None)
check('REAL FILE: the suite whose helper is `t()` is counted, and it is the '
      'file that made this discover the dialect instead of naming it',
      F.arms(io.open(os.path.join(REPO, 'api/_lib/safe-number.test.js'),
                     encoding='utf-8', errors='replace').read()) not in (None, []),
      'safe-number.test.js')

print('\n5. SUITE MATCHING IS STRICT IN ONE DIRECTION AND GENEROUS IN THE OTHER')
tests = {'tests/run_widget_probe.py': "check('a', 1)",
         'tests/mentions.py': 'the word widget appears in this prose\n',
         'tests/drives.py': "subprocess.run([sys.executable, 'widget.py'])\n"}
check('the naming convention matches',
      'tests/run_widget_probe.py' in F.suites('tools/widget.py', tests))
check('a probe that SHELLS OUT to the tool matches -- several probes here drive '
      'the tool as a subprocess and excluding that shape would report them '
      'unverified', 'tests/drives.py' in F.suites('tools/widget.py', tests),
      F.suites('tools/widget.py', tests))
check('CONTROL: prose merely containing the stem does NOT match. A loose search '
      'matched tools/sabotage.py to 34 files',
      'tests/mentions.py' not in F.suites('tools/widget.py', tests),
      F.suites('tools/widget.py', tests))
check('CONTROL: an artefact nothing references gets an empty list',
      F.suites('tools/nothing_at_all.py', tests) == [])

print('\n6. IT DOES NOT SCORE, AND MUST NOT START')
names = dir(F)
check('no function pairs a claim to an arm, by name',
      not any(n in names for n in ('match_claims', 'score_coverage',
                                   'coverage_pct', 'coverage', 'match')), names)
rc, out = run([])
check('the output states that the columns are not a score',
      'NOT A SCORE' in out, out[-900:])
check('...and says why, with the measured number rather than an assertion',
      '38%' in out and 'false positives out of five' in out,
      [l for l in out.splitlines() if '38' in l or 'false positive' in l])
check('...and warns that a SHORT claim list is not good news',
      'claims little passes' in out, out[-900:])

print('\n7. THE REAL POPULATION')
subs = F.added_since('2026-09-15')
check('the added-artefact list builds from real history',
      subs is not None and len(subs) > 0, subs and len(subs))
check('CONTROL: test files are excluded from the SUBJECT list -- a .test.js is '
      'not an artefact needing its own first article',
      all(not s.endswith('.test.js') for s in subs), subs)
_real_git = F.git
try:
    F.git = lambda *a: None
    check('CONTROL: git failing returns None, not [] -- an empty list would read '
          'as "nothing shipped today, all clear", which is the flattering wrong '
          'answer and the one this platform keeps getting caught by',
          F.added_since('2026-09-15') is None, F.added_since('2026-09-15'))
    rc_fail, out_fail = run([])
    check('...and the RUN says COULD NOT READ and exits 2, rather than printing '
          'a clean table over no data', rc_fail == 2 and 'COULD NOT READ' in out_fail,
          (rc_fail, out_fail[:200]))
finally:
    F.git = _real_git
all_tests = F.load_tests()
check('the test tree loads', all_tests is not None and len(all_tests) > 100,
      all_tests and len(all_tests))
verdicts = [F.inspect(s, all_tests) for s in subs
            if os.path.exists(os.path.join(REPO, s))]
check('every inspected artefact yields both lists',
      all('claims' in v and 'suites' in v for v in verdicts))
check('at least one artefact has a suite AND arms, so the extraction is not '
      'uniformly failing', any(v['suites'] and v['arms'] for v in verdicts))
check('CONTROL: and the arm counts are not all identical, which would mean the '
      'extractor was returning something constant',
      len({len(v['arms']) for v in verdicts if v['arms']}) > 3,
      sorted({len(v['arms']) for v in verdicts if v['arms']}))
rc_now, out_now = run([])
nothing_at_all = [v for v in verdicts if not v['suites'] and not v['selftest']]
unwired = [v for v in verdicts if not v['suites'] and v['selftest']]
check('an artefact with NOTHING -- no suite and no self-test -- is a finding, '
      'so the run does not exit 0 while claims sit unverified',
      (rc_now == 1) == bool(nothing_at_all),
      (rc_now, [v['subject'] for v in nothing_at_all]))
check('UNWIRED IS REPORTED AS ITS OWN STATE, not folded into "no suite". Five '
      'artefacts carried a working --selftest that nothing in the suite ran; '
      'reporting those as unverified was this tool mistaking its own blind '
      'spot for a fact about somebody else\'s work, for the third time',
      (not unwired) or 'UNWIRED' in out_now,
      [v['subject'] for v in unwired])
check('CONTROL: the two lists are disjoint, so nothing is counted twice',
      not (set(v['subject'] for v in nothing_at_all)
           & set(v['subject'] for v in unwired)))
check('CONTROL: a self-test is DETECTED by comparing the flag against argv, '
      'not by the string appearing anywhere -- this tool\'s own source contains '
      '"--self-check" inside a regex and enrolled itself on the first run',
      F.selftest_of('tools/sabotage.py') is not None
      and F.selftest_of('tools/traceability_matrix.py') is None,
      (F.selftest_of('tools/sabotage.py'),
       F.selftest_of('tools/traceability_matrix.py')))

print('\n8. COULD-NOT-TELL IS NOT FOLDED INTO A PASS')
check('a suite whose dialect is unknown is recorded separately from the arms',
      all('dialect_unknown' in v for v in verdicts))
check('CONTROL: an artefact with a suite but an unreadable dialect reports arms '
      'as None rather than 0',
      F.inspect('tools/first_article_inspection.py',
                {'tests/run_first_article_inspection_probe.py':
                 'nothing recognisable'})['arms'] is None)
check('the output is ASCII-safe for a cp1252 console',
      out == out.encode('ascii', 'replace').decode('ascii'),
      [l for l in out.splitlines()
       if l != l.encode('ascii', 'replace').decode('ascii')][:2])

print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
