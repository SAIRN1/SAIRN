"""ooda_phases.py -- item 67. Which PHASE is the bottleneck, not how long it took.

    python tools/ooda_phases.py
    python tools/ooda_phases.py --json
    python tools/ooda_phases.py --selftest

── WHY AN AGGREGATE CANNOT ANSWER THIS ───────────────────────────────────────
"Time to resolution" is one number over four separable phases:

    OBSERVE   the defect exists .......... somebody notices        DETECTED
    ORIENT    detected .................... understood
    DECIDE    understood .................. a course chosen
    ACT       decided ..................... fixed and verified

A single figure cannot tell a team that diagnoses instantly and takes a week to
decide from one that decides instantly and cannot see anything for a week. Those
need opposite fixes, and the aggregate is identical.

── AND ON THIS PLATFORM THE AGGREGATE IS NOT MERELY UNHELPFUL, IT IS EMPTY ───
MEASURED, 2026-09-15, over docs/defect-density-register.json against real commit
dates: **73 of 74 resolvable records were fixed THE SAME DAY they were recorded.**
Detect-to-fix is approximately zero across the entire register.

So the ACT phase -- the only one this repo records -- is already as fast as it
can be, and every remaining second of real-world exposure is in a phase nothing
times. A dashboard built on the aggregate would show a platform with no problem.

THE ONE REAL OBSERVE-PHASE NUMBER ANYBODY HAS is the cron-failure incident:
SILENT FOR 24 HOURS. Not a slow fix -- a fast fix that could not start. And the
class it belongs to is worse than one incident: `api/sairndental/send-reminder.js`
returned 500 EVERY HOUR FOR MONTHS on a `RESEND_FROM_ADDRESS` /
`RESEND_FROM_EMAIL` name mismatch, which is an Observe-phase failure measured in
months against an Act phase measured in minutes.

── WHAT THIS TOOL THEREFORE DOES ─────────────────────────────────────────────
It measures the one boundary that is recorded, states the three that are not,
and refuses to publish an aggregate. A number that exists is not a reason to
report it when three of its four components are missing -- that is the
"denominator over the subset you looked at" error one level up.

  RECORDED       detected -> fixed, from a record's `date` to its fix commit's
                 author date
  NOT RECORDED   injected -> detected  (the Observe phase, the bottleneck)
                 detected -> understood
                 understood -> decided

To make the Observe phase measurable, a record needs an INJECTION DATE. Item 66
is blocked on the same thing: 73 of 77 records carry no injection commit, and say
so in their own `unknown_reason` rather than being blame-backfilled. **This tool
and item 66 are blocked on ONE field**, which is worth knowing before either is
scheduled again.

── WHAT IT CANNOT SEE ────────────────────────────────────────────────────────
  * The fix commit's date is when the fix LANDED, not when work began, so even
    the recorded boundary is an upper bound on Act and includes Orient and
    Decide inside it. It is reported as `detect_to_fix`, never as `act`.
  * A record whose fix commit predates it -- there is one, at -25 days -- means
    the cited commit is not the fix. Reported as an ANOMALY rather than folded
    into a mean, because a negative duration is a data defect and averaging it
    away is how it survives.
"""
import collections
import datetime
import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO, 'docs', 'defect-density-register.json')

PHASES = [
    ('OBSERVE', 'the defect exists -> somebody notices', 'injection date', False),
    ('ORIENT', 'detected -> understood', 'an understood-at stamp', False),
    ('DECIDE', 'understood -> a course chosen', 'a decided-at stamp', False),
    ('ACT', 'decided -> fixed and verified', 'the fix commit date', True),
]


class CouldNotTell(Exception):
    pass


def commit_date(sha, cache):
    sha = (sha or '').strip()
    if not sha:
        return None
    if sha in cache:
        return cache[sha]
    p = subprocess.run(['git', '-C', REPO, 'log', '-1', '--format=%ad',
                        '--date=short', sha],
                       capture_output=True, encoding='utf-8', errors='replace')
    out = (p.stdout or '').strip() if p.returncode == 0 else None
    cache[sha] = out or None
    return cache[sha]


def measure():
    try:
        recs = json.load(io.open(REGISTER, encoding='utf-8'))['records']
    except OSError as e:
        raise CouldNotTell('defect register unreadable: %s' % e)
    except (ValueError, KeyError) as e:
        raise CouldNotTell('defect register unusable: %s' % e)
    if not recs:
        raise CouldNotTell('defect register has no records')

    cache = {}
    lags, anomalies, unresolvable = collections.Counter(), [], []
    injection_dated = 0
    for r in recs:
        if isinstance(r.get('injection'), dict) and r['injection'].get('commit'):
            injection_dated += 1
        fix = commit_date(r.get('commit'), cache)
        if not fix:
            unresolvable.append(r.get('subject', '?')[:60])
            continue
        try:
            a = datetime.date.fromisoformat(r['date'])
            b = datetime.date.fromisoformat(fix)
        except Exception:
            unresolvable.append(r.get('subject', '?')[:60])
            continue
        days = (b - a).days
        if days < 0:
            anomalies.append({'subject': r.get('subject', '?')[:70], 'days': days,
                              'recorded': r['date'], 'commit_date': fix})
            continue
        lags[days] += 1
    return {'records': len(recs), 'resolved': sum(lags.values()),
            'lags': dict(lags), 'anomalies': anomalies,
            'unresolvable': len(unresolvable),
            'injection_dated': injection_dated,
            'same_day': lags.get(0, 0)}


def _selftest():
    okall = True

    def check(name, cond, detail=''):
        nonlocal okall
        print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + str(detail)))
        if not cond:
            okall = False

    print('1. the phase table is complete and only ONE phase is recorded')
    check('four phases', len(PHASES) == 4, len(PHASES))
    rec = [p for p in PHASES if p[3]]
    check('exactly one is marked recorded', len(rec) == 1, [p[0] for p in rec])
    check('...and it is ACT, not OBSERVE', rec[0][0] == 'ACT', rec[0][0])
    check('OBSERVE is marked NOT recorded -- it is the bottleneck and untimed',
          any(p[0] == 'OBSERVE' and not p[3] for p in PHASES))

    print('\n2. a negative duration is an ANOMALY, never averaged away')
    src = io.open(os.path.join(REPO, 'tools', 'ooda_phases.py'),
                  encoding='utf-8').read()
    code = '\n'.join(l for l in src.split('\n') if not l.strip().startswith('#'))
    check('the code branches on days < 0', 'days < 0' in code)
    # ── ASSERT ON STRUCTURE, NOT ON THE WORD. FOURTH TIME TONIGHT. ───────────
    # The first version searched the source for the word "mean" and failed on
    # this tool's OWN printed explanation -- "a mean hides it". Same class as
    # three other arms written today: the QR suite's "no PII" arm firing on the
    # words "no patient or practice data", the Tier A gate's fail-open arm firing
    # on a docstring quoting the old line, and money.test.js's "no divide()" arm
    # firing on the comment saying why there is none.
    #
    # THE CLASS, NAMED: a text match counts a word's appearance in PROSE the same
    # as its appearance in LOGIC -- and the better the prose explains the
    # absence, the more likely the checker is to report the thing as present. The
    # defence is to assert on a structure prose cannot contain. An arithmetic
    # mean needs a division by a count; that is what to look for.
    import re as _re
    nostr = _re.sub(r"'[^']*'|\"[^\"]*\"", "''", code)
    check('no ARITHMETIC MEAN is computed -- checked structurally, not by word',
          not _re.search(r'/\s*(float\()?\s*len\s*\(', nostr),
          'an aggregate is the thing this tool refuses to publish')
    check('CONTROL: the prose really does contain the word, so the strip is '
          'load-bearing', 'mean' in src.lower())

    print('\n3. the real register measures, and the answer is the finding')
    try:
        m = measure()
        check('it resolved most records', m['resolved'] > 50, m['resolved'])
        share = 100.0 * m['same_day'] / m['resolved'] if m['resolved'] else 0
        check('detect->fix is ~0 for almost everything (>90%% same-day)',
              share > 90, '%.0f%%' % share)
        check('and the Observe phase is unmeasurable: <10 records have an '
              'injection date', m['injection_dated'] < 10, m['injection_dated'])
    except CouldNotTell as e:
        check('the real register measures', False, e)

    print('')
    print('  all arms pass' if okall else '  ARMS FAILED')
    return 0 if okall else 2


def main(argv):
    if '--selftest' in argv:
        return _selftest()
    try:
        m = measure()
    except CouldNotTell as e:
        print('COULD NOT CHECK: %s' % e)
        print('NOTHING WAS MEASURED. This is not a clean result.')
        return 2
    if '--json' in argv:
        print(json.dumps(m, indent=1))
        return 0

    print('OODA PHASE ISOLATION -- item 67, report only')
    print('')
    print('  phase     boundary                                 recorded?')
    for name, boundary, needs, recorded in PHASES:
        print('  %-9s %-40s %s' % (name, boundary,
                                   'YES' if recorded else 'no  (needs %s)' % needs))
    print('')
    print('  records                    %3d' % m['records'])
    print('  detect->fix resolvable     %3d   (%d could not be resolved)'
          % (m['resolved'], m['unresolvable']))
    print('  records with an INJECTION  %3d   <- the Observe phase needs this'
          % m['injection_dated'])
    print('')
    print('  detect->fix, in DAYS:')
    for days in sorted(m['lags']):
        n = m['lags'][days]
        print('    %+3d day(s)  %-3d %s' % (days, n, '#' * min(n, 46)))
    if m['resolved']:
        share = 100.0 * m['same_day'] / m['resolved']
        print('')
        print('  SAME DAY: %d of %d = %.0f%%' % (m['same_day'], m['resolved'], share))
    if m['anomalies']:
        print('')
        print('  ANOMALIES -- a fix commit DATED BEFORE the record, so the cited')
        print('  commit is not the fix. Reported rather than averaged away,')
        print('  because a negative duration is a data defect and a mean hides it:')
        for a in m['anomalies']:
            print('    %+d days  recorded %s, commit %s' % (a['days'], a['recorded'], a['commit_date']))
            print('             %s' % a['subject'])
    print('')
    print('NO AGGREGATE IS PUBLISHED, DELIBERATELY. Three of the four phase')
    print('boundaries are not recorded anywhere, and a "time to resolution" built')
    print('from one of four components is the denominator-over-the-subset error.')
    print('')
    print('THE MEASURABLE PHASE IS ALREADY FAST AND THAT IS THE POINT. Detect to')
    print('fix is essentially zero, so every second of real exposure lives in a')
    print('phase nothing times. The only Observe-phase number anybody has is the')
    print('cron-failure incident -- SILENT 24 HOURS -- and its worse sibling:')
    print('send-reminder.js returned 500 every hour FOR MONTHS on an env-var name')
    print('mismatch. An Observe phase measured in months, an Act phase in minutes.')
    print('')
    print('TO MEASURE OBSERVE, A RECORD NEEDS AN INJECTION DATE. Item 66 is')
    print('blocked on the same field. The two are one field apart, which is worth')
    print('knowing before either is scheduled again.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
