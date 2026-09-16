"""Does the defect budget actually GATE, and can it be talked out of it?

    python tests/run_defect_budget_policy_probe.py

SIX REQUIREMENTS WERE SPECIFIED BEFORE THIS WAS BUILT, and each one is here
because the obvious implementation gets it wrong. This file drives all six, and
every one carries the control that keeps the requirement from being satisfied
vacuously -- a margin that never lets the band change satisfies "margin"; an
override that is always refused satisfies "rare"; a policy that never forbids
anything satisfies "graduated".

  1  margin before firing      sections 2 and 3
  2  stamped with the number   sections 4 and 9
  3  revisit, never reverse    sections 5 and 10
  4  four graduated tiers      sections 1 and 9
  5  window flagged not picked sections 6 and 8
  6  override rare by design   section 7

THE CRITERIA ARE LOCKED AGAINST SYNTHETIC FIXTURES, NOT AGAINST THE REAL
REGISTER. Sections 8-11 build registers whose answer is known by construction --
a quiet one, a strained one, and one whose defects are all old -- and drive the
tool's REAL OUTPUT against them. Arms that only grep the source for a sentence
are marked DISCLOSURE and are never the only evidence for a requirement: a
string anchor stops matching one day and says nothing when it does.

NOTHING HERE TOUCHES THE REAL DECISION FILE OR THE REAL REGISTER. Every write
goes to a temp path and section 12 proves it: this tool's own subject is a
record of governance decisions, and a probe that can forge one is worse than no
probe.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import defect_budget_policy as P                                 # noqa: E402

fails = []
TODAY = time.strftime('%Y-%m-%d')


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def run(argv):
    """The tool's REAL stdout and exit code. Behaviour, not docstrings."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = P.main(argv)
    return rc, buf.getvalue()


def write_register(path, records):
    io.open(path, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(records, indent=1) + '\n')
    return path


def recs_of(n, severity, date):
    return [{'commit': 'f%04d' % i, 'date': date, 'severity': severity,
             'subject': 'synthetic fixture record %d' % i} for i in range(n)]


print('\n1. FOUR GRADUATED BANDS, not two')
check('above 50% is NORMAL', P.raw_band(80.0)[0] == 'NORMAL')
check('25-50% is INCREASED REVIEW', P.raw_band(40.0)[0] == 'INCREASED REVIEW')
check('10-25% is FEATURE FREEZE', P.raw_band(18.0)[0] == 'FEATURE FREEZE')
check('below 10% is ALL HANDS', P.raw_band(4.0)[0] == 'ALL HANDS')
check('exactly 0% is ALL HANDS, not an index error', P.raw_band(0.0)[0] == 'ALL HANDS')
check('all four bands are distinct -- four names that collapse to two is the '
      'binary policy with extra labels',
      len({n for _f, n, _a in P.BANDS}) == 4, P.BANDS)
check('new work is permitted in the top TWO bands and no others',
      P.NEW_WORK_ALLOWED == {'NORMAL', 'INCREASED REVIEW'}, P.NEW_WORK_ALLOWED)
check('...so a FEATURE FREEZE really forbids new vertical work',
      'FEATURE FREEZE' not in P.NEW_WORK_ALLOWED)

print('\n2. MARGIN -- it does not fire NEAR a boundary')
# 26% is inside MARGIN of the 25 line. Coming from INCREASED REVIEW, the band
# must hold rather than flicker as the number wobbles across it.
band, _a, approaching = P.band_with_margin(26.0, 'INCREASED REVIEW')
check('a number within the margin does NOT change the band',
      band == 'INCREASED REVIEW', (band, approaching))
band, _a, approaching = P.band_with_margin(24.0, 'INCREASED REVIEW')
check('...and the band it WOULD be in is reported, so the margin is visible '
      'rather than silent stickiness', approaching == 'FEATURE FREEZE',
      (band, approaching))
check('the held band keeps the HELD band\'s action, not the proposed one -- '
      'holding the name while printing the stricter action gates on a band '
      'nobody is in',
      P.band_with_margin(24.0, 'INCREASED REVIEW')[1]
      == P.raw_band(40.0)[1], P.band_with_margin(24.0, 'INCREASED REVIEW'))

print('\n3. CONTROL -- the margin is not an excuse never to move')
band, _a, _ap = P.band_with_margin(18.0, 'INCREASED REVIEW')
check('past the boundary WITH ROOM TO SPARE, the band changes',
      band == 'FEATURE FREEZE', band)
band, _a, _ap = P.band_with_margin(80.0, 'ALL HANDS')
check('and it changes in the RECOVERING direction too', band == 'NORMAL', band)
# THE HALF THAT MATTERS. The temptation is always to declare recovery early.
band, _a, _ap = P.band_with_margin(11.5, 'ALL HANDS')
check('LEAVING a strict band is delayed by the same margin -- the temptation is '
      'always to declare recovery early', band == 'ALL HANDS', band)
check('with no prior band there is nothing to hold, so the raw band applies',
      P.band_with_margin(26.0, None)[0] == 'INCREASED REVIEW')
check('CONTROL: the margin is smaller than the narrowest band, or it would '
      'span a whole tier and the middle bands could never be entered',
      0 < P.MARGIN < min(P.BANDS[i][0] - P.BANDS[i + 1][0]
                         for i in range(len(P.BANDS) - 1)), P.MARGIN)

print('\n4. EVERY DECISION IS STAMPED WITH THE NUMBER THAT PRODUCED IT')
recs = P.load_register()
s = P.stamp(recs, 'rolling', 42.0, 34.8, 70, 'INCREASED REVIEW')
for field in ('criteria_version', 'records_counted', 'records_in_register',
              'weighted_spent', 'remaining_pct', 'band', 'register_digest',
              'budget_per_window', 'window_mode'):
    check('the stamp carries %s' % field, field in s, sorted(s))
check('the digest is of the REGISTER CONTENTS, so a later reader can tell '
      '"the number changed" from "the reading was wrong"',
      P.register_digest(recs) == s['register_digest'])
check('CONTROL: dropping one record changes the digest',
      P.register_digest(recs[:-1]) != P.register_digest(recs))
check('CONTROL: changing a record\'s SEVERITY changes the digest -- a digest '
      'over identifiers alone would miss the field the weighting uses',
      P.register_digest([dict(recs[0], severity='critical')] + list(recs[1:]))
      != P.register_digest(recs))
check('CONTROL: the same register digests the same, so a difference means a '
      'difference and not clock noise',
      P.register_digest(recs) == P.register_digest(list(recs)))

print('\n5. REVISIT, NOT REVERSE')
old = P.stamp(recs, 'permanent', 80.0, 12.0, 70, 'NORMAL')
dec = {'window_mode': 'permanent', 'stamps': [old], 'overrides': []}
flags = P.revisit_flags(dec, recs)
check('a recorded decision whose band would differ now raises a flag',
      len(flags) == 1 and flags[0]['was'] == 'NORMAL', flags)
check('...and the flag says whether the REGISTER changed or only the reading',
      flags and 'register_changed' in flags[0], flags)
check('the recorded decision is NOT rewritten -- a policy that silently '
      'un-freezes itself is one nobody can rely on',
      dec['stamps'][0]['band'] == 'NORMAL', dec['stamps'][0])
cur_pct, cur_tot, cur_n = P.remaining_pct(recs, 'permanent')
agreeing = P.stamp(recs, 'permanent', cur_pct, cur_tot, cur_n,
                   P.raw_band(cur_pct)[0])
check('CONTROL: a decision that still agrees raises NO flag, so the flag is '
      'about disagreement and not about age',
      P.revisit_flags({'window_mode': 'permanent', 'stamps': [agreeing]}, recs) == [])
check('CONTROL: with no window mode recorded nothing is flagged, because '
      'nothing was decided to revisit',
      P.revisit_flags({'window_mode': None, 'stamps': [old]}, recs) == [])

print('\n6. THE WINDOW QUESTION IS FLAGGED, NOT PICKED')
roll = P.remaining_pct(recs, 'rolling')
perm = P.remaining_pct(recs, 'permanent')
check('BOTH window modes are computed',
      isinstance(roll[0], float) and isinstance(perm[0], float))
check('rolling counts NO MORE records than permanent -- a window that widened '
      'the count would be the opposite of a window', roll[2] <= perm[2],
      (roll[2], perm[2]))
check('the shipped default is UNDECIDED: no window mode is baked into the '
      'module, so the first reader must choose one',
      P.load_decisions().get('window_mode') is None
      or os.path.exists(P.DECISIONS), P.load_decisions().get('window_mode'))
src = io.open(os.path.join(REPO, 'tools', 'defect_budget_policy.py'),
              encoding='utf-8').read()
check('DISCLOSURE: the source names the real cost of BOTH choices rather than '
      'recommending one', 'ages out' in src and 'only ever falls' in src)

TMP = tempfile.mkdtemp(prefix='budget-policy-probe-')
REAL_DECISIONS, REAL_REGISTER = P.DECISIONS, P.REGISTER
REAL_EXISTED = os.path.exists(REAL_DECISIONS)
REAL_BYTES = (io.open(REAL_DECISIONS, 'rb').read() if REAL_EXISTED else None)
REGISTER_BYTES_BEFORE = io.open(REAL_REGISTER, 'rb').read()

try:
    P.DECISIONS = os.path.join(TMP, 'decisions.json')

    check('a --decide with no reason is REFUSED -- a governance choice with no '
          'recorded why cannot be revisited by anybody but its author',
          run(['--decide', 'rolling', 'because'])[0] == 1)
    check('an invalid window mode is refused',
          run(['--decide', 'sometimes', 'a perfectly good long reason here'])[0] == 1)
    check('CONTROL: neither refusal wrote a decision file, so a refused choice '
          'is not a quietly recorded one', not os.path.exists(P.DECISIONS))
    check('a --decide WITH a reason is recorded',
          run(['--decide', 'rolling',
               'discovery phase: recent history predicts the next month'])[0] == 0)
    d = json.load(io.open(P.DECISIONS, encoding='utf-8'))
    check('...and it stores the reason, not just the choice',
          d['window_mode'] == 'rolling' and len(d['window_reason']) > 20, d)
    check('...and stamps the decision with the number that produced it',
          d['stamps'] and 'register_digest' in d['stamps'][0], d.get('stamps'))
    check('...and that stamped number RECOMPUTES to the same value from the '
          'same register -- a stamp that cannot be reproduced records nothing',
          abs(d['stamps'][0]['remaining_pct']
              - round(P.remaining_pct(recs, 'rolling')[0], 2)) < 0.01,
          d['stamps'][0])

    print('\n7. THE OVERRIDE IS RARE BY CONSTRUCTION')
    check('an override with no real reason is refused',
          run(['--override', 'needed'])[0] == 1)
    check('an override WITH a reason is recorded',
          run(['--override', 'production incident, customer data at risk now'])[0] == 0)
    d = json.load(io.open(P.DECISIONS, encoding='utf-8'))
    check('...with its reason and its register digest',
          d['overrides'][0]['reason'] and d['overrides'][0]['register_digest'])
    for i in range(P.OVERRIDE_ALARM_IN_WINDOW):
        run(['--override', 'another genuine emergency number %d here' % i])
    rc, out = run(['--override', 'one more real emergency, past the alarm now'])
    n = len(P.recent_overrides(json.load(io.open(P.DECISIONS, encoding='utf-8'))))
    check('past the alarm the tool reports the MECHANISM as failed rather than '
          'any single use -- the failure mode is twenty good overrides, not one '
          'bad one', 'THE OVERRIDE MECHANISM HAS FAILED' in out,
          (n, out[:200]))
    # CONTROL, and it is the one that keeps requirement 6 from being satisfied
    # by simply refusing overrides. A policy that cannot be overridden in a real
    # emergency does not get respected -- it gets disabled entirely.
    check('CONTROL: the override is still ACCEPTED past the alarm. Refusing it '
          'would make the policy undeployable, and an undeployable policy is '
          'deleted rather than obeyed', rc == 0)
    check('CONTROL: the alarm is not permanently on -- a fresh record with ONE '
          'override is below it, so the alarm is about frequency and not about '
          'the mechanism existing',
          len(P.recent_overrides({'overrides': [
              {'at': TODAY + 'T00:00:00Z'}]})) <= P.OVERRIDE_ALARM_IN_WINDOW)
    rc, quiet = run([])
    check('CONTROL: the override count is printed on EVERY run, at the top, '
          'not only on the run that used one',
          'OVERRIDES IN THE LAST' in quiet
          and quiet.index('OVERRIDES IN THE LAST') < quiet.index('register:'),
          quiet[:300])

    # ── SYNTHETIC FIXTURES. The answer is known by construction. ────────────
    QUIET = write_register(os.path.join(TMP, 'quiet.json'),
                           recs_of(2, 'low', TODAY))            # 0.5 spent
    STRAINED = write_register(os.path.join(TMP, 'strained.json'),
                              recs_of(16, 'high', TODAY))       # 48.0 spent -> 20%
    AGED = write_register(os.path.join(TMP, 'aged.json'),
                          recs_of(30, 'high', '2026-01-01'))    # 90.0, all old

    print('\n8. THE TWO WINDOW MODES REALLY DISAGREE -- which is what makes '
          'refusing to pick a decision and not a hedge')
    P.REGISTER = AGED
    aged = P.load_register()
    a_roll = P.raw_band(P.remaining_pct(aged, 'rolling')[0])[0]
    a_perm = P.raw_band(P.remaining_pct(aged, 'permanent')[0])[0]
    check('on a register of OLD defects the two modes give DIFFERENT bands -- '
          'rolling %s, permanent %s' % (a_roll, a_perm), a_roll != a_perm,
          (a_roll, a_perm))
    check('rolling is the more forgiving one there: an unfixed defect ages out '
          'and the budget recovers for free', a_roll == 'NORMAL', a_roll)
    check('permanent is the unforgiving one: nothing ages out',
          a_perm == 'ALL HANDS', a_perm)
    P.DECISIONS = os.path.join(TMP, 'undecided.json')
    rc, out = run([])
    check('with no decision recorded the tool gates NOTHING and SAYS so in its '
          'real output', 'NOTHING IS GATED' in out, out[:400])
    check('CONTROL: and it prints no band verdict at all, so "refuses to pick" '
          'is not one of the two picks in disguise',
          'NEW VERTICAL WORK' not in out and 'ACTION     :' not in out, out[:400])

    print('\n9. THE GATE ACTUALLY FORBIDS SOMETHING (and does not forbid '
          'everything)')
    P.REGISTER = STRAINED
    P.DECISIONS = os.path.join(TMP, 'strained-decisions.json')
    run(['--decide', 'permanent',
         'fixture: every defect counts, nothing ages out of this budget'])
    rc, out = run([])
    check('a register at 20% remaining prints FEATURE FREEZE',
          'FEATURE FREEZE' in out, out[-600:])
    check('...and NEW VERTICAL WORK: NOT PERMITTED. This is the whole point: a '
          'budget that never forbids anything is a dashboard',
          'NEW VERTICAL WORK: NOT PERMITTED' in out, out[-600:])
    check('...and the band printed is stamped with the number that produced it',
          '20.0%' in out, out[-600:])
    P.REGISTER = QUIET
    P.DECISIONS = os.path.join(TMP, 'quiet-decisions.json')
    run(['--decide', 'permanent', 'fixture: a quiet register, nothing ages out'])
    rc, out = run([])
    check('CONTROL: a quiet register is NORMAL and new work IS permitted -- the '
          'gate is not just always-deny with a reason attached',
          'NORMAL' in out and 'NEW VERTICAL WORK: PERMITTED' in out, out[-600:])
    check('CONTROL: the quiet register does NOT report UNCALIBRATED, so that '
          'disclosure is a reading of the data and not printed unconditionally',
          'UNCALIBRATED' not in out, out[-600:])

    print('\n10. REVISIT FIRES ON REAL OUTPUT, AND REVERSES NOTHING')
    # Decided while quiet (NORMAL); the register then goes bad underneath it.
    P.REGISTER = STRAINED
    rc, out = run([])
    check('a recorded decision the data no longer supports prints REVISIT',
          'REVISIT (not reversed)' in out, out[-800:])
    check('...naming both the band it WAS and the band it would be NOW',
          'NORMAL' in out and 'FEATURE FREEZE' in out, out[-800:])
    stored = json.load(io.open(P.DECISIONS, encoding='utf-8'))
    check('...and the stored decision is UNCHANGED on disk. Revisit, not '
          'reverse: a human decides',
          [st['band'] for st in stored['stamps']] == ['NORMAL'], stored['stamps'])
    check('...and the flag says the REGISTER changed, not just the reading',
          'register changed' in out, out[-800:])

    print('\n11. IT REFUSES TO FLATTER ITSELF')
    P.REGISTER = write_register(os.path.join(TMP, 'empty.json'), [])
    try:
        P.load_register()
        check('an EMPTY register RAISES rather than returning a full budget -- '
              'an empty register is the most flattering possible wrong answer',
              False, 'load_register() returned instead of raising')
    except ValueError as e:
        check('an EMPTY register RAISES rather than returning a full budget -- '
              'an empty register is the most flattering possible wrong answer',
              'empty' in str(e).lower(), str(e))
    P.REGISTER = REAL_REGISTER
    real_recs = P.load_register()
    P.DECISIONS = os.path.join(TMP, 'real-undecided.json')
    rc, out = run([])
    check('on the REAL register the tool reports UNCALIBRATED rather than '
          'tuning the budget until the output looks sensible', 'UNCALIBRATED' in out,
          out[:600])
    check('...and prints the OBSERVED rate as the evidence a budget should be '
          'set from', 'OBSERVED rate' in out, out[:900])
    obs = P.observed_rate(real_recs)
    check('the observed rate is computed from the register span, not assumed',
          obs and obs['span_days'] >= 1 and obs['per_window'] > 0, obs)
    check('CONTROL: the observed rate is NOT written back into the budget. '
          'BUDGET_PER_WINDOW is still what the module shipped with -- a budget '
          'auto-tuned to current output permits whatever is happening now',
          abs(P.BUDGET_PER_WINDOW - obs['per_window']) > 1.0,
          (P.BUDGET_PER_WINDOW, obs['per_window']))
    check('DISCLOSURE: and it says so in the output, rather than leaving the '
          'observed number looking like a recommendation',
          'NOT AUTOMATICALLY THE BUDGET' in out, out[:1200])
finally:
    P.DECISIONS, P.REGISTER = REAL_DECISIONS, REAL_REGISTER
    shutil.rmtree(TMP, ignore_errors=True)

print('\n12. THE PROBE CANNOT FORGE A GOVERNANCE RECORD')
check('the module globals are restored',
      P.DECISIONS == REAL_DECISIONS and P.REGISTER == REAL_REGISTER)
check('the real decision file is exactly as it was -- this probe writes only to '
      'a temp path, and a probe that can forge a decision record is worse than '
      'no probe',
      os.path.exists(REAL_DECISIONS) == REAL_EXISTED
      and (not REAL_EXISTED or io.open(REAL_DECISIONS, 'rb').read() == REAL_BYTES))
check('the real defect register is byte-identical -- nothing here edits the '
      'evidence it is judged against',
      io.open(REAL_REGISTER, 'rb').read() == REGISTER_BYTES_BEFORE)
check('the temp directory is gone', not os.path.exists(TMP))

print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
