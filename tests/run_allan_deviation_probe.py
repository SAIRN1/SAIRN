#!/usr/bin/env python
"""Control for tools/allan_deviation_check.py.

    python tests/run_allan_deviation_probe.py     (exit 0 pass, 1 fail)

THE ESTIMATOR IS THE RISK, NOT THE PLUMBING. An Allan deviation will produce a
plausible number for any series you hand it, and a plausible number is the one
nobody checks -- which is how this platform got a negative-binomial k of 0.87,
reading as heavy superspreading, out of pure chance.

So every arm here drives synthetic series whose ANSWER IS KNOWN, in both
directions, and the refusals get the same treatment as the verdicts: a test
that can only ever answer "indistinguishable" is not a test, and one that can
only ever refuse is not either.
"""
CONTROLS_FOR = ['allan_deviation_check.py']

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
import allan_deviation_check as A                                 # noqa: E402

FAILS, PASSES = [], [0]


def ok(label, cond, detail=''):
    if cond:
        PASSES[0] += 1
        print('  ok   %s' % label)
    else:
        FAILS.append(label)
        print('  FAIL %s\n       %s' % (label, str(detail)[:300]))


def series(kind, n=400, seed=20260917):
    rnd = random.Random(seed)
    if kind == 'white':
        return [10 + rnd.gauss(0, 3) for _ in range(n)]
    if kind == 'drift':
        return [10 + 0.20 * i + rnd.gauss(0, 3) for i in range(n)]
    if kind == 'walk':
        out, v = [], 10.0
        for _ in range(n):
            v += rnd.gauss(0, 1.0)
            out.append(v)
        return out
    raise ValueError(kind)


def slope_of(x, taus=(1, 2, 4, 8, 16, 32, 64)):
    pts = [p for p in A.overlapping_adev(x, list(taus))
           if p['rel_err'] <= A.MAX_RELATIVE_ERROR]
    return A.loglog_slope(pts), len(pts)


print('1. the estimator separates the three noise types it claims to')
_w, _nw = slope_of(series('white'))
_d, _nd = slope_of(series('drift'))
_r, _nr = slope_of(series('walk'))
ok('WHITE NOISE reads negative -- averaging still helps', _w is not None and _w < -0.30, _w)
ok('LINEAR DRIFT reads strongly positive', _d is not None and _d > 0.70, _d)
ok('RANDOM WALK reads positive but below drift',
   _r is not None and 0.20 < _r < 1.20, _r)
ok('...and the three are ORDERED, which a single threshold cannot fake',
   _w < _r < _d, (_w, _r, _d))

print('')
print('2. the verdict vocabulary follows the slope, not a mood')
ok('a white-noise slope classifies as WHITE NOISE', A.classify(_w)[0] == 'WHITE NOISE',
   A.classify(_w))
ok('a drift slope classifies as DRIFT', A.classify(_d)[0] == 'DRIFT', A.classify(_d))
ok('no slope at all is NO SLOPE, never a clean bill',
   A.classify(None)[0] == 'NO SLOPE')

print('')
print('3. THE REFUSALS, which are the reason this tool is worth having')
# UNDERPOWERED IS NOT "NO DRIFT". A short series must yield too few usable
# points to fit, rather than a confident number.
_s, _n = slope_of(series('drift', n=12), taus=(1, 2, 4, 8))
ok('a 12-bin series produces fewer than three usable tau points',
   _n < 3, 'usable=%d slope=%s' % (_n, _s))
# And the other direction: the SAME process at length IS answerable, so the arm
# above is about power and not about the tool having stopped working.
_s2, _n2 = slope_of(series('drift', n=400))
ok('...and the SAME process at 400 bins IS answerable', _n2 >= 3 and _s2 > 0.70,
   'usable=%d slope=%s' % (_n2, _s2))

# THE STATIONARITY REFUSAL. An onboarding ramp must be refused BEFORE a slope
# is fitted, because the slope would be true and about the wrong subject.
_ramp = [0] * 30 + [20] * 10
ok('a series whose mass is all at the end is caught as a ramp',
   A.ramp_share(_ramp) >= A.RAMP_SHARE, A.ramp_share(_ramp))
_flat = [5] * 40
ok('...and an EVEN series is not -- the rule is not just "recent data exists"',
   A.ramp_share(_flat) < A.RAMP_SHARE, A.ramp_share(_flat))

print('')
print('4. zeros are data')
# A day with no record is a measured zero. Dropping it turns a sparse series
# into a dense one that looks busy, which would change every number above.
_counts, _a, _b = A.daily_counts(['2026-01-01', '2026-01-05', '2026-01-05'])
ok('a gap between dated records becomes zeros, not a shorter series',
   _counts == [1, 0, 0, 0, 2], _counts)
ok('...and the window is reported from the real first and last date',
   (_a, _b) == ('2026-01-01', '2026-01-05'), (_a, _b))

print('')
print('5. TEETH -- the blind lock the tool runs on every invocation')
ok('the tool carries its own fixtures and they pass', not A.self_check(verbose=False))
# If self_check could never fail, arm 5 is decoration. Drive it against a
# deliberately broken slope function.
_real = A.loglog_slope
try:
    A.loglog_slope = lambda pts: -0.5
    ok('...and they FAIL when the estimator is broken, so the lock is real',
       len(A.self_check(verbose=False)) >= 2,
       'a constant estimator passed the blind lock')
finally:
    A.loglog_slope = _real

print('')
print('=' * 66)
print('%d passed, %d failed' % (PASSES[0], len(FAILS)))
for f in FAILS:
    print('  FAILED: %s' % f)
sys.exit(1 if FAILS else 0)
