"""Do the I and D terms actually see what P cannot -- and can they be talked out of it?

    python tests/run_trend_alarm_probe.py

Item 45. The tool's own `--fixtures` lock is the blind half, driven here as
well so a failure there fails the SUITE rather than only a hand run. What this
file adds is the part the lock cannot cover:

  * the real series, built from real git history, with the divergence checked
    as a NUMBER rather than as a sentence in a docstring;
  * every arming criterion refused AND cleared, because a gate that can never
    pass and a gate that always passes fail the same assertion;
  * the two write commands, proven not to touch the real tuning file.

THE CONTROL THAT MATTERS MOST IS THE SIGN. A D-term that fires on fast
IMPROVEMENT is not a worse alarm, it is an inverted one, and it passes every
test that only ever feeds it a worsening series. Section 3 drives both.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import trend_alarm as T                                          # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = T.main(argv)
    return rc, buf.getvalue()


FLAT = [('2026-01-%02dT00:00' % (i + 1), 10.0) for i in range(50)]
CREEP = [('2026-01-%02dT00:00' % (i + 1), 10.4) for i in range(50)]
RISING = [('2026-01-%02dT00:00' % (i + 1), 10.0 + i) for i in range(50)]
FALLING = [('2026-01-%02dT00:00' % (i + 1), 60.0 - i) for i in range(50)]


print('\n1. THE TOOL\'S OWN BLIND LOCK RUNS IN THE SUITE, NOT ONLY BY HAND')
lock_lines, lock_bad = T.fixtures()
check('every fixture arm passes', lock_bad == 0,
      [l for l in lock_lines if l.startswith('  FAIL')])
check('the lock is not empty -- an empty lock passes trivially and is how a '
      'control quietly stops testing anything', len(lock_lines) >= 15,
      len(lock_lines))
rc, out = run(['--fixtures'])
check('--fixtures reads NO real series, so the lock cannot be contaminated by '
      'the data it is meant to be independent of',
      'no real series read' in out and rc == 0, out[:200])

print('\n2. THE INTEGRAL TERM SEES WHAT P CANNOT')
check('a series parked just past the band accumulates a real number',
      T.i_term(CREEP, 10.0, 'higher')['sum'] > 0)
check('...while P on that same series says PASS against any sane threshold -- '
      'which is the blind spot, stated as two numbers that disagree',
      T.p_term(CREEP, 50.0, 'higher') < 0 and T.i_term(CREEP, 10.0, 'higher')['sum'] > 0)
check('CONTROL: a series inside the band accumulates exactly zero. An integral '
      'that always grows is a clock with a threshold',
      T.i_term(FLAT, 20.0, 'higher')['sum'] == 0)
check('CONTROL: the accumulation is one-sided -- time spent GOOD does not net '
      'off time spent bad',
      T.i_term(FLAT[:25] + CREEP[25:], 10.2, 'higher')['sum'] > 0)
check('CONTROL: it counts BREACHING readings separately from the magnitude, so '
      'one huge excursion is not reported as a persistent problem',
      T.i_term(FLAT[:49] + [('2026-01-50T00:00', 900.0)], 20.0, 'higher')['breaching'] == 1)
check('the window is bounded -- an integral over all history never forgets and '
      'is therefore permanently alarmed',
      T.i_term(CREEP, 10.0, 'higher')['readings'] == min(T.I_WINDOW, len(CREEP)))

print('\n3. THE DERIVATIVE TERM, AND THE SIGN IS THE WHOLE TEST')
d_up = T.d_term(RISING, 100.0, 'higher')
check('a rising series under worse_is=higher is WORSENING', d_up['worsening'])
check('...and projects a crossing while P still says comfortably inside',
      T.p_term(RISING, 100.0, 'higher') < 0 and d_up['to_threshold'] is not None,
      (T.p_term(RISING, 100.0, 'higher'), d_up))
check('CONTROL: the SAME series under worse_is=lower is IMPROVING. An inverted '
      'D-term is indistinguishable from a correct one until this arm runs',
      not T.d_term(RISING, 100.0, 'lower')['worsening'])
check('CONTROL: an improving series projects NO crossing rather than a negative '
      'countdown printed as if it were a deadline',
      T.d_term(FALLING, 100.0, 'higher')['to_threshold'] is None)
check('CONTROL: a flat series is not worsening under EITHER direction, so the '
      'term is not simply answering yes',
      not T.d_term(FLAT, 100.0, 'higher')['worsening']
      and not T.d_term(FLAT, 100.0, 'lower')['worsening'])
check('two readings REFUSE rather than fitting a line through two points and '
      'reporting it as a trend', T.d_term(RISING[:2], 100.0, 'higher')['slope'] is None)
check('CONTROL: the slope is a real least-squares fit, not the last-minus-first '
      'difference -- a single spike at the end must not set the trend',
      abs(T.d_term(FLAT[:19] + [('2026-01-20T00:00', 200.0)], None, 'higher')['slope']
          - (200.0 - 10.0) / 19.0) > 1.0)

print('\n4. THE ARMING GATE REFUSES, AND CAN ALSO CLEAR')
empty = {'episodes': [], 'gains': {}}
check('a long series with no labelled episode is NOT armed -- length is the '
      'cheap half and passing on it alone is the whole trap',
      any('NO LABELLED EPISODE' in r for r in T.arming(RISING, empty, 'x')))
check('a short series is refused for length as well',
      any('TOO FEW OBSERVATIONS' in r for r in T.arming(RISING[:5], empty, 'x')))
check('gains missing is its own named reason, not folded into the others',
      any('NO GAINS RECORDED' in r for r in T.arming(RISING, empty, 'x')))
armed = {'episodes': [{'series': 'x', 'at': '2026-01-01', 'why': 'fixture'}],
         'gains': {'x': {'kp': 1, 'ki': 1, 'kd': 1}}}
check('CONTROL: with an episode AND gains AND length, the gate CLEARS. A gate '
      'that can never pass is a disabled feature with a paragraph attached',
      T.arming(RISING, armed, 'x') == [])
check('CONTROL: an episode for a DIFFERENT series does not arm this one',
      any('NO LABELLED EPISODE' in r for r in T.arming(
          RISING, {'episodes': [{'series': 'other'}], 'gains': {'x': {}}}, 'x')))
check('the refusal NAMES the measured value, not just the verdict -- "too few" '
      'without the number cannot be acted on',
      '%d' % len(RISING[:5]) in ' '.join(T.arming(RISING[:5], empty, 'x')))

print('\n5. THE REAL SERIES -- built from real history, not asserted')
tr = T.series_traceability_untraced()
ra = T.series_traceability_ratio()
check('the traceability series builds from git history at all',
      tr is not None and len(tr) > 0, tr and len(tr))
check('...with enough readings to be worth a slope (>= MIN_OBSERVATIONS)',
      len(tr) >= T.MIN_OBSERVATIONS, len(tr))
check('both views come from the SAME readings, so a divergence between them is '
      'not two different samples', len(tr) == len(ra), (len(tr), len(ra)))
check('the series is sorted by time -- four clones commit out of order and an '
      'unsorted series makes every slope meaningless',
      [a for a, _v in tr] == sorted(a for a, _v in tr))
check('CONTROL: the values are not all identical, which would make every term '
      'trivially zero', len({v for _a, v in tr}) > 3, len({v for _a, v in tr}))

print('\n6. THE LIVE DIVERGENCE -- checked as numbers, not as a docstring')
tune = T.load_tuning()
results = [T.analyse(n, T.SERIES[n], tune) for n in sorted(T.SERIES)]
by = {r['name']: r for r in results}
du = by['traceability-untraced']['d']
dr = by['traceability-ratio']['d']
check('the untraced COUNT is worsening', du.get('worsening') is True, du)
check('the traced RATIO is improving over the same readings',
      dr.get('worsening') is False, dr)
check('...so one document yields two views with OPPOSITE verdicts, which is '
      'the finding and is measured rather than claimed',
      du.get('worsening') != dr.get('worsening'))
divs = T.divergences(results)
check('the tool REPORTS that divergence rather than leaving it to be noticed '
      'across two blocks', len(divs) == 1, divs)
check('...and the report carries both slopes, so a reader can check it',
      divs and '%+.4f' % du['slope'] in divs[0][2] and '%+.4f' % dr['slope'] in divs[0][2],
      divs and divs[0][2][:200])
check('CONTROL: a divergence is only looked for between DECLARED same-source '
      'pairs -- any two unrelated metrics point different ways sometimes, and '
      'calling that a finding is a coincidence in a suit',
      all(a in T.SERIES and b in T.SERIES for a, b, _w in T.SAME_SOURCE)
      and ('defect-rate' not in [x for p in T.SAME_SOURCE for x in p[:2]]))
check('CONTROL: two series moving the SAME way produce no divergence',
      T.divergences([
          {'name': 'traceability-ratio', 'd': {'slope': 1.0, 'worsening': True},
           'observations': 5, 'first': ('a', 1), 'last': ('b', 2)},
          {'name': 'traceability-untraced', 'd': {'slope': 1.0, 'worsening': True},
           'observations': 5, 'first': ('a', 1), 'last': ('b', 2)}]) == [])

print('\n7. NO SERIES SILENTLY BECOMES A PASS')
rc, out = run([])
check('a metric with NO declared threshold says so rather than reporting a '
      'margin of zero', 'NO THRESHOLD DECLARED' in out, out[:400])
check('...and that is a finding, so the run does not exit 0',
      rc != 0, rc)
armed_blocks = [l for l in out.splitlines() if l.strip().startswith('NOT ARMED --')]
check('every series prints its NOT ARMED reasons rather than a verdict',
      len(armed_blocks) == len(T.SERIES), (len(armed_blocks), len(T.SERIES)))
check('the word ALARM is never used as a verdict on a real series -- the tool '
      'measures and says it is not armed',
      'ALARM' not in out.replace('TREND ALARM', '').replace('NOTHING HERE ALARMS', ''),
      [l for l in out.splitlines() if 'ALARM' in l][:3])

print('\n8. THE WRITE COMMANDS CANNOT FORGE A TUNING RECORD')
REAL = T.TUNING
existed = os.path.exists(REAL)
before = io.open(REAL, 'rb').read() if existed else None
tmp = tempfile.mkdtemp(prefix='trend-alarm-probe-')
try:
    T.TUNING = os.path.join(tmp, 'tuning.json')
    check('an episode with no explanation is REFUSED -- a date is a label with '
          'nothing in it to tune against',
          run(['--record-episode', 'defect-rate', '2026-09-14', 'bad'])[0] == 2)
    check('an episode for an unknown series is refused',
          run(['--record-episode', 'not-a-series', '2026-09-14',
               'a perfectly long explanation of what went bad'])[0] == 2)
    check('CONTROL: neither refusal wrote a file', not os.path.exists(T.TUNING))
    check('gains BEFORE any episode are refused -- that is the exact ordering '
          'this tool exists to enforce',
          run(['--set-gains', 'defect-rate', '1', '1', '1'])[0] == 2)
    check('an episode WITH an explanation is recorded',
          run(['--record-episode', 'defect-rate', '2026-09-14',
               'the weighted rate crossed 60/day and nothing said so'])[0] == 0)
    check('...and only THEN are gains accepted',
          run(['--set-gains', 'defect-rate', '1', '0.5', '2'])[0] == 0)
    t = json.load(io.open(T.TUNING, encoding='utf-8'))
    check('the record keeps the WHY, not just the date',
          len(t['episodes'][0]['why']) > 20, t['episodes'][0])
    check('...and stamps the criteria version that was in force',
          t['episodes'][0]['criteria_version'] == T.CRITERIA_VERSION)
    check('with an episode and gains recorded, that series ARMS -- proving the '
          'gate is reachable and not decoration',
          T.arming(RISING, t, 'defect-rate') == [], T.arming(RISING, t, 'defect-rate'))
finally:
    T.TUNING = REAL
    shutil.rmtree(tmp, ignore_errors=True)
check('the real tuning file is exactly as it was',
      os.path.exists(REAL) == existed
      and (not existed or io.open(REAL, 'rb').read() == before))

print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
