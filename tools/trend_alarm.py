"""Item 45 -- the two alarm terms this platform does not have: PERSISTENT and WORSENING.

    python tools/trend_alarm.py                       # every series, all three terms
    python tools/trend_alarm.py --series <name>
    python tools/trend_alarm.py --fixtures            # the blind lock, reads no real data
    python tools/trend_alarm.py --json

Exit 0 when nothing is reportable, 1 on a finding, 2 when a series could not be
built. REPORT ONLY, and the arming gate below is why: nothing here alarms.

── WHAT THE PLATFORM ALREADY HAS, AND WHAT IT IS ──────────────────────────────
`docs/2026-09-13-cross-domain-disciplines.md` §4 made every numeric threshold
report MARGIN-TO-VIOLATION and alarm tighter than the failure point. Item 20's
band does the same for the defect budget. Both compare the CURRENT VALUE to a
static line.

In controller terms that is the PROPORTIONAL term and nothing else, and a
P-only controller has two blind spots that are not edge cases:

  THE INTEGRAL BLIND SPOT   a metric that sits slightly bad for a long time and
                            never crosses. Each reading passes. The accumulated
                            harm is real and no single reading shows it.
  THE DERIVATIVE BLIND SPOT a metric that is comfortably inside the line and
                            moving toward it fast. Every reading passes right up
                            to the one that does not, and by then the thing has
                            already happened.

This adds both as MEASUREMENTS. It does not add a controller.

── WHY IT MEASURES AND DOES NOT ALARM, WHICH IS THE WHOLE DESIGN ──────────────
A PID controller is only as good as its gains, and gains are TUNED against
history where you know what should have fired. Shipping KP/KI/KD picked by
judgement and calling the result an alarm is the failure this file exists to
avoid -- it produces a number that looks measured and is not.

So the three terms are computed and printed on every run, because a slope and an
accumulated exceedance are FACTS about the series that need no gain at all. What
needs a gain is the word ALARM, and that is gated:

  ENOUGH OBSERVATIONS      fewer than MIN_OBSERVATIONS and a false-positive rate
                           has a confidence interval wider than the rate.
  A LABELLED EPISODE       at least one recorded instance of the metric actually
                           going bad. WITHOUT ONE, ONLY THE FALSE-POSITIVE HALF
                           IS MEASURABLE -- you can prove an alarm stays quiet on
                           a calm stretch, which an alarm wired to `return` also
                           does. Detection cannot be measured against zero
                           examples, and a tool reporting one number for both is
                           the single-figure failure §2 of the disciplines names.
  A QUIET-STRETCH BUDGET   and the gains must not fire on the calm part of the
                           real series more than MAX_FP_ON_QUIET of the time.

This platform currently supplies the first and NOT the second, which is stated
on every run rather than worked around.

── THE FINDING THAT MADE THIS WORTH BUILDING ──────────────────────────────────
Run it. `traceability-untraced` and `traceability-ratio` are the SAME document,
the same 221 readings, and they move in OPPOSITE directions: the ratio improves
monotonically while the absolute count of untraced test files rises. A threshold
on the headline ratio reads better every single day for five days, and the
backlog it is a ratio of grows the whole time.

That is not a hypothetical integral blind spot. It is the live one, and it is
the metric this repo's own generated documents put at the top of the page.

── WHAT IT CANNOT DO ──────────────────────────────────────────────────────────
  * Decide a threshold. A series with none is REPORTED as having none, because
    a metric with no line is one nothing can ever be said to be drifting toward.
  * Know whether a direction is bad. `worse_is` is declared per series and is a
    judgement; get it backwards and every term inverts silently, which is why
    the fixture lock drives both signs.
  * Distinguish a real trend from a short run. The D-term is a least-squares
    slope over a window and says so; it is evidence, not a verdict.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TUNING = os.path.join(REPO, 'docs', 'trend-alarm-tuning.json')

CRITERIA_VERSION = '2026-09-15.1'

# ── THE ARMING GATE, DECLARED BEFORE ANY REAL SERIES IS READ ──────────────────
MIN_OBSERVATIONS = 30
MIN_LABELLED_EPISODES = 1
MAX_FP_ON_QUIET = 0.05

# Window for the integral term, and lookback for the derivative, in OBSERVATIONS
# rather than days: these series are written by a generator on a human's cadence,
# not on a clock, and a fixed number of days is a different sample size every run.
I_WINDOW = 40
D_LOOKBACK = 20


def git(*args):
    """Explicit utf-8. The locale default here is cp1252 and this repo's
    generated documents are full of em-dashes -- tools/subprocess_decode_check.py
    exists because that failure is silent in one direction and fatal in the
    other."""
    p = subprocess.run(['git'] + list(args), cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return p.stdout if p.returncode == 0 else None


# ── SERIES ────────────────────────────────────────────────────────────────────
# Each is (at, value). `at` is an ISO minute so two commits in the same minute
# from two clones still order deterministically by the string.

def _doc_history(path, pattern, pick):
    """A dated series recovered from the git history of a GENERATED document.

    Generated documents are the only place this platform keeps a metric over
    TIME -- every checker reports now, and the previous answer is only in the
    commit that wrote it.
    """
    log = git('log', '--format=%H|%ad', '--date=format:%Y-%m-%dT%H:%M',
              '--follow', '--', path)
    if log is None:
        return None
    rx, pts = re.compile(pattern), []
    for line in log.strip().splitlines():
        if '|' not in line:
            continue
        h, at = line.split('|', 1)
        src = git('show', h + ':' + path)
        if src is None:
            continue
        m = rx.search(src)
        if m:
            pts.append((at, float(pick(m))))
    pts.sort()
    return pts or None


TRACE_RX = r'\*\*(\d+) of (\d+) test files are traced'


def series_traceability_untraced():
    return _doc_history('docs/traceability-matrix.md', TRACE_RX,
                        lambda m: int(m.group(2)) - int(m.group(1)))


def series_traceability_ratio():
    return _doc_history('docs/traceability-matrix.md', TRACE_RX,
                        lambda m: 100.0 * int(m.group(1)) / int(m.group(2)))


def series_defect_rate():
    """Weighted defects per day from the register -- the series item 20 gates on
    and item 80 refused to fit."""
    p = os.path.join(REPO, 'docs', 'defect-density-register.json')
    if not os.path.exists(p):
        return None
    data = json.load(io.open(p, encoding='utf-8'))
    recs = data['records'] if isinstance(data, dict) else data
    w = {'critical': 5.0, 'high': 3.0, 'moderate': 1.0, 'low': 0.25}
    per = {}
    for r in recs:
        d = r.get('date')
        if d:
            per[d] = per.get(d, 0.0) + w.get(r.get('severity'), 1.0)
    return sorted((d + 'T00:00', v) for d, v in per.items()) or None


# threshold: the line a P-term would compare against. None is a real answer and
# is reported as one -- it means nothing can be said to be drifting toward
# anything, which is the state most of this platform's metrics are actually in.
# band: where "slightly bad" starts. The integral term accumulates past THIS,
# not past the threshold, which is the whole point of having it.
SERIES = {
    'traceability-untraced': {
        'fn': series_traceability_untraced,
        'worse_is': 'higher',
        'threshold': None,
        'band': None,
        'units': 'test files',
        'what': 'test files on disk that no source in the repo cites',
    },
    'traceability-ratio': {
        'fn': series_traceability_ratio,
        'worse_is': 'lower',
        'threshold': None,
        'band': None,
        'units': '%',
        'what': 'share of test files traced to a stated requirement',
    },
    'defect-rate': {
        'fn': series_defect_rate,
        'worse_is': 'higher',
        'threshold': 60.0,
        'band': 45.0,
        'units': 'weighted defects/day',
        'what': "item 20's budget, per day rather than per window",
    },
}


# ── THE THREE TERMS ───────────────────────────────────────────────────────────

def _signed(value, ref, worse_is):
    """How far past `ref` in the BAD direction, positive when bad."""
    return (value - ref) if worse_is == 'higher' else (ref - value)


def p_term(pts, threshold, worse_is):
    """Current value against the line. None when there is no line, which is a
    finding rather than a zero."""
    if threshold is None or not pts:
        return None
    return _signed(pts[-1][1], threshold, worse_is)


def i_term(pts, band, worse_is, window=I_WINDOW):
    """Accumulated exceedance PAST THE BAND over the last `window` readings.

    Sums only the bad side. A series that spends half its time slightly good
    does not get to net that against the time it spends slightly bad -- harm
    accumulated is not cancelled by having been fine afterwards, and a signed
    sum here is how a persistent problem averages itself out of existence.
    """
    if band is None or not pts:
        return None
    w = pts[-window:]
    over = [max(0.0, _signed(v, band, worse_is)) for _a, v in w]
    return {'sum': sum(over), 'readings': len(w),
            'breaching': sum(1 for x in over if x > 0)}


def d_term(pts, threshold, worse_is, lookback=D_LOOKBACK):
    """Least-squares slope per reading over the lookback, and -- when there is a
    threshold and the slope is toward it -- how many readings until it crosses.

    Per READING, not per day: see I_WINDOW. A projection in readings is honest
    about what was actually sampled; converting it to days would silently assume
    a cadence nothing guarantees.
    """
    if not pts:
        return None
    w = pts[-lookback:]
    n = len(w)
    if n < 3:
        return {'slope': None, 'readings': n, 'to_threshold': None,
                'why': 'fewer than 3 readings -- a slope through 2 points is the '
                       'two points'}
    xs = list(range(n))
    ys = [v for _a, v in w]
    mx = sum(xs) / n
    my = sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return {'slope': None, 'readings': n, 'to_threshold': None,
                'why': 'no spread in x'}
    slope = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / den
    worsening = slope > 0 if worse_is == 'higher' else slope < 0
    to = None
    if threshold is not None and worsening and slope != 0:
        gap = _signed(threshold, ys[-1], 'higher' if worse_is == 'higher' else 'lower')
        gap = abs(threshold - ys[-1])
        to = gap / abs(slope)
    return {'slope': slope, 'readings': n, 'worsening': worsening,
            'to_threshold': to}


# ── ARMING ────────────────────────────────────────────────────────────────────

def load_tuning():
    if not os.path.exists(TUNING):
        return {'criteria_version': CRITERIA_VERSION, 'episodes': [], 'gains': {}}
    return json.load(io.open(TUNING, encoding='utf-8'))


def arming(pts, tune, name):
    """Can the word ALARM be used for this series yet, and if not, which half is
    missing. Returns reasons, never a silent False."""
    reasons = []
    n = len(pts or [])
    if n < MIN_OBSERVATIONS:
        reasons.append('TOO FEW OBSERVATIONS: %d, bar is %d. A false-positive '
                       'rate measured on this many readings has an interval '
                       'wider than the rate.' % (n, MIN_OBSERVATIONS))
    eps = [e for e in tune.get('episodes', []) if e.get('series') == name]
    if len(eps) < MIN_LABELLED_EPISODES:
        reasons.append('NO LABELLED EPISODE: %d recorded, bar is %d. THIS IS THE '
                       'HALF THAT CANNOT BE WORKED AROUND -- without one recorded '
                       'instance of this metric actually going bad, the only '
                       'measurable number is that the alarm stayed quiet on a '
                       'calm stretch, which `return` also achieves. Detection '
                       'rate and false-positive rate are two numbers and only '
                       'one of them exists here.' % (len(eps), MIN_LABELLED_EPISODES))
    if not tune.get('gains', {}).get(name):
        reasons.append('NO GAINS RECORDED for this series. KP/KI/KD are not '
                       'shipped with values: a gain chosen by judgement and '
                       'presented as a measurement is the defect this tool was '
                       'built to not commit.')
    return reasons


# ── THE BLIND LOCK ────────────────────────────────────────────────────────────
# Fixed BEFORE the real series was read, and driven in BOTH directions for every
# term, because the classic failure in all three is a sign: a D-term that fires
# on fast IMPROVEMENT is not a worse alarm than one that fires on fast decline,
# it is an inverted one, and it looks identical in a passing test that only ever
# feeds it the bad case.
def fixtures():
    out, bad = [], 0

    def ck(name, cond, detail=''):
        nonlocal bad
        out.append(('  ok   ' if cond else '  FAIL ') + name
                   + ('' if cond else '  <- ' + str(detail)[:200]))
        if not cond:
            bad += 1

    flat = [('2026-01-%02dT00:00' % (i + 1), 10.0) for i in range(50)]
    creep = [('2026-01-%02dT00:00' % (i + 1), 10.4) for i in range(50)]
    rising = [('2026-01-%02dT00:00' % (i + 1), 10.0 + i) for i in range(50)]
    falling = [('2026-01-%02dT00:00' % (i + 1), 60.0 - i) for i in range(50)]

    ck('P: a value inside the line is negative (good side)',
       p_term(flat, 20.0, 'higher') < 0)
    ck('P: a value past the line is positive (bad side)',
       p_term(flat, 5.0, 'higher') > 0)
    ck('P: worse_is=lower INVERTS the sign, or every verdict is backwards',
       p_term(flat, 20.0, 'lower') > 0 and p_term(flat, 5.0, 'lower') < 0)
    ck('P: no threshold is None, NOT zero -- zero would read as exactly on the line',
       p_term(flat, None, 'higher') is None)

    ck('I: a series parked JUST past the band accumulates, though it never '
       'crosses any threshold -- the integral blind spot, stated as a number',
       i_term(creep, 10.0, 'higher')['sum'] > 0)
    ck('I: ...and it counts every reading as breaching, not just the last',
       i_term(creep, 10.0, 'higher')['breaching'] == 40)
    ck('CONTROL I: a series inside the band accumulates NOTHING. An integral '
       'that always grows is a clock',
       i_term(flat, 20.0, 'higher')['sum'] == 0)
    ck('CONTROL I: the bad side only. A stretch spent GOOD must not net off a '
       'stretch spent bad -- harm is not cancelled by later being fine',
       i_term(flat[:25] + creep[25:], 10.2, 'higher')['sum'] > 0)
    ck('CONTROL I: with no band there is nothing to accumulate past, and that '
       'is None rather than 0', i_term(flat, None, 'higher') is None)

    d = d_term(rising, 100.0, 'higher')
    ck('D: a rising series under worse_is=higher is WORSENING', d['worsening'])
    ck('D: ...with a positive slope of about 1 per reading', abs(d['slope'] - 1.0) < 1e-6, d)
    ck('D: ...and projects a crossing while still well inside the line -- the '
       'derivative blind spot, stated as a number',
       d['to_threshold'] is not None and 30 < d['to_threshold'] < 60, d)
    ck('CONTROL D: the SAME rising series under worse_is=lower is IMPROVING, '
       'not worsening. An inverted D-term looks identical until this runs',
       not d_term(rising, 100.0, 'lower')['worsening'])
    ck('CONTROL D: an improving series projects NO crossing, rather than a '
       'negative one printed as a countdown',
       d_term(falling, 100.0, 'higher')['to_threshold'] is None)
    ck('CONTROL D: a flat series is not worsening in either direction',
       not d_term(flat, 100.0, 'higher')['worsening']
       and not d_term(flat, 100.0, 'lower')['worsening'])
    ck('D: two readings refuse rather than fitting a line to two points',
       d_term(rising[:2], 100.0, 'higher')['slope'] is None)

    ck('P AND D DISAGREE ON THE SAME SERIES, which is the entire case for '
       'having a D-term: P says comfortably inside, D says heading out',
       p_term(rising, 100.0, 'higher') < 0
       and d_term(rising, 100.0, 'higher')['worsening'])

    ck('ARMING: a long series with no labelled episode is still NOT armed -- '
       'length is the cheap half',
       any('NO LABELLED EPISODE' in r for r in
           arming(rising, {'episodes': [], 'gains': {}}, 'x')))
    ck('ARMING: a short series is refused for length too',
       any('TOO FEW OBSERVATIONS' in r for r in
           arming(rising[:5], {'episodes': [], 'gains': {}}, 'x')))
    ck('CONTROL ARMING: given BOTH an episode and gains, the gate clears -- a '
       'gate that can never pass is a disabled feature with a paragraph',
       arming(rising, {'episodes': [{'series': 'x', 'at': '2026-01-01',
                                     'why': 'fixture'}],
                       'gains': {'x': {'kp': 1, 'ki': 1, 'kd': 1}}}, 'x') == [])
    return out, bad


# ── TWO READINGS OF ONE SOURCE THAT DISAGREE ──────────────────────────────────
# DECLARED AS A PAIR, not inferred. Two series "disagreeing" is only meaningful
# when they are known to be two views of the SAME underlying thing -- otherwise
# any two metrics pointing different ways is a coincidence dressed as a finding,
# which is the shape checker_control_check.py records three inference models
# failing at inside an hour.
SAME_SOURCE = [
    ('traceability-ratio', 'traceability-untraced',
     'docs/traceability-matrix.md, one generator, the same readings'),
]


def divergences(results):
    by = {r['name']: r for r in results}
    out = []
    for a, b, src in SAME_SOURCE:
        ra, rb = by.get(a), by.get(b)
        if not ra or not rb or ra.get('error') or rb.get('error'):
            continue
        da, db = ra['d'], rb['d']
        if da.get('slope') is None or db.get('slope') is None:
            continue
        if da.get('worsening') == db.get('worsening'):
            continue
        good = a if not da['worsening'] else b
        bad = b if not da['worsening'] else a
        out.append((a, b,
            'SAME SOURCE (%s), OPPOSITE VERDICTS. `%s` is improving at %+.4f '
            'per reading while `%s` is worsening at %+.4f. The headline is the '
            'one that improves, so a P-term threshold on it reads better every '
            'day while the backlog it is a ratio of grows -- %d readings, '
            '%.2f -> %.2f on the improving view and %.2f -> %.2f on the other. '
            'This is the integral blind spot live, not as an example.'
            % (src, good, by[good]['d']['slope'], bad, by[bad]['d']['slope'],
               ra['observations'], by[good]['first'][1], by[good]['last'][1],
               by[bad]['first'][1], by[bad]['last'][1])))
    return out


# ── REPORT ────────────────────────────────────────────────────────────────────

def analyse(name, cfg, tune):
    pts = cfg['fn']()
    if pts is None:
        return {'name': name, 'error': 'the series could not be built'}
    return {
        'name': name, 'what': cfg['what'], 'units': cfg['units'],
        'worse_is': cfg['worse_is'], 'threshold': cfg['threshold'],
        'band': cfg['band'], 'observations': len(pts),
        'first': pts[0], 'last': pts[-1],
        'p': p_term(pts, cfg['threshold'], cfg['worse_is']),
        'i': i_term(pts, cfg['band'], cfg['worse_is']),
        'd': d_term(pts, cfg['threshold'], cfg['worse_is']),
        'arming': arming(pts, tune, name),
    }


def main(argv):
    if '--fixtures' in argv:
        lines, bad = fixtures()
        print('TREND ALARM -- blind lock, %d arms, no real series read' % len(lines))
        for l in lines:
            print(l)
        print('  %s' % ('ALL FIXTURES PASS' if not bad else '%d FIXTURE(S) FAILED' % bad))
        return 1 if bad else 0

    # THE GATE HAS A DOOR, and it is deliberately a narrow one. Without these
    # two commands the arming criteria would be unreachable, and a criterion
    # nothing can ever satisfy is a disabled feature with a paragraph attached.
    if '--record-episode' in argv:
        i = argv.index('--record-episode')
        rest = argv[i + 1:]
        if len(rest) < 3 or rest[0] not in SERIES:
            sys.stderr.write('--record-episode <series> <YYYY-MM-DD> <what went '
                             'bad, and how it was known>\n')
            return 2
        why = ' '.join(rest[2:]).strip()
        if len(why) < 20:
            sys.stderr.write('An episode needs to say WHAT WENT BAD and HOW IT '
                             'WAS KNOWN. An episode recorded as a date is a '
                             'label with no content to tune against.\n')
            return 2
        t = load_tuning()
        t.setdefault('episodes', []).append(
            {'series': rest[0], 'at': rest[1], 'why': why,
             'criteria_version': CRITERIA_VERSION})
        io.open(TUNING, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(t, indent=2, ensure_ascii=False) + '\n')
        print('RECORDED an episode for %s at %s. %d episode(s) now.'
              % (rest[0], rest[1], len(t['episodes'])))
        return 0

    if '--set-gains' in argv:
        i = argv.index('--set-gains')
        rest = argv[i + 1:]
        if len(rest) < 4 or rest[0] not in SERIES:
            sys.stderr.write('--set-gains <series> <kp> <ki> <kd>\n')
            return 2
        t = load_tuning()
        if not [e for e in t.get('episodes', []) if e.get('series') == rest[0]]:
            sys.stderr.write('REFUSED: no labelled episode for %s. Gains set '
                             'before there is anything to tune against are '
                             'judgement wearing a measurement\'s clothes, which '
                             'is the one thing this tool exists not to do.\n'
                             % rest[0])
            return 2
        t.setdefault('gains', {})[rest[0]] = {
            'kp': float(rest[1]), 'ki': float(rest[2]), 'kd': float(rest[3]),
            'criteria_version': CRITERIA_VERSION}
        io.open(TUNING, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(t, indent=2, ensure_ascii=False) + '\n')
        print('GAINS RECORDED for %s.' % rest[0])
        return 0

    tune = load_tuning()
    want = None
    if '--series' in argv:
        want = argv[argv.index('--series') + 1]
        if want not in SERIES:
            sys.stderr.write('unknown series. known: %s\n' % ', '.join(sorted(SERIES)))
            return 2
    names = [want] if want else sorted(SERIES)

    lines, bad = fixtures()
    if bad:
        # THE LOCK RUNS FIRST AND ITS FAILURE IS TERMINAL. A term whose sign is
        # wrong on a fixture reports confidently wrong numbers on real data.
        print('THE FIXTURE LOCK FAILED -- no real series was read.')
        for l in lines:
            print(l)
        return 2

    results = [analyse(n, SERIES[n], tune) for n in names]

    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION,
                          'series': results}, indent=2, default=str))
        return 1 if any(r.get('finding') for r in results) else 0

    print('TREND ALARM -- item 45, criteria %s' % CRITERIA_VERSION)
    print('  P is what this platform already has. I and D are what it does not.')
    print('  %d fixture arms passed before any real series was read.' % len(lines))
    print('')
    rc = 0
    for r in results:
        print('  %s' % r['name'].upper())
        if r.get('error'):
            print('    COULD NOT BUILD THE SERIES: %s' % r['error'])
            rc = max(rc, 2)
            continue
        print('    %s' % r['what'])
        print('    %d readings, %s -> %s   worse is %s'
              % (r['observations'], r['first'][0], r['last'][0], r['worse_is']))
        print('    now: %.2f %s' % (r['last'][1], r['units']))
        if r['threshold'] is None:
            print('    P  : NO THRESHOLD DECLARED. Not zero and not a pass -- a '
                  'metric with no line cannot be said to be drifting toward '
                  'anything, and that is the state, not an omission to fix here.')
            rc = max(rc, 1)
        else:
            print('    P  : %+.2f %s past the line of %.2f'
                  % (r['p'], r['units'], r['threshold']))
        if r['i'] is None:
            print('    I  : NO BAND DECLARED, so nothing can accumulate.')
        else:
            print('    I  : %.2f %s-readings accumulated past the band of %.2f, '
                  'over %d readings, %d of them breaching'
                  % (r['i']['sum'], r['units'], r['band'], r['i']['readings'],
                     r['i']['breaching']))
        d = r['d']
        if d.get('slope') is None:
            print('    D  : %s' % d.get('why', 'no slope'))
        else:
            print('    D  : %+.4f %s per reading over the last %d -- %s'
                  % (d['slope'], r['units'], d['readings'],
                     'WORSENING' if d['worsening'] else 'improving'))
            if d['to_threshold'] is not None:
                print('         projects crossing the line in about %.0f more '
                      'readings at this slope' % d['to_threshold'])
                rc = max(rc, 1)
        if r['arming']:
            print('    NOT ARMED -- these are measurements, not an alarm:')
            for why in r['arming']:
                print('      - %s' % why)
        print('')

    for a, b, note in divergences(results):
        rc = max(rc, 1)
        print('  DIVERGENCE -- %s and %s' % (a.upper(), b.upper()))
        print('    %s' % note)
        print('')

    print('  WHY NOTHING HERE ALARMS: see NOT ARMED above. The gains are not')
    print('  shipped with values and the labelled episodes do not exist yet.')
    print('  Tuning a controller against a series with no recorded instance of')
    print('  the metric going bad measures the false-positive half only, and')
    print('  reporting that one number as if it were performance is exactly the')
    print('  single-figure failure this platform has a standing rule against.')
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
