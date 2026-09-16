"""Item 20 -- a measured defect budget that GATES what gets worked on next.

    python tools/defect_budget_policy.py
    python tools/defect_budget_policy.py --json
    python tools/defect_budget_policy.py --decide rolling|permanent "<why>"
    python tools/defect_budget_policy.py --override "<reason>"   # rare, and counted

Exit 0 always. It REPORTS a band and, once the window question is decided,
states whether new-vertical work is permitted. It never edits anything but its
own decision file.

── WHAT THIS IS, AND WHAT tools/defect_budget.py IS NOT ───────────────────────
`defect_budget.py` ranks WHICH STANDING RULE has bitten most often. That is a
measurement and it changes what the next CONTROL should target.

This is the layer above it: Google's error-budget policy shape, where a measured
number decides WHAT KIND OF WORK IS ALLOWED -- new verticals, or mandatory
reliability work. A budget that only informs is a dashboard; a budget that gates
is a policy, and the difference is whether anything is actually forbidden.

── THE FOUR BANDS, AND WHY NOT TWO ────────────────────────────────────────────
Binary (in budget / out of budget) is the version everybody builds and nobody
keeps, because the day it flips it forbids everything at once and somebody
overrides it. Google's real bands are graduated and so are these:

    > 50 % remaining   NORMAL            new vertical work proceeds
    25 - 50 %          INCREASED REVIEW  new work proceeds, second reviewer
    10 - 25 %          FEATURE FREEZE    reliability work only
    < 10 %             ALL HANDS         reliability work only, everyone

A graduated response is what makes the freeze credible when it comes: by then
two quieter bands have already been visibly in force.

── MARGIN: IT DOES NOT FIRE NEAR A BOUNDARY ───────────────────────────────────
A number that sits on a threshold flips band on noise, and a gate that changes
its mind weekly is one people route around. Inside MARGIN of a boundary the band
DOES NOT CHANGE -- the tool reports APPROACHING and keeps the current band until
the number is past the line with room to spare.

That is deliberately asymmetric in effect and symmetric in code: it delays
entering a stricter band AND delays leaving one. Delaying the exit is the half
that matters, because the temptation is always to declare recovery early.

── EVERY DECISION IS STAMPED WITH THE NUMBER THAT PRODUCED IT ─────────────────
A decision recorded as "FEATURE FREEZE, 2026-09-15" cannot be audited: the
register moves, and next week's reader cannot tell whether the decision was
right on the evidence available. Every stamp carries the criteria version, the
record count, the computed remaining percentage, AND a digest of the register
contents, so a later reader can tell "the number changed" from "the reading was
wrong".

── REVISIT, NOT REVERSE ───────────────────────────────────────────────────────
When a recomputation would have produced a DIFFERENT band from one already
recorded, this raises a REVISIT flag. It does not reverse the decision, and that
restraint is the design: a policy that silently un-freezes itself when the
number drifts back is a policy nobody can rely on, and one that auto-freezes on
a recount is one that fires on noise. A human reads the flag.

── THE WINDOW QUESTION IS FLAGGED, NOT ANSWERED ───────────────────────────────
Rolling window or permanent aging is a real decision with real consequences and
this tool REFUSES TO PICK ONE:

  ROLLING    only defects inside the window count. Recent history is what
             predicts the next month -- but a long-standing defect ages out of
             the budget without anybody fixing it, and the budget recovers for
             free.
  PERMANENT  everything counts forever. Nothing ages out -- but the budget only
             ever goes down, so after enough history the band is ALL HANDS
             permanently and the policy stops discriminating.

Both numbers are computed and printed. Until `--decide` records a choice with a
reason, the tool reports BOTH bands and gates NOTHING. A tool that picked
silently would be making a governance decision inside a utility.

── THE OVERRIDE IS RARE BY CONSTRUCTION ───────────────────────────────────────
An override that can be used habitually is not an override, it is the normal
path with extra typing. So:

  * every use is RECORDED with its reason and its stamp;
  * the count in the trailing window is printed on EVERY run, at the top;
  * past OVERRIDE_ALARM_IN_WINDOW uses, the tool reports the override mechanism
    ITSELF as failed -- it does not refuse the override (a policy that cannot be
    overridden in a real emergency gets disabled entirely), it reports that the
    thing is no longer an exception.

The failure mode being defended against is not one bad override. It is twenty
good ones.

── WHAT IT CANNOT DO ──────────────────────────────────────────────────────────
  * Decide the budget. BUDGET_PER_WINDOW is a judgement and is written here to
    be argued with, not derived.
  * Know whether a defect was serious. It weights by the register's own
    severity field and nothing else.
  * Stop anybody doing anything. It states the band; the humans hold to it.
"""
import hashlib
import io
import json
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO, 'docs', 'defect-density-register.json')
DECISIONS = os.path.join(REPO, 'docs', 'defect-budget-decisions.json')

CRITERIA_VERSION = '2026-09-15.1'

# ── THE BUDGET, WRITTEN TO BE ARGUED WITH ─────────────────────────────────
# Weighted defects allowed per window. Derived from nothing: it is a judgement,
# and a number presented as derived would be harder to change than one presented
# as chosen. Severity weights follow the register's own vocabulary.
BUDGET_PER_WINDOW = 60.0
WINDOW_DAYS = 30
WEIGHTS = {'critical': 5.0, 'high': 3.0, 'moderate': 1.0, 'low': 0.25}

# Percentage points of margin either side of a band boundary. Inside this, the
# band does not change.
MARGIN = 3.0

BANDS = (
    (50.0, 'NORMAL', 'new vertical work proceeds'),
    (25.0, 'INCREASED REVIEW', 'new work proceeds, second reviewer required'),
    (10.0, 'FEATURE FREEZE', 'reliability work only'),
    (0.0, 'ALL HANDS', 'reliability work only, everyone'),
)
NEW_WORK_ALLOWED = {'NORMAL', 'INCREASED REVIEW'}

OVERRIDE_ALARM_IN_WINDOW = 3


def load_register():
    data = json.load(io.open(REGISTER, encoding='utf-8'))
    recs = data['records'] if isinstance(data, dict) else data
    if not recs:
        raise ValueError('the defect register is empty -- an empty register '
                         'produces a full budget, which is the most flattering '
                         'possible wrong answer')
    return recs


def register_digest(recs):
    """WHAT the number was computed from, not just when. A stamp carrying only a
    date cannot tell a later reader "the register changed" from "the reading was
    wrong", which is the only question worth asking about an old decision."""
    key = json.dumps([[r.get('commit'), r.get('date'), r.get('severity'),
                       r.get('subject')] for r in recs], sort_keys=True)
    return hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]


def spent(recs, mode, today=None):
    """Weighted defects counted against the budget, under one window mode."""
    today = today or time.strftime('%Y-%m-%d')
    total = 0.0
    counted = 0
    for r in recs:
        if mode == 'rolling':
            d = r.get('date')
            if not d or days_between(d, today) > WINDOW_DAYS:
                continue
        total += WEIGHTS.get(r.get('severity'), 1.0)
        counted += 1
    return total, counted


def days_between(a, b):
    ta = time.mktime(time.strptime(a, '%Y-%m-%d'))
    tb = time.mktime(time.strptime(b, '%Y-%m-%d'))
    return int(round((tb - ta) / 86400.0))


def remaining_pct(recs, mode, today=None):
    total, counted = spent(recs, mode, today)
    pct = max(0.0, (BUDGET_PER_WINDOW - total) / BUDGET_PER_WINDOW * 100.0)
    return pct, total, counted


def raw_band(pct):
    for floor, name, action in BANDS:
        if pct > floor:
            return name, action
    return BANDS[-1][1], BANDS[-1][2]


def band_with_margin(pct, current):
    """The band, refusing to move while the number is within MARGIN of the
    boundary it would cross.

    Returns (band, action, approaching). `approaching` is the band it WOULD be
    in without the margin, when that differs -- reported so the margin is
    visible rather than a silent stickiness.
    """
    proposed, action = raw_band(pct)
    if current is None or proposed == current:
        return proposed, action, None
    # Distance to the nearest boundary. Inside the margin, hold.
    nearest = min((abs(pct - f) for f, _n, _a in BANDS), default=99.0)
    if nearest < MARGIN:
        held = [(n, a) for f, n, a in BANDS if n == current]
        if held:
            return current, held[0][1], proposed
    return proposed, action, None


def load_decisions():
    if not os.path.exists(DECISIONS):
        return {'criteria_version': CRITERIA_VERSION, 'window_mode': None,
                'window_reason': None, 'stamps': [], 'overrides': []}
    return json.load(io.open(DECISIONS, encoding='utf-8'))


def save_decisions(d):
    io.open(DECISIONS, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(d, indent=2, ensure_ascii=False) + '\n')


def stamp(recs, mode, pct, total, counted, band):
    return {
        'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'criteria_version': CRITERIA_VERSION,
        'window_mode': mode,
        'window_days': WINDOW_DAYS if mode == 'rolling' else None,
        'budget_per_window': BUDGET_PER_WINDOW,
        'records_counted': counted,
        'records_in_register': len(recs),
        'weighted_spent': round(total, 2),
        'remaining_pct': round(pct, 2),
        'band': band,
        'register_digest': register_digest(recs),
    }


def revisit_flags(decisions, recs):
    """Past decisions whose band would be DIFFERENT if recomputed now.

    NOT reversed. A policy that silently un-freezes when the number drifts back
    is one nobody can rely on; one that auto-freezes on a recount fires on noise.
    """
    out = []
    mode = decisions.get('window_mode')
    if not mode:
        return out
    pct, _t, _c = remaining_pct(recs, mode)
    now_band, _a = raw_band(pct)
    for s in decisions.get('stamps', []):
        if s.get('band') and s['band'] != now_band:
            out.append({'decided_at': s['at'], 'was': s['band'], 'now': now_band,
                        'then_pct': s['remaining_pct'], 'now_pct': round(pct, 2),
                        'register_changed': s.get('register_digest')
                                            != register_digest(recs)})
    return out


def observed_rate(recs):
    """The rate the register actually shows, so a budget can be set FROM
    evidence rather than from a feeling. Returned, never applied: a budget set
    to current output permits whatever is happening now by definition."""
    dates = sorted(r.get('date') for r in recs if r.get('date'))
    if not dates:
        return None
    span = max(1, days_between(dates[0], dates[-1]) + 1)
    weighted = sum(WEIGHTS.get(r.get('severity'), 1.0) for r in recs)
    return {'first': dates[0], 'last': dates[-1], 'span_days': span,
            'per_day': weighted / span,
            'per_window': weighted / span * WINDOW_DAYS}


def recent_overrides(decisions, today=None):
    today = today or time.strftime('%Y-%m-%d')
    out = []
    for o in decisions.get('overrides', []):
        d = (o.get('at') or '')[:10]
        try:
            if days_between(d, today) <= WINDOW_DAYS:
                out.append(o)
        except ValueError:
            out.append(o)
    return out


def main(argv):
    recs = load_register()
    dec = load_decisions()

    if '--decide' in argv:
        i = argv.index('--decide')
        mode = argv[i + 1] if len(argv) > i + 1 else ''
        why = ' '.join(argv[i + 2:]).strip()
        if mode not in ('rolling', 'permanent'):
            sys.stderr.write('--decide takes `rolling` or `permanent`.\n')
            return 1
        if len(why) < 20:
            sys.stderr.write('--decide needs a REASON. This is a governance '
                             'choice with a real cost either way; a decision '
                             'with no recorded reason cannot be revisited by '
                             'anybody but the person who made it.\n')
            return 1
        dec['window_mode'] = mode
        dec['window_reason'] = why
        dec['window_decided_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        pct, total, counted = remaining_pct(recs, mode)
        band, _a = raw_band(pct)
        dec.setdefault('stamps', []).append(stamp(recs, mode, pct, total, counted, band))
        save_decisions(dec)
        print('RECORDED: window_mode=%s, band=%s at %.1f%% remaining' % (mode, band, pct))
        return 0

    if '--override' in argv:
        i = argv.index('--override')
        why = ' '.join(argv[i + 1:]).strip()
        if len(why) < 20:
            sys.stderr.write('--override needs a reason, and a real one. An '
                             'override with no recorded justification is the '
                             'normal path with extra typing.\n')
            return 1
        dec.setdefault('overrides', []).append({
            'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'reason': why, 'criteria_version': CRITERIA_VERSION,
            'register_digest': register_digest(recs)})
        save_decisions(dec)
        n = len(recent_overrides(dec))
        print('OVERRIDE RECORDED. %d in the last %d days.' % (n, WINDOW_DAYS))
        if n > OVERRIDE_ALARM_IN_WINDOW:
            print('THE OVERRIDE MECHANISM HAS FAILED, and this is the finding '
                  'rather than any single use: %d in %d days is not an '
                  'exception, it is the process. Either the budget is wrong or '
                  'the band is being ignored -- both are decisions to make out '
                  'loud.' % (n, WINDOW_DAYS))
        return 0

    roll_pct, roll_total, roll_n = remaining_pct(recs, 'rolling')
    perm_pct, perm_total, perm_n = remaining_pct(recs, 'permanent')
    mode = dec.get('window_mode')
    overrides = recent_overrides(dec)

    if '--json' in argv:
        print(json.dumps({
            'criteria_version': CRITERIA_VERSION,
            'window_mode': mode,
            'rolling': {'remaining_pct': round(roll_pct, 2), 'band': raw_band(roll_pct)[0],
                        'counted': roll_n},
            'permanent': {'remaining_pct': round(perm_pct, 2), 'band': raw_band(perm_pct)[0],
                          'counted': perm_n},
            'revisit': revisit_flags(dec, recs),
            'overrides_in_window': len(overrides),
            'register_digest': register_digest(recs),
        }, indent=2))
        return 0

    print('DEFECT BUDGET POLICY -- item 20, criteria %s' % CRITERIA_VERSION)
    if overrides:
        # AT THE TOP, ALWAYS. An override count buried under the verdict is one
        # nobody reads, and the failure mode is twenty good overrides.
        print('  OVERRIDES IN THE LAST %d DAYS: %d%s'
              % (WINDOW_DAYS, len(overrides),
                 '   <- THE MECHANISM HAS FAILED' if len(overrides) > OVERRIDE_ALARM_IN_WINDOW else ''))
    print('  register: %d records, digest %s' % (len(recs), register_digest(recs)))
    print('  budget  : %.0f weighted defects per %d-day window' % (BUDGET_PER_WINDOW, WINDOW_DAYS))
    print('')
    print('  ROLLING   (%d-day window) : %5.1f%% remaining  -> %-16s  %d record(s) counted'
          % (WINDOW_DAYS, roll_pct, raw_band(roll_pct)[0], roll_n))
    print('  PERMANENT (nothing ages) : %5.1f%% remaining  -> %-16s  %d record(s) counted'
          % (perm_pct, raw_band(perm_pct)[0], perm_n))
    print('')

    # ── THE BUDGET IS UNCALIBRATED, AND SAYING SO BEATS TUNING IT ───────────
    # On its first run BOTH windows read 0 % and ALL HANDS. A policy whose very
    # first reading is its most extreme band is not measuring anything: it would
    # freeze all work on day one and be overridden the same afternoon, which is
    # how a gate becomes decoration.
    #
    # THE TEMPTING FIX IS TO RAISE THE BUDGET UNTIL THE OUTPUT LOOKS SENSIBLE.
    # That is tuning the criteria to flatter the corpus -- the failure this
    # platform has a standing rule against -- so the number stays as written and
    # the tool reports that it cannot yet gate, with the OBSERVED RATE that a
    # real budget should be set from.
    obs = observed_rate(recs)
    if obs and raw_band(roll_pct)[0] == BANDS[-1][1] and raw_band(perm_pct)[0] == BANDS[-1][1]:
        print('  UNCALIBRATED -- NOTHING IS GATED ON THIS YET.')
        print('  Both windows read the most extreme band on the first reading,')
        print('  which means the budget is wrong rather than the platform being')
        print('  in crisis. BUDGET_PER_WINDOW is %.0f; the OBSERVED rate is'
              % BUDGET_PER_WINDOW)
        print('  %.1f weighted defects per %d days over %d days of register'
              % (obs['per_window'], WINDOW_DAYS, obs['span_days']))
        print('  (%.1f/day across %d records, %s to %s).'
              % (obs['per_day'], len(recs), obs['first'], obs['last']))
        print('')
        print('  THAT NUMBER IS NOT AUTOMATICALLY THE BUDGET EITHER. It is the')
        print('  rate of a platform in intensive discovery, where finding defects')
        print('  is the WORK -- and a budget set to current output permits')
        print('  whatever is happening now by definition. Setting it is a')
        print('  judgement; this prints the evidence for it and refuses to pick.')
        print('')

    if not mode:
        print('  NO BAND IS IN FORCE, AND NOTHING IS GATED.')
        print('  The window question is a real governance decision and this tool')
        print('  REFUSES TO PICK ONE. ROLLING means a long-standing defect ages')
        print('  out and the budget recovers without anybody fixing it.')
        print('  PERMANENT means the budget only ever falls, so after enough')
        print('  history the band is ALL HANDS for ever and stops discriminating.')
        print('')
        print('    python tools/defect_budget_policy.py --decide rolling "<why>"')
        print('    python tools/defect_budget_policy.py --decide permanent "<why>"')
        print('')
        print('  Both numbers are above. Neither is the answer until somebody')
        print('  records which one this platform is run on, and why.')
        return 0

    pct = roll_pct if mode == 'rolling' else perm_pct
    last = (dec.get('stamps') or [{}])[-1].get('band')
    band, action, approaching = band_with_margin(pct, last)
    print('  WINDOW MODE: %s -- %s' % (mode, dec.get('window_reason', '')[:90]))
    print('  BAND       : %s  (%.1f%% remaining)' % (band, pct))
    print('  ACTION     : %s' % action)
    print('  NEW VERTICAL WORK: %s'
          % ('PERMITTED' if band in NEW_WORK_ALLOWED else 'NOT PERMITTED'))
    if approaching:
        print('  APPROACHING %s -- held at %s because the number is within %.0f '
              'points of the boundary. The margin delays LEAVING a band as well '
              'as entering one, and the exit is the half that matters.'
              % (approaching, band, MARGIN))
    for r in revisit_flags(dec, recs):
        print('  REVISIT (not reversed): a decision recorded %s as %s would be '
              '%s now (%.1f%% -> %.1f%%%s). A human decides.'
              % (r['decided_at'][:10], r['was'], r['now'], r['then_pct'],
                 r['now_pct'], ', register changed' if r['register_changed'] else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
