"""tests/run_reliability_growth_probe.py -- item 80's fitters can be shown to
WORK, and its gate can be shown to refuse for the right reason.

    python tests/run_reliability_growth_probe.py

THE ASYMMETRY THAT SHAPES THIS SUITE: today the tool REFUSES, and a refusal is
the cheapest thing in the world to fake. A gate that rejects everything, or a
fitter nobody has ever seen succeed, produces exactly the output this tool
produces now. So most of the arms below are about the POSITIVE direction --
that the fitters recover parameters they were given, and that the gate ADMITS a
series which qualifies. Only then is today's refusal a statement about the
data.

AND ONE ARM IS ABOUT A DEFECT THE BLIND LOCK ALREADY CAUGHT, kept because the
shape recurs: the same `a >= max(observed)` clamp was applied to both models.
It is correct for Goel-Okumoto, whose `a` IS the asymptote, and wrong for
Musa-Okumoto, which is unbounded. On a synthetic curve with a=40 the clamp
forced a>=110.9 and returned SSE 3497 against a true SSE of 0 -- caught before
the real series was ever read, because the lock generates from KNOWN parameters
rather than from a plot somebody eyeballed.
"""
import json
import math
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import reliability_growth as R                                   # noqa: E402

failures = []


def check(label, ok, detail=''):
    print(('  PASS ' if ok else '  FAIL ') + label + (('   ' + str(detail)) if detail else ''))
    if not ok:
        failures.append(label)


print('1. the blind lock')
check('1a  every fixture classifies as written', R.run_fixtures() == [], R.run_fixtures())
p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'reliability_growth.py'),
                    '--fixtures'], capture_output=True, text=True, cwd=REPO)
check('1b  the lock runs on its own and passes', p.returncode == 0, 'exit %d' % p.returncode)

print('2. THE FITTERS WORK -- without this, the refusal below is worthless')
ts = list(range(1, 31))
go = R.goel_okumoto(ts, R._synthetic_go(200.0, 0.12, 30))
check('2a  Goel-Okumoto recovers a=200 from its own curve',
      abs(go['a'] - 200.0) / 200.0 < 0.15, '%.1f' % go['a'])
mo = R.musa_okumoto(ts, R._synthetic_mo(40.0, 0.5, 30))
check('2b  Musa-Okumoto recovers a=40 from its own curve -- the arm that caught '
      'the asymptote clamp being copied onto an unbounded model',
      abs(mo['a'] - 40.0) / 40.0 < 0.15, '%.1f' % mo['a'])
# THE TOLERANCE IS RELATIVE, NOT AN ABSOLUTE SSE. The first version asked for
# sse < 1.0, which is not a statement about anything: SSE scales with the
# number of points and the square of the curve's magnitude. Expressed as RMS
# error against the curve's peak it is a fraction a reader can judge -- and the
# clamp defect this arm exists to catch sat at 15% by the same measure, so a 1%
# bar separates them by an order of magnitude rather than by a tuned constant.
_curve = R._synthetic_mo(40.0, 0.5, 30)
_rms = math.sqrt(mo['sse'] / len(_curve))
check('2c  ...and the fit is genuinely close: RMS error under 1%% of the '
      'curve peak, where the clamp defect this arm caught was 15%%',
      _rms / max(_curve) < 0.01,
      'rms %.3f on a peak of %.1f = %.2f%%' % (_rms, max(_curve), 100 * _rms / max(_curve)))
lo = R.goel_okumoto(ts, R._synthetic_go(200.0, 0.12, 30))['a']
hi = R.goel_okumoto(ts, R._synthetic_go(600.0, 0.12, 30))['a']
check('2d  CONTROL: a bigger population fits a bigger `a` -- 2a would pass on a '
      'function that ignores its input', hi > lo * 1.5, '%.0f vs %.0f' % (lo, hi))
check('2e  the fit is DETERMINISTIC -- a fitter that answers differently on the '
      'same input is the flake this platform has already quarantined one checker for',
      R.goel_okumoto(ts, R._synthetic_go(200.0, 0.12, 30)) == go)

print('3. THE GATE ADMITS what qualifies')
falling = [{'t': i, 'rate_per_100': 40.0 / i, 'defects': 1, 'substantive': 100,
            'date': 'd%02d' % i} for i in range(1, 26)]
saved = R.EFFORT_RECORDED
try:
    R.EFFORT_RECORDED = True
    ok, probs, rho = R.admissible(falling)
    check('3a  a long, falling, effort-recorded series is ADMITTED -- a gate that '
          'refuses everything is not a gate', ok, probs)
    check('3b  ...and its measured trend really is negative', rho < R.FALLING_TREND_AT,
          '%+.2f' % rho)
finally:
    R.EFFORT_RECORDED = saved

print('4. ...and REFUSES for the right reason, one criterion at a time')
saved = R.EFFORT_RECORDED
try:
    R.EFFORT_RECORDED = True
    flat = [{'t': i, 'rate_per_100': 12.0 + (3 if i % 2 else -3), 'defects': 1,
             'substantive': 100, 'date': 'd%02d' % i} for i in range(1, 26)]
    ok, probs, _ = R.admissible(flat)
    check('4a  long but FLAT is refused, and the reason names the rate',
          not ok and any('NOT FALLING' in x for x in probs), probs)
    ok, probs, _ = R.admissible(falling[:6])
    check('4b  SHORT but falling is refused, and the reason names the length',
          not ok and any('TOO FEW INTERVALS' in x for x in probs), probs)
    thin = [dict(r, substantive=3) for r in falling]
    ok, probs, _ = R.admissible(thin)
    check('4c  a series whose denominators are too small has NO usable rate, '
          'rather than a rate computed on three commits',
          not ok and any('NO USABLE RATE' in x for x in probs), probs)
finally:
    R.EFFORT_RECORDED = saved
ok, probs, _ = R.admissible(falling)
check('4d  the EFFORT criterion fires on its own, and is not a threshold that '
      'could be met by waiting',
      not ok and any('EFFORT IS NOT RECORDED' in x for x in probs))

print('5. what the real run says about itself')
r = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'reliability_growth.py')],
                   capture_output=True, text=True, cwd=REPO)
out = r.stdout or ''
check('5a  it refuses on the real series (exit 1) rather than fitting it',
      r.returncode == 1, 'exit %d' % r.returncode)
check('5b  it prints the series it judged, so the refusal can be checked',
      '2026-09-10' in out and 'per 100' in out)
# ── 5c WENT RED BECAUSE THE DATA MOVED, NOT BECAUSE THE TOOL BROKE ─────────
# It asserted `'EXCLUDED FROM THE RATE TREND' in out` UNCONDITIONALLY. That
# section is conditional: reliability_growth.py prints it only when some
# interval has a rate but a denominator under MIN_DENOMINATOR (10). It passed
# for as long as the register was sparse enough to have a thin interval.
#
# MEASURED 2026-09-14, after nine upstream commits: every one of the 6
# intervals now carries 28-157 substantive commits, so NOTHING IS THIN, the
# section correctly does not print, and this arm could never pass again until
# the data got sparse enough to be wrong in the old way. A test that only
# passes while the input is in one particular state is a string anchor into
# somebody else's data -- disciplines item 8's commonest shape, arriving in a
# probe rather than in a checker.
#
# THE ARM WAS WRONG, NOT THE TOOL, and the fix is to assert the PROPERTY
# instead of the sentence. The property is "nothing is dropped silently", and
# it has two honest satisfactions depending on the data:
#
#   some interval is thin  -> the excluded section must name it
#   none is thin           -> there is nothing to exclude, and the arm must
#                             not demand a disclosure of an empty set
#
# So the expected state is RE-DERIVED from the tool's own JSON on every run --
# a re-reference against the source, not a remembered string. It now fails if
# the tool ever drops a thin interval without saying so, in EITHER data state,
# and it cannot rot when the register grows again.
_series = json.loads(subprocess.run(
    [sys.executable, os.path.join(REPO, 'tools', 'reliability_growth.py'), '--json'],
    capture_output=True, text=True, cwd=REPO).stdout).get('series') or []
_thin = [s for s in _series
         if s.get('rate_per_100') is not None
         and s.get('substantive', 0) < R.MIN_DENOMINATOR]
_names_them = 'EXCLUDED FROM THE RATE TREND' in out
if _thin:
    check('5c  %d interval(s) ARE thin, so the report must NAME them rather than '
          'dropping them silently' % len(_thin),
          _names_them and all(s['date'] in out for s in _thin),
          'thin=%s, section present=%s' % ([s['date'] for s in _thin], _names_them))
else:
    # THE ARM STILL ASSERTS SOMETHING in this state -- an else branch that
    # checked nothing would be a skip wearing a pass's clothes, which is the
    # defect this whole file exists to prevent one level down.
    check('5c  NO interval is thin (all %d denominators >= %d), so the report '
          'must NOT claim an exclusion it did not make'
          % (len(_series), R.MIN_DENOMINATOR),
          not _names_them and len(_series) > 0,
          'section present=%s, intervals=%d' % (_names_them, len(_series)))
check('5d  it does not overclaim the DIRECTION of a weak correlation -- flat and '
      'rising fail identically and it says so',
      'Flat and rising fail identically' in out)
check('5e  it says what would change the answer, and which of those is a BUILD '
      'rather than a wait', 'WHAT WOULD CHANGE THE ANSWER' in out and 'is a BUILD' in out)
j = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'reliability_growth.py'),
                    '--json'], capture_output=True, text=True, cwd=REPO)
data = json.loads(j.stdout)
check('5f  the JSON carries fit: null -- a consumer cannot pick up a model the '
      'report refused to fit', data['fit'] is None and data['admissible'] is False)
check('5g  the series is derived LIVE, not copied from the scoping document -- a '
      'second hand-kept copy of a series is one that drifts',
      len(data['series']) >= 6 and all('substantive' in row for row in data['series']))

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  ' + f)
sys.exit(1 if failures else 0)
