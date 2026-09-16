"""Control for tools/risk_event_tree.py (item 84).

Run: python tests/run_risk_event_tree_probe.py

The self-check exercises the tree on synthetic probabilities. This re-derives
the two numbers that matter A DIFFERENT WAY and checks the tool against them:
the worst-state probability by direct algebra rather than by enumerating
sixteen paths, and the range by dense sampling rather than by corner search.

THE CORNER SEARCH IS AN OPTIMISATION AND OPTIMISATIONS ARE WHERE A RANGE
QUIETLY NARROWS. It is exact only because the worst state is monotone in every
p_fail; if that ever stops being true the corners stop being the extremes and
the reported range would be too tight in the direction that flatters.
"""
import itertools
import os
import random
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import risk_event_tree as R                                      # noqa: E402

CONTROLS_FOR = ['risk_event_tree.py']

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


print('risk event tree control\n')

# ── 1. THE WORST STATE, BY ALGEBRA RATHER THAN BY ENUMERATION ──────────────
# P(worst) = p1 * p2 * p3 * p4 -- all four barriers fail. Derived here from the
# definition rather than from the tool's path walk, so a mis-assembled path
# would disagree.
rng = random.Random(84)
for _ in range(200):
    ps = [round(rng.random(), 4) for _ in range(4)]
    direct = ps[0] * ps[1] * ps[2] * ps[3]
    got = R.tree(ps).get(R.WORST, 0.0)
    if abs(direct - got) > 1e-12:
        check('the worst state equals p1*p2*p3*p4 for %s' % (ps,), False,
              '%r vs %r' % (direct, got))
        break
else:
    check('the worst state equals p1*p2*p3*p4 over 200 random vectors', True)

# And PREVENTED is 1 - p1*p2, which is the other half of the same claim.
for _ in range(50):
    ps = [round(rng.random(), 4) for _ in range(4)]
    if abs((1 - ps[0] * ps[1]) - R.tree(ps).get('PREVENTED', 0.0)) > 1e-12:
        check('PREVENTED equals 1 - p1*p2', False, ps)
        break
else:
    check('PREVENTED equals 1 - p1*p2, so the prevention branch is an OR', True)

# ── 2. THE RANGE, BY DENSE SAMPLING RATHER THAN BY CORNER SEARCH ───────────
lo, hi, _lv, _hv = R.worst_case_range(R.BARRIERS)
sampled_lo, sampled_hi = 1.0, 0.0
for _ in range(4000):
    ps = [rng.uniform(b['p_fail'][0], b['p_fail'][1]) for b in R.BARRIERS]
    p = R.tree(ps).get(R.WORST, 0.0)
    sampled_lo = min(sampled_lo, p)
    sampled_hi = max(sampled_hi, p)
check('no sampled point falls OUTSIDE the reported range -- the corner search '
      'is not narrowing it', lo - 1e-9 <= sampled_lo and sampled_hi <= hi + 1e-9,
      'reported %.6f-%.6f, sampled %.6f-%.6f' % (lo, hi, sampled_lo, sampled_hi))
check('...and the sampling gets CLOSE to both ends, so the range is not '
      'absurdly wide either', (sampled_lo - lo) < 0.02 and (hi - sampled_hi) < 0.02,
      'reported %.6f-%.6f, sampled %.6f-%.6f' % (lo, hi, sampled_lo, sampled_hi))
check('the range is a real interval, not a point dressed as one', hi > lo,
      (lo, hi))

# ── 3. MONOTONICITY, WHICH IS WHAT MAKES THE CORNER SEARCH LEGITIMATE ──────
# Checked per barrier rather than assumed. If this ever fails the range above
# is unsound and this probe is the only thing that would say so.
for i in range(4):
    base = [0.4, 0.4, 0.4, 0.4]
    up = list(base)
    up[i] = 0.9
    check('the worst state is monotone increasing in p_fail[%d]' % i,
          R.tree(up).get(R.WORST, 0.0) > R.tree(base).get(R.WORST, 0.0))

# ── 4. THE STABILITY VERDICT IS EARNED, NOT ASSERTED ───────────────────────
stable, orders = R.ranking_stable(R.BARRIERS)
check('the stability check enumerates real orderings', len(orders) >= 1, orders)
check('...and its verdict agrees with the number of orders it found',
      stable == (len(orders) == 1), (stable, len(orders)))
# Both directions: a tree whose bands are all identical must rank stably.
flat = [dict(b, p_fail=(0.5, 0.5)) for b in R.BARRIERS]
st2, o2 = R.ranking_stable(flat)
check('a tree with no uncertainty ranks STABLY -- the check can say yes',
      st2 and len(o2) == 1, o2)

# ── 5. THE DECLARED TREE IS THE ONE THE ITEMS DESCRIBE ─────────────────────
items = sorted(b['item'] for b in R.BARRIERS)
check('the four barriers are exactly items 6, 19, 35 and 65',
      items == ['item 19', 'item 35', 'item 6', 'item 65'], items)
check('each barrier names what was MEASURED separately from the judgement',
      all(b.get('measured') and b.get('basis') for b in R.BARRIERS))
check('the widest band belongs to the barrier whose evidence was never run',
      max(R.BARRIERS, key=lambda b: b['p_fail'][1] - b['p_fail'][0])['item']
      == 'item 65',
      [(b['item'], round(b['p_fail'][1] - b['p_fail'][0], 2)) for b in R.BARRIERS])

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
