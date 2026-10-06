#!/usr/bin/env python3
"""A CAP ON A RATIO THAT TURNS AN OVERRUN INTO COMPLETION -- or into a maximum.

    python tools/overrun_inversion_scan.py
    python tools/overrun_inversion_scan.py --json
    python tools/overrun_inversion_scan.py --selftest

Exit 0 CLEAN, 1 FOUND SOMETHING, 2 COULD NOT RUN. Never 0 for "could not tell".

── THE CLASS, AND IT IS NOT "A CAP IS BAD" ────────────────────────────────
Found 2026-09-27 in SAIRNbuild's WIP schedule:

    var pct = estTotal > 0 ? Math.min(1, costToDate / estTotal) : 0;
    var earned = Math.round(pct * revised);

A job that had spent 130% of its estimated cost reported 100% complete, so
`earned` became the WHOLE contract -- the largest figure the arithmetic can
produce -- and over/under billing swung to its most UNDER-billed reading. The
truth was the opposite: that job was losing money and was probably over-billed.

THE CAP DID NOT ROUND AN OVERRUN OFF. IT INVERTED THE FINDING. That is the
class, and it has three parts that all have to be present:

  1. a RATIO -- something divided by an estimate, budget, target or total;
  2. a CAP at the ratio's nominal maximum (Math.min(1, ...), Math.min(100, ...));
  3. the capped value FEEDING something else -- a money figure, a verdict, a
     status -- rather than only being displayed.

WITHOUT (3) A CAP IS USUALLY RIGHT. A progress BAR capped at 100% of its track
is correct: the bar is a picture, nothing is derived from it, and a 130%-wide
div is a layout bug. This scanner reports (1)+(2) and then asks about (3) in a
way it can be honest about, because (3) is a data-flow question a regex cannot
settle. So every hit is a READ REQUEST, ranked, never a verdict.

── WHY THE DIRECTION MATTERS MORE THAN THE CAP ────────────────────────────
Ask of every hit: WHEN THE INPUT EXCEEDS THE ESTIMATE, DOES THE OUTPUT MOVE
TOWARDS "FINE"? A cap that clamps a value towards the SAFE end is a defensive
clamp. A cap that clamps towards the REASSURING end is an inversion, because
exceeding an estimate is evidence the estimate was wrong, not evidence the work
is done. The two are the same three tokens and opposite defects.

── WHAT IT CANNOT SEE, PRINTED ON EVERY RUN ───────────────────────────────
See BLIND_SPOTS. The largest: it cannot follow the capped value to its
consumer, so it cannot tell a display clamp from a derived-money clamp. That is
the judgement each hit exists to prompt, and pretending otherwise would make
this a gate that refuses correct code.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# IMPORTED, NOT RE-DECLARED. A second copy of a bound is a second source of
# truth, and the one that drifts is always the copy nobody is looking at.
sys.path.insert(0, os.path.join(REPO, 'tools'))
from nhi_register import SPAWN_BOUND                           # noqa: E402
CRITERIA_VERSION = '2026-09-28.1'

# A ratio capped at its nominal maximum. The two spellings that exist on this
# platform, plus the clamp idiom. Deliberately NOT "any Math.min": a min
# against a constant that is not a ratio ceiling is ordinary arithmetic.
CAP_RE = re.compile(
    r'Math\.min\s*\(\s*(?P<ceil>1|1\.0|100|100\.0)\s*,(?P<rest>[^;\n]{0,160})'
    r'|Math\.min\s*\((?P<rest2>[^;\n]{0,160}?),\s*(?P<ceil2>1|1\.0|100|100\.0)\s*\)')

# The denominator words that make a ratio an ESTIMATE ratio. A cap on
# elapsed/duration is a different animal and is reported at a lower rank.
ESTIMATE = re.compile(
    r'budget|estimate|est[A-Z_]|forecast|eac|target|quota|allow|plan(?:ned)?'
    r'|capacity|expected|baseline|goal|limit|threshold', re.I)
PROGRESSY = re.compile(r'pct|percent|complete|progress|ratio|frac|share|util', re.I)
# A capped value that is then MULTIPLIED or assigned into something is far more
# likely to be feeding a derived figure than one that ends up in a style rule.
DISPLAYISH = re.compile(r'style|width|height|\.css|bar|gauge|meter|opacity|px', re.I)

BLIND_SPOTS = [
    'IT CANNOT FOLLOW THE CAPPED VALUE TO ITS CONSUMER. A cap feeding a CSS '
    'width is correct and a cap feeding earned revenue is the defect, and they '
    'are the same three tokens. Every hit is a read request, never a verdict.',
    'A cap written without Math.min is invisible -- `if (r > 1) r = 1;`, a '
    'clamp helper, or a ceiling applied in SQL or in a template. The scan '
    'reports what it matched and cannot report what it has no pattern for.',
    'It does not know whether the denominator is ever RE-FORECAST. SAIRNbuild '
    'had the cap AND a denominator that was the original budget; either alone '
    'is survivable and together they invert the finding.',
    'A cap at a value other than the ratio ceiling (0.95, 1.5) is not matched '
    'at all, and a deliberately-capped index can still hide an overrun.',
    'Minified or single-line-packed JavaScript defeats the 160-character '
    'window, so a hit can be truncated and read as a different expression.',
]


def tracked():
    try:
        # 120 -> SPAWN_BOUND, 2026-10-06. `git ls-files '*.js' '*.html'`
        # measured 0.056s worst over 20 samples under load. 120s was 2000x the
        # failure point: it would have reported a hung git as a slow pass for
        # two minutes. The floor and its justification are stated once, in
        # tools/nhi_register.py, rather than re-argued here.
        p = subprocess.run(['git', 'ls-files', '*.js', '*.html'], cwd=REPO,
                           capture_output=True, timeout=SPAWN_BOUND)
    except Exception:
        return None
    if p.returncode != 0:
        return None
    out = (p.stdout or b'').decode('utf-8', 'replace').split('\n')
    return [f.strip() for f in out
            if f.strip() and not f.strip().startswith(('archive/', 'node_modules/'))]


def rank(expr, line):
    """HIGH / MEDIUM / LOW -- how likely this cap feeds a derived figure.

    A RANK IS NOT A VERDICT. It orders the reading; it does not decide.
    """
    ctx = expr + ' ' + line
    if DISPLAYISH.search(ctx):
        return 'LOW'
    if ESTIMATE.search(ctx) and PROGRESSY.search(ctx):
        return 'HIGH'
    if ESTIMATE.search(ctx) or PROGRESSY.search(ctx):
        return 'MEDIUM'
    return 'LOW'


def scan():
    files = tracked()
    if files is None:
        return None
    rows = []
    for rel in files:
        try:
            body = io.open(os.path.join(REPO, rel), encoding='utf-8',
                           errors='replace').read()
        except OSError:
            continue
        for m in CAP_RE.finditer(body):
            rest = m.group('rest') or m.group('rest2') or ''
            ceil = m.group('ceil') or m.group('ceil2') or ''
            # A ratio needs a division. `Math.min(1, n)` over an integer count
            # is not this class and is the bulk of the false positives.
            if '/' not in rest:
                continue
            lineno = body.count('\n', 0, m.start()) + 1
            start = body.rfind('\n', 0, m.start()) + 1
            end = body.find('\n', m.end())
            line = body[start:end if end > 0 else len(body)].strip()
            rows.append({'file': rel, 'line': lineno, 'ceiling': ceil,
                         'expr': m.group(0).strip()[:120],
                         'context': line[:200],
                         'rank': rank(m.group(0), line)})
    return rows


def selftest():
    """Lock the criteria against synthetic sources before believing a real
    number. A classifier that has only run on real input has not been shown to
    discriminate -- three tools on this platform were wrong exactly that way."""
    out, bad = [], 0

    def arm(name, ok, detail=''):
        nonlocal bad
        out.append('  %s %s%s' % ('ok  ' if ok else 'FAIL', name,
                                  '' if ok else '\n       ' + str(detail)[:300]))
        if not ok:
            bad += 1

    def hits(src):
        got = []
        for m in CAP_RE.finditer(src):
            rest = m.group('rest') or m.group('rest2') or ''
            if '/' not in rest:
                continue
            got.append((m.group(0).strip(), rank(m.group(0), src)))
        return got

    # THE REAL DEFECT, verbatim from sairnbuild.html before the fix.
    real = 'var pct=estTotal>0?Math.min(1,costToDate/estTotal):0;'
    h = hits(real)
    arm('the SAIRNbuild defect is found', len(h) == 1, h)
    arm('...and ranks HIGH -- an estimate denominator under a progress name',
        h and h[0][1] == 'HIGH', h)

    # THE OTHER SPELLING: the ceiling second.
    arm('a ceiling written second is found too',
        len(hits('var p = Math.min(spent / budget, 1);')) == 1)

    # PERCENT RATHER THAN FRACTION.
    arm('a cap at 100 is found', len(hits('var p=Math.min(100, done/target*100);')) == 1)

    # ── THE FALSE POSITIVES THAT MUST NOT FIRE ────────────────────────────
    arm('a min over an integer COUNT is NOT a ratio and is not reported',
        hits('var n = Math.min(1, rows.length);') == [],
        'no division, so it is not this class at all')
    arm('a progress BAR width ranks LOW, not HIGH',
        hits("el.style.width = Math.min(100, done/total*100) + '%';")[0][1] == 'LOW',
        'a bar capped at its own track is CORRECT -- the bar is a picture and '
        'nothing is derived from it. Ranking that HIGH would bury the real '
        'hits under every progress indicator on the platform')
    arm('an unrelated Math.min is not reported',
        hits('var lo = Math.min(a, b);') == [])

    # ── THE BAR ARM ABOVE DOES NOT ACTUALLY TEST DISPLAYISH (2026-10-05) ───
    # dead_rule_sweep reported DISPLAYISH DEAD and the reason is worth more
    # than the fix: `done/total*100` matches NEITHER ESTIMATE NOR PROGRESSY, so
    # with DISPLAYISH neutralised that string falls through rank()'s final
    # `return 'LOW'` and the arm gets the same answer BY A DIFFERENT ROUTE. A
    # verdict two routes agree on is one route's worth of evidence, and the
    # route being tested is the one that is not there.
    #
    # This arm uses a source that would rank MEDIUM without DISPLAYISH --
    # `costToDate/estTotal` is an estimate denominator -- so the demotion is
    # the rule's and nothing else's. Measured: LOW with the rule, MEDIUM
    # without it.
    disp = 'el.style.width = Math.min(1, costToDate/estTotal)*100 + "px";'
    arm('DISPLAYISH demotes a cap that would otherwise rank MEDIUM -- an '
        'estimate denominator written into a style width is a PICTURE, and '
        'nothing is derived from a picture',
        hits(disp) and hits(disp)[0][1] == 'LOW', hits(disp))
    arm('...and the SAME expression outside a display context is NOT demoted, '
        'so the arm above is not satisfied by a rule that demotes everything',
        rank('Math.min(1, costToDate/estTotal)',
             'var pct = Math.min(1, costToDate/estTotal);') != 'LOW',
        rank('Math.min(1, costToDate/estTotal)',
             'var pct = Math.min(1, costToDate/estTotal);'))

    # ── THE CONTROL. Without it every arm above is satisfied by a scanner
    # that reports everything, or by one that reports nothing.
    arm('CONTROL -- the scanner DISCRIMINATES rather than answering one way',
        len(hits(real)) == 1 and hits('var lo = Math.min(a, b);') == [],
        'the same answer for a known defect and a known non-defect')

    live = scan()
    arm('the real scan runs over the tracked tree',
        live is not None and len(live) > 0,
        'the live scan produced %s rows -- with zero, a clean result would mean '
        'nothing' % (len(live) if live is not None else 'no'))
    return out, bad


def main(argv):
    if '--selftest' in argv:
        print('OVERRUN INVERSION SCAN -- selftest (criteria %s)' % CRITERIA_VERSION)
        o, bad = selftest()
        for line in o:
            print(line)
        print('  %s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
        return 1 if bad else 0

    rows = scan()
    if rows is None:
        print('COULD NOT RUN: git ls-files failed, so the file list is unknown '
              'and NOTHING was scanned. Zero findings here is not a clean '
              'sweep.', file=sys.stderr)
        return 2

    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION, 'rows': rows,
                          'blind_spots': BLIND_SPOTS}, indent=1))
        return 1 if any(r['rank'] != 'LOW' for r in rows) else 0

    order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    rows.sort(key=lambda r: (order[r['rank']], r['file'], r['line']))
    print('OVERRUN INVERSION SCAN -- a cap on a ratio that turns an overrun '
          'into completion')
    print('  criteria %s' % CRITERIA_VERSION)
    for k in ('HIGH', 'MEDIUM', 'LOW'):
        print('  %-6s %d' % (k, sum(1 for r in rows if r['rank'] == k)))
    print('')
    print('EVERY ROW IS A READ REQUEST, NOT A VERDICT. Ask one question of each:')
    print('  when the input EXCEEDS the estimate, does the output move towards')
    print('  "fine"? A cap clamping towards the SAFE end is defensive. A cap')
    print('  clamping towards the REASSURING end is an inversion, because')
    print('  exceeding an estimate is evidence the ESTIMATE was wrong.')
    for k in ('HIGH', 'MEDIUM', 'LOW'):
        sel = [r for r in rows if r['rank'] == k]
        if not sel:
            continue
        print('\n== %s (%d) ==' % (k, len(sel)))
        for r in sel:
            print('  %s:%d' % (r['file'], r['line']))
            print('      %s' % r['context'])
    print('')
    print('WHAT THIS CANNOT SEE:')
    for b in BLIND_SPOTS:
        print('  - %s' % b)
    return 1 if any(r['rank'] != 'LOW' for r in rows) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
