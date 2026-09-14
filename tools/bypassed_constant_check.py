#!/usr/bin/env python
"""bypassed_constant_check.py -- a rate constant that some call site ignores.

    python tools/bypassed_constant_check.py
    python tools/bypassed_constant_check.py --json

── THE DEFECT ─────────────────────────────────────────────────────────────
A file declares `var SB_TAX_FICA_RATE = 0.0765;`, with a comment explaining
what it is and why it matters -- and two call sites elsewhere in the same file
multiply by `0.0765` directly. The constant is not wrong and the call sites are
not wrong. What is wrong is that CHANGING THE RATE MOVES ONE AND NOT THE OTHERS,
and nothing says so.

Found 2026-09-14 in sairnbiz.html: the employer FICA rate, declared once with a
careful note distinguishing it from the employee half, bypassed at the
hiring-cost estimate and the payroll summary. The 2026-09-03 competitive-gap
audit reached the same conclusion from the product side -- *"a product that
needs a deploy to stay legal is a product that is quietly wrong between
deploys"* -- and the 2026-08-28 SAIRNsenior pass reached it from the regulatory
side. This is the mechanical half of a finding two independent passes already
made.

── WHY THIS SCANS THE APP HTML, WHICH NOTHING ELSE DOES ───────────────────
`tools/completeness_check.py` finds a rule declared and not applied everywhere,
and it walks `api/` ONLY. Every app's business logic -- tax rates, thresholds,
caps, weights -- lives in the app HTML, which is outside its reach. This is the
same question asked where the constants actually are.

── THE CRITERION WAS NARROWED ONCE, AND THE FIRST VERSION IS RECORDED ─────
The obvious rule -- "a declared constant whose VALUE appears again as a literal"
-- flagged **60 candidates across the platform and almost all were noise**:
`TRIAL_DAYS = 30` against 134 unrelated `30`s in stonedesk.html, `SD_CTX_MAX
_MEMORIES = 10` against 242 unrelated `10`s. A small integer occurs everywhere
for unrelated reasons and matching on the value alone cannot tell the difference.

NARROWED TO DISTINCTIVE VALUES ONLY: a decimal carrying three or more
significant digits. 0.0765 is not a number that turns up incidentally; 30 is.
That takes the platform from 60 candidates to **2, and both were the real one**.

**THE BLIND SPOT IS THEREFORE DELIBERATE AND IS NOT A GAP TO TUNE AWAY.** A
bypassed integer constant -- a cap, a day count, a limit -- is INVISIBLE to
this, and widening to catch it reintroduces 58 false positives. A checker that
cries wolf is one people stop reading, which costs more than the misses.

Exit 0 clean, 1 a finding, 2 could not run.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

# Three or more significant decimal digits. See the header for the measurement
# that produced this bound rather than a guess.
DECL = re.compile(r'\bvar\s+([A-Z][A-Z0-9_]{3,40})\s*=\s*(0\.\d{3,6})\s*;')


def scan(body):
    """(name, value, bypass_count) for every declared constant some literal
    bypasses, in one comment-stripped file body."""
    decls = DECL.findall(body)
    if not decls:
        return []
    # HOW MANY DECLARATIONS SHARE EACH VALUE. sairnbiz declares the employer and
    # employee FICA halves separately -- deliberately, they are different money
    # at the same percentage -- so each one SEES THE OTHER'S DECLARATION as a
    # literal. Subtracting the declaration count is what stops two correct
    # constants reporting each other forever, which the first version did.
    per_value = {}
    for _n, v in decls:
        per_value[v] = per_value.get(v, 0) + 1
    out = []
    for name, val in decls:
        total = len(re.findall(r'(?<![\w.])' + re.escape(val) + r'(?![\w.])', body))
        bypasses = total - per_value[val]
        if bypasses > 0:
            out.append((name, val, bypasses))
    return out


def main(argv):
    try:
        from jscomments import strip_comments
    except Exception as e:
        # A CHECK THAT DEPENDS ON ANOTHER TOOL MUST FAIL CLOSED WHEN IT IS
        # ABSENT -- PR 1.11. Without comment stripping these files are dense
        # with prose ABOUT the very numbers being searched for, and a run
        # without it is not a weaker check, it is a different one.
        print('COULD NOT RUN: tools/jscomments.py could not be imported (%s). '
              'Nothing was scanned. These files discuss their own rates in '
              'prose, so a scan without comment stripping would report findings '
              'that are sentences.' % type(e).__name__)
        return EXIT_COULD_NOT_RUN

    try:
        files = sorted(f for f in os.listdir(REPO) if f.endswith('.html'))
    except Exception as e:
        print('COULD NOT RUN: could not list %s (%s)' % (REPO, type(e).__name__))
        return EXIT_COULD_NOT_RUN
    if len(files) < 15:
        # A ZERO OR TINY LIST IS A BROKEN READER, not a platform with no apps,
        # and every loop below would report clean against it.
        print('COULD NOT RUN: found %d .html files in the repo root -- that is a '
              'broken reader, not a platform with no app pages.' % len(files))
        return EXIT_COULD_NOT_RUN

    findings, scanned, declared = [], 0, 0
    for f in files:
        try:
            src = io.open(os.path.join(REPO, f), encoding='utf-8',
                          errors='replace').read()
        except Exception:
            continue
        body = strip_comments(src)
        scanned += 1
        declared += len(DECL.findall(body))
        for name, val, n in scan(body):
            findings.append({'file': f, 'const': name, 'value': val, 'bypasses': n})

    if '--json' in argv:
        print(json.dumps({'files_scanned': scanned, 'constants_declared': declared,
                          'findings': findings}, indent=2))
        return EXIT_FINDING if findings else EXIT_CLEAN

    print('BYPASSED CONSTANT CHECK -- app HTML, distinctive decimals only')
    print('  files scanned            : %d' % scanned)
    print('  distinctive constants    : %d' % declared)
    print('  bypassed by a literal    : %d' % len(findings))
    print('')
    print('  SCOPE, STATED BECAUSE A CLEAN RUN MUST NOT READ AS MORE THAN IT IS:')
    print('  only DECIMALS with three or more significant digits. A bypassed')
    print('  INTEGER constant -- a cap, a day count, a limit -- is invisible to')
    print('  this and that is deliberate: widening to catch it took the platform')
    print('  from 2 findings to 60, 58 of them noise. See the header.')
    print('  It also scans the app HTML ONLY. api/ is completeness_check.py\'s.')
    if not findings:
        print('')
        print('  No declared decimal rate is bypassed by its own literal.')
        return EXIT_CLEAN
    print('')
    for r in findings:
        print('  %s  %s = %s' % (r['file'], r['const'], r['value']))
        print('    the literal %s appears %d more time(s) than there are'
              % (r['value'], r['bypasses']))
        print('    declarations of it. Changing the rate would move the')
        print('    declaration and leave those call sites quietly wrong.')
    return EXIT_FINDING


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
