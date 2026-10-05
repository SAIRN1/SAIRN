#!/usr/bin/env python
# OWNER: fourth
r"""A CITED TEST THAT EXISTS AND NEVER LOADS THE THING IT IS CITED FOR.

    python tools/citation_arm_depth_check.py
    python tools/citation_arm_depth_check.py --json
    python tools/citation_arm_depth_check.py --list

REPORT ONLY. Exit 0 clean, 1 findings, 2 COULD NOT RUN. Writes nothing.

── ONE LEVEL DEEPER THAN A DEAD CITATION ──────────────────────────────────
`tools/traceability_matrix.py` already drops a citation naming a file that is
not on disk, and `docs/MASTER-PLAN.md` prints those under DEAD CITATIONS. That
caught `api/sairncash/portal.test.js` -- the index promised coverage of the
Stripe Billing Portal endpoint and no such file existed.

The next shape along is a citation whose test file DOES exist and never
touches its subject. The index reads identically in both cases, the matrix
counts the second one as traced, and nothing looks at whether the arms reach
the endpoint. That is the gap this measures.

── THE POPULATION IS DELIBERATELY NARROW, AND THAT IS THE DESIGN ──────────
`docs/2026-09-29-write-site-basis-rule-scope.md` records a proposed rule that
fired on 82 rows and was killed by RUNNING it: three false-positive classes
accounted for most of them. So this does not try to decide, from prose, what
an arbitrary index row's test "should" exercise. It asks one question that has
a mechanical answer:

    For a source file `X.js` that has a SIBLING `X.test.js`, does that test
    actually LOAD X -- require() it, read it off disk, or spawn it?

A test named for a module and sitting beside it is the author asserting the
pairing; this checks the assertion. Anything outside that pairing is NOT
reported, because for those the subject is a judgement call and a judgement
call reported as a defect is how the 82-row rule died.

── WHAT COUNTS AS LOADING, AND WHY MENTIONING IS NOT ENOUGH ───────────────
require('./X'), require('../X.js'), readFileSync(... 'X.js'), import from
'./X', spawn/exec of 'X.js', or a documented extraction that names the file.
A bare mention in a comment does NOT count: the whole point of the check is
that prose about a file is not coverage of it. That distinction is the finding
class, so accepting prose would make the tool vacuous against its own subject.

── WHAT THIS CANNOT SEE, STATED RATHER THAN IMPLIED ───────────────────────
* A test that loads X and asserts nothing about it still passes here. Loading
  is necessary, not sufficient. Gate 4 (a fault probe) is the check that asks
  whether an arm would go RED; this one only asks whether the subject is in
  the room.
* A test that covers X through a SHELL -- importing the dispatcher that calls
  X -- is reported, and that is a known false-positive class. It is printed
  with the others rather than guessed at, because "reached indirectly" and
  "not reached" cannot be told apart without following the call graph, and a
  tool that guessed would be the 82-row rule again.
* Tests NOT co-located with a source file are outside the population
  entirely. They are counted and printed as the denominator so a clean result
  cannot be read as "every citation was checked".
"""

import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

TEST_SUFFIXES = ('.test.js',)


def _rel(p):
    return os.path.relpath(p, REPO).replace('\\', '/')


def pairs():
    """[(source rel, test rel)] for every X.js with a sibling X.test.js."""
    out = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs
                   if d not in ('.git', 'node_modules', '__pycache__', 'vendor')]
        for f in files:
            for suf in TEST_SUFFIXES:
                if not f.endswith(suf):
                    continue
                src = os.path.join(root, f[:-len(suf)] + '.js')
                if os.path.isfile(src):
                    out.append((_rel(src), _rel(os.path.join(root, f))))
    return sorted(set(out))


def loads(test_rel, src_rel, root=None):
    """Does `test_rel` LOAD `src_rel`, as opposed to mentioning it?

    Comments are stripped FIRST. A file whose only reference to its subject is
    a comment is the exact finding this tool exists for, so counting comment
    text would make the check agree with itself.

    `root` exists so tests/run_citation_arm_depth_probe.py can drive this
    against synthetic fixtures. This repo answered 85 of 85 clean on the first
    run, and a brand-new detector that finds nothing is the one result worth
    least -- it is indistinguishable from a detector that cannot find
    anything. The fixtures settle which it is, in BOTH directions.
    """
    root = REPO if root is None else root
    try:
        s = io.open(os.path.join(root, test_rel), encoding='utf-8',
                    errors='replace').read()
    except OSError:
        return None  # COULD NOT TELL -- never folded into a verdict
    # Strip // line comments and /* */ blocks. Crude but one-directional: it
    # can only ever REMOVE evidence, so it cannot manufacture a pass.
    s = re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)
    s = re.sub(r'(?m)^\s*//.*$', ' ', s)
    s = re.sub(r'(?<![:"\'])//.*$', ' ', s, flags=re.M)

    base = os.path.basename(src_rel)            # portal.js
    stem = base[:-3]                            # portal
    pats = [
        r'require\s*\(\s*[\'"][^\'"]*' + re.escape(stem) + r'(?:\.js)?[\'"]',
        r'require\.resolve\s*\(\s*[\'"][^\'"]*' + re.escape(stem) + r'(?:\.js)?[\'"]',
        r'from\s+[\'"][^\'"]*' + re.escape(stem) + r'(?:\.js)?[\'"]',
        r'import\s*\(\s*[\'"][^\'"]*' + re.escape(stem) + r'(?:\.js)?[\'"]',
        # Read off disk, which is how the HTML-extracting suites work.
        re.escape(base),
    ]
    for p in pats:
        if re.search(p, s):
            return True
    return False


def analyse():
    rows = []
    for src, test in pairs():
        rows.append({'source': src, 'test': test, 'loads': loads(test, src)})
    return rows


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    rows = analyse()
    if not rows:
        sys.stderr.write('COULD NOT RUN -- no X.js / X.test.js pair found '
                         'anywhere in the repo. That is not a clean result; '
                         'the walk found nothing to measure.\n')
        return 2

    unreadable = [r for r in rows if r['loads'] is None]
    findings = [r for r in rows if r['loads'] is False]
    ok = [r for r in rows if r['loads'] is True]

    if '--json' in argv:
        print(json.dumps({'pairs': len(rows), 'loads': len(ok),
                          'does_not_load': len(findings),
                          'could_not_read': len(unreadable),
                          'findings': [r['test'] for r in findings]},
                         indent=2, sort_keys=True))
        return 1 if findings else 0

    print('CITED TEST / SUBJECT DEPTH -- does a co-located test LOAD its subject?')
    print('  co-located pairs found        %4d' % len(rows))
    print('  test loads its subject        %4d' % len(ok))
    print('  test does NOT load it         %4d' % len(findings))
    print('  could not read the test       %4d' % len(unreadable))
    print('')
    if unreadable:
        print('COULD NOT TELL -- these were not read and are in NEITHER count:')
        for r in unreadable:
            print('   %s' % r['test'])
        print('')
    if findings:
        print('FINDINGS -- the file exists, is named for its subject, and never')
        print('loads it. Each needs a judgement: either an arm that reaches the')
        print('subject, or a line saying what it really covers.')
        for r in findings:
            print('   %-52s does not load %s' % (r['test'], r['source']))
        print('')
    if '--list' in argv:
        print('CLEAN PAIRS:')
        for r in ok:
            print('   %-52s loads %s' % (r['test'], r['source']))
        print('')
    print('THIS IS NOT A COVERAGE FIGURE. Loading a subject is NECESSARY and not')
    print('sufficient -- a test that requires its module and asserts nothing')
    print('passes here. And co-located pairs are the only population checked:')
    print('every other citation in the repo is OUTSIDE this measurement, so a')
    print('clean run says nothing about them.')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
