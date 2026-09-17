#!/usr/bin/env python
"""allan_deviation_check.py -- is the trend DRIFT, or is it noise?

    python tools/allan_deviation_check.py
    python tools/allan_deviation_check.py --self-check

Exit 0 the question was answered / 1 real drift found / 2 could not answer.

── WHY A RATE AND A COUNT CANNOT ANSWER THIS ───────────────────────────────
"Defects per day went from 4 to 63" is a pair of numbers, and a pair of numbers
cannot tell a process that is DRIFTING from one that is NOISY around a constant
mean. Both produce a rising-looking line over a short window; only one of them
means anything is changing.

**ALLAN DEVIATION IS THE INSTRUMENT FOR EXACTLY THIS QUESTION** and it is not
invented here: it is the standard two-sample deviation from frequency metrology
(David Allan, 1966), used because the ordinary standard deviation DOES NOT
CONVERGE for the noise types that contain drift -- you can take more data and
watch the number keep growing, which is the property that makes a flat standard
deviation reassuring and wrong.

Read it by the SLOPE of ADEV against averaging interval tau on log-log axes:

    slope ~= -0.5   white noise        averaging helps; nothing is drifting
    slope ~=  0     flicker noise      averaging stops helping
    slope ~= +0.5   random walk        the process wanders; a mean is not a fact
    slope ~= +1.0   linear drift       there is a real trend

── THE REFUSALS, WHICH ARE THE POINT ───────────────────────────────────────
This platform's own item 59 is the cautionary case: a Gini of 0.971 was read as
evidence of clustering when at that rate it was evidence of SPARSENESS, and a
negative-binomial k of 0.87 -- heavy superspreading -- came out of pure chance
because the expression explodes when variance approaches the mean. So:

  * **UNDERPOWERED IS NOT "NO DRIFT".** The relative uncertainty of an ADEV
    point is about 1/sqrt(2*(N/tau - 1)). With few bins the number is real and
    means nothing, and a test that can only ever answer "indistinguishable" is
    not a test. Points past the power limit are DROPPED and SAID, not plotted.

  * **A NON-STATIONARY SERIES IS REFUSED BEFORE IT IS MEASURED.** If most of
    the mass sits at one end of the window, the dominant signal is when
    RECORDING started, not when defects happened. Allan deviation would
    faithfully measure the onboarding ramp and report drift -- a true number
    about the wrong subject, which is the shape item 59 walked into.

  * **THE VERDICT NAMES ITS SUBJECT.** Drift in a defect REGISTER is drift in
    what got recorded. Whether that tracks defects requires an assumption this
    tool does not make and says so.
"""
import io
import json
import math
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXIT_ANSWERED, EXIT_DRIFT, EXIT_COULD_NOT = 0, 1, 2

# An ADEV point whose relative uncertainty exceeds this is not reported. 0.35 is
# loose on purpose: the aim is to drop the points that cannot mean anything, not
# to demand metrology-grade confidence from a defect log.
MAX_RELATIVE_ERROR = 0.35
# If this share of the total lands in the last quarter of the window, the series
# is an adoption ramp and the slope would describe that rather than defects.
RAMP_SHARE = 0.60


def daily_counts(dates, start=None, end=None):
    """A dense day-by-day series. ZEROS ARE DATA -- a day with no record is a
    measured zero, and dropping it is what turns a sparse series into a dense
    one that looks busy."""
    ds = sorted(d[:10] for d in dates if d)
    if not ds:
        return [], None, None
    import datetime
    a = datetime.date.fromisoformat(start or ds[0])
    b = datetime.date.fromisoformat(end or ds[-1])
    n = (b - a).days + 1
    if n <= 0:
        return [], None, None
    counts = [0] * n
    for d in ds:
        i = (datetime.date.fromisoformat(d) - a).days
        if 0 <= i < n:
            counts[i] += 1
    return counts, a.isoformat(), b.isoformat()


def overlapping_adev(x, taus):
    """Overlapping Allan deviation of a series of per-bin RATES.

    Overlapping rather than non-overlapping because it uses every available
    pair at each tau, which is the difference between a usable number and a
    decorative one on a series this short.
    """
    n = len(x)
    out = []
    for tau in taus:
        if tau < 1 or n < 3 * tau:
            continue
        # Cluster averages at this tau, one per starting offset.
        avgs = [sum(x[i:i + tau]) / float(tau) for i in range(0, n - tau + 1)]
        diffs = [avgs[i + tau] - avgs[i] for i in range(0, len(avgs) - tau)]
        if len(diffs) < 2:
            continue
        var = sum(d * d for d in diffs) / (2.0 * len(diffs))
        m = float(n) / tau
        rel = 1.0 / math.sqrt(2.0 * (m - 1.0)) if m > 1.0 else float('inf')
        out.append({'tau': tau, 'adev': math.sqrt(var), 'pairs': len(diffs),
                    'rel_err': rel})
    return out


def loglog_slope(points):
    """Least-squares slope of log(adev) against log(tau), fitted on the UPPER
    half of the tau range.

    ── THE BLIND LOCK CAUGHT THIS BEFORE IT TOUCHED REAL DATA ──────────────
    The first version fitted every point and reported +0.27 for a fixture that
    is a textbook linear drift -- which would have been read as "flicker, no
    direction" on a series that is unambiguously drifting.

    IT WAS NOT A BUG IN THE ARITHMETIC. A real series carries MORE THAN ONE
    NOISE TYPE, and they dominate in different places: white noise owns the
    short taus (slope -0.5) and drift owns the long ones (slope +1). A single
    least-squares line through both measures the CROSSOVER, which is a number
    about the mixture and not about either process. The noise type a reader
    cares about -- does this keep getting worse -- lives in the asymptote.

    So the fit uses the upper half of the usable taus, with a floor of three
    points. This is the standard reading of an Allan plot and not a tuning
    knob: it is where the question is asked, not a threshold chosen to make an
    answer come out.
    """
    usable = [p for p in points if p['adev'] > 0 and p['tau'] > 0]
    if len(usable) < 3:
        return None
    usable.sort(key=lambda p: p['tau'])
    half = usable[len(usable) // 2:] if len(usable) >= 6 else usable
    if len(half) < 3:
        half = usable[-3:]
    pts = [(math.log(p['tau']), math.log(p['adev'])) for p in half]
    if len(pts) < 3:
        return None
    n = len(pts)
    sx = sum(a for a, _ in pts)
    sy = sum(b for _, b in pts)
    sxx = sum(a * a for a, _ in pts)
    sxy = sum(a * b for a, b in pts)
    den = n * sxx - sx * sx
    if abs(den) < 1e-12:
        return None
    return (n * sxy - sx * sy) / den


# The vocabulary is taken from the noise-type slopes above rather than from a
# threshold somebody picked. A slope between the named ones is reported as
# BETWEEN, not rounded to whichever is nearer.
def classify(slope):
    if slope is None:
        return 'NO SLOPE', 'fewer than three usable tau points'
    if slope <= -0.35:
        return 'WHITE NOISE', ('averaging keeps helping -- this is scatter '
                               'around a constant mean, not a trend')
    if slope < 0.20:
        return 'FLICKER', ('averaging has stopped helping; there is structure '
                           'but not a direction')
    if slope < 0.75:
        return 'RANDOM WALK', ('the process wanders -- a mean over this window '
                               'is not a fact about the next one')
    return 'DRIFT', 'there is a real, directional trend'


def ramp_share(counts):
    if not counts or sum(counts) == 0:
        return 0.0
    q = max(1, len(counts) // 4)
    return sum(counts[-q:]) / float(sum(counts))


def analyse(label, counts, span):
    print('')
    print('== %s ==' % label)
    if not counts:
        print('  COULD NOT ANSWER: no dated records at all.')
        return EXIT_COULD_NOT, None
    total = sum(counts)
    print('  window      : %s -> %s (%d daily bins, %d records)'
          % (span[0], span[1], len(counts), total))
    print('  mean/day    : %.3f' % (total / float(len(counts))))
    share = ramp_share(counts)
    print('  last quarter: %.0f%% of all records' % (share * 100))

    if share >= RAMP_SHARE:
        print('')
        print('  REFUSED -- NOT A STATIONARY SERIES, so the slope would not be')
        print('  about defects. %.0f%% of every record in this window lands in its'
              % (share * 100))
        print('  final quarter. That is the shape of a register being ADOPTED,')
        print('  and Allan deviation would faithfully measure the onboarding')
        print('  ramp and call it drift -- a true number about the wrong')
        print('  subject, which is precisely the trap item 59 walked into with')
        print('  a Gini of 0.971.')
        print('')
        print('  WHAT WOULD ANSWER IT: the same computation over a window that')
        print('  starts AFTER the ramp, once that window is long enough to')
        print('  carry three or more tau points inside the power limit. On this')
        print('  data that is not yet true, and saying so is the answer.')
        return EXIT_COULD_NOT, None

    rates = [float(c) for c in counts]
    taus = [1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32]
    pts = overlapping_adev(rates, taus)
    usable = [p for p in pts if p['rel_err'] <= MAX_RELATIVE_ERROR]
    dropped = [p for p in pts if p['rel_err'] > MAX_RELATIVE_ERROR]

    print('')
    print('  tau(d)   ADEV     pairs   rel.err')
    for p in pts:
        print('  %5d   %7.4f  %5d   %5.2f%s'
              % (p['tau'], p['adev'], p['pairs'], p['rel_err'],
                 '   DROPPED (underpowered)' if p['rel_err'] > MAX_RELATIVE_ERROR else ''))
    if dropped:
        print('  %d point(s) dropped. UNDERPOWERED IS NOT "NO DRIFT" -- those'
              % len(dropped))
        print('  numbers are real and cannot mean anything at this record count.')

    if len(usable) < 3:
        print('')
        print('  COULD NOT ANSWER: %d usable tau point(s), fewer than the three'
              % len(usable))
        print('  a slope needs. A test that can only ever answer')
        print('  "indistinguishable" is not a test, so this is exit 2 and never')
        print('  a clean bill.')
        return EXIT_COULD_NOT, None

    slope = loglog_slope(usable)
    verdict, why = classify(slope)
    print('')
    print('  log-log slope over %d usable point(s): %+0.2f' % (len(usable), slope))
    print('  VERDICT: %s -- %s' % (verdict, why))
    print('')
    print('  AND WHAT IT IS ABOUT: this is the rate of RECORDING. Drift here is')
    print('  drift in what got written down. Whether that tracks the rate of')
    print('  defects needs an assumption this tool does not make.')
    return (EXIT_DRIFT if verdict in ('RANDOM WALK', 'DRIFT') else EXIT_ANSWERED), slope


# ── THE BLIND LOCK: synthetic series whose ANSWER IS KNOWN ────────────────
# Locked before the tool ever ran on real data, in both directions, because a
# statistic that comes out plausible on real input is the one nobody checks.
def self_check(verbose=True):
    import random
    bad = []
    rnd = random.Random(20260917)
    n = 400
    white = [max(0.0, 10 + rnd.gauss(0, 3)) for _ in range(n)]
    drift = [10 + 0.20 * i + rnd.gauss(0, 3) for i in range(n)]
    walk, v = [], 10.0
    for _ in range(n):
        v += rnd.gauss(0, 1.0)
        walk.append(v)
    cases = [('white noise -> negative slope', white, lambda s: s < -0.30),
             ('linear drift -> strongly positive', drift, lambda s: s > 0.70),
             ('random walk -> positive but under drift', walk,
              lambda s: 0.20 < s < 1.20)]
    for label, series, want in cases:
        pts = [p for p in overlapping_adev(series, [1, 2, 4, 8, 16, 32, 64])
               if p['rel_err'] <= MAX_RELATIVE_ERROR]
        sl = loglog_slope(pts)
        ok = sl is not None and want(sl)
        if verbose:
            print('  %-4s %-42s slope=%s'
                  % ('ok' if ok else 'FAIL', label,
                     '%+0.2f' % sl if sl is not None else 'None'))
        if not ok:
            bad.append(label)
    # AND THE OTHER DIRECTION ON THE POWER RULE: a short series must produce
    # NO usable points, not a confident slope.
    short = white[:12]
    pts = [p for p in overlapping_adev(short, [1, 2, 4, 8])
           if p['rel_err'] <= MAX_RELATIVE_ERROR]
    ok = len(pts) < 3
    if verbose:
        print('  %-4s %-42s usable=%d'
              % ('ok' if ok else 'FAIL', 'a 12-point series is underpowered', len(pts)))
    if not ok:
        bad.append('short series produced a slope')
    return bad


def main(argv):
    print('THE BLIND LOCK -- synthetic series whose answer is known, both ways')
    bad = self_check()
    if bad:
        print('\nCOULD NOT RUN: the estimator failed its own fixtures (%s).'
              % ', '.join(bad))
        return EXIT_COULD_NOT
    if '--self-check' in argv:
        print('\nself-check clean.')
        return EXIT_ANSWERED

    worst = EXIT_ANSWERED
    reg = os.path.join(REPO, 'docs', 'defect-density-register.json')
    try:
        recs = json.load(io.open(reg, encoding='utf-8'))['records']
    except Exception as e:                                         # noqa: BLE001
        print('\nCOULD NOT ANSWER: %s unreadable -- %s' % (reg, e))
        return EXIT_COULD_NOT
    counts, a, b = daily_counts([r.get('date') for r in recs])
    rc, _ = analyse('defect register -- records per day', counts, (a, b))
    worst = max(worst, rc)

    # The accepted-risk register, same question about a different series.
    ar = os.path.join(REPO, 'docs', 'ACCEPTED-RISKS.md')
    if os.path.isfile(ar):
        import re
        src = io.open(ar, encoding='utf-8', errors='replace').read()
        dates = re.findall(r'(20\d\d-\d\d-\d\d)', src)
        counts2, a2, b2 = daily_counts(dates)
        rc2, _ = analyse('accepted risks -- dated entries per day',
                         counts2, (a2, b2))
        worst = max(worst, rc2)
    else:
        print('\n== accepted risks ==\n  COULD NOT ANSWER: %s is absent.' % ar)
        worst = max(worst, EXIT_COULD_NOT)
    return worst


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
