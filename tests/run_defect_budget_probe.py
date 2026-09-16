"""Does defect_budget rank the right rules, and does it refuse when it cannot look?

    python tests/run_defect_budget_probe.py

The arm that earns its place first is 2c: changing the threshold must change the
answer. A budget tool whose output is the same at 3 and at 10 is not applying a
budget, and on day one -- when one rule dominates -- that is easy to miss.
"""
# REQUIREMENT: the defect-density ranking is per RULE and not per app, because a
#   per-app budget punishes looking and the app audited hardest would score
#   worst
#
import contextlib
import io as _io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
os.chdir(REPO)

import defect_budget as db   # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('  ok   ' if cond else '  FAIL ') + name
          + (('\n        ' + str(detail)[:260]) if (detail and not cond) else ''))


def run(records, argv=()):
    real = db.load
    db.load = lambda: {'records': records}
    buf = _io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = db.main(list(argv))
    finally:
        db.load = real
    return rc, buf.getvalue()


def rec(rules, conf='clean'):
    return {'rules': rules, 'citation_confidence': conf, 'commit': 'x'}


print('--- 1. it tallies bites per rule ---')
rows = [rec(['1.1'])] * 6 + [rec(['1.5'])] * 2 + [rec(['9.9'])]
rc, out = run(rows)
check('1a  it runs', rc == 0, rc)
check('1b  the busiest rule is over budget at the default', 'OVER BUDGET' in out, out)
check('1c  ...and it is 1.1, not the rule with two bites',
      '1.1, ' in out or 'order: 1.1' in out, out)
check('1d  a rule with one bite is listed but NOT over budget',
      '9.9' in out and 'order: 1.1' in out and '9.9,' not in out.split('order:')[-1], out)

print('\n--- 2. the threshold actually does something ---')
rc, a = run(rows, ['--budget', '2'])
rc, b = run(rows, ['--budget', '10'])
check('2a  a low budget catches more', a.count('OVER BUDGET') >= b.count('OVER BUDGET'), (a, b))
check('2b  a budget above every count catches nothing',
      'Nothing over budget at 10' in b, b)
check('2c  CONTROL: the two thresholds gave DIFFERENT answers, so 2b is not '
      'passing because the tool never reports anything',
      ('OVER BUDGET' in a) and ('Nothing over budget' in b), (a[-200:], b[-200:]))

print('\n--- 3. it publishes its own sensitivity ---')
rc, out = run(rows)
check('3a  the run prints what other thresholds would say -- a threshold whose '
      'sensitivity is hidden is one nobody can argue with',
      'SENSITIVITY' in out and 'at 3' in out and 'at 10' in out, out)

print('\n--- 4. not-citable records are counted, never dropped ---')
rc, out = run(rows + [rec([], 'not-citable')] * 4)
check('4a  the not-citable count is reported', 'not-citable' in out, out)
check('4b  ...and it is the real number', 'NO rule      : 4' in out.replace('  ', ' ')
      or ': 4 ' in out, out)

print('\n--- 5. it refuses rather than reporting everything inside budget ---')
real = db.load
db.load = lambda: None
buf = _io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = db.main([])
db.load = real
check('5a  a missing register exits 2 -- an empty tally would report every rule '
      'inside budget, the most reassuring way to know nothing', rc == 2, rc)
check('5b  and says so', 'know nothing' in buf.getvalue(), buf.getvalue())

rc, out = run([])
check('5c  zero records exits 2, because zero targets is not a clean sweep',
      rc == 2, rc)

rc, out = run(rows, ['--budget', 'lots'])
check('5d  a non-integer budget is refused rather than defaulted', rc == 2, rc)

print('\n--- 6. it refuses to be read as blame ---')
rc, out = run(rows)
check('6a  the output says a high count is not a bad RULE',
      'not a bad rule' in out.lower(), out)
check('6b  ...and names the effort distortion it cannot remove',
      'effort-distorted' in out, out)

print('\n%d passed, %d failed' % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
