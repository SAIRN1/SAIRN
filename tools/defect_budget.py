"""defect_budget.py -- which standing rule has bitten often enough to be next.

    python tools/defect_budget.py
    python tools/defect_budget.py --json
    python tools/defect_budget.py --budget 3

── WHY PER RULE AND NOT PER APP ──────────────────────────────────────────
Item 20 asked for a defect budget that changes what gets worked on. The obvious
entity is the app, and item 51 measured that it will not work: 11 apps, exactly
ONE with 10 or more records and it is `PLATFORM`, a catch-all holding 65% of
everything, and 9 of 11 with three or fewer. A budget on n=1 is that one value
wearing a decision.

**A per-app budget would also invert the incentive.** Discovery is not
saturating (docs/2026-09-14-ibnr-scoping.md: six days, ~490 substantive commits,
no downward trend), so the app somebody audited hardest looks WORST and the
untouched app looks clean. Budgeting on that would punish looking.

The standing RULE is the entity the data supports. Measured 2026-09-14 over 68
records: 1.1 has bitten 16 times, 1.5 fourteen, 1.11 seven, 1.2 and 1.3 six
each. **Two rules account for 30 of the bites.** A rule crosses apps and
sessions, so it is far less a measure of where somebody happened to look.

── WHAT "OVER BUDGET" MEANS, AND WHAT IT DOES NOT ────────────────────────
It means: this failure mode has recurred often enough that the NEXT occurrence
is predictable rather than incidental, so the next control built here should
target it.

IT DOES NOT BLOCK ANYTHING. Report-only, and it should stay that way -- a gate
on this number would reward not citing a rule, and `--rule not-citable` exists
precisely so a record can decline honestly.

── THE THRESHOLD IS STATED AND ITS SENSITIVITY IS PRINTED ────────────────
Default 5. Chosen because the measured distribution has a clear head and tail --
16, 14, 7, 6, 6, then 3, 2, 1, 1, 1, 1, 1 -- and 5 separates them. That is a
judgement about a distribution, not a derivation, so the run prints what the
answer would be at 3 and at 7 as well. A threshold whose sensitivity is hidden
is a threshold nobody can argue with.

── WHAT IT CANNOT SEE ────────────────────────────────────────────────────
  * The 9 `not-citable` records are bites nobody could attribute to a rule.
    They are counted in the denominator and named, never quietly dropped.
  * A rule you are LOOKING for is a rule you find. This is less
    effort-distorted than per-app, not undistorted.
  * `arguable` citations count the same as `clean` ones. Weighting them would
    need a confidence model nothing here has.
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join('docs', 'defect-density-register.json')
DEFAULT_BUDGET = 5


def load():
    p = os.path.join(REPO, REG.replace('/', os.sep))
    if not os.path.isfile(p):
        return None
    return json.load(io.open(p, encoding='utf-8'))


def tally(records):
    bites, arguable = {}, {}
    for r in records:
        for rid in (r.get('rules') or []):
            bites[rid] = bites.get(rid, 0) + 1
            if r.get('citation_confidence') == 'arguable':
                arguable[rid] = arguable.get(rid, 0) + 1
    return bites, arguable


def main(argv):
    doc = load()
    if doc is None:
        print('COULD NOT CHECK: %s is not in this clone. An empty tally would '
              'report every rule inside budget, which is the most reassuring '
              'possible way to know nothing. Not a pass.' % REG)
        return 2
    recs = doc.get('records') or []
    if not recs:
        print('COULD NOT CHECK: the register holds zero records. ZERO TARGETS '
              'IS NOT A CLEAN SWEEP.')
        return 2

    budget = DEFAULT_BUDGET
    if '--budget' in argv:
        i = argv.index('--budget')
        try:
            budget = int(argv[i + 1])
        except Exception:                                      # noqa: BLE001
            print('--budget takes an integer'); return 2

    bites, arguable = tally(recs)
    not_citable = [r for r in recs if r.get('citation_confidence') == 'not-citable']
    over = sorted([(n, rid) for rid, n in bites.items() if n >= budget], reverse=True)

    if '--json' in argv:
        print(json.dumps({'budget': budget, 'bites': bites,
                          'over_budget': [rid for _n, rid in over],
                          'not_citable': len(not_citable),
                          'records': len(recs)}, indent=1))
        return 0

    print('DEFECT BUDGET BY STANDING RULE -- report only, nothing is blocked')
    print('  records                     : %d' % len(recs))
    print('  distinct rules cited        : %d' % len(bites))
    print('  records citing NO rule      : %d   (not-citable, counted not dropped)'
          % len(not_citable))
    print('  budget                      : %d bites' % budget)
    print('')
    for n, rid in sorted([(n, r) for r, n in bites.items()], reverse=True):
        flag = '  <-- OVER BUDGET' if n >= budget else ''
        print('    %-8s %2d %s%s' % (rid, n, '#' * min(n, 30), flag))
    print('')
    if over:
        print('  OVER BUDGET, in priority order: %s'
              % ', '.join(rid for _n, rid in over))
        print('  These are the failure modes whose NEXT occurrence is')
        print('  predictable rather than incidental. The next control built here')
        print('  should target the top of this list.')
    else:
        print('  Nothing over budget at %d.' % budget)
    print('')
    # THE SENSITIVITY, PRINTED. A threshold nobody can argue with is a
    # threshold nobody will challenge when it is wrong.
    print('  SENSITIVITY -- how many rules are over budget at other thresholds:')
    for b in (3, 5, 7, 10):
        print('    at %-3d %d rule(s)' % (b, sum(1 for v in bites.values() if v >= b)))
    print('')
    print('  A HIGH COUNT IS NOT A BAD RULE. It is a rule this platform keeps')
    print('  breaking, which is the opposite -- the rule is right and the')
    print('  practice around it is not. And a rule you are LOOKING for is a rule')
    print('  you find, so this is less effort-distorted than per-app, not')
    print('  undistorted.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
