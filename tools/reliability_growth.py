"""Item 80 -- software reliability growth models, and the admissibility gate
that decides whether this platform's data may be fitted at all.

    python tools/reliability_growth.py            # the series, the gate, the verdict
    python tools/reliability_growth.py --fixtures # the blind lock alone
    python tools/reliability_growth.py --json

── WHAT AN SRGM CLAIMS, AND WHAT IT NEEDS TO BE ALLOWED TO CLAIM IT ────────
A reliability growth model fits cumulative defects against time and extrapolates
the remaining population: Goel-Okumoto m(t) = a(1 - e^-bt), Musa-Okumoto
m(t) = a ln(1 + bt). The `a` it returns is the headline -- "there are about this
many defects left".

THAT NUMBER IS ONLY MEANINGFUL IF THE DISCOVERY RATE IS FALLING. Every growth
model assumes a DEPLETING population: finding defects removes them, so the find
rate declines, and the curve bends. Fit one to a flat series and it will still
return an `a` -- a large, confident, meaningless one, because the curve has no
knee to locate. A model that cannot refuse is a number generator.

── SO THE GATE IS THE DELIVERABLE, AND IT IS DECLARED FIRST ────────────────
Three criteria, fixed below before the real series was read, each refusing with
the measured value rather than a verdict:

  ENOUGH INTERVALS    fewer than MIN_INTERVALS and two parameters cannot be
                      identified. Any pair of (a, b) fits six points.
  A FALLING RATE      the normalised find rate must trend DOWN. This is the
                      model's core assumption, not a preference.
  EFFORT RECORDED     the find rate tracks EFFORT as much as population. Flat
                      under RISING effort means depletion; flat under FLAT
                      effort means a deep reserve -- and the two are opposite
                      conclusions from the same series. Without effort, neither
                      can be claimed.

── THE MODELS ARE IMPLEMENTED AND PROVEN BEFORE THE REFUSAL ────────────────
Both fitters are locked against SYNTHETIC series generated from KNOWN
parameters and required to recover them. That matters more than it looks: a
refusal from a tool that has never been shown to work is indistinguishable from
a broken tool. The fixtures make the refusal a statement about the DATA.

── WHAT THIS IS NOT ────────────────────────────────────────────────────────
Not an IBNR reserve. `docs/2026-09-14-ibnr-scoping.md` asks how many defects
exist and have not been found; this asks whether the found-over-time curve may
be extrapolated at all. They share a series and answer different questions, and
this one's honest answer today is NO with a reason.
"""
import json
import math
import os
import subprocess
import sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO, 'docs', 'defect-density-register.json')

# ── THE ADMISSIBILITY CRITERIA, DECIDED BEFORE THE REAL SERIES WAS READ ────
# Written as constants so moving one is a visible act rather than a quiet
# adjustment to make the data qualify.
MIN_INTERVALS = 15        # two free parameters need far more than a handful
FALLING_TREND_AT = -0.30  # rank correlation of rate against time must be at least this negative
EFFORT_RECORDED = False   # nothing on this platform records ATTENTION per interval
# A RATE NEEDS A DENOMINATOR BIG ENOUGH TO BE A RATE. A day with three
# substantive commits and no defect yields 0.0 per 100 and is an artefact of
# where the window was cut, not a measurement. Same discipline as
# tools/benford_check.py's TOO FEW VALUES refusal, and the excluded intervals
# are NAMED on every run rather than silently dropped.
MIN_DENOMINATOR = 10


def series():
    """Defects per day from the register, and substantive commits per day from
    git, derived live rather than copied out of the scoping document -- a second
    hand-maintained copy of a series is one that drifts.

    SUBSTANTIVE excludes `chore(claims)`, which is pure coordination churn and
    was measured at 49% of all commits. Using total commits as the denominator
    would halve the rate and flatter the result.
    """
    recs = json.load(open(REGISTER, encoding='utf-8'))['records']
    defects = Counter(r['date'] for r in recs)
    out = subprocess.run(['git', 'log', '--since=2026-09-08', '--date=short',
                          '--format=%ad|%s'], capture_output=True, text=True, encoding='utf-8', errors='replace',
                         cwd=REPO).stdout
    commits, subst = Counter(), Counter()
    for line in (out or '').strip().split(chr(10)):
        if '|' not in line:
            continue
        day, subj = line.split('|', 1)
        commits[day] += 1
        if not subj.startswith('chore(claims)'):
            subst[day] += 1
    days = sorted(set(list(defects) + [d for d in subst if subst[d]]))
    rows = []
    for i, d in enumerate(days):
        s = subst.get(d, 0)
        rows.append({'date': d, 't': i + 1, 'defects': defects.get(d, 0),
                     'commits': commits.get(d, 0), 'substantive': s,
                     'rate_per_100': (100.0 * defects.get(d, 0) / s) if s else None})
    return rows


def rank_corr(xs, ys):
    """Spearman rank correlation. Stdlib only -- no numpy in this repo, and a
    dependency for one statistic would be its own SOUP entry."""
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return (num / den) if den else 0.0


def _fit(model, ts, cum, a_min):
    """Coarse-to-fine grid search on (a, b) minimising squared error.

    DETERMINISTIC ON PURPOSE. A fitter seeded from the clock or from a random
    start would give a different answer on the same input, and this platform has
    already quarantined one checker for exactly that -- a verdict that changes
    while nothing does.

    `a_min` IS PER MODEL AND IS NOT A TUNING KNOB. The first version clamped
    `a >= max(cum)` for both, which is CORRECT for Goel-Okumoto -- there `a` is
    the asymptote m(inf), so it cannot be below anything already observed -- and
    WRONG for Musa-Okumoto, which is unbounded: its `a` is a rate scale, not a
    ceiling. On a synthetic curve with a=40 the clamp forced a >= 110.9 and the
    fitter returned a=110.9 with SSE 3497 against a true SSE of 0. The blind
    lock caught it before the real series was ever read, which is the entire
    reason the lock generates from KNOWN parameters rather than eyeballing a
    plot. Same constraint copied across two models with different semantics --
    the shape docs/2026-09-13-cross-domain-disciplines.md names as
    byte-identical is not safe-in-context.
    """
    best = None
    a_lo, a_hi = a_min, max(max(cum) * 20 + 10, a_min * 20 + 10)
    b_lo, b_hi = 1e-4, 2.0
    for _ in range(6):
        for i in range(40):
            a = a_lo + (a_hi - a_lo) * i / 39.0
            for j in range(40):
                b = b_lo + (b_hi - b_lo) * j / 39.0
                sse = sum((model(a, b, t) - c) ** 2 for t, c in zip(ts, cum))
                if best is None or sse < best[0]:
                    best = (sse, a, b)
        _, a, b = best
        aw, bw = (a_hi - a_lo) / 8.0, (b_hi - b_lo) / 8.0
        a_lo, a_hi = max(a_min, a - aw), a + aw
        b_lo, b_hi = max(1e-5, b - bw), b + bw
    return {'a': best[1], 'b': best[2], 'sse': best[0]}


def goel_okumoto(ts, cum):
    # `a` IS THE ASYMPTOTE here -- m(inf) = a -- so it cannot be below anything
    # already observed.
    return _fit(lambda a, b, t: a * (1 - math.exp(-b * t)), ts, cum, max(cum))


def musa_okumoto(ts, cum):
    # `a` IS A RATE SCALE here, not a ceiling: a*ln(1+bt) is unbounded, so the
    # observed maximum constrains it not at all. See _fit's docstring for what
    # assuming otherwise did.
    return _fit(lambda a, b, t: a * math.log(1 + b * t), ts, cum, 1e-3)


def admissible(rows):
    """The gate. Returns (ok, [problems]) -- each problem carrying its number."""
    problems = []
    n = len(rows)
    if n < MIN_INTERVALS:
        problems.append('TOO FEW INTERVALS: %d, bar is %d. Two free parameters cannot '
                        'be identified from this many points -- some (a, b) fits any '
                        'short series exactly, and the fit says nothing.'
                        % (n, MIN_INTERVALS))
    rated = [r for r in rows
             if r['rate_per_100'] is not None and r['substantive'] >= MIN_DENOMINATOR]
    if len(rated) < 3:
        problems.append('NO USABLE RATE SERIES: %d interval(s) have a denominator.'
                        % len(rated))
        rho = None
    else:
        rho = rank_corr([r['t'] for r in rated], [r['rate_per_100'] for r in rated])
        if rho > FALLING_TREND_AT:
            problems.append('THE FIND RATE IS NOT FALLING: rank correlation against time '
                            'is %+.2f, bar is %+.2f. Every growth model assumes a '
                            'DEPLETING population -- finding defects removes them, so the '
                            'rate declines and the curve bends. Fitted to a flat series '
                            'the model still returns a large confident `a`, because there '
                            'is no knee to locate.' % (rho, FALLING_TREND_AT))
    if not EFFORT_RECORDED:
        problems.append('EFFORT IS NOT RECORDED, and this one is not a threshold. The '
                        'find rate tracks ATTENTION as much as population: flat under '
                        'RISING effort means depletion, flat under FLAT effort means a '
                        'deep reserve, and those are OPPOSITE conclusions from the same '
                        'series. Commit count is a proxy for activity and a poor one for '
                        'attention.')
    return (not problems), problems, rho


# ── THE BLIND LOCK ────────────────────────────────────────────────────────
# The fitters are proven against SYNTHETIC series generated from KNOWN
# parameters before the real one is read, and the gate is proven to refuse a
# long-but-flat series and to ADMIT a long falling one.
#
# The second half is the part that matters. A gate that refuses everything is
# indistinguishable from a gate that works, and a refusal from a fitter nobody
# has seen succeed is indistinguishable from a broken fitter. Both directions
# are locked here, so today's refusal is a statement about THE DATA.
def _synthetic_go(a, b, n):
    return [a * (1 - math.exp(-b * t)) for t in range(1, n + 1)]


def _synthetic_mo(a, b, n):
    return [a * math.log(1 + b * t) for t in range(1, n + 1)]


def run_fixtures():
    bad = []

    # 1. The fitters recover parameters they were given.
    ts = list(range(1, 31))
    for label, gen, fit, a, b in (
            ('Goel-Okumoto recovers a from its own curve', _synthetic_go, goel_okumoto, 200.0, 0.12),
            ('Musa-Okumoto recovers a from its own curve', _synthetic_mo, musa_okumoto, 40.0, 0.5)):
        got = fit(ts, gen(a, b, 30))
        if abs(got['a'] - a) / a > 0.15:
            bad.append((label, a, round(got['a'], 1)))

    # 2. CONTROL on the fitter: it must NOT return the same `a` for a different
    #    curve, or arm 1 passes on a function that ignores its input.
    lo = goel_okumoto(ts, _synthetic_go(200.0, 0.12, 30))['a']
    hi = goel_okumoto(ts, _synthetic_go(600.0, 0.12, 30))['a']
    if abs(hi - lo) / lo < 0.5:
        bad.append(('CONTROL: a bigger population fits a bigger `a`', 'different',
                    '%.0f vs %.0f' % (lo, hi)))

    # 3. The gate ADMITS a long, falling, effort-recorded series.
    # A REALISTIC DENOMINATOR, because MIN_DENOMINATOR is part of the gate: a
    # fixture built on a denominator the gate would reject tests nothing.
    falling = [{'t': i, 'rate_per_100': 40.0 / i, 'defects': 1, 'substantive': 100,
                'date': 'd%02d' % i} for i in range(1, 26)]
    global EFFORT_RECORDED
    saved = EFFORT_RECORDED
    try:
        EFFORT_RECORDED = True
        ok, probs, rho = admissible(falling)
        if not ok:
            bad.append(('CONTROL: a long FALLING series is ADMITTED -- a gate that '
                        'refuses everything is not a gate', True, probs))
        # 4. ...and REFUSES the same length when the rate is flat.
        flat = [{'t': i, 'rate_per_100': 12.0 + (3 if i % 2 else -3), 'defects': 1,
                 'substantive': 100, 'date': 'd%02d' % i} for i in range(1, 26)]
        ok2, probs2, _ = admissible(flat)
        if ok2 or not any('NOT FALLING' in p for p in probs2):
            bad.append(('a long but FLAT series is refused for the right reason',
                        'NOT FALLING', probs2))
        # 5. ...and refuses a SHORT falling one, naming the length.
        ok3, probs3, _ = admissible(falling[:6])
        if ok3 or not any('TOO FEW INTERVALS' in p for p in probs3):
            bad.append(('a SHORT falling series is refused for the right reason',
                        'TOO FEW INTERVALS', probs3))
    finally:
        EFFORT_RECORDED = saved

    # 6. The effort criterion is not a threshold and fires on its own.
    ok4, probs4, _ = admissible(falling)
    if not any('EFFORT IS NOT RECORDED' in p for p in probs4):
        bad.append(('the effort criterion fires while effort is unrecorded', True, probs4))
    return bad


def main(argv):
    # UNDER --json THE BANNER GOES TO STDERR. A consumer piping this to jq must
    # receive JSON and nothing else -- the probe caught exactly that, failing to
    # parse its own tool's output. The blind-lock result is NOT suppressed, only
    # redirected: a lock whose verdict is invisible is a lock nobody ran.
    out = sys.stderr if '--json' in argv else sys.stdout

    def say(*a):
        print(*a, file=out)

    bad = run_fixtures()
    say('RELIABILITY GROWTH -- item 80')
    if bad:
        print('  !! THE MODELS OR THE GATE FAILED THEIR OWN FIXTURES. NOTHING WAS FITTED.')
        for row in bad:
            print('     %s -- wanted %r, got %r' % row)
        return 2
    say('  blind lock: both fitters recover parameters from their own curves, the')
    say('              gate ADMITS a long falling series and REFUSES a long flat one')
    say('              and a short falling one. Run before the real series was read.')
    if '--fixtures' in argv:
        return 0

    rows = series()
    ok, problems, rho = admissible(rows)

    if '--json' in argv:
        print(json.dumps({'series': rows, 'admissible': ok, 'problems': problems,
                          'rate_trend_rank_corr': rho,
                          'fit': None,
                          'fit_note': 'not fitted -- see problems'}, indent=2, sort_keys=True))
        return 0

    print()
    say('  THE SERIES, derived live from docs/defect-density-register.json and git,')
    say('  not copied from docs/2026-09-14-ibnr-scoping.md -- a second hand-kept copy')
    say('  of a series is one that drifts.')
    print()
    say('  %-12s %8s %9s %12s %10s' % ('date', 'defects', 'commits', 'substantive',
                                         'per 100'))
    for r in rows:
        print('  %-12s %8d %9d %12d %10s'
              % (r['date'], r['defects'], r['commits'], r['substantive'],
                 ('%.1f' % r['rate_per_100']) if r['rate_per_100'] is not None else '--'))
    print()
    thin = [r['date'] for r in rows
            if r['rate_per_100'] is not None and r['substantive'] < MIN_DENOMINATOR]
    if thin:
        print('  EXCLUDED FROM THE RATE TREND (denominator under %d substantive '
              'commits, so' % MIN_DENOMINATOR)
        print('  the rate is an artefact of where the window was cut): %s'
              % ', '.join(thin))
    if rho is not None:
        print('  RATE TREND: rank correlation against time %+.2f (bar %+.2f to fit).'
              % (rho, FALLING_TREND_AT))
        print('  THE SIGN IS THE POINT, NOT THE SIZE. On %d intervals a rank '
              'correlation is weak' % len([r for r in rows
                                           if r['rate_per_100'] is not None
                                           and r['substantive'] >= MIN_DENOMINATOR]))
        print('  evidence for any direction -- what it is NOT is negative, and a growth')
        print('  model needs negative. Flat and rising fail identically here.')
    if ok:
        cum, run = [], 0
        for r in rows:
            run += r['defects']
            cum.append(run)
        ts = [r['t'] for r in rows]
        go, mo = goel_okumoto(ts, cum), musa_okumoto(ts, cum)
        print('  ADMISSIBLE. Goel-Okumoto a=%.0f b=%.3f | Musa-Okumoto a=%.0f b=%.3f'
              % (go['a'], go['b'], mo['a'], mo['b']))
        print('  TWO MODELS ARE REPORTED, NOT ONE. Where they disagree the spread IS')
        print('  the uncertainty; a single figure would hide it.')
        return 0

    say('  NOT ADMISSIBLE -- the series is not fitted, and this is a refusal with')
    say('  reasons rather than a model with a caveat:')
    for p in problems:
        print('     - %s' % p)
    print()
    say('  WHAT WOULD CHANGE THE ANSWER, in the order it would arrive:')
    say('   1. TIME. The interval count rises on its own; nothing has to be built.')
    say('   2. A FALLING RATE. This one cannot be arranged -- it is the thing being')
    say('      measured, and arranging it would be the analysis choosing its answer.')
    say('   3. EFFORT PER INTERVAL. The only one that is a BUILD: something that')
    say('      records attention rather than activity. Commit count is not it.')
    print()
    say('  Until then the honest statement is the one docs/2026-09-14-ibnr-scoping.md')
    say('  already reaches from the same series: discovery is NOT saturating, which is')
    say('  a DIRECTION and not a size. This tool exists so that the day the data')
    say('  qualifies, the fit is a command rather than a project -- and so that until')
    say('  then nobody fits it anyway.')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
